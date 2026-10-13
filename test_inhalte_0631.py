# -*- coding: utf-8 -*-
"""Tests ab 0.63.1: Inhaltsfehler B-C-01 bis B-C-10 (S2).

  * B-C-01: Kachel "Gesamtergebnis" rundet Gesamt und Teil 2 ab (E-C2), damit
    nie "50 Punkte" neben "nicht bestanden" steht. Note und Regeln bleiben.
  * B-C-02 bis B-C-10 (ohne B-C-06, zurueckgestellt): je Befund die korrigierte Stelle (Text-Test, bei Zahlen
    mit Nachrechnung) und dass der alte, falsche Text weg ist.
  * Bestand: Anzahl der Eintraege, richtige Antwort an gleicher Stelle und
    Pruefwerte ueber alle Eintraege ausser den geplanten Feldern (= Stand
    0.62.5, cf4912b). So faellt jede ungeplante Aenderung auf.

Aufruf:  python test_inhalte_0631.py
"""
import ast
import hashlib
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_TMP = tempfile.mkdtemp(prefix="fisi_inhalte_0631_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "inhalte.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(_TMP, "selbsttest.log"))
os.environ["HOME"] = _TMP
os.environ["APPDATA"] = _TMP

import fisi_pruefung as fp  # noqa: E402

INHALTE = os.path.join(HERE, "inhalte")


def lade(datei):
    with open(os.path.join(INHALTE, datei), encoding="utf-8") as handle:
        return json.load(handle)


def anzeige_funktion(datei, name):
    """Die reine Text-Funktion der Kachel (PC: _points, Handy: points_text)
    aus der Quelle lesen, ohne Oberflaeche zu laden."""
    with open(os.path.join(HERE, datei), encoding="utf-8") as handle:
        baum = ast.parse(handle.read())
    knoten = next(k for k in baum.body if isinstance(k, ast.FunctionDef) and k.name == name)
    raum = {}
    exec(compile(ast.Module(body=[knoten], type_ignores=[]), datei, "exec"), raum)
    return raum[name]


PC_PUNKTE = anzeige_funktion("app_gui.py", "_points")
HANDY_PUNKTE = anzeige_funktion(os.path.join("mobile", "src", "main.py"), "points_text")


def kachelzeile(ergebnis, punkte):
    return "Gesamt %s Punkte · %s" % (punkte(ergebnis["gesamt"]),
                                      "bestanden" if ergebnis["bestanden"] else "nicht bestanden")


# ============================================================================
#  B-C-01 Kachel abrunden
# ============================================================================

class KachelAbrundenTest(unittest.TestCase):
    """Werte von 49,95 bis unter 50 wurden als "50" gezeigt, obwohl Note und
    Regeln mit dem ungerundeten Wert "nicht bestanden" ergeben."""

    FAELLE = [
        # (Werte, ungerundet gesamt, Anzeige gesamt, Anzeige teil2)
        (dict(ap1=49.75, projekt=50, konzeption=50, netzwerke=50, wiso=50), "49,9", "50"),
        (dict(ap1=50, projekt=45.0, konzeption=58, netzwerke=60, wiso=56.7), "49,9", "49,9"),
        (dict(ap1=40, projekt=30.0, konzeption=93, netzwerke=100, wiso=76.7), "49,9", "52,4"),
        (dict(ap1=60, projekt=30.0, konzeption=93, netzwerke=100, wiso=56.7), "51,9", "49,9"),
    ]

    def test_grenzfaelle_abgerundet(self):
        for werte, gesamt, teil2 in self.FAELLE:
            ergebnis = fp.overall(werte)
            self.assertEqual(PC_PUNKTE(ergebnis["gesamt"]), gesamt, werte)
            self.assertEqual(PC_PUNKTE(ergebnis["teil2"]), teil2, werte)

    def test_kachel_nie_50_bei_nicht_bestanden(self):
        werte = dict(ap1=50, projekt=45.0, konzeption=58, netzwerke=60, wiso=56.7)
        ergebnis = fp.overall(werte)
        self.assertFalse(ergebnis["bestanden"])
        self.assertTrue(ergebnis["note"].startswith("5"))
        for punkte in (PC_PUNKTE, HANDY_PUNKTE):
            self.assertEqual(kachelzeile(ergebnis, punkte),
                             "Gesamt 49,9 Punkte · nicht bestanden")

    def test_note_und_regeln_unveraendert(self):
        # Schutz: Note und Regeln rechnen weiter ungerundet (49,97 -> Note 5)
        ergebnis = fp.overall(dict(ap1=50, projekt=45.0, konzeption=58, netzwerke=60,
                                   wiso=56.7))
        self.assertEqual([ok for _t, ok in ergebnis["regeln"]], [False, False, True, True])
        gut = fp.overall(dict(ap1=70, projekt=70, konzeption=60, netzwerke=55, wiso=80))
        self.assertEqual(gut["gesamt"], 68.5)
        self.assertTrue(gut["bestanden"])
        alle50 = fp.overall(dict(ap1=50, projekt=50, konzeption=50, netzwerke=50, wiso=50))
        self.assertEqual((alle50["gesamt"], alle50["teil2"]), (50.0, 50.0))
        self.assertTrue(alle50["bestanden"])

    def test_gleitkomma_reste(self):
        # Schutz: Reste der Gleitkommarechnung kippen nicht auf 49,9
        self.assertEqual(PC_PUNKTE(fp._abrunden(49.99999999999999)), "50")
        self.assertEqual(PC_PUNKTE(fp._abrunden(0.1 * 3 * 100 / 0.6)), "50")
        self.assertEqual(fp._abrunden(100.0), 100.0)
        self.assertEqual(fp._abrunden(0.0), 0.0)
        werte = dict(ap1=50, projekt=0.1 * 3 * 100 / 0.6, konzeption=50, netzwerke=50, wiso=50)
        self.assertEqual(PC_PUNKTE(fp.overall(werte)["gesamt"]), "50")


