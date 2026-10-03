"""Review or remove expired Studio drafts. Run explicitly per environment."""

import argparse
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.models import Campaign, StudioDraft
from app.database.session import create_database_engine
from app.integrations.image_storage import get_image_storage
from app.modules.catalogs.router import catalog_id_for_draft
from app.modules.studio.router import draft_original_filename


def main() -> None:
    parser = argparse.ArgumentParser(description="Limpiar borradores de Estudio IA vencidos")
    parser.add_argument("--apply", action="store_true", help="Eliminar archivos y filas; sin esta opción solo muestra el inventario")
    args = parser.parse_args()
    settings = get_settings()
    engine = create_database_engine(settings)
    with Session(engine) as session:
        drafts = session.scalars(select(StudioDraft).where(
            StudioDraft.expires_at <= datetime.now(timezone.utc),
        )).all()
        print(f"Borradores para limpiar: {len(drafts)}")
        if args.apply:
            storage = get_image_storage(settings)
            cleaned = 0
            for draft in drafts:
                filenames = [draft_original_filename(draft)]
                filenames.extend(f"chunk-{index:02d}" for index in range(draft.chunk_count))
                filenames.extend(f"asset-{item['id']}.png" for item in draft.preview_ids)
                try:
                    for filename in filenames:
                        storage.delete(draft.user_id, draft.id, filename)
                    if draft.status != "saved":
                        catalog_id = catalog_id_for_draft(draft.id)
                        if session.get(Campaign, catalog_id) is None:
                            for filename in [draft_original_filename(draft),
                                             *(f"asset-{item['id']}.png" for item in draft.preview_ids)]:
                                storage.delete(draft.user_id, catalog_id, filename)
                except Exception:
                    session.rollback()
                    print(f"No se pudo limpiar un borrador; se conserva para reintento: {draft.id}")
                    continue
                session.delete(draft)
                session.commit()
                cleaned += 1
            print(f"Borradores limpiados: {cleaned}")
    engine.dispose()


if __name__ == "__main__":
    main()
