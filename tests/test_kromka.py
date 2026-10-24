# -*- coding: utf-8 -*-
"""Testy částí, které nevolají síť ani model.

Spuštění: python -m unittest discover -s tests
"""

import sys
import unittest
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kromka import (akce, config, htmlutil, ilustrace, kino_dk, piktogramy,  # noqa: E402
                    karta, znacka,
                    pipeline, render, rewrite, styl)

FIXTURES = Path(__file__).resolve().parent / "fixtures"

try:
    import PIL  # noqa: F401
    _MA_PIL = True
except ImportError:
    _MA_PIL = False
class Slugify(unittest.TestCase):
    """Pravidla ověřená proti skutečným URL na webu města."""

    def test_zakladni(self):
        self.assertEqual(
            htmlutil.slugify("V Kroměříži přibude pět nových informačních odjezdových tabulí"),
            "v-kromerizi-pribude-pet-novych-informacnich-odjezdovych-tabuli")

    def test_desetinna_carka_se_maze(self):
        # Past, kvůli které první verze trefila 404: 1,2 → 12, ne 1-2.
        self.assertEqual(
            htmlutil.slugify("Město díky fotovoltaickým elektrárnám ročně uspoří zhruba 1,2 milionu korun"),
            "mesto-diky-fotovoltaickym-elektrarnam-rocne-uspori-zhruba-12-milionu-korun")

    def test_tecka_v_cisle_se_maze(self):
        # Město píše tisíce s tečkou: "53.245". Skutečná URL má 53245.
        self.assertEqual(
            htmlutil.slugify("Vánoční sbírka vynesla žákům speciální školy a dětskému domovu 53.245 korun"),
            "vanocni-sbirka-vynesla-zakum-specialni-skoly-a-detskemu-domovu-53245-korun")

    def test_mezera_zustava_oddelovacem(self):
        self.assertEqual(htmlutil.slugify("Rada města"), "rada-mesta")

    def test_otaznik_a_dvojtecka(self):
        self.assertEqual(htmlutil.slugify("VIDEO: Kroměříž má nový územní plán"),
                         "video-kromeriz-ma-novy-uzemni-plan")

    def test_pomlcka_je_oddelovac(self):
        self.assertEqual(htmlutil.slugify("Koncepce na roky 2027–2032"),
                         "koncepce-na-roky-2027-2032")

    def test_zaloha_dela_pomlcky(self):
        self.assertEqual(htmlutil.slugify_zaloha("Uspoří 1,2 milionu"), "uspori-1-2-milionu")


class PojistkaCisla(unittest.TestCase):
    def test_cislo_ze_zdroje_projde(self):
        self.assertEqual(rewrite.zkontroluj_cisla("Ročně najedou 340 tisíc km", "Najedou 340 tisíc km"), [])

    def test_vymyslene_cislo_neprojde(self):
        self.assertEqual(rewrite.zkontroluj_cisla("Přibudou tabule", "Přibude 7 tabulí"), ["7"])

    def test_cislovka_slovy_se_smi_prepsat_na_cislici(self):
        # Zdroj píše "pět", přepis "5 tabulí" — legitimní, nesmí spadnout.
        self.assertEqual(rewrite.zkontroluj_cisla("Přibude pět tabulí na třech zastávkách",
                                                  "5 tabulí na 3 zastávkách"), [])

    def test_milion_slovy(self):
        self.assertEqual(rewrite.zkontroluj_cisla("přepraví zhruba jeden milion cestujících",
                                                  "sveze 1000000 lidí"), [])

    def test_datum_clanku_je_povolene(self):
        self.assertEqual(rewrite.zkontroluj_cisla("Rada rozhodla", "Rada rozhodla 23. října",
                                                  datum="2026-10-23T08:15:00+02:00"), [])

    def test_mezera_v_cisle_nevadi(self):
        self.assertEqual(rewrite.zkontroluj_cisla("vynesla 53 245 korun", "vynesla 53245 korun"), [])

    def test_ceska_tisicova_tecka(self):
        # Zdroj píše váhu jako "2.360 g", přepis jako "2360 g". Je to
        # totéž číslo, tečka odděluje tisíce.
        self.assertEqual(rewrite.zkontroluj_cisla("vážila 2.360 g", "vážila 2360 g"), [])

    def test_desetinna_tecka_zustava_desetinna(self):
        # Dvě číslice za tečkou je desetinná část, ne oddělovač tisíců.
        self.assertEqual(rewrite.zkontroluj_cisla("v 13.46 hodin", "ve 1346 hodin"), ["1346"])

    def test_loni_se_smi_dopocitat(self):
        # Zpráva z ledna 2025 běžně mluví o loňsku. Rok o jedna vedle
        # data vydání je odvození, ne vymyšlené číslo.
        self.assertEqual(rewrite.zkontroluj_cisla("Loni se narodilo 398 dětí",
                                                  "V roce 2024 se narodilo 398 dětí",
                                                  datum="2025-01-02T10:00:00+01:00"), [])

    def test_vzdalenejsi_rok_neprojde(self):
        self.assertEqual(rewrite.zkontroluj_cisla("Loni se narodilo 398 dětí",
                                                  "V roce 2019 se narodilo 398 dětí",
                                                  datum="2025-01-02T10:00:00+01:00"), ["2019"])


class PojistkaCitace(unittest.TestCase):
    def test_ceske_uvozovky_zachytí(self):
        self.assertTrue(rewrite.zkontroluj_citace("Starosta řekl: „Bude to dobré.“"))

    def test_rovne_uvozovky_zachyti(self):
        self.assertTrue(rewrite.zkontroluj_citace('Řekl "ano"'))

    def test_parafraze_projde(self):
        self.assertFalse(rewrite.zkontroluj_citace("Opatrný to zdůvodnil tím, že dorazí víc lidí."))


