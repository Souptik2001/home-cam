# Deploying the server on Bob

The live single-household deployment uses a user-level systemd service, SQLite, and a listener bound only to Bob's Tailscale address. Cloudflare Tunnel is the only intended public ingress.

## Addresses

- Private origin: `http://100.94.160.64:8787`
- Temporary private DNS: `http://bob-home.taildba06.ts.net:8787`
- Public application: `https://amader-home-assistant.souptik.dev`
- Camera: `https://camera.souptik.dev`

The origin must not listen on `0.0.0.0`, the LAN address, or a router-forwarded port. The Android application and iPhone PWA use only the public HTTPS application hostname.

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

Secret files are mode `0600`; their containing directories are mode `0700`. Never place VAPID, Firebase, HMAC, pairing, Cloudflare, or Android-signing credentials inside the repository.

## Required Web Push environment

`server.env` must include:

```ini
WEB_PUSH_VAPID_PUBLIC_KEY=<87-character URL-safe application server key>
WEB_PUSH_VAPID_PRIVATE_KEY_PATH=/home/bob-home/.config/amader-home-assistant/vapid/private_key.pem
WEB_PUSH_VAPID_SUBJECT=mailto:<operator-address>
WEB_PUSH_ALLOWED_HOSTS=["web.push.apple.com","fcm.googleapis.com"]
WEB_PUSH_TIMEOUT_SECONDS=5
PAIRING_ATTEMPTS_PER_MINUTE=5
PAIRING_RATE_LIMIT_MAX_CLIENTS=2048
TRUSTED_PROXY_NETWORKS=[]
```

`TRUSTED_PROXY_NETWORKS` stays empty for direct private access. After the Cloudflare route is active, set it only to the connector's observed origin-side IP/CIDR so `CF-Connecting-IP` can safely separate pairing-rate-limit buckets. Do not trust arbitrary forwarding headers from Tailnet or LAN clients.

## Install/update

```sh
cd /home/bob-home/home-cam/amader-home-assistant/server
/home/bob-home/.hermes/bin/uv sync --frozen --no-dev

install -Dm600 ../deploy/amader-home-assistant.service \
  /home/bob-home/.config/systemd/user/amader-home-assistant.service
systemctl --user daemon-reload
systemctl --user enable --now amader-home-assistant.service
```

Confirm the current Tailscale IP with `tailscale ip -4` before installing the checked-in unit.

## Cloudflare public hostname

Use the existing remotely managed Cloudflare Tunnel for `souptik.dev`:

1. Open **Cloudflare Zero Trust → Networks → Tunnels**.
2. Open the existing healthy tunnel.
3. Add a public hostname:
   - Subdomain: `amader-home-assistant`
   - Domain: `souptik.dev`
   - Type: `HTTP`
   - URL: `100.94.160.64:8787`
4. Do not configure a public router port-forward.
5. Do not place Cloudflare Access login in front of this hostname: iPhone background Web Push and service-worker API refreshes must reach the application's own bearer-authenticated endpoints. Pairing throttling and HMAC ingestion remain enforced by the application.
6. Read the origin-side connector address from the Uvicorn access log, set the narrowest correct `TRUSTED_PROXY_NETWORKS` entry, restart the API, and verify that spoofed `CF-Connecting-IP` from a non-trusted peer is ignored.

`deploy/amader-cloudflared.service` is an optional host-level connector template. Its token file must remain outside Git. Do not start a duplicate connector when the existing tunnel connector is healthy.

## Verification

```sh
systemctl --user is-enabled amader-home-assistant.service
systemctl --user is-active amader-home-assistant.service
curl --fail http://100.94.160.64:8787/health/live
curl --fail http://100.94.160.64:8787/health/ready
ss -ltnp '( sport = :8787 )'

curl --fail https://amader-home-assistant.souptik.dev/health/live
curl --fail https://amader-home-assistant.souptik.dev/health/ready
curl --fail https://amader-home-assistant.souptik.dev/manifest.webmanifest | python3 -m json.tool
curl --fail --head https://amader-home-assistant.souptik.dev/sw.js
```

The final device acceptance test must install the PWA from the public HTTPS hostname, pair it, enable notifications, ring the doorbell, and verify a locked-screen notification whose tap opens `https://camera.souptik.dev`.

## Push notifications

The iPhone PWA uses VAPID Web Push. Native Android Firebase delivery remains safely disabled until one of these is configured outside Git:

```ini
FIREBASE_CREDENTIALS_PATH=/home/bob-home/.config/amader-home-assistant/firebase-service-account.json
```

or `FIREBASE_CREDENTIALS_JSON`.

## Backup

Use SQLite's online backup API while the service is active:

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
journalctl --user -u amader-home-assistant.service -n 100 --no-pager
systemctl --user disable --now amader-home-assistant.service
```
