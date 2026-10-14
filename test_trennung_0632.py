#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests 0.63.2 N8 (B-D-06): gemeinsame Umbruchregel fisi_trennung (PC und
Handy), ohne Anzeige.

Weisung zu Meldung 38/40 B3 (a): eigenes ungeschuetztes Modul, Eintrag in
mobile/vorbereiten.py SHARED_FILES (die Handy-App bekommt es), Kopie in
.gitignore. Die APK-Pruefung verlangt es in app.zip (pruefung/apk_pruefen.py
APP_FILES, FG-97, Weisung zu Meldung 42 Frage 5).

Regel (Testplan N8 K2, K4, K5, A-N8-05) mit fester Zeichenbreite gemessen:
  * jede Zeile passt in die Breite (Wortliste x Breiten 80..400 px)
  * ein zu langes Wort wird nach einem vorhandenen Bindestrich geteilt
  * die Nummer "4." bleibt beim ersten Wort
  * passt der Titel mit dem gewoehnlichen Umbruch, bleibt der Text gleich
  * Silbentrennung nur nach der bestaetigten Liste (Weisung zu Meldung 42,
    Fragen 11-13, Meldung 42 Anhang A): alle 33 Woerter mit genau ihren
    Stellen, "nie trennen", mindestens 2 Buchstaben je Seite, bevorzugte
    Stellen zuerst, kein doppelter Strich an einem vorhandenen Bindestrich

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


def ohne_trennstriche(zeilen, text):
    """Setzt die Zeilen wieder zusammen: Leerzeichen an Umbruechen und
    eingefuegte Trennstriche fallen weg (ein vorhandener Bindestrich bleibt)."""
    ziel = text.replace(" ", "")
    ganz = ""
    for index, zeile in enumerate(zeilen):
        stueck = zeile.replace(" ", "")
        if index < len(zeilen) - 1 and stueck.endswith("-") and \
                not ziel[len(ganz):].startswith(stueck):
            stueck = stueck[:-1]
        ganz += stueck
    return ganz


# Erwartung: Meldung 42 Anhang A, Spalte "erwartete Stellen", Wort fuer Wort
# (von Chat bestaetigt, Weisung zu Meldung 42 Abschnitt 2.11). Unabhaengige
# Abschrift - nicht aus fisi_trennung gelesen.
ANHANG_A = """
Wirt|schaft|lich|keits‖be|trach|tung
Wirt|schaft|lich|keits‖ver|gleich
Mehr‖fak|tor-‖Au|then|ti|fi|zie|rung
PRÜ|FUNGS‖TRAI|NER
AN‖PAS|SUN|GEN
Da|ten‖si|che|rungs‖kon|zep|te
Hoch‖ver|füg|bar|keit
Kun|den‖zu|frie|den|heit
IPv6-‖Adres|se
Netz‖werk‖in|fra|struk|tur
Ab|schluss‖pro|jekt
Schwie|rig|keits‖grad
Broad|cast-‖Adres|se
Prä|fix‖län|ge
Wild|card-‖Mas|ke
Punkt-‖zu-‖Punkt-‖Ver|bin|dun|gen
Vir|tu|a|li|sie|rung
Da|ten‖schutz-‖Grund‖ver|ord|nung
Ver|schlüs|se|lung
Nutz‖wert‖ana|ly|se
AP2-‖Pro|jekt‖do|ku|men|ta|ti|on
Amor|ti|sa|ti|ons‖rech|nung
Über|tra|gungs‖ge|schwin|dig|keit
Un|ter|bre|chungs‖freie
UND-‖Ver|knüp|fung
Sub‖netz‖mas|ke
Not|fall‖wie|der‖her|stel|lung
In|ves|ti|ti|ons‖ent|schei|dung
Da|ten‖schutz‖kon|for|me
Do|ku|men|ten‖ma|nage|ment‖sys|tem
Schwach|stel|len‖ma|nage|ment
Netz‖werk‖kom|po|nen|ten
Re|mote‖desk|top‖diens|te-‖Farm
""".split()

# "Nie trennen" (Anhang A): keine Stelle, auch nicht bei Platzmangel mit Strich
NIE_TRENNEN = ("192.168.1.50/24", "255.255.255.0", "IPv6", "AP1", "AP2", "RFC", "3021",
               "2^(32", "-")


