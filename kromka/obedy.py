# -*- coding: utf-8 -*-
"""Polední menu z vlastních webů kroměřížských podniků.

Záměrně **mimo `sources/`**, ze stejného důvodu jako `akce.py`: registr
zdrojů posílá každou položku do přepisu modelem. Menu se nepřepisuje —
názvy jídel a ceny jdou na web tak, jak je podnik napsal.

Meníčka.cz jako zdroj nejdou: v patičce mají „Užití obsahu je bez souhlasu
provozovatele zakázáno" a výpis je jejich placená databáze. Podnik, který má
na svém webu jen jejich rámeček, sem proto nepatří — byl by to pořád obsah
Meníček. Průzkum 34 podniků z 5. 11. 2026 je v README.

Hlavní pravidlo: **včerejší menu se nikdy neukáže jako dnešní.** Stránky
s datem se berou jen v den, který na nich stojí. Sladovna datum nepíše, tam
se menu bere jen staženo dnes, a když je stejné jako menu z dřívějšího dne,
bere se, že ho ještě nepřepsali.

Jako u `kino_dk.py`: rozbitá stránka vrátí prázdno a nikdy nevyhodí výjimku,
build se musí postavit i bez obědů.
"""

import hashlib
import html
import json
import re
import sys
from datetime import date, datetime, timezone

from . import config, net
from .akce import ted

# Pořadí na stránce je abecední, ať žádný podnik není „první" z naší vůle.
PODNIKY = [
    {"id": "beer-bowl", "nazev": "Beer & Bowl",
     "web": "https://www.bowlingkm.cz/",
     "menu": "https://www.bowlingkm.cz/menu-jidelni-listek/poledni",
     "parser": "dmenu"},
    {"id": "earnest", "nazev": "Earnest",
     "web": "https://restaurace.earnest.cz/",
     "menu": "https://restaurace.earnest.cz/poledni-menu",
     "parser": "dmenu"},
    {"id": "kozlovna-oskol", "nazev": "Kozlovna Oskol",
     "web": "https://www.kozlovnaoskol.cz/",
     "menu": "https://www.kozlovnaoskol.cz/denni-nabidka/",
     "parser": "oskol"},
    {"id": "nova-bohemia", "nazev": "Nová Bohemia",
     "web": "https://www.novabohemia-restaurace.cz/",
     "menu": "https://www.novabohemia-restaurace.cz/",
     "parser": "bohemia"},
    {"id": "sladovna", "nazev": "Restaurace Sladovna",
     "web": "https://www.restauracesladovnakm.cz/",
     "menu": "https://www.restauracesladovnakm.cz/obedove-menu",
     "parser": "sladovna"},
]

DNY = ("PONDĚLÍ", "ÚTERÝ", "STŘEDA", "ČTVRTEK", "PÁTEK", "SOBOTA", "NEDĚLE")

_DATUM = re.compile(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})")
# Cena na konci řádku: „139 Kč", „159", „20Kč", „170,-", „Kč 65,-". Gramáž
# („160 g") končí písmenem, takže se za cenu nepovažuje. Holé číslo bez Kč
# nejvýš trojmístné a ne za tečkou, jinak by „HUSÍ HODY 6.-11.11.2026" stálo
# 2026 Kč.
_CENA = re.compile(r"\s*(?:Kč\s*)?(?:(\d{2,4})\s*(?:,-|,–|Kč\.?)|(?<![\d.,])(\d{2,3}))\s*$")
_CISLOVANI = re.compile(r"^\d{1,2}\.\s*")


# Značky uvnitř řádku textu. Mezera místo nich by z „(<a>1a</a>)" udělala
# „( 1a )" a z „<strong>…</strong><span>, …" čárku odraženou mezerou.
_INLINE = re.compile(r"</?(?:a|span|strong|b|em|i|u|font|small|sup|sub)\b[^>]*>", re.I)


def _bez_znacek(kus):
    """Komentáře (i zakomentované „více" a značky Svelte) a inline značky pryč,
    ostatní značky na mezeru."""
    kus = re.sub(r"(?s)<!--.*?-->", "", kus)
    kus = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", kus)
    return _INLINE.sub("", kus)


