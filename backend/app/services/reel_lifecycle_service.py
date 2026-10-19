"""Offer validity, 24-hour grace window and automatic removal of reels.

Lifecycle of a live reel:
  1. Goes live (approved)        -> clock starts: expires_at = now + validity_days.
  2. now >= expires_at           -> is_expired; hidden from shoppers; merchant warned.
  3. now <  grace_period_until   -> merchant may extend (expires_at + 24h).
  4. now >= grace_period_until   -> reel soft-deleted, coupon deactivated.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.coupon import CouponTemplate
from app.models.merchant import Sector
from app.models.notification import NotificationCategory
from app.models.reel import Reel, ReelStatus
from app.services.notification_service import NotificationService

logger = logging.getLogger("fyndo.reel_lifecycle")

GRACE_PERIOD = timedelta(hours=24)

# Hard sector validity ceilings (docs/AGENTS.md section 2)
SECTOR_VALIDITY_LIMITS = {
    Sector.FOOD: 5,
    Sector.FASHION: 15,
    Sector.FOOTWEAR: 15,
    Sector.ELECTRONICS: 15,
    Sector.REAL_ESTATE: 60,
}


class OfferExtensionError(Exception):
    """Raised when an offer can no longer (or cannot yet) be extended."""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_aware(value: Optional[datetime]) -> Optional[datetime]:
    """SQLite hands back naive datetimes; treat them as UTC."""
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


def max_validity_days(sector) -> int:
    key = Sector(getattr(sector, "value", sector)) if sector else None
    return SECTOR_VALIDITY_LIMITS.get(key, 15)


def live_offer_clause(now: Optional[datetime] = None):
    """Filter for reels whose offer has not run out (legacy reels have no expiry)."""
    now = now or utcnow()
    return or_(Reel.expires_at.is_(None), Reel.expires_at > now)


def start_offer_clock(
    reel: Reel, coupon: Optional[CouponTemplate], now: Optional[datetime] = None
) -> None:
    """Called whenever a reel goes live so the shopper-facing validity is honoured."""
    now = now or utcnow()
    days = coupon.validity_days if coupon else max_validity_days(None)
    _set_expiry(reel, coupon, now + timedelta(days=days))


def _set_expiry(reel: Reel, coupon: Optional[CouponTemplate], expires_at: datetime) -> None:
    reel.expires_at = expires_at
    reel.grace_period_until = expires_at + GRACE_PERIOD
    reel.is_expired = False
    if coupon:
        coupon.expires_at = expires_at


def extend_offer(
    reel: Reel,
    coupon: Optional[CouponTemplate],
    additional_days: int,
    sector,
    now: Optional[datetime] = None,
) -> datetime:
    """Pushes the offer end out by ``additional_days`` from today (sector-capped)."""
    now = now or utcnow()
    if reel.deleted_at is not None:
        raise OfferExtensionError("This offer has already been removed.")
    if reel.expires_at is None:
        raise OfferExtensionError("This offer is not live yet.")
    grace_end = as_aware(reel.grace_period_until)
    if grace_end is not None and now >= grace_end:
        raise OfferExtensionError("The 24-hour window to extend this offer has closed.")

    days = min(additional_days, max_validity_days(sector))
    new_expiry = now + timedelta(days=days)
    current = as_aware(reel.expires_at)
    if current and new_expiry <= current:
        raise OfferExtensionError("The new end date must be later than the current one.")
    _set_expiry(reel, coupon, new_expiry)
    if coupon:
        coupon.validity_days = days
    return new_expiry


async def _notify_owner(db: AsyncSession, reel: Reel, *, event: str, title: str, body: str):
    owner_id = reel.merchant.user_id if reel.merchant else None
    if not owner_id:
        return
    await NotificationService.notify_safe(
        db,
        user_id=owner_id,
        event_type=event,
        title=title,
        body=body,
        category=NotificationCategory.UPDATES.value,
        action_type="REEL",
        action_ref=str(reel.id),
    )


async def sweep_reels(db: AsyncSession, now: Optional[datetime] = None) -> Dict[str, int]:
    """One pass of the lifecycle engine. Safe to run repeatedly."""
    now = now or utcnow()
    counts = {"started": 0, "expired": 0, "removed": 0}
    base = (
        select(Reel)
        .options(selectinload(Reel.merchant), selectinload(Reel.coupon_template))
        .where(Reel.deleted_at.is_(None))
    )

    # Live reels approved outside the API (e.g. admin panel edits) get their clock now.
    unstarted = await db.execute(
        base.where(Reel.status == ReelStatus.APPROVED, Reel.expires_at.is_(None))
    )
    for reel in unstarted.scalars().all():
        start_offer_clock(reel, reel.coupon_template, now)
        counts["started"] += 1
    await db.flush()

    newly_expired = await db.execute(
        base.where(Reel.is_expired.is_(False), Reel.expires_at <= now)
    )
    for reel in newly_expired.scalars().all():
        reel.is_expired = True
        counts["expired"] += 1
        await _notify_owner(
            db, reel,
            event="reel_offer_expired",
            title="Your offer has ended",
            body=f"“{reel.title}” is no longer shown to shoppers. "
                 "Extend it within 24 hours or it will be removed.",
        )
    await db.flush()

    past_grace = await db.execute(
        base.where(Reel.is_expired.is_(True), Reel.grace_period_until <= now)
    )
    for reel in past_grace.scalars().all():
        reel.deleted_at = now
        if reel.coupon_template:
            reel.coupon_template.is_active = False
        counts["removed"] += 1
        await _notify_owner(
            db, reel,
            event="reel_offer_removed",
            title="Offer removed",
            body=f"“{reel.title}” was removed because its offer ended.",
        )

    await db.flush()
    return counts


async def run_periodic_sweep(interval_seconds: int) -> None:
    """Background loop started from the app lifespan."""
    from app.core.database import async_session_factory

    while True:
        try:
            async with async_session_factory() as session:
                counts = await sweep_reels(session)
                await session.commit()
            if any(counts.values()):
                logger.info("Reel lifecycle sweep: %s", counts)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("Reel lifecycle sweep failed", exc_info=True)
        await asyncio.sleep(interval_seconds)
