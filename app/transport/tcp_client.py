from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import Iterator, Optional, Union

from app.domain.models import FtirSensorReading, SensorReading
from app.transport.ndjson import decode_message
from app.transport.client_config import HOST, PORT, TIMEOUT_S

@dataclass
class TCPNDJSONClient:
    """
    TCP client that receives NDJSON messages from a streaming server.

    This transport adapter connects to a TCP server (e.g., simulator) and yields:
    - raw NDJSON lines via :meth:`lines`
    - decoded domain objects via :meth:`messages`

    Notes
    -----
    - This class is an infrastructure component. It does not implement business
      logic and should not decide alarm conditions.
    - Error handling in :meth:`messages` is intentionally tolerant: malformed
      lines are logged and skipped.

    Parameters
    ----------
    host
        Remote host address of the NDJSON stream server.
    port
        Remote TCP port.
    timeout_s
        Connection timeout (seconds) used for initial connect only.

    Attributes
    ----------
    _sock
        Active socket once connected; None when not connected.
    """

    host: str = HOST
    port: int = PORT
    timeout_s: float = TIMEOUT_S

    _sock: Optional[socket.socket] = None

    def connect(self) -> None:
        """
        Open a TCP connection to the configured host/port.

        Notes
        -----
        - A timeout is applied for the connect operation.
        - After connecting, timeout is cleared (blocking mode) to support
          continuous streaming.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout_s)
        sock.connect((self.host, self.port))
        sock.settimeout(None)  # streaming mode
        self._sock = sock
        print(f"[APP] Connected to simulator at {self.host}:{self.port}")

    def lines(self) -> Iterator[str]:
        """
        Yield complete NDJSON lines from the socket stream.

        Yields
        ------
        str
            A single NDJSON line (without the trailing newline).

        Raises
        ------
        RuntimeError
            If called before :meth:`connect`.
        ConnectionError
            If the remote side closes the connection.
        UnicodeDecodeError
            If received bytes cannot be decoded as UTF-8.
        """
        if not self._sock:
            raise RuntimeError("Not connected")

        buf = b""
        while True:
            chunk = self._sock.recv(4096)
            if not chunk:
                raise ConnectionError("Server closed connection")
            buf += chunk

            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                s = line.decode("utf-8").strip()
                if s:
                    yield s

    def messages(self) -> Iterator[Union[SensorReading, FtirSensorReading]]:
        """
        Yield decoded domain messages from the NDJSON stream.

        This method decodes lines using :func:`app.transport.ndjson.decode_message`.
        Malformed lines are logged and skipped (best-effort streaming).

        Yields
        ------
        SensorReading or FtirSensorReading
            Decoded domain objects.
        """
        for line in self.lines():
            try:
                yield decode_message(line)
            except Exception:
                print("[APP] BAD LINE:", repr(line[:200]))
                continue

    def close(self) -> None:
        """
        Close the underlying socket if open.

        Notes
        -----
        Any close errors are swallowed because this is a shutdown path.
        """
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
