/* KROMCL jako appka: registrace service workeru a výzva k instalaci.
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
          zavri(el, volba.outcome !== 'accepted');
        });
      }),
      tlacitko('Teď ne', false, function () { zavri(el, true); })
    ]);
  });
})();
