# -*- coding: utf-8 -*-
"""Doplnění údajů o projekcích ze stránek Domu kultury.

Otevřená data mají u kina program, ceny, synopse i kódy trailerů, ale ne
stopáž, přístupnost ani původní název. Ty jsou na stránce filmu, na kterou
už data odkazují polem `web` — sitemapa s 5 843 adresami se tedy procházet
nemusí a stahuje se jen to, co je v okně programu.

Odkaz na koupi lístku z téhle stránky získat **nejde**. Tlačítko Koupit je
`<a href="#" class="buy" data="…">` a odesílá POST formulář na
`websale-dkk.colosseum.eu/hall`; GET se stejnými parametry vrátí tutéž
obecnou stránku bez ohledu na projekci. Proto se odkazuje na stránku filmu,
kde to tlačítko je.

Nic z toho není pod otevřenou licencí jako data města, takže se přebírají
jen krátké faktické údaje, ne text. Když se cokoli nepovede, vrátí se
prázdno — program se musí vykreslit i bez toho.
"""

import html
import json
import re

from . import config, net

# Jen stránky Domu kultury, ať se přes pole `web` nestahuje půlka internetu.
_POVOLENY_HOST = "www.dk-kromeriz.cz"

_H1 = re.compile(r'<h1[^>]*itemprop="name"[^>]*>(.*?)</h1>\s*<h2[^>]*>(.*?)</h2>',
                 re.S | re.I)
_DELKA = re.compile(r'<div[^>]+class="delka"[^>]*>(.*?)</div>', re.S | re.I)
_PRISTUP = re.compile(r'<div[^>]+id="pristup"[^>]*>(.*?)</div>', re.S | re.I)
_BUNKY = re.compile(r'<td[^>]*class="r"[^>]*>(.*?)</td>', re.S | re.I)
_FORMAT = re.compile(r"titulky|dabing|dabov|\b[23]D\b", re.I)


def _cisty(kus):
    """Vnitřek značky na holý text."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", kus))).strip()


def rozeber(markup):
    """Údaje ze stránky filmu. Co se nenajde, v dictu prostě není."""
    out = {}
    nazev = _H1.search(markup)
    if nazev:
        puvodni = _cisty(nazev.group(2))
        # H2 nese plný název ("National Theatre Live: Frankenstein"); když se
        # od H1 neliší, nemá smysl ho ukazovat dvakrát.
        if puvodni and puvodni != _cisty(nazev.group(1)):
            out["puvodni_nazev"] = puvodni
    delka = _DELKA.search(markup)
    if delka:
        out["stopaz"] = _cisty(delka.group(1)).strip("()")
    pristup = _PRISTUP.search(markup)
    if pristup:
        out["pristupnost"] = _cisty(pristup.group(1))
    for bunka in _BUNKY.findall(markup):
        text = _cisty(bunka)
        if text and _FORMAT.search(text):
            out["format"] = text
            break
    return out


def _nacti_cache():
    if not config.KINO_CACHE.exists():
        return {}
    try:
        return json.loads(config.KINO_CACHE.read_text(encoding="utf-8"))
    except ValueError:
        return {}


def _uloz_cache(cache):
    config.KINO_CACHE.parent.mkdir(parents=True, exist_ok=True)
    config.KINO_CACHE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")


def doplnit(terminy, verbose=True):
    """Ke každé projekci přidá klíč `kino` s údaji ze stránky filmu.

    Stahuje se jednou na adresu, ne jednou na termín — jeden film mívá
    v programu několik projekcí.
    """
    cache = _nacti_cache()
    nove = stazeno = chyb = 0
    for termin in terminy:
        web = termin.get("web") or ""
        if termin.get("typ") != "Kino" or _POVOLENY_HOST not in web:
            continue
        if web not in cache:
            try:
                cache[web] = rozeber(net.get(web))
                stazeno += 1
            except Exception as exc:                  # noqa: BLE001
                # Rozbitá stránka nesmí shodit build celého webu.
                cache[web] = {}
                chyb += 1
                if verbose:
                    print("  kino: {0} se nestáhlo ({1})".format(web, exc))
            nove += 1
        if cache[web]:
            termin["kino"] = cache[web]
    if nove:
        _uloz_cache(cache)
    if verbose:
        print("Kino: {0} nových stránek, {1} staženo, {2} selhalo.".format(
            nove, stazeno, chyb))
    return terminy
