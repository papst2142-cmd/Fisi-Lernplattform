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
