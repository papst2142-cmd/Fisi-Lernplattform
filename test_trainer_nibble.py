#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests ab 0.63.1 (Nebenbefund 14, Bericht 0.63.1): Trainer "Netz aufteilen",
Rechenweg-Status der Subnetze.

Bei Aufgaben "an Nibble-Grenzen" (IPv6) sagt die Vorueberlegung "verwendet
werden die ersten N"; die Handy-Liste darunter darf dann nur Nr. 1 bis N als
"verwendet" fuehren, alle weiteren als "frei, Reserve". Geprueft fuer alle
Aufgaben "Netz aufteilen" ueber alle Stufen und viele Startwerte, PC- und
Handy-Rechenweg. Die gewuenschte Anzahl N wird aus dem Aufgabentext gelesen,
nicht aus dem Programmcode.

  N-1  Handy: jedes gelistete "Subnetz X: ..." hat den Status, den die
       Aufgabe (und die Vorueberlegung) verlangt; gibt es mehr Subnetze als
       gewuenscht, steht mindestens eines als "frei, Reserve" da
  N-2  Vorueberlegung nennt dieselbe Anzahl wie der Aufgabentext
  N-3  PC: kein Widerspruch (kein "Alle ... werden verwendet" bei Reserve,
       keine Statuszeile), Zeilen hoechstens 75 bzw. 28 Zeichen
  N-4  festes Beispiel trainer_task("teilen", 3, "7-0") woertlich
"""
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import fisi_lernen as fl  # noqa: E402

STARTWERTE = 400
PC_BREITE, HANDY_BREITE = 75, 28
GENUTZT, RESERVE = "verwendet", "frei, Reserve"
AUFGABE = re.compile(r"^Das Netz \S+ soll in ([\d.]+) gleich große Subnetze "
                     r"(an Nibble-Grenzen \(4-Bit-Grenzen\) )?aufgeteilt werden\.")
STATUS = re.compile(r"^Subnetz ([\d.]+): (.*)$")


def zahl(text):
    return int(text.replace(".", ""))


def aufgaben():
    """Alle Stufen, viele Startwerte, auch die Startwerte einer Runde."""
    for stufe in (1, 2, 3):
        for wert in range(STARTWERTE):
            for schmal in (False, True):
                yield fl.trainer_task("teilen", stufe, "nb-%d" % wert, schmal)
        for task in fl.trainer_round("teilen", stufe, "nibble"):
            yield task


def lesen(task):
    treffer = AUFGABE.match(task.text)
    assert treffer, task.text
    return zahl(treffer.group(1)), bool(treffer.group(2))


def vorueberlegung(zeilen):
    """Anzahl aus "verwendet werden die ersten N." (PC eine Zeile, Handy
    ueber zwei Zeilen umbrochen), sonst None."""
    text = " ".join(" ".join(zeilen).split())
    treffer = re.search(r"verwendet werden die ersten ([\d.]+)\.", text)
    return zahl(treffer.group(1)) if treffer else None


class TrainerNibbleStatusTest(unittest.TestCase):

    def test_n0_genug_nibble_aufgaben(self):
        nibble = sum(1 for task in aufgaben() if lesen(task)[1])
        self.assertGreater(nibble, 100)

    def test_n1_handy_status_wie_gewuenscht(self):
        for task in aufgaben():
            gewuenscht, _nibble = lesen(task)
            gelistet = [STATUS.match(z) for z in task.steps_schmal]
            gelistet = [(zahl(t.group(1)), t.group(2)) for t in gelistet if t]
            self.assertTrue(gelistet, task.text)
            for nummer, status in gelistet:
                self.assertEqual(status, GENUTZT if nummer <= gewuenscht else RESERVE,
                                 (task.text, nummer))
            genutzt = [n for n, s in gelistet if s == GENUTZT]
            self.assertEqual(genutzt, [n for n, _s in gelistet if n <= gewuenscht], task.text)
            if max(n for n, _s in gelistet) > gewuenscht:
                self.assertIn(RESERVE, [s for _n, s in gelistet], task.text)

    def test_n2_vorueberlegung_gleich_aufgabe(self):
        for task in aufgaben():
            gewuenscht, nibble = lesen(task)
            for zeilen in (task.steps, task.steps_schmal):
                self.assertEqual(vorueberlegung(zeilen), gewuenscht if nibble else None,
                                 task.text)

    def test_n3_pc_ohne_widerspruch_und_breiten(self):
        for task in aufgaben():
            gewuenscht, nibble = lesen(task)
            self.assertTrue(all(len(z) <= PC_BREITE for z in task.steps), task.text)
            self.assertTrue(all(len(z) <= HANDY_BREITE for z in task.steps_schmal), task.text)
            self.assertFalse([z for z in task.steps if STATUS.match(z.strip())], task.text)
            alle = re.search(r"Alle ([\d.]+) Subnetze werden verwendet",
                             " ".join(task.steps))
            if alle:
                self.assertEqual(zahl(alle.group(1)), gewuenscht, task.text)
            if nibble:
                self.assertIsNone(alle, task.text)

    def test_n4_festes_beispiel(self):
        task = fl.trainer_task("teilen", 3, "7-0")
        self.assertTrue(task.text.startswith("Das Netz 2001:db8:cbf5:8000::/49 soll in 140 "
                                             "gleich große Subnetze an Nibble-Grenzen"))
        status = [z for z in task.steps_schmal if STATUS.match(z)]
        self.assertEqual(status, ["Subnetz 1: verwendet", "Subnetz 2: verwendet",
                                  "Subnetz 3: verwendet", "Subnetz 4: verwendet",
                                  "Subnetz 2.047: frei, Reserve",
                                  "Subnetz 2.048: frei, Reserve"])
        self.assertEqual(task.solution, {
            "adressen": "2^68", "letzte": "2001:db8:cbf5:864f:ffff:ffff:ffff:ffff",
            "praefix": "/60", "netz": "2001:db8:cbf5:8640::"})


if __name__ == "__main__":
    unittest.main(verbosity=1)
