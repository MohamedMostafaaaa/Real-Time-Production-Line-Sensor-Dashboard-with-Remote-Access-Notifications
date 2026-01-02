"""
Unit tests for app.notification.webhook_notifier.

These tests validate webhook notification behavior using mocked HTTP calls:
- correct request parameters passed to requests.post
- Authorization header handling
- HTTP error propagation via raise_for_status()

No real network requests are made.
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from app.notification.base import NotificationEvent
from app.notification.webhook_notifier import WebhookConfig, WebhookNotifier


def _mk_event() -> NotificationEvent:
    """
    Create a minimal NotificationEvent for webhook tests.
    """
    return NotificationEvent(
        type="alarm_event",
        payload={"k": "v"},
        severity="CRITICAL",
        source="S1",
        ts="2026-01-01T10:00:00",
    )


def test_webhook_notifier_posts_payload_without_auth(monkeypatch) -> None:
    """
    notify() should POST the event payload with correct headers and options
    when no auth header is configured.
    """
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None

    def fake_post(
        url: str,
        json: Dict[str, Any],
        headers: Dict[str, str],
        timeout: float,
        verify: bool,
    ):
        assert url == "https://example.com/webhook"
        assert json == {"k": "v"}
        assert headers == {"Content-Type": "application/json"}
        assert timeout == 3.0
        assert verify is False
        return mock_response

    monkeypatch.setattr("requests.post", fake_post)

    cfg = WebhookConfig(
        url="https://example.com/webhook",
        timeout_s=3.0,
        verify_tls=False,
    )
    notifier = WebhookNotifier(cfg)

    notifier.notify(_mk_event())

    mock_response.raise_for_status.assert_called_once()


def test_webhook_notifier_posts_payload_with_auth_header(monkeypatch) -> None:
    """
    notify() should include Authorization header when configured.
    """
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None

    def fake_post(
        url: str,
        json: Dict[str, Any],
        headers: Dict[str, str],
        timeout: float,
        verify: bool,
    ):
        assert headers["Authorization"] == "Bearer TOKEN"
        return mock_response

    monkeypatch.setattr("requests.post", fake_post)

    cfg = WebhookConfig(
        url="https://example.com/webhook",
        auth_header="Bearer TOKEN",
    )
    notifier = WebhookNotifier(cfg)

    notifier.notify(_mk_event())

    mock_response.raise_for_status.assert_called_once()


def test_webhook_notifier_propagates_http_error(monkeypatch) -> None:
    """
    notify() should propagate HTTP errors raised by raise_for_status().
    """
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("HTTP 500")

    def fake_post(*args, **kwargs):
        return mock_response

    monkeypatch.setattr("requests.post", fake_post)

    cfg = WebhookConfig(url="https://example.com/webhook")
    notifier = WebhookNotifier(cfg)

    with pytest.raises(Exception):
        notifier.notify(_mk_event())
