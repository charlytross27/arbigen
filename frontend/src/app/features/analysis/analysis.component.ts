import { Component, DestroyRef, computed, effect, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { DecimalPipe } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { takeUntilDestroyed, toObservable, toSignal } from '@angular/core/rxjs-interop';
import { catchError, combineLatest, map, of, startWith, switchMap } from 'rxjs';
import { SavedAnalysis } from '../../core/models/saved-analysis.model';
import { MarketplaceSearch } from '../../core/models/marketplace-product.model';
import { AnalyticalDataset } from '../../core/models/analytical-dataset.model';
import { AnalysisFeatures } from '../../core/models/analysis-features.model';
import { ClusterReport } from '../../core/models/analysis-clusters.model';
import { ForecastReport } from '../../core/models/analysis-forecast.model';
import { FinancialScenario, OpportunityScoreReport, ScoreWeights } from '../../core/models/opportunity-score.model';
import { TrendsSeries } from '../../core/models/trends.model';
import type { EChartsOption } from 'echarts';
import { AnalysisApiService } from '../../core/services/analysis-api.service';
import { IconComponent } from '../../shared/icon.component';
import { buildPriceDistributionChart } from './saved-analysis-charts';
import { AnalysisChartComponent } from './chart.component';

type AnalysisState =
  | { readonly status: 'loading' }
  | { readonly status: 'missing' }
  | { readonly status: 'error' }
  | { readonly status: 'saved'; readonly item: SavedAnalysis };

type MarketplaceState =
  | { readonly analysisId: string; readonly status: 'loading' }
  | { readonly analysisId: string; readonly status: 'error'; readonly message: string }
  | { readonly analysisId: string; readonly status: 'success'; readonly data: MarketplaceSearch };

type TrendsState =
  | { readonly analysisId: string; readonly status: 'loading' | 'uploading' }
  | { readonly analysisId: string; readonly status: 'error'; readonly message: string }
  | { readonly analysisId: string; readonly status: 'success'; readonly data: TrendsSeries };

type DatasetState =
  | { readonly analysisId: string; readonly status: 'loading' | 'reprocessing' }
  | { readonly analysisId: string; readonly status: 'error'; readonly message: string }
  | { readonly analysisId: string; readonly status: 'success'; readonly data: AnalyticalDataset };

type FeaturesState =
  | { readonly analysisId: string; readonly status: 'loading' }
  | { readonly analysisId: string; readonly status: 'error'; readonly message: string }
  | { readonly analysisId: string; readonly status: 'success'; readonly data: AnalysisFeatures };

type ClustersState =
  | { readonly analysisId: string; readonly status: 'loading' }
  | { readonly analysisId: string; readonly status: 'error'; readonly message: string }
  | { readonly analysisId: string; readonly status: 'success'; readonly data: ClusterReport };

type ForecastState =
  | { readonly analysisId: string; readonly status: 'loading' }
  | { readonly analysisId: string; readonly status: 'error'; readonly message: string }
  | { readonly analysisId: string; readonly status: 'success'; readonly data: ForecastReport };

type ScoreState =
  | { readonly analysisId: string; readonly status: 'loading' | 'previewing' | 'editing' }
  | { readonly analysisId: string; readonly status: 'error'; readonly message: string }
  | { readonly analysisId: string; readonly status: 'success'; readonly data: OpportunityScoreReport };

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

@Component({
  selector: 'app-analysis', standalone: true,
  imports: [DecimalPipe, RouterLink, IconComponent, AnalysisChartComponent],
  templateUrl: './analysis.component.html', styleUrl: './analysis.component.scss',
})
export class AnalysisComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly api = inject(AnalysisApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly reload = signal(0);
  readonly marketplace = signal<MarketplaceState | null>(null);
  readonly trends = signal<TrendsState | null>(null);
  readonly selectedTrendsFile = signal<File | null>(null);
  readonly dataset = signal<DatasetState | null>(null);
  readonly features = signal<FeaturesState | null>(null);
  readonly clusters = signal<ClustersState | null>(null);
  readonly forecast = signal<ForecastState | null>(null);
  readonly score = signal<ScoreState | null>(null);
  readonly financialScenario: FinancialScenario = {
    sale_price: null, product_cost: null, shipping_cost: null, commission_pct: null, other_costs: null,
  };
  readonly scoreWeights: ScoreWeights = { growth: 0.25, stability: 0.15, margin: 0.35, roi: 0.25 };

  readonly state = toSignal(combineLatest([
    this.route.paramMap,
    toObservable(this.reload),
  ]).pipe(
    switchMap(([params]) => {
      const id = params.get('id');
      if (!id || !UUID_PATTERN.test(id)) return of<AnalysisState>({ status: 'missing' });
      return this.api.get(id).pipe(
        map((item): AnalysisState => ({ status: 'saved', item })),
        startWith<AnalysisState>({ status: 'loading' }),
        catchError((error: HttpErrorResponse) => of<AnalysisState>(error.status === 404 ? { status: 'missing' } : { status: 'error' })),
      );
    }),
  ), { initialValue: { status: 'loading' } as AnalysisState });

  readonly priceDistributionChart = computed<EChartsOption | null>(() => {
    const current = this.dataset();
    return current?.status === 'success' ? buildPriceDistributionChart(current.data.products, current.data.country) : null;
  });

  readonly trendsChart = computed<EChartsOption | null>(() => {
    const current = this.trends();
    if (current?.status !== 'success' || !current.data.points.length) return null;
    return {
      animation: false,
      grid: { left: 45, right: 18, top: 20, bottom: 40 },
      tooltip: { trigger: 'axis', formatter: (params: any) => {
        const item = Array.isArray(params) ? params[0] : params;
        const point = current.data.points[item.dataIndex];
        return `${point.date}: ${point.less_than_one ? '&lt;1' : point.value}`;
      } },
      xAxis: { type: 'category', data: current.data.points.map(point => point.date), axisLabel: { color: '#829084', hideOverlap: true } },
      yAxis: { type: 'value', min: 0, max: 100, axisLabel: { color: '#829084' } },
      series: [{ type: 'line', smooth: false, symbolSize: 5, lineStyle: { color: '#39785b', width: 2 }, itemStyle: { color: '#39785b' }, areaStyle: { color: 'rgba(57,120,91,.08)' }, data: current.data.points.map(point => point.less_than_one ? null : point.value), connectNulls: false }],
    };
  });

  readonly forecastChart = computed<EChartsOption | null>(() => {
    const trends = this.trends();
    const forecast = this.forecast();
    if (trends?.status !== 'success' || forecast?.status !== 'success' ||
        trends.analysisId !== forecast.analysisId || forecast.data.status !== 'ready' || !trends.data.points.length) return null;
    const history = trends.data.points;
    const predictions = forecast.data.predictions;
    const dates = [...history.map(point => point.date), ...predictions.map(point => point.date)];
    const before = Array<null>(history.length).fill(null);
    const after = Array<null>(predictions.length).fill(null);
    return {
      animation: false,
      legend: { bottom: 0, textStyle: { color: '#829084', fontSize: 10 } },
      grid: { left: 45, right: 18, top: 20, bottom: 65 },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: dates, axisLabel: { color: '#829084', hideOverlap: true } },
      yAxis: { type: 'value', min: 0, max: 100, axisLabel: { color: '#829084' } },
      series: [
        { name: 'Histórico', type: 'line', symbolSize: 4, data: [...history.map(point => point.less_than_one ? null : point.value), ...after], lineStyle: { color: '#39785b', width: 2 }, itemStyle: { color: '#39785b' }, connectNulls: false },
        { name: 'Pronóstico', type: 'line', symbolSize: 5, data: [...before.slice(0, -1), history.at(-1)?.value ?? null, ...predictions.map(point => Number(point.value))], lineStyle: { color: '#d18b43', width: 2, type: 'dashed' }, itemStyle: { color: '#d18b43' }, connectNulls: false },
        { name: 'Rango inferior', type: 'line', symbol: 'none', data: [...before, ...predictions.map(point => Number(point.lower))], lineStyle: { color: '#d9ad7d', width: 1, type: 'dotted' } },
        { name: 'Rango superior', type: 'line', symbol: 'none', data: [...before, ...predictions.map(point => Number(point.upper))], lineStyle: { color: '#d9ad7d', width: 1, type: 'dotted' } },
      ],
    };
  });

  constructor() {
    effect(() => {
      const current = this.state();
      if (current.status !== 'saved') return;
      if (this.trends()?.analysisId === current.item.id) return;
      this.trends.set({ analysisId: current.item.id, status: 'loading' });
      this.api.trends(current.item.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: data => this.trends.set({ analysisId: current.item.id, status: 'success', data }),
        error: (error: HttpErrorResponse) => this.trends.set({ analysisId: current.item.id, status: 'error', message: this.errorMessage(error, 'No pudimos cargar los datos de Trends.') }),
      });
    });
    effect(() => {
      const current = this.state();
      if (current.status !== 'saved') return;
      if (this.dataset()?.analysisId === current.item.id) return;
      this.loadSavedDataset(current.item.id);
    });
    effect(() => {
      const current = this.state();
      if (current.status !== 'saved') return;
      if (this.features()?.analysisId === current.item.id) return;
      this.loadFeatures(current.item.id);
    });
    effect(() => {
      const current = this.state();
      if (current.status !== 'saved') return;
      if (this.clusters()?.analysisId === current.item.id) return;
      this.loadClusters(current.item.id);
    });
    effect(() => {
      const current = this.state();
      if (current.status !== 'saved') return;
      if (this.forecast()?.analysisId === current.item.id) return;
      this.loadForecast(current.item.id);
    });
    effect(() => {
      const current = this.state();
      if (current.status !== 'saved') return;
      if (this.score()?.analysisId === current.item.id) return;
      this.loadScore(current.item.id);
    });
  }

  retry(): void { this.reload.update(value => value + 1); }

  marketplaceFor(id: string): MarketplaceState | null {
    const state = this.marketplace();
    return state?.analysisId === id ? state : null;
  }

  marketplaceError(id: string): string | null {
    const state = this.marketplaceFor(id);
    return state?.status === 'error' ? state.message : null;
  }

  marketplaceResult(id: string): MarketplaceSearch | null {
    const state = this.marketplaceFor(id);
    return state?.status === 'success' ? state.data : null;
  }

  loadMarketplace(item: SavedAnalysis): void {
    if (this.marketplaceFor(item.id)?.status === 'loading') return;
    this.marketplace.set({ analysisId: item.id, status: 'loading' });
    this.api.refreshDataset(item.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: data => {
        this.dataset.set({ analysisId: item.id, status: 'success', data });
        if (data.snapshot) this.marketplace.set({ analysisId: item.id, status: 'success', data: data.snapshot });
        this.loadFeatures(item.id);
        this.loadClusters(item.id);
        this.loadScore(item.id);
      },
      error: (error: HttpErrorResponse) => {
        const apiMessage = error.error?.error?.message;
        const message = error.status === 0
          ? 'No pudimos conectar con Arbigen. Comprueba tu conexión e inténtalo de nuevo.'
          : typeof apiMessage === 'string' ? apiMessage : 'No pudimos consultar Mercado Libre. Inténtalo de nuevo.';
        this.marketplace.set({ analysisId: item.id, status: 'error', message });
      },
    });
  }

  datasetFor(id: string): DatasetState | null {
    const current = this.dataset();
    return current?.analysisId === id ? current : null;
  }

  datasetResult(id: string): AnalyticalDataset | null {
    const current = this.datasetFor(id);
    return current?.status === 'success' ? current.data : null;
  }

  datasetError(id: string): string | null {
    const current = this.datasetFor(id);
    return current?.status === 'error' ? current.message : null;
  }

  reprocessDataset(item: SavedAnalysis): void {
    if (this.datasetFor(item.id)?.status === 'reprocessing') return;
    this.dataset.set({ analysisId: item.id, status: 'reprocessing' });
    this.api.reprocessDataset(item.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: data => { this.dataset.set({ analysisId: item.id, status: 'success', data }); this.loadFeatures(item.id); this.loadClusters(item.id); this.loadScore(item.id); },
      error: (error: HttpErrorResponse) => this.dataset.set({ analysisId: item.id, status: 'error', message: this.errorMessage(error, 'No pudimos actualizar los datos guardados.') }),
    });
  }

  private loadSavedDataset(id: string): void {
    this.dataset.set({ analysisId: id, status: 'loading' });
    this.api.dataset(id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: data => {
        this.dataset.set({ analysisId: id, status: 'success', data });
        if (data.snapshot) this.marketplace.set({ analysisId: id, status: 'success', data: data.snapshot });
      },
      error: (error: HttpErrorResponse) => this.dataset.set({ analysisId: id, status: 'error', message: this.errorMessage(error, 'No pudimos cargar los datos guardados.') }),
    });
  }

  featuresFor(id: string): FeaturesState | null {
    const current = this.features();
    return current?.analysisId === id ? current : null;
  }

  featuresResult(id: string): AnalysisFeatures | null {
    const current = this.featuresFor(id);
    return current?.status === 'success' ? current.data : null;
  }

  featuresError(id: string): string | null {
    const current = this.featuresFor(id);
    return current?.status === 'error' ? current.message : null;
  }

  private loadFeatures(id: string): void {
    this.features.set({ analysisId: id, status: 'loading' });
    this.api.features(id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: data => this.features.set({ analysisId: id, status: 'success', data }),
      error: (error: HttpErrorResponse) => this.features.set({ analysisId: id, status: 'error', message: this.errorMessage(error, 'No pudimos cargar las variables analíticas.') }),
    });
  }

  clustersFor(id: string): ClustersState | null {
    const current = this.clusters();
    return current?.analysisId === id ? current : null;
  }

  clustersResult(id: string): ClusterReport | null {
    const current = this.clustersFor(id);
    return current?.status === 'success' ? current.data : null;
  }

  clustersError(id: string): string | null {
    const current = this.clustersFor(id);
    return current?.status === 'error' ? current.message : null;
  }

  private loadClusters(id: string): void {
    this.clusters.set({ analysisId: id, status: 'loading' });
    this.api.clusters(id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: data => this.clusters.set({ analysisId: id, status: 'success', data }),
      error: (error: HttpErrorResponse) => this.clusters.set({ analysisId: id, status: 'error', message: this.errorMessage(error, 'No pudimos cargar los segmentos.') }),
    });
  }

  forecastFor(id: string): ForecastState | null {
    const current = this.forecast();
    return current?.analysisId === id ? current : null;
  }

  forecastResult(id: string): ForecastReport | null {
    const current = this.forecastFor(id);
    return current?.status === 'success' ? current.data : null;
  }

  forecastError(id: string): string | null {
    const current = this.forecastFor(id);
    return current?.status === 'error' ? current.message : null;
  }

  forecastModelLabel(model: ForecastReport['selected_model']): string {
    switch (model) {
      case 'naive': return 'Último valor';
      case 'moving_average_3': return 'Promedio de 3 datos';
      case 'drift': return 'Cambio reciente';
      case 'seasonal_naive': return 'Patrón de temporadas anteriores';
      default: return '—';
    }
  }

  forecastFrequencyLabel(frequency: ForecastReport['frequency']): string {
    return frequency === 'daily' ? 'diaria' : frequency === 'weekly' ? 'semanal' : frequency === 'monthly' ? 'mensual' : '—';
  }

  private loadForecast(id: string): void {
    this.forecast.set({ analysisId: id, status: 'loading' });
    this.api.forecast(id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: data => this.forecast.set({ analysisId: id, status: 'success', data }),
      error: (error: HttpErrorResponse) => this.forecast.set({ analysisId: id, status: 'error', message: this.errorMessage(error, 'No pudimos revisar la evolución del interés.') }),
    });
  }

  scoreFor(id: string): ScoreState | null {
    const current = this.score();
    return current?.analysisId === id ? current : null;
  }

  scoreResult(id: string): OpportunityScoreReport | null {
    const current = this.scoreFor(id);
    return current?.status === 'success' ? current.data : null;
  }

  scoreMissingLabel(key: string): string {
    return {
      market_sample: 'al menos 8 productos con precio válido',
      trend_growth: '6 puntos recientes y consecutivos de Trends',
      validated_forecast: 'datos suficientes para comprobar la proyección',
      financial_inputs: 'precio de venta y costos del escenario',
      roi_denominator: 'costos mayores que cero para comparar la ganancia',
    }[key] ?? key;
  }

  invalidateScore(id: string): void {
    this.score.set({ analysisId: id, status: 'editing' });
  }

  setFinancial(key: keyof FinancialScenario, event: Event, id: string): void {
    const raw = (event.target as HTMLInputElement).value;
    this.financialScenario[key] = raw === '' ? null : Number(raw);
    this.invalidateScore(id);
  }

  setWeight(key: keyof ScoreWeights, event: Event, id: string): void {
    this.scoreWeights[key] = Number((event.target as HTMLInputElement).value);
    this.invalidateScore(id);
  }

  private loadScore(id: string): void {
    this.score.set({ analysisId: id, status: 'loading' });
    this.api.opportunityScore(id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: data => this.score.set({ analysisId: id, status: 'success', data }),
      error: (error: HttpErrorResponse) => this.score.set({ analysisId: id, status: 'error', message: this.errorMessage(error, 'No pudimos evaluar el score.') }),
    });
  }

  previewScore(item: SavedAnalysis, event: Event): void {
    event.preventDefault();
    const form = event.target as HTMLFormElement;
    if (!form.reportValidity() || this.scoreFor(item.id)?.status === 'previewing') return;
    if (Object.values(this.financialScenario).some(value => value === null || !Number.isFinite(value))) return;
    const weights = Object.values(this.scoreWeights);
    if (weights.some(value => !Number.isFinite(value) || value < 0 || value > 1) || Math.abs(weights.reduce((a, b) => a + b, 0) - 1) > 1e-9) {
      this.score.set({ analysisId: item.id, status: 'error', message: 'Los cuatro pesos deben estar entre 0 y 1 y sumar 1.' });
      return;
    }
    this.score.set({ analysisId: item.id, status: 'previewing' });
    this.api.previewOpportunityScore(item.id, { financial: this.financialScenario, weights: this.scoreWeights })
      .pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: data => this.score.set({ analysisId: item.id, status: 'success', data }),
        error: (error: HttpErrorResponse) => this.score.set({ analysisId: item.id, status: 'error', message: this.errorMessage(error, 'No pudimos calcular el escenario.') }),
      });
  }

  formatFeature(value: string | null, suffix = ''): string {
    if (value === null) return '—';
    const number = Number(value);
    if (!Number.isFinite(number)) return '—';
    return `${new Intl.NumberFormat('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(number)}${suffix}`;
  }

  materialHints(features: AnalysisFeatures): string {
    const entries = Object.entries(features.market.material_hints);
    return entries.length ? entries.map(([material, count]) => `${material}: ${count}`).join(' · ') : 'No se mencionan materiales';
  }

  downloadDataset(item: SavedAnalysis): void {
    const data = this.datasetResult(item.id);
    if (!data) return;
    const objectUrl = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
    const link = document.createElement('a');
    link.href = objectUrl;
    link.download = `arbigen-dataset-${item.id}.json`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
  }

  trendsFor(id: string): TrendsState | null {
    const current = this.trends();
    return current?.analysisId === id ? current : null;
  }

  trendsError(id: string): string | null {
    const current = this.trendsFor(id);
    return current?.status === 'error' ? current.message : null;
  }

  trendsResult(id: string): TrendsSeries | null {
    const current = this.trendsFor(id);
    return current?.status === 'success' ? current.data : null;
  }

  selectTrendsFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.selectedTrendsFile.set(input.files?.[0] ?? null);
  }

  async uploadTrends(item: SavedAnalysis): Promise<void> {
    const file = this.selectedTrendsFile();
    if (!file || this.trendsFor(item.id)?.status === 'uploading') return;
    if (!file.name.toLowerCase().endsWith('.csv') || file.size > 256 * 1024) {
      this.trends.set({ analysisId: item.id, status: 'error', message: 'Selecciona un CSV de Google Trends de hasta 256 KB.' });
      return;
    }
    let csv: string;
    try { csv = await file.text(); }
    catch { this.trends.set({ analysisId: item.id, status: 'error', message: 'No pudimos leer el archivo CSV.' }); return; }
    this.trends.set({ analysisId: item.id, status: 'uploading' });
    this.api.importTrends(item.id, csv).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: data => { this.trends.set({ analysisId: item.id, status: 'success', data }); this.loadSavedDataset(item.id); this.loadFeatures(item.id); this.loadForecast(item.id); this.loadScore(item.id); },
      error: (error: HttpErrorResponse) => this.trends.set({ analysisId: item.id, status: 'error', message: this.errorMessage(error, 'No pudimos importar el CSV.') }),
    });
  }

  private errorMessage(error: HttpErrorResponse, fallback: string): string {
    if (error.status === 0) return 'No pudimos conectar con Arbigen. Comprueba tu conexión e inténtalo de nuevo.';
    const message = error.error?.error?.message;
    return typeof message === 'string' ? message : fallback;
  }

  countryLabel(country: string): string {
    return { MX: 'México', CO: 'Colombia', AR: 'Argentina' }[country as 'MX' | 'CO' | 'AR'] ?? country;
  }

  formatDate(value: string): string {
    return new Intl.DateTimeFormat('es-MX', { dateStyle: 'long', timeStyle: 'short' }).format(new Date(value));
  }
}
