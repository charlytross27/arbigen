"""Pronóstico bajo demanda desde la serie de Trends persistida."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database.models import Analysis
from app.modules.analyses.trends import read_trends
from app.modules.etl.domain import AnalyticalTrendPoint
from app.modules.forecasting.model import MODEL_VERSION, forecast_trends


class ForecastPointRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    value: Decimal
    lower: Decimal
    upper: Decimal


class ForecastReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    model_version: str
    status: Literal["ready", "insufficient_data", "censored_data", "irregular_series", "low_skill"]
    source_point_count: int
    used_point_count: int
    censored_count: int
    frequency: Literal["daily", "weekly", "monthly"] | None
    selected_model: Literal["naive", "moving_average_3", "drift", "seasonal_naive"] | None
    direction: Literal["creciente", "estable", "decreciente"] | None
    seasonal_signal: bool
    backtest_mae: Decimal | None
    naive_mae: Decimal | None
    candidate_mae: dict[str, Decimal]
    backtest_origins: int
    horizon: int
    predictions: list[ForecastPointRead]
    reason: str | None


def read_forecast(session: Session, analysis: Analysis) -> ForecastReportRead:
    trends = read_trends(session, analysis)
    points = [AnalyticalTrendPoint(point.date, point.value, point.less_than_one) for point in trends.points]
    report = forecast_trends(points)
    return ForecastReportRead(model_version=MODEL_VERSION, **report.__dict__)
