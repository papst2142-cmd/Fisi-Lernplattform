#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test ab 0.63.2 (B-9b, FG-93): Hinweis "→ wischen" im Handy-Spiel.

Terminal (spiel.TerminalBoard) und Tilgungsplan (GameScreen._loan_plan) sind
seit N3 waagrecht wischbar. Neu: rechts unter dem Bereich steht der Hinweis
der Rechner ("→ wischen", Schrift und Farbe wie ui.FitBox, ohne Verlauf),
aber nur, wenn der Inhalt breiter ist als der sichtbare Platz. Gemessen wird
mit ui.SwipeHint: die wischbare Row meldet ihre sichtbare Breite, ihr Kind
seine volle Breite (on_size_change). Hier werden diese Meldungen mit den
Breiten nachgestellt, die die Handy-Nachbildung im Browser gemessen hat
(bau_0.63.2/b9b, z. B. Terminal 384 px Normal: sichtbar 268, Inhalt 343,8;
Tilgungsplan: sichtbar 268, Inhalt 213,2).

FitBox und fit_lines bleiben unveraendert (No-Op-Test, gruen auf b0e75bc
und nachher).

Gegenprobe mit anderem Code-Ordner:
    SPIEL_HANDY_CODE=<ordner> python test_wischhinweis_handy_0632.py
