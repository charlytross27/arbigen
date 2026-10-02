export type AnalysisCountry = 'MX' | 'CO' | 'AR';
export type AnalysisPeriod = '3m' | '6m' | '12m';

export interface ExploreRequest {
  readonly query: string;
  readonly market: 'Mercado Libre';
  readonly country: AnalysisCountry;
  readonly category: string | null;
  readonly period: AnalysisPeriod;
}

export interface CreateAnalysisRequest {
  readonly query: string;
  readonly country: AnalysisCountry;
  readonly category: string | null;
  readonly period_months: 3 | 6 | 12;
}

export interface SavedAnalysis {
  readonly id: string;
  readonly query: string;
  readonly country: AnalysisCountry;
  readonly category: string | null;
  readonly period_months: number;
  readonly status: string;
  readonly created_at: string;
}

export interface SavedAnalysisPage {
  readonly items: readonly SavedAnalysis[];
  readonly total: number;
  readonly limit: number;
  readonly offset: number;
}
