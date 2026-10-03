"""Score provisional y reproducible; no estima demanda, ventas ni competencia."""

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from app.modules.features.domain import FeatureReport
from app.modules.forecasting.domain import ForecastReport
from app.modules.profitability.model import FinancialAssumptions, calculate_profitability


MODEL_VERSION = "exploratory-v2"
HUNDRED = Decimal(100)
CENT = Decimal("0.01")
MIN_PRODUCTS = 8
SMALL_SAMPLE_LIMIT = 20
MIN_PRICE_COVERAGE = Decimal(80)
MAX_MARKET_AGE_DAYS = 30
MAX_TREND_AGE_DAYS = {"daily": 14, "weekly": 42, "monthly": 93}


@dataclass(frozen=True)
class ScoreWeights:
    growth: Decimal = Decimal("0.25")
    stability: Decimal = Decimal("0.15")
    margin: Decimal = Decimal("0.35")
    roi: Decimal = Decimal("0.25")

    def __post_init__(self) -> None:
        values = (self.growth, self.stability, self.margin, self.roi)
        if any(not value.is_finite() or value < 0 or value > 1 for value in values) or sum(values) != 1:
            raise ValueError("Los pesos deben estar entre 0 y 1 y sumar exactamente 1.")


@dataclass(frozen=True)
class ScoreReport:
    model_version: str
    status: str
    score: Decimal | None
    currency: str
    weights: ScoreWeights
    components: dict[str, Decimal | None]
    missing: tuple[str, ...]
    warnings: tuple[str, ...]
    limitations: tuple[str, ...]
    evidence: "ScoreEvidence"
    sensitivity: tuple["ScoreSensitivity", ...]
    commission_cost: Decimal | None
    total_cost: Decimal | None
    unit_profit: Decimal | None
    margin_pct: Decimal | None
    roi_pct: Decimal | None


@dataclass(frozen=True)
class ScoreEvidence:
    product_count: int
    source_count: int | None
    price_coverage_pct: Decimal | None
    trend_point_count: int
    trend_observed_count: int
    trend_source: str | None
    trend_last_date: date | None
    market_fetched_date: date | None
    forecast_mae: Decimal | None
    forecast_naive_mae: Decimal | None
    forecast_backtest_origins: int


@dataclass(frozen=True)
class ScoreSensitivity:
    case: str
    sale_price: Decimal
    unit_profit: Decimal
    score: Decimal | None


