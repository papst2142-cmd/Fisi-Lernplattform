#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer 0.62: Lizenz und Rechtliches (Plan 0.62, Abschnitt 7.3)
==================================================================

* Wortlaute aus fisi_rechtliches (Nicos Freigabe E1, E2, E11, E12)
* PC und Handy holen die Texte aus fisi_rechtliches, alte IHK-Wortlaute weg
* Erststart-Merker nur in einstellungen.json (nicht in Sicherung/Abgleich)
* LICENSE.txt, Erzeuger lizenzen.py (Abbruch bei Datei ohne Zuordnung),
  readline-Sperre im Bau, Handy-Liste (Weg B)
* Oberflaeche: Lizenzfenster PC und Seiten am Handy oeffnen in unter 1 s

Start:  python test_rechtliches.py   (Teile mit Oberflaeche brauchen ein Display)
"""

import os
import re
import shutil
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_TMP = tempfile.mkdtemp(prefix="fisi_rechtliches_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "rechtliches.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(_TMP, "selbsttest.log"))

import build  # noqa: E402
import fisi_hilfe as fh  # noqa: E402
import fisi_rechtliches as fr  # noqa: E402
import lizenzen  # noqa: E402
from fisi_update import load_settings, save_settings  # noqa: E402

ANDROID_LIST = os.path.join(HERE, "mobile", "lizenzen_android.txt")
# Auflage A4: keine Rechtsaussagen. "geprueft" steht nur verneint im
# freigegebenen Hinweistext ("weder herausgegeben noch geprüft").
FORBIDDEN = ("lizenziert", "rechtssicher", "frei von Rechten Dritter")
ALLOWED_CHECKED = "weder herausgegeben noch geprüft"


def read(*parts):
    with open(os.path.join(HERE, *parts), encoding="utf-8") as handle:
        return handle.read()


def release_text():
    return build.release_notes("0.62")


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


# ============================================================================
#  WORTLAUTE
# ============================================================================

class WortlautTest(unittest.TestCase):

    def test_texte_wie_freigegeben(self):
        self.assertEqual(fr.COPYRIGHT, "Copyright (c) 2026 Nico H – Alle Rechte vorbehalten")
        self.assertEqual(fr.CLAUDE_HINWEIS, "Erstellt mit Hilfe von Claude (Anthropic).")
        self.assertEqual(fr.HINWEIS_KURZ, "Übungsprüfung, keine offizielle IHK-Prüfung.")
        self.assertEqual(fr.NOTE_LANG,
                         "Note nach IHK-Schlüssel (Orientierung, keine amtliche Note)")
        self.assertEqual(fr.NOTE_KURZ, "Note (Orientierung)")
        self.assertEqual(fr.ERSTSTART,
                         "Privates Lernprogramm: keine offiziellen IHK-Prüfungsaufgaben, kein "
                         "IHK-Produkt. Mehr dazu unter Optionen › Über das Programm.")
        self.assertEqual(fr.BTN_VERSTANDEN, "Verstanden")
        self.assertEqual((fr.BTN_LIZENZ, fr.BTN_FREMD),
                         ("Lizenz", "Hinweise zu Fremdbestandteilen"))
        # E11: Satz zur Herkunft, von Nico fuer alle Inhalte bestaetigt
        self.assertIn("Die Aufgaben, Szenarien und Testprojekte sind eigene Übungsaufgaben. "
                      "Sie enthalten keine offiziellen Prüfungsaufgaben.", fr.HINWEIS)
        self.assertTrue(fr.HINWEIS.startswith(
            "Die Fachinformatiker Lernplattform ist ein privates Lernprogramm. Sie ist "
            "kein Angebot und kein Produkt einer Industrie- und Handelskammer (IHK)"))
        # E12: Fassung Claude Chat, keine bestimmte Kammer
        self.assertEqual(fr.KI_HINWEIS,
                         "Wenn du für dein Abschlussprojekt KI-Hilfsmittel nutzt (zum Beispiel "
                         "für Texte, Code oder Bilder), verlangen manche Kammern eine Angabe "
                         "dazu in der Projektdokumentation. Frag bei deiner IHK nach, was für "
                         "dich gilt.")
        self.assertNotIn("Nürnberg", fr.KI_HINWEIS)

    def test_nico_h_ohne_punkt(self):
        source = read("fisi_rechtliches.py")
        self.assertIn('PUBLISHER = "Nico H"', source)
        self.assertNotIn("Nico H.", source)

    def test_claude_hinweis_nur_der_name(self):
        for word in ("Partner", "offiziell", "empfohlen", "Logo", "unterstützt"):
            self.assertNotIn(word.lower(), fr.CLAUDE_HINWEIS.lower())

    def test_keine_rechtsaussagen(self):
        texts = {"fisi_rechtliches": " ".join(
            value for name, value in vars(fr).items() if name.isupper() and
            isinstance(value, str)),
                 "LICENSE.txt": read("LICENSE.txt"),
                 "Hilfe Rechtliches": fh.HELP_BY_ID["rechtliches"]["text"],
                 "AENDERUNGEN 0.62": release_text()}
        for where, text in texts.items():
            for word in FORBIDDEN:
                self.assertNotIn(word.lower(), text.lower(), (where, word))
            rest = text.replace(ALLOWED_CHECKED, "")
            self.assertNotIn("geprüft", rest.lower(), where)

    def test_aenderungen_nennen_den_namen_und_macos(self):
        notes = release_text()
        self.assertIn("Fachinformatiker Lernplattform", notes.split(".")[0])
        self.assertIn("gebaut und automatisch gestartet, aber nicht von Menschen auf einem "
                      "echten Mac getestet", " ".join(notes.split()))

    def test_ueber_text(self):
        text = fr.about_text("Fachinformatiker Lernplattform", "0.62", "PLATTFORM")
        self.assertTrue(text.startswith("Fachinformatiker Lernplattform Version 0.62\n"
                                        + fr.COPYRIGHT + "\n"))
        for part in ("PLATTFORM", fr.HINWEIS, fr.CLAUDE_HINWEIS):
            self.assertIn(part, text)


class OberflaechenTextTest(unittest.TestCase):
    FILES = ("app_gui.py", os.path.join("mobile", "src", "main.py"), "fisi_hilfe.py")

    def test_alte_ihk_wortlaute_weg(self):
        for name in self.FILES:
            source = read(name)
            for old in ("IHK-Note", "Notenschlüssel der IHK", "Wie in der echten Prüfung",
                        "wie in der echten Prüfung", "Verordnung 2020\""):
                self.assertNotIn(old, source, (name, old))

    def test_pc_und_handy_nutzen_fisi_rechtliches(self):
        for name in ("app_gui.py", os.path.join("mobile", "src", "main.py")):
            source = read(name)
            self.assertIn("import fisi_rechtliches as fr", source)
            for call in ("fr.about_text(", "fr.HINWEIS_KURZ", "fr.NOTE_LANG", "fr.NOTE_KURZ",
                         "fr.BTN_LIZENZ", "fr.BTN_FREMD", "fr.notice_due()",
                         "fr.mark_notice_seen()", "fr.ERSTSTART", "fr.BTN_VERSTANDEN"):
                self.assertIn(call, source, (name, call))
            # keine eigenen Kopien der Texte
            for text in (fr.HINWEIS[:60], fr.CLAUDE_HINWEIS, "Alle Rechte vorbehalten"):
                self.assertNotIn(text, source, (name, text))

    def test_untertitel_pruefungskarte_gleich(self):
        subtitle = 'subtitle="Aufbau nach der Ausbildungsverordnung 2020"'
        self.assertIn(subtitle, read("app_gui.py"))
        self.assertIn(subtitle, read("mobile", "src", "main.py"))

    def test_hilfe(self):
        # A6: KI-Hinweis im vorhandenen Abschnitt, kein eigener "Abschlussprojekt"
        self.assertIn(fr.KI_HINWEIS, fh.HELP_BY_ID["pruefung"]["text"])
        self.assertNotIn("abschlussprojekt", fh.HELP_IDS)
        self.assertEqual(sum(fr.KI_HINWEIS in s["text"] for s in fh.HELP_SECTIONS), 1)
        text = fh.HELP_BY_ID["rechtliches"]["text"]
        for part in (fr.HINWEIS, fr.COPYRIGHT, fr.CLAUDE_HINWEIS, "„Über das Programm“",
                     "„Lizenz“", "„Hinweise zu Fremdbestandteilen“"):
            self.assertIn(part, text)
        self.assertIn("frag bei deiner IHK nach", read("fisi_projekt.py"))

    def test_handy_bekommt_dateien(self):
        source = read("mobile", "vorbereiten.py")
        for name in ('"fisi_rechtliches.py"', '"LICENSE.txt"', '"lizenzen_android.txt"',
                     '"THIRD_PARTY_NOTICES.txt"'):
            self.assertIn(name, source)
        ignore = read(".gitignore")
        for name in ("mobile/src/fisi_rechtliches.py", "mobile/src/LICENSE.txt",
                     "mobile/src/THIRD_PARTY_NOTICES.txt"):
            self.assertIn(name + "\n", ignore)


# ============================================================================
#  LIZENZDATEIEN UND ERZEUGER
# ============================================================================

class LizenzTest(unittest.TestCase):

    def test_license_txt(self):
        text = read("LICENSE.txt")
        self.assertTrue(text.startswith("Fachinformatiker Lernplattform\n"))
        self.assertIn("\n" + fr.COPYRIGHT + "\n", text)
        self.assertIn("THIRD_PARTY_NOTICES.txt", text)
        self.assertIn("zur eigenen Prüfungsvorbereitung genutzt werden", text)
        self.assertNotIn("kostenlos", text)          # E1: L1 ohne "kostenlos"

    def test_abschnitte_lesen(self):
        intro, sections = fr.parse_notices("Kopf\nZeile\n#### A – MIT\nText A\n\n"
                                           "#### B – Apache-2.0\nText B\n")
        self.assertEqual(intro, "Kopf\nZeile")
        self.assertEqual(sections, [("A – MIT", "Text A"), ("B – Apache-2.0", "Text B")])
        choices = fr.notice_choices(intro, sections + [("A – BSD", "noch ein A")])
        self.assertEqual([name for name, _text in choices], [fr.UEBERSICHT, "A", "B", "A "])

    def test_fehlende_datei_ohne_absturz(self):
        self.assertEqual(fr.read_file("gibt_es_nicht.txt"), fr.DATEI_FEHLT % "gibt_es_nicht.txt")

    def _folder(self, files):
        folder = tempfile.mkdtemp(dir=_TMP)
        for rel, data in files.items():
            path = os.path.join(folder, *rel.split("/"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as handle:
                handle.write(data)
        return folder

    def test_erzeuger_bricht_bei_unbekannter_datei_ab(self):
        elf = b"\x7fELF" + b"\0" * 60
        folder = self._folder({"FISI-Lernplattform": elf,
                               "_internal/PIL/_imaging.so": elf,
                               "_internal/libunbekannt-aus-dem-nichts.so.1": elf,
                               "_internal/notiz.txt": b"kein Programm"})
        gen = lizenzen.Generator(folder)
        gen.run()
        self.assertEqual(gen.unassigned, ["_internal/libunbekannt-aus-dem-nichts.so.1"])
        self.assertEqual(gen.assigned["FISI-Lernplattform"], "pyinstaller")
        self.assertEqual(gen.assigned["_internal/PIL/_imaging.so"], "py:pillow")
        with self.assertRaises(SystemExit) as error:
            lizenzen.generate(folder, os.path.join(folder, "out.txt"), "0.62")
        self.assertIn("libunbekannt-aus-dem-nichts", str(error.exception))
        self.assertFalse(os.path.exists(os.path.join(folder, "out.txt")))

    def test_erzeuger_und_gegenprobe(self):
        elf = b"\x7fELF" + b"\0" * 60
        folder = self._folder({"FISI-Lernplattform": elf,
                               "_internal/PIL/_imaging.so": elf,
                               "_internal/fisi_symbole.otf": b"OTTO"})
        out = os.path.join(folder, "THIRD_PARTY_NOTICES.txt")
        gen, files = lizenzen.generate(folder, out, "0.62")
        self.assertEqual(len(files), 3)
        self.assertEqual(gen.unassigned, [])
        with open(out, encoding="utf-8") as handle:
            intro, sections = fr.parse_notices(handle.read())
        self.assertIn("Version 0.62", intro)
        titles = [fr.section_label(title) for title, _body in sections]
        self.assertIn("customtkinter 6.0.0", " ".join(titles))
        self.assertTrue(any(t.startswith("Python ") for t in titles))
        self.assertTrue(any(t.startswith("PyInstaller") for t in titles))
        self.assertTrue(lizenzen.counter_check(folder))

    def test_bau_ohne_readline(self):
        source = read("build.py")
        self.assertIn('"--exclude-module", "readline",', source)
        folder = tempfile.mkdtemp(dir=_TMP)
        build.check_no_readline(folder)
        open(os.path.join(folder, "libreadline.so.8"), "wb").close()
        with self.assertRaises(SystemExit):
            build.check_no_readline(folder)

    def test_appimage_fest_und_geprueft(self):
        workflow = read(".github", "workflows", "build.yml")
        self.assertNotIn("download/continuous/", workflow)
        self.assertIn("appimagetool/releases/download/1.9.1/", workflow)
        self.assertIn("type2-runtime/releases/download/20251108/runtime-x86_64", workflow)
        self.assertIn("sha256sum --check --strict", workflow)
        self.assertIn('"--runtime-file"', read("build.py"))

    def test_handy_liste_vorhanden(self):
        text = read("mobile", "lizenzen_android.txt")
        intro, sections = fr.parse_notices(text)
        self.assertIn("pruefung/lizenzen_android.py", intro)
        titles = " ".join(title for title, _body in sections)
        for name in ("AndroidX", "Kotlin", "KaTeX", "flet 1.0.1", "Python 3.14",
                     "Flutter-Sammlung, Teil 1 von", "OpenSSL", "SQLite"):
            self.assertIn(name, titles)
        self.assertNotRegex(text, r"\d{4}-\d{2}-\d{2} ")     # kein Erzeugungsdatum


# ============================================================================
#  ERSTSTART-HINWEIS
# ============================================================================

class ErststartTest(unittest.TestCase):

    def setUp(self):
        settings = load_settings()
        settings.pop(fr.HINWEIS_KEY, None)
        save_settings(settings)

    def test_bis_verstanden_faellig(self):
        self.assertTrue(fr.notice_due())
        self.assertTrue(fr.notice_due({"rundgang_gesehen": "2026-01-01"}))   # Altnutzer (E6)
        fr.mark_notice_seen()
        self.assertFalse(fr.notice_due())
        self.assertTrue(load_settings()[fr.HINWEIS_KEY])

    def test_nicht_in_sicherung_und_abgleich(self):
        for name in ("fisi_sicherung.py", "fisi_sync.py", "fisi_core.py"):
            self.assertNotIn("hinweis_rechtliches", read(name), name)
            self.assertNotIn("HINWEIS_KEY", read(name), name)


# ============================================================================
#  OBERFLAECHE
# ============================================================================

def _big_notices_folder():
    """Ordner mit THIRD_PARTY_NOTICES.txt in Handy-Groesse (die groesste Datei)."""
    folder = tempfile.mkdtemp(dir=_TMP)
    shutil.copy(ANDROID_LIST, os.path.join(folder, fr.NOTICES_FILE))
    shutil.copy(os.path.join(HERE, "LICENSE.txt"), os.path.join(folder, fr.LICENSE_FILE))
    return folder


@unittest.skipUnless(_tk_ok(), "kein Display")
class PcTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import customtkinter as ctk
        import app_gui
        cls.app_gui = app_gui
        fh.mark_tour_seen()
        app_gui.UpdateController.auto_check = lambda self: None
        app_gui.SyncController.auto_start = lambda self: None
        cls.folder = _big_notices_folder()
        cls.old_dirs = fr._search_dirs
        fr._search_dirs = lambda: [cls.folder]
        cls.root = ctk.CTk()
        cls.root.geometry("1360x900+0+0")
        cls.app = app_gui.FISIApp(cls.root)
        cls.pump()

    @classmethod
    def tearDownClass(cls):
        fr._search_dirs = cls.old_dirs
        for job in cls.root.tk.splitlist(cls.root.tk.call("after", "info")):
            cls.root.tk.call("after", "cancel", job)
        cls.root.destroy()

    @classmethod
    def pump(cls, times=8):
        for _ in range(times):
            cls.root.update_idletasks()
            cls.root.update()

    def test_a_erststart_leiste(self):
        settings = load_settings()
        settings.pop(fr.HINWEIS_KEY, None)
        save_settings(settings)
        self.app.show_view("dashboard")
        bar = self.app.maybe_show_notice()
        self.pump()
        self.assertIsNotNone(bar)
        view = self.app.views["dashboard"]
        self.assertTrue(bar.winfo_ismapped())
        self.assertLess(bar.winfo_y(), view.hero.winfo_y())
        buttons = [w for w in bar.winfo_children()
                   if getattr(w, "_caption", None) is not None or hasattr(w, "set_text")]
        self.assertTrue(buttons)
        buttons[0].command()
        self.pump()
        self.assertFalse(fr.notice_due())
        self.assertIsNone(self.app.maybe_show_notice())

    def test_b_fenster_lizenz_und_fremd_unter_einer_sekunde(self):
        self.app.show_view("settings")
        self.pump()
        view = self.app.views["settings"]
        for kind in ("lizenz", "fremd"):
            started = time.perf_counter()
            window = view.show_legal(kind)
            self.pump(2)
            seconds = time.perf_counter() - started
            print("Fenster %s offen nach %.3f s" % (kind, seconds))
            self.assertLess(seconds, 1.0, kind)
            text = window.text.get("1.0", "end")
            if kind == "lizenz":
                self.assertIn(fr.COPYRIGHT, text)
            else:
                self.assertIn("Hinweise zu Fremdbestandteilen", text)
                names = list(window.choices)
                self.assertEqual(names[0], fr.UEBERSICHT)
                started = time.perf_counter()
                window.listbox.selection_clear(0, "end")
                window.listbox.selection_set("end")
                window.listbox.event_generate("<<ListboxSelect>>")
                self.pump(2)
                print("Abschnitt %r nach %.3f s" % (names[-1], time.perf_counter() - started))
                self.assertIn("vulkan", window.text.get("1.0", "end").lower())
                self.assertLess(time.perf_counter() - started, 1.0)
            # zweiter Klick holt dasselbe Fenster nach vorn
            self.assertIs(view.show_legal(kind), window)
            window.destroy()
            self.pump()


@unittest.skipUnless(_flet_ok(), "flet fehlt")
class HandyTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import flet as ft
        sys.path.insert(1, os.path.join(HERE, "mobile", "src"))
        import main
        cls.ft, cls.main = ft, main
        cls.pushed = pushed = []

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

            def push(self, crumbs, content):
                pushed.append((crumbs, content))

        cls.app = FakeApp()
        cls.folder = _big_notices_folder()
        cls.old_dirs = fr._search_dirs
        fr._search_dirs = lambda: [cls.folder]

    @classmethod
    def tearDownClass(cls):
        fr._search_dirs = cls.old_dirs

    def test_seiten_unter_einer_sekunde(self):
        screen = self.main.SCREEN_CLASSES["settings"](self.app)
        started = time.perf_counter()
        screen.show_license()
        print("Handy Lizenz nach %.3f s" % (time.perf_counter() - started))
        crumbs, _content = self.pushed[-1]
        self.assertEqual(crumbs, fr.CRUMB_LIZENZ)
        started = time.perf_counter()
        screen.show_notices()
        seconds = time.perf_counter() - started
        print("Handy Fremdbestandteile nach %.3f s" % seconds)
        self.assertLess(seconds, 1.0)
        self.assertEqual(self.pushed[-1][0], fr.CRUMB_FREMD)
        menu, body = screen.notices_menu, screen.notices_body
        self.assertEqual(menu.value, fr.UEBERSICHT)
        self.assertGreater(len(menu.options), 40)
        menu.value = menu.options[-1].key
        menu.on_select(type("E", (), {"control": menu})())
        self.assertIn("vulkan", body.value.lower())

    def test_erststart_leiste(self):
        settings = load_settings()
        settings.pop(fr.HINWEIS_KEY, None)
        save_settings(settings)
        self.app.screens["dashboard"] = self.main.SCREEN_CLASSES["dashboard"](self.app)
        holder = self.app.maybe_show_notice()
        self.assertTrue(holder.visible)
        self.assertIs(self.app.screens["dashboard"].root.controls[0], holder)
        button = holder.content.content.controls[1].controls[0]
        button._handler(None)
        self.assertFalse(holder.visible)
        self.assertFalse(fr.notice_due())


if __name__ == "__main__":
    unittest.main(verbosity=2)
