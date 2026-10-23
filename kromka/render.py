# -*- coding: utf-8 -*-
"""Vykreslení statického webu. Žádný šablonovací engine, jen f-stringy.

Vlastní vizuál, ne kopie předlohy: tučné černé linky a tvrdé stíny, ale světlé
pozadí, jedna signální zelená na akcenty a podpora tmavého režimu.

SEO vrstva je tu schválně celá na jednom místě: kanonická adresa, Open Graph,
Twitter karta, JSON-LD a drobečková navigace se skládají v `_stranka`, aby se
na žádném typu stránky nedaly zapomenout.
"""

import html
import json
import re
import shutil
from datetime import date, datetime, timedelta, timezone

from . import akce, config, htmlutil, piktogramy
MESICE = ["", "ledna", "února", "března", "dubna", "května", "června",
          "července", "srpna", "září", "října", "listopadu", "prosince"]

CSS = """
:root {
  --papir: #f5f3ee; --inkoust: #0c0c0c; --akcent: ACCENT;
  --slabe: #6b6b6b; --ram: #0c0c0c; --karta: #ffffff;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --papir: #121212; --inkoust: #f2f2f2; --slabe: #9a9a9a;
    --ram: #f2f2f2; --karta: #1c1c1c;
  }
}
:root[data-theme="dark"] {
  --papir: #121212; --inkoust: #f2f2f2; --slabe: #9a9a9a;
  --ram: #f2f2f2; --karta: #1c1c1c;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--papir); color: var(--inkoust);
  font-family: "Space Grotesk", ui-sans-serif, system-ui, sans-serif;
  font-size: 17px; line-height: 1.6; -webkit-text-size-adjust: 100%;
  overflow-wrap: break-word;
}
h1, h2, h3, .logo { font-family: Syne, ui-sans-serif, system-ui, sans-serif; font-weight: 800; line-height: 1.12; }
a { color: inherit; }
img { max-width: 100%; height: auto; }
.obal { max-width: 1100px; margin: 0 auto; padding: 0 16px; }
.preskocit { position: absolute; left: -9999px; }
.preskocit:focus { left: 8px; top: 8px; background: var(--akcent); color: #000; padding: 8px 12px; z-index: 50; }
header.hlava { border-bottom: 4px solid var(--ram); background: var(--karta); position: sticky; top: 0; z-index: 10; }
.hlava .obal { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; padding-top: 14px; padding-bottom: 14px; }
.logo { font-size: clamp(26px, 7vw, 44px); letter-spacing: -0.04em; text-decoration: none; }
.logo span { color: var(--akcent); }
.tagline { font-size: 13px; color: var(--slabe); text-transform: uppercase; letter-spacing: 0.08em; }
.znacka { display: flex; flex-direction: column; }
.menu { position: relative; }
.menu .prepinac { position: absolute; opacity: 0; width: 1px; height: 1px; }
.menu .odkazy { display: flex; flex-wrap: wrap; gap: 4px 14px; list-style: none; margin: 0; padding: 0; }
.menu .odkazy a { font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; text-decoration: none; border-bottom: 3px solid transparent; padding-bottom: 2px; }
.menu .odkazy a:hover, .menu .odkazy a:focus-visible { border-bottom-color: var(--akcent); }
.menu .hamburger { display: none; align-items: center; gap: 8px; font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; background: var(--karta); color: var(--inkoust); border: 3px solid var(--ram); box-shadow: 4px 4px 0 var(--ram); padding: 8px 12px; }
.carky { width: 18px; height: 2px; background: currentColor; box-shadow: 0 6px 0 currentColor, 0 -6px 0 currentColor; display: block; }
main { padding: 28px 0 56px; }
.drobecky { font-size: 13px; color: var(--slabe); margin-bottom: 14px; }
.drobecky a { text-decoration: none; border-bottom: 1px solid var(--slabe); }
.mrizka { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 22px; }
.karta {
  background: var(--karta); border: 3px solid var(--ram); box-shadow: 6px 6px 0 var(--ram);
  display: flex; flex-direction: column; text-decoration: none; overflow: hidden;
  transition: transform .15s ease, box-shadow .15s ease;
}
.karta:hover, .karta:focus-visible { transform: translate(-2px, -2px); box-shadow: 9px 9px 0 var(--ram); }
.karta img { width: 100%; aspect-ratio: 3/2; object-fit: cover; display: block; border-bottom: 3px solid var(--ram); }
.karta .telo { padding: 14px 16px 18px; display: flex; flex-direction: column; gap: 8px; flex: 1; }
.karta h2, .karta h3 { font-size: 20px; margin: 0; }
.stitky { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.stitek { background: var(--inkoust); color: var(--papir); font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; padding: 3px 7px; text-decoration: none; }
a.stitek:hover { background: var(--akcent); color: #000; }
.datum { font-size: 13px; color: var(--slabe); }
.hlavni { grid-column: 1 / -1; }
.hlavni h2 { font-size: clamp(24px, 5vw, 40px); }
.hlavni img { aspect-ratio: 21/9; }
article.clanek { max-width: 720px; margin: 0 auto; }
article.clanek h1 { font-size: clamp(27px, 6vw, 44px); margin: 10px 0 14px; }
article.clanek img.hero { width: 100%; border: 3px solid var(--ram); box-shadow: 6px 6px 0 var(--ram); display: block; }
figure { margin: 0 0 8px; }
figcaption { font-size: 13px; color: var(--slabe); margin-top: 10px; }
.tldr { border: 3px solid var(--ram); background: var(--karta); box-shadow: 6px 6px 0 var(--ram); padding: 18px 20px; margin: 28px 0; }
.tldr h2 { margin: 0 0 12px; font-size: 14px; letter-spacing: .14em; text-transform: uppercase; }
.tldr ul { margin: 0; padding-left: 20px; }
.tldr li { margin-bottom: 10px; }
.tldr b { background: linear-gradient(transparent 62%, var(--akcent) 62%); }
.zdroj { border: 3px dashed var(--slabe); padding: 16px 18px; margin: 34px 0 0; font-size: 15px; }
.zdroj a { font-weight: 700; }
.dalsi { margin-top: 48px; }
.dalsi h2 { font-size: 18px; text-transform: uppercase; letter-spacing: .1em; margin-bottom: 16px; }
footer { border-top: 4px solid var(--ram); background: var(--karta); padding: 26px 0; font-size: 14px; color: var(--slabe); }
footer .obal { display: flex; flex-wrap: wrap; gap: 14px; justify-content: space-between; }
.strankovani { display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; margin-top: 40px; }
.strankovani a { border: 3px solid var(--ram); padding: 8px 16px; text-decoration: none; font-weight: 700; background: var(--karta); box-shadow: 4px 4px 0 var(--ram); }
@media (max-width: 640px) {
  body { font-size: 16px; }
  .hlava .obal { flex-direction: column; align-items: flex-start; gap: 2px; }
  .tagline { font-size: 11px; }
  .hlava .obal { flex-direction: row; align-items: center; justify-content: space-between; gap: 10px; }
  .menu .hamburger { display: inline-flex; cursor: pointer; }
  .menu .odkazy { display: none; position: absolute; right: 0; top: calc(100% + 12px); z-index: 20; flex-direction: column; gap: 0; min-width: 200px; background: var(--karta); border: 3px solid var(--ram); box-shadow: 6px 6px 0 var(--ram); }
  .menu .prepinac:checked ~ .odkazy { display: flex; }
  .menu .prepinac:focus-visible ~ .hamburger { outline: 3px solid var(--akcent); outline-offset: 2px; }
  .menu .odkazy li + li { border-top: 2px solid var(--ram); }
  .menu .odkazy a { display: block; padding: 12px 16px; border-bottom: 0; }
  .menu .odkazy a:hover, .menu .odkazy a:focus-visible { background: var(--akcent); color: #000; border-bottom: 0; }
  .mrizka { grid-template-columns: 1fr; gap: 18px; }
  .karta, .tldr, article.clanek img.hero { box-shadow: 4px 4px 0 var(--ram); }
  .tldr { padding: 14px 16px; }
}
.obrazek { aspect-ratio: 3/2; display: grid; place-items: center; background: var(--akcent); border-bottom: 3px solid var(--ram); color: var(--inkoust); }
.obrazek .piktogram { width: 38%; height: auto; transform: rotate(-3deg); transition: transform .25s cubic-bezier(.34,1.56,.64,1); }
.piktogram .oko { fill: currentColor; stroke: none; }
.karta:hover .piktogram, .karta:focus-within .piktogram { transform: rotate(3deg) scale(1.1); }
.obrazek.hero .piktogram { animation: kyvani 5s ease-in-out infinite; }
@keyframes kyvani { 0%, 100% { transform: rotate(-3deg) } 50% { transform: rotate(3deg) translateY(-3px) } }
.hlavni .znacka { display: flex; flex-direction: column; }
.obrazek { aspect-ratio: 21/9; }
.obrazek.hero { aspect-ratio: 2/1; border: 3px solid var(--ram); border-bottom-width: 3px; box-shadow: 6px 6px 0 var(--ram); }
.obrazek.hero .piktogram { width: 26%; }
@media (max-width: 640px) { .obrazek.hero { box-shadow: 4px 4px 0 var(--ram); } }
@media (prefers-reduced-motion: reduce) { *, .obrazek .piktogram { transition: none !important; animation: none !important; } }

/* --- Program akcí. Nový blok patří na konec: výš v souboru se pravidla
   přebíjejí (.obrazek má aspect-ratio dvakrát) a vkládat doprostřed se
   nevyplácí. --- */
.menu .je-sekce { font-weight: 700; color: var(--akcent); -webkit-text-stroke: .4px var(--ram); }
.uvod { max-width: 62ch; font-size: 18px; margin: 0 0 26px; }
.filtr { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 30px; }
.filtr-odkaz { display: inline-block; padding: 6px 12px; border: 2px solid var(--ram); background: var(--karta); color: var(--inkoust); text-decoration: none; font-size: 14px; font-weight: 500; }
.filtr-odkaz:hover { box-shadow: 3px 3px 0 var(--ram); }
.filtr-odkaz.je-aktivni { background: var(--akcent); font-weight: 700; box-shadow: 3px 3px 0 var(--ram); }
.den { margin: 0 0 34px; }
.den h2 { font-size: 20px; text-transform: lowercase; border-bottom: 3px solid var(--ram); padding-bottom: 6px; margin: 0 0 16px; }
.akce-seznam { display: grid; gap: 14px; }
.akce { display: flex; gap: 14px; background: var(--karta); border: 3px solid var(--ram); box-shadow: 4px 4px 0 var(--ram); padding: 14px; }
.akce-kdy { flex: 0 0 74px; display: flex; flex-direction: column; align-items: center; gap: 8px; }
.akce-cas { font-family: Syne, sans-serif; font-weight: 800; font-size: 19px; line-height: 1.1; text-align: center; }
.akce-znak { width: 40px; color: var(--inkoust); }
.akce-znak .piktogram { width: 100%; height: auto; }
.akce-telo { min-width: 0; }
.akce-telo h3 { font-size: 18px; margin: 0 0 4px; }
.akce-puvodni { display: block; font-family: 'Space Grotesk', sans-serif; font-weight: 400; font-size: 14px; color: var(--slabe); }
.akce-kde, .akce-info, .akce-perex, .akce-odkazy { margin: 0 0 4px; font-size: 14px; }
.akce-kde { color: var(--slabe); font-weight: 500; }
.akce-perex { font-size: 15px; }
.akce-info { font-weight: 500; }
.akce-odkazy a { margin-right: 12px; }
.akce-prazdno { font-size: 18px; }
.atribuce { margin: 34px 0 0; padding-top: 14px; border-top: 2px dashed var(--ram); font-size: 13px; color: var(--slabe); max-width: 70ch; }
/* Logo má spodní mez clamp() 26 px, pod 371 px šířky se tedy přestane
   zmenšovat. Na 320 px pak logo 199 + mezera 10 + hamburger 109 + okraje 32
   dá 350 px a hlavička vodorovně přetéká o 13 px. Týká se nejužších
   telefonů (iPhone SE, mini). */
@media (max-width: 360px) { .logo { font-size: 21px; } }
@media (max-width: 640px) {
  .akce { gap: 10px; padding: 11px; box-shadow: 3px 3px 0 var(--ram); }
  .akce-kdy { flex-basis: 54px; }
  .akce-cas { font-size: 17px; }
  .akce-znak { width: 30px; }
  .akce-telo h3 { font-size: 17px; }
}
""".replace("ACCENT", config.ACCENT)

