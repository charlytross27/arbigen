from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal, Protocol


@dataclass(frozen=True)
class MarketplaceProduct:
    id: str
    title: str
    price: Decimal | None
    currency: str | None
    permalink: str | None
    image_url: str | None


@dataclass(frozen=True)
class MarketplaceSearchResult:
    source: Literal["listings", "catalog"]
    site_id: str
    query: str
    fetched_at: datetime
    items: list[MarketplaceProduct]


class MarketplaceSearchProvider(Protocol):
    def search(self, *, country: str, query: str, limit: int) -> MarketplaceSearchResult: ...


class MarketplaceSearchError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)
