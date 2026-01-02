from __future__ import annotations

from typing import List, Tuple
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

AlarmRow = Tuple[str, str, str, str, str]  # time, source, value, type, message


class AlarmTable(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")

        title = QLabel("Alarm Log")
        title.setStyleSheet("font-size: 14px; font-weight: 700;")

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Active"])
        self.filter_combo.setFixedWidth(120)

        header = QHBoxLayout()
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(QLabel("View:"))
        header.addWidget(self.filter_combo)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Time", "Sensor", "Value", "Type", "Message"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addLayout(header)
        layout.addWidget(self.table)

    def mode(self) -> str:
        return self.filter_combo.currentText()

    def set_rows(self, rows: List[AlarmRow]) -> None:
        self.table.setRowCount(len(rows))
        for i, (t, s, v, typ, msg) in enumerate(rows):
            self._item(i, 0, t)
            self._item(i, 1, s)
            self._item(i, 2, v)
            self._item(i, 3, typ)
            self._item(i, 4, msg)
        self.table.resizeColumnsToContents()

    def _item(self, r: int, c: int, text: str) -> None:
        it = QTableWidgetItem(text)
        it.setFlags(it.flags() & ~Qt.ItemIsEditable)
        if c in (0, 1, 2, 3):
            it.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(r, c, it)
