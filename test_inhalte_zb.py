# -*- coding: utf-8 -*-
"""Tests ab 0.63.2, Bauauftrag N12: "z. B." in den Lerninhalten (B-N-08),
S4-Felder (N-d) und schon gestellte WiSo-Fragen (N-g).

  * B-N-08: in inhalte/*.json steht kein "z.B." mehr, sondern "z. B." (wie
    B-D-13/S4, normales Leerzeichen), und "Broadcast-Adresse" statt
    "Broadcastadresse". Bewusst NICHT geaendert: inhalte/spiel/ (F25 a,
    "_hinweis" in aufgaben_vorlagen.json).
  * Umbenennungen: die 27 Fragetexte mit "z.B." (28 Stellen: 14 Karten,
    13 Quizfragen) und die 2 Fragetexte P1487/P1488 mit "Broadcastadresse"
    (Nacharbeit Meldung 24, Frage 4 a) je mit Eintrag in
    inhalte/umbenennungen.json, nur angehaengt, keine Kette zu den
    Eintraegen von S4.
  * Bestand: Anzahl 1.565/2.120/265/330/50, Kriterienzahl jeder AP1/AP2-
    Teilaufgabe gleich (laufende AP1/AP2-Pruefungen nicht betroffen),
    Rahmenplan-Zuordnung gleich, Fragetexte im Schutzbereich STAND_054 nur
    um diese Umbenennungen geaendert.
  * Lernstand-Migration (Plan Nr. 38 Test (3)): Datenbank mit dem Code v0.63.1
    und Antworten zu allen 12 (S4) + 29 (N12) umbenannten Fragen: mit diesem
    Stand geoeffnet aendern sich genau diese Fragetexte, nichts sonst, keine
    Antwort geht verloren; ohne solche Antworten byte-gleich; Abgleich von
    einem Geraet mit v0.63.1.
  * N-g: used_items liest abgeschlossene WiSo-Pruefungen ueber den heutigen
    Fragetext (auch ueber Ketten), schreibt aber nichts um.
  Laufende WiSo-Pruefung ueber das Update (Test (4)): test_inhalte_0632.
  LaufendePruefungTest.test_wiso_zb_ueber_das_update.

Aufruf:  python test_inhalte_zb.py
"""
import hashlib
import itertools
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_TMP = tempfile.mkdtemp(prefix="fisi_inhalte_zb_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "inhalte.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(_TMP, "selbsttest.log"))
os.environ["HOME"] = _TMP
os.environ["APPDATA"] = _TMP

import fisi_pruefung as fp  # noqa: E402
import test_inhalte_0632 as s4  # noqa: E402  (Migration: lauf, code_stand, zeilen)

INHALTE = os.path.join(HERE, "inhalte")
ZB, ZB_NEU = "z.B.", "z. B."
BC, BC_NEU = "Broadcastadresse", "Broadcast-Adresse"
ZB_GROSS, ZB_GROSS_NEU = "Z.B.", "Z. B."          # FG-87


def lade(datei):
    with open(os.path.join(INHALTE, datei), encoding="utf-8") as handle:
        return json.load(handle)


def roh(datei):
    with open(os.path.join(INHALTE, datei), encoding="utf-8") as handle:
        return handle.read()


# (Art, Index, Fragetext bis 0.63.1 / S4); der neue ist der heutige Fragetext
UMBENANNT_ZB = [
    ("karte", 250, "Welches Cloud-Servicemodell ist z.B. ein webbasiertes Office-Paket?"),
    ("karte", 262, "Was ist Out-of-Band-Management bei Servern (z.B. iLO, iDRAC, IPMI)?"),
    ("karte", 268, "Was ist ein Mietvertrag im IT-Bereich, z.B. beim Leasing oder der Miete "
                   "von Hardware?"),
    ("karte", 390, "Was leistet das ACME-Protokoll, z.B. bei Let's Encrypt?"),
    ("karte", 475, "Was bedeutet Copyleft, z.B. bei der GPL?"),
    ("karte", 530, "Was leistet das Scannen von Container-Images, z.B. mit Trivy?"),
    ("karte", 543, "Was ist Conditional Access (bedingter Zugriff), z.B. in Microsoft Entra ID?"),
    ("karte", 593, "Wozu installiert man Gasterweiterungen (z.B. VMware Tools, "
                   "Integrationsdienste) in einer VM?"),
    ("karte", 607, "Was ist Objektspeicher (z.B. S3) in der Cloud?"),
    ("karte", 648, "Was ist der Unterschied zwischen Kategorie (z.B. Cat 6A) und Klasse "
                   "(z.B. EA) bei Kupferverkabelung?"),
    ("karte", 660, "Wie funktioniert ein passives optisches Netz (PON, z.B. GPON)?"),
    ("karte", 821, "Warum gilt Nachbarkanalstörung (z.B. APs auf 2,4-GHz-Kanal 1 und 3) als "
                   "schlimmer als Gleichkanalstörung (beide auf Kanal 1)?"),
    ("karte", 1366, "In der Tabelle mitarbeiter steht in der Spalte telefon z.B. \"0221 4711, "
                    "0171 123456\". Welche Normalform ist verletzt, und wie beheben Sie das?"),
    ("karte", 1388, "Wozu schreibt eine Datenbank jede Änderung zuerst in ein Transaktionslog "
                    "(z.B. WAL oder Redo-Log)?"),
    ("quiz", 66, "Was ist der Zweck eines Betriebssystem-Images (z.B. per Clonezilla) in der "
                 "Systemadministration?"),
    ("quiz", 99, "Welchen Port verwendet TFTP, z.B. beim Booten über das Netzwerk?"),
    ("quiz", 135, "Was ist ein Container-Image (z.B. bei Docker)?"),
    ("quiz", 346, "Wie lange kann ein Verbraucher einen Fernabsatzvertrag, z.B. einen "
                  "Onlinekauf, in der Regel widerrufen?"),
    ("quiz", 541, "Welchen UDP-Port nutzt Multicast-DNS (z.B. Bonjour) im lokalen Netz?"),
    ("quiz", 656, "Wie lautet die Wildcard-Maske (z.B. für ACLs oder OSPF) zum Präfix /27?"),
    ("quiz", 657, "Wie lautet die Wildcard-Maske (z.B. für ACLs oder OSPF) zum Präfix /22?"),
    ("quiz", 658, "Wie lautet die Wildcard-Maske (z.B. für ACLs oder OSPF) zum Präfix /19?"),
    ("quiz", 756, "Warum hält man die Versionen von Abhängigkeiten in einer Lockdatei "
                  "(z.B. package-lock.json) fest?"),
    ("quiz", 782, "Welcher Befehl zeigt die Meldungen des Kernels an, z.B. beim Einstecken "
                  "eines USB-Sticks?"),
    ("quiz", 838, "Welche Change-Art durchläuft die vollständige Bewertung und Freigabe, z.B. "
                  "durch das CAB?"),
    ("quiz", 984, "Wie lange muss ein Unternehmen per E-Mail empfangene Handelsbriefe, z.B. "
                  "eine Auftragsbestätigung ohne Rechnungsfunktion, aufbewahren?"),
    ("quiz", 1178, "Ein Onlineshop leitet Kunden zum Bezahlen an einen Zahlungsdienstleister "
                   "weiter. Dieser prüft die Zahlungsdaten auch nach eigenen gesetzlichen "
                   "Pflichten, z.B. zur Geldwäsche. Welche Rolle hat er?"),
]
# Fragetexte mit "Broadcastadresse", aber ohne "z.B." (P1487, P1488): ab der
# Nacharbeit zu Meldung 24 (Frage 4 a) ebenfalls umbenannt (je Index, alter Text)
UMBENANNT_BC = [
    ("quiz", 1486, "Sie dokumentieren das Netz eines Kunden. Ein Laptop hat die Adresse "
                   "172.16.9.155/27. Welche Netz- und Broadcastadresse tragen Sie ein?"),
    ("quiz", 1487, "Ein PC mit 10.44.7.201/26 soll per Wake-on-LAN geweckt werden. Das Tool "
                   "verlangt die Broadcastadresse seines Subnetzes. Welche tragen Sie ein?"),
]
UMBENANNT_N12 = UMBENANNT_ZB + UMBENANNT_BC
# Die zwei WiSo-Fragen, die B-N-08 beruehrt (Themen recht/arbeitswelt)
WISO_FERNABSATZ = 346      # nur der Fragetext
WISO_WERKVERTRAG = 150     # Antwort = Option 0 (dieselbe Option)

