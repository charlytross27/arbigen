"""Cálculo puro de rentabilidad por unidad; no estima ventas ni demanda."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP


CENT = Decimal("0.01")
HUNDRED = Decimal(100)


@dataclass(frozen=True)
class FinancialAssumptions:
    sale_price: Decimal
    product_cost: Decimal
    shipping_cost: Decimal
    commission_pct: Decimal
    other_costs: Decimal


@dataclass(frozen=True)
class ProfitabilityResult:
    commission_cost: Decimal
    total_cost: Decimal
    unit_profit: Decimal
    margin_pct: Decimal | None
    roi_pct: Decimal | None
    break_even_price: Decimal | None


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_profitability(inputs: FinancialAssumptions) -> ProfitabilityResult:
    amounts = (inputs.sale_price, inputs.product_cost, inputs.shipping_cost,
               inputs.commission_pct, inputs.other_costs)
    if any(not value.is_finite() or value < 0 for value in amounts) or inputs.commission_pct > 100:
        raise ValueError("Los precios y costos deben ser positivos o cero; la comisión debe ser 0–100 %.")

    commission = _money(inputs.sale_price * inputs.commission_pct / HUNDRED)
    fixed_cost = inputs.product_cost + inputs.shipping_cost + inputs.other_costs
    total_cost = _money(fixed_cost + commission)
    profit = _money(inputs.sale_price - total_cost)
    margin = _money(profit / inputs.sale_price * HUNDRED) if inputs.sale_price > 0 else None
    roi = _money(profit / total_cost * HUNDRED) if total_cost > 0 else None
    if inputs.commission_pct < HUNDRED:
        exact_break_even = fixed_cost / (1 - inputs.commission_pct / HUNDRED)
        break_even = exact_break_even.quantize(CENT, rounding=ROUND_CEILING)
        # La comisión se cobra en centavos; ese redondeo puede mover el umbral
        # un centavo respecto de la división exacta.
        while break_even > 0 and break_even - CENT >= _money(fixed_cost + _money((break_even - CENT) * inputs.commission_pct / HUNDRED)):
            break_even -= CENT
        while break_even < _money(fixed_cost + _money(break_even * inputs.commission_pct / HUNDRED)):
            break_even += CENT
    else:
        break_even = Decimal("0.00") if fixed_cost == 0 else None
    return ProfitabilityResult(commission, total_cost, profit, margin, roi, break_even)
