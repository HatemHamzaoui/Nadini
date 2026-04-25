/**
 * Nadini — Service Worker
 * Cache-first for static assets, network-first for HTML pages.
 */
const CACHE_NAME = "nadini-v1";

const PRECACHE = [
  "/assets/favicon.svg",
  "/assets/icon-192.svg",
  "/assets/icon-512.svg",
  "/app/style.css",
  "/app/meeting.css",
  "/app/i18n-app.js",
  "/app/auth.js",
  "/app/page-common.js",
  "/app/dashboard.js",
  "/app/meeting.js",
  "/app/settings.js",
  "/app/toast.js",
  "/app/config.js",
  "/landing/style.css",
  "/landing/i18n.js",
  "/landing/app.js",
];

// Install: precache static assets
self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE))
  );
  self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch: network-first for HTML, cache-first for assets
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);

  // Skip non-GET
  if (e.request.method !== "GET") return;

  // HTML pages: network first, fallback to cache
  if (e.request.headers.get("accept")?.includes("text/html")) {
    e.respondWith(
      fetch(e.request)
        .then((res) => {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(e.request, clone));
          return res;
        })
        .catch(() => caches.match(e.request).then((r) => r || caches.match("/404.html")))
    );
    return;
  }

  // Assets: cache first, fallback to network
  e.respondWith(
    caches.match(e.request).then((cached) => {
      if (cached) return cached;
      return fetch(e.request).then((res) => {
        // Cache successful responses
        if (res.ok && url.origin === self.location.origin) {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(e.request, clone));
        }
        return res;
      });
    })
  );
});
