import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class Session {
  const Session({required this.baseUrl, required this.token});

  final Uri baseUrl;
  final String token;
}

abstract interface class SessionStore {
  Future<Session?> read();
  Future<void> write(Session session);
  Future<void> clear();
}

class SecureSessionStore implements SessionStore {
  SecureSessionStore([FlutterSecureStorage? storage])
    : _storage = storage ?? const FlutterSecureStorage();

  static const _baseUrlKey = 'server_base_url';
  static const _tokenKey = 'session_token';

  final FlutterSecureStorage _storage;

  @override
  Future<Session?> read() async {
    final values = await _storage.readAll();
    final baseUrl = Uri.tryParse(values[_baseUrlKey] ?? '');
    final token = values[_tokenKey];
    if (baseUrl == null || token == null || token.isEmpty) return null;
    return Session(baseUrl: baseUrl, token: token);
  }

  @override
  Future<void> write(Session session) async {
    await _storage.write(key: _baseUrlKey, value: session.baseUrl.toString());
    await _storage.write(key: _tokenKey, value: session.token);
  }

  @override
  Future<void> clear() => _storage.deleteAll();
}
