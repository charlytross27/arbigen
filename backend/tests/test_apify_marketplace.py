import json
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal

import httpx
import pytest

from app.core.config import Settings
from app.integrations.apify.provider import ApifyMarketplaceSearchProvider
from app.integrations import marketplace_search
from app.integrations.mercado_libre.provider import MercadoLibreHttpProvider
from app.modules.analyses import marketplace
from app.modules.analyses.dataset import _market_product, _raw_product
from app.modules.etl.pipeline import prepare_dataset
from app.modules.marketplace.domain import MarketplaceProduct, MarketplaceSearchError, MarketplaceSearchResult


def test_apify_normalizes_mexican_results_and_caps_the_actor_run() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v2/actors/karamelo~mercadolibre-scraper-espanol-castellano/run-sync-get-dataset-items"
        assert request.url.params["limit"] == "200"
        assert request.url.params["maxItems"] == "200"
        assert request.headers["Authorization"] == "Bearer test-token"
        assert json.loads(request.read()) == {
            "keyword": "anillos de plata", "country": "https://listado.mercadolibre.com.mx/",
            "sort": "relevance", "maxPages": 4, "promoted": False, "extractProductDetails": False,
        }
        return httpx.Response(201, json=[
            {"idPublicacion": "MLM123", "articuloTitulo": "Anillo de plata", "zProductoLink": "https://www.mercadolibre.com.mx/anillo", "nuevoPrecio": "419.90", "Moneda": "MXN", "imgDireccion": "https://http2.mlstatic.com/anillo.webp", "Vendedor": "Tienda", "tipoRegistro": "busqueda", "tipoResultado": "ORGANIC"},
            {"idPublicacion": "MLM123", "articuloTitulo": "Duplicado", "zProductoLink": "https://www.mercadolibre.com.mx/duplicado", "tipoRegistro": "busqueda"},
            {"idPublicacion": "MLM124", "articuloTitulo": "Anuncio", "zProductoLink": "https://www.mercadolibre.com.mx/otro", "tipoResultado": "AD"},
            {"idPublicacion": "MLM125", "articuloTitulo": "Enlace inseguro", "zProductoLink": "https://example.com/otro"},
        ])

    provider = ApifyMarketplaceSearchProvider("test-token", "karamelo/mercadolibre-scraper-espanol-castellano", transport=httpx.MockTransport(handler))
    result = provider.search(country="MX", query="anillos de plata", limit=200)
    assert result.source == "listings"
    assert result.site_id == "MLM"
    assert len(result.items) == 1
    assert result.items[0].price == Decimal("419.90")
    assert result.items[0].currency == "MXN"
    assert result.items[0].image_url == "https://http2.mlstatic.com/anillo.webp"
    assert set(asdict(result.items[0])) == {"id", "title", "price", "currency", "permalink", "image_url", "signals"}
    assert result.items[0].signals.sold_quantity is None


def test_apify_normalizes_optional_listing_signals_without_inventing_missing_values() -> None:
    row = {
        "idPublicacion": "MLM6201055542", "articuloTitulo": "Set de fotografía",
        "zProductoLink": "https://articulo.mercadolibre.com.mx/MLM-6201055542",
        "nuevoPrecio": "3815", "Moneda": "MXN", "precioAnterior": "4,200",
        "cantidadVendida": None, "numeroEvaluaciones": "1,234", "produtoReviews": "4.7",
        "envioGratis": True, "enStock": None, "esTiendaOficial": False,
        "esCompraInternacional": False, "itemPosition": 1,
        "produtoCategoryID": "MLM191051", "produtoDomainID": "MLM-PHOTOGRAPHIC_BACKDROP_STANDS",
        "idVariacion": "MLMU5164639732", "resultadosTotales": "991 resultados",
    }
    provider = ApifyMarketplaceSearchProvider("token", "karamelo~mercadolibre-scraper-espanol-castellano", transport=httpx.MockTransport(lambda _: httpx.Response(201, json=[row])))
    result = provider.search(country="MX", query="set de fotografía", limit=10)
    item = result.items[0]
    assert result.reported_total_results == 991
    assert item.signals.previous_price == Decimal("4200")
    assert item.signals.review_count == 1234
    assert item.signals.rating == Decimal("4.7")
    assert item.signals.free_shipping is True
    assert item.signals.official_store is False
    assert item.signals.stock_available is None
    assert item.signals.sold_quantity is None
    assert item.signals.category_id == "MLM191051"
    assert item.signals.variation_id == "MLMU5164639732"
    assert _market_product(_raw_product(item)).signals == item.signals
    assert prepare_dataset(country="MX", products=result.items, trends=[]).products[0].signals == item.signals


def test_apify_skips_invalid_price_and_supports_missing_price() -> None:
    rows = [
        {"SKU": "MLM1", "articuloTitulo": "Sin precio", "zProductoLink": "https://www.mercadolibre.com.mx/item1"},
        {"idPublicacion": "MLM2", "articuloTitulo": "Precio inválido", "zProductoLink": "https://www.mercadolibre.com.mx/item2", "nuevoPrecio": "NaN", "Moneda": "MXN"},
    ]
    provider = ApifyMarketplaceSearchProvider("token", "karamelo~mercadolibre-scraper-espanol-castellano", transport=httpx.MockTransport(lambda _: httpx.Response(201, json=rows)))
    result = provider.search(country="MX", query="anillos", limit=2)
    assert len(result.items) == 1
    assert result.items[0].price is None
    assert result.items[0].currency is None


