# -*- coding: utf-8 -*-
"""Stáhne fonty Syne a Space Grotesk, aby web nemusel volat Google.

Pouští se ručně jednou, výsledek se commituje:

    python bin/fonty.py

Proč u sebe a ne z Google Fonts: prohlížeč by při každém načtení poslal
Googlu IP adresu čtenáře (v Německu za to soud v roce 2022 přiznal
odškodné), web by čekal na dvě cizí spojení navíc a service worker by cizí
font offline neměl. Oba fonty jsou pod licencí SIL OFL 1.1, která šíření
dovoluje, pokud licence jde s nimi — proto se stahuje i OFL.txt.

Vyrobí:
  static/fonts/*.woff2      pro web, latinka a latinka rozšířená (čeština)
  static/fonts/OFL-*.txt    licence vedle fontů, které se servírují
  kromka/pisma/*.ttf        pro víkendovou kartu; Pillow woff2 neumí
  kromka/pisma/OFL-*.txt    licence vedle TTF
  kromka/pisma/fonty.css    @font-face s rozsahy znaků od Googlu
"""

import re
import sys
import urllib.request
from pathlib import Path

KOREN = Path(__file__).resolve().parent.parent
WEB = KOREN / "static" / "fonts"
PISMA = KOREN / "kromka" / "pisma"

# Google posílá podle User-Agenta: modernímu prohlížeči woff2 po
# podmnožinách znaků, staršímu statické TTF po řezech.
UA_WOFF2 = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
UA_TTF = "curl/8"

CSS_WEB = ("https://fonts.googleapis.com/css2?family=Syne:wght@700;800"
           "&family=Space+Grotesk:wght@400;500;700&display=swap")
CSS_TTF = ("https://fonts.googleapis.com/css2?family=Syne:wght@700;800"
           "&family=Space+Grotesk:wght@500;700")
LICENCE = {
    "syne": "https://raw.githubusercontent.com/google/fonts/main/ofl/syne/OFL.txt",
    "spacegrotesk": "https://raw.githubusercontent.com/google/fonts/main/ofl/spacegrotesk/OFL.txt",
}
# Rozsah vah, který proměnný font na webu pokrývá.
VAHY = {"Syne": "700 800", "Space Grotesk": "400 700"}
PODMNOZINY = ("latin-ext", "latin")


def stahni(url, ua=UA_WOFF2):
    pozadavek = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(pozadavek, timeout=30) as odpoved:
        return odpoved.read()


def slug(rodina):
    return rodina.lower().replace(" ", "-")


def main():
    WEB.mkdir(parents=True, exist_ok=True)
    PISMA.mkdir(parents=True, exist_ok=True)

    # --- woff2 pro web -----------------------------------------------------
    css = stahni(CSS_WEB).decode("utf-8")
    pravidla, hotove = [], set()
    for podmn, telo in re.findall(r"/\* ([a-z-]+) \*/\s*@font-face \{(.*?)\}", css, re.S):
        if podmn not in PODMNOZINY:
            continue
        rodina = re.search(r"font-family: '([^']+)'", telo).group(1)
        url = re.search(r"url\(([^)]+)\)", telo).group(1)
        rozsah = re.search(r"unicode-range: ([^;]+);", telo).group(1)
        nazev = "{0}-{1}.woff2".format(slug(rodina), podmn)
        if nazev in hotove:
            continue          # proměnný font: všechny váhy jsou v jednom souboru
        hotove.add(nazev)
        (WEB / nazev).write_bytes(stahni(url))
        pravidla.append(
            "@font-face {{ font-family: '{0}'; font-style: normal; "
            "font-weight: {1}; font-display: swap; "
            "src: url(/fonts/{2}) format('woff2'); unicode-range: {3}; }}".format(
                rodina, VAHY[rodina], nazev, rozsah))
    (PISMA / "fonty.css").write_text(
        "/* Vygenerováno bin/fonty.py, ručně neupravovat. */\n"
        + "\n".join(pravidla) + "\n", encoding="utf-8")

    # --- TTF pro kartu ----------------------------------------------------
    css = stahni(CSS_TTF, UA_TTF).decode("utf-8")
    for rodina, vaha, url in re.findall(
            r"font-family: '([^']+)'.*?font-weight: (\d+).*?url\(([^)]+)\)", css, re.S):
        (PISMA / "{0}-{1}.ttf".format(rodina.replace(" ", ""), vaha)).write_bytes(
            stahni(url, UA_TTF))

    # --- licence ----------------------------------------------------------
    for jmeno, url in LICENCE.items():
        text = stahni(url)
        (WEB / "OFL-{0}.txt".format(jmeno)).write_bytes(text)
        (PISMA / "OFL-{0}.txt".format(jmeno)).write_bytes(text)

    for slozka in (WEB, PISMA):
        for soubor in sorted(slozka.iterdir()):
            print("  {0:<42} {1:>7} B".format(
                str(soubor.relative_to(KOREN)).replace("\\", "/"), soubor.stat().st_size))


if __name__ == "__main__":
    sys.exit(main())