ZAKLAD = """<!doctype html>
<html lang="cs">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulek}</title>
<meta name="description" content="{popis}">
<link rel="canonical" href="{kanonicka}">
<meta property="og:title" content="{og_titulek}">
<meta property="og:description" content="{popis}">
<meta property="og:type" content="{og_typ}">
<meta property="og:url" content="{kanonicka}">
<meta property="og:site_name" content="{brand}">
<meta property="og:locale" content="{locale}">
{og_obrazek}{og_cas}
<meta name="twitter:card" content="{tw_karta}">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
<link rel="alternate" type="application/rss+xml" title="{brand}" href="/feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Space+Grotesk:wght@400;500;700&display=swap" rel="stylesheet">
<style>{css}</style>
{jsonld}</head>
<body>
<a class="preskocit" href="#obsah">Přeskočit na obsah</a>
<header class="hlava"><div class="obal">
  <div class="znacka">
    <a class="logo" href="/">{brand}<span>.</span></a>
    <p class="tagline">{tagline}</p>
  </div>
  <nav class="menu" aria-label="Témata">
    <input class="prepinac" type="checkbox" id="menu-prepinac">
    <label class="hamburger" for="menu-prepinac">
      <span class="carky" aria-hidden="true"></span>Témata
    </label>
    <ul class="odkazy">{menu}</ul>
  </nav>
</div></header>
<main id="obsah"><div class="obal">{obsah}</div></main>
<footer><div class="obal">
  <p style="max-width:620px;margin:0">{disclaimer}</p>
  <p style="margin:0"><a href="/feed.xml">RSS</a> &middot; <a href="/o-webu.html">O webu</a></p>
</div></footer>
</body>
</html>
"""


