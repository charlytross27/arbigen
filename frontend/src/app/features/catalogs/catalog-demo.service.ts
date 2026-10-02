import { computed, Injectable, signal } from '@angular/core';
import type { CampaignConfiguration, StudioVariant } from '../../core/models/campaign.model';
import type { CatalogAsset, CatalogCampaign } from '../../core/models/catalog.model';
import { demoTreatment } from '../studio/studio-demo.service';
import { renderStudioPreview } from '../studio/studio-preview';
import { CATALOG_FIXTURES } from './catalog.fixtures';

interface StudioAssetInput {
  readonly variant: StudioVariant;
  readonly blob: Blob;
  readonly selected: boolean;
}

// Almacenamiento mock en memoria de la pestaña. No usa localStorage ni backend.
@Injectable({ providedIn: 'root' })
export class CatalogDemoService {
  private readonly items = signal<readonly CatalogCampaign[]>(CATALOG_FIXTURES);
  private readonly hiddenIds = signal<ReadonlySet<string>>(new Set());
  private campaignCounter = 0;
  private assetCounter = 0;

  readonly campaigns = computed(() => this.items().filter(item => !this.hiddenIds().has(item.id)));
  readonly recentlyDeleted = signal<CatalogCampaign | null>(null);

  saveFromStudio(configuration: CampaignConfiguration, file: File, previews: readonly StudioAssetInput[]): CatalogCampaign {
    const selected = previews.filter(preview => preview.selected);
    const included = selected.length ? selected : previews;
    if (!included.length) throw new Error('No hay vistas previas para el catálogo.');
    const id = `session-catalog-${++this.campaignCounter}`;
    const originalFormat = file.type === 'image/jpeg' ? 'JPEG' : file.type === 'image/webp' ? 'WebP' : 'PNG';
    const campaign: CatalogCampaign = {
      id, name: `${configuration.productName.trim()} · ${configuration.style}`,
      productName: configuration.productName.trim(), configuration,
      originalUrl: URL.createObjectURL(file), originalName: file.name, originalFormat,
      assets: included.map((preview, index) => ({
        id: `${id}-asset-${index + 1}`, label: preview.variant.label,
        url: URL.createObjectURL(preview.blob), format: 'PNG' as const,
        favorite: preview.selected, local: true,
      })),
      createdAt: new Date().toISOString(), origin: 'session',
    };
    this.items.update(items => [campaign, ...items]);
    return campaign;
  }

  toggleFavorite(campaignId: string, assetId: string): void {
    this.items.update(items => items.map(item => item.id === campaignId
      ? { ...item, assets: item.assets.map(asset => asset.id === assetId ? { ...asset, favorite: !asset.favorite } : asset) }
      : item));
  }

  deleteCampaign(id: string): void {
    const campaign = this.campaigns().find(item => item.id === id);
    if (!campaign) return;
    this.hiddenIds.update(current => new Set([...current, id]));
    this.recentlyDeleted.set(campaign);
  }

  restoreDeleted(): void {
    const campaign = this.recentlyDeleted();
    if (!campaign) return;
    this.hiddenIds.update(current => {
      const next = new Set(current);
      next.delete(campaign.id);
      return next;
    });
    this.recentlyDeleted.set(null);
  }

  async addVariation(campaignId: string): Promise<void> {
    const campaign = this.campaigns().find(item => item.id === campaignId);
    if (!campaign || campaign.assets.length >= 4) throw new Error('Este catálogo ya tiene cuatro vistas.');
    const asset = await this.createLocalAsset(campaign);
    if (!this.campaigns().some(item => item.id === campaignId)) {
      URL.revokeObjectURL(asset.url);
      return;
    }
    this.items.update(items => items.map(item => item.id === campaignId
      ? { ...item, assets: [...item.assets, asset] }
      : item));
  }

  async regenerateAsset(campaignId: string, assetId: string): Promise<void> {
    const campaign = this.campaigns().find(item => item.id === campaignId);
    const previous = campaign?.assets.find(asset => asset.id === assetId);
    if (!campaign || !previous) throw new Error('La vista previa no está disponible.');
    const replacement = await this.createLocalAsset(campaign);
    if (!this.campaigns().some(item => item.id === campaignId)) {
      URL.revokeObjectURL(replacement.url);
      return;
    }
    this.items.update(items => items.map(item => item.id === campaignId
      ? { ...item, assets: item.assets.map(asset => asset.id === assetId
        ? { ...replacement, id: assetId, favorite: asset.favorite }
        : asset) }
      : item));
    if (previous.local) URL.revokeObjectURL(previous.url);
  }

  private async createLocalAsset(campaign: CatalogCampaign): Promise<CatalogAsset> {
    const sequence = ++this.assetCounter;
    const treatment = demoTreatment(campaign.configuration, sequence + campaign.assets.length);
    const variant: StudioVariant = { id: `catalog-${sequence}`, ...treatment };
    const blob = await renderStudioPreview(campaign.originalUrl, variant, campaign.configuration.aspectRatio);
    return {
      id: `${campaign.id}-local-${sequence}`, label: treatment.label,
      url: URL.createObjectURL(blob), format: 'PNG', favorite: false, local: true,
    };
  }
}
