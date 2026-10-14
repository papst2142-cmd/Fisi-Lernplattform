#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test ab 0.63.2 (FG-109, Weisung 44 Nachtrag 2.2): Der PDF-Export des
Abschlussprojekts bleibt byte-gleich zum Stand vor FG-109 - als FESTER
Erwartungswert (sha256), nicht nur als Vergleich im selben Lauf.

Hintergrund: Ab FG-109 liefert fisi_projekt.euro() "1.234,50" + U+00A0 + "€"
(geschuetztes Leerzeichen). Der PDF-Weg (fisi_pdf._clean) setzt U+00A0 auf ein
normales Leerzeichen; die PDF-Datei muss deshalb Byte fuer Byte dieselbe
bleiben wie mit dem alten Code (a82fd34, " €").

Das Datum in der Fusszeile (datetime.date.today) wird fest auf den 14.10.2026
gesetzt, damit der Erwartungswert nicht vom Tag abhaengt.

P1  sha256 und Laenge der PDF-Datei = fester Wert (erzeugt mit a82fd34)
P2  im Seiteninhalt stehen die Kostenzeilen mit normalem Leerzeichen vor
    dem Euro-Zeichen (cp1252 0x80), nie mit 0xA0

Gegenprobe mit anderem Code-Ordner (z. B. Stand a82fd34, dort ebenfalls gruen):
    PDF_FEST_CODE=<ordner> python test_pdf_festwert_0632.py
"""

import datetime
import hashlib
import os
import re
import sys
import unittest
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("PDF_FEST_CODE") or HERE)
sys.path.insert(0, CODE)

import fisi_pdf          # noqa: E402
import fisi_projekt as fpj  # noqa: E402

PROJEKT = {"titel": "Testprojekt", "kosten_einsparung": "500", "kosten_laufend": "40",
           "material_name_0": "Server", "material_betrag_0": "4999",
           "material_name_1": "Lizenz", "material_betrag_1": "1234,5"}

# Fester Erwartungswert, erzeugt mit dem Code von a82fd34 (vor FG-109) und
# dem Datum 14.10.2026 (Beleg: bau_0.63.2/fg109/logs/pdf_festwert_erzeugen.log)
SOLL_SHA256 = "01546b982fdb55615bdae2ae9d0ccc3c439a5f6cd560a82e0b36efb703d0bbbd"
SOLL_LAENGE = 3499

KOSTEN_ZEILEN = (b"Personalkosten: 1.240,00 \x80", b"Sachkosten: 6.233,50 \x80",
                 b"Projektkosten gesamt: 7.473,50 \x80", b"(460,00 \x80 Einsparung")


class _FesterTag(datetime.date):
    @classmethod
    def today(cls):
        return cls(2026, 10, 14)


class _FestesDatum:
    """Ersatz fuer das Modul datetime in fisi_pdf (nur date.today)."""
    date = _FesterTag


def pdf_bytes(fields=PROJEKT):
    original = fisi_pdf.datetime
    fisi_pdf.datetime = _FestesDatum
    try:
        return fpj.export_pdf(fields)
    finally:
        fisi_pdf.datetime = original


def seiten_inhalt(data):
    teile = re.findall(rb"stream\n(.*?)\nendstream", data, re.S)
    return b"\n".join(zlib.decompress(teil) for teil in teile)


class PdfFestwertTest(unittest.TestCase):

    def test_p1_pdf_bytegleich_fester_wert(self):
        data = pdf_bytes()
        self.assertTrue(data.startswith(b"%PDF-1.4"))
        self.assertEqual(len(data), SOLL_LAENGE)
        self.assertEqual(hashlib.sha256(data).hexdigest(), SOLL_SHA256)

    def test_p2_kostenzeilen_ohne_geschuetztes_leerzeichen(self):
        inhalt = seiten_inhalt(pdf_bytes())
        self.assertIn(b"14.10.2026", inhalt)
        for zeile in KOSTEN_ZEILEN:
            self.assertTrue(zeile in inhalt, zeile)
        self.assertFalse(b"\xa0" in inhalt, "0xA0 im Seiteninhalt")


if __name__ == "__main__":
    unittest.main()
