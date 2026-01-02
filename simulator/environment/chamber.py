from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from typing import Optional

from simulator.environment.env_constants import (
    CHAMBER_AMBIENT_C,
    CHAMBER_DEFAULT_SETPOINT_C,
    CHAMBER_HEAT_RAMP_C_PER_SEC,
    CHAMBER_COOL_RAMP_C_PER_SEC,
    CHAMBER_OFF_DRIFT_C_PER_SEC,
)


class ChamberMode(str, Enum):
    """Operating mode when chamber is powered on."""
    HEAT = "HEAT"
    COOL = "COOL"


@dataclass
class TemperatureChamber:
    """Simple temperature chamber model with ramping.

    Responsibilities
    ----------------
    - Track current temperature
    - Move toward a target with a configurable ramp rate
    - Drift back to ambient when power is off (also ramped)

    Notes
    -----
    This class does not know about sensors. Sensors read `current_c`.
    """

    powered_on: bool = False
    mode: ChamberMode = ChamberMode.HEAT

    ambient_c: float = CHAMBER_AMBIENT_C
    setpoint_c: float = CHAMBER_DEFAULT_SETPOINT_C

    heat_ramp_c_per_s: float = CHAMBER_HEAT_RAMP_C_PER_SEC
    cool_ramp_c_per_s: float = CHAMBER_COOL_RAMP_C_PER_SEC
    off_drift_c_per_s: float = CHAMBER_OFF_DRIFT_C_PER_SEC

    current_c: float = CHAMBER_AMBIENT_C

    def set_power(self, on: bool) -> None:
        self.powered_on = bool(on)

    def set_mode(self, mode: ChamberMode) -> None:
        self.mode = mode

    def set_setpoint(self, setpoint_c: float) -> None:
        self.setpoint_c = float(setpoint_c)

    def target_temp(self) -> float:
        # Power OFF → drift to ambient; Power ON → target setpoint
        return self.setpoint_c if self.powered_on else self.ambient_c

    def step(self, now: datetime, dt_s: float) -> float:
        """Advance the chamber state by dt_s seconds."""
        if dt_s <= 0:
            return self.current_c

        target = self.target_temp()

        # Pick ramp rate based on direction & power/mode
        if not self.powered_on:
            rate = self.off_drift_c_per_s
        else:
            # When powered on, we still move toward target; mode influences expectation,
            # but ramp is based on direction.
            rate = self.heat_ramp_c_per_s if target >= self.current_c else self.cool_ramp_c_per_s

        max_step = rate * dt_s
        diff = target - self.current_c

        if abs(diff) <= max_step:
            self.current_c = target
        else:
            self.current_c += max_step if diff > 0 else -max_step

        return self.current_c
