from __future__ import annotations

import threading
from dataclasses import dataclass
from queue import Queue
from typing import Union

from app.domain.models import SensorReading, FtirSensorReading
from app.services.controller import MonitoringController
from app.core.state_store import StateStore
from app.notification.notification_thread import NotificationWorkerThread

from app.runtime.readings_receiver_thread import ReadingsReceiverThread, ReadingsReceiverConfig
from app.runtime.alarm_worker_thread import AlarmWorkerThread
from app.runtime.event_bus import EventBus
from app.runtime.notification_adapter_thread import NotificationAdapterThread

IncomingMessage = Union[SensorReading, FtirSensorReading]


@dataclass(frozen=True)
class AppRuntimeConfig:
    """
    Runtime configuration for thread orchestration and transport connection.

    Parameters
    ----------
    readings_host
        TCP host of the simulator/streaming server.
    readings_port
        TCP port of the simulator/streaming server.
    reconnect_delay_s
        Delay (seconds) between reconnect attempts after network errors.
    connect_timeout_s
        TCP connect timeout (seconds) used during initial connect.
    """

    readings_host: str
    readings_port: int
    reconnect_delay_s: float = 0.5
    connect_timeout_s: float = 5.0


class AppRuntime:
    """
    Thread supervisor and composition root for the app runtime.

    This class owns:
    - a shared stop event
    - queues for inter-thread communication
    - thread lifecycles (start/stop/join)
    - event bus integration (AlarmEvent -> notifications)

    Thread Topology
    ---------------
    1) ReadingsReceiverThread (I/O)
       - owns TCP connection
       - decodes NDJSON messages
       - pushes decoded readings into `readings_q`

    2) AlarmWorkerThread (business logic)
       - consumes decoded readings
       - invokes MonitoringController.handle_message()
       - controller updates StateStore and runs AlarmEngine
       - controller publishes AlarmEvent into EventBus

    3) NotificationAdapterThread (adapter)
       - consumes AlarmEvent from EventBus queue
       - builds webhook payload snapshot from StateStore
       - emits NotificationEvent into NotificationWorkerThread

    Notes
    -----
    - All threads are daemon threads; `stop()` + `join()` are still used for clean shutdown.
    - Backpressure policy:
      - Receiver drops newest readings if queue is full.
      - EventBus drops if overloaded.
      - This protects UI responsiveness.
    """

    def __init__(
        self,
        cfg: AppRuntimeConfig,
        controller: MonitoringController,
        bus: EventBus,
        store: StateStore,
        notifier: NotificationWorkerThread,
    ):
        """
        Parameters
        ----------
        cfg
            Runtime configuration (network connection + reconnect policy).
        controller
            Orchestrates store updates and alarm evaluation.
        bus
            In-process event bus used to decouple alarm generation from notification delivery.
        store
            Thread-safe application state store.
        notifier
            Notification worker thread that performs outbound delivery (e.g., webhook).
        """
        self._cfg = cfg
        self._controller = controller
        self._bus = bus
        self._store = store
        self._notifier = notifier
        self._stop = threading.Event()

        # Queue of decoded incoming readings from the receiver thread.
        self.readings_q: "Queue[IncomingMessage]" = Queue(maxsize=5000)

        self._receiver = ReadingsReceiverThread(
            ReadingsReceiverConfig(
                host=cfg.readings_host,
                port=cfg.readings_port,
                reconnect_delay_s=cfg.reconnect_delay_s,
                connect_timeout_s=cfg.connect_timeout_s,
            ),
            readings_q=self.readings_q,
            stop_event=self._stop,
        )

        self._alarm_worker = AlarmWorkerThread(
            controller=controller,
            readings_q=self.readings_q,
            stop_event=self._stop,
        )

        self._notify_adapter = NotificationAdapterThread(
            bus=self._bus,
            store=self._store,
            notifier=self._notifier,
            stop_event=self._stop,
        )

    def start(self) -> None:
        """
        Start all runtime threads.

        Notes
        -----
        Threads are started in a safe order:
        - receiver first (so data can begin flowing)
        - alarm worker next (consumes readings)
        - notification adapter last (consumes alarm events)
        """
        self._receiver.start()
        self._alarm_worker.start()
        self._notify_adapter.start()

    def stop(self) -> None:
        """
        Stop all runtime threads and wait briefly for shutdown.

        Notes
        -----
        - Stop is cooperative: threads check the stop event and exit.
        - Receiver is also asked to close its TCP socket to unblock recv.
        """
        self._receiver.stop()
        self._alarm_worker.stop()
        self._notify_adapter.stop()

        self._receiver.join(timeout=2.0)
        self._alarm_worker.join(timeout=2.0)
        self._notify_adapter.join(timeout=2.0)
