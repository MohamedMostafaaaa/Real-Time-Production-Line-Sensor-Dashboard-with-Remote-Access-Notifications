from __future__ import annotations

APP_QSS = """
QMainWindow {
    background: #0f172a; /* slate-900 */
    color: #e2e8f0;      /* slate-200 */
    font-family: Segoe UI, Arial;
    font-size: 12px;
}

QLabel {
    color: #e2e8f0;
}

QFrame#Card {
    background: #111827; /* gray-900 */
    border: 1px solid #1f2937; /* gray-800 */
    border-radius: 12px;
}

QTableWidget {
    background: #0b1220;
    border: 1px solid #1f2937;
    border-radius: 10px;
    gridline-color: #1f2937;
    color: #e2e8f0;
}

QHeaderView::section {
    background: #111827;
    color: #cbd5e1;
    border: 0px;
    padding: 6px;
    font-weight: 600;
}

QTableWidget::item {
    padding: 6px;
}

QPushButton {
    background: #1d4ed8; /* blue-700 */
    border: 0px;
    padding: 8px 12px;
    border-radius: 10px;
    color: #ffffff;
    font-weight: 600;
}
QPushButton:hover {
    background: #2563eb; /* blue-600 */
}
"""

COLOR_OK = "#22c55e"      # green-500
COLOR_WARN = "#f59e0b"    # amber-500
COLOR_CRIT = "#ef4444"    # red-500
COLOR_TEXT_MUTED = "#94a3b8"  # slate-400
