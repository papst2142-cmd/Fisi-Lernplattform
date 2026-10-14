#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests 0.63.2 N9 (B-J-06, B-E-06): Schriftstufen 160 % ("Extra groß") und
200 % ("Maximal").

Plan-Nachtrag 0.63.2, Nr. 25 (B-J-06) und Nr. 27 (B-E-06), F22 (b):
  * Stufenliste: die drei bisherigen Stufen unveraendert, dazu 1,6 und 2,0;
    unbekannte Kennung -> Normal (Mischbetrieb: 0.63.1 kennt die neuen
    Kennungen nicht und faellt ebenso auf Normal zurueck)
  * Handy: alle Seiten bauen bei 1,6 und 2,0 ohne Fehler (main.selftest);
    ab 160 % stehen Banner, Ringkarten und Kacheln untereinander, Kopfzeile
    und Diagramme werden hoeher; bis "Sehr gross" bleibt der Aufbau wie bisher
  * Handy-Navigationsleiste (B-E-06): Hoehe und Symbole wachsen mit der
    Schrift; die Beschriftung bleibt bei hoechstens 12 (gemessen: jede
    groessere Beschriftung bricht "Fortschritt" bei 384 dp mitten im Wort um)
  * PC: alle Hauptansichten (auch Spiel mit Firma) bauen bei 1,6 und 2,0 im
    Fenster 1120 x 720 ohne Fehler; jedes Bedienelement ist erreichbar (ganz
    im Fenster oder in einem rollbaren Bereich, den der Bildlauf erreicht);
    die Kopfzeile stellt das Suchfeld nur ab 160 % und nur bei Platzmangel
    unter die Brotkrumen

Gegen 14b3bd4 rot (nur drei Stufen; Kennung "riesig" unbekannt).

Start: xvfb-run -a python test_schriftstufe_0632.py   (PC-Teil braucht eine
Anzeige; vorher einmal python mobile/vorbereiten.py)
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

ALT = [{"id": "normal", "name": "Normal", "faktor": 1.0},
       {"id": "gross", "name": "Groß", "faktor": 1.15},
       {"id": "sehr_gross", "name": "Sehr groß", "faktor": 1.3}]
NEU_FAKTOREN = {"extra_gross": 1.6, "riesig": 2.0}


# ---------------------------------------------------------------------------
#  Stufenliste
# ---------------------------------------------------------------------------

