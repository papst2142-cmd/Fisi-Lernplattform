#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer die Auswertung ab 0.56: Richtig und falsch pro Tag (aus der
Spalte correct der vorhandenen Ereignisse), die Ergebnisse im
Pruefungstrainer (ohne Platzhalterpunkt) und die Klappbereiche der
Optionen (PC und Handy). Die Datenbank liegt in einem Temp-Ordner.

Start:  python test_auswertung.py   (Klappbereich am PC braucht ein Display)
"""

import datetime
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fisi_lernen as fl  # noqa: E402
from fisi_core import DBManager  # noqa: E402

TABLES = ("card_events", "quiz_answers", "scenario_events", "project_events",
          "ap1_events", "trainer_aufgaben")


class TageswerteTest(unittest.TestCase):
    """DBManager.activity_split_days und die Hilfen in fisi_lernen."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = DBManager(os.path.join(self.tmp, "test.db"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _set_day(self, day):
        """Alle bisherigen Ereignisse auf den Tag day legen."""
        conn = sqlite3.connect(self.db.db_path)
        try:
            for table in TABLES:
                conn.execute("UPDATE %s SET timestamp = ? || substr(timestamp, 11)"
                             % table, (day,))
            conn.commit()
        finally:
            conn.close()

    def test_leere_datenbank(self):
        self.assertEqual(self.db.activity_split_days(), {})

    def test_alle_quellen_getrennt_nach_bewertung(self):
        db = self.db
        db.log_card("netzwerk", "F1", "karte", True)
        db.log_card("netzwerk", "F2", "karte", False)
        db.log_card("netzwerk", "F3", "karte", None)        # ohne Bewertung: zaehlt nicht
        db.log_quiz_answer("netzwerk", "Q1", True)
        db.log_quiz_answer("netzwerk", "Q2", False)
        db.log_scenario(1, "S", "routing", True)
        db.log_scenario(2, "S", "routing")                  # nur angesehen
        db.log_project(1, "P", "x", False)
        db.log_ap1(1, "A", "hardware", True)
        db.log_trainer("subnetz", 1, True)
        db.log_trainer("subnetz", 1, False)
        split = db.activity_split_days()
        self.assertEqual(len(split), 1)
        (day, (right, wrong)), = split.items()
        self.assertEqual((right, wrong), (5, 4))
        # Summe stimmt mit dem Tageszaehler (Tagesziel) ueberein
        self.assertEqual(db.activity_days()[day], right + wrong)

    def test_mehrere_tage(self):
        self.db.log_quiz_answer("x", "a", True)
        self._set_day("2026-10-01")
        self.db.log_quiz_answer("x", "b", False)
        self.db.log_quiz_answer("x", "c", False)
        conn = sqlite3.connect(self.db.db_path)
        conn.execute("UPDATE quiz_answers SET timestamp = '2026-10-03' || substr(timestamp, 11)"
                     " WHERE question != 'a'")
        conn.commit()
        conn.close()
        self.assertEqual(self.db.activity_split_days(),
                         {"2026-10-01": (1, 0), "2026-10-03": (0, 2)})

    def test_reihe_luecken_und_prozent(self):
        today = datetime.date(2026, 10, 5)
        split = {"2026-10-05": (3, 1), "2026-10-03": (0, 2)}
        series = fl.daily_split_series(split, 7, today=today)
        self.assertEqual(len(series), 7)
        self.assertEqual(series[0][0], datetime.date(2026, 9, 29))
        self.assertEqual(series[-1], (today, 3, 1))
        self.assertEqual(series[-3], (datetime.date(2026, 10, 3), 0, 2))
        self.assertEqual(series[1][1:], (0, 0))            # Tag ohne Daten bleibt 0/0
        self.assertEqual(fl.split_percent(3, 1), (75, 25))
        self.assertEqual(fl.split_percent(0, 2), (0, 100))
        self.assertEqual(fl.split_percent(0, 0), (None, None))
        self.assertEqual(fl.split_percent(2, 1), (67, 33))  # Summe immer 100
        self.assertEqual(fl.split_summary(series), "7 Tage: 50 % richtig, 50 % falsch (3 von 6)")
        empty = fl.daily_split_series({}, 7, today=today)
        self.assertEqual(fl.split_summary(empty), "7 Tage: noch keine bewerteten Aufgaben")