# Zahl je Datei nach N12 (vorher = S4-Stand 29558a8 in Klammern)
ANZAHL_TEXT = {
    # Datei: ("z. B.", "Broadcast-Adresse", "Broadcastadresse")
    "fachgespraech.json": (7, 0, 0),             # (0 + 7)
    "karteikarten.json": (433, 3, 0),            # (29 + 404)
    "projektarbeiten.json": (68, 0, 0),          # (23 + 45)
    "quizfragen.json": (211, 29, 0),             # (13 + 198), (19 + 10)
    "szenarien_ap1.json": (156, 9, 0),           # (1 + 155), (6 + 3)
    "szenarien_ap2.json": (201, 3, 0),           # (19 + 182), (1 + 2)
}
# Kriterienzahl je Teilaufgabe aller 595 AP1/AP2-Aufgaben. Bis 29ef1b0 (= S4
# 29558a8 = 0.63.1): 1065d53e...7dee2. Ab FG-87 ("Z.B." kein eigenes Kriterium
# mehr) genau drei Teilaufgaben mit einem Kriterium weniger (KRITERIEN_FG87);
# mit den alten Zahlen dieser drei ergibt sich wieder der alte Wert.
KRITERIEN_HASH_BIS_29EF1B0 = "1065d53e08a3c65ef4bc859ac473da0deb5235fae25030b36a1983309bc7dee2"
KRITERIEN_HASH = "4fc35722cd7f0b4d7334d4b188ae63c624d592727bfe77d6f425924a1042e4df"
# (Quelle, Index, Teilaufgabe): (Kriterien bis 29ef1b0, ab FG-87)
KRITERIEN_FG87 = {("ap1", 24, 1): (3, 2),      # A1-025 T2
                  ("ap1", 38, 2): (3, 2),      # A1-039 T3
                  ("ap2", 35, 0): (2, 1)}      # A2-036 T1
# Rahmenplan-Punkte aller Karten/Fragen der Reihe nach (= 14b3bd4 = 29558a8)
RAHMENPLAN_HASH = "b62aa2d0a92a4a7e49881fa11f6fec7208f9c05b6d2ded733aa990adf5c15220"
# test_rahmenplan.STAND_054 bis S4 (c582094/29558a8)
STAND_054_S4 = {"karteikarten": "c561380390f8e0017a47b1ea1d41760d0851b71ccc237a896d4d2bf4853c2759",
                "quizfragen": "d014140dec13a4e19cc334b72994024603ee41c43bb5e1c760d036782a3d492a"}


def neu(text):
    return text.replace(ZB, ZB_NEU).replace(BC, BC_NEU)


def neue_texte():
    listen = {"karte": lade("karteikarten.json"), "quiz": lade("quizfragen.json")}
    return [(art, alt, listen[art][index]["q"]) for art, index, alt in UMBENANNT_N12]


# ============================================================================
#  B-N-08: Wortlaut
# ============================================================================

