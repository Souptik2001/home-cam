#!/usr/bin/env bash
set -euo pipefail

for argument in "$@"; do
  case "$argument" in
    --debug|--profile|--release)
      printf 'build-release.sh fixes the Android build mode to --release; remove %s\n' "$argument" >&2
      exit 2
      ;;
    --dart-define=ENABLE_FIREBASE_MESSAGING=*)
      printf 'build-release.sh always enables Firebase Messaging; remove %s\n' "$argument" >&2
      exit 2
      ;;
  esac
done

FLUTTER="${FLUTTER:-flutter}"
exec "$FLUTTER" build apk \
  "$@" \
  --release \
  --dart-define=ENABLE_FIREBASE_MESSAGING=true
