from __future__ import annotations

import json

import pytest

from amader_home_assistant.config import Settings
from amader_home_assistant.push import (
    PushMessage,
    WebPushSender,
    create_web_push_sender,
)


class FakeResponse:
    def __init__(self) -> None:
        self.headers = {"location": "provider-message"}


def test_web_push_sender_encrypts_minimal_notification_payload(monkeypatch) -> None:
    captured = {}

    def fake_webpush(**kwargs):
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr("pywebpush.webpush", fake_webpush)
    sender = WebPushSender(
        "/secure/vapid-private.pem",
        "mailto:admin@souptik.dev",
        allowed_hosts={"web.push.apple.com"},
        timeout_seconds=4.0,
    )
    subscription = {
        "endpoint": "https://web.push.apple.com/subscription",
        "expirationTime": None,
        "keys": {"p256dh": "public-key", "auth": "auth-key"},
    }

    result = sender.send(
        json.dumps(subscription),
        PushMessage(
            title="Someone is at the door",
            body="The doorbell was pressed.",
            data={
                "event_id": "event-1",
                "route": "/camera",
                "camera_url": "https://camera.souptik.dev",
            },
        ),
    )

    assert captured["subscription_info"] == subscription
    assert captured["vapid_private_key"] == "/secure/vapid-private.pem"
    assert captured["vapid_claims"] == {"sub": "mailto:admin@souptik.dev"}
    assert captured["ttl"] == 60
    assert captured["timeout"] == 4.0
    assert captured["requests_session"].max_redirects == 0
    assert json.loads(captured["data"])["data"]["route"] == "/camera"
    assert result.provider_message_id == "provider-message"


def test_web_push_sender_rejects_unapproved_stored_endpoint() -> None:
    sender = WebPushSender(
        "/secure/vapid-private.pem",
        "mailto:admin@souptik.dev",
        allowed_hosts={"web.push.apple.com"},
        timeout_seconds=4.0,
    )
    message = PushMessage(title="Doorbell", body="Ring", data={})

    with pytest.raises(ValueError, match="approved push service"):
        sender.send(
            json.dumps(
                {
                    "endpoint": "https://127.0.0.1/internal",
                    "keys": {"p256dh": "public-key", "auth": "auth-key"},
                }
            ),
            message,
        )


def test_create_web_push_sender_rejects_missing_private_key_file(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        web_push_vapid_public_key="B" + "a" * 86,
        web_push_vapid_private_key_path=tmp_path / "missing.pem",
        web_push_vapid_subject="mailto:admin@example.com",
    )

    with pytest.raises(ValueError, match="does not exist"):
        create_web_push_sender(settings)


def test_create_web_push_sender_rejects_mismatched_key_pair(tmp_path) -> None:
    from py_vapid import Vapid02

    private_key = tmp_path / "private.pem"
    vapid = Vapid02()
    vapid.generate_keys()
    vapid.save_key(str(private_key))
    settings = Settings(
        _env_file=None,
        web_push_vapid_public_key="B" + "a" * 86,
        web_push_vapid_private_key_path=private_key,
        web_push_vapid_subject="mailto:admin@example.com",
    )

    with pytest.raises(ValueError, match="does not match"):
        create_web_push_sender(settings)
