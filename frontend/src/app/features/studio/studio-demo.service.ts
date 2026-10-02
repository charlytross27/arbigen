import { Injectable } from '@angular/core';
import { Observable, delay, of } from 'rxjs';
import { CampaignConfiguration, CampaignLighting, CampaignStyle, StudioVariant } from '../../core/models/campaign.model';

const STYLE_FILTERS: Record<CampaignStyle, string> = {
  Minimalista: 'saturate(0.85) contrast(1.03)',
  Premium: 'contrast(1.12) saturate(0.95)',
  Lifestyle: 'saturate(1.14) brightness(1.03)',
  Urbano: 'contrast(1.16) saturate(0.88)',
  Natural: 'saturate(1.08) brightness(1.04)',
  Studio: 'contrast(1.06) brightness(1.07)',
};

const LIGHTING_FILTERS: Record<CampaignLighting, string> = {
  Natural: 'brightness(1.02)',
  Cálida: 'sepia(0.12) brightness(1.03)',
  Fría: 'hue-rotate(8deg) brightness(1.02)',
  Estudio: 'brightness(1.09) contrast(1.04)',
  Dramática: 'contrast(1.18) brightness(0.91)',
};

const TREATMENTS = [
  { label: 'Luz suave', filter: 'brightness(1.05)' },
  { label: 'Contraste', filter: 'contrast(1.13)' },
  { label: 'Tono cálido', filter: 'sepia(0.11) saturate(1.08)' },
  { label: 'Tono neutro', filter: 'saturate(0.88) brightness(1.02)' },
] as const;

export function demoTreatment(configuration: CampaignConfiguration, sequence: number): Pick<StudioVariant, 'label' | 'filter'> {
  const treatment = TREATMENTS[(sequence - 1) % TREATMENTS.length];
  return {
    label: treatment.label,
    filter: `${STYLE_FILTERS[configuration.style]} ${LIGHTING_FILTERS[configuration.lighting]} ${treatment.filter}`,
  };
}

// MOCK: genera instrucciones de recorte y filtros locales. No llama a OpenAI ni crea escenas.
@Injectable({ providedIn: 'root' })
export class StudioDemoService {
  generate(configuration: CampaignConfiguration, round: number): Observable<readonly StudioVariant[]> {
    const variants = Array.from({ length: configuration.variations }, (_, index) => {
      return {
        id: `${round}-${index + 1}`,
        ...demoTreatment(configuration, index + round),
      };
    });
    return of(variants).pipe(delay(1400));
  }
}
