from __future__ import annotations

import sys
import threading
import time

from PySide6.QtWidgets import QApplication

from simulator.config.settings import SimulatorSettings
from simulator.core.device_state import DeviceState
from simulator.core.simulator_engine import SimulatorEngine
from simulator.ui.main_window import SimulatorMainWindow
from simulator.transport.tcp_server import TCPPublishServer

from simulator.sensors.temperature import ChamberTemperaturePair
from simulator.sensors.pressure import PressureSensor
from simulator.sensors.vibration import VibrationSensor
from simulator.sensors.ftnir import FTNIRSensor


def build_engine(device: DeviceState) -> SimulatorEngine:
    sensors = [
        ChamberTemperaturePair(name="ChamberTemperaturePair"),  # emits TempLowerMSP + TempUpperMSP
        PressureSensor(name="Pressure"),          # emits Pressure
        VibrationSensor(name="Vibration"),         # emits Vibration (affected by chamber + shaking)
        FTNIRSensor(name="FTNIR"),             # emits FTNIR (if enabled)
    ]
    return SimulatorEngine(device=device, sensors=sensors)


def tcp_publish_loop(server: TCPPublishServer, engine: SimulatorEngine, stop_flag: threading.Event) -> None:
    server.start()
    

    while not stop_flag.is_set():
        try:
            server.accept_one()
        except OSError:
            break

        print("[SIM] Streaming data.")
        last = time.perf_counter()

        while not stop_flag.is_set():
            now = time.perf_counter()
            dt = now - last
            last = now

            msgs = engine.step(dt)
            for m in msgs:
                server.send(m)

            if getattr(server, "_client_sock", None) is None:
                break

            time.sleep(0.01)


def main() -> None:
    app = QApplication(sys.argv)

    settings = SimulatorSettings()

    # Shared state for GUI + engine + TCP
    device = DeviceState()

    # Register sensors once here (not in UI)
    for s in settings.all_sensors():
        device.register_sensor(s, enabled=settings.default_enabled.get(s, True))

    engine = build_engine(device)

    server = TCPPublishServer(host=settings.host, port=settings.port)
    stop_flag = threading.Event()
    t = threading.Thread(target=tcp_publish_loop, args=(server, engine, stop_flag), daemon=True)
    t.start()

    win = SimulatorMainWindow(device, settings)
    win.show()

    def on_quit() -> None:
        stop_flag.set()
        try:
            server.close()
        except Exception:
            pass

    app.aboutToQuit.connect(on_quit)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
