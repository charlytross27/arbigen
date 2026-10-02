"""Entidades persistentes de cuentas, investigaciones y datos analíticos."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


def uuid_id() -> Mapped[UUID]:
    # La anotación de retorno ayuda a reutilizar el tipo en cada modelo.
    return mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))


def created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = uuid_id()
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    csrf_token: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = created_at()


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[UUID] = uuid_id()
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    query: Mapped[str] = mapped_column(String(200), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    category: Mapped[str | None] = mapped_column(String(120))
    period_months: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="pending")
    trend_source: Mapped[str | None] = mapped_column(String(40))
    trend_imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()

    __table_args__ = (CheckConstraint("period_months > 0", name="period_positive"),)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[UUID] = uuid_id()
    analysis_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(160))
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text)
    permalink: Mapped[str | None] = mapped_column(Text)
    attributes_json: Mapped[dict] = mapped_column("attributes", JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))

    __table_args__ = (CheckConstraint("price >= 0", name="price_nonnegative"),)


class MarketplaceSnapshot(Base):
    """Última muestra normalizada de la fuente, anterior a las reglas ETL."""

    __tablename__ = "marketplace_snapshots"

    analysis_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), primary_key=True)
    source: Mapped[str] = mapped_column(String(24), nullable=False)
    site_id: Mapped[str] = mapped_column(String(8), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    prepared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_products: Mapped[list] = mapped_column(JSONB, nullable=False)
    quality: Mapped[dict] = mapped_column(JSONB, nullable=False)


class TrendPoint(Base):
    __tablename__ = "trend_points"

    id: Mapped[UUID] = uuid_id()
    analysis_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    less_than_one: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    __table_args__ = (UniqueConstraint("analysis_id", "date", name="uq_trend_points_analysis_date"),)


class Cluster(Base):
    __tablename__ = "clusters"

    id: Mapped[UUID] = uuid_id()
    analysis_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    cluster_number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (UniqueConstraint("analysis_id", "cluster_number", name="uq_clusters_analysis_number"),)


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[UUID] = uuid_id()
    analysis_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    cluster_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("clusters.id", ondelete="SET NULL"), index=True)
    opportunity_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    estimated_roi: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    estimated_margin: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    competition_level: Mapped[str | None] = mapped_column(String(32))
    trend_type: Mapped[str | None] = mapped_column(String(32))

    __table_args__ = (CheckConstraint("opportunity_score BETWEEN 0 AND 100", name="score_range"),)


class FinancialScenario(Base):
    """Una hipótesis financiera guardada por investigación; no contiene ventas estimadas."""

    __tablename__ = "financial_scenarios"

    analysis_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), primary_key=True)
    product_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"))
    product_external_id: Mapped[str | None] = mapped_column(String(160))
    product_title: Mapped[str] = mapped_column(String(300), nullable=False)
    reference_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    sale_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    product_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    shipping_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    commission_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    other_costs: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("reference_price >= 0", name="scenario_reference_price_nonnegative"),
        CheckConstraint("sale_price >= 0 AND product_cost >= 0 AND shipping_cost >= 0 AND other_costs >= 0", name="scenario_costs_nonnegative"),
        CheckConstraint("commission_pct BETWEEN 0 AND 100", name="scenario_commission_range"),
    )


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[UUID] = uuid_id()
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    opportunity_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="SET NULL"), index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    product_name: Mapped[str] = mapped_column(String(160), nullable=False)
    product_description: Mapped[str | None] = mapped_column(Text)
    style: Mapped[str] = mapped_column(String(40), nullable=False)
    scene: Mapped[str] = mapped_column(String(300), nullable=False)
    lighting: Mapped[str] = mapped_column(String(40), nullable=False)
    aspect_ratio: Mapped[str] = mapped_column(String(8), nullable=False)
    original_image_url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="draft")
    created_at: Mapped[datetime] = created_at()


class GeneratedAsset(Base):
    __tablename__ = "generated_assets"

    id: Mapped[UUID] = uuid_id()
    campaign_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = created_at()
