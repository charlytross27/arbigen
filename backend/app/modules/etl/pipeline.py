"""Reglas ETL sobre contratos internos, sin referencias a proveedores externos."""

import html
import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Iterable

from app.modules.etl.domain import AnalyticalProduct, AnalyticalTrendPoint, PreparedDataset, ProductQuality
from app.modules.marketplace.domain import MarketplaceProduct
from app.modules.trends.domain import TrendObservation


COUNTRY_CURRENCY = {"MX": "MXN", "CO": "COP", "AR": "ARS"}
MATERIAL_HINTS = ("acero inoxidable", "algodon", "madera", "cuero", "plata")
MAX_PRICE = Decimal("9999999999.99")


def _title(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", html.unescape(value)).split())[:300]


def _fold(value: str) -> str:
    return "".join(character for character in unicodedata.normalize("NFKD", value.casefold()) if not unicodedata.combining(character))


def _attributes(title: str) -> dict[str, str]:
    folded = _fold(title)
    for material in MATERIAL_HINTS:
        if re.search(rf"(?<!\w){re.escape(material)}(?!\w)", folded):
            return {"material_hint": material, "hint_source": "title"}
    return {}


def _price(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    try:
        if not value.is_finite() or value < 0 or value > MAX_PRICE:
            return None
        rounded = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, AttributeError):
        return None
    return rounded if rounded <= MAX_PRICE else None


def _candidate_rank(product: MarketplaceProduct, expected_currency: str) -> tuple[bool, bool, bool, bool]:
    valid_price = _price(product.price) is not None
    return (
        bool(_title(product.title)) and valid_price and product.currency == expected_currency,
        bool(_title(product.title)),
        valid_price and product.currency == expected_currency,
        bool(product.permalink),
    )


def prepare_trends(trends: Iterable[TrendObservation]) -> tuple[AnalyticalTrendPoint, ...]:
    trend_rows: dict[date, AnalyticalTrendPoint] = {}
    for point in trends:
        if point.date in trend_rows:
            raise ValueError("La serie de Trends contiene fechas duplicadas.")
        if point.less_than_one:
            if point.value is not None:
                raise ValueError("Un valor censurado de Trends no debe tener índice numérico.")
        elif point.value is None or not point.value.is_finite() or not 0 <= point.value <= 100:
            raise ValueError("La serie de Trends contiene un índice inválido.")
        trend_rows[point.date] = AnalyticalTrendPoint(point.date, point.value, point.less_than_one)
    return tuple(trend_rows[key] for key in sorted(trend_rows))


def prepare_dataset(*, country: str, products: Iterable[MarketplaceProduct], trends: Iterable[TrendObservation]) -> PreparedDataset:
    if country not in COUNTRY_CURRENCY:
        raise ValueError("País no admitido para el dataset analítico.")
    expected_currency = COUNTRY_CURRENCY[country]
    rows = list(products)
    selected: dict[str, MarketplaceProduct] = {}
    duplicates = 0
    for product in rows:
        if product.id in selected:
            duplicates += 1
            previous = selected[product.id]
            if _candidate_rank(product, expected_currency) > _candidate_rank(previous, expected_currency):
                selected[product.id] = product
        else:
            selected[product.id] = product

    clean: list[AnalyticalProduct] = []
    missing_title = missing_price = invalid_price = invalid_currency = 0
    for product in selected.values():
        title = _title(product.title)
        if not title:
            missing_title += 1
            continue
        if product.price is None:
            missing_price += 1
            continue
        price = _price(product.price)
        if price is None:
            invalid_price += 1
            continue
        if product.currency != expected_currency:
            invalid_currency += 1
            continue
        clean.append(AnalyticalProduct(product.id, title, price, expected_currency, product.permalink, product.image_url, _attributes(title)))

    quality = ProductQuality(len(rows), duplicates, missing_title, missing_price, invalid_price, invalid_currency, len(clean))
    return PreparedDataset(tuple(clean), prepare_trends(trends), quality)
