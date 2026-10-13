#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests 0.63.2 A6: PC-Rechnerseite nie breiter als das Fenster.

Plan 0.63.2 (S1 A6, Befund T3, Nebenbefund 8): Die Rechnerseite liess sich
seitlich schieben, weil das Raster der USV-Karte ("Last" und "Akku"
nebeneinander) und die Farbtiefe-Knoepfe der Bildschirm-Karte breiter waren
als der sichtbare Bereich. Ab 0.63.2 stehen die beiden USV-Spalten
untereinander, wenn sie nebeneinander nicht passen, und die
Farbtiefe-Knoepfe brechen bei Bedarf um (PillGroup umbrechen=True).

Fuer Normal/Gross/Sehr gross (Faktor 1,00/1,15/1,30), Fenster 1120 x 800 und
1360 x 900, hell und dunkel (je Faktor ein eigener Prozess):
  * kein seitlicher Rollbalken: canvas.xview() == (0.0, 1.0) und die Seite
    ist nicht breiter als der sichtbare Bereich
  * alle USV-Eingabefelder und alle Farbtiefe-Knoepfe sind abgebildet,
    liegen im sichtbaren Bereich und ueberlappen sich nicht
  * Rechnen mit den Vorgaben liefert denselben Text wie der Kern
    (USV-Empfehlung, Bildschirm mit jeder Farbtiefe)
Gegen 14b3bd4 rot.

Start:  xvfb-run -a python test_rechner_seite_breite.py
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

FAKTOREN = {1.0: "normal", 1.15: "gross", 1.3: "sehr_gross"}
FENSTER = ((1120, 800), (1360, 900))


def worker(faktor):
    home = tempfile.mkdtemp(prefix="fisi_a6_")
    os.environ.update(HOME=home, APPDATA=home, FISI_DB_PATH=os.path.join(home, "t.db"),
                      FISI_SELFTEST=os.path.join(home, "log.txt"))
    import customtkinter as ctk
    import app_gui
    import fisi_core as fc
    import fisi_theme
    import fisi_widgets
    if hasattr(app_gui, "apply_appearance"):
        app_gui.apply_appearance()
    fisi_theme.apply_font_size(FAKTOREN[faktor])
    fisi_widgets.apply_ui_scale(faktor)
    app_gui.UpdateController.auto_check = lambda self: None
    app_gui.SyncController.auto_start = lambda self: None
    errors = []
    app_gui.messagebox.showerror = lambda *a, **k: errors.append(a)
    root = ctk.CTk()
    breite, hoehe = FENSTER[0]
    root.geometry("%dx%d+0+0" % (breite, hoehe))
    app = app_gui.FISIApp(root)

    def pump(seconds=0.4):
        end = time.time() + seconds
        while time.time() < end:
            root.update()
            time.sleep(0.01)

    pump(0.8)
    found = []
    werte = {}

    def box(widget):
        x, y = widget.winfo_rootx(), widget.winfo_rooty()
        return x, y, x + widget.winfo_width(), y + widget.winfo_height()

    def overlap(a, b):
        return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]

    for farbe in ("dunkel", "hell"):
        if farbe == "hell":
            app.change_color(mode=fisi_theme.MODE_LIGHT)
            pump(1.5)
        for breite, hoehe in FENSTER:
            app.show_view("calc")
            root.geometry("%dx%d+0+0" % (breite, hoehe))
            pump(1.0)
            view = app.views["calc"]
            canvas = view.canvas
            canvas.xview_moveto(0)
            pump(0.4)
            name = "%s %dx%d %s" % (FAKTOREN[faktor], breite, hoehe, farbe)
            inner_w = view.inner.winfo_reqwidth()
            visible = canvas.winfo_width()
            werte[name] = {"seite": inner_w, "sichtbar": visible,
                           "xview": [round(x, 4) for x in canvas.xview()]}
            if tuple(canvas.xview()) != (0.0, 1.0):
                found.append("%s: seitlicher Rollbalken (xview %r, Seite %d > %d px)"
                             % (name, canvas.xview(), inner_w, visible))
            right = canvas.winfo_rootx() + visible
            widgets = [("USV " + key, entry) for key, entry in view.ups_entries.items()]
            widgets += [("Farbtiefe %d" % i, button)
                        for i, button in enumerate(view.depth_pills.buttons)]
            boxes = []
            for label, widget in widgets:
                if not widget.winfo_ismapped():
                    found.append("%s: %s nicht abgebildet" % (name, label))
                    continue
                b = box(widget)
                if b[2] > right or b[0] < canvas.winfo_rootx():
                    found.append("%s: %s ausserhalb des sichtbaren Bereichs (%r, rechts %d)"
                                 % (name, label, b, right))
                for other_label, other in boxes:
                    if overlap(b, other):
                        found.append("%s: %s ueberlappt %s" % (name, label, other_label))
                boxes.append((label, b))
            # Rechnen mit Vorgaben: Text wie der Kern
            view.calc_ups("empfehlung")
            fields = {key: entry.get() for key, entry in view.ups_entries.items()}
            want = fc.ups_calculate("empfehlung", fields, view.ups_unit.get())["text"]
            if view.txt_ups.get("1.0", "end-1c") != want:
                found.append("%s: USV-Text weicht vom Kern ab" % name)
            for index, (value, _label) in enumerate(app_gui.COLOR_DEPTHS):
                view.depth_pills.select(index)
                view.calc_screen()
                want = fc.screen_report(view.entry_width.get(), view.entry_height.get(),
                                        value, view.entry_fps.get())
                if view.depth_pills.get() != value or \
                        view.txt_screen.get("1.0", "end-1c") != want:
                    found.append("%s: Bildschirm-Text Farbtiefe %r weicht ab" % (name, value))
            view.depth_pills.select(2)
    if errors:
        found.append("Fehlermeldungen: %r" % errors)
    print("ERG " + json.dumps({"fehler": found, "werte": werte}, ensure_ascii=False))
    sys.stdout.flush()
    os._exit(0)


def _tk_ok():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:  # noqa: BLE001
        return False


HAS_DISPLAY = False if "--fall" in sys.argv else _tk_ok()


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class RechnerSeiteBreiteTest(unittest.TestCase):

    def run_case(self, faktor):
        done = subprocess.run([sys.executable, os.path.abspath(__file__), "--fall",
                               str(faktor)],
                              capture_output=True, text=True, timeout=900, cwd=HERE)
        lines = [line for line in done.stdout.splitlines() if line.startswith("ERG ")]
        self.assertTrue(lines, "kein Ergebnis:\n%s\n%s" % (done.stdout[-2000:],
                                                           done.stderr[-4000:]))
        result = json.loads(lines[-1][4:])
        for name, werte in sorted(result["werte"].items()):
            print("\n  %s: %s" % (name, werte), end="")
        print()
        self.assertEqual(result["fehler"], [], FAKTOREN[faktor])
        self.assertEqual(len(result["werte"]), 2 * len(FENSTER))


def _make(faktor):
    def test(self):
        self.run_case(faktor)
    return test


for _faktor in FAKTOREN:
    setattr(RechnerSeiteBreiteTest, "test_%s" % FAKTOREN[_faktor], _make(_faktor))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--fall":
        worker(float(sys.argv[2]))
    unittest.main(verbosity=2)
