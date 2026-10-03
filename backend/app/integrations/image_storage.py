"""Image storage behind a replaceable byte-storage boundary."""

import os
from pathlib import Path
from typing import Protocol
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from fastapi import HTTPException
from vercel.blob import BlobClient
from vercel.blob.errors import BlobError, BlobNotFoundError

from app.core.config import Settings


class ImageStorage(Protocol):
    def put(self, user_id: UUID, campaign_id: UUID, filename: str, data: bytes) -> None: ...
    def read(self, user_id: UUID, campaign_id: UUID, filename: str) -> bytes: ...
    def delete(self, user_id: UUID, campaign_id: UUID, filename: str) -> None: ...


def _valid_filename(filename: str) -> bool:
    if filename.startswith("chunk-") and len(filename) == 8 and filename[6:].isdigit():
        return 0 <= int(filename[6:]) <= 99
    if filename in {"original.png", "original.jpg", "original.webp"}:
        return True
    if not (filename.startswith("asset-") and filename.endswith(".png")):
        return False
    try:
        return str(UUID(filename[6:-4])) == filename[6:-4]
    except ValueError:
        return False


class LocalImageStorage:
    """Private files in Development. Never expose filesystem paths to clients."""

    def __init__(self, root: Path):
        self.root = root

    def _path(self, user_id: UUID, campaign_id: UUID, filename: str) -> Path:
        # Every path component is constructed from UUIDs or a fixed filename.
        if not _valid_filename(filename):
            raise ValueError("Nombre de archivo no permitido.")
        return self.root / str(user_id) / str(campaign_id) / filename

    def put(self, user_id: UUID, campaign_id: UUID, filename: str, data: bytes) -> None:
        path = self._path(user_id, campaign_id, filename)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = path.with_name(f".{uuid4()}.tmp")
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    def read(self, user_id: UUID, campaign_id: UUID, filename: str) -> bytes:
        try:
            return self._path(user_id, campaign_id, filename).read_bytes()
        except FileNotFoundError:
            raise HTTPException(404, "La imagen no está disponible.") from None

    def delete(self, user_id: UUID, campaign_id: UUID, filename: str) -> None:
        self._path(user_id, campaign_id, filename).unlink(missing_ok=True)


class VercelBlobImageStorage:
    """Private production blobs; only authenticated API routes deliver bytes."""

    def __init__(self, token: str | None, environment: str):
        self.token = token
        self.environment = environment

    def _key(self, user_id: UUID, campaign_id: UUID, filename: str) -> str:
        if not _valid_filename(filename):
            raise ValueError("Nombre de archivo no permitido.")
        return f"arbigen/{self.environment}/{user_id}/{campaign_id}/{filename}"

    def put(self, user_id: UUID, campaign_id: UUID, filename: str, data: bytes) -> None:
        key = self._key(user_id, campaign_id, filename)
        content_type = ("application/octet-stream" if filename.startswith("chunk-") else
                        "image/jpeg" if filename.endswith(".jpg") else
                        "image/webp" if filename.endswith(".webp") else "image/png")
        try:
            with BlobClient(token=self.token) as client:
                result = client.put(key, data, access="private", content_type=content_type,
                                    overwrite=True, add_random_suffix=False)
                if not (urlsplit(result.url).hostname or "").endswith(".private.blob.vercel-storage.com"):
                    client.delete(result.url)
                    raise HTTPException(503, "El almacén de imágenes debe ser un Blob store Private.")
        except BlobError:
            raise HTTPException(503, "No pudimos guardar la imagen en este momento.") from None

    def read(self, user_id: UUID, campaign_id: UUID, filename: str) -> bytes:
        key = self._key(user_id, campaign_id, filename)
        try:
            with BlobClient(token=self.token) as client:
                result = client.get(key, access="private", use_cache=False)
        except BlobNotFoundError:
            raise HTTPException(404, "La imagen no está disponible.") from None
        except BlobError:
            raise HTTPException(503, "No pudimos abrir la imagen en este momento.") from None
        if result is None or result.status_code == 404:
            raise HTTPException(404, "La imagen no está disponible.")
        if result.status_code != 200:
            raise HTTPException(503, "No pudimos abrir la imagen en este momento.")
        return result.content

    def delete(self, user_id: UUID, campaign_id: UUID, filename: str) -> None:
        key = self._key(user_id, campaign_id, filename)
        try:
            with BlobClient(token=self.token) as client:
                client.delete(key)
        except BlobNotFoundError:
            return
        except BlobError:
            raise HTTPException(503, "No pudimos limpiar la imagen en este momento.") from None


def get_image_storage(settings: Settings) -> ImageStorage:
    if settings.environment == "production":
        if settings.image_storage_backend != "vercel_blob":
            raise HTTPException(503, "El almacenamiento de imágenes aún no está configurado para Production.")
        if not settings.blob_read_write_token:
            raise HTTPException(503, "Falta configurar el acceso al almacén de imágenes de Production.")
        return VercelBlobImageStorage(settings.blob_read_write_token, "production")
    if settings.image_storage_backend != "local":
        raise HTTPException(503, "Development guarda las imágenes solo en disco local.")
    return LocalImageStorage(settings.image_storage_path)
