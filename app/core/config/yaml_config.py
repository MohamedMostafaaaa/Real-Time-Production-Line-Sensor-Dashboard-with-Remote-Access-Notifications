from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from app.domain.models import SensorConfig


@dataclass(frozen=True)
class TcpClientConfig:
    """TCP client connection settings used by the readings receiver."""
    host: str = "127.0.0.1"
    port: int = 9009
    timeout_s: float = 5.0
    reconnect_delay_s: float = 0.5


@dataclass(frozen=True)
class WebhookConfigData:
    """Webhook notifier configuration (URL + auth)."""
    url: str
    auth_header: Optional[str] = None
    timeout_s: float = 3.0
    verify_tls: bool = True


@dataclass(frozen=True)
class TempDiffCriteriaConfig:
    """TempDiffCriteria parameters."""
    sensor_lower: str
    sensor_upper: str
    max_delta: float = 3.0


@dataclass(frozen=True)
class FtirPeakShiftCriteriaConfig:
    """FtirPeakShiftCriteria parameters."""
    sensor_name: str
    expected_peaks_nm: List[float]
    max_allowed_shift_nm: List[float]
    search_window_nm: float = 12.0
    require_length_match: bool = True


@dataclass(frozen=True)
class AlarmConfig:
    """Alarm engine + criteria configuration."""
    value_eps: float = 0.5
    enable_scalar_limits: bool = True
    temp_diff: Optional[TempDiffCriteriaConfig] = None
    ftir_peak_shift: Optional[FtirPeakShiftCriteriaConfig] = None


@dataclass(frozen=True)
class AppConfig:
    """
    Root application configuration loaded from YAML.

    This is the single source of truth for runtime-tunable values so the EXE
    can be configured without rebuilding.
    """
    plot_window_seconds: int
    sensors: List[SensorConfig]
    transport: TcpClientConfig
    alarms: AlarmConfig
    webhook: WebhookConfigData


def _read_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError("config.yaml must contain a YAML mapping at the root")
    return data


def _resolve_default_config_path() -> Path:
    """
    Resolve config.yaml location.

    Priority:
    1) APP_CONFIG env var if provided
    2) config.yaml next to the executable (or this module when running from source)
    3) ./config.yaml in current working directory
    """
    import os
    import sys

    env = os.getenv("APP_CONFIG")
    if env:
        return Path(env).expanduser().resolve()

    # PyInstaller-friendly: executable directory
    exe_dir = Path(sys.executable).resolve().parent
    candidate = exe_dir / "config.yaml"
    if candidate.exists():
        return candidate

    # source/dev fallback
    return Path("config.yaml").resolve()


def load_app_config(path: Optional[str] = None) -> AppConfig:
    """
    Load application configuration from YAML and convert into typed config objects.

    Parameters
    ----------
    path
        Explicit path to config.yaml. If None, uses default resolution.

    Returns
    -------
    AppConfig
        Parsed and validated configuration.

    Raises
    ------
    FileNotFoundError
        If config file does not exist.
    ValueError
        If required fields are missing or invalid.
    """
    cfg_path = Path(path).expanduser().resolve() if path else _resolve_default_config_path()
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config not found: {cfg_path}")

    raw = _read_yaml(cfg_path)

    # ---- plot ----
    plot_window_seconds = int(raw.get("plot_window_seconds", 20))

    # ---- sensors ----
    sensors_raw = raw.get("sensors", {}).get("scalar_configs", [])
    sensors: List[SensorConfig] = []
    for item in sensors_raw:
        sensors.append(
            SensorConfig(
                name=str(item["name"]),
                units=str(item["units"]),
                low_limit=float(item["low_limit"]),
                high_limit=float(item["high_limit"]),
            )
        )

    # ---- transport ----
    t = raw.get("transport", {}).get("tcp_client", {})
    transport = TcpClientConfig(
        host=str(t.get("host", "127.0.0.1")),
        port=int(t.get("port", 9009)),
        timeout_s=float(t.get("timeout_s", 5.0)),
        reconnect_delay_s=float(t.get("reconnect_delay_s", 0.5)),
    )

    # ---- webhook ----
    w = raw.get("webhook", {})
    webhook = WebhookConfigData(
        url=str(w["url"]),
        auth_header=w.get("auth_header"),
        timeout_s=float(w.get("timeout_s", 3.0)),
        verify_tls=bool(w.get("verify_tls", True)),
    )

    # ---- alarms ----
    a = raw.get("alarms", {})
    alarms = AlarmConfig(
        value_eps=float(a.get("value_eps", 0.5)),
        enable_scalar_limits=bool(a.get("enable_scalar_limits", True)),
        temp_diff=None,
        ftir_peak_shift=None,
    )

    if "temp_diff" in a and a["temp_diff"] is not None:
        td = a["temp_diff"]
        alarms = AlarmConfig(
            value_eps=alarms.value_eps,
            enable_scalar_limits=alarms.enable_scalar_limits,
            temp_diff=TempDiffCriteriaConfig(
                sensor_lower=str(td["sensor_lower"]),
                sensor_upper=str(td["sensor_upper"]),
                max_delta=float(td.get("max_delta", 3.0)),
            ),
            ftir_peak_shift=alarms.ftir_peak_shift,
        )

    if "ftir_peak_shift" in a and a["ftir_peak_shift"] is not None:
        fp = a["ftir_peak_shift"]
        alarms = AlarmConfig(
            value_eps=alarms.value_eps,
            enable_scalar_limits=alarms.enable_scalar_limits,
            temp_diff=alarms.temp_diff,
            ftir_peak_shift=FtirPeakShiftCriteriaConfig(
                sensor_name=str(fp["sensor_name"]),
                expected_peaks_nm=[float(x) for x in fp["expected_peaks_nm"]],
                max_allowed_shift_nm=[float(x) for x in fp["max_allowed_shift_nm"]],
                search_window_nm=float(fp.get("search_window_nm", 12.0)),
                require_length_match=bool(fp.get("require_length_match", True)),
            ),
        )

    return AppConfig(
        plot_window_seconds=plot_window_seconds,
        sensors=sensors,
        transport=transport,
        alarms=alarms,
        webhook=webhook,
    )
