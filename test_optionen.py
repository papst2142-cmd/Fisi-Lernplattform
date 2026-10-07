#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer 0.59: Optionen mit Klappbereichen, Vorlagen, Suche, Anzeigenamen
der Hintergruende im Hell-Modus (8c) und Desktop-Verknuepfung unter Linux (8b).

Start:  python test_optionen.py   (Teile mit Oberflaeche brauchen ein Display)
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_TMP = tempfile.mkdtemp(prefix="fisi_optionen_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "optionen.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(_TMP, "selbsttest.log"))

import fisi_diagnose as fdg  # noqa: E402
import fisi_hilfe as fh  # noqa: E402
import fisi_leistung as fle  # noqa: E402
import fisi_optionen as fo  # noqa: E402
import fisi_rahmenplan as frp  # noqa: E402
import fisi_sicherung as fsi  # noqa: E402
import fisi_theme as th  # noqa: E402
import fisi_verknuepfung as fsc  # noqa: E402
from fisi_lernen import DELETE_TITLE  # noqa: E402

# Ab 0.59.2 (U): "problem" und "leistung" stehen als Zwischenueberschriften
# im letzten Bereich "diagnose"
PC_IDS = ["updates", "rundgang", "schrift", "farben", "tagesziel", "rahmenplan", "abgleich",
          "sicherung", "datenbank", "lerninhalte", "spiel", "loeschen", "ueber", "diagnose"]
NAMES_DARK = {"violett": "Violett", "nachtblau": "Nachtblau", "tannengruen": "Tannengrün",
              "aubergine": "Aubergine", "anthrazit": "Anthrazit", "schwarz": "Schwarz"}
NAMES_LIGHT = {"violett": "Flieder", "nachtblau": "Hellblau", "tannengruen": "Mintgrün",
               "aubergine": "Rosé", "anthrazit": "Hellgrau", "schwarz": "Weiß"}
ACCENTS = ("accent", "accent2", "green", "purple", "orange", "red")


def _tk_ok():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:  # noqa: BLE001
        return False


def _flet_ok():
    try:
        import flet
        return bool(flet)
    except Exception:  # noqa: BLE001
        return False


def _reset_theme():
    th.custom_colors.clear()
    th.apply_mode(th.MODE_DARK)
    th.apply_background(th.DEFAULT_BACKGROUND)
    th.apply_preset(th.DEFAULT_PRESET)


# ============================================================================
#  AUFBAU (gemeinsam PC und Handy)
# ============================================================================

