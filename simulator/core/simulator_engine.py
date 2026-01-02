from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Union

from simulator.domain.models import SensorReading  

from simulator.core.device_state import DeviceState
from simulator.core.sim_context import SimContext
from simulator.sensors.base import SensorModel, SimMessage


@dataclass
class SimulatorEngine:
    device: DeviceState
    sensors: List[SensorModel]

    latest_scalars: Dict[str, float] = field(default_factory=dict)
    _last_step_time: Optional[datetime] = None

    def step(
        self,
        arg: Optional[Union[datetime, float]] = None,
        *,
        now: Optional[datetime] = None,
        dt_s: Optional[float] = None,
    ) -> List[SimMessage]:
        # normalize args
        if dt_s is None and isinstance(arg, (int, float)):
            dt_s = float(arg)
        if now is None and isinstance(arg, datetime):
            now = arg
        if now is None:
            now = datetime.now()

        # compute dt if not provided
        if dt_s is None:
            if self._last_step_time is None:
                dt_s = 0.0
            else:
                dt_s = max(0.0, (now - self._last_step_time).total_seconds())

        self._last_step_time = now

        # step environment
        self.device.chamber.step(now=now, dt_s=dt_s)

        # context
        ctx = SimContext(now=now, device=self.device, latest_scalars=self.latest_scalars)

        # tick sensors
        out: List[SimMessage] = []
        for sensor in self.sensors:
            msgs = sensor.tick(ctx)
            if not msgs:
                continue
            out.extend(msgs)

            # update scalar cache
            for m in msgs:
                if isinstance(m, SensorReading):
                    self.latest_scalars[m.sensor] = float(m.value)

        return out
