#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests 0.63.2 A13 (S5c): erstes Oeffnen des Rechners ohne Vorladen.

Plan 0.63.2 (S5 Abschnitt 4, Messung M1): Das erste Oeffnen war unter
Windows 170 ms langsamer als erlaubt. Ursache: Waehrend des Aufbaus war der
sichtbare Bereich der Ansicht 1 px breit, der seitliche Schieberegler wurde
ein- und ausgeblendet, und jede dieser Runden ordnete die ganze Seite neu
an; dazu baute das Oeffnen den (unsichtbaren) Rechen-Trainer mit.
Ab 0.63.2:
  * die Rechner-Ansicht hat ihre Groesse schon, bevor die Karten entstehen
    (die Subnetting-Karte entsteht in einem sichtbaren Bereich mit der
    echten Breite)
  * der Trainer entsteht erst beim ersten Wechsel auf "Trainer" bzw. beim
    Vorladen (prepare), nicht beim Oeffnen
  * Wechsel Rechner -> Trainer -> Rechner zeigt jeweils genau einen Teil
Gegen e0f9c7e rot (Groesse beim Aufbau 1 px, Trainer beim Oeffnen gebaut).

Start:  xvfb-run -a python test_rechner_oeffnen_a13.py
"""

import os
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _display_available():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:
        return False


HAS_DISPLAY = _display_available()
# schmales Fenster: USV-Spalten stehen untereinander (A6)
FENSTER_SCHMAL = (900, 700)


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige")
class RechnerOeffnenTest(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="fisi a13 ")
        self._env = {k: os.environ.get(k) for k in
                     ("FISI_DB_PATH", "FISI_SELFTEST", "HOME", "FISI_VORLADEN")}
        os.environ["FISI_DB_PATH"] = os.path.join(self.folder, "test.db")
        os.environ["FISI_SELFTEST"] = os.path.join(self.folder, "log.txt")
        os.environ["HOME"] = self.folder
        os.environ["FISI_VORLADEN"] = "0"      # erstes Oeffnen baut selbst
        import customtkinter as ctk
        import app_gui
        import fisi_widgets
        self.app_gui = app_gui
        # Bilder gehoeren zum jeweiligen Hauptfenster (wie test_vorladen.py)
        fisi_widgets.FoldCard._open_state.clear()
        fisi_widgets._PHOTO_CACHE.clear()
        fisi_widgets._IMAGE_CACHE.clear()
        app_gui.UpdateController.auto_check = lambda self: None
        app_gui.SyncController.auto_start = lambda self: None
        self.errors = []
        self._showerror = app_gui.messagebox.showerror
        app_gui.messagebox.showerror = lambda *a, **k: self.errors.append(a)
        if hasattr(app_gui, "apply_appearance"):
            app_gui.apply_appearance()
        self.root = ctk.CTk()
        self.root.geometry("1360x880+0+0")
        self.app = app_gui.FISIApp(self.root)
        self.pump(0.6)
        # Zaehler: wie oft entsteht ein Trainer, welche Breite hat der
        # sichtbare Bereich, wenn die Subnetting-Karte entsteht?
        self.trainer_gebaut = []
        self.breite_beim_aufbau = []
        self._orig_trainer = app_gui.TrainerPanel.__init__
        self._orig_subnet = app_gui.SubnetCalc.__init__
        test = self

        def trainer_init(panel, *args, **kwargs):
            test.trainer_gebaut.append(panel)
            return test._orig_trainer(panel, *args, **kwargs)

        def subnet_init(calc, card, *args, **kwargs):
            widget = card
            while widget is not None and not isinstance(widget, app_gui.CalcView):
                widget = widget.master
            if widget is not None:
                test.breite_beim_aufbau.append(widget.canvas.winfo_width())
            return test._orig_subnet(calc, card, *args, **kwargs)

        app_gui.TrainerPanel.__init__ = trainer_init
        app_gui.SubnetCalc.__init__ = subnet_init

    def tearDown(self):
        self.app_gui.TrainerPanel.__init__ = self._orig_trainer
        self.app_gui.SubnetCalc.__init__ = self._orig_subnet
        self.app_gui.messagebox.showerror = self._showerror
        try:
            tk_ = self.root.tk     # offene Zeitgeber abbrechen (wie test_vorladen.py)
            for job in tk_.splitlist(tk_.call("after", "info")):
                tk_.call("after", "cancel", job)
            self.root.destroy()
        except Exception:
            pass
        for key, value in self._env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def pump(self, seconds):
        end = time.time() + seconds
        while time.time() < end:
            self.root.update()
            time.sleep(0.01)

    def oeffnen(self):
        self.assertIsNone(self.app.views.built("calc"), "Rechner schon gebaut (Vorladen?)")
        self.app.show_view("calc")
        self.root.update_idletasks()
        self.root.update()
        return self.app.views["calc"]

    def test_groesse_vor_dem_fuellen(self):
        view = self.oeffnen()
        self.pump(0.3)
        sichtbar = view.canvas.winfo_width()
        self.assertGreater(sichtbar, 100)
        self.assertEqual(len(self.breite_beim_aufbau), 1, self.breite_beim_aufbau)
        # Die Subnetting-Karte entsteht schon im sichtbaren Bereich mit der
        # echten Breite (vorher: 1 px)
        self.assertEqual(self.breite_beim_aufbau[0], sichtbar)
        self.assertEqual(self.app.current, "calc")
        self.assertTrue(view.winfo_ismapped())
        self.assertEqual(tuple(view.canvas.xview()), (0.0, 1.0))
        self.assertEqual(self.errors, [])

    def test_breite_angepasst_ohne_groessenaenderung(self):
        """Wird das Fenster nach dem Oeffnen nicht mehr veraendert, ist die
        Seite trotzdem schon an die sichtbare Breite angepasst (Subnetting-
        Karte, USV-Spalten): ein weiteres Anpassen aendert nichts."""
        self.root.geometry("%dx%d+0+0" % FENSTER_SCHMAL)
        self.pump(0.8)
        view = self.oeffnen()
        self.pump(0.8)
        vorher = (view.subnet_gap, view.ups_stacked, view.ups_label_min)
        self.assertTrue(view.ups_stacked, "USV-Spalten nebeneinander: Seite nicht angepasst (oder Fenster zu breit)")
        view._fit()
        self.pump(0.3)
        self.assertEqual((view.subnet_gap, view.ups_stacked, view.ups_label_min), vorher)
        self.assertEqual(tuple(view.canvas.xview()), (0.0, 1.0))
        self.assertEqual(self.errors, [])

    def test_trainer_erst_beim_ersten_wechsel(self):
        view = self.oeffnen()
        self.assertEqual(self.trainer_gebaut, [], "Trainer schon beim Oeffnen gebaut")
        self.assertTrue(view.calc_layout.winfo_ismapped())
        # Wechsel auf "Trainer": jetzt entsteht er, genau einmal
        view.tab_pills.select_value("trainer")
        self.pump(0.3)
        self.assertEqual(len(self.trainer_gebaut), 1)
        trainer = view.trainer
        self.assertIs(trainer, self.trainer_gebaut[0])
        self.assertTrue(trainer.winfo_ismapped())
        self.assertFalse(view.calc_layout.winfo_ismapped())
        # Die Bedienung wirkt: Runde starten zeigt die erste Aufgabe
        trainer.start_round()
        self.pump(0.2)
        self.assertTrue(trainer.btn_check.winfo_ismapped())
        # zurueck und wieder hin: nichts Neues gebaut, je ein Teil sichtbar
        view.tab_pills.select_value("rechner")
        self.pump(0.3)
        self.assertTrue(view.calc_layout.winfo_ismapped())
        self.assertFalse(trainer.winfo_ismapped())
        view.tab_pills.select_value("trainer")
        self.pump(0.3)
        self.assertTrue(trainer.winfo_ismapped())
        self.assertEqual(len(self.trainer_gebaut), 1)
        self.assertEqual(self.errors, [])

    def test_rechner_reiter_ohne_trainer(self):
        """Ein Wechsel auf "Rechner", solange der Trainer fehlt, baut ihn nicht."""
        view = self.oeffnen()
        view._on_tab("rechner")
        self.pump(0.2)
        self.assertEqual(self.trainer_gebaut, [])
        self.assertTrue(view.calc_layout.winfo_ismapped())
        self.assertEqual(self.errors, [])

    def test_vorladen_baut_trainer_mit(self):
        """Mit Vorladen (prepare) ist der Trainer vor dem ersten Wechsel da;
        ein zweites prepare baut nichts mehr."""
        view = self.oeffnen()
        self.assertTrue(view.prepare())
        self.assertEqual(len(self.trainer_gebaut), 1)
        self.assertFalse(view.trainer.winfo_ismapped())
        self.assertFalse(view.prepare())
        view.tab_pills.select_value("trainer")
        self.pump(0.3)
        self.assertEqual(len(self.trainer_gebaut), 1)
        self.assertTrue(view.trainer.winfo_ismapped())
        self.assertEqual(self.errors, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
