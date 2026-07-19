"""Canonical SQLAlchemy models for API usage and durable budget alerts."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class APIUsage(Base):
    """One billable or quota-bearing provider API operation."""

    __tablename__ = "api_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    tokens_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    cost: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
        index=True,
    )
    request_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    video_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    success: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "tokens_used >= 0", name="ck_api_usage_tokens_used_nonnegative"
        ),
        CheckConstraint("cost >= 0", name="ck_api_usage_cost_nonnegative"),
    )


class DailyBudget(Base):
    """UTC daily API spend aggregate and alert state."""

    __tablename__ = "daily_budgets"

    date: Mapped[str] = mapped_column(String(10), primary_key=True)
    total_cost: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        server_default=text("0"),
    )
    alert_sent: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    budget_exceeded: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    __table_args__ = (
        CheckConstraint(
            "total_cost >= 0", name="ck_daily_budgets_total_cost_nonnegative"
        ),
    )


class WebhookOutbox(Base):
    """Durable alert delivery state shared by API and worker processes."""

    __tablename__ = "webhook_outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    utc_date: Mapped[str] = mapped_column(String(10), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    last_attempt: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    claim_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_recovered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_cost: Mapped[float] = mapped_column(Float, nullable=False)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("utc_date", "alert_type", name="uq_utc_date_alert_type"),
        CheckConstraint(
            "status IN ('pending', 'processing', 'sent', 'failed')",
            name="ck_webhook_outbox_status",
        ),
        CheckConstraint(
            "retry_count >= 0",
            name="ck_webhook_outbox_retry_count_nonnegative",
        ),
        CheckConstraint(
            "current_cost >= 0",
            name="ck_webhook_outbox_current_cost_nonnegative",
        ),
        Index(
            "ix_webhook_outbox_due",
            "status",
            "next_attempt_at",
            "retry_count",
            "id",
        ),
        Index(
            "ix_webhook_outbox_stale_claims",
            "status",
            "claimed_at",
            "id",
        ),
    )
