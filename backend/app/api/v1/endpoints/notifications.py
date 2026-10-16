"""Notification inbox endpoints: list, unread count, mark-read and device tokens."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.core.audit import audit_log
from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.notification import (
    DeviceTokenRegisterRequest,
    DeviceTokenResponse,
    DeviceTokenUnregisterRequest,
    NotificationOut,
    NotificationPage,
    UnreadCountResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter()


def _role(role: object) -> str:
    return str(getattr(role, "value", role))


@router.get("/notifications", response_model=ResponseEnvelope[NotificationPage])
async def list_notifications(
    category: Optional[str] = Query(None, description="ALL | DEALS | UPDATES | RADAR | SYSTEM"),
    unread_only: bool = Query(False),
    limit: int = Query(30, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _=Depends(rate_limit("notifications_read", 240)),
):
    """Paginated inbox for the signed-in user, newest first."""
    items, unread, next_cursor, has_more = await NotificationService.list_for_user(
        db,
        current_user.id,
        category=category,
        unread_only=unread_only,
        limit=limit,
        cursor=cursor,
    )
    page = NotificationPage(
        items=[NotificationOut.model_validate(item) for item in items],
        unread_count=unread,
        next_cursor=next_cursor,
        has_more=has_more,
    )
    return ResponseEnvelope(data=page)


@router.get(
    "/notifications/unread-count", response_model=ResponseEnvelope[UnreadCountResponse]
)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _=Depends(rate_limit("notifications_read", 240)),
):
    """Lightweight badge counter for the tab bar."""
    count = await NotificationService.unread_count(db, current_user.id)
    return ResponseEnvelope(data=UnreadCountResponse(unread_count=count))


@router.post("/notifications/read-all", response_model=ResponseEnvelope[dict])
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _=Depends(rate_limit("notifications_write", 120)),
):
    """Marks every unread alert as read for the signed-in user."""
    updated = await NotificationService.mark_all_read(db, current_user.id)
    audit_log(
        "notification.read_all",
        actor_id=current_user.id,
        actor_role=_role(current_user.role),
        target_type="user",
        target_id=current_user.id,
        updated=updated,
    )
    return ResponseEnvelope(data={"updated": updated}, message="All alerts marked as read.")


@router.post("/notifications/{notification_id}/read", response_model=ResponseEnvelope[dict])
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _=Depends(rate_limit("notifications_write", 120)),
):
    """Marks a single alert as read (idempotent)."""
    outcome = await NotificationService.mark_read(
        db, user_id=current_user.id, notification_id=notification_id
    )
    if outcome is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
    audit_log(
        "notification.read",
        actor_id=current_user.id,
        actor_role=_role(current_user.role),
        target_type="notification",
        target_id=notification_id,
        newly_read=outcome,
    )
    return ResponseEnvelope(
        data={"notification_id": str(notification_id), "is_read": True},
        message="Alert marked as read.",
    )


@router.post(
    "/notifications/device-token",
    response_model=ResponseEnvelope[DeviceTokenResponse],
    status_code=status.HTTP_201_CREATED,
)
async def register_device_token(
    payload: DeviceTokenRegisterRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _=Depends(rate_limit("notifications_write", 120)),
):
    """Registers (or re-activates) a push token for the signed-in device."""
    device = await NotificationService.register_device(
        db, user_id=current_user.id, token=payload.token, platform=payload.platform
    )
    audit_log(
        "notification.device_registered",
        actor_id=current_user.id,
        actor_role=_role(current_user.role),
        target_type="device_token",
        target_id=device.id,
        platform=device.platform,
    )
    return ResponseEnvelope(
        data=DeviceTokenResponse(
            id=device.id, platform=device.platform, is_active=device.is_active
        ),
        message="Device registered for alerts.",
    )


@router.post("/notifications/device-token/unregister", response_model=ResponseEnvelope[dict])
async def unregister_device_token(
    payload: DeviceTokenUnregisterRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _=Depends(rate_limit("notifications_write", 120)),
):
    """Deactivates a push token, e.g. on sign-out."""
    removed = await NotificationService.unregister_device(
        db, user_id=current_user.id, token=payload.token
    )
    audit_log(
        "notification.device_unregistered",
        actor_id=current_user.id,
        actor_role=_role(current_user.role),
        target_type="device_token",
        removed=removed,
    )
    return ResponseEnvelope(
        data={"removed": removed}, message="Device unregistered from alerts."
    )