class PojistkaKontakty(unittest.TestCase):
    def test_email_zachyti(self):
        self.assertEqual(rewrite.zkontroluj_kontakty("Napiš na jan.novak@mestokm.cz"),
                         ["jan.novak@mestokm.cz"])

    def test_telefon_zachyti(self):
        self.assertEqual(rewrite.zkontroluj_kontakty("Volej 573 321 157"), ["573 321 157"])

    def test_telefon_s_predvolbou(self):
        self.assertTrue(rewrite.zkontroluj_kontakty("+420 573 321 157"))

    def test_bezny_text_projde(self):
        self.assertEqual(rewrite.zkontroluj_kontakty(
            "Ročně najedou 340 tisíc kilometrů a sveze milion lidí."), [])

    def test_datum_a_castka_nejsou_telefon(self):
        self.assertEqual(rewrite.zkontroluj_kontakty("Ušetří 1,2 milionu korun do 23. prosince"), [])


class PojistkaOpisovani(unittest.TestCase):
    ZDROJ = ("Kroměřížská radnice šetří díky fotovoltaickým elektrárnám "
             "instalovaným na budovách města a jeho příspěvkových organizací "
             "ročně částku zhruba 1,2 milionu korun.")

    def test_opsana_veta_se_zachyti(self):
        opsane = ("Kroměřížská radnice šetří díky fotovoltaickým elektrárnám "
                  "instalovaným na budovách zhruba 1,2 milionu.")
        self.assertTrue(rewrite.zkontroluj_opisovani(self.ZDROJ, opsane))

    def test_vlastni_slova_projdou(self):
        self.assertEqual(rewrite.zkontroluj_opisovani(
            self.ZDROJ, "Solárky ušetří městu 1,2 milionu ročně."), [])

    def test_nazev_instituce_projde(self):
        zdroj = ("Tabule instalujeme ve spolupráci s Integrovanou dopravou "
                 "Zlínského kraje na třech zastávkách v Kroměříži.")
        vystup = ("Dělá to město spolu s Integrovanou dopravou Zlínského kraje "
                  "a tabule budou na třech zastávkách.")
        self.assertEqual(rewrite.zkontroluj_opisovani(zdroj, vystup), [])

    def test_vycet_obci_projde(self):
        # Výčet jmen měst má jediný správný tvar. Shoda na něm neznamená
        # opisování o nic víc než shoda na datu.
        zdroj = ("Na závod dorazili jezdci z Břeclavi, Tábora, Znojma, Chebu, "
                 "Pelhřimova, Písku a Mělníku a bylo jich přes dvě stě.")
        vystup = ("Sjeli se jezdci z Břeclavi, Tábora, Znojma, Chebu, "
                  "Pelhřimova, Písku a Mělníku, dohromady přes dvě stě lidí.")
        self.assertEqual(rewrite.zkontroluj_opisovani(zdroj, vystup), [])

    def test_rozsah_datumu_projde(self):
        zdroj = ("Přihlášky se podávají od 6. prosince 2024 do 2. března 2025 "
                 "na podatelně úřadu.")
        vystup = ("Přihlásit se dá od 6. prosince 2024 do 2. března 2025, "
                  "papír hodíš na podatelnu.")
        self.assertEqual(rewrite.zkontroluj_opisovani(zdroj, vystup), [])

    def test_funkce_se_jmenem_projde(self):
        zdroj = ("Novinku představil místostarosta Pavel Motyčka, který má "
                 "sociální oblast na starost už druhé volební období.")
        vystup = ("Přišel s tím místostarosta Pavel Motyčka, který má sociální "
                  "oblast na starost, a popsal to takhle.")
        self.assertEqual(rewrite.zkontroluj_opisovani(zdroj, vystup), [])

    def test_cizi_jmeno_s_diakritikou_projde(self):
        # "Râmnicu Vâlcea" se starým regexem rozpadlo na "r" a "mnicu",
        # přestalo se poznávat jako jméno a dělalo falešný poplach.
        zdroj = ("Rumunská ambasáda a partnerské město Râmnicu Vâlcea "
                 "podepsaly memorandum o spolupráci na radnici.")
        vystup = ("Rumunská ambasáda a partnerské město Râmnicu Vâlcea "
                  "si plácly na memorandu.")
        self.assertEqual(rewrite.zkontroluj_opisovani(zdroj, vystup), [])

    def test_bezna_veta_se_porad_zachyti(self):
        # Pojistka dostala hodně výjimek. Tohle hlídá, že pořád funguje:
        # osm běžných slov v řadě bez jmen a dat musí spadnout.
        zdroj = ("Radnice chce v příštím roce opravit chodníky v celé "
                 "čtvrti a přidat k nim nové lavičky.")
        vystup = ("Radnice chce v příštím roce opravit chodníky v celé "
                  "čtvrti, to je plán.")
        self.assertTrue(rewrite.zkontroluj_opisovani(zdroj, vystup))


class PojistkaPodobneVety(unittest.TestCase):
    """Díra, kterou kontrola na osm slov v řadě sama neuhlídá."""

    ZDROJ = ("Na třech zastávkách autobusové dopravy v Kroměříži budou "
             "instalovány nové elektronické tabule, na kterých cestující "
             "najdou aktuální informace o odjezdech autobusů.")

    def test_maskovana_kopie_se_zachyti(self):
        # Záměny rozsypané po celé větě: osm slov v řadě se nikde nenaváže.
        mazane = ("Na třech zastávkách autobusové přepravy v Kroměříži budou "
                  "umístěny nové digitální tabule, na nichž cestující najdou "
                  "čerstvé informace o odjezdech spojů.")
        self.assertEqual(rewrite.zkontroluj_opisovani(self.ZDROJ, mazane), [],
                         "tenhle případ má stará pojistka propustit")
        self.assertTrue(rewrite.zkontroluj_podobne_vety(self.ZDROJ, mazane))

    def test_stejna_stavba_jina_slova_se_zachyti(self):
        kopie = ("Na třech zastávkách městské dopravy v Kroměříži vzniknou "
                 "nové elektronické panely, na kterých lidé uvidí aktuální "
                 "údaje o odjezdech autobusů.")
        self.assertTrue(rewrite.zkontroluj_podobne_vety(self.ZDROJ, kopie))

    def test_vlastni_veta_projde(self):
        vlastni = ("Tři kroměřížské zastávky dostanou obrazovky, co ukážou, "
                   "za jak dlouho přijede autobus.")
        self.assertEqual(rewrite.zkontroluj_podobne_vety(self.ZDROJ, vlastni), [])

    def test_nadsazka_projde(self):
        vlastni = ("Konec hádání, jestli ti ujel bus, protože na tři zastávky "
                   "míří tabule s živými odjezdy.")
        self.assertEqual(rewrite.zkontroluj_podobne_vety(self.ZDROJ, vlastni), [])

    def test_kratka_veta_se_nepocita(self):
        zdroj = "Samotná instalace je plánována v následujících týdnech."
        self.assertEqual(rewrite.zkontroluj_podobne_vety(
            zdroj, "Instalace je plánována v následujících týdnech."), [])


