import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.redis import get_redis_client
from app.models.coupon import CouponStatus, DiscountType, UserCoupon
from app.models.merchant import Merchant
from app.services.totp import TotpService


class RedemptionService:
    @staticmethod
    def calculate_discount(discount_type: str, discount_value: float, bill_amount: float) -> float:
        if discount_type == DiscountType.PERCENTAGE.value:
            return round(min(bill_amount, bill_amount * discount_value / 100), 2)
        return round(min(bill_amount, discount_value), 2)

    @staticmethod
    async def check_pin_rate_limit(staff_id: uuid.UUID, coupon_id: uuid.UUID) -> None:
        redis = await get_redis_client()
        key = f"rate:backup-pin:{staff_id}:{coupon_id}"
        attempts = await redis.incr(key)
        if attempts == 1:
            await redis.expire(key, 600)
        if attempts > 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many backup PIN attempts. Please wait 10 minutes.",
            )

    @staticmethod
    async def validate_qr_for_staff(
        db: AsyncSession,
        qr_payload: str,
        staff_merchant_id: uuid.UUID,
    ) -> Tuple[UserCoupon, str]:
        """
        Validates QR payload format, claim existence, merchant match,
        expiration, and dynamic TOTP cryptographic freshness.
        """
        parsed = TotpService.parse_qr_payload(qr_payload)
        if not parsed or "claim_id" not in parsed or "totp" not in parsed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unrecognized QR code format. Please scan a valid Fyndo pass.",
            )

        try:
            claim_id = uuid.UUID(parsed["claim_id"])
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid coupon voucher claim ID.",
            )

        stmt = (
            select(UserCoupon)
            .options(selectinload(UserCoupon.template), selectinload(UserCoupon.user))
            .where(UserCoupon.id == claim_id)
        )
        res = await db.execute(stmt)
        coupon = res.scalars().first()

        if not coupon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Coupon claim record not found.",
            )

        c_status = coupon.status.value if hasattr(coupon.status, "value") else str(coupon.status)
        if c_status == "REDEEMED":
            redeemed_time = (
                coupon.redeemed_at.strftime("%I:%M %p") if coupon.redeemed_at else "earlier"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"This voucher was already redeemed at {redeemed_time}.",
            )

        exp = (
            coupon.expires_at.replace(tzinfo=timezone.utc)
            if coupon.expires_at.tzinfo is None
            else coupon.expires_at
        )
        if exp < datetime.now(timezone.utc):
            coupon.status = CouponStatus.EXPIRED
            await db.flush()
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="This coupon has expired.",
            )

        # Check store ownership
        if coupon.template.merchant_id != staff_merchant_id:
            merch_res = await db.execute(
                select(Merchant).where(Merchant.id == coupon.template.merchant_id)
            )
            other_merch = merch_res.scalars().first()
            shop_name = other_merch.business_name if other_merch else "another store"
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Wrong Store: This coupon belongs to '{shop_name}', not your store.",
            )

        # Strict 60-second freshness check on payload generation timestamp
        qr_ts = parsed.get("ts")
        if qr_ts and isinstance(qr_ts, (int, float)):
            age_seconds = int(time.time()) - int(qr_ts)
            if age_seconds > 60:
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail=f"QR code expired ({age_seconds}s old). Rotating 60s pass timed out. Please ask customer to refresh their screen.",
                )

        # Dynamic TOTP validation (60-second rotating security code, zero-drift window)
        totp_token = parsed["totp"]
        if not TotpService.verify_token(coupon.totp_secret, totp_token):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="QR code expired. Rotating 60s pass timed out. Please ask customer to refresh their screen.",
            )

        return coupon, totp_token
