import type { CampaignConfiguration } from './campaign.model';

export interface CatalogAsset {
  readonly id: string;
  readonly label: string;
  readonly url: string;
  readonly format: 'PNG';
  readonly favorite: boolean;
}

export interface CatalogSource {
  readonly analysisId: string;
  readonly productId: string | null;
  readonly productTitle: string;
}

export interface CatalogCampaign {
  readonly id: string;
  readonly name: string;
  readonly productName: string;
  readonly source: CatalogSource | null;
  readonly configuration: CampaignConfiguration;
  readonly originalUrl: string;
  readonly originalName: string;
  readonly originalFormat: 'PNG' | 'JPEG' | 'WebP';
  readonly assets: readonly CatalogAsset[];
  readonly createdAt: string;
}
