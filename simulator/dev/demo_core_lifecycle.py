from __future__ import annotations

import time
from datetime import datetime

from simulator import sensors
from simulator.core.device_state import DeviceState
from simulator.core.simulator_engine import SimulatorEngine
from simulator.sensors.base import SensorModel
from simulator.sensors.temperature import ChamberTemperaturePair
from simulator.sensors.pressure import PressureSensor
from simulator.sensors.vibration import VibrationSensor
from simulator.sensors.ftnir import FTNIRSensor


def main() -> None:
    device = DeviceState()

    # Register all sensors so state is visible to GUIs/commands
    for n in ["TempLowerMSP", "TempUpperMSP", "Pressure", "Vibration", "FTNIR"]:
        device.register_sensor(n, enabled=True)

    engine = SimulatorEngine(
        device=device,
        sensors=[
            ChamberTemperaturePair(
                name="TempMSP",
                hz=5.0,
                lower_name="TempLowerMSP",
                upper_name="TempUpperMSP",
            ),
            PressureSensor(name="Pressure", hz=2.0),
            VibrationSensor(name="Vibration", hz=2.0),
        ],
    )

    print(">> A) Running normal for 3s")
    t0 = time.time()
    while time.time() - t0 < 3:
        msgs = engine.step()
        if msgs:
            # print a small sample
            m = msgs[0]
            print(type(m).__name__, getattr(m, "sensor", "?"))
        time.sleep(0.05)

    print("\n>> B) Disable Pressure for 3s")
    device.set_sensor_enabled("Pressure", False)
    t0 = time.time()
    while time.time() - t0 < 3:
        msgs = engine.step()
        # ensure Pressure doesn't appear
        if any(getattr(m, "sensor", "") == "Pressure" for m in msgs):
            print("!! ERROR: Pressure emitted while disabled")
        time.sleep(0.05)
    print("   (Pressure stayed silent)")

    print("\n>> C) Restart Pressure for 5s (should stay silent)")
    device.restart_sensor("Pressure", duration_s=5, now=datetime.now())
    t0 = time.time()
    while time.time() - t0 < 6:
        rem = device.restart_remaining_s("Pressure")
        msgs = engine.step()
        if any(getattr(m, "sensor", "") == "Pressure" for m in msgs) and rem > 0:
            print("!! ERROR: Pressure emitted during restart window")
        if int(rem) in (5, 3, 1) and abs(rem - round(rem)) < 0.05:
            print(f"   remaining ~{int(rem)}s")
        time.sleep(0.05)

    print(">> DONE")


if __name__ == "__main__":
    main()
