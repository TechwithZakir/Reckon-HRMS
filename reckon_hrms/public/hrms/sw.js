// Minimal offline shell for the HRMS home and check-in pages. Network first; cache as fallback.
const CACHE = "reckon-hrms-v1";
const SHELL = ["/hrms-home", "/hrms-checkin"];
self.addEventListener("install", (e) => e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL))));
self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET" || e.request.url.includes("/api/")) return;
  e.respondWith(fetch(e.request).then((r) => {
    const copy = r.clone();
    caches.open(CACHE).then((c) => c.put(e.request, copy));
    return r;
  }).catch(() => caches.match(e.request)));
});
