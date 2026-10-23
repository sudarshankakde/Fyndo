import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.api import api_router
from app.admin import admin_router
from app.admin.deps import RedirectToLogin, redirect_to_login_handler
from app.core.config import settings
from app.core.database import Base, engine, ensure_compatibility_schema
from app.core.logging_config import configure_logging
from app.core.logging_middleware import RequestLoggingMiddleware
from app.core.middleware import MaxBodySizeMiddleware, SecurityHeadersMiddleware
from app.core.redis import close_redis_client, get_redis_client
from app.services.reel_lifecycle_service import run_periodic_sweep
import app.models  # Ensure all SQLAlchemy models are registered

configure_logging()
logger = logging.getLogger("fyndo.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle events: startup and shutdown."""
    logger.info("Starting up Fyndo Core API...")

    # Initialize database tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await ensure_compatibility_schema()
        logger.info("PostgreSQL database tables verified and created successfully.")
    except Exception as e:
        logger.error(f"Database schema initialization notice: {e}")

    # Initialize Redis connection
    try:
        await get_redis_client()
    except Exception as e:
        logger.warning(f"Cache initialization notice: {e}")

    sweep_task = None
    if settings.REEL_LIFECYCLE_SWEEP_SECONDS > 0:
        sweep_task = asyncio.create_task(
            run_periodic_sweep(settings.REEL_LIFECYCLE_SWEEP_SECONDS)
        )

    yield

    logger.info("Shutting down Fyndo Core API...")
    if sweep_task:
        sweep_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sweep_task
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

# Middleware stack. Starlette applies these in reverse registration order, so
# the last middleware registered is outermost. Request logging is registered
# last so it observes every request (including CORS preflights and the 413
# emitted by MaxBodySizeMiddleware); CORS sits just inside it so every
# response — including errors — is decorated with the CORS headers.
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(MaxBodySizeMiddleware, max_bytes=settings.MAX_REQUEST_BYTES)
app.add_middleware(
    CORSMiddleware,
    # allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_origins=["*"],
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Formats all standard HTTPExceptions into standard ErrorEnvelope."""
    detail = exc.detail if isinstance(exc.detail, str) else "Request could not be processed."
    details = exc.detail if not isinstance(exc.detail, str) else None
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": detail,
                "details": details
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = [
        {
            "field": ".".join(str(part) for part in error["loc"] if part != "body"),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed.",
                "details": details,
            },
        },
    )


# Mount static uploads directory for direct reel video streaming & thumbnails
import os
from fastapi.staticfiles import StaticFiles

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Register API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

# HTML super-admin panel. It sits outside the API contract, keeps its own
# session cookie, and redirects anonymous visitors to its own login form
# instead of returning a JSON 401 envelope.
app.add_exception_handler(RedirectToLogin, redirect_to_login_handler)
app.include_router(admin_router)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
        "documentation": "/docs",
        "health": f"{settings.API_V1_STR}/health"
    }
