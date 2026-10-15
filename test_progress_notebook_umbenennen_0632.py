# -*- coding: utf-8 -*-
"""Befund-Test 0.63.2 (Weisung Antwort Nachtrag 45a, Frage 4): Notizblock und
Fortschritt nach Umbenennen an Ort und Stelle.

Merge-Test FG-117 (zuerst Befund-Test auf version-0632-fg115-probe): Zeigen die
beiden Ansichten nach dem Umbenennen alter Fragetexte durch ein zweites Programm
(eigener Prozess, wie test_dash_query_0632 Test a) Veraltetes? Seit FG-117 gruen.

apply_question_renames (fisi_core) schreibt alte Fragetexte an Ort und Stelle
um; Anzahl und hoechste Nummer der Tabellen bleiben gleich. NotebookView und
ProgressView merken sich beim Seitenwechsel genau diesen Stempel (on_show,
_refresh_key, seit 0.50/0.54); der Notizblock merkt sich ausserdem sein
StatusBook (_status_book), der Fortschritt seine Abdeckung (coverage_key).

  * a Notizblock, Seitenwechsel nach Umbenennen (zweites Programm)
  * b Fortschritt (Abdeckung), Seitenwechsel nach Umbenennen (zweites Programm)
  * c Notizblock, explizites refresh() nach Umbenennen
  * d Fortschritt, explizites refresh() nach Umbenennen
  * e Kontrolle: neue Zeile nach Umbenennen -> beide Ansichten richtig
  * f wie a-d mit Quiz-Antworten (quiz_answers): Seitenwechsel, dann refresh()

Wahrheit ist jeweils die Berechnung direkt aus der Datenbank
(notebook_entries(StatusBook(db)), frp.Coverage(StatusBook(db), plan).point).
Vorbedingungen in jedem Test: Stempel vor/nach dem Umbenennen gleich, und die
Wahrheit aendert sich durch das Umbenennen (sonst waere der Test leer).
Aufruf:  xvfb-run -a python test_progress_notebook_umbenennen_0632.py
"""
import datetime
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)
_TMP = tempfile.mkdtemp(prefix="fisi_pnu_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "pnu.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(_TMP, "selbsttest.log"))
os.environ["HOME"] = _TMP
os.environ["APPDATA"] = _TMP
os.environ["FISI_VORLADEN"] = "0"

import fisi_core as fc  # noqa: E402
import fisi_rahmenplan as frp  # noqa: E402

VALID_CARDS = {card["q"] for card in fc.KARTEIKARTEN}
# (alter Text, neuer Text) der Karteikarten, deren neuer Text gilt und deren
# alter nicht (inhalte/umbenennungen.json)
CARD_RENAMES = [(old, new) for old, new in fc.QUESTION_RENAMES["card_events"].items()
                if new in VALID_CARDS and old not in VALID_CARDS]
VALID_QUIZ = {quiz["q"] for quiz in fc.QUIZ_QUESTIONS}
QUIZ_RENAMES = [(old, new) for old, new in fc.QUESTION_RENAMES["quiz_answers"].items()
                if new in VALID_QUIZ and old not in VALID_QUIZ]
YESTERDAY = (datetime.date.today() - datetime.timedelta(days=1)).isoformat() + " 10:00:00"
TABLES = ("card_events", "quiz_answers")


def insert_cards(path, questions, correct):
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
        return tuple(conn.execute("SELECT COUNT(*), MAX(rowid) FROM %s" % table).fetchone()
                     for table in TABLES)
    finally:
        conn.close()


