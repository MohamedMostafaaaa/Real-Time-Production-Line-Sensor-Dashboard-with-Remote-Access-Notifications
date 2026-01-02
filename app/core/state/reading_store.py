from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from app.domain.models import FtirSensorReading, SensorReading


@dataclass
class ReadingsStore:
    """
    In-memory store for latest sensor readings ("snapshots").

    This store keeps only the most recent reading per sensor channel:
    - Scalar sensors: temperature, pressure, etc.
    - FTIR sensors: fixed-length spectrum vectors

    Notes
    -----
    - This store does not attempt to order by timestamp; it implements a simple
      "last write wins" policy. The caller is responsible for updating in the
      intended order.
    - Thread-safety is not handled here; the enclosing `StateStore` is
      responsible for synchronization.

    Attributes
    ----------
    scalars
        Mapping from scalar sensor name -> latest SensorReading.
    spectra
        Mapping from FTIR sensor name -> latest FtirSensorReading.
    """

    scalars: Dict[str, SensorReading] = field(default_factory=dict)
    spectra: Dict[str, FtirSensorReading] = field(default_factory=dict)

    def update_scalar(self, reading: SensorReading) -> None:
        """
        Update (overwrite) the latest scalar reading for a sensor.

        Parameters
        ----------
        reading
            Scalar sensor reading to store.
        """
        self.scalars[reading.sensor] = reading

    def update_spectrum(self, reading: FtirSensorReading) -> None:
        """
        Update (overwrite) the latest FTIR reading for a sensor.

        Parameters
        ----------
        reading
            FTIR sensor reading to store.
        """
        self.spectra[reading.sensor] = reading

    def get_latest_scalar(self, sensor: str) -> Optional[SensorReading]:
        """
        Get the latest scalar reading for a sensor.

        Parameters
        ----------
        sensor
            Scalar sensor name.

        Returns
        -------
        SensorReading or None
            Latest scalar reading if present.
        """
        return self.scalars.get(sensor)

    def get_latest_spectrum(self, sensor: str) -> Optional[FtirSensorReading]:
        """
        Get the latest FTIR reading for a sensor.

        Parameters
        ----------
        sensor
            FTIR sensor name.

        Returns
        -------
        FtirSensorReading or None
            Latest FTIR reading if present.
        """
        return self.spectra.get(sensor)
