# -*- coding: utf-8 -*-
"""Vykreslení statického webu. Žádný šablonovací engine, jen f-stringy.

Vlastní vizuál, ne kopie předlohy: tučné černé linky a tvrdé stíny, ale světlé
pozadí, jedna signální zelená na akcenty a podpora tmavého režimu.
"""

import html
import shutil
from datetime import datetime, timezone

from . import config

MESICE = ["", "ledna", "února", "března", "dubna", "května", "června",
          "července", "srpna", "září", "října", "listopadu", "prosince"]

CSS = """
:root {
  --papir: #f5f3ee; --inkoust: #0c0c0c; --akcent: ACCENT;
  --slabe: #6b6b6b; --ram: #0c0c0c; --karta: #ffffff;
}
:root:not([data-theme="light"]) { }
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
}
h1, h2, h3, .logo { font-family: Syne, ui-sans-serif, system-ui, sans-serif; font-weight: 800; line-height: 1.1; }
a { color: inherit; }
.obal { max-width: 1100px; margin: 0 auto; padding: 0 16px; }
header.hlava { border-bottom: 4px solid var(--ram); background: var(--karta); position: sticky; top: 0; z-index: 10; }
.hlava .obal { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; padding-top: 14px; padding-bottom: 14px; }
.logo { font-size: clamp(28px, 7vw, 44px); letter-spacing: -0.04em; text-decoration: none; }
.logo span { color: var(--akcent); }
.tagline { font-size: 13px; color: var(--slabe); text-transform: uppercase; letter-spacing: 0.08em; }
main { padding: 32px 0 64px; }
.mrizka { display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 22px; }
.karta {
  background: var(--karta); border: 3px solid var(--ram); box-shadow: 6px 6px 0 var(--ram);
  display: flex; flex-direction: column; text-decoration: none; overflow: hidden;
  transition: transform .15s ease, box-shadow .15s ease;
}
.karta:hover { transform: translate(-2px, -2px); box-shadow: 9px 9px 0 var(--ram); }
.karta img { width: 100%; aspect-ratio: 3/2; object-fit: cover; display: block; border-bottom: 3px solid var(--ram); }
.karta .telo { padding: 14px 16px 18px; display: flex; flex-direction: column; gap: 8px; flex: 1; }
.karta h2 { font-size: 20px; margin: 0; }
.stitky { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.stitek { background: var(--inkoust); color: var(--papir); font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; padding: 3px 7px; }
.stitek.jemny { background: transparent; color: var(--slabe); border: 2px solid var(--slabe); }
.datum { font-size: 13px; color: var(--slabe); }
.hlavni { grid-column: 1 / -1; }
.hlavni h2 { font-size: clamp(26px, 5vw, 40px); }
.hlavni img { aspect-ratio: 21/9; }
article.clanek { max-width: 720px; margin: 0 auto; }
article.clanek h1 { font-size: clamp(28px, 6vw, 46px); margin: 10px 0 14px; }
article.clanek img.hero { width: 100%; border: 3px solid var(--ram); box-shadow: 6px 6px 0 var(--ram); display: block; }
figcaption { font-size: 13px; color: var(--slabe); margin-top: 10px; }
.tldr { border: 3px solid var(--ram); background: var(--karta); box-shadow: 6px 6px 0 var(--ram); padding: 18px 20px; margin: 28px 0; }
.tldr h3 { margin: 0 0 12px; font-size: 14px; letter-spacing: .14em; text-transform: uppercase; }
.tldr ul { margin: 0; padding-left: 20px; }
.tldr li { margin-bottom: 10px; }
.tldr b { background: linear-gradient(transparent 62%, var(--akcent) 62%); }
.zdroj { border: 3px dashed var(--slabe); padding: 16px 18px; margin: 34px 0 0; font-size: 15px; }
.zdroj a { font-weight: 700; }
footer { border-top: 4px solid var(--ram); background: var(--karta); padding: 28px 0; font-size: 14px; color: var(--slabe); }
footer .obal { display: flex; flex-wrap: wrap; gap: 14px; justify-content: space-between; }
.strankovani { display: flex; gap: 12px; justify-content: center; margin-top: 40px; }
.strankovani a { border: 3px solid var(--ram); padding: 8px 16px; text-decoration: none; font-weight: 700; background: var(--karta); box-shadow: 4px 4px 0 var(--ram); }
@media (max-width: 640px) { .hlava .obal { flex-direction: column; gap: 2px; } .tagline { font-size: 11px; } }
""".replace("ACCENT", config.ACCENT)

