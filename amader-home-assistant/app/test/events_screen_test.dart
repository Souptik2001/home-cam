import 'dart:async';

import 'package:amader_home_assistant/features/events/doorbell_event.dart';
import 'package:amader_home_assistant/features/events/event_repository.dart';
import 'package:amader_home_assistant/features/events/events_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

class FakeEventRepository implements EventRepository {
  FakeEventRepository(
    List<DoorbellEvent> events, {
    this.error,
    String? nextCursor,
  }) : pages = {null: EventPage(events: events, nextCursor: nextCursor)};

  FakeEventRepository.pages(this.pages) : error = null;

  final Map<String?, EventPage> pages;
  final Object? error;
  final List<String?> requestedCursors = [];

  @override
  Future<EventPage> fetchEvents({String? cursor}) async {
    requestedCursors.add(cursor);
    if (error != null) throw error!;
    return pages[cursor] ?? const EventPage(events: []);
  }
}

class RefreshPendingRepository implements EventRepository {
  final refresh = Completer<EventPage>();
  final List<String?> requestedCursors = [];
  var requestCount = 0;

  @override
  Future<EventPage> fetchEvents({String? cursor}) {
    requestedCursors.add(cursor);
    requestCount += 1;
    if (requestCount == 1) {
      return Future.value(
        EventPage(
          events: List.generate(
            20,
            (index) => DoorbellEvent(
              id: 'event-$index',
              type: 'doorbell',
              title: 'Event $index',
              occurredAt: DateTime(
                2026,
                10,
                19,
                20,
              ).subtract(Duration(minutes: index)),
            ),
          ),
          nextCursor: 'stale-cursor',
        ),
      );
    }
    return refresh.future;
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
    expect(find.text('October 17, 2026'), findsOneWidget);
    expect(find.text('October 16, 2026'), findsOneWidget);
    expect(find.byTooltip('Refresh events'), findsOneWidget);
  });

  testWidgets('loads the next event page when scrolling near the end', (
    tester,
  ) async {
    final firstPageEvents = List.generate(
      20,
      (index) => DoorbellEvent(
        id: 'first-$index',
        type: 'doorbell',
        title: 'First page $index',
        occurredAt: DateTime(
          2026,
          10,
          19,
          20,
        ).subtract(Duration(minutes: index)),
      ),
    );
    final olderEvent = DoorbellEvent(
      id: 'older',
      type: 'doorbell',
      title: 'Loaded lazily',
      occurredAt: DateTime(2026, 10, 18, 20),
    );
    final repository = FakeEventRepository.pages({
      null: EventPage(events: firstPageEvents, nextCursor: 'page-2'),
      'page-2': EventPage(events: [olderEvent]),
    });

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
    expect(repository.requestedCursors, [null]);
    expect(find.text('Loaded lazily'), findsNothing);

    await tester.drag(find.byType(ListView), const Offset(0, -3000));
    await tester.pumpAndSettle();

    expect(repository.requestedCursors, [null, 'page-2']);
    expect(find.text('Loaded lazily'), findsOneWidget);
    expect(find.text('October 18, 2026'), findsOneWidget);
  });

  testWidgets('refresh clears the old cursor before awaiting its response', (
    tester,
  ) async {
    final repository = RefreshPendingRepository();
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

    await tester.tap(find.byTooltip('Refresh events'));
    await tester.pump();
    await tester.drag(find.byType(ListView), const Offset(0, -3000));
    await tester.pump();

    expect(repository.requestedCursors, [null, null]);
    repository.refresh.complete(const EventPage(events: []));
    await tester.pumpAndSettle();
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
