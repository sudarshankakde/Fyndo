import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.redis import close_redis_client, get_redis_client
import app.models  # Ensure all SQLAlchemy models are registered

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("fyndo.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle events: startup and shutdown."""
    logger.info("Starting up Fyndo Core API...")

    # Initialize database tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("PostgreSQL database tables verified and created successfully.")
    except Exception as e:
        logger.error(f"Database schema initialization notice: {e}")

    # Initialize Redis connection
    try:
        await get_redis_client()
    except Exception as e:
        logger.warning(f"Cache initialization notice: {e}")

    yield

    logger.info("Shutting down Fyndo Core API...")
    await close_redis_client()
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Hyper-Local Short Video & In-Store Digital Coupon Platform API",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Formats all standard HTTPExceptions into standard ErrorEnvelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail
            }
        }
    )


# Mount static uploads directory for direct reel video streaming & thumbnails
import os
from fastapi.staticfiles import StaticFiles

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Register API Router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
        "documentation": "/docs",
        "health": f"{settings.API_V1_STR}/health"
    }
