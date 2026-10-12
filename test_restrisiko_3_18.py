#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Restrisiken 3 und 18 aus dem Bericht 0.62.4 (Abschnitt 8) als Tests
(R-7 in 0.62.5 nachgestellt; ab 0.62.5 behoben, Entscheidung Nico 12.10.2026
"Beide beheben").

Restrisiko 3 (Uhr gestellt, alte Messung noch gueltig): Die Uhr von A ging
2 Stunden vor und wurde beim Abgleich gemessen. Spaeter stellt Nico die Uhr
richtig. Bis zu 24 Stunden nach der Messung (nach der Geraeteuhr) rechnet A
noch mit der alten Abweichung: Eine Loeschung auf A bekam eine Marke
2 Stunden zu frueh, ein eigener Eintrag lag 2 Stunden zu frueh. Bis 0.62.4
blieb dann ein Eintrag von B, der vor der Loeschung entstand; ein eigener
Eintrag von A nach einer Loeschung von B ging verloren.
Ab 0.62.5: Hat sich die gemessene Abweichung seit der letzten Messung um
mehr als 5 Minuten geaendert (die Uhr wurde gestellt), liest der Abgleich
eigene neue Marken und eigene noch nicht hochgeladene Eintraege, die die alte
Abweichung enthalten, mit der neuen Abweichung - wenn das zeitlich moeglich
ist (fisi_sync._undo_stale_correction).

Restrisiko 18 (Nachtrag trifft aeltere eigene Eintraege): A lernt offline mit
richtiger Uhr, danach geht die Uhr von A 2 Stunden vor. Bis 0.62.4 verschob
_correct_own_entries beim ersten Abgleich mit der neuen Abweichung auch
diesen aelteren Eintrag um 2 Stunden nach vorn; lag eine Loeschung von B
dazwischen, ging er verloren. Ab 0.62.5 traegt der Nachtrag die Abweichung
nur ein, wenn der Eintrag damit nicht vor die letzte Messung faellt (dann
kann er nicht mit der falschen Uhr entstanden sein).

Schutz-Tests: Was der Nachtrag schon richtig machte (Eintraege mit falscher
Uhr nach einer richtigen Messung, A-1 Lauf 2; bekannte Abweichung), bleibt.
Grenz-Tests halten fest, was nach dem Fix bewusst bleibt (siehe dort).

Jedes Geraet ist ein eigener Prozess mit eigener Wegwerf-Datenbank, eigenem
HOME und eigener Zeitzone; abgeglichen wird gegen die Attrappe auf 127.0.0.1
(Werkzeuge aus test_abgleich.py). Die Zeit laeuft ueber die verstellbare
Geraeteuhr und den Date-Kopf der Attrappe (wie test_03d). Keine echten Daten.

