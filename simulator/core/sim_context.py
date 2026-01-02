from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict

from simulator.core.device_state import DeviceState


@dataclass(frozen=True)
class SimContext:
    """
    Immutable context passed into each sensor tick.

    The engine constructs a `SimContext` once per simulation step and passes it to
    each sensor model. This keeps sensors deterministic and avoids hidden globals.

    Parameters
    ----------
    now
        Current simulation timestamp for this tick.
    device
        Shared device state (thread-safe). Sensors may query this to decide whether
        they are enabled/active and to read environment settings.
    latest_scalars
        Cache of latest emitted scalar readings, keyed by sensor name. This enables
        coupled behaviors without forcing sensors to depend on each other directly.

    Notes
    -----
    Sensors should avoid importing the engine or global singletons. Everything
    needed for a tick should be provided by this context.
    """

    now: datetime
    device: DeviceState
    latest_scalars: Dict[str, float]
