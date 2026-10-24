# -*- coding: utf-8 -*-
"""Akce z otevřených dat města Kroměříž.

Záměrně **mimo `sources/`**. `pipeline.nove_polozky` posílá každou položku
z každého registrovaného zdroje přes model do přepisu a ukládá ji mezi
články. Akce se nepřepisují — jsou to fakta pod licencí, která doslovné
převzetí dovoluje výměnou za uvedení zdroje. Kdyby zdroj akcí skončil
v `sources.REGISTR`, přepisovalo by se 133 termínů měsíčně a platilo by se
za to.

Celý program je jeden soubor `data/akce.json`, ne soubor na akci. Je to
rolující okno, které se přepisuje celé; sto souborů měsíčně vznikajících
a mizejících by v repu dělalo jen hluk.
"""

import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from . import config, net

# Datum v parametrech exportu, datum a čas uvnitř XML.
_PARAM = "%d.%m.%Y"
_CAS = "%Y-%m-%d %H:%M:%S"


def _text(el, tag):
    hodnota = el.findtext(tag)
    return html.unescape((hodnota or "").strip())


def _radek(el, tag):
    """Krátké pole na jeden řádek.

    Poznámka k ceně v exportu běžně obsahuje odřádkování („snížené: 60 Kč\\n\\n
    rodinné: 190 Kč"), což by v jednořádkovém pruhu pod názvem rozhodilo
    kartu.
    """
    return re.sub(r"\s+", " ", _text(el, tag)).strip()


def _cislo(el, tag):
    try:
        return int(_text(el, tag) or 0)
    except ValueError:
        return 0


def _bool(el, tag):
    return _text(el, tag) == "1"


def _cas(hodnota):
    """`2026-10-24 17:30:00` na ISO. Prázdné nebo rozbité vrací prázdno."""
    try:
        return datetime.strptime(hodnota, _CAS).isoformat()
    except (ValueError, TypeError):
        return ""


def ted():
    """Teď v Praze, bez časové zóny — stejně jako časy akcí v datech.

    GitHub Actions běží v UTC. S `date.today()` by build těsně po půlnoci
    ukazoval na stránce „dnes" ještě včerejšek a karta by za „už začalo"
    brala čas o hodinu nebo dvě posunutý. Windows bez balíčku tzdata zónu
    nezná; tam se bere místní čas stroje, který je pražský.
    """
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Prague")).replace(tzinfo=None, microsecond=0)
    except Exception:                                 # noqa: BLE001
        return datetime.now().replace(microsecond=0)


def adresa(od, do):
    return "{0}?export_type=event_date&from={1}&to={2}&place_id=0&type=0".format(
        config.AKCE_EXPORT, od.strftime(_PARAM), do.strftime(_PARAM))


def stahni(dni=None):
    """Stáhne XML export na následujících `dni` dní včetně dneška."""
    dni = dni or config.AKCE_DNI
    dnes = ted()
    return net.get(adresa(dnes, dnes + timedelta(days=dni)))


def _deti(koren, tag):
    """Potomci prvku, nebo prázdný seznam, když prvek chybí.

    Ne `koren.find(tag) or []`: pravdivost prvku závisí na počtu jeho
    potomků a Python ji v budoucnu změní na vždy pravdivou.
    """
    prvek = koren.find(tag)
    return list(prvek) if prvek is not None else []


def rozparsuj(xml_text):
    """XML na `{mista, typy, terminy}` s normalizovanými termíny.

    Číselníky míst a typů jsou v exportu zvlášť a termíny na ně odkazují
    číslem. Rozbalují se rovnou, aby se s nimi nemusel tahat render.
    """
    koren = ET.fromstring(xml_text)
    mista = {}
    for m in _deti(koren, "places"):
        mista[_cislo(m, "id")] = {"nazev": _text(m, "label"),
                                  "web": _odkaz(_text(m, "web"))}
    typy = {}
    for t in _deti(koren, "event_types"):
        typy[_cislo(t, "id")] = _text(t, "label")

    terminy = [_termin(e, mista, typy) for e in _deti(koren, "events")]
    terminy.sort(key=lambda t: (t["zacatek"], t["nazev"]))
    return {"mista": mista, "typy": typy, "terminy": terminy}


