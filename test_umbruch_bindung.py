#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests 0.63.2 A5 (PC-Teil): Umbruch im Rechenweg, Wert nicht vom Vorsatz
trennen (Nebenbefund 13).

Plan 0.63.2 (S1 A5, Abschnitt 3.6 A5-PC): In fit_lines (gemeinsam fuer PC
und Handy) gehoeren "=", "->", "→" und "hex" zum folgenden Wort: eine Zeile
endet nicht auf ihnen, der Umbruch kommt davor ("... = 2^7 = 128" /
"= hex 80" statt "... = 128 = hex" / "80"). Dazu der Satz mit Doppelpunkt
"An der naechsten 4-Bit-Grenze (Nibble): /44 = 4.096 Subnetze. ...":
Beschriftung und Wert bleiben in einer Zeile, wenn sie zusammen passen;
Regel F-8 b ("Beschriftung:" und darunter der Wert) nur, wenn nicht.

Geprueft fuer die Rechenwege und Ergebnisse "Netz aufteilen" und "Nach
Hostbedarf" (IPv4/IPv6, feste Netze) und alle Breiten 20 bis 75 Zeichen:
  (a) keine Ausgabezeile, die fit_lines erzeugt hat, endet auf "=", "->",
      "→" oder "hex" - ausser Bindewort und folgendes Wort passen zusammen
      nicht in eine Zeile (dann bleibt es wie bisher)
  (b) Wortlaut: Ausgabe ohne Leerraum = Eingabe ohne Leerraum
  (c) keine Zeile wird durch die Regel breiter als die Breite (verglichen
      mit dem Stand ohne Regel: nur Zeilen, die schon vorher zu breit waren)
Reine Textfunktionen, kein Fenster. Gegen 14b3bd4 rot.

