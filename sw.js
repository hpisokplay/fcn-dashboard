/* FCN 部位監控儀表板 — Service Worker
 * 策略:
 *  - 同源檔案 (index.html / manifest / prices.json / data.csv / 圖示):網路優先 → 離線時回退快取。
 *    這確保「上線時永遠拿到最新版與最新股價」,不會被舊快取卡住。
 *  - 第三方靜態程式庫 (Vue / Tailwind / FontAwesome…):快取優先(版本固定,可離線)。
 *  - 其他(股價代理 / Yahoo 等即時資料):不攔截,一律走網路,永不快取。
 */
const CACHE = 'fcn-dash-v1';
const CORE = [
  './',
  './index.html',
  './manifest.json',
  './icon-192.png',
  './icon-512.png',
  './apple-touch-icon.png',
];
const STATIC_HOSTS = [
  'cdn.tailwindcss.com',
  'cdnjs.cloudflare.com',
  'unpkg.com',
  'cdn.jsdelivr.net',
  'fonts.googleapis.com',
  'fonts.gstatic.com',
  'use.fontawesome.com',
  'ka-f.fontawesome.com',
];

self.addEventListener('install', (e) => {
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(CORE)).catch(() => {}));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  let url;
  try { url = new URL(req.url); } catch (_) { return; }

  // 同源:網路優先,離線回退快取
  if (url.origin === self.location.origin) {
    e.respondWith(
      fetch(req)
        .then((res) => {
          if (res && res.status === 200 && res.type === 'basic') {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
          }
          return res;
        })
        .catch(() => caches.match(req).then((r) => r || caches.match('./index.html')))
    );
    return;
  }

  // 第三方靜態程式庫:快取優先(背景更新)
  if (STATIC_HOSTS.includes(url.hostname)) {
    e.respondWith(
      caches.match(req).then((cached) => {
        const net = fetch(req)
          .then((res) => {
            if (res && (res.status === 200 || res.type === 'opaque')) {
              const copy = res.clone();
              caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
            }
            return res;
          })
          .catch(() => cached);
        return cached || net;
      })
    );
    return;
  }

  // 其他(即時資料):不攔截 → 一律走網路,永不快取
});
