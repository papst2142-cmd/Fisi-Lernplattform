#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer 0.59.1 (Linux):
  * .deb-Paket: Symbole in 48/64/128/256/512 px, Depends: libxft2, libxss1,
    StartupWMClass im Menueeintrag. Gebaut wird mit build.package_deb aus
    einem kleinen Platzhalter-Programmordner (nur wo dpkg-deb vorhanden ist).
  * Fensterklasse: className "fisi-lernplattform" ergibt die Klasse
    "Fisi-lernplattform" - genau der Wert in StartupWMClass (braucht ein
    Display, sonst uebersprungen).
  * Desktop-Verknuepfung (fisi_verknuepfung) mit derselben StartupWMClass.
  * Nachtrag 0.59.1: Paketbeschreibung rein ASCII (das App-Zentrum von
    Ubuntu 26.04 zeigte Umlaute einer lokalen .deb als "?"), Comment= im
    Menueeintrag mit Umlauten (UTF-8 ohne BOM, desktop-file-validate),
    SingleMainWindow=true; die Desktop-Verknuepfung bleibt ASCII.
  * Release-Text: Der Linux-Absatz steht unter "### Herunterladen", das
    Update-Fenster zeigt ihn nicht (Schritt aus build.yml wird ausgefuehrt,
    nur wo bash vorhanden ist).

Start:  python test_linux_paket.py
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build  # noqa: E402
import fisi_update as fu  # noqa: E402
import fisi_verknuepfung as fsc  # noqa: E402

EXPECTED_WM_CLASS = "Fisi-lernplattform"


def _tk_ok():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:  # noqa: BLE001
        return False


class DesktopEintragTest(unittest.TestCase):
    def test_klassenname_aus_paketname(self):
        self.assertEqual(build.WM_CLASS, EXPECTED_WM_CLASS)

    def test_menueeintrag_hat_startupwmclass(self):
        text = build.DESKTOP_ENTRY.format(exec="fisi-lernplattform", wm_class=build.WM_CLASS)
        self.assertIn("\nStartupWMClass=%s\n" % EXPECTED_WM_CLASS, text)
        self.assertIn("\nIcon=fisi-lernplattform\n", text)

    def test_verknuepfung_hat_startupwmclass(self):
        text = fsc.entry_text("/opt/fisi-lernplattform/FISI-Lernplattform", "fisi-lernplattform")
        self.assertIn("\nStartupWMClass=%s\n" % EXPECTED_WM_CLASS, text)
        self.assertIn(fsc.MARKER, text)
        self.assertEqual(text.count("StartupWMClass="), 1)

    def test_menueeintrag_umlaute_und_einzelfenster(self):
        text = build.DESKTOP_ENTRY.format(exec="fisi-lernplattform", wm_class=build.WM_CLASS)
        self.assertIn("\nComment=Lernprogramm f\u00fcr die Pr\u00fcfungsvorbereitung zum "
                      "Fachinformatiker (Schwerpunkt Systemintegration)\n", text)
        # Ab 0.61: neuer Name, FISI bleibt Suchwort (F3)
        self.assertIn("\nName=Fachinformatiker Lernplattform\n", text)
        self.assertIn("\nKeywords=Fachinformatiker;FI;FISI;", text)
        self.assertIn("\nSingleMainWindow=true\n", text)
        self.assertEqual(text.count("SingleMainWindow="), 1)

    def test_verknuepfung_bleibt_ascii(self):
        text = fsc.entry_text("/opt/fisi-lernplattform/FISI-Lernplattform", "fisi-lernplattform")
        self.assertIn("Comment=Lernprogramm fuer die Pruefungsvorbereitung", text)
        self.assertIn("\nName=Fachinformatiker Lernplattform\n", text)
        self.assertNotIn("SingleMainWindow", text)

    def test_programm_nutzt_denselben_klassennamen(self):
        with open(os.path.join(HERE, "app_gui.py"), encoding="utf-8") as handle:
            source = handle.read()
        match = re.search(r'^LINUX_CLASS_NAME = "([^"]+)"', source, re.M)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), build.PACKAGE_NAME)
        # Tk schreibt den ersten Buchstaben der Klasse gross
        self.assertEqual(match.group(1)[:1].upper() + match.group(1)[1:], EXPECTED_WM_CLASS)


