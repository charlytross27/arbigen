export interface SavedFinancialScenario {
  readonly analysis_id: string;
  readonly product_id: string | null;
  readonly product_external_id: string | null;
  readonly product_title: string;
  readonly reference_price: string;
  readonly currency: string;
  readonly sale_price: string;
  readonly product_cost: string;
  readonly shipping_cost: string;
  readonly commission_pct: string;
  readonly other_costs: string;
  readonly commission_cost: string;
  readonly total_cost: string;
  readonly unit_profit: string;
  readonly margin_pct: string | null;
  readonly roi_pct: string | null;
  readonly break_even_price: string | null;
  readonly updated_at: string;
}

export interface SaveFinancialScenarioRequest {
  readonly product_id: string;
  readonly sale_price: number;
  readonly product_cost: number;
  readonly shipping_cost: number;
  readonly commission_pct: number;
  readonly other_costs: number;
}
