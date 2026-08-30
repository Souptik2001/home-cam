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
CAMERA_MODE="${CAMERA_MODE:-1640:1232}"
CAMERA_FRAMERATE="${CAMERA_FRAMERATE:-30}"
CAMERA_INTRA="${CAMERA_INTRA:-30}"
HIGH_BITRATE="${HIGH_BITRATE:-4000000}"

rpicam-vid -t 0 --inline --codec h264 --mode "$CAMERA_MODE" \
  --width 1280 --height 720 --framerate "$CAMERA_FRAMERATE" \
  --intra "$CAMERA_INTRA" --bitrate "$HIGH_BITRATE" -o - | \
ffmpeg -f h264 -framerate "$CAMERA_FRAMERATE" -i - \
-filter_complex "[0:v]scale=640:360[vlowout]" \
-map 0:v:0 -c:v copy -fps_mode passthrough \
  -f rtsp -rtsp_transport tcp rtsp://localhost:8554/high \
-map "[vlowout]" -c:v libx264 -preset ultrafast -tune zerolatency \
  -g 10 -keyint_min 10 -sc_threshold 0 -fps_mode cfr \
  -f rtsp -rtsp_transport tcp rtsp://localhost:8554/low
'
