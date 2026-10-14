#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests 0.63.2 N8: Tastatur, Namen der Symbolknoepfe, Startknoepfe, zweite
Pruefung, Auslassungspunkte und "z. B." (PC und Handy).

Plan-Nachtrag 0.63.2 Nr. 22 (B-J-05), 23 (B-J-N3), 24 (B-D-14), 44 (N-c);
Testplan N8 Abschnitte 4-7.

B-J-05  K20 Tab erreicht die fuenf Fachbereich-Kacheln des Dashboards in
        der Reihenfolge der Fachbereiche, jede genau einmal (Umschalt+Tab
        umgekehrt); K21 Eingabe-, Ziffernblock-Eingabe- und Leertaste wie ein
        Klick (Zoom auf/zu); K22 Fokusrahmen um die Kachel; K23 Maus wie bisher.
B-J-N3  K30 jeder IconButton-Aufruf (AST) und jede IconButton-Instanz hat
        einen Namen; K31 Name als Tooltip (Maus, nach Verzoegerung) und beim
        Tab-Fokus, weg beim Verlassen/Ansichtswechsel/Farbwechsel, kein
        verwaister Zeitgeber; K32 die vier Startknoepfe "<Kurzname> starten",
        verschieden, starten die richtige Pruefung (PC = Handy).
B-D-14  K40 laufende Pruefung wird bei start() gezeigt, nie ueberschrieben;
        K41 auch wenn sie waehrend der Rueckfrage entsteht; K42 ohne laufende
        Pruefung wie bisher; K43 Phase "bewerten" zaehlt als laufend
        (PC und Handy). F23 (a): keine neue Meldung.
N-c     K50 die fuenf Texte mit "…" statt "...", sonst zeichengleich; K51 PC-
        und Handy-Text "weitere Treffer" gleich; K52 feste Liste der
        "z.B."-Zeichenketten, die bleiben (nicht sichtbar oder gemeldet).

