from decimal import Decimal

import httpx
import pytest
from app.integrations.mercado_libre.provider import (
    MercadoLibreHttpProvider,
)
from app.modules.marketplace.domain import MarketplaceSearchError


def test_provider_maps_country_and_normalizes_current_listings() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/sites/MLM/search"
        assert request.url.params["q"] == "anillos de plata"
        assert request.url.params["limit"] == "12"
        assert request.headers["Authorization"] == "Bearer test-token"
        return httpx.Response(200, json={"results": [
            {"id": "MLM123", "title": "Anillo de plata", "price": 419.9, "currency_id": "MXN", "permalink": "https://articulo.mercadolibre.com.mx/MLM123", "thumbnail": "https://http2.mlstatic.com/anillo.jpg"},
            {"id": "MLM124", "title": "Sin enlace seguro", "price": 99, "currency_id": "MXN", "permalink": "http://example.com/unsafe"},
        ]})

    provider = MercadoLibreHttpProvider("test-token", transport=httpx.MockTransport(handler))
    snapshot = provider.search(country="MX", query="anillos de plata", limit=12)
    assert snapshot.source == "listings"
    assert snapshot.site_id == "MLM"
    assert len(snapshot.items) == 1
    assert snapshot.items[0].price == Decimal("419.9")
    assert snapshot.items[0].image_url == "https://http2.mlstatic.com/anillo.jpg"


@pytest.mark.parametrize("country", ["CO", "AR"])
def test_provider_rejects_non_mexico_country(country: str) -> None:
    provider = MercadoLibreHttpProvider("token", transport=httpx.MockTransport(lambda _: pytest.fail("No se debe llamar al proveedor")))
    with pytest.raises(MarketplaceSearchError) as failure:
        provider.search(country=country, query="lámpara", limit=5)
    assert failure.value.code == "unsupported_country"


def test_provider_uses_real_catalog_when_listing_search_is_forbidden() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/sites/MLM/search":
            return httpx.Response(403, json={"error": "forbidden"})
        assert request.url.path == "/products/search"
        assert request.url.params["site_id"] == "MLM"
        assert request.url.params["status"] == "active"
        assert request.headers["Authorization"] == "Bearer token"
        return httpx.Response(200, json={"results": [
            {"id": "MLM100", "name": "Producto inactivo", "status": "inactive"},
            {"id": "MLM101", "name": "Anillo de catálogo", "status": "active", "pictures": [{"url": "https://http2.mlstatic.com/catalogo.jpg"}]},
        ]})

    snapshot = MercadoLibreHttpProvider("token", transport=httpx.MockTransport(handler)).search(country="MX", query="anillos", limit=12)
    assert snapshot.source == "catalog"
    assert len(snapshot.items) == 1
    assert snapshot.items[0].id == "MLM101"
    assert snapshot.items[0].price is None
    assert snapshot.items[0].permalink is None
    assert snapshot.items[0].image_url == "https://http2.mlstatic.com/catalogo.jpg"


@pytest.mark.parametrize("status,code", [(401, "invalid_token"), (403, "forbidden"), (429, "rate_limited"), (500, "upstream_error")])
def test_provider_reports_upstream_failures_without_leaking_body(status: int, code: str) -> None:
    provider = MercadoLibreHttpProvider("token", transport=httpx.MockTransport(lambda _: httpx.Response(status, text="secret upstream details")))
    with pytest.raises(MarketplaceSearchError) as failure:
        provider.search(country="MX", query="anillos", limit=12)
    assert failure.value.code == code
    assert "secret" not in str(failure.value)


def test_provider_requires_backend_token() -> None:
    with pytest.raises(MarketplaceSearchError) as failure:
        MercadoLibreHttpProvider(None).search(country="MX", query="anillos", limit=12)
    assert failure.value.code == "not_configured"
