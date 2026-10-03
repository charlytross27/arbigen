import { HttpClient } from '@angular/common/http';
import { effect, Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../../environments/environment';
import type { CampaignConfiguration, StudioVariant } from '../../core/models/campaign.model';
import type { CatalogCampaign } from '../../core/models/catalog.model';
import { AuthService } from '../../core/services/auth.service';

interface StudioAssetInput {
  readonly variant: StudioVariant;
  readonly blob: Blob;
  readonly selected: boolean;
}

export interface CatalogSourceInput {
  readonly analysisId: string;
  readonly productId: string;
}

interface CatalogResponse {
  id: string;
  name: string;
  product_name: string;
  configuration: {
    product_name: string; product_description: string; style: CampaignConfiguration['style'];
    scene: string; lighting: CampaignConfiguration['lighting'];
    aspect_ratio: CampaignConfiguration['aspectRatio']; variations: number;
  };
  original_url: string;
  original_name: string;
  original_mime_type: string;
  source: { analysis_id: string; product_id: string | null; product_title: string } | null;
  created_at: string;
  assets: { id: string; label: string; url: string; favorite: boolean }[];
}

function base64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('No pudimos leer la imagen.'));
    reader.onload = () => resolve(String(reader.result).split(',', 2)[1] ?? '');
    reader.readAsDataURL(blob);
  });
}

function mapCampaign(data: CatalogResponse, version = ''): CatalogCampaign {
  const format = data.original_mime_type === 'image/jpeg' ? 'JPEG' : data.original_mime_type === 'image/webp' ? 'WebP' : 'PNG';
  return {
    id: data.id, name: data.name, productName: data.product_name,
    source: data.source ? {
      analysisId: data.source.analysis_id,
      productId: data.source.product_id,
      productTitle: data.source.product_title,
    } : null,
    configuration: {
      productName: data.configuration.product_name,
      productDescription: data.configuration.product_description,
      style: data.configuration.style, scene: data.configuration.scene,
      lighting: data.configuration.lighting, aspectRatio: data.configuration.aspect_ratio,
      variations: data.configuration.variations,
    },
    originalUrl: data.original_url, originalName: data.original_name, originalFormat: format,
    createdAt: data.created_at,
    assets: data.assets.map(asset => ({
      id: asset.id, label: asset.label, url: asset.url + version,
      format: 'PNG' as const, favorite: asset.favorite,
    })),
  };
}

@Injectable({ providedIn: 'root' })
export class CatalogService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);
  private readonly baseUrl = `${environment.apiBasePath}/v1/catalogs`;
  readonly campaigns = signal<readonly CatalogCampaign[]>([]);
  readonly recentlyDeleted = signal<CatalogCampaign | null>(null);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  private cachedUserId: string | null = null;

  constructor() {
    effect(() => {
      const userId = this.auth.user()?.id ?? null;
      if (this.cachedUserId !== userId) {
        this.cachedUserId = userId;
        this.campaigns.set([]);
        this.recentlyDeleted.set(null);
      }
    });
  }

  async load(): Promise<void> {
    const userId = this.auth.user()?.id;
    this.loading.set(true);
    this.error.set(null);
    try {
      const campaigns = await firstValueFrom(this.http.get<CatalogResponse[]>(this.baseUrl));
      if (userId === this.auth.user()?.id) this.campaigns.set(campaigns.map(item => mapCampaign(item)));
    } catch {
      this.error.set('No pudimos cargar tus catálogos. Inténtalo de nuevo.');
    } finally {
      this.loading.set(false);
    }
  }

  async saveFromStudio(configuration: CampaignConfiguration, file: File, previews: readonly StudioAssetInput[], source: CatalogSourceInput | null): Promise<CatalogCampaign> {
    const selected = previews.filter(preview => preview.selected);
    const included = selected.length ? selected : previews;
    if (!included.length) throw new Error('No hay vistas previas para el catálogo.');
    const assets = await Promise.all(included.map(async preview => ({
      label: preview.variant.label, image_base64: await base64(preview.blob), favorite: preview.selected,
    })));
    const response = await firstValueFrom(this.http.post<CatalogResponse>(this.baseUrl, {
      configuration: {
        image_base64: await base64(file), image_mime_type: file.type,
        product_name: configuration.productName.trim(),
        product_description: configuration.productDescription.trim(),
        style: configuration.style, scene: configuration.scene.trim(),
        lighting: configuration.lighting, aspect_ratio: configuration.aspectRatio,
        variations: configuration.variations,
      }, original_name: file.name, assets,
      source: source ? { analysis_id: source.analysisId, product_id: source.productId } : null,
    }, { headers: this.auth.csrfHeaders() }));
    const campaign = mapCampaign(response);
    this.campaigns.update(items => [campaign, ...items]);
    return campaign;
  }

  async toggleFavorite(campaignId: string, assetId: string): Promise<void> {
    const campaign = this.campaigns().find(item => item.id === campaignId);
    const asset = campaign?.assets.find(item => item.id === assetId);
    if (!asset) return;
    const favorite = !asset.favorite;
    await firstValueFrom(this.http.put(`${this.baseUrl}/${campaignId}/assets/${assetId}/favorite`,
      { favorite }, { headers: this.auth.csrfHeaders() }));
    this.campaigns.update(items => items.map(item => item.id === campaignId
      ? { ...item, assets: item.assets.map(current => current.id === assetId ? { ...current, favorite } : current) }
      : item));
  }

  async deleteCampaign(id: string): Promise<void> {
    const campaign = this.campaigns().find(item => item.id === id);
    if (!campaign) return;
    await firstValueFrom(this.http.delete(`${this.baseUrl}/${id}`, { headers: this.auth.csrfHeaders() }));
    this.campaigns.update(items => items.filter(item => item.id !== id));
    this.recentlyDeleted.set(campaign);
  }

  async restoreDeleted(): Promise<void> {
    const campaign = this.recentlyDeleted();
    if (!campaign) return;
    const result = await firstValueFrom(this.http.post<CatalogResponse>(`${this.baseUrl}/${campaign.id}/restore`,
      {}, { headers: this.auth.csrfHeaders() }));
    this.campaigns.update(items => [mapCampaign(result), ...items]);
    this.recentlyDeleted.set(null);
  }

  async addVariation(campaignId: string): Promise<void> {
    const result = await firstValueFrom(this.http.post<CatalogResponse>(`${this.baseUrl}/${campaignId}/assets`,
      {}, { headers: this.auth.csrfHeaders() }));
    this.replace(mapCampaign(result));
  }

  async regenerateAsset(campaignId: string, assetId: string): Promise<void> {
    const result = await firstValueFrom(this.http.post<CatalogResponse>(`${this.baseUrl}/${campaignId}/assets/${assetId}/regenerate`,
      {}, { headers: this.auth.csrfHeaders() }));
    this.replace(mapCampaign(result, `?v=${Date.now()}`));
  }

  private replace(campaign: CatalogCampaign): void {
    this.campaigns.update(items => items.map(item => item.id === campaign.id ? campaign : item));
  }
}