class StufenTest(unittest.TestCase):

    def setUp(self):
        import fisi_theme
        self.th = fisi_theme
        self.vorher = fisi_theme.current_font_size

    def tearDown(self):
        self.th.apply_font_size(self.vorher)

    def test_liste(self):
        th = self.th
        self.assertEqual(th.FONT_SIZES[:3], ALT)            # alte Stufen byte-gleich
        self.assertEqual({s["id"]: s["faktor"] for s in th.FONT_SIZES[3:]}, NEU_FAKTOREN)
        self.assertEqual(len(th.FONT_SIZES), 5)
        faktoren = [s["faktor"] for s in th.FONT_SIZES]
        self.assertEqual(faktoren, sorted(faktoren))
        self.assertEqual(th.FONT_IDS, [s["id"] for s in th.FONT_SIZES])
        self.assertEqual(len(set(th.FONT_IDS)), 5)
        self.assertTrue(all(s["name"] for s in th.FONT_SIZES))

    def test_namen_b4(self):
        """Weisung zu Meldung 38/40, B4: Namen wortgleich, ohne Prozent, PC =
        Handy (eine Liste); die gespeicherten Kennungen bleiben, damit der
        Rueckweg zu 0.63.1 (unbekannte Kennung -> Normal) gleich bleibt."""
        th = self.th
        self.assertEqual([s["name"] for s in th.FONT_SIZES],
                         ["Normal", "Groß", "Sehr groß", "Extra groß", "Maximal"])
        self.assertEqual(th.FONT_IDS, ["normal", "gross", "sehr_gross", "extra_gross", "riesig"])
        self.assertEqual(th.FONT_CHOICES, [(s["id"], s["name"]) for s in th.FONT_SIZES])
        for item in th.FONT_SIZES:
            self.assertNotIn("%", item["name"])
            self.assertFalse(any(z.isdigit() for z in item["name"]), item["name"])
        # Gespeichert wird die Kennung, nie der Name
        import fisi_update
        home = tempfile.mkdtemp(prefix="fisi_stufe_name_")
        alt = os.environ.get("HOME"), os.environ.get("APPDATA")
        os.environ["HOME"] = os.environ["APPDATA"] = home
        try:
            for item in th.FONT_SIZES[3:]:
                settings = fisi_update.load_settings()
                settings[th.FONT_KEY] = th.apply_font_size(item["id"])
                fisi_update.save_settings(settings)
                self.assertEqual(fisi_update.load_settings()[th.FONT_KEY], item["id"])
                self.assertEqual(th.saved_font_size(), item["id"])
        finally:
            for key, value in zip(("HOME", "APPDATA"), alt):
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_kennungen(self):
        th = self.th
        for item in th.FONT_SIZES:
            self.assertEqual(th.apply_font_size(item["id"]), item["id"])
            self.assertEqual(th.font_factor(), item["faktor"])
        # unbekannte Kennung (z. B. von einer spaeteren Version) -> Normal
        self.assertEqual(th.apply_font_size("gibt_es_nicht"), "normal")
        self.assertEqual(th.font_factor("riesig"), 2.0)

    def test_gespeichert(self):
        import fisi_update
        th = self.th
        home = tempfile.mkdtemp(prefix="fisi_stufe_")
        alt = os.environ.get("HOME"), os.environ.get("APPDATA")
        os.environ["HOME"] = os.environ["APPDATA"] = home
        try:
            for kennung, soll in (("riesig", "riesig"), ("extra_gross", "extra_gross"),
                                  ("unsinn", "normal")):
                settings = fisi_update.load_settings()
                settings[th.FONT_KEY] = kennung
                fisi_update.save_settings(settings)
                self.assertEqual(th.saved_font_size(), soll)
        finally:
            for key, value in zip(("HOME", "APPDATA"), alt):
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


# ---------------------------------------------------------------------------
#  Handy (ohne Bildschirm)
# ---------------------------------------------------------------------------

SRC = os.path.join(HERE, "mobile", "src")


def _handy():
    if SRC not in sys.path:
        sys.path.insert(1, SRC)
    os.environ.setdefault("FISI_DB_PATH", os.path.join(tempfile.mkdtemp(), "h.db"))
    import main
    import ui
    return main, ui


def _selbsttest(stufe):
    """main.selftest() in einem eigenen Prozess bei dieser Stufe."""
    home = tempfile.mkdtemp(prefix="fisi_stufe_handy_")
    code = ("import os,sys; sys.path.insert(0, %r); os.chdir(%r)\n"
            "import fisi_theme; fisi_theme.apply_font_size(%r)\n"
            "import ui; ui.set_font_factor(fisi_theme.font_factor())\n"
            "import main; f = main.selftest()\n"
            "print('FAKTOR', ui.FONT_FACTOR[0])\n"
            "print('FEHLER', len(f)); [print(x[:2000]) for x in f]\n") % (SRC, SRC, stufe)
    env = dict(os.environ, HOME=home, FISI_DB_PATH=os.path.join(home, "h.db"),
               FISI_SELFTEST=os.path.join(home, "s.log"))
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                          timeout=900, env=env)
    return done.returncode, done.stdout[-6000:] + done.stderr[-4000:]


class _App:
    def __init__(self):
        import fisi_core as fc
        self.db = fc.DBManager(os.path.join(tempfile.mkdtemp(), "t.db"))
        self.sync = None

    def toast(self, *_a, **_k):
        pass

    def start_review(self):
        pass


