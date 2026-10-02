from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True)
class ForecastPoint:
    date: date
    value: Decimal
    lower: Decimal
    upper: Decimal


@dataclass(frozen=True)
class ForecastReport:
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
    predictions: tuple[ForecastPoint, ...]
    reason: str | None
