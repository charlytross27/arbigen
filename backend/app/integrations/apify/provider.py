"""Adaptador del Actor Karamelo de Apify; ninguna clave de su JSON sale de aquí."""

import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

import httpx

from app.modules.marketplace.domain import MarketplaceProduct, MarketplaceSearchError, MarketplaceSearchResult


API_BASE_URL = "https://api.apify.com/v2"
ACTOR_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+(?:[~/][A-Za-z0-9_-]+)?$")
MARKETS = {
    "MX": ("https://listado.mercadolibre.com.mx/", "mercadolibre.com.mx", "MLM", "MXN"),
    "CO": ("https://listado.mercadolibre.com.co/", "mercadolibre.com.co", "MCO", "COP"),
    "AR": ("https://listado.mercadolibre.com.ar/", "mercadolibre.com.ar", "MLA", "ARS"),
}


def _https_url(value: object, allowed_host: str) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname:
        return None
    if parsed.hostname != allowed_host and not parsed.hostname.endswith("." + allowed_host):
        return None
    return value


def _price(value: object) -> Decimal | None:
    if not isinstance(value, (str, int, float, Decimal)) or isinstance(value, bool):
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?", normalized):
        decimal_position = max(normalized.rfind("."), normalized.rfind(","))
        if len(normalized) - decimal_position - 1 <= 2:
            normalized = re.sub(r"[.,]", "", normalized[:decimal_position]) + "." + normalized[decimal_position + 1:]
        else:
            normalized = re.sub(r"[.,]", "", normalized)
    elif re.fullmatch(r"\d+(?:[.,]\d{1,2})?", normalized):
        normalized = normalized.replace(",", ".")
    else:
        return None
    try:
        price = Decimal(normalized)
    except (InvalidOperation, ValueError):
        return None
    return price if price.is_finite() and price >= 0 else None


def _product(raw: object, *, site_id: str, host: str, currency_code: str) -> MarketplaceProduct | None:
    if not isinstance(raw, dict) or raw.get("tipoRegistro") not in (None, "busqueda") or raw.get("tipoResultado") == "AD":
        return None
    product_id = raw.get("idPublicacion") or raw.get("SKU")
    title = raw.get("articuloTitulo")
    permalink = _https_url(raw.get("zProductoLink"), host)
    if not isinstance(product_id, str) or not product_id.startswith(site_id) or not isinstance(title, str) or not title.strip() or not permalink:
        return None
    price: Decimal | None = None
    currency: str | None = None
    raw_price = raw.get("nuevoPrecio")
    if raw_price not in (None, ""):
        price = _price(raw_price)
        if price is None or raw.get("Moneda") != currency_code:
            return None
        currency = currency_code
    return MarketplaceProduct(
        id=product_id,
        title=title.strip(),
        price=price,
        currency=currency,
        permalink=permalink,
        image_url=_https_url(raw.get("imgDireccion"), "mlstatic.com"),
    )


class ApifyMarketplaceSearchProvider:
    def __init__(self, api_token: str | None, actor_id: str | None, *, timeout_seconds: int = 120, max_pages: int = 4, transport: httpx.BaseTransport | None = None):
        self.api_token = api_token.strip() if api_token else None
        self.actor_id = actor_id.strip() if actor_id else None
        self.timeout_seconds = timeout_seconds
        self.max_pages = max_pages
        self.transport = transport

    def search(self, *, country: str, query: str, limit: int) -> MarketplaceSearchResult:
        if country not in MARKETS:
            raise MarketplaceSearchError("unsupported_country")
        if not self.api_token or not self.actor_id or not ACTOR_ID_PATTERN.fullmatch(self.actor_id):
            raise MarketplaceSearchError("not_configured")
        if not 1 <= limit <= 1000:
            raise ValueError("Límite no admitido.")

        country_url, host, site_id, currency_code = MARKETS[country]
        actor_id = self.actor_id.replace("/", "~")
        try:
            with httpx.Client(timeout=httpx.Timeout(self.timeout_seconds, connect=10.0), transport=self.transport, follow_redirects=False) as client:
                response = client.post(
                    f"{API_BASE_URL}/actors/{actor_id}/run-sync-get-dataset-items",
                    params={"limit": limit, "maxItems": limit, "format": "json"},
                    json={
                        "keyword": query,
                        "country": country_url,
                        "sort": "relevance",
                        "maxPages": self.max_pages,
                        "promoted": False,
                        "extractProductDetails": False,
                    },
                    headers={"Authorization": f"Bearer {self.api_token}", "Accept": "application/json"},
                )
        except httpx.TimeoutException as error:
            raise MarketplaceSearchError("upstream_timeout") from error
        except httpx.RequestError as error:
            raise MarketplaceSearchError("network_error") from error

        if response.status_code == 401:
            raise MarketplaceSearchError("invalid_token")
        if response.status_code == 402:
            raise MarketplaceSearchError("billing_required")
        if response.status_code == 403:
            raise MarketplaceSearchError("forbidden")
        if response.status_code == 408:
            raise MarketplaceSearchError("upstream_timeout")
        if response.status_code == 429:
            raise MarketplaceSearchError("rate_limited")
        if response.status_code != 201:
            raise MarketplaceSearchError("upstream_error")
        try:
            rows = response.json()
        except ValueError as error:
            raise MarketplaceSearchError("invalid_response") from error
        if not isinstance(rows, list):
            raise MarketplaceSearchError("invalid_response")
        products: list[MarketplaceProduct] = []
        seen: set[str] = set()
        for row in rows[:limit]:
            product = _product(row, site_id=site_id, host=host, currency_code=currency_code)
            if product and product.id not in seen:
                products.append(product)
                seen.add(product.id)
        if rows and not products:
            raise MarketplaceSearchError("invalid_response")
        return MarketplaceSearchResult(
            source="listings", site_id=site_id, query=query,
            fetched_at=datetime.now(timezone.utc), items=products,
        )
