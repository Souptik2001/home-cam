import 'package:amader_home_assistant/core/network/api_client.dart';
import 'package:amader_home_assistant/features/events/doorbell_event.dart';

class EventPage {
  const EventPage({required this.events, this.nextCursor});

  factory EventPage.fromJson(Object? response) {
    final values = switch (response) {
      List<Object?> list => list,
      Map<String, dynamic> map when map['events'] is List<Object?> =>
        map['events'] as List<Object?>,
      _ => throw const FormatException('Events response must contain a list.'),
    };
    final events = values
        .whereType<Map>()
        .map(
          (value) => DoorbellEvent.fromJson(Map<String, dynamic>.from(value)),
        )
        .toList();
    final nextCursor = response is Map<String, dynamic>
        ? response['next_cursor']?.toString()
        : null;
    return EventPage(
      events: sortEventsNewestFirst(events),
      nextCursor: nextCursor?.isNotEmpty == true ? nextCursor : null,
    );
  }

  final List<DoorbellEvent> events;
  final String? nextCursor;
}

abstract interface class EventRepository {
  Future<EventPage> fetchEvents({String? cursor});
}

class ApiEventRepository implements EventRepository {
  ApiEventRepository(this._apiClient);

  static const pageSize = 20;

  final ApiClient _apiClient;

  @override
  Future<EventPage> fetchEvents({String? cursor}) async {
    final queryParameters = {'limit': '$pageSize', 'paginated': 'true'};
    if (cursor != null) queryParameters['cursor'] = cursor;
    final path = Uri(
      path: '/api/v1/events',
      queryParameters: queryParameters,
    ).toString();
    return EventPage.fromJson(await _apiClient.getJson(path));
  }
}
