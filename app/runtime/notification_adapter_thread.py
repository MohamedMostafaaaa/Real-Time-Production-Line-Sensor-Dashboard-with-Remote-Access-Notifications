from __future__ import annotations

import threading
from queue import Empty

from app.core.state_store import StateStore
from app.domain.events import AlarmEvent
from app.notification.base import NotificationEvent
from app.notification.notification_thread import NotificationWorkerThread
from app.notification.payload import build_alarm_webhook_payload
from app.runtime.event_bus import EventBus


class NotificationAdapterThread:
    """
    Adapter thread that bridges domain AlarmEvent -> NotificationWorkerThread.

    Responsibilities
    ----------------
    - Subscribe to `EventBus.alarm_events_q` (domain events).
    - Build a webhook payload snapshot using the current `StateStore`.
    - Emit `NotificationEvent` objects into `NotificationWorkerThread` asynchronously.

    Concurrency Model
    -----------------
    - Runs as a daemon thread.
    - Polls queue with timeout to remain responsive to stop signals.
    - Any exception during payload building or emit is caught and logged.

    Parameters
    ----------
    bus
        Event bus providing AlarmEvent queue.
    store
        StateStore used to build snapshot totals and event payload.
    notifier
        Notification worker responsible for actual sending.
    stop_event
        Stop signal for the thread.
    """

    def __init__(
        self,
        bus: EventBus,
        store: StateStore,
        notifier: NotificationWorkerThread,
        stop_event: threading.Event,
    ):
        self._bus = bus
        self._store = store
        self._notifier = notifier
        self._stop = stop_event
        self._thread = threading.Thread(target=self._run, name="notification-adapter", daemon=True)

    def start(self) -> None:
        """
        Start the adapter thread if not already running.
        """
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self) -> None:
        """
        Signal the adapter thread to stop.
        """
        self._stop.set()

    def join(self, timeout: float | None = 2.0) -> None:
        """
        Join the adapter thread.

        Parameters
        ----------
        timeout
            Maximum time to wait for the thread to exit.
        """
        self._thread.join(timeout=timeout)

    def _run(self) -> None:
        """
        Worker loop: consume AlarmEvent and emit NotificationEvent.
        """
        while not self._stop.is_set():
            try:
                ev: AlarmEvent = self._bus.alarm_events_q.get(timeout=0.5)
            except Empty:
                continue

            try:
                payload = build_alarm_webhook_payload(self._store, ev)
                self._notifier.emit(
                    NotificationEvent(
                        type="alarm_event",
                        payload=payload,
                        severity=str(ev.severity),
                        source=ev.source,
                        ts=ev.timestamp.isoformat(timespec="seconds"),
                    )
                )
            except Exception as e:
                print(f"[APP][NOTIFY-ADAPTER] failed: {e!r}")