def _termin(el, mista, typy):
    zacatek = _cas(_text(el, "time_from"))
    konec = _cas(_text(el, "time_to"))
    misto_id = _cislo(el, "place")
    # Místo 0 znamená neuvedeno; v číselníku má prázdný název.
    misto = mista.get(misto_id, {}).get("nazev", "")
    return {
        "id": _cislo(el, "id"),
        "akce_id": _cislo(el, "event_id"),
        "nazev": _radek(el, "name"),
        "perex": _perex(_text(el, "perex")),
        "zacatek": zacatek,
        "konec": konec,
        "vicedenni": bool(zacatek and konec and zacatek[:10] != konec[:10]),
        "typ_id": _cislo(el, "type"),
        "typ": typy.get(_cislo(el, "type"), ""),
        "misto": misto,
        "misto_web": mista.get(misto_id, {}).get("web", ""),
        "poznamka": _radek(el, "note"),
        "cena": _cislo(el, "price"),
        "cena_pozn": _radek(el, "price_note"),
        "zdarma": _bool(el, "free_entrance"),
        "pro_deti": _bool(el, "for_kids"),
        "web": _odkaz(_text(el, "web")),
        "youtube": _text(el, "youtube"),
        "upraveno": _cas(_text(el, "last_edit")),
    }


def _odkaz(text):
    """Adresa vždy s protokolem.

    Pořadatelé do exportu píšou i „www.hkkm.cz" bez https. Takový odkaz
    bere prohlížeč jako relativní a vede na kromcl.cz/program/www.hkkm.cz,
    tedy na 404 — 23. 10. 2026 to bylo 22 ze 115 odkazů.
    """
    text = (text or "").strip()
    if not text or re.match(r"^[a-z][a-z0-9+.-]*://", text, re.I):
        return text
    return "https://" + text.lstrip("/")


def _perex(text):
    """Perex bez značek a bez zdvojených mezer.

    V exportu bývá čistý, ale pole `text` je plné HTML a není důvod věřit,
    že se do perexu nikdy nedostane.
    """
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()


def uloz(data):
    config.AKCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.AKCE_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    return config.AKCE_FILE


def nacti():
    """Uložený program, nebo prázdná kostra, když ještě nic nestáhl."""
    if not config.AKCE_FILE.exists():
        return {"stazeno": "", "mista": {}, "typy": {}, "terminy": []}
    data = json.loads(config.AKCE_FILE.read_text(encoding="utf-8"))
    # JSON klíče jsou vždy řetězce, čísla se musí vrátit zpátky.
    data["mista"] = {int(k): v for k, v in data.get("mista", {}).items()}
    data["typy"] = {int(k): v for k, v in data.get("typy", {}).items()}
    return data


def stari_hodin(data):
    stazeno = data.get("stazeno") or ""
    try:
        kdy = datetime.fromisoformat(stazeno)
    except ValueError:
        return None
    if kdy.tzinfo is None:
        kdy = kdy.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - kdy).total_seconds() / 3600.0


def aktualizuj(dni=None, vynutit=False, verbose=True):
    """Stáhne a uloží program. Vrací uložená data.

    Bez `vynutit` se čerstvá data nestahují znovu — hodinový cron by jinak
    tahal 574 kB čtyřiadvacetkrát denně kvůli pár změnám.
    """
    ulozene = nacti()
    stari = stari_hodin(ulozene)
    if not vynutit and stari is not None and stari < config.AKCE_MAX_STARI_HODIN:
        if verbose:
            print("Program je {0:.1f} h starý, stahování se přeskakuje.".format(stari))
        return ulozene

    data = rozparsuj(stahni(dni))
    data["stazeno"] = datetime.now(timezone.utc).isoformat()
    data["dni"] = dni or config.AKCE_DNI
    uloz(data)
    if verbose:
        print("Staženo {0} termínů, {1} míst, {2} typů.".format(
            len(data["terminy"]), len(data["mista"]), len(data["typy"])))
    return data