def _cisty(kus):
    """Vnitřek značky na holý text na jednom řádku."""
    text = html.unescape(re.sub(r"<[^>]+>", " ", _bez_znacek(kus))).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _radky(kus):
    """HTML na řádky textu tam, kde je na stránce vidět zalomení."""
    kus = re.sub(r"(?i)<br\s*/?>|</(p|div|h[1-6]|li|tr)>", "\n", _bez_znacek(kus))
    radky = []
    for radek in html.unescape(re.sub(r"<[^>]+>", " ", kus)).split("\n"):
        radek = re.sub(r"\s+", " ", radek.replace("\xa0", " ")).strip()
        if radek:
            radky.append(radek)
    return radky


def _s_cenou(text):
    """(text bez ceny, cena jako int nebo None)."""
    shoda = _CENA.search(text)
    if not shoda:
        return text.strip(), None
    return text[:shoda.start()].strip(), int(shoda.group(1) or shoda.group(2))


def _datum(text):
    shoda = _DATUM.search(text)
    if not shoda:
        return None
    try:
        return date(int(shoda.group(3)), int(shoda.group(2)), int(shoda.group(1)))
    except ValueError:
        return None


def _den_v_tydnu(radek):
    """Index dne, když řádek začíná jeho jménem („ČTVRTEK 5. 11."), jinak None."""
    slovo = radek.split(" ")[0].upper().rstrip(":-–")
    return DNY.index(slovo) if slovo in DNY else None


def _menu(polevky=(), jidla=(), poznamky=()):
    """Jednotný tvar. Bez jediného jídla to menu není."""
    if not jidla:
        return {}
    return {"polevky": list(polevky), "jidla": list(jidla), "poznamky": list(poznamky)}


# --- Beer & Bowl a Earnest -------------------------------------------------
# Stejný redakční systém: <section id="dmenu">, den v <h2>, polévka
# v <p class="polevky">, jídla v tabulce s td.jidlo a td.cena.

_DMENU = re.compile(r'<section[^>]+id="dmenu"[^>]*>(.*?)</section>', re.S | re.I)
_H2 = re.compile(r"<h2[^>]*>(.*?)</h2>", re.S | re.I)
_POLEVKY = re.compile(r'<p[^>]+class="polevky"[^>]*>(.*?)</p>', re.S | re.I)
_RADEK = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_JIDLO = re.compile(r'<td[^>]+class="jidlo"[^>]*>(.*?)</td>', re.S | re.I)
_TD_CENA = re.compile(r'<td[^>]+class="cena"[^>]*>(.*?)</td>', re.S | re.I)
_ALG = re.compile(r'<span[^>]+class="alg"[^>]*>(.*?)</span>', re.S | re.I)


def rozeber_dmenu(markup, dnes):
    sekce = _DMENU.search(markup)
    if not sekce:
        return {}
    kusy = _H2.split(sekce.group(1))
    # split se skupinou: [před, nadpis1, obsah1, nadpis2, obsah2, …]
    for i in range(1, len(kusy) - 1, 2):
        if _datum(_cisty(kusy[i])) != dnes:
            continue
        obsah = kusy[i + 1]
        polevky = []
        blok = _POLEVKY.search(obsah)
        if blok:
            vnitrek = re.sub(r'(?is)<span[^>]+class="soupnote".*?</span>|<a[^>]+class="[^"]*more[^"]*".*?</a>',
                             " ", blok.group(1))
            for radek in _radky(vnitrek):
                nazev, cena = _s_cenou(radek)
                if not nazev and cena is not None and polevky and polevky[-1]["cena"] is None:
                    polevky[-1]["cena"] = cena        # „Kč 65,-" na vlastním řádku
                elif nazev:
                    polevky.append({"nazev": nazev, "cena": cena})
        jidla = []
        for radek in _RADEK.findall(obsah):
            bunka = _JIDLO.search(radek)
            if not bunka:
                continue
            alg = _ALG.search(bunka.group(1))
            nazev = _cisty(_ALG.sub(" ", bunka.group(1)))
            cena = _s_cenou(_cisty(_TD_CENA.search(radek).group(1)))[1] if _TD_CENA.search(radek) else None
            jidlo = {"nazev": nazev, "cena": cena}
            if alg:
                jidlo["alergeny"] = re.sub(r"^Alergeny:\s*", "", _cisty(alg.group(1)))
            if nazev:
                jidla.append(jidlo)
        return _menu(polevky, jidla)
    return {}


