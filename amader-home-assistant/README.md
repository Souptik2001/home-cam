# Amader Home Assistant

A self-hosted doorbell event and notification platform inside the existing `home-cam` repository.

```text
amader-home-assistant/
├── server/  # FastAPI API, persistence, PWA frontend, Web Push and FCM
├── app/     # Native Flutter Android app (iOS source retained, PWA is the free iPhone path)
├── deploy/  # Bob server systemd deployment and operations
├── docs/    # Installation and platform instructions
└── compose.yaml
```

The live camera destination is `https://camera.souptik.dev`. The planned public application origin is `https://amader-home-assistant.souptik.dev`.

## Client architecture

- **Android:** signed native Flutter application with an FCM notification channel.
- **iPhone:** installable PWA served by the FastAPI server. It uses standards-based Web Push with self-owned VAPID keys, so it does not require Firebase or a paid Apple Developer membership.
- **Shared backend:** pairing, event history, camera configuration, device registration, notification delivery attempts, and signed doorbell ingestion.

For iPhone push, Safari creates a browser subscription backed by Apple's push service. The server encrypts each notification for that subscription and sends it using its VAPID identity. The user must add the site to the iPhone Home Screen before enabling notifications.

## Current deployment

The backend runs as `amader-home-assistant.service` on Bob's server. Until the Cloudflare hostname is configured, its verified private endpoint is:

```text
http://bob-home.taildba06.ts.net:8787
```

The public deployment will use a Cloudflare Tunnel hostname:

```text
https://amader-home-assistant.souptik.dev
```

The origin remains non-public and the Cloudflare tunnel forwards only the application hostname. API bearer sessions, one-time pairing, pairing-rate limits, and HMAC-signed doorbell ingestion remain enforced at the application layer.

Docker Compose remains available for a future privileged/container deployment. The verified live deployment currently uses a hardened user-level systemd service and SQLite WAL mode.

## Capabilities

- Signed, bounded, replay-resistant doorbell event ingestion
- Durable newest-first event history with explicit UTC timestamps
- One-time pairing, protected API sessions, and pairing throttling
- Installable responsive PWA with iPhone Home Screen support
- Standards-based encrypted Web Push using private VAPID keys
- Notification taps opening `https://camera.souptik.dev`
- Native Android application and optional Firebase Cloud Messaging
- Per-device notification delivery-attempt logging
- Restricted camera navigation and HTTPS-only mobile server configuration

## Development verification

```sh
cd server
uv sync
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv build
node --check src/amader_home_assistant/web/app.js
node --check src/amader_home_assistant/web/sw.js

cd ../app
flutter pub get
flutter analyze
flutter test
```

## Builds

- Android release APKs are built on Bob's Linux server using a private release keystore stored outside Git.
- The iPhone PWA needs no IPA. In Safari, open the public HTTPS hostname, choose **Share → Add to Home Screen**, launch it from the Home Screen, pair it, and press **Enable notifications**.
