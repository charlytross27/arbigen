"""Composición de la fuente histórica; el router depende del contrato interno."""

from app.integrations.google_trends.csv_provider import GoogleTrendsCsvProvider
from app.modules.trends.domain import TrendsProvider


def get_trends_provider() -> TrendsProvider:
    return GoogleTrendsCsvProvider()
