"""
Unit tests for app.core.state.reading_store.ReadingsStore.

These tests validate that ReadingsStore behaves as a snapshot store:
- last write wins per sensor key
- retrieval returns the stored reading or None if missing

Notes
-----
ReadingsStore does not enforce timestamp ordering. The tests reflect the
intended behavior ("last write wins").
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.core.state.reading_store import ReadingsStore
from app.domain.models import FtirSensorReading, SensorReading, SensorStatus


def test_update_and_get_latest_scalar_roundtrip() -> None:
    """
    Storing a scalar reading should make it retrievable via get_latest_scalar.
    """
    store = ReadingsStore()
    ts = datetime(2026, 1, 1, 10, 0, 0)

    r = SensorReading(sensor="Pressure", value=5.0, timestamp=ts, status=SensorStatus.OK)
    store.update_scalar(r)

    got = store.get_latest_scalar("Pressure")
    assert got is not None
    assert got.value == 5.0
    assert got.timestamp == ts


def test_scalar_last_write_wins_for_same_sensor_key() -> None:
    """
    Updating the same scalar sensor key should overwrite the previous snapshot.
    """
    store = ReadingsStore()
    t0 = datetime(2026, 1, 1, 10, 0, 0)
    t1 = t0 + timedelta(seconds=1)

    r0 = SensorReading(sensor="Pressure", value=5.0, timestamp=t0)
    r1 = SensorReading(sensor="Pressure", value=6.0, timestamp=t1)

    store.update_scalar(r0)
    store.update_scalar(r1)

    got = store.get_latest_scalar("Pressure")
    assert got is not None
    assert got.value == 6.0
    assert got.timestamp == t1


def test_get_latest_scalar_missing_returns_none() -> None:
    """
    Requesting an unknown scalar sensor should return None.
    """
    store = ReadingsStore()
    assert store.get_latest_scalar("Unknown") is None


def test_update_and_get_latest_spectrum_roundtrip() -> None:
    """
    Storing an FTIR reading should make it retrievable via get_latest_spectrum.
    """
    store = ReadingsStore()
    ts = datetime(2026, 1, 1, 10, 0, 0)

    ft = FtirSensorReading(sensor="FTIR", values=[1.0, 2.0, 3.0], timestamp=ts, status=SensorStatus.OK)
    store.update_spectrum(ft)

    got = store.get_latest_spectrum("FTIR")
    assert got is not None
    assert list(got.values) == [1.0, 2.0, 3.0]
    assert got.timestamp == ts


def test_spectrum_last_write_wins_for_same_sensor_key() -> None:
    """
    Updating the same FTIR sensor key should overwrite the previous snapshot.
    """
    store = ReadingsStore()
    t0 = datetime(2026, 1, 1, 10, 0, 0)
    t1 = t0 + timedelta(seconds=1)

    ft0 = FtirSensorReading(sensor="FTIR", values=[1.0, 2.0], timestamp=t0)
    ft1 = FtirSensorReading(sensor="FTIR", values=[9.0, 9.0], timestamp=t1)

    store.update_spectrum(ft0)
    store.update_spectrum(ft1)

    got = store.get_latest_spectrum("FTIR")
    assert got is not None
    assert list(got.values) == [9.0, 9.0]
    assert got.timestamp == t1


def test_get_latest_spectrum_missing_returns_none() -> None:
    """
    Requesting an unknown FTIR sensor should return None.
    """
    store = ReadingsStore()
    assert store.get_latest_spectrum("UnknownFTIR") is None
