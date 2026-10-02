from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings


def database_url(settings: Settings, *, migration: bool = False) -> URL:
    value = settings.database_migration_url if migration and settings.database_migration_url else settings.database_url
    if not value or not value.strip():
        name = "DATABASE_MIGRATION_URL o DATABASE_URL" if migration else "DATABASE_URL"
        raise RuntimeError(f"Configura {name} para usar PostgreSQL.")
    try:
        url = make_url(value.strip())
    except Exception:
        raise ValueError("La URL de PostgreSQL no es válida.") from None
    if url.drivername not in {"postgres", "postgresql", "postgresql+psycopg"} or not url.database:
        raise ValueError("Se requiere una URL de PostgreSQL con nombre de base de datos.")
    return url.set(drivername="postgresql+psycopg")


def create_database_engine(settings: Settings) -> Engine:
    # La creación del engine no abre una conexión. Cada Function reutiliza un pool pequeño.
    return create_engine(
        database_url(settings),
        pool_size=2,
        max_overflow=0,
        pool_timeout=10,
        pool_recycle=300,
        pool_use_lifo=True,
        pool_pre_ping=True,
    )


@lru_cache
def get_engine() -> Engine:
    return create_database_engine(get_settings())


def get_session() -> Iterator[Session]:
    # Una sesión por petición; el commit corresponde al servicio que escribe.
    with Session(get_engine()) as session:
        yield session
