#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests 0.63.1 Teil 1.4: Rechner-Teile erst bei Bedarf bauen.

Plan 0.63.1 Abschnitt 6.2/6.4: Beim Oeffnen ohne Vorladen entsteht nur
IPv4 "Netzdaten"; "Netz aufteilen" und "Nach Hostbedarf" entstehen beim
ersten Antippen, der erste Wechsel zu IPv6 baut nur IPv6 "Netzdaten". Mit
Vorladen baut CalcView.prepare alle 5 Ansichten verdeckt.

Gegen a74712d (0.63) rot: dort baut das Oeffnen alle drei IPv4-Ansichten
und prepare nur den IPv6-Teil (dort ebenfalls alle IPv6-Ansichten).

Start:  xvfb-run -a python test_rechner_bedarf.py
"""

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_TMP = tempfile.mkdtemp(prefix="fisi_rechner_bedarf_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "rechner_bedarf.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(_TMP, "selbsttest.log"))
os.environ["HOME"] = _TMP
os.environ["APPDATA"] = _TMP
# ohne Vorladen: der Rechner wird erst beim Oeffnen gebaut
os.environ["FISI_VORLADEN"] = "0"

import fisi_core as fc  # noqa: E402

ALLE = [(mode, key) for mode, _m in fc.SUBNET_MODES for key, _k in fc.SUBNET_VIEWS[mode]]


def _tk_ok():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:  # noqa: BLE001
        return False


HAS_DISPLAY = _tk_ok()
_SHARED = {}


def _shared_app():
    if _SHARED:
        return _SHARED
    import customtkinter as ctk
    import app_gui
    app_gui.UpdateController.auto_check = lambda self: None
    app_gui.SyncController.auto_start = lambda self: None
    errors = []
    _SHARED["showerror"] = app_gui.messagebox.showerror
    app_gui.messagebox.showerror = lambda *args, **kwargs: errors.append(args)
    root = ctk.CTk()
    root.geometry("1360x880+0+0")
    app = app_gui.FISIApp(root)
    for _ in range(4):
        root.update_idletasks()
        root.update()
    _SHARED.update(app_gui=app_gui, errors=errors, root=root, app=app,
                   vor_dem_oeffnen=app.views.built("calc"))
    app.show_view("calc")
    return _SHARED


def tearDownModule():
    if not _SHARED:
        return
    app_gui = _SHARED["app_gui"]
    app_gui.messagebox.showerror = _SHARED["showerror"]
    root = _SHARED["root"]
    try:
        for job in root.tk.splitlist(root.tk.call("after", "info")):
            root.tk.call("after", "cancel", job)
        root.destroy()
    except Exception:  # noqa: BLE001
        pass


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class BedarfTest(unittest.TestCase):
    """Reihenfolge zaehlt (eine App fuer alle Schritte): Namen mit Nummer."""

    @classmethod
    def setUpClass(cls):
        shared = _shared_app()
        cls.app_gui = shared["app_gui"]
        cls.errors = shared["errors"]
        cls.root = shared["root"]
        cls.app = shared["app"]
        cls.vor_dem_oeffnen = shared["vor_dem_oeffnen"]
        cls.view = cls.app.views["calc"]
        cls.sub = cls.view.subnet
        cls.settle()

    @classmethod
    def settle(cls, times=3):
        for _ in range(times):
            cls.root.update_idletasks()
            cls.root.update()

    def setUp(self):
        self.errors.clear()

    def gebaut(self):
        return sorted(key for key in ALLE if key in self.sub.views)

    @staticmethod
    def text(box):
        return box.get("1.0", "end-1c")

    def test_1_oeffnen_baut_nur_netzdaten(self):
        self.assertIsNone(self.vor_dem_oeffnen)          # wirklich ohne Vorladen
        self.assertEqual(self.app.preloader.mode, "aus")
        self.assertEqual(self.gebaut(), [("ipv4", "netzdaten")])
        self.assertFalse(self.sub.built("ipv6"))
        # Pillen der Ansichten sind trotzdem alle da (Wortlaut aus dem Kern)
        pills = self.sub.view_pills["ipv4"]
        self.assertEqual([(v, b.cget("text")) for v, b in zip(pills.values, pills.buttons)],
                         fc.SUBNET_VIEWS["ipv4"])
        # "in" und get() bauen nichts
        self.assertNotIn(("ipv4", "aufteilen"), self.sub.views)
        self.assertIsNone(self.sub.views.get(("ipv4", "bedarf")))
        self.assertEqual(self.gebaut(), [("ipv4", "netzdaten")])

    def test_2_antippen_aufteilen(self):
        sub = self.sub
        sub.view_pills["ipv4"].select_value("aufteilen")
        self.settle()
        self.assertEqual(self.gebaut(), [("ipv4", "aufteilen"), ("ipv4", "netzdaten")])
        view = sub.views[("ipv4", "aufteilen")]
        self.assertEqual(sub.view_of["ipv4"], "aufteilen")
        self.assertTrue(view["frame"].winfo_ismapped())
        self.assertFalse(sub.views[("ipv4", "netzdaten")]["frame"].winfo_ismapped())
        net, count = fc.SUBNET_DEFAULTS[("ipv4", "aufteilen")]
        self.assertEqual(view["net"].get(), net)
        self.assertEqual(view["count"].get(), count)
        self.assertEqual(self.text(view["box"]), "")
        self.assertIsNone(view["result"])
        # Rechnen, Blaettern, Rechenweg
        view["net"].set("10.0.0.0/16")
        view["count"].set("300")
        sub.calc("ipv4", "aufteilen")
        self.settle()
        self.assertEqual(self.errors, [])
        result = fc.split_network("10.0.0.0/16", "300", version=4)
        self.assertGreater(result["seiten"], 1)
        self.assertEqual(self.text(view["box"]), fc.split_report(result, 1))
        self.assertTrue(view["pager"].winfo_ismapped())
        sub.turn(view, "next")
        self.settle()
        self.assertEqual(view["page"], 2)
        self.assertEqual(self.text(view["box"]), fc.split_report(result, 2))
        sub.toggle_info("ipv4", "aufteilen")
        self.settle()
        self.assertTrue(view["info"].winfo_ismapped())
        self.assertEqual(self.text(view["info"]), fc.split_explain(result))
        # Wechsel weg und zurueck: Ergebnis und Seite bleiben, Rechenweg zu
        sub.view_pills["ipv4"].select_value("netzdaten")
        self.settle()
        sub.view_pills["ipv4"].select_value("aufteilen")
        self.settle()
        self.assertIs(sub.views[("ipv4", "aufteilen")], view)   # nicht neu gebaut
        self.assertEqual(view["page"], 2)
        self.assertEqual(self.text(view["box"]), fc.split_report(result, 2))
        self.assertFalse(view["info_open"])

    def test_3_antippen_bedarf(self):
        sub = self.sub
        sub.view_pills["ipv4"].select_value("bedarf")
        self.settle()
        self.assertIn(("ipv4", "bedarf"), sub.views)
        view = sub.views[("ipv4", "bedarf")]
        self.assertTrue(view["frame"].winfo_ismapped())
        net, needs = fc.SUBNET_DEFAULTS[("ipv4", "bedarf")]
        self.assertEqual(view["net"].get(), net)
        self.assertEqual(view["needs"].get("1.0", "end-1c"), needs)
        self.assertEqual(self.text(view["box"]), "")
        sub.calc("ipv4", "bedarf")
        self.settle()
        self.assertEqual(self.errors, [])
        self.assertEqual(self.text(view["box"]),
                         fc.hosts_report(fc.subnet_by_hosts(net, needs, version=4)))
        sub.view_pills["ipv4"].select_value("netzdaten")
        self.settle()

    def test_4_erster_wechsel_ipv6_baut_nur_netzdaten(self):
        sub = self.sub
        self.assertFalse(sub.built("ipv6"))
        sub.mode_pills.select_value("ipv6")
        self.settle()
        self.assertEqual(sub.mode, "ipv6")
        self.assertTrue(sub.mode_frames["ipv6"].winfo_ismapped())
        self.assertIn(("ipv6", "netzdaten"), sub.views)
        self.assertNotIn(("ipv6", "aufteilen"), sub.views)
        self.assertTrue(sub.views[("ipv6", "netzdaten")]["frame"].winfo_ismapped())
        # IPv6 hat kein "Nach Hostbedarf": KeyError, nichts gebaut
        with self.assertRaises(KeyError):
            sub.views[("ipv6", "bedarf")]
        self.assertNotIn(("ipv6", "bedarf"), sub.views)
        sub.view_pills["ipv6"].select_value("aufteilen")
        self.settle()
        view = sub.views[("ipv6", "aufteilen")]
        self.assertTrue(view["frame"].winfo_ismapped())
        net, count = fc.SUBNET_DEFAULTS[("ipv6", "aufteilen")]
        self.assertEqual(view["net"].get(), net)
        self.assertEqual(view["count"].get(), count)
        sub.calc("ipv6", "aufteilen")
        self.settle()
        self.assertEqual(self.errors, [])
        self.assertEqual(self.text(view["box"]),
                         fc.split_report(fc.split_network(net, count, version=6), 1))
        sub.mode_pills.select_value("ipv4")
        self.settle()
        self.assertEqual(sub.view_of["ipv4"], "netzdaten")
        # nichts ist doppelt entstanden: je Modus Pillenzeile + ein Rahmen je Ansicht
        self.assertEqual(self.gebaut(), sorted(ALLE))
        for mode, frame in sub.mode_frames.items():
            self.assertEqual(len(frame.winfo_children()), 1 + len(fc.SUBNET_VIEWS[mode]), mode)

    def test_5_vorladen_baut_alle(self):
        # Plan 6.2: prepare baut den IPv6-Teil und die drei uebrigen Ansichten
        card = self.app_gui.Card(self.view.content, title=fc.SUBNET_TITLE)
        try:
            fresh = self.app_gui.SubnetCalc(card)
            self.assertEqual(sorted(dict.keys(fresh.views)), [("ipv4", "netzdaten")])
            self.assertTrue(fresh.build_rest())
            self.assertEqual(sorted(dict.keys(fresh.views)), sorted(ALLE))
            self.assertEqual(len(ALLE), 5)
            self.assertFalse(fresh.build_rest())          # schon alles da
            self.assertFalse(fresh.mode_frames["ipv6"].winfo_ismapped())
            self.assertEqual(fresh.mode, "ipv4")
            self.assertEqual(fresh.view_of, {"ipv4": "netzdaten", "ipv6": "netzdaten"})
            for key in ALLE:
                if key[1] != "netzdaten":
                    self.assertEqual(fresh.views[key]["frame"].winfo_manager(), "", key)
        finally:
            card.destroy()
        # die echte Karte: prepare nutzt build_rest (alles schon gebaut: False)
        self.assertFalse(self.view.prepare())

    def test_6_prepare_auf_frischer_ansicht(self):
        # prepare der Ansicht selbst (wie der Vorlade-Schritt), auf einer
        # frischen Karte: True und danach alle 5 Ansichten
        card = self.app_gui.Card(self.view.content, title=fc.SUBNET_TITLE)
        saved = self.view.subnet
        try:
            self.view.subnet = self.app_gui.SubnetCalc(card)
            self.assertEqual(sorted(dict.keys(self.view.subnet.views)), [("ipv4", "netzdaten")])
            self.assertTrue(self.view.prepare())
            self.assertEqual(sorted(dict.keys(self.view.subnet.views)), sorted(ALLE))
            self.assertFalse(self.view.prepare())
        finally:
            self.view.subnet = saved
            card.destroy()


if __name__ == "__main__":
    unittest.main(verbosity=2)