class AufbauTest(unittest.TestCase):

    def test_reihenfolge_updates_vor_rundgang(self):
        self.assertEqual([area["id"] for area in fo.areas(pc=True)], PC_IDS)
        self.assertEqual(fo.areas()[0]["titel"], "Updates")
        self.assertEqual(fo.areas()[1]["titel"], fh.OPTIONS_TITLE)

    def test_handy_ohne_datenbank_sonst_gleich(self):
        handy = [area["id"] for area in fo.areas(pc=False)]
        self.assertEqual(handy, [key for key in PC_IDS if key != "datenbank"])

    def test_offen_nur_updates(self):
        # bis 0.59.1 auch "Problem melden", ab 0.59.2 im eingeklappten Bereich
        opened = [area["id"] for area in fo.AREAS if fo.opened_at_start(area["id"])]
        self.assertEqual(opened, ["updates"])

    # -- ab 0.59.2 (U): Diagnose und Werkzeuge ------------------------------

    def test_diagnose_ist_der_letzte_bereich(self):
        for pc in (True, False):
            self.assertEqual(fo.areas(pc)[-1]["id"], fo.DIAGNOSE_ID)
        self.assertEqual(fo.DIAGNOSE_TITLE, "Diagnose und Werkzeuge")
        self.assertFalse(fo.opened_at_start(fo.DIAGNOSE_ID))

    def test_diagnose_abschnitte(self):
        import fisi_haenger as fhg
        pc = [(item["id"], item["titel"]) for item in fo.diagnose_sections(pc=True)]
        self.assertEqual(pc, [("problem", fdg.TITLE), ("leistung", fle.TITLE),
                              ("haenger", fhg.TITLE)])
        handy = [item["id"] for item in fo.diagnose_sections(pc=False)]
        self.assertEqual(handy, ["problem", "leistung"])

    def test_suche_findet_werkzeuge(self):
        for word in ("Problem", "Problem melden", "Fehler", "Messung", "Leistungsmessung",
                     "Diagnose", "Werkzeuge"):
            for pc in (True, False):
                hits = [hit[0] for hit in fo.search_options(word, pc=pc)]
                self.assertIn(fo.DIAGNOSE_ID, hits, (word, pc))
        for word in ("haenger", "Hänger"):
            self.assertIn(fo.DIAGNOSE_ID, [hit[0] for hit in fo.search_options(word)])
            # am Handy gibt es keine Haenger-Diagnose
            self.assertNotIn(fo.DIAGNOSE_ID,
                             [hit[0] for hit in fo.search_options(word, pc=False)])
        self.assertEqual(fo.hit_target(fo.DIAGNOSE_TITLE, "Problem"), (fo.DIAGNOSE_ID, False))

    def test_texte_nennen_den_neuen_ort(self):
        import fisi_update as fu
        self.assertIn("Diagnose und Werkzeuge", fh.HELP_BY_ID["problem"]["text"])
        self.assertIn("Diagnose und Werkzeuge", fh.HELP_BY_ID["leistung"]["text"])
        self.assertIn("Diagnose und Werkzeuge › Problem melden", fu.FAILED_TEXT)
        for section in fh.HELP_SECTIONS:
            self.assertNotIn("unter „Problem melden“", section["text"], section["id"])

    def test_titel_wie_in_den_modulen(self):
        titles = {area["id"]: area["titel"] for area in fo.AREAS}
        self.assertEqual(titles["schrift"], th.FONT_TITLE)
        self.assertEqual(titles["rahmenplan"], frp.OPTIONS_TITLE)
        self.assertEqual(titles["sicherung"], fsi.TITLE)
        self.assertEqual(titles["diagnose"], fo.DIAGNOSE_TITLE)
        self.assertEqual(titles["loeschen"], DELETE_TITLE)

    def test_kacheln_bei_sehr_gross_umbrechen(self):
        self.assertEqual(fo.tile_columns(th.font_factor("normal")), 6)
        self.assertEqual(fo.tile_columns(th.font_factor("gross")), 6)
        self.assertEqual(fo.tile_columns(th.font_factor("sehr_gross")), 3)

    def test_beschriftung_bereich_und_zustand(self):
        self.assertEqual(th.fold_label("Farben", False), "Farben, eingeklappt")
        self.assertEqual(th.fold_label("Farben", True), "Farben, aufgeklappt")
        self.assertEqual((th.FOLD_OPEN_TEXT, th.FOLD_CLOSE_TEXT), ("aufklappen", "einklappen"))

    def test_keine_neue_einstellung(self):
        """E4: Der Klappzustand wird nirgends gespeichert."""
        for name in ("fisi_optionen.py", "fisi_widgets.py", "app_gui.py",
                     os.path.join("mobile", "src", "ui.py"),
                     os.path.join("mobile", "src", "main.py")):
            with open(os.path.join(HERE, name), encoding="utf-8") as handle:
                text = handle.read()
            self.assertNotIn("save_settings(fo", text, name)
            self.assertNotIn("optionen_offen", text, name)

    def test_handy_bekommt_fisi_optionen(self):
        sys.path.insert(1, os.path.join(HERE, "mobile"))
        import vorbereiten
        self.assertIn("fisi_optionen.py", vorbereiten.SHARED_FILES)
        with open(os.path.join(HERE, ".gitignore"), encoding="utf-8") as handle:
            self.assertIn("mobile/src/fisi_optionen.py", handle.read())


# ============================================================================
#  SUCHE (E5)
# ============================================================================

class SucheTest(unittest.TestCase):

    def test_treffer_in_eingeklapptem_bereich(self):
        hits = fo.search_options("Token")
        self.assertEqual([hit[0] for hit in hits], ["abgleich"])
        self.assertFalse(hits[0][3])
        self.assertEqual(fo.hit_target("Abgleich PC und Handy", "Token"), ("abgleich", False))

    def test_treffer_im_unterbereich_vorlagen(self):
        for query in ("Vorlagen", "Schwarz", "Weiß", "hintergrund", "Cyan/Pink"):
            hits = fo.search_options(query)
            self.assertIn("farben", [hit[0] for hit in hits], query)
            self.assertTrue([hit for hit in hits if hit[0] == "farben"][0][3], query)
            self.assertEqual(fo.hit_target("Farben", query), ("farben", True), query)
        # "Regler" liegt in Farben, aber nicht in den Vorlagen
        self.assertEqual(fo.hit_target("Farben", "Regler"), ("farben", False))

    def test_kein_treffer(self):
        self.assertEqual(fo.search_options("xyzzy-nichts"), [])
        self.assertEqual(fo.search_options(""), [])
        self.assertEqual(fo.hit_target("Gibt es nicht", "x"), (None, False))

    def test_datenbank_nur_am_pc(self):
        self.assertTrue(fo.search_options("Speicherort", pc=True))
        self.assertEqual(fo.search_options("Speicherort", pc=False), [])

    def test_titel_trifft_auch(self):
        self.assertEqual(fo.search_options("schriftgröße")[0][0], "schrift")


