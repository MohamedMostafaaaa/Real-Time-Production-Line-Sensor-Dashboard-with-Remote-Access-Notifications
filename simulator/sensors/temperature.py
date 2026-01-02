from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional

from simulator.core.sim_context import SimContext
from simulator.domain.models import SensorReading, SensorStatus
from simulator.sensors.base import SensorModel, SimMessage
from simulator.sensors.sensors_constants import (
    CHAMBER_FOLLOW_OFFSET_C,
    DEFAULT_SCALAR_HZ,
    TEMP_LOWER_NAME,
    TEMP_NOISE_SIGMA,
    TEMP_UPPER_NAME,
)


@dataclass
class ChamberTemperaturePair(SensorModel):
    """
    Pair of temperature sensors that follow the simulated chamber temperature.

    Behavior
    --------
    - Reads chamber temperature from `ctx.device.chamber.current_c`
    - Adds a follow offset and sensor-specific offsets/noise
    - Emits two scalar readings (lower and upper) in the same tick

    Parameters
    ----------
    lower_name, upper_name
        Output sensor names for the two channels.
    hz
        Sampling rate in Hz.
    upper_offset_c
        Additional offset applied to the upper sensor relative to lower.
    follow_offset_c
        Offset applied relative to chamber temperature (models placement/lag).
    noise_sigma
        Gaussian noise standard deviation applied to readings.
    seed
        RNG seed for deterministic simulation runs.
    """

    lower_name: str = TEMP_LOWER_NAME
    upper_name: str = TEMP_UPPER_NAME

    hz: float = DEFAULT_SCALAR_HZ

    upper_offset_c: float = 0.8
    follow_offset_c: float = CHAMBER_FOLLOW_OFFSET_C
    noise_sigma: float = TEMP_NOISE_SIGMA
    seed: Optional[int] = 123

    _rng: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        super().__init__(name=f"ChamberTemperaturePair({self.lower_name},{self.upper_name})", hz=self.hz)
        self._rng = random.Random(self.seed)

    def tick(self, ctx: SimContext) -> List[SimMessage]:
        """
        Emit two temperature readings if rate limiting and sensor state allow.

        Parameters
        ----------
        ctx
            Simulation tick context.

        Returns
        -------
        list of SimMessage
            Empty list if no emission; otherwise two SensorReading messages.
        """
        if not self.should_emit(ctx.now):
            return []

        if not ctx.device.is_sensor_active(self.lower_name, ctx.now):
            return []
        if not ctx.device.is_sensor_active(self.upper_name, ctx.now):
            return []

        chamber_temp = float(ctx.device.chamber.current_c)
        base = chamber_temp + float(self.follow_offset_c)

        lower = base + self._rng.gauss(0.0, float(self.noise_sigma))
        upper = lower + float(self.upper_offset_c) + self._rng.gauss(0.0, float(self.noise_sigma) / 2.0)

        ts = ctx.now
        return [
            SensorReading(sensor=self.lower_name, value=float(lower), timestamp=ts, status=SensorStatus.OK),
            SensorReading(sensor=self.upper_name, value=float(upper), timestamp=ts, status=SensorStatus.OK),
        ]
