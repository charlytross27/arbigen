import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { CreateAnalysisRequest, SavedAnalysis, SavedAnalysisPage } from '../models/saved-analysis.model';
import { TrendsSeries } from '../models/trends.model';
import { AnalyticalDataset } from '../models/analytical-dataset.model';
import { AnalysisFeatures } from '../models/analysis-features.model';
import { ClusterReport } from '../models/analysis-clusters.model';
import { ForecastReport } from '../models/analysis-forecast.model';
import { OpportunityScoreReport, ScorePreviewRequest } from '../models/opportunity-score.model';
import { DashboardData, DashboardPeriod } from '../models/dashboard.model';

const WORKSPACE_KEY = 'arbigen-demo-workspace-id';
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

@Injectable({ providedIn: 'root' })
export class AnalysisApiService {
  private readonly http = inject(HttpClient);
  private readonly workspaceId = this.loadWorkspaceId();
  private readonly baseUrl = '/api/v1/analyses';

  create(payload: CreateAnalysisRequest): Observable<SavedAnalysis> {
    return this.http.post<SavedAnalysis>(this.baseUrl, payload, { headers: this.headers() });
  }

  list(limit = 20, offset = 0): Observable<SavedAnalysisPage> {
    return this.http.get<SavedAnalysisPage>(this.baseUrl, {
      headers: this.headers(), params: { limit, offset },
    });
  }

  dashboard(days: DashboardPeriod): Observable<DashboardData> {
    return this.http.get<DashboardData>('/api/v1/dashboard', { headers: this.headers(), params: { days } });
  }

  get(id: string): Observable<SavedAnalysis> {
    return this.http.get<SavedAnalysis>(`${this.baseUrl}/${encodeURIComponent(id)}`, { headers: this.headers() });
  }

  dataset(id: string): Observable<AnalyticalDataset> {
    return this.http.get<AnalyticalDataset>(`${this.baseUrl}/${encodeURIComponent(id)}/dataset`, { headers: this.headers() });
  }

  features(id: string): Observable<AnalysisFeatures> {
    return this.http.get<AnalysisFeatures>(`${this.baseUrl}/${encodeURIComponent(id)}/features`, { headers: this.headers() });
  }

  clusters(id: string): Observable<ClusterReport> {
    return this.http.get<ClusterReport>(`${this.baseUrl}/${encodeURIComponent(id)}/clusters`, { headers: this.headers() });
  }

  forecast(id: string): Observable<ForecastReport> {
    return this.http.get<ForecastReport>(`${this.baseUrl}/${encodeURIComponent(id)}/forecast`, { headers: this.headers() });
  }

  opportunityScore(id: string): Observable<OpportunityScoreReport> {
    return this.http.get<OpportunityScoreReport>(`${this.baseUrl}/${encodeURIComponent(id)}/opportunity-score`, { headers: this.headers() });
  }

  previewOpportunityScore(id: string, payload: ScorePreviewRequest): Observable<OpportunityScoreReport> {
    return this.http.post<OpportunityScoreReport>(`${this.baseUrl}/${encodeURIComponent(id)}/opportunity-score/preview`, payload, { headers: this.headers() });
  }

  refreshDataset(id: string): Observable<AnalyticalDataset> {
    return this.http.post<AnalyticalDataset>(`${this.baseUrl}/${encodeURIComponent(id)}/dataset/refresh`, null, { headers: this.headers() });
  }

  reprocessDataset(id: string): Observable<AnalyticalDataset> {
    return this.http.post<AnalyticalDataset>(`${this.baseUrl}/${encodeURIComponent(id)}/dataset/reprocess`, null, { headers: this.headers() });
  }

  trends(id: string): Observable<TrendsSeries> {
    return this.http.get<TrendsSeries>(`${this.baseUrl}/${encodeURIComponent(id)}/trends`, { headers: this.headers() });
  }

  importTrends(id: string, csv: string): Observable<TrendsSeries> {
    return this.http.post<TrendsSeries>(`${this.baseUrl}/${encodeURIComponent(id)}/trends`, csv, {
      headers: this.headers().set('Content-Type', 'text/csv; charset=utf-8'),
    });
  }

  private headers(): HttpHeaders {
    return new HttpHeaders({ 'X-Demo-Workspace-ID': this.workspaceId });
  }

  private loadWorkspaceId(): string {
    try {
      const existing = window.localStorage.getItem(WORKSPACE_KEY);
      if (existing && UUID_PATTERN.test(existing)) return existing;
      const created = window.crypto.randomUUID();
      window.localStorage.setItem(WORKSPACE_KEY, created);
      return created;
    } catch {
      // La demo también funciona si el navegador bloquea localStorage; no persiste su ID.
      return window.crypto.randomUUID();
    }
  }
}
