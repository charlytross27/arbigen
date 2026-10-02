import type { FinancialInputs } from '../../core/models/opportunity.model';

export interface ProfitabilityResult {
  readonly commissionCost: number;
  readonly totalCost: number;
  readonly profit: number;
  readonly marginPercent: number | null;
  readonly roiPercent: number | null;
  readonly breakEvenPrice: number | null;
}

// Cálculo por unidad. La comisión se aplica al precio de venta; impuestos,
// devoluciones y publicidad solo se incluyen si el usuario los suma a otros gastos.
export function calculateProfitability(input: FinancialInputs): ProfitabilityResult | null {
  const values = [input.productCost, input.shippingCost, input.commissionPercent, input.otherCosts, input.salePrice];
  if (values.some(value => !Number.isFinite(value) || value < 0) || input.commissionPercent > 100) return null;

  const commissionRate = input.commissionPercent / 100;
  const fixedCost = input.productCost + input.shippingCost + input.otherCosts;
  const commissionCost = input.salePrice * commissionRate;
  const totalCost = fixedCost + commissionCost;
  const profit = input.salePrice - totalCost;
  const rawBreakEven = commissionRate < 1 ? fixedCost / (1 - commissionRate) : fixedCost === 0 ? 0 : null;

  return {
    commissionCost,
    totalCost,
    profit,
    marginPercent: input.salePrice > 0 ? (profit / input.salePrice) * 100 : null,
    roiPercent: totalCost > 0 ? (profit / totalCost) * 100 : null,
    // El precio mostrado en centavos nunca queda por debajo del equilibrio exacto.
    breakEvenPrice: rawBreakEven === null ? null : rawBreakEven === 0 ? 0 : Math.ceil(rawBreakEven * 100 - 1e-9) / 100,
  };
}
