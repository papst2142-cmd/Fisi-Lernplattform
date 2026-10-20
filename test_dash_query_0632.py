# -*- coding: utf-8 -*-
"""Tests 0.63.2, FG-115 (Weisung zu Meldung 45, Frage 6): Dashboard nach
Umbenennen an Ort und Stelle.

apply_question_renames (fisi_core) schreibt alte Fragetexte im Lernstand an
Ort und Stelle auf die neuen um - beim Start eines zweiten Programms und im
Abgleich. Anzahl und hoechste Nummer der Tabellen bleiben dabei gleich. Das
Dashboard merkt sich seine Abfragen ueber genau diesen Stempel: beim
Seitenwechsel seit 0.50 (on_show, _refresh_key), bei refresh() seit N7
(_dash_query). Ohne FG-115 zeigt es danach den alten Wert, bis sich eine
Antworttabelle aendert, das Datum wechselt oder neu gestartet wird.

  * a Seitenwechsel nach dem Umbenennen (zweites Programm, eigener Prozess)
  * b explizites refresh() nach dem Umbenennen, auch zweimal hintereinander
  * c neue Zeile nach dem Umbenennen; danach wieder schrittweise
  * d ohne alte Fragetexte: Zwischenspeicher und Seitenwechsel wie bisher
    (keine Mehrarbeit im Normalfall)
  * e Zaehler "Karteikarten" (COUNT DISTINCT question) nach dem Umbenennen

Wahrheit ist jeweils die Abfrage direkt auf der Datenbank (ReviewPlan.from_db,
distinct_cards_learned). Kein skip: Fehlt die Anzeige, endet die Klasse mit
ERROR.
Aufruf:  xvfb-run -a python test_dash_query_0632.py
"""
import datetime
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)
_TMP = tempfile.mkdtemp(prefix="fisi_fg115_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "fg115.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(_TMP, "selbsttest.log"))
os.environ["HOME"] = _TMP
os.environ["APPDATA"] = _TMP
os.environ["FISI_VORLADEN"] = "0"

import fisi_core as fc  # noqa: E402
import fisi_lernen as fl  # noqa: E402

VALID_CARDS = {card["q"] for card in fc.KARTEIKARTEN}
# (alter Text, neuer Text) der Karteikarten, deren neuer Text gilt und deren
# alter nicht (inhalte/umbenennungen.json)
CARD_RENAMES = [(old, new) for old, new in fc.QUESTION_RENAMES["card_events"].items()
                if new in VALID_CARDS and old not in VALID_CARDS]
YESTERDAY = (datetime.date.today() - datetime.timedelta(days=1)).isoformat() + " 10:00:00"


def insert_cards(path, questions, correct=0):
    """Wie ein aelteres Programm: Zeilen direkt in den Lernstand."""
    conn = sqlite3.connect(path)
    for question in questions:
        conn.execute("INSERT INTO card_events (uid, timestamp, category, question, mode,"
                     " correct) VALUES (?, ?, ?, ?, ?, ?)",
                     (uuid.uuid4().hex, YESTERDAY, "x", question, "lernen", correct))
    conn.commit()
    conn.close()


def rename_in_place(path):
    """Wie der Abgleich: apply_question_renames ueber eine eigene Verbindung."""
    conn = sqlite3.connect(path)
    fc.apply_question_renames(conn.cursor())
    conn.commit()
    conn.close()


def second_program(path):
    """Wie ein zweites Programm: eigener Prozess, DBManager -> _migrate."""
    subprocess.run([sys.executable, "-I", "-c",
                    "import sys; sys.path.insert(0, sys.argv[1]); import fisi_core as fc;"
                    " fc.DBManager(sys.argv[2])", HERE, path],
                   check=True, env=dict(os.environ))


def stamp(path):
    conn = sqlite3.connect(path)
    try:
        return conn.execute("SELECT COUNT(*), MAX(rowid) FROM card_events").fetchone()
    finally:
        conn.close()


class DashQueryTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import app_gui
        app_gui.UpdateController.auto_check = lambda self: None
        app_gui.SyncController.auto_start = lambda self: None
        app_gui.show_badge_toast = lambda *a, **k: None
        cls.root = app_gui.ctk.CTk()
        cls.errors = []
        cls.root.report_callback_exception = lambda *exc: cls.errors.append(exc)
        cls.root.geometry("1360x900+0+0")
        cls.app = app_gui.FISIApp(cls.root)
        cls.app.show_view("dashboard")
        cls.root.update()
        cls.view = cls.app.views["dashboard"]
        cls.home_db = cls.view.db

    @classmethod
    def tearDownClass(cls):
        try:
            tk_ = cls.root.tk
            for job in tk_.splitlist(tk_.call("after", "info")):
                tk_.call("after", "cancel", job)
            cls.root.destroy()
        except Exception:  # noqa: BLE001
            pass

    def setUp(self):
        self.assertGreaterEqual(len(CARD_RENAMES), 8)
        self.dir = tempfile.mkdtemp(prefix="db_", dir=_TMP)
        self.path = os.path.join(self.dir, "t.db")
        self.db = fc.DBManager(self.path)
        view = self.view
        # Eigene Datenbank je Test; Merkzustand des Dashboards zuruecksetzen,
        # damit kein Stempel einer anderen Datenbank zufaellig passt
        view.db = self.db
        view._dash_cache = {}
        view._review_index = None
        view._refreshed = None
        self.app.show_view("dashboard")
        self.root.update()

    def tearDown(self):
        self.view.db = self.home_db
        self.view._dash_cache = {}
        self.view._review_index = None
        self.view._refreshed = None
        shutil.rmtree(self.dir, ignore_errors=True)
        self.assertEqual(self.errors, [])

    # -- Hilfen ---------------------------------------------------------------

    def switch(self):
        """Seitenwechsel: weg vom Dashboard und zurueck (on_show)."""
        self.app.show_view("cards")
        self.root.update()
        self.app.show_view("dashboard")
        self.root.update()

    def shown(self):
        self.root.update_idletasks()
        return self.view.lbl_due.cget("text")

    def truth(self):
        return fl.due_text(fl.ReviewPlan.from_db(self.db))

    def assertDue(self, expected_count, msg):
        self.assertEqual(self.shown(), self.truth(), msg)
        self.assertEqual(fl.ReviewPlan.from_db(self.db).count(fl.SRC_CARD), expected_count, msg)

    def prepare_old_texts(self):
        """3 neue Texte gestern falsch (heute faellig); danach schreibt ein
        aelteres Programm 5 alte Texte (gelten erst nach dem Umbenennen)."""
        insert_cards(self.path, [new for _old, new in CARD_RENAMES[:3]])
        self.view.refresh()
        self.assertDue(3, "Start")
        insert_cards(self.path, [old for old, _new in CARD_RENAMES[3:8]])

    # -- Tests ----------------------------------------------------------------

    def test_a_seitenwechsel_nach_umbenennen(self):
        """Seit 0.50 falsch (3 statt 8): on_show verglich nur den Stempel."""
        self.prepare_old_texts()
        self.switch()
        self.assertDue(3, "nach dem aelteren Programm, Seitenwechsel")
        before = stamp(self.path)
        second_program(self.path)
        self.assertEqual(stamp(self.path), before)      # Stempel gleich (Ursache)
        self.switch()
        self.assertDue(8, "nach dem Umbenennen, Seitenwechsel")
        self.switch()
        self.assertDue(8, "nach dem Umbenennen, zweiter Seitenwechsel")

    def test_b_refresh_nach_umbenennen(self):
        """Seit N7 falsch: refresh() nahm "faellig" aus dem Zwischenspeicher."""
        self.prepare_old_texts()
        self.view.refresh()
        self.assertDue(3, "nach dem aelteren Programm, refresh")
        before = stamp(self.path)
        rename_in_place(self.path)
        self.assertEqual(stamp(self.path), before)
        self.view.refresh()
        self.assertDue(8, "nach dem Umbenennen, refresh")
        self.view.refresh()
        self.assertDue(8, "nach dem Umbenennen, zweites refresh")
        self.switch()
        self.assertDue(8, "nach dem Umbenennen, refresh und Seitenwechsel")

    def test_c_neue_zeile_nach_umbenennen(self):
        """Neue Zeile nach dem Umbenennen: richtig; danach wieder schrittweise."""
        self.prepare_old_texts()
        self.view.refresh()
        rename_in_place(self.path)
        self.db.log_card("x", CARD_RENAMES[0][1], "lernen", None)
        self.view.refresh()
        self.assertDue(8, "neue Zeile nach dem Umbenennen, refresh")
        self.switch()
        self.assertDue(8, "neue Zeile nach dem Umbenennen, Seitenwechsel")
        index = self.view._review_index
        self.assertFalse(index.always_full)
        full, steps = index.full_builds, index.steps
        self.db.log_card("x", CARD_RENAMES[1][1], "lernen", None)
        self.view.refresh()
        self.assertDue(8, "zweite neue Zeile")
        self.assertEqual((index.full_builds, index.steps), (full, steps + 1))

    def test_d_ohne_alte_texte_bleibt_zwischenspeicher(self):
        """Normalfall: keine Abfrage und kein Neuzeichnen mehr als bisher."""
        insert_cards(self.path, [new for _old, new in CARD_RENAMES[:3]])
        self.view.refresh()
        self.assertDue(3, "Start")
        self.assertFalse(self.view._review_index.always_full)
        counts = dict(self.view.query_counts)
        self.view.refresh()
        self.assertEqual(self.view.query_counts, counts, "refresh ohne Aenderung")
        self.switch()
        refreshes = self.view.refresh_count
        self.switch()
        self.switch()
        self.assertEqual(self.view.refresh_count, refreshes, "Seitenwechsel ohne Aenderung")
        self.assertEqual(self.view.query_counts, counts)
        self.db.log_card("x", CARD_RENAMES[1][1], "lernen", False)
        self.view.refresh()
        self.assertDue(2, "neue Zeile (Karte heute beantwortet)")
        self.assertEqual(self.view.query_counts["faellig"], counts["faellig"] + 1)
        self.assertEqual(self.view.query_counts["serie"], counts["serie"] + 1)

    def test_e_karten_nach_umbenennen(self):
        """Auch andere Abfragen lesen den Fragetext: Karte X mit neuem und
        altem Text zaehlt vor dem Umbenennen doppelt, danach einfach."""
        old, new = CARD_RENAMES[0]
        insert_cards(self.path, [new], correct=1)
        self.view.refresh()
        insert_cards(self.path, [old], correct=1)
        self.view.refresh()

        def shown_cards():
            self.root.update_idletasks()
            return self.view.bar_cards._note.split(" / ")[0]

        self.assertEqual(self.db.distinct_cards_learned(), 2)
        self.assertEqual(shown_cards(), "2")
        rename_in_place(self.path)
        self.assertEqual(self.db.distinct_cards_learned(), 1)
        self.view.refresh()
        self.assertEqual(shown_cards(), "1", "refresh")
        self.switch()
        self.assertEqual(shown_cards(), "1", "Seitenwechsel")
        self.view.refresh()
        self.assertEqual(shown_cards(), "1", "zweites refresh")


def tearDownModule():
    shutil.rmtree(_TMP, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