@unittest.skipUnless(shutil.which("dpkg-deb") and shutil.which("dpkg"),
                     "dpkg-deb fehlt (nur unter Debian/Ubuntu)")
class DebPaketTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.mkdtemp(prefix="fisi_deb_")
        cls.old = (build.DIST, build.OUTPUT, build.ROOT)
        dist = os.path.join(cls.folder, "dist")
        program = os.path.join(dist, build.APP_NAME)
        os.makedirs(program)
        with open(os.path.join(program, build.APP_NAME), "w") as handle:
            handle.write("#!/bin/sh\necho Platzhalter\n")
        os.chmod(os.path.join(program, build.APP_NAME), 0o755)
        # Ab 0.62: Lizenzdateien legt build_app neben das Programm
        for name in build.LEGAL_FILES:
            with open(os.path.join(program, name), "w", encoding="utf-8") as handle:
                handle.write("Platzhalter %s\n" % name)
        root = os.path.join(cls.folder, "root")
        os.makedirs(root)
        shutil.copy(os.path.join(HERE, "icon.png"), os.path.join(root, "icon.png"))
        build.DIST, build.OUTPUT, build.ROOT = dist, os.path.join(cls.folder, "out"), root
        os.makedirs(build.OUTPUT)
        quiet = build.run
        build.run = lambda command, **kwargs: subprocess.run(
            command, check=True, capture_output=True, **kwargs)
        try:
            build.package_deb("9.99")
        finally:
            build.run = quiet
        cls.deb = [os.path.join(build.OUTPUT, name) for name in os.listdir(build.OUTPUT)][0]

    @classmethod
    def tearDownClass(cls):
        build.DIST, build.OUTPUT, build.ROOT = cls.old
        shutil.rmtree(cls.folder, ignore_errors=True)

    def _field(self, name):
        return subprocess.run(["dpkg-deb", "-f", self.deb, name], check=True,
                              capture_output=True, text=True).stdout.strip()

    def test_lizenz_und_hinweise(self):
        # Ab 0.62: Lizenz und Hinweise im Programmordner und unter /usr/share/doc
        listing = subprocess.run(["dpkg-deb", "-c", self.deb], check=True,
                                 capture_output=True, text=True).stdout
        for path in ("./opt/fisi-lernplattform/LICENSE.txt",
                     "./opt/fisi-lernplattform/THIRD_PARTY_NOTICES.txt",
                     "./usr/share/doc/fisi-lernplattform/LICENSE.txt",
                     "./usr/share/doc/fisi-lernplattform/THIRD_PARTY_NOTICES.txt",
                     "./usr/share/doc/fisi-lernplattform/copyright"):
            self.assertIn(path + "\n", listing)

    def test_depends(self):
        self.assertEqual(self._field("Depends"), "libxft2, libxss1")
        self.assertEqual(self._field("Version"), "9.99")

    def test_symbole_in_allen_groessen(self):
        from PIL import Image
        target = os.path.join(self.folder, "entpackt")
        subprocess.run(["dpkg-deb", "-x", self.deb, target], check=True)
        for size in (48, 64, 128, 256, 512):
            path = os.path.join(target, "usr", "share", "icons", "hicolor",
                                "%dx%d" % (size, size), "apps", "fisi-lernplattform.png")
            self.assertTrue(os.path.exists(path), path)
            with Image.open(path) as image:
                self.assertEqual(image.size, (size, size))
                self.assertEqual(image.mode, "RGBA")
        desktop = os.path.join(target, "usr", "share", "applications", "fisi-lernplattform.desktop")
        with open(desktop, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("\nStartupWMClass=%s\n" % EXPECTED_WM_CLASS, text)
        self.assertIn("\nExec=fisi-lernplattform\n", text)

    def test_paketbeschreibung_rein_ascii(self):
        # Kein Byte ueber 127: Das App-Zentrum (Ubuntu 26.04) zeigte Umlaute
        # der Paketbeschreibung einer lokalen .deb als "?" (Test B 0.59.1),
        # obwohl dpkg -s sie richtig anzeigte.
        self.assertEqual(self._field("Description").splitlines()[:2], [
            "Pruefungsvorbereitung Fachinformatiker (Schwerpunkt Systemintegration)",
            " Karteikarten, Pruefungstrainer, AP1-/AP2-Szenarien, Testprojekte und"])
        target = os.path.join(self.folder, "steuerung")
        subprocess.run(["dpkg-deb", "-e", self.deb, target], check=True)
        with open(os.path.join(target, "control"), "rb") as handle:
            raw = handle.read()
        self.assertTrue(all(byte < 128 for byte in raw), "Nicht-ASCII in control")

    def test_umlaute_im_menueeintrag(self):
        target = os.path.join(self.folder, "umlaute")
        subprocess.run(["dpkg-deb", "-x", self.deb, target], check=True)
        desktop = os.path.join(target, "usr", "share", "applications", "fisi-lernplattform.desktop")
        with open(desktop, "rb") as handle:
            raw = handle.read()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), "BOM im Menueeintrag")
        text = raw.decode("utf-8")
        self.assertIn("\nComment=Lernprogramm f\u00fcr die Pr\u00fcfungsvorbereitung", text)
        self.assertIn("\nSingleMainWindow=true\n", text)

    def test_menueeintrag_gueltig(self):
        tool = shutil.which("desktop-file-validate")
        if not tool:
            self.skipTest("desktop-file-validate fehlt")
        target = os.path.join(self.folder, "pruefen")
        subprocess.run(["dpkg-deb", "-x", self.deb, target], check=True)
        desktop = os.path.join(target, "usr", "share", "applications", "fisi-lernplattform.desktop")
        result = subprocess.run([tool, desktop], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


@unittest.skipUnless(sys.platform.startswith("linux") and _tk_ok(), "braucht Linux mit Display")
class FensterklasseTest(unittest.TestCase):
    def test_wm_class(self):
        import tkinter
        root = tkinter.Tk(className="fisi-lernplattform")
        try:
            self.assertEqual(root.winfo_class(), EXPECTED_WM_CLASS)
        finally:
            root.destroy()


@unittest.skipUnless(shutil.which("bash"), "bash fehlt")
class ReleaseTextTest(unittest.TestCase):
    """Fuehrt den Schritt "Pruefsummen (SHA-256) in den Release-Text" aus
    build.yml mit einem Platzhalter-Ordner aus."""

    STEP = "Pruefsummen (SHA-256) in den Release-Text"

    def _script(self):
        with open(os.path.join(HERE, ".github", "workflows", "build.yml"), encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        start = next(i for i, line in enumerate(lines) if line.strip() == "- name: " + self.STEP)
        run = next(i for i in range(start, len(lines)) if lines[i].strip() == "run: |")
        indent = len(lines[run + 1]) - len(lines[run + 1].lstrip())
        body = []
        for line in lines[run + 1:]:
            if line.strip() and len(line) - len(line.lstrip()) < indent:
                break
            body.append(line[indent:])
        return "\n".join(body) + "\n"

    def _release_text(self, version):
        folder = tempfile.mkdtemp(prefix="fisi_release_")
        try:
            os.makedirs(os.path.join(folder, "installer"))
            for name in ("fisi-lernplattform_%s_amd64.deb" % version, "x.exe"):
                with open(os.path.join(folder, "installer", name), "w") as handle:
                    handle.write(name)
            with open(os.path.join(folder, "versionshinweise.md"), "w", encoding="utf-8") as handle:
                handle.write("Kurz.\n\n- **Neu:** etwas\n")
            with open(os.path.join(folder, "build.py"), "w", encoding="utf-8") as handle:
                handle.write("def app_version():\n    return %r\n" % version)
            subprocess.run(["bash", "-e", "-c", self._script()], cwd=folder, check=True,
                           capture_output=True)
            with open(os.path.join(folder, "versionshinweise.md"), encoding="utf-8") as handle:
                return handle.read()
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_linux_absatz_unter_herunterladen(self):
        text = self._release_text("0.59.1")
        head, _sep, tail = text.partition("### Herunterladen")
        self.assertTrue(tail)
        self.assertIn("sudo apt install ./fisi-lernplattform_0.59.1_amd64.deb", tail)
        self.assertIn("sudo apt remove fisi-lernplattform", tail)
        self.assertIn("mv ~/.local/share/applications/fisi-lernplattform.desktop "
                      "~/fisi-lernplattform.desktop.alt", tail)
        self.assertIn("**Update-Fenster:**", tail)
        self.assertLess(tail.index("sudo apt install"), tail.index("### Prüfsummen (SHA-256)"))
        self.assertNotIn("apt", head)

    def test_update_fenster_zeigt_ihn_nicht(self):
        text = self._release_text("0.59.1")
        notes = fu.plain_notes(text)
        self.assertEqual(notes, "Kurz.\n• Neu: etwas")
        self.assertNotIn("apt", notes)

    def test_hinweis_update_fenster_nur_bei_0591(self):
        self.assertNotIn("**Update-Fenster:**", self._release_text("0.60"))
        self.assertIn("fisi-lernplattform_0.60_amd64.deb", self._release_text("0.60"))


@unittest.skipUnless(shutil.which("bash") and shutil.which("sha256sum") and shutil.which("stat"),
                     "bash/sha256sum fehlt")
class VorabTextTest(unittest.TestCase):
    """Nachtrag 0.59.1: Schritt "Dateien und Text der Testversion (Linux und
    Handy)" aus build.yml mit Platzhalter-Dateien ausfuehren."""

    STEP = "Dateien und Text der Testversion (Linux und Handy)"

    def _run(self, names, zweck="VM und TalkBack"):
        script = ReleaseTextTest._script(self).replace("${{ github.ref_name }}", "version-0591")
        folder = tempfile.mkdtemp(prefix="fisi_vorab_")
        try:
            os.makedirs(os.path.join(folder, "neu"))
            for name in names:
                with open(os.path.join(folder, "neu", name), "w") as handle:
                    handle.write(name * 3)
            with open(os.path.join(folder, "build.py"), "w", encoding="utf-8") as handle:
                handle.write("def app_version():\n    return '0.59'\n")
            env = dict(os.environ, VORAB="0.59.1-test1", ZWECK=zweck,
                       GITHUB_SHA="0123456789abcdef")
            result = subprocess.run(["bash", "-e", "-c", script], cwd=folder, env=env,
                                    capture_output=True, text=True)
            text = ""
            if os.path.exists(os.path.join(folder, "vorab.md")):
                with open(os.path.join(folder, "vorab.md"), encoding="utf-8") as handle:
                    text = handle.read()
            files = sorted(os.listdir(os.path.join(folder, "vorab"))) \
                if os.path.isdir(os.path.join(folder, "vorab")) else []
            return result.returncode, text, files
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_nur_deb_und_apk(self):
        deb, apk = "fisi-lernplattform_0.59_amd64.deb", "FISI-Lernplattform-0.59-Android.apk"
        code, text, files = self._run([deb, "FISI-Lernplattform-0.59-x86_64.AppImage", apk])
        self.assertEqual(code, 0)
        self.assertEqual(files, sorted([deb, apk]))
        self.assertTrue(text.startswith("**Nur zum Testen, nicht ver\u00f6ffentlichen.**"))
        self.assertIn("(Stand `0123456`)", text)
        self.assertIn("Getestet wird: VM und TalkBack", text)
        import hashlib
        digest = hashlib.sha256((deb * 3).encode()).hexdigest()
        self.assertIn("- `%s` \u00b7 %d Bytes \u00b7 `%s`" % (deb, len(deb) * 3, digest), text)
        self.assertNotIn("AppImage", text)

    def test_fehlende_apk_bricht_ab(self):
        code, _text, _files = self._run(["fisi-lernplattform_0.59_amd64.deb"])
        self.assertNotEqual(code, 0)


OLD_SHORTCUT_061 = """[Desktop Entry]
Type=Application
Name=FISI Lernplattform
Comment=Lernprogramm fuer die Umschulung zum Fachinformatiker Systemintegration
Exec="/home/nico/Programme/FISI Lernplattform.AppImage"
Icon=/home/nico/.local/share/icons/hicolor/512x512/apps/fisi-lernplattform.png
Terminal=false
Categories=Education;
Keywords=FISI;IHK;Lernen;Netzwerk;Subnetting;RAID;
StartupWMClass=Fisi-lernplattform
X-FISI-Verknuepfung=true
"""


class VerknuepfungErneuern(unittest.TestCase):
    """Ab 0.61 (F4/E1): eigene Desktop-Verknuepfung mit dem Namen bis 0.60.1
    wird beim Start still erneuert - nur die Anzeigezeilen."""

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.path = os.path.join(self.folder, fsc.FILE_NAME)
        self.old_desktop = os.environ.pop("XDG_CURRENT_DESKTOP", None)   # kein gio

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)
        if self.old_desktop is not None:
            os.environ["XDG_CURRENT_DESKTOP"] = self.old_desktop

    def _write(self, text, mode=0o755):
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.chmod(self.path, mode)

    def _read(self):
        with open(self.path, encoding="utf-8") as handle:
            return handle.read()

    def test_a_eigene_alte_wird_erneuert(self):
        self._write(OLD_SHORTCUT_061)
        self.assertEqual(fsc.renew_own("appimage", self.folder), self.path)
        text = self._read()
        self.assertIn("\nName=Fachinformatiker Lernplattform\nGenericName=Lernprogramm\n", text)
        self.assertIn("\nComment=Lernprogramm fuer die Pruefungsvorbereitung zum Fachinformatiker "
                      "(Schwerpunkt Systemintegration)\n", text)
        self.assertIn("\nKeywords=Fachinformatiker;FI;FISI;IHK;", text)
        # Startbefehl, Symbol und Merker Byte fuer Byte gleich
        for line in OLD_SHORTCUT_061.splitlines():
            if line.split("=", 1)[0] not in fsc.DISPLAY_KEYS:
                self.assertIn("\n" + line + "\n", "\n" + text)
        self.assertEqual(text.count("Exec="), 1)
        self.assertEqual(os.stat(self.path).st_mode & 0o777, 0o755)
        self.assertFalse(os.path.exists(self.path + ".tmp"))

    def test_b_fremde_datei_bleibt(self):
        foreign = OLD_SHORTCUT_061.replace(fsc.MARKER + "\n", "")
        self._write(foreign)
        self.assertIsNone(fsc.renew_own("appimage", self.folder))
        self.assertEqual(self._read(), foreign)

    def test_c_schon_neu_bleibt(self):
        self._write(OLD_SHORTCUT_061)
        fsc.renew_own("deb", self.folder)
        once = self._read()
        self.assertIsNone(fsc.renew_own("deb", self.folder))
        self.assertEqual(self._read(), once)

    def test_f_eigene_umbenannte_bleibt(self):
        renamed = OLD_SHORTCUT_061.replace("Name=FISI Lernplattform", "Name=Mein Lernen")
        self._write(renamed)
        self.assertIsNone(fsc.renew_own("deb", self.folder))
        self.assertEqual(self._read(), renamed)

    def test_d_ohne_verknuepfung_oder_ausserhalb_linux(self):
        self.assertIsNone(fsc.renew_own("appimage", self.folder))
        self.assertFalse(os.path.exists(self.path))
        self._write(OLD_SHORTCUT_061)
        self.assertIsNone(fsc.renew_own("windows", self.folder))
        self.assertEqual(self._read(), OLD_SHORTCUT_061)

    def test_e_erneuern_vor_dem_rundgang(self):
        # Container-Test T6: beim ersten Start (Rundgang offen) wartete die
        # Erneuerung bis zum Schliessen des Rundgangs - jetzt laeuft sie vorher
        with open(os.path.join(HERE, "app_gui.py"), encoding="utf-8") as handle:
            source = handle.read()
        start = source.index("    def maybe_start_tour(self):")
        body = source[start:source.index("\n    def ", start + 10)]
        self.assertIn("fsc.renew_own()", body)
        self.assertLess(body.index("fsc.renew_own()"), body.index("fh.tour_due("))


if __name__ == "__main__":
    unittest.main(verbosity=2)
