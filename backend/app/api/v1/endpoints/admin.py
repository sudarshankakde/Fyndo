import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.api.v1.endpoints.auth import get_current_user
from app.core.database import get_db
from app.models.reel import Reel, ReelStatus
from app.models.user import User, UserRole
from app.schemas.admin import AdminReelListItem, ModerationDecisionRequest
from app.schemas.common import ResponseEnvelope

router = APIRouter()


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency verifying Super Admin privileges."""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin privileges required."
        )
    return current_user


@router.get("/admin/moderation/reels", response_model=ResponseEnvelope[List[AdminReelListItem]])
async def list_pending_reels(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Lists all reels currently queued in PENDING_MODERATION state."""
    stmt = (
        select(Reel)
        .options(selectinload(Reel.merchant), selectinload(Reel.coupon_template))
        .where(Reel.status == ReelStatus.PENDING_MODERATION)
        .where(Reel.deleted_at.is_(None))
        .order_by(Reel.created_at.asc())
    )
    res = await db.execute(stmt)
    reels = res.scalars().all()

    items: List[AdminReelListItem] = []
    for r in reels:
        def get_val(v):
            return v.value if hasattr(v, "value") else str(v) if v is not None else None

        m = r.merchant
        ct = r.coupon_template
        items.append(
            AdminReelListItem(
                id=r.id,
                title=r.title,
                video_url=r.video_url,
                thumbnail_url=r.thumbnail_url,
                duration_seconds=r.duration_seconds,
                audio_type=get_val(r.audio_type),
                status=get_val(r.status),
                merchant_id=m.id if m else uuid.uuid4(),
                merchant_name=m.business_name if m else "Unknown",
                sector=get_val(m.sector) if m else "GENERAL",
                city=m.city if m else "Nagpur",
                coupon_title=ct.title if ct else None,
                discount_type=get_val(ct.discount_type) if ct else None,
                discount_value=float(ct.discount_value) if ct else None,
                min_order_amount=float(ct.min_order_amount) if ct else None,
                validity_days=ct.validity_days if ct else None
            )
        )

    return ResponseEnvelope(data=items)


@router.post("/admin/moderation/reels/{reel_id}/decision", response_model=ResponseEnvelope[dict])
async def decide_reel_moderation(
    reel_id: uuid.UUID,
    payload: ModerationDecisionRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Approves or rejects a reel in moderation queue."""
    stmt = select(Reel).where(Reel.id == reel_id)
    res = await db.execute(stmt)
    reel = res.scalars().first()
    if not reel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found.")

    decision_norm = payload.decision.upper()
    if decision_norm == "APPROVE":
        reel.status = ReelStatus.APPROVED
        reel.rejection_reason = None
        message = "Reel approved and pushed to live discovery feed."
    elif decision_norm == "REJECT":
        reel.status = ReelStatus.REJECTED
        reel.rejection_reason = payload.rejection_reason or "Violated content or audio guidelines."
        message = "Reel rejected."
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision must be either 'APPROVE' or 'REJECT'."
        )

    status_str = reel.status.value if hasattr(reel.status, "value") else str(reel.status)
    return ResponseEnvelope(
        data={"reel_id": str(reel.id), "status": status_str},
        message=message
    )
