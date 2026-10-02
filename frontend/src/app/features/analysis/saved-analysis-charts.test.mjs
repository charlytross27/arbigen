import assert from 'node:assert/strict';
import { test } from 'node:test';
import { buildPriceDistributionChart } from './saved-analysis-charts.ts';

const product = price => ({ price: String(price) });
const counts = chart => chart.series[0].data;

test('no dibuja precios si la muestra está vacía', () => {
  assert.equal(buildPriceDistributionChart([], 'MX'), null);
});

test('agrupa precios iguales en una sola barra', () => {
  const chart = buildPriceDistributionChart([product(120), product(120), product(120)], 'MX');
  assert.deepEqual(counts(chart), [3]);
  assert.deepEqual(chart.xAxis.data, ['120']);
});

test('incluye los valores mínimo y máximo sin perder productos', () => {
  const chart = buildPriceDistributionChart(
    [product(100), product(125), product(150), product(175), product(200), product(200)],
    'CO',
  );
  assert.deepEqual(counts(chart), [1, 1, 1, 1, 2]);
  assert.equal(counts(chart).reduce((total, count) => total + count, 0), 6);
  assert.equal(chart.series[0].name, 'Productos · COP');
});
