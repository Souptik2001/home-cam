from __future__ import annotations

import hashlib
import sqlite3
import time

from conftest import RecordingPushSender, auth_header, signed_ingest
from fastapi.testclient import TestClient


def test_pairing_returns_token_stores_only_hashes_and_code_is_one_time(
    client: TestClient, database_path
) -> None:
    first = client.post(
        "/api/v1/pair", json={"code": "pair-once", "name": "Kitchen tablet"}
    )
    second = client.post(
        "/api/v1/pair", json={"code": "pair-once", "name": "Another device"}
    )

    assert first.status_code == 201
    assert first.json()["token_type"] == "bearer"
    token = first.json()["token"]
    assert len(token) >= 32
    assert second.status_code == 409
    with sqlite3.connect(database_path) as connection:
        stored = connection.execute(
            "SELECT token_hash, pairing_code_hash FROM paired_sessions"
        ).fetchone()
    assert stored == (
        hashlib.sha256(token.encode()).hexdigest(),
        hashlib.sha256(b"pair-once").hexdigest(),
    )
    assert token not in stored
    assert "pair-once" not in stored


def test_pairing_rejects_wrong_code(client: TestClient) -> None:
    response = client.post("/api/v1/pair", json={"code": "wrong", "name": "Phone"})

    assert response.status_code == 401
    assert (
        "code" not in response.text.lower()
        or "invalid pairing code" in response.text.lower()
    )


def test_pairing_is_rate_limited_by_client(settings) -> None:
    from amader_home_assistant.main import create_app

    limited = settings.model_copy(update={"pairing_attempts_per_minute": 2})
    with TestClient(create_app(settings=limited)) as client:
        first = client.post("/api/v1/pair", json={"code": "wrong-one", "name": "Phone"})
        second = client.post(
            "/api/v1/pair", json={"code": "wrong-two", "name": "Phone"}
        )
        blocked = client.post(
            "/api/v1/pair", json={"code": "wrong-three", "name": "Phone"}
        )

    assert first.status_code == 401
    assert second.status_code == 401
    assert blocked.status_code == 429
    assert blocked.headers["retry-after"] == "60"


def test_pairing_uses_forwarded_client_only_from_trusted_proxy(settings) -> None:
    from amader_home_assistant.main import create_app

    limited = settings.model_copy(
        update={
            "pairing_attempts_per_minute": 1,
            "pairing_rate_limit_max_clients": 2,
            "trusted_proxy_networks": ["10.0.0.0/8"],
        }
    )
    app = create_app(settings=limited)
    with TestClient(app, client=("10.1.2.3", 50000)) as trusted:
        first = trusted.post(
            "/api/v1/pair",
            headers={"CF-Connecting-IP": "203.0.113.10"},
            json={"code": "wrong", "name": "Phone"},
        )
        second_client = trusted.post(
            "/api/v1/pair",
            headers={"CF-Connecting-IP": "203.0.113.11"},
            json={"code": "wrong", "name": "Phone"},
        )
        trusted.post(
            "/api/v1/pair",
            headers={"CF-Connecting-IP": "203.0.113.12"},
            json={"code": "wrong", "name": "Phone"},
        )

    with TestClient(app, client=("192.0.2.50", 50000)) as untrusted:
        spoofed = untrusted.post(
            "/api/v1/pair",
            headers={"CF-Connecting-IP": "203.0.113.20"},
            json={"code": "wrong", "name": "Phone"},
        )
        blocked = untrusted.post(
            "/api/v1/pair",
            headers={"CF-Connecting-IP": "203.0.113.21"},
            json={"code": "wrong", "name": "Phone"},
        )

    assert first.status_code == 401
    assert second_client.status_code == 401
    assert len(app.state.pairing_attempts) <= 2
    assert spoofed.status_code == 401
    assert blocked.status_code == 429


def test_protected_routes_require_a_valid_bearer_token(client: TestClient) -> None:
    assert client.get("/api/v1/events").status_code == 401
    assert client.post("/api/v1/devices", json={}).status_code == 401
    assert client.get("/api/v1/camera/config").status_code == 401


def test_device_can_be_registered_and_updated(
    paired_client: tuple[TestClient, str],
) -> None:
    client, token = paired_client
    created = client.post(
        "/api/v1/devices",
        headers=auth_header(token),
        json={
            "name": "Alice phone",
            "platform": "android",
            "push_token": "push-token-1",
        },
    )

    assert created.status_code == 201
    device_id = created.json()["id"]
    updated = client.put(
        f"/api/v1/devices/{device_id}",
        headers=auth_header(token),
        json={
            "name": "Alice Pixel",
            "platform": "android",
            "push_token": "push-token-2",
            "enabled": False,
        },
    )
    assert updated.status_code == 200
    assert updated.json() == {
        "id": device_id,
        "name": "Alice Pixel",
        "platform": "android",
        "enabled": False,
    }

    reregistered = client.post(
        "/api/v1/devices",
        headers=auth_header(token),
        json={
            "name": "Alice Pixel refreshed",
            "platform": "android",
            "push_token": "push-token-2",
            "enabled": True,
        },
    )
    assert reregistered.status_code == 201
    assert reregistered.json() == {
        "id": device_id,
        "name": "Alice Pixel refreshed",
        "platform": "android",
        "enabled": True,
    }


def test_camera_config_returns_public_https_url(
    paired_client: tuple[TestClient, str],
) -> None:
    client, token = paired_client

    response = client.get("/api/v1/camera/config", headers=auth_header(token))

    assert response.status_code == 200
    assert response.json() == {"base_url": "https://camera.souptik.dev"}


