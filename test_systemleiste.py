#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ab 0.62.1 (Teil A): Abstand zur Android-Systemleiste am Handy.

Jede Ansicht der Handy-App (Reiter und alle Unterseiten) haengt ihren Inhalt
in eine SafeArea. Flutter gibt der SafeArea die echte Hoehe der Bedienleiste
des Geraets (3 Tasten oder Gesten, im Querformat auch seitlich). Fehlt die
Huelle, reicht der Inhalt unter die Leiste (Fehler bis 0.62).

Der Test prueft den Aufbau, nicht die Pixel: Die Android-Leiste gibt es im
Container und in der CI nicht.
"""
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("FISI_DB_PATH", os.path.join(tempfile.mkdtemp(), "leiste.db"))


def _flet_ok():
    try:
        import flet  # noqa: F401
        return True
    except ImportError:
        return False


@unittest.skipUnless(_flet_ok(), "flet fehlt")
class SystemleisteTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import flet as ft
        sys.path.insert(1, os.path.join(HERE, "mobile", "src"))
        import main
        cls.ft, cls.main = ft, main

        class FakePage:
            def __init__(self):
                self.views, self.overlay, self.tasks = [], [], []

            def run_task(self, handler, *args, **kwargs):
                self.tasks.append(handler)

            def __getattr__(self, _name):
                return lambda *args, **kwargs: None

        cls.page = FakePage()
        cls.app = main.FISIMobileApp(cls.page)

    def assert_safe(self, view, name):
        ft = self.ft
        self.assertEqual(len(view.controls), 1, name)
        hull = view.controls[0]
        self.assertTrue(isinstance(hull, ft.SafeArea), "%s: Inhalt ohne SafeArea" % name)
        # Ohne expand bekommt die Liste keine feste Hoehe und scrollt nicht
        # mehr (Flet: Expanded nur fuer direkte Kinder der Ansicht)
        self.assertTrue(hull.expand, "%s: SafeArea ohne expand" % name)
        self.assertTrue(hull.avoid_intrusions_bottom, name)
        self.assertTrue(hull.avoid_intrusions_left and hull.avoid_intrusions_right, name)
        # Bei offener Tastatur kein doppelter Abstand
        self.assertFalse(hull.maintain_bottom_view_padding, name)

    def test_reiter(self):
        for key, *_rest in self.main.NAV:
            self.app.show_tab(key)
            self.assertEqual(len(self.page.views), 1)
            self.assert_safe(self.page.views[0], "Reiter " + key)

    def test_unterseiten(self):
        tabs = [item[0] for item in self.main.NAV]
        keys = [k for k in self.main.SCREEN_CLASSES if k not in tabs]
        self.assertGreaterEqual(len(keys), 9)
        for key in keys:
            self.app.show_tab("dashboard")
            self.app.open(key)
            self.assertEqual(len(self.page.views), 2, key)
            self.assert_safe(self.page.views[-1], "Unterseite " + key)

    def test_lizenz_und_fremdbestandteile(self):
        settings = self.app.screens["settings"]
        for name in ("show_license", "show_notices"):
            self.app.show_tab("settings")
            getattr(settings, name)()
            self.assert_safe(self.page.views[-1], name)

    def test_spiel_reise(self):
        # Spiel > Reise (Nicos Fund zu 0.62.1): Unterseite des Spiels ueber push()
        self.app.show_tab("game")
        game = self.app.screens["game"]
        if game.game.state.profile is None:
            game.game.set_profile("Test", {})   # nur in der Test-Datenbank
        for tab in ("rueckblick", "erfolge"):
            self.app.show_tab("game")
            game.open_journey(tab=tab)
            self.assertEqual(len(self.page.views), 2, tab)
            self.assert_safe(self.page.views[-1], "Spiel Reise " + tab)

    def test_hilfe_erkennt_offene_seite(self):
        # open_help/scroll_top finden den Inhalt trotz Huelle
        self.app.show_tab("dashboard")
        self.app.open_help()
        self.assertIs(self.main.view_content(self.page.views[-1]),
                      self.app.screens["help"].root)
        before = len(self.page.views)
        self.app.open_help("rechtliches")
        self.assertEqual(len(self.page.views), before)

    def test_nach_oben_scrollen_findet_liste(self):
        # scroll_top sucht die Liste der obersten Ansicht (durch die Huelle)
        self.app.show_tab("dashboard")
        self.app.open("quiz")
        before = len(self.page.tasks)
        self.app.scroll_top()
        self.assertEqual(len(self.page.tasks), before + 1)


if __name__ == "__main__":
    unittest.main()
