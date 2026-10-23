# -*- coding: utf-8 -*-
"""Zdroj: oficiální aktuality města Kroměříž (TYPO3 + news plugin).

Dvě věci, které nejsou samozřejmé a stojí za zapamatování:

1. <guid> ve feedu je číselné ID a odkaz z něj NEFUNGUJE — přesměruje se na
   /aktuality/detail/<cislo> a vrátí 404. Skutečná adresa článku se odvozuje
   ze slugifikovaného titulku. Ověřeno napříč ročníky 2025 i 2026.
2. Feed nese jen perex (medián 464 znaků), žádnou fotku ani rubriku. Všechno
   ostatní je až na detailní stránce.
"""

import html
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from .. import htmlutil, net
from ..errors import NeresolvovanyClanek

SOURCE_ID = "mesto-kromeriz"
SOURCE_NAME = "Město Kroměříž"
BASE = "https://www.mesto-kromeriz.cz"
FEED_URL = BASE + "/fileadmin/rss/feed.xml"
DETAIL = BASE + "/aktuality/detail/{0}"


def fetch_items():
    """Načte feed. Vrací seznam položek seřazený od nejnovější."""
    strom = ET.fromstring(net.get(FEED_URL))
    polozky = []
    for item in strom.iterfind("./channel/item"):
        titulek = (item.findtext("title") or "").strip()
        if not titulek:
            continue
        slug = htmlutil.slugify(titulek)
        polozky.append({
            "source": SOURCE_ID,
            "source_name": SOURCE_NAME,
            "slug": slug,
            "id": htmlutil.klic(SOURCE_ID, slug),
            "title": titulek,
            "perex": (item.findtext("description") or "").strip(),
            "published": _datum(item.findtext("pubDate")),
            "url": DETAIL.format(slug),
        })
    polozky.sort(key=lambda p: p["published"], reverse=True)
    return polozky


def fetch_detail(item):
    """Dotáhne plný text, fotku, autora a rubriku. Mutuje a vrací item."""
    markup = None
    for adresa in _kandidati(item):
        try:
            kandidat = net.get(adresa)
        except RuntimeError:
            continue
        # Přípona -1 může patřit úplně jinému článku se stejně znějícím
        # titulkem. Bez téhle kontroly bychom přepsali cizí zprávu.
        if _sedi_titulek(kandidat, item["title"]):
            markup = kandidat
            item["url"] = adresa
            break

    if markup is None:
        nalez = _najdi_v_prehledu(item)
        if nalez:
            item["url"], markup = nalez

    if markup is None:
        raise NeresolvovanyClanek(item["title"])

    # Perex je na stránce vlastní blok a v news-content už NENÍ. Bez něj by
    # článku chyběl úvodní odstavec, ve kterém bývá hlavní sdělení i citace.
    perex = htmlutil.to_paragraphs(htmlutil.grab(markup, "div", "plugin-perex"))
    jadro = htmlutil.to_paragraphs(htmlutil.grab(markup, "div", "news-content"))
    item["body"] = perex + jadro
    if perex and not item.get("perex"):
        item["perex"] = perex[0]

    item["author"] = _prvni_radek(htmlutil.grab(markup, "div", "news-author"))
    item["rubrika"] = _prvni_radek(htmlutil.grab(markup, "div", "tag-name"))

    obrazek = htmlutil.meta(markup, "og:image")
    item["image_url"] = obrazek
    item["image_caption"] = _popisek(markup)

    # og:url je kanonická adresa — když se liší, slug se trefil jinam
    kanon = htmlutil.meta(markup, "og:url")
    if kanon:
        item["url"] = kanon
    return item


_PREHLED_CACHE = {}


def _prehled_slugy():
    """Slugy ze stránky aktualit. Stahuje se jednou za běh."""
    if "slugy" not in _PREHLED_CACHE:
        try:
            markup = net.get(BASE + "/aktuality/")
        except RuntimeError:
            _PREHLED_CACHE["slugy"] = []
            return []
        nalezene = re.findall(r'/aktuality/detail/([a-z0-9-]+)"', markup)
        _PREHLED_CACHE["slugy"] = sorted(set(nalezene))
    return _PREHLED_CACHE["slugy"]


def _najdi_v_prehledu(item):
    """Poslední záchrana pro článek, kterému po publikaci přepsali titulek.

    TYPO3 generuje slug jen při založení, takže 'vypracovala' v URL může
    patřit článku, který se dnes jmenuje 'zpracovala'. Z titulku se to
    nedopočítá, ale v přehledu aktualit ten odkaz je — stačí najít slug
    s největším překryvem slov a ověřit ho podle og:title.
    """
    hledane = set(item["slug"].split("-"))
    if not hledane:
        return None
    ohodnocene = []
    for slug in _prehled_slugy():
        shoda = len(hledane & set(slug.split("-"))) / float(len(hledane))
        if shoda >= 0.6:
            ohodnocene.append((shoda, slug))
    for _, slug in sorted(ohodnocene, reverse=True)[:3]:
        adresa = DETAIL.format(slug)
        try:
            markup = net.get(adresa)
        except RuntimeError:
            continue
        if _sedi_titulek(markup, item["title"]):
            return adresa, markup
    return None


def _sedi_titulek(markup, titulek):
    """Porovná og:title stránky s titulkem z feedu, bez diakritiky a mezer."""
    nalezeny = htmlutil.meta(markup, "og:title")
    if not nalezeny:
        return True  # stránka titulek neuvádí, nic lepšího nemáme
    return htmlutil.slugify(nalezeny) == htmlutil.slugify(titulek)


def _kandidati(item):
    """Adresy k vyzkoušení, od nejpravděpodobnější. TYPO3 přidává -1 až -3,
    když už slug stejného znění existuje."""
    zakladni = [item["slug"], htmlutil.slugify_zaloha(item["title"])]
    poradi = []
    for slug in zakladni:
        for pripona in ("", "-1", "-2", "-3"):
            kandidat = slug + pripona
            if kandidat not in poradi:
                poradi.append(kandidat)
    return [DETAIL.format(s) for s in poradi]


def _datum(raw):
    if not raw:
        return ""
    try:
        return parsedate_to_datetime(raw.strip()).isoformat()
    except (TypeError, ValueError):
        return ""


def _prvni_radek(fragment):
    radky = htmlutil.to_paragraphs(fragment)
    return radky[0] if radky else ""


def _popisek(markup):
    """Popisek hlavní fotky je v atributu alt, ne jako text pod obrázkem."""
    blok = htmlutil.grab(markup, "div", "plugin-main-image")
    m = re.search(r'<img[^>]+alt="([^"]*)"', blok)
    return html.unescape(m.group(1)).strip() if m else ""