class KlicClanku(unittest.TestCase):
    """Identifikátor nesmí prozradit adresu oznámení."""

    SLUG = "trikralovi-kolednici-zavitali-na-kromerizskou-radnici"

    def test_neobsahuje_slug(self):
        self.assertNotIn(self.SLUG, htmlutil.klic("mesto-kromeriz", self.SLUG))

    def test_je_stabilni(self):
        # Na stabilitě stojí rozpoznávání už zpracovaných článků. Kdyby
        # se klíč měnil, cron by platil celý archiv znovu.
        self.assertEqual(htmlutil.klic("mesto-kromeriz", self.SLUG),
                         htmlutil.klic("mesto-kromeriz", self.SLUG))

    def test_ruzne_slugy_ruzne_klice(self):
        self.assertNotEqual(htmlutil.klic("mesto-kromeriz", "aaa"),
                            htmlutil.klic("mesto-kromeriz", "bbb"))

    def test_zdroj_zustava_citelny(self):
        self.assertTrue(htmlutil.klic("mesto-kromeriz", self.SLUG)
                        .startswith("mesto-kromeriz:"))


class Znacka(unittest.TestCase):
    """Favicona a ikony appky jdou z jedné geometrie v kromka/znacka.py."""

    def test_svg_ma_dlazdici_a_tri_tahy(self):
        svg = znacka.svg()
        self.assertIn(znacka.ZELENA, svg)
        self.assertEqual(svg.count("<path"), 3)

    def test_pismeno_se_vejde_na_dlazdici(self):
        for tvar in znacka.mnohouhelniky():
            for x, y in tvar:
                self.assertTrue(0 <= x <= znacka.MRIZKA and 0 <= y <= znacka.MRIZKA)

    def test_maskovatelna_ikona_je_v_bezpecnem_kruhu(self):
        # Android ořízne ikonu do kruhu a zaručeně ukáže jen 40 % od středu.
        stred = znacka.MRIZKA / 2
        polomer = znacka.MRIZKA * znacka.BEZPECNY_POLOMER
        for tvar in znacka.mnohouhelniky(znacka.MERITKO_MASKY):
            for x, y in tvar:
                self.assertLessEqual(((x - stred) ** 2 + (y - stred) ** 2) ** .5,
                                     polomer)


class Appka(unittest.TestCase):
    """Instalace jako appka: manifest, šablona a statické soubory."""

    def test_manifest_je_platny(self):
        import json
        m = json.loads(render._manifest())
        self.assertEqual(m["short_name"], config.BRAND)
        self.assertEqual(m["display"], "standalone")
        ucely = {i.get("purpose") for i in m["icons"]}
        self.assertIn("maskable", ucely)
        self.assertIn("any", ucely)

    def test_ikony_z_manifestu_existuji(self):
        import json
        for ikona in json.loads(render._manifest())["icons"]:
            self.assertTrue((config.STATIC / ikona["src"].lstrip("/")).exists(),
                            ikona["src"])

    def test_zkratky_vedou_na_program(self):
        import json
        cesty = [z["url"] for z in json.loads(render._manifest())["shortcuts"]]
        self.assertIn(render.PROGRAM_CESTA, cesty)
        self.assertIn("/program/vikend.html", cesty)

    def test_sablona_odkazuje_manifest_a_skript(self):
        for kus in ('rel="manifest"', 'href="/favicon.svg"',
                    'rel="apple-touch-icon"', 'src="/app.js" defer'):
            self.assertIn(kus, render.ZAKLAD)

    def test_staticke_soubory_jsou_v_repu(self):
        for nazev in ("favicon.svg", "favicon.ico", "apple-touch-icon.png",
                      "icon-192.png", "icon-512.png", "icon-maskable-512.png",
                      "sw.js", "app.js"):
            self.assertTrue((config.STATIC / nazev).exists(), nazev)

    def test_service_worker_stranky_nejdriv_ze_site(self):
        # Web se přestavuje každou hodinu. Mezipaměť napřed by v appce
        # ukazovala staré zprávy a program, který už neplatí. Fonty mají
        # pořadí opačné záměrně, proto se kontroluje jen větev stránek.
        sw = (config.STATIC / "sw.js").read_text(encoding="utf-8")
        stranky = sw[sw.index("pozadavek.mode !== 'navigate'"):]
        self.assertLess(stranky.index("await fetch("), stranky.index("caches.match("))

    def test_service_worker_zna_vsechny_fonty(self):
        # Seznam v sw.js je druhé místo, kde fonty žijí. Po změně ve
        # static/fonts by offline appka jinak tiše přišla o písmo.
        import re
        sw = (config.STATIC / "sw.js").read_text(encoding="utf-8")
        v_sw = set(re.findall(r"'/fonts/([^']+)'", sw))
        na_disku = {f.name for f in (config.STATIC / "fonts").glob("*.woff2")}
        self.assertEqual(v_sw, na_disku)

    def test_sablona_nevola_google(self):
        # Fonty jsou u sebe kvůli soukromí čtenářů; návrat odkazu na
        # Google Fonts by to tiše zrušil.
        self.assertNotIn("fonts.googleapis.com", render.ZAKLAD)
        self.assertNotIn("fonts.gstatic.com", render.ZAKLAD)
        self.assertNotIn("fonts.googleapis.com", render.CSS)
        self.assertIn("@font-face", render.CSS)

    def test_mereni_jen_na_ostre_domene(self):
        # Náhled na localhostu by jinak plnil GA4 vlastními návštěvami.
        kod = render._mereni()
        self.assertIn("gtag/js?id=" + config.GA4_ID, kod)
        self.assertIn("location.hostname === 'kromcl.cz'", kod)
        self.assertNotIn("__", kod)
        self.assertIn("{mereni}", render.ZAKLAD)

    def test_prazdne_ga4_id_mereni_vypne(self):
        from unittest import mock
        with mock.patch.object(config, "GA4_ID", ""):
            self.assertEqual(render._mereni(), "")

    def test_typ_stranky_podle_adresy(self):
        for cesta, typ in [("/", "uvod"), ("/strana-2.html", "uvod"),
                           ("/clanek/x.html", "clanek"), ("/tema/doprava.html", "tema"),
                           ("/program/dnes.html", "okno"), ("/program/vikend.html", "okno"),
                           (render.PROGRAM_CESTA, "program"), ("/program/kino.html", "program"),
                           ("/o-webu.html", "o-webu")]:
            self.assertEqual(render._typ_stranky(cesta), typ, cesta)

    def test_mereni_nese_tema_stranky(self):
        kod = render._mereni("/clanek/x.html", "školství")
        self.assertIn('"typ_stranky": "clanek"', kod)
        self.assertIn('"tema": "\\u0161kolstv\\u00ed"', kod)

    def test_udalosti_najdou_tridy_ze_sablony(self):
        # app.js pozná kliknutí podle tříd z render.py. Přejmenování třídy
        # by měření tiše vypnulo, proto se hlídají obě strany.
        import inspect
        app = (config.STATIC / "app.js").read_text(encoding="utf-8")
        sablona = inspect.getsource(render)
        for trida in ("dalsi", "drobecky", "menu", "stitek", "filtr-odkaz", "pribeh-odkaz"):
            self.assertRegex(app, r"'\.?" + trida + "'", trida)
            self.assertIn('class="' + trida, sablona, trida)
        for nazev in ("appka_instalace", "pribeh_stazeni", "rss_klik",
                      "instalace_nabidka", "navigace", "program_filtr"):
            self.assertIn("'" + nazev + "'", app, nazev)


