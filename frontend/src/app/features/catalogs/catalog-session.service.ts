import { computed, Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import type { CampaignConfiguration, StudioVariant } from '../../core/models/campaign.model';
import type { CatalogAsset, CatalogCampaign } from '../../core/models/catalog.model';
import { StudioApiService } from '../studio/studio-api.service';

interface StudioAssetInput {
  readonly variant: StudioVariant;
  readonly blob: Blob;
  readonly selected: boolean;
}

// Las imágenes son reales, pero el catálogo aún vive solo en memoria de la pestaña.
@Injectable({ providedIn: 'root' })
export class CatalogSessionService {
  private readonly api = inject(StudioApiService);
  private readonly items = signal<readonly CatalogCampaign[]>([]);
  private readonly hiddenIds = signal<ReadonlySet<string>>(new Set());
  private readonly originalFiles = new Map<string, File>();
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
        favorite: preview.selected,
      })),
      createdAt: new Date().toISOString(),
    };
    this.originalFiles.set(id, file);
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
    const asset = await this.createGeneratedAsset(campaign);
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
    const replacement = await this.createGeneratedAsset(campaign);
    if (!this.campaigns().some(item => item.id === campaignId)) {
      URL.revokeObjectURL(replacement.url);
      return;
    }
    this.items.update(items => items.map(item => item.id === campaignId
      ? { ...item, assets: item.assets.map(asset => asset.id === assetId
        ? { ...replacement, id: assetId, favorite: asset.favorite }
        : asset) }
      : item));
    URL.revokeObjectURL(previous.url);
  }

  private async createGeneratedAsset(campaign: CatalogCampaign): Promise<CatalogAsset> {
    const file = this.originalFiles.get(campaign.id);
    if (!file) throw new Error('La fotografía original ya no está disponible.');
    const sequence = ++this.assetCounter;
    const result = await firstValueFrom(this.api.generate(file, { ...campaign.configuration, variations: 1 }));
    const image = result.images[0];
    if (!image) throw new Error('No se recibió una imagen.');
    const blob = await fetch(`data:${image.mime_type};base64,${image.image_base64}`).then(response => response.blob());
    if (blob.type !== 'image/png' || !blob.size) throw new Error('La imagen recibida no es válida.');
    return {
      id: `${campaign.id}-generated-${sequence}`, label: `Escena ${sequence + campaign.assets.length}`,
      url: URL.createObjectURL(blob), format: 'PNG', favorite: false,
    };
  }
}
