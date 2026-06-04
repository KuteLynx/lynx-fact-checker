const CACHE = 'lynx-fc-v1';

self.addEventListener('install', (e) => {
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(clients.claim());
});

// Interceptar compartir desde otra app
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);

  // Si es un share target (tiene ?url=... en la query)
  if (url.searchParams.has('url')) {
    e.respondWith(
      Response.redirect('/' + url.search, 302)
    );
  }
});
