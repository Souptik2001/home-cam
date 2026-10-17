# Amader Home Assistant

A self-hosted doorbell event and notification platform inside the existing `home-cam` repository.

```text
amader-home-assistant/
├── server/  # FastAPI API, SQLite/PostgreSQL persistence, pairing and FCM
├── app/     # One Flutter codebase for Android and iOS
├── deploy/  # Bob server systemd deployment and operations
├── docs/    # Platform build instructions
└── compose.yaml
```

The live camera destination is `https://camera.souptik.dev`.

## Current deployment

The backend runs as `amader-home-assistant.service` on Bob's server and listens only on its Tailscale address:

```text
http://bob-home.taildba06.ts.net:8787
```

Tailscale encrypts this private transport. The API also requires a one-time pairing code for phones and an HMAC signature for doorbell sources. See `deploy/README.md`.

Docker Compose remains available for a future privileged/container deployment. The current account cannot access the host Docker daemon, so the verified live deployment uses a hardened user-level systemd service and SQLite WAL mode.

## Capabilities

- Signed and replay-resistant doorbell event ingestion
- Durable event history
- One-time device pairing and protected API sessions
- Android/iOS device registration
- Optional Firebase Cloud Messaging delivery
- Android high-importance doorbell channel
- iOS Time Sensitive notifications, with Critical Alerts configurable after Apple approval
- Notification routing directly to the camera screen
- In-app camera view with browser fallback

Push delivery remains disabled until Firebase Android/iOS app files and a backend Firebase service-account credential are installed. No Firebase or Apple secret belongs in Git.

## Development verification

```sh
cd server
uv sync
uv run pytest -q
uv run ruff check .
uv run ruff format --check .

cd ../app
flutter pub get
flutter analyze
flutter test
```

## Builds

- Android release APKs are built on Bob's Linux server using the private release keystore stored outside Git.
- Signed iOS IPAs require macOS, Xcode and an Apple Developer signing identity. Follow `docs/ios-build.md` exactly.
