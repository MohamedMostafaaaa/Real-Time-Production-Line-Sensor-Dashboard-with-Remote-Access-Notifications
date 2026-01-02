"""
Unit tests for app.core.state.alarm_store.AlarmStore.

These tests validate:
- event append order
- state overwrite behavior
- filtering of active alarm states
- clearing of events and states

The store is tested in isolation; thread-safety is assumed to be handled by
the enclosing StateStore.
"""

from __future__ import annotations

from datetime import datetime

from app.core.alarm.alarm_base import AlarmId
from app.core.state.alarm_store import AlarmStore
from app.domain.events import AlarmEvent, AlarmTransition
from app.domain.models import AlarmSeverity, AlarmState, AlarmType


def test_add_event_appends_in_order() -> None:
    """
    add_event should append alarm events in insertion order.
    """
    store = AlarmStore()
    ts = datetime(2026, 1, 1, 10, 0, 0)

    ev1 = AlarmEvent(
        source="S1",
        alarm_type=AlarmType.LOW_LIMIT,
        severity=AlarmSeverity.WARNING,
        transition=AlarmTransition.RAISED,
        timestamp=ts,
        message="Low limit breached",
    )
    ev2 = AlarmEvent(
        source="S1",
        alarm_type=AlarmType.LOW_LIMIT,
        severity=AlarmSeverity.WARNING,
        transition=AlarmTransition.CLEARED,
        timestamp=ts,
        message="Back to normal",
    )

    store.add_event(ev1)
    store.add_event(ev2)

    assert store.events == [ev1, ev2]


def test_set_state_overwrites_existing_state() -> None:
    """
    set_state should overwrite the state for the same AlarmId.
    """
    store = AlarmStore()
    ts = datetime(2026, 1, 1, 10, 0, 0)

    aid = AlarmId(source="S1", alarm_type=AlarmType.HIGH_LIMIT, rule_name="config_high_limit")

    st1 = AlarmState(
        source="S1",
        alarm_type=AlarmType.HIGH_LIMIT,
        alarm_severity=AlarmSeverity.WARNING,
        active=True,
        first_seen=ts,
        last_seen=ts,
        message="High limit breached",
        last_value=12.0,
    )
    st2 = AlarmState(
        source="S1",
        alarm_type=AlarmType.HIGH_LIMIT,
        alarm_severity=AlarmSeverity.WARNING,
        active=False,
        first_seen=ts,
        last_seen=ts,
        message="Back to normal",
        last_value=9.0,
    )

    store.set_state(aid, st1)
    store.set_state(aid, st2)

    assert store.states[aid] is st2
    assert store.states[aid].active is False


def test_active_states_filters_only_active() -> None:
    """
    active_states should return only states where active=True.
    """
    store = AlarmStore()
    ts = datetime(2026, 1, 1, 10, 0, 0)

    aid_active = AlarmId(source="S1", alarm_type=AlarmType.LOW_LIMIT, rule_name="config_low_limit")
    aid_inactive = AlarmId(source="S2", alarm_type=AlarmType.HIGH_LIMIT, rule_name="config_high_limit")

    store.set_state(
        aid_active,
        AlarmState(
            source="S1",
            alarm_type=AlarmType.LOW_LIMIT,
            alarm_severity=AlarmSeverity.WARNING,
            active=True,
            first_seen=ts,
            last_seen=ts,
            message="Low limit breached",
        ),
    )
    store.set_state(
        aid_inactive,
        AlarmState(
            source="S2",
            alarm_type=AlarmType.HIGH_LIMIT,
            alarm_severity=AlarmSeverity.WARNING,
            active=False,
            first_seen=ts,
            last_seen=ts,
            message="Back to normal",
        ),
    )

    active = store.active_states()
    assert len(active) == 1
    assert active[0].source == "S1"


def test_clear_removes_all_events_and_states() -> None:
    """
    clear should remove all stored events and states.
    """
    store = AlarmStore()
    ts = datetime(2026, 1, 1, 10, 0, 0)

    aid = AlarmId(source="S1", alarm_type=AlarmType.LOW_LIMIT, rule_name="config_low_limit")

    store.add_event(
        AlarmEvent(
            source="S1",
            alarm_type=AlarmType.LOW_LIMIT,
            severity=AlarmSeverity.WARNING,
            transition=AlarmTransition.RAISED,
            timestamp=ts,
            message="Low limit breached",
        )
    )
    store.set_state(
        aid,
        AlarmState(
            source="S1",
            alarm_type=AlarmType.LOW_LIMIT,
            alarm_severity=AlarmSeverity.WARNING,
            active=True,
            first_seen=ts,
            last_seen=ts,
            message="Low limit breached",
        ),
    )

    store.clear()

    assert store.events == []
    assert store.states == {}
