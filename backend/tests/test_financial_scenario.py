"""Escenario persistido sin usar datos de producción ni llamar a Apify."""

from collections.abc import Iterator
import os
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.models import Product
from app.database.session import database_url, get_session
from app.main import create_app
from tests.auth_support import authenticated_headers


@pytest.mark.skipif(not os.getenv("ARBIGEN_TEST_DATABASE_URL"), reason="Requiere PostgreSQL local de prueba explícito y migrado")
def test_financial_scenario_is_private_persisted_and_survives_product_refresh() -> None:
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
            try:
                with TestClient(app) as client:
                    analysis = client.post("/api/v1/analyses", headers=owner,
                                           json={"query": "juguetes de bebe", "country": "MX", "period_months": 3})
                    assert analysis.status_code == 201
                    analysis_id = analysis.json()["id"]
                    path = f"/api/v1/analyses/{analysis_id}/financial-scenario"
                    with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                        product = Product(analysis_id=analysis_id, external_id="MLM123", title="Juguete de bebé", price=420,
                                          currency="MXN", attributes_json={})
                        session.add(product)
                        session.commit()
                        product_id = str(product.id)

                    assert client.get(path, headers=owner).json() is None
                    assert client.get(path, headers=outsider).status_code == 404
                    payload = {"product_id": product_id, "sale_price": "420.00", "product_cost": "115.00",
                               "shipping_cost": "35.00", "commission_pct": "15.00", "other_costs": "77.00"}
                    assert client.put(path, headers={k: v for k, v in owner.items() if k != "X-CSRF-Token"}, json=payload).status_code == 403
                    assert client.put(path, headers=outsider, json=payload).status_code == 404
                    assert client.put(path, headers=owner, json=payload | {"product_id": str(uuid4())}).status_code == 404
                    assert client.put(path, headers=owner, json=payload | {"commission_pct": "101"}).status_code == 422
                    assert client.put(path, headers=owner, json=payload | {"sale_price": "0"}).status_code == 422

                    saved = client.put(path, headers=owner, json=payload)
                    assert saved.status_code == 200
                    assert saved.json()["unit_profit"] == "130.00"
                    assert saved.json()["break_even_price"] == "267.06"
                    assert saved.json()["product_title"] == "Juguete de bebé"
                    assert client.get(path, headers=owner).json()["product_id"] == product_id
                    score = client.get(f"/api/v1/analyses/{analysis_id}/opportunity-score", headers=owner)
                    assert score.status_code == 200
                    assert score.json()["unit_profit"] == "130.00"
                    assert "financial_inputs" not in score.json()["missing"]
                    preview = client.post(
                        f"/api/v1/analyses/{analysis_id}/opportunity-score/preview",
                        headers=owner,
                        json={"financial": {key: value for key, value in payload.items() if key != "product_id"} | {"sale_price": "400.00"}},
                    )
                    assert preview.status_code == 200
                    assert preview.json()["unit_profit"] == "113.00"
                    assert client.get(path, headers=owner).json()["unit_profit"] == "130.00"
                    assert client.put(path, headers=owner, json=payload | {"sale_price": "400.00"}).json()["unit_profit"] == "113.00"

                    with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                        session.execute(delete(Product).where(Product.id == product_id))
                        session.commit()
                    retained = client.get(path, headers=owner).json()
                    assert retained["product_id"] is None
                    assert retained["product_title"] == "Juguete de bebé"
                    assert retained["unit_profit"] == "113.00"
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
