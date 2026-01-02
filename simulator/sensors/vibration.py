from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional

from simulator.core.sim_context import SimContext
from simulator.domain.models import SensorReading, SensorStatus
from simulator.environment.env_constants import CHAMBER_ON_ADD_MM_S
from simulator.sensors.base import SensorModel, SimMessage
from simulator.sensors.sensors_constants import (
    DEFAULT_SCALAR_HZ,
    VIBRATION_BASELINE_MM_S,
    VIBRATION_NAME,
    VIBRATION_NOISE_SIGMA,
)


@dataclass
class VibrationSensor(SensorModel):
    """
    Vibration sensor model influenced by environment (chamber + shaking).

    Behavior
    --------
    - Starts from a baseline vibration value.
    - Adds a fixed amount when the chamber is powered on.
    - Adds an additional amount based on the shaking environment.
    - Adds Gaussian noise.

    Parameters
    ----------
    sensor_name
        Output sensor channel name.
    hz
        Sampling rate in Hz.
    baseline_mm_s
        Baseline vibration magnitude.
    noise_sigma
        Gaussian noise standard deviation.
    seed
        RNG seed for deterministic simulation runs.
    """

    sensor_name: str = VIBRATION_NAME
    hz: float = DEFAULT_SCALAR_HZ

    baseline_mm_s: float = VIBRATION_BASELINE_MM_S
    noise_sigma: float = VIBRATION_NOISE_SIGMA
    seed: Optional[int] = 999

    _rng: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        super().__init__(name=f"VibrationSensor({self.sensor_name})", hz=self.hz)
        self._rng = random.Random(self.seed)

    def tick(self, ctx: SimContext) -> List[SimMessage]:
        """
        Emit a vibration reading if rate limiting and sensor state allow.

        Parameters
        ----------
        ctx
            Simulation tick context.

        Returns
        -------
        list of SimMessage
            Empty list if no emission; otherwise one SensorReading.
        """
        if not self.should_emit(ctx.now):
            return []

        if not ctx.device.is_sensor_active(self.sensor_name, ctx.now):
            return []

        v = float(self.baseline_mm_s)

        if ctx.device.chamber.powered_on:
            v += float(CHAMBER_ON_ADD_MM_S)

        v += float(ctx.device.shaking.vibration_add_mm_s())
        v += float(self._rng.gauss(0.0, self.noise_sigma))

        return [
            SensorReading(
                sensor=self.sensor_name,
                value=v,
                timestamp=ctx.now,
                status=SensorStatus.OK,
            )
        ]
