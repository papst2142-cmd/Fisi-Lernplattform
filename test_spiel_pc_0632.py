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
  B-I-05  Eingebaute Leistungsmessung: Seitenwechsel bis fertig gezeichnet,
          Zaehlen der Elemente ausserhalb der Dauer, Feld "messart" (2) und
          getrennte Auswertung alter und neuer Messart (fisi_leistung).

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


# ============================================================================
#  B-N-01: Fehler beim Aufbau eines Reiters
# ============================================================================

def _texts(widget, out=None):
    import tkinter
    import customtkinter as ctk
    out = [] if out is None else out
    for child in widget.winfo_children():
        if isinstance(child, tkinter.Label) and isinstance(child.master, ctk.CTkBaseClass):
            continue   # innerer Label eines CTkLabel (Text sonst doppelt)
        try:
            out.append(str(child.cget("text")))
        except Exception:   # noqa: BLE001 - Rahmen ohne Text
            pass
        _texts(child, out)
    return out


class ReiterFehlerTest(AppCase):
    profile = True

    def setUp(self):
        if not HAS_DISPLAY:
            self.fail("keine Anzeige - dieser Test darf nicht uebersprungen werden "
                      "(unter Linux mit xvfb-run starten)")
        super().setUp()
        import fisi_game_gui
        self.gui = fisi_game_gui
        self.shown = []
        self._saved_showerror = fisi_game_gui.messagebox.showerror
        fisi_game_gui.messagebox.showerror = lambda title, text, **_k: self.shown.append(
            (title, text))
        self.stop_preloader()
        self.app.slot_chosen = True

    def tearDown(self):
        self.gui.messagebox.showerror = self._saved_showerror
        super().tearDown()

    def _click(self, row, key):
        # wie ein echter Klick: ueber die Ereignisschleife (Fehler landen dann
        # in report_callback_exception, nicht im Test)
        self.root.after(0, lambda: row.select(key))
        self.pump(0.3)

    def _packed(self, view):
        return [child for child in view.content.winfo_children()
                if child.winfo_manager() == "pack"]

    def _broken(self, view, name):
        original = getattr(type(view), name)

        def broken(self_, *args, **kwargs):
            original(self_, *args, **kwargs)
            raise RuntimeError("kuenstlicher Fehler im Reiter")
        setattr(view, name, lambda *a, **k: broken(view, *a, **k))
        return lambda: delattr(view, name)

    def test_reise_klick_auf_kaputten_reiter(self):
        self.app.show_view("reise")
        self.pump(0.3)
        view = self.app.views["reise"]
        self.assertEqual(view.tab, "rueckblick")
        good = view._tab_body
        before = self._packed(view)
        # "Erfolge" baut die Bestwerte (halb gebaut) und scheitert dann
        restore = self._broken(view, "_build_records")
        self._click(view._tab_row, "erfolge")
        # Meldung: Fenster und report_callback_exception (fehler.log)
        self.assertEqual(len(self.shown), 1, self.shown)
        self.assertEqual(self.shown[0][0], self.gui.TabCache.TAB_ERROR_TITLE)
        self.assertIn("„Erfolge“", self.shown[0][1])
        self.assertEqual(len(self.errors), 1)
        self.assertIn("kuenstlicher Fehler", self.errors[0])
        # Zurueck auf dem funktionierenden Reiter, nichts Halbes sichtbar
        self.assertEqual(view.tab, "rueckblick")
        self.assertEqual(view._tab_row.value, "rueckblick")
        self.assertEqual(self._packed(view), before)
        self.assertTrue(good.winfo_ismapped())
        self.assertNotIn("BESTWERTE", _texts(view.content))
        self.assertNotIn("erfolge", view._tab_frames)
        # Ohne Fehler geht der Reiter danach wieder auf
        restore()
        self._click(view._tab_row, "erfolge")
        self.assertEqual(view.tab, "erfolge")
        self.assertIn("BESTWERTE", _texts(view._tab_body))
        self.assertEqual(len(self._packed(view)), len(before))
        self.assertEqual(len(self.shown), 1)
        self.assertEqual(len(self.errors), 1)

    def test_reise_neuaufbau_mit_kaputtem_reiter(self):
        self.app.show_view("reise")
        self.pump(0.3)
        view = self.app.views["reise"]
        normal = len(self._packed(view))
        restore = self._broken(view, "_build_records")
        view.tab = "erfolge"
        self.root.after(0, view.render)
        self.pump(0.3)
        self.assertEqual(len(self.shown), 1)
        self.assertEqual(len(self.errors), 1)
        self.assertEqual(view.tab, "rueckblick")
        self.assertEqual(view._tab_row.value, "rueckblick")
        self.assertEqual(len(self._packed(view)), normal)
        self.assertTrue(view._tab_body.winfo_ismapped())
        self.assertNotIn("BESTWERTE", _texts(view.content))
        restore()