Start:  python test_umbruch_bindung.py
"""

import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import fisi_core as fc  # noqa: E402

BIND = ("=", "->", "→", "hex")
BREITEN = range(20, 76)
AUFTEILEN = (("10.0.0.0/8", "1000", 4), ("192.168.0.0/24", "6", 4),
             ("100.0.0.0/8", "4000000", 4), ("2001:db8::/32", "300", 6),
             ("::/0", "300", 6), ("2001:db8::/48", "16", 6))
BEDARF = (("192.168.10.0/24", "A 50\nB 20\nC 10\nD 2"),
          ("10.0.0.0/8", "Server 2000\nBuero 500\nWLAN 300\nGaeste 60\nLink 2"),
          ("172.16.0.0/16", "Netz1 1000\nNetz2 500\nNetz3 200"))


def texte():
    """(Name, Rohtext) aller geprueften Rechenwege und Ergebnisse."""
    out = []
    for net, count, version in AUFTEILEN:
        result = fc.split_network(net, count, version=version)
        out.append(("aufteilen %s %s Rechenweg" % (net, count), fc.split_explain(result)))
        out.append(("aufteilen %s %s Ergebnis" % (net, count), fc.split_report(result, 1)))
    for net, needs in BEDARF:
        result = fc.subnet_by_hosts(net, needs, version=4)
        out.append(("bedarf %s Rechenweg" % net, fc.hosts_explain(result)))
        out.append(("bedarf %s Ergebnis" % net, fc.hosts_report(result)))
    return out


def ends_bound(line):
    """Bindewoerter am Ende der Zeile (Liste, leer wenn keins)."""
    words = line.split()
    tail = []
    while words and words[-1] in BIND:
        tail.insert(0, words.pop())
    return tail, words


def problems(raw, zeichen):
    shown = fc.fit_lines(raw, zeichen)
    found = []
    raw_lines = set(raw.split("\n"))
    lines = shown.split("\n")
    for number, line in enumerate(lines):
        tail, rest = ends_bound(line)
        if not tail or line in raw_lines:
            continue
        if not rest:
            continue                      # Zeile besteht nur aus Bindewoertern
        follow = lines[number + 1] if number + 1 < len(lines) else ""
        first = follow.split()[0] if follow.split() else ""
        lead = len(follow) - len(follow.lstrip(" "))
        if first and lead + len(" ".join(tail + [first])) > zeichen:
            continue                      # passt zusammen nicht: wie bisher
        found.append("Zeile endet auf %r: %r / %r" % (" ".join(tail), line, follow))
    if "".join(shown.split()) != "".join(raw.split()):
        found.append("Wortlaut weicht ab")
    return found, lines


def _old_line_lengths(raw, zeichen):
    """Zeilenlaengen ohne die Regel (Bindewoerter wirkungslos gemacht)."""
    saved = getattr(fc, "_FIT_BIND", None)
    saved_prose = getattr(fc, "_fit_prose", None)
    try:
        if saved is not None:
            fc._FIT_BIND = ()
        if saved_prose is not None:
            fc._fit_prose = lambda line, z: None
        return fc.fit_lines(raw, zeichen).split("\n")
    finally:
        if saved is not None:
            fc._FIT_BIND = saved
        if saved_prose is not None:
            fc._fit_prose = saved_prose


class BindungTest(unittest.TestCase):

    def test_a_b_alle_breiten(self):
        found = []
        for name, raw in texte():
            for zeichen in BREITEN:
                errors, _lines = problems(raw, zeichen)
                found.extend("%s @%d: %s" % (name, zeichen, e) for e in errors)
        self.assertEqual(found[:20], [], "%d Funde" % len(found))

    def test_c_nicht_breiter(self):
        found = []
        for name, raw in texte():
            for zeichen in BREITEN:
                old = max(len(line) for line in _old_line_lengths(raw, zeichen))
                new = fc.fit_lines(raw, zeichen).split("\n")
                for line in new:
                    if len(line) > zeichen and len(line) > old:
                        found.append("%s @%d: %r (%d > %d, vorher max %d)"
                                     % (name, zeichen, line, len(line), zeichen, old))
        self.assertEqual(found[:20], [], "%d Funde" % len(found))

    def test_beispiele_nebenbefund_13(self):
        result = fc.split_network("2001:db8::/32", "300", version=6)
        raw = fc.split_explain(result)
        # Satz-Zeile (Satzregel, _fit_sentence)
        lines = fc.fit_lines(raw, 60).split("\n")
        self.assertIn("   Schrittweite im 3. Hextett = 2^(48 - 41) = 2^7 = 128", lines)
        self.assertIn("   = hex 80", lines)
        lines = fc.fit_lines(raw, 45).split("\n")
        self.assertIn("   neue Präfixlänge = alte Präfixlänge + k", lines)
        self.assertIn("   = 32 + 9 = 41 -> /41", lines)
        lines = fc.fit_lines(raw, 40).split("\n")
        self.assertIn("   Adressen je Subnetz = 2^(128 - 41)", lines)
        self.assertIn("   = 2^87", lines)
        # Wert-Zeile (Regel F-8 b, _fit_value)
        value = "Schritt : 2^(48 - 41) = 2^7 = 128 = hex 80"
        self.assertEqual(fc.fit_lines(value, 32),
                         "Schritt:\n  2^(48 - 41) = 2^7 = 128\n  = hex 80")
        self.assertEqual(fc.fit_lines("Weg : a = b -> c", 9),
                         "Weg:\n  a = b\n  -> c")

    def test_nibble(self):
        result = fc.split_network("2001:db8::/32", "300", version=6)
        raw = fc.split_explain(result)
        for zeichen in (45, 50, 55, 60, 66):
            lines = fc.fit_lines(raw, zeichen).split("\n")
            row = next(line for line in lines if "(Nibble)" in line)
            self.assertTrue(row.startswith("   An der nächsten 4-Bit-Grenze (Nibble): /44"),
                            (zeichen, row))
            self.assertNotIn("(Nibble):", [line.strip() for line in lines])
        # passt nicht einmal Beschriftung und "/44": Regel F-8 b wie bisher
        lines = fc.fit_lines(raw, 41).split("\n")
        self.assertIn("   An der nächsten 4-Bit-Grenze (Nibble):", lines)
        self.assertIn("     /44 = 4.096 Subnetze. In der", lines)

    def test_spalten_unveraendert(self):
        """Zeilen "Beschriftung : Wert" (Leerzeichen vor dem Doppelpunkt)
        und Tabellen bleiben bei Regel F-8 b bzw. unveraendert."""
        line = "Adressen gesamt       : 79.228.162.514.264.337.593.543.950.336"
        self.assertEqual(fc.fit_lines(line, 36),
                         "Adressen gesamt:\n  79.228.162.514.264.337.593.543.950\n  .336")
        table = "  1   000000000 0000 0000 0000 0000 = 0000  2001:db8::/41"
        self.assertEqual(fc.fit_lines(table, 30), table)

    def test_hilfe_selbst(self):
        self.assertEqual(ends_bound("a = b ="), (["="], ["a", "=", "b"]))
        self.assertEqual(ends_bound("x hex"), (["hex"], ["x"]))
        self.assertEqual(ends_bound("x"), ([], ["x"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
