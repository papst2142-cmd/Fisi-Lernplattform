#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests 0.63.2 N8 (B-J-N3, Testplan K33): Die Startknoepfe der Pruefung
("<Kurzname> starten", N8-F4) passen in ihre Zeile.

Der laengere Knopftext machte die Zeilen der Pruefungsauswahl bei Sehr gross
und 1120 px breiter als den sichtbaren Bereich (gemessen 891 > 781; schon
vorher 788 > 781). Ab 0.63.2 brechen Name und Angaben links neben dem Knopf
um, wenn sie sonst nicht passen (ExamPanel._fit_start_rows).

Je Faktor Normal/Gross/Sehr gross ein eigener Prozess, Fenster 1120 x 720 und
1360 x 900, hell und dunkel, Standardschrift und abgelehnte Standardschrift
(fontconfig, Muster test_trainer_breite_0632):
  * kein seitlicher Rollbalken (canvas.xview() == (0.0, 1.0)), Seite nicht
    breiter als der sichtbare Bereich
  * jeder der vier Knoepfe ganz im sichtbaren Bereich und in seiner Zeile,
    Name und Angaben ueberlappen den Knopf nicht, nichts abgeschnitten
    (Text passt in seine Umbruchbreite)
  * die Knopftexte sind paarweise verschieden
NoOpTest: Normal 1360 mit der Standardschrift - keine Umbruchbreite gesetzt
(Name und Angaben wie bisher in einer Zeile).

CI-Teil: "breite" (FG-96; bis die Datei dort eingetragen ist, laeuft sie
in "rest").

Start:  xvfb-run -a python test_startzeilen_breite_0632.py
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


