const CACHE_NAME = "bba-os-v3";
const STATIC_ASSETS = [
    "/static/vendor/tabler/css/tabler.min.css",
    "/static/vendor/tabler/js/tabler.min.js",
    "/static/css/custom.css",
    "/static/css/theme-slash.css",
    "/static/js/datepicker.js",
    "/static/js/color-picker.js",
    "/static/fonts/JetBrainsMono-Regular.woff2",
    "/static/fonts/JetBrainsMono-Bold.woff2",
    "/static/icons/app-192.png",
    "/static/icons/app-512.png",
];

self.addEventListener("install", (event) => {
    event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS)));
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
    );
    self.clients.claim();
});

self.addEventListener("fetch", (event) => {
    const url = new URL(event.request.url);
    if (STATIC_ASSETS.some((asset) => url.pathname === asset)) {
        event.respondWith(caches.match(event.request).then((cached) => cached || fetch(event.request)));
    }
});
