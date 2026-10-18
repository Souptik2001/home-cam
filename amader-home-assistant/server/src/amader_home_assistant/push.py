from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

import requests

from amader_home_assistant.config import Settings


@dataclass(frozen=True)
class PushMessage:
    title: str
    body: str
    data: dict[str, str]


@dataclass(frozen=True)
class PushResult:
    provider_message_id: str | None = None


class PushSender(Protocol):
    enabled: bool

    def send(self, token: str, message: PushMessage) -> PushResult: ...


class DisabledPushSender:
    enabled = False

    def send(self, token: str, message: PushMessage) -> PushResult:
        return PushResult()


def validate_web_push_endpoint(endpoint: str, allowed_hosts: set[str]) -> None:
    parsed = urlparse(endpoint)
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https"
        or not host
        or host not in allowed_hosts
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
    ):
        raise ValueError("web push endpoint is not an approved push service")


class WebPushSender:
    enabled = True

    def __init__(
        self,
        private_key: str,
        subject: str,
        *,
        allowed_hosts: set[str],
        timeout_seconds: float,
    ) -> None:
        self._private_key = private_key
        self._subject = subject
        self._allowed_hosts = {host.lower() for host in allowed_hosts}
        self._timeout_seconds = timeout_seconds

    def send(self, token: str, message: PushMessage) -> PushResult:
        from pywebpush import webpush

        subscription = json.loads(token)
        endpoint = subscription.get("endpoint")
        if not isinstance(endpoint, str):
            raise TypeError("web push subscription is missing its endpoint")
        validate_web_push_endpoint(endpoint, self._allowed_hosts)
        session = requests.Session()
        session.max_redirects = 0
        try:
            response = webpush(
                subscription_info=subscription,
                data=json.dumps(
                    {
                        "title": message.title,
                        "body": message.body,
                        "data": message.data,
                    },
                    separators=(",", ":"),
                ),
                vapid_private_key=self._private_key,
                vapid_claims={"sub": self._subject},
                ttl=60,
                timeout=self._timeout_seconds,
                requests_session=session,
            )
        finally:
            session.close()
        return PushResult(provider_message_id=response.headers.get("location"))


class FirebasePushSender:
    enabled = True

    def __init__(
        self,
        credential_source: str | dict[str, object],
        *,
        ios_critical_alerts_enabled: bool = False,
    ) -> None:
        import firebase_admin
        from firebase_admin import credentials

        credential = credentials.Certificate(credential_source)
        self._app = firebase_admin.initialize_app(credential)
        self._ios_critical_alerts_enabled = ios_critical_alerts_enabled

    def send(self, token: str, message: PushMessage) -> PushResult:
        from firebase_admin import messaging

        ios_sound: str | messaging.CriticalSound
        if self._ios_critical_alerts_enabled:
            ios_sound = messaging.CriticalSound(
                name="default", critical=True, volume=1.0
            )
        else:
            ios_sound = "default"

        provider_id = messaging.send(
            messaging.Message(
                token=token,
                notification=messaging.Notification(
                    title=message.title, body=message.body
                ),
                data=message.data,
                android=messaging.AndroidConfig(
                    priority="high",
                    ttl=timedelta(seconds=0),
                    notification=messaging.AndroidNotification(
                        channel_id="doorbell_critical_alerts",
                        sound="default",
                        default_vibrate_timings=True,
                        priority="max",
                    ),
                ),
                apns=messaging.APNSConfig(
                    headers={"apns-priority": "10"},
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound=ios_sound,
                            custom_data={"interruption-level": "time-sensitive"},
                        )
                    ),
                ),
            ),
            app=self._app,
        )
        return PushResult(provider_message_id=provider_id)


def _derive_vapid_public_key(private_key: str, private_key_path: str | None) -> str:
    from py_vapid import Vapid02

    if private_key_path is not None:
        path = Path(private_key_path)
        if not path.is_file():
            raise ValueError(f"Web Push VAPID private key does not exist: {path}")
        vapid = Vapid02.from_file(str(path))
    elif "-----BEGIN" in private_key:
        vapid = Vapid02.from_pem(private_key.encode())
    else:
        vapid = Vapid02.from_string(private_key)
    numbers = vapid.public_key.public_numbers()
    raw = b"\x04" + numbers.x.to_bytes(32, "big") + numbers.y.to_bytes(32, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def create_web_push_sender(settings: Settings) -> PushSender:
    private_key = settings.web_push_vapid_private_key.get_secret_value()
    private_key_path = (
        str(settings.web_push_vapid_private_key_path)
        if settings.web_push_vapid_private_key_path is not None
        else None
    )
    configured = [
        bool(private_key or private_key_path),
        bool(settings.web_push_vapid_public_key),
        bool(settings.web_push_vapid_subject),
    ]
    if any(configured) and not all(configured):
        raise ValueError("Web Push VAPID configuration is incomplete")
    if not all(configured):
        return DisabledPushSender()
    derived_public_key = _derive_vapid_public_key(private_key, private_key_path)
    if derived_public_key != settings.web_push_vapid_public_key:
        raise ValueError("Web Push VAPID public key does not match the private key")
    return WebPushSender(
        private_key_path or private_key,
        settings.web_push_vapid_subject,
        allowed_hosts=set(settings.web_push_allowed_hosts),
        timeout_seconds=settings.web_push_timeout_seconds,
    )


def create_push_sender(settings: Settings) -> PushSender:
    sender_options = {
        "ios_critical_alerts_enabled": settings.ios_critical_alerts_enabled,
    }
    if settings.firebase_credentials_json is not None:
        raw = settings.firebase_credentials_json.get_secret_value()
        return FirebasePushSender(json.loads(raw), **sender_options)
    if settings.firebase_credentials_path is not None:
        return FirebasePushSender(
            str(settings.firebase_credentials_path), **sender_options
        )
    return DisabledPushSender()
