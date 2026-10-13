#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests ab 0.63.2 (Plan 0.63.2, Teil S3 Kern- und Rechner-Logik):

  A8       /32 zeigt keine Broadcast-Adresse; ipv4_values unveraendert
  A10      _int_matcher: "2²" ist falsch statt einer Ausnahme, nur Ziffern 0-9
  B-N-06   Teilungsweg im Trainer "Zahlen" vollstaendig (kein "...")
  B-D-04   Obergrenzen RAID und Bildschirm (= Restrisiko 17)
  B-D-03   keine unendlichen Werte, groesste erlaubte Werte endlich
  B-D-15   Hinweiszeile "Punkt als Tausender gelesen." (mit Restrisiko 13 USV)
           und PC-Kaesten hoch genug (F-S3-2 a)
  RR12     "01.000" ist keine Zahl (auch im Subnetting, F-S3-4 a)
  RR16     Farbtiefe 1 bis 64 Bit
  B-K-N3   Bildrate mit Nachkommastellen ("29,97"), Rundung ohne
           Gleitkommafehler (Auflage 4.4 Z1: 49,95 / 49,99 / 50,0 / 0,05 / 0,0)
  B-I-N1   400 Ziffern in jedem Zahlfeld: Meldung, keine andere Ausnahme
  B-P-01   Projekt liest Zahlen nach der Leseregel der Rechner (mit Z5:
           Seitenziel "inf"/"nan" stuerzt nicht mehr ab)

Der Code-Ordner ist waehlbar (Rot-Probe gegen einen alten Stand):

    RECHNER_CODE=<ordner mit dem Code> python test_rechner_0632.py

