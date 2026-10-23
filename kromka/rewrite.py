# -*- coding: utf-8 -*-
"""Klasifikace citlivosti a samotný přepis přes Claude API.

Pojistky proti vymýšlení jsou dvě a obě jsou strojové, ne jen prosba v promptu:

* `zkontroluj_cisla` — každé číslo ve výstupu musí být i ve zdroji. Model, který
  si domyslí částku nebo datum, tím neprojde.
* `zkontroluj_citace` — výstup nesmí obsahovat uvozovky. Citace se parafrázují,
  protože přepsaná citace v uvozovkách je slovo vložené do úst konkrétnímu
  člověku a to je jediná věc, která tenhle projekt může opravdu potopit.
"""

import json
import re

from . import config, styl
CITLIVOST_PROMPT = """Jsi klasifikátor zpravodajských článků z webu českého města.

Odpověz JEDNÍM slovem, nic dalšího:

vynechat — článek se dotýká úmrtí konkrétního člověka, vážné nehody se zraněním,
  trestného činu s obětí, sebevraždy, požáru s oběťmi, násilí nebo zneužívání.
neutralni — článek se dotýká konfliktu ve městě, sociálních problémů, závislostí,
  stížností obyvatel na konkrétní skupinu, politického sporu, soudu, pokuty,
  kritiky jmenované osoby, zdravotního rizika nebo krizové situace.
volny — cokoliv jiného: investice, kultura, doprava, sport, školství, výsledky
  voleb, opravy, akce pro veřejnost, ocenění, provozní informace.

Titulek: {titulek}

Text:
{text}"""

ZPRAVA_PROMPT = """Jsi redaktor webu {brand}, který píše o dění v Kroměříži.

Právě sis přečetl oznámení radnice. Teď o té věci napíšeš VLASTNÍ zprávu.
Nepřepisuješ cizí text, informuješ o události.

Rozdíl je zásadní a právní. Město má na svém webu „Všechna práva vyhrazena —
použití obsahu nebo jeho části je možné pouze se souhlasem města Kroměříž."
Souhlas nemáme. Fakta jsou volná a smíš je použít; formulace města nikoliv.

## Jak z oznámení udělat vlastní zprávu

1. Přečti si oznámení a vypiš si holá fakta: co, kdo, kdy, kde, za kolik.
2. Zavři ho a napiš zprávu z těch faktů. Vlastní stavbou, vlastním pořadím.
3. Začni tím, co je pro čtenáře v Kroměříži nejdůležitější, i kdyby to
   v oznámení bylo až ve třetím odstavci.
4. ŽÁDNÁ souvislá sekvence delší než šest slov se nesmí shodovat s oznámením.
   Výjimka jsou vlastní jména, názvy institucí a ustálené názvy akcí.
5. Nepřebírej pořadí odstavců ani stavbu vět z oznámení.
6. Výčty a seznamy přeformuluj taky. Právě u nich se nejčastěji stane, že je
   přepíšeš slovo od slova. Pojmenuj věci po svém a čísla piš číslicemi:
   „osmi mateřských škol s třinácti pracovišti, šesti základních škol"
   → „8 školek na 13 adresách a 6 základek".

## Tón

{ton}

{jazyk}

{proti_slopu}

## Pravidla, která se neporušují

1. Nesmíš přidat JEDINÝ fakt, který ti oznámení nedalo. Žádná čísla, data,
   jména, částky, místa ani důvody navíc. Když zdroj neříká proč, ty taky ne.
2. Čísla, data a částky musí sedět přesně.
3. Nepoužívej uvozovky a necituj nikoho přímo. Co někdo řekl, parafrázuj:
   „Hebnar to zdůvodnil tím, že…" Ne „Hebnar řekl: …".
4. Jména a funkce veřejných osob zachovej správně. Nikomu se neposmívej.
   Vtip patří situaci a úřednímu jazyku, nikdy konkrétnímu člověku.
5. Nehodnoť politicky. Výsledek voleb je fakt, ze kterého se nedělá názor.
6. Nadpis nesmí končit tečkou.
7. Nikdy nemluv o oznámení, o tiskové zprávě ani o tom, odkud to víš.
   Čtenář žádný jiný text nevidí. Píšeš zprávu, ne komentář k cizí zprávě.
8. Číslo nikdy nepoužívej jako vtip vedle jiného čísla. Dvě různá čísla
   v jedné větě čtenáře zmatou.
9. Žádné e-maily, telefonní čísla ani čísla účtů.
10. Vybírej, nepřevyprávěj. Vezmi, co má pro čtenáře cenu, zbytek vynech.
   Odstavec má do 80 slov. Historické odbočky a výčty institucí vypusť.

## Výstup

Vrať POUZE JSON, bez markdown bloku, v tomhle tvaru:

{{
  "headline": "nadpis, max 90 znaků, konkrétní, bez tečky na konci",
  "tldr": [
    {{"label": "Dvě Anglická Slova", "text": "jedna věta česky", "emoji": "🚌📺"}}
  ],
  "body": ["odstavec", "odstavec"],
  "tags": ["doprava"]
}}

tldr má přesně 3 položky. body má 2 až 4 odstavce. tags jsou 1 až 3 krátká
česká slova malými písmeny z okruhu: doprava, kultura, sport, školství, peníze,
stavba, radnice, volby, příroda, lidé, akce.

## Oznámení radnice, ze kterého si bereš fakta

Titulek: {titulek}
Rubrika: {rubrika}
Datum: {datum}

{text}"""

