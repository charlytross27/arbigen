"""Persist imported Google Trends interest and censored values.

Revision ID: 0002_trends_csv
Revises: 0001_initial
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_trends_csv"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("analyses", sa.Column("trend_source", sa.String(40), nullable=True))
    op.add_column("analyses", sa.Column("trend_imported_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("trend_points", "value", existing_type=sa.Numeric(12, 4), nullable=True)
    op.add_column("trend_points", sa.Column("less_than_one", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.create_check_constraint("ck_trend_points_value", "trend_points", "(less_than_one AND value IS NULL) OR (NOT less_than_one AND value BETWEEN 0 AND 100)")


def downgrade() -> None:
    if op.get_bind().execute(sa.text("SELECT EXISTS (SELECT 1 FROM trend_points WHERE less_than_one)")).scalar():
        raise RuntimeError("No se puede revertir: existen valores de Trends <1 que el esquema anterior no representa.")
    op.drop_constraint("ck_trend_points_value", "trend_points", type_="check")
    op.alter_column("trend_points", "value", existing_type=sa.Numeric(12, 4), nullable=False)
    op.drop_column("trend_points", "less_than_one")
    op.drop_column("analyses", "trend_imported_at")
    op.drop_column("analyses", "trend_source")