class VikendovaKarta(unittest.TestCase):
    """Výběr akcí na kartu do příběhu („pestrý výběr", 24. 10. 2026)."""

    DNY = {"2026-10-24", "2026-10-25"}

    @staticmethod
    def akce(den, cas, typ="Sport", akce_id=None, vicedenni=False, nazev=None):
        return {"zacatek": "2026-10-{0}T{1}:00".format(den, cas), "typ": typ,
                "akce_id": akce_id or den + cas + typ, "vicedenni": vicedenni,
                "nazev": nazev or "{0} {1} {2}".format(typ, den, cas),
                "misto": "Zimní stadion"}

    def test_nejvys_sest(self):
        terminy = [self.akce("24", "1{0}:00".format(i)) for i in range(5)]
        terminy += [self.akce("25", "1{0}:00".format(i)) for i in range(5)]
        self.assertEqual(len(karta.vyber(terminy, self.DNY)), karta.MAX_AKCI)

    def test_nejvys_dve_kina(self):
        terminy = [self.akce("24", "1{0}:00".format(i), "Kino") for i in range(6)]
        terminy.append(self.akce("25", "18:00"))
        kina = [t for t in karta.vyber(terminy, self.DNY) if t["typ"] == "Kino"]
        self.assertEqual(len(kina), karta.MAX_KINO)

    def test_bez_vystav(self):
        # Výstava běží týdny a „na víkend" není.
        terminy = [self.akce("24", "10:00", vicedenni=True), self.akce("24", "18:00")]
        vybrane = karta.vyber(terminy, self.DNY)
        self.assertEqual([t["zacatek"][11:16] for t in vybrane], ["18:00"])

    def test_nedele_nezmizi(self):
        # Čistě podle času by šest sobotních akcí vytlačilo celou neděli.
        terminy = [self.akce("24", "1{0}:00".format(i)) for i in range(8)]
        terminy.append(self.akce("25", "15:00"))
        dny = {t["zacatek"][:10] for t in karta.vyber(terminy, self.DNY)}
        self.assertIn("2026-10-25", dny)

    def test_stejna_akce_jen_jednou(self):
        terminy = [self.akce("24", "17:00", "Kino", akce_id=7),
                   self.akce("25", "17:00", "Kino", akce_id=7)]
        self.assertEqual(len(karta.vyber(terminy, self.DNY)), 1)

    def test_serazeno_podle_casu(self):
        terminy = [self.akce("25", "10:00"), self.akce("24", "20:00"),
                   self.akce("24", "09:00")]
        zacatky = [t["zacatek"] for t in karta.vyber(terminy, self.DNY)]
        self.assertEqual(zacatky, sorted(zacatky))

    def test_mimo_vikend_nic(self):
        self.assertEqual(karta.vyber([self.akce("26", "18:00")], self.DNY), [])

    def test_rozsah_v_jednom_mesici(self):
        self.assertEqual(karta.rozsah_dnu(self.DNY), "24.–25. října")

    def test_rozsah_pres_mesic(self):
        self.assertEqual(karta.rozsah_dnu({"2026-10-31", "2026-11-01"}),
                         "31. října – 1. listopadu")

    def test_zalom_drzi_sirku_a_pocet_radku(self):
        sirka = len                      # jeden znak = jeden pixel
        radky = karta.zalom("jedna dva tri ctyri pet sest sedm osm devet", sirka, 12, 2)
        self.assertEqual(len(radky), 2)
        self.assertTrue(radky[-1].endswith("…"))
        for radek in radky:
            self.assertLessEqual(len(radek), 12)

    def test_predlozka_nezustane_na_konci_radku(self):
        radky = karta.zalom("Koncert v Domě kultury", len, 11, 3)
        self.assertFalse(any(r.endswith(" v") for r in radky), radky)

    def test_radova_cislovka_drzi_se_slovem(self):
        radky = karta.zalom("Meziříčí / 2. hokejová liga", len, 14, 3)
        self.assertFalse(any(r.endswith(" 2.") for r in radky), radky)

    @unittest.skipUnless(_MA_PIL, "Pillow není nainstalovaný")
    def test_karta_ma_rozmer_pribehu(self):
        import tempfile
        from PIL import Image
        terminy = [self.akce("24", "18:00"), self.akce("25", "15:00")]
        with tempfile.TemporaryDirectory() as slozka:
            cil = Path(slozka) / "karta.png"
            karta.vytvor(terminy, self.DNY, cil)
            self.assertEqual(Image.open(cil).size, karta.ROZMER)

    @unittest.skipUnless(_MA_PIL, "Pillow není nainstalovaný")
    def test_zacate_akce_na_karte_nejsou(self):
        # Karta se přestavuje každou hodinu; v sobotu odpoledne nesmí
        # nabízet dopolední program.
        import tempfile
        terminy = [self.akce("24", "10:00"), self.akce("24", "18:00")]
        with tempfile.TemporaryDirectory() as slozka:
            vybrane = karta.vytvor(terminy, self.DNY, Path(slozka) / "k.png",
                                   ted=datetime(2026, 10, 24, 15, 0))
        self.assertEqual([t["zacatek"][11:16] for t in vybrane], ["18:00"])

    def test_bez_akci_karta_nevznikne(self):
        self.assertIsNone(karta.vytvor([], self.DNY, "nikam.png"))