TON_VOLNY = """Mluvený jazyk generace Alpha, jak se píše na telefonu. TL;DR
odrážky mají anglický label a emoji na konci. Buď vtipný, ale vtip dělej ze
situace a z úředního jazyka, nikdy z lidí."""

TON_NEUTRALNI = """Krátké věty, žádný úřednický jazyk, oslovuj čtenáře. ŽÁDNÝ
slang, ŽÁDNÉ emoji, ŽÁDNÉ anglické labely, ŽÁDNÉ vtipy. Tohle je citlivé téma a
řeší se věcně. V poli "emoji" vrať prázdný řetězec a label piš česky."""


def _zeptej_se(model, prompt, max_tokens):
    """Pošle prompt modelu. Tři backendy, protože ne každý stroj má API klíč.

    api  — oficiální SDK, potřebuje ANTHROPIC_API_KEY. Jediná varianta, která
           funguje v GitHub Actions.
    cli  — `claude --print` na předplatném. Na vlastním stroji zadarmo, ale
           vyžaduje přihlášené Claude Code a v CI se na to nedá spolehnout.
    stub — žádný model. Poskládá výstup ze zdrojového textu, aby se dala projet
           celá cesta (klasifikace → přepis → pojistky → render) bez placení.
           Slouží k ověření mechaniky, ne k publikování.
    """
    if config.BACKEND == "stub":
        return _stub(prompt)
    if config.BACKEND == "cli":
        return _pres_cli(model, prompt)
    from anthropic import Anthropic
    # Klíč založený na úrovni organizace není navázaný na workspace a API ho
    # bez téhle hlavičky odmítne. Klíč založený uvnitř workspace ji nepotřebuje.
    hlavicky = {}
    if config.WORKSPACE_ID:
        hlavicky["anthropic-workspace-id"] = config.WORKSPACE_ID
    odpoved = Anthropic().messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
        extra_headers=hlavicky or None,
    )
    return _text_z_odpovedi(odpoved)


def _text_z_odpovedi(odpoved):
    """Vytáhne text z odpovědi. Nelze brát content[0] — model vrací jako první
    blok přemýšlení, které žádný `.text` nemá."""
    if getattr(odpoved, "stop_reason", "") == "max_tokens":
        raise ValueError("Odpověď se nevešla do max_tokens a je useknutá.")
    kusy = [blok.text for blok in odpoved.content if getattr(blok, "type", "") == "text"]
    if not kusy:
        raise ValueError("Odpověď neobsahuje textový blok.")
    return "\n".join(kusy)


