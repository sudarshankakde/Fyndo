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
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.privacy import mask_phone
from app.models.reel import Reel, ReelStatus, ReelView
from app.models.reel_engagement import ReelComment, ReelLike
from app.models.user import User, UserRole
from app.schemas.reel import ReelCommentOut
from app.services.reel_lifecycle_service import live_offer_clause

logger = logging.getLogger("fyndo.reel_engagement")


class ReelNotFoundError(Exception):
    """Raised when the target reel is missing, unapproved or deactivated."""


class CommentNotFoundError(Exception):
    """Raised when a replied-to comment does not exist on the reel."""


def _display_name(user: User) -> str:
    return user.username or user.full_name or mask_phone(user.phone)


def _initial(user: User) -> str:
    return (_display_name(user) or "F")[0].upper()


def _is_store_reply(user: User) -> bool:
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    return role == UserRole.MERCHANT.value


def _comment_out(comment: ReelComment, user: User) -> ReelCommentOut:
    return ReelCommentOut(
        id=comment.id,
        parent_comment_id=comment.parent_comment_id,
        user_name=_display_name(user),
        user_initial=_initial(user),
        profile_image_url=user.profile_image_url,
        text=comment.text,
        created_at=comment.created_at,
        is_store_reply=_is_store_reply(user),
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
    """Records a unique daily view. Returns (views_count, counted)."""
    reel = await _get_live_reel(db, reel_id)
    if not reel:
        raise ReelNotFoundError()

    day_start = datetime.combine(
        datetime.now(timezone.utc).date(), datetime.min.time(), tzinfo=timezone.utc
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

    db.add(
        ReelView(
            reel_id=reel_id,
            user_id=current_user.id if current_user else None,
            viewer_key=viewer_key,
        )
    )
    await db.execute(
        update(Reel)
        .where(Reel.id == reel_id)
        .values(views_count=Reel.views_count + 1)
        .execution_options(synchronize_session=False)
    )
    await db.flush()
    views_count = (
        await db.execute(select(Reel.views_count).where(Reel.id == reel_id))
    ).scalar_one()
    return int(views_count), True


async def toggle_like(db: AsyncSession, *, reel_id: uuid.UUID, user: User) -> Tuple[bool, int]:
    """Adds or removes the current user's like. Returns (liked, likes_count)."""
    if not await _get_live_reel(db, reel_id):
        raise ReelNotFoundError()

    existing = (
        await db.execute(
            select(ReelLike).where(
                ReelLike.reel_id == reel_id, ReelLike.user_id == user.id
            )
        )
    ).scalars().first()

    if existing:
        await db.execute(delete(ReelLike).where(ReelLike.id == existing.id))
        liked = False
    else:
        db.add(ReelLike(reel_id=reel_id, user_id=user.id))
        liked = True
    await db.flush()

    likes_count = (
        await db.execute(select(func.count(ReelLike.id)).where(ReelLike.reel_id == reel_id))
    ).scalar_one()
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
            select(ReelComment, User)
            .join(User, ReelComment.user_id == User.id)
            .where(ReelComment.reel_id == reel_id)
            .order_by(ReelComment.created_at.asc())
            .limit(200)
        )
    ).all()
    return [_comment_out(comment, user) for comment, user in rows]


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
        parent_comment_id = parent.parent_comment_id or parent.id

    comment = ReelComment(
        reel_id=reel_id,
        user_id=user.id,
        parent_comment_id=parent_comment_id,
        text=text.strip(),
    )
    db.add(comment)
    await db.flush()
    await db.refresh(comment)
    return _comment_out(comment, user)