class ErgebnisseTest(unittest.TestCase):
    """Ergebnisse im Pruefungstrainer: echte Sessions, kein Platzhalter."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = DBManager(os.path.join(self.tmp, "test.db"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_ohne_session_keine_werte(self):
        self.assertEqual(fl.result_series(self.db.get_all_results()), ([], []))

    def test_session_mit_datum_und_prozent(self):
        self.db.save_test_result(8, 10, 80.0, "", 60)
        self.db.save_test_result(5, 10, 50.0, "", 60)
        labels, values = fl.result_series(self.db.get_all_results())
        today = datetime.date.today()
        self.assertEqual(labels, [today.strftime("%d.%m.")] * 2)
        self.assertEqual(values, [80.0, 50.0])             # aelteste zuerst

    def test_hoechstens_20_sessions(self):
        rows = [("2026-10-%02dT10:00:00" % (i % 28 + 1), 1, 1, float(i)) for i in range(25)]
        labels, values = fl.result_series(rows)
        self.assertEqual(len(labels), 20)
        self.assertEqual(values[-1], 0.0)

    def test_texte_vorhanden(self):
        self.assertIn("abgeschlossene", fl.RESULT_CHART_SUBTITLE)
        self.assertIn("Prüfungstrainer", fl.RESULT_CHART_EMPTY)
        self.assertNotIn("Session", fl.RESULT_CHART_TITLE)


class KurveTest(unittest.TestCase):
    """Ab 0.56: Die Kurve in "Aufgaben pro Tag" (und allen Liniendiagrammen)
    schwingt nie unter 0 und nie ueber die Datenpunkte hinaus."""

    @staticmethod
    def _bezier(p1, c1, c2, p2, t):
        u = 1 - t
        return tuple(u ** 3 * a + 3 * u * u * t * b + 3 * u * t * t * c + t ** 3 * d
                     for a, b, c, d in zip(p1, c1, c2, p2))

    def test_kein_ueberschwingen(self):
        import random
        import fisi_theme
        rng = random.Random(56)
        cases = [[0, 0, 20, 0, 0], [0, 35, 0, 0, 3, 40, 40, 2], [5, 5, 5],
                 [0, 1, 0, 1, 0], [60, 0, 0, 0, 60]]
        cases += [[rng.choice([0, 0, rng.randint(0, 80)]) for _ in range(rng.randint(2, 30))]
                  for _ in range(200)]
        for values in cases:
            # Bildschirmkoordinaten: y waechst nach unten, Nulllinie bei 200
            points = [(10 + 25 * index, 200 - 2 * value) for index, value in enumerate(values)]
            controls = fisi_theme.curve_controls(points)
            self.assertEqual(len(controls), len(points) - 1)
            for (p1, p2), (c1, c2) in zip(zip(points, points[1:]), controls):
                low, high = min(p1[1], p2[1]), max(p1[1], p2[1])
                for step in range(21):
                    x, y = self._bezier(p1, c1, c2, p2, step / 20.0)
                    self.assertTrue(low - 1e-9 <= y <= high + 1e-9, (values, p1, p2, y))
                    self.assertTrue(p1[0] - 1e-9 <= x <= p2[0] + 1e-9)

    def test_pc_kurve_laeuft_durch_die_punkte(self):
        try:
            import fisi_widgets
        except Exception as error:   # ohne customtkinter
            self.skipTest(str(error))
        points = [(0, 200), (30, 100), (60, 200), (90, 200)]
        curve = fisi_widgets._smooth_curve(points, 200, 0)
        for point in points:
            self.assertIn(point, [(round(x, 6), round(y, 6)) for x, y in curve])
        self.assertTrue(all(100 <= y <= 200 for _x, y in curve))


class HistorieOrtTest(unittest.TestCase):
    """Ab 0.56: "Historie loeschen" steht in den Optionen unter "Loeschen und
    zuruecksetzen" (PC und Handy), im Fortschritt nicht mehr."""

    def _class_source(self, path, name):
        import ast
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
        for node in ast.parse(source).body:
            if isinstance(node, ast.ClassDef) and node.name == name:
                return ast.get_source_segment(source, node)
        self.fail("%s fehlt in %s" % (name, path))

    def test_pc_und_handy(self):
        here = os.path.dirname(os.path.abspath(__file__))
        for path, progress, settings in (
                (os.path.join(here, "app_gui.py"), "ProgressView", "SettingsView"),
                (os.path.join(here, "mobile", "src", "main.py"), "ProgressScreen",
                 "SettingsScreen")):
            old = self._class_source(path, progress)
            new = self._class_source(path, settings)
            self.assertNotIn("clear_history", old, path)
            self.assertNotIn("Historie löschen", old, path)
            self.assertIn("HISTORY_BUTTON, self.clear_history", new, path)
            self.assertIn("self.db.clear_history()", new, path)
            # Abfrage unveraendert
            self.assertIn("Wirklich alle gespeicherten Testergebnisse und", new, path)
        self.assertEqual(fl.HISTORY_BUTTON, "Historie löschen")
        self.assertIn("Historie", fl.DELETE_SUBTITLE)


