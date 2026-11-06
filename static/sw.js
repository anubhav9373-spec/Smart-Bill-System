const CACHE_NAME = 'smartbill-static-v1';
const STATIC_ASSETS = [
  '/static/css/style.css',
  '/static/css/app-redesign.css',
  '/static/css/home.css',
  '/static/js/api.js',
  '/static/js/billing.js',
  '/static/js/dashboard.js',
  '/static/js/products.js',
  '/static/js/sales.js',
  '/static/js/profile.js',
  '/static/assets/smartbill-logo-dark.svg',
  '/static/assets/smartbill-logo-light.svg',
  '/static/assets/smartbill-favicon.svg',
  '/static/manifest.webmanifest'
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch((err) => {
        console.warn('Pre-cache skipped some optional assets:', err);
      });
    })
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);

  // Never intercept non-GET requests (POST, PUT, DELETE)
  if (request.method !== 'GET') {
    return;
  }

  // Network-first for dynamic API routes & HTML page navigations to always have fresh data
  if (url.pathname.startsWith('/api/') || request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => caches.match(request))
    );
    return;
  }

  // Cache-first (with stale-while-revalidate) for static assets & external web fonts
  if (
    url.pathname.startsWith('/static/') ||
    url.hostname.includes('fonts.googleapis.com') ||
    url.hostname.includes('fonts.gstatic.com') ||
    url.hostname.includes('cdn.jsdelivr.net')
  ) {
    event.respondWith(
      caches.match(request).then((cachedResponse) => {
        const fetchPromise = fetch(request).then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const responseToCache = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, responseToCache));
          }
          return networkResponse;
        }).catch(() => cachedResponse);

        return cachedResponse || fetchPromise;
      })
    );
    return;
  }

  // Default: network with cache fallback
  event.respondWith(
    fetch(request).catch(() => caches.match(request))
  );
});

