"""Reel engagement: view counting, likes and comments.

View counting was previously a read-modify-write on `reels.views_count`
(`reel.views_count += 1`) which loses updates when several viewers watch the
same reel at once. It now uses a single atomic SQL `UPDATE ... SET
views_count = views_count + 1`.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.privacy import mask_phone
from app.core.redis import get_redis_client
from app.core.time_utils import ist_now, IST
from app.models.coupon import CouponTemplate
from app.models.merchant import KycStatus, Merchant, MerchantStaff
from app.models.notification import NotificationCategory
from app.models.reel import Reel, ReelStatus, ReelView
from app.models.reel_engagement import ReelComment, ReelLike, ReelBookmark
from app.models.user import User, UserRole
from app.schemas.reel import ReelCommentOut, SavedReelOut
from app.services.notification_service import NotificationService
from app.services.reel_lifecycle_service import live_offer_clause


logger = logging.getLogger("fyndo.reel_engagement")


class ReelNotFoundError(Exception):
    """Raised when the target reel is missing, unapproved or deactivated."""


class CommentNotFoundError(Exception):
    """Raised when a replied-to comment does not exist on the reel."""


def _display_name(user: User, merchant: Optional[Merchant] = None) -> str:
    if merchant and merchant.business_name:
        return merchant.business_name
    return user.full_name or user.username or (mask_phone(user.phone) if user.phone else "Shopper")


def _initial(user: User, merchant: Optional[Merchant] = None) -> str:
    return (_display_name(user, merchant) or "F")[0].upper()


def _is_store_reply(user: User) -> bool:
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    return role == UserRole.MERCHANT.value


def _comment_out(
    comment: ReelComment, user: User, merchant: Optional[Merchant] = None
) -> ReelCommentOut:
    name = _display_name(user, merchant)
    img = (
        merchant.logo_url
        if (merchant and merchant.logo_url)
        else user.profile_image_url
    )
    return ReelCommentOut(
        id=comment.id,
        parent_comment_id=comment.parent_comment_id,
        user_name=name,
        user_initial=_initial(user, merchant),
        profile_image_url=img,
        text=comment.text,
        created_at=comment.created_at,
        is_store_reply=_is_store_reply(user),
        is_pinned=bool(getattr(comment, "is_pinned", False)),
    )


async def _get_live_reel(db: AsyncSession, reel_id: uuid.UUID) -> Optional[Reel]:
    result = await db.execute(
        select(Reel).where(
            Reel.id == reel_id,
            Reel.status == ReelStatus.APPROVED,
            Reel.deleted_at.is_(None),
            live_offer_clause(),
        )
    )
    return result.scalars().first()


async def record_view(
    db: AsyncSession,
    *,
    reel_id: uuid.UUID,
    current_user: Optional[User],
    viewer_key: Optional[str],
) -> Tuple[int, bool]:
    """Records a unique daily view using fast Redis dedup + atomic SQL update."""
    reel = await _get_live_reel(db, reel_id)
    if not reel:
        raise ReelNotFoundError()

    user_or_key = str(current_user.id) if current_user else (viewer_key or "anon")
    today_str = ist_now().strftime("%Y%m%d")
    redis_dedup_key = f"view:dedup:{reel_id}:{today_str}:{user_or_key}"

    # 1. Fast path: Redis deduplication (sub-millisecond, bypasses DB completely for re-views)
    try:
        redis = await get_redis_client()
        is_first_today = await redis.set(redis_dedup_key, "1", ex=86400, nx=True)
        if not is_first_today:
            return int(reel.views_count), False
    except Exception as exc:
        logger.debug(f"Redis view dedup fallback to DB: {exc}")
        day_start = datetime.combine(
            ist_now().date(), datetime.min.time(), tzinfo=IST
        )
        dedup = select(ReelView.id).where(
            ReelView.reel_id == reel_id, ReelView.created_at >= day_start
        )
        if current_user:
            dedup = dedup.where(ReelView.user_id == current_user.id)
        elif viewer_key:
            dedup = dedup.where(ReelView.viewer_key == viewer_key)
        else:
            dedup = None

        if dedup is not None:
            already_seen = (await db.execute(dedup.limit(1))).scalars().first()
            if already_seen:
                return int(reel.views_count), False

    # 2. Record individual view ledger
    db.add(
        ReelView(
            reel_id=reel_id,
            user_id=current_user.id if current_user else None,
            viewer_key=viewer_key,
        )
    )

    # 3. Atomic counter increment with RETURNING (eliminates follow-up SELECT query)
    updated_res = await db.execute(
        update(Reel)
        .where(Reel.id == reel_id)
        .values(views_count=Reel.views_count + 1)
        .returning(Reel.views_count)
        .execution_options(synchronize_session=False)
    )
    await db.flush()
    views_count = updated_res.scalar_one_or_none()
    if views_count is None:
        views_count = int(reel.views_count) + 1
    return int(views_count), True


async def toggle_like(db: AsyncSession, *, reel_id: uuid.UUID, user: User) -> Tuple[bool, int]:
    """Adds or removes the current user's like. Returns (liked, likes_count)."""
    reel = await _get_live_reel(db, reel_id)
    if not reel:
        raise ReelNotFoundError()

    existing = (
        await db.execute(
            select(ReelLike).where(
                ReelLike.reel_id == reel_id, ReelLike.user_id == user.id
            )
        )
    ).scalars().first()

    try:
        async with db.begin_nested():
            if existing:
                await db.execute(delete(ReelLike).where(ReelLike.id == existing.id))
                liked = False
            else:
                db.add(ReelLike(reel_id=reel_id, user_id=user.id))
                liked = True
            await db.flush()
    except IntegrityError:
        # Race condition: concurrent double-tap from same user handled gracefully
        liked = True

    likes_count = (
        await db.execute(select(func.count(ReelLike.id)).where(ReelLike.reel_id == reel_id))
    ).scalar_one()

    if liked:
        reel_merchant = (
            await db.execute(select(Merchant).where(Merchant.id == reel.merchant_id))
        ).scalars().first()
        if reel_merchant and reel_merchant.user_id != user.id:
            liker_name = _display_name(user)
            await NotificationService.notify_safe(
                db,
                user_id=reel_merchant.user_id,
                event_type="reel_like",
                title="New like on your reel",
                body=f"{liker_name} liked your reel \"{reel.title}\"",
                category=NotificationCategory.UPDATES.value,
                image_url=reel.thumbnail_url,
                action_type="REEL",
                action_ref=str(reel.id),
                payload={"reel_id": str(reel.id)},
            )

    return liked, int(likes_count)


