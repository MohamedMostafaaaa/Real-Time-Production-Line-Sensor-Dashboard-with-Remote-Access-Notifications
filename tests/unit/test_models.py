"""
Unit tests for app.domain.models.

These tests verify:
- Enum stability (required members exist and preserve expected values)
- Dataclass immutability (frozen models)
- Basic domain invariants (timestamp ordering, default statuses)

The goal is to validate domain contracts used across the engine, criteria, and UI.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta

import pytest

from app.domain.models import (
    AlarmSeverity,
    AlarmState,
    AlarmType,
    FtirSensorReading,
    MaterialType,
    SensorConfig,
    SensorReading,
    SensorStatus,
)


def test_sensor_status_enum_values() -> None:
    """
    Ensure SensorStatus members and values are stable.

    These values are commonly used across UI/logging and should not change
    silently without intent.
    """
    assert SensorStatus.OK.value == "OK"
    assert SensorStatus.FAULTY.value == "FAULTY"



def test_alarm_type_enum_members_exist() -> None:
    """
    Verify AlarmType includes the expected rule categories.

    Alarm criteria and UI rely on these categories being present.
    """
    assert AlarmType.LOW_LIMIT.value == "LOW_LIMIT"
    assert AlarmType.HIGH_LIMIT.value == "HIGH_LIMIT"
    assert AlarmType.WAVELENGTH_SHIFT.value == "WAVELENGTH_SHIFT"
    assert AlarmType.DIFF_BETWEEN_TEMP_SENSORS.value == "DIFF_BETWEEN_TEMP_SENSORS"


def test_alarm_severity_enum_values() -> None:
    """
    Ensure AlarmSeverity members and values are stable.
    """
    assert AlarmSeverity.WARNING.value == "WARNING"
    assert AlarmSeverity.CRITICAL.value == "CRITICAL"


def test_sensor_config_is_frozen() -> None:
    """
    Ensure SensorConfig is immutable.

    Configuration should be treated as a value object (safe to share).
    """
    cfg = SensorConfig(name="Pressure", units="bar", low_limit=1.0, high_limit=10.0)
    with pytest.raises(FrozenInstanceError):
        cfg.low_limit = 0.5  # type: ignore[misc]


def test_sensor_reading_defaults_and_immutability() -> None:
    """
    Validate SensorReading defaults and immutability.

    - status defaults to OK
    - dataclass is frozen
    """
    r = SensorReading(sensor="Pressure", value=5.0, timestamp=datetime(2026, 1, 1))
    assert r.status is SensorStatus.OK

    with pytest.raises(FrozenInstanceError):
        r.value = 6.0  # type: ignore[misc]


def test_ftir_sensor_reading_defaults_and_immutability() -> None:
    """
    Validate FtirSensorReading defaults and immutability.

    - status defaults to OK
    - values accept sequences (list/tuple)
    - dataclass is frozen
    """
    ft = FtirSensorReading(sensor="FTIR", values=[1.0, 2.0, 3.0], timestamp=datetime(2026, 1, 1))
    assert ft.status is SensorStatus.OK
    assert list(ft.values) == [1.0, 2.0, 3.0]

    with pytest.raises(FrozenInstanceError):
        ft.sensor = "FTIR2"  # type: ignore[misc]


def test_alarm_state_basic_invariants() -> None:
    """
    Validate basic AlarmState invariants.

    This test checks that the model supports expected usage:
    - first_seen is not after last_seen (common invariant in state updates)
    - last_value is optional
    """
    t0 = datetime(2026, 1, 1, 10, 0, 0)
    t1 = t0 + timedelta(seconds=5)

    st = AlarmState(
        source="S1",
        alarm_type=AlarmType.WAVELENGTH_SHIFT,
        alarm_severity=AlarmSeverity.CRITICAL,
        active=True,
        first_seen=t0,
        last_seen=t1,
        message="shift detected",
        last_value=1.23,
    )

    assert st.first_seen <= st.last_seen
    assert st.last_value == 1.23

    with pytest.raises(FrozenInstanceError):
        st.active = False  # type: ignore[misc]
