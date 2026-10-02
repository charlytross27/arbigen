"""Inicio muestra únicamente datos persistidos del espacio y periodo elegidos."""

import os
from collections.abc import Iterator
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.models import Analysis, MarketplaceSnapshot, Product, TrendPoint
from app.database.session import database_url, get_session
from app.main import create_app
from tests.auth_support import authenticated_headers


@pytest.mark.skipif(not os.getenv("ARBIGEN_TEST_DATABASE_URL"), reason="Requiere PostgreSQL local explícito y migrado")
def test_dashboard_counts_period_and_workspace_without_marketplace_calls() -> None:
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
            owner = authenticated_headers(connection)
            outsider = authenticated_headers(connection)
            payload = {"query": "juguetes de bebe", "country": "MX", "period_months": 12}
            with TestClient(app) as client:
                recent_id = UUID(client.post("/api/v1/analyses", headers=owner, json=payload).json()["id"])
                old_id = UUID(client.post("/api/v1/analyses", headers=owner, json=payload | {"query": "anillos de plata"}).json()["id"])
                client.post("/api/v1/analyses", headers=outsider, json=payload | {"query": "termos"})
                now = datetime.now(timezone.utc)
                with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                    session.get(Analysis, old_id).created_at = now - timedelta(days=15)
                    session.get(Analysis, recent_id).trend_imported_at = now
                    session.add(MarketplaceSnapshot(
                        analysis_id=recent_id, source="test", site_id="MLM", fetched_at=now,
                        prepared_at=now, raw_products=[], quality={"source_count": 2, "duplicate_count": 0,
                        "missing_title_count": 0, "missing_price_count": 0, "invalid_price_count": 0,
                        "invalid_currency_count": 0, "included_count": 2},
                    ))
                    session.add_all(Product(analysis_id=recent_id, external_id=f"MLM{index}",
                                            title=f"Producto {index}", price=Decimal(100 + index),
                                            currency="MXN", attributes_json={}) for index in range(2))
                    session.add(TrendPoint(analysis_id=recent_id, date=date(2026, 1, 1),
                                           value=Decimal(50), less_than_one=False))
                    session.commit()

                endpoint = "/api/v1/dashboard"
                seven = client.get(endpoint, headers=owner, params={"days": 7})
                assert seven.status_code == 200
                data = seven.json()
                assert (data["analysis_count"], data["prepared_count"], data["priced_product_count"], data["trends_count"]) == (1, 1, 2, 1)
                assert len(data["recent"]) == 1 and data["recent"][0]["trend_point_count"] == 1
                assert {item["kind"] for item in data["activity"]} == {"analysis_saved", "products_prepared", "trends_imported"}
                thirty = client.get(endpoint, headers=owner, params={"days": 30}).json()
                assert thirty["analysis_count"] == 2 and len(thirty["recent"]) == 2
                assert client.get(endpoint, headers=outsider).json()["analysis_count"] == 1
                assert client.get(endpoint, headers=authenticated_headers(connection)).json()["analysis_count"] == 0
                assert client.get(endpoint, headers=owner, params={"days": 14}).status_code == 422
            transaction.rollback()
    finally:
        engine.dispose()
