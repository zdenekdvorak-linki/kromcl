# KROMCL — pokyny pro session

**Přečti `README.md` jako první**, hlavně sekci Principy a posledních pár
řádků v „Změny & rozhodnutí". Principy jsou invarianty, ne doporučení.

## Pracovní pravidla

- Po každé větší změně (nová feature, změna vzorce, refaktor) **dopiš řádek do
  „Změny & rozhodnutí"** v README — datum, co, krátce proč.
- Zamítnutý nápad patří do **Parking lotu i s důvodem**, ať se na něj příště
  neptá nikdo od nuly.
- Když se změna dostane do konfliktu s některým principem, **řekni to nahlas**
  a zeptej se. Neporušuj je potichu.
- Texty webu (disclaimer, stránka O webu, tón promptů) jsou součást produktu,
  ne výplň. Měň je stejně vědomě jako kód.

## Časté pasti

- **Slug se nepočítá naivně.** Interpunkce se maže, nenahrazuje pomlčkou:
  `1,2 milionu` → `12-milionu`. Test `test_desetinna_carka_se_maze` to hlídá.
- **`<guid>` z feedu je k ničemu**, odkaz z něj vrací 404. Adresa se vždy
  odvozuje z titulku.
- **Perex je na detailní stránce vlastní blok** a v `news-content` už není.
  Když se vynechá, článku chybí úvodní odstavec s hlavním sdělením.
- **Popisek hlavní fotky je v atributu `alt`**, ne jako text pod obrázkem.
- **Pojistka na čísla musí znát číslovky slovy.** Při rozšiřování `_CISLOVKY`
  přidej i test.
- **Slovník ikon v `ilustrace._IKONY` chytá i podobná slova.** „postava" není stavba,
  „dopravy" obsahuje „opravy". Při rozšiřování přidej test na falešnou shodu
  (`test_stavba_se_nechyta_na_podobnych_slovech`).
- **Zakázaný slang se chytá jako předpona** (`boomer` chytí i „boomerka“).
  Výraz, který je začátkem běžného slova nebo jména, potřebuje ve
  `data/slovnik.json` `"presne": true` (simp/simplifikace, Karen/Karenina).
  Pozor i na skloňování se změnou hlásky: „boomeři“ potřebuje tvar `boomeř`.
  Falešná shoda zahodí celý článek, takže ke každému novému výrazu patří
  test (`test_zakazane_se_nechyta_na_podobnych_slovech`).
- **Piktogram musí jít nakreslit i na kartu og:image.** `og.cesta` umí jen
  podmnožinu SVG (M L H V C S Q A Z, circle, ellipse, rect). Nový tvar
  s jiným prvkem nebo příkazem shodí `test_kazdy_piktogram_se_prevede`.
- **`data/articles/*.json` se nepřepisují.** Když se mění prompt, starý článek
  zůstává takový, jaký je; přegenerování je vědomý krok (smazat JSON).

## Spuštění

```bash
python -m kromka nove                 # zdarma, bez modelu
python -m kromka detail <slug>        # zdarma, ověří parser
python -m kromka run --limit 5
python -m unittest discover -s tests
```

Backend se přepíná `KROMKA_BACKEND=api|cli`. `api` potřebuje
`ANTHROPIC_API_KEY` a je jediný, který funguje v GitHub Actions.

Náhled webu: `preview_start` s konfigurací `kromka`, port 4173.

Akci do kalendáře města podává skill `/pridat-akci` (`.claude/skills/`).
Odeslání vytvoří skutečný záznam u města, takže se na zkoušku neodesílá.

## Co sem nepatří

Tenhle projekt nemá nic společného s klientskými weby v `work/SEO/`. Pravidla
pro klientské reporty, značku Econea ani styl „Zelená coura" tady neplatí.
