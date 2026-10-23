# -*- coding: utf-8 -*-
"""Jediné místo, kde se mění značka, cesty, modely a bezpečnostní pravidla."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _nacti_env(cesta):
    """Přečte .env vedle projektu: řádky KLIC=hodnota, # je komentář.

    Skutečné prostředí má přednost, aby se dalo v GitHub Actions a při
    zkušebním běhu přepsat cokoliv bez sahání do souboru.
    """
    if not cesta.exists():
        return
    for radek in cesta.read_text(encoding="utf-8").splitlines():
        radek = radek.strip()
        if not radek or radek.startswith("#") or "=" not in radek:
            continue
        klic, hodnota = radek.split("=", 1)
        os.environ.setdefault(klic.strip(), hodnota.strip().strip('"').strip("'"))


_nacti_env(ROOT / ".env")

# --- Značka ---------------------------------------------------------------
# Změna názvu webu = změna těchhle pěti řádků, nic jiného.
BRAND = "KROMCL"
TAGLINE = "Kroměříž bez filtru"
SITE_URL = os.environ.get("KROMKA_SITE_URL", "https://kromcl.cz")
LOCALE = "cs_CZ"
ACCENT = "#39E67A"  # signální zelená, používá se jen na akcenty

# --- Cesty ----------------------------------------------------------------
# KROMKA_DATA a KROMKA_SITE se dají přesměrovat jinam, aby zkušební běh
# (BACKEND=stub) nesahal na ostrý archiv.
DATA = Path(os.path.expanduser(os.environ.get("KROMKA_DATA", str(ROOT / "data"))))
ARTICLES = DATA / "articles"
IMAGES = DATA / "images"
STATE_FILE = DATA / "state.json"
AKCE_FILE = DATA / "akce.json"
KINO_CACHE = DATA / "kino-dk.json"
SITE = Path(os.path.expanduser(os.environ.get("KROMKA_SITE", str(ROOT / "site"))))

# --- Akce -----------------------------------------------------------------
# Otevřená data města. Na rozdíl od zpráv je tahle sada pod licencí, která
# doslovné převzetí dovoluje výměnou za uvedení zdroje — proto se fakta
# nepřepisují a atribuce je povinná na každé stránce, která je zobrazuje.
AKCE_EXPORT = "https://opendata.mesto-kromeriz.cz/akce/export/export-xml"
AKCE_SPECIFIKACE = "https://opendata.mesto-kromeriz.cz/akce/specifikace/"
AKCE_POSKYTOVATEL = "Město Kroměříž"
AKCE_LICENCE = "CC BY 4.0"
AKCE_LICENCE_URL = "https://creativecommons.org/licenses/by/4.0/deed.cs"
AKCE_DNI = 30

# Hodinový cron nesmí tahat 574 kB pokaždé. Bez --vynutit se stahování
# přeskočí, dokud jsou uložená data mladší.
AKCE_MAX_STARI_HODIN = 12

# --- Modely ---------------------------------------------------------------
# Klasifikace je jednoslovná odpověď, stačí nejlevnější model.
MODEL_CLASSIFY = os.environ.get("KROMKA_MODEL_CLASSIFY", "claude-haiku-5-5")
MODEL_REWRITE = os.environ.get("KROMKA_MODEL_REWRITE", "claude-sonnet-5-5")

# Model utratí část rozpočtu za přemýšlení, takže limit musí být výrazně větší
# než samotný JSON. Na 2000 se odpověď usekávala uprostřed řetězce.
# I jednoslovná odpověď potřebuje rozpočet na přemýšlení, u citlivých textů
# ho model spotřebuje nejvíc. Na 64 se klasifikace usekávala.
MAX_TOKENS_CLASSIFY = 1024
MAX_TOKENS_REWRITE = 8000

# "api" = Anthropic SDK + ANTHROPIC_API_KEY (jediné, co jede v GitHub Actions).
# "cli" = claude --print na předplatném, zadarmo, ale jen na přihlášeném stroji.
BACKEND = os.environ.get("KROMKA_BACKEND", "api")

# Jen pro klíč založený na úrovni organizace. Klíč vytvořený uvnitř workspace
# si workspace nese sám a tohle zůstane prázdné.
WORKSPACE_ID = os.environ.get("ANTHROPIC_WORKSPACE_ID", "")
CLAUDE_BIN = os.environ.get(
    "KROMKA_CLAUDE_BIN", str(Path.home() / ".local" / "bin" / "claude"))

# --- Chování --------------------------------------------------------------
HTTP_TIMEOUT = 30
HTTP_RETRIES = 3
USER_AGENT = "KromkaBot/1.0 (+{0}; prepis zprav mesta do jazyka mladych)".format(SITE_URL)

# False = všechno jede stejným tónem a klasifikace se vůbec nevolá.
# True = citlivá témata jedou neutrálně (a se SKIP_SENSITIVE úplně vypadnou).
# Rozhodnutí Zdeňka 23. 10. 2026: web je celý v nadsázce, město o negativních
# událostech píše samo a my jen měníme jazyk. Vráceno zpět = jediný řádek.
ROZLISOVAT_CITLIVOST = os.environ.get("KROMKA_CITLIVOST", "0") == "1"

# Uplatní se jen když ROZLISOVAT_CITLIVOST je True.
SKIP_SENSITIVE = False

# Kolik článků se vejde na úvodní stránku, než se stránkuje.
PAGE_SIZE = 30

# Web města má v patičce: „Všechna práva vyhrazena - použití obsahu nebo jeho
# části je možné pouze se souhlasem města Kroměříž." Souhlas nemáme, takže se
# cizí fotky nestahují ani nezobrazují. Nepřepínat bez písemného souhlasu.
CIZI_FOTKY = False

# Veřejná kontaktní adresa pro opravy a stížnosti. Dokud je prázdná,
# stránka „Jak to děláme" kontakt nenabízí — a tím web přichází o nejlevnější
# pojistku vůbec: možnost vyřešit spor mailem místo právníkem.
KONTAKT = os.environ.get("KROMKA_KONTAKT", "")

# Veřejný repozitář. Kód pojistek i naměřené hodnoty si může kdokoli ověřit,
# což je silnější doklad než jakékoli prohlášení na webu.
REPOZITAR = "https://github.com/zdenekdvorak-linki/kromcl"

# Kolikrát se smí článek pokusit zpracovat napříč běhy, než se vzdáme.
# Chrání před nekonečným placeným opakováním vadné položky v cronu.
MAX_SELHANI = 3

# --- Atribuce -------------------------------------------------------------
DISCLAIMER = (
    "Zpravodajství o Kroměříži pro mladé duchem i jazykem. Co se ve městě "
    "děje, si přečteme, ověříme a převyprávíme po svém."
)
