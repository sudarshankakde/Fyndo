import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class UserRole(str, Enum):
    SHOPPER = "SHOPPER"
    MERCHANT = "MERCHANT"
    SUPER_ADMIN = "SUPER_ADMIN"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    phone: Mapped[str] = mapped_column(
        String(15),
        unique=True,
        index=True,
        nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(100), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, index=True)
    profile_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        String(20),
        default=UserRole.SHOPPER,
        nullable=False
    )
    preferred_language: Mapped[str] = mapped_column(
        String(5),
        default="en",
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    latitude: Mapped[Optional[float]] = mapped_column(nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    address_text: Mapped[Optional[str]] = mapped_column(nullable=True)
    pincode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    shopping_preferences: Mapped[Optional[str]] = mapped_column(nullable=True)
    location_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    merchant = relationship("Merchant", back_populates="owner", uselist=False)
    coupons = relationship("UserCoupon", back_populates="user")
