"""Lectura de variables a partir del dataset persistido, sin I/O externo."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database.models import Analysis
from app.modules.analyses.dataset import analytical_products, read_dataset
from app.modules.etl.domain import AnalyticalTrendPoint
from app.modules.features.engineering import calculate_features


class MarketFeaturesRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    currency: str
    source_count: int | None
    priced_count: int
    price_coverage_pct: Decimal | None
    price_min: Decimal | None
    price_max: Decimal | None
    price_mean: Decimal | None
    price_median: Decimal | None
    price_stddev: Decimal | None
    material_hints: dict[str, int]


class TrendFeaturesRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    point_count: int
    observed_count: int
    censored_count: int
    observed_coverage_pct: Decimal | None
    mean_index: Decimal | None
    volatility_index: Decimal | None
    moving_average_3: Decimal | None
    growth_3v3_pct: Decimal | None
    momentum_3v3: Decimal | None
    acceleration_3v3: Decimal | None


class FeatureReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    country: str
    market: MarketFeaturesRead
    trend: TrendFeaturesRead


def read_features(session: Session, analysis: Analysis) -> FeatureReportRead:
    dataset = read_dataset(session, analysis)
    products = analytical_products(dataset)
    trends = [AnalyticalTrendPoint(point.date, point.value, point.less_than_one) for point in dataset.trends]
    report = calculate_features(
        country=analysis.country, products=products, trends=trends,
        source_count=dataset.quality.source_count if dataset.quality else None,
    )
    return FeatureReportRead.model_validate(report)
