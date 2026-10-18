import 'dart:convert';

import 'package:amader_home_assistant/core/auth/session_store.dart';
import 'package:http/http.dart' as http;

class ApiException implements Exception {
  const ApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

class ApiClient {
  ApiClient({required this.sessionStore, http.Client? httpClient})
    : _httpClient = httpClient ?? http.Client();

  final SessionStore sessionStore;
  final http.Client _httpClient;

  Future<Object?> getJson(String path) async {
    final request = await _authorizedRequest('GET', path);
    final response = await _httpClient.send(request);
    return _decode(await http.Response.fromStream(response));
  }

  Future<Object?> postJson(String path, Map<String, Object?> body) async {
    final request = await _authorizedRequest('POST', path)
      ..headers['content-type'] = 'application/json'
      ..body = jsonEncode(body);
    final response = await _httpClient.send(request);
    return _decode(await http.Response.fromStream(response));
  }

  Future<http.Request> _authorizedRequest(String method, String path) async {
    final session = await sessionStore.read();
    if (session == null) throw const ApiException('This device is not paired.');
    return http.Request(method, session.baseUrl.resolve(path))
      ..headers['authorization'] = 'Bearer ${session.token}'
      ..headers['accept'] = 'application/json';
  }

  Object? _decode(http.Response response) {
    Object? body;
    if (response.body.isNotEmpty) {
      try {
        body = jsonDecode(response.body);
      } on FormatException {
        throw ApiException(
          'The server returned an invalid response.',
          statusCode: response.statusCode,
        );
      }
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      final message = body is Map<String, dynamic>
          ? body['detail']?.toString() ?? body['message']?.toString()
          : null;
      throw ApiException(
        message ?? 'Server request failed (${response.statusCode}).',
        statusCode: response.statusCode,
      );
    }
    return body;
  }
}
