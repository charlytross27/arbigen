export type DashboardPeriod = 7 | 30;

export interface DashboardAnalysis {
  readonly id: string;
  readonly query: string;
  readonly country: 'MX' | 'CO' | 'AR';
  readonly category: string | null;
  readonly created_at: string;
  readonly prepared_at: string | null;
  readonly product_count: number;
  readonly trend_point_count: number;
}

export interface DashboardActivity {
  readonly analysis_id: string;
  readonly query: string;
  readonly country: 'MX' | 'CO' | 'AR';
  readonly kind: 'analysis_saved' | 'products_prepared' | 'trends_imported';
  readonly occurred_at: string;
}

export interface DashboardData {
  readonly period_days: DashboardPeriod;
  readonly analysis_count: number;
  readonly prepared_count: number;
  readonly priced_product_count: number;
  readonly trends_count: number;
  readonly recent: readonly DashboardAnalysis[];
  readonly activity: readonly DashboardActivity[];
}