class ZbTest(unittest.TestCase):

    def test_kein_zb_mehr(self):
        for datei in ANZAHL_TEXT:
            self.assertNotIn(ZB, roh(datei), datei)

    def test_anzahl_je_datei(self):
        # jede alte Stelle ist genau eine neue, keine verschwunden, keine dazu
        for datei, (zb, bc_neu, bc_alt) in ANZAHL_TEXT.items():
            text = roh(datei)
            self.assertEqual((text.count(ZB_NEU), text.count(BC_NEU), text.count(BC)),
                             (zb, bc_neu, bc_alt), datei)

    def test_leerzeichen_wie_s4(self):
        # "z. B." mit normalem Leerzeichen (wie B-D-13), kein geschuetztes
        for datei in ANZAHL_TEXT:
            text = roh(datei)
            for zeichen in (" ", " ", " "):
                self.assertNotIn("z." + zeichen + "B.", text, datei)

    def test_broadcast_fragetexte(self):
        # P1487/P1488 (Nacharbeit Meldung 24, Frage 4 a): Fragetext und
        # Erklaerung "Broadcast-Adresse", sonst wie vorher; nirgends mehr
        # "Broadcastadresse"
        quiz = lade("quizfragen.json")
        for _art, index, alt in UMBENANNT_BC:
            self.assertIn(BC, alt)
            self.assertEqual(quiz[index]["q"], alt.replace(BC, BC_NEU), index)
            self.assertNotIn(BC, quiz[index]["exp"], index)
        rest = [i for i, q in enumerate(quiz) if BC in json.dumps(q, ensure_ascii=False)]
        self.assertEqual(rest, [])

    def test_fachgespraech_nur_zb(self):
        # fachgespraech.json (7 Hinweise): ausser "z. B." alles wie bis S4;
        # ab FG-87 ebenso "Z. B." statt "Z.B." (4 Hinweise, gezaehlt in
        # KriterienGrossZbTest)
        text = json.dumps(lade("fachgespraech.json"), ensure_ascii=False, sort_keys=True)
        text = text.replace(ZB_NEU, ZB).replace(ZB_GROSS_NEU, ZB_GROSS)
        self.assertEqual(hashlib.sha256(text.encode("utf-8")).hexdigest(),
                         "2535d08816d2094809ba212028ffc9545717d7f6711323cfecbe13a469ef5dad")

    def test_spielinhalte_unberuehrt(self):
        # F25 (a): "_hinweis" in aufgaben_vorlagen.json bleibt
        vorlagen = roh(os.path.join("spiel", "aufgaben_vorlagen.json"))
        self.assertEqual(vorlagen.count(ZB), 1)
        self.assertIn(ZB, json.loads(vorlagen)["_hinweis"][1])

    def test_s4_felder_nur_zb(self):
        # N-d: die 80 Felder von S4 unterscheiden sich vom Stand S4 nur durch
        # "z. B." (zurueckgesetzt ergibt sich der alte Pruefwert von S4)
        werte = []
        for datei, felder in sorted(s4.FELDER.items()):
            eintraege = lade(datei)
            werte += [[datei, index, list(pfad), s4.feldwert(eintraege[index], pfad)]
                      for index, pfad in sorted(felder)]
        text = json.dumps(werte, ensure_ascii=False, sort_keys=True)
        self.assertEqual(hashlib.sha256(text.encode("utf-8")).hexdigest(), s4.PRUEFWERT_FELDER)
        zurueck = text.replace(ZB_NEU, ZB).replace(BC_NEU, BC)
        self.assertEqual(hashlib.sha256(zurueck.encode("utf-8")).hexdigest(),
                         "6a778451d3e3ce7d140b8bd66b395e9a9f9989a420bcf76daf57c4bb120336ab")
        self.assertEqual(sum(ZB_NEU in w[3] for w in werte), 7)


# ============================================================================
#  Bestand
# ============================================================================

class BestandZbTest(unittest.TestCase):

    def test_anzahl(self):
        for datei, anzahl in s4.ANZAHL.items():
            self.assertEqual(len(lade(datei)), anzahl, datei)

    def test_kriterien_je_teilaufgabe(self):
        # Test (5): laufende AP1/AP2-Pruefungen speichern Haken je Kriterium;
        # "z. B." darf keinen Satz teilen. Ab FG-87 (TZ2): genau drei
        # Teilaufgaben haben ein Kriterium weniger, alle anderen gleich viele
        anzahl, gleich, weniger = {}, 0, {}
        for quelle in ("ap1", "ap2"):
            for index, szenario in enumerate(fp.source_data(quelle)):
                teile = fp.scenario_parts(szenario)
                anzahl["%s-%d" % (quelle, index)] = None if teile is None else [
                    len(t["kriterien"]) for t in teile["teile"]]
                if teile is None:
                    continue
                for nummer, teil in enumerate(teile["teile"]):
                    alt = teil["loesung"].replace(ZB_NEU, ZB)
                    self.assertEqual(len(fp.criteria(alt)), len(teil["kriterien"]))
                    gleich += 1
                    if (quelle, index, nummer) in KRITERIEN_FG87:
                        weniger[(quelle, index, nummer)] = len(teil["kriterien"])
        self.assertEqual(hashlib.sha256(json.dumps(anzahl, sort_keys=True).encode())
                         .hexdigest(), KRITERIEN_HASH)
        self.assertEqual(gleich, 1787)
        self.assertEqual(weniger, {k: neu for k, (_alt, neu) in KRITERIEN_FG87.items()})
        # mit den alten Zahlen der drei: genau der Wert bis 29ef1b0 (also sonst
        # keine Teilaufgabe geaendert)
        for (quelle, index, nummer), (alt, _neu) in KRITERIEN_FG87.items():
            anzahl["%s-%d" % (quelle, index)][nummer] = alt
        self.assertEqual(hashlib.sha256(json.dumps(anzahl, sort_keys=True).encode())
                         .hexdigest(), KRITERIEN_HASH_BIS_29EF1B0)

    def test_rahmenplan_gleich(self):
        import fisi_core as core
        import fisi_rahmenplan as frp
        punkte = frp.item_points()
        rp = {"karte": [sorted(punkte[(frp.SRC_CARD, k["q"])]) for k in core.KARTEIKARTEN],
              "quiz": [sorted(punkte[(frp.SRC_QUIZ, q["q"])]) for q in core.QUIZ_QUESTIONS]}
        self.assertEqual(hashlib.sha256(json.dumps(rp, sort_keys=True).encode()).hexdigest(),
                         RAHMENPLAN_HASH)

    def test_stand_054_nur_umbenannt(self):
        # Schutzbereich test_rahmenplan.STAND_054: mit den alten Texten der
        # Umbenennungen ergibt sich genau der Wert von S4
        for name, art, anzahl in (("karteikarten", "karte", 1400), ("quizfragen", "quiz", 1946)):
            texte = [e["q"] for e in lade(name + ".json")[:anzahl]]
            for a, index, alt in UMBENANNT_N12:
                if a == art and index < anzahl:
                    texte[index] = alt
            self.assertEqual(hashlib.sha256("\n".join(texte).encode("utf-8")).hexdigest(),
                             STAND_054_S4[name], name)


# ============================================================================
#  Umbenennungen
# ============================================================================

