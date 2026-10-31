"""Admin panel views and actions for Merchant KYC queue verification."""
import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.admin.deps import current_admin
from app.admin.helpers import panel_context, record_audit_log
from app.admin.templating import templates
from app.core.database import get_db
from app.models import KycStatus, Merchant
from app.services.moderation_alerts import notify_merchant_decision

logger = logging.getLogger("fyndo.admin.kyc")
router = APIRouter()


async def _get_merchant(pk: str, db: AsyncSession) -> Merchant:
    try:
        merchant_id = uuid.UUID(pk)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid merchant UUID.")
    merchant = (
        await db.execute(
            select(Merchant)
            .options(selectinload(Merchant.owner))
            .where(Merchant.id == merchant_id)
        )
    ).scalars().first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found.")
    return merchant


@router.get("/kyc")
async def kyc_queue_view(
    request: Request,
    status: str = "PENDING",
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    """Lists merchants requiring or having completed KYC verification."""
    stmt = select(Merchant).options(selectinload(Merchant.owner)).order_by(Merchant.created_at.desc())
    status_filter = status.upper().strip()

    if status_filter != "ALL":
        try:
            enum_status = KycStatus(status_filter)
            stmt = stmt.where(Merchant.kyc_status == enum_status)
        except ValueError:
            stmt = stmt.where(Merchant.kyc_status == KycStatus.PENDING)
            status_filter = "PENDING"

    merchants = (await db.execute(stmt)).scalars().all()
    pending_count = (
        await db.execute(
            select(func.count()).select_from(Merchant).where(Merchant.kyc_status == KycStatus.PENDING)
        )
    ).scalar_one() or 0

    return templates.TemplateResponse(
        request,
        "kyc_queue.html",
        panel_context(
            request,
            admin,
            merchants=merchants,
            current_filter=status_filter,
            pending_count=pending_count,
        ),
    )


@router.post("/kyc/{pk}/approve")
async def approve_kyc_action(
    pk: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    """Approves a merchant's store KYC verification."""
    merchant = await _get_merchant(pk, db)
    merchant.kyc_status = KycStatus.APPROVED
    merchant.kyc_rejection_reason = None
    await db.flush()

    await record_audit_log(
        db,
        admin_user=admin.get("sub"),
        action="merchant.kyc_decision",
        target_type="merchant",
        target_id=merchant.id,
        details={"decision": "APPROVE"},
    )
    await notify_merchant_decision(db, merchant=merchant, decision="APPROVE", rejection_reason=None)
    await db.commit()

    ref = request.headers.get("referer", "")
    target = f"/admin/merchants/{pk}?ok=Store+KYC+approved" if f"/admin/merchants/{pk}" in ref else "/admin/kyc?ok=Merchant+KYC+approved+successfully"
    return RedirectResponse(url=target, status_code=303)


@router.post("/kyc/{pk}/reject")
async def reject_kyc_action(
    pk: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    """Rejects a merchant's store KYC verification with an explicit reason."""
    merchant = await _get_merchant(pk, db)
    form = await request.form()
    reason = str(
        form.get("rejection_reason")
        or "Submitted documents do not match business registration details."
    ).strip()
    merchant.kyc_status = KycStatus.REJECTED
    merchant.kyc_rejection_reason = reason
    await db.flush()

    await record_audit_log(
        db,
        admin_user=admin.get("sub"),
        action="merchant.kyc_decision",
        target_type="merchant",
        target_id=merchant.id,
        details={"decision": "REJECT", "rejection_reason": reason},
    )
    await notify_merchant_decision(db, merchant=merchant, decision="REJECT", rejection_reason=reason)
    await db.commit()

    ref = request.headers.get("referer", "")
    target = f"/admin/merchants/{pk}?ok=Store+KYC+rejected" if f"/admin/merchants/{pk}" in ref else "/admin/kyc?ok=Merchant+KYC+rejected"
    return RedirectResponse(url=target, status_code=303)


@router.post("/kyc/bulk-approve")
async def bulk_approve_kyc_action(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    """Bulk approves all merchants currently pending KYC verification."""
    stmt = select(Merchant).where(Merchant.kyc_status == KycStatus.PENDING)
    merchants = (await db.execute(stmt)).scalars().all()
    count = 0
    for merchant in merchants:
        merchant.kyc_status = KycStatus.APPROVED
        merchant.kyc_rejection_reason = None
        await notify_merchant_decision(db, merchant=merchant, decision="APPROVE", rejection_reason=None)
        count += 1

    await db.flush()
    await record_audit_log(
        db,
        admin_user=admin.get("sub"),
        action="merchant.bulk_kyc_approve",
        target_type="merchant",
        details={"approved_count": count},
    )
    await db.commit()
    return RedirectResponse(url=f"/admin/kyc?ok=Bulk+approved+{count}+pending+merchants", status_code=303)
