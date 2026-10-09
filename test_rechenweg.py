#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests ab 0.62.3 (Plan 0.62.3, Teil E): Rechenwege am Handy und Pruefung aller
Rechenwege und Rechner-Anzeigen.

  Test 1   Handy-Fassungen: hoechstens 28 Zeichen je Zeile
  Test 2   Handy-Fassungen: dieselben Zahlen wie am PC (Zusatzzahlen nur aus
           einer ausdruecklichen Liste: Oktett-Nummern, Dezimalwert je Oktett)
  Test 2b  Ergebnisse in derselben Reihenfolge wie am PC
  Test 3   dieselben Schritt-Ueberschriften
  Test 4   alle angezeigten Zahlen gleich der Ausgangsbasis v0.62.2
           (pruefung/rechenweg_basis_0622.json), ausser den freigegebenen
           Aenderungen Z1-Z12, Z14, Z15 - jede einzeln mit vorher/nachher;
           dazu deutsche Schreibweise der Anzeigen (Z4, Z7) und fps 30 (Z8)
  Test 5   Spalten gerade ("=", Punkte, Bitreihen)
  Test 6   Handy: Box ohne Umbruch, seitlich wischbar; USV-Hinweis ausserhalb
  Test 7   grosse Netze schnell, erste/letzte Host-Adresse wie bisher
  Test 9   PC-Trainer unveraendert bis auf freigegebenen Wortlaut; Handy-Form
           von Schritt 3 mit denselben Werten
  Z12      RAID 10 mit 4, 6, 8 Festplatten (2, 3, 4), ungerade: ungueltig

Test 8 (Fingerabdruck der Spielwerte) ist das vorhandene Werkzeug aus dem
Bericht 0.54; Ergebnis steht im Bericht 0.62.3.

