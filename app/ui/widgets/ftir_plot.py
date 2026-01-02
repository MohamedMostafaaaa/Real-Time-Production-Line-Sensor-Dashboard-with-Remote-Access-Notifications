from __future__ import annotations

from typing import List, Sequence

import pyqtgraph as pg
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel

from app.domain.spectrum_axis import WAVELENGTH_AXIS_DESC  # or DESC (see note below)


class FtirPlot(QFrame):
    """
    FTIR/FT-NIR spectrum plot with a fixed hardcoded wavelength axis.

    - X axis: wavelength (nm) taken from app.domain.spectrum_axis
    - Y axis: spectrum values received from simulator
    - Shows nice major ticks: 1350, 1600, 1800, 2000, ...
    """

    def __init__(self, title_text: str = "FTIR Spectrum", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")

        title = QLabel(title_text)
        title.setStyleSheet("font-size: 14px; font-weight: 700;")

        self.plot = pg.PlotWidget()
        self.plot.setBackground(None)
        self.plot.showGrid(x=True, y=True, alpha=0.2)

        self.plot.setLabel("bottom", "Wavelength", units="nm")
        self.plot.setLabel("left", "%Reflectance / Transmittance")  # rename if you want

        # Major ticks you want to see on the axis:
        major_ticks = [1350, 1600, 1800, 2000, 2200, 2400, 2550]
        self._apply_x_ticks(major_ticks)

        self.curve = self.plot.plot([], [])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(self.plot)

        # Cache the fixed axis as floats
        self._x_axis: List[float] = list(map(float, WAVELENGTH_AXIS_DESC))

    def _apply_x_ticks(self, major_ticks_nm: Sequence[float]) -> None:
        axis = self.plot.getAxis("bottom")
        # Force ticks exactly at these wavelengths (labels are strings)
        axis.setTicks([[(float(t), str(int(t))) for t in major_ticks_nm]])

    def set_spectrum(self, values: List[float]) -> None:
        # Safety: x/y length mismatch
        n = min(len(values), len(self._x_axis))
        if n <= 1:
            self.curve.setData([], [])
            return

        xs = self._x_axis[:n]
        ys = values[:n]
        self.curve.setData(xs, ys)
