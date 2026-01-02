"""
Unit tests for the AlarmEngine.

These tests validate the alarm lifecycle state machine implemented by
`AlarmEngine`, including:
- RAISED transitions (inactive -> active)
- UPDATED transitions (active -> active with changed value/message)
- CLEARED transitions (active -> inactive)
- Float comparison tolerance behavior
- Optional store hook integration (event/state persistence)

The tests use lightweight fake implementations of:
- AlarmCriteria
- StateStore-like objects

This ensures deterministic, fast, and isolated unit testing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Sequence

import pytest

from app.core.alarm.alarm_base import AlarmContext, AlarmDecision, AlarmId
from app.core.alarm.alarm_engine import AlarmEngine, _value_changed
from app.domain.events import AlarmTransition
from app.domain.models import AlarmSeverity, AlarmType, AlarmState


@dataclass
class FakeCriteria:
    """
    Fake AlarmCriteria for unit testing.

    This test double returns a preconfigured sequence of AlarmDecision objects,
    allowing deterministic control over alarm engine behavior.

    Parameters
    ----------
    decisions
        Alarm decisions that should be returned when evaluated.
    """

    decisions: Sequence[AlarmDecision]

    def evaluate(self, store: object, ctx: AlarmContext) -> Sequence[AlarmDecision]:
        """
        Return the preconfigured alarm decisions.

        Parameters
        ----------
        store
            Unused in this fake implementation.
        ctx
            Alarm evaluation context (unused).

        Returns
        -------
        Sequence[AlarmDecision]
            The predefined alarm decisions.
        """
        return self.decisions


class FakeStore:
    """
    Fake StateStore capturing AlarmEngine side effects.

    This object implements the optional hooks recognized by AlarmEngine:
    - add_alarm_event
    - set_alarm_state

    It records all received events and states so tests can assert on them.
    """

    def __init__(self) -> None:
        """Initialize empty event and state containers."""
        self.events: List[object] = []
        self.states: dict[AlarmId, AlarmState] = {}

    def add_alarm_event(self, ev: object) -> None:
        """
        Capture an alarm event emitted by the engine.

        Parameters
        ----------
        ev
            AlarmEvent instance.
        """
        self.events.append(ev)

    def set_alarm_state(self, alarm_id: AlarmId, st: AlarmState) -> None:
        """
        Capture an alarm state update from the engine.

        Parameters
        ----------
        alarm_id
            Identifier of the alarm.
        st
            Latest AlarmState for the alarm.
        """
        self.states[alarm_id] = st


def _mk_decision(
    *,
    active: bool,
    msg: str = "msg",
    val: float | None = 1.0,
    rule: str = "ruleA",
    severity: AlarmSeverity = AlarmSeverity.CRITICAL,
    source: str = "S1",
    alarm_type: AlarmType = AlarmType.WAVELENGTH_SHIFT,
) -> AlarmDecision:
    """
    Construct an AlarmDecision for test scenarios.

    This helper minimizes boilerplate and keeps test cases readable.

    Parameters
    ----------
    active
        Whether the alarm should be active.
    msg
        Alarm message.
    val
        Alarm numeric value (optional).
    rule
        Rule name associated with the alarm.
    severity
        Alarm severity level.
    source
        Source identifier (e.g., sensor name).
    alarm_type
        Type of alarm.

    Returns
    -------
    AlarmDecision
        Configured alarm decision instance.
    """
    alarm_id = AlarmId(source=source, alarm_type=alarm_type, rule_name=rule)
    return AlarmDecision(
        alarm_id=alarm_id,
        severity=severity,
        should_be_active=active,
        message=msg,
        value=val,
    )


def test_value_changed_tolerance() -> None:
    """
    Verify float comparison tolerance logic.

    The `_value_changed` helper should:
    - treat two None values as unchanged
    - treat None vs value as changed
    - ignore small differences within epsilon
    - detect meaningful differences beyond epsilon
    """
    assert _value_changed(None, None, eps=1e-3) is False
    assert _value_changed(None, 1.0, eps=1e-3) is True
    assert _value_changed(1.0, None, eps=1e-3) is True
    assert _value_changed(1.0000, 1.0005, eps=1e-3) is False
    assert _value_changed(1.0000, 1.0020, eps=1e-3) is True


def test_alarm_lifecycle_raised_updated_cleared_and_store_hooks() -> None:
    """
    Validate full alarm lifecycle and store integration.

    This test exercises the following sequence:
    1. First evaluation produces an active alarm -> RAISED
    2. Second evaluation keeps alarm active without changes -> no event
    3. Third evaluation changes value beyond tolerance -> UPDATED
    4. Fourth evaluation deactivates alarm -> CLEARED

    The test also verifies that optional store hooks are invoked correctly.
    """
    store = FakeStore()

    t0 = datetime(2026, 1, 1, 10, 0, 0)
    t1 = t0 + timedelta(seconds=5)
    t2 = t1 + timedelta(seconds=5)
    t3 = t2 + timedelta(seconds=5)

    # 1) inactive -> active => RAISED
    d0 = _mk_decision(active=True, msg="A", val=10.0)
    engine = AlarmEngine(criteria=[FakeCriteria([d0])], value_eps=1e-6)

    events0 = engine.run_once(store, now=t0)
    assert len(events0) == 1
    assert events0[0].transition == AlarmTransition.RAISED

    # Store hooks
    assert len(store.events) == 1
    assert d0.alarm_id in store.states
    assert store.states[d0.alarm_id].active is True

    # 2) active -> active (no change) => no UPDATED
    d1 = _mk_decision(active=True, msg="A", val=10.0)
    engine.criteria = [FakeCriteria([d1])]

    events1 = engine.run_once(store, now=t1)
    assert events1 == []
    assert store.states[d0.alarm_id].last_seen == t1

    # 3) active -> active (value change) => UPDATED
    d2 = _mk_decision(active=True, msg="A", val=10.1)
    engine.criteria = [FakeCriteria([d2])]

    events2 = engine.run_once(store, now=t2)
    assert len(events2) == 1
    assert events2[0].transition == AlarmTransition.UPDATED

    # 4) active -> inactive => CLEARED
    d3 = _mk_decision(active=False, msg="cleared", val=None)
    engine.criteria = [FakeCriteria([d3])]

    events3 = engine.run_once(store, now=t3)
    assert len(events3) == 1
    assert events3[0].transition == AlarmTransition.CLEARED
    assert store.states[d0.alarm_id].active is False


def test_no_event_when_first_seen_inactive() -> None:
    """
    Ensure no CLEARED event is emitted for first-seen inactive alarms.

    If an alarm is first encountered in an inactive state, the engine should
    create its AlarmState but not emit any lifecycle events.
    """
    store = FakeStore()
    t0 = datetime(2026, 1, 1, 12, 0, 0)

    d0 = _mk_decision(active=False, msg="inactive", val=None)
    engine = AlarmEngine(criteria=[FakeCriteria([d0])])

    events = engine.run_once(store, now=t0)
    assert events == []
    assert d0.alarm_id in store.states
    assert store.states[d0.alarm_id].active is False
