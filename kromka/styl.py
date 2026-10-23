# -*- coding: utf-8 -*-
"""Jazyk KROMCL: slovník generace Alpha, zákazy a pravidla proti AI slopu.

Pravidla žijí tady v repu schválně. Sdílený `stylecheck.py` je v Dropboxu a
v GitHub Actions neexistuje, takže kdyby kvalita textu stála na něm, v CI by
nestála na ničem. Lokálně se pustí navíc, viz funkce `stylecheck` níž.

Zdroje slovníku (ověřeno 23. 10. 2026):
  atlaso.cz, aktualnibod.cz, genppt.com/blog/gen-alpha-slang
"""

import json
import os
import re
import subprocess
from pathlib import Path

from . import config

# --- Slovník ---------------------------------------------------------------
# Slovník žije v data/slovnik.json, aby se dal rozšiřovat bez sahání do kódu.
# Klíč `misto` říká, jakou běžnou českou formulaci výraz nahrazuje; podle toho
# ho prompt nabízí, protože psát se má česky a slang je koření.

SLOVNIK_SOUBOR = config.DATA / "slovnik.json"
_CACHE = {}


def nacti_slovnik():
    if "data" not in _CACHE:
        with SLOVNIK_SOUBOR.open(encoding="utf-8") as f:
            _CACHE["data"] = json.load(f)
    return _CACHE["data"]


def zapis_slovnik(data):
    with SLOVNIK_SOUBOR.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    _CACHE.pop("data", None)
    _CACHE.pop("re", None)


def vyrazy(stav=None, kategorie=None):
    """Výrazy ze slovníku, volitelně filtrované stavem a kategorií."""
    vse = nacti_slovnik()["vyrazy"]
    return [v for v in vse
            if (stav is None or v.get("stav") == stav)
            and (kategorie is None or v.get("kategorie", "slang") == kategorie)]


def zakazane():
    return [v["vyraz"] for v in vyrazy("zakazane")]


def _radek(v):
    kus = "- **{0}**".format(v["vyraz"])
    misto = ", ".join(v.get("misto") or [])
    if misto:
        kus += " místo: {0}".format(misto)
    kus += " — {0}".format(v["vyznam"])
    tvary = v.get("tvary") or []
    if tvary:
        kus += " (tvary: {0})".format(", ".join(tvary))
    return kus


def _zakazane_re():
    if "re" not in _CACHE:
        slova = zakazane() + [t for v in vyrazy("zakazane")
                              for t in (v.get("tvary") or [])]
        # Delší tvary musí v alternaci stát první, jinak „mog" ukousne „mogging".
        serazene = sorted(set(slova), key=len, reverse=True)
        _CACHE["re"] = re.compile(
            r"\b(?:" + "|".join(re.escape(z) for z in serazene) + r")\w*",
            re.IGNORECASE | re.UNICODE)
    return _CACHE["re"]


def zkontroluj_zakazany_slang(text):
    """Výrazy, které shazují lidi. Prázdný seznam = čisté."""
    return sorted({m.group(0).lower() for m in _zakazane_re().finditer(text)})


# --- Antiteze --------------------------------------------------------------
# Nejoblíbenější obrat jazykových modelů a na všech Zdeňkových webech je to
# zákaz, ne limit.
_ANTITEZE = [
    re.compile(r",\s*ne\s+\w", re.IGNORECASE),
    re.compile(r"\bne(ní|jde|šlo|bylo)\b[^.!?]{0,80}\bale\b", re.IGNORECASE),
    re.compile(r"\bnejde o\b[^.!?]{0,60}\bjde o\b", re.IGNORECASE),
    re.compile(r"\bnejen\b[^.!?]{0,60}\bale (i|také)\b", re.IGNORECASE),
]


def zkontroluj_antitezi(text):
    """Výskyty konstrukce „A, ne B" a jejích rozvolněných variant."""
    nalezy = []
    for vzor in _ANTITEZE:
        for m in vzor.finditer(text):
            nalezy.append(text[max(0, m.start() - 40):m.end() + 30].strip())
    return nalezy


# --- Pravidla do promptu ---------------------------------------------------

