"""Server-Sent Events hub — push channel from server to a specific browser.

Alerts fire from the scheduler thread; the browser needs to hear about them
without polling. SSE is the simplest fit: a one-way text/event-stream the
frontend opens with EventSource. We keep a set of queues per device; the
scheduler publishes (thread-safe via queue.Queue) and each open stream drains
its queue.

stdlib queue.Queue is thread-safe, so the sync scheduler thread and the async
stream coroutine talk through it safely without locks of our own.
"""
from __future__ import annotations

import asyncio
import json
import queue as _queue
import threading

_HEARTBEAT_S = 15      # comment ping so proxies/clients keep the stream open
_POLL_S = 1.0
_MAX_BACKLOG = 100     # drop oldest if a dead client never drains


class SseHub:
    def __init__(self) -> None:
        self._subs: dict[str, set[_queue.Queue]] = {}
        self._lock = threading.Lock()

    def subscribe(self, device: str) -> _queue.Queue:
        q: _queue.Queue = _queue.Queue(maxsize=_MAX_BACKLOG)
        with self._lock:
            self._subs.setdefault(device, set()).add(q)
        return q

    def unsubscribe(self, device: str, q: _queue.Queue) -> None:
        with self._lock:
            qs = self._subs.get(device)
            if qs:
                qs.discard(q)
                if not qs:
                    self._subs.pop(device, None)

    def publish(self, device: str, event: dict) -> None:
        """Push an event to every open stream for this device. Thread-safe."""
        with self._lock:
            qs = list(self._subs.get(device, ()))
        for q in qs:
            try:
                q.put_nowait(event)
            except _queue.Full:
                try:
                    q.get_nowait()       # drop oldest, keep the stream alive
                    q.put_nowait(event)
                except (_queue.Empty, _queue.Full):
                    pass

    def device_count(self) -> int:
        with self._lock:
            return len(self._subs)

    async def stream(self, device: str, is_disconnected):
        """Async generator yielding SSE frames for one device until it drops."""
        q = self.subscribe(device)
        try:
            yield ": connected\n\n"
            since_beat = 0.0
            while True:
                if await is_disconnected():
                    break
                try:
                    event = q.get_nowait()
                    yield f"data: {json.dumps(event)}\n\n"
                    continue
                except _queue.Empty:
                    pass
                await asyncio.sleep(_POLL_S)
                since_beat += _POLL_S
                if since_beat >= _HEARTBEAT_S:
                    since_beat = 0.0
                    yield ": ping\n\n"
        finally:
            self.unsubscribe(device, q)


hub = SseHub()
