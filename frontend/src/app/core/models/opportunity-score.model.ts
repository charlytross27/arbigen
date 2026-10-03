export interface ScoreWeights {
  growth: number;
  stability: number;
  margin: number;
  roi: number;
}

export interface FinancialScenario {
  sale_price: number | null;
  product_cost: number | null;
  shipping_cost: number | null;
  commission_pct: number | null;
  other_costs: number | null;
}

export interface ScorePreviewRequest {
  financial: FinancialScenario;
  weights: ScoreWeights;
}

export interface OpportunityScoreReport {
  model_version: string;
  status: 'ready' | 'incomplete';
  score: string | null;
  currency: string;
  weights: Readonly<Record<keyof ScoreWeights, string>>;
  components: Readonly<Record<keyof ScoreWeights, string | null>>;
  missing: string[];
  warnings: string[];
  limitations: string[];
  evidence: {
    product_count: number;
    source_count: number | null;
    price_coverage_pct: string | null;
    trend_point_count: number;
    trend_observed_count: number;
    trend_source: string | null;
    trend_last_date: string | null;
    market_fetched_date: string | null;
    forecast_mae: string | null;
    forecast_naive_mae: string | null;
    forecast_backtest_origins: number;
  };
  sensitivity: ReadonlyArray<{
    case: 'price_down_10pct' | 'fixed_costs_up_10pct';
    sale_price: string;
    unit_profit: string;
    score: string | null;
  }>;
  commission_cost: string | null;
  total_cost: string | null;
  unit_profit: string | null;
  margin_pct: string | null;
  roi_pct: string | null;
}
