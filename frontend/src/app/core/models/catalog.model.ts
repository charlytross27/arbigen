import type { CampaignConfiguration } from './campaign.model';

export interface CatalogAsset {
  readonly id: string;
  readonly label: string;
  readonly url: string;
  readonly format: 'PNG' | 'SVG';
  readonly favorite: boolean;
  readonly local: boolean;
}

export interface CatalogCampaign {
  readonly id: string;
  readonly name: string;
  readonly productName: string;
  readonly configuration: CampaignConfiguration;
  readonly originalUrl: string;
  readonly originalName: string;
  readonly originalFormat: 'PNG' | 'JPEG' | 'WebP' | 'SVG';
  readonly assets: readonly CatalogAsset[];
  readonly createdAt: string;
  readonly origin: 'example' | 'session';
}
