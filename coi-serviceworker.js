/*! coi-serviceworker
 *  Adapted from https://github.com/gzuidhof/coi-serviceworker (MIT License)
 *  Adds Cross-Origin-Opener-Policy and Cross-Origin-Embedder-Policy headers
 *  so SharedArrayBuffer is available on hosts that can't set headers (e.g. GitHub Pages).
 */
(() => {
  if (typeof window === 'undefined') {
    // Service worker context.
    self.addEventListener('install', () => self.skipWaiting());
    self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));

    self.addEventListener('fetch', (event) => {
      const r = event.request;
      if (r.cache === 'only-if-cached' && r.mode !== 'same-origin') return;

      const request =
        r.cache === 'no-store'
          ? r
          : new Request(r, { cache: 'no-store', mode: r.mode === 'navigate' ? 'same-origin' : r.mode });

      event.respondWith(
        fetch(request)
          .then((response) => {
            if (response.status === 0) return response;
            const newHeaders = new Headers(response.headers);
            newHeaders.set('Cross-Origin-Embedder-Policy', 'require-corp');
            newHeaders.set('Cross-Origin-Opener-Policy', 'same-origin');
            newHeaders.set('Cross-Origin-Resource-Policy', 'cross-origin');
            return new Response(response.body, {
              status: response.status,
              statusText: response.statusText,
              headers: newHeaders,
            });
          })
          .catch((e) => console.error('coi-serviceworker fetch error:', e))
      );
    });
  } else {
    // Page context: register the SW (this same file) and reload once if needed.
    const reloadedKey = 'coiReloadedBySW';

    if (!window.crossOriginIsolated && navigator.serviceWorker) {
      navigator.serviceWorker
        .register(window.document.currentScript.src, { scope: './' })
        .then((registration) => {
          registration.addEventListener('updatefound', () => {
            console.log('coi-serviceworker update found, reloading.');
            window.location.reload();
          });
          if (registration.active && !navigator.serviceWorker.controller) {
            // First install on this origin: reload so the SW can intercept.
            if (!sessionStorage.getItem(reloadedKey)) {
              sessionStorage.setItem(reloadedKey, '1');
              window.location.reload();
            }
          }
        })
        .catch((err) => console.error('coi-serviceworker registration failed:', err));
    }
  }
})();
