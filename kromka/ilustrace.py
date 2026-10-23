# -*- coding: utf-8 -*-
"""Obrázky v těle článku: karty s čísly a ikony u odstavců.

Holý text pod TL;DR působil chudě. Obrázky se tady skládají z hotového
přepisu, ne z nového pole od modelu, a z toho plynou dvě vlastnosti:

- Platí pro celý archiv hned. Přepis se znovu negeneruje (princip 5), takže
  cokoli, co by potřebovalo nové pole, by vidělo jen pár nových článků.
- Nepřidává fakt (princip 2). Karta ukazuje číslo, které v textu doslova
  stojí; popisek je obecný druh („peníze", „plocha", „kdy"), ne tvrzení
  o tom, k čemu číslo patří. Ikona je jen kresba podle slova v odstavci.
"""

import html
import re

from . import piktogramy

_MESICE = {  # 6. pád, jak ho píše text („v listopadu") → 1. pád na kartu
    "lednu": "leden", "únoru": "únor", "březnu": "březen", "dubnu": "duben",
    "květnu": "květen", "červnu": "červen", "červenci": "červenec",
    "srpnu": "srpen", "září": "září", "říjnu": "říjen",
    "listopadu": "listopad", "prosinci": "prosinec",
}
_MESIC = r"\b[vV] (" + "|".join(_MESICE) + r")\b"  # i „V listopadu" na začátku věty
_GENITIV = ("ledna", "února", "března", "dubna", "května", "června", "července",
            "srpna", "září", "října", "listopadu", "prosince")
_DATUM = re.compile(r"\b(\d{1,2})\. (" + "|".join(_GENITIV) + r")\b")

# Číslo s tisícovou mezerou nebo tečkou a desetinnou čárkou: 390, 53 245,
# 53.245, 1,2. Tečka před tisíci je zvyk zdroje a přepis ji občas převezme.
_CISLO = r"(\d{1,3}(?:[ \u00a0.]\d{3})+|\d+)(?:,(\d+))?"
_PENIZE = re.compile(_CISLO + r"\s*(tisíc\w*|milion\w*|miliard\w*)?\s*(?:korun\w*|Kč)(?!\w)")
_PLOCHA = re.compile(_CISLO + r"\s*(?:m²|m2|metrů čtverečních|čtverečních metrů)(?!\w)")
_RAD = [("tisíc", "tis."), ("miliard", "mld."), ("milion", "mil.")]

# Ikona u odstavce. Pořadí rozhoduje: odstavec dostane první téma, které
# v něm najde a které v článku ještě nebylo. Radnice a lidé jsou na konci,
# protože se objevují skoro všude a jinak by přebily všechno konkrétní.
_IKONY = [
    ("penize", r"\bkorun|\bkč\b|rozpoč|dotac|zaplat|investic|peně[zž]|financ"),
    ("sport", r"hřiš|sport|cvič|bazén|stadion|workout|zápas|turnaj"),
    ("doprava", r"autobus|parkov|silnic|doprav|chodník|cyklo|semafor|křižovat|zastávk"),
    # Ne „staví" a „postav" bez koncovky: „staví se u dveří", „postava z příběhu".
    ("stavba", r"\bstavb|\bstavě[tl]|\bstavebn|rekonstruk|\boprav[iuy]|"
               r"\bpostav(?:í|il|ět|en)|staveniš|terén"),
    ("skolstvi", r"škol|žák|student|učitel"),
    ("priroda", r"\bstrom|\bzahrad|zeleň|\bpark(?:u|y|em|ů|ech)?\b|přírod"),
    ("kultura", r"koncert|divadl|výstav|kultur|muze"),
    ("volby", r"volb|volič"),
    ("akce", _MESIC),
    ("radnice", r"zastupitel|radnic|rada města"),
    ("lide", r"lidé|obyvatel|občan|starost"),
]
_IKONY = [(t, re.compile(rx, re.IGNORECASE)) for t, rx in _IKONY]


