"""
Alarm event domain models.

This module defines the event-level representation of alarm lifecycle changes.
An `AlarmEvent` represents *what happened* at a specific time, while
`AlarmState` (in models.py) represents *what is currently true*.

Events are typically used for:
- logging and audit trails
- UI notification streams
- reporting and post-analysis
"""

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
    RAISED : str
        Alarm became active.
    CLEARED : str
        Alarm returned to normal / became inactive.
    UPDATED : str
        Alarm remained active but was updated (new value or message).
    """

    RAISED = "RAISED"
    CLEARED = "CLEARED"
    UPDATED = "UPDATED"


@dataclass(frozen=True)
class AlarmEvent:
    """
    Alarm event emitted when an alarm transitions.

    'AlarmEvent' captures *what changed* and *when*, and is intentionally
    immutable so it can be safely logged, stored, or transmitted.

    Parameters
    ----------
    source
        Sensor or subsystem responsible for the alarm.
    alarm_type
        Category/type of alarm.
    severity
        Severity level at the time of the transition.
    transition
        Lifecycle transition (RAISED, CLEARED, UPDATED).
    timestamp
        Timestamp when the transition occurred.
    message
        Human-readable description (used in UI/logs).
    value
        Optional numeric value associated with the event.
    details
        Optional extra context (useful for complex alarms such as spectral rules).
    """

    source: str
    alarm_type: AlarmType
    severity: AlarmSeverity
    transition: AlarmTransition
    timestamp: datetime
    message: str
    value: Optional[float] = None
    details: Optional[str] = None
