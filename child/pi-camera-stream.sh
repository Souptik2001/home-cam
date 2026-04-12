#!/usr/bin/env bash
set -euo pipefail

MEDIA_MTX_DIR="$HOME/mediamtx"
MEDIA_MTX_BIN="$MEDIA_MTX_DIR/mediamtx"
MEDIA_MTX_CFG="$MEDIA_MTX_DIR/mediamtx.yml"

cleanup() {
  pkill -P $$ || true
}
trap cleanup EXIT

cd "$MEDIA_MTX_DIR"

"$MEDIA_MTX_BIN" "$MEDIA_MTX_CFG" &
sleep 2

exec /bin/bash -lc '
rpicam-vid -t 0 --inline --codec h264 --width 1280 --height 720 --framerate 30 -o - | \
ffmpeg -fflags nobuffer -flags low_delay -f h264 -r 30 -i - -c:v copy \
-f rtsp -rtsp_transport tcp rtsp://localhost:8554/cam
'