Gegen einen anderen Stand:  ABGLEICH_CODE=<ordner> python test_restrisiko_3_18.py
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

    def ruhe(self, geraete):
        """Zwei Runden nur Abgleich: nichts mehr hochladen (kein Hin und Her)."""
        vorher = ta.commits()
        for _ in range(2):
            for device in geraete:
                device.sync()
        self.assertEqual(ta.commits() - vorher, 0, "Hin und Her")

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
        self.ruhe((a, b))
        for device in (a, b):
            self.assertTrue(ta.ohne(device.namen(), "-vorher"), device.name)
        return marke_a, self.ergebnis("Risiko 3, Uhr vorher %+gs, gestellt nach %g h, "
                                      "Marke A %s" % (uhr_vorher, stunden_bis_stellen,
                                                      marke_a),
                                      (a, b), "b-fenster")

    def test_risiko_3_alte_messung_noch_gueltig(self):
        """Uhr +2 h gemessen, 3 h spaeter richtig gestellt (Messung 1 h alt,
        also noch gueltig): Die Loeschung greift wie ohne falsche Uhr.
        (Bis 0.62.4: {"A": 3, "B": 3}, Marke 2 h zu frueh - Restrisiko 3.)"""
        _, zahlen = self._risiko_3(TWO_H, 3)
        self.assertEqual(zahlen, {"A": 0, "B": 0})

    def test_risiko_3_vergleich_ohne_falsche_uhr(self):
        """Gleicher Ablauf, die Uhr von A ging nie falsch: Die Loeschung greift
        (wie in 0.62.3)."""
        _, zahlen = self._risiko_3(0.0, 3)
        self.assertEqual(zahlen, {"A": 0, "B": 0})

    def test_risiko_3_eigener_eintrag_nach_dem_stellen(self):
        """Uhr +2 h gemessen, 3 h spaeter richtig gestellt; B loescht vorher,
        A lernt danach offline. Der Eintrag bleibt wie ohne falsche Uhr.
        (Bis 0.62.4: {"A": 0, "B": 0} - _stamp rechnete die alte Abweichung
        ein, der Eintrag lag 2 h zu frueh und fiel unter Bs Loeschung.)"""
        a, b = self.geraet("A"), self.geraet("B", "UTC")
        self.zeit(0, A=TWO_H)
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        for device in (a, b, a):
            device.sync()                       # A misst +2 h
        self.zeit(2.5)                          # Uhr von A inzwischen gestellt
        b("reset_all")
        b.sync()
        self.zeit(3)
        a("lerne", 2, "nach")                   # NACH der Loeschung
        for device in (a, b, a):
            device.sync()
        self.ruhe((a, b))
        for device in (a, b):
            self.assertTrue(ta.ohne(device.namen(), "-vorher"), device.name)
        zahlen = self.ergebnis("Risiko 3, eigener Eintrag nach dem Stellen", (a, b), "a-nach")
        self.assertEqual(zahlen, {"A": 2, "B": 2})

    def test_risiko_3_mischbetrieb(self):
        """Wie Risiko 3, dazu ein Geraet mit 0.62.3 (O), das vor der Loeschung
        offline lernt: Die Loeschung greift auch dort, ohne Hin und Her."""
        alt = ta.code_stand("v0.62.3")
        if alt is None:
            if ta.IN_CI:
                self.fail("Code aus v0.62.3 nicht verfuegbar")
            self.skipTest("Code aus v0.62.3 nicht verfuegbar (git archive)")
        a, b = self.geraet("A"), self.geraet("B", "UTC")
        o = ta.Geraet(self.id().rsplit(".", 1)[-1], "O", "Europe/Berlin", alt)
        self.geraete.append(o)
        self.zeit(0, A=TWO_H)
        for device in (a, b, o):
            device("lerne", 2, "vorher")
        for device in (a, b, o, a):
            device.sync()                       # A misst +2 h
        self.zeit(3)                            # Uhr von A gestellt
        o("lerne", 3, "fenster")                # VOR der Loeschung
        o.sync()
        ta.pause()
        a("reset_all")
        for device in (a, b, o, a, b):
            device.sync()
        self.ruhe((a, b, o))
        for device in (a, b, o):
            self.assertTrue(ta.ohne(device.namen(), "-vorher"), device.name)
        zahlen = self.ergebnis("Risiko 3 Mischbetrieb", (a, b, o), "o-fenster")
        self.assertEqual(zahlen, {"A": 0, "B": 0, "O": 0})

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
        self.ruhe((a, b))
        for device in (a, b):
            self.assertTrue(ta.ohne(device.namen(), "-vorher"), device.name)
        return self.ergebnis("Risiko 18, Uhr danach %+gs" % uhr_danach, (a, b), "a-frueh")

    def test_risiko_18_aelterer_eigener_eintrag(self):
        """Eintrag nach der Loeschung, aber vor dem Verstellen der Uhr: Er
        bleibt wie ohne verstellte Uhr. (Bis 0.62.4: {"A": 0, "B": 0} - der
        Nachtrag verschob ihn 2 h nach vorn unter die Loeschung, Restrisiko 18.)"""
        zahlen = self._risiko_18(TWO_H)
        self.assertEqual(zahlen, {"A": 2, "B": 2})

    def test_risiko_18_vergleich_ohne_verstellte_uhr(self):
        """Gleicher Ablauf ohne verstellte Uhr: Der Eintrag bleibt."""
        zahlen = self._risiko_18(0.0)
        self.assertEqual(zahlen, {"A": 2, "B": 2})

    # ------------------------------------------------------------- Schutz
    def test_schutz_nachtrag_nach_richtiger_messung(self):
        """Was der Nachtrag richtig macht (A-1 Lauf 2, Test 3b): A misst mit
        richtiger Uhr, danach geht die Uhr +2 h vor, A lernt offline, B loescht
        danach. Beim ersten Abgleich traegt A die neue Abweichung nach: Die
        Eintraege von vor Bs Loeschung sind weg, was A danach lernt, bleibt."""
        a, b = self.geraet("A"), self.geraet("B", "UTC")
        self.zeit(0)
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        for device in (a, b, a):
            device.sync()
        self.zeit(0.5, A=TWO_H)
        a("lerne", 2, "fenster")                # VOR Bs Loeschung, Uhr falsch
        self.zeit(1, A=TWO_H)
        b("reset_all")
        b.sync()
        self.zeit(1.5, A=TWO_H)
        a.sync()                                # erste Messung der +2 h
        a("lerne", 2, "danach")                 # mit bekannter Abweichung
        for device in (b, a, b):
            device.sync()
        for device in (a, b):
            self.assertTrue(ta.ohne(device.namen(), "-vorher"), device.name)
        self.assertEqual(self.ergebnis("Schutz Nachtrag", (a, b), "a-fenster"),
                         {"A": 0, "B": 0})
        self.assertEqual(self.ergebnis("Schutz Nachtrag", (a, b), "a-danach"),
                         {"A": 2, "B": 2})

    def test_schutz_bekannte_abweichung(self):
        """Uhr von A geht die ganze Zeit +2 h vor und ist gemessen (kein
        Sprung): Was A vor Bs Loeschung lernt, ist weg, was danach kommt,
        bleibt (wie Test 3 "bekannt")."""
        a, b = self.geraet("A"), self.geraet("B", "UTC")
        self.zeit(0, A=TWO_H)
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        for device in (a, b, a):
            device.sync()
        self.zeit(1, A=TWO_H)
        a("lerne", 2, "vor")
        self.zeit(1.5, A=TWO_H)
        b("reset_all")
        b.sync()
        self.zeit(2, A=TWO_H)
        a("lerne", 2, "nach")
        self.zeit(2.5, A=TWO_H)
        for device in (a, b, a):
            device.sync()
        self.assertEqual(self.ergebnis("Schutz bekannt", (a, b), "a-vor"), {"A": 0, "B": 0})
        self.assertEqual(self.ergebnis("Schutz bekannt", (a, b), "a-nach"), {"A": 2, "B": 2})

    # ------------------------------------------------------------- Grenzen
    def _grenze_3(self, abgleich_nach):
        """A (+2 h, gemessen) loescht noch MIT falscher Uhr (Marke richtig),
        gleicht nicht ab; B lernt danach; dann wird As Uhr gestellt und A
        gleicht abgleich_nach Stunden nach der Messung ab."""
        a, b = self.geraet("A"), self.geraet("B", "UTC")
        self.zeit(0, A=TWO_H)
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        for device in (a, b, a):
            device.sync()
        self.zeit(1, A=TWO_H)
        a("reset_all")                          # Uhr noch falsch: Marke richtig
        self.zeit(1.5)
        b("lerne", 3, "fenster")                # NACH der Loeschung
        b.sync()
        self.zeit(abgleich_nach)                # As Uhr inzwischen gestellt
        for device in (a, b, a):
            device.sync()
        return self.ergebnis("Grenze 3, Abgleich nach %g h" % abgleich_nach, (a, b),
                             "b-fenster")

    def test_grenze_3_abgleich_bald_nach_dem_loeschen(self):
        """Gleicht A weniger als die Abweichung (2 h) nach dem Loeschen ab,
        kann die Marke nicht mit gestellter Uhr entstanden sein: Sie bleibt,
        Bs Eintraege nach der Loeschung bleiben."""
        self.assertEqual(self._grenze_3(2.5), {"A": 3, "B": 3})

    def test_grenze_3_abgleich_spaet_nach_dem_loeschen(self):
        """BEWUSST FESTGEHALTENE GRENZE des Fixes: Gleicht A erst mehr als 2 h
        nach dem Loeschen ab und wurde die Uhr dazwischen gestellt, ist nicht
        zu erkennen, ob vor oder nach dem Stellen geloescht wurde. Der Abgleich
        nimmt "nach dem Stellen" an (sonst bliebe Restrisiko 3): Die Marke
        liegt dann 2 h spaeter, Bs Eintraege aus diesen 2 h gehen verloren -
        so wie in 0.62.3, das die Ortszeit der falschen Uhr nahm.
        (0.62.4: {"A": 3, "B": 3}.)"""
        self.assertEqual(self._grenze_3(3.5), {"A": 0, "B": 0})

    def test_grenze_f6_uhr_nach_gestellt(self):
        """BEWUSST FESTGEHALTENE GRENZE (A-9 G1/F6, wie 0.62.4): Uhr von A
        geht 2 h NACH, gemessen; 3 h spaeter gestellt; A lernt, B loescht
        danach. Der Eintrag laege mit der alten Abweichung 2 h zu spaet und
        bleibt (die Loeschung greift fuer ihn nicht; kein Verlust). Eigene
        Eintraege werden nach einem Uhrsprung nur spaeter gelesen, nie
        frueher - frueher koennte einen Eintrag unter eine Loeschung schieben,
        der mit noch falscher Uhr richtig gestempelt war."""
        a, b = self.geraet("A"), self.geraet("B", "UTC")
        self.zeit(0, A=-TWO_H)
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        for device in (a, b, a):
            device.sync()
        self.zeit(3)
        a("lerne", 1, "x")
        self.zeit(3.5)
        b("reset_all")
        b.sync()
        for device in (a, b, a):
            device.sync()
        self.assertEqual(self.ergebnis("Grenze F6", (a, b), "a-x"), {"A": 1, "B": 1})


def tearDownModule():
    ta.SERVER.shutdown()
    shutil.rmtree(ta.WORK, ignore_errors=True)


if __name__ == "__main__":
    if os.name == "nt":
        print("test_restrisiko_3_18.py braucht Zeitzonen je Prozess (TZ) - nur Linux/macOS.")
        sys.exit(0)
    print("Code der Geraete: %s" % ta.CODE)
    unittest.main(verbosity=2)
