from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database.models import Analysis, User
from app.modules.analyses.schemas import AnalysisCreate


def _workspace_email(workspace_id: UUID) -> str:
    # Identidad demo por navegador, sin correo real ni autenticación.
    return f"demo-{workspace_id}@workspace.arbigen.invalid"


def find_workspace_user_id(session: Session, workspace_id: UUID) -> UUID | None:
    return session.scalar(select(User.id).where(User.email == _workspace_email(workspace_id)))


def _get_or_create_workspace_user(session: Session, workspace_id: UUID) -> UUID:
    email = _workspace_email(workspace_id)
    user_id = session.scalar(
        insert(User)
        .values(email=email, name="Espacio demo")
        .on_conflict_do_nothing(index_elements=[User.email])
        .returning(User.id)
    )
    if user_id is not None:
        return user_id
    existing = find_workspace_user_id(session, workspace_id)
    if existing is None:
        raise RuntimeError("No se pudo recuperar el espacio demo.")
    return existing


def create_analysis(session: Session, workspace_id: UUID, payload: AnalysisCreate) -> Analysis:
    user_id = _get_or_create_workspace_user(session, workspace_id)
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


def list_analyses(session: Session, workspace_id: UUID, limit: int, offset: int) -> tuple[list[Analysis], int]:
    user_id = find_workspace_user_id(session, workspace_id)
    if user_id is None:
        return [], 0
    where = Analysis.user_id == user_id
    total = session.scalar(select(func.count()).select_from(Analysis).where(where)) or 0
    items = list(session.scalars(
        select(Analysis).where(where).order_by(Analysis.created_at.desc(), Analysis.id.desc()).limit(limit).offset(offset)
    ))
    return items, total


def get_analysis(session: Session, workspace_id: UUID, analysis_id: UUID) -> Analysis | None:
    user_id = find_workspace_user_id(session, workspace_id)
    if user_id is None:
        return None
    return session.scalar(select(Analysis).where(Analysis.id == analysis_id, Analysis.user_id == user_id))