# ============================================================================
#  ANZEIGENAMEN DER HINTERGRUENDE (8c)
# ============================================================================

class NamenTest(unittest.TestCase):

    def tearDown(self):
        _reset_theme()

    def test_namen_hell_und_dunkel(self):
        for back in th.BACKGROUND_IDS:
            self.assertEqual(th.background_name(back, th.MODE_DARK), NAMES_DARK[back])
            self.assertEqual(th.background_name(back, th.MODE_LIGHT), NAMES_LIGHT[back])
            self.assertEqual(th.light_background(back)["name"], NAMES_LIGHT[back])
            self.assertEqual(th.background(back)["name"], NAMES_DARK[back])   # intern gleich

    def test_auswahl_bleibt_beim_moduswechsel(self):
        th.apply_background("schwarz")
        th.apply_mode(th.MODE_LIGHT)
        self.assertEqual(th.current_background, "schwarz")
        self.assertEqual(th.background_name(th.current_background), "Weiß")
        th.apply_mode(th.MODE_DARK)
        self.assertEqual(th.current_background, "schwarz")
        self.assertEqual(th.background_name(th.current_background), "Schwarz")

    def test_farbwerte_unveraendert(self):
        """Nur der Name kam dazu: alle Werte der hellen Hintergruende wie 0.58.1
        (Pruefsumme mit main cb63c96 berechnet)."""
        values = {key: {k: v for k, v in th.light_background(key).items() if k != "name"}
                  for key in th.BACKGROUND_IDS}
        text = json.dumps(values, sort_keys=True)
        self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),
                         "364285fbb507063ad96effef2b9e67cc814ebf516cd8fcf869632b13ab27eab8")


# ============================================================================
#  KONTRAST DER KOPFZEILE (Plan 3.5)
# ============================================================================

class KontrastTest(unittest.TestCase):
    """Titel und Pfeil in der Akzentfarbe, Hinweis "aufklappen" in text_dim,
    auf der Karte und der Vorlagen-Flaeche (beim Darueberfahren wechselt nur
    der Rand, nicht die Flaeche) - in allen 72
    Farbwelten, hell und dunkel. Text 4,5:1, Pfeil 3:1."""

    def tearDown(self):
        _reset_theme()

    def test_alle_72_farbwelten(self):
        worlds = 0
        for mode in th.MODE_IDS:
            for back in th.BACKGROUND_IDS:
                for preset in th.PRESET_IDS:
                    th.apply_mode(mode)
                    th.apply_background(back)
                    th.apply_preset(preset)
                    worlds += 1
                    surfaces = [th.C["card"], th.C["card_alt"]]
                    for surface in surfaces:
                        where = (mode, back, preset, surface)
                        for accent in ACCENTS:
                            # Titel (Text) und Pfeil in derselben Farbe
                            self.assertGreaterEqual(th.contrast(th.C[accent], surface), 4.5,
                                                    (accent,) + where)
                        self.assertGreaterEqual(th.contrast(th.C["text_dim"], surface), 4.5,
                                                where)
                        self.assertGreaterEqual(th.contrast(th.C["muted"], surface), 4.5,
                                                where)
        self.assertEqual(worlds, 72)


# ============================================================================
#  DESKTOP-VERKNUEPFUNG (8b)
# ============================================================================

