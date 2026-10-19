import 'package:amader_home_assistant/features/camera/camera_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets(
    'opens the protected camera in the system browser automatically',
    (tester) async {
      final cameraUri = Uri.parse('https://camera.souptik.dev');
      final openedUris = <Uri>[];

      await tester.pumpWidget(
        MaterialApp(
          home: CameraScreen(
            cameraUri: cameraUri,
            openExternal: (uri) async {
              openedUris.add(uri);
              return true;
            },
          ),
        ),
      );
      await tester.pump();

      expect(openedUris, [cameraUri]);
      expect(find.text('Camera opened in your browser'), findsOneWidget);
    },
  );

  testWidgets('shows a retry button when no browser can open the camera', (
    tester,
  ) async {
    var attempts = 0;

    await tester.pumpWidget(
      MaterialApp(
        home: CameraScreen(
          cameraUri: Uri.parse('https://camera.souptik.dev'),
          openExternal: (_) async {
            attempts += 1;
            return false;
          },
        ),
      ),
    );
    await tester.pump();
    await tester.pump();

    expect(attempts, 1);
    expect(find.text('Camera could not open'), findsOneWidget);
    expect(find.text('Try again'), findsOneWidget);
  });
}
