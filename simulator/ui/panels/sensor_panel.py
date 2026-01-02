from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QCheckBox
)

from simulator.core.device_state import DeviceState
from simulator.ui.widgets.lamp import Lamp


class SensorRow(QWidget):
    def __init__(self, name: str, device: DeviceState):
        super().__init__()
        self.name = name
        self.device = device

        self.lamp = Lamp()
        self.label = QLabel(name)
        self.enable_cb = QCheckBox("Enabled")
        self.restart_btn = QPushButton("Restart")
        self.restart_btn.setFixedWidth(90)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.lamp)
        layout.addWidget(self.label)
        layout.addStretch()
        layout.addWidget(self.enable_cb)
        layout.addWidget(self.restart_btn)

        self.enable_cb.toggled.connect(self._on_toggle)
        self.restart_btn.clicked.connect(self._on_restart)

        # initial sync from device
        self._sync_checkbox_from_device()
        self.refresh()

    def _sync_checkbox_from_device(self) -> None:
        enabled = self.device.get_sensor_enabled(self.name)
        self.enable_cb.blockSignals(True)
        self.enable_cb.setChecked(enabled)
        self.enable_cb.blockSignals(False)

    def refresh(self) -> None:
        from datetime import datetime
        now = datetime.now()

        # keep checkbox synced if something else changed it
        self._sync_checkbox_from_device()

        if not self.device.get_sensor_enabled(self.name):
            self.lamp.set_disabled()
        elif self.device.restart_remaining_s(self.name, now) > 0:
            self.lamp.set_restarting()
        else:
            self.lamp.set_active()

    def _on_toggle(self, checked: bool) -> None:
        self.device.set_sensor_enabled(self.name, checked)
        self.refresh()

    def _on_restart(self) -> None:
        self.device.restart_sensor(self.name, duration_s=5.0)
        self.refresh()


class SensorPanel(QWidget):
    def __init__(self, device: DeviceState, sensors: list[str]):
        super().__init__()
        self.rows: list[SensorRow] = []

        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        title = QLabel("Sensors")
        title.setStyleSheet("font-size: 14px; font-weight: 700;")
        layout.addWidget(title)

        for s in sensors:
            row = SensorRow(s, device)
            self.rows.append(row)
            layout.addWidget(row)

        layout.addStretch()

    def refresh(self) -> None:
        for r in self.rows:
            r.refresh()