Start:  python test_rechenweg.py
"""

import json
import os
import re
import sys
import tempfile
import time
import unittest
from collections import Counter
from difflib import SequenceMatcher

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.join(HERE, "pruefung"))

import fisi_core as fc            # noqa: E402
import fisi_lernen as fl          # noqa: E402
import rechenweg_texte as rt      # noqa: E402

GRENZE = 28    # Freigabe 0.62.3 (F-P2): Anheben nur mit Freigabe

PAARE = [("SUBNET", fc.CALC_EXPLAIN_SUBNET, fc.CALC_EXPLAIN_SUBNET_HANDY),
         ("RAID", fc.CALC_EXPLAIN_RAID, fc.CALC_EXPLAIN_RAID_HANDY),
         ("SCREEN", fc.CALC_EXPLAIN_SCREEN, fc.CALC_EXPLAIN_SCREEN_HANDY),
         ("UPS", fc.CALC_EXPLAIN_UPS, fc.CALC_EXPLAIN_UPS_HANDY)]

# Test 2: Zahlen, die nur die Handy-Fassung hat (Bitreihen Oktett fuer Oktett)
ZUSATZ = {
    "SUBNET": Counter(
        # Schritt 1: "1. Oktett 11111111 = 255" ... (255/0 stehen auch am PC)
        ["n:1", "n:2", "n:3", "n:4"]
        # Schritt 2: Oktett-Nummer, Dezimalwert der Adresse und der Maske
        + ["n:1", "n:192", "n:255", "n:2", "n:168", "n:255", "n:3", "n:1", "n:255",
           "n:4", "n:50", "n:0"]),
    "RAID": Counter(), "SCREEN": Counter(), "UPS": Counter(),
}
# Test 2b: beim Subnetting die Ergebniswerte (die Bitreihen stehen am Handy
# anders); bei den anderen Rechenwegen muss die ganze Zahlenfolge gleich sein
ERGEBNISSE = {"SUBNET": {"ip:255.255.255.0", "ip:192.168.1.0", "ip:0.0.0.255",
                         "ip:192.168.1.255", "n:256", "n:254", "ip:192.168.1.1",
                         "ip:192.168.1.254"}}

# Test 4: freigegebene Aenderungen angezeigter Zahlen (Freigabe Plan 0.62.3,
# Abschnitt 4.2), je Quelle als Liste (Art, Stelle, vorher, nachher, Nummer).
# Stelle = Index in der Zahlenfolge der Ausgangsbasis.
FREIGEGEBEN = {
    "upsaufgabe:5": [("replace", 13, ["n:390.62"], ["n:390.63"], "Z1"),
                     ("replace", 18, ["n:390.62"], ["n:390.63"], "Z1")],
    "subnet:192.168.10.1/31": [("replace", 3, ["ip:192.168.10.1"], ["n:31", "n:3021"], "Z2")],
    "raid:RAID 5|4|1,5": [("replace", 2, ["n:2"], ["n:1.5"], "Z3")],
    "raid:RAID 5|3|0,5": [("replace", 2, ["n:0"], ["n:0.5"], "Z3")],
    "text:CALC_EXPLAIN_SCREEN": [("replace", 11, ["n:16.7"], ["n:16.8"], "Z5")],
    "upsaufgabe:4": [("insert", 9, [], ["n:1", "n:6"], "Z6"),
                     ("replace", 11, ["n:0.1667"], ["n:1", "n:6"], "Z6")],
    "raid:RAID 10|4|1000": [("insert", 8, [], ["n:2"], "Z12")],
    "raid:RAID 10|6|2000": [("insert", 8, [], ["n:3"], "Z12")],
    "raid:RAID 10|8|1000": [("insert", 8, [], ["n:4"], "Z12")],
    "text:CALC_EXPLAIN_RAID": [("insert", 13, [], ["n:2"], "Z15"),
                               ("insert", 45, [], ["n:2"], "Z12")],
    "text:CALC_EXPLAIN_SUBNET": [("insert", 54, [], ["n:2", "n:128"], "Z14")],
}
# Aenderungen nur der Schreibweise (Wert gleich, Test 4 vergleicht Werte):
# Z4 deutsche Zahlen in den Anzeigen, Z7 IPv6 gegliedert, Z9 KiB/MiB/GiB/MiB/s,
# Z10 "Abzug von 2 Adressen" (Wert 2 bleibt), Z11 "1.200 VA"/"1.000 W".
SCHREIBWEISE = {
    "Z4": ("screen:1920|1080|24|30", ["2.073.600", "6.220.800 Byte", "6.075,00 KiB",
                                       "49.766.400 Bit"]),
    "Z4 RAID": ("raid:RAID 5|4|1000", ["4.000,00 GB", "75,0 %", "4 x 1.000 GB"]),
    "Z4 Subnetz": ("subnet:10.20.30.40/8", ["16.777.214", "16.777.216"]),
    "Z7": ("subnet:2001:db8::1/64", ["18.446.744.073.709.551.616"]),
    "Z9": ("screen:1920|1080|24|30", ["177,98 MiB/s", "1.492,99 Mbit/s", "10,43 GiB/Minute",
                                       "5,93 MiB"]),
    "Z10": ("text:CALC_EXPLAIN_SUBNET", ["Abzug von 2 Adressen"]),
    "Z11": ("upsaufgabe:3", ["1.200 VA", "1.500 VA und 1.000 W"]),
    "Z11 Rechenweg": ("text:CALC_EXPLAIN_UPS", ["USV 1.500 VA / 900 W", "667 / 1.500 = 44 %"]),
}


def _oktette(tokens):
    """Bitreihen in einzelne Oktette zerlegen (PC: eine Reihe, Handy: je Oktett)."""
    out = []
    for token in tokens:
        if token.startswith("bits:"):
            out += ["okt:" + part for part in token[5:].split(".")]
        elif re.fullmatch(r"[sn]:[01]{8}", token):
            out.append("okt:" + token[2:].zfill(8))
        else:
            out.append(token)
    return out


def _zahlen(text):
    return _oktette(rt.zahlen(text, "de"))


def _ueberschriften(text):
    """Nicht eingerueckte Zeilen, Absatz fuer Absatz zusammengesetzt."""
    heads, current = [], []
    for line in text.split("\n"):
        if line and not line.startswith(" "):
            current.append(line)
        elif current:
            heads.append(" ".join(current))
            current = []
    if current:
        heads.append(" ".join(current))
    return heads


class HandyFassungTest(unittest.TestCase):
    def test_1_zeilenlaenge(self):
        self.assertEqual(fc.CALC_EXPLAIN_HANDY_WIDTH, GRENZE)
        for name, _pc, handy in PAARE:
            for number, line in enumerate(handy.split("\n"), 1):
                self.assertLessEqual(len(line), GRENZE, "%s Zeile %d hat %d Zeichen: %r"
                                     % (name, number, len(line), line))

    def test_2_gleiche_zahlen(self):
        for name, pc, handy in PAARE:
            pc_z, handy_z = Counter(_zahlen(pc)), Counter(_zahlen(handy))
            self.assertEqual(pc_z - handy_z, Counter(), "%s: Zahlen fehlen am Handy" % name)
            self.assertEqual(handy_z - pc_z, ZUSATZ[name],
                             "%s: Zusatzzahlen am Handy nicht wie erlaubt" % name)

    def test_2b_reihenfolge_der_ergebnisse(self):
        for name, pc, handy in PAARE:
            keep = ERGEBNISSE.get(name)
            pc_z = [z for z in _zahlen(pc) if keep is None or z in keep]
            handy_z = [z for z in _zahlen(handy) if keep is None or z in keep]
            self.assertEqual(pc_z, handy_z, "%s: Reihenfolge der Ergebnisse" % name)

    def test_3_gleiche_schritte(self):
        for name, pc, handy in PAARE:
            pc_h, handy_h = _ueberschriften(pc), _ueberschriften(handy)
            self.assertGreaterEqual(len(pc_h), 4, name)
            self.assertEqual(pc_h, handy_h, "%s: Schritte" % name)

    def test_handy_waehlt_handy_fassung(self):
        with open(os.path.join(HERE, "mobile", "src", "main.py"), encoding="utf-8") as handle:
            source = handle.read()
        for name in ("SUBNET", "RAID", "SCREEN", "UPS"):
            self.assertIn("self._explain(CALC_EXPLAIN_%s_HANDY)" % name, source)
            self.assertNotIn("self._explain(CALC_EXPLAIN_%s)" % name, source)
        with open(os.path.join(HERE, "app_gui.py"), encoding="utf-8") as handle:
            pc = handle.read()
        self.assertNotIn("_HANDY", pc)


class ZahlenUnveraendertTest(unittest.TestCase):
    """Test 4: alle Zahlen gleich der Ausgangsbasis, ausser Z1-Z12, Z14, Z15."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(HERE, "pruefung", "rechenweg_basis_0622.json")
        with open(path, encoding="utf-8") as handle:
            cls.basis = json.load(handle)["texte"]
        cls.neu = rt.erzeuge(fc, fl)

    def test_4_alle_quellen(self):
        self.assertEqual(set(self.basis), set(self.neu))
        self.assertGreaterEqual(len(self.basis), 500)
        gefunden, zahlen = {}, 0
        for quelle in sorted(self.basis):
            alt = rt.zahlen(self.basis[quelle], rt.schreibweise_alt(quelle))
            neu = rt.zahlen(self.neu[quelle], "de")
            zahlen += len(alt)
            ops = [(art, i1, alt[i1:i2], neu[j1:j2])
                   for art, i1, i2, j1, j2 in SequenceMatcher(a=alt, b=neu, autojunk=False)
                   .get_opcodes() if art != "equal"]
            if ops:
                gefunden[quelle] = ops
        erwartet = {quelle: [eintrag[:4] for eintrag in liste]
                    for quelle, liste in FREIGEGEBEN.items()}
        self.assertEqual(gefunden, erwartet)
        self.assertGreater(zahlen, 10000)

    def test_4_jede_freigabe_einzeln(self):
        nummern = sorted({e[4] for liste in FREIGEGEBEN.values() for e in liste})
        self.assertEqual(nummern, ["Z1", "Z12", "Z14", "Z15", "Z2", "Z3", "Z5", "Z6"])

    def test_4_schreibweise(self):
        for nummer, (quelle, teile) in SCHREIBWEISE.items():
            for teil in teile:
                self.assertIn(teil, self.neu[quelle], "%s: %s" % (nummer, quelle))

    def test_4_anzeigen_deutsch(self):
        for quelle, text in self.neu.items():
            art = quelle.split(":", 1)[0]
            if art in ("raid", "screen"):
                self.assertIsNone(re.search(r"\d,\d{3}(?!\d)|\b\d+\.\d{1,2}\b", text),
                                  "%s englisch: %s" % (quelle, text))
            if art == "subnet":
                for line in text.split("\n"):
                    if "Hosts" in line or "Adressen gesamt" in line:
                        self.assertIsNone(re.search(r"\d{4}", line), line)

    def test_4_z2_nur_31(self):
        self.assertIn("Broadcast-Adresse     : keine (/31, RFC 3021)",
                      fc.subnet_report("192.168.10.1/31"))
        for value in ("192.168.10.1/30", "192.168.10.7/32"):
            self.assertNotIn("keine", fc.subnet_report(value))

    def test_4_z8_fps_vorgabe_30(self):
        for path, pattern in (("app_gui.py", r'self\.entry_fps = EntryBox\([^)]*value="30"\)'),
                              (os.path.join("mobile", "src", "main.py"),
                               r'self\.entry_fps = ui\.entry\("30"')):
            with open(os.path.join(HERE, path), encoding="utf-8") as handle:
                self.assertRegex(handle.read(), pattern, path)
        anzeige = fc.screen_report("1920", "1080", "24", "30")
        for wert in ("177,98", "1.492,99", "10,43"):
            self.assertIn(wert, anzeige)
            self.assertIn(wert, fc.CALC_EXPLAIN_SCREEN)


