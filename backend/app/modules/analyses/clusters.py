"""Lectura de segmentos calculados desde productos guardados, sin proveedor externo."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database.models import Analysis
from app.modules.analyses.dataset import analytical_products, read_dataset
from app.modules.clustering.model import MODEL_VERSION, cluster_products


class ClusterExampleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    external_id: str
    title: str
    price: Decimal


class ClusterSegmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    number: int
    label: str
    count: int
    share_pct: Decimal
    price_min: Decimal
    price_max: Decimal
    price_mean: Decimal
    price_median: Decimal
    material_hints: dict[str, int]
    examples: list[ClusterExampleRead]


class ClusterReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    model_version: str
    country: str
    currency: str
    status: Literal["ready", "insufficient_data", "no_separation"]
    product_count: int
    clustered_count: int
    excluded_outlier_count: int
    selected_k: int | None
    silhouette: Decimal | None
    segments: list[ClusterSegmentRead]
    reason: str | None


def read_clusters(session: Session, analysis: Analysis) -> ClusterReportRead:
    report = cluster_products(country=analysis.country, products=analytical_products(read_dataset(session, analysis)))
    return ClusterReportRead(model_version=MODEL_VERSION, **report.__dict__)
