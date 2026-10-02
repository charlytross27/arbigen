from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class TrendObservation:
    date: date
    value: Decimal | None
    less_than_one: bool = False


@dataclass(frozen=True)
class TrendSeries:
    source: str
    points: tuple[TrendObservation, ...]


class TrendsInputError(ValueError):
    pass


class TrendsProvider(Protocol):
    def load(self, *, query: str, country: str, payload: bytes) -> TrendSeries: ...
