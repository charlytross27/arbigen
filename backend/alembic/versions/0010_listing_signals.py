"""Preserve normalized listing signals and search result context.

Revision ID: 0010_listing_signals
Revises: 0009_studio_attempts
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "0010_listing_signals"
down_revision = "0009_studio_attempts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("listing_signals", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("marketplace_snapshots", sa.Column("reported_total_results", sa.Integer()))


def downgrade() -> None:
    op.drop_column("marketplace_snapshots", "reported_total_results")
    op.drop_column("products", "listing_signals")
