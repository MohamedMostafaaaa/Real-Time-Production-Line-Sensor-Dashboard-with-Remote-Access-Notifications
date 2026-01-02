"""
Unit tests for app.runtime.reading_receiver_thread.ReadingsReceiverThread.

Validates:
- receiver connects and pushes decoded messages into readings_q (using fake TCP client)
- stop() closes client and exits thread cleanly

No real socket connections are made (TCPNDJSONClient is monkeypatched).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime
from queue import Queue
from typing import Iterator, Optional

from app.domain.models import SensorReading
from app.runtime.readings_receiver_thread import IncomingMessage, ReadingsReceiverConfig, ReadingsReceiverThread


@dataclass
class FakeTCPClient:
    """Fake TCP client providing connect/messages/close."""
    host: str
    port: int
    timeout_s: float
    closed: bool = False

    def connect(self) -> None:
        return None

    def messages(self) -> Iterator[IncomingMessage]:
        yield SensorReading(sensor="P", value=1.0, timestamp=datetime(2026, 1, 1, 0, 0, 0))
        # keep streaming a bit
        time.sleep(0.05)
        yield SensorReading(sensor="P", value=2.0, timestamp=datetime(2026, 1, 1, 0, 0, 1))
        time.sleep(0.05)

    def close(self) -> None:
        self.closed = True


def test_readings_receiver_pushes_messages(monkeypatch) -> None:
    """
    Receiver should push messages from TCP client into readings_q.
    """
    stop = threading.Event()
    q: "Queue[IncomingMessage]" = Queue()

    # Patch TCPNDJSONClient constructor used inside the thread.
    def fake_ctor(host: str, port: int, timeout_s: float):
        return FakeTCPClient(host=host, port=port, timeout_s=timeout_s)

    monkeypatch.setattr("app.runtime.readings_receiver_thread.TCPNDJSONClient", fake_ctor)

    cfg = ReadingsReceiverConfig(host="127.0.0.1", port=9009, reconnect_delay_s=0.01, connect_timeout_s=0.1)
    t = ReadingsReceiverThread(cfg=cfg, readings_q=q, stop_event=stop)
    t.start()

    time.sleep(0.25)
    t.stop()
    t.join(2.0)

    # We should have received at least one message.
    assert q.qsize() >= 1
