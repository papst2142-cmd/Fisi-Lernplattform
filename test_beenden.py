#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer das Beenden des PC-Programms (ab 0.55.1) - mit Oberflaeche.

Jeder Fall startet das echte Programm (app_gui.main) in einem eigenen
Prozess, oeffnet eine Ansicht oder einen Dialog und schliesst es dann wie
das X am Fenster bzw. wie der Update-Dialog (on_close). Geprueft wird:
  * der Prozess endet innerhalb von CLOSE_LIMIT Sekunden (kein Prozess
    bleibt zurueck, der dem Installer die Dateien sperrt)
  * fehler.log bleibt leer (vorher: "can't delete Tcl command")
  * beim Beenden fuer ein Update steht "Programm sauber beendet" in update.log
Dazu: Notausgang, Bereinigung geloeschter Tcl-Befehle (drop_deleted_commands).

Braucht eine Anzeige (unter Linux z.B. xvfb-run). Ohne Anzeige werden die
Tests uebersprungen.

Start:  python test_beenden.py
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# Hoechstens so lange darf der Prozess nach dem Schliessen noch laufen
CLOSE_LIMIT = 6

VIEWS = ("dashboard", "cards", "quiz", "ap1scenarios", "scenarios", "testproject",
         "abschluss", "notebook", "calc", "game", "progress", "settings")

# Kindprozess: startet das Programm, oeffnet die Ansicht und schliesst.
CHILD = r'''
import os, sys, time
sys.path.insert(0, sys.argv[1])
os.chdir(sys.argv[1])
view, mode = sys.argv[2], sys.argv[3]
import app_gui
# Kein Netz: keine Update-Suche, kein Abgleich
app_gui.UpdateController.auto_check = lambda self: None
app_gui.SyncController.auto_start = lambda self: None
init = app_gui.FISIApp.__init__

def patched(self, root):
    init(self, root)
    def start():
        views = [k for k in self.views if k != "search"] if view == "alle" else [view]
        for key in views:
            self.show_view(key)
            root.update()
        if mode == "update":
            dialog = app_gui.UpdateDialog(self, app_gui.fisi_update.UpdateInfo(
                "9.9", "- Test\n- Neuerungen", app_gui.fisi_update.RELEASES_PAGE))
            root.update()
            # wie UpdateDialog._installed nach dem Start des Installers
            self.update_exit = True
            dialog.after(300, lambda: self.on_close(final_sync=False))
        elif mode == "bericht":
            self.show_view("settings")
            self.views["settings"]._show_report()
            root.update()
            root.after(300, self.on_close)
        elif mode == "dialog_offen":
            app_gui.UpdateDialog(self, app_gui.fisi_update.UpdateInfo(
                "9.9", "- Test", app_gui.fisi_update.RELEASES_PAGE))
            root.update()
            root.after(300, self.on_close)
        else:
            root.after(300, self.on_close)
        print("GESCHLOSSEN", time.time(), flush=True)
    root.after(800, start)
app_gui.FISIApp.__init__ = patched
app_gui.main()
print("ENDE", time.time(), flush=True)
'''

# Kindprozess fuer den Notausgang: Abbau bleibt "haengen"
CHILD_HANG = r'''
import os, sys, time
sys.path.insert(0, sys.argv[1])
import app_gui
app_gui.arm_emergency_exit(for_update=True, seconds=1)
time.sleep(30)
print("NICHT BEENDET", flush=True)
'''


def _display_available():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:
        return False


