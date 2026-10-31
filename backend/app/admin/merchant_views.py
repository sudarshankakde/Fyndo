"""Admin panel views and actions for merchant management."""
import logging, math, uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.admin.deps import current_admin
from app.admin.helpers import panel_context, record_audit_log
from app.admin.templating import templates
from app.core.database import get_db
from app.models import KycStatus, Merchant, MerchantStaff, Reel, SubscriptionStatus, User
from app.models.audit_log import AuditLog
from app.services.moderation_alerts import notify_merchant_decision
from app.services.settings_service import get_auto_trial_duration_days

logger = logging.getLogger("fyndo.admin.merchants")
router = APIRouter()
PAGE_SIZE = 50


async def _get_merchant_or_404(pk: str, db: AsyncSession) -> Merchant:
    try:
        mid = uuid.UUID(pk)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid merchant UUID.")
    m = (await db.execute(select(Merchant).options(selectinload(Merchant.owner)).where(Merchant.id == mid))).scalars().first()
    if not m:
        raise HTTPException(status_code=404, detail="Merchant not found.")
    return m


@router.get("/merchants")
async def merchant_list_view(
    request: Request,
    sub_filter: str = "ALL",
    kyc_filter: str = "ALL",
    q: str = "",
    page: int = 1,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    now = datetime.now(timezone.utc)
    page = max(1, page)
    stmt = select(Merchant).options(selectinload(Merchant.owner))

    sub_norm = sub_filter.upper().strip()
    if sub_norm == "ACTIVE":
        stmt = stmt.where(Merchant.subscription_status == SubscriptionStatus.ACTIVE, or_(Merchant.subscription_expires_at.is_(None), Merchant.subscription_expires_at > now))
    elif sub_norm == "EXPIRED":
        stmt = stmt.where(or_(Merchant.subscription_status == SubscriptionStatus.EXPIRED, Merchant.subscription_expires_at <= now))
    elif sub_norm == "INACTIVE":
        stmt = stmt.where(Merchant.subscription_status == SubscriptionStatus.INACTIVE)

    kyc_norm = kyc_filter.upper().strip()
    if kyc_norm in ("APPROVED", "PENDING", "REJECTED"):
        stmt = stmt.where(Merchant.kyc_status == KycStatus(kyc_norm))

    if q.strip():
        p = f"%{q.strip()}%"
        stmt = stmt.outerjoin(Merchant.owner).where(or_(Merchant.business_name.ilike(p), Merchant.phone.ilike(p), User.phone.ilike(p), User.full_name.ilike(p)))

    total_count = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one() or 0
    total_pages = max(1, math.ceil(total_count / PAGE_SIZE))
    merchants = (await db.execute(stmt.order_by(Merchant.created_at.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE))).scalars().all()

    m_ids = [m.id for m in merchants]
    reel_counts: Dict[uuid.UUID, int] = {}
    if m_ids:
        r_rows = (await db.execute(select(Reel.merchant_id, func.count(Reel.id)).where(Reel.merchant_id.in_(m_ids)).group_by(Reel.merchant_id))).all()
        reel_counts = {mid: c for mid, c in r_rows}

    return templates.TemplateResponse(
        request, "merchants_list.html",
        panel_context(request, admin, merchants=merchants, reel_counts=reel_counts, total_count=total_count, total_pages=total_pages, current_page=page, sub_filter=sub_norm, kyc_filter=kyc_norm, search_query=q.strip(), now=now)
    )


@router.get("/merchants/{pk}")
async def merchant_detail_view(pk: str, request: Request, db: AsyncSession = Depends(get_db), admin: Dict[str, Any] = Depends(current_admin)):
    merchant = await _get_merchant_or_404(pk, db)
    staff = (await db.execute(select(MerchantStaff).where(MerchantStaff.merchant_id == merchant.id))).scalars().all()
    reels = (await db.execute(select(Reel).where(Reel.merchant_id == merchant.id).order_by(Reel.created_at.desc()))).scalars().all()
    audit_logs = (await db.execute(select(AuditLog).where(AuditLog.target_id == str(merchant.id)).order_by(AuditLog.timestamp.desc()).limit(10))).scalars().all()
    return templates.TemplateResponse(request, "merchant_detail.html", panel_context(request, admin, merchant=merchant, staff=staff, reels=reels, audit_logs=audit_logs, now=datetime.now(timezone.utc)))


def _redirect_target(request: Request, pk: str, ok_msg: str) -> str:
    ref = request.headers.get("referer", "")
    if "/admin/merchants" in ref and f"/admin/merchants/{pk}" not in ref:
        return f"/admin/merchants?ok={ok_msg}"
    return f"/admin/merchants/{pk}?ok={ok_msg}"


@router.post("/merchants/{pk}/subscription/activate")
async def activate_merchant_subscription_action(pk: str, request: Request, db: AsyncSession = Depends(get_db), admin: Dict[str, Any] = Depends(current_admin)):
    m = await _get_merchant_or_404(pk, db)
    form = await request.form()
    duration_raw = form.get("duration_days")
    duration = int(duration_raw) if duration_raw and str(duration_raw).isdigit() else await get_auto_trial_duration_days(db)
    now = datetime.now(timezone.utc)
    m.subscription_status, m.subscription_expires_at = SubscriptionStatus.ACTIVE, now + timedelta(days=duration)
    if m.subscription_start_date is None: m.subscription_start_date = now
    await db.flush()
    await record_audit_log(db, admin_user=admin.get("sub"), action="merchant.subscription_activate", target_type="merchant", target_id=m.id, details={"duration_days": duration})
    await db.commit()
    return RedirectResponse(url=_redirect_target(request, pk, "Subscription+activated"), status_code=303)


@router.post("/merchants/{pk}/subscription/extend")
@router.post("/merchants/{pk}/extend-subscription")
async def extend_merchant_subscription_action(pk: str, request: Request, db: AsyncSession = Depends(get_db), admin: Dict[str, Any] = Depends(current_admin)):
    m = await _get_merchant_or_404(pk, db)
    form = await request.form()
    d_raw = form.get("duration_days") or request.query_params.get("duration_days")
    days = int(d_raw) if d_raw and str(d_raw).isdigit() else 90
    now = datetime.now(timezone.utc)
    cur = m.subscription_expires_at
    if cur and cur.tzinfo is None: cur = cur.replace(tzinfo=timezone.utc)
    base = cur if (cur and cur > now) else now
    m.subscription_expires_at, m.subscription_status = base + timedelta(days=days), SubscriptionStatus.ACTIVE
    if m.subscription_start_date is None: m.subscription_start_date = now
    await db.flush()
    await record_audit_log(db, admin_user=admin.get("sub"), action="merchant.extend_subscription", target_type="merchant", target_id=m.id, details={"duration_days": days})
    await db.commit()
    return RedirectResponse(url=_redirect_target(request, pk, f"Subscription+extended+by+{days}+days"), status_code=303)


@router.post("/merchants/{pk}/subscription/set-expiry")
async def set_merchant_expiry_action(pk: str, request: Request, db: AsyncSession = Depends(get_db), admin: Dict[str, Any] = Depends(current_admin)):
    m = await _get_merchant_or_404(pk, db)
    form = await request.form()
    dt_str = form.get("expiry_date")
    if not dt_str: return RedirectResponse(url=f"/admin/merchants/{pk}?err=Please+select+a+valid+date", status_code=303)
    try:
        parsed = datetime.strptime(str(dt_str).strip(), "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
    except ValueError:
        return RedirectResponse(url=f"/admin/merchants/{pk}?err=Invalid+date+format", status_code=303)
    now = datetime.now(timezone.utc)
    m.subscription_expires_at = parsed
    m.subscription_status = SubscriptionStatus.ACTIVE if parsed > now else SubscriptionStatus.EXPIRED
    if m.subscription_start_date is None: m.subscription_start_date = now
    await db.flush()
    await record_audit_log(db, admin_user=admin.get("sub"), action="merchant.set_expiry", target_type="merchant", target_id=m.id, details={"new_expires_at": parsed.isoformat()})
    await db.commit()
    return RedirectResponse(url=f"/admin/merchants/{pk}?ok=Expiration+set+to+{parsed.strftime('%Y-%m-%d')}", status_code=303)


@router.post("/merchants/{pk}/subscription/deactivate")
async def deactivate_merchant_subscription_action(pk: str, request: Request, db: AsyncSession = Depends(get_db), admin: Dict[str, Any] = Depends(current_admin)):
    m = await _get_merchant_or_404(pk, db)
    m.subscription_status = SubscriptionStatus.INACTIVE
    await db.flush()
    await record_audit_log(db, admin_user=admin.get("sub"), action="merchant.subscription_deactivate", target_type="merchant", target_id=m.id)
    await db.commit()
    return RedirectResponse(url=f"/admin/merchants/{pk}?ok=Subscription+suspended", status_code=303)


@router.post("/merchants/{pk}/kyc/approve")
async def approve_merchant_kyc_action(pk: str, request: Request, db: AsyncSession = Depends(get_db), admin: Dict[str, Any] = Depends(current_admin)):
    m = await _get_merchant_or_404(pk, db)
    m.kyc_status, m.kyc_rejection_reason = KycStatus.APPROVED, None
    await db.flush()
    await record_audit_log(db, admin_user=admin.get("sub"), action="merchant.kyc_decision", target_type="merchant", target_id=m.id, details={"decision": "APPROVE"})
    await notify_merchant_decision(db, merchant=m, decision="APPROVE", rejection_reason=None)
    await db.commit()
    return RedirectResponse(url=_redirect_target(request, pk, "Store+KYC+approved"), status_code=303)


@router.post("/merchants/{pk}/kyc/reject")
async def reject_merchant_kyc_action(pk: str, request: Request, db: AsyncSession = Depends(get_db), admin: Dict[str, Any] = Depends(current_admin)):
    m = await _get_merchant_or_404(pk, db)
    form = await request.form()
    reason = str(form.get("rejection_reason") or "Submitted documents do not match business registration details.").strip()
    m.kyc_status, m.kyc_rejection_reason = KycStatus.REJECTED, reason
    await db.flush()
    await record_audit_log(db, admin_user=admin.get("sub"), action="merchant.kyc_decision", target_type="merchant", target_id=m.id, details={"decision": "REJECT", "rejection_reason": reason})
    await notify_merchant_decision(db, merchant=m, decision="REJECT", rejection_reason=reason)
    await db.commit()
    return RedirectResponse(url=_redirect_target(request, pk, "Store+KYC+rejected"), status_code=303)


@router.post("/merchants/bulk/extend-expired")
async def bulk_extend_expired_merchants_action(request: Request, db: AsyncSession = Depends(get_db), admin: Dict[str, Any] = Depends(current_admin)):
    now = datetime.now(timezone.utc)
    merchants = (await db.execute(select(Merchant).where(or_(Merchant.subscription_status == SubscriptionStatus.EXPIRED, Merchant.subscription_expires_at <= now)))).scalars().all()
    for m in merchants:
        m.subscription_status, m.subscription_expires_at = SubscriptionStatus.ACTIVE, now + timedelta(days=90)
        if m.subscription_start_date is None: m.subscription_start_date = now
    await db.flush()
    await record_audit_log(db, admin_user=admin.get("sub"), action="merchant.bulk_extend_expired", target_type="merchant", details={"extended_count": len(merchants), "duration_days": 90})
    await db.commit()
    return RedirectResponse(url=f"/admin/merchants?ok=Extended+{len(merchants)}+expired+merchants+by+90+days", status_code=303)


@router.post("/merchants/bulk/approve-kyc")
async def bulk_approve_merchant_kyc_action(request: Request, db: AsyncSession = Depends(get_db), admin: Dict[str, Any] = Depends(current_admin)):
    merchants = (await db.execute(select(Merchant).where(Merchant.kyc_status == KycStatus.PENDING))).scalars().all()
    for m in merchants:
        m.kyc_status, m.kyc_rejection_reason = KycStatus.APPROVED, None
        await notify_merchant_decision(db, merchant=m, decision="APPROVE", rejection_reason=None)
    await db.flush()
    await record_audit_log(db, admin_user=admin.get("sub"), action="merchant.bulk_approve_kyc", target_type="merchant", details={"approved_count": len(merchants)})
    await db.commit()
    return RedirectResponse(url=f"/admin/merchants?ok=Approved+{len(merchants)}+pending+merchant+KYC+applications", status_code=303)
