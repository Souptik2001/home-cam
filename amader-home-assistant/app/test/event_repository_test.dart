import 'package:amader_home_assistant/core/auth/session_store.dart';
import 'package:amader_home_assistant/core/network/api_client.dart';
import 'package:amader_home_assistant/features/events/event_repository.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

class TestSessionStore implements SessionStore {
  @override
  Future<Session?> read() async => Session(
    baseUrl: Uri.parse('https://amader-home-assistant.souptik.dev'),
    token: 'session-token',
  );

  @override
  Future<void> clear() async {}

  @override
  Future<void> write(Session session) async {}
}

void main() {
  test('requests cursor pages and parses the next cursor', () async {
    final requested = <Uri>[];
    final apiClient = ApiClient(
      sessionStore: TestSessionStore(),
      httpClient: MockClient((request) async {
        requested.add(request.url);
        return http.Response(
          '''{"events":[{"id":"event-1","event_type":"doorbell","occurred_at":"2026-10-19T17:43:46Z"}],"next_cursor":"older-page"}''',
          200,
          headers: {'content-type': 'application/json'},
        );
      }),
    );
    final repository = ApiEventRepository(apiClient);

    final page = await repository.fetchEvents(cursor: 'cursor with spaces');

    expect(page.events.single.id, 'event-1');
    expect(page.nextCursor, 'older-page');
    expect(requested.single.path, '/api/v1/events');
    expect(requested.single.queryParameters, {
      'limit': '20',
      'paginated': 'true',
      'cursor': 'cursor with spaces',
    });
  });

  test('accepts the legacy unpaginated event list during rollout', () {
    final page = EventPage.fromJson([
      {
        'id': 'legacy',
        'event_type': 'doorbell',
        'occurred_at': '2026-10-19T17:43:46Z',
      },
    ]);

    expect(page.events.single.id, 'legacy');
    expect(page.nextCursor, isNull);
  });
}
