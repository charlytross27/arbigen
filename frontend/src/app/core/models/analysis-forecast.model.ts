export interface ForecastPoint {
  readonly date: string;
  readonly value: string;
  readonly lower: string;
  readonly upper: string;
}

export interface ForecastReport {
  readonly model_version: string;
  readonly status: 'ready' | 'insufficient_data' | 'censored_data' | 'irregular_series' | 'low_skill';
  readonly source_point_count: number;
  readonly used_point_count: number;
  readonly censored_count: number;
  readonly frequency: 'daily' | 'weekly' | 'monthly' | null;
  readonly selected_model: 'naive' | 'moving_average_3' | 'drift' | 'seasonal_naive' | null;
  readonly direction: 'creciente' | 'estable' | 'decreciente' | null;
  readonly seasonal_signal: boolean;
  readonly backtest_mae: string | null;
  readonly naive_mae: string | null;
  readonly candidate_mae: Readonly<Record<string, string>>;
  readonly backtest_origins: number;
  readonly horizon: number;
  readonly predictions: readonly ForecastPoint[];
  readonly reason: string | null;
}