class SpaltenTest(unittest.TestCase):
    """Test 5: '=', Punkte und Bitreihen stehen untereinander."""

    def test_5_subnetting_pc(self):
        lines = fc.CALC_EXPLAIN_SUBNET.split("\n")
        bits = next(line for line in lines if line.startswith("   /24 = "))
        dec = lines[lines.index(bits) + 1]
        punkte = [i for i, c in enumerate(bits) if c == "."]
        self.assertEqual([i for i, c in enumerate(dec) if c == "."], punkte)
        self.assertEqual(dec.index("="), bits.index("="))
        rows = [line for line in lines if re.search(r"= [01]{8}\.", line) and line != bits]
        self.assertEqual(len(rows), 3)
        self.assertEqual(len({row.index("=") for row in rows}), 1)
        self.assertEqual(len({len(row) for row in rows}), 1)
        dash = next(line for line in lines if line.strip().startswith("-----"))
        self.assertEqual(len(dash), len(rows[0]))

    def test_5_subnetting_handy(self):
        lines = fc.CALC_EXPLAIN_SUBNET_HANDY.split("\n")
        rows = [line for line in lines if re.search(r"= [01]{8}$", line)]
        self.assertEqual(len(rows), 12)
        self.assertEqual(len({row.index("=") for row in rows}), 1)
        okt = [line for line in lines if re.match(r" \d\. Oktett [01]{8} = ", line)]
        self.assertEqual(len(okt), 4)
        self.assertEqual(len({row.index("=") for row in okt}), 1)

    def test_5_trainer(self):
        for level in (1, 2, 3):
            for seed in range(40):
                task = fl.trainer_task("ipv4", level, "e3-%d" % seed)
                rows = [s for s in task.steps if re.search(r"[01]{8}\.[01]{8}", s)]
                self.assertEqual(len(rows), 3)
                self.assertEqual(len({re.search(r"[01]{8}\.", s).start() for s in rows}), 1,
                                 rows)
                narrow = fl.trainer_task("ipv4", level, "e3-%d" % seed, schmal=True)
                rows = [s for s in narrow.steps if re.search(r" [01]{8}( = \d+)?$", s)]
                self.assertEqual(len(rows), 12)
                self.assertEqual(len({re.search(r"[01]{8}", s).start() for s in rows}), 1)

    def test_5_anzeigen(self):
        for text in (fc.screen_report("1920", "1080", "24", "30"),
                     fc.raid_report("RAID 10", "6", "2000"), fc.subnet_report("10.0.0.1/8")):
            spalten = {line.index(":") for line in text.split("\n") if ":" in line[:24]}
            self.assertEqual(spalten, {22}, text)


