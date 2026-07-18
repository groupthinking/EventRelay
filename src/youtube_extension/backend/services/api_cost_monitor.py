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
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import aiohttp
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    UniqueConstraint,
    case,
    create_engine,
    delete,
    func,
    or_,
    text,
)
from sqlalchemy.orm import declarative_base, sessionmaker

# Default database location. Allow override via environment variable.
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

# SQLAlchemy Base Declarative
Base = declarative_base()


class APIUsage(Base):
    """SQLAlchemy model for API usage records"""

    __tablename__ = "api_usage"
    id = Column(Integer, primary_key=True, autoincrement=True)
    service = Column(String, nullable=False, index=True)
    endpoint = Column(String, nullable=False)
    tokens_used = Column(Integer, default=0)
    cost = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    request_type = Column(String, nullable=True)
    user_id = Column(String, nullable=True)
    video_id = Column(String, nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(String, nullable=True)


class DailyBudget(Base):
    """SQLAlchemy model for daily budgets"""

    __tablename__ = "daily_budgets"
    date = Column(String, primary_key=True)
    total_cost = Column(Float, default=0.0)
    alert_sent = Column(Boolean, default=False)
    budget_exceeded = Column(Boolean, default=False)


class WebhookOutbox(Base):
    """SQLAlchemy model for durable webhook outbox"""

    __tablename__ = "webhook_outbox"
    id = Column(Integer, primary_key=True, autoincrement=True)
    utc_date = Column(String, nullable=False)
    alert_type = Column(String, nullable=False)
    status = Column(
        String, nullable=False, default="pending"
    )  # pending, processing, sent, failed
    retry_count = Column(Integer, nullable=False, default=0)
    last_attempt = Column(DateTime, nullable=True)
    next_attempt_at = Column(DateTime, nullable=True)
    error_message = Column(String, nullable=True)
    current_cost = Column(Float, nullable=False)
    payload = Column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint("utc_date", "alert_type", name="uq_utc_date_alert_type"),
        Index("ix_webhook_outbox_due", "status", "next_attempt_at", "retry_count"),
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

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the API cost monitor"""
        resolved_path = db_path or DEFAULT_DB_PATH
        if resolved_path not in {":memory:", ":memory"}:
            resolved_path = str(Path(resolved_path).expanduser().resolve())
        self.db_path = resolved_path
        self.daily_budget = float(os.getenv("API_DAILY_BUDGET", "10.00"))
        self.alert_threshold = float(os.getenv("API_ALERT_THRESHOLD", "8.00"))
        self.cost_tracking_enabled = (
            os.getenv("API_COST_TRACKING", "true").lower() == "true"
        )

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

        # Initialize engine and sessionmaker
        if self.db_path in {":memory:", ":memory"}:
            self.engine = create_engine("sqlite://", connect_args={"timeout": 30})
        else:
            self.engine = create_engine(
                f"sqlite:///{self.db_path}", connect_args={"timeout": 30}
            )
        self.Session = sessionmaker(bind=self.engine)

        # Initialize database
        self._init_database()

        logger.info(
            f"📊 API Cost Monitor initialized - Budget: ${self.daily_budget}, Alert: ${self.alert_threshold}"
        )

    def _init_database(self):
        """Initialize the database schema using SQLAlchemy Base Metadata"""
        try:
            if self.db_path not in {":memory:", ":memory"}:
                db_parent = Path(self.db_path).expanduser().resolve().parent
                db_parent.mkdir(parents=True, exist_ok=True)

            Base.metadata.create_all(self.engine)
            self._upgrade_sqlite_outbox_schema()

        except Exception as e:
            logger.error(f"Failed to initialize cost monitoring database: {e}")
            raise

    def _upgrade_sqlite_outbox_schema(self) -> None:
        """Add scheduling state to existing SQLite databases without data loss."""
        if self.engine.dialect.name != "sqlite":
            return

        # Serialize the inspect/ALTER/index sequence. A deferred transaction lets
        # two processes both observe the missing column before either writes;
        # BEGIN EXCLUSIVE makes the second process inspect only after the first
        # migration commits.
        with self.engine.connect() as connection:
            connection.exec_driver_sql("BEGIN EXCLUSIVE")
            try:
                columns = {
                    row[1]
                    for row in connection.exec_driver_sql(
                        "PRAGMA table_info(webhook_outbox)"
                    )
                }
                if "next_attempt_at" not in columns:
                    connection.exec_driver_sql(
                        "ALTER TABLE webhook_outbox ADD COLUMN next_attempt_at DATETIME"
                    )
                index_columns = [
                    row[2]
                    for row in connection.exec_driver_sql(
                        "PRAGMA index_info(ix_webhook_outbox_due)"
                    )
                ]
                expected_columns = ["status", "next_attempt_at", "retry_count"]
                if index_columns and index_columns != expected_columns:
                    connection.exec_driver_sql(
                        "DROP INDEX IF EXISTS ix_webhook_outbox_due"
                    )
                connection.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS ix_webhook_outbox_due "
                    "ON webhook_outbox (status, next_attempt_at, retry_count)"
                )
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

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

        # Store in database
        session = self.Session()
        try:
            db_record = APIUsage(
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
            session.add(db_record)
            session.commit()
        except Exception as e:
            logger.error(f"Failed to record API usage: {e}")
            try:
                session.rollback()
            except Exception:
                pass
        finally:
            session.close()

        # Check budget alerts
        await self._check_budget_alerts()

        logger.debug(f"💰 API Usage: {service} - ${cost:.4f} ({tokens_used} tokens)")

        return record

    async def _check_budget_alerts(self) -> None:
        """Check and send budget alerts if thresholds are exceeded.

        ``record_usage`` calls this after every usage record, so alerts must be
        gated: each alert type is dispatched at most once per UTC day, the first
        time that day's spend crosses the corresponding threshold. Without this,
        every subsequent API call would re-send the webhook and flood recipients.
        """
        try:
            today = datetime.now(timezone.utc).date().isoformat()
            daily_cost = await self.get_daily_cost(today)

            if daily_cost >= self.alert_threshold and self._claim_alert(
                today, "threshold", daily_cost
            ):
                await self._send_budget_alert(daily_cost, "threshold")

            if daily_cost >= self.daily_budget and self._claim_alert(
                today, "exceeded", daily_cost
            ):
                await self._send_budget_alert(daily_cost, "exceeded")

        except Exception as e:
            logger.error(f"Error checking budget alerts: {e}")

    def _claim_alert(
        self, date: str, alert_type: str, current_cost: float = 0.0
    ) -> bool:
        """Atomically claim today's alert of ``alert_type``.

        Returns True only for the caller that first inserts the outbox item
        or flips the day's flag from 0 to 1 in a context-managed SQLAlchemy session.
        Because the transaction commits atomically, concurrent processes racing
        cannot both win, ensuring each alert is dispatched at most once per UTC day.
        """
        session = self.Session()
        try:
            # Check if outbox item already exists to avoid unnecessary locks
            existing = (
                session.query(WebhookOutbox)
                .filter_by(utc_date=date, alert_type=alert_type)
                .first()
            )
            if existing:
                return False

            # Update or create DailyBudget record
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

            # Prepare payload message
            alert_msg = f"🚨 API Budget Alert: ${current_cost:.2f} "
            if alert_type == "threshold":
                alert_msg += f"(Alert threshold: ${self.alert_threshold})"
            else:
                alert_msg += f"EXCEEDED daily budget of ${self.daily_budget}"

            # Create outbox item
            outbox_item = WebhookOutbox(
                utc_date=date,
                alert_type=alert_type,
                status="pending",
                retry_count=0,
                current_cost=current_cost,
                payload=alert_msg,
            )
            session.add(outbox_item)
            session.commit()
            return True
        except Exception as e:
            logger.debug(
                f"Failed to claim alert due to concurrency or database exception: {e}"
            )
            try:
                session.rollback()
            except Exception:
                pass
            return False
        finally:
            session.close()

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
            logger.error(f"Error during stale webhook delivery recovery: {e}")
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

    def _select_outbox_item_ids(self, *, now: datetime, force: bool) -> list[int]:
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
            return [
                row[0]
                for row in (
                    session.query(WebhookOutbox.id)
                    .filter(*filters)
                    .order_by(WebhookOutbox.next_attempt_at, WebhookOutbox.id)
                    .all()
                )
            ]
        except Exception as e:
            logger.error("Error selecting webhook outbox items: %s", e)
            return []
        finally:
            session.close()

    async def process_outbox(self, *, force: bool = False) -> int:
        """Deliver eligible items, honoring persisted due times by default.

        ``force=True`` is an explicit operational/test escape hatch that ignores
        only the due timestamp; compare-and-swap claims and retry bounds remain.
        """
        await self.recover_stale_deliveries()

        # Configuration absence is not a successful delivery and must not consume
        # an attempt. The worker will revisit the pending row after configuration.
        if not self.webhook_url:
            return 0

        item_ids = await asyncio.to_thread(
            self._select_outbox_item_ids,
            now=datetime.now(timezone.utc),
            force=force,
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

        session = self.Session()
        try:
            result = (
                session.query(func.sum(APIUsage.cost))
                .filter(func.date(APIUsage.timestamp) == date)
                .scalar()
            )
            return float(result) if result is not None else 0.0
        except Exception as e:
            logger.error(f"Error getting daily cost: {e}")
            return 0.0
        finally:
            session.close()

    async def get_usage_analytics(self, days: int = 7) -> dict[str, Any]:
        """Get detailed usage analytics for the past N days"""
        session = self.Session()
        try:
            # Date range
            end_date = datetime.now(timezone.utc).date()
            start_date = end_date - timedelta(days=days)

            # Total costs by service
            service_stats_query = (
                session.query(
                    APIUsage.service,
                    func.sum(APIUsage.cost),
                    func.count(APIUsage.id),
                    func.avg(APIUsage.cost),
                )
                .filter(
                    func.date(APIUsage.timestamp).between(
                        start_date.isoformat(), end_date.isoformat()
                    )
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

            # Daily breakdown
            daily_stats_query = (
                session.query(
                    func.date(APIUsage.timestamp).label("date"),
                    func.sum(APIUsage.cost),
                    func.count(APIUsage.id),
                )
                .filter(
                    func.date(APIUsage.timestamp).between(
                        start_date.isoformat(), end_date.isoformat()
                    )
                )
                .group_by(func.date(APIUsage.timestamp))
                .order_by(func.date(APIUsage.timestamp))
                .all()
            )

            daily_stats = []
            for row in daily_stats_query:
                date, total_cost, request_count = row
                daily_stats.append(
                    {
                        "date": date,
                        "total_cost": total_cost,
                        "request_count": request_count,
                    }
                )

            # Error rates
            error_rates_query = (
                session.query(
                    APIUsage.service,
                    func.sum(case((APIUsage.success.is_(False), 1), else_=0)),
                    func.count(APIUsage.id),
                )
                .filter(
                    func.date(APIUsage.timestamp).between(
                        start_date.isoformat(), end_date.isoformat()
                    )
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

            # Current session stats
            session_stats = {
                "costs": dict(self.session_costs),
                "requests": dict(self.session_requests),
            }

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
                    "today_cost": await self.get_daily_cost(),
                    "budget_remaining": max(
                        0.0, self.daily_budget - await self.get_daily_cost()
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Error generating usage analytics: {e}")
            return {}
        finally:
            session.close()

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
        try:
            usage_cutoff = datetime.now(timezone.utc) - timedelta(days=90)
            budget_cutoff = (
                (datetime.now(timezone.utc) - timedelta(days=365)).date().isoformat()
            )

            session = self.Session()
            try:
                session.execute(
                    delete(APIUsage).where(APIUsage.timestamp < usage_cutoff)
                )
                session.execute(
                    delete(DailyBudget).where(DailyBudget.date < budget_cutoff)
                )
                session.execute(
                    delete(WebhookOutbox).where(WebhookOutbox.utc_date < budget_cutoff)
                )
                session.commit()
                logger.info("Basic API cost cleanup completed successfully")
            except Exception as e:
                session.rollback()
                logger.error(f"Error in basic API cost cleanup: {e}")
            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error in basic API cost cleanup: {e}")

    async def trigger_manual_cleanup(self) -> dict[str, Any]:
        """Manually trigger API cost database cleanup and return results using SQLAlchemy"""
        try:
            start_time = time.time()
            session = self.Session()
            try:
                usage_cutoff = datetime.now(timezone.utc) - timedelta(days=90)
                budget_cutoff = (
                    (datetime.now(timezone.utc) - timedelta(days=365))
                    .date()
                    .isoformat()
                )

                # Get counts before deletion
                before_usage = session.query(APIUsage).count()
                before_budgets = session.query(DailyBudget).count()
                before_outbox = session.query(WebhookOutbox).count()

                session.execute(
                    delete(APIUsage).where(APIUsage.timestamp < usage_cutoff)
                )
                session.execute(
                    delete(DailyBudget).where(DailyBudget.date < budget_cutoff)
                )
                session.execute(
                    delete(WebhookOutbox).where(WebhookOutbox.utc_date < budget_cutoff)
                )
                session.commit()

                after_usage = session.query(APIUsage).count()
                after_budgets = session.query(DailyBudget).count()
                after_outbox = session.query(WebhookOutbox).count()

                records_deleted = (
                    (before_usage - after_usage)
                    + (before_budgets - after_budgets)
                    + (before_outbox - after_outbox)
                )

                # Reclaim space
                session.execute(text("VACUUM"))
            except Exception as e:
                session.rollback()
                raise e
            finally:
                session.close()

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

            logger.info(f"Manual API cost cleanup completed: {cleanup_summary}")
            return cleanup_summary

        except Exception as e:
            logger.error(f"Error in manual API cost cleanup: {e}")
            return {"error": str(e)}


# Global instance
cost_monitor = APICostMonitor()


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
        monitor = APICostMonitor()

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
