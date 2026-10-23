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

### Co se nepočítá jako opsané slovo

Pojistka na osm slov v řadě hlásí nález, jen když v něm po odečtení
výjimek zbude aspoň **pět vlastních slov**. Nepočítá se nic, co má jediný
správný tvar: spojky a zájmena, ustálené úřední termíny, **jména ze
zdroje** (slovo, které zdroj aspoň jednou píše s velkým písmenem uvnitř
věty), čísla, měsíce a dny.

Bez té výjimky pojistka hlásila opisování na větách typu „z Břeclavi,
Tábora, Znojma, Chebu" nebo „od 6. prosince 2024 do 2. března 2025", kde
se nic opsat nedá. Měřeno na archivu z 23. 10. 2026: práh 4 dával 11
falešných poplachů z 32 úryvků a záchyt 98 %, práh 5 nula poplachů a
záchyt 95 %, práh 6 už jen záchyt 87 % bez dalšího zlepšení. Zbylých 5 %
jsou krátké věty a výčty jmen; na ty je druhá pojistka, podobnost vět.

### Program akcí

Druhý typ obsahu vedle zpráv, s jiným právním režimem. Město publikuje
akce jako otevřená data pod **CC BY 4.0**, a ta licence doslovné převzetí
dovoluje výměnou za uvedení zdroje. Fakta se proto nepřepisují a na každé
stránce programu je atribuce — u zpráv se na zdroj neodkazuje, protože
k oznámením města žádnou licenci nemáme.

`kromka/akce.py` je záměrně **mimo `sources/`**. `pipeline.nove_polozky`
prochází všechny registrované zdroje a každou položku posílá do přepisu;
akce v registru by se přepisovaly jako zprávy, 133 termínů měsíčně.

Stránky: `/program.html`, okna `/program/dnes.html` a
`/program/vikend.html`, a stránka ke každému typu, který v okně 30 dní
má aspoň jeden termín. Každá má vlastní titulek, popis, H1 a ručně
psaný úvod v `TYPY_AKCI` a `VYBERY`.

Okna v čase jsou důležitější než typy a je to změřené. Ahrefs (cz,
říjen 2026): „akce kroměříž tento víkend" 500 hledání měsíčně, obtížnost
2; „kroměříž akce dnes" 450, obtížnost 1; „kino nadsklepí" 350. Naproti
tomu „divadlo kroměříž", „koncerty kroměříž", „výstavy kroměříž" i
„kulturní akce kroměříž" mají nulu. Typy proto zůstávají jako navigace
se sitemap prioritou 0.5, kino 0.8, okna 0.9.

Víkend je nejbližší sobota a neděle; v sobotu i v neděli je to ten
právě probíhající (`_okno_vikend`). Vícedenní akce (výstavy) spadnou do
okna, pokud přes něj běží. Prázdný typ se nevykreslí, prázdné okno ano —
adresa musí být stabilní a „dnes se nic nekoná" je poctivá odpověď.

Cron volá `akce` každou hodinu, ale stahuje nejvýš jednou za
`AKCE_MAX_STARI_HODIN` (12 h). Výpadek endpointu `all` neshodí, zůstane
poslední uložený program.