class UmbenennungenZbTest(unittest.TestCase):

    def test_27_fragen_28_stellen(self):
        self.assertEqual(len(UMBENANNT_ZB), 27)
        self.assertEqual(sum(alt.count(ZB) for _a, _i, alt in UMBENANNT_ZB), 28)
        self.assertEqual(sum(1 for a, _i, _t in UMBENANNT_ZB if a == "karte"), 14)

    def test_2_broadcast_fragen(self):
        self.assertEqual(len(UMBENANNT_BC), 2)
        self.assertEqual(sum(alt.count(BC) for _a, _i, alt in UMBENANNT_BC), 2)
        self.assertEqual(sum(alt.count(ZB) for _a, _i, alt in UMBENANNT_BC), 0)
        self.assertEqual(len(UMBENANNT_N12), 29)

    def test_neu_ist_alt_mit_zb(self):
        for art, alt, jetzt in neue_texte():
            self.assertEqual(jetzt, neu(alt), (art, alt))
            self.assertNotEqual(jetzt, alt)

    def test_eintraege_angehaengt(self):
        daten = lade("umbenennungen.json")
        for art in ("karte", "quiz"):
            soll = [(alt, jetzt) for a, alt, jetzt in neue_texte() if a == art]
            eintraege = list(daten[art].items())
            self.assertEqual(eintraege[-len(soll):], soll, art)
            # davor genau die Eintraege bis S4 (alte unveraendert, siehe test_inhalte_0631)
            self.assertEqual(len(eintraege), {"karte": 8, "quiz": 18}[art] + len(soll))

    def test_alt_weg_neu_da(self):
        alle = {"karte": {e["q"] for e in lade("karteikarten.json")},
                "quiz": {e["q"] for e in lade("quizfragen.json")}}
        for art, alt, jetzt in neue_texte():
            self.assertNotIn(alt, alle[art])
            self.assertIn(jetzt, alle[art])

    def test_keine_kette_keine_schleife(self):
        # kein Ziel einer Umbenennung (auch von S4) ist alt oder enthaelt "z.B.";
        # jedes Ziel ist ein heutiger Fragetext
        daten = lade("umbenennungen.json")
        alle = {"karte": {e["q"] for e in lade("karteikarten.json")},
                "quiz": {e["q"] for e in lade("quizfragen.json")}}
        for art in ("karte", "quiz"):
            for alt, jetzt in daten[art].items():
                self.assertNotIn(ZB, jetzt)
                self.assertNotIn(BC, jetzt)
                self.assertNotIn(jetzt, daten[art])
                self.assertIn(jetzt, alle[art], jetzt)

    def test_kern_kennt_die_umbenennungen(self):
        import fisi_core as core
        for art, alt, jetzt in neue_texte():
            tabelle = "card_events" if art == "karte" else "quiz_answers"
            self.assertEqual(core.QUESTION_RENAMES[tabelle].get(alt), jetzt)
            if art == "quiz":
                self.assertEqual(fp.current_question(alt), jetzt)

    def test_genehmigte_ausnahmen(self):
        # Lernstand-Ausnahmen: 12 (S4, F7 d / Meldung 21 Frage 22, K1430 und P2103
        # namentlich) + 27 (B-N-08) + 2 (P1487/P1488, Meldung 24 Frage 4 a);
        # umbenennungen.json kennt keine weiteren neuen
        s4_ids = sorted((art, index) for art, index, _alt in s4.UMBENANNT)
        self.assertEqual(len(s4_ids), 12)
        self.assertIn(("karte", 1429), s4_ids)      # K1430
        self.assertIn(("quiz", 2102), s4_ids)       # P2103
        daten = lade("umbenennungen.json")
        neu_seit_0631 = sum(len(daten[art]) for art in ("karte", "quiz")) - (5 + 9)
        self.assertEqual(neu_seit_0631, 12 + 27 + 2)


# ============================================================================
#  Lernstand-Migration (Plan Nr. 38 Test (3))
# ============================================================================

class MigrationZbTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.alt = s4.code_stand(s4.ALT_TAG)
        if cls.alt is None:
            return
        cls.ordner = tempfile.mkdtemp(prefix="migration_zb_", dir=_TMP)
        karten, quiz = lade("karteikarten.json"), lade("quizfragen.json")
        listen = {"karte": karten, "quiz": quiz}
        cls.paare = {"karte": {}, "quiz": {}}
        daten = {"karte": [], "quiz": [],
                 "andere_karte": [[karten[0]["cat"], karten[0]["q"]]],
                 "anderes_quiz": [[quiz[0]["cat"], quiz[0]["q"]],
                                  # Nachbar von P1487, bleibt
                                  [quiz[1485]["cat"], quiz[1485]["q"]]]}
        # alle genehmigten Ausnahmen: 12 aus S4 (F7 d, Frage 22), 27 aus B-N-08
        # und 2 aus Meldung 24 Frage 4 a (P1487/P1488)
        for art, index, alt in list(s4.UMBENANNT) + UMBENANNT_N12:
            eintrag = listen[art][index]
            daten[art].append([eintrag["cat"], alt])
            cls.paare[art][alt] = eintrag["q"]
        cls.daten = daten
        cls.db_alt = os.path.join(cls.ordner, "alt.db")
        cls.vorher = s4.lauf(cls.alt, cls.db_alt, "anlegen", daten)
        cls.zeilen_vorher = s4.zeilen(cls.db_alt)
        cls.db_neu = os.path.join(cls.ordner, "neu.db")
        shutil.copyfile(cls.db_alt, cls.db_neu)
        cls.nachher = s4.lauf(HERE, cls.db_neu, "lesen")
        cls.zeilen_nachher = s4.zeilen(cls.db_neu)

    def setUp(self):
        if self.alt is None:
            if s4.IN_CI:
                self.fail("Code aus %s nicht verfuegbar" % s4.ALT_TAG)
            self.skipTest("Code aus %s nicht verfuegbar (git archive)" % s4.ALT_TAG)

    def test_genau_die_fragetexte_geaendert(self):
        vorher, nachher = self.zeilen_vorher, self.zeilen_nachher
        self.assertEqual(sorted(vorher), sorted(nachher))
        geaendert, texte = 0, set()
        for tabelle, alte in vorher.items():
            neue = nachher[tabelle]
            self.assertEqual(len(alte), len(neue), tabelle)
            if tabelle not in ("card_events", "quiz_answers"):
                self.assertEqual(alte, neue, tabelle)        # auch pruefungen (N-g)
                continue
            art = "karte" if tabelle == "card_events" else "quiz"
            for alt, jetzt in zip(alte, neue):
                soll = list(alt)
                soll[3] = self.paare[art].get(alt[3], alt[3])
                self.assertEqual(list(jetzt), soll, tabelle)  # uid, Zeit, Ergebnis gleich
                if alt[3] != jetzt[3]:
                    geaendert += 1
                    texte.add((art, alt[3]))
        # Karten je 3 Antworten (17 Fragen), Quiz je 2 bzw. 3 (24 Fragen)
        self.assertEqual(geaendert, 17 * 3 + 24 * 2 + 8)
        soll = {(art, alt) for art, paare in self.paare.items() for alt in paare}
        self.assertEqual(texte, soll)
        self.assertEqual(len(texte), 12 + 27 + 2)

    def test_lernstand_je_frage_vollstaendig(self):
        alt = {(q, k): v for q, k, v in self.vorher["ergebnisse"]}
        jetzt = {(q, k): v for q, k, v in self.nachher["ergebnisse"]}
        self.assertEqual(len(alt), len(jetzt))
        for art, paare in self.paare.items():
            for frage_alt, frage_neu in paare.items():
                self.assertNotIn((art, frage_alt), jetzt)
                self.assertEqual(jetzt[(art, frage_neu)], alt[(art, frage_alt)], frage_neu)
        self.assertEqual(self.vorher["kennzahlen"], self.nachher["kennzahlen"])
        self.assertEqual(self.vorher["fachbereiche"], self.nachher["fachbereiche"])
        self.assertEqual(self.vorher["themen"], self.nachher["themen"])

    def test_zweites_oeffnen_byte_gleich(self):
        kopie = os.path.join(self.ordner, "zweimal.db")
        shutil.copyfile(self.db_neu, kopie)
        vorher = s4.sha(kopie)
        s4.lauf(HERE, kopie, "oeffnen")
        self.assertEqual(s4.sha(kopie), vorher)

    def test_ohne_umbenannte_antworten_byte_gleich(self):
        datenbank = os.path.join(self.ordner, "ohne.db")
        s4.lauf(self.alt, datenbank, "anlegen", dict(self.daten, karte=[], quiz=[]))
        vorher, groesse = s4.sha(datenbank), os.path.getsize(datenbank)
        s4.lauf(HERE, datenbank, "lesen")
        self.assertEqual((s4.sha(datenbank), os.path.getsize(datenbank)), (vorher, groesse))
        self.assertFalse(os.path.exists(datenbank + "-journal"))
        self.assertFalse(os.path.exists(datenbank + "-wal"))

    def test_abgleich_von_altem_geraet(self):
        export = s4.lauf(self.alt, self.db_alt, "export")["export"]
        datenbank = os.path.join(self.ordner, "abgleich.db")
        ergebnis = s4.lauf(HERE, datenbank, "merge", export)
        jetzt = {(q, k): v for q, k, v in ergebnis["ergebnisse"]}
        for art, paare in self.paare.items():
            for frage_alt, frage_neu in paare.items():
                self.assertNotIn((art, frage_alt), jetzt)
                self.assertIn((art, frage_neu), jetzt)
        conn = sqlite3.connect(datenbank)
        try:
            for tabelle in ("card_events", "quiz_answers"):
                self.assertEqual(sorted(r[0] for r in conn.execute("SELECT uid FROM %s" % tabelle)),
                                 sorted(r[0] for r in export["tables"][tabelle]))
        finally:
            conn.close()
        self.assertEqual(ergebnis["kennzahlen"], self.vorher["kennzahlen"])

    def test_gestellte_fragen_beim_neuen_text(self):
        # N-g mit echter Datenbank: die mit v0.63.1 gespeicherte WiSo-Pruefung
        # (alte Fragetexte in pruefungen.daten) zaehlt beim heutigen Text, die
        # Datenbank bleibt dabei byte-gleich
        import fisi_core as core
        kopie = os.path.join(self.ordner, "verlauf.db")
        shutil.copyfile(self.db_neu, kopie)
        vorher = s4.sha(kopie)
        db = core.DBManager(kopie)
        verlauf = db.exams()
        used = fp.used_items(verlauf, fp.WISO)
        for frage_alt, frage_neu in self.paare["quiz"].items():
            self.assertIn(frage_neu, used)
            self.assertNotIn(frage_alt, used)
        fp.new_exam(fp.WISO, verlauf, seed=3)
        del db
        self.assertEqual(s4.sha(kopie), vorher)


