from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis_client
from app.schemas.common import ResponseEnvelope

router = APIRouter()


@router.get("/health", response_model=ResponseEnvelope[dict])
async def health_check(db: AsyncSession = Depends(get_db)):
    """Liveness/readiness probe verifying the database and cache are reachable."""
    database_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        database_status = f"unreachable ({exc})"

    redis_status = "connected"
    try:
        redis = await get_redis_client()
        await redis.ping()
    except Exception as exc:
        redis_status = f"unreachable ({exc})"

    healthy = database_status == "connected"

    return ResponseEnvelope(
        data={
            "status": "healthy" if healthy else "degraded",
            "service": settings.PROJECT_NAME,
            "environment": settings.ENVIRONMENT,
            "database": database_status,
            "cache": redis_status,
        },
        message="System operational" if healthy else "System degraded",
    )
