from typing import Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.modules.auth.router import current_user_id
from app.modules.dashboard.service import DashboardRead, read_dashboard


router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardRead)
def get_dashboard(
    days: int = Query(default=30),
    user_id: UUID = Depends(current_user_id),
    session: Session = Depends(get_session),
) -> DashboardRead:
    if days not in (7, 30):
        raise HTTPException(status_code=422, detail="El periodo debe ser de 7 o 30 días.")
    return read_dashboard(session, user_id, cast(Literal[7, 30], days))
