"""WebSocket Connection Manager — In-Memory Fan-Out für MVP."""
from __future__ import annotations

import json
import uuid

from fastapi import WebSocket

from app.core.logging import get_logger

log = get_logger(__name__)


class WebSocketManager:
    """Verwaltet aktive WebSocket-Verbindungen pro Meeting."""

    def __init__(self) -> None:
        # {meeting_id: {participant_id: WebSocket}}
        self._connections: dict[uuid.UUID, dict[uuid.UUID, WebSocket]] = {}

    async def connect(
        self, meeting_id: uuid.UUID, participant_id: uuid.UUID, ws: WebSocket
    ) -> None:
        await ws.accept()
        if meeting_id not in self._connections:
            self._connections[meeting_id] = {}
        self._connections[meeting_id][participant_id] = ws
        log.info("ws_connected", meeting_id=str(meeting_id), participant_id=str(participant_id))
        try:
            from app.core.metrics import ACTIVE_WEBSOCKETS, ACTIVE_MEETINGS
            ACTIVE_WEBSOCKETS.inc()
            ACTIVE_MEETINGS.set(len(self._connections))
        except Exception:
            pass

    def disconnect(self, meeting_id: uuid.UUID, participant_id: uuid.UUID) -> None:
        if meeting_id in self._connections:
            self._connections[meeting_id].pop(participant_id, None)
            if not self._connections[meeting_id]:
                del self._connections[meeting_id]
        log.info("ws_disconnected", meeting_id=str(meeting_id), participant_id=str(participant_id))
        try:
            from app.core.metrics import ACTIVE_WEBSOCKETS, ACTIVE_MEETINGS
            ACTIVE_WEBSOCKETS.dec()
            ACTIVE_MEETINGS.set(len(self._connections))
        except Exception:
            pass

    async def broadcast(
        self,
        meeting_id: uuid.UUID,
        message: dict,
        *,
        exclude: uuid.UUID | None = None,
    ) -> None:
        if meeting_id not in self._connections:
            return

        data = json.dumps(message)
        dead: list[uuid.UUID] = []

        for pid, ws in self._connections[meeting_id].items():
            if pid == exclude:
                continue
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(pid)

        for pid in dead:
            self.disconnect(meeting_id, pid)

    async def send_to(
        self, meeting_id: uuid.UUID, participant_id: uuid.UUID, message: dict
    ) -> None:
        ws = self._connections.get(meeting_id, {}).get(participant_id)
        if ws:
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                self.disconnect(meeting_id, participant_id)

    def get_participant_count(self, meeting_id: uuid.UUID) -> int:
        return len(self._connections.get(meeting_id, {}))
