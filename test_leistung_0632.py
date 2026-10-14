#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer N6 (0.63.2): Leistung PC I - mit Oberflaeche.

B-I-01 (Schriftgroesse/Darstellung wechseln):
  * die neue Oberflaeche ist bedienbar (Abdeckung weg), bevor die alte ganz
    abgebaut ist; die alte wird danach in mehreren Schritten abgebaut (je
    Ansicht ein Schritt), zuletzt startet das Vorladen neu
  * ein offener Bereich "Optische Anpassungen" bleibt offen, sein Inhalt kommt
    im naechsten Schritt (Kopf schon offen, N6-F2)
  * danach: alte Oberflaeche weg, keine verwaisten Zeitgeber, keine Fehler,
    Haenger-Diagnose wieder wie vorher, Ergebnis gleich wie ohne Wechsel
  * waehrend des Abbaus: Seitenwechsel, zweiter Wechsel, laufende Pruefung
  * Leistungsmessung: Zeile "darstellung" mit beiden Zeiten (bis bedienbar,
    bis alles fertig); PerfMonitor ausser dem Feld theme_ready_ms unveraendert
    (FG-46 erweitert, N6-F3)

B-I-04 (Klick waehrend des Vorladens):
  * Rechner, Karteikarten, Szenarien (AP1/AP2) und Testprojekt werden beim
    Vorladen in Teilen gebaut, jeder Teil samt Zeichnen unter der Teil-Grenze
  * in Teilen gebaut (ganz oder halb und dann geoeffnet) sind die Ansichten
    gleich wie direkt gebaut (Steuerelemente, Texte, Lage)
  * ein Klick hat Vorrang vor dem naechsten Teil; die sichtbare Ansicht
    fasst der Vorlader nicht an

Braucht eine Anzeige (unter Linux z.B. xvfb-run). Ohne Anzeige werden die
Tests uebersprungen.