# --- Kozlovna Oskol --------------------------------------------------------
# Webnode, celý týden pod sebou: „ČTVRTEK 5. 11. 2026", polévka s cenou,
# pak „1. … 139 Kč". Pátek tam někdy visí s datem minulého týdne — proto
# rozhoduje datum, ne jméno dne.

_OBSAH_WEBNODE = re.compile(r"<h1[^>]*>.*?</main>", re.S | re.I)


def rozeber_oskol(markup, dnes):
    obsah = _OBSAH_WEBNODE.search(markup)
    if not obsah:
        return {}
    polevky, jidla, poznamky = [], [], []
    v_dnesku = False
    for radek in _radky(obsah.group(0)):
        if _den_v_tydnu(radek) is not None:
            if v_dnesku:
                break
            v_dnesku = _datum(radek) == dnes
            continue
        if not v_dnesku:
            continue
        nazev, cena = _s_cenou(radek)
        if not nazev:
            continue
        if _CISLOVANI.match(nazev):
            jidla.append({"nazev": _CISLOVANI.sub("", nazev), "cena": cena})
        elif cena is not None and not jidla:
            polevky.append({"nazev": nazev, "cena": cena})
        elif re.search(r"\w", nazev):
            poznamky.append(radek)
    return _menu(polevky, jidla, poznamky)


# --- Nová Bohemia ----------------------------------------------------------
# Týden v jednom bloku: „2.-6.11.", jména dnů, pod nimi polévka a M1, a za
# „DALŠÍ NABÍDKA PO CELÝ TÝDEN" jídla M2–M5, která platí každý den.
# Řádky „ZDE VLOŽIT…" jsou šablona pro redakci, návštěvník je nevidí.

_TYDEN = re.compile(r"(\d{1,2})\.\s*(?:(\d{1,2})\.)?\s*[-–]\s*(\d{1,2})\.\s*(\d{1,2})\.")
_BLOK_BOHEMIA = re.compile(r'<div[^>]+id="week"[^>]*>(.*?)</section>', re.S | re.I)
_CELY_TYDEN = "DALŠÍ NABÍDKA PO CELÝ TÝDEN"


def _v_tydnu(radek, dnes):
    """True, když řádek nese rozsah týdne („2.-6.11.") a dnešek v něm leží."""
    shoda = _TYDEN.search(radek)
    if not shoda:
        return None
    od_d, od_m, do_d, do_m = shoda.groups()
    try:
        do = date(dnes.year, int(do_m), int(do_d))
        od = date(dnes.year, int(od_m or do_m), int(od_d))
    except ValueError:
        return False
    if od > do:                                       # přes Silvestra
        od = od.replace(year=od.year - 1)
    return od <= dnes <= do


def rozeber_bohemia(markup, dnes):
    blok = _BLOK_BOHEMIA.search(markup)
    if not blok:
        return {}
    radky = [r for r in _radky(blok.group(1))
             if "ZDE VLOŽIT" not in r.upper() and re.search(r"\w", r)]
    tyden = next((r for r in radky if _TYDEN.search(r)), None)
    if not tyden or not _v_tydnu(tyden, dnes):
        return {}
    polevky, jidla, poznamky = [], [], []
    rezim = None                                      # None / "den" / "tyden"
    for radek in radky:
        den = _den_v_tydnu(radek)
        if den is not None:
            rezim = "den" if den == dnes.weekday() else None
            continue
        if radek.upper().startswith(_CELY_TYDEN):
            rezim = "tyden"
            continue
        if rezim is None or radek == tyden:
            continue
        nazev, cena = _s_cenou(radek)
        if not nazev:
            continue
        if re.match(r"M\d+\s*:", nazev):
            jidla.append({"nazev": nazev, "cena": cena})
        elif cena is not None and rezim == "den" and not polevky:
            polevky.append({"nazev": nazev, "cena": cena})
        else:
            poznamky.append(radek)
    # Bez dnešního dne (sobota, svátek) jsou jídla M2–M5 sama o sobě
    # podezřelá: týdenní nabídka bez denní by mohla být z minulého týdne.
    if not any(_den_v_tydnu(r) == dnes.weekday() for r in radky):
        return {}
    return _menu(polevky, jidla, poznamky)