**Odkaz na koupi lístku z webu Domu kultury získat nejde.** Tlačítko
Koupit je POST formulář na `websale-dkk.colosseum.eu/hall`; GET se
stejnými parametry vrátí obecnou stránku bez ohledu na projekci. U kina
se proto odkazuje na stránku filmu, kde to tlačítko je.

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
| `kromka/akce.py` | program z otevřených dat: stažení, parsování, uložení do `data/akce.json`; **mimo `sources/`** |
| `kromka/kino_dk.py` | stopáž, přístupnost, formát a původní název ze stránek Domu kultury, mezipaměť v `data/kino-dk.json` |
| `kromka/render.py` | `TYPY_AKCI`, `VYBERY` — metadata vstupních stránek programu; `_program_stranky`, `_karta_akce`, `_okno_vikend` |
| `kromka/cli.py` | příkazy `nove`, `run`, `backfill`, `detail`, `akce`, `build`, `all` |

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
| 2026-10-23 | Pojistka na kontaktní údaje ve výstupu | Model přepsal do textu e-maily úředníků a dostaly se na web |
| 2026-10-23 | Fotky do WebP, rozměry do `<img>`, hero eager | 11,6 → 7,3 MB; bez rozměrů skáče layout, lazy u hero brzdí LCP |
| 2026-10-23 | SEO vrstva: kanonická adresa, OG, JSON-LD, témata, drobečky, související | Articles byly slepé uličky bez prolinkování a bez strukturovaných dat |
| 2026-10-23 | Render maže generované složky před zápisem | Po převodu na WebP zůstaly v `site/` staré JPEGy, na které nic neodkazuje |
| 2026-10-23 | Adresy témat přes `slugify` | `/tema/školství.html` je křehká URL |
| 2026-10-23 | `jen_novejsi` pro `run` a `all` | Hodinový cron s limitem 10 by projel 649 článků archivu sám za tři dny |
| 2026-10-23 | Nasazeno na GitHub Pages, doména `kromcl.cz` | Actions-based Pages si doménu z artefaktu nevezme, musí se nastavit v repu |
| 2026-10-23 | Pojistky **1.1**: jména, data a výčty se nepočítají jako vlastní slova, práh zvednut na pět | Z 34 pádů archivu jich 15 hlásilo opisování na jménech obcí, funkcích s jménem a datech. Měřeno na archivu: falešné poplachy 11/32 → 0/32, záchyt doslovné věty zůstal 95 % |
| 2026-10-23 | `_SLOVO` bere jakékoli písmeno, ne jen české | „Râmnicu Vâlcea" se rozpadlo na „r" a „mnicu", přestalo se poznávat jako jméno a dělalo falešný poplach |
| 2026-10-23 | Pojistka na čísla umí českou tisícovou tečku | Zdroj píše „2.360 g", přepis „2360 g"; pojistka to brala jako vymyšlené číslo |
| 2026-10-23 | Rok o jedna vedle data vydání je povolený | Zpráva z ledna 2025 běžně říká „loni"; 2024 ve zdroji doslova není |
| 2026-10-23 | Důvod pádu se do `state.json` zapisuje bez textu, který ho vyvolal | Stav se commituje do veřejného repa a pojistky hlásí nález i s úryvkem oznámení. Ten úryvek je zdroj, a ten se po použití zahazuje |
| 2026-10-23 | `zdroj_slug` se do článku neukládá | Nikdo ho nečetl a ukazoval na oznámení |
| 2026-10-23 | `beh.log` do `.gitignore` | Log nese titulky zdrojových oznámení a ležel uvnitř datové složky, odkud by se commitnul |
| 2026-10-23 | **Program akcí** z otevřených dat města, `/program.html` + okna dnes a víkend + 8 typů | Měřítko úspěchu jsou vracející se místní čtenáři a program je důvod k návratu, který zprávy nedají. Data jsou pod CC BY 4.0, takže fakta beze změny a s atribucí |
| 2026-10-23 | Stránky oken dnes a víkend navíc proti plánu | Ahrefs: okna mají 950 hledání měsíčně, sedm z osmi typů nulu |
| 2026-10-23 | Scrape Domu kultury jen na stopáž, přístupnost, formát a původní název | Odkaz na lístek tam není jako URL, jen jako POST formulář Colosseum |
| 2026-10-23 | Logo pod 360 px na 21 px | Hlavička na 320 px přetékala o 13 px (logo 199 + hamburger 109 + okraje); chyba z doby před kalendářem |
| 2026-10-23 | Výměna hlídá čerstvost archivu | `backfill` bere od nejstaršího, takže čistý běh z prázdné evidence vyrobil archiv končící 2025-03-21, zatímco živý sahal po dnešek. Z počtu článků to vidět není a na zpravodajském webu je to horší než chybějící článek |
| 2026-10-23 | Identifikátor článku je otisk slugu, ne slug sám | Soubory v repu se jmenovaly `mesto-kromeriz__<slug oznámení>.json`, takže veřejné `data/` prozrazovalo adresu zdroje. Otisk je deterministický, evidence zpracovaných funguje dál |
| 2026-10-23 | `bin/vymena_archivu.py` | Výměna archivu má jednu prověřenou cestu místo ručních kroků; bez `--potvrdit` jen hlásí, co by udělala |
| 2026-10-23 | Práh podobnosti vět 0.55 → **0.65** | Starý práh stál na čtyřech ručních vzorcích a na tvrzení o mezeře mezi 0.13 a 0.68. Archiv ji vyvrátil: deset vlastních vět s týmiž fakty leželo mezi 0.55 a 0.62 |

