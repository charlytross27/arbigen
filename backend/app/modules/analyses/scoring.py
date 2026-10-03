"""Adaptador HTTP para el cálculo puro sobre datos ya persistidos."""

from dataclasses import asdict
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from app.database.models import Analysis, FinancialScenario
from app.modules.analyses.dataset import analytical_products, read_dataset
from app.modules.etl.domain import AnalyticalTrendPoint
from app.modules.features.engineering import calculate_features
from app.modules.forecasting.model import forecast_trends
from app.modules.scoring.model import FinancialAssumptions, ScoreWeights, calculate_score


class FinancialInputsRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sale_price: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    product_cost: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    shipping_cost: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    commission_pct: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    other_costs: Decimal = Field(ge=0, max_digits=15, decimal_places=2)


class ScoreWeightsRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    growth: Decimal = Field(default=Decimal("0.25"), ge=0, le=1)
    stability: Decimal = Field(default=Decimal("0.15"), ge=0, le=1)
    margin: Decimal = Field(default=Decimal("0.35"), ge=0, le=1)
    roi: Decimal = Field(default=Decimal("0.25"), ge=0, le=1)

    @model_validator(mode="after")
    def sum_to_one(self) -> "ScoreWeightsRead":
        if self.growth + self.stability + self.margin + self.roi != 1:
            raise ValueError("Los pesos deben sumar exactamente 1.")
        return self


class ScorePreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    financial: FinancialInputsRead
    weights: ScoreWeightsRead = Field(default_factory=ScoreWeightsRead)


class ScoreReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    model_version: str
    status: Literal["ready", "incomplete"]
    score: Decimal | None
    currency: str
    weights: ScoreWeightsRead
    components: dict[str, Decimal | None]
    missing: list[str]
    warnings: list[str]
    limitations: list[str]
    evidence: "ScoreEvidenceRead"
    sensitivity: list["ScoreSensitivityRead"]
    commission_cost: Decimal | None
    total_cost: Decimal | None
    unit_profit: Decimal | None
    margin_pct: Decimal | None
    roi_pct: Decimal | None


class ScoreEvidenceRead(BaseModel):
    product_count: int
    source_count: int | None
    price_coverage_pct: Decimal | None
    trend_point_count: int
    trend_observed_count: int
    trend_source: str | None
    trend_last_date: date | None
    market_fetched_date: date | None
    forecast_mae: Decimal | None
    forecast_naive_mae: Decimal | None
    forecast_backtest_origins: int


class ScoreSensitivityRead(BaseModel):
    case: Literal["price_down_10pct", "fixed_costs_up_10pct"]
    sale_price: Decimal
    unit_profit: Decimal
    score: Decimal | None


def read_score(session: Session, analysis: Analysis, payload: ScorePreviewRequest | None = None) -> ScoreReportRead:
    dataset = read_dataset(session, analysis)
    trends = [AnalyticalTrendPoint(point.date, point.value, point.less_than_one) for point in dataset.trends]
    features = calculate_features(
        country=analysis.country, products=analytical_products(dataset), trends=trends,
        source_count=dataset.quality.source_count if dataset.quality else None,
    )
    forecast = forecast_trends(trends)
    saved = session.get(FinancialScenario, analysis.id) if payload is None else None
    financial = (FinancialAssumptions(**payload.financial.model_dump()) if payload else
                 FinancialAssumptions(saved.sale_price, saved.product_cost, saved.shipping_cost,
                                      saved.commission_pct, saved.other_costs) if saved else None)
    weights = ScoreWeights(**payload.weights.model_dump()) if payload else None
    return ScoreReportRead.model_validate(asdict(calculate_score(
        features=features, forecast=forecast, assumptions=financial, weights=weights,
        trend_source=dataset.trend_source,
        trend_last_date=trends[-1].date if trends else None,
        market_fetched_date=dataset.snapshot.fetched_at.date() if dataset.snapshot else None,
        as_of=date.today(),
    )))
