/**
 * Příspěvky čtenářů KROMCL: založení formuláře a endpoint pro cron
 * (kromka/prispevky.py). Samostatný projekt na script.google.com.
 *
 * Jednou: spustit `zalozit()`. Založí Google Form s otázkami, tabulku
 * odpovědí se sloupci pro redakci, upozornění e-mailem a klíč endpointu.
 * Do protokolu vypíše adresy a klíč. Formulář zůstane nezveřejněný, dokud
 * se nespustí `zverejnit()`.
 *
 * Pak: Nasadit → Nová implementace → Webová aplikace, spouštět jako já,
 * přístup Kdokoli. Adresu a klíč do repo secrets KROMKA_PRISPEVKY_URL a
 * KROMKA_PRISPEVKY_KLIC, adresu formuláře pro vložení do proměnné
 * KROMKA_PRISPEVKY_FORMULAR.
 *
 * Bez klíče endpoint nic nevrátí. A ani s klíčem nevrátí e-mail: ten je
 * v tabulce jen pro redakci a do veřejného repa nesmí.
 *
 * Akce (POST, tělo JSON):
 *   {klic, akce: "nacti"}  → {ok, radky: [{id, cas, jmeno, nadpis, text, odkaz, stav}]}
 *                            jen řádky ve stavu „schváleno" a „stáhnout"
 *   {klic, akce: "stav", id, stav, odkaz, poznamka} → {ok}
 *   {akce: "odeslat", jmeno, email, nadpis, text, odkaz, souhlas, web, trvani}
 *                          → {ok} nebo {ok: false, chyba, pole}
 *                            bez klíče: posílá ho formulář na kromcl.cz
 *
 * Odeslání zapíše odpověď do Google Formu, takže tabulka i upozornění jedou
 * stejně jako při vyplnění formuláře u Googlu. Odpověď Apps Scriptu se dá
 * z cizí stránky přečíst (na rozdíl od formResponse Googlu), a web tak
 * hlásí skutečný výsledek, ne „odesláno" naslepo.
 */

var UPOZORNENI = 'zdenek@linki.cz';

// Otázky formuláře jsou zároveň názvy sloupců v tabulce. Přejmenování otázky
// přejmenuje sloupec, takže se musí změnit i tady. Časová značka je vždy
// první sloupec; její název závisí na jazyku tabulky, proto se hledá pozicí.
var OTAZKY = {
  jmeno: 'Jméno',
  email: 'E-mail',
  nadpis: 'Nadpis',
  text: 'Text',
  odkaz: 'Odkaz',
  souhlas: 'Souhlas'
};
var REDAKCE = { stav: 'Stav', clanek: 'Odkaz na článek', poznamka: 'Poznámka' };

// Všechny hodnoty sloupce Stav, i ty, které zapisuje cron. Rozbalovací
// seznam jiné neprověří a zápis z cronu by spadl. „akce" a „akce odeslána"
// píše redakce a skill /pridat-akci; endpoint je nevrací, cron je nevidí.
var STAVY = ['schváleno', 'zamítnuto', 'stáhnout', 'publikováno', 'chyba', 'staženo',
  'akce', 'akce odeslána'];
var KE_ZPRACOVANI = ['schváleno', 'stáhnout'];

var SOUHLAS = 'Souhlasím, že KROMCL můj text přepíše a zveřejní na kromcl.cz ' +
  'pod mým jménem. Píšu jen to, co vím z první ruky, a nikoho nepomlouvám. ' +
  'E-mail slouží jen redakci pro doplňující otázky.';

// --- Založení ---------------------------------------------------------------

