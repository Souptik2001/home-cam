import 'package:amader_home_assistant/features/events/doorbell_event.dart';
import 'package:amader_home_assistant/features/events/event_repository.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

class EventsScreen extends StatefulWidget {
  const EventsScreen({
    required this.repository,
    required this.onOpenCamera,
    super.key,
  });

  final EventRepository repository;
  final VoidCallback onOpenCamera;

  @override
  State<EventsScreen> createState() => _EventsScreenState();
}

class _EventsScreenState extends State<EventsScreen> {
  List<DoorbellEvent>? _events;
  Object? _error;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  @override
  void didUpdateWidget(covariant EventsScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.repository != widget.repository) {
      _events = null;
      _refresh();
    }
  }

  Future<void> _refresh() async {
    setState(() => _error = null);
    try {
      final events = await widget.repository.fetchEvents();
      if (mounted) setState(() => _events = sortEventsNewestFirst(events));
    } catch (error) {
      if (mounted) setState(() => _error = error);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Events'),
        actions: [
          IconButton(
            tooltip: 'Refresh events',
            onPressed: _refresh,
            icon: const Icon(Icons.refresh),
          ),
          IconButton(
            tooltip: 'Camera',
            onPressed: widget.onOpenCamera,
            icon: const Icon(Icons.videocam_outlined),
          ),
        ],
      ),
      body: RefreshIndicator(onRefresh: _refresh, child: _body()),
    );
  }

  Widget _body() {
    if (_error != null) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: [
          SizedBox(
            height: 480,
            child: _Status(
              icon: Icons.cloud_off_outlined,
              title: 'Could not load events',
              message: 'Check the server connection and try again.',
              action: FilledButton(
                onPressed: _refresh,
                child: const Text('Try again'),
              ),
            ),
          ),
        ],
      );
    }
    final events = _events;
    if (events == null) return const Center(child: CircularProgressIndicator());
    if (events.isEmpty) {
      return const CustomScrollView(
        physics: AlwaysScrollableScrollPhysics(),
        slivers: [
          SliverFillRemaining(
            hasScrollBody: false,
            child: _Status(
              icon: Icons.event_note_outlined,
              title: 'No events yet',
              message: 'Doorbell activity will appear here.',
            ),
          ),
        ],
      );
    }
    return ListView.separated(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(12),
      itemCount: events.length,
      separatorBuilder: (_, _) => const SizedBox(height: 8),
      itemBuilder: (context, index) {
        final event = events[index];
        final localTime = event.occurredAt.toLocal();
        return Card(
          child: ListTile(
            leading: const CircleAvatar(child: Icon(Icons.doorbell_outlined)),
            title: Text(
              event.title?.isNotEmpty == true ? event.title! : 'Doorbell event',
            ),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (event.message?.isNotEmpty == true) Text(event.message!),
                Text(DateFormat.yMMMd().add_jm().format(localTime)),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _Status extends StatelessWidget {
  const _Status({
    required this.icon,
    required this.title,
    required this.message,
    this.action,
  });

  final IconData icon;
  final String title;
  final String message;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 64),
            const SizedBox(height: 16),
            Text(title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Text(message, textAlign: TextAlign.center),
            if (action != null) ...[const SizedBox(height: 16), action!],
          ],
        ),
      ),
    );
  }
}
