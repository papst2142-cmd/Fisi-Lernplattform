#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Namens-Waechter (ab 0.61, Plan 0.61 Abschnitt 4)
=================================================

Ab 0.61 heisst das Programm sichtbar "Fachinformatiker Lernplattform". Alles,
woran ein Programm etwas wiedererkennt, behaelt dagegen seinen alten Namen:
Datenordner, Datenbank, Exe, Installer-Kennung (AppId), Paketnamen,
Android-Paket, Sicherungsformat, Repository, Release-Dateinamen, Schalter.
Dieser Test haelt diese Namen fest. Wird er rot, wurde ein technischer Name
geaendert - das kostet Anwender den Lernstand, erzeugt eine zweite
Installation oder verhindert Updates. Dann die Aenderung zuruecknehmen, nicht
den Test anpassen.

Dazu Gegenproben: die neuen Anzeigenamen sind gesetzt, und in den sichtbaren
Texten steht nicht mehr "FISI Lernplattform".

Laeuft ohne Fenster auf Linux, Windows und macOS (CI: alle drei).
Start:  python test_namen.py
"""

import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build  # noqa: E402
import fisi_core  # noqa: E402
import fisi_haenger  # noqa: E402
import fisi_sicherung  # noqa: E402
import fisi_update  # noqa: E402
import fisi_verknuepfung  # noqa: E402


def read(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as handle:
        return handle.read()


class TechnischeNamenBleiben(unittest.TestCase):
    """Diese Werte duerfen sich NIE aendern (Grund steht jeweils dabei)."""

    def test_datenordner_und_datenbank(self):
        # Lernstand, Einstellungen, Sperre und Protokolle liegen dort
        self.assertEqual(fisi_core.DATA_DIR_NAME, "FISI-Lernplattform")
        self.assertEqual(fisi_core.DATA_DIR_NAME_LINUX, "fisi-lernplattform")
        self.assertEqual(fisi_core.DB_FILE_NAME, "fisi_lernplattform.db")
        self.assertEqual(os.path.basename(fisi_core.LEGACY_DB_PATH), "fisi_lernplattform.db")

    def test_datenordner_je_system(self):
        home = os.path.join("H", "nutzer")
        self.assertEqual(fisi_core.data_dir("nt", {"APPDATA": "AD"}, home),
                         os.path.join("AD", "FISI-Lernplattform"))
        self.assertEqual(fisi_core.data_dir("nt", {}, home),
                         os.path.join(home, "FISI-Lernplattform"))
        self.assertEqual(fisi_core.data_dir("darwin", {}, home),
                         os.path.join(home, "Library", "Application Support",
                                      "FISI-Lernplattform"))
        self.assertEqual(fisi_core.data_dir("linux", {}, home),
                         os.path.join(home, ".local", "share", "fisi-lernplattform"))
        self.assertEqual(fisi_core.data_dir("linux", {"XDG_DATA_HOME": "X"}, home),
                         os.path.join("X", "fisi-lernplattform"))

    def test_datenbankpfad_auf_diesem_system(self):
        # resolve_db_path() ohne FISI_DB_PATH: Datenordner dieses Systems
        old = {key: os.environ.get(key) for key in ("FISI_DB_PATH", "APPDATA", "XDG_DATA_HOME")}
        with tempfile.TemporaryDirectory() as folder:
            try:
                os.environ.pop("FISI_DB_PATH", None)
                os.environ["APPDATA"] = folder
                os.environ["XDG_DATA_HOME"] = folder
                if os.path.exists(fisi_core.LEGACY_DB_PATH):
                    self.skipTest("Datenbank neben dem Programm (alte Installation)")
                path = fisi_core.resolve_db_path()
                expected = os.path.join(fisi_core.data_dir(), "fisi_lernplattform.db")
            finally:
                for key, value in old.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
            self.assertEqual(path, expected)
            self.assertIn(os.path.basename(os.path.dirname(path)),
                          ("FISI-Lernplattform", "fisi-lernplattform"))

    def test_handy_nutzt_denselben_datenbanknamen(self):
        text = read(os.path.join("mobile", "src", "main.py"))
        self.assertIn('os.environ["FISI_DB_PATH"] = os.path.join(os.environ["FLET_APP_STORAGE_DATA"],', text)
        self.assertRegex(text, r"FLET_APP_STORAGE_DATA\"\],\s+DB_FILE_NAME\)")

    def test_bau_namen(self):
        # Exe, .app, Prozessname (pgrep), /opt-Inhalt
        self.assertEqual(build.APP_NAME, "FISI-Lernplattform")
        # .deb-Paket, /opt- und /usr/bin-Pfad, .desktop-Datei, Symbol
        self.assertEqual(build.PACKAGE_NAME, "fisi-lernplattform")
        # Fensterklasse = StartupWMClass (Dock-Symbol)
        self.assertEqual(build.WM_CLASS, "Fisi-lernplattform")
        source = read("build.py")
        # macOS: neue Bundle-Id = anderes Programm
        self.assertIn('"--osx-bundle-identifier", "de.fisi.lernplattform"', source)
        # Release-Dateien (Update erkennt Endungen, Update-Test den Setup-Namen)
        self.assertIn('"%s-%s-%s.AppImage" % (APP_NAME, version, machine)', source)
        self.assertIn('"%s-%s-macOS-%s.dmg" % (APP_NAME, version, arch)', source)
        self.assertIn('"%s_%s_%s.deb" % (PACKAGE_NAME, version, architecture)', source)
        self.assertIn('"Package: %s\\n"', source)

    def test_installer(self):
        iss = read("FISI-Lernplattform.iss")
        # Inno erkennt das Programm an der AppId: neue AppId = zweite Installation
        self.assertIn("\nAppId={{6B2E7B7B-6C1E-4E59-9C55-FISI-LERNPLATTFORM}}\n", iss)
        self.assertIn('\n#define MyAppExeName "FISI-Lernplattform.exe"\n', iss)
        self.assertIn("\nDefaultDirName={localappdata}\\Programs\\FISI-Lernplattform\n", iss)
        self.assertIn("\nOutputBaseFilename=FISI-Lernplattform-Setup-{#MyAppVersion}\n", iss)
        self.assertIn('Source: "dist\\FISI-Lernplattform\\*"', iss)
        # /FISIEXE: die laufende alte Version uebergibt ihn dem neuen Installer
        self.assertIn("{param:FISIEXE|}", iss)
        self.assertIn("/FISIEXE=", read("fisi_update.py"))

    def test_update(self):
        self.assertEqual(fisi_update.REPOSITORY, "papst2142-cmd/Fisi-Lernplattform")
        source = read("fisi_update.py")
        self.assertIn('sys.executable.startswith("/opt/fisi-lernplattform/")', source)
        self.assertIn('"FISI-Lernplattform-Update"', source)
        # Die installierte alte Version findet die neue Datei an diesen Mustern
        assets = [{"name": name} for name in (
            "FISI-Lernplattform-Setup-9.9.exe", "FISI-Lernplattform-9.9-x86_64.AppImage",
            "fisi-lernplattform_9.9_amd64.deb", "FISI-Lernplattform-9.9-macOS-arm64.dmg",
            "FISI-Lernplattform-9.9-macOS-intel.dmg", "FISI-Lernplattform-9.9-Android.apk")]
        expected = {("windows", None): "FISI-Lernplattform-Setup-9.9.exe",
                    ("appimage", None): "FISI-Lernplattform-9.9-x86_64.AppImage",
                    ("deb", None): "fisi-lernplattform_9.9_amd64.deb",
                    ("macos", "arm64"): "FISI-Lernplattform-9.9-macOS-arm64.dmg",
                    ("macos", "x86_64"): "FISI-Lernplattform-9.9-macOS-intel.dmg",
                    ("android", None): "FISI-Lernplattform-9.9-Android.apk"}
        for (kind, machine), name in expected.items():
            self.assertEqual(fisi_update.pick_asset(assets, kind, machine or "x86_64")["name"],
                             name, kind)

    def test_sicherung(self):
        # Formatkennung: Einspielen prueft art == KIND
        self.assertEqual(fisi_sicherung.KIND, "FISI-Sicherung")
        self.assertEqual(fisi_sicherung.BACKUP_EXT, ".fisisicherung")

    def test_linux(self):
        self.assertEqual(fisi_verknuepfung.FILE_NAME, "fisi-lernplattform.desktop")
        self.assertEqual(fisi_verknuepfung.ICON_NAME, "fisi-lernplattform")
        self.assertEqual(fisi_verknuepfung.DEB_COMMAND, "/usr/bin/fisi-lernplattform")
        self.assertEqual(fisi_verknuepfung.MARKER, "X-FISI-Verknuepfung=true")
        self.assertIn("\nStartupWMClass=Fisi-lernplattform\n", fisi_verknuepfung.ENTRY)
        self.assertIn('\nLINUX_CLASS_NAME = "fisi-lernplattform"\n', read("app_gui.py"))
        self.assertEqual(fisi_haenger.KILL_COMMAND,
                         "kill -USR1 $(pgrep -i -x -o fisi-lernplattf)")

    def test_schalter(self):
        # Dokumentierte Umgebungsvariablen werden weiter gelesen
        for name, files in (("FISI_DB_PATH", ("fisi_core.py",)),
                            ("FISI_XIM", ("fisi_eingabe.py",)),
                            ("FISI_SELFTEST", ("app_gui.py", "build.py")),
                            ("FISI_VORLADEN", ("app_gui.py",))):
            for name_file in files:
                self.assertIn(name, read(name_file), "%s in %s" % (name, name_file))

    def test_android(self):
        toml = read(os.path.join("mobile", "pyproject.toml"))
        # [project] name und org ergeben die Paketkennung
        # io.github.papst2142cmd.fisi_lernplattform - neue Kennung = zweite App
        self.assertRegex(toml, r'(?m)^name = "fisi-lernplattform"$')
        self.assertRegex(toml, r'(?m)^org = "io\.github\.papst2142cmd"$')
        workflow = read(os.path.join(".github", "workflows", "build.yml"))
        # Signaturschluessel: gleicher Alias, gleiches Secret
        self.assertIn("FLET_ANDROID_SIGNING_KEY_ALIAS: upload", workflow)
        self.assertIn("secrets.ANDROID_KEYSTORE_BASE64", workflow)
        self.assertIn('"installer_output/FISI-Lernplattform-${VERSION}-Android.apk"', workflow)


# Zeilen, die den alten Namen absichtlich nennen: Hinweis "frueherer Name" in
# LIESMICH/INSTALLER-ANLEITUNG, [InstallDelete] und Kommentare in der .iss,
# Erkennung der alten Linux-Verknuepfung (fisi_verknuepfung.OLD_NAME_LINE)
OLD_NAME_ALLOWED = (r"bis 0\.60\.1|^\s*;|^Type: (files|dirifempty); Name: \"\{auto"
                    r"|^OLD_NAME_LINE = ")


class NeueAnzeigenamen(unittest.TestCase):
    """Gegenprobe: die neuen Namen sind gesetzt (Nicos Entscheidung 08.10.2026)."""

    def test_konstanten(self):
        self.assertEqual(fisi_core.APP_DISPLAY_NAME, "Fachinformatiker Lernplattform")
        self.assertEqual(fisi_core.APP_SHORT_NAME, "FI Lernplattform")
        self.assertEqual(fisi_core.APP_LOGO_TEXT, "FI")
        self.assertEqual(build.DISPLAY_NAME, "Fachinformatiker Lernplattform")
        self.assertFalse(hasattr(fisi_core, "APP_NAME"),
                         "APP_NAME entfaellt: Anzeige und Datenordner sind getrennt")

    def test_herausgeber(self):
        self.assertIn("\nAppPublisher=Nico H\n", read("FISI-Lernplattform.iss"))
        self.assertEqual(build.PUBLISHER, "Nico H")
        self.assertIn('("CompanyName", PUBLISHER)', read("build.py"))
        self.assertIn('"Maintainer: Nico H <333448595+papst2142-cmd@users.noreply.github.com>\\n"',
                      read("build.py"))
        self.assertRegex(read(os.path.join("mobile", "pyproject.toml")), r'(?m)^company = "Nico H"$')

    def test_installer_entfernt_alte_verknuepfungen(self):
        # Ohne diese Zeilen haette der Nutzer nach dem Update zwei Startmenue-
        # Eintraege und zwei Desktop-Symbole (Plan 0.61, 7.1)
        iss = read("FISI-Lernplattform.iss")
        self.assertIn("\nUsePreviousGroup=no\n", iss)
        for line in ('Type: files; Name: "{autoprograms}\\FISI Lernplattform\\FISI Lernplattform.lnk"',
                     'Type: files; Name: "{autoprograms}\\FISI Lernplattform\\FISI Lernplattform '
                     'deinstallieren.lnk"',
                     'Type: dirifempty; Name: "{autoprograms}\\FISI Lernplattform"',
                     'Type: files; Name: "{autodesktop}\\FISI Lernplattform.lnk"'):
            self.assertIn("\n" + line + "\n", iss)

    def test_macos_app_pruefung(self):
        # M3: build.check_macos_bundle meldet falsche Namen in der Info.plist
        import plistlib
        with tempfile.TemporaryDirectory() as folder:
            app = os.path.join(folder, "FISI-Lernplattform.app")
            os.makedirs(os.path.join(app, "Contents"))
            plist = {"CFBundleDisplayName": "Fachinformatiker Lernplattform",
                     "CFBundleIdentifier": "de.fisi.lernplattform",
                     "CFBundleShortVersionString": "0.61"}
            with open(os.path.join(app, "Contents", "Info.plist"), "wb") as handle:
                plistlib.dump(plist, handle)
            build.check_macos_bundle(app, "0.61")
            plist["CFBundleIdentifier"] = "de.fachinformatiker.lernplattform"
            with open(os.path.join(app, "Contents", "Info.plist"), "wb") as handle:
                plistlib.dump(plist, handle)
            with self.assertRaises(SystemExit):
                build.check_macos_bundle(app, "0.61")

    def test_handy_beschriftung(self):
        self.assertRegex(read(os.path.join("mobile", "pyproject.toml")),
                         r'(?m)^product = "FI Lernplattform"$')

    def test_kein_alter_name_in_sichtbaren_texten(self):
        files = ["app_gui.py", "fisi_hilfe.py", "fisi_verknuepfung.py", "fisi_sicherung.py",
                 "fisi_diagnose.py", "fisi_pdf.py", "start.py", "build.py", "fisi_core.py",
                 "FISI-Lernplattform.iss", "LIESMICH.txt", "INSTALLER-ANLEITUNG.txt",
                 "GIT-ANLEITUNG.txt",
                 os.path.join("mobile", "src", "main.py"), os.path.join("mobile", "pyproject.toml"),
                 os.path.join(".github", "workflows", "build.yml")]
        for name in files:
            hits = ["%s:%d" % (name, number) for number, line in enumerate(read(name).splitlines(), 1)
                    if re.search(r"FISI Lernplattform|FISI LERNPLATTFORM", line)
                    and not re.search(OLD_NAME_ALLOWED, line)]
            self.assertEqual(hits, [], "alter Name in sichtbarem Text")
        self.assertNotIn("Lernplattform Projekt", read("build.py") + read("FISI-Lernplattform.iss"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
