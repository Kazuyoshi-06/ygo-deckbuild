/// <reference types="@sveltejs/kit" />
/// <reference no-default-lib="true"/>
/// <reference lib="esnext" />
/// <reference lib="webworker" />

import { build, files, version } from '$service-worker';

const sw = /** @type {ServiceWorkerGlobalScope} */ (/** @type {unknown} */ (self));

const CACHE = `ygo-intel-${version}`;
// App shell only — built JS/CSS bundles plus static assets (icons, fonts config, etc).
// API responses are intentionally never cached here: they're already served through
// the Redis cache layer (T3.7) with its own TTL/invalidation, and serving stale deck
// or banlist data offline would be actively misleading.
const ASSETS = [...build, ...files];

sw.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.addAll(ASSETS))
      .then(() => sw.skipWaiting())
  );
});

sw.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))))
      .then(() => sw.clients.claim())
  );
});

sw.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;

  const url = new URL(event.request.url);
  if (url.pathname.startsWith('/api/')) return; // always go to the network for data

  event.respondWith(
    (async () => {
      const cache = await caches.open(CACHE);

      // Network-first: prefer fresh app code/assets when online, fall back to the
      // cached app shell when offline so the UI still loads instead of showing
      // the browser's offline error page.
      try {
        const response = await fetch(event.request);
        if (response.ok) cache.put(event.request, response.clone());
        return response;
      } catch {
        const cached = await cache.match(event.request);
        if (cached) return cached;
        throw new Error(`Offline and no cached response for ${event.request.url}`);
      }
    })()
  );
});
