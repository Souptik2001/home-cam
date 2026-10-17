# Deploying the server on Bob

The live single-household deployment uses a user-level systemd service, SQLite, and a listener bound only to Bob's Tailscale address.

## Live addresses

- API: `http://bob-home.taildba06.ts.net:8787`
- Camera: `https://camera.souptik.dev`

The API URL is HTTP at the application layer, but it is reachable only through the encrypted Tailscale network. The service does not listen on the LAN or public interfaces. Android and iOS contain narrowly scoped transport exceptions for this exact MagicDNS hostname.

## Files outside Git

```text
~/.config/amader-home-assistant/server.env
~/.config/amader-home-assistant/pairing-code.txt
~/.config/amader-home-assistant/front-door-hmac-secret.txt
~/.local/share/amader-home-assistant/data/amader-home-assistant.db
```

All secret files are mode `0600`; their containing directory is mode `0700`.

## Install/update

```sh
cd /home/bob-home/home-cam/amader-home-assistant/server
/home/bob-home/.hermes/bin/uv sync --frozen --no-dev

install -Dm600 ../deploy/amader-home-assistant.service \
  /home/bob-home/.config/systemd/user/amader-home-assistant.service
systemctl --user daemon-reload
systemctl --user enable --now amader-home-assistant.service
```

The checked-in unit is a template. Confirm the current Tailscale IP with `tailscale ip -4` before installing it.

## Verification

```sh
systemctl --user is-enabled amader-home-assistant.service
systemctl --user is-active amader-home-assistant.service
curl --fail http://bob-home.taildba06.ts.net:8787/health/live
curl --fail http://bob-home.taildba06.ts.net:8787/health/ready
ss -ltnp '( sport = :8787 )'
```

## Push notifications

Push delivery is deliberately disabled until a Firebase service-account credential is installed. Configure one of:

```ini
FIREBASE_CREDENTIALS_PATH=/home/bob-home/.config/amader-home-assistant/firebase-service-account.json
```

or `FIREBASE_CREDENTIALS_JSON`. Keep the credential outside Git with mode `0600`, then restart the service.

Set `IOS_CRITICAL_ALERTS_ENABLED=true` only after Apple grants the Critical Alerts entitlement. Otherwise iOS receives a Time Sensitive request.

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
