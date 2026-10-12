#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests ab 0.62.4 (Plan 0.62.4, Abschnitt 3.5, Gruppe 5): gemeinsame Leseregel
der Rechner RAID, Bildschirm und USV (B-D-15, Entscheidung F-7 A) und
Tausenderpunkt im RAID-Rechenweg am PC und am Handy (B-N-03).

  LeseregelTest   T1-T18 aus plan/belege/eingaben_rechner.md, soweit sie zu
                  0.62.4 gehoeren (Regeln 1 bis 4 und 7). Nicht hier, weil
                  0.62.5: T5 nur "1001" (Obergrenze), T10 (29,97 Bilder/Sekunde),
                  T17 nur UpsPicture._bar (USV-Bild bei inf). T11 (Farbtiefe
                  direkt aufgerufen) gehoert zu keiner der Regeln 1-4, 7.
                  Rot auf v0.62.3.
  RechenwegTest   B-N-03: alle Zahlen ab 1000 im RAID-Rechenweg mit Punkt,
                  die drei Handy-Zeilen neu umbrochen. Rot auf v0.62.3.
  SchutzTest      Subnetting, Handy-Zeilen <= 28 Zeichen, "0.125" bleibt
                  0,125, die heute gebrauchten Eingaben lesen sich wie heute.
                  Schutz-Tests: auf v0.62.3 schon gruen.

Der Code-Ordner ist waehlbar (fuer die Rot-Probe gegen einen alten Stand):

    TAUSENDER_CODE=<ordner mit dem Code> python test_tausenderpunkt.py

