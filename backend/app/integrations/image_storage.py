"""Development image storage behind a replaceable byte-storage boundary."""

import os
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

from fastapi import HTTPException

from app.core.config import Settings


class ImageStorage(Protocol):
    def put(self, user_id: UUID, campaign_id: UUID, filename: str, data: bytes) -> None: ...
    def read(self, user_id: UUID, campaign_id: UUID, filename: str) -> bytes: ...
    def delete(self, user_id: UUID, campaign_id: UUID, filename: str) -> None: ...


class LocalImageStorage:
    """Private files in Development. Never expose filesystem paths to clients."""

    def __init__(self, root: Path):
        self.root = root

    def _path(self, user_id: UUID, campaign_id: UUID, filename: str) -> Path:
        # Every path component is constructed from UUIDs or a fixed filename.
        if filename != "original.png" and filename != "original.jpg" and filename != "original.webp" \
                and not (filename.startswith("asset-") and filename.endswith(".png")
                         and self._is_uuid(filename[6:-4])):
            raise ValueError("Nombre de archivo no permitido.")
        return self.root / str(user_id) / str(campaign_id) / filename

    @staticmethod
    def _is_uuid(value: str) -> bool:
        try:
            return str(UUID(value)) == value
        except ValueError:
            return False

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


def get_image_storage(settings: Settings) -> ImageStorage:
    if settings.environment == "production":
        raise HTTPException(503, "El almacenamiento de imágenes aún no está configurado para Production.")
    return LocalImageStorage(settings.image_storage_path)
