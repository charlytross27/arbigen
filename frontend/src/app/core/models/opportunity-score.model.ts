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
  limitations: string[];
  commission_cost: string | null;
  total_cost: string | null;
  unit_profit: string | null;
  margin_pct: string | null;
  roi_pct: string | null;
}