def _tk_ok():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:
        return False


@unittest.skipUnless(_tk_ok(), "kein Display fuer Tk")
class KlappbereichPcTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import customtkinter as ctk
        from fisi_widgets import FoldCard, setup_fonts
        cls.FoldCard = FoldCard
        cls.root = ctk.CTk()
        setup_fonts(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def setUp(self):
        self.FoldCard._open_state.clear()

    def test_standard_zu_und_umschalten(self):
        card = self.FoldCard(self.root, fl.DELETE_TITLE, fl.DELETE_SUBTITLE, key="t_loeschen")
        card.pack()
        self.root.update()
        self.assertFalse(card.opened)
        self.assertFalse(card.body.winfo_ismapped())
        self.assertIn(fl.FOLD_OPEN, card.arrow.cget("text"))
        card.toggle()
        self.root.update()
        self.assertTrue(card.body.winfo_ismapped())
        self.assertIn(fl.FOLD_CLOSE, card.arrow.cget("text"))
        # Tastatur: Kopf nimmt den Fokus, Eingabetaste klappt wieder zu
        card.head.focus_force()
        self.root.update()
        self.assertEqual(self.root.focus_get(), card.head)
        card.head.event_generate("<Return>")
        self.root.update()
        self.assertFalse(card.opened)

    def test_abstaende_bei_skalierung_nicht_doppelt(self):
        """Windows-Skalierung ueber 100 %: erneutes Aufklappen behaelt die
        Abstaende (vorher wurden sie ein zweites Mal skaliert)."""
        import customtkinter as ctk
        ctk.set_widget_scaling(1.5)
        try:
            card = self.FoldCard(self.root, "Skalierung", key="t_skalierung")
            card.pack()
            self.root.update()
            closed = str(card.head.pack_info()["pady"])
            card.toggle()
            self.root.update()
            body = card.body.pack_info()
            first = (str(body["padx"]), str(body["pady"]), str(card.head.pack_info()["pady"]))
            self.assertEqual(str(body["padx"]), str(round(card.pad * 1.5)))
            for _round in range(2):
                card.toggle()
                self.root.update()
                self.assertEqual(str(card.head.pack_info()["pady"]), closed)
                card.toggle()
                self.root.update()
            body = card.body.pack_info()
            again = (str(body["padx"]), str(body["pady"]), str(card.head.pack_info()["pady"]))
            self.assertEqual(again, first)
            card.destroy()
        finally:
            ctk.set_widget_scaling(1.0)

    def test_zustand_bleibt_beim_neuaufbau(self):
        card = self.FoldCard(self.root, "Farben", key="t_farben")
        card.toggle()
        card.destroy()
        again = self.FoldCard(self.root, "Farben", key="t_farben")
        self.assertTrue(again.opened)


class KlappbereichHandyTest(unittest.TestCase):

    def setUp(self):
        here = os.path.dirname(os.path.abspath(__file__))
        src = os.path.join(here, "mobile", "src")
        try:
            import flet  # noqa: F401
        except ImportError:
            self.skipTest("flet nicht installiert")
        if not os.path.exists(os.path.join(src, "fisi_lernen.py")):
            self.skipTest("mobile/vorbereiten.py noch nicht gelaufen")
        sys.path.insert(0, src)
        import ui
        self.ui = ui

    def test_standard_zu_und_umschalten(self):
        import flet as ft
        card = self.ui.FoldCard(fl.DELETE_TITLE, [ft.Text("x")], key="h_loeschen",
                                open_text=fl.FOLD_OPEN, close_text=fl.FOLD_CLOSE)
        self.assertFalse(card.body.visible)
        card.toggle()
        self.assertTrue(card.body.visible)
        self.assertEqual(card.header_semantics.label, "%s, %s" % (fl.DELETE_TITLE, fl.FOLD_CLOSE))
        self.assertTrue(card.header_semantics.expanded)
        card.toggle()
        self.assertFalse(card.body.visible)


if __name__ == "__main__":
    unittest.main(verbosity=1)
