#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests ab 0.63.1 (Plan 0.63.1 Teil 1.2, Abschnitt 4.3): PC-Pillenzeile
"Aufgabenart" im Trainer bricht bei Bedarf um.

  * Bei 1120 x 720 und Schriftfaktor 1,00 / 1,15 / 1,30 liegt jede Pille
    ganz im Kartenkoerper, die letzte ("Nach Hostbedarf") ist abgebildet und
    vollstaendig, die Seite hat keinen waagrechten Rollbalken.
  * Reihenfolge (links nach rechts, Zeile fuer Zeile) und Text der Pillen
    gleich TRAINER_KINDS; Auswahl/get() unveraendert.
  * Alle anderen PillGroup-Nutzer (ohne umbrechen) bleiben nebeneinander
    gepackt wie vorher (Geometrie bei 1360).

Hat TRAINER_KINDS noch keine sechs Arten (Zweig ohne Trainer T5), haengt der
Test fuer die Pruefung die beiden T5-Arten mit ihrem Wortlaut an (nur im
Testprozess), damit der Fall mit sechs Pillen immer geprueft wird.

Je Schriftfaktor laeuft ein eigener Prozess (die Schriftgroesse gilt ab dem
Erzeugen des Fensters). Start:  xvfb-run -a python test_pillen_pc.py
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

# Wortlaut der beiden Arten aus Trainer T5 (version-0631-trainer, fisi_lernen.py)
T5_ARTEN = [("teilen", "Netz aufteilen"), ("bedarf", "Nach Hostbedarf")]
FAKTOREN = {1.0: "normal", 1.15: "gross", 1.3: "sehr_gross"}


def _tk_ok():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:  # noqa: BLE001
        return False


def _kind_messen(faktor, breite, hoehe):
    """Kindprozess: baut das echte Fenster, oeffnet den Trainer und liefert
    die Geometrie der Pillen als JSON auf stdout."""
    home = tempfile.mkdtemp(prefix="fisi_pillen_pc_")
    os.environ.update(HOME=home, FISI_DB_PATH=os.path.join(home, "pillen.db"),
                      FISI_SELFTEST=os.path.join(home, "selbsttest.log"))
    os.environ.pop("FISI_VORLADEN", None)
    import customtkinter as ctk
    import app_gui
    import fisi_theme
    import fisi_widgets
    if len(app_gui.TRAINER_KINDS) < 6:
        app_gui.TRAINER_KINDS = list(app_gui.TRAINER_KINDS) + [
            kind for kind in T5_ARTEN if kind not in app_gui.TRAINER_KINDS]
    app_gui.apply_appearance()
    fisi_theme.apply_font_size(FAKTOREN[faktor])
    fisi_widgets.apply_ui_scale(faktor)
    app_gui.UpdateController.auto_check = lambda self: None
    app_gui.SyncController.auto_start = lambda self: None
    app_gui.messagebox.showerror = lambda *args, **kwargs: None
    root = ctk.CTk()
    root.geometry("%dx%d+0+0" % (breite, hoehe))
    app = app_gui.FISIApp(root)

    def pump(dauer):
        ende = time.time() + dauer
        while time.time() < ende:
            root.update()
            time.sleep(0.01)
    pump(0.5)
    root.geometry("%dx%d+0+0" % (breite, hoehe))
    pump(0.5)
    app.show_view("calc")
    pump(0.5)
    view = app.views["calc"]
    view._on_tab("trainer")
    pump(0.8)

    def rect(widget):
        return [widget.winfo_rootx(), widget.winfo_rooty(),
                widget.winfo_width(), widget.winfo_height()]

    pills = view.trainer.kind_pills
    body = pills.master
    erg = {
        "faktor": faktor, "breite": breite,
        "kinds": [list(kind) for kind in app_gui.TRAINER_KINDS],
        "body": rect(body),
        "fenster": rect(root),
        "canvas_breite": view.canvas.winfo_width(),
        "inner_breite": view.inner.winfo_width(),
        "xview": list(view.canvas.xview()),
        "hbar_sichtbar": bool(view.hscrollbar.winfo_manager()
                              and view.hscrollbar.winfo_ismapped()),
        "pillen": [{"text": button.cget("text"), "rect": rect(button),
                    "req": button.winfo_reqwidth(),
                    "sichtbar": bool(button.winfo_ismapped())}
                   for button in pills.buttons],
        "gap": pills._apply_widget_scaling(8),
    }
    # Auswahl/get() unveraendert
    auswahl = []
    for index, value in enumerate(pills.values):
        pills.select(index)
        auswahl.append([value, pills.get(), pills.buttons[index]._active])
    pills.select(0)
    erg["auswahl"] = auswahl
    # Bestand: alle anderen Pillengruppen der Rechner-Ansicht (ohne umbrechen)
    andere = []
    for name, group in (("tab_pills", view.tab_pills),
                        ("level_pills", view.trainer.level_pills)):
        andere.append({"name": name,
                       "manager": [button.winfo_manager() for button in group.buttons],
                       "rects": [rect(button) for button in group.buttons]})
    erg["andere"] = andere
    print("ERGEBNIS " + json.dumps(erg))
    sys.stdout.flush()
    root.destroy()


