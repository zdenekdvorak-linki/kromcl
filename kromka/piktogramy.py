# -*- coding: utf-8 -*-
"""Piktogramy k tématům, kreslené v kódu.

Fotky města přebírat nesmíme, takže si obrázky kreslíme sami. Inline SVG má
proti vygenerovanému rastru tři výhody, které se tady hodí všechny: nic se
nestahuje, obrázek se barví podle světlého i tmavého motivu, a protože má
pevný poměr stran, stránka při načítání nepohne layoutem.

Kreslí se jedním perem: viewBox 64×64, tah 5, hranaté konce. Každý piktogram
má oči. Jsou to postavy, ne značky z úřední cedule — na webu, který si dělá
legraci z úředního jazyka, by korektní piktogram byl ta nejhorší volba.
Oči nesou výraz, zbytek kresby nese informaci; proto je lze přidat i ke
stopkám nebo k urně, aniž by přestaly být stopkami a urnou.

Pět témat nese skutečné kroměřížské stavby: označník MHD, Květnou zahradu
shora, radniční věž na Velkém náměstí, kostel svatého Jana Křtitele a
arcibiskupský zámek jako výchozí značku. Kreslené jsou ty stavby, ne konkrétní
fotografie — stavby trvale umístěné na veřejném prostranství smí kdokoli
zobrazit (§ 33 autorského zákona), kdežto obkreslená cizí fotka by byla
odvozené dílo té fotky. Proto se nikdy nekreslí podle jediné předlohy.
"""

import html

VIEWBOX = "0 0 64 64"


def _oci(x1, x2, y, r=2.6):
    """Dvě oči. Vyplněné, bez tahu — třídu obarvuje CSS."""
    return ('<circle class="oko" cx="{0}" cy="{2}" r="{3}"/>'
            '<circle class="oko" cx="{1}" cy="{2}" r="{3}"/>').format(x1, x2, y, r)


