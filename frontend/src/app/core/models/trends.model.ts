export interface TrendPoint {
  readonly date: string;
  readonly value: number | null;
  readonly less_than_one: boolean;
}

export interface TrendsSeries {
  readonly source: string | null;
  readonly imported_at: string | null;
  readonly points: readonly TrendPoint[];
}
