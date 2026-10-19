const CACHE = "amader-home-v5";
const SHELL = [
  "/",
  "/styles.css?v=5",
  "/app.js?v=5",
  "/manifest.webmanifest",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
];
const CAMERA_ORIGIN = "https://camera.souptik.dev";

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))),
    ),
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET" || new URL(event.request.url).origin !== self.location.origin) return;
  if (new URL(event.request.url).pathname.startsWith("/api/")) return;
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE).then((cache) => cache.put(event.request, copy));
        return response;
      })
      .catch(() => caches.match(event.request).then((response) => response || caches.match("/"))),
  );
});

self.addEventListener("push", (event) => {
  let payload = { title: "Doorbell", body: "Someone rang the doorbell.", data: {} };
  try {
    if (event.data) payload = event.data.json();
  } catch (_) {
    // Retain the generic notification for malformed provider data.
  }
  event.waitUntil(
    self.registration.showNotification(payload.title || "Doorbell", {
      body: payload.body || "Someone rang the doorbell.",
      icon: "/icons/icon-192.png",
      badge: "/icons/badge-96.png",
      tag: payload.data?.event_id || "doorbell",
      renotify: true,
      data: payload.data || {},
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  let target = "/";
  try {
    const candidate = new URL(event.notification.data?.camera_url || "");
    if (candidate.origin === CAMERA_ORIGIN && candidate.protocol === "https:") target = candidate.href;
  } catch (_) {
    // Fall back to the authenticated PWA.
  }
  event.waitUntil(self.clients.openWindow(target));
});
