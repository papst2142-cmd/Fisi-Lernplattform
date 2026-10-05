#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer das Vorladen der Ansichten und die Ladeanzeige (ab 0.56, Plan
Abschnitt 3) - mit Oberflaeche.

Geprueft wird:
  * das Vorladen laeuft nach dem Start und baut die grossen Ansichten auf;
    eine vorgeladene Ansicht zeichnet beim Anzeigen nicht noch einmal
  * ein Klick hat Vorrang: kein Schritt direkt nach einer Eingabe, die
    sichtbare bzw. schon geoeffnete Ansicht wird nicht angefasst
  * nach der Wahl des Spielstands werden die Spielansichten und die Reiter
    von Reise vorgebaut; der Reiterwechsel baut dann nichts mehr
  * die Ladeanzeige erscheint bei einer (voraussichtlich) langsamen Ansicht
    mit dem gemeinsamen Text und verschwindet wieder; bei schnellen nicht
  * Schliessen waehrend des Vorladens und waehrend die Ladeanzeige
    erscheint: Prozess endet, fehler.log bleibt leer, kein TclError

Braucht eine Anzeige (unter Linux z.B. xvfb-run). Ohne Anzeige werden die
Tests uebersprungen.

Start:  python test_vorladen.py
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

CLOSE_LIMIT = 6


def _display_available():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:
        return False


HAS_DISPLAY = _display_available()