function zalozit() {
  var vlastnosti = PropertiesService.getScriptProperties();
  if (vlastnosti.getProperty('FORMULAR_ID')) {
    throw new Error('Formulář už existuje: ' + vlastnosti.getProperty('FORMULAR_ID') +
      '. Znovu se nezakládá, aby nevznikly dva.');
  }

  var form = FormApp.create('KROMCL – pošli novinku');
  form.setDescription('Víš o něčem, co se v Kroměříži děje? Napiš nám to. ' +
    'Redakce si to přečte, a když to projde, napíšeme to po svém a vyjde to ' +
    'na kromcl.cz pod tvým jménem.');
  form.setConfirmationMessage('Díky! Redakce si to přečte. Když to projde, ' +
    'najdeš to na kromcl.cz pod svým jménem.');
  form.setCollectEmail(false);
  form.setAllowResponseEdits(false);
  form.setShowLinkToRespondAgain(true);
  form.setProgressBar(false);
  try {
    // Ve Workspace bývá formulář jen pro lidi z domény. Čtenáři přihlášení nejsou.
    form.setRequireLogin(false);
  } catch (chyba) {
    Logger.log('setRequireLogin nejde (' + chyba + '), zkontrolovat ručně v Nastavení.');
  }

  form.addTextItem().setTitle(OTAZKY.jmeno)
    .setHelpText('Ukáže se pod článkem.').setRequired(true)
    .setValidation(FormApp.createTextValidation()
      .requireTextLengthLessThanOrEqualTo(80).build());
  form.addTextItem().setTitle(OTAZKY.email)
    .setHelpText('Jen pro redakci, kdyby se potřebovala doptat. Na web nejde.')
    .setRequired(true)
    .setValidation(FormApp.createTextValidation().requireTextIsEmail().build());
  form.addTextItem().setTitle(OTAZKY.nadpis)
    .setHelpText('O čem to je, jednou větou.').setRequired(true)
    .setValidation(FormApp.createTextValidation()
      .requireTextLengthLessThanOrEqualTo(150).build());
  form.addParagraphTextItem().setTitle(OTAZKY.text)
    .setHelpText('Co, kdo, kdy, kde. Přepíšeme to do našeho jazyka a nic nepřidáme.')
    .setRequired(true)
    .setValidation(FormApp.createParagraphTextValidation()
      .requireTextLengthLessThanOrEqualTo(6000).build());
  form.addTextItem().setTitle(OTAZKY.odkaz)
    .setHelpText('Nepovinné. Web spolku, příspěvek na sítích, kde se dá zjistit víc.')
    .setValidation(FormApp.createTextValidation().requireTextIsUrl().build());
  var souhlas = form.addCheckboxItem().setTitle(OTAZKY.souhlas).setRequired(true);
  souhlas.setChoices([souhlas.createChoice(SOUHLAS)]);

  var tabulka = SpreadsheetApp.create('KROMCL – příspěvky čtenářů');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, tabulka.getId());
  SpreadsheetApp.flush();

  var list = listOdpovedi_(tabulka.getId(), form.getId());
  pripravSloupce_(list);
  tabulka.getSheets().forEach(function (jiny) {
    if (jiny.getSheetId() !== list.getSheetId() && jiny.getLastRow() === 0) {
      tabulka.deleteSheet(jiny);
    }
  });

  ScriptApp.newTrigger('upozornit').forForm(form).onFormSubmit().create();

  var klic = Utilities.getUuid().replace(/-/g, '') + Utilities.getUuid().replace(/-/g, '');
  vlastnosti.setProperties({
    FORMULAR_ID: form.getId(),
    TABULKA_ID: tabulka.getId(),
    KLIC: klic
  });

  Logger.log('Formulář (úprava): ' + form.getEditUrl());
  Logger.log('Formulář (pro čtenáře): ' + form.getPublishedUrl());
  Logger.log('KROMKA_PRISPEVKY_FORMULAR=' + form.getPublishedUrl() + '?embedded=true');
  Logger.log('Tabulka: ' + tabulka.getUrl());
  Logger.log('KROMKA_PRISPEVKY_KLIC=' + klic);
}

function zverejnit() {
  var form = FormApp.openById(vlastnost_('FORMULAR_ID'));
  form.setPublished(true);
  form.setAcceptingResponses(true);
  Logger.log('Zveřejněno: ' + form.isPublished() + ', přijímá odpovědi: ' +
    form.isAcceptingResponses());
}

function pripravSloupce_(list) {
  // Formulář zapíše hlavičku sám, ale až s první odpovědí nebo po chvíli.
  var hlavicka = list.getRange(1, 1, 1, Math.max(list.getLastColumn(), 1)).getValues()[0];
  if (hlavicka.indexOf(OTAZKY.text) < 0) {
    throw new Error('Tabulka ještě nemá hlavičku z formuláře. Spustit pripravSloupce() za minutu.');
  }
  var od = hlavicka.length + 1;
  var nove = [REDAKCE.stav, REDAKCE.clanek, REDAKCE.poznamka]
    .filter(function (n) { return hlavicka.indexOf(n) < 0; });
  if (nove.length) list.getRange(1, od, 1, nove.length).setValues([nove]);

  var sloupce = sloupce_(list.getRange(1, 1, 1, list.getLastColumn()).getValues()[0]);
  var pravidlo = SpreadsheetApp.newDataValidation()
    .requireValueInList(STAVY, true).setAllowInvalid(false).build();
  list.getRange(2, sloupce.stav + 1, list.getMaxRows() - 1, 1).setDataValidation(pravidlo);
  list.setFrozenRows(1);
  list.getRange(1, 1, 1, list.getLastColumn()).setFontWeight('bold');
}

/** Ruční záchrana, když při založení hlavička ještě nebyla. */
function pripravSloupce() {
  pripravSloupce_(listOdpovedi_(vlastnost_('TABULKA_ID'), vlastnost_('FORMULAR_ID')));
}

