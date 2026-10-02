import { Injectable } from '@angular/core';
import { Observable, delay, of } from 'rxjs';
import { OpportunityDetail, SimilarProduct } from '../../core/models/opportunity.model';

type DemoExtras = Pick<OpportunityDetail, 'symbol' | 'characteristics' | 'importantVariables' | 'similarProducts' | 'defaults'>;
type DemoSeed = Pick<OpportunityDetail, 'id' | 'product' | 'category' | 'country' | 'currency' | 'score' | 'trend' | 'competition' | 'competitorCount' | 'demand' | 'averagePrice' | 'cluster' | 'clusterDescription'>;

const SEEDS: readonly DemoSeed[] = [
  {
    id: 'demo-rings', product: 'Anillos de plata ajustables', category: 'Joyería y accesorios',
    country: 'México', currency: 'MXN', score: 87, trend: 'Creciente', competition: 'Media',
    competitorCount: 23, demand: 'Alta', averagePrice: 420,
    cluster: 'Minimalista / Plata / Ajustable', clusterDescription: 'Estilo definido y demanda ilustrativa alta.',
  },
  {
    id: 'demo-lamps', product: 'Lámparas de mesa nórdicas', category: 'Hogar y decoración',
    country: 'México', currency: 'MXN', score: 82, trend: 'Creciente', competition: 'Media',
    competitorCount: 31, demand: 'Alta', averagePrice: 870,
    cluster: 'Nórdica / compacta', clusterDescription: 'Diseño definido con demanda ilustrativa alta.',
  },
  {
    id: 'demo-cups', product: 'Vasos térmicos de acero', category: 'Lifestyle y cocina',
    country: 'México', currency: 'MXN', score: 78, trend: 'Estable', competition: 'Alta',
    competitorCount: 47, demand: 'Alta', averagePrice: 335,
    cluster: 'Acero / minimalista', clusterDescription: 'Diseño sobrio y precio medio.',
  },
];

// MOCK: nombres, precios, competidores y señales son ejemplos inventados.
const EXTRAS: Record<string, DemoExtras> = {
  'demo-rings': {
    symbol: 'ring', characteristics: ['Plata', 'Ajustable', 'Estilo minimalista'],
    importantVariables: [
      { label: 'Diferenciación', detail: 'Acabado y presentación del anillo.' },
      { label: 'Precio', detail: 'Comparar tu precio con el promedio ficticio.' },
      { label: 'Costo unitario', detail: 'Proveedor, empaque y envío por pieza.' },
    ],
    similarProducts: [
      { name: 'Anillo fino ajustable', price: 390, distinction: 'Diseño liso' },
      { name: 'Anillo de plata abierto', price: 445, distinction: 'Acabado pulido' },
      { name: 'Set de anillos minimalistas', price: 510, distinction: 'Paquete de 2' },
    ],
    defaults: { productCost: 115, shippingCost: 35, commissionPercent: 15, otherCosts: 77, salePrice: 420 },
  },
  'demo-lamps': {
    symbol: 'lamp', characteristics: ['Mesa', 'Diseño nórdico', 'Formato compacto'],
    importantVariables: [
      { label: 'Material', detail: 'Pantalla, base y acabado visual.' },
      { label: 'Envío', detail: 'El volumen puede elevar el costo por unidad.' },
      { label: 'Precio', detail: 'Ubicación frente al segmento medio ficticio.' },
    ],
    similarProducts: [
      { name: 'Lámpara compacta blanca', price: 790, distinction: 'Base metálica' },
      { name: 'Lámpara de mesa nórdica', price: 890, distinction: 'Pantalla textil' },
      { name: 'Lámpara de lectura minimal', price: 970, distinction: 'Brazo orientable' },
    ],
    defaults: { productCost: 345, shippingCost: 90, commissionPercent: 15, otherCosts: 100, salePrice: 870 },
  },
  'demo-cups': {
    symbol: 'cup', characteristics: ['Acero inoxidable', 'Térmico', 'Uso diario'],
    importantVariables: [
      { label: 'Capacidad', detail: 'Tamaño y conservación térmica percibida.' },
      { label: 'Competencia', detail: 'La categoría ilustrativa tiene muchas opciones.' },
      { label: 'Costo unitario', detail: 'Proveedor, empaque y envío por vaso.' },
    ],
    similarProducts: [
      { name: 'Vaso térmico 350 ml', price: 289, distinction: 'Tapa deslizante' },
      { name: 'Vaso de acero mate', price: 339, distinction: 'Acabado sobrio' },
      { name: 'Vaso térmico 500 ml', price: 399, distinction: 'Mayor capacidad' },
    ],
    defaults: { productCost: 125, shippingCost: 38, commissionPercent: 15, otherCosts: 35, salePrice: 335 },
  },
};

function fromSeed(seed: DemoSeed): OpportunityDetail {
  const extra = EXTRAS[seed.id];
  return {
    ...seed,
    ...extra,
  };
}

const BAG_PRODUCTS: readonly SimilarProduct[] = [
  { name: 'Bolso tejido de mano', price: 560, distinction: 'Tamaño compacto' },
  { name: 'Bolso artesanal natural', price: 630, distinction: 'Fibra vegetal' },
  { name: 'Bolso tejido con asa', price: 710, distinction: 'Formato amplio' },
];

const OPPORTUNITIES: readonly OpportunityDetail[] = [
  ...SEEDS.map(fromSeed),
  {
    id: 'demo-bags', product: 'Bolsos tejidos artesanales',
    category: 'Moda y accesorios', symbol: 'bag', country: 'México', currency: 'MXN',
    score: 81, trend: 'Estacional', competition: 'Media', competitorCount: 28,
    demand: 'Media', averagePrice: 630, cluster: 'Artesanal / fibra natural',
    clusterDescription: 'Diseño de inspiración artesanal con precio medio ilustrativo.',
    characteristics: ['Tejido artesanal', 'Fibra natural', 'Accesorio de temporada'],
    importantVariables: [
      { label: 'Estacionalidad', detail: 'La demanda de ejemplo cambia por temporada.' },
      { label: 'Material', detail: 'Tipo de fibra y calidad del acabado.' },
      { label: 'Costo unitario', detail: 'Tiempo de confección y empaque.' },
    ],
    similarProducts: BAG_PRODUCTS,
    defaults: { productCost: 240, shippingCost: 55, commissionPercent: 15, otherCosts: 55, salePrice: 630 },
  },
];

@Injectable({ providedIn: 'root' })
export class OpportunityDemoService {
  getOpportunity(id: string | null): Observable<OpportunityDetail | null> {
    return of(OPPORTUNITIES.find(item => item.id === id) ?? null).pipe(delay(220));
  }
}
