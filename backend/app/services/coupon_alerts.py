"""Tells the store, instantly, that a shopper has picked up one of its coupons."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coupon import CouponTemplate, UserCoupon
from app.models.merchant import Merchant
from app.models.notification import NotificationCategory
from app.models.user import User
from app.services.notification_service import NotificationService
from app.services.socket_service import broadcast_safe

COUPON_ENROLLED = "COUPON_ENROLLED"


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


async def announce_coupon_enrolled(
    db: AsyncSession, *, template: CouponTemplate, user_coupon: UserCoupon, shopper: User
) -> None:
    """Inbox alert for the owner plus a live push to every open store screen."""
    shopper_name = shopper.full_name or shopper.username or "A shopper"
    owner_id = (
        await db.execute(select(Merchant.user_id).where(Merchant.id == template.merchant_id))
    ).scalar_one_or_none()
    if owner_id:
        await NotificationService.notify_safe(
            db,
            user_id=owner_id,
            event_type="coupon_enrolled",
            title="New coupon claimed",
            body=f"{shopper_name} just claimed “{template.title}”.",
            category=NotificationCategory.DEALS.value,
            action_type="COUPON_TEMPLATE",
            action_ref=str(template.id),
        )
    await broadcast_safe(
        str(template.merchant_id),
        {
            "event": COUPON_ENROLLED,
            "data": {
                "coupon_template_id": str(template.id),
                "user_coupon_id": str(user_coupon.id),
                "reel_id": str(template.reel_id),
                "coupon_title": template.title,
                "shopper_name": shopper_name,
                "claimed_at": _iso(user_coupon.claimed_at),
            },
        },
    )
