"""Unit tests for NotificationMessage and NotificationService."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.services.notification_service import (
    NotificationMessage,
    NotificationService,
)

# ===========================================================================
# NotificationMessage dataclass + __post_init__
# ===========================================================================


class TestNotificationMessage:
    def test_required_fields_stored(self):
        m = NotificationMessage(title="Alert", message="Something happened")
        assert m.title == "Alert"
        assert m.message == "Something happened"

    def test_priority_default_normal(self):
        assert NotificationMessage(title="t", message="m").priority == "normal"

    def test_category_default_system(self):
        assert NotificationMessage(title="t", message="m").category == "system"

    def test_recipient_default_none(self):
        assert NotificationMessage(title="t", message="m").recipient is None

    def test_metadata_default_empty_dict(self):
        m = NotificationMessage(title="t", message="m")
        assert m.metadata == {}

    def test_metadata_none_replaced_with_empty_dict(self):
        m = NotificationMessage(title="t", message="m", metadata=None)
        assert m.metadata == {}

    def test_timestamp_auto_set(self):
        before = datetime.utcnow()
        m = NotificationMessage(title="t", message="m")
        after = datetime.utcnow()
        assert before <= m.timestamp <= after

    def test_explicit_timestamp_preserved(self):
        ts = datetime(2024, 6, 1, 12, 0, 0)
        m = NotificationMessage(title="t", message="m", timestamp=ts)
        assert m.timestamp == ts

    def test_custom_priority_stored(self):
        m = NotificationMessage(title="t", message="m", priority="urgent")
        assert m.priority == "urgent"

    def test_custom_recipient_stored(self):
        m = NotificationMessage(title="t", message="m", recipient="user-42")
        assert m.recipient == "user-42"


# ===========================================================================
# NotificationService init
# ===========================================================================


class TestNotificationServiceInit:
    @pytest.fixture
    def svc(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        return NotificationService()

    def test_notifications_list_starts_empty(self, svc):
        assert svc.notifications == []

    def test_email_disabled_by_default(self, svc):
        assert svc.email_enabled is False

    def test_slack_disabled(self, svc):
        assert svc.slack_enabled is False

    def test_config_stored(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cfg = {"smtp": {"enabled": True}}
        svc = NotificationService(config=cfg)
        assert svc.config == cfg

    def test_email_enabled_from_config(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        svc = NotificationService(config={"smtp": {"enabled": True}})
        assert svc.email_enabled is True


# ===========================================================================
# NotificationService.get_notifications — filtering
# ===========================================================================


class TestGetNotifications:
    @pytest.fixture
    def svc(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        return NotificationService()

    @pytest.mark.asyncio
    async def test_returns_all_when_no_filter(self, svc):
        svc.notifications = [
            NotificationMessage(title="A", message="a", category="alert"),
            NotificationMessage(title="B", message="b", category="system"),
        ]
        result = await svc.get_notifications()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_filters_by_category(self, svc):
        svc.notifications = [
            NotificationMessage(title="A", message="a", category="alert"),
            NotificationMessage(title="B", message="b", category="system"),
            NotificationMessage(title="C", message="c", category="alert"),
        ]
        result = await svc.get_notifications(category="alert")
        assert len(result) == 2
        assert all(n.category == "alert" for n in result)

    @pytest.mark.asyncio
    async def test_filters_by_priority(self, svc):
        svc.notifications = [
            NotificationMessage(title="A", message="a", priority="high"),
            NotificationMessage(title="B", message="b", priority="normal"),
        ]
        result = await svc.get_notifications(priority="high")
        assert len(result) == 1
        assert result[0].priority == "high"

    @pytest.mark.asyncio
    async def test_limit_respected(self, svc):
        svc.notifications = [NotificationMessage(title=str(i), message="x") for i in range(10)]
        result = await svc.get_notifications(limit=3)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_returns_most_recent_within_limit(self, svc):
        svc.notifications = [NotificationMessage(title=str(i), message="x") for i in range(5)]
        result = await svc.get_notifications(limit=2)
        assert result[-1].title == "4"

    @pytest.mark.asyncio
    async def test_empty_service_returns_empty_list(self, svc):
        result = await svc.get_notifications()
        assert result == []


# ===========================================================================
# NotificationService.get_notification_stats
# ===========================================================================


class TestGetNotificationStats:
    @pytest.fixture
    def svc(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        return NotificationService()

    @pytest.mark.asyncio
    async def test_empty_returns_zeroes(self, svc):
        stats = await svc.get_notification_stats()
        assert stats["total"] == 0
        assert stats["by_category"] == {}
        assert stats["by_priority"] == {}

    @pytest.mark.asyncio
    async def test_total_counted(self, svc):
        svc.notifications = [
            NotificationMessage(title="A", message="a"),
            NotificationMessage(title="B", message="b"),
        ]
        stats = await svc.get_notification_stats()
        assert stats["total"] == 2

    @pytest.mark.asyncio
    async def test_by_category_counts(self, svc):
        svc.notifications = [
            NotificationMessage(title="A", message="a", category="alert"),
            NotificationMessage(title="B", message="b", category="alert"),
            NotificationMessage(title="C", message="c", category="system"),
        ]
        stats = await svc.get_notification_stats()
        assert stats["by_category"]["alert"] == 2
        assert stats["by_category"]["system"] == 1

    @pytest.mark.asyncio
    async def test_by_priority_counts(self, svc):
        svc.notifications = [
            NotificationMessage(title="A", message="a", priority="high"),
            NotificationMessage(title="B", message="b", priority="normal"),
            NotificationMessage(title="C", message="c", priority="normal"),
        ]
        stats = await svc.get_notification_stats()
        assert stats["by_priority"]["high"] == 1
        assert stats["by_priority"]["normal"] == 2


# ===========================================================================
# NotificationService.send_alert / send_system_notification / send_user_notification
# ===========================================================================


class TestSendHelpers:
    @pytest.fixture
    def svc(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        return NotificationService()

    @pytest.mark.asyncio
    async def test_send_alert_stores_notification(self, svc):
        await svc.send_alert("Disk Full", "Disk usage at 95%")
        assert len(svc.notifications) == 1
        assert svc.notifications[0].category == "alert"

    @pytest.mark.asyncio
    async def test_send_alert_default_priority_high(self, svc):
        await svc.send_alert("t", "m")
        assert svc.notifications[0].priority == "high"

    @pytest.mark.asyncio
    async def test_send_system_notification_category(self, svc):
        await svc.send_system_notification("Restart", "Server restarted")
        assert svc.notifications[0].category == "system"

    @pytest.mark.asyncio
    async def test_send_user_notification_sets_recipient(self, svc):
        await svc.send_user_notification("user-1", "Welcome", "Hello!")
        assert svc.notifications[0].recipient == "user-1"
        assert svc.notifications[0].category == "user"

    @pytest.mark.asyncio
    async def test_send_notification_returns_true(self, svc):
        result = await svc.send_alert("t", "m")
        assert result is True
