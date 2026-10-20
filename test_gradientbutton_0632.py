"""Tests 0.63.2 (B-J-06, Rest S6; Weisung zu Meldung 43, 2.8): ui.GradientButton
ab 160 % ohne Symbol - der Text steht direkt im Knopf und zentriert, damit er
umbrechen kann. Mit Symbol und bis "Sehr gross" bleibt die Reihe wie bisher.
Name, Rolle und Antippen bleiben unveraendert.
Ab FG-111: ab 160 % ohne Symbol waechst der Knopf mit dem Text (mindestens so
hoch wie bisher, zweizeilig hoeher); im Pruefungstrainer stehen "Antwort
einreichen" und "Abbrechen" ab 160 % untereinander; ebenso "Abgeben"/"Abbrechen"
in der laufenden Pruefung und "Antwort zeigen"/"Jetzt ueben" im Notizbuch.

Gegenprobe mit anderem Code: STUFEN_CODE=<ordner> python test_gradientbutton_0632.py
"""
import os
import sys
import unittest

HERE = os.environ.get("STUFEN_CODE") or os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.join(HERE, "mobile", "src"))

import flet as ft  # noqa: E402

import ui  # noqa: E402
import fisi_core as fc  # noqa: E402
import main  # noqa: E402
import tempfile  # noqa: E402
import types  # noqa: E402
import fisi_pruefung as fp  # noqa: E402

KLEIN = (1.0, 1.15, 1.3)     # Normal, Gross, Sehr gross
GROSS = (1.6, 2.0)           # Extra gross, Maximal
ICON = ft.Icons.PLAY_ARROW


class _Stufe(unittest.TestCase):

    def setUp(self):
        self._alt = ui.FONT_FACTOR[0]

    def tearDown(self):
        ui.set_font_factor(self._alt)

    def knopf(self, faktor, icon=None, kind="primary", expand=None, handler=None):
        ui.set_font_factor(faktor)
        return ui.GradientButton("Karteikarten zu Dienste", handler, kind=kind,
                                 icon=icon, expand=expand)

    def reihe_wie_bisher(self, knopf, icon):
        inner = knopf.content.content
        self.assertIsInstance(inner, ft.Row)
        self.assertTrue(inner.tight)
        self.assertEqual(inner.spacing, 8)
        self.assertEqual(inner.alignment, ft.MainAxisAlignment.CENTER)
        self.assertIs(inner.controls[-1], knopf.caption)
        self.assertEqual(len(inner.controls), 2 if icon else 1)
        if icon:
            self.assertIsInstance(inner.controls[0], ft.Icon)
        self.assertEqual(knopf.caption.text_align, ft.Text("x").text_align)


