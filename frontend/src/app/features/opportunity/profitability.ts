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

  const cents = (value: number) => Math.round((value + Number.EPSILON) * 100);
  const rateBasisPoints = Math.round((input.commissionPercent + Number.EPSILON) * 100);
  const fixedCents = cents(input.productCost) + cents(input.shippingCost) + cents(input.otherCosts);
  const saleCents = cents(input.salePrice);
  const commissionAt = (priceCents: number) => Math.round(priceCents * rateBasisPoints / 10000);
  const commissionCents = commissionAt(saleCents);
  const totalCents = fixedCents + commissionCents;
  const profitCents = saleCents - totalCents;
  const commissionCost = commissionCents / 100;
  const totalCost = totalCents / 100;
  const profit = profitCents / 100;
  let breakEvenCents: number | null = null;
  if (rateBasisPoints < 10000) {
    breakEvenCents = fixedCents === 0 ? 0 : Math.ceil(fixedCents * 10000 / (10000 - rateBasisPoints) - 1e-9);
    while (breakEvenCents > 0 && breakEvenCents - 1 >= fixedCents + commissionAt(breakEvenCents - 1)) breakEvenCents--;
    while (breakEvenCents < fixedCents + commissionAt(breakEvenCents)) breakEvenCents++;
  } else if (fixedCents === 0) {
    breakEvenCents = 0;
  }

  return {
    commissionCost,
    totalCost,
    profit,
    marginPercent: saleCents > 0 ? (profitCents / saleCents) * 100 : null,
    roiPercent: totalCost > 0 ? (profit / totalCost) * 100 : null,
    breakEvenPrice: breakEvenCents === null ? null : breakEvenCents / 100,
  };
}
