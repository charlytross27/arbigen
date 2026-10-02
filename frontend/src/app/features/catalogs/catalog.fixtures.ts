import type { CatalogCampaign } from '../../core/models/catalog.model';

// MOCK DATA ONLY: campañas y artes SVG ilustrativos, sin imágenes generadas con IA.
export const CATALOG_FIXTURES: readonly CatalogCampaign[] = [
  {
    id: 'demo-catalog-rings', name: 'Esencia minimalista', productName: 'Anillos de plata ajustables',
    configuration: { productName: 'Anillos de plata ajustables', productDescription: 'Plata ajustable de diseño fino', style: 'Minimalista', scene: 'Mesa de piedra clara', lighting: 'Natural', aspectRatio: '1:1', variations: 2 },
    originalUrl: '/demo-catalogs/ring-original.svg', originalName: 'anillos-original.svg', originalFormat: 'SVG',
    assets: [
      { id: 'rings-natural', label: 'Piedra clara', url: '/demo-catalogs/ring-natural.svg', format: 'SVG', favorite: true, local: false },
      { id: 'rings-premium', label: 'Fondo editorial', url: '/demo-catalogs/ring-premium.svg', format: 'SVG', favorite: false, local: false },
    ],
    opportunityId: 'demo-rings', createdAt: '2026-09-26T12:00:00.000Z', origin: 'example',
  },
  {
    id: 'demo-catalog-lamps', name: 'Luz para habitar', productName: 'Lámparas de mesa nórdicas',
    configuration: { productName: 'Lámparas de mesa nórdicas', productDescription: 'Lámpara compacta de mesa', style: 'Natural', scene: 'Sala serena', lighting: 'Cálida', aspectRatio: '4:5', variations: 2 },
    originalUrl: '/demo-catalogs/lamp-original.svg', originalName: 'lampara-original.svg', originalFormat: 'SVG',
    assets: [
      { id: 'lamps-natural', label: 'Sala cálida', url: '/demo-catalogs/lamp-natural.svg', format: 'SVG', favorite: true, local: false },
      { id: 'lamps-studio', label: 'Estudio suave', url: '/demo-catalogs/lamp-studio.svg', format: 'SVG', favorite: false, local: false },
    ],
    opportunityId: 'demo-lamps', createdAt: '2026-09-23T12:00:00.000Z', origin: 'example',
  },
];