def _e(text):
    return html.escape(text or "", quote=True)


def _domena():
    """Holá doména z SITE_URL, bez schématu a bez koncového lomítka."""
    return config.SITE_URL.split("://", 1)[-1].rstrip("/")


def _tema_cesta(tag):
    """URL tématu. Název tématu má diakritiku, adresa ji mít nesmí —
    procentem kódovaná čeština v URL se špatně sdílí i loguje."""
    return "/tema/{0}.html".format(htmlutil.slugify(tag))


def _abs(cesta):
    return config.SITE_URL.rstrip("/") + cesta


def _datum_cesky(iso):
    if not iso:
        return ""
    try:
        d = datetime.fromisoformat(iso)
    except ValueError:
        return iso[:10]
    return "{0}. {1} {2}".format(d.day, MESICE[d.month], d.year)


def _zkrat(text, limit=155):
    """Popisek pro vyhledávač. Ořez na hranici slova, ne uprostřed."""
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    orez = text[:limit].rsplit(" ", 1)[0]
    return orez.rstrip(",.;:–-") + "…"


def _jsonld(*bloky):
    bloky = [b for b in bloky if b]
    if not bloky:
        return ""
    data = bloky[0] if len(bloky) == 1 else bloky
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    # </script> uvnitř řetězce by ukončil blok dřív, než má.
    text = text.replace("</", "<\\/")
    return '<script type="application/ld+json">{0}</script>\n'.format(text)


def _menu():
    """Odkazy na stránky témat. Pořadí je pevné, aby menu neposkakovalo
    podle toho, co zrovna vyšlo."""
    poradi = ["radnice", "doprava", "stavba", "peníze", "školství",
              "kultura", "sport", "akce", "volby", "příroda", "lidé"]
    # Program není téma článků, ale vlastní sekce — proto stojí první
    # a vede jinam než zbytek menu.
    polozky = ['<li><a class="je-sekce" href="{0}">program</a></li>'.format(
        _e(PROGRAM_CESTA))]
    polozky += ['<li><a href="{0}">{1}</a></li>'.format(
        _e(_tema_cesta(t)), _e(t)) for t in poradi]
    return "".join(polozky)


def _stranka(titulek, popis, obsah, cesta="/", og_typ="website", obrazek="",
             og_titulek=None, jsonld="", publikovano=""):
    og = ""
    if obrazek:
        og = ('<meta property="og:image" content="{0}">\n'
              '<meta property="og:image:alt" content="{1}">\n').format(
            _e(obrazek), _e(og_titulek or titulek))
    cas = ""
    if publikovano:
        cas = '<meta property="article:published_time" content="{0}">\n'.format(_e(publikovano))
    return ZAKLAD.format(
        titulek=_e(titulek), popis=_e(_zkrat(popis)), og_typ=og_typ,
        og_titulek=_e(og_titulek or titulek), og_obrazek=og, og_cas=cas,
        kanonicka=_e(_abs(cesta)), locale=config.LOCALE, css=CSS,
        brand=_e(config.BRAND), tagline=_e(config.TAGLINE),
        disclaimer=_e(config.DISCLAIMER), obsah=obsah, jsonld=jsonld,
        menu=_menu(),
        tw_karta="summary_large_image" if obrazek else "summary",
    )


def _obrazek_tag(clanek, trida="", lazy=True):
    """Místo fotky kreslený piktogram tématu.

    Fotky města přebírat nesmíme. Piktogram drží stejný poměr stran jako
    dřív fotka, takže se layout nezměnil a stránka nepohne obsahem.
    """
    tema = piktogramy.pro_tema(clanek.get("tags"))
    popis = "Téma: {0}".format((clanek.get("tags") or ["zpráva"])[0])
    return '<div class="obrazek {0}" data-tema="{1}">{2}</div>'.format(
        trida, _e(tema), piktogramy.svg(tema, trida="piktogram", popis=popis))


def _karta(clanek, hlavni=False, uroven="h2"):
    stitky = "".join(
        '<a class="stitek" href="{0}">{1}</a>'.format(_e(_tema_cesta(t)), _e(t))
        for t in clanek.get("tags", []))
    return (
        '<article class="karta{hlavni}">{obrazek}'
        '<div class="telo"><div class="stitky">{stitky}</div>'
        '<{u}><a href="/clanek/{slug}.html" style="text-decoration:none">{nadpis}</a></{u}>'
        '<p class="datum" style="margin:0">{datum}</p></div></article>'
    ).format(
        hlavni=" hlavni" if hlavni else "", u=uroven,
        slug=_e(clanek["slug"]), obrazek=_obrazek_tag(clanek, lazy=not hlavni),
        stitky=stitky, nadpis=_e(clanek["headline"]),
        datum=_datum_cesky(clanek.get("published")),
    )


def _drobecky(polozky):
    """polozky = [(nazev, cesta nebo None)] — poslední je aktuální stránka."""
    kusy = []
    for nazev, cesta in polozky:
        if cesta:
            kusy.append('<a href="{0}">{1}</a>'.format(_e(cesta), _e(nazev)))
        else:
            kusy.append(_e(nazev))
    return '<nav class="drobecky" aria-label="Drobečková navigace">{0}</nav>'.format(
        " / ".join(kusy))


