from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.core.redis import get_redis_client
from app.schemas.common import ResponseEnvelope

router = APIRouter()


@router.get("/health", response_model=ResponseEnvelope[dict])
async def health_check():
    """Liveness/readiness probe verifying the database and cache are reachable."""
    database_status = "connected"
    try:
        from app.core.database import async_session_factory
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
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
