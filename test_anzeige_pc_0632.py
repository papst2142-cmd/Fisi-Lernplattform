#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests 0.63.2 Strang S1b: Anzeige PC (und die Handy-Teile derselben Texte).

  * B-D-05  Dezimalkomma: "66,7 %", "3,2 von 18,8 MB" (keine "%.1f"-Formate mehr)
  * B-D-07  Tausenderpunkt ("von 1.565 Karten", "Offen 2.174"), "0 %" mit
            geschuetztem Leerzeichen, Testprojekt "50 von 50 Kundenaufträgen"
  * B-G-16  ein gemeinsamer Text "Alle Lerndaten löschen" (PC = Handy)
  * B-J-01/02/03 Kontraste >= 4,5:1, B-D-11 Rahmen/Schalter-Spur >= 3:1
            (alle 6 Hintergruende, hell und dunkel)
  * B-J-N1  Abschlussprojekt: Tab "Als PDF" vor "Als Text"
  * B-J-N2  Rundgang: Tab links -> rechts
  * B-D-09/Z2 aktiver Menueeintrag ganz sichtbar, jeder Eintrag erreichbar
            und nicht vom Lernstatus-Kasten verdeckt
  * B-D-12  "Historie löschen": Bestaetigung bzw. genau ein Fehlerfenster
  * Z1      Punkte abrunden ohne Gleitkommafehler (49,95 -> 49,9)
  * Z6      PC-Listenpfeile auf der ersten/letzten Seite gesperrt

Die Oberflaechen-Teile laufen je Schriftgroesse in einem eigenen Prozess.
Gegenprobe gegen einen anderen Code-Stand (z.B. 14b3bd4):
    ANZEIGE_CODE=<ordner mit dem Code> xvfb-run -a python test_anzeige_pc_0632.py

Start:  xvfb-run -a python test_anzeige_pc_0632.py
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("ANZEIGE_CODE") or HERE)
sys.path.insert(0, CODE)

FAKTOREN = {1.0: "normal", 1.15: "gross", 1.3: "sehr_gross"}
MIN_TEXT = 4.5
MIN_RAND = 3.0


def _source(*parts):
    with open(os.path.join(CODE, *parts), encoding="utf-8") as handle:
        return handle.read()


def _code_only(source):
    """Quelltext ohne Kommentarzeilen."""
    return "\n".join(line for line in source.splitlines()
                     if not line.strip().startswith("#"))


# Zahlen mit 4 oder mehr Ziffern ohne Tausenderpunkt; Datumsangaben
# (2026.10.13, "Oktober 2026") und Uhrzeiten sind keine Mengen
_DATE = re.compile(r"\b\d{4}\.\d{2}\.\d{2}\b|\b\d{2}\.\d{2}\.\d{4}\b|\(c\) \d{4}|"
                   r"(Januar|Februar|März|April|Mai|Juni|Juli|August|September|"
                   r"Oktober|November|Dezember) \d{4}|Version \S+")
_BARE = re.compile(r"(?<![\d.,])\d{4,}(?![\d.,])")


def bare_numbers(texts):
    found = []
    for text in texts:
        cleaned = _DATE.sub("", text)
        if _BARE.search(cleaned):
            found.append(text)
    return found


# ============================================================================
#  Teile ohne Oberflaeche
# ============================================================================

class QuelltextTest(unittest.TestCase):
    """B-D-05 und B-G-16 am Quelltext (PC und Handy)."""

    def test_b_d_05_keine_punkt_formate(self):
        for parts in (("app_gui.py",), ("mobile", "src", "main.py")):
            code = _code_only(_source(*parts))
            self.assertNotIn('"%.1f %%"', code, parts)
            self.assertNotIn("(%.1f %%)", code, parts)
            self.assertNotIn("%.1f von %.1f MB", code, parts)

    def test_b_g_16_gemeinsamer_text(self):
        import fisi_optionen as fo
        text = getattr(fo, "RESET_ALL_TEXT", "")
        for word in ("Klausursimulationen", "Subnetting-Trainer", "Testprojekte",
                     "Abschlussprojekt", "Einstellungen", "Spielstand",
                     "Wissen im Spiel", "Abgleich", "nicht rückgängig"):
            self.assertIn(word, text)
        old = "Der Spielstand des Lernspiels bleibt erhalten."
        for parts in (("app_gui.py",), ("mobile", "src", "main.py")):
            source = _source(*parts)
            self.assertIn("fo.RESET_ALL_TEXT", source, parts)
            self.assertNotIn(old, source, parts)
            self.assertNotIn("auch auf dem PC", source, parts)

    def test_b_g_16_aussagen_am_code(self):
        """Was der Text verspricht, stimmt mit dem Loeschen ueberein."""
        import fisi_core as fc
        for table in ("pruefungen", "trainer_aufgaben", "project_events",
                      "card_events", "quiz_answers", "test_results"):
            self.assertIn(table, fc.EVENT_TABLES)
        for kept in ("abschlussprojekt", "spiel_ereignisse"):
            self.assertNotIn(kept, fc.EVENT_TABLES)

    def test_b_d_12_texte(self):
        import fisi_optionen as fo
        self.assertEqual(getattr(fo, "DELETE_HISTORY_DONE", None), "Die Historie wurde gelöscht.")
        self.assertEqual(getattr(fo, "DELETE_NOTHING", None), "Es wurde nichts gelöscht.")


