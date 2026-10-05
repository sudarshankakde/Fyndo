from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Fyndo API"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    PORT: int = 5000

    # PostgreSQL Database URL (Asyncpg)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/fyndo_db"

    # Redis Connection
    REDIS_URL: str = "redis://localhost:6379"

    # JWT Authentication
    JWT_ACCESS_SECRET: str = "fyndo_super_secret_access_jwt_key_nagpur_mumbai_beta_2026"
    JWT_REFRESH_SECRET: str = "fyndo_super_secret_refresh_jwt_key_nagpur_mumbai_beta_2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Super Admin Master Credentials
    SUPER_ADMIN_IDENTIFIER: str = "+919999900000"
    SUPER_ADMIN_PASSWORD: str = "AdminFyndo@2026"


    # Cloudinary Credentials
    CLOUDINARY_CLOUD_NAME: Optional[str] = None
    CLOUDINARY_API_KEY: Optional[str] = None
    CLOUDINARY_API_SECRET: Optional[str] = None
    CLOUDINARY_URL: Optional[str] = None

    # OTP Provider
    SMS_GATEWAY_PROVIDER: str = "mock"  # "mock" | "twilio" | "gupshup"
    SMS_GATEWAY_API_KEY: Optional[str] = "mock_key"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
