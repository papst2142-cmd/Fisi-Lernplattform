#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer die Zugaenglichkeit ab 0.56 (Plan Abschnitt 6):
  * Kontraste der Theme-Farben (Schrift 4,5:1, Bedienelemente 3:1) in jeder
    Kombination aus Darstellung, Hintergrund und Grundfarbe
  * Schriftgroesse: gespeichert (nur dieses Geraet), angewendet am PC (live)
    und am Handy (Faktor auf ft.Text)
  * Tastatur am PC: NeoButton per Eingabe/Leertaste, Fokusrahmen, Tab
    erreicht die Navigation, verdeckte Ansichten werden uebersprungen,
    Karteikarte und Pruefungstrainer ganz ohne Maus
  * TalkBack-Beschriftungen der Handy-Bausteine

Datenbank und Einstellungen liegen in einem Temp-Ordner (FISI_DB_PATH).
Start:  python test_zugang.py   (Teile mit Oberflaeche brauchen ein Display)
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_TMP = tempfile.mkdtemp(prefix="fisi_zugang_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "zugang.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(_TMP, "selbsttest.log"))

import fisi_theme as th  # noqa: E402

TEXT_KEYS = ("text", "text_soft", "text_dim", "muted", "accent", "accent2", "cyan", "pink",
             "purple", "green", "yellow", "orange", "blue", "red")
SURFACES = ("bg", "sidebar", "card", "card_alt", "card_hi")


def _tk_ok():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:  # noqa: BLE001
        return False


def _all_combinations():
    """Ruft fn fuer jede Kombination auf und stellt danach den Standard her."""
    for mode in th.MODE_IDS:
        for back in th.BACKGROUND_IDS:
            for preset in th.PRESET_IDS:
                th.apply_mode(mode)
                th.apply_background(back)
                th.apply_preset(preset)
                yield mode, back, preset


def _reset_theme():
    th.apply_mode(th.DEFAULT_MODE)
    th.apply_background(th.DEFAULT_BACKGROUND)
    th.apply_preset(th.DEFAULT_PRESET)


class KontrastTest(unittest.TestCase):
    """Ab 0.56: alle relevanten Farbpaare, hell und dunkel."""

    def tearDown(self):
        _reset_theme()

    def test_schrift_auf_allen_flaechen(self):
        for combo in _all_combinations():
            for key in TEXT_KEYS:
                for surface in SURFACES:
                    self.assertGreaterEqual(th.contrast(th.C[key], th.C[surface]), 4.5,
                                            (combo, key, surface))

    def test_weisse_schrift_auf_allen_verlaeufen(self):
        """Auch Loeschen (danger) und Erfolg (success) - vorher 2,8 bzw. 1,8:1."""
        for combo in _all_combinations():
            for name, colors in th.GRADIENTS.items():
                for color in colors:
                    self.assertGreaterEqual(th.contrast(th.C["on_accent"], color), 4.5,
                                            (combo, name, color))

    def test_bedienelemente_mindestens_3_zu_1(self):
        """Rand der Eingabefelder/Antwortkreise und Fokusrahmen."""
        for combo in _all_combinations():
            for key in ("field_border", "focus"):
                for surface in SURFACES:
                    self.assertGreaterEqual(th.contrast(th.C[key], th.C[surface]),
                                            th.CONTROL_CONTRAST, (combo, key, surface))

    def test_farbwelt_bleibt(self):
        """Nur gezielte Aenderungen: Grundtoene unveraendert."""
        _reset_theme()
        self.assertEqual(th.C["bg"], "#120A24")
        self.assertEqual(th.C["accent"], "#22D3EE")
        self.assertEqual(th.GRADIENTS["primary"], ("#7C3AED", "#DB2777"))
        self.assertEqual(th.GRADIENTS["danger"][0], "#DC2626")
        # Eingabefeld-Rand im Farbton des bisherigen Rands (border_hi), nur heller
        self.assertGreater(th.luminance(th.C["field_border"]), th.luminance(th.C["border_hi"]))


