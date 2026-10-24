# -*- coding: utf-8 -*-
"""Týdenní pozvánka: vlastní článek o všem, co se koná od pondělí do neděle.

Jediný článek na webu, který nevzniká z oznámení radnice. Zdrojem je program
z otevřených dat (CC BY 4.0), takže pod ním je atribuce místo odkazu na
oznámení. Model píše jen komentář: úvod, pár vět ke každému dni a závěr.
Časy, názvy a místa se vykreslují přímo z dat a do JSONu se ukládají jako
snímek, protože `akce.json` drží jen měsíc dopředu a stará pozvánka by jinak
o seznamy přišla.

Vzniká v hodinovém cronu: v pondělí od 6:00, a když pondělí vypadne, ještě
v úterý. Od středy by zvala na půlku proběhlých akcí, takže se týden vynechá.
"""

from datetime import datetime, timedelta, timezone

from . import akce, config, htmlutil, rewrite, store, styl

ZDROJ = "pozvanka"
OD_HODINY = 6
# Pondělí a úterý. Středa už je pozdě.
DNY_VZNIKU = (0, 1)

DNY = ("pondělí", "úterý", "středa", "čtvrtek", "pátek", "sobota", "neděle")
MESICE = ["", "ledna", "února", "března", "dubna", "května", "června",
          "července", "srpna", "září", "října", "listopadu", "prosince"]

# Když model závěr nevrátí, šablona ho nesmí nechat prázdný.
ZAVER_ZALOHA = "Chceš delší okno na akce? Mrkni do celého programu."

# Snímek termínu: jen to, co vykresluje `render._karta_akce`.
POLE_SNIMKU = ("id", "akce_id", "nazev", "perex", "zacatek", "konec", "vicedenni",
               "typ", "misto", "poznamka", "cena", "cena_pozn", "zdarma",
               "pro_deti", "web", "youtube", "kino")

POZVANKA_PROMPT = """Jsi redaktor webu {brand}, který každé pondělí píše pozvánku na akce v Kroměříži.

Dostaneš celý program na tenhle týden, od pondělí {od} do neděle {do}. Napíšeš
k němu vlastní komentář. Pod každým dnem čtenář uvidí seznam všech akcí
s časem, názvem, místem a cenou, ten se vykreslí sám z dat. Ty mu neopakuješ
seznam, ty mu říkáš, na co se ten den vyplatí jít a proč by měl zvednout zadek
z gauče.

## Tón

{ton}

{jazyk}

{proti_slopu}

## Pravidla, která se neporušují

1. Nesmíš přidat JEDINÝ fakt, který program neříká. Žádné časy, ceny, jména,
   místa, účinkující ani děj filmu navíc. Když program o akci nic neříká,
   piš jen o tom, co z názvu a typu plyne. Nepiš, že se akce vrací, koná
   poprvé nebo naposledy, když to program sám neříká. Když říkáš, ve které
   dny se něco hraje, drž se dnů z programu přesně.
2. Časy, ceny ani data do textu nepiš. Jsou v seznamu hned pod tvým textem
   a dvakrát napsané číslo je jen šance se splést.
3. Nepoužívej uvozovky. Ani u názvů akcí a filmů: název napiš bez nich, nebo
   akci pojmenuj po svém („beseda o mámách", „nový Tarantino").
4. Nikomu se neposmívej. Vtip patří situaci, nikdy konkrétnímu člověku
   ani účinkujícímu.
5. Nadpis nesmí končit tečkou.
6. Nemluv o programu, datech ani o tom, odkud to víš. Čtenář žádný jiný
   text nevidí.
7. Žádné e-maily, telefonní čísla ani webové adresy.
8. Den bez akcí přiznej jednou krátkou větou. Nic si nevymýšlej, aby nebyl
   prázdný.
9. Vybírej, nepřevyprávěj. Ke dni 1 až 3 věty, k úvodu 1 až 2 odstavce do
   80 slov.

## Výstup

Vrať POUZE JSON, bez markdown bloku, v tomhle tvaru:

{{
  "headline": "nadpis pozvánky, max 90 znaků, s pointou, bez tečky na konci",
  "tldr": [
    {{"label": "Dvě Anglická Slova", "text": "jedna věta česky", "emoji": "🎬🎸"}}
  ],
  "body": ["úvodní odstavec"],
  "dny": {{
{klice_dnu}
  }},
  "vystavy": "1 až 2 věty k výstavám, které běží celý týden, nebo prázdný řetězec",
  "zaver": "jedna věta, která čtenáře pošle do celého programu na měsíc dopředu; odkaz přidá šablona"
}}

tldr má přesně 3 položky. body má 1 až 2 odstavce. dny mají přesně těchhle
sedm klíčů.

## Program na tenhle týden

{program}"""


def tyden(dnes):
    """Sedm ISO dnů od pondělí týdne, do kterého `dnes` patří."""
    pondeli = dnes - timedelta(days=dnes.weekday())
    return [(pondeli + timedelta(days=i)).isoformat() for i in range(7)]


