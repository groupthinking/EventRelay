#!/usr/bin/env python3
"""
API Cost Monitoring and Management Service
==========================================

Real-time API cost tracking, quota management, and optimization for UVAI platform.
Monitors OpenAI, Anthropic, Gemini, YouTube Data API, and other service usage.
"""

import asyncio
import contextvars
import json
import logging
import os
import random
import re
import threading
import time
from collections import defaultdict, deque
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date as calendar_date
from datetime import datetime, timedelta, timezone
from datetime import time as clock_time
from pathlib import Path
from typing import Any, Optional, Union

import aiohttp
from sqlalchemy import (
    case,
    create_engine,
    delete,
    func,
    inspect,
    or_,
    text,
)
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from youtube_extension.backend.config.database import Base
from youtube_extension.backend.models.api_cost import (
    APIUsage,
    DailyBudget,
    WebhookOutbox,
)

# Compatibility path used only by explicit local callers and the module self-test.
_DEFAULT_DB_PATH_ENV = os.getenv("API_COST_MONITOR_DB_PATH")
DEFAULT_DB_PATH = (
    _DEFAULT_DB_PATH_ENV
    if _DEFAULT_DB_PATH_ENV
    else str(
        (Path(os.getenv("RUNTIME_DIR", "/tmp")) / "api_cost_monitoring.db").resolve()
    )
)

# Configure logging
logger = logging.getLogger(__name__)

# Keep the public webhook helper's one-argument signature for existing callers and
# tests while attaching an outbox event identifier to each delivery attempt.
_WEBHOOK_EVENT_ID: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "api_cost_webhook_event_id", default=None
)
_PRODUCTION_NAMES = {"staging", "prod", "production"}
_RUNTIME_ROLE_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")
_REQUIRED_API_COST_COLUMNS = {
    "api_usage": {
        "id",
        "service",
        "endpoint",
        "tokens_used",
        "cost",
        "timestamp",
        "request_type",
        "user_id",
        "video_id",
        "success",
        "error_message",
    },
    "daily_budgets": {
        "date",
        "total_cost",
        "alert_sent",
        "budget_exceeded",
    },
    "webhook_outbox": {
        "id",
        "utc_date",
        "alert_type",
        "status",
        "retry_count",
        "last_attempt",
        "next_attempt_at",
        "claimed_at",
        "claim_token",
        "last_recovered_at",
        "sent_at",
        "error_message",
        "current_cost",
        "payload",
    },
}
_POSTGRES_SCHEMA_CONTRACT_SQL = """
    WITH column_metadata AS (
        SELECT
            schema_record.nspname AS schema_name,
            table_record.relname AS table_name,
            attribute.attname AS column_name,
            format_type(attribute.atttypid, attribute.atttypmod) AS column_type,
            attribute.attnotnull AS is_not_null,
            pg_get_expr(
                default_record.adbin, default_record.adrelid, false
            ) AS default_expression,
            pg_get_serial_sequence(
                format(
                    '%I.%I', schema_record.nspname, table_record.relname
                ),
                attribute.attname
            ) AS serial_sequence
        FROM pg_attribute AS attribute
        JOIN pg_class AS table_record
          ON table_record.oid = attribute.attrelid
        JOIN pg_namespace AS schema_record
          ON schema_record.oid = table_record.relnamespace
        LEFT JOIN pg_attrdef AS default_record
          ON default_record.adrelid = attribute.attrelid
         AND default_record.adnum = attribute.attnum
        WHERE schema_record.nspname = 'public'
          AND table_record.relname IN (
              'api_usage', 'daily_budgets', 'webhook_outbox'
          )
          AND table_record.relkind IN ('r', 'p')
          AND attribute.attnum > 0
          AND NOT attribute.attisdropped
    ),
    expected_columns (
        table_name, column_name, column_type, is_not_null, default_kind
    ) AS (
        VALUES
            ('api_usage', 'id', 'integer', true, 'serial'),
            ('api_usage', 'service', 'character varying(100)', true, 'none'),
            ('api_usage', 'endpoint', 'character varying(255)', true, 'none'),
            ('api_usage', 'tokens_used', 'integer', true, 'zero'),
            ('api_usage', 'cost', 'double precision', true, 'none'),
            (
                'api_usage', 'timestamp', 'timestamp with time zone', true,
                'current_timestamp'
            ),
            (
                'api_usage', 'request_type', 'character varying(100)', false,
                'none'
            ),
            (
                'api_usage', 'user_id', 'character varying(255)', false,
                'none'
            ),
            (
                'api_usage', 'video_id', 'character varying(255)', false,
                'none'
            ),
            ('api_usage', 'success', 'boolean', true, 'true'),
            ('api_usage', 'error_message', 'text', false, 'none'),
            (
                'daily_budgets', 'date', 'character varying(10)', true,
                'none'
            ),
            ('daily_budgets', 'total_cost', 'double precision', true, 'zero'),
            ('daily_budgets', 'alert_sent', 'boolean', true, 'false'),
            ('daily_budgets', 'budget_exceeded', 'boolean', true, 'false'),
            ('webhook_outbox', 'id', 'integer', true, 'serial'),
            (
                'webhook_outbox', 'utc_date', 'character varying(10)', true,
                'none'
            ),
            (
                'webhook_outbox', 'alert_type', 'character varying(64)', true,
                'none'
            ),
            (
                'webhook_outbox', 'status', 'character varying(16)', true,
                'pending'
            ),
            ('webhook_outbox', 'retry_count', 'integer', true, 'zero'),
            (
                'webhook_outbox', 'last_attempt', 'timestamp with time zone',
                false, 'none'
            ),
            (
                'webhook_outbox', 'next_attempt_at', 'timestamp with time zone',
                false, 'none'
            ),
            (
                'webhook_outbox', 'claimed_at', 'timestamp with time zone',
                false, 'none'
            ),
            (
                'webhook_outbox', 'claim_token', 'character varying(64)', false,
                'none'
            ),
            (
                'webhook_outbox', 'last_recovered_at',
                'timestamp with time zone', false, 'none'
            ),
            (
                'webhook_outbox', 'sent_at', 'timestamp with time zone', false,
                'none'
            ),
            ('webhook_outbox', 'error_message', 'text', false, 'none'),
            (
                'webhook_outbox', 'current_cost', 'double precision', true,
                'none'
            ),
            ('webhook_outbox', 'payload', 'text', false, 'none')
    ),
    constraint_columns AS (
        SELECT
            schema_record.nspname AS schema_name,
            table_record.relname AS table_name,
            constraint_record.conname AS constraint_name,
            constraint_record.contype AS constraint_type,
            constraint_record.convalidated AS constraint_validated,
            regexp_replace(
                regexp_replace(
                    lower(pg_get_constraintdef(constraint_record.oid, false)),
                    '[[:space:]()]', '', 'g'
                ),
                '::(charactervarying|text|integer|doubleprecision)(\\[\\])?',
                '', 'g'
            ) AS normalized_definition,
            ARRAY(
                SELECT attribute.attname::text
                FROM unnest(constraint_record.conkey) WITH ORDINALITY
                    AS column_key(attnum, ordinality)
                JOIN pg_attribute AS attribute
                  ON attribute.attrelid = constraint_record.conrelid
                 AND attribute.attnum = column_key.attnum
                ORDER BY column_key.ordinality
            ) AS column_names
        FROM pg_constraint AS constraint_record
        JOIN pg_class AS table_record
          ON table_record.oid = constraint_record.conrelid
        JOIN pg_namespace AS schema_record
          ON schema_record.oid = table_record.relnamespace
        WHERE schema_record.nspname = 'public'
    ),
    index_columns AS (
        SELECT
            schema_record.nspname AS schema_name,
            table_record.relname AS table_name,
            index_record.relname AS index_name,
            index_metadata.indisunique AS is_unique,
            index_metadata.indisvalid AS is_valid,
            index_metadata.indisready AS is_ready,
            index_metadata.indpred IS NULL AS is_not_partial,
            index_metadata.indexprs IS NULL AS has_no_expressions,
            index_metadata.indnkeyatts AS key_count,
            index_metadata.indnatts AS total_column_count,
            ARRAY(
                SELECT attribute.attname::text
                FROM unnest(index_metadata.indkey) WITH ORDINALITY
                    AS column_key(attnum, ordinality)
                JOIN pg_attribute AS attribute
                  ON attribute.attrelid = index_metadata.indrelid
                 AND attribute.attnum = column_key.attnum
                ORDER BY column_key.ordinality
            ) AS column_names
        FROM pg_index AS index_metadata
        JOIN pg_class AS table_record
          ON table_record.oid = index_metadata.indrelid
        JOIN pg_class AS index_record
          ON index_record.oid = index_metadata.indexrelid
        JOIN pg_namespace AS schema_record
          ON schema_record.oid = table_record.relnamespace
        WHERE schema_record.nspname = 'public'
    )
    SELECT
        (
            SELECT
                count(*) = 29
                AND COALESCE(
                    bool_and(
                        COALESCE(
                            actual.column_type = expected.column_type
                            AND actual.is_not_null = expected.is_not_null
                            AND CASE expected.default_kind
                                WHEN 'none' THEN
                                    actual.default_expression IS NULL
                                WHEN 'serial' THEN
                                    actual.serial_sequence = format(
                                        'public.%s_%s_seq',
                                        expected.table_name,
                                        expected.column_name
                                    )
                                    AND regexp_replace(
                                        lower(actual.default_expression),
                                        '[[:space:]]', '', 'g'
                                    ) IN (
                                        format(
                                            'nextval(''%s_%s_seq''::regclass)',
                                            expected.table_name,
                                            expected.column_name
                                        ),
                                        format(
                                            'nextval(''public.%s_%s_seq''::regclass)',
                                            expected.table_name,
                                            expected.column_name
                                        )
                                    )
                                WHEN 'zero' THEN
                                    regexp_replace(
                                        lower(actual.default_expression),
                                        '[[:space:]]', '', 'g'
                                    ) ~ '^[()]?0([.]0*)?[()]?(::(integer|doubleprecision))?$'
                                WHEN 'current_timestamp' THEN
                                    regexp_replace(
                                        lower(actual.default_expression),
                                        '[[:space:]]', '', 'g'
                                    ) ~ '^current_timestamp(\\([0-9]+\\))?$'
                                WHEN 'true' THEN
                                    regexp_replace(
                                        lower(actual.default_expression),
                                        '[[:space:]]', '', 'g'
                                    ) ~ '^[()]?true[()]?(::boolean)?$'
                                WHEN 'false' THEN
                                    regexp_replace(
                                        lower(actual.default_expression),
                                        '[[:space:]]', '', 'g'
                                    ) ~ '^[()]?false[()]?(::boolean)?$'
                                WHEN 'pending' THEN
                                    regexp_replace(
                                        lower(actual.default_expression),
                                        '[[:space:]]', '', 'g'
                                    ) ~ '^[()]?''pending''[()]?(::charactervarying)?$'
                                ELSE false
                            END,
                            false
                        )
                    ),
                    false
                )
            FROM expected_columns AS expected
            LEFT JOIN column_metadata AS actual
              ON actual.table_name = expected.table_name
             AND actual.column_name = expected.column_name
        )
        AND (SELECT count(*) = 29 FROM column_metadata)
        AS column_contract,
        EXISTS (
            SELECT 1 FROM constraint_columns
            WHERE table_name = 'api_usage'
              AND constraint_type = 'p'
              AND constraint_validated
              AND column_names = ARRAY['id']
        ) AS api_usage_primary_key,
        EXISTS (
            SELECT 1 FROM constraint_columns
            WHERE table_name = 'daily_budgets'
              AND constraint_type = 'p'
              AND constraint_validated
              AND column_names = ARRAY['date']
        ) AS daily_budgets_primary_key,
        EXISTS (
            SELECT 1 FROM constraint_columns
            WHERE table_name = 'webhook_outbox'
              AND constraint_type = 'p'
              AND constraint_validated
              AND column_names = ARRAY['id']
        ) AS webhook_outbox_primary_key,
        EXISTS (
            SELECT 1 FROM constraint_columns
            WHERE table_name = 'webhook_outbox'
              AND constraint_name = 'uq_utc_date_alert_type'
              AND constraint_type = 'u'
              AND constraint_validated
              AND column_names = ARRAY['utc_date', 'alert_type']
        ) AS outbox_alert_uniqueness,
        (
            SELECT count(*) = 6
            FROM constraint_columns
            WHERE constraint_type = 'c'
              AND constraint_validated
              AND (
                  (
                      table_name = 'api_usage'
                      AND constraint_name =
                          'ck_api_usage_tokens_used_nonnegative'
                      AND normalized_definition = 'checktokens_used>=0'
                  )
                  OR (
                      table_name = 'api_usage'
                      AND constraint_name = 'ck_api_usage_cost_nonnegative'
                      AND normalized_definition = 'checkcost>=0'
                  )
                  OR (
                      table_name = 'daily_budgets'
                      AND constraint_name =
                          'ck_daily_budgets_total_cost_nonnegative'
                      AND normalized_definition = 'checktotal_cost>=0'
                  )
                  OR (
                      table_name = 'webhook_outbox'
                      AND constraint_name = 'ck_webhook_outbox_status'
                      AND normalized_definition IN (
                          'checkstatus=anyarray[''pending'',''processing'',''sent'',''failed'']',
                          'checkstatusin''pending'',''processing'',''sent'',''failed'''
                      )
                  )
                  OR (
                      table_name = 'webhook_outbox'
                      AND constraint_name =
                          'ck_webhook_outbox_retry_count_nonnegative'
                      AND normalized_definition = 'checkretry_count>=0'
                  )
                  OR (
                      table_name = 'webhook_outbox'
                      AND constraint_name =
                          'ck_webhook_outbox_current_cost_nonnegative'
                      AND normalized_definition = 'checkcurrent_cost>=0'
                  )
              )
        ) AS check_definitions,
        EXISTS (
            SELECT 1 FROM index_columns
            WHERE table_name = 'webhook_outbox'
              AND index_name = 'ix_webhook_outbox_due'
              AND NOT is_unique
              AND is_valid
              AND is_ready
              AND is_not_partial
              AND has_no_expressions
              AND key_count = 4
              AND total_column_count = 4
              AND column_names = ARRAY[
                  'status', 'next_attempt_at', 'retry_count', 'id'
              ]
        ) AS outbox_due_index,
        EXISTS (
            SELECT 1 FROM index_columns
            WHERE table_name = 'webhook_outbox'
              AND index_name = 'ix_webhook_outbox_stale_claims'
              AND NOT is_unique
              AND is_valid
              AND is_ready
              AND is_not_partial
              AND has_no_expressions
              AND key_count = 3
              AND total_column_count = 3
              AND column_names = ARRAY['status', 'claimed_at', 'id']
        ) AS outbox_stale_claims_index
"""


