import 'package:amader_home_assistant/app.dart';
import 'package:amader_home_assistant/core/auth/session_store.dart';
import 'package:amader_home_assistant/core/network/api_client.dart';
import 'package:amader_home_assistant/core/notifications/notification_service.dart';
import 'package:flutter_test/flutter_test.dart';

class EmptySessionStore implements SessionStore {
  @override
  Future<void> clear() async {}

  @override
  Future<Session?> read() async => null;

  @override
  Future<void> write(Session session) async {}
}

void main() {
  testWidgets('first run opens the pairing screen', (tester) async {
    await tester.pumpWidget(
      AmaderHomeAssistantApp(
        sessionStore: EmptySessionStore(),
        notificationServiceFactory: (ApiClient _) =>
            const NoopNotificationService(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Pair your doorbell'), findsOneWidget);
    expect(find.text('Server URL'), findsOneWidget);
    expect(find.text('Pairing code'), findsOneWidget);
  });
}
