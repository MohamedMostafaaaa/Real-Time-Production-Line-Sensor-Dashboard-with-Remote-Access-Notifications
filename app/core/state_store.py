from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.core.alarm.alarm_base import AlarmId
from app.core.config.sensor_config_registry import SensorConfigRegistry
from app.core.state.reading_store import ReadingsStore
from app.core.state.alarm_store import AlarmStore
from app.domain.events import AlarmEvent
from app.domain.models import AlarmState, SensorConfig, SensorReading, FtirSensorReading


@dataclass
class StateStore:
    """
    Thread-safe facade for application state.

    'StateStore' aggregates and coordinates access to:
    - configuration registry (scalar sensor limits/metadata)
    - latest sensor readings (scalar + FTIR)
    - alarm history (events) and current alarm states

    Concurrency Model
    -----------------
    All reads/writes are guarded by a single re-entrant lock (`threading.RLock`).
    This provides consistent snapshots for the UI and prevents concurrent
    mutations from background update threads.

    Design Notes
    ------------
    - The store exposes both "active" methods (update/get) and UI-facing
      snapshot properties (snapshots/ftir_snapshots/alarm_events/alarm_states).
    - Snapshot properties return copies to avoid common iteration hazards such
      as "dict changed size during iteration".

    Attributes
    ----------
    configs
        SensorConfig registry used by criteria to discover scalar limits.
    readings
        Latest scalar and FTIR readings store.
    alarms
        Alarm store (events + current states).
    """

    configs: SensorConfigRegistry = field(default_factory=SensorConfigRegistry)
    readings: ReadingsStore = field(default_factory=ReadingsStore)
    alarms: AlarmStore = field(default_factory=AlarmStore)

    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)

    # --- Config API ---
    def set_config(self, cfg: SensorConfig) -> None:
        """
        Add or update a scalar sensor configuration.

        Parameters
        ----------
        cfg
            Sensor configuration to register.
        """
        with self._lock:
            self.configs.load([cfg])

    @property
    def scalar_configs(self) -> List[SensorConfig]:
        """
        Return all registered scalar sensor configurations.

        Returns
        -------
        list of SensorConfig
            Current scalar sensor configs.
        """
        with self._lock:
            return self.configs.all()

    # --- Readings API ---
    def update_scalar(self, reading: SensorReading) -> None:
        """
        Update the latest scalar reading for a sensor.

        Parameters
        ----------
        reading
            Scalar sensor reading.
        """
        with self._lock:
            self.readings.update_scalar(reading)

    def update_spectrum(self, reading: FtirSensorReading) -> None:
        """
        Update the latest FTIR spectrum reading for a sensor.

        Parameters
        ----------
        reading
            FTIR sensor reading.
        """
        with self._lock:
            self.readings.update_spectrum(reading)

    def get_latest(self, sensor: str) -> Optional[SensorReading]:
        """
        Get the latest scalar reading for a sensor.

        Parameters
        ----------
        sensor
            Sensor name.

        Returns
        -------
        SensorReading or None
            Latest scalar reading if available.
        """
        with self._lock:
            return self.readings.get_latest_scalar(sensor)

    def get_latest_ftir(self, sensor: str) -> Optional[FtirSensorReading]:
        """
        Get the latest FTIR reading for a sensor.

        Parameters
        ----------
        sensor
            FTIR sensor name.

        Returns
        -------
        FtirSensorReading or None
            Latest FTIR reading if available.
        """
        with self._lock:
            return self.readings.get_latest_spectrum(sensor)

    # --- Alarm API (used by AlarmEngine) ---
    def add_alarm_event(self, event: AlarmEvent) -> None:
        """
        Append an alarm event to the alarm history.

        Parameters
        ----------
        event
            Alarm event to persist.
        """
        with self._lock:
            self.alarms.add_event(event)

    def set_alarm_state(self, alarm_id: AlarmId, state: AlarmState) -> None:
        """
        Set the current state for a given alarm id.

        Parameters
        ----------
        alarm_id
            Alarm identifier (engine key).
        state
            Current alarm state.
        """
        with self._lock:
            self.alarms.set_state(alarm_id, state)

    def get_active_alarm_states(self) -> List[AlarmState]:
        """
        Return currently active alarm states.

        Returns
        -------
        list of AlarmState
            Active alarm states.
        """
        with self._lock:
            return self.alarms.active_states()

    def clear_alarm_history(self) -> None:
        """
        Clear stored alarm events and states.

        Notes
        -----
        This is typically triggered by UI actions (e.g., "Clear log").
        """
        with self._lock:
            self.alarms.clear()

    # -------------------------
    # UI-facing compatibility properties
    # Return copies to avoid "dict changed size during iteration"
    # -------------------------
    @property
    def snapshots(self) -> Dict[str, SensorReading]:
        """
        Snapshot copy of latest scalar readings.

        Returns
        -------
        dict[str, SensorReading]
            Mapping of sensor name -> latest scalar reading.
        """
        with self._lock:
            return dict(self.readings.scalars)

    @property
    def ftir_snapshots(self) -> Dict[str, FtirSensorReading]:
        """
        Snapshot copy of latest FTIR readings.

        Returns
        -------
        dict[str, FtirSensorReading]
            Mapping of sensor name -> latest FTIR reading.
        """
        with self._lock:
            return dict(self.readings.spectra)

    @property
    def alarm_events(self) -> List[AlarmEvent]:
        """
        Snapshot copy of alarm event history.

        Returns
        -------
        list of AlarmEvent
            Alarm events in insertion order.
        """
        with self._lock:
            return list(self.alarms.events)

    @property
    def alarm_states(self) -> Dict[AlarmId, AlarmState]:
        """
        Snapshot copy of current alarm states.

        Returns
        -------
        dict[AlarmId, AlarmState]
            Mapping of alarm id -> current alarm state.
        """
        with self._lock:
            return dict(self.alarms.states)
