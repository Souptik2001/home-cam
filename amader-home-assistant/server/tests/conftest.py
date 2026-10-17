from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from amader_home_assistant.config import Settings
from amader_home_assistant.main import create_app
from amader_home_assistant.push import PushMessage, PushResult


class RecordingPushSender:
    enabled = True

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[str, PushMessage]] = []

    def send(self, token: str, message: PushMessage) -> PushResult:
        self.calls.append((token, message))
        if self.fail:
            raise RuntimeError("provider unavailable")
        return PushResult(provider_message_id="provider-message-1")


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    return tmp_path / "doorbell.sqlite3"


@pytest.fixture
def settings(database_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{database_path}",
        doorbell_hmac_secrets={"front-door": "ingest-secret"},
        pairing_code="pair-once",
        allowed_origins=["https://app.example.test"],
        hmac_max_age_seconds=300,
    )


@pytest.fixture
def push_sender() -> RecordingPushSender:
    return RecordingPushSender()


@pytest.fixture
def client(
    settings: Settings, push_sender: RecordingPushSender
) -> Iterator[TestClient]:
    with TestClient(
        create_app(settings=settings, push_sender=push_sender)
    ) as test_client:
        yield test_client


@pytest.fixture
def paired_client(client: TestClient) -> tuple[TestClient, str]:
    response = client.post(
        "/api/v1/pair", json={"code": "pair-once", "name": "Family phone"}
    )
    assert response.status_code == 201
    return client, response.json()["token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def signed_ingest(
    client: TestClient,
    payload: dict[str, Any],
    *,
    source_id: str = "front-door",
    secret: str = "ingest-secret",
    timestamp: int | None = None,
    nonce: str = "nonce-1",
):
    body = json.dumps(payload, separators=(",", ":")).encode()
    timestamp = timestamp if timestamp is not None else int(time.time())
    canonical = b".".join(
        [source_id.encode(), str(timestamp).encode(), nonce.encode(), body]
    )
    signature = hmac.new(secret.encode(), canonical, hashlib.sha256).hexdigest()
    return client.post(
        "/api/v1/ingest/doorbell",
        content=body,
        headers={
            "content-type": "application/json",
            "x-doorbell-source": source_id,
            "x-doorbell-timestamp": str(timestamp),
            "x-doorbell-nonce": nonce,
            "x-doorbell-signature": signature,
        },
    )
