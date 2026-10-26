# -*- coding: utf-8 -*-
"""Facebook: nový článek jako příspěvek na stránce Kromcl.

Stejný tvar jako IndexNow. `all` články jen zařadí do fronty a
`python -m kromka facebook` je pošle až po nasazení, aby si Facebook na
adrese stáhl novou stránku i s kartou og:image. Fronta leží v `data/`,
takže ji bot commitne a přežije do dalšího běhu; v tomtéž souboru jsou
i odeslané články, a ty už nikdy neodejdou podruhé.

Rozhodnuto 26. 10. 2026: sdílí se všechny typy článků (zprávy, pozvánka,
příspěvky čtenářů), text je TL;DR článku, odkaz s UTM jde do `link`, aby
Facebook ukázal kartu. Do skupin publikovat nejde (Meta zavřela Groups API
v dubnu 2024), Kromcl je stránka a na tu ano.

Za běh odejde nejvýš jeden příspěvek. Cron jede hodinu, takže dávka tří
článků se rozprostře do tří hodin a čtenář ve feedu nepřeskočí dva ze tří.
Co nestihne odejít do 24 hodin od zařazení, se zahodí: zpráva o včerejší
uzavírce na FB nepatří.
"""

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from . import config, store

GRAPH = "https://graph.facebook.com/v26.0"
MAX_ZA_BEH = 1
MAX_STARI = timedelta(hours=24)


def _soubor():
    return config.DATA / "facebook.json"


def nacti():
    cesta = _soubor()
    if not cesta.exists():
        return {"fronta": [], "odeslane": {}}
    with cesta.open(encoding="utf-8") as f:
        return json.load(f)


def uloz(stav):
    config.DATA.mkdir(parents=True, exist_ok=True)
    with _soubor().open("w", encoding="utf-8") as f:
        json.dump(stav, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def _ted():
    return datetime.now(timezone.utc)


def zarad(clanky, ted=None):
    """Přidá články do fronty. Odeslané ani už zařazené se nepřidají."""
    if not clanky:
        return 0
    stav = nacti()
    znama = set(stav["odeslane"]) | {z["id"] for z in stav["fronta"]}
    kdy = (ted or _ted()).isoformat(timespec="seconds")
    nove = [{"id": c["id"], "zarazeno": kdy} for c in clanky if c["id"] not in znama]
    if nove:
        stav["fronta"].extend(nove)
        uloz(stav)
    return len(nove)


def odkaz(clanek):
    """Adresa článku s UTM. Slug je v kampani, ať GA4 ukáže, který článek táhl."""
    from .render import _abs

    parametry = urllib.parse.urlencode([
        ("utm_source", "facebook"), ("utm_medium", "social"),
        ("utm_campaign", clanek["slug"]), ("utm_content", "autopost"),
    ])
    return _abs("/clanek/{0}.html?{1}".format(clanek["slug"], parametry))


def text(clanek):
    """TL;DR jako na webu: emoji, štítek a věta, každý bod na řádku.

    Titulek se nepíše, ten Facebook ukáže na kartě pod textem.
    """
    radky = []
    for bod in clanek.get("tldr", []):
        casti = [bod.get("emoji", ""), (bod.get("label", "") + ":") if bod.get("label") else "",
                 bod.get("text", "")]
        radky.append(" ".join(c for c in casti if c))
    return "\n\n".join(radky) or clanek["headline"]


def zapnuto():
    return bool(config.FB_PAGE_ID and config.FB_TOKEN)


def _posli(clanek):
    """POST na /{stránka}/feed. Vrací ID příspěvku, při chybě výjimku s popisem."""
    data = urllib.parse.urlencode({
        "message": text(clanek), "link": odkaz(clanek),
        "access_token": config.FB_TOKEN,
    }).encode("utf-8")
    pozadavek = urllib.request.Request(
        "{0}/{1}/feed".format(GRAPH, config.FB_PAGE_ID), data=data, method="POST")
    try:
        with urllib.request.urlopen(pozadavek, timeout=config.HTTP_TIMEOUT) as odpoved:
            return json.load(odpoved)["id"]
    except urllib.error.HTTPError as exc:
        # Do výjimky jen popis z Graph API; URL ani tělo s tokenem ne.
        try:
            popis = json.load(exc).get("error", {}).get("message", "")
        except ValueError:
            popis = ""
        raise RuntimeError("HTTP {0}: {1}".format(exc.code, popis)) from None


def odesli(ted=None, posli=_posli):
    """Pošle nejstarší články z fronty. Vrací seznam řádků pro log.

    Neúspěch nechá článek ve frontě na příští běh; zahodí se až po 24 h.
    """
    ted = ted or _ted()
    stav = nacti()
    zpravy = []
    zbyva = []
    odeslano = 0
    for polozka in stav["fronta"]:
        if _ted_minus(polozka["zarazeno"], ted) > MAX_STARI:
            zpravy.append("Zahozeno po 24 h: {0}".format(polozka["id"]))
            continue
        if odeslano >= MAX_ZA_BEH:
            zbyva.append(polozka)
            continue
        try:
            clanek = store.nacti(polozka["id"])
        except FileNotFoundError:
            zpravy.append("Článek už neexistuje, vyřazen: {0}".format(polozka["id"]))
            continue
        try:
            post_id = posli(clanek)
        except Exception as exc:                      # noqa: BLE001
            zpravy.append("Neodešlo, zkusí se příště: {0} ({1})".format(clanek["slug"], exc))
            zbyva.append(polozka)
            continue
        stav["odeslane"][polozka["id"]] = {"post": post_id, "kdy": ted.isoformat(timespec="seconds")}
        zpravy.append("Odesláno: {0} (příspěvek {1})".format(clanek["slug"], post_id))
        odeslano += 1
    stav["fronta"] = zbyva
    uloz(stav)
    return zpravy


def _ted_minus(iso, ted):
    return ted - datetime.fromisoformat(iso)