def id_pro(pondeli):
    return "{0}:{1}".format(ZDROJ, pondeli)


def ma_vzniknout(ted, existuje):
    """Má teď vzniknout pozvánka? `ted` je pražský čas bez zóny."""
    if existuje:
        return False
    if ted.weekday() == 0:
        return ted.hour >= OD_HODINY
    return ted.weekday() in DNY_VZNIKU


def _v_okne(termin, dny):
    from .render import _v_okne as v_okne
    return v_okne(termin, dny)


def rozdel(terminy, dny):
    """Akce po dnech podle času, co běží už od dřív, zvlášť jako výstavy.

    Rozhoduje začátek, ne příznak `vicedenni`. Halloweenská noc ze soboty
    na neděli je v datech vícedenní, ale patří k sobotě; mezi výstavami by
    ji nikdo nehledal. Do bloku na konci jde jen to, co začalo před
    pondělím, a to jednou, ne v každém dni.
    """
    po_dnech = {den: [] for den in dny}
    vystavy = []
    for t in terminy:
        if not _v_okne(t, set(dny)):
            continue
        zacatek = (t.get("zacatek") or "")[:10]
        if zacatek in po_dnech:
            po_dnech[zacatek].append(t)
        else:
            vystavy.append(t)
    for den in po_dnech:
        po_dnech[den].sort(key=lambda t: t.get("zacatek", ""))
    vystavy.sort(key=lambda t: (t.get("konec", ""), t.get("nazev", "")))
    return po_dnech, vystavy


def _den(iso):
    d = datetime.strptime(iso, "%Y-%m-%d")
    return "{0} {1}. {2}".format(DNY[d.weekday()], d.day, MESICE[d.month])


def _rozsah(dny):
    od = datetime.strptime(dny[0], "%Y-%m-%d")
    do = datetime.strptime(dny[-1], "%Y-%m-%d")
    if od.month == do.month:
        return "{0}.–{1}. {2} {3}".format(od.day, do.day, MESICE[do.month], do.year)
    return "{0}. {1} – {2}. {3} {4}".format(od.day, MESICE[od.month], do.day,
                                           MESICE[do.month], do.year)


def slug_pro(dny):
    """Pevný vzor kvůli hledání „akce Kroměříž", ne nadpis od modelu."""
    return htmlutil.slugify("Akce v Kroměříži " + _rozsah(dny))


def _radek(t):
    kusy = []
    if t.get("vicedenni"):
        kusy.append("do " + _den(t["konec"][:10]))
    else:
        kusy.append(t["zacatek"][11:16].replace(":", "."))
    kusy.append(t.get("nazev", ""))
    for pole in ("typ", "misto"):
        if t.get(pole):
            kusy.append(t[pole])
    if t.get("zdarma"):
        kusy.append("zdarma")
    elif t.get("cena"):
        kusy.append("{0} Kč".format(t["cena"]))
    if t.get("pro_deti"):
        kusy.append("pro děti")
    radek = "- " + " | ".join(kusy)
    if t.get("perex") and t["perex"] != t.get("nazev"):
        radek += "\n  " + t["perex"][:400]
    return radek


def program_text(po_dnech, vystavy):
    """Fakta pro prompt. Totéž slouží pojistkám jako zdroj."""
    casti = []
    for den in sorted(po_dnech):
        casti.append("### {0} ({1})".format(_den(den), den))
        casti.extend(_radek(t) for t in po_dnech[den])
        if not po_dnech[den]:
            casti.append("- nic se nekoná")
        casti.append("")
    casti.append("### Výstavy a akce, které běží už od dřív a pokračují přes týden")
    casti.extend(_radek(t) for t in vystavy)
    if not vystavy:
        casti.append("- žádné")
    return "\n".join(casti)


def _zdroj_pojistek(program, dny):
    """Program plus data dní a časy i s dvojtečkou. Model napíše „ve 20:00"
    stejně legitimně jako „ve 20.00" a pojistka to nesmí brát jako vymyšlené."""
    kusy = [program.replace(".", " . ").replace(":", " : ")]
    for den in dny:
        d = datetime.strptime(den, "%Y-%m-%d")
        kusy.append("{0}. {1}. {2}".format(d.day, d.month, d.year))
    return program + "\n" + "\n".join(kusy)


def _snimek(t):
    return {k: t[k] for k in POLE_SNIMKU if k in t}


