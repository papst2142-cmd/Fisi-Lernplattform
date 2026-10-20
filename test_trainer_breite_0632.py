#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests 0.63.2 N8 (N-e): Rechen-Trainer am PC nie breiter als der sichtbare
Bereich.

Plan-Nachtrag 0.63.2 Nr. 46 (N-e, Fund aus S1a): Bei Sehr gross und 1120 px
war die Seite des Trainer-Reiters breiter als sichtbar (berichtet 848 > 781).
Ab 0.63.2 folgt die Umbruchbreite des Aufgabentexts der Kartenbreite, und die
Felder einer Aufgabe brechen bei Platzmangel um (Beschriftung ueber dem Feld,
Muster der A6-Regel "unter das Feld").

Fuer Normal/Gross/Sehr gross (je Faktor ein eigener Prozess), Fenster
1120 x 720 und 1360 x 900, hell und dunkel, jede Aufgabenart (6) und Stufe
(3) mit festem Startwert - je Runde die Aufgabe mit dem laengsten Text und
die mit den meisten Feldern (Testplan N8 K60):
  * kein seitlicher Rollbalken (canvas.xview() == (0.0, 1.0)), Seite nicht
    breiter als der sichtbare Bereich
  * jedes Eingabefeld abgebildet und ganz im sichtbaren Bereich, Felder
    ueberlappen sich nicht, die Beschriftung steht beim Feld (links daneben
    in derselben Zeile oder direkt darueber, linksbuendig)
  * der Aufgabentext passt in seine Umbruchbreite (Tk teilt nicht weiter)
Jeder Fall laeuft zweimal: mit der Standardschrift und mit abgelehnter
Standardschrift (fontconfig, Muster test_spiel_breite_0632/N5: im Container
DejaVu Sans wie auf GitHub, auf GitHub eine dritte Schrift).
NoOpTest (K61): Normal 1360 mit der Standardschrift - Aufgabentext und Felder
stehen wie bisher (eine Zeile je Feld, Beschriftung links, Umbruchbreite 900).

CI-Teil: "breite" (FG-96; bis die Datei dort eingetragen ist, laeuft sie
in "rest").

Start:  xvfb-run -a python test_trainer_breite_0632.py
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
FENSTER = ((1120, 720), (1360, 900))
STARTWERT = 6302


def _faelle():
    """(Art, Stufe, Index) - je Runde die Aufgabe mit dem laengsten Text und
    die mit den meisten Feldern (fester Startwert)."""
    import fisi_lernen as fl
    faelle = []
    for kind, _name in fl.TRAINER_KINDS:
        for level, _lname in fl.TRAINER_LEVELS:
            runde = fl.trainer_round(kind, level, STARTWERT)
            laengster = max(range(len(runde)), key=lambda i: len(runde[i].text))
            meiste = max(range(len(runde)), key=lambda i: len(runde[i].fields))
            for index in sorted({laengster, meiste}):
                faelle.append((kind, level, index))
    return faelle


