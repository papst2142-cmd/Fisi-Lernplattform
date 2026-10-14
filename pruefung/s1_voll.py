#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Volle Pruefung S-1 (Testplan N14 Abschnitte 5.2 bis 5.6) - laeuft NICHT in
der CI (Laufzeit), sondern im Container; das Log gehoert in den Bericht.
Die CI-Teilmenge steht in test_s1_0632.py (dieselben Werkzeuge und Soll).

  MatrixVoll    alle 32 Zellen (U1-U8 x Loescher A/B x A gleicht vorher ab
                ja/nein) mit den Codes (N,N), (O,O), (N,O), (O,N);
                N = dieser Stand, O = v0.63.1. (N,N) gegen das Soll aus
                test_s1_0632.SOLL, (O,O) gegen test_s1_0632.BISHER (belegt
                damit die Vergleichstabelle), gemischt: kein Etikett weniger
                als (O,O) (AK1).
  Loescharten   "Historie loeschen", "Bestenliste loeschen", "Spielstand
                zuruecksetzen" unter U1/U3, A loescht ohne Abgleich, Codes
                (N,N), (N,O) gegen (O,O); Kontrolle ohne Zeitbezug
                ("Spielstand loeschen", "Projekt loeschen") gegen den
                Vergleichsstand: gleicher Inhalt.
  DreiGeraete   A, B, C (C offline, gleicht zuletzt ab) in allen 8
                Mischungen v0.63.1/N in U1 "B loescht ohne Abgleich" und U3
                "A loescht ohne Abgleich" gegen nur v0.63.1.
  Sonder        U11 doppelte Stunde 25.10.2026 (Uhr 1 h vor, Neustart), U9
                Kontrollen (290 s, Messung 25 h alt, Messung in der Zukunft)
                gegen den Vergleichsstand: gleiche Zahlen.
  Zufall        26 Zufallsablaeufe (Startwerte 1..26) mit N und mit dem
                Vergleichsstand: kein Etikett hat mit N weniger (AK1).

Vergleichsstand (Zufall, Kontrolle, Sonder): S1_REF_CODE=<ordner mit dem
Code von S6b>, sonst v0.63.1 (git archive).
Aufruf aus dem Repository-Ordner:
    python pruefung/s1_voll.py [Klasse[.test] ...]
