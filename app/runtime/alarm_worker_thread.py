from __future__ import annotations

import threading
from queue import Empty, Queue
from typing import Union

from app.domain.models import FtirSensorReading, SensorReading
from app.services.controller import MonitoringController

IncomingMessage = Union[SensorReading, FtirSensorReading]


class AlarmWorkerThread:
    """
    Worker thread for alarm processing.

    Responsibilities
    ----------------
    - Consume decoded sensor readings from a queue (scalar or FTIR).
    - Delegate processing to `MonitoringController.handle_message(...)`, which:
      - updates the StateStore
      - runs the AlarmEngine
      - optionally publishes events to EventBus (non-blocking)

    Concurrency Model
    -----------------
    - The thread polls the queue with a timeout to remain responsive to stop signals.
    - Exceptions in controller handling are caught and logged to avoid killing the thread.

    Parameters
    ----------
    controller
        Monitoring controller used to process incoming readings.
    readings_q
        Queue of decoded incoming messages (SensorReading / FtirSensorReading).
    stop_event
        Thread stop signal. When set, the worker exits its loop.
    """

    def __init__(
        self,
        controller: MonitoringController,
        readings_q: "Queue[IncomingMessage]",
        stop_event: threading.Event,
    ):
        self._controller = controller
        self._q = readings_q
        self._stop = stop_event
        self._thread = threading.Thread(target=self._run, name="alarm-worker", daemon=True)

    def start(self) -> None:
        """
        Start the worker thread if it is not already running.
        """
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self) -> None:
        """
        Signal the worker thread to stop.
        """
        self._stop.set()

    def join(self, timeout: float | None = 2.0) -> None:
        """
        Join the worker thread.

        Parameters
        ----------
        timeout
            Maximum time to wait for the thread to exit.
        """
        self._thread.join(timeout=timeout)

    def _run(self) -> None:
        """
        Worker loop that consumes messages and delegates processing to controller.
        """
        while not self._stop.is_set():
            try:
                msg = self._q.get(timeout=0.5)
            except Empty:
                continue

            try:
                self._controller.handle_message(msg)
            except Exception as e:
                print(f"[APP][ALARM] handle_message failed: {e!r}")
