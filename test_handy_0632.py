#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ab 0.63.2 (Bauer S2b): Handy-Logik und Hinweise.

A12  Aenderung vor Hinweis: Nach einem Hinweis (toast -> page.show_dialog)
     zeichnet Flet die uebrigen Aenderungen eines Ereignisses nicht mehr von
     selbst (flet/messaging/session.py after_event). Die Stellen zeichnen
     darum am Ende ausdruecklich (_redraw). Datenbank-Meldungen beim Start
     bleiben stehen.
Z7   Dasselbe fuer alle weiteren Handy-Ereignisse, die schreiben.
B-E-03 Blaetterpfeile auf der ersten bzw. letzten Seite gesperrt.
B-E-04 Leere Suche zeigt einen Hinweis.
B-E-10 USV-Bild bricht bei inf/NaN nicht ab.
B-G-23 WiSo: Hinweis "Zeit abgelaufen" (PC und Handy, gleicher Text).
B-D-12 Handy: "Historie loeschen" bestaetigt; Fehler: genau ein Hinweis.

Die Tests pruefen das Modell und die Reihenfolge (Aufzeichnung), nicht die
Pixel: Ein echtes Flet-Fenster gibt es im Container nicht.
"""
import ast
import datetime
import itertools
import math
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
# Fest (nicht setdefault): Der Test loescht die Historie und schreibt
# einstellungen.json neben der Datenbank, nie in echte Lerndaten
os.environ["FISI_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "handy_0632.db")

WISO_TEXT = "Die Zeit ist um, die Prüfung wurde abgegeben und ausgewertet."
SEARCH_HINT = "Gib oben einen Suchbegriff ein und tippe auf die Lupe."
DB_TEXT = "Datenbank-Hinweis (Test)"


def _flet_ok():
    try:
        import flet  # noqa: F401
        return True
    except ImportError:
        return False


class FakePage:
    """Seite ohne Flutter. show_dialog oeffnet den Hinweis wie Flet."""

    def __init__(self):
        self.views, self.overlay, self.tasks = [], [], []

    def run_task(self, handler, *args, **kwargs):
        self.tasks.append(handler)

    def show_dialog(self, dialog):
        dialog.open = True

    def __getattr__(self, _name):
        return lambda *args, **kwargs: None


_SHARED = {}


def _app():
    if "app" not in _SHARED:
        sys.path.insert(1, os.path.join(HERE, "mobile", "src"))
        import main
        _SHARED["main"] = main
        _SHARED["app"] = main.FISIMobileApp(FakePage())
    return _SHARED["main"], _SHARED["app"]


def _past(hours=5):
    return datetime.datetime.now() - datetime.timedelta(hours=hours)


@unittest.skipUnless(_flet_ok(), "flet fehlt")
class HandyBasis(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.main, cls.app = _app()
        import fisi_pruefung as fp
        cls.fp = fp

    def setUp(self):
        """Aufzeichnung: Hinweise und ausdrueckliches Zeichnen in Reihenfolge."""
        self.events = []
        self.snap = lambda: None
        main = self.main

        def redraw(*controls):
            self.events.append(("redraw", [id(c) for c in controls], self.snap()))
        toast_original = self.app.toast

        def toast(message, color=None, **kwargs):
            self.events.append(("toast", message, self.snap()))
            toast_original(message, color, **kwargs)
        patches = [mock.patch.object(main, "_redraw", redraw),
                   mock.patch.object(self.app, "toast", toast)]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def db_error(self, name, result=None):
        """Schreib-/Lesemethode der Datenbank meldet einen Fehler (wie
        DBManager._report ueber error_handler) und liefert result."""
        db = self.app.db

        def failing(*_args, **_kwargs):
            db.error_handler(DB_TEXT)
            return result
        return mock.patch.object(db, name, failing)

    def toast_index(self, text=DB_TEXT):
        for index, event in enumerate(self.events):
            if event[0] == "toast" and text in event[1]:
                return index
        self.fail("kein Hinweis mit %r: %r" % (text, self.events))

    def redraws_after(self, index, control):
        return [event for event in self.events[index + 1:]
                if event[0] == "redraw" and id(control) in event[1]]

    def assert_drawn_after_toast(self, control, text=DB_TEXT, name=""):
        index = self.toast_index(text)
        self.assertTrue(self.redraws_after(index, control),
                        "%s: nach dem Hinweis nicht gezeichnet: %r" % (name, self.events))


# ============================================================================
#  A12
# ============================================================================

class HinweisZeichnenTest(HandyBasis):

    def quiz(self):
        quiz = self.app.screens["quiz"]
        quiz._reset_controls()
        quiz.mode_pills.select_value("uebung", notify=False)
        quiz.status_pills.select_value(self.main.FILTER_ALL, notify=False)
        quiz.exam.visible = False
        quiz.practice_box.visible = True
        quiz._update_pool()
        self.addCleanup(quiz._reset_controls)
        return quiz

    def test_start_quiz_nach_datenbank_hinweis(self):
        quiz = self.quiz()
        self.snap = lambda: quiz.lbl_progress.value
        original = quiz.book.preferred_order

        def failing(*args, **kwargs):
            self.app.db.error_handler(DB_TEXT)
            return original(*args, **kwargs)
        with mock.patch.object(quiz.book, "preferred_order", failing):
            quiz.start_quiz()
        drawn = self.redraws_after(self.toast_index(), quiz.root)
        self.assertTrue(drawn, self.events)
        self.assertTrue(drawn[-1][2].startswith("Frage 1 / "), drawn)

    def test_antwort_nach_schreibfehler(self):
        quiz = self.quiz()
        quiz.start_quiz()
        quiz.options.select(quiz.session[0]["a"])
        self.events.clear()
        self.snap = lambda: (quiz.btn_submit.caption.value, quiz.box_explain.visible)
        with self.db_error("log_quiz_answer"):
            quiz.submit_answer()
        drawn = self.redraws_after(self.toast_index(), quiz.root)
        self.assertTrue(drawn, self.events)
        caption, explain = drawn[-1][2]
        self.assertIn(caption, ("Nächste Frage", "Auswertung anzeigen"))
        self.assertTrue(explain)

    def test_pille_pruefung_mit_abgelaufener_zeit(self):
        """Fehler (vermutet sichtbar): Tipp auf "Pruefung", waehrend die Zeit
        im Hintergrund ablief. Die Bewertung wird vor dem Hinweis gezeichnet,
        der Wechsel zur Pruefung danach."""
        fp = self.fp
        quiz = self.quiz()
        fp.save_running(fp.new_exam(fp.NETZWERKE, [], seed=1, now=_past()))
        self.addCleanup(fp.clear_running)
        self.addCleanup(setattr, quiz.exam, "state", None)
        self.snap = lambda: quiz.exam.visible
        quiz._on_mode("pruefung")
        index = self.toast_index("Jetzt folgt die Bewertung")
        before = [event for event in self.events[:index]
                  if event[0] == "redraw" and id(quiz.exam) in event[1]]
        self.assertTrue(before, "Bewertung nicht vor dem Hinweis gezeichnet: %r" % self.events)
        after = self.redraws_after(index, quiz.root)
        self.assertTrue(after, self.events)
        self.assertTrue(after[-1][2], "Pruefung beim Zeichnen nicht sichtbar")

    def test_start_mit_beschaedigter_datenbank(self):
        """Die Datenbank-Meldung beim Start blieb nicht stehen (show_tab
        schloss sie sofort). Jetzt kommt sie nach dem Aufbau als Hinweis."""
        main = self.main
        folder = tempfile.mkdtemp()
        path = os.path.join(folder, "kaputt.db")
        with open(path, "wb") as handle:
            handle.write(b"das ist keine SQLite-Datei " * 400)
        page = FakePage()
        with mock.patch.dict(os.environ, {"FISI_DB_PATH": path}), \
                mock.patch.object(main, "_redraw", lambda *c: None):
            app = main.FISIMobileApp(page)
        snack = getattr(app, "_toast", None)
        self.assertIsNotNone(snack, "kein Hinweis beim Start")
        self.assertTrue(snack.open, "Startmeldung sofort wieder geschlossen")
        texts = [text for text in main.fc.DB_ERROR_TEXTS.values() if text in snack.content.value]
        self.assertTrue(texts, snack.content.value)

    def test_erinnerung_zeichnet_nach_dem_hinweis(self):
        """Schutz (kein Fehler auf 14b3bd4): nach dem Hinweis folgt page.update()."""
        main, app = self.main, self.app
        calls = []
        self.snap = lambda: None
        with mock.patch.object(main, "reminder_due", lambda *a, **k: True), \
                mock.patch.object(main, "save_learning_settings", lambda **k: True), \
                mock.patch.object(main, "reminder_text", lambda goal: "Erinnerung (Test)"), \
                mock.patch.object(app.page, "update",
                                  lambda *a: calls.append(len(self.events)), create=True):
            app.check_reminder()
        index = self.toast_index("Erinnerung (Test)")
        self.assertTrue([c for c in calls if c > index], (calls, self.events))


# ============================================================================
#  B-G-23
# ============================================================================

class PruefungZeitTest(HandyBasis):

    def test_wiso_meldet_zeit_handy(self):
        fp = self.fp
        exam = self.app.screens["quiz"].exam
        before = len(self.app.db.exams())
        fp.save_running(fp.new_exam(fp.WISO, [], seed=1, now=_past()))
        self.addCleanup(fp.clear_running)
        exam.show()
        index = self.toast_index(WISO_TEXT)
        self.assertEqual(self.events[index][1], WISO_TEXT)
        drawn = [e for e in self.events[:index] if e[0] == "redraw" and id(exam) in e[1]]
        self.assertTrue(drawn, "Ergebnis nicht vor dem Hinweis gezeichnet")
        self.assertIsNotNone(exam.result)
        self.assertEqual(len(self.app.db.exams()), before + 1, "Ergebnis nicht gespeichert")

    def test_andere_pruefung_unveraendert(self):
        fp = self.fp
        exam = self.app.screens["quiz"].exam
        fp.save_running(fp.new_exam(fp.NETZWERKE, [], seed=2, now=_past()))
        self.addCleanup(fp.clear_running)
        self.addCleanup(setattr, exam, "state", None)
        exam.show()
        texts = [e[1] for e in self.events if e[0] == "toast"]
        self.assertEqual(texts, ["Die Zeit ist um, die Prüfung wurde abgegeben. Jetzt folgt "
                                 "die Bewertung."])


class PruefungZeitOeffnenTest(HandyBasis):
    """Nacharbeit M1: Zeit lief ausserhalb des Pruefungstrainers ab, dann
    Lernen -> Pruefungstrainer (app.open). push schliesst offene Hinweise;
    der Hinweis muss danach trotzdem offen sein."""

    def run_open(self, art, text):
        fp, app = self.fp, self.app
        quiz = app.screens["quiz"]
        quiz.mode_pills.select_value("uebung", notify=False)
        self.addCleanup(quiz.mode_pills.select_value, "uebung", False)
        self.addCleanup(setattr, quiz.exam, "state", None)
        fp.save_running(fp.new_exam(art, [], seed=5, now=_past()))
        self.addCleanup(fp.clear_running)
        app.show_tab("learn")
        self.addCleanup(app.show_tab, "dashboard")
        app.open("quiz")
        snack = getattr(app, "_toast", None)
        self.assertIsNotNone(snack, self.events)
        self.assertEqual(snack.content.value, text)
        self.assertTrue(snack.open, "Hinweis nach dem Oeffnen sofort geschlossen")
        self.assertEqual([e[1] for e in self.events if e[0] == "toast"], [text])

    def test_wiso_ueber_oeffnen(self):
        self.run_open(self.fp.WISO, WISO_TEXT)

    def test_andere_pruefung_ueber_oeffnen(self):
        self.run_open(self.fp.NETZWERKE, "Die Zeit ist um, die Prüfung wurde abgegeben. "
                                         "Jetzt folgt die Bewertung.")


class PruefungZeitPcTest(unittest.TestCase):
    """PC: ExamPanel._submit ohne Fenster (Attrappe fuer self)."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, HERE)
        try:
            import app_gui
        except Exception as error:   # pragma: no cover - ohne Tk
            raise unittest.SkipTest("app_gui nicht ladbar: %s" % error)
        import fisi_pruefung as fp
        cls.app_gui, cls.fp = app_gui, fp

    def run_submit(self, art):
        fp = self.fp
        events = []

        class Fake:
            state = fp.new_exam(art, [], seed=3, now=_past())

            def _flush_answers(self):
                pass

            def _stop_timer(self):
                pass

            def _finish(self):
                events.append("ausgewertet")

            def show_grading(self):
                events.append("bewertung")
        with mock.patch.object(self.app_gui.messagebox, "showinfo",
                               lambda *args, **kwargs: events.append(args)), \
                mock.patch.object(fp, "save_running", lambda state: True):
            self.app_gui.ExamPanel._submit(Fake(), auto=True)
        return events

    def test_wiso_meldet_zeit_pc(self):
        self.assertEqual(self.run_submit(self.fp.WISO),
                         ["ausgewertet", ("Zeit abgelaufen", WISO_TEXT)])

    def test_andere_pruefung_pc_unveraendert(self):
        self.assertEqual(self.run_submit(self.fp.NETZWERKE),
                         [("Zeit abgelaufen", "Die Zeit ist um, die Prüfung wurde abgegeben. "
                                              "Jetzt folgt die Bewertung."), "bewertung"])

    def test_text_pc_gleich_handy(self):
        for name in ("app_gui.py", os.path.join("mobile", "src", "main.py")):
            with open(os.path.join(HERE, name), encoding="utf-8") as handle:
                tree = ast.parse(handle.read())
            found = [node.value for node in ast.walk(tree)
                     if isinstance(node, ast.Constant) and node.value == WISO_TEXT]
            self.assertEqual(len(found), 1, name)


