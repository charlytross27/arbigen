"""Record source image metadata for account-owned visual campaigns.

Revision ID: 0006_catalog_image_metadata
Revises: 0005_financial_scenarios
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_catalog_image_metadata"
down_revision = "0005_financial_scenarios"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("original_image_name", sa.String(160), nullable=False, server_default="Fotografía original"))
    op.add_column("campaigns", sa.Column("original_image_content_type", sa.String(32), nullable=False, server_default="image/png"))
    op.add_column("campaigns", sa.Column("variations", sa.Integer(), nullable=False, server_default="1"))
    op.create_check_constraint("ck_campaigns_variations_range", "campaigns", "variations BETWEEN 1 AND 4")


def downgrade() -> None:
    op.drop_constraint("ck_campaigns_variations_range", "campaigns", type_="check")
    op.drop_column("campaigns", "variations")
    op.drop_column("campaigns", "original_image_content_type")
    op.drop_column("campaigns", "original_image_name")
