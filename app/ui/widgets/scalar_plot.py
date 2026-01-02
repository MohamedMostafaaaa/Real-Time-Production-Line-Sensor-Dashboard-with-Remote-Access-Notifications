from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import pyqtgraph as pg
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout

# Rolling window seconds
ROLLING_SECONDS = 20


@dataclass
class Series:
    xs: List[float]  # seconds relative
    ys: List[float]


class ScalarPlotGrid(QFrame):
    """
    2x2 grid of small rolling plots for scalar sensors.
    """

    def __init__(self, sensor_names: List[str], parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")

        self.sensor_names = sensor_names
        self._series: Dict[str, List[Tuple[datetime, float]]] = {n: [] for n in sensor_names}

        title = QLabel("Scalar Sensors (rolling 20s)")
        title.setStyleSheet("font-size: 14px; font-weight: 700;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)
        outer.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(10)
        outer.addLayout(grid)

        self.plots: Dict[str, pg.PlotWidget] = {}
        self.curves: Dict[str, pg.PlotDataItem] = {}

        pg.setConfigOptions(antialias=True)

        for idx, name in enumerate(sensor_names):
            plot = pg.PlotWidget()
            plot.setBackground(None)
            plot.showGrid(x=True, y=True, alpha=0.2)
            plot.setTitle(name, size="10pt")
            curve = plot.plot([], [])
            self.plots[name] = plot
            self.curves[name] = curve

            r, c = divmod(idx, 2)
            grid.addWidget(plot, r, c)

    def push(self, sensor: str, ts: datetime, value: float) -> None:
        if sensor not in self._series:
            return
        self._series[sensor].append((ts, value))

        # trim old points
        cutoff = ts - timedelta(seconds=ROLLING_SECONDS)
        self._series[sensor] = [(t, v) for (t, v) in self._series[sensor] if t >= cutoff]

    def refresh(self, now: datetime) -> None:
        """
        Redraw plots (call periodically from QTimer).
        """
        for name, points in self._series.items():
            if not points:
                continue
            t0 = points[0][0]
            xs = [(t - t0).total_seconds() for (t, _) in points]
            ys = [v for (_, v) in points]
            self.curves[name].setData(xs, ys)
