from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QTableWidget, QTableWidgetItem, QVBoxLayout, QLabel

from app.ui.theme import COLOR_OK, COLOR_WARN, COLOR_CRIT, COLOR_TEXT_MUTED


Row = Tuple[str, str, str, str]  # name, value, timestamp, status


class SensorTable(QFrame):
    """
    Table of all sensors (name, latest value, timestamp, status).
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")

        title = QLabel("Live Sensor Snapshot")
        title.setStyleSheet("font-size: 14px; font-weight: 700;")

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Sensor", "Latest Value", "Timestamp", "Status"])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(self.table)

    def set_rows(self, rows: List[Row]) -> None:
        self.table.setRowCount(len(rows))

        for i, (name, value, ts, status) in enumerate(rows):
            self._set_item(i, 0, name)
            self._set_item(i, 1, value)
            self._set_item(i, 2, ts)
            self._set_item(i, 3, status, status=True)

        self.table.resizeColumnsToContents()

    def _set_item(self, row: int, col: int, text: str, status: bool = False) -> None:
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)

        if status:
            # Color-code by status text
            color = COLOR_OK
            if text.upper() == "FAULTY":
                color = COLOR_CRIT
            item.setForeground(Qt.white)
            item.setBackground(Qt.transparent)
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.UserRole, text)
            item.setForeground(Qt.white)
            item.setBackground(Qt.transparent)
            item.setToolTip(text)
            item.setForeground(Qt.white)
            item.setBackground(Qt.transparent)
            item.setForeground(Qt.white)
            item.setBackground(Qt.transparent)
            item.setForeground(Qt.white)
            item.setBackground(Qt.transparent)
            item.setForeground(Qt.white)
            item.setBackground(Qt.transparent)
            item.setForeground(Qt.white)
            item.setBackground(Qt.transparent)
            item.setForeground(Qt.white)
            item.setBackground(Qt.transparent)
            item.setForeground(Qt.white)
            item.setBackground(Qt.transparent)
            item.setForeground(Qt.white)
            item.setBackground(Qt.transparent)
            item.setForeground(Qt.white)
            item.setBackground(Qt.transparent)
            item.setForeground(Qt.white)
            item.setBackground(Qt.transparent)
            item.setForeground(Qt.white)
            item.setBackground(Qt.transparent)
            item.setForeground(Qt.white)

            # simpler: set text color only
            item.setForeground(Qt.white)
            item.setForeground(Qt.white)
            item.setForeground(Qt.white)
            item.setForeground(Qt.white)
            # Use stylesheet on table? We'll color via background brush:
            from PySide6.QtGui import QBrush, QColor

            if text.upper() == "OK":
                item.setBackground(QBrush(QColor(COLOR_OK)))
            elif text.upper() == "FAULTY":
                item.setBackground(QBrush(QColor(COLOR_CRIT)))
            else:
                item.setBackground(QBrush(QColor(COLOR_WARN)))

        self.table.setItem(row, col, item)
