"""Cost-free catalog persistence and ownership checks."""

import base64
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.database.models import AuthSession, Campaign, GeneratedAsset, User
from app.database.session import get_session
from app.main import create_app
from app.modules.catalogs.router import (
    CatalogAssetInput, CatalogCreate, FavoriteUpdate, add_asset, create_catalog, delete_catalog,
    get_asset_image, get_catalog, get_original, list_catalogs, restore_catalog,
    regenerate_asset, update_favorite,
)
from app.modules.studio.router import GenerateImagesRequest, GenerateImagesResponse, GeneratedImage

IMAGE = b"\x89PNG\r\n\x1a\nsmall-catalog-test-image"


def test_catalog_persists_privately_and_restores_after_delete(tmp_path) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    for model in (User, Campaign, GeneratedAsset):
        model.__table__.create(engine)
    owner, stranger = uuid4(), uuid4()
    settings = Settings(environment="test", image_storage_path=tmp_path, _env_file=None)
    payload = CatalogCreate(
        configuration=GenerateImagesRequest(
            image_base64=base64.b64encode(IMAGE).decode(), image_mime_type="image/png",
            product_name="Anillo plata", product_description="Plata lisa",
            style="Minimalista", scene="Mesa clara", lighting="Natural",
            aspect_ratio="1:1", variations=1,
        ),
        original_name="producto.png",
        assets=[CatalogAssetInput(label="Escena 1", image_base64=base64.b64encode(IMAGE).decode())],
    )
    with Session(engine) as session:
        session.add_all([
            User(id=owner, email="owner@example.test", name="Owner"),
            User(id=stranger, email="stranger@example.test", name="Stranger"),
        ])
        session.commit()
        created = create_catalog(payload, owner, session, settings)
        campaign_id = created["id"]
        asset_id = created["assets"][0]["id"]
        assert get_original(campaign_id, owner, session, settings).body == IMAGE
        assert get_asset_image(campaign_id, asset_id, owner, session, settings).body == IMAGE
        assert len(list_catalogs(owner, session, settings)) == 1
        assert list_catalogs(stranger, session, settings) == []
        with pytest.raises(HTTPException) as denied:
            get_catalog(campaign_id, stranger, session, settings)
        assert denied.value.status_code == 404
        update_favorite(campaign_id, asset_id, FavoriteUpdate(favorite=True), owner, session)

    # A new database session simulates loading the gallery after a page refresh.
    with Session(engine) as session:
        assert get_catalog(campaign_id, owner, session, settings)["assets"][0]["favorite"] is True
        delete_catalog(campaign_id, owner, session)
        assert list_catalogs(owner, session, settings) == []
        with pytest.raises(HTTPException) as hidden:
            get_asset_image(campaign_id, asset_id, owner, session, settings)
        assert hidden.value.status_code == 404
        restore_catalog(campaign_id, owner, session)
        assert len(list_catalogs(owner, session, settings)) == 1


def test_catalog_add_and_regenerate_use_saved_original_without_paid_call(tmp_path, monkeypatch) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    for model in (User, Campaign, GeneratedAsset):
        model.__table__.create(engine)
    owner = uuid4()
    settings = Settings(environment="test", image_storage_path=tmp_path, _env_file=None)
    payload = CatalogCreate(
        configuration=GenerateImagesRequest(
            image_base64=base64.b64encode(IMAGE).decode(), image_mime_type="image/png",
            product_name="Anillo plata", style="Minimalista", scene="Mesa clara",
            lighting="Natural", aspect_ratio="1:1", variations=1,
        ), original_name="original.png",
        assets=[CatalogAssetInput(label="Escena 1", image_base64=base64.b64encode(IMAGE).decode())],
    )
    observed = []

    def fake_generate(request, _settings):
        observed.append(request)
        return GenerateImagesResponse(images=[GeneratedImage(image_base64=base64.b64encode(IMAGE + b"-new").decode())])

    monkeypatch.setattr("app.modules.catalogs.router.generate_images", fake_generate)
    with Session(engine) as session:
        session.add(User(id=owner, email="owner@example.test", name="Owner"))
        session.commit()
        created = create_catalog(payload, owner, session, settings)
        campaign_id = created["id"]
        added = add_asset(campaign_id, owner, session, settings)
        assert len(added["assets"]) == 2
        first_id = created["assets"][0]["id"]
        regenerated = regenerate_asset(campaign_id, first_id, owner, session, settings)
        assert len(regenerated["assets"]) == 2
        assert get_asset_image(campaign_id, first_id, owner, session, settings).body == IMAGE + b"-new"
        assert len(observed) == 2
        assert all(base64.b64decode(item.image_base64) == IMAGE for item in observed)


def test_catalog_http_requires_session_and_csrf(tmp_path) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    for model in (User, AuthSession, Campaign, GeneratedAsset):
        model.__table__.create(engine)
    owner, token, csrf = uuid4(), "local-test-session", "local-test-csrf"
    with Session(engine) as session:
        session.add(User(id=owner, email="owner@example.test", name="Owner", password_hash="test-only"))
        session.add(AuthSession(
            token_hash=sha256(token.encode()).hexdigest(), user_id=owner,
            csrf_token=csrf, expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        ))
        session.commit()

    settings = Settings(environment="test", cors_origins=["http://testserver"],
                        image_storage_path=tmp_path, _env_file=None)
    app = create_app(settings)

    def test_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = test_session
    payload = CatalogCreate(
        configuration=GenerateImagesRequest(
            image_base64=base64.b64encode(IMAGE).decode(), image_mime_type="image/png",
            product_name="Anillo plata", style="Minimalista", scene="Mesa clara",
            lighting="Natural", aspect_ratio="1:1", variations=1,
        ), original_name="original.png",
        assets=[CatalogAssetInput(label="Escena 1", image_base64=base64.b64encode(IMAGE).decode())],
    )
    with TestClient(app) as client:
        assert client.get("/api/v1/catalogs").status_code == 401
        client.cookies.set("arbigen_session", token)
        assert client.post("/api/v1/catalogs", json=payload.model_dump(),
                           headers={"Origin": "http://testserver"}).status_code == 403
        created = client.post("/api/v1/catalogs", json=payload.model_dump(),
                              headers={"Origin": "http://testserver", "X-CSRF-Token": csrf})
        assert created.status_code == 201
        campaign_id = created.json()["id"]
        asset_id = created.json()["assets"][0]["id"]
        assert client.get(f"/api/v1/catalogs/{campaign_id}/assets/{asset_id}/image").content == IMAGE
