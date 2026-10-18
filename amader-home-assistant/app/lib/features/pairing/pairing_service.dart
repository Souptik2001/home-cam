import 'dart:convert';

import 'package:amader_home_assistant/core/auth/session_store.dart';
import 'package:amader_home_assistant/core/network/api_client.dart';
import 'package:http/http.dart' as http;

class PairingCredentials {
  const PairingCredentials({required this.baseUrl, required this.pairingCode});

  final Uri baseUrl;
  final String pairingCode;
}

abstract interface class PairingService {
  Future<void> pair(PairingCredentials credentials);
}

class ApiPairingService implements PairingService {
  ApiPairingService({required this.sessionStore, http.Client? httpClient})
    : _httpClient = httpClient ?? http.Client();

  final SessionStore sessionStore;
  final http.Client _httpClient;

  @override
  Future<void> pair(PairingCredentials credentials) async {
    final response = await _httpClient.post(
      credentials.baseUrl.resolve('/api/v1/pair'),
      headers: const {
        'accept': 'application/json',
        'content-type': 'application/json',
      },
      body: jsonEncode({
        'code': credentials.pairingCode,
        'name': 'Amader Home Assistant mobile',
      }),
    );
    Object? body;
    try {
      body = jsonDecode(response.body);
    } on FormatException {
      throw const ApiException(
        'The server returned an invalid pairing response.',
      );
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      final message = body is Map<String, dynamic>
          ? body['detail']?.toString() ?? body['message']?.toString()
          : null;
      throw ApiException(
        message ?? 'Pairing failed (${response.statusCode}).',
        statusCode: response.statusCode,
      );
    }
    final token = body is Map<String, dynamic>
        ? (body['session_token'] ?? body['token'])?.toString()
        : null;
    if (token == null || token.isEmpty) {
      throw const ApiException('Pairing succeeded without a session token.');
    }
    await sessionStore.write(
      Session(baseUrl: credentials.baseUrl, token: token),
    );
  }
}
