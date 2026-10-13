#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests ab 0.63.2 fuer die Spiel-Fehler am PC (Bauauftrag N2):

  B-F-03  "Tickets heute" mit 150 und mehr Eintraegen: Die Spielansicht wurde
          so hoch (1493 + 61 * N px), dass X das Bild ablehnte (BadAlloc bzw.
          BadValue bei X_CreatePixmap) und das Programm ohne Meldung endete.
          Jetzt hoechstens GameView.TICKET_PAGE Eintraege je Seite, Blaettern
          wie in den Listen der Lernplattform, Kopfzeile zaehlt weiter alle.
          Der Aufbau laeuft in einem eigenen Prozess (stuerzt X ab, endet nur
          dieser Prozess, der Test meldet ihn rot).
  B-N-01  Scheitert der Aufbau eines Reiters in Reise oder Firma, erscheint
          eine Meldung (Fenster und fehler.log ueber report_callback_exception),
          der halb gebaute Inhalt verschwindet, Reiterzeile und Inhalt zeigen
          wieder den zuletzt funktionierenden Reiter.

Der Test wird NIE uebersprungen: Fehlt die Anzeige, ist er rot.
Start:  xvfb-run -a python test_spiel_pc_0632.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from test_vorladen import AppCase, HAS_DISPLAY   # noqa: E402  vorhandene Testhilfe


# ============================================================================
#  B-F-03: viele Eintraege in "Tickets heute"
# ============================================================================

def _ticket_db(path, count):
    """Platz 1 mit Spielfigur und count geloesten Tickets an Arbeitstag 1
    (wie die Nachstellung der Pruefung 0.62.4, bf03_unabhaengig.py: Game.solve
    laesst nur heute offene Tickets zu, darum direkt als Ereignis)."""
    import fisi_core
    import fisi_game as fg
    db = fisi_core.DBManager(path)
    game = fg.Game(db, device="PC")
    run = game.new_run(1)
    game.set_profile("Test", {})
    state = game.reload()
    tasks = [task for task in game.content["aufgaben"] if not task.get("zwischenfall")]
    if count > len(tasks):
        raise AssertionError("nur %d Aufgaben" % len(tasks))
    for task in tasks[:count]:
        payload = {"aufgabe": task["id"], "tag": state.day, "richtig": True, "geld": 0,
                   "reputation": {}}
        db.log_game_event(fg.EV_SOLVED, json.dumps(payload), "PC", run)
    game.invalidate()
    return len(game.reload().todays_tickets())


# Laeuft im eigenen Prozess: Spielansicht oeffnen, Platz 1 waehlen, zeichnen,
# Hoehe und Zeilen melden, dann einmal weiterblaettern.
_CHILD = r"""
import json, os, sys, time
sys.path.insert(0, sys.argv[1])
factor = float(sys.argv[2])
import customtkinter as ctk
import app_gui, fisi_theme, fisi_widgets, fisi_game_gui
app_gui.apply_appearance()
if factor != 1.0:
    fisi_theme.apply_font_size({1.15: "gross", 1.3: "sehr_gross"}[factor])
    fisi_widgets.apply_ui_scale(factor)
app_gui.UpdateController.auto_check = lambda self: None
app_gui.SyncController.auto_start = lambda self: None
errors = []
root = ctk.CTk()
root.report_callback_exception = lambda *exc: errors.append(repr(exc[1]))
app = app_gui.FISIApp(root)
root.geometry("1360x900+0+0")
rows = []
original = fisi_game_gui.GameView._ticket_row
def counting(self, parent, task, status):
    rows.append(task["id"])
    return original(self, parent, task, status)
fisi_game_gui.GameView._ticket_row = counting
def pump(seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        root.update()
        time.sleep(0.005)
pump(0.3)
app.show_view("game")
pump(0.3)
view = app.views["game"]
run = [item for item in view.game.slots() if not item["extra"] and item.get("lauf")][0]["lauf"]
del rows[:]
view._choose(run)
pump(1.0)
report = {"rows": len(rows), "height": view.content.winfo_reqheight(),
          "subtitles": [], "pages": [], "errors": errors}
import tkinter
def texts(widget, out):
    for child in widget.winfo_children():
        if isinstance(child, tkinter.Label) and isinstance(child.master, ctk.CTkBaseClass):
            continue   # innerer Label eines CTkLabel (Text sonst doppelt)
        try:
            out.append(str(child.cget("text")))
        except Exception:
            pass
        texts(child, out)
    return out
all_texts = texts(view.content, [])
report["subtitles"] = [t for t in all_texts if "bearbeitet" in t]
report["pages"] = [t for t in all_texts if t.startswith("Seite ")]
if hasattr(view, "_turn_tickets") and report["pages"]:
    first = list(rows)
    del rows[:]
    view._turn_tickets(1)
    pump(0.5)
    report["rows_page2"] = len(rows)
    report["overlap"] = len(set(first) & set(rows))
    report["pages2"] = [t for t in texts(view.content, []) if t.startswith("Seite ")]
print("ERGEBNIS " + json.dumps(report), flush=True)
os._exit(0)
"""


