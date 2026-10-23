# -*- coding: utf-8 -*-
"""Testy částí, které nevolají síť ani model.

Spuštění: python -m unittest discover -s tests
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kromka import config, htmlutil, piktogramy, rewrite, styl  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
