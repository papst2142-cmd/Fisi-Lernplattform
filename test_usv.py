#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer den USV-Kapazitaetsrechner ab 0.58 (Plan 2):
  * Formeln (VA <-> W, Akku in Wh und Ah, Laufzeit, Alterungszuschlag) mit
    dem Rechenbeispiel aus der Quelle (EnerSys: 89,29 Ah)
  * Empfehlung nach der 80-%-Regel, Grenzfaelle genau auf der Grenze
  * Randwerte und Eingabefehler (leer, Text, 0, negativ, zu gross, Komma)
  * Uebungsaufgaben: Loesungen stimmen mit den Formeln ueberein
  * Bild: Daten fuer PC und Handy, Vorlesetext fuer TalkBack
  * Oberflaeche: gleiche Beschriftungen PC und Handy, Tab-Reihenfolge am PC

Start:  python test_usv.py   (Teile mit Oberflaeche brauchen ein Display)
"""

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_TMP = tempfile.mkdtemp(prefix="fisi_usv_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "usv.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(_TMP, "selbsttest.log"))

import fisi_core as fc  # noqa: E402
from fisi_core import InputError  # noqa: E402


def _tk_ok():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:  # noqa: BLE001
        return False


def fields(**changes):
    result = dict(fc.UPS_FIELD_DEFAULTS)
    result.update({key: str(value) for key, value in changes.items()})
    return result


class FormelTest(unittest.TestCase):

    def test_va_und_w(self):
        self.assertEqual(fc.ups_load(800, "VA", 0.9), (720.0, 800))
        watt, va = fc.ups_load(600, "W", 0.9)
        self.assertEqual(watt, 600)
        self.assertAlmostEqual(va, 666.667, places=3)

    def test_beispiel_enersys(self):
        # ((450 / 0,84) / 48) x 8 = 89,29 Ah (Quelle EnerSys)
        need = fc.ups_battery_need(450, 84, 480, 0, 48)
        self.assertAlmostEqual(need["bedarf_ah"], 89.29, places=2)

    def test_akku_mit_alterung(self):
        need = fc.ups_battery_need(600, 80, 15, 25, 24)
        self.assertAlmostEqual(need["last_wh"], 150)
        self.assertAlmostEqual(need["akku_wh"], 187.5)
        self.assertAlmostEqual(need["bedarf_wh"], 234.375)
        self.assertAlmostEqual(need["bedarf_ah"], 9.765625)

    def test_laufzeit(self):
        energy = fc.ups_battery_energy(12, 12, 2, 1)
        self.assertEqual(energy, 288)
        runtime = fc.ups_runtime(600, 80, energy, 25)
        self.assertAlmostEqual(runtime["neu"], 23.04)
        self.assertAlmostEqual(runtime["ende"], 18.432)
        self.assertAlmostEqual(fc.ups_end_share(25), 80)
        self.assertEqual(fc.ups_battery_energy(12, 9, 4, 2), 864)

    def test_a_und_b_passen_zusammen(self):
        # Ein Akku genau nach Berechnung A schafft die Laufzeit am Lebensende
        need = fc.ups_battery_need(750, 85, 20, 25, 48)
        runtime = fc.ups_runtime(750, 85, need["bedarf_wh"], 25)
        self.assertAlmostEqual(runtime["ende"], 20)
        self.assertAlmostEqual(runtime["neu"], 25)

    def test_straenge_aufrunden(self):
        self.assertEqual(fc.ups_strings_needed(390.625, 288), 2)
        self.assertEqual(fc.ups_strings_needed(288, 288), 1)
        self.assertEqual(fc.ups_strings_needed(576.0000001, 288), 2)

    def test_deutsche_zahlen(self):
        self.assertEqual(fc.de_number(1234.5), "1.234,50")
        self.assertEqual(fc.de_number(0.25, 3), "0,250")
        self.assertEqual(fc._de_short(0.9), "0,9")
        self.assertEqual(fc._de_short(12.0), "12")


class EmpfehlungTest(unittest.TestCase):

    def test_standardwerte_passend(self):
        result = fc.ups_calculate("empfehlung", fields())
        self.assertTrue(result["passend"])
        self.assertIn("USV passend", result["text"])
        self.assertEqual(result["bild"]["urteil"], "passend")

    def test_genau_80_prozent_ist_passend(self):
        ok, _checks = fc.ups_check(720, 800, 1000, 900, 20, 15)
        self.assertTrue(ok)

    def test_ueber_80_prozent_zu_klein(self):
        ok, checks = fc.ups_check(1080, 1200, 1500, 1000, 30, 15)
        self.assertFalse(ok)
        self.assertEqual([check[0] for check in checks], [True, False, True])

    def test_laufzeit_zu_kurz(self):
        result = fc.ups_calculate("empfehlung", fields(minuten=20))
        self.assertFalse(result["passend"])
        self.assertIn("USV zu klein", result["text"])
        self.assertEqual(result["bild"]["balken"][-1]["art"], "knapp")
        self.assertIn("zu kurz", result["bild"]["balken"][-1]["text"])

    def test_ohne_nennleistung_in_w(self):
        result = fc.ups_calculate("empfehlung", fields(nenn_w=""))
        self.assertTrue(result["passend"])
        self.assertIn("nur VA geprüft", result["text"])

    def test_last_in_va(self):
        result = fc.ups_calculate("empfehlung", fields(last=1200, nenn_va=1500,
                                                      nenn_w=1000), unit="VA")
        self.assertIn("1.080 W / 1.200 VA", result["text"])
        self.assertFalse(result["passend"])

    def test_regel_wird_erklaert(self):
        self.assertIn("80 %", fc.UPS_RULE_TEXT)
        self.assertIn("Schneider Electric", fc.UPS_RULE_TEXT)


class EingabeTest(unittest.TestCase):

    def assertError(self, mode="akku", unit="W", **changes):
        with self.assertRaises(InputError) as caught:
            fc.ups_calculate(mode, fields(**changes), unit)
        return str(caught.exception)

    def test_leer(self):
        self.assertIn("Last", self.assertError(last=""))
        self.assertIn("Leistungsfaktor", self.assertError(pf="  "))

    def test_kein_zahlentext(self):
        self.assertIn("Zahl", self.assertError(eta="achtzig"))
        self.assertIn("Zahl", self.assertError(last="nan"))
        self.assertIn("Zahl", self.assertError(last="inf"))

    def test_null_und_negativ(self):
        for key in ("last", "minuten", "block_v"):
            self.assertIn("größer als 0", self.assertError(**{key: 0}))
            self.assertIn("größer als 0", self.assertError(**{key: -5}))
        self.assertIn("größer als 0", self.assertError("laufzeit", block_ah=0))

    def test_grenzen(self):
        self.assertIn("zwischen 0,1 und 1", self.assertError(pf="1,2"))
        self.assertIn("zwischen 10 und 100", self.assertError(eta=5))
        self.assertIn("zwischen 10 und 100", self.assertError(eta=101))
        self.assertIn("zwischen 0 und 100", self.assertError(alterung=-1))
        self.assertIn("höchstens 1.440", self.assertError(minuten=1441))

    def test_ganze_zahlen(self):
        self.assertIn("ganze Zahl", self.assertError(reihe="1,5"))
        self.assertIn("zwischen 1 und 20", self.assertError("laufzeit", parallel=0))

    def test_randwerte_gehen(self):
        for changes in ({"pf": "0,1"}, {"pf": "1"}, {"eta": "100"}, {"eta": "10"},
                        {"alterung": "0"}, {"minuten": "1440"}, {"reihe": "100"},
                        {"last": "0,01"}):
            for mode, _caption in fc.UPS_MODES:
                fc.ups_calculate(mode, fields(**changes))

    def test_komma_punkt_und_tausender(self):
        self.assertEqual(fc.ups_number({"last": "1.500,5"}, "last"), 1500.5)
        self.assertEqual(fc.ups_number({"last": "1500,5"}, "last"), 1500.5)
        self.assertEqual(fc.ups_number({"last": "1500.5"}, "last"), 1500.5)
        self.assertEqual(fc.ups_number({"last": " 600 "}, "last"), 600)

    def test_nennleistung_nur_bei_empfehlung(self):
        fc.ups_calculate("akku", fields(nenn_va=""))
        fc.ups_calculate("laufzeit", fields(nenn_va="x"))
        self.assertIn("USV-Nennleistung", self.assertError("empfehlung", nenn_va=""))
        self.assertIn("USV-Nennleistung", self.assertError("empfehlung", nenn_w="-1"))

    def test_unbekannte_berechnung(self):
        self.assertError("raten")


class AufgabenTest(unittest.TestCase):

    def test_alle_aufgaben_mit_loesung(self):
        self.assertGreaterEqual(len(fc.UPS_TASKS), 5)
        for index, task in enumerate(fc.UPS_TASKS):
            text = fc.ups_task_text(index, solution=True)
            self.assertIn("Annahmen:", text)
            self.assertIn("Lösungsweg:", text)
            self.assertIn("Antwort:", text)
            self.assertNotIn("Lösungsweg", fc.ups_task_text(index))
            self.assertTrue(task["annahmen"])

    def test_loesungen_aus_den_formeln(self):
        self.assertIn("720 W", fc.ups_task_solution(0))
        self.assertIn("1.000 VA", fc.ups_task_solution(0))
        self.assertIn("89,29 Ah", fc.ups_task_solution(1))
        self.assertIn("36,72 min", fc.ups_task_solution(2))
        self.assertIn("29,38 min", fc.ups_task_solution(2))
        self.assertIn("zu klein", fc.ups_task_solution(3))
        self.assertIn("4,82 Ah", fc.ups_task_solution(4))
        self.assertIn("2 Stränge", fc.ups_task_solution(5))

    def test_annahmen_wiederholen_nichts_aus_der_aufgabe(self):
        # Nachtrag 0.58: Gegebenes steht nicht noch einmal unter "Annahmen"
        import re
        for task in fc.UPS_TASKS:
            for number in re.findall(r"\d+(?:,\d+)?", task["annahmen"]):
                self.assertNotIn(number, task["frage"], task["titel"])
            self.assertNotIn("Annahme)", task["annahmen"])

    def test_reihum(self):
        self.assertTrue(fc.ups_task_text(len(fc.UPS_TASKS)).startswith("Aufgabe 1 von"))


class BildTest(unittest.TestCase):

    def test_akku_bild(self):
        picture = fc.ups_calculate("akku", fields())["bild"]
        self.assertEqual(picture["last"], "600 W")
        self.assertEqual(picture["akku"], "234 Wh")
        self.assertIsNone(picture["urteil"])
        self.assertIsNone(picture["auslastung"])
        self.assertEqual([bar["art"] for bar in picture["balken"]], ["ziel", "neu", "ok"])
        self.assertEqual(max(bar["anteil"] for bar in picture["balken"]), 1)

    def test_empfehlung_bild(self):
        picture = fc.ups_calculate("empfehlung", fields())["bild"]
        self.assertAlmostEqual(picture["auslastung"], 66.667, places=2)
        self.assertEqual(picture["grenze"], 80)

    def test_vorlesetext(self):
        picture = fc.ups_calculate("empfehlung", fields())["bild"]
        summary = fc.ups_picture_summary(picture)
        for part in ("Last 600 W", "USV η 80 %", "Akku 288 Wh", "Akku neu 23,0 min",
                     "Empfehlung: USV passend"):
            self.assertIn(part, summary)


class OberflaecheTextTest(unittest.TestCase):
    """Beschriftungen kommen fuer PC und Handy aus fisi_core."""

    def test_beide_oberflaechen(self):
        for path in ("app_gui.py", os.path.join("mobile", "src", "main.py")):
            with open(os.path.join(HERE, path), encoding="utf-8") as handle:
                source = handle.read()
            for name in ("UPS_TITLE", "UPS_SUBTITLE", "UPS_FIELD_CAPTIONS", "UPS_MODES",
                         "UPS_RULE_TEXT", "UPS_TASKS_TITLE", "UPS_TASK_NEXT",
                         "UPS_SOLUTION_SHOW", "CALC_EXPLAIN_UPS", "ups_calculate"):
                self.assertIn(name, source, (path, name))


class HandyTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        sys.path.insert(1, os.path.join(HERE, "mobile", "src"))
        import main as handy
        import ui
        cls.handy, cls.ui = handy, ui

    def test_bild_mit_vorlesetext(self):
        picture = self.ui.UpsPicture()
        result = fc.ups_calculate("empfehlung", fields())
        picture.set_picture(result["bild"], fc.ups_picture_summary(result["bild"]))
        self.assertTrue(picture.label.startswith("Bild: Last 600 W"))
        self.assertTrue(picture.column.controls)

    def test_felder_haben_beschriftung(self):
        screen = self.handy.CalcScreen.__new__(self.handy.CalcScreen)
        screen.toast = lambda *args: None
        card = screen._build_ups()
        self.assertEqual(set(screen.ups_entries), set(fc.UPS_FIELD_CAPTIONS))
        labels = []

        def walk(control):
            if getattr(control, "label", None) and type(control).__name__ == "Semantics":
                labels.append(control.label)
            for name in ("content", "controls"):
                child = getattr(control, name, None)
                for item in child if isinstance(child, list) else [child]:
                    if item is not None and hasattr(item, "__dict__"):
                        walk(item)
        walk(card)
        for caption in fc.UPS_FIELD_CAPTIONS.values():
            self.assertIn(caption, labels)
        self.assertIn("USV passend", screen.out_ups.content.value)

    def test_fehler_als_hinweis(self):
        screen = self.handy.CalcScreen.__new__(self.handy.CalcScreen)
        toasts = []
        screen.toast = lambda text, color: toasts.append(text)
        screen._build_ups()
        screen.ups_entries["last"].value = "abc"
        screen.calc_ups("akku")
        self.assertEqual(len(toasts), 1)
        self.assertIn("Last", toasts[0])

    def test_aufgaben_blaettern(self):
        screen = self.handy.CalcScreen.__new__(self.handy.CalcScreen)
        screen.toast = lambda *args: None
        screen._build_ups()
        screen.toggle_ups_solution()
        self.assertIn("Lösungsweg", screen.out_ups_task.content.value)
        screen.next_ups_task()
        self.assertTrue(screen.out_ups_task.content.value.startswith("Aufgabe 2"))
        self.assertNotIn("Lösungsweg", screen.out_ups_task.content.value)


@unittest.skipUnless(_tk_ok(), "kein Display fuer Tk")
class PcTest(unittest.TestCase):
    """Rechner-Ansicht am PC: Bild, Fehler, Tastatur."""

    @classmethod
    def setUpClass(cls):
        import customtkinter as ctk
        import app_gui
        import fisi_widgets as fw
        cls.app_gui, cls.fw = app_gui, fw
        app_gui.UpdateController.auto_check = lambda self: None
        app_gui.SyncController.auto_start = lambda self: None
        cls.errors = []
        app_gui.messagebox.showerror = lambda *args, **kwargs: cls.errors.append(args)
        cls.root = ctk.CTk()
        cls.root.geometry("1360x880+0+0")
        cls.app = app_gui.FISIApp(cls.root)
        cls.app.show_view("calc")
        cls.view = cls.app.views["calc"]
        cls.settle()

    @classmethod
    def tearDownClass(cls):
        try:
            for job in cls.root.tk.splitlist(cls.root.tk.call("after", "info")):
                cls.root.tk.call("after", "cancel", job)
            cls.root.destroy()
        except Exception:  # noqa: BLE001
            pass

    @classmethod
    def settle(cls, times=6):
        for _ in range(times):
            cls.root.update_idletasks()
            cls.root.update()

    def test_startwerte_gerechnet(self):
        text = self.view.txt_ups.get("1.0", "end")
        self.assertIn("USV passend", text)
        self.assertEqual(self.view.ups_picture._picture["urteil"], "passend")
        self.assertTrue(self.view.ups_picture.find_all())

    def test_fehler_meldung(self):
        self.errors.clear()
        entry = self.view.ups_entries["eta"]
        entry.delete(0, "end")
        entry.insert(0, "200")
        self.view.calc_ups("laufzeit")
        entry.delete(0, "end")
        entry.insert(0, "80")
        self.assertEqual(len(self.errors), 1)
        self.assertIn("Wirkungsgrad", self.errors[0][1])

    def test_umschalten_auf_va(self):
        self.view.ups_unit.select_value("VA", notify=False)
        try:
            self.view.calc_ups("akku")
            self.settle(2)
            text = self.view.txt_ups.get("1.0", "end")
            self.assertIn("540 W / 600 VA", text)
            self.assertIn("Benötigte Kapazität", text)
        finally:
            self.view.ups_unit.select_value("W", notify=False)

    def test_aufgaben(self):
        self.view.ups_task = 0
        self.view.ups_solution = False
        self.view.toggle_ups_solution()
        self.assertIn("Lösungsweg", self.view.txt_ups_task.get("1.0", "end"))
        self.view.next_ups_task()
        text = self.view.txt_ups_task.get("1.0", "end")
        self.assertTrue(text.startswith("Aufgabe 2"))
        self.assertNotIn("Lösungsweg", text)

    def test_tab_reihenfolge_der_felder(self):
        order = ["last", "pf", "eta", "nenn_va", "nenn_w", "block_v", "block_ah", "reihe",
                 "parallel", "minuten", "alterung"]
        self.fw.focus_widget(self.view.ups_entries["last"])
        self.settle(2)
        reached = []
        for _ in range(40):
            path = str(self.root.tk.call("focus"))
            focus = self.root.nametowidget(path)
            for key, entry in self.view.ups_entries.items():
                if path.startswith(str(entry) + ".") and key not in reached:
                    reached.append(key)
            if len(reached) == len(order):
                break
            focus.event_generate("<Tab>")
            self.settle(2)
        self.assertEqual(reached, order)


if __name__ == "__main__":
    unittest.main(verbosity=2)
