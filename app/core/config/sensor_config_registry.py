from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from app.domain.models import SensorConfig


@dataclass
class SensorConfigRegistry:
    """
    Registry for scalar sensor configurations.

    This class maintains an in-memory mapping from sensor name to
    class: 'SensorConfig'. It is typically populated
    at startup or during configuration reload and then queried by
    alarm criteria and other runtime components.

    Notes
    -----
    - The registry performs simple replacement on load: if a configuration
      with the same sensor name already exists, it is overwritten.

    Attributes
    ----------
    _configs
        Internal mapping of sensor name to SensorConfig.
    """

    _configs: Dict[str, SensorConfig] = field(default_factory=dict)

    def load(self, cfgs: Iterable[SensorConfig]) -> None:
        """
        Load or update sensor configurations.

        Parameters
        ----------
        cfgs
            Iterable of SensorConfig objects. Each configuration is indexed
            by its sensor name. Existing entries with the same name are
            replaced.

        """
        for cfg in cfgs:
            self._configs[cfg.name] = cfg

    def get(self, sensor: str) -> Optional[SensorConfig]:
        """
        Retrieve the configuration for a given sensor.

        Parameters
        ----------
        sensor
            Name of the sensor.

        Returns
        -------
        SensorConfig or None
            The configuration associated with the sensor, or None if the
            sensor is not registered.
        """
        return self._configs.get(sensor)

    def all(self) -> List[SensorConfig]:
        """
        Return all registered sensor configurations.

        Returns
        -------
        list of SensorConfig
            A list containing all stored sensor configurations.
        """
        return list(self._configs.values())
