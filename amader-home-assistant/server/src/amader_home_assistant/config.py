from __future__ import annotations

from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./data/amader-home-assistant.db"
    doorbell_hmac_secrets: dict[str, str] = Field(default_factory=dict)
    pairing_code: SecretStr = SecretStr("")
    hmac_max_age_seconds: int = Field(default=300, ge=1, le=3600)
    max_ingest_body_bytes: int = Field(default=16384, ge=1024, le=1048576)
    allowed_origins: list[str] = Field(default_factory=list)
    camera_base_url: str = "https://camera.souptik.dev"
    firebase_credentials_path: Path | None = None
    firebase_credentials_json: SecretStr | None = None
    ios_critical_alerts_enabled: bool = False
