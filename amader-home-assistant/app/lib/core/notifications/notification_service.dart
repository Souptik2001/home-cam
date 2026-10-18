import 'dart:async';
import 'dart:io';

import 'package:amader_home_assistant/core/network/api_client.dart';
import 'package:amader_home_assistant/core/routing/app_route.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

abstract interface class NotificationService {
  Future<void> initialize(void Function(AppRoute route) onRoute);
  Future<void> dispose();
}

class NoopNotificationService implements NotificationService {
  const NoopNotificationService();

  @override
  Future<void> initialize(void Function(AppRoute route) onRoute) async {}

  @override
  Future<void> dispose() async {}
}

class FirebaseNotificationService implements NotificationService {
  FirebaseNotificationService(this._apiClient);

  final ApiClient _apiClient;
  final FlutterLocalNotificationsPlugin _localNotifications =
      FlutterLocalNotificationsPlugin();
  final List<StreamSubscription<Object?>> _subscriptions = [];

  @override
  Future<void> initialize(void Function(AppRoute route) onRoute) async {
    await Firebase.initializeApp();
    await _localNotifications.initialize(
      settings: const InitializationSettings(
        android: AndroidInitializationSettings('@mipmap/ic_launcher'),
        iOS: DarwinInitializationSettings(),
      ),
      onDidReceiveNotificationResponse: (response) {
        onRoute(AppRoute.fromName(response.payload));
      },
    );

    final messaging = FirebaseMessaging.instance;
    await messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
      provisional: false,
    );
    await messaging.setForegroundNotificationPresentationOptions(
      alert: true,
      badge: true,
      sound: true,
    );

    final initialMessage = await messaging.getInitialMessage();
    if (initialMessage != null) {
      onRoute(AppRoute.fromPayload(initialMessage.data));
    }

    _subscriptions.add(
      FirebaseMessaging.onMessageOpenedApp.listen(
        (message) => onRoute(AppRoute.fromPayload(message.data)),
      ),
    );
    _subscriptions.add(
      FirebaseMessaging.onMessage.listen((message) {
        if (Platform.isAndroid) {
          unawaited(_showAndroidForegroundNotification(message));
        }
      }),
    );
    _subscriptions.add(
      messaging.onRegistered.listen((token) {
        unawaited(
          _registerToken(token).catchError((Object error) {
            // A notification registration failure must not prevent app startup.
          }),
        );
      }),
    );
    await messaging.register();
  }

  Future<void> _showAndroidForegroundNotification(RemoteMessage message) async {
    final notification = message.notification;
    await _localNotifications.show(
      id:
          (message.messageId ?? message.hashCode.toString()).hashCode &
          0x7fffffff,
      title: notification?.title ?? 'Someone is at the door',
      body: notification?.body ?? 'The doorbell was pressed.',
      notificationDetails: const NotificationDetails(
        android: AndroidNotificationDetails(
          'doorbell_alerts',
          'Doorbell alerts',
          channelDescription: 'Alerts when someone rings the doorbell',
          importance: Importance.max,
          priority: Priority.max,
          playSound: true,
          enableVibration: true,
          category: AndroidNotificationCategory.alarm,
        ),
      ),
      payload: AppRoute.fromPayload(message.data).path,
    );
  }

  Future<void> _registerToken(String token) async {
    await _apiClient.postJson('/api/v1/devices', {
      'name': 'Amader Home Assistant mobile',
      'platform': Platform.isIOS ? 'ios' : 'android',
      'push_token': token,
      'enabled': true,
    });
  }

  @override
  Future<void> dispose() async {
    for (final subscription in _subscriptions) {
      await subscription.cancel();
    }
    _subscriptions.clear();
  }
}

NotificationService createNotificationService(ApiClient apiClient) {
  const enabled = bool.fromEnvironment('ENABLE_FIREBASE_MESSAGING');
  return enabled
      ? FirebaseNotificationService(apiClient)
      : const NoopNotificationService();
}
