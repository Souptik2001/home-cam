# Amader Home Assistant

Custom doorbell notification platform contained in the existing `home-cam` repository.

```text
amader-home-assistant/
├── server/  # FastAPI backend and PostgreSQL integration
└── app/     # One Flutter codebase for Android and iOS
```

The live camera destination is `https://camera.souptik.dev`.

## Why Docker for the server

The server is deployed with Docker Compose because it gives us a reproducible API/database environment, isolated dependencies, simple upgrades, health checks, and straightforward backup/rollback. The API binds to localhost by default; the existing HTTPS reverse proxy should publish it when a production hostname is selected.

## Start the server locally

```sh
cd amader-home-assistant
cp .env.example .env
docker compose up --build -d
docker compose ps
curl http://127.0.0.1:8787/health/live
curl http://127.0.0.1:8787/health/ready
```

Do not commit `.env` or any Firebase, APNs, camera, database, or signing credentials.

## Mobile builds

Both mobile platforms use the single Flutter project in `app/`.

- Android APKs can be built on this Linux host after the Android SDK is installed and configured.
- A signed iOS IPA requires macOS/Xcode plus Apple Developer signing and provisioning. The source can be prepared here, but signing must run on a configured Mac or macOS CI runner.

See `app/README.md` and `server/README.md` for component commands.
