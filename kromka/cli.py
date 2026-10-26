# -*- coding: utf-8 -*-
"""Příkazová řádka: python -m kromka <prikaz>"""

import argparse
import json
import sys

from . import (akce, config, facebook, indexnow, kino_dk, pipeline, pozvanka, prispevky,
               render, sources, store)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="kromka", description="Přepis zpráv města do jazyka mladých")
    pod = parser.add_subparsers(dest="prikaz", required=True)

    p = pod.add_parser("nove", help="vypíše, co je ve feedu a ještě nemá přepis")
    p.add_argument("--limit", type=int, default=20)

    p = pod.add_parser("run", help="zpracuje jen opravdu nové články (pro cron)")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--i-archiv", action="store_true",
                   help="ber i nezpracovaný archiv, ne jen články novější než poslední hotový")

    p = pod.add_parser("backfill", help="zpracuje archiv (nejstarší první)")
    p.add_argument("--limit", type=int, default=25)

    p = pod.add_parser("detail", help="stáhne a vypíše jeden článek bez volání API")
    p.add_argument("slug")

    p = pod.add_parser("akce", help="stáhne program akcí z otevřených dat města")
    p.add_argument("--dni", type=int, default=config.AKCE_DNI)
    p.add_argument("--vynutit", action="store_true",
                   help="stáhni, i když jsou uložená data ještě čerstvá")
    p.add_argument("--bez-kina", action="store_true",
                   help="nedoplňuj stopáž a přístupnost ze stránek Domu kultury")

    p = pod.add_parser("slovnik", help="vypíše nebo rozšíří slovník jazyka")
    p.add_argument("--pridej", metavar="VÝRAZ",
                   help="nový výraz; doptá se na zbytek")
    p.add_argument("--stav", default="zive",
                   choices=["zive", "ironicke", "zastarale", "zakazane"])

    p = pod.add_parser("doklad", help="doloží u článků, že nevznikly opsáním")
    p.add_argument("slug", nargs="?", help="jeden článek; bez něj souhrn za všechny")

    p = pod.add_parser("pozvanka", help="napíše týdenní pozvánku na akce")
    p.add_argument("--tyden", metavar="YYYY-MM-DD",
                   help="kterýkoli den týdne; bez něj tenhle týden")
    p.add_argument("--vynutit", action="store_true",
                   help="napiš ji znovu, i když už pro ten týden existuje")

    p = pod.add_parser("prispevky", help="zpracuje schválené příspěvky čtenářů a postaví web")
    p.add_argument("--nanecisto", action="store_true",
                   help="jen vypiš, co je v tabulce ke zpracování")

    pod.add_parser("build", help="vykreslí statický web ze uložených JSONů")
    p = pod.add_parser("all", help="run + build")
    p.add_argument("--limit", type=int, default=10)

    p = pod.add_parser("indexnow", help="nahlásí Bingu a Seznamu adresy z fronty (po nasazení)")
    p.add_argument("--vse", action="store_true",
                   help="nahlas celý web ze sitemapy, ne jen frontu")
    p.add_argument("--nanecisto", action="store_true",
                   help="jen vypiš, co by se poslalo")

    p = pod.add_parser("facebook", help="pošle nejstarší článek z fronty na stránku Kromcl (po nasazení)")
    p.add_argument("--nanecisto", action="store_true",
                   help="jen vypiš frontu a text příspěvku, nic neposílej")

    args = parser.parse_args(argv)

    if args.prikaz == "nove":
        polozky = pipeline.nove_polozky(limit=args.limit)
        for polozka in polozky:
            print("{0}  {1}".format(polozka["published"][:10], polozka["title"]))
        print("\nCelkem čeká: {0}".format(len(pipeline.nove_polozky())))
        return 0

    if args.prikaz == "detail":
        zdroj = sources.podle_id("mesto-kromeriz")
        polozka = {"source": "mesto-kromeriz", "source_name": zdroj.SOURCE_NAME,
                   "slug": args.slug, "id": "mesto-kromeriz:" + args.slug,
                   "title": "", "perex": "", "published": "",
                   "url": zdroj.DETAIL.format(args.slug)}
        zdroj.fetch_detail(polozka)
        print(json.dumps(polozka, ensure_ascii=False, indent=2))
        return 0

    if args.prikaz == "slovnik":
        return _slovnik(args)

    if args.prikaz == "doklad":
        return _doklad(args)

    if args.prikaz == "indexnow":
        return _indexnow(args)

    if args.prikaz == "facebook":
        return _facebook(args)

    if args.prikaz == "pozvanka":
        return _pozvanka(args)

    if args.prikaz == "prispevky":
        if not prispevky.zapnuto():
            print("Příspěvky nejsou nastavené (KROMKA_PRISPEVKY_URL a _KLIC).")
            return 1
        if args.nanecisto:
            for radek in prispevky.nacti():
                print("{0:12s} {1}".format(radek.get("stav", ""), radek.get("nadpis", "")))
            return 0
        prispevky.v_cronu()

    if args.prikaz in ("akce", "all"):
        _akce(args)
        if args.prikaz == "akce":
            return 0

    if args.prikaz in ("run", "backfill", "all"):
        # `run` i `all` jedou v cronu, takže se archivu nedotknou, dokud se to
        # výslovně nepovolí. Jinak by hodinový běh archiv sežral sám.
        jen_novejsi = args.prikaz in ("run", "all") and not getattr(args, "i_archiv", False)
        hotove = pipeline.davka(args.limit, nejstarsi=(args.prikaz == "backfill"),
                                jen_novejsi=jen_novejsi)
        if args.prikaz != "all":
            return 0
        # Jen `all` končí nasazením; odešle se až po něm (příkaz indexnow).
        nova = _pozvanka_v_cronu()
        if nova:
            hotove = list(hotove or []) + [nova]
        hotove = list(hotove or []) + prispevky.v_cronu()
        if hotove:
            indexnow.zarad(indexnow.adresy(hotove))
            facebook.zarad(hotove)

    clanky = store.vsechny()
    pocet = render.vykresli(clanky)
    print("Vykresleno {0} souborů z {1} článků do {2}".format(pocet, len(clanky), config.SITE))
    return 0


