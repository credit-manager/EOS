/**
 * EOS Service Worker — P66 Mobile / PWA
 *
 * Strategy:
 * - App shell + static assets: cache-first with background refresh
 * - API GET requests: network-first, fallback to cache (read-only offline)
 * - API writes (POST/PUT/DELETE): never cached — handled by the app-level
 *   offline queue (src/services/offlineQueue.ts) which replays them on reconnect
 * - Navigation requests: network-first, fallback to cached shell
 */

const CACHE_NAME = 'eos-cache-v1';
const SHELL_CACHE = 'eos-shell-v1';

const APP_SHELL = [
  '/',
  '/index.html',
  '/manifest.webmanifest',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      .then((cache) => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key !== SHELL_CACHE && key !== CACHE_NAME)
            .map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

function isApiRequest(url) {
  return url.pathname.includes('/api/');
}

function isWriteMethod(method) {
  return method !== 'GET';
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Same-origin only
  if (url.origin !== self.location.origin) return;

  // Never intercept writes — the app offline queue owns them
  if (isWriteMethod(request.method)) return;

  // API reads: network-first, cache fallback (offline read-only ERP)
  if (isApiRequest(url)) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response && response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(() =>
          caches.match(request).then(
            (cached) =>
              cached ||
              new Response(
                JSON.stringify({ detail: 'offline', offline: true }),
                { status: 503, headers: { 'Content-Type': 'application/json' } }
              )
          )
        )
    );
    return;
  }

  // Static assets: cache-first, refresh in background
  event.respondWith(
    caches.match(request).then((cached) => {
      const network = fetch(request)
        .then((response) => {
          if (response && response.ok) {
            const clone = response.clone();
            caches.open(SHELL_CACHE).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => cached);
      return cached || network;
    })
  );
});

// Allow the page to trigger immediate activation of an updated SW
self.addEventListener('message', (event) => {
  if (event.data === 'SKIP_WAITING') self.skipWaiting();
});

// Background sync hook: notify open clients to replay the offline queue
self.addEventListener('sync', (event) => {
  if (event.tag === 'eos-offline-sync') {
    event.waitUntil(
      self.clients.matchAll({ includeUncontrolled: true }).then((clients) => {
        clients.forEach((client) => client.postMessage({ type: 'REPLAY_OFFLINE_QUEUE' }));
      })
    );
  }
});
