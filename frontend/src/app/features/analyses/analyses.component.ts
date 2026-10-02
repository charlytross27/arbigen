import { Component, DestroyRef, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { SavedAnalysis } from '../../core/models/saved-analysis.model';
import { AnalysisApiService } from '../../core/services/analysis-api.service';
import { IconComponent } from '../../shared/icon.component';

type ListStatus = 'loading' | 'success' | 'error';

@Component({
  selector: 'app-analyses', standalone: true,
  imports: [RouterLink, IconComponent],
  templateUrl: './analyses.component.html', styleUrl: './analyses.component.scss',
})
export class AnalysesComponent {
  private readonly api = inject(AnalysisApiService);
  private readonly destroyRef = inject(DestroyRef);
  readonly status = signal<ListStatus>('loading');
  readonly items = signal<readonly SavedAnalysis[]>([]);
  readonly total = signal(0);
  readonly loadingMore = signal(false);
  readonly errorMessage = signal<string | null>(null);

  constructor() { this.load(true); }

  refresh(): void { this.load(true); }
  loadMore(): void { this.load(false); }

  countryLabel(country: string): string {
    return { MX: 'México', CO: 'Colombia', AR: 'Argentina' }[country as 'MX' | 'CO' | 'AR'] ?? country;
  }

  formatDate(value: string): string {
    return new Intl.DateTimeFormat('es-MX', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
  }

  private load(reset: boolean): void {
    if (this.loadingMore() || (!reset && this.status() === 'loading')) return;
    if (reset) {
      this.status.set('loading');
      this.items.set([]);
    } else this.loadingMore.set(true);
    this.errorMessage.set(null);
    const offset = reset ? 0 : this.items().length;
    this.api.list(20, offset).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: page => {
        this.items.update(current => reset ? page.items : [...current, ...page.items]);
        this.total.set(page.total);
        this.status.set('success');
        this.loadingMore.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(error.status === 0
          ? 'No pudimos conectar con FastAPI. Comprueba que el backend esté iniciado.'
          : 'No pudimos consultar PostgreSQL. Inténtalo de nuevo.');
        if (reset) this.status.set('error');
        this.loadingMore.set(false);
      },
    });
  }
}
