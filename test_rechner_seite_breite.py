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
  * stehen die USV-Spalten untereinander, beginnen alle Felder an derselben
    Stelle (Gegenpruefung S1a, L3)
  * Rechnen mit den Vorgaben liefert denselben Text wie der Kern
    (USV-Empfehlung, Bildschirm mit jeder Farbtiefe)
Gegen 14b3bd4 rot.

Ab CI Welle 3b (0.63.2): Auf GitHub fehlt die Schrift Inter, dort waehlt die
App DejaVu Sans (breiter); bei Sehr gross und 1120 px war die Seite dann
29 px breiter als sichtbar (RAID-Auswahl und USV-Knopfzeile ohne Umbruch).
Deshalb zusaetzlich:
  * auch RAID-Level-Knoepfe und alle Knoepfe der USV-Karte liegen im
    sichtbaren Bereich und ueberlappen sich nicht, auch mit aufgedeckter
    Loesung der Uebungsaufgabe (laengerer Knopftext)
  * SchriftwechselTest: dasselbe mit einer anderen Schrift - die
    Standardschrift wird per fontconfig abgelehnt (im Container DejaVu Sans
    statt Inter wie auf GitHub, auf GitHub eine dritte Schrift); der Test
    prueft, dass wirklich eine andere Schrift gewaehlt wurde.

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
            widgets += [("RAID %d" % i, button)
                        for i, button in enumerate(view.raid_pills.buttons)]
            widgets += [("USV-Knopf %r" % str(button.cget("text"))[:24], button)
                        for row in view.ups_button_rows for button in row.winfo_children()]
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
            # Gegenpruefung S1a (L3): untereinander beginnen alle USV-Felder
            # beider Spalten an derselben Stelle
            load_box, battery_box = view.ups_boxes
            stacked = battery_box.winfo_rooty() >= load_box.winfo_rooty() + load_box.winfo_height()
            starts = sorted({entry.winfo_rootx() for entry in view.ups_entries.values()})
            werte[name]["usv_untereinander"] = stacked
            werte[name]["usv_feldanfang"] = starts
            if stacked and len(starts) != 1:
                found.append("%s: USV-Felder untereinander nicht buendig (x %r)"
                             % (name, starts))
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
            # Loesung der Uebungsaufgabe aufdecken: laengerer Knopftext
            view.toggle_ups_solution()
            pump(0.6)
            name_l = name + " Loesung"
            if tuple(canvas.xview()) != (0.0, 1.0) or \
                    view.inner.winfo_reqwidth() > canvas.winfo_width():
                found.append("%s: seitlicher Rollbalken (xview %r, Seite %d > %d px)"
                             % (name_l, canvas.xview(), view.inner.winfo_reqwidth(),
                                canvas.winfo_width()))
            boxes = []
            for row in view.ups_button_rows:
                for button in row.winfo_children():
                    b = box(button)
                    label = "USV-Knopf %r" % str(button.cget("text"))[:24]
                    if b[2] > right or b[0] < canvas.winfo_rootx():
                        found.append("%s: %s ausserhalb des sichtbaren Bereichs (%r, rechts %d)"
                                     % (name_l, label, b, right))
                    if button.winfo_width() < button.winfo_reqwidth() - 2:
                        found.append("%s: %s schmaler als verlangt (%d < %d)"
                                     % (name_l, label, button.winfo_width(),
                                        button.winfo_reqwidth()))
                    for other_label, other in boxes:
                        if overlap(b, other):
                            found.append("%s: %s ueberlappt %s" % (name_l, label, other_label))
                    boxes.append((label, b))
            view.toggle_ups_solution()
            pump(0.4)
    if errors:
        found.append("Fehlermeldungen: %r" % errors)
    print("ERG " + json.dumps({"fehler": found, "werte": werte,
                               "schrift": fisi_widgets.F.get("family")}, ensure_ascii=False))
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


def _fc_ohne(family):
    """fontconfig-Datei, die die Einstellungen des eigenen Prozesses nutzt
    (ein gesetztes FONTCONFIG_FILE, sonst die des Systems), aber zusaetzlich
    family (und ihre Display-Variante) ablehnt (Muster aus N5,
    test_spiel_breite_0632)."""
    path = os.path.join(tempfile.mkdtemp(prefix="fisi_fc_"), "fonts.conf")
    basis = os.path.abspath(os.environ.get("FONTCONFIG_FILE") or "/etc/fonts/fonts.conf")
    patterns = "".join(
        "<pattern><patelt name=\"family\"><string>%s</string></patelt></pattern>" % name
        for name in (family, family + " Display"))
    with open(path, "w", encoding="utf-8") as handle:
        handle.write('<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n'
                     '<fontconfig><include ignore_missing="yes">%s</include>'
                     '<selectfont><rejectfont>%s</rejectfont></selectfont>'
                     '</fontconfig>\n' % (basis, patterns))
    return path


_ERGEBNISSE = {}


def ergebnis(faktor, ohne=None):
    """Ergebnis eines Kindprozesses (zwischengespeichert); ohne = abgelehnte
    Schrift."""
    key = (faktor, ohne)
    if key not in _ERGEBNISSE:
        env = dict(os.environ)
        if ohne:
            env["FONTCONFIG_FILE"] = _fc_ohne(ohne)
        done = subprocess.run([sys.executable, os.path.abspath(__file__), "--fall",
                               str(faktor)],
                              capture_output=True, text=True, timeout=900, cwd=HERE, env=env)
        lines = [line for line in done.stdout.splitlines() if line.startswith("ERG ")]
        _ERGEBNISSE[key] = (json.loads(lines[-1][4:]) if lines else
                            "kein Ergebnis:\n%s\n%s" % (done.stdout[-2000:],
                                                        done.stderr[-4000:]))
    return _ERGEBNISSE[key]


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class RechnerSeiteBreiteTest(unittest.TestCase):

    def run_case(self, faktor, ohne=None):
        result = ergebnis(faktor, ohne)
        self.assertIsInstance(result, dict, result)
        print("\n  Schrift: %s" % result["schrift"], end="")
        for name, werte in sorted(result["werte"].items()):
            print("\n  %s: %s" % (name, werte), end="")
        print()
        self.assertEqual(result["fehler"], [], "%s (Schrift %s)" % (FAKTOREN[faktor],
                                                                   result["schrift"]))
        self.assertEqual(len(result["werte"]), 2 * len(FENSTER))
        return result


def _make(faktor):
    def test(self):
        self.run_case(faktor)
    return test


for _faktor in FAKTOREN:
    setattr(RechnerSeiteBreiteTest, "test_%s" % FAKTOREN[_faktor], _make(_faktor))


class SchriftwechselTest(RechnerSeiteBreiteTest):
    """Dasselbe mit einer anderen Schrift (andere Schriftmetrik): die
    Standardschrift wird abgelehnt - im Container DejaVu Sans statt Inter,
    genau die Schrift des GitHub-Rechners."""


def _make_ohne(faktor):
    def test(self):
        standard = ergebnis(faktor)
        self.assertIsInstance(standard, dict, standard)
        result = self.run_case(faktor, ohne=standard["schrift"])
        self.assertNotEqual(result["schrift"], standard["schrift"],
                            "Schrift nicht gewechselt")
    return test


for _faktor in FAKTOREN:
    setattr(SchriftwechselTest, "test_%s" % FAKTOREN[_faktor], _make_ohne(_faktor))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--fall":
        worker(float(sys.argv[2]))
    unittest.main(verbosity=2)
