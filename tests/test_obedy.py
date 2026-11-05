# -*- coding: utf-8 -*-
"""Polední menu: parsery nad ořezanými skutečnými stránkami, pojistka na
datum, stahování bez sítě a vykreslení stránky."""

import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kromka import config, obedy, render  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CTVRTEK = date(2026, 11, 5)


def _vzorek(id_):
    return (FIXTURES / "obedy-{0}.html".format(id_)).read_text(encoding="utf-8")


def _podnik(id_):
    return next(p for p in obedy.PODNIKY if p["id"] == id_)


def _rozeber(id_, dnes=CTVRTEK):
    return obedy.rozeber(_podnik(id_), _vzorek(id_), dnes)


class ObedyCena(unittest.TestCase):
    def test_tvary_ceny(self):
        self.assertEqual(obedy._s_cenou("Dýňový krém 20Kč"), ("Dýňový krém", 20))
        self.assertEqual(obedy._s_cenou("Kuřecí řízek, okurek 159"), ("Kuřecí řízek, okurek", 159))
        self.assertEqual(obedy._s_cenou("Hrášková 40,-"), ("Hrášková", 40))
        self.assertEqual(obedy._s_cenou("Kč 65,-"), ("", 65))
        self.assertEqual(obedy._s_cenou("Panenka 1290 Kč"), ("Panenka", 1290))

    def test_datum_ani_gramaz_nejsou_cena(self):
        # Rok na konci oznámení by jinak stál 2026 Kč.
        self.assertIsNone(obedy._s_cenou("HUSÍ HODY 6.-11.11.2026")[1])
        self.assertIsNone(obedy._s_cenou("Filet z candáta 150g")[1])
        self.assertIsNone(obedy._s_cenou("otevřeno i v neděli 12-17 hod.")[1])


class ObedyParsery(unittest.TestCase):
    def test_beer_bowl(self):
        menu = _rozeber("beer-bowl")
        self.assertEqual(menu["polevky"][0]["cena"], 30)
        self.assertEqual(len(menu["jidla"]), 6)
        prvni = menu["jidla"][0]
        self.assertTrue(prvni["nazev"].startswith("Vídeňská hovězí pečeně (150 g)"))
        self.assertEqual((prvni["cena"], prvni["alergeny"]), (175, "1a, 9"))

    def test_earnest_bez_mezer_po_znackach(self):
        menu = _rozeber("earnest")
        self.assertEqual(menu["polevky"][0]["cena"], 65)
        self.assertEqual(len(menu["jidla"]), 8)
        # Inline značky nesmí nechat mezeru před čárkou ani v závorce.
        self.assertIn("(1a, 3, 7, 9)", menu["polevky"][0]["nazev"])
        self.assertTrue(any(j["nazev"].startswith("Vejce Benedikt, 2 zastřená")
                            for j in menu["jidla"]))

    def test_oskol_den_podle_data(self):
        menu = _rozeber("kozlovna-oskol")
        self.assertEqual(menu["polevky"], [{"nazev": "Dýňový krém", "cena": 20}])
        self.assertEqual([j["cena"] for j in menu["jidla"]], [139, 149, 159, 199])
        self.assertTrue(menu["jidla"][0]["nazev"].startswith("Luštěninový guláš"))
        self.assertTrue(_rozeber("kozlovna-oskol", date(2026, 11, 2))["jidla"][0]
                        ["nazev"].startswith("Čínské rýžové nudle"))

    def test_oskol_patek_z_minuleho_tydne_se_neukaze(self):
        # Na stránce je „PÁTEK 30. 10. 2026". V pátek 6. 11. tedy nic,
        # 30. 10. by to platilo.
        self.assertEqual(_rozeber("kozlovna-oskol", date(2026, 11, 6)), {})
        self.assertEqual(len(_rozeber("kozlovna-oskol", date(2026, 10, 30))["jidla"]), 4)

    def test_bohemia_den_a_cely_tyden(self):
        menu = _rozeber("nova-bohemia")
        self.assertEqual(menu["polevky"][0]["nazev"], "Hrášková s uzeným masem a opečeným chlebem")
        self.assertEqual([j["nazev"][:2] for j in menu["jidla"]], ["M1", "M2", "M3", "M4", "M5"])
        self.assertIn("HUSÍ HODY 6.-11.11.2026", menu["poznamky"])
        vse = " ".join(menu["poznamky"] + [j["nazev"] for j in menu["jidla"]])
        self.assertNotIn("ZDE VLOŽIT", vse.upper())
        # „více" je na stránce zakomentované.
        self.assertNotIn("více", menu["poznamky"])

    def test_bohemia_mimo_tyden_nic(self):
        self.assertEqual(_rozeber("nova-bohemia", date(2026, 11, 9)), {})
        self.assertEqual(_rozeber("nova-bohemia", date(2026, 11, 7)), {})   # sobota

    def test_sladovna(self):
        menu = _rozeber("sladovna")
        # Na stránce je zvýhodněná cena k menu, ne cena samotné polévky.
        self.assertEqual(menu["polevky"][0]["cena"], 40)
        self.assertEqual(len(menu["jidla"]), 4)
        self.assertTrue(menu["poznamky"][0].startswith("Dnes máme zavřeno"))
        self.assertNotIn("Mattoni", " ".join(j["nazev"] for j in menu["jidla"]))

    def test_rozbite_html_vrati_prazdno(self):
        # Cizí web se změní bez varování; build to nesmí shodit.
        for podnik in obedy.PODNIKY:
            for vstup in ("", "<html>", '<section id="dmenu"><h2>čtvrtek 5. 11. 2026',
                          "<h1>Polední menu</h1><div id=\"week\">2.-6.11.</section>"):
                with self.subTest(podnik=podnik["id"], vstup=vstup):
                    self.assertEqual(obedy.rozeber(podnik, vstup, CTVRTEK), {})


