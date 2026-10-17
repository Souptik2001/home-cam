enum AppRoute {
  events('/events'),
  camera('/camera');

  const AppRoute(this.path);
  final String path;

  static AppRoute fromName(String? name) {
    final normalized = (name ?? '').trim().toLowerCase();
    if (normalized == 'camera' || normalized == '/camera') return camera;
    return events;
  }

  static AppRoute fromPayload(Map<String, dynamic> payload) {
    return fromName(
      payload['route']?.toString() ?? payload['screen']?.toString(),
    );
  }
}
