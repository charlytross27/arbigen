import assert from 'node:assert/strict';
import { test } from 'node:test';
import { calculateProfitability } from './profitability.ts';

test('calcula costos, margen, ROI y equilibrio con comisión sobre venta', () => {
  const result = calculateProfitability({
    productCost: 115, shippingCost: 35, commissionPercent: 15, otherCosts: 77, salePrice: 420,
  });
  assert.ok(result);
  assert.equal(result.commissionCost, 63);
  assert.equal(result.totalCost, 290);
  assert.equal(result.profit, 130);
  assert.ok(Math.abs(result.marginPercent - 130 / 420 * 100) < 1e-10);
  assert.ok(Math.abs(result.roiPercent - 130 / 290 * 100) < 1e-10);
  assert.equal(result.breakEvenPrice, 267.06);
});

test('muestra pérdidas cuando el precio no cubre costos', () => {
  const result = calculateProfitability({
    productCost: 100, shippingCost: 20, commissionPercent: 10, otherCosts: 0, salePrice: 100,
  });
  assert.ok(result);
  assert.equal(result.totalCost, 130);
  assert.equal(result.profit, -30);
  assert.equal(result.marginPercent, -30);
  assert.ok(result.roiPercent < 0);
  assert.equal(result.breakEvenPrice, 133.33);
});

test('mantiene cocientes indefinidos cuando el denominador es cero', () => {
  const result = calculateProfitability({
    productCost: 0, shippingCost: 0, commissionPercent: 0, otherCosts: 0, salePrice: 0,
  });
  assert.deepEqual(result, {
    commissionCost: 0, totalCost: 0, profit: 0,
    marginPercent: null, roiPercent: null, breakEvenPrice: 0,
  });
});

test('equilibrio refleja la comisión efectivamente redondeada a centavos', () => {
  const result = calculateProfitability({
    productCost: 0.01, shippingCost: 0, commissionPercent: 40, otherCosts: 0, salePrice: 0.01,
  });
  assert.equal(result.commissionCost, 0);
  assert.equal(result.breakEvenPrice, 0.01);
});

test('indica que una comisión del 100 % impide un equilibrio finito', () => {
  const result = calculateProfitability({
    productCost: 50, shippingCost: 0, commissionPercent: 100, otherCosts: 0, salePrice: 500,
  });
  assert.ok(result);
  assert.equal(result.profit, -50);
  assert.equal(result.breakEvenPrice, null);
  const noFixedCosts = calculateProfitability({
    productCost: 0, shippingCost: 0, commissionPercent: 100, otherCosts: 0, salePrice: 500,
  });
  assert.equal(noFixedCosts.breakEvenPrice, 0);
});

test('rechaza entradas negativas, no finitas y comisiones superiores al 100 %', () => {
  const valid = { productCost: 10, shippingCost: 5, commissionPercent: 15, otherCosts: 0, salePrice: 30 };
  assert.equal(calculateProfitability({ ...valid, productCost: -1 }), null);
  assert.equal(calculateProfitability({ ...valid, salePrice: Number.NaN }), null);
  assert.equal(calculateProfitability({ ...valid, commissionPercent: 100.01 }), null);
});