# ============================================================================
#  B-C-02 bis B-C-10 Inhalte
# ============================================================================

class InhalteTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.karten = lade("karteikarten.json")
        cls.quiz = lade("quizfragen.json")
        cls.projekte = lade("projektarbeiten.json")
        cls.ap1 = lade("szenarien_ap1.json")
        cls.ap2 = lade("szenarien_ap2.json")

    def test_b_c_02_raid(self):
        karte = self.karten[33]  # K0034
        self.assertEqual(karte["q"], "Was ist der Unterschied zwischen RAID 5 und RAID 6?")
        self.assertNotIn("RAID 5 ist schneller als RAID 6 bei Schreibzugriffen", karte["options"])
        self.assertIn("RAID 6 ist bei Schreibzugriffen schneller als RAID 5", karte["options"])
        self.assertNotIn("Paritätsplatte und", karte["a_full"])
        self.assertIn("verteilen die Parität über alle Platten", karte["a_full"])
        self.assertEqual(karte["a"], "RAID 6 nutzt doppelte Parität, RAID 5 einfache")

    def test_b_c_03_ausbildungsvertrag(self):
        karte = self.karten[64]  # K0065
        self.assertTrue(karte["q"].startswith("Wer legt die wesentlichen Inhalte eines "
                                              "Ausbildungsvertrags"))
        alles = " ".join([karte["a"], karte["a_full"]] + karte["options"])
        self.assertNotIn("schriftlich", alles)
        self.assertNotIn("Der Vertrag muss nicht schriftlich abgeschlossen werden",
                         karte["options"])
        self.assertIn("Textform", karte["a"])
        # Auflage C-1 (Freigabe Plan 0.63.1): richtige Antwort und Antwort 1 woertlich
        richtig = ("Ausbildender (Betrieb) und Auszubildender vereinbaren u.a. "
                   "Ausbildungsziel, -dauer, Vergütung und Probezeit; der Betrieb hält "
                   "den Inhalt in Textform fest")
        self.assertEqual(karte["a"], richtig)
        self.assertEqual(karte["options"][0], richtig)
        self.assertEqual(karte["options"][2], "Die Berufsschule legt die Vertragsinhalte fest")
        self.assertNotIn("vereinbaren sie", alles)
        self.assertNotIn("formfrei", alles)
        self.assertIn("in Textform ab", karte["a_full"])
        self.assertIn("§ 11 BBiG", karte["a_full"])
        self.assertEqual(karte["options"][0], karte["a"])

    def test_b_c_04_kalkulation(self):
        hinweis = self.projekte[4]["hinweise"][4]  # T005
        self.assertEqual((6 * 150, 8 * 250), (900, 2000))
        self.assertIn("6-8 Access Points (je ca. 150-250 Euro) = ca. 900-2.000 Euro", hinweis)
        self.assertNotIn("1.200-2.000", hinweis)

    def test_b_c_05_poe(self):
        projekt = self.projekte[9]  # T010
        hinweis = projekt["hinweise"][3]
        self.assertAlmostEqual(8 * 15.4, 123.2)
        self.assertIn("8 * 15,4 W = 123,2 W", hinweis)
        self.assertIn("IEEE 802.3af", hinweis)
        self.assertIn("150 W", hinweis)
        self.assertNotIn("120 W", hinweis)
        self.assertNotIn("104 W", hinweis)
        self.assertIn("(je Kamera 12,95 W)", projekt["aufgaben"][3])

    def test_b_c_06_zurueckgestellt(self):
        # B-C-06 (P1480) ist zurueckgestellt: Der Fragetext darf wegen
        # test_rahmenplan.UmhaengenTest (Fragetexte Stand 0.54) ohne Freigabe
        # nicht geaendert werden. Bis zur Entscheidung bleibt er wie in 0.62.5.
        frage = self.quiz[1479]  # P1480
        self.assertTrue(frage["q"].endswith("Wie lange dauert das mindestens (ohne Overhead)?"))
        self.assertEqual(frage["a"], "ca. 28 Minuten 48 Sekunden")

    def test_b_c_07_quote(self):
        loesung = self.ap1[182]["solution"][2]  # A1-183
        self.assertEqual((80 - 4) / 80, 0.95)
        self.assertIn("76 / 80 = 95,0 %", loesung)
        self.assertNotIn("78 / 80", loesung)
        self.assertNotIn("97,5", loesung)
        self.assertIn("Der Versandhändler muss abnehmen.", loesung)

    def test_b_c_08_ruegepflicht(self):
        loesung = self.ap2[123]["solution"][0]  # A2-124
        self.assertNotIn("Da beide Seiten Unternehmer sind", loesung)
        for teil in ("§ 377 HGB", "zwischen Kaufleuten", "§ 14 BGB", "§ 477 BGB",
                     "in der Regel aber kein Kaufmann"):
            self.assertIn(teil, loesung)
        # Antwort 5 (Meldung 10): "in der Regel kein Kaufmann" ohne Ausnahmen im Lerntext
        for ausnahme in ("MVZ", "Formkaufmann", "GmbH", "§ 6 HGB"):
            self.assertNotIn(ausnahme, loesung)

    def test_b_c_09_egress(self):
        loesung = self.ap2[288]["solution"][2]  # A2-289
        speicher = (396 + 558) / 2 * 60
        abrufe = round(10000 * (0.02 + 0.07) * 5, 2)
        self.assertEqual((speicher, abrufe), (28620, 4500))
        self.assertEqual(50000 - (speicher + abrufe), 16880)
        self.assertIn("10.000 GB * (0,02 + 0,07) * 5 = 4.500 Euro", loesung)
        self.assertIn("28.620 + 4.500 = 33.120 Euro", loesung)
        self.assertIn("B ist 16.880 Euro günstiger", loesung)
        for alt in ("29.620", "20.380", "= 1.000 Euro"):
            self.assertNotIn(alt, loesung)

    def test_b_c_10_zentrale(self):
        loesung = self.ap2[293]["solution"][2]  # A2-294
        gespraeche = round(6 * 2 * 0.1, 1)
        self.assertEqual(gespraeche, 1.2)
        self.assertEqual(round(14 * 4 + gespraeche, 1), 57.2)
        self.assertEqual(round((14 * 2 + gespraeche) / 40 * 100, 1), 73.0)
        self.assertIn("6 * 2 * 0,1 = 1,2 Mbit/s", loesung)
        self.assertIn("57,2 Mbit/s von 100, also 57,2 %", loesung)
        self.assertIn("29,2 Mbit/s von 40, also 73 %", loesung)
        for alt in ("56,6", "28,6", "71,5"):
            self.assertNotIn(alt, loesung)


