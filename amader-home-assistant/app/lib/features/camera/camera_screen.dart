import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

typedef CameraExternalLauncher = Future<bool> Function(Uri uri);

class CameraScreen extends StatefulWidget {
  const CameraScreen({required this.cameraUri, this.openExternal, super.key});

  final Uri cameraUri;
  final CameraExternalLauncher? openExternal;

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> {
  bool _opening = true;
  bool _failed = false;
  bool _opened = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _openExternally());
  }

  Future<void> _openExternally() async {
    if (mounted) {
      setState(() {
        _opening = true;
        _failed = false;
        _opened = false;
      });
    }
    final launcher = widget.openExternal ?? _launchExternalBrowser;
    final opened = await launcher(widget.cameraUri);
    if (!mounted) return;
    if (opened && await Navigator.of(context).maybePop()) return;
    if (!mounted) return;
    setState(() {
      _opening = false;
      _failed = !opened;
      _opened = opened;
    });
  }

  Future<bool> _launchExternalBrowser(Uri uri) {
    return launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Camera')),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                _failed
                    ? Icons.videocam_off_outlined
                    : Icons.open_in_browser_outlined,
                size: 64,
              ),
              const SizedBox(height: 16),
              if (_opening) ...[
                const CircularProgressIndicator(),
                const SizedBox(height: 16),
                const Text('Opening camera in your browser…'),
              ] else ...[
                Text(
                  _failed
                      ? 'Camera could not open'
                      : 'Camera opened in your browser',
                  style: Theme.of(context).textTheme.titleLarge,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 8),
                Text(
                  _failed
                      ? 'Use the button below to try again.'
                      : 'Return to the browser to view Frigate.',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                FilledButton.icon(
                  onPressed: _openExternally,
                  icon: const Icon(Icons.open_in_browser),
                  label: Text(_opened ? 'Open again' : 'Try again'),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
