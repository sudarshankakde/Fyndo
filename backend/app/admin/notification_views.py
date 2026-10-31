"""Admin views for platform-wide push notification broadcasting and dispatch."""
import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.deps import current_admin
from app.admin.helpers import panel_context, record_audit_log, redirect_to
from app.admin.templating import templates
from app.core.database import get_db
from app.models.notification import DevicePlatform, DeviceToken, Notification, NotificationCategory
from app.models.user import User, UserRole
from app.services.notification_service import NotificationService
from app.services.push_service import PushService

logger = logging.getLogger("fyndo.admin.notifications")
router = APIRouter()


@router.get("/broadcast")
@router.get("/notifications-broadcast")
async def broadcast_notifications_view(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    """Notification broadcast dashboard with device stats, recent alerts, and composer."""
    total_notifications = (
        await db.execute(select(func.count()).select_from(Notification))
    ).scalar_one() or 0

    push_sent_count = (
        await db.execute(
            select(func.count()).select_from(Notification).where(Notification.push_sent.is_(True))
        )
    ).scalar_one() or 0

    total_devices = (
        await db.execute(
            select(func.count()).select_from(DeviceToken).where(DeviceToken.is_active.is_(True))
        )
    ).scalar_one() or 0

    android_devices = (
        await db.execute(
            select(func.count())
            .select_from(DeviceToken)
            .where(
                DeviceToken.platform == DevicePlatform.ANDROID,
                DeviceToken.is_active.is_(True),
            )
        )
    ).scalar_one() or 0

    ios_devices = (
        await db.execute(
            select(func.count())
            .select_from(DeviceToken)
            .where(
                DeviceToken.platform == DevicePlatform.IOS,
                DeviceToken.is_active.is_(True),
            )
        )
    ).scalar_one() or 0

    merchants_count = (
        await db.execute(
            select(func.count())
            .select_from(User)
            .where(User.role == UserRole.MERCHANT, User.is_active.is_(True))
        )
    ).scalar_one() or 0

    shoppers_count = (
        await db.execute(
            select(func.count())
            .select_from(User)
            .where(User.role == UserRole.SHOPPER, User.is_active.is_(True))
        )
    ).scalar_one() or 0

    # Recent 15 broadcast/system alerts
    recent_notifications = (
        await db.execute(
            select(Notification)
            .order_by(Notification.created_at.desc())
            .limit(15)
        )
    ).scalars().all()

    categories = [c.value for c in NotificationCategory]
    push_service_enabled = PushService.is_enabled()

    return templates.TemplateResponse(
        request,
        "broadcast_notifications.html",
        panel_context(
            request,
            admin,
            total_notifications=total_notifications,
            push_sent_count=push_sent_count,
            total_devices=total_devices,
            android_devices=android_devices,
            ios_devices=ios_devices,
            merchants_count=merchants_count,
            shoppers_count=shoppers_count,
            recent_notifications=recent_notifications,
            categories=categories,
            push_service_enabled=push_service_enabled,
        ),
    )


@router.post("/broadcast/send")
async def send_broadcast_notification(
    request: Request,
    audience: str = Form(""),
    target_user: Optional[str] = Form(None),
    title: str = Form(""),
    body: str = Form(""),
    category: str = Form(NotificationCategory.UPDATES.value),
    send_push: bool = Form(True),
    image_url: Optional[str] = Form(None),
    action_type: Optional[str] = Form(None),
    action_ref: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    """Dispatches in-app and push notification to target audience or specific user."""
    clean_title = title.strip()
    clean_body = body.strip()

    if not clean_title or not clean_body:
        return redirect_to(request, "/admin/broadcast?err=Title+and+body+cannot+be+empty")

    user_ids: List[uuid.UUID] = []

    if audience == "MERCHANT":
        stmt = select(User.id).where(User.role == UserRole.MERCHANT, User.is_active.is_(True))
        user_ids = list((await db.execute(stmt)).scalars().all())
    elif audience == "SHOPPER":
        stmt = select(User.id).where(User.role == UserRole.SHOPPER, User.is_active.is_(True))
        user_ids = list((await db.execute(stmt)).scalars().all())
    elif audience == "ALL":
        stmt = select(User.id).where(User.is_active.is_(True))
        user_ids = list((await db.execute(stmt)).scalars().all())
    elif audience == "USER":
        identifier = (target_user or "").strip()
        if not identifier:
            return redirect_to(request, "/admin/broadcast?err=Please+specify+a+user+phone+or+UUID")

        # Try match by UUID or phone
        target_uid = None
        try:
            parsed_id = uuid.UUID(identifier)
            target_user_row = (await db.execute(select(User).where(User.id == parsed_id))).scalars().first()
            if target_user_row:
                target_uid = target_user_row.id
        except ValueError:
            phone_cand = identifier if identifier.startswith("+") else f"+91{identifier}"
            target_user_row = (
                await db.execute(select(User).where(User.phone == phone_cand))
            ).scalars().first()
            if target_user_row:
                target_uid = target_user_row.id

        if not target_uid:
            return redirect_to(
                request,
                f"/admin/broadcast?err=User+not+found+with+identifier+{identifier}"
            )
        user_ids = [target_uid]
    else:
        return redirect_to(request, "/admin/broadcast?err=Invalid+audience+selected")

    if not user_ids:
        return redirect_to(
            request,
            "/admin/broadcast?err=No+active+users+found+for+the+selected+audience"
        )

    # Dispatch via NotificationService
    dispatched_count = await NotificationService.notify_many(
        db,
        user_ids=user_ids,
        event_type="admin.broadcast",
        title=clean_title,
        body=clean_body,
        category=category,
        image_url=image_url.strip() if image_url and image_url.strip() else None,
        action_type=action_type.strip() if action_type and action_type.strip() else None,
        action_ref=action_ref.strip() if action_ref and action_ref.strip() else None,
        push=send_push,
    )
    await db.commit()

    # Record operational audit trail
    await record_audit_log(
        db,
        admin_user=admin.get("sub"),
        action="notification.broadcast",
        target_type="audience",
        target_id=audience,
        details={
            "title": clean_title,
            "audience": audience,
            "recipients_count": dispatched_count,
            "category": category,
            "send_push": send_push,
        },
        outcome="success",
    )
    await db.commit()

    return redirect_to(
        request,
        f"/admin/broadcast?ok=Successfully+dispatched+broadcast+to+{dispatched_count}+recipient(s)"
    )