def _indexnow(args):
    """Odešle frontu z posledního `all`, nebo s --vse celou sitemapu.

    Ve workflow běží až po nasazení, aby vyhledávač na nahlášené adrese
    našel novou verzi. Fronta se maže jen po úspěchu.
    """
    adresy = indexnow.z_sitemapy() if args.vse else indexnow.ve_fronte()
    if args.nanecisto:
        print("\n".join(indexnow.telo(adresy)["urlList"]) or "Fronta je prázdná.")
        return 0
    ok, zprava = indexnow.odesli(adresy)
    print(zprava)
    if ok and not args.vse:
        indexnow.vyprazdni_frontu()
    return 0 if ok else 1


def _facebook(args):
    """Pošle frontu z posledního `all` na stránku Kromcl.

    Ve workflow běží až po nasazení, aby Facebook na adrese našel článek
    i kartu og:image. Chyba vrací 0: neodeslaný článek zůstává ve frontě
    a výpadek Facebooku nemá v Actions svítit jako rozbitý web.
    """
    if args.nanecisto:
        fronta = facebook.nacti()["fronta"]
        if not fronta:
            print("Fronta je prázdná.")
        for polozka in fronta:
            clanek = store.nacti(polozka["id"])
            print("{0}  {1}\n{2}\n{3}\n".format(
                polozka["zarazeno"], clanek["headline"], facebook.odkaz(clanek),
                facebook.text(clanek)))
        return 0
    if not facebook.zapnuto():
        print("Facebook není nastavený (KROMKA_FB_PAGE_ID a KROMKA_FB_TOKEN), přeskakuju.")
        return 0
    for radek in facebook.odesli() or ["Fronta je prázdná."]:
        print(radek)
    return 0


def _pozvanka(args):
    """Ruční běh pozvánky. Hotový JSON se jinak nepřepisuje (princip 5)."""
    from datetime import date

    den = date.fromisoformat(args.tyden) if args.tyden else akce.ted().date()
    clanek_id = pozvanka.id_pro(pozvanka.tyden(den)[0])
    if store.existuje(clanek_id) and not args.vynutit:
        print("Pozvánka {0} už existuje; přepsat jde jen s --vynutit.".format(clanek_id))
        return 1
    clanek = pozvanka.napis(den)
    akci = sum(len(d["terminy"]) for d in clanek["dny"])
    print("Napsáno: {0}\n  /clanek/{1}.html\n  {2} akcí po dnech, {3} výstav".format(
        clanek["headline"], clanek["slug"], akci, len(clanek["vystavy"])))
    return 0


def _pozvanka_v_cronu():
    """V pondělí a úterý pozvánka, jinak nic. Chyba nesmí shodit zprávy."""
    try:
        return pozvanka.v_cronu()
    except Exception as exc:                          # noqa: BLE001
        print("Pozvánka nevznikla ({0}).".format(exc), file=sys.stderr)
        return None


def _akce(args):
    """Stáhne program a doplní k projekcím údaje z webu Domu kultury.

    Volá se i z `all`, tedy z hodinového cronu. Stahování se tam přeskočí,
    dokud jsou uložená data mladší než config.AKCE_MAX_STARI_HODIN — jinak
    by se 574 kB tahalo čtyřiadvacetkrát denně.
    """
    try:
        data = akce.aktualizuj(dni=getattr(args, "dni", None),
                               vynutit=getattr(args, "vynutit", False))
    except Exception as exc:                          # noqa: BLE001
        # Výpadek otevřených dat nesmí shodit `all` — to by se v cronu
        # nenasadily ani zprávy. Zůstane poslední uložený program.
        print("Program se nepodařilo stáhnout ({0}), zůstává uložený.".format(exc),
              file=sys.stderr)
        return akce.nacti()
    if not getattr(args, "bez_kina", False) and data.get("terminy"):
        puvodni = sum(1 for t in data["terminy"] if t.get("kino"))
        kino_dk.doplnit(data["terminy"])
        if sum(1 for t in data["terminy"] if t.get("kino")) != puvodni:
            akce.uloz(data)
    return data


