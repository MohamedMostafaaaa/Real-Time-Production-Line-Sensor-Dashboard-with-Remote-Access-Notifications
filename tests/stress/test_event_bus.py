"""
Unit and stress tests for app.runtime.event_bus.EventBus.

Unit tests validate:
- publish_alarm enqueues events when capacity is available
- publish_alarm does not raise when the queue is full (drop policy)

Stress tests validate:
- publish_alarm is safe under concurrent calls from multiple threads
- the bus does not deadlock or crash under high contention

Notes
-----
Thread stress tests are probabilistic: passing increases confidence but does not
prove the absence of races. Run repeatedly for higher confidence.
"""

from __future__ import annotations

import threading
from datetime import datetime
from queue import Empty
from typing import List

import pytest

from app.domain.events import AlarmEvent, AlarmTransition
from app.domain.models import AlarmSeverity, AlarmType
from app.runtime.event_bus import EventBus


def _mk_event(i: int) -> AlarmEvent:
    """
    Create a minimal AlarmEvent for EventBus tests.

    Parameters
    ----------
    i
        Integer used to create a unique message.

    Returns
    -------
    AlarmEvent
        Minimal valid event instance.
    """
    return AlarmEvent(
        source="S",
        alarm_type=AlarmType.LOW_LIMIT,
        severity=AlarmSeverity.WARNING,
        transition=AlarmTransition.RAISED,
        timestamp=datetime(2026, 1, 1, 0, 0, 0),
        message=f"e{i}",
    )


def _drain_queue(q, limit: int = 10_000) -> List[AlarmEvent]:
    """
    Drain up to `limit` items from a queue without blocking.

    Parameters
    ----------
    q
        Queue to drain.
    limit
        Maximum number of items to read.

    Returns
    -------
    list of AlarmEvent
        Items drained from the queue.
    """
    out: List[AlarmEvent] = []
    for _ in range(limit):
        try:
            out.append(q.get_nowait())
        except Empty:
            break
    return out


def test_publish_alarm_enqueues_event_when_space_available() -> None:
    """
    publish_alarm should enqueue events when the queue has capacity.
    """
    bus = EventBus()
    ev = _mk_event(1)

    bus.publish_alarm(ev)

    got = bus.alarm_events_q.get_nowait()
    assert got.message == "e1"


def test_publish_alarm_drops_when_full_without_raising() -> None:
    """
    publish_alarm should not raise if the queue is full (drop policy).

    The bus is designed to be best-effort and protect responsiveness.
    """
    bus = EventBus()

    # Fill the queue to capacity.
    for i in range(bus.alarm_events_q.maxsize):
        bus.alarm_events_q.put_nowait(_mk_event(i))

    # This publish should be dropped, and must not raise.
    bus.publish_alarm(_mk_event(999999))

    # Queue size should not exceed maxsize.
    assert bus.alarm_events_q.qsize() == bus.alarm_events_q.maxsize


@pytest.mark.stress
def test_event_bus_publish_alarm_concurrent_producers() -> None:
    """
    Stress-test publish_alarm from multiple threads concurrently.

    Validates:
    - no exceptions from concurrent publishing
    - no deadlocks
    - queue size remains bounded (drop-on-full behavior)

    This test does not require that all events are preserved (drops are expected
    if producers outrun consumers).
    """
    bus = EventBus()
    start = threading.Barrier(16)  # 16 producer threads
    errors: List[BaseException] = []

    def producer(tid: int) -> None:
        try:
            start.wait()
            for k in range(3000):
                bus.publish_alarm(_mk_event(tid * 1_000_000 + k))
        except BaseException as e:
            errors.append(e)

    threads = [threading.Thread(target=producer, args=(t,)) for t in range(16)]
    for t in threads:
        t.start()

    for t in threads:
        t.join(timeout=10)

    assert all(not t.is_alive() for t in threads), "A producer thread did not finish (possible deadlock)"
    if errors:
        raise AssertionError(f"Concurrency test caught exceptions: {errors!r}")

    # Queue must remain bounded.
    assert bus.alarm_events_q.qsize() <= bus.alarm_events_q.maxsize

    # Drain to ensure items are valid AlarmEvents (sanity).
    drained = _drain_queue(bus.alarm_events_q, limit=5000)
    assert all(isinstance(e, AlarmEvent) for e in drained)
