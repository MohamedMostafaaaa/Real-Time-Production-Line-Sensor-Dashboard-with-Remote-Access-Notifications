from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional

from simulator.core.sim_context import SimContext
from simulator.domain.models import FtirSensorReading, SensorStatus
from simulator.sensors.base import SensorModel, SimMessage
from simulator.sensors.sensors_constants import DEFAULT_FTIR_HZ, FTNIR_BASELINE, FTNIR_NAME, FTNIR_POINTS


def _shift_1d(y: List[float], shift_pts: int) -> List[float]:
    """
    Shift a 1D spectrum by an integer number of samples.

    Parameters
    ----------
    y
        Spectrum values.
    shift_pts
        Integer shift (samples). Positive shifts pad from the left (edge padded),
        negative shifts pad from the right. No wrap-around is performed.

    Returns
    -------
    list of float
        Shifted spectrum values.

    Notes
    -----
    - `+shift_pts` moves spectral features to "higher indices" in the stored array.
    - Padding uses the first/last value to avoid wrap artifacts.
    """
    n = len(y)
    if n == 0 or shift_pts == 0:
        return list(y)

    k = min(abs(int(shift_pts)), n)

    if shift_pts > 0:
        return [y[0]] * k + y[: n - k]
    else:
        return y[k:] + [y[-1]] * k


@dataclass
class FTNIRSensor(SensorModel):
    """
    Fixed-length FTNIR/FTIR-like spectrum sensor model.

    Behavior
    --------
    - Emits a fixed baseline spectrum of length `points`
    - Adds Gaussian noise to all frames
    - Optionally injects a "wavelength shift" fault by shifting sample indices

    Parameters
    ----------
    sensor_name
        Output sensor channel name.
    hz
        Output rate in Hz.
    points
        Expected number of spectrum points.
    noise_sigma
        Standard deviation of additive Gaussian noise.
    seed
        RNG seed for deterministic simulation runs.
    enable_shift_faults
        Enable/disable shift fault injection.
    shift_probability
        Probability that a given emitted spectrum will be shifted.
    shift_min_pts, shift_max_pts
        Range of integer shift magnitudes (inclusive).

    Raises
    ------
    ValueError
        If the baseline spectrum length does not match `points`.
    """

    sensor_name: str = FTNIR_NAME
    hz: float = DEFAULT_FTIR_HZ

    points: int = FTNIR_POINTS

    noise_sigma: float = 0.002
    seed: Optional[int] = 42

    enable_shift_faults: bool = True
    shift_probability: float = 0.05
    shift_min_pts: int = 1
    shift_max_pts: int = 1

    _rng: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        super().__init__(name=self.name, hz=self.hz)
        self._rng = random.Random(self.seed)

        if len(FTNIR_BASELINE) != self.points:
            raise ValueError(
                f"FTNIR_BASELINE length {len(FTNIR_BASELINE)} != FTNIR_POINTS {self.points}"
            )

    def tick(self, ctx: SimContext) -> List[SimMessage]:
        """
        Emit one FTNIR spectrum frame if rate limiting and sensor state allow.

        Parameters
        ----------
        ctx
            Simulation tick context.

        Returns
        -------
        list of SimMessage
            Empty list if no emission; otherwise one FtirSensorReading.
        """
        if not self.should_emit(ctx.now):
            return []

        if not ctx.device.is_sensor_active(self.sensor_name, ctx.now):
            return []

        y = list(FTNIR_BASELINE)

        # Inject shift fault sometimes
        if self.enable_shift_faults and (self._rng.random() < self.shift_probability):
            shift_pts = self._rng.randint(self.shift_min_pts, self.shift_max_pts)
            if self._rng.random() < 0.5:
                shift_pts = -shift_pts
            y = _shift_1d(y, shift_pts)

        # Add small noise always
        if self.noise_sigma > 0.0:
            y = [v + self._rng.gauss(0.0, self.noise_sigma) for v in y]

        return [
            FtirSensorReading(
                sensor=self.sensor_name,
                values=y,
                timestamp=ctx.now,
                status=SensorStatus.OK,
            )
        ]
