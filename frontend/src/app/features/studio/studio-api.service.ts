import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, concatMap, from, of, switchMap, tap, throwError, toArray } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/services/auth.service';
import type { CampaignConfiguration } from '../../core/models/campaign.model';

interface StudioDraft { readonly id: string; readonly chunk_size: number; readonly chunk_count: number }
interface DraftStatus extends StudioGenerationResponse {
  readonly status: 'uploading' | 'ready' | 'generating' | 'interrupted' | 'generated' | 'saved';
  readonly chunk_size: number;
  readonly chunk_count: number;
}
export interface GeneratedStudioImage {
  readonly id: string;
  readonly label: string;
  readonly url: string;
  readonly mime_type: 'image/png';
}
export interface StudioGenerationResponse {
  readonly draft_id: string;
  readonly images: readonly GeneratedStudioImage[];
}

export class StudioGenerationPendingError extends Error {}
export class StudioGenerationInterruptedError extends Error {}

@Injectable({ providedIn: 'root' })
export class StudioApiService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);
  private readonly baseUrl = `${environment.apiBasePath}/v1/studio/drafts`;
  private active: { file: File; optionsKey: string; id: string } | null = null;

  generate(file: File, configuration: CampaignConfiguration, retry = false): Observable<StudioGenerationResponse> {
    const options = {
      product_name: configuration.productName.trim(),
      product_description: configuration.productDescription.trim(),
      style: configuration.style, scene: configuration.scene.trim(),
      lighting: configuration.lighting, aspect_ratio: configuration.aspectRatio,
      variations: configuration.variations,
    };
    const optionsKey = JSON.stringify(options);
    if (retry && this.active?.file === file && this.active.optionsKey === optionsKey) {
      const id = this.active.id;
      return this.http.get<DraftStatus>(`${this.baseUrl}/${id}`).pipe(switchMap(draft => {
        if (draft.status === 'generated') return of(draft);
        if (draft.status === 'ready') return this.startGeneration(id, options);
        if (draft.status === 'uploading') return this.uploadAndGenerate({ id, chunk_size: draft.chunk_size, chunk_count: draft.chunk_count }, file, options);
        if (draft.status === 'generating') return throwError(() => new StudioGenerationPendingError('La generación anterior sigue en curso. Comprueba el resultado en unos minutos.'));
        if (draft.status === 'interrupted') return throwError(() => new StudioGenerationInterruptedError('La generación anterior se interrumpió. Puedes iniciar una nueva solicitud; podría generar otro cargo.'));
        return throwError(() => new Error('Este borrador ya no está disponible. Sube la fotografía de nuevo.'));
      }));
    }
    this.active = null;
    return this.http.post<StudioDraft>(this.baseUrl, {
      original_name: file.name, image_mime_type: file.type, image_size: file.size,
    }, { headers: this.auth.csrfHeaders() }).pipe(
      tap(draft => { this.active = { file, optionsKey, id: draft.id }; }),
      switchMap(draft => this.uploadAndGenerate(draft, file, options)),
    );
  }

  private uploadAndGenerate(draft: StudioDraft, file: File, options: object): Observable<StudioGenerationResponse> {
    return from(Array.from({ length: draft.chunk_count }, (_, index) => index)).pipe(
        concatMap(index => this.http.put<void>(`${this.baseUrl}/${draft.id}/chunks/${index}`,
          file.slice(index * draft.chunk_size, Math.min(file.size, (index + 1) * draft.chunk_size)),
          { headers: this.auth.csrfHeaders().set('Content-Type', 'application/octet-stream') })),
        toArray(),
        switchMap(() => this.http.post(`${this.baseUrl}/${draft.id}/finalize`, {},
          { headers: this.auth.csrfHeaders() })),
        switchMap(() => this.startGeneration(draft.id, options)),
    );
  }

  private startGeneration(id: string, options: object): Observable<StudioGenerationResponse> {
    return this.http.post<StudioGenerationResponse>(`${this.baseUrl}/${id}/generate`, options,
      { headers: this.auth.csrfHeaders() });
  }
}
