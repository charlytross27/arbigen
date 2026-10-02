import { DecimalPipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, computed, effect, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { takeUntilDestroyed, toObservable, toSignal } from '@angular/core/rxjs-interop';
import { catchError, combineLatest, forkJoin, map, of, startWith, switchMap } from 'rxjs';
import { AnalyticalDataset } from '../../core/models/analytical-dataset.model';
import { SavedAnalysis } from '../../core/models/saved-analysis.model';
import { SavedFinancialScenario, SaveFinancialScenarioRequest } from '../../core/models/saved-financial-scenario.model';
import { AnalysisApiService } from '../../core/services/analysis-api.service';
import { IconComponent } from '../../shared/icon.component';
import { FinancialInputs } from '../../core/models/opportunity.model';
import { calculateProfitability } from './profitability';

type ViewState =
  | { readonly status: 'loading' }
  | { readonly status: 'missing' }
  | { readonly status: 'error' }
  | { readonly status: 'ready'; readonly analysis: SavedAnalysis; readonly dataset: AnalyticalDataset; readonly saved: SavedFinancialScenario | null };

type FinancialField = keyof FinancialInputs;
type RawInputs = Record<FinancialField, string>;
const EMPTY_INPUTS: RawInputs = {
  salePrice: '', productCost: '', shippingCost: '', commissionPercent: '', otherCosts: '',
};
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

@Component({
  selector: 'app-saved-opportunity', standalone: true,
  imports: [DecimalPipe, RouterLink, IconComponent],
  templateUrl: './saved-opportunity.component.html',
  styleUrls: ['./opportunity.component.scss', './saved-opportunity.component.scss'],
})
export class SavedOpportunityComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly api = inject(AnalysisApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly reload = signal(0);
  private initializedId: string | null = null;

  readonly state = toSignal(combineLatest([this.route.paramMap, toObservable(this.reload)]).pipe(
    switchMap(([params]) => {
      const id = params.get('id');
      if (!id || !UUID_PATTERN.test(id)) return of<ViewState>({ status: 'missing' });
      return forkJoin({
        analysis: this.api.get(id), dataset: this.api.dataset(id), saved: this.api.financialScenario(id),
      }).pipe(
        map(({ analysis, dataset, saved }): ViewState => ({ status: 'ready', analysis, dataset, saved })),
        startWith<ViewState>({ status: 'loading' }),
        catchError((error: HttpErrorResponse) => of<ViewState>({ status: error.status === 404 ? 'missing' : 'error' })),
      );
    }),
  ), { initialValue: { status: 'loading' } as ViewState });

  readonly savedScenario = signal<SavedFinancialScenario | null>(null);
  readonly selectedProductId = signal('');
  readonly inputs = signal<RawInputs>(EMPTY_INPUTS);
  readonly touched = signal<ReadonlySet<FinancialField>>(new Set());
  readonly saving = signal(false);
  readonly saveError = signal<string | null>(null);
  readonly saveMessage = signal<string | null>(null);

  readonly selectedProduct = computed(() => {
    const view = this.state();
    return view.status === 'ready'
      ? view.dataset.products.find(product => product.id === this.selectedProductId()) ?? null
      : null;
  });
  readonly currency = computed(() => {
    const view = this.state();
    return this.selectedProduct()?.currency
      ?? this.savedScenario()?.currency
      ?? (view.status === 'ready' ? view.dataset.products[0]?.currency : null) ?? '';
  });
  readonly simulation = computed(() => {
    const raw = this.inputs();
    const values = {} as Record<FinancialField, number>;
    for (const field of Object.keys(raw) as FinancialField[]) {
      if (this.fieldError(field)) return null;
      values[field] = Number(raw[field]);
    }
    return calculateProfitability(values);
  });

  constructor() {
    effect(() => {
      const view = this.state();
      if (view.status !== 'ready' || this.initializedId === view.analysis.id) return;
      this.savedScenario.set(view.saved);
      this.restore(view.saved);
      this.initializedId = view.analysis.id;
    });
  }

  fieldError(field: FinancialField): string | null {
    const raw = this.inputs()[field];
    if (!raw.trim()) return 'Introduce un valor.';
    if (!/^\d+(?:\.\d{1,2})?$/.test(raw)) return 'Usa un importe no negativo con hasta dos decimales.';
    const value = Number(raw);
    if (field === 'salePrice' && value === 0) return 'El precio de venta debe ser mayor a cero.';
    if (!Number.isFinite(value) || value > (field === 'commissionPercent' ? 100 : 9999999999.99)) {
      return field === 'commissionPercent' ? 'La comisión debe estar entre 0 y 100 %.' : 'El importe es demasiado grande.';
    }
    return null;
  }

  visibleFieldError(field: FinancialField): string | null {
    return this.touched().has(field) ? this.fieldError(field) : null;
  }

  updateInput(field: FinancialField, event: Event): void {
    this.inputs.update(current => ({ ...current, [field]: (event.target as HTMLInputElement).value }));
    this.touched.update(current => new Set([...current, field]));
    this.saveMessage.set(null);
  }

  selectProduct(event: Event): void {
    this.selectedProductId.set((event.target as HTMLSelectElement).value);
    this.saveMessage.set(null);
  }

  restore(scenario: SavedFinancialScenario | null = this.savedScenario()): void {
    this.selectedProductId.set(scenario?.product_id ?? '');
    this.inputs.set(scenario ? {
      salePrice: scenario.sale_price, productCost: scenario.product_cost,
      shippingCost: scenario.shipping_cost, commissionPercent: scenario.commission_pct,
      otherCosts: scenario.other_costs,
    } : EMPTY_INPUTS);
    this.touched.set(new Set());
    this.saveError.set(null);
    this.saveMessage.set(null);
  }

  save(): void {
    const view = this.state();
    const product = this.selectedProduct();
    if (view.status !== 'ready' || !product || !this.simulation() || this.saving()) return;
    const raw = this.inputs();
    const payload: SaveFinancialScenarioRequest = {
      product_id: product.id, sale_price: Number(raw.salePrice),
      product_cost: Number(raw.productCost), shipping_cost: Number(raw.shippingCost),
      commission_pct: Number(raw.commissionPercent), other_costs: Number(raw.otherCosts),
    };
    this.saving.set(true);
    this.saveError.set(null);
    this.api.saveFinancialScenario(view.analysis.id, payload).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: saved => {
        this.savedScenario.set(saved);
        this.saving.set(false);
        this.saveMessage.set('Escenario guardado en tu cuenta.');
      },
      error: (error: HttpErrorResponse) => {
        this.saving.set(false);
        this.saveError.set(error.error?.error?.message ?? 'No se pudo guardar el escenario.');
      },
    });
  }

  downloadScenario(): void {
    const scenario = this.savedScenario();
    if (!scenario) return;
    const blob = new Blob([JSON.stringify(scenario, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `arbigen-scenario-${scenario.analysis_id}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  countryLabel(country: string): string {
    return { MX: 'México', CO: 'Colombia', AR: 'Argentina' }[country] ?? country;
  }

  retry(): void { this.reload.update(value => value + 1); }
}
