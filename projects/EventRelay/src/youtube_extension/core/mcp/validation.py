"""
MCP Context Validation - Context Integrity and Validation

This module provides comprehensive validation for MCP contexts, ensuring
data integrity, security, and compliance across the system.

Key Responsibilities:
- Context schema validation
- Data integrity checking
- Security validation
- Compliance checking
- Error reporting and recovery
"""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Union
from enum import Enum
import hashlib

from pydantic import BaseModel, Field, ValidationError, validator

from .context_manager import MCPContext, ContextStatus, ContextPriority

# Configure logging
logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Validation Error Severity Levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationRule(Enum):
    """Built-in Validation Rules"""
    REQUIRED_FIELDS = "required_fields"
    DATA_TYPES = "data_types"
    VALUE_RANGES = "value_ranges"
    FORMAT_VALIDATION = "format_validation"
    INTEGRITY_CHECK = "integrity_check"
    SECURITY_CHECK = "security_check"
    COMPLIANCE_CHECK = "compliance_check"


class ContextValidationError(Exception):
    """
    MCP Context Validation Error

    Custom exception for context validation failures with detailed error information.
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        rule: Optional[ValidationRule] = None,
        severity: ValidationSeverity = ValidationSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.field = field
        self.rule = rule
        self.severity = severity
        self.details = details or {}

        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization"""
        return {
            "message": self.message,
            "field": self.field,
            "rule": self.rule.value if self.rule else None,
            "severity": self.severity.value,
            "details": self.details,
            "timestamp": datetime.utcnow().isoformat()
        }


