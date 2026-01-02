import time
from datetime import datetime

from simulator.core.simulator_orchestrator import Simulator
from simulator.environment.temp_chamber import TemperatureChamber, ChamberMode
from simulator.sensors.temperature import ChamberTemperaturePair
from app.domain.models import SensorReading


def print_readings(msgs):
    for m in msgs:
        if isinstance(m, SensorReading):
            print(
                f"{m.timestamp.strftime('%H:%M:%S')} | "
                f"{m.sensor:15s} = {m.value:6.2f} °C"
            )


def main():
    # Create chamber + temperature sensor
    chamber = TemperatureChamber()
    temp_sensor = ChamberTemperaturePair()

    sim = Simulator(
        sensors=[temp_sensor],
        chamber=chamber
    )

    print("\n=== CHAMBER OFF (ambient) ===")
    chamber.set_power(False)

    for _ in range(30):
        msgs = sim.step(datetime.now())
        print_readings(msgs)
        time.sleep(0.5)

    print("\n=== CHAMBER HEATING to 60°C ===")
    chamber.set_power(True)
    chamber.set_mode(ChamberMode.HEAT)
    chamber.set_setpoint(60.0)

    for _ in range(30):
        msgs = sim.step(datetime.now())
        print_readings(msgs)
        time.sleep(0.5)

    print("\n=== CHAMBER COOLING to -10°C ===")
    chamber.set_mode(ChamberMode.COOL)
    chamber.set_setpoint(-10.0)

    for _ in range(30):
        msgs = sim.step(datetime.now())
        print_readings(msgs)
        time.sleep(0.5)


if __name__ == "__main__":
    main()
