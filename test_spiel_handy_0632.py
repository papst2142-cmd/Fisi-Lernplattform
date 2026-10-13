#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test ab 0.63.2 (N3): Spiel am Handy, Knoepfe der Firma und Spiel-Terminal.

B-E-08  Knoepfe in der Firma brechen als Reihe um, jeder Knopf in seiner
        Textbreite (vorher gleich breit nebeneinander, "Weiterbi", "Entlasse",
        "Angebot kalku", "-5.00("); Tilgungsplan in Spalten ohne Umbruch und
        ohne Abschneiden, waagrecht wischbar, wenn er nicht passt.
B-N-04  Spiel-Terminal: jede Zeile einzeilig (no_wrap) in einem waagrecht
        wischbaren Bereich, Ein- und Ausgabe wachsen gleich mit der Schrift;
        Befehlsknoepfe duerfen umbrechen.

Geprueft wird der Steuerelement-Baum der echten Handy-Ansicht
(mobile/src/spiel.py, GameScreen mit einem echten Spiel auf einer
Wegwerf-Datenbank, ohne Seite). Die gezeichneten Breiten (Textbreite <=
Knopfbreite in der Handy-Nachbildung 384/412 px) misst das Werkzeug der
Belege (bau_0.63.2/n3/werkzeug), nicht dieser Test.

Fuer die Gegenprobe kann der Code-Ordner umgestellt werden:
    SPIEL_HANDY_CODE=<ordner mit dem Code> python test_spiel_handy_0632.py
Vorher einmal: python mobile/vorbereiten.py
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("SPIEL_HANDY_CODE") or HERE)
sys.path.insert(0, CODE)
sys.path.insert(1, os.path.join(CODE, "mobile", "src"))

import fisi_core as core   # noqa: E402
import fisi_game as fg     # noqa: E402
import flet as ft          # noqa: E402
import ui                  # noqa: E402
import spiel as sp         # noqa: E402

FACTOR = ui.FONT_FACTOR[0]


class App:
    """Ersatz fuer die Handy-App (nur was GameScreen beim Aufbau braucht)."""

    def __init__(self, db):
        self.db = db
        self.slot_chosen = True
        self.page = None

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


def walk(control):
    """Alle Steuerelemente unter control (Tiefensuche, Reihenfolge wie im Baum)."""
    yield control
    for name in ("controls", "content"):
        value = getattr(control, name, None)
        if isinstance(value, list):
            for child in value:
                yield from walk(child)
        elif isinstance(value, ft.Control):
            yield from walk(value)


def captions(row):
    return [item.caption.value for item in getattr(row, "controls", None) or []
            if isinstance(item, ui.GradientButton)]


def button_rows(controls, wanted):
    rows = []
    for root in controls:
        for item in walk(root):
            if isinstance(item, ft.Row) and set(captions(item)) == set(wanted):
                rows.append(item)
    return rows


class Base(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="n3_test_")
        self.db = core.DBManager(os.path.join(self.tmp, "h.db"))
        self.screen = sp.GameScreen(App(self.db))
        self.game = self.screen.game

    def tearDown(self):
        ui.set_font_factor(FACTOR)
        self.db.close() if hasattr(self.db, "close") else None
        shutil.rmtree(self.tmp, ignore_errors=True)

    def firm(self):
        """Figur, alle Auftraege erledigt, Firma, eine Person, ein Grosskredit
        (wie die Foto-Belege)."""
        game, db = self.game, self.db
        game.set_profile("Pruefer", {})
        goal = game.content["balancing"]["gruendung"]
        for number, task in enumerate(game.content["aufgaben"]):
            data = {"aufgabe": task["id"], "tag": number + 1, "richtig": True, "geld": 0,
                    "reputation": {}}
            if number == 0:
                data["geld"] = goal["startkapital"] + 10000
                data["reputation"] = {key: 90 for key in fg.AXIS_KEYS}
            db.log_game_event(fg.EV_SOLVED, json.dumps(data), "Handy", game.run)
            db.log_game_event(fg.EV_DAY_END, json.dumps({"tag": number + 1, "gehalt": 0}),
                              "Handy", game.run)
        game.reload()
        game.found_firm("Pruef IT")
        game.hire(fg.applicants(game.state, game.content)[0]["id"])
        package = fg.loan_rules(game.content)["pakete"][-1]
        offer = fg.loan_offer(game.state, package["summe"], package["laufzeit"], package,
                              game.content)
        db.log_game_event(fg.EV_LOAN, json.dumps({
            "kredit": "%s%d:1" % (fg.LOAN_PREFIX, game.state.day), "tag": game.state.day,
            "name": offer["name"], "paket": offer["paket"], "summe": offer["summe"],
            "laufzeit": offer["laufzeit"], "zins": offer["zins"], "rate": offer["rate"]}),
            "Handy", game.run)
        game.reload()
        self.assertTrue(game.state.staff and game.state.loans)
        return game.state


