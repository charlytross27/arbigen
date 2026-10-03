from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal, Protocol


@dataclass(frozen=True)
class ListingSignals:
    """Optional listing observations; None means the source did not report a value."""

    previous_price: Decimal | None = None
    free_shipping: bool | None = None
    official_store: bool | None = None
    international_purchase: bool | None = None
    stock_available: bool | None = None
    sold_quantity: int | None = None
    review_count: int | None = None
    rating: Decimal | None = None
    position: int | None = None
    seller_id: str | None = None
    brand: str | None = None
    category_id: str | None = None
    domain_id: str | None = None
    catalog_product_id: str | None = None
    variation_id: str | None = None


@dataclass(frozen=True)
class MarketplaceProduct:
    id: str
    title: str
    price: Decimal | None
    currency: str | None
    permalink: str | None
    image_url: str | None
    signals: ListingSignals = field(default_factory=ListingSignals)


@dataclass(frozen=True)
class MarketplaceSearchResult:
    source: Literal["listings", "catalog"]
    site_id: str
    query: str
    fetched_at: datetime
    items: list[MarketplaceProduct]
    reported_total_results: int | None = None


class MarketplaceSearchProvider(Protocol):
    def search(self, *, country: str, query: str, limit: int) -> MarketplaceSearchResult: ...


class MarketplaceSearchError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)
