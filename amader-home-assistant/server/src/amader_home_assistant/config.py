from __future__ import annotations

import ipaddress
import re
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
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
    pairing_attempts_per_minute: int = Field(default=5, ge=1, le=60)
    pairing_rate_limit_max_clients: int = Field(default=2048, ge=16, le=100000)
    trusted_proxy_networks: list[str] = Field(default_factory=list)
    allowed_origins: list[str] = Field(default_factory=list)
    camera_base_url: str = "https://camera.souptik.dev"
    firebase_credentials_path: Path | None = None
    firebase_credentials_json: SecretStr | None = None
    ios_critical_alerts_enabled: bool = False
    web_push_vapid_public_key: str = ""
    web_push_vapid_private_key: SecretStr = SecretStr("")
    web_push_vapid_private_key_path: Path | None = None
    web_push_vapid_subject: str = ""
    web_push_allowed_hosts: list[str] = Field(
        default_factory=lambda: ["web.push.apple.com", "fcm.googleapis.com"]
    )
    web_push_timeout_seconds: float = Field(default=5.0, ge=1.0, le=30.0)

    @field_validator("web_push_vapid_public_key")
    @classmethod
    def validate_web_push_vapid_public_key(cls, value: str) -> str:
        if value and not re.fullmatch(r"[A-Za-z0-9_-]{87}", value):
            raise ValueError(
                "Web Push VAPID public key must be an 87-character URL-safe key"
            )
        return value

    @field_validator("web_push_allowed_hosts")
    @classmethod
    def validate_web_push_allowed_hosts(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        hostname_pattern = re.compile(
            r"(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
            r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
        )
        for value in values:
            host = value.strip().lower().rstrip(".")
            try:
                ipaddress.ip_address(host.strip("[]"))
            except ValueError:
                pass
            else:
                raise ValueError(
                    "Web Push allow-list entries must be exact DNS hostnames"
                )
            if not hostname_pattern.fullmatch(host):
                raise ValueError(
                    "Web Push allow-list entries must be exact DNS hostnames"
                )
            normalized.append(host)
        if not normalized:
            raise ValueError("Web Push allow-list must not be empty")
        return normalized