class OdkazyProgramu(unittest.TestCase):
    def test_doplni_protokol(self):
        # 22 ze 115 odkazů v exportu nemělo https a vedlo na 404.
        self.assertEqual(akce._odkaz("www.hkkm.cz"), "https://www.hkkm.cz")

    def test_necha_plnou_adresu(self):
        self.assertEqual(akce._odkaz("http://www.dub.cz/x"), "http://www.dub.cz/x")
        self.assertEqual(akce._odkaz("https://a.cz"), "https://a.cz")

    def test_prazdny_zustane_prazdny(self):
        self.assertEqual(akce._odkaz(""), "")
        self.assertEqual(akce._odkaz("  "), "")

    def test_ted_je_bez_zony(self):
        # Časy akcí v datech zónu nemají; porovnání se zónou by spadlo.
        self.assertIsNone(akce.ted().tzinfo)


class Kostka(unittest.TestCase):
    """Kroměříž v kostce: přepis hesla z Wikipedie pod CC BY-SA."""

    VZOREK = {
        "nadpis": "Kroměříž v kostce", "titulek": "T", "popis": "P", "uvod": "U",
        "zdroj": {"heslo": "Kroměříž",
                  "url": "https://cs.wikipedia.org/wiki/Krom%C4%9B%C5%99%C3%AD%C5%BE",
                  "revize": 123, "datum": "2026-10-19",
                  "historie": "https://cs.wikipedia.org/w/index.php?title=x&action=history",
                  "licence": "CC BY-SA 4.0",
                  "licence_url": "https://creativecommons.org/licenses/by-sa/4.0/deed.cs"},
        "sekce": [
            {"id": "a", "nadpis": "První", "odstavce": ["<b>x</b>"]},
            {"id": "b", "nadpis": "Druhá", "odstavce": ["y"],
             "seznamy": [{"nadpis": "Seznam", "polozky": ["jedna", "dvě"]}]},
        ],
    }

    def test_zdroj_ukazuje_na_konkretni_verzi(self):
        # Živé heslo se mění; atribuce musí vést na text, ze kterého jsme psali.
        url = render._kostka_zdroj_url(self.VZOREK["zdroj"])
        self.assertIn("oldid=123", url)
        self.assertIn("title=Krom%C4%9B%C5%99%C3%AD%C5%BE", url)

    def test_atribuce_splnuje_licenci(self):
        html = render._kostka(self.VZOREK)
        self.assertIn("oldid=123", html)
        self.assertIn("action=history", html)
        self.assertIn('rel="license noopener"', html)
        self.assertIn("CC BY-SA 4.0", html)
        self.assertIn("po svém", html)  # označení úpravy

    def test_obsah_vede_na_kazdou_sekci(self):
        html = render._kostka(self.VZOREK)
        for s in self.VZOREK["sekce"]:
            self.assertIn('href="#{0}"'.format(s["id"]), html)
            self.assertIn('<section id="{0}">'.format(s["id"]), html)
        self.assertIn("<h3>Seznam</h3><ul><li>jedna</li>", html)

    def test_text_se_utece(self):
        self.assertNotIn("<b>x</b>", render._kostka(self.VZOREK))

    def test_jsonld_nese_zdroj_a_licenci(self):
        ld = render._ld_kostka(self.VZOREK)
        self.assertIn("oldid=123", ld["isBasedOn"]["url"])
        self.assertEqual(ld["license"], self.VZOREK["zdroj"]["licence_url"])

    def test_ostra_data_jsou_uplna(self):
        data = render._nacti_kostku()
        self.assertIsNotNone(data)
        self.assertTrue(data["zdroj"]["licence"].startswith("CC BY-SA"))
        self.assertTrue(str(data["zdroj"]["revize"]).isdigit())
        idcka = [s["id"] for s in data["sekce"]]
        self.assertEqual(len(idcka), len(set(idcka)))
        for s in data["sekce"]:
            self.assertTrue(s["nadpis"] and s["odstavce"], s["id"])


class DruhPadu(unittest.TestCase):
    """Stav se commituje do veřejného repa, nesmí v něm být zdroj."""

    def test_uryvek_zdroje_se_zahodi(self):
        self.assertEqual(
            pipeline._druh_padu(
                'Doslova převzaté formulace z oznámení: „od 6 prosince 2024"'),
            "Doslova převzaté formulace z oznámení")

    def test_cislo_shody_zustane(self):
        self.assertEqual(
            pipeline._druh_padu('Věty skoro totožné s oznámením (shoda 0.67): „ab"'),
            "Věty skoro totožné s oznámením (shoda 0.67)")

    def test_mistni_cesta_se_zahodi(self):
        self.assertEqual(
            pipeline._druh_padu("[Errno 2] No such file: 'C:/Users/kdosi/x.json'"),
            "[Errno 2] No such file")

    def test_duvod_bez_dvojtecky_zustane_cely(self):
        self.assertEqual(
            pipeline._druh_padu("Výstup obsahuje přímou citaci v uvozovkách."),
            "Výstup obsahuje přímou citaci v uvozovkách.")


