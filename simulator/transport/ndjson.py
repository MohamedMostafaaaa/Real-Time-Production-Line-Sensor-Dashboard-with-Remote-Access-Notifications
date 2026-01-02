from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict

from simulator.domain.models import FtirSensorReading, SensorReading
from simulator.sensors.base import SimMessage


def _dt_to_str(dt: datetime) -> str:
    """
    Convert a datetime into an ISO-8601 string.

    Parameters
    ----------
    dt
        Datetime to serialize.

    Returns
    -------
    str
        ISO-8601 formatted timestamp string.
    """
    return dt.isoformat()


def encode_message(msg: SimMessage) -> str:
    """
    Encode a simulator message into a JSON string (NDJSON payload).

    The simulator transport stream uses NDJSON (newline-delimited JSON). This
    function encodes a single message object into one JSON object string.
    The caller is responsible for appending a trailing newline.

    Parameters
    ----------
    msg
        Message to serialize. Supported types are:
        - :class:`~simulator.domain.models.SensorReading`
        - :class:`~simulator.domain.models.FtirSensorReading`

    Returns
    -------
    str
        JSON string representing the message object.

    Raises
    ------
    TypeError
        If `msg` is not a supported message type.

    Notes
    -----
    The output payload uses a `"type"` field:
    - `"sensor_reading"` for scalar readings
    - `"ftir_spectrum"` for spectrum readings

    The `"status"` field is serialized as a string. If `status` is an Enum,
    its `.value` is used.
    """
    if isinstance(msg, SensorReading):
        payload: Dict[str, Any] = {
            "type": "sensor_reading",
            "sensor": msg.sensor,
            "value": msg.value,
            "timestamp": _dt_to_str(msg.timestamp),
            "status": msg.status.value if hasattr(msg.status, "value") else msg.status,
        }
        return json.dumps(payload)

    if isinstance(msg, FtirSensorReading):
        payload = {
            "type": "ftir_spectrum",
            "sensor": msg.sensor,
            "values": list(msg.values),
            "timestamp": _dt_to_str(msg.timestamp),
            "status": msg.status.value if hasattr(msg.status, "value") else msg.status,
        }
        return json.dumps(payload)

    raise TypeError(f"Unsupported message type: {type(msg)}")