def worker(faktor):
    home = tempfile.mkdtemp(prefix="fisi_k33_")
    os.environ.update(HOME=home, APPDATA=home, FISI_DB_PATH=os.path.join(home, "t.db"),
                      FISI_SELFTEST=os.path.join(home, "log.txt"))
    import customtkinter as ctk
    import tkinter.font as tkfont
    import app_gui
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
    found, werte, noop = [], {}, {}
    for farbe in ("dunkel", "hell"):
        if farbe == "hell":
            app.change_color(mode=fisi_theme.MODE_LIGHT)
            pump(1.5)
        for breite, hoehe in FENSTER:
            root.geometry("%dx%d+0+0" % (breite, hoehe))
            pump(1.0)
            app.show_view("quiz")
            pump(0.6)
            view = app.views["quiz"]
            view.mode_pills.select_value("pruefung")
            pump(1.2)
            panel = view.exam
            panel.show_choice()
            pump(1.2)
            name = "%s %dx%d %s" % (FAKTOREN[faktor], breite, hoehe, farbe)
            canvas = view.canvas
            sichtbar = box(canvas)
            seite = view.inner.winfo_reqwidth()
            werte[name] = [seite, canvas.winfo_width()]
            if tuple(round(v, 3) for v in canvas.xview()) != (0.0, 1.0) or \
                    seite > canvas.winfo_width():
                found.append("%s: Seite %d breiter als sichtbar %d (xview %r)"
                             % (name, seite, canvas.winfo_width(), canvas.xview()))
            knoepfe, stapel = [], [panel]
            while stapel:
                widget = stapel.pop(0)
                if isinstance(widget, fisi_widgets.NeoButton) and \
                        str(widget.cget("text")).endswith(" starten"):
                    knoepfe.append(widget)
                stapel.extend(widget.winfo_children())
            texte = [str(k.cget("text")) for k in knoepfe]
            if len(knoepfe) != 4 or len(set(texte)) != 4:
                found.append("%s: Startknoepfe %r" % (name, texte))
                continue
            for knopf in knoepfe:
                kb, zeile = box(knopf), box(knopf.master)
                if kb[0] < sichtbar[0] or kb[2] > sichtbar[2] or not knopf.winfo_ismapped():
                    found.append("%s: Knopf %r ausserhalb des sichtbaren Bereichs %r / %r"
                                 % (name, knopf.cget("text"), kb, sichtbar))
                if kb[0] < zeile[0] or kb[2] > zeile[2]:
                    found.append("%s: Knopf %r ragt aus seiner Zeile" % (name, knopf.cget("text")))
                textbereich = [c for c in knopf.master.winfo_children() if c is not knopf][0]
                for label in textbereich.winfo_children():
                    lb = box(label)
                    if overlap(lb, kb) or lb[2] > kb[0]:
                        found.append("%s: %r ueberlappt den Knopf %r"
                                     % (name, label.cget("text"), knopf.cget("text")))
                    if lb[2] > sichtbar[2]:
                        found.append("%s: %r rechts abgeschnitten" % (name, label.cget("text")))
                    wrap = float(label.cget("wraplength") or 0)
                    font = tkfont.Font(font=label._label.cget("font"))
                    scale = app_gui.px(1000) / 1000.0
                    if wrap:
                        for wort in str(label.cget("text")).split(" "):
                            if font.measure(wort) > wrap * scale + 1:
                                found.append("%s: Wort %r breiter als die Umbruchbreite"
                                             % (name, wort))
                    if FAKTOREN[faktor] == "normal" and breite == 1360:
                        noop["%s|%s|%s" % (farbe, knopf.cget("text"),
                                          label.cget("text"))] = wrap
    if errors:
        found.append("Fehlermeldungen: %r" % errors)
    print("ERG " + json.dumps({"fehler": found, "werte": werte, "noop": noop,
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
                              capture_output=True, text=True, timeout=900, cwd=HERE, env=env)
        lines = [line for line in done.stdout.splitlines() if line.startswith("ERG ")]
        _ERGEBNISSE[key] = (json.loads(lines[-1][4:]) if lines else
                            "kein Ergebnis:\n%s\n%s" % (done.stdout[-2000:],
                                                        done.stderr[-4000:]))
    return _ERGEBNISSE[key]


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class StartzeilenBreiteTest(unittest.TestCase):

    def pruefen(self, faktor, ohne=None):
        result = ergebnis(faktor, ohne)
        self.assertIsInstance(result, dict, result)
        knapp = max(result["werte"].items(), key=lambda kv: kv[1][0] - kv[1][1])
        print("\n  Schrift %s, knappster Fall %s: Seite %d / sichtbar %d"
              % (result["schrift"], knapp[0], knapp[1][0], knapp[1][1]))
        self.assertEqual(result["fehler"], [], FAKTOREN[faktor])
        self.assertEqual(len(result["werte"]), 2 * len(FENSTER))
        return result


class StartzeilenSchriftwechselTest(StartzeilenBreiteTest):
    """Dieselben Faelle mit abgelehnter Standardschrift."""

    def pruefen(self, faktor, ohne=None):
        standard = ergebnis(1.0)
        self.assertIsInstance(standard, dict, standard)
        result = super().pruefen(faktor, standard["schrift"])
        self.assertNotEqual(result["schrift"], standard["schrift"],
                            "fontconfig hat die Schrift nicht gewechselt")


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class StartzeilenNoOpTest(unittest.TestCase):
    """Normal 1360, Standardschrift: Name und Angaben ohne Umbruchbreite."""

    def test_normal_1360_wie_bisher(self):
        result = ergebnis(1.0)
        self.assertIsInstance(result, dict, result)
        self.assertEqual(len(result["noop"]), 2 * 4 * 2, result["noop"])
        self.assertEqual({k: v for k, v in result["noop"].items() if v}, {})


def _make(faktor):
    def test(self):
        self.pruefen(faktor)
    return test


for _faktor in FAKTOREN:
    setattr(StartzeilenBreiteTest, "test_%s" % FAKTOREN[_faktor], _make(_faktor))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--fall":
        worker(float(sys.argv[2]))
    unittest.main(verbosity=2)
