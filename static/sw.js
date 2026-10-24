/* Service worker KROMCL.
 *
 * Dělá dvě věci: bez něj si Chrome nemusí web nabídnout k instalaci, a s ním
 * se dají naposledy otevřené stránky číst i bez signálu.
 *
 * Stránky vždy nejdřív ze sítě, mezipaměť jen při výpadku. Web se
 * přestavuje každou hodinu; obráceně by appka ukazovala staré zprávy
 * a program, který už neplatí.
 *
 * Fonty naopak nejdřív z mezipaměti: nemění se a bez nich by offline
 * stránka spadla na náhradní písmo. Ukládají se rovnou při instalaci,
 * aby byly k dispozici i dřív, než si je stránka sama vyžádá.
 *
 * Při změně chování nebo seznamu fontů zvyš VERZE — prohlížeč pak staré
 * úložiště smaže.
 */
const VERZE = 'kromka-v2';
const FONTY = [
  '/fonts/space-grotesk-latin.woff2',
  '/fonts/space-grotesk-latin-ext.woff2',
  '/fonts/syne-latin.woff2',
  '/fonts/syne-latin-ext.woff2',
];

self.addEventListener('install', (udalost) => {
  udalost.waitUntil((async () => {
    // Chybějící font nesmí shodit instalaci celého workeru.
    const uloziste = await caches.open(VERZE);
    await Promise.all(FONTY.map((url) => uloziste.add(url).catch(() => {})));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (udalost) => {
  udalost.waitUntil((async () => {
    for (const klic of await caches.keys()) {
      if (klic !== VERZE) await caches.delete(klic);
    }
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (udalost) => {
  const pozadavek = udalost.request;
  if (pozadavek.method !== 'GET') return;
  const url = new URL(pozadavek.url);

  if (url.origin === self.location.origin && url.pathname.startsWith('/fonts/')) {
    udalost.respondWith((async () => {
      const ulozeny = await caches.match(pozadavek);
      if (ulozeny) return ulozeny;
      const odpoved = await fetch(pozadavek);
      if (odpoved.ok) {
        const kopie = odpoved.clone();
        caches.open(VERZE).then((uloziste) => uloziste.put(pozadavek, kopie));
      }
      return odpoved;
    })());
    return;
  }

  if (pozadavek.mode !== 'navigate') return;

  udalost.respondWith((async () => {
    try {
      const odpoved = await fetch(pozadavek);
      // Chybovou stránku do mezipaměti neukládat, jinak by ji appka
      // offline ukazovala místo poslední dobré verze.
      if (odpoved.ok) {
        const kopie = odpoved.clone();
        caches.open(VERZE).then((uloziste) => uloziste.put(pozadavek, kopie));
      }
      return odpoved;
    } catch (chyba) {
      const ulozena = await caches.match(pozadavek)
        || await caches.match('/')
        || await caches.match('/index.html');
      return ulozena || new Response(
        '<!doctype html><meta charset="utf-8"><meta name="viewport" '
        + 'content="width=device-width,initial-scale=1"><title>Offline</title>'
        + '<p style="font:18px system-ui;padding:24px">Jsi offline a tahle '
        + 'stránka tu ještě uložená není. Až chytíš signál, zkus to znovu.</p>',
        { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
    }
  })());
});
