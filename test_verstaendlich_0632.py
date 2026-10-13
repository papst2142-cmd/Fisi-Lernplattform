#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests ab 0.63.2 (Plan 0.63.2, S2c, B-N-07): Verstaendlichkeits-Hinweise aus
Teil E in den Rechenwegen, Rechner-Anzeigen und im Trainer. Je Stelle ein
Textnachweis wie im Werkzeug n_teil_e_stand.py (Pruefung 0.62.4 Teil 6),
PC und Handy gleich.

  Ohne neue Zahlen: 5.4, 5.6, 5.8, 4.2, 4.14
  Mit neuen Zahlen (test_rechenweg.py Z19-Z28): 5.1, 5.2, 5.3, 5.5, 5.7,
                    5.13, 4.9, 4.15b
  Trainer (fisi_lernen.py, ausserhalb des T5-Blocks): 5.9, 5.11, 5.12,
                    3.16, 1.19, 4.12, 4.13

Der Code-Ordner ist waehlbar (Rot-Probe gegen einen alten Stand):

    RECHNER_CODE=<ordner mit dem Code> python test_verstaendlich_0632.py

Start:  python test_verstaendlich_0632.py
"""

import ipaddress
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("RECHNER_CODE") or HERE)
sys.path.insert(0, CODE)

import fisi_core as fc            # noqa: E402
import fisi_lernen as fl          # noqa: E402

PAARE = [("SUBNET", fc.CALC_EXPLAIN_SUBNET, fc.CALC_EXPLAIN_SUBNET_HANDY),
         ("SCREEN", fc.CALC_EXPLAIN_SCREEN, fc.CALC_EXPLAIN_SCREEN_HANDY),
         ("UPS", fc.CALC_EXPLAIN_UPS, fc.CALC_EXPLAIN_UPS_HANDY)]


def _quelle(name):
    with open(os.path.join(CODE, name), encoding="utf-8") as handle:
        return handle.read()


def _flach(text):
    """Handy-Fassung: Zeilen zusammenziehen, damit Saetze ueber Umbrueche
    hinweg gefunden werden (PC und Handy gleich pruefbar)."""
    return re.sub(r"\s+", " ", text.replace("-\n ", "-"))


def _abschnitt(text, start, ende):
    return text[text.index(start):text.index(ende)]


class OhneNeueZahlenTest(unittest.TestCase):
    def test_5_4_umgestellt(self):
        for text in (fc.CALC_EXPLAIN_UPS, fc.CALC_EXPLAIN_UPS_HANDY):
            self.assertIn("umgestellt nach S: S (VA) = P (W) / Leistungsfaktor", _flach(text))

    def test_5_6_klammern_und_einheit(self):
        for text in (fc.CALC_EXPLAIN_UPS, fc.CALC_EXPLAIN_UPS_HANDY):
            self.assertIn("(288 Wh x 0,8 / 600 W) x 60 min/h = 23,04 min", _flach(text))
        self.assertIn("Laufzeit = (216 Wh x 0,85 / 300 W) x 60 min/h = 36,72 min",
                      fc.ups_task_solution(2))

    def test_5_8_strang_benannt(self):
        felder = dict(fc.UPS_FIELD_DEFAULTS)
        text = fc.ups_calculate("laufzeit", felder, "W")["text"]
        self.assertIn("Akku-Energie          : 24 V x 12 Ah x 1 Strang = 288,00 Wh", text)
        text = fc.ups_calculate("laufzeit", dict(felder, parallel="2"), "W")["text"]
        self.assertIn("Akku-Energie          : 24 V x 12 Ah x 2 Stränge = 576,00 Wh", text)

    def test_4_14_keine_unbenutzte_konstante(self):
        self.assertFalse(hasattr(fc, "UPS_UNIT_CAPTION"))

    def test_4_2_gemeinsame_beschriftungen(self):
        namen = {"RAID_TITLE": "RAID-Kapazität",
                 "RAID_SUBTITLE": "Nutzkapazität, Verlust, Effizienz",
                 "RAID_FIELD_LEVEL": "RAID-Level",
                 "RAID_FIELD_DISKS": "Anzahl Festplatten",
                 "RAID_FIELD_SIZE": "Kapazität je Festplatte (GB)",
                 "SCREEN_TITLE": "Bildschirm-Datenvolumen",
                 "SCREEN_SUBTITLE": "Pixel, Farbtiefe, Datenrate",
                 "SCREEN_FIELD_WIDTH": "Breite (Pixel)",
                 "SCREEN_FIELD_HEIGHT": "Höhe (Pixel)",
                 "SCREEN_FIELD_FPS": "Bildrate (fps, optional)",
                 "SCREEN_FIELD_DEPTH": "Farbtiefe"}
        pc, handy, kern = (_quelle("app_gui.py"), _quelle(os.path.join("mobile", "src", "main.py")),
                           _quelle("fisi_core.py"))
        for name, wortlaut in namen.items():
            self.assertEqual(getattr(fc, name, None), wortlaut, name)   # Wortlaut gleich
            self.assertEqual(kern.count('"%s"' % wortlaut), 1, wortlaut)  # eine Quelle
            self.assertNotIn('"%s"' % wortlaut, pc, wortlaut)
            self.assertNotIn('"%s"' % wortlaut, handy, wortlaut)
            self.assertRegex(pc, r"\b%s\b" % name)
            self.assertIn("fc.%s" % name, handy)
        # die Meldungen der Rechner nennen dieselbe Beschriftung
        with self.assertRaises(fc.InputError) as fehler:
            fc.raid_report("RAID 5", "x", "1000")
        self.assertIn(fc.RAID_FIELD_DISKS, str(fehler.exception))


class MitNeuenZahlenTest(unittest.TestCase):
    def test_5_1_grenze_im_oktett(self):
        for text in (fc.CALC_EXPLAIN_SUBNET, fc.CALC_EXPLAIN_SUBNET_HANDY):
            vor4 = text.split("SCHRITT 4")[0]
            self.assertRegex(vor4, r"/2[5-9]|/3[0-2]")
            flach = _flach(vor4)
            self.assertIn("Beispiel 192.168.1.50/28, im 4. Oktett:", flach)
            self.assertIn("Adresse (50): 00110010 Maske (240): 11110000 "
                          "UND-Ergebnis: 00110000 = 48", flach)
            self.assertIn("-> Netzadresse bei /28: 192.168.1.48", flach)

    def test_5_2_oder_mit_bitreihen(self):
        for text in (fc.CALC_EXPLAIN_SUBNET, fc.CALC_EXPLAIN_SUBNET_HANDY):
            schritt3 = _abschnitt(text, "SCHRITT 3", "SCHRITT 4")
            self.assertEqual(re.findall(r"[01]{8}", schritt3),
                             ["00000000", "11111111", "11111111"])
            self.assertIn("ODER-Ergebnis: 11111111 = 255", _flach(schritt3))

    def test_5_3_ausnahmen_31_32(self):
        for text in (fc.CALC_EXPLAIN_SUBNET, fc.CALC_EXPLAIN_SUBNET_HANDY):
            flach = _flach(text)
            self.assertIn("Ausnahmen: Bei /31 sind beide Adressen nutzbar (nur für "
                          "Punkt-zu-Punkt-Verbindungen, RFC 3021).", flach)
            self.assertIn("/32 ist eine einzelne Adresse, ohne Netz- und "
                          "Broadcast-Adresse.", flach)

    def test_5_5_achtzig_prozent_benannt(self):
        for text in (fc.CALC_EXPLAIN_UPS, fc.CALC_EXPLAIN_UPS_HANDY):
            flach = _flach(text)
            self.assertIn("150 Wh / 0,8 (Wirkungsgrad) = 187,5 Wh", flach)
            self.assertIn("Laufzeit = (Akku-Energie x Wirkungsgrad / Last) x 60 min/h", flach)
            self.assertIn("am Lebensende (80 % Restkapazität, siehe Schritt 4):", flach)
            self.assertIn("Achtung: 80 % bzw. 0,8 steht hier für drei verschiedene Werte: "
                          "Wirkungsgrad (Schritt 3), Restkapazität am Lebensende "
                          "(Schritt 4) und höchste Auslastung (Empfehlung).", flach)

    def test_5_7_beispielkopf(self):
        for text in (fc.CALC_EXPLAIN_UPS, fc.CALC_EXPLAIN_UPS_HANDY):
            kopf = _flach(text.split("\n\n")[0])
            self.assertIn("Leistungsfaktor 0,9", kopf)
            self.assertIn("mit je 12 Ah", kopf)
            self.assertIn("USV 1.500 VA / 900 W", kopf)

    def test_5_13_binaerpraefix(self):
        for text in (fc.CALC_EXPLAIN_SCREEN, fc.CALC_EXPLAIN_SCREEN_HANDY):
            schritt3 = _flach(_abschnitt(text, "SCHRITT 3", "SCHRITT 4"))
            self.assertIn("1024 = 2^10, deshalb heißen die Einheiten KiB und MiB "
                          "(Binärpräfixe).", schritt3)
            self.assertIn("1 kB = 1000 Byte", schritt3)

    def test_4_9_stellenzahl_wie_anzeige(self):
        anzeige = fc.ups_calculate("empfehlung", dict(fc.UPS_FIELD_DEFAULTS), "W")["text"]
        for text in (fc.CALC_EXPLAIN_UPS, fc.CALC_EXPLAIN_UPS_HANDY):
            flach = _flach(text)
            for wert in ("23,0 min", "18,4 min", "44,4 %", "66,7 %"):
                self.assertIn(wert, flach)
                self.assertIn(wert, anzeige)
            self.assertIn("600 W / 0,9 = 666,67 VA, gerundet 667 VA", flach)
            self.assertIn("666,67 / 1.500 = 44,4 %, 600 / 900 = 66,7 %", flach)
            self.assertNotIn(" 44 %", flach)
            self.assertNotIn(" 67 %", flach)

    def test_4_15b_zweierpotenz(self):
        for netz in ("2001:db8::1/64", "2001:db8:abcd:12::/48", "fe80::1/10",
                     "2001:db8::1/127", "2001:db8::1/128"):
            n = ipaddress.ip_network(netz, strict=False)
            self.assertIn("Adressen gesamt       : 2^%d = %s"
                          % (128 - n.prefixlen, fc.de_int(n.num_addresses)),
                          fc.subnet_report(netz))
        # IPv4 bleibt ohne Zweierpotenz
        self.assertIn("Adressen gesamt       : 256", fc.subnet_report("192.168.1.50/24"))


class TrainerTest(unittest.TestCase):
    def _aufgaben(self, art, anzahl=40):
        for level in (1, 2, 3):
            for seed in range(anzahl):
                yield fl.trainer_task(art, level, "bn07-%d" % seed)

    def test_5_9_hex_richtung_und_buchstaben(self):
        gesehen = {"hex": 0, "andere": 0, "buchstaben": 0}
        for task in self._aufgaben("zahlen"):
            steps = "\n".join(task.steps)
            if task.text.startswith("Rechne Hexadezimal "):
                gesehen["hex"] += 1
                self.assertNotIn("Binär -> Hex", steps)
                self.assertIn("Hex -> Binär: jede Hex-Ziffer als Vierergruppe (Nibble) "
                              "schreiben: ", steps)
                ziffern = task.text.split()[2]
                buchstaben = sorted(set(z for z in ziffern if z in "ABCDEF"))
                if buchstaben:
                    gesehen["buchstaben"] += 1
                    self.assertIn("   Hex-Ziffern: " + ", ".join(
                        "%s = %d" % (b, 10 + "ABCDEF".index(b)) for b in buchstaben), steps)
                else:
                    self.assertNotIn("Hex-Ziffern:", steps)
            else:
                gesehen["andere"] += 1
                self.assertIn("Binär -> Hex: in Vierergruppen (Nibbles)", steps)
                self.assertNotIn("Hex-Ziffern:", steps)
        self.assertTrue(all(gesehen.values()), gesehen)

    def test_5_11_folge_oktette(self):
        satz = ("   Die Oktette danach sind in der Netzadresse 0 und in der "
                "Broadcast-Adresse 255.")
        gesehen = set()
        for task in self._aufgaben("ipv4"):
            prefix = int(task.text.split("/")[1].split()[0])
            mit = prefix % 8 != 0 and prefix < 24
            gesehen.add(mit)
            self.assertEqual(satz in task.steps, mit, (prefix, task.steps))
            if mit:     # Satz stimmt mit der Loesung ueberein
                okt = prefix // 8
                self.assertEqual(task.solution["netz"].split(".")[okt + 1:], ["0"] * (3 - okt))
                self.assertEqual(task.solution["broadcast"].split(".")[okt + 1:],
                                 ["255"] * (3 - okt))
        self.assertEqual(gesehen, {True, False})

    def test_5_12_und_1_19_ipv6(self):
        neu = ("2. Die längste Folge von Nullblöcken (mindestens zwei) durch '::' "
               "ersetzen, bei Gleichstand die erste.")
        hinweis = "   Hier gibt es keine solche Folge, dieser Schritt entfällt."
        gesehen = set()
        for task in self._aufgaben("ipv6", 120):
            if task.fields[0][0] != "kurz":
                continue
            self.assertIn(neu, task.steps)
            ohne = "::" not in task.solution["kurz"]
            gesehen.add(ohne)
            self.assertEqual(hinweis in task.steps, ohne)
            if ohne:
                self.assertEqual(task.steps.index(hinweis), task.steps.index(neu) + 1)
        self.assertEqual(gesehen, {True, False})
        self.assertNotIn("längsten Block aufeinanderfolgender", _quelle("fisi_lernen.py"))

    def test_3_16_aufgabentext(self):
        task = fl.trainer_task("ipv4", 2, "bn07-1")
        self.assertRegex(task.text, r"^Berechne zur Adresse [\d.]+/\d+ die Netzdaten \(die "
                                    r"Adresse kann auch selbst die Netz- oder "
                                    r"Broadcast-Adresse sein\)\.$")

    def test_4_13_artname(self):
        self.assertEqual(fl.TRAINER_KIND_NAME["ipv6"], "IPv6-Schreibweise")
        self.assertIn("„IPv6-Schreibweise“", _quelle("fisi_hilfe.py"))
        self.assertNotIn("IPv6 kürzen", _quelle("fisi_hilfe.py"))

    def test_4_12_kartentitel(self):
        self.assertEqual(getattr(fl, "TRAINER_TITLE", None), "Rechen-Trainer")
        pc, handy = _quelle("app_gui.py"), _quelle(os.path.join("mobile", "src", "main.py"))
        self.assertIn('setup = Card(self, title=TRAINER_TITLE, accent=C["accent"],', pc)
        self.assertIn("ui.Card(TRAINER_TITLE, [", handy)
        for text in (pc, handy):
            self.assertNotIn('"Subnetting-Trainer"', text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
