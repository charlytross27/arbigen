export interface MarketFeatures {
  readonly currency: string;
  readonly source_count: number | null;
  readonly priced_count: number;
  readonly price_coverage_pct: string | null;
  readonly price_min: string | null;
  readonly price_max: string | null;
  readonly price_mean: string | null;
  readonly price_median: string | null;
  readonly price_stddev: string | null;
  readonly material_hints: Readonly<Record<string, number>>;
}

export interface TrendFeatures {
  readonly point_count: number;
  readonly observed_count: number;
  readonly censored_count: number;
  readonly observed_coverage_pct: string | null;
  readonly mean_index: string | null;
  readonly volatility_index: string | null;
  readonly moving_average_3: string | null;
  readonly growth_3v3_pct: string | null;
  readonly momentum_3v3: string | null;
  readonly acceleration_3v3: string | null;
}

export interface AnalysisFeatures {
  readonly country: 'MX' | 'CO' | 'AR';
  readonly market: MarketFeatures;
  readonly trend: TrendFeatures;
}
