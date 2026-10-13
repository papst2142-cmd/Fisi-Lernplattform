#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Restrisiken S-5, S-6 und R-d aus dem Bericht 0.62.5 als Tests (Plan 0.63.2,
Teil S5 Abschnitt 5). Ab 0.63.2 ist R-d behoben (Plan-Nachtrag Abschnitt 4,
Weg A "mehrdeutig -> behalten", Freigabe F19/FG-57, Bauer S6b).

S-6 Doppelte Stunde am So 25.10.2026 (Ende der Sommerzeit, 03:00 MESZ ->
02:00 MEZ, also 01:00 UTC): Die Uhr eines Geraets geht genau 1 Stunde
falsch (gemessen) und wird IN der doppelten Stunde richtig gestellt. Ein
Eintrag von vor dem Stellen hat die Abweichung schon eingerechnet; er darf im
Nachtrag (fisi_sync._correct_own_entries) nicht wie unkorrigiert aussehen
(F5-Muster, Test 9e in test_abgleich.py). Die Geraete laufen mit echter
Zeitzone (TZ=Europe/Berlin bzw. UTC); die festen Zeitpunkte am 25.10.2026
werden in Abstaende zur echten Zeit umgerechnet, damit der Test vor und
nach dem 25.10. gleich laeuft.

S-5 Uhr in 24 h zweimal gestellt (+2 h -> richtig -> +2 h): Die Erkennung
(fisi_core.clock_deviation) rechnet Messung + Summe der Spruenge seit der
Messung.

R-d RR18-Rest: Eintrag mit richtiger Uhr mehr als die Abweichung nach der
letzten Messung, danach Uhr verstellt, dann erster Abgleich. Bis 0.63.1
verschob der Nachtrag den Eintrag (die Untergrenze an der letzten Messung
griff nicht), er fiel unter eine Loeschung, die vor ihm lag. Ab 0.63.2
verschiebt der Nachtrag bei vorgehender Uhr nur, was sicher nach dem Stellen
der Uhr entstand; Mehrdeutiges bleibt (RdWegATest, Tests 0 bis 4).

Werkzeuge wie test_restrisiko_3_18.py (Geraete-Prozesse
pruefung/abgleich_geraet.py, Attrappe mit datum_versatz, Laufzeit-Uhr laeuft
nur mit der verstrichenen Zeit: aendert sich die Abweichung, wurde die Uhr
gestellt). Keine echten Uhren werden gestellt, keine echten Daten.

