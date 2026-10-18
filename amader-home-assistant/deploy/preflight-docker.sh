#!/usr/bin/env bash
set -euo pipefail

NETWORK="amader-home-tunnel"
CLOUDFLARED_CONTAINER="frigate-cloudflared"
API_CONTAINER="amader-home-assistant"

fail() {
  printf 'preflight failed: %s\n' "$*" >&2
  exit 1
}

command -v docker >/dev/null || fail "docker is unavailable"
docker info >/dev/null 2>&1 || fail "current user cannot access the Docker daemon"
docker compose config --quiet

# Resolve the exact bind sources and runtime identity after Compose has applied
# shell variables and the project .env file. The JSON is consumed internally so
# application secrets expanded from env_file are never printed.
mapfile -t RESOLVED < <(python3 <<'PY'
import json
import subprocess

config = json.loads(
    subprocess.check_output(
        ["docker", "compose", "config", "--format", "json"],
        text=True,
    )
)
api = config["services"]["api"]
volumes = {item["target"]: item["source"] for item in api.get("volumes", [])}
for target in (
    "/app/data",
    "/run/secrets/web-push-vapid-private.pem",
    "/run/secrets/firebase-service-account.json",
):
    source = volumes.get(target)
    if not source:
        raise SystemExit(f"Compose is missing the required bind for {target}")
    print(source)
print(api.get("user") or "")
PY
)

[[ ${#RESOLVED[@]} -eq 4 ]] || fail "could not resolve Compose bind sources"
DATA_DIR="${RESOLVED[0]}"
VAPID_KEY="${RESOLVED[1]}"
FIREBASE_CREDENTIALS="${RESOLVED[2]}"
RUNTIME_USER="${RESOLVED[3]}"
DATABASE_FILE="$DATA_DIR/amader-home-assistant.db"

[[ "$RUNTIME_USER" == "1000:1000" ]] || fail "Compose runtime user must be 1000:1000"
[[ -d "$DATA_DIR" ]] || fail "data directory does not exist: $DATA_DIR"
[[ -f "$DATABASE_FILE" ]] || fail "existing SQLite database is missing: $DATABASE_FILE"
[[ -f "$VAPID_KEY" ]] || fail "VAPID private key is missing: $VAPID_KEY"
[[ -f "$FIREBASE_CREDENTIALS" ]] || fail "Firebase service-account credential is missing: $FIREBASE_CREDENTIALS"

python3 - "$DATA_DIR" "$DATABASE_FILE" "$VAPID_KEY" "$FIREBASE_CREDENTIALS" "$RUNTIME_USER" <<'PY'
import json
import sqlite3
import sys
from pathlib import Path


data_dir = Path(sys.argv[1])
database_file = Path(sys.argv[2])
vapid_key = Path(sys.argv[3])
firebase_credentials = Path(sys.argv[4])
uid, gid = (int(value) for value in sys.argv[5].split(":", 1))


def require_mode(path: Path, required: int, label: str) -> None:
    metadata = path.stat()
    if metadata.st_uid == uid:
        available = (metadata.st_mode >> 6) & 0o7
    elif metadata.st_gid == gid:
        available = (metadata.st_mode >> 3) & 0o7
    else:
        available = metadata.st_mode & 0o7
    if available & required != required:
        raise SystemExit(
            f"{label} is not accessible to runtime UID/GID {uid}:{gid}: {path}"
        )


def require_private_file(path: Path, label: str) -> None:
    require_mode(path, 0o4, label)
    if path.stat().st_mode & 0o077:
        raise SystemExit(f"{label} must not be accessible by group or others: {path}")
    if path.parent.stat().st_mode & 0o077:
        raise SystemExit(
            f"{label} parent directory must not be accessible by group or others: "
            f"{path.parent}"
        )


require_mode(data_dir, 0o7, "SQLite data directory")
require_mode(database_file, 0o6, "SQLite database")
require_private_file(vapid_key, "VAPID private key")
require_private_file(firebase_credentials, "Firebase service-account credential")
try:
    firebase = json.loads(firebase_credentials.read_text())
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit(f"Firebase service-account credential is invalid: {exc}") from exc
if firebase.get("type") != "service_account":
    raise SystemExit("Firebase credential is not a service-account JSON file")
for field in ("project_id", "private_key", "client_email"):
    if not firebase.get(field):
        raise SystemExit(f"Firebase service-account credential is missing {field}")
for suffix in ("-wal", "-shm"):
    sidecar = Path(f"{database_file}{suffix}")
    if sidecar.exists():
        require_mode(sidecar, 0o6, f"SQLite {suffix[1:]} sidecar")

required_tables = {
    "doorbell_events",
    "paired_sessions",
    "paired_devices",
    "notification_delivery_attempts",
}
with sqlite3.connect(f"file:{database_file}?mode=ro", uri=True) as connection:
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise SystemExit(f"SQLite integrity check failed: {integrity}")
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
missing = sorted(required_tables - tables)
if missing:
    raise SystemExit(f"SQLite database is missing tables: {', '.join(missing)}")
PY

python3 - "$NETWORK" "$CLOUDFLARED_CONTAINER" "$API_CONTAINER" <<'PY'
import json
import subprocess
import sys

network, cloudflared, api = sys.argv[1:]
data = json.loads(subprocess.check_output(["docker", "network", "inspect", network]))[0]
config = data.get("IPAM", {}).get("Config", [])
if not any(
    item.get("Subnet") == "172.30.250.0/24"
    and item.get("Gateway") == "172.30.250.1"
    for item in config
):
    raise SystemExit("amader-home-tunnel has an unexpected subnet or gateway")

by_name = {item.get("Name"): item for item in data.get("Containers", {}).values()}
connector = by_name.get(cloudflared)
if connector is None or connector.get("IPv4Address") != "172.30.250.2/24":
    raise SystemExit("frigate-cloudflared is not attached at 172.30.250.2")

for item in data.get("Containers", {}).values():
    if item.get("IPv4Address") == "172.30.250.3/24" and item.get("Name") != api:
        raise SystemExit("172.30.250.3 is occupied by an unexpected container")
PY

printf 'Docker deployment preflight passed.\n'
