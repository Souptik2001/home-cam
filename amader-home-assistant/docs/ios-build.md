# Compile the iOS app on your Mac

A signed iPhone build must be produced on macOS with Xcode and your Apple Developer signing identity.

## 1. Install prerequisites

Install the latest Xcode from the Mac App Store, open it once, and let it install its components. Then run:

```sh
sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer
sudo xcodebuild -runFirstLaunch
xcodebuild -version
```

Install Flutter and CocoaPods with Homebrew:

```sh
brew install --cask flutter
brew install cocoapods
flutter doctor -v
```

Resolve every iOS/Xcode item reported by `flutter doctor` before continuing.

## 2. Get the project

```sh
git clone https://github.com/Souptik2001/home-cam.git
cd home-cam
git checkout feat/amader-home-assistant-bootstrap
cd amader-home-assistant/app
flutter pub get
flutter analyze
flutter test
```

After PR #2 is merged, use `git checkout main` instead.

## 3. Configure your Apple signing team

Open the workspace, not the `.xcodeproj` file:

```sh
open ios/Runner.xcworkspace
```

In Xcode:

1. Select **Runner** in the project navigator.
2. Select the **Runner** target.
3. Open **Signing & Capabilities**.
4. Enable **Automatically manage signing**.
5. Select your Apple Developer **Team**.
6. Confirm the bundle identifier is unique. The planned identifier is `dev.souptik.amaderHomeAssistant`.
7. Add the **Push Notifications** capability.
8. Add **Background Modes** and select **Remote notifications**.

Do not add the Critical Alerts entitlement unless Apple has approved it for this app.

## 4. Add Firebase configuration

In the Firebase project, register an iOS app using the exact Xcode bundle identifier. Download `GoogleService-Info.plist` and place it at:

```text
ios/Runner/GoogleService-Info.plist
```

Open Xcode and drag that file into the **Runner** group, selecting **Copy items if needed** and the **Runner** target.

In Firebase Cloud Messaging settings, upload an APNs authentication key (`.p8`) associated with your Apple Developer team. Never commit the `.p8`, its key ID, or service-account credentials.

## 5. Test on your iPhone

Your iPhone must be connected to the same Tailscale network as Bob's server.

```sh
flutter run --release \
  --dart-define=ENABLE_FIREBASE_MESSAGING=true
```

When the app opens, pair it using:

```text
Server URL: http://bob-home.taildba06.ts.net:8787
Pairing code: obtain the current one-time code from Bob
```

Permit notifications when prompted. Ring tests must cover foreground, background, terminated, and locked-screen states.

## 6. Build the IPA

```sh
flutter clean
flutter pub get
cd ios
pod install --repo-update
cd ..
flutter build ipa --release \
  --dart-define=ENABLE_FIREBASE_MESSAGING=true
```

The IPA is written under:

```text
build/ios/ipa/
```

If Xcode reports signing problems, open `ios/Runner.xcworkspace`, select the correct Team and device, then use **Product → Archive**. In the Organizer choose **Distribute App** for TestFlight/App Store Connect or an allowed development/ad-hoc method.

## Build without Firebase temporarily

For UI/API testing before Firebase is configured:

```sh
flutter build ipa --release
```

That build can pair, show event history, and open the camera, but it will not receive doorbell push notifications.
