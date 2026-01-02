from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Optional

from simulator.environment.chamber import TemperatureChamber, ChamberMode
from simulator.environment.shaking import ShakingEnvironment, ShakeMode


@dataclass
class DeviceState:
    """
    Single source of truth for simulator runtime state (thread-safe).

    Owns:
    - Sensor lifecycle: enabled/disabled + restart windows
    - Environment state: chamber + shaking

    Does NOT:
    - Generate readings (sensors do that)
    - Run timing loop (engine does that)
    - Do networking (transport does that)
    """

    sensor_enabled: Dict[str, bool] = field(default_factory=dict)
    sensor_restart_until: Dict[str, datetime] = field(default_factory=dict)

    chamber: TemperatureChamber = field(default_factory=TemperatureChamber)
    shaking: ShakingEnvironment = field(default_factory=ShakingEnvironment)

    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    # --------------------------
    # Sensor registry / lifecycle
    # --------------------------
    def register_sensor(self, name: str, enabled: bool = True) -> None:
        with self._lock:
            self.sensor_enabled.setdefault(name, enabled)

    def get_sensor_enabled(self, name: str) -> bool:
        with self._lock:
            return bool(self.sensor_enabled.get(name, True))

    def set_sensor_enabled(self, name: str, enabled: bool) -> None:
        with self._lock:
            self.sensor_enabled[name] = bool(enabled)
            if not enabled:
                self.sensor_restart_until.pop(name, None)

    def restart_sensor(self, name: str, duration_s: float, now: Optional[datetime] = None) -> None:
        with self._lock:
            self.sensor_enabled[name] = True
            t0 = now or datetime.now()
            self.sensor_restart_until[name] = t0 + timedelta(seconds=float(duration_s))

    def is_sensor_active(self, name: str, now: Optional[datetime] = None) -> bool:
        t = now or datetime.now()
        with self._lock:
            if not self.sensor_enabled.get(name, True):
                return False

            until = self.sensor_restart_until.get(name)
            if until is None:
                return True

            if t >= until:
                self.sensor_restart_until.pop(name, None)
                return True

            return False

    def restart_remaining_s(self, name: str, now: Optional[datetime] = None) -> float:
        t = now or datetime.now()
        with self._lock:
            until = self.sensor_restart_until.get(name)
            if until is None:
                return 0.0
            return max(0.0, (until - t).total_seconds())

    # --------------------------
    # Environment setters (thread-safe)
    # --------------------------
    def set_chamber_power(self, on: bool) -> None:
        with self._lock:
            self.chamber.powered_on = bool(on)

    def set_chamber_mode(self, mode: ChamberMode) -> None:
        with self._lock:
            self.chamber.mode = mode

    def set_chamber_setpoint(self, c: float) -> None:
        with self._lock:
            self.chamber.setpoint_c = float(c)

    def set_chamber_heat_ramp(self, v: float) -> None:
        with self._lock:
            self.chamber.heat_ramp_c_per_s = float(v)

    def set_chamber_cool_ramp(self, v: float) -> None:
        with self._lock:
            self.chamber.cool_ramp_c_per_s = float(v)

    def set_chamber_off_drift(self, v: float) -> None:
        with self._lock:
            self.chamber.off_drift_c_per_s = float(v)

    def set_shaking_mode(self, mode: ShakeMode) -> None:
        with self._lock:
            self.shaking.mode = mode