class ValidationResult(BaseModel):
    """Result of a validation operation"""

    is_valid: bool = Field(default=True)
    errors: List[ContextValidationError] = Field(default_factory=list)
    warnings: List[ContextValidationError] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_error(
        self,
        message: str,
        field: Optional[str] = None,
        rule: Optional[ValidationRule] = None,
        severity: ValidationSeverity = ValidationSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a validation error"""
        error = ContextValidationError(message, field, rule, severity, details)
        self.errors.append(error)
        if severity != ValidationSeverity.INFO:
            self.is_valid = False

    def add_warning(
        self,
        message: str,
        field: Optional[str] = None,
        rule: Optional[ValidationRule] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a validation warning"""
        warning = ContextValidationError(message, field, rule, ValidationSeverity.WARNING, details)
        self.warnings.append(warning)

    def has_errors(self) -> bool:
        """Check if there are any validation errors"""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are any validation warnings"""
        return len(self.warnings) > 0

    def get_error_summary(self) -> Dict[str, Any]:
        """Get a summary of validation results"""
        return {
            "is_valid": self.is_valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": [error.to_dict() for error in self.errors],
            "warnings": [warning.to_dict() for warning in self.warnings]
        }


class MCPValidator:
    """
    MCP Context Validator - Comprehensive context validation system

    Provides multi-layer validation for MCP contexts including schema validation,
    data integrity, security checks, and compliance verification.
    """

    def __init__(self):
        """Initialize the MCP Validator"""
        self.custom_rules: Dict[str, callable] = {}
        self.validation_stats: Dict[str, int] = {}

        # Initialize validation statistics
        for rule in ValidationRule:
            self.validation_stats[rule.value] = 0

        logger.info("MCP Validator initialized")

    def validate_context(self, context: Union[MCPContext, Dict[str, Any]]) -> ValidationResult:
        """
        Perform comprehensive validation on an MCP context

        Args:
            context: MCPContext instance or context data dictionary

        Returns:
            ValidationResult with detailed validation information
        """
        result = ValidationResult()

        try:
            # Convert to MCPContext if it's a dict
            if isinstance(context, dict):
                context_obj = MCPContext(**context)
            else:
                context_obj = context

            # Run all validation rules
            self._validate_required_fields(context_obj, result)
            self._validate_data_types(context_obj, result)
            self._validate_value_ranges(context_obj, result)
            self._validate_format(context_obj, result)
            self._validate_integrity(context_obj, result)
            self._validate_security(context_obj, result)
            self._validate_compliance(context_obj, result)

            # Run custom validation rules
            for rule_name, rule_func in self.custom_rules.items():
                try:
                    rule_func(context_obj, result)
                except Exception as e:
                    logger.error(f"Custom validation rule '{rule_name}' failed: {e}")
                    result.add_error(
                        f"Custom validation rule '{rule_name}' failed: {str(e)}",
                        rule=ValidationRule.SECURITY_CHECK
                    )

            # Update validation statistics
            self._update_validation_stats(result)

        except ValidationError as e:
            # Handle Pydantic validation errors
            for error in e.errors():
                field_path = ".".join(str(loc) for loc in error["loc"])
                result.add_error(
                    f"Schema validation failed for field '{field_path}': {error['msg']}",
                    field=field_path,
                    rule=ValidationRule.DATA_TYPES,
                    details={"pydantic_error": error}
                )

        except Exception as e:
            result.add_error(
                f"Unexpected validation error: {str(e)}",
                severity=ValidationSeverity.CRITICAL,
                details={"exception_type": type(e).__name__}
            )

        return result

    def validate_context_quick(self, context: Union[MCPContext, Dict[str, Any]]) -> bool:
        """
        Quick validation check - returns True if context is valid, False otherwise

        Args:
            context: MCPContext instance or context data dictionary

        Returns:
            True if valid, False if any errors found
        """
        result = self.validate_context(context)
        return result.is_valid

    def add_custom_rule(self, name: str, rule_func: callable) -> None:
        """
        Add a custom validation rule

        Args:
            name: Unique name for the validation rule
            rule_func: Function that takes (context, result) and adds errors/warnings to result
        """
        self.custom_rules[name] = rule_func
        logger.info(f"Added custom validation rule: {name}")

    def remove_custom_rule(self, name: str) -> bool:
        """
        Remove a custom validation rule

        Args:
            name: Name of the validation rule to remove

        Returns:
            True if rule was removed, False if not found
        """
        if name in self.custom_rules:
            del self.custom_rules[name]
            logger.info(f"Removed custom validation rule: {name}")
            return True
        return False

    def get_validation_stats(self) -> Dict[str, Any]:
        """
        Get validation statistics

        Returns:
            Dictionary with validation statistics
        """
        return {
            "total_validations": sum(self.validation_stats.values()),
            "rule_breakdown": self.validation_stats.copy(),
            "custom_rules": list(self.custom_rules.keys())
        }

    def _validate_required_fields(self, context: MCPContext, result: ValidationResult) -> None:
        """Validate required fields are present and not empty"""
        self.validation_stats[ValidationRule.REQUIRED_FIELDS.value] += 1

        required_fields = ['id', 'user', 'task', 'intent']

        for field in required_fields:
            value = getattr(context, field)
            if not value or (isinstance(value, str) and not value.strip()):
                result.add_error(
                    f"Required field '{field}' is missing or empty",
                    field=field,
                    rule=ValidationRule.REQUIRED_FIELDS
                )

    def _validate_data_types(self, context: MCPContext, result: ValidationResult) -> None:
        """Validate data types of context fields"""
        self.validation_stats[ValidationRule.DATA_TYPES.value] += 1

        # Validate string fields
        string_fields = ['id', 'user', 'task', 'intent', 'env', 'subtask']
        for field in string_fields:
            value = getattr(context, field)
            if value is not None and not isinstance(value, str):
                result.add_error(
                    f"Field '{field}' must be a string, got {type(value).__name__}",
                    field=field,
                    rule=ValidationRule.DATA_TYPES
                )

        # Validate list fields
        if not isinstance(context.history, list):
            result.add_error(
                "Field 'history' must be a list",
                field="history",
                rule=ValidationRule.DATA_TYPES
            )

        # Validate dict fields
        dict_fields = ['code_state', 'metadata']
        for field in dict_fields:
            value = getattr(context, field)
            if value is not None and not isinstance(value, dict):
                result.add_error(
                    f"Field '{field}' must be a dictionary, got {type(value).__name__}",
                    field=field,
                    rule=ValidationRule.DATA_TYPES
                )

    def _validate_value_ranges(self, context: MCPContext, result: ValidationResult) -> None:
        """Validate value ranges and constraints"""
        self.validation_stats[ValidationRule.VALUE_RANGES.value] += 1

        # Validate ID format (should be UUID-like)
        if context.id and not re.match(r'^[a-f0-9\-]{36}$', context.id):
            result.add_warning(
                "Context ID should be a valid UUID format",
                field="id",
                rule=ValidationRule.VALUE_RANGES
            )

        # Validate expiration is in the future
        if context.expires_at and context.expires_at <= datetime.utcnow():
            result.add_warning(
                "Context expiration date is in the past",
                field="expires_at",
                rule=ValidationRule.VALUE_RANGES
            )

        # Validate priority is valid enum
        if not isinstance(context.priority, ContextPriority):
            result.add_error(
                f"Invalid priority value: {context.priority}",
                field="priority",
                rule=ValidationRule.VALUE_RANGES
            )

    def _validate_format(self, context: MCPContext, result: ValidationResult) -> None:
        """Validate data format and structure"""
        self.validation_stats[ValidationRule.FORMAT_VALIDATION.value] += 1

        # Validate history entries format
        for i, entry in enumerate(context.history):
            required_keys = ['timestamp', 'action']
            for key in required_keys:
                if key not in entry:
                    result.add_error(
                        f"History entry {i} missing required key: {key}",
                        field=f"history[{i}]",
                        rule=ValidationRule.FORMAT_VALIDATION
                    )

            # Validate timestamp format
            if 'timestamp' in entry:
                try:
                    datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                except ValueError:
                    result.add_error(
                        f"History entry {i} has invalid timestamp format",
                        field=f"history[{i}].timestamp",
                        rule=ValidationRule.FORMAT_VALIDATION
                    )

    def _validate_integrity(self, context: MCPContext, result: ValidationResult) -> None:
        """Validate context integrity using checksum"""
        self.validation_stats[ValidationRule.INTEGRITY_CHECK.value] += 1

        if not context.validate_integrity():
            result.add_error(
                "Context integrity check failed - checksum mismatch",
                rule=ValidationRule.INTEGRITY_CHECK,
                severity=ValidationSeverity.CRITICAL
            )

    def _validate_security(self, context: MCPContext, result: ValidationResult) -> None:
        """Validate security constraints"""
        self.validation_stats[ValidationRule.SECURITY_CHECK.value] += 1

        # Check for potentially dangerous content in metadata
        dangerous_patterns = [
            r'<script',  # XSS attempts
            r'javascript:',  # JavaScript injection
            r'data:',  # Data URL injection
            r'vbscript:',  # VBScript injection
        ]

        metadata_str = json.dumps(context.metadata, default=str)
        for pattern in dangerous_patterns:
            if re.search(pattern, metadata_str, re.IGNORECASE):
                result.add_error(
                    f"Potentially dangerous content detected in metadata: {pattern}",
                    field="metadata",
                    rule=ValidationRule.SECURITY_CHECK,
                    severity=ValidationSeverity.CRITICAL
                )

        # Check for overly long strings that might indicate buffer overflow attempts
        max_string_length = 10000
        string_fields = ['user', 'task', 'intent', 'subtask']

        for field in string_fields:
            value = getattr(context, field)
            if isinstance(value, str) and len(value) > max_string_length:
                result.add_warning(
                    f"Field '{field}' is unusually long ({len(value)} characters)",
                    field=field,
                    rule=ValidationRule.SECURITY_CHECK
                )

    def _validate_compliance(self, context: MCPContext, result: ValidationResult) -> None:
        """Validate compliance with business rules"""
        self.validation_stats[ValidationRule.COMPLIANCE_CHECK.value] += 1

        # Check for required compliance metadata
        compliance_fields = ['data_retention', 'privacy_level', 'audit_required']

        for field in compliance_fields:
            if field not in context.metadata:
                result.add_warning(
                    f"Missing compliance metadata: {field}",
                    field=f"metadata.{field}",
                    rule=ValidationRule.COMPLIANCE_CHECK
                )

        # Validate context age (shouldn't be too old without updates)
        max_age_days = 30
        context_age = datetime.utcnow() - context.created_at

        if context_age > timedelta(days=max_age_days) and context.status == ContextStatus.ACTIVE:
            result.add_warning(
                f"Context is {context_age.days} days old and still active",
                field="status",
                rule=ValidationRule.COMPLIANCE_CHECK,
                details={"age_days": context_age.days, "max_age_days": max_age_days}
            )

    def _update_validation_stats(self, result: ValidationResult) -> None:
        """Update validation statistics based on result"""
        # This is already handled in individual validation methods
        pass


# Global validator instance
_validator = None


def get_validator() -> MCPValidator:
    """Get the global MCP validator instance"""
    global _validator
    if _validator is None:
        _validator = MCPValidator()
    return _validator


def validate_context(context: Union[MCPContext, Dict[str, Any]]) -> ValidationResult:
    """Convenience function to validate a context"""
    return get_validator().validate_context(context)


def validate_context_quick(context: Union[MCPContext, Dict[str, Any]]) -> bool:
    """Convenience function for quick validation check"""
    return get_validator().validate_context_quick(context)
