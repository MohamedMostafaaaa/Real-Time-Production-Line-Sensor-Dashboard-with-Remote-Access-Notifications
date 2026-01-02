"""
Alarm evaluation contracts (context, identifiers, and decisions).

This module defines the core data structures that form the contract between:

- Alarm criteria (stateless evaluators) producing -> class:`AlarmDecision`
- The alarm engine (stateful lifecycle manager) consuming decisions and emitting events/states

The objects here are immutable, and hashable so they can be
used safely as keys (e.g., in dictionaries) and passed across threads without surprises.

Notes
-----

- `AlarmId` is designed to be stable and uniquely identify a single alarm "instance" inside
the engine across time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol, Sequence

from app.domain.models import AlarmSeverity, AlarmType


@dataclass(frozen=True)
class AlarmContext:
    """
    Context passed into alarm evaluation.

    Alarm criteria needs a consistent timestamp to evaluate readings, apply
    time-based rules, or annotate results. This context provides a single source
    of truth for "now" during one engine evaluation cycle.

    Parameters
    ----------
    now
        Evaluation timestamp for the current cycle.
    """

    now: datetime


@dataclass(frozen=True)
class AlarmId:
    """
    Unique identifier for an alarm instance inside the engine.

    An alarm is uniquely identified by:
    - ``source``: where it came from (e.g., sensor name)
    - ``alarm_type``: category/type of alarm condition (e.g., HIGH_LIMIT, LOW_LIMIT)
    - ``rule_name``: human-friendly name distinguishing multiple rules

    Examples
    --------
    Two alarms from the same source/type but different rule name are distinct:

    - Pressure + LOW_LIMIT  (rule_name="Pressure low limit")
    - Pressure + HIGH_LIMIT (rule_name="Pressure high limit")

    Notes
    -----
    This object is **immutable and hashable** (frozen dataclass), which allows it
    to be used as a dictionary key for storing alarm states.

    Parameters
    ----------
    source
        Sensor/subsystem name that produced the alarm.
    alarm_type
        Category/type of alarm condition.
    rule_name
        Human-friendly rule name (separates multiple alarms per source/type).
    """

    source: str
    alarm_type: AlarmType
    rule_name: str


@dataclass(frozen=True)
class AlarmDecision:
    """
    Result of evaluating a single alarm condition.

    Alarm criteria (stateless evaluators) produce decisions. The engine then
    consumes decisions to:
    - transition alarm lifecycle (RAISED/CLEARED/UPDATED),
    - emit events, and
    - update stored alarm state.

    Invariants
    ----------
    - ``alarm_id`` must be stable for the same logical alarm across evaluations.
    - ``should_be_active`` reflects whether the condition is currently true.
    - ``severity`` is typically interpreted by UI/reporting; the engine may also
      store it as part of the state.

    Parameters
    ----------
    alarm_id
        Unique identifier of this alarm "instance".
    severity
        Severity of the alarm.
    should_be_active
        Whether the alarm condition is currently true.
    message
        Human-readable message describing the condition.
    value
        Optional scalar value associated with the alarm (e.g., measured delta,
        sensor reading, computed score).
    """

    alarm_id: AlarmId
    severity: AlarmSeverity
    should_be_active: bool
    message: str
    value: Optional[float] = None


class AlarmCriteria(Protocol):
    """
    Protocol interface for alarm criteria evaluation.

    Any class implementing this protocol can be used by -> class:`AlarmEngine`.
    Criteria should be **stateless** and derive all required information from 
    the provided ``store`` and ``ctx``.

    Methods
    -------
    evaluate(store, ctx)
        Evaluate the current system state and return zero or more alarm decisions.
    """

    def evaluate(self, store: object, ctx: AlarmContext) -> Sequence[AlarmDecision]:
        """
        Evaluate alarm conditions and return decisions.

        Parameters
        ----------
        store
            StateStore-like object containing the latest readings/state required
            to evaluate rules.
        ctx
            Evaluation context (e.g., timestamp) for the current engine cycle.

        Returns
        -------
        Sequence[AlarmDecision]
            Zero or more alarm decisions produced by this criterion.
        """
        ...
