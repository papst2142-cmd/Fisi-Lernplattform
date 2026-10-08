# -*- coding: utf-8 -*-
"""Tests ab 0.60 (K-A, K-B, K-C, K-G): Dashboard, Lernserie, Versionszeile, Hilfe.

  * K-A: die Lernserie steht nur noch im Banner (PC und Handy), der Schalter
    "Lernserie anzeigen" wirkt dort; Fortschritt hat drei Kacheln
  * K-B: eindeutige Beschriftungen, am PC und Handy dieselben Texte; der Ring
    "Pruefungstrainer" zeigt gross die verschiedenen Fragen
  * K-C: Versionszeile am Handy nur auf der Startseite
  * K-G: Hilfe oeffnet eingeklappt, "Hilfe" und "Suchen" in der Handy-Kopfzeile

Aufruf:  python test_dashboard.py   (PC-Teil braucht eine Anzeige, z.B. xvfb-run)
"""
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)
_TMP = tempfile.mkdtemp(prefix="fisi_dashboard_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "dashboard.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(_TMP, "selbsttest.log"))
os.environ["HOME"] = _TMP
os.environ["APPDATA"] = _TMP

import fisi_core as fc  # noqa: E402
import fisi_lernen as fl  # noqa: E402

PC_SOURCE = open(os.path.join(HERE, "app_gui.py"), encoding="utf-8").read()
MOBILE_SOURCE = open(os.path.join(HERE, "mobile", "src", "main.py"), encoding="utf-8").read()
DASH_NAMES = sorted(name for name in dir(fl) if name.startswith("DASH_"))


def _fill_db():
    """Beispieldaten: 30 Karten, 20 verschiedene Fragen mit 50 Antworten."""
    db = fc.DBManager()
    for card in fc.KARTEIKARTEN[:30]:
        db.log_card(card["cat"], card["q"], "lernen", True)
    questions = fc.QUIZ_QUESTIONS[:20]
    for index in range(50):
        question = questions[index % 20]
        db.log_quiz_answer(question["cat"], question["q"], index % 2 == 0)
    return db


def _flet_texts(control, found):
    for attr in ("value", "text", "label", "tooltip"):
        value = getattr(control, attr, None)
        if isinstance(value, str) and value.strip():
            found.append(value)
    for attr in ("content", "title"):
        value = getattr(control, attr, None)
        if value is not None and hasattr(value, "__dict__"):
            _flet_texts(value, found)
    for attr in ("controls", "spans"):
        for child in getattr(control, attr, None) or []:
            _flet_texts(child, found)
    return found


class TexteTest(unittest.TestCase):
    """K-B: dieselben Texte am PC und Handy, keine alten Bezeichnungen mehr."""

    def test_beide_oberflaechen_nutzen_alle_dashboard_texte(self):
        self.assertGreaterEqual(len(DASH_NAMES), 10)
        for name in DASH_NAMES:
            self.assertTrue(re.search(r"\b%s\b" % name, PC_SOURCE), "PC: " + name)
            if name != "DASH_SIDEBAR_BAR":     # die Seitenleiste gibt es nur am PC
                self.assertTrue(re.search(r"\b%s\b" % name, MOBILE_SOURCE), "Handy: " + name)

    def test_abgesprochene_texte(self):
        self.assertEqual(fl.DASH_RING_QUIZ, "Prüfungstrainer")
        self.assertEqual(fl.DASH_QUIZ_SUB % 2174, "von 2174 Fragen beantwortet")
        self.assertEqual(fl.DASH_CARDS_SUB % 1565, "von 1565 Karten bearbeitet")
        self.assertEqual(fl.LEARN_CHART_SERIES, "Lernaktivitäten pro Tag")
        self.assertEqual(fc.KIND_QUIZ, "Prüfungsfrage")
        self.assertEqual(fl.dash_quote_text(3, 4), "3 von 4 Antworten richtig")

    def test_keine_alten_bezeichnungen(self):
        old = ["Quizfragen", "Quiz gesamt", "Quiz-Erfolgsquote", "Inhalte bearbeitet",
               "Inhalten bearbeitet", "Fragen richtig beantwortet"]
        for source, where in ((PC_SOURCE, "PC"), (MOBILE_SOURCE, "Handy")):
            code = "\n".join(line.split("#")[0] for line in source.splitlines())
            strings = re.findall(r'"([^"\n]*)"', code)
            for text in old:
                hits = [s for s in strings if text.strip('"') in s]
                self.assertEqual(hits, [], "%s: %s" % (where, text))

    def test_fortschritt_kacheln_gleich_benannt(self):
        for title in ("Test-Sessions", "Durchschnitt", "Bestes Ergebnis"):
            self.assertIn('"%s"' % title, PC_SOURCE)
            self.assertIn('"%s"' % title, MOBILE_SOURCE)


class HandyTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import flet as ft
        sys.path.insert(1, os.path.join(HERE, "mobile", "src"))
        import main
        import ui
        cls.ft, cls.main, cls.ui = ft, main, ui

        class FakePage:
            views = []

            def __getattr__(self, _name):
                return lambda *args, **kwargs: None

        class FakeApp(main.FISIMobileApp):
            def __init__(self):
                self.page = FakePage()
                self.body = ft.Container()
                self.db = main.DBManager()
                self.sync = main.SyncController(self)
                self.perf = main.MobilePerf(self)
                self.screens = {}
                self._recoloring = False

        cls.FakeApp = FakeApp
        _fill_db()

    def setUp(self):
        fl.save_learning_settings(serie_an=True, ziel_an=True)

    def dashboard_texts(self):
        app = self.FakeApp()
        screen = self.main.SCREEN_CLASSES["dashboard"](app)
        screen.on_show()
        return _flet_texts(screen.root, [])

    def test_ring_pruefungstrainer_zeigt_verschiedene_fragen(self):
        texts = self.dashboard_texts()
        index = texts.index(fl.DASH_RING_QUIZ.upper())
        self.assertIn("20", texts[index:index + 4])
        self.assertIn(fl.DASH_QUIZ_SUB % len(fc.QUIZ_QUESTIONS), texts)
        self.assertIn(fl.dash_quote_text(25, 50), texts)

    def test_lernserie_nur_im_banner(self):
        texts = self.dashboard_texts()
        streak = [text for text in texts if "Lernserie" in text]
        self.assertEqual(len(streak), 1, streak)
        self.assertTrue(streak[0].startswith("Lernserie: "))
        self.assertIn(fl.DASH_LEARNED % (50, len(fc.KARTEIKARTEN) + len(fc.QUIZ_QUESTIONS)),
                      streak[0])

    def test_schalter_lernserie_wirkt_am_banner(self):
        fl.save_learning_settings(serie_an=False)
        texts = self.dashboard_texts()
        self.assertFalse([text for text in texts if "Lernserie" in text])

    def test_fortschritt_zwei_oben_eine_unten(self):
        app = self.FakeApp()
        screen = self.main.SCREEN_CLASSES["progress"](app)
        rows = [control for control in screen.root.controls
                if isinstance(control, self.ft.Row)][:2]
        self.assertEqual([len(row.controls) for row in rows], [2, 1])
        self.assertEqual(sorted(screen.stats), ["avg", "best", "tests"])

    def test_versionszeile_nur_auf_der_startseite(self):
        pc_version = re.search(r'^APP_VERSION = "([^"]+)"', PC_SOURCE, re.M).group(1)
        self.assertEqual(self.main.VERSION_LINE % self.main.APP_VERSION,
                         "Version " + pc_version)
        app = self.FakeApp()
        app.lbl_version = self.ft.Text(self.main.VERSION_LINE % self.main.APP_VERSION)
        app.screens = {key: type("S", (), {"crumbs": ("A", "B"), "root": None,
                                           "on_show": lambda self: None,
                                           "reset_folds": lambda self: None})()
                       for key, _i, _j, _n in self.main.NAV}
        app.nav = type("N", (), {"selected_index": 0})()
        app.crumb_main = self.ft.Text("")
        app.crumb_sub = self.ft.Text("")
        app.close_toast = lambda: None
        for key, _i, _j, _n in self.main.NAV:
            app.show_tab(key)
            self.assertEqual(app.lbl_version.visible, key == "dashboard", key)

    def test_hilfe_oeffnet_eingeklappt(self):
        app = self.FakeApp()
        screen = self.main.SCREEN_CLASSES["help"](app)
        app.screens = {"help": screen}
        opened = []
        app.open = opened.append
        screen.folds["update"].toggle()
        screen.folds["schutzprogramm"].toggle()
        app.open_help()
        self.assertEqual(opened, ["help"])
        self.assertFalse(any(fold.opened for fold in screen.folds.values()))
        # Ueber die Suche: nur der gesuchte Abschnitt ist offen
        screen.folds["update"].toggle()
        app.open_help("schutzprogramm")
        self.assertEqual([key for key, fold in screen.folds.items() if fold.opened],
                         ["schutzprogramm"])

    def test_kopfzeile_hilfe_und_suchen_benannt(self):
        self.assertIn("named(fh.HELP_TITLE", MOBILE_SOURCE)
        self.assertIn("named(SEARCH_TEXT", MOBILE_SOURCE)
        control = self.main.named("Hilfe", self.ft.IconButton(icon=self.ft.Icons.HELP))
        self.assertEqual(control.content.label, "Hilfe")