def worker(faktor):
    home = tempfile.mkdtemp(prefix="fisi_ne_")
    os.environ.update(HOME=home, APPDATA=home, FISI_DB_PATH=os.path.join(home, "t.db"),
                      FISI_SELFTEST=os.path.join(home, "log.txt"))
    import customtkinter as ctk
    import tkinter.font as tkfont
    import app_gui
    import fisi_lernen as fl
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
    root.geometry("%dx%d+0+0" % FENSTER[0])
    app = app_gui.FISIApp(root)

    def pump(seconds=0.3):
        end = time.time() + seconds
        while time.time() < end:
            root.update()
            time.sleep(0.01)

    def box(widget):
        x, y = widget.winfo_rootx(), widget.winfo_rooty()
        return x, y, x + widget.winfo_width(), y + widget.winfo_height()

    def overlap(a, b):
        return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]

    pump(0.8)
    faelle = _faelle()
    found, werte, noop = [], {}, {}
    start = time.time()
    for farbe in ("dunkel", "hell"):
        if farbe == "hell":
            app.change_color(mode=fisi_theme.MODE_LIGHT)
            pump(1.5)
        for breite, hoehe in FENSTER:
            app.show_view("calc")
            root.geometry("%dx%d+0+0" % (breite, hoehe))
            pump(0.8)
            view = app.views["calc"]
            view.tab_pills.select(1)
            view._on_tab("trainer")
            pump(0.5)
            panel = view.trainer
            canvas = view.canvas
            left_edge = canvas.winfo_rootx()
            for kind, level, index in faelle:
                panel.tasks = fl.trainer_round(kind, level, STARTWERT)
                panel.index = index
                panel.results = []
                panel.load_task()
                pump(0.25)
                canvas.xview_moveto(0)
                pump(0.05)
                name = "%s %dx%d %s %s/%d #%d" % (FAKTOREN[faktor], breite, hoehe, farbe,
                                                  kind, level, index)
                seite, sichtbar = view.inner.winfo_reqwidth(), canvas.winfo_width()
                werte[name] = [seite, sichtbar]
                if tuple(canvas.xview()) != (0.0, 1.0) or seite > sichtbar:
                    found.append("%s: seitlicher Rollbalken (xview %r, Seite %d > %d px)"
                                 % (name, canvas.xview(), seite, sichtbar))
                right = left_edge + sichtbar
                # Aufgabentext: jede Zeile, die Tk zeigt, passt in die Umbruchbreite
                label = panel.lbl_task
                wrap = label._label.cget("wraplength")
                font = tkfont.Font(font=label._label.cget("font"))
                for zeile in str(label.cget("text")).split("\n"):
                    if wrap and font.measure(zeile) > int(wrap) + 1 and " " not in zeile:
                        found.append("%s: Aufgabentext-Zeile breiter als Umbruchbreite"
                                     % name)
                if box(label)[2] > right:
                    found.append("%s: Aufgabentext ragt ueber den Rand (%r, rechts %d)"
                                 % (name, box(label), right))
                boxes = []
                for key, beschriftung in panel.tasks[index].fields:
                    entry = panel.entries[key]
                    if not entry.winfo_ismapped():
                        found.append("%s: Feld %s nicht abgebildet" % (name, key))
                        continue
                    b = box(entry)
                    if b[2] > right or b[0] < left_edge:
                        found.append("%s: Feld %s ausserhalb (%r, rechts %d)"
                                     % (name, key, b, right))
                    for other_key, other in boxes:
                        if overlap(b, other):
                            found.append("%s: Feld %s ueberlappt %s" % (name, key, other_key))
                    boxes.append((key, b))
                    lab = [w for w in panel.fields_box.grid_slaves()
                           if isinstance(w, ctk.CTkLabel) and w.cget("text") == beschriftung]
                    if not lab:
                        found.append("%s: Beschriftung %r fehlt" % (name, beschriftung))
                        continue
                    lb = box(lab[0])
                    daneben = lb[2] <= b[0] and lb[1] < b[3] and b[1] < lb[3]
                    darueber = lb[3] <= b[1] + 1 and b[1] - lb[3] <= 12 and \
                        abs(lb[0] - b[0]) <= 2
                    if not (daneben or darueber):
                        found.append("%s: Beschriftung %r nicht beim Feld (%r / %r)"
                                     % (name, beschriftung, lb, b))
                    if lb[2] > right:
                        found.append("%s: Beschriftung %r ausserhalb" % (name, beschriftung))
                if FAKTOREN[faktor] == "normal" and breite == 1360:
                    noop[name] = {
                        "wrap": int(wrap or 0),
                        # Zeile der Beschriftung == Zeile ihres Felds
                        # (auch auf dem alten Stand ohne field_labels messbar)
                        "neben_feld": [
                            any(isinstance(w, ctk.CTkLabel) and w.cget("text") == beschr and
                                int(w.grid_info()["row"]) ==
                                int(panel.entries[k].grid_info()["row"]) and
                                int(w.grid_info()["column"]) == 0
                                for w in panel.fields_box.grid_slaves())
                            for k, beschr in panel.tasks[index].fields],
                        "gestapelt": bool(getattr(panel, "fields_stacked", False)),
                        "spalte_beschriftung": sorted({
                            int(w.grid_info()["column"]) for w in panel.fields_box.grid_slaves()
                            if isinstance(w, ctk.CTkLabel) and
                            w.cget("text") in dict(panel.tasks[index].fields).values()})}
    if errors:
        found.append("Fehlermeldungen: %r" % errors)
    print("ERG " + json.dumps({"fehler": found, "werte": werte, "noop": noop,
                               "faelle": len(faelle), "dauer": round(time.time() - start, 1),
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
    """fontconfig-Datei wie die des eigenen Prozesses, lehnt aber family (und
    ihre Display-Variante) ab (Muster test_rechner_seite_breite)."""
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
    key = (faktor, ohne)
    if key not in _ERGEBNISSE:
        env = dict(os.environ)
        if ohne:
            env["FONTCONFIG_FILE"] = _fc_ohne(ohne)
        done = subprocess.run([sys.executable, os.path.abspath(__file__), "--fall",
                               str(faktor)],
                              capture_output=True, text=True, timeout=1200, cwd=HERE, env=env)
        lines = [line for line in done.stdout.splitlines() if line.startswith("ERG ")]
        _ERGEBNISSE[key] = (json.loads(lines[-1][4:]) if lines else
                            "kein Ergebnis:\n%s\n%s" % (done.stdout[-2000:],
                                                        done.stderr[-4000:]))
    return _ERGEBNISSE[key]


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class TrainerBreiteTest(unittest.TestCase):

    def pruefen(self, faktor, ohne=None):
        result = ergebnis(faktor, ohne)
        self.assertIsInstance(result, dict, result)
        groesste = max(result["werte"].items(), key=lambda kv: kv[1][0] - kv[1][1])
        print("\n  Schrift %s, %d Faelle, %s s, knappster Fall %s: Seite %d / sichtbar %d"
              % (result["schrift"], result["faelle"], result["dauer"], groesste[0],
                 groesste[1][0], groesste[1][1]))
        self.assertEqual(result["fehler"], [], FAKTOREN[faktor])
        self.assertEqual(len(result["werte"]), result["faelle"] * 2 * len(FENSTER))
        return result


class TrainerSchriftwechselTest(TrainerBreiteTest):
    """Dieselben Faelle mit abgelehnter Standardschrift."""

    def pruefen(self, faktor, ohne=None):
        standard = ergebnis(1.0)
        self.assertIsInstance(standard, dict, standard)
        result = super().pruefen(faktor, standard["schrift"])
        self.assertNotEqual(result["schrift"], standard["schrift"],
                            "fontconfig hat die Schrift nicht gewechselt")


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class TrainerNoOpTest(unittest.TestCase):
    """K61: Normal 1360, Standardschrift - Felder wie bisher (Beschriftung
    links in Spalte 0, in derselben Rasterzeile wie ihr Feld, nicht
    gestapelt), Umbruchbreite des Aufgabentexts 900. Ab N8 hat jedes Feld
    drei Rasterzeilen (3r, 3r+1, 3r+2); die leeren Zeilen haben Hoehe 0."""

    def test_normal_1360_wie_bisher(self):
        result = ergebnis(1.0)
        self.assertIsInstance(result, dict, result)
        self.assertTrue(result["noop"])
        for name, werte in sorted(result["noop"].items()):
            self.assertEqual(werte["wrap"], 900, name)
            self.assertEqual(werte["spalte_beschriftung"], [0], name)
            self.assertFalse(werte["gestapelt"], name)
            self.assertTrue(werte["neben_feld"] and all(werte["neben_feld"]), (name, werte))


def _make(faktor):
    def test(self):
        self.pruefen(faktor)
    return test


for _faktor in FAKTOREN:
    setattr(TrainerBreiteTest, "test_%s" % FAKTOREN[_faktor], _make(_faktor))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--fall":
        worker(float(sys.argv[2]))
    unittest.main(verbosity=2)
