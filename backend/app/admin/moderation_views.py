"""Admin panel views and actions for reel moderation."""
import logging
import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.admin.deps import current_admin
from app.admin.helpers import panel_context
from app.admin.templating import templates
from app.core.audit import audit_log
from app.core.database import get_db
from app.models import Reel, ReelStatus
from app.services.moderation_alerts import notify_reel_decision
from app.services.reel_lifecycle_service import start_offer_clock

logger = logging.getLogger("fyndo.admin.moderation")
router = APIRouter()


async def _scalar(db: AsyncSession, stmt) -> int:
    return int((await db.execute(stmt)).scalar_one() or 0)


@router.get("/moderation")
async def moderation_view(
    request: Request,
    status: str = "PENDING_MODERATION",
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    stmt = (
        select(Reel)
        .options(selectinload(Reel.merchant), selectinload(Reel.coupon_template))
        .order_by(Reel.created_at.desc())
    )
    filter_norm = status.upper().strip()
    if filter_norm != "ALL":
        try:
            status_enum = ReelStatus(filter_norm)
            stmt = stmt.where(Reel.status == status_enum)
        except ValueError:
            pass

    reels = (await db.execute(stmt)).scalars().all()
    pending_count = await _scalar(
        db,
        select(func.count()).select_from(Reel).where(Reel.status == ReelStatus.PENDING_MODERATION),
    )

    return templates.TemplateResponse(
        request,
        "moderation.html",
        panel_context(
            request,
            admin,
            reels=reels,
            current_filter=filter_norm,
            pending_count=pending_count,
        ),
    )


@router.post("/moderation/reels/{reel_id}/approve")
async def approve_reel_action(
    reel_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    live = (selectinload(Reel.merchant), selectinload(Reel.coupon_template))
    reel = (await db.execute(select(Reel).options(*live).where(Reel.id == reel_id))).scalars().first()
    if reel:
        reel.status = ReelStatus.APPROVED
        reel.rejection_reason = None
        if reel.expires_at is None:
            start_offer_clock(reel, reel.coupon_template)
        await db.flush()
        audit_log(
            "reel.moderate",
            actor_role="SUPER_ADMIN",
            target_type="reel",
            target_id=reel.id,
            decision="APPROVE",
            status="APPROVED",
        )
        owner_id = reel.merchant.user_id if reel.merchant else None
        await notify_reel_decision(db, reel=reel, owner_id=owner_id, decision="APPROVE")
        await db.commit()
    return RedirectResponse(url="/admin/moderation?ok=Reel+approved+and+published+live", status_code=303)


@router.post("/moderation/reels/{reel_id}/reject")
async def reject_reel_action(
    reel_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    form = await request.form()
    reason = str(form.get("rejection_reason") or "Violated content or audio guidelines.").strip()
    live = (selectinload(Reel.merchant), selectinload(Reel.coupon_template))
    reel = (await db.execute(select(Reel).options(*live).where(Reel.id == reel_id))).scalars().first()
    if reel:
        reel.status = ReelStatus.REJECTED
        reel.rejection_reason = reason
        await db.flush()
        audit_log(
            "reel.moderate",
            actor_role="SUPER_ADMIN",
            target_type="reel",
            target_id=reel.id,
            decision="REJECT",
            status="REJECTED",
            rejection_reason=reason,
        )
        owner_id = reel.merchant.user_id if reel.merchant else None
        await notify_reel_decision(db, reel=reel, owner_id=owner_id, decision="REJECT")
        await db.commit()
    return RedirectResponse(url="/admin/moderation?ok=Reel+rejected", status_code=303)

