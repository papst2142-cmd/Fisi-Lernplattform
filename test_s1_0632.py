#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S-1 (Plan-Nachtrag 0.63.2 Nr. 41, Bauauftrag N14, F20 Weg b, FG-58):
Uhr gestellt, Sprung nicht feststellbar - Behalten-Regel ohne Netz.

Ausgang (Bericht 0.62.5 Abschnitt 12): Nach einem Neustart des Systems
(Linux/Android: neue Kennung des Systemstarts) oder - ohne lesbare Kennung
des Systemstarts (Windows/macOS) - nach einem Neustart des Programms ist ein
Sprung der Uhr seit der letzten Messung nicht feststellbar
(fisi_core._clock_jump -> None). Bis 0.63.1 rechneten _stamp und
_marker_now dann die gespeicherte Abweichung voll ein (wie 0.62.4). War die
Uhr inzwischen richtig gestellt, ging dabei etwas verloren:
  * Vorlauf (Uhr ging vor), gestellt: eigene Eintraege lagen um die alte
    Abweichung zu frueh und fielen unter eine Loeschung eines anderen Geraets
    (P1/P2 und Matrix U1/U2 "B loescht, ohne Abgleich").
  * Nachlauf (Uhr ging nach), gestellt: die eigene Loeschmarke lag um die
    alte Abweichung zu spaet und nahm Eintraege anderer Geraete mit, die
    danach entstanden (P4 und Matrix U3/U4 "A loescht, ohne Abgleich").
Ab 0.63.2 (Weg b): Ist der Sprung nicht feststellbar (clock_jump_unknown),
waehlt das Programm je Verwendung die Lesart, die Eintraege behaelt: beim
Stempeln eigener Eintraege wird eine Vorlauf-Abweichung nicht eingerechnet
(Eintrag eher spaeter), eine Nachlauf-Abweichung weiter; bei Loeschmarken
umgekehrt (Nachlauf nicht, Vorlauf weiter: Marke eher frueher).
clock_deviation selbst bleibt unveraendert (einziger Aufrufer ausserhalb:
fisi_sync._correct_own_entries, unveraendert). Kein Netz, kein neues
Dateiformat, kein neuer sync_meta-Schluessel.

Bekannte Grenze (Weisung zu Meldung 38/40, B10 (a)): Weg b laesst auch bei
Loeschungen DIESES Geraets Eintraege uebrig, die ohne den Fix geloescht
wuerden (Matrix U5/U7/U8 "a-av", U6 "b-bv", P3) - sie kommen beim naechsten
Abgleich wieder. Es geht dabei nichts verloren (AK1, Teilmenge).

AK1 (Weisung zu Meldung 41, Frage 1): gegenueber 0.63.1 nie mehr Verlust;
gegenueber S6b eine benannte Ausnahme (U6-Fall): Geht die Uhr dauerhaft nach
und ist der Sprung nicht feststellbar, liegt die eigene Loeschmarke vor einer
frueheren Loeschung eines anderen Geraets; "Alles ersetzen" hebt diese dann
nicht auf (test_grenze_g8_f2b_u6_nachlauf_weiter_falsch, bekannte Grenze,
kein Versprechen; ein zweites "Alles ersetzen" mit derselben Datei holt die
Eintraege zurueck).

Testplan: bau_0.63.2/testplaene/Testplan_N14.md. Hier (CI, Teil "rest"):
Kern-Gitter im Testprozess, Ablaeufe P1-P5, die Matrix-Zellen, in denen
sich etwas aendert, die Hinweis-Zellen (N14-F2), Lernstand T-a (AK7) und
B-G-08 im unsicheren Zustand (N14-A-G8, N14-F5). Alle Matrix-Zellen mit
allen Code-Mischungen, weitere Loescharten, drei Geraete, Sonderfaelle und
26 Zufallsablaeufe: pruefung/s1_voll.py (im Container, Log im Bericht).

