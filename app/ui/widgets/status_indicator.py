from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

from app.ui.theme import COLOR_OK, COLOR_WARN, COLOR_CRIT, COLOR_TEXT_MUTED


class StatusIndicator(QFrame):
    """
    Small status widget: colored dot + label.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")

        self._dot = QLabel("●")
        self._dot.setStyleSheet(f"color: {COLOR_OK}; font-size: 16px;")
        self._text = QLabel("System OK")
        self._text.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-weight: 600;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.addWidget(self._dot, 0, Qt.AlignVCenter)
        layout.addWidget(self._text, 0, Qt.AlignVCenter)
        layout.addStretch(1)

    def set_level(self, level: str, text: str) -> None:
        """
        level: 'OK' | 'WARNING' | 'CRITICAL'
        """
        color = COLOR_OK
        if level == "WARNING":
            color = COLOR_WARN
        elif level == "CRITICAL":
            color = COLOR_CRIT

        self._dot.setStyleSheet(f"color: {color}; font-size: 16px;")
        self._text.setText(text)
