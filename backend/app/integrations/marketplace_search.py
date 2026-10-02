"""Punto de composición de la fuente externa de productos."""

from app.core.config import get_settings
from app.integrations.apify.provider import ApifyMarketplaceSearchProvider
from app.integrations.mercado_libre.provider import MercadoLibreHttpProvider
from app.modules.marketplace.domain import MarketplaceSearchProvider


def get_marketplace_search_provider() -> MarketplaceSearchProvider:
    settings = get_settings()
    if settings.marketplace_search_provider == "apify" or (
        settings.marketplace_search_provider == "auto" and settings.apify_api_token
    ):
        return ApifyMarketplaceSearchProvider(
            settings.apify_api_token, settings.apify_actor_id,
            timeout_seconds=settings.apify_request_timeout_seconds, max_pages=settings.apify_max_pages,
        )
    return MercadoLibreHttpProvider(settings.mercado_libre_access_token)