# ============================================================================
#  N-g: schon gestellte WiSo-Fragen
# ============================================================================

class GestelltTest(unittest.TestCase):

    def setUp(self):
        self.quiz = lade("quizfragen.json")
        self.fern_alt = UMBENANNT_ZB[[i for _a, i, _t in UMBENANNT_ZB].index(WISO_FERNABSATZ)][2]
        self.fern_neu = self.quiz[WISO_FERNABSATZ]["q"]
        # S4: P1025 (Widerrufsrecht), ebenfalls im WiSo-Pool
        self.agb_alt = [alt for art, index, alt in s4.UMBENANNT if (art, index) == ("quiz", 1024)][0]
        self.agb_neu = self.quiz[1024]["q"]

    def verlauf(self, fragen):
        return [{"art": fp.WISO, "daten": {"fragen": [{"q": q, "richtig": True} for q in fragen]}},
                {"art": fp.AP1, "daten": {"aufgaben": [{"index": 4}]}}]

    def test_alter_text_zaehlt_beim_neuen(self):
        used = fp.used_items(self.verlauf([self.fern_alt, self.agb_alt]), fp.WISO)
        self.assertEqual(used, {self.fern_neu, self.agb_neu})
        # auch die Kurzform (nur Text statt dict) aus aelteren Staenden
        self.assertEqual(fp.used_items([{"art": fp.WISO, "daten": {"fragen": [self.fern_alt]}}],
                                       fp.WISO), {self.fern_neu})
        self.assertEqual(fp.used_items(self.verlauf([]), fp.AP1), {4})

    def test_neue_pruefung_meidet_die_frage(self):
        verlauf = self.verlauf([self.fern_alt, self.agb_alt])
        pool = fp.wiso_pool()
        self.assertIn(self.fern_neu, pool)
        self.assertIn(self.agb_neu, pool)
        for seed in range(60):
            fragen = fp.new_exam(fp.WISO, verlauf, seed=seed)["fragen"]
            self.assertEqual(len(fragen), fp.WISO_COUNT)
            self.assertNotIn(self.fern_neu, fragen, seed)
            self.assertNotIn(self.agb_neu, fragen, seed)

    def test_kette(self):
        # alt -> Zwischentext -> heutiger Text
        gespeichert = fp.QUESTION_RENAMES.get("quiz_answers")
        try:
            fp.QUESTION_RENAMES["quiz_answers"] = dict(gespeichert, **{
                "Ganz alter Text?": self.fern_alt})
            used = fp.used_items(self.verlauf(["Ganz alter Text?"]), fp.WISO)
            self.assertEqual(used, {self.fern_neu})
        finally:
            fp.QUESTION_RENAMES["quiz_answers"] = gespeichert

    def test_ohne_umbenennung_wie_bisher(self):
        fragen = [q for q in fp.wiso_pool()[:10]]
        verlauf = self.verlauf(fragen) + [{"art": fp.WISO, "daten": {}},
                                          {"art": fp.WISO, "daten": {"fragen": ["unbekannt?"]}}]
        self.assertEqual(fp.used_items(verlauf, fp.WISO), set(fragen) | {"unbekannt?"})
        for seed in range(20):
            self.assertFalse(set(fp.new_exam(fp.WISO, verlauf, seed=seed)["fragen"]) & set(fragen))

    def test_verlauf_wird_nicht_umgeschrieben(self):
        verlauf = self.verlauf([self.fern_alt])
        kopie = json.loads(json.dumps(verlauf))
        fp.used_items(verlauf, fp.WISO)
        fp.new_exam(fp.WISO, verlauf, seed=5)
        self.assertEqual(verlauf, kopie)


