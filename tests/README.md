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

### Pojistka na skoro totožné věty

Díra, kterou kontrola na osm slov v řadě sama neuhlídá: když se záměny rozsypou
po celé větě, řetěz se nikde nenaváže. Práh 0,55 je změřený, ne odhadnutý —
maskované kopie vycházely 0,68 až 0,71, vlastní věty 0,00 až 0,13.

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

## Co se netestuje

Volání modelu, stahování z webu a render. Ty se ověřují ručně podle smoke
checklistu v `README.md`.
