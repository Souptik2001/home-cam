from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import UTC, datetime
from signal import pause
from urllib.parse import urlparse

import requests
from gpiozero import Button

GPIO_PIN = 17
INGEST_PATH = "/api/v1/ingest/doorbell"


def build_signed_event(
    server_url: str,
    source_id: str,
    hmac_secret: str,
    *,
    timestamp: int | None = None,
    nonce: str | None = None,
) -> tuple[str, bytes, dict[str, str]]:
    server_url = server_url.rstrip("/")
    parsed = urlparse(server_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("AMADER_HOME_ASSISTANT_URL must be a valid HTTPS URL")
    if not source_id:
        raise ValueError("AMADER_DOORBELL_SOURCE must not be empty")
    if len(hmac_secret) < 32:
        raise ValueError("AMADER_DOORBELL_HMAC_SECRET must be at least 32 characters")

    event_timestamp = int(time.time()) if timestamp is None else int(timestamp)
    event_nonce = secrets.token_urlsafe(24) if nonce is None else nonce
    occurred_at = (
        datetime.fromtimestamp(event_timestamp, UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
    body = json.dumps(
        {
            "event_type": "doorbell",
            "metadata": {"trigger": "gpio17"},
            "occurred_at": occurred_at,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    canonical = b".".join(
        [
            source_id.encode(),
            str(event_timestamp).encode(),
            event_nonce.encode(),
            body,
        ]
    )
    signature = hmac.new(hmac_secret.encode(), canonical, hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-Doorbell-Source": source_id,
        "X-Doorbell-Timestamp": str(event_timestamp),
        "X-Doorbell-Nonce": event_nonce,
        "X-Doorbell-Signature": f"sha256={signature}",
    }
    return server_url + INGEST_PATH, body, headers


def send_doorbell_event(
    server_url: str,
    source_id: str,
    hmac_secret: str,
    *,
    attempts: int = 3,
    timeout: float = 10,
) -> bool:
    url, body, headers = build_signed_event(server_url, source_id, hmac_secret)
    attempts = max(1, attempts)

    for attempt in range(1, attempts + 1):
        try:
            response = requests.post(
                url,
                data=body,
                headers=headers,
                timeout=timeout,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            if attempt == attempts:
                print(
                    f"Doorbell event failed after {attempts} attempts: {exc}",
                    flush=True,
                )
                return False
            print(
                f"Doorbell event attempt {attempt} failed; retrying: {exc}",
                flush=True,
            )
            time.sleep(1)
            continue

        if response.status_code in (200, 201):
            print("Doorbell event delivered successfully!", flush=True)
            return True
        if response.status_code >= 500 and attempt < attempts:
            print(
                f"Doorbell server returned {response.status_code}; retrying.",
                flush=True,
            )
            time.sleep(1)
            continue

        print(
            f"Doorbell event failed with status {response.status_code}: "
            f"{response.text}",
            flush=True,
        )
        return False

    return False


def main() -> None:
    server_url = os.getenv("AMADER_HOME_ASSISTANT_URL", "")
    source_id = os.getenv("AMADER_DOORBELL_SOURCE", "")
    hmac_secret = os.getenv("AMADER_DOORBELL_HMAC_SECRET", "")
    attempts = int(os.getenv("AMADER_REQUEST_ATTEMPTS", "3"))
    timeout = float(os.getenv("AMADER_REQUEST_TIMEOUT_SECONDS", "10"))

    if not server_url or not source_id or not hmac_secret:
        raise SystemExit(
            "AMADER_HOME_ASSISTANT_URL, AMADER_DOORBELL_SOURCE, and "
            "AMADER_DOORBELL_HMAC_SECRET must be configured."
        )

    # Keep GPIO 17 HIGH while idle and trigger when the input becomes LOW.
    button = Button(GPIO_PIN, pull_up=True, bounce_time=0.1)
    button.when_pressed = lambda: send_doorbell_event(
        server_url,
        source_id,
        hmac_secret,
        attempts=attempts,
        timeout=timeout,
    )

    print(
        f"Listening for a LOW signal on GPIO {GPIO_PIN} for source {source_id}...",
        flush=True,
    )
    pause()


if __name__ == "__main__":
    main()
