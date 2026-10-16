"""Alert copy for moderation decisions.

Keeps user-facing wording out of the endpoint layer and in one place so the
merchant-facing inbox/push messages stay consistent and reviewable.
"""
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.merchant import Merchant
from app.models.notification import NotificationCategory
from app.models.reel import Reel
from app.services.notification_service import NotificationService


async def notify_merchant_decision(
    db: AsyncSession, *, merchant: Merchant, decision: str, rejection_reason: Optional[str]
) -> None:
    """Alerts the store owner that their KYC submission was approved/rejected."""
    approved = decision == "APPROVE"
    await NotificationService.notify_safe(
        db,
        user_id=merchant.user_id,
        event_type="merchant_kyc_approved" if approved else "merchant_kyc_rejected",
        title="Store verified" if approved else "Verification needs attention",
        body=(
            f"{merchant.business_name} is verified. Your reels and offers can now go live."
            if approved
            else (rejection_reason or "Your store verification was not approved.")
        ),
        category=NotificationCategory.SYSTEM.value,
        action_type="MERCHANT",
        action_ref=str(merchant.id),
    )


async def notify_reel_decision(
    db: AsyncSession, *, reel: Reel, owner_id: Optional[uuid.UUID], decision: str
) -> None:
    """Alerts the store owner that a submitted reel passed or failed review."""
    if not owner_id:
        return
    approved = decision == "APPROVE"
    await NotificationService.notify_safe(
        db,
        user_id=owner_id,
        event_type="reel_approved" if approved else "reel_rejected",
        title="Reel is live" if approved else "Reel needs changes",
        body=(
            f"Your reel “{reel.title}” passed review and is now discoverable."
            if approved
            else (reel.rejection_reason or "Your reel did not pass review.")
        ),
        category=NotificationCategory.UPDATES.value,
        action_type="REEL",
        action_ref=str(reel.id),
    )
