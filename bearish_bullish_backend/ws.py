"""WebSocket connection manager for screener broadcasts."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)

SEND_TIMEOUT_SEC = 5.0


class ConnectionManager:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()

    @property
    def count(self) -> int:
        return len(self._clients)

    async def connect(self, ws: WebSocket, initial_message: dict[str, Any] | None = None) -> None:
        await ws.accept()
        self._clients.add(ws)
        logger.info("WS client connected (%d total)", self.count)
        if initial_message is not None:
            await self._send(ws, json.dumps(initial_message))

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._clients:
            self._clients.discard(ws)
            logger.info("WS client disconnected (%d total)", self.count)

    async def _send(self, ws: WebSocket, text: str) -> bool:
        try:
            await asyncio.wait_for(ws.send_text(text), timeout=SEND_TIMEOUT_SEC)
            return True
        except Exception as exc:  # closed socket, timeout, runtime error
            logger.debug("Dropping WS client: %s", exc)
            return False

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Serialise once and fan out concurrently; unreachable clients are removed."""
        if not self._clients:
            return
        text = json.dumps(message)
        clients = list(self._clients)
        results = await asyncio.gather(*(self._send(ws, text) for ws in clients))
        for ws, ok in zip(clients, results):
            if not ok:
                self.disconnect(ws)
