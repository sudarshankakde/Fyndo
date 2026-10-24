import logging
import secrets
from typing import Annotated, List, Optional
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

logger = logging.getLogger("fyndo.config")

# Secrets that shipped in-repo and must never be trusted for real traffic.
KNOWN_WEAK_SECRETS = {
    "fyndo_super_secret_access_jwt_key_nagpur_mumbai_beta_2026",
    "fyndo_super_secret_refresh_jwt_key_nagpur_mumbai_beta_2026",
    "your_super_secret_jwt_key",
    "changeme",
    "secret",
}
MIN_SECRET_LENGTH = 32
DEV_DEFAULT_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


class Settings(BaseSettings):
    PROJECT_NAME: str = "Fyndo API"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    PORT: int = 5000

    # PostgreSQL Database URL (Asyncpg)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/fyndo_db"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 30
    DB_POOL_TIMEOUT: int = 20
    DB_POOL_RECYCLE_SECONDS: int = 1800

    # Redis Connection
    REDIS_URL: str = "redis://localhost:6379"
    # When true, an unreachable Redis is a hard failure instead of a silent
    # in-memory fallback. Defaults to True in production.
    REDIS_REQUIRED: Optional[bool] = None

    # JWT Authentication (no usable defaults: injected from the environment)
    JWT_ACCESS_SECRET: Optional[str] = None
    JWT_REFRESH_SECRET: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Super Admin Master Credentials
    SUPER_ADMIN_IDENTIFIER: str = "+919999900000"
    SUPER_ADMIN_EMAIL: str = "admin@fyndo.in"
    SUPER_ADMIN_PASSWORD: Optional[str] = "AdminFyndo@2026"

    # Cloudinary Credentials
    CLOUDINARY_CLOUD_NAME: Optional[str] = None
    CLOUDINARY_API_KEY: Optional[str] = None
    CLOUDINARY_API_SECRET: Optional[str] = None
    CLOUDINARY_URL: Optional[str] = None

    # OTP Provider
    SMS_GATEWAY_PROVIDER: str = "mock"  # "mock" | "twilio" | "gupshup"
    SMS_GATEWAY_API_KEY: Optional[str] = "mock_key"

    # CORS (comma separated list accepted from the environment). NoDecode lets
    # the validator below accept both CSV and JSON rather than forcing JSON.
    BACKEND_CORS_ORIGINS: Annotated[List[str], NoDecode] = list(DEV_DEFAULT_ORIGINS)

    # Media pipeline
    UPLOAD_ROOT: str = "uploads"
    MEDIA_MAX_VIDEO_MB: int = 60
    MEDIA_MAX_IMAGE_MB: int = 8
    MEDIA_CHUNK_BYTES: int = 1024 * 1024
    DEFAULT_REEL_THUMBNAIL_URL: Optional[str] = None
    REEL_MIN_SECONDS: int = 15
    REEL_MAX_SECONDS: int = 60
    REEL_OUTPUT_WIDTH: int = 1080
    REEL_OUTPUT_HEIGHT: int = 1920
    REEL_PROCESSING_TIMEOUT_SECONDS: int = 180
    REEL_ENCODE_THREADS: int = 2

    # Rate limiting
    ENABLE_RATE_LIMITING: bool = True
    FEED_RATE_LIMIT_PER_MIN: int = 60
    # How often expired reel offers are checked; 0 disables the background sweep.
    REEL_LIFECYCLE_SWEEP_SECONDS: int = 300
    POS_RATE_LIMIT_PER_MIN: int = 30
    MAX_REQUEST_BYTES: int = 80 * 1024 * 1024

    # Logging (console always; size-rotated files when LOG_TO_FILE)
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Optional[str] = None  # None -> JSON in production, text in dev
    LOG_TO_FILE: bool = True
    LOG_DIR: str = "logs"
    LOG_FILE_NAME: str = "fyndo.log"
    AUDIT_FILE_NAME: str = "audit.log"
    LOG_MAX_BYTES: int = 10 * 1024 * 1024
    LOG_BACKUP_COUNT: int = 5

    # Push notifications (Expo Push Service / FCM gateway)
    PUSH_ENABLED: bool = True
    PUSH_PROVIDER: str = "mock"  # "mock" | "expo" | "fcm"
    EXPO_ACCESS_TOKEN: Optional[str] = None
    PUSH_TIMEOUT_SECONDS: float = 5.0
    NOTIFICATION_RETENTION_DAYS: int = 14
    NOTIFICATION_PAGE_SIZE: int = 30

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.strip().lower() in {"production", "prod"}

    @property
    def cors_allow_credentials(self) -> bool:
        """Credentials are only safe to allow when origins are explicitly listed."""
        return "*" not in self.BACKEND_CORS_ORIGINS

    @property
    def log_json(self) -> bool:
        """Emit JSON logs by default in production, human-readable in development."""
        if not self.LOG_FORMAT:
            return self.is_production
        return self.LOG_FORMAT.strip().lower() == "json"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_origins(cls, value):
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                return value  # let pydantic parse JSON lists
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def _harden_secrets(self) -> "Settings":
        # 1. JWT signing keys: reject weak/shipped values, fail fast in production.
        for field_name in ("JWT_ACCESS_SECRET", "JWT_REFRESH_SECRET"):
            value = getattr(self, field_name)
            is_weak = (
                not value
                or len(value) < MIN_SECRET_LENGTH
                or value in KNOWN_WEAK_SECRETS
            )
            if is_weak:
                if self.is_production:
                    raise ValueError(
                        f"{field_name} must be a strong value "
                        f"(>= {MIN_SECRET_LENGTH} characters) in production."
                    )
                setattr(self, field_name, secrets.token_urlsafe(48))
                logger.warning(
                    "Generated an ephemeral development %s. Set it in .env to keep "
                    "dev sessions stable across restarts.", field_name
                )

        if self.JWT_ACCESS_SECRET == self.JWT_REFRESH_SECRET:
            if self.is_production:
                raise ValueError(
                    "JWT_ACCESS_SECRET and JWT_REFRESH_SECRET must be different in production."
                )
            self.JWT_REFRESH_SECRET = secrets.token_urlsafe(48)

        # 2. Super Admin password: never ship a usable default.
        if not self.SUPER_ADMIN_PASSWORD or len(self.SUPER_ADMIN_PASSWORD) < 10:
            if self.is_production:
                raise ValueError(
                    "SUPER_ADMIN_PASSWORD must be set to a strong value in production."
                )
            self.SUPER_ADMIN_PASSWORD = secrets.token_urlsafe(12)
            logger.warning("Generated an ephemeral development SUPER_ADMIN_PASSWORD.")

        # 3. CORS: a wildcard origin may never be combined with credentials.
        if "*" in self.BACKEND_CORS_ORIGINS:
            if self.is_production:
                raise ValueError("Wildcard CORS origin is not allowed in production.")
            logger.warning(
                "Wildcard CORS origin detected; credentials are disabled for this configuration."
            )

        # 4. Redis is mandatory outside local development.
        if self.REDIS_REQUIRED is None:
            self.REDIS_REQUIRED = self.is_production

        # 5. Production OTP delivery must not silently run in mock mode.
        if self.is_production and (self.SMS_GATEWAY_PROVIDER or "").lower() == "mock":
            logger.error(
                "SMS_GATEWAY_PROVIDER=mock while ENVIRONMENT=production: OTP login will fail."
            )

        return self


settings = Settings()
