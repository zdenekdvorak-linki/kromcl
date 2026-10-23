# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primárně lidé mezi 15 a 25 lety žijící v Kroměříži. Čtou na mobilu, jednou
rukou, v krátkých oknech — na zastávce, mezi hodinami, ve frontě. Oficiální web
města nečtou a nikdy číst nebudou; informace o vlastním městě k nim dnes dorazí
náhodou přes sociální sítě, nebo vůbec.

Sekundárně kdokoliv z Kroměříže, komu vadí úřednický jazyk. Není to ale cílová
skupina, podle které se dělají rozhodnutí.

## Product Purpose

Brát veřejný RSS kanál městských aktualit a přepisovat tiskové zprávy do jazyka,
kterým cílová skupina mluví, aniž by se změnila fakta.

Úspěch znamená vracející se místní čtenáře — lidi, kteří si zvyknou chodit.
Neměří se tím, kolikrát se jeden článek sdílel.

## Positioning

Oficiální zprávy beze změny obsahu, ale v jazyce, který cílová skupina čte
dobrovolně. Soused ani agregátor tohle netvrdí: obsah zůstává přesný a
dohledatelný, mění se jen jak je podaný.

Inspirací byl clutch.orlicky.net, který totéž dělá pro Orlicko. KROMCL ale
stojí na vlastním kódu, vlastních pojistkách i vlastním vzhledu.

## Operating Context

Statický web generovaný z RSS města, nasazený na GitHub Pages na doméně
kromcl.cz. Cron každou hodinu zpracuje nové zprávy; archiv se doplňuje ručně.

Čtenář přichází zvenku — z vyhledávače, z odkazu ve skupině, z RSS. Málokdy
píše adresu ručně. Typická návštěva je krátká a začíná na článku, ne na úvodce.

## Capabilities and Constraints

- Zdrojem je jeden veřejný RSS kanál města. Další zdroje jsou připravené
  architekturou, ale zatím se nepoužívají.
- Přepis dělá jazykový model. Strojové pojistky odmítnou výstup, který obsahuje
  číslo mimo zdroj, přímou citaci v uvozovkách nebo kontaktní údaj.
- Každý článek odkazuje na originál. Článek bez funkčního odkazu se nepublikuje.
- AI původ přepisu je přiznaný v hlavičce, patičce i u článku.
- Fotky pocházejí z tiskových zpráv města; souhlas tiskového mluvčího zatím
  nedorazil.
- Statický web bez serveru, bez databáze a bez přihlašování. Žádná personalizace.
- **Bez reklamy, teď ani později.** Layout nemusí držet volná místa.

## Brand Commitments

Název **KROMCL**, podtitul „Kroměříž bez filtru", doména kromcl.cz. Název se
schválně shoduje s adresou.

Tón textů: internetový slang generace Z, herní metafory, TL;DR s emoji. Vtip
míří na situaci a na úřednický jazyk, nikdy na konkrétního člověka.

## Evidence on Hand

- 57 hotových článků v `data/articles/`, dalších 649 čeká v archivu zdroje.
- Vlastní fotografie nemáme žádné; všechny pocházejí z tiskových zpráv města.
- Žádná návštěvnost, žádná zpětná vazba od čtenářů, žádné měření. Web zatím
  nikdo neviděl. Budoucí práce si nesmí vymýšlet čísla o dosahu ani citace
  čtenářů.

## Product Principles

1. **Fakta se nemění, mění se jazyk.** Všechno ostatní je podřízené tomuhle.
2. **Originál má vždycky přednost a vždycky je na něj odkaz.**
3. **Vtip patří situaci, ne lidem.** Web se baví úředničinou, ne obyvateli.
4. **Mobil je výchozí, ne odvozený.** Desktop je ta druhá verze.
5. **Čitelnost archivu před efektem.** Cílem je návrat, ne jedno zhlédnutí.

## Accessibility & Inclusion

Žádný potvrzený specifický požadavek. Web je v češtině, obsah je textový a
krátký; základní přístupnost (kontrast, klávesnice, popisky obrázků) je
samozřejmost, ne nadstandard.
