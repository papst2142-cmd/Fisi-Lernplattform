#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Restrisiken 3 und 18 aus dem Bericht 0.62.4 (Abschnitt 8) als Tests
nachgestellt (ab 0.62.5, R-7). NUR Tests: fisi_sync.py bleibt, wie es ist.

Die Tests halten das HEUTIGE Verhalten fest (Zusicherung auf das, was der Code
tatsaechlich tut), damit eine spaetere Aenderung an der Uhr-Korrektur sichtbar
wird. Ob das Verhalten so bleiben soll, entscheidet Nico.

Restrisiko 3 (Uhr gestellt, alte Messung noch gueltig): Die Uhr von A ging
2 Stunden vor und wurde beim Abgleich gemessen. Spaeter stellt Nico die Uhr
richtig. Bis zu 24 Stunden nach der Messung (nach der Geraeteuhr) rechnet A
noch mit der alten Abweichung: Eine Loeschung auf A bekommt eine Marke
2 Stunden zu frueh. Ein Eintrag von B, der vor der Loeschung entstand, bleibt.

Restrisiko 18 (Nachtrag trifft aeltere eigene Eintraege): A lernt offline mit
richtiger Uhr, danach geht die Uhr von A 2 Stunden vor. Beim ersten Abgleich
mit der neuen Abweichung verschiebt _correct_own_entries auch diesen aelteren
Eintrag um 2 Stunden nach vorn. Lag eine Loeschung von B zwischen der
verschobenen und der echten Zeit, wird der Eintrag geloescht, obwohl er
nach der Loeschung entstand.

Jedes Geraet ist ein eigener Prozess mit eigener Wegwerf-Datenbank, eigenem
HOME und eigener Zeitzone; abgeglichen wird gegen die Attrappe auf 127.0.0.1
(Werkzeuge aus test_abgleich.py). Die Zeit laeuft ueber die verstellbare
Geraeteuhr und den Date-Kopf der Attrappe (wie test_03d). Keine echten Daten.

