from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from simulator.environment.env_constants import (
    SHAKE_OFF_ADD_MM_S,
    SHAKE_WEAK_ADD_MM_S,
    SHAKE_MED_ADD_MM_S,
    SHAKE_STRONG_ADD_MM_S,
)

class ShakeMode(str, Enum):
    """
    Mechanical shaking intensity mode.

    Members
    -------
    OFF
        No shaking.
    WEAK
        Low-intensity shaking.
    MEDIUM
        High-intensity shaking.
    STRONG
        Maximum-intensity shaking.
    """

    OFF = "OFF"
    WEAK = "WEAK"
    MEDIUM = "MEDIUM"
    STRONG = "STRONG"


@dataclass
class ShakingEnvironment:
    """
    Simple shaking environment model.

    This model adds an extra vibration component to sensors depending
    on the current shaking mode.

    Attributes
    ----------
    mode
        Current shaking mode.
    """

    mode: ShakeMode = ShakeMode.OFF

    def vibration_add_mm_s(self) -> float:
        """
        Return the vibration contribution based on the current shake mode.

        Returns
        -------
        float
            Additional vibration magnitude in mm/s.
        """
        if self.mode == ShakeMode.WEAK:
            return SHAKE_WEAK_ADD_MM_S
        if self.mode == ShakeMode.MEDIUM:
            return SHAKE_MED_ADD_MM_S
        if self.mode == ShakeMode.STRONG:
            return SHAKE_STRONG_ADD_MM_S
        return SHAKE_OFF_ADD_MM_S
