export interface ListingSignals {
  readonly previous_price: string | null;
  readonly free_shipping: boolean | null;
  readonly official_store: boolean | null;
  readonly international_purchase: boolean | null;
  readonly stock_available: boolean | null;
  readonly sold_quantity: number | null;
  readonly review_count: number | null;
  readonly rating: string | null;
  readonly position: number | null;
  readonly seller_id: string | null;
  readonly brand: string | null;
  readonly category_id: string | null;
  readonly domain_id: string | null;
  readonly catalog_product_id: string | null;
  readonly variation_id: string | null;
}

export interface MarketplaceProduct {
  readonly id: string;
  readonly title: string;
  readonly price: string | null;
  readonly currency: string | null;
  readonly permalink: string | null;
  readonly image_url: string | null;
  readonly signals: ListingSignals;
}

export interface MarketplaceSearch {
  readonly source: 'listings' | 'catalog';
  readonly site_id: string;
  readonly query: string;
  readonly fetched_at: string;
  readonly items: readonly MarketplaceProduct[];
  readonly reported_total_results: number | null;
}