def _pres_cli(model, prompt):
    import subprocess
    proces = subprocess.run(
        [config.CLAUDE_BIN, "--print", "--model", model],
        input=prompt.encode("utf-8"),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=300,
    )
    if proces.returncode != 0:
        raise RuntimeError(proces.stderr.decode("utf-8", "replace").strip())
    return proces.stdout.decode("utf-8", "replace")


def _stub(prompt):
    """Náhrada modelu pro zkušební běh. Skládá výstup ze zdroje, takže projde
    pojistkami — kromě uvozovek, které se musí odstranit stejně jako to dělá
    parafráze v ostrém promptu."""
    if prompt.startswith("Jsi klasifikátor"):
        return "volny"
    zdroj = prompt.split("## Zdroj", 1)[-1]
    radky = [r.strip() for r in zdroj.split("\n") if r.strip()]
    titulek = next((r[8:].strip() for r in radky if r.startswith("Titulek:")), "Zpráva")
    odstavce = [r for r in radky if not r.startswith(("Titulek:", "Rubrika:", "Datum:"))]
    odstavce = [re.sub(r"[„“”»«\"]", "", o) for o in odstavce] or ["Bez textu."]
    data = {
        "headline": titulek.rstrip(".")[:90],
        "tldr": [{"label": "Bod {0}".format(i + 1), "text": o[:160], "emoji": ""}
                 for i, o in enumerate((odstavce + odstavce + odstavce)[:3])],
        "body": odstavce[:3],
        "tags": ["radnice"],
    }
    return json.dumps(data, ensure_ascii=False)


def klasifikuj(item):
    """Vrací 'volny', 'neutralni' nebo 'vynechat'."""
    zprava = CITLIVOST_PROMPT.format(
        titulek=item["title"],
        text="\n\n".join(item.get("body") or [item.get("perex", "")])[:4000],
    )
    slovo = _zeptej_se(config.MODEL_CLASSIFY, zprava, config.MAX_TOKENS_CLASSIFY).strip().lower()
    return slovo if slovo in ("volny", "neutralni", "vynechat") else "neutralni"


def prepis(item, citlivost, pokusy=2):
    """Vrátí dict s headline, tldr, body, tags. Vyhodí při porušení pojistek.

    Jeden opravný pokus, protože rozbitý JSON nebo vymyšlené číslo bývá
    náhoda, ne systematická chyba. Víc pokusů už jen platí za totéž.
    """
    zprava = ZPRAVA_PROMPT.format(
        brand=config.BRAND,
        ton=TON_VOLNY if citlivost == "volny" else TON_NEUTRALNI,
        jazyk=styl.pravidla_jazyka() if citlivost == "volny" else "",
        proti_slopu=styl.PRAVIDLA_PROTI_SLOPU,
        titulek=item["title"],
        rubrika=item.get("rubrika") or "—",
        datum=(item.get("published") or "")[:10],
        text="\n\n".join(item.get("body") or [item.get("perex", "")]),
    )
    posledni = None
    for pokus in range(pokusy):
        try:
            return _jeden_pokus(item, zprava)
        except (ValueError, KeyError, TypeError) as exc:
            posledni = exc
            if pokus < pokusy - 1:
                zprava += (
                    "\n\n## Předchozí pokus neprošel\n{0}\n"
                    "Oprav přesně tohle a zbytek nech být. Jde-li o převzaté "
                    "formulace, přepiš ty pasáže vlastními slovy; fakta v nich "
                    "zůstávají, mění se jen pojmenování a stavba věty."
                ).format(exc)
    raise ValueError(str(posledni))


