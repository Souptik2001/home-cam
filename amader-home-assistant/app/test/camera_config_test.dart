import 'dart:convert';

import 'package:amader_home_assistant/core/auth/session_store.dart';
import 'package:amader_home_assistant/core/network/api_client.dart';
import 'package:amader_home_assistant/features/camera/camera_config.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

class StaticSessionStore implements SessionStore {
  const StaticSessionStore(this.session);

  final Session session;

  @override
  Future<void> clear() async {}

  @override
  Future<Session?> read() async => session;

  @override
  Future<void> write(Session session) async {}
}

void main() {
  test(
    'loads the HTTPS camera URL from the protected server endpoint',
    () async {
      late http.Request captured;
      final client = ApiClient(
        sessionStore: StaticSessionStore(
          Session(baseUrl: Uri.parse('https://api.example/'), token: 'token'),
        ),
        httpClient: MockClient((request) async {
          captured = request;
          return http.Response(
            jsonEncode({'base_url': 'https://camera.souptik.dev'}),
            200,
            headers: {'content-type': 'application/json'},
          );
        }),
      );

      final uri = await ApiCameraConfigRepository(client).fetchCameraUri();

      expect(uri, Uri.https('camera.souptik.dev'));
      expect(captured.url.path, '/api/v1/camera/config');
      expect(captured.headers['authorization'], 'Bearer token');
    },
  );

  test('rejects non-HTTPS camera URLs returned by the server', () {
    expect(
      () => parseCameraUri('http://camera.souptik.dev'),
      throwsFormatException,
    );
  });

  test('allows only the configured camera host in the webview', () {
    final cameraUri = Uri.parse('https://camera.souptik.dev');
    expect(isAllowedCameraNavigation(cameraUri, cameraUri), isTrue);
    expect(
      isAllowedCameraNavigation(
        cameraUri,
        Uri.parse('https://camera.souptik.dev/live'),
      ),
      isTrue,
    );
    expect(
      isAllowedCameraNavigation(
        cameraUri,
        Uri.parse('https://example.com/phishing'),
      ),
      isFalse,
    );
    expect(
      isAllowedCameraNavigation(
        cameraUri,
        Uri.parse('http://camera.souptik.dev'),
      ),
      isFalse,
    );
  });
}
