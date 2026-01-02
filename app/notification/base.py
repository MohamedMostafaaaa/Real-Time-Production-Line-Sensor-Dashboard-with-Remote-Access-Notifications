from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol


@dataclass(frozen=True)
class NotificationEvent:
    """
    Notification event contract used by the notification layer.

    A 'NotificationEvent' is a transport message that can be sent to 
    one or more notifiers. It represents *what should be communicated*, 
    not *how* it is delivered.

    Parameters
    ----------
    type
        Event type identifier (e.g., "alarm_report", "alarm_raised", "status").
    payload
        Arbitrary structured payload containing event data. This is intentionally
        flexible to support different notifier implementations.
    severity
        Optional severity label (e.g., "WARNING", "CRITICAL").
    source
        Optional source identifier (e.g., sensor name, subsystem).
    ts
        Optional timestamp string describing when the event occurred.

    Notes
    -----
    The class is frozen (immutable) so events remain stable once created,
    supporting safe logging and auditability.
    """

    type: str
    payload: Dict[str, Any]
    severity: Optional[str] = None
    source: Optional[str] = None
    ts: Optional[str] = None


class Notifier(Protocol):
    """
    Protocol interface for notification delivery.

    Any notifier implementation can be used if it provides a 'notify(event)'
    method with the correct signature. This enables dependency inversion and
    makes notification dispatch easy to test with fakes/mocks.

    Methods
    -------
    notify(event)
        Deliver a notification event.
    """

    def notify(self, event: NotificationEvent) -> None:
        """
        Deliver a notification event.

        Parameters
        ----------
        event
            The notification event to deliver.
        """
        ...
