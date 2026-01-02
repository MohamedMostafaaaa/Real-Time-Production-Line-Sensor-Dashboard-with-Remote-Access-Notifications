from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication

from app.core.state_store import StateStore
from app.ui.main_dashboard import MainWindow
from app.ui.theme import APP_QSS


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_QSS)

    # For now: start with empty store (later we connect TCP thread + controller)
    store = StateStore()

    scalar_sensors = ["TempLowerMSP", "TempUpperMSP", "Pressure", "Vibration"]
    win = MainWindow(store=store, scalar_sensors=scalar_sensors, ftir_sensor_name="FTNIR1")
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