// --- Upozornění -------------------------------------------------------------

function upozornit(e) {
  var odpovedi = {};
  e.response.getItemResponses().forEach(function (r) {
    odpovedi[r.getItem().getTitle()] = r.getResponse();
  });
  MailApp.sendEmail({
    to: UPOZORNENI,
    subject: 'KROMCL: nový příspěvek – ' + (odpovedi[OTAZKY.nadpis] || ''),
    body: 'Od: ' + (odpovedi[OTAZKY.jmeno] || '') + ' (' + (odpovedi[OTAZKY.email] || '') + ')\n\n' +
      (odpovedi[OTAZKY.nadpis] || '') + '\n\n' + (odpovedi[OTAZKY.text] || '') + '\n\n' +
      (odpovedi[OTAZKY.odkaz] ? 'Odkaz: ' + odpovedi[OTAZKY.odkaz] + '\n\n' : '') +
      'Schválit: ' + SpreadsheetApp.openById(vlastnost_('TABULKA_ID')).getUrl()
  });
}

// --- Endpoint ---------------------------------------------------------------

function doPost(e) {
  var vstup;
  try {
    vstup = JSON.parse(e.postData.contents);
  } catch (chyba) {
    return odpoved_({ ok: false, chyba: 'neplatný JSON' });
  }
  if (vstup.akce === 'odeslat') return odpoved_(odeslat_(vstup));

  var klic = PropertiesService.getScriptProperties().getProperty('KLIC');
  if (!klic || vstup.klic !== klic) return odpoved_({ ok: false, chyba: 'klíč' });

  if (vstup.akce === 'nacti') return odpoved_({ ok: true, radky: nacti_() });
  if (vstup.akce === 'stav') return odpoved_(zapisStav_(vstup));
  return odpoved_({ ok: false, chyba: 'neznámá akce' });
}

// Víc odeslání za hodinu od všech dohromady KROMCL nedostane; víc by znamenalo
// robota. Strop zároveň drží v mezích denní kvótu e-mailů s upozorněním.
var STROP_ZA_HODINU = 30;
// Člověk formulář nevyplní za tři sekundy, robot ano.
var NEJKRATSI_VYPLNENI_MS = 3000;

function odeslat_(v) {
  // Skryté pole „web" vyplní jen robot. Tváříme se, že prošlo, ať to nezkouší jinak.
  if (v.web) return { ok: true };
  if (!(Number(v.trvani) >= NEJKRATSI_VYPLNENI_MS)) {
    return { ok: false, chyba: 'Tohle bylo moc rychlé. Zkus to prosím znovu.' };
  }

  var hodnoty = {
    jmeno: String(v.jmeno || '').trim(),
    email: String(v.email || '').trim(),
    nadpis: String(v.nadpis || '').trim(),
    text: String(v.text || '').trim(),
    odkaz: String(v.odkaz || '').trim()
  };
  var pole = {};
  if (!hodnoty.jmeno) pole.jmeno = 'Napiš jméno, ukáže se pod článkem.';
  else if (hodnoty.jmeno.length > 80) pole.jmeno = 'Jméno může mít nejvýš 80 znaků.';
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(hodnoty.email)) pole.email = 'Tohle nevypadá jako e-mail.';
  if (!hodnoty.nadpis) pole.nadpis = 'O čem to je? Stačí jedna věta.';
  else if (hodnoty.nadpis.length > 150) pole.nadpis = 'Nadpis může mít nejvýš 150 znaků.';
  if (!hodnoty.text) pole.text = 'Napiš, co se děje.';
  else if (hodnoty.text.length > 6000) pole.text = 'Text může mít nejvýš 6000 znaků.';
  if (hodnoty.odkaz && !/^https?:\/\/\S+$/i.test(hodnoty.odkaz)) {
    pole.odkaz = 'Odkaz musí začínat https://';
  }
  if (v.souhlas !== true) pole.souhlas = 'Bez souhlasu to zveřejnit nemůžeme.';
  if (Object.keys(pole).length) {
    return { ok: false, chyba: 'Něco ještě chybí, mrkni na označená pole.', pole: pole };
  }

  var mezipamet = CacheService.getScriptCache();
  var hodina = 'odeslano-' + Utilities.formatDate(new Date(), 'Etc/UTC', 'yyyyMMddHH');
  var zamek = LockService.getScriptLock();
  zamek.waitLock(10000);
  try {
    var pocet = Number(mezipamet.get(hodina) || 0);
    if (pocet >= STROP_ZA_HODINU) {
      return { ok: false, chyba: 'Teď toho chodí moc najednou. Zkus to prosím za hodinu.' };
    }
    mezipamet.put(hodina, String(pocet + 1), 3700);
  } finally {
    zamek.releaseLock();
  }

  var form = FormApp.openById(vlastnost_('FORMULAR_ID'));
  var odpoved = form.createResponse();
  var podle = {};
  podle[OTAZKY.jmeno] = hodnoty.jmeno;
  podle[OTAZKY.email] = hodnoty.email;
  podle[OTAZKY.nadpis] = hodnoty.nadpis;
  podle[OTAZKY.text] = hodnoty.text;
  podle[OTAZKY.odkaz] = hodnoty.odkaz;
  form.getItems().forEach(function (polozka) {
    var nazev = polozka.getTitle();
    if (nazev === OTAZKY.souhlas) {
      odpoved.withItemResponse(polozka.asCheckboxItem().createResponse([SOUHLAS]));
    } else if (polozka.getType() === FormApp.ItemType.PARAGRAPH_TEXT && podle[nazev]) {
      odpoved.withItemResponse(polozka.asParagraphTextItem().createResponse(podle[nazev]));
    } else if (polozka.getType() === FormApp.ItemType.TEXT && podle[nazev]) {
      odpoved.withItemResponse(polozka.asTextItem().createResponse(podle[nazev]));
    }
  });
  odpoved.submit();
  return { ok: true };
}