class VerknuepfungTest(unittest.TestCase):

    def setUp(self):
        self.home = tempfile.mkdtemp(dir=_TMP)
        self.desktop = os.path.join(self.home, "Schreibtisch")
        os.makedirs(self.desktop)
        self.icon = os.path.join(HERE, "icon.png")
        self.env = dict(os.environ)
        os.environ["XDG_DATA_HOME"] = os.path.join(self.home, ".local", "share")
        os.environ["XDG_CURRENT_DESKTOP"] = "KDE"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.env)

    def test_appimage_anlegen_und_erneuern_ohne_duplikat(self):
        os.environ["APPIMAGE"] = "/home/nico/Programme/FISI Lernplattform.AppImage"
        status, path, sure = fsc.create("appimage", self.desktop, self.icon)
        self.assertEqual(status, "neu")
        self.assertTrue(sure)   # KDE: Ausfuehrrecht genuegt
        self.assertTrue(os.access(path, os.X_OK))
        text = _read(path)
        self.assertIn('Exec="/home/nico/Programme/FISI Lernplattform.AppImage"', text)
        icon = os.path.join(self.home, ".local", "share", "icons", "hicolor", "512x512",
                            "apps", "fisi-lernplattform.png")
        self.assertIn("Icon=" + icon, text)
        self.assertTrue(os.path.isfile(icon))
        # AppImage verschoben: Knopf erneuert, keine zweite Datei
        os.environ["APPIMAGE"] = "/opt/neu/FISI.AppImage"
        status, path2, _sure = fsc.create("appimage", self.desktop, self.icon)
        self.assertEqual((status, path2), ("erneuert", path))
        self.assertEqual(os.listdir(self.desktop), [fsc.FILE_NAME])
        self.assertIn("Exec=/opt/neu/FISI.AppImage", _read(path))

    def test_deb_zeigt_auf_befehl_und_symbol(self):
        _status, path, _sure = fsc.create("deb", self.desktop)
        text = _read(path)
        self.assertIn("Exec=/usr/bin/fisi-lernplattform\n", text)
        self.assertIn("Icon=fisi-lernplattform\n", text)

    def test_gueltig_nach_desktop_file_validate(self):
        if shutil.which("desktop-file-validate") is None:
            self.skipTest("desktop-file-validate nicht installiert")
        os.environ["APPIMAGE"] = "/tmp/mit Leerzeichen/FISI.AppImage"
        for kind in ("appimage", "deb"):
            _status, path, _sure = fsc.create(kind, self.desktop, self.icon)
            result = subprocess.run(["desktop-file-validate", path], capture_output=True,
                                    text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout.strip(), "", kind)

    def test_ohne_desktop_ordner(self):
        original = fsc.desktop_dir
        fsc.desktop_dir = lambda: None
        try:
            self.assertEqual(fsc.create("deb")[0], "kein_desktop")
            self.assertEqual(fsc.message(fsc.create("deb")), fsc.MSG_NO_DESKTOP)
        finally:
            fsc.desktop_dir = original

    def test_pfad_aus_xdg_user_dir(self):
        bin_dir = os.path.join(self.home, "bin")
        os.makedirs(bin_dir)
        script = os.path.join(bin_dir, "xdg-user-dir")
        with open(script, "w") as handle:
            handle.write("#!/bin/sh\necho %s\n" % self.desktop)
        os.chmod(script, 0o755)
        os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
        os.environ["HOME"] = self.home
        self.assertEqual(fsc.desktop_dir(), self.desktop)
        # xdg-user-dir liefert den Benutzerordner: kein Desktop
        with open(script, "w") as handle:
            handle.write("#!/bin/sh\necho %s\n" % self.home)
        self.assertIsNone(fsc.desktop_dir())

    def test_gnome_braucht_vertrauensmarkierung(self):
        os.environ["XDG_CURRENT_DESKTOP"] = "ubuntu:GNOME"
        self.assertEqual(fsc.desktop_session(), "gnome")
        os.environ["XDG_CURRENT_DESKTOP"] = "KDE"
        self.assertEqual(fsc.desktop_session(), "kde")
        os.environ["XDG_CURRENT_DESKTOP"] = ""
        self.assertEqual(fsc.desktop_session(), "andere")
        # Nicht sicher markiert -> Hinweis "Start erlauben"
        self.assertIn("Start erlauben", fsc.message(("neu", "/x", False)))
        self.assertNotIn("Start erlauben", fsc.message(("neu", "/x", True)))

    def test_exec_maskierung(self):
        self.assertEqual(fsc.quote_exec("/opt/a/b"), "/opt/a/b")
        self.assertEqual(fsc.quote_exec("/a b/c"), '"/a b/c"')
        self.assertEqual(fsc.quote_exec('/a$b c'), '"/a\\$b c"')

    def test_rueckfrage(self):
        original = fsc.desktop_dir
        fsc.desktop_dir = lambda: self.desktop
        try:
            self.assertFalse(fsc.should_ask(None) and fsc.kind() is None)
            fsc.set_answer("fragen")
            self.assertTrue(fsc.should_ask("deb"))
            fsc.set_answer("nie")
            self.assertFalse(fsc.should_ask("deb"))
            fsc.set_answer("fragen")
            fsc.create("deb")
            self.assertFalse(fsc.should_ask("deb"))   # liegt schon da
        finally:
            fsc.desktop_dir = original
            fsc.set_answer("fragen")

    def test_nur_unter_linux_installiert(self):
        self.assertFalse(fsc.supported("windows"))
        self.assertTrue(fsc.supported("deb"))
        self.assertTrue(fsc.supported("appimage"))
        if not getattr(sys, "frozen", False):
            self.assertIsNone(fsc.kind())   # Quellcode: kein Knopf, keine Frage


