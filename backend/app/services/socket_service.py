"""In-process WebSocket fan-out for real-time merchant alerts.

Connections are kept per merchant so every open owner dashboard and cashier
terminal of a store receives the same events. The pool lives in this process
only; running several API workers would need a shared broker (e.g. Redis
pub/sub) in front of ``broadcast_to_merchant``.
"""
import asyncio
import logging
from collections import defaultdict
from typing import Any, Dict, Set

from fastapi import WebSocket

logger = logging.getLogger("fyndo.sockets")


class MerchantConnectionManager:
    def __init__(self) -> None:
        self._connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, merchant_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[merchant_id].add(websocket)

    async def disconnect(self, merchant_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            sockets = self._connections.get(merchant_id)
            if not sockets:
                return
            sockets.discard(websocket)
            if not sockets:
                self._connections.pop(merchant_id, None)

    def connection_count(self, merchant_id: str) -> int:
        return len(self._connections.get(merchant_id, ()))

    async def broadcast_to_merchant(self, merchant_id: str, payload: Dict[str, Any]) -> int:
        """Sends ``payload`` to every live socket of the merchant; returns deliveries."""
        async with self._lock:
            targets = list(self._connections.get(merchant_id, ()))
        delivered = 0
        for websocket in targets:
            try:
                await websocket.send_json(payload)
                delivered += 1
            except Exception:
                logger.debug("Dropping dead merchant socket for %s", merchant_id, exc_info=True)
                await self.disconnect(merchant_id, websocket)
        return delivered


merchant_sockets = MerchantConnectionManager()


async def broadcast_safe(merchant_id: str, payload: Dict[str, Any]) -> int:
    """Best-effort broadcast that never breaks the calling request."""
    try:
        return await merchant_sockets.broadcast_to_merchant(merchant_id, payload)
    except Exception:
        logger.warning("Merchant broadcast failed for %s", merchant_id, exc_info=True)
        return 0
