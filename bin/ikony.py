# -*- coding: utf-8 -*-
"""Vyrobí ikony webu do `static/` z geometrie v `kromka/znacka.py`.

Pouští se ručně po změně značky, výsledek se commituje:

    python bin/ikony.py

Build webu ikony jen kopíruje. Kdyby je kreslil sám, potřeboval by Pillow
na každém stroji, kde se staví — v GitHub Actions ho máme, ale build má jít
i bez něj.
"""

import sys
from pathlib import Path

KOREN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOREN))

from kromka import znacka                            # noqa: E402

CIL = KOREN / "static"


def main():
    CIL.mkdir(parents=True, exist_ok=True)

    (CIL / "favicon.svg").write_text(znacka.svg(), encoding="utf-8")

    # ICO pro prohlížeče a roboty, kteří si o /favicon.ico řeknou sami.
    # Každá velikost se kreslí zvlášť; zmenšená z velké by v 16 px rozmazala.
    velikosti = [16, 32, 48]
    obrazy = [znacka.png(v) for v in velikosti]
    obrazy[-1].save(CIL / "favicon.ico", format="ICO",
                    sizes=[(v, v) for v in velikosti],
                    append_images=obrazy[:-1])

    # iPhone a iPad si roh zaoblí samy, dlaždice může jít do kraje.
    znacka.png(180).save(CIL / "apple-touch-icon.png", optimize=True)

    # Instalovaná aplikace: běžné ikony a maskovatelná pro Android.
    znacka.png(192).save(CIL / "icon-192.png", optimize=True)
    znacka.png(512).save(CIL / "icon-512.png", optimize=True)
    znacka.png(512, meritko=znacka.MERITKO_MASKY).save(
        CIL / "icon-maskable-512.png", optimize=True)

    for soubor in sorted(CIL.glob("*")):
        if soubor.suffix in (".svg", ".ico", ".png"):
            print("  {0:<24} {1:>6} B".format(soubor.name, soubor.stat().st_size))


if __name__ == "__main__":
    main()
