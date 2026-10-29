"""Dashboard, list and detail views for the HTML super-admin panel."""
import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.admin.deps import current_admin
from app.admin.helpers import form_fields, get_row, meta_or_404, panel_context, redirect_to
from app.admin.registry import ALL_MODELS
from app.admin.templating import templates
from app.admin.utils import count_rows, query_page, serialize_detail, serialize_row
from app.api.v1.endpoints.admin_system import (
    get_db_stats,
    get_redis_stats,
    get_system_resources,
)
from app.core.audit import audit_log
from app.core.database import get_db
from app.models import (
    CouponStatus,
    KycStatus,
    Merchant,
    Notification,
    Reel,
    ReelStatus,
    UserCoupon,
)
from app.models.system_settings import AUTO_APPROVE_REELS
from app.services.audit_service import (
    enrich_logs_with_user_details,
    get_audit_stats,
    query_audit_logs,
)
from app.services.moderation_alerts import notify_reel_decision
from app.services.reel_lifecycle_service import start_offer_clock
from app.services.settings_service import is_auto_approve_enabled, set_setting

logger = logging.getLogger("fyndo.admin")
router = APIRouter()


async def _scalar(db: AsyncSession, stmt) -> int:
    return int((await db.execute(stmt)).scalar_one() or 0)


async def _highlights(db: AsyncSession) -> list:
    """Four at-a-glance counters that matter to a live operator."""
    return [
        {
            "label": "Awaiting KYC review",
            "value": await _scalar(
                db,
                select(func.count())
                .select_from(Merchant)
                .where(Merchant.kyc_status == KycStatus.PENDING.value),
            ),
            "href": "/admin/merchants?q=",
            "tone": "warn",
        },
        {
            "label": "Reels pending moderation",
            "value": await _scalar(
                db,
                select(func.count())
                .select_from(Reel)
                .where(Reel.status == ReelStatus.PENDING_MODERATION.value),
            ),
            "href": "/admin/moderation",
            "tone": "warn",
        },
        {
            "label": "Coupons redeemed",
            "value": await _scalar(
                db,
                select(func.count())
                .select_from(UserCoupon)
                .where(UserCoupon.status == CouponStatus.REDEEMED.value),
            ),
            "href": "/admin/user_coupons",
            "tone": "good",
        },
        {
            "label": "Inbox alerts created",
            "value": await _scalar(db, select(func.count()).select_from(Notification)),
            "href": "/admin/notifications",
            "tone": "neutral",
        },
    ]


@router.get("/")
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    stats = []
    for meta in ALL_MODELS:
        stats.append({"meta": meta, "count": await count_rows(db, meta)})
    total_records = sum(item["count"] for item in stats)
    system_resources = get_system_resources()
    redis_stats = await get_redis_stats()
    db_stats = await get_db_stats(db)

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        panel_context(
            request,
            admin,
            stats=stats,
            highlights=await _highlights(db),
            total_records=total_records,
            auto_approve_reels=await is_auto_approve_enabled(db),
            system=system_resources,
            redis=redis_stats,
            database=db_stats,
        ),
    )


