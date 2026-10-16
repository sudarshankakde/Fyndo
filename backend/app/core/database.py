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
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=(settings.ENVIRONMENT == "development"),
    future=True,
    pool_pre_ping=True
)

# Async session factory
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

_compatibility_schema_ready = False


async def ensure_compatibility_schema() -> None:
    """Adds columns introduced after the initial beta schema when needed."""
    global _compatibility_schema_ready
    if _compatibility_schema_ready:
        return

    async with engine.begin() as conn:
        dialect = conn.dialect.name
        if dialect == "sqlite":
            tables_and_columns = {
                "user_coupons": {
                    "backup_pin_used_at": "DATETIME",
                },
                "redemptions_ledger": {
                    "bill_amount": "NUMERIC(10, 2) NOT NULL DEFAULT 0",
                },
                "reel_comments": {
                    "parent_comment_id": "UUID NULL",
                },
                "users": {
                    "username": "VARCHAR(30) NULL",
                    "profile_image_url": "VARCHAR(500) NULL",
                },
            }
            for table, columns in tables_and_columns.items():
                existing = await conn.run_sync(
                    lambda sync_conn, table_name=table: {
                        column["name"] for column in inspect(sync_conn).get_columns(table_name)
                    }
                )
                for column, definition in columns.items():
                    if column not in existing:
                        await conn.execute(
                            text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                        )
        elif dialect == "postgresql":
            await conn.execute(
                text(
                    "ALTER TABLE user_coupons ADD COLUMN IF NOT EXISTS "
                    "backup_pin_used_at TIMESTAMPTZ NULL"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE redemptions_ledger ADD COLUMN IF NOT EXISTS "
                    "bill_amount NUMERIC(10, 2) NOT NULL DEFAULT 0"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE reel_comments ADD COLUMN IF NOT EXISTS "
                    "parent_comment_id UUID NULL"
                )
            )
    _compatibility_schema_ready = True


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing database sessions to FastAPI routes."""
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
