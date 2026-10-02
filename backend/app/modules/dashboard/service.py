"""Lectura agregada por espacio, sin proveedores externos ni métricas inferidas."""

from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models import Analysis, MarketplaceSnapshot, Product, TrendPoint
from app.modules.analyses.service import find_workspace_user_id


class DashboardAnalysisRead(BaseModel):
    id: UUID
    query: str
    country: str
    category: str | None
    created_at: datetime
    prepared_at: datetime | None
    product_count: int
    trend_point_count: int


class DashboardActivityRead(BaseModel):
    analysis_id: UUID
    query: str
    country: str
    kind: Literal["analysis_saved", "products_prepared", "trends_imported"]
    occurred_at: datetime


class DashboardRead(BaseModel):
    period_days: Literal[7, 30]
    analysis_count: int
    prepared_count: int
    priced_product_count: int
    trends_count: int
    recent: list[DashboardAnalysisRead]
    activity: list[DashboardActivityRead]


def read_dashboard(session: Session, workspace_id: UUID, period_days: Literal[7, 30]) -> DashboardRead:
    user_id = find_workspace_user_id(session, workspace_id)
    if user_id is None:
        return DashboardRead(period_days=period_days, analysis_count=0, prepared_count=0,
                             priced_product_count=0, trends_count=0, recent=[], activity=[])
    cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)
    product_counts = (select(Product.analysis_id.label("analysis_id"), func.count(Product.id).label("count"))
                      .group_by(Product.analysis_id).subquery())
    trend_counts = (select(TrendPoint.analysis_id.label("analysis_id"), func.count(TrendPoint.id).label("count"))
                    .group_by(TrendPoint.analysis_id).subquery())
    totals = session.execute(
        select(func.count(Analysis.id), func.count(MarketplaceSnapshot.analysis_id),
               func.coalesce(func.sum(product_counts.c.count), 0), func.count(Analysis.trend_imported_at))
        .outerjoin(MarketplaceSnapshot, MarketplaceSnapshot.analysis_id == Analysis.id)
        .outerjoin(product_counts, product_counts.c.analysis_id == Analysis.id)
        .where(Analysis.user_id == user_id, Analysis.created_at >= cutoff)
    ).one()
    rows = session.execute(
        select(Analysis.id, Analysis.query, Analysis.country, Analysis.category, Analysis.created_at,
               MarketplaceSnapshot.prepared_at,
               func.coalesce(product_counts.c.count, 0), func.coalesce(trend_counts.c.count, 0))
        .outerjoin(MarketplaceSnapshot, MarketplaceSnapshot.analysis_id == Analysis.id)
        .outerjoin(product_counts, product_counts.c.analysis_id == Analysis.id)
        .outerjoin(trend_counts, trend_counts.c.analysis_id == Analysis.id)
        .where(Analysis.user_id == user_id, Analysis.created_at >= cutoff)
        .order_by(Analysis.created_at.desc(), Analysis.id.desc()).limit(5)
    ).all()
    recent = [DashboardAnalysisRead(
        id=row[0], query=row[1], country=row[2], category=row[3], created_at=row[4],
        prepared_at=row[5], product_count=row[6], trend_point_count=row[7],
    ) for row in rows]

    created = session.execute(
        select(Analysis.id, Analysis.query, Analysis.country, Analysis.created_at)
        .where(Analysis.user_id == user_id, Analysis.created_at >= cutoff)
        .order_by(Analysis.created_at.desc()).limit(6)
    ).all()
    prepared = session.execute(
        select(Analysis.id, Analysis.query, Analysis.country, MarketplaceSnapshot.prepared_at)
        .join(MarketplaceSnapshot, MarketplaceSnapshot.analysis_id == Analysis.id)
        .where(Analysis.user_id == user_id, MarketplaceSnapshot.prepared_at >= cutoff)
        .order_by(MarketplaceSnapshot.prepared_at.desc()).limit(6)
    ).all()
    imported = session.execute(
        select(Analysis.id, Analysis.query, Analysis.country, Analysis.trend_imported_at)
        .where(Analysis.user_id == user_id, Analysis.trend_imported_at >= cutoff)
        .order_by(Analysis.trend_imported_at.desc()).limit(6)
    ).all()
    activity = [DashboardActivityRead(analysis_id=row[0], query=row[1], country=row[2],
                                      kind=kind, occurred_at=row[3])
                for kind, records in (("analysis_saved", created), ("products_prepared", prepared),
                                      ("trends_imported", imported)) for row in records]
    activity.sort(key=lambda item: item.occurred_at, reverse=True)
    return DashboardRead(period_days=period_days, analysis_count=totals[0], prepared_count=totals[1],
                         priced_product_count=totals[2], trends_count=totals[3], recent=recent,
                         activity=activity[:6])