class FirmButtonsTest(Base):
    """B-E-08: Knopfreihen der Firma umbrechen, Knoepfe in Textbreite."""

    def assert_wrapped(self, rows, wanted):
        self.assertTrue(rows, "Knopfreihe %s nicht gefunden" % (wanted,))
        for row in rows:
            self.assertTrue(row.wrap, "Reihe %s bricht nicht um" % (wanted,))
            for button in row.controls:
                self.assertFalse(button.expand, "%s ist gleich breit gestreckt"
                                 % button.caption.value)
                self.assertIsNone(button.alignment, "%s fuellt die Zeile statt der "
                                  "Textbreite" % button.caption.value)

    def test_mitarbeiter(self):
        state = self.firm()
        wanted = ("Weiterbilden", "Themen", "Entlassen")
        self.assert_wrapped(button_rows(self.screen._firm_mitarbeiter(state), wanted), wanted)

    def test_kredite_betraege_und_tilgungsplan(self):
        state = self.firm()
        self.screen.plans_for = set(state.loans)
        controls = self.screen._firm_kredite(state)
        wanted = ("−5.000", "−1.000", "+1.000", "+5.000")
        self.assert_wrapped(button_rows(controls, wanted), wanted)
        wanted = ("Plan ausblenden", "Ablösen")
        self.assert_wrapped(button_rows(controls, wanted), wanted)
        self.screen.plans_for = set()
        wanted = ("Tilgungsplan", "Ablösen")
        self.assert_wrapped(button_rows(self.screen._firm_kredite(state), wanted), wanted)

    def test_ausschreibung(self):
        state = self.firm()
        tenders = state.tenders()
        self.assertTrue(tenders, "keine Ausschreibung im Spielstand")
        box = self.screen._tender_box(state, tenders[0], None)
        wanted = ("Angebot kalkulieren", "Details")
        self.assert_wrapped(button_rows([box], wanted), wanted)
        # mit Grund (gesperrt) bleibt die Reihe gleich
        box = self.screen._tender_box(state, tenders[0], "Grund")
        self.assert_wrapped(button_rows([box], wanted), wanted)


