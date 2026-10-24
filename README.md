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
| `kromka/config.py` | značka, cesty, modely, backend, disclaimer, `GA4_ID` — jediné místo na změnu názvu webu |
| `kromka/render.py` | `MERENI`, `_mereni`, `_typ_stranky` — gtag GA4 v `<head>` s parametry stránky, jen na ostré doméně |
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
| `kromka/ilustrace.py` | obrázky v těle článku: `karty` (peníze, plocha, kdy) a `ikony` u odstavců podle slovníku `_IKONY` |
| `kromka/akce.py` | program z otevřených dat: stažení, parsování, uložení do `data/akce.json`; **mimo `sources/`** |
| `kromka/kino_dk.py` | stopáž, přístupnost, formát a původní název ze stránek Domu kultury, mezipaměť v `data/kino-dk.json` |
| `kromka/render.py` | `TYPY_AKCI`, `VYBERY` — metadata vstupních stránek programu; `_program_stranky`, `_karta_akce`, `_okno_vikend` |
| `kromka/cli.py` | příkazy `nove`, `run`, `backfill`, `detail`, `akce`, `build`, `all` |
| `kromka/znacka.py` | geometrie značky (K na dlaždici) — z ní jde SVG favicona i všechny PNG ikony |
| `bin/ikony.py` | vyrobí ikony do `static/`; pouští se ručně po změně značky, výsledek se commituje |
| `static/` | kopíruje se do kořene webu i s podsložkami: ikony, `fonts/`, `sw.js` (service worker), `app.js` (výzva k instalaci) |
| `bin/fonty.py` | stáhne Syne a Space Grotesk do `static/fonts/` (woff2) a `kromka/pisma/` (TTF pro kartu) i s licencí OFL; pouští se ručně jednou |
| `kromka/pisma/` | TTF pro víkendovou kartu a `fonty.css` s pravidly `@font-face`, který si render přidá před ostatní styly |
| `kromka/karta.py` | víkendová karta 1080 × 1920 do instagramového příběhu: výběr akcí, zalamování textu, kreslení v Pillow |
| `data/kromeriz-v-kostce.json` | text průvodce Kroměříž v kostce: úvod, 15 sekcí, zdroj s číslem revize hesla; opravuje se tady, ne v kódu |
| `kromka/render.py` | `KOSTKA_CESTA`, `_kostka`, `_ld_kostka`, `_kostka_stranka` — stránka průvodce, atribuce CC BY-SA, JSON-LD `Article` s `isBasedOn` |

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
| 2026-10-24 | **Fonty u sebe** místo Google Fonts | Google by dostal IP adresu každého čtenáře, web čekal na dvě cizí spojení a appka offline padala na náhradní písmo. Čtyři soubory woff2, dohromady 90 kB, licence OFL jde s nimi |
| 2026-10-24 | **Víkendová karta** na `/program/vikend-pribeh.png` + odkaz na stránce víkendu | Důvod vracet se každý týden a obsah tam, kde publikum je. Pestrý výběr: jednodenní akce, nejvýš 2 kina, bez výstav, nejdřív až 3 na den |
| 2026-10-24 | **Měření GA4** (`G-M0MPCR8ZW7`, služba KROMCL v účtu gyd.name), gtag přímo, bez GTM a **bez lišty se souhlasem** | Měřítko úspěchu jsou vracející se čtenáři a bez měření ho nikdo nevidí. GTM by byl jen kontejner navíc pro jediný tag. Lišta zamítnuta vědomě (Zdeněk), přestože opt-in v ČR platí od 2022 a GA4 posílá Googlu IP adresu, kterou kvůli tomu fonty z Googlu nenačítají. Fonty zůstávají u sebe kvůli rychlosti a offline appce. Skript se načte jen na `kromcl.cz`, náhled na localhostu data neplní; vypíná se prázdným `KROMKA_GA4_ID` |
| 2026-10-24 | **Události GA4**: parametry stránky + šest událostí, popis v sekci Měření | Ukázat, co přivádí čtenáře zpátky. Kliknutí se poznají podle tříd ze šablony místo atributů `data-mereni`, takže mapování je na jednom místě v `app.js`; test hlídá, že třídy v šabloně zůstaly |
| 2026-10-24 | Karta nebere akce, které už začaly | Přestavuje se každou hodinu; v sobotu odpoledne by nabízela dopolední program |
| 2026-10-24 | Okna dnes a víkend podle pražského času (`akce.ted()`) | GitHub Actions běží v UTC; po půlnoci by „dnes" ukazovalo včerejšek, jednu až dvě hodiny denně |
| 2026-10-24 | Odkazy akcí vždy s protokolem | 22 ze 115 odkazů v exportu bylo „www.…" bez https a vedlo na kromcl.cz/program/www.…, tedy na 404 |
| 2026-10-24 | Favicona **K na dlaždici**, web jde nainstalovat jako appka | Z pěti návrhů jediná čistá i v 16 px na skutečném rastru. Výzva k instalaci od druhé zobrazené stránky, po „Teď ne" 30 dní klid; na iPhonu návod přes Sdílet, protože Safari instalační dialog nemá |
| 2026-10-24 | **První spustitelný JavaScript** na webu (`static/app.js`, `static/sw.js`) | Instalace bez JS nejde. Lištu vkládá až skript, takže bez JS nic nechybí ani se nic nerozbije |
| 2026-10-24 | Service worker vždy nejdřív ze sítě | Web se přestavuje každou hodinu; obráceně by appka ukazovala staré zprávy a neplatný program. Z mezipaměti jen při výpadku signálu |
| 2026-10-24 | Ikony se commitují, build je jen kopíruje | Kdyby je kreslil build, potřeboval by Pillow na každém stroji, kde se staví |
| 2026-10-24 | Datum „1. 11." s nezlomitelnou mezerou | „do 30. 11." se ve sloupci programu lámalo na tři řádky |
| 2026-10-23 | Menu na desktopu: program + 5 témat + „další ▾", hamburger až do 900 px | Dvanáct položek se nevešlo ani na 1440 px (menu 716 px, položky 766). Zkrácené menu potřebuje 469 px a láme se pod ~870 px okna; 900 je s rezervou na písmo na Macu. Pět témat podle počtu článků, napevno. Téma bez článků se neodkazuje — „volby" vedly na 404. Program je štítek, ne zelený text: ten měl kontrast 1,6 : 1 |
| 2026-10-23 | **Program akcí** z otevřených dat města, `/program.html` + okna dnes a víkend + 8 typů | Měřítko úspěchu jsou vracející se místní čtenáři a program je důvod k návratu, který zprávy nedají. Data jsou pod CC BY 4.0, takže fakta beze změny a s atribucí |
| 2026-10-23 | Stránky oken dnes a víkend navíc proti plánu | Ahrefs: okna mají 950 hledání měsíčně, sedm z osmi typů nulu |
| 2026-10-23 | Scrape Domu kultury jen na stopáž, přístupnost, formát a původní název | Odkaz na lístek tam není jako URL, jen jako POST formulář Colosseum |
| 2026-10-23 | Logo pod 360 px na 21 px | Hlavička na 320 px přetékala o 13 px (logo 199 + hamburger 109 + okraje); chyba z doby před kalendářem |
| 2026-10-23 | Výměna hlídá čerstvost archivu | `backfill` bere od nejstaršího, takže čistý běh z prázdné evidence vyrobil archiv končící 2025-03-21, zatímco živý sahal po dnešek. Z počtu článků to vidět není a na zpravodajském webu je to horší než chybějící článek |
| 2026-10-23 | Identifikátor článku je otisk slugu, ne slug sám | Soubory v repu se jmenovaly `mesto-kromeriz__<slug oznámení>.json`, takže veřejné `data/` prozrazovalo adresu zdroje. Otisk je deterministický, evidence zpracovaných funguje dál |
| 2026-10-23 | `bin/vymena_archivu.py` | Výměna archivu má jednu prověřenou cestu místo ručních kroků; bez `--potvrdit` jen hlásí, co by udělala |
| 2026-10-23 | **Obrázky v těle článku**: karty s čísly pod prvním odstavcem a ikona u odstavce, obojí z piktogramů webu | Holý text pod TL;DR působil chudě. Skládá se z hotového přepisu regexem a slovníkem, takže platí pro celý archiv a nepřidává fakt. Pravidlo „aspoň dvě karty" dávalo karty 7 článkům z 64; s jednou kartou a daty 48 |
| 2026-10-23 | Práh podobnosti vět 0.55 → **0.65** | Starý práh stál na čtyřech ručních vzorcích a na tvrzení o mezeře mezi 0.13 a 0.68. Archiv ji vyvrátil: deset vlastních vět s týmiž fakty leželo mezi 0.55 a 0.62 |
| 2026-10-24 | **Kroměříž v kostce** z Wikipedie, plný průvodce, odkaz v patičce a na O webu | Obsah, který nestárne a odpovídá na hledání o městě samotném. Heslo je pod CC BY-SA 4.0, takže atribuce na revizi 26310890, označení úpravy a stejná licence pro náš text. Psáno jednou ručně, ne modelem v buildu |
| 2026-10-24 | **Tlačítko Sdílet** u článků, Kroměříže v kostce a víkendové karty | Nainstalovaná appka nemá adresní řádek ani menu, odkaz se z ní nedal poslat. Sdílí se kanonická adresa bez parametrů, UTM se nepřidává (duplicity, ošklivé odkazy); dosah měří událost GA4 `share`. Záloha kopírováním přes skryté pole, protože vestavěné prohlížeče sociálních sítí schránku často nepustí |

