# Dopis správkyni otevřených dat k akcím

**Komu:** Bc. Simona Unger, správa akcí, Město Kroměříž
**E-mail:** simona.unger@mesto-kromeriz.cz
*(uvedeno v patičce opendata.mesto-kromeriz.cz/akce 24. 10. 2026)*

**Předmět:** Chyba ve formuláři pro přidání akce (diakritika) a prosba o drobné nastavení

---

Dobrý den, paní Ungerová,

jmenuji se Zdeněk Dvořák a provozuji web kromcl.cz, který přepisuje
aktuality města do jazyka mladších čtenářů. Od října na něm běží i
program akcí, který bereme z Vašich otevřených dat. Přebíráme ho beze
změny a na každé stránce programu uvádíme město jako zdroj a licenci
CC BY 4.0. Za ta data děkuji, je to jedna z nejužitečnějších věcí,
které město zveřejňuje.

Píšu kvůli dvěma věcem.

**1. Formulář pro přidání akce nepřijme český text**

Když ve formuláři na opendata.mesto-kromeriz.cz/akce/formular/ obsahuje
název akce jakékoli písmeno s diakritikou, akce se neuloží a server
vrátí chybu databáze. Narazil jsem na to 24. 10. 2026 kolem 12:50. Akce
s názvem „TEST KROMCL - prosím smazat" skončila touto hláškou:

> Chyba SQL dotazu při vložení akce: SQLSTATE[22007]: Invalid datetime
> format: 1366 Incorrect string value: '\xEDm sma...' for column
> `events`.`label` at row 1

Chyba se objeví pokaždé, když v textu je „í", „ž" nebo třeba pomlčka
„–". Pořadatel, který akci píše česky, ji tedy teď přidat nemůže a
formulář mu ukáže jen technickou hlášku. Při testu se nic neuložilo,
takže v databázi po mně nezůstal žádný záznam ke smazání.

Pro dodavatele systému: z kódu chyby to vypadá, že se text před uložením
převádí z UTF-8 do jednobajtového kódování (\xED je „í" ve windows-1250),
a databáze, která čeká UTF-8, ho pak odmítne. Obvykle jde o volání
`iconv` nebo `utf8_decode` před INSERT, nebo o nastavení znakové sady
připojení k databázi.

**2. Prosba o povolení formuláře na kromcl.cz**

Rád bych na kromcl.cz přidal stránku „Přidej akci" s krátkým formulářem
uzpůsobeným pro mobil. Akce by se z něj posílala přímo do Vaší databáze,
stejnými poli jako Váš formulář. Schvalování by zůstalo celé u Vás a
k nám by se akce vrátila exportem až po schválení. Nic bychom
neukládali a kontaktní údaje pořadatele by šly jen Vám.

Aby to fungovalo poctivě, potřebuji vědět, jestli Váš server akci
přijal, nebo vrátil chybu. Prohlížeč to webu kromcl.cz dovolí přečíst,
jen když odpověď serveru obsahuje jednu hlavičku. Pro dodavatele:

```
Access-Control-Allow-Origin: https://kromcl.cz
```

u odpovědí na POST na adresu https://opendata.mesto-kromeriz.cz/formular.
Formulář posílá multipart/form-data bez vlastních hlaviček, takže
předběžný dotaz (OPTIONS) není potřeba. Hlavička neotevírá nic dalšího:
poslat data na tu adresu může i dnes kdokoli, hlavička jen dovolí
kromcl.cz přečíst odpověď a ukázat pořadateli, jestli akce prošla.

Je pro Vás takové propojení v pořádku? Pokud ne, nevadí. Na stránce
programu pak jen odkážu na Váš formulář.

Děkuji za čas.

S pozdravem

Zdeněk Dvořák
zdenek@linki.cz
https://kromcl.cz

---

## Poznámky k odeslání

- Posílá Zdeněk ze svého e-mailu. Před odesláním si ověř, že je kontakt
  pořád platný.
- Test proběhl 24. 10. 2026 v 12:47–12:50: tři pokusy, ani jeden se
  neuložil. Poslední byl se session a hlavičkami vlastního formuláře
  města, chyba tedy není způsobená tím, že data přišla z cizího webu.
- Formulář na kromcl.cz se staví až po odpovědi. Zadání je odsouhlasené
  v README, sekce „Program akcí".
- Kdyby město hlavičku nepovolilo, ale chybu opravilo: zbývá odeslání
  s přechodem na odpověď města. Ta je ale holý JSON, takže je potřeba
  znovu rozhodnout, jestli to stojí za to, nebo stačí odkaz.
