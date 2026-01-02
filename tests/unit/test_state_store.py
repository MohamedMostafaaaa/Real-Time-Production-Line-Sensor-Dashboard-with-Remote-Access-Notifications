"""
Unit tests for app.core.state_store.StateStore.

These tests verify that StateStore:
- delegates correctly to its sub-stores (configs, readings, alarms)
- returns snapshot COPIES for UI-facing properties
- supports basic end-to-end workflows used by criteria and AlarmEngine

Notes
-----
This module tests the facade behavior, not the full internal correctness of
ReadingsStore/AlarmStore (those should be tested in their own modules).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.core.alarm.alarm_base import AlarmId
from app.core.state_store import StateStore
from app.domain.events import AlarmEvent, AlarmTransition
from app.domain.models import (
    AlarmSeverity,
    AlarmState,
    AlarmType,
    FtirSensorReading,
    SensorConfig,
    SensorReading,
    SensorStatus,
)


def test_config_roundtrip_scalar_configs() -> None:
    """
    StateStore should accept a SensorConfig and expose it via scalar_configs.
    """
    store = StateStore()
    cfg = SensorConfig(name="Pressure", units="bar", low_limit=1.0, high_limit=10.0)

    store.set_config(cfg)
    cfgs = store.scalar_configs

    assert any(c.name == "Pressure" for c in cfgs)


def test_scalar_reading_roundtrip_get_latest_and_snapshots_copy() -> None:
    """
    StateStore should store scalar readings and provide:
    - get_latest(sensor)
    - snapshots property that returns a COPY
    """
    store = StateStore()

    t0 = datetime(2026, 1, 1, 10, 0, 0)
    r1 = SensorReading(sensor="Pressure", value=5.0, timestamp=t0, status=SensorStatus.OK)
    store.update_scalar(r1)

    latest = store.get_latest("Pressure")
    assert latest is not None
    assert latest.value == 5.0

    snap1 = store.snapshots
    snap1["Injected"] = SensorReading(sensor="Injected", value=1.0, timestamp=t0)  # mutate copy
    snap2 = store.snapshots

    # Ensure internal store was not affected by mutating the returned snapshot
    assert "Injected" not in snap2


def test_ftir_reading_roundtrip_get_latest_ftir_and_snapshots_copy() -> None:
    """
    StateStore should store FTIR readings and provide:
    - get_latest_ftir(sensor)
    - ftir_snapshots property that returns a COPY
    """
    store = StateStore()

    t0 = datetime(2026, 1, 1, 10, 0, 0)
    ft = FtirSensorReading(sensor="FTIR", values=[1.0, 2.0, 3.0], timestamp=t0, status=SensorStatus.OK)
    store.update_spectrum(ft)

    latest = store.get_latest_ftir("FTIR")
    assert latest is not None
    assert list(latest.values) == [1.0, 2.0, 3.0]

    snap1 = store.ftir_snapshots
    snap1["Injected"] = FtirSensorReading(sensor="Injected", values=[0.0], timestamp=t0)  # mutate copy
    snap2 = store.ftir_snapshots

    assert "Injected" not in snap2


def test_alarm_event_and_state_roundtrip_and_snapshot_copies() -> None:
    """
    StateStore should persist alarm events and states and expose snapshot copies.
    """
    store = StateStore()
    ts = datetime(2026, 1, 1, 10, 0, 0)

    aid = AlarmId(source="S1", alarm_type=AlarmType.LOW_LIMIT, rule_name="config_low_limit")
    st = AlarmState(
        source="S1",
        alarm_type=AlarmType.LOW_LIMIT,
        alarm_severity=AlarmSeverity.WARNING,
        active=True,
        first_seen=ts,
        last_seen=ts,
        message="Low limit breached",
        last_value=0.5,
    )

    ev = AlarmEvent(
        source="S1",
        alarm_type=AlarmType.LOW_LIMIT,
        severity=AlarmSeverity.WARNING,
        transition=AlarmTransition.RAISED,
        timestamp=ts,
        message="Low limit breached",
        value=0.5,
        details="rule=config_low_limit",
    )

    store.set_alarm_state(aid, st)
    store.add_alarm_event(ev)

    # Validate retrieval
    states = store.alarm_states
    events = store.alarm_events
    assert aid in states
    assert len(events) == 1
    assert events[0].transition is AlarmTransition.RAISED

    # Validate snapshot copy behavior
    states["Injected"] = st  # type: ignore[index]
    events.append(ev)

    states2 = store.alarm_states
    events2 = store.alarm_events
    assert "Injected" not in states2
    assert len(events2) == 1


def test_get_active_alarm_states() -> None:
    """
    StateStore should return only active alarm states.
    """
    store = StateStore()
    ts = datetime(2026, 1, 1, 10, 0, 0)

    aid_active = AlarmId(source="S1", alarm_type=AlarmType.HIGH_LIMIT, rule_name="config_high_limit")
    aid_inactive = AlarmId(source="S2", alarm_type=AlarmType.LOW_LIMIT, rule_name="config_low_limit")

    st_active = AlarmState(
        source="S1",
        alarm_type=AlarmType.HIGH_LIMIT,
        alarm_severity=AlarmSeverity.WARNING,
        active=True,
        first_seen=ts,
        last_seen=ts + timedelta(seconds=1),
        message="High limit breached",
        last_value=12.0,
    )
    st_inactive = AlarmState(
        source="S2",
        alarm_type=AlarmType.LOW_LIMIT,
        alarm_severity=AlarmSeverity.WARNING,
        active=False,
        first_seen=ts,
        last_seen=ts + timedelta(seconds=1),
        message="Back to normal",
        last_value=2.0,
    )

    store.set_alarm_state(aid_active, st_active)
    store.set_alarm_state(aid_inactive, st_inactive)

    active = store.get_active_alarm_states()
    assert len(active) == 1
    assert active[0].source == "S1"


def test_clear_alarm_history() -> None:
    """
    clear_alarm_history should clear both alarm events and alarm states.
    """
    store = StateStore()
    ts = datetime(2026, 1, 1, 10, 0, 0)

    aid = AlarmId(source="S1", alarm_type=AlarmType.LOW_LIMIT, rule_name="config_low_limit")
    st = AlarmState(
        source="S1",
        alarm_type=AlarmType.LOW_LIMIT,
        alarm_severity=AlarmSeverity.WARNING,
        active=True,
        first_seen=ts,
        last_seen=ts,
        message="Low limit breached",
    )
    ev = AlarmEvent(
        source="S1",
        alarm_type=AlarmType.LOW_LIMIT,
        severity=AlarmSeverity.WARNING,
        transition=AlarmTransition.RAISED,
        timestamp=ts,
        message="Low limit breached",
    )

    store.set_alarm_state(aid, st)
    store.add_alarm_event(ev)

    assert len(store.alarm_events) == 1
    assert len(store.alarm_states) == 1

    store.clear_alarm_history()

    assert store.alarm_events == []
    assert store.alarm_states == {}
