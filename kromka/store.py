# -*- coding: utf-8 -*-
"""Úložiště. Jeden článek = jeden JSON v data/articles, verzovaný v gitu.

Hotový přepis se nikdy nepřepisuje znovu — jednou zaplacený token se podruhé
neplatí a archiv zůstává stabilní.
"""

import json

from . import config


def _cesta(article_id):
    return config.ARTICLES / (article_id.replace(":", "__") + ".json")


def existuje(article_id):
    return _cesta(article_id).exists()


def nacti(article_id):
    with _cesta(article_id).open(encoding="utf-8") as f:
        return json.load(f)


def uloz(clanek):
    config.ARTICLES.mkdir(parents=True, exist_ok=True)
    cesta = _cesta(clanek["id"])
    with cesta.open("w", encoding="utf-8") as f:
        json.dump(clanek, f, ensure_ascii=False, indent=2, sort_keys=True)
    return cesta


def vsechny():
    """Všechny hotové články, od nejnovějšího."""
    if not config.ARTICLES.exists():
        return []
    clanky = []
    for cesta in config.ARTICLES.glob("*.json"):
        with cesta.open(encoding="utf-8") as f:
            clanky.append(json.load(f))
    clanky.sort(key=lambda c: c.get("published", ""), reverse=True)
    return clanky


def nacti_stav():
    if not config.STATE_FILE.exists():
        return {"zpracovane": []}
    with config.STATE_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def uloz_stav(stav):
    config.DATA.mkdir(parents=True, exist_ok=True)
    with config.STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(stav, f, ensure_ascii=False, indent=2, sort_keys=True)
