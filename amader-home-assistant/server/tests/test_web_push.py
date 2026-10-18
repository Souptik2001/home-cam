from __future__ import annotations

import json
import sqlite3

from conftest import RecordingPushSender, auth_header, signed_ingest
from fastapi.testclient import TestClient

from amader_home_assistant.main import create_app


def test_pwa_assets_are_served_with_installable_manifest(client: TestClient) -> None:
    index = client.get("/")
    manifest = client.get("/manifest.webmanifest")
    app_script = client.get("/app.js")
    service_worker = client.get("/sw.js")

    assert index.status_code == 200
    assert index.text.count("Amader Home Assistant") == 2
    assert "PRIVATE DOORBELL" not in index.text
    assert "Doorbell history and instant camera access." not in index.text
    assert 'rel="manifest"' in index.text
    assert 'href="/styles.css?v=3"' in index.text
    assert 'src="/app.js?v=3"' in index.text
    assert manifest.status_code == 200
    assert manifest.json()["display"] == "standalone"
    assert manifest.json()["start_url"] == "/"
    assert app_script.status_code == 200
    assert 'serviceWorker.register("/sw.js?v=3")' in app_script.text
    assert service_worker.status_code == 200
    assert 'const CACHE = "amader-home-v3"' in service_worker.text
    assert '"/styles.css?v=3"' in service_worker.text
    assert '"/app.js?v=3"' in service_worker.text
    assert "notificationclick" in service_worker.text
    assert (
        service_worker.headers["cache-control"] == "no-store, no-cache, must-revalidate"
    )
    assert service_worker.headers["cloudflare-cdn-cache-control"] == "no-store"
    assert service_worker.headers["service-worker-allowed"] == "/"


def test_authenticated_pwa_can_read_vapid_key_and_register_subscription(
    settings, push_sender: RecordingPushSender
) -> None:
    configured = settings.model_copy(
        update={
            "web_push_vapid_public_key": "public-vapid-key",
            "web_push_vapid_private_key": "private-vapid-key",
            "web_push_vapid_subject": "mailto:admin@souptik.dev",
        }
    )
    web_sender = RecordingPushSender(provider_message_id="web-push")
    with TestClient(
        create_app(
            settings=configured,
            push_sender=push_sender,
            web_push_sender=web_sender,
        )
    ) as client:
        paired = client.post(
            "/api/v1/pair", json={"code": "pair-once", "name": "iPhone PWA"}
        )
        token = paired.json()["token"]

        vapid = client.get("/api/v1/push/vapid-public-key", headers=auth_header(token))
        registered = client.post(
            "/api/v1/push/subscriptions",
            headers=auth_header(token),
            json={
                "name": "iPhone PWA",
                "endpoint": "https://web.push.apple.com/example/subscription",
                "expiration_time": None,
                "keys": {"p256dh": "browser-public-key", "auth": "browser-auth"},
            },
        )

    assert vapid.status_code == 200
    assert vapid.json() == {"public_key": "public-vapid-key"}
    assert registered.status_code == 201
    assert registered.json()["platform"] == "web"


def test_web_subscription_requires_approved_https_endpoint(
    paired_client: tuple[TestClient, str],
) -> None:
    client, token = paired_client

    insecure = client.post(
        "/api/v1/push/subscriptions",
        headers=auth_header(token),
        json={
            "name": "Unsafe browser",
            "endpoint": "http://push.example.test/subscription",
            "keys": {"p256dh": "browser-public-key", "auth": "browser-auth"},
        },
    )
    unapproved = client.post(
        "/api/v1/push/subscriptions",
        headers=auth_header(token),
        json={
            "name": "Unapproved browser",
            "endpoint": "https://127.0.0.1/subscription",
            "keys": {"p256dh": "browser-public-key", "auth": "browser-auth"},
        },
    )

    assert insecure.status_code == 422
    assert unapproved.status_code == 422
    assert "approved push service" in unapproved.text


