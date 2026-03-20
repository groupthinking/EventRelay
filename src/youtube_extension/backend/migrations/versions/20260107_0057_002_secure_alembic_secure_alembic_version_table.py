"""Secure Alembic Version Table

Revision ID: 002_secure_alembic
Revises: 001_initial_schema
Create Date: 2026-01-07 00:57:13.364248

"""
from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '002_secure_alembic'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema"""
    # Option 2: Enable RLS and deny access strictly
    op.execute("ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON public.alembic_version FROM PUBLIC, anon, authenticated")
    # No policies added -> effective deny-all for non-superusers

def downgrade() -> None:
    """Downgrade database schema"""
    op.execute("ALTER TABLE public.alembic_version DISABLE ROW LEVEL SECURITY")
    op.execute("GRANT SELECT ON public.alembic_version TO authenticated")
    # Note: Adjust GRANT as needed for your previous state
