"""Push notification dispatch.

Delivers notifications through the Expo Push Service, which fronts both FCM
(Android) and APNs (iOS), so a single integration covers every platform.
Dispatch is best-effort: the in-app inbox record is always persisted first and
a push failure is logged, never propagated to the caller.
"""
import logging
from typing import Any, Dict, Iterable, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger("fyndo.push")

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
_MAX_BATCH_SIZE = 100


class PushService:
    @staticmethod
    def is_enabled() -> bool:
        provider = (settings.PUSH_PROVIDER or "mock").strip().lower()
        return bool(settings.PUSH_ENABLED) and provider != "mock"

    @staticmethod
    def _build_messages(
        tokens: Iterable[str], title: str, body: str, data: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        messages: List[Dict[str, Any]] = []
        for token in tokens:
            if not token:
                continue
            messages.append(
                {
                    "to": token,
                    "title": title,
                    "body": body,
                    "sound": "default",
                    "priority": "high",
                    "data": data or {},
                }
            )
        return messages

    @classmethod
    async def send(
        cls,
        tokens: Iterable[str],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Dispatches a push to every token. Returns True if any batch was accepted."""
        messages = cls._build_messages(tokens, title, body, data)
        if not messages:
            return False

        if not cls.is_enabled():
            logger.info(
                "Push dispatch skipped (provider=%s, enabled=%s) for %d device(s).",
                settings.PUSH_PROVIDER,
                settings.PUSH_ENABLED,
                len(messages),
            )
            return False

        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if settings.EXPO_ACCESS_TOKEN:
            headers["Authorization"] = f"Bearer {settings.EXPO_ACCESS_TOKEN}"

        delivered = False
        for start in range(0, len(messages), _MAX_BATCH_SIZE):
            batch = messages[start:start + _MAX_BATCH_SIZE]
            try:
                async with httpx.AsyncClient(timeout=settings.PUSH_TIMEOUT_SECONDS) as client:
                    response = await client.post(EXPO_PUSH_URL, json=batch, headers=headers)
                    response.raise_for_status()
                delivered = True
            except Exception as exc:  # noqa: BLE001 - best-effort delivery
                logger.warning("Push dispatch failed for %d device(s): %s", len(batch), exc)

        if delivered:
            logger.info("Push dispatched to %d device(s).", len(messages))
        return delivered