def test_signed_ingest_is_idempotent_and_events_are_newest_first(
    paired_client: tuple[TestClient, str],
) -> None:
    client, token = paired_client
    older = signed_ingest(
        client,
        {"occurred_at": "2026-10-17T10:00:00Z", "metadata": {"motion": True}},
        nonce="older-nonce",
    )
    newer = signed_ingest(
        client,
        {"occurred_at": "2026-10-17T10:01:00Z", "metadata": {"motion": False}},
        nonce="newer-nonce",
    )
    duplicate = signed_ingest(
        client,
        {"occurred_at": "2026-10-17T10:00:00Z", "metadata": {"motion": True}},
        nonce="older-nonce",
    )

    assert older.status_code == 201
    assert newer.status_code == 201
    assert duplicate.status_code == 200
    assert duplicate.json()["id"] == older.json()["id"]
    assert duplicate.json()["duplicate"] is True

    events = client.get("/api/v1/events", headers=auth_header(token))
    assert events.status_code == 200
    assert [event["id"] for event in events.json()] == [
        newer.json()["id"],
        older.json()["id"],
    ]
    assert events.json()[1]["metadata"] == {"motion": True}
    assert events.json()[0]["occurred_at"].endswith("Z")
    assert events.json()[0]["received_at"].endswith("Z")


def test_ingest_rejects_bad_signature_unknown_source_and_stale_timestamp(
    client: TestClient,
) -> None:
    payload = {"occurred_at": "2026-10-17T10:00:00Z"}

    bad_signature = signed_ingest(client, payload, secret="wrong")
    unknown_source = signed_ingest(client, payload, source_id="garage")
    stale = signed_ingest(client, payload, timestamp=int(time.time()) - 301)

    assert bad_signature.status_code == 401
    assert unknown_source.status_code == 401
    assert stale.status_code == 401


def test_ingest_rejects_oversized_body_before_signature_validation(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/ingest/doorbell",
        content=b"x" * 20000,
        headers={
            "content-type": "application/json",
            "x-doorbell-source": "front-door",
            "x-doorbell-timestamp": str(int(time.time())),
            "x-doorbell-nonce": "oversized",
            "x-doorbell-signature": "invalid",
        },
    )

    assert response.status_code == 413


def test_ingest_sends_push_and_records_success(
    paired_client: tuple[TestClient, str],
    push_sender: RecordingPushSender,
    database_path,
) -> None:
    client, token = paired_client
    registered = client.post(
        "/api/v1/devices",
        headers=auth_header(token),
        json={"name": "Phone", "platform": "android", "push_token": "push-1"},
    )
    assert registered.status_code == 201

    response = signed_ingest(
        client, {"occurred_at": "2026-10-17T10:00:00Z"}, nonce="push-success"
    )

    assert response.status_code == 201
    assert push_sender.calls[0][0] == "push-1"
    assert push_sender.calls[0][1].data["event_id"] == response.json()["id"]
    assert push_sender.calls[0][1].data["route"] == "/camera"
    with sqlite3.connect(database_path) as connection:
        attempt = connection.execute(
            "SELECT status, provider_message_id FROM notification_delivery_attempts"
        ).fetchone()
    assert attempt == ("sent", "provider-message-1")


def test_push_failure_does_not_lose_event_and_is_recorded(
    settings, database_path
) -> None:
    from amader_home_assistant.main import create_app

    sender = RecordingPushSender(fail=True)
    with TestClient(create_app(settings=settings, push_sender=sender)) as client:
        paired = client.post(
            "/api/v1/pair", json={"code": "pair-once", "name": "Phone"}
        )
        token = paired.json()["token"]
        client.post(
            "/api/v1/devices",
            headers=auth_header(token),
            json={"name": "Phone", "platform": "ios", "push_token": "push-fail"},
        )
        ingested = signed_ingest(
            client,
            {"occurred_at": "2026-10-17T10:00:00Z"},
            nonce="push-failure",
        )

        assert ingested.status_code == 201
        events = client.get("/api/v1/events", headers=auth_header(token)).json()
        assert [event["id"] for event in events] == [ingested.json()["id"]]

    with sqlite3.connect(database_path) as connection:
        attempt = connection.execute(
            "SELECT status, error FROM notification_delivery_attempts"
        ).fetchone()
    assert attempt[0] == "failed"
    assert "provider unavailable" in attempt[1]


def test_missing_firebase_credentials_uses_safe_disabled_mode(
    settings, database_path
) -> None:
    from amader_home_assistant.main import create_app

    with TestClient(create_app(settings=settings)) as client:
        paired = client.post(
            "/api/v1/pair", json={"code": "pair-once", "name": "Phone"}
        )
        token = paired.json()["token"]
        client.post(
            "/api/v1/devices",
            headers=auth_header(token),
            json={"name": "Phone", "platform": "android", "push_token": "push-off"},
        )

        ingested = signed_ingest(
            client,
            {"occurred_at": "2026-10-17T10:00:00Z"},
            nonce="push-disabled",
        )

    assert ingested.status_code == 201
    with sqlite3.connect(database_path) as connection:
        attempt = connection.execute(
            "SELECT status, error FROM notification_delivery_attempts"
        ).fetchone()
    assert attempt == ("disabled", "android push sender is not configured")


def test_cors_only_allows_configured_origin(client: TestClient) -> None:
    allowed = client.options(
        "/api/v1/events",
        headers={
            "Origin": "https://app.example.test",
            "Access-Control-Request-Method": "GET",
        },
    )
    denied = client.options(
        "/api/v1/events",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert allowed.headers["access-control-allow-origin"] == "https://app.example.test"
    assert "access-control-allow-origin" not in denied.headers
