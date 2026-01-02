"""
Unit tests for app.notification.payload.

These tests validate that build_alarm_webhook_payload:
- produces the expected payload structure (type/event/totals)
- formats timestamps with second precision
- computes totals and Counter-based breakdowns correctly

No I/O is performed; tests use an in-memory fake store.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

from app.core.alarm.alarm_base import AlarmId
from app.domain.events import AlarmEvent, AlarmTransition
from app.domain.models import AlarmSeverity, AlarmState, AlarmType
from app.notification.payload import build_alarm_webhook_payload
from typing import cast
from app.core.state_store import StateStore


@dataclass
class FakeStateStore:
    """
    Minimal store test double providing the attributes used by payload builder.

    Attributes
    ----------
    alarm_states
        Mapping of AlarmId -> AlarmState.
    alarm_events
        List of AlarmEvent history.
    """

    alarm_states: Dict[AlarmId, AlarmState]
    alarm_events: List[AlarmEvent]


def test_build_alarm_webhook_payload_structure_and_event_fields() -> None:
    """
    Payload should include top-level keys: type, event, totals.
    Event sub-payload should include required alarm event fields with stringified enums.
    """
    ts = datetime(2026, 1, 1, 10, 0, 5)

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

    store = FakeStateStore(alarm_states={}, alarm_events=[])

    payload = build_alarm_webhook_payload(cast(StateStore, store), ev)

    assert payload["type"] == "alarm_event"
    assert "event" in payload
    assert "totals" in payload

    event = payload["event"]
    assert event["source"] == "S1"
    assert event["alarm_type"] == str(AlarmType.LOW_LIMIT)
    assert event["severity"] == str(AlarmSeverity.WARNING)
    assert event["transition"] == str(AlarmTransition.RAISED)
    assert event["timestamp"] == "2026-01-01T10:00:05"  # seconds precision
    assert event["message"] == "Low limit breached"
    assert event["value"] == 0.5
    assert event["details"] == "rule=config_low_limit"


def test_build_alarm_webhook_payload_totals_and_breakdowns() -> None:
    """
    Totals should reflect:
    - total number of states
    - number of active states
    - total number of events
    - breakdown counters for states and events
    """
    ts = datetime(2026, 1, 1, 10, 0, 0)

    # Two states: one active CRITICAL wavelength shift, one inactive WARNING low limit
    aid1 = AlarmId(source="FTIR", alarm_type=AlarmType.WAVELENGTH_SHIFT, rule_name="r1")
    aid2 = AlarmId(source="P", alarm_type=AlarmType.LOW_LIMIT, rule_name="r2")

    st1 = AlarmState(
        source="FTIR",
        alarm_type=AlarmType.WAVELENGTH_SHIFT,
        alarm_severity=AlarmSeverity.CRITICAL,
        active=True,
        first_seen=ts,
        last_seen=ts,
        message="Shift",
        last_value=1.2,
    )
    st2 = AlarmState(
        source="P",
        alarm_type=AlarmType.LOW_LIMIT,
        alarm_severity=AlarmSeverity.WARNING,
        active=False,
        first_seen=ts,
        last_seen=ts,
        message="OK",
        last_value=2.0,
    )

    # Two events: one RAISED warning, one UPDATED critical
    ev1 = AlarmEvent(
        source="P",
        alarm_type=AlarmType.LOW_LIMIT,
        severity=AlarmSeverity.WARNING,
        transition=AlarmTransition.RAISED,
        timestamp=ts,
        message="Low limit breached",
        value=0.5,
    )
    ev2 = AlarmEvent(
        source="FTIR",
        alarm_type=AlarmType.WAVELENGTH_SHIFT,
        severity=AlarmSeverity.CRITICAL,
        transition=AlarmTransition.UPDATED,
        timestamp=ts,
        message="Shift updated",
        value=1.5,
    )

    store = FakeStateStore(
        alarm_states={aid1: st1, aid2: st2},
        alarm_events=[ev1, ev2],
    )



    payload = build_alarm_webhook_payload(cast(StateStore, store), ev2)
    totals = payload["totals"]

    assert totals["alarm_states_total"] == 2
    assert totals["alarm_states_active"] == 1
    assert totals["alarm_events_total"] == 2

    # Breakdown keys are stringified (enums -> str(enum))
    assert totals["state_counts_by_severity"][str(AlarmSeverity.CRITICAL)] == 1
    assert totals["state_counts_by_severity"][str(AlarmSeverity.WARNING)] == 1

    assert totals["state_counts_by_type"][str(AlarmType.WAVELENGTH_SHIFT)] == 1
    assert totals["state_counts_by_type"][str(AlarmType.LOW_LIMIT)] == 1

    assert totals["event_counts_by_transition"][str(AlarmTransition.RAISED)] == 1
    assert totals["event_counts_by_transition"][str(AlarmTransition.UPDATED)] == 1

    assert totals["event_counts_by_severity"][str(AlarmSeverity.WARNING)] == 1
    assert totals["event_counts_by_severity"][str(AlarmSeverity.CRITICAL)] == 1

    assert totals["event_counts_by_type"][str(AlarmType.LOW_LIMIT)] == 1
    assert totals["event_counts_by_type"][str(AlarmType.WAVELENGTH_SHIFT)] == 1