Gegen einen anderen Stand:  ABGLEICH_CODE=<ordner> python test_restrisiko_0632.py
Nur unter Linux/macOS (Zeitzone je Prozess ueber TZ).
"""

import ast
import datetime
import itertools
import json
import os
import random
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

import test_abgleich as ta
import test_restrisiko_3_18 as rr

HOUR = 3600.0
TWO_H = 2 * HOUR
UTC = datetime.timezone.utc
# Toleranz fuer den Vergleich eines Zeitstempels mit der wahren Zeit: Alle
# Uhren laufen waehrend des Tests mit der echten Zeit weiter (Sekunden bis
# wenige Minuten); ein Fehler waere eine ganze Stunde.
STEMPEL_TOLERANZ = 600


def wahr(iso):
    """Fester Zeitpunkt (UTC) als datetime mit Zone."""
    return datetime.datetime.fromisoformat(iso).replace(tzinfo=UTC)


class Restrisiko0632Test(unittest.TestCase):
    # Werkzeuge aus test_restrisiko_3_18.py (ohne dessen Tests zu erben)
    setUp_rr = rr.RestrisikoTest.setUp
    tearDown = rr.RestrisikoTest.tearDown
    geraet = rr.RestrisikoTest.geraet
    zeit = rr.RestrisikoTest.zeit
    ruhe = rr.RestrisikoTest.ruhe
    ergebnis = rr.RestrisikoTest.ergebnis

    def setUp(self):
        self.setUp_rr()
        # Bezugspunkt: Geraete-Ziel - jetzt bzw. wahre Zeit - jetzt
        self.jetzt = datetime.datetime.now(UTC)

    # ------------------------------------------------------------ Werkzeuge
    def bei(self, iso, **uhren):
        """Wahre Zeit = iso (UTC) fuer GitHub und alle Geraete; uhren wie
        zeit() (Abweichung der Geraeteuhr in Sekunden)."""
        self.zeit((wahr(iso) - self.jetzt).total_seconds() / HOUR, **uhren)

    @staticmethod
    def zeilen(device, etikett):
        """(timestamp, utc_offset) der Karteikarten <etikett>-i auf device,
        direkt aus der Datenbank gelesen (Geraet wartet gerade)."""
        conn = sqlite3.connect(os.path.join(device.home, "lern.db"))
        try:
            return conn.execute("SELECT timestamp, utc_offset FROM card_events WHERE "
                                "question LIKE ? ORDER BY timestamp",
                                (etikett + "-%",)).fetchall()
        finally:
            conn.close()

    def stempel_pruefen(self, device, etikett, iso):
        """Ortszeit minus Abstand muss die wahre Zeit iso (UTC) sein."""
        rows = self.zeilen(device, etikett)
        self.assertTrue(rows, etikett)
        ziel = wahr(iso) + (datetime.datetime.now(UTC) - self.jetzt)
        for stamp, offset in rows:
            moment = datetime.datetime.strptime(stamp[:19], "%Y-%m-%d %H:%M:%S")
            utc = (moment - datetime.timedelta(minutes=offset)).replace(tzinfo=UTC)
            ta.bericht("Stempel %s: %s Abstand %+d min -> %s UTC (wahr ca. %s)"
                       % (etikett, stamp, offset, utc.strftime("%H:%M:%S"), iso[11:]))
            self.assertLessEqual(abs((utc - ziel).total_seconds()), STEMPEL_TOLERANZ,
                                 "%s: %s %+d" % (etikett, stamp, offset))
        return rows

    def ohne_doppelte(self, geraete):
        for device in geraete:
            tabellen = device("zaehle")["tabellen"]
            for name, werte in tabellen.items():
                self.assertEqual(werte["doppelt"], 0, "%s %s" % (device.name, name))
                self.assertEqual(werte["zeilen"], werte["uids"], "%s %s" % (device.name, name))

    def messung(self, device):
        """Gespeicherte Messung (Sekunden) fuer den Beleg."""
        value = device.marke("uhr_abweichung")
        return json.loads(value)["s"] if value else None

    # ------------------------------------------------------- S-6 doppelte Stunde
    def _doppelte_stunde(self, abweichung, e1, sprung, loeschung, nachher):
        """A (Europe/Berlin) geht abweichung Sekunden falsch, gemessen am
        24.10. 22:00 UTC; lernt e1 mit falscher Uhr; um sprung wird die Uhr
        richtig gestellt, A lernt e2; B (UTC) loescht um loeschung, lernt
        "nachher" um nachher; danach Abgleich A, B, A und Ruhe."""
        a, b = self.geraet("A"), self.geraet("B", "UTC")
        self.bei("2026-10-24T22:00:00", A=abweichung)   # 00:00 MESZ
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        for device in (a, b, a):
            device.sync()                               # A misst die Abweichung
        ta.bericht("S-6 Messung A: %s s" % self.messung(a))
        self.assertAlmostEqual(self.messung(a), abweichung, delta=60)
        ereignisse = sorted([(e1, "e1"), (sprung, "e2"), (loeschung, "loeschung"),
                             (nachher, "nachher")])
        gestellt = False
        for iso, was in ereignisse:
            if was == "e2":
                gestellt = True                         # Uhr von A richtig gestellt
            self.bei(iso, **({} if gestellt else {"A": abweichung}))
            if was in ("e1", "e2"):
                a("lerne", 2, was)
                self.stempel_pruefen(a, "a-" + was, iso)
            elif was == "loeschung":
                b("reset_all")
                b.sync()
            else:
                b("lerne", 2, "nachher")
        self.bei("2026-10-25T01:35:00")                 # 02:35 MEZ, erster Abgleich danach
        for device in (a, b, a):
            device.sync()
        self.ruhe((a, b))
        self.ohne_doppelte((a, b))
        for device in (a, b):
            self.assertTrue(ta.ohne(device.namen(), "-vorher"), device.name)
        return {etikett: self.ergebnis("S-6 Uhr %+gs" % abweichung, (a, b), etikett)
                for etikett in ("a-e1", "a-e2", "b-nachher")}

    def test_s6_nachgehende_uhr_in_der_doppelten_stunde_gestellt(self):
        """A geht 1 h nach (gemessen). 00:20 UTC (02:20 MESZ, A zeigt 01:20
        MESZ): e1. 01:10 UTC (02:10 MEZ): Uhr von A richtig gestellt (+1 h),
        e2. 01:30 UTC: B loescht. Beide Eintraege lagen vor der Loeschung."""
        z = self._doppelte_stunde(-HOUR, "2026-10-25T00:20:00", "2026-10-25T01:10:00",
                                  "2026-10-25T01:30:00", "2026-10-25T01:32:00")
        self.assertEqual(z, {"a-e1": {"A": 0, "B": 0}, "a-e2": {"A": 0, "B": 0},
                             "b-nachher": {"A": 2, "B": 2}})

    def test_s6_vorgehende_uhr_in_der_doppelten_stunde_gestellt(self):
        """Gespiegelt: A geht 1 h vor (gemessen). 00:20 UTC (02:20 MESZ, A
        zeigt 02:20 MEZ): e1. 01:10 UTC: Uhr von A um 1 h zurueckgestellt
        (03:10 MEZ -> 02:10 MEZ), e2. 01:30 UTC: B loescht."""
        z = self._doppelte_stunde(HOUR, "2026-10-25T00:20:00", "2026-10-25T01:10:00",
                                  "2026-10-25T01:30:00", "2026-10-25T01:32:00")
        self.assertEqual(z, {"a-e1": {"A": 0, "B": 0}, "a-e2": {"A": 0, "B": 0},
                             "b-nachher": {"A": 2, "B": 2}})

    def test_s6_vorgehende_uhr_gleicher_ortszeit_text(self):
        """A geht 1 h vor und wird um 00:40 UTC zurueckgestellt: vor dem
        Stellen zeigt A 02:40 MEZ (+01:00), danach 02:40 MESZ (+02:00) -
        derselbe Text. e1 kurz davor, e2 kurz danach; B loescht 00:50 UTC."""
        z = self._doppelte_stunde(HOUR, "2026-10-25T00:39:00", "2026-10-25T00:41:00",
                                  "2026-10-25T00:50:00", "2026-10-25T00:52:00")
        self.assertEqual(z, {"a-e1": {"A": 0, "B": 0}, "a-e2": {"A": 0, "B": 0},
                             "b-nachher": {"A": 2, "B": 2}})

    def test_s6_gleicher_ortszeit_text(self):
        """Der eigentliche F5-Fall: A geht 1 h nach (gemessen). 01:15:00 UTC
        zeigt A 02:15 MESZ (+02:00), lernt e1; 01:15:20 UTC loescht B;
        01:15:40 UTC wird As Uhr richtig gestellt, A zeigt 02:15 MEZ (+01:00)
        und lernt e2. Gleicher Ortszeit-Text, verschiedene Zone: e1 (vor der
        Loeschung) ist weg, e2 (danach) bleibt."""
        z = self._doppelte_stunde(-HOUR, "2026-10-25T01:15:00", "2026-10-25T01:15:40",
                                  "2026-10-25T01:15:20", "2026-10-25T01:16:00")
        self.assertEqual(z, {"a-e1": {"A": 0, "B": 0}, "a-e2": {"A": 2, "B": 2},
                             "b-nachher": {"A": 2, "B": 2}})

    # ----------------------------------------------------- S-5 zweimal gestellt
    def test_s5_zweimal_gestellt(self):
        """A misst +2 h (Stunde 0). Stunde 3: Uhr von A richtig gestellt, A
        lernt "mitte" (vor der Loeschung). Stunde 4: B loescht. Stunde 4,5:
        A lernt "mittenach" (Uhr noch richtig). Stunde 5: Uhr von A wieder
        +2 h, A lernt "spaet". Erst danach Abgleich. "mitte" ist weg,
        "mittenach" und "spaet" bleiben."""
        a, b = self.geraet("A"), self.geraet("B", "UTC")
        self.zeit(0, A=TWO_H)
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        for device in (a, b, a):
            device.sync()                       # A misst +2 h
        self.assertAlmostEqual(self.messung(a), TWO_H, delta=60)
        self.zeit(3)                            # richtig gestellt
        a("lerne", 2, "mitte")
        self.zeit(4)
        b("reset_all")
        b.sync()
        self.zeit(4.5)
        a("lerne", 2, "mittenach")
        self.zeit(5, A=TWO_H)                   # wieder +2 h
        a("lerne", 2, "spaet")
        for etikett in ("mitte", "mittenach", "spaet"):
            ta.bericht("S-5 Stempel a-%s: %s" % (etikett, self.zeilen(a, "a-" + etikett)))
        for device in (a, b, a):
            device.sync()
        self.ruhe((a, b))
        self.ohne_doppelte((a, b))
        for device in (a, b):
            self.assertTrue(ta.ohne(device.namen(), "-vorher"), device.name)
        z = {e: self.ergebnis("S-5 zweimal gestellt", (a, b), e)
             for e in ("a-mitte", "a-mittenach", "a-spaet")}
        self.assertEqual(z, {"a-mitte": {"A": 0, "B": 0}, "a-mittenach": {"A": 2, "B": 2},
                             "a-spaet": {"A": 2, "B": 2}})

    # ------------------------------------------------------------ R-d RR18-Rest
    def _rd(self, uhr_danach, loeschung=2.5, lernen=3.0, verstellt=3.5):
        """Messung Stunde 0 (A richtig), B loescht Stunde loeschung, A lernt
        "spaet" Stunde lernen (nach der Loeschung), Stunde verstellt geht A
        uhr_danach vor, erster Abgleich."""
        a, b = self.geraet("A"), self.geraet("B", "UTC")
        self.zeit(0)
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        for device in (a, b, a):
            device.sync()                       # Messung: Uhr von A richtig
        self.zeit(loeschung)
        b("reset_all")
        b.sync()
        self.zeit(lernen)
        a("lerne", 2, "spaet")                  # NACH der Loeschung
        self.zeit(verstellt, A=uhr_danach)
        a.sync()                                # erste Messung der neuen Abweichung
        ta.bericht("R-d Stempel a-spaet nach dem Abgleich: %s" % (self.zeilen(a, "a-spaet"),))
        b.sync()
        a.sync()
        self.ruhe((a, b))
        for device in (a, b):
            self.assertTrue(ta.ohne(device.namen(), "-vorher"), device.name)
        return self.ergebnis("R-d, Uhr danach %+gs" % uhr_danach, (a, b), "a-spaet")

    def test_rd_eintrag_lange_nach_der_messung(self):
        """R-d (behoben in 0.63.2): A lernt mit richtiger Uhr 3 h nach der
        letzten Messung und 0,5 h nach Bs Loeschung; danach geht As Uhr 2 h
        vor. Bis 0.63.1 schob der Nachtrag den Eintrag beim ersten Abgleich um
        2 h nach vorn unter die Loeschung ({"A": 0, "B": 0}). Ab 0.63.2 liegt
        er zwischen "sicher vor" und "sicher nach" dem Stellen (mehrdeutig)
        und bleibt, wie er ist."""
        self.assertEqual(self._rd(TWO_H), {"A": 2, "B": 2})

    def test_grenze_rd_eintrag_lange_nach_der_messung(self):
        """GRENZ-TEST (bewusst umgestellt in 0.63.2, FG-60): hielt bis 0.63.1
        das Verhalten von R-d fest ({"A": 0, "B": 0}, Eintrag verloren). Ab
        0.63.2 bleibt der Eintrag auf beiden Geraeten ({"A": 2, "B": 2});
        aendert sich das, faellt es hier auf."""
        self.assertEqual(self._rd(TWO_H), {"A": 2, "B": 2})

    def test_rd_vergleich_ohne_verstellte_uhr(self):
        """Gleicher Ablauf ohne verstellte Uhr: Der Eintrag bleibt."""
        self.assertEqual(self._rd(0.0), {"A": 2, "B": 2})

    def test_s6_rd_uhr_in_der_doppelten_stunde_falsch_gestellt(self):
        """R-d am 25.10. (behoben in 0.63.2, bis 0.63.1 e1 verloren): Uhr von A richtig (gemessen
        24.10. 22:00 UTC). B loescht 00:10 UTC. A lernt 00:20 UTC (02:20
        MESZ) mit richtiger Uhr, NACH der Loeschung. 00:40 UTC stellt jemand
        As Uhr 1 h vor (A zeigt 02:40 MEZ statt 02:40 MESZ - "Winterzeit von
        Hand"). Erster Abgleich 01:35 UTC: Bis 0.63.1 schob der Nachtrag den
        Eintrag um 1 h nach vorn (23:20 UTC am 24.10.), unter die Loeschung.
        Ab 0.63.2 ist er mehrdeutig und bleibt: {"A": 2, "B": 2}."""
        a, b = self.geraet("A"), self.geraet("B", "UTC")
        self.bei("2026-10-24T22:00:00")
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        for device in (a, b, a):
            device.sync()
        self.bei("2026-10-25T00:10:00")
        b("reset_all")
        b.sync()
        self.bei("2026-10-25T00:20:00")
        a("lerne", 2, "e1")
        self.stempel_pruefen(a, "a-e1", "2026-10-25T00:20:00")
        self.bei("2026-10-25T00:40:00", A=HOUR)        # Uhr von Hand 1 h vor
        a("lerne", 2, "e2")
        self.bei("2026-10-25T01:35:00", A=HOUR)
        a.sync()
        ta.bericht("S-6/R-d Stempel nach dem Abgleich: e1 %s, e2 %s"
                   % (self.zeilen(a, "a-e1"), self.zeilen(a, "a-e2")))
        b.sync()
        a.sync()
        self.ruhe((a, b))
        z = {e: self.ergebnis("S-6/R-d Uhr von Hand vor", (a, b), e) for e in ("a-e1", "a-e2")}
        self.assertEqual(z, {"a-e1": {"A": 2, "B": 2}, "a-e2": {"A": 2, "B": 2}})

    # ------------------------------------------- R-d Weg A (0.63.2), Tests 1 bis 4
    def _weg_a(self, ablauf, etikett, vorher_weg=True):
        """Gemeinsamer Rahmen: Messung Stunde 0 mit richtiger Uhr (A und B
        lernen "vorher", Abgleich A, B, A), dann ablauf(a, b) (endet mit dem
        ersten Abgleich von A), danach B, A und Ruhe. Liefert {A, B} fuer
        etikett. vorher_weg: "vorher" ist nach Bs Loeschung auf beiden weg
        (sonst nur Beleg)."""
        a, b = self.geraet("A"), self.geraet("B", "UTC")
        self.zeit(0)
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        for device in (a, b, a):
            device.sync()
        self.assertAlmostEqual(self.messung(a), 0, delta=60)
        ablauf(a, b)
        ta.bericht("R-d Weg A Stempel %s nach dem Abgleich: %s"
                   % (etikett, self.zeilen(a, etikett)))
        b.sync()
        a.sync()
        self.ruhe((a, b))
        self.ohne_doppelte((a, b))
        for device in (a, b):
            if vorher_weg:
                self.assertTrue(ta.ohne(device.namen(), "-vorher"), device.name)
        self.ergebnis("R-d Weg A", (a, b), "a-vorher")
        return self.ergebnis("R-d Weg A", (a, b), etikett)

    def test_rd_1_nachlauf_mehrdeutig_wie_heute(self):
        """(1) Uhr von A wird 2 h zurueckgestellt (Nachlauf). A lernt danach,
        NACH Bs Loeschung (Geraeteuhr zeigt etwa die Zeit der Messung, also
        mehrdeutig). Behalten heisst hier: verschieben (spaeter rucken), wie
        bis 0.63.1. Der Eintrag bleibt. (Wie bis 0.63.1 rueckt dabei auch
        As "vorher" spaeter, weil die Datei es nach Bs Loeschung nicht mehr
        kennt - es bleibt auf beiden Geraeten; nur Beleg, kein Verlust.)"""
        def ablauf(a, b):
            self.zeit(1, A=-TWO_H)              # Uhr 2 h zurueck
            self.zeit(1.5, A=-TWO_H)
            b("reset_all")
            b.sync()
            self.zeit(2, A=-TWO_H)
            a("lerne", 2, "spaet")
            self.zeit(2.5, A=-TWO_H)
            a.sync()
        self.assertEqual(self._weg_a(ablauf, "a-spaet", vorher_weg=False), {"A": 2, "B": 2})

    def test_grenze_rd_2_vorlauf_nach_dem_stellen_mehrdeutig(self):
        """(2) GRENZ-TEST (gewollt, F19): Uhr von A geht ab Stunde 0,1 2 h
        vor; A lernt Stunde 0,3 (mit falscher Uhr, also nach dem Stellen),
        B loescht Stunde 0,5, erster Abgleich von A Stunde 2,5. Der Eintrag
        liegt zwischen "sicher vor" und "sicher nach" dem Stellen und bleibt
        unverschoben: Er uebersteht die Loeschung, obwohl er in Wahrheit davor
        lag ("kommt zurueck" statt verloren; bis 0.63.1: {"A": 0, "B": 0})."""
        def ablauf(a, b):
            self.zeit(0.1, A=TWO_H)
            self.zeit(0.3, A=TWO_H)
            a("lerne", 2, "fenster")
            self.zeit(0.5, A=TWO_H)
            b("reset_all")
            b.sync()
            self.zeit(2.5, A=TWO_H)
            a.sync()
        self.assertEqual(self._weg_a(ablauf, "a-fenster"), {"A": 2, "B": 2})

    def _rd_3(self, neustart):
        def ablauf(a, b):
            self.zeit(0.5, A=TWO_H)
            self.zeit(1.0, A=TWO_H)
            a("lerne", 2, "fenster")            # mit falscher Uhr, vor Bs Loeschung
            self.zeit(1.2, A=TWO_H)
            b("reset_all")
            b.sync()
            if neustart:
                self.assertTrue(a("neustart")["ok"])
            self.zeit(1.5, A=TWO_H)
            a.sync()
        return self._weg_a(ablauf, "a-fenster")

    def test_rd_3_anderer_systemstart_alles_mehrdeutig(self):
        """(3) Wie der Schutz-Test "sicher nach" (unten), aber A wurde vor dem
        Abgleich neu gestartet (anderer Systemstart, die Laufzeit-Uhr bestaetigt
        den Sprung nicht): Der ganze Bereich ist mehrdeutig, nichts wird
        verschoben, der Eintrag bleibt (bis 0.63.1: {"A": 0, "B": 0})."""
        self.assertEqual(self._rd_3(True), {"A": 2, "B": 2})

    def test_rd_3_schutz_sicher_nach_wird_verschoben(self):
        """Schutz zu (3), gleicher Ablauf ohne Neustart: Der Eintrag entstand
        sicher nach dem Stellen (mit falscher Uhr) und vor Bs Loeschung - er
        bekommt die Abweichung und ist weg, wie bis 0.63.1."""
        self.assertEqual(self._rd_3(False), {"A": 0, "B": 0})

    def test_rd_4_zwei_spruenge(self):
        """(4) Muster S-5: Uhr von A Stunde 0,2 +2 h, Stunde 0,4 wieder
        richtig, B loescht Stunde 2,9, A lernt Stunde 3 mit richtiger Uhr,
        Stunde 3,5 wieder +2 h, erster Abgleich Stunde 4. Netto ein Sprung von
        2 h (fuer die Laufzeit-Uhr nicht unterscheidbar); der Eintrag ist
        mehrdeutig und bleibt (bis 0.63.1: {"A": 0, "B": 0})."""
        def ablauf(a, b):
            self.zeit(0.2, A=TWO_H)
            self.zeit(0.4)
            self.zeit(2.9)
            b("reset_all")
            b.sync()
            self.zeit(3.0)
            a("lerne", 2, "spaet")
            self.zeit(3.5, A=TWO_H)
            self.zeit(4.0, A=TWO_H)
            a.sync()
        self.assertEqual(self._weg_a(ablauf, "a-spaet"), {"A": 2, "B": 2})

    # ------------------------------------------------ R-d Mischbetrieb (T-b)
    def _rd_misch_ablauf(self, codes, lauf, uhr=TWO_H):
        """Plan-Nachtrag 4.4 (Mischbetrieb T-b mit verstellter Uhr), uebernommen
        aus gp_s6b skripte/rd_misch.py: A, B, C (C zeitweise offline) mit Code
        codes; B loescht, A und B lernen danach, As Uhr geht 2 h vor, A lernt
        nach dem Stellen, Abgleiche, C kommt zurueck."""
        ta.server_reset()
        for device in self.geraete:
            device.close()
        self.geraete, self.stand = [], {}
        geraete = []
        for name, tz, code in zip("ABC", ("Europe/Berlin", "UTC", "America/New_York"), codes):
            device = ta.Geraet("rdm_" + lauf, name, tz, code)
            self.geraete.append(device)
            self.stand[name] = [tz, 0.0, 0.0]
            geraete.append(device)
        a, b, c = geraete
        self.zeit(0)
        for device in (a, b, c):
            device("lerne", 2, "vorher")
        for device in (a, b, c, a, b):
            device.sync()
        self.zeit(1)
        c("lerne", 2, "offline")
        self.zeit(2.5)
        b("reset_all")
        b.sync()
        self.zeit(3)
        a("lerne", 2, "spaet")
        b("lerne", 2, "spaet")
        self.zeit(3.5, A=uhr)
        a("lerne", 2, "falsch")          # nach dem Stellen
        self.zeit(4, A=uhr)
        a.sync()
        b.sync()
        a.sync()
        self.zeit(4.5, A=uhr)
        c("lerne", 2, "zurueck")
        for _ in range(3):
            for device in (c, a, b):
                device.sync()
        return {device.name: device.namen() for device in (a, b, c)}

    def test_rd_mischbetrieb_t_b(self):
        """R-d im Mischbetrieb (Plan-Nachtrag 4.4, gp_s6b L3): alle 7
        Mischungen aus v0.63.1 und 0.63.2 auf A, B, C gegen denselben Ablauf
        nur mit v0.63.1 - kein Geraet hat weniger. Hat A 0.63.2 (A gleicht die
        eigene Uhr nach), bleibt a-spaet (vor dem Stellen gelernt) ueberall."""
        alt = ta.code_stand(BASIS)
        self.assertTrue(alt)
        stand_alt = self._rd_misch_ablauf((alt, alt, alt), "alt")
        ta.bericht("R-d Mischbetrieb nur v0.63.1: %s" % stand_alt)
        fehler = []
        for codes in itertools.product((alt, ta.CODE), repeat=3):
            if codes == (alt, alt, alt):
                continue
            name = "".join("n" if code == ta.CODE else "a" for code in codes)
            stand = self._rd_misch_ablauf(codes, name)
            ta.bericht("R-d Mischbetrieb %s (A,B,C; n=0.63.2): %s" % (name, stand))
            for dev in "ABC":
                fehlt = {k: n for k, n in stand_alt[dev].items() if stand[dev].get(k, 0) < n}
                if fehlt:
                    fehler.append((name, dev, fehlt))
                if codes[0] == ta.CODE:
                    self.assertEqual(stand[dev].get("a-spaet"), 2, (name, dev, stand[dev]))
        self.assertEqual(fehler, [])


class ZeitzoneTest(unittest.TestCase):
    def test_echte_zeitzone_berlin(self):
        """Die Geraete-Prozesse rechnen mit der echten Zeitzone (TZ):
        25.10.2026 00:30 UTC = 02:30 MESZ (+02:00), 01:30 UTC = 02:30 MEZ
        (+01:00) - die doppelte Stunde."""
        code = ("import datetime as d; u=d.timezone.utc\n"
                "for h in ('00:30','01:30'):\n"
                "    m=d.datetime.fromisoformat('2026-10-25T'+h).replace(tzinfo=u).astimezone()\n"
                "    print(m.isoformat())")
        out = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True,
                             text=True, env={"TZ": "Europe/Berlin",
                                             "PATH": os.environ.get("PATH", "")}).stdout
        ta.bericht("Europe/Berlin: %s" % out.split())
        self.assertEqual(out.split(), ["2026-10-25T02:30:00+02:00",
                                       "2026-10-25T02:30:00+01:00"])


# ============================================================================
#  R-d Weg A im Testprozess: Tests (0) und (0b), Vergleich mit 14b3bd4
# ============================================================================

BASIS = "v0.63.1"       # = 14b3bd4


class RdWegATest(unittest.TestCase):
    """Ruft fisi_sync._correct_own_entries direkt auf (Geraeteuhr,
    Laufzeit-Uhr und Systemstart nachgebildet) und vergleicht mit derselben
    Funktion aus 14b3bd4 (v0.63.1, git archive), ausgefuehrt mit denselben
    Hilfsfunktionen."""

    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp(prefix="fisi_rd_weg_a_")
        cls.env = {k: os.environ.get(k) for k in ("TZ", "FISI_DB_PATH")}
        os.environ["TZ"] = "Europe/Berlin"
        os.environ.setdefault("FISI_DB_PATH", os.path.join(cls.work, "start.db"))
        time.tzset()
        sys.path.insert(0, ta.CODE)
        try:
            import fisi_core
            import fisi_sync
        finally:
            sys.path.remove(ta.CODE)
        cls.core, cls.sync = fisi_core, fisi_sync
        basis = ta.code_stand(BASIS)
        if basis is None:
            cls.alt = None
            return
        with open(os.path.join(basis, "fisi_sync.py"), encoding="utf-8") as handle:
            text = handle.read()
        node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef)
                    and n.name == "_correct_own_entries")
        quelle = ast.get_source_segment(text, node).replace(
            "def _correct_own_entries(", "def _correct_own_entries_basis(", 1)
        exec(compile(quelle, "fisi_sync.py@" + BASIS, "exec"), fisi_sync.__dict__)
        cls.alt = staticmethod(fisi_sync._correct_own_entries_basis)
        db = fisi_core.DBManager(os.path.join(cls.work, "vorlage.db"),
                                 error_handler=lambda message: None)
        cls.vorlage = db.db_path

    @classmethod
    def tearDownClass(cls):
        for key, value in cls.env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        time.tzset()
        shutil.rmtree(cls.work, ignore_errors=True)

    def setUp(self):
        if self.alt is None:
            if ta.IN_CI:
                self.fail("Code aus %s nicht verfuegbar" % BASIS)
            self.skipTest("Code aus %s nicht verfuegbar (git archive)" % BASIS)

    # ------------------------------------------------------------ Werkzeuge
    def fall(self, name, eintraege, messung, jetzt_geraet, laufzeit, start="S1",
             prozess="P1"):
        """Datenbank mit eintraege [(Geraeteuhr UTC, Zusatz zum Abstand)] und
        messung (s, Geraeteuhr beim Messen UTC) oder None. Liefert eine
        Funktion lauf(funktion, J) -> Menge der verschobenen Nummern."""
        path = os.path.join(self.work, name + ".db")
        shutil.copyfile(self.vorlage, path)
        conn = sqlite3.connect(path)
        try:
            for nummer, (moment, zusatz) in enumerate(eintraege):
                local = moment.replace(tzinfo=UTC).astimezone()
                conn.execute("INSERT INTO card_events (timestamp, utc_offset, category, "
                             "question, mode, correct, uid) VALUES (?, ?, ?, ?, ?, ?, ?)",
                             (local.strftime("%Y-%m-%d %H:%M:%S"),
                              self.core.offset_minutes(local) + zusatz, "Kat",
                              "e-%d" % nummer, "karte", 1, "uid%d" % nummer))
            if messung is not None:
                conn.execute("INSERT INTO sync_meta (key, value) VALUES (?, ?)", (
                    self.core.CLOCK_KEY, json.dumps({
                        "s": messung[0],
                        "gemessen": messung[1].replace(tzinfo=UTC).astimezone().isoformat(),
                        "lauf": 1000.0, "start": "S1", "prozess": "P1"})))
            conn.commit()
        finally:
            conn.close()
        jetzt = jetzt_geraet.replace(tzinfo=UTC).astimezone()

        def lauf(funktion, deviation):
            kopie = path + ".%s.db" % funktion.__name__
            shutil.copyfile(path, kopie)
            db = self.core.DBManager(kopie, error_handler=lambda message: None)
            vorher = dict(sqlite3.connect(kopie).execute(
                "SELECT question, utc_offset FROM card_events").fetchall())
            with mock.patch.object(self.sync, "device_now", lambda: jetzt), \
                    mock.patch.object(self.core, "device_now", lambda: jetzt), \
                    mock.patch.object(self.core, "_boot_clock", lambda: 1000.0 + laufzeit), \
                    mock.patch.object(self.core, "_boot_id", lambda: start), \
                    mock.patch.object(self.core, "PROCESS_TOKEN", prozess):
                funktion(db, None, deviation)
            nachher = dict(sqlite3.connect(kopie).execute(
                "SELECT question, utc_offset FROM card_events").fetchall())
            return {q for q in vorher if nachher[q] != vorher[q]}
        return lauf

    # ------------------------------------------------------------ (0)
    def test_rd_0_teilmenge_und_nachlauf_wie_basis(self):
        """(0) 400 zufaellige Faelle (fester Startwert): Abweichung vor/nach,
        Messung fehlt/richtig/falsch und frisch/alt, Laufzeit-Uhr passend,
        widersprechend oder anderer Systemstart, Eintraege ueber 26 h (auch
        schon korrigierte). Die verschobenen Eintraege sind immer eine
        Teilmenge derer von 14b3bd4; bei nachgehender Uhr und ohne Messung
        genau dieselben (Vergleichstest "Nachlauf wie heute")."""
        zufall = random.Random(20261025)
        basis = datetime.datetime(2026, 10, 25, 0, 30)
        weniger = gleich = 0
        for nummer in range(400):
            wahr_jetzt = basis + datetime.timedelta(hours=zufall.uniform(-30, 30))
            j = zufall.choice((-1, 1)) * zufall.uniform(301, 2 * 86400)
            art = zufall.choice(("keine", "richtig", "richtig", "falsch"))
            s_vorher = (0.0 if art == "keine" else zufall.uniform(-250, 250)
                        if art == "richtig" else zufall.choice((-1, 1)) * zufall.uniform(
                            400, 2 * 86400))
            alter = zufall.uniform(0.05, 30) * HOUR       # wahre Zeit seit der Messung
            gemessen = (wahr_jetzt - datetime.timedelta(seconds=alter)
                        + datetime.timedelta(seconds=s_vorher))
            jetzt = wahr_jetzt + datetime.timedelta(seconds=j)
            uhr = zufall.choice(("passt", "passt", "widerspricht", "neustart"))
            laufzeit = alter + (zufall.uniform(600, 3 * HOUR) * zufall.choice((-1, 1))
                                if uhr == "widerspricht" else 0.0)
            eintraege = [(jetzt - datetime.timedelta(seconds=zufall.uniform(0, 26 * HOUR)),
                          zufall.choice((0,) * 9 + (60,))) for _ in range(25)]
            lauf = self.fall("f%d" % nummer, eintraege,
                             None if art == "keine" else (s_vorher, gemessen), jetzt,
                             max(laufzeit, 0.0), *(("S2", "P2") if uhr == "neustart" else ()))
            neu, alt = lauf(self.sync._correct_own_entries, j), lauf(self.alt, j)
            text = "Fall %d: J=%+.0f s, Messung %s s=%+.0f, Uhr %s" % (
                nummer, j, art, s_vorher, uhr)
            self.assertLessEqual(neu, alt, text)
            if j < 0 or art == "keine":
                self.assertEqual(neu, alt, text)
            weniger += neu < alt
            gleich += neu == alt
        ta.bericht("R-d (0): 400 Faelle, %d gleich wie 14b3bd4, %d mit weniger "
                   "verschobenen Eintraegen, 0 mit mehr" % (gleich, weniger))
        self.assertGreater(weniger, 20)     # die Regel greift wirklich

    # ------------------------------------------------------------ (0b)
    def test_rd_0b_ueberlappung_sicher_vor_gilt(self):
        """(0b) Kurzer Abstand bis zum Abgleich: Messung vor 1 h (wahre Zeit)
        mit richtiger Uhr, seitdem 2 h vorgestellt (Laufzeit-Uhr bestaetigt).
        "sicher vor" (T < Messung + 2 h) und "sicher nach" (T > jetzt - 2 h)
        ueberlappen; ein Eintrag dort bleibt (14b3bd4 verschob ihn). Ein
        Eintrag nur "sicher nach" wird wie bisher verschoben."""
        jetzt = datetime.datetime(2026, 10, 12, 12, 0)
        gemessen = jetzt - datetime.timedelta(hours=3)          # Geraeteuhr
        ueberlappt = gemessen + datetime.timedelta(hours=2)     # = jetzt - 1 h
        nach = jetzt - datetime.timedelta(minutes=10)
        lauf = self.fall("ueberlappung", [(ueberlappt, 0), (nach, 0)], (0.0, gemessen),
                         jetzt, HOUR)
        neu, alt = lauf(self.sync._correct_own_entries, TWO_H), lauf(self.alt, TWO_H)
        ta.bericht("R-d (0b): verschoben neu %s, 14b3bd4 %s" % (sorted(neu), sorted(alt)))
        self.assertEqual(alt, {"e-0", "e-1"})
        self.assertEqual(neu, {"e-1"})


def tearDownModule():
    ta.SERVER.shutdown()
    shutil.rmtree(ta.WORK, ignore_errors=True)


if __name__ == "__main__":
    if os.name == "nt":
        print("test_restrisiko_0632.py braucht Zeitzonen je Prozess (TZ) - nur Linux/macOS.")
        sys.exit(0)
    print("Code der Geraete: %s" % ta.CODE)
    unittest.main(verbosity=2)
