from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from simulator.environment.chamber import ChamberMode
from simulator.environment.shaking import ShakeMode


class EnvironmentPanel(QFrame):
    """
    UI controls for simulator environment:
    - Temperature chamber: power, mode, setpoint, ramps, current temp display
    - Shaking: mode selector
    """

    chamber_power_changed = Signal(bool)
    chamber_mode_changed = Signal(object)         # ChamberMode
    chamber_setpoint_changed = Signal(float)
    chamber_heat_ramp_changed = Signal(float)
    chamber_cool_ramp_changed = Signal(float)
    chamber_off_drift_changed = Signal(float)

    shaking_mode_changed = Signal(object)         # ShakeMode

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("Environment")
        title.setStyleSheet("font-size: 14px; font-weight: 700;")
        root.addWidget(title)

        # -------- Chamber Group --------
        chamber_box = QGroupBox("Temperature Chamber")
        c_lay = QVBoxLayout(chamber_box)

        top = QHBoxLayout()
        self.power = QCheckBox("Powered ON")

        self.mode = QComboBox()
        self.mode.addItem("HEAT", ChamberMode.HEAT)
        self.mode.addItem("COOL", ChamberMode.COOL)

        top.addWidget(self.power)
        top.addStretch(1)
        top.addWidget(QLabel("Mode:"))
        top.addWidget(self.mode)
        c_lay.addLayout(top)

        self.setpoint = QDoubleSpinBox()
        self.setpoint.setRange(-50.0, 200.0)
        self.setpoint.setDecimals(2)
        self.setpoint.setSuffix(" °C")

        self.heat_ramp = QDoubleSpinBox()
        self.heat_ramp.setRange(0.001, 5.0)
        self.heat_ramp.setDecimals(3)
        self.heat_ramp.setSuffix(" °C/s")

        self.cool_ramp = QDoubleSpinBox()
        self.cool_ramp.setRange(0.001, 5.0)
        self.cool_ramp.setDecimals(3)
        self.cool_ramp.setSuffix(" °C/s")

        self.off_drift = QDoubleSpinBox()
        self.off_drift.setRange(0.001, 5.0)
        self.off_drift.setDecimals(3)
        self.off_drift.setSuffix(" °C/s")

        c_lay.addLayout(self._row("Setpoint:", self.setpoint))
        c_lay.addLayout(self._row("Heat ramp:", self.heat_ramp))
        c_lay.addLayout(self._row("Cool ramp:", self.cool_ramp))
        c_lay.addLayout(self._row("Off drift:", self.off_drift))

        cur_row = QHBoxLayout()
        cur_row.addWidget(QLabel("Current:"))
        self.current = QLabel("-")
        self.current.setStyleSheet("font-weight: 700;")
        cur_row.addStretch(1)
        cur_row.addWidget(self.current)
        c_lay.addLayout(cur_row)

        # -------- Shaking Group --------
        shaking_box = QGroupBox("Shaking")
        s_lay = QHBoxLayout(shaking_box)

        self.shake_mode = QComboBox()
        self.shake_mode.addItem("OFF", ShakeMode.OFF)
        self.shake_mode.addItem("WEAK", ShakeMode.WEAK)
        self.shake_mode.addItem("MEDIUM", ShakeMode.MEDIUM)
        self.shake_mode.addItem("STRONG", ShakeMode.STRONG)

        s_lay.addWidget(QLabel("Mode:"))
        s_lay.addWidget(self.shake_mode)
        s_lay.addStretch(1)

        root.addWidget(chamber_box)
        root.addWidget(shaking_box)
        root.addStretch(1)

        # ---- Signals (A) connect UI -> controller later through MainWindow ----
        self.power.toggled.connect(self.chamber_power_changed.emit)
        self.mode.currentIndexChanged.connect(self._emit_mode)
        self.setpoint.valueChanged.connect(self.chamber_setpoint_changed.emit)
        self.heat_ramp.valueChanged.connect(self.chamber_heat_ramp_changed.emit)
        self.cool_ramp.valueChanged.connect(self.chamber_cool_ramp_changed.emit)
        self.off_drift.valueChanged.connect(self.chamber_off_drift_changed.emit)
        self.shake_mode.currentIndexChanged.connect(self._emit_shake)

    def _row(self, label: str, widget) -> QHBoxLayout:
        lay = QHBoxLayout()
        lay.addWidget(QLabel(label))
        lay.addStretch(1)
        lay.addWidget(widget)
        return lay

    def _emit_mode(self, idx: int) -> None:
        self.chamber_mode_changed.emit(self.mode.itemData(idx))

    def _emit_shake(self, idx: int) -> None:
        self.shaking_mode_changed.emit(self.shake_mode.itemData(idx))

    # ---- (B) initialize panel from DeviceState once ----
    def load_from_device(self, device) -> None:
        """
        Initialize widget values from DeviceState (call once at startup).
        """
        ch = device.chamber
        sh = device.shaking

        self.power.blockSignals(True)
        self.power.setChecked(bool(ch.powered_on))
        self.power.blockSignals(False)

        # select mode by data
        self._set_combo_by_data(self.mode, ch.mode)
        self.setpoint.setValue(float(ch.setpoint_c))
        self.heat_ramp.setValue(float(getattr(ch, "heat_ramp_c_per_s", 0.15)))
        self.cool_ramp.setValue(float(getattr(ch, "cool_ramp_c_per_s", 0.15)))
        self.off_drift.setValue(float(getattr(ch, "off_drift_c_per_s", 0.05)))

        self._set_combo_by_data(self.shake_mode, sh.mode)

        self.set_current_temp(float(ch.current_c))

    def _set_combo_by_data(self, combo: QComboBox, value) -> None:
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.blockSignals(True)
                combo.setCurrentIndex(i)
                combo.blockSignals(False)
                return

    # ---- (C) refresh current temperature ----
    def set_current_temp(self, c: float) -> None:
        self.current.setText(f"{c:.2f} °C")
