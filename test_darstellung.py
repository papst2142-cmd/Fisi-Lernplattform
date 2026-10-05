#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer die Darstellung ab 0.58 (Plan 1 und 3a):
  * Datumsachse: Beschriftungen nach Textbreite ausgeduennt, vom rechten
    Ende gezaehlt (fisi_theme.label_stride / shown_labels), PC und Handy
  * Handy-Diagramme: Legende im Liniendiagramm, Schrift waechst mit
  * Dashboard bei 1360 px ohne seitlichen Schieberegler (Normal, Gross,
    Sehr gross)
  * Farbige Reglerspuren: Farben an Anfang, Mitte und Ende, Rueckfall bei
    ungueltigen Werten, Knopf mit mindestens 3:1 zur Spur
  * Zeitgrenze des Starttests (build.selftest_timeout)

Start:  python test_darstellung.py   (Teile mit Oberflaeche brauchen ein Display)
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import fisi_theme as th  # noqa: E402


def _tk_ok():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:  # noqa: BLE001
        return False


class AchseTest(unittest.TestCase):
    """Ausduennen der Datumsachse (PC und Handy nutzen dieselbe Regel)."""

    def test_genug_platz_jede_beschriftung(self):
        self.assertEqual(th.label_stride(14, 60, 30), 1)

    def test_30_tage_wird_ausgeduennt(self):
        stride = th.label_stride(30, 20, 34)
        self.assertGreater(stride, 1)
        self.assertGreaterEqual(20 * stride, 34 * th.LABEL_SPACING)
        self.assertIn(stride, th.LABEL_STRIDES)

    def test_letzter_tag_immer_beschriftet(self):
        for count in (7, 14, 30):
            for stride in th.LABEL_STRIDES:
                shown = th.shown_labels(count, stride)
                self.assertIn(count - 1, shown)
                gaps = {b - a for a, b in zip(shown, shown[1:])}
                self.assertTrue(gaps <= {stride}, (count, stride, gaps))

    def test_randfaelle(self):
        self.assertEqual(th.label_stride(1, 10, 100), 1)
        self.assertEqual(th.label_stride(5, 0, 100), 1)
        self.assertEqual(th.shown_labels(0, 3), [])
        self.assertEqual(th.label_stride(30, 0.1, 500), 30)

    def test_pc_und_handy_nutzen_die_regel(self):
        with open(os.path.join(HERE, "fisi_widgets.py"), encoding="utf-8") as handle:
            pc = handle.read()
        with open(os.path.join(HERE, "mobile", "src", "ui.py"), encoding="utf-8") as handle:
            handy = handle.read()
        for text in (pc, handy):
            self.assertIn("label_stride(", text)
            self.assertIn("shown_labels(", text)


