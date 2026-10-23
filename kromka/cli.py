# -*- coding: utf-8 -*-
"""Příkazová řádka: python -m kromka <prikaz>"""

import argparse
import json
import sys

from . import config, pipeline, render, sources, store


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

    p = pod.add_parser("slovnik", help="vypíše nebo rozšíří slovník jazyka")
    p.add_argument("--pridej", metavar="VÝRAZ",
                   help="nový výraz; doptá se na zbytek")
    p.add_argument("--stav", default="zive",
                   choices=["zive", "ironicke", "zastarale", "zakazane"])

    pod.add_parser("build", help="vykreslí statický web ze uložených JSONů")
    p = pod.add_parser("all", help="run + build")
    p.add_argument("--limit", type=int, default=10)

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

    if args.prikaz in ("run", "backfill", "all"):
        # `run` i `all` jedou v cronu, takže se archivu nedotknou, dokud se to
        # výslovně nepovolí. Jinak by hodinový běh archiv sežral sám.
        jen_novejsi = args.prikaz in ("run", "all") and not getattr(args, "i_archiv", False)
        pipeline.davka(args.limit, nejstarsi=(args.prikaz == "backfill"),
                       jen_novejsi=jen_novejsi)
        if args.prikaz != "all":
            return 0

    clanky = store.vsechny()
    pocet = render.vykresli(clanky)
    print("Vykresleno {0} souborů z {1} článků do {2}".format(pocet, len(clanky), config.SITE))
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