def _walk(control, found=None):
    found = [] if found is None else found
    found.append(control)
    for name in ("content", "controls"):
        child = getattr(control, name, None)
        for item in child if isinstance(child, list) else [child]:
            if item is not None and hasattr(item, "__dict__"):
                _walk(item, found)
    return found


@unittest.skipUnless(os.path.exists(os.path.join(SRC, "fisi_theme.py")),
                     "vorher python mobile/vorbereiten.py")
class HandyBautTest(unittest.TestCase):
    """Alle Handy-Seiten bauen bei 160 % und 200 % (main.selftest)."""

    def test_160(self):
        code, text = _selbsttest("extra_gross")
        self.assertEqual(code, 0, text)
        self.assertIn("FEHLER 0", text, text)
        self.assertIn("FAKTOR 1.6", text, text)      # wirklich bei 160 % gebaut

    def test_200(self):
        code, text = _selbsttest("riesig")
        self.assertEqual(code, 0, text)
        self.assertIn("FEHLER 0", text, text)
        self.assertIn("FAKTOR 2.0", text, text)


@unittest.skipUnless(os.path.exists(os.path.join(SRC, "fisi_theme.py")),
                     "vorher python mobile/vorbereiten.py")
class HandyAufbauTest(unittest.TestCase):
    """Ab 160 % untereinander und hoeher, bis 130 % wie bisher."""

    def setUp(self):
        self.main, self.ui = _handy()

    def tearDown(self):
        self.ui.set_font_factor(1.0)

    def _bei(self, faktor):
        self.ui.set_font_factor(faktor)

    def test_schwelle(self):
        ui = self.ui
        for faktor, gross in ((1.0, False), (1.15, False), (1.3, False), (1.6, True),
                              (2.0, True)):
            self._bei(faktor)
            self.assertEqual(ui.large(), gross, faktor)

    def test_banner(self):
        ft = self.main.ft
        for faktor in (1.0, 1.15, 1.3):
            self._bei(faktor)
            banner = self.ui.HeroPanel()
            self.assertIsInstance(banner.content, ft.Row, faktor)
            self.assertTrue(banner.content.controls[0].expand)
        for faktor in (1.6, 2.0):
            self._bei(faktor)
            banner = self.ui.HeroPanel()
            self.assertIsInstance(banner.content, ft.Column, faktor)
            texte, zahl = banner.content.controls
            self.assertIs(texte.controls[0], banner.title)
            self.assertIs(zahl.controls[0], banner.big)

    def _kachelzeilen(self, screen):
        ft = self.main.ft
        rings = (screen.ring_cards, screen.ring_quiz, screen.ring_ap1, screen.ring_scen)
        found = []
        for item in screen.root.controls:
            if isinstance(item, (ft.Row, ft.Column)) and any(
                    ring in _walk(item) for ring in rings):
                found.append(item)
        return found

    def test_ringkarten(self):
        ft = self.main.ft
        for faktor in (1.0, 1.3):
            self._bei(faktor)
            zeilen = self._kachelzeilen(self.main.DashboardScreen(_App()))
            self.assertEqual(len(zeilen), 2)
            for zeile in zeilen:
                self.assertIsInstance(zeile, ft.Row)
                self.assertTrue(zeile.intrinsic_height)
                self.assertTrue(all(card.expand for card in zeile.controls))
        for faktor in (1.6, 2.0):
            self._bei(faktor)
            screen = self.main.DashboardScreen(_App())
            zeilen = self._kachelzeilen(screen)
            self.assertEqual(len(zeilen), 2)
            for zeile in zeilen:
                self.assertIsInstance(zeile, ft.Column)
                self.assertEqual(len(zeile.controls), 2)
                self.assertTrue(all(card.expand is None for card in zeile.controls))
            # Ring so gross wie gewuenscht, die Karte ist jetzt breit genug
            self.assertEqual(screen.ring_cards.size, self.ui.grow(112))

    def test_kopfzeile(self):
        app = self.main.FISIMobileApp.__new__(self.main.FISIMobileApp)
        ft = self.main.ft
        app.crumb_main, app.crumb_sub = ft.Text("DASHBOARD"), ft.Text("HOME")
        app.lbl_version = ft.Text("Version")
        for faktor in (1.0, 1.15, 1.3):
            self._bei(faktor)
            self.assertIsNone(app._appbar(root=True).toolbar_height, faktor)
        for faktor in (1.6, 2.0):
            self._bei(faktor)
            self.assertEqual(app._appbar(root=True).toolbar_height,
                             self.ui.grow(56), faktor)
            self.assertEqual(app._appbar(root=False, crumbs=("A", "B")).toolbar_height,
                             self.ui.grow(56))

    def test_diagramme(self):
        for faktor in (1.0, 1.3):
            self._bei(faktor)
            self.assertEqual(self.ui.LineChart(height=200).canvas.height, 200)
            self.assertEqual(self.ui.ShareBars(height=180).canvas.height, 180)
        for faktor in (1.6, 2.0):
            self._bei(faktor)
            self.assertEqual(self.ui.LineChart(height=200).canvas.height,
                             self.ui.grow(200))
            self.assertEqual(self.ui.ShareBars(height=180).canvas.height,
                             self.ui.grow(180))

    def test_kacheln_fortschritt(self):
        ft = self.main.ft
        for faktor, art in ((1.3, ft.Row), (2.0, ft.Column)):
            self._bei(faktor)
            screen = self.main.ProgressScreen(_App())
            zeile = [item for item in screen.root.controls
                     if isinstance(item, (ft.Row, ft.Column))][0]
            self.assertIsInstance(zeile, art, faktor)
            self.assertEqual(len(zeile.controls), 2)