# ============================================================================
#  Bestand bleibt (nur geplante Felder geaendert)
# ============================================================================

# Geplante Felder je Datei: {Index: [Feldpfad, ...]}
GEPLANT = {
    "karteikarten.json": {33: [("options", 1), ("a_full",)],
                          64: [("a",), ("options", 0), ("options", 2), ("a_full",)]},
    "projektarbeiten.json": {4: [("hinweise", 4)], 9: [("hinweise", 3)]},
    "szenarien_ap1.json": {182: [("solution", 2)]},
    "szenarien_ap2.json": {123: [("solution", 0)], 288: [("solution", 2)],
                           293: [("solution", 2)]},
}
# Ab 0.63.2 (FG-25): zusaetzlich die Felder der Inhaltskorrekturen 0.63.2
# (S4: A14/B-C-06, B-C-11 bis B-C-39, B-D-13 "ModeWelt", B-N-13). Einzeln
# geprueft in test_inhalte_0632.py; hier bleibt alles UEBRIGE gesperrt.
GEPLANT_0632 = {
    "karteikarten.json": {58: [("a",), ("options", 0), ("a_full",)], 120: [("q",)],
                          159: [("a_full",)], 301: [("a",), ("options", 0), ("a_full",)],
                          740: [("q",)], 858: [("a_full",)], 859: [("a_full",)],
                          882: [("options", 1), ("a_full",)],
                          1295: [("a",), ("options", 0), ("a_full",)], 1429: [("q",)]},
    "projektarbeiten.json": {0: [("aufgaben", 4), ("ausgangssituation",)], 9: [("hinweise", 0)],
                             21: [("aufgaben", 3), ("hinweise", 3)], 27: [("hinweise", 4)],
                             37: [("hinweise", 3)], 44: [("rahmenbedingungen", 4)],
                             47: [("aufgaben", 2)]},
    "quizfragen.json": {28: [("exp",)], 71: [("exp",), ("q",)], 158: [("q",)],
                        628: [("options", 0), ("a",)], 777: [("exp",)],
                        828: [("exp",), ("q",)], 931: [("q",)], 1024: [("q",)],
                        1323: [("exp",), ("q",)], 1479: [("options", 3), ("exp",)],
                        1495: [("exp",), ("q",)], 1933: [("exp",), ("q",)], 2102: [("q",)]},
    "szenarien_ap1.json": {4: [("solution", 2)], 58: [("solution", 4)], 91: [("text", 0)],
                           143: [("solution", 0)],
                           207: [("text", 2), ("text", 3), ("text", 4), ("text", 5)]},
    "szenarien_ap2.json": {0: [("solution", 0), ("solution", 6)],
                           23: [("text", 1), ("text", 2), ("text", 3)],
                           25: [("solution", 2), ("solution", 3)],
                           46: [("text", 1), ("text", 2), ("text", 3), ("text", 4)],
                           134: [("text", 0), ("solution", 0)],
                           218: [("text", 10), ("text", 11), ("text", 12)], 223: [("text", 0)],
                           228: [("text", 1), ("text", 2), ("text", 3), ("text", 4), ("text", 5)],
                           296: [("text", 2), ("text", 3), ("text", 4), ("text", 5)]},
}
for _datei, _felder in GEPLANT_0632.items():
    for _index, _pfade in _felder.items():
        GEPLANT.setdefault(_datei, {}).setdefault(_index, []).extend(_pfade)