class AkceParsovani(unittest.TestCase):
    """Vzorek je oříznutý skutečný export, ne vymyšlené XML."""

    @classmethod
    def setUpClass(cls):
        xml = (FIXTURES / "akce-vzorek.xml").read_text(encoding="utf-8")
        cls.data = akce.rozparsuj(xml)
        cls.terminy = cls.data["terminy"]

    def test_nacte_ciselniky(self):
        self.assertEqual(len(self.data["typy"]), 8)
        self.assertEqual(self.data["typy"][11], "Kino")

    def test_kazdy_termin_ma_nazev_a_zacatek(self):
        for t in self.terminy:
            self.assertTrue(t["nazev"], t)
            self.assertTrue(t["zacatek"], t)

    def test_razeni_podle_zacatku(self):
        zacatky = [t["zacatek"] for t in self.terminy]
        self.assertEqual(zacatky, sorted(zacatky))

    def test_vicedenni_se_pozna(self):
        vicedenni = [t for t in self.terminy if t["vicedenni"]]
        self.assertTrue(vicedenni)
        for t in vicedenni:
            self.assertNotEqual(t["zacatek"][:10], t["konec"][:10])

    def test_misto_nula_je_prazdne(self):
        # place=0 je v číselníku s prázdným názvem a znamená neuvedeno.
        bez_mista = [t for t in self.terminy if not t["misto"]]
        self.assertTrue(bez_mista, "vzorek měl obsahovat akci bez místa")

    def test_perex_nema_znacky(self):
        for t in self.terminy:
            self.assertNotIn("<", t["perex"])

    def test_kratka_pole_jsou_na_jeden_radek(self):
        # Poznámka k ceně v exportu obsahuje odřádkování; v pruhu pod
        # názvem by rozhodila kartu.
        for t in self.terminy:
            for pole in ("nazev", "poznamka", "cena_pozn"):
                self.assertNotIn("\n", t[pole], (t["nazev"], pole))

    def test_rozbity_cas_neshodi_parsovani(self):
        self.assertEqual(akce._cas("nesmysl"), "")
        self.assertEqual(akce._cas(""), "")


class AkceOkna(unittest.TestCase):
    """Okna „dnes" a „víkend" — podle nich lidé akce hledají."""

    def test_dnes_je_jeden_den(self):
        self.assertEqual(render._okno_dnes(date(2026, 10, 23)),
                         {"2026-10-23"})

    def test_vikend_z_patku_je_nadchazejici(self):
        self.assertEqual(render._okno_vikend(date(2026, 10, 23)),
                         {"2026-10-24", "2026-10-25"})

    def test_vikend_v_sobotu_je_ten_probihajici(self):
        self.assertEqual(render._okno_vikend(date(2026, 10, 24)),
                         {"2026-10-24", "2026-10-25"})

    def test_vikend_v_nedeli_se_vraci_na_sobotu(self):
        # V neděli nesmí skočit na příští týden, zrovna probíhá.
        self.assertEqual(render._okno_vikend(date(2026, 10, 25)),
                         {"2026-10-24", "2026-10-25"})

    def test_vikend_v_pondeli_je_pristi(self):
        self.assertEqual(render._okno_vikend(date(2026, 10, 26)),
                         {"2026-10-31", "2026-11-01"})

    def test_vicedenni_akce_spada_do_okna(self):
        vystava = {"zacatek": "2026-05-15T09:00:00",
                   "konec": "2026-11-01T17:00:00", "vicedenni": True}
        self.assertTrue(render._v_okne(vystava, {"2026-10-23"}))

    def test_jednodenni_mimo_okno_nespada(self):
        koncert = {"zacatek": "2026-10-30T19:00:00",
                   "konec": "2026-10-30T21:00:00", "vicedenni": False}
        self.assertFalse(render._v_okne(koncert, {"2026-10-23"}))


class AkceVykresleni(unittest.TestCase):
    def test_cena_nula_neni_zdarma(self):
        # V datech znamená 0 „neuvedena", ne vstup zdarma.
        self.assertEqual(render._cena_text({"cena": 0}), "")
        self.assertEqual(render._cena_text({"cena": 0, "zdarma": True}), "zdarma")
        self.assertEqual(render._cena_text({"cena": 80}), "80 Kč")

    def test_cas_bez_nuly_na_zacatku(self):
        self.assertEqual(render._cas_hm("2026-10-24T09:00:00"), "9.00")
        self.assertEqual(render._cas_hm("2026-10-24T17:30:00"), "17.30")

    def test_datum_kratce(self):
        # Nezlomitelná mezera: datum se v úzkém sloupci nesmí rozdělit.
        self.assertEqual(render._datum_kratce("2026-11-01"), "1.\u00a011.")

    def test_pristupnost_se_zkrati(self):
        self.assertEqual(
            render._pristupnost("nevhodné pro nezletilé osoby do 12 let"),
            "nevhodné do 12 let")

    def test_kazdy_typ_ma_vlastni_piktogram(self):
        for typ in render.TYPY_AKCI:
            self.assertNotEqual(piktogramy.pro_typ_akce(typ), "akce", typ)

    def test_kazdy_typ_ma_vlastni_metadata(self):
        # Stránky typů mají být samostatné, ne přefiltrovaný rodič.
        for pole in ("titulek", "popis", "h1", "uvod"):
            hodnoty = [u[pole] for u in render.TYPY_AKCI.values()]
            self.assertEqual(len(hodnoty), len(set(hodnoty)), pole)

    def test_karta_neopakuje_poznamku_a_format(self):
        # Data města mají „titulky", DK „titulky | 2D"; vedle sebe to
        # vypadá jako chyba.
        karta = render._karta_akce({
            "nazev": "Film", "zacatek": "2026-10-24T17:30:00",
            "typ": "Kino", "poznamka": "titulky",
            "kino": {"format": "titulky | 2D"}})
        self.assertEqual(karta.count("titulky | 2D"), 1)
        self.assertNotIn("titulky ·", karta)

    def test_karta_uteche_html_v_nazvu(self):
        karta = render._karta_akce({
            "nazev": '<script>zle()</script>', "zacatek": "2026-10-24T10:00:00",
            "typ": "Sport"})
        self.assertNotIn("<script>", karta)

    def test_atribuce_jmenuje_zdroj_i_licenci(self):
        podpis = render._atribuce()
        self.assertIn(config.AKCE_POSKYTOVATEL, podpis)
        self.assertIn("creativecommons.org", podpis)


