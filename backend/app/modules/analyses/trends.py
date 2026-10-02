from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database.models import Analysis, TrendPoint
from app.modules.trends.domain import TrendSeries


class TrendPointRead(BaseModel):
    date: date
    value: Decimal | None
    less_than_one: bool


class TrendsRead(BaseModel):
    source: str | None
    imported_at: datetime | None
    points: list[TrendPointRead]


def read_trends(session: Session, analysis: Analysis) -> TrendsRead:
    rows = session.scalars(select(TrendPoint).where(TrendPoint.analysis_id == analysis.id).order_by(TrendPoint.date)).all()
    return TrendsRead(
        source=analysis.trend_source,
        imported_at=analysis.trend_imported_at,
        points=[TrendPointRead(date=row.date, value=row.value, less_than_one=row.less_than_one) for row in rows],
    )


def replace_trends(session: Session, analysis: Analysis, series: TrendSeries) -> TrendsRead:
    session.execute(delete(TrendPoint).where(TrendPoint.analysis_id == analysis.id))
    session.add_all(TrendPoint(analysis_id=analysis.id, date=point.date, value=point.value, less_than_one=point.less_than_one) for point in series.points)
    analysis.trend_source = series.source
    analysis.trend_imported_at = datetime.now(timezone.utc)
    session.commit()
    return read_trends(session, analysis)
