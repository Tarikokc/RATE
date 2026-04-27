const CACHE_NAME = 'rate-pwa-v1';
const STATIC_ASSETS = [
  '/',
  '/manifest.webmanifest'
];

// Install: mise en cache des assets statiques
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate: nettoyage des anciens caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

// Fetch: Network First pour les API, Cache First pour les assets statiques
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Les appels API Flask → toujours réseau (pas de cache)
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(fetch(event.request));
    return;
  }

  // Assets statiques Angular → Cache First avec fallback réseau
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request).then((response) => {
        // Ne cache que les réponses valides
        if (!response || response.status !== 200 || response.type !== 'basic') {
          return response;
        }
        const responseClone = response.clone();
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, responseClone);
        });
        return response;
      }).catch(() => {
        // Offline fallback: retourne la page d'accueil depuis le cache
        if (event.request.destination === 'document') {
          return caches.match('/');
        }
      });
    })
  );
});
