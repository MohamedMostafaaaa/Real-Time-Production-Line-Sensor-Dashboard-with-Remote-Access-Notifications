from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication

from app.ui.main_dashboard import MainWindow
from app.bootstrap import build_app_system


def main() -> None:
    """
    Start the desktop UI and runtime threads.

    Notes
    -----
    - Loads configuration from `config.yaml` by default.
    - Optional CLI usage:
        python -m app.dev.run_app --config path/to/config.yaml
    """
    app = QApplication(sys.argv)

    config_path = None
    if "--config" in sys.argv:
        i = sys.argv.index("--config")
        if i + 1 < len(sys.argv):
            config_path = sys.argv[i + 1]

    wiring = build_app_system(config_path=config_path)

    scalar_sensors = [c.name for c in wiring.config.sensors]
    win = MainWindow(
        store=wiring.store,
        scalar_sensors=scalar_sensors,
        ftir_sensor_name="FTNIR",
    )
    win.show()

    wiring.runtime.start()

    def _stop_all() -> None:
        wiring.runtime.stop()
        wiring.notifier.stop()

    app.aboutToQuit.connect(_stop_all)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
