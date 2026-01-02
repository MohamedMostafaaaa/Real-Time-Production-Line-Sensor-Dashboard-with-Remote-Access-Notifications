"""
Unit tests for app.core.alarm.alarms_criteria.

These tests validate the behavior of the stateless criteria evaluators:
- ScalarLimitCriteria
- TempDiffCriteria
- FtirPeakShiftCriteria

The tests use lightweight fake store objects that mimic the minimal store
interfaces used by the criteria helpers:
- get_latest / snapshots for scalar readings
- get_latest_ftir / ftir_snapshots for FTIR readings
- scalar_configs / configs for configuration discovery

The goal is to test rule logic deterministically without involving the engine,
threads, UI, or real I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import pytest

from app.core.alarm.alarm_base import AlarmContext
from app.core.alarm.alarms_criteria import FtirPeakShiftCriteria, ScalarLimitCriteria, TempDiffCriteria
from app.domain.models import (
    AlarmSeverity,
    AlarmType,
    FtirSensorReading,
    SensorConfig,
    SensorReading,
    SensorStatus,
)
from app.domain.spectrum_axis import WAVELENGTH_AXIS_DESC


@dataclass
class FakeStore:
    """
    Minimal store test double for criteria evaluation.

    Attributes
    ----------
    scalar_configs
        List of scalar sensor configs used by ScalarLimitCriteria.
    snapshots
        Mapping from sensor name to latest SensorReading.
    ftir_snapshots
        Mapping from sensor name to latest FtirSensorReading.
    """

    scalar_configs: List[SensorConfig]
    snapshots: Dict[str, SensorReading]
    ftir_snapshots: Dict[str, FtirSensorReading]

    def get_latest(self, sensor: str) -> Optional[SensorReading]:
        """Return the latest scalar reading for a sensor."""
        return self.snapshots.get(sensor)

    def get_latest_ftir(self, sensor: str) -> Optional[FtirSensorReading]:
        """Return the latest FTIR reading for a sensor."""
        return self.ftir_snapshots.get(sensor)


def _ctx(ts: datetime | None = None) -> AlarmContext:
    """
    Create a consistent AlarmContext for tests.

    Parameters
    ----------
    ts
        Optional explicit timestamp.

    Returns
    -------
    AlarmContext
        Context used by criteria.
    """
    return AlarmContext(now=ts or datetime(2026, 1, 1, 0, 0, 0))


def test_scalar_limit_criteria_emits_low_and_high_decisions() -> None:
    """
    ScalarLimitCriteria should emit two decisions per configured sensor:
    - LOW_LIMIT
    - HIGH_LIMIT

    It should set should_be_active based on the configured thresholds.
    """
    cfg = SensorConfig(name="Pressure", units="bar", low_limit=1.0, high_limit=10.0)

    store = FakeStore(
        scalar_configs=[cfg],
        snapshots={
            "Pressure": SensorReading(sensor="Pressure", value=0.5, timestamp=_ctx().now, status=SensorStatus.OK)
        },
        ftir_snapshots={},
    )

    crit = ScalarLimitCriteria()
    decisions = list(crit.evaluate(store, _ctx()))

    assert len(decisions) == 2

    low = next(d for d in decisions if d.alarm_id.alarm_type is AlarmType.LOW_LIMIT)
    high = next(d for d in decisions if d.alarm_id.alarm_type is AlarmType.HIGH_LIMIT)

    assert low.severity is AlarmSeverity.WARNING
    assert low.should_be_active is True
    assert "LOW" in low.message

    assert high.severity is AlarmSeverity.WARNING
    assert high.should_be_active is False


def test_scalar_limit_criteria_skips_faulty_readings() -> None:
    """
    ScalarLimitCriteria should ignore readings with status != OK.
    """
    cfg = SensorConfig(name="Pressure", units="bar", low_limit=1.0, high_limit=10.0)

    store = FakeStore(
        scalar_configs=[cfg],
        snapshots={
            "Pressure": SensorReading(sensor="Pressure", value=0.5, timestamp=_ctx().now, status=SensorStatus.FAULTY)
        },
        ftir_snapshots={},
    )

    crit = ScalarLimitCriteria()
    decisions = list(crit.evaluate(store, _ctx()))

    assert decisions == []


def test_temp_diff_criteria_active_and_inactive() -> None:
    """
    TempDiffCriteria should emit a decision when both readings exist and are OK.

    - active when abs(lower-upper) > max_delta
    - inactive otherwise
    """
    store = FakeStore(
        scalar_configs=[],
        snapshots={
            "TLOW": SensorReading(sensor="TLOW", value=20.0, timestamp=_ctx().now),
            "TUP": SensorReading(sensor="TUP", value=30.5, timestamp=_ctx().now),
        },
        ftir_snapshots={},
    )

    crit = TempDiffCriteria(sensor_lower="TLOW", sensor_upper="TUP", max_delta=3.0)
    decisions = list(crit.evaluate(store, _ctx()))
    assert len(decisions) == 1
    assert decisions[0].alarm_id.alarm_type is AlarmType.DIFF_BETWEEN_TEMP_SENSORS
    assert decisions[0].should_be_active is True

    # Now make the readings close enough -> inactive
    store.snapshots["TUP"] = SensorReading(sensor="TUP", value=21.0, timestamp=_ctx().now)
    decisions2 = list(crit.evaluate(store, _ctx()))
    assert len(decisions2) == 1
    assert decisions2[0].should_be_active is False


def test_temp_diff_criteria_skips_missing_or_faulty() -> None:
    """
    TempDiffCriteria should emit no decisions if:
    - any reading is missing, or
    - any reading is not OK.
    """
    store_missing = FakeStore(
        scalar_configs=[],
        snapshots={"TLOW": SensorReading(sensor="TLOW", value=20.0, timestamp=_ctx().now)},
        ftir_snapshots={},
    )
    crit = TempDiffCriteria(sensor_lower="TLOW", sensor_upper="TUP")
    assert list(crit.evaluate(store_missing, _ctx())) == []

    store_faulty = FakeStore(
        scalar_configs=[],
        snapshots={
            "TLOW": SensorReading(sensor="TLOW", value=20.0, timestamp=_ctx().now, status=SensorStatus.FAULTY),
            "TUP": SensorReading(sensor="TUP", value=20.5, timestamp=_ctx().now, status=SensorStatus.OK),
        },
        ftir_snapshots={},
    )
    assert list(crit.evaluate(store_faulty, _ctx())) == []


def test_ftir_peak_shift_length_mismatch_emits_critical_active() -> None:
    """
    If require_length_match is True and spectrum length != axis length,
    FtirPeakShiftCriteria should emit a CRITICAL active decision and return.
    """
    axis = list(WAVELENGTH_AXIS_DESC)
    y = [1.0] * (len(axis) - 5)  # intentional mismatch

    store = FakeStore(
        scalar_configs=[],
        snapshots={},
        ftir_snapshots={
            "FTIR": FtirSensorReading(sensor="FTIR", values=y, timestamp=_ctx().now, status=SensorStatus.OK)
        },
    )

    crit = FtirPeakShiftCriteria(
        sensor_name="FTIR",
        expected_peaks_nm=[axis[len(axis) // 2]],
        max_allowed_shift_nm=[1.0],
        require_length_match=True,
    )

    decisions = list(crit.evaluate(store, _ctx()))
    assert len(decisions) == 1
    d = decisions[0]
    assert d.severity is AlarmSeverity.CRITICAL
    assert d.should_be_active is True
    assert "length mismatch" in d.message


def test_ftir_peak_shift_ok_when_dips_at_expected_locations() -> None:
    """
    FtirPeakShiftCriteria should be inactive when all dips are found within
    the allowed shift thresholds.
    """
    axis = list(map(float, WAVELENGTH_AXIS_DESC))
    y = [1.0] * len(axis)

    # Pick two "expected" wavelengths directly from the axis so they are findable.
    i1 = len(axis) // 3
    i2 = 2 * len(axis) // 3
    expected = [axis[i1], axis[i2]]

    # Create dips exactly at those indices.
    y[i1] = 0.0
    y[i2] = 0.0

    store = FakeStore(
        scalar_configs=[],
        snapshots={},
        ftir_snapshots={"FTIR": FtirSensorReading(sensor="FTIR", values=y, timestamp=_ctx().now)},
    )

    crit = FtirPeakShiftCriteria(
        sensor_name="FTIR",
        expected_peaks_nm=expected,
        max_allowed_shift_nm=[2.0, 2.0],  # generous
        search_window_nm=12.0,
        require_length_match=True,
    )

    decisions = list(crit.evaluate(store, _ctx()))
    assert len(decisions) == 1
    assert decisions[0].should_be_active is False
    assert "OK" in decisions[0].message


def test_ftir_peak_shift_active_when_dip_shift_exceeds_threshold() -> None:
    """
    FtirPeakShiftCriteria should become active when a dip is found but its
    shift from the expected peak exceeds the allowed threshold.
    """
    axis = list(map(float, WAVELENGTH_AXIS_DESC))
    y = [1.0] * len(axis)

    # Choose an expected peak from the axis
    i_expected = len(axis) // 2
    expected_nm = axis[i_expected]

    # Place a dip a few indices away within the search window
    # to simulate a shift.
    i_shifted = min(len(axis) - 2, i_expected + 5)
    y[i_shifted] = 0.0

    store = FakeStore(
        scalar_configs=[],
        snapshots={},
        ftir_snapshots={"FTIR": FtirSensorReading(sensor="FTIR", values=y, timestamp=_ctx().now)},
    )

    crit = FtirPeakShiftCriteria(
        sensor_name="FTIR",
        expected_peaks_nm=[expected_nm],
        max_allowed_shift_nm=[0.1],  # very strict
        search_window_nm=100.0,      # ensure we can still find the shifted dip
        require_length_match=True,
    )

    decisions = list(crit.evaluate(store, _ctx()))
    assert len(decisions) == 1
    assert decisions[0].severity is AlarmSeverity.CRITICAL
    assert decisions[0].should_be_active is True
    assert "shifted" in decisions[0].message or "Δ=" in decisions[0].message
