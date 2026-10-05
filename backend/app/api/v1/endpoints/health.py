from fastapi import APIRouter
from app.core.config import settings
from app.core.redis import get_redis_client
from app.schemas.common import ResponseEnvelope

router = APIRouter()


@router.get("/health", response_model=ResponseEnvelope[dict])
async def health_check():
    """System health check endpoint verifying application and cache availability."""
    redis_status = "connected"
    try:
        redis = await get_redis_client()
        await redis.ping()
    except Exception as e:
        redis_status = f"unreachable ({e})"

    health_data = {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "cache": redis_status
    }
    return ResponseEnvelope(data=health_data, message="System operational")