class AbExtraGrossOhneSymbolTest(_Stufe):

    def test_text_direkt_im_knopf_zentriert(self):
        for faktor in GROSS:
            for kind in ("primary", "ghost"):
                knopf = self.knopf(faktor, kind=kind, expand=True)
                inner = knopf.content.content
                # FG-111: Text direkt im Knopf neben einem unsichtbaren Abstandhalter,
                # der die bisherige Hoehe als Mindesthoehe haelt
                self.assertIsInstance(inner, ft.Stack, (faktor, kind))
                self.assertEqual(inner.alignment, ft.Alignment.CENTER)
                halter, text = inner.controls
                self.assertIs(text, knopf.caption, (faktor, kind))
                self.assertEqual(halter.width, 0)
                self.assertIsNone(halter.content)
                self.assertEqual(knopf.caption.text_align, ft.TextAlign.CENTER,
                                 (faktor, kind))

    def test_knopf_waechst_mindestens_bisherige_hoehe(self):
        for faktor in GROSS:
            knopf = self.knopf(faktor, expand=True)
            halter = knopf.content.content.controls[0]
            rand = knopf.padding.top
            self.assertIsNone(knopf.height)                       # waechst mit dem Text
            self.assertGreater(rand, 0)
            self.assertEqual(knopf.padding.bottom, rand)
            self.assertEqual(halter.height + 2 * rand, ui.grow(46))   # einzeilig wie bisher
            self.assertEqual(knopf.border_radius, ui.grow(46) // 2)


class ReiheWieBisherTest(_Stufe):

    def test_bis_sehr_gross_ohne_symbol(self):
        for faktor in KLEIN:
            with self.subTest(faktor=faktor):
                self.reihe_wie_bisher(self.knopf(faktor), None)

    def test_mit_symbol_alle_stufen(self):
        for faktor in KLEIN + GROSS:
            with self.subTest(faktor=faktor):
                self.reihe_wie_bisher(self.knopf(faktor, icon=ICON), ICON)


class NameRolleAntippenTest(_Stufe):

    def test_alle_stufen(self):
        for faktor in KLEIN + GROSS:
            for icon in (None, ICON):
                with self.subTest(faktor=faktor, icon=icon):
                    seen = []
                    knopf = self.knopf(faktor, icon=icon, handler=seen.append)
                    sem = knopf.content
                    # ein Element: Rolle Schaltflaeche innen, Name aus dem Text
                    self.assertIsInstance(sem, ft.Semantics)
                    self.assertTrue(sem.button)
                    self.assertIsNone(sem.label)
                    self.assertFalse(isinstance(sem.content, ft.Semantics))
                    inner = sem.content
                    teile = inner.controls if isinstance(inner, (ft.Row, ft.Stack)) else [inner]
                    self.assertFalse(any(isinstance(t, ft.Semantics) for t in teile))
                    self.assertEqual(knopf.caption.value, "Karteikarten zu Dienste")
                    knopf.set_text("Neu")
                    self.assertIn(knopf.caption, teile)
                    self.assertEqual(knopf.caption.value, "Neu")
                    # Antippen am Knopf selbst, gesperrt nimmt er nichts an
                    self.assertEqual(knopf.on_click, knopf._clicked)
                    self.assertTrue(knopf.ink)
                    knopf.on_click("e")
                    self.assertEqual(seen, ["e"])
                    knopf.set_enabled(False)
                    knopf.on_click("f")
                    self.assertEqual(seen, ["e"])
                    # Hoehe fest wie bisher (bis Sehr gross und mit Symbol)
                    if faktor in KLEIN or icon:
                        self.assertEqual(knopf.height, ui.grow(46))
                        self.assertEqual(knopf.padding, ft.Padding.symmetric(horizontal=20))
                    self.assertEqual(knopf.border_radius, ui.grow(46) // 2)
                    self.assertEqual(knopf.alignment, ft.Alignment.CENTER)



class _App:
    def __init__(self):
        self.db = fc.DBManager(os.path.join(tempfile.mkdtemp(), "t.db"))
        self.sync = None
        self.page = types.SimpleNamespace(run_task=lambda *_a, **_k: None,
                                          update=lambda: None)

    def toast(self, *_args, **_kwargs):
        pass

    def __getattr__(self, _name):
        return lambda *_a, **_k: None


class QuizReiheTest(_Stufe):
    """FG-111: "Antwort einreichen" und "Abbrechen" ab 160 % untereinander in
    voller Breite (nebeneinander war "einreichen" breiter als der Knopf)."""

    def reihe(self, faktor):
        ui.set_font_factor(faktor)
        quiz = main.QuizScreen(_App())
        for item in quiz.practice_box.controls:
            kinder = getattr(item, "controls", [])
            if any(k is quiz.btn_submit for k in kinder):
                return quiz, item
        self.fail("Knopfreihe nicht gefunden")

    def test_bis_sehr_gross_nebeneinander(self):
        for faktor in KLEIN:
            quiz, reihe = self.reihe(faktor)
            self.assertIsInstance(reihe, ft.Row, faktor)
            self.assertEqual(reihe.spacing, 10)
            self.assertEqual(len(reihe.controls), 2)
            self.assertIs(reihe.controls[0], quiz.btn_submit)
            self.assertIs(reihe.controls[1], quiz.btn_cancel)
            self.assertTrue(quiz.btn_submit.expand)

    def test_ab_160_untereinander(self):
        for faktor in GROSS:
            quiz, reihe = self.reihe(faktor)
            self.assertIsInstance(reihe, ft.Column, faktor)
            self.assertEqual(reihe.horizontal_alignment, ft.CrossAxisAlignment.STRETCH)
            self.assertIs(reihe.controls[0], quiz.btn_submit)
            self.assertIs(reihe.controls[1], quiz.btn_cancel)
            self.assertFalse(quiz.btn_submit.expand)



def _reihen_mit_knopf(wurzel, beschriftung):
    """Alle Reihen (Row/Column) unter wurzel, die den Knopf mit der Beschriftung
    direkt enthalten."""
    treffer, offen = [], [wurzel]
    while offen:
        item = offen.pop()
        kinder = list(getattr(item, "controls", None) or [])
        if any(isinstance(k, ui.GradientButton) and k.caption.value == beschriftung
               for k in kinder):
            treffer.append(item)
        inhalt = getattr(item, "content", None)
        offen += kinder + ([inhalt] if inhalt is not None else [])
    return treffer


class _Reihe(_Stufe):
    """Reihe mit zwei Knoepfen: bis Sehr gross ft.Row wie heute, ab 160 %
    untereinander in voller Breite (main.tile_row)."""

    def pruefen(self, reihe, faktor, spacing):
        knoepfe = reihe.controls
        self.assertEqual(len(knoepfe), 2)
        self.assertTrue(all(isinstance(k, ui.GradientButton) for k in knoepfe))
        if faktor in KLEIN:
            self.assertIsInstance(reihe, ft.Row, faktor)
            self.assertEqual(reihe.spacing, spacing)
            self.assertTrue(all(k.expand for k in knoepfe))
        else:
            self.assertIsInstance(reihe, ft.Column, faktor)
            self.assertEqual(reihe.spacing, spacing)
            self.assertEqual(reihe.horizontal_alignment, ft.CrossAxisAlignment.STRETCH)
            self.assertFalse(any(k.expand for k in knoepfe))


class PruefungReiheTest(_Reihe):
    """main.py ExamPanel.show_running: "Abgeben"/"Abbrechen" (Maximal:
    "Abbrech/en" brach mitten im Wort um)."""

    def test_alle_stufen(self):
        for faktor in KLEIN + GROSS:
            with self.subTest(faktor=faktor):
                ui.set_font_factor(faktor)
                panel = main.ExamPanel(_App())
                panel.state = fp.new_exam(fp.NETZWERKE, [], seed=1)
                panel.show_running()
                reihen = _reihen_mit_knopf(panel.controls[0], "Abgeben")
                self.assertEqual(len(reihen), 1)
                self.assertEqual([k.caption.value for k in reihen[0].controls],
                                 ["Abgeben", "Abbrechen"])
                self.pruefen(reihen[0], faktor, 10)


class NotizbuchReiheTest(_Reihe):
    """main.py NotebookScreen._row: "Antwort zeigen"/"Jetzt ueben" (Extra gross:
    "ausblen/den" brach mitten im Wort um)."""

    def test_alle_stufen(self):
        for faktor in KLEIN + GROSS:
            with self.subTest(faktor=faktor):
                ui.set_font_factor(faktor)
                buch = main.NotebookScreen(_App())
                eintraege = main.notebook_entries(buch.book, status=main.FILTER_ALL,
                                                  category=main.FILTER_ALL,
                                                  topic=main.FILTER_ALL, sources=None)
                zeile = buch._row(eintraege[0])
                spalte = zeile.content.controls[1]
                reihe = spalte.controls[-1]
                self.assertEqual([k.caption.value for k in reihe.controls],
                                 ["Antwort zeigen", "Jetzt üben"])
                self.pruefen(reihe, faktor, 8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
