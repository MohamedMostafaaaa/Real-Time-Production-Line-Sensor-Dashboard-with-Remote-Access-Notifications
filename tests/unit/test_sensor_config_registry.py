"""
Unit tests for app.core.config.sensor_config_registry.SensorConfigRegistry.

These tests validate registry behavior:
- loading configurations populates internal mapping
- loading the same sensor name overwrites previous configuration
- get() returns a config when present and None when missing
- all() returns a list of all stored configurations

No I/O is performed.
"""

from __future__ import annotations

from app.core.config.sensor_config_registry import SensorConfigRegistry
from app.domain.models import SensorConfig


def test_load_and_get_returns_config() -> None:
    """
    load() should store configs indexed by sensor name and get() should retrieve them.
    """
    reg = SensorConfigRegistry()
    cfg = SensorConfig(name="Pressure", units="bar", low_limit=1.0, high_limit=10.0)

    reg.load([cfg])

    got = reg.get("Pressure")
    assert got is not None
    assert got.name == "Pressure"
    assert got.units == "bar"
    assert got.low_limit == 1.0
    assert got.high_limit == 10.0


def test_get_returns_none_when_missing() -> None:
    """
    get() should return None when the sensor is not registered.
    """
    reg = SensorConfigRegistry()
    assert reg.get("UnknownSensor") is None


def test_load_overwrites_existing_config_for_same_sensor() -> None:
    """
    load() should overwrite previous config when a new config has the same sensor name.
    """
    reg = SensorConfigRegistry()

    cfg1 = SensorConfig(name="Temp", units="C", low_limit=0.0, high_limit=50.0)
    cfg2 = SensorConfig(name="Temp", units="C", low_limit=-5.0, high_limit=55.0)

    reg.load([cfg1])
    reg.load([cfg2])

    got = reg.get("Temp")
    assert got is not None
    assert got.low_limit == -5.0
    assert got.high_limit == 55.0


def test_all_returns_all_configs() -> None:
    """
    all() should return a list containing all registered configurations.
    """
    reg = SensorConfigRegistry()

    cfgs = [
        SensorConfig(name="A", units="u", low_limit=0.0, high_limit=1.0),
        SensorConfig(name="B", units="u", low_limit=2.0, high_limit=3.0),
    ]
    reg.load(cfgs)

    out = reg.all()
    assert isinstance(out, list)
    assert len(out) == 2
    assert {c.name for c in out} == {"A", "B"}