class ProgressNotebookRenameTest(unittest.TestCase):

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
        cls.notebook = cls.app.views["notebook"]
        cls.progress = cls.app.views["progress"]
        cls.home_db = cls.notebook.db

    @classmethod
    def tearDownClass(cls):
        try:
            tk_ = cls.root.tk
            for job in tk_.splitlist(tk_.call("after", "info")):
                tk_.call("after", "cancel", job)
            cls.root.destroy()
        except Exception:  # noqa: BLE001
            pass

    def _reset(self, db):
        for view in (self.notebook, self.progress):
            view.db = db
            view._refreshed = None
        self.notebook._book_stamp = None
        self.progress._coverage_key = None

    def setUp(self):
        self.assertGreaterEqual(len(CARD_RENAMES), 8)
        self.dir = tempfile.mkdtemp(prefix="db_", dir=_TMP)
        self.path = os.path.join(self.dir, "t.db")
        self.db = fc.DBManager(self.path)
        # Eigene Datenbank je Test; Merkzustand beider Ansichten zuruecksetzen,
        # damit kein Stempel einer anderen Datenbank zufaellig passt
        self._reset(self.db)
        self.app.show_view("dashboard")
        self.pump()

    def tearDown(self):
        self._reset(self.home_db)
        shutil.rmtree(self.dir, ignore_errors=True)
        self.assertEqual(self.errors, [])

    # -- Hilfen ---------------------------------------------------------------

    def pump(self, rounds=15):
        """Ereignisse abarbeiten; die Abdeckung fuellt sich per after(50)."""
        for _ in range(rounds):
            self.root.update()
            time.sleep(0.01)
        self.root.update()

    def show(self, key):
        """Seitenwechsel: weg (Karteikarten) und zur Ansicht key (on_show)."""
        self.app.show_view("cards")
        self.pump(2)
        self.app.show_view(key)
        self.pump()

    # Notizblock
    def nb_shown(self):
        return len(self.notebook.entries)

    def nb_truth(self):
        return len(fc.notebook_entries(fc.StatusBook(self.db)))

    # Fortschritt (Abdeckung)
    def pr_shown(self):
        card = self.progress.coverage_card
        self.assertIsNotNone(card, "Abdeckung nicht aufgebaut")
        return dict(card.coverage.point)

    def pr_truth(self):
        return dict(frp.Coverage(fc.StatusBook(self.db), frp.load_rp_settings()).point)

    def assertCoverage(self, msg):
        shown, truth = self.pr_shown(), self.pr_truth()
        diff = sorted(point for point in set(shown) | set(truth)
                      if shown.get(point) != truth.get(point))
        self.assertEqual(diff, [], "%s: %d Punkte abweichend (%s)" % (
            msg, len(diff), ", ".join("%s %r statt %r" % (point, shown.get(point),
                                                          truth.get(point))
                                      for point in diff[:5])))

    def prepare(self, correct):
        """3 neue Texte gestern; danach schreibt ein aelteres Programm 5 alte
        Texte (gelten erst nach dem Umbenennen)."""
        insert_cards(self.path, [new for _old, new in CARD_RENAMES[:3]], correct)
        insert_cards(self.path, [old for old, _new in CARD_RENAMES[3:8]], correct)

    def rename_checked(self, rename, truth):
        before_stamp, before_truth = stamp(self.path), truth()
        rename(self.path)
        self.assertEqual(stamp(self.path), before_stamp, "Vorbedingung: Stempel gleich")
        self.assertNotEqual(truth(), before_truth, "Vorbedingung: Wahrheit aendert sich")

    # -- Tests ----------------------------------------------------------------

    def test_a_notizblock_seitenwechsel(self):
        self.prepare(correct=0)
        self.show("notebook")
        self.assertEqual(self.nb_shown(), self.nb_truth(), "vor dem Umbenennen")
        self.assertEqual(self.nb_truth(), 3)
        self.rename_checked(second_program, self.nb_truth)
        self.assertEqual(self.nb_truth(), 8)
        self.show("notebook")
        self.assertEqual(self.nb_shown(), self.nb_truth(),
                         "Notizblock nach dem Umbenennen, Seitenwechsel")

    def test_b_fortschritt_seitenwechsel(self):
        self.prepare(correct=1)
        self.show("progress")
        self.assertCoverage("vor dem Umbenennen")
        self.rename_checked(second_program, self.pr_truth)
        self.show("progress")
        self.assertCoverage("Abdeckung nach dem Umbenennen, Seitenwechsel")

    def test_c_notizblock_refresh(self):
        self.prepare(correct=0)
        self.show("notebook")
        self.assertEqual(self.nb_shown(), 3)
        self.rename_checked(rename_in_place, self.nb_truth)
        self.notebook.refresh(keep_page=True)
        self.pump()
        self.assertEqual(self.nb_shown(), self.nb_truth(),
                         "Notizblock nach dem Umbenennen, refresh()")

    def test_d_fortschritt_refresh(self):
        self.prepare(correct=1)
        self.show("progress")
        self.assertCoverage("vor dem Umbenennen")
        self.rename_checked(rename_in_place, self.pr_truth)
        self.progress.refresh()
        self.pump()
        self.assertCoverage("Abdeckung nach dem Umbenennen, refresh()")

    def test_e_kontrolle_neue_zeile(self):
        """Kontrolle: Aendert sich der Stempel (neue Zeile), sind beide richtig."""
        self.prepare(correct=0)
        self.show("notebook")
        self.show("progress")
        self.rename_checked(second_program, self.nb_truth)
        renamed = {new for _old, new in CARD_RENAMES}
        other = next(card["q"] for card in fc.KARTEIKARTEN if card["q"] not in renamed)
        self.db.log_card("x", other, "lernen", False)
        self.show("notebook")
        self.assertEqual(self.nb_truth(), 9)
        self.assertEqual(self.nb_shown(), self.nb_truth(), "Notizblock, neue Zeile")
        self.show("progress")
        self.assertCoverage("Abdeckung, neue Zeile")

    def test_f_quiz_seitenwechsel_und_refresh(self):
        """Wie a-d mit Quiz: falsch -> Notizblock, richtig -> Abdeckung."""
        old, new = [o for o, _n in QUIZ_RENAMES], [n for _o, n in QUIZ_RENAMES]
        for wrong, right, step in ((new[:2] + old[2:5], new[5:7] + old[7:9], "Seitenwechsel"),
                                   (old[9:12], old[12:15], "refresh()")):
            for question in wrong + right:
                self.db.log_quiz_answer("x", question, question in right)
            self.show("notebook")
            self.show("progress")
            self.assertEqual(self.nb_shown(), self.nb_truth(), "Quiz vor dem Umbenennen")
            self.assertCoverage("Quiz vor dem Umbenennen")
            before = self.pr_truth()
            self.rename_checked(second_program, self.nb_truth)
            self.assertNotEqual(self.pr_truth(), before, "Vorbedingung: Abdeckung aendert sich")
            if step == "refresh()":
                self.notebook.refresh(keep_page=True)
                self.progress.refresh()
                self.pump()
            else:
                self.show("notebook")
                self.show("progress")
            self.assertEqual(self.nb_shown(), self.nb_truth(), "Quiz-Notizblock, " + step)
            self.assertCoverage("Quiz-Abdeckung, " + step)


def tearDownModule():
    shutil.rmtree(_TMP, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
