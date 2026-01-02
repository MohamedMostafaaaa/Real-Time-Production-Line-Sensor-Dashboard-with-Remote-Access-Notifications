from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Union

from simulator.core.sim_context import SimContext
from simulator.domain.models import FtirSensorReading, SensorReading

SimMessage = Union[SensorReading, FtirSensorReading]


@dataclass
class SensorModel(ABC):
    """
    Abstract base class for all sensor models.

    Responsibilities
    ----------------
    - Provide a common interface for sensors via :meth:`tick`.
    - Provide rate limiting based on a configured sampling frequency (Hz)
      via :meth:`should_emit`.

    Not Responsible For
    -------------------
    - Networking / TCP streaming
    - UI rendering
    - Device lifecycle (enable/disable/restart); handled by DeviceState

    Parameters
    ----------
    name
        Human-readable model name (mainly for logging/debugging).
    hz
        Sampling rate in Hz. If `hz <= 0`, the sensor never emits.
    """

    name: str
    hz: float

    _last_emit: Optional[datetime] = field(default=None, init=False, repr=False)

    def should_emit(self, now: datetime) -> bool:
        """
        Determine whether the sensor should emit at time `now` based on Hz.

        Parameters
        ----------
        now
            Current simulation timestamp.

        Returns
        -------
        bool
            True if the model should emit on this tick, False otherwise.
        """
        if self.hz <= 0:
            return False

        if self._last_emit is None:
            self._last_emit = now
            return True

        period = 1.0 / self.hz
        if (now - self._last_emit).total_seconds() >= period:
            self._last_emit = now
            return True
        return False

    @abstractmethod
    def tick(self, ctx: SimContext) -> List[SimMessage]:
        """
        Generate zero or more messages for the current simulation tick.

        Parameters
        ----------
        ctx
            Simulation context providing the current timestamp and shared device state.

        Returns
        -------
        list of SimMessage
            Emitted messages for this tick (possibly empty).
        """
        raise NotImplementedError
