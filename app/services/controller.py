from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Union

from app.core.alarm.alarm_engine import AlarmEngine
from app.core.state_store import StateStore
from app.domain.events import AlarmEvent
from app.domain.models import FtirSensorReading, SensorReading
from app.runtime.event_bus import EventBus

IncomingMessage = Union[SensorReading, FtirSensorReading]


@dataclass
class MonitoringController:
    """
    Orchestrate ingestion of incoming sensor messages and alarm evaluation.

    Responsibilities
    ----------------
    - Accept decoded incoming messages (scalar or FTIR).
    - Update the shared application state (`StateStore`) with the new reading.
    - Run one alarm evaluation cycle via `AlarmEngine`.
    - Optionally publish emitted alarm events to an `EventBus`.

    Notes
    -----
    This controller contains orchestration logic only. Business rule evaluation
    lives in alarm criteria modules, and lifecycle transitions live in the
    alarm engine.

    Parameters
    ----------
    store
        Thread-safe application state facade used by criteria and UI.
    alarm_engine
        Alarm lifecycle engine that evaluates criteria and emits AlarmEvents.
    bus
        Optional event bus used to publish AlarmEvents to subscribers
        (e.g., notification layer). If None, publishing is skipped.
    """

    store: StateStore
    alarm_engine: AlarmEngine
    bus: Optional[EventBus] = None

    def handle_message(self, msg: IncomingMessage, now: Optional[datetime] = None) -> List[AlarmEvent]:
        """
        Handle one incoming message and return emitted alarm events.

        Parameters
        ----------
        msg
            Incoming decoded message (scalar or FTIR).
        now
            Optional timestamp to use for this processing cycle. If None,
            uses local current time.

        Returns
        -------
        list of AlarmEvent
            Alarm lifecycle events emitted during this cycle.

        Side Effects
        ------------
        - Updates `store` with the new reading.
        - Calls `alarm_engine.run_once(store, now=ts)`.
        - If a bus is configured, publishes emitted events using `bus.publish_alarm`.
        - Backward compatibility: if store lacks `add_alarm_event` but has `add_alarm`,
          forwards events to `store.add_alarm(...)`.
        """
        ts = now or datetime.now()

        if isinstance(msg, SensorReading):
            self.store.update_scalar(msg)
        else:
            self.store.update_spectrum(msg)

        events = self.alarm_engine.run_once(self.store, now=ts)

        if self.bus is not None:
            for ev in events:
                self.bus.publish_alarm(ev)

        # Backward compatibility fallback for older store implementations.
        if not hasattr(self.store, "add_alarm_event") and hasattr(self.store, "add_alarm"):
            for e in events:
                self.store.add_alarm(e)  # type: ignore[attr-defined]

        return events
