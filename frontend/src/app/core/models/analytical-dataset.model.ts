import { MarketplaceSearch } from './marketplace-product.model';
import { TrendPoint } from './trends.model';

export interface ProductQuality {
  readonly source_count: number;
  readonly duplicate_count: number;
  readonly missing_title_count: number;
  readonly missing_price_count: number;
  readonly invalid_price_count: number;
  readonly invalid_currency_count: number;
  readonly included_count: number;
}

export interface AnalyticalProduct {
  readonly id: string;
  readonly external_id: string | null;
  readonly title: string;
  readonly price: string;
  readonly currency: string;
  readonly permalink: string | null;
  readonly image_url: string | null;
  readonly attributes: Readonly<Record<string, string>>;
}

export interface AnalyticalDataset {
  readonly country: 'MX' | 'CO' | 'AR';
  readonly trend_source: string | null;
  readonly trend_imported_at: string | null;
  readonly snapshot: MarketplaceSearch | null;
  readonly prepared_at: string | null;
  readonly quality: ProductQuality | null;
  readonly products: readonly AnalyticalProduct[];
  readonly trends: readonly TrendPoint[];
}
