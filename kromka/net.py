# -*- coding: utf-8 -*-
"""Stahování přes stdlib. Žádné requests, ať se v GitHub Actions nic neinstaluje."""

import time
import urllib.error
import urllib.request

from . import config


def get(url, binary=False):
    """Stáhne URL. Vrací str (utf-8) nebo bytes. Při chybě zkouší znovu."""
    last = None
    for pokus in range(config.HTTP_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": config.USER_AGENT})
            with urllib.request.urlopen(req, timeout=config.HTTP_TIMEOUT) as resp:
                raw = resp.read()
                return raw if binary else raw.decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            # 404 ani 403 se opakováním nespraví, nemá smysl čekat.
            if 400 <= exc.code < 500:
                raise RuntimeError("{0} vrátilo {1}".format(url, exc.code))
            last = exc
            if pokus < config.HTTP_RETRIES - 1:
                time.sleep(2 ** pokus)
        except (urllib.error.URLError, OSError) as exc:
            last = exc
            if pokus < config.HTTP_RETRIES - 1:
                time.sleep(2 ** pokus)
    raise RuntimeError("Nepodařilo se stáhnout {0}: {1}".format(url, last))


def post_json(url, data):
    """Pošle JSON a vrátí odpověď jako JSON. Bez opakování: zápis stavu
    zopakovaný naslepo by mohl udělat dvakrát totéž.

    Apps Script odpovídá přesměrováním na googleusercontent.com; urllib ho
    následuje jako GET, a tam je výsledek skriptu.
    """
    import json

    req = urllib.request.Request(
        url, data=json.dumps(data).encode("utf-8"), method="POST",
        headers={"User-Agent": config.USER_AGENT, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=config.HTTP_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def exists(url):
    """True, když URL vrací 2xx. Používá se na ověření odvozeného slugu."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": config.USER_AGENT})
        with urllib.request.urlopen(req, timeout=config.HTTP_TIMEOUT) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False
