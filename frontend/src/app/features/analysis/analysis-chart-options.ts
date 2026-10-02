import type { EChartsOption } from 'echarts';
import { AnalysisFixture } from '../../core/models/analysis.model';
import { AnalysisPeriod } from '../../core/models/saved-analysis.model';

const MONTHS = ['Oct', 'Nov', 'Dic', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep'];
const COLORS = ['#a9b9aa', '#327459', '#c4a573'];
const INK = '#40544a';
const MUTED = '#8a988d';
const GRID = '#edf0eb';

export interface AnalysisCharts {
  readonly interest: EChartsOption;
  readonly forecast: EChartsOption;
  readonly prices: EChartsOption;
  readonly priceDemand: EChartsOption;
  readonly clusters: EChartsOption;
}

function axisLabel() { return { color: MUTED, fontSize: 10 }; }
function splitLine() { return { lineStyle: { color: GRID } }; }

export function buildAnalysisCharts(fixture: AnalysisFixture, period: AnalysisPeriod): AnalysisCharts {
  const visibleMonths = period === '3m' ? 3 : period === '6m' ? 6 : 12;
  const labels = MONTHS.slice(-visibleMonths);
  const interest = fixture.interest.slice(-visibleMonths);
  const previous = fixture.interest.slice(-Math.min(visibleMonths, 4));
  const previousLabels = MONTHS.slice(-previous.length);
  const projectionLabels = [...previousLabels, 'Oct*', 'Nov*', 'Dic*'];
  const projection = [
    ...Array<null>(previous.length - 1).fill(null),
    previous.at(-1) ?? null,
    ...fixture.illustrativeProjection,
  ];

  return {
    interest: {
      animation: false,
      grid: { left: 37, right: 14, top: 20, bottom: 30 },
      tooltip: { trigger: 'axis', valueFormatter: value => `${value} / 100` },
      xAxis: { type: 'category', data: labels, boundaryGap: false, axisLine: { lineStyle: { color: GRID } }, axisTick: { show: false }, axisLabel: axisLabel() },
      yAxis: { type: 'value', min: 0, max: 100, interval: 25, axisLine: { show: false }, axisLabel: axisLabel(), splitLine: splitLine() },
      series: [{ name: 'Interés relativo · demo', type: 'line', data: interest, smooth: true, symbol: 'circle', symbolSize: 5, itemStyle: { color: '#39785b' }, lineStyle: { width: 3, color: '#39785b' }, areaStyle: { color: 'rgba(94,151,106,.13)' } }],
    },
    forecast: {
      animation: false,
      grid: { left: 37, right: 15, top: 20, bottom: 30 },
      tooltip: { trigger: 'axis', valueFormatter: value => `${value} / 100` },
      xAxis: { type: 'category', data: projectionLabels, boundaryGap: false, axisLine: { lineStyle: { color: GRID } }, axisTick: { show: false }, axisLabel: axisLabel() },
      yAxis: { type: 'value', min: 0, max: 100, interval: 25, axisLine: { show: false }, axisLabel: axisLabel(), splitLine: splitLine() },
      series: [
        { name: 'Referencia histórica · demo', type: 'line', data: [...previous, null, null, null], smooth: true, symbol: 'circle', symbolSize: 5, lineStyle: { color: '#39785b', width: 2 }, itemStyle: { color: '#39785b' } },
        { name: 'Proyección ilustrativa', type: 'line', data: projection, smooth: true, symbol: 'circle', symbolSize: 5, lineStyle: { color: '#b99b69', width: 2, type: 'dashed' }, itemStyle: { color: '#b99b69' } },
      ],
    },
    prices: {
      animation: false,
      grid: { left: 37, right: 12, top: 20, bottom: 40 },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: value => `${value} publicaciones demo` },
      xAxis: { type: 'category', data: fixture.priceBuckets.map(bucket => bucket.label), axisLine: { lineStyle: { color: GRID } }, axisTick: { show: false }, axisLabel: { ...axisLabel(), interval: 0, rotate: 16 } },
      yAxis: { type: 'value', min: 0, minInterval: 1, axisLine: { show: false }, axisLabel: axisLabel(), splitLine: splitLine() },
      series: [{ name: 'Publicaciones · demo', type: 'bar', data: fixture.priceBuckets.map(bucket => bucket.count), barWidth: '52%', itemStyle: { color: '#8cae8c', borderRadius: [3, 3, 0, 0] } }],
    },
    priceDemand: {
      animation: false,
      grid: { left: 37, right: 16, top: 20, bottom: 37 },
      tooltip: { trigger: 'item' },
      xAxis: { type: 'value', name: 'Precio MXN', nameLocation: 'middle', nameGap: 25, nameTextStyle: { color: MUTED, fontSize: 10 }, scale: true, axisLine: { lineStyle: { color: GRID } }, axisLabel: axisLabel(), splitLine: splitLine() },
      yAxis: { type: 'value', min: 0, max: 100, name: 'Índice', nameTextStyle: { color: MUTED, fontSize: 10 }, axisLine: { show: false }, axisLabel: axisLabel(), splitLine: splitLine() },
      series: [{ name: 'Precio / índice · demo', type: 'scatter', data: fixture.priceDemand.map(point => [point.price, point.demandIndex]), symbolSize: 11, itemStyle: { color: '#609174', opacity: .78 } }],
    },
    clusters: {
      animation: false,
      grid: { left: 37, right: 16, top: 22, bottom: 51 },
      legend: { bottom: 0, icon: 'circle', itemWidth: 8, itemHeight: 8, textStyle: { color: INK, fontSize: 10 } },
      tooltip: { trigger: 'item' },
      xAxis: { type: 'value', name: 'Precio MXN', nameLocation: 'middle', nameGap: 26, nameTextStyle: { color: MUTED, fontSize: 10 }, scale: true, axisLine: { lineStyle: { color: GRID } }, axisLabel: axisLabel(), splitLine: splitLine() },
      yAxis: { type: 'value', min: 0, max: 100, name: 'Índice', nameTextStyle: { color: MUTED, fontSize: 10 }, axisLine: { show: false }, axisLabel: axisLabel(), splitLine: splitLine() },
      series: fixture.clusters.map((cluster, index) => ({
        name: `Segmento ${cluster.number}`, type: 'scatter' as const,
        data: cluster.points.map(point => [point.price, point.demandIndex]),
        symbolSize: cluster.recommended ? 14 : 11,
        itemStyle: { color: COLORS[index] ?? COLORS[0], opacity: .9 },
      })),
    },
  };
}