class ObedyStazeni(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._patche = [mock.patch.object(config, "OBEDY_FILE",
                                          Path(self._tmp.name) / "obedy.json")]
        for p in self._patche:
            p.start()
        self.stazene = []

    def tearDown(self):
        for p in self._patche:
            p.stop()
        self._tmp.cleanup()

    def _get(self, selhat=()):
        def get(url, binary=False, agent=None):
            self.stazene.append(url)
            podnik = next(p for p in obedy.PODNIKY if p["menu"] == url)
            if podnik["id"] in selhat:
                raise RuntimeError("výpadek")
            return _vzorek(podnik["id"])
        return get

    def _aktualizuj(self, kdy, vynutit=False, selhat=()):
        with mock.patch.object(obedy, "ted", return_value=kdy), \
                mock.patch.object(obedy.net, "get", side_effect=self._get(selhat)):
            return obedy.aktualizuj(vynutit=vynutit, verbose=False)

    def test_mimo_okno_nestahuje(self):
        self._aktualizuj(datetime(2026, 11, 7, 11, 0))      # sobota
        self._aktualizuj(datetime(2026, 11, 5, 7, 30))      # před osmou
        self._aktualizuj(datetime(2026, 11, 5, 14, 5))      # po druhé
        self.assertEqual(self.stazene, [])

    def test_ve_vsedni_den_stahne_vsechny_a_podruhe_ne(self):
        data = self._aktualizuj(datetime(2026, 11, 5, 11, 17))
        self.assertEqual(len(self.stazene), len(obedy.PODNIKY))
        dnes = obedy.dnesni(data, CTVRTEK)
        self.assertTrue(all(dnes.values()))
        self.assertTrue(config.OBEDY_FILE.exists())
        self._aktualizuj(datetime(2026, 11, 5, 11, 20))
        self.assertEqual(len(self.stazene), len(obedy.PODNIKY))

    def test_vypadek_jednoho_podniku_neshodi_ostatni(self):
        data = self._aktualizuj(datetime(2026, 11, 5, 11, 17), selhat={"earnest"})
        dnes = obedy.dnesni(data, CTVRTEK)
        self.assertEqual(dnes["earnest"], {})
        self.assertTrue(dnes["kozlovna-oskol"])

    def test_vcerejsi_zaznam_dnes_neplati(self):
        data = self._aktualizuj(datetime(2026, 11, 5, 11, 17))
        self.assertTrue(all(not m for m in obedy.dnesni(data, date(2026, 11, 6)).values()))

    def test_sladovna_se_stejnym_menu_druhy_den_neplati(self):
        # Stránka bez data: když se menu přes noc nezměnilo, nepřepsali ho.
        self._aktualizuj(datetime(2026, 11, 5, 11, 17))
        data = self._aktualizuj(datetime(2026, 11, 6, 9, 17))
        patek = obedy.dnesni(data, date(2026, 11, 6))
        self.assertEqual(patek["sladovna"], {})
        self.assertEqual(patek["kozlovna-oskol"], {})        # pátek s datem 30. 10.
        self.assertEqual(len(patek["nova-bohemia"]["jidla"]), 5)
        # A ve čtvrtek samotném se opakované stažení počítá dál.
        data = self._aktualizuj(datetime(2026, 11, 5, 12, 30), vynutit=True)
        self.assertTrue(obedy.dnesni(data, CTVRTEK)["sladovna"])


class ObedyStranka(unittest.TestCase):
    MENU = {"polevky": [{"nazev": "Dýňový krém", "cena": 20}],
            "jidla": [{"nazev": "Guláš <script>", "cena": 139, "alergeny": "1, 7"}],
            "poznamky": ["Husí hody"]}

    def _data(self, den="2026-11-05"):
        return {"podniky": {"kozlovna-oskol": {"den": den, "menu": self.MENU,
                                               "stazeno": "2026-11-05T10:17:00+00:00"}}}

    def test_vsedni_den(self):
        markup = render._obedy(self._data(), datetime(2026, 11, 5, 12, 0))
        self.assertIn("Guláš &lt;script&gt;", markup)
        self.assertNotIn("<script>", markup)
        self.assertIn("139\xa0Kč", markup)
        self.assertIn("alergeny 1, 7", markup)
        self.assertIn("utm_campaign=obedy", markup)
        # Podnik s menu nahoře, ostatní pod ním s poctivou větou.
        self.assertLess(markup.index("Kozlovna Oskol"), markup.index("Beer &amp; Bowl"))
        self.assertIn("Dnešní menu na webu zatím není.", markup)

    def test_vcerejsi_data_se_neukazi(self):
        markup = render._obedy(self._data("2026-11-04"), datetime(2026, 11, 5, 12, 0))
        self.assertNotIn("Dýňový krém", markup)

    def test_o_vikendu_prazdny_stav(self):
        markup = render._obedy(self._data("2026-11-07"), datetime(2026, 11, 7, 12, 0))
        self.assertIn(render.OBEDY_VIKEND, markup)
        self.assertNotIn('class="obed"', markup)

    def test_v_menu_hned_za_programem(self):
        menu = render._menu()
        self.assertLess(menu.index(render.PROGRAM_CESTA), menu.index(render.OBEDY_CESTA))
        self.assertLess(menu.index(render.OBEDY_CESTA), menu.index("radnice"))

    def test_v_sitemape(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(config, "OBEDY_FILE", Path(tmp) / "obedy.json"):
            obedy.uloz(self._data())
            sitemap = render._sitemap([], {})
        self.assertIn(render._abs(render.OBEDY_CESTA) + "</loc><lastmod>2026-11-05<", sitemap)


if __name__ == "__main__":
    unittest.main()
