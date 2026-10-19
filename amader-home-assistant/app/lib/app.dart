import 'dart:async';

import 'package:amader_home_assistant/core/auth/session_store.dart';
import 'package:amader_home_assistant/core/network/api_client.dart';
import 'package:amader_home_assistant/core/notifications/notification_service.dart';
import 'package:amader_home_assistant/core/routing/app_route.dart';
import 'package:amader_home_assistant/features/camera/camera_config.dart';
import 'package:amader_home_assistant/features/camera/camera_screen.dart';
import 'package:amader_home_assistant/features/events/event_repository.dart';
import 'package:amader_home_assistant/features/events/events_screen.dart';
import 'package:amader_home_assistant/features/pairing/pairing_screen.dart';
import 'package:amader_home_assistant/features/pairing/pairing_service.dart';
import 'package:flutter/material.dart';

class AmaderHomeAssistantApp extends StatefulWidget {
  AmaderHomeAssistantApp({
    SessionStore? sessionStore,
    NotificationService Function(ApiClient)? notificationServiceFactory,
    super.key,
  }) : sessionStore = sessionStore ?? SecureSessionStore(),
       notificationServiceFactory =
           notificationServiceFactory ?? createNotificationService;

  final SessionStore sessionStore;
  final NotificationService Function(ApiClient) notificationServiceFactory;

  @override
  State<AmaderHomeAssistantApp> createState() => _AmaderHomeAssistantAppState();
}

class _AmaderHomeAssistantAppState extends State<AmaderHomeAssistantApp> {
  final _navigatorKey = GlobalKey<NavigatorState>();
  late Future<Session?> _session;
  NotificationService? _notificationService;
  ApiClient? _apiClient;
  bool _notificationsStarted = false;

  @override
  void initState() {
    super.initState();
    _session = widget.sessionStore.read();
  }

  void _paired() {
    setState(() => _session = widget.sessionStore.read());
  }

  void _openRoute(AppRoute route) {
    if (route == AppRoute.camera) unawaited(_openCamera());
  }

  Future<void> _openCamera([DateTime? occurredAt]) async {
    final apiClient = _apiClient;
    final navigator = _navigatorKey.currentState;
    if (apiClient == null || navigator == null) return;
    try {
      final configuredUri = await ApiCameraConfigRepository(apiClient)
          .fetchCameraUri();
      final cameraUri = occurredAt == null
          ? configuredUri
          : buildCameraHistoryUri(configuredUri, occurredAt);
      if (!mounted) return;
      await navigator.push(
        MaterialPageRoute<void>(
          builder: (_) => CameraScreen(cameraUri: cameraUri),
        ),
      );
    } catch (error) {
      final context = _navigatorKey.currentContext;
      if (context != null && context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not open the camera: $error')),
        );
      }
    }
  }

  void _startNotifications(ApiClient apiClient) {
    if (_notificationsStarted) return;
    _notificationsStarted = true;
    _notificationService = widget.notificationServiceFactory(apiClient);
    unawaited(
      _notificationService!.initialize(_openRoute).catchError((Object error) {
        debugPrint('Notifications unavailable: $error');
      }),
    );
  }

  @override
  void dispose() {
    unawaited(_notificationService?.dispose());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      navigatorKey: _navigatorKey,
      title: 'Amader Home Assistant',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.teal),
        useMaterial3: true,
      ),
      home: FutureBuilder<Session?>(
        future: _session,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Scaffold(
              body: Center(child: CircularProgressIndicator()),
            );
          }
          final session = snapshot.data;
          if (session == null) {
            return PairingScreen(
              pairingService: ApiPairingService(
                sessionStore: widget.sessionStore,
              ),
              onPaired: _paired,
            );
          }
          final apiClient = _apiClient ??= ApiClient(
            sessionStore: widget.sessionStore,
          );
          _startNotifications(apiClient);
          return EventsScreen(
            repository: ApiEventRepository(apiClient),
            onOpenCamera: () => unawaited(_openCamera()),
            onOpenEvent: (event) => unawaited(_openCamera(event.occurredAt)),
          );
        },
      ),
    );
  }
}
