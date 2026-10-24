/* Service worker KROMCL.
 *
 * Dělá dvě věci: bez něj si Chrome nemusí web nabídnout k instalaci, a s ním
 * se dají naposledy otevřené stránky číst i bez signálu.
 *
 * Vždy nejdřív síť, mezipaměť jen při výpadku. Web se přestavuje každou
 * hodinu; obráceně by appka ukazovala staré zprávy a program, který už neplatí.
 * Ukládají se jen celé stránky (navigace), ne obrázky ani cizí fonty.
 *
 * Při změně chování zvyš VERZE — prohlížeč pak staré úložiště smaže.
 */
const VERZE = 'kromka-v1';

self.addEventListener('install', () => self.skipWaiting());

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
  if (pozadavek.mode !== 'navigate' || pozadavek.method !== 'GET') return;

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