class FirmaReiterFehlerTest(ReiterFehlerTest):
    """Wie ReiterFehlerTest, aber mit gegruendeter Firma (alle Reiter)."""

    def setUp(self):
        if not HAS_DISPLAY:
            self.fail("keine Anzeige - dieser Test darf nicht uebersprungen werden "
                      "(unter Linux mit xvfb-run starten)")
        import traceback
        from test_reiter_sichtbar import _firma_spielstand
        self.folder = tempfile.mkdtemp(prefix="fisi reiterfehler ")
        os.environ["FISI_DB_PATH"] = os.path.join(self.folder, "test.db")
        os.environ["FISI_SELFTEST"] = os.path.join(self.folder, "log.txt")  # kein Netz
        os.environ["HOME"] = self.folder
        import customtkinter as ctk
        import app_gui
        import fisi_game_gui
        import fisi_widgets
        self.app_gui = app_gui
        fisi_widgets.FoldCard._open_state.clear()
        fisi_widgets._PHOTO_CACHE.clear()
        fisi_widgets._IMAGE_CACHE.clear()
        _firma_spielstand(os.environ["FISI_DB_PATH"])
        app_gui.apply_appearance()
        self.errors = []
        self.root = ctk.CTk()
        self.root.report_callback_exception = lambda *exc: self.errors.append(
            "".join(traceback.format_exception(*exc)))
        self.app = app_gui.FISIApp(self.root)
        self.root.geometry("1360x900+0+0")
        self.pump(0.2)
        self.gui = fisi_game_gui
        self.shown = []
        self._saved_showerror = fisi_game_gui.messagebox.showerror
        fisi_game_gui.messagebox.showerror = lambda title, text, **_k: self.shown.append(
            (title, text))
        self.stop_preloader()
        self.app.slot_chosen = True

    # die Reise-Tests laufen schon in ReiterFehlerTest
    test_reise_klick_auf_kaputten_reiter = None
    test_reise_neuaufbau_mit_kaputtem_reiter = None

    def test_firma_klick_auf_kaputten_reiter(self):
        view = self.app.views["firma"]
        self.app.show_view("firma")
        self.pump(0.3)
        tabs = [key for key, _name in self.gui.fg.firm_tabs(view.game.state)]
        self.assertGreater(len(tabs), 1, tabs)
        first = view.tab
        names = dict(self.gui.fg.firm_tabs(view.game.state))
        good = view._tab_body
        before = self._packed(view)
        for other in [key for key in tabs if key != first]:
            restore = self._broken(view, "_build_" + other)
            self._click(view._tab_row, other)
            self.assertIn("„%s“" % names[other], self.shown[-1][1])
            self.assertEqual(view.tab, first, other)
            self.assertEqual(view._tab_row.value, first, other)
            self.assertEqual(self._packed(view), before, other)
            self.assertTrue(good.winfo_ismapped(), other)
            restore()
        self.assertEqual(len(self.shown), len(tabs) - 1, self.shown)
        self.assertEqual(len(self.errors), len(tabs) - 1)


# ============================================================================
#  B-I-05: eingebaute Leistungsmessung (Seitenwechsel bis fertig gezeichnet)
# ============================================================================

