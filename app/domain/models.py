"""
Domain models and enums.

This module defines the core domain-level types used across the system:
- Sensor statuses, material types, alarm types and severities
- Scalar sensor configuration and readings
- FTIR sensor readings (fixed-length spectrum vector)
- AlarmState, which represents the current alarm status for UI/reporting

These are designed as immutable (frozen) dataclasses where appropriate to
support safe sharing across layers and threads.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Sequence


class SensorStatus(str, Enum):
    """
    Operational status of a sensor reading.

    This status is used for both scalar sensors and FTIR sensors.

    Members
    -------
    OK : str
        The sensor is operating normally.
    FAULTY : str
        The sensor is experiencing a fault or an error.
    """

    OK = "OK"
    FAULTY = "FAULTY"


class MaterialType(str, Enum):
    """
    Material being analyzed by the FTIR sensor.

    Members
    -------
    POLY : str
        Polyethylene material.
    MRC : str
        Multi-Resin Composite material.
    Noise : str
        No material is being tested (baseline/noise condition).
    """

    POLY = "POLY"
    MRC = "MRC"
    Noise = "Noise"


class AlarmType(str, Enum):
    """
    Category identifying the kind of rule violation that caused the alarm.

    Members
    -------
    LOW_LIMIT : str
        Scalar reading fell below the configured low limit.
    HIGH_LIMIT : str
        Scalar reading rose above the configured high limit.
    WAVELENGTH_SHIFT : str
        Peak wavelength in FTIR reading shifted beyond acceptable range.
    DIFF_BETWEEN_TEMP_SENSORS : str
        Difference between lower and upper MSP temperature sensors exceeded limit.
    """

    LOW_LIMIT = "LOW_LIMIT"
    HIGH_LIMIT = "HIGH_LIMIT"
    WAVELENGTH_SHIFT = "WAVELENGTH_SHIFT"
    DIFF_BETWEEN_TEMP_SENSORS = "DIFF_BETWEEN_TEMP_SENSORS"


class AlarmSeverity(str, Enum):
    """
    Severity level for alarms.

    Members
    -------
    WARNING : str
        Abnormal condition requiring attention.
    CRITICAL : str
        Severe condition requiring immediate intervention.
    """

    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class SensorConfig:
    """
    Configuration for a scalar sensor channel.

    Defines sensor channel metadata (name/units) and allowable operating limits
    that are typically used by alarm rules.

    Parameters
    ----------
    name
        Name of the sensor channel (e.g., "TempLowerMSP", "Pressure").
    units
        Measurement units (e.g., "C", "bar").
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
    Scalar sensor reading (temperature, pressure, etc.).

    Parameters
    ----------
    sensor
        Name of the sensor channel.
    value
        The scalar measured value.
    timestamp
        Timestamp when the reading was captured.
    status
        Operational status of the reading.

    Notes
    -----
    Scalar readings are kept separate from FTIR readings. FTIR readings contain
    multiple points (a spectrum vector), while scalar readings are single values.
    """

    sensor: str
    value: float
    timestamp: datetime
    status: SensorStatus = SensorStatus.OK


@dataclass(frozen=True)
class FtirSensorReading:
    """
    Fixed-length FTIR sensor reading.

    Parameters
    ----------
    sensor
        Name of the FTIR sensor channel.
    values
        Spectrum vector (fixed length) representing absorbance/intensity values.
    timestamp
        Timestamp when the reading was captured.
    status
        Operational status of the reading.
    """

    sensor: str
    values: Sequence[float]
    timestamp: datetime
    status: SensorStatus = SensorStatus.OK


@dataclass(frozen=True)
class AlarmState:
    """
    Current state of an alarm for fast UI queries and reporting.

    'AlarmState' represents "what is true now" (active/inactive), while an
    event model (e.g., AlarmEvent) represents "what happened" (raised/updated/cleared).

    Parameters
    ----------
    source
        Sensor/subsystem responsible for the alarm (e.g., "TempLowerMSP").
    alarm_type
        Category/type of the alarm condition.
    alarm_severity
        Severity level of the alarm.
    active
        Whether the alarm is currently active.
    first_seen
        Timestamp when the alarm was first observed active.
    last_seen
        Timestamp of the most recent evaluation/update for this alarm.
    message
        Latest human-readable alarm message.
    last_value
        Optional latest numeric value associated with the alarm.
    """

    source: str
    alarm_type: AlarmType
    alarm_severity: AlarmSeverity
    active: bool
    first_seen: datetime
    last_seen: datetime
    message: str
    last_value: Optional[float] = None
