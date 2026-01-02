from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from app.core.alarm.alarm_base import AlarmContext, AlarmCriteria, AlarmDecision, AlarmId
from app.domain.models import (
    AlarmSeverity,
    AlarmType,
    FtirSensorReading,
    SensorConfig,
    SensorReading,
    SensorStatus,
)
from app.domain.spectrum_axis import WAVELENGTH_AXIS_DESC


def _get_latest_scalar(store: object, sensor: str) -> Optional[SensorReading]:
    """
    Retrieve the latest scalar sensor reading from a store-like object.

    The function supports multiple store patterns to keep criteria decoupled:
    - Preferred: ``store.get_latest(sensor) -> SensorReading | None``
    - Fallback: ``store.snapshots`` dict containing ``{sensor_name: SensorReading}``

    Parameters
    ----------
    store
        Store-like object that may implement either method/attribute pattern.
    sensor
        Scalar sensor channel name.

    Returns
    -------
    SensorReading or None
        Latest reading for the requested sensor if available.
    """
    if hasattr(store, "get_latest"):
        return store.get_latest(sensor)  # type: ignore[attr-defined]
    snapshots = getattr(store, "snapshots", None)
    if isinstance(snapshots, dict) and sensor in snapshots:
        val = snapshots[sensor]
        if isinstance(val, SensorReading):
            return val
    return None


def _get_scalar_configs(store: object) -> List[SensorConfig]:
    """
    Retrieve scalar ``SensorConfig`` objects from a store-like object.

    Supported store patterns
    -----------------------
    - ``store.scalar_configs``: ``list[SensorConfig]``
    - ``store.configs``: ``dict[str, SensorConfig]``

    Parameters
    ----------
    store
        Store-like object that may expose scalar configurations.

    Returns
    -------
    list of SensorConfig
        Scalar sensor configurations; empty list if none are found.
    """
    if hasattr(store, "scalar_configs"):
        return list(getattr(store, "scalar_configs"))  # type: ignore[arg-type]
    cfgs = getattr(store, "configs", None)
    if isinstance(cfgs, dict):
        return list(cfgs.values())
    return []


def _get_latest_spectrum(store: object, sensor: str) -> Optional[FtirSensorReading]:
    """
    Retrieve the latest FTIR spectrum reading from a store-like object.

    Supported store patterns
    -----------------------
    - Preferred: ``store.get_latest_ftir(sensor) -> FtirSensorReading | None``
    - Fallback: ``store.ftir_snapshots`` dict containing ``{sensor_name: FtirSensorReading}``

    Parameters
    ----------
    store
        Store-like object that may implement either method/attribute pattern.
    sensor
        FTIR sensor channel name.

    Returns
    -------
    FtirSensorReading or None
        Latest FTIR reading for the requested sensor if available.
    """
    if hasattr(store, "get_latest_ftir"):
        return store.get_latest_ftir(sensor)  # type: ignore[attr-defined]
    ftir_snapshots = getattr(store, "ftir_snapshots", None)
    if isinstance(ftir_snapshots, dict) and sensor in ftir_snapshots:
        val = ftir_snapshots[sensor]
        if isinstance(val, FtirSensorReading):
            return val
    return None


def _find_local_minimum_index_in_window(
    x_desc: list[float],
    y: list[float],
    expected_nm: float,
    window_nm: float,
) -> Optional[int]:
    """
    Find the index of the local minimum (dip) within a wavelength window.

    The wavelength axis is assumed to be *descending* (e.g., 2550 -> 1350).
    The algorithm:
    1) Collect indices i where ``expected-window <= x[i] <= expected+window``
    2) Return the index i that minimizes y[i]

    Parameters
    ----------
    x_desc
        Descending wavelength axis values (nm).
    y
        Spectrum intensity/absorbance values.
    expected_nm
        Expected peak (dip) location in nm.
    window_nm
        Search half-window around expected location in nm.

    Returns
    -------
    int or None
        Index of minimum within the window if found, else None.
    """
    if not x_desc or not y:
        return None

    n = min(len(x_desc), len(y))
    lo = expected_nm - window_nm
    hi = expected_nm + window_nm

    idxs = [i for i in range(n) if lo <= x_desc[i] <= hi]
    if not idxs:
        return None

    return min(idxs, key=lambda i: y[i])


