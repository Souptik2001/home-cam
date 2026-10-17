# Install Amader Home on iPhone

The iPhone client is a Progressive Web App. It does not require an App Store download, Firebase account, Apple Developer membership, or IPA file.

## Requirements

- iOS/iPadOS 16.4 or newer
- Safari
- Public HTTPS access to `https://amader-home-assistant.souptik.dev`
- The current one-time pairing code

## Install

1. Open Safari on the iPhone.
2. Visit `https://amader-home-assistant.souptik.dev`.
3. Tap Safari's **Share** button.
4. Select **Add to Home Screen**.
5. Keep the name **Amader Home** and tap **Add**.
6. Leave Safari and open **Amader Home** from the Home Screen.
7. Enter the current one-time pairing code.
8. Press **Enable notifications**.
9. Accept the iOS notification permission prompt.

Web Push permission can be requested on iPhone only after the PWA has been added to the Home Screen and launched from its icon.

## Acceptance tests

Ring the doorbell and verify all of these states:

1. PWA open in the foreground.
2. PWA in the background.
3. PWA removed from the app switcher.
4. iPhone locked.
5. Wi-Fi disabled and the iPhone using mobile data.
6. Notification tap opens `https://camera.souptik.dev`.
7. The event appears in the PWA history with the correct local date and time.

PWA Web Push is a normal notification. It cannot claim Apple's native Critical Alerts entitlement or guarantee bypassing Silent Mode/Focus.