def _messen(faktor, breite=1120, hoehe=720):
    proc = subprocess.run(
        [sys.executable, os.path.abspath(__file__), "--kind", str(faktor), str(breite),
         str(hoehe)], capture_output=True, text=True, timeout=300, cwd=HERE)
    for line in proc.stdout.splitlines():
        if line.startswith("ERGEBNIS "):
            return json.loads(line[len("ERGEBNIS "):])
    raise AssertionError("Kindprozess ohne Ergebnis (rc %s):\n%s\n%s"
                         % (proc.returncode, proc.stdout[-2000:], proc.stderr[-4000:]))


HAS_DISPLAY = _tk_ok()
_CACHE = {}


def _ergebnis(faktor, breite=1120, hoehe=720):
    key = (faktor, breite, hoehe)
    if key not in _CACHE:
        _CACHE[key] = _messen(faktor, breite, hoehe)
    return _CACHE[key]


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class PillenUmbruchTest(unittest.TestCase):
    """Plan 4.3: 1120 x 720, Faktor 1,00 / 1,15 / 1,30."""

    def pruefe_faktor(self, faktor):
        erg = _ergebnis(faktor)
        bx, _by, bw, _bh = erg["body"]
        self.assertGreaterEqual(len(erg["pillen"]), 6)
        for pille in erg["pillen"]:
            x, _y, w, _h = pille["rect"]
            with self.subTest(faktor=faktor, pille=pille["text"]):
                self.assertTrue(pille["sichtbar"], "nicht abgebildet")
                self.assertGreaterEqual(x, bx, "links ausserhalb des Kartenkoerpers")
                self.assertLessEqual(x + w, bx + bw, "rechte Kante ausserhalb des "
                                     "Kartenkoerpers")
                self.assertGreaterEqual(w, pille["req"], "Pille abgeschnitten")
        # "Nach Hostbedarf" abgebildet und vollstaendig
        letzte = [p for p in erg["pillen"] if p["text"] == "Nach Hostbedarf"]
        self.assertEqual(len(letzte), 1)
        self.assertTrue(letzte[0]["sichtbar"])
        x, _y, w, _h = letzte[0]["rect"]
        fx, _fy, fw, _fh = erg["fenster"]
        self.assertLessEqual(x + w, fx + fw, "Nach Hostbedarf ragt aus dem Fenster")
        # kein waagrechter Rollbalken, Inhalt nicht breiter als die Ansicht
        self.assertFalse(erg["hbar_sichtbar"], "waagrechter Rollbalken sichtbar")
        self.assertLessEqual(erg["inner_breite"], erg["canvas_breite"])
        self.assertEqual(erg["xview"], [0.0, 1.0])

    def test_normal(self):
        self.pruefe_faktor(1.0)

    def test_gross(self):
        self.pruefe_faktor(1.15)

    def test_sehr_gross(self):
        self.pruefe_faktor(1.3)

    def test_reihenfolge_und_text(self):
        for faktor in FAKTOREN:
            erg = _ergebnis(faktor)
            labels = [label for _value, label in erg["kinds"]]
            with self.subTest(faktor=faktor):
                self.assertEqual([p["text"] for p in erg["pillen"]], labels)
                # sichtbare Reihenfolge: Zeile fuer Zeile (oben nach unten),
                # in der Zeile von links nach rechts
                lese = sorted(erg["pillen"], key=lambda p: (p["rect"][1], p["rect"][0]))
                self.assertEqual([p["text"] for p in lese], labels)
                # Zeilen liegen sauber untereinander, Abstand 8 px (skaliert)
                zeilen = sorted({p["rect"][1] for p in erg["pillen"]})
                hoehe = erg["pillen"][0]["rect"][3]
                for oben, unten in zip(zeilen, zeilen[1:]):
                    self.assertEqual(unten - oben, hoehe + erg["gap"])
                # in jeder Zeile Abstand 8 px (skaliert), erste Pille links buendig
                for y in zeilen:
                    zeile = sorted((p for p in erg["pillen"] if p["rect"][1] == y),
                                   key=lambda p: p["rect"][0])
                    self.assertEqual(zeile[0]["rect"][0], erg["body"][0])
                    for links, rechts in zip(zeile, zeile[1:]):
                        self.assertEqual(rechts["rect"][0],
                                         links["rect"][0] + links["rect"][2] + erg["gap"])

    def test_erste_zeile_so_voll_wie_moeglich(self):
        for faktor in FAKTOREN:
            erg = _ergebnis(faktor)
            zeilen = sorted({p["rect"][1] for p in erg["pillen"]})
            with self.subTest(faktor=faktor):
                for y, naechste in zip(zeilen, zeilen[1:]):
                    zeile = [p for p in erg["pillen"] if p["rect"][1] == y]
                    erste_danach = min((p for p in erg["pillen"] if p["rect"][1] == naechste),
                                       key=lambda p: p["rect"][0])
                    rechts = max(p["rect"][0] + p["rect"][2] for p in zeile)
                    # die naechste Pille haette nicht mehr in die Zeile gepasst
                    self.assertGreater(rechts + erg["gap"] + erste_danach["rect"][2],
                                       erg["body"][0] + erg["body"][2])

    def test_auswahl_get(self):
        for faktor in FAKTOREN:
            erg = _ergebnis(faktor)
            with self.subTest(faktor=faktor):
                self.assertEqual([a[0] for a in erg["auswahl"]],
                                 [value for value, _label in erg["kinds"]])
                for value, got, aktiv in erg["auswahl"]:
                    self.assertEqual(got, value)
                    self.assertTrue(aktiv)


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class BestandPillenTest(unittest.TestCase):
    """Plan 4.3: alle anderen PillGroup-Nutzer unveraendert (nebeneinander
    gepackt, Abstand 8 px), Geometrie bei 1360."""

    def test_andere_nebeneinander(self):
        erg = _ergebnis(1.0, 1360, 900)
        for gruppe in erg["andere"]:
            with self.subTest(gruppe=gruppe["name"]):
                self.assertEqual(set(gruppe["manager"]), {"pack"})
                rects = gruppe["rects"]
                self.assertEqual(len({r[1] for r in rects}), 1, "nicht in einer Zeile")
                for links, rechts in zip(rects, rects[1:]):
                    self.assertEqual(rechts[0], links[0] + links[2] + erg["gap"])

    def test_standard_ohne_umbrechen(self):
        # Quelltext: Standard bleibt False, nur der Trainer schaltet um
        with open(os.path.join(HERE, "app_gui.py"), encoding="utf-8") as handle:
            text = handle.read()
        import re
        self.assertTrue("umbrechen=False" in text, "PillGroup ohne Schluessel umbrechen=False")
        self.assertEqual(len(re.findall(r"PillGroup\([^)]*umbrechen=True", text)), 1)
        self.assertTrue("PillGroup(setup.body, TRAINER_KINDS, umbrechen=True)" in text,
                        "Trainer-Pillen ohne umbrechen=True")


if __name__ == "__main__":
    if len(sys.argv) >= 5 and sys.argv[1] == "--kind":
        _kind_messen(float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]))
    else:
        unittest.main(verbosity=2)
