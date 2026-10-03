"""Track Studio generation attempts so interrupted work can be identified.

Revision ID: 0009_studio_attempts
Revises: 0008_studio_drafts
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_studio_attempts"
down_revision = "0008_studio_drafts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("studio_drafts", sa.Column("generation_started_at", sa.DateTime(timezone=True)))
    op.add_column("studio_drafts", sa.Column("generation_attempt_id", sa.UUID()))


def downgrade() -> None:
    op.drop_column("studio_drafts", "generation_attempt_id")
    op.drop_column("studio_drafts", "generation_started_at")