def _clanek(clanek, souvisejici):
    casti = []
    tema = (clanek.get("tags") or [None])[0]
    casti.append(_drobecky([
        ("Domů", "/"),
        (tema, _tema_cesta(tema)) if tema else ("Článek", None),
        (clanek["headline"][:40], None),
    ]))

    stitky = "".join('<a class="stitek" href="{0}">{1}</a>'.format(_e(_tema_cesta(t)), _e(t))
                     for t in clanek.get("tags", []))
    casti.append('<div class="stitky">{0}<time class="datum" datetime="{1}">{2}</time></div>'.format(
        stitky, _e((clanek.get("published") or "")[:10]),
        _datum_cesky(clanek.get("published"))))
    casti.append("<h1>{0}</h1>".format(_e(clanek["headline"])))

    # Hlavní obrázek článku je kreslený piktogram tématu; fotky nepřebíráme.
    casti.append(_obrazek_tag(clanek, trida="hero", lazy=False))

    polozky = "".join(
        "<li>{emoji}<b>{label}</b> {text}</li>".format(
            emoji=(_e(p.get("emoji", "")) + " ") if p.get("emoji") else "",
            label=_e(p.get("label", "")), text=_e(p.get("text", "")))
        for p in clanek.get("tldr", []))
    if polozky:
        casti.append('<div class="tldr"><h2>TL;DR</h2><ul>{0}</ul></div>'.format(polozky))

    for odstavec in clanek.get("body", []):
        casti.append("<p>{0}</p>".format(_e(odstavec)))

    telo = '<article class="clanek">{0}</article>'.format("".join(casti))

    if souvisejici:
        karty = "".join(_karta(c, uroven="h3") for c in souvisejici)
        telo += ('<section class="dalsi"><h2>Další z Kroměříže</h2>'
                 '<div class="mrizka">{0}</div></section>'.format(karty))
    return telo


def _ld_clanek(clanek):
    cesta = "/clanek/{0}.html".format(clanek["slug"])
    data = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": clanek["headline"][:110],
        "description": _zkrat(" ".join(p.get("text", "") for p in clanek.get("tldr", []))),
        "datePublished": clanek.get("published", ""),
        "dateModified": clanek.get("rewritten_at") or clanek.get("published", ""),
        "inLanguage": "cs-CZ",
        "mainEntityOfPage": {"@type": "WebPage", "@id": _abs(cesta)},
        "url": _abs(cesta),
        "author": {"@type": "Organization", "name": config.BRAND, "url": config.SITE_URL},
        "publisher": {"@type": "Organization", "name": config.BRAND, "url": config.SITE_URL},
        # Poctivé přiznání, že jde o přepis cizí zprávy.
        "keywords": ", ".join(clanek.get("tags", [])),
    }
    if clanek.get("image_local"):
        data["image"] = [_abs("/img/" + clanek["image_local"])]
    return data


def _ld_drobecky(clanek):
    tema = (clanek.get("tags") or [None])[0]
    polozky = [{"@type": "ListItem", "position": 1, "name": "Domů", "item": config.SITE_URL}]
    if tema:
        polozky.append({"@type": "ListItem", "position": 2, "name": tema,
                        "item": _abs(_tema_cesta(tema))})
    polozky.append({"@type": "ListItem", "position": len(polozky) + 1,
                    "name": clanek["headline"]})
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": polozky}


def _ld_web():
    return {
        "@context": "https://schema.org", "@type": "WebSite",
        "name": config.BRAND, "url": config.SITE_URL,
        "description": config.TAGLINE, "inLanguage": "cs-CZ",
        "publisher": {"@type": "Organization", "name": config.BRAND, "url": config.SITE_URL},
    }


def _souvisejici(clanek, vsechny, pocet=3):
    """Články se stejným tématem. Interní prolinkování, aby článek nebyl slepý."""
    moje = set(clanek.get("tags", []))
    kandidati = [c for c in vsechny if c["slug"] != clanek["slug"]]
    kandidati.sort(key=lambda c: (-len(moje & set(c.get("tags", []))),
                                  c.get("published", "")), reverse=False)
    vybrane = [c for c in kandidati if moje & set(c.get("tags", []))][:pocet]
    if len(vybrane) < pocet:
        zbytek = [c for c in kandidati if c not in vybrane]
        zbytek.sort(key=lambda c: c.get("published", ""), reverse=True)
        vybrane += zbytek[:pocet - len(vybrane)]
    return vybrane


# --- Program akcí ---------------------------------------------------------
# Každý typ je samostatná vstupní stránka, ne přefiltrovaný rodič. Proto má
# vlastní adresu, titulek, popis, H1 i úvodní odstavec — a ten se píše ručně,
# protože odstavec vyrobený šablonou by byl zase jen jinak poskládaný rodič.
# Klíč je název typu z číselníku města.
TYPY_AKCI = {
    "Kino": {
        "slug": "kino",
        "h1": "Kino Nadsklepí: program",
        "titulek": "Program Kina Nadsklepí v Kroměříži",
        "popis": "Co hraje Kino Nadsklepí v Kroměříži. Časy projekcí, ceny, "
                 "délka filmu a od kolika let, na měsíc dopředu.",
        "uvod": "Nadsklepí točí program každý den, takže tahle stránka je "
                "nejhustší z celého programu. U každé projekce je čas, cena, "
                "jestli jsou titulky nebo dabing, jak je film dlouhý a od "
                "kolika let.",
    },
    "Divadlo": {
        "slug": "divadlo",
        "h1": "Divadlo v Kroměříži",
        "titulek": "Divadelní představení v Kroměříži",
        "popis": "Divadelní představení v Kroměříži na měsíc dopředu. "
                 "Kde se hraje, kdy se začíná a co to stojí.",
        "uvod": "Představení v Domě kultury i mimo něj. Divadlo se tu nehraje "
                "každý den, takže když něco vyjde na termín, který ti sedí, "
                "nemá smysl to odkládat.",
    },
    "Muzea, výstavy, galerie": {
        "slug": "vystavy",
        "h1": "Výstavy v Kroměříži",
        "titulek": "Výstavy, muzea a galerie v Kroměříži",
        "popis": "Výstavy v kroměřížských muzeích a galeriích. Dokdy jsou "
                 "k vidění, kde a za kolik.",
        "uvod": "Výstavy běží týdny až měsíce, takže je najdeš nahoře v sekci "
                "Probíhá. U každé je, dokdy je otevřená — ten údaj je tu "
                "důležitější než čas začátku.",
    },
    "Hudba a tanec": {
        "slug": "hudba",
        "h1": "Koncerty a tancovačky v Kroměříži",
        "titulek": "Koncerty a hudební akce v Kroměříži",
        "popis": "Koncerty, tancovačky a hudební akce v Kroměříži na měsíc "
                 "dopředu, včetně cen a míst.",
        "uvod": "Od klubů po zámecké sály. Ceny se tu liší nejvíc z celého "
                "programu, tak koukej i na poznámku u vstupného — slevy pro "
                "studenty bývají právě tam.",
    },
    "Přednášky a besedy": {
        "slug": "besedy",
        "h1": "Přednášky a besedy v Kroměříži",
        "titulek": "Přednášky a besedy v Kroměříži",
        "popis": "Přednášky, besedy a workshopy v Kroměříži. Kdy, kde a "
                 "jestli se platí vstup.",
        "uvod": "Druhá nejpočetnější kategorie programu. Hodně z nich je "
                "v knihovně a hodně zadarmo — na to kouká štítek u ceny.",
    },
    "Sport": {
        "slug": "sport",
        "h1": "Sport v Kroměříži",
        "titulek": "Sportovní akce a zápasy v Kroměříži",
        "popis": "Zápasy, závody a sportovní akce v Kroměříži na měsíc "
                 "dopředu.",
        "uvod": "Zápasy i akce, na které se dá přijít bez klubové příslušnosti. "
                "U domácích zápasů je místo konání tím, co potřebuješ vědět "
                "nejdřív.",
    },
    "Zábava": {
        "slug": "zabava",
        "h1": "Zábava v Kroměříži",
        "titulek": "Zábavné akce v Kroměříži",
        "popis": "Zábavné akce, kvízy a společenské večery v Kroměříži.",
        "uvod": "Všechno, co se nevešlo nikam jinam a stojí za večer venku. "
                "Bývá to nepravidelné, takže se sem vyplatí koukat.",
    },
    "Jarmarky, trhy a gastro": {
        "slug": "jarmarky",
        "h1": "Trhy a jídlo v Kroměříži",
        "titulek": "Jarmarky, trhy a gastro akce v Kroměříži",
        "popis": "Farmářské trhy, jarmarky a gastro akce v Kroměříži. "
                 "Termíny a místa na měsíc dopředu.",
        "uvod": "Trhy na Velkém náměstí i jednorázové gastro akce. Většina "
                "je venku a zadarmo, platí se až u stánku.",
    },
}