Start:  xvfb-run -a python test_anzeige_tastatur_0632.py
"""

import ast
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_HOME = tempfile.mkdtemp(prefix="fisi_n8_")
os.environ.update(HOME=_HOME, APPDATA=_HOME, FISI_DB_PATH=os.path.join(_HOME, "n8.db"),
                  FISI_SELFTEST=os.path.join(_HOME, "log.txt"))


def _source(rel):
    with open(os.path.join(HERE, rel), encoding="utf-8") as handle:
        return handle.read()


def _strings(rel):
    """Alle Zeichenketten (AST) einer Datei."""
    return [node.value for node in ast.walk(ast.parse(_source(rel)))
            if isinstance(node, ast.Constant) and isinstance(node.value, str)]


def _assign(rel, name):
    for node in ast.walk(ast.parse(_source(rel))):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
                if isinstance(target, ast.Tuple) and any(
                        isinstance(t, ast.Name) and t.id == name for t in target.elts):
                    values = ast.literal_eval(node.value)
                    return values[[t.id for t in target.elts].index(name)]
    raise AssertionError("%s nicht in %s" % (name, rel))


# ============================================================================
#  ohne Anzeige
# ============================================================================

class IconButtonNamenAstTest(unittest.TestCase):
    """K30 (Quelltext): kein IconButton(...) ohne Namen."""

    DATEIEN = ("app_gui.py", "fisi_widgets.py", "fisi_game_gui.py")

    def test_jeder_aufruf_hat_namen(self):
        aufrufe = 0
        for rel in self.DATEIEN:
            for node in ast.walk(ast.parse(_source(rel))):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = func.id if isinstance(func, ast.Name) else (
                    func.attr if isinstance(func, ast.Attribute) else None)
                if name != "IconButton":
                    continue
                aufrufe += 1
                keywords = {kw.arg: kw.value for kw in node.keywords}
                self.assertIn("name", keywords, "%s:%d ohne Namen" % (rel, node.lineno))
                value = keywords["name"]
                if isinstance(value, ast.Constant):
                    text = value.value
                else:
                    self.assertIsInstance(value, ast.Name, "%s:%d" % (rel, node.lineno))
                    text = _assign(rel, value.id)
                self.assertTrue(isinstance(text, str) and text.strip(),
                                "%s:%d leerer Name" % (rel, node.lineno))
        # 6 in app_gui (Zahlenfeld 2, Blaettern 2 x 2), 2 im Kalender
        self.assertEqual(aufrufe, 8)

    def test_namen_wie_am_handy(self):
        self.assertEqual(_assign("app_gui.py", "PAGE_PREV"),
                         _assign("mobile/src/main.py", "PAGE_PREV"))
        self.assertEqual(_assign("app_gui.py", "PAGE_NEXT"),
                         _assign("mobile/src/main.py", "PAGE_NEXT"))
        ui = _strings("mobile/src/ui.py")
        for name in ("MONTH_PREV", "MONTH_NEXT"):
            self.assertIn(_assign("fisi_widgets.py", name), ui)
        for name in ("STEP_LESS", "STEP_MORE"):
            self.assertIn(_assign("app_gui.py", name), ui)


class StartTexteTest(unittest.TestCase):
    """K32 (Text): "<Kurzname> starten", PC = Handy, paarweise verschieden."""

    def test_texte(self):
        import fisi_pruefung as fp
        pc = _assign("app_gui.py", "EXAM_START_TEXT")
        self.assertEqual(pc, "%s starten")
        self.assertEqual(_assign("mobile/src/main.py", "EXAM_START_TEXT"), pc)
        texte = [pc % exam["kurz"] for exam in fp.EXAMS]
        self.assertEqual(texte, ["AP1 starten", "Konzeption starten", "Netzwerke starten",
                                 "WiSo starten"])
        self.assertEqual(len(set(texte)), 4)
        self.assertNotIn("Starten", _strings("app_gui.py"))
        self.assertNotIn("Starten", _strings("mobile/src/main.py"))


class NcTexteTest(unittest.TestCase):
    """K50/K51/K52 (N-c)."""

    PC = ("Suchen …  (Strg+F)", "… weitere %d Treffer nicht angezeigt.",
          "Update wird heruntergeladen … %s von %s MB")
    HANDY = ("Deine Lösung …", "… weitere %d Treffer nicht angezeigt.")

    def test_k50_texte(self):
        pc, handy = _strings("app_gui.py"), _strings("mobile/src/main.py")
        for text in self.PC:
            self.assertIn(text, pc)
            self.assertNotIn(text.replace("…", "..."), pc)
        for text in self.HANDY:
            self.assertIn(text, handy)
            self.assertNotIn(text.replace("…", "..."), handy)
        # bewusst nicht geaendert (Plan Nr. 44): Beispiel eines Schluessel-Anfangs
        self.assertIn("github_pat_...", handy)

    def test_k51_weitere_treffer_gleich(self):
        pc = [s for s in _strings("app_gui.py") if "weitere %d Treffer" in s]
        handy = [s for s in _strings("mobile/src/main.py") if "weitere %d Treffer" in s]
        self.assertEqual(len(pc), 1)
        self.assertEqual(pc, handy)

    # Zeichenketten mit "z.B.", die bleiben (Datei, Anfang des Texts, Grund).
    # Alle anderen sichtbaren Programmtexte haben "z. B." (Testplan K52).
    BLEIBEN = [
        ("build.py", "Ungueltige Version %s", "Konsole beim Bauen (Plan Nr. 44)"),
        ("build.py", "Ungueltige Version %s", "Konsole beim Bauen (Plan Nr. 44)"),
        ("build.py", "Bitte die neue Version", "Konsole beim Bauen (Plan Nr. 44)"),
        ("fisi_pruefung.py", "z.B.", "Abkuerzungserkennung FG-87, kein Anzeigetext"),
        ("fisi_core.py", "RECHENWEG BILDSCHIRM-DATENVOLUMEN\nAm Beispiel 1920",
         "N8-F7: Handy-Zeile wuerde 27 > 26 Zeichen - gemeldet, PC und Handy gleich"),
        ("fisi_core.py", "RECHENWEG\nBILDSCHIRM-DATENVOLUMEN",
         "N8-F7: Zeile ' (z. B. 8 Bit = 256 Farben,' 27 > 26 - gemeldet"),
        ("fisi_lernen.py", "Teile das Netz %s nach VLSM",
         "Bestandstest test_rechenweg TrainerTest.test_9_pc_text - gemeldet"),
    ]
    GEAENDERT = [
        ("fisi_core.py", "RECHENWEG SUBNETTING\nAm Beispiel 192"),
        ("fisi_core.py", "RECHENWEG SUBNETTING\nAm Beispiel\n"),
        ("fisi_projekt.py", "Anforderungen, Alternativen"),
        ("fisi_sync.py", "Das Repository bitte"),
    ]

    @staticmethod
    def _zb():
        dateien = subprocess.run(["git", "-C", HERE, "ls-files", "*.py"], capture_output=True,
                                 text=True).stdout.split()
        funde = []
        for rel in sorted(dateien):
            if os.path.basename(rel).startswith("test_"):
                continue
            tree = ast.parse(_source(rel))
            docs = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                                     ast.ClassDef)) and node.body and \
                        isinstance(node.body[0], ast.Expr) and \
                        isinstance(node.body[0].value, ast.Constant):
                    docs.add(id(node.body[0].value))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and \
                        id(node) not in docs:
                    funde.append((rel, node.value))
        return funde

    def test_k52_feste_liste(self):
        if not os.path.isdir(os.path.join(HERE, ".git")) and \
                not os.path.isfile(os.path.join(HERE, ".git")):
            self.skipTest("kein git-Stand")
        funde = self._zb()
        mit_alt = [(rel, text) for rel, text in funde if "z.B." in text]
        rest = list(mit_alt)
        for rel, anfang, _grund in self.BLEIBEN:
            treffer = [f for f in rest if f[0] == rel and f[1].startswith(anfang)]
            self.assertTrue(treffer, (rel, anfang))
            rest.remove(treffer[0])
        self.assertEqual(rest, [], "weitere Zeichenketten mit 'z.B.'")
        for rel, anfang in self.GEAENDERT:
            treffer = [text for r, text in funde if r == rel and text.startswith(anfang)]
            self.assertEqual(len(treffer), 1, (rel, anfang))
            self.assertIn("z. B.", treffer[0])
            self.assertNotIn("z.B.", treffer[0])


# ============================================================================
#  Handy (Flet-Modell, ohne Flutter)
# ============================================================================

def _flet_ok():
    try:
        import flet  # noqa: F401
        return True
    except ImportError:
        return False


class FakePage:
    def __init__(self):
        self.views, self.overlay, self.tasks = [], [], []

    def run_task(self, handler, *args, **kwargs):
        self.tasks.append(handler)

    def show_dialog(self, dialog):
        dialog.open = True

    def __getattr__(self, _name):
        return lambda *args, **kwargs: None


@unittest.skipUnless(_flet_ok(), "flet fehlt")
class HandyPruefungTest(unittest.TestCase):
    """B-D-14 am Handy (K40-K43) und Startknoepfe (K32)."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(1, os.path.join(HERE, "mobile", "src"))
        import main
        import fisi_pruefung as fp
        cls.main, cls.fp = main, fp
        cls.app = main.FISIMobileApp(FakePage())
        cls.panel = cls.app.screens["quiz"].exam

    def setUp(self):
        self.fp.clear_running()
        self.addCleanup(self.fp.clear_running)
        self.gezeigt = []
        for name in ("show_running", "show_grading", "show_choice"):
            patch = mock.patch.object(self.panel, name,
                                      lambda n=name: self.gezeigt.append(n))
            patch.start()
            self.addCleanup(patch.stop)
        self.fragen = []

    def confirm(self, entsteht=None):
        def confirm(title, message, on_yes):
            self.fragen.append(message)
            if entsteht:
                self.fp.save_running(entsteht)
            on_yes()
        return mock.patch.object(self.app, "confirm", confirm)

    def laufend(self, art, phase="laeuft"):
        state = self.fp.new_exam(art, [], seed=7)
        state["phase"] = phase
        self.fp.save_running(state)
        return json.dumps(self.fp.load_running(), sort_keys=True)

    def test_k40_laufende_bleibt(self):
        vorher = self.laufend(self.fp.AP1)
        with self.confirm():
            self.panel.start(self.fp.WISO)
        self.assertEqual(json.dumps(self.fp.load_running(), sort_keys=True), vorher)
        self.assertEqual(self.gezeigt, ["show_running"])
        self.assertEqual(self.fragen, [], "keine Rueckfrage, keine neue Meldung")

    def test_k41_entsteht_waehrend_der_rueckfrage(self):
        andere = self.fp.new_exam(self.fp.NETZWERKE, [], seed=3)
        with self.confirm(entsteht=andere):
            self.panel.start(self.fp.WISO)
        self.assertEqual(self.fp.load_running()["art"], self.fp.NETZWERKE)
        self.assertEqual(self.gezeigt, ["show_running"])

    def test_k42_ohne_laufende_wie_bisher(self):
        with self.confirm():
            self.panel.start(self.fp.WISO)
        state = self.fp.load_running()
        self.assertEqual((state["art"], state["phase"]), (self.fp.WISO, "laeuft"))
        self.assertEqual(self.gezeigt, ["show_running"])
        self.assertEqual(len(self.fragen), 1)

    def test_k43_bewerten_zaehlt_als_laufend(self):
        vorher = self.laufend(self.fp.KONZEPTION, phase="bewerten")
        with self.confirm():
            self.panel.start(self.fp.AP1)
        self.assertEqual(json.dumps(self.fp.load_running(), sort_keys=True), vorher)
        self.assertEqual(self.gezeigt, ["show_grading"])

    def test_k32_startknoepfe(self):
        import flet as ft
        mock.patch.stopall()
        self.panel.show_choice()
        texte = []

        def walk(control):
            if isinstance(control, self.main.ui.GradientButton):
                texte.append(control)
            for name in ("controls", "content"):
                child = getattr(control, name, None)
                for item in (child if isinstance(child, list) else [child]):
                    if isinstance(item, ft.Control):
                        walk(item)
        for control in self.panel.controls:
            walk(control)
        beschriftungen = [b.caption.value for b in texte]
        beschriftungen = [t for t in beschriftungen if t and t.endswith(" starten")]
        self.assertEqual(beschriftungen, ["AP1 starten", "Konzeption starten",
                                          "Netzwerke starten", "WiSo starten"])


