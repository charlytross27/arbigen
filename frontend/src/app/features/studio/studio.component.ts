import { Component, computed, inject, OnDestroy, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';
import { HttpErrorResponse } from '@angular/common/http';
import { CampaignAspectRatio, CampaignConfiguration, CampaignLighting, CampaignStyle, StudioVariant } from '../../core/models/campaign.model';
import { IconComponent } from '../../shared/icon.component';
import { CatalogSessionService } from '../catalogs/catalog-session.service';
import { StudioApiService, StudioGenerationResponse } from './studio-api.service';

interface SourceImage {
  readonly file: File;
  readonly name: string;
  readonly size: number;
  readonly url: string;
}

type StudioStatus = 'idle' | 'loading' | 'success' | 'error';

const MAX_FILE_SIZE = 10 * 1024 * 1024;
const ACCEPTED_TYPES = new Set(['image/png', 'image/jpeg', 'image/webp']);

@Component({
  selector: 'app-studio', standalone: true,
  imports: [RouterLink, IconComponent],
  templateUrl: './studio.component.html', styleUrl: './studio.component.scss',
})
export class StudioComponent implements OnDestroy {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(StudioApiService);
  private readonly catalogs = inject(CatalogSessionService);
  private generationSubscription: Subscription | null = null;
  private uploadVersion = 0;
  private generationVersion = 0;
  private destroyed = false;

  readonly styles: readonly CampaignStyle[] = ['Minimalista', 'Premium', 'Lifestyle', 'Urbano', 'Natural', 'Studio'];
  readonly lightingOptions: readonly CampaignLighting[] = ['Natural', 'Cálida', 'Fría', 'Estudio', 'Dramática'];
  readonly ratios: readonly CampaignAspectRatio[] = ['1:1', '4:5', '16:9'];

  readonly source = signal<SourceImage | null>(null);
  readonly configuration = signal<CampaignConfiguration>({
    productName: (this.route.snapshot.queryParamMap.get('product') ?? '').slice(0, 80),
    productDescription: '', style: 'Minimalista', scene: 'Cafetería moderna',
    lighting: 'Natural', aspectRatio: '1:1', variations: 2,
  });
  readonly status = signal<StudioStatus>('idle');
  readonly variants = signal<readonly StudioVariant[]>([]);
  readonly downloadUrls = signal<ReadonlyMap<string, string>>(new Map());
  readonly previewBlobs = signal<ReadonlyMap<string, Blob>>(new Map());
  readonly savedIds = signal<ReadonlySet<string>>(new Set());
  readonly saveError = signal<string | null>(null);
  readonly generationError = signal<string | null>(null);
  readonly fileError = signal<string | null>(null);
  readonly formTouched = signal(false);
  readonly canGenerate = computed(() => {
    const config = this.configuration();
    return !!this.source() && config.productName.trim().length >= 2 && config.scene.trim().length >= 3 && this.status() !== 'loading';
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
    if (!ACCEPTED_TYPES.has(file.type)) {
      this.fileError.set('Usa una imagen PNG, JPEG o WebP.');
      return;
    }
    if (file.size === 0 || file.size > MAX_FILE_SIZE) {
      this.fileError.set('La imagen debe tener contenido y pesar como máximo 10 MB.');
      return;
    }

    const url = URL.createObjectURL(file);
    try {
      const image = new Image();
      image.src = url;
      await image.decode();
      if (this.destroyed || version !== this.uploadVersion) {
        URL.revokeObjectURL(url);
        return;
      }
      this.invalidateResults();
      const previous = this.source();
      this.source.set({ file, name: file.name, size: file.size, url });
      if (previous) URL.revokeObjectURL(previous.url);
    } catch {
      URL.revokeObjectURL(url);
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

  generate(): void {
    this.formTouched.set(true);
    if (!this.source()) this.fileError.set('Sube una fotografía para generar las imágenes.');
    if (!this.canGenerate()) return;

    this.cancelPending();
    this.clearDownloads();
    this.variants.set([]);
    this.savedIds.set(new Set());
    this.status.set('loading');
    this.generationError.set(null);
    const version = ++this.generationVersion;
    this.generationSubscription = this.api.generate(this.source()!.file, this.configuration()).subscribe({
      next: result => { void this.prepareVariants(result, version); },
      error: (error: HttpErrorResponse) => {
        if (version !== this.generationVersion || this.destroyed) return;
        this.generationError.set(error.error?.error?.message ?? 'No pudimos generar las imágenes. Inténtalo de nuevo.');
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

  createCatalog(): void {
    const image = this.source();
    if (!image || this.status() !== 'success') return;
    this.saveError.set(null);
    const previews: { variant: StudioVariant; blob: Blob; selected: boolean }[] = [];
    for (const variant of this.variants()) {
      const blob = this.previewBlobs().get(variant.id);
      if (!blob) {
        this.saveError.set('No pudimos preparar el catálogo. Regenera las vistas previas.');
        return;
      }
      previews.push({ variant, blob, selected: this.savedIds().has(variant.id) });
    }
    try {
      const campaign = this.catalogs.saveFromStudio(this.configuration(), image.file, previews);
      void this.router.navigate(['/catalogs', campaign.id]);
    } catch {
      this.saveError.set('No pudimos crear el catálogo.');
    }
  }

  fileSize(size: number): string { return `${Math.round(size / 1024)} KB`; }

  private async prepareVariants(result: StudioGenerationResponse, version: number): Promise<void> {
    const urls = new Map<string, string>();
    const blobs = new Map<string, Blob>();
    const variants: StudioVariant[] = [];
    try {
      for (const [index, generated] of result.images.entries()) {
        const variant: StudioVariant = { id: `${version}-${index + 1}`, label: `Escena ${index + 1}` };
        const blob = await fetch(`data:${generated.mime_type};base64,${generated.image_base64}`).then(response => response.blob());
        if (blob.type !== 'image/png' || !blob.size) throw new Error('Imagen inválida.');
        urls.set(variant.id, URL.createObjectURL(blob));
        blobs.set(variant.id, blob);
        variants.push(variant);
      }
      if (version !== this.generationVersion || this.destroyed) {
        for (const url of urls.values()) URL.revokeObjectURL(url);
        return;
      }
      this.downloadUrls.set(urls);
      this.previewBlobs.set(blobs);
      this.variants.set(variants);
      this.status.set('success');
    } catch {
      for (const url of urls.values()) URL.revokeObjectURL(url);
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
    this.clearDownloads();
  }

  private clearDownloads(): void {
    for (const url of this.downloadUrls().values()) URL.revokeObjectURL(url);
    this.downloadUrls.set(new Map());
    this.previewBlobs.set(new Map());
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
