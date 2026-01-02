"""
Unit tests for app.transport.ndjson.

These tests validate pure transport parsing behavior:
- iter_json_objects can parse concatenated JSON objects safely
- decode_message converts NDJSON strings to the correct domain objects
- default handling (status defaults to OK)
- error handling for unknown message types and empty inputs

No network I/O is involved; tests are fully deterministic.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from app.domain.models import FtirSensorReading, SensorReading, SensorStatus
from app.transport.ndjson import decode_message, iter_json_objects


def test_iter_json_objects_parses_single_object() -> None:
    """
    iter_json_objects should yield a dict when input contains one JSON object.
    """
    objs = list(iter_json_objects('{"a": 1, "b": 2}'))
    assert objs == [{"a": 1, "b": 2}]


def test_iter_json_objects_parses_concatenated_objects() -> None:
    """
    iter_json_objects should parse concatenated JSON objects without delimiters.
    """
    text = '{"a": 1}{"b": 2}{"c": 3}'
    objs = list(iter_json_objects(text))
    assert objs == [{"a": 1}, {"b": 2}, {"c": 3}]


def test_iter_json_objects_ignores_non_dict_json() -> None:
    """
    iter_json_objects should only yield dictionary objects.

    Lists/strings/numbers should be ignored even if they decode successfully.
    """
    text = '[1,2,3]{"a": 1}"x"{"b": 2}'
    objs = list(iter_json_objects(text))
    assert objs == [{"a": 1}, {"b": 2}]


def test_decode_message_sensor_reading_defaults_status_ok() -> None:
    """
    decode_message should decode a sensor_reading and default status to OK.
    """
    line = (
        '{"type":"sensor_reading","sensor":"Pressure","value":5.0,'
        '"timestamp":"2026-01-01T10:00:00"}'
    )
    msg = decode_message(line)
    assert isinstance(msg, SensorReading)
    assert msg.sensor == "Pressure"
    assert msg.value == 5.0
    assert msg.timestamp == datetime.fromisoformat("2026-01-01T10:00:00")
    assert msg.status is SensorStatus.OK


def test_decode_message_sensor_reading_with_status() -> None:
    """
    decode_message should decode an explicit status field for sensor_reading.
    """
    line = (
        '{"type":"sensor_reading","sensor":"Pressure","value":5.0,'
        '"timestamp":"2026-01-01T10:00:00","status":"FAULTY"}'
    )
    msg = decode_message(line)
    assert isinstance(msg, SensorReading)
    assert msg.status is SensorStatus.FAULTY


def test_decode_message_ftir_spectrum_defaults_status_ok() -> None:
    """
    decode_message should decode an ftir_spectrum and default status to OK.
    """
    line = (
        '{"type":"ftir_spectrum","sensor":"FTIR","values":[1,2,3],'
        '"timestamp":"2026-01-01T10:00:00"}'
    )
    msg = decode_message(line)
    assert isinstance(msg, FtirSensorReading)
    assert msg.sensor == "FTIR"
    assert list(msg.values) == [1, 2, 3]
    assert msg.timestamp == datetime.fromisoformat("2026-01-01T10:00:00")
    assert msg.status is SensorStatus.OK


def test_decode_message_robust_returns_first_object_if_concatenated() -> None:
    """
    If multiple JSON objects exist in a line, decode_message should decode the first.
    """
    line = (
        '{"type":"sensor_reading","sensor":"A","value":1,'
        '"timestamp":"2026-01-01T10:00:00"}'
        '{"type":"sensor_reading","sensor":"B","value":2,'
        '"timestamp":"2026-01-01T10:00:00"}'
    )
    msg = decode_message(line)
    assert isinstance(msg, SensorReading)
    assert msg.sensor == "A"
    assert msg.value == 1.0


def test_decode_message_unknown_type_raises() -> None:
    """
    decode_message should raise ValueError for unknown message types.
    """
    line = '{"type":"unknown","x":1,"timestamp":"2026-01-01T10:00:00"}'
    with pytest.raises(ValueError):
        decode_message(line)


def test_decode_message_no_json_found_raises() -> None:
    """
    decode_message should raise ValueError when input contains no JSON objects.
    """
    with pytest.raises(ValueError):
        decode_message("   \n  ")
