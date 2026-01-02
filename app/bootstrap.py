from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.core.config.yaml_config import AppConfig, load_app_config
from app.core.state_store import StateStore
from app.core.alarm.alarm_engine import AlarmEngine
from app.core.alarm.alarms_criteria import ScalarLimitCriteria, TempDiffCriteria, FtirPeakShiftCriteria

from app.notification.notification_thread import NotificationWorkerThread
from app.notification.webhook_notifier import WebhookNotifier, WebhookConfig

from app.runtime.event_bus import EventBus
from app.runtime.app_runtime import AppRuntime, AppRuntimeConfig
from app.services.controller import MonitoringController


@dataclass(frozen=True)
class AppWiring:
    """Everything the UI layer needs to run the system."""
    config: AppConfig
    store: StateStore
    notifier: NotificationWorkerThread
    runtime: AppRuntime


def build_alarm_engine(cfg: AppConfig) -> AlarmEngine:
    criteria = []

    if cfg.alarms.enable_scalar_limits:
        criteria.append(ScalarLimitCriteria())

    if cfg.alarms.temp_diff is not None:
        td = cfg.alarms.temp_diff
        criteria.append(
            TempDiffCriteria(
                sensor_lower=td.sensor_lower,
                sensor_upper=td.sensor_upper,
                max_delta=td.max_delta,
            )
        )

    if cfg.alarms.ftir_peak_shift is not None:
        fp = cfg.alarms.ftir_peak_shift
        criteria.append(
            FtirPeakShiftCriteria(
                sensor_name=fp.sensor_name,
                expected_peaks_nm=fp.expected_peaks_nm,
                max_allowed_shift_nm=fp.max_allowed_shift_nm,
                search_window_nm=fp.search_window_nm,
                require_length_match=fp.require_length_match,
            )
        )

    return AlarmEngine(criteria=criteria, value_eps=cfg.alarms.value_eps)


def build_notifier(cfg: AppConfig) -> NotificationWorkerThread:
    auth_header = cfg.webhook.auth_header

    if auth_header and not auth_header.startswith("Bearer "):
        auth_header = f"Bearer {auth_header}"

    notify_thread = NotificationWorkerThread(
        notifiers=[
            WebhookNotifier(
                WebhookConfig(
                    url=cfg.webhook.url,
                    auth_header=auth_header,
                    timeout_s=cfg.webhook.timeout_s,
                    verify_tls=cfg.webhook.verify_tls,
                )
            )
        ]
    )
    return notify_thread



def build_app_system(config_path: Optional[str] = None) -> AppWiring:
    cfg = load_app_config(config_path)

    # --- STATE ---
    store = StateStore()
    store.configs.load(cfg.sensors)

    # --- ALARMS ---
    alarm_engine = build_alarm_engine(cfg)

    # --- NOTIFICATIONS ---
    notifier = build_notifier(cfg)
    notifier.start()

    # --- EVENT BUS ---
    bus = EventBus()

    # --- CONTROLLER ---
    controller = MonitoringController(store=store, alarm_engine=alarm_engine, bus=bus)

    # --- RUNTIME ---
    runtime = AppRuntime(
        cfg=AppRuntimeConfig(
            readings_host=cfg.transport.host,
            readings_port=cfg.transport.port,
            connect_timeout_s=cfg.transport.timeout_s,
            reconnect_delay_s=cfg.transport.reconnect_delay_s,
        ),
        controller=controller,
        bus=bus,
        store=store,
        notifier=notifier,
    )


    return AppWiring(config=cfg, store=store, notifier=notifier, runtime=runtime)