def zkontroluj(data, zdroj):
    """Stejné pojistky jako u zpráv, kromě opisování.

    Data jsou pod CC BY a doslovné převzetí dovolují. Názvy akcí mají navíc
    běžně osm a víc slov („Íránský poutník zpátky doma. Výstava ke 140.
    výročí…"), takže pojistka na opisování by hlásila jen falešné poplachy.
    """
    vystup = " ".join(
        [data["headline"]]
        + [o["text"] for o in data["tldr"]]
        + list(data["body"])
        + list(data["dny"].values())
        + [data.get("vystavy") or "", data.get("zaver") or ""])
    vymyslena = rewrite.zkontroluj_cisla(zdroj, vystup)
    if vymyslena:
        raise ValueError("Čísla, která v programu nejsou: {0}".format(", ".join(vymyslena)))
    if rewrite.zkontroluj_citace(vystup):
        raise ValueError("Výstup obsahuje uvozovky; názvy akcí piš bez nich.")
    kontakty = rewrite.zkontroluj_kontakty(vystup)
    if kontakty:
        raise ValueError("Výstup obsahuje kontaktní údaje: {0}".format(", ".join(kontakty)))
    slang = styl.zkontroluj_zakazany_slang(vystup)
    if slang:
        raise ValueError("Zakázané výrazy shazující lidi: {0}".format(", ".join(slang)))
    antiteze = styl.zkontroluj_antitezi(vystup)
    if antiteze:
        raise ValueError("Antiteze „A, ne B\": {0}".format(antiteze[0]))


def _over_tvar(data, dny):
    if len(data["tldr"]) != 3:
        raise ValueError("tldr nemá přesně 3 položky.")
    if not data["body"]:
        raise ValueError("Chybí úvod.")
    chybi = [d for d in dny if not (data["dny"].get(d) or "").strip()]
    if chybi:
        raise ValueError("Chybí komentář ke dnům: {0}".format(", ".join(chybi)))


def napis(dnes, pokusy=2):
    """Napíše a uloží pozvánku na týden, do kterého patří `dnes`. Vrací článek.

    Jeden opravný pokus s popisem chyby, stejně jako u přepisu zpráv.
    """
    dny = tyden(dnes)
    po_dnech, vystavy = rozdel(akce.nacti().get("terminy", []), dny)
    program = program_text(po_dnech, vystavy)
    zprava = POZVANKA_PROMPT.format(
        brand=config.BRAND, od=_den(dny[0]), do=_den(dny[-1]),
        ton=rewrite.TON_VOLNY, jazyk=styl.pravidla_jazyka(),
        proti_slopu=styl.PRAVIDLA_PROTI_SLOPU,
        klice_dnu=",\n".join('    "{0}": "1 až 3 věty k {1}"'.format(d, _den(d))
                             for d in dny),
        program=program,
    )
    zdroj = _zdroj_pojistek(program, dny)

    posledni = None
    for pokus in range(pokusy):
        try:
            data = rewrite._json(rewrite._zeptej_se(
                config.MODEL_REWRITE, zprava, config.MAX_TOKENS_REWRITE))
            _over_tvar(data, dny)
            zkontroluj(data, zdroj)
            break
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            posledni = exc
            if pokus < pokusy - 1:
                zprava += ("\n\n## Předchozí pokus neprošel\n{0}\n"
                           "Oprav přesně tohle a zbytek nech být.").format(exc)
    else:
        raise ValueError(str(posledni))

    clanek = {
        "id": id_pro(dny[0]),
        "typ": ZDROJ,
        "source": ZDROJ,
        "source_name": config.BRAND,
        "slug": slug_pro(dny),
        "headline": data["headline"].rstrip().rstrip("."),
        "tldr": data["tldr"],
        "body": data["body"],
        "tags": ["akce"],
        "dny": [{"den": d, "text": data["dny"][d].strip(),
                 "terminy": [_snimek(t) for t in po_dnech[d]]} for d in dny],
        "vystavy": [_snimek(t) for t in vystavy],
        "vystavy_text": (data.get("vystavy") or "").strip(),
        "zaver": (data.get("zaver") or "").strip() or ZAVER_ZALOHA,
        "published": _vydano(dny[0]),
        "rewritten_at": datetime.now(timezone.utc).isoformat(),
        "model": "stub" if config.BACKEND == "stub" else config.MODEL_REWRITE,
        "sensitivity": "volny",
    }
    store.uloz(clanek)
    return clanek


def _vydano(pondeli):
    """Teď, ale nejdřív pondělí 6:00. Pozvánka napsaná předem kvůli kontrole
    nesmí v archivu předběhnout týden, na který zve."""
    nejdriv = datetime.strptime(pondeli, "%Y-%m-%d").replace(hour=OD_HODINY)
    kdy = max(akce.ted(), nejdriv)
    try:
        from zoneinfo import ZoneInfo
        return kdy.replace(tzinfo=ZoneInfo("Europe/Prague")).isoformat()
    except Exception:                                 # noqa: BLE001
        return kdy.isoformat()


def v_cronu():
    """Volá `all`. Vrací nový článek, nebo None.

    Pády se počítají v `state.json` jako u zpráv. Bez toho by pozvánka, která
    neprojde pojistkami, platila dvě volání modelu každou hodinu dva dny.
    """
    from . import pipeline

    ted = akce.ted()
    clanek_id = id_pro(tyden(ted.date())[0])
    if not ma_vzniknout(ted, store.existuje(clanek_id)):
        return None
    pady = store.nacti_stav().get("selhani", {}).get(clanek_id, {}).get("pocet", 0)
    if pady >= config.MAX_SELHANI:
        return None
    try:
        return napis(ted.date())
    except Exception as exc:                          # noqa: BLE001
        pipeline._zapis_selhani(clanek_id, str(exc))
        raise
