from datetime import datetime
import time
from app.domain.models import SensorReading, Spectrum
from simulator.core.simulator_orchestrator import Simulator
from simulator.sensors.temperature import ChamberTemperaturePair


def main():
    temp_pair = ChamberTemperaturePair()
    sim = Simulator(sensors=[temp_pair])

    start = time.time()
    while time.time() - start < 10.0:
        msgs = sim.step(datetime.now())
        for m in msgs:
            if isinstance(m, SensorReading):
                print(m.sensor, round(m.value, 3), m.timestamp)
            elif isinstance(m, Spectrum):
                print(m.sensor, len(m.absorbance), m.timestamp, "ref_temp=", m.ref_temp)


if __name__ == "__main__":
    main()
