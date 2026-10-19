import 'package:amader_home_assistant/features/events/doorbell_event.dart';
import 'package:amader_home_assistant/features/events/event_repository.dart';
import 'package:amader_home_assistant/features/events/events_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

class FakeEventRepository implements EventRepository {
  FakeEventRepository(this.events, {this.error});

  final List<DoorbellEvent> events;
  final Object? error;

  @override
  Future<List<DoorbellEvent>> fetchEvents() async {
    if (error != null) throw error!;
    return events;
  }
}

void main() {
  testWidgets('event history displays newest events first', (tester) async {
    final repository = FakeEventRepository([
      DoorbellEvent(
        id: 'old',
        type: 'doorbell',
        title: 'Old ring',
        occurredAt: DateTime(2026, 10, 16, 9),
      ),
      DoorbellEvent(
        id: 'new',
        type: 'doorbell',
        title: 'New ring',
        occurredAt: DateTime(2026, 10, 17, 10),
      ),
    ]);

    await tester.pumpWidget(
      MaterialApp(
        home: EventsScreen(
          repository: repository,
          onOpenCamera: () {},
          onOpenEvent: (_) {},
        ),
      ),
    );
    await tester.pumpAndSettle();

    final newY = tester.getTopLeft(find.text('New ring')).dy;
    final oldY = tester.getTopLeft(find.text('Old ring')).dy;
    expect(newY, lessThan(oldY));
    expect(find.byTooltip('Refresh events'), findsOneWidget);
  });

  testWidgets('tapping an event opens its camera History timestamp', (
    tester,
  ) async {
    final event = DoorbellEvent(
      id: 'ring',
      type: 'doorbell',
      title: 'Front door',
      occurredAt: DateTime.parse('2026-10-19T17:43:46Z'),
    );
    DoorbellEvent? openedEvent;

    await tester.pumpWidget(
      MaterialApp(
        home: EventsScreen(
          repository: FakeEventRepository([event]),
          onOpenCamera: () {},
          onOpenEvent: (value) => openedEvent = value,
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Front door'));
    expect(openedEvent, same(event));
    expect(find.byTooltip('Open camera history'), findsOneWidget);
  });

  testWidgets('event history displays empty and error states', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: EventsScreen(
          repository: FakeEventRepository(const []),
          onOpenCamera: () {},
          onOpenEvent: (_) {},
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('No events yet'), findsOneWidget);

    await tester.pumpWidget(
      MaterialApp(
        home: EventsScreen(
          repository: FakeEventRepository(
            const [],
            error: Exception('offline'),
          ),
          onOpenCamera: () {},
          onOpenEvent: (_) {},
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Could not load events'), findsOneWidget);
    expect(find.text('Try again'), findsOneWidget);
  });
}
