---
name: pridat-akci
description: Použij, když uživatel chce přidat akci do městského kalendáře Kroměříže, tedy vyplnit formulář opendata.mesto-kromeriz.cz/formular přes Claude in Chrome. Triggeruj na „přidej akci do kalendáře města", „pošli akci městu", „vyplň formulář akcí", „zpracuj akce z příspěvků", explicitní `/pridat-akci`. Vstup je volný (vložený text pozvánky, URL stránky akce, plakát) nebo řádky ve stavu `akce` v tabulce příspěvků čtenářů. Skill pole vytěží, formulář vyplní, ukáže souhrn a screenshot a odešle teprve po výslovném „ano". Nepoužívej pro vlastní formulář na kromcl.cz (ten se staví až po odpovědi města, viz README, „Program akcí").
---

# Přidat akci do kalendáře města

Formulář města přijímá akce bez přihlášení a schvaluje je správkyně
otevřených dat. Co projde, se k nám vrátí exportem v `data/akce.json`.
Skill akci jen podává. Schválení je vždycky na městě.

Platformy: Claude in Chrome a `sheets_cli.py` jedou na Windows i na Macu.
Nic nativního tu není.

## Postup

### 1. Vstup

- **Volný vstup:** text, URL nebo plakát (obrázek, PDF). URL přečti přes
  `get_page_text`, plakát přes Read.
- **Příspěvky čtenářů:** tabulka „KROMCL – příspěvky čtenářů", ID je
  v `.env` jako `KROMKA_PRISPEVKY_TABULKA`. Ber jen řádky, které mají ve
  sloupci Stav hodnotu `akce`:

  ```bash
  SID=$(grep '^KROMKA_PRISPEVKY_TABULKA=' .env | cut -d= -f2 | tr -d '\r')
  python ~/.claude/skills/sheets/sheets_cli.py read "$SID" --sheet "Odpovědi formuláře 1" --json
  ```

  Sloupce: Časová značka, Jméno, E-mail, Nadpis, Text, Odkaz, Souhlas,
  Stav, Odkaz na článek, Poznámka. `read` vynechává prázdné buňky na konci
  řádku, páruj proto podle hlavičky. Číslo řádku si poznamenej kvůli
  zápisu v kroku 7.

### 2. Vytěžit pole

Sestav objekt podle mapy níž. **Nic si nevymýšlej.** Povinná pole, která
ve zdroji nejsou, chybějící konec akce a nejasné místo vyřeš jedním
souhrnným dotazem. Text piš věcně a česky. Je to podklad pro správkyni,
ne článek KROMCL, takže tón webu a jeho pojistky tu neplatí.

| Klíč | Pole formuláře | Hodnota |
|---|---|---|
| `label` * | Název | název akce |
| `perex` * | Krátké shrnutí | jedna až dvě věty, co a pro koho |
| `text` * | Informace k události | HTML: `<p>`, `<strong>`, `<em>`, `<ul><li>`, `<a href>` |
| `cal_from` * | Čas začátku | `DD.MM.RRRR HH:MM` |
| `cal_to` * | Čas konce | `DD.MM.RRRR HH:MM`; vícedenní akce = poslední den |
| `cal_note` | Poznámka k termínu | např. „každou sobotu do 30. 11." |
| `type` * | Typ události | id: 8 Divadlo, 10 Hudba a tanec, 15 Jarmarky, trhy a gastro, 11 Kino, 9 Muzea, výstavy, galerie, 12 Přednášky a besedy, 13 Sport, 14 Zábava |
| `for_kids` | Vhodná pro děti | `"1"` ano, `"0"` ne (výchozí) |
| `place_id` / `place_name` | Místo ze seznamu | id, nebo přesný název z číselníku; skript ho najde sám |
| `place_note` | Jiné místo | adresa, když místo v číselníku není |
| `is_price` | Vstup zdarma | `"0"` = zdarma, `"1"` = placené (výchozí) |
| `price` | Základní cena | číslo v Kč, povinné při `is_price "1"` |
| `price_note` | Poznámka ke vstupnému | další druhy vstupného |
| `accessible_from` | Přístupnost | `"0"` neuvedeno, `"15"`, `"18"` |
| `appropriate_from` | Vhodnost pro mládež | `"0"` neuvedeno, `"12"`, `"15"` (nevhodný do) |
| `event_ticket_url` | Nákup lístku online | URL |
| `web` | Web akce | URL |
| `fb` | Facebook | URL události nebo stránky |
| `youtube` | Video | jen 11místný kód z adresy, ne celá URL |
| `owner_name` | Jméno | viz Kontakt |
| `owner_email` * | Kontaktní e-mail | viz Kontakt |
| `owner_phone` | Telefon | viz Kontakt |
| `owner_message` | Poznámka | vzkaz správkyni |