# ============================================================================
#  PC (mit Anzeige)
# ============================================================================

def _tk_ok():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:  # noqa: BLE001
        return False


HAS_DISPLAY = _tk_ok()
_PC = {}


def _pc():
    if "app" not in _PC:
        import customtkinter as ctk
        import app_gui
        import fisi_theme
        import fisi_widgets
        if hasattr(app_gui, "apply_appearance"):
            app_gui.apply_appearance()
        fisi_theme.apply_font_size("normal")
        fisi_widgets.apply_ui_scale(1.0)
        app_gui.UpdateController.auto_check = lambda self: None
        app_gui.SyncController.auto_start = lambda self: None
        root = ctk.CTk()
        root.geometry("1360x900+0+0")
        app = app_gui.FISIApp(root)
        _PC.update(app=app, root=root, app_gui=app_gui, widgets=fisi_widgets,
                   theme=fisi_theme)
    return _PC


def pump(seconds=0.3):
    root = _PC["root"]
    end = time.time() + seconds
    while time.time() < end:
        root.update()
        time.sleep(0.01)


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class PcBasis(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pc = _pc()
        cls.app, cls.root, cls.gui, cls.fw = pc["app"], pc["root"], pc["app_gui"], pc["widgets"]
        pump(1.0)


class KachelTastaturTest(PcBasis):
    """B-J-05 (K20-K23)."""

    def kacheln(self):
        view = self.app.views["dashboard"]
        spalten = []
        for category in self.gui.CATEGORIES:
            ring = view.fach_rings[category][0]
            spalten.append(ring.master)
        return view, spalten

    def setUp(self):
        self.app.show_view("dashboard")
        pump(0.8)
        view = self.app.views["dashboard"]
        if view.zoom_category:
            view._toggle_zoom(view.zoom_category)
            pump(0.3)

    def test_k20_tab_reihenfolge(self):
        view, spalten = self.kacheln()
        pfade = [str(s) for s in spalten]
        start = spalten[0]
        # rueckwaerts bis vor die erste Kachel, dann vorwaerts zaehlen
        vorher = self.fw.next_focus(start, forward=False)
        self.assertIsNotNone(vorher)
        kette, aktuell = [], self.root.nametowidget(vorher)
        for _ in range(12):
            naechster = self.fw.next_focus(aktuell, forward=True)
            if naechster is None:
                break
            kette.append(naechster)
            aktuell = self.root.nametowidget(naechster)
        treffer = [p for p in kette if p in pfade]
        self.assertEqual(treffer[:5], pfade, kette)
        self.assertEqual(kette[:5], pfade, "die Kacheln folgen direkt aufeinander")
        # Umschalt+Tab umgekehrt
        rueck, aktuell = [], spalten[-1]
        for _ in range(4):
            aktuell = self.root.nametowidget(self.fw.next_focus(aktuell, forward=False))
            rueck.append(str(aktuell))
        self.assertEqual(rueck, list(reversed(pfade[:-1])))

    def test_k21_tasten_wie_klick(self):
        view, spalten = self.kacheln()
        for category, spalte in zip(self.gui.CATEGORIES, spalten):
            for taste in ("<Return>", "<KP_Enter>", "<space>"):
                self.fw.focus_widget(spalte)
                pump(0.1)
                spalte.event_generate(taste)
                pump(0.3)
                self.assertEqual(view.zoom_category, category, (category, taste))
                self.assertIsNotNone(view.zoom_card)
                self.assertTrue(view.zoom_card.winfo_ismapped())
                spalte = self.kacheln()[1][self.gui.CATEGORIES.index(category)]
                self.fw.focus_widget(spalte)
                spalte.event_generate(taste)
                pump(0.3)
                self.assertIsNone(view.zoom_category, (category, taste, "zu"))
                spalte = self.kacheln()[1][self.gui.CATEGORIES.index(category)]

    def test_k22_fokusrahmen(self):
        _view, spalten = self.kacheln()
        spalte = spalten[2]
        self.fw.focus_widget(spalte)
        pump(0.5)
        ring = self.fw.focus_ring(self.root)
        self.assertIsNotNone(ring)
        self.assertIs(ring.widget, spalte)
        self.assertTrue(self.fw.keyboard_mode())

    def test_k23_maus_wie_bisher(self):
        view, spalten = self.kacheln()
        # CTkLabel: die Bindung sitzt am inneren Tk-Label (wie ein echter Klick)
        name = view.fach_rings[self.gui.CATEGORIES[1]][2]
        name._label.event_generate("<Button-1>")
        pump(0.3)
        self.assertEqual(view.zoom_category, self.gui.CATEGORIES[1])
        name = self.kacheln()[0].fach_rings[self.gui.CATEGORIES[1]][2]
        name._label.event_generate("<Button-1>")
        pump(0.3)
        self.assertIsNone(view.zoom_category)


class SymbolNamenTest(PcBasis):
    """B-J-N3 (K30 Laufzeit, K31)."""

    def iconbuttons(self):
        gefunden, stapel = [], [self.root]
        while stapel:
            widget = stapel.pop()
            if isinstance(widget, self.fw.IconButton):
                gefunden.append(widget)
            stapel.extend(widget.winfo_children())
        return gefunden

    def test_k30_alle_instanzen(self):
        gesehen = set()
        for key in ("dashboard", "ap1scenarios", "scenarios", "testproject", "notebook",
                    "progress"):
            self.app.show_view(key)
            pump(0.8)
            for button in self.iconbuttons():
                self.assertTrue(button.name.strip(), "%s ohne Namen" % button)
                gesehen.add(button.name)
        for name in ("Vorherige Seite", "Nächste Seite", "Vorheriger Monat",
                     "Nächster Monat"):
            self.assertIn(name, gesehen)

    def offene_schilder(self):
        return [w for w in self.root.winfo_children()
                if isinstance(w, self.fw.tk.Toplevel) and w.wm_overrideredirect()]

    def test_k31_tooltip_maus_und_fokus(self):
        self.app.show_view("testproject")
        pump(0.8)
        knopf = self.app.views["testproject"].paged.btn_next
        tip = knopf.tooltip
        # Ausgangslage: Mauszeiger weg vom Knopf, Fokus nicht auf dem Knopf,
        # kein Schild (ein echtes Enter des Zeigers unter Xvfb ausschliessen)
        self.root.event_generate("<Motion>", warp=True, x=1, y=1)
        self.root.focus_force()
        pump(0.3)
        tip.hide()
        self.assertIsNone(tip.window)
        # Zeitpunkt jedes Zeigens merken: die Verzoegerung wird an der Uhr
        # geprueft, nicht an festen Wartezeiten (Rechner unter Last)
        gezeigt = []
        echt = tip.show

        def zeigen():
            gezeigt.append(time.time())
            echt()
        tip.show = zeigen
        # Maus: nach der Verzoegerung, weg beim Verlassen
        start = time.time()
        knopf.event_generate("<Enter>")
        self.assertIsNone(tip.window, "nicht sofort")
        self.assertIsNotNone(tip._job)
        pump(self.fw.Tooltip.DELAY / 1000.0 + 0.3)
        self.assertIsNotNone(tip.window)
        self.assertEqual(len(gezeigt), 1)
        self.assertGreaterEqual(gezeigt[0] - start, self.fw.Tooltip.DELAY / 1000.0 - 0.02,
                                "nicht vor der Verzoegerung")
        texte = [w.cget("text") for w in tip.window.winfo_children()]
        self.assertEqual(texte, ["Nächste Seite"])
        knopf.event_generate("<Leave>")
        pump(0.2)
        self.assertIsNone(tip.window)
        # Verlassen vor der Verzoegerung: kein Schild, kein Zeitgeber
        knopf.event_generate("<Enter>")
        self.assertIsNotNone(tip._job)
        knopf.event_generate("<Leave>")
        self.assertIsNone(tip._job)
        pump(self.fw.Tooltip.DELAY / 1000.0 + 0.3)
        self.assertIsNone(tip.window)
        self.assertEqual(len(gezeigt), 1)
        tip.show = echt
        # Tab-Fokus: sofort, weg beim Fokusverlust
        # (den Knopf vorher aus dem Bild scrollen: focus_widget scrollt ihn
        # hinein, das Schild steht danach direkt unter dem Knopf)
        view = self.app.views["testproject"]
        view.canvas.yview_moveto(0.0)
        pump(0.3)
        self.fw.focus_widget(knopf)
        pump(0.3)
        self.assertIsNotNone(tip.window)
        tip.window.update_idletasks()
        abstand = tip.window.winfo_rooty() - (knopf.winfo_rooty() + knopf.winfo_height())
        self.assertTrue(0 <= abstand <= self.gui.px(20), ("Schild nicht am Knopf", abstand))
        self.assertLessEqual(abs(tip.window.winfo_rootx() - knopf.winfo_rootx()), 1)
        self.fw.focus_widget(self.app.views["testproject"].paged.btn_prev
                             if self.app.views["testproject"].paged.page else
                             self.app.views["testproject"].paged.rows[0]["frame"])
        pump(0.3)
        self.assertIsNone(tip.window)
        # Ansichtswechsel mit offenem Schild
        knopf.event_generate("<Enter>")
        pump(self.fw.Tooltip.DELAY / 1000.0 + 0.3)
        self.assertIsNotNone(tip.window)
        self.app.show_view("dashboard")
        pump(0.5)
        self.assertIsNone(tip.window)
        self.assertEqual(self.offene_schilder(), [])

    def test_k31_farbwechsel_ohne_reste(self):
        self.app.show_view("testproject")
        pump(0.8)
        knopf = self.app.views["testproject"].paged.btn_next
        knopf.event_generate("<Enter>")
        pump(self.fw.Tooltip.DELAY / 1000.0 + 0.3)
        self.assertIsNotNone(knopf.tooltip.window)
        modus = _PC["theme"].MODE_LIGHT
        self.app.change_color(mode=modus)
        pump(2.0)
        self.assertEqual(self.offene_schilder(), [])
        self.app.change_color(mode=_PC["theme"].MODE_DARK)
        pump(2.0)
        self.assertEqual(self.offene_schilder(), [])


class PruefungPcTest(PcBasis):
    """B-J-N3 K32 und B-D-14 K40-K43 am PC."""

    def setUp(self):
        import fisi_pruefung as fp
        self.fp = fp
        fp.clear_running()
        self.addCleanup(fp.clear_running)
        self.panel = self.app.views["quiz"].exam
        self.gezeigt = []
        self.fragen = []

    def beobachten(self):
        for name in ("show_running", "show_grading"):
            patch = mock.patch.object(self.panel, name,
                                      lambda n=name: self.gezeigt.append(n))
            patch.start()
            self.addCleanup(patch.stop)

    def frage(self, antwort=True, entsteht=None):
        def askyesno(title, message, **_kw):
            self.fragen.append(message)
            if entsteht:
                self.fp.save_running(entsteht)
            return antwort
        return mock.patch.object(self.gui.messagebox, "askyesno", askyesno)

    def laufend(self, art, phase="laeuft"):
        state = self.fp.new_exam(art, [], seed=11)
        state["phase"] = phase
        self.fp.save_running(state)
        return json.dumps(self.fp.load_running(), sort_keys=True)

    def test_k32_startknoepfe(self):
        self.panel.show_choice()
        pump(0.3)
        knoepfe, stapel = [], [self.panel]
        while stapel:
            widget = stapel.pop(0)
            if isinstance(widget, self.fw.NeoButton) and \
                    str(widget.cget("text")).endswith(" starten"):
                knoepfe.append(widget)
            stapel.extend(widget.winfo_children())
        texte = [str(k.cget("text")) for k in knoepfe]
        self.assertEqual(texte, ["AP1 starten", "Konzeption starten", "Netzwerke starten",
                                 "WiSo starten"])
        for knopf, exam in zip(knoepfe, self.fp.EXAMS):
            self.fragen = []
            with self.frage(antwort=False):
                knopf.command()
            self.assertEqual(len(self.fragen), 1)
            self.assertTrue(self.fragen[0].startswith(exam["name"]), (knopf, self.fragen))
        self.assertIsNone(self.fp.load_running())

    def test_k40_laufende_bleibt(self):
        self.beobachten()
        vorher = self.laufend(self.fp.AP1)
        with self.frage():
            self.panel.start(self.fp.WISO)
        self.assertEqual(json.dumps(self.fp.load_running(), sort_keys=True), vorher)
        self.assertEqual(self.gezeigt, ["show_running"])
        self.assertEqual(self.fragen, [], "keine Rueckfrage, keine neue Meldung")

    def test_k41_entsteht_waehrend_der_rueckfrage(self):
        self.beobachten()
        andere = self.fp.new_exam(self.fp.NETZWERKE, [], seed=5)
        with self.frage(entsteht=andere):
            self.panel.start(self.fp.WISO)
        self.assertEqual(self.fp.load_running()["art"], self.fp.NETZWERKE)
        self.assertEqual(self.gezeigt, ["show_running"])

    def test_k42_ohne_laufende_wie_bisher(self):
        self.beobachten()
        with self.frage():
            self.panel.start(self.fp.WISO)
        state = self.fp.load_running()
        self.assertEqual((state["art"], state["phase"]), (self.fp.WISO, "laeuft"))
        self.assertEqual(self.gezeigt, ["show_running"])
        self.assertEqual(len(self.fragen), 1)

    def test_k43_bewerten_zaehlt_als_laufend(self):
        self.beobachten()
        vorher = self.laufend(self.fp.KONZEPTION, phase="bewerten")
        with self.frage():
            self.panel.start(self.fp.AP1)
        self.assertEqual(json.dumps(self.fp.load_running(), sort_keys=True), vorher)
        self.assertEqual(self.gezeigt, ["show_grading"])

    def test_k44_nein_aendert_nichts(self):
        self.beobachten()
        with self.frage(antwort=False):
            self.panel.start(self.fp.AP1)
        self.assertIsNone(self.fp.load_running())
        self.assertEqual(self.gezeigt, [])


class NcPcTest(PcBasis):
    """K50 an der Oberflaeche: Platzhalter des Suchfelds."""

    def test_platzhalter(self):
        self.assertEqual(self.app.header.search_entry.cget("placeholder_text"),
                         "Suchen …  (Strg+F)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
