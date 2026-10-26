import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Sector(str, Enum):
    FASHION_CLOTHING = "FASHION_CLOTHING"
    GROCERY_SUPERMARKET = "GROCERY_SUPERMARKET"
    CAFE_COFFEE_SHOPS = "CAFE_COFFEE_SHOPS"
    ELECTRONICS = "ELECTRONICS"
    BEAUTY_PERSONAL_CARE = "BEAUTY_PERSONAL_CARE"
    HOME_LIVING = "HOME_LIVING"
    SPORTS_FITNESS = "SPORTS_FITNESS"
    BOOKS_STATIONERY = "BOOKS_STATIONERY"
    KIDS_TOYS = "KIDS_TOYS"
    REAL_ESTATE = "REAL_ESTATE"
    JEWELRY_ACCESSORIES = "JEWELRY_ACCESSORIES"
    TRAVEL_LUGGAGE = "TRAVEL_LUGGAGE"
    FAST_FOOD = "FAST_FOOD"
    RESTAURANTS_DINING = "RESTAURANTS_DINING"
    SALON_SPA = "SALON_SPA"
    ENTERTAINMENT = "ENTERTAINMENT"
    SPORTS_ACTIVITY_CENTERS = "SPORTS_ACTIVITY_CENTERS"
    PETS_SUPPLIES = "PETS_SUPPLIES"
    EVENTS_FESTIVALS = "EVENTS_FESTIVALS"
    OTHER = "OTHER"

    # Backward compatibility aliases
    FOOD = "FOOD"
    FASHION = "FASHION"
    FOOTWEAR = "FOOTWEAR"


class KycStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    business_name: Mapped[str] = mapped_column(String(150), nullable=False)
    sector: Mapped[Sector] = mapped_column(String(30), nullable=False)
    address_text: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    gstin: Mapped[str] = mapped_column(String(20), nullable=True)
    kyc_doc_url: Mapped[str] = mapped_column(String(500), nullable=False)
    kyc_status: Mapped[KycStatus] = mapped_column(
        String(20),
        default=KycStatus.PENDING,
        nullable=False,
        index=True
    )
    kyc_rejection_reason: Mapped[str] = mapped_column(Text, nullable=True)
    # Permanent storefront video; unlike reels it never expires.
    profile_video_url: Mapped[str] = mapped_column(String(500), nullable=True)
    profile_video_thumbnail_url: Mapped[str] = mapped_column(String(500), nullable=True)
    cover_url: Mapped[str] = mapped_column(String(500), nullable=True)
    logo_url: Mapped[str] = mapped_column(String(500), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    phone: Mapped[str] = mapped_column(String(30), nullable=True)
    website: Mapped[str] = mapped_column(String(200), nullable=True)
    business_hours: Mapped[str] = mapped_column(String(100), nullable=True)
    sub_categories: Mapped[str] = mapped_column(Text, nullable=True)
    call_clicks_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
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
    owner = relationship("User", back_populates="merchant")
    staff = relationship("MerchantStaff", back_populates="merchant")
    reels = relationship("Reel", back_populates="merchant")


class MerchantStaff(Base):
    __tablename__ = "merchant_staff"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="CASCADE"),
        nullable=False
    )
    staff_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    pin_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_upload_reels: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    merchant = relationship("Merchant", back_populates="staff")


class MerchantOnboardingDraft(Base):
    __tablename__ = "merchant_onboarding_drafts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    step: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    business_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    sector: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    address_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    pincode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gstin: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    kyc_doc_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
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

