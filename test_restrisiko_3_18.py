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
Ab 0.62.5 (Entscheidung Nico 12.10.2026 12:03 UTC "sauber in 0.62.5"): Beim
Messen merkt sich das Geraet zusaetzlich den Stand einer Laufzeit-Uhr (seit
Systemstart, laeuft auch im Ruhezustand weiter, laesst sich nicht stellen)
und die Kennung von Systemstart und Prozess. Beim Stempeln (_stamp,
_marker_now ueber clock_deviation) zeigt der Vergleich mit der Laufzeit-Uhr,
ob und um wie viel die Uhr seit der Messung gestellt wurde. Ist sie danach
(gemessene Abweichung + Sprung) richtig (<= 5 Minuten), wird die alte
Abweichung nicht mehr eingerechnet. Sonst - Sprung zu einer weiter falschen
Uhr, Neustart des Systems (Sprung nicht feststellbar), Messung aus einem
aelteren Stand ohne die neuen Felder - wie 0.62.4. Der Behelf im Abgleich
(fisi_sync._undo_stale_correction, Commit 4528241) entfaellt und mit ihm der
neue Verlustweg R-a (test_grenze_3_abgleich_spaet_nach_dem_loeschen).

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
Geraeteuhr und den Date-Kopf der Attrappe (wie test_03d); die Laufzeit-Uhr
der Geraete laeuft mit der verstrichenen Zeit mit, nicht mit dem Stellen der
Uhr (Behelf in pruefung/abgleich_geraet.py, "uhr SEK LAUF"). Keine echten
Uhren werden gestellt, keine echten Daten.