# Každý tvar je seznam SVG elementů bez atributů tahu; ty doplní svg().
TVARY = {
    "doprava": [  # označník zastávky a autobus, co se těší
        '<path d="M14 56V20"/>',
        '<circle cx="14" cy="12" r="8"/>',
        '<rect x="26" y="24" width="30" height="24" rx="3"/>',
        '<path d="M26 37h30"/>',
        '<circle cx="34" cy="52" r="4"/>',
        '<circle cx="48" cy="52" r="4"/>',
        _oci(36, 46, 31),
        '<path d="M41 42q4 3 8 0"/>',  # úsměv pod předním sklem
    ],
    "kultura": [  # kostel sv. Jana Křtitele, kupole je hlava
        '<path d="M16 38a16 16 0 0 1 32 0"/>',
        '<path d="M32 16V8M28 12h8"/>',
        '<path d="M10 54V34l4-5 4 5v20"/>',
        '<path d="M46 54V34l4-5 4 5v20"/>',
        '<path d="M16 38v16M48 38v16"/>',
        '<path d="M6 54h52"/>',
        _oci(26, 38, 32),
        '<path d="M26 38q6 4 12 0"/>',
    ],
    "priroda": [  # Květná zahrada shora: rotunda a čtyři záhony v rozích
        '<rect x="6" y="6" width="52" height="52"/>',
        '<circle cx="32" cy="33" r="13"/>',
        '<path d="M32 20v-5"/>',
        '<rect x="11" y="11" width="7" height="7"/>',
        '<rect x="46" y="11" width="7" height="7"/>',
        '<rect x="11" y="46" width="7" height="7"/>',
        '<rect x="46" y="46" width="7" height="7"/>',
        _oci(27, 37, 31, 2.4),
        '<path d="M27 37q5 4 10 0"/>',
    ],
    "radnice": [  # radniční věž, ciferník je obličej
        '<path d="M32 4 18 16h28z"/>',
        '<rect x="19" y="16" width="26" height="38"/>',
        '<circle cx="32" cy="30" r="10"/>',
        '<path d="M12 54h40"/>',
        _oci(28, 36, 28, 2.2),
        '<path d="M28 34q4 3 8 0"/>',
    ],
    "skolstvi": [  # studentská čepice nasazená do čela
        '<path d="M4 26 32 13l28 13-28 12z"/>',
        '<path d="M16 33v11c0 4 32 4 32 0V33"/>',
        _oci(25, 39, 40),
        '<path d="M26 45q6 4 12 0"/>',
    ],
    "penize": [  # dvě mince, na spodní obličej
        '<ellipse cx="32" cy="17" rx="18" ry="7"/>',
        '<path d="M14 17v22c0 4 36 4 36 0V17"/>',
        _oci(25, 39, 30),
        '<path d="M26 36q6 4 12 0"/>',
    ],
    "sport": [  # stopky, ciferník je obličej
        '<circle cx="32" cy="38" r="18"/>',
        '<path d="M26 8h12"/>',
        '<path d="M32 8v12"/>',
        _oci(26, 38, 35),
        '<path d="M26 43q6 5 12 0"/>',
    ],
    "stavba": [  # jeřáb a náklad, co visí a kouká
        '<path d="M16 56V12"/>',
        '<path d="M7 56h18"/>',
        '<path d="M16 14h38"/>',
        '<path d="M44 14v14"/>',
        '<rect x="36" y="28" width="16" height="13"/>',
        _oci(41, 47, 33, 2.2),
    ],
    "volby": [  # urna se štěrbinou a lístkem
        '<rect x="8" y="30" width="48" height="24" rx="2"/>',
        '<path d="M23 30h18"/>',
        '<path d="m28 31 5-22 13 3-4 19z"/>',
        _oci(18, 28, 43, 2.2),
        '<path d="M19 48q4 3 8 0"/>',
    ],
    "lide": [  # dvě postavy, obě koukají
        '<circle cx="22" cy="22" r="9"/>',
        '<path d="M8 52c0-9 6-14 14-14s14 5 14 14"/>',
        '<circle cx="47" cy="27" r="7"/>',
        '<path d="M39 52c0-7 4-11 8-11s10 4 10 11"/>',
        _oci(19, 25, 21, 2.2),
        '<path d="M19 26q3 2.5 6 0"/>',
        _oci(44, 50, 26, 1.8),
    ],
    "akce": [  # kalendář, na kterém se něco chystá
        '<rect x="10" y="16" width="44" height="38" rx="3"/>',
        '<path d="M10 29h44"/>',
        '<path d="M22 10v10M42 10v10"/>',
        _oci(24, 40, 38, 3),
        '<path d="M24 44q8 6 16 0"/>',
    ],
    "plocha": [  # čtverečkovaná plocha, prostřední políčko kouká; karta m² v článku
        '<rect x="8" y="14" width="48" height="40"/>',
        '<path d="M8 27h48M8 41h48M24 14v40M40 14v40"/>',
        _oci(28, 36, 34, 2.4),
    ],
    # --- Typy akcí z otevřených dat města -------------------------------
    "kino": [  # klapka, spodní deska je obličej
        '<path d="M8 26h48v26H8z"/>',
        '<path d="M8 26 11 13l45 5-3 8z"/>',
        '<path d="M22 15v10M34 17v9M46 19v8"/>',
        _oci(26, 40, 36, 2.6),
        '<path d="M26 42q7 5 14 0"/>',
    ],
    "divadlo": [  # maska, která se dívá zpátky
        '<path d="M16 12h32v22c0 12-7 20-16 20s-16-8-16-20z"/>',
        '<path d="M16 20h-6M48 20h6"/>',
        _oci(25, 39, 30, 3),
        '<path d="M24 40q8 7 16 0"/>',
    ],
    "vystava": [  # obraz v rámu nad lavičkou
        '<rect x="8" y="10" width="48" height="36" rx="2"/>',
        '<rect x="16" y="18" width="32" height="20"/>',
        '<path d="M14 54h36"/>',
        _oci(27, 37, 26, 2.4),
        '<path d="M27 31q5 4 10 0"/>',
    ],
    "hudba": [  # nota s hlavou
        '<path d="M26 44V12l22-6"/>',
        '<path d="M26 20 48 14"/>',
        '<ellipse cx="18" cy="45" rx="10" ry="8"/>',
        _oci(14, 22, 44, 2.2),
        '<path d="M14 49q4 3 8 0"/>',
    ],
    "beseda": [  # bublina, co mluví a kouká
        '<path d="M8 12h48v32H34l-12 10V44H8z"/>',
        _oci(26, 38, 26, 3),
        '<path d="M26 32q6 5 12 0"/>',
    ],
    "zabava": [  # balonek
        '<ellipse cx="32" cy="26" rx="18" ry="20"/>',
        '<path d="M28 46h8l-4 6z"/>',
        '<path d="M32 52v8"/>',
        _oci(26, 38, 23, 3),
        '<path d="M26 31q6 5 12 0"/>',
    ],
    "jarmark": [  # stánek s plachtou
        '<path d="M8 24h48l-6-12H14z"/>',
        '<path d="M8 24v30M56 24v30"/>',
        '<path d="M4 54h56"/>',
        '<rect x="18" y="34" width="28" height="20"/>',
        _oci(27, 37, 42, 2.4),
        '<path d="M27 47q5 4 10 0"/>',
    ],
    # Výchozí značka: arcibiskupský zámek. Cibulová báň dělá účes.
    "_vychozi": [
        '<path d="M32 5c-11 6-12 11 0 15 12-4 11-9 0-15z"/>',
        '<rect x="20" y="20" width="24" height="24"/>',
        '<path d="M6 44h52v12H6z"/>',
        '<path d="M18 44v12M46 44v12"/>',
        _oci(27, 37, 30, 2.4),
        '<path d="M27 36q5 4 10 0"/>',
    ],
}