def _jeden_pokus(item, zprava):
    data = _json(_zeptej_se(config.MODEL_REWRITE, zprava, config.MAX_TOKENS_REWRITE))

    zdroj = " ".join([item["title"]] + (item.get("body") or []) + [item.get("perex", "")])
    vystup = " ".join(
        [data["headline"]]
        + [o["text"] for o in data["tldr"]]
        + data["body"]
    )

    vymyslena = zkontroluj_cisla(zdroj, vystup, item.get("published", ""))
    if vymyslena:
        raise ValueError("Čísla, která nejsou ve zdroji: {0}".format(", ".join(vymyslena)))
    if zkontroluj_citace(vystup):
        raise ValueError("Výstup obsahuje přímou citaci v uvozovkách.")
    kontakty = zkontroluj_kontakty(vystup)
    if kontakty:
        raise ValueError("Výstup obsahuje kontaktní údaje: {0}".format(", ".join(kontakty)))
    opsane = zkontroluj_opisovani(zdroj, vystup)
    if opsane:
        raise ValueError("Doslova převzaté formulace z oznámení: {0}".format(
            " | ".join('„{0}"'.format(o) for o in opsane[:3])))
    slang = styl.zkontroluj_zakazany_slang(vystup)
    if slang:
        raise ValueError("Zakázané výrazy shazující lidi: {0}".format(", ".join(slang)))
    antiteze = styl.zkontroluj_antitezi(vystup)
    if antiteze:
        raise ValueError("Antiteze „A, ne B\": {0}".format(antiteze[0]))
    if data["headline"].rstrip().endswith("."):
        data["headline"] = data["headline"].rstrip().rstrip(".")
    return data


def _json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    zacatek = text.find("{")
    konec = text.rfind("}")
    return json.loads(text[zacatek:konec + 1])


_CISLO = re.compile(r"\d[\d\s ]*(?:[.,]\d+)?")

# Zdroj píše "pět tabulí", přepis legitimně napíše "5 tabulí". Bez téhle mapy
# by pojistka shodila skoro každý článek. Hledá se podle kořene, aby seděly
# i tvary jako pěti, třech, osmi.
_CISLOVKY = [
    ("nula", "0"), ("jed", "1"), ("prvn", "1"), ("dva", "2"), ("dvě", "2"),
    ("dvou", "2"), ("dvě", "2"), ("druh", "2"), ("tři", "3"), ("tře", "3"),
    ("čtyř", "4"), ("čtvrt", "4"), ("pět", "5"), ("pěti", "5"), ("pát", "5"),
    ("šest", "6"), ("šesti", "6"), ("sedm", "7"), ("osm", "8"), ("devět", "9"),
    ("devít", "9"), ("deset", "10"), ("deseti", "10"), ("desát", "10"),
    ("jedenáct", "11"), ("dvanáct", "12"), ("třináct", "13"), ("čtrnáct", "14"),
    ("patnáct", "15"), ("šestnáct", "16"), ("sedmnáct", "17"), ("osmnáct", "18"),
    ("devatenáct", "19"), ("dvacet", "20"), ("dvaceti", "20"), ("třicet", "30"),
    ("čtyřicet", "40"), ("padesát", "50"), ("šedesát", "60"), ("sedmdesát", "70"),
    ("osmdesát", "80"), ("devadesát", "90"), ("sto", "100"), ("set", "100"),
    ("stě", "100"), ("tisíc", "1000"), ("milion", "1000000"), ("milión", "1000000"),
    ("miliard", "1000000000"),
]


def _cisla(text):
    """Čísla v normalizované podobě: bez mezer uvnitř, desetinná čárka na tečku."""
    nalezena = set()
    for kus in _CISLO.findall(text):
        kus = re.sub(r"[\s ]", "", kus).replace(",", ".").rstrip(".")
        if kus:
            nalezena.add(kus)
            nalezena.add(kus.lstrip("0") or "0")
    return nalezena