class SchriftgroesseTest(unittest.TestCase):
    """Ab 0.56: Einstellung je Geraet (einstellungen.json, nicht Lern-DB)."""

    def tearDown(self):
        th.save_font_size(th.FONT_NORMAL)

    def test_speichern_und_lesen(self):
        self.assertEqual([item["faktor"] for item in th.FONT_SIZES], [1.0, 1.15, 1.3])
        th.save_font_size("sehr_gross")
        self.assertEqual(th.current_font_size, "sehr_gross")
        self.assertEqual(th.saved_font_size(), "sehr_gross")
        self.assertAlmostEqual(th.font_factor(), 1.3)
        path = os.path.join(_TMP, "einstellungen.json")
        with open(path, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)[th.FONT_KEY], "sehr_gross")

    def test_unbekannt_ist_normal(self):
        self.assertEqual(th.apply_font_size("riesig"), th.FONT_NORMAL)
        self.assertEqual(th.font_factor("riesig"), 1.0)

    def test_gleiche_texte_pc_und_handy(self):
        with open(os.path.join(HERE, "app_gui.py"), encoding="utf-8") as handle:
            pc = handle.read()
        with open(os.path.join(HERE, "mobile", "src", "main.py"), encoding="utf-8") as handle:
            mobile = handle.read()
        # Ab 0.59 kommt der Bereichstitel fuer beide aus fisi_optionen.py
        with open(os.path.join(HERE, "fisi_optionen.py"), encoding="utf-8") as handle:
            self.assertIn("fisi_theme.FONT_TITLE", handle.read())
        for name in ("FONT_SUBTITLE", "FONT_HINT", "FONT_CHOICES",
                     "BUSY_FONT_TITLE", "BUSY_FONT_TEXT"):
            self.assertIn("fisi_theme." + name, pc, name)
            self.assertIn("fisi_theme." + name, mobile, name)


