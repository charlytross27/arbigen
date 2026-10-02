from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True)
class ClusterExample:
    external_id: str
    title: str
    price: Decimal


@dataclass(frozen=True)
class ClusterSegment:
    number: int
    label: str
    count: int
    share_pct: Decimal
    price_min: Decimal
    price_max: Decimal
    price_mean: Decimal
    price_median: Decimal
    material_hints: dict[str, int]
    examples: tuple[ClusterExample, ...]


@dataclass(frozen=True)
class ClusterReport:
    country: str
    currency: str
    status: Literal["ready", "insufficient_data", "no_separation"]
    product_count: int
    clustered_count: int
    excluded_outlier_count: int
    selected_k: int | None
    silhouette: Decimal | None
    segments: tuple[ClusterSegment, ...]
    reason: str | None