class PunkteTest(unittest.TestCase):
    """Z1 (Auflage 4.4 Nr. 1): abrunden ohne Gleitkommafehler."""

    FAELLE = ((49.95, "49,9"), (49.99, "49,9"), (50.0, "50"), (0.05, "0"), (0.0, "0"),
              (49.99999999999999, "50"), (66.66, "66,6"), (100.0, "100"), (7.3, "7,3"),
              (0.1, "0,1"), (0.7, "0,7"), (2.3, "2,3"))

    def test_hilfe(self):
        import fisi_pruefung as fp
        self.assertTrue(hasattr(fp, "punkte_text"), "fisi_pruefung.punkte_text fehlt")
        for value, want in self.FAELLE:
            self.assertEqual(fp.punkte_text(value), want, repr(value))

    def test_alle_zehntel_ohne_kippen(self):
        import fisi_pruefung as fp
        for tenth in range(1001):
            want = str(tenth // 10) if tenth % 10 == 0 else "%d,%d" % divmod(tenth, 10)
            self.assertEqual(fp.punkte_text(tenth / 10), want, tenth)

    def test_pc_benutzt_hilfe(self):
        import app_gui
        for value, want in self.FAELLE:
            self.assertEqual(app_gui._points(value), want, repr(value))


def _load_mobile():
    import flet  # noqa: F401
    sys.path.insert(1, os.path.join(CODE, "mobile", "src"))
    import main
    return main


class HandyTest(unittest.TestCase):
    """Handy-Teile derselben Texte (Bildschirm-Attrappe wie test_dashboard)."""

    @classmethod
    def setUpClass(cls):
        home = tempfile.mkdtemp(prefix="fisi_anzeige_h_")
        os.environ.update(HOME=home, APPDATA=home, FISI_DB_PATH=os.path.join(home, "h.db"),
                          FISI_SELFTEST=os.path.join(home, "s.log"))
        import flet as ft
        main = _load_mobile()
        import fisi_core as fc
        cls.ft, cls.main, cls.fc = ft, main, fc

        class FakePage:
            views = []

            def __getattr__(self, _name):
                return lambda *args, **kwargs: None

        class FakeApp(main.FISIMobileApp):
            def __init__(self):
                self.page = FakePage()
                self.body = ft.Container()
                self.db = main.DBManager()
                self.sync = main.SyncController(self)
                self.perf = main.MobilePerf(self)
                self.screens = {}
                self._recoloring = False

        cls.FakeApp = FakeApp
        db = main.DBManager()
        db.save_test_result(2, 3, 200.0 / 3, "4", 60)

    def texts(self, control, found=None):
        found = [] if found is None else found
        for attr in ("value", "text", "label", "tooltip"):
            value = getattr(control, attr, None)
            if isinstance(value, str) and value.strip():
                found.append(value)
        for attr in ("content", "title", "big", "small"):
            value = getattr(control, attr, None)
            if value is not None and hasattr(value, "__dict__"):
                self.texts(value, found)
        for attr in ("controls", "spans"):
            for child in getattr(control, attr, None) or []:
                self.texts(child, found)
        return found

    def screen_texts(self, key):
        screen = self.main.SCREEN_CLASSES[key](self.FakeApp())
        if hasattr(screen, "on_show"):
            screen.on_show()
        return self.texts(screen.root)

    def test_b_d_07_dashboard_tausender(self):
        texts = self.screen_texts("dashboard")
        self.assertEqual(bare_numbers(texts), [])
        self.assertIn(self.main.DASH_CARDS_SUB % self.fc.de_int(len(self.fc.KARTEIKARTEN)),
                      texts)

    def test_b_d_07_count_text(self):
        counts = {self.main.Q_OPEN: 2174, self.main.Q_PRACTICE: 0, self.main.Q_DONE: 1000}
        self.assertEqual(self.main.count_text(counts),
                         "Offen\u00a02.174 · Zu üben\u00a00 · Abgeschlossen\u00a01.000")

    def test_b_d_07_ring_prozent(self):
        source = _code_only(_source("mobile", "src", "main.py") + _source("mobile", "src", "ui.py"))
        self.assertNotIn('"%d%%"', source)

    def test_b_d_07_testprojekt_kundenauftraege(self):
        texts = self.screen_texts("testproject")
        count = len(self.fc.PROJEKTARBEITEN)
        self.assertIn("%d von %d Kundenaufträgen" % (count, count), texts)
        ap1 = self.screen_texts("ap1scenarios")
        self.assertTrue([t for t in ap1 if re.fullmatch(r"[\d.]+ von [\d.]+ Aufgaben", t)], ap1)

    def test_b_d_05_fortschritt(self):
        texts = self.screen_texts("progress")
        self.assertIn("66,7 %", texts)
        self.assertFalse([t for t in texts if re.search(r"\d\.\d %", t)], texts)

    def test_z1_bereichszeilen(self):
        self.assertEqual(self.main.points_text(49.95), "49,9")
        self.assertEqual(self.main.points_text(50.0), "50")

    def test_pc_gleich_handy(self):
        """Gleichheitstest PC = Handy (Plan 5.3 Nr. 5) fuer die neuen Texte."""
        import app_gui
        for value, _want in PunkteTest.FAELLE:
            self.assertEqual(app_gui._points(value), self.main.points_text(value))
        counts = {self.main.Q_OPEN: 2174, self.main.Q_PRACTICE: 3, self.main.Q_DONE: 1000}
        split = lambda text: [part.strip() for part in text.split("·")]  # noqa: E731
        self.assertEqual(split(app_gui.count_text(counts)), split(self.main.count_text(counts)))


# ============================================================================
#  Oberflaeche PC (eigener Prozess je Schriftgroesse)
# ============================================================================

def worker(faktor, breite, hoehe):
    home = tempfile.mkdtemp(prefix="fisi_anzeige_")
    os.environ.update(HOME=home, APPDATA=home, FISI_DB_PATH=os.path.join(home, "t.db"),
                      FISI_SELFTEST=os.path.join(home, "log.txt"))
    os.chdir(CODE)
    import sqlite3
    import tkinter as tk
    import customtkinter as ctk
    import app_gui
    import fisi_core as fc
    import fisi_theme
    import fisi_widgets
    import fisi_hilfe as fh
    fisi_theme.apply_font_size(FAKTOREN[faktor])
    fisi_widgets.apply_ui_scale(faktor)
    app_gui.UpdateController.auto_check = lambda self: None
    app_gui.SyncController.auto_start = lambda self: None
    app_gui.FISIApp.maybe_start_tour = lambda self: None
    boxes = []
    app_gui.messagebox.showerror = lambda *a, **k: boxes.append(("error",) + a)
    app_gui.messagebox.showinfo = lambda *a, **k: boxes.append(("info",) + a)
    app_gui.messagebox.askyesno = lambda *a, **k: True

    # Lernstand: ein paar Karten/Fragen und ein Testergebnis 66,67 %
    db = fc.DBManager()
    for card in fc.KARTEIKARTEN[:5]:
        db.log_card(card["cat"], card["q"], "lernen", True)
    for question in fc.QUIZ_QUESTIONS[:5]:
        db.log_quiz_answer(question["cat"], question["q"], False)
    db.save_test_result(2, 3, 200.0 / 3, "4", 60)

    root = ctk.CTk()
    root.geometry("%dx%d+0+0" % (breite, hoehe))
    app = app_gui.FISIApp(root)
    errors = {}

    def fail(key, text):
        errors.setdefault(key, []).append(text)

    def pump(seconds=0.3):
        end = time.time() + seconds
        while time.time() < end:
            root.update()
            time.sleep(0.01)

    def label_texts(widget, found=None):
        found = [] if found is None else found
        try:
            text = widget.cget("text")
            if isinstance(text, str) and text.strip():
                found.append(text)
        except (tk.TclError, ValueError, AttributeError):
            pass
        if isinstance(widget, tk.Canvas):
            for item in widget.find_all():
                if widget.type(item) == "text":
                    found.append(widget.itemcget(item, "text"))
        for child in widget.winfo_children():
            label_texts(child, found)
        return found

    pump(0.8)
    root.geometry("%dx%d+0+0" % (breite, hoehe))
    pump(0.6)

    # -- B-D-07: Tausenderpunkt und "0 %" ---------------------------------
    for key in ("dashboard", "quiz", "notebook", "settings", "cards"):
        app.show_view(key)
        pump(0.5)
        texts = label_texts(app.views[key]) + label_texts(app.sidebar)
        bad = bare_numbers(texts)
        if bad:
            fail("tausender", "%s: %s" % (key, bad[:5]))
        wrong = [t for t in texts if re.fullmatch(r"\d+%", t)]   # "0%" ohne Abstand
        if wrong:
            fail("ring", "%s: %s" % (key, wrong[:5]))
    counts = {app_gui.Q_OPEN: 2174, app_gui.Q_PRACTICE: 0, app_gui.Q_DONE: 1000}
    if app_gui.count_text(counts) != ("Offen\u00a02.174  ·  Zu üben\u00a00  ·  "
                                       "Abgeschlossen\u00a01.000"):
        fail("count_text", repr(app_gui.count_text(counts)))

    # -- B-D-05: Fortschritt ------------------------------------------------
    app.show_view("progress")
    pump(0.5)
    progress = app.views["progress"]
    texts = label_texts(progress)
    if "66,7 %" not in texts:
        fail("komma", "Durchschnitt/Bestes nicht '66,7 %%': %s"
             % [t for t in texts if "%" in t][:6])
    rows = [progress.tree.item(item, "values") for item in progress.tree.get_children()]
    if not any("66,7 %" in values for values in rows):
        fail("komma", "Tabelle: %s" % rows[:2])

    # -- Z6 und Kundenauftraege: Testprojekt-Liste --------------------------
    app.show_view("testproject")
    pump(0.5)
    paged = app.views["testproject"].paged
    count = len(fc.PROJEKTARBEITEN)
    want = "%d von %d Kundenaufträgen" % (count, count)
    if paged.lbl_count.cget("text") != want:
        fail("kundenauftraege", repr(paged.lbl_count.cget("text")))

    def arrows(owner):
        found = [w for w in owner.winfo_children() if isinstance(w, fisi_widgets.IconButton)]
        for child in owner.winfo_children():
            found += arrows(child)
        return found

    def state(button):
        return bool(getattr(button, "_enabled", True))

    pager = paged.lbl_page.master
    left, right = sorted(arrows(pager), key=lambda w: w.winfo_rootx())
    if state(left) or not state(right):
        fail("pfeile", "Seite 1: links %s, rechts %s" % (state(left), state(right)))
    paged.turn(99)
    pump(0.2)
    if not state(left) or state(right):
        fail("pfeile", "letzte Seite: links %s, rechts %s" % (state(left), state(right)))
    paged.turn(-99)
    pump(0.2)
    app.show_view("ap1scenarios")
    pump(0.4)
    ap_text = app.views["ap1scenarios"].paged.lbl_count.cget("text")
    if not ap_text.endswith(" Aufgaben"):
        fail("kundenauftraege", "AP1: %r" % ap_text)
    app.show_view("notebook")
    pump(0.5)
    note = app.views["notebook"]
    nleft, nright = sorted(arrows(note.lbl_page.master), key=lambda w: w.winfo_rootx())
    if state(nleft):
        fail("pfeile", "Notizblock Seite 1: links aktiv")

    # -- B-J-N1: Tab im Abschlussprojekt ------------------------------------
    app.show_view("abschluss")
    pump(0.5)
    project = app.views["abschluss"]
    buttons = {}

    def walk(widget):
        caption = getattr(widget, "_caption", None)
        if caption in ("Löschen", "Als PDF", "Als Text"):
            buttons.setdefault(caption, widget)
        for child in widget.winfo_children():
            walk(child)
    walk(project)
    if len(buttons) == 3:
        def owner(widget):
            for caption, button in buttons.items():
                if str(widget).startswith(str(button)):
                    return caption
            return None
        order = []
        current = buttons["Löschen"]
        for _step in range(12):
            current = current.tk_focusNext()
            if current is None:
                break
            name = owner(current)
            if name and name not in order:
                order.append(name)
        if order[:2] != ["Als PDF", "Als Text"]:
            fail("tab_projekt", "Reihenfolge ab Löschen: %s" % order)
        if not buttons["Als PDF"].winfo_rootx() < buttons["Als Text"].winfo_rootx():
            fail("tab_projekt", "Anordnung geaendert")
    else:
        fail("tab_projekt", "Knoepfe nicht gefunden: %s" % sorted(buttons))

    # -- B-J-N2: Rundgang ----------------------------------------------------
    tour = app.start_tour()
    pump(0.4)
    tour.show_page(1)
    pump(0.3)
    captions = [getattr(w, "_caption", "?") for w in tour.focusables]
    if captions != [fh.TOUR_NEXT, fh.TOUR_SKIP, fh.TOUR_BACK]:
        fail("tab_rundgang", "Seite 2: %s" % captions)
    inner = [tour._focus_target(w) for w in tour.focusables]
    inner[0].focus_force()
    pump(0.2)
    seen = [root.focus_get()]
    for _step in range(3):
        root.focus_get().event_generate("<Tab>")
        pump(0.1)
        seen.append(root.focus_get())
    if seen != [inner[0], inner[1], inner[2], inner[0]]:
        fail("tab_rundgang", "Tab-Folge Seite 2 stimmt nicht")
    tour.show_page(len(fh.TOUR_PAGES) - 1)
    pump(0.3)
    buttons_last = [getattr(w, "_caption", None) for w in tour.focusables
                    if isinstance(w, app_gui.NeoButton)]
    if buttons_last != [fh.TOUR_SKIP, fh.TOUR_BACK, fh.TOUR_FINISH]:
        fail("tab_rundgang", "letzte Seite: %s" % buttons_last)
    if isinstance(tour.focusables[0], app_gui.NeoButton):
        fail("tab_rundgang", "letzte Seite beginnt nicht mit einer Eingabe")
    tour.destroy()
    pump(0.2)

    # -- B-D-09 / Z2: Menue --------------------------------------------------
    sidebar = app.sidebar
    canvas = sidebar.menu_area.canvas

    def fully_visible(row):
        top = canvas.winfo_rooty()
        bottom = top + canvas.winfo_height()
        y = row.winfo_rooty()
        return row.winfo_ismapped() and y >= top and y + row.winfo_height() <= bottom

    for key in ("calc", "help", "settings", "dashboard", "progress"):
        app.show_view(key)
        pump(0.5)
        if not fully_visible(sidebar.rows[key]):
            fail("menue_aktiv", "%s nicht ganz sichtbar" % key)
    # dasselbe mit offenem Spiel-Untermenue (Plan: Normal 1360 x 900)
    if "game" not in sidebar.expanded:
        sidebar._toggle("game")
    pump(0.3)
    for key in ("calc", "help", "settings"):
        app.show_view(key)
        pump(0.5)
        if not fully_visible(sidebar.rows[key]):
            fail("menue_aktiv", "%s nicht ganz sichtbar (Spiel offen)" % key)
    rows = getattr(sidebar, "sub_rows", {})
    status_tops = [child.winfo_rooty() for child in sidebar.winfo_children()
                   if child.winfo_manager() == "pack"
                   and child.pack_info().get("side") == "bottom"]
    menu_bottom = canvas.winfo_rooty() + canvas.winfo_height()
    if status_tops and menu_bottom > min(status_tops):
        fail("menue_erreichbar", "Menue reicht unter den Lernstatus-Kasten")
    for key, row in list(sidebar.rows.items()) + list(rows.items()):
        if not row.winfo_ismapped():
            continue
        sidebar.menu_area.see(row)
        pump(0.15)
        if not fully_visible(row):
            fail("menue_erreichbar", "%s nicht erreichbar" % key)

    # -- B-D-12: Historie loeschen -------------------------------------------
    app.show_view("settings")
    pump(0.4)
    settings = app.views["settings"]
    boxes.clear()
    settings.clear_history()
    pump(0.2)
    if [b[0] for b in boxes] != ["info"] or "Die Historie wurde gelöscht." not in boxes[0][2]:
        fail("historie", "Erfolg: %s" % boxes)
    boxes.clear()
    real = app.db.get_connection

    def broken():
        raise sqlite3.OperationalError("attempt to write a readonly database")
    app.db.get_connection = broken
    try:
        settings.clear_history()
        pump(0.2)
    finally:
        app.db.get_connection = real
    if len(boxes) != 1 or "Es wurde nichts gelöscht." not in boxes[0][2]:
        fail("historie", "Fehler: %s" % boxes)

    print("ERG " + json.dumps({"fehler": errors}), flush=True)
    os._exit(0)


def farben_worker():
    """B-J-01/02/03 und B-D-11 in allen 6 Hintergruenden, hell und dunkel."""
    home = tempfile.mkdtemp(prefix="fisi_farben_")
    os.environ.update(HOME=home, APPDATA=home, FISI_DB_PATH=os.path.join(home, "t.db"),
                      FISI_SELFTEST=os.path.join(home, "log.txt"))
    os.chdir(CODE)
    import datetime
    from tkinter import ttk
    import customtkinter as ctk
    import app_gui
    import fisi_core as fc
    import fisi_theme
    import fisi_widgets
    from fisi_theme import C
    app_gui.UpdateController.auto_check = lambda self: None
    app_gui.SyncController.auto_start = lambda self: None
    app_gui.FISIApp.maybe_start_tour = lambda self: None
    fisi_theme.BUSY_MIN_SECONDS = 0
    db = fc.DBManager()
    db.log_card(fc.KARTEIKARTEN[0]["cat"], fc.KARTEIKARTEN[0]["q"], "lernen", True)
    root = ctk.CTk()
    root.geometry("1360x900+0+0")
    app = app_gui.FISIApp(root)
    errors = {}
    werte = {}

    def fail(key, text):
        errors.setdefault(key, []).append(text)

    def pump(seconds=0.3):
        end = time.time() + seconds
        while time.time() < end:
            root.update()
            time.sleep(0.01)

    def find(widget, test):
        if test(widget):
            return widget
        for child in widget.winfo_children():
            hit = find(child, test)
            if hit is not None:
                return hit
        return None

    def check(key, name, fore, back, minimum):
        ratio = fisi_theme.contrast(fore, back)
        werte.setdefault(key, []).append(round(ratio, 2))
        if ratio < minimum:
            fail(key, "%s: %s auf %s = %.2f:1" % (name, fore, back, ratio))

    pump(0.8)
    for mode in (fisi_theme.MODE_DARK, fisi_theme.MODE_LIGHT):
        for background in fisi_theme.BACKGROUND_IDS:
            app.change_color(background_id=background, mode=mode)
            pump(0.6)
            name = "%s/%s" % (mode, background)
            # B-J-01: Textfeld (make_text) und Liste "Rechtliches"
            # (Textfeld frisch ueber make_text, wie alle Textfelder der App)
            box = fisi_widgets.make_text(app.root)
            inner = box._textbox
            check("b_j_01", name + " Textfeld", inner.cget("selectforeground"),
                  inner.cget("selectbackground"), MIN_TEXT)
            box.destroy()
            dialog = app_gui.LegalDialog(app, "fremd")
            pump(0.3)
            if dialog.listbox is not None:
                check("b_j_01", name + " Liste", dialog.listbox.cget("selectforeground"),
                      dialog.listbox.cget("selectbackground"), MIN_TEXT)
            else:
                fail("b_j_01", "%s: keine Liste im Fenster" % name)
            dialog.destroy()
            # B-J-02: Auswahlzeile der Tabelle
            style = ttk.Style(root)
            fore = dict(style.map("Dash.Treeview", "foreground")).get("selected")
            back = dict(style.map("Dash.Treeview", "background")).get("selected")
            for state_fore in style.map("Dash.Treeview", "foreground"):
                if "selected" in state_fore[:-1]:
                    fore = state_fore[-1]
            for state_back in style.map("Dash.Treeview", "background"):
                if "selected" in state_back[:-1]:
                    back = state_back[-1]
            check("b_j_02", name, str(fore), str(back), MIN_TEXT)
            # B-J-03: Kalenderzahl auf Lila
            app.show_view("dashboard")
            pump(0.4)
            calendar = app.views["dashboard"].calendar
            canvas = calendar.canvas
            day = str(datetime.date.today().day)
            colors = [canvas.itemcget(item, "fill") for item in canvas.find_all()
                      if canvas.type(item) == "text" and canvas.itemcget(item, "text") == day]
            if not colors:
                fail("b_j_03", "%s: Tag %s nicht gefunden" % (name, day))
            for color in colors:
                check("b_j_03", name, color, C["purple"], MIN_TEXT)
            # B-D-11: Rahmen der Aufklappliste und Spur der Schalter
            menu = app.views["abschluss"].menu_project
            parts = menu._canvas.find_withtag("border_parts")
            if not parts:
                fail("b_d_11", "%s: Aufklappliste ohne Rahmen" % name)
            else:
                check("b_d_11", name + " Rahmen", menu._canvas.itemcget(parts[0], "fill"),
                      C["card"], MIN_RAND)
            app.show_view("settings")
            pump(0.4)
            switch = find(app.views["settings"], lambda w: isinstance(w, ctk.CTkSwitch))
            if switch is None:
                fail("b_d_11", "%s: kein Schalter" % name)
            else:
                check("b_d_11", name + " Schalter", switch.cget("fg_color"), C["card"],
                      MIN_RAND)
    print("ERG " + json.dumps({"fehler": errors, "werte": werte}), flush=True)
    os._exit(0)


def _tk_ok():
    try:
        import tkinter
        tkinter.Tk().destroy()
        return True
    except Exception:
        return False


HAS_DISPLAY = False if "--fall" in sys.argv else _tk_ok()


def _run(args):
    done = subprocess.run([sys.executable, os.path.abspath(__file__), "--fall"] + args,
                          capture_output=True, text=True, timeout=900, cwd=HERE,
                          env=dict(os.environ, ANZEIGE_CODE=CODE))
    lines = [line for line in done.stdout.splitlines() if line.startswith("ERG ")]
    if not lines:
        raise AssertionError("kein Ergebnis:\n%s\n%s" % (done.stdout[-2000:], done.stderr[-4000:]))
    return json.loads(lines[-1][4:])


_CACHE = {}


def _result(faktor, breite, hoehe):
    key = (faktor, breite, hoehe)
    if key not in _CACHE:
        _CACHE[key] = _run(["anzeige", str(faktor), str(breite), str(hoehe)])
    return _CACHE[key]["fehler"]


CHECKS = ("tausender", "ring", "count_text", "komma", "kundenauftraege", "pfeile",
          "tab_projekt", "tab_rundgang", "menue_aktiv", "menue_erreichbar", "historie")
FENSTER = {1.0: (1360, 900), 1.15: (1120, 720), 1.3: (1120, 720)}


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class OberflaecheTest(unittest.TestCase):
    """Je Schriftgroesse ein Prozess; je Pruefpunkt ein eigener Test."""


def _make(faktor, check):
    def test(self):
        fehler = _result(faktor, *FENSTER[faktor])
        self.assertEqual(fehler.get(check, []), [], "%s %s" % (FAKTOREN[faktor], check))
    return test


for _faktor in FAKTOREN:
    for _check in CHECKS:
        setattr(OberflaecheTest, "test_%s_%s" % (FAKTOREN[_faktor], _check),
                _make(_faktor, _check))


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class FarbenTest(unittest.TestCase):
    """B-J-01/02/03 (>= 4,5:1) und B-D-11 (>= 3:1), 6 Hintergruende x hell/dunkel."""

    @classmethod
    def setUpClass(cls):
        cls.result = _run(["farben"])
        print("\n  Kontraste: %s" % {k: (min(v), max(v)) for k, v in
                                     cls.result.get("werte", {}).items()})

    def test_b_j_01_markierung(self):
        self.assertEqual(self.result["fehler"].get("b_j_01", []), [])

    def test_b_j_02_auswahlzeile(self):
        self.assertEqual(self.result["fehler"].get("b_j_02", []), [])

    def test_b_j_03_kalenderzahl(self):
        self.assertEqual(self.result["fehler"].get("b_j_03", []), [])

    def test_b_d_11_rahmen_und_spur(self):
        self.assertEqual(self.result["fehler"].get("b_d_11", []), [])


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--fall":
        if sys.argv[2] == "anzeige":
            worker(float(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]))
        else:
            farben_worker()
    unittest.main(verbosity=2)
