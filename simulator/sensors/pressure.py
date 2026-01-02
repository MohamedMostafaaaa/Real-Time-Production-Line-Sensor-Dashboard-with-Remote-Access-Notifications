from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional

from simulator.domain.models import SensorReading, SensorStatus
from simulator.core.sim_context import SimContext
from simulator.sensors.base import SensorModel, SimMessage
from simulator.sensors.sensors_constants import (
    DEFAULT_SCALAR_HZ,
    PRESSURE_NAME,
    PRESSURE_BASELINE_BAR,
    PRESSURE_NOISE_SIGMA,
)


@dataclass
class PressureSensor(SensorModel):
    """
    Pressure sensor model (scalar).

    The model emits pressure readings at a configured rate (Hz). Values are
    normally distributed around ``baseline_bar`` with standard deviation
    ``noise_sigma``.

    Spike injection
    --------------
    To validate alarm pipelines, the sensor can inject occasional spikes that
    jump above/below the typical operating range.

    A spike is generated when ``spike_probability`` triggers. The spike
    direction is chosen by ``spike_high_probability`` (otherwise a low spike),
    and its magnitude is sampled uniformly from
    ``[spike_delta_min_bar, spike_delta_max_bar]``.

    Notes
    -----
    - The simulator does not know the app's configured limits. The default spike
      deltas are chosen to likely cross typical low/high limits around the baseline.
      Tune spike parameters if your configured limits differ.
    - Spikes are single-sample by default (one emitted reading).
    """

    sensor_name: str = PRESSURE_NAME
    hz: float = DEFAULT_SCALAR_HZ

    baseline_bar: float = PRESSURE_BASELINE_BAR
    noise_sigma: float = PRESSURE_NOISE_SIGMA
    seed: Optional[int] = 321

    # Spike settings (tune these to exceed your configured limits)
    spike_probability: float = 0.05          # chance per emitted sample
    spike_high_probability: float = 0.5      # among spikes: chance it's a HIGH spike
    spike_delta_min_bar: float = 1.0         # spike magnitude lower bound
    spike_delta_max_bar: float = 2.0         # spike magnitude upper bound
    clamp_min_bar: float = 0.0              # pressure cannot be negative

    _rng: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        super().__init__(name=f"PressureSensor({self.sensor_name})", hz=self.hz)
        self._rng = random.Random(self.seed)

    def tick(self, ctx: SimContext) -> List[SimMessage]:
        """
        Generate a pressure reading at time ctx.now if rate-limited emission allows it.

        Returns
        -------
        list of SimMessage
            Either empty (no emission) or a single SensorReading.
        """
        if not self.should_emit(ctx.now):
            return []

        if not ctx.device.is_sensor_active(self.sensor_name, ctx.now):
            return []

        #Base reading with noise
        v = self.baseline_bar + self._rng.gauss(0.0, self.noise_sigma)

        # Optional spike injection
        if self.spike_probability > 0.0 and self._rng.random() < float(self.spike_probability):
            delta = self._rng.uniform(float(self.spike_delta_min_bar), float(self.spike_delta_max_bar))
            if self._rng.random() < float(self.spike_high_probability):
                v = self.baseline_bar + delta
            else:
                v = self.baseline_bar - delta

        # Clamp to a non-negative floor
        if v < float(self.clamp_min_bar):
            v = float(self.clamp_min_bar)

        return [
            SensorReading(
                sensor=self.sensor_name,
                value=float(v),
                timestamp=ctx.now,
                status=SensorStatus.OK,
            )
        ]
