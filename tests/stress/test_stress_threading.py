"""
Stress tests for StateStore concurrency.

These tests attempt to surface race conditions by exercising StateStore from
multiple threads concurrently. They validate safety properties such as:
- no exceptions during concurrent reads/writes
- snapshot properties returning copies (safe to iterate/mutate externally)
- store remains usable after concurrent operations

Notes
-----
Threading tests are probabilistic: they increase confidence but do not prove
the absence of races. Run multiple times for higher confidence.
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta
from typing import List

import pytest

from app.core.state_store import StateStore
from app.domain.events import AlarmEvent, AlarmTransition
from app.domain.models import AlarmSeverity, AlarmState, AlarmType, FtirSensorReading, SensorReading


def _mk_alarm_event(ts: datetime, i: int) -> AlarmEvent:
    """Create a minimal AlarmEvent for stress testing."""
    return AlarmEvent(
        source="S",
        alarm_type=AlarmType.LOW_LIMIT,
        severity=AlarmSeverity.WARNING,
        transition=AlarmTransition.RAISED,
        timestamp=ts,
        message=f"e{i}",
    )


@pytest.mark.stress
def test_state_store_concurrent_read_write_no_exceptions() -> None:
    """
    Concurrent writers/readers should not raise exceptions.

    This is mainly aimed at preventing iteration hazards such as:
    - "dict changed size during iteration"
    """
    store = StateStore()
    start = threading.Barrier(8)  # 4 writers + 4 readers
    errors: List[BaseException] = []
    stop = threading.Event()

    base_ts = datetime(2026, 1, 1, 0, 0, 0)

    def writer_scalar(tid: int) -> None:
        try:
            start.wait()
            for k in range(2000):
                ts = base_ts + timedelta(microseconds=tid * 1_000_000 + k)
                store.update_scalar(SensorReading(sensor=f"P{tid}", value=float(k), timestamp=ts))
                if k % 200 == 0:
                    store.add_alarm_event(_mk_alarm_event(ts, k))
        except BaseException as e:
            errors.append(e)
        finally:
            stop.set()

    def writer_ftir(tid: int) -> None:
        try:
            start.wait()
            for k in range(2000):
                ts = base_ts + timedelta(microseconds=tid * 1_000_000 + k)
                store.update_spectrum(FtirSensorReading(sensor=f"FTIR{tid}", values=[float(k), float(k + 1)], timestamp=ts))
        except BaseException as e:
            errors.append(e)
        finally:
            stop.set()

    def reader(tid: int) -> None:
        try:
            start.wait()
            # keep reading until writers are likely done
            for _ in range(4000):
                snaps = store.snapshots
                ftir = store.ftir_snapshots
                events = store.alarm_events
                states = store.alarm_states

                # Mutate returned snapshots to ensure they are copies
                snaps["X"] = SensorReading(sensor="X", value=1.0, timestamp=base_ts)
                ftir["Y"] = FtirSensorReading(sensor="Y", values=[1.0], timestamp=base_ts)
                events.append(_mk_alarm_event(base_ts, 999999))
                states.clear()
        except BaseException as e:
            errors.append(e)

    threads = [
        threading.Thread(target=writer_scalar, args=(0,)),
        threading.Thread(target=writer_scalar, args=(1,)),
        threading.Thread(target=writer_ftir, args=(0,)),
        threading.Thread(target=writer_ftir, args=(1,)),
        threading.Thread(target=reader, args=(0,)),
        threading.Thread(target=reader, args=(1,)),
        threading.Thread(target=reader, args=(2,)),
        threading.Thread(target=reader, args=(3,)),
    ]

    for t in threads:
        t.start()

    for t in threads:
        t.join(timeout=10)

    # If any thread is still alive, fail (avoid hanging CI)
    assert all(not t.is_alive() for t in threads), "A thread did not finish (possible deadlock)"

    # Fail if any exceptions were captured
    if errors:
        raise AssertionError(f"Concurrency test caught exceptions: {errors!r}")

    # Basic sanity: store should still be usable
    _ = store.snapshots
    _ = store.ftir_snapshots
    _ = store.alarm_events
    _ = store.alarm_states


@pytest.mark.stress
def test_state_store_clear_alarm_history_under_concurrency() -> None:
    """
    clear_alarm_history should be safe even if other threads read alarm snapshots.
    """
    store = StateStore()
    start = threading.Barrier(3)
    errors: List[BaseException] = []

    ts = datetime(2026, 1, 1, 0, 0, 0)

    def writer() -> None:
        try:
            start.wait()
            for i in range(2000):
                store.add_alarm_event(_mk_alarm_event(ts, i))
        except BaseException as e:
            errors.append(e)

    def clearer() -> None:
        try:
            start.wait()
            for _ in range(50):
                store.clear_alarm_history()
        except BaseException as e:
            errors.append(e)

    def reader() -> None:
        try:
            start.wait()
            for _ in range(2000):
                _ = store.alarm_events
                _ = store.alarm_states
        except BaseException as e:
            errors.append(e)

    threads = [
        threading.Thread(target=writer),
        threading.Thread(target=clearer),
        threading.Thread(target=reader),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert all(not t.is_alive() for t in threads), "A thread did not finish (possible deadlock)"

    if errors:
        raise AssertionError(f"Concurrency test caught exceptions: {errors!r}")