def is_production_environment() -> bool:
    """Return whether a deployment marker requires production-grade safety."""

    return (
        os.getenv("ENVIRONMENT", "").strip().lower() in _PRODUCTION_NAMES
        or os.getenv("VERCEL_ENV", "").strip().lower() == "production"
    )


def _environment_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized not in {"true", "false"}:
        raise RuntimeError(f"{name} must be exactly true or false")
    return normalized == "true"


def _normalize_database_url(raw_url: str) -> URL:
    """Normalize PostgreSQL URLs onto the supported synchronous Psycopg driver."""

    try:
        url = make_url(raw_url)
    except Exception as exc:
        raise RuntimeError("API-cost DATABASE_URL is invalid") from exc

    backend = url.get_backend_name()
    if backend == "postgresql" or url.drivername == "postgres":
        return url.set(drivername="postgresql+psycopg")
    if backend == "sqlite":
        return url
    raise RuntimeError("API-cost database must use PostgreSQL or explicit local SQLite")


def validate_cloud_sql_database_url(
    database_url: Union[URL, str], instance: str
) -> None:
    """Require a production URL to use the Cloud SQL socket mounted by Cloud Run."""

    url = (
        database_url
        if isinstance(database_url, URL)
        else _normalize_database_url(database_url)
    )
    expected_host = f"/cloudsql/{instance}"
    if (
        url.get_backend_name() != "postgresql"
        or url.host not in {None, ""}
        or url.query.get("host") != expected_host
    ):
        raise RuntimeError(
            "Deployed API-cost DATABASE_URL must use the attached Cloud SQL Unix "
            f"socket (host={expected_host})"
        )


@dataclass
class APIUsageRecord:
    """Individual API usage record with cost tracking"""

    service: str
    endpoint: str
    tokens_used: int
    cost: float
    timestamp: datetime
    request_type: str
    user_id: Optional[str] = None
    video_id: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class RateLimitTracker:
    """Rate limiting tracker for API calls"""

    max_requests: int
    window_seconds: int
    requests: deque = None

    def __post_init__(self):
        if self.requests is None:
            self.requests = deque()


