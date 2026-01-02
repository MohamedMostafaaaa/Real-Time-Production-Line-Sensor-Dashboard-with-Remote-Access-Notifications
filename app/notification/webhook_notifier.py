from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import requests

from app.notification.base import NotificationEvent


@dataclass(frozen=True)
class WebhookConfig:
    """
    Configuration for webhook-based notifications.

    Parameters
    ----------
    url
        Target webhook URL.
    timeout_s
        HTTP request timeout in seconds.
    verify_tls
        Whether to verify TLS certificates.
    auth_header
        Optional Authorization header value (e.g., Bearer token).
    """

    url: str
    timeout_s: float = 2.0
    verify_tls: bool = True
    auth_header: Optional[str] = None


class WebhookNotifier:
    """
    Notification sender that delivers events via HTTP webhook.

    This notifier sends a JSON payload to a configured webhook endpoint
    using an HTTP POST request.

    Notes
    -----
    - This class performs side effects (network I/O).
    - HTTP errors are surfaced via ``raise_for_status()``.
    """

    def __init__(self, cfg: WebhookConfig):
        """
        Initialize the webhook notifier.

        Parameters
        ----------
        cfg
            Webhook configuration.
        """
        self._cfg = cfg

    def notify(self, event: NotificationEvent) -> None:
        """
        Send a notification event to the configured webhook endpoint.

        Parameters
        ----------
        event
            Notification event whose payload will be sent as JSON.

        Raises
        ------
        requests.HTTPError
            If the HTTP response status indicates an error.
        requests.RequestException
            For network-related errors.
        """
        headers = {"Content-Type": "application/json"}
        if self._cfg.auth_header:
            headers["Authorization"] = self._cfg.auth_header

        r = requests.post(
            self._cfg.url,
            json=event.payload,
            headers=headers,
            timeout=self._cfg.timeout_s,
            verify=self._cfg.verify_tls,
        )
        r.raise_for_status()