## Appka a favicona

Značka je jedna geometrie v `kromka/znacka.py`. Z ní `bin/ikony.py` vyrobí
`favicon.svg`, `favicon.ico` (16, 32, 48 px), `apple-touch-icon.png` a ikony
aplikace 192 a 512 px včetně maskovatelné. Ta má písmeno zmenšené na 75 %,
protože Android ikonu ořízne do kruhu a zaručeně ukáže jen 40 % od středu.

`_manifest()` v `render.py` skládá manifest z `config`, takže změna značky
zůstává na pěti řádcích. Zkratky na dlouhý stisk vedou na program — víkend,
dnes a celý program.

**Service worker** (`static/sw.js`) bere stránky vždy nejdřív ze sítě a
z mezipaměti jen při výpadku. Ukládá jen celé stránky, ne obrázky ani cizí
fonty. Při změně chování zvyš `VERZE`, prohlížeč pak staré úložiště smaže.

**Výzva k instalaci** (`static/app.js`):

- ukáže se nejdřív na druhé zobrazené stránce a nikdy v nainstalované appce
- „Teď ne" ji schová na 30 dní, stav je v `localStorage` pod `kromka-instalace`
- Chrome, Edge a Android: vlastní tlačítko přes `beforeinstallprompt`
- iPhone: Safari instalační dialog nemá, lišta jen poradí cestu přes Sdílet
- Firefox na desktopu instalaci neumí, nic se neukáže

