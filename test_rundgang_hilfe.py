#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer Erststart-Rundgang und Hilfe (fisi_hilfe.py, ab 0.56).

Alle Datenbanken und die einstellungen.json liegen in einem Temp-Ordner
(FISI_DB_PATH), die echten Einstellungen bleiben unberuehrt. Die Tests mit
Oberflaeche brauchen eine Anzeige (unter Linux z.B. xvfb-run) und werden
sonst uebersprungen.

Start:  python test_rundgang_hilfe.py
"""

import ast
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import fisi_hilfe as fh  # noqa: E402
import fisi_rahmenplan as frp  # noqa: E402
from fisi_core import DBManager  # noqa: E402
from fisi_update import load_settings, save_settings  # noqa: E402

MOBILE_MAIN = os.path.join(HERE, "mobile", "src", "main.py")


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _row_counts(db_path):
    conn = sqlite3.connect(db_path)
    try:
        tables = [row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")]
        return {table: conn.execute('SELECT COUNT(*) FROM "%s"' % table).fetchone()[0]
                for table in tables}
    finally:
        conn.close()


class TempFolder(unittest.TestCase):
    """Temp-Ordner mit FISI_DB_PATH dorthin (fuer einstellungen.json)."""

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="fisi rundgang Ä ")
        self.old = os.environ.get("FISI_DB_PATH")
        os.environ["FISI_DB_PATH"] = os.path.join(self.folder, "fisi.db")
        self.db = DBManager(os.environ["FISI_DB_PATH"])

    def tearDown(self):
        if self.old is None:
            os.environ.pop("FISI_DB_PATH", None)
        else:
            os.environ["FISI_DB_PATH"] = self.old
        shutil.rmtree(self.folder, ignore_errors=True)


# ============================================================================
#  RUNDGANG: WANN ER ERSCHEINT (BESTANDSSCHUTZ)
# ============================================================================

class TourDueTest(TempFolder):
    def test_leere_datenbank_ohne_merker(self):
        self.assertFalse(fh.db_has_data(self.db))
        self.assertTrue(fh.tour_due(self.db))

    def test_merker_wird_gesetzt(self):
        before = _row_counts(self.db.db_path)
        self.assertTrue(fh.mark_tour_seen())
        settings = load_settings()
        self.assertTrue(settings[fh.TOUR_SEEN_KEY])
        self.assertTrue(fh.tour_seen())
        self.assertFalse(fh.tour_due(self.db))
        # Keine Aenderung an der Datenbank
        self.assertEqual(before, _row_counts(self.db.db_path))

    def test_vorhandener_lernstand_ohne_merker(self):
        """Bestandsschutz: wer schon gelernt hat, sieht den Rundgang nicht
        von selbst - auch ohne Merker. Die Pruefung schreibt nichts."""
        self.db.log_card("Netzwerk", "Frage", "lernen", True)
        before = _row_counts(self.db.db_path)
        self.assertTrue(fh.db_has_data(self.db))
        self.assertFalse(fh.tour_due(self.db))
        self.assertNotIn(fh.TOUR_SEEN_KEY, load_settings())
        self.assertFalse(os.path.exists(os.path.join(self.folder, "einstellungen.json")))
        self.assertEqual(before, _row_counts(self.db.db_path))

    def test_jede_art_von_daten_zaehlt(self):
        writers = [
            lambda db: db.log_quiz_answer("Systeme", "Quiz", True),
            lambda db: db.log_trainer("ipv4", 1, True),
            lambda db: db.save_test_result(8, 10, 80.0, "gut", 300),
            lambda db: db.save_project_field("p1", "titel", "Projekt"),
            lambda db: db.log_slot(1, "lauf1", "angelegt", "{}"),
            lambda db: db.log_record("lauf1", "erfolg", "x", 1.0),
        ]
        for number, write in enumerate(writers):
            db = DBManager(os.path.join(self.folder, "d%d.db" % number))
            self.assertFalse(fh.db_has_data(db))
            write(db)
            self.assertTrue(fh.db_has_data(db), "Schreiber %d" % number)
            self.assertFalse(fh.tour_due(db))

    def test_unlesbare_datenbank_gilt_als_befuellt(self):
        class Broken:
            def _execute(self, *_args, **kwargs):
                return kwargs.get("default")
        self.assertTrue(fh.db_has_data(Broken()))
        self.assertFalse(fh.tour_due(Broken()))

    def test_merker_ohne_daten(self):
        save_settings({fh.TOUR_SEEN_KEY: "2026-10-05"})
        self.assertFalse(fh.tour_due(self.db))


# ============================================================================
#  RUNDGANG: "JETZT EINRICHTEN"
# ============================================================================

class SetupTest(TempFolder):
    def test_einrichten_speichert_richtig(self):
        save_settings({"auto_check": False, "darstellung": "hell"})
        error = fh.save_setup("  Alex   Muster ", {"B": True, "D": False, "E": True},
                              "29.09.2027", "2028-04-26")
        self.assertIsNone(error)
        settings = load_settings()
        self.assertEqual(settings[fh.NAME_KEY], "Alex Muster")
        self.assertEqual(fh.load_name(), "Alex Muster")
        values = frp.load_rp_settings()
        self.assertTrue(values["rp_abschnitt_b"])
        self.assertFalse(values["rp_abschnitt_d"])
        self.assertTrue(values["rp_abschnitt_e"])
        self.assertEqual(values["rp_termin_ap1"], "2027-09-29")
        self.assertEqual(values["rp_termin_ap2"], "2028-04-26")
        # Andere Einstellungen bleiben erhalten, Gewichtung unveraendert
        self.assertFalse(settings["auto_check"])
        self.assertEqual(settings["darstellung"], "hell")
        self.assertTrue(values["rp_gewichtung"])
        # Startwerte beim naechsten Oeffnen
        start = fh.setup_values()
        self.assertEqual(start["name"], "Alex Muster")
        self.assertEqual(start["abschnitte"], {"B": True, "D": False, "E": True})
        self.assertEqual(start["rp_termin_ap1"], "29.09.2027")

    def test_ungueltiges_datum_wird_abgelehnt(self):
        save_settings({"rp_termin_ap1": "2027-09-29"})
        before = load_settings()
        for ap1, ap2 in (("31.02.2027", "26.04.2028"), ("29.09.2027", "morgen"),
                         ("2027-13-01", ""), ("29.9.27x", "")):
            self.assertEqual(fh.save_setup("Alex", {"B": True}, ap1, ap2), frp.DATE_INVALID)
            self.assertEqual(load_settings(), before, (ap1, ap2))
        self.assertEqual(fh.check_date("31.02.2027"), (None, frp.DATE_INVALID))
        self.assertEqual(fh.check_date(" 01.03.2027 "), ("2027-03-01", None))

    def test_leere_termine_wie_in_den_optionen(self):
        self.assertIsNone(fh.save_setup("", {}, "", " "))
        values = frp.load_rp_settings()
        self.assertEqual(values["rp_termin_ap1"], "")
        self.assertEqual(values["rp_termin_ap2"], "")
        self.assertEqual(load_settings()[fh.NAME_KEY], "")

    def test_name_wird_gekuerzt(self):
        fh.save_setup("x" * 100, {}, "", "")
        self.assertEqual(len(fh.load_name()), fh.NAME_MAX)

    def test_name_nur_auf_diesem_geraet(self):
        """Der Name steht nur in einstellungen.json: nicht in der Datenbank,
        nicht in der Sicherungsdatei, nicht im Bericht "Problem melden"."""
        import fisi_diagnose
        import fisi_sicherung
        self.db.log_card("Netzwerk", "Frage", "lernen", True)
        before = _row_counts(self.db.db_path)
        fh.save_setup("Zyxwvu Namenstest", {}, "", "")
        self.assertEqual(before, _row_counts(self.db.db_path))
        conn = sqlite3.connect(self.db.db_path)
        try:
            for table in before:
                for row in conn.execute('SELECT * FROM "%s"' % table):
                    self.assertNotIn("Zyxwvu", repr(row))
        finally:
            conn.close()
        backup = fisi_sicherung.create_backup(self.db, "0.56")
        text = backup if isinstance(backup, (bytes, str)) else json.dumps(backup)
        if isinstance(text, bytes):
            import gzip
            try:
                text = gzip.decompress(text).decode("utf-8")
            except OSError:
                text = text.decode("utf-8", "replace")
        self.assertNotIn("Zyxwvu", text)
        report = fisi_diagnose.build_report(self.db, "0.56", geraet="PC")
        self.assertNotIn("Zyxwvu", report)
        # Ab 0.56 (Nachbesserung): auch nicht im Abgleich und nicht nach dem
        # Aendern in den Optionen
        import fisi_sync
        fh.save_name("Zyxwvu Optionen")
        self.assertEqual(before, _row_counts(self.db.db_path))
        payload = json.dumps(fisi_sync.export_local(self.db), ensure_ascii=False)
        self.assertNotIn("Zyxwvu", payload)
        self.assertNotIn("Zyxwvu", fisi_diagnose.build_report(self.db, "0.56", geraet="PC"))

    def test_name_in_den_optionen_und_begruessung(self):
        """Ab 0.56: Feld in den Optionen (fh.save_name) und "Hallo <Name>"."""
        save_settings({"darstellung": "hell"})
        self.assertEqual(fh.greeting(), "")              # ohne Namen keine Begruessung
        self.assertEqual(fh.save_name("  Alex   Muster "), "Alex Muster")
        self.assertEqual(fh.load_name(), "Alex Muster")
        self.assertEqual(fh.greeting(), "Hallo Alex Muster")
        self.assertEqual(load_settings()["darstellung"], "hell")
        self.assertEqual(fh.save_name("y" * 80), "y" * fh.NAME_MAX)
        self.assertEqual(fh.save_name("   "), "")
        self.assertEqual(fh.greeting(), "")
        self.assertEqual(fh.greeting("Kim"), "Hallo Kim")


# ============================================================================
#  HILFE: TEXTE
# ============================================================================

TOPICS = ["lernen", "pruefung", "rechner", "spiel", "fortschritt", "sicherung", "abgleich",
          "update", "problem", "tastatur"]

# Navigation am Handy (mobile/src/main.py NAV und LearnScreen.ENTRIES), aus
# dem Quelltext gelesen, damit der Test ohne flet laeuft
MOBILE_NAV_RE = re.compile(r'\("(\w+)", ft\.Icons\.\w+, ft\.Icons\.\w+, "([^"]+)"\)')
MOBILE_LEARN_RE = re.compile(r'\("(\w+)", ft\.Icons\.\w+, "([^"]+)",')
# PC-Name -> Name am Handy (einzige Ausnahme der gleichen Beschriftung)
HANDY_NAME = {"Dashboard": "Start"}
# Begriffe, die es nur auf einem Geraet gibt (der Text sagt das dazu)
ONLY_PC = {"Dashboard", "Jetzt aktualisieren"}
ONLY_HANDY = {"Start", "Lernen", "Installieren"}
# Keine Beschriftung, sondern Erklaerung bzw. Anleitung
NOT_A_LABEL = {"Anführungszeichen", "Abgleich PC und Handy"}


def _quoted(text):
    return re.findall("„([^“]+)“", text)


def _pc_nav_names():
    import app_gui
    names = []
    for _key, _icon, text, subs in app_gui.NAV_ITEMS:
        names.append(text)
        if isinstance(subs, list):
            names += [sub[2] for sub in subs if isinstance(sub, tuple)]
    return names


def _mobile_names():
    source = _read(MOBILE_MAIN)
    return ([caption for _key, caption in MOBILE_NAV_RE.findall(source)],
            [title for _key, title in MOBILE_LEARN_RE.findall(source)])


class HelpTextTest(unittest.TestCase):
    def test_alle_themen_und_schutzprogramm(self):
        ids = [section["id"] for section in fh.HELP_SECTIONS]
        for topic in TOPICS + ["schutzprogramm"]:
            self.assertIn(topic, ids)
        self.assertEqual(len(ids), len(set(ids)))
        for section in fh.HELP_SECTIONS:
            self.assertTrue(section["titel"].strip())
            self.assertGreater(len(section["text"]), 120, section["id"])
            self.assertLess(len(section["text"]), 1200, section["id"])
        warning = fh.HELP_BY_ID["schutzprogramm"]["text"]
        self.assertIn("github.com/papst2142-cmd/Fisi-Lernplattform/releases", warning)
        self.assertIn("SHA-256", warning)
        self.assertIn("Release-Seite", warning)

    def test_keine_behauptungen_ueber_screenreader(self):
        everything = " ".join(section["text"] for section in fh.HELP_SECTIONS) + \
            " ".join(page["text"] for page in fh.TOUR_PAGES)
        for word in ("Screenreader", "NVDA", "TalkBack", "Sprachausgabe", "barrierefrei"):
            self.assertNotIn(word.lower(), everything.lower())

    def test_reiter_gibt_es_am_pc_und_handy(self):
        pc = _pc_nav_names()
        nav, learn = _mobile_names()
        self.assertEqual(len(nav), 6, nav)
        self.assertIn("Karteikarten", learn)
        for section in fh.HELP_SECTIONS:
            for name in section["reiter"]:
                self.assertIn(name, pc, (section["id"], name))
                handy = HANDY_NAME.get(name, name)
                self.assertTrue(handy in nav or handy in learn, (section["id"], name))
                self.assertIn("„%s“" % name, section["text"], (section["id"], name))

    def test_genannte_begriffe_stehen_so_in_der_oberflaeche(self):
        """Jeder Begriff in „…“ steht als Text im Programm: auf beiden Geraeten
        (gemeinsame Module oder beide Oberflaechen), Geraete-Begriffe nur dort."""
        shared = "".join(_read(os.path.join(HERE, name)) for name in os.listdir(HERE)
                         if name.startswith("fisi_") and name.endswith(".py")
                         and name != "fisi_hilfe.py")
        shared += _read(os.path.join(HERE, "LIESMICH.txt"))
        pc = shared + _read(os.path.join(HERE, "app_gui.py"))
        handy = shared + "".join(_read(os.path.join(HERE, "mobile", "src", name))
                                 for name in ("main.py", "ui.py", "spiel.py"))
        texts = [section["text"] for section in fh.HELP_SECTIONS] + \
            [page["text"] for page in fh.TOUR_PAGES] + \
            [fh.SETUP_DATES_HINT, fh.HELP_INTRO]
        terms = sorted({term for text in texts for term in _quoted(text)})
        self.assertGreater(len(terms), 40)
        for term in terms:
            if term in NOT_A_LABEL:
                continue
            literal = re.compile(r'["\'][^"\'\n]*%s' % re.escape(term))
            in_pc, in_handy = bool(literal.search(pc)), bool(literal.search(handy))
            if term in ONLY_PC:
                self.assertTrue(in_pc, term)
            elif term in ONLY_HANDY:
                self.assertTrue(in_handy, term)
            else:
                self.assertTrue(in_pc and in_handy, (term, in_pc, in_handy))

    def test_suche(self):
        hits = fh.search_help("schutzprogramm")
        self.assertEqual(hits[0][0], "schutzprogramm")
        self.assertEqual(fh.search_help(""), [])
        self.assertEqual(fh.search_help("xyzzy-nichts"), [])
        self.assertIn("sicherung", [hit[0] for hit in fh.search_help("SICHERUNG")])
        for _id, title, text in fh.search_help("Token"):
            self.assertNotIn("\n", text)
            self.assertIn(title, fh.HELP_BY_TITLE)

    def test_rundgang_seiten(self):
        self.assertTrue(4 <= len(fh.TOUR_PAGES) <= 6)
        self.assertEqual(fh.TOUR_PAGES[-1]["titel"], "Jetzt einrichten")
        ids = [page["id"] for page in fh.TOUR_PAGES]
        for topic in ("willkommen", "fortschritt", "spiel", "sicherung", "einrichten"):
            self.assertIn(topic, ids)
        self.assertEqual(fh.TOUR_SKIP, "Überspringen")


class SameTextsTest(unittest.TestCase):
    """PC und Handy zeigen dieselben Texte: beide nehmen sie aus fisi_hilfe
    und schreiben keine eigenen Hilfetexte."""

    NAMES = ("HELP_SECTIONS", "HELP_TITLE", "HELP_INTRO", "TOUR_PAGES", "TOUR_SKIP",
             "TOUR_NEXT", "TOUR_BACK", "TOUR_FINISH", "TOUR_STEP", "SETUP_NAME",
             "SETUP_PLAN", "SETUP_PLAN_HINT", "SETUP_DATES", "SETUP_DATES_HINT",
             "OPTIONS_TITLE", "OPTIONS_TEXT", "BTN_TOUR", "BTN_HELP", "SEARCH_KIND")

    def _uses(self, path):
        tree = ast.parse(_read(path))
        return {node.attr for node in ast.walk(tree)
                if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                and node.value.id == "fh"}

    def test_beide_oberflaechen_nutzen_fisi_hilfe(self):
        pc = self._uses(os.path.join(HERE, "app_gui.py"))
        handy = self._uses(MOBILE_MAIN)
        for name in self.NAMES:
            if name == "TOUR_KEYS":
                continue
            self.assertIn(name, pc, "PC: " + name)
            self.assertIn(name, handy, "Handy: " + name)
        for path in (os.path.join(HERE, "app_gui.py"), MOBILE_MAIN):
            source = _read(path)
            for section in fh.HELP_SECTIONS:
                # kein Hilfetext doppelt im Quelltext der Oberflaeche
                self.assertNotIn(section["text"][:60], source)

    def test_handy_bekommt_fisi_hilfe(self):
        sys.path.insert(0, os.path.join(HERE, "mobile"))
        try:
            import vorbereiten
        finally:
            sys.path.pop(0)
        self.assertIn("fisi_hilfe.py", vorbereiten.SHARED_FILES)
        self.assertIn("mobile/src/fisi_hilfe.py", _read(os.path.join(HERE, ".gitignore")))

    def test_handy_kopie_ist_gleich(self):
        copy = os.path.join(HERE, "mobile", "src", "fisi_hilfe.py")
        if not os.path.exists(copy):
            self.skipTest("mobile/vorbereiten.py noch nicht gelaufen")
        self.assertEqual(_read(copy), _read(os.path.join(HERE, "fisi_hilfe.py")))


class NavigationTest(unittest.TestCase):
    def test_hilfe_vor_optionen(self):
        import app_gui
        keys = [item[0] for item in app_gui.NAV_ITEMS]
        self.assertEqual(keys[-2:], ["help", "settings"])
        self.assertEqual(app_gui.NAV_ITEMS[-2][2], "Hilfe")
        self.assertEqual(app_gui.VIEW_TITLES["help"], ("SYSTEM", "HILFE"))
        symbol = app_gui.NAV_SYMBOLS["help"]
        import fisi_widgets
        self.assertIn(symbol, fisi_widgets.SYMBOLS)

    def test_symbol_in_der_schrift(self):
        from PIL import ImageFont
        import fisi_widgets
        font = ImageFont.truetype(os.path.join(HERE, fisi_widgets.SYMBOL_FONT_FILE), 40)
        for name, code in fisi_widgets.SYMBOLS.items():
            self.assertIsNotNone(font.getmask(chr(code)).getbbox(), name)

    def test_handy_hilfe_in_der_kopfzeile(self):
        source = _read(MOBILE_MAIN)
        self.assertIn("ft.Icons.HELP_OUTLINE_ROUNDED", source)
        self.assertIn('"help": HelpScreen', source)
        nav, _learn = _mobile_names()
        self.assertNotIn("Hilfe", nav)   # untere Leiste bleibt bei 6 Punkten


# ============================================================================
#  OBERFLAECHE PC (MIT ANZEIGE)
# ============================================================================

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
class PcTourTest(unittest.TestCase):
    """Ein Hauptfenster fuer alle Faelle (Tk mag keine zweite Wurzel mit
    denselben Bildern), Datenbank und Einstellungen im Temp-Ordner."""

    @classmethod
    def setUpClass(cls):
        import customtkinter as ctk
        cls.folder = tempfile.mkdtemp(prefix="fisi rundgang gui ")
        cls.old = {key: os.environ.get(key) for key in ("FISI_DB_PATH", "FISI_SELFTEST")}
        os.environ["FISI_DB_PATH"] = os.path.join(cls.folder, "fisi.db")
        os.environ["FISI_SELFTEST"] = os.path.join(cls.folder, "log.txt")   # kein Netz
        import app_gui
        cls.root = ctk.CTk()
        cls.app = app_gui.FISIApp(cls.root)
        cls.root.update()

    @classmethod
    def tearDownClass(cls):
        cls.app.on_close(final_sync=False)
        for key, value in cls.old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        shutil.rmtree(cls.folder, ignore_errors=True)

    def _app(self):
        import app_gui
        return app_gui, self.root, self.app

    def test_a_kein_rundgang_bei_vorhandenem_lernstand(self):
        _gui, root, app = self._app()
        filled = DBManager(os.path.join(self.folder, "befuellt.db"))
        filled.log_card("Netzwerk", "Frage", "lernen", True)
        original, app.db = app.db, filled
        try:
            app.maybe_start_tour()
            root.update()
        finally:
            app.db = original
        self.assertIsNone(getattr(app, "tour", None))
        self.assertNotIn(fh.TOUR_SEEN_KEY, load_settings())

    def test_b_rundgang_tastatur_und_einrichten(self):
        gui, root, app = self._app()
        settings_view = app.views["settings"]
        app.maybe_start_tour()
        root.update()
        tour = app.tour
        self.assertTrue(tour.winfo_exists())
        # Tab-Reihenfolge bleibt im Rundgang: Weiter -> Ueberspringen -> Weiter
        first = tour.focusables[0]
        self.assertEqual(first._caption, fh.TOUR_NEXT)
        self.assertEqual([w._caption for w in tour.focusables], [fh.TOUR_NEXT, fh.TOUR_SKIP])
        inner = [tour._focus_target(w) for w in tour.focusables]
        inner[0].focus_force()   # Fenster hat unter xvfb sonst keinen Fokus
        root.update()
        self.assertIs(root.focus_get(), inner[0])
        inner[0].event_generate("<Tab>")
        root.update()
        self.assertIs(root.focus_get(), inner[1])
        inner[1].event_generate("<Tab>")
        root.update()
        self.assertIs(root.focus_get(), inner[0])
        inner[0].event_generate("<Shift-Tab>")
        root.update()
        self.assertIs(root.focus_get(), inner[1])
        inner[1].event_generate("<Tab>")
        root.update()
        for _page in fh.TOUR_PAGES[1:]:
            root.focus_get().event_generate("<Return>")   # Eingabe auf "Weiter"
            root.update()
        self.assertEqual(tour.index, len(fh.TOUR_PAGES) - 1)
        # Einrichten: Name, 3 Schalter, 2 Termine, dann Speichern, Zurueck, Ueberspringen
        self.assertEqual(len(tour.focusables), 1 + len(frp.OPTIONAL_SECTIONS) + 2 + 3)
        tour.focus_force()
        tour._focus_target(tour.focusables[0]).focus_force()
        root.update()
        self.assertIs(root.focus_get(), tour.entry_name._entry)   # erst der Name
        tour._focus_target(tour.focusables[0]).event_generate("<Tab>")
        root.update()
        switch = tour.focusables[1]
        self.assertIs(root.focus_get(), tour._focus_target(switch))
        before = switch.get()
        tour._focus_target(switch).event_generate("<space>")
        root.update()
        self.assertNotEqual(before, switch.get())
        tour._focus_target(switch).event_generate("<space>")
        root.update()
        tour.entry_name.set("Alex")
        tour.section_vars["D"].set(True)
        tour.date_entries["rp_termin_ap1"].set("31.02.2027")
        tour.finish()
        root.update()
        self.assertTrue(tour.winfo_exists())
        self.assertEqual(tour.lbl_error.cget("text"), frp.DATE_INVALID)
        self.assertNotIn(fh.NAME_KEY, load_settings())
        tour.date_entries["rp_termin_ap1"].set("01.10.2027")
        tour.finish()
        root.update()
        self.assertFalse(tour.winfo_exists())
        settings = load_settings()
        self.assertEqual(settings[fh.NAME_KEY], "Alex")
        self.assertTrue(settings[fh.TOUR_SEEN_KEY])
        # Ab 0.56: Name im Feld der Optionen und als Begruessung im Dashboard
        self.assertEqual(settings_view.entry_name.get(), "Alex")
        self.assertEqual(app.views["dashboard"].hero._texts[0], "Hallo Alex")
        settings_view.entry_name.set("  Kim  ")
        settings_view._save_name()
        self.assertEqual(fh.load_name(), "Kim")
        self.assertEqual(settings_view.entry_name.get(), "Kim")
        self.assertEqual(app.views["dashboard"].hero._texts[0], "Hallo Kim")
        settings_view.entry_name.set("")
        settings_view._save_name()
        self.assertEqual(app.views["dashboard"].hero._texts[0], "Dein Lernstand")
        settings_view.entry_name.set("Alex")
        settings_view._save_name()
        self.assertEqual(frp.load_rp_settings()["rp_termin_ap1"], "2027-10-01")
        # Optionen zeigen die neuen Werte
        self.assertTrue(settings_view.rp_vars["rp_abschnitt_d"].get())
        self.assertEqual(settings_view.rp_dates["rp_termin_ap1"].get(), "01.10.2027")
        # Danach nicht mehr von selbst, aber aus den Optionen
        app.maybe_start_tour()
        root.update()
        self.assertFalse(app.tour.winfo_exists())
        settings_view.btn_tour._on_click()
        root.update()
        self.assertTrue(app.tour.winfo_exists())
        # Esc auf einem Knopf des Rundgangs = Ueberspringen
        app.tour._focus_target(app.tour.focusables[0]).event_generate("<Escape>")
        root.update()
        self.assertFalse(app.tour.winfo_exists())
        self.assertEqual(load_settings()[fh.NAME_KEY], "Alex")

    def test_c_hilfe_ansicht_und_suche(self):
        _gui, root, app = self._app()
        app.show_view("help")
        root.update()
        view = app.views["help"]
        self.assertEqual(sorted(view.folds), sorted(fh.HELP_IDS))
        self.assertFalse(view.folds["update"].opened)
        app.do_search("Fehlalarm")
        root.update()
        app.open_search_hit(fh.SEARCH_KIND, fh.HELP_BY_ID["schutzprogramm"]["titel"])
        root.update()
        self.assertEqual(app.current, "help")
        self.assertTrue(view.folds["schutzprogramm"].opened)


# Kindprozess: echtes Programm mit leerer Datenbank (Rundgang erscheint von
# selbst), dann Schliessen wie mit dem X - wie in test_beenden.py
CHILD = r'''
import os, sys, time
sys.path.insert(0, sys.argv[1])
os.chdir(sys.argv[1])
import app_gui
app_gui.UpdateController.auto_check = lambda self: None
app_gui.SyncController.auto_start = lambda self: None
init = app_gui.FISIApp.__init__

def patched(self, root):
    init(self, root)
    def check():
        tour = getattr(self, "tour", None)
        print("RUNDGANG", bool(tour is not None and tour.winfo_exists()), flush=True)
        root.after(300, self.on_close)
        print("GESCHLOSSEN", time.time(), flush=True)
    root.after(1500, check)
app_gui.FISIApp.__init__ = patched
app_gui.main()
print("ENDE", time.time(), flush=True)
'''


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class PcStartTest(unittest.TestCase):
    def _run(self, fill):
        folder = tempfile.mkdtemp(prefix="fisi rundgang start ")
        self.addCleanup(shutil.rmtree, folder, True)
        db_path = os.path.join(folder, "fisi.db")
        if fill:
            DBManager(db_path).log_card("Netzwerk", "Frage", "lernen", True)
        env = dict(os.environ, FISI_DB_PATH=db_path)
        env.pop("FISI_SELFTEST", None)
        started = time.time()
        result = subprocess.run([sys.executable, "-c", CHILD, HERE], env=env,
                                capture_output=True, text=True, timeout=60)
        log = os.path.join(folder, "fehler.log")
        errors = _read(log) if os.path.exists(log) else ""
        return result, errors, time.time() - started, folder

    def test_neuer_nutzer_rundgang_und_sauberes_beenden(self):
        result, errors, _took, folder = self._run(fill=False)
        self.assertIn("RUNDGANG True", result.stdout, result.stdout + result.stderr)
        self.assertIn("ENDE", result.stdout)
        self.assertEqual(errors.strip(), "")
        # Schliessen ohne Ueberspringen setzt keinen Merker
        path = os.path.join(folder, "einstellungen.json")
        settings = json.loads(_read(path)) if os.path.exists(path) else {}
        self.assertNotIn(fh.TOUR_SEEN_KEY, settings)

    def test_bestehender_nutzer_kein_rundgang(self):
        result, errors, _took, _folder = self._run(fill=True)
        self.assertIn("RUNDGANG False", result.stdout, result.stdout + result.stderr)
        self.assertIn("ENDE", result.stdout)
        self.assertEqual(errors.strip(), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
