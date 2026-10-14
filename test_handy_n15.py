#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ab 0.63.2 (Bauer N15): Handy-Hinweise, Zeichnen im Spiel, Blaetterpfeile.

N-a  Ein Seitenwechsel schliesst nur Hinweise, die vor dem Ereignis offen
     waren: toast vergibt eine laufende Nummer, push(toast_bis=...) schliesst
     nur kleinere Nummern. Szenarien/Testprojekte (open_detail) lesen die
     Nummer vor dem Schreiben (_flush). Ohne Parameter wie bisher.
     Ab Weisung zu Meldung 41 (Abschnitt 16): open liest die Nummer vor
     on_show oder nimmt eine mitgegebene an (HA3-HA9), das Spiel gibt sie an
     den Seitenwechsel (SP1-SP6, SP1 ueber open_site(toast_bis=...)).
N-b  Z7 im Spiel (mobile/src/spiel.py): Ereignisse, die schreiben und danach
     ohne eigenes Zeichnen enden, zeichnen am Ende mit spiel._redraw (wie
     main._redraw), damit die Anzeige nach einem Datenbank-Hinweis nicht
     haengt. Bestandsaufnahme aller self.game.<m>(-Aufrufe als Tabelle.
N-h  Subnetting-Blaettern: gesperrte Pfeile in C["muted"], freie in
     C["accent"] (gleiche Regel wie _paint_page_buttons, B-E-03).
     Ab Nico 14b (Meldung 39): in Lila/Magenta und Blau/Tuerkis hell gesperrt
     C["muted"] zu 40 % zur Karte aufgehellt (PfeilFarbe14bTest).

Eigenstaendig lauffaehig (eigene FakePage/Basis, kein Import aus anderen
Testdateien). Geprueft werden Modell und Reihenfolge (Aufzeichnung), nicht
die Pixel. Fuer die Gegenprobe kann der Code-Ordner umgestellt werden:
    N15_CODE=<ordner mit dem Code> python test_handy_n15.py
"""
import ast
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("N15_CODE") or HERE)
# Fest (nicht setdefault): nie in echte Lerndaten schreiben
os.environ["FISI_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "handy_n15.db")

DB_TEXT = "Datenbank-Hinweis (Test N15)"
MAIN_PY = os.path.join(CODE, "mobile", "src", "main.py")
SPIEL_PY = os.path.join(CODE, "mobile", "src", "spiel.py")


def _flet_ok():
    try:
        import flet  # noqa: F401
        return True
    except ImportError:
        return False


class FakePage:
    """Seite ohne Flutter. show_dialog oeffnet den Hinweis wie Flet;
    update wird aufgezeichnet (Zaehlung je Seitenwechsel)."""

    def __init__(self):
        self.views, self.overlay, self.tasks, self.updates = [], [], [], []
        self.recorder = None

    def run_task(self, handler, *args, **kwargs):
        self.tasks.append(handler)

    def show_dialog(self, dialog):
        dialog.open = True

    def update(self, *controls):
        self.updates.append(controls)
        if self.recorder is not None:
            self.recorder.append(("page_update",))

    def __getattr__(self, _name):
        return lambda *args, **kwargs: None


_SHARED = {}


def _app():
    if "app" not in _SHARED:
        sys.path.insert(0, CODE)
        sys.path.insert(1, os.path.join(CODE, "mobile", "src"))
        import main
        import spiel
        _SHARED["main"], _SHARED["spiel"] = main, spiel
        _SHARED["app"] = main.FISIMobileApp(FakePage())
    return _SHARED["main"], _SHARED["spiel"], _SHARED["app"]


@unittest.skipUnless(_flet_ok(), "flet fehlt")
class N15Basis(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.main, cls.spiel, cls.app = _app()

    def setUp(self):
        """Aufzeichnung: Hinweise und ausdrueckliches Zeichnen in Reihenfolge."""
        self.events = []
        self.app.page.recorder = self.events

        def redraw(*controls):
            self.events.append(("redraw", [id(c) for c in controls]))
        toast_original = self.app.toast

        def toast(message, color=None, **kwargs):
            self.events.append(("toast", message))
            toast_original(message, color, **kwargs)
        # create=True: auf Staenden ohne spiel._redraw (vor N-b) zeichnet das
        # Spiel nie -> die Pruefung schlaegt fehl statt abzubrechen
        patches = [mock.patch.object(self.main, "_redraw", redraw),
                   mock.patch.object(self.spiel, "_redraw", redraw, create=True),
                   mock.patch.object(self.app, "toast", toast)]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.addCleanup(setattr, self.app.page, "recorder", None)

    def db_error(self, name, result=None, db=None):
        """Schreibmethode der Datenbank meldet einen Fehler (wie
        DBManager._report ueber error_handler) und liefert result."""
        db = db or self.app.db

        def failing(*_args, **_kwargs):
            db.error_handler(DB_TEXT)
            return result
        return mock.patch.object(db, name, failing)

    def toast_index(self, text=DB_TEXT):
        for index, event in enumerate(self.events):
            if event[0] == "toast" and text in event[1]:
                return index
        self.fail("kein Hinweis mit %r: %r" % (text, self.events))

    def assert_drawn_after_toast(self, control, name=""):
        index = self.toast_index()
        drawn = [event for event in self.events[index + 1:]
                 if event[0] == "redraw" and id(control) in event[1]]
        self.assertTrue(drawn, "%s: nach dem Hinweis nicht gezeichnet: %r" % (name, self.events))

    def toasts(self, text=DB_TEXT):
        return [event for event in self.events if event[0] == "toast" and text in event[1]]

    def drop_views(self):
        while len(self.app.page.views) > 1:
            self.app.page.views.pop()


# ============================================================================
#  N-a  Hinweis-Nummer und push(toast_bis=...)
# ============================================================================

class HinweisNummerTest(N15Basis):
    """A-N15-01 (K1): jede Hinweis-Ausgabe zaehlt genau um 1, Lesen ohne Folgen."""

    def test_nummer_steigt_je_hinweis(self):
        app = self.app
        start = app.toast_mark()
        self.assertEqual(app.toast_mark(), start)              # Lesen aendert nichts
        app.toast("eins")
        self.assertEqual(app._toast_nr, start)
        self.assertEqual(app.toast_mark(), start + 1)
        app.db.error_handler(DB_TEXT)                          # Datenbank-Weg (_db_error)
        self.assertEqual(app._toast_nr, start + 1)
        self.assertEqual(app.toast_mark(), start + 2)
        app.toast("drei")
        self.assertEqual(app.toast_mark(), start + 3)
        self.assertEqual(app.toast_mark(), start + 3)


class PushOhneParameterTest(N15Basis):
    """A-N15-02 (K2): ohne Parameter wie bisher - offener Hinweis zu, ein
    page.update je Seitenwechsel."""

    def test_push_schliesst(self):
        app = self.app
        self.addCleanup(self.drop_views)
        app.toast("alt")
        snack = app._toast
        before = len(app.page.updates)
        app.push(("A", "B"), self.main.ft.Column())
        self.assertFalse(snack.open)
        self.assertEqual(len(app.page.updates) - before, 1)

    def test_zurueck_und_reiter_schliessen(self):
        app = self.app
        self.addCleanup(self.drop_views)
        app.push(("A", "B"), self.main.ft.Column())
        app.toast("alt")
        snack = app._toast
        app._view_popped(None)
        self.assertFalse(snack.open)
        app.toast("alt 2")
        snack = app._toast
        app._show_tab(app.tab)
        self.assertFalse(snack.open)


class PushMitParameterTest(N15Basis):
    """A-N15-03 (K3): nur Hinweise mit kleinerer Nummer werden geschlossen."""

    def test_grenzen(self):
        app = self.app
        self.addCleanup(self.drop_views)
        for offset, expect_open in ((-1, True), (0, True), (1, False)):
            app.toast("Hinweis %d" % offset)
            snack, number = app._toast, app._toast_nr
            app.push(("A", "B"), self.main.ft.Column(), toast_bis=number + offset)
            self.assertEqual(snack.open, expect_open, offset)
            if expect_open:
                self.assertIs(app._toast, snack)               # kein zweiter Hinweis
                self.assertEqual(snack.duration, self.main.TOAST_MS)
            self.drop_views()

    def test_ohne_offenen_hinweis(self):
        app = self.app
        self.addCleanup(self.drop_views)
        app.close_toast()
        app.push(("A", "B"), self.main.ft.Column(), toast_bis=app.toast_mark())
        self.assertIsNone(app._toast)


class DetailHinweisTest(N15Basis):
    """A-N15-04/-05/-06 (K4, K5): Szenarien und Testprojekte."""

    WRITERS = (("scenarios", "log_scenario"), ("ap1scenarios", "log_ap1"),
               ("testproject", "log_project"))

    def test_schreibfehler_bleibt_offen(self):
        for key, writer in self.WRITERS:
            with self.subTest(key):
                screen = self.app.screens[key]
                self.addCleanup(self.drop_views)
                screen.pending = 0                       # _flush schreibt
                self.events.clear()
                with self.db_error(writer):
                    screen.open_detail(1)
                self.assertEqual(len(self.toasts()), 1, self.events)
                self.assertTrue(self.app._toast is not None and self.app._toast.open,
                                "%s: Hinweis nach push geschlossen" % key)
                # Detailseite wird nach dem Hinweis gezeichnet (push -> page.update)
                self.assertIn(("page_update",), self.events[self.toast_index() + 1:])
                self.drop_views()

    def test_alter_hinweis_wird_geschlossen(self):
        for key, _writer in self.WRITERS:
            with self.subTest(key):
                screen = self.app.screens[key]
                self.addCleanup(self.drop_views)
                screen.pending = None
                self.app.toast("Gespeichert")
                snack = self.app._toast
                screen.open_detail(0)
                self.assertFalse(snack.open, key)
                self.drop_views()


def _find_click(control, default):
    """Steuerelement mit on_click=lambda _e, k=<default>: ... (Kachel)."""
    stack = [control]
    while stack:
        item = stack.pop()
        handler = getattr(item, "on_click", None)
        if handler is not None and getattr(handler, "__defaults__", None) == (default,):
            return handler
        for name in ("content", "controls"):
            child = getattr(item, name, None)
            if isinstance(child, list):
                stack.extend(child)
            elif child is not None and not isinstance(child, str):
                stack.append(child)
    return None


class SeitenwechselHinweisTest(N15Basis):
    """Weisung zu Meldung 41, Abschnitt 16, Frage 17: HA3-HA9. Ein Hinweis aus
    dem Ereignis vor dem Seitenwechsel (open) bleibt offen; aeltere schliesst
    open weiter. Testname test_ha<n>_..."""

    def setUp(self):
        super().setUp()
        self.app.close_toast()
        self.drop_views()
        self.addCleanup(self.drop_views)
        self.cards = self.app.screens["cards"]
        self.addCleanup(setattr, self.cards, "pending", None)

    def pending_card(self):
        """Karteikarte aufgedeckt, nicht bewertet: _flush schreibt (log_card)."""
        card = self.cards.cards[0]
        self.cards.pending = card
        return card["q"]

    def assert_open(self, text=DB_TEXT):
        self.assertEqual(len(self.toasts(text)), 1, self.events)
        snack = self.app._toast
        self.assertTrue(snack is not None and snack.open,
                        "Hinweis nach dem Seitenwechsel geschlossen: %r" % self.events)
        self.assertIn(text, snack.content.value)

    def failing_on_show(self, key):
        app = self.app
        return mock.patch.object(app.screens[key], "on_show",
                                 lambda: app.db.error_handler(DB_TEXT))

    def test_ha3_open_on_show(self):
        """open liest die Nummer vor on_show (Pruefungstrainer schreibt dort)."""
        with self.failing_on_show("quiz"):
            self.app.open("quiz")
        self.assert_open()

    def test_ha4_lernen_kachel(self):
        app = self.app
        app.show_tab("learn")
        self.addCleanup(app.show_tab, "dashboard")
        click = _find_click(app.screens["learn"].root, "quiz")
        self.assertIsNotNone(click, "Kachel Pruefungstrainer nicht gefunden")
        self.events.clear()
        with self.failing_on_show("quiz"):
            click(None)
        self.assert_open()

    def test_ha5_notizblock_karten(self):
        key = self.pending_card()
        with self.db_error("log_card"):
            self.app.screens["notebook"].practice(self.main.SRC_CARD, [key])
        self.assert_open()

    def test_ha5_notizblock_pruefung_laeuft(self):
        """Hinweis "Es laeuft gerade eine Pruefung ..." bleibt nach open stehen."""
        fp, quiz = self.main.fp, self.app.screens["quiz"]
        quiz.mode_pills.select_value("pruefung", notify=False)
        self.addCleanup(quiz.mode_pills.select_value, "uebung", False)
        self.addCleanup(setattr, quiz.exam, "state", None)
        fp.save_running(fp.new_exam(fp.WISO, [], seed=5))
        self.addCleanup(fp.clear_running)
        question = quiz.questions[0]["q"]
        self.app.screens["notebook"].practice(self.main.SRC_QUIZ, [question])
        self.assert_open("Es läuft gerade eine Prüfung")

    def test_ha6_open_cards(self):
        self.pending_card()
        with self.db_error("log_card"):
            self.app.open_cards("Alle")
        self.assert_open()

    def test_ha7_suchtreffer_karte(self):
        key = self.pending_card()
        with self.db_error("log_card"):
            self.app.open_search_hit("Karteikarte", key)
        self.assert_open()

    def test_ha8_start_review(self):
        key = self.pending_card()

        class Plan:
            def first_source(self):
                return "card_source"

            def session(self, _source):
                return [key]
        with mock.patch.object(self.main, "SRC_CARD", "card_source"), \
                mock.patch.object(self.main.ReviewPlan, "from_db", lambda _db: Plan()), \
                self.db_error("log_card"):
            self.app.start_review()
        self.assert_open()

    def test_ha9_practice_part(self):
        key = self.pending_card()
        with self.db_error("log_card"):
            self.app._practice_part([(self.main.SRC_CARD, [key])])
        self.assert_open()

    def test_testnamen_wie_stellen(self):
        names = sorted(name.split("_")[1] for name in dir(self) if name.startswith("test_ha"))
        self.assertEqual(sorted(set(names)), ["ha%d" % n for n in range(3, 10)])

    def test_alter_hinweis_wird_geschlossen(self):
        """Schutz: ein Hinweis von vorher schliesst open weiter (ohne und mit
        mitgegebener Nummer)."""
        app = self.app
        app.toast("alt")
        snack = app._toast
        app.open("cards")
        self.assertFalse(snack.open)
        self.drop_views()
        app.toast("alt 2")
        snack = app._toast
        app.open_cards("Alle")
        self.assertFalse(snack.open)


def _parse(path):
    with open(path, encoding="utf-8") as handle:
        return ast.parse(handle.read())


def _callers(path):
    """(Klasse, Funktion, aufgerufen) fuer push/open/show_tab/_show_tab mit
    Empfaenger self oder self.app, in Reihenfolge der Datei."""
    tree = _parse(path)
    rows = []
    for cls in [node for node in tree.body if isinstance(node, ast.ClassDef)]:
        for func in [node for node in cls.body if isinstance(node, ast.FunctionDef)]:
            for node in ast.walk(func):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr in ("push", "open", "show_tab", "_show_tab")
                        and ast.unparse(node.func.value) in ("self", "self.app")):
                    rows.append((cls.name, func.name, node.func.attr, node))
    rows.sort(key=lambda row: row[3].lineno)
    return rows


# Aufrufer von push/open/show_tab (K6). "ja" = schreibt im selben Ereignis vor
# dem Seitenwechsel (Beleg in bau_0.63.2/n15/aufrufer_push_open.md).
# "nummer": gibt toast_bis mit (Weisung zu Meldung 41, Abschnitt 16: SP1-SP6,
# HA3-HA9). "selbst": der Seitenwechsel open liest die Nummer selbst am Anfang
# (HA4, Lernen-Kachel ohne Schreiben davor).
AUFRUFER = [
    ("main", "LearnScreen", "build", "open", "selbst"),           # HA4: on_show quiz
    ("main", "ScenarioScreen", "open_detail", "push", "nummer"),
    ("main", "ProjectScreen", "open_detail", "push", "nummer"),
    ("main", "ProjectScreen", "use_as_template", "open", "nein"),
    ("main", "NotebookScreen", "practice", "open", "nummer"),     # HA5
    ("main", "NotebookScreen", "practice", "open", "nummer"),     # HA5
    ("main", "SettingsScreen", "show_license", "push", "nein"),
    ("main", "SettingsScreen", "show_notices", "push", "nein"),
    ("main", "FISIMobileApp", "__init__", "show_tab", "nein"),     # A12 sammelt
    ("main", "FISIMobileApp", "_appbar", "open", "nein"),
    ("main", "FISIMobileApp", "_nav_changed", "show_tab", "nein"),
    ("main", "FISIMobileApp", "show_tab", "_show_tab", "nein"),
    ("main", "FISIMobileApp", "open", "push", "nummer"),          # HA3: on_show vor push
    ("main", "FISIMobileApp", "open_cards", "open", "nummer"),    # HA6
    ("main", "FISIMobileApp", "open_help", "open", "nein"),
    ("main", "FISIMobileApp", "open_search_hit", "show_tab", "nein"),
    ("main", "FISIMobileApp", "open_search_hit", "open", "nummer"),   # HA7
    ("main", "FISIMobileApp", "open_search_hit", "open", "nummer"),   # HA7
    ("main", "FISIMobileApp", "open_achievements", "show_tab", "nein"),
    ("main", "FISIMobileApp", "open_achievements", "show_tab", "nein"),
    ("main", "FISIMobileApp", "start_review", "open", "nummer"),  # HA8
    ("main", "FISIMobileApp", "_practice_part", "open", "nummer"),    # HA9
    ("spiel", "GameScreen", "open_picker", "show_tab", "nein"),
    ("spiel", "GameScreen", "open_ticket", "push", "nein"),
    ("spiel", "GameScreen", "open_site", "push", "nummer"),       # SP3 (SP1 Parameter)
    ("spiel", "GameScreen", "run_action", "open", "nein"),
    ("spiel", "GameScreen", "open_journey", "push", "nummer"),    # SP2
    ("spiel", "GameScreen", "open_firm", "push", "nummer"),       # SP4
    ("spiel", "GameScreen", "open_farm", "push", "nummer"),       # SP5
    ("spiel", "GameScreen", "open_farm_task", "push", "nein"),
    ("spiel", "GameScreen", "_open_raid", "open", "nein"),
    ("spiel", "GameScreen", "_open_cards", "open", "nummer"),     # SP6
]


class AufruferListeTest(unittest.TestCase):
    """A-N15-07 (K6): Aufrufer-Liste aus dem Quelltext = Liste im Test; jeder
    Aufrufer mit "nummer" gibt toast_bis mit, kein anderer."""

    def test_liste(self):
        found = []
        for name, path in (("main", MAIN_PY), ("spiel", SPIEL_PY)):
            for cls, func, called, node in _callers(path):
                keywords = [keyword.arg for keyword in node.keywords]
                found.append(((name, cls, func, called), "toast_bis" in keywords))
        self.assertEqual([row for row, _kw in found], [row[:4] for row in AUFRUFER])
        for (row, has_mark), expected in zip(found, AUFRUFER):
            self.assertEqual(has_mark, expected[4] == "nummer", row)

    def test_nummer_am_anfang(self):
        """K4: open_detail liest die Nummer als Erstes (vor _flush)."""
        tree = _parse(MAIN_PY)
        for cls in [node for node in tree.body if isinstance(node, ast.ClassDef)
                    and node.name in ("ScenarioScreen", "ProjectScreen")]:
            func = [node for node in cls.body if isinstance(node, ast.FunctionDef)
                    and node.name == "open_detail"][0]
            first = ast.unparse(func.body[0])
            self.assertEqual(first, "mark = self.app.toast_mark()", cls.name)

    def test_nummer_am_anfang_seitenwechsel(self):
        """SP1-SP6, HA3-HA9: jede Funktion mit "nummer" liest die Nummer als
        erste Anweisung (nach dem Docstring), vor jedem Schreiben."""
        expected = {
            ("main", "FISIMobileApp", "open"):
                "mark = self.toast_mark() if toast_bis is None else toast_bis",
            ("spiel", "GameScreen", "open_site"):
                "mark = self.app.toast_mark() if toast_bis is None else toast_bis"}
        for name, path in (("main", MAIN_PY), ("spiel", SPIEL_PY)):
            for cls in [node for node in _parse(path).body if isinstance(node, ast.ClassDef)]:
                for func in [node for node in cls.body if isinstance(node, ast.FunctionDef)]:
                    row = (name, cls.name, func.name)
                    if not any(entry[:3] == row and entry[4] == "nummer"
                               for entry in AUFRUFER):
                        continue
                    body = func.body
                    if ast.get_docstring(func) is not None:
                        body = body[1:]
                    own = "mark = self.toast_mark()" if (
                        name == "main" and cls.name == "FISIMobileApp") else \
                        "mark = self.app.toast_mark()"
                    with self.subTest(row=row):
                        self.assertEqual(ast.unparse(body[0]), expected.get(row, own))

    def test_feierabend_gibt_nummer_an_open_site(self):
        """SP1: Feierabend liest die Nummer vor end_day und gibt sie open_site mit."""
        tree = _parse(SPIEL_PY)
        func = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
                and node.name == "run_action"][0]
        branch = [node for node in ast.walk(func) if isinstance(node, ast.If)
                  and ast.unparse(node.test) == "action == 'feierabend'"][0]
        self.assertEqual(ast.unparse(branch.body[0]), "mark = self.app.toast_mark()")
        calls = [ast.unparse(node) for node in ast.walk(ast.Module(branch.body, []))
                 if isinstance(node, ast.Call) and ast.unparse(node.func) == "self.open_site"]
        self.assertEqual(calls, ["self.open_site('zuhause', replace=True, toast_bis=mark)"])


# ============================================================================
#  N-b  Z7 im Spiel
# ============================================================================

# Bestandsaufnahme (K20): jeder self.game.<m>(-Aufruf in spiel.py in Reihenfolge
# der Datei: (Funktion, Methode, Befund). Befund: "liest" (kein Schreibweg),
# "haengt" (Ereignis endet ohne Zeichnen -> _redraw am Ende), "update" (das
# Ereignis zeichnet selbst: page.update/confirm/push/_show_tab). Begruendung je
# Zeile in bau_0.63.2/n15/ergebnis.md.
BESTAND = [
    ("on_show", "reload", "update"), ("on_show", "check_knowledge", "update"),
    ("slot_bar", "active_label", "liest"), ("_choose_slot", "select_run", "update"),
    ("_new_slot", "new_run", "update"), ("_enter_slot", "check_knowledge", "update"),
    ("_delete_slot", "delete_run", "update"), ("_rename_slot", "rename_slot", "update"),
    ("_slot_picker", "slots", "liest"), ("_profile_editor", "active_label", "liest"),
    ("_save_profile", "set_profile", "haengt"), ("_overview", "knowledge", "liest"),
    ("_decide_here", "decide", "haengt"), ("open_ticket", "topic_knowledge", "liest"),
    ("_submit", "solve", "haengt"), ("_order_spare", "order_spare", "update"),
    ("_defer", "defer", "update"), ("_close", "reload", "update"),
    ("open_site", "reload", "update"), ("run_action", "end_day", "update"),
    ("open_journey", "reload", "update"), ("open_journey", "check_knowledge", "update"),
    ("_achievements", "records", "liest"), ("_achievements", "topic_knowledge", "liest"),
    ("open_firm", "reload", "update"), ("_firm_auftraege", "firm_levels", "liest"),
    ("_delegate", "delegate", "haengt"), ("_firm_projekte", "firm_levels", "liest"),
    ("_toggle_member", "toggle_project_member", "haengt"), ("_found", "found_firm", "update"),
    ("_train", "train", "haengt"), ("_decide", "decide", "haengt"),
    ("_coach", "coach", "update"), ("_fire", "fire", "update"),
    ("_hire", "hire", "haengt"), ("_open_branch", "open_branch", "update"),
    ("_expand_branch", "expand_branch", "update"), ("_transfer", "transfer", "haengt"),
    ("_build_room", "build_room", "update"), ("_expand", "expand", "update"),
    ("_book_ad", "book_ad", "update"), ("_stop_ad", "stop_ad", "update"),
    ("_start_cert", "start_cert", "update"), ("_take_loan", "take_loan", "update"),
    ("_take_loan", "take_loan", "update"), ("_repay_loan", "repay_loan", "update"),
    ("_home_tap", "place_furniture_at", "haengt"), ("_rotate", "rotate_furniture", "haengt"),
    ("_nudge", "nudge_furniture", "haengt"), ("_undo", "restore_layout", "haengt"),
    ("_box", "box_furniture", "haengt"), ("_sell", "sell_furniture", "update"),
    ("_buy", "buy_furniture", "haengt"), ("_floor", "set_floor", "haengt"),
    ("_move", "move_home", "update"), ("open_farm", "reload", "update"),
    ("_fill_farm", "topic_knowledge", "liest"), ("_farm_changed", "reload", "update"),
    ("_farm_start", "farm_start", "update"),
    ("_farm_toggle_member", "farm_toggle_member", "haengt"),
    ("open_farm_task", "topic_knowledge", "liest"), ("_farm_submit", "farm_solve", "haengt"),
    ("_farm_close", "reload", "update"),
]
# _farm_changed: von _farm_start (confirm) und _farm_toggle_member (haengt,
# dort gezeichnet) aufgerufen; das Zeichnen steht am Ende des Ereignisses.
HAENGT = sorted({func for func, _method, finding in BESTAND if finding == "haengt"})


def _game_calls(path):
    tree = _parse(path)
    rows = []
    for cls in [node for node in tree.body if isinstance(node, ast.ClassDef)]:
        for func in [node for node in cls.body if isinstance(node, ast.FunctionDef)]:
            for node in ast.walk(func):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and ast.unparse(node.func.value) == "self.game"):
                    rows.append((node.lineno, func.name, node.func.attr))
    return [row[1:] for row in sorted(rows)]


def _gamescreen_methods(path):
    tree = _parse(path)
    cls = [node for node in tree.body if isinstance(node, ast.ClassDef)
           and node.name == "GameScreen"][0]
    return {node.name: node for node in cls.body if isinstance(node, ast.FunctionDef)}


class BestandTest(unittest.TestCase):
    """A-N15-20 (K20) und K26: Aufrufliste = Tabelle; _redraw nur am Ende der
    haengenden Ereignisse, sonst nirgends in GameScreen."""

    def test_aufrufliste_wie_tabelle(self):
        self.assertEqual(_game_calls(SPIEL_PY), [row[:2] for row in BESTAND])

    def test_zeichnen_nur_am_ende_der_haengenden_stellen(self):
        methods = _gamescreen_methods(SPIEL_PY)
        with_redraw = {}
        for name, func in methods.items():
            calls = [node for node in ast.walk(func) if isinstance(node, ast.Call)
                     and isinstance(node.func, ast.Name) and node.func.id == "_redraw"]
            if calls:
                with_redraw[name] = len(calls)
        self.assertEqual(sorted(with_redraw), HAENGT)
        for name in HAENGT:
            self.assertEqual(with_redraw[name], 1, name)
            body = methods[name].body
            last = body[-1]
            if isinstance(last, ast.Return):
                last = body[-2]
            self.assertEqual(ast.unparse(last).split("(")[0], "_redraw",
                             "%s: _redraw nicht am Ende" % name)

    def test_hilfsfunktion_woertlich_wie_main(self):
        """B6: spiel._redraw ist woertlich main._redraw."""
        def function(path):
            found = [node for node in _parse(path).body if isinstance(node, ast.FunctionDef)
                     and node.name == "_redraw"]
            self.assertEqual(len(found), 1, path)
            return found[0]
        self.assertEqual(ast.dump(function(SPIEL_PY)), ast.dump(function(MAIN_PY)))


@unittest.skipUnless(_flet_ok(), "flet fehlt")
class HilfsfunktionGleichTest(unittest.TestCase):
    """B6: beide Hilfsfunktionen tun dasselbe (Verhalten, nicht nur Text)."""

    def test_gleiches_verhalten(self):
        main, spiel, _app_ = _app()

        class Control:
            def __init__(self, error=None):
                self.error, self.calls = error, 0

            def update(self):
                self.calls += 1
                if self.error:
                    raise self.error

        for error in (None, RuntimeError("ohne Seite"), AssertionError(), AttributeError()):
            counts = []
            for redraw in (main._redraw, spiel._redraw):
                first, second = Control(error), Control()
                redraw(first, second)
                counts.append((first.calls, second.calls))
            self.assertEqual(counts[0], counts[1], error)
            self.assertEqual(counts[0], (1, 1), error)
        for redraw in (main._redraw, spiel._redraw):
            with self.assertRaises(ValueError):
                redraw(Control(ValueError("anderer Fehler")))


def _quick_content():
    """Ein Auftrag, keine Zwischenfaelle - schnell eine Firma (wie
    test_spiel_abgabe._farm_content)."""
    import fisi_game as fg
    content = json.loads(json.dumps(fg.GAME))
    content["aufgaben"] = content["aufgaben"][:1]
    content["zwischenfaelle"] = []
    return content


class Board:
    """Testdoppel fuer die Eingabe eines Tickets (get/complete/answer/reveal)."""

    def __init__(self, answer):
        self.selected = answer if not isinstance(answer, dict) else None
        self.answer = dict(answer) if isinstance(answer, dict) else {}
        self.revealed = []

    def get(self):
        return self.selected

    def complete(self):
        return True

    def reveal(self, *args):
        self.revealed.append(args)


class SpielBasis(N15Basis):
    """Echte Spielseite (GameScreen) der App, mit eigenem Spiel auf einer
    Wegwerf-Datenbank (Fehlerweg wie die App: error_handler -> Hinweis)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        import fisi_core
        import fisi_game as fg
        cls.fg = fg
        cls.screen = cls.app.screens["game"]
        cls.saved_game = cls.screen.game
        if "spielstand" not in _SHARED:
            # Einmal fuer alle Spiel-Tests: Firma mit laufender Serverfarm
            db = fisi_core.DBManager(os.path.join(tempfile.mkdtemp(), "spiel_n15.db"),
                                     error_handler=cls.app.db.error_handler)
            _SHARED["spielstand"] = (db, _farm_game(db))
        cls.db, cls.game = _SHARED["spielstand"]
        cls.home_game = cls.game
        cls.app.slot_chosen = True

    @classmethod
    def tearDownClass(cls):
        cls.screen.game = cls.saved_game
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.screen.game = self.game
        self.addCleanup(self.drop_views)

    def game_error(self, name, result=None):
        """Die Spiel-Methode schreibt, und das Schreiben meldet einen Fehler:
        Hinweis ueber error_handler, Spielstand unveraendert (wie Game._log,
        wenn db.log_game_event scheitert)."""
        game = self.screen.game

        def failing(*_args, **_kwargs):
            game.db.error_handler(DB_TEXT)
            return result
        return mock.patch.object(game, name, failing)

    def run_handler(self, method, call, result=None):
        self.events.clear()
        with self.game_error(method, result):
            call()
        self.assertEqual(len(self.toasts()), 1, self.events)

    def open_firm(self):
        self.screen.open_firm()
        self.events.clear()

    def open_home(self):
        screen = self.screen
        screen.open_site("zuhause")
        screen.editing = True
        screen.selected = next(iter(screen.game.state.furniture))
        screen.undo = []
        self.events.clear()


class SpielZeichnenTest(SpielBasis):
    """A-N15-21 (K21, K22): je haengender Stelle ein Testfall
    (Testname test_stelle_<Ereignis>)."""

    # -- Spielstand/Uebersicht ------------------------------------------------
    def test_stelle__save_profile(self):
        self.screen.render()
        self.run_handler("set_profile", lambda: self.screen._save_profile("Neu", {}))
        self.assert_drawn_after_toast(self.screen.root, "_save_profile")

    def test_stelle__decide_here(self):
        self.screen.render()
        self.run_handler("decide", lambda: self.screen._decide_here("d1", "a"))
        self.assert_drawn_after_toast(self.screen.root, "_decide_here")

    # -- Firma ------------------------------------------------------------------
    def _firm_case(self, name, method, call):
        self.open_firm()
        self.run_handler(method, call)
        self.assert_drawn_after_toast(self.screen.root, name)
        self.assert_drawn_after_toast(self.screen.firm_box, name)

    def test_stelle__delegate(self):
        self._firm_case("_delegate", "delegate", lambda: self.screen._delegate("t1", "p1"))

    def test_stelle__toggle_member(self):
        self._firm_case("_toggle_member", "toggle_project_member",
                        lambda: self.screen._toggle_member("p1", "m1"))

    def test_stelle__train(self):
        self._firm_case("_train", "train", lambda: self.screen._train("m1", "ziel"))

    def test_stelle__decide(self):
        self._firm_case("_decide", "decide", lambda: self.screen._decide("d1", "a"))

    def test_stelle__hire(self):
        self._firm_case("_hire", "hire", lambda: self.screen._hire("b1"))

    def test_stelle__transfer(self):
        self._firm_case("_transfer", "transfer",
                        lambda: self.screen._transfer({"id": "m1"}, self.fg.SITE_BRANCH))

    # -- Zuhause (Einrichten) ---------------------------------------------------
    def _home_case(self, name, method, call, result=None):
        self.screen.game = self.home_game
        self.open_home()
        self.run_handler(method, call, result)
        self.assert_drawn_after_toast(self.screen.office, name)

    def _free_cell(self):
        state = self.screen.game.state
        for y in range(1, 40):
            for x in range(1, 40):
                if not self.fg.furniture_at(state, x + 0.5, y + 0.5):
                    return x + 0.5, y + 0.5
        self.fail("kein freies Feld")

    def test_stelle__home_tap(self):
        def call():
            self.assertTrue(self.screen._home_tap(*self._free_cell()))
        self._home_case("_home_tap", "place_furniture_at", call)

    def test_stelle__rotate(self):
        self._home_case("_rotate", "rotate_furniture", self.screen._rotate, result=1)

    def test_stelle__nudge(self):
        self._home_case("_nudge", "nudge_furniture", lambda: self.screen._nudge(1, 0))

    def test_stelle__undo(self):
        def call():
            state = self.screen.game.state
            self.screen.undo = [(state.home_id, self.fg.home_layout(state))]
            self.screen._undo()
        self._home_case("_undo", "restore_layout", call)

    def test_stelle__box(self):
        self._home_case("_box", "box_furniture", self.screen._box)

    def test_stelle__floor(self):
        def call():
            state = self.screen.game.state
            room = self.fg.apartment(state.home_id)["gebaeude"]["raeume"][0]["id"]
            self.screen._floor(room, kind="fliesen")
        self._home_case("_floor", "set_floor", call)

    def test_stelle__buy(self):
        piece = self.fg.shop_items()[0]["id"]
        self._home_case("_buy", "buy_furniture", lambda: self.screen._buy(piece),
                        result=piece)

    # -- Ticket und Serverfarm --------------------------------------------------
    def _ticket(self, game):
        screen = self.screen
        screen.game = game
        task = game.state.open_tickets()[0]
        screen.open_ticket(task["id"])
        screen.options = Board(self.fg.find_solution(task, screen.available))
        self.events.clear()
        return task

    def test_stelle__submit(self):
        """Echter Weg: game.solve laeuft, db.log_game_event scheitert."""
        game = self.fg.Game(self.db, "Handy")
        self.addCleanup(game.select_run, self.game.run)
        game.new_run(3)
        game.set_profile("Ticket", {})
        self._ticket(game)
        with self.db_error("log_game_event", db=self.db):
            self.screen._submit()
        self.assertEqual(len(self.toasts()), 1, self.events)
        for control in (self.screen.result_box, self.screen.buttons):
            self.assert_drawn_after_toast(control, "_submit")

    def test_stelle__farm_toggle_member(self):
        self.screen.open_farm()
        self.events.clear()
        self.run_handler("farm_toggle_member", lambda: self.screen._farm_toggle_member("m1"))
        self.assert_drawn_after_toast(self.screen.farm_box, "_farm_toggle_member")

    def test_stelle__farm_submit(self):
        """Echter Weg mit laufender Serverfarm (wie test_spiel_abgabe._farm_game)."""
        fg = self.fg
        game = self.game
        screen = self.screen
        task = [item for item in fg.farm_open_tasks(game.state)
                if not fg.farm_task_problem(game.state, item["id"])][0]
        screen.open_farm_task(task["id"])
        markup = fg.farm_markups()[0]
        screen.farm_markup = markup
        answer = (fg.find_solution(fg.farm_offer_task(markup))
                  if task["typ"] == fg.FARM_OFFER_TYPE else fg.farm_solution(task))
        screen.options = Board(answer)
        self.events.clear()
        with self.db_error("log_game_event", db=self.db):
            screen._farm_submit()
        self.assertEqual(len(self.toasts()), 1, self.events)
        for control in (screen.result_box, screen.buttons):
            self.assert_drawn_after_toast(control, "_farm_submit")

    def test_testnamen_wie_stellen(self):
        """Tabelle der Testnamen = Tabelle der haengenden Stellen."""
        names = sorted(name[len("test_stelle_"):] for name in dir(self)
                       if name.startswith("test_stelle_"))
        self.assertEqual(names, HAENGT)


def _farm_game(db):
    """Firma Stufe 4 mit Serverraum, Zertifikaten, 3 Leuten und laufender
    Serverfarm (wie test_spiel_abgabe._farm_game)."""
    import fisi_game as fg
    content = _quick_content()
    task = content["aufgaben"][0]
    game = fg.Game(db, "Handy", content)
    game.set_profile("Farm", {})
    db.log_game_event(fg.EV_SOLVED, json.dumps(
        {"aufgabe": task["id"], "tag": 1, "richtig": True, "geld": 400000,
         "reputation": {key: 60 for key in fg.AXIS_KEYS}}), "Handy", game.run)
    game.reload()
    game.found_firm("Test IT")
    while game.state.firm["stufe"] < 4:
        game.expand()
    game.build_room("serverraum")
    for cert in ("iso27001", "netzwerk"):
        db.log_game_event(fg.EV_CERT, json.dumps({"zert": cert, "tag": game.state.day,
                                                  "bis_tag": game.state.day, "geld": 0}),
                          "Handy", game.run)
    game.reload()
    for _ in range(3):
        game.hire(fg.applicants(game.state, content)[0]["id"])
    for decision in game.state.open_decisions():
        option = next(item for item in decision["optionen"] if not item.get("problem"))
        game.decide(decision["id"], option["id"])
    game.end_day()
    game.farm_start()
    game.farm_set_team([item["id"] for item in game.state.staff_list()][:3])
    return game


class SpielEchterWegTest(SpielBasis):
    """K22, echter Schreibweg fuer Zuhause: die Spiel-Methode laeuft wirklich,
    db.log_game_event scheitert (Stichprobe neben den Testfaellen oben)."""

    def test_boden_und_kaufen(self):
        screen = self.screen
        screen.game = self.home_game
        for name, call in (
                ("_floor", lambda: screen._floor(
                    self.fg.apartment(screen.game.state.home_id)["gebaeude"]["raeume"][0]["id"],
                    kind="fliesen")),
                ("_buy", lambda: screen._buy(self.fg.shop_items()[0]["id"]))):
            self.open_home()
            with self.db_error("log_game_event", db=self.db):
                call()
            self.assertEqual(len(self.toasts()), 1, (name, self.events))
            self.assert_drawn_after_toast(screen.office, name)


class SpielSeitenwechselTest(SpielBasis):
    """Weisung zu Meldung 41, Abschnitt 16: SP1-SP6. Ein Hinweis aus dem
    Schreiben vor dem Seitenwechsel im Spiel bleibt offen. Testname test_sp<n>_..."""

    def setUp(self):
        super().setUp()
        self.app.close_toast()
        self.events.clear()

    def assert_open(self):
        self.assertEqual(len(self.toasts()), 1, self.events)
        snack = self.app._toast
        self.assertTrue(snack is not None and snack.open,
                        "Hinweis nach dem Seitenwechsel geschlossen: %r" % self.events)

    def test_sp1_feierabend(self):
        with self.game_error("end_day", result={"tag": 2, "gehalt": 0}):
            self.screen.run_action("feierabend")
        self.assert_open()

    def test_sp2_reise(self):
        with self.game_error("check_knowledge"):
            self.screen.open_journey()
        self.assert_open()

    def test_sp3_ort(self):
        with self.game_error("reload"):
            self.screen.open_site("buero")
        self.assert_open()

    def test_sp4_firma(self):
        with self.game_error("reload"):
            self.screen.open_firm()
        self.assert_open()

    def test_sp5_farm(self):
        with self.game_error("reload"):
            self.screen.open_farm()
        self.assert_open()

    def test_sp6_karteikarten(self):
        cards = self.app.screens["cards"]
        self.addCleanup(setattr, cards, "pending", None)
        cards.pending = cards.cards[0]
        with self.db_error("log_card"):
            self.screen._open_cards("Alle")
        self.assert_open()

    def test_testnamen_wie_stellen(self):
        names = {name.split("_")[1] for name in dir(self) if name.startswith("test_sp")}
        self.assertEqual(sorted(names), ["sp%d" % n for n in range(1, 7)])

    def test_alter_hinweis_wird_geschlossen(self):
        """Schutz: ein Hinweis von vorher schliesst der Seitenwechsel weiter."""
        for call in (lambda: self.screen.open_site("buero"), self.screen.open_firm):
            self.app.toast("alt")
            snack = self.app._toast
            call()
            self.assertFalse(snack.open)
            self.drop_views()

    def test_sp1_parameter_alter_hinweis(self):
        """SP1-Parameter: mit mitgegebener Nummer schliesst open_site nur
        aeltere Hinweise (die Nummer vom Anfang gilt, nicht eine eigene)."""
        self.app.toast("alt")                      # vor dem Ereignis
        old = self.app._toast
        self.screen.open_site("zuhause", toast_bis=self.app.toast_mark())
        self.assertFalse(old.open)
        self.drop_views()
        mark = self.app.toast_mark()               # Anfang des Ereignisses
        self.app.toast(DB_TEXT)                    # Hinweis aus dem Ereignis
        new = self.app._toast
        self.screen.open_site("zuhause", toast_bis=mark)
        self.assertTrue(new.open, "open_site nimmt die mitgegebene Nummer nicht an")


# ============================================================================
#  N-h  Subnetting-Blaettern: gesperrte Pfeile gedaempft
# ============================================================================

PROBE_NETZ = ("10.0.0.0/8", "256")           # 32 Seiten wie die Foto-Probe

# Nico 14b (Meldung 39): gesperrte Pfeile in Lila/Magenta und Blau/Tuerkis hell
# = C["muted"] zu 40 % zur Karte (#FFFFFF) gemischt. Feste Sollwerte je
# Hintergrund (unabhaengig vom Code nachgerechnet, Tabelle im Ergebnis N15,
# Nachtrag 14b). Alle anderen Faelle: C["muted"] unveraendert.
SOLL_14B = {"violett": "#A49BB8", "nachtblau": "#9AA3B9", "tannengruen": "#94A7A0",
            "aubergine": "#B098A7", "anthrazit": "#9D9DA5", "schwarz": "#9B9BA2"}
GEAENDERT_14B = ("lila_magenta", "blau_tuerkis")


def soll_gesperrt():
    """Sollfarbe gesperrter Pfeile fuer den aktuellen Farbstand."""
    import fisi_theme
    mode = fisi_theme.current_mode
    eigene = fisi_theme.custom_colors.get(mode)
    eigene = bool(eigene) and eigene != fisi_theme.custom_start(mode)
    if (mode == fisi_theme.MODE_LIGHT and not eigene
            and fisi_theme.current_preset in GEAENDERT_14B):
        return SOLL_14B[fisi_theme.current_background]
    return fisi_theme.C["muted"]
GROSS_NETZ = ("2001:db8:abcd::/48", "65536")  # 8.192 Seiten (main.selftest)


@unittest.skipUnless(_flet_ok(), "flet fehlt")
class BlaetterFarbeTest(N15Basis):

    def setUp(self):
        super().setUp()
        self.calc = self.app.screens["calc"]

    def panel(self, mode, net, count):
        panel = self.calc.subnet_panels[(mode, "aufteilen")]
        panel["net"].value, panel["count"].value = net, count
        self.calc.calc_split(mode)
        return panel

    def check(self, panel, label):
        C = self.main.C
        pages, page = panel["result"]["seiten"], panel["page"]
        for where, button in panel["page_buttons"].items():
            locked = page == 1 if where in ("first", "back") else page == pages
            self.assertEqual(button.disabled, locked, (label, where))
            self.assertEqual(button.icon_color, soll_gesperrt() if locked else C["accent"],
                             (label, where, page, pages))

    def test_seiten_direkt(self):
        """A-N15-40 (K40): Seite 1, Mitte, letzte; beide Modi."""
        for mode, (net, count) in (("ipv4", PROBE_NETZ), ("ipv6", GROSS_NETZ)):
            panel = self.panel(mode, net, count)
            pages = panel["result"]["seiten"]
            self.assertGreater(pages, 2)
            for page in (1, pages // 2, pages):
                panel["page"] = page
                self.calc._paint_pager(panel)
                self.check(panel, (mode, page))

    def test_ereignisse(self):
        """A-N15-41 (K41): Pfeile, Sprung, Neuberechnung."""
        panel = self.panel("ipv4", *PROBE_NETZ)
        self.check(panel, "neu")
        for where in ("next", "last", "back", "first"):
            self.calc.subnet_page("ipv4", where)
            self.check(panel, where)
        if panel["jump"] is not None:
            for number in ("1", "16", "32"):
                panel["jump"].value = number
                self.calc.subnet_jump("ipv4")
                self.assertEqual(panel["page"], int(number))
                self.check(panel, "Sprung " + number)
        self.calc.subnet_page("ipv4", "last")
        panel["count"].value = "4"                        # eine Seite: Blaettern weg
        self.calc.calc_split("ipv4")
        self.assertFalse(panel["pager"].visible)
        panel["count"].value = PROBE_NETZ[1]
        self.calc.calc_split("ipv4")                     # wieder Seite 1 von 32
        self.check(panel, "zurueck auf mehrere Seiten")

    def test_gleiche_regel_wie_listen(self):
        """A-N15-42 (K42): Ergebnis je Zustand wie _paint_page_buttons."""
        ft = self.main.ft
        panel = self.panel("ipv4", *PROBE_NETZ)
        pages = panel["result"]["seiten"]
        for page in (1, 2, pages):
            panel["page"] = page
            self.calc._paint_pager(panel)
            prev, forward = ft.IconButton(ft.Icons.CHEVRON_LEFT), ft.IconButton(ft.Icons.CHEVRON_RIGHT)
            self.main._paint_page_buttons(prev, forward, page - 1, pages)
            self.assertEqual(panel["page_buttons"]["back"].icon_color, prev.icon_color, page)
            self.assertEqual(panel["page_buttons"]["first"].icon_color, prev.icon_color, page)
            self.assertEqual(panel["page_buttons"]["next"].icon_color, forward.icon_color, page)
            self.assertEqual(panel["page_buttons"]["last"].icon_color, forward.icon_color, page)

    def test_farbsaetze(self):
        """A-N15-43 (K43): alle Grundfarben hell und dunkel (Farben aus C zur
        Laufzeit); je Darstellung zusaetzlich nach dem Neuaufbau (_build_ui)
        wie beim Farbwechsel in den Optionen."""
        import fisi_theme
        main = self.main
        saved = (fisi_theme.current_preset, fisi_theme.current_mode)
        seen = set()
        try:
            for mode in fisi_theme.MODE_IDS:
                for number, preset in enumerate(fisi_theme.PRESET_IDS):
                    fisi_theme.apply_mode(mode)
                    fisi_theme.apply_preset(preset)
                    if number == len(fisi_theme.PRESET_IDS) - 1:
                        self.app._build_ui()
                        self.calc = self.app.screens["calc"]
                    panel = self.panel("ipv4", *PROBE_NETZ)
                    self.check(panel, (preset, mode))
                    seen.add((main.C["muted"], main.C["accent"]))
        finally:
            fisi_theme.apply_mode(saved[1])
            fisi_theme.apply_preset(saved[0])
            self.app._build_ui()
        self.assertEqual(len(seen), len(fisi_theme.PRESET_IDS) * len(fisi_theme.MODE_IDS))


# ============================================================================
#  Nico 14b (Meldung 39): gesperrt und frei unterscheidbar in allen Farbwelten
# ============================================================================

# Mindestabstand gesperrt <-> frei (CIE76, fisi_theme.color_distance). 29 =
# knapp unter dem kleinsten Abstand, den die Messung K44 als gut sichtbar
# zeigte (Blau/Tuerkis dunkel 29,7); Nico sah 17,1/17,5 als zu schwach.
MIN_ABSTAND = 29.0
# Fuer die geaenderten Faelle zusaetzlich: WCAG-Kontrast gesperrt <-> frei
# (vorher 1,00 bis 1,28:1) und gesperrt auf der Karte (Pfeil bleibt sichtbar)
MIN_KONTRAST_14B = 1.9
MIN_KARTE_14B = 2.4
# Bekannte Grenze (nicht Teil von 14b, an Nico gemeldet): unveraenderte
# Farbwelten hell mit anderem Hintergrund unter MIN_ABSTAND (Messwert).
UNTER_MIN_UNVERAENDERT = {
    ("cyan_pink", "tannengruen"): 18.6, ("gruen_lime", "tannengruen"): 21.2,
    ("cyan_pink", "anthrazit"): 24.4, ("rot_pink", "aubergine"): 24.5,
    ("cyan_pink", "schwarz"): 24.6, ("cyan_pink", "nachtblau"): 25.1,
}


@unittest.skipUnless(_flet_ok(), "flet fehlt")
class PfeilFarbe14bTest(N15Basis):

    def setUp(self):
        super().setUp()
        import fisi_theme
        self.theme = fisi_theme
        self.calc = self.app.screens["calc"]
        saved = (fisi_theme.current_preset, fisi_theme.current_background,
                 fisi_theme.current_mode, dict(fisi_theme.custom_colors))

        def restore():
            fisi_theme.custom_colors.clear()
            fisi_theme.custom_colors.update(saved[3])
            fisi_theme.apply_mode(saved[2])
            fisi_theme.apply_background(saved[1])
            fisi_theme.apply_preset(saved[0])
        self.restore = restore
        self.addCleanup(restore)
        panel = self.calc.subnet_panels[("ipv4", "aufteilen")]
        panel["net"].value, panel["count"].value = PROBE_NETZ
        self.calc.calc_split("ipv4")
        self.panel = panel

    def welt(self, preset, background, mode):
        self.theme.apply_mode(mode)
        self.theme.apply_background(background)
        self.theme.apply_preset(preset)

    def farben(self):
        """(gesperrt, frei) aus der Oberflaeche: Rechner-Blaettern auf Seite 1
        und Handy-Liste (_paint_page_buttons) auf Seite 1; beide gleich."""
        ft = self.main.ft
        panel = self.panel
        panel["page"] = 1
        self.calc._paint_pager(panel)
        buttons = panel["page_buttons"]
        self.assertTrue(buttons["back"].disabled and not buttons["next"].disabled)
        prev, forward = ft.IconButton(ft.Icons.CHEVRON_LEFT), ft.IconButton(ft.Icons.CHEVRON_RIGHT)
        self.main._paint_page_buttons(prev, forward, 0, 3)
        self.assertEqual((prev.icon_color, forward.icon_color),
                         (buttons["back"].icon_color, buttons["next"].icon_color))
        self.assertEqual(buttons["first"].icon_color, buttons["back"].icon_color)
        self.assertEqual(buttons["last"].icon_color, buttons["next"].icon_color)
        return buttons["back"].icon_color, buttons["next"].icon_color

    def alle(self):
        for mode in self.theme.MODE_IDS:
            for background in self.theme.BACKGROUND_IDS:
                for preset in self.theme.PRESET_IDS:
                    yield preset, background, mode

    def test_14b_geaenderte_faelle(self):
        """Lila/Magenta und Blau/Tuerkis hell, je Hintergrund: Sollfarbe,
        Mindestabstand, Kontrast gesperrt<->frei und auf der Karte."""
        t = self.theme
        for preset in GEAENDERT_14B:
            for background in t.BACKGROUND_IDS:
                self.welt(preset, background, t.MODE_LIGHT)
                gesperrt, frei = self.farben()
                name = (preset, background)
                self.assertEqual(gesperrt, SOLL_14B[background], name)
                self.assertEqual(frei, t.C["accent"], name)
                self.assertGreaterEqual(t.color_distance(gesperrt, frei), MIN_ABSTAND, name)
                self.assertGreaterEqual(t.contrast(gesperrt, frei), MIN_KONTRAST_14B, name)
                self.assertGreaterEqual(t.contrast(gesperrt, t.C["card"]), MIN_KARTE_14B, name)

    def test_unveraenderte_farbwelten_gleich(self):
        """Alle anderen Faelle (dunkel; hell in den vier anderen Grundfarben)
        gesperrt genau C["muted"] wie gebaut, frei C["accent"]."""
        n = 0
        for preset, background, mode in self.alle():
            if mode == self.theme.MODE_LIGHT and preset in GEAENDERT_14B:
                continue
            self.welt(preset, background, mode)
            self.assertEqual(self.farben(), (self.theme.C["muted"], self.theme.C["accent"]),
                             (preset, background, mode))
            n += 1
        self.assertEqual(n, 60)

    def test_mindestabstand_alle_farbwelten(self):
        """Alle Grundfarben x Hintergruende x hell/dunkel: Abstand gesperrt <->
        frei mindestens MIN_ABSTAND; Ausnahmen nur die gemessene, gemeldete
        Liste UNTER_MIN_UNVERAENDERT (genau diese, Wert auf 0,1 genau)."""
        t = self.theme
        unter = {}
        for preset, background, mode in self.alle():
            self.welt(preset, background, mode)
            gesperrt, frei = self.farben()
            abstand = t.color_distance(gesperrt, frei)
            if abstand < MIN_ABSTAND:
                self.assertEqual(mode, t.MODE_LIGHT, (preset, background, mode, abstand))
                unter[(preset, background)] = round(abstand, 1)
        self.assertEqual(unter, UNTER_MIN_UNVERAENDERT)

    def test_standard_hintergrund_ohne_ausnahme(self):
        """Hintergrund Violett/Flieder (Standard, Messung K44 und Fotos):
        alle sechs Grundfarben hell und dunkel ohne Ausnahme >= MIN_ABSTAND."""
        t = self.theme
        for mode in t.MODE_IDS:
            for preset in t.PRESET_IDS:
                self.welt(preset, "violett", mode)
                gesperrt, frei = self.farben()
                self.assertGreaterEqual(t.color_distance(gesperrt, frei), MIN_ABSTAND,
                                        (preset, mode))

    def test_eigene_farben_unveraendert(self):
        """Eigene Farben (Regler verschoben) in Lila/Magenta hell: C["muted"]."""
        t = self.theme
        self.welt("lila_magenta", "violett", t.MODE_LIGHT)
        values = t.custom_start(t.MODE_LIGHT)
        h, s, l = values["akzent1"]
        values["akzent1"] = ((h + 20) % 360, s, l)
        t.apply_custom(t.MODE_LIGHT, values)
        self.assertTrue(t.custom_colors.get(t.MODE_LIGHT))
        self.assertEqual(self.farben(), (t.C["muted"], t.C["accent"]))
        # Regler auf dem Startwert = Farbwelt exakt ("sanft") -> wie 14b
        t.apply_custom(t.MODE_LIGHT, t.custom_start(t.MODE_LIGHT))
        self.assertEqual(self.farben()[0], SOLL_14B["violett"])

    def test_nach_neuaufbau(self):
        """Nach dem Neuaufbau (_build_ui, wie beim Farbwechsel): Liste einer
        Ansicht (PagedListBox) und Rechner zeigen die neue Farbe."""
        t = self.theme
        try:
            for preset in ("lila_magenta", "blau_tuerkis", "cyan_pink"):
                self.welt(preset, "violett", t.MODE_LIGHT)
                self.app._build_ui()
                self.calc = self.app.screens["calc"]
                panel = self.calc.subnet_panels[("ipv4", "aufteilen")]
                panel["net"].value, panel["count"].value = PROBE_NETZ
                self.calc.calc_split("ipv4")
                self.panel = panel
                soll = SOLL_14B["violett"] if preset in GEAENDERT_14B else t.C["muted"]
                self.assertEqual(self.farben()[0], soll, preset)
                main = self.main
                items = [{"title": "Aufgabe %d" % n, "cat": main.CATEGORIES[0], "theme": "T"}
                         for n in range(2 * main.fc.LIST_PAGE_SIZE + 1)]
                box = main.PagedListBox(items, lambda _p: None, subtitle=lambda item: "",
                                        status_source=dict)
                box.refresh()
                self.assertEqual((box.btn_prev.icon_color, box.btn_next.icon_color),
                                 (soll, t.C["accent"]), preset)
        finally:
            self.restore()
            self.app._build_ui()


if __name__ == "__main__":
    unittest.main(verbosity=2)