PRAVIDLA_JAZYKA = """## Jak se píše

Píšeš pro lidi mezi 15 a 25 lety z Kroměříže, kteří to čtou na mobilu.

Tenhle jazyk není koření, je to celý web. Když zpráva vyjde tak, že by mohla
stát na webu radnice, selhal jsi. Psát novinářsky umí každý; ty máš psát tak,
jak si to ti lidé mezi sebou přepošlou.

Konkrétně:
- Nadpis musí mít pointu nebo slang, ne jenom fakt.
- Každá TL;DR odrážka má anglický label a na konci emoji.
- V každém odstavci těla je aspoň jeden výraz z téhle listiny.
- Začni reakcí, ne faktem. Fakt přijde hned ve druhé větě.
- Oslovuj čtenáře „ty". Krátké věty. Klidně si odfrkni nahlas.
- Poslední věta je tvoje reakce na celou věc. Může to být verdikt (W, L, mid,
  peak, cooked), ale klidně i jiná pointa, otázka nebo odfrknutí. Nesahej
  pokaždé po stejném slově — tři články za sebou zakončené „W" jsou nuda.

Co naopak NESMÍŠ: vyskládat větu tak, že se v tom ztratí fakt. Čísla, jména
a termíny zůstávají přesné a čitelné i někomu, kdo slang nezná.

Takhle to vypadá, když se to povede:
- ŠPATNĚ: „Radnice dokončila koncepci školství na roky 2027–2032."
  DOBŘE: „Radnice vyplodila plán, co bude se školama do roku 2032. Šest let
  dopředu, to je docela flex."
- ŠPATNĚ: „Nové elektronické tabule budou instalovány na třech zastávkách."
  DOBŘE: „Konec hádání, jestli ti to ujelo. Na tři zastávky míří tabule,
  co ukážou, za jak dlouho fakt přijede bus."
- ŠPATNĚ: „Město ušetřilo 1,2 milionu korun ročně."
  DOBŘE: „Městská kasa dostala buff o 1,2 milionu ročně. Solárky farmí
  elektřinu na střechách a rozpočet to cítí."

Živé výrazy. U každého je napsané, jakou běžnou formulaci nahrazuje — sáhni po
něm tam, kde bys jinak napsal přesně to. Uvedené tvary jsou doložené,
jiné si nevymýšlej:
{jadro}

Tyhle používej jen vědomě a ironicky:
{ironicke}

## Úřední termíny, které mají lidský tvar

Tohle je nejrychlejší způsob, jak z oznámení udělat vlastní text. Kdykoliv ti
pod rukou vzniká úřední termín, sáhni po jeho běžném tvaru:
{uredni}

ZAKÁZANÉ výrazy, ani v nadsázce: {zakazane}.
Slouží k shazování lidí a vtip má mířit na situaci a na úřední jazyk."""


PRAVIDLA_PROTI_SLOPU = """## Obraty, po kterých text okamžitě zní jako stroj

1. ZÁKAZ antiteze „A, ne B". Žádné „je to volba, ne podmínka", „nešlo o
   výměnu, ale o srovnání", „nejde o X, jde o Y". Piš oznamovací větu.
2. Žádný zmizelý konatel na začátku věty ani odstavce. Ne „podařilo se
   nainstalovat", ale napiš, kdo to udělal: „technické služby instalovaly".
3. Žádná ozdobná trojice bez slovesa. Ne „Sedm dní, osm klientů, jedna linka."
   Výčtu dej sloveso a konatele.
4. Nevysvětluj čtenáři, co je na tom zajímavé. Žádné „zajímavé je", „podstatné
   je", „když se na to podíváme". Ukaž tu věc a závěr nech na čtenáři.
5. Žádný nedoložený dovětek. Věta nesmí začít faktem a skončit soudem, který
   nikde nestojí. Když pro tvrzení nemáš oporu, vypusť ho celé.
6. Nevymýšlej motivace ani pocity lidí. Piš, co se stalo, a proč nech být,
   pokud to někdo sám neřekl.

## Anglické vazby přeložené doslova

Čeština tyhle vazby nemá, i když jsou gramaticky správné:
- věc „nese" své součásti → má je, nebo na ní jsou
- „uvnitř sedí / navrchu sedí" komponenta → je uvnitř, je na horní straně
- „výhoda leží v ceně" → výhodou je cena
- „ceny startují na" → ceny začínají na, pořídíš od
- „dává smysl" → má smysl
- „doručit slib" → splnit slib
- „hluboká sleva" → vysoká sleva
- „napříč vším" → u všech
- „za zlomek času" → mnohem rychleji
- „poháněný AI" → využívá model, běží na modelu"""


def pravidla_jazyka():
    return PRAVIDLA_JAZYKA.format(
        jadro="\n".join(_radek(v) for v in vyrazy("zive", "slang")),
        ironicke="\n".join(_radek(v) for v in vyrazy("ironicke")),
        uredni="\n".join(_radek(v) for v in vyrazy("zive", "uredni")),
        zakazane=", ".join(zakazane()),
    )


# --- Napojení na sdílený stylecheck ----------------------------------------

STYLECHECK = Path(os.path.expanduser(
    "~/.claude/skills/_internal/style/stylecheck.py"))


def stylecheck_dostupny():
    return STYLECHECK.exists()


def stylecheck(cesta_md, slozka_webu):
    """Pustí sdílený stylecheck.py, když je po ruce. Vrací (ok, výpis).

    V GitHub Actions soubor neexistuje a kontrola se přeskočí — proto jsou
    tvrdé pojistky v `rewrite.py`, ne tady.
    """
    if not stylecheck_dostupny():
        return True, "stylecheck.py není po ruce, přeskočeno"
    proces = subprocess.run(
        ["python", str(STYLECHECK), "--site", str(slozka_webu), str(cesta_md)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
    return proces.returncode == 0, proces.stdout.decode("utf-8", "replace")
