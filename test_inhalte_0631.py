# -*- coding: utf-8 -*-
"""Tests ab 0.63.1: Inhaltsfehler B-C-01 bis B-C-10 (S2).

  * B-C-01: Kachel "Gesamtergebnis" rundet Gesamt und Teil 2 ab (E-C2), damit
    nie "50 Punkte" neben "nicht bestanden" steht. Note und Regeln bleiben.
  * B-C-02 bis B-C-10: je Befund die korrigierte Stelle (Text-Test, bei Zahlen
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

    def test_b_c_06_einheit(self):
        frage = self.quiz[1479]  # P1480
        self.assertTrue(frage["q"].endswith("(ohne Overhead, 1 GB = 10^9 Byte)?"))
        self.assertEqual(frage["a"], "ca. 28 Minuten 48 Sekunden")
        sekunden = 12 * 18 * 10 ** 9 * 8 / 10 ** 9
        self.assertEqual(divmod(int(sekunden), 60), (28, 48))
        umbenannt = lade("umbenennungen.json")["quiz"]
        alt = frage["q"].replace("(ohne Overhead, 1 GB = 10^9 Byte)?", "(ohne Overhead)?")
        self.assertEqual(umbenannt.get(alt), frage["q"])

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
    "quizfragen.json": {1479: [("q",)]},
    "szenarien_ap1.json": {182: [("solution", 2)]},
    "szenarien_ap2.json": {123: [("solution", 0)], 288: [("solution", 2)],
                           293: [("solution", 2)]},
}
ANZAHL = {"karteikarten.json": 1565, "quizfragen.json": 2120, "szenarien_ap1.json": 265,
          "szenarien_ap2.json": 330, "projektarbeiten.json": 50}
# SHA-256 ueber alle Eintraege, geplante Felder durch "*" ersetzt (Stand 0.62.5, cf4912b)
PRUEFWERT = {
    "karteikarten.json":
        "adfb69fb728ccd513b0e781d777794b8e0e71a71f295526b0c308d9976ee7165",
    "quizfragen.json":
        "38c41c3376bab5b9b169c5e7b87d02c0e4b6df506072fadce7d94978dcf89ac4",
    "szenarien_ap1.json":
        "321e2e6e564791532d68da033f38d87fe3b5c14935a7e8c9b2e6bc7000649a95",
    "szenarien_ap2.json":
        "d1dc2c96d2327f702cf5a0a562481e84c47ac7514aa41be3b8bd84e672a2af35",
    "projektarbeiten.json":
        "bfc9e918e2a31ed30d1ef8f385d18b784a42560af581e2d81ecdeab3a51000c6",
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


def pruefwert_umbenennungen(daten):
    kopie = json.loads(json.dumps(daten))
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

    def test_umbenennungen_nur_angehaengt(self):
        daten = lade("umbenennungen.json")
        self.assertEqual(pruefwert_umbenennungen(daten), PRUEFWERT_UMBENENNUNGEN)
        self.assertEqual(list(daten["quiz"].values())[-1], P1480_NEU)

    def test_richtige_antwort_an_gleicher_stelle(self):
        # B-C-02/03 tauschen nur Texte, die Stelle der richtigen Antwort bleibt
        karten = lade("karteikarten.json")
        self.assertEqual(karten[33]["options"].index(karten[33]["a"]), 0)
        self.assertEqual(karten[64]["options"].index(karten[64]["a"]), 0)
        self.assertEqual(lade("quizfragen.json")[1479]["options"].index(
            "ca. 28 Minuten 48 Sekunden"), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
