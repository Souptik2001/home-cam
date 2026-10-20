import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test(
    'production release wrapper pins Firebase messaging arguments',
    () async {
      final temp = await Directory.systemTemp.createTemp(
        'amader-release-test-',
      );
      addTearDown(() => temp.delete(recursive: true));
      final argumentsFile = File('${temp.path}/arguments');
      final fakeFlutter = File('${temp.path}/fake flutter')
        ..writeAsStringSync('''#!/bin/sh
printf '%s\\0' "\$@" > "\$OUTPUT_FILE"
''');
      await Process.run('chmod', ['0755', fakeFlutter.path]);

      final result = await Process.run(
        'bash',
        ['tool/build-release.sh', '--split-per-abi'],
        environment: {
          ...Platform.environment,
          'FLUTTER': fakeFlutter.path,
          'OUTPUT_FILE': argumentsFile.path,
        },
      );

      expect(result.exitCode, 0, reason: '${result.stderr}');
      final arguments = argumentsFile
          .readAsStringSync()
          .split('\u0000')
          .where((value) => value.isNotEmpty)
          .toList();
      expect(arguments, [
        'build',
        'apk',
        '--split-per-abi',
        '--release',
        '--dart-define=ENABLE_FIREBASE_MESSAGING=true',
      ]);
    },
  );

  for (final conflictingArgument in [
    '--dart-define=ENABLE_FIREBASE_MESSAGING=false',
    '--debug',
    '--profile',
    '--release',
  ]) {
    test('release wrapper rejects $conflictingArgument', () async {
      final temp = await Directory.systemTemp.createTemp(
        'amader-release-test-',
      );
      addTearDown(() => temp.delete(recursive: true));
      final marker = File('${temp.path}/invoked');
      final fakeFlutter = File('${temp.path}/fake-flutter')
        ..writeAsStringSync('''#!/bin/sh
touch "\$OUTPUT_FILE"
''');
      await Process.run('chmod', ['0755', fakeFlutter.path]);

      final result = await Process.run(
        'bash',
        ['tool/build-release.sh', conflictingArgument],
        environment: {
          ...Platform.environment,
          'FLUTTER': fakeFlutter.path,
          'OUTPUT_FILE': marker.path,
        },
      );

      expect(result.exitCode, isNot(0));
      expect(marker.existsSync(), isFalse);
    });
  }
}
