from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "YGO Deck Intelligence"
    environment: str = "development"
    debug: bool = False
    secret_key: str = "change-me-in-production"

    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/ygo_deckbuild"
    redis_url: str = "redis://localhost:6379/0"

    storage_backend: str = "local"
    storage_local_path: str = "./media"

    ygopro_api_base: str = "https://db.ygoprodeck.com/api/v7"
    verify_ssl: bool = True

    # URL or local path to an EdoPro/YGOPRO compatible cards.cdb (single source)
    ygopro_cdb_url: str = ""

    # Semicolon-separated list of local .cdb paths (takes priority over ygopro_cdb_url)
    # Example: C:\EdoPro\expansions\cards.cdb;C:\EdoPro\repos\prerelease.cdb
    ygopro_cdb_paths: str = ""

    # If true, trigger a CDB sync automatically when the backend starts
    auto_sync_cdb_on_startup: bool = False

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Auth (single-user mode)
    auth_enabled: bool = True
    auth_username: str = "admin"
    auth_password: str = "changeme"

    # Alerting — optional webhook URL (Slack / Discord / generic)
    alert_webhook_url: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
