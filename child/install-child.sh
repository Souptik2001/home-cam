#!/usr/bin/env bash
set -euo pipefail

MEDIAMTX_VERSION="1.18.2"
ARM64_SHA256="c78aa7a1bdab94b2b02be364661f17802143215dba37e1fa67c3e0849248b485"
ARMV7_SHA256="d5eb3c9ce4c5466107016e53ac2258b50b476a796d6774ef9ce94260729a635c"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SENSOR="${1:-}"
INSTALL_USER="$(id -un)"

if [[ $EUID -eq 0 ]]; then
  echo "Run this as the normal camera user, not as root." >&2
  exit 1
fi

case "$SENSOR" in
  imx219) camera_mode="1640:1232" ;;
  imx708) camera_mode="2304:1296" ;;
  *)
    echo "Usage: $0 imx219|imx708" >&2
    echo "Confirm the sensor first with: rpicam-vid --list-cameras" >&2
    exit 2
    ;;
esac

case "$(uname -m)" in
  aarch64|arm64)
    archive="mediamtx_v${MEDIAMTX_VERSION}_linux_arm64.tar.gz"
    expected_sha="$ARM64_SHA256"
    ;;
  armv7l)
    archive="mediamtx_v${MEDIAMTX_VERSION}_linux_armv7.tar.gz"
    expected_sha="$ARMV7_SHA256"
    ;;
  *)
    echo "Unsupported architecture: $(uname -m)" >&2
    exit 3
    ;;
esac

for command in curl tar ffmpeg rpicam-vid systemctl sha256sum install sudo grep; do
  command -v "$command" >/dev/null || {
    echo "Missing dependency: $command" >&2
    exit 4
  }
done

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT
url="https://github.com/bluenviron/mediamtx/releases/download/v${MEDIAMTX_VERSION}/${archive}"

curl --fail --location --retry 3 --output "$workdir/$archive" "$url"
printf '%s  %s\n' "$expected_sha" "$workdir/$archive" | sha256sum --check --status || {
  echo "MediaMTX checksum verification failed" >&2
  exit 5
}

tar -xzf "$workdir/$archive" -C "$workdir"
install -d -m 0755 "$HOME/mediamtx"
install -m 0755 "$workdir/mediamtx" "$HOME/mediamtx/mediamtx"
install -m 0644 "$SCRIPT_DIR/mediamtx.yml" "$HOME/mediamtx/mediamtx.yml"

sudo install -m 0755 "$SCRIPT_DIR/pi-camera-stream.sh" /usr/local/bin/pi-camera-stream.sh
unit_tmp="$workdir/pi-camera-stream.service"
unit_text="$(<"$SCRIPT_DIR/pi-camera-stream.service")"
unit_text="${unit_text//User=admin/User=$INSTALL_USER}"
unit_text="${unit_text//\/home\/admin/$HOME}"
printf '%s\n' "$unit_text" >"$unit_tmp"
sudo install -m 0644 "$unit_tmp" /etc/systemd/system/pi-camera-stream.service

if [[ ! -e /etc/default/pi-camera-stream ]]; then
  env_tmp="$workdir/pi-camera-stream"
  cat >"$env_tmp" <<EOF
CAMERA_MODE=$camera_mode
CAMERA_FRAMERATE=30
CAMERA_INTRA=30
HIGH_BITRATE=4000000
EOF
  sudo install -m 0644 "$env_tmp" /etc/default/pi-camera-stream
else
  echo "Preserving existing /etc/default/pi-camera-stream"
fi

sudo systemctl daemon-reload
sudo systemctl enable --now pi-camera-stream.service

systemctl is-enabled --quiet pi-camera-stream.service
systemctl is-active --quiet pi-camera-stream.service
"$HOME/mediamtx/mediamtx" --version | grep -Fx "v${MEDIAMTX_VERSION}"

echo "Child stream installed. Verify localhost /high and /low with ffprobe before adding it to Frigate."
