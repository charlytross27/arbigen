"""Score provisional y reproducible; no estima demanda, ventas ni competencia."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.modules.features.domain import FeatureReport
from app.modules.forecasting.domain import ForecastReport
from app.modules.profitability.model import FinancialAssumptions, calculate_profitability


MODEL_VERSION = "exploratory-v1"
HUNDRED = Decimal(100)
CENT = Decimal("0.01")


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
    limitations: tuple[str, ...]
    commission_cost: Decimal | None
    total_cost: Decimal | None
    unit_profit: Decimal | None
    margin_pct: Decimal | None
    roi_pct: Decimal | None


def _round(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _clamp(value: Decimal) -> Decimal:
    return max(Decimal(0), min(HUNDRED, value))


def calculate_score(
    *, features: FeatureReport, forecast: ForecastReport,
    assumptions: FinancialAssumptions | None = None, weights: ScoreWeights | None = None,
) -> ScoreReport:
    """Calcula solo si hay muestra, tendencia validada y supuestos financieros completos.

    Los umbrales son convenciones exploratorias versionadas, no una fórmula
    definitiva de oportunidad comercial.
    """
    chosen_weights = weights or ScoreWeights()
    missing: list[str] = []
    if features.market.priced_count < 8:
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

    components = {
        "growth": _round(_clamp(Decimal(50) + growth)) if growth is not None else None,
        "stability": _round(_clamp(HUNDRED - forecast.backtest_mae * 5)) if forecast.status == "ready" and forecast.backtest_mae is not None else None,
        "margin": _round(_clamp(margin_pct * Decimal("2.5"))) if margin_pct is not None else None,
        "roi": _round(_clamp(roi_pct)) if roi_pct is not None else None,
    }
    score = None
    if not missing:
        # Una operación con pérdida no puede recibir una recomendación positiva.
        score = Decimal("0.00") if unit_profit is not None and unit_profit <= 0 else _round(sum(
            (components[key] or Decimal(0)) * getattr(chosen_weights, key) for key in components
        ))
    return ScoreReport(
        model_version=MODEL_VERSION, status="ready" if score is not None else "incomplete", score=score,
        currency=features.market.currency, weights=chosen_weights, components=components,
        missing=tuple(missing),
        limitations=("No incluye ventas ni demanda absoluta.", "No mide competencia ni saturación.",
                     "Los costos y el precio son supuestos del usuario; no se verifican con proveedores."),
        commission_cost=commission_cost, total_cost=total_cost, unit_profit=unit_profit,
        margin_pct=margin_pct, roi_pct=roi_pct,
    )
