# -*- coding: utf-8 -*-
"""Fronta a text příspěvků na Facebook. Síť se nevolá, odeslání je podvržené.

Spuštění: python -m unittest discover -s tests
"""

import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kromka import config, facebook, store  # noqa: E402

TED = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)


def _clanek(cislo):
    return {
        "id": "mesto-kromeriz:{0:016x}".format(cislo),
        "slug": "potkani-jsou-cooked-{0}".format(cislo),
        "headline": "Potkani jsou cooked",
        "tldr": [
            {"emoji": "📅🐀", "label": "Bait Dates", "text": "Návnady se kladou 19. října."},
            {"emoji": "💸🐀", "label": "Price Tag", "text": "Akce vyjde na 232 tisíc korun."},
        ],
    }


class Fronta(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._puvodni = (config.DATA, config.ARTICLES, config.SITE_URL)
        config.DATA = Path(self._tmp.name)
        config.ARTICLES = config.DATA / "articles"
        config.SITE_URL = "https://kromcl.cz"
        self.odeslane = []

    def tearDown(self):
        config.DATA, config.ARTICLES, config.SITE_URL = self._puvodni
        self._tmp.cleanup()

    def _posli(self, clanek):
        self.odeslane.append(clanek["slug"])
        return "123_{0}".format(len(self.odeslane))

    def _uloz(self, *cisla):
        clanky = [_clanek(c) for c in cisla]
        for c in clanky:
            store.uloz(c)
        return clanky

    def test_odkaz_ma_utm_se_slugem_v_kampani(self):
        self.assertEqual(
            facebook.odkaz(_clanek(1)),
            "https://kromcl.cz/clanek/potkani-jsou-cooked-1.html"
            "?utm_source=facebook&utm_medium=social"
            "&utm_campaign=potkani-jsou-cooked-1&utm_content=autopost")

    def test_text_je_tldr_bez_titulku(self):
        self.assertEqual(
            facebook.text(_clanek(1)),
            "📅🐀 Bait Dates: Návnady se kladou 19. října.\n\n"
            "💸🐀 Price Tag: Akce vyjde na 232 tisíc korun.")

    def test_bez_tldr_aspon_titulek(self):
        clanek = dict(_clanek(1), tldr=[])
        self.assertEqual(facebook.text(clanek), "Potkani jsou cooked")

    def test_zarazeny_clanek_se_nezaradi_dvakrat(self):
        clanky = self._uloz(1)
        self.assertEqual(facebook.zarad(clanky, ted=TED), 1)
        self.assertEqual(facebook.zarad(clanky, ted=TED), 0)
        self.assertEqual(len(facebook.nacti()["fronta"]), 1)

    def test_odeslany_clanek_uz_nikdy_neodejde(self):
        clanky = self._uloz(1)
        facebook.zarad(clanky, ted=TED)
        facebook.odesli(ted=TED, posli=self._posli)
        self.assertEqual(facebook.zarad(clanky, ted=TED), 0)
        facebook.odesli(ted=TED, posli=self._posli)
        self.assertEqual(self.odeslane, ["potkani-jsou-cooked-1"])
        self.assertEqual(facebook.nacti()["odeslane"][clanky[0]["id"]]["post"], "123_1")

    def test_za_beh_odejde_jen_jeden_nejstarsi(self):
        facebook.zarad(self._uloz(1, 2, 3), ted=TED)
        facebook.odesli(ted=TED, posli=self._posli)
        self.assertEqual(self.odeslane, ["potkani-jsou-cooked-1"])
        self.assertEqual(len(facebook.nacti()["fronta"]), 2)
        facebook.odesli(ted=TED + timedelta(hours=1), posli=self._posli)
        self.assertEqual(self.odeslane, ["potkani-jsou-cooked-1", "potkani-jsou-cooked-2"])

    def test_neuspech_zustane_ve_fronte(self):
        facebook.zarad(self._uloz(1), ted=TED)

        def spadni(clanek):
            raise RuntimeError("HTTP 500: výpadek")

        zpravy = facebook.odesli(ted=TED, posli=spadni)
        self.assertIn("zkusí se příště", zpravy[0])
        self.assertEqual(len(facebook.nacti()["fronta"]), 1)
        facebook.odesli(ted=TED + timedelta(hours=1), posli=self._posli)
        self.assertEqual(self.odeslane, ["potkani-jsou-cooked-1"])

    def test_po_24_hodinach_se_zahodi(self):
        facebook.zarad(self._uloz(1), ted=TED)
        zpravy = facebook.odesli(ted=TED + timedelta(hours=25), posli=self._posli)
        self.assertEqual(self.odeslane, [])
        self.assertIn("Zahozeno", zpravy[0])
        self.assertEqual(facebook.nacti()["fronta"], [])

    def test_smazany_clanek_se_vyradi(self):
        facebook.zarad([_clanek(1)], ted=TED)   # do fronty, ale ne do archivu
        facebook.odesli(ted=TED, posli=self._posli)
        self.assertEqual(self.odeslane, [])
        self.assertEqual(facebook.nacti()["fronta"], [])

    def test_bez_tokenu_je_vypnuto(self):
        puvodni = (config.FB_PAGE_ID, config.FB_TOKEN)
        try:
            config.FB_PAGE_ID, config.FB_TOKEN = "123", ""
            self.assertFalse(facebook.zapnuto())
        finally:
            config.FB_PAGE_ID, config.FB_TOKEN = puvodni


if __name__ == "__main__":
    unittest.main()
