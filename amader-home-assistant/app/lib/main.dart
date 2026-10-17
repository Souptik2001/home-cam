import 'package:flutter/material.dart';

void main() {
  runApp(const AmaderHomeAssistantApp());
}

class AmaderHomeAssistantApp extends StatelessWidget {
  const AmaderHomeAssistantApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Amader Home Assistant',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.teal),
        useMaterial3: true,
      ),
      home: const EventsScreen(),
    );
  }
}

class EventsScreen extends StatelessWidget {
  const EventsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Amader Home Assistant'),
        actions: [
          IconButton(
            tooltip: 'Camera',
            icon: const Icon(Icons.videocam_outlined),
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (context) => const CameraScreen(),
                ),
              );
            },
          ),
        ],
      ),
      body: const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.event_note_outlined, size: 64),
              SizedBox(height: 16),
              Text('Events', style: TextStyle(fontSize: 24)),
              SizedBox(height: 12),
              Text('No events yet', style: TextStyle(fontSize: 20)),
              SizedBox(height: 8),
              Text(
                'Camera events will appear here when they are available.',
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class CameraScreen extends StatelessWidget {
  const CameraScreen({super.key});

  static const cameraUrl = 'https://camera.souptik.dev';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Camera')),
      body: const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.videocam_outlined, size: 64),
              SizedBox(height: 16),
              SelectableText(
                cameraUrl,
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 18),
              ),
              SizedBox(height: 12),
              Text(
                'Live camera viewing will be added in a future update.',
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
