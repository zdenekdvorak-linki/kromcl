# Testy

Jen to, co nevolá síť ani model. Spuštění z kořene projektu:

```bash
python -m unittest discover -s tests
```

Vzorky jsou ručně vyrobené a vycházejí ze skutečných titulků a HTML z webu
města, ne z náhodných produkčních dat.

## `test_kromka.py`

### Slugify — pravidla ověřená proti živým URL

| Vstup | Očekávaný výstup | Co hlídá |
|---|---|---|
| `V Kroměříži přibude pět nových informačních odjezdových tabulí` | `v-kromerizi-pribude-pet-novych-informacnich-odjezdovych-tabuli` | základní tvar |
| `… uspoří zhruba 1,2 milionu korun` | `…-zhruba-12-milionu-korun` | čárka se **maže**, nedělá pomlčku |
| `… domovu 53.245 korun` | `…-domovu-53245-korun` | tečka v tisících se maže |
| `VIDEO: Kroměříž má nový územní plán` | `video-kromeriz-ma-novy-uzemni-plan` | dvojtečka se maže, mezera dělá pomlčku |
| `Koncepce na roky 2027–2032` | `koncepce-na-roky-2027-2032` | dlouhá pomlčka je oddělovač |
| `Rada města` | `rada-mesta` | mezera zůstává oddělovačem |
| `Uspoří 1,2 milionu` (záloha) | `uspori-1-2-milionu` | záložní varianta dělá pomlčky |

### Pojistka na čísla

| Zdroj | Výstup | Očekávání |
|---|---|---|
| `Ročně najedou 340 tisíc km` | `Najedou 340 tisíc km` | projde |
| `Přibudou tabule` | `Přibude 7 tabulí` | **zachytí `7`** |
| `Přibude pět tabulí na třech zastávkách` | `5 tabulí na 3 zastávkách` | projde (číslovky slovy) |
| `přepraví zhruba jeden milion cestujících` | `sveze 1000000 lidí` | projde |
| `Rada rozhodla` + datum článku | `Rada rozhodla 23. října` | projde (datum je povolené) |
| `vynesla 53 245 korun` | `vynesla 53245 korun` | projde (mezera v čísle) |
| `vážila 2.360 g` | `vážila 2360 g` | projde (česká tisícová tečka) |
| `v 13.46 hodin` | `ve 1346 hodin` | **zachytí** (dvě číslice za tečkou jsou desetinná část) |
| `Loni se narodilo 398 dětí` + datum 2025 | `V roce 2024…` | projde (rok o jedna vedle vydání) |
| totéž | `V roce 2019…` | **zachytí `2019`** |

### Co se nepočítá jako vlastní slovo

Nález na osm slov v řadě musí obsahovat pět vlastních slov. Jména ze
zdroje, data, čísla, spojky a ustálené termíny se nepočítají — mají jediný
správný tvar. Poslední test hlídá, že pojistka po těch výjimkách pořád
funguje.

| Výstup proti oznámení | Očekávání |
|---|---|
| výčet `z Břeclavi, Tábora, Znojma, Chebu, Pelhřimova…` | projde |
| `od 6. prosince 2024 do 2. března 2025` | projde |
| `místostarosta Pavel Motyčka, který má sociální oblast na starost` | projde |
| `partnerské město Râmnicu Vâlcea` | projde (cizí diakritika) |
| `Radnice chce v příštím roce opravit chodníky v celé čtvrti` | **zachytí** |

### Pojistka na skoro totožné věty

Díra, kterou kontrola na osm slov v řadě sama neuhlídá: když se záměny rozsypou
po celé větě, řetěz se nikde nenaváže. Práh je **0,65** a je měřený na
archivu: maskované kopie vycházejí 0,68 až 0,71, vlastní věty s týmiž fakty
0,55 až 0,62. Starší hodnota 0,55 stála na čtyřech ručních vzorcích a
archiv ji vyvrátil — deset vlastních vět pod ní spadlo.

| Výstup proti stejnému oznámení | Očekávání |
|---|---|
| `…autobusové **přepravy**… budou **umístěny** nové **digitální** tabule…` | zachytí (osm slov v řadě to propustí) |
| `…**městské** dopravy… **vzniknou** nové elektronické **panely**…` | zachytí |
| `Tři kroměřížské zastávky dostanou obrazovky, co ukážou, za jak dlouho přijede autobus.` | projde |
| `Konec hádání, jestli ti ujel bus, protože na tři zastávky míří tabule…` | projde |
| krátká faktická věta (pod 8 slov) | nepočítá se |

### Pojistka na citace

| Vstup | Očekávání |
|---|---|
| `Starosta řekl: „Bude to dobré.“` | zachytí |
| `Řekl "ano"` | zachytí |
| `Opatrný to zdůvodnil tím, že dorazí víc lidí.` | projde |

### Extrakce HTML

| Co | Očekávání |
|---|---|
| `grab` na `news-content` s vnořenými divy | vrátí jen vnitřek, ne sousední blok |
| `to_paragraphs` | dva odstavce, bez značek |
| `meta` na `og:image` | vrátí URL |
| `meta` na chybějící klíč | prázdný řetězec |

### Program akcí

Vzorky ve `tests/fixtures/` jsou oříznuté skutečné soubory, ne ručně
napsané:

| Soubor | Co v něm je |
|---|---|
| `akce-vzorek.xml` | šest termínů z exportu 23. 10. 2026, vybraných tak, aby pokryly pasti: vícedenní výstava, akce bez místa (`place=0`), projekce s odkazem na DK, cena 0, poznámka k ceně s odřádkováním, sport |
| `dk-film.html` | ořez stránky filmu z dk-kromeriz.cz na úseky, ze kterých se čte název, stopáž, přístupnost a formát |

| Co | Očekávání |
|---|---|
| parsování vzorku | 8 typů, každý termín má název a začátek, řazení podle začátku |
| `place=0` | prázdné místo, ne pád |
| krátká pole | na jeden řádek, bez `\n` |
| okno víkendu z pátku / soboty / neděle / pondělí | 24.+25. / 24.+25. / 24.+25. / 31.+1. |
| vícedenní výstava | spadne do okna, přes které běží |
| cena 0 | prázdný text, **ne** „zdarma" |
| karta s `titulky` a `titulky \| 2D` | formát jen jednou |
| HTML v názvu akce | utečené |
| metadata typů | titulek, popis, H1 i úvod se mezi typy neopakují |
| rozbité HTML stránky DK | prázdný dict, žádná výjimka |

## `test_facebook.py`

Fronta příspěvků na stránku Kromcl. Odeslání je podvržené, síť se nevolá.

| Situace | Očekávání |
|---|---|
| odkaz článku | `?utm_source=facebook&utm_medium=social&utm_campaign=<slug>&utm_content=autopost` |
| text | body TL;DR „emoji Štítek: věta“ oddělené prázdným řádkem, bez titulku |
| článek bez TL;DR | aspoň titulek |
| zařazení podruhé | nepřidá se |
| odeslaný článek zařazený znovu | neodejde |
| tři ve frontě | za běh odejde jen nejstarší |
| chyba při odeslání | článek zůstane ve frontě a odejde příště |
| ve frontě přes 24 h | zahodí se, neodejde |
| článek smazaný z archivu | vyřadí se z fronty |
| chybí token | sdílení vypnuté |

## Co se netestuje

Volání modelu, stahování z webu a render. Ty se ověřují ručně podle smoke
checklistu v `README.md`.
