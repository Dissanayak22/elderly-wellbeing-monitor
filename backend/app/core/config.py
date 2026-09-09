from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Elderly Wellbeing Monitor"
    app_env: str = "development"
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 480
    port: int = 8000
    database_url: str = f"sqlite:///{(ROOT / 'database' / 'app.db').as_posix()}"
    frontend_origins: str = (
        "http://127.0.0.1:5173,http://localhost:5173,"
        "http://127.0.0.1:5174,http://localhost:5174,"
        "http://127.0.0.1:5175,http://localhost:5175,"
        "http://127.0.0.1:8000,http://localhost:8000"
    )
    cors_origins: str = ""
    ai_demo_mode: bool = False
    seed_demo_data: bool = True
    enable_blockchain_audit: bool = False

    @property
    def effective_frontend_origins(self) -> str:
        return (self.frontend_origins or self.cors_origins or "http://127.0.0.1:5173,http://localhost:5173").strip()

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_sqlite(cls, value: str) -> str:
        if isinstance(value, str) and value.startswith("sqlite:///./"):
            rel = value.replace("sqlite:///./", "", 1)
            return f"sqlite:///{(ROOT / rel).as_posix()}"
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
