# -*- coding: utf-8 -*-
"""Převod fotek do WebP.

Město posílá JPEG kolem 350 kB. Při celém archivu je to čtvrt giga v gitu
i v Dropboxu a hlavně na mobilních datech čtenáře. WebP to srazí řádově
na pětinu bez viditelné ztráty.

Rozměry se ukládají do článku, aby se daly zapsat do <img width height>.
Bez nich prohlížeč neví, kolik místa fotce nechat, a stránka při načítání
poskakuje (Cumulative Layout Shift, jeden z Core Web Vitals).
"""

import io

from . import config

# 1600 px stačí na retina displeje i na og:image (doporučená šířka 1200).
MAX_SIRKA = 1600
KVALITA = 82


def uloz_webp(data, nazev_bez_pripony):
    """Bajty obrázku → WebP v data/images. Vrací (soubor, šířka, výška)."""
    from PIL import Image

    config.IMAGES.mkdir(parents=True, exist_ok=True)
    obrazek = Image.open(io.BytesIO(data))

    # EXIF orientace: bez tohohle se fotky z mobilu otočí naležato.
    try:
        from PIL import ImageOps
        obrazek = ImageOps.exif_transpose(obrazek)
    except Exception:  # noqa: BLE001 - chybějící EXIF není důvod přijít o fotku
        pass

    if obrazek.mode not in ("RGB", "RGBA"):
        obrazek = obrazek.convert("RGB")
    if obrazek.width > MAX_SIRKA:
        vyska = int(round(obrazek.height * MAX_SIRKA / float(obrazek.width)))
        obrazek = obrazek.resize((MAX_SIRKA, vyska), Image.LANCZOS)

    nazev = nazev_bez_pripony + ".webp"
    obrazek.save(str(config.IMAGES / nazev), "WEBP", quality=KVALITA, method=6)
    return nazev, obrazek.width, obrazek.height