def _povolena(zdroj, datum=""):
    """Co všechno smí být ve výstupu: čísla ze zdroje, číslovky slovy a datum."""
    povolena = _cisla(zdroj)
    maly = zdroj.lower()
    for koren, cislice in _CISLOVKY:
        if koren in maly:
            povolena.add(cislice)
    for kus in re.findall(r"\d+", datum):
        povolena.add(kus)
        povolena.add(kus.lstrip("0") or "0")
    return povolena


def zkontroluj_cisla(zdroj, vystup, datum=""):
    """Čísla, která jsou ve výstupu, ale ne ve zdroji. Prázdný seznam = čisté."""
    povolena = _povolena(zdroj, datum)
    return sorted(c for c in _cisla(vystup) if c not in povolena)


_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# České telefonní číslo: 9 číslic, volitelně s předvolbou a mezerami.
_TELEFON = re.compile(r"(?:\+420[\s ]?)?(?:\d{3}[\s ]){2}\d{3}\b")


_SLOVO = re.compile(r"[0-9a-záčďéěíňóřšťúůýž]+", re.IGNORECASE | re.UNICODE)

# Ustálené úřední a právní termíny. Nejsou to autorské formulace, jsou to
# názvy věcí, které se jinak pojmenovat nedají, a jejich shoda tedy neznamená
# opisování. Fungují jako lepidlo: samy o sobě nesmí vyrobit nález.
# Jen vlastní jména a názvy, které opravdu nemají jinou podobu. Všechno
# ostatní, co zní úředně, má lidský tvar ve slovníku (příspěvková organizace →
# příspěvkovka) a model ho má použít, ne spoléhat na výjimku.
USTALENE = [
    "integrovaná doprava zlínského kraje", "zlínského kraje",
    "odbor školství mládeže a tělovýchovy", "svč šipka",
    "kroměřížské technické služby", "komise rady pro bezpečnost",
]

# Prázdná slova, která také nic nedokazují.
_SPONY = {"a", "i", "o", "u", "v", "ve", "s", "se", "z", "ze", "na", "do", "od",
          "po", "za", "k", "ke", "pro", "při", "že", "je", "jsou", "byl",
          "byla", "bylo", "budou", "bude", "to", "ten", "ta", "tak", "jako",
          "jeho", "jejich", "který", "která", "které", "si", "už", "také"}


def zkontroluj_opisovani(zdroj, vystup, delka=8):
    """Souvislé sekvence slov doslova převzaté z oznámení.

    Fakta jsou volná, formulace města ne. Tohle je jediná pojistka, která to
    hlídá strojově — prompt sám o sobě model od opisování neodradí.

    Osm slov je zvolené tak, aby propadly názvy institucí a akcí, ale neprošla
    převzatá věta. Nález navíc musí po odečtení ustálených termínů a spojek
    obsahovat aspoň čtyři vlastní slova; jinak by stačilo, aby se potkaly dva
    úřední názvy, a hlásili bychom opisování tam, kde žádné není.
    """
    def ngramy(text):
        slova = [s.lower() for s in _SLOVO.findall(text)]
        return {" ".join(slova[i:i + delka])
                for i in range(len(slova) - delka + 1)}

    nalezy = []
    for kus in sorted(ngramy(zdroj) & ngramy(vystup)):
        zbytek = kus
        for termin in USTALENE:
            zbytek = zbytek.replace(termin, " ")
        vlastni = [s for s in zbytek.split() if s not in _SPONY]
        if len(vlastni) >= 4:
            nalezy.append(kus)
    return nalezy


def zkontroluj_kontakty(vystup):
    """Kontaktní údaje ve výstupu. Patří do originálu, ne na přepisový web —
    čtenáři jsou k ničemu a sklízečům spamu je zbytečné je rozmnožovat."""
    return sorted(set(_EMAIL.findall(vystup)) | set(_TELEFON.findall(vystup)))


def zkontroluj_citace(vystup):
    """True, když výstup obsahuje uvozovky, tedy nejspíš přímou řeč."""
    return bool(re.search(r"[„“”»«\"]", vystup))
