"""
Unit tests for app.domain.events.

These tests validate the alarm event domain contracts:
- Enum stability for AlarmTransition
- Immutability of AlarmEvent
- Correct construction and field preservation

The goal is to ensure that events emitted by the alarm engine are safe to
persist, log, and consume by downstream components.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from app.domain.events import AlarmEvent, AlarmTransition
from app.domain.models import AlarmSeverity, AlarmType


def test_alarm_transition_enum_values() -> None:
    """
    Ensure AlarmTransition enum members and values are stable.

    These string values are often serialized and used by UI and reporting layers.
    """
    assert AlarmTransition.RAISED.value == "RAISED"
    assert AlarmTransition.CLEARED.value == "CLEARED"
    assert AlarmTransition.UPDATED.value == "UPDATED"


def test_alarm_event_creation_and_fields() -> None:
    """
    Validate that AlarmEvent instances are created with correct field values.
    """
    ts = datetime(2026, 1, 1, 10, 0, 0)

    ev = AlarmEvent(
        source="S1",
        alarm_type=AlarmType.WAVELENGTH_SHIFT,
        severity=AlarmSeverity.CRITICAL,
        transition=AlarmTransition.RAISED,
        timestamp=ts,
        message="Peak shift detected",
        value=1.25,
        details="rule=FTIR_PeakShift",
    )

    assert ev.source == "S1"
    assert ev.alarm_type is AlarmType.WAVELENGTH_SHIFT
    assert ev.severity is AlarmSeverity.CRITICAL
    assert ev.transition is AlarmTransition.RAISED
    assert ev.timestamp == ts
    assert ev.message == "Peak shift detected"
    assert ev.value == 1.25
    assert ev.details == "rule=FTIR_PeakShift"


def test_alarm_event_is_frozen() -> None:
    """
    Ensure AlarmEvent is immutable.

    Immutability guarantees that emitted events cannot be modified after creation,
    which is critical for auditability and reproducibility.
    """
    ev = AlarmEvent(
        source="S1",
        alarm_type=AlarmType.LOW_LIMIT,
        severity=AlarmSeverity.WARNING,
        transition=AlarmTransition.CLEARED,
        timestamp=datetime(2026, 1, 1, 11, 0, 0),
        message="Back to normal",
    )

    with pytest.raises(FrozenInstanceError):
        ev.message = "changed"  # type: ignore[misc]
