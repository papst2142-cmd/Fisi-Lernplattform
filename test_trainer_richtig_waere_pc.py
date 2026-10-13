#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests 0.63.2 A1: PC-Trainer, Rueckmeldung "richtig wäre: <Wert>".

Plan 0.63.2 (S1 A1): Passt die Rueckmeldung neben dem Eingabefeld nicht bis
zum sichtbaren Rand der Seite, wird sie umbrochen ("richtig wäre:" und
darunter eingerueckt der Wert); passt neben dem Feld nicht einmal
"richtig wäre:" (Schrift Sehr gross), steht sie unter dem Feld.

Fuer alle 6 Trainer-Arten x 3 Stufen (fester Startwert, leere Antworten:
alle Felder falsch) und fuer IPv6 und "Netz aufteilen" zusaetzlich je eine
Aufgabe mit der laengsten Adresse (39 bzw. 38 Zeichen) prueft der Test je
Marke:
  * rechter Rand der Marke <= rechter sichtbarer Rand der Seite, und die
    Marke bekommt die Breite, die sie braucht (nichts abgeschnitten)
  * Wortlaut: angezeigter Text ohne Leerraum = "richtig wäre: " + Loesung
    ohne Leerraum
  * Lage: Normal und kurze Werte neben dem Feld; Sehr gross 1120 unter dem
    Feld; nie ueber einem anderen Feld (keine Ueberlappung)
  * Schutz: kein AttributeError, wenn das private CTk-Label keine Schrift
    liefert (Attrappe), und gleiches Ergebnis

Dunkel (Grundeinstellung), Fenster 1120 x 800 und 1360 x 900, Faktor
1,00 / 1,15 / 1,30; je Kombination ein eigener Prozess. Gegen 14b3bd4 rot.

