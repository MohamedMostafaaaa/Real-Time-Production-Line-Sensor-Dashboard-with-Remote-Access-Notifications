from __future__ import annotations

import random
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from PySide6.QtCore import QThread, Signal

from app.domain.models import SensorReading, FtirSensorReading, SensorStatus, MaterialType


class FakePublisher(QThread):
    """
    Publishes fake sensor messages to test GUI + controller + alarms without simulator.

    Emits:
    - TempLowerMSP, TempUpperMSP (coupled)
    - Pressure
    - Vibration
    - FTIR spectrum (values length N)
    """

    message = Signal(object)  # will emit SensorReading or FtirSensorReading

    def __init__(self, spectrum_points: int = 255, hz: float = 10.0, parent=None) -> None:
        super().__init__(parent)
        self._running = True
        self.spectrum_points = spectrum_points
        self.hz = hz

        self._rng = random.Random(123)
        self._t = 0.0

        # baseline states
        self._temp = 30.0
        self._pressure = 2.0
        self._vibration = 3.0
        self._material = MaterialType.POLY

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        period = 1.0 / max(self.hz, 1e-6)

        while self._running:
            now = datetime.now()
            self._t += period

            # -----------------------------
            # Temperatures (mostly tracking)
            # -----------------------------
            # ramp slowly
            self._temp += 0.02  # gradual heating
            lower = self._temp + self._rng.gauss(0.0, 0.05)

            # sometimes inject a tracking error (to trigger diff alarm)
            if int(self._t) % 15 == 0 and self._rng.random() < 0.3:
                upper = lower + 4.0  # big mismatch spike
            else:
                upper = lower + 0.8 + self._rng.gauss(0.0, 0.05)

            self.message.emit(SensorReading("TempLowerMSP", lower, now, SensorStatus.OK))
            self.message.emit(SensorReading("TempUpperMSP", upper, now, SensorStatus.OK))

            # -----------------------------
            # Pressure (sometimes low)
            # -----------------------------
            if int(self._t) % 20 == 0 and self._rng.random() < 0.4:
                self._pressure = 0.5  # trigger LOW
            else:
                # drift back to normal 2.0
                self._pressure += (2.0 - self._pressure) * 0.2
                self._pressure += self._rng.gauss(0.0, 0.03)

            self.message.emit(SensorReading("Pressure", self._pressure, now, SensorStatus.OK))

            # -----------------------------
            # Vibration (sometimes high)
            # -----------------------------
            if int(self._t) % 25 == 0 and self._rng.random() < 0.3:
                self._vibration = 12.0  # trigger HIGH
            else:
                self._vibration += (3.0 - self._vibration) * 0.2
                self._vibration += self._rng.gauss(0.0, 0.1)

            self.message.emit(SensorReading("Vibration", self._vibration, now, SensorStatus.OK))

            # -----------------------------
            # FTIR spectrum (simple synthetic)
            # -----------------------------
            if int(self._t * 2) % 2 == 0:  # ~5 Hz
                vals = self._fake_spectrum(self._material, self._t, self.spectrum_points)
                self.message.emit(
                    FtirSensorReading(
                        sensor="FTNIR1",
                        values=vals,
                        timestamp=now,
                        status=SensorStatus.OK,
                    )
                )

            self.msleep(int(period * 1000))

    def _fake_spectrum(self, material: MaterialType, t: float, n: int) -> list[float]:
        # 3 peaks + noise, peak amplitudes depend on material
        amps = {
            MaterialType.POLY: (1.2, 0.8, 1.0),
            MaterialType.MRC: (0.7, 1.4, 0.9),
        }[material]

        centers = (50, 120, 200)
        widths = (12, 18, 10)

        out: list[float] = []
        for i in range(n):
            v = 0.0
            for (a, c, w) in zip(amps, centers, widths):
                v += a * math.exp(-0.5 * ((i - c) / w) ** 2)
            # slow drift
            v += 0.02 * math.sin(0.5 * t)
            # noise
            v += self._rng.gauss(0.0, 0.01)
            out.append(v)
        return out