class TicketListeTest(unittest.TestCase):
    """B-F-03: Die Ansicht baut mit 149, 150, 250 und 442 Eintraegen ohne
    X-Fehler, bleibt unter der Grenze und zaehlt in der Kopfzeile alle."""

    # Hoehe der Ansicht mit 149 Eintraegen lief 0.62.4 gerade noch (10.582 px);
    # mit Blaettern bleibt sie weit darunter
    MAX_HEIGHT = 8000

    def setUp(self):
        if not HAS_DISPLAY:
            self.fail("keine Anzeige - dieser Test darf nicht uebersprungen werden "
                      "(unter Linux mit xvfb-run starten)")
        self.folder = tempfile.mkdtemp(prefix="fisi tickets ")

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def _run(self, count, factor=1.0):
        db = os.path.join(self.folder, "t%d_%s.db" % (count, factor))
        env = dict(os.environ, FISI_DB_PATH=db, HOME=self.folder,
                   FISI_SELFTEST=os.path.join(self.folder, "log.txt"),
                   PYTHONDONTWRITEBYTECODE="1")
        saved = os.environ.get("FISI_DB_PATH")
        os.environ["FISI_DB_PATH"] = db
        try:
            self.assertEqual(_ticket_db(db, count), count)
        finally:
            if saved is None:
                os.environ.pop("FISI_DB_PATH", None)
            else:
                os.environ["FISI_DB_PATH"] = saved
        script = os.path.join(self.folder, "kind.py")
        with open(script, "w", encoding="utf-8") as handle:
            handle.write(_CHILD)
        result = subprocess.run([sys.executable, script, HERE, str(factor)], env=env,
                                capture_output=True, text=True, timeout=300)
        lines = [line for line in result.stdout.splitlines() if line.startswith("ERGEBNIS ")]
        self.assertEqual(result.returncode, 0,
                         "%d Eintraege: Programm beendet (rc=%s)\n%s" % (
                             count, result.returncode, result.stderr[-1500:]))
        self.assertEqual(len(lines), 1, result.stdout[-1500:] + result.stderr[-1500:])
        return json.loads(lines[0][len("ERGEBNIS "):])

    def _check(self, count, factor=1.0):
        import fisi_game_gui
        # Soll 50 je Seite (gegen den alten Stand ohne Konstante ebenso, damit
        # der Test dort am Absturz bzw. an der Zeilenzahl rot wird)
        page = getattr(fisi_game_gui.GameView, "TICKET_PAGE", 50)
        report = self._run(count, factor)
        self.assertEqual(report["errors"], [])
        self.assertLess(report["height"], self.MAX_HEIGHT, report)
        self.assertEqual(report["rows"], min(count, page), report)
        # Kopfzeile zaehlt weiter alle Eintraege
        self.assertTrue(any("von %d bearbeitet" % count in text
                            for text in report["subtitles"]), report["subtitles"])
        pages = -(-count // page)
        if pages > 1:
            self.assertEqual(report["pages"], ["Seite 1 / %d" % pages])
            self.assertEqual(report["pages2"], ["Seite 2 / %d" % pages])
            self.assertEqual(report["rows_page2"], min(page, count - page))
            self.assertEqual(report["overlap"], 0)
        else:
            self.assertEqual(report["pages"], [])
        return report

    def test_149_eintraege(self):
        self._check(149)

    def test_150_eintraege(self):
        self._check(150)

    def test_250_eintraege(self):
        self._check(250)

    def test_442_eintraege_sehr_gross(self):
        self._check(442, factor=1.3)

    def test_wenige_eintraege_ohne_blaettern(self):
        # Im normalen Spiel (hoechstens etwa 37 je Tag) bleibt alles wie bisher
        report = self._check(37)
        self.assertEqual(report["pages"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