ZAKLAD = """<!doctype html>
<html lang="cs">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulek}</title>
<meta name="description" content="{popis}">
<meta property="og:title" content="{og_titulek}">
<meta property="og:description" content="{popis}">
<meta property="og:type" content="{og_typ}">
<meta property="og:locale" content="{locale}">
{og_obrazek}
<link rel="alternate" type="application/rss+xml" title="{brand}" href="/feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Space+Grotesk:wght@400;500;700&display=swap" rel="stylesheet">
<style>{css}</style>
</head>
<body>
<header class="hlava"><div class="obal">
  <a class="logo" href="/">{brand}<span>.</span></a>
  <div class="tagline">{tagline}</div>
</div></header>
<main><div class="obal">{obsah}</div></main>
<footer><div class="obal">
  <div style="max-width:620px">{disclaimer}</div>
  <div><a href="/feed.xml">RSS</a> &middot; <a href="/o-webu.html">O webu</a></div>
</div></footer>
</body>
</html>
"""


def _e(text):
    return html.escape(text or "", quote=True)


def _datum_cesky(iso):
    if not iso:
        return ""
    try:
        d = datetime.fromisoformat(iso)
    except ValueError:
        return iso[:10]
    return "{0}. {1} {2}".format(d.day, MESICE[d.month], d.year)


def _stranka(titulek, popis, obsah, og_typ="website", obrazek="", og_titulek=None):
    og = ''
    if obrazek:
        og = '<meta property="og:image" content="{0}">'.format(_e(obrazek))
    return ZAKLAD.format(
        titulek=_e(titulek), popis=_e(popis), og_typ=og_typ,
        og_titulek=_e(og_titulek or titulek), og_obrazek=og,
        locale=config.LOCALE, css=CSS, brand=_e(config.BRAND),
        tagline=_e(config.TAGLINE), disclaimer=_e(config.DISCLAIMER),
        obsah=obsah,
    )


def _karta(clanek, hlavni=False):
    obrazek = ""
    if clanek.get("image_local"):
        obrazek = '<img src="/img/{0}" alt="" loading="lazy">'.format(_e(clanek["image_local"]))
    stitky = "".join(
        '<span class="stitek">{0}</span>'.format(_e(t)) for t in clanek.get("tags", [])
    )
    if clanek.get("sensitivity") == "neutralni":
        stitky += '<span class="stitek jemny">bez slangu</span>'
    return (
        '<a class="karta{hlavni}" href="/clanek/{slug}.html">{obrazek}'
        '<div class="telo"><div class="stitky">{stitky}</div>'
        '<h2>{nadpis}</h2>'
        '<div class="datum">{datum}</div></div></a>'
    ).format(
        hlavni=" hlavni" if hlavni else "",
        slug=_e(clanek["slug"]), obrazek=obrazek, stitky=stitky,
        nadpis=_e(clanek["headline"]), datum=_datum_cesky(clanek.get("published")),
    )


def _clanek(clanek):
    casti = []
    stitky = "".join('<span class="stitek">{0}</span>'.format(_e(t)) for t in clanek.get("tags", []))
    if clanek.get("sensitivity") == "neutralni":
        # Ať čtenář ví, proč tenhle článek čte jinak než ostatní.
        stitky += '<span class="stitek jemny">citlivé téma, bez slangu</span>'
    casti.append('<div class="stitky">{0}<span class="datum">{1}</span></div>'.format(
        stitky, _datum_cesky(clanek.get("published"))))
    casti.append("<h1>{0}</h1>".format(_e(clanek["headline"])))

    if clanek.get("image_local"):
        casti.append(
            '<figure style="margin:0 0 8px"><img class="hero" src="/img/{0}" alt="{1}">'
            "<figcaption>{2} Foto: {3}</figcaption></figure>".format(
                _e(clanek["image_local"]), _e(clanek.get("image_caption", "")),
                _e(clanek.get("image_caption", "")), _e(clanek.get("author") or clanek["source_name"]))
        )

    polozky = "".join(
        "<li>{emoji}<b>{label}</b> {text}</li>".format(
            emoji=(_e(p.get("emoji", "")) + " ") if p.get("emoji") else "",
            label=_e(p.get("label", "")), text=_e(p.get("text", "")))
        for p in clanek.get("tldr", [])
    )
    if polozky:
        casti.append('<div class="tldr"><h3>TL;DR</h3><ul>{0}</ul></div>'.format(polozky))

    for odstavec in clanek.get("body", []):
        casti.append("<p>{0}</p>".format(_e(odstavec)))

    casti.append(
        '<div class="zdroj">Tohle je AI přepis tiskové zprávy města. '
        'Originál se vším všudy: <a href="{url}">{titulek}</a> '
        "({zdroj}, {datum}).</div>".format(
            url=_e(clanek["url"]), titulek=_e(clanek["title"]),
            zdroj=_e(clanek["source_name"]), datum=_datum_cesky(clanek.get("published")))
    )
    return '<article class="clanek">{0}</article>'.format("".join(casti))


