"""Admin panel views for viewing and filtering system operational audit logs."""
import logging
import math
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.deps import current_admin
from app.admin.helpers import panel_context
from app.admin.templating import templates
from app.core.database import get_db
from app.models.audit_log import AuditLog

logger = logging.getLogger("fyndo.admin.audit")
router = APIRouter()

PAGE_SIZE = 50


@router.get("/audit")
@router.get("/audit-logs")
async def audit_logs_view(
    request: Request,
    action: str = "ALL",
    admin_user: str = "ALL",
    q: str = "",
    page: int = 1,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    """Super admin audit log viewer with action and actor filtering."""
    page = max(1, page)
    stmt = select(AuditLog)

    action_filter = action.strip()
    if action_filter and action_filter != "ALL":
        stmt = stmt.where(AuditLog.action == action_filter)

    actor_filter = admin_user.strip()
    if actor_filter and actor_filter != "ALL":
        stmt = stmt.where(AuditLog.admin_user == actor_filter)

    query_str = q.strip()
    if query_str:
        pattern = f"%{query_str}%"
        stmt = stmt.where(
            or_(
                AuditLog.action.ilike(pattern),
                AuditLog.target_type.ilike(pattern),
                AuditLog.target_id.ilike(pattern),
                AuditLog.admin_user.ilike(pattern),
            )
        )

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_logs = (await db.execute(count_stmt)).scalar_one() or 0
    total_pages = max(1, math.ceil(total_logs / PAGE_SIZE))

    # Paginate
    stmt = stmt.order_by(AuditLog.timestamp.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    logs = (await db.execute(stmt)).scalars().all()

    # Distinct actions for filter dropdown
    distinct_actions = (
        await db.execute(select(AuditLog.action).distinct().order_by(AuditLog.action))
    ).scalars().all()

    # Distinct actors for filter dropdown
    distinct_actors = (
        await db.execute(
            select(AuditLog.admin_user)
            .where(AuditLog.admin_user.is_not(None))
            .distinct()
            .order_by(AuditLog.admin_user)
        )
    ).scalars().all()

    return templates.TemplateResponse(
        request,
        "audit.html",
        panel_context(
            request,
            admin,
            logs=logs,
            total_logs=total_logs,
            total_pages=total_pages,
            current_page=page,
            action_filter=action_filter,
            actor_filter=actor_filter,
            search_query=query_str,
            distinct_actions=distinct_actions,
            distinct_actors=distinct_actors,
        ),
    )
