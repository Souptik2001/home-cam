const TOKEN_KEY = "amader-home-token";
const CAMERA_ORIGIN = "https://camera.souptik.dev";
let token = localStorage.getItem(TOKEN_KEY);
let cameraUrl = null;

const pairing = document.querySelector("#pairing");
const dashboard = document.querySelector("#dashboard");
const statusBox = document.querySelector("#status");
const eventsList = document.querySelector("#events");
const emptyState = document.querySelector("#empty-state");
const pushButton = document.querySelector("#push-button");
const iosInstall = document.querySelector("#ios-install");

function setStatus(message, error = false) {
  statusBox.textContent = message;
  statusBox.classList.toggle("error", error);
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body) headers.set("Content-Type", "application/json");
  const response = await fetch(path, { ...options, headers });
  if (response.status === 401) {
    clearLocalSession();
    throw new Error("This device must be paired again.");
  }
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch (_) {
      // Keep the HTTP fallback message.
    }
    throw new Error(detail);
  }
  if (response.status === 204) return null;
  return response.json();
}

function clearLocalSession() {
  token = null;
  cameraUrl = null;
  localStorage.removeItem(TOKEN_KEY);
  pairing.classList.remove("hidden");
  dashboard.classList.add("hidden");
}

async function disconnectDevice() {
  await api("/api/v1/session/disconnect", { method: "POST" });
  if ("serviceWorker" in navigator) {
    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.getSubscription();
    if (subscription) {
      try {
        await subscription.unsubscribe();
      } catch (_) {
        // The server has already disabled delivery for this subscription.
      }
    }
  }
  clearLocalSession();
}

function isIos() {
  return /iphone|ipad|ipod/i.test(navigator.userAgent);
}

function isStandalone() {
  return window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
}

function base64ToUint8Array(value) {
  const padding = "=".repeat((4 - (value.length % 4)) % 4);
  const base64 = (value + padding).replace(/-/g, "+").replace(/_/g, "/");
  return Uint8Array.from(atob(base64), (character) => character.charCodeAt(0));
}

function buildCameraHistoryUrl(baseUrl, occurredAt) {
  const target = new URL(baseUrl);
  if (target.protocol !== "https:" || target.origin !== CAMERA_ORIGIN) {
    throw new Error("Camera history link is unavailable.");
  }
  const camera = target.hash.slice(1).trim();
  const timestamp = Math.floor(new Date(occurredAt).getTime() / 1000);
  if (!camera || !Number.isFinite(timestamp)) {
    throw new Error("Camera history link is unavailable.");
  }
  target.pathname = "/review";
  target.search = "";
  target.searchParams.set("timestamp", `${camera}_${timestamp}`);
  target.hash = "";
  return target.href;
}

function openEventHistory(event) {
  if (!cameraUrl) return;
  try {
    window.location.assign(buildCameraHistoryUrl(cameraUrl, event.occurred_at));
  } catch (error) {
    setStatus(error.message, true);
  }
}

function renderEvents(events) {
  eventsList.replaceChildren();
  emptyState.classList.toggle("hidden", events.length !== 0);
  for (const event of events) {
    const item = document.createElement("li");
    item.className = "event";
    item.tabIndex = 0;
    item.setAttribute("role", "link");
    item.setAttribute("aria-label", "Open camera history at this event");
    item.addEventListener("click", () => openEventHistory(event));
    item.addEventListener("keydown", (keyEvent) => {
      if (keyEvent.key === "Enter" || keyEvent.key === " ") {
        keyEvent.preventDefault();
        openEventHistory(event);
      }
    });

    const icon = document.createElement("span");
    icon.className = "event-icon";
    icon.textContent = "🔔";

    const details = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = "Doorbell rang";
    const timestamp = document.createElement("time");
    const date = new Date(event.occurred_at);
    timestamp.dateTime = event.occurred_at;
    timestamp.textContent = date.toLocaleString([], {
      dateStyle: "medium",
      timeStyle: "short",
    });
    details.append(title, timestamp);
    item.append(icon, details);
    eventsList.append(item);
  }
}

async function loadDashboard() {
  pairing.classList.add("hidden");
  dashboard.classList.remove("hidden");
  iosInstall.classList.toggle("hidden", !(isIos() && !isStandalone()));
  try {
    const [events, camera] = await Promise.all([
      api("/api/v1/events"),
      api("/api/v1/camera/config"),
    ]);
    cameraUrl = camera.base_url;
    renderEvents(events);
    setStatus("");
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function enableNotifications() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    throw new Error("Push notifications are not supported by this browser.");
  }
  if (isIos() && !isStandalone()) {
    iosInstall.classList.remove("hidden");
    throw new Error("Add this app to your iPhone Home Screen first.");
  }
  const permission = await Notification.requestPermission();
  if (permission !== "granted") throw new Error("Notification permission was not granted.");

  const registration = await navigator.serviceWorker.ready;
  const { public_key: publicKey } = await api("/api/v1/push/vapid-public-key");
  let subscription = await registration.pushManager.getSubscription();
  if (!subscription) {
    subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: base64ToUint8Array(publicKey),
    });
  }
  const serialized = subscription.toJSON();
  await api("/api/v1/push/subscriptions", {
    method: "POST",
    body: JSON.stringify({
      name: isIos() ? "iPhone PWA" : "Web PWA",
      endpoint: serialized.endpoint,
      expiration_time: serialized.expirationTime ?? null,
      keys: serialized.keys,
    }),
  });
  pushButton.textContent = "Notifications enabled";
  pushButton.disabled = true;
}

document.querySelector("#pair-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  setStatus("Pairing…");
  try {
    const result = await api("/api/v1/pair", {
      method: "POST",
      body: JSON.stringify({
        code: document.querySelector("#pairing-code").value,
        name: document.querySelector("#device-name").value,
      }),
    });
    token = result.token;
    localStorage.setItem(TOKEN_KEY, token);
    document.querySelector("#pairing-code").value = "";
    await loadDashboard();
  } catch (error) {
    setStatus(error.message, true);
  }
});

document.querySelector("#refresh-button").addEventListener("click", async () => {
  setStatus("Refreshing…");
  try {
    renderEvents(await api("/api/v1/events"));
    setStatus("Updated");
  } catch (error) {
    setStatus(error.message, true);
  }
});

document.querySelector("#camera-button").addEventListener("click", () => {
  if (cameraUrl) window.location.assign(cameraUrl);
});

pushButton.addEventListener("click", async () => {
  setStatus("Enabling notifications…");
  try {
    await enableNotifications();
    setStatus("Doorbell notifications are enabled.");
  } catch (error) {
    setStatus(error.message, true);
  }
});

document.querySelector("#disconnect-button").addEventListener("click", async () => {
  setStatus("Disconnecting…");
  try {
    await disconnectDevice();
    setStatus("This device has been disconnected.");
  } catch (error) {
    setStatus(`Could not disconnect: ${error.message}`, true);
  }
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js?v=4").catch(() => {
    setStatus("The notification service could not start.", true);
  });
}

if (token) loadDashboard();
