# -*- coding: utf-8 -*-
"""Drobné HTML nástroje nad stdlib HTMLParser.

Regulární výraz na vyříznutí <div> s vnořenými <div> nestačí, proto parser.
"""

import html
import hashlib
import re
import unicodedata
from html.parser import HTMLParser

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr"}


def _bez_diakritiky(text):
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def klic(zdroj_id, slug):
    """Identifikátor článku, ze kterého se nedá složit adresa zdroje.

    Dřív to byl `mesto-kromeriz:<slug oznámení>` a stejně se jmenoval
    i soubor v repu, takže veřejné `data/` prozrazovalo přesně to, co
    má zůstat schované. Otisk je deterministický, takže rozpoznávání
    už zpracovaných článků funguje dál bez jakékoli evidence navíc.

    Šestnáct znaků je přes 10^19 možností; na archiv o stovkách článků
    je šance na kolizi zanedbatelná a krátký název souboru se čte líp.
    """
    otisk = hashlib.sha256(slug.encode("utf-8")).hexdigest()[:16]
    return "{0}:{1}".format(zdroj_id, otisk)


def slugify(text):
    """Titulek → slug tak, jak ho dělá TYPO3 na webu města.

    Past: interpunkce uvnitř slova se MAŽE, nenahrazuje pomlčkou. Takže
    '1,2 milionu' → '12-milionu', ne '1-2-milionu'. Oddělovačem je jen mezera
    (a pomlčka, kterou TYPO3 bere jako mezeru). Ověřeno na skutečných URL.
    """
    text = _bez_diakritiky(text).lower()
    text = re.sub(r"[‐-―]", " ", text)       # – — jsou oddělovače
    text = re.sub(r"[^a-z0-9\s-]+", "", text)          # , . „ " ! ? se mažou
    return re.sub(r"[\s-]+", "-", text).strip("-")


def slugify_zaloha(text):
    """Naivní varianta: každý neznámý znak je pomlčka. Používá se, až když
    hlavní slug vrátí 404 — kdyby web pravidlo jednou změnil."""
    text = _bez_diakritiky(text).lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


class _DivGrabber(HTMLParser):
    """Vytáhne vnitřek prvního elementu, jehož class obsahuje hledané slovo."""

    def __init__(self, tag, css_class):
        HTMLParser.__init__(self, convert_charrefs=False)
        self.tag = tag
        self.css_class = css_class
        self.depth = 0
        self.capturing = False
        self.done = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if self.done:
            return
        if self.capturing:
            if tag == self.tag:
                self.depth += 1
            self.parts.append(self.get_starttag_text() or "")
            return
        if tag == self.tag:
            classes = dict(attrs).get("class") or ""
            if self.css_class in classes.split():
                self.capturing = True
                self.depth = 1

    def handle_endtag(self, tag):
        if self.done or not self.capturing:
            return
        if tag == self.tag:
            self.depth -= 1
            if self.depth == 0:
                self.done = True
                return
        self.parts.append("</{0}>".format(tag))

    def handle_startendtag(self, tag, attrs):
        if self.capturing and not self.done:
            self.parts.append(self.get_starttag_text() or "")

    def handle_data(self, data):
        if self.capturing and not self.done:
            self.parts.append(data)

    def handle_entityref(self, name):
        if self.capturing and not self.done:
            self.parts.append("&{0};".format(name))

    def handle_charref(self, name):
        if self.capturing and not self.done:
            self.parts.append("&#{0};".format(name))


def grab(markup, tag, css_class):
    """Vrátí vnitřní HTML prvního <tag class="... css_class ...">, jinak ''."""
    grabber = _DivGrabber(tag, css_class)
    grabber.feed(markup)
    return "".join(grabber.parts)


def to_paragraphs(markup):
    """HTML fragment → seznam odstavců jako čistý text."""
    markup = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", markup)
    markup = re.sub(r"(?i)<br\s*/?>", "\n", markup)
    markup = re.sub(r"(?i)</(p|div|li|h[1-6])>", "\n\n", markup)
    text = re.sub(r"(?s)<[^>]+>", "", markup)
    text = html.unescape(text)
    text = text.replace(" ", " ")
    out = []
    for blok in text.split("\n\n"):
        blok = re.sub(r"[ \t]+", " ", blok).strip()
        if blok:
            out.append(blok)
    return out


def meta(markup, key):
    """Hodnota <meta property|name="key" content="...">."""
    vzor = r'<meta[^>]+(?:property|name)="{0}"[^>]*content="([^"]*)"'.format(re.escape(key))
    m = re.search(vzor, markup, re.I)
    if not m:
        vzor = r'<meta[^>]+content="([^"]*)"[^>]*(?:property|name)="{0}"'.format(re.escape(key))
        m = re.search(vzor, markup, re.I)
    return html.unescape(m.group(1)) if m else ""