Gegen einen anderen Stand:  ABGLEICH_CODE=<ordner> python test_s1_0632.py
Nur unter Linux/macOS (Zeitzone je Prozess ueber TZ).
"""

import ast
import datetime
import json
import os
import shutil
import sqlite3
import sys
import unittest
from unittest import mock

import test_abgleich as ta
import test_abgleich_0632 as t0632
import test_restrisiko_3_18 as rr

HOUR = 3600.0
TWO_H = 2 * HOUR
UTC = datetime.timezone.utc
ALT = "v0.63.1"

# Uhr-Faelle (Testplan 5.1): d = Abweichung bei der Messung, e = danach,
# neustart: "programm" (ohne Kennung des Systemstarts, Windows/macOS),
# "system" (neue Kennung, Linux/Android), "alte_form" (Messung aus 0.62.4).
U_FAELLE = {
    "U1": (TWO_H, 0.0, "programm"),
    "U2": (TWO_H, 0.0, "system"),
    "U3": (-TWO_H, 0.0, "programm"),
    "U4": (-TWO_H, 0.0, "system"),
    "U5": (TWO_H, TWO_H, "programm"),
    "U6": (-TWO_H, -TWO_H, "programm"),
    "U7": (3 * HOUR, HOUR, "programm"),
    "U8": (TWO_H, TWO_H, "alte_form"),
}
ETIKETTEN = ("a-av", "b-bv", "a-an", "b-bn")


def _z(av, bv, an, bn):
    return {"a-av": av, "b-bv": bv, "a-an": an, "b-bn": bn}


RICHTIG = _z(0, 0, 2, 2)

# Soll je Zelle (U, Loescher, A gleicht vor der Loeschung ab) mit diesem
# Stand: (Zahlen je Etikett auf A und B, Hinweis-Sekunden nach der Loeschung
# auf A oder None). Vor dem Bau aus der Regel hergeleitet (Testplan 5.2) und
# mit der Pruefer-Probe (probe_s1_matrix.log, Prototyp) abgeglichen.
SOLL = {
    ("U1", "A", True): (RICHTIG, 0),
    ("U1", "A", False): (_z(0, 2, 2, 2), TWO_H),        # b-bv: Grenze 3 wie bisher
    ("U1", "B", True): (RICHTIG, None),
    ("U1", "B", False): (RICHTIG, None),                # bis 0.63.1: a-an 0 (Verlust)
    ("U3", "A", True): (_z(2, 0, 2, 2), 0),             # a-av: wie bisher
    ("U3", "A", False): (RICHTIG, 0),                   # bis 0.63.1: b-bn 0 (Verlust)
    ("U3", "B", True): (_z(2, 0, 2, 2), None),
    ("U3", "B", False): (_z(2, 0, 2, 2), None),
    ("U5", "A", True): (_z(2, 0, 2, 2), TWO_H),         # a-av: neu "kommt zurueck"
    ("U5", "A", False): (RICHTIG, TWO_H),               # Hinweis wahr (Uhr weiter +2 h)
    ("U5", "B", True): (_z(2, 0, 2, 2), None),          # a-av: neu "kommt zurueck"
    ("U5", "B", False): (_z(2, 0, 2, 2), None),         # a-av: neu "kommt zurueck"
    ("U6", "A", True): (RICHTIG, -TWO_H),
    ("U6", "A", False): (_z(0, 2, 2, 2), 0),            # b-bv: neu "kommt zurueck"
    ("U6", "B", True): (RICHTIG, None),
    ("U6", "B", False): (RICHTIG, None),
    ("U7", "A", True): (_z(2, 0, 2, 2), HOUR),          # a-av: neu "kommt zurueck"
    ("U7", "A", False): (_z(0, 2, 2, 2), 3 * HOUR),     # b-bv: Grenze wie bisher
    ("U7", "B", True): (_z(2, 0, 2, 2), None),          # a-av: neu "kommt zurueck"
    ("U7", "B", False): (_z(2, 0, 2, 2), None),         # bis 0.63.1: a-an 0 (Verlust)
}
for _l in "AB":
    for _v in (True, False):
        SOLL[("U2", _l, _v)] = SOLL[("U1", _l, _v)]
        SOLL[("U4", _l, _v)] = SOLL[("U3", _l, _v)]
        SOLL[("U8", _l, _v)] = SOLL[("U5", _l, _v)]

# Vergleich: dieselbe Zelle mit dem Stand vor N14 (S6b bzw. 14b3bd4; die
# Uhr-Teile _stamp/_marker_now/clock_deviation sind dort gleich), hergeleitet
# und auf 14b3bd4 belegt (probe_s1_matrix.log, code_base). Nur die
# abweichenden Zellen; alle anderen wie SOLL.
BISHER = {
    ("U1", "B", False): _z(0, 0, 0, 2),
    ("U3", "A", False): _z(0, 0, 2, 0),
    ("U5", "A", True): RICHTIG,
    ("U5", "B", True): RICHTIG,
    ("U5", "B", False): RICHTIG,
    ("U6", "A", False): RICHTIG,
    ("U7", "A", True): RICHTIG,
    ("U7", "B", True): RICHTIG,
    ("U7", "B", False): _z(0, 0, 0, 2),
}
for _l, _v in (("B", False), ("A", True), ("B", True)):
    if ("U1", _l, _v) in BISHER:
        BISHER[("U2", _l, _v)] = BISHER[("U1", _l, _v)]
for _k in [k for k in BISHER if k[0] == "U3"]:
    BISHER[("U4",) + _k[1:]] = BISHER[_k]
for _k in [k for k in BISHER if k[0] == "U5"]:
    BISHER[("U8",) + _k[1:]] = BISHER[_k]
BISHER_HINWEIS = {("U3", "A", False): -TWO_H, ("U4", "A", False): -TWO_H,
                  ("U6", "A", False): -TWO_H}


def bisher(zelle):
    return BISHER.get(zelle, SOLL[zelle][0])


# Zellen, die in der CI laufen (Teil "rest", Laufzeit): jede, deren Ergebnis
# sich gegenueber bisher aendert, und die Hinweis-Zellen U5/U8 ohne Abgleich
# (N14-F2: Hinweis wahr). Alle 32 Zellen: pruefung/s1_voll.py.
# Ergebnis eines zweiten "Alles ersetzen" im U6-Fall (Grenze G8, Weisung zu
# Meldung 41, Auflage 2), belegt logs/n14_g8_zweites_ersetzen.log
_ALLES = {"a-vorher": 2, "b-vorher": 2}
ZWEITES_ERSETZEN = {"direkt": _ALLES, "danach": {"A": _ALLES, "B": _ALLES}}
# Fester Sollwert nach dem ersten Ersetzen (U6-Fall, heutiges Ergebnis) und
# der Uhr-Hinweis bei As Loeschung t2, belegt logs/n14_g8_zweites_ersetzen.log
G8_U6_KARTEN = {"A": {}, "B": {}}
G8_U6_HINWEIS = 0
# Zweite benannte Ausnahme (Weisung zu Meldung 44, 2.5), feste Sollwerte =
# heutiges Ergebnis, belegt logs/w44_ausnahme2_*.log
LIFT_RESET = "aufgehoben:reset_at"
AUSNAHME2_HINWEIS = 0
AUSNAHME2_KARTEN = {"A": {"a-nach": 1}, "B": {"a-nach": 1}}
AUSNAHME2_KARTEN_0631 = {"A": {"a-nach": 1}, "B": {"a-nach": 1}}
# (S6b cb60f8b dort: "a-vorher" 2 und "b-vorher" 2 kommen zurueck, Hinweis -7200)


def _utc(text):
    """Marke (Text mit Zone) als UTC-Zeitpunkt."""
    return datetime.datetime.fromisoformat(text).astimezone(UTC)

CI_ZELLEN = sorted(set(BISHER) | {("U5", "A", False), ("U8", "A", False),
                                  ("U1", "A", False)})


class S1Basis(unittest.TestCase):
    """Werkzeuge aus test_restrisiko_3_18 (Uhr, Ruhe), Geraete mit
    pruefung/abgleich_geraet_voll.py und waehlbarem Code."""
    setUp = rr.RestrisikoTest.setUp
    tearDown = rr.RestrisikoTest.tearDown
    zeit = rr.RestrisikoTest.zeit
    ruhe = rr.RestrisikoTest.ruhe
    ergebnis = rr.RestrisikoTest.ergebnis
    alter_code = ta.AbgleichTest.alter_code

    def ordner(self):
        return self.id().rsplit(".", 1)[-1] + getattr(self, "lauf_nr", "")

    def geraet(self, name, tz="Europe/Berlin", code=None):
        device = t0632.GeraetVoll(self.ordner(), name, tz=tz, code=code or ta.CODE)
        self.geraete.append(device)
        self.stand[name] = [tz, 0.0, 0.0]
        return device

    def neu_starten(self, device, *befehle):
        """Programm neu starten (gleiche Datenbank, gleicher Code, gleiche
        Uhr und Laufzeit-Uhr); danach befehle."""
        tz, uhr, extra = self.stand[device.name]
        device.close()
        self.geraete.remove(device)
        neu = t0632.GeraetVoll(os.path.basename(os.path.dirname(device.home)), device.name,
                               tz=tz, code=device.code)
        self.geraete.append(neu)
        neu("uhr", uhr, ta.att.STATE.ctl.get("datum_versatz", 0.0) + extra)
        for befehl in befehle:
            neu(*befehl)
        return neu

    def unsicher_machen(self, a, art):
        """Nach dem Stellen: Sprung nicht feststellbar machen."""
        if art == "programm":
            return self.neu_starten(a, ("ohne_start",))
        if art == "system":
            a("neustart")
            return a
        return a        # alte_form: schon beim Messen

    @staticmethod
    def alte_form(a):
        messung = json.loads(a.marke("uhr_abweichung"))
        a("setmeta", "uhr_abweichung",
          json.dumps({"s": messung["s"], "gemessen": messung["gemessen"]}))

    def zahlen(self, geraete, etiketten):
        return {e: self.ergebnis("S-1", geraete, e) for e in etiketten}

    # ------------------------------------------------------------ Matrix 5.2
    def matrix_lauf(self, u, loescher, sync_vor, codes=(None, None), art="reset_all"):
        """A (Berlin) misst d, Uhr danach e, Sprung nicht feststellbar; A und
        B lernen "av"/"bv", (A gleicht ab), B gleicht ab; loescher loescht
        (art); beide lernen "an"/"bn"; Abgleich A, B, A, B; Ruhe.
        Liefert ({etikett: {A, B}}, Hinweis-Sekunden des Loeschers)."""
        d, e, neustart = U_FAELLE[u]
        a = self.geraet("A", code=codes[0])
        b = self.geraet("B", "UTC", code=codes[1])
        if neustart == "programm":
            a("ohne_start")
        self.zeit(0, A=d)
        for device in (a, b):
            device("lerne", 2, "vorher")
            if art != "reset_all":
                device("fuelle", "vorher")
        for device in (a, b, a):
            device.sync()                               # A misst d
        if neustart == "alte_form":
            self.alte_form(a)
        self.zeit(2.5, A=e)                             # e = 0: gestellt
        a = self.unsicher_machen(a, neustart)
        self.zeit(3.0, A=e)
        a("lerne", 2, "av")
        b("lerne", 2, "bv")
        if art != "reset_all":
            a("fuelle", "av")
            b("fuelle", "bv")
        if sync_vor:
            a.sync()                                    # misst neu, wieder feststellbar
        b.sync()
        self.zeit(3.4, A=e)
        antwort = (a if loescher == "A" else b)(art)
        self.assertTrue(antwort["ok"], antwort)
        self.zeit(3.6, A=e)
        a("lerne", 2, "an")
        b("lerne", 2, "bn")
        if art != "reset_all":
            a("fuelle", "an")
            b("fuelle", "bn")
        self.zeit(3.9, A=e)
        for device in (a, b, a, b):
            device.sync()
        self.ruhe((a, b))
        if art == "reset_all":
            for device in (a, b):
                self.assertTrue(ta.ohne(device.namen(), "-vorher"), (u, device.name))
            return self.zahlen((a, b), ETIKETTEN), antwort.get("uhr_fix"), (a, b)
        return None, antwort.get("uhr_fix"), (a, b)

    def zelle_pruefen(self, zelle, zahlen, hinweis):
        soll, soll_hinweis = SOLL[zelle]
        ta.bericht("Matrix %s: %s, Hinweis %s" % (zelle, zahlen, hinweis))
        for etikett, n in soll.items():
            self.assertEqual(zahlen[etikett], {"A": n, "B": n}, (zelle, etikett, zahlen))
        if soll_hinweis is not None:
            if soll_hinweis:
                self.assertLessEqual(abs(hinweis - soll_hinweis), 120, (zelle, hinweis))
            else:
                self.assertEqual(hinweis, 0, (zelle, hinweis))
        # AK1: nie weniger als bisher
        for etikett, n in bisher(zelle).items():
            self.assertGreaterEqual(zahlen[etikett]["A"], n, (zelle, etikett))
            self.assertGreaterEqual(zahlen[etikett]["B"], n, (zelle, etikett))


def _matrix_test(zelle):
    def test(self):
        zahlen, hinweis, _ = self.matrix_lauf(*zelle)
        self.zelle_pruefen(zelle, zahlen, hinweis)
    test.__doc__ = ("Matrix %s, %s loescht, A gleicht vorher %sab (Testplan 5.2)"
                    % (zelle[0], zelle[1], "" if zelle[2] else "nicht "))
    return test


class S1MatrixTest(S1Basis):
    """Matrix-Zellen mit Aenderung gegenueber bisher und Hinweis-Zellen
    (alle 32 Zellen und Code-Mischungen: pruefung/s1_voll.py)."""


for _zelle in CI_ZELLEN:
    setattr(S1MatrixTest, "test_matrix_%s_%s_%s" % (
        _zelle[0].lower(), _zelle[1].lower(), "mit_abgleich" if _zelle[2] else "ohne_abgleich"),
        _matrix_test(_zelle))


class S1AblaufTest(S1Basis):
    """Ablaeufe P1 bis P5 (Testplan 5.7)."""

    def _eigener_nach_stellen(self, d, art):
        """A misst d, Uhr wird richtig gestellt, Sprung nicht feststellbar;
        B loescht; A lernt danach offline: bleibt As Eintrag?"""
        a, b = self.geraet("A"), self.geraet("B", "UTC")
        if art == "programm":
            a("ohne_start")
        self.zeit(0, A=d)
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        for device in (a, b, a):
            device.sync()
        self.zeit(2.5)
        a = self.unsicher_machen(a, art)
        b("reset_all")
        b.sync()
        self.zeit(3)
        a("lerne", 2, "nach")
        for device in (a, b, a):
            device.sync()
        self.ruhe((a, b))
        for device in (a, b):
            self.assertTrue(ta.ohne(device.namen(), "-vorher"), device.name)
        return self.ergebnis("eigener Eintrag nach dem Stellen", (a, b), "a-nach")

    def test_risiko_3_eigener_eintrag_ohne_startkennung_neu_gestartet(self):
        """P1 (Gegentest zu test_grenze_3_ohne_startkennung_neu_gestartet,
        N14-F3): Uhr +2 h gemessen, richtig gestellt, Programm ohne Kennung
        des Systemstarts neu gestartet (Windows/macOS); B loescht, A lernt
        danach. Der Eintrag bleibt. (Bis 0.63.1: {"A": 0, "B": 0} - _stamp
        rechnete die alte Abweichung ein, der Eintrag lag 2 h zu frueh.)"""
        self.assertEqual(self._eigener_nach_stellen(TWO_H, "programm"), {"A": 2, "B": 2})

    def test_p2_eigener_eintrag_nach_systemneustart(self):
        """P2: wie P1 nach einem Neustart des Systems (Linux/Android, neue
        Kennung). (Bis 0.63.1: {"A": 0, "B": 0}.)"""
        self.assertEqual(self._eigener_nach_stellen(TWO_H, "system"), {"A": 2, "B": 2})

    def test_p5_schutz_nachlauf_eigener_eintrag(self):
        """P5 (Schutz): Uhr -2 h gemessen, gestellt, Programm neu gestartet;
        B loescht, A lernt danach: Der Eintrag bleibt (wie bisher)."""
        self.assertEqual(self._eigener_nach_stellen(-TWO_H, "programm"), {"A": 2, "B": 2})

    def test_p4_nachlauf_marke_nach_neustart(self):
        """P4: Uhr -2 h gemessen, gestellt, Programm neu gestartet (ohne
        Kennung des Systemstarts); A loescht, B lernt DANACH offline: Bs
        Eintraege bleiben. (Bis 0.63.1: {"A": 0, "B": 0} - die Marke lag 2 h
        zu spaet.)"""
        a, b = self.geraet("A"), self.geraet("B", "UTC")
        a("ohne_start")
        self.zeit(0, A=-TWO_H)
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        for device in (a, b, a):
            device.sync()
        self.zeit(3)
        a = self.neu_starten(a, ("ohne_start",))
        antwort = a("reset_all")
        ta.bericht("P4 Marke A %s, Hinweis %s" % (a.marke(), antwort.get("uhr_fix")))
        self.assertEqual(antwort.get("uhr_fix"), 0)
        self.zeit(3.5)
        b("lerne", 3, "nach")
        for device in (b, a, b, a):
            device.sync()
        self.ruhe((a, b))
        for device in (a, b):
            self.assertTrue(ta.ohne(device.namen(), "-vorher"), device.name)
        self.assertEqual(self.ergebnis("P4 Nachlauf Marke", (a, b), "b-nach"),
                         {"A": 3, "B": 3})

    def test_grenze_p3_eigene_loeschung_bei_weiter_falscher_uhr(self):
        """P3 - BEKANNTE GRENZE, KEIN VERSPRECHEN (Weisung zu Meldung 38/40,
        B10 (a)): Uhr bleibt +2 h falsch, Programm ohne Kennung des
        Systemstarts neu gestartet (nicht feststellbar); A lernt "x" (ohne
        Vorlauf-Korrektur gestempelt, liegt 2 h spaeter), gleicht ab und
        loescht 1 h spaeter selbst alles. "x" kommt beim Abgleich zurueck: es
        geht nichts verloren. (Bis 0.63.1: {"A": 0, "B": 0}.)"""
        a, b = self.geraet("A"), self.geraet("B", "UTC")
        a("ohne_start")
        self.zeit(0, A=TWO_H)
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        for device in (a, b, a):
            device.sync()
        self.zeit(0.5, A=TWO_H)
        a = self.neu_starten(a, ("ohne_start",))
        a("lerne", 2, "x")
        a.sync()
        b.sync()
        self.zeit(1.5, A=TWO_H)
        antwort = a("reset_all")
        ta.bericht("P3 Hinweis %s" % antwort.get("uhr_fix"))
        for device in (a, b, a, b):
            device.sync()
        self.ruhe((a, b))
        self.assertEqual(self.ergebnis("P3 eigene Loeschung", (a, b), "a-x"), {"A": 2, "B": 2})


class S1LernstandTest(S1Basis):
    """AK7: Datenbank aus v0.63.1 mit gespeicherter grosser Abweichung (vor
    und nach) mit diesem Stand oeffnen -> byte-gleich, keine Nebendateien."""

    def test_t_a_alte_datenbank_mit_messung_byte_gleich(self):
        alt = self.alter_code(ALT)
        for nr, s in enumerate((TWO_H, -TWO_H)):
            self.lauf_nr = "_%d" % nr
            a = self.geraet("A", code=alt)
            a("fuelle", "vor")
            a("lerne", 3, "vor")
            a("ohne_start")
            a("setmeta", "uhr_abweichung", json.dumps(
                {"s": s, "gemessen": datetime.datetime.now(UTC).astimezone().isoformat(),
                 "lauf": 1.0, "start": None, "prozess": "anderer"}))
            a("reset_all")
            a("fuelle", "nach")
            vorher = a("db_sha")
            a.code = ta.CODE
            a = self.neu_starten(a, ("ohne_start",))
            nachher = a("db_sha")
            ta.bericht("T-a S-1 (s=%+g): %s -> %s, Nebendateien %s" % (
                s, vorher["sha"][:16], nachher["sha"][:16], nachher["nebendateien"]))
            self.assertEqual(nachher["sha"], vorher["sha"], s)
            self.assertEqual(nachher["groesse"], vorher["groesse"], s)
            self.assertEqual(nachher["nebendateien"], [], s)
            a.close()
            self.geraete.remove(a)


def _verlauf(device):
    """{etikett: Zahl} der Eintraege in Testhistorie und Pruefungen."""
    stand = device("inhalt")["tabellen"]
    result = {}
    for table in ("test_results", "pruefungen"):
        for row in stand.get(table, []):
            werte = json.loads(row)
            text = json.dumps(werte, ensure_ascii=False)
            for teil in ("a-vl", "b-vl"):
                if teil in text:
                    result[teil] = result.get(teil, 0) + 1
    return result


class S1ErsetzenTest(S1Basis):
    """N14-A-G8 (Testplan 5.5, N14-F5): B-G-08/FG-81 Satz 6 im unsicheren
    Zustand - Abfolge f2b (und f2g "vor") mit A unter U3/U6, Programm ohne
    Kennung des Systemstarts neu gestartet. Soll: kein Etikett weniger als
    mit dem Stand S6b (AK1). Das Soll ist das Ergebnis von S6b (cad90c0) in
    demselben Ablauf (belegt, bau_0.63.2/n14/logs)."""

    def pfad(self, device, name="sicherung.fisisicherung"):
        return os.path.join(device.home, name)

    def _f2b(self, u, zweimal=False):
        d, e, _ = U_FAELLE[u]
        a, b = self.geraet("A"), self.geraet("B", "UTC")
        a("ohne_start")
        self.zeit(0, A=d)
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        for device in (a, b, a):
            device.sync()                               # A misst d
        self.zeit(1, A=d)
        a("sicherung_erstellen", self.pfad(a))
        self.zeit(2.5, A=e)
        a = self.neu_starten(a, ("ohne_start",))        # nicht feststellbar
        self.zeit(3.0, A=e)
        b("lerne", 1, "spaet")
        self.zeit(3.2, A=e)
        self.assertTrue(b("reset_all")["ok"])           # t1, A kennt das nicht
        b.sync()
        self.zeit(3.4, A=e)
        a("lerne", 1, "zw")
        self.zeit(3.6, A=e)
        antwort = a("reset_all")                        # t2, spaeter, ohne Abgleich
        self.assertTrue(antwort["ok"])
        stand = {"t1": b.marke(), "t2": a.marke(), "hinweis": antwort.get("uhr_fix")}
        self.zeit(3.8, A=e)
        a("sicherung_ersetzen", self.pfad(a))
        self.zeit(4.0, A=e)
        for _ in range(3):
            for device in (a, b):
                device.sync()
        self.ruhe((a, b))
        stand["karten"] = {device.name: device.namen() for device in (a, b)}
        if zweimal:
            # Weisung zu Meldung 41, Auflage 2: zweites "Alles ersetzen" mit
            # derselben Sicherungsdatei, danach Abgleich
            self.zeit(4.2, A=e)
            a("sicherung_ersetzen", self.pfad(a))
            stand["zweites_direkt"] = a.namen()
            self.zeit(4.4, A=e)
            for _ in range(3):
                for device in (a, b):
                    device.sync()
            self.ruhe((a, b))
            stand["zweites"] = {device.name: device.namen() for device in (a, b)}
        ta.bericht("G8 f2b %s: %s" % (u, stand))
        return stand

    def _f2g(self, u, variante):
        """f2g (test_abgleich_0632 auf S6b lokal, Weisung zu Meldung 37) mit
        A unter u: A kennt eine spaetere Loeschung "Alle Lerndaten" von C
        (t2), nicht die von B (t1); As eigene Loeschung ist "Historie
        loeschen" (tA). vor: t1 < t2 < tA; nach: tA < t1 < t2. A wird nach
        jedem eigenen Abgleich ohne Kennung des Systemstarts neu gestartet
        (Sprung nicht feststellbar)."""
        d, e, _ = U_FAELLE[u]
        a = self.geraet("A")
        b = self.geraet("B", "UTC")
        c = self.geraet("C", "Asia/Tokyo")
        a("ohne_start")
        self.zeit(0, A=d)
        a("lerne", 2, "vorher")
        a("fuelle", "vl")
        b("lerne", 2, "vorher")
        b("fuelle", "vl")
        c("lerne", 2, "vorher")
        for _ in range(2):
            for device in (a, b, c):
                device.sync()                           # A misst d
        self.zeit(1, A=d)
        a("sicherung_erstellen", self.pfad(a))
        self.zeit(2.5, A=e)
        a = self.neu_starten(a, ("ohne_start",))
        stand = {}
        if variante == "nach":
            self.zeit(2.8, A=e)
            stand["hinweis_tA"] = a("clear_history").get("uhr_fix")    # tA
        self.zeit(3.0, A=e)
        b("lerne", 1, "zw")
        self.zeit(3.1, A=e)
        self.assertTrue(b("reset_all")["ok"])           # t1, A kennt das nicht
        b.sync()
        self.zeit(3.2, A=e)
        c.sync()
        self.zeit(3.3, A=e)
        c("lerne", 1, "zw")
        self.zeit(3.4, A=e)
        self.assertTrue(c("reset_all")["ok"])           # t2
        c.sync()
        self.zeit(3.5, A=e)
        a.sync()                                        # A kennt t2 (nicht t1)
        a = self.neu_starten(a, ("ohne_start",))        # wieder nicht feststellbar
        if variante == "vor":
            self.zeit(3.7, A=e)
            stand["hinweis_tA"] = a("clear_history").get("uhr_fix")    # tA nach t2
        stand.update({"t1": b.marke(), "t2": c.marke(), "reset_at_A": a.marke(),
                      "tA": a.marke("history_cleared_at")})
        self.zeit(3.8, A=e)
        a("sicherung_ersetzen", self.pfad(a))
        self.zeit(4.0, A=e)
        for _ in range(3):
            for device in (a, b, c):
                device.sync()
        self.ruhe((a, b, c))
        stand["karten"] = {device.name: device.namen() for device in (a, b, c)}
        stand["verlauf"] = {device.name: _verlauf(device) for device in (a, b, c)}
        ta.bericht("G8 f2g %s %s: %s" % (u, variante, stand))
        return stand

    # Ergebnis von S6b (Basis 69e62ae) in denselben Ablaeufen, belegt
    # (logs/basis_69e62ae_g8_f2g.log); Soll: kein Etikett weniger (AK1).
    F2G_S6B = {"karten": {"a-vorher": 2, "a-vl": 1, "b-vorher": 2, "b-vl": 1, "c-vorher": 2},
               "verlauf": {"a-vl": 1, "b-vl": 1}}

    def _f2g_pruefen(self, u, variante):
        stand = self._f2g(u, variante)
        for name in "ABC":
            for art in ("karten", "verlauf"):
                for etikett, n in self.F2G_S6B[art].items():
                    self.assertGreaterEqual(stand[art][name].get(etikett, 0), n,
                                            (u, variante, name, art, etikett))

    def test_g8_f2g_u3_vor(self):
        self._f2g_pruefen("U3", "vor")

    def test_g8_f2g_u3_nach(self):
        self._f2g_pruefen("U3", "nach")

    def test_g8_f2g_u6_vor(self):
        self._f2g_pruefen("U6", "vor")

    def test_g8_f2g_u6_nach(self):
        self._f2g_pruefen("U6", "nach")

    def test_g8_f2b_u3_nachlauf_gestellt(self):
        """f2b, A ging 2 h nach (gemessen), Uhr gestellt, Neustart: wie S6b."""
        stand = self._f2b("U3")
        for name in "AB":
            self.assertEqual(stand["karten"][name], {"a-vorher": 2, "b-vorher": 2}, name)

    def test_grenze_g8_f2b_u6_nachlauf_weiter_falsch(self):
        """BEKANNTE GRENZE, KEIN VERSPRECHEN (Weisung zu Meldung 41, Frage 1
        (a) vorlaeufig, N14-F5): f2b, A geht weiter 2 h nach (gemessen),
        Programm ohne Kennung des Systemstarts neu gestartet. As eigene
        Loeschung (t2) bekommt mit Weg b die Geraetezeit (2 h zu frueh) und
        liegt damit vor Bs frueherer Loeschung (t1): t1 wird beim Ersetzen
        nicht aufgehoben, der eingespielte Stand verschwindet beim Abgleich
        auf A und B. AK1: gegenueber 0.63.1 nie mehr Verlust (0.63.1 hebt
        nichts auf, gleiches Ergebnis); gegenueber S6b eine benannte Ausnahme
        (dieser U6-Fall; S6b: {"a-vorher": 2, "b-vorher": 2} auf A und B).
        Die Eintraege bleiben in der Sicherungsdatei. Haelt das heutige
        Ergebnis fest, auch fuer ein zweites "Alles ersetzen" mit derselben
        Datei (Auflage 2)."""
        stand = self._f2b("U6", zweimal=True)
        # Fester Sollwert = heutiges Ergebnis (Weisung zu Meldung 42, 4 Nr. 2):
        # kein Uhr-Hinweis bei t2, nach dem ersten Ersetzen auf A und B leer,
        # nach dem zweiten Ersetzen direkt und nach 3 Runden je 2/2.
        self.assertEqual(stand["hinweis"], G8_U6_HINWEIS)
        for name in "AB":
            self.assertEqual(stand["karten"][name], G8_U6_KARTEN[name], name)
        self.assertEqual(stand["zweites_direkt"], ZWEITES_ERSETZEN["direkt"])
        for name in "AB":
            self.assertEqual(stand["zweites"][name], ZWEITES_ERSETZEN["danach"][name], name)

    def _ausnahme2(self, code=None, lauf=""):
        """Zweite benannte Ausnahme (Weisung zu Meldung 44, 2.5; Startwerte
        34/41 in s1_voll ZufallErsetzen): B misst -2 h und sichert, Uhr
        gestellt, Programm ohne Kennung des Systemstarts neu gestartet
        (nicht feststellbar). B loescht (t2) und ersetzt ohne Abgleich;
        24 min nach t2 loescht A (t3, A kennt t2 nicht); Abgleich."""
        self.lauf_nr = lauf
        a = self.geraet("A", code=code)
        b = self.geraet("B", "UTC", code=code)
        b("ohne_start")
        self.zeit(0, B=-TWO_H)
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        for device in (a, b, b):
            device.sync()                               # B misst -2 h
        self.zeit(1, B=-TWO_H)
        b("sicherung_erstellen", self.pfad(b))
        self.zeit(2.5)                                  # Uhr von B gestellt
        b = self.neu_starten(b, ("ohne_start",))        # nicht feststellbar
        self.zeit(3.0)
        b("lerne", 1, "zw")
        antwort = b("reset_all")                        # t2
        self.assertTrue(antwort["ok"])
        stand = {"hinweis": antwort.get("uhr_fix")}
        self.zeit(3.2)
        b("sicherung_ersetzen", self.pfad(b))
        stand["aufgehoben"] = b.marke(LIFT_RESET)
        self.zeit(3.4)
        self.assertTrue(a("reset_all")["ok"])           # t3, echt nach t2
        stand["t3"] = a.marke()
        self.zeit(3.6)
        a("lerne", 1, "nach")
        self.zeit(4.0)
        for _ in range(3):
            for device in (a, b):
                device.sync()
        self.ruhe((a, b))
        stand["karten"] = {device.name: device.namen() for device in (a, b)}
        for device in (a, b):
            device.close()
            self.geraete.remove(device)
        ta.server_reset()
        ta.bericht("Ausnahme 2 (%s): %s" % (code or "N", stand))
        return stand

    def test_ausnahme2_uhr_gestellt_fremde_loeschung_nach_ersetzen(self):
        """BENANNTE AUSNAHME 2 GEGENUEBER S6B (Weisung zu Meldung 44, 2.5):
        S6b rechnet die alte Messung (-2 h) in Bs Marke t2 ein, obwohl die
        Uhr gestellt ist: Marke und Aufhebungsmarke liegen 2 h zu spaet, die
        spaetere echte Loeschung t3 von A gilt dort mit als aufgehoben und
        "vorher" kommt zurueck. N setzt t2 richtig, t3 wirkt. Gegen 0.63.1
        (hebt nichts auf): gleiches Ergebnis, nie mehr Verlust. Feste
        Sollwerte = heutiges Ergebnis (N und v0.63.1)."""
        n = self._ausnahme2()
        self.assertEqual(n["hinweis"], AUSNAHME2_HINWEIS)
        # Aufhebungsmarke (t2) vor t3: die spaetere Loeschung wird nicht aufgehoben
        self.assertLess(_utc(json.loads(n["aufgehoben"])[0]), _utc(n["t3"]))
        for name in "AB":
            self.assertEqual(n["karten"][name], AUSNAHME2_KARTEN[name], name)
        alt = self._ausnahme2(self.alter_code(ALT), "_alt")
        for name in "AB":
            self.assertEqual(alt["karten"][name], AUSNAHME2_KARTEN_0631[name], ("0.63.1", name))


class S1KernTest(unittest.TestCase):
    """Kern-Gitter (Testplan 4.1) im Testprozess: _stamp, _marker_now,
    last_clock_fix und clock_deviation je Zustand und Abweichung. Messung
    zur Laufzeit 1000 s im Systemstart S1, Prozess P1 (wie
    UhrsprungKernTest)."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, ta.CODE)
        try:
            import fisi_core
        finally:
            sys.path.remove(ta.CODE)
        cls.core = fisi_core

    GEMESSEN = datetime.datetime(2026, 10, 12, 10, 0, tzinfo=UTC)
    # Zustand -> (gespeicherte Felder, jetzt_start, jetzt_prozess, Laufzeit
    # seit der Messung oder None = wie Geraeteuhr, feststellbar?)
    ZUSTAENDE = {
        "gleicher_prozess": ({"start": "S1", "prozess": "P1"}, "S1", "P1", True),
        "gleicher_start": ({"start": "S1", "prozess": "P1"}, "S1", "P2", True),
        "ohne_start_gleicher_prozess": ({"start": None, "prozess": "P1"}, None, "P1", True),
        "anderer_start": ({"start": "S1", "prozess": "P1"}, "S2", "P2", False),
        "ohne_start_anderer_prozess": ({"start": None, "prozess": "P1"}, None, "P2", False),
        "alte_form": ({"lauf": ..., "start": ..., "prozess": ...}, "S1", "P1", False),
        "lauf_unlesbar": ({"lauf": "x", "start": "S1", "prozess": "P1"}, "S1", "P1", False),
    }
    ABWEICHUNGEN = (TWO_H, -TWO_H, 400.0, -400.0, 290.0, -290.0)

    def messung(self, s, felder):
        data = {"s": s, "gemessen": self.GEMESSEN.isoformat(), "lauf": 1000.0}
        data.update(felder)
        return json.dumps({k: v for k, v in data.items() if v is not ...})

    def lesen(self, value, wand, laufzeit, jetzt_start, jetzt_prozess):
        """_stamp (Abstand minus Zonenabstand in Minuten), _marker_now (Text,
        Hinweis-Sekunden) und clock_deviation zum Zeitpunkt Messung + wand."""
        core = self.core
        jetzt = (self.GEMESSEN + datetime.timedelta(seconds=wand)).astimezone(
            datetime.timezone(datetime.timedelta(hours=2)))
        conn = sqlite3.connect(":memory:")
        try:
            conn.execute("CREATE TABLE sync_meta (key TEXT PRIMARY KEY, value TEXT)")
            if value is not None:
                conn.execute("INSERT INTO sync_meta VALUES (?, ?)", (core.CLOCK_KEY, value))
            meta = type("Meta", (), {"get_meta": lambda _self, key: value
                                     if key == core.CLOCK_KEY else None})()
            with mock.patch.object(core, "device_now", lambda: jetzt), \
                    mock.patch.object(core, "_boot_clock", lambda: 1000.0 + laufzeit), \
                    mock.patch.object(core, "_boot_id", lambda: jetzt_start), \
                    mock.patch.object(core, "PROCESS_TOKEN", jetzt_prozess):
                text, abstand = core.DBManager._stamp(meta)
                marke, hinweis = core.DBManager._marker_now(conn.cursor())
                abweichung = core.clock_deviation(value, jetzt)
        finally:
            conn.close()
        self.assertEqual(text, jetzt.strftime("%Y-%m-%d %H:%M:%S"))
        return abstand - 120, marke, hinweis, abweichung, jetzt

    def soll(self, eingerechnet, jetzt):
        """Was _stamp/_marker_now liefern, wenn eingerechnet (Sekunden oder
        None) eingerechnet wird."""
        stamp = int(round(eingerechnet / 60.0)) if eingerechnet else 0
        if eingerechnet:
            marke = self.core.format_with_zone(
                (jetzt - datetime.timedelta(seconds=eingerechnet)).astimezone())
        else:
            marke = self.core.format_with_zone(jetzt)
        return stamp, marke, eingerechnet or 0

    def gitter(self, wand_von_s, laufzeit_von_s):
        """Alle Zustaende x Abweichungen; liefert die Zellen, in denen das
        Soll gilt und geprueft wurde."""
        zellen = 0
        for zustand, (felder, j_start, j_prozess, feststellbar) in self.ZUSTAENDE.items():
            for s in self.ABWEICHUNGEN:
                wand, laufzeit = wand_von_s(s), laufzeit_von_s(s)
                value = self.messung(s, felder)
                stamp, marke, hinweis, abweichung, jetzt = self.lesen(
                    value, wand, laufzeit, j_start, j_prozess)
                # clock_deviation unveraendert (N14-F4): bei nicht
                # feststellbarem Sprung die Messung selbst (wie 0.62.4)
                if not feststellbar:
                    self.assertEqual(abweichung, s, (zustand, s))
                bisher = abweichung if abweichung is not None and abs(abweichung) > 300 else None
                unsicher = not feststellbar and abs(s) > 300
                fuer_stempel = None if unsicher and s > 0 else bisher
                fuer_marke = None if unsicher and s < 0 else bisher
                ort = (zustand, s, wand, laufzeit)
                self.assertEqual(stamp, self.soll(fuer_stempel, jetzt)[0], ort)
                soll_marke = self.soll(fuer_marke, jetzt)
                self.assertEqual(marke, soll_marke[1], ort)
                self.assertEqual(hinweis, soll_marke[2], ort)      # AK8
                zellen += 1
        return zellen

    def test_kein_sprung(self):
        """Uhr seit der Messung nicht gestellt (Geraeteuhr und Laufzeit-Uhr
        gleich weit): feststellbar -> wie bisher; nicht feststellbar ->
        Behalten-Regel."""
        self.assertEqual(self.gitter(lambda s: 3 * HOUR, lambda s: 3 * HOUR), 42)

    def test_richtig_gestellt(self):
        """Uhr nach der Messung um die Abweichung zurueckgestellt (danach
        richtig): feststellbar -> nichts mehr eingerechnet (wie bisher);
        nicht feststellbar -> Behalten-Regel."""
        self.assertEqual(self.gitter(lambda s: 3 * HOUR - s, lambda s: 3 * HOUR), 42)

    def test_ungueltige_messung_unveraendert(self):
        """Messung aelter als 24 h, in der Zukunft, unlesbar oder fehlend:
        nichts eingerechnet, in jedem Zustand (K10)."""
        for zustand, (felder, j_start, j_prozess, _) in self.ZUSTAENDE.items():
            for s in (TWO_H, -TWO_H):
                for value, wand in ((self.messung(s, felder), 25 * HOUR),
                                    (self.messung(s, felder), -60.0),
                                    ("kaputt", HOUR), (None, HOUR),
                                    (json.dumps({"s": s, "gemessen": "2026-10-12 10:00:00"}),
                                     HOUR)):
                    stamp, marke, hinweis, abweichung, jetzt = self.lesen(
                        value, wand, wand, j_start, j_prozess)
                    self.assertIsNone(abweichung, (zustand, s, value, wand))
                    self.assertEqual((stamp, marke, hinweis), self.soll(None, jetzt),
                                     (zustand, s, value, wand))

    def test_laufzeit_rueckwaerts_nicht_feststellbar(self):
        """Laufzeit-Uhr kleiner als beim Messen (anderer Systemstart):
        Behalten-Regel."""
        value = self.messung(-TWO_H, {"start": "S1", "prozess": "P1"})
        stamp, marke, hinweis, abweichung, jetzt = self.lesen(value, 6700, -500.0, "S1", "P1")
        self.assertEqual(abweichung, -TWO_H)
        self.assertEqual(stamp, -120)                       # Nachlauf weiter im Stempel
        self.assertEqual((marke, hinweis), self.soll(None, jetzt)[1:])
        value = self.messung(TWO_H, {"start": "S1", "prozess": "P1"})
        stamp, marke, hinweis, abweichung, jetzt = self.lesen(value, 6700, -500.0, "S1", "P1")
        self.assertEqual(stamp, 0)                          # Vorlauf nicht im Stempel
        self.assertEqual((marke, hinweis), self.soll(TWO_H, jetzt)[1:])

    def test_lesefunktion(self):
        """clock_jump_unknown (ab 0.63.2) liest nur: gleiche Zellen wie
        _clock_jump/clock_deviation."""
        core = self.core
        self.assertTrue(hasattr(core, "clock_jump_unknown"), "Lesefunktion fehlt")
        for zustand, (felder, j_start, j_prozess, feststellbar) in self.ZUSTAENDE.items():
            for s in self.ABWEICHUNGEN:
                value = self.messung(s, felder)
                jetzt = self.GEMESSEN + datetime.timedelta(seconds=HOUR)
                with mock.patch.object(core, "_boot_clock", lambda: 1000.0 + HOUR), \
                        mock.patch.object(core, "_boot_id", lambda: j_start), \
                        mock.patch.object(core, "PROCESS_TOKEN", j_prozess):
                    self.assertEqual(core.clock_jump_unknown(value, jetzt),
                                     not feststellbar and abs(s) > 300, (zustand, s))
        # Messung zu alt (> 24 h) oder in der Zukunft: gilt nicht (K10)
        value = self.messung(TWO_H, {"start": None, "prozess": "P1"})
        with mock.patch.object(core, "_boot_id", lambda: None), \
                mock.patch.object(core, "PROCESS_TOKEN", "P2"):
            self.assertTrue(core.clock_jump_unknown(
                value, self.GEMESSEN + datetime.timedelta(hours=23)))
            for stunden in (25, -0.1):
                self.assertFalse(core.clock_jump_unknown(
                    value, self.GEMESSEN + datetime.timedelta(hours=stunden)), stunden)
        for value in (None, "", "kaputt", "5", json.dumps({"s": "x"}),
                      json.dumps({"s": TWO_H, "gemessen": "2026-10-12 10:00:00"})):
            self.assertFalse(core.clock_jump_unknown(value), value)

    def test_uhr_teile_ast_gleich_wie_v0631(self):
        """N14-F4: clock_deviation, _clock_jump und clock_measurement sind
        AST-gleich zu v0.63.1 (= S6b, dort unveraendert)."""
        alt = ta.code_stand(ALT)
        if alt is None:
            if ta.IN_CI:
                self.fail("Code aus %s nicht verfuegbar" % ALT)
            self.skipTest("Code aus %s nicht verfuegbar (git archive)" % ALT)

        def funktionen(ordner):
            with open(os.path.join(ordner, "fisi_core.py"), encoding="utf-8") as handle:
                baum = ast.parse(handle.read())
            return {node.name: ast.dump(node) for node in baum.body
                    if isinstance(node, ast.FunctionDef)}
        neu, vorher = funktionen(ta.CODE), funktionen(alt)
        for name in ("clock_deviation", "_clock_jump", "clock_measurement"):
            self.assertEqual(neu[name], vorher[name], name)


def tearDownModule():
    ta.SERVER.shutdown()
    shutil.rmtree(ta.WORK, ignore_errors=True)
    shutil.rmtree(t0632.WORK_KERN, ignore_errors=True)


if __name__ == "__main__":
    if os.name == "nt":
        print("test_s1_0632.py braucht Zeitzonen je Prozess (TZ) - nur Linux/macOS.")
        sys.exit(0)
    print("Code der Geraete: %s" % ta.CODE)
    unittest.main(verbosity=2)
