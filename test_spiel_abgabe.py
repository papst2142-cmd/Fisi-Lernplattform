#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test ab 0.62.5 (B-A-04): Abgabe einer Antwort im Spiel, am PC und am Handy.

Geprueft wird der Abgabeweg genau so, wie ihn die Oberflaechen gehen:
  PC     fisi_game_gui.GameView._submit / _show_result   (Tickets)
         fisi_game_gui.FarmView._submit / _show_result   (Firmenauftraege)
  Handy  mobile/src/spiel.py GameScreen._submit           (Tickets)
         mobile/src/spiel.py GameScreen._farm_submit      (Firmenauftraege)

Die echten Methoden laufen auf einem kleinen Ersatz-Objekt (statt der ganzen
Ansicht) gegen ein echtes Spiel auf einer Wegwerf-Datenbank. Fuer JEDE
Aufgabenart (Auswahl, alle Problemarten, Zuordnung; bei der Serverfarm auch
Angebot und Bestueckung) wird geprueft:
  1. leere Eingabe: Hinweis, kein Spielereignis, nicht als beantwortet
     markiert; Hinweistext am PC und am Handy gleich
  2. richtige Antwort: genau ein Spielereignis (EV_SOLVED bzw.
     EV_FARM_TASK) mit "richtig", reveal mit dem passenden Wert (Signatur
     gegen die echte Eingabe-Klasse dieser Art geprueft), Fortschritt
     gemeldet, Ergebnis mit Ergebnis- und Erklaerungstext angezeigt
  3. zweites Einreichen: nichts passiert (kein Ereignis, kein Hinweis)
  4. Ticket nicht mehr offen (ValueError): Hinweistext, kein Absturz
  5. je eine falsche Antwort (Auswahl und eine Problemart): "falsch",
     reveal(False) bzw. reveal(richtige Antwort)

Grenze (offen genannt): Die Eingabe-Felder selbst (Klicken in Rack,
Formular, Terminal ...) werden hier nicht bedient; an ihrer Stelle steht ein
Testdoppel mit get/complete/answer/reveal. Das Zeichnen des Ergebnisses
laeuft echt (PC: CustomTkinter-Rahmen, Handy: Flet-Bausteine ohne Seite).

fisi_game_gui.py und mobile/src/spiel.py werden nur gelesen (importiert),
nie geaendert. Fuer die Gegenprobe kann der Code-Ordner umgestellt werden:
    ABGABE_CODE=<ordner mit dem Code> python test_spiel_abgabe.py

