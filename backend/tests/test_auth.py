from collections.abc import Iterator
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.database.models import Analysis, AuthSession, User
from app.database.session import get_session
from app.main import create_app


INVITATION = "test-invitation-code-with-enough-entropy"
ORIGIN = {"Origin": "http://testserver"}


def test_private_registration_sessions_csrf_and_user_isolation() -> None:
    settings = Settings(database_url=None, environment="test",
                        cors_origins=["http://testserver"], auth_registration_code=INVITATION, _env_file=None)
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def sqlite_uuid(connection, _record) -> None:
        connection.create_function("gen_random_uuid", 0, lambda: uuid4().hex)

    User.metadata.create_all(engine, tables=[User.__table__, AuthSession.__table__, Analysis.__table__])
    try:
        app = create_app(settings)

        def test_session() -> Iterator[Session]:
            with Session(engine) as session:
                yield session

        app.dependency_overrides[get_session] = test_session
        owner_email = f"owner-{uuid4()}@example.com"
        outsider_email = f"outsider-{uuid4()}@example.com"
        password = "correct-horse-battery-staple"
        with TestClient(app) as owner, TestClient(app) as outsider:
                assert owner.get("/api/v1/dashboard").status_code == 401
                assert owner.get("/api/v1/analyses", headers={"X-Demo-Workspace-ID": str(uuid4())}).status_code == 401
                payload = {"name": "Dueña", "email": owner_email, "password": password,
                           "invitation_code": INVITATION}
                assert owner.post("/api/v1/auth/register", json=payload, headers={"Origin": "https://attacker.example"}).status_code == 403
                assert owner.post("/api/v1/auth/register", json=payload | {"invitation_code": "incorrecto"}, headers=ORIGIN).status_code == 403
                registered = owner.post("/api/v1/auth/register", json=payload, headers=ORIGIN)
                assert registered.status_code == 201
                assert registered.json()["user"]["email"] == owner_email
                assert "HttpOnly" in registered.headers["set-cookie"]
                assert "SameSite=strict" in registered.headers["set-cookie"]
                assert owner.get("/api/v1/auth/me").json()["user"]["email"] == owner_email
                assert owner.post("/api/v1/analyses", json={"query": "anillos de plata", "country": "MX", "period_months": 3},
                                  headers=ORIGIN).status_code == 403
                csrf = registered.json()["csrf_token"]
                saved = owner.post("/api/v1/analyses", json={"query": "anillos de plata", "country": "MX", "period_months": 3},
                                   headers=ORIGIN | {"X-CSRF-Token": csrf})
                assert saved.status_code == 201
                assert owner.get("/api/v1/analyses").json()["total"] == 1
                assert owner.get("/api/v1/analyses").headers["cache-control"] == "private, no-store"

                registered_outsider = outsider.post("/api/v1/auth/register", headers=ORIGIN, json=payload | {"email": outsider_email})
                assert registered_outsider.status_code == 201
                assert outsider.get("/api/v1/analyses").json()["total"] == 0
                assert outsider.get(f"/api/v1/analyses/{saved.json()['id']}").status_code == 404
                assert owner.post("/api/v1/auth/logout", headers=ORIGIN | {"X-CSRF-Token": csrf}).status_code == 204
                assert owner.get("/api/v1/auth/me").status_code == 401
                assert owner.post("/api/v1/auth/login", headers=ORIGIN,
                                  json={"email": owner_email, "password": "wrong-password"}).status_code == 401
                logged_in = owner.post("/api/v1/auth/login", headers=ORIGIN,
                                       json={"email": owner_email, "password": password})
                assert logged_in.status_code == 200
                assert owner.get("/api/v1/analyses").json()["total"] == 1
    finally:
        engine.dispose()