def _refine_minimum_wavelength_parabola(
    x_desc: list[float],
    y: list[float],
    i0: int,
) -> float:
    """
    Refine the minimum location using 3-point parabolic interpolation.

    This reduces jitter where the discrete minimum flips between adjacent bins.

    Parameters
    ----------
    x_desc
        Descending wavelength axis values (nm).
    y
        Spectrum values.
    i0
        Index of the discrete minimum (dip).

    Returns
    -------
    float
        Refined wavelength estimate in nm (typically between samples).
    """
    n = min(len(x_desc), len(y))

    # If we can't take neighbors, fall back to sample wavelength
    if i0 <= 0 or i0 >= n - 1:
        return float(x_desc[i0])

    y1 = float(y[i0 - 1])
    y2 = float(y[i0])
    y3 = float(y[i0 + 1])

    denom = (y1 - 2.0 * y2 + y3)
    if abs(denom) < 1e-12:
        return float(x_desc[i0])

    delta = 0.5 * (y1 - y3) / denom

    # Clamp to avoid wild jumps from pathological noise
    if delta > 1.0:
        delta = 1.0
    elif delta < -1.0:
        delta = -1.0

    x_left = float(x_desc[i0 - 1])
    x_mid = float(x_desc[i0])
    x_right = float(x_desc[i0 + 1])

    if delta >= 0.0:
        return x_mid + delta * (x_right - x_mid)
    else:
        return x_mid + (-delta) * (x_left - x_mid)


def _find_local_minimum_wavelength_in_window(
    x_desc: list[float],
    y: list[float],
    expected_nm: float,
    window_nm: float,
) -> Optional[float]:
    """
    Find and refine the wavelength of a local minimum around an expected peak.

    Parameters
    ----------
    x_desc
        Descending wavelength axis values (nm).
    y
        Spectrum values.
    expected_nm
        Expected peak location in nm.
    window_nm
        Search half-window around expected location.

    Returns
    -------
    float or None
        Refined wavelength estimate if a dip is found; otherwise None.
    """
    i0 = _find_local_minimum_index_in_window(x_desc, y, expected_nm, window_nm)
    if i0 is None:
        return None
    return _refine_minimum_wavelength_parabola(x_desc, y, i0)


@dataclass(frozen=True)
class ScalarLimitCriteria(AlarmCriteria):
    """
    Evaluate low/high limit alarms for all scalar sensors using SensorConfig.

    For each scalar sensor config, this criterion emits two decisions:
    - AlarmType.LOW_LIMIT  (value < low_limit)
    - AlarmType.HIGH_LIMIT (value > high_limit)
    """

    def evaluate(self, store: object, ctx: AlarmContext) -> Sequence[AlarmDecision]:
        decisions: List[AlarmDecision] = []

        for cfg in _get_scalar_configs(store):
            reading = _get_latest_scalar(store, cfg.name)
            if reading is None:
                continue
            if reading.status != SensorStatus.OK:
                continue

            low_active = reading.value < cfg.low_limit
            decisions.append(
                AlarmDecision(
                    alarm_id=AlarmId(source=cfg.name, alarm_type=AlarmType.LOW_LIMIT, rule_name="config_low_limit"),
                    severity=AlarmSeverity.WARNING,
                    should_be_active=low_active,
                    message=(
                        f"{cfg.name} LOW: {reading.value:.3f} < {cfg.low_limit} {cfg.units}".strip()
                        if low_active
                        else f"{cfg.name} back above low limit".strip()
                    ),
                    value=reading.value,
                )
            )

            high_active = reading.value > cfg.high_limit
            decisions.append(
                AlarmDecision(
                    alarm_id=AlarmId(source=cfg.name, alarm_type=AlarmType.HIGH_LIMIT, rule_name="config_high_limit"),
                    severity=AlarmSeverity.WARNING,
                    should_be_active=high_active,
                    message=(
                        f"{cfg.name} HIGH: {reading.value:.3f} > {cfg.high_limit:.3f} {cfg.units}".strip()
                        if high_active
                        else f"{cfg.name} back below high limit".strip()
                    ),
                    value=reading.value,
                )
            )

        return decisions


