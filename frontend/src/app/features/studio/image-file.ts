export type SupportedImageType = 'image/png' | 'image/jpeg' | 'image/webp';

export function imageTypeFromBytes(bytes: Uint8Array): SupportedImageType | null {
  if (bytes.length >= 8 &&
      bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e && bytes[3] === 0x47 &&
      bytes[4] === 0x0d && bytes[5] === 0x0a && bytes[6] === 0x1a && bytes[7] === 0x0a) return 'image/png';
  if (bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return 'image/jpeg';
  if (bytes.length >= 12 &&
      String.fromCharCode(...bytes.slice(0, 4)) === 'RIFF' &&
      String.fromCharCode(...bytes.slice(8, 12)) === 'WEBP') return 'image/webp';
  return null;
}

export async function normalizedImageFile(file: File): Promise<File | null> {
  const bytes = new Uint8Array(await file.slice(0, 12).arrayBuffer());
  const actualType = imageTypeFromBytes(bytes);
  if (!actualType) return null;
  if (file.type === actualType) return file;
  const extension = actualType === 'image/jpeg' ? 'jpg' : actualType === 'image/webp' ? 'webp' : 'png';
  const name = `${file.name.replace(/\.[^.]+$/, '')}.${extension}`;
  return new File([file], name, { type: actualType, lastModified: file.lastModified });
}
