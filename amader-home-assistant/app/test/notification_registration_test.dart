import 'dart:async';

import 'package:amader_home_assistant/core/notifications/notification_service.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('registers the initial FCM token and later token refreshes', () async {
    final refreshes = StreamController<String>();
    final registered = <String>[];
    final registration = FcmTokenRegistration(
      getToken: () async => 'initial-token',
      tokenRefreshes: refreshes.stream,
      registerToken: (token) async => registered.add(token),
    );

    await registration.start();
    expect(registered, ['initial-token']);

    refreshes.add('refreshed-token');
    await pumpEventQueue();
    expect(registered, ['initial-token', 'refreshed-token']);

    await registration.dispose();
    await refreshes.close();
  });

  test('reports token refresh stream errors without throwing', () async {
    final refreshes = StreamController<String>();
    final errors = <Object>[];
    final registration = FcmTokenRegistration(
      getToken: () async => null,
      tokenRefreshes: refreshes.stream,
      registerToken: (_) async {},
      onError: (error, _) => errors.add(error),
    );

    await registration.start();
    refreshes.addError(StateError('refresh failed'));
    await pumpEventQueue();

    expect(errors, hasLength(1));
    expect(errors.single, isA<StateError>());

    await registration.dispose();
    await refreshes.close();
  });

  test(
    'disposal cancels refreshes while the initial token is pending',
    () async {
      final initialToken = Completer<String?>();
      var streamCancelled = false;
      final refreshes = StreamController<String>(
        onCancel: () => streamCancelled = true,
      );
      final registered = <String>[];
      final registration = FcmTokenRegistration(
        getToken: () => initialToken.future,
        tokenRefreshes: refreshes.stream,
        registerToken: (token) async => registered.add(token),
      );

      final started = registration.start();
      await registration.dispose();
      initialToken.complete('late-token');
      await started;
      refreshes.add('refresh-after-dispose');
      await pumpEventQueue();

      expect(streamCancelled, isTrue);
      expect(registered, isEmpty);

      await refreshes.close();
    },
  );
}
