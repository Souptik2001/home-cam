# Amader Home Assistant

A self-hosted doorbell event and notification platform inside the existing `home-cam` repository.

```text
amader-home-assistant/
├── server/  # FastAPI API, persistence, PWA frontend, Web Push and FCM
├── app/     # Native Flutter Android app (iOS source retained, PWA is the free iPhone path)
├── deploy/  # Docker, Cloudflare Tunnel, backup, and rollback operations
├── docs/    # Installation and platform instructions
└── compose.yaml
```

The live doorbell-camera destination is `https://camera.souptik.dev/#pi_cam_2`. The public application origin is `https://amader-home-assistant.souptik.dev`.

## Client architecture

- **Android:** signed native Flutter application with an FCM notification channel.
- **iPhone:** installable PWA served by the FastAPI server. It uses standards-based Web Push with self-owned VAPID keys, so it does not require Firebase or a paid Apple Developer membership.
- **Shared backend:** pairing, event history, camera configuration, device registration, notification delivery attempts, and signed doorbell ingestion.

For iPhone push, Safari creates a browser subscription backed by Apple's push service. The server encrypts each notification for that subscription and sends it using its VAPID identity. The user must add the site to the iPhone Home Screen before enabling notifications.

## Current deployment

The backend runs as the hardened Docker container `amader-home-assistant`. The existing `frigate-cloudflared` connector reaches it over the dedicated `amader-home-tunnel` bridge at:

```text
http://amader-home-assistant:8787
```

The verified public PWA and API are available at:

```text
https://amader-home-assistant.souptik.dev
```

The SQLite database and application secrets remain in external host directories and are bind-mounted into the container. The API root filesystem is read-only, capabilities are dropped, the VAPID key is mounted read-only, and the host compatibility port is bound only to Bob's Tailscale address. The retired user-level systemd service is disabled and retained only for rollback.

The origin remains non-public and Cloudflare Tunnel forwards only the application hostname. API bearer sessions, one-time pairing, bounded pairing-rate limits, and HMAC-signed doorbell ingestion remain enforced at the application layer.

## Capabilities

- Signed, bounded, replay-resistant doorbell event ingestion
- Durable newest-first event history with explicit UTC timestamps
- One-time pairing, protected API sessions, and pairing throttling
- Installable responsive PWA with iPhone Home Screen support
- Standards-based encrypted Web Push using private VAPID keys
- Notification taps opening `https://camera.souptik.dev/#pi_cam_2`
- Event-row taps opening Frigate 0.18+ History for `pi_cam_2` at the event's exact `occurred_at` timestamp
- Native Android application and optional Firebase Cloud Messaging
- Per-device notification delivery-attempt logging
- Restricted camera navigation and HTTPS-only mobile server configuration

## Android installation and reliable critical alerts

The Android application requires Google Play Services for Firebase Cloud Messaging. Install a signed release APK over the existing application and open it once after every install or update. Updating in place preserves the pairing, notification permission, and registered FCM token; uninstalling clears the local pairing.

For a new device:

1. Install and open **Amader Home Assistant**.
2. Pair it with a fresh one-time pairing code.
3. Allow notifications when Android asks.
4. Leave the app open for approximately ten seconds so it can retrieve and register its FCM token.
5. Confirm that **Critical doorbell alerts** appears in the app's notification settings.

### Recommended Android settings

Android manufacturers use different names and menu layouts. On Xiaomi, Redmi, or Poco devices, start at **Settings → Apps → Manage apps → Amader Home Assistant** and configure:

- **Autostart:** On.
- **Battery saver:** **No restrictions**.
- **Notifications → Critical doorbell alerts:** notifications, sound, vibration, floating/heads-up alerts, and lock-screen notifications enabled. Keep its importance at **High**.
- Do not use Android's **Force stop** button. Swiping the app out of Recent Apps is safe and does not unpair the device.
- The phone's **Always-on display** is not required; the screen may remain fully off and locked.

For optional Do Not Disturb bypass:

1. Open **Settings → Apps → Special app access → Do Not Disturb access**.
2. Allow **Amader Home Assistant**.
3. Close and reopen the application once so it can configure the critical channel.
4. Return to **Notifications → Critical doorbell alerts** and enable **Override Do Not Disturb** if the device exposes that switch.

Granting Do Not Disturb access does not grant access to messages, contacts, photos, or files. This application only uses it to mark the critical doorbell notification channel as eligible to bypass DND; Android and the device owner retain final control.

The server sends Android doorbell notifications with FCM `high` priority and zero TTL, matching the previous Home Assistant critical-notification behavior. Zero TTL requests immediate delivery and prevents a stale doorbell alert from appearing minutes later. If the phone is offline or unreachable at that instant, FCM can discard the notification instead of storing it. Notification-channel sound, vibration, alarm-stream audio, and DND settings affect presentation but cannot compensate for a disconnected device.

### Acceptance test for another Android device

After installation and pairing:

1. Send one notification while the phone is unlocked.
2. Clear Recent Apps and repeat the test.
3. Lock the phone and repeat immediately.
4. Leave the phone locked and untouched for at least 15–20 minutes, then repeat.
5. Verify sound/vibration and confirm that tapping the alert opens `https://camera.souptik.dev/#pi_cam_2`.

Wireless Debugging or ADB is not part of normal setup. It is needed only for focused diagnostics if registration or locked-screen delivery fails after the settings above have been checked.

## Development verification

```sh
cd server
uv sync
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv build
node --check src/amader_home_assistant/web/app.js
node --check src/amader_home_assistant/web/sw.js

cd ../app
flutter pub get
flutter analyze
flutter test
```

## Builds

- Android release APKs are built on Bob's Linux server using a private release keystore stored outside Git.
- The iPhone PWA needs no IPA. In Safari, open the public HTTPS hostname, choose **Share → Add to Home Screen**, launch it from the Home Screen, pair it, and press **Enable notifications**.
