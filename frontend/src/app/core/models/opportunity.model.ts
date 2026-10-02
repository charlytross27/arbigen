import { IconName } from '../../shared/icon.component';

type DemandLevel = 'Alta' | 'Media' | 'Baja';
type CompetitionLevel = 'Alta' | 'Media' | 'Baja';
type TrendType = 'Creciente' | 'Estable' | 'Estacional';

export interface FinancialInputs {
  readonly productCost: number;
  readonly shippingCost: number;
  readonly commissionPercent: number;
  readonly otherCosts: number;
  readonly salePrice: number;
}

export interface SimilarProduct {
  readonly name: string;
  readonly price: number;
  readonly distinction: string;
}

export interface OpportunityDetail {
  readonly id: string;
  readonly product: string;
  readonly category: string;
  readonly symbol: Extract<IconName, 'ring' | 'lamp' | 'cup' | 'bag'>;
  readonly country: 'México';
  readonly currency: 'MXN';
  readonly score: number;
  readonly trend: TrendType;
  readonly competition: CompetitionLevel;
  readonly competitorCount: number;
  readonly demand: DemandLevel;
  readonly averagePrice: number;
  readonly cluster: string;
  readonly clusterDescription: string;
  readonly characteristics: readonly string[];
  readonly importantVariables: readonly { label: string; detail: string }[];
  readonly similarProducts: readonly SimilarProduct[];
  readonly defaults: FinancialInputs;
}