ANZAHL = {"karteikarten.json": 1565, "quizfragen.json": 2120, "szenarien_ap1.json": 265,
          "szenarien_ap2.json": 330, "projektarbeiten.json": 50}
# SHA-256 ueber alle Eintraege, geplante Felder durch "*" ersetzt (Stand 0.62.5, cf4912b;
# quizfragen.json ohne geplante Felder, B-C-06 zurueckgestellt)
# Ab 0.63.2 (FG-25): mit den Feldern 0.63.1 UND 0.63.2 als "*". Derselbe Wert ergibt
# sich auf dem Stand 0.63.1 (14b3bd4): ausserhalb der geplanten Felder ist nichts
# geaendert. Werte bis 0.63.1: adfb69fb...7165, 7cc29b85...c9c3, 321e2e6e...9a95,
# d1dc2c96...af35, bfc9e918...00c6.
PRUEFWERT = {
    "karteikarten.json":
        "cbd53db8dcb19862ea601aeee64e8bd7e01cf26ea37f5736d1aef700296d0e99",
    "quizfragen.json":
        "84ed04c712799f04c4f9f173165f4b9ad3cba74c26c41317b433f26db3a9acfd",
    "szenarien_ap1.json":
        "13c8429fcc4bd64b66ed854bdcd07d210b482ba22ef442a08f3e2557f9a326c1",
    "szenarien_ap2.json":
        "4b7836306538051516a606f0472b87be9ad86ed28509776d8d75d3fb5d249879",
    "projektarbeiten.json":
        "eda3cfcd6bd42e9094dc66d779476f898ecf7fa01c3078ff631df190a7727f83",
}
PRUEFWERT_UMBENENNUNGEN = "a2ae7b3264d79cf6d82353de5277f03d91f4122507731609e6af031719d0706f"
P1480_NEU = ("Im Schulungsraum werden 12 PCs gleichzeitig mit einem Image von je 18 GB "
             "betankt. Der Deployment-Server hängt mit 1 Gbit/s am Switch. Wie lange dauert "
             "das mindestens (ohne Overhead, 1 GB = 10^9 Byte)?")


