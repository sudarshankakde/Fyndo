"""Notification service.

Owns the in-app inbox (create, paginate, mark-read) and fans each new
notification out to the recipient's registered devices through
:class:`PushService`. Every create is audit-logged so the alert history is
traceable.
"""
import asyncio
import base64
import binascii
import logging
import uuid
from datetime import datetime, timezone
from typing import Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.notification import (
    DevicePlatform,
    DeviceToken,
    Notification,
    NotificationCategory,
)

from app.services.push_service import PushService

logger = logging.getLogger("fyndo.notifications")

MAX_PAGE_SIZE = 100


class NotificationService:
    # ------------------------------------------------------------------ create
    @classmethod
    async def create(
        cls,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        event_type: str,
        title: str,
        body: str,
        category: str = NotificationCategory.UPDATES.value,
        image_url: Optional[str] = None,
        action_type: Optional[str] = None,
        action_ref: Optional[str] = None,
        payload: Optional[dict] = None,
        push: bool = True,
    ) -> Notification:
        """Persists one in-app notification and (optionally) queues a push."""
        notification = Notification(
            user_id=user_id,
            category=category,
            event_type=event_type,
            title=title,
            body=body,
            image_url=image_url,
            action_type=action_type,
            action_ref=action_ref,
            payload=payload,
        )
        db.add(notification)
        await db.flush()

        if push:
            notification.push_sent = await cls._dispatch_push(
                db,
                user_id=user_id,
                title=title,
                body=body,
                data={
                    "event_type": event_type,
                    "action_type": action_type,
                    "action_ref": action_ref,
                },
            )

        logger.info(
            "Notification created for user %s (%s).",
            user_id,
            event_type,
            extra={
                "event": "notification_created",
                "event_type": event_type,
                "notification_id": str(notification.id),
                "recipient_id": str(user_id),
            },
        )
        return notification

    @classmethod
    async def notify_many(
        cls, db: AsyncSession, *, user_ids: Iterable[uuid.UUID], **kwargs
    ) -> int:
        """Creates the same notification for several recipients (deduplicated)."""
        created = 0
        for user_id in dict.fromkeys(user_ids):
            if not user_id:
                continue
            await cls.create(db, user_id=user_id, **kwargs)
            created += 1
        return created

    @classmethod
    async def notify_safe(cls, db: AsyncSession, **kwargs) -> Optional[Notification]:
        """Best-effort alert: never raises, so the calling mutation still succeeds."""
        try:
            return await cls.create(db, **kwargs)
        except Exception:
            logger.warning(
                "Notification dispatch failed for event %s.", kwargs.get("event_type"),
                exc_info=True,
            )
            return None

    # -------------------------------------------------------------------- read
    @classmethod
    async def list_for_user(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        *,
        category: Optional[str] = None,
        unread_only: bool = False,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> Tuple[List[Notification], int, Optional[str], bool]:
        """Returns (items, unread_count, next_cursor, has_more) using keyset paging."""
        size = max(1, min(limit or settings.NOTIFICATION_PAGE_SIZE, MAX_PAGE_SIZE))
        filters = [Notification.user_id == user_id]
        if category and category.upper() != "ALL":
            filters.append(Notification.category == category.upper())
        if unread_only:
            filters.append(Notification.is_read.is_(False))
        if cursor:
            decoded = cls._decode_cursor(cursor)
            if decoded:
                created_at, last_id = decoded
                filters.append(
                    or_(
                        Notification.created_at < created_at,
                        and_(
                            Notification.created_at == created_at,
                            Notification.id < last_id,
                        ),
                    )
                )

        stmt = (
            select(Notification)
            .where(*filters)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .limit(size + 1)
        )
        rows = list((await db.execute(stmt)).scalars().all())
        has_more = len(rows) > size
        items = rows[:size]
        next_cursor = cls._encode_cursor(items[-1]) if has_more and items else None
        return items, await cls.unread_count(db, user_id), next_cursor, has_more

    @staticmethod
    async def unread_count(db: AsyncSession, user_id: uuid.UUID) -> int:
        result = await db.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id, Notification.is_read.is_(False)
            )
        )
        return int(result.scalar() or 0)

    @classmethod
    async def mark_read(
        cls, db: AsyncSession, *, user_id: uuid.UUID, notification_id: uuid.UUID
    ) -> Optional[bool]:
        """True when newly marked, False when already read, None when not found."""
        result = await db.execute(
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True, read_at=datetime.now(timezone.utc))
            .execution_options(synchronize_session=False)
        )
        if result.rowcount == 1:
            return True
        existing = await db.execute(
            select(Notification.is_read).where(
                Notification.id == notification_id, Notification.user_id == user_id
            )
        )
        return None if existing.first() is None else False

    @classmethod
    async def mark_all_read(cls, db: AsyncSession, user_id: uuid.UUID) -> int:
        result = await db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True, read_at=datetime.now(timezone.utc))
            .execution_options(synchronize_session=False)
        )
        return int(result.rowcount or 0)

    # ---------------------------------------------------------------- devices
    @classmethod
    async def register_device(
        cls, db: AsyncSession, *, user_id: uuid.UUID, token: str, platform: str
    ) -> DeviceToken:
        normalised = (platform or DevicePlatform.ANDROID.value).upper()
        if normalised not in {item.value for item in DevicePlatform}:
            normalised = DevicePlatform.ANDROID.value

        existing = (
            await db.execute(select(DeviceToken).where(DeviceToken.token == token))
        ).scalars().first()
        if existing:
            existing.user_id = user_id
            existing.platform = normalised
            existing.is_active = True
            await db.flush()
            return existing

        device = DeviceToken(
            user_id=user_id, token=token, platform=normalised, is_active=True
        )
        db.add(device)
        await db.flush()
        return device

    @staticmethod
    async def unregister_device(
        db: AsyncSession, *, user_id: uuid.UUID, token: str
    ) -> bool:
        """True only when an active token was actually deactivated."""
        result = await db.execute(
            update(DeviceToken)
            .where(
                DeviceToken.token == token,
                DeviceToken.user_id == user_id,
                DeviceToken.is_active.is_(True),
            )
            .values(is_active=False)
            .execution_options(synchronize_session=False)
        )
        return bool(result.rowcount)

    # ---------------------------------------------------------------- internal
    @staticmethod
    async def _active_tokens(db: AsyncSession, user_id: uuid.UUID) -> List[str]:
        result = await db.execute(
            select(DeviceToken.token).where(
                DeviceToken.user_id == user_id, DeviceToken.is_active.is_(True)
            )
        )
        return list(result.scalars().all())

    @classmethod
    async def _dispatch_push(
        cls,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        title: str,
        body: str,
        data: Optional[dict],
    ) -> bool:
        """Queues a background push so the API response is never blocked by FCM."""
        if not settings.PUSH_ENABLED:
            return False
        tokens = await cls._active_tokens(db, user_id)
        if not tokens:
            return False
        try:
            asyncio.create_task(PushService.send(tokens, title=title, body=body, data=data))
        except RuntimeError:
            logger.debug("No running event loop; skipping push dispatch.")
            return False
        return True

    @staticmethod
    def _encode_cursor(notification: Notification) -> str:
        raw = f"{notification.created_at.isoformat()}|{notification.id}"
        return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")

    @staticmethod
    def _decode_cursor(cursor: str) -> Optional[Tuple[datetime, uuid.UUID]]:
        try:
            raw = base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8")
            created_raw, _, id_raw = raw.partition("|")
            return datetime.fromisoformat(created_raw), uuid.UUID(id_raw)
        except (ValueError, TypeError, binascii.Error, UnicodeDecodeError):
            return None
