from __future__ import annotations

from datetime import datetime
from typing import List, Tuple

from app.core.state_store import StateStore
from app.domain.events import AlarmEvent

SensorRow = Tuple[str, str, str, str]
AlarmRow = Tuple[str, str, str, str, str]


def _sensor_alarm_level(store: StateStore, sensor_name: str) -> str:
    """
    Returns effective status for UI based on active alarms:
    OK / WARNING / CRITICAL
    """
    # find active alarms belonging to this sensor
    active = [
        st for st in store.alarm_states.values()
        if st.active and (st.source == sensor_name or st.source.startswith(sensor_name))
    ]
    if not active:
        return "OK"

    # CRITICAL if any critical else WARNING
    for st in active:
        sev = st.alarm_severity.value if hasattr(st.alarm_severity, "value") else str(st.alarm_severity)
        if sev == "CRITICAL":
            return "CRITICAL"
    return "WARNING"

def sensor_rows(store: StateStore) -> List[SensorRow]:
    rows: List[SensorRow] = []

    # scalar snapshots
    for name, reading in store.snapshots.items():
        status_text = _sensor_alarm_level(store, name)
        rows.append(
            (
                name,
                f"{reading.value:.3f}",
                reading.timestamp.strftime("%H:%M:%S"),
                status_text,
            )
        )

    # FTIR snapshot as a row (also uses alarm status)
    for name, reading in store.ftir_snapshots.items():
        status_text = _sensor_alarm_level(store, name)
        rows.append(
            (
                name,
                f"[{len(reading.values)} pts] ",
                reading.timestamp.strftime("%H:%M:%S"),
                status_text,
            )
        )

    rows.sort(key=lambda r: r[0])
    return rows


def alarm_rows(store: StateStore, limit: int = 200) -> List[AlarmRow]:
    rows: List[AlarmRow] = []
    for e in reversed(store.alarm_events[-limit:]):
        rows.append(
            (
                e.timestamp.strftime("%H:%M:%S"),
                e.source,
                "" if e.value is None else f"{e.value:.3f}",
                e.alarm_type.value if hasattr(e.alarm_type, "value") else str(e.alarm_type),
                e.message,
            )
        )
    return rows

def active_alarm_rows(store: StateStore, limit: int = 200) -> List[AlarmRow]:
    """
    Build rows from AlarmState (only active alarms), newest update first.
    """
    active = [a for a in store.alarm_states.values() if a.active]
    active.sort(key=lambda a: a.last_seen, reverse=True)

    rows: List[AlarmRow] = []
    for a in active[:limit]:
        rows.append(
            (
                a.last_seen.strftime("%H:%M:%S"),
                a.source,
                "" if a.last_value is None else f"{a.last_value:.3f}",
                a.alarm_type.value if hasattr(a.alarm_type, "value") else str(a.alarm_type),
                a.message,
            )
        )
    return rows