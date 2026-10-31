"""Subscription Service - Business logic & gating checks for Merchant Subscriptions."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status

from app.models.merchant import Merchant, SubscriptionStatus


def is_subscription_active(merchant: Optional[Merchant]) -> bool:
    """Evaluates whether the merchant's subscription is currently active."""
    if not merchant:
        return False
    return bool(getattr(merchant, "is_subscription_active", False))


def ensure_active_subscription(merchant: Optional[Merchant]) -> None:
    """Enforces active subscription for content creation operations.

    Raises HTTP 403 Forbidden with standard error message if the merchant
    subscription is missing, inactive, or expired.
    """
    if not merchant or not getattr(merchant, "is_subscription_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active merchant subscription required to publish reels. Your subscription is inactive or expired.",
        )
