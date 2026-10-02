from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health_contract() -> None:
    with TestClient(create_app(Settings(environment="test", _env_file=None))) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_route_uses_error_envelope() -> None:
    with TestClient(create_app(Settings(environment="test", _env_file=None))) as client:
        response = client.get("/api/missing")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "http_error", "message": "Not Found"}}


def test_cors_allows_only_configured_origin() -> None:
    with TestClient(create_app(Settings(cors_origins=["http://localhost:4200"], _env_file=None))) as client:
        allowed = client.get("/api/health", headers={"Origin": "http://localhost:4200"})
        denied = client.get("/api/health", headers={"Origin": "https://unconfigured.example"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:4200"
    assert "access-control-allow-origin" not in denied.headers
