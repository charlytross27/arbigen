from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.modules.auth.router import current_user_id
from app.integrations.marketplace_search import get_marketplace_search_provider
from app.integrations.google_trends.csv_provider import MAX_CSV_BYTES
from app.integrations.trends import get_trends_provider
from app.modules.analyses.dataset import DatasetRead, read_dataset, refresh_dataset, reprocess_dataset
from app.modules.analyses.features import FeatureReportRead, read_features
from app.modules.analyses.clusters import ClusterReportRead, read_clusters
from app.modules.analyses.forecast import ForecastReportRead, read_forecast
from app.modules.analyses.scoring import ScorePreviewRequest, ScoreReportRead, read_score
from app.modules.analyses.trends import TrendsRead, read_trends, replace_trends
from app.modules.analyses.schemas import AnalysisCreate, AnalysisList, AnalysisRead
from app.modules.analyses.service import create_analysis, get_analysis, list_analyses
from app.modules.marketplace.domain import MarketplaceSearchProvider
from app.modules.trends.domain import TrendsInputError, TrendsProvider


router = APIRouter(prefix="/api/v1/analyses", tags=["analyses"])


@router.post("", response_model=AnalysisRead, status_code=status.HTTP_201_CREATED)
def post_analysis(
    payload: AnalysisCreate,
    user_id: UUID = Depends(current_user_id),
    session: Session = Depends(get_session),
) -> AnalysisRead:
    return AnalysisRead.model_validate(create_analysis(session, user_id, payload))


@router.get("", response_model=AnalysisList)
def get_analyses(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: UUID = Depends(current_user_id),
    session: Session = Depends(get_session),
) -> AnalysisList:
    items, total = list_analyses(session, user_id, limit, offset)
    return AnalysisList(items=[AnalysisRead.model_validate(item) for item in items], total=total, limit=limit, offset=offset)


@router.get("/{analysis_id}", response_model=AnalysisRead)
def get_analysis_detail(
    analysis_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: Session = Depends(get_session),
) -> AnalysisRead:
    analysis = get_analysis(session, user_id, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Análisis no encontrado.")
    return AnalysisRead.model_validate(analysis)


@router.get("/{analysis_id}/dataset", response_model=DatasetRead)
def get_dataset(
    analysis_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: Session = Depends(get_session),
) -> DatasetRead:
    analysis = get_analysis(session, user_id, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Análisis no encontrado.")
    return read_dataset(session, analysis)


@router.get("/{analysis_id}/features", response_model=FeatureReportRead)
def get_features(
    analysis_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: Session = Depends(get_session),
) -> FeatureReportRead:
    analysis = get_analysis(session, user_id, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Análisis no encontrado.")
    return read_features(session, analysis)


@router.get("/{analysis_id}/clusters", response_model=ClusterReportRead)
def get_clusters(
    analysis_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: Session = Depends(get_session),
) -> ClusterReportRead:
    analysis = get_analysis(session, user_id, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Análisis no encontrado.")
    return read_clusters(session, analysis)


@router.get("/{analysis_id}/forecast", response_model=ForecastReportRead)
def get_forecast(
    analysis_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: Session = Depends(get_session),
) -> ForecastReportRead:
    analysis = get_analysis(session, user_id, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Análisis no encontrado.")
    return read_forecast(session, analysis)


@router.get("/{analysis_id}/opportunity-score", response_model=ScoreReportRead)
def get_opportunity_score(
    analysis_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: Session = Depends(get_session),
) -> ScoreReportRead:
    analysis = get_analysis(session, user_id, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Análisis no encontrado.")
    return read_score(session, analysis)


@router.post("/{analysis_id}/opportunity-score/preview", response_model=ScoreReportRead)
def post_opportunity_score_preview(
    analysis_id: UUID,
    payload: ScorePreviewRequest,
    user_id: UUID = Depends(current_user_id),
    session: Session = Depends(get_session),
) -> ScoreReportRead:
    analysis = get_analysis(session, user_id, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Análisis no encontrado.")
    return read_score(session, analysis, payload)


@router.post("/{analysis_id}/dataset/refresh", response_model=DatasetRead)
def post_dataset_refresh(
    analysis_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: Session = Depends(get_session),
    provider: MarketplaceSearchProvider = Depends(get_marketplace_search_provider),
) -> DatasetRead:
    analysis = get_analysis(session, user_id, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Análisis no encontrado.")
    return refresh_dataset(session, analysis, provider)


@router.post("/{analysis_id}/dataset/reprocess", response_model=DatasetRead)
def post_dataset_reprocess(
    analysis_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: Session = Depends(get_session),
) -> DatasetRead:
    analysis = get_analysis(session, user_id, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Análisis no encontrado.")
    return reprocess_dataset(session, analysis)


@router.get("/{analysis_id}/trends", response_model=TrendsRead)
def get_trends(
    analysis_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: Session = Depends(get_session),
) -> TrendsRead:
    analysis = get_analysis(session, user_id, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Análisis no encontrado.")
    return read_trends(session, analysis)


@router.post("/{analysis_id}/trends", response_model=TrendsRead)
async def import_trends_csv(
    analysis_id: UUID,
    request: Request,
    user_id: UUID = Depends(current_user_id),
    session: Session = Depends(get_session),
    provider: TrendsProvider = Depends(get_trends_provider),
) -> TrendsRead:
    analysis = get_analysis(session, user_id, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Análisis no encontrado.")
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() not in {"text/csv", "application/csv"}:
        raise HTTPException(status_code=415, detail="Envía un archivo CSV de Google Trends.")
    payload = bytearray()
    async for chunk in request.stream():
        payload.extend(chunk)
        if len(payload) > MAX_CSV_BYTES:
            raise HTTPException(status_code=413, detail="El CSV no debe superar 256 KB.")
    try:
        series = provider.load(query=analysis.query, country=analysis.country, payload=bytes(payload))
    except TrendsInputError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return replace_trends(session, analysis, series)
