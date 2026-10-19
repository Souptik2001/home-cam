class DoorbellEvent {
  const DoorbellEvent({
    required this.id,
    required this.type,
    required this.occurredAt,
    DateTime? receivedAt,
    this.title,
    this.message,
  }) : receivedAt = receivedAt ?? occurredAt;

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
    final receivedAt = DateTime.tryParse(json['received_at']?.toString() ?? '');
    return DoorbellEvent(
      id: json['id']?.toString() ?? '',
      type: (json['event_type'] ?? json['type'])?.toString() ?? 'doorbell',
      title: (json['title'] ?? metadata['title'])?.toString(),
      message: (json['message'] ?? metadata['message'] ?? metadata['body'])
          ?.toString(),
      occurredAt: occurredAt,
      receivedAt: receivedAt,
    );
  }

  final String id;
  final String type;
  final DateTime occurredAt;
  final DateTime receivedAt;
  final String? title;
  final String? message;
}

List<DoorbellEvent> sortEventsNewestFirst(Iterable<DoorbellEvent> events) {
  return [...events]..sort((a, b) {
    final occurredOrder = b.occurredAt.compareTo(a.occurredAt);
    if (occurredOrder != 0) return occurredOrder;
    final receivedOrder = b.receivedAt.compareTo(a.receivedAt);
    if (receivedOrder != 0) return receivedOrder;
    return b.id.compareTo(a.id);
  });
}
