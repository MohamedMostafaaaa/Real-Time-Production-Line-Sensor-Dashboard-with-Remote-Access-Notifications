from __future__ import annotations
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel


class Lamp(QLabel):
    """
    Circular lamp indicator:
    - green: active
    - red: disabled
    - yellow blinking: restarting
    """

    SIZE = 14

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self._blink = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._toggle)

        self.set_disabled()

    def _toggle(self) -> None:
        self._blink = not self._blink
        self.setVisible(self._blink)

    def set_active(self) -> None:
        self._timer.stop()
        self.setVisible(True)
        self.setStyleSheet(self._style("#2ecc71"))  # green

    def set_disabled(self) -> None:
        self._timer.stop()
        self.setVisible(True)
        self.setStyleSheet(self._style("#e74c3c"))  # red

    def set_restarting(self) -> None:
        self.setStyleSheet(self._style("#f1800f"))  # yellow
        self._timer.start(300)

    def _style(self, color: str) -> str:
        return (
            f"background-color:{color};"
            f"border-radius:{self.SIZE // 2}px;"
        )

    