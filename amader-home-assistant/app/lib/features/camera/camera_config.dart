import 'package:amader_home_assistant/core/network/api_client.dart';

const approvedCameraOrigin = 'https://camera.souptik.dev';

void _requireApprovedCameraOrigin(Uri uri) {
  if (uri.scheme != 'https' || uri.origin != approvedCameraOrigin) {
    throw const FormatException(
      'Camera URL must use the approved HTTPS origin.',
    );
  }
}

Uri parseCameraUri(Object? value) {
  final uri = Uri.tryParse(value?.toString() ?? '');
  if (uri == null || uri.host.isEmpty) {
    throw const FormatException('Camera URL must be a valid HTTPS URL.');
  }
  _requireApprovedCameraOrigin(uri);
  return uri;
}

Uri buildCameraHistoryUri(Uri cameraUri, DateTime occurredAt) {
  _requireApprovedCameraOrigin(cameraUri);
  final camera = cameraUri.fragment.trim();
  if (camera.isEmpty) {
    throw const FormatException('Camera URL must identify a camera.');
  }
  final timestamp = occurredAt.millisecondsSinceEpoch ~/ 1000;
  return Uri.parse(cameraUri.origin).replace(
    path: '/review',
    queryParameters: {'timestamp': '${camera}_$timestamp'},
  );
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