async def list_comments(db: AsyncSession, *, reel_id: uuid.UUID) -> List[ReelCommentOut]:
    exists = (
        await db.execute(
            select(Reel.id).where(Reel.id == reel_id, Reel.deleted_at.is_(None))
        )
    ).scalars().first()
    if not exists:
        raise ReelNotFoundError()

    rows = (
        await db.execute(
            select(ReelComment, User, Merchant)
            .join(User, ReelComment.user_id == User.id)
            .outerjoin(Merchant, Merchant.user_id == User.id)
            .where(ReelComment.reel_id == reel_id)
            .order_by(ReelComment.is_pinned.desc(), ReelComment.created_at.asc())
            .limit(200)
        )
    ).all()
    return [_comment_out(comment, user, merchant) for comment, user, merchant in rows]


async def create_comment(
    db: AsyncSession,
    *,
    reel_id: uuid.UUID,
    user: User,
    text: str,
    parent_comment_id: Optional[uuid.UUID],
) -> ReelCommentOut:
    reel = await _get_live_reel(db, reel_id)
    if not reel:
        raise ReelNotFoundError()
    if not reel.allow_comments:
        raise PermissionError("Comments are disabled for this reel.")

    parent = None
    if parent_comment_id:
        parent = (
            await db.execute(
                select(ReelComment).where(
                    ReelComment.id == parent_comment_id, ReelComment.reel_id == reel_id
                )
            )
        ).scalars().first()
        if not parent:
            raise CommentNotFoundError()
        # Flatten replies to a single level for stable threading.
        stored_parent_comment_id = parent.parent_comment_id or parent.id
    else:
        stored_parent_comment_id = None

    comment = ReelComment(
        reel_id=reel_id,
        user_id=user.id,
        parent_comment_id=stored_parent_comment_id,
        text=text.strip(),
        created_at=ist_now(),
    )
    db.add(comment)
    await db.flush()
    await db.refresh(comment)

    merchant = None
    if _is_store_reply(user):
        merchant = (
            await db.execute(select(Merchant).where(Merchant.user_id == user.id))
        ).scalars().first()

    # Dispatch engagement notifications
    commenter_name = _display_name(user, merchant)
    snippet = text.strip()
    if len(snippet) > 80:
        snippet = snippet[:77] + "..."

    # 1. Notify the author of the comment being replied to
    if parent and parent.user_id != user.id:
        await NotificationService.notify_safe(
            db,
            user_id=parent.user_id,
            event_type="reel_comment_reply",
            title=f"{commenter_name} replied to your comment",
            body=f'"{snippet}"',
            category=NotificationCategory.UPDATES.value,
            image_url=reel.thumbnail_url,
            action_type="COMMENT",
            action_ref=str(reel.id),
            payload={
                "reel_id": str(reel.id),
                "comment_id": str(comment.id),
                "parent_comment_id": str(parent.id),
            },
        )

    # 2. Notify the reel author (the merchant) about all engagement on their reel
    reel_merchant = (
        await db.execute(select(Merchant).where(Merchant.id == reel.merchant_id))
    ).scalars().first()

    if reel_merchant and reel_merchant.user_id != user.id:
        if not parent or parent.user_id != reel_merchant.user_id:
            title = (
                f"New reply from {commenter_name}"
                if parent
                else f"New comment from {commenter_name}"
            )
            await NotificationService.notify_safe(
                db,
                user_id=reel_merchant.user_id,
                event_type="reel_comment",
                title=title,
                body=f'"{snippet}" on "{reel.title}"',
                category=NotificationCategory.UPDATES.value,
                image_url=reel.thumbnail_url,
                action_type="COMMENT",
                action_ref=str(reel.id),
                payload={
                    "reel_id": str(reel.id),
                    "comment_id": str(comment.id),
                },
            )

    return _comment_out(comment, user, merchant)


