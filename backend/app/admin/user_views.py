"""Admin panel views and actions for platform user management and access control."""
import logging
import math
import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.deps import current_admin
from app.admin.helpers import panel_context, record_audit_log
from app.admin.templating import templates
from app.core.database import get_db
from app.models import User, UserRole

logger = logging.getLogger("fyndo.admin.users")
router = APIRouter()

PAGE_SIZE = 50


async def _get_user_or_404(user_id: str, db: AsyncSession) -> User:
    try:
        uid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid user UUID.")
    user = (await db.execute(select(User).where(User.id == uid))).scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@router.get("/users")
async def user_list_view(
    request: Request,
    role: str = "ALL",
    q: str = "",
    page: int = 1,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    """Lists registered platform users with search, role filtering, and ban actions."""
    page = max(1, page)
    stmt = select(User)

    role_filter = role.upper().strip()
    if role_filter != "ALL":
        try:
            enum_role = UserRole(role_filter)
            stmt = stmt.where(User.role == enum_role)
        except ValueError:
            role_filter = "ALL"

    query_str = q.strip()
    if query_str:
        pattern = f"%{query_str}%"
        stmt = stmt.where(
            or_(
                User.phone.ilike(pattern),
                User.full_name.ilike(pattern),
            )
        )

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_users = (await db.execute(count_stmt)).scalar_one() or 0
    total_pages = max(1, math.ceil(total_users / PAGE_SIZE))

    # Paginate
    stmt = stmt.order_by(User.created_at.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    users = (await db.execute(stmt)).scalars().all()

    template = "partials/user_table.html" if request.headers.get("HX-Request") else "users_list.html"
    return templates.TemplateResponse(
        request,
        template,
        panel_context(
            request,
            admin,
            users=users,
            total_users=total_users,
            total_pages=total_pages,
            current_page=page,
            role_filter=role_filter,
            search_query=query_str,
        ),
    )


@router.post("/users/{user_id}/ban")
async def ban_user_action(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    """Bans a user by setting is_active = False."""
    user = await _get_user_or_404(user_id, db)
    user.is_active = False
    await db.flush()

    await record_audit_log(
        db,
        admin_user=admin.get("sub"),
        action="user.ban",
        target_type="user",
        target_id=user.id,
        details={"phone": user.phone, "role": user.role.value if hasattr(user.role, "value") else str(user.role)},
    )
    await db.commit()
    return RedirectResponse(url=f"/admin/users?ok=User+{user.phone}+has+been+banned", status_code=303)


@router.post("/users/{user_id}/unban")
async def unban_user_action(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    """Unbans a user by setting is_active = True."""
    user = await _get_user_or_404(user_id, db)
    user.is_active = True
    await db.flush()

    await record_audit_log(
        db,
        admin_user=admin.get("sub"),
        action="user.unban",
        target_type="user",
        target_id=user.id,
        details={"phone": user.phone, "role": user.role.value if hasattr(user.role, "value") else str(user.role)},
    )
    await db.commit()
    return RedirectResponse(url=f"/admin/users?ok=User+{user.phone}+has+been+restored", status_code=303)
