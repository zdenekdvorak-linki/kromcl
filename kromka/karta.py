# -*- coding: utf-8 -*-
"""Víkendová karta: obrázek 1080 × 1920 do instagramového příběhu.

Každý build z programu vybere nejvýš šest akcí nejbližšího víkendu a nakreslí
je do karty na stálé adrese `/program/vikend-pribeh.png`. Na stránce víkendu
je na ni odkaz, aby ji mohli sdílet i čtenáři.

Výběr (rozhodnuto 24. 10. 2026, „pestrý výběr"):
  - jen jednodenní akce v sobotu a neděli; výstavy běží týdny a „na víkend"
    nejsou
  - nejvýš dvě projekce kina, jinak by karta byla program Nadsklepí
  - nejdřív až tři akce na den, pak doplnit podle času; čistě podle času by
    sobota mohla vytlačit celou neděli
  - stejná akce jen jednou, i když se hraje oba dny
  - výsledek seřazený podle začátku

Kreslí se v Pillow. Ten na každém stroji být nemusí — bez něj se karta
přeskočí a zbytek webu se postaví normálně.

Instagram v příběhu překrývá horních a spodních asi 250 px svým rozhraním,
proto je všechno podstatné mezi 250 a 1670.
"""

import re
from datetime import datetime
from pathlib import Path

from . import znacka

ROZMER = (1080, 1920)
MAX_AKCI = 6
MAX_KINO = 2
NA_DEN = 3

PAPIR = "#f5f3ee"
INKOUST = "#0c0c0c"
ZELENA = "#39E67A"
SEDA = "#55524c"
BILA = "#ffffff"

PISMA = Path(__file__).resolve().parent / "pisma"
MESICE = ["", "ledna", "února", "března", "dubna", "května", "června",
          "července", "srpna", "září", "října", "listopadu", "prosince"]
DNY = ("PO", "ÚT", "ST", "ČT", "PÁ", "SO", "NE")
# Jednopísmenné předložky a spojky nesmí zůstat na konci řádku.
_NESAMOSTATNE = {"a", "i", "k", "o", "s", "u", "v", "z", "A", "I", "K", "O",
                 "S", "U", "V", "Z"}


def vyber(terminy, dny):
    """Akce na kartu podle pravidla v hlavičce modulu."""
    kandidati = []
    videne = set()
    for t in sorted(terminy, key=lambda t: t.get("zacatek") or ""):
        if t.get("vicedenni") or (t.get("zacatek") or "")[:10] not in dny:
            continue
        klic = t.get("akce_id") or t.get("nazev")
        if klic in videne:
            continue
        videne.add(klic)
        kandidati.append(t)

    vybrane, kina = [], 0

    def pridej(t):
        nonlocal kina
        if t in vybrane or len(vybrane) >= MAX_AKCI:
            return
        if t.get("typ") == "Kino":
            if kina >= MAX_KINO:
                return
            kina += 1
        vybrane.append(t)

    for den in sorted(dny):
        za_den = 0
        for t in kandidati:
            if za_den >= NA_DEN:
                break
            if t["zacatek"][:10] == den and t not in vybrane:
                pred = len(vybrane)
                pridej(t)
                za_den += len(vybrane) - pred
    for t in kandidati:
        pridej(t)
    return sorted(vybrane, key=lambda t: t["zacatek"])


def rozsah_dnu(dny):
    """{"2026-10-24", "2026-10-25"} na „24.–25. října", přes měsíc
    „31. října – 1. listopadu"."""
    data = sorted(datetime.strptime(d, "%Y-%m-%d") for d in dny)
    od, do = data[0], data[-1]
    if od.month == do.month:
        return "{0}.–{1}. {2}".format(od.day, do.day, MESICE[do.month])
    return "{0}. {1} – {2}. {3}".format(od.day, MESICE[od.month], do.day, MESICE[do.month])


def _neodtrhavat(slovo):
    """Slovo, které česká typografie nenechá na konci řádku: jednopísmenná
    předložka nebo spojka a řadová číslovka („2. hokejová liga")."""
    return slovo in _NESAMOSTATNE or bool(re.match(r"^\d+\.$", slovo))


def zalom(text, sirka_textu, max_sirka, max_radku):
    """Zalomí text na řádky do šířky. Poslední řádek případně zkrátí výpustkou.

    `sirka_textu` je funkce text → šířka v pixelech, aby šlo zalamování
    testovat bez Pillow. Jednopísmenná předložka na konci řádku se přesune na
    další, jak chce česká typografie.
    """
    slova = text.split()
    radky, aktualni = [], []
    for slovo in slova:
        zkouska = " ".join(aktualni + [slovo])
        if aktualni and sirka_textu(zkouska) > max_sirka:
            presun = []
            if len(aktualni) > 1 and _neodtrhavat(aktualni[-1]):
                presun = [aktualni.pop()]
            radky.append(" ".join(aktualni))
            aktualni = presun + [slovo]
        else:
            aktualni.append(slovo)
    if aktualni:
        radky.append(" ".join(aktualni))

    if len(radky) > max_radku:
        radky = radky[:max_radku]
        posledni = radky[-1]
        while posledni and sirka_textu(posledni + "…") > max_sirka:
            posledni = posledni[:-1].rstrip()
        radky[-1] = posledni.rstrip(" ,.;:–-") + "…"
    return radky


