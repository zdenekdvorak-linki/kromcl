# -*- coding: utf-8 -*-
"""Token stránky Kromcl na Facebooku do GitHub secretu.

Vstupem je dlouhodobý user token z Graph API Exploreru (appka „Kromcl
autopost", po „Extend Access Token" v Access Token Tool). Skript si z něj
vytáhne Page token stránky, ověří ho zkušebním dotazem a teprve pak ho
zapíše jako secret `KROMKA_FB_TOKEN` a ID stránky jako proměnnou
`KROMKA_FB_PAGE_ID`.

Page token odvozený z dlouhodobého user tokenu nevyprší, dokud se nezmění
heslo nebo se appce neodebere oprávnění.

Token se čte skrytým vstupem, ne z argv, a do `gh` jde přes stdin, takže
se neobjeví v process listu ani v historii terminálu. Na výstup jdou jen
ID a název stránky, nikdy hodnota tokenu.

Použití z kořene projektu (potřebuje přihlášené `gh`):

    python bin/fb_token.py                  # stránka s názvem Kromcl
    python bin/fb_token.py --stranka Jina   # jiný název stránky
"""

import argparse
import getpass
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

GRAPH = "https://graph.facebook.com/v26.0"
REPO = "zdenekdvorak-linki/kromcl"


class Odmitnuto(Exception):
    """Token neprošel; skript se zeptá znovu."""


def _get(cesta, token, **parametry):
    parametry["access_token"] = token
    url = "{0}/{1}?{2}".format(GRAPH, cesta, urllib.parse.urlencode(parametry))
    try:
        with urllib.request.urlopen(url, timeout=30) as odpoved:
            return json.load(odpoved)
    except urllib.error.HTTPError as chyba:
        # Tělo chyby token neobsahuje, jen popis; URL s tokenem se nevypisuje.
        try:
            popis = json.load(chyba).get("error", {}).get("message", "")
        except ValueError:
            popis = ""
        raise Odmitnuto("Graph API vrátilo {0}: {1}".format(chyba.code, popis))


def najdi_stranku(user_token, nazev):
    """Page token stránky podle názvu. Prochází i další stránky výsledků."""
    data = _get("me/accounts", user_token, fields="id,name,access_token", limit=100)
    videne = []
    while True:
        for stranka in data.get("data", []):
            videne.append(stranka["name"])
            if stranka["name"].strip().lower() == nazev.lower():
                return stranka
        dalsi = data.get("paging", {}).get("next")
        if not dalsi:
            break
        with urllib.request.urlopen(dalsi, timeout=30) as odpoved:
            data = json.load(odpoved)
    raise Odmitnuto(
        "Stránka „{0}“ v /me/accounts není. Vidím: {1}.\n"
        "Při generování tokenu musí být v okně souhlasu zaškrtnutá. Když patří "
        "pod business portfolio, je potřeba i oprávnění business_management."
        .format(nazev, ", ".join(videne) or "nic")
    )


def over(stranka):
    """Zkušební dotaz Page tokenem a kontrola, že token nevyprší."""
    token = stranka["access_token"]
    ja = _get("me", token, fields="id,name")
    if ja.get("id") != stranka["id"]:
        raise Odmitnuto("Token nepatří stránce {0}, ale {1}.".format(stranka["id"], ja.get("id")))
    info = _get("debug_token", token, input_token=token).get("data", {})
    chybi = {"pages_manage_posts", "pages_read_engagement"} - set(info.get("scopes", []))
    if chybi:
        raise Odmitnuto("Tokenu chybí oprávnění: {0}".format(", ".join(sorted(chybi))))
    return info.get("expires_at", 0)


def _kdy(timestamp):
    if not timestamp:
        return "bez omezení"
    from datetime import datetime
    return "do " + datetime.fromtimestamp(timestamp).strftime("%d. %m. %Y %H:%M")


def ze_schranky():
    """Token ze schránky, schránka se pak vymaže. Windows i macOS.

    Skrytý vstup přes getpass na Windows nebere Ctrl+V, v některých
    terminálech tak vložení skončí jako nesmysl. Ze schránky to nehrozí.
    """
    if sys.platform == "win32":
        cist = ["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"]
        smazat = ["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value ' '"]
    else:
        cist, smazat = ["pbpaste"], ["pbcopy"]
    token = subprocess.run(cist, capture_output=True, check=True).stdout.decode("utf-8", "replace").strip()
    subprocess.run(smazat, input=b"", check=False)
    return token


def zapis(stranka):
    subprocess.run(
        ["gh", "secret", "set", "KROMKA_FB_TOKEN", "--repo", REPO],
        input=stranka["access_token"].encode("utf-8"), check=True,
    )
    subprocess.run(
        ["gh", "variable", "set", "KROMKA_FB_PAGE_ID", "--repo", REPO,
         "--body", stranka["id"]],
        check=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stranka", default="Kromcl", help="název stránky na FB")
    parser.add_argument("--schranka", action="store_true",
                        help="vezmi token ze schránky (a pak ji vymaž) místo vkládání")
    args = parser.parse_args()

    if args.schranka:
        user_token = ze_schranky()
        if not user_token.startswith("EAA"):
            sys.exit("Ve schránce není token z Facebooku (začíná na EAA). Nic se nezapsalo.")
        try:
            stranka = najdi_stranku(user_token, args.stranka)
            vyprsi = over(stranka)
            user_vyprsi = _get("debug_token", user_token, input_token=user_token) \
                .get("data", {}).get("expires_at", 0)
        except Odmitnuto as chyba:
            sys.exit(str(chyba))
        if vyprsi:
            sys.exit("Token stránky má omezenou platnost. User token platí {0}, token "
                     "stránky {1}. Nic se nezapsalo.".format(_kdy(user_vyprsi), _kdy(vyprsi)))
        zapis(stranka)
        print("Stránka: {0} (ID {1}), token nevyprší".format(stranka["name"], stranka["id"]))
        print("Zapsáno: secret KROMKA_FB_TOKEN, proměnná KROMKA_FB_PAGE_ID v {0}".format(REPO))
        return

    # Po odmítnutí se ptá znovu, místo aby skončil: druhé vložení by jinak
    # dopadlo na příkazový řádek a token by zůstal v historii shellu.
    while True:
        user_token = getpass.getpass("Dlouhodobý user token (vstup se nezobrazuje, "
                                     "prázdný Enter = konec): ").strip()
        if not user_token:
            sys.exit("Nic se nezapsalo.")
        try:
            stranka = najdi_stranku(user_token, args.stranka)
            vyprsi = over(stranka)
            if not vyprsi:
                break
            user_vyprsi = _get("debug_token", user_token, input_token=user_token) \
                .get("data", {}).get("expires_at", 0)
        except Odmitnuto as chyba:
            print(chyba)
            continue
        # Krátkodobý token by za hodinu přestal fungovat a cron by tiše selhával.
        print("Token stránky má omezenou platnost. Vložený user token platí {0}, "
              "token stránky {1}.".format(_kdy(user_vyprsi), _kdy(vyprsi)))
        print("Je potřeba token z Access Token Tool po Extend Access Token "
              "(platí asi 60 dní), ne ten z pole v Exploreru (platí hodinu či dvě).")
    zapis(stranka)

    print("Stránka: {0} (ID {1}), token nevyprší".format(stranka["name"], stranka["id"]))
    print("Zapsáno: secret KROMKA_FB_TOKEN, proměnná KROMKA_FB_PAGE_ID v {0}".format(REPO))


if __name__ == "__main__":
    main()
