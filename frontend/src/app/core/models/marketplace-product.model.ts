export interface MarketplaceProduct {
  readonly id: string;
  readonly title: string;
  readonly price: string | null;
  readonly currency: string | null;
  readonly permalink: string | null;
  readonly image_url: string | null;
}

export interface MarketplaceSearch {
  readonly source: 'listings' | 'catalog';
  readonly site_id: string;
  readonly query: string;
  readonly fetched_at: string;
  readonly items: readonly MarketplaceProduct[];
}