def pruefwert(datei, eintraege):
    kopie = json.loads(json.dumps(eintraege))
    for index, pfade in GEPLANT.get(datei, {}).items():
        for pfad in pfade:
            ziel = kopie[index]
            for teil in pfad[:-1]:
                ziel = ziel[teil]
            ziel[pfad[-1]] = "*"
    text = json.dumps(kopie, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# Ab 0.63.2 (FG-25, F7 d): neue Eintraege (Fragetexte B-N-13, B-C-27/-28/-29/-30/-33).
# Sie werden vor dem Pruefwert entfernt; alle alten Eintraege bleiben so gesperrt
# wie bisher. Die neuen prueft test_inhalte_0632.UmbenennungenTest einzeln.
UMBENENNUNGEN_0632 = {
    "karte": {
        "Welche Domäne trennt ein Router, ein einfacher Switch aber nicht?",
        "Welches Geschäft darf ein Prokurist ohne besondere Befugnis nicht abschließen?",
        "In der Klasse Konto ist das Attribut saldo öffentlich. Ein Kollege setzt es an "
        "einer Stelle im Programm einfach auf einen negativen Wert. Welches OOP-Prinzip "
        "wurde nicht umgesetzt?",
    },
    "quiz": {
        "Welches Protokoll nutzt NFS standardmäßig?",
        "Ein Videorekorder (NVR) hat 8 TB nutzbaren Speicher. 6 Kameras zeichnen dauerhaft "
        "mit je 4 Mbit/s auf. Wie viele volle Tage lassen sich speichern?",
        "Ein Access Point zeigt 867 Mbit/s Datenrate, netto kommen etwa 45 % an. Jeder "
        "Laptop im Seminarraum soll 1,5 MB/s bekommen. Wie viele Laptops kann der AP damit "
        "höchstens gleichzeitig versorgen?",
        "Das IT-Budget bleibt 3 Jahre lang bei 180.000,00 Euro. Die Preise für "
        "IT-Dienstleistungen steigen angenommen um 4 % pro Jahr. Wie viel ist das Budget "
        "im dritten Jahr in heutigen Preisen noch wert?",
        "Welche Phase gehört zum ITIL-Service-Lebenszyklus?",
        "Welche Information steht im Ethernet-Frame, aber nicht im IP-Paket?",
        "Welcher Verkabelungsfehler wird von einem einfachen Durchgangsprüfer (Wiremap) "
        "nicht erkannt?",
        "Bei welchem Onlinekauf hat ein Verbraucher kein Widerrufsrecht?",
        "Welches der folgenden Merkmale ist durch das Allgemeine Gleichbehandlungsgesetz "
        "(AGG) nicht geschützt?",
    },
}


def pruefwert_umbenennungen(daten):
    kopie = json.loads(json.dumps(daten))
    for art, alte in UMBENENNUNGEN_0632.items():
        kopie[art] = {alt: neu for alt, neu in kopie[art].items() if alt not in alte}
    kopie["quiz"] = {alt: neu for alt, neu in kopie["quiz"].items() if neu != P1480_NEU}
    text = json.dumps(kopie, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class BestandTest(unittest.TestCase):

    def test_anzahl(self):
        for datei, anzahl in ANZAHL.items():
            self.assertEqual(len(lade(datei)), anzahl, datei)

    def test_nur_geplante_felder_geaendert(self):
        for datei, soll in PRUEFWERT.items():
            self.assertEqual(pruefwert(datei, lade(datei)), soll, datei)

    def test_umbenennungen_unveraendert(self):
        # B-C-06 zurueckgestellt: kein neuer Eintrag, Datei wie in 0.62.5
        # Ab 0.63.2 (FG-25): alte Eintraege unveraendert (gleicher Pruefwert wie
        # bisher), neu nur die 12 geplanten aus UMBENENNUNGEN_0632.
        daten = lade("umbenennungen.json")
        self.assertEqual(pruefwert_umbenennungen(daten), PRUEFWERT_UMBENENNUNGEN)
        self.assertNotIn(P1480_NEU, daten["quiz"].values())

    def test_richtige_antwort_an_gleicher_stelle(self):
        # B-C-02/03 tauschen nur Texte, die Stelle der richtigen Antwort bleibt
        karten = lade("karteikarten.json")
        self.assertEqual(karten[33]["options"].index(karten[33]["a"]), 0)
        self.assertEqual(karten[64]["options"].index(karten[64]["a"]), 0)
        self.assertEqual(lade("quizfragen.json")[1479]["options"].index(
            "ca. 28 Minuten 48 Sekunden"), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
