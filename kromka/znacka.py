# -*- coding: utf-8 -*-
"""Značka KROMCL: černé K na zelené dlaždici.

Geometrie je tady jednou a vyrábí se z ní všechno — SVG favicona i PNG ikony
pro iPhone a pro instalovanou aplikaci. Kdyby se kreslily zvlášť, rozejdou se
při první úpravě.

Mřížka 64 × 64. K jsou tři tahy o síle 9 s hranatými konci; tady jsou
převedené na mnohoúhelníky, protože Pillow tah s hranatým koncem šikmé čáry
nenakreslí a SVG z mnohoúhelníků vypadá stejně jako z tahů.

Vybraná 24. 10. 2026 z pěti návrhů (`nahled/favicon-navrhy.html`). Jako jediná
zůstala čistá i v 16 px na skutečném rastru; ostatní se v liště slévaly.
"""

import math

ZELENA = "#39E67A"
INKOUST = "#0c0c0c"
MRIZKA = 64

# Tahy písmene K: (začátek, konec), síla 9.
_TAHY = (
    ((19, 12), (19, 52)),     # dřík
    ((48, 12), (24, 32)),     # horní rameno
    ((24, 32), (50, 52)),     # dolní rameno
)
_SILA = 9

# Maskovatelná ikona: Android ji ořízne do kruhu nebo zaobleného čtverce
# a zaručeně ukáže jen kruh o poloměru 40 % velikosti. Písmeno se proto
# zmenší, aby se nic neuřízlo.
MERITKO_MASKY = 0.75
BEZPECNY_POLOMER = 0.4


def _tah_na_mnohouhelnik(a, b, sila):
    """Úsečka s hranatými konci jako čtyřúhelník."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    delka = math.hypot(dx, dy)
    nx, ny = -dy / delka * sila / 2, dx / delka * sila / 2
    return [(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny),
            (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)]


def mnohouhelniky(meritko=1.0):
    """Tvary písmene v souřadnicích mřížky, volitelně zmenšené ke středu."""
    stred = MRIZKA / 2
    vysledek = []
    for a, b in _TAHY:
        body = _tah_na_mnohouhelnik(a, b, _SILA)
        vysledek.append([(stred + (x - stred) * meritko,
                          stred + (y - stred) * meritko) for x, y in body])
    return vysledek


def svg(meritko=1.0):
    """Samostatné SVG pro `favicon.svg`."""
    cesty = "".join(
        '<path d="M{0}Z"/>'.format(
            "L".join("{0:.2f} {1:.2f}".format(x, y) for x, y in tvar))
        for tvar in mnohouhelniky(meritko))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {m} {m}">'
            '<rect width="{m}" height="{m}" fill="{zelena}"/>'
            '<g fill="{inkoust}">{cesty}</g></svg>\n').format(
                m=MRIZKA, zelena=ZELENA, inkoust=INKOUST, cesty=cesty)


def png(velikost, meritko=1.0, nadvzorkovani=8):
    """Ikona jako obrázek Pillow.

    Kreslí se osmkrát větší a pak zmenšuje, jinak by šikmé hrany K byly
    zubaté. Pillow se importuje až tady: build webu ho nepotřebuje, ikony se
    vyrábějí jednou skriptem `bin/ikony.py` a commitují se.
    """
    from PIL import Image, ImageDraw

    velky = velikost * nadvzorkovani
    obraz = Image.new("RGB", (velky, velky), ZELENA)
    kresba = ImageDraw.Draw(obraz)
    krok = velky / MRIZKA
    for tvar in mnohouhelniky(meritko):
        kresba.polygon([(x * krok, y * krok) for x, y in tvar], fill=INKOUST)
    return obraz.resize((velikost, velikost), Image.LANCZOS)
