from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout
from PySide6.QtCore import QTimer

from simulator.core.device_state import DeviceState
from simulator.ui.panels.sensor_panel import SensorPanel
from simulator.ui.panels.environment_panel import EnvironmentPanel
from simulator.core.controller import SimulatorUIController

from simulator.config.settings import SimulatorSettings


class SimulatorMainWindow(QMainWindow):
    def __init__(self, device: DeviceState, settings: SimulatorSettings):
        super().__init__()
        self.setWindowTitle("Simulator Control Panel")
        self.setMinimumSize(400, 500)

        sensors = settings.all_sensors()

        self.env_panel = EnvironmentPanel()
        self.sensor_panel = SensorPanel(device, sensors)

        # controller
        self.ctrl = SimulatorUIController(device, self.sensor_panel)

        # connect EnvironmentPanel signals -> controller
        self.env_panel.chamber_power_changed.connect(self.ctrl.set_chamber_power)
        self.env_panel.chamber_mode_changed.connect(self.ctrl.set_chamber_mode)
        self.env_panel.chamber_setpoint_changed.connect(self.ctrl.set_chamber_setpoint)
        self.env_panel.chamber_heat_ramp_changed.connect(self.ctrl.set_chamber_heat_ramp)
        self.env_panel.chamber_cool_ramp_changed.connect(self.ctrl.set_chamber_cool_ramp)
        self.env_panel.chamber_off_drift_changed.connect(self.ctrl.set_chamber_off_drift)
        self.env_panel.shaking_mode_changed.connect(self.ctrl.set_shaking_mode)

        # initialize UI from device once
        self.env_panel.load_from_device(device)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        layout.addWidget(self.sensor_panel, 2)
        layout.addWidget(self.env_panel, 3)
        self.setCentralWidget(central)

        # refresh current temperature label
        self._env_timer = QTimer(self)
        self._env_timer.timeout.connect(lambda: self.env_panel.set_current_temp(device.chamber.current_c))
        self._env_timer.start(200)
