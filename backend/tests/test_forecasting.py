"""Backtesting cronológico y contrato de lectura del pronóstico."""

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
from app.modules.etl.domain import AnalyticalTrendPoint
from app.modules.forecasting.model import forecast_trends


def daily(values: list[int | None]) -> list[AnalyticalTrendPoint]:
    return [AnalyticalTrendPoint(date(2026, 1, 1) + timedelta(days=index),
                                 Decimal(value) if value is not None else None, value is None)
            for index, value in enumerate(values)]


def test_drift_wins_rolling_backtest_on_regular_growth() -> None:
    report = forecast_trends(daily([20 + index * 2 for index in range(20)]))
    assert report.status == "ready"
    assert report.frequency == "daily" and report.selected_model == "drift"
    assert report.backtest_origins >= 6
    assert report.backtest_mae == Decimal("0.00") < report.naive_mae
    assert report.candidate_mae["drift"] == report.backtest_mae
    assert report.candidate_mae["naive"] == report.naive_mae
    assert report.direction == "creciente"
    assert [(point.date, point.value) for point in report.predictions] == [
        (date(2026, 1, 21), Decimal("60.00")),
        (date(2026, 1, 22), Decimal("62.00")),
        (date(2026, 1, 23), Decimal("64.00")),
    ]
    assert report.predictions[0].lower == Decimal("55.00")


def test_seasonal_baseline_only_appears_after_enough_cycles() -> None:
    values = [20, 30, 40, 50, 60, 50, 30] * 5
    report = forecast_trends(daily(values))
    assert report.status == "ready"
    assert report.selected_model == "seasonal_naive"
    assert report.seasonal_signal is True
    assert [point.value for point in report.predictions] == [Decimal("20.00"), Decimal("30.00"), Decimal("40.00")]


def test_rejects_short_irregular_and_unreliable_series_without_imputation() -> None:
    assert forecast_trends(daily([30] * 15)).status == "insufficient_data"
    censored = forecast_trends(daily([20] * 17 + [None, 30, 40]))
    assert censored.status == "censored_data"
    assert censored.used_point_count == 2 and censored.censored_count == 1
    irregular = daily([30] * 20)
    irregular[10] = AnalyticalTrendPoint(irregular[10].date + timedelta(days=1), Decimal(30), False)
    with pytest.raises(ValueError, match="duplicadas"):
        forecast_trends(irregular)
    irregular[10] = AnalyticalTrendPoint(date(2026, 2, 10), Decimal(30), False)
    assert forecast_trends(irregular).status == "irregular_series"
    volatile = forecast_trends(daily([0, 100] * 10))
    assert volatile.status == "low_skill" and volatile.predictions == ()


def test_month_end_frequency_preserves_calendar_dates() -> None:
    values = [AnalyticalTrendPoint(date(year, month, day), Decimal(40), False)
              for year, month, day in [(2025, 1, 31), (2025, 2, 28), (2025, 3, 31), (2025, 4, 30),
                                       (2025, 5, 31), (2025, 6, 30), (2025, 7, 31), (2025, 8, 31),
                                       (2025, 9, 30), (2025, 10, 31), (2025, 11, 30), (2025, 12, 31),
                                       (2026, 1, 31), (2026, 2, 28), (2026, 3, 31), (2026, 4, 30)]]
    report = forecast_trends(values)
    assert report.status == "ready" and report.frequency == "monthly"
    assert [point.date for point in report.predictions] == [date(2026, 5, 31), date(2026, 6, 30), date(2026, 7, 31)]


def test_uses_recent_regular_suffix_after_censored_point() -> None:
    points = [AnalyticalTrendPoint(date(2025, 12, 18), None, True)] + [
        AnalyticalTrendPoint(date(2026, 1, 1) + timedelta(days=7 * index), Decimal(40), False)
        for index in range(16)
    ]
    report = forecast_trends(points)
    assert report.status == "ready" and report.frequency == "weekly"
    assert report.source_point_count == 17 and report.used_point_count == 16
    assert report.censored_count == 1
    assert report.predictions[0].date == date(2026, 4, 23)


@pytest.mark.skipif(not os.getenv("ARBIGEN_TEST_DATABASE_URL"), reason="Requiere PostgreSQL local de prueba explícito y migrado")
def test_forecast_api_reads_imported_series_without_marketplace_provider() -> None:
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
                analysis_id = created.json()["id"]
                endpoint = f"/api/v1/analyses/{analysis_id}/forecast"
                assert client.get(endpoint, headers=outsider).status_code == 404
                assert client.get(endpoint, headers=owner).json()["status"] == "insufficient_data"
                rows = [f"2025-{month:02d},{20 + month * 2}" for month in range(1, 13)] + [
                    f"2026-{month:02d},{44 + month * 2}" for month in range(1, 5)]
                csv = ("Month,juguetes de bebe: (Mexico)\n" + "\n".join(rows) + "\n").encode()
                imported = client.post(f"/api/v1/analyses/{analysis_id}/trends",
                                       headers=owner | {"Content-Type": "text/csv"}, content=csv)
                assert imported.status_code == 200
                forecast = client.get(endpoint, headers=owner)
                assert forecast.status_code == 200
                assert forecast.json()["status"] == "ready"
                assert forecast.json()["frequency"] == "monthly"
                assert forecast.json()["selected_model"] == "drift"
                assert len(forecast.json()["predictions"]) == 3
                assert forecast.json()["predictions"][0]["date"] == "2026-05-01"
            transaction.rollback()
    finally:
        engine.dispose()
