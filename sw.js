// Guarda o formulário e as bases de endereços para funcionar sem internet.
const VERSAO = "dengue-v1";
const ESSENCIAIS = ["./", "index.html", "manifest.webmanifest", "icone.svg", "bases/municipios.json"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(VERSAO).then(c => c.addAll(ESSENCIAIS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(ks => Promise.all(ks.filter(k => k !== VERSAO).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.includes("/bases/") && !url.pathname.endsWith("municipios.json")) {
    // Bases de endereços: usa a cópia guardada; só baixa se ainda não tiver
    e.respondWith(caches.open(VERSAO).then(async c => {
      const guardada = await c.match(e.request, {ignoreSearch: true});
      if (guardada) return guardada;
      const r = await fetch(e.request);
      if (r.ok) c.put(e.request, r.clone());
      return r;
    }));
    return;
  }
  // Página e lista de municípios: tenta a versão nova; sem internet, usa a guardada
  e.respondWith(fetch(e.request).then(r => {
    if (r.ok) caches.open(VERSAO).then(c => c.put(e.request, r.clone()));
    return r;
  }).catch(() => caches.match(e.request, {ignoreSearch: true}).then(r => r || caches.match("index.html"))));
});