Braucht eine Anzeige (unter Linux xvfb-run, wie pruefung/ci_tests.sh).
Start:  python test_spiel_abgabe.py
"""

import inspect
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("ABGABE_CODE") or HERE)
sys.path.insert(0, CODE)
sys.path.insert(1, os.path.join(CODE, "mobile", "src"))

import fisi_core as core   # noqa: E402
import fisi_game as fg     # noqa: E402

# Eingabe-Klasse je Aufgabenart, wie in GameView._build_ticket /
# FarmView._build_board (PC) und GameScreen (Handy) - nur fuer die Pruefung
# der reveal-Signatur.
BOARD_CLASS = {"bauteile": "SlotBoard", "bestellung": "OrderBoard", "rack": "RackBoard",
               "formular": "FormBoard", "terminal": "TerminalBoard",
               "diagnose": "DiagnoseBoard", "wartung": "MaintenanceBoard",
               "bestueckung": "FitBoard", "angebot": "FormBoard",
               "zuordnung": "MatchBoard"}
TICKET_TYPES = {"auswahl", "bauteile", "bestellung", "rack", "formular", "terminal",
                "diagnose", "wartung", "zuordnung"}


class Board:
    """Testdoppel fuer die Eingabe-Felder. reveal() prueft die Argumente
    gegen die echte Klasse dieser Aufgabenart."""

    def __init__(self, real_cls, answer, filled):
        self.real_cls = real_cls
        self.filled = filled
        self.selected = answer if not isinstance(answer, dict) else None
        self.answer = dict(answer) if isinstance(answer, dict) else {}
        self.revealed = []

    def get(self):
        return self.selected if self.filled else None

    def complete(self):
        return self.filled

    def reveal(self, *args):
        inspect.signature(self.real_cls.reveal).bind(None, *args)
        self.revealed.append(args)


class App:
    def __init__(self):
        self.progress = []
        self.search = []

    def notify_progress(self, **kwargs):
        self.progress.append(kwargs)

    def open_search_hit(self, kind, title):
        self.search.append((kind, title))


class MessageBox:
    """Ersatz fuer tkinter.messagebox im PC-Modul (nur waehrend des Tests)."""

    def __init__(self):
        self.shown = []

    def showwarning(self, title, text):
        self.shown.append(("warning", title, text))

    def showinfo(self, title, text):
        self.shown.append(("info", title, text))


def _farm_content():
    content = json.loads(json.dumps(fg.GAME))
    content["aufgaben"] = content["aufgaben"][:1]
    content["zwischenfaelle"] = []
    return content


def _farm_game(db, device):
    """Firma mit Stufe 4, Serverraum, Zertifikaten, 3 Leuten und laufender
    Serverfarm (wie test_spiel.ServerfarmTest._ready/_play)."""
    content = _farm_content()
    task = content["aufgaben"][0]
    game = fg.Game(db, device, content)
    game.set_profile("Test", {})
    db.log_game_event(fg.EV_SOLVED, json.dumps(
        {"aufgabe": task["id"], "tag": 1, "richtig": True, "geld": 400000,
         "reputation": {key: 60 for key in fg.AXIS_KEYS}}), device, game.run)
    game.reload()
    game.found_firm("Test IT")
    while game.state.firm["stufe"] < 4:
        game.expand()
    game.build_room("serverraum")
    for cert in ("iso27001", "netzwerk"):
        db.log_game_event(fg.EV_CERT, json.dumps({"zert": cert, "tag": game.state.day,
                                                  "bis_tag": game.state.day, "geld": 0}),
                          device, game.run)
    game.reload()
    for _ in range(3):
        game.hire(fg.applicants(game.state, content)[0]["id"])
    _end_farm_day(game)
    game.farm_start()
    game.farm_set_team([item["id"] for item in game.state.staff_list()][:3])
    return game


def _end_farm_day(game):
    for decision in game.state.open_decisions():
        option = next(item for item in decision["optionen"] if not item.get("problem"))
        game.decide(decision["id"], option["id"])
    return game.end_day()


def _texts_tk(widget):
    out = []
    try:
        text = widget.cget("text")
        if text:
            out.append(str(text))
    except Exception:
        pass
    for child in widget.winfo_children():
        out.extend(_texts_tk(child))
    return out


def _texts_ft(control):
    out = []
    value = getattr(control, "value", None)
    if isinstance(value, str) and value:
        out.append(value)
    for name in ("content", "controls"):
        item = getattr(control, name, None)
        if isinstance(item, list):
            for child in item:
                out.extend(_texts_ft(child))
        elif item is not None and not isinstance(item, str):
            out.extend(_texts_ft(item))
    return out


class _Base(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="fisi abgabe ")
        self.dbs = []
        self.hints = {}     # (art, Fall) -> Text, je Seite in self.hints_side

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def _db(self, name):
        return core.DBManager(os.path.join(self.folder, name + ".db"))

    def _events(self, game, kind):
        return [event for event in game.db.game_events(game.run) if event[1] == kind]

    def expected_reveal(self, kind, task, payload):
        if kind == "auswahl":
            return (task["antwort"],)
        if kind in fg.PROBLEM_TYPES or kind == fg.FARM_OFFER_TYPE:
            return (payload["richtig"],)
        return ()

    # -- ein Durchgang je Seite -------------------------------------------------

    def play_tickets(self, side):
        """Spielt Tickets, bis jede Art einmal richtig ueber die Oberflaeche
        abgegeben wurde; Auswahl und eine Problemart zusaetzlich einmal falsch."""
        game = fg.Game(self._db("tickets_" + side.name), side.device)
        game.set_profile("Test", {})
        game.reload()
        done, wrong = {}, set()
        for _day in range(250):
            for task in game.state.open_tickets():
                task = game.state.prepared_task(task)
                kind = task["typ"]
                available = game.state.available_parts(task)
                answer = fg.find_solution(task, available)
                if task.get("austausch") and answer["teil"] not in available:
                    game.order_spare(task["id"], answer["teil"])
                    continue
                if kind not in done:
                    self.check_ticket(side, game, task, answer, available, right=True)
                    done[kind] = task["id"]
                elif kind not in wrong and kind in ("auswahl", "rack") \
                        and not task.get("zwischenfall"):
                    bad = [o for o in task["optionen"] if o != task["antwort"]][0] \
                        if kind == "auswahl" else {}
                    self.check_ticket(side, game, task, bad, available, right=False)
                    wrong.add(kind)
                else:
                    game.solve(task["id"], answer, False)
            if set(done) >= TICKET_TYPES and wrong == {"auswahl", "rack"}:
                break
            if game.state.all_done():
                break
            game.end_day()
        self.assertEqual(set(done), TICKET_TYPES, "%s: nicht alle Arten erreicht" % side.name)
        self.assertEqual(wrong, {"auswahl", "rack"}, side.name)
        return done

    def check_ticket(self, side, game, task, answer, available, right):
        kind = task["typ"]
        label = "%s Ticket %s (%s)" % (side.name, task["id"], kind)
        before = len(self._events(game, fg.EV_SOLVED))
        # 1. leere Eingabe
        view = side.ticket_view(game, task, Board(side.board_cls(kind), answer, False),
                                available)
        side.submit(view, task)
        self.assertFalse(view.answered, label)
        self.assertEqual(len(self._events(game, fg.EV_SOLVED)), before, label)
        hint = side.last_hint()
        self.assertTrue(hint, label)
        self.hints.setdefault(side.name, {})[("leer", kind)] = hint
        # 2. Antwort einreichen
        view = side.ticket_view(game, task, Board(side.board_cls(kind), answer, True),
                                available)
        side.submit(view, task)
        self.assertTrue(view.answered, label)
        events = self._events(game, fg.EV_SOLVED)
        self.assertEqual(len(events), before + 1, label)
        payload = events[-1][2]
        self.assertEqual(payload["aufgabe"], task["id"], label)
        self.assertIs(bool(payload["richtig"]), right, label)
        self.assertEqual(view.options.revealed,
                         [self.expected_reveal(kind, task, payload)], label)
        self.assertEqual(len(view.app.progress), 1, label)
        texts = side.result_texts(view)
        self.assertIn(fg.result_text(task, payload, available), texts, label)
        self.assertIn(task["erklaerung"], texts, label)
        # 3. zweites Einreichen: nichts passiert (auch kein Hinweis)
        hints = side.hint_count()
        side.submit(view, task)
        self.assertEqual(side.hint_count(), hints, label)
        self.assertEqual(len(self._events(game, fg.EV_SOLVED)), before + 1, label)
        self.assertEqual(len(view.options.revealed), 1, label)
        self.assertEqual(len(view.app.progress), 1, label)
        # 4. Ticket ist nicht mehr offen
        if right and kind == "auswahl" and ("offen", "auswahl") not in \
                self.hints.get(side.name, {}):
            view = side.ticket_view(game, task, Board(side.board_cls(kind), answer, True),
                                    available)
            side.submit(view, task)
            self.assertFalse(view.answered, label)
            self.assertEqual(len(self._events(game, fg.EV_SOLVED)), before + 1, label)
            self.hints[side.name][("offen", "auswahl")] = side.last_hint()
            self.assertEqual(side.last_hint(), "Dieses Ticket ist heute nicht (mehr) offen.")
            side.check_closed(view)

    def play_farm(self, side):
        game = _farm_game(self._db("farm_" + side.name), side.device)
        done = {}
        for _day in range(80):
            if game.state.farm["fertig"]:
                break
            for task in fg.farm_open_tasks(game.state):
                if fg.farm_task_problem(game.state, task["id"]):
                    break
                self.check_farm(side, game, task)
                done.setdefault(task["typ"], []).append(task["id"])
            _end_farm_day(game)
        self.assertTrue(game.state.farm["fertig"], side.name)
        self.assertEqual(sorted(done), sorted(set(t["typ"] for t in fg.farm_tasks())),
                         side.name)
        self.assertEqual(sum(len(ids) for ids in done.values()), len(fg.farm_tasks()))
        return done

    def check_farm(self, side, game, task):
        kind = task["typ"]
        label = "%s Serverfarm %s (%s)" % (side.name, task["id"], kind)
        markup = fg.farm_markups()[0]
        if kind == fg.FARM_OFFER_TYPE:
            answer = fg.find_solution(fg.farm_offer_task(markup))
        else:
            answer = fg.farm_solution(task)
        before = len(self._events(game, fg.EV_FARM_TASK))
        view = side.farm_view(game, task, Board(side.board_cls(kind), answer, False), markup)
        side.farm_submit(view, task)
        self.assertFalse(view.answered, label)
        self.assertEqual(len(self._events(game, fg.EV_FARM_TASK)), before, label)
        self.hints.setdefault(side.name, {})[("farm-leer", kind)] = side.last_hint()
        self.assertTrue(side.last_hint(), label)

        view = side.farm_view(game, task, Board(side.board_cls(kind), answer, True), markup)
        side.farm_submit(view, task)
        self.assertTrue(view.answered, label)
        events = self._events(game, fg.EV_FARM_TASK)
        self.assertEqual(len(events), before + 1, label)
        payload = events[-1][2]
        self.assertTrue(payload["richtig"], label)
        self.assertEqual(view.options.revealed,
                         [self.expected_reveal(kind, task, payload)], label)
        self.assertEqual(len(view.app.progress), 1, label)
        head, _text = fg.farm_result_text(game.state, payload)
        texts = side.result_texts(view)
        self.assertIn(head, texts, label)
        self.assertIn(task["erklaerung"], texts, label)
        hints = side.hint_count()
        side.farm_submit(view, task)
        self.assertEqual(side.hint_count(), hints, label)
        self.assertEqual(len(self._events(game, fg.EV_FARM_TASK)), before + 1, label)
        self.assertEqual(len(view.options.revealed), 1, label)


# ============================================================================
#  Seiten: PC (CustomTkinter) und Handy (Flet)
# ============================================================================

class PCSide:
    name = "PC"
    device = "PC"

    def __init__(self, root):
        import fisi_game_gui as gg
        import fisi_widgets
        self.gg = gg
        self.root = root
        self.box = MessageBox()
        self._old_box = gg.messagebox
        gg.messagebox = self.box
        self.widgets = fisi_widgets

    def restore(self):
        self.gg.messagebox = self._old_box

    def board_cls(self, kind):
        if kind == "auswahl":
            return self.gg.OptionList
        return getattr(self.gg, BOARD_CLASS[kind])

    def _frames(self, view):
        view.result_box = self.gg.ctk.CTkFrame(self.root)
        view.controls = self.gg.ctk.CTkFrame(self.root)

    def ticket_view(self, game, task, board, available):
        gg = self.gg
        cls = type("PCTicket", (), {"_submit": gg.GameView._submit,
                                     "_show_result": gg.GameView._show_result,
                                     "_open_learn": gg.GameView._open_learn})
        view = cls()
        view.game, view.options, view.available = game, board, available
        view.used_help, view.answered, view.return_to = False, False, None
        view.ticket = task["id"]
        view.app = App()
        view.closed = []
        view._close_ticket = lambda: view.closed.append(True)
        self._frames(view)
        return view

    def farm_view(self, game, task, board, markup):
        gg = self.gg
        cls = type("PCFarm", (), {"_submit": gg.FarmView._submit,
                                   "_show_result": gg.FarmView._show_result,
                                   "_open_learn": gg.FarmView._open_learn})
        view = cls()
        view.game, view.options, view.markup, view.task = game, board, markup, task
        view.used_help, view.answered = False, False
        view.app = App()
        view.closed = []
        view._close = lambda: view.closed.append(True)
        self._frames(view)
        return view

    def submit(self, view, task):
        view._submit(task)

    farm_submit = submit

    def last_hint(self):
        return self.box.shown[-1][2] if self.box.shown else None

    def hint_count(self):
        return len(self.box.shown)

    def result_texts(self, view):
        self.root.update_idletasks()
        return _texts_tk(view.result_box) + _texts_tk(view.controls)

    def check_closed(self, view):
        if view.closed != [True]:
            raise AssertionError("PC: Ticket nach Fehler nicht geschlossen")


class HandySide:
    name = "Handy"
    device = "Handy"

    def __init__(self):
        import flet as ft
        import spiel
        self.ft = ft
        self.spiel = spiel
        self.toasts = []

    def restore(self):
        pass

    def board_cls(self, kind):
        if kind == "auswahl":
            return self.spiel.ui.OptionList
        return getattr(self.spiel, BOARD_CLASS[kind])

    def _view(self, game, task, board):
        sp, ft = self.spiel, self.ft
        cls = type("HandyScreen", (), {"_submit": sp.GameScreen._submit,
                                        "_farm_submit": sp.GameScreen._farm_submit})
        view = cls()
        view.game, view.options, view.task = game, board, task
        view.used_help, view.answered = False, False
        view.app = App()
        view.toast = lambda text, _color=None: self.toasts.append(text)
        view.result_box = ft.Column()
        view.buttons = ft.Column()
        view.from_site = None
        view._close = view._farm_close = view._open_learn = lambda *_a: None
        return view

    def ticket_view(self, game, task, board, available):
        view = self._view(game, task, board)
        view.available = available
        return view

    def farm_view(self, game, task, board, markup):
        view = self._view(game, task, board)
        view.farm_markup = markup
        return view

    def submit(self, view, _task):
        view._submit()

    def farm_submit(self, view, _task):
        view._farm_submit()

    def last_hint(self):
        return self.toasts[-1] if self.toasts else None

    def hint_count(self):
        return len(self.toasts)

    def result_texts(self, view):
        return _texts_ft(view.result_box) + _texts_ft(view.buttons)

    def check_closed(self, view):
        pass


# ============================================================================
#  Tests
# ============================================================================

class SpielAbgabeTest(_Base):
    @classmethod
    def setUpClass(cls):
        import customtkinter as ctk
        import fisi_widgets
        cls.root = ctk.CTk()     # ohne Anzeige: Fehler (Test wird nie uebersprungen)
        cls.root.withdraw()
        fisi_widgets.setup_fonts(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def _both(self, play):
        sides = [PCSide(self.root), HandySide()]
        try:
            return {side.name: play(side) for side in sides}
        finally:
            for side in sides:
                side.restore()

    def test_tickets_alle_arten(self):
        result = self._both(self.play_tickets)
        print("\nTickets je Art (PC):", result["PC"])
        print("Tickets je Art (Handy):", result["Handy"])
        self.assertEqual(self.hints["PC"], self.hints["Handy"],
                         "Hinweistexte PC und Handy verschieden")

    def test_serverfarm_alle_arten(self):
        result = self._both(self.play_farm)
        print("\nServerfarm je Art (PC):", {k: len(v) for k, v in result["PC"].items()})
        self.assertEqual(self.hints["PC"], self.hints["Handy"],
                         "Hinweistexte PC und Handy verschieden")


if __name__ == "__main__":
    unittest.main(verbosity=2)
