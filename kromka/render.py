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
import shutil
from datetime import datetime, timezone

from . import config, htmlutil, piktogramy
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
  <p style="margin:0"><a href="/feed.xml">RSS</a> &middot; <a href="/o-webu.html">O webu</a> &middot; <a href="/jak-to-delame.html">Jak to děláme</a></p>
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
    return "".join(
        '<li><a href="{0}">{1}</a></li>'.format(_e(_tema_cesta(t)), _e(t))
        for t in poradi)


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

    if config.CIZI_FOTKY and clanek.get("image_local"):
        casti.append("<figure>{img}<figcaption>{popis} Foto: {autor}</figcaption></figure>".format(
            img=_obrazek_tag(clanek, trida="hero", lazy=False),
            popis=_e(clanek.get("image_caption", "")),
            autor=_e(clanek.get("author") or clanek["source_name"])))

    polozky = "".join(
        "<li>{emoji}<b>{label}</b> {text}</li>".format(
            emoji=(_e(p.get("emoji", "")) + " ") if p.get("emoji") else "",
            label=_e(p.get("label", "")), text=_e(p.get("text", "")))
        for p in clanek.get("tldr", []))
    if polozky:
        casti.append('<div class="tldr"><h2>TL;DR</h2><ul>{0}</ul></div>'.format(polozky))

    for odstavec in clanek.get("body", []):
        casti.append("<p>{0}</p>".format(_e(odstavec)))

    casti.append(
        '<div class="zdroj">Oficiální informace k téhle zprávě vydalo '
        '<a href="{url}" rel="nofollow">{zdroj}</a> '
        "({titulek}, {datum}).</div>".format(
            url=_e(clanek["url"]), titulek=_e(clanek["title"]),
            zdroj=_e(clanek["source_name"]), datum=_datum_cesky(clanek.get("published"))))

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
        "isBasedOn": clanek["url"],
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


def vykresli(clanky):
    """Vyrobí celý web do config.SITE. Vrací počet zapsaných souborů."""
    config.SITE.mkdir(parents=True, exist_ok=True)
    # Tyhle složky jsou celé generované. Bez úklidu v nich zůstávají soubory
    # ze starších běhů (po převodu na WebP třeba původní JPEGy) a vyvezou se
    # na web, kde na ně nic neodkazuje.
    for podslozka in ("clanek", "img", "tema"):
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

    (config.SITE / "jak-to-delame.html").write_text(_stranka(
        "Jak to děláme – " + config.BRAND,
        "Odkud bereme zprávy, jak je píšeme a čím si hlídáme, že nejsou opsané.",
        _jak_to_delame(), cesta="/jak-to-delame.html"), encoding="utf-8")
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
    (config.SITE / "sitemap.xml").write_text(_sitemap(clanky), encoding="utf-8")
    (config.SITE / "robots.txt").write_text(
        "User-agent: *\nAllow: /\nSitemap: {0}/sitemap.xml\n".format(config.SITE_URL),
        encoding="utf-8")
    (config.SITE / "CNAME").write_text(_domena() + "\n", encoding="utf-8")
    return zapsano + 7


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


def _jak_to_delame():
    kontakt = ""
    if config.KONTAKT:
        kontakt = (
            "<h2>Když je něco špatně</h2>"
            "<p>Napiš na <a href=\"mailto:{0}\">{0}</a>. Chybu opravíme, a pokud "
            "bude mít město nebo kdokoli jiný námitku k nějaké zprávě, stáhneme "
            "ji a teprve potom se budeme bavit o tom, kdo měl pravdu.</p>"
        ).format(_e(config.KONTAKT))
    return (
        '<article class="clanek">{drobecky}<h1>Jak to děláme</h1>'
        "<p>Tahle stránka je tu proto, aby se nikdo nemusel ptát, odkud bereme "
        "zprávy a jak s nimi nakládáme.</p>"

        "<h2>Odkud to víme</h2>"
        "<p>Z veřejného kanálu aktualit města Kroměříž. Nikam se nevloupáváme "
        "a nic neodemykáme — je to stejný zdroj, který si může načíst kdokoli.</p>"

        "<h2>Co s tím děláme</h2>"
        "<p>Z oznámení si vezmeme fakta a napíšeme o nich vlastní zprávu. Fakta "
        "jsou volná, formulace města ne, takže nepřebíráme ani věty, ani pořadí "
        "odstavců. Každá zpráva odkazuje na místo, kde město zveřejnilo oficiální "
        "informace.</p>"

        "<h2>Čím si to hlídáme</h2>"
        "<p>Nestačí nám to slíbit, tak to měříme. Než zpráva vyjde, stroj ověří, "
        "že:</p><ul>"
        "<li>se s oznámením neshoduje <strong>žádná souvislá sekvence delší než "
        "sedm slov</strong> (výjimkou jsou jména a názvy institucí),</li>"
        "<li>text neobsahuje <strong>jedinou přímou citaci</strong> — co kdo "
        "řekl, parafrázujeme, aby se nikomu nedala vložit do úst věta, kterou "
        "neřekl,</li>"
        "<li>v textu nejsou <strong>e-maily ani telefonní čísla</strong>,</li>"
        "<li>každé <strong>číslo, datum a částka</strong> má oporu v oznámení.</li>"
        "</ul>"
        "<p>Co těmi kontrolami neprojde, nevyjde. Ke každé zprávě se navíc ukládá "
        "snímek oznámení, ze kterého vznikla, a naměřené hodnoty, takže se to dá "
        "kdykoli přepočítat.</p>"

        "<h2>Fotky nepřebíráme</h2>"
        "<p>Web města má vyhrazená práva a souhlas s převzetím nemáme, takže "
        "tady žádné jeho fotky nenajdeš. Obrázky u zpráv jsou kreslené "
        "piktogramy.</p>"

        "<h2>Ověř si to</h2>"
        "<p>Kód i naměřené hodnoty jsou veřejné na "
        '<a href="{repo}" rel="noopener">GitHubu</a>. Nemusíš nám věřit, můžeš '
        "si to spočítat.</p>"

        "{kontakt}"
        "<p>Nejsme oficiální web města a nic z toho, co tady čteš, není "
        "stanovisko radnice.</p>"
        "</article>"
    ).format(drobecky=_drobecky([("Domů", "/"), ("Jak to děláme", None)]),
             repo=_e(config.REPOZITAR), kontakt=kontakt)


def _o_webu():
    return (
        '<article class="clanek">{drobecky}<h1>O webu</h1>'
        "<p>{disclaimer}</p>"
        "<p>O dění ve městě se dozvídáme z veřejného kanálu městských aktualit. "
        "Zprávy pak píšeme vlastními slovy. Nic z toho, co tady čteš, není "
        "oficiální stanovisko radnice — u každé zprávy je odkaz na místo, kde "
        "město zveřejnilo oficiální informace.</p>"
        "<p>Texty píše jazykový model. Čísla a data se strojově kontrolují, "
        "nikoho tu necitujeme v uvozovkách a kontaktní údaje sem nedáváme. "
        "Fotky města nepřebíráme. Chyba se ale stát může. Když nějakou "
        "najdeš, napiš.</p>"
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


def _sitemap(clanky):
    dnes = datetime.now(timezone.utc).date().isoformat()
    radky = ['<url><loc>{0}/jak-to-delame.html</loc><lastmod>{1}</lastmod><priority>0.5</priority></url>'.format(
        config.SITE_URL, dnes),
        '<url><loc>{0}/</loc><lastmod>{1}</lastmod><priority>1.0</priority></url>'.format(
        config.SITE_URL, dnes)]
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