class APICostMonitor:
    """
    Comprehensive API cost monitoring and management service

    Features:
    - Real-time cost tracking for all API services
    - Rate limiting with intelligent backoff
    - Quota management and budget alerts
    - Cost optimization through caching
    - Circuit breaker pattern for failed APIs
    - Detailed usage analytics and reporting
    """

    # API Cost Models (per 1K tokens/requests)
    COST_MODELS = {
        "openai": {
            "gpt-4o": {"input": 0.0025, "output": 0.01},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            "text-embedding-3-small": {"input": 0.00002, "output": 0},
            "text-embedding-3-large": {"input": 0.00013, "output": 0},
        },
        "anthropic": {
            # Current models (per-1K USD)
            "claude-opus-4-8": {"input": 0.005, "output": 0.025},
            "claude-opus-4-7": {"input": 0.005, "output": 0.025},
            "claude-sonnet-4-6": {"input": 0.003, "output": 0.015},
            "claude-haiku-4-5": {"input": 0.001, "output": 0.005},
            # Historical (retired) — retained for costing past usage logs
            "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
            "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
            "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
        },
        "google": {
            "gemini-3-pro": {"input": 0.000875, "output": 0.0035},
            "gemini-3-flash": {"input": 0.000052, "output": 0.00021},
            "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
            "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
        },
        "youtube": {
            "search": 100,  # quota units per request
            "videos": 1,  # quota units per request
            "channels": 1,  # quota units per request
            "captions": 200,  # quota units per request
        },
    }

    def __init__(
        self,
        db_path: Optional[str] = None,
        *,
        database_url: Optional[str] = None,
        initialize_schema: Optional[bool] = None,
    ):
        """Initialize the monitor without performing PostgreSQL DDL.

        ``db_path`` remains as a backwards-compatible, explicit local SQLite
        opt-in. Production persistence must be configured with PostgreSQL via
        ``API_COST_DATABASE_URL`` or ``DATABASE_URL`` and migrated separately.
        """
        self.is_production = is_production_environment()
        self.daily_budget = float(os.getenv("API_DAILY_BUDGET", "10.00"))
        self.alert_threshold = float(os.getenv("API_ALERT_THRESHOLD", "8.00"))
        self.cost_tracking_enabled = _environment_bool("API_COST_TRACKING", True)
        self.delivery_enabled = _environment_bool(
            "API_COST_DELIVERY_ENABLED", not self.is_production
        )
        self.runtime_db_role = os.getenv("API_COST_RUNTIME_DB_ROLE", "").strip() or None

        # Webhook notification settings
        self.webhook_url = os.getenv("API_COST_WEBHOOK_URL")
        self.webhook_max_attempts = 5
        self.webhook_retry_base_seconds = max(
            0.0, float(os.getenv("API_COST_WEBHOOK_RETRY_BASE_SECONDS", "5"))
        )
        self.webhook_retry_max_seconds = max(
            self.webhook_retry_base_seconds,
            float(os.getenv("API_COST_WEBHOOK_RETRY_MAX_SECONDS", "300")),
        )
        self.webhook_poll_interval_seconds = max(
            0.01, float(os.getenv("API_COST_WEBHOOK_POLL_SECONDS", "1"))
        )
        self.webhook_stale_timeout_seconds = max(
            1, int(os.getenv("API_COST_WEBHOOK_STALE_SECONDS", "30"))
        )
        self._worker_task: Optional[asyncio.Task[None]] = None
        self._worker_wake_event: Optional[asyncio.Event] = None

        # Rate limiters for different services
        self.rate_limiters = {
            "openai": RateLimitTracker(int(os.getenv("OPENAI_RATE_LIMIT", "50")), 60),
            "anthropic": RateLimitTracker(
                int(os.getenv("ANTHROPIC_RATE_LIMIT", "30")), 60
            ),
            "google": RateLimitTracker(int(os.getenv("GEMINI_RATE_LIMIT", "60")), 60),
            "youtube": RateLimitTracker(
                int(os.getenv("YOUTUBE_QUOTA_LIMIT", "10000")), 86400
            ),  # Daily quota
        }

        # Circuit breakers
        self.circuit_breakers = defaultdict(
            lambda: {"failures": 0, "last_failure": None, "open": False}
        )
        self.max_failures = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5"))

        # Current session tracking
        self.session_costs = defaultdict(float)
        self.session_requests = defaultdict(int)

        # Lock for thread safety
        self._lock = threading.Lock()

        configured_url = (
            database_url
            or os.getenv("API_COST_DATABASE_URL")
            or os.getenv("DATABASE_URL")
        )
        configured_path = db_path or os.getenv("API_COST_MONITOR_DB_PATH")

        if configured_url:
            self.database_url: Optional[URL] = _normalize_database_url(configured_url)
        elif configured_path:
            if configured_path in {":memory:", ":memory"}:
                self.database_url = make_url("sqlite://")
            else:
                resolved_path = str(Path(configured_path).expanduser().resolve())
                self.database_url = URL.create("sqlite", database=resolved_path)
        else:
            self.database_url = None

        persistence_required = self.cost_tracking_enabled or self.delivery_enabled
        cloud_sql_instance = os.getenv("CLOUD_SQL_INSTANCE_CONNECTION_NAME", "").strip()
        if self.is_production and self.database_url is not None:
            if self.database_url.get_backend_name() != "postgresql":
                raise RuntimeError(
                    "PostgreSQL DATABASE_URL is required for API-cost tracking "
                    "or delivery in production"
                )
        if self.is_production and persistence_required and self.database_url is None:
            raise RuntimeError(
                "PostgreSQL DATABASE_URL is required for API-cost tracking "
                "or delivery in production"
            )
        if self.is_production and persistence_required and not self.runtime_db_role:
            raise RuntimeError(
                "API_COST_RUNTIME_DB_ROLE is required for API-cost tracking "
                "or delivery in production"
            )
        if self.is_production and persistence_required and not cloud_sql_instance:
            raise RuntimeError(
                "CLOUD_SQL_INSTANCE_CONNECTION_NAME is required for API-cost "
                "tracking or delivery in production"
            )
        if self.is_production and self.database_url is not None and cloud_sql_instance:
            validate_cloud_sql_database_url(self.database_url, cloud_sql_instance)

        self.engine = None
        self.Session = None
        self.db_path: Optional[str] = None
        self._is_postgres = False
        if self.database_url is not None:
            self._is_postgres = self.database_url.get_backend_name() == "postgresql"
            self.db_path = (
                self.database_url.database
                if not self._is_postgres
                else self.database_url.render_as_string(hide_password=True)
            )
            if not self._is_postgres and self.db_path is None:
                self.db_path = ":memory:"
            self.engine = self._create_database_engine(self.database_url)
            self.Session = sessionmaker(
                bind=self.engine, expire_on_commit=False, future=True
            )

            should_initialize = (
                initialize_schema
                if initialize_schema is not None
                else not self._is_postgres
            )
            if should_initialize and self._is_postgres:
                raise RuntimeError(
                    "Runtime PostgreSQL schema creation is forbidden; run Alembic first"
                )
            if should_initialize:
                self._init_database()

        logger.info(
            "API Cost Monitor initialized - budget=%s alert=%s persistence=%s",
            self.daily_budget,
            self.alert_threshold,
            "postgresql" if self._is_postgres else "local" if self.engine else "off",
        )

    @staticmethod
    def _create_database_engine(database_url: URL):
        if database_url.get_backend_name() == "sqlite":
            kwargs: dict[str, Any] = {
                "connect_args": {"timeout": 30, "check_same_thread": False},
                "future": True,
            }
            if not database_url.database:
                kwargs["poolclass"] = StaticPool
            return create_engine(database_url, **kwargs)
        pool_size = max(1, int(os.getenv("API_COST_DB_POOL_SIZE", "2")))
        max_overflow = max(0, int(os.getenv("API_COST_DB_MAX_OVERFLOW", "0")))
        pool_timeout = max(1, int(os.getenv("API_COST_DB_POOL_TIMEOUT", "10")))
        connect_timeout = max(1, int(os.getenv("API_COST_DB_CONNECT_TIMEOUT", "5")))
        statement_timeout = max(
            100, int(os.getenv("API_COST_DB_STATEMENT_TIMEOUT_MS", "5000"))
        )
        lock_timeout = max(100, int(os.getenv("API_COST_DB_LOCK_TIMEOUT_MS", "2000")))
        return create_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_pre_ping=True,
            pool_recycle=max(60, int(os.getenv("API_COST_DB_POOL_RECYCLE", "1800"))),
            connect_args={
                "connect_timeout": connect_timeout,
                "application_name": "eventrelay-api-cost",
                "options": (
                    f"-c statement_timeout={statement_timeout} "
                    f"-c lock_timeout={lock_timeout} -c timezone=UTC "
                    "-c search_path=public"
                ),
            },
            future=True,
        )

    def _init_database(self) -> None:
        """Create and validate an explicitly selected local SQLite schema."""
        if self.engine is None or self._is_postgres:
            return
        if self.db_path:
            db_parent = Path(self.db_path).expanduser().resolve().parent
            db_parent.mkdir(parents=True, exist_ok=True)
        Base.metadata.create_all(
            self.engine,
            tables=[APIUsage.__table__, DailyBudget.__table__, WebhookOutbox.__table__],
        )
        self._upgrade_sqlite_outbox_schema()
        self._validate_database_schema()

    def _upgrade_sqlite_outbox_schema(self) -> None:
        """Add compatible SQLite outbox columns and indexes without data loss."""
        if self.engine is None or self.engine.dialect.name != "sqlite":
            return

        with self.engine.connect() as connection:
            connection.exec_driver_sql("BEGIN EXCLUSIVE")
            try:
                columns = {
                    row[1]
                    for row in connection.exec_driver_sql(
                        "PRAGMA table_info(webhook_outbox)"
                    )
                }
                if not columns:
                    connection.commit()
                    return

                unique_indexes = [
                    row[1]
                    for row in connection.exec_driver_sql(
                        "PRAGMA index_list(webhook_outbox)"
                    )
                    if row[2]
                ]
                unique_index_columns = []
                for index_name in unique_indexes:
                    unique_index_columns.append(
                        [
                            row[2]
                            for row in connection.exec_driver_sql(
                                f"PRAGMA index_info({index_name!r})"
                            )
                        ]
                    )
                if ["utc_date", "alert_type"] not in unique_index_columns:
                    raise RuntimeError(
                        "Legacy API-cost SQLite schema is incompatible; "
                        "back up and recreate the local database"
                    )

                for column_name, column_type in (
                    ("next_attempt_at", "DATETIME"),
                    ("claimed_at", "DATETIME"),
                    ("claim_token", "VARCHAR(64)"),
                    ("last_recovered_at", "DATETIME"),
                    ("sent_at", "DATETIME"),
                ):
                    if column_name not in columns:
                        connection.exec_driver_sql(
                            "ALTER TABLE webhook_outbox "
                            f"ADD COLUMN {column_name} {column_type}"
                        )

                index_columns = [
                    row[2]
                    for row in connection.exec_driver_sql(
                        "PRAGMA index_info(ix_webhook_outbox_due)"
                    )
                ]
                expected_due_index_columns = [
                    "status",
                    "next_attempt_at",
                    "retry_count",
                ]
                if index_columns and index_columns != expected_due_index_columns:
                    connection.exec_driver_sql(
                        "DROP INDEX IF EXISTS ix_webhook_outbox_due"
                    )
                connection.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS ix_webhook_outbox_due "
                    "ON webhook_outbox (status, next_attempt_at, retry_count)"
                )
                connection.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS ix_webhook_outbox_stale_claims "
                    "ON webhook_outbox (status, claimed_at, id)"
                )
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    def _validate_database_schema(self) -> None:
        if self.engine is None:
            raise RuntimeError("API-cost persistence is not configured")
        if self._is_postgres:
            required_selects = (
                "SELECT id, service, endpoint, tokens_used, cost, timestamp, "
                "request_type, user_id, video_id, success, error_message "
                "FROM public.api_usage LIMIT 0",
                "SELECT date, total_cost, alert_sent, budget_exceeded "
                "FROM public.daily_budgets LIMIT 0",
                "SELECT id, utc_date, alert_type, status, retry_count, last_attempt, "
                "next_attempt_at, claimed_at, claim_token, last_recovered_at, sent_at, "
                "error_message, current_cost, payload "
                "FROM public.webhook_outbox LIMIT 0",
            )
            with self.engine.connect() as connection:
                for statement in required_selects:
                    connection.execute(text(statement))
                schema_checks = (
                    connection.execute(text(_POSTGRES_SCHEMA_CONTRACT_SQL))
                    .mappings()
                    .one()
                )
            failed_checks = sorted(
                name for name, passed in schema_checks.items() if not passed
            )
            if failed_checks:
                raise RuntimeError(
                    "API-cost PostgreSQL schema contract failed: "
                    + ", ".join(failed_checks)
                )
            return
        inspector = inspect(self.engine)
        for table_name, required_columns in _REQUIRED_API_COST_COLUMNS.items():
            if not inspector.has_table(table_name):
                raise RuntimeError(f"API-cost database is missing table {table_name}")
            actual_columns = {
                column["name"] for column in inspector.get_columns(table_name)
            }
            missing = required_columns - actual_columns
            if missing:
                if not self._is_postgres:
                    raise RuntimeError(
                        "Legacy API-cost SQLite schema is incompatible; "
                        "back up and recreate the local database"
                    )
                raise RuntimeError(
                    f"API-cost database table {table_name} is missing columns: "
                    f"{', '.join(sorted(missing))}"
                )

    @contextmanager
    def _session_scope(self, *, commit: bool = False) -> Iterator[Session]:
        if self.Session is None:
            raise RuntimeError("API-cost persistence is not configured")
        with self.Session() as session:
            try:
                yield session
                if commit:
                    session.commit()
            except Exception:
                session.rollback()
                raise

    def ensure_database_ready(self) -> None:
        """Validate the runtime schema and effective DML privileges.

        Migration-head ownership belongs to the deployment job. Runtime
        credentials intentionally do not need access to Alembic's version table.
        """
        if self._is_postgres:
            if not self.runtime_db_role:
                raise RuntimeError(
                    "API_COST_RUNTIME_DB_ROLE is required for PostgreSQL readiness"
                )
            if not _RUNTIME_ROLE_PATTERN.fullmatch(self.runtime_db_role):
                raise RuntimeError(
                    "API_COST_RUNTIME_DB_ROLE must be a plain PostgreSQL role "
                    "identifier"
                )
        self._validate_database_schema()
        if not self._is_postgres:
            return
        assert self.engine is not None
        privilege_sql = text("""
            SELECT
              pg_has_role(
                current_user, :runtime_role, 'MEMBER'
              ) AS expected_role_member,
              runtime_login.rolcanlogin AS login_role,
              runtime_login.rolinherit AS inherits_privileges,
              NOT (
                runtime_login.rolsuper
                OR runtime_login.rolcreatedb
                OR runtime_login.rolcreaterole
                OR runtime_login.rolreplication
                OR runtime_login.rolbypassrls
              ) AS non_elevated,
              NOT EXISTS (
                SELECT 1
                FROM pg_auth_members AS membership
                JOIN pg_roles AS parent_role
                  ON parent_role.oid = membership.roleid
                WHERE membership.member = runtime_login.oid
                  AND parent_role.rolname <> :runtime_role
              ) AS only_expected_parent_role,
              NOT runtime_group.rolcanlogin AS group_nologin,
              NOT (
                runtime_group.rolsuper
                OR runtime_group.rolcreatedb
                OR runtime_group.rolcreaterole
                OR runtime_group.rolreplication
                OR runtime_group.rolbypassrls
              ) AS group_non_elevated,
              NOT EXISTS (
                SELECT 1
                FROM pg_auth_members AS group_membership
                WHERE group_membership.member = runtime_group.oid
              ) AS group_no_parent_roles,
              has_schema_privilege(
                current_user, 'public', 'USAGE'
              ) AS schema_usage,
              NOT has_schema_privilege(
                current_user, 'public', 'CREATE'
              ) AS no_schema_create,
              NOT has_database_privilege(
                current_user, current_database(), 'CREATE'
              ) AS no_database_create,
              NOT EXISTS (
                SELECT 1
                FROM pg_database AS database
                WHERE database.datname = current_database()
                  AND pg_has_role(
                    current_user, database.datdba, 'MEMBER'
                  )
              ) AS no_database_ownership,
              NOT EXISTS (
                SELECT 1
                FROM pg_class AS relation
                JOIN pg_namespace AS namespace
                  ON namespace.oid = relation.relnamespace
                WHERE namespace.nspname = 'public'
                  AND relation.relname IN (
                    'api_usage', 'daily_budgets', 'webhook_outbox',
                    'api_usage_id_seq', 'webhook_outbox_id_seq'
                  )
                  AND pg_has_role(
                    current_user, relation.relowner, 'MEMBER'
                  )
              ) AS no_target_ownership,
              NOT EXISTS (
                SELECT 1
                FROM pg_namespace AS namespace
                WHERE namespace.nspname <> 'public'
                  AND namespace.nspname <> 'information_schema'
                  AND namespace.nspname !~ '^pg_'
                  AND (
                    has_schema_privilege(
                      current_user, namespace.oid, 'USAGE'
                    )
                    OR has_schema_privilege(
                      current_user, namespace.oid, 'CREATE'
                    )
                  )
              ) AS no_unexpected_schema_access,
              NOT EXISTS (
                SELECT 1
                FROM pg_class AS relation
                JOIN pg_namespace AS namespace
                  ON namespace.oid = relation.relnamespace
                CROSS JOIN (
                  VALUES
                    ('SELECT'), ('INSERT'), ('UPDATE'), ('DELETE'),
                    ('TRUNCATE'), ('REFERENCES'), ('TRIGGER')
                ) AS candidate(privilege_name)
                WHERE relation.relkind IN ('r', 'p', 'v', 'm', 'f')
                  AND namespace.nspname <> 'information_schema'
                  AND namespace.nspname !~ '^pg_'
                  AND NOT (
                    namespace.nspname = 'public'
                    AND relation.relname IN (
                      'api_usage', 'daily_budgets', 'webhook_outbox'
                    )
                    AND candidate.privilege_name IN (
                      'SELECT', 'INSERT', 'UPDATE', 'DELETE'
                    )
                  )
                  AND has_table_privilege(
                    current_user, relation.oid, candidate.privilege_name
                  )
              ) AS no_unexpected_table_access,
              NOT EXISTS (
                SELECT 1
                FROM pg_class AS relation
                JOIN pg_namespace AS namespace
                  ON namespace.oid = relation.relnamespace
                CROSS JOIN (
                  VALUES ('USAGE'), ('SELECT'), ('UPDATE')
                ) AS candidate(privilege_name)
                WHERE relation.relkind = 'S'
                  AND namespace.nspname <> 'information_schema'
                  AND namespace.nspname !~ '^pg_'
                  AND NOT (
                    namespace.nspname = 'public'
                    AND relation.relname IN (
                      'api_usage_id_seq', 'webhook_outbox_id_seq'
                    )
                    AND candidate.privilege_name IN ('USAGE', 'SELECT')
                  )
                  AND has_sequence_privilege(
                    current_user, relation.oid, candidate.privilege_name
                  )
              ) AS no_unexpected_sequence_access,
              (
                SELECT bool_and(
                  has_table_privilege(
                    current_user, required.relation_name,
                    required.privilege_name
                  )
                )
                FROM (VALUES
                  ('public.api_usage', 'SELECT'),
                  ('public.api_usage', 'INSERT'),
                  ('public.api_usage', 'UPDATE'),
                  ('public.api_usage', 'DELETE'),
                  ('public.daily_budgets', 'SELECT'),
                  ('public.daily_budgets', 'INSERT'),
                  ('public.daily_budgets', 'UPDATE'),
                  ('public.daily_budgets', 'DELETE'),
                  ('public.webhook_outbox', 'SELECT'),
                  ('public.webhook_outbox', 'INSERT'),
                  ('public.webhook_outbox', 'UPDATE'),
                  ('public.webhook_outbox', 'DELETE')
                ) AS required(relation_name, privilege_name)
              ) AS required_table_dml,
              NOT EXISTS (
                SELECT 1
                FROM (VALUES
                  ('public.api_usage', 'TRUNCATE'),
                  ('public.api_usage', 'REFERENCES'),
                  ('public.api_usage', 'TRIGGER'),
                  ('public.daily_budgets', 'TRUNCATE'),
                  ('public.daily_budgets', 'REFERENCES'),
                  ('public.daily_budgets', 'TRIGGER'),
                  ('public.webhook_outbox', 'TRUNCATE'),
                  ('public.webhook_outbox', 'REFERENCES'),
                  ('public.webhook_outbox', 'TRIGGER')
                ) AS unsafe(relation_name, privilege_name)
                WHERE has_table_privilege(
                  current_user, unsafe.relation_name,
                  unsafe.privilege_name
                )
              ) AS no_unsafe_table_privileges,
              (
                SELECT bool_and(
                  has_sequence_privilege(
                    current_user, required.sequence_name,
                    required.privilege_name
                  )
                )
                FROM (VALUES
                  ('public.api_usage_id_seq', 'USAGE'),
                  ('public.api_usage_id_seq', 'SELECT'),
                  ('public.webhook_outbox_id_seq', 'USAGE'),
                  ('public.webhook_outbox_id_seq', 'SELECT')
                ) AS required(sequence_name, privilege_name)
              ) AS required_sequence_access,
              NOT EXISTS (
                SELECT 1
                FROM (VALUES
                  ('public.api_usage_id_seq', 'UPDATE'),
                  ('public.webhook_outbox_id_seq', 'UPDATE')
                ) AS unsafe(sequence_name, privilege_name)
                WHERE has_sequence_privilege(
                  current_user, unsafe.sequence_name,
                  unsafe.privilege_name
                )
              ) AS no_unsafe_sequence_privileges,
              NOT EXISTS (
                SELECT 1
                FROM (VALUES
                  ('SELECT'), ('INSERT'), ('UPDATE'), ('DELETE'),
                  ('TRUNCATE'), ('REFERENCES'), ('TRIGGER')
                ) AS forbidden(privilege_name)
                WHERE has_table_privilege(
                  current_user, 'public.alembic_version',
                  forbidden.privilege_name
                )
              ) AS no_alembic_access
            FROM pg_roles AS runtime_login
            JOIN pg_roles AS runtime_group
              ON runtime_group.rolname = :runtime_role
            WHERE runtime_login.rolname = current_user
            """)
        with self.engine.connect() as connection:
            checks = dict(
                connection.execute(
                    privilege_sql,
                    {"runtime_role": self.runtime_db_role},
                )
                .mappings()
                .one()
            )
        failed_checks = [name for name, passed in checks.items() if passed is not True]
        if failed_checks:
            raise RuntimeError(
                "API-cost runtime database privileges are unsafe or incomplete: "
                + ", ".join(failed_checks)
            )

    def check_rate_limit(self, service: str) -> tuple[bool, int]:
        """
        Check if service is within rate limits

        Returns:
            (allowed: bool, wait_seconds: int)
        """
        if service not in self.rate_limiters:
            return True, 0

        with self._lock:
            limiter = self.rate_limiters[service]
            now = time.time()

            # Remove old requests outside the window
            while (
                limiter.requests and now - limiter.requests[0] > limiter.window_seconds
            ):
                limiter.requests.popleft()

            # Check if under limit
            if len(limiter.requests) < limiter.max_requests:
                limiter.requests.append(now)
                return True, 0

            # Calculate wait time
            oldest_request = limiter.requests[0]
            wait_seconds = int(limiter.window_seconds - (now - oldest_request)) + 1

            return False, wait_seconds

    def check_circuit_breaker(self, service: str) -> bool:
        """Check if circuit breaker is open for service"""
        breaker = self.circuit_breakers[service]

        if not breaker["open"]:
            return False

        # Check if we should try again (5 minute cooldown)
        if breaker["last_failure"] and time.time() - breaker["last_failure"] > 300:
            breaker["open"] = False
            breaker["failures"] = 0
            logger.info(f"🔄 Circuit breaker reset for {service}")
            return False

        return True

    def record_api_failure(self, service: str, error: str):
        """Record API failure for circuit breaker"""
        with self._lock:
            breaker = self.circuit_breakers[service]
            breaker["failures"] += 1
            breaker["last_failure"] = time.time()

            if breaker["failures"] >= self.max_failures:
                breaker["open"] = True
                logger.warning(
                    f"🚫 Circuit breaker opened for {service} after {breaker['failures']} failures"
                )

    def calculate_cost(
        self, service: str, model: str, input_tokens: int, output_tokens: int = 0
    ) -> float:
        """Calculate cost based on service, model, and token usage"""
        if service not in self.COST_MODELS:
            return 0.0

        service_costs = self.COST_MODELS[service]
        if model not in service_costs:
            # Use average cost for unknown models
            model = list(service_costs.keys())[0]

        if service == "youtube":
            # YouTube uses quota units, not token pricing
            return input_tokens * 0.0001  # Rough estimate per quota unit

        model_cost = service_costs[model]
        if isinstance(model_cost, dict):
            input_cost = (input_tokens / 1000) * model_cost["input"]
            output_cost = (output_tokens / 1000) * model_cost["output"]
            return input_cost + output_cost
        else:
            return (input_tokens / 1000) * model_cost

    async def record_usage(
        self,
        service: str,
        endpoint: str,
        tokens_used: int,
        model: str = None,
        output_tokens: int = 0,
        request_type: str = None,
        user_id: str = None,
        video_id: str = None,
        success: bool = True,
        error_message: str = None,
    ) -> APIUsageRecord:
        """Record API usage and calculate costs"""

        if not self.cost_tracking_enabled:
            return None

        # Calculate cost
        cost = self.calculate_cost(
            service, model or "default", tokens_used, output_tokens
        )

        # Create usage record
        record = APIUsageRecord(
            service=service,
            endpoint=endpoint,
            tokens_used=tokens_used,
            cost=cost,
            timestamp=datetime.now(timezone.utc),
            request_type=request_type,
            user_id=user_id,
            video_id=video_id,
            success=success,
            error_message=error_message,
        )

        # Update session tracking
        with self._lock:
            self.session_costs[service] += cost
            self.session_requests[service] += 1

        stored = False
        if self.Session is None:
            logger.warning(
                "API usage was not persisted because persistence is disabled"
            )
        else:
            try:
                await asyncio.to_thread(self._record_usage_sync, record)
                stored = True
            except Exception as exc:
                # The provider operation has already completed. Telemetry is
                # best effort and must never make that paid result retry/fail.
                logger.error("Failed to record API usage: %s", exc)

        if stored:
            await self._check_budget_alerts()

        logger.debug("API usage: %s - $%.4f (%s tokens)", service, cost, tokens_used)
        return record

    def _record_usage_sync(self, record: APIUsageRecord) -> None:
        """Persist one usage record on a worker thread."""
        with self._session_scope(commit=True) as session:
            session.add(
                APIUsage(
                    service=record.service,
                    endpoint=record.endpoint,
                    tokens_used=record.tokens_used,
                    cost=record.cost,
                    timestamp=record.timestamp,
                    request_type=record.request_type,
                    user_id=record.user_id,
                    video_id=record.video_id,
                    success=record.success,
                    error_message=record.error_message,
                )
            )

    async def _check_budget_alerts(self) -> None:
        """Check and enqueue budget alerts if thresholds are exceeded."""
        try:
            today = datetime.now(timezone.utc).date().isoformat()
            daily_cost = await self.get_daily_cost(today)

            threshold_claimed = (
                daily_cost >= self.alert_threshold
                and await asyncio.to_thread(
                    self._claim_alert, today, "threshold", daily_cost
                )
            )
            if threshold_claimed:
                await self._send_budget_alert(daily_cost, "threshold")

            exceeded_claimed = (
                daily_cost >= self.daily_budget
                and await asyncio.to_thread(
                    self._claim_alert, today, "exceeded", daily_cost
                )
            )
            if exceeded_claimed:
                await self._send_budget_alert(daily_cost, "exceeded")

        except Exception as exc:
            logger.error("Error checking budget alerts: %s", exc)

    def _claim_alert(
        self, date: str, alert_type: str, current_cost: float = 0.0
    ) -> bool:
        """Atomically claim today's alert of ``alert_type``.

        Returns True only for the caller that first inserts the outbox item
        or flips the day's flag from 0 to 1 in a context-managed SQLAlchemy session.
        Because the transaction commits atomically, concurrent processes racing
        cannot both win, ensuring each alert is dispatched at most once per UTC day.
        """
        try:
            with self._session_scope(commit=True) as session:
                existing = (
                    session.query(WebhookOutbox)
                    .filter_by(utc_date=date, alert_type=alert_type)
                    .first()
                )
                if existing:
                    return False

                budget = session.query(DailyBudget).filter_by(date=date).first()
                if not budget:
                    budget = DailyBudget(
                        date=date,
                        total_cost=current_cost,
                        alert_sent=False,
                        budget_exceeded=False,
                    )
                    session.add(budget)

                if alert_type == "threshold":
                    if budget.alert_sent:
                        return False
                    budget.alert_sent = True
                elif alert_type == "exceeded":
                    if budget.budget_exceeded:
                        return False
                    budget.budget_exceeded = True

                alert_msg = f"🚨 API Budget Alert: ${current_cost:.2f} "
                if alert_type == "threshold":
                    alert_msg += f"(Alert threshold: ${self.alert_threshold})"
                else:
                    alert_msg += f"EXCEEDED daily budget of ${self.daily_budget}"

                session.add(
                    WebhookOutbox(
                        utc_date=date,
                        alert_type=alert_type,
                        status="pending",
                        retry_count=0,
                        current_cost=current_cost,
                        payload=alert_msg,
                    )
                )
            return True
        except Exception as exc:
            logger.debug(
                "Failed to claim alert due to concurrency or database exception: %s",
                exc,
            )
            return False

    def _trigger_delivery(self):
        """Wake the explicitly managed worker without spawning per-alert tasks."""
        if self._worker_wake_event is not None:
            self._worker_wake_event.set()

    async def start(self) -> asyncio.Task[None]:
        """Start the monitor's single managed outbox worker."""
        if self._worker_task is not None and not self._worker_task.done():
            return self._worker_task

        self._worker_wake_event = asyncio.Event()
        self._worker_task = asyncio.create_task(
            self._outbox_worker(), name="api-cost-webhook-outbox"
        )
        return self._worker_task

    async def close(self) -> None:
        """Stop the managed worker and wait for any claim cleanup to finish."""
        task = self._worker_task
        if task is None:
            return

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        finally:
            if self._worker_task is task:
                self._worker_task = None
                self._worker_wake_event = None

    async def _outbox_worker(self) -> None:
        """Continuously deliver due outbox items until explicitly closed."""
        while True:
            wake_event = self._worker_wake_event
            if wake_event is None:
                return
            wake_event.clear()
            try:
                await self.process_outbox()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Unhandled error in API-cost webhook outbox worker")

            try:
                await asyncio.wait_for(
                    wake_event.wait(), timeout=self.webhook_poll_interval_seconds
                )
            except asyncio.TimeoutError:
                pass

    def _retry_at(self, attempt: int, now: datetime) -> datetime:
        """Return a bounded exponential equal-jitter retry timestamp."""
        exponential_cap = min(
            self.webhook_retry_max_seconds,
            self.webhook_retry_base_seconds * (2 ** max(0, attempt - 1)),
        )
        half_cap = exponential_cap / 2
        delay = half_cap + random.uniform(0, half_cap)
        return now + timedelta(seconds=delay)

    def _retry_state(
        self, attempt: int, now: datetime, error_message: str
    ) -> tuple[Optional[datetime], str]:
        """Return persisted scheduling and error state for a failed attempt."""
        if attempt >= self.webhook_max_attempts:
            return (
                None,
                f"Retry exhausted after {self.webhook_max_attempts} attempts: "
                f"{error_message}",
            )
        return self._retry_at(attempt, now), error_message

    async def recover_stale_deliveries(
        self, stale_timeout_seconds: Optional[int] = None
    ) -> None:
        """Recover abandoned claims without blocking the application event loop."""
        await asyncio.to_thread(
            self._recover_stale_deliveries_sync, stale_timeout_seconds
        )

    def _recover_stale_deliveries_sync(
        self, stale_timeout_seconds: Optional[int] = None
    ) -> None:
        """Recover processing claims in a worker thread."""
        if stale_timeout_seconds is None:
            stale_timeout_seconds = self.webhook_stale_timeout_seconds

        session = self.Session()
        try:
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(seconds=stale_timeout_seconds)
            stale_items = (
                session.query(WebhookOutbox)
                .filter(
                    WebhookOutbox.status == "processing",
                    or_(
                        WebhookOutbox.last_attempt.is_(None),
                        WebhookOutbox.last_attempt < cutoff,
                    ),
                )
                .all()
            )

            for item in stale_items:
                next_attempt_at, recovery_error = self._retry_state(
                    max(1, item.retry_count),
                    now,
                    "Recovery: Stale/Crashed delivery task recovered",
                )
                filters = [
                    WebhookOutbox.id == item.id,
                    WebhookOutbox.status == "processing",
                ]
                if item.last_attempt is None:
                    filters.append(WebhookOutbox.last_attempt.is_(None))
                else:
                    filters.append(WebhookOutbox.last_attempt == item.last_attempt)

                recovered = (
                    session.query(WebhookOutbox)
                    .filter(*filters)
                    .update(
                        {
                            WebhookOutbox.status: "failed",
                            WebhookOutbox.next_attempt_at: next_attempt_at,
                            WebhookOutbox.error_message: recovery_error,
                            WebhookOutbox.last_recovered_at: now,
                        },
                        synchronize_session=False,
                    )
                )
                if recovered:
                    logger.info(
                        "Recovered stale webhook delivery %s for %s (%s)",
                        item.id,
                        item.utc_date,
                        item.alert_type,
                    )

            session.commit()
        except Exception as e:
            logger.error("Error during stale webhook delivery recovery: %s", e)
            try:
                session.rollback()
            except Exception:
                pass
        finally:
            session.close()

    def _try_claim_outbox_item(
        self,
        item_id: int,
        claim_time: datetime,
        respect_schedule: bool = True,
    ) -> Optional[dict[str, Any]]:
        """Claim one due item with a single compare-and-swap UPDATE."""
        session = self.Session()
        try:
            filters = [
                WebhookOutbox.id == item_id,
                WebhookOutbox.status.in_(["pending", "failed"]),
                WebhookOutbox.retry_count < self.webhook_max_attempts,
            ]
            if respect_schedule:
                filters.append(
                    or_(
                        WebhookOutbox.next_attempt_at.is_(None),
                        WebhookOutbox.next_attempt_at <= claim_time,
                    )
                )

            claimed = (
                session.query(WebhookOutbox)
                .filter(*filters)
                .update(
                    {
                        WebhookOutbox.status: "processing",
                        WebhookOutbox.retry_count: WebhookOutbox.retry_count + 1,
                        WebhookOutbox.last_attempt: claim_time,
                        WebhookOutbox.claimed_at: claim_time,
                        WebhookOutbox.next_attempt_at: None,
                    },
                    synchronize_session=False,
                )
            )
            if claimed != 1:
                session.rollback()
                return None

            session.commit()
            item = session.query(WebhookOutbox).filter_by(id=item_id).one()
            return {
                "id": item.id,
                "payload": item.payload,
                "utc_date": item.utc_date,
                "alert_type": item.alert_type,
                "retry_count": item.retry_count,
                "last_attempt": item.last_attempt,
            }
        except Exception as e:
            logger.debug("Could not claim webhook outbox item %s: %s", item_id, e)
            try:
                session.rollback()
            except Exception:
                pass
            return None
        finally:
            session.close()

    def _complete_outbox_claim(
        self,
        claim: dict[str, Any],
        *,
        success: bool,
        error_message: Optional[str] = None,
    ) -> bool:
        """Conditionally complete exactly the attempt represented by ``claim``."""
        session = self.Session()
        try:
            values: dict[Any, Any]
            if success:
                values = {
                    WebhookOutbox.status: "sent",
                    WebhookOutbox.next_attempt_at: None,
                    WebhookOutbox.error_message: None,
                    WebhookOutbox.sent_at: datetime.now(timezone.utc),
                }
            else:
                next_attempt_at, persisted_error = self._retry_state(
                    claim["retry_count"],
                    datetime.now(timezone.utc),
                    error_message or "Delivery failed",
                )
                values = {
                    WebhookOutbox.status: "failed",
                    WebhookOutbox.next_attempt_at: next_attempt_at,
                    WebhookOutbox.error_message: persisted_error,
                }

            completed = (
                session.query(WebhookOutbox)
                .filter(
                    WebhookOutbox.id == claim["id"],
                    WebhookOutbox.status == "processing",
                    WebhookOutbox.retry_count == claim["retry_count"],
                    WebhookOutbox.last_attempt == claim["last_attempt"],
                )
                .update(values, synchronize_session=False)
            )
            if completed != 1:
                session.rollback()
                return False
            session.commit()
            return True
        except Exception as e:
            logger.error("Error completing outbox item %s: %s", claim["id"], e)
            try:
                session.rollback()
            except Exception:
                pass
            return False
        finally:
            session.close()

    def _select_outbox_item_ids(
        self, *, now: datetime, force: bool, max_items: Optional[int]
    ) -> list[int]:
        """Return due outbox IDs using a short worker-thread transaction."""
        session = self.Session()
        try:
            filters = [
                WebhookOutbox.status.in_(["pending", "failed"]),
                WebhookOutbox.retry_count < self.webhook_max_attempts,
            ]
            if not force:
                filters.append(
                    or_(
                        WebhookOutbox.next_attempt_at.is_(None),
                        WebhookOutbox.next_attempt_at <= now,
                    )
                )
            query = (
                session.query(WebhookOutbox.id)
                .filter(*filters)
                .order_by(WebhookOutbox.next_attempt_at, WebhookOutbox.id)
            )
            if max_items is not None:
                query = query.limit(max(0, max_items))
            return [row[0] for row in query.all()]
        except Exception as e:
            logger.error("Error selecting webhook outbox items: %s", e)
            return []
        finally:
            session.close()

    async def process_outbox(
        self, max_items: Optional[int] = None, *, force: bool = False
    ) -> int:
        """Deliver eligible items, honoring persisted due times by default.

        ``force=True`` is an explicit operational/test escape hatch that ignores
        only the due timestamp; compare-and-swap claims and retry bounds remain.
        """
        if not self.delivery_enabled:
            logger.debug("API-cost outbox delivery is disabled")
            return 0

        await self.recover_stale_deliveries()

        if not self.webhook_url:
            return 0

        item_ids = await asyncio.to_thread(
            self._select_outbox_item_ids,
            now=datetime.now(timezone.utc),
            force=force,
            max_items=max_items,
        )

        completed = 0
        for item_id in item_ids:
            claim = await asyncio.to_thread(
                self._try_claim_outbox_item,
                item_id,
                datetime.now(timezone.utc),
                respect_schedule=not force,
            )
            if claim is None:
                continue

            event_id = f"api-cost:{claim['utc_date']}:{claim['alert_type']}"
            token = _WEBHOOK_EVENT_ID.set(event_id)
            try:
                success = await self._send_webhook_notification(claim["payload"])
            except asyncio.CancelledError:
                await asyncio.to_thread(
                    self._complete_outbox_claim,
                    claim,
                    success=False,
                    error_message="Delivery cancelled during worker shutdown",
                )
                raise
            except Exception as e:
                logger.error("Webhook outbox delivery %s raised: %s", item_id, e)
                success = False
            finally:
                _WEBHOOK_EVENT_ID.reset(token)

            if await asyncio.to_thread(
                self._complete_outbox_claim, claim, success=success
            ):
                completed += 1

        return completed

    async def _send_webhook_notification(self, message: str) -> bool:
        """Send an async webhook notification if URL is configured.

        The payload carries both Slack's ``text`` and Discord's ``content``
        field so a generic incoming webhook works for either provider.

        Returns:
            True if the POST completed with a successful 2xx status; False otherwise.
        """
        if not self.webhook_url:
            return False

        try:
            payload = {"text": message, "content": message}
            event_id = _WEBHOOK_EVENT_ID.get()
            headers = (
                {"Idempotency-Key": event_id, "X-Event-ID": event_id}
                if event_id
                else None
            )
            request_kwargs: dict[str, Any] = {
                "json": payload,
                "timeout": aiohttp.ClientTimeout(total=5),
            }
            if headers is not None:
                request_kwargs["headers"] = headers
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    **request_kwargs,
                ) as response:
                    if response.status >= 200 and response.status < 300:
                        return True
                    else:
                        logger.error(
                            f"Failed to send webhook alert, status: {response.status}"
                        )
                        return False
        except Exception as e:
            logger.error(f"Error sending webhook alert: {e}")
            return False

    async def _send_budget_alert(self, current_cost: float, alert_type: str):
        """Send budget alert using configured webhook system and durable outbox"""
        alert_msg = f"🚨 API Budget Alert: ${current_cost:.2f} "

        if alert_type == "threshold":
            alert_msg += f"(Alert threshold: ${self.alert_threshold})"
        else:
            alert_msg += f"EXCEEDED daily budget of ${self.daily_budget}"

        logger.warning(alert_msg)

        self._trigger_delivery()

    async def get_daily_cost(self, date: str = None) -> float:
        """Get total cost for a specific date"""
        if not date:
            date = datetime.now(timezone.utc).date().isoformat()

        if self.Session is None:
            return 0.0
        try:
            return await asyncio.to_thread(self._get_daily_cost_sync, date)
        except Exception as exc:
            logger.error("Error getting daily cost: %s", exc)
            return 0.0

    def _get_daily_cost_sync(self, date: str) -> float:
        start_at, end_at = self._utc_day_bounds(date)
        with self._session_scope() as session:
            result = (
                session.query(func.sum(APIUsage.cost))
                .filter(
                    APIUsage.timestamp >= start_at,
                    APIUsage.timestamp < end_at,
                )
                .scalar()
            )
            return float(result) if result is not None else 0.0

    @staticmethod
    def _utc_day_bounds(
        value: Union[str, calendar_date],
    ) -> tuple[datetime, datetime]:
        """Return an indexable half-open UTC interval for one calendar day."""
        day = calendar_date.fromisoformat(value) if isinstance(value, str) else value
        start_at = datetime.combine(day, clock_time.min, tzinfo=timezone.utc)
        return start_at, start_at + timedelta(days=1)

    async def get_usage_analytics(self, days: int = 7) -> dict[str, Any]:
        """Get detailed usage analytics for the past N days"""
        if self.Session is None:
            return self._empty_usage_analytics(days)
        try:
            return await asyncio.to_thread(self._get_usage_analytics_sync, days)
        except Exception as exc:
            logger.error("Error generating usage analytics: %s", exc)
            return {}

    def _get_usage_analytics_sync(self, days: int) -> dict[str, Any]:
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=days)
        start_at, _ = self._utc_day_bounds(start_date)
        _, end_at = self._utc_day_bounds(end_date)
        today_start, today_end = self._utc_day_bounds(end_date)
        with self._session_scope() as session:
            service_stats_query = (
                session.query(
                    APIUsage.service,
                    func.sum(APIUsage.cost),
                    func.count(APIUsage.id),
                    func.avg(APIUsage.cost),
                )
                .filter(
                    APIUsage.timestamp >= start_at,
                    APIUsage.timestamp < end_at,
                )
                .group_by(APIUsage.service)
                .all()
            )
            service_stats = {}
            for row in service_stats_query:
                service, total_cost, request_count, avg_cost = row
                service_stats[service] = {
                    "total_cost": total_cost,
                    "request_count": request_count,
                    "average_cost": avg_cost,
                }

            daily_stats_query = (
                session.query(
                    func.date(APIUsage.timestamp).label("date"),
                    func.sum(APIUsage.cost),
                    func.count(APIUsage.id),
                )
                .filter(
                    APIUsage.timestamp >= start_at,
                    APIUsage.timestamp < end_at,
                )
                .group_by(func.date(APIUsage.timestamp))
                .order_by(func.date(APIUsage.timestamp))
                .all()
            )

            daily_stats = []
            for row in daily_stats_query:
                day_value, total_cost, request_count = row
                daily_stats.append(
                    {
                        "date": (
                            day_value.isoformat()
                            if hasattr(day_value, "isoformat")
                            else str(day_value)
                        ),
                        "total_cost": total_cost,
                        "request_count": request_count,
                    }
                )

            error_rates_query = (
                session.query(
                    APIUsage.service,
                    func.sum(case((APIUsage.success.is_(False), 1), else_=0)),
                    func.count(APIUsage.id),
                )
                .filter(
                    APIUsage.timestamp >= start_at,
                    APIUsage.timestamp < end_at,
                )
                .group_by(APIUsage.service)
                .all()
            )

            error_rates = {}
            for row in error_rates_query:
                service, errors, total = row
                error_rates[service] = {
                    "error_count": errors or 0,
                    "total_requests": total,
                    "error_rate": (
                        (errors / total) * 100
                        if total > 0 and errors is not None
                        else 0
                    ),
                }

            session_stats = {
                "costs": dict(self.session_costs),
                "requests": dict(self.session_requests),
            }
            today_cost_result = (
                session.query(func.sum(APIUsage.cost))
                .filter(
                    APIUsage.timestamp >= today_start,
                    APIUsage.timestamp < today_end,
                )
                .scalar()
            )
            today_cost = (
                float(today_cost_result) if today_cost_result is not None else 0.0
            )

            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days,
                },
                "service_breakdown": service_stats,
                "daily_breakdown": daily_stats,
                "error_rates": error_rates,
                "current_session": session_stats,
                "budget_status": {
                    "daily_budget": self.daily_budget,
                    "alert_threshold": self.alert_threshold,
                    "today_cost": today_cost,
                    "budget_remaining": max(0.0, self.daily_budget - today_cost),
                },
            }

    def _empty_usage_analytics(self, days: int) -> dict[str, Any]:
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=days)
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days,
            },
            "service_breakdown": {},
            "daily_breakdown": [],
            "error_rates": {},
            "current_session": {
                "costs": dict(self.session_costs),
                "requests": dict(self.session_requests),
            },
            "budget_status": {
                "daily_budget": self.daily_budget,
                "alert_threshold": self.alert_threshold,
                "today_cost": 0.0,
                "budget_remaining": self.daily_budget,
            },
        }

    async def optimize_api_usage(self) -> dict[str, Any]:
        """Provide API usage optimization recommendations"""
        analytics = await self.get_usage_analytics(30)  # 30-day analysis
        recommendations = []

        # Check for high-cost services
        for service, stats in analytics.get("service_breakdown", {}).items():
            avg_cost = stats.get("average_cost", 0)
            if avg_cost > 0.01:  # High average cost per request
                recommendations.append(
                    f"Consider caching for {service} (avg cost: ${avg_cost:.4f}/request)"
                )

        # Check error rates
        for service, rates in analytics.get("error_rates", {}).items():
            error_rate = rates.get("error_rate", 0)
            if error_rate > 5:  # More than 5% error rate
                recommendations.append(
                    f"High error rate for {service}: {error_rate:.1f}% - implement better error handling"
                )

        # Budget analysis
        budget_status = analytics.get("budget_status", {})
        utilization = (
            budget_status.get("today_cost", 0) / budget_status.get("daily_budget", 1)
        ) * 100

        if utilization > 80:
            recommendations.append(
                "Approaching daily budget limit - consider implementing request throttling"
            )

        return {
            "recommendations": recommendations,
            "budget_utilization": f"{utilization:.1f}%",
            "top_cost_services": sorted(
                analytics.get("service_breakdown", {}).items(),
                key=lambda x: x[1].get("total_cost", 0),
                reverse=True,
            )[:3],
        }

    def get_current_quota_usage(self) -> dict[str, int]:
        """Get current quota usage for all services"""
        usage = {}
        for service, limiter in self.rate_limiters.items():
            usage[service] = len(limiter.requests)
        return usage

    async def get_cost_dashboard(self) -> dict[str, Any]:
        """Get real-time cost dashboard data"""
        analytics = await self.get_usage_analytics(1)  # Today's data
        optimization = await self.optimize_api_usage()

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "today_summary": {
                "total_cost": await self.get_daily_cost(),
                "budget_remaining": max(
                    0.0, self.daily_budget - await self.get_daily_cost()
                ),
                "requests_made": sum(
                    stats.get("request_count", 0)
                    for stats in analytics.get("service_breakdown", {}).values()
                ),
                "services_used": len(analytics.get("service_breakdown", {})),
            },
            "rate_limit_status": {
                service: {
                    "requests_used": len(limiter.requests),
                    "limit": limiter.max_requests,
                    "window_seconds": limiter.window_seconds,
                }
                for service, limiter in self.rate_limiters.items()
            },
            "circuit_breaker_status": dict(self.circuit_breakers.items()),
            "optimization": optimization,
        }

    async def cleanup_old_data(self):
        """Clean up old API usage data to prevent database bloat"""
        try:
            logger.info("Using basic cleanup for API costs via SQLAlchemy ORM")
            await self._basic_cost_cleanup()
        except Exception as e:
            logger.error(f"Error in API cost cleanup process: {e}")

    async def _basic_cost_cleanup(self):
        """Basic cleanup fallback for API cost data using SQLAlchemy"""
        await asyncio.to_thread(self._basic_cost_cleanup_sync)

    def _basic_cost_cleanup_sync(self) -> None:
        try:
            usage_cutoff = datetime.now(timezone.utc) - timedelta(days=90)
            budget_cutoff = (
                (datetime.now(timezone.utc) - timedelta(days=365)).date().isoformat()
            )

            with self._session_scope(commit=True) as session:
                session.execute(
                    delete(APIUsage).where(APIUsage.timestamp < usage_cutoff)
                )
                session.execute(
                    delete(DailyBudget).where(DailyBudget.date < budget_cutoff)
                )
                session.execute(
                    delete(WebhookOutbox).where(WebhookOutbox.utc_date < budget_cutoff)
                )
            logger.info("Basic API cost cleanup completed successfully")
        except Exception as exc:
            logger.error("Error in basic API cost cleanup: %s", exc)

    async def trigger_manual_cleanup(self) -> dict[str, Any]:
        """Manually clean API-cost data and return a summary."""
        try:
            return await asyncio.to_thread(self._trigger_manual_cleanup_sync)
        except Exception as exc:
            logger.error("Error in manual API cost cleanup: %s", exc)
            return {"error": str(exc)}

    def _trigger_manual_cleanup_sync(self) -> dict[str, Any]:
        start_time = time.time()
        with self._session_scope(commit=True) as session:
            usage_cutoff = datetime.now(timezone.utc) - timedelta(days=90)
            budget_cutoff = (
                (datetime.now(timezone.utc) - timedelta(days=365)).date().isoformat()
            )

            before_usage = session.query(APIUsage).count()
            before_budgets = session.query(DailyBudget).count()
            before_outbox = session.query(WebhookOutbox).count()

            session.execute(delete(APIUsage).where(APIUsage.timestamp < usage_cutoff))
            session.execute(delete(DailyBudget).where(DailyBudget.date < budget_cutoff))
            session.execute(
                delete(WebhookOutbox).where(WebhookOutbox.utc_date < budget_cutoff)
            )
            session.flush()

            after_usage = session.query(APIUsage).count()
            after_budgets = session.query(DailyBudget).count()
            after_outbox = session.query(WebhookOutbox).count()

            records_deleted = (
                (before_usage - after_usage)
                + (before_budgets - after_budgets)
                + (before_outbox - after_outbox)
            )

        cleanup_summary = {
            "database": self.db_path,
            "tables_cleaned": 3,
            "total_records_deleted": records_deleted,
            "total_space_freed_mb": 0.0,
            "execution_time_seconds": time.time() - start_time,
            "successful_cleanups": 3,
            "failed_cleanups": 0,
            "details": [
                {
                    "table": "api_usage",
                    "records_deleted": before_usage - after_usage,
                    "space_freed_mb": 0.0,
                    "execution_time_ms": int((time.time() - start_time) * 1000),
                    "success": True,
                    "error": None,
                },
                {
                    "table": "daily_budgets",
                    "records_deleted": before_budgets - after_budgets,
                    "space_freed_mb": 0.0,
                    "execution_time_ms": 0,
                    "success": True,
                    "error": None,
                },
                {
                    "table": "webhook_outbox",
                    "records_deleted": before_outbox - after_outbox,
                    "space_freed_mb": 0.0,
                    "execution_time_ms": 0,
                    "success": True,
                    "error": None,
                },
            ],
        }
        logger.info("Manual API cost cleanup completed: %s", cleanup_summary)
        return cleanup_summary


