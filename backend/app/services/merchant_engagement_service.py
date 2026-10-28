"""Store follows, call-button tracking, ratings and the owner's insight counters."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import case, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coupon import CouponStatus, UserCoupon
from app.models.merchant import Merchant
from app.models.merchant_engagement import MerchantCallClick, MerchantFollower, MerchantRating
from app.models.reel import Reel
from app.models.user import User

# Repeated taps from the same person within this window count once.
CALL_DEDUP_WINDOW = timedelta(seconds=60)


async def followers_count(db: AsyncSession, merchant_id: uuid.UUID) -> int:
    stmt = select(func.count(MerchantFollower.id)).where(MerchantFollower.merchant_id == merchant_id)
    return int((await db.execute(stmt)).scalar_one() or 0)


async def is_following(db: AsyncSession, merchant_id: uuid.UUID, user: Optional[User]) -> bool:
    if not user:
        return False
    stmt = select(MerchantFollower.id).where(
        MerchantFollower.merchant_id == merchant_id, MerchantFollower.user_id == user.id
    )
    return (await db.execute(stmt)).first() is not None


async def toggle_follow(db: AsyncSession, merchant_id: uuid.UUID, user: User) -> Tuple[bool, int]:
    """Follows when not following, unfollows otherwise. Returns (following, count)."""
    existing = (
        await db.execute(
            select(MerchantFollower).where(
                MerchantFollower.merchant_id == merchant_id, MerchantFollower.user_id == user.id
            )
        )
    ).scalars().first()
    if existing:
        await db.delete(existing)
        following = False
    else:
        try:
            async with db.begin_nested():
                db.add(MerchantFollower(merchant_id=merchant_id, user_id=user.id))
        except IntegrityError:
            pass  # A concurrent tap already created the follow.
        following = True
    await db.flush()
    return following, await followers_count(db, merchant_id)


async def list_following(db: AsyncSession, user: User) -> List[Tuple[Merchant, datetime]]:
    rows = await db.execute(
        select(Merchant, MerchantFollower.created_at)
        .join(MerchantFollower, MerchantFollower.merchant_id == Merchant.id)
        .where(MerchantFollower.user_id == user.id)
        .order_by(MerchantFollower.created_at.desc())
    )
    return [(merchant, followed_at) for merchant, followed_at in rows.all()]


async def track_call(
    db: AsyncSession,
    merchant_id: uuid.UUID,
    user: Optional[User],
    device_fingerprint: Optional[str],
) -> bool:
    """Logs a 'Call store' tap. Returns False when it was a duplicate tap."""
    if user or device_fingerprint:
        since = datetime.now(timezone.utc) - CALL_DEDUP_WINDOW
        stmt = select(MerchantCallClick.id).where(
            MerchantCallClick.merchant_id == merchant_id,
            MerchantCallClick.created_at >= since,
        )
        if user:
            stmt = stmt.where(MerchantCallClick.user_id == user.id)
        else:
            stmt = stmt.where(MerchantCallClick.device_fingerprint == device_fingerprint)
        if (await db.execute(stmt.limit(1))).first():
            return False

    db.add(MerchantCallClick(
        merchant_id=merchant_id,
        user_id=user.id if user else None,
        device_fingerprint=device_fingerprint,
    ))
    await db.execute(
        update(Merchant)
        .where(Merchant.id == merchant_id)
        .values(call_clicks_count=Merchant.call_clicks_count + 1)
    )
    await db.flush()
    return True


async def upsert_rating(
    db: AsyncSession, merchant_id: uuid.UUID, user: User, rating: int, review_text: Optional[str]
) -> MerchantRating:
    row = (
        await db.execute(
            select(MerchantRating).where(
                MerchantRating.merchant_id == merchant_id, MerchantRating.user_id == user.id
            )
        )
    ).scalars().first()
    if row is None:
        row = MerchantRating(merchant_id=merchant_id, user_id=user.id)
        db.add(row)
    row.rating = rating
    row.review_text = review_text
    row.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(row)
    return row


async def user_rating(
    db: AsyncSession, merchant_id: uuid.UUID, user: Optional[User]
) -> Optional[int]:
    if not user:
        return None
    stmt = select(MerchantRating.rating).where(
        MerchantRating.merchant_id == merchant_id, MerchantRating.user_id == user.id
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def rating_summary(db: AsyncSession, merchant_id: uuid.UUID) -> Dict:
    rows = (
        await db.execute(
            select(MerchantRating.rating, func.count(MerchantRating.id))
            .where(MerchantRating.merchant_id == merchant_id)
            .group_by(MerchantRating.rating)
        )
    ).all()
    breakdown = {str(star): 0 for star in range(1, 6)}
    total = 0
    weighted = 0
    for star, count in rows:
        breakdown[str(star)] = int(count)
        total += int(count)
        weighted += int(star) * int(count)
    average = round(weighted / total, 1) if total else 0.0
    return {"average": average, "count": total, "breakdown": breakdown}


async def recent_reviews(
    db: AsyncSession, merchant_id: uuid.UUID, limit: int = 20
) -> List[Tuple[MerchantRating, User]]:
    rows = await db.execute(
        select(MerchantRating, User)
        .join(User, User.id == MerchantRating.user_id)
        .where(MerchantRating.merchant_id == merchant_id)
        .order_by(MerchantRating.updated_at.desc())
        .limit(limit)
    )
    return [(rating, user) for rating, user in rows.all()]


async def merchant_insights(db: AsyncSession, merchant: Merchant) -> Dict:
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    calls_7d = (
        await db.execute(
            select(func.count(MerchantCallClick.id)).where(
                MerchantCallClick.merchant_id == merchant.id,
                MerchantCallClick.created_at >= week_ago,
            )
        )
    ).scalar_one()
    reel_views = (
        await db.execute(
            select(func.coalesce(func.sum(Reel.views_count), 0)).where(Reel.merchant_id == merchant.id)
        )
    ).scalar_one()
    summary = await rating_summary(db, merchant.id)
    return {
        "followers_count": await followers_count(db, merchant.id),
        "call_clicks_total": merchant.call_clicks_count or 0,
        "call_clicks_last_7_days": int(calls_7d or 0),
        "reel_views_total": int(reel_views or 0),
        "rating_average": summary["average"],
        "rating_count": summary["count"],
    }


async def coupon_counts_for_templates(
    db: AsyncSession, template_ids: List[uuid.UUID]
) -> Dict[uuid.UUID, Tuple[int, int]]:
    """Batched counts of (claims, redemptions) keyed by coupon_template_id."""
    if not template_ids:
        return {}
    stmt = (
        select(
            UserCoupon.coupon_template_id,
            func.count(UserCoupon.id),
            func.coalesce(
                func.sum(
                    case((UserCoupon.status == CouponStatus.REDEEMED, 1), else_=0)
                ),
                0,
            ),
        )
        .where(UserCoupon.coupon_template_id.in_(template_ids))
        .group_by(UserCoupon.coupon_template_id)
    )
    rows = (await db.execute(stmt)).all()
    return {row[0]: (int(row[1]), int(row[2])) for row in rows}
