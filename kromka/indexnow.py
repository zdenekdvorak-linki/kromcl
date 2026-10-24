# -*- coding: utf-8 -*-
"""IndexNow: po nasazení řekne Bingu a Seznamu, že vyšel nový článek.

Bez toho čekají, až na web samy přijdou, a zpráva o zítřejší uzavírce se do
výsledků dostane pozdě. Jedno odeslání na `api.indexnow.org` se sdílí mezi
všemi zapojenými vyhledávači; Google IndexNow nepodporuje, ten má sitemapu.

Hlásí se jen to, co se opravdu změnilo (rozhodnuto 24. 10. 2026): nový
článek, úvodka a stránky jeho témat. Hodinové přestavby programu ne, to by
vyhledávače braly jako spam.

Build a nasazení jsou ve workflow dva kroky, takže `all` adresy jen zařadí
do fronty vedle složky webu a `python -m kromka indexnow` je odešle až po
nasazení. Klíč je veřejný z povahy věci: leží v kořeni webu jako
`<klíč>.txt` a vyhledávač podle něj ověří, že hlášení přišlo od majitele.
"""

import json
import urllib.error
import urllib.request
from urllib.parse import urlparse

from . import config

# Limit jednoho požadavku podle protokolu.
MAX_ADRES = 10000


def _fronta():
    return config.SITE.parent / "indexnow-fronta.txt"


def adresy(clanky):
    """Adresy, které se novým článkem změnily, bez opakování."""
    from .render import _abs, _tema_cesta

    vysledek = [_abs("/")]
    for clanek in clanky:
        vysledek.append(_abs("/clanek/{0}.html".format(clanek["slug"])))
        vysledek.extend(_abs(_tema_cesta(t)) for t in clanek.get("tags", []))
    return list(dict.fromkeys(vysledek))


def zarad(nove):
    """Přidá adresy do fronty. Fronta přežije neúspěšné odeslání."""
    if not nove:
        return 0
    cesta = _fronta()
    stare = cesta.read_text(encoding="utf-8").split() if cesta.exists() else []
    vsechny = list(dict.fromkeys(stare + list(nove)))
    cesta.parent.mkdir(parents=True, exist_ok=True)
    cesta.write_text("\n".join(vsechny) + "\n", encoding="utf-8")
    return len(vsechny)


def ve_fronte():
    cesta = _fronta()
    return cesta.read_text(encoding="utf-8").split() if cesta.exists() else []


def z_sitemapy():
    """Všechny adresy z vykreslené sitemapy. Pro první nahlášení celého webu."""
    import re
    mapa = (config.SITE / "sitemap.xml").read_text(encoding="utf-8")
    return re.findall(r"<loc>([^<]+)</loc>", mapa)


def telo(adresy_k_odeslani):
    host = urlparse(config.SITE_URL).hostname
    return {
        "host": host,
        "key": config.INDEXNOW_KLIC,
        "keyLocation": "{0}/{1}.txt".format(config.SITE_URL.rstrip("/"), config.INDEXNOW_KLIC),
        # Hlásit smí jen adresy vlastního webu, jinak protokol vrátí 422.
        "urlList": [a for a in adresy_k_odeslani if urlparse(a).hostname == host][:MAX_ADRES],
    }


def odesli(adresy_k_odeslani):
    """Pošle adresy. Vrací (ok, zpráva); síťová chyba běh neshodí."""
    data = telo(adresy_k_odeslani)
    if not data["urlList"]:
        return True, "Nic k nahlášení."
    if data["host"] in ("localhost", "127.0.0.1"):
        return False, "Web běží na {0}, tam se nic nehlásí.".format(data["host"])
    pozadavek = urllib.request.Request(
        config.INDEXNOW_ENDPOINT, data=json.dumps(data).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json; charset=utf-8",
                 "User-Agent": config.USER_AGENT})
    try:
        with urllib.request.urlopen(pozadavek, timeout=config.HTTP_TIMEOUT) as odpoved:
            kod = odpoved.status
    except urllib.error.HTTPError as exc:
        kod = exc.code
    except (urllib.error.URLError, OSError) as exc:
        return False, "IndexNow nedostupný: {0}".format(exc)
    # 202 = přijato, klíč se teprve ověřuje. Obojí je úspěch.
    if kod in (200, 202):
        return True, "Nahlášeno {0} adres (HTTP {1}).".format(len(data["urlList"]), kod)
    return False, "IndexNow vrátil HTTP {0}.".format(kod)


def vyprazdni_frontu():
    cesta = _fronta()
    if cesta.exists():
        cesta.unlink()