def test_generic_device_route_rejects_web_platform(
    paired_client: tuple[TestClient, str],
) -> None:
    client, token = paired_client

    response = client.post(
        "/api/v1/devices",
        headers=auth_header(token),
        json={"name": "Bypass", "platform": "web", "push_token": "{}"},
    )

    assert response.status_code == 422


def test_doorbell_event_routes_web_device_to_web_push_sender(
    settings, push_sender: RecordingPushSender, database_path
) -> None:
    configured = settings.model_copy(
        update={
            "web_push_vapid_public_key": "public-vapid-key",
            "web_push_vapid_private_key": "private-vapid-key",
            "web_push_vapid_subject": "mailto:admin@souptik.dev",
        }
    )
    web_sender = RecordingPushSender(provider_message_id="web-provider-message")
    with TestClient(
        create_app(
            settings=configured,
            push_sender=push_sender,
            web_push_sender=web_sender,
        )
    ) as client:
        paired = client.post(
            "/api/v1/pair", json={"code": "pair-once", "name": "iPhone PWA"}
        )
        token = paired.json()["token"]
        subscription = {
            "endpoint": "https://web.push.apple.com/example/subscription",
            "expirationTime": None,
            "keys": {"p256dh": "browser-public-key", "auth": "browser-auth"},
        }
        registered = client.post(
            "/api/v1/push/subscriptions",
            headers=auth_header(token),
            json={
                "name": "iPhone PWA",
                "endpoint": subscription["endpoint"],
                "expiration_time": None,
                "keys": subscription["keys"],
            },
        )
        assert registered.status_code == 201

        ingested = signed_ingest(
            client,
            {"occurred_at": "2026-10-17T10:00:00Z"},
            nonce="web-push-event",
        )

    assert ingested.status_code == 201
    assert push_sender.calls == []
    assert len(web_sender.calls) == 1
    stored_subscription, message = web_sender.calls[0]
    assert json.loads(stored_subscription) == subscription
    assert message.data["camera_url"] == "https://camera.souptik.dev"
    assert message.data["route"] == "/camera"
    with sqlite3.connect(database_path) as connection:
        attempt = connection.execute(
            "SELECT status, provider_message_id FROM notification_delivery_attempts"
        ).fetchone()
    assert attempt == ("sent", "web-provider-message")


def test_disconnect_revokes_session_and_stops_web_push_delivery(
    settings, push_sender: RecordingPushSender, database_path
) -> None:
    web_sender = RecordingPushSender(provider_message_id="should-not-send")
    with TestClient(
        create_app(
            settings=settings,
            push_sender=push_sender,
            web_push_sender=web_sender,
        )
    ) as client:
        paired = client.post(
            "/api/v1/pair", json={"code": "pair-once", "name": "iPhone PWA"}
        )
        token = paired.json()["token"]
        registered = client.post(
            "/api/v1/push/subscriptions",
            headers=auth_header(token),
            json={
                "name": "iPhone PWA",
                "endpoint": "https://web.push.apple.com/disconnect-test",
                "keys": {"p256dh": "browser-public-key", "auth": "browser-auth"},
            },
        )
        assert registered.status_code == 201

        disconnected = client.post(
            "/api/v1/session/disconnect", headers=auth_header(token)
        )
        ingested = signed_ingest(
            client,
            {"occurred_at": "2026-10-17T10:00:00Z"},
            nonce="after-disconnect",
        )
        rejected = client.get("/api/v1/events", headers=auth_header(token))

    assert disconnected.status_code == 204
    assert ingested.status_code == 201
    assert rejected.status_code == 401
    assert web_sender.calls == []
    with sqlite3.connect(database_path) as connection:
        enabled, active = connection.execute(
            "SELECT pd.enabled, ps.active FROM paired_devices pd "
            "JOIN paired_sessions ps ON ps.id=pd.session_id"
        ).fetchone()
        attempts = connection.execute(
            "SELECT COUNT(*) FROM notification_delivery_attempts"
        ).fetchone()[0]
    assert (enabled, active) == (0, 0)
    assert attempts == 0
