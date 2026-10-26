# -*- coding: utf-8 -*-
"""Příspěvky čtenářů: tabulka → přepis → článek → web, bez sítě a bez modelu."""

import inspect
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kromka import config, prispevky, render, store  # noqa: E402

FIXTURA = Path(__file__).resolve().parent / "fixtures" / "prispevky.json"


class PrispevkyBehem(unittest.TestCase):
    """Celá cesta s fixturou místo endpointu a backendem stub."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self.radky = json.loads(FIXTURA.read_text(encoding="utf-8"))["radky"]
        self.soubor = tmp / "prispevky.json"
        self._zapis(self.radky)
        self._patche = [
            mock.patch.object(config, "BACKEND", "stub"),
            mock.patch.object(config, "ARTICLES", tmp / "articles"),
            mock.patch.object(config, "PRISPEVKY_SOUBOR", str(self.soubor)),
        ]
        for p in self._patche:
            p.start()

    def tearDown(self):
        for p in self._patche:
            p.stop()
        self._tmp.cleanup()

    def _zapis(self, radky):
        self.soubor.write_text(json.dumps({"radky": radky}, ensure_ascii=False), encoding="utf-8")

    def test_schvaleny_vyjde_zamitnuty_ne(self):
        nove = prispevky.v_cronu(verbose=False)
        self.assertEqual(len(nove), 1)
        clanek = nove[0]
        self.assertEqual(clanek["typ"], "prispevek")
        self.assertEqual(clanek["autor"], "Jana Nováková")
        self.assertEqual(clanek["odkaz"], "https://example.org/spolek-zahrada")
        self.assertTrue(clanek["id"].startswith("ctenar:"))
        self.assertTrue(store.existuje(clanek["id"]))

    def test_email_ani_cizi_pole_do_archivu_nejdou(self):
        clanek = prispevky.v_cronu(verbose=False)[0]
        ulozeny = json.dumps(store.nacti(clanek["id"]), ensure_ascii=False)
        self.assertNotIn("jana@example.org", ulozeny)
        self.assertNotIn("email", store.nacti(clanek["id"]))
        self.assertNotIn("2026-10-26T08:15:00Z", ulozeny)

    def test_id_je_stabilni_a_hotovy_se_neprepisuje(self):
        prvni = prispevky.v_cronu(verbose=False)[0]
        self.assertEqual(prispevky.id_pro(self.radky[0]), prvni["id"])
        # Druhý běh nic nového nenapíše (princip 5), jen srovná stav.
        self.assertEqual(prispevky.v_cronu(verbose=False), [])

    def test_stahnout_smaze_clanek(self):
        clanek = prispevky.v_cronu(verbose=False)[0]
        radky = [dict(self.radky[0], stav="stáhnout")]
        self._zapis(radky)
        prispevky.v_cronu(verbose=False)
        self.assertFalse(store.existuje(clanek["id"]))
        self.assertEqual(store.vsechny(), [])

    def test_vypadek_cteni_neshodi_beh(self):
        with mock.patch.object(prispevky, "nacti", side_effect=RuntimeError("výpadek")):
            self.assertEqual(prispevky.v_cronu(verbose=False), [])

    def test_chyba_pojistky_se_zapise_jako_chyba(self):
        stavy = []
        with mock.patch.object(prispevky.rewrite, "prepis_prispevku",
                               side_effect=ValueError("Čísla, která nejsou ve zdroji: 7")), \
                mock.patch.object(prispevky, "zapis_stav",
                                  side_effect=lambda *a, **k: stavy.append((a, k))):
            self.assertEqual(prispevky.v_cronu(verbose=False), [])
        self.assertEqual(stavy[0][0][1], prispevky.CHYBA)
        # Do tabulky jde druh pádu bez úryvku, stejně jako do state.json.
        self.assertEqual(stavy[0][1]["poznamka"], "Čísla, která nejsou ve zdroji")

    def test_bez_jmena_nevyjde(self):
        self._zapis([dict(self.radky[0], jmeno="  ")])
        self.assertEqual(prispevky.v_cronu(verbose=False), [])

    def test_render_ukaze_ctenare_a_nofollow(self):
        clanek = prispevky.v_cronu(verbose=False)[0]
        html = render._clanek(clanek, [])
        self.assertIn("od čtenáře", html)
        self.assertIn("Jana Nováková", html)
        self.assertIn('rel="nofollow ugc noopener"', html)
        ld = render._ld_clanek(clanek)
        self.assertEqual(ld["author"], {"@type": "Person", "name": "Jana Nováková"})


class PrispevkyBezpecnost(unittest.TestCase):

    def test_odkaz_jen_http(self):
        self.assertEqual(prispevky.bezpecny_odkaz("javascript:alert(1)"), "")
        self.assertEqual(prispevky.bezpecny_odkaz("mailto:a@b.cz"), "")
        self.assertEqual(prispevky.bezpecny_odkaz(" https://a.cz/x "), "https://a.cz/x")

    def test_vypnuto_bez_nastaveni(self):
        with mock.patch.object(config, "PRISPEVKY_URL", ""), \
                mock.patch.object(config, "PRISPEVKY_SOUBOR", ""):
            self.assertFalse(prispevky.zapnuto())
            self.assertEqual(prispevky.v_cronu(verbose=False), [])

    def test_zprava_mesta_nema_podpis(self):
        html = render._clanek({"slug": "x", "headline": "Most", "body": ["Text."],
                               "tags": ["doprava"], "autor": "Někdo"}, [])
        self.assertNotIn("od čtenáře", html)
        self.assertNotIn("Poslal(a)", html)


class PrispevkyOdkazy(unittest.TestCase):
    """Formulář musí být vidět všude, kde jsme se dohodli."""

    def test_odkaz_v_menu_paticce_a_pod_clankem(self):
        stranka = render._stranka("T", "P", "<p>x</p>")
        self.assertIn('<li class="menu-prispevek"><a class="je-sekce je-prispevek" '
                      'href="/poslat-novinku.html"', stranka)
        # V hamburgeru druhá za programem; drží to `order` v CSS podle třídy.
        self.assertIn("li.menu-prispevek { order: 0; }", stranka)
        self.assertIn('</span>Menu', stranka)
        self.assertRegex(stranka, r'(?s)<footer>.*href="/poslat-novinku.html"')
        clanek = render._clanek({"slug": "x", "headline": "Most", "body": ["Text."],
                                 "tags": ["doprava"]}, [])
        self.assertIn('class="vyzva vyzva-clanek"', clanek)
        self.assertIn("vyzva-o-webu", render._o_webu())

    def test_stranka_s_formularem(self):
        with mock.patch.object(config, "PRISPEVKY_URL", "https://script.google.com/macros/s/x/exec"), \
                mock.patch.object(config, "PRISPEVKY_FORMULAR",
                                  "https://docs.google.com/forms/d/e/x/viewform?embedded=true"):
            html = render._prispevek_stranka()
        self.assertIn('data-adresa="https://script.google.com/macros/s/x/exec"', html)
        # Bez JS skrytý, místo něj odkaz na Google Form bez parametru pro rám.
        self.assertRegex(html, r'<form class="prispevek"[^>]* hidden>')
        self.assertIn('<noscript><p class="zdroj">Formulář potřebuje JavaScript', html)
        self.assertIn('href="https://docs.google.com/forms/d/e/x/viewform"', html)
        self.assertNotIn("<iframe", html)
        for nazev in ("jmeno", "email", "nadpis", "text", "odkaz", "souhlas", "web"):
            self.assertIn('name="{0}"'.format(nazev), html, nazev)
        with mock.patch.object(config, "PRISPEVKY_URL", ""):
            self.assertNotIn("<form", render._prispevek_stranka())

    def test_souhlas_sedi_se_skriptem(self):
        # Do tabulky jde text z Google Formu; čtenář musí odsouhlasit tentýž.
        skript = (config.ROOT / "apps-script" / "prispevky.gs").read_text(encoding="utf-8")
        import re
        kusy = re.search(r"var SOUHLAS = (.*?);\n", skript, re.S).group(1)
        text = "".join(re.findall(r"'([^']*)'", kusy))
        self.assertEqual(text, render.PRISPEVEK_SOUHLAS)

    def test_app_js_odesila_a_meri(self):
        app = (config.STATIC / "app.js").read_text(encoding="utf-8")
        self.assertIn("'prispevek_odeslani'", app)
        self.assertIn("text/plain", app)
        self.assertIn("form.prispevek", app)

    def test_mereni_zna_mista(self):
        app = (config.STATIC / "app.js").read_text(encoding="utf-8")
        sablona = inspect.getsource(render)
        self.assertIn("'prispevek_klik'", app)
        for trida in ("vyzva-uvod", "vyzva-clanek", "vyzva-o-webu"):
            self.assertIn("'." + trida + "'", app, trida)
            self.assertIn(trida, sablona, trida)


if __name__ == "__main__":
    unittest.main()
