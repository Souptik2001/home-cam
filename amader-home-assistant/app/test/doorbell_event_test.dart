import 'package:amader_home_assistant/features/events/doorbell_event.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('parses event timestamps and optional display fields', () {
    final event = DoorbellEvent.fromJson({
      'id': 'evt-1',
      'event_type': 'doorbell',
      'metadata': {
        'title': 'Someone is at the door',
        'message': 'Front door bell rang',
      },
      'occurred_at': '2026-10-17T12:30:00Z',
      'received_at': '2026-10-17T12:30:01Z',
    });

    expect(event.id, 'evt-1');
    expect(event.type, 'doorbell');
    expect(event.title, 'Someone is at the door');
    expect(event.message, 'Front door bell rang');
    expect(event.occurredAt, DateTime.utc(2026, 10, 17, 12, 30));
    expect(event.receivedAt, DateTime.utc(2026, 10, 17, 12, 30, 1));
  });

  test('accepts timestamp aliases and rejects missing timestamps', () {
    expect(
      DoorbellEvent.fromJson({
        'id': 7,
        'timestamp': '2026-10-17T12:30:00+00:00',
      }).id,
      '7',
    );

    expect(
      () => DoorbellEvent.fromJson({'id': 'bad'}),
      throwsA(isA<FormatException>()),
    );
  });

  test('sorts event history newest first', () {
    final events = [
      DoorbellEvent(
        id: 'old',
        type: 'doorbell',
        occurredAt: DateTime.utc(2026, 10, 16),
      ),
      DoorbellEvent(
        id: 'new',
        type: 'doorbell',
        occurredAt: DateTime.utc(2026, 10, 17),
      ),
    ];

    final sorted = sortEventsNewestFirst(events);

    expect(sorted.map((event) => event.id), ['new', 'old']);
    expect(events.map((event) => event.id), ['old', 'new']);
  });

  test('sorts tied events by received time and then id descending', () {
    final occurredAt = DateTime.utc(2026, 10, 17, 12, 30);
    final events = [
      DoorbellEvent(
        id: 'event-a',
        type: 'doorbell',
        occurredAt: occurredAt,
        receivedAt: DateTime.utc(2026, 10, 17, 12, 30, 1),
      ),
      DoorbellEvent(
        id: 'event-b',
        type: 'doorbell',
        occurredAt: occurredAt,
        receivedAt: DateTime.utc(2026, 10, 17, 12, 30, 1),
      ),
      DoorbellEvent(
        id: 'event-old-receipt',
        type: 'doorbell',
        occurredAt: occurredAt,
        receivedAt: DateTime.utc(2026, 10, 17, 12, 30),
      ),
    ];

    expect(sortEventsNewestFirst(events).map((event) => event.id), [
      'event-b',
      'event-a',
      'event-old-receipt',
    ]);
  });
}