PROGRAM_CESTA = "/program.html"

# Výběry podle času. Vznikly z dat Ahrefs (cz, říjen 2026): lidé nehledají
# typ akce, hledají okno. „akce kroměříž tento víkend" má 500 hledání
# měsíčně při obtížnosti 2, „kroměříž akce dnes" 450 při 1 — zatímco
# „divadlo kroměříž", „koncerty kroměříž", „výstavy kroměříž" i „kulturní
# akce kroměříž" mají shodně nulu. Typy proto zůstávají jako navigace,
# ale tyhle dvě stránky jsou to, co někdo opravdu hledá.
#
# Na rozdíl od typů se vykreslí i prázdné. Adresa musí být stabilní, aby
# měla šanci se ve vyhledávání usadit, a „dnes se nekoná nic" je poctivá
# odpověď na dotaz „akce dnes".
VYBERY = {
    "dnes": {
        "h1": "Co se dnes děje v Kroměříži",
        "titulek": "Akce v Kroměříži dnes",
        "popis": "Co se v Kroměříži děje dnes. Kino, koncerty, výstavy "
                 "a všechno ostatní s časem a místem, aktualizované každou hodinu.",
        "uvod": "Všechno, co dneska v Kroměříži začíná, plus výstavy, které "
                "zrovna běží. Seznam se přepisuje každou hodinu, takže co "
                "už skončilo, tu nenajdeš.",
        "prazdno": "Dneska v Kroměříži nic nezačíná. Mrkni na víkend nebo na "
                   "celý program.",
    },
    "vikend": {
        "h1": "Kam v Kroměříži tento víkend",
        "titulek": "Akce v Kroměříži tento víkend",
        "popis": "Kam v Kroměříži o víkendu. Sobotní a nedělní program — "
                 "kino, koncerty, trhy i výstavy na jednom místě.",
        "uvod": "Sobota a neděle, která přijde nejblíž. Když je zrovna "
                "víkend, je tu ten právě probíhající. Výstavy, které běží "
                "přes víkend, jsou nahoře.",
        "prazdno": "Na nejbližší víkend tu zatím nic není. Zkus celý program, "
                   "věci se doplňují průběžně.",
    },
}


def _vyber_cesta(klic):
    return "/program/{0}.html".format(klic)


def _okno_dnes(dnes):
    return {dnes.isoformat()}


def _okno_vikend(dnes):
    """Nejbližší sobota a neděle. Když je víkend, tak ten právě probíhající."""
    do_soboty = (5 - dnes.weekday()) % 7
    if dnes.weekday() == 6:          # v neděli se zpátky na sobotu
        do_soboty = -1
    sobota = dnes + timedelta(days=do_soboty)
    return {sobota.isoformat(), (sobota + timedelta(days=1)).isoformat()}


_OKNA = {"dnes": _okno_dnes, "vikend": _okno_vikend}


def _v_okne(termin, dny):
    """Termín patří do okna, když v něm začíná nebo přes něj běží."""
    zacatek = (termin.get("zacatek") or "")[:10]
    if zacatek in dny:
        return True
    if not termin.get("vicedenni"):
        return False
    konec = (termin.get("konec") or "")[:10]
    return any(zacatek <= den <= konec for den in dny)


def _typ_cesta(nazev_typu):
    udaje = TYPY_AKCI.get(nazev_typu)
    return "/program/{0}.html".format(udaje["slug"]) if udaje else PROGRAM_CESTA


def _cas_hm(iso):
    return "{0}.{1}".format(iso[11:13].lstrip("0") or "0", iso[14:16]) if iso else ""