HAS_DISPLAY = _display_available()


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class CloseTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="fisi beenden Ä ")
        self.env = dict(os.environ, FISI_DB_PATH=os.path.join(self.folder, "fisi.db"))
        self.env.pop("FISI_SELFTEST", None)
        self.script = os.path.join(self.folder, "kind.py")
        with open(self.script, "w", encoding="utf-8") as handle:
            handle.write(CHILD)

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def read(self, name):
        try:
            with open(os.path.join(self.folder, name), encoding="utf-8") as handle:
                return handle.read()
        except OSError:
            return ""

    def close_in(self, view, mode="x"):
        process = subprocess.Popen([sys.executable, self.script, HERE, view, mode],
                                   env=self.env, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True)
        try:
            output, _ = process.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            process.kill()
            output, _ = process.communicate()
            self.fail("Prozess laeuft nach 120 s noch (%s/%s):\n%s" % (view, mode, output))
        stamps = {}
        for line in output.splitlines():
            if line.startswith(("GESCHLOSSEN ", "ENDE ")):
                word, value = line.split()
                stamps[word] = float(value)
        self.assertIn("ENDE", stamps, "mainloop nicht verlassen (%s/%s):\n%s"
                      % (view, mode, output[-3000:]))
        self.assertEqual(process.returncode, 0, output[-3000:])
        self.assertLess(stamps["ENDE"] - stamps["GESCHLOSSEN"], CLOSE_LIMIT)
        self.assertEqual(self.read("fehler.log"), "", "fehler.log nicht leer (%s/%s)"
                         % (view, mode))
        self.assertNotIn("TclError", output)
        return output

    def test_jede_hauptansicht(self):
        for view in VIEWS:
            with self.subTest(view=view):
                self.close_in(view)

    def test_alle_ansichten_nacheinander(self):
        self.close_in("alle")

    def test_update_dialog_beim_update(self):
        self.close_in("dashboard", "update")
        log = self.read("update.log")
        self.assertIn("Programm sauber beendet", log)
        self.assertNotIn("Notausgang", log)

    def test_update_dialog_offen_x(self):
        self.close_in("dashboard", "dialog_offen")

    def test_problem_melden_offen(self):
        self.close_in("settings", "bericht")

    def test_alles_offen_dann_update(self):
        self.close_in("alle", "update")
        self.assertIn("Programm sauber beendet", self.read("update.log"))


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class EmergencyExitTest(unittest.TestCase):
    def test_notausgang(self):
        folder = tempfile.mkdtemp(prefix="fisi notausgang ")
        try:
            script = os.path.join(folder, "haengt.py")
            with open(script, "w", encoding="utf-8") as handle:
                handle.write(CHILD_HANG)
            env = dict(os.environ, FISI_DB_PATH=os.path.join(folder, "fisi.db"))
            started = time.time()
            result = subprocess.run([sys.executable, script, HERE], env=env,
                                    capture_output=True, text=True, timeout=30)
            self.assertLess(time.time() - started, 15)
            self.assertNotIn("NICHT BEENDET", result.stdout)
            for name in ("fehler.log", "update.log"):
                with open(os.path.join(folder, name), encoding="utf-8") as handle:
                    self.assertIn("Notausgang", handle.read())
        finally:
            shutil.rmtree(folder, ignore_errors=True)


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class DeletedCommandTest(unittest.TestCase):
    """Genau der Fehler aus fehler.log 0.54/0.55: Der Zeitgeber eines
    Textfelds wird ueber das Hauptfenster abgebrochen (loescht den
    Tcl-Befehl), danach baut das Textfeld ab."""

    def setUp(self):
        import customtkinter as ctk
        import tkinter as tk
        import fisi_widgets
        self.ctk, self.tk, self.fw = ctk, tk, fisi_widgets
        self.root = ctk.CTk()
        self.root.withdraw()

    def tearDown(self):
        try:
            # Zeitgeber von customtkinter abbrechen (wie on_close ab 0.55.1)
            for job in self.root.tk.splitlist(self.root.tk.call("after", "info")):
                self.root.tk.call("after", "cancel", job)
            self.root.destroy()
        except Exception:
            pass

    def _orphan_textbox_timer(self, parent):
        box = self.ctk.CTkTextbox(parent)
        box.pack()
        self.root.update()
        job = box.after(10000, lambda: None)
        script = self.root.tk.splitlist(self.root.tk.call("after", "info", job))[0]
        self.root.after_cancel(job)    # so wie on_close bis 0.55
        self.assertFalse(self.root.tk.call("info", "commands", script))
        self.assertIn(script, box._tclCommands)
        return box

    def test_textfeld(self):
        box = self._orphan_textbox_timer(self.root)
        box.destroy()     # vorher: TclError "can't delete Tcl command"
        self.assertIsNone(box._tclCommands)

    def test_textfeld_im_toplevel(self):
        top = self.ctk.CTkToplevel(self.root)
        self._orphan_textbox_timer(top)
        top.destroy()
        self.root.update()

    def test_ganzes_fenster(self):
        frame = self.ctk.CTkFrame(self.root)
        frame.pack()
        self._orphan_textbox_timer(frame)
        for job in self.root.tk.splitlist(self.root.tk.call("after", "info")):
            self.root.tk.call("after", "cancel", job)
        self.root.destroy()   # wie on_close

    def test_andere_fehler_kommen_durch(self):
        box = self.ctk.CTkTextbox(self.root)
        self.assertEqual(self.fw.drop_deleted_commands(box), 0)
        box._tclCommands.append("gibt_es_nicht_123")
        self.assertEqual(self.fw.drop_deleted_commands(box), 1)
        self.assertNotIn("gibt_es_nicht_123", box._tclCommands)
        box.destroy()


if __name__ == "__main__":
    unittest.main(verbosity=2)
