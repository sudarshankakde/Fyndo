import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import pyotp

from app.core.redis import get_redis_client
from app.models.coupon import CouponStatus, CouponTemplate, DiscountType, UserCoupon
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
        Validates QR payload format (or manual TOTP/backup PIN/pass code),
        claim existence, merchant match, expiration, and cryptographic freshness.
        """
        parsed = TotpService.parse_qr_payload(qr_payload)
        coupon: Optional[UserCoupon] = None
        totp_token: str = ""

        if parsed and "claim_id" in parsed and "totp" in parsed:
            # === Dynamic QR Code Payload ===
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

            # Strict 60-second freshness check on payload generation timestamp
            qr_ts = parsed.get("ts")
            if qr_ts and isinstance(qr_ts, (int, float)):
                age_seconds = int(time.time()) - int(qr_ts)
                if age_seconds > 60:
                    raise HTTPException(
                        status_code=status.HTTP_410_GONE,
                        detail=f"QR code expired ({age_seconds}s old). Rotating 60s pass timed out. Please ask customer to refresh their screen.",
                    )

            totp_token = str(parsed["totp"])
            if not TotpService.verify_token(coupon.totp_secret, totp_token):
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail="QR code expired. Rotating 60s pass timed out. Please ask customer to refresh their screen.",
                )
        else:
            # === Manual Code Entry (6-digit TOTP, 4-digit backup PIN, Pass Code, or UUID) ===
            raw = qr_payload.strip().upper()
            code = raw.replace("FYNDO-", "").replace("FYNDO", "").replace(" ", "").replace("-", "")

            if len(code) < 4:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Please enter at least 4 digits of the customer pass code or PIN.",
                )

            # Fetch active claimed coupons for this store
            stmt = (
                select(UserCoupon)
                .join(UserCoupon.template)
                .options(selectinload(UserCoupon.template), selectinload(UserCoupon.user))
                .where(
                    CouponTemplate.merchant_id == staff_merchant_id,
                    UserCoupon.status == CouponStatus.CLAIMED,
                )
            )
            res = await db.execute(stmt)
            store_coupons = res.scalars().all()

            for c in store_coupons:
                # 1. Check 6-digit TOTP
                if len(code) == 6 and code.isdigit():
                    totp_calc = pyotp.TOTP(c.totp_secret, interval=60)
                    for offset in (-1, 0, 1):
                        if totp_calc.at(int(time.time()) + offset * 60) == code:
                            coupon = c
                            totp_token = code
                            break
                    if coupon:
                        break

                # 2. Check 4-digit Backup PIN
                elif len(code) == 4 and code.isdigit():
                    if not c.backup_pin_used_at and TotpService.verify_backup_pin(c.totp_secret, code):
                        coupon = c
                        totp_token = code
                        break

                # 3. Check coupon ID prefix or full UUID
                c_id_clean = str(c.id).upper().replace("-", "")
                if c_id_clean.startswith(code):
                    coupon = c
                    totp_token = pyotp.TOTP(c.totp_secret, interval=60).now()
                    break

            if not coupon:
                # Check other merchants to provide clear user feedback if wrong store
                other_stmt = (
                    select(UserCoupon)
                    .join(UserCoupon.template)
                    .options(selectinload(UserCoupon.template), selectinload(UserCoupon.user))
                    .where(UserCoupon.status == CouponStatus.CLAIMED)
                )
                other_res = await db.execute(other_stmt)
                all_coupons = other_res.scalars().all()
                for c in all_coupons:
                    if c.template.merchant_id != staff_merchant_id:
                        is_match = False
                        if len(code) == 6 and code.isdigit():
                            totp_calc = pyotp.TOTP(c.totp_secret, interval=60)
                            for offset in (-1, 0, 1):
                                if totp_calc.at(int(time.time()) + offset * 60) == code:
                                    is_match = True
                                    break
                        elif len(code) == 4 and code.isdigit() and not c.backup_pin_used_at:
                            is_match = TotpService.verify_backup_pin(c.totp_secret, code)

                        if is_match:
                            merch_res = await db.execute(
                                select(Merchant).where(Merchant.id == c.template.merchant_id)
                            )
                            other_merch = merch_res.scalars().first()
                            shop_name = other_merch.business_name if other_merch else "another store"
                            raise HTTPException(
                                status_code=status.HTTP_403_FORBIDDEN,
                                detail=f"Wrong Store: This coupon belongs to '{shop_name}', not your store.",
                            )

                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired customer pass code. Please ask the customer to refresh their screen.",
                )

        # Common validations
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

        return coupon, totp_token