class LeistungsMessartTest(AppCase):
    """B-I-05: Die Dauer eines Seitenwechsels reicht bis die Seite fertig
    gezeichnet ist (auch Arbeit, die erst durch die Groessen-Ereignisse beim
    Zeichnen entsteht), das Zaehlen der Elemente liegt ausserhalb, und die
    Zeile traegt messart 2. Alte Messdateien ohne Spalte werden gelesen, die
    Auswertung vergleicht nur gleiche Messart."""

    LOAD = 0.4    # kuenstliche Zeichenlast in Sekunden

    def setUp(self):
        if not HAS_DISPLAY:
            self.fail("keine Anzeige - dieser Test darf nicht uebersprungen werden "
                      "(unter Linux mit xvfb-run starten)")
        super().setUp()
        import fisi_leistung
        self.fle = fisi_leistung
        self.stop_preloader()
        self.app.perf.set_active(True)
        self.show("settings")

    def tearDown(self):
        try:
            self.app.perf.set_active(False)
        except Exception:   # noqa: BLE001
            pass
        super().tearDown()

    def show(self, key):
        # wie ein Klick: ueber die Ereignisschleife
        self.root.after(0, lambda: self.app.show_view(key))
        self.pump(0.6)

    def _pages(self):
        self.app.perf.rec.flush()
        return [row for row in self.fle.read_rows()
                if row["ereignis"] == self.fle.EVENT_PAGE]

    def _with_load(self, view):
        """Beim Zeigen einen Rahmen einhaengen, dessen erstes Groessen-Ereignis
        (entsteht erst beim Zeichnen, nach dem ersten Leerlauf) LOAD dauert."""
        import tkinter as tk
        original = view.on_show
        seen = []

        def on_show():
            original()
            frame = tk.Frame(view, width=50, height=50)

            def slow(_event):
                if not seen:
                    seen.append(1)
                    time.sleep(self.LOAD)
            frame.bind("<Configure>", slow)
            # erst im Leerlauf einhaengen: Geometrie und Groessen-Ereignis
            # entstehen dann erst beim Zeichnen, nach dem ersten Leerlauf
            # (wie bei Bedienelementen, die sich beim Zeichnen neu aufbauen)
            view.after_idle(lambda: frame.place(x=0, y=0))
        view.on_show = on_show
        return seen

    def test_dauer_bis_fertig_gezeichnet(self):
        seen = self._with_load(self.app.views["dashboard"])
        self.show("dashboard")
        self.assertEqual(seen, [1], "kuenstliche Zeichenlast lief nicht")
        row = self._pages()[-1]
        self.assertEqual((row["von"], row["nach"]), ("settings", "dashboard"))
        self.assertGreaterEqual(self.fle._duration(row), self.LOAD * 1000, row)
        self.assertEqual(self.fle.messart_of(row), self.fle.MESSART_GEZEICHNET)
        self.assertEqual(row["messart"], "2")
        self.assertTrue(row["elemente"] and row["aufgaben"])

    def test_zaehlen_ausserhalb_der_messung(self):
        perf = self.app.perf
        original = perf.elements

        def slow_count():
            time.sleep(1.5)
            return original()
        perf.elements = slow_count
        try:
            self.show("dashboard")
            self.pump(1.8)
        finally:
            perf.elements = original
        row = self._pages()[-1]
        self.assertEqual(row["nach"], "dashboard")
        self.assertTrue(row["elemente"])
        self.assertLess(self.fle._duration(row), 1500, row)

    def test_andere_ereignisse_ohne_messart(self):
        # Messart aendert kein Verhalten bestehender Messungen (FG-40):
        # Start, Darstellung usw. bleiben ohne Kennzeichnung
        self.show("dashboard")
        self.app.perf.rec.flush()
        rows = self.fle.read_rows()
        others = [row for row in rows if row["ereignis"] != self.fle.EVENT_PAGE]
        self.assertTrue(others)
        for row in others:
            self.assertEqual(row["messart"], "", row)

    def test_alte_datei_und_getrennte_auswertung(self):
        fle = self.fle
        # Messdatei von 0.63.1 (ohne Spalte messart)
        old_header = ";".join(fle.COLUMNS[:-1])
        old_path = os.path.join(self.folder, "alt.csv")
        with open(old_path, "w", encoding="utf-8") as handle:
            handle.write(old_header + "\n")
            for ms in ("36,0", "40,0", "38,0"):
                handle.write(";".join(["2026-10-01T10:00:00.000", "0.63.1", "PC", "Linux",
                                       "seite", "settings", "dashboard", ms] +
                                      [""] * (len(fle.COLUMNS) - 9)) + "\n")
        old_rows = fle.read_rows(old_path)
        self.assertEqual(len(old_rows), 3)
        self.assertNotIn("messart", old_rows[0])
        self.assertEqual({fle.messart_of(row) for row in old_rows}, {fle.MESSART_ALT})
        self.assertEqual(fle.page_times(old_rows, fle.MESSART_ALT),
                         {"dashboard": [36.0, 40.0, 38.0]})
        # neue Messung mit dem Programm
        self.show("dashboard")
        new_rows = self._pages()
        self.assertTrue(new_rows)
        # alt gegen neu: keine gemeinsame Messart -> kein Vergleich
        self.assertEqual(fle.compare_pages(old_rows, new_rows), {})
        # gleiche Messart wird verglichen
        both = fle.compare_pages(new_rows, new_rows)
        self.assertEqual(list(both), [fle.MESSART_GEZEICHNET])
        self.assertIn("dashboard", both[fle.MESSART_GEZEICHNET])
        self.assertEqual(fle.compare_pages(old_rows, old_rows),
                         {fle.MESSART_ALT: {"dashboard": (38.0, 38.0)}})
        # Eine alte Messdatei bekommt beim Weiterschreiben die neue Kopfzeile,
        # ihre Zeilen bleiben alte Messart
        rec = fle.Recorder("0.63.2", "PC", path=old_path)
        rec.active = True
        rec.record(fle.EVENT_PAGE, von="a", nach="b", dauer_ms=1.0,
                   messart=fle.MESSART_GEZEICHNET, speicher=False)
        rec.flush()
        rows = fle.read_rows(old_path)
        self.assertEqual([fle.messart_of(row) for row in rows],
                         [fle.MESSART_ALT] * 3 + [fle.MESSART_GEZEICHNET])


if __name__ == "__main__":
    unittest.main(verbosity=2)
