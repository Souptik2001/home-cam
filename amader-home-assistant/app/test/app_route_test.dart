import 'package:amader_home_assistant/core/routing/app_route.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('parses camera routes from notification payloads', () {
    expect(AppRoute.fromPayload({'route': '/camera'}), AppRoute.camera);
    expect(AppRoute.fromPayload({'route': 'camera'}), AppRoute.camera);
    expect(AppRoute.fromPayload({'screen': 'camera'}), AppRoute.camera);
  });

  test('unknown or absent payload routes resolve to events', () {
    expect(AppRoute.fromPayload({'route': '/unknown'}), AppRoute.events);
    expect(AppRoute.fromPayload(const {}), AppRoute.events);
    expect(AppRoute.fromName('/camera'), AppRoute.camera);
  });
}
