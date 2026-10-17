import 'package:amader_home_assistant/features/pairing/pairing_service.dart';
import 'package:flutter/material.dart';

class PairingScreen extends StatefulWidget {
  const PairingScreen({
    required this.pairingService,
    required this.onPaired,
    super.key,
  });

  final PairingService pairingService;
  final VoidCallback onPaired;

  @override
  State<PairingScreen> createState() => _PairingScreenState();
}

class _PairingScreenState extends State<PairingScreen> {
  final _formKey = GlobalKey<FormState>();
  final _baseUrlController = TextEditingController();
  final _codeController = TextEditingController();
  bool _submitting = false;
  String? _error;

  @override
  void dispose() {
    _baseUrlController.dispose();
    _codeController.dispose();
    super.dispose();
  }

  Uri? _normalizedUri(String value) {
    final trimmed = value.trim();
    final parsed = Uri.tryParse(trimmed);
    final allowedScheme =
        parsed?.scheme == 'https' ||
        (parsed?.scheme == 'http' &&
            parsed?.host == 'bob-home.taildba06.ts.net');
    if (parsed == null || !allowedScheme || parsed.host.isEmpty) {
      return null;
    }
    final path = parsed.path == '/'
        ? ''
        : parsed.path.replaceFirst(RegExp(r'/+$'), '');
    return parsed.replace(path: path, query: null, fragment: null);
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      await widget.pairingService.pair(
        PairingCredentials(
          baseUrl: _normalizedUri(_baseUrlController.text)!,
          pairingCode: _codeController.text.trim(),
        ),
      );
      if (mounted) widget.onPaired();
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 480),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Icon(Icons.doorbell_outlined, size: 72),
                    const SizedBox(height: 20),
                    Text(
                      'Pair your doorbell',
                      style: Theme.of(context).textTheme.headlineMedium,
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Enter the server address and one-time pairing code.',
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 28),
                    TextFormField(
                      key: const Key('serverUrlField'),
                      controller: _baseUrlController,
                      keyboardType: TextInputType.url,
                      textInputAction: TextInputAction.next,
                      autocorrect: false,
                      decoration: const InputDecoration(
                        labelText: 'Server URL',
                        hintText: 'https://home.example.com',
                        border: OutlineInputBorder(),
                      ),
                      validator: (value) => _normalizedUri(value ?? '') == null
                          ? 'Use HTTPS, or Bob’s private Tailscale server URL.'
                          : null,
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      key: const Key('pairingCodeField'),
                      controller: _codeController,
                      textInputAction: TextInputAction.done,
                      autocorrect: false,
                      decoration: const InputDecoration(
                        labelText: 'Pairing code',
                        border: OutlineInputBorder(),
                      ),
                      validator: (value) => (value ?? '').trim().isEmpty
                          ? 'Enter the pairing code.'
                          : null,
                      onFieldSubmitted: (_) => _submit(),
                    ),
                    if (_error != null) ...[
                      const SizedBox(height: 16),
                      Text(
                        _error!,
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.error,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ],
                    const SizedBox(height: 20),
                    FilledButton.icon(
                      onPressed: _submitting ? null : _submit,
                      icon: _submitting
                          ? const SizedBox.square(
                              dimension: 18,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.link),
                      label: const Text('Pair device'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