Gegen einen anderen Stand:  ABGLEICH_CODE=<ordner> python test_restrisiko_3_18.py
Nur unter Linux/macOS (Zeitzone je Prozess ueber TZ).
"""

import datetime
import json
import os
import shutil
import sys
import time
import unittest
from unittest import mock

import test_abgleich as ta

HOUR = 3600.0
TWO_H = 2 * HOUR


class RestrisikoTest(unittest.TestCase):
    def setUp(self):
        ta.server_reset()
        self.geraete = []
        self.stand = {}         # Name -> [Zeitzone, Uhr (s), Laufzeit-Zusatz (s)]

    def tearDown(self):
        for geraet in self.geraete:
            geraet.close()

    def geraet(self, name, tz="Europe/Berlin"):
        device = ta.Geraet(self.id().rsplit(".", 1)[-1], name, tz)
        self.geraete.append(device)
        self.stand[name] = [tz, 0.0, 0.0]
        return device

    def zeit(self, stunden, **uhren):
        """Echte Zeit + stunden fuer GitHub und alle Geraete; uhren gibt je
        Geraet die zusaetzliche Abweichung seiner Uhr (Sekunden). Die
        Laufzeit-Uhr der Geraete laeuft nur mit der verstrichenen Zeit
        (stunden) mit: Aendert sich die Abweichung, wurde die Uhr gestellt."""
        ta.att.STATE.ctl["datum_versatz"] = stunden * HOUR
        for device in self.geraete:
            stand = self.stand.get(device.name)
            extra = stand[2] if stand else 0.0
            uhr = stunden * HOUR + uhren.get(device.name, 0.0)
            if stand:
                stand[1] = uhr
            device("uhr", uhr, stunden * HOUR + extra)

    def neu_starten(self, device, *befehle):
        """Programm auf device beenden und neu starten (gleiche Datenbank,
        gleiches HOME, gleicher Systemstart, gleiche Uhr); danach befehle."""
        tz, uhr, extra = self.stand[device.name]
        device.close()
        self.geraete.remove(device)
        neu = ta.Geraet(self.id().rsplit(".", 1)[-1], device.name, tz)
        self.geraete.append(neu)
        lauf = ta.att.STATE.ctl.get("datum_versatz", 0.0) + extra
        neu("uhr", uhr, lauf)
        for befehl in befehle:
            neu(*befehl)
        return neu

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
    def _risiko_3(self, uhr_vorher, stunden_bis_stellen, start=(), neustart=None):
        """start: Befehle an A gleich zu Beginn; neustart: None, oder Befehle
        nach einem Neustart des Programms auf A nach dem Stellen der Uhr."""
        a, b = self.geraet("A"), self.geraet("B", "UTC")
        for befehl in start:
            a(*befehl)
        self.zeit(0, A=uhr_vorher)
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        for device in (a, b, a):
            device.sync()                       # A misst seine Abweichung
        self.zeit(stunden_bis_stellen)          # Uhr von A richtig gestellt
        if neustart is not None:
            a = self.neu_starten(a, *neustart)
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

    def test_risiko_3_programm_neu_gestartet(self):
        """Wie Risiko 3, aber das Programm auf A wurde nach dem Stellen der Uhr
        neu gestartet (gleicher Systemstart): Die Kennung des Systemstarts
        (Linux, Android: /proc/sys/kernel/random/boot_id) zeigt, dass die
        Laufzeit-Uhr weiterlief - der Sprung wird erkannt."""
        if not os.path.exists("/proc/sys/kernel/random/boot_id"):
            self.skipTest("keine Kennung des Systemstarts (nur Linux)")
        _, zahlen = self._risiko_3(TWO_H, 3, neustart=())
        self.assertEqual(zahlen, {"A": 0, "B": 0})

    def test_risiko_3_ohne_startkennung_gleicher_prozess(self):
        """Wie Risiko 3 auf einem System ohne lesbare Kennung des
        Systemstarts (Windows, macOS), Programm nicht neu gestartet: Die
        Kennung des Prozesses genuegt, der Sprung wird erkannt."""
        _, zahlen = self._risiko_3(TWO_H, 3, start=[("ohne_start",)])
        self.assertEqual(zahlen, {"A": 0, "B": 0})

    def test_grenze_3_ohne_startkennung_neu_gestartet(self):
        """BEWUSST FESTGEHALTENE GRENZE: Ohne Kennung des Systemstarts
        (Windows, macOS) und nach einem Neustart des Programms ist nicht zu
        erkennen, ob die Laufzeit-Uhr weiterlief. Die Loeschmarke rechnet die
        gemessene Vorlauf-Abweichung dann weiter ein (bis 24 h wie 0.62.4; ab
        0.63.2 S-1 Behalten-Regel: Marke eher frueher): Bs Eintraege vor der
        Loeschung bleiben. Eigene Eintraege rechnen sie ab 0.63.2 nicht mehr
        ein (Gegentest P1: test_s1_0632.S1AblaufTest.
        test_risiko_3_eigener_eintrag_ohne_startkennung_neu_gestartet). Sicher
        statt ungewiss: ein Neustart des Systems mit weiter falscher Uhr darf
        die Abweichung nicht verlieren (test_neustart_bekannte_abweichung).
        Der PC gleicht beim Programmstart ab und misst dann neu.
        (4528241 mit Behelf im Abgleich: {"A": 0, "B": 0}, dafuer R-a.)"""
        _, zahlen = self._risiko_3(TWO_H, 3, start=[("ohne_start",)],
                                   neustart=[("ohne_start",)])
        self.assertEqual(zahlen, {"A": 3, "B": 3})

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
        """R-a aus 4528241 darf nicht entstehen: A loescht noch MIT falscher
        Uhr (Marke richtig, Messung gilt), die Uhr wird danach gestellt, A
        gleicht erst mehr als 2 h nach dem Loeschen ab. Die Marke bleibt, Bs
        Eintraege nach der Loeschung bleiben (wie 0.62.4). Der Uhrsprung wird
        beim Stempeln erkannt, nicht erst im Abgleich - die Marke von vor dem
        Stellen wird nicht mehr umgedeutet.
        (4528241: {"A": 0, "B": 0} - Verlustweg R-a.)"""
        self.assertEqual(self._grenze_3(3.5), {"A": 3, "B": 3})

    def test_risiko_f6_uhr_nach_gestellt(self):
        """A-9 G1/F6 (R-c aus 4528241): Uhr von A geht 2 h NACH, gemessen;
        3 h spaeter gestellt; A lernt, B loescht danach. Der Sprung wird beim
        Stempeln erkannt: Der Eintrag liegt richtig, die Loeschung greift.
        (0.62.4 und 4528241: {"A": 1, "B": 1} - der Eintrag lag mit der
        alten Abweichung 2 h zu spaet und blieb.)"""
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
        self.assertEqual(self.ergebnis("Risiko F6", (a, b), "a-x"), {"A": 0, "B": 0})


    # ------------------------------------------- Schutz: wie 0.62.4, wenn unsicher
    def _bekannte_abweichung_loeschen(self, nach_messung):
        """Uhr von A geht die ganze Zeit +2 h vor und ist gemessen. Nach der
        Messung nach_messung(a) (Neustart, alte Form der Messung ...). B lernt
        vor As Loeschung offline, danach lernen B und A weiter; A gleicht erst
        spaeter ab. Liefert die Zahlen fuer b-vor, b-nach und a-nach."""
        a, b = self.geraet("A"), self.geraet("B", "UTC")
        self.zeit(0, A=TWO_H)
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        for device in (a, b, a):
            device.sync()                       # A misst +2 h
        self.zeit(0.5, A=TWO_H)
        a = nach_messung(a)
        self.zeit(0.7, A=TWO_H)
        b("lerne", 3, "vor")                    # VOR der Loeschung, offline
        ta.pause()
        self.zeit(1, A=TWO_H)
        a("reset_all")                          # Marke mit bekannter Abweichung
        self.zeit(1.2, A=TWO_H)
        b("lerne", 3, "nach")                   # NACH der Loeschung
        b.sync()
        self.zeit(1.3, A=TWO_H)
        a("lerne", 2, "nach")                   # NACH der Loeschung
        self.zeit(2, A=TWO_H)
        for device in (a, b, a, b):
            device.sync()
        self.ruhe((a, b))
        return {etikett: self.ergebnis("Bekannte Abweichung", (a, b), etikett)
                for etikett in ("b-vor", "b-nach", "a-nach")}

    def test_neustart_bekannte_abweichung(self):
        """Neustart des Systems (neue Kennung des Systemstarts) mit weiter
        falscher Uhr: Ein Sprung ist nicht feststellbar, die Messung gilt wie
        in 0.62.4 weiter - die Marke liegt richtig, nichts nach der Loeschung
        geht verloren. Gegenprobe: Die Laufzeit-Uhr nach dem Neustart steht so,
        dass ein Vergleich ueber den Neustart hinweg "Uhr richtig gestellt"
        ergaebe (Marke dann 2 h in der Zukunft, auf GitHub-Zeit des Abgleichs
        gesetzt: b-nach und a-nach verloren)."""
        def neustart(a):
            self.stand["A"][2] = TWO_H
            a("neustart")
            self.zeit(0.5, A=TWO_H)
            return a
        zahlen = self._bekannte_abweichung_loeschen(neustart)
        self.assertEqual(zahlen, {"b-vor": {"A": 0, "B": 0}, "b-nach": {"A": 3, "B": 3},
                                  "a-nach": {"A": 2, "B": 2}})

    def test_alte_messung_ohne_neue_felder(self):
        """Eine Messung aus 0.62.4 (nur "s" und "gemessen", ohne Laufzeit-Uhr
        und Kennungen) gilt wie in 0.62.4: Die Marke liegt richtig."""
        def alte_form(a):
            messung = json.loads(a.marke("uhr_abweichung"))
            a("setmeta", "uhr_abweichung",
              json.dumps({"s": messung["s"], "gemessen": messung["gemessen"]}))
            return a
        zahlen = self._bekannte_abweichung_loeschen(alte_form)
        self.assertEqual(zahlen, {"b-vor": {"A": 0, "B": 0}, "b-nach": {"A": 3, "B": 3},
                                  "a-nach": {"A": 2, "B": 2}})

    def test_schutz_auf_weiter_falsche_uhr_gestellt(self):
        """Uhr +3 h gemessen, dann auf +1 h verstellt (weiter falsch, A-9 G2):
        Der Sprung ist erkannt, aber die Uhr geht danach nicht richtig - es
        bleibt bei der Messung wie 0.62.4 (Marke 2 h zu frueh: Bs Eintraege
        vor der Loeschung bleiben, Grenze wie Restrisiko 3). Wuerde die
        Messung stattdessen verworfen, laege die Marke 1 h zu spaet und Bs
        Eintraege nach der Loeschung gingen verloren - ein Verlustweg, den
        0.62.4 nicht hat."""
        a, b = self.geraet("A"), self.geraet("B", "UTC")
        self.zeit(0, A=3 * HOUR)
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        for device in (a, b, a):
            device.sync()                       # A misst +3 h
        self.zeit(0.5, A=HOUR)                  # auf +1 h verstellt
        self.zeit(2.7, A=HOUR)                  # Geraeteuhr wieder nach der Messung
        b("lerne", 3, "vor")
        ta.pause()
        self.zeit(3, A=HOUR)
        a("reset_all")
        ta.bericht("Marke A %s" % a.marke())
        self.zeit(3.2, A=HOUR)
        b("lerne", 3, "nach")
        b.sync()
        self.zeit(4.5, A=HOUR)
        for device in (a, b, a, b):
            device.sync()
        self.ruhe((a, b))
        for device in (a, b):
            self.assertTrue(ta.ohne(device.namen(), "-vorher"), device.name)
        self.assertEqual(self.ergebnis("Schutz weiter falsch", (a, b), "b-nach"),
                         {"A": 3, "B": 3})
        self.assertEqual(self.ergebnis("Schutz weiter falsch", (a, b), "b-vor"),
                         {"A": 3, "B": 3})

    def test_grenze_3_alte_messung_ohne_neue_felder(self):
        """BEWUSST FESTGEHALTENE GRENZE: Stammt die noch gueltige Messung aus
        0.62.4 (ohne Laufzeit-Uhr), ist ein Sprung nicht feststellbar - wie
        0.62.4 ({"A": 3, "B": 3}). Endet mit dem ersten Abgleich nach dem
        Update (neue Messung), spaetestens nach 24 h."""
        a, b = self.geraet("A"), self.geraet("B", "UTC")
        self.zeit(0, A=TWO_H)
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        for device in (a, b, a):
            device.sync()
        messung = json.loads(a.marke("uhr_abweichung"))
        a("setmeta", "uhr_abweichung",
          json.dumps({"s": messung["s"], "gemessen": messung["gemessen"]}))
        self.zeit(3)
        b("lerne", 3, "fenster")
        ta.pause()
        a("reset_all")
        for device in (a, b, a, b):
            device.sync()
        self.ruhe((a, b))
        self.assertEqual(self.ergebnis("Grenze 3 alte Messung", (a, b), "b-fenster"),
                         {"A": 3, "B": 3})


class UhrsprungKernTest(unittest.TestCase):
    """clock_deviation mit Laufzeit-Uhr (fisi_core, ab 0.62.5) ohne Geraete:
    Messung zur Laufzeit 1000 s im Systemstart S1, Prozess P1."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, ta.CODE)
        try:
            import fisi_core
        finally:
            sys.path.remove(ta.CODE)
        cls.core = fisi_core

    def abweichung(self, s, wand, laufzeit, start="S1", prozess="P1", jetzt_start="S1",
                   jetzt_prozess="P1", **felder):
        """s gemessen; wand/laufzeit = verstrichene Sekunden auf Geraeteuhr
        bzw. Laufzeit-Uhr seit der Messung; felder ersetzen gespeicherte
        Felder (... = Feld fehlt)."""
        core = self.core
        gemessen = datetime.datetime(2026, 10, 12, 10, 0, tzinfo=datetime.timezone.utc)
        data = {"s": s, "gemessen": gemessen.isoformat(), "lauf": 1000.0,
                "start": start, "prozess": prozess}
        data.update(felder)
        data = {k: v for k, v in data.items() if v is not ...}
        jetzt = gemessen + datetime.timedelta(seconds=wand)
        with mock.patch.object(core, "_boot_clock", lambda: 1000.0 + laufzeit), \
                mock.patch.object(core, "_boot_id", lambda: jetzt_start), \
                mock.patch.object(core, "PROCESS_TOKEN", jetzt_prozess):
            return core.clock_deviation(json.dumps(data), jetzt)

    def test_kein_sprung(self):
        self.assertEqual(self.abweichung(TWO_H, 3 * HOUR, 3 * HOUR), TWO_H)

    def test_vorgehende_uhr_richtig_gestellt(self):
        """Restrisiko 3: +2 h gemessen, um 2 h zurueckgestellt."""
        self.assertLessEqual(abs(self.abweichung(TWO_H, HOUR, 3 * HOUR)), 300)

    def test_nachgehende_uhr_richtig_gestellt(self):
        """A-9 F6: -2 h gemessen, um 2 h vorgestellt."""
        self.assertLessEqual(abs(self.abweichung(-TWO_H, 5 * HOUR, 3 * HOUR)), 300)

    def test_auf_weiter_falsche_uhr_gestellt(self):
        """+1 h gemessen, auf +3 h verstellt (A-9 G2): wie 0.62.4."""
        self.assertEqual(self.abweichung(HOUR, 5 * HOUR, 3 * HOUR), HOUR)

    def test_schwelle_danach(self):
        """Nach dem Stellen noch 290 s daneben: richtig; 310 s: weiter falsch."""
        self.assertEqual(self.abweichung(TWO_H, 3 * HOUR - TWO_H + 290, 3 * HOUR), 290)
        self.assertEqual(self.abweichung(TWO_H, 3 * HOUR - TWO_H + 310, 3 * HOUR), TWO_H)

    def test_schwelle_sprung(self):
        """Ein Sprung bis 300 s ist keiner (Gangabweichung, Stellen um
        Sekunden): 400 s gemessen, 290 s zurueck -> 400 bleibt."""
        self.assertEqual(self.abweichung(400, 3 * HOUR - 290, 3 * HOUR), 400)
        self.assertLessEqual(abs(self.abweichung(400, 3 * HOUR - 310, 3 * HOUR)), 300)

    def test_anderer_systemstart(self):
        """Neustart des Systems: Laufzeit-Uhr nicht vergleichbar - wie 0.62.4."""
        self.assertEqual(self.abweichung(TWO_H, HOUR, 3 * HOUR, jetzt_start="S2",
                                         jetzt_prozess="P2"), TWO_H)

    def test_gleicher_systemstart_anderer_prozess(self):
        self.assertLessEqual(abs(self.abweichung(TWO_H, HOUR, 3 * HOUR,
                                                 jetzt_prozess="P2")), 300)

    def test_ohne_startkennung(self):
        """Ohne Kennung des Systemstarts: nur im selben Prozess."""
        self.assertLessEqual(abs(self.abweichung(TWO_H, HOUR, 3 * HOUR, start=None,
                                                 jetzt_start=None)), 300)
        self.assertEqual(self.abweichung(TWO_H, HOUR, 3 * HOUR, start=None,
                                         jetzt_start=None, jetzt_prozess="P2"), TWO_H)

    def test_alte_messung_ohne_felder(self):
        """Messung aus 0.62.4: wie 0.62.4."""
        self.assertEqual(self.abweichung(TWO_H, HOUR, 3 * HOUR, lauf=..., start=...,
                                         prozess=...), TWO_H)

    def test_unlesbare_felder(self):
        self.assertEqual(self.abweichung(TWO_H, HOUR, 3 * HOUR, lauf="x"), TWO_H)
        self.assertEqual(self.abweichung(TWO_H, HOUR, 3 * HOUR, lauf=None), TWO_H)

    def test_laufzeit_rueckwaerts(self):
        """Laufzeit-Uhr kleiner als beim Messen (kann nur ein anderer
        Systemstart sein): wie 0.62.4."""
        self.assertEqual(self.abweichung(-TWO_H, 6700, -500.0), -TWO_H)

    def test_alter_bleibt(self):
        """Weiter wie 0.62.4: aelter als 24 h oder in der Zukunft -> None."""
        self.assertIsNone(self.abweichung(TWO_H, 25 * HOUR, 25 * HOUR))
        self.assertIsNone(self.abweichung(TWO_H, -60, 3 * HOUR))

    def test_messung_schreiben(self):
        """clock_measurement schreibt s, gemessen, Laufzeit und Kennungen;
        gleich danach gilt die Messung."""
        core = self.core
        value = core.clock_measurement(TWO_H)
        data = json.loads(value)
        self.assertEqual(set(data), {"s", "gemessen", "lauf", "start", "prozess"})
        self.assertEqual(data["prozess"], core.PROCESS_TOKEN)
        self.assertEqual(core.clock_deviation(value), TWO_H)

    def test_laufzeit_uhr(self):
        """Linux/Android: Laufzeit-Uhr mit Ruhezustand (CLOCK_BOOTTIME)."""
        if not hasattr(time, "CLOCK_BOOTTIME"):
            self.skipTest("nur Linux")
        self.assertAlmostEqual(self.core._boot_clock(),
                               time.clock_gettime(time.CLOCK_BOOTTIME), delta=1.0)


def tearDownModule():
    ta.SERVER.shutdown()
    shutil.rmtree(ta.WORK, ignore_errors=True)


if __name__ == "__main__":
    if os.name == "nt":
        print("test_restrisiko_3_18.py braucht Zeitzonen je Prozess (TZ) - nur Linux/macOS.")
        sys.exit(0)
    print("Code der Geraete: %s" % ta.CODE)
    unittest.main(verbosity=2)
