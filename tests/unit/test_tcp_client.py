"""
Unit tests for app.transport.tcp_client.TCPNDJSONClient.

These tests validate transport behavior without performing real network I/O:
- connect() uses socket.socket with correct settings
- lines() yields complete lines from streamed chunks
- lines() handles empty payload (server close) as ConnectionError
- messages() decodes valid lines and skips malformed lines

Approach
--------
We use a lightweight fake socket and monkeypatch socket.socket to return it.
"""

from __future__ import annotations


from dataclasses import dataclass, field
from typing import List, Any, Tuple, cast
import pytest
import socket
from app.domain.models import SensorReading
from app.transport.tcp_client import TCPNDJSONClient
from app.domain.models import SensorReading



@dataclass
class FakeSocket:
    """
    Simple fake socket for deterministic recv behavior.

    Parameters
    ----------
    recv_chunks
        A list of byte chunks returned on successive recv() calls.
        When chunks are exhausted, recv() returns b"" to simulate server close.
    """

    recv_chunks: List[bytes]
    connected_to: Tuple[str, int] | None = None
    timeout_history: List[Any] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.timeout_history is None:
            self.timeout_history = []

    def settimeout(self, value) -> None:
        """Record timeout settings applied by the client."""
        self.timeout_history.append(value)

    def connect(self, addr: Tuple[str, int]) -> None:
        """Record the address connected to."""
        self.connected_to = addr

    def recv(self, n: int) -> bytes:
        """Return the next chunk, or b'' when exhausted."""
        if self.recv_chunks:
            return self.recv_chunks.pop(0)
        return b""

    def close(self) -> None:
        """No-op close for the fake socket."""
        return None


def test_connect_uses_timeout_then_streaming_mode(monkeypatch) -> None:
    """
    connect() should:
    - create a socket
    - set timeout for connect
    - connect to host/port
    - clear timeout (None) for streaming mode
    """
    fake = FakeSocket(recv_chunks=[])

    def fake_socket_ctor(*args, **kwargs):
        return fake

    monkeypatch.setattr("socket.socket", fake_socket_ctor)

    client = TCPNDJSONClient(host="10.0.0.1", port=1234, timeout_s=2.5)
    client.connect()

    assert fake.connected_to == ("10.0.0.1", 1234)
    assert fake.timeout_history == [2.5, None]
    assert client._sock is fake

    client.close()
    assert client._sock is None


def test_lines_yields_complete_lines_from_chunks(monkeypatch) -> None:
    """
    lines() should buffer partial chunks and yield full newline-terminated lines.
    """
    # Two lines split across chunks + an extra newline + whitespace line
    chunks = [
        b'{"a":1}\n{"b":',
        b'2}\n\n   \n{"c":3}\n',
    ]
    fake = FakeSocket(recv_chunks=chunks)

    client = TCPNDJSONClient()
    client._sock = cast(socket.socket, fake)  # set connected state

    it = client.lines()
    assert next(it) == '{"a":1}'
    assert next(it) == '{"b":2}'
    assert next(it) == '{"c":3}'

    # Next recv will return b"" -> ConnectionError
    with pytest.raises(ConnectionError):
        next(it)


def test_lines_raises_runtime_error_if_not_connected() -> None:
    """
    lines() should raise RuntimeError if called before connect().
    """
    client = TCPNDJSONClient()
    with pytest.raises(RuntimeError):
        next(client.lines())


def test_messages_decodes_valid_and_skips_invalid(monkeypatch) -> None:
    """
    messages() should yield decoded objects and skip lines that fail decoding.
    """
    client = TCPNDJSONClient()

    # Stub lines() to avoid socket handling in this test.
    def fake_lines():
        yield '{"type":"sensor_reading","sensor":"P","value":1,"timestamp":"2026-01-01T00:00:00"}'
        yield "NOT JSON"
        yield '{"type":"sensor_reading","sensor":"P","value":2,"timestamp":"2026-01-01T00:00:01"}'

    monkeypatch.setattr(client, "lines", fake_lines)


    msgs = list(client.messages())
    assert len(msgs) == 2
    assert all(isinstance(m, SensorReading) for m in msgs)
    assert isinstance(msgs[0], SensorReading)
    assert msgs[0].value == 1.0
