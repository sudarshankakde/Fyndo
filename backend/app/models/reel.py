import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.time_utils import ist_now


class AudioType(str, Enum):
    CAMERA_MIC = "CAMERA_MIC"
    VOICEOVER = "VOICEOVER"


class ReelStatus(str, Enum):
    PENDING_MODERATION = "PENDING_MODERATION"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Reel(Base):
    __tablename__ = "reels"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    video_url: Mapped[str] = mapped_column(String(500), nullable=False)
    video_hls_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    thumbnail_url: Mapped[str] = mapped_column(String(500), nullable=False)
    cloudinary_public_id: Mapped[str] = mapped_column(String(255), nullable=True)
    audio_type: Mapped[AudioType] = mapped_column(
        String(20),
        default=AudioType.CAMERA_MIC,
        nullable=False
    )
    status: Mapped[ReelStatus] = mapped_column(
        String(30),
        default=ReelStatus.PENDING_MODERATION,
        nullable=False,
        index=True
    )
    rejection_reason: Mapped[str] = mapped_column(Text, nullable=True)
    views_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    allow_comments: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=ist_now,
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=ist_now,
        onupdate=ist_now,
        nullable=False
    )
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    # Offer lifecycle: the clock starts when the reel goes live. Once expired the
    # merchant has until grace_period_until to extend before the reel is removed.
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    grace_period_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_expired: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_staff_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("merchant_staff.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    merchant = relationship("Merchant", back_populates="reels")
    coupon_template = relationship("CouponTemplate", back_populates="reel", uselist=False)
    views = relationship("ReelView", back_populates="reel", cascade="all, delete-orphan")


class ReelView(Base):
    __tablename__ = "reel_views"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    reel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reels.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    viewer_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=ist_now,
        nullable=False,
        index=True
    )

    reel = relationship("Reel", back_populates="views")
