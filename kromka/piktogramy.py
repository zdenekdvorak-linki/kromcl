# -*- coding: utf-8 -*-
"""Piktogramy k tématům, kreslené v kódu.

Fotky města přebírat nesmíme, takže si obrázky kreslíme sami. Inline SVG má
proti vygenerovanému rastru tři výhody, které se tady hodí všechny: nic se
nestahuje, obrázek se barví podle světlého i tmavého motivu, a protože má
pevný poměr stran, stránka při načítání nepohne layoutem.

Kreslí se jedním perem: viewBox 64×64, tah 5, hranaté konce. Stejná logika
jako zbytek webu — tlustá čára a žádné výplně.

Pět témat nese skutečné kroměřížské stavby: označník MHD, Květnou zahradu
shora, radniční věž na Velkém náměstí, kostel svatého Jana Křtitele a
arcibiskupský zámek jako výchozí značku. Kreslené jsou ty stavby, ne konkrétní
fotografie — stavby trvale umístěné na veřejném prostranství smí kdokoli
zobrazit (§ 33 autorského zákona), kdežto obkreslená cizí fotka by byla
odvozené dílo té fotky. Proto se nikdy nekreslí podle jediné předlohy.

Zbylá témata zůstávají abstraktní. Vymýšlet ke „sportu" kroměřížskou budovu
na sílu by dopadlo hůř než poctivé stopky.
"""

import html

VIEWBOX = "0 0 64 64"

# Každý tvar je seznam SVG elementů bez atributů tahu; ty doplní _svg().
TVARY = {
    "doprava": [  # kulatý označník zastávky a autobus za ním
        '<path d="M14 56V20"/>',
        '<circle cx="14" cy="12" r="8"/>',
        '<rect x="26" y="24" width="30" height="24" rx="3"/>',
        '<path d="M26 36h30"/>',
        '<circle cx="34" cy="52" r="4"/>',
        '<circle cx="48" cy="52" r="4"/>',
    ],
    "kultura": [  # kostel svatého Jana Křtitele: kupole mezi dvěma věžemi
        '<path d="M20 36a12 12 0 0 1 24 0"/>',
        '<rect x="29" y="14" width="6" height="8"/>',
        '<path d="M32 14V8"/>',
        '<path d="M12 54V30l5-6 5 6v24"/>',
        '<path d="M42 54V30l5-6 5 6v24"/>',
        '<path d="M20 36v18M44 36v18"/>',
        '<path d="M6 54h52"/>',
    ],
    "sport": [  # stopky
        '<circle cx="32" cy="38" r="18"/>',
        '<path d="M32 38V27"/>',
        '<path d="M26 8h12"/>',
        '<path d="M32 8v8"/>',
    ],
    "skolstvi": [  # studentská čepice
        '<path d="M6 26 32 14l26 12-26 12z"/>',
        '<path d="M18 32v12c0 3 28 3 28 0V32"/>',
    ],
    "penize": [  # sloupec mincí
        '<ellipse cx="32" cy="18" rx="18" ry="7"/>',
        '<path d="M14 18v11c0 4 36 4 36 0V18"/>',
        '<path d="M14 29v11c0 4 36 4 36 0V29"/>',
    ],
    "stavba": [  # jeřáb
        '<path d="M16 56V12"/>',
        '<path d="M7 56h18"/>',
        '<path d="M16 14h38"/>',
        '<path d="M44 14v14"/>',
        '<rect x="37" y="28" width="14" height="11"/>',
    ],
    "radnice": [  # radniční věž na Velkém náměstí
        '<path d="M32 2 23 13h18z"/>',
        '<rect x="24" y="13" width="16" height="43"/>',
        '<circle cx="32" cy="26" r="5"/>',
        '<path d="M24 42h16"/>',
        '<path d="M12 56h40"/>',
    ],
    "volby": [  # urna se štěrbinou a lístkem, který do ní padá
        '<rect x="8" y="30" width="48" height="24" rx="2"/>',
        '<path d="M23 30h18"/>',
        '<path d="m28 31 5-22 13 3-4 19z"/>',
    ],
    "priroda": [  # Květná zahrada shora: rotunda uprostřed radiálního parteru
        '<rect x="6" y="6" width="52" height="52"/>',
        '<circle cx="32" cy="32" r="9"/>',
        '<path d="M32 23v-4"/>',
        '<path d="m25 25-8-8M39 25l8-8M25 39l-8 8M39 39l8 8"/>',
        '<path d="M32 6v8M32 50v8M6 32h8M50 32h8"/>',
    ],
    "lide": [  # dvě postavy
        '<circle cx="22" cy="22" r="8"/>',
        '<path d="M8 52c0-9 6-14 14-14s14 5 14 14"/>',
        '<circle cx="46" cy="26" r="6"/>',
        '<path d="M38 52c0-7 4-11 8-11s10 4 10 11"/>',
    ],
    "akce": [  # kalendář s hvězdou
        '<rect x="10" y="16" width="44" height="38" rx="3"/>',
        '<path d="M10 29h44"/>',
        '<path d="M22 10v10M42 10v10"/>',
        '<path d="m32 34 3 7 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1z"/>',
    ],
    # Když téma nesedí na nic z výše uvedeného: arcibiskupský zámek, tedy
    # cibulová báň nad věží a dlouhé křídlo. Pořád Kroměříž, ne obecný otazník.
    "_vychozi": [
        '<path d="M32 2c-7 8-8 13 0 17 8-4 7-9 0-17z"/>',
        '<path d="M29 19h6v5h-6z"/>',
        '<rect x="24" y="24" width="16" height="22"/>',
        '<circle cx="32" cy="33" r="4"/>',
        '<path d="M6 46h52v10H6z"/>',
        '<path d="M18 46v10M46 46v10"/>',
    ],
}

# Tagy ze slovníku článků mají diakritiku, soubory tvarů ne.
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
