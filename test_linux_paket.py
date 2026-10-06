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


if __name__ == "__main__":
    unittest.main(verbosity=2)