def erwartung(eintrag):
    """(wort, alle Stellen, bevorzugte Stellen) aus der Schreibweise der Liste."""
    wort, alle, bevorzugt = "", [], []
    for zeichen in eintrag:
        if zeichen in "‖|":
            alle.append(len(wort))
            if zeichen == "‖":
                bevorzugt.append(len(wort))
        else:
            wort += zeichen
    return wort, alle, bevorzugt


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
                self.assertEqual(ohne_trennstriche(zeilen, text),
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
        """Ohne zulaessige Stelle (Wort nicht in der Liste, kein Bindestrich):
        teilen wie bisher (ohne Strich), Nummer beim Wort, jede Zeile passt."""
        zeilen, geteilt = ft.zeilen("4. Kundenzufriedenheitsanalyse", 150, messen)
        self.assertTrue(geteilt)
        self.assertEqual(zeilen[0], "4. Kundenzufrie")   # 15 Zeichen = 150 px
        self.assertFalse(any(z.endswith("-") for z in zeilen[:-1]), zeilen)


class ListeTest(unittest.TestCase):
    """Weisung zu Meldung 42, Fragen 11-13: nur die bestaetigte Liste
    (Anhang A), mindestens 2 Buchstaben je Seite, einzelner Vokal in der
    Wortmitte zulaessig, bevorzugte Stellen zuerst."""

    def test_33_woerter_genau_ihre_stellen(self):
        self.assertEqual(len(ANHANG_A), 33)
        for eintrag in ANHANG_A:
            wort, alle, bevorzugt = erwartung(eintrag)
            for form in (wort, wort.lower(), wort.upper()):
                self.assertEqual(ft.trennstellen(form), alle, (eintrag, form))
                self.assertEqual(ft.bevorzugte_stellen(form), bevorzugt, (eintrag, form))
            # Satzzeichen am Rand bleiben am Wort ("Investitionsentscheidung:")
            self.assertEqual(ft.trennstellen(wort + ":"), alle, eintrag)
            self.assertEqual(ft.trennstellen("(" + wort + ")"), [p + 1 for p in alle], eintrag)

    def test_nur_die_liste(self):
        """Frage 11 (b): ein Wort ausserhalb der Liste bekommt nur Stellen nach
        einem vorhandenen Bindestrich (keine Silbenregel)."""
        listenwoerter = {erwartung(e)[0].lower() for e in ANHANG_A}
        self.assertEqual({w.lower() for w in (erwartung(e)[0] for e in ft.WOERTER)},
                         listenwoerter)
        for wort in ("Kundenzufriedenheitsanalyse", "Datensicherungskonzept",
                     "Wirtschaftlichkeit", "Anpassung", "Netzwerk"):
            self.assertEqual(ft.trennstellen(wort), [], wort)
        self.assertEqual(ft.trennstellen("Mehrfaktor-Verfahren"), [11])

    def test_nie_trennen(self):
        for wort in NIE_TRENNEN:
            self.assertEqual(ft.trennstellen(wort), [], wort)
        # Formel: nur das Wort "Präfixlänge" darf getrennt werden
        self.assertEqual(ft.trennstellen("Präfixlänge)"), [3, 6, 9])
        for text in ("192.168.1.50/24", "255.255.255.0", "IPv6 AP1 AP2 RFC 3021",
                     "2^(32 - Präfixlänge)"):
            for breite in range(60, 200, 10):
                zeilen, _ = ft.zeilen(text, breite, messen)
                for zeile in zeilen[:-1]:
                    letztes = zeile.split(" ")[-1]
                    if letztes.endswith("-") and letztes != "-":
                        self.assertTrue(text.startswith("2^(32") and
                                        letztes[:-1] in "Präfixlänge",
                                        (text, breite, zeilen))

    def test_mindestens_zwei_buchstaben(self):
        """Frage 12: links und rechts jeder Stelle mindestens 2 Buchstaben -
        auch an einem vorhandenen Bindestrich."""
        for eintrag in ANHANG_A:
            wort = erwartung(eintrag)[0]
            for stelle in ft.trennstellen(wort):
                self.assertGreaterEqual(sum(z.isalpha() for z in wort[:stelle]), 2, eintrag)
                self.assertGreaterEqual(sum(z.isalpha() for z in wort[stelle:]), 2, eintrag)
        self.assertEqual(ft.trennstellen("E-Mail-Adresse"), [7])
        self.assertEqual(ft.trennstellen("IT-X"), [])
        self.assertEqual(ft.trennstellen("-ab-"), [])

    def test_einzelner_vokal_und_vorrang(self):
        """Frage 13: "Vir-tu-a-li-sie-rung" zulaessig; eine weitere Stelle wird
        nur genommen, wenn keine bevorzugte passt."""
        self.assertEqual(ft.zeilen("Virtualisierung", 60, messen)[0][0], "Virtu-")
        # 22 Zeichen Platz: "Wirtschaftlichkeitsbe-" passte, die Fuge geht vor
        self.assertEqual(ft.zeilen("Wirtschaftlichkeitsbetrachtung", 220, messen)[0],
                         ["Wirtschaftlichkeits-", "betrachtung"])
        # passt keine bevorzugte, die hinterste passende weitere Stelle
        self.assertEqual(ft.zeilen("Wirtschaftlichkeitsbetrachtung", 180, messen)[0][0],
                         "Wirtschaftlich-")
        self.assertEqual(ft.zeilen("Nutzwertanalyse", 100, messen)[0],
                         ["Nutzwert-", "analyse"])

    def test_zeilen_der_liste(self):
        """Jedes Wort der Liste in Breiten 80..400 px, mit Nummer "29. " ab
        120 px (dann passt jede Silbe mit Strich, laengste "29. Schwach-" und
        "schluss-"): jede Zeile passt, jede Zeile
        im Wort endet mit "-" (nie "--", kein Rueckfall ohne Strich), getrennt
        nur an Stellen der Liste, die Nummer bleibt beim Wort."""
        for eintrag in ANHANG_A:
            wort, alle, _ = erwartung(eintrag)
            for text, vorn in ((wort, 0), ("29. " + wort, 4)):
                for breite in range(120 if vorn else 80, 401, 10):
                    zeilen, _ = ft.zeilen(text, breite, messen)
                    self.assertEqual(ohne_trennstriche(zeilen, text), text.replace(" ", ""))
                    if vorn:
                        self.assertTrue(len(zeilen[0]) > vorn, (text, breite, zeilen))
                    position = 0
                    for zeile in zeilen[:-1]:
                        self.assertNotIn("--", zeile, (text, breite, zeilen))
                        self.assertLessEqual(messen(zeile), breite, (text, breite, zeilen))
                        stueck = zeile[:-1] if zeile.endswith("-") and \
                            text[position:position + len(zeile)] != zeile else zeile
                        position += len(stueck)
                        self.assertTrue(zeile.endswith("-"), (text, breite, zeilen))
                        self.assertIn(position - vorn, alle, (text, breite, zeilen))

    def test_kein_doppelter_strich(self):
        """An einem vorhandenen Bindestrich kein zweiter Strich."""
        self.assertEqual(ft.zeilen("Punkt-zu-Punkt-Verbindungen", 100, messen)[0][:3],
                         ["Punkt-zu-", "Punkt-", "Verbindun-"])
        self.assertEqual(ft.zeilen("Remotedesktopdienste-Farm", 210, messen)[0],
                         ["Remotedesktopdienste-", "Farm"])

    def test_nummer_titel_handy(self):
        self.assertEqual(ft.nummer_titel(4, "Wirtschaftlichkeit", " ✓"),
                         "4. Wirtschaftlichkeit ✓")


class HandyPaketTest(unittest.TestCase):
    """B3 (a): Die Handy-App bekommt das Modul."""

    def test_shared_files(self):
        sys.path.insert(0, os.path.join(HERE, "mobile"))
        import vorbereiten
        self.assertIn("fisi_trennung.py", vorbereiten.SHARED_FILES)

    def test_apk_pruefung_kennt_modul(self):
        """B3 (a): Die APK-Pruefung verlangt fisi_trennung.pyc in app.zip."""
        sys.path.insert(0, os.path.join(HERE, "pruefung"))
        import apk_pruefen
        self.assertIn("fisi_trennung.pyc", apk_pruefen.APP_FILES)

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
