"""Catalog provenance is verified against account-owned research without paid APIs."""

import base64
import os
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.models import Analysis, Product, User
from app.database.session import database_url
from app.modules.catalogs.router import CatalogAssetInput, CatalogCreate, CatalogSourceInput, create_catalog, get_catalog
from app.modules.studio.router import GenerateImagesRequest

IMAGE = b"\x89PNG\r\n\x1a\nsmall-catalog-source-test-image"


@pytest.mark.skipif(not os.getenv("ARBIGEN_TEST_DATABASE_URL"), reason="Requiere PostgreSQL local de prueba explícito")
def test_catalog_source_must_match_own_analysis_and_product(tmp_path) -> None:
    settings = Settings(
        database_url=os.environ["ARBIGEN_TEST_DATABASE_URL"],
        environment="test", image_storage_path=tmp_path, _env_file=None,
    )
    engine = create_engine(database_url(settings))
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                with Session(connection, join_transaction_mode="create_savepoint") as session:
                    owner = User(email="catalog-source-owner@example.test", name="Owner")
                    stranger = User(email="catalog-source-stranger@example.test", name="Stranger")
                    session.add_all([owner, stranger])
                    session.flush()
                    analysis = Analysis(user_id=owner.id, query="pantalones cortos", country="MX", period_months=6)
                    other_analysis = Analysis(user_id=stranger.id, query="camisetas", country="MX", period_months=6)
                    session.add_all([analysis, other_analysis])
                    session.flush()
                    product = Product(analysis_id=analysis.id, title="Short deportivo original", price=Decimal("450"), currency="MXN")
                    other_product = Product(analysis_id=other_analysis.id, title="Camiseta ajena", price=Decimal("350"), currency="MXN")
                    session.add_all([product, other_product])
                    session.flush()

                    encoded = base64.b64encode(IMAGE).decode()
                    payload = CatalogCreate(
                        configuration=GenerateImagesRequest(
                            image_base64=encoded, image_mime_type="image/png",
                            product_name="Short deportivo", style="Minimalista",
                            scene="Mesa clara", lighting="Natural", aspect_ratio="1:1", variations=1,
                        ),
                        original_name="producto.png",
                        assets=[CatalogAssetInput(label="Escena 1", image_base64=encoded)],
                        source=CatalogSourceInput(analysis_id=analysis.id, product_id=product.id),
                    )
                    created = create_catalog(payload, owner.id, session, settings)
                    assert created["source"] == {
                        "analysis_id": analysis.id,
                        "product_id": product.id,
                        "product_title": product.title,
                    }
                    assert get_catalog(created["id"], owner.id, session, settings)["source"] == created["source"]

                    for source in (
                        CatalogSourceInput(analysis_id=other_analysis.id, product_id=other_product.id),
                        CatalogSourceInput(analysis_id=analysis.id, product_id=other_product.id),
                    ):
                        with pytest.raises(HTTPException) as denied:
                            create_catalog(payload.model_copy(update={"source": source}), owner.id, session, settings)
                        assert denied.value.status_code == 404

                    # Reprocessing can replace products; the title snapshot remains useful.
                    session.delete(product)
                    session.commit()
                    source_after_reprocess = get_catalog(created["id"], owner.id, session, settings)["source"]
                    assert source_after_reprocess["product_id"] is None
                    assert source_after_reprocess["product_title"] == "Short deportivo original"
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
