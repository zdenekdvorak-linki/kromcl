# -*- coding: utf-8 -*-
"""Příspěvky čtenářů: Google Form → moderace v tabulce → přepis → článek.

Čtenář pošle novinku formulářem na /poslat-novinku.html. Odpověď skončí
v tabulce, kde ji redakce schválí nebo zamítne sloupcem Stav. Apps Script
u tabulky (`apps-script/prispevky.gs`) vrací jen řádky ve stavu „schváleno"
a „stáhnout", a to bez e-mailu — ten zůstává v tabulce pro doplňující
otázky a do veřejného repa se nikdy nedostane.

Záměrně mimo `sources/`, stejně jako `akce.py` a `pozvanka.py`: registr
zdrojů čeká feed s URL detailu a `pipeline.nove_polozky` by příspěvek
poslal do přepisu jako oznámení radnice.

Pravdou o stavu je tabulka, ne `state.json`. Chyba pojistky se zapíše zpátky
jako „chyba" a druh pádu; redakce může text v tabulce opravit a dát znovu
„schváleno". Automatické opakování proto není potřeba.
"""

import hashlib
import json
import sys
from datetime import datetime, timezone

from . import config, htmlutil, net, rewrite, store

ZDROJ = "ctenar"

SCHVALENO = "schváleno"
STAHNOUT = "stáhnout"
PUBLIKOVANO = "publikováno"
STAZENO = "staženo"
CHYBA = "chyba"

# Jeden příspěvek je jedno volání modelu. Strop drží účet v mezích, i kdyby
# redakce schválila dávku najednou; zbytek vezme další hodinový běh.
MAX_ZA_BEH = 5

# Delší text by jen pálil tokeny; novinka se vejde do pár odstavců.
MAX_ZNAKU = 6000


def zapnuto():
    return bool(config.PRISPEVKY_SOUBOR or (config.PRISPEVKY_URL and config.PRISPEVKY_KLIC))


def nacti():
    """Řádky ke zpracování: [{id, cas, jmeno, nadpis, text, odkaz, stav}]."""
    if config.PRISPEVKY_SOUBOR:
        with open(config.PRISPEVKY_SOUBOR, encoding="utf-8") as f:
            return json.load(f).get("radky", [])
    odpoved = net.post_json(config.PRISPEVKY_URL,
                            {"klic": config.PRISPEVKY_KLIC, "akce": "nacti"})
    if not odpoved.get("ok"):
        raise RuntimeError("Endpoint příspěvků odmítl čtení: {0}".format(odpoved.get("chyba")))
    return odpoved.get("radky", [])


def zapis_stav(radek_id, stav, odkaz="", poznamka=""):
    """Zapíše výsledek zpátky do tabulky. Chyba zápisu běh neshodí."""
    if config.PRISPEVKY_SOUBOR:
        print("  [tabulka] {0}: {1} {2} {3}".format(radek_id, stav, odkaz, poznamka).rstrip())
        return True
    try:
        odpoved = net.post_json(config.PRISPEVKY_URL, {
            "klic": config.PRISPEVKY_KLIC, "akce": "stav", "id": radek_id,
            "stav": stav, "odkaz": odkaz, "poznamka": poznamka})
        return bool(odpoved.get("ok"))
    except Exception as exc:                          # noqa: BLE001
        print("  stav příspěvku se nezapsal ({0})".format(exc), file=sys.stderr)
        return False


def id_pro(radek):
    """Otisk časové značky odpovědi. Stabilní a z adresy nic neprozradí."""
    otisk = hashlib.sha1(str(radek["id"]).encode("utf-8")).hexdigest()[:16]
    return "{0}:{1}".format(ZDROJ, otisk)


def cesta_clanku(clanek):
    return "/clanek/{0}.html".format(clanek["slug"])


def bezpecny_odkaz(odkaz):
    """Jen http a https. Cokoli jiného (javascript:, mailto:) se zahodí."""
    odkaz = (odkaz or "").strip()
    return odkaz if odkaz.lower().startswith(("http://", "https://")) and " " not in odkaz else ""


