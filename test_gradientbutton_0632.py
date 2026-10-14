"""Tests 0.63.2 (B-J-06, Rest S6; Weisung zu Meldung 43, 2.8): ui.GradientButton
ab 160 % ohne Symbol - der Text steht direkt im Knopf und zentriert, damit er
umbrechen kann. Mit Symbol und bis "Sehr gross" bleibt die Reihe wie bisher.
Name, Rolle und Antippen bleiben unveraendert, die Hoehe bleibt fest.

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
                self.assertIs(knopf.content.content, knopf.caption, (faktor, kind))
                self.assertEqual(knopf.caption.text_align, ft.TextAlign.CENTER,
                                 (faktor, kind))


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
                    teile = inner.controls if isinstance(inner, ft.Row) else [inner]
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
                    # Hoehe fest wie bisher
                    self.assertEqual(knopf.height, ui.grow(46))
                    self.assertEqual(knopf.border_radius, ui.grow(46) // 2)
                    self.assertEqual(knopf.padding, ft.Padding.symmetric(horizontal=20))
                    self.assertEqual(knopf.alignment, ft.Alignment.CENTER)


if __name__ == "__main__":
    unittest.main(verbosity=2)