# Navigationsleiste (B-E-06)
FORTSCHRITT = "Fortschritt"
ZIEL_BREITE_384 = 384 / 6      # sechs Ziele nebeneinander
ZEICHEN_BREITE = 0.45          # mittlere Zeichenbreite je Schriftgroesse (Roboto)
# Kalibriert an Probefotos im Behelf (Flet-Web, 384 px, N9 navfoto): bei 12 px
# steht "Fortschritt" einzeilig (Schaetzung 59,4 dp), bei 14,3 px (Sehr gross
# ohne Grenze) bricht es um (Schaetzung 70,8 dp > 62)


@unittest.skipUnless(os.path.exists(os.path.join(SRC, "fisi_theme.py")),
                     "vorher python mobile/vorbereiten.py")
class NavigationsleisteTest(unittest.TestCase):

    def setUp(self):
        self.main, self.ui = _handy()

    def tearDown(self):
        self.ui.set_font_factor(1.0)

    def _leiste(self, faktor):
        main, ft = self.main, self.main.ft
        self.ui.set_font_factor(faktor)

        class Seite:
            views = []
            def __getattr__(self, _name):
                return None
        app = main.FISIMobileApp.__new__(main.FISIMobileApp)
        page = Seite()
        page.views = []
        app.page = page
        app.db = _App().db
        app.sync = None
        app._build_ui()
        return page.theme.navigation_bar_theme, app.nav

    def test_waechst_mit(self):
        for item in self.main.fisi_theme.FONT_SIZES:
            faktor = item["faktor"]
            thema, leiste = self._leiste(faktor)
            self.assertEqual(thema.height, self.ui.grow(80), faktor)
            for ziel in leiste.destinations:
                self.assertEqual(ziel.icon.size, self.ui.grow(24), faktor)
                self.assertEqual(ziel.selected_icon.size, self.ui.grow(24), faktor)
            groesse = thema.label_text_style.size
            self.assertEqual(groesse, min(12, self.ui.fs(11)), faktor)
            # "Fortschritt" passt einzeilig in ein Ziel (384 dp, 6 Ziele)
            self.assertLessEqual(len(FORTSCHRITT) * ZEICHEN_BREITE * groesse,
                                 ZIEL_BREITE_384 - 2, faktor)
        thema, _leiste = self._leiste(1.0)
        self.assertEqual(thema.height, 80)       # Normal wie Flutter-Standard
        self.assertEqual(thema.label_text_style.size, 11)


