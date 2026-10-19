"""Dashboard, list and detail views for the HTML super-admin panel."""
import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.deps import current_admin
from app.admin.helpers import form_fields, get_row, meta_or_404, panel_context
from app.admin.registry import ALL_MODELS
from app.admin.templating import templates
from app.admin.utils import count_rows, query_page, serialize_detail, serialize_row
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
            "href": "/admin/reels",
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
        ),
    )


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