class BoxTest(unittest.TestCase):
    """Test 6: Box ohne Umbruch (A) am Handy, USV-Hinweis ausserhalb."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(1, os.path.join(HERE, "mobile", "src"))
        import flet as ft
        import main as handy
        import ui
        cls.ft, cls.handy, cls.ui = ft, handy, ui

    def _wischbar(self, box):
        return (isinstance(box.content, self.ft.Row) and box.content.scroll is not None
                and box.data is box.content.controls[0] and box.data.no_wrap)

    def test_6_read_box(self):
        box = self.ui.read_box("x", mono=True, scroll=True)
        self.assertTrue(self._wischbar(box))
        self.ui.set_box(box, "neu")
        self.assertEqual(box.data.value, "neu")
        plain = self.ui.read_box("x")
        self.assertIs(plain.content, plain.data)
        self.assertFalse(plain.data.no_wrap)

    def test_6_rechner(self):
        screen = self.handy.CalcScreen.__new__(self.handy.CalcScreen)
        screen.toast = lambda *args: None
        db = fc.DBManager(os.path.join(tempfile.mkdtemp(prefix="fisi rechenweg "), "t.db"))
        screen.app = type("App", (), {"db": db, "sync": None})()
        screen.build()
        for box in (screen.out_subnet, screen.out_raid, screen.out_screen, screen.out_ups):
            self.assertTrue(self._wischbar(box))
        erklaert = []

        def walk(control):
            if isinstance(control, self.ft.Container) and isinstance(
                    getattr(control, "data", None), self.ft.Text):
                erklaert.append(control)
            for name in ("content", "controls"):
                child = getattr(control, name, None)
                for item in child if isinstance(child, list) else [child]:
                    if item is not None and hasattr(item, "__dict__"):
                        walk(item)
        walk(screen.calc_box)
        texte = {box.data.value: box for box in erklaert}
        for name, _pc, handy in PAARE:
            self.assertIn(handy, texte, name)
            self.assertTrue(self._wischbar(texte[handy]), name)
        # USV: Tabelle wischt, Hinweis bricht als normaler Text um
        screen.calc_ups("empfehlung")
        self.assertIn("USV passend", screen.out_ups.data.value)
        self.assertNotIn(fc.UPS_SIMPLE_TEXT, screen.out_ups.data.value)
        self.assertEqual(screen.out_ups_hint.value, fc.UPS_SIMPLE_TEXT)
        self.assertNotIsInstance(screen.out_ups_hint, self.ft.Container)
        # Rechner-Anzeigen ueber set_box
        screen.calc_raid()
        self.assertIn("Nutzkapazität", screen.out_raid.data.value)


class GrosseNetzeTest(unittest.TestCase):
    """Test 7: /8 schnell, /0 laeuft durch, erste/letzte Host-Adresse wie bisher."""

    def test_7_zeit(self):
        start = time.perf_counter()
        fc.subnet_report("10.0.0.1/8")
        self.assertLess(time.perf_counter() - start, 0.5)
        start = time.perf_counter()
        text = fc.subnet_report("0.0.0.0/0")
        self.assertLess(time.perf_counter() - start, 0.5)
        self.assertIn("Letzte Host-Adresse   : 255.255.255.254", text)

    def test_7_wie_der_alte_weg(self):
        import ipaddress
        for prefix in range(0, 33):
            network = ipaddress.ip_network("172.20.200.17/%d" % prefix, strict=False)
            values = fc.ipv4_values(network)
            if prefix >= 12:
                hosts = list(network.hosts())          # alter Weg (bis 0.62.2)
                first = hosts[0] if hosts else network.network_address
                last = hosts[-1] if hosts else network.broadcast_address
            else:
                # alter Weg ohne Liste nachgebaut: hosts() = alle ausser Netz/Broadcast
                first, last = network[1], network[-2]
            self.assertEqual((values["erste"], values["letzte"]), (first, last), prefix)


class TrainerTest(unittest.TestCase):
    """Test 9: PC-Trainer unveraendert bis auf den freigegebenen Wortlaut."""

    ERSETZEN = [   # (vorher, nachher, Befund)
        ("Feld: Broadcast\n", "Feld: Broadcast-Adresse\n", "1.2"),
        ("Feld: Erster Host\n", "Feld: Erste Host-Adresse\n", "1.3"),
        ("Feld: Letzter Host\n", "Feld: Letzte Host-Adresse\n", "1.3"),
        ("3. Adresse binär:  ", "3. Adresse binär:   ", "1.23"),
        ("   Maske binär:    ", "   Maske binär:     ", "1.23"),
        ("4. Broadcast: alle", "4. Broadcast-Adresse: alle", "1.2"),
        ("bis Broadcast - 1)", "bis Broadcast-Adresse - 1)", "1.2"),
        (", Broadcast ", ", Broadcast-Adresse ", "1.2"),
        ("·16^", " x 16^", "1.20"),
    ]

    @classmethod
    def setUpClass(cls):
        path = os.path.join(HERE, "pruefung", "rechenweg_basis_0622.json")
        with open(path, encoding="utf-8") as handle:
            cls.basis = json.load(handle)["texte"]

    def test_9_pc_text(self):
        count = 0
        for kind, _name in fl.TRAINER_KINDS:
            for level, _label in fl.TRAINER_LEVELS:
                for seed in range(rt.TRAINER_SEEDS):
                    alt = self.basis["trainer:%s|%d|%d" % (kind, level, seed)]
                    for before, after, _nr in self.ERSETZEN:
                        alt = alt.replace(before, after)
                    neu = rt.trainer_text(fl.trainer_task(kind, level, "e3-%d" % seed))
                    self.assertEqual(neu, alt, (kind, level, seed))
                    count += 1
        self.assertEqual(count, 480)

    def test_9_handy_form(self):
        for level in (1, 2, 3):
            for seed in range(40):
                pc = fl.trainer_task("ipv4", level, "e3-%d" % seed)
                handy = fl.trainer_task("ipv4", level, "e3-%d" % seed, schmal=True)
                self.assertEqual((handy.text, handy.fields, handy.solution),
                                 (pc.text, pc.fields, pc.solution))
                start = pc.steps.index(next(s for s in pc.steps if s.startswith("3. ")))
                block = handy.steps[start:start + 18]
                self.assertEqual(handy.steps[:start] + handy.steps[start + 18:],
                                 pc.steps[:start] + pc.steps[start + 3:])
                self.assertTrue(all(len(line) <= GRENZE for line in block), block)
                pc_z = Counter(_zahlen("\n".join(pc.steps[start:start + 3])))
                handy_z = Counter(_zahlen("\n".join(block)))
                self.assertEqual(pc_z - handy_z, Counter())
                netz = [int(o) for o in pc.solution["netz"].split(".")]
                self.assertEqual(handy_z - pc_z, Counter(["n:%d" % n for n in (1, 2, 3, 4)]
                                                         + ["n:%d" % n for n in netz]))

    def test_9_handy_nutzt_schalter(self):
        with open(os.path.join(HERE, "mobile", "src", "main.py"), encoding="utf-8") as handle:
            self.assertIn("random.randrange(1 << 30), schmal=True)", handle.read())
        with open(os.path.join(HERE, "app_gui.py"), encoding="utf-8") as handle:
            self.assertNotRegex(handle.read(), r"trainer_(round|task)\([^)]*schmal")


class Raid10Test(unittest.TestCase):
    """Z12 (Auflage): 4, 6, 8 Festplatten -> bis zu 2, 3, 4; ungerade -> ungueltig."""

    def test_z12_gerade(self):
        for disks, upto in ((4, 2), (6, 3), (8, 4)):
            text = fc.raid_report("RAID 10", str(disks), "1000")
            joined = " ".join(part.strip() for part in text.split("\n"))
            self.assertIn("Ausfalltoleranz : 1 Festplatte sicher (bis zu %d, wenn je "
                          "Spiegelpaar nur eine ausfällt)" % upto,
                          re.sub(r" +:", " :", joined))

    def test_z12_ungerade(self):
        for disks in (3, 5, 7, 9):
            text = fc.raid_report("RAID 10", str(disks), "1000")
            self.assertTrue(text.startswith("Ungültige Konfiguration für RAID 10."), text)
            self.assertNotIn("bis zu", text)
            self.assertIsNone(fc.raid_values("RAID 10", disks, 1000))

    def test_z12_andere_level_ohne_zusatz(self):
        for level in ("RAID 0", "RAID 1", "RAID 5", "RAID 6"):
            self.assertNotIn("bis zu", fc.raid_report(level, "6", "1000"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
