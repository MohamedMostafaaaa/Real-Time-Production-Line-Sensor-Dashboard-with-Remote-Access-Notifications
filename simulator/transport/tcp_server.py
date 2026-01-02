from __future__ import annotations

import socket
import threading
from dataclasses import dataclass
from typing import Optional

from simulator.transport.ndjson import encode_message
from simulator.transport.server_config import HOST, PORT


@dataclass
class TCPPublishServer:
    """
    Single-client TCP server that publishes simulator messages as NDJSON.

    Behavior
    --------
    - Binds and listens on (host, port)
    - Accepts one TCP client at a time
    - Sends messages to the connected client as UTF-8 NDJSON lines
    - If a new client connects, any previous client is closed and replaced

    Concurrency Model
    -----------------
    The server protects access to the client socket using a threading lock so
    that accept/send/close can be called safely from different threads.

    Parameters
    ----------
    host
        Interface to bind on. Defaults to:`~simulator.transport.server_config.HOST`.
    port
        Port to bind on. Defaults to:`~simulator.transport.server_config.PORT`.
    """

    host: str = HOST
    port: int = PORT

    _server_sock: Optional[socket.socket] = None
    _client_sock: Optional[socket.socket] = None
    _lock: threading.Lock = threading.Lock()

    def start(self) -> None:
        """
        Create, bind, and listen on the server socket.

        Raises
        ------
        OSError
            If binding or listening fails (e.g., port already in use).
        """
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self.host, self.port))
        self._server_sock.listen(1)
        print(f"[SIM] TCP server listening on {self.host}:{self.port}")

    def accept_one(self) -> None:
        """
        Accept a single client connection.

        Notes
        -----
        If another client is already connected, it is closed and replaced.
        """
        if not self._server_sock:
            raise RuntimeError("Server not started")

        client, addr = self._server_sock.accept()
        with self._lock:
            # close previous client if any
            if self._client_sock:
                try:
                    self._client_sock.close()
                except Exception:
                    pass
            self._client_sock = client
        print(f"[SIM] Client connected from {addr}")

    def send(self, msg) -> None:
        """
        Send one message as an NDJSON line to the connected client.

        Parameters
        ----------
        msg
            Simulator message to serialize and send. Must be supported by
            :func:`~simulator.transport.ndjson.encode_message`.

        Notes
        -----
        - If no client is connected, this method does nothing.
        - If the client disconnects during send, the client socket is closed and cleared.
        """
        line = encode_message(msg) + "\n"
        data = line.encode("utf-8")

        with self._lock:
            sock = self._client_sock

        if not sock:
            return  # no client yet

        try:
            sock.sendall(data)
        except (BrokenPipeError, ConnectionResetError, OSError):
            # client disconnected
            with self._lock:
                try:
                    sock.close()
                except Exception:
                    pass
                self._client_sock = None
            print("[SIM] Client disconnected")

    def close(self) -> None:
        """
        Close client and server sockets.

        Notes
        -----
        Safe to call multiple times. Errors during close are swallowed.
        """
        with self._lock:
            if self._client_sock:
                try:
                    self._client_sock.close()
                except Exception:
                    pass
                self._client_sock = None
        if self._server_sock:
            try:
                self._server_sock.close()
            except Exception:
                pass
            self._server_sock = None
