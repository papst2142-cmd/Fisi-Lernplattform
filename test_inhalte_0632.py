# -*- coding: utf-8 -*-
"""Tests ab 0.63.2: Inhaltskorrekturen Strang S4.

  * A14/B-C-06 (P1480, Fragetext bleibt), B-C-11 (8 Szenarien wieder in der
    Pruefungssimulation, Text-Weg), B-C-12 bis B-C-39, B-D-13 (Typografie,
    "ModeWelt") mit Z8 (weitere "..." in Statustexten), B-N-13 (Verneinung
    gross): je Befund die korrigierte Stelle und dass der alte Text weg ist,
    bei Zahlen mit Nachrechnung.
  * Bestand: Anzahl 1.565/2.120/265/330/50, genau eine Option = Antwort,
    richtige Antwort an gleicher Stelle, Wortlaut aller 80 geaenderten Felder
    (Pruefwert), Rahmenplan-Zuordnung der geaenderten Fragen unveraendert.
  * Umbenennungen (F7 d): 10 Fragetexte im Schutzbereich STAND_054 und 2
    ausserhalb, je ein Eintrag in inhalte/umbenennungen.json, alte Eintraege
    unveraendert.
  * Lernstand-Migration (Plan 8.1 Nr. 3): Datenbank mit dem Code v0.63.1 und
    Antworten zu allen 12 umbenannten Fragen anlegen, mit diesem Stand
    oeffnen: geaendert sind genau diese Fragetexte, alles andere gleich,
    Lernstand je Frage vollstaendig; ohne solche Antworten bleibt die Datei
    byte-gleich; Antworten eines Geraets mit v0.63.1 per Abgleich zaehlen
    beim neuen Text.

Aufruf:  python test_inhalte_0632.py
"""
import ast
import datetime
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_TMP = tempfile.mkdtemp(prefix="fisi_inhalte_0632_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "inhalte.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(_TMP, "selbsttest.log"))
os.environ["HOME"] = _TMP
os.environ["APPDATA"] = _TMP

import fisi_pruefung as fp  # noqa: E402

INHALTE = os.path.join(HERE, "inhalte")
IN_CI = bool(os.environ.get("GITHUB_ACTIONS") or os.environ.get("CI"))
ALT_TAG = "v0.63.1"


def lade(datei):
    with open(os.path.join(INHALTE, datei), encoding="utf-8") as handle:
        return json.load(handle)


def literale(datei):
    """Alle Stringliterale einer Quelldatei (ohne Oberflaeche zu laden).
    Aneinandergehaengte Literale ("a" "b") sind dabei ein Text."""
    with open(os.path.join(HERE, datei), encoding="utf-8") as handle:
        baum = ast.parse(handle.read())
    return [k.value for k in ast.walk(baum)
            if isinstance(k, ast.Constant) and isinstance(k.value, str)]


# ============================================================================
#  Inhalte je Befund
# ============================================================================

class InhalteTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.karten = lade("karteikarten.json")
        cls.quiz = lade("quizfragen.json")
        cls.projekte = lade("projektarbeiten.json")
        cls.ap1 = lade("szenarien_ap1.json")
        cls.ap2 = lade("szenarien_ap2.json")

    def test_b_c_06_p1480(self):
        frage = self.quiz[1479]  # P1480
        # A14 / F7 (d): Fragetext bleibt, Antwort und Stelle bleiben
        self.assertTrue(frage["q"].endswith("Wie lange dauert das mindestens (ohne Overhead)?"))
        self.assertEqual(frage["a"], "ca. 28 Minuten 48 Sekunden")
        self.assertEqual(frage["options"][0], frage["a"])
        # die binaere Rechnung ist keine angebotene Falschantwort mehr
        self.assertNotIn("ca. 30 Minuten 55 Sekunden", frage["options"])
        self.assertEqual(frage["options"][3], "ca. 4 Stunden 48 Minuten")
        self.assertIn("(GB hier dezimal, 1 GB = 10^9 Byte)", frage["exp"])
        self.assertIn("= 1.728 s = 28 Minuten 48 Sekunden.", frage["exp"])
        self.assertEqual(12 * 18 * 10**9 * 8 / 10**9, 1728)                 # 28:48
        self.assertEqual(divmod(1728, 60), (28, 48))
        self.assertEqual(round(12 * 18 * 2**30 * 8 / 10**9), 1855)          # 30:55
        self.assertEqual(divmod(1855, 60), (30, 55))
        self.assertEqual(12 * 18 * 10**9 * 8 // (100 * 10**6), 17280)       # 4:48:00
        self.assertEqual(divmod(17280, 60), (288, 0))                       # 288 min = 4 h 48 min
        self.assertEqual(divmod(288, 60), (4, 48))

    def test_b_c_11_jedes_szenario_simulierbar(self):
        for quelle, liste in (("AP1", fp.AP1_SZENARIEN), ("AP2", fp.SZENARIEN)):
            ohne = [nummer + 1 for nummer, szenario in enumerate(liste)
                    if fp.scenario_parts(szenario) is None]
            self.assertEqual(ohne, [], quelle)
        teile = {("ap1", 208): 3, ("ap2", 1): 2, ("ap2", 24): 3, ("ap2", 26): 3,
                 ("ap2", 47): 3, ("ap2", 219): 3, ("ap2", 229): 3, ("ap2", 297): 3}
        for (quelle, nummer), anzahl in teile.items():
            liste = fp.AP1_SZENARIEN if quelle == "ap1" else fp.SZENARIEN
            self.assertEqual(len(fp.scenario_parts(liste[nummer - 1])["teile"]), anzahl,
                             (quelle, nummer))
            self.assertIn(nummer - 1, fp.usable_indices(quelle, liste[nummer - 1]["theme"]))

    def test_b_c_11_zeilen(self):
        zeilen = {("ap1", 207): [2, 3, 4, 5], ("ap2", 23): [1, 2, 3],
                  ("ap2", 46): [1, 2, 3, 4], ("ap2", 218): [11, 12],
                  ("ap2", 228): [1, 2, 3, 4, 5], ("ap2", 296): [3, 4, 5]}
        for (quelle, index), nummern in zeilen.items():
            text = (self.ap1 if quelle == "ap1" else self.ap2)[index]["text"]
            for nummer in nummern:
                self.assertTrue(text[nummer].startswith("  - "), (quelle, index, nummer))
                self.assertFalse(text[nummer][4].isspace(), (quelle, index, nummer))
        # Tabellenkoepfe zwei Leerzeichen mehr, damit die Spalten buendig bleiben
        self.assertEqual(self.ap2[218]["text"][10],
                         "    Neighbor ID   Pri  State        Dead Time  Address    Interface")
        self.assertEqual(self.ap2[218]["text"][11].index("1    FULL"),
                         self.ap2[218]["text"][10].index("Pri"))
        self.assertEqual(self.ap2[296]["text"][2],
                         "    Quelle                  Ziel / Dienst                 Mbit/s")
        self.assertEqual(self.ap2[296]["text"][3].index("Cloud-Backup"),
                         self.ap2[296]["text"][2].index("Ziel"))
        loesung = self.ap2[0]["solution"]  # A2-001
        self.assertEqual((loesung[0], loesung[6]), ("1. Subnetze:", "2. Routing:"))
        loesung = self.ap2[25]["solution"]  # A2-026
        self.assertTrue(loesung[2].startswith("   Mail-Relay 10.0.50.20 -> "))
        self.assertTrue(loesung[3].startswith("   Internes Netz 10.0.10.0/24 -> "))

    def test_b_c_12_auskunft(self):
        text = self.karten[858]["a_full"]  # K0859
        self.assertNotIn("Die Monatsfrist läuft ab Eingang beim Verantwortlichen", text)
        self.assertIn("Damit die Monatsfrist für die Antwort (Art. 12 Abs. 3 DSGVO) sicher "
                      "eingehalten wird, muss die Weiterleitung unverzüglich erfolgen.", text)

    def test_b_c_13_signatur(self):
        text = self.karten[859]["a_full"]  # K0860
        self.assertNotIn("mit ihrem öffentlichen Schlüssel", text)
        self.assertIn("prüfen mit dem öffentlichen Schlüssel der Absenderin.", text)

    def test_b_c_14_windows11(self):
        karte = self.karten[882]  # K0883
        self.assertNotIn("Ob der Legacy-Modus (CSM) statt UEFI aktiviert ist", karte["options"])
        self.assertEqual(karte["options"][1], "Ob der Legacy-Modus (CSM) eingeschaltet werden muss")
        self.assertIn("TPM 2.0 und UEFI mit Secure-Boot-Fähigkeit voraus", karte["a_full"])
        self.assertIn("für die Prüfung genügt aber, dass das Mainboard es unterstützt.",
                      karte["a_full"])

    def test_b_c_15_owasp(self):
        karte = self.karten[1295]  # K1296
        neu = ("Veraltete Komponenten (OWASP Top 10:2021, A06), Abhilfe durch Inventar der "
               "Bibliotheken und Updates")
        self.assertEqual((karte["a"], karte["options"][0]), (neu, neu))
        self.assertTrue(karte["a_full"].endswith(
            "Die Bezeichnung folgt der OWASP Top 10:2021, dort ist es die Kategorie A06."))
        self.assertNotIn("2025", karte["a_full"] + karte["a"])

    def test_b_c_16_ftth(self):
        text = self.karten[159]["a_full"]  # K0160
        self.assertNotIn("bis in die Wohnung bzw. das Gebäude", text)
        self.assertIn("bis in die Wohnung (bei FTTB nur bis ins Gebäude, danach Kupfer).", text)

    def test_b_c_17_prokura(self):
        karte = self.karten[301]  # K0302
        neu = "Eine umfassende, gesetzlich festgelegte Vollmacht, die im Handelsregister eingetragen wird"
        self.assertEqual((karte["a"], karte["options"][0]), (neu, neu))
        self.assertNotIn("umfassende Handlungsvollmacht", " ".join(karte["options"]))
        self.assertIn("Handlungsvollmacht (§ 54 HGB)", karte["a_full"])
        self.assertIn("wird nicht ins Handelsregister eingetragen.", karte["a_full"])

    def test_b_c_18_scrum(self):
        karte = self.karten[58]  # K0059
        neu = "Product Owner, Scrum Master und Developers (Entwickler)"
        self.assertEqual((karte["a"], karte["options"][0]), (neu, neu))
        self.assertIn("die Developers setzen die Arbeit in Sprints um", karte["a_full"])
        self.assertIn("Scrum-Leitfaden von 2020", karte["a_full"])
        self.assertNotIn("das Entwicklungsteam setzt", karte["a_full"])

    def test_b_c_19_zeitplan(self):
        hinweis = self.projekte[37]["hinweise"][3]  # T038
        self.assertEqual(9 + 10 + 3, 22)
        self.assertEqual((22 / 4, 22 / 8), (5.5, 2.75))
        self.assertNotIn("24 Stunden / 4 Stunden", hinweis)
        self.assertIn("Vor Ort fallen 9 + 10 + 3 = 22 Stunden an", hinweis)
        self.assertIn("22 Stunden / 4 Stunden je Abend = 5,5, also 6 Abende", hinweis)
        self.assertIn("22 / 8 = 2,75, also 3 Abende", hinweis)
        self.assertIn("Gruppe B ist dabei vereinfacht ganz als Vor-Ort-Zeit gerechnet", hinweis)

    def test_b_c_20_preiserhoehung(self):
        text = self.projekte[44]["rahmenbedingungen"][4]  # T045
        self.assertIn("danach ist eine einmalige Erhöhung um höchstens 4 % möglich", text)

    def test_b_c_21_daempfung(self):
        text = self.projekte[47]["aufgaben"][2]  # T048
        self.assertIn("das Tropenhaus (Faserdämpfung vereinfacht mit der Trassenlänge). Reicht",
                      text)

    def test_b_c_22_bdsg(self):
        # Wortlaut Freigabe Plan 0.63.2, Abschnitt 5
        hinweis = self.projekte[9]["hinweise"][0]  # T010
        self.assertTrue(hinweis.endswith(
            "Für Beschäftigte ist zusätzlich § 26 BDSG zu beachten. Nach dem Urteil des EuGH "
            "vom 30.03.2023 (C-34/21) zur gleichlautenden hessischen Regelung ist auch die "
            "allgemeine Regel des § 26 Abs. 1 Satz 1 BDSG in vielen Fällen nicht anwendbar; "
            "die Rechtsgrundlage bleibt dann Art. 6 Abs. 1 DSGVO."))
        self.assertNotIn("nur eingeschränkt anwendbar", hinweis)

    def test_b_c_23_leitung(self):
        text = self.projekte[0]["aufgaben"][4]  # T001
        self.assertNotIn("Standleitung", text)
        self.assertIn("gegen den Ausfall der Internetleitung (Hauptleitung) ab?", text)

    def test_b_c_24_naechte(self):
        projekt = self.projekte[21]  # T022
        self.assertEqual(22 / 2, 11)
        self.assertIn("Wie viele Nächte brauchen Sie höchstens, bis alle 22 Switches umgestellt "
                      "sind?", projekt["aufgaben"][3])
        self.assertNotIn("dauert die Umstellung der Switches nach dem Pilot", projekt["aufgaben"][3])
        self.assertIn("Danach höchstens 22 / 2 = 11 Nächte für alle Switches (sind die Switches "
                      "des Pilotbereichs schon umgestellt, entsprechend weniger).",
                      projekt["hinweise"][3])

    def test_b_c_25_grundschutz(self):
        hinweis = self.projekte[27]["hinweise"][4]  # T028
        self.assertNotIn("Diese ist Voraussetzung für eine spätere ISO-27001-Zertifizierung", hinweis)
        self.assertTrue(hinweis.endswith(
            "Eine spätere ISO-27001-Zertifizierung auf Basis von IT-Grundschutz ist mit der "
            "Standard- oder der Kern-Absicherung möglich, mit der Basis-Absicherung allein nicht."))

    def test_b_c_26_umask(self):
        text = self.quiz[777]["exp"]  # P0778
        self.assertEqual(oct(0o666 & ~0o027), "0o640")
        self.assertNotEqual(oct(0o666 - 0o027), "0o640")
        self.assertNotIn("666 - 027", text)
        self.assertIn("666 UND NICHT 027 (bitweise) ergibt 640", text)

    def test_b_c_27_nfs(self):
        frage = self.quiz[828]  # P0829
        self.assertEqual(frage["q"], "Welchen Port nutzt NFS standardmäßig?")
        self.assertIn("Port 2049 (NFS Version 4 über TCP, Version 3 über TCP oder UDP)", frage["exp"])
        self.assertIn("2049", frage["a"])

    def test_b_c_28_nvr(self):
        frage = self.quiz[1323]  # P1324
        tage = 8e12 / (6 * 4e6 / 8 * 86400)
        self.assertEqual(int(tage), 30)
        self.assertEqual(int(8 * 2**40 / (6 * 4e6 / 8 * 86400)), 33)
        self.assertTrue(frage["q"].endswith("Wie viele volle Tage lassen sich speichern "
                                            "(1 TB = 10^12 Byte)?"))
        self.assertTrue(frage["exp"].startswith("Gerechnet wird dezimal (1 TB = 10^12 Byte = "
                                                "1.000 GB). "))

    def test_b_c_29_ap(self):
        frage = self.quiz[1495]  # P1496
        self.assertEqual(int(867 * 0.45 / 12), 32)
        self.assertIn("soll 1,5 MB/s (1 MB = 10^6 Byte) bekommen.", frage["q"])
        self.assertIn("1,5 MB/s * 8 = 12 Mbit/s (dezimal, 1 MB = 10^6 Byte).", frage["exp"])

    def test_b_c_30_budget(self):
        frage = self.quiz[1933]  # P1934
        self.assertAlmostEqual(180000 / 1.04 ** 3, 160019.34, places=2)
        self.assertIn("Wie viel ist das Budget nach drei Jahren in heutigen Preisen", frage["q"])
        self.assertNotIn("im dritten Jahr", frage["q"])
        self.assertTrue(frage["exp"].startswith(
            "Gemeint ist der Wert nach drei Jahren, also nach drei Preissteigerungen."))
        self.assertIn("160.019,34 Euro", frage["a"] + frage["exp"])

    def test_b_c_31_hash(self):
        text = self.quiz[28]["exp"]  # P0029
        self.assertNotIn("eindeutigen Prüfwert", text)
        self.assertIn("einen charakteristischen Prüfwert", text)
        self.assertIn("(Kollision)", text)

    def test_b_c_32_shadow(self):
        frage = self.quiz[628]  # P0629
        # ab N12 (B-N-08): "z. B." statt "z.B."
        neu = "Nur root (und ggf. die Gruppe shadow) darf sie lesen, z. B. 640 root:shadow oder 000"
        self.assertEqual((frage["a"], frage["options"][0]), (neu, neu))

    def test_b_c_33_itil(self):
        frage = self.quiz[71]  # P0072
        self.assertEqual(frage["q"], "Welche Phase gehört zum ITIL-Service-Lebenszyklus (ITIL v3/2011)?")
        self.assertIn("Phasen des Service-Lebenszyklus nach ITIL v3/2011", frage["exp"])
        self.assertIn("ITIL 4 (seit 2019) ersetzt den Lebenszyklus durch das Service Value System.",
                      frage["exp"])

    def test_b_c_34_ruhezeit_sonntag(self):
        szenario = self.ap1[58]  # A1-059
        # Auflage Freigabe Abschnitt 5: der Folgetag ist wirklich ein Sonntag
        self.assertIn("an einem Samstag von 8:00 bis 20:00 Uhr", szenario["text"][0])
        samstag = datetime.datetime(2026, 10, 10, 20, 0)
        self.assertEqual(samstag.weekday(), 5)
        frueh = samstag + datetime.timedelta(hours=11)
        self.assertEqual((frueh.weekday(), frueh.hour, frueh.minute), (6, 7, 0))   # So 7:00
        loesung = szenario["solution"][4]
        self.assertIn("mindestens 11 Stunden (§ 5 ArbZG)", loesung)
        self.assertIn("frühestens am nächsten Tag um 7:00 Uhr. Der nächste Tag ist aber ein Sonntag.",
                      loesung)
        self.assertIn("(§ 9 ArbZG), außer eine Ausnahme nach § 10 ArbZG greift.", loesung)
        self.assertTrue(loesung.endswith("Sonst darf er regulär erst am Montag wieder arbeiten."))

    def test_b_c_35_bindefrist(self):
        text = self.ap1[91]["text"][0]  # A1-092
        self.assertIn("mit dem Liefertermin 21.09.2026, gültig bis 15.09.2026.", text)
        angebot, frist, bestellung = (datetime.date(2026, 8, 25), datetime.date(2026, 9, 15),
                                      datetime.date(2026, 9, 1))
        self.assertTrue(angebot <= bestellung <= frist)

    def test_b_c_36_bdsg(self):
        # Wortlaut Freigabe Plan 0.63.2, Abschnitt 5
        loesung = self.ap1[143]["solution"][0]  # A1-144
        self.assertIn(
            "(Art. 6 Abs. 1 lit. b DSGVO; § 26 Abs. 1 Satz 1 BDSG ist nach dem Urteil des EuGH "
            "vom 30.03.2023 (C-34/21) zur gleichlautenden hessischen Regelung in vielen Fällen "
            "nicht anwendbar)", loesung)
        self.assertNotIn("in Verbindung mit § 26 BDSG", loesung)
        self.assertNotIn("nur eingeschränkt anwendbar", loesung)

    def test_b_c_37_air_gap(self):
        loesung = self.ap1[4]["solution"][2]  # A1-005
        self.assertNotIn("(Prinzip des Air Gap)", loesung)
        self.assertIn("(räumlich getrennte Kopie, Schutz vor lokalen Schäden)", loesung)
        self.assertIn("Davon zu unterscheiden ist ein Air Gap", loesung)

    def test_b_c_38_nis2(self):
        szenario = self.ap2[134]  # A2-135
        kenntnis = datetime.datetime(2026, 10, 2, 22, 40)
        erste, bewertung = datetime.datetime(2026, 10, 3, 11, 0), datetime.datetime(2026, 10, 5, 15, 0)
        self.assertEqual((kenntnis.weekday(), erste.weekday(), bewertung.weekday()), (4, 5, 0))
        self.assertLessEqual(erste, kenntnis + datetime.timedelta(hours=24))
        self.assertLessEqual(bewertung, kenntnis + datetime.timedelta(hours=72))
        self.assertIn("Die erste Meldung wurde am Samstag, 03.10.2026, um 11:00 Uhr abgegeben, die "
                      "Meldung mit erster Bewertung am Montag, 05.10.2026, um 15:00 Uhr.",
                      szenario["text"][0])
        self.assertNotIn("Die Meldung wird am Montag", szenario["text"][0])
        self.assertIn("Die erste Meldung um 11:00 Uhr ist rechtzeitig.", szenario["solution"][0])

    def test_b_c_39_zweite_adresse(self):
        text = self.ap2[223]["text"][0]  # A2-224
        self.assertIn("Unter einer zweiten Adresse (10.30.6.41) nimmt derselbe Sicherungsspeicher "
                      "über dasselbe Bündel auch die Daten des Redaktionssystems an.", text)

    def test_b_d_13_modewelt(self):
        text = self.projekte[0]["ausgangssituation"]  # T001
        self.assertIn("„ModeWelt GmbH“", text)
        self.assertNotIn('"ModeWelt', text)

    def test_b_d_13_programmtexte(self):
        pc, handy = literale("app_gui.py"), literale(os.path.join("mobile", "src", "main.py"))
        notiz = ("Nichts zu üben – sehr gut! Falsch beantwortete Fragen landen "
                 "automatisch hier.")
        for texte in (pc, handy):
            self.assertTrue(notiz in texte, notiz)            # PC = Handy
            self.assertFalse(enthalten("Nichts zu üben - ", texte))
        self.assertTrue(enthalten("Windows, Linux und macOS bringen alles Nötige mit – es muss "
                                  "nichts zusätzlich installiert werden.", pc))
        self.assertFalse(enthalten("alles Nötige mit - ", pc))
        self.assertTrue("Suchen … (z. B. RAID, DNS, DSGVO)" in handy, "Handy-Suche")
        self.assertFalse(enthalten("Suchen ... (z.B.", handy))

    def test_z8_statustexte(self):
        pc, handy = literale("app_gui.py"), literale(os.path.join("mobile", "src", "main.py"))
        for neu in ("Gleiche ab …", "Suche nach Updates …", "Update wird heruntergeladen …",
                    "Update wird installiert …"):
            self.assertTrue(neu in pc, neu)
            self.assertFalse(neu.replace("…", "...") in pc, neu)
        for neu in ("Gleiche ab …", "Suche nach Updates …"):
            self.assertTrue(neu in handy, neu)
            self.assertFalse(neu.replace("…", "...") in handy, neu)

    def test_b_n_13_verneinung_gross(self):
        fragen = {("karten", 120): "NICHT", ("karten", 740): "NICHT", ("karten", 1429): "NICHT",
                  ("quiz", 158): "NICHT", ("quiz", 931): "NICHT", ("quiz", 1024): "KEIN",
                  ("quiz", 2102): "NICHT"}
        for (liste, index), wort in fragen.items():
            frage = getattr(self, liste)[index]["q"]
            letzter = frage.rsplit(". ", 1)[-1]
            woerter = re.findall(r"\w+", letzter)
            self.assertIn(wort, woerter, (liste, index))
            self.assertNotIn(wort.lower(), woerter, (liste, index))


# ============================================================================
#  Bestand
# ============================================================================

ANZAHL = {"karteikarten.json": 1565, "quizfragen.json": 2120, "szenarien_ap1.json": 265,
          "szenarien_ap2.json": 330, "projektarbeiten.json": 50}
# Geaenderte Felder 0.63.2 (= test_inhalte_0631.GEPLANT_0632)
FELDER = {
    "karteikarten.json": [(58, ("a",)), (58, ("a_full",)), (58, ("options", 0)), (120, ("q",)),
                          (159, ("a_full",)), (301, ("a",)), (301, ("a_full",)),
                          (301, ("options", 0)), (740, ("q",)), (858, ("a_full",)),
                          (859, ("a_full",)), (882, ("a_full",)), (882, ("options", 1)),
                          (1295, ("a",)), (1295, ("a_full",)), (1295, ("options", 0)),
                          (1429, ("q",))],
    "projektarbeiten.json": [(0, ("aufgaben", 4)), (0, ("ausgangssituation",)),
                             (9, ("hinweise", 0)), (21, ("aufgaben", 3)), (21, ("hinweise", 3)),
                             (27, ("hinweise", 4)), (37, ("hinweise", 3)),
                             (44, ("rahmenbedingungen", 4)), (47, ("aufgaben", 2))],
    "quizfragen.json": [(28, ("exp",)), (71, ("exp",)), (71, ("q",)), (158, ("q",)),
                        (628, ("a",)), (628, ("options", 0)), (777, ("exp",)), (828, ("exp",)),
                        (828, ("q",)), (931, ("q",)), (1024, ("q",)), (1323, ("exp",)),
                        (1323, ("q",)), (1479, ("exp",)), (1479, ("options", 3)),
                        (1495, ("exp",)), (1495, ("q",)), (1933, ("exp",)), (1933, ("q",)),
                        (2102, ("q",))],
    "szenarien_ap1.json": [(4, ("solution", 2)), (58, ("solution", 4)), (91, ("text", 0)),
                           (143, ("solution", 0)), (207, ("text", 2)), (207, ("text", 3)),
                           (207, ("text", 4)), (207, ("text", 5))],
    "szenarien_ap2.json": [(0, ("solution", 0)), (0, ("solution", 6)), (23, ("text", 1)),
                           (23, ("text", 2)), (23, ("text", 3)), (25, ("solution", 2)),
                           (25, ("solution", 3)), (46, ("text", 1)), (46, ("text", 2)),
                           (46, ("text", 3)), (46, ("text", 4)), (134, ("solution", 0)),
                           (134, ("text", 0)), (218, ("text", 10)), (218, ("text", 11)),
                           (218, ("text", 12)), (223, ("text", 0)), (228, ("text", 1)),
                           (228, ("text", 2)), (228, ("text", 3)), (228, ("text", 4)),
                           (228, ("text", 5)), (296, ("text", 2)), (296, ("text", 3)),
                           (296, ("text", 4)), (296, ("text", 5))],
}
# SHA-256 ueber den Wortlaut aller 80 Felder (Stand 0.63.1: 7c4483f2...cf19)
# Ab N12 (B-N-08/N-d, FG-60): 7 dieser Felder enthielten "z.B." und haben jetzt
# "z. B." (K0302, K0859, T010, P0029, P0629 a/options, A1-005). Wert bis S4
# (c582094/29558a8): 6a778451...36ab; genau diesen Wert ergibt der neue Wortlaut,
# wenn man "z. B." wieder zu "z.B." macht (test_inhalte_zb.test_s4_felder_nur_zb).
PRUEFWERT_FELDER = "ba35e8e89f6330cef4f1b9a3a641ef172fe9594ef59a7d4edc79077507114da9"
# SHA-256 ueber die Stelle der richtigen Antwort aller Karten bzw. Fragen (= 0.63.1)
ANTWORTSTELLEN = {
    "karteikarten.json": "3302b4c437a357738619fc6dec0abb0e00bcf7951d7dd9e8ffb37ae3e6aeb1ba",
    "quizfragen.json": "8a0493ee39ed14189b0c045009c685aa19689cfe690cd92c6de301a4020039c9",
}
# Rahmenplan-Punkte der geaenderten Karten/Fragen (= 0.63.1, gemessen mit
# fisi_rahmenplan.item_points auf 14b3bd4)
RAHMENPLAN = {
    ("karte", 58): ["A1a", "A1g", "B1a"], ("karte", 120): ["A8a", "C2b"],
    ("karte", 159): ["C2c"], ("karte", 301): ["A1b"], ("karte", 740): ["A1b"],
    ("karte", 858): ["A6a"], ("karte", 859): ["D4d"], ("karte", 882): ["C1a", "C1b"],
    ("karte", 1295): ["A6c", "A6e", "A8d", "B2a", "C3d", "E3h"], ("karte", 1429): ["A4b"],
    ("quiz", 28): ["A6b", "D4d"], ("quiz", 71): ["C3i"], ("quiz", 158): ["A8b", "C2a"],
    ("quiz", 628): ["A9a", "C3c"], ("quiz", 777): ["A9a", "C3c"], ("quiz", 828): ["A9b"],
    ("quiz", 931): ["C2b"], ("quiz", 1024): ["A1b"], ("quiz", 1323): ["A3a"],
    ("quiz", 1479): ["C2b"], ("quiz", 1495): ["C2b"], ("quiz", 1933): ["F1c"],
    ("quiz", 2102): ["F5a"],
}


def enthalten(teil, texte):
    return any(teil in text for text in texte)


def feldwert(eintrag, pfad):
    for teil in pfad:
        eintrag = eintrag[teil]
    return eintrag


class BestandTest(unittest.TestCase):

    def test_anzahl(self):
        for datei, anzahl in ANZAHL.items():
            self.assertEqual(len(lade(datei)), anzahl, datei)

    def test_genau_eine_option_ist_antwort(self):
        for datei in ("karteikarten.json", "quizfragen.json"):
            falsch = [index for index, eintrag in enumerate(lade(datei))
                      if sum(option == eintrag["a"] for option in eintrag["options"]) != 1]
            self.assertEqual(falsch, [], datei)

    def test_richtige_antwort_an_gleicher_stelle(self):
        for datei, soll in ANTWORTSTELLEN.items():
            stellen = [eintrag["options"].index(eintrag["a"]) for eintrag in lade(datei)]
            self.assertEqual(hashlib.sha256(json.dumps(stellen).encode()).hexdigest(), soll, datei)

    def test_wortlaut_aller_felder(self):
        werte = []
        for datei, felder in sorted(FELDER.items()):
            eintraege = lade(datei)
            werte += [[datei, index, list(pfad), feldwert(eintraege[index], pfad)]
                      for index, pfad in sorted(felder)]
        self.assertEqual(len(werte), 80)
        text = json.dumps(werte, ensure_ascii=False, sort_keys=True)
        self.assertEqual(hashlib.sha256(text.encode("utf-8")).hexdigest(), PRUEFWERT_FELDER)

    def test_felder_wie_in_test_inhalte_0631(self):
        import test_inhalte_0631 as alt
        for datei, felder in FELDER.items():
            soll = sorted((index, pfad) for index, pfade in alt.GEPLANT_0632[datei].items()
                          for pfad in pfade)
            self.assertEqual(sorted(felder), soll, datei)

    def test_rahmenplan_unveraendert(self):
        import fisi_rahmenplan as frp
        punkte = frp.item_points()
        listen = {"karte": lade("karteikarten.json"), "quiz": lade("quizfragen.json")}
        for (quelle, index), soll in RAHMENPLAN.items():
            self.assertEqual(sorted(punkte[(quelle, listen[quelle][index]["q"])]), soll,
                             (quelle, index))


# ============================================================================
#  Umbenennungen (F7 d)
# ============================================================================

# (Art, Index, alter Fragetext); der neue ist der heutige Fragetext
UMBENANNT = [
    ("karte", 120, "Welche Domäne trennt ein Router, ein einfacher Switch aber nicht?"),
    ("karte", 740, "Welches Geschäft darf ein Prokurist ohne besondere Befugnis nicht abschließen?"),
    ("karte", 1429, "In der Klasse Konto ist das Attribut saldo öffentlich. Ein Kollege setzt es "
                    "an einer Stelle im Programm einfach auf einen negativen Wert. Welches "
                    "OOP-Prinzip wurde nicht umgesetzt?"),
    ("quiz", 71, "Welche Phase gehört zum ITIL-Service-Lebenszyklus?"),
    ("quiz", 158, "Welche Information steht im Ethernet-Frame, aber nicht im IP-Paket?"),
    ("quiz", 828, "Welches Protokoll nutzt NFS standardmäßig?"),
    ("quiz", 931, "Welcher Verkabelungsfehler wird von einem einfachen Durchgangsprüfer "
                  "(Wiremap) nicht erkannt?"),
    ("quiz", 1024, "Bei welchem Onlinekauf hat ein Verbraucher kein Widerrufsrecht?"),
    ("quiz", 1323, "Ein Videorekorder (NVR) hat 8 TB nutzbaren Speicher. 6 Kameras zeichnen "
                   "dauerhaft mit je 4 Mbit/s auf. Wie viele volle Tage lassen sich speichern?"),
    ("quiz", 1495, "Ein Access Point zeigt 867 Mbit/s Datenrate, netto kommen etwa 45 % an. "
                   "Jeder Laptop im Seminarraum soll 1,5 MB/s bekommen. Wie viele Laptops kann "
                   "der AP damit höchstens gleichzeitig versorgen?"),
    ("quiz", 1933, "Das IT-Budget bleibt 3 Jahre lang bei 180.000,00 Euro. Die Preise für "
                   "IT-Dienstleistungen steigen angenommen um 4 % pro Jahr. Wie viel ist das "
                   "Budget im dritten Jahr in heutigen Preisen noch wert?"),
    ("quiz", 2102, "Welches der folgenden Merkmale ist durch das Allgemeine "
                   "Gleichbehandlungsgesetz (AGG) nicht geschützt?"),
]
# Schutzbereich test_rahmenplan.STAND_054: Karten 1-1.400, Quizfragen 1-1.946
SCHUTZ = {"karte": 1400, "quiz": 1946}


def neue_texte():
    listen = {"karte": lade("karteikarten.json"), "quiz": lade("quizfragen.json")}
    return [(art, alt, listen[art][index]["q"]) for art, index, alt in UMBENANNT]


class UmbenennungenTest(unittest.TestCase):

    def test_genau_die_geplanten_neu(self):
        import test_inhalte_0631 as alt
        daten = lade("umbenennungen.json")
        for art in ("karte", "quiz"):
            neu = {k: v for k, v in daten[art].items() if k in alt.UMBENENNUNGEN_0632[art]}
            soll = {a: n for x, a, n in neue_texte() if x == art}
            self.assertEqual(neu, soll, art)
        self.assertEqual(sum(len(v) for v in alt.UMBENENNUNGEN_0632.values()), 12)

    def test_f7_d_zehn_im_schutzbereich(self):
        im_schutz = [(art, index) for art, index, _alt in UMBENANNT if index < SCHUTZ[art]]
        self.assertEqual(len(im_schutz), 10)
        self.assertNotIn(("quiz", 1479), im_schutz)       # B-C-06 nach A14 ohne Fragetext

    def test_alt_weg_neu_da(self):
        alle = {"karte": {e["q"] for e in lade("karteikarten.json")},
                "quiz": {e["q"] for e in lade("quizfragen.json")}}
        for art, alt, neu in neue_texte():
            self.assertNotIn(alt, alle[art])
            self.assertIn(neu, alle[art])
            self.assertNotEqual(alt, neu)

    def test_kern_kennt_die_umbenennungen(self):
        import fisi_core as core
        for art, alt, neu in neue_texte():
            tabelle = "card_events" if art == "karte" else "quiz_answers"
            self.assertEqual(core.QUESTION_RENAMES[tabelle].get(alt), neu)


# ============================================================================
#  Lernstand-Migration (Plan 8.1 Nr. 3)
# ============================================================================

_STAENDE = {}


def code_stand(tag):
    """Ordner mit dem Code aus einem Tag (git archive), oder None (wie test_abgleich)."""
    if tag in _STAENDE:
        return _STAENDE[tag]
    ziel = os.path.join(_TMP, "stand_" + tag)

    def archiv():
        proc = subprocess.run(["git", "-C", HERE, "archive", "--format=tar", tag],
                              capture_output=True)
        if proc.returncode:
            return False
        os.makedirs(ziel, exist_ok=True)
        pfad = ziel + ".tar"
        with open(pfad, "wb") as handle:
            handle.write(proc.stdout)
        with tarfile.open(pfad) as tar:
            try:
                tar.extractall(ziel, filter="data")
            except TypeError:
                tar.extractall(ziel)
        os.remove(pfad)
        return True

    ok = archiv()
    if not ok:
        subprocess.run(["git", "-C", HERE, "fetch", "--depth=1", "--no-tags", "origin",
                        "+refs/tags/%s:refs/tags/%s" % (tag, tag)], capture_output=True,
                       timeout=120)
        ok = archiv()
    _STAENDE[tag] = ziel if ok else None
    return _STAENDE[tag]


SKRIPT = r'''
import json, sys
code, aufgabe, daten = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
sys.path.insert(0, code)
import fisi_core as core
db = core.DBManager()
out = {"datei": core.__file__}
if aufgabe == "anlegen":
    for nummer, (kat, frage) in enumerate(daten["karte"]):
        db.log_card(kat, frage, "lernen", None)
        db.log_card(kat, frage, "lernen", False)
        db.log_card(kat, frage, "lernen", nummer % 2 == 0)
    for nummer, (kat, frage) in enumerate(daten["quiz"]):
        db.log_quiz_answer(kat, frage, False)
        db.log_quiz_answer(kat, frage, True)
        if nummer % 3 == 0:
            db.log_quiz_answer(kat, frage, True)
    for kat, frage in daten["andere_karte"]:
        db.log_card(kat, frage, "lernen", True)
    for kat, frage in daten["anderes_quiz"]:
        db.log_quiz_answer(kat, frage, True)
    s = core.SZENARIEN[0]
    db.log_scenario(0, s["title"], s["theme"], True)
    a = core.AP1_SZENARIEN[0]
    db.log_ap1(0, a["title"], a["theme"], False)
    db.log_project(0, "Projekt", "netzwerk", True)
    db.log_trainer("subnetz", 1, True)
    db.save_test_result(8, 10, 80.0, "2", 120)
    db.save_exam("wiso", 55.5, "4", 3600, {"fragen": [f for _k, f in daten["quiz"]]})
    db.save_project_field("Eigenes Projekt", "titel", "Netzwerk der Filiale")
if aufgabe == "export":
    import fisi_sync
    out["export"] = fisi_sync.export_local(db)
if aufgabe == "merge":
    import fisi_sync
    fisi_sync.merge_into_local(db, daten)
if aufgabe == "pruefung_anlegen":
    import fisi_pruefung as fp
    state = fp.new_exam(daten["art"], seed=1)
    if daten["art"] == fp.WISO:
        nach_text = {q["q"]: q for q in core.QUIZ_QUESTIONS}
        vorne = daten["fragen"]
        state["fragen"] = vorne + [q for q in state["fragen"] if q not in vorne][:len(state["fragen"]) - len(vorne)]
        state["optionen"] = {q: list(reversed(nach_text[q]["options"])) for q in state["fragen"]}
        state["antworten"] = {q: nach_text[q]["a"] for q in state["fragen"]}
        # ab N12 (Test (4) B-N-08): bei diesen Fragen eine falsche Antwort waehlen
        for q in daten.get("falsch", []):
            state["antworten"][q] = [o for o in nach_text[q]["options"] if o != nach_text[q]["a"]][0]
    else:
        state["aufgaben"] = daten["aufgaben"]
        for nummer in range(len(state["aufgaben"])):
            for teil, part in enumerate(fp.task_details(state, nummer)["teile"]):
                key = fp.answer_key(nummer, teil)
                state["antworten"][key] = "Antwort %s" % key
                anzahl = len(part["kriterien"])
                if daten.get("haken") == "wechsel":     # 1., 3., 5. ... abgehakt
                    state["kriterien"][key] = [i % 2 == 0 for i in range(anzahl)]
                else:
                    state["kriterien"][key] = [True] * anzahl
                state["punkte"][key] = part["punkte"]
        fp.submit(state)
    fp.save_running(state)
    out["state"] = state
if aufgabe == "pruefung_bewerten":
    # ab N12: Bewertung ohne Speichern (Vergleichswert mit dem alten Code)
    import fisi_pruefung as fp
    state = fp.submit(fp.load_running())
    out["bewertet"] = fp.evaluate(state)
    out["zeilen"] = fp.wiso_result(state)
if aufgabe == "pruefung_laden":
    import fisi_pruefung as fp
    out["geladen"] = fp.load_running()
if aufgabe == "pruefung_abgeben":
    import fisi_pruefung as fp
    state = fp.load_running()
    out["geladen"] = json.loads(json.dumps(state))
    if state["art"] == fp.WISO:
        fp.submit(state)
    else:
        # wie die Oberflaeche (Haken je Kriterium, PC app_gui.py/Handy main.py "toggled")
        for nummer in range(len(state["aufgaben"])):
            for teil, part in enumerate(fp.task_details(state, nummer)["teile"]):
                key = fp.answer_key(nummer, teil)
                marks = state["kriterien"].setdefault(key, [False] * len(part["kriterien"]))
                for index in range(len(part["kriterien"])):
                    marks[index] = True
                state["punkte"][key] = fp.suggested_points(part["punkte"], marks)
    out["ergebnis"] = fp.finish(db, state)
    out["laufend"] = fp.load_running()
if aufgabe in ("anlegen", "merge", "lesen", "pruefung_abgeben"):
    out["ergebnisse"] = sorted([q, k, [[t, v] for t, v in werte]]
                               for (q, k), werte in db.question_results().items())
    out["kennzahlen"] = [db.distinct_cards_learned(), db.distinct_quiz_questions(),
                         db.count_card_events(), db.count_quiz_answers(),
                         db.quiz_success_rate()]
    out["fachbereiche"] = db.category_stats()
    out["themen"] = db.topic_stats()
print("ERGEBNIS " + json.dumps(out, ensure_ascii=False))
'''


def lauf(code, datenbank, aufgabe, daten=None):
    env = dict(os.environ, FISI_DB_PATH=datenbank, HOME=_TMP, APPDATA=_TMP,
               FISI_SELFTEST=os.path.join(_TMP, "selbsttest_lauf.log"))
    proc = subprocess.run([sys.executable, "-c", SKRIPT, code, aufgabe,
                           json.dumps(daten or {}, ensure_ascii=False)],
                          cwd=_TMP, env=env, capture_output=True, timeout=600)
    zeilen = [z for z in proc.stdout.decode("utf-8").splitlines() if z.startswith("ERGEBNIS ")]
    if proc.returncode or not zeilen:
        raise AssertionError("Lauf %s mit %s: %s" % (aufgabe, code, proc.stderr.decode()[-2000:]))
    ergebnis = json.loads(zeilen[-1][len("ERGEBNIS "):])
    # Schutz: wirklich der Code aus dem gewuenschten Ordner (alt bzw. neu)
    if os.path.dirname(os.path.abspath(ergebnis["datei"])) != os.path.abspath(code):
        raise AssertionError("falscher Code: %s statt %s" % (ergebnis["datei"], code))
    return ergebnis


def sha(pfad):
    with open(pfad, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def zeilen(pfad):
    """Alle Tabellen der Datenbank, Zeile fuer Zeile (nach id)."""
    conn = sqlite3.connect(pfad)
    try:
        tabellen = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
        return {t: conn.execute("SELECT * FROM %s ORDER BY rowid" % t).fetchall()
                for t in tabellen}
    finally:
        conn.close()


class MigrationTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.alt = code_stand(ALT_TAG)
        if cls.alt is None:
            return
        cls.ordner = tempfile.mkdtemp(prefix="migration_", dir=_TMP)
        karten, quiz = lade("karteikarten.json"), lade("quizfragen.json")
        listen = {"karte": karten, "quiz": quiz}
        cls.paare = {"karte": {}, "quiz": {}}
        daten = {"karte": [], "quiz": [], "andere_karte": [[karten[0]["cat"], karten[0]["q"]]],
                 "anderes_quiz": [[quiz[0]["cat"], quiz[0]["q"]]]}
        for art, index, alt in UMBENANNT:
            eintrag = listen[art][index]
            daten[art].append([eintrag["cat"], alt])
            cls.paare[art][alt] = eintrag["q"]
        cls.daten = daten
        cls.db_alt = os.path.join(cls.ordner, "alt.db")
        cls.vorher = lauf(cls.alt, cls.db_alt, "anlegen", daten)
        cls.zeilen_vorher = zeilen(cls.db_alt)
        cls.db_neu = os.path.join(cls.ordner, "neu.db")
        shutil.copyfile(cls.db_alt, cls.db_neu)
        cls.nachher = lauf(HERE, cls.db_neu, "lesen")
        cls.zeilen_nachher = zeilen(cls.db_neu)

    def setUp(self):
        if self.alt is None:
            if IN_CI:
                self.fail("Code aus %s nicht verfuegbar" % ALT_TAG)
            self.skipTest("Code aus %s nicht verfuegbar (git archive)" % ALT_TAG)

    def umbenannt(self, tabelle, frage):
        art = "karte" if tabelle == "card_events" else "quiz"
        return self.paare[art].get(frage, frage)

    def test_genau_die_fragetexte_geaendert(self):
        vorher, nachher = self.zeilen_vorher, self.zeilen_nachher
        self.assertEqual(sorted(vorher), sorted(nachher))
        geaendert = 0
        for tabelle, alte in vorher.items():
            neue = nachher[tabelle]
            self.assertEqual(len(alte), len(neue), tabelle)
            if tabelle not in ("card_events", "quiz_answers"):
                self.assertEqual(alte, neue, tabelle)
                continue
            spalte = 3  # id, timestamp, category, question, ...
            for alt, neu in zip(alte, neue):
                soll = list(alt)
                soll[spalte] = self.umbenannt(tabelle, alt[spalte])
                self.assertEqual(list(neu), soll, tabelle)
                geaendert += alt[spalte] != neu[spalte]
        # 3 Karten je 3 Antworten, 9 Quizfragen je 2 bzw. 3 Antworten
        self.assertEqual(geaendert, 3 * 3 + 9 * 2 + 3)
        # Pruefungsverlauf (gespeicherte Fragen der Klausur) bleibt wie er war
        self.assertEqual(vorher["pruefungen"], nachher["pruefungen"])

    def test_lernstand_je_frage_vollstaendig(self):
        alt = {(q, k): v for q, k, v in self.vorher["ergebnisse"]}
        neu = {(q, k): v for q, k, v in self.nachher["ergebnisse"]}
        self.assertEqual(len(alt), len(neu))
        for art, paare in self.paare.items():
            for frage_alt, frage_neu in paare.items():
                self.assertIn((art, frage_alt), alt)
                self.assertNotIn((art, frage_alt), neu)
                self.assertEqual(neu[(art, frage_neu)], alt[(art, frage_alt)], frage_neu)
        rest_alt = {k: v for k, v in alt.items() if k[1] not in self.paare.get(k[0], {})}
        rest_neu = {k: v for k, v in neu.items()
                    if k[1] not in set(self.paare.get(k[0], {}).values())}
        self.assertEqual(rest_alt, rest_neu)
        self.assertEqual(self.vorher["kennzahlen"], self.nachher["kennzahlen"])
        self.assertEqual(self.vorher["fachbereiche"], self.nachher["fachbereiche"])
        self.assertEqual(self.vorher["themen"], self.nachher["themen"])

    def test_zweites_oeffnen_byte_gleich(self):
        kopie = os.path.join(self.ordner, "zweimal.db")
        shutil.copyfile(self.db_neu, kopie)
        vorher = sha(kopie)
        lauf(HERE, kopie, "oeffnen")
        self.assertEqual(sha(kopie), vorher)

    def test_ohne_umbenannte_antworten_byte_gleich(self):
        datenbank = os.path.join(self.ordner, "ohne.db")
        daten = dict(self.daten, karte=[], quiz=[])
        lauf(self.alt, datenbank, "anlegen", daten)
        vorher, groesse = sha(datenbank), os.path.getsize(datenbank)
        lauf(HERE, datenbank, "lesen")
        self.assertEqual((sha(datenbank), os.path.getsize(datenbank)), (vorher, groesse))
        self.assertFalse(os.path.exists(datenbank + "-journal"))
        self.assertFalse(os.path.exists(datenbank + "-wal"))

    def test_abgleich_von_altem_geraet(self):
        """Antworten eines Geraets mit v0.63.1 (alte Fragetexte) zaehlen nach dem
        Abgleich beim neuen Text, Kennung (uid) bleibt."""
        export = lauf(self.alt, self.db_alt, "export")["export"]
        datenbank = os.path.join(self.ordner, "abgleich.db")
        ergebnis = lauf(HERE, datenbank, "merge", export)
        neu = {(q, k): v for q, k, v in ergebnis["ergebnisse"]}
        for art, paare in self.paare.items():
            for frage_alt, frage_neu in paare.items():
                self.assertNotIn((art, frage_alt), neu)
                self.assertIn((art, frage_neu), neu)
        uids_alt = {t: sorted(r[0] for r in export["tables"][t])
                    for t in ("card_events", "quiz_answers")}
        conn = sqlite3.connect(datenbank)
        try:
            for tabelle, uids in uids_alt.items():
                self.assertEqual(sorted(r[0] for r in conn.execute(
                    "SELECT uid FROM %s" % tabelle)), uids)
        finally:
            conn.close()
        self.assertEqual(ergebnis["kennzahlen"], self.vorher["kennzahlen"])


# ============================================================================
#  Laufende Pruefung ueber das Update (Nacharbeit S4)
# ============================================================================

class LaufendePruefungTest(unittest.TestCase):
    """Eine Pruefung, die beim Update auf 0.63.2 laeuft, liegt mit Frage- und
    Antworttexten (WiSo) bzw. Kriterien-Haken (AP1/AP2) in einstellungen.json.
    Angelegt mit dem Code v0.63.1, fortgesetzt und abgegeben mit diesem Stand:
    nichts darf abbrechen oder verloren gehen."""

    @classmethod
    def setUpClass(cls):
        cls.alt = code_stand(ALT_TAG)

    def setUp(self):
        if self.alt is None:
            if IN_CI:
                self.fail("Code aus %s nicht verfuegbar" % ALT_TAG)
            self.skipTest("Code aus %s nicht verfuegbar (git archive)" % ALT_TAG)
        self.ordner = tempfile.mkdtemp(prefix="laufend_", dir=_TMP)
        self.db = os.path.join(self.ordner, "lernstand.db")

    def test_wiso_mit_alten_fragetexten(self):
        alte = {alt: neu for _art, alt, neu in neue_texte() if _art == "quiz"}
        wiso = [UMBENANNT[i][2] for i in range(len(UMBENANNT))
                if UMBENANNT[i][0] == "quiz" and UMBENANNT[i][1] in (1024, 1933, 2102)]
        self.assertEqual(len(wiso), 3)
        angelegt = lauf(self.alt, self.db, "pruefung_anlegen", {"art": "wiso", "fragen": wiso})
        self.assertEqual(angelegt["state"]["fragen"][:3], wiso)
        ergebnis = lauf(HERE, self.db, "pruefung_abgeben")
        geladen = ergebnis["geladen"]
        neu = [alte[q] for q in wiso]
        self.assertEqual(geladen["fragen"][:3], neu)
        self.assertEqual(len(geladen["fragen"]), len(angelegt["state"]["fragen"]))
        for alt, frage in zip(wiso, neu):
            self.assertEqual(geladen["antworten"][frage], angelegt["state"]["antworten"][alt])
            self.assertEqual(geladen["optionen"][frage], angelegt["state"]["optionen"][alt])
            self.assertNotIn(alt, geladen["antworten"])
        # alle Antworten waren richtig -> 100 Punkte, gespeichert, nicht mehr laufend
        self.assertEqual(ergebnis["ergebnis"]["punkte"], 100.0)
        self.assertIsNone(ergebnis["laufend"])
        antworten = {(q, k): v for q, k, v in ergebnis["ergebnisse"]}
        for frage in neu:
            self.assertEqual([w for _t, w in antworten[("quiz", frage)]], [True])
        for alt in wiso:
            self.assertNotIn(("quiz", alt), antworten)

    def test_wiso_zb_ueber_das_update(self):
        # N12, B-N-08 Test (4) (GP-S1): laufende WiSo-Pruefung aus v0.63.1 mit den
        # zwei Fragen, die "z.B." beruehrt: Fernabsatz (nur Fragetext) und
        # Werkvertrag (richtige Antwort = Option 0 geaendert). Gleiche Punkte wie
        # dieselbe Pruefung ohne Umbenennung (alter Code, alter Inhalt), je Frage
        # genau eine Antwort unter dem neuen Text, richtig bleibt richtig,
        # falsch bleibt falsch.
        quiz = lade("quizfragen.json")
        fern_neu, werk = quiz[346]["q"], quiz[150]["q"]
        fern_alt = fern_neu.replace("z. B.", "z.B.")
        werk_a_neu = quiz[150]["a"]
        werk_a_alt = werk_a_neu.replace("z. B.", "z.B.")
        self.assertNotEqual(fern_alt, fern_neu)
        self.assertNotEqual(werk_a_alt, werk_a_neu)
        self.assertEqual(quiz[150]["options"][0], werk_a_neu)
        for falsch, punkte in (([], 100.0), ([fern_alt, werk], round(100.0 * 28 / 30, 1))):
            with self.subTest(falsch=bool(falsch)):
                angelegt = lauf(self.alt, self.db, "pruefung_anlegen",
                                {"art": "wiso", "fragen": [fern_alt, werk], "falsch": falsch})
                alt_state = angelegt["state"]
                self.assertEqual(alt_state["fragen"][:2], [fern_alt, werk])
                self.assertIn(werk_a_alt, alt_state["optionen"][werk])
                if not falsch:
                    self.assertEqual(alt_state["antworten"][werk], werk_a_alt)
                soll = lauf(self.alt, self.db, "pruefung_bewerten")["bewertet"]["punkte"]
                self.assertEqual(soll, punkte)
                ergebnis = lauf(HERE, self.db, "pruefung_abgeben")
                geladen = ergebnis["geladen"]
                self.assertEqual(geladen["fragen"][:2], [fern_neu, werk])
                self.assertNotIn(fern_alt, geladen["antworten"])
                self.assertIn(werk_a_neu, geladen["optionen"][werk])
                self.assertNotIn(werk_a_alt, geladen["optionen"][werk])
                self.assertEqual(geladen["antworten"][werk],
                                 alt_state["antworten"][werk] if falsch else werk_a_neu)
                self.assertEqual(ergebnis["ergebnis"]["punkte"], soll)
                self.assertNotIn("unbekannt", ergebnis["ergebnis"]["daten"])
                self.assertIsNone(ergebnis["laufend"])
                antworten = {(q, k): v for q, k, v in ergebnis["ergebnisse"]}
                for frage in (fern_neu, werk):
                    self.assertEqual([w for _t, w in antworten[("quiz", frage)]], [not falsch],
                                     frage)
                self.assertNotIn(("quiz", fern_alt), antworten)
                os.remove(self.db)

    def test_aufgaben_mit_mehr_kriterien(self):
        # A1-005 (B-C-37) und A1-059 (B-C-34): Musterloesung hat jetzt mehr Kriterien
        aufgaben = [{"quelle": "ap1", "index": 4}, {"quelle": "ap1", "index": 58}]
        angelegt = lauf(self.alt, self.db, "pruefung_anlegen", {"art": "ap1", "aufgaben": aufgaben})
        alt_haken = angelegt["state"]["kriterien"]
        ergebnis = lauf(HERE, self.db, "pruefung_abgeben")
        geladen = ergebnis["geladen"]
        state = {"aufgaben": aufgaben}
        for nummer in range(2):
            for teil, part in enumerate(fp.task_details(state, nummer)["teile"]):
                key = fp.answer_key(nummer, teil)
                haken = geladen["kriterien"][key]
                self.assertEqual(len(haken), len(part["kriterien"]), key)
                self.assertEqual(haken[:len(alt_haken[key])], alt_haken[key], key)
        self.assertEqual(geladen["punkte"], angelegt["state"]["punkte"])
        self.assertEqual(geladen["antworten"], angelegt["state"]["antworten"])
        self.assertIsNone(ergebnis["laufend"])
        # alle Kriterien abgehakt -> volle Punkte beider Aufgaben (2 x 25)
        self.assertEqual(ergebnis["ergebnis"]["punkte"], 50.0)

    def test_netzwerke_mit_mehr_kriterien(self):
        # A2-135 (B-C-38): erste Teilaufgabe hat jetzt ein Kriterium mehr
        aufgaben = [{"quelle": "ap2", "index": 134}]
        angelegt = lauf(self.alt, self.db, "pruefung_anlegen",
                        {"art": "netzwerke", "aufgaben": aufgaben})
        ergebnis = lauf(HERE, self.db, "pruefung_abgeben")
        self.assertEqual(len(ergebnis["geladen"]["kriterien"]["0-0"]),
                         len(fp.task_details({"aufgaben": aufgaben}, 0)["teile"][0]["kriterien"]))
        self.assertEqual(ergebnis["geladen"]["punkte"], angelegt["state"]["punkte"])
        self.assertIsNone(ergebnis["laufend"])

    def test_haken_an_richtiger_stelle(self):
        # Nacharbeit 2 (M1): neue Kriterien stehen nicht immer hinten
        # (A2-135: an Stelle 3). Abgehakt sind in 0.63.1 das 1., 3., 5. ...
        # Kriterium; nach dem Update muss jeder Haken beim selben Kriterium
        # stehen und jedes neue Kriterium "nicht abgehakt" sein.
        faelle = [("ap1", [{"quelle": "ap1", "index": 4}, {"quelle": "ap1", "index": 58}],
                   {"0-2": [True, False], "1-2": [True, False, False, False]}),
                  ("netzwerke", [{"quelle": "ap2", "index": 134}],
                   {"0-0": [True, False, False, True, False, True]})]
        for art, aufgaben, erwartet in faelle:
            with self.subTest(art=art):
                angelegt = lauf(self.alt, self.db, "pruefung_anlegen",
                                {"art": art, "aufgaben": aufgaben, "haken": "wechsel"})
                alt_haken = angelegt["state"]["kriterien"]
                geladen = lauf(HERE, self.db, "pruefung_laden")["geladen"]["kriterien"]
                state = {"aufgaben": aufgaben}
                for nummer in range(len(aufgaben)):
                    for teil, part in enumerate(fp.task_details(state, nummer)["teile"]):
                        key = fp.answer_key(nummer, teil)
                        if key in erwartet:
                            self.assertEqual(geladen[key], erwartet[key], key)
                            alt = fp.CRITERIA_BEFORE[(aufgaben[nummer]["quelle"],
                                                      aufgaben[nummer]["index"], teil)]
                            # unveraenderte Kriterien: Haken wie vorher
                            for i, text in enumerate(alt):
                                if text in part["kriterien"]:
                                    self.assertEqual(geladen[key][part["kriterien"].index(text)],
                                                     alt_haken[key][i], (key, text))
                        else:
                            self.assertEqual(geladen[key], alt_haken[key], key)
        self.assertEqual(fp.align_marks([True], ["a"], ["b", "c"]), [True, False])


class PruefungRobustTest(unittest.TestCase):
    """Zuordnung gespeicherter Texte ohne Umbenennungsliste (im Zweifel behalten)."""

    def setUp(self):
        self.quiz = [q for q in fp.QUIZ_QUESTIONS if q["q"] in set(fp.wiso_pool())]

    def state(self, fragen, optionen, antworten):
        return {"art": fp.WISO, "start": "2026-10-13 10:00:00", "start_utc": 0, "minuten": 60,
                "phase": "laeuft", "fragen": fragen, "optionen": optionen,
                "antworten": antworten, "punkte": {}, "kriterien": {}}

    def test_geaenderter_antworttext_wird_zugeordnet(self):
        frage = self.quiz[0]
        alt = frage["a"] + " (alte Fassung)"
        optionen = [alt if o == frage["a"] else o for o in frage["options"]]
        state = fp.migrate_running(self.state([frage["q"]], {frage["q"]: optionen},
                                              {frage["q"]: alt}))
        self.assertEqual(state["antworten"][frage["q"]], frage["a"])
        self.assertEqual(sorted(state["optionen"][frage["q"]]), sorted(frage["options"]))
        self.assertTrue(fp.wiso_result(state)[0][3])

    def test_unbekannte_frage_bleibt_und_bricht_nicht_ab(self):
        bekannt = self.quiz[1]
        fragen = ["Eine Frage, die es nicht mehr gibt?", bekannt["q"]]
        state = fp.migrate_running(self.state(
            fragen, {f: ["a", "b", "c", "d"] for f in fragen},
            {fragen[0]: "a", bekannt["q"]: bekannt["a"]}))
        self.assertEqual(state["fragen"], fragen)            # nichts verworfen
        zeilen = fp.wiso_result(state)
        self.assertEqual([z[3] for z in zeilen], [False, True])
        # Nacharbeit 2 (L2): die unbekannte Frage senkt die Punkte nicht
        # (bis c582094 hier 50.0, da sie im Nenner zaehlte)
        self.assertEqual(fp.evaluate(fp.submit(state))["punkte"], 100.0)

    def test_haken_wandert_nie_auf_fremdes_kriterium(self):
        # Nacharbeit 3 (L4): nie einen fremden Haken setzen
        # umgestellte Reihenfolge: difflib sieht "b" als neu eingefuegt und das
        # alte "b" als weggefallen; dessen Haken darf nicht auf "a" landen
        self.assertEqual(fp.align_marks([False, False, True], ["x", "a", "b"], ["x", "b", "a"]),
                         [False, False, False])
        # geloeschtes Kriterium: sein Haken faellt weg
        self.assertEqual(fp.align_marks([False, True], ["a", "b"], ["a"]), [False])
        self.assertEqual(fp.align_marks([False, True, False], ["a", "b", "c"], ["a", "c"]),
                         [False, False])
        # Ueberlauf (zwei alte Kriterien durch eines ersetzt): kein Haken aufs letzte
        self.assertEqual(fp.align_marks([False, False, True], ["a", "b", "c"], ["a", "z"]),
                         [False, False])
        # eigene Haken bleiben dabei erhalten
        self.assertEqual(fp.align_marks([True, True, False], ["x", "a", "b"], ["x", "b", "a"]),
                         [True, False, True])
        self.assertEqual(fp.align_marks([True, True], ["a", "b"], ["z"]), [True])

    def test_abgabe_mit_unbekannter_frage(self):
        # Nacharbeit 2 (L1/L2): finish schreibt fuer die unbekannte Frage nichts
        # in den Lernstand, sie zaehlt nicht in den Punkten, bleibt aber im
        # gespeicherten Ergebnis unter "unbekannt" sichtbar.
        import fisi_core as core
        bekannt = self.quiz[2]
        unbekannt = "Eine Frage, die es nicht mehr gibt?"
        fragen = [unbekannt, bekannt["q"]]
        state = fp.migrate_running(self.state(
            fragen, {f: ["a", "b", "c", "d"] for f in fragen},
            {unbekannt: "a", bekannt["q"]: bekannt["a"]}))
        pfad = os.path.join(tempfile.mkdtemp(prefix="abgabe_", dir=_TMP), "lernstand.db")
        db = core.DBManager(pfad)
        ergebnis = fp.finish(db, fp.submit(state))
        self.assertEqual(ergebnis["punkte"], 100.0)
        self.assertEqual(ergebnis["daten"]["richtig"], 1)
        self.assertEqual([f["q"] for f in ergebnis["daten"]["fragen"]], [bekannt["q"]])
        self.assertEqual(ergebnis["daten"]["unbekannt"], [unbekannt])
        conn = sqlite3.connect(pfad)
        try:
            zeilen = conn.execute("SELECT question, correct FROM quiz_answers").fetchall()
            gespeichert = conn.execute("SELECT punkte, daten FROM pruefungen").fetchall()
        finally:
            conn.close()
        self.assertEqual([z[0] for z in zeilen], [bekannt["q"]])
        self.assertEqual([bool(z[1]) for z in zeilen], [True])
        self.assertEqual(len(gespeichert), 1)
        self.assertEqual(gespeichert[0][0], 100.0)
        self.assertEqual(json.loads(gespeichert[0][1])["unbekannt"], [unbekannt])


if __name__ == "__main__":
    unittest.main(verbosity=2)