@router.get("/system")
async def system_health(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    system_res = get_system_resources()
    redis_stats = await get_redis_stats()
    db_stats = await get_db_stats(db)
    audit_stats = await get_audit_stats(db, hours=24)
    overall_status = "healthy"
    if db_stats.get("status") != "connected" or redis_stats.get("status") != "connected":
        overall_status = "degraded"

    return templates.TemplateResponse(
        request,
        "system_health.html",
        panel_context(
            request,
            admin,
            system=system_res,
            redis=redis_stats,
            database=db_stats,
            audit_stats=audit_stats,
            overall_status=overall_status,
        ),
    )


@router.post("/system/cache/flush")
async def flush_cache_action(
    request: Request,
    admin: Dict[str, Any] = Depends(current_admin),
):
    try:
        from app.core.redis import get_redis_client
        redis = await get_redis_client()
        keys = []
        async for key in redis.scan_iter(match="*", count=200):
            keys.append(key)
        deleted = 0
        if keys:
            deleted = await redis.delete(*keys)
        audit_log("admin.cache_flush", actor_id=admin.get("sub"), actor_role="SUPER_ADMIN", deleted_keys=deleted)
        return redirect_to(request, f"/admin/system?ok=Flushed+{deleted}+cache+keys+successfully")
    except Exception as exc:
        return redirect_to(request, f"/admin/system?err=Cache+flush+failed:+{str(exc)}")


@router.post("/settings/auto-approve")
async def toggle_auto_approve(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    """Dashboard switch: publish new merchant reels without manual review."""
    form = await request.form()
    enabled = form.get("enabled") == "on"
    await set_setting(db, AUTO_APPROVE_REELS, enabled)
    await db.commit()
    audit_log(
        "system_settings.update",
        actor_id=admin.get("sub"),
        actor_role="SUPER_ADMIN",
        target_type="system_settings",
        target_id=AUTO_APPROVE_REELS,
        value=enabled,
        source="admin_panel",
    )
    return RedirectResponse("/admin/", status_code=303)


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
        select(func.count()).select_from(Reel).where(Reel.status == ReelStatus.PENDING_MODERATION)
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


@router.get("/audit-logs")
async def audit_logs_view(
    request: Request,
    search: str = "",
    method: str = "ALL",
    status: str = "ALL",
    user_role: str = "ALL",
    db_only: str = "0",
    page: int = 1,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    """Production request and database query inspection view."""
    has_db_mutations = db_only in ("1", "true", "True")
    logs, total_count, page_count = await query_audit_logs(
        db,
        method=method,
        status_filter=status,
        user_role=user_role,
        search=search,
        has_db_mutations=has_db_mutations,
        page=page,
        page_size=50,
    )
    stats = await get_audit_stats(db, hours=24)
    user_map = await enrich_logs_with_user_details(db, logs)

    return templates.TemplateResponse(
        request,
        "audit_logs.html",
        panel_context(
            request,
            admin,
            logs=logs,
            stats=stats,
            user_map=user_map,
            total_count=total_count,
            page_count=page_count,
            current_page=page,
            search=search,
            method=method,
            status_filter=status,
            user_role=user_role,
            has_db_mutations=has_db_mutations,
        ),
    )


@router.get("/{model_key}")
async def list_view(
    request: Request,
    model_key: str,
    q: str = "",
    sort: str = "",
    dir: str = "desc",
    page: int = 1,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    meta = meta_or_404(model_key)
    desc = str(dir).lower() != "asc"
    rows, total, page_count, current_page = await query_page(
        db, meta, q, sort, desc, page, meta.page_size
    )
    context = panel_context(
        request,
        admin,
        meta=meta,
        rows=[serialize_row(meta, row) for row in rows],
        total=total,
        page=current_page,
        page_count=page_count,
        q=q,
        sort=sort or meta.sort_column,
        dir="desc" if desc else "asc",
    )
    template = "partials/table.html" if request.headers.get("HX-Request") else "list.html"
    return templates.TemplateResponse(request, template, context)


@router.get("/{model_key}/new")
async def create_form(
    request: Request,
    model_key: str,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    meta = meta_or_404(model_key)
    return templates.TemplateResponse(
        request,
        "form.html",
        panel_context(
            request,
            admin,
            meta=meta,
            fields=await form_fields(db, meta),
            row_pk=None,
            errors=[],
        ),
    )


@router.get("/{model_key}/{pk}")
async def detail_view(
    request: Request,
    model_key: str,
    pk: str,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    meta = meta_or_404(model_key)
    row = await get_row(db, meta, pk)
    return templates.TemplateResponse(
        request,
        "detail.html",
        panel_context(
            request,
            admin,
            meta=meta,
            row_pk=pk,
            title=str(getattr(row, meta.label_column, None) or pk) if meta.label_column else pk,
            fields=serialize_detail(meta, row),
        ),
    )