@dataclass(frozen=True)
class TempDiffCriteria(AlarmCriteria):
    """
    Check whether two temperature sensors track each other.

    The criterion emits a single alarm decision:
    - AlarmType.DIFF_BETWEEN_TEMP_SENSORS

    Logic
    -----
    ``diff = abs(lower.value - upper.value)``
    Alarm is active when ``diff > max_delta``.

    Notes
    -----
    - If either reading is missing, no decision is emitted.
    - If either reading is faulty, no decision is emitted.
    """

    sensor_lower: str
    sensor_upper: str
    max_delta: float = 3.0  # degrees Celsius

    def evaluate(self, store: object, ctx: AlarmContext) -> Sequence[AlarmDecision]:
        decisions: List[AlarmDecision] = []

        lower = _get_latest_scalar(store, self.sensor_lower)
        upper = _get_latest_scalar(store, self.sensor_upper)

        if lower is None or upper is None:
            return decisions

        if lower.status != SensorStatus.OK or upper.status != SensorStatus.OK:
            return decisions

        diff = abs(lower.value - upper.value)
        active = diff > self.max_delta

        msg = (
            f"Diff bet upper and lower MSP = {diff:.3f} C > {self.max_delta} C"
            if active
            else f"Temp diff OK: diff={diff:.3f} C"
        )

        decisions.append(
            AlarmDecision(
                alarm_id=AlarmId(
                    source=f"{self.sensor_lower}|{self.sensor_upper}",
                    alarm_type=AlarmType.DIFF_BETWEEN_TEMP_SENSORS,
                    rule_name="config_high_temp_diff",
                ),
                severity=AlarmSeverity.WARNING,
                should_be_active=active,
                message=msg,
                value=diff,
            )
        )

        return decisions


@dataclass(frozen=True)
class FtirPeakShiftCriteria(AlarmCriteria):
    """
    Detect FTIR peak wavelength shift using a hardcoded descending axis.

    Characteristics
    --------------
    - Uses ``WAVELENGTH_AXIS_DESC`` (descending wavelength axis)
    - Treats peaks as "dips" (local minima)
    - Searches within ``search_window_nm`` around each expected peak
    - Compares measured shift against a per-peak allowed maximum shift

    Notes
    -----
    - If ``require_length_match`` is True and lengths mismatch, a CRITICAL alarm
      decision is emitted immediately.
    - If ``expected_peaks_nm`` and ``max_allowed_shift_nm`` mismatch in length,
      a ValueError is raised.
    """

    sensor_name: str
    expected_peaks_nm: list[float]
    max_allowed_shift_nm: list[float]

    search_window_nm: float = 12.0
    require_length_match: bool = True

    def evaluate(self, store: object, ctx: AlarmContext) -> Sequence[AlarmDecision]:
        decisions: List[AlarmDecision] = []

        reading = _get_latest_spectrum(store, self.sensor_name)
        if reading is None:
            return decisions

        y = list(map(float, reading.values))
        x = list(WAVELENGTH_AXIS_DESC)

        if self.require_length_match and len(y) != len(x):
            decisions.append(
                AlarmDecision(
                    alarm_id=AlarmId(
                        source=self.sensor_name,
                        alarm_type=AlarmType.WAVELENGTH_SHIFT,
                        rule_name="ftir_peak_shift_hardcoded_axis",
                    ),
                    severity=AlarmSeverity.CRITICAL,
                    should_be_active=True,
                    message=f"FTIR axis/values length mismatch: axis={len(x)} values={len(y)}",
                    value=float(abs(len(x) - len(y))),
                )
            )
            return decisions

        if len(self.expected_peaks_nm) != len(self.max_allowed_shift_nm):
            raise ValueError("expected_peaks_nm and max_allowed_shift_nm must have same length")

        violations: List[str] = []
        worst_shift = 0.0

        for expected, max_shift in zip(self.expected_peaks_nm, self.max_allowed_shift_nm):
            found_nm = _find_local_minimum_wavelength_in_window(
                x_desc=x,
                y=y,
                expected_nm=float(expected),
                window_nm=float(self.search_window_nm),
            )

            if found_nm is None:
                violations.append(f"Peak near {expected:.1f} nm not found")
                continue

            shift = abs(float(found_nm) - float(expected))
            worst_shift = max(worst_shift, shift)

            if shift > float(max_shift):
                violations.append(
                    f"Peak {expected:.1f} nm shifted to {float(found_nm):.1f} nm "
                    f"(Δ={shift:.2f} nm > {float(max_shift):.2f} nm)"
                )

        active = len(violations) > 0
        msg = " | ".join(violations) if active else "FTIR peaks OK"

        decisions.append(
            AlarmDecision(
                alarm_id=AlarmId(
                    source=self.sensor_name,
                    alarm_type=AlarmType.WAVELENGTH_SHIFT,
                    rule_name="ftir_peak_shift_hardcoded_axis",
                ),
                severity=AlarmSeverity.WARNING,
                should_be_active=active,
                message=msg,
                value=worst_shift if active else 0.0,
            )
        )

        return decisions