Start:  python test_rechner_0632.py
"""

import ipaddress
import os
import random
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("RECHNER_CODE") or HERE)
sys.path.insert(0, CODE)

import fisi_core as fc            # noqa: E402
import fisi_lernen as fl          # noqa: E402
import fisi_projekt as fp         # noqa: E402

NEUNEN = "9" * 400
GRENZE = 28                       # Handy-Zeile (Freigabe 0.62.3, F-P2)
HINWEIS = "Punkt als Tausender gelesen."


def zeile(bericht, anfang):
    for line in bericht.splitlines():
        if line.startswith(anfang):
            return line.split(":", 1)[1].strip()
    return None


class Meldung(unittest.TestCase):
    def assertMeldung(self, aufruf, text=None):
        with self.assertRaises(fc.InputError) as caught:
            aufruf()
        if text is not None:
            self.assertEqual(str(caught.exception), text)
        return str(caught.exception)


class A8Test(unittest.TestCase):
    def test_a8_32_ohne_broadcast(self):
        for adresse in ("10.0.0.7/32", "192.168.10.7/32"):
            self.assertEqual(zeile(fc.subnet_report(adresse), "Broadcast-Adresse"),
                             "keine (/32, einzelne Adresse)")
            # erste/letzte Host-Adresse und Hosts bleiben
            bericht = fc.subnet_report(adresse)
            self.assertEqual(zeile(bericht, "Nutzbare Hosts"), "1")
            self.assertEqual(zeile(bericht, "Erste Host-Adresse"), adresse[:-3])
        self.assertEqual(zeile(fc.subnet_report("192.168.10.1/31"), "Broadcast-Adresse"),
                         "keine (/31, RFC 3021)")
        self.assertEqual(zeile(fc.subnet_report("192.168.10.1/30"), "Broadcast-Adresse"),
                         "192.168.10.3")
        self.assertEqual(zeile(fc.subnet_report("192.168.10.1/24"), "Broadcast-Adresse"),
                         "192.168.10.255")

    def test_a8_ipv4_values_unveraendert(self):
        # eigener Nachbau des Stands 0.63.1 (Spiel nutzt ipv4_values)
        for prefix in range(33):
            net = ipaddress.ip_network("172.20.200.17/%d" % prefix, strict=False)
            if prefix < 31:
                first, last = net.network_address + 1, net.broadcast_address - 1
                hosts = net.num_addresses - 2
            else:
                liste = list(net.hosts())
                first = liste[0] if liste else net.network_address
                last = liste[-1] if liste else net.broadcast_address
                hosts = 2 if prefix == 31 else 1
            soll = {"netz": net.network_address, "maske": net.netmask,
                    "wildcard": net.hostmask, "broadcast": net.broadcast_address,
                    "erste": first, "letzte": last, "hosts": hosts,
                    "adressen": net.num_addresses, "praefix": prefix}
            self.assertEqual(fc.ipv4_values(net), soll, prefix)


class A10Test(unittest.TestCase):
    def test_a10_hochzahl_kein_fehler(self):
        match = fl._int_matcher(22)
        for text in ("22", " 2 2 ", "2.2"):
            self.assertIs(match(text), True, text)
        for text in ("2²", "²", "٢٢", "２２", "", "-22", "21"):
            self.assertIs(match(text), False, text)       # keine Ausnahme

    def test_a10_ueber_die_aufgaben(self):
        for kind, feld in (("zahlen", "dez"), ("ipv4", "hosts")):
            gefunden = 0
            for seed in range(80):
                task = fl.trainer_task(kind, 1, "a10-%d" % seed)
                if feld not in task.solution:
                    continue
                gefunden += 1
                self.assertEqual(task.check({feld: "2²"})[feld], False)
                self.assertEqual(task.check({feld: task.solution[feld]})[feld], True)
            self.assertGreater(gefunden, 0, kind)


class BN06Test(unittest.TestCase):
    def test_bn06_alle_teilungszeilen(self):
        mit_mehr_als_12 = 0
        for level in (1, 2, 3):
            for seed in range(40):
                task = fl.trainer_task("zahlen", level, "e3-%d" % seed)
                if "dez" in task.solution:
                    continue                                 # nicht Dezimal gegeben
                wert = int(task.solution["bin"], 2)
                self.assertNotIn("   ...", task.steps)
                reihe = [s for s in task.steps if re.fullmatch(r"   \d+ : 2 = \d+ Rest [01]", s)]
                self.assertEqual(len(reihe), wert.bit_length(), (level, seed))
                self.assertTrue(all(len(s) <= GRENZE for s in reihe), reihe)
                reste = "".join(s[-1] for s in reihe)[::-1]
                self.assertEqual(int(reste, 2), wert)
                self.assertEqual(reihe[-1], "   1 : 2 = 0 Rest 1")
                mit_mehr_als_12 += len(reihe) > 12
        self.assertEqual(mit_mehr_als_12, 12)        # Plan: 12 von 120 Aufgaben


class BD04GrenzenTest(Meldung):
    def test_bd04_grenzen_je_feld(self):
        self.assertIn("1000 x 1.000.000 GB",
                      fc.raid_report("RAID 5", "1000", "1000000"))
        self.assertMeldung(lambda: fc.raid_report("RAID 5", "1001", "1000"),
                           "Die Anzahl der Festplatten ist zu groß (höchstens 1.000).")
        self.assertMeldung(lambda: fc.raid_report("RAID 5", "4", "1000001"),
                           "Die Kapazität je Festplatte ist zu groß "
                           "(höchstens 1.000.000 GB).")
        self.assertMeldung(lambda: fc.raid_report("RAID 5", "4", "1.000.000,01"),
                           "Die Kapazität je Festplatte ist zu groß "
                           "(höchstens 1.000.000 GB).")
        self.assertIn("4 x 0,01 GB", fc.raid_report("RAID 5", "4", "0,01"))
        self.assertMeldung(lambda: fc.raid_report("RAID 5", "4", "0,001"),
                           "Die Kapazität je Festplatte ist zu klein "
                           "(mindestens 0,01 GB).")
        self.assertMeldung(lambda: fc.raid_report("RAID 5", "4", "0,009"),
                           "Die Kapazität je Festplatte ist zu klein "
                           "(mindestens 0,01 GB).")
        self.assertIn("100000 x 100000 Pixel",
                      fc.screen_report("100000", "100000", "24", ""))
        self.assertMeldung(lambda: fc.screen_report("100001", "1080", "24", ""),
                           "Die Breite ist zu groß (höchstens 100.000 Pixel).")
        self.assertMeldung(lambda: fc.screen_report("1920", "100001", "24", ""),
                           "Die Höhe ist zu groß (höchstens 100.000 Pixel).")

    def test_rr17_zwanzig_ziffern(self):
        zwanzig = "9" * 20
        self.assertMeldung(lambda: fc.raid_report("RAID 5", zwanzig, "1000"),
                           "Die Anzahl der Festplatten ist zu groß (höchstens 1.000).")
        self.assertMeldung(lambda: fc.raid_report("RAID 5", "4", zwanzig),
                           "Die Kapazität je Festplatte ist zu groß "
                           "(höchstens 1.000.000 GB).")
        self.assertMeldung(lambda: fc.screen_report(zwanzig, "1080", "24", "30"),
                           "Die Breite ist zu groß (höchstens 100.000 Pixel).")
        self.assertMeldung(lambda: fc.screen_report("1920", zwanzig, "24", "30"),
                           "Die Höhe ist zu groß (höchstens 100.000 Pixel).")

    def test_bd04_reihenfolge_und_bestand(self):
        # erst "groesser als 0" wie bisher, die Bildrate-Meldungen unveraendert
        self.assertMeldung(lambda: fc.raid_report("RAID 5", "0", "1000"),
                           "Anzahl und Kapazität müssen größer als 0 sein.")
        self.assertMeldung(lambda: fc.raid_report("RAID 5", "4", "0"),
                           "Anzahl und Kapazität müssen größer als 0 sein.")
        self.assertMeldung(lambda: fc.screen_report("0", "1080", "24", ""),
                           "Breite und Höhe müssen größer als 0 sein.")
        self.assertMeldung(lambda: fc.screen_report("1920", "1080", "24", "1001"))
        self.assertTrue(fc.raid_report("RAID 10", "1000", "1").startswith("RAID-Level"))


class BD03Test(Meldung):
    def test_bd03_keine_unendlichen_werte(self):
        for wert in ("inf", "-inf", "nan", "1e309", "Infinity"):
            for feld, aufruf in (
                    ("Anzahl Festplatten", lambda: fc.raid_report("RAID 5", wert, "1000")),
                    ("Kapazität je Festplatte (GB)",
                     lambda: fc.raid_report("RAID 5", "4", wert)),
                    ("Breite (Pixel)", lambda: fc.screen_report(wert, "1080", "24", "30")),
                    ("Höhe (Pixel)", lambda: fc.screen_report("1920", wert, "24", "30")),
                    ("Bildrate (fps)", lambda: fc.screen_report("1920", "1080", "24", wert))):
                with self.subTest(wert=wert, feld=feld):
                    self.assertIn(feld, self.assertMeldung(aufruf))

    def test_bd03_groesste_werte_endlich(self):
        for level in fc.RAID_LEVELS:
            text = fc.raid_report(level, "1000", "1000000")
            self.assertNotRegex(text, r"inf|nan|e\+")
        text = fc.screen_report("100000", "100000", "64", "1000")
        self.assertNotRegex(text, r"inf|nan|e\+")
        self.assertEqual(zeile(text, "Bildrate (fps)"), "1.000 Bilder/Sekunde")


class BD15HinweisTest(unittest.TestCase):
    def test_bd15_hinweiszeile(self):
        mit = [fc.raid_report("RAID 5", "1.000", "1000"),
               fc.raid_report("RAID 5", "4", "1.000"),
               fc.raid_report("RAID 5", "4", "1.000,5"),
               fc.raid_report("RAID 10", "4", "2.000"),
               fc.screen_report("1.920", "1080", "24", "30"),
               fc.screen_report("1920", "1.080", "24", ""),
               fc.screen_report("1920", "1080", "24", "1.000")]
        for text in mit:
            self.assertEqual(text.split("\n")[-1], HINWEIS, text)
            self.assertEqual(text.count(HINWEIS), 1)
        ohne = [fc.raid_report("RAID 5", "1000", "1000"),
                fc.raid_report("RAID 5", "4", "1,5"),
                fc.raid_report("RAID 5", "4", "0.125"),
                fc.raid_report("RAID 5", "4", "1 000"),
                fc.raid_report("RAID 5", "4", "7,2"),
                fc.screen_report("1920", "1080", "24", "29,97"),
                fc.screen_report("1920", "1080", "24", "23.976".replace(".", ",")),
                fc.screen_report("1920", "1080", "24", "")]
        for text in ohne:
            self.assertNotIn(HINWEIS, text)
        self.assertLessEqual(len(HINWEIS), GRENZE)

    def test_rr13_usv(self):
        felder = dict(fc.UPS_FIELD_DEFAULTS)
        for mode, _name in fc.UPS_MODES:
            text = fc.ups_calculate(mode, felder)["text"]
            self.assertNotIn(HINWEIS, text, mode)
        laufzeit = dict(felder, block_ah="7.200")
        text = fc.ups_calculate("laufzeit", laufzeit)["text"]
        self.assertIn("7.200 Ah", text)
        tabelle, gefunden, rest = text.partition("\n\n" + fc.UPS_SIMPLE_TEXT)
        self.assertTrue(gefunden)
        self.assertEqual(rest, "")                   # Handy trennt so (main.py)
        self.assertEqual(tabelle.split("\n")[-1], HINWEIS)
        # Berechnung A liest block_ah nicht: kein Hinweis
        self.assertNotIn(HINWEIS, fc.ups_calculate("akku", laufzeit)["text"])
        for key in ("last", "minuten"):
            text = fc.ups_calculate("akku", dict(felder, **{key: "1.000"}))["text"]
            self.assertIn(HINWEIS, text, key)
        text = fc.ups_calculate("empfehlung", dict(felder, nenn_va="1.500"))["text"]
        self.assertIn(HINWEIS, text)
        text = fc.ups_calculate("empfehlung", dict(felder, last="1,5"))["text"]
        self.assertNotIn(HINWEIS, text)
        # Nacharbeit (Gegenpruefung L1): "empfehlung" liest auch nenn_w und
        # block_ah (parallel hat hoechstens 20, kein Tausenderpunkt moeglich)
        for key, wert in (("nenn_w", "1.000"), ("block_ah", "7.200")):
            text = fc.ups_calculate("empfehlung", dict(felder, **{key: wert}))["text"]
            self.assertIn(HINWEIS, text, key)


class RR12Test(Meldung):
    def test_rr12_fuehrende_null(self):
        for wert in ("01.000", "00.500", "012.345", "01.000.000"):
            with self.subTest(wert=wert):
                self.assertMeldung(
                    lambda: fc.raid_report("RAID 5", "4", wert),
                    "Bitte eine Zahl eingeben: Kapazität je Festplatte (GB). "
                    "Zum Beispiel 1.000 oder 1,5.")
        for wert, soll in (("0.125", 0.125), ("01.5", 1.5), ("0,5", 0.5), ("-0", 0.0),
                           ("1.000", 1000.0), ("0.5", 0.5)):
            self.assertEqual(fc.read_number(wert, "x"), soll, wert)


class RR16Test(Meldung):
    def test_rr16_farbtiefe(self):
        for tiefe in ("-5", "0", "-8", "65", "100"):
            self.assertMeldung(lambda: fc.screen_report("1920", "1080", tiefe, "30"),
                               "Bitte eine Farbtiefe von 1 bis 64 Bit wählen.")
        # Nacharbeit (Gegenpruefung L2): erst Lesefehler, dann Farbtiefe
        for tiefe in ("0", "65"):
            self.assertMeldung(lambda: fc.screen_report("1920", "1080", tiefe, "abc"),
                               "Bitte eine Zahl eingeben: Bildrate (fps). "
                               "Zum Beispiel 1.000 oder 1,5.")
            self.assertMeldung(lambda: fc.screen_report("abc", "1080", tiefe, "30"),
                               "Bitte eine Zahl eingeben: Breite (Pixel). "
                               "Zum Beispiel 1.000.")
        for tiefe in (1, 8, 16, 24, 32, 64):
            text = fc.screen_report("1920", "1080", str(tiefe), "30")
            self.assertEqual(zeile(text, "Farbtiefe"), "%d Bit/Pixel" % tiefe)


class BKN3Test(unittest.TestCase):
    def test_bkn3_bildrate_mit_komma(self):
        for eingabe, soll in (("29,97", "29,97"), ("23,976", "23,976"), ("12,5", "12,5"),
                              ("0,5", "0,5"), ("30", "30"), ("1.000", "1.000"),
                              # Auflage 4.4 Z1: Rundung ohne Gleitkommafehler
                              ("49,95", "49,95"), ("49,99", "49,99"), ("50,0", "50"),
                              ("0,05", "0,05"), ("0,001", "0,001"), ("59,94", "59,94")):
            text = fc.screen_report("1920", "1080", "24", eingabe)
            self.assertEqual(zeile(text, "Bildrate (fps)"), soll + " Bilder/Sekunde", eingabe)
        # 0,0 bedeutet wie bisher "ohne Bildrate"
        self.assertNotIn("Bildrate", fc.screen_report("1920", "1080", "24", "0,0"))

    def test_bkn3_datenrate_unveraendert(self):
        text = fc.screen_report("1920", "1080", "24", "29,97")
        self.assertEqual(zeile(text, "Datenrate"), "177,80 MiB/s")


class BIN1Test(unittest.TestCase):
    def test_bin1_400_ziffern(self):
        aufrufe = [lambda: fc.raid_report("RAID 5", NEUNEN, "1000"),
                   lambda: fc.raid_report("RAID 5", "4", NEUNEN),
                   lambda: fc.screen_report(NEUNEN, "1080", "24", "30"),
                   lambda: fc.screen_report("1920", NEUNEN, "24", "30"),
                   lambda: fc.screen_report("1920", "1080", "24", NEUNEN)]
        felder = dict(fc.UPS_FIELD_DEFAULTS, nenn_w="1000")
        self.assertEqual(len(felder), 11)
        for key in felder:
            aufrufe.append(lambda key=key: fc.ups_calculate(
                "empfehlung", dict(felder, **{key: NEUNEN})))
        for nummer, aufruf in enumerate(aufrufe):
            with self.subTest(nummer=nummer):
                with self.assertRaises(fc.InputError):
                    aufruf()

    def test_bin1_z5_projekt_seitenziel(self):
        for wert in ("inf", "nan", "-inf", NEUNEN, "1e309"):
            seiten, ziel = fp.page_estimate({fp.PAGES_FIELD: wert})
            self.assertEqual(ziel, fp.DEFAULT_PAGES, wert)
        self.assertEqual(fp.to_number(NEUNEN, 7), 7)


class BP01Test(unittest.TestCase):
    def test_bp01_projekt_leseregel(self):
        for text, soll in (("1.000", 1000.0), ("1.000.000", 1000000.0),
                           ("1.234,50", 1234.5), ("25 €", 25.0), ("25,5", 25.5),
                           ("1 000", 1000.0), ("0.5", 0.5), ("-5", -5.0)):
            self.assertEqual(fp.to_number(text, 7), soll, text)
        for text in ("abc", "inf", "nan", "1e3", "12,3456", "", None, "01.000"):
            self.assertEqual(fp.to_number(text, 7), 7, text)

    def test_bp01_sachkosten(self):
        felder = {"material_name_0": "Switch", "material_betrag_0": "1.000"}
        self.assertIn("Sachkosten: 1.000,00 €", fp.cost_lines(felder))
        felder["material_betrag_0"] = "inf"
        self.assertIn("Sachkosten: 0,00 €", fp.cost_lines(felder))


class PcKaestenHinweisTest(unittest.TestCase):
    """F-S3-2 (a): die Hinweiszeile passt ohne Scrollen in die PC-Kaesten
    (sichtbar sind height - 1 Zeilen, wie test_rechenweg.PcKaestenTest)."""

    def _hoehe(self, name):
        with open(os.path.join(CODE, "app_gui.py"), encoding="utf-8") as handle:
            source = handle.read()
        return int(re.search(r"self\.txt_%s = make_text\([^)]*height=(\d+)" % name,
                             source).group(1))

    def test_raid_10_mit_hinweis(self):
        text = fc.raid_report("RAID 10", "1.000", "1.000")
        self.assertEqual(text.split("\n")[-1], HINWEIS)
        self.assertEqual(text.count("\n") + 1, 10)
        self.assertGreaterEqual(self._hoehe("raid") - 1, 10)

    def test_bildschirm_mit_bildrate_und_hinweis(self):
        text = fc.screen_report("1.920", "1.080", "24", "29,97")
        self.assertEqual(text.split("\n")[-1], HINWEIS)
        self.assertEqual(text.count("\n") + 1, 13)
        self.assertGreaterEqual(self._hoehe("screen") - 1, 13)


if __name__ == "__main__":
    unittest.main(verbosity=2)
