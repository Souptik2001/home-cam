import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('native Android critical doorbell channel uses alarm audio', () {
    final source = File(
      'android/app/src/main/kotlin/dev/souptik/amader_home_assistant/MainActivity.kt',
    ).readAsStringSync();

    expect(source, contains('"doorbell_critical_alerts"'));
    expect(source, contains('AudioAttributes.USAGE_ALARM'));
    expect(source, contains('RingtoneManager.TYPE_ALARM'));
    expect(source, contains('Notification.VISIBILITY_PUBLIC'));
    expect(source, contains('isNotificationPolicyAccessGranted'));
    expect(source, contains('setBypassDnd(true)'));
  });

  test('Android manifest declares notification policy access', () {
    final manifest = File('android/app/src/main/AndroidManifest.xml')
        .readAsStringSync();

    expect(manifest, contains('android.permission.ACCESS_NOTIFICATION_POLICY'));
  });
}
