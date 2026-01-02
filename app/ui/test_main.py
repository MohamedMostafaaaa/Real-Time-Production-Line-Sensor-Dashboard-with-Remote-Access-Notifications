from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication

from app.core.state_store import StateStore
from app.services.controller import MonitoringController
from app.core.alarm.alarm_engine import AlarmEngine

from app.ui.main_dashboard import MainWindow
from app.ui.theme import APP_QSS

# criteria
from app.core.alarm.alarms_criteria import ScalarLimitCriteria, TempDiffCriteria
from app.domain.models import SensorConfig

# fake publisher
from app.ui.workers.fake_publisher import FakePublisher


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_QSS)

    # --- Build store + configs
    store = StateStore()
    store.set_config(SensorConfig("Pressure", "bar", 1.0, 5.0))
    store.set_config(SensorConfig("Vibration", "mm/s", 0.0, 8.0))
    store.set_config(SensorConfig("TempLowerMSP", "°C", 0.0, 60.0))
    store.set_config(SensorConfig("TempUpperMSP", "°C", 0.0, 60.0))

    # --- Build engine + controller
    engine = AlarmEngine(criteria=[
        ScalarLimitCriteria(),
        TempDiffCriteria(
            sensor_lower="TempLowerMSP",
            sensor_upper="TempUpperMSP",
            max_delta=2.0,
        ),
    ])
    controller = MonitoringController(store=store, alarm_engine=engine)

    # --- Build GUI
    scalar_sensors = ["TempLowerMSP", "TempUpperMSP", "Pressure", "Vibration"]
    win = MainWindow(store=store, scalar_sensors=scalar_sensors, ftir_sensor_name="FTNIR1")
    win.show()

    # --- Fake publisher: feed pipeline
    pub = FakePublisher(spectrum_points=255, hz=10.0)
    pub.message.connect(lambda msg: controller.handle_message(msg))
    pub.start()

    # Ensure clean stop
    def on_quit() -> None:
        pub.stop()
        pub.wait(1000)

    app.aboutToQuit.connect(on_quit)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