# ============================================================================
#  B-E-03
# ============================================================================

class BlaetternTest(HandyBasis):

    def paged(self, count):
        main = self.main
        items = [{"title": "Aufgabe %d" % n, "cat": main.CATEGORIES[0], "theme": "T"}
                 for n in range(count)]
        box = main.PagedListBox(items, lambda _p: None, subtitle=lambda item: "",
                                status_source=dict)
        box.refresh()
        return box

    def assert_buttons(self, box, prev, forward, name):
        self.assertEqual((bool(box.btn_prev.disabled), bool(box.btn_next.disabled)),
                         (prev, forward), name)

    def test_liste(self):
        size = self.main.fc.LIST_PAGE_SIZE
        box = self.paged(3)
        self.assert_buttons(box, True, True, "eine Seite")
        box = self.paged(2 * size + 1)
        self.assert_buttons(box, True, False, "Seite 1 von 3")
        box.turn(1)
        self.assert_buttons(box, False, False, "Seite 2 von 3")
        box.turn(1)
        self.assert_buttons(box, False, True, "Seite 3 von 3")
        box.turn(-2)
        self.assert_buttons(box, True, False, "zurueck auf Seite 1")

    def test_listen_der_ansichten(self):
        for key in ("scenarios", "ap1scenarios", "testproject"):
            box = self.app.screens[key].paged
            box.refresh()
            pages = max(1, -(-len(box.filtered) // self.main.fc.LIST_PAGE_SIZE))
            self.assertTrue(box.btn_prev.disabled, key)
            self.assertEqual(bool(box.btn_next.disabled), pages == 1, key)

    def test_notizblock(self):
        main = self.main
        screen = self.app.screens["notebook"]
        screen.refresh()
        saved = screen.entries
        self.addCleanup(setattr, screen, "entries", saved)
        screen.entries = []
        screen.page = 0
        screen._paint()
        self.assertTrue(screen.btn_prev.disabled and screen.btn_next.disabled, "leer")
        screen.entries = [{} for _n in range(2 * main.NOTEBOOK_PAGE + 1)]
        with mock.patch.object(screen, "_row", lambda entry: main.ft.Text("x")), \
                mock.patch.object(self.app, "scroll_top", lambda: None):
            screen.page = 0
            screen._paint()
            self.assertEqual((bool(screen.btn_prev.disabled), bool(screen.btn_next.disabled)),
                             (True, False))
            screen.turn(1)
            self.assertEqual((bool(screen.btn_prev.disabled), bool(screen.btn_next.disabled)),
                             (False, False))
            screen.turn(1)
            self.assertEqual((bool(screen.btn_prev.disabled), bool(screen.btn_next.disabled)),
                             (False, True))


# ============================================================================
#  B-E-04
# ============================================================================

class SucheLeerTest(HandyBasis):

    def test_leere_suche_zeigt_hinweis(self):
        main = self.main
        screen = main.SearchScreen(self.app)
        self.assertEqual(screen.lbl_info.value, SEARCH_HINT)
        self.assertEqual(getattr(main, "SEARCH_EMPTY_HINT", None), SEARCH_HINT)
        screen.search("raid")
        self.assertTrue(screen.results.controls)
        self.assertNotEqual(screen.lbl_info.value, SEARCH_HINT)
        screen.search("   ")
        self.assertEqual(screen.lbl_info.value, SEARCH_HINT)
        self.assertEqual(screen.results.controls, [])


# ============================================================================
#  B-E-10
# ============================================================================

class UsvBildTest(HandyBasis):

    def bar_parts(self, share):
        bar = self.main.ui.UpsPicture._bar(share, "#ff0000")
        return [part.expand for part in bar.content.controls]

    def test_nicht_endliche_werte(self):
        self.assertEqual(self.bar_parts(math.inf), [1000])
        self.assertEqual(self.bar_parts(math.nan), [1000])
        self.assertEqual(self.bar_parts(-math.inf), [1000])
        nan_bar = self.main.ui.UpsPicture._bar(math.nan, "#ff0000")
        self.assertEqual(nan_bar.content.controls[0].bgcolor, self.main.C["ring_bg"])
        self.assertEqual(self.bar_parts(0.5), [500, 500])
        # +inf = voll: der eine Teil hat die Balkenfarbe, nicht ring_bg
        inf_bar = self.main.ui.UpsPicture._bar(math.inf, "#ff0000")
        self.assertEqual(inf_bar.content.controls[0].bgcolor, "#ff0000")

    def test_bild_mit_nan(self):
        picture = {"last": "1 W", "last_detail": "", "usv": "", "usv_detail": "",
                   "akku": "", "akku_detail": "", "auslastung": math.nan, "grenze": 80,
                   "urteil": None,
                   "balken": [{"label": "Akku neu", "text": "nan min", "anteil": math.nan,
                               "art": "neu"},
                              {"label": "Gewünscht", "text": "inf min", "anteil": math.inf,
                               "art": "ziel"}]}
        self.main.ui.UpsPicture().set_picture(picture)


# ============================================================================
#  B-D-12 (Handy)
# ============================================================================

class HistorieLoeschenTest(HandyBasis):

    def setUp(self):
        super().setUp()
        patch = mock.patch.object(self.app, "confirm", lambda title, text, yes: yes())
        patch.start()
        self.addCleanup(patch.stop)
        self.settings = self.app.screens["settings"]

    def toasts(self):
        return [event[1] for event in self.events if event[0] == "toast"]

    def test_erfolg(self):
        self.settings.clear_history()
        toasts = self.toasts()
        self.assertEqual(len(toasts), 1, toasts)
        self.assertTrue(toasts[0].startswith("Die Historie wurde gelöscht."), toasts)

    def test_fehler_genau_ein_hinweis(self):
        db = self.app.db
        handler = db.error_handler
        for name in ("clear_history", "reset_all"):
            self.events.clear()
            with self.db_error(name, result=False):
                getattr(self.settings, name)()
            toasts = self.toasts()
            self.assertEqual(len(toasts), 1, (name, toasts))
            self.assertTrue(toasts[0].startswith("Es wurde nichts gelöscht."), toasts)
            self.assertEqual(toasts[0], "Es wurde nichts gelöscht.\n\n" + DB_TEXT,
                             "Leerzeile vor dem Datenbanktext (PC = Handy)")
            self.assertIs(db.error_handler, handler, "Meldeweg nicht zurueckgesetzt")

    def test_meldeweg_zurueck_auch_bei_ausnahme(self):
        db = self.app.db
        handler = db.error_handler

        def crash():
            db.error_handler(DB_TEXT)
            raise RuntimeError("Test")
        with mock.patch.object(db, "clear_history", crash):
            with self.assertRaises(RuntimeError):
                self.settings.clear_history()
        self.assertIs(db.error_handler, handler, "finally fehlt")

    def test_fehler_schreibgeschuetzt(self):
        """Echter Fehlerweg: Datenbank nimmt nichts mehr an (wie nach einer
        Meldung "schreibgeschuetzt"); es kommt trotzdem genau ein Hinweis."""
        db = self.app.db
        saved = (db.read_only_reason, dict(db.error_counts))

        def restore():
            db.read_only_reason, db.error_counts = saved[0], saved[1]
        self.addCleanup(restore)
        db.read_only_reason = "schreibschutz"
        self.settings.clear_history()
        self.assertEqual(self.toasts(), ["Es wurde nichts gelöscht."])


# ============================================================================
#  Z7: weitere schreibende Ereignisse
# ============================================================================

class SchreibfehlerZeichnenTest(HandyBasis):

    def cards(self):
        cards = self.app.screens["cards"]
        cards.status_pills.select_value(self.main.FILTER_ALL, notify=False)
        cards.cat_pills.select_value("Alle", notify=False)
        cards.apply_filter()
        self.events.clear()
        return cards

    def test_karteikarten_blaettern_filter_modus(self):
        cards = self.cards()
        for name, event in (("step", lambda: cards.step(1)),
                            ("apply_filter", cards.apply_filter),
                            ("_on_mode", lambda: cards._on_mode(cards.mode))):
            self.events.clear()
            cards.pending = cards.filtered[0]
            with self.db_error("log_card"):
                event()
            self.assert_drawn_after_toast(cards.root, name=name)

    def test_karteikarten_leere_auswahl(self):
        """Leer-Zweig von update_ui (keine Karte in der Auswahl)."""
        cards = self.cards()
        saved = cards.filtered
        self.addCleanup(setattr, cards, "filtered", saved)
        cards.pending = cards.filtered[0]
        cards.filtered = []
        with self.db_error("log_card"):
            cards.update_ui()
        self.assertEqual(cards.lbl_counter.value, "0 / 0")
        self.assert_drawn_after_toast(cards.root, name="update_ui leer")

    def test_karteikarten_bewerten_und_pruefen(self):
        cards = self.cards()
        cards.pending = cards.filtered[cards.index]
        with self.db_error("log_card"):
            cards.rate(True)
        self.assert_drawn_after_toast(cards.root, name="rate")
        self.events.clear()
        cards._on_mode("freitext")
        cards.txt_answer.value = "irgendwas"
        self.events.clear()
        with self.db_error("log_card"):
            cards.check_answer()
        self.assert_drawn_after_toast(cards.root, name="check_answer")

    def test_quiz_auswertung(self):
        quiz = self.app.screens["quiz"]
        quiz._reset_controls()
        self.addCleanup(quiz._reset_controls)
        quiz.session = [quiz.questions[0]]
        quiz.index, quiz.score, quiz.answered, quiz.running = 0, 0, True, True
        quiz.start_time = 0
        with self.db_error("save_test_result", result=False):
            quiz.submit_answer()
        self.assert_drawn_after_toast(quiz.root, name="finish_quiz")

    def test_pruefung_auswerten(self):
        fp = self.fp
        exam = self.app.screens["quiz"].exam
        exam.state = fp.submit(fp.new_exam(fp.WISO, [], seed=4))
        with self.db_error("log_quiz_answer"):
            exam._finish_now()
        self.assert_drawn_after_toast(exam, name="_finish_now")

    def test_szenarien_und_testprojekt(self):
        for key, writer in (("scenarios", "log_scenario"), ("ap1scenarios", "log_ap1"),
                            ("testproject", "log_project")):
            screen = self.app.screens[key]
            screen.open_detail(0)
            screen.pending = 0
            self.events.clear()
            with self.db_error(writer):
                screen.next_item()
            self.assert_drawn_after_toast(screen.detail, name=key + " next_item")
            screen.pending = screen.index
            self.events.clear()
            with self.db_error(writer):
                screen.rate(True)
            self.assert_drawn_after_toast(screen.detail, name=key + " rate")
            self.assert_drawn_after_toast(screen.root, name=key + " rate Liste")

    def test_abschlussprojekt(self):
        screen = self.app.screens["abschluss"]
        main = self.main

        counter = itertools.count()

        def pending():
            value = "Titel %d" % next(counter)
            screen.pending.add("titel")
            screen.inputs["titel"] = lambda: value
            self.events.clear()
        cases = [("_blurred", screen._blurred),
                 ("_on_tab", lambda: screen._on_tab(screen.tab)),
                 ("_export", lambda: screen._export("txt")),
                 ("_set_check", lambda: screen._set_check("x_test", True)),
                 ("_set_category", lambda: screen._set_category(main.CATEGORIES[0]))]
        for name, event in cases:
            screen._on_tab("uebersicht")
            pending()
            with self.db_error("save_project_field"):
                event()
            self.assert_drawn_after_toast(screen.root, name=name)

    def test_abschlussprojekt_fachgespraech_bewerten(self):
        screen = self.app.screens["abschluss"]
        main = self.main
        screen._set_category(main.CATEGORIES[0])
        screen._on_tab("fachgespraech")
        buttons = []

        def walk(control):
            if isinstance(control, main.ui.GradientButton) and \
                    control.caption.value == "Gewusst":
                buttons.append(control)
            for child in (getattr(control, "controls", None) or []):
                walk(child)
            content = getattr(control, "content", None)
            if content is not None and not isinstance(content, str):
                walk(content)
        walk(screen.tab_boxes["fachgespraech"])
        self.assertTrue(buttons)
        self.events.clear()
        with self.db_error("save_project_field"):
            buttons[0]._handler(None)
        self.assert_drawn_after_toast(screen.root, name="Fachgespraech bewerten")
        screen._on_tab("uebersicht")

    def test_trainer_pruefen(self):
        trainer = self.app.screens["calc"].trainer
        trainer.start_round()
        self.events.clear()
        with self.db_error("log_trainer"):
            trainer.check()
        self.assert_drawn_after_toast(trainer, name="Trainer check")

    def test_abschlussprojekt_vorlage(self):
        """H1: Vorlage uebernehmen zeigt einen eigenen Hinweis; vorher wird
        das neu geladene Projekt gezeichnet (Ende von _on_tab)."""
        screen = self.app.screens["abschluss"]
        screen._on_tab("uebersicht")
        self.events.clear()
        screen.use_template(0)
        index = next(i for i, e in enumerate(self.events) if e[0] == "toast")
        before = [e for e in self.events[:index]
                  if e[0] == "redraw" and id(screen.root) in e[1]]
        self.assertTrue(before, self.events)

    def test_app_geht_in_den_hintergrund(self):
        screen = self.app.screens["abschluss"]
        screen._on_tab("uebersicht")
        screen.pending.add("titel")
        screen.inputs["titel"] = lambda: "Hintergrund"
        self.events.clear()
        event = mock.Mock(state=self.main.ft.AppLifecycleState.PAUSE)
        with self.db_error("save_project_field"), \
                mock.patch.object(self.app.sync, "on_leave", lambda: None):
            self.app._lifecycle(event)
        self.assert_drawn_after_toast(screen.root, name="_lifecycle")


if __name__ == "__main__":
    unittest.main()
