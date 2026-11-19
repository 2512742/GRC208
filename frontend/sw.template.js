/* RiskTrack service worker (generated at build time by vite.config.ts; do not edit dist/sw.js).
 *
 * - App files (hashed JS/CSS, icons) are precached, so the app opens instantly and offline.
 * - Pages: network first; offline, the cached app shell opens and shows an offline banner.
 * - /api is NEVER cached or intercepted: risk data, evidence and personal data stay on the
 *   server, are always fresh, and nothing sensitive remains on a shared device after sign-out.
 * - Cross-origin requests (Google Fonts) are left to the browser.
 */
const VERSION = "__VERSION__";
const CACHE = `risktrack-${VERSION}`;
const PRECACHE = __PRECACHE__;

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith("risktrack-") && k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

// The page asks the waiting worker to take over when the user clicks "Reload".
self.addEventListener("message", (event) => {
  if (event.data === "SKIP_WAITING") self.skipWaiting();
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname === "/api" || url.pathname.startsWith("/api/")) return; // never cached

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() => caches.match("/index.html").then((r) => r || Response.error())),
    );
    return;
  }

  if (url.pathname.startsWith("/assets/")) {
    // Hashed file names never change: cache first.
    event.respondWith(
      caches.match(request).then(
        (hit) =>
          hit ||
          fetch(request).then((response) => {
            if (response.ok) caches.open(CACHE).then((c) => c.put(request, response.clone()));
            return response;
          }),
      ),
    );
    return;
  }

  // Everything else (icons, manifest, theme script): stale while revalidate.
  event.respondWith(
    caches.match(request).then((hit) => {
      const network = fetch(request)
        .then((response) => {
          if (response.ok) caches.open(CACHE).then((c) => c.put(request, response.clone()));
          return response;
        })
        .catch(() => hit || Response.error());
      return hit || network;
    }),
  );
});
