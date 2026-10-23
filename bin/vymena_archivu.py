# -*- coding: utf-8 -*-
"""Výměna přegenerovaného archivu za živý.

Bez `--potvrdit` jen vypíše, co by se stalo, a nic nezmění. Kontroly běží
v obou režimech, takže suchý běh je skutečná prověrka, ne jen výpis.

Použití z kořene projektu:

    python bin/vymena_archivu.py                # suchý běh
    python bin/vymena_archivu.py --potvrdit     # provede výměnu
"""

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

KOREN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOREN))

from kromka import htmlutil                         # noqa: E402
from kromka.pipeline import CIZI_POLE, _druh_padu   # noqa: E402

import re                                           # noqa: E402

OTISK = re.compile(r"^[0-9a-f]{16}$")


def preklicuj(stare_id):
    """Starý identifikátor nesoucí slug oznámení převede na otisk.

    Co už otisk je, nechá být — převod musí jít pustit opakovaně, aniž
    by pokaždé vyrobil jiný klíč.
    """
    if ":" not in stare_id:
        return stare_id
    zdroj, zbytek = stare_id.split(":", 1)
    if OTISK.match(zbytek):
        return stare_id
    return htmlutil.klic(zdroj, zbytek)

NOVA = KOREN / "data-cista"
ZIVA = KOREN / "data"
POTVRZENO = "--potvrdit" in sys.argv

# Pole, která v hotovém článku být musí. Chybějící znamená rozbitý zápis.
POVINNA = ("id", "slug", "headline", "tldr", "body", "tags", "published",
           "doklad", "model")


def chyba(zprava):
    print("CHYBA: {0}".format(zprava))
    sys.exit(1)


def nactene_clanky(slozka):
    clanky = {}
    for soubor in sorted((slozka / "articles").glob("*.json")):
        clanky[soubor] = json.loads(soubor.read_text(encoding="utf-8"))
    return clanky


# --- 1. Nic nesmí běžet -----------------------------------------------------
import subprocess                                   # noqa: E402

try:
    vystup = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
         "Where-Object { $_.CommandLine -like '*kromka*' }).Count"],
        capture_output=True, text=True, timeout=60).stdout.strip()
    if vystup not in ("", "0"):
        chyba("ještě běží {0} proces(ů) kromka, výměna by míchala dvě verze".format(vystup))
except (OSError, subprocess.SubprocessError) as exc:
    print("poznámka: běžící procesy se nepodařilo zkontrolovat ({0})".format(exc))

# --- 2. Prověrka nových článků ---------------------------------------------
nove = nactene_clanky(NOVA)
if not nove:
    chyba("v {0} nejsou žádné články".format(NOVA))

slugy = {}
potiz = []
odstranena = []
k_prohlidce = []
for soubor, clanek in nove.items():
    for pole in POVINNA:
        if not clanek.get(pole):
            potiz.append("{0}: chybí {1}".format(soubor.name, pole))
    for pole in CIZI_POLE:
        if clanek.pop(pole, None) is not None:
            odstranena.append("{0}: {1}".format(soubor.name, pole))
    if clanek.get("doklad", {}).get("nejdelsi_shoda_slov", 0) >= 8:
        k_prohlidce.append((soubor.name, clanek))
    if clanek.get("slug") in slugy:
        potiz.append("{0}: slug koliduje s {1}".format(soubor.name, slugy[clanek["slug"]]))
    slugy[clanek.get("slug")] = soubor.name
    if clanek.get("headline", "").rstrip().endswith("."):
        potiz.append("{0}: titulek končí tečkou".format(soubor.name))

if potiz:
    print("Nálezy v nových článcích:")
    for p in potiz:
        print("  -", p)
    chyba("{0} nálezů, výměna se nekoná".format(len(potiz)))

print("Nových článků: {0}, všechny prošly prověrkou.".format(len(nove)))

# --- Čerstvost ------------------------------------------------------------
# `backfill` bere od nejstaršího, takže čistý běh z prázdné evidence
# vyrobí archiv, který končí před rokem a půl. Na zpravodajském webu to
# je horší než chybějící článek, a z počtu článků to poznat není.
nejnovejsi_novy = max(c["published"] for c in nove.values())[:10]
ziva_data = [json.loads(p.read_text(encoding="utf-8"))["published"][:10]
             for p in (ZIVA / "articles").glob("*.json")]
nejnovejsi_zivy = max(ziva_data) if ziva_data else ""
print("Nejnovější článek: nový {0}, živý {1}".format(
    nejnovejsi_novy, nejnovejsi_zivy or "—"))
if nejnovejsi_zivy and nejnovejsi_novy < nejnovejsi_zivy:
    chyba("nový archiv končí dřív než živý ({0} < {1}); web by se tvářil, "
          "že se ve městě půl roku nic nestalo. Doplň nejnovější články "
          "příkazem `python -m kromka run --limit N` a spusť výměnu znovu."
          .format(nejnovejsi_novy, nejnovejsi_zivy))
if odstranena:
    print("Odstraněná cizí pole: {0}".format(len(odstranena)))
    for radek in odstranena:
        print("  -", radek)