# --- Sladovna --------------------------------------------------------------
# SvelteKit vykreslený na serveru. Datum na stránce není ani v datech
# stránky (`info.date` je prázdné), proto pojistka otiskem v `aktualizuj`.

_SLADOVNA = re.compile(r"<h1[^>]*>\s*Polední menu\s*</h1>(.*?)</section>", re.S | re.I)
_H3 = re.compile(r"<h3[^>]*>(.*?)</h3>", re.S | re.I)
_SLADOVNA_RADEK = re.compile(r"<p[^>]*>(.*?)</p>\s*<span[^>]*>(.*?)</span>", re.S | re.I)
# Nápoje k menu nejsou oběd; ostatní sekce (hlavní chody, dezerty) ano.
_BEZ_SEKCI = ("nápoje",)


def rozeber_sladovna(markup, dnes=None):
    blok = _SLADOVNA.search(markup)
    if not blok:
        return {}
    kusy = _H3.split(blok.group(1))
    # Oznámení podniku („Dnes máme zavřeno…") stojí mezi nadpisem a menu.
    uvod = re.split(r'(?i)<a[^>]+href="/objednavka|<div', kusy[0])[0]
    poznamky = [_cisty(p) for p in re.findall(r"(?is)<p[^>]*>(.*?)</p>", uvod) if _cisty(p)]
    polevky, jidla = [], []
    for i in range(1, len(kusy) - 1, 2):
        sekce = _cisty(kusy[i]).lower()
        if sekce in _BEZ_SEKCI:
            continue
        for text, cena in _SLADOVNA_RADEK.findall(kusy[i + 1]):
            nazev = _CISLOVANI.sub("", _cisty(text))
            polozka = {"nazev": nazev, "cena": _s_cenou(_cisty(cena))[1]}
            if not nazev:
                continue
            (polevky if sekce.startswith("polév") else jidla).append(polozka)
    return _menu(polevky, jidla, poznamky)


PARSERY = {"dmenu": rozeber_dmenu, "oskol": rozeber_oskol,
           "bohemia": rozeber_bohemia, "sladovna": rozeber_sladovna}
# Stránky, které datum dne nepíšou a potřebují pojistku otiskem.
BEZ_DATA = {"sladovna"}


def rozeber(podnik, markup, dnes):
    """Dnešní menu podniku, nebo {}. Nikdy nevyhodí výjimku.

    Komentáře pryč dřív, než se hledá blok s menu: zakomentovaná část
    stránky („<!-- <div class=more-block>…") by jinak mohla vypadat jako
    živá a vyhrát.
    """
    try:
        markup = re.sub(r"(?s)<!--.*?-->", "", markup)
        return PARSERY[podnik["parser"]](markup, dnes)
    except Exception as exc:                          # noqa: BLE001
        print("  obědy: {0} se nerozebral ({1})".format(podnik["nazev"], exc),
              file=sys.stderr)
        return {}


def otisk(menu):
    return hashlib.sha1(json.dumps(menu, ensure_ascii=False, sort_keys=True)
                        .encode("utf-8")).hexdigest()[:16]


