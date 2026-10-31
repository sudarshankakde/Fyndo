import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

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
    SubscriptionStatus,
    UserCoupon,
)
from app.models.audit_log import AuditLog
from app.services.audit_service import get_audit_stats
from app.services.settings_service import (
    get_auto_trial_duration_days,
    is_auto_approve_enabled,
    is_auto_approve_kyc_enabled,
    is_auto_trial_enabled,
)

logger = logging.getLogger("fyndo.admin")
router = APIRouter()


async def _scalar(db: AsyncSession, stmt) -> int:
    return int((await db.execute(stmt)).scalar_one() or 0)


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
    now = datetime.now(timezone.utc)

    # Subscription summary cards
    active_sub_count = await _scalar(
        db,
        select(func.count(Merchant.id)).where(
            Merchant.subscription_status == SubscriptionStatus.ACTIVE,
            or_(Merchant.subscription_expires_at.is_(None), Merchant.subscription_expires_at > now),
        ),
    )
    expired_sub_count = await _scalar(
        db,
        select(func.count(Merchant.id)).where(
            or_(
                Merchant.subscription_status == SubscriptionStatus.EXPIRED,
                Merchant.subscription_expires_at <= now,
            )
        ),
    )
    inactive_sub_count = await _scalar(
        db,
        select(func.count(Merchant.id)).where(
            Merchant.subscription_status == SubscriptionStatus.INACTIVE
        ),
    )
    trial_sub_count = await _scalar(
        db,
        select(func.count(Merchant.id)).where(
            Merchant.subscription_status == SubscriptionStatus.ACTIVE
        ),
    )

    # Action queues
    kyc_queue_count = await _scalar(
        db,
        select(func.count(Merchant.id)).where(Merchant.kyc_status == KycStatus.PENDING),
    )
    pending_reels_count = await _scalar(
        db,
        select(func.count(Reel.id)).where(Reel.status == ReelStatus.PENDING_MODERATION),
    )

    # Recent 10 audit logs
    recent_audits = (
        await db.execute(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(10))
    ).scalars().all()

    system_resources = get_system_resources()
    redis_stats = await get_redis_stats()
    db_stats = await get_db_stats(db)

    highlights = [
        {"label": "Awaiting KYC review", "value": kyc_queue_count, "href": "/admin/kyc", "tone": "warn"},
        {"label": "Reels pending moderation", "value": pending_reels_count, "href": "/admin/moderation", "tone": "warn"},
        {"label": "Coupons redeemed", "value": await _scalar(db, select(func.count()).select_from(UserCoupon).where(UserCoupon.status == CouponStatus.REDEEMED)), "href": "/admin/user_coupons", "tone": "good"},
        {"label": "Inbox alerts created", "value": await _scalar(db, select(func.count()).select_from(Notification)), "href": "/admin/notifications", "tone": "neutral"},
    ]

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        panel_context(
            request,
            admin,
            stats=stats,
            highlights=highlights,
            total_records=total_records,
            active_sub_count=active_sub_count,
            expired_sub_count=expired_sub_count,
            inactive_sub_count=inactive_sub_count,
            trial_sub_count=trial_sub_count,
            kyc_queue_count=kyc_queue_count,
            pending_reels_count=pending_reels_count,
            recent_audits=recent_audits,
            auto_approve_reels=await is_auto_approve_enabled(db),
            auto_approve_kyc=await is_auto_approve_kyc_enabled(db),
            auto_trial_enabled=await is_auto_trial_enabled(db),
            auto_trial_duration_days=await get_auto_trial_duration_days(db),
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
            row=row,
            title=str(getattr(row, meta.label_column, None) or pk) if meta.label_column else pk,
            fields=serialize_detail(meta, row),
        ),
    )