Start:  xvfb-run -a python test_trainer_richtig_waere_pc.py
"""

import json
import os
import random
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

FAKTOREN = {1.0: "normal", 1.15: "gross", 1.3: "sehr_gross"}
FENSTER = ((1120, 800), (1360, 900))
SEED = 7
# Startwerte mit der laengsten Loesung (gesucht ueber 3000 Startwerte,
# fisi_lernen.trainer_round, erste Aufgabe): (Art, Stufe) -> (Startwert, Laenge)
LANG = {("ipv6", 1): (11, 34), ("ipv6", 2): (704, 31), ("ipv6", 3): (0, 39),
        ("teilen", 3): (5, 38)}
RICHTIG_WAERE = "richtig wäre: %s"


def worker(faktor, breite, hoehe):
    """Laeuft im eigenen Prozess; gibt eine JSON-Zeile "ERG {...}" aus."""
    home = tempfile.mkdtemp(prefix="fisi_rw_")
    os.environ.update(HOME=home, APPDATA=home, FISI_DB_PATH=os.path.join(home, "t.db"),
                      FISI_SELFTEST=os.path.join(home, "log.txt"))
    import customtkinter as ctk
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
    root.geometry("%dx%d+0+0" % (breite, hoehe))
    app = app_gui.FISIApp(root)

    def pump(seconds=0.3):
        end = time.time() + seconds
        while time.time() < end:
            root.update()
            time.sleep(0.01)

    pump(0.8)
    app.show_view("calc")
    root.geometry("%dx%d+0+0" % (breite, hoehe))
    pump(0.8)
    view = app.views["calc"]
    view._on_tab("trainer")
    pump(0.5)
    tr = view.trainer
    canvas = view.canvas
    found = []
    stats = {"marken": 0, "neben": 0, "unter": 0, "umbrochen": 0, "faelle": 0,
             "modus": str(ctk.get_appearance_mode())}
    original_randrange = random.randrange

    def box(widget):
        x, y = widget.winfo_rootx(), widget.winfo_rooty()
        return x, y, x + widget.winfo_width(), y + widget.winfo_height()

    def overlap(a, b):
        return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]

    cases = []
    for kind, _name in fl.TRAINER_KINDS:
        for level, _lname in fl.TRAINER_LEVELS:
            cases.append((kind, level, SEED, False))
            if (kind, level) in LANG:
                cases.append((kind, level, LANG[(kind, level)][0], True))

    for kind, level, seed, lang in cases:
        name = "%s/%d/%s" % (kind, level, "lang" if lang else seed)
        random.randrange = lambda _n, s=seed: s
        try:
            tr.kind_pills.select_value(kind)
            tr.level_pills.select_value(level)
            pump(0.1)
            tr.start_round()
        finally:
            random.randrange = original_randrange
        canvas.xview_moveto(0)
        pump(0.3)
        task = tr.tasks[0]
        if lang:
            longest = max(len(v) for v in task.solution.values())
            if longest != LANG[(kind, level)][1]:
                found.append("%s: laengste Loesung %d statt %d Zeichen"
                             % (name, longest, LANG[(kind, level)][1]))
        expected = task.check({key: "" for key, _label in task.fields})
        tr.check()
        pump(0.5)
        stats["faelle"] += 1
        visible = canvas.winfo_rootx() + canvas.winfo_width()
        others = [w for w in tr.fields_box.winfo_children() if w.winfo_ismapped()]
        for key, mark in tr.marks.items():
            stats["marken"] += 1
            shown = mark.cget("text")
            want = "richtig" if expected[key] else RICHTIG_WAERE % task.solution[key]
            if "".join(shown.split()) != "".join(want.split()):
                found.append("%s %s: Wortlaut %r statt %r" % (name, key, shown, want))
            if "\n" in shown:
                stats["umbrochen"] += 1
            right = mark.winfo_rootx() + mark.winfo_width()
            if right > visible:
                found.append("%s %s: Marke ragt %d px ueber den sichtbaren Rand"
                             % (name, key, right - visible))
            if mark.winfo_width() < mark.winfo_reqwidth():
                found.append("%s %s: Marke abgeschnitten (%d < %d px)"
                             % (name, key, mark.winfo_width(), mark.winfo_reqwidth()))
            info = mark.grid_info()
            entry = tr.entries[key]
            under = int(info.get("column", 2)) != 2
            stats["unter" if under else "neben"] += 1
            if under and mark.winfo_rooty() < entry.winfo_rooty() + entry.winfo_height():
                found.append("%s %s: Marke 'unter dem Feld' liegt nicht unter dem Feld"
                             % (name, key))
            if faktor == 1.0 and kind in ("ipv4", "vlsm", "zahlen", "bedarf") and under:
                found.append("%s %s: Normal, kurzer Wert, aber nicht neben dem Feld" % (name, key))
            if under:
                stats.setdefault("unter_arten", [])
                if kind not in stats["unter_arten"]:
                    stats["unter_arten"].append(kind)
            mine = box(mark)
            for other in others:
                if other is mark:
                    continue
                if overlap(mine, box(other)):
                    found.append("%s %s: Marke ueberlappt %s" % (name, key, other))
                    break
        # Seite selbst: die Marken machen die Seite nicht breiter
        right_marks = max((m.winfo_rootx() + m.winfo_reqwidth()) for m in tr.marks.values())
        if right_marks > visible:
            found.append("%s: gebrauchte Breite der Marken %d > sichtbar %d"
                         % (name, right_marks, visible))

    # Schutz (Plan A1): das private CTk-Label liefert keine Schrift -> kein
    # AttributeError, Ergebnis gleich (die Messung braucht _label nicht)
    before = {key: (mark.cget("text"), dict(mark.grid_info()).get("column"))
              for key, mark in tr.marks.items()}

    class Attrappe:
        def __init__(self, inner):
            self._inner = inner

        def cget(self, _name):
            raise AttributeError("Attrappe: keine Schrift")

        def __getattr__(self, attr):
            return getattr(self._inner, attr)

    saved = {}
    try:
        for key, mark in tr.marks.items():
            saved[key] = mark._label
            mark._label = Attrappe(mark._label)
            mark.fit_raw = getattr(mark, "fit_raw", "")
        fit = getattr(tr, "_fit_marks", None)
        if fit is None:
            found.append("Schutz: TrainerPanel hat keine Anpassung der Marken")
        else:
            fit()
    except AttributeError as exc:
        found.append("Schutz: AttributeError %s" % exc)
    finally:
        for key, label in saved.items():
            tr.marks[key]._label = label
    pump(0.3)
    after = {key: (mark.cget("text"), dict(mark.grid_info()).get("column"))
             for key, mark in tr.marks.items()}
    if after != before:
        found.append("Schutz: Ergebnis mit Attrappe weicht ab: %r -> %r" % (before, after))
    if errors:
        found.append("Fehlermeldungen: %r" % errors)
    print("ERG " + json.dumps({"fehler": found, "werte": stats}, ensure_ascii=False))
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
class RichtigWaereTest(unittest.TestCase):
    """Je Schriftgroesse und Fenster ein Prozess (worker)."""

    def run_case(self, faktor, breite, hoehe):
        done = subprocess.run([sys.executable, os.path.abspath(__file__), "--fall",
                               str(faktor), str(breite), str(hoehe)],
                              capture_output=True, text=True, timeout=900, cwd=HERE)
        lines = [line for line in done.stdout.splitlines() if line.startswith("ERG ")]
        self.assertTrue(lines, "kein Ergebnis:\n%s\n%s" % (done.stdout[-2000:],
                                                           done.stderr[-4000:]))
        result = json.loads(lines[-1][4:])
        print("\n  %s %dx%d: %s" % (FAKTOREN[faktor], breite, hoehe, result["werte"]))
        self.assertEqual(result["fehler"], [], "%s %dx%d" % (FAKTOREN[faktor], breite, hoehe))
        return result["werte"]


def _make(faktor, breite, hoehe):
    def test(self):
        werte = self.run_case(faktor, breite, hoehe)
        self.assertEqual(werte["faelle"], 18 + len(LANG))
        self.assertEqual(werte["modus"], "Dark")
        if faktor == 1.3 and breite == 1120:
            # Sehr gross 1120: dort steht die Rueckmeldung (auch) unter dem Feld
            self.assertGreater(werte["unter"], 0)
    return test


for _faktor in FAKTOREN:
    for _breite, _hoehe in FENSTER:
        setattr(RichtigWaereTest, "test_%s_%d" % (FAKTOREN[_faktor], _breite),
                _make(_faktor, _breite, _hoehe))


class StartwertTest(unittest.TestCase):
    """Die Startwerte liefern wirklich die langen Adressen (ohne Oberflaeche)."""

    def test_lang(self):
        import fisi_lernen as fl
        for (kind, level), (seed, length) in LANG.items():
            task = fl.trainer_round(kind, level, seed)[0]
            self.assertEqual(max(len(v) for v in task.solution.values()), length,
                             (kind, level, seed))


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "--fall":
        worker(float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]))
    unittest.main(verbosity=2)