class KinoDK(unittest.TestCase):
    def test_rozebere_vzorek_stranky(self):
        markup = (FIXTURES / "dk-film.html").read_text(encoding="utf-8")
        udaje = kino_dk.rozeber(markup)
        self.assertEqual(udaje["stopaz"], "asi 2 hodiny")
        self.assertEqual(udaje["format"], "titulky | 2D")
        self.assertIn("do 12 let", udaje["pristupnost"])
        self.assertEqual(udaje["puvodni_nazev"],
                         "National Theatre Live: Frankenstein")

    def test_rozbite_html_vrati_prazdno(self):
        # Scrape cizí stránky nesmí shodit build celého webu.
        for vstup in ("", "<html>", '<div class="delka">(2 h',
                      "<h1>bez mikrodat</h1>"):
            self.assertEqual(kino_dk.rozeber(vstup), {})


class PojistkaSlang(unittest.TestCase):
    def test_zakazany_vyraz_se_zachyti(self):
        self.assertEqual(styl.zkontroluj_zakazany_slang("Ten gyatt je mid."),
                         ["gyatt"])

    def test_delsi_tvar_vyhraje(self):
        self.assertEqual(styl.zkontroluj_zakazany_slang("Klasické mogging."),
                         ["mogging"])

    def test_povoleny_slang_projde(self):
        self.assertEqual(styl.zkontroluj_zakazany_slang(
            "Radnice to posunula, W rozhodnutí, aura +100."), [])

    def test_uvnitr_jineho_slova_neplati(self):
        self.assertEqual(styl.zkontroluj_zakazany_slang("Rozbopovaný nesmysl"), [])


class PojistkaAntiteze(unittest.TestCase):
    def test_carka_ne(self):
        self.assertTrue(styl.zkontroluj_antitezi("Je to volba, ne podmínka."))

    def test_neslo_ale(self):
        self.assertTrue(styl.zkontroluj_antitezi("Nešlo o výměnu, ale o srovnání."))

    def test_nejde_o_jde_o(self):
        self.assertTrue(styl.zkontroluj_antitezi("Nejde o peníze, jde o princip."))

    def test_bezna_veta_projde(self):
        self.assertEqual(styl.zkontroluj_antitezi(
            "Strom se rozsvítí v neděli a trhy běží do 23. prosince."), [])


class Piktogramy(unittest.TestCase):
    def test_tema_podle_prvniho_znameho_tagu(self):
        self.assertEqual(piktogramy.pro_tema(["neznámé", "doprava"]), "doprava")

    def test_diakritika_v_tagu(self):
        self.assertEqual(piktogramy.pro_tema(["školství"]), "skolstvi")

    def test_vychozi_kdyz_nic_nesedi(self):
        self.assertEqual(piktogramy.pro_tema(["cosi"]), "_vychozi")
        self.assertEqual(piktogramy.pro_tema([]), "_vychozi")

    def test_svg_je_dekorativni_bez_popisu(self):
        self.assertIn('aria-hidden="true"', piktogramy.svg("doprava"))

    def test_svg_s_popisem_ma_roli(self):
        self.assertIn('role="img"', piktogramy.svg("doprava", popis="Téma: doprava"))

    def test_vsechna_temata_maji_tvar(self):
        for tema in piktogramy.dostupna_temata():
            self.assertTrue(piktogramy.svg(tema).count("<") > 2, tema)


class ExtrakceHtml(unittest.TestCase):
    UKAZKA = (
        '<div class="news"><div class="news-content"><div class="plugin-text">'
        "<p>První odstavec.</p><p>Druhý <strong>odstavec</strong>.</p>"
        "</div></div><div class='jine'>Nepatří sem</div></div>"
    )

    def test_grab_bere_vnorene_divy(self):
        vnitrek = htmlutil.grab(self.UKAZKA, "div", "news-content")
        self.assertIn("První odstavec", vnitrek)
        self.assertNotIn("Nepatří sem", vnitrek)

    def test_odstavce(self):
        odstavce = htmlutil.to_paragraphs(htmlutil.grab(self.UKAZKA, "div", "news-content"))
        self.assertEqual(odstavce, ["První odstavec.", "Druhý odstavec."])

    def test_meta(self):
        markup = '<meta property="og:image" content="https://x/y.jpg" />'
        self.assertEqual(htmlutil.meta(markup, "og:image"), "https://x/y.jpg")

    def test_meta_chybejici(self):
        self.assertEqual(htmlutil.meta("<html></html>", "og:image"), "")