# ============================================================================
#  FG-87 (Zusatz von Nico, Frage 5 b): "Z.B." in den Bewertungskriterien
# ============================================================================

# Kriterien der drei Teilaufgaben bis 0.63.1 (= bis 29ef1b0)
KRITERIEN_FG87_ALT = {
    ("ap1", 24, 1): ["Z.B.",
                     "\"Standard-Image freigegeben\" und \"Alle 40 Arbeitsplätze umgestellt\".",
                     "Meilensteine haben keine Dauer, sie markieren einen wichtigen "
                     "Zwischenstand."],
    ("ap1", 38, 2): ["Z.B.",
                     "TCP 3389 (RDP), TCP 445 (SMB), TCP 22 (SSH ohne Einschränkung), "
                     "Datenbankports wie 3306.",
                     "Fernzugriff gehört hinter ein VPN."],
    ("ap2", 35, 0): ["Z.B.",
                     "\"Bei welchen Tätigkeiten merken Sie die Langsamkeit besonders?\", "
                     "\"Mit welchen Programmen arbeiten Sie täglich?\", \"Wie viele Mitarbeiter "
                     "arbeiten an den Geräten?\", \"Welche Pläne haben Sie für die nächsten "
                     "Jahre?\""],
}

SKRIPT_FG87 = r"""
import json, os, sys
code, aufgabe, daten = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
sys.path.insert(0, code)
import fisi_core as core
import fisi_pruefung as fp
out = {"datei": fp.__file__}
if aufgabe == "kriterien":
    out["kriterien"] = [fp.task_details({"aufgaben": [{"quelle": q, "index": i}]}, 0)
                        ["teile"][t]["kriterien"] for q, i, t in daten["teile"]]
if aufgabe == "anlegen":
    state = fp.new_exam(daten["art"], seed=1)
    state["aufgaben"] = daten["aufgaben"]
    for nummer in range(len(state["aufgaben"])):
        for teil, part in enumerate(fp.task_details(state, nummer)["teile"]):
            key = fp.answer_key(nummer, teil)
            state["antworten"][key] = "Antwort %s" % key
            state["kriterien"][key] = daten["haken"].get(
                key, [i % 2 == 0 for i in range(len(part["kriterien"]))])
            state["punkte"][key] = max(0, part["punkte"] - nummer - teil)
    fp.submit(state)
    fp.save_running(state)
    out["state"] = state
if aufgabe == "laden":
    out["geladen"] = fp.load_running()
if aufgabe == "speichern":
    # wie die Oberflaeche nach einem Klick: laden (umgestellt) und speichern
    state = fp.load_running()
    fp.save_running(state)
    out["geladen"] = state
if aufgabe == "abgeben":
    state = fp.load_running()
    out["geladen"] = json.loads(json.dumps(state))
    out["ergebnis"] = fp.finish(core.DBManager(), state)
    out["laufend"] = fp.load_running()
print("ERGEBNIS " + json.dumps(out, ensure_ascii=False))
"""


def lauf_fg87(code, datenbank, aufgabe, daten=None):
    env = dict(os.environ, FISI_DB_PATH=datenbank, HOME=_TMP, APPDATA=_TMP,
               FISI_SELFTEST=os.path.join(_TMP, "selbsttest_fg87.log"))
    proc = subprocess.run([sys.executable, "-c", SKRIPT_FG87, code, aufgabe,
                           json.dumps(daten or {}, ensure_ascii=False)],
                          cwd=_TMP, env=env, capture_output=True, timeout=600)
    zeilen = [z for z in proc.stdout.decode("utf-8").splitlines() if z.startswith("ERGEBNIS ")]
    if proc.returncode or not zeilen:
        raise AssertionError("Lauf %s mit %s: %s" % (aufgabe, code, proc.stderr.decode()[-2000:]))
    ergebnis = json.loads(zeilen[-1][len("ERGEBNIS "):])
    if os.path.dirname(os.path.abspath(ergebnis["datei"])) != os.path.abspath(code):
        raise AssertionError("falscher Code: %s statt %s" % (ergebnis["datei"], code))
    return ergebnis


def laufender_stand(aufgaben, kriterien, art=fp.AP1):
    return {"art": art, "start": "2026-10-13 10:00:00", "start_utc": 0, "minuten": 90,
            "phase": "laeuft", "aufgaben": aufgaben,
            "antworten": {k: "Antwort %s" % k for k in kriterien},
            "punkte": {k: 3 for k in kriterien}, "kriterien": kriterien}


def teile_von(quelle, index):
    return fp.task_details({"aufgaben": [{"quelle": quelle, "index": index}]}, 0)["teile"]


