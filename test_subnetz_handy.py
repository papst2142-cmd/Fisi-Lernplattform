#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer die Handy-Karte "Subnetting" ab 0.63 (Plan 0.63, T4) und die
Befunde aus 0.62.6, die 0.63 am Handy mitnimmt:
  * Aufbau: Titel, Schalter IPv4/IPv6, Ansichten je Modus, Beschriftungen
    aus den Konstanten in fisi_core.py (eine Quelle fuer PC und Handy, T-UI-3)
  * Rechnen in jeder Ansicht, Blaettern, Sprung auf eine Seite, Rechenweg
    zur Vorgabe und zur Eingabe (Handy-Fassung, hoechstens 28 Zeichen)
  * Moduswechsel nach Plan 4.6 (T-UI-5): Eingaben und Ergebnis bleiben,
    keine neue Rechnung, Rechenweg zu, eigene Ansicht je Modus, Start IPv4
  * B-D-04: Ergebnis bei Fehler leeren (Subnetting, RAID, Bildschirm, USV
    mit Bild); USV "+0 %" als Schutz
  * B-E-01/B-E-02: Ergebniskaesten mit fit=True, Pillen mit umbrechen=True,
    sobald ui.py die Schnittstelle "Anzeige Handy" kennt

Start:  python test_subnetz_handy.py   (ohne Display, Flet-Steuerelemente
werden nur aufgebaut, nicht angezeigt)
"""

import inspect
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_TMP = tempfile.mkdtemp(prefix="fisi_subnetz_handy_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "handy.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(_TMP, "selbsttest.log"))

import fisi_core as fc  # noqa: E402

sys.path.insert(1, os.path.join(HERE, "mobile", "src"))
import flet as ft  # noqa: E402
import main as handy  # noqa: E402
import ui  # noqa: E402


def _walk(control, found=None):
    """Alle Steuerelemente unter control (content und controls)."""
    found = [] if found is None else found
    found.append(control)
    for name in ("content", "controls"):
        child = getattr(control, name, None)
        for item in child if isinstance(child, list) else [child]:
            if item is not None and hasattr(item, "__dict__"):
                _walk(item, found)
    return found


def _texts(control):
    return [c.value for c in _walk(control) if isinstance(c, ft.Text)]


class _App:
    def __init__(self):
        self.db = fc.DBManager(os.path.join(tempfile.mkdtemp(dir=_TMP), "t.db"))
        self.sync = None
        self.scrolled = 0

    def scroll_top(self):
        self.scrolled += 1


def _screen():
    screen = handy.CalcScreen.__new__(handy.CalcScreen)
    screen.toasts = []
    screen.toast = lambda text, color=None: screen.toasts.append(text)
    screen.app = _App()
    screen.build()
    return screen


def _out(screen, mode, view):
    return screen.subnet_panels[(mode, view)]["out"].data.value


def _explain(screen, mode, view):
    row, box = screen.subnet_panels[(mode, view)]["explain"]
    return row.controls[0], box


def _fehler(func, *args):
    try:
        func(*args)
    except fc.InputError as error:
        return error
    raise AssertionError("keine Meldung")


HAT_SPRUNG = hasattr(fc, "SUBNET_PAGE_JUMP_FIELD") and hasattr(fc, "SUBNET_PAGE_JUMP")
HAT_DETAILS = hasattr(fc, "ipv6_details")


class AufbauTest(unittest.TestCase):
    """T-UI-2/T-UI-3: Karte, Schalter, Ansichten, Beschriftungen."""

    def setUp(self):
        self.screen = _screen()

    def test_titel_und_untertitel(self):
        card = self.screen.subnet_card
        self.assertEqual(card.title_text.value, fc.SUBNET_TITLE.upper())
        self.assertEqual(card.subtitle_text.value, fc.SUBNET_SUBTITLE["ipv4"])
        self.assertIs(self.screen.calc_box.controls[0], card)

    def test_schalter_und_ansichten(self):
        screen = self.screen
        self.assertEqual(screen.mode_pills.values, [m for m, _c in fc.SUBNET_MODES])
        self.assertEqual(screen.mode_pills.get(), "ipv4")
        for mode, _caption in fc.SUBNET_MODES:
            pills = screen.view_pills[mode]
            self.assertEqual(pills.values, [v for v, _c in fc.SUBNET_VIEWS[mode]])
            self.assertEqual(pills.visible, mode == "ipv4")
        self.assertNotIn("bedarf", screen.view_pills["ipv6"].values)
        captions = _texts(screen.subnet_card)
        for _mode, caption in fc.SUBNET_MODES:
            self.assertIn(caption, captions)
        for mode in fc.SUBNET_VIEWS:
            for _view, caption in fc.SUBNET_VIEWS[mode]:
                self.assertIn(caption, captions)

    def test_start_ipv4_netzdaten(self):
        sichtbar = [key for key, panel in self.screen.subnet_panels.items()
                    if panel["box"].visible]
        self.assertEqual(sichtbar, [("ipv4", "netzdaten")])
        self.assertEqual(set(self.screen.subnet_panels),
                         {(m, v) for m in fc.SUBNET_VIEWS for v, _c in fc.SUBNET_VIEWS[m]})

    def test_beschriftungen_aus_fisi_core(self):
        captions = _texts(self.screen.subnet_card)
        # Ab 0.63.2 (A5-c, FG-27): nach "/" steht in der Handy-Anzeige ein
        # unsichtbares U+2060; sichtbar gleich -> vor dem Vergleich entfernen
        sichtbar = [text.replace("\u2060", "") for text in captions]
        for mode in ("ipv4", "ipv6"):
            self.assertIn(fc.SUBNET_FIELD_NET[mode], sichtbar)
        self.assertIn(fc.SUBNET_FIELD_COUNT, captions)
        self.assertIn(fc.SUBNET_FIELD_NEEDS, captions)
        # Kein eigener Text mehr am Handy (alte Beschriftungen weg)
        with open(handy.__file__, encoding="utf-8") as handle:
            source = handle.read()
        self.assertNotIn("Subnetting / VLSM", source)
        self.assertNotIn("IP-Adresse mit Präfix", source)
        for name in ("Erste Seite", "Letzte Seite", "Netz aufteilen", "Nach Hostbedarf",
                     "Anzahl Subnetze", "Netz mit Präfix"):
            self.assertNotIn('"%s"' % name, source, name)

    def test_blaettern_beschriftet(self):
        panel = self.screen.subnet_panels[("ipv6", "aufteilen")]
        labels = [c.label for c in _walk(panel["pager"]) if isinstance(c, ft.Semantics)]
        tips = [b.tooltip for b in panel["page_buttons"].values()]
        for caption in (fc.SUBNET_PAGE_FIRST, fc.SUBNET_PAGE_BACK, fc.SUBNET_PAGE_NEXT,
                        fc.SUBNET_PAGE_LAST):
            self.assertIn(caption, labels)
            self.assertIn(caption, tips)
        self.assertFalse(panel["pager"].visible)

    def test_vorgaben(self):
        panels = self.screen.subnet_panels
        self.assertEqual(panels[("ipv4", "netzdaten")]["net"].value, "192.168.1.50/24")
        self.assertEqual(panels[("ipv6", "netzdaten")]["net"].value, "2001:db8:abcd:12::1/64")
        for key in (("ipv4", "aufteilen"), ("ipv6", "aufteilen")):
            net, count = fc.SUBNET_DEFAULTS[key]
            self.assertEqual((panels[key]["net"].value, panels[key]["count"].value), (net, count))
        net, needs = fc.SUBNET_DEFAULTS[("ipv4", "bedarf")]
        bedarf = panels[("ipv4", "bedarf")]
        self.assertEqual((bedarf["net"].value, bedarf["needs"].value), (net, needs))
        self.assertTrue(bedarf["needs"].multiline)
        self.assertEqual((bedarf["needs"].min_lines, bedarf["needs"].max_lines), (4, 12))

    def test_leer_vor_erstem_berechnen(self):
        for key, panel in self.screen.subnet_panels.items():
            self.assertEqual(panel["out"].data.value, "", key)
        self.assertIs(self.screen.out_subnet, self.screen.subnet_panels[("ipv4", "netzdaten")]["out"])


class RechnenTest(unittest.TestCase):
    """Ergebnisse und Rechenwege je Ansicht."""

    def setUp(self):
        self.screen = _screen()

    def test_netzdaten_ipv4(self):
        self.screen.calc_subnet()
        self.assertEqual(self.screen.out_subnet.data.value, fc.subnet_report("192.168.1.50/24"))
        _button, box = _explain(self.screen, "ipv4", "netzdaten")
        self.assertEqual(box.data.value, fc.CALC_EXPLAIN_SUBNET_HANDY)
        _button, box = _explain(self.screen, "ipv6", "netzdaten")
        self.assertEqual(box.data.value, fc.CALC_EXPLAIN_SUBNET_V6_HANDY)

    @unittest.skipUnless(HAT_DETAILS, "fisi_core.ipv6_details fehlt (Zweig version-063-kern)")
    def test_netzdaten_ipv6_mit_details(self):
        self.screen._on_subnet_mode("ipv6")
        self.screen.calc_subnet()
        value = "2001:db8:abcd:12::1/64"
        expected = fc.subnet_report(value) + "".join(
            "\n%-22s: %s" % pair for pair in fc.ipv6_details(value))
        self.assertEqual(_out(self.screen, "ipv6", "netzdaten"), expected)
        self.assertIn(fc.IPV6_LABEL_AUSGESCHRIEBEN, expected)
        self.assertIn(fc.IPV6_LABEL_ADRESSTYP, expected)
        # IPv4 bleibt ohne die zwei Zeilen
        self.screen._on_subnet_mode("ipv4")
        self.screen.calc_subnet()
        self.assertNotIn(fc.IPV6_LABEL_ADRESSTYP, self.screen.out_subnet.data.value)

    def test_netzdaten_version_des_schalters(self):
        """N-M-2/N-M-3 auch in der Ansicht Netzdaten, danach Kasten leer."""
        screen = self.screen
        screen.calc_subnet(mode="ipv4")
        screen.entry_ip.value = "2001:db8::/48"
        screen.calc_subnet(mode="ipv4")
        self.assertEqual(screen.toasts[-1], "Im Modus IPv4 bitte ein IPv4-Netz angeben "
                                            "(z. B. 192.168.10.0/24).")
        self.assertEqual(screen.out_subnet.data.value, "")
        panel = screen.subnet_panels[("ipv6", "netzdaten")]
        for value in ("192.168.1.0/24", "10.0.0.1"):
            screen.calc_subnet(mode="ipv6")
            self.assertNotEqual(panel["out"].data.value, "")
            panel["net"].value = value
            screen.calc_subnet(mode="ipv6")
            self.assertEqual(screen.toasts[-1], "Im Modus IPv6 bitte ein IPv6-Netz angeben "
                                                "(z. B. 2001:db8:abcd::/48).")
            self.assertEqual(panel["out"].data.value, "")
            panel["net"].value = "2001:db8:abcd:12::1/64"
        # Ohne Praefix bleibt es bei subnet_report (wie bisher): 10.0.0.1 = /32
        screen.entry_ip.value = "10.0.0.1"
        screen.calc_subnet(mode="ipv4")
        self.assertEqual(screen.out_subnet.data.value, fc.subnet_report("10.0.0.1"))
        screen.entry_ip.value = "kaputt"
        screen.calc_subnet(mode="ipv4")
        self.assertEqual(screen.toasts[-1], str(_fehler(fc.subnet_report, "kaputt")))

    def test_aufteilen_ipv4_vorgabe(self):
        screen = self.screen
        _button, box = _explain(screen, "ipv4", "aufteilen")
        result = fc.split_network("192.168.10.0/24", "6", version=4)
        self.assertEqual(box.data.value, fc.split_explain(result, schmal=True))  # Beispiel B
        screen.calc_split("ipv4")
        self.assertEqual(_out(screen, "ipv4", "aufteilen"),
                         fc.split_report(result, 1, schmal=True))
        self.assertFalse(screen.subnet_panels[("ipv4", "aufteilen")]["pager"].visible)

    def test_aufteilen_rechenweg_zur_eingabe(self):
        screen = self.screen
        panel = screen.subnet_panels[("ipv4", "aufteilen")]
        panel["net"].value, panel["count"].value = "10.0.0.0/16", "1.000"
        screen.calc_subnet_view("ipv4", "aufteilen")
        result = fc.split_network("10.0.0.0/16", 1000, version=4)
        self.assertEqual(panel["explain"][1].data.value, fc.split_explain(result, schmal=True))
        self.assertTrue(panel["pager"].visible)
        for line in panel["explain"][1].data.value.splitlines():
            self.assertLessEqual(len(line), fc.CALC_EXPLAIN_HANDY_WIDTH, line)
        for line in panel["out"].data.value.splitlines():
            self.assertLessEqual(len(line), fc.CALC_EXPLAIN_HANDY_WIDTH, line)

    def test_ipv6_vorgabe_und_blaettern(self):
        screen = self.screen
        screen._on_subnet_mode("ipv6")
        screen._on_subnet_view("aufteilen")
        panel = screen.subnet_panels[("ipv6", "aufteilen")]
        _button, box = _explain(screen, "ipv6", "aufteilen")
        result6 = fc.split_network("2001:db8:abcd::/48", "6", version=6)
        self.assertEqual(box.data.value, fc.split_explain(result6, schmal=True))  # Beispiel C
        panel["count"].value = "65536"
        result = fc.split_network("2001:db8:abcd::/48", 65536, version=6)
        with mock.patch.object(fc, "split_network", wraps=fc.split_network) as rechnen:
            screen.calc_split()
            self.assertEqual(rechnen.call_count, 1)
            self.assertTrue(panel["pager"].visible)
            self.assertEqual(panel["page_text"].value, "Seite 1 von 8.192")
            self.assertTrue(panel["page_buttons"]["first"].disabled)
            self.assertTrue(panel["page_buttons"]["back"].disabled)
            self.assertFalse(panel["page_buttons"]["next"].disabled)
            screen.subnet_page("ipv6", "next")
            self.assertEqual(panel["out"].data.value, fc.split_report(result, 2, schmal=True))
            screen.subnet_page("ipv6", "last")
            self.assertEqual(panel["page_text"].value, "Seite 8.192 von 8.192")
            self.assertTrue(panel["page_buttons"]["last"].disabled)
            self.assertTrue(panel["page_buttons"]["next"].disabled)
            self.assertEqual(panel["out"].data.value, fc.split_report(result, 8192, schmal=True))
            screen.subnet_page("ipv6", "back")
            self.assertEqual(panel["page"], 8191)
            screen.subnet_page("ipv6", "first")
            self.assertEqual(panel["page"], 1)
            self.assertEqual(rechnen.call_count, 1)        # Blaettern rechnet nicht neu

    @unittest.skipUnless(HAT_SPRUNG, "Konstanten fuer den Seitensprung fehlen "
                                     "(Zweig version-063-kern)")
    def test_sprung_auf_seite(self):
        screen = self.screen
        panel = screen.subnet_panels[("ipv4", "aufteilen")]
        panel["count"].value = "64"
        screen.calc_split("ipv4")
        self.assertEqual(panel["page_text"].value, "Seite 1 von 8")
        self.assertIn(fc.SUBNET_PAGE_JUMP_FIELD,
                      [c.label for c in _walk(panel["pager"]) if isinstance(c, ft.Semantics)])
        self.assertIn(fc.SUBNET_PAGE_JUMP, _texts(panel["pager"]))
        panel["jump"].value = "3"
        screen.subnet_jump("ipv4")
        self.assertEqual(panel["page"], 3)
        panel["jump"].value = "1.000"                      # ueber das Ende: letzte Seite
        screen.subnet_jump("ipv4")
        self.assertEqual(panel["page"], 8)
        panel["jump"].value = "0"
        screen.subnet_jump("ipv4")
        self.assertEqual(panel["page"], 1)
        panel["jump"].value = "5"
        screen.subnet_jump("ipv4")
        before = panel["out"].data.value
        for wrong in ("abc", "2,5", ""):
            panel["jump"].value = wrong
            screen.subnet_jump("ipv4")
            self.assertEqual(panel["page"], 5, wrong)     # Fehler: Seite bleibt
            self.assertEqual(panel["out"].data.value, before, wrong)
        self.assertEqual(len(screen.toasts), 3)
        self.assertIn(fc.SUBNET_PAGE_JUMP_FIELD, screen.toasts[0])

    def test_nach_hostbedarf(self):
        screen = self.screen
        _button, box = _explain(screen, "ipv4", "bedarf")
        net, needs = fc.SUBNET_DEFAULTS[("ipv4", "bedarf")]
        result = fc.subnet_by_hosts(net, needs, version=4)
        self.assertEqual(box.data.value, fc.hosts_explain(result, schmal=True))  # Beispiel D
        screen.calc_hosts()
        self.assertEqual(_out(screen, "ipv4", "bedarf"), fc.hosts_report(result, schmal=True))

    def test_hostbedarf_passt_nicht_ist_ergebnis(self):
        screen = self.screen
        panel = screen.subnet_panels[("ipv4", "bedarf")]
        panel["needs"].value = "A 120\nB 60\nC 50\nD 20"            # Beispiel E
        screen.calc_hosts()
        self.assertEqual(screen.toasts, [])
        text = panel["out"].data.value
        self.assertIn("Es fehlen 32 Adressen.", text.replace("\n", " ").replace("  ", " "))
        result = fc.subnet_by_hosts("192.168.10.0/24", panel["needs"].value, version=4)
        self.assertEqual(panel["explain"][1].data.value, fc.hosts_explain(result, schmal=True))

    def test_version_des_schalters(self):
        screen = self.screen
        panel = screen.subnet_panels[("ipv4", "aufteilen")]
        panel["net"].value = "2001:db8::/48"
        screen.calc_split("ipv4")
        self.assertEqual(screen.toasts, ["Im Modus IPv4 bitte ein IPv4-Netz angeben "
                                         "(z. B. 192.168.10.0/24)."])
        screen._on_subnet_mode("ipv6")
        screen._on_subnet_view("aufteilen")
        panel6 = screen.subnet_panels[("ipv6", "aufteilen")]
        panel6["net"].value = "10.0.0.0/8"
        screen.calc_split()
        self.assertEqual(screen.toasts[-1], "Im Modus IPv6 bitte ein IPv6-Netz angeben "
                                            "(z. B. 2001:db8:abcd::/48).")
        bedarf = screen.subnet_panels[("ipv4", "bedarf")]
        bedarf["net"].value = "2001:db8::/48"
        screen.calc_hosts()
        self.assertTrue(screen.toasts[-1].startswith("Im Modus IPv4"))   # N-M-4


class FehlerLeerenTest(unittest.TestCase):
    """B-D-04 (Teil 0.63): nach einer Fehleingabe ist der Kasten leer."""

    def setUp(self):
        self.screen = _screen()

    def _pruefe(self, mode, view, setze, rechne):
        screen = self.screen
        panel = screen.subnet_panels[(mode, view)]
        rechne()
        self.assertNotEqual(panel["out"].data.value, "", (mode, view))
        button, box = panel["explain"]
        button.controls[0]._handler(None)                   # Rechenweg aufklappen
        self.assertTrue(box.visible)
        text_vorher = box.data.value
        setze(panel)
        anzahl = len(screen.toasts)
        rechne()
        self.assertEqual(len(screen.toasts), anzahl + 1, (mode, view))
        self.assertEqual(panel["out"].data.value, "", (mode, view))
        self.assertFalse(box.visible, (mode, view))         # Rechenweg zu
        self.assertEqual(box.data.value, text_vorher)       # letzte gueltige Rechnung
        self.assertEqual(button.controls[0].caption.value, "Rechenweg anzeigen")

    def test_netzdaten(self):
        def setze(panel):
            panel["net"].value = "kein Netz"
        self._pruefe("ipv4", "netzdaten", setze, lambda: self.screen.calc_subnet(mode="ipv4"))
        self._pruefe("ipv6", "netzdaten", setze, lambda: self.screen.calc_subnet(mode="ipv6"))

    def test_aufteilen(self):
        def setze(panel):
            panel["count"].value = "0"
        for mode in ("ipv4", "ipv6"):
            self._pruefe(mode, "aufteilen", setze, lambda m=mode: self.screen.calc_split(m))

    def test_aufteilen_blaettern_weg(self):
        screen = self.screen
        panel = screen.subnet_panels[("ipv4", "aufteilen")]
        panel["count"].value = "64"
        screen.calc_split("ipv4")
        self.assertTrue(panel["pager"].visible)
        panel["count"].value = "512"                        # zu viele Subnetze
        screen.calc_split("ipv4")
        self.assertEqual(panel["out"].data.value, "")
        self.assertFalse(panel["pager"].visible)
        self.assertIsNone(panel["result"])
        screen.subnet_page("ipv4", "next")                  # ohne Ergebnis: nichts
        self.assertEqual(panel["out"].data.value, "")
        self.assertTrue(screen.toasts[-1].startswith("Zu viele Subnetze: /24 + 9 Bit"))

    def test_hostbedarf(self):
        def setze(panel):
            panel["needs"].value = "A 50, B 20"
        self._pruefe("ipv4", "bedarf", setze, self.screen.calc_hosts)

    def test_raid_und_bildschirm(self):
        screen = self.screen
        screen.calc_raid()
        self.assertIn("Nutzkapazität", screen.out_raid.data.value)
        screen.entry_disks.value = "abc"
        screen.calc_raid()
        self.assertEqual(screen.out_raid.data.value, "")
        screen.calc_screen()
        self.assertNotEqual(screen.out_screen.data.value, "")
        screen.entry_width.value = "-5"
        screen.calc_screen()
        self.assertEqual(screen.out_screen.data.value, "")
        self.assertEqual(len(screen.toasts), 2)

    def test_usv_mit_bild(self):
        screen = self.screen
        self.assertIn("USV passend", screen.out_ups.data.value)
        self.assertTrue(screen.ups_picture.column.controls)
        screen.ups_entries["last"].value = "abc"
        screen.calc_ups("akku")
        self.assertEqual(screen.out_ups.data.value, "")
        self.assertEqual(screen.out_ups_hint.value, "")
        self.assertEqual(screen.ups_picture.label, "")
        self.assertEqual(len(screen.toasts), 1)
        # Wieder richtig: alles wieder da
        screen.ups_entries["last"].value = "600"
        screen.calc_ups("empfehlung")
        self.assertIn("USV passend", screen.out_ups.data.value)
        self.assertTrue(screen.ups_picture.label.startswith("Bild: Last 600 W"))

    def test_fehler_wird_sofort_gezeichnet(self):
        """Im Browser gesehen: Nach dem Hinweis (page.show_dialog) zeichnet
        Flet die uebrigen Aenderungen nicht mehr von selbst. Der geleerte
        Kasten muss darum ausdruecklich gezeichnet werden."""
        screen = self.screen
        gezeichnet = []

        def merke(*controls):
            gezeichnet.extend(id(c) for c in controls)
            # zum Zeitpunkt des Zeichnens ist der Kasten schon leer
            for c in controls:
                data = getattr(c, "data", None)
                if c in kaesten:
                    self.assertEqual(data.value, "")
        panels = screen.subnet_panels
        kaesten = [panels[k]["out"] for k in panels] + [screen.out_raid, screen.out_screen,
                                                        screen.out_ups]
        faelle = [
            (lambda: setattr(panels[("ipv4", "netzdaten")]["net"], "value", "x"),
             lambda: screen.calc_subnet(mode="ipv4"), panels[("ipv4", "netzdaten")]),
            (lambda: setattr(panels[("ipv6", "aufteilen")]["count"], "value", "0"),
             lambda: screen.calc_split("ipv6"), panels[("ipv6", "aufteilen")]),
            (lambda: setattr(panels[("ipv4", "bedarf")]["needs"], "value", "A 1, B 2"),
             screen.calc_hosts, panels[("ipv4", "bedarf")]),
        ]
        with mock.patch.object(handy, "_redraw", merke):
            for setze, rechne, panel in faelle:
                rechne()
                gezeichnet.clear()
                setze()
                rechne()
                self.assertIn(id(panel["box"]), gezeichnet, panel["view"])
            screen.calc_raid()
            gezeichnet.clear()
            screen.entry_disks.value = "abc"
            screen.calc_raid()
            self.assertIn(id(screen.out_raid), gezeichnet)
            gezeichnet.clear()
            screen.entry_width.value = "abc"
            screen.calc_screen()
            self.assertIn(id(screen.out_screen), gezeichnet)
            gezeichnet.clear()
            screen.ups_entries["last"].value = "abc"
            screen.calc_ups("akku")
            for control in (screen.out_ups, screen.out_ups_hint, screen.ups_picture):
                self.assertIn(id(control), gezeichnet)

    def test_usv_plus_null_prozent(self):
        """Schutz (D-5): Alterung "-0" zeigt "+0 %", nie "+-"."""
        screen = self.screen
        for value in ("-0", "-0,0", "0"):
            screen.ups_entries["alterung"].value = value
            screen.calc_ups("akku")
            self.assertIn("(+0 %)", screen.out_ups.data.value, value)
            self.assertNotIn("+-", screen.out_ups.data.value, value)


class ModuswechselTest(unittest.TestCase):
    """T-UI-5 (Plan 0.63 4.6) am Handy."""

    def setUp(self):
        self.screen = _screen()

    def test_wechsel_behaelt_alles_und_rechnet_nicht(self):
        screen = self.screen
        panel = screen.subnet_panels[("ipv4", "aufteilen")]
        screen.view_pills["ipv4"].select_value("aufteilen")
        panel["net"].value, panel["count"].value = "10.0.0.0/16", "100"
        screen.calc_split("ipv4")
        screen.subnet_page("ipv4", "next")
        text = panel["out"].data.value
        button, box = panel["explain"]
        button.controls[0]._handler(None)
        self.assertTrue(box.visible)
        zaehler = {}
        patches = [mock.patch.object(fc, name, wraps=getattr(fc, name))
                   for name in ("split_network", "split_report", "subnet_by_hosts",
                                "split_explain", "hosts_explain")]
        patches.append(mock.patch.object(handy, "subnet_report", wraps=fc.subnet_report))
        mocks = [p.start() for p in patches]
        try:
            screen.mode_pills.select(1)                     # IPv6 wie getippt
            self.assertEqual(screen.subnet_mode, "ipv6")
            self.assertEqual(screen.subnet_card.subtitle_text.value, "IPv6")
            self.assertTrue(screen.view_pills["ipv6"].visible)
            self.assertFalse(screen.view_pills["ipv4"].visible)
            self.assertTrue(screen.subnet_panels[("ipv6", "netzdaten")]["box"].visible)
            self.assertFalse(panel["box"].visible)
            screen.mode_pills.select(0)
            for name, mocked in zip(("split_network", "split_report", "subnet_by_hosts",
                                     "split_explain", "hosts_explain", "subnet_report"),
                                    mocks):
                zaehler[name] = mocked.call_count
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(set(zaehler.values()), {0}, zaehler)   # keine neue Rechnung
        self.assertTrue(panel["box"].visible)
        self.assertEqual(screen.view_pills["ipv4"].get(), "aufteilen")
        self.assertEqual((panel["net"].value, panel["count"].value), ("10.0.0.0/16", "100"))
        self.assertEqual(panel["out"].data.value, text)
        self.assertEqual(panel["page"], 2)
        self.assertFalse(box.visible)                       # Rechenweg zu
        self.assertEqual(button.controls[0].caption.value, "Rechenweg anzeigen")
        self.assertEqual(screen.app.scrolled, 2)            # je Wechsel an den Anfang

    def test_hostbedarf_und_ipv6(self):
        screen = self.screen
        screen.view_pills["ipv4"].select_value("bedarf")
        screen.mode_pills.select_value("ipv6")
        sichtbar = [k for k, p in screen.subnet_panels.items() if p["box"].visible]
        self.assertEqual(sichtbar, [("ipv6", "netzdaten")])
        screen.view_pills["ipv6"].select_value("aufteilen")
        screen.mode_pills.select_value("ipv4")
        sichtbar = [k for k, p in screen.subnet_panels.items() if p["box"].visible]
        self.assertEqual(sichtbar, [("ipv4", "bedarf")])
        screen.mode_pills.select_value("ipv6")
        sichtbar = [k for k, p in screen.subnet_panels.items() if p["box"].visible]
        self.assertEqual(sichtbar, [("ipv6", "aufteilen")])

    def test_ansichtswechsel_klappt_rechenweg_zu(self):
        screen = self.screen
        button, box = screen.subnet_panels[("ipv4", "netzdaten")]["explain"]
        button.controls[0]._handler(None)
        screen.view_pills["ipv4"].select_value("aufteilen")
        screen.view_pills["ipv4"].select_value("netzdaten")
        self.assertFalse(box.visible)
        self.assertEqual(screen.app.scrolled, 0)            # nur der Moduswechsel springt

    def test_fehler_bleibt_im_modus(self):
        screen = self.screen
        screen.calc_subnet(mode="ipv4")
        screen._on_subnet_mode("ipv6")
        screen.subnet_panels[("ipv6", "netzdaten")]["net"].value = "kaputt"
        screen.calc_subnet()
        self.assertEqual(_out(screen, "ipv6", "netzdaten"), "")
        screen._on_subnet_mode("ipv4")
        self.assertEqual(screen.out_subnet.data.value, fc.subnet_report("192.168.1.50/24"))

    def test_neustart_immer_ipv4(self):
        self.screen._on_subnet_mode("ipv6")
        neu = _screen()
        self.assertEqual(neu.subnet_mode, "ipv4")
        self.assertEqual(neu.mode_pills.get(), "ipv4")
        self.assertEqual(neu.subnet_card.subtitle_text.value, "IPv4")


class SchnittstelleTest(unittest.TestCase):
    """B-E-01/B-E-02: Aufrufe der Schnittstelle "Anzeige Handy"."""

    def test_erkennung_passt_zu_ui(self):
        self.assertEqual(handy.UI_FIT, "fit" in inspect.signature(ui.read_box).parameters)
        self.assertEqual(handy.UI_UMBRECHEN,
                         "umbrechen" in inspect.signature(ui.PillGroup.__init__).parameters)

    def test_aufrufe(self):
        boxes, pills = {}, {}
        real_box, real_pills = ui.read_box, ui.PillGroup

        def box(*args, **kwargs):
            made = real_box(*args, **kwargs)
            boxes[id(made)] = kwargs
            return made

        def group(*args, **kwargs):
            made = real_pills(*args, **kwargs)
            pills[id(made)] = kwargs
            return made
        with mock.patch.object(ui, "read_box", box), mock.patch.object(ui, "PillGroup", group):
            screen = _screen()
        ergebnis = [screen.out_subnet, screen.out_raid, screen.out_screen, screen.out_ups]
        ergebnis += [p["out"] for p in screen.subnet_panels.values()]
        self.assertEqual(len({id(b) for b in ergebnis}), 8)
        for made in ergebnis:
            self.assertEqual(boxes[id(made)].get("fit", False), handy.UI_FIT)
            self.assertTrue(boxes[id(made)].get("scroll"))
        # Ab 0.63.2 (A3, Meldung S2c, FG-Antrag): Rechenwege setzen sich wie
        # die Ergebnisse auf die Breite (sonst bei Sehr gross abgeschnitten),
        # bleiben aber wischbar (Test 6); Aufgaben bleiben ohne fit
        for panel in screen.subnet_panels.values():
            self.assertEqual(boxes[id(panel["explain"][1])].get("fit", False), handy.UI_FIT)
            self.assertTrue(boxes[id(panel["explain"][1])].get("scroll"))
        self.assertNotIn("fit", boxes[id(screen.out_ups_task)])
        umbrechend = [screen.raid_pills, screen.depth_pills, screen.mode_pills,
                      *screen.view_pills.values()]
        for made in umbrechend:
            self.assertEqual(pills[id(made)].get("umbrechen", False), handy.UI_UMBRECHEN)
        self.assertNotIn("umbrechen", pills[id(screen.ups_unit)])

    @unittest.skipUnless("fit" in inspect.signature(ui.read_box).parameters,
                         "ui.py ohne fit (Zweig version-063-anzeige)")
    def test_wischbar_mit_fit(self):
        """Test 6 bleibt gueltig: die Kaesten wischen weiter seitlich."""
        screen = _screen()
        for box in (screen.out_subnet, screen.out_raid, screen.out_screen, screen.out_ups):
            self.assertIsInstance(box.content, ft.Row)
            self.assertIsNotNone(box.content.scroll)
            self.assertTrue(box.data.no_wrap)


if __name__ == "__main__":
    unittest.main(verbosity=2)
