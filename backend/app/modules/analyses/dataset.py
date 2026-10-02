"""Persistencia RAW normalizada y vista analítica de un análisis guardado."""

from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database.models import Analysis, MarketplaceSnapshot, Product, TrendPoint
from app.modules.analyses.marketplace import MarketplaceSearchRead, search_marketplace
from app.modules.analyses.trends import TrendPointRead
from app.modules.etl.pipeline import prepare_dataset, prepare_trends
from app.modules.etl.domain import AnalyticalProduct
from app.modules.marketplace.domain import MarketplaceProduct, MarketplaceSearchProvider, MarketplaceSearchResult
from app.modules.trends.domain import TrendObservation


class ProductQualityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_count: int
    duplicate_count: int
    missing_title_count: int
    missing_price_count: int
    invalid_price_count: int
    invalid_currency_count: int
    included_count: int


class AnalyticalProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_id: str | None
    title: str
    price: Decimal
    currency: str
    permalink: str | None
    image_url: str | None
    attributes: dict[str, str]


class DatasetRead(BaseModel):
    country: str
    trend_source: str | None
    trend_imported_at: datetime | None
    snapshot: MarketplaceSearchRead | None
    prepared_at: datetime | None
    quality: ProductQualityRead | None
    products: list[AnalyticalProductRead]
    trends: list[TrendPointRead]


def analytical_products(dataset: DatasetRead) -> list[AnalyticalProduct]:
    """Convierte la lectura persistida al contrato compartido del pipeline."""
    return [AnalyticalProduct(
        external_id=product.external_id or product.id.hex,
        title=product.title, price=product.price, currency=product.currency,
        permalink=product.permalink, image_url=product.image_url,
        attributes=dict(product.attributes),
    ) for product in dataset.products]


def _raw_product(product: MarketplaceProduct) -> dict:
    return {
        "id": product.id, "title": product.title,
        "price": str(product.price) if product.price is not None else None,
        "currency": product.currency, "permalink": product.permalink, "image_url": product.image_url,
    }


def _market_product(raw: dict) -> MarketplaceProduct:
    return MarketplaceProduct(
        id=raw["id"], title=raw["title"],
        price=Decimal(raw["price"]) if raw["price"] is not None else None,
        currency=raw["currency"], permalink=raw["permalink"], image_url=raw["image_url"],
    )


def _trends(session: Session, analysis_id: UUID) -> list[TrendObservation]:
    rows = session.scalars(select(TrendPoint).where(TrendPoint.analysis_id == analysis_id).order_by(TrendPoint.date)).all()
    return [TrendObservation(row.date, row.value, row.less_than_one) for row in rows]


def read_dataset(session: Session, analysis: Analysis) -> DatasetRead:
    snapshot = session.get(MarketplaceSnapshot, analysis.id)
    rows = session.scalars(select(Product).where(Product.analysis_id == analysis.id).order_by(Product.price, Product.id)).all()
    trends = prepare_trends(_trends(session, analysis.id))
    return DatasetRead(
        country=analysis.country,
        trend_source=analysis.trend_source,
        trend_imported_at=analysis.trend_imported_at,
        snapshot=MarketplaceSearchRead(
            source=snapshot.source, site_id=snapshot.site_id, query=analysis.query,
            fetched_at=snapshot.fetched_at,
            items=[_market_product(raw) for raw in snapshot.raw_products],
        ) if snapshot else None,
        prepared_at=snapshot.prepared_at if snapshot else None,
        quality=ProductQualityRead.model_validate(snapshot.quality) if snapshot else None,
        products=[AnalyticalProductRead(
            id=row.id, external_id=row.external_id, title=row.title, price=row.price,
            currency=row.currency, permalink=row.permalink, image_url=row.image_url,
            attributes=row.attributes_json,
        ) for row in rows],
        trends=[TrendPointRead(date=point.date, value=point.value, less_than_one=point.less_than_one) for point in trends],
    )


def _persist_dataset(session: Session, analysis: Analysis, snapshot: MarketplaceSearchResult) -> DatasetRead:
    prepared = prepare_dataset(country=analysis.country, products=snapshot.items, trends=_trends(session, analysis.id))
    record = session.get(MarketplaceSnapshot, analysis.id)
    if record is None:
        record = MarketplaceSnapshot(analysis_id=analysis.id)
        session.add(record)
    record.source = snapshot.source
    record.site_id = snapshot.site_id
    record.fetched_at = snapshot.fetched_at
    record.prepared_at = datetime.now(timezone.utc)
    record.raw_products = [_raw_product(product) for product in snapshot.items]
    record.quality = asdict(prepared.product_quality)
    session.execute(delete(Product).where(Product.analysis_id == analysis.id))
    session.add_all(Product(
        analysis_id=analysis.id, external_id=product.external_id, title=product.title,
        price=product.price, currency=product.currency, permalink=product.permalink,
        image_url=product.image_url, attributes_json=product.attributes,
    ) for product in prepared.products)
    session.commit()
    return read_dataset(session, analysis)


def refresh_dataset(session: Session, analysis: Analysis, provider: MarketplaceSearchProvider) -> DatasetRead:
    snapshot = search_marketplace(analysis.country, analysis.query, provider)
    return _persist_dataset(session, analysis, snapshot)


def reprocess_dataset(session: Session, analysis: Analysis) -> DatasetRead:
    record = session.get(MarketplaceSnapshot, analysis.id)
    if record is None:
        raise HTTPException(status_code=409, detail="Primero prepara una muestra de productos para este análisis.")
    snapshot = MarketplaceSearchResult(
        source=record.source, site_id=record.site_id, query=analysis.query,
        fetched_at=record.fetched_at, items=[_market_product(raw) for raw in record.raw_products],
    )
    return _persist_dataset(session, analysis, snapshot)