def vytvor(terminy, dny, cil, ted=None):
    """Nakreslí kartu do `cil`. Vrací seznam vybraných akcí, nebo None,
    když není co kreslit nebo chybí Pillow.

    `ted` vyřadí akce, které už začaly: karta se přestavuje každou hodinu
    a v sobotu odpoledne by jinak nabízela dopolední program.
    """
    if ted is not None:
        hranice = ted.isoformat()
        terminy = [t for t in terminy if (t.get("zacatek") or "") >= hranice]
    akce = vyber(terminy, dny)
    if not akce:
        return None
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Víkendová karta se přeskakuje: chybí Pillow.")
        return None

    def pismo(nazev, velikost):
        return ImageFont.truetype(str(PISMA / nazev), velikost)

    syne = pismo("Syne-700.ttf", 96)
    den_pismo = pismo("Syne-700.ttf", 38)
    # Čas ve Space Grotesk: Syne má tak široké číslice, že „16.30" se do
    # sloupce nevešlo a usekla se jednička.
    cas_pismo = pismo("SpaceGrotesk-700.ttf", 40)
    tucne = pismo("SpaceGrotesk-700.ttf", 46)
    nazev_pismo = pismo("SpaceGrotesk-700.ttf", 33)
    misto_pismo = pismo("SpaceGrotesk-500.ttf", 26)
    pata_pismo = pismo("SpaceGrotesk-700.ttf", 34)

    obraz = Image.new("RGB", ROZMER, PAPIR)
    k = ImageDraw.Draw(obraz)
    sirka = ROZMER[0]

    # --- Hlavička: zelený pás do kraje, text v bezpečné zóně od 250 ---------
    # Pozice měřené z obrysu písma, ne odhadnuté: Syne v 96 px je vyšší,
    # než vypadá, a podtitul se s druhým řádkem dřív překrýval.
    radek1 = 262
    radek2 = k.textbbox((72, radek1), "KAM O", font=syne)[3] + 28
    pod = k.textbbox((72, radek2), "VÍKENDU", font=syne)[3] + 30
    podtitul = "v Kroměříži · {0}".format(rozsah_dnu(dny))
    # Spodek pásu z obrysu podtitulu i s dotahy (j v „října"), jinak se
    # písmena dotýkala černé linky.
    pas = k.textbbox((76, pod), podtitul, font=tucne)[3] + 30
    k.rectangle([0, 0, sirka, pas], fill=ZELENA)
    k.rectangle([0, pas, sirka, pas + 8], fill=INKOUST)
    k.text((72, radek1), "KAM O", font=syne, fill=INKOUST)
    k.text((72, radek2), "VÍKENDU", font=syne, fill=INKOUST)
    k.text((76, pod), podtitul, font=tucne, fill=INKOUST)

    # --- Karty akcí ---------------------------------------------------------
    # Šest karet a pata musí skončit nad spodní hranicí 1670.
    y, vyska, mezera = pas + 40, 146, 12
    levy, pravy, stin = 60, sirka - 60, 10
    sloupec = 160
    radkovani = 39
    for t in akce:
        k.rectangle([levy + stin, y + stin, pravy + stin, y + vyska + stin], fill=INKOUST)
        k.rectangle([levy, y, pravy, y + vyska], fill=BILA, outline=INKOUST, width=5)
        zacatek = datetime.fromisoformat(t["zacatek"])
        stred = levy + sloupec / 2
        k.text((stred, y + 52), DNY[zacatek.weekday()], font=den_pismo,
               fill=INKOUST, anchor="mm")
        k.text((stred, y + 98), "{0}.{1:02d}".format(zacatek.hour, zacatek.minute),
               font=cas_pismo, fill=INKOUST, anchor="mm")
        k.line([levy + sloupec, y + 5, levy + sloupec, y + vyska - 5], fill=INKOUST, width=4)

        x = levy + sloupec + 26
        max_sirka = pravy - x - 26
        radky = zalom(t.get("nazev", ""), nazev_pismo.getlength, max_sirka, 2)
        misto = t.get("misto") or "místo neuvedeno"
        if t.get("zdarma"):
            misto += " · zdarma"
        misto = zalom(misto, misto_pismo.getlength, max_sirka, 1)[0]

        # Blok názvu a místa svisle na střed karty. Jinak u jednořádkového
        # názvu zela uprostřed díra a dvouřádkový se tlačil na místo.
        blok = len(radky) * radkovani + 8 + 30
        ty = y + (vyska - blok) / 2
        for radek in radky:
            k.text((x, ty), radek, font=nazev_pismo, fill=INKOUST)
            ty += radkovani
        k.text((x, ty + 8), misto, font=misto_pismo, fill=SEDA)
        y += vyska + mezera

    # --- Pata: značka z kromka/znacka.py, ne písmeno ze Syne ---------------
    # Pod poslední kartou, ale nejvýš tak, aby skončila nad hranicí 1670.
    pata_y = min(y + 24, 1670 - 76)
    ikona = znacka.png(72)
    k.rectangle([60 - 4, pata_y - 4, 60 + 72 + 4, pata_y + 72 + 4], fill=INKOUST)
    obraz.paste(ikona, (60, pata_y))
    k.text((160, pata_y + 36), "Celý program na kromcl.cz",
           font=pata_pismo, fill=INKOUST, anchor="lm")

    cil = Path(cil)
    cil.parent.mkdir(parents=True, exist_ok=True)
    obraz.save(str(cil), optimize=True)
    return akce
