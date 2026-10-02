import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { catchError, map, of, startWith, switchMap } from 'rxjs';
import { DashboardActivity, DashboardData, DashboardPeriod } from '../../core/models/dashboard.model';
import { AnalysisApiService } from '../../core/services/analysis-api.service';
import { IconComponent } from '../../shared/icon.component';

type DashboardState = { status: 'loading' } | { status: 'error' } | { status: 'success'; data: DashboardData };

@Component({
  selector: 'app-dashboard', standalone: true,
  imports: [RouterLink, IconComponent],
  templateUrl: './dashboard.component.html', styleUrl: './dashboard.component.scss',
})
export class DashboardComponent {
  private readonly api = inject(AnalysisApiService);
  readonly period = signal<DashboardPeriod>(30);
  private readonly reload = signal(0);
  private readonly request = computed(() => ({ days: this.period(), reload: this.reload() }));
  readonly state = toSignal(toObservable(this.request).pipe(
    switchMap(({ days }) => this.api.dashboard(days).pipe(
      map((data): DashboardState => ({ status: 'success', data })),
      startWith<DashboardState>({ status: 'loading' }),
      catchError(() => of<DashboardState>({ status: 'error' })),
    )),
  ), { initialValue: { status: 'loading' } as DashboardState });
  readonly featured = computed(() => {
    const current = this.state();
    if (current.status !== 'success') return null;
    return [...current.data.recent].sort((left, right) =>
      Number(right.product_count > 0) + Number(right.trend_point_count > 0)
      - Number(left.product_count > 0) - Number(left.trend_point_count > 0)
    )[0] ?? null;
  });

  setPeriod(event: Event): void {
    this.period.set((event.target as HTMLSelectElement).value === '7' ? 7 : 30);
  }

  retry(): void { this.reload.update(value => value + 1); }

  countryLabel(country: string): string {
    return { MX: 'México', CO: 'Colombia', AR: 'Argentina' }[country as 'MX' | 'CO' | 'AR'] ?? country;
  }

  activityLabel(kind: DashboardActivity['kind']): string {
    return { analysis_saved: 'Investigación guardada', products_prepared: 'Muestra de productos preparada',
             trends_imported: 'Serie de Trends importada' }[kind];
  }

  activityIcon(kind: DashboardActivity['kind']): 'chart' | 'catalog' | 'trend' {
    return { analysis_saved: 'chart', products_prepared: 'catalog', trends_imported: 'trend' }[kind] as 'chart' | 'catalog' | 'trend';
  }

  formatDate(value: string): string {
    return new Intl.DateTimeFormat('es-MX', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
  }
}
