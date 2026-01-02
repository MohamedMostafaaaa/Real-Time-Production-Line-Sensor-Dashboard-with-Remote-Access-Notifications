from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class SimulatorSettings:
    host: str = "127.0.0.1"
    port: int = 9009

    # Names exposed to UI + DeviceState
    scalar_sensors: Tuple[str,...] = (
        "TempLowerMSP",
        "TempUpperMSP",
        "Pressure",
        "Vibration",
    )

    spectrum_sensors: Tuple[str,...] = (
        "FTNIR",
    )

    # default enabled flags (single place)
    default_enabled: Dict[str, bool] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        # dataclass(frozen=True) workaround
        object.__setattr__(
            self,
            "default_enabled",
            {
                "TempLowerMSP": True,
                "TempUpperMSP": True,
                "Pressure": True,
                "Vibration": True,
                "FTNIR": False,  # keep off unless you want it
            },
        )

    def all_sensors(self) -> List[str]:
        return list(self.scalar_sensors) + list(self.spectrum_sensors)
