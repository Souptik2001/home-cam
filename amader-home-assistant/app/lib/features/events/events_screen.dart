import 'package:amader_home_assistant/features/events/doorbell_event.dart';
import 'package:amader_home_assistant/features/events/event_repository.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

class EventsScreen extends StatefulWidget {
  const EventsScreen({
    required this.repository,
    required this.onOpenCamera,
    required this.onOpenEvent,
    super.key,
  });

  final EventRepository repository;
  final VoidCallback onOpenCamera;
  final ValueChanged<DoorbellEvent> onOpenEvent;

  @override
  State<EventsScreen> createState() => _EventsScreenState();
}

class _EventsScreenState extends State<EventsScreen> {
  final _scrollController = ScrollController();
  List<DoorbellEvent>? _events;
  String? _nextCursor;
  Object? _error;
  bool _loadingMore = false;
  bool _loadMoreFailed = false;
  int _requestGeneration = 0;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
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

  @override
  void dispose() {
    _scrollController
      ..removeListener(_onScroll)
      ..dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.extentAfter < 300) _loadMore();
  }

  Future<void> _refresh() async {
    final generation = ++_requestGeneration;
    setState(() {
      _error = null;
      _loadingMore = false;
      _loadMoreFailed = false;
      _nextCursor = null;
    });
    try {
      final page = await widget.repository.fetchEvents();
      if (!mounted || generation != _requestGeneration) return;
      setState(() {
        _events = sortEventsNewestFirst(page.events);
        _nextCursor = page.nextCursor;
      });
    } catch (error) {
      if (mounted && generation == _requestGeneration) {
        setState(() => _error = error);
      }
    }
  }

  Future<void> _loadMore() async {
    final cursor = _nextCursor;
    if (cursor == null || _loadingMore) return;
    final generation = _requestGeneration;
    setState(() {
      _loadingMore = true;
      _loadMoreFailed = false;
    });
    try {
      final page = await widget.repository.fetchEvents(cursor: cursor);
      if (!mounted || generation != _requestGeneration) return;
      final existing = _events ?? const <DoorbellEvent>[];
      final ids = existing.map((event) => event.id).toSet();
      setState(() {
        _events = sortEventsNewestFirst([
          ...existing,
          ...page.events.where((event) => ids.add(event.id)),
        ]);
        _nextCursor = page.nextCursor;
        _loadingMore = false;
      });
    } catch (_) {
      if (mounted && generation == _requestGeneration) {
        setState(() {
          _loadingMore = false;
          _loadMoreFailed = true;
        });
      }
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
    final hasFooter = _nextCursor != null;
    return ListView.builder(
      controller: _scrollController,
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(12),
      itemCount: events.length + (hasFooter ? 1 : 0),
      itemBuilder: (context, index) {
        if (index == events.length) return _loadMoreFooter();
        final event = events[index];
        final localTime = event.occurredAt.toLocal();
        final showDate =
            index == 0 ||
            !_isSameLocalDate(events[index - 1].occurredAt, event.occurredAt);
        return Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (showDate) ...[
                Padding(
                  padding: const EdgeInsets.fromLTRB(4, 12, 4, 6),
                  child: Text(
                    DateFormat.yMMMMd().format(localTime),
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
              ],
              Card(
                child: ListTile(
                  onTap: () => widget.onOpenEvent(event),
                  trailing: const Tooltip(
                    message: 'Open camera history',
                    child: Icon(Icons.history),
                  ),
                  leading: const CircleAvatar(
                    child: Icon(Icons.doorbell_outlined),
                  ),
                  title: Text(
                    event.title?.isNotEmpty == true
                        ? event.title!
                        : 'Doorbell event',
                  ),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (event.message?.isNotEmpty == true)
                        Text(event.message!),
                      Text(DateFormat.jm().format(localTime)),
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _loadMoreFooter() {
    if (_loadMoreFailed) {
      return Center(
        child: TextButton.icon(
          onPressed: _loadMore,
          icon: const Icon(Icons.refresh),
          label: const Text('Retry loading older events'),
        ),
      );
    }
    return const Padding(
      padding: EdgeInsets.all(20),
      child: Center(child: CircularProgressIndicator()),
    );
  }

  bool _isSameLocalDate(DateTime first, DateTime second) {
    final a = first.toLocal();
    final b = second.toLocal();
    return a.year == b.year && a.month == b.month && a.day == b.day;
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
