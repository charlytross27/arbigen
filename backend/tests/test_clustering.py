"""Segmentación reproducible y lectura de productos persistidos sin nueva extracción."""

import os
from collections.abc import Iterator
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.session import database_url, get_session
from app.integrations.marketplace_search import get_marketplace_search_provider
from app.main import create_app
from tests.auth_support import authenticated_headers
from app.modules.clustering.model import cluster_products
from app.modules.etl.domain import AnalyticalProduct
from app.modules.marketplace.domain import MarketplaceProduct, MarketplaceSearchResult


PRICES = [100, 105, 110, 115, 120, 125, 600, 620, 640, 660, 680, 700]


def analytical_products(prices: list[int], currency: str = "MXN") -> list[AnalyticalProduct]:
    return [AnalyticalProduct(f"P{index}", f"Producto de plata {index}", Decimal(price), currency, None, None,
                              {"material_hint": "plata"}) for index, price in enumerate(prices)]


def test_kmeans_finds_stable_price_segments_without_commercial_claims() -> None:
    products = analytical_products(PRICES)
    report = cluster_products(country="MX", products=products)
    assert report.status == "ready"
    assert report.selected_k == 2
    assert report.silhouette is not None and report.silhouette >= Decimal("0.90")
    assert [(segment.count, segment.price_median) for segment in report.segments] == [
        (6, Decimal("112.50")), (6, Decimal("650.00")),
    ]
    assert sum(segment.count for segment in report.segments) == len(products)
    assert report.segments[0].material_hints == {"plata": 6}
    assert cluster_products(country="MX", products=list(reversed(products))) == report
    assert all("competencia" not in segment.label.lower() and "demanda" not in segment.label.lower()
               for segment in report.segments)


def test_clustering_declines_sparse_or_nearly_uniform_samples() -> None:
    sparse = cluster_products(country="MX", products=analytical_products(PRICES[:5]))
    assert sparse.status == "insufficient_data" and sparse.segments == ()
    flat = cluster_products(country="MX", products=analytical_products(list(range(100, 112))))
    assert flat.status == "no_separation" and flat.selected_k is None
    with pytest.raises(ValueError, match="monedas"):
        cluster_products(country="CO", products=analytical_products(PRICES))


def test_single_extreme_price_is_reported_and_does_not_force_a_singleton_group() -> None:
    prices = [Decimal(value) for value in ["96.03", "132.86", "149.00", "160.26", "175.00", "176.65",
                                           "179.99", "230.00", "246.30", "288.77", "298.00", "1499.00"]]
    products = [AnalyticalProduct(f"P{index}", "Producto", price, "MXN", None, None, {})
                for index, price in enumerate(prices)]
    report = cluster_products(country="MX", products=products)
    assert report.status == "ready"
    assert report.product_count == 12
    assert report.clustered_count == 11
    assert report.excluded_outlier_count == 1
    assert report.selected_k == 2
    assert [segment.count for segment in report.segments] == [4, 7]
    assert max(segment.price_max for segment in report.segments) == Decimal("298.00")


@pytest.mark.parametrize("country,currency", [("CO", "COP"), ("AR", "ARS")])
def test_clustering_supports_three_segments_in_local_currency(country: str, currency: str) -> None:
    prices = [100, 105, 110, 115, 120, 300, 310, 320, 330, 340, 800, 820, 840, 860, 880]
    report = cluster_products(country=country, products=analytical_products(prices, currency))
    assert report.currency == currency
    assert report.selected_k == 3
    assert [segment.count for segment in report.segments] == [5, 5, 5]


@pytest.mark.skipif(not os.getenv("ARBIGEN_TEST_DATABASE_URL"), reason="Requiere PostgreSQL local de prueba explícito y migrado")
def test_clusters_api_uses_saved_dataset_and_isolates_workspace() -> None:
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
                        MarketplaceProduct(f"MLM{index}", f"Anillo de plata {index}", Decimal(price), "MXN", None, None)
                        for index, price in enumerate(PRICES)
                    ])

            provider = FakeProvider()
            app.dependency_overrides[get_session] = test_session
            app.dependency_overrides[get_marketplace_search_provider] = lambda: provider
            owner = authenticated_headers(connection)
            outsider = authenticated_headers(connection)
            with TestClient(app) as client:
                created = client.post("/api/v1/analyses", headers=owner,
                                      json={"query": "anillos de plata", "country": "MX", "period_months": 3})
                assert created.status_code == 201
                analysis_id = created.json()["id"]
                endpoint = f"/api/v1/analyses/{analysis_id}/clusters"
                assert client.get(endpoint, headers=outsider).status_code == 404
                assert client.get(endpoint, headers=owner).json()["status"] == "insufficient_data"
                refreshed = client.post(f"/api/v1/analyses/{analysis_id}/dataset/refresh", headers=owner)
                assert refreshed.status_code == 200 and provider.calls == 1
                first = client.get(endpoint, headers=owner)
                assert first.status_code == 200
                assert first.json()["status"] == "ready"
                assert first.json()["selected_k"] == 2
                assert sum(segment["count"] for segment in first.json()["segments"]) == len(PRICES)
                assert client.get(endpoint, headers=owner).json() == first.json()
                assert provider.calls == 1
            transaction.rollback()
    finally:
        engine.dispose()
