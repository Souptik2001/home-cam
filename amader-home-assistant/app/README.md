# Amader Home Assistant

Flutter mobile shell for the Amader Home Assistant project. The app currently provides:

- an Events screen with an empty state;
- a Camera action that identifies `https://camera.souptik.dev`;
- Android and iOS platform projects.

Live camera embedding, push notifications, and Firebase configuration are intentionally not included in this bootstrap.

## Requirements

Use the repository-provided Flutter SDK:

```sh
export PATH="/home/bob-home/.local/bin:/home/bob-home/.local/share/flutter-sdk/bin:$PATH"
```

## Development

```sh
flutter pub get
flutter analyze
flutter test
flutter run
```

## Platform builds

### Android

An Android APK can be built on Linux once the Android SDK and required build tools are installed:

```sh
flutter build apk
```

The output is written under `build/app/outputs/flutter-apk/`.

### iOS

The iOS project is included, but producing a signed IPA requires macOS, Xcode, and valid Apple Developer signing credentials/profiles. It cannot be signed on Linux. On a configured Mac, use:

```sh
flutter build ipa
```

Do not commit signing credentials, Firebase secrets, or generated private configuration files.
