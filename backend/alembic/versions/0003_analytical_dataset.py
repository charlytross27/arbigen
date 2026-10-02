"""Separate normalized marketplace input from cleaned analytical products.

Revision ID: 0003_analytical_dataset
Revises: 0002_trends_csv
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_analytical_dataset"
down_revision = "0002_trends_csv"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("permalink", sa.Text(), nullable=True))
    op.create_table(
        "marketplace_snapshots",
        sa.Column("analysis_id", sa.UUID(), nullable=False),
        sa.Column("source", sa.String(24), nullable=False),
        sa.Column("site_id", sa.String(8), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("prepared_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_products", postgresql.JSONB(), nullable=False),
        sa.Column("quality", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], name=op.f("fk_marketplace_snapshots_analysis_id_analyses"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("analysis_id", name=op.f("pk_marketplace_snapshots")),
    )


def downgrade() -> None:
    op.drop_table("marketplace_snapshots")
    op.drop_column("products", "permalink")