class HandyTest(unittest.TestCase):
    """Handy-Bausteine: Schriftfaktor und TalkBack-Beschriftungen."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(1, os.path.join(HERE, "mobile", "src"))
        import ui
        cls.ui = ui

    def tearDown(self):
        self.ui.set_font_factor(1.0)

    def test_schriftfaktor_auf_text(self):
        import flet as ft
        self.ui.set_font_factor(1.3)
        self.assertEqual(ft.Text("a", size=10).size, 13)
        self.assertEqual(ft.Text("a").size, 18.2)          # Standard 14
        self.assertEqual(self.ui.grow(36), 47)
        self.ui.set_font_factor(1.0)
        self.assertEqual(ft.Text("a", size=10).size, 10)

    def test_beschriftungen(self):
        ui = self.ui
        ring = ui.Ring(size=112)
        ring.set(0.25, "#FFFFFF", big="12", small="von 48 Karten")
        self.assertEqual(ring.semantics.label, "12 von 48 Karten 25 Prozent")
        chart = ui.LineChart()
        chart.set_data(["Mo", "Di"], [3, 5], "#FFFFFF", goal=(20, "Tagesziel", "#FFFFFF"))
        self.assertEqual(chart.label, "Diagramm: Mo 3, Di 5, Tagesziel 20")
        bars = ui.ShareBars()
        bars.set_data([("Mo", 80, 20), ("Di", None, None)])
        self.assertIn("Mo 80 Prozent richtig, 20 Prozent falsch", bars.label)
        self.assertIn("Di keine Aufgaben", bars.label)
        options = ui.OptionList()
        options.set_options(["A", "B"])
        options.select("B")
        options.reveal("A")
        labels = [entry["semantics"].label for entry in options._rows]
        self.assertEqual(labels, ["A, richtige Antwort", "B, deine Antwort, falsch"])
        pills = ui.PillGroup([("a", "Eins"), ("b", "Zwei")], initial=1)
        self.assertEqual([item.selected for item in pills.semantics], [False, True])
        stepper = ui.Stepper()
        self.assertEqual([stepper.controls[0].label, stepper.controls[2].label],
                         ["Weniger", "Mehr"])


@unittest.skipUnless(_tk_ok(), "kein Display fuer Tk")
class TastaturPcTest(unittest.TestCase):
    """Programm einmal aufbauen und per Tastatur bedienen."""

    @classmethod
    def setUpClass(cls):
        import customtkinter as ctk
        import app_gui
        import fisi_widgets as fw
        cls.ctk, cls.app_gui, cls.fw = ctk, app_gui, fw
        app_gui.UpdateController.auto_check = lambda self: None
        app_gui.SyncController.auto_start = lambda self: None
        cls.infos = []
        for name in ("showinfo", "showwarning", "showerror"):
            setattr(app_gui.messagebox, name, lambda *a, **k: cls.infos.append(a))
        cls.root = ctk.CTk()
        cls.root.geometry("1360x880+0+0")
        cls.app = app_gui.FISIApp(cls.root)
        cls.settle()

    @classmethod
    def tearDownClass(cls):
        try:
            for job in cls.root.tk.splitlist(cls.root.tk.call("after", "info")):
                cls.root.tk.call("after", "cancel", job)
            cls.root.destroy()
        except Exception:  # noqa: BLE001
            pass
        shutil.rmtree(_TMP, ignore_errors=True)

    @classmethod
    def settle(cls, times=6):
        for _ in range(times):
            cls.root.update_idletasks()
            cls.root.update()

    def press(self, widget, key):
        """Taste an das fokussierte Element (wie echte Tastatur)."""
        self.fw.focus_widget(widget)
        self.settle(2)
        widget.event_generate(key)
        self.settle()

    def tab(self, shift=False):
        focus = self.root.tk.call("focus") or "."
        self.root.nametowidget(str(focus)).event_generate(
            "<<PrevWindow>>" if shift else "<Tab>")
        self.settle(2)
        return self.root.nametowidget(str(self.root.tk.call("focus")))

    # -- NeoButton und Fokusrahmen ----------------------------------------

    def test_neobutton_per_tastatur(self):
        calls = []
        button = self.fw.NeoButton(self.root, "Test", lambda: calls.append(1))
        button.place(x=400, y=400)
        self.settle()
        self.assertEqual(str(button.tk.call(button._w, "cget", "-takefocus")), "1")
        self.press(button, "<Return>")
        self.press(button, "<space>")
        self.assertEqual(calls, [1, 1])
        button.set_enabled(False)
        self.assertEqual(str(button.tk.call(button._w, "cget", "-takefocus")), "0")
        self.press(button, "<Return>")
        self.assertEqual(calls, [1, 1])
        button.destroy()

    def test_fokusrahmen_erscheint_und_verschwindet(self):
        import fisi_theme
        button = self.fw.NeoButton(self.root, "Rahmen", lambda: None)
        button.place(x=500, y=500)
        self.settle()
        self.fw.focus_widget(button)
        self.settle()
        ring = self.fw.focus_ring(button)
        self.assertTrue(ring.shows())
        bar = ring.bars[0]
        self.assertEqual(bar.cget("bg").upper(), fisi_theme.C["focus"].upper())
        # liegt um den Knopf herum
        self.assertLess(bar.winfo_rootx(), button.winfo_rootx())
        self.assertLess(bar.winfo_rooty(), button.winfo_rooty())
        # Mausklick: Rahmen weg (wie :focus-visible)
        button.event_generate("<Button-1>", x=5, y=5)
        self.settle()
        self.assertFalse(ring.shows())
        button.destroy()

    def test_klappkopf_bekommt_rahmen(self):
        self.app.show_view("settings")
        self.settle()
        view = self.app.views["settings"]
        heads = [w.head for w in self._walk(view.inner) if isinstance(w, self.fw.FoldCard)]
        self.assertTrue(heads)
        self.fw.focus_widget(heads[0])
        self.settle()
        self.assertTrue(self.fw.focus_ring(heads[0]).shows())

    # -- Navigation ------------------------------------------------------

    def test_tab_erreicht_navigation_und_ueberspringt_verdeckte(self):
        self.app.show_view("dashboard")
        self.settle()
        self.app.show_view("cards")
        self.settle()
        self.root.tk.call("focus", self.root._w)
        seen = []
        for _step in range(80):
            seen.append(self.tab())
        names = [w.text_label.cget("text") for w in seen
                 if isinstance(w, self.app_gui.NavRow)]
        for _key, _icon, text, _sub in self.app_gui.NAV_ITEMS:
            self.assertIn(text, names)
        dashboard = str(self.app.views.built("dashboard")) + "."
        self.assertFalse([w for w in seen if str(w).startswith(dashboard)])
        # Navigation zuerst, dann Kopf, dann Inhalt
        first_nav = next(i for i, w in enumerate(seen) if isinstance(w, self.app_gui.NavRow))
        first_view = next(i for i, w in enumerate(seen)
                          if str(w).startswith(str(self.app.views["cards"])))
        self.assertLess(first_nav, first_view)
        # Rueckwaerts geht es auch
        back = self.tab(shift=True)
        self.assertIn(back, seen)

    def test_navigation_per_eingabetaste(self):
        row = self.app.sidebar.rows["progress"]
        self.press(row, "<Return>")
        self.assertEqual(self.app.current, "progress")
        self.press(self.app.sidebar.rows["dashboard"], "<space>")
        self.assertEqual(self.app.current, "dashboard")

    # -- Karteikarte und Pruefungstrainer --------------------------------

    def test_karteikarte_ohne_maus(self):
        self.app.show_view("cards")
        self.settle()
        view = self.app.views["cards"]
        mc = view.mode_pills.buttons[view.mode_pills.values.index("mc")]
        self.press(mc, "<Return>")
        self.assertEqual(view.mode, "mc")
        first = view.options._rows[0]
        self.press(first["frame"], "<space>")
        self.assertEqual(view.options.get(), first["text"])
        # Pfeil runter springt zur naechsten Antwort
        first["frame"].event_generate("<Down>")
        self.settle()
        self.assertEqual(str(self.root.tk.call("focus")), str(view.options._rows[1]["frame"]))
        self.press(view.btn_check, "<Return>")
        self.assertTrue(view.lbl_feedback.cget("text"))
        self.assertTrue(view.logged)
        index = view.index
        self.press(view.btn_next, "<Return>")
        self.assertEqual(view.index, index + 1)
        # Freitext: Tab verlaesst das Textfeld, Strg+Eingabe prueft
        free = view.mode_pills.buttons[view.mode_pills.values.index("freitext")]
        self.press(free, "<Return>")
        box = view.txt_answer._textbox
        self.fw.focus_widget(box)
        self.settle()
        box.insert("end", "Antwort")
        box.event_generate("<Tab>")
        self.settle()
        self.assertNotIn("\t", view.txt_answer.get("1.0", "end"))
        self.assertNotEqual(str(self.root.tk.call("focus")), str(box))
        self.fw.focus_widget(box)
        box.event_generate("<Control-Return>")
        self.settle()
        self.assertTrue(view.lbl_solution.cget("text"))

    def test_pruefungstrainer_ohne_maus(self):
        self.app.show_view("quiz")
        self.settle()
        view = self.app.views["quiz"]
        self.press(view.btn_start, "<Return>")
        self.assertTrue(view.running)
        row = view.options._rows[0]
        self.press(row["frame"], "<Return>")
        self.assertEqual(view.options.get(), row["text"])
        self.press(view.btn_submit, "<Return>")
        self.assertTrue(view.answered)
        self.press(view.btn_submit, "<Return>")
        self.assertEqual(view.index, 1)
        self.assertFalse(view.answered)
        view.stop_timer()
        view._reset_controls()

    # -- Schriftgroesse live ------------------------------------------------

    def test_schriftgroesse_live(self):
        import fisi_theme
        ctk = self.ctk
        self.app.show_view("settings")
        self.settle()
        try:
            self.app.change_font_size("gross")
            self.settle()
            self.assertEqual(fisi_theme.current_font_size, "gross")
            self.assertAlmostEqual(ctk.ScalingTracker.widget_scaling, 1.15)
            self.assertEqual(fisi_theme.saved_font_size(), "gross")
            view = self.app.views["settings"]
            self.assertEqual(view.font_choice.value, "gross")
            # neu aufgebaute Knoepfe sind entsprechend groesser
            button = self.fw.NeoButton(view.inner, "Probe", lambda: None, height=38)
            self.assertAlmostEqual(button._apply_widget_scaling(38), 38 * 1.15, delta=1)
            button.destroy()
        finally:
            self.app.change_font_size("normal")
            self.settle()
        self.assertAlmostEqual(ctk.ScalingTracker.widget_scaling, 1.0)

    @staticmethod
    def _walk(widget):
        stack = [widget]
        while stack:
            node = stack.pop()
            yield node
            stack.extend(node.winfo_children())


if __name__ == "__main__":
    unittest.main(verbosity=1)
