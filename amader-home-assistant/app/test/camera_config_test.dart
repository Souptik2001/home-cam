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
            jsonEncode({'base_url': 'https://camera.souptik.dev/#pi_cam_2'}),
            200,
            headers: {'content-type': 'application/json'},
          );
        }),
      );

      final uri = await ApiCameraConfigRepository(client).fetchCameraUri();

      expect(uri, Uri.parse('https://camera.souptik.dev/#pi_cam_2'));
      expect(captured.url.path, '/api/v1/camera/config');
      expect(captured.headers['authorization'], 'Bearer token');
    },
  );

  test('builds a Frigate History link for the configured camera and event', () {
    final uri = buildCameraHistoryUri(
      Uri.parse('https://camera.souptik.dev/#pi_cam_2'),
      DateTime.parse('2026-10-19T17:43:46Z'),
    );

    expect(
      uri.toString(),
      'https://camera.souptik.dev/review?timestamp=pi_cam_2_1792431826',
    );
  });

  test('rejects a History link when the camera key is missing', () {
    expect(
      () => buildCameraHistoryUri(
        Uri.parse('https://camera.souptik.dev'),
        DateTime.parse('2026-10-19T17:43:46Z'),
      ),
      throwsFormatException,
    );
  });

  test('rejects camera URLs outside the approved origin', () {
    expect(
      () => parseCameraUri('https://attacker.example/#pi_cam_2'),
      throwsFormatException,
    );
    expect(
      () => buildCameraHistoryUri(
        Uri.parse('https://attacker.example/#pi_cam_2'),
        DateTime.parse('2026-10-19T17:43:46Z'),
      ),
      throwsFormatException,
    );
  });

  test('rejects non-HTTPS camera URLs returned by the server', () {
    expect(
      () => parseCameraUri('http://camera.souptik.dev'),
      throwsFormatException,
    );
  });
}
