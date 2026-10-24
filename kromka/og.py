# -*- coding: utf-8 -*-
"""Karta 1200 × 630 pro náhled odkazu (og:image) a obrázek v JSON-LD.

Fotky města přebírat nesmíme (`config.CIZI_FOTKY`), takže bez vlastní karty
by odkaz na Facebooku, v Messengeru, WhatsAppu i na Discordu vyšel bez
obrázku a Google by článek nevzal do Discoveru, který chce obrázek široký
aspoň 1200 px.

Podoba vybraná 24. 10. 2026 z mockupu tří variant (varianta A): zelený pás
se značkou a tématem, titulek Syne na papíře, piktogram tématu v bílém rámu
s tvrdým stínem jako karty na webu, dole doména a datum. Titulek se zmenšuje,
dokud se nevejde; teprve na nejmenší velikosti se zkrátí výpustkou.

Piktogramy jsou SVG a Pillow SVG neumí. `piktogram()` proto převede cesty
z `piktogramy.TVARY` na lomené čáry a nakreslí je sám: tah s hranatým
koncem a kulatým spojem jako v šabloně. Stačí na podmnožinu SVG, kterou
piktogramy používají (path s M L H V C S Q A Z, circle, ellipse, rect s rx).
Nový piktogram se tak na kartě objeví bez dalšího kroku.

Kreslí se v Pillow. Bez něj se karta přeskočí a stránka zůstane bez
obrázku, jako dřív.
"""

import functools
import math
import re
from pathlib import Path

from . import karta, piktogramy

ROZMER = (1200, 630)

PAPIR = "#f5f3ee"
INKOUST = "#0c0c0c"
ZELENA = "#39E67A"
BILA = "#ffffff"

PISMA = Path(__file__).resolve().parent / "pisma"

# Rozložení varianty A v pixelech karty.
OKRAJ = 56
PAS = 96                     # výška zeleného pásu, pod ním linka 8 px
TITULEK_Y, TITULEK_SIRKA, TITULEK_VYSKA = 146, 760, 370
TITULEK_PISMO = range(64, 38, -2)   # od největšího, dokud se nevejde
RAM, RAM_Y, STIN = 280, 160, 12
PIKTOGRAM = 210

# Tah piktogramu v jednotkách viewBoxu 64 × 64, jako v piktogramy.svg().
TAH = 5

