"""Local Development and private Blob Production, without network writes."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.integrations.image_storage import LocalImageStorage, VercelBlobImageStorage, get_image_storage


def test_development_uses_local_storage_even_with_blob_token(tmp_path) -> None:
    settings = Settings(environment="development", image_storage_backend="local",
                        blob_read_write_token="unused-test-token", image_storage_path=tmp_path,
                        _env_file=None)
    storage = get_image_storage(settings)
    assert isinstance(storage, LocalImageStorage)
    user_id, campaign_id = uuid4(), uuid4()
    storage.put(user_id, campaign_id, "original.jpg", b"local-photo")
    assert storage.read(user_id, campaign_id, "original.jpg") == b"local-photo"
    assert (tmp_path / str(user_id) / str(campaign_id) / "original.jpg").read_bytes() == b"local-photo"

    invalid = Settings(environment="development", image_storage_backend="vercel_blob",
                       blob_read_write_token="unused-test-token", _env_file=None)
    with pytest.raises(HTTPException) as unavailable:
        get_image_storage(invalid)
    assert unavailable.value.status_code == 503


def test_production_uses_private_blob_and_requires_explicit_configuration(tmp_path, monkeypatch) -> None:
    objects: dict[str, bytes] = {}
    calls: list[tuple] = []

    class FakeBlobClient:
        def __init__(self, *, token):
            assert token == "production-test-token"

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def put(self, key, data, **options):
            calls.append(("put", key, options))
            objects[key] = data
            return SimpleNamespace(url=f"https://store.private.blob.vercel-storage.com/{key}")

        def get(self, key, **options):
            calls.append(("get", key, options))
            return SimpleNamespace(status_code=200, content=objects[key]) if key in objects else None

        def delete(self, key):
            calls.append(("delete", key))
            objects.pop(key, None)

    monkeypatch.setattr("app.integrations.image_storage.BlobClient", FakeBlobClient)
    production = Settings(environment="production", image_storage_path=tmp_path, _env_file=None)
    with pytest.raises(HTTPException) as unavailable:
        get_image_storage(production)
    assert unavailable.value.status_code == 503
    no_token = Settings(environment="production", image_storage_backend="vercel_blob",
                        blob_read_write_token=None, _env_file=None)
    with pytest.raises(HTTPException) as unconfigured:
        get_image_storage(no_token)
    assert unconfigured.value.status_code == 503

    storage = get_image_storage(Settings(environment="production", image_storage_backend="vercel_blob",
                                         blob_read_write_token="production-test-token", _env_file=None))
    assert isinstance(storage, VercelBlobImageStorage)
    user_id, campaign_id = uuid4(), uuid4()
    key = f"arbigen/production/{user_id}/{campaign_id}/original.webp"
    storage.put(user_id, campaign_id, "original.webp", b"image")
    assert storage.read(user_id, campaign_id, "original.webp") == b"image"
    assert ("put", key, {"access": "private", "content_type": "image/webp",
                         "overwrite": True, "add_random_suffix": False}) in calls
    assert ("get", key, {"access": "private", "use_cache": False}) in calls
    storage.delete(user_id, campaign_id, "original.webp")
    assert key not in objects
    assert not list(tmp_path.rglob("*.webp"))
    with pytest.raises(ValueError):
        storage._key(user_id, campaign_id, "../../secret")


def test_public_store_response_is_removed_before_catalog_can_be_saved(monkeypatch) -> None:
    deleted = []

    class PublicStoreClient:
        def __init__(self, *, token):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def put(self, key, data, **options):
            return SimpleNamespace(url=f"https://store.public.blob.vercel-storage.com/{key}")

        def delete(self, url):
            deleted.append(url)

    monkeypatch.setattr("app.integrations.image_storage.BlobClient", PublicStoreClient)
    with pytest.raises(HTTPException) as rejected:
        VercelBlobImageStorage("test-token", "production").put(uuid4(), uuid4(), "original.png", b"image")
    assert rejected.value.status_code == 503
    assert len(deleted) == 1
