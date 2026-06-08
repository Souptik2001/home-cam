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
rpicam-vid -t 0 --inline --codec h264 --mode 2304:1296 --width 1280 --height 720 --framerate 30 --intra 30 -o - | \
ffmpeg -use_wallclock_as_timestamps 1 -fflags +genpts -f h264 -r 30 -i - \
-filter_complex "[0:v]split=2[vhigh][vlow];[vlow]scale=640:360[vlowout]" \
-map "[vhigh]" -c:v libx264 -preset ultrafast -tune zerolatency -g 30 -f rtsp -rtsp_transport tcp rtsp://localhost:8554/high \
-map "[vlowout]" -c:v libx264 -preset ultrafast -tune zerolatency -g 10 -f rtsp -rtsp_transport tcp rtsp://localhost:8554/low
'