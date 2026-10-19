# Amader Home Assistant

Flutter Android/iOS client for the Amader Home Assistant doorbell. Mobile v1 includes:

- first-run server URL and pairing-code setup;
- session-token storage with `flutter_secure_storage`;
- authenticated event history, grouped by local date and loaded incrementally as the user scrolls, with refresh, empty, and error states;
- event-row links to Frigate 0.18+ History for the configured camera at the exact event timestamp;
- camera and notification navigation through the authenticated system browser;
- notification route parsing so a `/camera` payload opens the Camera screen;
- optional Firebase Messaging registration and device-registration API calls.

## Requirements

Use the repository-provided Flutter SDK:

```sh
export PATH="/home/bob-home/.local/share/flutter-sdk/bin:$PATH"
```

## Development

```sh
flutter pub get
flutter analyze
flutter test
flutter run
```

## Backend API contract

The app currently expects these endpoints under the base URL entered during pairing:

- `POST /api/v1/pair` with `{"code":"...","name":"Amader Home Assistant mobile"}`; returns `{"token":"..."}` (a `session_token` alias is also accepted).
- `GET /api/v1/events?paginated=true&limit=20&cursor=...` with `Authorization: Bearer SESSION_TOKEN`; returns `{"events": [...], "next_cursor": "..."}` (the legacy array response is also accepted). Each event needs `id` and `occurred_at` (the aliases `timestamp` and `created_at` are accepted); `received_at` is used to preserve server ordering for tied occurrence times. The app reads `event_type` and optional `metadata.title`, `metadata.message`, or `metadata.body` fields.
- `POST /api/v1/devices` with authentication and `{"name":"Amader Home Assistant mobile","platform":"android|ios","push_token":"...","enabled":true}` when Firebase registration becomes available.

Notification data may contain `route: /camera`, `route: camera`, or `screen: camera`.

## Firebase Messaging (optional)

Firebase is disabled by default, so the project builds and tests without native Firebase credentials. Do not commit either credential file; both paths are ignored:

- Android: `android/app/google-services.json`
- iOS: `ios/Runner/GoogleService-Info.plist`

After supplying valid native configuration, enable the integration at build/run time:

```sh
flutter run --dart-define=ENABLE_FIREBASE_MESSAGING=true
```

Android applies the Google Services Gradle plugin only when `google-services.json` exists. The app requests notification permission through Firebase Messaging, listens for notification opens/initial messages, and registers the resulting messaging registration ID with the backend. Android also creates the high-importance `doorbell_alerts` channel and declares `POST_NOTIFICATIONS`; iOS requests alert, badge, and sound permission and enables the remote-notification background mode.

Firebase delivery is not functional until valid Firebase native configuration, APNs setup for iOS, and matching backend messaging credentials are supplied.

## Platform builds

### Android

```sh
flutter build apk
```

The output is written under `build/app/outputs/flutter-apk/`.

### iOS

The iOS source is included, but producing a signed IPA requires macOS, Xcode, and valid Apple Developer signing/provisioning. On a configured Mac:

```sh
flutter build ipa
```

Do not commit signing credentials, Firebase secrets, or generated private configuration files.
