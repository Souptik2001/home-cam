from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess

import pytest
from conftest import RecordingPushSender, auth_header, signed_ingest
from fastapi.testclient import TestClient

from amader_home_assistant.main import create_app


def test_pwa_assets_are_served_with_installable_manifest(client: TestClient) -> None:
    index = client.get("/")
    manifest = client.get("/manifest.webmanifest")
    app_script = client.get("/app.js")
    service_worker = client.get("/sw.js")

    assert index.status_code == 200
    assert index.text.count("Amader Home Assistant") == 2
    assert "PRIVATE DOORBELL" not in index.text
    assert "Doorbell history and instant camera access." not in index.text
    assert 'rel="manifest"' in index.text
    assert 'href="/styles.css?v=5"' in index.text
    assert 'src="/app.js?v=5"' in index.text
    assert manifest.status_code == 200
    assert manifest.json()["display"] == "standalone"
    assert manifest.json()["start_url"] == "/"
    assert app_script.status_code == 200
    assert 'serviceWorker.register("/sw.js?v=5")' in app_script.text
    assert "buildCameraHistoryUrl" in app_script.text
    assert "buildEventsPagePath" in app_script.text
    assert "eventDateKey" in app_script.text
    assert 'item.addEventListener("click"' in app_script.text
    assert "IntersectionObserver" in app_script.text
    assert 'id="events-sentinel"' in index.text
    assert 'id="events-retry"' in index.text
    assert service_worker.status_code == 200
    assert 'const CACHE = "amader-home-v5"' in service_worker.text
    assert '"/styles.css?v=5"' in service_worker.text
    assert '"/app.js?v=5"' in service_worker.text
    assert "notificationclick" in service_worker.text
    assert (
        service_worker.headers["cache-control"] == "no-store, no-cache, must-revalidate"
    )
    assert service_worker.headers["cloudflare-cdn-cache-control"] == "no-store"
    assert service_worker.headers["service-worker-allowed"] == "/"


def test_pwa_history_link_uses_exact_timestamp_and_rejects_other_origins(
    client: TestClient,
) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the browser URL behavior test")
    assert node is not None

    source = client.get("/app.js").text
    start = source.index("function buildCameraHistoryUrl")
    end = source.index("\n\nfunction openEventHistory", start)
    function_source = source[start:end]
    page_start = source.index("function buildEventsPagePath")
    page_end = source.index("\n\nfunction eventDateKey", page_start)
    page_function_source = source[page_start:page_end]
    date_start = page_end + 2
    date_end = source.index("\n\nfunction eventDateHeading", date_start)
    date_function_source = source[date_start:date_end]
    heading_start = date_end + 2
    heading_end = source.index("\n\nfunction appendEvents", heading_start)
    heading_function_source = source[heading_start:heading_end]
    append_start = heading_end + 2
    append_end = source.index("\n\nasync function loadEvents", append_start)
    append_function_source = source[append_start:append_end]
    script = f"""
const CAMERA_ORIGIN = "https://camera.souptik.dev";
{function_source}
{page_function_source}
{date_function_source}
{heading_function_source}
{append_function_source}
const expected = "https://camera.souptik.dev/review?timestamp=pi_cam_2_1792431826";
const actual = buildCameraHistoryUrl(
  "https://camera.souptik.dev/#pi_cam_2",
  "2026-10-19T17:43:46Z",
);
if (actual !== expected) throw new Error(`${{actual}} != ${{expected}}`);
for (const unsafe of [
  "http://camera.souptik.dev/#pi_cam_2",
  "https://attacker.example/#pi_cam_2",
]) {{
  let rejected = false;
  try {{ buildCameraHistoryUrl(unsafe, "2026-10-19T17:43:46Z"); }}
  catch (_) {{ rejected = true; }}
  if (!rejected) throw new Error(`unsafe camera URL accepted: ${{unsafe}}`);
}}
if (buildEventsPagePath(null) !== "/api/v1/events?limit=20&paginated=true") {{
  throw new Error("first events page URL is incorrect");
}}
if (buildEventsPagePath("older cursor") !== "/api/v1/events?limit=20&paginated=true&cursor=older+cursor") {{
  throw new Error("events cursor was not encoded");
}}
if (eventDateKey("2026-10-19T17:43:46Z") !== "2026-10-19") {{
  throw new Error("event date grouping key is incorrect");
}}
class FakeElement {{
  constructor(tagName) {{
    this.tagName = tagName;
    this.children = [];
    this.className = "";
    this.dataset = {{}};
    this.textContent = "";
  }}
  append(...children) {{ this.children.push(...children); }}
  setAttribute() {{}}
  addEventListener() {{}}
}}
const document = {{ createElement: (tagName) => new FakeElement(tagName) }};
const eventsList = new FakeElement("ol");
let lastEventDateKey = null;
let eventIds = new Set();
function openEventHistory() {{}}
appendEvents([
  {{ id: "one", occurred_at: "2026-10-19T10:00:00Z" }},
  {{ id: "two", occurred_at: "2026-10-19T09:00:00Z" }},
  {{ id: "three", occurred_at: "2026-10-18T20:00:00Z" }},
]);
const rowClasses = eventsList.children.map((child) => child.className);
if (rowClasses.join(",") !== "event-date,event,event,event-date,event") {{
  throw new Error(`event rows were not grouped by date: ${{rowClasses}}`);
}}
"""
    subprocess.run(
        [node, "-e", script],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "TZ": "UTC"},
    )