class LoanPlanTest(Base):
    """B-E-08: Tilgungsplan in Spalten, Zellen ohne Umbruch, wischbar."""

    def plan(self):
        state = self.firm()
        item = fg.loan_status(state, state.running_loans()[0])
        rows, skipped = fg.loan_plan_rows(item)
        self.assertTrue(skipped, "Testfall braucht die Zeile '… weitere Raten …'")
        return item, rows, skipped, self.screen._loan_plan(item)

    def test_zellen_einzeilig_und_vollstaendig(self):
        item, rows, skipped, plan = self.plan()
        values = {"%d" % row[0] for row in rows} | {sp.euro(v) for row in rows for v in row[1:]}
        texts = [c for c in walk(plan) if isinstance(c, ft.Text)]
        shown = {c.value for c in texts}
        for value in values | {"Tag", "Rate", "Zinsen", "Tilgung", "Rest"}:
            self.assertIn(value, shown, "Betrag fehlt: %s" % value)
        for text in texts:
            if text.value in values or text.value in ("Tag", "Rate", "Zinsen", "Tilgung",
                                                       "Rest"):
                self.assertTrue(text.no_wrap, "Zelle bricht um: %s" % text.value)
                self.assertFalse(text.expand, "Zelle gleich breit gestreckt: %s" % text.value)

    def test_wischbar_und_reihenfolge(self):
        item, rows, skipped, plan = self.plan()
        scrolls = [c for c in walk(plan) if isinstance(c, ft.Row) and c.scroll]
        self.assertEqual(len(scrolls), 1, "Tabelle nicht waagrecht wischbar")
        # Reihenfolge wie vorher: Kopf, Zeilen, "… n weitere Raten …", letzte Zeile,
        # danach der Hinweis zu den Zinsen (ausserhalb des Wischbereichs)
        table = scrolls[0].controls[0]
        first, gap, last = table.controls
        self.assertEqual(gap.value, "… %d weitere Raten …" % skipped)
        self.assertEqual([c.value for c in first.controls[0].controls[:-1]],
                         ["Tag"] + ["%d" % row[0] for row in rows[:-1]])
        self.assertEqual([c.value for c in last.controls[4].controls[:-1]],
                         [sp.euro(rows[-1][4])])
        self.assertTrue(plan.controls[-1].value.startswith("Noch zu zahlende Zinsen"))
        # beide Bloecke: 5 Spalten, rechtsbuendig; die unsichtbare Zeile (Hoehe 0)
        # traegt alle Werte der Spalte, damit beide Bloecke gleich breit sind
        for block in (first, last):
            self.assertEqual(len(block.controls), 5)
            for index, column in enumerate(block.controls):
                self.assertEqual(column.horizontal_alignment, ft.CrossAxisAlignment.END)
                sizer = column.controls[-1]
                self.assertEqual(sizer.height, 0)
                self.assertEqual({c.value for c in sizer.content.controls},
                                 {c.value for b in (first, last)
                                  for c in b.controls[index].controls[:-1]})


TASK = "terminal-datenplatte"


class TerminalTest(Base):
    """B-N-04: Terminal-Zeilen einzeilig, Bereich wischbar, Schrift waechst mit."""

    def board(self, factor=1.0, runs=(0, 1)):
        ui.set_font_factor(factor)
        board = sp.TerminalBoard(fg.task_by_id(TASK))
        for index in runs:
            board.run(index)
        return board

    def test_zeilen_einzeilig(self):
        board = self.board()
        lines = board.lines.controls
        self.assertGreater(len(lines), 4)
        longest = max(len(line.value or "") for line in lines)
        self.assertGreater(longest, 30, "Testfall braucht eine lange Ausgabezeile")
        for line in lines:
            self.assertTrue(line.no_wrap, "Zeile bricht um: %r" % (
                line.value or "".join(span.text for span in line.spans or [])))

    def test_bereich_wischbar(self):
        board = self.board()
        row = board.screen.content
        self.assertTrue(isinstance(row, ft.Row) and row.scroll,
                        "Terminal nicht waagrecht wischbar (Inhalt: %s)" % type(row).__name__)
        self.assertIs(row.controls[0], board.lines)

    def test_schrift_waechst_mit(self):
        for factor in (1.0, 1.15, 1.3):
            board = self.board(factor)
            for line in board.lines.controls:
                if line.spans:
                    sizes = {span.style.size for span in line.spans}
                else:
                    sizes = {line.size}
                self.assertEqual(sizes, {ui.fs(12)}, "Faktor %s" % factor)

    def test_befehlsknoepfe_duerfen_umbrechen(self):
        board = self.board(runs=())
        texts = [c for c in walk(board.choices) if isinstance(c, ft.Text)
                 and c.font_family == ui.MONO]
        self.assertTrue(texts)
        for text in texts:
            self.assertFalse(text.no_wrap)


if __name__ == "__main__":
    unittest.main(verbosity=2)