Gegen einen anderen Stand:  ABGLEICH_CODE=<ordner> python test_restrisiko_3_18.py
(Auf v0.62.3 sind 4 der 5 Tests rot: Dort gibt es keine Uhr-Korrektur, die
Loeschung greift in Risiko 3; Risiko 18 scheitert dort schon an "vorher",
weil v0.62.3 Zeitzonen nicht vergleicht, B-G-24.)
Nur unter Linux/macOS (Zeitzone je Prozess ueber TZ).
"""

import os
import shutil
import sys
import unittest

import test_abgleich as ta

HOUR = 3600.0
TWO_H = 2 * HOUR


class RestrisikoTest(unittest.TestCase):
    def setUp(self):
        ta.server_reset()
        self.geraete = []

    def tearDown(self):
        for geraet in self.geraete:
            geraet.close()

    def geraet(self, name, tz="Europe/Berlin"):
        device = ta.Geraet(self.id().rsplit(".", 1)[-1], name, tz)
        self.geraete.append(device)
        return device

    def zeit(self, stunden, **uhren):
        """Echte Zeit + stunden fuer GitHub und alle Geraete; uhren gibt je
        Geraet die zusaetzliche Abweichung seiner Uhr (Sekunden)."""
        ta.att.STATE.ctl["datum_versatz"] = stunden * HOUR
        for device in self.geraete:
            device("uhr", stunden * HOUR + uhren.get(device.name, 0.0))

    def ergebnis(self, text, geraete, etikett):
        zahlen = {d.name: d.namen().get(etikett, 0) for d in geraete}
        ta.bericht("%s: %s = %s" % (text, etikett, zahlen))
        return zahlen

    # ------------------------------------------------------------ Restrisiko 3
    def _risiko_3(self, uhr_vorher, stunden_bis_stellen):
        a, b = self.geraet("A"), self.geraet("B", "UTC")
        self.zeit(0, A=uhr_vorher)
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        for device in (a, b, a):
            device.sync()                       # A misst seine Abweichung
        self.zeit(stunden_bis_stellen)          # Uhr von A richtig gestellt
        b("lerne", 3, "fenster")                # B lernt offline, VOR der Loeschung
        ta.pause()
        a("reset_all")                          # Loeschung auf A
        marke_a = a.marke()
        for device in (a, b, a, b):
            device.sync()
        for device in (a, b):
            self.assertTrue(ta.ohne(device.namen(), "-vorher"), device.name)
        return marke_a, self.ergebnis("Risiko 3, Uhr vorher %+gs, gestellt nach %g h, "
                                      "Marke A %s" % (uhr_vorher, stunden_bis_stellen,
                                                      marke_a),
                                      (a, b), "b-fenster")

    def test_risiko_3_alte_messung_noch_gueltig(self):
        """Uhr +2 h gemessen, 3 h spaeter richtig gestellt (Messung 1 h alt,
        also gueltig): Bs Eintraege von VOR der Loeschung bleiben.
        Heutiges Verhalten = Restrisiko 3 bestaetigt."""
        _, zahlen = self._risiko_3(TWO_H, 3)
        self.assertEqual(zahlen, {"A": 3, "B": 3})

    def test_risiko_3_vergleich_ohne_falsche_uhr(self):
        """Gleicher Ablauf, die Uhr von A ging nie falsch: Die Loeschung greift
        (wie in 0.62.3)."""
        _, zahlen = self._risiko_3(0.0, 3)
        self.assertEqual(zahlen, {"A": 0, "B": 0})

    def test_risiko_3_sofort_gestellt(self):
        """Uhr +2 h gemessen und gleich danach richtig gestellt: Die Messung
        liegt dann nach der Geraeteuhr in der Zukunft und gilt nicht mehr
        (clock_deviation, Alter < 0). Die Loeschung greift."""
        _, zahlen = self._risiko_3(TWO_H, 0)
        self.assertEqual(zahlen, {"A": 0, "B": 0})

    # ----------------------------------------------------------- Restrisiko 18
    def _risiko_18(self, uhr_danach):
        a, b = self.geraet("A"), self.geraet("B", "UTC")
        self.zeit(0)
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        for device in (a, b, a):
            device.sync()                       # Messung: Uhr von A richtig
        self.zeit(0.5)
        b("reset_all")                          # Loeschung auf B
        b.sync()
        self.zeit(1)
        a("lerne", 2, "frueh")                  # A lernt offline, NACH der Loeschung
        self.zeit(1.5, A=uhr_danach)            # Uhr von A geht jetzt vor
        a.sync()                                # erste Messung der neuen Abweichung
        b.sync()
        a.sync()
        for device in (a, b):
            self.assertTrue(ta.ohne(device.namen(), "-vorher"), device.name)
        return self.ergebnis("Risiko 18, Uhr danach %+gs" % uhr_danach, (a, b), "a-frueh")

    def test_risiko_18_aelterer_eigener_eintrag(self):
        """Eintrag nach der Loeschung, aber vor dem Verstellen der Uhr: Der
        Nachtrag verschiebt ihn 2 h nach vorn, er faellt unter die Loeschung
        und ist auf beiden Geraeten weg. Heutiges Verhalten = Restrisiko 18
        bestaetigt."""
        zahlen = self._risiko_18(TWO_H)
        self.assertEqual(zahlen, {"A": 0, "B": 0})

    def test_risiko_18_vergleich_ohne_verstellte_uhr(self):
        """Gleicher Ablauf ohne verstellte Uhr: Der Eintrag bleibt."""
        zahlen = self._risiko_18(0.0)
        self.assertEqual(zahlen, {"A": 2, "B": 2})


def tearDownModule():
    ta.SERVER.shutdown()
    shutil.rmtree(ta.WORK, ignore_errors=True)


if __name__ == "__main__":
    if os.name == "nt":
        print("test_restrisiko_3_18.py braucht Zeitzonen je Prozess (TZ) - nur Linux/macOS.")
        sys.exit(0)
    print("Code der Geraete: %s" % ta.CODE)
    unittest.main(verbosity=2)
