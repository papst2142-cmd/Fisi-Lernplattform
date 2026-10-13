#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Restrisiken S-5, S-6 und R-d aus dem Bericht 0.62.5 als Tests (Plan 0.63.2,
Teil S5 Abschnitt 5). Nur Nachstellung, kein Code-Fix.

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
letzten Messung, danach Uhr verstellt, dann erster Abgleich. Der Nachtrag
verschiebt den Eintrag (die Untergrenze an der letzten Messung greift nicht)
und er faellt unter eine Loeschung, die vor ihm lag. Als expectedFailure
festgehalten (Entscheidung Nico offen), dazu ein Grenz-Test mit dem
tatsaechlichen Verhalten.

Werkzeuge wie test_restrisiko_3_18.py (Geraete-Prozesse
pruefung/abgleich_geraet.py, Attrappe mit datum_versatz, Laufzeit-Uhr laeuft
nur mit der verstrichenen Zeit: aendert sich die Abweichung, wurde die Uhr
gestellt). Keine echten Uhren werden gestellt, keine echten Daten.

Gegen einen anderen Stand:  ABGLEICH_CODE=<ordner> python test_restrisiko_0632.py
Nur unter Linux/macOS (Zeitzone je Prozess ueber TZ).
"""

import datetime
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import unittest

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

    @unittest.expectedFailure
    def test_rd_eintrag_lange_nach_der_messung(self):
        """BEKANNTER FEHLER (R-d, Entscheidung Nico offen): A lernt mit
        richtiger Uhr 3 h nach der letzten Messung und 0,5 h nach Bs
        Loeschung; danach geht As Uhr 2 h vor. Beim ersten Abgleich schiebt
        der Nachtrag den Eintrag um 2 h nach vorn (Stunde 1, nicht vor die
        letzte Messung - die Untergrenze greift nicht), er faellt unter die
        Loeschung und geht auf beiden Geraeten verloren. Richtig waere
        {"A": 2, "B": 2}; tatsaechlich {"A": 0, "B": 0}
        (test_grenze_rd_eintrag_lange_nach_der_messung)."""
        self.assertEqual(self._rd(TWO_H), {"A": 2, "B": 2})

    def test_grenze_rd_eintrag_lange_nach_der_messung(self):
        """GRENZ-TEST: haelt das tatsaechliche Verhalten von R-d fest
        (Eintrag verloren). Wird R-d behoben, hier {"A": 2, "B": 2} eintragen
        und expectedFailure oben entfernen."""
        self.assertEqual(self._rd(TWO_H), {"A": 0, "B": 0})

    def test_rd_vergleich_ohne_verstellte_uhr(self):
        """Gleicher Ablauf ohne verstellte Uhr: Der Eintrag bleibt."""
        self.assertEqual(self._rd(0.0), {"A": 2, "B": 2})

    @unittest.expectedFailure
    def test_s6_rd_uhr_in_der_doppelten_stunde_falsch_gestellt(self):
        """BEKANNTER FEHLER (R-d am 25.10.): Uhr von A richtig (gemessen
        24.10. 22:00 UTC). B loescht 00:10 UTC. A lernt 00:20 UTC (02:20
        MESZ) mit richtiger Uhr, NACH der Loeschung. 00:40 UTC stellt jemand
        As Uhr 1 h vor (A zeigt 02:40 MEZ statt 02:40 MESZ - "Winterzeit von
        Hand"). Erster Abgleich 01:35 UTC: Der Nachtrag schiebt den Eintrag
        um 1 h nach vorn (23:20 UTC am 24.10.), unter die Loeschung - er geht
        verloren. Richtig waere {"A": 2, "B": 2}."""
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


def tearDownModule():
    ta.SERVER.shutdown()
    shutil.rmtree(ta.WORK, ignore_errors=True)


if __name__ == "__main__":
    if os.name == "nt":
        print("test_restrisiko_0632.py braucht Zeitzonen je Prozess (TZ) - nur Linux/macOS.")
        sys.exit(0)
    print("Code der Geraete: %s" % ta.CODE)
    unittest.main(verbosity=2)
