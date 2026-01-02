"""
Alarm lifecycle engine.

This module contains the stateful alarm lifecycle manager that turns stateless
`AlarmDecision` outputs (from `AlarmCriteria`) into:
- Persistent `AlarmState` objects and
- Discrete `AlarmEvent` transitions (RAISED / CLEARED / UPDATED).

The engine does not implement alarm rule logic itself; it orchestrates the
evaluation pipeline and applies decisions to a simple alarm state machine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Sequence

from app.core.alarm.alarm_base import AlarmContext, AlarmCriteria, AlarmDecision, AlarmId
from app.domain.events import AlarmEvent, AlarmTransition
from app.domain.models import AlarmState


def _value_changed(a: Optional[float], b: Optional[float], eps: float = 0.5) -> bool:
    """
    Compare two optional floats with a tolerance.

    This helper is used to avoid producing noisy UPDATED events when values
    fluctuate within a small tolerance.

    Parameters
    ----------
    a, b
        Values to compare. Either value may be None.
    eps
        Minimum absolute difference to consider the value changed.

    Returns
    -------
    bool
        True if values differ meaningfully, False otherwise.
    """
    if a is None and b is None:
        return False
    if a is None or b is None:
        return True
    return abs(a - b) > eps


@dataclass
class AlarmEngine:
    """
    Alarm lifecycle manager (RAISED / CLEARED / UPDATED).

    The engine is responsible for the *stateful* alarm lifecycle decisions.
    It does NOT implement rule logic. Instead, it calls one or more
    `AlarmCriteria` evaluators (stateless) which return `AlarmDecision` objects.

    Lifecycle Model
    ---------------
    For each `AlarmId`, the engine maintains an `AlarmState`:

    - RAISED:  inactive -> active
    - CLEARED: active -> inactive
    - UPDATED: active -> active, but message/value changed (beyond tolerance)

    Notes
    -----
    - This engine updates state only for alarm IDs appearing in the current
      decisions list.
    - If a store object provides optional hooks, they will be called:
        * add_alarm_event(event)
        * set_alarm_state(alarm_id, state)

    Parameters
    ----------
    criteria
        Sequence of criteria evaluators producing alarm decisions.
    value_eps
        Tolerance for float comparisons to avoid noisy UPDATED events.
    """

    criteria: Sequence[AlarmCriteria]
    value_eps: float = 0.5
    _states: Dict[AlarmId, AlarmState] = field(default_factory=dict)

    def run_once(self, store: object, now: Optional[datetime] = None) -> List[AlarmEvent]:
        """
        Evaluate alarms once and update alarm states.

        Parameters
        ----------
        store
            StateStore-like object holding latest readings. Used by criteria evaluators.
        now
            Timestamp for this evaluation. If None, uses `datetime.now()`.

        Returns
        -------
        list of AlarmEvent
            Alarm lifecycle events produced by this evaluation.
        """
        ts = now or datetime.now()
        ctx = AlarmContext(now=ts)

        # Collect decisions from all criteria (stateless evaluation).
        decisions: List[AlarmDecision] = []
        for c in self.criteria:
            decisions.extend(list(c.evaluate(store, ctx)))

        # Apply decisions to state machine and emit events.
        events = self._apply_decisions(decisions, ts)

        # Optional store hooks.
        if hasattr(store, "add_alarm_event"):
            for ev in events:
                store.add_alarm_event(ev)  # type: ignore[attr-defined]

        if hasattr(store, "set_alarm_state"):
            for alarm_id, st in self._states.items():
                store.set_alarm_state(alarm_id, st)  # type: ignore[attr-defined]

        return events

    def get_active_alarms(self) -> List[AlarmState]:
        """
        Return currently active alarms.

        Returns
        -------
        list of AlarmState
            Active alarm states.
        """
        return [s for s in self._states.values() if s.active]

    def _apply_decisions(self, decisions: Sequence[AlarmDecision], ts: datetime) -> List[AlarmEvent]:
        """
        Apply criteria decisions to the alarm state machine.

        Parameters
        ----------
        decisions
            Alarm decisions from criteria evaluation.
        ts
            Evaluation timestamp.

        Returns
        -------
        list of AlarmEvent
            Emitted lifecycle events (RAISED/CLEARED/UPDATED).
        """
        events: List[AlarmEvent] = []

        for d in decisions:
            prev = self._states.get(d.alarm_id)

            # If alarm_id never seen before, create its state.
            if prev is None:
                self._states[d.alarm_id] = AlarmState(
                    source=d.alarm_id.source,
                    alarm_type=d.alarm_id.alarm_type,
                    alarm_severity=d.severity,
                    active=d.should_be_active,
                    first_seen=ts,
                    last_seen=ts,
                    message=d.message,
                    last_value=d.value,
                )

                # Only emit an event if it starts active.
                if d.should_be_active:
                    events.append(
                        AlarmEvent(
                            source=d.alarm_id.source,
                            alarm_type=d.alarm_id.alarm_type,
                            severity=d.severity,
                            transition=AlarmTransition.RAISED,
                            timestamp=ts,
                            message=d.message,
                            value=d.value,
                            details=f"rule={d.alarm_id.rule_name}",
                        )
                    )
                continue

            # Case 1: inactive -> active => RAISED
            if (prev.active is False) and (d.should_be_active is True):
                self._states[d.alarm_id] = AlarmState(
                    source=prev.source,
                    alarm_type=prev.alarm_type,
                    alarm_severity=d.severity,
                    active=True,
                    first_seen=prev.first_seen,
                    last_seen=ts,
                    message=d.message,
                    last_value=d.value,
                )
                events.append(
                    AlarmEvent(
                        source=prev.source,
                        alarm_type=prev.alarm_type,
                        severity=d.severity,
                        transition=AlarmTransition.RAISED,
                        timestamp=ts,
                        message=d.message,
                        value=d.value,
                        details=f"rule={d.alarm_id.rule_name}",
                    )
                )
                continue

            # Case 2: active -> inactive => CLEARED
            if (prev.active is True) and (d.should_be_active is False):
                self._states[d.alarm_id] = AlarmState(
                    source=prev.source,
                    alarm_type=prev.alarm_type,
                    alarm_severity=prev.alarm_severity,
                    active=False,
                    first_seen=prev.first_seen,
                    last_seen=ts,
                    message=d.message,
                    last_value=d.value,
                )
                events.append(
                    AlarmEvent(
                        source=prev.source,
                        alarm_type=prev.alarm_type,
                        severity=prev.alarm_severity,
                        transition=AlarmTransition.CLEARED,
                        timestamp=ts,
                        message=d.message,
                        value=d.value,
                        details=f"rule={d.alarm_id.rule_name}",
                    )
                )
                continue

            # Case 3: active -> active => UPDATED only if something changed
            if (prev.active is True) and (d.should_be_active is True):
                changed = (prev.message != d.message) or _value_changed(prev.last_value, d.value, self.value_eps)

                # Always refresh stored state (last_seen + message + last_value).
                self._states[d.alarm_id] = AlarmState(
                    source=prev.source,
                    alarm_type=prev.alarm_type,
                    alarm_severity=prev.alarm_severity,
                    active=True,
                    first_seen=prev.first_seen,
                    last_seen=ts,
                    message=d.message,
                    last_value=d.value,
                )

                if changed:
                    events.append(
                        AlarmEvent(
                            source=prev.source,
                            alarm_type=prev.alarm_type,
                            severity=prev.alarm_severity,
                            transition=AlarmTransition.UPDATED,
                            timestamp=ts,
                            message=d.message,
                            value=d.value,
                            details=f"rule={d.alarm_id.rule_name}",
                        )
                    )
                continue

            # Case 4: inactive -> inactive => no event (refresh state anyway)
            if (prev.active is False) and (d.should_be_active is False):
                self._states[d.alarm_id] = AlarmState(
                    source=prev.source,
                    alarm_type=prev.alarm_type,
                    alarm_severity=prev.alarm_severity,
                    active=False,
                    first_seen=prev.first_seen,
                    last_seen=ts,
                    message=d.message,
                    last_value=d.value,
                )

        return events