`*` = povinné. Plakát (`image`, JPG, PNG, GIF nebo PDF) skript neplní,
viz krok 4.

**Místo:** číselník je v `<select name="newaction[place_id]">` na stránce.
Položky se slovem „ZRUŠENO" nikdy nevybírej. Když si shodou nejsi jistý
(„Zámek" může být Arcibiskupský zámek i Zámek Holešov), zeptej se.

**Kontakt** (sekce 7):

- Volný vstup: kontakt pořadatele, jak je uvedený ve zdroji. Když tam
  není, zeptej se.
- Příspěvek čtenáře: `owner_name` „Zdeněk Dvořák", `owner_email`
  „zdenek@linki.cz", `owner_message` „Akci poslal čtenář kromcl.cz,
  kontakt na pořadatele rádi předáme." **E-mail ani jméno čtenáře do
  formuláře nikdy nejdou.** Souhlas ve formuláři příspěvků mu slibuje, že
  e-mail uvidí jen redakce.

**Duplicita:** než budeš vyplňovat, ověř, že akce už v datech města není:

```bash
python -X utf8 -c "import json,sys; d=json.load(open('data/akce.json',encoding='utf-8')); q=sys.argv[1].lower(); [print(t['zacatek'], t['nazev'], '|', t['misto']) for t in d['terminy'] if q in t['nazev'].lower()]" "<slovo z názvu>"
```

Snímek drží jen měsíc dopředu a jen schválené akce. Prázdný výsledek
neznamená, že ji nikdo nepodal.

### 3. Vyplnit

1. `tabs_context_mcp`, potom vlastní nový tab (`tabs_create_mcp`) a
   `navigate` na `https://opendata.mesto-kromeriz.cz/formular`.
2. Přečti [vyplnit.js](vyplnit.js) a předej ho `javascript_tool` celý,
   s řádkem `vyplnAkci({...})` na konci. Vrácené `CHYBY` oprav a spusť
   znovu. Skript lze pouštět opakovaně, pole přepíše.
3. Ověř screenshotem po sekcích. Formulář je dlouhý, posouvej o 10 kroků.

Proč skript, a ne `form_input`: popis je editor Trumbowyg a kalendář je
jen pro čtení. Ani jedno se klikáním spolehlivě nevyplní a přepínač
„Jiné místo" teprve odemyká textové pole.

### 4. Plakát (nepovinný)

Formulář chce soubor na disku. Plakát z vloženého souboru nahraj rovnou.
Plakát z webu stáhni do scratchpadu teprve po souhlasu uživatele (název,
zdroj, velikost). Pak `find` „Plakát file input" a `file_upload` s jeho
`ref`. Na tlačítko „Vybrat soubor" neklikej, otevřel by se systémový
dialog.

### 5. Souhrn a souhlas

V chatu ukaž tabulku vyplněných polí, místo a kontakt a přidej screenshot.
Zeptej se: „Odeslat akci městu?" **Bez výslovného „ano" neodesílej.**
Každá akce potřebuje vlastní souhlas, a to i v dávce z tabulky.

### 6. Odeslat a přečíst výsledek

Ještě **před kliknutím** zavolej `read_network_requests` (načti ho přes
ToolSearch). Chrome začne síť sledovat až od prvního volání, jinak
odpověď na POST nezachytíš. Pak klikni na „Přidat událost" (`find`
„Přidat událost button"). Formulář posílá AJAX POST na `/formular` a
dostane JSON `error`, `error_items` a `infomessage`. Skript města
(`AddEventResult`) s ním naloží takhle:

- `error == 0`: na 2 s ukáže `infomessage` v popupu a **přesměruje na
  `/akce/`**. Přesměrování je tedy samo o sobě důkaz úspěchu, i když
  hlášku nestihneš přečíst.
- chyba: popup se seznamem `error_items`, stránka zůstane na formuláři.

Po kliknutí počkej 3 s a zkontroluj adresu tabu. Odpověď přečti
z `read_network_requests` s `urlPattern: "/formular"`.

- **Prošlo:** tab je na `/akce/`. Akce čeká na schválení správkyní.
  Ověřeno 26. 10. 2026 na akci s diakritikou i pomlčkou v názvu.
- **`error_items`:** formulář odmítl konkrétní pole. Oprav je a ukaž znovu
  souhrn.
- **`Incorrect string value ... for column events.label`:** chyba města
  s diakritikou z 24. 10. 2026. Odeslání 26. 10. už prošlo, takže je
  nejspíš opravená a tahle větev je jen pojistka pro případ, že se vrátí.
  Nabídni verzi bez diakritiky: ukaž, jak bude vypadat název a shrnutí, a
  upozorni, že takhle zůstane ve veřejných datech. Po „ano" znovu načti
  stránku, spusť `vyplnAkci({...}, {bezDiakritiky: true})` a odešli.
  Adresy, e-mail a telefon se nemění.
- **Cokoli jiného:** nic neopakuj, ukaž hlášku a skonči.

### 7. Zápis do tabulky (jen u příspěvků)

Buňka Stav obsahuje `akce`, zápis proto potřebuje `--overwrite`. Použij
ho jen na Stav a Poznámku toho jednoho řádku, ničeho jiného se nedotýkej.

| Výsledek | Stav (sloupec H) | Poznámka (sloupec J) |
|---|---|---|
| prošlo | `akce odeslána` | `městu <D. M. RRRR>, čeká na schválení`, u záložní verze s dovětkem „bez diakritiky" |
| neprošlo | beze změny | `akce neodeslána <D. M. RRRR>: <hláška>` |

```bash
python ~/.claude/skills/sheets/sheets_cli.py write "$SID" --range "'Odpovědi formuláře 1'!H<řádek>" --value "akce odeslána" --overwrite
python ~/.claude/skills/sheets/sheets_cli.py write "$SID" --range "'Odpovědi formuláře 1'!J<řádek>" --value "<poznámka>" --overwrite
```

Stavy `akce` a `akce odeslána` cron ignoruje (`prispevky.gs` vrací jen
`schváleno` a `stáhnout`), takže se z akce nestane článek.

### 8. Úklid

Zavři svůj tab (`tabs_close_mcp`).

## Pasti

- **Výchozí termín je zítra 00:00.** Když skript termín nepřepíše, akce
  odejde s nesmyslným časem. Proto kontroluje tvar data.
- **Vstup zdarma „Ano" je `is_price "0"`.** Hodnota říká, jestli je
  cena, ne jestli je zdarma.
- **`javascript_tool` zablokuje odpověď, ve které je adresa s dotazem
  nebo něco jako cookie.** Proto skript vrací jen text bez URL. Když
  potřebuješ pole zkontrolovat, vypisuj názvy a krátké hodnoty, ne celé
  `<option>` ani skripty stránky.
- **Odeslání vytvoří skutečný záznam u města.** Na zkoušku se
  neodesílá. Test 24. 10. 2026 prošel jen proto, že se kvůli chybě nic
  neuložilo.
- **Screenshoty v `browser_batch` občas vyprší** (formulář je dlouhý a
  vykreslování se zasekne). Hodnoty pak ověř přečtením polí v
  `javascript_tool` a screenshot pořiď samostatně.
