/* KROMCL jako appka: registrace service workeru, výzva k instalaci,
 * tlačítko Sdílet, události GA4 a Core Web Vitals.
 *
 * Jediný vlastní JavaScript na webu (vedle měření GA4 v hlavičce, viz
 * render.MERENI). Bez něj nic nechybí — lišta se vkládá až
 * odsud, takže kdo JS nemá, neuvidí rozbité tlačítko.
 *
 * Kdy se lišta ukáže:
 *   - nejdřív na druhé zobrazené stránce; na první je to vlezlé, člověk
 *     ještě neví, jestli tu chce zůstat
 *   - po „Teď ne" ne dřív než za 30 dní
 *   - nikdy, když už web běží jako appka nebo je nainstalovaný
 *
 * Chrome, Edge a Android mají vlastní instalační dialog (beforeinstallprompt).
 * Safari na iPhonu ho nemá, tam lišta jen poradí cestu přes Sdílet.
 * Ostatní prohlížeče instalaci neumí a nic se neukáže.
 */
(function () {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(function () {});
  }

  // Události GA4. Funkce gtag existuje jen na ostré doméně (render.MERENI),
  // jinde se nic neměří. Kliknutí se poznají podle tříd ze šablony, test
  // v tests/test_kromka.py hlídá, že tam pořád jsou.
  function zmer(nazev, parametry) {
    if (window.gtag) window.gtag('event', nazev, parametry || {});
  }

  // Pořadí rozhoduje: štítek uvnitř „Další z Kroměříže" se počítá jako dalsi.
  var NAVIGACE = [['.dalsi', 'dalsi'], ['.drobecky', 'drobecky'],
    ['.menu', 'menu'], ['.stitek', 'stitek']];

  document.addEventListener('click', function (udalost) {
    var a = udalost.target.closest && udalost.target.closest('a[href]');
    if (!a) return;
    if (a.closest('.pribeh-odkaz')) return zmer('pribeh_stazeni');
    if (/\/feed\.xml$/.test(a.pathname)) return zmer('rss_klik');
    if (a.classList.contains('filtr-odkaz')) {
      // /program.html → vse, /program/kino.html → kino
      var typ = a.pathname.indexOf('/program/') === 0
        ? a.pathname.slice(9).replace(/\.html$/, '') : 'vse';
      return zmer('program_filtr', { typ_akce: typ });
    }
    for (var i = 0; i < NAVIGACE.length; i++) {
      if (a.closest(NAVIGACE[i][0])) return zmer('navigace', { misto: NAVIGACE[i][1] });
    }
  });

  // Mimo lištu: instalaci z menu prohlížeče lišta nevidí.
  window.addEventListener('appinstalled', function () { zmer('appka_instalace'); });

  /* Sdílení. Nainstalovaná appka nemá adresní řádek ani menu prohlížeče,
   * takže bez tohohle tlačítka se z ní nedá poslat odkaz vůbec.
   *
   * Telefon otevře vlastní sdílecí nabídku (navigator.share). Kde ji
   * prohlížeč nemá, tlačítko odkaz zkopíruje. Kde neumí ani to, zůstane
   * skryté. U víkendové karty se posílá rovnou obrázek, pokud to systém
   * dovolí; jinak adresa stránky víkendu.
   *
   * Obrázek se stahuje předem, ne až po klepnutí: Safari povolí sdílení
   * jen bezprostředně po klepnutí a čekání na síť by ho shodilo.
   */
  var umiSdilet = typeof navigator.share === 'function';
  var umiSchranku = !!(navigator.clipboard && window.isSecureContext);
  var umiKopirovat = umiSchranku || !!(document.queryCommandSupported
    && document.queryCommandSupported('copy'));

  // GA4 doporučená událost share; zmer() je nahoře u ostatních událostí.
  function zmerSdileni(tl, zpusob) {
    zmer('share', {
      method: zpusob,
      content_type: tl.dataset.druh,
      item_id: new URL(tl.dataset.url).pathname
    });
  }

  function napis(tl, text) {
    var popisek = tl.querySelector('span');
    var puvodni = popisek.textContent;
    popisek.textContent = text;
    setTimeout(function () { popisek.textContent = puvodni; }, 2500);
  }

  // Starý způsob přes skryté pole. Vestavěné prohlížeče aplikací (Instagram,
  // Messenger) schránku často nepustí, tohle ano.
  function kopirujPolem(text) {
    var pole = document.createElement('textarea');
    pole.value = text;
    pole.setAttribute('readonly', '');
    pole.style.position = 'fixed';
    pole.style.opacity = '0';
    document.body.appendChild(pole);
    pole.select();
    var vyslo = false;
    try { vyslo = document.execCommand('copy'); } catch (e) {}
    pole.remove();
    return vyslo;
  }

  function kopiruj(tl) {
    function hotovo() {
      napis(tl, 'Link máš zkopírovaný');
      zmerSdileni(tl, 'kopie');
    }
    function zaloha() {
      if (kopirujPolem(tl.dataset.url)) hotovo();
      else napis(tl, 'Nezkopírovalo se');
    }
    if (umiSchranku) navigator.clipboard.writeText(tl.dataset.url).then(hotovo, zaloha);
    else zaloha();
  }

  if (umiSdilet || umiKopirovat) {
    Array.prototype.forEach.call(document.querySelectorAll('.sdilet'), function (tl) {
      var obrazek = null;
      // Tři sekundy po načtení stránky: 120 kB obrázku jinak na pomalé síti
      // zdrží vykreslení obsahu (Lighthouse: LCP víkendu 2,0 → 2,5 s, a to
      // i se stahováním hned po load). Kdo klepne dřív, pošle odkaz.
      function pripravObrazek() {
        fetch(tl.dataset.soubor).then(function (r) {
          return r.ok ? r.blob() : null;
        }).then(function (data) {
          if (!data) return;
          var soubor = new File([data], tl.dataset.nazev || 'kromcl.png',
            { type: data.type || 'image/png' });
          if (navigator.canShare({ files: [soubor] })) {
            obrazek = soubor;
            tl.querySelector('span').textContent = 'Šérni do storíčka';
          }
        }).catch(function () {});
      }
      if (umiSdilet && tl.dataset.soubor && typeof navigator.canShare === 'function'
          && typeof File === 'function') {
        var pozdeji = function () { setTimeout(pripravObrazek, 3000); };
        if (document.readyState === 'complete') pozdeji();
        else window.addEventListener('load', pozdeji);
      }

      tl.addEventListener('click', function () {
        if (!umiSdilet) { kopiruj(tl); return; }
        var co = obrazek
          ? { files: [obrazek], title: tl.dataset.titulek }
          : { title: tl.dataset.titulek, url: tl.dataset.url };
        navigator.share(co).then(function () {
          zmerSdileni(tl, obrazek ? 'obrazek' : 'nabidka');
        }, function (chyba) {
          // Zavřená nabídka není chyba. Jiné selhání (třeba Windows bez
          // cílů sdílení) dorovná kopie odkazu.
          if (chyba && chyba.name !== 'AbortError' && umiKopirovat) kopiruj(tl);
        });
      });
      tl.hidden = false;
    });
  }

  /* Core Web Vitals skutečných návštěvníků do GA4. Laboratorní měření
   * (Lighthouse) je odhad; Google vlastní data o malém webu nemusí mít
   * nikdy, protože potřebuje dost návštěv.
   *
   * Knihovna web-vitals (static/vendor/, Apache-2.0) se stáhne jen tam, kde
   * měří gtag, a až po načtení stránky, ať nesoupeří o síť s obsahem.
   * Co se stalo dřív, si dočte z vyrovnávací paměti prohlížeče.
   * debug_target je selektor prvku, který hodnotu způsobil (největší prvek,
   * posunutý prvek, prvek interakce), aby šlo z dat poznat, co opravit.
   */
  function posliVitals(m) {
    var a = m.attribution || {};
    zmer(m.name, {
      value: m.delta,
      metric_id: m.id,
      metric_value: m.value,
      metric_rating: m.rating,
      debug_target: (a.target || a.largestShiftTarget || a.interactionTarget || '').slice(0, 100)
    });
  }

  function nactiVitals() {
    var s = document.createElement('script');
    s.src = '/vendor/web-vitals.js';
    s.onload = function () {
      window.webVitals.onLCP(posliVitals);
      window.webVitals.onCLS(posliVitals);
      window.webVitals.onINP(posliVitals);
    };
    document.head.appendChild(s);
  }

  if (window.gtag) {
    if (document.readyState === 'complete') nactiVitals();
    else window.addEventListener('load', nactiVitals);
  }

  var jeAppka = window.matchMedia('(display-mode: standalone)').matches
    || window.navigator.standalone === true;
  if (jeAppka) return;

  var KLIC = 'kromka-instalace';
  var MESIC = 30 * 24 * 3600 * 1000;
  var stav = {};
  try { stav = JSON.parse(localStorage.getItem(KLIC) || '{}'); } catch (e) {}
  function uloz() {
    try { localStorage.setItem(KLIC, JSON.stringify(stav)); } catch (e) {}
  }

  stav.stranek = (stav.stranek || 0) + 1;
  uloz();

  var odmitnuto = stav.odmitnuto && Date.now() - stav.odmitnuto < MESIC;
  if (stav.nainstalovano || odmitnuto || stav.stranek < 2) return;

  var nazev = (document.querySelector('meta[name="application-name"]') || {}).content
    || document.title;
  var jeIos = /iPad|iPhone|iPod/.test(navigator.userAgent)
    || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

  function lista(text, tlacitka) {
    var el = document.createElement('div');
    el.className = 'instalace';
    el.setAttribute('role', 'region');
    el.setAttribute('aria-label', 'Instalace aplikace');
    var ikona = document.createElement('img');
    ikona.src = '/favicon.svg';
    ikona.alt = '';
    ikona.width = 40;
    ikona.height = 40;
    var p = document.createElement('p');
    var b = document.createElement('b');
    b.textContent = nazev + ' jako appka. ';
    p.appendChild(b);
    p.appendChild(document.createTextNode(text));
    var akce = document.createElement('div');
    akce.className = 'instalace-akce';
    tlacitka.forEach(function (t) { akce.appendChild(t); });
    el.appendChild(ikona);
    el.appendChild(p);
    el.appendChild(akce);
    document.body.appendChild(el);
    document.body.classList.add('s-instalaci');
    return el;
  }

  function tlacitko(text, hlavni, akce) {
    var t = document.createElement('button');
    t.type = 'button';
    t.className = hlavni ? 'instalace-hlavni' : 'instalace-vedlejsi';
    t.textContent = text;
    t.addEventListener('click', akce);
    return t;
  }

  function zavri(el, natrvalo) {
    el.remove();
    document.body.classList.remove('s-instalaci');
    if (natrvalo) { stav.odmitnuto = Date.now(); uloz(); }
  }

  window.addEventListener('appinstalled', function () {
    stav.nainstalovano = true;
    uloz();
    var el = document.querySelector('.instalace');
    if (el) zavri(el, false);
  });

  if (jeIos) {
    var iosLista = lista('Klepni dole na Sdílet a dej „Přidat na plochu“. '
      + 'Bez storu, bez reklam.', [
      tlacitko('Jasně', true, function () { zavri(iosLista, true); })
    ]);
    zmer('instalace_nabidka', { vysledek: 'ios_navod' });
    return;
  }

  window.addEventListener('beforeinstallprompt', function (udalost) {
    udalost.preventDefault();
    if (document.querySelector('.instalace')) return;
    var el = lista('Hoď si ho na plochu a máš Kroměříž na jedno ťuknutí. '
      + 'Bez storu, bez reklam.', [
      tlacitko('Přidat na plochu', true, function () {
        udalost.prompt();
        udalost.userChoice.then(function (volba) {
          zmer('instalace_nabidka', {
            vysledek: volba.outcome === 'accepted' ? 'prijato' : 'odmitnuto'
          });
          zavri(el, volba.outcome !== 'accepted');
        });
      }),
      tlacitko('Teď ne', false, function () {
        zmer('instalace_nabidka', { vysledek: 'ted_ne' });
        zavri(el, true);
      })
    ]);
    zmer('instalace_nabidka', { vysledek: 'zobrazeno' });
  });
})();
