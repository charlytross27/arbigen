from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.modules.marketplace.domain import ListingSignals


@dataclass(frozen=True)
class AnalyticalProduct:
    external_id: str
    title: str
    price: Decimal
    currency: str
    permalink: str | None
    image_url: str | None
    attributes: dict[str, str]
    signals: ListingSignals = field(default_factory=ListingSignals)


@dataclass(frozen=True)
class AnalyticalTrendPoint:
    date: date
    value: Decimal | None
    less_than_one: bool


@dataclass(frozen=True)
class ProductQuality:
    source_count: int
    duplicate_count: int
    missing_title_count: int
    missing_price_count: int
    invalid_price_count: int
    invalid_currency_count: int
    included_count: int


@dataclass(frozen=True)
class PreparedDataset:
    products: tuple[AnalyticalProduct, ...]
    trends: tuple[AnalyticalTrendPoint, ...]
    product_quality: ProductQuality