_WECHSEL_HANDY = r"""
import asyncio, json, os, sys
sys.path.insert(0, %r); os.chdir(%r)
import main, ui
th = main.fisi_theme

class Seite:
    def __init__(self):
        self.views, self.overlay = [], []
    def update(self, *a, **k):
        pass
    def run_task(self, fn, *args):
        asyncio.run(fn(*args))
    def __getattr__(self, _name):
        return None

app = main.FISIMobileApp.__new__(main.FISIMobileApp)
app.page = Seite()
app.db = main.DBManager()
app.sync = main.SyncController(app)
app.perf = main.MobilePerf(app)
app.screens = {}
app._recoloring = False
th.apply_font_size("normal"); ui.set_font_factor(1.0)
app._build_ui()
schritte = []
for ziel in (%r, "normal"):
    app.change_color(font_size=ziel)
    thema = app.page.theme.navigation_bar_theme
    schritte.append({"stufe": th.current_font_size, "faktor": ui.FONT_FACTOR[0],
                     "gespeichert": th.saved_font_size(), "tab": app.tab,
                     "leiste": thema.height, "abdeckung": len(app.page.overlay),
                     "gesperrt": bool(app._recoloring)})
print("ERG " + json.dumps(schritte))
"""


def _wechsel_handy(stufe):
    home = tempfile.mkdtemp(prefix="fisi_stufe_wechsel_")
    env = dict(os.environ, HOME=home, APPDATA=home, FISI_DB_PATH=os.path.join(home, "h.db"),
               FISI_SELFTEST=os.path.join(home, "s.log"))
    done = subprocess.run([sys.executable, "-c", _WECHSEL_HANDY % (SRC, SRC, stufe)],
                          capture_output=True, text=True, timeout=900, env=env)
    lines = [line for line in done.stdout.splitlines() if line.startswith("ERG ")]
    return (json.loads(lines[-1][4:]) if lines else
            "kein Ergebnis:\n%s\n%s" % (done.stdout[-2000:], done.stderr[-4000:]))


@unittest.skipUnless(os.path.exists(os.path.join(SRC, "fisi_theme.py")),
                     "vorher python mobile/vorbereiten.py")
class HandyWechselTest(unittest.TestCase):

    def test_normal_200_normal(self):
        """A-N9-11: Optionen Normal -> 200 % -> Normal (change_color mit
        font_size): ohne Fehler, gespeichert, Seite bleibt Optionen, Leiste
        waechst und schrumpft wieder, Abdeckung weg."""
        erg = _wechsel_handy("riesig")
        self.assertIsInstance(erg, list, erg)
        self.assertEqual([(w["stufe"], w["faktor"], w["gespeichert"]) for w in erg],
                         [("riesig", 2.0, "riesig"), ("normal", 1.0, "normal")])
        self.assertEqual([w["leiste"] for w in erg], [160, 80])
        for schritt in erg:
            self.assertEqual(schritt["tab"], "settings", schritt)
            self.assertEqual(schritt["abdeckung"], 0, schritt)
            self.assertFalse(schritt["gesperrt"], schritt)


# ---------------------------------------------------------------------------
#  PC (Anzeige noetig)
# ---------------------------------------------------------------------------

def _tk_ok():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:  # noqa: BLE001
        return False


HAS_DISPLAY = False if "--fall" in sys.argv else _tk_ok()

PC_ANSICHTEN = ["dashboard", "cards", "quiz", "ap1scenarios", "scenarios", "testproject",
                "abschluss", "notebook", "calc", "game", "progress", "help", "settings",
                "search"]
PC_SPIEL = ["buero", "kunde", "zuhause", "firma", "reise"]
BEDIEN = ("NeoButton", "EntryBox", "CTkEntry", "CTkOptionMenu", "CTkCheckBox", "CTkTextbox",
          "CTkSwitch", "IconButton", "CTkSegmentedButton")


