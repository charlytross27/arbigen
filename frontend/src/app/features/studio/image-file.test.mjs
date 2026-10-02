import assert from 'node:assert/strict';
import { test } from 'node:test';
import { imageTypeFromBytes, normalizedImageFile } from './image-file.ts';

test('reconoce el formato por contenido y corrige un MIME incorrecto', async () => {
  const jpeg = new Uint8Array([0xff, 0xd8, 0xff, 0xe0, 0, 0]);
  const file = new File([jpeg], 'producto.png', { type: 'image/png' });
  const normalized = await normalizedImageFile(file);
  assert.equal(normalized?.type, 'image/jpeg');
  assert.equal(normalized?.name, 'producto.jpg');
  assert.deepEqual(new Uint8Array(await normalized.arrayBuffer()), jpeg);
});

test('conserva un PNG válido y rechaza datos que no son una imagen admitida', async () => {
  const png = new File([new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])],
    'producto.png', { type: 'image/png' });
  assert.equal(await normalizedImageFile(png), png);
  const unknown = new File([new Uint8Array([0, 1, 2])], 'producto.jpg', { type: 'image/jpeg' });
  assert.equal(await normalizedImageFile(unknown), null);
});

test('reconoce WebP por sus cabeceras RIFF y WEBP', () => {
  assert.equal(imageTypeFromBytes(new TextEncoder().encode('RIFF1234WEBP')), 'image/webp');
});