class AppCase(unittest.TestCase):
    """Startet fuer jeden Test ein eigenes Hauptfenster mit leerer Datenbank."""

    profile = False   # Spielfigur anlegen (fuer Reise mit Reitern)

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="fisi vorladen ")
        os.environ["FISI_DB_PATH"] = os.path.join(self.folder, "test.db")
        os.environ["FISI_SELFTEST"] = os.path.join(self.folder, "log.txt")  # kein Netz
        os.environ["HOME"] = self.folder
        import customtkinter as ctk
        import app_gui
        import fisi_widgets
        self.app_gui = app_gui
        fisi_widgets._PHOTO_CACHE.clear()
        fisi_widgets._IMAGE_CACHE.clear()
        if self.profile:
            import fisi_core
            import fisi_game
            db = fisi_core.DBManager(os.environ["FISI_DB_PATH"])
            fisi_game.Game(db, "PC").set_profile("Test", {})
        app_gui.apply_appearance()
        self.errors = []
        self.root = ctk.CTk()
        self.root.report_callback_exception = lambda *exc: self.errors.append(
            "".join(traceback.format_exception(*exc)))
        self.app = app_gui.FISIApp(self.root)
        self.root.geometry("1360x900+0+0")
        self.pump(0.2)

    def tearDown(self):
        try:
            tk_ = self.root.tk
            for job in tk_.splitlist(tk_.call("after", "info")):
                tk_.call("after", "cancel", job)
            self.root.destroy()
        except Exception:
            pass
        import fisi_widgets
        fisi_widgets._PHOTO_CACHE.clear()
        fisi_widgets._IMAGE_CACHE.clear()
        shutil.rmtree(self.folder, ignore_errors=True)

    def pump(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.root.update()
            time.sleep(0.005)

    def pump_until(self, condition, timeout=90):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if condition():
                return True
            self.root.update()
            time.sleep(0.005)
        return condition()

    def stop_preloader(self):
        pre = self.app.preloader
        if pre.job is not None:
            self.root.after_cancel(pre.job)
            pre.job = None
        pre.queue = []

    def watch_hint(self):
        """Zeichnet auf, wie oft die Ladeanzeige erscheint und welchen Text
        sie zeigt; prueft beim Ausblenden, dass sie noch steht."""
        app = self.app
        record = {"shown": 0, "texts": [], "frames": []}
        show, hide = app._show_loading, app._hide_loading

        def texts(widget):
            found = []
            for child in widget.winfo_children():
                try:
                    found.append(child.cget("text"))
                except Exception:
                    pass
                found.extend(texts(child))
            return found

        def shown():
            frame = show()
            record["shown"] += 1
            record["frames"].append(frame)
            record["texts"].extend(t for t in texts(frame) if t)
            return frame

        def hidden(frame):
            self.assertTrue(frame.winfo_exists())
            hide(frame)

        app._show_loading = shown
        app._hide_loading = hidden
        return record


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class PreloadTest(AppCase):
    def test_vorladen_laeuft_und_spart_das_neuzeichnen(self):
        app, pre = self.app, self.app.preloader
        self.assertFalse(pre.done)
        self.assertEqual(pre.steps_done, 0, "Vorladen darf den Start nicht verzoegern")
        self.assertIsNone(app.views.built("progress"))
        self.assertTrue(self.pump_until(lambda: pre.done), "Vorladen nicht fertig")
        for key in self.app_gui.PRELOAD_VIEWS:
            self.assertIsNotNone(app.views.built(key), key)
        self.assertGreaterEqual(pre.steps_done, len(self.app_gui.PRELOAD_VIEWS))
        # Die sichtbare Ansicht bleibt das Dashboard
        self.assertEqual(app.current, "dashboard")
        # Vorgeladen: Fortschritt und Notizblock zeichnen beim Anzeigen nicht neu
        for key in ("progress", "notebook"):
            view = app.views[key]
            calls = []
            original = view.refresh
            view.refresh = lambda *a, **k: (calls.append(1), original(*a, **k))
            self.assertFalse(self.app_gui._needs_work(view), key)
            app.show_view(key)
            self.root.update()
            self.assertEqual(calls, [], "%s wurde neu gezeichnet" % key)
            self.assertEqual(app.current, key)
        self.assertEqual(self.errors, [])

    def test_klick_hat_vorrang(self):
        app, pre = self.app, self.app.preloader
        self.stop_preloader()
        pre.queue = self.app_gui.preload_tasks(False)
        # Eben geklickt: der Schritt wartet und plant sich neu
        pre._input()
        before = list(pre.queue)
        pre._step()
        self.assertEqual(pre.queue, before)
        self.assertIsNotNone(pre.job)
        self.stop_preloader()
        # Die sichtbare Ansicht wird nicht angefasst
        app.show_view("quiz")
        self.root.update()
        self.assertFalse(pre._run(("view", "quiz")))
        # Eine schon geoeffnete Ansicht wird nicht neu aufgebaut
        app.show_view("notebook")
        self.root.update()
        notebook = app.views.built("notebook")
        app.show_view("dashboard")
        self.root.update()
        self.assertFalse(pre._run(("view", "notebook")))
        self.assertIs(app.views.built("notebook"), notebook)
        # Ohne Eingabe laeuft der naechste Schritt
        pre.last_input = 0
        pre.queue = [("view", "calc")]
        pre._step()
        self.assertIsNotNone(app.views.built("calc"))
        self.assertTrue(pre.done)
        self.assertEqual(app.current, "dashboard")
        self.assertEqual(self.errors, [])

    def test_spielansichten_erst_nach_der_platzwahl(self):
        app, pre = self.app, self.app.preloader
        self.assertTrue(self.pump_until(lambda: pre.done))
        for key in self.app_gui.PRELOAD_GAME_VIEWS:
            self.assertIsNone(app.views.built(key), key)
        self.assertFalse(pre._run(("view", "firma")))


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class GamePreloadTest(AppCase):
    profile = True

    def test_reise_reiter_vorgebaut(self):
        app, pre = self.app, self.app.preloader
        self.stop_preloader()
        app.show_view("game")
        self.root.update()
        app.views["game"]._enter_slot()
        app.show_view("dashboard")
        self.root.update()
        pre.last_input = 0
        self.assertTrue(self.pump_until(lambda: pre.done))
        for key in self.app_gui.PRELOAD_GAME_VIEWS:
            self.assertIn(("view", key), pre.step_ms, "Spielansicht nicht vorgeladen")
        self.assertIn(("tab", "reise", "erfolge"), pre.step_ms)
        journey = app.views.built("reise")
        self.assertIsNotNone(journey)
        self.assertTrue(journey._parked, "vorgebauter Reiter liegt nicht bereit")
        builds = []
        original = journey._tab_build
        journey._tab_build = lambda build: (builds.append(1), original(build))
        hint = self.watch_hint()
        app.show_view("reise")
        self.root.update()
        self.assertEqual(journey._parked, [], "vorgebaute Reiter nicht weggeraeumt")
        journey._choose_tab("erfolge")
        self.root.update()
        self.assertEqual(builds, [], "Reiter wurde trotz Vorladen neu gebaut")
        self.assertEqual(hint["shown"], 0)
        self.assertEqual(journey.tab, "erfolge")
        self.assertEqual(self.errors, [])

    def test_reiter_ohne_vorladen_mit_ladeanzeige(self):
        app = self.app
        self.stop_preloader()
        app.show_view("game")
        self.root.update()
        app.views["game"]._enter_slot()
        self.stop_preloader()
        hint = self.watch_hint()
        app.show_view("reise")      # noch nicht vorbereitet: Ladeanzeige
        self.root.update()
        self.assertEqual(hint["shown"], 1)
        app.views["reise"]._choose_tab("erfolge")
        self.root.update()
        self.assertEqual(hint["shown"], 2)
        self.assertIn(self.app_gui.fisi_theme.LOADING_TEXT, hint["texts"])
        self.assertEqual(self.errors, [])


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class LoadingHintTest(AppCase):
    def test_anzeige_bei_langsamer_ansicht(self):
        app = self.app
        self.stop_preloader()
        theme = self.app_gui.fisi_theme
        hint = self.watch_hint()
        app.show_view("progress")   # gross und noch nicht vorgeladen
        self.root.update()
        self.assertEqual(hint["shown"], 1)
        self.assertIn(theme.LOADING_TEXT, hint["texts"])
        frame = hint["frames"][0]
        self.assertFalse(frame.winfo_exists(), "Ladeanzeige ist nicht verschwunden")
        self.assertIsNone(app._loading)
        self.assertEqual(app.current, "progress")
        self.assertIn(("view", "progress"), app.cost_ms)
        # Unveraendert: kein Neuzeichnen, keine Anzeige
        app.show_view("dashboard")
        self.root.update()
        app.show_view("progress")
        self.root.update()
        self.assertEqual(hint["shown"], 1)
        # Muss neu zeichnen und dauerte zuletzt lange: Anzeige
        app.cost_ms[("view", "progress")] = theme.LOADING_THRESHOLD_MS + 200
        app.views["progress"]._refreshed = None
        app.show_view("dashboard")
        self.root.update()
        app.show_view("progress")
        self.root.update()
        self.assertEqual(hint["shown"], 2)
        # Muss neu zeichnen, ging zuletzt aber schnell: keine Anzeige
        app.cost_ms[("view", "progress")] = 20
        app.views["progress"]._refreshed = None
        app.show_view("dashboard")
        self.root.update()
        app.show_view("progress")
        self.root.update()
        self.assertEqual(hint["shown"], 2)
        self.assertEqual(self.errors, [])

    def test_keine_anzeige_bei_kleiner_ansicht(self):
        app = self.app
        self.stop_preloader()
        hint = self.watch_hint()
        app.do_search("raid")       # Suche: kein Vorlade-Schritt, unbekannt = schnell
        self.root.update()
        self.assertEqual(hint["shown"], 0)
        self.assertEqual(app.current, "search")

    def test_klick_waehrend_der_anzeige_wird_ignoriert(self):
        app = self.app
        self.stop_preloader()
        show = app._show_loading
        inner = []

        def shown():
            frame = show()
            # wie ein Klick, der waehrend des Zeichnens der Anzeige ankommt
            app._pumping = True
            try:
                app.show_view("calc")
            finally:
                app._pumping = False
            inner.append(app.views.built("calc"))
            return frame
        app._show_loading = shown
        app.show_view("quiz")
        self.root.update()
        self.assertEqual(inner, [None])
        self.assertEqual(app.current, "quiz")
        self.assertEqual(self.errors, [])


# Kindprozess: Programm starten und waehrend des Vorladens schliessen
CHILD = r'''
import os, sys, time
sys.path.insert(0, sys.argv[1])
os.chdir(sys.argv[1])
mode = sys.argv[2]
import app_gui
app_gui.UpdateController.auto_check = lambda self: None
app_gui.SyncController.auto_start = lambda self: None
init = app_gui.FISIApp.__init__
state = {"steps_after_close": 0}

def patched(self, root):
    init(self, root)
    app = self
    if mode == "vorladen":
        run = app_gui.ViewPreloader._run
        def counting(pre, task):
            if app._closing:
                state["steps_after_close"] += 1
            worked = run(pre, task)
            if worked and pre.steps_done == 3:
                print("GESCHLOSSEN", time.time(), flush=True)
                root.after(0, app.on_close)
            return worked
        app_gui.ViewPreloader._run = counting
    elif mode == "im_schritt":
        # Schliessen mitten in einem Vorlade-Schritt (z.B. aus einer
        # Ereignisverarbeitung heraus)
        run = app_gui.ViewPreloader._run
        def closing(pre, task):
            worked = run(pre, task)
            if worked and pre.steps_done == 2:
                print("GESCHLOSSEN", time.time(), flush=True)
                app.on_close()
            return worked
        app_gui.ViewPreloader._run = closing
    elif mode == "anzeige":
        # Das X kommt an, waehrend die Ladeanzeige gezeichnet wird: als
        # Fensterereignis in der Warteschlange, das die Anzeige beim
        # Zeichnen selbst abarbeitet (wie WM_DELETE_WINDOW)
        root.bind("<<FisiSchliessen>>", lambda _e: app.on_close())
        show = app._show_loading
        def closing_hint():
            print("GESCHLOSSEN", time.time(), flush=True)
            root.event_generate("<<FisiSchliessen>>", when="tail")
            return show()
        app._show_loading = closing_hint
        root.after(300, lambda: app.show_view("progress"))
app_gui.FISIApp.__init__ = patched
app_gui.main()
print("NACH_SCHLIESSEN", state["steps_after_close"], flush=True)
print("ENDE", time.time(), flush=True)
'''


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class CloseDuringPreloadTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="fisi vorladen beenden ")
        self.env = dict(os.environ, FISI_DB_PATH=os.path.join(self.folder, "fisi.db"))
        self.env.pop("FISI_SELFTEST", None)
        self.script = os.path.join(self.folder, "kind.py")
        with open(self.script, "w", encoding="utf-8") as handle:
            handle.write(CHILD)

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def close_in(self, mode):
        process = subprocess.Popen([sys.executable, self.script, HERE, mode],
                                   env=self.env, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True)
        try:
            output, _ = process.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            process.kill()
            output, _ = process.communicate()
            self.fail("Prozess laeuft nach 120 s noch (%s):\n%s" % (mode, output))
        stamps = {}
        for line in output.splitlines():
            if line.startswith(("GESCHLOSSEN ", "ENDE ")):
                word, value = line.split()
                stamps[word] = float(value)
        self.assertIn("GESCHLOSSEN", stamps, output[-3000:])
        self.assertIn("ENDE", stamps, "mainloop nicht verlassen (%s):\n%s"
                      % (mode, output[-3000:]))
        self.assertEqual(process.returncode, 0, output[-3000:])
        self.assertLess(stamps["ENDE"] - stamps["GESCHLOSSEN"], CLOSE_LIMIT)
        try:
            with open(os.path.join(self.folder, "fehler.log"), encoding="utf-8") as handle:
                log = handle.read()
        except OSError:
            log = ""
        self.assertEqual(log, "", "fehler.log nicht leer (%s)" % mode)
        self.assertNotIn("TclError", output)
        self.assertNotIn("Traceback", output)
        return output

    def test_schliessen_waehrend_vorladen(self):
        output = self.close_in("vorladen")
        self.assertIn("NACH_SCHLIESSEN 0", output)

    def test_schliessen_im_vorlade_schritt(self):
        output = self.close_in("im_schritt")
        self.assertIn("NACH_SCHLIESSEN 0", output)

    def test_schliessen_waehrend_ladeanzeige(self):
        self.close_in("anzeige")


if __name__ == "__main__":
    unittest.main(verbosity=2)
