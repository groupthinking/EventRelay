#!/usr/bin/env python3
"""
API Cost Monitoring and Management Service
==========================================

Real-time API cost tracking, quota management, and optimization for UVAI platform.
Monitors OpenAI, Anthropic, Gemini, YouTube Data API, and other service usage.
"""

import asyncio
import json
import logging
import os
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
    Integer,
    String,
    UniqueConstraint,
    case,
    create_engine,
    delete,
    func,
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
    error_message = Column(String, nullable=True)
    current_cost = Column(Float, nullable=False)
    payload = Column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint("utc_date", "alert_type", name="uq_utc_date_alert_type"),
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
            "gemini-1.5-flash": {"input": 0.000075, "output": 0.003},
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

            # Trigger stale webhook recoveries asynchronously
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.recover_stale_deliveries())
            except RuntimeError:
                threading.Thread(
                    target=lambda: asyncio.run(self.recover_stale_deliveries()),
                    daemon=True,
                ).start()

        except Exception as e:
            logger.error(f"Failed to initialize cost monitoring database: {e}")

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
        """Trigger non-blocking, asynchronous delivery of pending/failed alerts."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.process_outbox())
        except RuntimeError:
            threading.Thread(
                target=lambda: asyncio.run(self.process_outbox()), daemon=True
            ).start()

    async def recover_stale_deliveries(self, stale_timeout_seconds: int = 30):
        """Recover items stuck in 'processing' status (due to crashes, task cancellation, etc.)"""
        session = self.Session()
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(
                seconds=stale_timeout_seconds
            )
            stale_items = (
                session.query(WebhookOutbox)
                .filter(
                    WebhookOutbox.status == "processing",
                    WebhookOutbox.last_attempt < cutoff,
                )
                .all()
            )

            for item in stale_items:
                item.status = "failed"
                item.error_message = "Recovery: Stale/Crashed delivery task recovered"
                logger.info(
                    f"Recovered stale webhook delivery {item.id} for {item.utc_date} ({item.alert_type})"
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

    async def process_outbox(self):
        """Process pending/failed outbox deliveries with bounded retry and crash recovery."""
        await self.recover_stale_deliveries()

        session = self.Session()
        try:
            items = (
                session.query(WebhookOutbox)
                .filter(
                    WebhookOutbox.status.in_(["pending", "failed"]),
                    WebhookOutbox.retry_count < 5,  # Bounded retry limit of 5
                )
                .all()
            )

            if not items:
                return

            for item in items:
                item_id = item.id
                payload = item.payload

                # Atomically claim this specific item
                try:
                    db_item = session.query(WebhookOutbox).filter_by(id=item_id).first()
                    if (
                        db_item
                        and db_item.status in ["pending", "failed"]
                        and db_item.retry_count < 5
                    ):
                        db_item.status = "processing"
                        db_item.retry_count += 1
                        db_item.last_attempt = datetime.now(timezone.utc)
                        session.commit()
                    else:
                        continue
                except Exception as e:
                    logger.error(f"Error claiming outbox item {item_id}: {e}")
                    try:
                        session.rollback()
                    except Exception:
                        pass
                    continue

                # Run delivery without blocking the session or holding database locks
                success = await self._send_webhook_notification(payload)

                # Update item status based on delivery outcome
                try:
                    db_item = session.query(WebhookOutbox).filter_by(id=item_id).first()
                    if db_item:
                        if success:
                            db_item.status = "sent"
                            db_item.error_message = None
                        else:
                            db_item.status = "failed"
                            db_item.error_message = "Delivery failed"
                        session.commit()
                except Exception as e:
                    logger.error(
                        f"Error updating status for outbox item {item_id}: {e}"
                    )
                    try:
                        session.rollback()
                    except Exception:
                        pass
        finally:
            session.close()

    async def _send_webhook_notification(self, message: str) -> bool:
        """Send an async webhook notification if URL is configured.

        The payload carries both Slack's ``text`` and Discord's ``content``
        field so a generic incoming webhook works for either provider.

        Returns:
            True if the POST completed with a successful 2xx status; False otherwise.
        """
        if not self.webhook_url:
            return True  # Behave as successful delivery if no webhook is configured

        try:
            payload = {"text": message, "content": message}
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=5),
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
