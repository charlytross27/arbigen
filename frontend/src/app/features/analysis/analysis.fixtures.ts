import { AnalysisFixture, MarketPoint } from '../../core/models/analysis.model';

// MOCK DATA ONLY. Las series, segmentos, ROI y scores fueron redactados para una demo visual.
// No proceden de Mercado Libre, Google Trends ni de modelos entrenados.
const RING_POINTS: readonly MarketPoint[] = [
  { price: 205, demandIndex: 42 }, { price: 235, demandIndex: 53 },
  { price: 280, demandIndex: 60 }, { price: 300, demandIndex: 64 },
  { price: 330, demandIndex: 58 }, { price: 355, demandIndex: 67 },
  { price: 380, demandIndex: 72 }, { price: 395, demandIndex: 77 },
  { price: 415, demandIndex: 79 }, { price: 440, demandIndex: 74 },
  { price: 470, demandIndex: 82 }, { price: 515, demandIndex: 61 },
  { price: 575, demandIndex: 48 }, { price: 620, demandIndex: 39 },
  { price: 690, demandIndex: 37 },
];

const LAMP_POINTS: readonly MarketPoint[] = [
  { price: 520, demandIndex: 46 }, { price: 580, demandIndex: 54 },
  { price: 640, demandIndex: 62 }, { price: 700, demandIndex: 71 },
  { price: 760, demandIndex: 69 }, { price: 810, demandIndex: 78 },
  { price: 870, demandIndex: 82 }, { price: 930, demandIndex: 76 },
  { price: 990, demandIndex: 73 }, { price: 1060, demandIndex: 65 },
  { price: 1130, demandIndex: 57 }, { price: 1210, demandIndex: 51 },
  { price: 1300, demandIndex: 43 }, { price: 1450, demandIndex: 34 },
];

const CUP_POINTS: readonly MarketPoint[] = [
  { price: 150, demandIndex: 50 }, { price: 180, demandIndex: 58 },
  { price: 210, demandIndex: 65 }, { price: 240, demandIndex: 69 },
  { price: 275, demandIndex: 76 }, { price: 305, demandIndex: 80 },
  { price: 335, demandIndex: 78 }, { price: 365, demandIndex: 71 },
  { price: 395, demandIndex: 72 }, { price: 425, demandIndex: 64 },
  { price: 470, demandIndex: 56 }, { price: 520, demandIndex: 47 },
  { price: 580, demandIndex: 41 }, { price: 650, demandIndex: 33 },
];

export const ANALYSIS_FIXTURES: readonly AnalysisFixture[] = [
  {
    id: 'demo-rings', product: 'Anillos de plata ajustables', category: 'Joyería y accesorios',
    country: 'México', currency: 'MXN', score: 87, roi: 42, netMargin: 31,
    competition: 'Media', trend: 'Creciente', averagePrice: 420, competitorCount: 23, demand: 'Alta',
    summary: 'Una propuesta de estilo minimalista concentra el ejemplo de mayor potencial, con interés al alza y competencia intermedia.',
    interest: [38, 41, 45, 44, 49, 53, 57, 56, 62, 69, 73, 79],
    illustrativeProjection: [82, 85, 88],
    priceBuckets: [
      { label: '$150–249', count: 4 }, { label: '$250–349', count: 8 },
      { label: '$350–449', count: 13 }, { label: '$450–549', count: 9 },
      { label: '$550–699', count: 5 },
    ],
    priceDemand: RING_POINTS,
    clusters: [
      { number: 1, label: 'Económico / alto volumen', description: 'Precio bajo, competencia más intensa.', averagePrice: 255, competitorCount: 39, demand: 'Media', expectedMargin: 22, recommended: false, points: RING_POINTS.slice(0, 5) },
      { number: 2, label: 'Minimalista / Plata / Ajustable', description: 'Estilo definido y demanda ilustrativa alta.', averagePrice: 420, competitorCount: 23, demand: 'Alta', expectedMargin: 38, recommended: true, points: RING_POINTS.slice(5, 11) },
      { number: 3, label: 'Premium / diseño', description: 'Precio más alto y nicho más pequeño.', averagePrice: 595, competitorCount: 14, demand: 'Baja', expectedMargin: 30, recommended: false, points: RING_POINTS.slice(11) },
    ],
  },
  {
    id: 'demo-lamps', product: 'Lámparas de mesa nórdicas', category: 'Hogar y decoración',
    country: 'México', currency: 'MXN', score: 82, roi: 36, netMargin: 28,
    competition: 'Media', trend: 'Creciente', averagePrice: 870, competitorCount: 31, demand: 'Alta',
    summary: 'Las lámparas compactas de estética nórdica ilustran un segmento de precio medio con interés sostenido.',
    interest: [43, 45, 48, 52, 50, 55, 59, 63, 64, 67, 72, 76],
    illustrativeProjection: [78, 81, 83],
    priceBuckets: [
      { label: '$450–649', count: 5 }, { label: '$650–849', count: 10 },
      { label: '$850–1049', count: 14 }, { label: '$1050–1249', count: 8 },
      { label: '$1250–1499', count: 4 },
    ],
    priceDemand: LAMP_POINTS,
    clusters: [
      { number: 1, label: 'Básica / funcional', description: 'Entrada accesible, más competidores.', averagePrice: 620, competitorCount: 42, demand: 'Media', expectedMargin: 20, recommended: false, points: LAMP_POINTS.slice(0, 4) },
      { number: 2, label: 'Nórdica / compacta', description: 'Diseño definido con demanda ilustrativa alta.', averagePrice: 870, competitorCount: 31, demand: 'Alta', expectedMargin: 34, recommended: true, points: LAMP_POINTS.slice(4, 10) },
      { number: 3, label: 'Diseño / premium', description: 'Precio alto y público más acotado.', averagePrice: 1270, competitorCount: 17, demand: 'Baja', expectedMargin: 29, recommended: false, points: LAMP_POINTS.slice(10) },
    ],
  },
  {
    id: 'demo-cups', product: 'Vasos térmicos de acero', category: 'Lifestyle y cocina',
    country: 'México', currency: 'MXN', score: 78, roi: 32, netMargin: 26,
    competition: 'Alta', trend: 'Estable', averagePrice: 335, competitorCount: 47, demand: 'Alta',
    summary: 'La demanda ilustrativa es estable, mientras la competencia aumenta en opciones sin diferenciación visual.',
    interest: [61, 63, 60, 64, 62, 65, 66, 63, 67, 65, 68, 66],
    illustrativeProjection: [67, 66, 68],
    priceBuckets: [
      { label: '$100–199', count: 7 }, { label: '$200–299', count: 13 },
      { label: '$300–399', count: 17 }, { label: '$400–499', count: 10 },
      { label: '$500–699', count: 5 },
    ],
    priceDemand: CUP_POINTS,
    clusters: [
      { number: 1, label: 'Básico / masivo', description: 'Competencia más intensa en el precio bajo.', averagePrice: 210, competitorCount: 62, demand: 'Alta', expectedMargin: 18, recommended: false, points: CUP_POINTS.slice(0, 4) },
      { number: 2, label: 'Acero / minimalista', description: 'Diseño sobrio y precio medio.', averagePrice: 335, competitorCount: 47, demand: 'Alta', expectedMargin: 29, recommended: true, points: CUP_POINTS.slice(4, 10) },
      { number: 3, label: 'Premium / gran capacidad', description: 'Precio alto con nicho más pequeño.', averagePrice: 530, competitorCount: 24, demand: 'Media', expectedMargin: 28, recommended: false, points: CUP_POINTS.slice(10) },
    ],
  },
];