class KriterienGrossZbTest(unittest.TestCase):
    """FG-87: "Z.B." / "Z. B." teilt kein Kriterium mehr; laufende Pruefungen
    mit A1-025 T2, A1-039 T3, A2-036 T1 werden umgestellt (Haken von "Z.B."
    faellt weg, die Aussage behaelt ihren eigenen), alle anderen bleiben
    byte-gleich. Tests TZ1-TZ8 (Plan plan_fg87_ZB.md T1-T8)."""

    def test_tz1_criteria_gross_zb(self):
        self.assertEqual(fp.criteria("Z.B. Router tauschen. Danach testen."),
                         ["Z.B. Router tauschen.", "Danach testen."])
        self.assertEqual(fp.criteria("Z. B. Router tauschen. Danach testen."),
                         ["Z. B. Router tauschen.", "Danach testen."])
        # vor "Z.B." endet ein Satz weiterhin (darum nicht im Tupel _ABBREVIATIONS)
        self.assertEqual(fp.criteria("Das reicht so. Z.B. Router tauschen. Danach testen."),
                         ["Das reicht so.", "Z.B. Router tauschen.", "Danach testen."])
        self.assertEqual(fp.criteria("Das reicht so. Z. B. Router tauschen."),
                         ["Das reicht so.", "Z. B. Router tauschen."])
        # mitten im Satz und am Zeilenanfang einer Aufzaehlung
        self.assertEqual(fp.criteria("Beispiele, Z.B. Router tauschen. Danach testen."),
                         ["Beispiele, Z.B. Router tauschen.", "Danach testen."])
        self.assertEqual(fp.criteria("- Z. B. Router tauschen. Danach testen."),
                         ["Z. B. Router tauschen.", "Danach testen."])
        # klein wie bisher
        self.assertEqual(fp.criteria("Das ist z. B. so. Gut so."), ["Das ist z. B. so.", "Gut so."])
        self.assertEqual(fp.criteria("Das ist z.B. so. Gut so."), ["Das ist z.B. so.", "Gut so."])

    def test_tz1_bekannte_grenzen(self):
        # Nicht erkannt (im Bestand nicht vorhanden, siehe test_tz3_*): Verhalten
        # wie bis 0.63.1
        self.assertEqual(fp.criteria("Z.b. Router tauschen. Danach testen."),
                         ["Z.b.", "Router tauschen.", "Danach testen."])
        self.assertEqual(fp.criteria("z.b. Router tauschen. Danach testen."),
                         ["z.b.", "Router tauschen.", "Danach testen."])
        self.assertEqual(fp.criteria("Z. B. Router tauschen. Danach testen."),
                         ["Router tauschen.", "Danach testen."])
        self.assertEqual(fp.criteria("XYZ.B. Router tauschen."), ["XYZ.B.", "Router tauschen."])

    def test_tz2_nur_drei_teilaufgaben(self):
        # Gegenrechnung zu BestandZbTest.test_kriterien_je_teilaufgabe: bis 0.63.1
        # stand "Z.B." allein; heute steht es vor der Aussage
        for (quelle, index, teil), (alt, neu) in KRITERIEN_FG87.items():
            kriterien = teile_von(quelle, index)[teil]["kriterien"]
            self.assertEqual(len(KRITERIEN_FG87_ALT[(quelle, index, teil)]), alt)
            self.assertEqual(len(kriterien), neu)
            self.assertTrue(kriterien[0].startswith((ZB_GROSS + " ", ZB_GROSS_NEU + " ")))

    def test_tz5_alle_hakenmuster(self):
        # Haken-Regel (Antwort Meldung 26, Frage 2 a): Haken von "Z.B." faellt
        # weg, die Aussage behaelt ihren eigenen, nie ein fremder Haken
        for (quelle, index, teil), alt in KRITERIEN_FG87_ALT.items():
            teile = teile_von(quelle, index)
            for muster in itertools.product([False, True], repeat=len(alt)):
                kriterien = {fp.answer_key(0, n): [n % 2 == 0] * len(p["kriterien"])
                             for n, p in enumerate(teile)}
                key = fp.answer_key(0, teil)
                kriterien[key] = list(muster)
                vorher = laufender_stand([{"quelle": quelle, "index": index}], kriterien)
                kopie = json.loads(json.dumps(vorher))
                jetzt = fp.migrate_running(kopie)
                self.assertEqual(jetzt["kriterien"][key], list(muster[1:]), (quelle, index, muster))
                self.assertEqual(len(jetzt["kriterien"][key]), len(teile[teil]["kriterien"]))
                for k in kriterien:
                    if k != key:
                        self.assertEqual(jetzt["kriterien"][k], vorher["kriterien"][k])
                ohne = {k: v for k, v in jetzt.items() if k != "kriterien"}
                self.assertEqual(ohne, {k: v for k, v in vorher.items() if k != "kriterien"})
                # zweites Oeffnen aendert nichts
                self.assertEqual(fp.migrate_running(json.loads(json.dumps(jetzt))), jetzt)

    def test_tz6_criteria_before_wie_0631(self):
        for schluessel, alt in KRITERIEN_FG87_ALT.items():
            self.assertEqual(fp.CRITERIA_BEFORE[schluessel], alt, schluessel)
        self.assertEqual(fp._SPLIT_FRAGMENTS, ("Z.B.",))
        alt_code = s4.code_stand(s4.ALT_TAG)
        if alt_code is None:
            if s4.IN_CI:
                self.fail("Code aus %s nicht verfuegbar" % s4.ALT_TAG)
            self.skipTest("Code aus %s nicht verfuegbar" % s4.ALT_TAG)
        ordner = tempfile.mkdtemp(prefix="fg87_kriterien_", dir=_TMP)
        teile = sorted(KRITERIEN_FG87_ALT)
        ergebnis = lauf_fg87(alt_code, os.path.join(ordner, "k.db"), "kriterien",
                             {"teile": [list(t) for t in teile]})
        self.assertEqual(ergebnis["kriterien"], [KRITERIEN_FG87_ALT[t] for t in teile])

    def test_tz7_andere_pruefungen_byte_gleich(self):
        # alle 592 anderen Aufgaben, je 3 Hakenmuster: migrate_running aendert nichts
        faelle = 0
        for quelle in ("ap1", "ap2"):
            for index, _szenario in enumerate(fp.source_data(quelle)):
                if any((quelle, index) == k[:2] for k in KRITERIEN_FG87):
                    continue
                teile = teile_von(quelle, index)
                for muster in ("alle", "keine", "wechsel"):
                    kriterien = {}
                    for n, p in enumerate(teile):
                        m = len(p["kriterien"])
                        kriterien[fp.answer_key(0, n)] = (
                            [True] * m if muster == "alle" else [False] * m if muster == "keine"
                            else [k % 2 == 0 for k in range(m)])
                    stand = laufender_stand([{"quelle": quelle, "index": index}], kriterien)
                    vorher = json.dumps(stand, sort_keys=True)
                    self.assertEqual(json.dumps(fp.migrate_running(stand), sort_keys=True),
                                     vorher, (quelle, index, muster))
                    faelle += 1
        self.assertEqual(faelle, 592 * 3)
        # die drei Aufgaben, schon mit den neuen Kriterien (in 0.63.2 gestartet)
        for quelle, index, _teil in KRITERIEN_FG87:
            teile = teile_von(quelle, index)
            kriterien = {fp.answer_key(0, n): [True] * len(p["kriterien"])
                         for n, p in enumerate(teile)}
            stand = laufender_stand([{"quelle": quelle, "index": index}], kriterien)
            vorher = json.dumps(stand, sort_keys=True)
            self.assertEqual(json.dumps(fp.migrate_running(stand), sort_keys=True), vorher)

    def test_tz8_unbekannt_kuerzer_bleibt(self):
        # (iv) kuerzere neue Liste ohne passenden Eintrag: unveraendert
        teile = teile_von("ap1", 0)
        kriterien = {fp.answer_key(0, n): [True, False] * (len(p["kriterien"]) + 1)
                     for n, p in enumerate(teile)}
        stand = laufender_stand([{"quelle": "ap1", "index": 0}], kriterien)
        vorher = json.dumps(stand, sort_keys=True)
        self.assertEqual(json.dumps(fp.migrate_running(stand), sort_keys=True), vorher)
        # betroffene Aufgabe, aber Laenge passt nicht zu CRITERIA_BEFORE: unveraendert
        key = fp.answer_key(0, 1)
        stand = laufender_stand([{"quelle": "ap1", "index": 24}],
                                {key: [True, True, False, True]})
        vorher = json.dumps(stand, sort_keys=True)
        self.assertEqual(json.dumps(fp.migrate_running(stand), sort_keys=True), vorher)
        # S4-Fall (neue Liste laenger) wie bisher, "Z.B." spielt dort keine Rolle
        self.assertEqual(fp.align_marks([True], ["a"], ["b", "c"]), [True, False])
        stand = laufender_stand([{"quelle": "ap1", "index": 4}], {fp.answer_key(0, 2): [True]})
        self.assertEqual(fp.migrate_running(stand)["kriterien"][fp.answer_key(0, 2)],
                         [True, False])


