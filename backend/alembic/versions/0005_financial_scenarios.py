"""Persist one product-backed financial scenario per saved analysis.

Revision ID: 0005_financial_scenarios
Revises: 0004_auth_sessions
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_financial_scenarios"
down_revision = "0004_auth_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "financial_scenarios",
        sa.Column("analysis_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=True),
        sa.Column("product_external_id", sa.String(160), nullable=True),
        sa.Column("product_title", sa.String(300), nullable=False),
        sa.Column("reference_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("sale_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("product_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("shipping_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("commission_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("other_costs", sa.Numeric(12, 2), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("reference_price >= 0", name=op.f("ck_financial_scenarios_scenario_reference_price_nonnegative")),
        sa.CheckConstraint("sale_price >= 0 AND product_cost >= 0 AND shipping_cost >= 0 AND other_costs >= 0", name=op.f("ck_financial_scenarios_scenario_costs_nonnegative")),
        sa.CheckConstraint("commission_pct BETWEEN 0 AND 100", name=op.f("ck_financial_scenarios_scenario_commission_range")),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], name=op.f("fk_financial_scenarios_analysis_id_analyses"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name=op.f("fk_financial_scenarios_product_id_products"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("analysis_id", name=op.f("pk_financial_scenarios")),
    )


def downgrade() -> None:
    op.drop_table("financial_scenarios")
