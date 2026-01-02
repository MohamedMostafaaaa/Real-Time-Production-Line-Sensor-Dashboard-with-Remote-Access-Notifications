from __future__ import annotations

from PySide6.QtCore import QObject, QTimer
from simulator.core.device_state import DeviceState
from simulator.ui.panels.sensor_panel import SensorPanel
from simulator.environment.chamber import ChamberMode
from simulator.environment.shaking import ShakeMode


class SimulatorUIController(QObject):
    """Glue: UI -> DeviceState, plus UI periodic refresh."""

    def __init__(self, device: DeviceState, panel: SensorPanel):
        super().__init__()
        self.device = device
        self.panel = panel

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.panel.refresh)
        self.timer.start(200)

    def set_chamber_power(self, on: bool) -> None:
        self.device.set_chamber_power(on)

    def set_chamber_mode(self, mode: ChamberMode) -> None:
        self.device.set_chamber_mode(mode)

    def set_chamber_setpoint(self, c: float) -> None:
        self.device.set_chamber_setpoint(c)

    def set_chamber_heat_ramp(self, v: float) -> None:
        self.device.set_chamber_heat_ramp(v)

    def set_chamber_cool_ramp(self, v: float) -> None:
        self.device.set_chamber_cool_ramp(v)

    def set_chamber_off_drift(self, v: float) -> None:
        self.device.set_chamber_off_drift(v)

    def set_shaking_mode(self, mode: ShakeMode) -> None:
        self.device.set_shaking_mode(mode)
