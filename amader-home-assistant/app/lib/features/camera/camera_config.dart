import 'package:amader_home_assistant/core/network/api_client.dart';

Uri parseCameraUri(Object? value) {
  final uri = Uri.tryParse(value?.toString() ?? '');
  if (uri == null || uri.scheme != 'https' || uri.host.isEmpty) {
    throw const FormatException('Camera URL must be a valid HTTPS URL.');
  }
  return uri;
}

abstract interface class CameraConfigRepository {
  Future<Uri> fetchCameraUri();
}

class ApiCameraConfigRepository implements CameraConfigRepository {
  ApiCameraConfigRepository(this._apiClient);

  final ApiClient _apiClient;

  @override
  Future<Uri> fetchCameraUri() async {
    final response = await _apiClient.getJson('/api/v1/camera/config');
    if (response is! Map<String, dynamic>) {
      throw const FormatException('Camera configuration is invalid.');
    }
    return parseCameraUri(response['base_url']);
  }
}