Nur unter Linux/macOS (Zeitzone je Prozess ueber TZ).
"""

import datetime
import itertools
import json
import os
import random
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import test_abgleich as ta  # noqa: E402
import test_abgleich_0632 as t0632  # noqa: E402
import test_s1_0632 as s1  # noqa: E402

HOUR = s1.HOUR
TWO_H = s1.TWO_H
UTC = datetime.timezone.utc


class VollBasis(s1.S1Basis):
    def alt(self):
        return self.alter_code(s1.ALT)

    def ref(self):
        return os.environ.get("S1_REF_CODE") or self.alt()

    def neuer_lauf(self, name):
        """Geraete schliessen, Attrappe leeren, neuer Ordner."""
        for device in self.geraete:
            device.close()
        self.geraete = []
        self.stand = {}
        ta.server_reset()
        self.lauf_nr = "_" + name

    @staticmethod
    def codename(code):
        return "N" if code in (None, ta.CODE) else "O"


# ------------------------------------------------------------------- Matrix
def _matrix_voll(zelle):
    def test(self):
        alt = self.alt()
        stand = {}
        for codes in ((None, None), (alt, alt), (None, alt), (alt, None)):
            name = "".join(self.codename(c) for c in codes)
            self.neuer_lauf(name)
            zahlen, hinweis, _ = self.matrix_lauf(*zelle, codes=codes)
            stand[name] = zahlen
            ta.bericht("MatrixVoll %s %s: %s, Hinweis %s" % (zelle, name, zahlen, hinweis))
            if name == "NN":
                self.zelle_pruefen(zelle, zahlen, hinweis)
        for etikett, n in s1.bisher(zelle).items():
            self.assertEqual(stand["OO"][etikett], {"A": n, "B": n}, ("OO", zelle, etikett))
        for name in ("NO", "ON"):
            for etikett in s1.ETIKETTEN:
                for dev in "AB":
                    self.assertGreaterEqual(stand[name][etikett][dev], stand["OO"][etikett][dev],
                                            (name, zelle, etikett, dev))
    return test


class MatrixVoll(VollBasis):
    pass


for _zelle in sorted(s1.SOLL):
    setattr(MatrixVoll, "test_%s_%s_%s" % (_zelle[0].lower(), _zelle[1].lower(),
                                           "mit" if _zelle[2] else "ohne"),
            _matrix_voll(_zelle))


# --------------------------------------------------------------- Loescharten
TABELLE = {"clear_history": "pruefungen", "reset_records": "spiel_bestenliste",
           "reset_game": "spiel_ereignisse"}
SOLL_ART = {"U1": {"a-av": 0, "b-bv": 1, "a-an": 1, "b-bn": 1},      # b-bv Grenze 3
            "U3": {"a-av": 0, "b-bv": 0, "a-an": 1, "b-bn": 1}}      # bisher b-bn 0


def _hat(row, etikett):
    """Zeile (JSON-Liste aus "inhalt") gehoert zu etikett: ein Wert ist
    genau etikett (Bestenliste) oder enthaelt es als JSON-Text (Daten)."""
    return any(isinstance(v, str) and (v == etikett or '"%s"' % etikett in v)
               for v in json.loads(row))


def zaehle_art(geraete, table):
    result = {}
    for etikett in s1.ETIKETTEN:
        result[etikett] = {}
        for device in geraete:
            rows = device("inhalt")["tabellen"].get(table, [])
            result[etikett][device.name] = sum(1 for row in rows if _hat(row, etikett))
    return result


def _art_test(u, art):
    def test(self):
        alt = self.alt()
        table = TABELLE[art]
        stand = {}
        for codes in ((alt, alt), (None, None), (None, alt)):
            name = "".join(self.codename(c) for c in codes)
            self.neuer_lauf(name)
            _, hinweis, geraete = self.matrix_lauf(u, "A", False, codes=codes, art=art)
            stand[name] = zaehle_art(geraete, table)
            ta.bericht("Loeschart %s %s %s (%s): %s, Hinweis %s"
                       % (art, u, name, table, stand[name], hinweis))
        for etikett, n in SOLL_ART[u].items():
            self.assertEqual(stand["NN"][etikett], {"A": n, "B": n}, (art, u, etikett))
        for name in ("NN", "NO"):
            for etikett in s1.ETIKETTEN:
                for dev in "AB":
                    self.assertGreaterEqual(stand[name][etikett][dev], stand["OO"][etikett][dev],
                                            (art, u, name, etikett, dev))
    return test


class Loescharten(VollBasis):
    def _kontrolle(self, was):
        """U1, A loescht ohne Zeitbezug (Spielstand loeschen / Projekt
        loeschen); Ergebnis mit N und mit dem Vergleichsstand gleich."""
        stand = {}
        for code in (self.ref(), None):
            self.neuer_lauf(self.codename(code) + was)
            a = self.geraet("A", code=code)
            b = self.geraet("B", "UTC", code=code)
            a("ohne_start")
            self.zeit(0, A=TWO_H)
            a("fuelle", "vorher")
            b("fuelle", "vorher")
            for device in (a, b, a):
                device.sync()
            self.zeit(2.5)
            a = self.neu_starten(a, ("ohne_start",))
            self.zeit(3.0)
            a("fuelle", "av")
            b("fuelle", "bv")
            b.sync()
            self.zeit(3.4)
            if was == "spiel":
                self.assertTrue(a("delete_run", 1, "lauf-b-vorher")["ok"])
            else:
                a("projekt_loeschen", "Projekt b-vorher")
            self.zeit(3.6)
            a("fuelle", "an")
            self.zeit(3.9)
            for device in (a, b, a, b):
                device.sync()
            self.ruhe((a, b))
            stand[self.codename(code)] = {d.name: t0632.inhalt_ohne_zeit(d("inhalt"))
                                          for d in (a, b)}
        ta.bericht("Kontrolle %s: N = Vergleich: %s" % (was, stand["N"] == stand["O"]))
        self.assertEqual(stand["N"], stand["O"])

    def test_kontrolle_spielstand_loeschen(self):
        self._kontrolle("spiel")

    def test_kontrolle_projekt_loeschen(self):
        self._kontrolle("projekt")


for _u in ("U1", "U3"):
    for _art in TABELLE:
        setattr(Loescharten, "test_%s_%s" % (_art, _u.lower()), _art_test(_u, _art))


# ------------------------------------------------------------- drei Geraete
class DreiGeraete(VollBasis):
    def lauf3(self, u, loescher, codes):
        d, e, neustart = s1.U_FAELLE[u]
        a = self.geraet("A", code=codes[0])
        b = self.geraet("B", "UTC", code=codes[1])
        c = self.geraet("C", "Asia/Tokyo", code=codes[2])
        a("ohne_start")
        self.zeit(0, A=d)
        for device in (a, b, c):
            device("lerne", 2, "vorher")
        for device in (a, b, c, a):
            device.sync()
        self.zeit(2.5, A=e)
        a = self.unsicher_machen(a, neustart)
        self.zeit(3.0, A=e)
        a("lerne", 2, "av")
        b("lerne", 2, "bv")
        c("lerne", 2, "cv")                        # C offline
        b.sync()
        self.zeit(3.4, A=e)
        self.assertTrue((a if loescher == "A" else b)("reset_all")["ok"])
        self.zeit(3.6, A=e)
        a("lerne", 2, "an")
        b("lerne", 2, "bn")
        c("lerne", 2, "cn")
        self.zeit(3.9, A=e)
        for device in (a, b, a, b, c, a, b, c):
            device.sync()
        self.ruhe((a, b, c))
        return {k: self.ergebnis("drei", (a, b, c), k)
                for k in ("a-av", "b-bv", "c-cv", "a-an", "b-bn", "c-cn")}

    def _alle(self, u, loescher, gerettet):
        alt = self.alt()
        stand = {}
        for codes in itertools.product((alt, None), repeat=3):
            name = "".join(self.codename(c) for c in codes)
            self.neuer_lauf(name)
            stand[name] = self.lauf3(u, loescher, codes)
            ta.bericht("DreiGeraete %s %s loescht %s: %s" % (u, loescher, name, stand[name]))
        fehler = []
        for name, zahlen in stand.items():
            for etikett, je in zahlen.items():
                for dev, n in je.items():
                    if n < stand["OOO"][etikett][dev]:
                        fehler.append((name, etikett, dev, n))
            if name[0] == "N":
                self.assertEqual(zahlen[gerettet], {"A": 2, "B": 2, "C": 2}, (name, zahlen))
        self.assertEqual(fehler, [])

    def test_u1_b_loescht_ohne_abgleich(self):
        self._alle("U1", "B", "a-an")

    def test_u3_a_loescht_ohne_abgleich(self):
        self._alle("U3", "A", "b-bn")


# ------------------------------------------------------------- Sonderfaelle
class Sonder(VollBasis):
    def bei(self, iso, **uhren):
        ziel = datetime.datetime.fromisoformat(iso).replace(tzinfo=UTC)
        self.zeit((ziel - self.jetzt).total_seconds() / HOUR, **uhren)

    def setUp(self):
        super().setUp()
        self.jetzt = datetime.datetime.now(UTC)

    def _u11(self, loescher, code):
        """Uhr von A 1 h vor, gemessen 24.10. 22:00 UTC; Programm ohne
        Kennung des Systemstarts neu gestartet (nicht feststellbar), Uhr
        weiter 1 h vor; A lernt 00:50 UTC (doppelte Stunde, erster
        Durchgang), loescher loescht 01:10 UTC, A und B lernen 01:20 UTC."""
        a = self.geraet("A", code=code)
        b = self.geraet("B", "UTC", code=code)
        a("ohne_start")
        self.bei("2026-10-24T22:00:00", A=HOUR)
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        for device in (a, b, a):
            device.sync()
        self.bei("2026-10-25T00:30:00", A=HOUR)
        a = self.neu_starten(a, ("ohne_start",))
        self.bei("2026-10-25T00:50:00", A=HOUR)
        a("lerne", 2, "av")
        b("lerne", 2, "bv")
        b.sync()
        self.bei("2026-10-25T01:10:00", A=HOUR)
        antwort = (a if loescher == "A" else b)("reset_all")
        self.bei("2026-10-25T01:20:00", A=HOUR)
        a("lerne", 2, "an")
        b("lerne", 2, "bn")
        self.bei("2026-10-25T01:35:00", A=HOUR)
        for device in (a, b, a, b):
            device.sync()
        self.ruhe((a, b))
        return self.zahlen((a, b), s1.ETIKETTEN), antwort.get("uhr_fix")

    def test_u11_doppelte_stunde(self):
        for loescher in "AB":
            stand = {}
            for code in (self.ref(), None):
                self.neuer_lauf(loescher + self.codename(code))
                stand[self.codename(code)] = self._u11(loescher, code)
                ta.bericht("U11 %s loescht %s: %s" % (loescher, self.codename(code),
                                                      stand[self.codename(code)]))
            zahlen, hinweis = stand["N"]
            for etikett in s1.ETIKETTEN:
                for dev in "AB":
                    self.assertGreaterEqual(zahlen[etikett][dev], stand["O"][0][etikett][dev],
                                            (loescher, etikett, dev))
            self.assertEqual(zahlen["a-an"], {"A": 2, "B": 2})
            self.assertEqual(zahlen["b-bn"], {"A": 2, "B": 2})
            if loescher == "A":
                # Uhr geht weiter 1 h vor, Marke korrigiert: Hinweis wahr
                self.assertLessEqual(abs(hinweis - HOUR), 120, hinweis)
                self.assertEqual(zahlen["b-bv"], {"A": 0, "B": 0})

    def _u9(self, art, code):
        a = self.geraet("A", code=code)
        b = self.geraet("B", "UTC", code=code)
        a("ohne_start")
        if art == "290":
            d, e, stellen, loeschen = 290.0, 290.0, 2.5, 3.4
        elif art == "alt":
            d, e, stellen, loeschen = TWO_H, TWO_H, 24.6, 25.4
        else:                                   # Zukunft: sofort richtig gestellt
            d, e, stellen, loeschen = TWO_H, 0.0, 0.1, 0.5
        self.zeit(0, A=d)
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        for device in (a, b, a):
            device.sync()
        self.zeit(stellen, A=e)
        a = self.neu_starten(a, ("ohne_start",))
        self.zeit(stellen + 0.1, A=e)
        a("lerne", 2, "av")
        b("lerne", 2, "bv")
        b.sync()
        self.zeit(loeschen, A=e)
        hinweis = a("reset_all").get("uhr_fix")
        self.zeit(loeschen + 0.1, A=e)
        a("lerne", 2, "an")
        b("lerne", 2, "bn")
        self.zeit(loeschen + 0.3, A=e)
        for device in (a, b, a, b):
            device.sync()
        self.ruhe((a, b))
        return self.zahlen((a, b), s1.ETIKETTEN), hinweis

    def test_u9_kontrollen_ohne_wirkung(self):
        for art in ("290", "alt", "zukunft"):
            stand = {}
            for code in (self.ref(), None):
                self.neuer_lauf(art + self.codename(code))
                stand[self.codename(code)] = self._u9(art, code)
            ta.bericht("U9 %s: N %s, Vergleich %s" % (art, stand["N"], stand["O"]))
            self.assertEqual(stand["N"], stand["O"], art)


# ------------------------------------------------------------------ Zufall
UHREN = (0.0, TWO_H, -TWO_H, 3 * HOUR)


def plan(seed):
    """Zufallsablauf: Liste von Schritten (geraet, befehl, wert)."""
    rnd = random.Random(seed)
    namen = "ABC"[:2 + (seed % 3 == 0)]
    schritte = [("*", "ohne_start", n) for n in namen if rnd.random() < 0.6]
    uhr = {n: rnd.choice(UHREN) for n in namen}
    schritte.append(("*", "uhr", dict(uhr)))
    for n in namen:
        schritte.append((n, "lerne", None))
    for n in namen:
        schritte.append((n, "sync", None))
    for _ in range(14):
        n = rnd.choice(namen)
        was = rnd.choice(("lerne", "lerne", "sync", "sync", "reset_all", "uhr", "neustart_p",
                          "neustart_s"))
        if was == "uhr":
            uhr[n] = rnd.choice(UHREN)
            schritte.append(("*", "uhr", dict(uhr)))
        else:
            schritte.append((n, was, None))
    return namen, schritte


class Zufall(VollBasis):
    def ablauf(self, seed, code):
        namen, schritte = plan(seed)
        zonen = {"A": "Europe/Berlin", "B": "UTC", "C": "Asia/Tokyo"}
        geraete = {n: self.geraet(n, zonen[n], code=code) for n in namen}
        t = 0.0
        uhr = {}
        nr = 0
        for geraet, was, wert in schritte:
            if geraet == "*" and was == "ohne_start":
                geraete[wert]("ohne_start")
                continue
            t += 0.2
            if was == "uhr":
                uhr = wert
                self.zeit(t, **uhr)
                continue
            self.zeit(t, **uhr)
            device = geraete[geraet]
            if was == "lerne":
                nr += 1
                device("lerne", 2, "s%02d" % nr)
            elif was == "sync":
                device.sync()
            elif was == "reset_all":
                device("reset_all")
            elif was == "neustart_p":
                geraete[geraet] = self.neu_starten(device, ("ohne_start",))
            elif was == "neustart_s":
                device("neustart")
        t += 0.2
        self.zeit(t, **uhr)
        for _ in range(2):
            for n in namen:
                geraete[n].sync()
        vorher = ta.commits()
        for _ in range(2):
            for n in namen:
                geraete[n].sync()
        unruhe = ta.commits() - vorher
        return {n: geraete[n].namen() for n in namen}, unruhe

    def test_26_zufallsablaeufe(self):
        ref = self.ref()
        fehler, mehr = [], 0
        for seed in range(1, 27):
            stand = {}
            for code in (ref, None):
                self.neuer_lauf("%02d%s" % (seed, self.codename(code)))
                stand[self.codename(code)] = self.ablauf(seed, code)
            n, o = stand["N"][0], stand["O"][0]
            for dev in n:
                for etikett in set(n[dev]) | set(o[dev]):
                    if n[dev].get(etikett, 0) < o[dev].get(etikett, 0):
                        fehler.append((seed, dev, etikett, n[dev].get(etikett, 0),
                                       o[dev].get(etikett, 0)))
                    elif n[dev].get(etikett, 0) > o[dev].get(etikett, 0):
                        mehr += 1
            ta.bericht("Zufall %02d: N %s (Hochladungen in Ruhe %d), Vergleich %s (%d)"
                       % (seed, stand["N"][0], stand["N"][1], stand["O"][0], stand["O"][1]))
        ta.bericht("Zufall: %d Etiketten mit N mehr als Vergleich, Fehler %s" % (mehr, fehler))
        self.assertEqual(fehler, [])


def tearDownModule():
    s1.tearDownModule()


if __name__ == "__main__":
    print("Code der Geraete: %s, Vergleich: %s" % (ta.CODE, os.environ.get("S1_REF_CODE")
                                                   or s1.ALT))
    unittest.main(verbosity=2)
