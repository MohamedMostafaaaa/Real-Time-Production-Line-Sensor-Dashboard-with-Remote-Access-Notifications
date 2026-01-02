from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List
from app.domain.models import SensorConfig


@dataclass(frozen=True)
class Settings:
    """
    Central place for system configuration.
    """

    # How many seconds of history we keep for plots
    plot_window_seconds: int = 20

    def scalar_sensor_configs(self) -> Dict[str, SensorConfig]:
        """
        Returns configuration for all scalar sensors.
        """
        return {
            "TempLowerMSP": SensorConfig(
                name="TempLowerMSP",
                units="C",
                low_limit=-5.0,
                high_limit=55.0,
            ),
            "TempUpperMSP": SensorConfig(
                name="TempUpperMSP",
                units="C",
                low_limit=-5.0,
                high_limit=55.0,
            ),
            "Pressure": SensorConfig(
                name="Pressure",
                units="bar",
                low_limit=1.0,
                high_limit=2.0,
            ),
            "Vibration": SensorConfig(
                name="Vibration",
                units="mm/s",
                low_limit=0.0,
                high_limit=8.0,
            ),
        }
    
 