class HandyDiagrammTest(unittest.TestCase):
    """Legende und mitwachsende Schrift im Handy-Liniendiagramm."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(1, os.path.join(HERE, "mobile", "src"))
        import ui
        cls.ui = ui

    def tearDown(self):
        self.ui.set_font_factor(1.0)

    def _texts(self, chart):
        import flet.canvas as cv
        chart.canvas._width = 360
        chart.canvas._draw()
        return [shape for shape in chart.canvas.shapes if isinstance(shape, cv.Text)]

    def test_legende_aufgaben(self):
        import fisi_lernen
        chart = self.ui.LineChart()
        chart.set_data(["01.10", "02.10"], [3, 5], "#FFFFFF",
                       name=fisi_lernen.LEARN_CHART_SERIES)
        texts = [shape.value for shape in self._texts(chart)]
        self.assertIn("Aufgaben pro Tag", texts)

    def test_ohne_name_keine_legende(self):
        chart = self.ui.LineChart()
        chart.set_data(["01.10", "02.10"], [3, 5], "#FFFFFF")
        self.assertNotIn("Aufgaben pro Tag", [s.value for s in self._texts(chart)])

    def test_schrift_waechst_bei_sehr_gross(self):
        chart = self.ui.LineChart()
        chart.set_data(["01.10", "02.10"], [3, 5], "#FFFFFF", name="Aufgaben pro Tag")
        normal = {shape.style.size for shape in self._texts(chart)}
        self.ui.set_font_factor(1.3)
        chart.set_data(["01.10", "02.10"], [3, 5], "#FFFFFF", name="Aufgaben pro Tag")
        large = {shape.style.size for shape in self._texts(chart)}
        self.assertEqual(normal, {10})
        self.assertEqual(large, {13})

    def test_30_tage_ausgeduennt(self):
        labels = ["%02d.09" % day for day in range(1, 31)]
        chart = self.ui.LineChart()
        chart.set_data(labels, list(range(30)), "#FFFFFF")
        shown = [s.value for s in self._texts(chart) if s.value in labels]
        self.assertLess(len(shown), 30)
        self.assertIn("30.09", shown)

    def test_balken_schrift_waechst(self):
        import flet.canvas as cv

        def sizes():
            bars = self.ui.ShareBars()
            bars.set_data([("01.10", 80, 20), ("02.10", None, None)])
            bars.canvas._width = 360
            bars.canvas._draw()
            return {s.style.size for s in bars.canvas.shapes if isinstance(s, cv.Text)}

        normal = sizes()
        self.ui.set_font_factor(1.3)
        self.assertEqual(sizes(), {self.ui.fs(size) for size in normal})
        self.assertTrue(all(self.ui.fs(size) > size for size in normal))


class SpurTest(unittest.TestCase):
    """Farbige Reglerspuren (Plan 3a), Werte (h, s, l)."""

    def test_farbton_spektrum(self):
        values = (270, 80, 50)
        self.assertEqual(th.track_color(values, "h", 0), th.hsl_to_hex(0, 80, 50))
        self.assertEqual(th.track_color(values, "h", 0.5), th.hsl_to_hex(179.5, 80, 50))
        self.assertEqual(th.track_color(values, "h", 1), th.hsl_to_hex(359, 80, 50))

    def test_saettigung_grau_bis_voll(self):
        values = (120, 60, 40)
        self.assertEqual(th.track_color(values, "s", 0), th.hsl_to_hex(120, 0, 40))
        self.assertEqual(th.track_color(values, "s", 0.5), th.hsl_to_hex(120, 50, 40))
        self.assertEqual(th.track_color(values, "s", 1), th.hsl_to_hex(120, 100, 40))
        start = th.hex_to_rgb(th.track_color(values, "s", 0))
        self.assertEqual(len(set(start)), 1)          # grau

    def test_helligkeit_dunkel_ueber_farbe_bis_hell(self):
        values = (270, 80, 30)
        self.assertEqual(th.track_color(values, "l", 0).upper(), "#000000")
        self.assertEqual(th.track_color(values, "l", 0.5), th.hsl_to_hex(270, 80, 50))
        self.assertEqual(th.track_color(values, "l", 1).upper(), "#FFFFFF")

    def test_viele_stuetzstellen(self):
        colors = th.track_colors((0, 100, 50), "h", 61)
        self.assertEqual(len(colors), 61)
        self.assertEqual(colors[0], th.track_color((0, 100, 50), "h", 0))
        self.assertEqual(colors[-1], th.track_color((0, 100, 50), "h", 1))

    def test_rueckfall_bei_ungueltigen_werten(self):
        for bad in (None, (), ("x", None, float("nan")), (999, -5, 300)):
            for key in "hsl":
                color = th.track_color(bad, key, 0.5)
                self.assertRegex(color, r"^#[0-9A-Fa-f]{6}$")
                self.assertIn(th.knob_colors(bad, key)[0], (th.KNOB_LIGHT, th.KNOB_DARK))
        self.assertEqual(th._safe_triple(None), (0, 0, 50))
        self.assertEqual(th._safe_triple((999, -5, 300)), (359, 0, 100))

    def test_knopf_mindestens_3_zu_1(self):
        worst = 99.0
        for hue in range(0, 360, 15):
            for sat in range(0, 101, 10):
                for light in range(0, 101, 5):
                    for key in "hsl":
                        worst = min(worst, th.knob_contrast((hue, sat, light), key))
        self.assertGreaterEqual(worst, th.KNOB_MIN_CONTRAST)

    def test_knopf_rand_ist_die_andere_farbe(self):
        fill, ring = th.knob_colors((60, 100, 50), "l")
        self.assertEqual({fill, ring}, {th.KNOB_LIGHT, th.KNOB_DARK})


class SpurHandyTest(unittest.TestCase):
    """Spuren der Handy-Regler folgen den Werten (gleiche Funktion wie PC)."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(1, os.path.join(HERE, "mobile", "src"))
        import main as handy
        cls.handy = handy
        cls.panel = handy.CustomColors(lambda mode, values, world=None: None)

    def test_spuren_nach_werten(self):
        values = (130, 70, 40)
        self.panel.values["akzent2"] = values
        self.panel._tracks.pop("akzent2", None)
        self.panel._paint_tracks("akzent2")
        for key, stops in self.panel.TRACK_STOPS.items():
            gradient = self.panel.tracks[("akzent2", key)].gradient
            self.assertEqual(gradient.colors, th.track_colors(values, key, stops))
            self.assertEqual(self.panel.sliders[("akzent2", key)].thumb_color,
                             th.knob_colors(values, key)[0])


