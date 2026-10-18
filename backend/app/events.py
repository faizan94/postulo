"""Per-search event bus with a replay buffer (PHASE1_PLAN.md §5.4).

A channel lives from POST /api/searches until the run ends. Late subscribers get the buffered
events first, so nothing is missed. Events are idempotent on the client (job cards upsert by
posting_id), so a snapshot plus a replay may repeat a card without harm.
"""

import asyncio
import json
from typing import Any

Event = dict[str, Any]


class _Channel:
    def __init__(self) -> None:
        self.buffer: list[Event] = []
        self.subscribers: set[asyncio.Queue[Event | None]] = set()


class EventBus:
    def __init__(self) -> None:
        self._channels: dict[int, _Channel] = {}

    def open(self, search_id: int) -> None:
        self._channels.setdefault(search_id, _Channel())

    def publish(self, search_id: int, event: Event) -> None:
        ch = self._channels.get(search_id)
        if ch is None:
            return
        ch.buffer.append(event)
        for q in ch.subscribers:
            q.put_nowait(event)

    def close(self, search_id: int) -> None:
        ch = self._channels.pop(search_id, None)
        if ch is not None:
            for q in ch.subscribers:
                q.put_nowait(None)

    def subscribe(self, search_id: int) -> tuple[list[Event], asyncio.Queue[Event | None]] | None:
        """None if the search has no live channel (finished, or never started here)."""
        ch = self._channels.get(search_id)
        if ch is None:
            return None
        q: asyncio.Queue[Event | None] = asyncio.Queue()
        ch.subscribers.add(q)
        return list(ch.buffer), q

    def unsubscribe(self, search_id: int, q: asyncio.Queue[Event | None]) -> None:
        ch = self._channels.get(search_id)
        if ch is not None:
            ch.subscribers.discard(q)


def sse(event: Event) -> str:
    return f"data: {json.dumps(event, default=str)}\n\n"
