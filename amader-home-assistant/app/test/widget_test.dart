import 'package:amader_home_assistant/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('shows the Events screen with a meaningful empty state', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const AmaderHomeAssistantApp());

    expect(find.text('Amader Home Assistant'), findsOneWidget);
    expect(find.text('Events'), findsOneWidget);
    expect(find.byIcon(Icons.event_note_outlined), findsOneWidget);
    expect(find.text('No events yet'), findsOneWidget);
    expect(
      find.text('Camera events will appear here when they are available.'),
      findsOneWidget,
    );
  });

  testWidgets('opens the Camera screen and identifies the camera URL', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const AmaderHomeAssistantApp());

    await tester.tap(find.byTooltip('Camera'));
    await tester.pumpAndSettle();

    expect(find.text('Camera'), findsOneWidget);
    expect(find.byIcon(Icons.videocam_outlined), findsOneWidget);
    expect(find.text('https://camera.souptik.dev'), findsOneWidget);
    expect(
      find.text('Live camera viewing will be added in a future update.'),
      findsOneWidget,
    );
  });
}
