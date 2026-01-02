from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Iterator, Union

from app.domain.models import FtirSensorReading, SensorReading, SensorStatus


def _str_to_dt(s: str) -> datetime:
    """
    Convert an ISO-8601 datetime string to a datetime object.

    Parameters
    ----------
    s
        Datetime string in ISO format (e.g., "2026-01-01T10:00:00").

    Returns
    -------
    datetime
        Parsed datetime instance.

    Raises
    ------
    ValueError
        If the input is not a valid ISO formatted datetime string.
    """
    return datetime.fromisoformat(s)


def _decode_obj(obj: Dict[str, Any]) -> Union[SensorReading, FtirSensorReading]:
    """
    Decode a message dictionary into a domain reading object.

    Supported message types
    -----------------------
    - ``type="sensor_reading"`` -> :class:`~app.domain.models.SensorReading`
    - ``type="ftir_spectrum"``  -> :class:`~app.domain.models.FtirSensorReading`

    Parameters
    ----------
    obj
        JSON-decoded dictionary that must contain a ``type`` field.

    Returns
    -------
    SensorReading or FtirSensorReading
        Decoded domain object.

    Raises
    ------
    KeyError
        If required fields for a given message type are missing.
    ValueError
        If ``type`` is unknown or if field conversions fail.
    """
    t = obj.get("type")

    if t == "sensor_reading":
        return SensorReading(
            sensor=str(obj["sensor"]),
            value=float(obj["value"]),
            timestamp=_str_to_dt(str(obj["timestamp"])),
            status=SensorStatus(obj.get("status", "OK")),
        )

    if t == "ftir_spectrum":
        return FtirSensorReading(
            sensor=str(obj["sensor"]),
            values=list(obj["values"]),
            timestamp=_str_to_dt(str(obj["timestamp"])),
            status=SensorStatus(obj.get("status", "OK")),
        )

    raise ValueError(f"Unknown message type: {t}")


def iter_json_objects(text: str) -> Iterator[Dict[str, Any]]:
    """
    Yield one or more JSON objects found in a string.

    This function is robust against inputs where multiple JSON objects are
    accidentally concatenated without delimiters, e.g.::

        '{"a": 1}{"b": 2}'

    Only dictionary objects are yielded (non-dict JSON like lists/strings are ignored).

    Parameters
    ----------
    text
        Input string potentially containing one or more JSON objects.

    Yields
    ------
    dict
        Parsed JSON objects (dictionaries) found in the input.

    Notes
    -----
    - This is transport-level parsing; it does not validate the schema beyond
      JSON decoding.
    - If the string is empty/whitespace, nothing is yielded.
    """
    s = text.strip()
    if not s:
        return

    dec = json.JSONDecoder()
    i = 0
    n = len(s)

    while i < n:
        while i < n and s[i].isspace():
            i += 1
        if i >= n:
            break

        obj, end = dec.raw_decode(s, i)
        if isinstance(obj, dict):
            yield obj
        i = end


def decode_message(line: str) -> Union[SensorReading, FtirSensorReading]:
    """
    Decode an NDJSON line into a domain object.

    Robustness behavior
    -------------------
    If the sender mistakenly concatenates multiple JSON objects into a single
    line, this function decodes and returns the **first valid JSON object**
    found.

    Parameters
    ----------
    line
        Input line containing one (or more concatenated) JSON objects.

    Returns
    -------
    SensorReading or FtirSensorReading
        Decoded domain object.

    Raises
    ------
    ValueError
        If no JSON object is found or if the message type is unknown.
    """
    for obj in iter_json_objects(line):
        return _decode_obj(obj)

    raise ValueError("No JSON object found in line")
