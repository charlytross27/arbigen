from datetime import datetime
from dataclasses import replace
from decimal import Decimal
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict

from app.core.config import get_settings
from app.modules.marketplace.domain import MarketplaceSearchError, MarketplaceSearchProvider, MarketplaceSearchResult


class ListingSignalsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class MarketplaceProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    price: Decimal | None
    currency: str | None
    permalink: str | None
    image_url: str | None
    signals: ListingSignalsRead


class MarketplaceSearchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: Literal["listings", "catalog"]
    site_id: str
    query: str
    fetched_at: datetime
    items: list[MarketplaceProductRead]
    reported_total_results: int | None = None


def search_marketplace(country: str, query: str, provider: MarketplaceSearchProvider) -> MarketplaceSearchResult:
    limit = get_settings().max_products_per_analysis
    try:
        snapshot: MarketplaceSearchResult = provider.search(
            country=country, query=query, limit=limit,
        )
    except MarketplaceSearchError as error:
        messages = {
            "not_configured": (503, "Configura el proveedor de búsqueda de productos en el backend."),
            "unsupported_country": (409, "La fuente de productos configurada no admite este país."),
            "invalid_token": (503, "El proveedor de productos no aceptó el token configurado."),
            "billing_required": (503, "El proveedor de extracción requiere crédito o habilitar facturación."),
            "forbidden": (503, "El proveedor de productos rechazó el acceso (403)."),
            "rate_limited": (503, "El proveedor de productos limitó las consultas. Inténtalo más tarde."),
            "network_error": (502, "No se pudo conectar con el proveedor de productos."),
            "upstream_timeout": (504, "La extracción de productos tardó demasiado. Inténtalo más tarde."),
            "upstream_error": (502, "El proveedor de productos no pudo responder a la consulta."),
            "invalid_response": (502, "El proveedor de productos devolvió una respuesta no válida."),
        }
        status_code, message = messages.get(error.code, (502, "No se pudo consultar Mercado Libre."))
        raise HTTPException(status_code=status_code, detail=message) from None
    return replace(snapshot, items=snapshot.items[:limit])