class PrepisBezSite(unittest.TestCase):
    """Projede `prepis` přes stub backend, tedy bez modelu i bez sítě."""

    POLOZKA = {
        "title": "V Kroměříži přibude pět nových tabulí",
        "published": "2026-10-23T08:15:00+02:00",
        "rubrika": "Tiskové zprávy",
        "perex": "",
        "body": [
            "Na třech zastávkách přibudou tabule. „Ukážou i meziměstské spoje,“ uvedl Jan Hebnar.",
            "Ročně najedou autobusy 340 tisíc kilometrů.",
        ],
    }

    def setUp(self):
        self._puvodni = config.BACKEND
        config.BACKEND = "stub"

    def tearDown(self):
        config.BACKEND = self._puvodni

    def test_vraci_ocekavanou_strukturu(self):
        data = rewrite.prepis(dict(self.POLOZKA), "volny")
        self.assertEqual(len(data["tldr"]), 3)
        self.assertTrue(data["body"])
        self.assertTrue(data["tags"])

    def test_nadpis_nekonci_teckou(self):
        data = rewrite.prepis(dict(self.POLOZKA), "volny")
        self.assertFalse(data["headline"].endswith("."))

    def test_vystup_projde_pojistkami(self):
        # Kdyby neprošel, `prepis` by vyhodil ValueError — tohle hlídá, že
        # pojistky jsou v cestě opravdu zapojené.
        data = rewrite.prepis(dict(self.POLOZKA), "volny")
        vystup = " ".join([data["headline"]]
                          + [o["text"] for o in data["tldr"]] + data["body"])
        self.assertFalse(rewrite.zkontroluj_citace(vystup))

    def test_vymyslene_cislo_shodi_prepis(self):
        """Model vrátí číslo, které ve zdroji není — `prepis` musí vyhodit."""
        puvodni = rewrite._zeptej_se
        rewrite._zeptej_se = lambda *a, **k: (
            '{"headline": "Tabule", "tldr": [], '
            '"body": ["Stalo to 999 korun"], "tags": ["doprava"]}')
        try:
            with self.assertRaises(ValueError) as chyba:
                rewrite.prepis(dict(self.POLOZKA), "volny", pokusy=1)
            self.assertIn("999", str(chyba.exception))
        finally:
            rewrite._zeptej_se = puvodni

    def test_opravny_pokus(self):
        """První odpověď je vadná, druhá dobrá — `prepis` to má ustát."""
        puvodni = rewrite._zeptej_se
        odpovedi = [
            'tohle není JSON',
            '{"headline": "Tabule", "tldr": [], "body": ["Přibudou tabule"], "tags": ["doprava"]}',
        ]
        rewrite._zeptej_se = lambda *a, **k: odpovedi.pop(0)
        try:
            data = rewrite.prepis(dict(self.POLOZKA), "volny", pokusy=2)
            self.assertEqual(data["headline"], "Tabule")
            self.assertEqual(odpovedi, [])
        finally:
            rewrite._zeptej_se = puvodni


class Ilustrace(unittest.TestCase):
    def hodnoty(self, *odstavce):
        return ["\u00a0".join(filter(None, k[1:3])) for k in ilustrace.karty(list(odstavce))]

    def test_penize_ve_vsech_zapisech(self):
        self.assertEqual(self.hodnoty("Zaplatí cca 390 tisíc korun."), ["390\u00a0tis.\u00a0Kč"])
        self.assertEqual(self.hodnoty("Stojí 1,2 milionu korun."), ["1,2\u00a0mil.\u00a0Kč"])
        self.assertEqual(self.hodnoty("Vyšlo to na 53 245 korun."), ["53\u00a0245\u00a0Kč"])
        self.assertEqual(self.hodnoty("Vyšlo to na 53.245 korun."), ["53\u00a0245\u00a0Kč"])
        self.assertEqual(self.hodnoty("Dá 2 miliardy korun."), ["2\u00a0mld.\u00a0Kč"])
        self.assertEqual(self.hodnoty("Vstup za 80 Kč."), ["80\u00a0Kč"])

    def test_karty_v_poradi_textu_a_kazdy_druh_jednou(self):
        karty = ilustrace.karty(["Stavět se začne v listopadu, plocha 85 m², cena 390 tisíc korun.",
                                 "Pak v prosinci a dalších 10 m²."])
        self.assertEqual([k[0] for k in karty], ["akce", "plocha", "penize"])
        self.assertEqual(karty[0][1], "listopad")

    def test_mrizka_jen_do_sta_metru(self):
        self.assertEqual(ilustrace.karty(["Plocha 85 m²."])[0][4], 85)
        self.assertIsNone(ilustrace.karty(["Plocha 250 m²."])[0][4])
        self.assertIsNone(ilustrace.karty(["Plocha 85,5 m²."])[0][4])

    def test_jedina_karta_jde_na_celou_sirku(self):
        self.assertIn("ilu-jedna", ilustrace.karty_html(["Stojí 390 tisíc korun."]))
        self.assertNotIn("ilu-jedna", ilustrace.karty_html(["Stojí 390 tisíc korun, hotovo v září."]))
        self.assertEqual(ilustrace.karty_html(["Bez jediného čísla."]), "")

    def test_kdy_bere_drivejsi_z_data_a_mesice(self):
        self.assertEqual(self.hodnoty("Od 19. října jedou pasti, v listopadu konec."), ["19. října"])
        self.assertEqual(self.hodnoty("V listopadu začnou, 2. prosince konec."), ["listopad"])
        self.assertEqual(self.hodnoty("Začnou v listopadu, 2. prosince konec."), ["listopad"])

    def test_ikony_se_v_clanku_neopakuji(self):
        self.assertEqual(ilustrace.ikony(["Nové hřiště.", "Další hřiště.", "Bez obrázku tady."]),
                         ["sport", None, None])

    def test_parkovani_neni_park(self):
        self.assertEqual(ilustrace.ikony(["Ubude parkování."]), ["doprava"])
        self.assertEqual(ilustrace.ikony(["Vysadí stromy v parku."]), ["priroda"])

    def test_stavba_se_nechyta_na_podobnych_slovech(self):
        self.assertEqual(ilustrace.ikony(["Je to postava z příběhu."]), [None])
        self.assertEqual(ilustrace.ikony(["Referent dopravy Pavel."]), ["doprava"])
        self.assertEqual(ilustrace.ikony(["Opravy vozovek začnou."]), ["stavba"])
        self.assertEqual(ilustrace.ikony(["Ulice Dolnozahradská."]), [None])

    def test_clanek_ma_karty_po_prvnim_odstavci(self):
        clanek = {"headline": "T", "slug": "t", "tags": ["sport"], "tldr": [],
                  "body": ["Hřiště bude.", "Stojí 390 tisíc korun, staví se v listopadu."]}
        stranka = render._clanek(clanek, [])
        self.assertLess(stranka.index("Hřiště bude."), stranka.index("ilu-cisla"))
        self.assertLess(stranka.index("ilu-cisla"), stranka.index("Stojí 390"))
        self.assertIn('class="s-ikonou"', stranka)


if __name__ == "__main__":
    unittest.main()
