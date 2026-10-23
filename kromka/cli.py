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

    p = pod.add_parser("run", help="zpracuje nové články (nejnovější první)")
    p.add_argument("--limit", type=int, default=10)

    p = pod.add_parser("backfill", help="zpracuje archiv (nejstarší první)")
    p.add_argument("--limit", type=int, default=25)

    p = pod.add_parser("detail", help="stáhne a vypíše jeden článek bez volání API")
    p.add_argument("slug")

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

    if args.prikaz in ("run", "backfill", "all"):
        pipeline.davka(args.limit, nejstarsi=(args.prikaz == "backfill"))
        if args.prikaz != "all":
            return 0

    clanky = store.vsechny()
    pocet = render.vykresli(clanky)
    print("Vykresleno {0} souborů z {1} článků do {2}".format(pocet, len(clanky), config.SITE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
