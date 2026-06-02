"""Unit tests for AuditAction, AuditLevel, SecurityEventType, SeverityLevel, AuditLog, SecurityEvent."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.models.audit import (
    AuditAction,
    AuditLevel,
    AuditLog,
    SecurityEvent,
    SecurityEventType,
    SeverityLevel,
)


# ===========================================================================
# AuditAction enum
# ===========================================================================


class TestAuditActionEnum:
    def test_create_value(self):
        assert AuditAction.CREATE.value == "create"

    def test_read_value(self):
        assert AuditAction.READ.value == "read"

    def test_update_value(self):
        assert AuditAction.UPDATE.value == "update"

    def test_delete_value(self):
        assert AuditAction.DELETE.value == "delete"

    def test_login_value(self):
        assert AuditAction.LOGIN.value == "login"

    def test_logout_value(self):
        assert AuditAction.LOGOUT.value == "logout"

    def test_download_value(self):
        assert AuditAction.DOWNLOAD.value == "download"

    def test_upload_value(self):
        assert AuditAction.UPLOAD.value == "upload"

    def test_process_value(self):
        assert AuditAction.PROCESS.value == "process"

    def test_export_value(self):
        assert AuditAction.EXPORT.value == "export"

    def test_import_value(self):
        assert AuditAction.IMPORT.value == "import"

    def test_configure_value(self):
        assert AuditAction.CONFIGURE.value == "configure"

    def test_has_twelve_members(self):
        assert len(AuditAction) == 12


# ===========================================================================
# AuditLevel enum
# ===========================================================================


class TestAuditLevelEnum:
    def test_info_value(self):
        assert AuditLevel.INFO.value == "info"

    def test_warning_value(self):
        assert AuditLevel.WARNING.value == "warning"

    def test_error_value(self):
        assert AuditLevel.ERROR.value == "error"

    def test_critical_value(self):
        assert AuditLevel.CRITICAL.value == "critical"

    def test_has_four_members(self):
        assert len(AuditLevel) == 4


# ===========================================================================
# SecurityEventType enum
# ===========================================================================


class TestSecurityEventTypeEnum:
    def test_authentication_failure_value(self):
        assert SecurityEventType.AUTHENTICATION_FAILURE.value == "authentication_failure"

    def test_authorization_failure_value(self):
        assert SecurityEventType.AUTHORIZATION_FAILURE.value == "authorization_failure"

    def test_suspicious_activity_value(self):
        assert SecurityEventType.SUSPICIOUS_ACTIVITY.value == "suspicious_activity"

    def test_data_breach_attempt_value(self):
        assert SecurityEventType.DATA_BREACH_ATTEMPT.value == "data_breach_attempt"

    def test_unusual_access_pattern_value(self):
        assert SecurityEventType.UNUSUAL_ACCESS_PATTERN.value == "unusual_access_pattern"

    def test_malicious_request_value(self):
        assert SecurityEventType.MALICIOUS_REQUEST.value == "malicious_request"

    def test_rate_limit_exceeded_value(self):
        assert SecurityEventType.RATE_LIMIT_EXCEEDED.value == "rate_limit_exceeded"

    def test_privilege_escalation_value(self):
        assert SecurityEventType.PRIVILEGE_ESCALATION.value == "privilege_escalation"

    def test_sql_injection_attempt_value(self):
        assert SecurityEventType.SQL_INJECTION_ATTEMPT.value == "sql_injection_attempt"

    def test_xss_attempt_value(self):
        assert SecurityEventType.XSS_ATTEMPT.value == "xss_attempt"

    def test_has_ten_members(self):
        assert len(SecurityEventType) == 10


# ===========================================================================
# SeverityLevel enum
# ===========================================================================


class TestSeverityLevelEnum:
    def test_low_value(self):
        assert SeverityLevel.LOW.value == "low"

    def test_medium_value(self):
        assert SeverityLevel.MEDIUM.value == "medium"

    def test_high_value(self):
        assert SeverityLevel.HIGH.value == "high"

    def test_critical_value(self):
        assert SeverityLevel.CRITICAL.value == "critical"

    def test_has_four_members(self):
        assert len(SeverityLevel) == 4


# ===========================================================================
# AuditLog.is_sensitive_action
# ===========================================================================


class TestAuditLogIsSensitiveAction:
    def _isa(self, action: AuditAction) -> bool:
        log = AuditLog(action=action, resource_type="test", description="test", tenant_id="test")
        return log.is_sensitive_action()

    def test_delete_is_sensitive(self):
        assert self._isa(AuditAction.DELETE) is True

    def test_export_is_sensitive(self):
        assert self._isa(AuditAction.EXPORT) is True

    def test_configure_is_sensitive(self):
        assert self._isa(AuditAction.CONFIGURE) is True

    def test_create_is_not_sensitive(self):
        assert self._isa(AuditAction.CREATE) is False

    def test_read_is_not_sensitive(self):
        assert self._isa(AuditAction.READ) is False

    def test_login_is_not_sensitive(self):
        assert self._isa(AuditAction.LOGIN) is False

    def test_update_is_not_sensitive(self):
        assert self._isa(AuditAction.UPDATE) is False


# ===========================================================================
# AuditLog.get_change_summary
# ===========================================================================


class TestAuditLogGetChangeSummary:
    def _gcs(self, old: dict | None, new: dict | None) -> str | None:
        log = AuditLog(
            action=AuditAction.UPDATE,
            resource_type="test",
            description="test",
            tenant_id="test",
            old_values=old,
            new_values=new,
        )
        return log.get_change_summary()

    def test_returns_none_when_no_old_values(self):
        assert self._gcs(None, {"name": "new"}) is None

    def test_returns_none_when_no_new_values(self):
        assert self._gcs({"name": "old"}, None) is None

    def test_returns_none_when_both_none(self):
        assert self._gcs(None, None) is None

    def test_returns_change_description(self):
        summary = self._gcs({"status": "active"}, {"status": "inactive"})
        assert "status" in summary
        assert "active" in summary
        assert "inactive" in summary

    def test_returns_empty_string_when_no_actual_changes(self):
        assert self._gcs({"name": "same"}, {"name": "same"}) == ""

    def test_multiple_changes_separated_by_semicolons(self):
        summary = self._gcs({"a": 1, "b": 2}, {"a": 10, "b": 20})
        assert ";" in summary


# ===========================================================================
# SecurityEvent.is_critical
# ===========================================================================


class TestSecurityEventIsCritical:
    def _ic(self, severity: SeverityLevel) -> bool:
        event = SecurityEvent(
            event_type=SecurityEventType.SQL_INJECTION_ATTEMPT,
            severity=severity,
            title="test",
            description="test",
            tenant_id="test",
        )
        return event.is_critical()

    def test_critical_severity_is_critical(self):
        assert self._ic(SeverityLevel.CRITICAL) is True

    def test_high_severity_is_not_critical(self):
        assert self._ic(SeverityLevel.HIGH) is False

    def test_medium_severity_is_not_critical(self):
        assert self._ic(SeverityLevel.MEDIUM) is False

    def test_low_severity_is_not_critical(self):
        assert self._ic(SeverityLevel.LOW) is False


# ===========================================================================
# SecurityEvent.needs_immediate_attention
# ===========================================================================


class TestSecurityEventNeedsImmediateAttention:
    def _nia(self, severity: SeverityLevel, investigated: bool = False, false_positive: bool = False) -> bool:
        event = SecurityEvent(
            event_type=SecurityEventType.SQL_INJECTION_ATTEMPT,
            severity=severity,
            title="test",
            description="test",
            tenant_id="test",
            investigated=investigated,
            false_positive=false_positive,
        )
        return event.needs_immediate_attention()

    def test_high_uninvestigated_non_false_positive_needs_attention(self):
        assert self._nia(SeverityLevel.HIGH) is True

    def test_critical_uninvestigated_non_false_positive_needs_attention(self):
        assert self._nia(SeverityLevel.CRITICAL) is True

    def test_medium_severity_does_not_need_attention(self):
        assert self._nia(SeverityLevel.MEDIUM) is False

    def test_already_investigated_does_not_need_attention(self):
        assert self._nia(SeverityLevel.HIGH, investigated=True) is False

    def test_false_positive_does_not_need_attention(self):
        assert self._nia(SeverityLevel.HIGH, false_positive=True) is False


# ===========================================================================
# SecurityEvent.get_threat_summary
# ===========================================================================


class TestSecurityEventGetThreatSummary:
    @pytest.fixture
    def event(self) -> SecurityEvent:
        return SecurityEvent(
            event_type=SecurityEventType.SQL_INJECTION_ATTEMPT,
            severity=SeverityLevel.HIGH,
            title="test",
            description="test",
            tenant_id="test",
            blocked=True,
            source_ip=None,
            country="US",
            investigated=False,
            resolved=False,
        )

    def test_returns_dict(self, event):
        assert isinstance(SecurityEvent.get_threat_summary(event), dict)

    def test_event_type_value_present(self, event):
        assert SecurityEvent.get_threat_summary(event)["event_type"] == "sql_injection_attempt"

    def test_severity_value_present(self, event):
        assert SecurityEvent.get_threat_summary(event)["severity"] == "high"

    def test_blocked_present(self, event):
        assert SecurityEvent.get_threat_summary(event)["blocked"] is True

    def test_source_ip_none_when_not_set(self, event):
        assert SecurityEvent.get_threat_summary(event)["source_ip"] is None

    def test_country_present(self, event):
        assert SecurityEvent.get_threat_summary(event)["country"] == "US"

    def test_investigated_present(self, event):
        assert SecurityEvent.get_threat_summary(event)["investigated"] is False

    def test_resolved_present(self, event):
        assert SecurityEvent.get_threat_summary(event)["resolved"] is False
