from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

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
                    notification=messaging.AndroidNotification(
                        channel_id="doorbell_alerts",
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