def _round(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _clamp(value: Decimal) -> Decimal:
    return max(Decimal(0), min(HUNDRED, value))


def _components(growth: Decimal | None, mae: Decimal | None,
                margin: Decimal | None, roi: Decimal | None) -> dict[str, Decimal | None]:
    return {
        "growth": _round(_clamp(Decimal(50) + growth)) if growth is not None else None,
        "stability": _round(_clamp(HUNDRED - mae * 5)) if mae is not None else None,
        "margin": _round(_clamp(margin * Decimal("2.5"))) if margin is not None else None,
        "roi": _round(_clamp(roi)) if roi is not None else None,
    }


def _weighted_score(components: dict[str, Decimal | None], weights: ScoreWeights,
                    unit_profit: Decimal, roi: Decimal | None) -> Decimal | None:
    if roi is None:
        return None
    if unit_profit <= 0:
        return Decimal("0.00")
    return _round(sum((components[key] or Decimal(0)) * getattr(weights, key) for key in components))


def _sensitivity(assumptions: FinancialAssumptions, growth: Decimal, mae: Decimal,
                 weights: ScoreWeights) -> tuple[ScoreSensitivity, ...]:
    cases = (
        ("price_down_10pct", replace(assumptions, sale_price=_round(assumptions.sale_price * Decimal("0.90")))),
        ("fixed_costs_up_10pct", replace(
            assumptions,
            product_cost=_round(assumptions.product_cost * Decimal("1.10")),
            shipping_cost=_round(assumptions.shipping_cost * Decimal("1.10")),
            other_costs=_round(assumptions.other_costs * Decimal("1.10")),
        )),
    )
    results = []
    for case, alternative in cases:
        economics = calculate_profitability(alternative)
        components = _components(growth, mae, economics.margin_pct, economics.roi_pct)
        results.append(ScoreSensitivity(
            case, alternative.sale_price, economics.unit_profit,
            _weighted_score(components, weights, economics.unit_profit, economics.roi_pct),
        ))
    return tuple(results)


def calculate_score(
    *, features: FeatureReport, forecast: ForecastReport,
    assumptions: FinancialAssumptions | None = None, weights: ScoreWeights | None = None,
    trend_source: str | None = None, trend_last_date: date | None = None,
    market_fetched_date: date | None = None, as_of: date | None = None,
) -> ScoreReport:
    """Calcula solo si hay muestra, tendencia validada y supuestos financieros completos.

    Los umbrales son convenciones exploratorias versionadas, no una fórmula
    definitiva de oportunidad comercial.
    """
    chosen_weights = weights or ScoreWeights()
    missing: list[str] = []
    if features.market.priced_count < MIN_PRODUCTS:
        missing.append("market_sample")
    growth = features.trend.growth_3v3_pct
    if growth is None:
        missing.append("trend_growth")
    if forecast.status != "ready" or forecast.backtest_mae is None:
        missing.append("validated_forecast")
    if assumptions is None:
        missing.append("financial_inputs")

    commission_cost = total_cost = unit_profit = margin_pct = roi_pct = None
    if assumptions is not None:
        amounts = (assumptions.sale_price, assumptions.product_cost, assumptions.shipping_cost,
                   assumptions.commission_pct, assumptions.other_costs)
        if any(not value.is_finite() or value < 0 for value in amounts) or assumptions.sale_price <= 0 or assumptions.commission_pct > 100:
            raise ValueError("El precio debe ser positivo; costos y comisión deben ser válidos.")
        economics = calculate_profitability(assumptions)
        commission_cost = economics.commission_cost
        total_cost = economics.total_cost
        unit_profit = economics.unit_profit
        margin_pct = economics.margin_pct
        roi_pct = economics.roi_pct
        if roi_pct is None:
            missing.append("roi_denominator")

    mae = forecast.backtest_mae if forecast.status == "ready" else None
    components = _components(growth, mae, margin_pct, roi_pct)
    score = None
    if not missing:
        assert unit_profit is not None
        score = _weighted_score(components, chosen_weights, unit_profit, roi_pct)

    warnings: list[str] = []
    market = features.market
    if MIN_PRODUCTS <= market.priced_count < SMALL_SAMPLE_LIMIT:
        warnings.append("small_market_sample")
    if market.price_coverage_pct is not None and market.price_coverage_pct < MIN_PRICE_COVERAGE:
        warnings.append("low_price_coverage")
    if features.trend.point_count and trend_source != "google_trends_csv":
        warnings.append("trend_geo_unverified")
    if as_of is not None:
        if market_fetched_date is not None and (as_of - market_fetched_date).days > MAX_MARKET_AGE_DAYS:
            warnings.append("market_stale")
        max_trend_age = MAX_TREND_AGE_DAYS.get(forecast.frequency or "")
        if trend_last_date is not None and max_trend_age is not None and (as_of - trend_last_date).days > max_trend_age:
            warnings.append("trend_stale")
    evidence = ScoreEvidence(
        product_count=market.priced_count, source_count=market.source_count,
        price_coverage_pct=market.price_coverage_pct,
        trend_point_count=features.trend.point_count,
        trend_observed_count=features.trend.observed_count,
        trend_source=trend_source, trend_last_date=trend_last_date,
        market_fetched_date=market_fetched_date,
        forecast_mae=mae, forecast_naive_mae=forecast.naive_mae,
        forecast_backtest_origins=forecast.backtest_origins,
    )
    sensitivity = (
        _sensitivity(assumptions, growth, mae, chosen_weights)
        if score is not None and assumptions is not None and growth is not None and mae is not None
        else ()
    )
    return ScoreReport(
        model_version=MODEL_VERSION, status="ready" if score is not None else "incomplete", score=score,
        currency=features.market.currency, weights=chosen_weights, components=components,
        missing=tuple(missing),
        warnings=tuple(warnings), evidence=evidence, sensitivity=sensitivity,
        limitations=("No incluye ventas ni demanda absoluta.", "No mide competencia ni saturación.",
                     "Los costos y el precio son supuestos del usuario; no se verifican con proveedores.",
                     "La escala y los umbrales son convenciones exploratorias, no probabilidades ni una calibración comercial."),
        commission_cost=commission_cost, total_cost=total_cost, unit_profit=unit_profit,
        margin_pct=margin_pct, roi_pct=roi_pct,
    )
