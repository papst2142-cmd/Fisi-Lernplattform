# -*- coding: utf-8 -*-
"""Tests ab 0.63.2, FG-103 (Variante B, Weisung 42 Abschnitt 2.9): das
Aufzaehlungszeichen am Anfang einer Kriterienzeile faellt nur weg, wenn
Leerraum oder das Zeilenende folgt.

Bis 0.63.1 nahm fisi_pruefung.criteria() mit lstrip("-•*") auch das Minus
einer Befehlsoption weg: "1. -c 1 schickt ..." wurde zum Kriterium
"c 1 schickt ...". Betroffen waren genau vier Teilaufgaben (A1-069 T2,
A2-317 T1, A2-322 T1, A2-328 T3).

  * T1: in den vier Teilaufgaben ist das erste Kriterium genau der erste
    Satz der Loesungszeile ohne Nummer und beginnt mit dem Minus.
  * T2: ueber alle AP1/AP2-Aufgaben unterscheiden sich gegenueber der alten
    Regel genau diese vier Teilaufgaben, jeweils nur durch das fuehrende
    "-" eines Kriteriums; die Kriterienzahl ist ueberall gleich.
  * T3: echte Aufzaehlungen ("- x", "• x", "* x", "-<Tab>x") verlieren ihr
    Zeichen wie bisher, "-" und "---" ebenso; "--privileged a." und
    "*/15 b." behalten es.

Ohne Fenster.  Aufruf:  python test_kriterien_fg103.py
"""
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_TMP = tempfile.mkdtemp(prefix="fisi_kriterien_fg103_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "kriterien.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(_TMP, "selbsttest.log"))
os.environ["HOME"] = _TMP
os.environ["APPDATA"] = _TMP

import fisi_pruefung as fp  # noqa: E402

# (Quelle, Index in der Inhaltsdatei, Teilaufgabe ab 0) -> Anfang des ersten
# Kriteriums; A1-069 = ap1 Index 68 usw.
BETROFFEN = {
    ("ap1", 68, 1): "-rw-r----- = 640",
    ("ap2", 316, 0): "-mtime zählt",
    ("ap2", 321, 0): "-c 1 schickt",
    ("ap2", 327, 2): "-rw-r--r-- ist",
}


def alte_kriterien(text):
    """Die Regel bis 0.63.1 (nur fuer den Vergleich): wie fp.criteria, aber
    mit lstrip("-•*") statt _BULLET."""
    original = getattr(fp, "_BULLET", None)
    fp._BULLET = _AlteRegel()
    try:
        return fp.criteria(text)
    finally:
        fp._BULLET = original


class _AlteRegel:
    """Ersatz fuer _BULLET.sub: nimmt wie bis 0.63.1 alle fuehrenden
    Zeichen "-", "•", "*" weg (Zeile ist da schon gestrippt)."""

    def sub(self, _ersatz, zeile):
        return zeile.lstrip("-•*")


def teilaufgaben():
    """Alle zerlegbaren AP1/AP2-Teilaufgaben als ((Quelle, Index, Nummer), Teil)."""
    for quelle in ("ap1", "ap2"):
        for index, szenario in enumerate(fp.source_data(quelle)):
            teile = fp.scenario_parts(szenario)
            if teile is None:
                continue
            for nummer, teil in enumerate(teile["teile"]):
                yield (quelle, index, nummer), teil


class BetroffeneTest(unittest.TestCase):

    def test_t1_erstes_kriterium_mit_minus(self):
        teile = dict(teilaufgaben())
        for schluessel, anfang in BETROFFEN.items():
            with self.subTest(schluessel):
                teil = teile[schluessel]
                erstes = fp.criteria(teil["loesung"])[0]
                self.assertTrue(erstes.startswith(anfang), erstes)
                # genau der erste Satz der Loesungszeile ohne Nummer
                zeile = teil["loesung"].split("\n")[0].strip()
                self.assertTrue(zeile.startswith(anfang), zeile)
                self.assertTrue(zeile.startswith(erstes), (zeile, erstes))
                self.assertEqual(teil["kriterien"][0], erstes)


class GesamtTest(unittest.TestCase):

    def test_t2_genau_vier_unterschiede(self):
        unterschiede = {}
        zahl = 0
        for schluessel, teil in teilaufgaben():
            neu, alt = fp.criteria(teil["loesung"]), alte_kriterien(teil["loesung"])
            self.assertEqual(len(neu), len(alt), schluessel)
            zahl += 1
            if neu != alt:
                anders = [(a, n) for a, n in zip(alt, neu) if a != n]
                unterschiede[schluessel] = anders
        self.assertGreater(zahl, 1000)
        self.assertEqual(set(unterschiede), set(BETROFFEN))
        for schluessel, anders in unterschiede.items():
            with self.subTest(schluessel):
                # nur ein Kriterium, und nur durch das fuehrende "-"
                self.assertEqual(len(anders), 1, anders)
                alt, neu = anders[0]
                self.assertEqual(neu, "-" + alt)
                self.assertTrue(neu.startswith(BETROFFEN[schluessel]), neu)


class AufzaehlungTest(unittest.TestCase):

    def test_t3_aufzaehlungszeichen(self):
        # "x" steht fuer einen Text; criteria() verwirft Saetze bis 2 Zeichen,
        # darum hier ein laengerer Text
        for zeile in ("- xyz", "• xyz", "* xyz", "-\txyz"):
            with self.subTest(zeile):
                self.assertEqual(fp.criteria(zeile), ["xyz"])
                self.assertEqual(fp.criteria(zeile), alte_kriterien(zeile))
        # nur Zeichen: wie bisher (kein Kriterium, Rueckfall auf den Text)
        for zeile in ("-", "---"):
            with self.subTest(zeile):
                self.assertEqual(fp.criteria(zeile), alte_kriterien(zeile))
                self.assertEqual(fp.criteria(zeile), [zeile])
        self.assertEqual(fp.criteria("--privileged a."), ["--privileged a."])
        self.assertEqual(fp.criteria("*/15 b."), ["*/15 b."])


if __name__ == "__main__":
    unittest.main(verbosity=2)
