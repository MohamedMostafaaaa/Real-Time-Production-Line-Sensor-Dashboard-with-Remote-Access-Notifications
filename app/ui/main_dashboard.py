from __future__ import annotations

from datetime import datetime
from turtle import mode

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter

from app.core.state_store import StateStore
from app.ui.widgets.status_indicator import StatusIndicator
from app.ui.widgets.ftir_plot import FtirPlot
from app.ui.widgets.scalar_plot import ScalarPlotGrid
from app.ui.widgets.sensor_table import SensorTable
from app.ui.widgets.alarm_table import AlarmTable
from app.ui.adapters.store_snapshots import active_alarm_rows, sensor_rows, alarm_rows
from app.ui.theme import COLOR_OK, COLOR_WARN, COLOR_CRIT


class MainWindow(QMainWindow):
    """
    Main dashboard window.
    - Left: big FTIR plot
    - Right: 2x2 scalar plots
    - Bottom: sensor table + alarm log
    """

    def __init__(self, store: StateStore, scalar_sensors: list[str], ftir_sensor_name: str = "FTIR1") -> None:
        super().__init__()
        self.setWindowTitle("Monitoring Dashboard")
        self.resize(1400, 820)

        self.store = store
        self.scalar_sensors = scalar_sensors
        self.ftir_sensor_name = ftir_sensor_name

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Top bar
        top = QHBoxLayout()
        self.status = StatusIndicator()
        top.addWidget(self.status)
        top.addStretch(1)
        layout.addLayout(top)

        # Middle: plots (splitter)
        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)

        self.ftir_plot = FtirPlot("Spectrum" + ("\t" * 3) + "%Reflectance")
        self.scalar_grid = ScalarPlotGrid(sensor_names=scalar_sensors)

        splitter.addWidget(self.ftir_plot)
        splitter.addWidget(self.scalar_grid)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, stretch=3)

        # Bottom: tables (splitter)
        bottom_splitter = QSplitter()
        bottom_splitter.setChildrenCollapsible(False)

        self.sensor_table = SensorTable()
        self.alarm_table = AlarmTable()

        bottom_splitter.addWidget(self.sensor_table)
        bottom_splitter.addWidget(self.alarm_table)
        bottom_splitter.setStretchFactor(0, 2)
        bottom_splitter.setStretchFactor(1, 3)

        layout.addWidget(bottom_splitter, stretch=2)

        # UI refresh timer
        self.timer = QTimer(self)
        self.timer.setInterval(200)  # 5 Hz refresh
        self.timer.timeout.connect(self.refresh_ui)
        self.timer.start()

    def refresh_ui(self) -> None:
        now = datetime.now()

        # Update scalar plots from latest snapshots
        for name in self.scalar_sensors:
            r = self.store.get_latest(name)
            if r is not None:
                self.scalar_grid.push(name, r.timestamp, r.value)

        self.scalar_grid.refresh(now)

        # Update FTIR plot if available
        ft = self.store.get_latest_ftir(self.ftir_sensor_name)
        if ft is not None:
            self.ftir_plot.set_spectrum(ft.values)

        # Update tables
        self.sensor_table.set_rows(sensor_rows(self.store))
        mode = self.alarm_table.mode()
        if mode == "Active":
            self.alarm_table.set_rows(active_alarm_rows(self.store))
        else:
            self.alarm_table.set_rows(alarm_rows(self.store))

        # Global status indicator (simple policy)
        active = self.store.get_active_alarm_states()
        if not active:
            self.status.set_level("OK", "System OK (no active alarms)")
        else:
            # CRITICAL if any critical, else WARNING
            level = "WARNING"
            for a in active:
                if getattr(a.alarm_severity, "value", str(a.alarm_severity)) == "CRITICAL":
                    level = "CRITICAL"
                    break
            self.status.set_level(level, f"{level}: {len(active)} active alarms")
