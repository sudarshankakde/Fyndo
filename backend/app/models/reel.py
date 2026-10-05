import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    merchant = relationship("Merchant", back_populates="reels")
    coupon_template = relationship("CouponTemplate", back_populates="reel", uselist=False)
