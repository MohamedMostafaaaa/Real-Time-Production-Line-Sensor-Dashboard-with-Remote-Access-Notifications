"""
Unit tests for app.services.controller.MonitoringController.

These tests validate orchestration behavior:
- correct routing of incoming message types (scalar vs FTIR)
- running the alarm engine after storing the reading
- publishing emitted alarm events to the bus when provided
- backward compatibility fallback to store.add_alarm when add_alarm_event is missing

No threads, UI, or network I/O are involved.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, cast

from app.core.state_store import StateStore
from app.domain.events import AlarmEvent, AlarmTransition
from app.domain.models import AlarmSeverity, AlarmType, FtirSensorReading, SensorReading
from app.services.controller import MonitoringController


@dataclass
class FakeAlarmEngine:
    """
    Fake alarm engine that records calls and returns a predefined event list.
    """

    events_to_return: List[AlarmEvent] = field(default_factory=list)
    last_now: Optional[datetime] = None
    call_count: int = 0

    def run_once(self, store: object, now: Optional[datetime] = None) -> List[AlarmEvent]:
        """Record invocation and return predefined events."""
        self.call_count += 1
        self.last_now = now
        return list(self.events_to_return)


@dataclass
class FakeBus:
    """
    Fake event bus that records published alarm events.
    """

    published: List[AlarmEvent] = field(default_factory=list)

    def publish_alarm(self, ev: AlarmEvent) -> None:
        """Record published events."""
        self.published.append(ev)


@dataclass
class FakeStore:
    """
    Minimal store test double for controller behavior.

    This fake implements only the methods used by MonitoringController.
    """

    scalar_updates: List[SensorReading] = field(default_factory=list)
    spectrum_updates: List[FtirSensorReading] = field(default_factory=list)
    legacy_added_alarms: List[AlarmEvent] = field(default_factory=list)

    def update_scalar(self, reading: SensorReading) -> None:
        """Record scalar update."""
        self.scalar_updates.append(reading)

    def update_spectrum(self, reading: FtirSensorReading) -> None:
        """Record spectrum update."""
        self.spectrum_updates.append(reading)

    # Legacy API (used only when add_alarm_event does not exist)
    def add_alarm(self, ev: AlarmEvent) -> None:
        """Legacy alarm event sink."""
        self.legacy_added_alarms.append(ev)


def _mk_event(ts: datetime, msg: str) -> AlarmEvent:
    """
    Create a minimal AlarmEvent for tests.

    Parameters
    ----------
    ts
        Event timestamp.
    msg
        Message for the event.

    Returns
    -------
    AlarmEvent
        Test alarm event.
    """
    return AlarmEvent(
        source="S1",
        alarm_type=AlarmType.LOW_LIMIT,
        severity=AlarmSeverity.WARNING,
        transition=AlarmTransition.RAISED,
        timestamp=ts,
        message=msg,
    )


def test_handle_message_scalar_updates_store_and_runs_engine() -> None:
    """
    Scalar messages should call store.update_scalar and then run the alarm engine.
    """
    ts = datetime(2026, 1, 1, 10, 0, 0)
    store = FakeStore()
    engine = FakeAlarmEngine(events_to_return=[_mk_event(ts, "e1")])

    controller = MonitoringController(store=cast(StateStore, store), alarm_engine=cast(object, engine))  # type: ignore[arg-type]
    msg = SensorReading(sensor="Pressure", value=5.0, timestamp=ts)

    events = controller.handle_message(msg, now=ts)

    assert store.scalar_updates == [msg]
    assert store.spectrum_updates == []
    assert engine.call_count == 1
    assert engine.last_now == ts
    assert len(events) == 1
    assert events[0].message == "e1"


def test_handle_message_spectrum_updates_store_and_runs_engine() -> None:
    """
    FTIR messages should call store.update_spectrum and then run the alarm engine.
    """
    ts = datetime(2026, 1, 1, 10, 0, 0)
    store = FakeStore()
    engine = FakeAlarmEngine(events_to_return=[_mk_event(ts, "e1")])

    controller = MonitoringController(store=cast(StateStore, store), alarm_engine=cast(object, engine))  # type: ignore[arg-type]
    msg = FtirSensorReading(sensor="FTIR", values=[1.0, 2.0], timestamp=ts)

    events = controller.handle_message(msg, now=ts)

    assert store.spectrum_updates == [msg]
    assert store.scalar_updates == []
    assert engine.call_count == 1
    assert engine.last_now == ts
    assert len(events) == 1


def test_handle_message_publishes_events_to_bus() -> None:
    """
    If a bus is provided, controller should publish each emitted AlarmEvent.
    """
    ts = datetime(2026, 1, 1, 10, 0, 0)
    ev1 = _mk_event(ts, "e1")
    ev2 = _mk_event(ts, "e2")

    store = FakeStore()
    engine = FakeAlarmEngine(events_to_return=[ev1, ev2])
    bus = FakeBus()

    controller = MonitoringController(
        store=cast(StateStore, store),
        alarm_engine=cast(object, engine),  # type: ignore[arg-type]
        bus=cast(object, bus),              # type: ignore[arg-type]
    )

    msg = SensorReading(sensor="Pressure", value=5.0, timestamp=ts)
    events = controller.handle_message(msg, now=ts)

    assert events == [ev1, ev2]
    assert bus.published == [ev1, ev2]


def test_handle_message_legacy_fallback_add_alarm_used_when_add_alarm_event_missing() -> None:
    """
    If store lacks add_alarm_event but has add_alarm, controller should call add_alarm
    for each emitted event (legacy compatibility path).
    """
    ts = datetime(2026, 1, 1, 10, 0, 0)
    ev1 = _mk_event(ts, "e1")

    store = FakeStore()
    engine = FakeAlarmEngine(events_to_return=[ev1])

    # FakeStore intentionally has add_alarm but does NOT have add_alarm_event.
    assert not hasattr(store, "add_alarm_event")
    assert hasattr(store, "add_alarm")

    controller = MonitoringController(store=cast(StateStore, store), alarm_engine=cast(object, engine))  # type: ignore[arg-type]
    msg = SensorReading(sensor="Pressure", value=5.0, timestamp=ts)

    controller.handle_message(msg, now=ts)

    assert store.legacy_added_alarms == [ev1]


def test_handle_message_legacy_fallback_not_used_when_add_alarm_event_exists() -> None:
    """
    If store has add_alarm_event, legacy add_alarm fallback should not run.
    """
    ts = datetime(2026, 1, 1, 10, 0, 0)
    ev1 = _mk_event(ts, "e1")

    @dataclass
    class StoreWithAddAlarmEvent(FakeStore):
        """FakeStore variant that includes add_alarm_event like the real StateStore."""

        def add_alarm_event(self, event: AlarmEvent) -> None:
            """Simulate modern store API (no-op for this test)."""
            return None

    store = StoreWithAddAlarmEvent()
    engine = FakeAlarmEngine(events_to_return=[ev1])

    controller = MonitoringController(store=cast(StateStore, store), alarm_engine=cast(object, engine))  # type: ignore[arg-type]
    msg = SensorReading(sensor="Pressure", value=5.0, timestamp=ts)

    controller.handle_message(msg, now=ts)

    assert store.legacy_added_alarms == []