def vykresli(clanky):
    """Vyrobí celý web do config.SITE. Vrací počet zapsaných souborů."""
    config.SITE.mkdir(parents=True, exist_ok=True)
    (config.SITE / "clanek").mkdir(exist_ok=True)
    obrazky = config.SITE / "img"
    obrazky.mkdir(exist_ok=True)
    for soubor in config.IMAGES.glob("*"):
        shutil.copy2(soubor, obrazky / soubor.name)

    zapsano = 0
    for clanek in clanky:
        cesta = config.SITE / "clanek" / (clanek["slug"] + ".html")
        obrazek = ""
        if clanek.get("image_local"):
            obrazek = "{0}/img/{1}".format(config.SITE_URL, clanek["image_local"])
        cesta.write_text(_stranka(
            "{0} – {1}".format(clanek["headline"], config.BRAND),
            " ".join(p.get("text", "") for p in clanek.get("tldr", []))[:300],
            _clanek(clanek), og_typ="article", obrazek=obrazek,
            og_titulek=clanek["headline"],
        ), encoding="utf-8")
        zapsano += 1

    stranky = [clanky[i:i + config.PAGE_SIZE] for i in range(0, len(clanky), config.PAGE_SIZE)] or [[]]
    for cislo, davka in enumerate(stranky, start=1):
        karty = "".join(_karta(c, hlavni=(cislo == 1 and i == 0)) for i, c in enumerate(davka))
        obsah = '<div class="mrizka">{0}</div>{1}'.format(karty, _strankovani(cislo, len(stranky)))
        nazev = config.SITE / ("index.html" if cislo == 1 else "strana-{0}.html".format(cislo))
        nazev.write_text(_stranka(
            "{0} — {1}".format(config.BRAND, config.TAGLINE),
            config.DISCLAIMER, obsah,
        ), encoding="utf-8")
        zapsano += 1

    (config.SITE / "o-webu.html").write_text(_stranka(
        "O webu – " + config.BRAND, config.DISCLAIMER, _o_webu()), encoding="utf-8")
    (config.SITE / "feed.xml").write_text(_rss(clanky), encoding="utf-8")
    (config.SITE / "sitemap.xml").write_text(_sitemap(clanky), encoding="utf-8")
    (config.SITE / "robots.txt").write_text(
        "User-agent: *\nAllow: /\nSitemap: {0}/sitemap.xml\n".format(config.SITE_URL), encoding="utf-8")
    # GitHub Pages čte vlastní doménu ze souboru CNAME ve vydaném webu.
    # Musí se generovat sem, jinak ho každé nasazení smaže.
    (config.SITE / "CNAME").write_text(_domena() + "\n", encoding="utf-8")
    return zapsano + 5


def _domena():
    """Holá doména z SITE_URL, bez schématu a bez koncového lomítka."""
    return config.SITE_URL.split("://", 1)[-1].rstrip("/")


def _strankovani(cislo, celkem):
    if celkem < 2:
        return ""
    odkazy = []
    if cislo > 1:
        odkazy.append('<a href="{0}">← novější</a>'.format(
            "/" if cislo == 2 else "/strana-{0}.html".format(cislo - 1)))
    if cislo < celkem:
        odkazy.append('<a href="/strana-{0}.html">starší →</a>'.format(cislo + 1))
    return '<div class="strankovani">{0}</div>'.format("".join(odkazy))


def _o_webu():
    return (
        '<article class="clanek"><h1>O webu</h1>'
        "<p>{disclaimer}</p>"
        "<p>Zdrojem je veřejný RSS kanál města Kroměříž. Každý článek odkazuje na "
        "originál a nic z toho, co tady čteš, není oficiální stanovisko radnice.</p>"
        "<p>Citlivá témata — neštěstí, trestné činy, konflikty — se přepisují "
        "věcným tónem bez slangu, nebo se nepřepisují vůbec.</p>"
        "<p>Přepis dělá jazykový model. Fakta se strojově kontrolují proti "
        "originálu, ale chyba se stát může. Když nějakou najdeš, napiš.</p>"
        "</article>"
    ).format(disclaimer=_e(config.DISCLAIMER))


def _rss(clanky):
    polozky = []
    for clanek in clanky[:50]:
        polozky.append(
            "<item><title>{t}</title><link>{u}</link><guid>{u}</guid>"
            "<description><![CDATA[{d}]]></description><pubDate>{p}</pubDate></item>".format(
                t=_e(clanek["headline"]),
                u="{0}/clanek/{1}.html".format(config.SITE_URL, clanek["slug"]),
                d=" ".join(p.get("text", "") for p in clanek.get("tldr", [])),
                p=clanek.get("published", ""))
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>'
        "<title>{b}</title><link>{s}</link><description>{d}</description>{i}"
        "</channel></rss>"
    ).format(b=_e(config.BRAND), s=config.SITE_URL, d=_e(config.TAGLINE), i="".join(polozky))


def _sitemap(clanky):
    dnes = datetime.now(timezone.utc).date().isoformat()
    url = ['<url><loc>{0}/</loc><lastmod>{1}</lastmod></url>'.format(config.SITE_URL, dnes)]
    for clanek in clanky:
        url.append("<url><loc>{0}/clanek/{1}.html</loc><lastmod>{2}</lastmod></url>".format(
            config.SITE_URL, clanek["slug"], (clanek.get("published") or dnes)[:10]))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{0}</urlset>'
    ).format("".join(url))