function vlastnost_(nazev) {
  var hodnota = PropertiesService.getScriptProperties().getProperty(nazev);
  if (!hodnota) throw new Error('Chybí vlastnost ' + nazev + ', nejdřív spustit zalozit().');
  return hodnota;
}

function listOdpovedi_(tabulkaId, formularId) {
  var tabulka = SpreadsheetApp.openById(tabulkaId);
  var listy = tabulka.getSheets();
  for (var i = 0; i < listy.length; i++) {
    var adresa = listy[i].getFormUrl();
    if (adresa && adresa.indexOf(formularId) >= 0) return listy[i];
  }
  // Starší vazba adresu formuláře nemusí nést; odpovědi jsou pak na prvním listu.
  return listy[0];
}

function list_() {
  return listOdpovedi_(vlastnost_('TABULKA_ID'), vlastnost_('FORMULAR_ID'));
}

function sloupce_(hlavicka) {
  var index = { cas: 0 };
  var nazvy = {
    jmeno: OTAZKY.jmeno, nadpis: OTAZKY.nadpis, text: OTAZKY.text, odkaz: OTAZKY.odkaz,
    stav: REDAKCE.stav, clanek: REDAKCE.clanek, poznamka: REDAKCE.poznamka
  };
  Object.keys(nazvy).forEach(function (k) {
    index[k] = hlavicka.indexOf(nazvy[k]);
    if (index[k] < 0) throw new Error('Chybí sloupec ' + nazvy[k]);
  });
  return index;
}

function idRadku_(cas) {
  // Časová značka odpovědi je stabilní i po seřazení tabulky, číslo řádku ne.
  return Utilities.formatDate(new Date(cas), 'Etc/UTC', "yyyy-MM-dd'T'HH:mm:ss'Z'");
}

function nacti_() {
  var data = list_().getDataRange().getValues();
  var s = sloupce_(data[0]);
  var radky = [];
  for (var i = 1; i < data.length; i++) {
    var r = data[i];
    var stav = String(r[s.stav]).trim().toLowerCase();
    if (!r[s.cas] || KE_ZPRACOVANI.indexOf(stav) < 0) continue;
    radky.push({
      id: idRadku_(r[s.cas]),
      cas: idRadku_(r[s.cas]),
      jmeno: String(r[s.jmeno]),
      nadpis: String(r[s.nadpis]),
      text: String(r[s.text]),
      odkaz: String(r[s.odkaz]),
      stav: stav
    });
  }
  return radky;
}

function zapisStav_(vstup) {
  var zamek = LockService.getScriptLock();
  zamek.waitLock(10000);
  try {
    var list = list_();
    var data = list.getDataRange().getValues();
    var s = sloupce_(data[0]);
    for (var i = 1; i < data.length; i++) {
      if (!data[i][s.cas] || idRadku_(data[i][s.cas]) !== vstup.id) continue;
      list.getRange(i + 1, s.stav + 1).setValue(vstup.stav || '');
      if (vstup.odkaz) list.getRange(i + 1, s.clanek + 1).setValue(vstup.odkaz);
      list.getRange(i + 1, s.poznamka + 1).setValue(vstup.poznamka || '');
      return { ok: true };
    }
    return { ok: false, chyba: 'řádek nenalezen' };
  } finally {
    zamek.releaseLock();
  }
}

function odpoved_(data) {
  return ContentService.createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}