def test_pwa_event_loading_refresh_deduplication_and_retry_state(
    client: TestClient,
) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the browser event-loading behavior test")
    assert node is not None

    source = client.get("/app.js").text
    build_start = source.index("function buildEventsPagePath")
    build_end = source.index("\n\nfunction eventDateKey", build_start)
    build_source = source[build_start:build_end]
    date_start = build_end + 2
    append_end = source.index("\n\nasync function loadEvents", date_start)
    helpers_source = source[date_start:append_end]
    load_start = append_end + 2
    load_end = source.index("\n\nasync function loadDashboard", load_start)
    load_source = source[load_start:load_end]
    script = f"""
class FakeClassList {{
  constructor() {{ this.values = new Set(); }}
  add(value) {{ this.values.add(value); }}
  remove(value) {{ this.values.delete(value); }}
  toggle(value, force) {{
    if (force === undefined ? !this.values.has(value) : force) this.values.add(value);
    else this.values.delete(value);
  }}
  contains(value) {{ return this.values.has(value); }}
}}
class FakeElement {{
  constructor(tagName) {{
    this.tagName = tagName;
    this.children = [];
    this.className = "";
    this.classList = new FakeClassList();
    this.dataset = {{}};
    this.textContent = "";
  }}
  append(...children) {{ this.children.push(...children); }}
  replaceChildren(...children) {{ this.children = [...children]; }}
  setAttribute() {{}}
  addEventListener() {{}}
}}
const document = {{ createElement: (tagName) => new FakeElement(tagName) }};
const eventsList = new FakeElement("ol");
const eventsSentinel = new FakeElement("div");
const eventsLoading = new FakeElement("span");
const eventsRetry = new FakeElement("button");
const emptyState = new FakeElement("p");
let nextEventsCursor = "older";
let loadingEvents = false;
let eventsGeneration = 0;
let lastEventDateKey = null;
let eventIds = new Set();
let status = "";
function setStatus(message) {{ status = message; }}
function openEventHistory() {{}}
{build_source}
{helpers_source}
{load_source}
let resolveOlder;
const calls = [];
async function api(path) {{
  calls.push(path);
  if (path.includes("cursor=older")) {{
    return new Promise((resolve) => {{ resolveOlder = resolve; }});
  }}
  return {{
    events: [
      {{ id: "fresh", occurred_at: "2026-10-19T10:00:00Z" }},
      {{ id: "fresh", occurred_at: "2026-10-19T10:00:00Z" }},
    ],
    next_cursor: null,
  }};
}}
const lazy = loadEvents();
const refresh = loadEvents({{ reset: true }});
await refresh;
resolveOlder({{
  events: [{{ id: "stale", occurred_at: "2026-10-18T10:00:00Z" }}],
  next_cursor: null,
}});
await lazy;
const eventRows = eventsList.children.filter((child) => child.className === "event");
if (calls.length !== 2) throw new Error(`refresh was discarded: ${{calls}}`);
if (eventRows.length !== 1 || eventRows[0].dataset.eventId !== "fresh") {{
  throw new Error("refresh/deduplication state is incorrect");
}}
nextEventsCursor = "failure";
api = async () => {{ throw new Error("offline"); }};
await loadEvents();
if (eventsSentinel.classList.contains("hidden")) throw new Error("retry sentinel hidden");
if (!eventsLoading.classList.contains("hidden")) throw new Error("loading label remained visible");
if (eventsRetry.classList.contains("hidden")) throw new Error("retry control hidden");
"""
    subprocess.run(
        [node, "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "TZ": "UTC"},
    )


def test_authenticated_pwa_can_read_vapid_key_and_register_subscription(
    settings, push_sender: RecordingPushSender
) -> None:
    configured = settings.model_copy(
        update={
            "web_push_vapid_public_key": "public-vapid-key",
            "web_push_vapid_private_key": "private-vapid-key",
            "web_push_vapid_subject": "mailto:admin@souptik.dev",
        }
    )
    web_sender = RecordingPushSender(provider_message_id="web-push")
    with TestClient(
        create_app(
            settings=configured,
            push_sender=push_sender,
            web_push_sender=web_sender,
        )
    ) as client:
        paired = client.post(
            "/api/v1/pair", json={"code": "pair-once", "name": "iPhone PWA"}
        )
        token = paired.json()["token"]

        vapid = client.get("/api/v1/push/vapid-public-key", headers=auth_header(token))
        registered = client.post(
            "/api/v1/push/subscriptions",
            headers=auth_header(token),
            json={
                "name": "iPhone PWA",
                "endpoint": "https://web.push.apple.com/example/subscription",
                "expiration_time": None,
                "keys": {"p256dh": "browser-public-key", "auth": "browser-auth"},
            },
        )

    assert vapid.status_code == 200
    assert vapid.json() == {"public_key": "public-vapid-key"}
    assert registered.status_code == 201
    assert registered.json()["platform"] == "web"


def test_web_subscription_requires_approved_https_endpoint(
    paired_client: tuple[TestClient, str],
) -> None:
    client, token = paired_client

    insecure = client.post(
        "/api/v1/push/subscriptions",
        headers=auth_header(token),
        json={
            "name": "Unsafe browser",
            "endpoint": "http://push.example.test/subscription",
            "keys": {"p256dh": "browser-public-key", "auth": "browser-auth"},
        },
    )
    unapproved = client.post(
        "/api/v1/push/subscriptions",
        headers=auth_header(token),
        json={
            "name": "Unapproved browser",
            "endpoint": "https://127.0.0.1/subscription",
            "keys": {"p256dh": "browser-public-key", "auth": "browser-auth"},
        },
    )

    assert insecure.status_code == 422
    assert unapproved.status_code == 422
    assert "approved push service" in unapproved.text


def test_generic_device_route_rejects_web_platform(
    paired_client: tuple[TestClient, str],
) -> None:
    client, token = paired_client

    response = client.post(
        "/api/v1/devices",
        headers=auth_header(token),
        json={"name": "Bypass", "platform": "web", "push_token": "{}"},
    )

    assert response.status_code == 422


def test_doorbell_event_routes_web_device_to_web_push_sender(
    settings, push_sender: RecordingPushSender, database_path
) -> None:
    configured = settings.model_copy(
        update={
            "web_push_vapid_public_key": "public-vapid-key",
            "web_push_vapid_private_key": "private-vapid-key",
            "web_push_vapid_subject": "mailto:admin@souptik.dev",
        }
    )
    web_sender = RecordingPushSender(provider_message_id="web-provider-message")
    with TestClient(
        create_app(
            settings=configured,
            push_sender=push_sender,
            web_push_sender=web_sender,
        )
    ) as client:
        paired = client.post(
            "/api/v1/pair", json={"code": "pair-once", "name": "iPhone PWA"}
        )
        token = paired.json()["token"]
        subscription = {
            "endpoint": "https://web.push.apple.com/example/subscription",
            "expirationTime": None,
            "keys": {"p256dh": "browser-public-key", "auth": "browser-auth"},
        }
        registered = client.post(
            "/api/v1/push/subscriptions",
            headers=auth_header(token),
            json={
                "name": "iPhone PWA",
                "endpoint": subscription["endpoint"],
                "expiration_time": None,
                "keys": subscription["keys"],
            },
        )
        assert registered.status_code == 201

        ingested = signed_ingest(
            client,
            {"occurred_at": "2026-10-17T10:00:00Z"},
            nonce="web-push-event",
        )

    assert ingested.status_code == 201
    assert push_sender.calls == []
    assert len(web_sender.calls) == 1
    stored_subscription, message = web_sender.calls[0]
    assert json.loads(stored_subscription) == subscription
    assert message.data["camera_url"] == "https://camera.souptik.dev/#pi_cam_2"
    assert message.data["route"] == "/camera"
    with sqlite3.connect(database_path) as connection:
        attempt = connection.execute(
            "SELECT status, provider_message_id FROM notification_delivery_attempts"
        ).fetchone()
    assert attempt == ("sent", "web-provider-message")


def test_disconnect_revokes_session_and_stops_web_push_delivery(
    settings, push_sender: RecordingPushSender, database_path
) -> None:
    web_sender = RecordingPushSender(provider_message_id="should-not-send")
    with TestClient(
        create_app(
            settings=settings,
            push_sender=push_sender,
            web_push_sender=web_sender,
        )
    ) as client:
        paired = client.post(
            "/api/v1/pair", json={"code": "pair-once", "name": "iPhone PWA"}
        )
        token = paired.json()["token"]
        registered = client.post(
            "/api/v1/push/subscriptions",
            headers=auth_header(token),
            json={
                "name": "iPhone PWA",
                "endpoint": "https://web.push.apple.com/disconnect-test",
                "keys": {"p256dh": "browser-public-key", "auth": "browser-auth"},
            },
        )
        assert registered.status_code == 201

        disconnected = client.post(
            "/api/v1/session/disconnect", headers=auth_header(token)
        )
        ingested = signed_ingest(
            client,
            {"occurred_at": "2026-10-17T10:00:00Z"},
            nonce="after-disconnect",
        )
        rejected = client.get("/api/v1/events", headers=auth_header(token))

    assert disconnected.status_code == 204
    assert ingested.status_code == 201
    assert rejected.status_code == 401
    assert web_sender.calls == []
    with sqlite3.connect(database_path) as connection:
        enabled, active = connection.execute(
            "SELECT pd.enabled, ps.active FROM paired_devices pd "
            "JOIN paired_sessions ps ON ps.id=pd.session_id"
        ).fetchone()
        attempts = connection.execute(
            "SELECT COUNT(*) FROM notification_delivery_attempts"
        ).fetchone()[0]
    assert (enabled, active) == (0, 0)
    assert attempts == 0