_PREVOD = {
    "školství": "skolstvi",
    "peníze": "penize",
    "příroda": "priroda",
    "lidé": "lide",
}


def pro_tema(tagy):
    """Název tvaru podle prvního tagu, který něco umíme nakreslit."""
    for tag in tagy or []:
        klic = _PREVOD.get(tag, tag)
        if klic in TVARY:
            return klic
    return "_vychozi"


# Typy akcí z číselníku otevřených dat. Klíčuje se názvem, ne číslem —
# číslo je interní identifikátor cizího systému a může se změnit, kdežto
# podle názvu je na první pohled vidět, co se kreslí.
_TYPY_AKCI = {
    "Divadlo": "divadlo",
    "Muzea, výstavy, galerie": "vystava",
    "Hudba a tanec": "hudba",
    "Kino": "kino",
    "Přednášky a besedy": "beseda",
    "Sport": "sport",
    "Zábava": "zabava",
    "Jarmarky, trhy a gastro": "jarmark",
}


def pro_typ_akce(nazev_typu):
    """Název tvaru pro typ akce. Neznámý typ dostane kalendář."""
    return _TYPY_AKCI.get((nazev_typu or "").strip(), "akce")


def svg(tema, trida="piktogram", popis=""):
    """Inline SVG. Dekorativní je schované čtečkám, popsané dostane title."""
    tvary = "".join(TVARY.get(tema, TVARY["_vychozi"]))
    if popis:
        pristupnost = ' role="img" aria-label="{0}"'.format(html.escape(popis, quote=True))
    else:
        pristupnost = ' aria-hidden="true" focusable="false"'
    return (
        '<svg class="{trida}" viewBox="{vb}"{a11y} fill="none" '
        'stroke="currentColor" stroke-width="5" stroke-linecap="square" '
        'stroke-linejoin="round">{tvary}</svg>'
    ).format(trida=trida, vb=VIEWBOX, a11y=pristupnost, tvary=tvary)


def dostupna_temata():
    return sorted(t for t in TVARY if not t.startswith("_"))
