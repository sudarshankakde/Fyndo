from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import inspect, text
from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""
    pass


# Initialize async SQLAlchemy engine
_is_sqlite = "sqlite" in settings.DATABASE_URL
_engine_kwargs = {
    "echo": bool(getattr(settings, "DB_ECHO", False)),
    "future": True,
    "pool_pre_ping": True,
}
if not _is_sqlite:
    _engine_kwargs.update({
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
        "pool_recycle": settings.DB_POOL_RECYCLE_SECONDS,
    })

if not _is_sqlite:
    _engine_kwargs.setdefault("connect_args", {})
    # Use UTC for PostgreSQL session timezone to prevent invalid OS timezone names (e.g. Windows 'India Standard Time')
    _engine_kwargs["connect_args"].update({"server_settings": {"timezone": "UTC"}})

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

# Async session factory
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

_compatibility_schema_ready = False

# Indexes backing the proximity feed and reel engagement queries. Created with
# IF NOT EXISTS so they are safe to apply to existing databases.
_PERFORMANCE_INDEXES = (
    "CREATE INDEX IF NOT EXISTS ix_merchants_geo ON merchants (latitude, longitude)",
    "CREATE INDEX IF NOT EXISTS ix_merchants_sector ON merchants (sector)",
    "CREATE INDEX IF NOT EXISTS ix_reels_status_created ON reels (status, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_reel_views_reel_created ON reel_views (reel_id, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_reel_comments_reel_created ON reel_comments (reel_id, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_redemptions_ledger_merchant_created "
    "ON redemptions_ledger (merchant_id, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_reels_expires_at ON reels (expires_at)",
    "CREATE INDEX IF NOT EXISTS ix_reel_bookmarks_user ON reel_bookmarks (user_id, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_request_audit_logs_time ON request_audit_logs (timestamp)",
    "CREATE INDEX IF NOT EXISTS ix_request_audit_logs_status_time ON request_audit_logs (status_code, timestamp)",
    "CREATE INDEX IF NOT EXISTS ix_request_audit_logs_path_time ON request_audit_logs (path, timestamp)",
)



# Columns added after the initial beta schema: table -> column -> (sqlite, postgres) DDL.
_COMPAT_COLUMNS = {
    "user_coupons": {
        "backup_pin_used_at": ("DATETIME", "TIMESTAMPTZ NULL"),
    },
    "redemptions_ledger": {
        "bill_amount": ("NUMERIC(10, 2) NOT NULL DEFAULT 0", "NUMERIC(10, 2) NOT NULL DEFAULT 0"),
    },
    "reel_comments": {
        "parent_comment_id": ("UUID NULL", "UUID NULL"),
        "is_pinned": ("BOOLEAN NOT NULL DEFAULT 0", "BOOLEAN NOT NULL DEFAULT FALSE"),
    },
    "users": {
        "username": ("VARCHAR(30) NULL", "VARCHAR(30) NULL"),
        "profile_image_url": ("VARCHAR(500) NULL", "VARCHAR(500) NULL"),
        "latitude": ("FLOAT NULL", "DOUBLE PRECISION NULL"),
        "longitude": ("FLOAT NULL", "DOUBLE PRECISION NULL"),
        "city": ("VARCHAR(100) NULL", "VARCHAR(100) NULL"),
        "address_text": ("TEXT NULL", "TEXT NULL"),
        "pincode": ("VARCHAR(20) NULL", "VARCHAR(20) NULL"),
        "shopping_preferences": ("TEXT NULL", "TEXT NULL"),
        "location_updated_at": ("DATETIME NULL", "TIMESTAMPTZ NULL"),
        "onboarding_completed": ("BOOLEAN NOT NULL DEFAULT 0", "BOOLEAN NOT NULL DEFAULT FALSE"),
    },
    "merchants": {
        "profile_video_url": ("VARCHAR(500) NULL", "VARCHAR(500) NULL"),
        "profile_video_thumbnail_url": ("VARCHAR(500) NULL", "VARCHAR(500) NULL"),
        "cover_url": ("VARCHAR(500) NULL", "VARCHAR(500) NULL"),
        "logo_url": ("VARCHAR(500) NULL", "VARCHAR(500) NULL"),
        "description": ("TEXT NULL", "TEXT NULL"),
        "phone": ("VARCHAR(30) NULL", "VARCHAR(30) NULL"),
        "website": ("VARCHAR(200) NULL", "VARCHAR(200) NULL"),
        "business_hours": ("VARCHAR(100) NULL", "VARCHAR(100) NULL"),
        "call_clicks_count": ("INTEGER NOT NULL DEFAULT 0", "INTEGER NOT NULL DEFAULT 0"),
        "sub_categories": ("TEXT NULL", "TEXT NULL"),
    },
    "merchant_staff": {
        "can_upload_reels": ("BOOLEAN NOT NULL DEFAULT 0", "BOOLEAN NOT NULL DEFAULT FALSE"),
        "can_manage_content": ("BOOLEAN NOT NULL DEFAULT 0", "BOOLEAN NOT NULL DEFAULT FALSE"),
    },
    "reels": {
        "video_hls_url": ("VARCHAR(500) NULL", "VARCHAR(500) NULL"),
        "expires_at": ("DATETIME NULL", "TIMESTAMPTZ NULL"),
        "grace_period_until": ("DATETIME NULL", "TIMESTAMPTZ NULL"),
        "is_expired": ("BOOLEAN NOT NULL DEFAULT 0", "BOOLEAN NOT NULL DEFAULT FALSE"),
        "created_by_staff_id": (
            "UUID NULL",
            "UUID NULL REFERENCES merchant_staff(id) ON DELETE SET NULL",
        ),
    },
    "coupon_templates": {
        "expires_at": ("DATETIME NULL", "TIMESTAMPTZ NULL"),
    },
}


async def ensure_compatibility_schema() -> None:
    """Adds columns/indexes introduced after the initial beta schema when needed."""
    global _compatibility_schema_ready
    if _compatibility_schema_ready:
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        dialect = conn.dialect.name

        if dialect == "sqlite":
            for table, columns in _COMPAT_COLUMNS.items():
                existing = await conn.run_sync(
                    lambda sync_conn, table_name=table: {
                        column["name"] for column in inspect(sync_conn).get_columns(table_name)
                    }
                )
                for column, (definition, _) in columns.items():
                    if column not in existing:
                        await conn.execute(
                            text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                        )
        elif dialect == "postgresql":
            for table, columns in _COMPAT_COLUMNS.items():
                for column, (_, definition) in columns.items():
                    await conn.execute(
                        text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}")
                    )
        for statement in _PERFORMANCE_INDEXES:
            await conn.execute(text(statement))
    _compatibility_schema_ready = True


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing database sessions to FastAPI routes."""
    if not _compatibility_schema_ready:
        await ensure_compatibility_schema()
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
