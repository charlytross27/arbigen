import os
from collections.abc import Iterator
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.session import database_url, get_session
from app.integrations.google_trends.csv_provider import GoogleTrendsCsvProvider
from app.main import create_app
from app.modules.trends.domain import TrendsInputError


def csv_bytes(term: str = "anillos de plata", country: str = "México", value: str = "<1") -> bytes:
    return f"Category: All categories\n\nMonth,{term}: ({country})\n2026-07,0\n2026-08,{value}\n2026-09,100\n".encode()


def test_csv_provider_normalizes_and_preserves_censored_values() -> None:
    series = GoogleTrendsCsvProvider().load(query="Anillos de plata", country="MX", payload=csv_bytes())
    assert series.source == "google_trends_csv"
    assert [point.value for point in series.points] == [Decimal(0), None, Decimal(100)]
    assert [point.less_than_one for point in series.points] == [False, True, False]


def test_csv_provider_accepts_time_header_without_claiming_country_verification() -> None:
    payload = b'"Time","juguetes de bebe"\n"2026-07-01",0\n"2026-08-01",<1\n"2026-09-01",30\n'
    series = GoogleTrendsCsvProvider().load(query="juguetes de bebe", country="MX", payload=payload)
    assert series.source == "google_trends_csv_geo_unverified"
    assert [point.value for point in series.points] == [Decimal(0), None, Decimal(30)]
    with pytest.raises(TrendsInputError, match="palabra clave"):
        GoogleTrendsCsvProvider().load(query="otra búsqueda", country="MX", payload=payload)


@pytest.mark.parametrize("country,label", [("CO", "Colombia"), ("AR", "Argentina")])
def test_csv_provider_supports_countries(country: str, label: str) -> None:
    series = GoogleTrendsCsvProvider().load(query="anillos de plata", country=country, payload=csv_bytes(country=label))
    assert len(series.points) == 3


@pytest.mark.parametrize("term,country,value", [
    ("otra búsqueda", "México", "42"),
    ("anillos de plata", "Colombia", "42"),
    ("anillos de plata", "México", "101"),
    ("anillos de plata", "México", "NaN"),
])
def test_csv_provider_rejects_mismatched_or_invalid_data(term: str, country: str, value: str) -> None:
    with pytest.raises(TrendsInputError):
        GoogleTrendsCsvProvider().load(query="anillos de plata", country="MX", payload=csv_bytes(term, country, value))


@pytest.mark.skipif(not os.getenv("ARBIGEN_TEST_DATABASE_URL"), reason="Requiere PostgreSQL local de prueba explícito y migrado")
def test_trends_endpoint_persists_and_isolates_workspaces() -> None:
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
                created = client.post("/api/v1/analyses", headers=owner, json={"query": "anillos de plata", "country": "MX", "period_months": 3})
                assert created.status_code == 201
                endpoint = f"/api/v1/analyses/{created.json()['id']}/trends"
                assert client.get(endpoint, headers=outsider).status_code == 404
                assert client.post(endpoint, headers=outsider | {"Content-Type": "text/csv"}, content=csv_bytes()).status_code == 404
                assert client.get(endpoint, headers=owner).json()["points"] == []
                response = client.post(endpoint, headers=owner | {"Content-Type": "text/csv"}, content=csv_bytes())
                assert response.status_code == 200
                assert response.json()["source"] == "google_trends_csv"
                assert response.json()["points"][1] == {"date": "2026-08-01", "value": None, "less_than_one": True}
                invalid = client.post(endpoint, headers=owner | {"Content-Type": "text/csv"}, content=csv_bytes(country="Colombia"))
                assert invalid.status_code == 422
                assert client.get(endpoint, headers=owner).json()["points"] == response.json()["points"]
                replacement = client.post(endpoint, headers=owner | {"Content-Type": "text/csv"}, content=csv_bytes(value="25"))
                assert replacement.status_code == 200
                assert replacement.json()["points"][1]["value"] == "25.0000"
                time_csv = b'"Time","anillos de plata"\n"2026-07-01",10\n"2026-08-01",20\n'
                time_response = client.post(endpoint, headers=owner | {"Content-Type": "text/csv"}, content=time_csv)
                assert time_response.status_code == 200
                assert time_response.json()["source"] == "google_trends_csv_geo_unverified"
                assert len(time_response.json()["points"]) == 2
                exported = client.get(f"/api/v1/analyses/{created.json()['id']}/dataset", headers=owner)
                assert exported.status_code == 200
                assert exported.json()["trend_source"] == "google_trends_csv_geo_unverified"
                assert exported.json()["trend_imported_at"] is not None
            transaction.rollback()
    finally:
        engine.dispose()