# Dlouhá shoda není nutně opsání — pojistka ji propustila proto, že je
# v ní jméno nebo datum. Ale osm a víc slov v řadě si zaslouží, aby to
# člověk viděl, tak se zdroj na tuhle jednu věc dohledá a zahodí.
if k_prohlidce:
    print()
    print("K PROHLÍDNUTÍ: {0} článků má shodu se zdrojem 8+ slov".format(
        len(k_prohlidce)))
    try:
        from kromka import rewrite, sources
        zdroj_obj = sources.vsechny()[0]
        polozky = {p["id"]: p for p in zdroj_obj.fetch_items()}
        for nazev, clanek in k_prohlidce:
            print("  {0}".format(nazev))
            print("    shoda: {0} slov".format(
                clanek["doklad"]["nejdelsi_shoda_slov"]))
            # fetch_items uz vraci otisky, ulozeny clanek jeste stary klic
            polozka = polozky.get(preklicuj(clanek["id"]))
            if polozka is None:
                print("    zdroj uz ve feedu neni, uryvek nedohledam")
                continue
            zdroj_obj.fetch_detail(polozka)
            zdroj = " ".join([polozka["title"]] + (polozka.get("body") or []))
            vystup = " ".join([clanek["headline"]]
                              + [o["text"] for o in clanek["tldr"]]
                              + clanek["body"])
            for kus in rewrite.zkontroluj_opisovani(zdroj, vystup, delka=8):
                print("    hlasila by: {0}".format(kus))
            slova_z = [s.lower() for s in rewrite._SLOVO.findall(zdroj)]
            slova_v = [s.lower() for s in rewrite._SLOVO.findall(vystup)]
            delka = clanek["doklad"]["nejdelsi_shoda_slov"]
            ng_v = {" ".join(slova_v[i:i + delka])
                    for i in range(len(slova_v) - delka + 1)}
            ng_z = {" ".join(slova_z[i:i + delka])
                    for i in range(len(slova_z) - delka + 1)}
            for kus in sorted(ng_z & ng_v):
                print("    uryvek: {0}".format(kus))
    except Exception as exc:                       # noqa: BLE001
        print("    zdroj se nepodarilo dohledat: {0}".format(exc))

# --- 3. Co se zahodí ze stavu ----------------------------------------------
stav_cesta = NOVA / "state.json"
stav = json.loads(stav_cesta.read_text(encoding="utf-8"))
k_zahozeni = []
for aid, zaznam in sorted(stav.get("selhani", {}).items()):
    zkracene = _druh_padu(zaznam.get("duvod", ""))
    if zkracene != zaznam.get("duvod"):
        k_zahozeni.append(aid)
    zaznam["duvod"] = zkracene
print("Důvodů pádu se zkrátí (ať v repu není text zdroje): {0}".format(len(k_zahozeni)))

# --- Překlíčování: identifikátor nesmí nést slug oznámení ------------------
k_prekliceni = sum(1 for c in nove.values() if preklicuj(c["id"]) != c["id"])
print("Článků k překlíčování: {0} z {1}".format(k_prekliceni, len(nove)))

# Evidence zpracovaných se slučuje se živou, jinak by cron považoval
# starý archiv za nový a platil by ho znovu.
ziva_stav = json.loads((ZIVA / "state.json").read_text(encoding="utf-8"))
for klic_seznamu in ("zpracovane", "neresolvovane"):
    slouceno = set(preklicuj(i) for i in stav.get(klic_seznamu, []))
    slouceno |= set(preklicuj(i) for i in ziva_stav.get(klic_seznamu, []))
    stav[klic_seznamu] = sorted(slouceno)
stav["selhani"] = {preklicuj(k): v for k, v in stav.get("selhani", {}).items()}
print("Evidence zpracovaných: {0} živých + {1} nových = {2} po sloučení".format(
    len(ziva_stav.get("zpracovane", [])),
    len(json.loads(stav_cesta.read_text(encoding="utf-8")).get("zpracovane", [])),
    len(stav["zpracovane"])))

log = NOVA / "beh.log"
print("Log běhu se odloží mimo repo: {0}".format("ano" if log.exists() else "není"))

# --- 4. Co zmizí ze živého archivu -----------------------------------------
stare = sorted((ZIVA / "articles").glob("*.json"))
print("Živých článků ke smazání: {0}".format(len(stare)))

if not POTVRZENO:
    print()
    print("Suchý běh. Pro provedení spusť znovu s --potvrdit.")
    sys.exit(0)

# --- 5. Záloha -------------------------------------------------------------
znacka = datetime.now().strftime("%Y%m%d-%H%M%S")
zaloha = KOREN.parent / "Kromcl-zalohy" / znacka
zaloha.mkdir(parents=True, exist_ok=True)
shutil.copytree(ZIVA, zaloha / "data")
print("Záloha živého archivu: {0}".format(zaloha / "data"))

# --- 6. Výměna -------------------------------------------------------------
for soubor in stare:
    os.remove(soubor)
for soubor, clanek in nove.items():
    clanek["id"] = preklicuj(clanek["id"])
    cil = ZIVA / "articles" / (clanek["id"].replace(":", "__") + ".json")
    cil.write_text(json.dumps(clanek, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
(ZIVA / "state.json").write_text(
    json.dumps(stav, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
if log.exists():
    shutil.move(str(log), str(zaloha / "beh.log"))

print("Vyměněno: {0} článků v {1}".format(len(nove), ZIVA / "articles"))
print("Teď spusť: python -m kromka build")