def _bez_data(zaznam, menu, dnes):
    """Pojistka pro stránku bez data: menu stejné jako z dřívějška není dnešní.

    Vrací (menu k zobrazení, otisk, odkdy otisk platí). Riziko je
    opačné: podnik, který dva dny po sobě vaří přesně totéž, druhý den
    vypadne. To je menší zlo než pondělní stránka s pátečním menu.
    """
    if not menu:
        return {}, zaznam.get("otisk", ""), zaznam.get("otisk_od", "")
    novy = otisk(menu)
    if novy == zaznam.get("otisk") and zaznam.get("otisk_od", "") < dnes.isoformat():
        return {}, novy, zaznam["otisk_od"]
    if novy == zaznam.get("otisk"):
        return menu, novy, zaznam["otisk_od"]
    return menu, novy, dnes.isoformat()


# --- Uložení ---------------------------------------------------------------

def nacti():
    try:
        data = json.loads(config.OBEDY_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"podniky": {}}
    data.setdefault("podniky", {})
    return data


def uloz(data):
    config.OBEDY_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.OBEDY_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")


def _stari_minut(zaznam):
    try:
        kdy = datetime.fromisoformat(zaznam.get("stazeno", ""))
    except ValueError:
        return None
    if kdy.tzinfo is None:
        kdy = kdy.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - kdy).total_seconds() / 60


def v_okne(kdy):
    """Všední den mezi OBEDY_OKNO[0] a [1] hodinou."""
    return kdy.weekday() < 5 and config.OBEDY_OKNO[0] <= kdy.hour < config.OBEDY_OKNO[1]


def dnesni(data, dnes=None):
    """Podnik → dnešní menu ({} když není). Co nemá dnešní datum, neplatí."""
    dnes = (dnes or ted().date()).isoformat()
    vysledek = {}
    for podnik in PODNIKY:
        zaznam = data.get("podniky", {}).get(podnik["id"], {})
        vysledek[podnik["id"]] = (zaznam.get("menu") or {}) if zaznam.get("den") == dnes else {}
    return vysledek


def aktualizuj(vynutit=False, nanecisto=False, verbose=True):
    """Stáhne menu podniků, kterým je záznam starší než OBEDY_MAX_STARI_MINUT.

    Mimo okno (víkend, noc, odpoledne) nestahuje nic, ledaže `vynutit`.
    Každý podnik je na vlastní doméně a za hodinu se stáhne nejvýš jednou,
    takže Crawl-delay Kozlovny (10 s) se dodrží bez čekání.
    """
    data = nacti()
    kdy = ted()
    if not vynutit and not v_okne(kdy):
        if verbose:
            print("Obědy: mimo okno stahování, nic se nestahuje.")
        return data
    dnes = kdy.date()
    stazeno = chyb = 0
    for podnik in PODNIKY:
        zaznam = dict(data["podniky"].get(podnik["id"], {}))
        stari = _stari_minut(zaznam)
        if (not vynutit and zaznam.get("den") == dnes.isoformat()
                and stari is not None and stari < config.OBEDY_MAX_STARI_MINUT):
            continue
        try:
            markup = net.get(podnik["menu"], agent=config.OBEDY_USER_AGENT)
        except Exception as exc:                      # noqa: BLE001
            # Výpadek jednoho webu nesmí shodit ostatní ani build. Záznam
            # zůstane; když je ze včerejška, stránka ho stejně neukáže.
            chyb += 1
            print("  obědy: {0} se nestáhl ({1})".format(podnik["nazev"], exc),
                  file=sys.stderr)
            continue
        menu = rozeber(podnik, markup, dnes)
        if podnik["id"] in BEZ_DATA:
            menu, zaznam["otisk"], zaznam["otisk_od"] = _bez_data(zaznam, menu, dnes)
        zaznam.update({"den": dnes.isoformat(), "menu": menu,
                       "stazeno": datetime.now(timezone.utc).isoformat(timespec="seconds")})
        data["podniky"][podnik["id"]] = zaznam
        stazeno += 1
        if verbose:
            print("  obědy: {0}: {1}".format(
                podnik["nazev"], "{0} jídel".format(len(menu["jidla"])) if menu else "dnes nic"))
    if stazeno and not nanecisto:
        uloz(data)
    if verbose:
        print("Obědy: {0} staženo, {1} selhalo.".format(stazeno, chyb))
    return data