_cost_monitor_instance: Optional[APICostMonitor] = None
_cost_monitor_lock = threading.Lock()


def get_cost_monitor() -> APICostMonitor:
    """Return the process-wide monitor, creating it only on first use."""
    global _cost_monitor_instance
    if _cost_monitor_instance is None:
        with _cost_monitor_lock:
            if _cost_monitor_instance is None:
                _cost_monitor_instance = APICostMonitor()
    return _cost_monitor_instance


async def ensure_api_cost_database_ready() -> None:
    """Asynchronously validate runtime database compatibility and privileges."""
    monitor = get_cost_monitor()
    if not monitor.cost_tracking_enabled and not monitor.delivery_enabled:
        return
    await asyncio.to_thread(monitor.ensure_database_ready)


class _LazyCostMonitor:
    """Compatibility proxy for callers importing the historical global name."""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_cost_monitor(), name)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(get_cost_monitor(), name, value)


cost_monitor = _LazyCostMonitor()


async def track_api_call(
    service: str, endpoint: str, tokens: int, **kwargs
) -> APIUsageRecord:
    """Convenience function for tracking API calls"""
    return await cost_monitor.record_usage(service, endpoint, tokens, **kwargs)


def check_rate_limit_decorator(service: str):
    """Decorator to check rate limits before API calls"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            allowed, wait_time = cost_monitor.check_rate_limit(service)
            if not allowed:
                logger.warning(
                    f"⏰ Rate limit reached for {service}, waiting {wait_time}s"
                )
                await asyncio.sleep(wait_time)

            if cost_monitor.check_circuit_breaker(service):
                raise Exception(f"Circuit breaker open for {service}")

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                cost_monitor.record_api_failure(service, str(e))
                raise

        return wrapper

    return decorator


if __name__ == "__main__":
    # Test the cost monitor
    import asyncio

    async def test_cost_monitor():
        monitor = APICostMonitor(db_path=DEFAULT_DB_PATH)

        # Test usage recording
        await monitor.record_usage(
            service="openai",
            endpoint="chat/completions",
            tokens_used=1500,
            model="gpt-4o-mini",
            output_tokens=500,
            request_type="video_analysis",
        )

        # Get analytics
        analytics = await monitor.get_usage_analytics()
        print("📊 Usage Analytics:")
        print(json.dumps(analytics, indent=2, default=str))

        # Get dashboard
        dashboard = await monitor.get_cost_dashboard()
        print("\n📈 Cost Dashboard:")
        print(json.dumps(dashboard, indent=2, default=str))

    asyncio.run(test_cost_monitor())
