class DoorbellEvent {
  const DoorbellEvent({
    required this.id,
    required this.type,
    required this.occurredAt,
    this.title,
    this.message,
  });

  factory DoorbellEvent.fromJson(Map<String, dynamic> json) {
    final metadata = json['metadata'] is Map
        ? Map<String, dynamic>.from(json['metadata'] as Map)
        : const <String, dynamic>{};
    final rawTimestamp =
        json['occurred_at'] ?? json['timestamp'] ?? json['created_at'];
    final occurredAt = DateTime.tryParse(rawTimestamp?.toString() ?? '');
    if (occurredAt == null) {
      throw const FormatException('Event timestamp is missing or invalid.');
    }
    return DoorbellEvent(
      id: json['id']?.toString() ?? '',
      type: (json['event_type'] ?? json['type'])?.toString() ?? 'doorbell',
      title: (json['title'] ?? metadata['title'])?.toString(),
      message: (json['message'] ?? metadata['message'] ?? metadata['body'])
          ?.toString(),
      occurredAt: occurredAt,
    );
  }

  final String id;
  final String type;
  final DateTime occurredAt;
  final String? title;
  final String? message;
}

List<DoorbellEvent> sortEventsNewestFirst(Iterable<DoorbellEvent> events) {
  return [...events]..sort((a, b) => b.occurredAt.compareTo(a.occurredAt));
}