_ELEMENT = re.compile(r"<(path|circle|ellipse|rect)\b([^>]*)/?>")
_ATRIBUT = re.compile(r'([a-z-]+)="([^"]*)"')
_TOKEN = re.compile(r"[MmLlHhVvCcSsQqAaZz]|-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


# --- Převod SVG na lomené čáry ------------------------------------------------

def _oblouk(x1, y1, rx, ry, rotace, velky, kladny, x2, y2):
    """Eliptický oblouk SVG (koncové body) na body lomené čáry.

    Převod na střed podle přílohy F.6.5 specifikace SVG. Vrací body bez
    počátečního, ten už v čáře je.
    """
    if rx == 0 or ry == 0 or (x1 == x2 and y1 == y2):
        return [(x2, y2)]
    rx, ry = abs(rx), abs(ry)
    fi = math.radians(rotace)
    cos, sin = math.cos(fi), math.sin(fi)
    dx, dy = (x1 - x2) / 2, (y1 - y2) / 2
    x1p, y1p = cos * dx + sin * dy, -sin * dx + cos * dy
    # Příliš malý poloměr se podle specifikace zvětší, aby oblouk vyšel.
    lam = (x1p / rx) ** 2 + (y1p / ry) ** 2
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    citatel = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    jmenovatel = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    koef = math.sqrt(max(0.0, citatel / jmenovatel))
    if velky == kladny:
        koef = -koef
    cxp, cyp = koef * rx * y1p / ry, -koef * ry * x1p / rx
    cx = cos * cxp - sin * cyp + (x1 + x2) / 2
    cy = sin * cxp + cos * cyp + (y1 + y2) / 2

    def uhel(ux, uy, vx, vy):
        u = math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
        return u

    t1 = uhel(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dt = uhel((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not kladny and dt > 0:
        dt -= 2 * math.pi
    elif kladny and dt < 0:
        dt += 2 * math.pi
    kroku = max(4, int(abs(dt) / math.radians(8)))
    body = []
    for i in range(1, kroku + 1):
        t = t1 + dt * i / kroku
        ex, ey = rx * math.cos(t), ry * math.sin(t)
        body.append((cos * ex - sin * ey + cx, sin * ex + cos * ey + cy))
    return body


def _bezier(body, kroku=16):
    """Bézierova křivka (2. nebo 3. stupně) na body bez počátečního."""
    vysledek = []
    for i in range(1, kroku + 1):
        t = i / kroku
        if len(body) == 3:
            (x0, y0), (x1, y1), (x2, y2) = body
            x = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * x1 + t * t * x2
            y = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * y1 + t * t * y2
        else:
            (x0, y0), (x1, y1), (x2, y2), (x3, y3) = body
            a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
            x = a * x0 + b * x1 + c * x2 + d * x3
            y = a * y0 + b * y1 + c * y2 + d * y3
        vysledek.append((x, y))
    return vysledek


def cesta(d):
    """Atribut `d` na seznam podcest [(body, uzavrena)]."""
    tokeny = _TOKEN.findall(d)
    podcesty, body = [], []
    x = y = sx = sy = 0.0
    prikaz, posledni_ridici = None, None
    i = 0

    def cisla(n):
        nonlocal i
        hodnoty = [float(t) for t in tokeny[i:i + n]]
        i += n
        return hodnoty

    def ukonci(uzavrena):
        nonlocal body
        if len(body) > 1:
            podcesty.append((body, uzavrena))
        body = []

    while i < len(tokeny):
        if tokeny[i].isalpha():
            prikaz = tokeny[i]
            i += 1
            if prikaz in "Zz":
                ukonci(True)
                x, y = sx, sy
                posledni_ridici = None
                continue
        if prikaz is None:
            raise ValueError("Cesta nezačíná příkazem: " + d)
        rel = prikaz.islower()
        p = prikaz.upper()
        ox, oy = (x, y) if rel else (0.0, 0.0)
        if p == "M":
            nx, ny = cisla(2)
            ukonci(False)
            x, y = ox + nx, oy + ny
            sx, sy = x, y
            body = [(x, y)]
            # Další dvojice čísel po M jsou podle specifikace L.
            prikaz = "l" if rel else "L"
            posledni_ridici = None
            continue
        if not body:
            body = [(x, y)]
        if p == "L":
            nx, ny = cisla(2)
            x, y = ox + nx, oy + ny
            body.append((x, y))
            posledni_ridici = None
        elif p == "H":
            (nx,) = cisla(1)
            x = ox + nx
            body.append((x, y))
            posledni_ridici = None
        elif p == "V":
            (ny,) = cisla(1)
            y = oy + ny
            body.append((x, y))
            posledni_ridici = None
        elif p in "CS":
            if p == "C":
                x1, y1, x2, y2, nx, ny = cisla(6)
                k1 = (ox + x1, oy + y1)
            else:
                x2, y2, nx, ny = cisla(4)
                # S zrcadlí poslední řídicí bod předchozí křivky.
                k1 = ((2 * x - posledni_ridici[0], 2 * y - posledni_ridici[1])
                      if posledni_ridici else (x, y))
            k2 = (ox + x2, oy + y2)
            konec = (ox + nx, oy + ny)
            body.extend(_bezier([(x, y), k1, k2, konec]))
            posledni_ridici = k2
            x, y = konec
        elif p == "Q":
            x1, y1, nx, ny = cisla(4)
            k1 = (ox + x1, oy + y1)
            konec = (ox + nx, oy + ny)
            body.extend(_bezier([(x, y), k1, konec], kroku=12))
            posledni_ridici = None
            x, y = konec
        elif p == "A":
            rx, ry, rotace, velky, kladny, nx, ny = cisla(7)
            konec = (ox + nx, oy + ny)
            body.extend(_oblouk(x, y, rx, ry, rotace, bool(velky), bool(kladny), *konec))
            posledni_ridici = None
            x, y = konec
        else:
            raise ValueError("Nepodporovaný příkaz cesty {0}: {1}".format(prikaz, d))
    ukonci(False)
    return podcesty


def _elipsa(cx, cy, rx, ry, kroku=72):
    return [(cx + rx * math.cos(2 * math.pi * i / kroku),
             cy + ry * math.sin(2 * math.pi * i / kroku)) for i in range(kroku)]


def _obdelnik(x, y, w, h, r):
    if not r:
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    r = min(r, w / 2, h / 2)
    body = []
    rohy = ((x + w - r, y + r, -90), (x + w - r, y + h - r, 0),
            (x + r, y + h - r, 90), (x + r, y + r, 180))
    for cx, cy, start in rohy:
        for i in range(7):
            u = math.radians(start + 15 * i)
            body.append((cx + r * math.cos(u), cy + r * math.sin(u)))
    return body


def tvary(tema):
    """Piktogram jako [(druh, body, uzavrena)], druh je "tah" nebo "vypln"."""
    vysledek = []
    for prvek in piktogramy.TVARY.get(tema, piktogramy.TVARY["_vychozi"]):
        for nazev, atributy in _ELEMENT.findall(prvek):
            a = dict(_ATRIBUT.findall(atributy))
            f = {k: float(v) for k, v in a.items() if re.match(r"^-?[\d.]+$", v)}
            # Oči jsou v šabloně vyplněné a bez tahu (CSS .piktogram .oko).
            druh = "vypln" if a.get("class") == "oko" else "tah"
            if nazev == "path":
                for body, uzavrena in cesta(a["d"]):
                    vysledek.append((druh, body, uzavrena))
            elif nazev == "circle":
                vysledek.append((druh, _elipsa(f["cx"], f["cy"], f["r"], f["r"]), True))
            elif nazev == "ellipse":
                vysledek.append((druh, _elipsa(f["cx"], f["cy"], f["rx"], f["ry"]), True))
            elif nazev == "rect":
                vysledek.append((druh, _obdelnik(f.get("x", 0), f.get("y", 0), f["width"],
                                                 f["height"], f.get("rx", 0)), True))
    return vysledek


# --- Kreslení ---------------------------------------------------------------

def _tah(kresba, body, uzavrena, sila, barva):
    """Lomená čára s kulatými spoji a hranatými konci (stroke-linecap square)."""
    pul = sila / 2
    if uzavrena:
        body = body + [body[0]]
    usecky = [(a, b) for a, b in zip(body, body[1:]) if math.hypot(b[0] - a[0], b[1] - a[1]) > 1e-9]
    for i, (a, b) in enumerate(usecky):
        dx, dy = b[0] - a[0], b[1] - a[1]
        delka = math.hypot(dx, dy)
        ux, uy = dx / delka, dy / delka
        if not uzavrena and i == 0:
            a = (a[0] - ux * pul, a[1] - uy * pul)
        if not uzavrena and i == len(usecky) - 1:
            b = (b[0] + ux * pul, b[1] + uy * pul)
        nx, ny = -uy * pul, ux * pul
        kresba.polygon([(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny),
                        (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)], fill=barva)
    spoje = body[1:-1] if not uzavrena else body
    for x, y in spoje:
        kresba.ellipse([x - pul, y - pul, x + pul, y + pul], fill=barva)


@functools.lru_cache(maxsize=64)
def piktogram(tema, velikost, barva=INKOUST, pozadi=BILA, nadvzorkovani=4):
    """Piktogram jako obrázek Pillow, čtverec `velikost` px.

    Kreslí se několikrát větší a pak zmenšuje, jinak by šikmé tahy a oblouky
    byly zubaté — stejný postup jako u ikon ve `znacka.png`. Tvarů je
    dvacet a karet stovky, proto mezipaměť; výsledek se jen vkládá, nemění.
    """
    from PIL import Image, ImageDraw

    velky = velikost * nadvzorkovani
    meritko = velky / 64
    obraz = Image.new("RGB", (velky, velky), pozadi)
    kresba = ImageDraw.Draw(obraz)
    for druh, body, uzavrena in tvary(tema):
        body = [(x * meritko, y * meritko) for x, y in body]
        if druh == "vypln":
            kresba.polygon(body, fill=barva)
        else:
            _tah(kresba, body, uzavrena, TAH * meritko, barva)
    return obraz.resize((velikost, velikost), Image.LANCZOS)


def rozloz_titulek(nadpis, sirka_textu):
    """Největší velikost písma, ve které se titulek vejde, a jeho řádky.

    `sirka_textu(velikost)` vrací funkci text → šířka, aby šlo rozložení
    testovat bez Pillow. Na nejmenší velikosti se poslední řádek zkrátí.
    """
    velikosti = list(TITULEK_PISMO)
    for velikost in velikosti:
        radku = int(TITULEK_VYSKA // (velikost * 1.05))
        radky = karta.zalom(nadpis, sirka_textu(velikost), TITULEK_SIRKA, 99)
        if len(radky) <= radku:
            return velikost, radky
    velikost = velikosti[-1]
    radku = int(TITULEK_VYSKA // (velikost * 1.05))
    return velikost, karta.zalom(nadpis, sirka_textu(velikost), TITULEK_SIRKA, radku)


def vytvor(cil, nadpis, stitek, tema, pata):
    """Nakreslí kartu do `cil` (PNG). Vrací True, nebo False bez Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return False

    def pismo(nazev, velikost):
        return ImageFont.truetype(str(PISMA / nazev), velikost)

    obraz = Image.new("RGB", ROZMER, PAPIR)
    k = ImageDraw.Draw(obraz)
    sirka, vyska = ROZMER

    # Pás se značkou a tématem.
    k.rectangle([0, 0, sirka, PAS], fill=ZELENA)
    k.rectangle([0, PAS, sirka, PAS + 8], fill=INKOUST)
    k.text((OKRAJ, PAS / 2), "KROMCL.", font=pismo("Syne-800.ttf", 40),
           fill=INKOUST, anchor="lm")
    if stitek:
        maly = pismo("SpaceGrotesk-700.ttf", 26)
        text = stitek.upper()
        proklad = 26 * 0.1
        delka = sum(maly.getlength(z) for z in text) + proklad * (len(text) - 1)
        x2 = sirka - OKRAJ
        x1 = x2 - delka - 32
        k.rectangle([x1, PAS / 2 - 22, x2, PAS / 2 + 22], fill=INKOUST)
        x = x1 + 16
        for znak in text:
            k.text((x, PAS / 2), znak, font=maly, fill=BILA, anchor="lm")
            x += maly.getlength(znak) + proklad

    # Titulek.
    velikost, radky = rozloz_titulek(
        nadpis, lambda v: pismo("Syne-800.ttf", v).getlength)
    syne = pismo("Syne-800.ttf", velikost)
    for i, radek in enumerate(radky):
        k.text((OKRAJ, TITULEK_Y + i * velikost * 1.05), radek, font=syne,
               fill=INKOUST, anchor="la")

    # Piktogram v rámu s tvrdým stínem.
    x1 = sirka - OKRAJ - RAM
    k.rectangle([x1 + STIN, RAM_Y + STIN, x1 + RAM + STIN, RAM_Y + RAM + STIN], fill=INKOUST)
    k.rectangle([x1, RAM_Y, x1 + RAM, RAM_Y + RAM], fill=BILA, outline=INKOUST, width=6)
    okraj = (RAM - PIKTOGRAM) // 2
    obraz.paste(piktogram(tema, PIKTOGRAM), (x1 + okraj, RAM_Y + okraj))

    if pata:
        k.text((OKRAJ, vyska - 44), pata, font=pismo("SpaceGrotesk-700.ttf", 26),
               fill=INKOUST, anchor="ld")

    cil = Path(cil)
    cil.parent.mkdir(parents=True, exist_ok=True)
    # Paleta 64 barev: karta má čtyři plochy a hrany písma, rozdíl proti
    # plným barvám na pohled není a soubor je třetinový (59 → 20 kB).
    # Karta se kreslí každý build ke každé stránce, u archivu o 700
    # článcích je to rozdíl 40 MB na nasazení.
    obraz.quantize(64, method=Image.Quantize.MEDIANCUT).save(str(cil), optimize=True)
    return True