def _odstavce(text):
    radky = [r.strip() for r in (text or "")[:MAX_ZNAKU].replace("\r", "").split("\n")]
    return [r for r in radky if r]


def _ted():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Prague")).isoformat(timespec="seconds")
    except Exception:                                 # noqa: BLE001
        return datetime.now(timezone.utc).isoformat(timespec="seconds")


def napis(radek):
    """Přepíše jeden schválený řádek a uloží článek. Vrací článek."""
    from . import pipeline

    jmeno = (radek.get("jmeno") or "").strip()
    nadpis = (radek.get("nadpis") or "").strip()
    odstavce = _odstavce(radek.get("text"))
    if not (jmeno and nadpis and odstavce):
        raise ValueError("Chybí jméno, nadpis nebo text")

    published = _ted()
    data = rewrite.prepis_prispevku(
        {"title": nadpis, "body": odstavce, "published": published})
    clanek_id = id_pro(radek)
    # Jen vyjmenovaná pole. Cokoli dalšího z tabulky (e-mail, souhlas,
    # časová značka) do veřejného archivu nepatří, i kdyby ho endpoint poslal.
    clanek = {
        "id": clanek_id,
        "typ": "prispevek",
        "source": ZDROJ,
        "source_name": config.BRAND,
        "slug": pipeline._volny_slug(htmlutil.slugify(data["headline"])[:80], clanek_id),
        "headline": data["headline"],
        "tldr": data["tldr"],
        "body": data["body"],
        "tags": data.get("tags") or ["lidé"],
        "autor": jmeno[:80],
        "odkaz": bezpecny_odkaz(radek.get("odkaz")),
        "published": published,
        "rewritten_at": datetime.now(timezone.utc).isoformat(),
        "model": "stub" if config.BACKEND == "stub" else config.MODEL_REWRITE,
        "sensitivity": "volny",
    }
    store.uloz(clanek)
    return clanek


def stahni(clanek_id):
    """Smaže článek z archivu. Web ho při dalším buildu nevykreslí.

    Repozitář je veřejný, v historii gitu text zůstane. Z webu, ze sitemapy
    a z feedu zmizí hned.
    """
    cesta = store._cesta(clanek_id)
    if cesta.exists():
        cesta.unlink()
        return True
    return False


def v_cronu(verbose=True):
    """Volá `all`. Vrací nově publikované články. Výpadek nic neshodí."""
    from . import pipeline

    if not zapnuto():
        return []
    try:
        radky = nacti()
    except Exception as exc:                          # noqa: BLE001
        print("Příspěvky se nepodařilo načíst ({0}).".format(exc), file=sys.stderr)
        return []

    nove = []
    for radek in radky:
        stav = (radek.get("stav") or "").strip().lower()
        if "id" not in radek:
            continue
        clanek_id = id_pro(radek)

        if stav == STAHNOUT:
            if stahni(clanek_id) and verbose:
                print("  příspěvek stažen: {0}".format(radek.get("nadpis", "")))
            zapis_stav(radek["id"], STAZENO)
            continue
        if stav != SCHVALENO:
            continue

        # Princip 5: hotový přepis se negeneruje znovu. Jen se srovná stav,
        # kdyby se minule nepovedl zápis do tabulky.
        if store.existuje(clanek_id):
            hotovy = store.nacti(clanek_id)
            zapis_stav(radek["id"], PUBLIKOVANO, _abs(cesta_clanku(hotovy)))
            continue
        if len(nove) >= MAX_ZA_BEH:
            continue
        try:
            clanek = napis(radek)
        except Exception as exc:                      # noqa: BLE001
            print("  příspěvek neprošel: {0}".format(exc), file=sys.stderr)
            zapis_stav(radek["id"], CHYBA, poznamka=pipeline._druh_padu(str(exc)))
            continue
        nove.append(clanek)
        zapis_stav(radek["id"], PUBLIKOVANO, _abs(cesta_clanku(clanek)))
        if verbose:
            print("  příspěvek hotov: {0}".format(clanek["headline"]))
    return nove


def _abs(cesta):
    return config.SITE_URL.rstrip("/") + cesta
