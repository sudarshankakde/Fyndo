"""Admin panel views for platform analytics and metrics visualization."""
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.deps import current_admin
from app.admin.helpers import panel_context
from app.admin.templating import templates
from app.core.database import get_db
from app.models import KycStatus, Merchant, Reel, ReelStatus, SubscriptionStatus

logger = logging.getLogger("fyndo.admin.analytics")
router = APIRouter()


@router.get("/analytics")
async def analytics_view(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    """Platform analytics: signups timeline, conversion rates, and moderation efficiency."""
    now = datetime.now(timezone.utc)
    since_30d = now - timedelta(days=29)

    # 1. 30-day merchant signups distribution
    day_counts: Dict[str, int] = {}
    for i in range(29, -1, -1):
        day_key = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        day_counts[day_key] = 0

    stmt = (
        select(func.date(Merchant.created_at).label("day"), func.count(Merchant.id).label("count"))
        .where(Merchant.created_at >= since_30d)
        .group_by(func.date(Merchant.created_at))
        .order_by("day")
    )
    rows = (await db.execute(stmt)).all()
    for row in rows:
        day_str = str(row.day)
        if day_str in day_counts:
            day_counts[day_str] = int(row.count)

    chart_labels = list(day_counts.keys())
    chart_values = list(day_counts.values())

    # 2. Total merchants and KYC approval rate
    total_merchants = (await db.execute(select(func.count(Merchant.id)))).scalar_one() or 0
    approved_kyc = (
        await db.execute(select(func.count(Merchant.id)).where(Merchant.kyc_status == KycStatus.APPROVED))
    ).scalar_one() or 0
    pending_kyc = (
        await db.execute(select(func.count(Merchant.id)).where(Merchant.kyc_status == KycStatus.PENDING))
    ).scalar_one() or 0
    kyc_rate = round((approved_kyc / total_merchants * 100), 1) if total_merchants > 0 else 0.0

    # 3. Reel acceptance rate
    total_reels = (await db.execute(select(func.count(Reel.id)))).scalar_one() or 0
    approved_reels = (
        await db.execute(select(func.count(Reel.id)).where(Reel.status == ReelStatus.APPROVED))
    ).scalar_one() or 0
    decided_reels = (
        await db.execute(
            select(func.count(Reel.id)).where(Reel.status.in_([ReelStatus.APPROVED, ReelStatus.REJECTED]))
        )
    ).scalar_one() or 0
    reel_rate = round((approved_reels / decided_reels * 100), 1) if decided_reels > 0 else 0.0

    # 4. Active subscription rate
    active_subscriptions = (
        await db.execute(
            select(func.count(Merchant.id)).where(
                Merchant.subscription_status == SubscriptionStatus.ACTIVE,
                or_(
                    Merchant.subscription_expires_at.is_(None),
                    Merchant.subscription_expires_at > now,
                ),
            )
        )
    ).scalar_one() or 0
    subscription_rate = round((active_subscriptions / total_merchants * 100), 1) if total_merchants > 0 else 0.0

    return templates.TemplateResponse(
        request,
        "analytics.html",
        panel_context(
            request,
            admin,
            chart_labels=json.dumps(chart_labels),
            chart_values=json.dumps(chart_values),
            total_merchants=total_merchants,
            approved_kyc=approved_kyc,
            pending_kyc=pending_kyc,
            kyc_rate=kyc_rate,
            total_reels=total_reels,
            approved_reels=approved_reels,
            reel_rate=reel_rate,
            active_subscriptions=active_subscriptions,
            subscription_rate=subscription_rate,
        ),
    )
