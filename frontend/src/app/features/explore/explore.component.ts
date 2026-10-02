import { Component, DestroyRef, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AnalysisCountry, AnalysisPeriod, ExploreRequest, SavedAnalysis } from '../../core/models/saved-analysis.model';
import { AnalysisApiService } from '../../core/services/analysis-api.service';
import { IconComponent } from '../../shared/icon.component';

type ExploreStatus = 'idle' | 'loading' | 'success' | 'error';

@Component({
  selector: 'app-explore', standalone: true,
  imports: [RouterLink, IconComponent],
  templateUrl: './explore.component.html', styleUrl: './explore.component.scss',
})
export class ExploreComponent {
  private readonly api = inject(AnalysisApiService);
  private readonly destroyRef = inject(DestroyRef);

  readonly keyword = signal('');
  readonly country = signal<AnalysisCountry>('MX');
  readonly category = signal('');
  readonly period = signal<AnalysisPeriod>('12m');
  readonly keywordError = signal<string | null>(null);
  readonly status = signal<ExploreStatus>('idle');
  readonly errorMessage = signal<string | null>(null);
  readonly request = signal<ExploreRequest | null>(null);
  readonly saved = signal<SavedAnalysis | null>(null);
  readonly countries: Record<AnalysisCountry, string> = { MX: 'México', CO: 'Colombia', AR: 'Argentina' };
  readonly periods: Record<AnalysisPeriod, string> = { '3m': 'Últimos 3 meses', '6m': 'Últimos 6 meses', '12m': 'Últimos 12 meses' };

  setKeyword(event: Event): void {
    this.keyword.set((event.target as HTMLInputElement).value);
    this.keywordError.set(null);
    this.resetCompletedState();
  }

  useExample(): void {
    if (this.status() === 'loading') return;
    this.keyword.set('anillos de plata ajustables');
    this.keywordError.set(null);
    this.resetCompletedState();
  }

  setCountry(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    if (this.isCountry(value)) this.country.set(value);
    this.resetCompletedState();
  }

  setCategory(event: Event): void {
    this.category.set((event.target as HTMLSelectElement).value);
    this.resetCompletedState();
  }

  setPeriod(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    if (this.isPeriod(value)) this.period.set(value);
    this.resetCompletedState();
  }

  submit(event: Event): void {
    event.preventDefault();
    if (this.status() === 'loading') return;

    const form = event.currentTarget as HTMLFormElement;
    const data = new FormData(form);
    const query = String(data.get('query') ?? '').replace(/\s+/g, ' ').trim();
    if (query.length < 3) {
      this.keywordError.set('Escribe al menos 3 caracteres para investigar un producto.');
      form.querySelector<HTMLInputElement>('#product-query')?.focus();
      return;
    }
    if (query.length > 120) {
      this.keywordError.set('La búsqueda no puede superar los 120 caracteres.');
      form.querySelector<HTMLInputElement>('#product-query')?.focus();
      return;
    }

    const country = String(data.get('country') ?? '');
    const period = String(data.get('period') ?? '');
    if (!this.isCountry(country) || !this.isPeriod(period)) {
      this.errorMessage.set('Revisa el país y el periodo seleccionados.');
      this.status.set('error');
      return;
    }

    const rawCategory = String(data.get('category') ?? '').trim();
    const request: ExploreRequest = {
      query,
      market: 'Mercado Libre',
      country,
      category: rawCategory || null,
      period,
    };
    this.keyword.set(query);
    this.start(request);
  }

  restart(): void {
    this.keyword.set('');
    this.country.set('MX');
    this.category.set('');
    this.period.set('12m');
    this.status.set('idle');
    this.request.set(null);
    this.saved.set(null);
    this.errorMessage.set(null);
  }

  retry(): void {
    const request = this.request();
    if (request) this.start(request);
    else this.status.set('idle');
  }

  private start(request: ExploreRequest): void {
    this.request.set(request);
    this.keywordError.set(null);
    this.errorMessage.set(null);
    this.saved.set(null);
    this.status.set('loading');
    const periodMonths = { '3m': 3, '6m': 6, '12m': 12 } as const;
    this.api.create({
      query: request.query, country: request.country,
      category: request.category, period_months: periodMonths[request.period],
    }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: saved => { this.saved.set(saved); this.status.set('success'); },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(error.status === 0
          ? 'No pudimos conectar con FastAPI. Comprueba que el backend esté iniciado.'
          : 'No pudimos guardar la búsqueda. Revisa la conexión a PostgreSQL e inténtalo de nuevo.');
        this.status.set('error');
      },
    });
  }

  private resetCompletedState(): void {
    if (this.status() === 'success' || this.status() === 'error') {
      this.status.set('idle');
      this.request.set(null);
      this.saved.set(null);
      this.errorMessage.set(null);
    }
  }

  private isCountry(value: string): value is AnalysisCountry {
    return value === 'MX' || value === 'CO' || value === 'AR';
  }

  private isPeriod(value: string): value is AnalysisPeriod {
    return value === '3m' || value === '6m' || value === '12m';
  }
}