# ============================================================================
#  PC-OBERFLAECHE
# ============================================================================

@unittest.skipUnless(_tk_ok(), "kein Display fuer Tk")
class OptionenPcTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import customtkinter as ctk
        import app_gui
        import fisi_widgets
        cls.app_gui, cls.fw = app_gui, fisi_widgets
        fh.mark_tour_seen()
        app_gui.UpdateController.auto_check = lambda self: None
        app_gui.SyncController.auto_start = lambda self: None
        cls.root = ctk.CTk()
        cls.root.geometry("1360x900+0+0")
        cls.app = app_gui.FISIApp(cls.root)
        cls.pump()

    @classmethod
    def tearDownClass(cls):
        for job in cls.root.tk.splitlist(cls.root.tk.call("after", "info")):
            cls.root.tk.call("after", "cancel", job)
        cls.root.destroy()
        _reset_theme()

    @classmethod
    def pump(cls, times=8):
        for _ in range(times):
            cls.root.update_idletasks()
            cls.root.update()

    def open_settings(self):
        self.app.show_view("dashboard")
        self.app.show_view("settings")
        self.pump()
        return self.app.views["settings"]

    def test_a_beim_oeffnen_alles_zu_ausser_updates(self):
        view = self.open_settings()
        self.assertEqual(list(view.areas), PC_IDS)
        for key, card in view.areas.items():
            if key == "updates":
                self.assertNotIsInstance(card, self.fw.FoldCard, key)
                self.assertTrue(card.body.winfo_ismapped(), key)
            else:
                self.assertIsInstance(card, self.fw.FoldCard, key)
                self.assertFalse(card.opened, key)
                self.assertFalse(card.body.winfo_ismapped(), key)
        self.assertFalse(view.folds["vorlagen"].opened)
        # Updates steht auf der Seite vor dem Rundgang
        self.assertLess(view.areas["updates"].winfo_y(), view.areas["rundgang"].winfo_y())

    def test_b_mehrere_offen_und_beim_naechsten_oeffnen_wieder_zu(self):
        view = self.open_settings()
        view.folds["farben"].toggle()
        view.folds["tagesziel"].toggle()
        view.folds["vorlagen"].toggle()
        self.pump()
        self.assertTrue(view.folds["farben"].opened and view.folds["tagesziel"].opened)
        self.assertTrue(view.folds["vorlagen"].body.winfo_ismapped())
        view = self.open_settings()
        self.assertFalse(any(fold.opened for fold in view.folds.values()))
        self.assertFalse([key for key, value in self.fw.FoldCard._open_state.items()
                          if key.startswith(fo.STATE_PREFIX) and value])

    def test_c_kopfzeile_pfeil_hinweis_und_beschriftung(self):
        view = self.open_settings()
        fold = view.folds["farben"]
        self.assertEqual(fold.arrow.cget("text"), "aufklappen")
        self.assertEqual(fold.accessible_name(), "Farben, eingeklappt")
        self.assertEqual(fold.pointer.winfo_x() < fold.title_label.winfo_x(), True)
        for widget in fold.head.winfo_children():
            self.assertEqual(widget.cget("cursor"), "hand2")
        # ganze Zeile klickbar (CTkLabel bindet an das innere Tk-Label)
        fold.subtitle_label._label.event_generate("<Button-1>")
        self.pump()
        self.assertTrue(fold.opened)
        self.assertEqual(fold.arrow.cget("text"), "einklappen")
        self.assertEqual(fold.accessible_name(), "Farben, aufgeklappt")
        fold.toggle()

    def test_d_tastatur(self):
        view = self.open_settings()
        fold = view.folds["tagesziel"]
        fold.head.focus_force()
        self.pump()
        tk = self.app_gui.tk
        tk.Frame.event_generate(fold.head, "<Return>")
        self.pump()
        self.assertTrue(fold.opened)
        tk.Frame.event_generate(fold.head, "<space>")
        self.pump()
        self.assertFalse(fold.opened)

    def test_e_eingeklappte_inhalte_nicht_per_tab(self):
        view = self.open_settings()
        closed = [fold.body for fold in view.folds.values()]
        widget = view.btn_update
        seen = []
        for _step in range(40):
            path = self.fw.next_focus(widget)
            if not path:
                break
            widget = self.root.nametowidget(path)
            seen.append(widget)
        self.assertTrue(seen)
        heads = [str(fold.head) for key, fold in view.folds.items() if key != "vorlagen"]
        reached = [str(widget) for widget in seen]
        for head in heads[:5]:
            self.assertIn(head, reached)
        for widget in seen:
            for body in closed:
                self.assertFalse(str(widget).startswith(str(body) + "."), str(widget))

    def test_f_suche_oeffnet_bereich(self):
        self.open_settings()
        self.app.do_search("Token")
        self.pump()
        self.app.open_search_hit(fo.SEARCH_KIND, "Abgleich PC und Handy")
        self.pump()
        view = self.app.views["settings"]
        self.assertEqual(self.app.current, "settings")
        self.assertTrue(view.folds["abgleich"].opened)
        self.assertFalse(view.folds["farben"].opened)
        self.assertGreater(view.canvas.yview()[0], 0.0)
        # Suchfeld leeren: nichts klappt wieder zu
        self.app.header.search_entry.delete(0, "end")
        self.pump()
        self.assertTrue(view.folds["abgleich"].opened)

    def test_f2_diagnose_letzter_bereich_mit_allen_werkzeugen(self):
        # ab 0.59.2 (U): ganz unten, eingeklappt, enthaelt Problem melden,
        # Leistungsmessung und Haenger-Diagnose
        import fisi_haenger as fhg
        view = self.open_settings()
        card = view.areas["diagnose"]
        self.assertIs(card, list(view.areas.values())[-1])
        self.assertFalse(card.opened)
        card.toggle()
        self.pump()
        self.assertGreater(card.winfo_y(), view.areas["ueber"].winfo_y())
        body = str(card.body)
        for widget in (view.report_box, view.lbl_perf, view.lbl_hang):
            self.assertTrue(str(widget).startswith(body + "."), str(widget))
        texts = [label.cget("text") for label in _labels(card.body)]
        for text in (fdg.TITLE.upper(), fle.TITLE.upper(), fhg.TITLE.upper(), fdg.HELP,
                     fle.HELP, fhg.HELP):
            self.assertIn(text, texts)
        # Knoepfe (NeoButton zeichnet seinen Text selbst; per Name suchen)
        buttons = []

        def walk(widget):
            for child in widget.winfo_children():
                if isinstance(child, self.fw.NeoButton):
                    buttons.append(child.cget("text"))
                walk(child)
        walk(card.body)

        def has_button(text):
            return any(caption.endswith(text) for caption in buttons)
        for text in (fdg.BTN_COPY, fdg.BTN_SAVE, fdg.BTN_FOLDER, fle.BTN_SHOW, fle.BTN_DELETE):
            self.assertTrue(has_button(text), (text, buttons))
        if sys.platform.startswith("linux"):
            self.assertIn(fhg.KILL_COMMAND, texts)
            self.assertTrue(has_button(fhg.BTN_COPY), buttons)
        self.assertEqual(view.lbl_perf.cget("text") != "", True)

    def test_f3_suche_problem_oeffnet_diagnose(self):
        self.open_settings()
        self.app.do_search("Problem")
        self.pump()
        self.app.open_search_hit(fo.SEARCH_KIND, fo.DIAGNOSE_TITLE)
        self.pump()
        view = self.app.views["settings"]
        self.assertEqual(self.app.current, "settings")
        self.assertTrue(view.folds["diagnose"].opened)
        self.assertGreater(view.canvas.yview()[0], 0.5)

    def test_g_suche_oeffnet_vorlagen_und_trefferliste(self):
        self.open_settings()
        self.app.do_search("Vorlagen")
        self.pump()
        texts = [child.cget("text") for child in _labels(self.app.views["search"].results_box)]
        self.assertIn("Farben", texts)
        self.assertIn(fo.SEARCH_KIND, texts)
        self.app.open_search_hit(fo.SEARCH_KIND, "Farben")
        self.pump()
        view = self.app.views["settings"]
        self.assertTrue(view.folds["farben"].opened and view.folds["vorlagen"].opened)

    def test_h_zustandszeile_in_beiden_klappzustaenden(self):
        view = self.open_settings()
        panel = view.custom_colors
        expected = th.custom_state_text(panel.values, panel.mode)
        self.assertEqual(panel.state_line.cget("text"), expected)
        view.folds["farben"].toggle()
        view.folds["vorlagen"].toggle()
        self.pump()
        self.assertEqual(panel.state_line.cget("text"), expected)
        self.assertTrue(panel.state_line.winfo_ismapped())

    def test_i_kacheln_hell_heissen_anders(self):
        tiles = []
        th.apply_mode(th.MODE_LIGHT)
        try:
            for back in th.BACKGROUND_IDS:
                tile = self.app_gui.BackgroundTile(self.root, th.background(back), False,
                                                   lambda _id: None)
                tiles.append(tile)
                self.assertEqual(tile.name, NAMES_LIGHT[back])
        finally:
            th.apply_mode(th.MODE_DARK)
            for tile in tiles:
                tile.destroy()
        tile = self.app_gui.BackgroundTile(self.root, th.background("schwarz"), False,
                                           lambda _id: None)
        self.assertEqual(tile.name, "Schwarz")
        tile.destroy()

    def test_j_neuaufbau_behaelt_offene_bereiche(self):
        """Farb- oder Schriftwechsel in den Optionen: offene Bereiche bleiben offen."""
        view = self.open_settings()
        view.folds["farben"].toggle()
        view.folds["vorlagen"].toggle()
        self.app.change_color(background_id="nachtblau")
        self.pump(20)
        view = self.app.views["settings"]
        self.assertTrue(view.folds["farben"].opened and view.folds["vorlagen"].opened)
        self.assertFalse(view.folds["tagesziel"].opened)
        self.app.change_color(background_id=th.DEFAULT_BACKGROUND)
        self.pump(20)

    def test_l_hilfe_hat_dieselbe_kopfzeile(self):
        """F2: Die Hilfe-Abschnitte haben die neue Kopfzeile (Inhalte gleich)."""
        self.app.show_view("help")
        self.pump()
        view = self.app.views["help"]
        self.assertEqual(sorted(view.folds), sorted(fh.HELP_IDS))
        for key, fold in view.folds.items():
            self.assertTrue(fold.marker, key)
            self.assertEqual(fold.arrow.cget("text"),
                             th.FOLD_CLOSE_TEXT if fold.opened else th.FOLD_OPEN_TEXT)
            self.assertEqual(fold.accessible_name(),
                             th.fold_label(fh.HELP_BY_ID[key]["titel"], fold.opened))
            self.assertIn(fh.HELP_BY_ID[key]["text"],
                          [label.cget("text") for label in _labels(fold.body)])

    def test_k_breite_passt_sich_nach_einklappen_an(self):
        """Nach dem Einklappen ist die Seite nicht breiter als das Fenster,
        wenn der Inhalt hineinpasst (rechts wird nichts abgeschnitten)."""
        view = self.open_settings()

        def window_width():
            return int(float(view.canvas.itemcget(view._window, "width")))

        self.assertEqual(window_width(),
                         max(view.canvas.winfo_width(), view.inner.winfo_reqwidth()))
        view.folds["farben"].toggle()
        self.pump()
        view.folds["farben"].toggle()
        self.pump()
        self.assertEqual(window_width(),
                         max(view.canvas.winfo_width(), view.inner.winfo_reqwidth()))


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _labels(widget):
    found = []
    for child in widget.winfo_children():
        if hasattr(child, "cget"):
            try:
                child.cget("text")
                found.append(child)
            except Exception:  # noqa: BLE001
                pass
        found += _labels(child)
    return found


