# KROMCL

Statický web, který bere veřejný RSS kanál města Kroměříž, přepisuje tiskové
zprávy do jazyka, kterým mluví lidé mezi 15 a 25 lety, a vysypává hotové HTML.
Inspirace: [clutch.orlicky.net](https://clutch.orlicky.net/index.php), vlastní
je ale všechno od parseru po vizuál.

## Principy

Invarianty. Když se některý mění, musí to být vědomé rozhodnutí se zápisem do
logu změn, ne vedlejší efekt refaktoru.

1. **Originál má vždycky přednost a vždycky je na něj odkaz.** Článek bez
   funkčního odkazu na zdroj se nepublikuje. Proto `NeresolvovanyClanek`.
2. **Přepis nesmí přidat fakt.** Pojistky jsou strojové, ne jen prosba
   v promptu — `zkontroluj_cisla` a `zkontroluj_citace`. Když neprojdou,
   článek se zahodí a nezkouší se znovu se slabším pravidlem.
3. **Žádná přímá citace.** Co kdo řekl, se parafrázuje. Přepsaná citace
   v uvozovkách vkládá slova do úst jmenovanému člověku a to je jediná věc,
   která projekt může opravdu potopit.
4. **Vtip patří situaci a úřednickému jazyku, nikdy konkrétnímu člověku.**
   Rozlišování citlivosti je od 23. 10. 2026 vypnuté (`ROZLISOVAT_CITLIVOST`)
   — web je celý v nadsázce a město o negativních událostech píše samo, my
   jen měníme jazyk. Klasifikátor i neutrální tón v kódu zůstávají a zapínají
   se jedním řádkem. Tohle pravidlo o lidech platí dál, drží ho prompt.
5. **Hotový přepis se nikdy negeneruje podruhé.** Jeden článek = jeden JSON
   ve `data/articles`, verzovaný v gitu. Token se platí jednou.
6. **Žádná závislost navíc.** Všechno kromě volání modelu je stdlib, aby
   běh v GitHub Actions neinstaloval půl internetu.
7. **AI přepis je přiznaný** v hlavičce, patičce i u každého článku.

## Architektura

```
RSS feed města                  (708 položek, leden 2025 → dnes, jen perex)
   │
   ├─ diff proti data/state.json          nové = co tam ještě není
   │
   ├─ slug z titulku → /aktuality/detail/<slug>
   │     ověření og:title → záložní slug → hledání v přehledu → zahodit
   │
   ├─ detail: perex + news-content, autor, rubrika, og:image
   │
   ├─ klasifikace citlivosti        haiku, jedno slovo
   ├─ přepis                        sonnet, JSON
   ├─ pojistky                      čísla + uvozovky
   │
   ├─ data/articles/<id>.json       trvalý archiv v gitu
   └─ render → site/                HTML + RSS + sitemap + robots
```

Stav mimo soubory projektu žádný není. `data/state.json`:

| Klíč | Co drží |
|---|---|
| `zpracovane` | ID všech položek, které už proběhly (i zahozených) |
| `neresolvovane` | ID, u kterých se nepodařilo najít funkční URL článku |
| `selhani` | ID → počet pádů a poslední důvod; po `MAX_SELHANI` se vzdáme |

## Klíčové algoritmy s odůvodněním

### Odvození adresy článku ze slugu

`<guid>` ve feedu je číselné ID a **odkaz z něj nefunguje** — přesměruje se na
`/aktuality/detail/<cislo>` a vrátí 404. Adresa se proto počítá z titulku.

Pravidlo TYPO3, ověřené proti skutečným URL: **interpunkce uvnitř se maže,
oddělovačem je jen mezera** (a dlouhá pomlčka). Takže `1,2 milionu` →
`12-milionu`, ne `1-2-milionu`, a `53.245 korun` → `53245-korun`.

Zamítnuto: naivní „každý nealfanumerický znak je pomlčka". Trefilo 404 u všech
článků s částkou v titulku, což je u radnice každý desátý. Zůstalo jako
`slugify_zaloha`, které se zkouší jako druhé v pořadí.

Zamítnuto: index z `sitemap.xml?sitemap=news`. Obsahuje jen 1 000 posledních
URL, tedy zlomek archivu, a chybějící články v něm nejsou.

### Záchrana článku s přepsaným titulkem

TYPO3 generuje slug jen jednou při založení. Když redakce potom titulek
přepíše, URL zůstane stará a z feedu se nedopočítá. Reálný případ: feed i
`og:title` říkají „Radnice **z**pracovala novou koncepci školství", ale URL má
„Radnice **vy**pracovala".

Poslední záchrana stáhne přehled `/aktuality/` (jednou za běh), spočítá překryv
slov mezi hledaným slugem a slugy z přehledu, a kandidáty nad 60 % ověří podle
`og:title`. Funguje tedy pro čerstvé články, což je přesně to, co řeší cron.

Úspěšnost na vzorku 40 náhodných položek napříč archivem: **38/40** — 37 přímo,
1 přes přehled. Zbylé dva jsou starší články, které v přehledu už nejsou; ty se
zahazují (princip 1), protože dopočítat adresu naslepo by mohlo trefit cizí
zprávu.

### Vzdávání se po opakovaném pádu

Článek, který spadne na pojistce nebo na rozbitém JSONu, se zkusí ještě jednou
v témže běhu (s popisem chyby přidaným do promptu). Napříč běhy se počítají
pády v `state.json` a po `MAX_SELHANI` se položka označí za vyřízenou.

Bez toho by se vadný článek vracel do fronty při každém spuštění cronu a platilo
by se za něj donekonečna.

### Pojistka na čísla

Množina čísel ve výstupu musí být podmnožinou povolených. Povolené =
čísla ze zdroje + číslovky napsané ve zdroji slovy (`pět` → `5`) + datum
článku. Bez převodu číslovek by pojistka shodila skoro každý přepis, protože
„přibude pět tabulí" → „5 tabulí" je legitimní a žádoucí změna.

Zamítnuto: kontrola jmen. Produkovala falešné poplachy u skloňování a
u zkrácených tvarů („Hebnar" místo „Jan Hebnar"), takže by se stejně
vypínala. Jména hlídá prompt a korektura.

### Ověření kandidáta podle og:title

TYPO3 přidává u kolizí příponu `-1`, `-2`. Zkoušet je naslepo by mohlo trefit
úplně jiný článek se stejně znějícím titulkem, takže se u každého kandidáta
porovnává `og:title` se slugifikovaným titulkem z feedu.

## Mapa kódu

Čísla řádků jsou orientační.

| Soubor | Co v něm je |
|---|---|
| `kromka/config.py` | značka, cesty, modely, backend, disclaimer — jediné místo na změnu názvu webu |
| `kromka/net.py` | stahování přes `urllib`, 4xx se neopakuje |
| `kromka/htmlutil.py:21` | `slugify` — pravidlo TYPO3 |
| `kromka/htmlutil.py:41` | `_DivGrabber` — vyříznutí `<div>` s vnořenými divy |
| `kromka/htmlutil.py:101` | `to_paragraphs` — HTML fragment → odstavce |
| `kromka/sources/mesto_kromeriz.py:28` | `fetch_items` — parsování feedu |
| `kromka/sources/mesto_kromeriz.py:51` | `fetch_detail` — kandidáti URL, ověření, extrakce |
| `kromka/sources/mesto_kromeriz.py:112` | `_najdi_v_prehledu` — záchrana přepsaného titulku |
| `kromka/rewrite.py:18` | prompty: klasifikace a přepis včetně pravidel |
| `kromka/rewrite.py:90` | `_zeptej_se` — přepínač backendu api / cli / stub |
| `kromka/rewrite.py:148` | `klasifikuj` — citlivost |
| `kromka/rewrite.py:158` | `prepis` — volání s jedním opravným pokusem |
| `kromka/rewrite.py:256` | `zkontroluj_cisla`, `zkontroluj_citace` |
| `kromka/pipeline.py:27` | `zpracuj` — jedna položka od detailu po JSON |
| `kromka/pipeline.py:101` | `_zapis_selhani` — počítadlo pádů a vzdání se |
| `kromka/render.py:204` | `vykresli` — celý statický web |
| `kromka/render.py:17` | `CSS` — vizuál, tmavý režim, mobil |
| `kromka/cli.py` | příkazy `nove`, `run`, `backfill`, `detail`, `build`, `all` |

## Vývojové poznámky

Klíč patří do `.env` v kořeni projektu (vzor je v `.env.example`, soubor je
v `.gitignore`). Skutečné prostředí má přednost, takže se dá kdykoli přebít
proměnnou. Pro GitHub Actions se tentýž klíč zakládá jako repo secret
`ANTHROPIC_API_KEY`.

```bash
pip install -r requirements.txt
cp .env.example .env                  # a doplnit klíč

python -m kromka nove                 # co čeká, bez volání modelu
python -m kromka detail <slug>        # stažený článek jako JSON, zdarma
python -m kromka run --limit 5        # zpracuje 5 nejnovějších
python -m kromka backfill --limit 25  # archiv od nejstarších
python -m kromka build                # jen render z uložených JSONů
python -m unittest discover -s tests
```

Zkušební běh bez modelu a bez zásahu do ostrého archivu:

```bash
KROMKA_BACKEND=stub KROMKA_DATA=/tmp/k/data KROMKA_SITE=/tmp/k/site \
  python -m kromka all --limit 4
```

Náhled: `python -m http.server 4173 --directory site`, nebo `preview_start`
s konfigurací `kromka` z `.claude/launch.json`.

Smoke checklist po refaktoru:

0. `KROMKA_BACKEND=stub` běh podle receptu výš — projede celou cestu zdarma.
1. `python -m unittest discover -s tests` — 25 testů zeleně.
2. `python -m kromka detail v-kromerizi-pribude-pet-novych-informacnich-odjezdovych-tabuli`
   — musí vrátit 6 odstavců, autora a `image_url`.
3. `python -m kromka build` — projde a `site/index.html` není prázdný.
4. Článek označený `neutralni` nemá v `site/` emoji ani slang.

## Změny & rozhodnutí

| Datum | Co | Proč |
|---|---|---|
| 2026-10-23 | Založen projekt, zdroj mesto-kromeriz, render, pojistky, 3 ukázkové články | Zadání: vlastní obdoba clutch.orlicky.net pro Kroměříž |
| 2026-10-23 | `slugify` maže interpunkci místo nahrazení pomlčkou | Naivní varianta trefila 404 u všech titulků s částkou |
| 2026-10-23 | Pojistka na čísla umí číslovky slovy | Jinak padá legitimní přepis „pět" → „5" |
| 2026-10-23 | Kandidáti URL se ověřují podle `og:title` | Přípona `-1` může patřit cizímu článku |
| 2026-10-23 | Backend `cli` vedle `api` | Na stroji není API klíč, Claude Code jede na předplatném |
| 2026-10-23 | Článek bez funkční URL se zahazuje | Bez odkazu na originál by padl princip atribuce |
| 2026-10-23 | Název KROMCL potvrzen | Krátké, české, Kroměříž je v něm slyšet |
| 2026-10-23 | Backend `stub` + `KROMKA_DATA`/`KROMKA_SITE` | Celá cesta se dá ověřit bez API klíče a bez zásahu do archivu |
| 2026-10-23 | Záchrana přes přehled `/aktuality/` | Reálný případ „zpracovala" × „vypracovala"; vrátilo 1 ze 3 ztracených |
| 2026-10-23 | Jeden opravný pokus + `MAX_SELHANI` | Vadný článek se jinak vrací do fronty při každém cronu a platí se za něj pořád |
| 2026-10-23 | Načítání `.env` v `config.py` | Klíč má mít jedno místo; `export` se na dvou strojích zapomíná |
| 2026-10-23 | Podpora `ANTHROPIC_WORKSPACE_ID` | Klíč založený na úrovni organizace API odmítá bez té hlavičky |
| 2026-10-23 | Text se bere z prvního `text` bloku, ne z `content[0]` | Model vrací jako první blok přemýšlení, který `.text` nemá |
| 2026-10-23 | `max_tokens` 8000 pro přepis, 1024 pro klasifikaci | Přemýšlení ukrajuje z rozpočtu; na 2000 a 64 se odpovědi usekávaly |
| 2026-10-23 | Useknutá odpověď (`stop_reason`) hlásí vlastní chybu | Jinak to vypadá jako rozbitý JSON a hledá se to na špatném místě |
| 2026-10-23 | Ostrý běh: 6 článků modelem, klasifikátor označil Oskol jako citlivý | První ověření kvality proti živému modelu |
| 2026-10-23 | Prompt: pravidla 7–9 (žádná zmínka o zdroji, číslo není vtip vedle čísla, odstavec do 80 slov) | Model prolamoval čtvrtou stěnu, mátl dvěma čísly v jedné větě a na konci převyprávěl historické odbočky ze zdroje |
| 2026-10-23 | Značka KROMKA → **KROMCL**, doména `kromcl.cz` | kromka.cz je obsazená od 6/2025; značka se musí shodovat s adresou, kterou lidé píšou |
| 2026-10-23 | `ROZLISOVAT_CITLIVOST=False`, klasifikace se nevolá | Rozhodnutí Zdeňka: web je celý v nadsázce, město o negativních událostech píše samo. Klasifikátor byl navíc přecitlivělý (odchyt holubů, EIA cihelny). Ušetří to i jedno volání API na článek |
| 2026-10-23 | Složka přejmenována `Weby/Kromka` → `Weby/Kromcl` | Sjednocení se značkou a doménou |
| 2026-10-23 | Backfill: 54 článků v archivu, 32/32 bez jediné chyby | První velký běh; žádný článek nespadl na pojistkách ani nezůstal bez odkazu |

## Parking lot

| Nápad | Proč odložen |
|---|---|
| Index titulek → URL z ročníkových archivů | 24 stránkovaných požadavků na rok kvůli 5 % článků; `cHash` v URL brání skládání adres |
| Fallback na sitemapu při 404 | Sitemapa nese jen 1 000 posledních URL a chybějící články v ní nejsou |
| Kontrola jmen v pojistce | Falešné poplachy u skloňování, vypínalo by se |
| Konverze fotek do WebP | Vyžaduje Pillow, tedy závislost navíc; řeší se až kdyby vadila velikost |
| Další zdroje (kultura, sport, policie) | Nejdřív jeden zdroj živě; registr v `sources/__init__.py` je na to připravený |
| Komentáře a reakce | Moderace lokálního webu je práce navíc, kterou zatím nikdo nechce |