class MischbetriebFg87Test(unittest.TestCase):
    """TZ5 mit echtem Code v0.63.1: laufende Pruefung in 0.63.1 gestartet,
    in 0.63.2 geoeffnet (umgestellt) und gespeichert, wieder geoeffnet, in
    0.63.1 wieder geoeffnet, abgegeben. Einstellungen liegen nur auf diesem
    Geraet (einstellungen.json, kein Abgleich, nicht in der Sicherung)."""

    @classmethod
    def setUpClass(cls):
        cls.alt = s4.code_stand(s4.ALT_TAG)
        if cls.alt is not None:
            cls.ordner = tempfile.mkdtemp(prefix="fg87_misch_", dir=_TMP)

    def setUp(self):
        if self.alt is None:
            if s4.IN_CI:
                self.fail("Code aus %s nicht verfuegbar" % s4.ALT_TAG)
            self.skipTest("Code aus %s nicht verfuegbar (git archive)" % s4.ALT_TAG)

    def einstellungen(self, datenbank):
        with open(os.path.join(os.path.dirname(datenbank), "einstellungen.json"), "rb") as handle:
            return handle.read()

    def datenbank(self, name):
        ordner = os.path.join(self.ordner, name)
        os.makedirs(ordner)
        return os.path.join(ordner, "lernstand.db")

    FAELLE = [
        # (Art, Aufgaben, Haken in 0.63.1, erwartet in 0.63.2)
        ("ap1", [{"quelle": "ap1", "index": 24}, {"quelle": "ap1", "index": 38}],
         {"0-1": [True, False, True], "1-2": [False, True, False]},
         {"0-1": [False, True], "1-2": [True, False]}),
        ("netzwerke", [{"quelle": "ap2", "index": 35}, {"quelle": "ap2", "index": 134}],
         {"0-0": [True, False]},
         # A2-135 (S4, neue Liste laenger) daneben wie in test_inhalte_0632
         {"0-0": [False], "1-0": [True, False, False, True, False, True]}),
        ("netzwerke", [{"quelle": "ap2", "index": 35}],
         {"0-0": [False, True]},
         {"0-0": [True]}),
    ]

    def test_tz5_mischbetrieb(self):
        for nummer, (art, aufgaben, haken, erwartet) in enumerate(self.FAELLE):
            with self.subTest(fall=nummer):
                db = self.datenbank("fall%d" % nummer)
                alt = lauf_fg87(self.alt, db, "anlegen",
                                {"art": art, "aufgaben": aufgaben, "haken": haken})["state"]
                datei_alt = self.einstellungen(db)
                # 0.63.2 oeffnet: umgestellt, aber nichts geschrieben
                neu = lauf_fg87(HERE, db, "laden")["geladen"]
                self.assertEqual(self.einstellungen(db), datei_alt)
                for key, liste in alt["kriterien"].items():
                    self.assertEqual(neu["kriterien"][key], erwartet.get(key, liste), key)
                self.assertEqual(neu["punkte"], alt["punkte"])
                self.assertEqual(neu["antworten"], alt["antworten"])
                self.assertEqual({k: v for k, v in neu.items() if k != "kriterien"},
                                 {k: v for k, v in alt.items() if k != "kriterien"})
                # speichern (wie nach einem Klick), danach zweites Oeffnen: nichts
                # doppelt umgestellt, Datei byte-gleich
                lauf_fg87(HERE, db, "speichern")
                gespeichert = self.einstellungen(db)
                self.assertEqual(lauf_fg87(HERE, db, "laden")["geladen"], neu)
                self.assertEqual(self.einstellungen(db), gespeichert)
                # wieder 0.63.1 (Rueckkehr auf diesem Geraet): laedt, nichts
                # umgestellt, Punkte und Antworten gleich
                zurueck = lauf_fg87(self.alt, db, "laden")["geladen"]
                self.assertEqual(zurueck, neu)
                self.assertEqual(self.einstellungen(db), gespeichert)
                # abgeben in 0.63.2: Ergebnis = vergebene Punkte, Pruefung beendet
                ab = lauf_fg87(HERE, db, "abgeben")
                self.assertEqual(ab["geladen"], neu)
                self.assertIsNone(ab["laufend"])
                self.assertEqual(ab["ergebnis"]["punkte"], float(sum(alt["punkte"].values())))

    def test_tz5_alt_abgeben_nach_umstellung(self):
        # 0.63.1 -> 0.63.2 (gespeichert) -> Abgabe wieder in 0.63.1: geht, gleiche Punkte
        art, aufgaben, haken, _erwartet = self.FAELLE[0]
        db = self.datenbank("alt_abgabe")
        alt = lauf_fg87(self.alt, db, "anlegen",
                        {"art": art, "aufgaben": aufgaben, "haken": haken})["state"]
        lauf_fg87(HERE, db, "speichern")
        ab = lauf_fg87(self.alt, db, "abgeben")
        self.assertIsNone(ab["laufend"])
        self.assertEqual(ab["ergebnis"]["punkte"], float(sum(alt["punkte"].values())))

    def test_tz5_in_0632_gestartet_byte_gleich(self):
        art, aufgaben, _haken, _erwartet = self.FAELLE[0]
        db = self.datenbank("neu_gestartet")
        neu = lauf_fg87(HERE, db, "anlegen", {"art": art, "aufgaben": aufgaben, "haken": {}})
        datei = self.einstellungen(db)
        self.assertEqual(lauf_fg87(HERE, db, "laden")["geladen"], neu["state"])
        lauf_fg87(HERE, db, "speichern")
        self.assertEqual(self.einstellungen(db), datei)
        self.assertEqual(len(neu["state"]["kriterien"]["0-1"]), 2)
        self.assertEqual(len(neu["state"]["kriterien"]["1-2"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
