from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List


class SensorStatus(str, Enum):
    """
    Operational status of a sensor reading.

    This status indicates whether a sensor reading is valid (`OK`) or should be
    treated as faulty (`FAULTY`). It applies to both scalar and spectrum sensors.

    Members
    -------
    OK
        The sensor is operating normally.
    FAULTY
        The sensor is experiencing a fault or an error.
    """

    OK = "OK"
    FAULTY = "FAULTY"


@dataclass(frozen=True)
class SensorConfig:
    """
    Configuration for a scalar sensor channel.

    Parameters
    ----------
    name
        Name of the sensor channel (e.g., ``"TempLowerMSP"``, ``"Pressure"``).
    units
        Measurement units of the sensor (e.g., ``"C"``, ``"bar"``).
    low_limit
        Lower operating limit of the sensor.
    high_limit
        Upper operating limit of the sensor.
    """

    name: str
    units: str
    low_limit: float
    high_limit: float


@dataclass(frozen=True)
class SensorReading:
    """
    Scalar sensor reading (temperature, pressure, vibration, ...).

    Parameters
    ----------
    sensor
        Name of the sensor channel.
    value
        Scalar measured value.
    timestamp
        Timestamp when the reading was taken.
    status
        Operational status of the reading.

    Notes
    -----
    Scalar readings are separated from spectrum readings because spectrum sensors
    produce a vector of values (e.g., absorbance vs wavelength index).
    """

    sensor: str
    value: float
    timestamp: datetime
    status: SensorStatus = SensorStatus.OK


@dataclass(frozen=True)
class FtirSensorReading:
    """
    Fixed-length spectrum reading.

    Parameters
    ----------
    sensor
        Name of the spectrum sensor channel.
    values
        Spectrum sample values (fixed-length list).
    timestamp
        Timestamp when the reading was taken.
    status
        Operational status of the reading.
    """

    sensor: str
    values: List[float]
    timestamp: datetime
    status: SensorStatus = SensorStatus.OK
