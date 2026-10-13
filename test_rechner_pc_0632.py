#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests 0.63.2 A7 und A9 (PC-Subnetting-Karte).

A7: Der Kasten "Netzdaten" IPv4 zeigt nach "Berechnen" alle Zeilen (bisher
    9 feste Zeilen Hoehe; der Kasten war gerollt bzw. die letzte Zeile
    "Präfixlänge" nur teilweise oder erst nach Rollen zu sehen). Fuer Normal/Gross/Sehr gross,
    Fenster 1120 x 720 und 1120 x 800: Anzeigezeilen <= sichtbare Zeilen, der
    Kasten ist nicht gerollt und die letzte Zeile ("Präfixlänge") sichtbar.
    Je Schriftgroesse ein eigener Prozess.
(A9 folgt im eigenen Commit.)

Gegen 14b3bd4 rot. Start:  xvfb-run -a python test_rechner_pc_0632.py
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
FENSTER = ((1120, 720), (1120, 800))


def worker(faktor, breite, hoehe):
    home = tempfile.mkdtemp(prefix="fisi_a7_")
    os.environ.update(HOME=home, APPDATA=home, FISI_DB_PATH=os.path.join(home, "t.db"),
                      FISI_SELFTEST=os.path.join(home, "log.txt"))
    import customtkinter as ctk
    import app_gui
    import fisi_theme
    import fisi_widgets
    fisi_theme.apply_font_size(FAKTOREN[faktor])
    fisi_widgets.apply_ui_scale(faktor)
    app_gui.UpdateController.auto_check = lambda self: None
    app_gui.SyncController.auto_start = lambda self: None
    errors = []
    app_gui.messagebox.showerror = lambda *a, **k: errors.append(a)
    root = ctk.CTk()
    root.geometry("%dx%d+0+0" % (breite, hoehe))
    app = app_gui.FISIApp(root)

    def pump(seconds=0.4):
        end = time.time() + seconds
        while time.time() < end:
            root.update()
            time.sleep(0.01)

    pump(0.8)
    app.show_view("calc")
    root.geometry("%dx%d+0+0" % (breite, hoehe))
    pump(0.8)
    sub = app.views["calc"].subnet
    found = []
    werte = {}
    for net in ("192.168.1.50/24", "10.0.0.0/8", "172.16.5.4/30"):
        sub.mode_pills.select_value("ipv4")
        sub.view_pills["ipv4"].select_value("netzdaten")
        data = sub.views[("ipv4", "netzdaten")]
        data["net"].set(net)
        sub.calc("ipv4", "netzdaten")
        pump()
        box = data["box"]
        text = box._textbox
        shown = box.get("1.0", "end-1c")
        lines = shown.split("\n")
        display = int(text.count("1.0", "end", "displaylines")[0])
        last = len(lines)
        info = text.dlineinfo("%d.0" % last)
        werte[net] = {"zeilen": last, "anzeige": display, "chars": box.fit_chars,
                      "yview": [round(x, 3) for x in text.yview()]}
        if info is None:
            found.append("%s: letzte Zeile %r nicht sichtbar" % (net, lines[-1]))
        elif info[1] + info[3] > text.winfo_height():
            found.append("%s: letzte Zeile %r nur teilweise sichtbar" % (net, lines[-1]))
        if text.yview() != (0.0, 1.0):
            found.append("%s: Kasten gerollt bzw. Zeilen versteckt (yview %r)"
                         % (net, text.yview()))
        if not any(line.startswith("Präfixlänge") for line in lines) and \
                "Präfixlänge:" not in lines:
            found.append("%s: keine Zeile Präfixlänge" % net)
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
class A7NetzdatenTest(unittest.TestCase):

    def run_case(self, faktor, breite, hoehe):
        done = subprocess.run([sys.executable, os.path.abspath(__file__), "--fall",
                               str(faktor), str(breite), str(hoehe)],
                              capture_output=True, text=True, timeout=600, cwd=HERE)
        lines = [line for line in done.stdout.splitlines() if line.startswith("ERG ")]
        self.assertTrue(lines, "kein Ergebnis:\n%s\n%s" % (done.stdout[-2000:],
                                                           done.stderr[-4000:]))
        result = json.loads(lines[-1][4:])
        print("\n  %s %dx%d: %s" % (FAKTOREN[faktor], breite, hoehe, result["werte"]))
        self.assertEqual(result["fehler"], [], "%s %dx%d" % (FAKTOREN[faktor], breite, hoehe))


def _make(faktor, breite, hoehe):
    def test(self):
        self.run_case(faktor, breite, hoehe)
    return test


for _faktor in FAKTOREN:
    for _breite, _hoehe in FENSTER:
        setattr(A7NetzdatenTest, "test_%s_%dx%d" % (FAKTOREN[_faktor], _breite, _hoehe),
                _make(_faktor, _breite, _hoehe))


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "--fall":
        worker(float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]))
    unittest.main(verbosity=2)
