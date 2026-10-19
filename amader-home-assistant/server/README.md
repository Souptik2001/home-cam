# Amader Home Assistant Server

FastAPI v1 backend for a single-household doorbell. It stores events before
attempting notifications, uses SQLite by default, and can use any SQLAlchemy URL
supported by the installed driver (PostgreSQL via `psycopg` is included).

## Local development

```sh
cp .env.example .env
# Replace every placeholder secret in .env.
uv sync
uv run pytest
uv run uvicorn amader_home_assistant.main:app --reload
```

The default database is `./data/amader-home-assistant.db`. Tables and indexes are
created deterministically at application startup. For a service deployment, keep
the database on persistent storage, for example:

```sh
DATABASE_URL=sqlite:////var/lib/amader-home-assistant/app.db
```

## Required security configuration

- `PAIRING_CODE`: a one-time code. A successful pairing stores only its SHA-256
  hash. Rotate this environment value to allow another pairing.
- `DOORBELL_HMAC_SECRETS`: JSON mapping source IDs to shared secrets, for example
  `{"front-door":"a-long-random-secret"}`.
- `ALLOWED_ORIGINS`: JSON list of exact browser origins. An empty list enables no
  CORS origins; wildcard CORS is never configured.

Bearer session tokens are returned only once by `POST /api/v1/pair` and stored
only as hashes. Run the API behind HTTPS; pairing codes, bearer tokens, push
tokens, and HMAC secrets must not be logged.

## Doorbell ingestion signature

`POST /api/v1/ingest/doorbell` requires these headers:

- `X-Doorbell-Source`
- `X-Doorbell-Timestamp` (Unix seconds)
- `X-Doorbell-Nonce` (unique per source)
- `X-Doorbell-Signature`

Calculate the lowercase SHA-256 HMAC hex digest over the exact request bytes:

```text
source_id + "." + timestamp + "." + nonce + "." + raw_json_body
```

The timestamp must be within `HMAC_MAX_AGE_SECONDS` (300 by default). The unique
source/nonce pair makes retries idempotent: the first request returns `201`, and
a valid retry returns the existing event with `200` and `duplicate: true`.

Example event body:

```json
{
  "occurred_at": "2026-10-17T10:00:00Z",
  "event_type": "doorbell",
  "metadata": {"motion": true}
}
```

## API

Public machine and frontend endpoints:

- `GET /` (installable PWA)
- `GET /manifest.webmanifest`
- `GET /sw.js`
- `GET /health/live`
- `GET /health/ready`
- `POST /api/v1/pair`
- `POST /api/v1/ingest/doorbell` (HMAC authenticated)

Bearer-protected household endpoints:

- `GET /api/v1/events?limit=50` (newest first; maximum 200)
- `POST /api/v1/devices`
- `PUT /api/v1/devices/{device_id}`
- `GET /api/v1/camera/config` (returns `https://camera.souptik.dev/#pi_cam_2` by default)
- `GET /api/v1/push/vapid-public-key`
- `POST /api/v1/push/subscriptions`
- `POST /api/v1/session/disconnect`

## Push notifications

The iPhone PWA uses standards-based Web Push. Configure these five values:

- `WEB_PUSH_VAPID_PUBLIC_KEY`
- `WEB_PUSH_VAPID_PRIVATE_KEY_PATH`
- `WEB_PUSH_VAPID_SUBJECT` (a `mailto:` or HTTPS operator contact)
- `WEB_PUSH_ALLOWED_HOSTS` (exact browser push-service host allow-list)
- `WEB_PUSH_TIMEOUT_SECONDS` (short finite provider timeout)

Generate the private identity once, store it outside Git with mode `0600`, and keep
it stable. Replacing the VAPID key requires browsers to subscribe again. Web Push
payloads are encrypted for each browser subscription; endpoints are accepted only
from the explicit allow-list, redirects are disabled, and provider I/O runs outside
the request event loop. The server records each attempt separately from the durable
doorbell event.

The native Android app can additionally use Firebase. Set either
`FIREBASE_CREDENTIALS_PATH` or `FIREBASE_CREDENTIALS_JSON` to enable Firebase
Admin delivery. When a platform sender is absent, ingestion remains operational
and its delivery attempt is recorded as `disabled`. Provider exceptions are
recorded as failed attempts and never roll back or delete the doorbell event.

## Docker

Build from this directory:

```sh
docker build -t amader-home-assistant-server .
docker run --rm -p 8000:8000 \
  --env-file .env \
  -e WEB_PUSH_VAPID_PRIVATE_KEY_PATH=/run/secrets/web-push-vapid-private.pem \
  -v /home/bob-home/.config/amader-home-assistant/vapid/private_key.pem:/run/secrets/web-push-vapid-private.pem:ro \
  -v amader-home-data:/app/data \
  amader-home-assistant-server
```

The image runs as a non-root user and declares `/app/data` as its persistent
volume. Publish the service through an HTTPS reverse proxy rather than exposing
it directly to the internet.
