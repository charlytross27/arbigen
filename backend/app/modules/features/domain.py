from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class MarketFeatures:
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


@dataclass(frozen=True)
class TrendFeatures:
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


@dataclass(frozen=True)
class FeatureReport:
    country: str
    market: MarketFeatures
    trend: TrendFeatures