async def toggle_pin_comment(
    db: AsyncSession, *, reel_id: uuid.UUID, comment_id: uuid.UUID, user: User
) -> bool:
    reel = await _get_live_reel(db, reel_id)
    if not reel:
        raise ReelNotFoundError()

    merchant = (
        await db.execute(select(Merchant).where(Merchant.user_id == user.id))
    ).scalars().first()
    is_author = merchant is not None and merchant.id == reel.merchant_id

    if not is_author and user.phone:
        staff = (
            await db.execute(
                select(MerchantStaff).where(
                    MerchantStaff.phone == user.phone,
                    MerchantStaff.merchant_id == reel.merchant_id,
                )
            )
        ).scalars().first()
        if staff:
            is_author = True

    role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
    if not is_author and role_val == "ADMIN":
        is_author = True

    if not is_author:
        raise PermissionError("Only the author of this post can pin comments.")

    comment = (
        await db.execute(
            select(ReelComment).where(
                ReelComment.id == comment_id, ReelComment.reel_id == reel_id
            )
        )
    ).scalars().first()
    if not comment:
        raise CommentNotFoundError()

    if comment.is_pinned:
        comment.is_pinned = False
        pinned = False
    else:
        # Unpin any currently pinned comment on this reel (maximum 1 pinned comment)
        await db.execute(
            update(ReelComment)
            .where(ReelComment.reel_id == reel_id, ReelComment.is_pinned.is_(True))
            .values(is_pinned=False)
        )
        comment.is_pinned = True
        pinned = True

    await db.flush()
    return pinned


async def toggle_bookmark(
    db: AsyncSession, *, reel_id: uuid.UUID, user: User
) -> Tuple[bool, int]:
    """Adds or removes the current user's bookmark on a reel. Returns (bookmarked, bookmarks_count)."""
    if not await _get_live_reel(db, reel_id):
        raise ReelNotFoundError()

    existing = (
        await db.execute(
            select(ReelBookmark).where(
                ReelBookmark.reel_id == reel_id, ReelBookmark.user_id == user.id
            )
        )
    ).scalars().first()

    try:
        async with db.begin_nested():
            if existing:
                await db.execute(delete(ReelBookmark).where(ReelBookmark.id == existing.id))
                bookmarked = False
            else:
                db.add(ReelBookmark(reel_id=reel_id, user_id=user.id))
                bookmarked = True
            await db.flush()
    except IntegrityError:
        # Concurrent double-tap handled gracefully
        bookmarked = True

    count = (
        await db.execute(
            select(func.count(ReelBookmark.id)).where(ReelBookmark.reel_id == reel_id)
        )
    ).scalar_one()
    return bookmarked, int(count)


async def list_saved_reels(db: AsyncSession, *, user: User) -> List[SavedReelOut]:
    """Returns all bookmarked reels for the current user, newest saved first."""
    rows = (
        await db.execute(
            select(ReelBookmark.created_at, Reel, Merchant, CouponTemplate)
            .join(Reel, ReelBookmark.reel_id == Reel.id)
            .join(Merchant, Reel.merchant_id == Merchant.id)
            .outerjoin(CouponTemplate, Reel.id == CouponTemplate.reel_id)
            .where(
                ReelBookmark.user_id == user.id,
                Reel.deleted_at.is_(None),
            )
            .order_by(ReelBookmark.created_at.desc())
        )
    ).all()

    reel_ids = [reel.id for _, reel, _, _ in rows]
    liked_ids = set()
    if reel_ids:
        liked_ids = set(
            (
                await db.execute(
                    select(ReelLike.reel_id).where(
                        ReelLike.user_id == user.id,
                        ReelLike.reel_id.in_(reel_ids),
                    )
                )
            ).scalars().all()
        )

    out: List[SavedReelOut] = []
    for saved_at, reel, merchant, coupon in rows:
        out.append(
            SavedReelOut(
                id=reel.id,
                reel_id=reel.id,
                title=reel.title,
                video_url=reel.video_url,
                video_hls_url=reel.video_hls_url,
                thumbnail_url=reel.thumbnail_url,
                duration_seconds=reel.duration_seconds,
                views_count=reel.views_count,
                likes_count=0,
                is_liked=reel.id in liked_ids,
                is_bookmarked=True,
                shop_name=merchant.business_name,
                merchant_id=merchant.id,
                merchant_logo_url=merchant.logo_url,
                merchant_cover_url=merchant.cover_url,
                merchant_sector=merchant.sector.value if hasattr(merchant.sector, "value") else str(merchant.sector),
                offer_title=coupon.title if coupon else None,
                discount_type=coupon.discount_type.value if coupon and hasattr(coupon.discount_type, "value") else (str(coupon.discount_type) if coupon else None),
                discount_value=float(coupon.discount_value) if coupon else None,
                saved_at=saved_at,
                is_verified=bool(merchant.kyc_status == KycStatus.APPROVED),
            )
        )
    return out

