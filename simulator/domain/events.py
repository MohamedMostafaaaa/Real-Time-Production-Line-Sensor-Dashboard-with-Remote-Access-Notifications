from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from app.domain.models import AlarmSeverity, AlarmType


class AlarmTransition(str, Enum):
    """
    Alarm lifecycle transition.

    Members
    -------
    RAISED
        Alarm became active.
    CLEARED
        Alarm returned to normal / became inactive.
    UPDATED
        Alarm remained active but was updated (new value/message).
    """

    RAISED = "RAISED"
    CLEARED = "CLEARED"
    UPDATED = "UPDATED"


@dataclass(frozen=True)
class AlarmEvent:
    """
    Alarm event emitted when an alarm transitions (raised/cleared/updated).

    Parameters
    ----------
    source
        Sensor or subsystem responsible for the alarm.
    alarm_type
        Category/type of alarm.
    severity
        Severity level.
    transition
        Lifecycle transition (raised/cleared/updated).
    timestamp
        When the transition occurred.
    message
        Human-readable description for UI/logs.
    value
        Optional numeric value associated with the event (if applicable).
    details
        Optional extra context (useful for spectral alarms).
    """

    source: str
    alarm_type: AlarmType
    severity: AlarmSeverity
    transition: AlarmTransition
    timestamp: datetime
    message: str
    value: Optional[float] = None
    details: Optional[str] = None
