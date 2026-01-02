from __future__ import annotations

import threading
import time
import traceback
from dataclasses import dataclass
from queue import Queue
from typing import Optional, Union

from app.domain.models import FtirSensorReading, SensorReading
from app.transport.tcp_client import TCPNDJSONClient

IncomingMessage = Union[SensorReading, FtirSensorReading]


@dataclass(frozen=True)
class ReadingsReceiverConfig:
    """
    Configuration for the readings receiver thread.

    Parameters
    ----------
    host
        TCP server host.
    port
        TCP server port.
    reconnect_delay_s
        Delay in seconds between reconnect attempts after a failure.
    connect_timeout_s
        TCP connect timeout (seconds) used during the connect phase.
        After connecting, the socket is placed in blocking mode for streaming.
    """

    host: str
    port: int
    reconnect_delay_s: float = 0.5
    connect_timeout_s: float = 5.0


class ReadingsReceiverThread:
    """
    Dedicated I/O thread that receives decoded readings from a TCP NDJSON stream.

    Responsibilities
    ----------------
    - Own and manage the TCP connection lifecycle.
    - Auto-reconnect on failures until stopped.
    - Decode incoming NDJSON messages (via :meth:`TCPNDJSONClient.messages`).
    - Push decoded messages into `readings_q` using non-blocking put
      (drops newest message if queue is full).

    Stop Behavior
    -------------
    - :meth:`stop` sets the shared stop event and closes the TCP client socket
      to break any blocking receive.
    """

    def __init__(
        self,
        cfg: ReadingsReceiverConfig,
        readings_q: "Queue[IncomingMessage]",
        stop_event: threading.Event,
    ):
        """
        Parameters
        ----------
        cfg
            Receiver configuration (host/port/reconnect/timeout).
        readings_q
            Queue that receives decoded domain messages.
        stop_event
            Shared stop event used to stop all runtime threads.
        """
        self._cfg = cfg
        self._q = readings_q
        self._stop = stop_event
        self._thread = threading.Thread(target=self._run, name="readings-receiver", daemon=True)
        self._client: Optional[TCPNDJSONClient] = None

    def start(self) -> None:
        """
        Start the receiver thread if not already running.
        """
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self) -> None:
        """
        Signal the receiver thread to stop and close the TCP client if present.

        Notes
        -----
        Closing the socket helps break out of a blocking recv in the TCP client.
        """
        self._stop.set()
        try:
            if self._client:
                self._client.close()
        except Exception:
            pass

    def join(self, timeout: float | None = 2.0) -> None:
        """
        Join the receiver thread.

        Parameters
        ----------
        timeout
            Maximum time to wait for the thread to exit.
        """
        self._thread.join(timeout=timeout)

    def _run(self) -> None:
        """
        Connection loop: connect, receive messages, and reconnect on errors.

        Notes
        -----
        - Errors are logged and the thread retries after `reconnect_delay_s`.
        - When `stop_event` is set, the loop exits cleanly.
        """
        while not self._stop.is_set():
            try:
                self._client = TCPNDJSONClient(
                    host=self._cfg.host,
                    port=self._cfg.port,
                    timeout_s=self._cfg.connect_timeout_s,
                )
                self._client.connect()

                for msg in self._client.messages():
                    if self._stop.is_set():
                        break
                    try:
                        self._q.put_nowait(msg)
                    except Exception:
                        # Queue full: drop newest to protect app responsiveness.
                        pass

            except Exception as e:
                if self._stop.is_set():
                    break
                print(f"[APP][READINGS] connection/recv error: {e!r}")
                traceback.print_exc()
                time.sleep(self._cfg.reconnect_delay_s)

            finally:
                try:
                    if self._client:
                        self._client.close()
                except Exception:
                    pass
                self._client = None
