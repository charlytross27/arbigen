import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, from, switchMap } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/services/auth.service';
import type { CampaignConfiguration } from '../../core/models/campaign.model';

export interface GeneratedStudioImage { readonly image_base64: string; readonly mime_type: 'image/png' }
export interface StudioGenerationResponse { readonly images: readonly GeneratedStudioImage[] }

@Injectable({ providedIn: 'root' })
export class StudioApiService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);

  generate(file: File, configuration: CampaignConfiguration): Observable<StudioGenerationResponse> {
    return from(this.toBase64(file)).pipe(switchMap(image_base64 => this.http.post<StudioGenerationResponse>(
      `${environment.apiBasePath}/v1/studio/images`, {
        image_base64, image_mime_type: file.type,
        product_name: configuration.productName.trim(),
        product_description: configuration.productDescription.trim(),
        style: configuration.style, scene: configuration.scene.trim(),
        lighting: configuration.lighting, aspect_ratio: configuration.aspectRatio,
        variations: configuration.variations,
      }, { headers: this.auth.csrfHeaders() },
    )));
  }

  private toBase64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error('No pudimos leer la fotografía.'));
      reader.onload = () => resolve(String(reader.result).split(',', 2)[1] ?? '');
      reader.readAsDataURL(file);
    });
  }
}
