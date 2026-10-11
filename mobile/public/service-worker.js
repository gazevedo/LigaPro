/* Only the offline page and public app icons are cached. API responses remain private. */
const CACHE_NAME = 'ligapro-install-v4';
const OFFLINE_PAGE = '/offline.html';
const PUBLIC_FILES = [OFFLINE_PAGE, '/icons/icon-192.png', '/icons/icon-512.png', '/icons/icon-maskable-512.png', '/icons/apple-touch-icon.png'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(PUBLIC_FILES)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('ligapro-install-') && key !== CACHE_NAME).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin || url.pathname === '/api' || url.pathname.startsWith('/api/') || url.pathname.startsWith('/ws/')) return;
  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).catch(() => caches.match(OFFLINE_PAGE)));
  } else if (PUBLIC_FILES.includes(url.pathname)) {
    event.respondWith(caches.match(request).then(cached => cached || fetch(request)));
  }
});
self.addEventListener('push', event => {
  if (!event.data) return;
  let data;
  try { data = event.data.json(); } catch { return; }
  if (!/^[a-f0-9]{24}$/.test(data.match_id || '')) return;
  event.waitUntil(self.registration.showNotification(data.title || 'LigaPro', {
    body: data.body, icon: '/icons/icon-192.png', badge: '/icons/icon-192.png',
    tag: `match-${data.match_id}`, data: { matchId: data.match_id },
  }));
});
self.addEventListener('notificationclick', event => {
  event.notification.close();
  if (!/^[a-f0-9]{24}$/.test(event.notification.data?.matchId || '')) return;
  event.waitUntil(self.clients.openWindow(`/?matchReminder=${encodeURIComponent(event.notification.data.matchId)}`));
});
