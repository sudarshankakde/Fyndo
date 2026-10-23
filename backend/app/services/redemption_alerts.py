from datetime import datetime
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_log
from app.models.coupon import RedemptionsLedger, UserCoupon
from app.models.notification import NotificationCategory
from app.services.notification_service import NotificationService
from app.services.socket_service import broadcast_safe

COUPON_REDEEMED = "COUPON_REDEEMED"


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


async def announce_redemption(
    db: AsyncSession,
    *,
    coupon: UserCoupon,
    ledger: RedemptionsLedger,
    merchant_id: uuid.UUID,
    method: str,
) -> None:
    """Audit-logs the redemption and alerts the shopper and store that the voucher is used."""
    audit_log(
        "coupon.redeem",
        actor_id=ledger.staff_id,
        actor_role="ROLE_CASHIER",
        target_type="user_coupon",
        target_id=coupon.id,
        merchant_id=merchant_id,
        redemption_id=ledger.id,
        method=method,
        bill_amount=float(ledger.bill_amount),
        discount_applied=float(ledger.discount_applied),
    )
    await NotificationService.notify_safe(
        db,
        user_id=coupon.user_id,
        event_type="coupon_redeemed",
        title="Coupon redeemed",
        body=(
            f"“{coupon.template.title}” was redeemed. "
            f"You saved ₹{float(ledger.discount_applied):.0f}."
        ),
        category=NotificationCategory.DEALS.value,
        action_type="COUPON",
        action_ref=str(coupon.id),
    )
    await broadcast_safe(
        str(merchant_id),
        {
            "event": COUPON_REDEEMED,
            "data": {
                "redemption_id": str(ledger.id),
                "user_coupon_id": str(coupon.id),
                "coupon_title": coupon.template.title,
                "bill_amount": float(ledger.bill_amount),
                "discount_applied": float(ledger.discount_applied),
                "redeemed_at": _iso(ledger.created_at),
            },
        },
    )