@unittest.skipUnless(_tk_ok(), "kein Display fuer Tk")
class SpurPcTest(unittest.TestCase):
    """GradientSlider: Spurfarben je Spalte und unveraenderte Werte."""

    @classmethod
    def setUpClass(cls):
        import customtkinter as ctk
        import fisi_widgets as fw
        cls.fw = fw
        cls.root = ctk.CTk()
        fw.setup_fonts(cls.root)
        cls.calls = []
        cls.slider = fw.GradientSlider(cls.root, "s", 0, 100, width=220,
                                       command=cls.calls.append)
        cls.slider.pack()
        cls.root.update()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def test_spur_anfang_mitte_ende(self):
        values = (200, 40, 45)
        self.slider.set_hsl(values)
        colors = self.slider.track_pixels()
        _width, _height, radius, span = self.slider._geometry()
        self.assertEqual(colors[radius], th.track_color(values, "s", 0.5 / span))
        self.assertEqual(colors[-1], th.track_color(values, "s", 1))
        self.assertEqual(colors[0], th.track_color(values, "s", 0))
        middle = len(colors) // 2
        fraction = (middle + 0.5 - radius) / float(span)
        self.assertEqual(colors[middle], th.track_color(values, "s", fraction))

    def test_set_aendert_wert_ohne_befehl(self):
        self.calls.clear()
        self.slider.set(37)
        self.assertEqual(self.slider.get(), 37)
        self.assertEqual(self.calls, [])


class SelbsttestZeitTest(unittest.TestCase):
    """Plan 3.1: nur macOS Intel bekommt mehr Zeit."""

    def test_zeitgrenzen(self):
        import build
        self.assertEqual(build.selftest_timeout("darwin", "x86_64"), 240)
        self.assertEqual(build.selftest_timeout("darwin", "arm64"), 120)
        self.assertEqual(build.selftest_timeout("win32", "AMD64"), 120)
        self.assertEqual(build.selftest_timeout("linux", "x86_64"), 120)


DASH_SCRIPT = r"""
import json, os, sys
sys.path.insert(0, %(here)r)
os.environ["FISI_SELFTEST"] = "screenshot"
import app_gui, customtkinter as ctk
app_gui.UpdateController.auto_check = lambda self: None
app_gui.SyncController.auto_start = lambda self: None
app_gui.apply_appearance()
root = ctk.CTk()
root.geometry("1360x880+0+0")
app = app_gui.FISIApp(root)
for _ in range(30):
    root.update_idletasks(); root.update()
app.show_view("dashboard")
for _ in range(40):
    root.update_idletasks(); root.update()
view = app.views["dashboard"]
print(json.dumps({"canvas": view.canvas.winfo_width(),
                  "inner": view.inner.winfo_reqwidth(),
                  "mode": view.row1_mode}))
root.destroy()
"""


@unittest.skipUnless(_tk_ok(), "kein Display fuer Tk")
class DashboardBreiteTest(unittest.TestCase):
    """Plan 1.1: Dashboard passt bei 1360 px ohne seitlichen Schieberegler."""

    def _measure(self, size):
        folder = tempfile.mkdtemp(prefix="fisi_dash_")
        try:
            with open(os.path.join(folder, "einstellungen.json"), "w",
                      encoding="utf-8") as handle:
                json.dump({"auto_check": False, "schriftgroesse": size,
                           "nutzer_name": "Nico", "rundgang_gesehen": True}, handle)
            env = dict(os.environ, FISI_DB_PATH=os.path.join(folder, "test.db"))
            result = subprocess.run([sys.executable, "-c", DASH_SCRIPT % {"here": HERE}],
                                    env=env, capture_output=True, text=True, timeout=180)
            lines = [line for line in result.stdout.splitlines() if line.startswith("{")]
            self.assertTrue(lines, result.stderr[-2000:])
            return json.loads(lines[-1])
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_alle_schriftgroessen(self):
        for size in ("normal", "gross", "sehr_gross"):
            with self.subTest(size=size):
                values = self._measure(size)
                self.assertGreater(values["canvas"], 1000)
                self.assertLessEqual(values["inner"], values["canvas"], values)


if __name__ == "__main__":
    unittest.main(verbosity=2)
