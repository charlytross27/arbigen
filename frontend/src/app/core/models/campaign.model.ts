export type CampaignStyle = 'Minimalista' | 'Premium' | 'Lifestyle' | 'Urbano' | 'Natural' | 'Studio';
export type CampaignLighting = 'Natural' | 'Cálida' | 'Fría' | 'Estudio' | 'Dramática';
export type CampaignAspectRatio = '1:1' | '4:5' | '16:9';

export interface CampaignConfiguration {
  readonly productName: string;
  readonly productDescription: string;
  readonly style: CampaignStyle;
  readonly scene: string;
  readonly lighting: CampaignLighting;
  readonly aspectRatio: CampaignAspectRatio;
  readonly variations: number;
}

export interface StudioVariant {
  readonly id: string;
  readonly label: string;
  readonly filter: string;
}
