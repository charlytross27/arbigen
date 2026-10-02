from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models import Analysis
from app.modules.analyses.schemas import AnalysisCreate


def create_analysis(session: Session, user_id: UUID, payload: AnalysisCreate) -> Analysis:
    analysis = Analysis(
        user_id=user_id,
        query=payload.query,
        country=payload.country,
        category=payload.category,
        period_months=payload.period_months,
        status="saved",
    )
    session.add(analysis)
    session.commit()
    session.refresh(analysis)
    return analysis


def list_analyses(session: Session, user_id: UUID, limit: int, offset: int) -> tuple[list[Analysis], int]:
    where = Analysis.user_id == user_id
    total = session.scalar(select(func.count()).select_from(Analysis).where(where)) or 0
    items = list(session.scalars(
        select(Analysis).where(where).order_by(Analysis.created_at.desc(), Analysis.id.desc()).limit(limit).offset(offset)
    ))
    return items, total


def get_analysis(session: Session, user_id: UUID, analysis_id: UUID) -> Analysis | None:
    return session.scalar(select(Analysis).where(Analysis.id == analysis_id, Analysis.user_id == user_id))
