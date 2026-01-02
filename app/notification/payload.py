from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any, Dict

from app.core.state_store import StateStore
from app.domain.events import AlarmEvent


def _iso(ts: datetime) -> str:
    """
    Convert datetime to ISO-8601 string with second precision.

    Parameters
    ----------
    ts
        Timestamp to convert.

    Returns
    -------
    str
        ISO-8601 formatted timestamp (seconds precision).
    """
    return ts.isoformat(timespec="seconds")


def build_alarm_webhook_payload(store: StateStore, ev: AlarmEvent) -> Dict[str, Any]:
    """
    Build a webhook payload for an alarm event plus current store totals.

    The payload includes:
    - "event": the alarm event fields required by downstream consumers
    - "totals": snapshot counters computed from:
      - current alarm states (store.alarm_states)
      - alarm event history (store.alarm_events)

    Parameters
    ----------
    store
        Application state store used to read current alarm states and event history.
    ev
        Alarm event that triggered the webhook.

    Returns
    -------
    dict
        Webhook payload dictionary with keys: "type", "event", and "totals".
    """
    # ---- totals snapshot from store ----
    states = list(store.alarm_states.values())  # current state per alarm_id
    events = list(store.alarm_events)           # history list

    total_states = len(states)
    active_states = sum(1 for s in states if getattr(s, "active", False))

    # current state breakdowns
    states_by_severity = Counter(getattr(s, "alarm_severity", "UNKNOWN") for s in states)
    states_by_type = Counter(getattr(s, "alarm_type", "UNKNOWN") for s in states)

    # history breakdowns
    events_by_transition = Counter(getattr(e, "transition", "UNKNOWN") for e in events)
    events_by_severity = Counter(getattr(e, "severity", "UNKNOWN") for e in events)
    events_by_type = Counter(getattr(e, "alarm_type", "UNKNOWN") for e in events)

    # ---- event payload (exact requested fields) ----
    event_payload = {
        "source": ev.source,
        "alarm_type": str(ev.alarm_type),
        "severity": str(ev.severity),
        "transition": str(ev.transition),
        "timestamp": _iso(ev.timestamp),
        "message": ev.message,
        "value": ev.value,
        "details": ev.details,
    }

    totals_payload = {
        "alarm_states_total": total_states,
        "alarm_states_active": active_states,
        "alarm_events_total": len(events),
        "state_counts_by_severity": {str(k): int(v) for k, v in states_by_severity.items()},
        "state_counts_by_type": {str(k): int(v) for k, v in states_by_type.items()},
        "event_counts_by_transition": {str(k): int(v) for k, v in events_by_transition.items()},
        "event_counts_by_severity": {str(k): int(v) for k, v in events_by_severity.items()},
        "event_counts_by_type": {str(k): int(v) for k, v in events_by_type.items()},
    }

    return {
        "type": "alarm_event",
        "event": event_payload,
        "totals": totals_payload,
    }
