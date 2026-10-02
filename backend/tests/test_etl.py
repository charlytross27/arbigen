import os
from collections.abc import Iterator
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.models import MarketplaceSnapshot, Product
from app.database.session import database_url, get_session
from app.integrations.marketplace_search import get_marketplace_search_provider
from app.main import create_app
from app.modules.etl.pipeline import prepare_dataset
from app.modules.marketplace.domain import MarketplaceProduct, MarketplaceSearchResult
from app.modules.trends.domain import TrendObservation


def product(id: str, title: str, price: Decimal | None, currency: str | None = "MXN") -> MarketplaceProduct:
    return MarketplaceProduct(id, title, price, currency, f"https://www.mercadolibre.com.mx/{id}", None)


def test_etl_cleans_titles_deduplicates_normalizes_prices_and_preserves_censoring() -> None:
    prepared = prepare_dataset(country="MX", products=[
        product("MLM1", "Anillo de plata", None),
        product("MLM1", "  Anillo &amp; pulsera de PLATA  ", Decimal("420.125")),
        product("MLM2", "Sin precio", None),
        product("MLM3", "Precio negativo", Decimal("-1")),
        product("MLM4", "Otra moneda", Decimal("200"), "COP"),
        product("MLM5", "   ", Decimal("50")),
        product("MLM6", "Camiseta algodón", Decimal("100.005")),
    ], trends=[TrendObservation(date(2026, 7, 1), Decimal("0")), TrendObservation(date(2026, 8, 1), None, True)])
    assert prepared.product_quality.source_count == 7
    assert prepared.product_quality.duplicate_count == 1
    assert prepared.product_quality.missing_title_count == 1
    assert prepared.product_quality.missing_price_count == 1
    assert prepared.product_quality.invalid_price_count == 1
    assert prepared.product_quality.invalid_currency_count == 1
    assert prepared.product_quality.included_count == 2
    assert prepared.products[0].title == "Anillo & pulsera de PLATA"
    assert prepared.products[0].price == Decimal("420.13")
    assert prepared.products[0].attributes["material_hint"] == "plata"
    assert prepared.products[1].price == Decimal("100.01")
    assert prepared.products[1].attributes["material_hint"] == "algodon"
    assert prepared.trends[0].value == 0
    assert prepared.trends[1].value is None and prepared.trends[1].less_than_one


def test_etl_rejects_invalid_trends_and_keeps_catalog_without_prices() -> None:
    catalog = prepare_dataset(country="MX", products=[product("MLM1", "Catálogo", None)], trends=[])
    assert catalog.product_quality.included_count == 0
    assert catalog.product_quality.missing_price_count == 1
    with pytest.raises(ValueError, match="duplicadas"):
        prepare_dataset(country="MX", products=[], trends=[TrendObservation(date(2026, 1, 1), Decimal(2)), TrendObservation(date(2026, 1, 1), Decimal(3))])
    with pytest.raises(ValueError, match="censurado"):
        prepare_dataset(country="MX", products=[], trends=[TrendObservation(date(2026, 1, 1), Decimal(0), True)])


@pytest.mark.parametrize("country,currency", [("CO", "COP"), ("AR", "ARS")])
def test_etl_keeps_local_currency_without_fx_conversion(country: str, currency: str) -> None:
    item = product("ID1", "Bolso de cuero", Decimal("1234.567"), currency)
    prepared = prepare_dataset(country=country, products=[item], trends=[])
    assert prepared.products[0].price == Decimal("1234.57")
    assert prepared.products[0].currency == currency
    assert prepared.products[0].attributes["material_hint"] == "cuero"


@pytest.mark.skipif(not os.getenv("ARBIGEN_TEST_DATABASE_URL"), reason="Requiere PostgreSQL local de prueba explícito y migrado")
def test_dataset_api_refreshes_once_and_reprocesses_without_provider() -> None:
    settings = Settings(database_url=os.environ["ARBIGEN_TEST_DATABASE_URL"], environment="test", _env_file=None)
    engine = create_engine(database_url(settings))
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            app = create_app(settings)

            def test_session() -> Iterator[Session]:
                with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                    yield session

            class FakeProvider:
                calls = 0

                def search(self, *, country: str, query: str, limit: int) -> MarketplaceSearchResult:
                    self.calls += 1
                    assert (country, query, limit) == ("MX", "anillos de plata", 200)
                    return MarketplaceSearchResult("listings", "MLM", query, datetime.now(timezone.utc), [
                        product("MLM1", " Anillo  de  plata ", Decimal("420.125")),
                        product("MLM1", "Duplicado", Decimal("420.125")),
                        product("MLM2", "Sin precio", None),
                    ])

            provider = FakeProvider()
            app.dependency_overrides[get_session] = test_session
            app.dependency_overrides[get_marketplace_search_provider] = lambda: provider
            owner = {"X-Demo-Workspace-ID": str(uuid4())}
            outsider = {"X-Demo-Workspace-ID": str(uuid4())}
            with TestClient(app) as client:
                created = client.post("/api/v1/analyses", headers=owner, json={"query": "anillos de plata", "country": "MX", "period_months": 3})
                assert created.status_code == 201
                analysis_id = created.json()["id"]
                endpoint = f"/api/v1/analyses/{analysis_id}/dataset"
                assert client.post(endpoint + "/refresh", headers=outsider).status_code == 404
                assert provider.calls == 0
                assert client.get(endpoint, headers=owner).json()["snapshot"] is None
                assert client.post(endpoint + "/reprocess", headers=owner).status_code == 409
                refreshed = client.post(endpoint + "/refresh", headers=owner)
                assert refreshed.status_code == 200
                assert provider.calls == 1
                data = refreshed.json()
                assert data["quality"]["source_count"] == 3
                assert data["quality"]["duplicate_count"] == 1
                assert data["quality"]["included_count"] == 1
                assert data["products"][0]["price"] == "420.13"
                assert data["products"][0]["attributes"]["material_hint"] == "plata"
                assert len(data["snapshot"]["items"]) == 3
                assert client.get(endpoint, headers=owner).json()["products"][0]["price"] == "420.13"
                assert client.get(endpoint, headers=outsider).status_code == 404
                assert provider.calls == 1
                csv = b"Month,anillos de plata: (Mexico)\n2026-07,40\n2026-08,<1\n"
                assert client.post(f"/api/v1/analyses/{analysis_id}/trends", headers=owner | {"Content-Type": "text/csv"}, content=csv).status_code == 200
                reprocessed = client.post(endpoint + "/reprocess", headers=owner)
                assert reprocessed.status_code == 200
                assert provider.calls == 1
                assert len(reprocessed.json()["trends"]) == 2
                assert reprocessed.json()["trends"][1]["less_than_one"] is True
                assert connection.scalar(select(MarketplaceSnapshot).where(MarketplaceSnapshot.analysis_id == analysis_id)) is not None
                assert len(connection.scalars(select(Product).where(Product.analysis_id == analysis_id)).all()) == 1
            transaction.rollback()
    finally:
        engine.dispose()
