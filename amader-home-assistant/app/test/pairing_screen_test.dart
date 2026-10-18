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
  testWidgets('pairing shows a single Amader Home Assistant heading', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: PairingScreen(
          pairingService: FakePairingService(),
          onPaired: () {},
        ),
      ),
    );

    expect(find.text('Amader Home Assistant'), findsOneWidget);
    expect(find.text('Pair your doorbell'), findsNothing);
    expect(
      find.text('Enter the server address and one-time pairing code.'),
      findsNothing,
    );
  });

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

    expect(
      tester
          .widget<TextFormField>(find.byKey(const Key('serverUrlField')))
          .controller
          ?.text,
      'https://amader-home-assistant.souptik.dev',
    );
    await tester.enterText(
      find.byKey(const Key('pairingCodeField')),
      ' 123456 ',
    );
    await tester.tap(find.text('Pair device'));
    await tester.pumpAndSettle();

    expect(
      service.received?.baseUrl.toString(),
      'https://amader-home-assistant.souptik.dev',
    );
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

    expect(find.text('Use a valid HTTPS server URL.'), findsOneWidget);
    expect(service.received, isNull);
  });
}
