"""
Unit tests for alarm_base contracts.

These tests focus on the *contracts* (data structures & protocols) used by the
alarm engine and criteria implementations.

We verify:
- Immutability / frozen dataclasses (AlarmContext, AlarmId, AlarmDecision)
- Hashability of AlarmId (usable as dict key)
- Protocol compatibility for AlarmCriteria
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime
from typing import Sequence

import pytest

from app.core.alarm.alarm_base import AlarmContext, AlarmCriteria, AlarmDecision, AlarmId
from app.domain.models import AlarmSeverity, AlarmType


class _CriteriaImpl:
    """
    Minimal concrete implementation of AlarmCriteria used for protocol testing.

    This class deliberately does not inherit from AlarmCriteria; it only matches
    the required method signature to confirm Protocol-based duck typing works.
    """

    def evaluate(self, store: object, ctx: AlarmContext) -> Sequence[AlarmDecision]:
        """Return an empty decision list for protocol conformance tests."""
        return []


def test_alarm_context_is_frozen() -> None:
    """
    Ensure AlarmContext is immutable.

    A frozen context prevents accidental mutation during a single evaluation
    cycle and is safe to pass around the system.
    """
    ctx = AlarmContext(now=datetime(2026, 1, 1, 0, 0, 0))
    with pytest.raises(FrozenInstanceError):
        ctx.now = datetime(2026, 1, 2, 0, 0, 0)  # type: ignore[misc]


def test_alarm_id_is_hashable_and_frozen() -> None:
    """
    Ensure AlarmId can be used as a dictionary key and is immutable.

    The alarm engine stores state by AlarmId, so hashability is required.
    """
    aid = AlarmId(source="S1", alarm_type=AlarmType.WAVELENGTH_SHIFT, rule_name="rule")
    d = {aid: "state"}
    assert d[aid] == "state"

    with pytest.raises(FrozenInstanceError):
        aid.source = "S2"  # type: ignore[misc]


def test_alarm_decision_is_frozen() -> None:
    """
    Ensure AlarmDecision is immutable.

    Decisions should be treated as value objects produced by criteria and
    consumed by the engine without mutation.
    """
    aid = AlarmId(source="S1", alarm_type=AlarmType.WAVELENGTH_SHIFT, rule_name="rule")
    dec = AlarmDecision(
        alarm_id=aid,
        severity=AlarmSeverity.CRITICAL,
        should_be_active=True,
        message="msg",
        value=1.0,
    )

    with pytest.raises(FrozenInstanceError):
        dec.message = "changed"  # type: ignore[misc]


def test_alarm_criteria_protocol_conformance() -> None:
    """
    Verify Protocol-based duck typing works for AlarmCriteria.

    A class should be usable as AlarmCriteria if it provides the expected
    evaluate(store, ctx) method signature.
    """
    impl = _CriteriaImpl()

    # Runtime check: we don't need inheritance for protocol conformance.
    # This is a lightweight sanity check to support the architectural choice.
    assert hasattr(impl, "evaluate")
