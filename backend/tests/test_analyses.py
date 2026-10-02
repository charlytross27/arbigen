import os
from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.session import database_url, get_session
from app.main import create_app
from app.modules.analyses.schemas import AnalysisCreate


def test_create_payload_normalizes_search_without_market_metrics() -> None:
    payload = AnalysisCreate(query="  anillos   de plata  ", country="MX", category="  Joyería  y  accesorios ", period_months=6)
    assert payload.query == "anillos de plata"
    assert payload.category == "Joyería y accesorios"
    assert not hasattr(payload, "opportunity_score")


@pytest.mark.skipif(not os.getenv("ARBIGEN_TEST_DATABASE_URL"), reason="Requiere PostgreSQL local de prueba explícito y migrado")
def test_analysis_api_persists_lists_and_isolates_demo_workspaces() -> None:
    settings = Settings(database_url=os.environ["ARBIGEN_TEST_DATABASE_URL"], environment="test", _env_file=None)
    engine = create_engine(database_url(settings))
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            app = create_app(settings)

            def test_session() -> Iterator[Session]:
                with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                    yield session

            app.dependency_overrides[get_session] = test_session
            first_workspace = {"X-Demo-Workspace-ID": str(uuid4())}
            other_workspace = {"X-Demo-Workspace-ID": str(uuid4())}
            try:
                with TestClient(app) as client:
                    invalid = client.post("/api/v1/analyses", headers=first_workspace, json={"query": "  ", "country": "MX", "period_months": 6})
                    assert invalid.status_code == 422

                    first = client.post("/api/v1/analyses", headers=first_workspace, json={"query": "  anillos   de plata  ", "country": "MX", "category": "Joyería", "period_months": 6})
                    assert first.status_code == 201
                    assert first.json()["query"] == "anillos de plata"
                    assert first.json()["status"] == "saved"
                    assert "opportunity_score" not in first.json()
                    saved_id = first.json()["id"]

                    second = client.post("/api/v1/analyses", headers=first_workspace, json={"query": "lámparas nórdicas", "country": "CO", "period_months": 3})
                    assert second.status_code == 201
                    page = client.get("/api/v1/analyses?limit=1&offset=0", headers=first_workspace)
                    assert page.status_code == 200
                    assert page.json()["total"] == 2
                    assert len(page.json()["items"]) == 1
                    assert client.get(f"/api/v1/analyses/{saved_id}", headers=first_workspace).json()["id"] == saved_id

                    assert client.get("/api/v1/analyses", headers=other_workspace).json()["total"] == 0
                    assert client.get(f"/api/v1/analyses/{saved_id}", headers=other_workspace).status_code == 404
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
