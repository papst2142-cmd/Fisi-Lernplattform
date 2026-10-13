#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests 0.63.1 Teil 1.6 Nr. 3: "RFC" und die Zahl dahinter in einer Zeile.

Bericht 0.63 Abschnitt 10 Nr. 3: Am Handy stand "Dokumentation
(2001:db8::/32, RFC" und darunter "3849)". fit_lines (fisi_core, eine Quelle
fuer PC und Handy) behandelt "RFC" und die folgende Zahl jetzt wie ein Wort -
im Wert einer Zeile "Beschriftung : Wert" (_fit_value) und in Saetzen
(_fit_sentence). Die Ausgabe bleibt zeichengleich (nur andere Bruchstelle).

Gegen den Stand nach 1.3 (36da8d1) rot. Laeuft ohne Oberflaeche.
Start:  python test_anzeige_rfc.py
"""

import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import fisi_core as fc  # noqa: E402

RFC_ZAHL = re.compile(r"RFC \d")


def texte():
    """Kerntexte mit "RFC <Zahl>" (Netzdaten IPv6, Hostbedarf, Rechenwege)."""
    found = []
    for net in ("2001:db8::/32", "fc00::/8", "fd12:3456:789a::1/48", "4000::/16", "fe80::1/64",
                "ff02::1/128", "2002::/16", "64:ff9b::/96", "::1/128", "2001::/32"):
        text = fc.subnet_report(net)
        if hasattr(fc, "ipv6_details"):
            text += "".join("\n%-22s: %s" % pair for pair in fc.ipv6_details(net))
        found.append(text)
    result = fc.subnet_by_hosts("192.168.10.0/24", "A 50\nB 20\nC 10\nD 2", version=4)
    found += [fc.hosts_report(result), fc.hosts_explain(result)]
    for net, count in (("2001:db8::/32", "300"), ("10.0.0.0/8", "1000")):
        result = fc.split_network(net, count, version=6 if ":" in net else 4)
        found += [fc.split_explain(result), fc.split_report(result, 1)]
    found += [fc.CALC_EXPLAIN_SUBNET, fc.CALC_EXPLAIN_SUBNET_V6]
    # Satz ohne "Beschriftung : Wert" (Weg _fit_sentence)
    found.append("Dieser Satz nennt RFC 3849 und RFC 4193 und ist absichtlich recht lang.")
    return [text for text in found if RFC_ZAHL.search(text)]


class RfcZeileTest(unittest.TestCase):

    def test_bericht_beispiel(self):
        # das Foto aus Bericht 0.63: 2001:db8::/32 am Handy (Breiten wie S24)
        line = "Adresstyp             : Dokumentation (2001:db8::/32, RFC 3849)"
        for zeichen in (20, 22, 24, 26):
            rows = fc.fit_lines(line, zeichen).split("\n")
            self.assertIn("  (2001:db8::/32,", rows, zeichen)
            self.assertIn("  RFC 3849)", rows, zeichen)

    def test_satz(self):
        satz = "Dieser Satz nennt RFC 3849 und RFC 4193 und ist absichtlich recht lang."
        self.assertEqual(fc.fit_lines(satz, 21).split("\n"),
                         ["Dieser Satz nennt", "RFC 3849 und RFC 4193", "und ist absichtlich",
                          "recht lang."])

    def test_nie_getrennt(self):
        alle = texte()
        self.assertGreaterEqual(len(alle), 5)
        for text in alle:
            for zeichen in range(12, 131):
                shown = fc.fit_lines(text, zeichen)
                for row in shown.split("\n"):
                    self.assertFalse(row.rstrip().endswith("RFC"), (zeichen, row))
                # zeichengleich: nur Leerraum darf sich aendern
                self.assertEqual("".join(shown.split()), "".join(text.split()), zeichen)

    def test_nur_rfc_mit_zahl(self):
        # andere Woerter vor einer Zahl bleiben trennbar (nur "RFC" + Zahl)
        self.assertEqual(fc.fit_lines("Wert : abc RFCx 3849 xyz", 12).split("\n"),
                         ["Wert:", "  abc RFCx", "  3849 xyz"])
        # "RFC" ohne Zahl dahinter bleibt ein eigenes Wort
        self.assertEqual(fc.fit_lines("Wert : siehe RFC der IETF", 13).split("\n"),
                         ["Wert:", "  siehe RFC", "  der IETF"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