def _firma(path):
    """Spielfigur mit Firma und Mitarbeiter (wie test_reiter_sichtbar)."""
    import fisi_core
    import fisi_game as fg
    db = fisi_core.DBManager(path)
    game = fg.Game(db, "PC")
    game.set_profile("Test", {})
    goal = game.content["balancing"]["gruendung"]
    for number, task in enumerate(game.content["aufgaben"]):
        data = {"aufgabe": task["id"], "tag": number + 1, "richtig": True, "geld": 0,
                "reputation": {}}
        if number == 0:
            data["geld"] = goal["startkapital"] + 10000
            data["reputation"] = {key: 90 for key in fg.AXIS_KEYS}
        db.log_game_event(fg.EV_SOLVED, json.dumps(data), "PC")
        db.log_game_event(fg.EV_DAY_END, json.dumps({"tag": number + 1, "gehalt": 0}), "PC")
    game.reload()
    game.found_firm("Test IT-Service")
    game.hire(fg.applicants(game.state, game.content)[0]["id"])


def worker(stufe, breite, hoehe, wechsel=False):
    """Im eigenen Prozess: alle Ansichten bei dieser Stufe; "ERG {...}".
    wechsel=True: Start bei Normal, in den Optionen (Optik offen) auf diese
    Stufe und zurueck auf Normal wechseln (A-N9-10/11)."""
    home = tempfile.mkdtemp(prefix="fisi_stufe_pc_")
    os.environ.update(HOME=home, APPDATA=home, FISI_DB_PATH=os.path.join(home, "t.db"),
                      FISI_SELFTEST=os.path.join(home, "log.txt"))
    _firma(os.environ["FISI_DB_PATH"])
    import customtkinter as ctk
    import app_gui
    import fisi_theme
    import fisi_widgets
    import fisi_hilfe
    fisi_hilfe.mark_tour_seen()
    fisi_theme.apply_font_size("normal" if wechsel else stufe)
    fisi_widgets.apply_ui_scale(fisi_theme.font_factor())
    app_gui.UpdateController.auto_check = lambda self: None
    app_gui.SyncController.auto_start = lambda self: None
    meldungen, ausnahmen = [], []
    app_gui.messagebox.showerror = lambda *a, **k: meldungen.append(a)
    root = ctk.CTk()
    root.report_callback_exception = lambda *exc: ausnahmen.append(repr(exc[1]))
    root.geometry("%dx%d+0+0" % (breite, hoehe))
    app = app_gui.FISIApp(root)

    def pump(seconds):
        end = time.time() + seconds
        while time.time() < end:
            root.update()
            time.sleep(0.01)

    def walk(widget):
        yield widget
        for child in widget.winfo_children():
            yield from walk(child)

    def bedien(widget):
        return any(k.__name__ in BEDIEN for k in type(widget).__mro__)

    def rollbereich(widget):
        parent = widget.master
        while parent is not None:
            if isinstance(parent, fisi_widgets.ScrollArea):
                return parent
            parent = getattr(parent, "master", None)
        return None

    def pruefe(key):
        funde = []
        rx, ry = root.winfo_rootx(), root.winfo_rooty()
        rw, rh = root.winfo_width(), root.winfo_height()
        anzahl = 0
        for wurzel in (app.sidebar, app.header, app.views[key]):
            for w in walk(wurzel):
                if not w.winfo_ismapped() or not bedien(w) or bedien(w.master):
                    continue
                anzahl += 1
                ww, wh = w.winfo_width(), w.winfo_height()
                bereich = rollbereich(w)
                if bereich is None:
                    x, y = w.winfo_rootx() - rx, w.winfo_rooty() - ry
                    if x < -1 or y < -1 or x + ww > rw + 1 or y + wh > rh + 1 or ww < 4:
                        funde.append("%s: %s ausserhalb des Fensters (%d,%d %dx%d)"
                                     % (key, type(w).__name__, x, y, ww, wh))
                    continue
                ix = w.winfo_rootx() - bereich.inner.winfo_rootx()
                iy = w.winfo_rooty() - bereich.inner.winfo_rooty()
                region = [float(v) for v in str(bereich.canvas.cget("scrollregion")).split()]
                x1 = max(region[2] if len(region) == 4 else 0, bereich.canvas.winfo_width())
                y1 = max(region[3] if len(region) == 4 else 0, bereich.canvas.winfo_height())
                if ix + ww > x1 + 1 or iy + wh > y1 + 1:
                    funde.append("%s: %s im Bildlauf nicht erreichbar" % (key, type(w).__name__))
        # Ist der Inhalt breiter als sichtbar, rollt der Bereich ganz nach rechts
        view = app.views[key]
        if view.inner.winfo_reqwidth() > view.canvas.winfo_width() + 1:
            view.canvas.xview_moveto(1.0)
            pump(0.2)
            if view.canvas.xview()[1] < 0.999:
                funde.append("%s: rollt nicht bis zum rechten Rand" % key)
            view.canvas.xview_moveto(0.0)
        # Suchfeld sichtbar und nicht zusammengedrueckt
        kopf = app.header.search_box
        if kopf.winfo_width() < 0.8 * kopf.winfo_reqwidth() and not app.header.stacked:
            funde.append("%s: Suchfeld zusammengedrueckt" % key)
        return anzahl, funde

    pump(1.0)
    root.geometry("%dx%d+0+0" % (breite, hoehe))
    pump(0.8)
    ergebnis = {"ansichten": {}, "fehler": []}
    if wechsel:
        import fisi_optionen as fo
        ergebnis["wechsel"] = []
        try:
            app.show_view("settings")
            pump(0.6)
            app.views["settings"].open_area(fo.OPTIK_ID)
            pump(0.6)
            for ziel in (stufe, "normal"):
                app.change_font_size(ziel)
                pump(1.2)
                view = app.views["settings"]
                fold = view.folds[fo.OPTIK_ID]
                knoepfe = list(view.font_choice.buttons.values())
                ergebnis["wechsel"].append({
                    "stufe": fisi_theme.current_font_size,
                    "faktor": fisi_theme.font_factor(),
                    "ansicht": app.current, "optik_offen": bool(fold.opened),
                    "auswahl": view.font_choice.value,
                    "auswahl_breite": view.font_choice.winfo_width(),
                    "knoepfe": len(knoepfe),
                    "knoepfe_sichtbar": sum(1 for w in knoepfe if w.winfo_ismapped()),
                    "zeitgeber": len(app_gui._orphaned_timers(root)),
                    "funde": pruefe("settings")[1]})
        except Exception as error:  # noqa: BLE001
            import traceback
            ergebnis["fehler"].append("Wechsel: Ausnahme %r\n%s" % (error,
                                                                 traceback.format_exc()))
        ergebnis["fehler"].extend("Fehlermeldung: %r" % (m,) for m in meldungen)
        ergebnis["fehler"].extend("Ausnahme im Ereignis: %s" % a for a in ausnahmen)
        print("ERG " + json.dumps(ergebnis, ensure_ascii=False))
        sys.stdout.flush()
        os._exit(0)
    for key in PC_ANSICHTEN + ["SPIEL"] + PC_SPIEL:
        try:
            if key == "SPIEL":
                app.show_view("game")
                pump(0.6)
                view = app.views["game"]
                view._choose(view.game.run)
                pump(0.6)
                continue
            app.show_view(key)
            pump(0.8)
            app.views[key].to_top()
            pump(0.4)
            anzahl, funde = pruefe(key)
            ergebnis["ansichten"][key] = {"bedienelemente": anzahl,
                                          "kopf_untereinander": app.header.stacked}
            ergebnis["fehler"].extend(funde)
        except Exception as error:  # noqa: BLE001
            import traceback
            ergebnis["fehler"].append("%s: Ausnahme %r\n%s" % (key, error,
                                                             traceback.format_exc()))
    ergebnis["fehler"].extend("Fehlermeldung: %r" % (m,) for m in meldungen)
    ergebnis["fehler"].extend("Ausnahme im Ereignis: %s" % a for a in ausnahmen)
    print("ERG " + json.dumps(ergebnis, ensure_ascii=False))
    sys.stdout.flush()
    os._exit(0)


