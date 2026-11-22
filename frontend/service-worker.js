// SIGE - Service Worker com Estratégia Network-First (Garante Atualizações Imediatas)
const CACHE_NAME = 'sige-cache-v3.6.1-20261122_1400';
const ASSETS_TO_CACHE = [
  '/',
  '/contacto.html',
  '/privacidade.html',
  '/termos.html',
  '/404.html',
  '/site/site.css',
  '/site/site.js',
  '/login',
  '/login.html',
  '/painel.html',
  '/index.html',
  '/manifest.json',
  '/img/logo-sige.png',
  '/img/logo-sige.jpg'
];

self.addEventListener('message', (event) => {
  if (event.data && (event.data.action === 'skipWaiting' || event.data === 'skipWaiting')) {
    self.skipWaiting();
  }
});

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE).catch(() => {});
    })
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log('[SW SIGE] Limpando cache antigo:', key);
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  // Ignora requisições de API, healthcheck e version.json para garantir deteccao imediata de atualizacoes
  if (event.request.method !== 'GET' || 
      event.request.url.includes('/api/') || 
      event.request.url.includes('/health/') ||
      event.request.url.includes('version.json')) {
    return;
  }

  // Network-First: Sempre tenta buscar a versão mais recente do servidor
  event.respondWith(
    fetch(event.request)
      .then((networkResponse) => {
        // Se obteve sucesso na rede, atualiza o cache e devolve a resposta mais recente
        if (networkResponse && networkResponse.status === 200) {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        return networkResponse;
      })
      .catch(() => {
        // Se a rede falhar (offline), busca no cache como contingência
        return caches.match(event.request).then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }
          if (event.request.mode === 'navigate') {
            // Offline: /login -> login.html; caminhos de painel (/<perfil>/<página>) -> painel.html
            const caminho = new URL(event.request.url).pathname;
            if (caminho === '/login') return caches.match('/login.html');
            if (/^\/[a-z]{3,20}(\/[a-z0-9-]{1,50})?\/?$/.test(caminho) && caminho !== '/') return caches.match('/painel.html');
            return caches.match('/login.html');
          }
        });
      })
  );
});
