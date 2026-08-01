"""
Unit tests for src/youtube_extension/core/mcp/validation.py

Covers:
- ContextValidationError (init, to_dict, __str__)
- ValidationResult (add_error, add_warning, has_errors, has_warnings, get_error_summary)
- MCPValidator (init, validate_context, validate_context_quick, add_custom_rule,
                 remove_custom_rule, get_validation_stats)
- All private validation methods
- Module-level convenience functions (get_validator, validate_context,
                                      validate_context_quick)
- Edge cases: security violations, expired/old contexts, malformed history, etc.
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from youtube_extension.core.mcp.context_manager import (
    ContextStatus,
    MCPContext,
)
from youtube_extension.core.mcp.validation import (
    ContextValidationError,
    MCPValidator,
    ValidationResult,
    ValidationRule,
    ValidationSeverity,
    get_validator,
    validate_context,
    validate_context_quick,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_context(**kwargs) -> MCPContext:
    """Return a minimal valid MCPContext with a fresh checksum."""
    defaults = dict(user="test_user", task="test_task", intent="test_intent")
    defaults.update(kwargs)
    ctx = MCPContext(**defaults)
    ctx.update_checksum()
    return ctx


# ---------------------------------------------------------------------------
# ContextValidationError
# ---------------------------------------------------------------------------


class TestContextValidationError:
    def test_minimal_init(self):
        err = ContextValidationError("something went wrong")
        assert err.message == "something went wrong"
        assert err.field is None
        assert err.rule is None
        assert err.severity == ValidationSeverity.ERROR
        assert err.details == {}
        assert str(err) == "something went wrong"

    def test_full_init(self):
        details = {"key": "value"}
        err = ContextValidationError(
            message="bad field",
            field="user",
            rule=ValidationRule.REQUIRED_FIELDS,
            severity=ValidationSeverity.CRITICAL,
            details=details,
        )
        assert err.field == "user"
        assert err.rule == ValidationRule.REQUIRED_FIELDS
        assert err.severity == ValidationSeverity.CRITICAL
        assert err.details == {"key": "value"}

    def test_details_defaults_to_empty_dict_when_none(self):
        err = ContextValidationError("msg", details=None)
        assert err.details == {}

    def test_to_dict_keys(self):
        err = ContextValidationError(
            "msg",
            field="task",
            rule=ValidationRule.DATA_TYPES,
            severity=ValidationSeverity.WARNING,
            details={"foo": "bar"},
        )
        d = err.to_dict()
        assert d["message"] == "msg"
        assert d["field"] == "task"
        assert d["rule"] == ValidationRule.DATA_TYPES.value
        assert d["severity"] == ValidationSeverity.WARNING.value
        assert d["details"] == {"foo": "bar"}
        assert "timestamp" in d

    def test_to_dict_without_rule(self):
        err = ContextValidationError("msg")
        d = err.to_dict()
        assert d["rule"] is None

    def test_to_dict_timestamp_is_recent_isoformat(self):
        err = ContextValidationError("msg")
        ts_str = err.to_dict()["timestamp"]
        # Must parse without error and be a plausible recent datetime
        ts = datetime.fromisoformat(ts_str)
        # Should be within a 60-second window of now
        delta = abs((datetime.utcnow() - ts).total_seconds())
        assert delta < 60

    def test_is_exception_subclass(self):
        err = ContextValidationError("oops")
        assert isinstance(err, Exception)
        with pytest.raises(ContextValidationError):
            raise err


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------


class TestValidationResult:
    def test_defaults(self):
        vr = ValidationResult()
        assert vr.is_valid is True
        assert vr.errors == []
        assert vr.warnings == []
        assert vr.metadata == {}

    # add_error ---

    def test_add_error_sets_invalid(self):
        vr = ValidationResult()
        vr.add_error("bad", severity=ValidationSeverity.ERROR)
        assert vr.is_valid is False
        assert len(vr.errors) == 1

    def test_add_error_critical_sets_invalid(self):
        vr = ValidationResult()
        vr.add_error("critical", severity=ValidationSeverity.CRITICAL)
        assert vr.is_valid is False

    def test_add_error_info_keeps_valid(self):
        vr = ValidationResult()
        vr.add_error("info only", severity=ValidationSeverity.INFO)
        # INFO severity should not flip is_valid
        assert vr.is_valid is True
        assert len(vr.errors) == 1

    def test_add_error_with_field_and_rule(self):
        vr = ValidationResult()
        vr.add_error(
            "missing",
            field="user",
            rule=ValidationRule.REQUIRED_FIELDS,
            details={"extra": 1},
        )
        err = vr.errors[0]
        assert err.field == "user"
        assert err.rule == ValidationRule.REQUIRED_FIELDS
        assert err.details == {"extra": 1}

    def test_add_multiple_errors(self):
        vr = ValidationResult()
        vr.add_error("e1")
        vr.add_error("e2")
        assert len(vr.errors) == 2

    # add_warning ---

    def test_add_warning_does_not_invalidate(self):
        vr = ValidationResult()
        vr.add_warning("watch out")
        assert vr.is_valid is True
        assert len(vr.warnings) == 1

    def test_add_warning_with_all_params(self):
        vr = ValidationResult()
        vr.add_warning("warn", field="expires_at", rule=ValidationRule.VALUE_RANGES, details={"d": 1})
        w = vr.warnings[0]
        assert w.field == "expires_at"
        assert w.rule == ValidationRule.VALUE_RANGES
        assert w.severity == ValidationSeverity.WARNING

    def test_add_multiple_warnings(self):
        vr = ValidationResult()
        vr.add_warning("w1")
        vr.add_warning("w2")
        vr.add_warning("w3")
        assert len(vr.warnings) == 3

    # has_errors / has_warnings ---

    def test_has_errors_false_initially(self):
        assert ValidationResult().has_errors() is False

    def test_has_errors_true_after_add(self):
        vr = ValidationResult()
        vr.add_error("e")
        assert vr.has_errors() is True

    def test_has_warnings_false_initially(self):
        assert ValidationResult().has_warnings() is False

    def test_has_warnings_true_after_add(self):
        vr = ValidationResult()
        vr.add_warning("w")
        assert vr.has_warnings() is True

    # get_error_summary ---

    def test_get_error_summary_structure(self):
        vr = ValidationResult()
        vr.add_error("e1")
        vr.add_warning("w1")
        summary = vr.get_error_summary()
        assert summary["is_valid"] is False
        assert summary["error_count"] == 1
        assert summary["warning_count"] == 1
        assert len(summary["errors"]) == 1
        assert len(summary["warnings"]) == 1

    def test_get_error_summary_empty(self):
        summary = ValidationResult().get_error_summary()
        assert summary["is_valid"] is True
        assert summary["error_count"] == 0
        assert summary["warning_count"] == 0


# ---------------------------------------------------------------------------
# MCPValidator – initialisation
# ---------------------------------------------------------------------------


class TestMCPValidatorInit:
    def test_initial_state(self):
        v = MCPValidator()
        assert v.custom_rules == {}
        assert isinstance(v.validation_stats, dict)

    def test_all_rules_in_stats(self):
        v = MCPValidator()
        for rule in ValidationRule:
            assert rule.value in v.validation_stats
            assert v.validation_stats[rule.value] == 0


# ---------------------------------------------------------------------------
# MCPValidator – custom rules
# ---------------------------------------------------------------------------


class TestMCPValidatorCustomRules:
    def test_add_custom_rule(self):
        v = MCPValidator()
        v.add_custom_rule("my_rule", lambda ctx, res: None)
        assert "my_rule" in v.custom_rules

    def test_remove_existing_custom_rule(self):
        v = MCPValidator()
        v.add_custom_rule("r", lambda ctx, res: None)
        result = v.remove_custom_rule("r")
        assert result is True
        assert "r" not in v.custom_rules

    def test_remove_nonexistent_custom_rule(self):
        v = MCPValidator()
        result = v.remove_custom_rule("nonexistent")
        assert result is False

    def test_custom_rule_is_called_during_validation(self):
        v = MCPValidator()
        calls = []
        v.add_custom_rule("spy", lambda ctx, res: calls.append(ctx.id))
        ctx = _make_context()
        v.validate_context(ctx)
        assert len(calls) == 1

    def test_failing_custom_rule_adds_error(self):
        v = MCPValidator()

        def bad_rule(ctx, res):
            raise RuntimeError("intentional failure")

        v.add_custom_rule("bad", bad_rule)
        ctx = _make_context()
        result = v.validate_context(ctx)
        assert any("bad" in e.message for e in result.errors)


# ---------------------------------------------------------------------------
# MCPValidator – get_validation_stats
# ---------------------------------------------------------------------------


class TestMCPValidatorStats:
    def test_initial_stats(self):
        v = MCPValidator()
        stats = v.get_validation_stats()
        assert stats["total_validations"] == 0
        assert stats["custom_rules"] == []

    def test_stats_update_after_validation(self):
        v = MCPValidator()
        ctx = _make_context()
        v.validate_context(ctx)
        stats = v.get_validation_stats()
        # Each built-in rule runs once per validate_context call
        assert stats["total_validations"] == len(ValidationRule)

    def test_stats_reflect_custom_rules(self):
        v = MCPValidator()
        v.add_custom_rule("x", lambda ctx, res: None)
        stats = v.get_validation_stats()
        assert "x" in stats["custom_rules"]


# ---------------------------------------------------------------------------
# MCPValidator – validate_context_quick
# ---------------------------------------------------------------------------


class TestValidateContextQuick:
    def test_valid_context_returns_true(self):
        v = MCPValidator()
        ctx = _make_context()
        assert v.validate_context_quick(ctx) is True

    def test_invalid_context_returns_false(self):
        v = MCPValidator()
        ctx = _make_context()
        ctx.checksum = "bad_checksum"
        assert v.validate_context_quick(ctx) is False


# ---------------------------------------------------------------------------
# MCPValidator – validate_context: dict input
# ---------------------------------------------------------------------------


class TestValidateContextDict:
    def test_valid_dict(self):
        v = MCPValidator()
        ctx = _make_context()
        d = ctx.dict()
        result = v.validate_context(d)
        assert isinstance(result, ValidationResult)

    def test_dict_missing_required_field_raises_schema_error(self):
        v = MCPValidator()
        # 'user' is required; Pydantic will raise ValidationError internally
        result = v.validate_context({"task": "t", "intent": "i"})
        # The pydantic error should be captured as a validation error
        assert result.has_errors()

    def test_completely_invalid_dict_adds_error(self):
        v = MCPValidator()
        result = v.validate_context({"user": "u", "task": "t", "intent": "i"})
        # No checksum -> integrity check fails
        assert result.has_errors()


# ---------------------------------------------------------------------------
# _validate_required_fields
# ---------------------------------------------------------------------------


class TestValidateRequiredFields:
    def test_all_required_fields_present(self):
        v = MCPValidator()
        ctx = _make_context()
        result = ValidationResult()
        v._validate_required_fields(ctx, result)
        required_errors = [e for e in result.errors if e.rule == ValidationRule.REQUIRED_FIELDS]
        assert required_errors == []

    def test_empty_user_flagged(self):
        v = MCPValidator()
        ctx = _make_context(user="   ")
        result = ValidationResult()
        v._validate_required_fields(ctx, result)
        fields = [e.field for e in result.errors]
        assert "user" in fields

    def test_empty_task_flagged(self):
        v = MCPValidator()
        ctx = _make_context(task="")
        result = ValidationResult()
        v._validate_required_fields(ctx, result)
        fields = [e.field for e in result.errors]
        assert "task" in fields

    def test_empty_intent_flagged(self):
        v = MCPValidator()
        ctx = _make_context(intent="")
        result = ValidationResult()
        v._validate_required_fields(ctx, result)
        fields = [e.field for e in result.errors]
        assert "intent" in fields

    def test_stats_incremented(self):
        v = MCPValidator()
        ctx = _make_context()
        result = ValidationResult()
        v._validate_required_fields(ctx, result)
        assert v.validation_stats[ValidationRule.REQUIRED_FIELDS.value] == 1


# ---------------------------------------------------------------------------
# _validate_data_types
# ---------------------------------------------------------------------------


class TestValidateDataTypes:
    def test_valid_types_no_errors(self):
        v = MCPValidator()
        ctx = _make_context()
        result = ValidationResult()
        v._validate_data_types(ctx, result)
        dt_errors = [e for e in result.errors if e.rule == ValidationRule.DATA_TYPES]
        assert dt_errors == []

    def test_invalid_history_type(self):
        v = MCPValidator()
        ctx = _make_context()
        # Bypass Pydantic by direct attribute mutation
        object.__setattr__(ctx, "history", "not_a_list")
        result = ValidationResult()
        v._validate_data_types(ctx, result)
        fields = [e.field for e in result.errors]
        assert "history" in fields

    def test_invalid_metadata_type(self):
        v = MCPValidator()
        ctx = _make_context()
        object.__setattr__(ctx, "metadata", "not_a_dict")
        result = ValidationResult()
        v._validate_data_types(ctx, result)
        fields = [e.field for e in result.errors]
        assert "metadata" in fields

    def test_invalid_code_state_type(self):
        v = MCPValidator()
        ctx = _make_context()
        object.__setattr__(ctx, "code_state", [1, 2, 3])
        result = ValidationResult()
        v._validate_data_types(ctx, result)
        fields = [e.field for e in result.errors]
        assert "code_state" in fields

    def test_stats_incremented(self):
        v = MCPValidator()
        ctx = _make_context()
        result = ValidationResult()
        v._validate_data_types(ctx, result)
        assert v.validation_stats[ValidationRule.DATA_TYPES.value] == 1


# ---------------------------------------------------------------------------
# _validate_value_ranges
# ---------------------------------------------------------------------------


class TestValidateValueRanges:
    def test_valid_uuid_no_warning(self):
        v = MCPValidator()
        ctx = _make_context()
        # id generated by _make_context is a proper UUID
        result = ValidationResult()
        v._validate_value_ranges(ctx, result)
        id_warnings = [w for w in result.warnings if w.field == "id"]
        assert id_warnings == []

    def test_non_uuid_id_adds_warning(self):
        v = MCPValidator()
        ctx = _make_context()
        object.__setattr__(ctx, "id", "not-a-uuid-at-all!!")
        result = ValidationResult()
        v._validate_value_ranges(ctx, result)
        id_warnings = [w for w in result.warnings if w.field == "id"]
        assert len(id_warnings) == 1

    def test_past_expiry_adds_warning(self):
        v = MCPValidator()
        ctx = _make_context()
        # Set expiry to an hour ago
        object.__setattr__(ctx, "expires_at", datetime.utcnow() - timedelta(hours=1))
        result = ValidationResult()
        v._validate_value_ranges(ctx, result)
        exp_warnings = [w for w in result.warnings if w.field == "expires_at"]
        assert len(exp_warnings) == 1

    def test_future_expiry_no_warning(self):
        v = MCPValidator()
        ctx = _make_context()
        result = ValidationResult()
        v._validate_value_ranges(ctx, result)
        exp_warnings = [w for w in result.warnings if w.field == "expires_at"]
        assert exp_warnings == []

    def test_invalid_priority_adds_error(self):
        v = MCPValidator()
        ctx = _make_context()
        object.__setattr__(ctx, "priority", "INVALID_PRIORITY")
        result = ValidationResult()
        v._validate_value_ranges(ctx, result)
        prio_errors = [e for e in result.errors if e.field == "priority"]
        assert len(prio_errors) == 1

    def test_stats_incremented(self):
        v = MCPValidator()
        ctx = _make_context()
        result = ValidationResult()
        v._validate_value_ranges(ctx, result)
        assert v.validation_stats[ValidationRule.VALUE_RANGES.value] == 1


# ---------------------------------------------------------------------------
# _validate_format
# ---------------------------------------------------------------------------


class TestValidateFormat:
    def test_no_history_no_errors(self):
        v = MCPValidator()
        ctx = _make_context()
        result = ValidationResult()
        v._validate_format(ctx, result)
        assert not result.has_errors()

    def test_valid_history_entry_no_errors(self):
        v = MCPValidator()
        ctx = _make_context()
        ctx.add_history_entry("start", {"detail": "x"})
        # Rebuild checksum after mutation
        ctx.update_checksum()
        result = ValidationResult()
        v._validate_format(ctx, result)
        assert not result.has_errors()

    def test_history_entry_missing_timestamp(self):
        v = MCPValidator()
        ctx = _make_context()
        object.__setattr__(ctx, "history", [{"action": "run"}])
        result = ValidationResult()
        v._validate_format(ctx, result)
        fields = [e.field for e in result.errors]
        assert "history[0]" in fields

    def test_history_entry_missing_action(self):
        v = MCPValidator()
        ctx = _make_context()
        object.__setattr__(ctx, "history", [{"timestamp": "2024-01-01T00:00:00"}])
        result = ValidationResult()
        v._validate_format(ctx, result)
        fields = [e.field for e in result.errors]
        assert "history[0]" in fields

    def test_history_entry_invalid_timestamp_format(self):
        v = MCPValidator()
        ctx = _make_context()
        object.__setattr__(
            ctx,
            "history",
            [{"timestamp": "not-a-date", "action": "run"}],
        )
        result = ValidationResult()
        v._validate_format(ctx, result)
        fields = [e.field for e in result.errors]
        assert "history[0].timestamp" in fields

    def test_history_entry_valid_z_timestamp(self):
        v = MCPValidator()
        ctx = _make_context()
        object.__setattr__(
            ctx,
            "history",
            [{"timestamp": "2024-06-01T12:00:00Z", "action": "run"}],
        )
        result = ValidationResult()
        v._validate_format(ctx, result)
        # Valid Z-suffixed timestamp should not add format errors
        ts_errors = [e for e in result.errors if "timestamp" in (e.field or "")]
        assert ts_errors == []

    def test_stats_incremented(self):
        v = MCPValidator()
        ctx = _make_context()
        result = ValidationResult()
        v._validate_format(ctx, result)
        assert v.validation_stats[ValidationRule.FORMAT_VALIDATION.value] == 1


# ---------------------------------------------------------------------------
# _validate_integrity
# ---------------------------------------------------------------------------


class TestValidateIntegrity:
    def test_valid_checksum_passes(self):
        v = MCPValidator()
        ctx = _make_context()
        result = ValidationResult()
        v._validate_integrity(ctx, result)
        integrity_errors = [
            e for e in result.errors if e.rule == ValidationRule.INTEGRITY_CHECK
        ]
        assert integrity_errors == []

    def test_tampered_checksum_fails(self):
        v = MCPValidator()
        ctx = _make_context()
        object.__setattr__(ctx, "checksum", "tampered_value")
        result = ValidationResult()
        v._validate_integrity(ctx, result)
        integrity_errors = [
            e for e in result.errors if e.rule == ValidationRule.INTEGRITY_CHECK
        ]
        assert len(integrity_errors) == 1

    def test_no_checksum_fails(self):
        v = MCPValidator()
        ctx = MCPContext(user="u", task="t", intent="i")
        # No checksum set – validate_integrity returns False
        result = ValidationResult()
        v._validate_integrity(ctx, result)
        assert result.has_errors()

    def test_integrity_error_is_critical(self):
        v = MCPValidator()
        ctx = _make_context()
        object.__setattr__(ctx, "checksum", "bad")
        result = ValidationResult()
        v._validate_integrity(ctx, result)
        err = result.errors[0]
        assert err.severity == ValidationSeverity.CRITICAL

    def test_stats_incremented(self):
        v = MCPValidator()
        ctx = _make_context()
        result = ValidationResult()
        v._validate_integrity(ctx, result)
        assert v.validation_stats[ValidationRule.INTEGRITY_CHECK.value] == 1


# ---------------------------------------------------------------------------
# _validate_security
# ---------------------------------------------------------------------------


class TestValidateSecurity:
    def test_clean_metadata_no_errors(self):
        v = MCPValidator()
        ctx = _make_context()
        result = ValidationResult()
        v._validate_security(ctx, result)
        assert not result.has_errors()

    @pytest.mark.parametrize("dangerous", [
        "<script>alert(1)</script>",
        "javascript:void(0)",
        "data:text/html,<h1>",
        "vbscript:msgbox(1)",
    ])
    def test_dangerous_metadata_content_adds_error(self, dangerous):
        v = MCPValidator()
        ctx = _make_context(metadata={"payload": dangerous})
        ctx.update_checksum()
        result = ValidationResult()
        v._validate_security(ctx, result)
        sec_errors = [e for e in result.errors if e.rule == ValidationRule.SECURITY_CHECK]
        assert len(sec_errors) >= 1

    def test_dangerous_content_severity_is_critical(self):
        v = MCPValidator()
        ctx = _make_context(metadata={"x": "<script>evil</script>"})
        ctx.update_checksum()
        result = ValidationResult()
        v._validate_security(ctx, result)
        sec_errors = [e for e in result.errors if e.rule == ValidationRule.SECURITY_CHECK]
        assert all(e.severity == ValidationSeverity.CRITICAL for e in sec_errors)

    def test_long_string_field_adds_warning(self):
        v = MCPValidator()
        long_task = "A" * 10001
        ctx = _make_context(task=long_task)
        ctx.update_checksum()
        result = ValidationResult()
        v._validate_security(ctx, result)
        length_warnings = [
            w for w in result.warnings if w.rule == ValidationRule.SECURITY_CHECK
        ]
        assert len(length_warnings) >= 1

    def test_boundary_string_exactly_max_length_no_warning(self):
        v = MCPValidator()
        ctx = _make_context(task="B" * 10000)
        ctx.update_checksum()
        result = ValidationResult()
        v._validate_security(ctx, result)
        length_warnings = [
            w for w in result.warnings if w.rule == ValidationRule.SECURITY_CHECK and w.field == "task"
        ]
        assert length_warnings == []

    def test_stats_incremented(self):
        v = MCPValidator()
        ctx = _make_context()
        result = ValidationResult()
        v._validate_security(ctx, result)
        assert v.validation_stats[ValidationRule.SECURITY_CHECK.value] == 1


# ---------------------------------------------------------------------------
# _validate_compliance
# ---------------------------------------------------------------------------


class TestValidateCompliance:
    def test_missing_compliance_fields_add_warnings(self):
        v = MCPValidator()
        ctx = _make_context()  # empty metadata
        result = ValidationResult()
        v._validate_compliance(ctx, result)
        warn_fields = [w.field for w in result.warnings]
        assert "metadata.data_retention" in warn_fields
        assert "metadata.privacy_level" in warn_fields
        assert "metadata.audit_required" in warn_fields

    def test_all_compliance_fields_present_no_warnings(self):
        v = MCPValidator()
        ctx = _make_context(
            metadata={
                "data_retention": "30d",
                "privacy_level": "internal",
                "audit_required": True,
            }
        )
        ctx.update_checksum()
        result = ValidationResult()
        v._validate_compliance(ctx, result)
        compliance_warnings = [
            w for w in result.warnings if w.rule == ValidationRule.COMPLIANCE_CHECK
            and "metadata." in (w.field or "")
        ]
        assert compliance_warnings == []

    def test_old_active_context_adds_warning(self):
        v = MCPValidator()
        ctx = _make_context(
            metadata={
                "data_retention": "30d",
                "privacy_level": "internal",
                "audit_required": True,
            }
        )
        # Make the context 31 days old
        object.__setattr__(ctx, "created_at", datetime.utcnow() - timedelta(days=31))
        ctx.update_checksum()
        result = ValidationResult()
        v._validate_compliance(ctx, result)
        age_warnings = [
            w for w in result.warnings
            if w.rule == ValidationRule.COMPLIANCE_CHECK and w.field == "status"
        ]
        assert len(age_warnings) == 1
        assert age_warnings[0].details["age_days"] >= 31

    def test_old_completed_context_no_age_warning(self):
        v = MCPValidator()
        ctx = _make_context(
            metadata={
                "data_retention": "30d",
                "privacy_level": "internal",
                "audit_required": True,
            }
        )
        object.__setattr__(ctx, "created_at", datetime.utcnow() - timedelta(days=31))
        object.__setattr__(ctx, "status", ContextStatus.COMPLETED)
        ctx.update_checksum()
        result = ValidationResult()
        v._validate_compliance(ctx, result)
        age_warnings = [
            w for w in result.warnings
            if w.rule == ValidationRule.COMPLIANCE_CHECK and w.field == "status"
        ]
        assert age_warnings == []

    def test_stats_incremented(self):
        v = MCPValidator()
        ctx = _make_context()
        result = ValidationResult()
        v._validate_compliance(ctx, result)
        assert v.validation_stats[ValidationRule.COMPLIANCE_CHECK.value] == 1


# ---------------------------------------------------------------------------
# validate_context – full pipeline integration via MCPValidator
# ---------------------------------------------------------------------------


class TestValidateContextFull:
    def test_valid_context_no_errors_no_warnings(self):
        v = MCPValidator()
        ctx = _make_context(
            metadata={
                "data_retention": "30d",
                "privacy_level": "low",
                "audit_required": False,
            }
        )
        ctx.update_checksum()
        result = v.validate_context(ctx)
        assert result.is_valid is True
        assert not result.has_errors()

    def test_result_is_validation_result_instance(self):
        v = MCPValidator()
        ctx = _make_context()
        result = v.validate_context(ctx)
        assert isinstance(result, ValidationResult)

    def test_all_validation_stats_incremented(self):
        v = MCPValidator()
        ctx = _make_context()
        v.validate_context(ctx)
        for rule in ValidationRule:
            assert v.validation_stats[rule.value] == 1

    def test_unexpected_exception_captured_as_critical(self):
        v = MCPValidator()
        ctx = _make_context()
        # Make _validate_required_fields explode
        with patch.object(
            v,
            "_validate_required_fields",
            side_effect=RuntimeError("boom"),
        ):
            result = v.validate_context(ctx)
        critical_errors = [
            e for e in result.errors
            if e.severity == ValidationSeverity.CRITICAL
        ]
        assert len(critical_errors) >= 1

    def test_pydantic_validation_error_from_bad_dict(self):
        v = MCPValidator()
        # 'user' required – missing it should trigger pydantic ValidationError path
        result = v.validate_context({"task": "t", "intent": "i"})
        assert result.has_errors()

    def test_second_validation_doubles_stats(self):
        v = MCPValidator()
        ctx = _make_context()
        v.validate_context(ctx)
        v.validate_context(ctx)
        for rule in ValidationRule:
            assert v.validation_stats[rule.value] == 2


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------


class TestModuleFunctions:
    def test_get_validator_returns_mcpvalidator(self):
        # Reset global before test
        import youtube_extension.core.mcp.validation as mod
        mod._validator = None
        v = get_validator()
        assert isinstance(v, MCPValidator)

    def test_get_validator_singleton(self):
        import youtube_extension.core.mcp.validation as mod
        mod._validator = None
        v1 = get_validator()
        v2 = get_validator()
        assert v1 is v2

    def test_module_validate_context_returns_result(self):
        ctx = _make_context()
        result = validate_context(ctx)
        assert isinstance(result, ValidationResult)

    def test_module_validate_context_quick_valid(self):
        ctx = _make_context()
        assert validate_context_quick(ctx) is True

    def test_module_validate_context_quick_invalid(self):
        ctx = _make_context()
        object.__setattr__(ctx, "checksum", "bad")
        assert validate_context_quick(ctx) is False


# ---------------------------------------------------------------------------
# Enum completeness
# ---------------------------------------------------------------------------


class TestEnums:
    def test_validation_severity_values(self):
        values = {s.value for s in ValidationSeverity}
        assert values == {"info", "warning", "error", "critical"}

    def test_validation_rule_values(self):
        values = {r.value for r in ValidationRule}
        expected = {
            "required_fields",
            "data_types",
            "value_ranges",
            "format_validation",
            "integrity_check",
            "security_check",
            "compliance_check",
        }
        assert values == expected