Start:  python test_leistung_0632.py
"""

import ast
import os
import shutil
import sys
import tempfile
import time
import traceback
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# Laengster Vorlade-Teil samt Zeichnen (wie test_vorladen.PART_LIMIT_MS:
# Auflage A3 aus 0.60.1 sind 150 ms, hier mit Luft fuer langsame Rechner)
PART_LIMIT_MS = 400

# Die vier Gruppen aus B-I-04 (Szenarien = AP1 und AP2)
PART_VIEWS = ("calc", "cards", "ap1scenarios", "scenarios", "testproject")


def _display_available():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:
        return False


HAS_DISPLAY = _display_available()


ScrollAreaType = []   # fisi_widgets.ScrollArea (erst mit Anzeige importiert)


def widget_tree(widget, geometry=True):
    """Liste (Tiefe, Klasse, Text, Pillen-Auswahl, sichtbar, Lage) in der
    Reihenfolge der Kinder - fuer den Vergleich zweier Aufbauten."""
    rows = []
    if not ScrollAreaType:
        import fisi_widgets
        ScrollAreaType.append(fisi_widgets.ScrollArea)

    def walk(item, depth):
        text = ""
        try:
            text = str(item.cget("text"))
        except Exception:
            pass
        if not text and item.winfo_class() == "Text":
            try:
                text = item.get("1.0", "end-1c")
            except Exception:
                text = ""
        value = ""
        get = getattr(item, "get", None)
        if type(item).__name__ == "PillGroup" and callable(get):
            value = str(get())
        mapped = bool(item.winfo_ismapped())
        row = [depth, type(item).__name__, text, value, mapped]
        if geometry and isinstance(item, ScrollAreaType[0]):
            # Bildlaufflaeche: Breite des Inhalts und waagerechte Lage
            row += [item.canvas.itemcget(item._window, "width"),
                    tuple(round(x, 4) for x in item.canvas.xview())]
        if geometry and mapped:   # Lage nicht gezeigter Elemente ist ohne Bedeutung
            row += [item.winfo_x(), item.winfo_y(), item.winfo_width(), item.winfo_height()]
        rows.append(tuple(row))
        for child in item.winfo_children():
            walk(child, depth + 1)
    walk(widget, 0)
    return rows


class AppCase(unittest.TestCase):
    """Eigenes Hauptfenster mit leerer Datenbank je Test (wie test_vorladen)."""

    preload = None   # FISI_VORLADEN fuer diesen Test (None = normal)
    font = None      # Schriftgroesse vor dem Start (None = normal)
    size = "1360x900"

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="fisi n6 ")
        os.environ["FISI_DB_PATH"] = os.path.join(self.folder, "test.db")
        os.environ["FISI_SELFTEST"] = os.path.join(self.folder, "log.txt")  # kein Netz
        os.environ["HOME"] = self.folder
        self._saved_preload = os.environ.get("FISI_VORLADEN")
        if self.preload is not None:
            os.environ["FISI_VORLADEN"] = self.preload
        else:
            os.environ.pop("FISI_VORLADEN", None)
        import customtkinter as ctk
        import app_gui
        import fisi_haenger
        import fisi_theme
        import fisi_widgets
        self.app_gui = app_gui
        self.fhg = fisi_haenger
        self.theme = fisi_theme
        fisi_widgets.FoldCard._open_state.clear()
        fisi_widgets._PHOTO_CACHE.clear()
        fisi_widgets._IMAGE_CACHE.clear()
        app_gui.apply_appearance()
        if self.font is not None:
            fisi_theme.save_font_size(self.font)
        self.errors = []
        self.root = ctk.CTk()
        self.root.report_callback_exception = lambda *exc: self.errors.append(
            "".join(traceback.format_exception(*exc)))
        # Fehler in Tcl-Zeitgebern (z.B. "invalid command name" eines
        # abgebauten Elements) kommen ueber bgerror, nicht als Python-Fehler
        self.root.tk.createcommand("bgerror", lambda *msg: self.errors.append(
            "bgerror: %s" % (msg,)))
        self.app = app_gui.FISIApp(self.root)
        self.root.geometry(self.size + "+0+0")
        self.pump(0.2)

    def tearDown(self):
        try:
            tk_ = self.root.tk
            for job in tk_.splitlist(tk_.call("after", "info")):
                tk_.call("after", "cancel", job)
            self.root.destroy()
        except Exception:
            pass
        import fisi_theme
        import fisi_widgets
        fisi_widgets._PHOTO_CACHE.clear()
        fisi_widgets._IMAGE_CACHE.clear()
        fisi_widgets.FoldCard._open_state.clear()
        # Schriftgroesse gilt je Geraet (HOME) - fuer den naechsten Test zurueck
        if fisi_theme.current_font_size != "normal":
            fisi_theme.save_font_size("normal")
            self.app_gui.apply_ui_scale(fisi_theme.font_factor())
        if self._saved_preload is None:
            os.environ.pop("FISI_VORLADEN", None)
        else:
            os.environ["FISI_VORLADEN"] = self._saved_preload
        shutil.rmtree(self.folder, ignore_errors=True)

    def pump(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.root.update()
            time.sleep(0.005)

    def pump_until(self, condition, timeout=120):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if condition():
                return True
            self.root.update()
            time.sleep(0.005)
        return condition()

    def wait_preload(self):
        pre = self.app.preloader
        pre.last_input = 0
        self.assertTrue(self.pump_until(lambda: pre.done and not self.app.recolor_pending),
                        "Vorladen nicht fertig")


# ============================================================================
#  B-I-01: Wechsel von Schriftgroesse und Darstellung
# ============================================================================

@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class RecolorTest(AppCase):
    """Reihenfolge, Abbau in Schritten, Optik-Bereich im naechsten Schritt."""

    def watch(self):
        """Zeichnet die Reihenfolge auf: Abdeckung weg, jeder Abbau-Schritt
        (mit Zahl der zerstoerten Elemente), Start des Vorladens."""
        app = self.app
        old = app.container
        old_views = [app.views.built(key) for key in app.views.keys()]
        old_views = [view for view in old_views if view is not None]
        log = {"events": [], "old": old, "old_views": old_views,
               "total": self.app_gui.count_widgets(old)}
        hide = app._hide_busy

        def hide_busy(overlay):
            hide(overlay)
            settings = app.views.built("settings")
            fold = getattr(settings, "folds", {}).get("optik") if settings else None
            log["events"].append(("aufgedeckt", old.winfo_exists() == 1,
                                  bool(old.winfo_exists()) and bool(old.winfo_ismapped()),
                                  None if fold is None else (fold.opened, fold.built),
                                  app.preloader.started_at))
        app._hide_busy = hide_busy
        step = app._recolor_step

        def recolor_step():
            exists = bool(old.winfo_exists())
            before = self.app_gui.count_widgets(old) if exists else 0
            alive_before = sum(1 for view in old_views if view.winfo_exists())
            entry = ["schritt", 0, 0, exists]
            log["events"].append(entry)   # vor dem Schritt (er startet evtl. das Vorladen)
            step()
            after = self.app_gui.count_widgets(old) if old.winfo_exists() else 0
            alive_after = sum(1 for view in old_views if view.winfo_exists())
            entry[1:3] = [before - after, alive_before - alive_after]
            # K3: nach jedem Schritt keine verwaisten Zeitgeber
            log.setdefault("verwaist", []).extend(self.app_gui._orphaned_timers(self.root))
        app._recolor_step = recolor_step
        start = app.preloader.start

        def preload_start(*args, **kwargs):
            log["events"].append(("vorladen", bool(old.winfo_exists())))
            return start(*args, **kwargs)
        app.preloader.start = preload_start
        return log

    def open_optik(self):
        app = self.app
        app.show_view("settings")
        app.views["settings"].open_area("optik")
        self.pump(0.1)
        self.assertTrue(app.views["settings"].folds["optik"].built)

    def finish(self):
        self.assertTrue(self.pump_until(lambda: not self.app.recolor_pending, 60),
                        "Abbau nicht fertig")

    def check_order(self, log):
        events = log["events"]
        kinds = [event[0] for event in events]
        self.assertEqual(kinds[0], "aufgedeckt", kinds)
        # K1: bei "Abdeckung weg" gibt es die alte Oberflaeche noch, unsichtbar
        self.assertTrue(events[0][1], "alte Oberflaeche schon abgebaut, als die "
                                      "Abdeckung wegging (Abbau am Stueck)")
        self.assertFalse(events[0][2], "alte Oberflaeche noch sichtbar")
        steps = [event for event in events if event[0] == "schritt" and event[1] > 0]
        self.assertGreaterEqual(len(steps), 2, "Abbau nicht in Schritten: %s" % events)
        # K2: kein Schritt baut mehr als eine Ansicht ab; der letzte (Rest:
        # Seitenleiste, Kopf) hoechstens ein Viertel der alten Oberflaeche
        for event in steps:
            self.assertLessEqual(event[2], 1, "mehrere Ansichten in einem Schritt: %s"
                                 % (event,))
        rest = steps[-1]
        self.assertEqual(rest[2], 0, "letzter Schritt baute noch eine Ansicht ab")
        self.assertLessEqual(rest[1], log["total"] / 4.0, (rest, log["total"]))
        # K6: Vorladen erst nach dem letzten Abbau-Schritt, genau einmal
        self.assertEqual(kinds.count("vorladen"), 1, kinds)
        self.assertEqual(kinds[-1], "vorladen", kinds)
        self.assertFalse(events[-1][1], "Vorladen startete vor dem Ende des Abbaus")
        # K3: alles weg, keine verwaisten Zeitgeber, keine Fehler
        self.assertEqual(log.get("verwaist", []), [])
        self.assertFalse(log["old"].winfo_exists())
        for view in log["old_views"]:
            self.assertFalse(view.winfo_exists())
        self.assertEqual(self.app_gui._orphaned_timers(self.root), [])
        self.assertEqual(self.errors, [])

    def test_a_schrift_reihenfolge_und_optik(self):
        """A-N6-01: Optionen mit offenem Bereich, Schrift "Gross"."""
        app = self.app
        self.wait_preload()
        self.open_optik()
        task_before = self.fhg.current()[1]
        log = self.watch()
        app.change_font_size("gross")
        # K4: Abdeckung weg, Optionen sichtbar, Bereich offen, Inhalt folgt
        self.assertEqual(log["events"][0][3], (True, False),
                         "Optik-Bereich bei Abdeckung weg nicht offen-ohne-Inhalt")
        self.assertEqual(app.current, "settings")
        self.assertTrue(app.views.built("settings").winfo_ismapped())
        self.finish()
        self.check_order(log)
        fold = app.views.built("settings").folds["optik"]
        self.assertTrue(fold.opened and fold.built)
        self.assertEqual(len(app.views.built("settings").custom_colors.sliders), 9)
        self.assertTrue(fold.body.winfo_ismapped())
        self.assertEqual(self.theme.current_font_size, "gross")
        self.assertEqual(self.fhg.current()[1], task_before)
        # A-N6-02: zurueck auf Normal, gleiche Reihenfolge
        log = self.watch()
        app.change_font_size("normal")
        self.finish()
        self.check_order(log)
        self.assertEqual(self.theme.font_factor(), 1.0)

    def test_b_darstellung_hell_dunkel(self):
        """A-N6-03: Darstellung wechseln (alte Oberflaeche wird nicht umgefaerbt)."""
        app = self.app
        self.wait_preload()
        app.show_view("dashboard")
        self.pump(0.1)
        log = self.watch()
        other = self.theme.MODE_LIGHT if not self.theme.light else self.theme.MODE_DARK
        app.change_color(mode=other)
        self.finish()
        self.check_order(log)

    def test_c_grundfarbe(self):
        """A-N6-04: Grundfarbe/Vorlage wechseln."""
        app = self.app
        self.wait_preload()
        self.open_optik()
        presets = [item["id"] for item in self.theme.PRESETS
                   if item["id"] != self.theme.current_preset]
        log = self.watch()
        app.change_color(preset_id=presets[0])
        self.finish()
        self.check_order(log)
        self.assertEqual(self.theme.current_preset, presets[0])

    def test_d_optik_zu_bleibt_zu(self):
        """A-N6-11: Optik-Bereich zugeklappt: bleibt zu, kein Schritt fuer ihn."""
        app = self.app
        self.wait_preload()
        app.show_view("settings")
        self.pump(0.1)
        self.assertFalse(app.views["settings"].folds["optik"].opened)
        log = self.watch()
        app.change_font_size("gross")
        self.assertEqual(log["events"][0][3], (False, False))
        self.finish()
        self.check_order(log)
        self.assertFalse(app.views.built("settings").folds["optik"].opened)

    def test_e_andere_bereiche_bleiben(self):
        """K4: Klappzustand der anderen Bereiche wie vor dem Wechsel."""
        app = self.app
        self.wait_preload()
        self.open_optik()
        settings = app.views["settings"]
        settings.open_area("tagesziel")
        self.pump(0.1)
        before = {key: fold.opened for key, fold in settings.folds.items()}
        app.change_font_size("gross")
        self.finish()
        after = {key: fold.opened for key, fold in app.views.built("settings").folds.items()}
        self.assertEqual(after, before)

    def test_f_verwaiste_zeitgeber(self):
        """K3: ein Zeitgeber eines Elements der alten Oberflaeche wird nach dem
        Abbau abgebrochen (verwaist), nicht stehen gelassen."""
        app = self.app
        self.wait_preload()
        app.show_view("dashboard")
        self.pump(0.1)
        dashboard = app.views.built("dashboard")
        dashboard.after(600000, lambda: None)
        log = self.watch()
        app.change_font_size("gross")
        self.finish()
        self.assertFalse(dashboard.winfo_exists())
        self.assertEqual(log.get("verwaist"), [])
        self.assertEqual(self.app_gui._orphaned_timers(self.root), [])
        self.assertEqual(self.errors, [])

    def test_g_klick_waehrend_abbau(self):
        """A-N6-05 (K7a): Seitenwechsel sofort nach dem Aufdecken wirkt."""
        app = self.app
        self.wait_preload()
        self.open_optik()
        log = self.watch()
        app.change_font_size("gross")
        self.assertTrue(app.recolor_pending)
        self.assertFalse(app._recoloring)
        app.show_view("quiz")
        self.assertEqual(app.current, "quiz")
        self.assertTrue(log["old"].winfo_exists(), "Abbau schon fertig vor dem Klick")
        self.finish()
        self.assertEqual(app.current, "quiz")
        self.assertTrue(app.views.built("quiz").winfo_ismapped())
        self.check_order(log)

    def test_h_zweiter_wechsel_waehrend_abbau(self):
        """A-N6-06 (K7b): zweiter Wechsel waehrend des Abbaus: zweite Wahl
        gilt, beide alten Oberflaechen werden ganz abgebaut."""
        app = self.app
        self.wait_preload()
        self.open_optik()
        first_old = app.container
        first_views = [app.views.built(key) for key in app.views.keys()]
        app.change_font_size("gross")
        self.assertTrue(first_old.winfo_exists())
        second_old = app.container
        second_views = [app.views.built(key) for key in app.views.keys()]
        starts = []
        start = app.preloader.start
        app.preloader.start = lambda *a, **k: (starts.append(1), start(*a, **k))[1]
        app.change_font_size("sehr_gross")
        self.finish()
        self.assertEqual(self.theme.current_font_size, "sehr_gross")
        self.assertAlmostEqual(self.theme.font_factor(), 1.3)
        for widget in [first_old, second_old] + [v for v in first_views + second_views if v]:
            self.assertFalse(widget.winfo_exists())
        self.assertEqual(len(starts), 1)
        self.assertEqual(self.app_gui._orphaned_timers(self.root), [])
        fold = app.views.built("settings").folds["optik"]
        self.assertTrue(fold.opened and fold.built)
        self.assertEqual(self.errors, [])

    def test_i_laufende_pruefung(self):
        """A-N6-08: laufende Pruefung - alte Uhr angehalten, neue laeuft,
        keine Zugriffe auf abgebaute Elemente."""
        app = self.app
        self.wait_preload()
        app.show_view("quiz")
        self.pump(0.1)
        quiz = app.views["quiz"]
        import fisi_pruefung as fp
        ask = self.app_gui.messagebox.askyesno
        self.app_gui.messagebox.askyesno = lambda *args, **kwargs: True
        try:
            quiz.exam.start(sorted(fp.EXAM)[0])
        finally:
            self.app_gui.messagebox.askyesno = ask
        self.pump(1.2)
        self.assertIsNotNone(fp.load_running())
        old_exam = quiz.exam
        app.change_font_size("gross")
        self.finish()
        self.assertFalse(old_exam.winfo_exists())
        self.pump(1.2)
        self.assertEqual(self.errors, [])
        self.assertEqual(self.app_gui._orphaned_timers(self.root), [])

    def test_j_messzeile_beide_zeiten(self):
        """Leistungsmessung: Zeile "darstellung" kommt nach dem Abbau, dauer_ms
        (bis alles fertig) >= max_ms (bis bedienbar) > 0."""
        import fisi_leistung as fle
        app = self.app
        self.wait_preload()
        app.perf.set_active(True)
        try:
            app.change_font_size("gross")
            rows = []
            record = app.perf.rec.record

            def recording(event, *args, **kwargs):
                if event == fle.EVENT_THEME:
                    rows.append(dict(kwargs, pending=app.recolor_pending,
                                     old_alive=bool(app._teardown)))
                return record(event, *args, **kwargs)
            app.perf.rec.record = recording
            self.finish()
        finally:
            app.perf.set_active(False)
        self.assertEqual(len(rows), 1, rows)
        row = rows[0]
        self.assertFalse(row["old_alive"])
        self.assertIsNotNone(row["max_ms"])
        self.assertGreater(row["max_ms"], 0)
        self.assertGreaterEqual(row["dauer_ms"], row["max_ms"])
        self.assertIsNone(app.perf.theme_ready_ms)


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class RecolorSameResultTest(AppCase):
    """K5: Nach dem Wechsel in Schritten sieht die Oberflaeche aus wie nach
    einem Start mit dieser Schriftgroesse (Referenz ohne Wechsel)."""

    preload = "0"

    def settings_tree(self):
        view = self.app.views.built("settings")
        self.pump(0.3)
        return widget_tree(view)

    def test_gleich_wie_ohne_wechsel(self):
        app = self.app
        app.show_view("settings")
        app.views["settings"].open_area("optik")
        app.views["settings"].open_area("tagesziel")
        self.pump(0.2)
        app.change_font_size("gross")
        self.assertTrue(self.pump_until(lambda: not app.recolor_pending, 60))
        app.views["settings"].canvas.yview_moveto(0)
        staged = self.settings_tree()
        # Referenz: neues Fenster mit gespeicherter Schrift "Gross", dieselben
        # Bereiche offen
        self.tearDown_keep_font()
        app = self.app
        app.show_view("settings")
        app.views["settings"].open_area("optik")
        app.views["settings"].open_area("tagesziel")
        self.pump(0.2)
        app.views["settings"].canvas.yview_moveto(0)
        direct = self.settings_tree()
        self.assertEqual(len(staged), len(direct))
        for index, (one, two) in enumerate(zip(staged, direct)):
            self.assertEqual(one, two, "Zeile %d" % index)
        self.assertEqual(self.errors, [])

    def tearDown_keep_font(self):
        """Fenster abbauen und mit derselben Datenbank/Schrift neu starten."""
        import customtkinter as ctk
        import fisi_widgets
        tk_ = self.root.tk
        for job in tk_.splitlist(tk_.call("after", "info")):
            tk_.call("after", "cancel", job)
        self.root.destroy()
        fisi_widgets.FoldCard._open_state.clear()
        fisi_widgets._PHOTO_CACHE.clear()
        fisi_widgets._IMAGE_CACHE.clear()
        self.app_gui.apply_appearance()
        self.root = ctk.CTk()
        self.root.report_callback_exception = lambda *exc: self.errors.append(
            "".join(traceback.format_exception(*exc)))
        self.app = self.app_gui.FISIApp(self.root)
        self.root.geometry("1360x900+0+0")
        self.pump(0.2)


# ============================================================================
#  B-I-04: Vorladen in Teilen
# ============================================================================

@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class PartsPreloadTest(AppCase):

    def test_a_teile_und_grenze(self):
        """K9/K10 (A-N6-20): die fuenf Ansichten in >= 2 Teilen, jeder Schritt
        dieser Ansichten samt Zeichnen unter der Teil-Grenze."""
        app, pre = self.app, self.app.preloader
        for key in PART_VIEWS:
            self.assertTrue(app.views.can_build_in_parts(key), key)
        self.wait_preload()
        report = {}
        for key in PART_VIEWS:
            self.assertIn(("part", key), pre.block_ms, key)
            view = app.views.built(key)
            self.assertIsNotNone(view, key)
            self.assertFalse(view.parts_pending, key)
            mine = {task: ms for task, ms in pre.block_ms.items() if task[1] == key}
            report[key] = mine
        print("\nN6 Vorladen: fertig %s ms" % pre.finished_ms)
        for key, mine in report.items():
            print("  %-13s %s" % (key, ", ".join("%s=%d" % (t[0], ms)
                                                  for t, ms in sorted(mine.items()))))
        others = {self.app_gui.task_label(t): ms for t, ms in pre.block_ms.items()
                  if t[1] not in PART_VIEWS}
        print("  andere (nur Bericht): %s" % sorted(others.items(), key=lambda kv: -kv[1]))
        for key, mine in report.items():
            for task, ms in mine.items():
                self.assertLessEqual(ms, PART_LIMIT_MS, "%s: %d ms" % (task, ms))
        # Rechner: prepare (Rest der Subnetting-Karte) lief nach den Teilen
        self.assertFalse(app.views.built("calc").subnet.build_rest())
        # K13: Reihenfolge unveraendert
        order = []
        for task in pre.step_ms:
            first = ("view", task[1]) if task[0] == "part" else task
            if task[0] != "tab" and first not in order:
                order.append(first)
        self.assertEqual(order, list(self.app_gui.PRELOAD_ORDER))
        self.assertEqual(self.errors, [])

    def tree_after_show(self, key):
        self.app.show_view(key)
        self.pump(0.4)
        view = self.app.views.built(key)
        view.to_top()
        self.pump(0.1)
        return widget_tree(view)

    def rebuild_direct(self, key):
        """Die Ansicht wegwerfen und direkt (am Stueck) neu bauen."""
        app = self.app
        app.show_view("dashboard")
        self.pump(0.1)
        old = dict.pop(app.views, key)
        old.destroy()
        self.pump(0.1)
        view = app.views[key]
        if key == "calc":
            # In Teilen entstehen auch die uebrigen Subnetting-Ansichten (die
            # beim Vorladen am Stueck prepare baut) - Referenz also mit prepare
            self.assertTrue(view.prepare())
        return self.tree_after_show(key)

    def fresh_parts(self, key):
        """Die Ansicht neu in Teilen anlegen (erster Teil); eine schon
        vorgeladene vorher wegwerfen."""
        old = dict.pop(self.app.views, key, None)
        if old is not None:
            old.destroy()
            self.pump(0.05)
        return self.app.views.build_in_parts(key)

    def stop_preloader(self):
        pre = self.app.preloader
        if pre.job is not None:
            self.root.after_cancel(pre.job)
            pre.job = None
        pre.queue = []
        pre.done = True

    def assert_same(self, parts, direct, key):
        self.assertEqual(len(parts), len(direct), key)
        for index, (one, two) in enumerate(zip(parts, direct)):
            self.assertEqual(one, two, "%s Zeile %d" % (key, index))

    def test_b_gleich_wie_direkt(self):
        """K11 (A-N6-22): in Teilen gebaut = direkt gebaut (Baum mit Lage)."""
        self.stop_preloader()
        app = self.app
        for key in PART_VIEWS:
            view = self.fresh_parts(key)
            self.assertTrue(view.parts_pending, key)
            count = 1
            while view.parts_pending:
                view.build_next()
                count += 1
                self.pump(0.02)
            self.assertGreaterEqual(count, 2, key)
            parts = self.tree_after_show(key)
            direct = self.rebuild_direct(key)
            self.assert_same(parts, direct, key)
        self.assertEqual(self.errors, [])

    def test_c_halb_dann_oeffnen(self):
        """K11 (A-N6-23): ein Teil vorgeladen, dann oeffnet der Nutzer: fertig
        gebaut, gleich wie direkt, Ladeanzeige hoechstens einmal."""
        self.stop_preloader()
        app = self.app
        for key in PART_VIEWS:
            view = self.fresh_parts(key)
            view.build_next()
            self.assertTrue(view.parts_pending, key)
            shown = []
            show = app._show_loading
            app._show_loading = lambda: (shown.append(1), show())[1]
            try:
                parts = self.tree_after_show(key)
            finally:
                app._show_loading = show
            self.assertIs(app.views.built(key), view)
            self.assertFalse(view.parts_pending, key)
            self.assertLessEqual(len(shown), 1)
            direct = self.rebuild_direct(key)
            self.assert_same(parts, direct, key)
        self.assertEqual(self.errors, [])

    def test_d_klick_hat_vorrang(self):
        """K12 (A-N6-24): zwischen zwei Teilen eine Eingabe - der naechste Teil
        wartet, die Warteschlange bleibt."""
        app, pre = self.app, self.app.preloader
        self.stop_preloader()
        view = self.fresh_parts("calc")
        self.assertTrue(view.parts_pending)
        pre.queue = [("part", "calc"), ("view", "calc")]
        pre.done = False
        pre._input()
        before = list(pre.queue)
        pending = len(view._parts)
        pre._step()
        self.assertEqual(pre.queue, before)
        self.assertEqual(len(view._parts), pending)
        self.assertIsNotNone(pre.job)
        # ohne Eingabe: genau ein Teil je Schritt
        pre.last_input = 0
        self.root.after_cancel(pre.job)
        pre.job = None
        pre._step()
        self.assertEqual(len(view._parts), pending - 1)
        self.assertEqual(self.errors, [])

    def test_e_sichtbare_ansicht_unberuehrt(self):
        """A-N6-25: Nutzer oeffnet den Rechner, waehrend dessen Teile anstehen:
        fertig gebaut, der Vorlader ueberspringt ihn."""
        app, pre = self.app, self.app.preloader
        self.stop_preloader()
        view = self.fresh_parts("calc")
        app.show_view("calc")
        self.pump(0.1)
        self.assertFalse(view.parts_pending)
        pre.queue = [("part", "calc"), ("view", "calc")]
        pre.done = False
        pre.last_input = 0
        steps = pre.steps_done
        pre._step()
        self.assertEqual(pre.steps_done, steps)
        self.assertEqual(pre.queue, [])
        self.assertEqual(self.errors, [])

    def test_f_rechner_rechnet_gleich(self):
        """A-N6-26: nach dem Vorladen in Teilen rechnet der Rechner wie direkt."""
        self.stop_preloader()
        app = self.app
        view = self.fresh_parts("calc")
        view.complete()
        app.show_view("calc")
        self.pump(0.2)

        def results(calc):
            calc.calc_raid()
            calc.calc_screen()
            calc.calc_ups("empfehlung")
            return [calc.txt_raid.get("1.0", "end-1c"), calc.txt_screen.get("1.0", "end-1c"),
                    calc.txt_ups.get("1.0", "end-1c")]
        parts = results(view)
        app.show_view("dashboard")
        dict.pop(app.views, "calc").destroy()
        app.show_view("calc")
        self.pump(0.2)
        self.assertEqual(results(app.views["calc"]), parts)
        self.assertEqual(self.errors, [])

    def test_g_eingaben_sichern_bei_halber_ansicht(self):
        """Offene Eingaben speichern (Beenden, Sicherung) mit halb vorgeladenen
        Ansichten: kein Fehler."""
        self.stop_preloader()
        app = self.app
        for key in PART_VIEWS:
            self.fresh_parts(key)
        app.flush_inputs(revealed=True)
        app.flush_inputs(revealed=False)
        for key in PART_VIEWS:
            self.assertTrue(app.views.built(key).parts_pending, key)
        self.assertEqual(self.errors, [])


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class PartsPreloadSmallTest(PartsPreloadTest):
    """K11 auch bei schmalem Fenster und grosser Schrift (die Ansichten passen
    sich dort an: Spalten, Umbrueche, Breite der Bildlaufflaeche)."""

    font = "sehr_gross"
    size = "1120x720"

    def test_a_teile_und_grenze(self):
        self.skipTest("nur bei 1360x900 Normal (PartsPreloadTest)")

    test_d_klick_hat_vorrang = test_e_sichtbare_ansicht_unberuehrt = \
        test_f_rechner_rechnet_gleich = test_g_eingaben_sichern_bei_halber_ansicht = \
        test_a_teile_und_grenze


# ============================================================================
#  N6-F3 (FG-46 erweitert): PerfMonitor nur um das Feld erweitert
# ============================================================================

# PerfMonitor.__init__ und PerfMonitor.theme auf e0f9c7e (Stand vor N6),
# woertlich; verglichen wird der AST (mit dem laufenden Python geparst)
BASE_SOURCE = {
    "__init__": 'def __init__(self, app):\n    self.app = app\n    self.root = app.root\n    self.rec = fle.Recorder(APP_VERSION, "PC", toolkit=ctk.__version__)\n    # Ab 0.59.2: Spalte "vorgang" (letzter Vorgang, fisi_haenger)\n    self.rec.task_source = lambda: fhg.current()[1]\n    # Ab 0.59.3: Startzeile nennt die Eingabemethoden-Umgehung (nur wenn aktiv)\n    eingabe = fisi_eingabe.result()\n    if eingabe and eingabe.get("aktiv"):\n        self.rec.start_task = fisi_eingabe.MESS_TASK\n    self._flush_job = None\n    self._bound = False\n    self._resize = None\n    self._size = None\n    if self.rec.active:\n        self._start()\n        self.rec.record(fle.EVENT_START, elemente=self.elements(),\n                        aufgaben=self.tasks())',
    "theme": 'def theme(self, old, new, started):\n    if not self.rec.active:\n        return\n    elapsed = (time.perf_counter() - started) * 1000\n    self.rec.record(fle.EVENT_THEME, von=old, nach=new, dauer_ms=elapsed,\n                    elemente=self.elements(), aufgaben=self.tasks())\n    self.rec.flush()',
}
FIELD = "theme_ready_ms"


def _strip_field(node):
    """Alle Zuweisungen an self.FIELD und das Argument max_ms=self.FIELD
    entfernen (das sind die einzigen erlaubten Aenderungen)."""

    class Strip(ast.NodeTransformer):
        def visit_Assign(self, item):
            targets = [t for t in item.targets
                       if not (isinstance(t, ast.Attribute) and t.attr == FIELD)]
            if not targets:
                return None
            item.targets = targets
            return item

        def visit_Call(self, item):
            self.generic_visit(item)
            item.keywords = [k for k in item.keywords
                             if not (isinstance(k.value, ast.Attribute)
                                     and k.value.attr == FIELD)]
            return item
    return Strip().visit(node)


def _dump(item):
    item = _strip_field(item)
    body = item.body
    if body and isinstance(body[0], ast.Expr) and \
            isinstance(getattr(body[0], "value", None), ast.Constant):
        body = body[1:]   # Docstring
    item.body = body
    return ast.dump(ast.Module(body=[item], type_ignores=[]), include_attributes=False)


def method_dump(source, cls_name, method):
    """AST einer Methode ohne das Feld (siehe _strip_field) und ohne Docstring."""
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == cls_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == method:
                    return _dump(item)
    raise AssertionError("%s.%s nicht gefunden" % (cls_name, method))


def base_dump(method):
    return _dump(ast.parse(BASE_SOURCE[method]).body[0])


class PerfMonitorFieldTest(unittest.TestCase):
    """N6-F3: Das Feld misst nur. Ausser dem Feld und seinen Zuweisungen
    (und dem Eintrag in der Messzeile) ist an PerfMonitor.__init__ und
    PerfMonitor.theme nichts geaendert (AST-Vergleich mit dem woertlichen Stand e0f9c7e)."""

    def source(self):
        with open(os.path.join(HERE, "app_gui.py"), encoding="utf-8") as handle:
            return handle.read()

    def test_nur_das_feld(self):
        source = self.source()
        for method in BASE_SOURCE:
            self.assertEqual(method_dump(source, "PerfMonitor", method), base_dump(method),
                             method)

    def test_feld_wird_gesetzt_und_gelesen(self):
        source = self.source()
        tree = ast.parse(source)
        writers = set()
        readers = set()
        for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
            for func in [n for n in cls.body if isinstance(n, ast.FunctionDef)]:
                for node in ast.walk(func):
                    if isinstance(node, ast.Attribute) and node.attr == FIELD:
                        place = "%s.%s" % (cls.name, func.name)
                        if isinstance(node.ctx, ast.Store):
                            writers.add(place)
                        else:
                            readers.add(place)
        self.assertEqual(writers, {"PerfMonitor.__init__", "PerfMonitor.theme",
                                   "FISIApp._finish_recolor"})
        self.assertEqual(readers, {"PerfMonitor.theme"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
