"""Score exploratorio: puertas de evidencia, economía unitaria y contrato HTTP."""

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
from app.modules.forecasting.model import forecast_trends
from app.modules.scoring.model import FinancialAssumptions, ScoreWeights, calculate_score


def evidence(product_count: int = 8, trend_count: int = 20):
    products = [AnalyticalProduct(f"MLM{i}", f"Producto {i}", Decimal(100 + i), "MXN", None, None, {})
                for i in range(product_count)]
    trends = [AnalyticalTrendPoint(date(2026, 1, 1) + timedelta(days=i), Decimal(20 + 2 * i), False)
              for i in range(trend_count)]
    return (calculate_features(country="MX", products=products, trends=trends, source_count=product_count),
            forecast_trends(trends))


def financial(product_cost: str = "60") -> FinancialAssumptions:
    return FinancialAssumptions(Decimal(100), Decimal(product_cost), Decimal(5), Decimal(10), Decimal(5))


def test_score_uses_real_signals_and_explicit_unit_economics() -> None:
    features, forecast = evidence()
    report = calculate_score(features=features, forecast=forecast, assumptions=financial())
    assert report.status == "ready" and report.score is not None
    assert report.commission_cost == Decimal("10.00")
    assert report.total_cost == Decimal("80.00")
    assert report.unit_profit == Decimal("20.00")
    assert report.margin_pct == Decimal("20.00")
    assert report.roi_pct == Decimal("25.00")
    assert report.components["margin"] == Decimal("50.00")
    assert report.components["roi"] == Decimal("25.00")
    assert report.score == Decimal("54.25")
    assert any("competencia" in item for item in report.limitations)

    custom = calculate_score(features=features, forecast=forecast, assumptions=financial(),
                             weights=ScoreWeights(Decimal(0), Decimal(0), Decimal(1), Decimal(0)))
    assert custom.score == Decimal("50.00")


def test_missing_inputs_or_evidence_never_become_zero_score() -> None:
    features, forecast = evidence()
    no_inputs = calculate_score(features=features, forecast=forecast)
    assert no_inputs.score is None and no_inputs.missing == ("financial_inputs",)
    short_features, short_forecast = evidence(product_count=7, trend_count=5)
    incomplete = calculate_score(features=short_features, forecast=short_forecast, assumptions=financial())
    assert incomplete.score is None
    assert {"market_sample", "trend_growth", "validated_forecast"} <= set(incomplete.missing)
    loss = calculate_score(features=features, forecast=forecast, assumptions=financial("90"))
    assert loss.unit_profit == Decimal("-10.00") and loss.score == Decimal("0.00")
    zero_cost = calculate_score(features=features, forecast=forecast,
                                assumptions=FinancialAssumptions(Decimal(100), Decimal(0), Decimal(0), Decimal(0), Decimal(0)))
    assert zero_cost.score is None and "roi_denominator" in zero_cost.missing
    with pytest.raises(ValueError, match="sumar exactamente 1"):
        ScoreWeights(Decimal("0.3"), Decimal("0.3"), Decimal("0.3"), Decimal("0.3"))


@pytest.mark.skipif(not os.getenv("ARBIGEN_TEST_DATABASE_URL"), reason="Requiere PostgreSQL local de prueba explícito y migrado")
def test_score_api_isolated_and_read_only() -> None:
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
                                      json={"query": "juguetes de bebe", "country": "MX", "period_months": 12})
                assert created.status_code == 201
                endpoint = f"/api/v1/analyses/{created.json()['id']}/opportunity-score"
                assert client.get(endpoint, headers=outsider).status_code == 404
                initial = client.get(endpoint, headers=owner)
                assert initial.status_code == 200 and initial.json()["score"] is None
                payload = {"financial": {"sale_price": 100, "product_cost": 60, "shipping_cost": 5,
                                         "commission_pct": 10, "other_costs": 5}}
                preview = client.post(endpoint + "/preview", headers=owner, json=payload)
                assert preview.status_code == 200
                assert preview.json()["score"] is None
                assert preview.json()["unit_profit"] == "20.00"
                assert "market_sample" in preview.json()["missing"]
                assert client.get(endpoint, headers=owner).json()["unit_profit"] is None
                payload["weights"] = {"growth": 0.4, "stability": 0.4, "margin": 0.4, "roi": 0.4}
                assert client.post(endpoint + "/preview", headers=owner, json=payload).status_code == 422
            transaction.rollback()
    finally:
        engine.dispose()