def _den_cesky(iso):
    """`2026-10-24` na „pátek 24. října"."""
    DNY = ("pondělí", "úterý", "středa", "čtvrtek", "pátek", "sobota", "neděle")
    try:
        d = datetime.strptime(iso[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return iso[:10]
    return "{0} {1}. {2}".format(DNY[d.weekday()], d.day, MESICE[d.month])


def _datum_kratce(iso):
    """`2026-11-01` na „1. 11.". Do úzkého sloupce s časem se dlouhý tvar
    nevejde a zalomí se do čtyř řádků."""
    try:
        d = datetime.strptime(iso[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return iso[:10]
    return "{0}. {1}.".format(d.day, d.month)


def _pristupnost(text):
    """„nevhodné pro nezletilé osoby do 12 let" na „nevhodné do 12 let".

    Úřední tvar je v pruhu pod názvem nejdelší položkou ze všech a nic
    navíc neříká.
    """
    return re.sub(r"nevhodné pro nezletilé osoby do", "nevhodné do", text or "")


def _cena_text(termin):
    """Cena tak, jak ji město uvádí. Nula znamená neuvedena, ne zdarma."""
    if termin.get("zdarma"):
        return "zdarma"
    cena = termin.get("cena") or 0
    if not cena:
        return ""
    text = "{0} Kč".format(cena)
    if termin.get("cena_pozn"):
        text += " ({0})".format(termin["cena_pozn"])
    return text


def _karta_akce(termin):
    tvar = piktogramy.pro_typ_akce(termin.get("typ"))
    if termin.get("vicedenni"):
        kdy = "do {0}".format(_datum_kratce(termin.get("konec", "")))
    else:
        kdy = _cas_hm(termin.get("zacatek", ""))

    kde = [termin.get("misto") or "místo neuvedeno"]
    if termin.get("typ"):
        kde.append(termin["typ"])
    if termin.get("vicedenni"):
        # V úzkém sloupci je jen „do 1. 11."; celý rozsah patří sem, kde je
        # místo na to napsat ho čitelně.
        kde.append("{0} – {1}".format(_den_cesky(termin.get("zacatek", "")),
                                      _den_cesky(termin.get("konec", ""))))

    # Údaje ze stránky Domu kultury, pokud se podařilo je stáhnout.
    kino = termin.get("kino") or {}
    # Poznámka z otevřených dat bývá „titulky" a formát z DK „titulky | 2D".
    # Vypsat obojí vedle sebe vypadá jako chyba.
    poznamka = termin.get("poznamka", "")
    if poznamka and poznamka.lower() in kino.get("format", "").lower():
        poznamka = ""
    info = [_cena_text(termin), poznamka, kino.get("format", ""),
            kino.get("stopaz", ""), _pristupnost(kino.get("pristupnost", ""))]
    if termin.get("pro_deti"):
        info.append("pro děti")
    info = " · ".join(_e(x) for x in info if x)

    odkazy = []
    if termin.get("web"):
        odkazy.append('<a href="{0}" rel="noopener">Víc o akci</a>'.format(
            _e(termin["web"])))
    if termin.get("youtube"):
        odkazy.append('<a href="https://www.youtube.com/watch?v={0}" '
                      'rel="noopener">Trailer</a>'.format(_e(termin["youtube"])))

    nazev = _e(termin.get("nazev", ""))
    if kino.get("puvodni_nazev"):
        nazev += ' <span class="akce-puvodni">{0}</span>'.format(
            _e(kino["puvodni_nazev"]))

    return (
        '<article class="akce">'
        '<div class="akce-kdy"><span class="akce-cas">{kdy}</span>'
        '<div class="akce-znak">{znak}</div></div>'
        '<div class="akce-telo"><h3>{nazev}</h3>'
        '<p class="akce-kde">{kde}</p>'
        '{perex}{info}{odkazy}</div></article>'
    ).format(
        kdy=_e(kdy), znak=piktogramy.svg(tvar, trida="piktogram", popis=""),
        nazev=nazev, kde=" · ".join(_e(k) for k in kde),
        perex='<p class="akce-perex">{0}</p>'.format(
            _e(_zkrat(termin["perex"], 180))) if termin.get("perex") else "",
        info='<p class="akce-info">{0}</p>'.format(info) if info else "",
        odkazy='<p class="akce-odkazy">{0}</p>'.format(
            " ".join(odkazy)) if odkazy else "",
    )


def _filtr(aktivni, dostupne):
    """Lišta filtru. Odkazy vykreslené na serveru, žádný JavaScript.

    Nejdřív okna v čase, pak typy — v tom pořadí se podle dat i hledá.
    """
    def odkaz(cesta, popisek, je):
        return '<a class="filtr-odkaz{0}" href="{1}">{2}</a>'.format(
            " je-aktivni" if je else "", _e(cesta), _e(popisek))

    kusy = [odkaz(PROGRAM_CESTA, "Vše", aktivni is None)]
    for klic, udaje in VYBERY.items():
        kusy.append(odkaz(_vyber_cesta(klic),
                          "Dnes" if klic == "dnes" else "Víkend",
                          aktivni == klic))
    kusy.append('<span class="filtr-del" aria-hidden="true"></span>')
    for typ in TYPY_AKCI:
        if typ not in dostupne:
            continue
        kusy.append(odkaz(_typ_cesta(typ), TYPY_AKCI[typ]["h1"].split(":")[0],
                          typ == aktivni))
    return '<nav class="filtr" aria-label="Filtr programu">{0}</nav>'.format(
        "".join(kusy))


def _atribuce():
    """Podpis pod programem. Licence ho vyžaduje na každé stránce s daty."""
    return (
        '<p class="atribuce">Data o akcích poskytuje '
        '<a href="{spec}" rel="noopener">{kdo}</a> jako otevřená data pod '
        'licencí <a href="{lic_url}" rel="license noopener">{lic}</a>. '
        'Program přebíráme beze změny, včetně časů a cen; ověřit si je '
        'u pořadatele se vždycky vyplatí.</p>'
    ).format(spec=_e(config.AKCE_SPECIFIKACE), kdo=_e(config.AKCE_POSKYTOVATEL),
             lic_url=_e(config.AKCE_LICENCE_URL), lic=_e(config.AKCE_LICENCE))


def _program(terminy, aktivni, dostupne, prazdno=""):
    """Tělo stránky programu: probíhající akce, pak dny."""
    probiha = [t for t in terminy if t.get("vicedenni")]
    jednodenni = [t for t in terminy if not t.get("vicedenni")]

    casti = [_filtr(aktivni, dostupne)]
    if probiha:
        casti.append(
            '<section class="den"><h2>Probíhá teď</h2><div class="akce-seznam">'
            '{0}</div></section>'.format("".join(_karta_akce(t) for t in probiha)))

    dny = {}
    for t in jednodenni:
        dny.setdefault(t["zacatek"][:10], []).append(t)
    for den in sorted(dny):
        casti.append(
            '<section class="den"><h2 id="d{0}">{1}</h2>'
            '<div class="akce-seznam">{2}</div></section>'.format(
                _e(den), _e(_den_cesky(den)),
                "".join(_karta_akce(t) for t in dny[den])))

    if not terminy:
        casti.append('<p class="akce-prazdno">{0} <a href="{1}">Celý program '
                     'na měsíc dopředu.</a></p>'.format(
                         _e(prazdno or "Na nejbližší měsíc tu zatím nic není."),
                         PROGRAM_CESTA))
    casti.append(_atribuce())
    return "".join(casti)


def _ld_akce(termin):
    data = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": termin.get("nazev", ""),
        "startDate": termin.get("zacatek", ""),
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "eventStatus": "https://schema.org/EventScheduled",
    }
    if termin.get("konec"):
        data["endDate"] = termin["konec"]
    if termin.get("perex"):
        data["description"] = termin["perex"]
    if termin.get("misto"):
        data["location"] = {"@type": "Place", "name": termin["misto"],
                            "address": {"@type": "PostalAddress",
                                        "addressLocality": "Kroměříž",
                                        "addressCountry": "CZ"}}
    if termin.get("web"):
        data["url"] = termin["web"]
    if termin.get("zdarma"):
        data["isAccessibleForFree"] = True
    elif termin.get("cena"):
        data["offers"] = {"@type": "Offer", "price": termin["cena"],
                          "priceCurrency": "CZK"}
    return data


def _ld_seznam(terminy, cesta):
    """ItemList s akcemi. Prvních 30, dál to pro vyhledávač nemá cenu."""
    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "url": _abs(cesta),
        "numberOfItems": len(terminy),
        "itemListElement": [
            {"@type": "ListItem", "position": i, "item": _ld_akce(t)}
            for i, t in enumerate(terminy[:30], start=1)],
    }


def _ld_drobecky_program(nazev=None, cesta=None):
    polozky = [("Domů", "/"), ("Program", PROGRAM_CESTA)]
    if nazev:
        polozky.append((nazev, cesta))
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": n, "item": _abs(c)}
            for i, (n, c) in enumerate(polozky, start=1)],
    }


