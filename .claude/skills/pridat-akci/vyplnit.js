// Vyplní formulář opendata.mesto-kromeriz.cz/formular. Nic neodesílá.
//
// Použití přes javascript_tool: celý obsah souboru a za ním jeden řádek
//   vyplnAkci({...pole akce...})
// nebo vyplnAkci({...}, {bezDiakritiky: true}) pro záložní verzi.
// Klíče objektu jsou názvy polí formuláře bez obalu newaction[...],
// mapa i povolené hodnoty jsou v SKILL.md.
//
// Vrací hlášení jako text. Adresy v něm schválně nejsou: odpověď
// s adresou nebo dotazem v URL nástroj zablokuje.

function bezHacku(s) {
  return String(s)
    .replace(/[–—]/g, '-').replace(/[„“”]/g, '"').replace(/[‚‘’]/g, "'")
    .replace(/…/g, '...').replace(/ /g, ' ')
    .normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/[^\x00-\x7F]/g, '');
}

function vyplnAkci(akce, volby) {
  volby = volby || {};
  var $ = window.jQuery, hlaseni = [], chyby = [];
  var txt = function (s) { return volby.bezDiakritiky ? bezHacku(s || '') : (s || ''); };
  var pole = function (n) { return document.querySelector('[name="newaction[' + n + ']"]'); };
  var nastav = function (n, v) {
    var e = pole(n);
    if (!e) { chyby.push('pole ' + n + ' na stránce není'); return; }
    e.value = v;
    e.dispatchEvent(new Event('input', { bubbles: true }));
    $(e).trigger('change');
  };
  var zaskrtni = function (n, v) {
    var e = document.querySelector('input[name="newaction[' + n + ']"][value="' + v + '"]');
    if (!e) { chyby.push(n + '=' + v + ' není mezi možnostmi'); return; }
    e.click();
  };

  ['label', 'perex', 'cal_note', 'price_note', 'owner_name', 'owner_message']
    .forEach(function (n) { nastav(n, txt(akce[n])); });
  // Adresy, e-mail, telefon a cena se nepřepisují bez háčků, nemají je.
  ['price', 'event_ticket_url', 'web', 'fb', 'youtube', 'owner_email', 'owner_phone']
    .forEach(function (n) { nastav(n, akce[n] || ''); });

  // Popis je editor Trumbowyg; textarea pod ním se plní jen přes jeho API.
  $(pole('text')).trumbowyg('html', txt(akce.text));

  // Kalendář je jen pro čtení, hodnota se zapisuje přímo. Tvar 01.11.2026 19:00.
  ['cal_from', 'cal_to'].forEach(function (n) {
    if (!/^\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}$/.test(akce[n] || '')) chyby.push(n + ' není ve tvaru DD.MM.RRRR HH:MM');
    var e = pole(n); e.value = akce[n] || ''; $(e).trigger('change');
  });

  nastav('type', String(akce.type || ''));
  zaskrtni('for_kids', akce.for_kids === '1' ? '1' : '0');
  zaskrtni('is_price', akce.is_price === '0' ? '0' : '1');
  zaskrtni('accessible_from', akce.accessible_from || '0');
  zaskrtni('appropriate_from', akce.appropriate_from || '0');

  // Místo: buď id z číselníku, nebo přesný název z něj, jinak „Jiné místo".
  var vyber = pole('place_id'), prepinac = document.querySelectorAll('input[name="place"]');
  var id = String(akce.place_id || '');
  if (!id && akce.place_name) {
    var hledane = akce.place_name.trim().toLowerCase();
    var shoda = [].slice.call(vyber.options).filter(function (o) {
      return o.text.trim().toLowerCase() === hledane && !/zrušeno/i.test(o.text);
    })[0];
    if (shoda) id = shoda.value;
  }
  if (id && id !== '0') {
    prepinac[0].click(); nastav('place_id', id);
    var misto = vyber.options[vyber.selectedIndex];
    if (!misto || misto.value !== id) chyby.push('místo s id ' + id + ' v číselníku není');
    hlaseni.push('místo ze seznamu: ' + (misto ? misto.text : '(nevybráno)'));
  } else {
    prepinac[1].click(); nastav('place_note', txt(akce.place_note || akce.place_name));
    hlaseni.push('jiné místo: ' + pole('place_note').value);
  }

  // Kontrola povinných polí tak, jak je chce formulář.
  ['label', 'perex', 'text', 'cal_from', 'cal_to', 'owner_email'].forEach(function (n) {
    if (!pole(n).value.trim()) chyby.push('povinné pole ' + n + ' je prázdné');
  });
  if (!pole('type').value || pole('type').value === '0') chyby.push('chybí typ akce');
  if (akce.is_price !== '0' && !pole('price').value.trim()) chyby.push('vstup není zdarma, ale chybí cena');

  hlaseni.push('název: ' + pole('label').value);
  hlaseni.push('termín: ' + pole('cal_from').value + ' až ' + pole('cal_to').value);
  var typ = pole('type').options[pole('type').selectedIndex];
  hlaseni.push('typ: ' + (typ ? typ.text : '(nevybrán)'));
  if (volby.bezDiakritiky) hlaseni.push('VERZE BEZ DIAKRITIKY');
  return (chyby.length ? 'CHYBY:\n- ' + chyby.join('\n- ') + '\n' : 'bez chyb\n') + hlaseni.join('\n');
}
