from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from app.core.alarm.alarm_base import AlarmId
from app.domain.events import AlarmEvent
from app.domain.models import AlarmState


@dataclass
class AlarmStore:
    """
    In-memory store for alarm lifecycle data.

    This store maintains:
    - a list of alarm events (RAISED, UPDATED, CLEARED)
    - the current state of each alarm keyed by AlarmId

    Notes
    -----
    - This store is intentionally simple and not thread-safe.
      Synchronization is handled by the enclosing `StateStore`.
    - Setting a state for an existing AlarmId overwrites the previous state.
    """

    events: List[AlarmEvent] = field(default_factory=list)
    states: Dict[AlarmId, AlarmState] = field(default_factory=dict)

    def add_event(self, event: AlarmEvent) -> None:
        """
        Append an alarm event to the event history.

        Parameters
        ----------
        event
            AlarmEvent to add.
        """
        self.events.append(event)

    def set_state(self, alarm_id: AlarmId, state: AlarmState) -> None:
        """
        Set or overwrite the current state for an alarm.

        Parameters
        ----------
        alarm_id
            Identifier of the alarm.
        state
            Current AlarmState.
        """
        self.states[alarm_id] = state

    def active_states(self) -> List[AlarmState]:
        """
        Return only currently active alarm states.

        Returns
        -------
        list of AlarmState
            Alarm states where ``active`` is True.
        """
        return [s for s in self.states.values() if s.active]

    def clear(self) -> None:
        """
        Clear all stored alarm events and alarm states.

        """
        self.events.clear()
        self.states.clear()
