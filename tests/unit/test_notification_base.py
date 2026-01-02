"""
Unit tests for app.notification.base.

These tests validate notification-layer contracts:
- NotificationEvent is immutable (frozen)
- Optional fields default to None
- Notifier protocol supports duck typing (no inheritance required)

These are contract tests; no external I/O is involved.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Sequence

import pytest

from app.notification.base import NotificationEvent, Notifier


class _FakeNotifier:
    """
    Minimal notifier implementation for protocol conformance testing.

    This class does not inherit from Notifier; it only implements the required
    notify(event) method to validate Protocol-based duck typing.
    """

    def __init__(self) -> None:
        self.seen: list[NotificationEvent] = []

    def notify(self, event: NotificationEvent) -> None:
        """Record the received event for assertions."""
        self.seen.append(event)


def test_notification_event_defaults() -> None:
    """
    Optional fields should default to None when not provided.
    """
    ev = NotificationEvent(type="alarm_report", payload={"count": 3})
    assert ev.severity is None
    assert ev.source is None
    assert ev.ts is None


def test_notification_event_is_frozen() -> None:
    """
    NotificationEvent should be immutable to preserve auditability.
    """
    ev = NotificationEvent(type="alarm", payload={"x": 1}, severity="CRITICAL")
    with pytest.raises(FrozenInstanceError):
        ev.type = "changed"  # type: ignore[misc]


def test_notifier_protocol_duck_typing() -> None:
    """
    A class is usable as a Notifier if it implements notify(event).

    Protocol-based typing means we do not require inheritance.
    """
    n = _FakeNotifier()
    ev = NotificationEvent(type="status", payload={"ok": True})

    # Runtime sanity checks
    assert hasattr(n, "notify")

    n.notify(ev)
    assert n.seen == [ev]
