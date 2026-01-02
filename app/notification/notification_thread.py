from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from typing import List

from app.notification.base import NotificationEvent, Notifier


@dataclass(frozen=True)
class NotificationThreadConfig:
    max_queue: int = 2000
    retry_count: int = 3
    retry_backoff_s: float = 0.5
    poll_timeout_s: float = 0.5


class NotificationWorkerThread:
    def __init__(self, notifiers: List[Notifier], cfg: NotificationThreadConfig | None = None):
        self._notifiers = notifiers
        self._cfg = cfg or NotificationThreadConfig()
        self._q: "queue.Queue[NotificationEvent]" = queue.Queue(maxsize=self._cfg.max_queue)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="notification-worker", daemon=True)

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        try:
            self._q.put_nowait(NotificationEvent(type="__stop__", payload={}))
        except Exception:
            pass
        self._thread.join(timeout=2.0)

    def emit(self, event: NotificationEvent) -> None:
        try:
            self._q.put_nowait(event)
        except queue.Full:
            # Drop newest if overloaded to protect UI/app stability
            pass

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                event = self._q.get(timeout=self._cfg.poll_timeout_s)
            except queue.Empty:
                continue

            if event.type == "__stop__":
                break

            for notifier in self._notifiers:
                self._send_with_retries(notifier, event)

    def _send_with_retries(self, notifier: Notifier, event: NotificationEvent) -> None:
        for attempt in range(self._cfg.retry_count + 1):
            try:
                notifier.notify(event)
                return
            except Exception:
                if attempt >= self._cfg.retry_count:
                    return
                time.sleep(self._cfg.retry_backoff_s * (2 ** attempt))
