import { Injectable } from '@angular/core';
import { Observable, delay, of } from 'rxjs';
import { AnalysisFixture } from '../../core/models/analysis.model';
import { ANALYSIS_FIXTURES } from './analysis.fixtures';

// MOCK: mantiene la frontera de datos separada del componente. No hace llamadas HTTP.
@Injectable({ providedIn: 'root' })
export class AnalysisDemoService {
  getAnalysis(id: string | null, query: string | null, country: string | null, category: string | null): Observable<AnalysisFixture | null> {
    const fixture = id === 'demo-preview'
      ? this.matchPreview(query, country, category)
      : ANALYSIS_FIXTURES.find(item => item.id === id) ?? null;
    return of(fixture).pipe(delay(280));
  }

  private matchPreview(query: string | null, country: string | null, category: string | null): AnalysisFixture | null {
    if (country !== 'MX' || !query) return null;
    const normalized = query.trim().replace(/\s+/g, ' ').toLocaleLowerCase('es-MX');
    return ANALYSIS_FIXTURES.find(item =>
      item.product.toLocaleLowerCase('es-MX') === normalized && (!category || item.category === category)
    ) ?? null;
  }
}
