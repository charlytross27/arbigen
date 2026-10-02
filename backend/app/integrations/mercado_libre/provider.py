from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Literal
from urllib.parse import urlsplit

import httpx

from app.modules.marketplace.domain import MarketplaceProduct, MarketplaceSearchError, MarketplaceSearchResult


API_BASE_URL = "https://api.mercadolibre.com"
SITE_ID = "MLM"
ALLOWED_LINK_HOSTS = {"mercadolibre.com.mx"}


def _https_url(value: object, *, allowed_hosts: set[str] | None = None) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname:
        return None
    if allowed_hosts and not any(parsed.hostname == host or parsed.hostname.endswith("." + host) for host in allowed_hosts):
        return None
    return value


def _listing(raw: object) -> MarketplaceProduct | None:
    if not isinstance(raw, dict):
        return None
    listing_id, title, currency = raw.get("id"), raw.get("title"), raw.get("currency_id")
    permalink = _https_url(raw.get("permalink"), allowed_hosts=ALLOWED_LINK_HOSTS)
    if not all(isinstance(value, str) and value.strip() for value in (listing_id, title, currency)) or not permalink:
        return None
    try:
        price = Decimal(str(raw.get("price")))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not price.is_finite() or price < 0 or len(currency) != 3:
        return None
    return MarketplaceProduct(
        id=listing_id,
        title=title.strip(),
        price=price,
        currency=currency,
        permalink=permalink,
        image_url=_https_url(raw.get("thumbnail"), allowed_hosts={"mlstatic.com"}),
    )


def _catalog_product(raw: object) -> MarketplaceProduct | None:
    if not isinstance(raw, dict) or raw.get("status") != "active":
        return None
    product_id, name = raw.get("id"), raw.get("name")
    if not isinstance(product_id, str) or not product_id.startswith("MLM") or not isinstance(name, str) or not name.strip():
        return None
    pictures = raw.get("pictures")
    first_picture = pictures[0] if isinstance(pictures, list) and pictures and isinstance(pictures[0], dict) else {}
    return MarketplaceProduct(
        id=product_id,
        title=name.strip(),
        price=None,
        currency=None,
        permalink=None,
        image_url=_https_url(first_picture.get("url"), allowed_hosts={"mlstatic.com"}),
    )


class MercadoLibreHttpProvider:
    def __init__(self, access_token: str | None, *, transport: httpx.BaseTransport | None = None):
        self.access_token = access_token.strip() if access_token else None
        self.transport = transport

    def search(self, *, country: str, query: str, limit: int = 12) -> MarketplaceSearchResult:
        if not self.access_token:
            raise MarketplaceSearchError("not_configured")
        if country != "MX":
            raise MarketplaceSearchError("unsupported_country")
        if limit < 1:
            raise ValueError("Límite no admitido.")
        # Los endpoints oficiales actuales admiten una muestra menor que el límite del análisis.
        request_limit = min(limit, 20)
        try:
            with httpx.Client(timeout=8.0, transport=self.transport, follow_redirects=False) as client:
                response = client.get(
                    f"{API_BASE_URL}/sites/{SITE_ID}/search",
                    params={"q": query, "limit": request_limit, "offset": 0},
                    headers={"Authorization": f"Bearer {self.access_token}"},
                )
                if response.status_code == 403:
                    response = client.get(
                        f"{API_BASE_URL}/products/search",
                        params={"site_id": SITE_ID, "q": query, "status": "active", "limit": request_limit},
                        headers={"Authorization": f"Bearer {self.access_token}"},
                    )
                    source: Literal["listings", "catalog"] = "catalog"
                else:
                    source = "listings"
        except httpx.RequestError as error:
            raise MarketplaceSearchError("network_error") from error

        if response.status_code == 401:
            raise MarketplaceSearchError("invalid_token")
        if response.status_code == 403:
            raise MarketplaceSearchError("forbidden")
        if response.status_code == 429:
            raise MarketplaceSearchError("rate_limited")
        if response.status_code != 200:
            raise MarketplaceSearchError("upstream_error")
        try:
            payload = response.json()
        except ValueError as error:
            raise MarketplaceSearchError("invalid_response") from error
        if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
            raise MarketplaceSearchError("invalid_response")
        normalizer = _listing if source == "listings" else _catalog_product
        items = [product for raw in payload["results"][:request_limit] if (product := normalizer(raw)) is not None]
        return MarketplaceSearchResult(source=source, site_id=SITE_ID, query=query, fetched_at=datetime.now(timezone.utc), items=items)