**Tlačítko Sdílet** (`_sdilet` v `render.py`, obsluha v `app.js`). Appka
nemá adresní řádek ani menu prohlížeče, bez tlačítka se z ní odkaz poslat
nedá. Je pod titulkem článku, pod úvodem Kroměříže v kostce a vedle
víkendové karty.

- telefon otevře systémovou sdílecí nabídku (`navigator.share`)
- u víkendové karty posílá rovnou obrázek, pokud to systém dovolí — cesta
  do instagramového příběhu; obrázek se stahuje předem, protože Safari
  povolí sdílení jen hned po klepnutí
- bez sdílecí nabídky zkopíruje odkaz, a když nepustí schránku (vestavěné
  prohlížeče Instagramu a Messengeru), zkopíruje ho přes skryté pole
- bez JS zůstane skryté, v HTML má `hidden`
- sdílí se vždy kanonická adresa z `data-url`, ne adresa v okně, takže se
  s odkazem nešíří parametry; každá stránka má navíc self-canonical
- měří se událost GA4 `share` (`method` nabidka / obrazek / kopie,
  `content_type`, `item_id` = cesta); zavřená nabídka se nepočítá

**Ověřování:** vestavěný prohlížeč Claude aplikace service worker
nezaregistruje („unknown error when fetching the script"), přestože
`/sw.js` vrací 200 — je to omezení prostředí. Ve skutečném Edge se
zaregistruje a aktivuje. Edge bez okna na Windows zase nedovolí okno užší
než asi 500 px, takže mobilní snímek z něj vypadá přetékající; poctivý snímek
je ze stránky vložené do `<iframe width="390">`.

## Fonty

Syne a Space Grotesk jsou na webu, ne na Google Fonts. Stáhl je
`bin/fonty.py` (pouští se ručně jednou) do dvou míst:

- `static/fonts/` — čtyři proměnné woff2 pro web, po latince a latince
  rozšířené o češtinu, dohromady 90 kB; prohlížeč si je přednačte
- `kromka/pisma/` — statické TTF pro víkendovou kartu; Pillow woff2 neumí

K oběma patří `OFL-*.txt`, licence to při šíření vyžaduje. Service worker
má seznam fontů natvrdo a ukládá je při instalaci — test hlídá, že sedí se
soubory ve `static/fonts/`, a další test, že šablona nevolá Google.

## Víkendová karta

`kromka/karta.py` při každém buildu nakreslí obrázek 1080 × 1920 s
nejvýš šesti akcemi nejbližšího víkendu na `/program/vikend-pribeh.png`.
Na stránce víkendu na něj vede odkaz se stažením.

Výběr: jen jednodenní akce v sobotu a neděli, nejvýš dvě projekce kina,
žádné výstavy, nejdřív až tři akce na den a pak doplnit podle času,
stejná akce jen jednou, akce, které už začaly, vynechat. Výsledek se
řadí podle času.

Instagram v příběhu zakrývá horních a spodních asi 250 px, takže
všechno podstatné je mezi 250 a 1670. Hlavička i pata se počítají z
obrysu textu, ne z odhadu — odhad vedl k překryvu podtitulu s nadpisem.
Text se zalamuje česky: jednopísmenná předložka ani řadová číslovka
nezůstane na konci řádku.

Bez Pillow se karta i odkaz vynechají a zbytek webu se postaví.

**Ověřování:** Edge bez okna se „virtuálním časem" (`--virtual-time-budget`)
nečeká na síť a úložiště service workeru, takže test ukládání fontů v
něm zamrzne. Logika `sw.js` se proto ověřovala v Node s napodobeným
prostředím; registraci samotnou v Edge ověřila už první verze.

## Kroměříž v kostce

`/kromeriz-v-kostce.html` je převyprávěné heslo
[Kroměříž](https://cs.wikipedia.org/wiki/Krom%C4%9B%C5%99%C3%AD%C5%BE) z české
Wikipedie: patnáct sekcí od základních čísel po partnerská města, obsah
s kotvami nahoře. Vede na něj patička a stránka O webu.

Heslo je pod **CC BY-SA 4.0**, jiný režim než zprávy i program. Licence chce
uvést zdroj a autory, označit, že jde o úpravu, a pustit upravený text dál
pod stejnou licencí. Atribuce na konci stránky proto odkazuje na **konkrétní
revizi** (`oldid`), ze které text vznikl, ne na živé heslo, a na historii
hesla jako seznam autorů. Licence je u odkazu i v JSON-LD.

Text se nepíše při buildu, je hotový v `data/kromeriz-v-kostce.json`.
Čísla v něm jsou podmnožinou čísel ze zdroje. Tragické pasáže (požáry,
mor, Kroměřížská selicha, rok 1945) jsou bez slangu a politici bez
hodnocení. Při aktualizaci: stáhnout novou revizi, přepsat dotčené sekce,
přepsat `revize` a `datum` v `zdroj`.

## Měření

GA4 `G-M0MPCR8ZW7`, služba KROMCL v účtu gyd.name, uchovávání dat
14 měsíců. Skript vkládá `render.MERENI` a načte se jen na `kromcl.cz`.

**Parametry ke každé stránce** (jdou s `page_view` i s každou událostí):

| Parametr | Hodnoty |
|---|---|
| `typ_stranky` | `uvod`, `clanek`, `tema`, `program`, `okno` (dnes a víkend), jinak název souboru (`o-webu`, `404`, `kromeriz-v-kostce`) |
| `tema` | první štítek článku, u stránky tématu to téma |
| `rezim` | `appka` v nainstalované appce, jinak `web` |

**Události** (`static/app.js`). První tři jsou v GA4 klíčové události
s počítáním jednou za událost. Založené přes Admin API (`keyEvents.create`),
protože rozhraní GA4 dovolí označit jen událost, která už má zpracovaná data:

| Událost | Kdy | Parametr |
|---|---|---|
| `appka_instalace` | prohlížeč ohlásí instalaci, i z vlastního menu | — |
| `pribeh_stazeni` | klik na stažení víkendové karty | — |
| `rss_klik` | klik na odkaz na `/feed.xml` | — |
| `instalace_nabidka` | lišta s instalací | `vysledek`: `zobrazeno`, `prijato`, `odmitnuto`, `ted_ne`, `ios_navod` |
| `navigace` | klik v `.dalsi`, `.drobecky`, `.menu`, na `.stitek` (v tomhle pořadí) | `misto`: `dalsi`, `drobecky`, `menu`, `stitek` |
| `program_filtr` | klik na `.filtr-odkaz` | `typ_akce`: slug typu nebo okna, `vse` |

Všech šest parametrů je v GA4 zaregistrovaných jako vlastní dimenze
s rozsahem Událost. Proklik ven („Víc o akci", „Trailer") měří GA4 samo
jako `click` v rozšířeném měření.

**Ověření bez ostré domény:** na localhostu `gtag` neexistuje. Do stránky
ve vloženém `<iframe>` se dá podstrčit `w.gtag = (...a) => log.push(a)` a
klikat přes `element.click()` s `preventDefault` v zachytávací fázi.

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
| Typografické ozdoby textu: iniciála, zvýrazněná čísla, předěly, vytažená hláška, číslované odstavce | Zamítnuto v mockupu 23. 10. 2026. „Chudé" znamenalo chybějící obraz, ne typografii |
| Text jako karty, chat s botem, čtverečkovaný panel, šikmá páska, slovníček slangu s bublinami | Zamítnuto v mockupu 23. 10. 2026 ze stejného důvodu |
| Časová osa (vydání → měsíc z textu) | Bez nového pole má jen dva body, třetí by byl vymyšlený (princip 2); ukáže se jen u článků s měsícem |
| Scéna se štítky článku jako postavami | Opakuje hero piktogram o kus výš |
