"""Large images move through short requests and authenticated streamed reads."""

import base64
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import UUID, uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.database.models import AuthSession, Campaign, GeneratedAsset, StudioDraft, User
from app.database.session import get_session
from app.main import create_app
from app.modules.studio.router import GenerateImagesResponse, GeneratedImage


def test_large_studio_draft_can_be_saved_without_large_json_or_paid_call(tmp_path, monkeypatch) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    for model in (User, AuthSession, StudioDraft, Campaign, GeneratedAsset):
        model.__table__.create(engine)
    owner, stranger = uuid4(), uuid4()
    token, other_token, csrf = "studio-owner-session", "studio-other-session", "test-csrf"
    with Session(engine) as session:
        session.add_all([
            User(id=owner, email="owner@example.test", name="Owner", password_hash="test"),
            User(id=stranger, email="other@example.test", name="Other", password_hash="test"),
        ])
        for user_id, secret in ((owner, token), (stranger, other_token)):
            session.add(AuthSession(token_hash=sha256(secret.encode()).hexdigest(),
                                    user_id=user_id, csrf_token=csrf,
                                    expires_at=datetime.now(timezone.utc) + timedelta(days=1)))
        session.commit()

    original = b"\x89PNG\r\n\x1a\n" + b"a" * (7 * 1024 * 1024)
    generated = b"\x89PNG\r\n\x1a\n" + b"b" * (5 * 1024 * 1024)
    observed = []

    def fake_generate(request, _settings):
        observed.append(len(base64.b64decode(request.image_base64)))
        with Session(engine) as check:
            running = check.get(StudioDraft, UUID(draft["id"]))
            assert running.status == "generating"
            assert running.generation_attempt_id is not None
            assert len(running.preview_ids) == 1
        with TestClient(app) as concurrent:
            concurrent.cookies.set("arbigen_session", token)
            duplicate = concurrent.post(f"{draft_url}/generate", json={
                "product_name": "Producto grande", "style": "Premium", "scene": "Mesa clara",
                "lighting": "Natural", "aspect_ratio": "1:1", "variations": 1,
            }, headers=headers)
            assert duplicate.status_code == 409
        return GenerateImagesResponse(images=[GeneratedImage(image_base64=base64.b64encode(generated).decode())])

    monkeypatch.setattr("app.modules.studio.router.generate_images", fake_generate)
    settings = Settings(environment="test", cors_origins=["http://testserver"],
                        image_storage_path=tmp_path, _env_file=None)
    app = create_app(settings)

    def test_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = test_session
    headers = {"Origin": "http://testserver", "X-CSRF-Token": csrf}
    with TestClient(app) as client:
        client.cookies.set("arbigen_session", token)
        created = client.post("/api/v1/studio/drafts", json={
            "original_name": "producto.png", "image_mime_type": "image/png", "image_size": len(original),
        }, headers=headers)
        assert created.status_code == 201, created.text
        draft = created.json()
        assert draft["chunk_size"] == 2 * 1024 * 1024
        assert draft["chunk_count"] == 4
        draft_url = f"/api/v1/studio/drafts/{draft['id']}"
        assert client.post(f"{draft_url}/finalize", json={}, headers=headers).status_code == 409
        assert client.put(f"{draft_url}/chunks/0", content=b"short", headers=headers).status_code == 422

        with TestClient(app) as other:
            other.cookies.set("arbigen_session", other_token)
            assert other.get(f"{draft_url}/previews/{uuid4()}/image").status_code == 404

        for index in range(draft["chunk_count"]):
            chunk = original[index * draft["chunk_size"]:(index + 1) * draft["chunk_size"]]
            assert len(chunk) < 4_500_000
            uploaded = client.put(f"{draft_url}/chunks/{index}", content=chunk, headers=headers)
            assert uploaded.status_code == 204, uploaded.text
        assert client.post(f"{draft_url}/finalize", json={}, headers=headers).status_code == 200
        assert client.get(f"{draft_url}/original").content == original
        with TestClient(app) as other:
            other.cookies.set("arbigen_session", other_token)
            assert other.get(f"{draft_url}/original").status_code == 404
        response = client.post(f"{draft_url}/generate", json={
            "product_name": "Producto grande", "product_description": "", "style": "Premium",
            "scene": "Mesa clara", "lighting": "Natural", "aspect_ratio": "1:1", "variations": 1,
        }, headers=headers)
        assert response.status_code == 200, response.text
        result = response.json()
        assert observed == [len(original)]
        assert "image_base64" not in response.text
        assert len(response.content) < 2000
        asset = result["images"][0]
        assert client.get(asset["url"]).content == generated
        with TestClient(app) as other:
            other.cookies.set("arbigen_session", other_token)
            assert other.get(asset["url"]).status_code == 404
        status = client.get(draft_url).json()
        assert status["status"] == "generated"
        assert status["configuration"]["product_name"] == "Producto grande"
        assert status["original_name"] == "producto.png"
        repeated = client.post(f"{draft_url}/generate", json={
            "product_name": "Producto grande", "style": "Premium", "scene": "Mesa clara",
            "lighting": "Natural", "aspect_ratio": "1:1", "variations": 1,
        }, headers=headers)
        assert repeated.status_code == 200
        assert repeated.json()["images"] == result["images"]
        assert observed == [len(original)]

        saved = client.post("/api/v1/catalogs/from-draft", json={
            "draft_id": draft["id"], "selected_ids": [asset["id"]],
        }, headers=headers)
        assert saved.status_code == 201, saved.text
        catalog = saved.json()
        assert catalog["assets"][0]["favorite"] is True
        assert client.get(catalog["original_url"]).content == original
        assert client.get(catalog["assets"][0]["url"]).content == generated
        assert client.get("/api/v1/catalogs").json()[0]["id"] == catalog["id"]
        repeated_save = client.post("/api/v1/catalogs/from-draft", json={
            "draft_id": draft["id"], "selected_ids": [asset["id"]],
        }, headers=headers)
        assert repeated_save.status_code == 201
        assert repeated_save.json()["id"] == catalog["id"]
        assert len(client.get("/api/v1/catalogs").json()) == 1

        abandoned = client.post("/api/v1/studio/drafts", json={
            "original_name": "otro.png", "image_mime_type": "image/png", "image_size": len(original),
        }, headers=headers).json()
        with Session(engine) as check:
            row = check.get(StudioDraft, UUID(abandoned["id"]))
            row.status = "generating"
            row.generation_attempt_id = uuid4()
            row.generation_started_at = datetime.now(timezone.utc)
            check.commit()
        stale_url = f"/api/v1/studio/drafts/{abandoned['id']}"
        assert client.get(stale_url).json()["status"] == "generating"
        with Session(engine) as check:
            row = check.get(StudioDraft, UUID(abandoned["id"]))
            row.generation_started_at = datetime.now(timezone.utc) - timedelta(minutes=7)
            check.commit()
        assert client.get(stale_url).json()["status"] == "interrupted"
        assert client.post(f"{stale_url}/generate", json={
            "product_name": "Producto grande", "style": "Premium", "scene": "Mesa clara",
            "lighting": "Natural", "aspect_ratio": "1:1", "variations": 1,
        }, headers=headers).status_code == 409
        assert observed == [len(original)]

        def failed_generate(_request, _settings):
            raise HTTPException(502, "Servicio de prueba no disponible.")

        monkeypatch.setattr("app.modules.studio.router.generate_images", failed_generate)
        small = b"\x89PNG\r\n\x1a\nsmall-photo"
        failed = client.post("/api/v1/studio/drafts", json={
            "original_name": "pequeno.png", "image_mime_type": "image/png", "image_size": len(small),
        }, headers=headers).json()
        failed_url = f"/api/v1/studio/drafts/{failed['id']}"
        assert client.put(f"{failed_url}/chunks/0", content=small, headers=headers).status_code == 204
        assert client.post(f"{failed_url}/finalize", json={}, headers=headers).status_code == 200
        assert client.post(f"{failed_url}/generate", json={
            "product_name": "Producto pequeño", "style": "Premium", "scene": "Mesa clara",
            "lighting": "Natural", "aspect_ratio": "1:1", "variations": 1,
        }, headers=headers).status_code == 502
        failed_status = client.get(failed_url).json()
        assert failed_status["status"] == "ready"
        assert failed_status["images"] == []
        assert failed_status["configuration"]["product_name"] == "Producto pequeño"
    engine.dispose()
