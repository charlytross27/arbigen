import { AnalysisPeriod } from './saved-analysis.model';

export type DemandLevel = 'Alta' | 'Media' | 'Baja';
export type CompetitionLevel = 'Alta' | 'Media' | 'Baja';
export type TrendType = 'Creciente' | 'Estable' | 'Estacional';

export interface PriceBucket {
  readonly label: string;
  readonly count: number;
}

export interface MarketPoint {
  readonly price: number;
  readonly demandIndex: number;
}

export interface AnalysisCluster {
  readonly number: number;
  readonly label: string;
  readonly description: string;
  readonly averagePrice: number;
  readonly competitorCount: number;
  readonly demand: DemandLevel;
  readonly expectedMargin: number;
  readonly recommended: boolean;
  readonly points: readonly MarketPoint[];
}

export interface AnalysisFixture {
  readonly id: string;
  readonly product: string;
  readonly category: string;
  readonly country: 'México';
  readonly currency: 'MXN';
  readonly score: number;
  readonly roi: number;
  readonly netMargin: number;
  readonly competition: CompetitionLevel;
  readonly trend: TrendType;
  readonly summary: string;
  readonly averagePrice: number;
  readonly competitorCount: number;
  readonly demand: DemandLevel;
  readonly interest: readonly number[];
  readonly illustrativeProjection: readonly number[];
  readonly priceBuckets: readonly PriceBucket[];
  readonly priceDemand: readonly MarketPoint[];
  readonly clusters: readonly AnalysisCluster[];
}

export interface AnalysisView {
  readonly fixture: AnalysisFixture;
  readonly period: AnalysisPeriod;
}