## Výměna archivu

Přegenerovaný archiv se do živé složky nepřelévá ručně. `bin/vymena_archivu.py`
bez parametru projde kontroly a vypíše, co by se stalo; s `--potvrdit` výměnu
provede a živý archiv před tím zazálohuje mimo repo.

Co kontroluje:

- **neběží žádný `kromka` proces** — jinak by se v jedné složce potkaly
  články ze dvou verzí kódu, což se už jednou stalo
- každý článek má povinná pole a žádné cizí pole ze zdroje (ta odstraní)
- slugy nekolidují, titulek nekončí tečkou
- u článku se shodou 8+ slov dohledá zdroj a **vypíše ten úryvek**, aby
  šlo posoudit, co pojistka propustila kvůli výjimce na jména a data
- důvody pádu ve `state.json` zkrátí na druh pádu bez textu zdroje
- `beh.log` odloží k záloze, mimo repo
- **překlíčuje identifikátory** na otisk a sloučí evidenci zpracovaných
  se živou, aby cron nepovažoval starý archiv za nový a neplatil ho znovu
- **čerstvost**: odmítne výměnu, pokud nový archiv končí dřív než živý

Po výměně se pustí `python -m kromka build`.

## Nasazení

Repozitář `zdenekdvorak-linki/kromcl`, veřejný. Pages se zdrojem GitHub Actions,
vlastní doména `kromcl.cz`. Secret `ANTHROPIC_API_KEY` a proměnná
`KROMKA_SITE_URL` jsou nastavené v repu.

Doména běží na Forpsi a potřebuje čtyři A záznamy na `@`:
`185.199.108.153`, `.109.153`, `.110.153`, `.111.153`, plus `www` jako CNAME na
`zdenekdvorak-linki.github.io`. Dokud nejsou, `github.io` se přesměrovává na
`kromcl.cz` a web není dostupný. Po propsání DNS se v Settings → Pages zapne
Enforce HTTPS (certifikát se vydá až po ověření domény).

## Parking lot

| Nápad | Proč odložen |
|---|---|
| Index titulek → URL z ročníkových archivů | 24 stránkovaných požadavků na rok kvůli 5 % článků; `cHash` v URL brání skládání adres |
| Fallback na sitemapu při 404 | Sitemapa nese jen 1 000 posledních URL a chybějící články v ní nejsou |
| Kontrola jmen v pojistce | Falešné poplachy u skloňování, vypínalo by se |
| Konverze fotek do WebP | Vyžaduje Pillow, tedy závislost navíc; řeší se až kdyby vadila velikost |
| Další zdroje (kultura, sport, policie) | Nejdřív jeden zdroj živě; registr v `sources/__init__.py` je na to připravený |
| Komentáře a reakce | Moderace lokálního webu je práce navíc, kterou zatím nikdo nechce |
