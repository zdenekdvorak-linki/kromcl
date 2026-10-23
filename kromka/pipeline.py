# -*- coding: utf-8 -*-
"""Běh: feed → diff → detail → fotka → klasifikace → přepis → uložení."""

import sys
import traceback
from datetime import datetime, timezone

from . import config, net, obrazky, rewrite, sources, store
from .errors import NeresolvovanyClanek


def nove_polozky(limit=None, nejstarsi=False, jen_novejsi=False):
    """Položky ze všech zdrojů, které ještě nemají hotový přepis.

    `jen_novejsi` zahodí všechno starší, než je nejnovější hotový článek.
    Pro cron je to zásadní: bez toho by hodinový běh považoval za „nové" i
    celý nezpracovaný archiv a projel by ho sám během pár dní.
    """
    stav = store.nacti_stav()
    hotove = set(stav.get("zpracovane", []))
    hranice = _nejnovejsi_hotovy() if jen_novejsi else ""
    cekaji = []
    for zdroj in sources.vsechny():
        for polozka in zdroj.fetch_items():
            if polozka["id"] in hotove or store.existuje(polozka["id"]):
                continue
            if hranice and polozka["published"] <= hranice:
                continue
            cekaji.append(polozka)
    cekaji.sort(key=lambda p: p["published"], reverse=not nejstarsi)
    return cekaji[:limit] if limit else cekaji


def _nejnovejsi_hotovy():
    data = [c.get("published", "") for c in store.vsechny()]
    return max(data) if data else ""


def zpracuj(polozka, verbose=True):
    """Jedna položka od detailu po uložený JSON. Vrací článek nebo None."""
    zdroj = sources.podle_id(polozka["source"])
    try:
        zdroj.fetch_detail(polozka)
    except NeresolvovanyClanek:
        _zapis_stav(polozka["id"], neresolvovany=True)
        if verbose:
            print("  bez funkčního odkazu, zahozeno: {0}".format(polozka["title"]))
        return None

    # Když se citlivost nerozlišuje, klasifikátor se vůbec nevolá.
    citlivost = rewrite.klasifikuj(polozka) if config.ROZLISOVAT_CITLIVOST else "volny"
    if citlivost == "vynechat" or (citlivost == "neutralni" and config.SKIP_SENSITIVE):
        _zapis_stav(polozka["id"])
        if verbose:
            print("  přeskočeno ({0}): {1}".format(citlivost, polozka["title"]))
        return None

    data = rewrite.prepis(polozka, citlivost)

    clanek = dict(polozka)
    clanek.update(data)
    clanek["sensitivity"] = citlivost
    clanek["image_local"], clanek["image_w"], clanek["image_h"] = _stahni_obrazek(polozka)
    clanek["rewritten_at"] = datetime.now(timezone.utc).isoformat()
    clanek["model"] = config.MODEL_REWRITE
    store.uloz(clanek)
    _zapis_stav(clanek["id"])
    if verbose:
        print("  hotovo ({0}): {1}".format(citlivost, clanek["headline"]))
    return clanek


def davka(limit, nejstarsi=False, jen_novejsi=False):
    """Zpracuje až `limit` položek. Chyba jedné nezastaví zbytek."""
    polozky = nove_polozky(limit=limit, nejstarsi=nejstarsi, jen_novejsi=jen_novejsi)
    if not polozky:
        print("Nic nového.")
        return []
    print("Ke zpracování: {0}".format(len(polozky)))
    hotove = []
    for polozka in polozky:
        print("- {0}".format(polozka["title"]))
        try:
            clanek = zpracuj(polozka)
            if clanek:
                hotove.append(clanek)
        except Exception as exc:  # noqa: BLE001 - jeden špatný článek nesmí shodit běh
            print("  CHYBA: {0}".format(exc), file=sys.stderr)
            traceback.print_exc(limit=1, file=sys.stderr)
            _zapis_selhani(polozka["id"], str(exc))
    return hotove


def _stahni_obrazek(polozka):
    """Stáhne fotku a uloží ji jako WebP. Vrací (soubor, šířka, výška)."""
    url = polozka.get("image_url")
    if not url:
        return "", 0, 0
    try:
        return obrazky.uloz_webp(net.get(url, binary=True), polozka["slug"])
    except Exception as exc:  # noqa: BLE001 - článek bez fotky je pořád článek
        print("  fotka se nestáhla: {0}".format(exc), file=sys.stderr)
        return "", 0, 0


def _zapis_selhani(article_id, duvod):
    """Spočítá, kolikrát článek spadl. Po MAX_SELHANI se přestane zkoušet.

    Bez tohohle by se vadný článek vracel do fronty při každém běhu cronu a
    platilo by se za něj donekonečna.
    """
    stav = store.nacti_stav()
    selhani = stav.get("selhani", {})
    zaznam = selhani.get(article_id, {"pocet": 0})
    zaznam["pocet"] += 1
    zaznam["duvod"] = duvod[:300]
    selhani[article_id] = zaznam
    stav["selhani"] = selhani
    if zaznam["pocet"] >= config.MAX_SELHANI:
        zpracovane = set(stav.get("zpracovane", []))
        zpracovane.add(article_id)
        stav["zpracovane"] = sorted(zpracovane)
        print("  {0}. selhání, článek se už nebude zkoušet".format(zaznam["pocet"]),
              file=sys.stderr)
    store.uloz_stav(stav)


def _zapis_stav(article_id, neresolvovany=False):
    stav = store.nacti_stav()
    zpracovane = set(stav.get("zpracovane", []))
    zpracovane.add(article_id)
    stav["zpracovane"] = sorted(zpracovane)
    if neresolvovany:
        seznam = set(stav.get("neresolvovane", []))
        seznam.add(article_id)
        stav["neresolvovane"] = sorted(seznam)
    store.uloz_stav(stav)
