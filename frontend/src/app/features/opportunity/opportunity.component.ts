import { DecimalPipe } from '@angular/common';
import { Component, computed, effect, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { catchError, combineLatest, map, of, startWith, switchMap } from 'rxjs';
import { FinancialInputs, OpportunityDetail } from '../../core/models/opportunity.model';
import { IconComponent } from '../../shared/icon.component';
import { OpportunityDemoService } from './opportunity-demo.service';
import { calculateProfitability } from './profitability';

type OpportunityState =
  | { readonly status: 'loading' }
  | { readonly status: 'empty' }
  | { readonly status: 'error' }
  | { readonly status: 'success'; readonly opportunity: OpportunityDetail };

type FinancialField = keyof FinancialInputs;
type RawInputs = Record<FinancialField, string>;

const EMPTY_INPUTS: RawInputs = {
  productCost: '', shippingCost: '', commissionPercent: '', otherCosts: '', salePrice: '',
};

@Component({
  selector: 'app-opportunity', standalone: true,
  imports: [DecimalPipe, RouterLink, IconComponent],
  templateUrl: './opportunity.component.html', styleUrl: './opportunity.component.scss',
})
export class OpportunityComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly demo = inject(OpportunityDemoService);
  private readonly reload = signal(0);
  private initializedId: string | null = null;

  readonly state = toSignal(combineLatest([this.route.paramMap, toObservable(this.reload)]).pipe(
    switchMap(([params]) => this.demo.getOpportunity(params.get('id')).pipe(
      map((opportunity): OpportunityState => opportunity
        ? { status: 'success', opportunity }
        : { status: 'empty' }),
      startWith<OpportunityState>({ status: 'loading' }),
      catchError(() => of<OpportunityState>({ status: 'error' })),
    )),
  ), { initialValue: { status: 'loading' } as OpportunityState });

  readonly inputs = signal<RawInputs>(EMPTY_INPUTS);
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
      const current = this.state();
      if (current.status !== 'success' || current.opportunity.id === this.initializedId) return;
      const defaults = current.opportunity.defaults;
      this.inputs.set({
        productCost: String(defaults.productCost),
        shippingCost: String(defaults.shippingCost),
        commissionPercent: String(defaults.commissionPercent),
        otherCosts: String(defaults.otherCosts),
        salePrice: String(defaults.salePrice),
      });
      this.initializedId = current.opportunity.id;
    });
  }

  updateInput(field: FinancialField, event: Event): void {
    this.inputs.update(current => ({ ...current, [field]: (event.target as HTMLInputElement).value }));
  }

  fieldError(field: FinancialField): string | null {
    const raw = this.inputs()[field];
    if (raw.trim() === '') return 'Introduce un valor.';
    const value = Number(raw);
    if (!Number.isFinite(value) || value < 0) return 'Introduce un número igual o mayor que cero.';
    if (field === 'commissionPercent' && value > 100) return 'La comisión debe estar entre 0 y 100 %.';
    return null;
  }

  resetDefaults(opportunity: OpportunityDetail): void {
    const defaults = opportunity.defaults;
    this.inputs.set({
      productCost: String(defaults.productCost), shippingCost: String(defaults.shippingCost),
      commissionPercent: String(defaults.commissionPercent), otherCosts: String(defaults.otherCosts),
      salePrice: String(defaults.salePrice),
    });
  }

  retry(): void { this.reload.update(value => value + 1); }
}
