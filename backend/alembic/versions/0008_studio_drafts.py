"""Stage large Studio images outside Function request and response bodies.

Revision ID: 0008_studio_drafts
Revises: 0007_catalog_source
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_studio_drafts"
down_revision = "0007_catalog_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "studio_drafts",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_name", sa.String(160), nullable=False),
        sa.Column("original_mime_type", sa.String(32), nullable=False),
        sa.Column("original_size", sa.Integer(), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="uploading"),
        sa.Column("configuration", sa.JSON(), nullable=True),
        sa.Column("preview_ids", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("original_size > 0 AND original_size <= 10485760", name="studio_draft_size"),
    )
    op.create_index("ix_studio_drafts_user_id", "studio_drafts", ["user_id"])
    op.create_index("ix_studio_drafts_expires_at", "studio_drafts", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_studio_drafts_expires_at", table_name="studio_drafts")
    op.drop_index("ix_studio_drafts_user_id", table_name="studio_drafts")
    op.drop_table("studio_drafts")
