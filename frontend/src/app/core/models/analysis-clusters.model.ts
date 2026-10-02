export interface ClusterExample {
  readonly external_id: string;
  readonly title: string;
  readonly price: string;
}

export interface ClusterSegment {
  readonly number: number;
  readonly label: string;
  readonly count: number;
  readonly share_pct: string;
  readonly price_min: string;
  readonly price_max: string;
  readonly price_mean: string;
  readonly price_median: string;
  readonly material_hints: Readonly<Record<string, number>>;
  readonly examples: readonly ClusterExample[];
}

export interface ClusterReport {
  readonly model_version: string;
  readonly country: 'MX' | 'CO' | 'AR';
  readonly currency: string;
  readonly status: 'ready' | 'insufficient_data' | 'no_separation';
  readonly product_count: number;
  readonly clustered_count: number;
  readonly excluded_outlier_count: number;
  readonly selected_k: number | null;
  readonly silhouette: string | null;
  readonly segments: readonly ClusterSegment[];
  readonly reason: string | null;
}
