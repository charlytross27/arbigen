"""Reasigna datos de usuarios demo antiguos a una cuenta local registrada.

Vista previa por defecto. Solo admite una base PostgreSQL en localhost y
ENVIRONMENT=development; nunca debe ejecutarse contra Neon/Production.
"""

import argparse

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.models import Analysis, Campaign, User
from app.database.session import create_database_engine, database_url


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-email", required=True, help="Cuenta registrada en la base local")
    parser.add_argument("--apply", action="store_true", help="Confirmar la reasignación tras revisar la vista previa")
    args = parser.parse_args()

    settings = get_settings()
    url = database_url(settings)
    if settings.environment != "development" or url.host not in {"localhost", "127.0.0.1", "::1"}:
        parser.error("Solo se permite ENVIRONMENT=development con PostgreSQL en localhost.")

    engine = create_database_engine(settings)
    try:
        with Session(engine) as session:
            target = session.scalar(select(User).where(func.lower(User.email) == args.target_email.strip().lower()))
            if target is None or not target.password_hash:
                parser.error("Registra primero una cuenta local con esa dirección de correo.")

            demo_ids = session.scalars(select(User.id).where(User.password_hash.is_(None))).all()
            if not demo_ids:
                print("No hay usuarios demo antiguos que reasignar.")
                return

            analyses = session.scalar(select(func.count()).select_from(Analysis).where(Analysis.user_id.in_(demo_ids)))
            campaigns = session.scalar(select(func.count()).select_from(Campaign).where(Campaign.user_id.in_(demo_ids)))
            print(f"Base local: {url.database}; cuenta destino: {target.email}")
            print(f"Usuarios demo: {len(demo_ids)}; análisis: {analyses}; campañas: {campaigns}")
            if not args.apply:
                print("Vista previa: no se cambió ningún dato. Repite con --apply para reasignar.")
                return

            session.execute(update(Analysis).where(Analysis.user_id.in_(demo_ids)).values(user_id=target.id))
            session.execute(update(Campaign).where(Campaign.user_id.in_(demo_ids)).values(user_id=target.id))
            session.commit()
            print("Datos locales reasignados a la cuenta registrada.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
