import 'package:amader_home_assistant/core/network/api_client.dart';
import 'package:amader_home_assistant/features/events/doorbell_event.dart';

abstract interface class EventRepository {
  Future<List<DoorbellEvent>> fetchEvents();
}

class ApiEventRepository implements EventRepository {
  ApiEventRepository(this._apiClient);

  final ApiClient _apiClient;

  @override
  Future<List<DoorbellEvent>> fetchEvents() async {
    final response = await _apiClient.getJson('/api/v1/events');
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
    return sortEventsNewestFirst(events);
  }
}