def _program_stranky(akce_data):
    """Zapíše /program.html a stránku ke každému zastoupenému typu.

    Typ bez jediného termínu v okně se nevykreslí a nikam se na něj
    neodkazuje — prázdná indexovatelná stránka je horší než žádná.
    """
    terminy = akce_data.get("terminy") or []
    dostupne = {t.get("typ") for t in terminy if t.get("typ") in TYPY_AKCI}
    (config.SITE / "program").mkdir(parents=True, exist_ok=True)

    uvod = ("Co se děje v Kroměříži příštích {0} dní. Divadlo, kino, koncerty, "
            "výstavy, sport i trhy na jednom místě, seřazené podle dne. "
            "Program bereme z otevřených dat města, takže časy a ceny jsou "
            "takové, jaké je zveřejnil pořadatel.").format(
        akce_data.get("dni") or config.AKCE_DNI)

    (config.SITE / "program.html").write_text(_stranka(
        "Program akcí v Kroměříži – " + config.BRAND,
        "Co se děje v Kroměříži příštích {0} dní: divadlo, kino, koncerty, "
        "výstavy, sport i trhy. Časy, místa a ceny na jednom místě.".format(
            akce_data.get("dni") or config.AKCE_DNI),
        '{0}<h1>Program akcí v Kroměříži</h1><p class="uvod">{1}</p>{2}'.format(
            _drobecky([("Domů", "/"), ("Program", None)]), _e(uvod),
            _program(terminy, None, dostupne)),
        cesta=PROGRAM_CESTA,
        jsonld=_jsonld(_ld_seznam(terminy, PROGRAM_CESTA),
                       _ld_drobecky_program()),
    ), encoding="utf-8")
    zapsano = 1

    dnes = date.today()
    for klic, udaje in VYBERY.items():
        dny = _OKNA[klic](dnes)
        vybrane = [t for t in terminy if _v_okne(t, dny)]
        cesta = _vyber_cesta(klic)
        (config.SITE / "program" / (klic + ".html")).write_text(_stranka(
            "{0} – {1}".format(udaje["titulek"], config.BRAND),
            udaje["popis"],
            '{0}<h1>{1}</h1><p class="uvod">{2}</p>{3}'.format(
                _drobecky([("Domů", "/"), ("Program", PROGRAM_CESTA),
                           (udaje["h1"], None)]),
                _e(udaje["h1"]), _e(udaje["uvod"]),
                _program(vybrane, klic, dostupne, udaje["prazdno"])),
            cesta=cesta, og_titulek=udaje["titulek"],
            jsonld=_jsonld(_ld_seznam(vybrane, cesta),
                           _ld_drobecky_program(udaje["h1"], cesta)),
        ), encoding="utf-8")
        zapsano += 1

    for typ, udaje in TYPY_AKCI.items():
        if typ not in dostupne:
            continue
        vybrane = [t for t in terminy if t.get("typ") == typ]
        cesta = _typ_cesta(typ)
        (config.SITE / "program" / (udaje["slug"] + ".html")).write_text(_stranka(
            "{0} – {1}".format(udaje["titulek"], config.BRAND),
            udaje["popis"],
            '{0}<h1>{1}</h1><p class="uvod">{2}</p>{3}'.format(
                _drobecky([("Domů", "/"), ("Program", PROGRAM_CESTA),
                           (udaje["h1"], None)]),
                _e(udaje["h1"]), _e(udaje["uvod"]),
                _program(vybrane, typ, dostupne)),
            cesta=cesta, og_titulek=udaje["titulek"],
            jsonld=_jsonld(_ld_seznam(vybrane, cesta),
                           _ld_drobecky_program(udaje["h1"], cesta)),
        ), encoding="utf-8")
        zapsano += 1
    return zapsano


def vykresli(clanky, akce_data=None):
    """Vyrobí celý web do config.SITE. Vrací počet zapsaných souborů."""
    config.SITE.mkdir(parents=True, exist_ok=True)
    # Tyhle složky jsou celé generované. Bez úklidu v nich zůstávají soubory
    # ze starších běhů (po převodu na WebP třeba původní JPEGy) a vyvezou se
    # na web, kde na ně nic neodkazuje.
    # Kořenové HTML je taky generované. Bez úklidu by po zrušené stránce
    # zůstal na webu soubor, na který už nic neodkazuje.
    for stary in config.SITE.glob("*.html"):
        stary.unlink()
    for podslozka in ("clanek", "img", "tema", "program"):
        shutil.rmtree(str(config.SITE / podslozka), ignore_errors=True)
        (config.SITE / podslozka).mkdir(parents=True, exist_ok=True)
    if config.CIZI_FOTKY:
        for soubor in config.IMAGES.glob("*"):
            shutil.copy2(soubor, config.SITE / "img" / soubor.name)

    zapsano = 0
    for clanek in clanky:
        cesta = "/clanek/{0}.html".format(clanek["slug"])
        obrazek = ""
        if config.CIZI_FOTKY and clanek.get("image_local"):
            obrazek = _abs("/img/" + clanek["image_local"])
        (config.SITE / "clanek" / (clanek["slug"] + ".html")).write_text(_stranka(
            "{0} – {1}".format(clanek["headline"], config.BRAND),
            " ".join(p.get("text", "") for p in clanek.get("tldr", [])),
            _clanek(clanek, _souvisejici(clanek, clanky)),
            cesta=cesta, og_typ="article", obrazek=obrazek,
            og_titulek=clanek["headline"], publikovano=clanek.get("published", ""),
            jsonld=_jsonld(_ld_clanek(clanek), _ld_drobecky(clanek)),
        ), encoding="utf-8")
        zapsano += 1

    zapsano += _rozcestniky(clanky)
    zapsano += _temata(clanky)
    if akce_data is None:
        akce_data = akce.nacti()
    zapsano += _program_stranky(akce_data)

    (config.SITE / "o-webu.html").write_text(_stranka(
        "O webu – " + config.BRAND, config.DISCLAIMER, _o_webu(),
        cesta="/o-webu.html"), encoding="utf-8")
    (config.SITE / "404.html").write_text(_stranka(
        "Stránka nenalezena – " + config.BRAND,
        "Tahle stránka tu není. Zkus úvodku.",
        '<article class="clanek"><h1>404, tady nic není</h1>'
        '<p>Odkaz je rozbitý nebo článek zmizel. '
        '<a href="/">Zpátky na úvodku.</a></p></article>',
        cesta="/404.html"), encoding="utf-8")
    (config.SITE / "feed.xml").write_text(_rss(clanky), encoding="utf-8")
    (config.SITE / "sitemap.xml").write_text(
        _sitemap(clanky, akce_data), encoding="utf-8")
    (config.SITE / "robots.txt").write_text(
        "User-agent: *\nAllow: /\nSitemap: {0}/sitemap.xml\n".format(config.SITE_URL),
        encoding="utf-8")
    (config.SITE / "CNAME").write_text(_domena() + "\n", encoding="utf-8")
    return zapsano + 6


