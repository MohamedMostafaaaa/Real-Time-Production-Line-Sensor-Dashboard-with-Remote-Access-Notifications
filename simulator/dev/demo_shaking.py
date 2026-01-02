import time
from datetime import datetime

from simulator.core.simulator_orchestrator import Simulator
from simulator.environment.temp_chamber import TemperatureChamber, ChamberMode
from simulator.environment.shaking import ShakeMode
from simulator.sensors.vibration import VibrationSensor
from app.domain.models import SensorReading


def main():
    chamber = TemperatureChamber()
    sim = Simulator(
        sensors=[VibrationSensor()],
        chamber=chamber,
    )

    print("\n--- No chamber, No shaking ---")
    chamber.set_power(False)
    sim.set_shake_mode(ShakeMode.OFF)
    for _ in range(10):
        for m in sim.step(datetime.now()):
            if isinstance(m, SensorReading):
                print(m.sensor, round(m.value, 3))
        time.sleep(0.1)

    print("\n--- Chamber ON (adds vibration) ---")
    chamber.set_power(True)
    chamber.set_mode(ChamberMode.HEAT)
    chamber.set_setpoint(60.0)
    sim.set_shake_mode(ShakeMode.OFF)
    for _ in range(10):
        for m in sim.step(datetime.now()):
            if isinstance(m, SensorReading):
                print(m.sensor, round(m.value, 3))
        time.sleep(0.1)

    print("\n--- Shaking WEAK ---")
    sim.set_shake_mode(ShakeMode.WEAK)
    for _ in range(10):
        for m in sim.step(datetime.now()):
            if isinstance(m, SensorReading):
                print(m.sensor, round(m.value, 3))
        time.sleep(0.1)

    print("\n--- Shaking MEDIUM ---")
    sim.set_shake_mode(ShakeMode.MEDIUM)
    for _ in range(10):
        for m in sim.step(datetime.now()):
            if isinstance(m, SensorReading):
                print(m.sensor, round(m.value, 3))
        time.sleep(0.1)

    print("\n--- Shaking STRONG ---")
    sim.set_shake_mode(ShakeMode.STRONG)
    for _ in range(10):
        for m in sim.step(datetime.now()):
            if isinstance(m, SensorReading):
                print(m.sensor, round(m.value, 3))
        time.sleep(0.1)


if __name__ == "__main__":
    main()
