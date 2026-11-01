import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coupon import RedemptionsLedger, UserCoupon
from app.schemas.common import ResponseEnvelope
from app.schemas.coupon import RedemptionVerifyResponse
from app.services.redemption_alerts import announce_redemption
from app.services.redemption_service import RedemptionService


async def record_and_announce_redemption(
    db: AsyncSession,
    *,
    coupon: UserCoupon,
    staff_merchant_id: uuid.UUID,
    staff_id: Optional[uuid.UUID],
    bill_amount: float,
    cashier_lat: Optional[float],
    cashier_lon: Optional[float],
    distance_offset: Optional[float],
    method: str,
    success_message: str,
) -> ResponseEnvelope[RedemptionVerifyResponse]:
    """Records ledger entry, emits audit log and notifications, and builds response envelope."""
    now = datetime.now(timezone.utc)
    discount_type = (
        coupon.template.discount_type.value
        if hasattr(coupon.template.discount_type, "value")
        else str(coupon.template.discount_type)
    )
    discount_applied = RedemptionService.calculate_discount(
        discount_type,
        float(coupon.template.discount_value),
        bill_amount,
    )
    ledger_entry = RedemptionsLedger(
        user_coupon_id=coupon.id,
        merchant_id=staff_merchant_id,
        staff_id=staff_id,
        bill_amount=bill_amount,
        discount_applied=discount_applied,
        cashier_latitude=cashier_lat,
        cashier_longitude=cashier_lon,
        distance_from_shop_m=distance_offset,
        created_at=now,
    )
    db.add(ledger_entry)
    await db.flush()

    customer_name = coupon.user.full_name or coupon.user.phone if coupon.user else None
    await announce_redemption(
        db, coupon=coupon, ledger=ledger_entry, merchant_id=staff_merchant_id, method=method
    )

    return ResponseEnvelope(
        data=RedemptionVerifyResponse(
            redemption_id=ledger_entry.id,
            status="VERIFIED_AND_REDEEMED",
            discount_applied=float(ledger_entry.discount_applied),
            customer_name=customer_name,
            customer_phone=coupon.user.phone if coupon.user else None,
            coupon_title=coupon.template.title,
            timestamp=now,
            bill_amount=bill_amount,
        ),
        message=success_message,
    )
