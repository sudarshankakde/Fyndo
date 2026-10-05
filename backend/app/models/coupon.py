import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class DiscountType(str, Enum):
    PERCENTAGE = "PERCENTAGE"
    FLAT_AMOUNT = "FLAT_AMOUNT"
    BOGO = "BOGO"


class CouponStatus(str, Enum):
    CLAIMED = "CLAIMED"
    REDEEMED = "REDEEMED"
    EXPIRED = "EXPIRED"


class CouponTemplate(Base):
    __tablename__ = "coupon_templates"

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
    reel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reels.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    discount_type: Mapped[DiscountType] = mapped_column(String(20), nullable=False)
    discount_value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    min_order_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    validity_days: Mapped[int] = mapped_column(Integer, nullable=False)
    terms: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    merchant = relationship("Merchant")
    reel = relationship("Reel", back_populates="coupon_template")
    user_coupons = relationship("UserCoupon", back_populates="template")


class UserCoupon(Base):
    __tablename__ = "user_coupons"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    coupon_template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coupon_templates.id"),
        nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    status: Mapped[CouponStatus] = mapped_column(
        String(20),
        default=CouponStatus.CLAIMED,
        nullable=False,
        index=True
    )
    totp_secret: Mapped[str] = mapped_column(String(64), nullable=False)
    claimed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    redeemed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    redeemed_by_staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("merchant_staff.id"),
        nullable=True
    )

    # Relationships
    template = relationship("CouponTemplate", back_populates="user_coupons")
    user = relationship("User", back_populates="coupons")


class RedemptionsLedger(Base):
    __tablename__ = "redemptions_ledger"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_coupon_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_coupons.id"),
        unique=True,
        nullable=False
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("merchants.id"),
        nullable=False,
        index=True
    )
    staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("merchant_staff.id"),
        nullable=True
    )
    discount_applied: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    cashier_latitude: Mapped[float] = mapped_column(Float, nullable=True)
    cashier_longitude: Mapped[float] = mapped_column(Float, nullable=True)
    distance_from_shop_m: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
