#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests 0.63.2 N8 (B-D-06): gemeinsame Umbruchregel fisi_trennung (PC und
Handy), ohne Anzeige.

Weisung zu Meldung 38/40 B3 (a): eigenes ungeschuetztes Modul, Eintrag in
mobile/vorbereiten.py SHARED_FILES (die Handy-App bekommt es), Kopie in
.gitignore. Die Pruefung, dass die fertige APK es enthaelt
(pruefung/apk_pruefen.py APP_FILES), braucht eine Aenderung an
apk_pruefen.py -> FG-97-Antrag (bau_0.63.2/n8), hier nicht gebaut.

Regel (Testplan N8 K2, K4, K5, A-N8-05) mit fester Zeichenbreite gemessen:
  * jede Zeile passt in die Breite (Wortliste x Breiten 80..400 px)
  * ein zu langes Wort wird nach einem vorhandenen Bindestrich geteilt
  * die Nummer "4." bleibt beim ersten Wort
  * passt der Titel mit dem gewoehnlichen Umbruch, bleibt der Text gleich
  * Silbentrennung ist NICHT gebaut (N8-F2: Erwartungsliste liegt bei Chat)

Start:  python test_trennung_0632.py
"""

import ast
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import fisi_trennung as ft  # noqa: E402

WOERTER = ["Mehrfaktor-Authentifizierung", "Wirtschaftlichkeitsbetrachtung",
           "PRÜFUNGSTRAINER", "Netzwerkinfrastruktur", "Datensicherungskonzept",
           "Hochverfügbarkeit", "IPv6-Adressierung", "Kundenzufriedenheitsanalyse",
           "4. Wirtschaftlichkeitsbetrachtung", "Einführung einer Mehrfaktor-Authentifizierung",
           "12. Einfache Wirtschaftlichkeitsbetrachtung ✓", "OPTISCHE ANPASSUNGEN"]


def messen(text):
    """Feste Zeichenbreite 10 px (wie eine Schaetzung je Zeichen am Handy)."""
    return 10 * len(text)


class RegelTest(unittest.TestCase):

    def test_jede_zeile_passt(self):
        """A-N8-05: Wortliste x Breiten 80..400 px - keine Zeile breiter als
        die Breite, kein Zeichen verloren (ausser eingefuegten Trennstrichen
        und den Leerzeichen an Umbruechen)."""
        for text in WOERTER:
            for breite in range(80, 401, 10):
                zeilen, _geteilt = ft.zeilen(text, breite, messen)
                for zeile in zeilen:
                    self.assertLessEqual(messen(zeile), breite, (text, breite, zeilen))
                self.assertEqual("".join(zeilen).replace(" ", ""),
                                 text.replace(" ", ""), (text, breite, zeilen))

    def test_bindestrich(self):
        self.assertEqual(ft.zeilen("Mehrfaktor-Authentifizierung", 200, messen),
                         (["Mehrfaktor-", "Authentifizierung"], True))
        self.assertEqual(ft.anzeige_text("Einführung einer Mehrfaktor-Authentifizierung",
                                         200, messen),
                         "Einführung einer\nMehrfaktor-\nAuthentifizierung")

    def test_nummer_bleibt_beim_titel(self):
        """K4: "4." steht nie allein - auch wenn das Wort geteilt werden muss."""
        for breite in range(60, 400, 10):
            for text in ("4. Wirtschaftlichkeitsbetrachtung", "4. Mehrfaktor-Authentifizierung",
                         "12. Einfache Wirtschaftlichkeitsbetrachtung ✓"):
                zeilen, _ = ft.zeilen(text, breite, messen)
                nummer = text.split(" ")[0]
                self.assertTrue(zeilen[0].startswith(nummer + " ") and
                                len(zeilen[0]) > len(nummer) + 1, (text, breite, zeilen))
        self.assertEqual(ft.zeilen("4. Mehrfaktor-Authentifizierung", 150, messen)[0][0],
                         "4. Mehrfaktor-")

    def test_unveraendert_wenn_es_passt(self):
        """K5: passt der Titel mit dem gewoehnlichen Umbruch, bleibt der Text
        zeichengleich (keine Trennung auf Vorrat, kein Zeilenumbruch)."""
        for text in ("3. Netzplan für eine Arztpraxis", "Einfache Wirtschaftlichkeitsbetrachtung",
                     "4. Wirtschaftlichkeitsbetrachtung"):
            self.assertEqual(ft.anzeige_text(text, 400, messen), text)
        # an Leerzeichen umbrechen reicht -> Text bleibt gleich (Tk/Flutter brechen)
        self.assertEqual(ft.anzeige_text("3. Netzplan für eine Arztpraxis", 150, messen),
                         "3. Netzplan für eine Arztpraxis")

    def test_rueckfall_ohne_stelle(self):
        """Ohne zulaessige Stelle: teilen wie bisher (ohne Strich), Nummer beim
        Wort, jede Zeile passt."""
        zeilen, geteilt = ft.zeilen("4. Wirtschaftlichkeitsbetrachtung", 150, messen)
        self.assertTrue(geteilt)
        self.assertEqual(zeilen[0], "4. Wirtschaftli")   # 15 Zeichen = 150 px
        self.assertFalse(any(z.endswith("-") for z in zeilen[:-1]), zeilen)

    def test_silbenregel_noch_nicht_gebaut_n8_f2(self):
        """Vorbehalt N8-F2 (Weisung 38/40): bis Chat die Erwartungsliste
        bestaetigt, kennt die Regel nur Stellen nach vorhandenen Bindestrichen.
        Faellt dieser Test, wurde die Silbenregel ohne Bestaetigung gebaut."""
        self.assertEqual(ft.trennstellen("Wirtschaftlichkeitsbetrachtung"), [])
        self.assertEqual(ft.trennstellen("PRÜFUNGSTRAINER"), [])
        self.assertEqual(ft.trennstellen("Mehrfaktor-Authentifizierung"), [11])
        self.assertEqual(ft.trennstellen("-ab-"), [])

    def test_nummer_titel_handy(self):
        self.assertEqual(ft.nummer_titel(4, "Wirtschaftlichkeit", " ✓"),
                         "4. Wirtschaftlichkeit ✓")


class HandyPaketTest(unittest.TestCase):
    """B3 (a): Die Handy-App bekommt das Modul."""

    def test_shared_files(self):
        sys.path.insert(0, os.path.join(HERE, "mobile"))
        import vorbereiten
        self.assertIn("fisi_trennung.py", vorbereiten.SHARED_FILES)

    def test_gitignore(self):
        with open(os.path.join(HERE, ".gitignore"), encoding="utf-8") as handle:
            self.assertIn("mobile/src/fisi_trennung.py", handle.read().splitlines())

    def test_handy_liste_nutzt_regel(self):
        """K4 am Handy: die Listenzeile setzt "4." mit geschuetztem
        Leerzeichen vor den Titel (fisi_trennung.nummer_titel)."""
        with open(os.path.join(HERE, "mobile", "src", "main.py"), encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import)
                   for alias in node.names}
        self.assertIn("fisi_trennung", imports)
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and
                 isinstance(node.func, ast.Attribute) and node.func.attr == "nummer_titel"]
        self.assertTrue(calls)


if __name__ == "__main__":
    unittest.main(verbosity=2)
