from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Arbigen API"
    environment: Literal["development", "test", "production"] = "development"
    cors_origins: list[str] = ["http://localhost:4200", "http://127.0.0.1:4200"]
    database_url: str | None = None
    database_migration_url: str | None = None
    auth_registration_code: str | None = Field(default=None, min_length=24)
    mercado_libre_access_token: str | None = None
    marketplace_search_provider: Literal["auto", "apify", "mercado_libre"] = "auto"
    max_products_per_analysis: int = Field(default=200, ge=1, le=1000)
    apify_api_token: str | None = None
    apify_actor_id: str = "karamelo/mercadolibre-scraper-espanol-castellano"
    apify_max_pages: int = Field(default=4, ge=1, le=50)
    apify_request_timeout_seconds: int = Field(default=120, ge=10, le=290)
    openai_api_key: str | None = None
    openai_image_model: str | None = None
    openai_image_timeout_seconds: int = Field(default=180, ge=30, le=290)
    image_storage_path: Path = Path(__file__).resolve().parents[2] / ".data" / "images"


@lru_cache
def get_settings() -> Settings:
    return Settings()
