"""Variables calculadas sobre datos internos y lectura aislada por workspace."""

import os
from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.session import database_url, get_session
from app.main import create_app
from app.modules.etl.domain import AnalyticalProduct, AnalyticalTrendPoint
from app.modules.features.engineering import calculate_features


def item(number: int, price: str, material: str = "") -> AnalyticalProduct:
    return AnalyticalProduct(f"MLM{number}", f"Producto {number}", Decimal(price), "MXN", None, None,
                             {"material_hint": material} if material else {})


def weekly(values: list[str | None]) -> list[AnalyticalTrendPoint]:
    return [AnalyticalTrendPoint(date(2026, 1, 5) + timedelta(days=7 * index),
                                 Decimal(value) if value is not None else None, value is None)
            for index, value in enumerate(values)]


def test_market_and_trend_features_use_real_counts_and_regular_windows() -> None:
    report = calculate_features(country="MX", products=[item(1, "100", "plata"), item(2, "200", "plata"), item(3, "300")],
                                trends=weekly(["10"] * 3 + ["20"] * 3 + ["30"] * 3), source_count=4)
    assert report.market.priced_count == 3
    assert report.market.price_coverage_pct == Decimal("75.00")
    assert report.market.price_mean == report.market.price_median == Decimal("200.00")
    assert report.market.price_stddev == Decimal("81.65")
    assert report.market.material_hints == {"plata": 2}
    assert report.trend.moving_average_3 == Decimal("30.00")
    assert report.trend.growth_3v3_pct == Decimal("50.00")
    assert report.trend.momentum_3v3 == Decimal("10.00")
    assert report.trend.acceleration_3v3 == Decimal("0.00")


def test_missing_censored_and_irregular_data_do_not_become_zero() -> None:
    empty = calculate_features(country="CO", products=[], trends=[], source_count=None)
    assert empty.market.currency == "COP"
    assert empty.market.price_mean is None and empty.market.price_coverage_pct is None
    assert empty.trend.mean_index is None and empty.trend.moving_average_3 is None

    censored = calculate_features(country="MX", products=[], trends=weekly(["10", "20", None, "30", "40", "50"]), source_count=0)
    assert censored.trend.observed_count == 5
    assert censored.trend.censored_count == 1
    assert censored.trend.observed_coverage_pct == Decimal("83.33")
    assert censored.trend.mean_index == Decimal("30.00")
    assert censored.trend.growth_3v3_pct is None

    irregular = weekly(["10", "10", "10", "20", "20", "20"])
    irregular[-1] = AnalyticalTrendPoint(irregular[-1].date + timedelta(days=2), Decimal("20"), False)
    report = calculate_features(country="MX", products=[], trends=irregular, source_count=None)
    assert report.trend.mean_index == Decimal("15.00")
    assert report.trend.moving_average_3 is None
    assert report.trend.growth_3v3_pct is None


@pytest.mark.skipif(not os.getenv("ARBIGEN_TEST_DATABASE_URL"), reason="Requiere PostgreSQL local de prueba explícito y migrado")
def test_features_api_reads_saved_data_without_marketplace_call() -> None:
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
            owner = {"X-Demo-Workspace-ID": str(uuid4())}
            outsider = {"X-Demo-Workspace-ID": str(uuid4())}
            with TestClient(app) as client:
                created = client.post("/api/v1/analyses", headers=owner,
                                      json={"query": "anillos de plata", "country": "MX", "period_months": 3})
                assert created.status_code == 201
                endpoint = f"/api/v1/analyses/{created.json()['id']}/features"
                assert client.get(endpoint, headers=outsider).status_code == 404
                initial = client.get(endpoint, headers=owner)
                assert initial.status_code == 200
                assert initial.json()["market"]["source_count"] is None
                assert initial.json()["market"]["price_mean"] is None
                assert initial.json()["trend"]["moving_average_3"] is None
                csv = b"Month,anillos de plata: (Mexico)\n2026-07,40\n2026-08,<1\n"
                imported = client.post(f"/api/v1/analyses/{created.json()['id']}/trends",
                                       headers=owner | {"Content-Type": "text/csv"}, content=csv)
                assert imported.status_code == 200
                updated = client.get(endpoint, headers=owner)
                assert updated.status_code == 200
                assert updated.json()["trend"]["point_count"] == 2
                assert updated.json()["trend"]["censored_count"] == 1
                assert updated.json()["trend"]["mean_index"] == "40.00"
                assert updated.json()["trend"]["moving_average_3"] is None
            transaction.rollback()
    finally:
        engine.dispose()
