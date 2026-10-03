import { Component, computed, inject, OnDestroy, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';
import { HttpErrorResponse } from '@angular/common/http';
import { CampaignAspectRatio, CampaignConfiguration, CampaignLighting, CampaignStyle, StudioVariant } from '../../core/models/campaign.model';
import { IconComponent } from '../../shared/icon.component';
import { CatalogService, CatalogSourceInput } from '../catalogs/catalog.service';
import { StudioApiService, StudioGenerationInterruptedError, StudioGenerationPendingError, StudioGenerationResponse } from './studio-api.service';
import { normalizedImageFile } from './image-file';

interface SourceImage {
  readonly file: File;
  readonly name: string;
  readonly size: number;
  readonly url: string;
}

type StudioStatus = 'idle' | 'loading' | 'success' | 'error';

const MAX_FILE_SIZE = 10 * 1024 * 1024;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

@Component({
  selector: 'app-studio', standalone: true,
  imports: [RouterLink, IconComponent],
  templateUrl: './studio.component.html', styleUrl: './studio.component.scss',
})
export class StudioComponent implements OnDestroy {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(StudioApiService);
  private readonly catalogs = inject(CatalogService);
  private generationSubscription: Subscription | null = null;
  private uploadVersion = 0;
  private generationVersion = 0;
  private destroyed = false;

  readonly styles: readonly CampaignStyle[] = ['Minimalista', 'Premium', 'Lifestyle', 'Urbano', 'Natural', 'Studio'];
  readonly lightingOptions: readonly CampaignLighting[] = ['Natural', 'Cálida', 'Fría', 'Estudio', 'Dramática'];
  readonly ratios: readonly CampaignAspectRatio[] = ['1:1', '4:5', '16:9'];

  readonly source = signal<SourceImage | null>(null);
  readonly catalogSource: CatalogSourceInput | null = (() => {
    const analysisId = this.route.snapshot.queryParamMap.get('analysis');
    const productId = this.route.snapshot.queryParamMap.get('productId');
    return analysisId && productId && UUID_PATTERN.test(analysisId) && UUID_PATTERN.test(productId)
      ? { analysisId, productId } : null;
  })();
  readonly configuration = signal<CampaignConfiguration>({
    productName: (this.route.snapshot.queryParamMap.get('product') ?? '').slice(0, 80),
    productDescription: '', style: 'Minimalista', scene: 'Cafetería moderna',
    lighting: 'Natural', aspectRatio: '1:1', variations: 1,
  });
  readonly status = signal<StudioStatus>('idle');
  readonly variants = signal<readonly StudioVariant[]>([]);
  readonly downloadUrls = signal<ReadonlyMap<string, string>>(new Map());
  readonly draftId = signal<string | null>(null);
  readonly savedIds = signal<ReadonlySet<string>>(new Set());
  readonly saveError = signal<string | null>(null);
  readonly saving = signal(false);
  readonly generationError = signal<string | null>(null);
  readonly retryState = signal<'normal' | 'pending' | 'interrupted'>('normal');
  readonly configurationError = signal(false);
  readonly fileError = signal<string | null>(null);
  readonly formTouched = signal(false);
  readonly canGenerate = computed(() => {
    const config = this.configuration();
    return !!this.source() && !this.fileError() && config.productName.trim().length >= 2 && config.scene.trim().length >= 3 && this.status() !== 'loading';
  });

  async onFileChange(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (file) await this.acceptFile(file);
  }

  private async acceptFile(file: File): Promise<void> {
    const version = ++this.uploadVersion;
    this.fileError.set(null);
    if (file.size === 0 || file.size > MAX_FILE_SIZE) {
      this.fileError.set('La imagen debe tener contenido y pesar como máximo 10 MB.');
      return;
    }

    let url: string | null = null;
    try {
      const normalized = await normalizedImageFile(file);
      if (!normalized) {
        if (version === this.uploadVersion && !this.destroyed)
          this.fileError.set('Este archivo no es PNG, JPEG ni WebP. Convierte la imagen a uno de esos formatos y vuelve a subirla.');
        return;
      }
      if (this.destroyed || version !== this.uploadVersion) return;
      url = URL.createObjectURL(normalized);
      const image = new Image();
      image.src = url;
      await image.decode();
      if (this.destroyed || version !== this.uploadVersion) {
        URL.revokeObjectURL(url);
        return;
      }
      this.invalidateResults();
      const previous = this.source();
      this.source.set({ file: normalized, name: normalized.name, size: normalized.size, url });
      if (previous) URL.revokeObjectURL(previous.url);
    } catch {
      if (url) URL.revokeObjectURL(url);
      if (version === this.uploadVersion && !this.destroyed) this.fileError.set('No pudimos abrir esa imagen. Prueba con otro archivo.');
    }
  }

  removeImage(): void {
    ++this.uploadVersion;
    this.invalidateResults();
    const previous = this.source();
    this.source.set(null);
    if (previous) URL.revokeObjectURL(previous.url);
    this.fileError.set(null);
  }

  updateText(field: 'productName' | 'productDescription' | 'scene', event: Event): void {
    const value = (event.target as HTMLInputElement | HTMLTextAreaElement).value;
    this.configuration.update(config => ({ ...config, [field]: value }));
    this.invalidateResults();
  }

  updateStyle(style: CampaignStyle): void {
    this.configuration.update(config => ({ ...config, style }));
    this.invalidateResults();
  }

  updateLighting(event: Event): void {
    const lighting = (event.target as HTMLSelectElement).value as CampaignLighting;
    this.configuration.update(config => ({ ...config, lighting }));
    this.invalidateResults();
  }

  updateRatio(aspectRatio: CampaignAspectRatio): void {
    this.configuration.update(config => ({ ...config, aspectRatio }));
    this.invalidateResults();
  }

  updateVariations(event: Event): void {
    const variations = Number((event.target as HTMLSelectElement).value);
    if (!Number.isInteger(variations) || variations < 1 || variations > 4) return;
    this.configuration.update(config => ({ ...config, variations }));
    this.invalidateResults();
  }

  generate(retry = false): void {
    if (!retry && this.retryState() === 'pending') return;
    this.formTouched.set(true);
    if (!this.source()) this.fileError.set('Sube una fotografía para generar las imágenes.');
    if (!this.canGenerate()) return;

    this.cancelPending();
    this.clearDownloads();
    this.variants.set([]);
    this.savedIds.set(new Set());
    this.status.set('loading');
    this.generationError.set(null);
    this.retryState.set('normal');
    this.configurationError.set(false);
    const version = ++this.generationVersion;
    this.generationSubscription = this.api.generate(this.source()!.file, this.configuration(), retry).subscribe({
      next: result => { void this.prepareVariants(result, version); },
      error: (error: unknown) => {
        if (version !== this.generationVersion || this.destroyed) return;
        this.generationError.set(error instanceof HttpErrorResponse
          ? error.error?.error?.message ?? 'No pudimos generar las imágenes. Inténtalo de nuevo.'
          : error instanceof Error ? error.message : 'No pudimos generar las imágenes. Inténtalo de nuevo.');
        this.configurationError.set(error instanceof HttpErrorResponse && error.status === 503);
        this.retryState.set(error instanceof StudioGenerationPendingError ? 'pending'
          : error instanceof StudioGenerationInterruptedError ? 'interrupted' : 'normal');
        this.status.set('error');
      },
    });
  }

  toggleSaved(id: string): void {
    this.savedIds.update(current => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  async createCatalog(): Promise<void> {
    const image = this.source();
    if (!image || this.status() !== 'success' || this.saving()) return;
    this.saveError.set(null);
    const draftId = this.draftId();
    if (!draftId) { this.saveError.set('No pudimos preparar el catálogo. Regenera las vistas previas.'); return; }
    try {
      this.saving.set(true);
      const campaign = await this.catalogs.saveFromDraft(draftId, [...this.savedIds()], this.catalogSource);
      await this.router.navigate(['/catalogs', campaign.id]);
    } catch (error) {
      this.saveError.set(error instanceof HttpErrorResponse
        ? error.error?.error?.message ?? 'No pudimos guardar el catálogo. Inténtalo de nuevo.'
        : 'No pudimos preparar el catálogo. Inténtalo de nuevo.');
    } finally {
      this.saving.set(false);
    }
  }

  fileSize(size: number): string { return `${Math.round(size / 1024)} KB`; }

  private prepareVariants(result: StudioGenerationResponse, version: number): void {
    const urls = new Map<string, string>();
    const variants: StudioVariant[] = [];
    try {
      for (const generated of result.images) {
        if (!generated.id || generated.mime_type !== 'image/png' || !generated.url.startsWith('/api/')) throw new Error('Imagen inválida.');
        const variant: StudioVariant = { id: generated.id, label: generated.label };
        urls.set(variant.id, generated.url);
        variants.push(variant);
      }
      if (version !== this.generationVersion || this.destroyed) return;
      this.draftId.set(result.draft_id);
      this.downloadUrls.set(urls);
      this.variants.set(variants);
      this.status.set('success');
    } catch {
      if (version === this.generationVersion && !this.destroyed) {
        this.generationError.set('No pudimos preparar las imágenes recibidas. Inténtalo de nuevo.');
        this.status.set('error');
      }
    }
  }

  private invalidateResults(): void {
    ++this.generationVersion;
    this.cancelPending();
    this.status.set('idle');
    this.variants.set([]);
    this.savedIds.set(new Set());
    this.saveError.set(null);
    this.generationError.set(null);
    this.retryState.set('normal');
    this.configurationError.set(false);
    this.clearDownloads();
  }

  private clearDownloads(): void {
    this.downloadUrls.set(new Map());
    this.draftId.set(null);
  }

  private cancelPending(): void {
    this.generationSubscription?.unsubscribe();
    this.generationSubscription = null;
  }

  ngOnDestroy(): void {
    this.destroyed = true;
    ++this.uploadVersion;
    this.cancelPending();
    this.clearDownloads();
    const image = this.source();
    if (image) URL.revokeObjectURL(image.url);
  }
}