Vorher einmal: python mobile/vorbereiten.py
"""

import hashlib
import json
import os
import shutil
import sys
import tempfile
import types
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
TASK = "terminal-datenplatte"


def walk(control):
    yield control
    for name in ("controls", "content"):
        value = getattr(control, name, None)
        if isinstance(value, list):
            for child in value:
                yield from walk(child)
        elif isinstance(value, ft.Control):
            yield from walk(value)


def size(width):
    return types.SimpleNamespace(width=width, height=20)


def hints_in(control):
    """Alle Hinweise "→ wischen" (Text) unter control."""
    return [c for c in walk(control) if isinstance(c, ft.Text) and c.value == "→ wischen"]


def hint_box(control, text):
    """Der sichtbar/unsichtbar geschaltete Traeger des Hinweises (Text selbst
    oder sein Container)."""
    for c in walk(control):
        if c is text:
            return c
        if isinstance(c, ft.Container) and c.content is text:
            return c
    return None


class App:
    def __init__(self, db):
        self.db = db
        self.slot_chosen = True
        self.page = None

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


class Base(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="b9b_test_")

    def tearDown(self):
        ui.set_font_factor(FACTOR)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def fitbox_hint(self):
        box = ui.read_box("x", mono=True, scroll=True, fit=True)
        return box.hint

    def assert_like_fitbox(self, text):
        """Wortlaut, Schrift, Farbe, Ausrichtung wie der Hinweis der Rechner."""
        ref = self.fitbox_hint()
        self.assertEqual(text.value, ui.FIT_HINT)
        self.assertEqual(text.value, "→ wischen")
        self.assertEqual(text.size, ref.size)
        self.assertEqual(text.color, ref.color)
        self.assertEqual(text.font_family, ref.font_family)
        self.assertEqual(text.text_align, ft.TextAlign.RIGHT)
        self.assertEqual(text.weight, ref.weight)

    def assert_scroll_area(self, area, scroller, content, parent):
        """Hinweis: unter dem Bereich (Geschwister, nicht im Wischbereich),
        rechts, ohne Verlauf, ohne eigene Tipp-/Wisch-Funktion; der Bereich
        selbst bleibt wischbar."""
        self.assertTrue(isinstance(scroller, ft.Row) and scroller.scroll)
        self.assertEqual(scroller.controls, [content])
        texts = hints_in(area)
        self.assertEqual(len(texts), 1, "Hinweis fehlt oder doppelt")
        text = texts[0]
        self.assert_like_fitbox(text)
        self.assertEqual(hints_in(scroller), [], "Hinweis liegt im Wischbereich")
        holder = hint_box(parent, text)
        self.assertIsNotNone(holder, "Hinweis nicht direkt unter dem Bereich")
        index = parent.controls.index(holder)
        self.assertGreater(index, 0)
        before = parent.controls[index - 1]
        self.assertIn(scroller, list(walk(before)), "Hinweis steht nicht unter dem Bereich")
        if isinstance(holder, ft.Container):
            self.assertEqual(holder.alignment, ft.Alignment.CENTER_RIGHT)
            self.assertIsNone(holder.on_click)
            self.assertIsNone(holder.gradient)
            self.assertIsNone(holder.foreground_decoration)
        for c in walk(area):
            if isinstance(c, ft.Container):
                self.assertIsNone(c.foreground_decoration, "Verlauf am Rand")
                self.assertIsNone(c.gradient, "Verlauf am Rand")
        return holder

    def assert_measured(self, holder, scroller, content):
        """Sichtbar genau dann, wenn Inhalt breiter als sichtbarer Platz."""
        self.assertFalse(holder.visible, "Hinweis vor der Messung sichtbar")
        self.assertIsNotNone(scroller.on_size_change, "sichtbare Breite wird nicht gemessen")
        self.assertIsNotNone(content.on_size_change, "Inhaltsbreite wird nicht gemessen")
        calls = []
        holder.update = lambda: calls.append("update")
        scroller.on_size_change(size(268.0))
        self.assertFalse(holder.visible, "nur eine Breite bekannt: kein Hinweis")
        content.on_size_change(size(343.8))           # Terminal 384 Normal (Browser)
        self.assertTrue(holder.visible, "zu breiter Inhalt ohne Hinweis")
        content.on_size_change(size(213.2))           # Tilgungsplan 384 Normal (Browser)
        self.assertFalse(holder.visible, "passender Inhalt mit Hinweis")
        content.on_size_change(size(268.0))           # genau so breit: passt
        self.assertFalse(holder.visible)
        content.on_size_change(size(268.4))           # Rundung
        self.assertFalse(holder.visible)
        content.on_size_change(size(269.0))
        self.assertTrue(holder.visible)
        scroller.on_size_change(size(318.0))          # Platz waechst (z. B. drehen)
        self.assertFalse(holder.visible)
        scroller.on_size_change(size(250.0))
        self.assertTrue(holder.visible)
        self.assertEqual(calls, [], "im Ereignis kein eigenes update() (wie FitBox)")


class TerminalHintTest(Base):

    def board(self, runs=(0, 1), factor=1.0):
        ui.set_font_factor(factor)
        board = sp.TerminalBoard(fg.task_by_id(TASK))
        for index in runs:
            board.run(index)
        return board

    def parts(self, board):
        scroller = board.screen.content
        parent = [c for c in walk(board) if isinstance(c, ft.Column)
                  and board.screen in (c.controls or [])][0]
        return scroller, board.lines, parent

    def test_hinweis_unter_dem_terminal(self):
        for factor in (1.0, 1.15, 1.3):
            board = self.board(factor=factor)
            scroller, content, parent = self.parts(board)
            self.assert_scroll_area(board, scroller, content, parent)
            # Abstand wie bei den Rechnern (FitBox: Kasten und Hinweis, spacing 4)
            self.assertEqual(parent.spacing, self.fitbox_parent_spacing())

    def fitbox_parent_spacing(self):
        return ui.read_box("x", mono=True, scroll=True, fit=True).spacing

    def test_da_bei_zu_breit_nicht_da_bei_passend(self):
        board = self.board()
        scroller, content, parent = self.parts(board)
        holder = self.assert_scroll_area(board, scroller, content, parent)
        self.assert_measured(holder, scroller, content)

    def test_nach_neuem_befehl_weiter_gemessen(self):
        board = self.board(runs=())
        scroller, content, parent = self.parts(board)
        holder = self.assert_scroll_area(board, scroller, content, parent)
        scroller.on_size_change(size(268.0))
        content.on_size_change(size(250.0))
        self.assertFalse(holder.visible)
        board.run(0)                                   # df -h: breite Ausgabe
        self.assertIs(board.screen.content, scroller)
        content.on_size_change(size(343.8))
        self.assertTrue(holder.visible)

    def test_bereich_bleibt_wie_n3(self):
        board = self.board()
        self.assertIs(board.screen.content.controls[0], board.lines)
        for line in board.lines.controls:
            self.assertTrue(line.no_wrap)


class LoanPlanHintTest(Base):

    def setUp(self):
        super().setUp()
        self.db = core.DBManager(os.path.join(self.tmp, "h.db"))
        self.screen = sp.GameScreen(App(self.db))

    def tearDown(self):
        self.db.close() if hasattr(self.db, "close") else None
        super().tearDown()

    def item(self):
        game, db = self.screen.game, self.db
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
        package = fg.loan_rules(game.content)["pakete"][-1]
        offer = fg.loan_offer(game.state, package["summe"], package["laufzeit"], package,
                              game.content)
        db.log_game_event(fg.EV_LOAN, json.dumps({
            "kredit": "%s%d:1" % (fg.LOAN_PREFIX, game.state.day), "tag": game.state.day,
            "name": offer["name"], "paket": offer["paket"], "summe": offer["summe"],
            "laufzeit": offer["laufzeit"], "zins": offer["zins"], "rate": offer["rate"]}),
            "Handy", game.run)
        game.reload()
        state = game.state
        return fg.loan_status(state, state.running_loans()[0])

    def parts(self, plan):
        scroller = [c for c in walk(plan) if isinstance(c, ft.Row) and c.scroll][0]
        return scroller, scroller.controls[0]

    def test_hinweis_unter_der_tabelle(self):
        plan = self.screen._loan_plan(self.item())
        scroller, content = self.parts(plan)
        holder = self.assert_scroll_area(plan, scroller, content, plan)
        # Reihenfolge: Tabelle, Hinweis, Satz zu den Zinsen
        self.assertIs(plan.controls[0], scroller)
        self.assertIs(plan.controls[1], holder)
        self.assertTrue(plan.controls[-1].value.startswith("Noch zu zahlende Zinsen"))

    def test_da_bei_zu_breit_nicht_da_bei_passend(self):
        plan = self.screen._loan_plan(self.item())
        scroller, content = self.parts(plan)
        holder = self.assert_scroll_area(plan, scroller, content, plan)
        self.assert_measured(holder, scroller, content)

    def test_im_kredit_aufgeklappt(self):
        item = self.item()
        state = self.screen.game.state
        self.screen.plans_for = set(state.loans)
        controls = self.screen._firm_kredite(state)
        texts = [t for root in controls for t in hints_in(root)]
        self.assertEqual(len(texts), 1)
        self.screen.plans_for = set()
        controls = self.screen._firm_kredite(state)
        self.assertEqual([t for root in controls for t in hints_in(root)], [])
        self.assertTrue(item)


class SwipeHintBausteinTest(Base):
    """Der Baustein selbst (ui.SwipeHint)."""

    def test_baustein(self):
        self.assertTrue(hasattr(ui, "SwipeHint"), "ui.SwipeHint fehlt")
        content = ft.Column([ft.Text("x")])
        view = ft.Row([content], scroll=ft.ScrollMode.AUTO)
        hint = ui.SwipeHint(view, content)
        self.assertFalse(hint.visible)
        view.on_size_change(size(0))
        content.on_size_change(size(500))
        self.assertFalse(hint.visible, "ohne sichtbare Breite kein Hinweis")
        view.on_size_change(size(300))
        self.assertTrue(hint.visible)
        content.on_size_change(size(None))
        self.assertFalse(hint.visible)


class FitBoxNoOpTest(unittest.TestCase):
    """FitBox und fit_lines unveraendert: Verhalten auf festen Texten und
    Breiten, Pruefsumme auf b0e75bc ermittelt (dort ebenfalls gruen)."""

    TEXTE = [
        "Netzadresse           : 192.168.10.0\nBroadcast-Adresse     : 192.168.10.63",
        "Letzte Adresse        : 2001:db8:85a3:0:ffff:ffff:ffff:ffff",
        "Festplatten           : 4 x 4.000 GB\nNutzbar               : 12.000 GB",
        "Pruefsumme            : " + "A1B2C3D4E5" * 3,
        "Noch keine Berechnung durchgeführt.",
        "",
    ]
    SOLL = "bc0e3668c1177f540e0bc53fa1e3b8a0ffa5b7b70fb43674b44ed4a9a5a2eba8"

    def zustand(self):
        out = []
        for factor in (1.0, 1.15, 1.3):
            ui.set_font_factor(factor)
            try:
                for text in self.TEXTE:
                    for breite in range(150, 461, 13):
                        box = ui.read_box("Noch keine Berechnung durchgeführt.", mono=True,
                                          scroll=True, fit=True)
                        ui.set_box(box, text)
                        box._box_sized(size(breite))
                        longest = max(len(line) for line in box.data.value.split("\n"))
                        if longest:
                            box._text_sized(size(7.83 * factor * longest))
                        deko = box.box.foreground_decoration
                        out.append([factor, breite, box.zeichen, box.data.value,
                                    box.hint.value, box.hint.visible, box.hint.size,
                                    box.hint.color, box.hint.font_family,
                                    [round(s, 4) for s in deko.gradient.stops] if deko else None,
                                    [type(c).__name__ for c in box.controls],
                                    box.spacing])
                    for zeichen in (None, 6, 12, 20, 28, 36, 50):
                        out.append([text, zeichen, core.fit_lines(text, zeichen)])
            finally:
                ui.set_font_factor(FACTOR)
        return out

    def test_fitbox_und_fit_lines_unveraendert(self):
        self.assertIs(ui.fit_lines, core.fit_lines)
        digest = hashlib.sha256(json.dumps(self.zustand(), ensure_ascii=False,
                                           sort_keys=True).encode("utf-8")).hexdigest()
        self.assertEqual(digest, self.SOLL)


if __name__ == "__main__":
    unittest.main(verbosity=2)
