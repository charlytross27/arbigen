import os
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database import models
from app.database.base import Base
from app.database.session import create_database_engine, database_url
from app.main import app as local_app
from index import app as vercel_app


def test_schema_has_separate_source_snapshot_and_analytical_products() -> None:
    assert set(Base.metadata.tables) == {
        "users", "analyses", "products", "trend_points", "clusters",
        "opportunities", "campaigns", "generated_assets", "marketplace_snapshots", "auth_sessions",
    }
    assert Base.metadata.tables["products"].c.attributes.type.__class__.__name__ == "JSONB"
    assert Base.metadata.tables["campaigns"].c.original_image_url.nullable is False
    assert Base.metadata.tables["users"].c.password_hash.nullable is True


def test_vercel_entrypoint_exports_the_same_fastapi_application() -> None:
    assert vercel_app is local_app


def test_postgres_urls_choose_pooled_runtime_and_direct_migrations() -> None:
    settings = Settings(
        database_url="postgres://user:secret@pool.example/arbigen?sslmode=require",
        database_migration_url="postgresql://user:secret@direct.example/arbigen?sslmode=require",
        _env_file=None,
    )
    assert database_url(settings).drivername == "postgresql+psycopg"
    assert database_url(settings).host == "pool.example"
    assert database_url(settings, migration=True).host == "direct.example"
    assert database_url(settings).query["sslmode"] == "require"
    engine = create_database_engine(settings)
    try:
        assert engine.pool.size() == 2
    finally:
        engine.dispose()


def test_missing_or_other_database_url_is_rejected_without_exposing_credentials() -> None:
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        database_url(Settings(database_url=None, database_migration_url=None, _env_file=None))
    with pytest.raises(ValueError, match="PostgreSQL"):
        database_url(Settings(database_url="sqlite:///tmp/arbigen.db", _env_file=None))


@pytest.mark.skipif(not os.getenv("ARBIGEN_TEST_DATABASE_URL"), reason="Requiere PostgreSQL local de prueba explícito")
def test_postgres_round_trip_in_rollback_transaction() -> None:
    settings = Settings(database_url=os.environ["ARBIGEN_TEST_DATABASE_URL"], _env_file=None)
    engine = create_engine(database_url(settings))
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                with Session(connection) as session:
                    user = models.User(email="fase8@example.test", name="Demo")
                    session.add(user)
                    session.flush()
                    analysis = models.Analysis(user_id=user.id, query="anillos de plata", country="MX", period_months=6)
                    session.add(analysis)
                    session.flush()
                    product = models.Product(analysis_id=analysis.id, title="Anillo", price=Decimal("420.00"), currency="MXN", attributes_json={"material": "plata"})
                    trend = models.TrendPoint(analysis_id=analysis.id, date=date(2026, 10, 1), value=Decimal("72.5000"))
                    cluster = models.Cluster(analysis_id=analysis.id, cluster_number=1, label="Minimalista")
                    session.add_all([product, trend, cluster])
                    session.flush()
                    opportunity = models.Opportunity(analysis_id=analysis.id, cluster_id=cluster.id, opportunity_score=Decimal("87.00"))
                    session.add(opportunity)
                    session.flush()
                    campaign = models.Campaign(user_id=user.id, opportunity_id=opportunity.id, name="Esencia minimalista", product_name="Anillo", style="Minimalista", scene="Mesa clara", lighting="Natural", aspect_ratio="1:1", original_image_url="https://example.test/original.png")
                    session.add(campaign)
                    session.flush()
                    asset = models.GeneratedAsset(campaign_id=campaign.id, label="Luz suave", image_url="https://example.test/asset.png")
                    session.add(asset)
                    session.flush()
                    assert session.scalar(select(models.Product).where(models.Product.id == product.id)).attributes_json == {"material": "plata"}
                    assert session.scalar(select(models.GeneratedAsset).where(models.GeneratedAsset.id == asset.id)).is_favorite is False
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
