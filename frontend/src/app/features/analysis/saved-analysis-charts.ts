import type { EChartsOption } from 'echarts';
import type { AnalyticalProduct } from '../../core/models/analytical-dataset.model';

const CURRENCY = { MX: 'MXN', CO: 'COP', AR: 'ARS' } as const;

export function buildPriceDistributionChart(
  products: readonly AnalyticalProduct[],
  country: keyof typeof CURRENCY,
): EChartsOption | null {
  const prices = products.map(product => Number(product.price)).filter(price => Number.isFinite(price) && price > 0);
  if (!prices.length) return null;

  const minimum = Math.min(...prices);
  const maximum = Math.max(...prices);
  const bucketCount = minimum === maximum ? 1 : Math.min(5, new Set(prices).size);
  const width = bucketCount === 1 ? 0 : (maximum - minimum) / bucketCount;
  const counts = Array<number>(bucketCount).fill(0);
  for (const price of prices) {
    const index = width === 0 ? 0 : Math.min(bucketCount - 1, Math.floor((price - minimum) / width));
    counts[index]++;
  }

  const format = new Intl.NumberFormat('es-MX', { maximumFractionDigits: 2 });
  const labels = counts.map((_, index) => {
    if (width === 0) return format.format(minimum);
    const lower = minimum + index * width;
    const upper = index === bucketCount - 1 ? maximum : minimum + (index + 1) * width;
    return `${format.format(lower)}–${format.format(upper)}`;
  });

  return {
    animation: false,
    grid: { left: 45, right: 18, top: 20, bottom: 60 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'category', data: labels, axisLabel: { color: '#829084', hideOverlap: true, rotate: 15 } },
    yAxis: { type: 'value', min: 0, minInterval: 1, axisLabel: { color: '#829084' } },
    series: [{ name: `Productos · ${CURRENCY[country]}`, type: 'bar', data: counts, barMaxWidth: 72, itemStyle: { color: '#609174', borderRadius: [4, 4, 0, 0] } }],
  };
}