def _display_available():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:
        return False


@unittest.skipUnless(_display_available(), "keine Anzeige (z.B. mit xvfb-run starten)")
class PcTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import app_gui
        app_gui.UpdateController.auto_check = lambda self: None
        app_gui.SyncController.auto_start = lambda self: None
        _fill_db()
        fl.save_learning_settings(serie_an=True, ziel_an=True)
        cls.gui = app_gui
        cls.root = app_gui.ctk.CTk()
        cls.app = app_gui.FISIApp(cls.root)
        cls.root.update()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def texts(self, widget, found=None):
        found = [] if found is None else found
        try:
            value = widget.cget("text")
            if isinstance(value, str) and value.strip():
                found.append(value)
        except Exception:
            pass
        if widget.winfo_class() == "Canvas":
            for item in widget.find_all():
                # Ringe brechen lange Unterzeilen um (ab 0.60) - Wortlaut gleich
                if widget.type(item) == "text" and widget.itemcget(item, "text").strip():
                    found.append(widget.itemcget(item, "text").replace("\n", " "))
        for child in widget.winfo_children():
            self.texts(child, found)
        return found

    def show(self, key):
        self.app.show_view(key)
        self.root.update()
        return self.app.views[key]

    def test_a_ring_und_lernserie(self):
        texts = self.texts(self.show("dashboard")) + self.texts(self.app.sidebar)
        streak = [text for text in texts if "Lernserie" in text]
        self.assertEqual(len(streak), 1, streak)
        self.assertIn(fl.DASH_QUIZ_SUB % len(fc.QUIZ_QUESTIONS), texts)
        self.assertIn("20", texts)
        self.assertIn(fl.DASH_SIDEBAR_BAR, texts)

    def test_b_drei_kacheln(self):
        view = self.show("progress")
        self.assertFalse(hasattr(view, "stat_streak"))
        for name in ("stat_tests", "stat_avg", "stat_best"):
            self.assertTrue(hasattr(view, name), name)

    def test_c_hilfe_oeffnet_eingeklappt(self):
        view = self.show("help")
        view.folds["update"].toggle()
        self.show("dashboard")
        self.show("help")
        self.assertFalse(any(fold.opened for fold in view.folds.values()))
        self.app.open_help("schutzprogramm")
        self.root.update()
        self.assertEqual([key for key, fold in view.folds.items() if fold.opened],
                         ["schutzprogramm"])

    def test_d_schalter_lernserie(self):
        fl.save_learning_settings(serie_an=False)
        try:
            self.show("settings")
            view = self.show("dashboard")
            view.on_show() if hasattr(view, "on_show") else None
            self.root.update()
            texts = self.texts(view)
            self.assertFalse([text for text in texts if "Lernserie" in text])
        finally:
            fl.save_learning_settings(serie_an=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
