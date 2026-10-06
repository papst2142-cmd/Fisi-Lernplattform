#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer 0.59.1: Fenster "Update verfuegbar" und Meldung nach
abgebrochener Passwortabfrage (.deb).
  * Groessenberechnung (update_window_size): "Normal" bleibt 560x500,
    groessere Schrift macht das Fenster breiter und hoeher, nie groesser als
    der nutzbare Bildschirm (auch bei einer kleinen Anzeige 540x1122).
  * Das echte Fenster in allen drei Schriftgroessen, auf einem normalen und
    einem kleinen Bildschirm: Knoepfe immer ganz sichtbar, Fenster passt auf
    den Bildschirm, laesst sich vergroessern (braucht ein Display).
  * Meldung nach abgebrochenem pkexec mit Terminal-Zeile und echtem
    Dateinamen.

Start:  python test_update_fenster.py
"""

import os
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_TMP = tempfile.mkdtemp(prefix="fisi_update_fenster_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "update_fenster.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(_TMP, "selbsttest.log"))

import fisi_update as fu  # noqa: E402

NOTES = ("Die Optionen sind übersichtlicher.\n\n"
         + "\n".join("- **Punkt %d:** ein längerer Satz, der in einem schmalen Fenster "
                     "mehrfach umbricht und so das Neuerungen-Feld füllt." % n
                     for n in range(1, 12))
         + "\n\n### Herunterladen\n\nLinux: sudo apt install ./x.deb\n")


def _tk_ok():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:  # noqa: BLE001
        return False


class MeldungTest(unittest.TestCase):
    def test_terminal_zeile_mit_dateiname(self):
        path = "/tmp/FISI-Lernplattform-Update/fisi-lernplattform_0.60_amd64.deb"
        text = fu.deb_cancel_message(path)
        self.assertTrue(text.startswith("Die automatische Installation wurde abgebrochen. "
                                        "Das Paket wurde zum manuellen Installieren geöffnet."))
        self.assertTrue(text.endswith("Im Terminal geht es mit: sudo apt install " + path))

    def test_leerzeichen_im_pfad(self):
        text = fu.deb_cancel_message("/tmp/mit leer/x.deb")
        self.assertTrue(text.endswith("sudo apt install '/tmp/mit leer/x.deb'"))

    def test_ablauf_unveraendert(self):
        # pkexec und xdg-open wie bisher, nur der Text kommt aus der Funktion
        with open(os.path.join(HERE, "fisi_update.py"), encoding="utf-8") as handle:
            source = handle.read()
        self.assertIn('subprocess.run(["pkexec", "apt-get", "install", "-y", path])', source)
        self.assertIn('subprocess.Popen(["xdg-open", path])\n'
                      '                return False, deb_cancel_message(path)', source)


@unittest.skipUnless(_tk_ok(), "kein Display")
class GroessenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app_gui
        cls.size = staticmethod(app_gui.update_window_size)

    def test_normal_wie_bisher(self):
        self.assertEqual(self.size(430, (1920, 1080))[0], (560, 500))

    def test_groessere_schrift_breiter(self):
        self.assertEqual(self.size(450, (1920, 1080), 1.15)[0], (644, 500))
        self.assertEqual(self.size(546, (1920, 1080), 1.3)[0], (728, 546))

    def test_kleine_anzeige(self):
        (width, height), minimum = self.size(625, (540, 1122), 1.3, min_height=430,
                                             min_width=472)
        self.assertEqual((width, height), (508, 625))
        self.assertEqual(minimum, (472, 430))

    def test_nie_groesser_als_bildschirm(self):
        (width, height), minimum = self.size(2000, (400, 300), 1.3, min_height=900,
                                             min_width=600)
        self.assertEqual((width, height), (368, 220))
        self.assertLessEqual(minimum[0], width)
        self.assertLessEqual(minimum[1], height)


@unittest.skipUnless(_tk_ok(), "kein Display")
class FensterTest(unittest.TestCase):
    """Das echte Fenster mit Platzhalter-Programm (kein Download)."""

    @classmethod
    def setUpClass(cls):
        import customtkinter as ctk
        cls.root = ctk.CTk()
        cls.root.geometry("300x200+0+0")

    @classmethod
    def tearDownClass(cls):
        import fisi_theme
        import fisi_widgets
        fisi_theme.apply_font_size("normal")
        fisi_widgets.apply_ui_scale(1.0)
        cls.root.destroy()

    def _open(self, size_id, installable, screen=None):
        import fisi_theme
        import fisi_widgets
        import app_gui
        fisi_theme.apply_font_size(size_id)
        fisi_widgets.apply_ui_scale(fisi_theme.font_factor())
        root = self.root
        fisi_widgets.setup_fonts(root)
        app = type("App", (), {"root": root})()
        info = fu.UpdateInfo("0.59.2", NOTES, fu.RELEASES_PAGE,
                             asset_name="x.deb" if installable else None,
                             asset_url="https://example.invalid/x.deb" if installable else None)
        original = fu.install_kind
        fu.install_kind = lambda: "deb"
        cls = app_gui.UpdateDialog
        saved = (cls.winfo_screenwidth, cls.winfo_screenheight)
        if screen:
            cls.winfo_screenwidth = lambda _self: screen[0]
            cls.winfo_screenheight = lambda _self: screen[1]
        try:
            dialog = cls(app, info)
            for _ in range(10):
                root.update()
                time.sleep(0.02)
        finally:
            fu.install_kind = original
            cls.winfo_screenwidth, cls.winfo_screenheight = saved
        return dialog

    def _check_buttons(self, dialog):
        bottom = dialog.winfo_rooty() + dialog.winfo_height()
        right = dialog.winfo_rootx() + dialog.winfo_width()
        for button in (dialog.btn_main, dialog.btn_later):
            self.assertTrue(button.winfo_ismapped())
            self.assertGreaterEqual(button.winfo_height(), 36)
            self.assertLessEqual(button.winfo_rooty() + button.winfo_height(), bottom)
            self.assertLessEqual(button.winfo_rootx() + button.winfo_width(), right)

    def test_alle_groessen(self):
        for size_id in ("normal", "gross", "sehr_gross"):
            for installable in (True, False):
                with self.subTest(size=size_id, installable=installable):
                    dialog = self._open(size_id, installable)
                    try:
                        self._check_buttons(dialog)
                        self.assertEqual(dialog.resizable(), (True, True))
                        if size_id == "normal":
                            self.assertEqual((dialog.winfo_width(), dialog.winfo_height()),
                                             (560, 500))
                    finally:
                        dialog.destroy()

    def test_kleine_anzeige_540x1122(self):
        for size_id in ("normal", "sehr_gross"):
            with self.subTest(size=size_id):
                dialog = self._open(size_id, False, screen=(540, 1122))
                try:
                    self._check_buttons(dialog)
                    self.assertLessEqual(dialog.winfo_width(), 540 - 32)
                    self.assertLessEqual(dialog.winfo_height(), 1122 - 80)
                finally:
                    dialog.destroy()

    def test_mindestgroesse_knoepfe_sichtbar(self):
        dialog = self._open("sehr_gross", True)
        try:
            width, height = dialog.wm_minsize()
            dialog.wm_geometry("%dx%d" % (width, height))
            for _ in range(10):
                self.root.update()
                time.sleep(0.02)
            self._check_buttons(dialog)
        finally:
            dialog.destroy()


if __name__ == "__main__":
    unittest.main(verbosity=2)
