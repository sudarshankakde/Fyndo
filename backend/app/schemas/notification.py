"""Pydantic schemas for the notification inbox and push device registration."""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    event_type: str
    title: str
    body: str
    image_url: Optional[str] = None
    action_type: Optional[str] = None
    action_ref: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    is_read: bool
    created_at: datetime
    expires_at: Optional[datetime] = None


class NotificationPage(BaseModel):
    """Envelope payload for the paginated inbox list."""

    items: List[NotificationOut]
    unread_count: int
    next_cursor: Optional[str] = None
    has_more: bool = False


class UnreadCountResponse(BaseModel):
    unread_count: int


class DeviceTokenRegisterRequest(BaseModel):
    token: str = Field(min_length=8, max_length=255)
    platform: str = Field(default="ANDROID")


class DeviceTokenResponse(BaseModel):
    id: uuid.UUID
    platform: str
    is_active: bool


class DeviceTokenUnregisterRequest(BaseModel):
    token: str = Field(min_length=8, max_length=255)


class NotificationCreateRequest(BaseModel):
    """Internal/admin broadcast payload."""

    user_id: uuid.UUID
    title: str = Field(min_length=1, max_length=140)
    body: str = Field(min_length=1, max_length=1000)
    category: str = Field(default="UPDATES")
    action_type: Optional[str] = None
    action_ref: Optional[str] = None