def _rozcestniky(clanky):
    stranky = [clanky[i:i + config.PAGE_SIZE]
               for i in range(0, len(clanky), config.PAGE_SIZE)] or [[]]
    for cislo, davka in enumerate(stranky, start=1):
        karty = "".join(_karta(c, hlavni=(cislo == 1 and i == 0))
                        for i, c in enumerate(davka))
        obsah = '<div class="mrizka">{0}</div>{1}'.format(
            karty, _strankovani(cislo, len(stranky)))
        cesta = "/" if cislo == 1 else "/strana-{0}.html".format(cislo)
        nazev = "index.html" if cislo == 1 else "strana-{0}.html".format(cislo)
        titulek = "{0} — {1}".format(config.BRAND, config.TAGLINE)
        if cislo > 1:
            titulek = "{0} — strana {1}".format(config.BRAND, cislo)
        (config.SITE / nazev).write_text(_stranka(
            titulek, config.DISCLAIMER, obsah, cesta=cesta,
            jsonld=_jsonld(_ld_web()) if cislo == 1 else "",
        ), encoding="utf-8")
    return len(stranky)


def _temata(clanky):
    """Stránka na každé téma. Prolinkuje archiv a dá vyhledávači co indexovat."""
    podle_tematu = {}
    for clanek in clanky:
        for tag in clanek.get("tags", []):
            podle_tematu.setdefault(tag, []).append(clanek)
    for tag, seznam in podle_tematu.items():
        karty = "".join(_karta(c) for c in seznam)
        obsah = (_drobecky([("Domů", "/"), (tag, None)])
                 + "<h1>Téma: {0}</h1>".format(_e(tag))
                 + '<p class="datum">{0} článků</p>'.format(len(seznam))
                 + '<div class="mrizka">{0}</div>'.format(karty))
        (config.SITE / "tema" / (htmlutil.slugify(tag) + ".html")).write_text(_stranka(
            "{0} v Kroměříži – {1}".format(tag.capitalize(), config.BRAND),
            "Všechno, co {0} napsal na téma {1}. Celkem {2} článků.".format(
                config.BRAND, tag, len(seznam)),
            obsah, cesta=_tema_cesta(tag),
        ), encoding="utf-8")
    return len(podle_tematu)


def _strankovani(cislo, celkem):
    if celkem < 2:
        return ""
    odkazy = []
    if cislo > 1:
        odkazy.append('<a href="{0}">← novější</a>'.format(
            "/" if cislo == 2 else "/strana-{0}.html".format(cislo - 1)))
    if cislo < celkem:
        odkazy.append('<a href="/strana-{0}.html">starší →</a>'.format(cislo + 1))
    return '<nav class="strankovani">{0}</nav>'.format("".join(odkazy))



def _o_webu():
    return (
        '<article class="clanek">{drobecky}<h1>O webu</h1>'
        "<p>{disclaimer}</p>"
        "<p>Píšeme o tom, co se děje v Kroměříži, jazykem, kterým se to dá "
        "číst. Nejsme oficiální web města a nic z toho, co tady najdeš, není "
        "stanovisko radnice.</p>"
        "<p>Texty píše jazykový model. Čísla a data si hlídáme strojově, "
        "nikoho tu necitujeme v uvozovkách a kontaktní údaje sem nedáváme. "
        "Chyba se ale stát může. Když nějakou najdeš, napiš.</p>"
        "</article>"
    ).format(disclaimer=_e(config.DISCLAIMER),
             drobecky=_drobecky([("Domů", "/"), ("O webu", None)]))

def _rss(clanky):
    polozky = []
    for clanek in clanky[:50]:
        adresa = _abs("/clanek/{0}.html".format(clanek["slug"]))
        polozky.append(
            "<item><title>{t}</title><link>{u}</link><guid isPermaLink=\"true\">{u}</guid>"
            "<description><![CDATA[{d}]]></description><pubDate>{p}</pubDate></item>".format(
                t=_e(clanek["headline"]), u=_e(adresa),
                d=" ".join(p.get("text", "") for p in clanek.get("tldr", [])),
                p=_rfc822(clanek.get("published", ""))))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
        "<title>{b}</title><link>{s}</link><description>{d}</description>"
        '<language>cs</language>'
        '<atom:link href="{s}/feed.xml" rel="self" type="application/rss+xml"/>{i}'
        "</channel></rss>"
    ).format(b=_e(config.BRAND), s=config.SITE_URL, d=_e(config.TAGLINE), i="".join(polozky))


def _rfc822(iso):
    """RSS chce RFC 822, ne ISO. Čtečky si na tom jinak vylámou zuby."""
    if not iso:
        return ""
    try:
        from email.utils import format_datetime
        return format_datetime(datetime.fromisoformat(iso))
    except (ValueError, ImportError):
        return iso


def _sitemap(clanky, akce_data=None):
    dnes = datetime.now(timezone.utc).date().isoformat()
    radky = ['<url><loc>{0}/</loc><lastmod>{1}</lastmod><priority>1.0</priority></url>'.format(
        config.SITE_URL, dnes)]
    terminy = (akce_data or {}).get("terminy") or []
    if terminy:
        radky.append("<url><loc>{0}</loc><lastmod>{1}</lastmod><priority>0.9</priority></url>".format(
            _abs(PROGRAM_CESTA), dnes))
        # Okna v čase jsou to, co lidé hledají — priorita jako u úvodky.
        # Typy jsou hlavně navigace, proto níž.
        for klic in VYBERY:
            radky.append("<url><loc>{0}</loc><lastmod>{1}</lastmod><priority>0.9</priority></url>".format(
                _abs(_vyber_cesta(klic)), dnes))
        for typ in TYPY_AKCI:
            if any(t.get("typ") == typ for t in terminy):
                priorita = "0.8" if typ == "Kino" else "0.5"
                radky.append("<url><loc>{0}</loc><lastmod>{1}</lastmod><priority>{2}</priority></url>".format(
                    _abs(_typ_cesta(typ)), dnes, priorita))
    temata = sorted({t for c in clanky for t in c.get("tags", [])})
    for tag in temata:
        radky.append("<url><loc>{0}</loc><lastmod>{1}</lastmod><priority>0.6</priority></url>".format(
            _abs(_tema_cesta(tag)), dnes))
    for clanek in clanky:
        radky.append("<url><loc>{0}</loc><lastmod>{1}</lastmod><priority>0.8</priority></url>".format(
            _abs("/clanek/{0}.html".format(clanek["slug"])),
            (clanek.get("published") or dnes)[:10]))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{0}</urlset>'
            ).format("".join(radky))