# ============================================================================
#  HANDY-LOGIK
# ============================================================================

@unittest.skipUnless(_flet_ok(), "flet nicht installiert")
class OptionenHandyTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import flet as ft
        sys.path.insert(1, os.path.join(HERE, "mobile", "src"))
        import main
        import ui
        cls.ft, cls.main, cls.ui = ft, main, ui

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

        cls.app = FakeApp()

    def screen(self):
        self.ui.FoldCard.reset_states(fo.STATE_PREFIX)
        return self.main.SCREEN_CLASSES["settings"](self.app)

    def test_hilfe_hat_dieselbe_kopfzeile(self):
        screen = self.main.SCREEN_CLASSES["help"](self.app)
        screen.build()
        self.assertEqual(sorted(screen.folds), sorted(fh.HELP_IDS))
        for key, fold in screen.folds.items():
            self.assertTrue(fold.marker, key)
            self.assertEqual(fold.accessible_name(),
                             th.fold_label(fh.HELP_BY_ID[key]["titel"], fold.opened))

    def test_alles_zu_ausser_updates(self):
        screen = self.screen()
        self.assertEqual(list(screen.areas), [key for key in PC_IDS if key != "datenbank"])
        self.assertEqual(screen.root.controls, list(screen.areas.values()))
        for key, card in screen.areas.items():
            if key == "updates":
                self.assertNotIsInstance(card, self.ui.FoldCard, key)
            else:
                self.assertIsInstance(card, self.ui.FoldCard, key)
                self.assertFalse(card.opened, key)
                self.assertFalse(card.body.visible, key)
        self.assertFalse(screen.folds["vorlagen"].opened)

    def test_talkback_beschriftung_und_ansage(self):
        screen = self.screen()
        fold = screen.folds["farben"]
        self.assertEqual(fold.header_semantics.label, "Farben, eingeklappt")
        self.assertTrue(fold.header_semantics.button)
        self.assertTrue(fold.header_semantics.live_region)
        self.assertFalse(fold.header_semantics.expanded)
        self.assertEqual(fold.arrow_text.value, "aufklappen")
        fold.toggle()
        self.assertEqual(fold.header_semantics.label, "Farben, aufgeklappt")
        self.assertTrue(fold.header_semantics.expanded)
        self.assertEqual(fold.arrow_text.value, "einklappen")

    def test_ganze_kopfzeile_mindestens_48_dp(self):
        fold = self.screen().folds["tagesziel"]
        button = fold.header_button
        self.assertIsNotNone(button.on_click)
        self.assertGreaterEqual(fold.arrow.size + 2 * button.padding.top, 48)

    def test_mehrere_offen_und_beim_oeffnen_wieder_zu(self):
        screen = self.screen()
        screen.folds["farben"].toggle()
        screen.folds["diagnose"].toggle()
        self.assertTrue(screen.folds["farben"].opened and screen.folds["diagnose"].opened)
        screen.reset_folds()
        self.assertFalse(any(fold.opened for fold in screen.folds.values()))

    def test_reiterwechsel_klappt_zu(self):
        screen = self.screen()
        self.app.screens = {key: SimpleNamespace(crumbs=("A", "B"), on_show=lambda: None,
                                                 root=None)
                            for key, _icon, _icon2, _name in self.main.NAV}
        self.app.screens["settings"] = screen
        self.app.nav = SimpleNamespace(selected_index=0)
        self.app.crumb_main = SimpleNamespace(value="")
        self.app.crumb_sub = SimpleNamespace(value="")
        self.app.tab = "dashboard"
        screen.folds["farben"].toggle()
        self.app.show_tab("settings")
        self.assertFalse(screen.folds["farben"].opened)
        # Neuaufbau nach Farbwechsel (_recoloring): bleibt offen
        screen.folds["farben"].toggle()
        self.app.tab = "dashboard"
        self.app._recoloring = True
        try:
            self.app.show_tab("settings")
        finally:
            self.app._recoloring = False
        self.assertTrue(screen.folds["farben"].opened)

    def test_suche_oeffnet_bereich_und_vorlagen(self):
        screen = self.screen()
        self.assertEqual(screen.open_area("farben", templates=True), screen.areas["farben"])
        self.assertTrue(screen.folds["farben"].opened and screen.folds["vorlagen"].opened)
        self.assertIsNone(screen.open_area("datenbank"))   # gibt es am Handy nicht
        search = self.main.SCREEN_CLASSES["search"](self.app)
        search.search("Token")
        texts = []

        def walk(control):
            if isinstance(control, self.ft.Text):
                texts.append(control.value)
            for name in ("content", "controls"):
                value = getattr(control, name, None)
                if isinstance(value, self.ft.Control):
                    walk(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, self.ft.Control):
                            walk(item)
        walk(search.results)
        self.assertIn("Abgleich PC und Handy", texts)

    def test_diagnose_am_handy(self):
        # ab 0.59.2 (U): letzter Bereich, Problem melden und Leistungsmessung,
        # keine Haenger-Diagnose
        import fisi_haenger as fhg
        screen = self.screen()
        card = screen.areas["diagnose"]
        self.assertIs(card, list(screen.areas.values())[-1])
        self.assertFalse(card.opened)
        texts = []

        def walk(control):
            if isinstance(control, self.ft.Text):
                texts.append(control.value)
            for name in ("content", "controls"):
                value = getattr(control, name, None)
                if isinstance(value, self.ft.Control):
                    walk(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, self.ft.Control):
                            walk(item)
        walk(card.body)
        for text in (fdg.TITLE.upper(), fle.TITLE.upper(), fdg.HELP, fle.HELP):
            self.assertIn(text, texts)
        self.assertNotIn(fhg.TITLE.upper(), texts)
        self.assertNotIn(fhg.HELP, texts)
        self.assertIs(screen.open_area("diagnose"), card)
        self.assertTrue(card.opened)

    def test_kacheln_hell_heissen_anders_auch_fuer_talkback(self):
        th.apply_mode(th.MODE_LIGHT)
        try:
            screen = self.screen()
            for back in th.BACKGROUND_IDS:
                tile = screen._background_tile(th.background(back))
                self.assertEqual(tile.label, "Hintergrund %s" % NAMES_LIGHT[back])
        finally:
            th.apply_mode(th.MODE_DARK)
        tile = self.screen()._background_tile(th.background("schwarz"))
        self.assertEqual(tile.label, "Hintergrund Schwarz")


def tearDownModule():
    shutil.rmtree(_TMP, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