def _cislo_text(cele, desetiny):
    cele = re.sub(r"[ \u00a0.]", "\u00a0", cele)
    return cele + ("," + desetiny if desetiny else "")


def karty(odstavce):
    """Seznam karet (tvar, hodnota, jednotka, popisek, plocha_m2) v pořadí textu.

    Od každého druhu nejvýš jedna, první výskyt. Jednotka jde na kartu menším
    písmem, jinak se „11,76 mil. Kč" v širokém Syne do třetiny sloupce nevejde.
    `plocha_m2` je celé číslo do 100 jen u plochy, kde se dá nakreslit
    mřížka; jinak None.
    """
    text = " ".join(odstavce)
    nalezy = []
    m = _PENIZE.search(text)
    if m:
        slovo = (m.group(3) or "").lower()
        rad = next((zkr for zac, zkr in _RAD if slovo.startswith(zac)), "")
        jednotka = (rad + "\u00a0" if rad else "") + "Kč"
        nalezy.append((m.start(), ("penize", _cislo_text(m.group(1), m.group(2)), jednotka,
                                   "peníze", None)))
    m = _PLOCHA.search(text)
    if m:
        cele = re.sub(r"\D", "", m.group(1))
        mrizka = int(cele) if not m.group(2) and int(cele) <= 100 else None
        nalezy.append((m.start(), ("plocha", _cislo_text(m.group(1), m.group(2)), "m²",
                                   "plocha", mrizka)))
    # „Kdy" je jedna karta: buď konkrétní datum, nebo měsíc, co je v textu dřív.
    # Datum má obyčejnou mezeru, ať se „17. března" v úzké kartě smí zalomit.
    kdy = [(m.start(), "{0}. {1}".format(m.group(1), m.group(2))) for m in [_DATUM.search(text)] if m]
    kdy += [(m.start(), _MESICE[m.group(1)]) for m in [re.search(_MESIC, text)] if m]
    if kdy:
        pozice, hodnota = min(kdy)
        nalezy.append((pozice, ("akce", hodnota, "", "kdy", None)))
    return [k for _, k in sorted(nalezy, key=lambda n: n[0])]


def karty_html(odstavce):
    """Blok karet, nebo prázdný řetězec, když v textu žádné číslo není.

    Samotná karta jde na celou šířku s ikonou vedle čísla. Pravidlo „aspoň
    dvě" dávalo karty jen 7 článkům z 64, s jednou kartou a daty 48.
    """
    seznam = karty(odstavce)
    if not seznam:
        return ""
    vystup = []
    for tvar, hodnota, jednotka, popisek, mrizka in seznam:
        navic = ""
        if mrizka:
            navic = '<span class="ilu-mrizka" aria-hidden="true">{0}</span>'.format(
                "".join('<i class="plne"></i>' if i < mrizka else "<i></i>" for i in range(100)))
        vystup.append('<div class="ilu-cislo ilu-{t}{s}">{svg}<span class="ilu-text"><b>{h}{j}</b>'
                      '<span class="ilu-popis">{p}</span></span>{n}</div>'.format(
            t=tvar, s=" ilu-s-mrizkou" if mrizka else "",
            svg=piktogramy.svg(tvar), h=html.escape(hodnota),
            j="<small>\u00a0{0}</small>".format(html.escape(jednotka)) if jednotka else "",
            p=html.escape(popisek), n=navic))
    return '<div class="ilu-cisla{0}">{1}</div>'.format(
        " ilu-jedna" if len(seznam) == 1 else "", "".join(vystup))


def ikony(odstavce):
    """Téma ikony ke každému odstavci (nebo None). V článku se neopakují."""
    pouzite, vystup = set(), []
    for odstavec in odstavce:
        tema = next((t for t, rx in _IKONY if t not in pouzite and rx.search(odstavec)), None)
        if tema:
            pouzite.add(tema)
        vystup.append(tema)
    return vystup


def ikona_html(tema):
    if not tema:
        return ""
    return '<span class="ilu-ikona">{0}</span>'.format(piktogramy.svg(tema))
