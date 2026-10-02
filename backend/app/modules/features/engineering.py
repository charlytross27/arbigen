"""Variables descriptivas puras; no consulta proveedores ni estima ventas."""

from collections import Counter
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence

from app.modules.etl.domain import AnalyticalProduct, AnalyticalTrendPoint
from app.modules.etl.pipeline import COUNTRY_CURRENCY
from app.modules.features.domain import FeatureReport, MarketFeatures, TrendFeatures


HUNDRED = Decimal(100)
TWO_DECIMALS = Decimal("0.01")


def _rounded(value: Decimal) -> Decimal:
    return value.quantize(TWO_DECIMALS, rounding=ROUND_HALF_UP)


def _mean(values: Sequence[Decimal]) -> Decimal:
    return sum(values, Decimal(0)) / len(values)


def _median(values: Sequence[Decimal]) -> Decimal:
    ordered = sorted(values)
    center = len(ordered) // 2
    return ordered[center] if len(ordered) % 2 else (ordered[center - 1] + ordered[center]) / 2


def _stddev(values: Sequence[Decimal]) -> Decimal:
    average = _mean(values)
    return (_mean([(value - average) ** 2 for value in values])).sqrt()


def _regular_dates(dates: Sequence[date]) -> bool:
    gaps = [(right - left).days for left, right in zip(dates, dates[1:])]
    return bool(gaps) and (all(gap == 1 for gap in gaps) or all(gap == 7 for gap in gaps) or all(28 <= gap <= 31 for gap in gaps))


def _window_means(points: Sequence[AnalyticalTrendPoint], window_count: int) -> list[Decimal] | None:
    required = window_count * 3
    if len(points) < required:
        return None
    recent = points[-required:]
    if any(point.value is None or point.less_than_one for point in recent) or not _regular_dates([point.date for point in recent]):
        return None
    return [_mean([point.value for point in recent[index:index + 3] if point.value is not None]) for index in range(0, required, 3)]


def calculate_features(
    *, country: str, products: Sequence[AnalyticalProduct],
    trends: Sequence[AnalyticalTrendPoint], source_count: int | None,
) -> FeatureReport:
    if country not in COUNTRY_CURRENCY:
        raise ValueError("País no admitido para ingeniería de variables.")
    if source_count is not None and (source_count < 0 or source_count < len(products)):
        raise ValueError("El conteo de entrada no es compatible con los productos depurados.")
    currency = COUNTRY_CURRENCY[country]
    if any(product.currency != currency for product in products):
        raise ValueError("El dataset contiene monedas distintas a la del país.")
    prices = [product.price for product in products]
    material_hints = dict(sorted(Counter(product.attributes["material_hint"] for product in products if product.attributes.get("material_hint")).items()))
    market = MarketFeatures(
        currency=currency,
        source_count=source_count,
        priced_count=len(prices),
        price_coverage_pct=_rounded(Decimal(len(prices)) / source_count * HUNDRED) if source_count else None,
        price_min=min(prices) if prices else None,
        price_max=max(prices) if prices else None,
        price_mean=_rounded(_mean(prices)) if prices else None,
        price_median=_rounded(_median(prices)) if prices else None,
        price_stddev=_rounded(_stddev(prices)) if len(prices) >= 2 else None,
        material_hints=material_hints,
    )

    ordered = sorted(trends, key=lambda point: point.date)
    observed = [point.value for point in ordered if point.value is not None and not point.less_than_one]
    censored = sum(point.less_than_one for point in ordered)
    last_window = _window_means(ordered, 1)
    two_windows = _window_means(ordered, 2)
    three_windows = _window_means(ordered, 3)
    trend = TrendFeatures(
        point_count=len(ordered),
        observed_count=len(observed),
        censored_count=censored,
        observed_coverage_pct=_rounded(Decimal(len(observed)) / len(ordered) * HUNDRED) if ordered else None,
        mean_index=_rounded(_mean(observed)) if observed else None,
        volatility_index=_rounded(_stddev(observed)) if len(observed) >= 2 else None,
        moving_average_3=_rounded(last_window[0]) if last_window else None,
        growth_3v3_pct=_rounded((two_windows[1] - two_windows[0]) / two_windows[0] * HUNDRED) if two_windows and two_windows[0] > 0 else None,
        momentum_3v3=_rounded(two_windows[1] - two_windows[0]) if two_windows else None,
        acceleration_3v3=_rounded(three_windows[2] - 2 * three_windows[1] + three_windows[0]) if three_windows else None,
    )
    return FeatureReport(country, market, trend)
