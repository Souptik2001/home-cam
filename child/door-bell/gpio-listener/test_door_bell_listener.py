from __future__ import annotations

import base64
import hashlib
import hmac
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

MODULE_PATH = Path(__file__).with_name("door-bell-listener.py")


def load_listener_module():
    fake_gpiozero = types.ModuleType("gpiozero")
    fake_gpiozero.__dict__["Button"] = object
    sys.modules.setdefault("gpiozero", fake_gpiozero)
    spec = importlib.util.spec_from_file_location("door_bell_listener", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SignedDoorbellEventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.listener = load_listener_module()

    def test_build_signed_event_matches_server_canonical_format(self) -> None:
        url, body, headers = self.listener.build_signed_event(
            "https://amader-home-assistant.souptik.dev/",
            "front-door",
            "a" * 32,
            timestamp=1_700_000_000,
            nonce="fixed-nonce",
        )

        expected_payload = {
            "event_type": "doorbell",
            "metadata": {"trigger": "gpio17"},
            "occurred_at": "2023-11-14T22:13:20Z",
        }
        expected_body = json.dumps(
            expected_payload, separators=(",", ":"), sort_keys=True
        ).encode()
        canonical = b".".join(
            [b"front-door", b"1700000000", b"fixed-nonce", expected_body]
        )
        expected_signature = hmac.new(b"a" * 32, canonical, hashlib.sha256).hexdigest()

        self.assertEqual(
            url,
            "https://amader-home-assistant.souptik.dev/api/v1/ingest/doorbell",
        )
        self.assertEqual(body, expected_body)
        self.assertEqual(
            headers,
            {
                "Content-Type": "application/json",
                "X-Doorbell-Source": "front-door",
                "X-Doorbell-Timestamp": "1700000000",
                "X-Doorbell-Nonce": "fixed-nonce",
                "X-Doorbell-Signature": f"sha256={expected_signature}",
            },
        )

    def test_send_retries_same_signed_event_after_timeout(self) -> None:
        response = Mock(status_code=201)
        with (
            patch.object(
                self.listener.requests,
                "post",
                side_effect=[self.listener.requests.Timeout("timeout"), response],
            ) as post,
            patch.object(self.listener.time, "sleep") as sleep,
            patch.object(self.listener.time, "time", return_value=1_700_000_000),
            patch.object(
                self.listener.secrets, "token_urlsafe", return_value="retry-nonce"
            ),
        ):
            sent = self.listener.send_doorbell_event(
                "https://amader-home-assistant.souptik.dev",
                "front-door",
                "b" * 32,
                attempts=2,
                timeout=10,
            )

        self.assertTrue(sent)
        self.assertEqual(post.call_count, 2)
        first = post.call_args_list[0].kwargs
        second = post.call_args_list[1].kwargs
        self.assertEqual(first["data"], second["data"])
        self.assertEqual(first["headers"], second["headers"])
        self.assertEqual(first["timeout"], 10)
        self.assertFalse(first["allow_redirects"])
        sleep.assert_called_once_with(1)

    def test_build_signed_event_rejects_non_https_server(self) -> None:
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            self.listener.build_signed_event(
                "http://example.test",
                "front-door",
                "c" * 32,
            )

    def test_build_signed_event_rejects_short_secret(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least 32"):
            self.listener.build_signed_event(
                "https://example.test",
                "front-door",
                base64.urlsafe_b64encode(b"short").decode(),
            )


if __name__ == "__main__":
    unittest.main()
