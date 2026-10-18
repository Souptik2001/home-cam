# Deploying the server on Bob

The live single-household deployment runs in Docker with SQLite persistence. The existing `frigate-cloudflared` connector reaches the API through a dedicated bridge network; Cloudflare Tunnel is the only intended public ingress.

## Addresses and containers

- Public application: `https://amader-home-assistant.souptik.dev`
- Tunnel origin: `http://amader-home-assistant:8787`
- API container: `amader-home-assistant` (`172.30.250.3` on `amader-home-tunnel`)
- Cloudflare connector: `frigate-cloudflared` (`172.30.250.2` on `amader-home-tunnel`)
- Tailnet-only maintenance origin: `http://100.94.160.64:8787`
- Camera: `https://camera.souptik.dev`

The host port is bound only to Bob's Tailscale address. Do not bind it to `0.0.0.0`, publish it on the LAN, or create a router port-forward. Android and the iPhone PWA use only the public HTTPS hostname.

## Files outside Git

```text
~/.config/amader-home-assistant/server.env
~/.config/amader-home-assistant/pairing-code.txt
~/.config/amader-home-assistant/front-door-hmac-secret.txt
~/.config/amader-home-assistant/vapid/private_key.pem
~/.config/amader-home-assistant/vapid/public_key.pem
~/.config/amader-home-assistant/vapid/application-server-key.txt
~/.local/share/amader-home-assistant/data/amader-home-assistant.db
```

The Compose service bind-mounts the data directory read-write and the VAPID private key read-only. Secret files remain mode `0600`; containing directories remain mode `0700`. Never place VAPID, Firebase, HMAC, pairing, Cloudflare, or Android-signing credentials inside the repository.

## Container network

The dedicated external bridge is created once:

```sh
docker network create \
  --driver bridge \
  --subnet 172.30.250.0/24 \
  --gateway 172.30.250.1 \
  amader-home-tunnel
```

The Frigate Compose definition attaches `frigate-cloudflared` to both `frigate_default` and `amader-home-tunnel`, with address `172.30.250.2`. Keeping cloudflared on `frigate_default` preserves `http://frigate:5000` for the camera route. The checked-in `deploy/frigate-cloudflared.network.override.yaml` records this integration for hosts whose primary Frigate Compose file does not already contain the equivalent block:

```sh
docker compose \
  -f /home/bob-home/frigate/compose.yaml \
  -f /home/bob-home/home-cam/amader-home-assistant/deploy/frigate-cloudflared.network.override.yaml \
  up -d --no-deps cloudflared
```

The API joins only `amader-home-tunnel`, with address `172.30.250.3`.

## Required Web Push environment

`~/.config/amader-home-assistant/server.env` includes the application settings and secrets. The container overrides host-specific paths with:

```ini
DATABASE_URL=sqlite:////app/data/amader-home-assistant.db
WEB_PUSH_VAPID_PRIVATE_KEY_PATH=/run/secrets/web-push-vapid-private.pem
TRUSTED_PROXY_NETWORKS=["172.30.250.2/32"]
```

The exact proxy address prevents an untrusted Tailnet or LAN client from spoofing `CF-Connecting-IP` for pairing-rate-limit identity.

## Build and update

```sh
cd /home/bob-home/home-cam/amader-home-assistant
./deploy/preflight-docker.sh
docker compose config --quiet
docker compose up -d --build api
```

The preflight resolves the same Compose interpolation and project `.env` values used by deployment. It fails closed if the selected SQLite file or VAPID key is missing, runtime UID/GID `1000:1000` cannot read/write the database directory and WAL sidecars, the database integrity/schema check fails, the shared network has an unexpected subnet, or cloudflared is not attached at its trusted address. Long-form bind mounts also disable Docker's automatic creation of missing source paths, and the container refuses to start without the existing database file.

The application image is tagged `amader-home-assistant-api:0.2.0`; its Python and `uv` bases are pinned by digest for deterministic rebuilds and a named rollback target. The image runs as UID/GID `1000:1000`, has a read-only root filesystem, drops all Linux capabilities, sets `no-new-privileges`, mounts only `/tmp` as tmpfs, and uses one Uvicorn worker because SQLite-backed in-memory throttling is intentionally single-instance.

## Cloudflare public hostname

Use the existing remotely managed Cloudflare Tunnel for `souptik.dev`:

1. Open **Cloudflare Zero Trust → Networks → Tunnels**.
2. Open the existing healthy tunnel.
3. Configure the route:
   - Hostname: `amader-home-assistant.souptik.dev`
   - Type: `HTTP`
   - URL: `amader-home-assistant:8787`
   - Effective origin: `http://amader-home-assistant:8787`
4. Do not configure a public router port-forward.
5. Do not place Cloudflare Access in front of this hostname. Background Web Push and service-worker API requests use the application's bearer/HMAC authentication and cannot complete an interactive Access redirect.

## Verification

```sh
docker inspect amader-home-assistant \
  --format 'status={{.State.Status}} health={{.State.Health.Status}}'

docker run --rm --network container:frigate-cloudflared \
  curlimages/curl:8.16.0 --fail \
  http://amader-home-assistant:8787/health/ready

curl --fail http://100.94.160.64:8787/health/ready
curl --fail https://amader-home-assistant.souptik.dev/health/ready
curl --fail https://amader-home-assistant.souptik.dev/manifest.webmanifest | python3 -m json.tool
curl --fail --head 'https://amader-home-assistant.souptik.dev/sw.js?v=3'
```

The service-worker response must include `Cache-Control: no-store, no-cache, must-revalidate`, `Service-Worker-Allowed: /`, and a Cloudflare cache status of `BYPASS` or `DYNAMIC`.

The final device acceptance test installs the PWA from the public HTTPS hostname, pairs it, enables notifications, rings the doorbell, and verifies a locked-screen notification whose tap opens `https://camera.souptik.dev`.

## Push notifications

The iPhone PWA uses VAPID Web Push. Native Android Firebase delivery remains safely disabled until one of these is configured outside Git:

```ini
FIREBASE_CREDENTIALS_PATH=/home/bob-home/.config/amader-home-assistant/firebase-service-account.json
```

or `FIREBASE_CREDENTIALS_JSON`.

## Backup

Use SQLite's online backup API while the container is active:

```sh
python3 - <<'PY'
import sqlite3
from pathlib import Path
source = Path.home() / '.local/share/amader-home-assistant/data/amader-home-assistant.db'
destination = Path.home() / '.local/share/amader-home-assistant/data/amader-home-assistant.backup.db'
with sqlite3.connect(source) as src, sqlite3.connect(destination) as dst:
    src.backup(dst)
print(destination)
PY
```

## Logs and rollback

```sh
docker logs --tail 100 amader-home-assistant
docker compose stop api
systemctl --user enable --now amader-home-assistant.service
```

The retired systemd unit remains available only as a rollback path. Never run the systemd and Docker instances concurrently against the same SQLite database.
