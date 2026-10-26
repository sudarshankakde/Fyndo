"""Reel engagement endpoints: daily view counting, likes and comments.

Separated from `reels.py` to respect the AGENTS.md 300-line file cap while
keeping every engagement route backed by the atomic
`app/services/reel_engagement_service.py` operations.
"""
import hashlib
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user, get_optional_user
from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.reel import ReelCommentCreate, ReelCommentOut, SavedReelOut
from app.services import reel_engagement_service as engagement

router = APIRouter()


def _viewer_key(request: Request) -> str:
    """Stable anonymous device fingerprint used to dedupe logged-out views."""
    host = request.client.host if request.client else "unknown"
    agent = request.headers.get("user-agent", "")
    return hashlib.sha256(f"{host}|{agent}".encode("utf-8")).hexdigest()[:64]


@router.post("/reels/{reel_id}/view", response_model=ResponseEnvelope[dict])
async def record_reel_view(
    reel_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
    _: None = Depends(rate_limit("reel_view", 600)),
):
    """Records a unique daily view; repeat views within a day are ignored."""
    try:
        views_count, counted = await engagement.record_view(
            db,
            reel_id=reel_id,
            current_user=current_user,
            viewer_key=_viewer_key(request),
        )
    except engagement.ReelNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found.")
    return ResponseEnvelope(data={"views_count": views_count, "counted": counted})


@router.post("/reels/{reel_id}/like", response_model=ResponseEnvelope[dict])
async def toggle_reel_like(
    reel_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(rate_limit("reel_like", 120)),
):
    """Toggles the signed-in shopper's like on a reel."""
    try:
        liked, likes_count = await engagement.toggle_like(db, reel_id=reel_id, user=current_user)
    except engagement.ReelNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found.")
    return ResponseEnvelope(
        data={"liked": liked, "likes_count": likes_count},
        message="Like added." if liked else "Like removed.",
    )


@router.get("/reels/{reel_id}/comments", response_model=ResponseEnvelope[list[ReelCommentOut]])
async def list_reel_comments(
    reel_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit("reel_comments_read", 240)),
):
    """Returns the reel's comments, oldest first, capped at 200 rows."""
    try:
        comments = await engagement.list_comments(db, reel_id=reel_id)
    except engagement.ReelNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found.")
    return ResponseEnvelope(data=comments)


@router.post(
    "/reels/{reel_id}/comments",
    response_model=ResponseEnvelope[ReelCommentOut],
    status_code=status.HTTP_201_CREATED,
)
async def create_reel_comment(
    reel_id: uuid.UUID,
    request: ReelCommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(rate_limit("reel_comment", 30)),
):
    """Posts a comment (or a one-level reply) on a reel."""
    try:
        comment = await engagement.create_comment(
            db,
            reel_id=reel_id,
            user=current_user,
            text=request.text,
            parent_comment_id=request.parent_comment_id,
        )
    except engagement.ReelNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found.")
    except engagement.CommentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The comment you replied to no longer exists.",
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return ResponseEnvelope(data=comment, message="Comment posted.")


@router.get("/reels/saved", response_model=ResponseEnvelope[list[SavedReelOut]])
async def list_saved_reels(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(rate_limit("reels_saved_read", 120)),
):
    """Returns the signed-in user's saved/bookmarked reels."""
    saved = await engagement.list_saved_reels(db, user=current_user)
    return ResponseEnvelope(data=saved)


@router.post("/reels/{reel_id}/bookmark", response_model=ResponseEnvelope[dict])
@router.post("/reels/{reel_id}/save", response_model=ResponseEnvelope[dict])
async def toggle_reel_bookmark(
    reel_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(rate_limit("reel_bookmark", 120)),
):
    """Toggles bookmarking a reel for the current user."""
    try:
        bookmarked, count = await engagement.toggle_bookmark(
            db, reel_id=reel_id, user=current_user
        )
    except engagement.ReelNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found.")
    return ResponseEnvelope(
        data={"bookmarked": bookmarked, "bookmarks_count": count},
        message="Reel saved to collection." if bookmarked else "Reel removed from saved.",
    )