Start:  python test_tausenderpunkt.py
"""

import math
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("TAUSENDER_CODE") or HERE)
sys.path.insert(0, CODE)

import fisi_core as fc            # noqa: E402

NEUNEN = "9" * 400
GRENZE = 28    # Freigabe 0.62.3 (F-P2), wie test_rechenweg.py


def zeile(bericht, anfang):
    for line in bericht.splitlines():
        if line.startswith(anfang):
            return line.split(":", 1)[1].strip()
    return None


class LeseregelTest(unittest.TestCase):
    """Rot auf v0.62.3, gruen ab 0.62.4."""

    def assertMeldung(self, aufruf, *teile):
        with self.assertRaises(fc.InputError) as caught:
            aufruf()
        for teil in teile:
            self.assertIn(teil, str(caught.exception))
        return str(caught.exception)

    def test_t01_raid_kapazitaet_1000(self):
        bericht = fc.raid_report("RAID 5", "4", "1.000")
        self.assertEqual(zeile(bericht, "Festplatten"), "4 x 1.000 GB")
        self.assertEqual(zeile(bericht, "Bruttokapazität"), "4.000,00 GB")

    def test_t02_raid_kapazitaet_12500(self):
        bericht = fc.raid_report("RAID 5", "4", "12.500")
        self.assertEqual(zeile(bericht, "Festplatten"), "4 x 12.500 GB")
        self.assertEqual(zeile(bericht, "Bruttokapazität"), "50.000,00 GB")

    def test_t03_raid_anzahl_1000(self):
        bericht = fc.raid_report("RAID 5", "1.000", "1000")
        self.assertEqual(zeile(bericht, "Festplatten"), "1000 x 1.000 GB")
        self.assertEqual(zeile(bericht, "Bruttokapazität"), "1.000.000,00 GB")

    def test_t04_raid_kapazitaet_abgelehnt(self):
        for wert in ("inf", "nan", "1e309", "1e300", "1e-300", "1e3", "1_000",
                     "١٠٠٠", NEUNEN):
            with self.subTest(wert=wert[:12]):
                self.assertMeldung(lambda: fc.raid_report("RAID 5", "4", wert),
                                   "Bitte eine Zahl eingeben",
                                   "Kapazität je Festplatte (GB)")

    def test_t05_raid_anzahl_abgelehnt(self):
        # "1001" (Obergrenze 1.000) gehoert zu 0.62.5
        for wert in ("1_000", "١٠٠٠"):
            with self.subTest(wert=wert):
                self.assertMeldung(lambda: fc.raid_report("RAID 5", wert, "1000"),
                                   "Bitte eine Zahl eingeben", "Anzahl Festplatten")

    def test_t06_400_ziffern_meldung_statt_overflow(self):
        aufrufe = [("Anzahl Festplatten", lambda: fc.raid_report("RAID 5", NEUNEN, "1000")),
                   ("Breite (Pixel)", lambda: fc.screen_report(NEUNEN, "1080", "24", "30")),
                   ("Höhe (Pixel)", lambda: fc.screen_report("1920", NEUNEN, "24", "30"))]
        for feld, aufruf in aufrufe:
            with self.subTest(feld=feld):
                self.assertMeldung(aufruf, "Bitte eine Zahl eingeben", feld)

    def test_t07_bildschirm_mit_tausenderpunkt(self):
        bericht = fc.screen_report("1.920", "1.080", "24", "30")
        self.assertEqual(zeile(bericht, "Auflösung"), "1920 x 1080 Pixel")
        self.assertEqual(bericht, fc.screen_report("1920", "1080", "24", "30"))

    def test_t08_bildrate_abgelehnt(self):
        for wert in ("inf", "nan", "1e309", "1e300", "1e-300"):
            with self.subTest(wert=wert):
                self.assertMeldung(lambda: fc.screen_report("1920", "1080", "24", wert),
                                   "Bitte eine Zahl eingeben", "Bildrate (fps)")

    def test_t09_bildrate_1000(self):
        bericht = fc.screen_report("1920", "1080", "24", "1.000")
        self.assertEqual(zeile(bericht, "Bildrate (fps)"), "1000 Bilder/Sekunde")
        self.assertEqual(zeile(bericht, "Datenrate"), "5.932,62 MiB/s")

    def test_t12_usv_last_1000(self):
        self.assertEqual(fc.ups_number({"last": "1.000"}, "last"), 1000.0)

    def test_t13_usv_last_1000000(self):
        self.assertEqual(fc.ups_number({"last": "1.000.000"}, "last"), 1000000.0)

    def test_t14_usv_wirkungsgrad_12500_bereich(self):
        self.assertMeldung(lambda: fc.ups_number({"eta": "12.500"}, "eta"),
                           "zwischen 10 und 100")

    def test_t15_usv_abgelehnt(self):
        for key in ("last", "minuten", "block_v", "block_ah", "nenn_va"):
            for wert in ("1e-300", "1e3", "1_000", "١٠٠٠"):
                with self.subTest(key=key, wert=wert):
                    self.assertMeldung(lambda: fc.ups_number({key: wert}, key),
                                       "Bitte eine Zahl eingeben",
                                       fc.UPS_FIELD_CAPTIONS[key])

    def test_t16_usv_minus_null(self):
        wert = fc.ups_number({"alterung": "-0"}, "alterung")
        self.assertEqual(wert, 0.0)
        self.assertEqual(math.copysign(1.0, wert), 1.0, "Vorzeichen von -0 bleibt")
        text = fc.ups_calculate("akku", dict(fc.UPS_FIELD_DEFAULTS, alterung="-0"))["text"]
        self.assertNotIn("+-0", text)

    def test_t17_usv_winzige_last_meldung(self):
        felder = dict(fc.UPS_FIELD_DEFAULTS, last="1e-300", block_ah="10000", parallel="20")
        self.assertMeldung(lambda: fc.ups_calculate("laufzeit", felder),
                           "Bitte eine Zahl eingeben", "Last")

    def test_t18_englische_mischform_abgelehnt(self):
        self.assertMeldung(lambda: fc.ups_number({"last": "1,000.5"}, "last"),
                           "Bitte eine Zahl eingeben")
        self.assertMeldung(lambda: fc.raid_report("RAID 5", "4", "1,000.5"),
                           "Bitte eine Zahl eingeben")
        self.assertMeldung(lambda: fc.screen_report("1920", "1080", "24", "1.00,5"),
                           "Bitte eine Zahl eingeben")

    def test_regel7_dezimal_im_ganzzahlfeld(self):
        for feld, aufruf in (
                ("Anzahl Festplatten", lambda: fc.raid_report("RAID 5", "1.5", "1000")),
                ("Breite (Pixel)", lambda: fc.screen_report("1.5", "1080", "24", "30")),
                ("Höhe (Pixel)", lambda: fc.screen_report("1920", "1,5", "24", "30"))):
            with self.subTest(feld=feld):
                self.assertMeldung(aufruf, "Bitte eine ganze Zahl eingeben", feld)

    def test_regel4_meldung_mit_beispiel(self):
        text = self.assertMeldung(lambda: fc.raid_report("RAID 5", "4", "abc"))
        self.assertEqual(text, "Bitte eine Zahl eingeben: Kapazität je Festplatte (GB). "
                               "Zum Beispiel 1.000 oder 1,5.")
        text = self.assertMeldung(lambda: fc.ups_number({"last": "1.5000"}, "last"))
        self.assertEqual(text, "Bitte eine Zahl eingeben: Last. Zum Beispiel 1.000 oder 1,5.")


class RechenwegTest(unittest.TestCase):
    """B-N-03, rot auf v0.62.3: dort je 14 Zahlen ohne Tausenderpunkt."""

    OHNE = re.compile(r"(?<![\d.,])\d{4,}(?!\d)")
    MIT = re.compile(r"(?<![\d.,])\d{1,3}(?:\.\d{3})+(?!\d)")

    def test_bn03_alle_zahlen_ab_1000_mit_punkt(self):
        for name in ("CALC_EXPLAIN_RAID", "CALC_EXPLAIN_RAID_HANDY"):
            text = getattr(fc, name)
            with self.subTest(name=name):
                self.assertEqual(self.OHNE.findall(text), [])
                self.assertEqual(sorted(set(self.MIT.findall(text))),
                                 ["1.000", "2.000", "3.000", "4.000"])
                self.assertEqual(len(self.MIT.findall(text)), 14)

    def test_bn03_handy_drei_zeilen_neu_umbrochen(self):
        lines = fc.CALC_EXPLAIN_RAID_HANDY.split("\n")
        for formel, ergebnis in ((" (4 - 1) x 1.000 GB", " = 3.000 GB nutzbar"),
                                 (" (4 - 2) x 1.000 GB", " = 2.000 GB nutzbar"),
                                 (" (4 / 2) x 1.000 GB", " = 2.000 GB nutzbar")):
            with self.subTest(formel=formel):
                self.assertIn(formel, lines)
                self.assertEqual(lines[lines.index(formel) + 1], ergebnis)


class BildrateGrenzeTest(unittest.TestCase):
    """Ab 0.62.4 (Gegenpruefung G4/G5, Fund M1): Normbildraten mit Punkt
    ("23.976") liest die Leseregel als 23976. Ueber 1.000 fps kommt deshalb
    eine Meldung statt einer still falschen Datenrate. Rot auf f0efb1d."""

    def test_bildrate_mit_punkt_ueber_1000_meldung(self):
        for wert in ("23.976", "59.940", "119.880", "1.001", "1001"):
            with self.subTest(wert=wert):
                with self.assertRaises(fc.InputError) as fehler:
                    fc.screen_report("1920", "1080", "24", wert)
                self.assertEqual(
                    str(fehler.exception),
                    "Die Bildrate ist zu groß (höchstens 1.000 Bilder pro Sekunde). "
                    "Nachkommastellen bitte mit Komma eingeben, zum Beispiel 23,976.")

    def test_bildrate_bis_1000_wie_bisher(self):
        for wert in ("23,976", "59,94", "1000", "1.000", "0,5", "30"):
            with self.subTest(wert=wert):
                fc.screen_report("1920", "1080", "24", wert)


class SchutzTest(unittest.TestCase):
    """Schutz-Tests: schon auf v0.62.3 gruen, duerfen nicht kippen."""

    def test_schutz_handy_hoechstens_28_zeichen(self):
        for name in dir(fc):
            if name.startswith("CALC_EXPLAIN_") and name.endswith("_HANDY"):
                for number, line in enumerate(getattr(fc, name).split("\n"), 1):
                    self.assertLessEqual(len(line), GRENZE, "%s Zeile %d: %r"
                                         % (name, number, line))

    def test_schutz_0_125_bleibt_dezimal(self):
        self.assertEqual(fc.ups_number({"last": "0.125"}, "last"), 0.125)
        bericht = fc.raid_report("RAID 5", "4", "0.125")
        self.assertEqual(zeile(bericht, "Bruttokapazität"), "0,50 GB")

    def test_schutz_dezimalpunkt_und_komma(self):
        self.assertEqual(fc.ups_number({"last": "1500.5"}, "last"), 1500.5)
        self.assertEqual(fc.ups_number({"last": "1.500,5"}, "last"), 1500.5)
        self.assertEqual(fc.ups_number({"pf": "0.9"}, "pf"), 0.9)
        self.assertIn("ganze Zahl", str(self._fehler(
            lambda: fc.ups_number({"reihe": "1.5"}, "reihe"))))

    def _fehler(self, aufruf):
        with self.assertRaises(fc.InputError) as caught:
            aufruf()
        return caught.exception

    def test_schutz_heute_gebrauchte_eingaben(self):
        """Die 40 Eingaben aus Tests, Vorgaben und Aufgaben (Beleg, Gegenprobe)
        ergeben dieselbe Anzeige wie die eindeutige Python-Schreibweise des
        Werts, den v0.62.3 gelesen hat (USV: ups_number; RAID-Kapazitaet und
        Bildrate: float nach Komma -> Punkt). Was v0.62.3 in RAID und Bildrate
        gar nicht lesen konnte ("1.500,5"), ist dort ausgenommen."""
        for text in HEUTE_GEBRAUCHT:
            raw = text.strip()
            raw = raw.replace(".", "").replace(",", ".") if "." in raw and "," in raw \
                else raw.replace(",", ".")
            kanonisch = repr(float(raw))
            with self.subTest(text=text):
                try:
                    float_alt = repr(float(text.strip().replace(",", ".")))
                except ValueError:
                    float_alt = None
                if float_alt is not None:
                    self.assertEqual(
                        self._lauf(lambda t: fc.raid_report("RAID 5", "4", t), text),
                        self._lauf(lambda t: fc.raid_report("RAID 5", "4", t), float_alt))
                    self.assertEqual(
                        self._lauf(lambda t: fc.screen_report("1920", "1080", "24", t), text),
                        self._lauf(lambda t: fc.screen_report("1920", "1080", "24", t),
                                   float_alt))
                for key in ("last", "pf", "alterung"):
                    self.assertEqual(self._lauf(lambda t: fc.ups_number({key: t}, key), text),
                                     self._lauf(lambda t: fc.ups_number({key: t}, key),
                                                kanonisch))

    @staticmethod
    def _lauf(aufruf, text):
        try:
            return aufruf(text)
        except fc.InputError as fehler:
            return "Meldung: %s" % fehler

    def test_schutz_subnetting(self):
        bericht = fc.subnet_report("192.168.1.50/24")
        self.assertEqual(zeile(bericht, "Netzadresse"), "192.168.1.0")
        self.assertEqual(zeile(bericht, "Nutzbare Hosts"), "254")
        self.assertEqual(zeile(fc.subnet_report("10.20.30.40/8"), "Nutzbare Hosts"),
                         "16.777.214")
        self.assertEqual(zeile(fc.subnet_report("10.0.0.0/255.255.255.0"), "Präfixlänge"),
                         "/24")
        for wert in ("192.168.1.50/1.000", "192.168.1.50/24,5", "192.168.1.50/1e1",
                     "1.000", "192.168.1.50/inf"):
            with self.subTest(wert=wert):
                self.assertIn("Bitte eine gültige Adresse", str(self._fehler(
                    lambda: fc.subnet_report(wert))))


# Beleg plan/belege/eingaben_rechner.md, Abschnitt Gegenprobe (HEUTE_GEBRAUCHT
# des Werkzeugs, doppelte Eintraege entfernt: 40 Eingaben)
HEUTE_GEBRAUCHT = ["1000", "2000", "4000", "1,5", "0,5", "29,97", "30", "25", "60", "0",
                   "1920", "1080", "1280", "720", "3840", "2160", "800", "600",
                   "0,9", "80", "15", "12", "2", "1", "1500", "900",
                   "1.500,5", "1500,5", "1500.5", " 600 ", "0,1", "100", "10",
                   "1440", "0,01", "4", "6", "8", "5", "3"]


if __name__ == "__main__":
    print("Code-Ordner: %s" % CODE)
    unittest.main(verbosity=2)
