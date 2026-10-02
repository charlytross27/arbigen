import type { CampaignAspectRatio, StudioVariant } from '../../core/models/campaign.model';

const OUTPUT_SIZE: Record<CampaignAspectRatio, { width: number; height: number }> = {
  '1:1': { width: 1200, height: 1200 },
  '4:5': { width: 1080, height: 1350 },
  '16:9': { width: 1440, height: 810 },
};

// Exporta exactamente el recorte y filtro mostrados. El archivo sigue siendo una
// edición local de la fotografía original, nunca una imagen generada con IA.
export async function renderStudioPreview(sourceUrl: string, variant: StudioVariant, ratio: CampaignAspectRatio): Promise<Blob> {
  const image = new Image();
  image.src = sourceUrl;
  await image.decode();

  const canvas = document.createElement('canvas');
  const size = OUTPUT_SIZE[ratio];
  canvas.width = size.width;
  canvas.height = size.height;
  const context = canvas.getContext('2d');
  if (!context) throw new Error('No se pudo preparar la vista previa.');

  const scale = Math.max(size.width / image.naturalWidth, size.height / image.naturalHeight);
  const drawnWidth = image.naturalWidth * scale;
  const drawnHeight = image.naturalHeight * scale;
  context.filter = variant.filter;
  context.drawImage(image, (size.width - drawnWidth) / 2, (size.height - drawnHeight) / 2, drawnWidth, drawnHeight);

  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(value => value ? resolve(value) : reject(new Error('No se pudo exportar la vista previa.')), 'image/png');
  });
}