def _doklad(args):
    """Vypíše, jak moc se články shodují s oznámením, ze kterého vznikly.

    Měří se znovu z uloženého snímku zdroje, ne z hodnot zapsaných při
    vzniku — jinak by to byl jen opis vlastního tvrzení.
    """
    from . import rewrite

    clanky = store.vsechny()
    if args.slug:
        clanky = [c for c in clanky if c["slug"] == args.slug]
        if not clanky:
            print("Článek {0!r} neznám.".format(args.slug))
            return 1

    bez_snimku = []
    nejhorsi = []
    for clanek in clanky:
        snimek = clanek.get("zdroj_snimek")
        if not snimek:
            bez_snimku.append(clanek["slug"])
            continue
        zdroj = snimek["titulek"] + "\n\n" + snimek["text"]
        vystup = " ".join([clanek["headline"]]
                          + [o["text"] for o in clanek.get("tldr", [])]
                          + clanek.get("body", []))
        delka, ukazka = rewrite.nejdelsi_shoda(zdroj, vystup)
        nejhorsi.append((delka, clanek["slug"], ukazka))
        if args.slug:
            print("Článek   : {0}".format(clanek["headline"]))
            print("Oznámení : {0}".format(snimek["titulek"]))
            print("Zdroj    : {0}".format(snimek["url"]))
            print("Nejdelší shodná sekvence: {0} slov (práh je 8)".format(delka))
            if ukazka:
                print("           „{0}\"".format(ukazka))
            print("Přímé citace: {0} | kontaktní údaje: {1}".format(
                len(rewrite.zkontroluj_citace(vystup) and [1] or []),
                len(rewrite.zkontroluj_kontakty(vystup))))

    if args.slug:
        return 0

    nejhorsi.sort(reverse=True)
    print("Změřeno článků: {0}".format(len(nejhorsi)))
    if bez_snimku:
        print("Bez uloženého snímku zdroje (vznikly před zavedením dokladu): "
              "{0}".format(len(bez_snimku)))
    if nejhorsi:
        prumer = sum(d for d, _, _ in nejhorsi) / float(len(nejhorsi))
        print("Nejdelší shodná sekvence: průměr {0:.1f} slova, maximum {1}".format(
            prumer, nejhorsi[0][0]))
        print("Nad prahem 8 slov: {0}".format(sum(1 for d, _, _ in nejhorsi if d >= 8)))
        print("\nNejvyšší shody:")
        for delka, slug, ukazka in nejhorsi[:5]:
            print("  {0:2d} slov  {1}".format(delka, slug[:58]))
            if ukazka:
                print("           „{0}\"".format(ukazka[:80]))
    return 0


def _slovnik(args):
    """Výpis nebo doplnění slovníku. Doptá se jen na to, co nelze uhodnout."""
    from . import styl

    if not args.pridej:
        for stav in ("zive", "ironicke", "zastarale", "zakazane"):
            polozky = styl.vyrazy(stav)
            if not polozky:
                continue
            print("\n== {0} ({1}) ==".format(stav, len(polozky)))
            for v in polozky:
                misto = ", ".join(v.get("misto") or []) or "—"
                print("  {0:14s} místo: {1}".format(v["vyraz"], misto))
        print("\nPřidání: python -m kromka slovnik --pridej <výraz>")
        return 0

    data = styl.nacti_slovnik()
    if any(v["vyraz"].lower() == args.pridej.lower() for v in data["vyrazy"]):
        print("Výraz {0!r} už ve slovníku je.".format(args.pridej))
        return 1

    print("Přidávám {0!r} jako {1}.".format(args.pridej, args.stav))
    vyznam = input("Co to znamená? ").strip()
    misto = input("Místo jakých běžných slov se to říká? (oddělenÉ čárkou) ").strip()
    tvary = input("Další tvary, pokud nějaké jsou? (čárkou) ").strip()
    duvod = ""
    if args.stav == "zakazane":
        duvod = input("Proč je zakázané? ").strip()

    novy = {
        "vyraz": args.pridej,
        "misto": [m.strip() for m in misto.split(",") if m.strip()],
        "vyznam": vyznam,
        "tvary": [t.strip() for t in tvary.split(",") if t.strip()],
        "stav": args.stav,
        "zdroj": "doma ověřeno",
    }
    if duvod:
        novy["duvod"] = duvod
    data["vyrazy"].append(novy)
    styl.zapis_slovnik(data)
    print("Uloženo. Slovník má teď {0} výrazů.".format(len(data["vyrazy"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
