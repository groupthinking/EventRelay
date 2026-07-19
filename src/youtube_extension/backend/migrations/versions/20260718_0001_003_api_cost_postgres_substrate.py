"""Create the shared PostgreSQL substrate for API-cost delivery.

Revision ID: 003_api_cost_postgres
Revises: 002_secure_alembic
Create Date: 2026-07-18 00:01:00
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_api_cost_postgres"
down_revision: Union[str, None] = "002_secure_alembic"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "api_usage",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("service", sa.String(length=100), nullable=False),
        sa.Column("endpoint", sa.String(length=255), nullable=False),
        sa.Column(
            "tokens_used", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("cost", sa.Float(), nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("request_type", sa.String(length=100), nullable=True),
        sa.Column("user_id", sa.String(length=255), nullable=True),
        sa.Column("video_id", sa.String(length=255), nullable=True),
        sa.Column(
            "success", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "tokens_used >= 0", name="ck_api_usage_tokens_used_nonnegative"
        ),
        sa.CheckConstraint("cost >= 0", name="ck_api_usage_cost_nonnegative"),
        sa.PrimaryKeyConstraint("id", name="pk_api_usage"),
    )
    op.create_index("ix_api_usage_service", "api_usage", ["service"], unique=False)
    op.create_index("ix_api_usage_timestamp", "api_usage", ["timestamp"], unique=False)

    op.create_table(
        "daily_budgets",
        sa.Column("date", sa.String(length=10), nullable=False),
        sa.Column(
            "total_cost", sa.Float(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "alert_sent",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "budget_exceeded",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "total_cost >= 0", name="ck_daily_budgets_total_cost_nonnegative"
        ),
        sa.PrimaryKeyConstraint("date", name="pk_daily_budgets"),
    )

    op.create_table(
        "webhook_outbox",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("utc_date", sa.String(length=10), nullable=False),
        sa.Column("alert_type", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column(
            "retry_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("last_attempt", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claim_token", sa.String(length=64), nullable=True),
        sa.Column("last_recovered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("current_cost", sa.Float(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'sent', 'failed')",
            name="ck_webhook_outbox_status",
        ),
        sa.CheckConstraint(
            "retry_count >= 0",
            name="ck_webhook_outbox_retry_count_nonnegative",
        ),
        sa.CheckConstraint(
            "current_cost >= 0",
            name="ck_webhook_outbox_current_cost_nonnegative",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_webhook_outbox"),
        sa.UniqueConstraint("utc_date", "alert_type", name="uq_utc_date_alert_type"),
    )
    op.create_index(
        "ix_webhook_outbox_due",
        "webhook_outbox",
        ["status", "next_attempt_at", "retry_count", "id"],
        unique=False,
    )
    op.create_index(
        "ix_webhook_outbox_stale_claims",
        "webhook_outbox",
        ["status", "claimed_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_outbox_stale_claims", table_name="webhook_outbox")
    op.drop_index("ix_webhook_outbox_due", table_name="webhook_outbox")
    op.drop_table("webhook_outbox")
    op.drop_table("daily_budgets")
    op.drop_index("ix_api_usage_timestamp", table_name="api_usage")
    op.drop_index("ix_api_usage_service", table_name="api_usage")
    op.drop_table("api_usage")