def test_apify_hard_caps_response_even_if_actor_returns_more_rows() -> None:
    rows = [
        {"idPublicacion": f"MLM{index}", "articuloTitulo": f"Anillo {index}", "zProductoLink": f"https://www.mercadolibre.com.mx/item{index}"}
        for index in range(205)
    ]
    provider = ApifyMarketplaceSearchProvider("token", "karamelo~mercadolibre-scraper-espanol-castellano", transport=httpx.MockTransport(lambda _: httpx.Response(201, json=rows)))
    result = provider.search(country="MX", query="anillos", limit=200)
    assert len(result.items) == 200
    assert result.items[-1].id == "MLM199"


def test_apify_rejects_nonempty_dataset_without_valid_products() -> None:
    provider = ApifyMarketplaceSearchProvider("token", "karamelo~mercadolibre-scraper-espanol-castellano", transport=httpx.MockTransport(lambda _: httpx.Response(201, json=[{"unexpected": "schema"}])))
    with pytest.raises(MarketplaceSearchError) as failure:
        provider.search(country="MX", query="anillos", limit=200)
    assert failure.value.code == "invalid_response"


@pytest.mark.parametrize("status,code", [(401, "invalid_token"), (402, "billing_required"), (403, "forbidden"), (408, "upstream_timeout"), (429, "rate_limited"), (500, "upstream_error")])
def test_apify_errors_do_not_expose_upstream_body(status: int, code: str) -> None:
    provider = ApifyMarketplaceSearchProvider("token", "karamelo~mercadolibre-scraper-espanol-castellano", transport=httpx.MockTransport(lambda _: httpx.Response(status, text="sensitive details")))
    with pytest.raises(MarketplaceSearchError) as failure:
        provider.search(country="MX", query="anillos", limit=5)
    assert failure.value.code == code
    assert "sensitive" not in str(failure.value)


def test_provider_selection_is_confined_to_composition(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(marketplace_search, "get_settings", lambda: Settings(
        marketplace_search_provider="auto", apify_api_token="token", _env_file=None,
    ))
    assert isinstance(marketplace_search.get_marketplace_search_provider(), ApifyMarketplaceSearchProvider)
    monkeypatch.setattr(marketplace_search, "get_settings", lambda: Settings(
        marketplace_search_provider="mercado_libre", apify_api_token="token", _env_file=None,
    ))
    assert isinstance(marketplace_search.get_marketplace_search_provider(), MercadoLibreHttpProvider)


def test_analysis_boundary_enforces_configured_limit_for_any_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(marketplace, "get_settings", lambda: Settings(max_products_per_analysis=2, _env_file=None))

    class OversizedProvider:
        def search(self, *, country: str, query: str, limit: int) -> MarketplaceSearchResult:
            assert (country, query, limit) == ("MX", "anillos", 2)
            return MarketplaceSearchResult(
                source="listings", site_id="MLM", query=query, fetched_at=datetime.now(timezone.utc),
                items=[MarketplaceProduct(id=f"MLM{index}", title=f"Anillo {index}", price=None, currency=None, permalink=None, image_url=None) for index in range(3)],
            )

    result = marketplace.search_marketplace("MX", "anillos", OversizedProvider())
    assert len(result.items) == 2


@pytest.mark.parametrize("country,url,host,site,currency,price,expected", [
    ("MX", "https://listado.mercadolibre.com.mx/", "mercadolibre.com.mx", "MLM", "MXN", "419.90", Decimal("419.90")),
    ("CO", "https://listado.mercadolibre.com.co/", "mercadolibre.com.co", "MCO", "COP", "1.234.567", Decimal("1234567")),
    ("AR", "https://listado.mercadolibre.com.ar/", "mercadolibre.com.ar", "MLA", "ARS", "1.234,56", Decimal("1234.56")),
])
def test_apify_maps_supported_countries(country: str, url: str, host: str, site: str, currency: str, price: str, expected: Decimal) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.read())["country"] == url
        return httpx.Response(201, json=[{
            "idPublicacion": f"{site}123", "articuloTitulo": "Producto",
            "zProductoLink": f"https://www.{host}/item", "nuevoPrecio": price, "Moneda": currency,
        }])

    result = ApifyMarketplaceSearchProvider("token", "karamelo~mercadolibre-scraper-espanol-castellano", transport=httpx.MockTransport(handler)).search(country=country, query="producto", limit=3)
    assert result.site_id == site
    assert result.items[0].currency == currency
    assert result.items[0].price == expected


def test_apify_requires_explicit_credentials_and_supported_country() -> None:
    provider = ApifyMarketplaceSearchProvider(None, None, transport=httpx.MockTransport(lambda _: pytest.fail("No network expected")))
    with pytest.raises(MarketplaceSearchError) as failure:
        provider.search(country="MX", query="anillos", limit=5)
    assert failure.value.code == "not_configured"
    with pytest.raises(MarketplaceSearchError) as failure:
        provider.search(country="BR", query="anillos", limit=5)
    assert failure.value.code == "unsupported_country"
