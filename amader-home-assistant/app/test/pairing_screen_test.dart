import 'package:amader_home_assistant/features/pairing/pairing_screen.dart';
import 'package:amader_home_assistant/features/pairing/pairing_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

class FakePairingService implements PairingService {
  PairingCredentials? received;

  @override
  Future<void> pair(PairingCredentials credentials) async {
    received = credentials;
  }
}

void main() {
  testWidgets('pairing submits a normalized server URL and code', (
    tester,
  ) async {
    final service = FakePairingService();
    var paired = false;

    await tester.pumpWidget(
      MaterialApp(
        home: PairingScreen(
          pairingService: service,
          onPaired: () => paired = true,
        ),
      ),
    );

    await tester.enterText(
      find.byKey(const Key('serverUrlField')),
      'https://home.example.test/',
    );
    await tester.enterText(
      find.byKey(const Key('pairingCodeField')),
      ' 123456 ',
    );
    await tester.tap(find.text('Pair device'));
    await tester.pumpAndSettle();

    expect(service.received?.baseUrl.toString(), 'https://home.example.test');
    expect(service.received?.pairingCode, '123456');
    expect(paired, isTrue);
  });

  testWidgets('pairing rejects an invalid server URL', (tester) async {
    final service = FakePairingService();

    await tester.pumpWidget(
      MaterialApp(
        home: PairingScreen(pairingService: service, onPaired: () {}),
      ),
    );

    await tester.enterText(
      find.byKey(const Key('serverUrlField')),
      'http://example.com',
    );
    await tester.enterText(find.byKey(const Key('pairingCodeField')), '123456');
    await tester.tap(find.text('Pair device'));
    await tester.pump();

    expect(
      find.text('Use HTTPS, or Bob’s private Tailscale server URL.'),
      findsOneWidget,
    );
    expect(service.received, isNull);
  });

  testWidgets('pairing allows the private HTTP Tailscale server', (
    tester,
  ) async {
    final service = FakePairingService();

    await tester.pumpWidget(
      MaterialApp(
        home: PairingScreen(pairingService: service, onPaired: () {}),
      ),
    );

    await tester.enterText(
      find.byKey(const Key('serverUrlField')),
      'http://bob-home.taildba06.ts.net:8787',
    );
    await tester.enterText(find.byKey(const Key('pairingCodeField')), '123456');
    await tester.tap(find.text('Pair device'));
    await tester.pumpAndSettle();

    expect(
      service.received?.baseUrl.toString(),
      'http://bob-home.taildba06.ts.net:8787',
    );
  });
}
