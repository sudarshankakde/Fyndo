"""Admin panel views and actions for platform-wide subscription management."""
import csv
import io
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.admin.deps import current_admin
from app.admin.helpers import panel_context, record_audit_log
from app.admin.templating import templates
from app.core.database import get_db
from app.models import Merchant, SubscriptionStatus

logger = logging.getLogger("fyndo.admin.subscriptions")
router = APIRouter()


@router.get("/subscriptions")
async def subscription_management_view(
    request: Request,
    filter: str = "ALL",
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    """Platform-wide subscription health, merchant statuses, and bulk operations."""
    now = datetime.now(timezone.utc)
    soon = now + timedelta(days=7)

    # Calculate summary KPIs
    all_merchants = (
        await db.execute(select(Merchant).options(selectinload(Merchant.owner)).order_by(Merchant.created_at.desc()))
    ).scalars().all()

    total_active = 0
    total_expired = 0
    total_expiring_soon = 0
    total_inactive = 0

    for m in all_merchants:
        exp = m.subscription_expires_at
        if exp and exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)

        if m.subscription_status == SubscriptionStatus.INACTIVE:
            total_inactive += 1
        elif m.subscription_status == SubscriptionStatus.EXPIRED or (exp and exp <= now):
            total_expired += 1
        elif m.subscription_status == SubscriptionStatus.ACTIVE:
            total_active += 1
            if exp and now < exp <= soon:
                total_expiring_soon += 1

    filter_norm = filter.upper().strip()
    filtered_merchants = []
    for m in all_merchants:
        exp = m.subscription_expires_at
        if exp and exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)

        is_exp = m.subscription_status == SubscriptionStatus.EXPIRED or (exp and exp <= now)
        is_act = m.subscription_status == SubscriptionStatus.ACTIVE and not is_exp
        is_inact = m.subscription_status == SubscriptionStatus.INACTIVE
        is_soon = is_act and (exp and now < exp <= soon)

        if filter_norm == "ACTIVE" and is_act:
            filtered_merchants.append(m)
        elif filter_norm == "EXPIRED" and is_exp:
            filtered_merchants.append(m)
        elif filter_norm == "EXPIRING_SOON" and is_soon:
            filtered_merchants.append(m)
        elif filter_norm == "INACTIVE" and is_inact:
            filtered_merchants.append(m)
        elif filter_norm not in ("ACTIVE", "EXPIRED", "EXPIRING_SOON", "INACTIVE"):
            filtered_merchants.append(m)

    return templates.TemplateResponse(
        request,
        "subscriptions.html",
        panel_context(
            request,
            admin,
            merchants=filtered_merchants,
            current_filter=filter_norm,
            total_active=total_active,
            total_expired=total_expired,
            total_expiring_soon=total_expiring_soon,
            total_inactive=total_inactive,
            now=now,
        ),
    )


@router.post("/subscriptions/bulk-extend")
async def bulk_extend_subscriptions_action(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    """Bulk extends all expired subscriptions by N days."""
    form = await request.form()
    duration_raw = form.get("duration_days")
    try:
        duration_days = max(1, min(3650, int(duration_raw))) if duration_raw else 90
    except (ValueError, TypeError):
        duration_days = 90

    now = datetime.now(timezone.utc)
    stmt = select(Merchant).where(
        or_(
            Merchant.subscription_status == SubscriptionStatus.EXPIRED,
            Merchant.subscription_expires_at <= now,
        )
    )
    merchants = (await db.execute(stmt)).scalars().all()
    count = 0
    for m in merchants:
        m.subscription_status = SubscriptionStatus.ACTIVE
        m.subscription_expires_at = now + timedelta(days=duration_days)
        if m.subscription_start_date is None:
            m.subscription_start_date = now
        count += 1

    await db.flush()
    await record_audit_log(
        db,
        admin_user=admin.get("sub"),
        action="merchant.bulk_subscription_extend",
        target_type="merchant",
        details={"extended_count": count, "duration_days": duration_days},
    )
    await db.commit()
    return RedirectResponse(
        url=f"/admin/subscriptions?ok=Successfully+extended+{count}+expired+merchants+by+{duration_days}+days",
        status_code=303,
    )


@router.get("/subscriptions/export-csv")
async def export_subscriptions_csv(
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    """Exports all merchant subscription records as a downloadable CSV."""
    merchants = (
        await db.execute(select(Merchant).options(selectinload(Merchant.owner)).order_by(Merchant.created_at.desc()))
    ).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Merchant ID",
        "Business Name",
        "Owner Name",
        "Phone",
        "City",
        "Sector",
        "Subscription Status",
        "Effective Status",
        "Start Date",
        "Expires At",
        "Joined Date",
    ])

    for m in merchants:
        writer.writerow([
            str(m.id),
            m.business_name,
            m.owner.full_name if m.owner else "",
            m.phone or (m.owner.phone if m.owner else ""),
            m.city or "",
            m.sector.value if m.sector and hasattr(m.sector, "value") else (m.sector or ""),
            m.subscription_status.value if hasattr(m.subscription_status, "value") else str(m.subscription_status),
            m.effective_subscription_status,
            m.subscription_start_date.isoformat() if m.subscription_start_date else "",
            m.subscription_expires_at.isoformat() if m.subscription_expires_at else "",
            m.created_at.isoformat() if m.created_at else "",
        ])

    csv_data = output.getvalue()
    filename = f"fyndo_subscriptions_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