_ERG = {}


def pc_ergebnis(stufe, breite=1120, hoehe=720, wechsel=False):
    key = (stufe, breite, hoehe, wechsel)
    if key not in _ERG:
        done = subprocess.run([sys.executable, os.path.abspath(__file__), "--fall", stufe,
                               str(breite), str(hoehe)] + (["--wechsel"] if wechsel else []),
                              capture_output=True, text=True,
                              timeout=1200, cwd=HERE)
        lines = [line for line in done.stdout.splitlines() if line.startswith("ERG ")]
        _ERG[key] = (json.loads(lines[-1][4:]) if lines else
                     "kein Ergebnis:\n%s\n%s" % (done.stdout[-2000:], done.stderr[-4000:]))
    return _ERG[key]


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (mit xvfb-run starten)")
class PcStufenTest(unittest.TestCase):

    def _pruefe(self, stufe):
        erg = pc_ergebnis(stufe)
        self.assertIsInstance(erg, dict, erg)
        self.assertEqual(erg["fehler"], [], stufe)
        self.assertEqual(sorted(erg["ansichten"]), sorted(PC_ANSICHTEN + PC_SPIEL))
        return erg

    def test_160(self):
        self._pruefe("extra_gross")

    def test_200(self):
        erg = self._pruefe("riesig")
        # 200 % in 1120 px: in der Firma (mit "Platz wechseln") steht das
        # Suchfeld unter den Brotkrumen, auf dem Dashboard passt beides nicht
        # nebeneinander (gemessen 1332 bzw. etwa 1100 px Bedarf bei 632 px)
        self.assertTrue(erg["ansichten"]["firma"]["kopf_untereinander"])

    def test_sehr_gross_kopfzeile_wie_bisher(self):
        erg = pc_ergebnis("sehr_gross")
        self.assertIsInstance(erg, dict, erg)
        self.assertFalse(any(v["kopf_untereinander"] for v in erg["ansichten"].values()),
                         erg["ansichten"])

    def test_wechsel_normal_200_normal(self):
        """A-N9-10/11: Optionen offen, Normal -> 200 % -> Normal in 1120 x 720:
        ohne Fehler, Optik bleibt offen, keine verwaisten Zeitgeber, die
        Auswahlreihe der Stufen (5 Eintraege) ist ganz erreichbar."""
        erg = pc_ergebnis("riesig", wechsel=True)
        self.assertIsInstance(erg, dict, erg)
        self.assertEqual(erg["fehler"], [])
        self.assertEqual([(w["stufe"], w["faktor"]) for w in erg["wechsel"]],
                         [("riesig", 2.0), ("normal", 1.0)])
        for schritt in erg["wechsel"]:
            self.assertEqual(schritt["ansicht"], "settings", schritt)
            self.assertTrue(schritt["optik_offen"], schritt)
            self.assertEqual(schritt["auswahl"], schritt["stufe"], schritt)
            self.assertEqual(schritt["knoepfe"], 5, schritt)
            self.assertEqual(schritt["knoepfe_sichtbar"], 5, schritt)
            self.assertEqual(schritt["zeitgeber"], 0, schritt)
            self.assertEqual(schritt["funde"], [], schritt)


if __name__ == "__main__":
    if "--fall" in sys.argv:
        index = sys.argv.index("--fall")
        worker(sys.argv[index + 1], int(sys.argv[index + 2]), int(sys.argv[index + 3]),
               "--wechsel" in sys.argv)
    unittest.main()
