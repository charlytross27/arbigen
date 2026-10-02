from decimal import Decimal

import pytest

from app.modules.profitability.model import FinancialAssumptions, calculate_profitability


def inputs(*, sale: str, product: str, shipping: str, commission: str, other: str) -> FinancialAssumptions:
    return FinancialAssumptions(Decimal(sale), Decimal(product), Decimal(shipping), Decimal(commission), Decimal(other))


def test_profitability_calculates_unit_economics_and_break_even() -> None:
    result = calculate_profitability(inputs(sale="420.00", product="115.00", shipping="35.00", commission="15.00", other="77.00"))
    assert result.commission_cost == Decimal("63.00")
    assert result.total_cost == Decimal("290.00")
    assert result.unit_profit == Decimal("130.00")
    assert result.margin_pct == Decimal("30.95")
    assert result.roi_pct == Decimal("44.83")
    assert result.break_even_price == Decimal("267.06")


def test_profitability_reports_loss_and_undefined_ratios() -> None:
    loss = calculate_profitability(inputs(sale="50", product="80", shipping="10", commission="10", other="0"))
    assert loss.unit_profit == Decimal("-45.00")
    assert loss.break_even_price == Decimal("100.00")
    zero = calculate_profitability(inputs(sale="0", product="0", shipping="0", commission="100", other="0"))
    assert zero.margin_pct is None and zero.roi_pct is None
    assert zero.break_even_price == Decimal("0.00")
    blocked = calculate_profitability(inputs(sale="10", product="1", shipping="0", commission="100", other="0"))
    assert blocked.break_even_price is None


def test_break_even_respects_commission_rounded_to_cents() -> None:
    result = calculate_profitability(inputs(sale="0.01", product="0.01", shipping="0", commission="40", other="0"))
    assert result.commission_cost == Decimal("0.00")
    assert result.break_even_price == Decimal("0.01")


@pytest.mark.parametrize("sale,commission", [("-1", "10"), ("1", "101"), ("NaN", "10")])
def test_profitability_rejects_invalid_inputs(sale: str, commission: str) -> None:
    with pytest.raises(ValueError):
        calculate_profitability(inputs(sale=sale, product="0", shipping="0", commission=commission, other="0"))
