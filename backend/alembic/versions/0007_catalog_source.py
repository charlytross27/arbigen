"""Keep a verified research/product reference for catalogs made from an analysis.

Revision ID: 0007_catalog_source
Revises: 0006_catalog_image_metadata
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_catalog_source"
down_revision = "0006_catalog_image_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("source_analysis_id", sa.UUID(), nullable=True))
    op.add_column("campaigns", sa.Column("source_product_id", sa.UUID(), nullable=True))
    op.add_column("campaigns", sa.Column("source_product_title", sa.String(300), nullable=True))
    op.create_index("ix_campaigns_source_analysis_id", "campaigns", ["source_analysis_id"])
    op.create_foreign_key("fk_campaigns_source_analysis_id_analyses", "campaigns", "analyses", ["source_analysis_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_campaigns_source_product_id_products", "campaigns", "products", ["source_product_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_campaigns_source_product_id_products", "campaigns", type_="foreignkey")
    op.drop_constraint("fk_campaigns_source_analysis_id_analyses", "campaigns", type_="foreignkey")
    op.drop_index("ix_campaigns_source_analysis_id", table_name="campaigns")
    op.drop_column("campaigns", "source_product_title")
    op.drop_column("campaigns", "source_product_id")
    op.drop_column("campaigns", "source_analysis_id")
