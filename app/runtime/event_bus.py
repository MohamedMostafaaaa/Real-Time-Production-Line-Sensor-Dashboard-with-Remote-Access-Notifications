from __future__ import annotations

from dataclasses import dataclass, field
from queue import Queue
from typing import Optional

from app.domain.events import AlarmEvent


@dataclass
class EventBus:
    """
    In-process event bus for alarm events using a thread-safe queue.

    The bus provides a simple producer/consumer mechanism:
    - Producers publish :class:`~app.domain.events.AlarmEvent` via :meth:`publish_alarm`.
    - Consumers (e.g., adapter threads) read from :attr:`alarm_events_q`.

    Concurrency Model
    -----------------
    Python's :class:`queue.Queue` is thread-safe. Multiple producers may call
    :meth:`publish_alarm` concurrently without additional locking.

    Backpressure Policy
    -------------------
    If the queue is full, events are dropped (best-effort). This prevents
    notification infrastructure overload from blocking the main application.

    Attributes
    ----------
    alarm_events_q
        Bounded queue of alarm events. Consumers should drain this queue in a loop.
    """

    alarm_events_q: "Queue[AlarmEvent]" = field(default_factory=lambda: Queue(maxsize=5000))

    def publish_alarm(self, ev: AlarmEvent) -> None:
        """
        Publish an alarm event to the queue (non-blocking).

        Parameters
        ----------
        ev
            AlarmEvent to publish.

        Notes
        -----
        If the queue is full or another error occurs, the event is dropped to
        preserve application responsiveness.
        """
        try:
            self.alarm_events_q.put_nowait(ev)
        except Exception:
            # Drop if overloaded to protect app responsiveness.
            pass
