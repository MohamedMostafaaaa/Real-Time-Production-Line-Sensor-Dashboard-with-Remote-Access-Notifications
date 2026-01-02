from __future__ import annotations
import sys

from PySide6.QtWidgets import QApplication
from simulator.core.device_state import DeviceState
from simulator.ui.main_window import SimulatorMainWindow
from simulator.core.device_state import DeviceState
from simulator.ui.main_window import SimulatorMainWindow
from simulator.config.settings import SimulatorSettings

def main() -> None:
    app = QApplication(sys.argv)
    settings = SimulatorSettings()
    device = DeviceState()
        # register sensors so enable/disable works
    for name in settings.all_sensors():
        device.register_sensor(name)
    # --- UI ---
    win = SimulatorMainWindow(
        device=device,
        settings=settings,
    )
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
