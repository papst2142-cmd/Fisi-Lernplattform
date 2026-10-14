#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer FG-116 (ab 0.63.2): Gleichstand einer Loeschmarke in zwei
Schreibweisen.

Befund N14 (Weisung 44, 2.5): Haben zwei Geraete dieselbe Loeschmarke in
derselben UTC-Sekunde, aber verschieden geschrieben (z.B. "...17:34:47+02:00"
und "...15:34:47+00:00"), behielt fisi_sync._later bei Gleichstand die eigene
Marke, und die Ruhepruefung in sync() vergleicht die Marken als Text. Jedes
Geraet lud dann bei jedem Abgleich seine Schreibweise wieder hoch (kein
Datenverlust, aber ein Hin und Her ohne Ende; seit mindestens v0.63.1).

Mit FG-116 gilt bei Gleichstand die Marke der Abgleich-Datei. Geprueft wird
mit echten Geraeteprozessen gegen die Attrappe (wie test_abgleich.py):
  * zwei neue Geraete, beide Reihenfolgen: nach dem Angleichen keine
    Hochladung mehr, beide Geraete und die Datei haben dieselbe Schreibweise,
    Eintraege wie vorher (nichts verloren, nichts zurueck);
  * eine schon vorhandene Marke in der "anderen" Schreibweise auf dem Geraet
    (Stand nach dem Update): ein Abgleich, danach Ruhe;
  * Eintraege ohne utc_offset (Text-Vergleich) zwischen den beiden
    Ortszeiten: beide Geraete enden mit denselben Eintraegen;
  * Mischbetrieb mit v0.63.1 (alter Code behaelt die eigene Marke) und mit
    v0.62.3 (Textvergleich): Ruhe nach dem Angleichen.

Nur unter Linux/macOS (Zeitzone je Prozess ueber TZ).
Start:  python test_abgleich_gleichstand_0632.py
"""

import datetime
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import test_abgleich as ta  # noqa: E402

UTC = datetime.timezone.utc
BERLIN = datetime.timezone(datetime.timedelta(hours=2))


def marke_jetzt(minuten=10):
    """Eine Marke in der Vergangenheit (volle Sekunde), in UTC und in +02:00
    geschrieben - derselbe Zeitpunkt. Ab Ende Oktober hat Berlin +01:00; die
    Marke wird deshalb fest mit +02:00 geschrieben (die Zone der Marke muss
    nicht die des Geraets sein)."""
    moment = (datetime.datetime.now(UTC) - datetime.timedelta(minutes=minuten)
              ).replace(microsecond=0)
    return moment, moment.isoformat(" "), moment.astimezone(BERLIN).isoformat(" ")


class GleichstandTest(unittest.TestCase):
    def setUp(self):
        ta.server_reset()
        self.geraete = []

    def tearDown(self):
        for geraet in self.geraete:
            geraet.close()

    def geraet(self, name, tz="Europe/Berlin", code=ta.CODE):
        device = ta.Geraet(self.id().rsplit(".", 1)[-1], name, tz, code)
        self.geraete.append(device)
        return device

    def alter_code(self, tag):
        folder = ta.code_stand(tag)
        if folder is None:
            if ta.IN_CI:
                self.fail("Code aus %s nicht verfuegbar" % tag)
            self.skipTest("Code aus %s nicht verfuegbar (git archive)" % tag)
        return folder

    def ruhe(self, geraete, runden=2):
        vorher = ta.commits()
        for _ in range(runden):
            for device in geraete:
                device.sync()
        return ta.commits() - vorher

    def _ablauf(self, a, b, marke_a, marke_b, moment):
        """A und B lernen und gleichen ab, dann bekommen beide dieselbe Marke
        in zwei Schreibweisen (wie eine schon vorhandene Marke); dazu je ein
        Eintrag vor der Marke (mit Abstand, faellt weg) und Eintraege nach
        ihr (bleiben). Liefert die Hochladungen der Ruherunden."""
        a("lerne", 2, "nach")
        b("lerne", 2, "nach")
        vor = moment - datetime.timedelta(minutes=30)
        a("eintrag", "vor", vor.astimezone(BERLIN).strftime("%Y-%m-%d %H:%M:%S"), 120)
        b("eintrag", "vor", vor.strftime("%Y-%m-%d %H:%M:%S"), 0)
        for device in (a, b, a, b):
            device.sync()
        a("setmeta", "reset_at", marke_a)
        b("setmeta", "reset_at", marke_b)
        # Angleichen: hoechstens je ein Abgleich mit Hochladung
        for device in (a, b, a, b):
            device.sync()
        return self.ruhe([a, b])

    def _pruefe_ende(self, a, b, hochladungen, soll_namen):
        datei = ta.datei().get("markers", {}).get("reset_at")
        ta.bericht("%s: Ruhe %d Hochladungen, Marke A %s, B %s, Datei %s" % (
            self.id().rsplit(".", 1)[-1], hochladungen, a.marke(), b.marke(), datei))
        self.assertEqual(hochladungen, 0, "Hin und Her: Hochladungen in Ruhe")
        self.assertEqual(a.marke(), datei)
        self.assertEqual(b.marke(), datei)
        self.assertEqual(a.namen(), soll_namen)
        self.assertEqual(b.namen(), soll_namen)

    def test_gleichstand_zwei_schreibweisen(self):
        """Gleiche UTC-Sekunde, A "+02:00", B "+00:00" (und umgekehrt):
        nach dem Angleichen keine Hochladung mehr, dieselbe Schreibweise
        ueberall, Eintraege nach der Marke bleiben, vor ihr fallen weg."""
        for nr, umgekehrt in enumerate((False, True)):
            with self.subTest(umgekehrt=umgekehrt):
                ta.server_reset()
                moment, utc_text, berlin_text = marke_jetzt()
                a = self.geraet("A%d" % nr, "Europe/Berlin")
                b = self.geraet("B%d" % nr, "UTC")
                marke_a, marke_b = ((utc_text, berlin_text) if umgekehrt
                                    else (berlin_text, utc_text))
                hochladungen = self._ablauf(a, b, marke_a, marke_b, moment)
                self._pruefe_ende(a, b, hochladungen,
                                  {"a%d-nach" % nr: 2, "b%d-nach" % nr: 2})

    def test_vorhandene_marke_andere_schreibweise(self):
        """Datei hat schon "+00:00", das Geraet noch "+02:00" (Stand nach dem
        Update): ein Abgleich gleicht an, danach Ruhe; die Datei behaelt ihre
        Schreibweise."""
        moment, utc_text, berlin_text = marke_jetzt()
        a = self.geraet("A", "Europe/Berlin")
        a("lerne", 2, "nach")
        a.sync()
        ta.datei_aendern(markers={"reset_at": utc_text})
        a("setmeta", "reset_at", berlin_text)
        a.sync()
        self.assertEqual(a.marke(), utc_text)
        self.assertEqual(ta.datei()["markers"]["reset_at"], utc_text)
        self.assertEqual(self.ruhe([a], 3), 0, "Hin und Her: Hochladungen in Ruhe")
        self.assertEqual(a.namen(), {"a-nach": 2})

    def test_eintrag_ohne_abstand_zwischen_den_ortszeiten(self):
        """Ein Eintrag ohne utc_offset (alte Datenbank, Text-Vergleich) liegt
        zwischen den beiden Ortszeiten der Marke: Beide Geraete enden mit
        denselben Eintraegen, keine Hochladung in Ruhe."""
        moment, utc_text, berlin_text = marke_jetzt(minuten=150)
        a = self.geraet("A", "Europe/Berlin")
        b = self.geraet("B", "UTC")
        a("lerne", 1, "nach")
        b("lerne", 1, "nach")
        zwischen = (moment + datetime.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        b("eintrag", "zwischen", zwischen, None)
        for device in (a, b, a, b):
            device.sync()
        a("setmeta", "reset_at", berlin_text)
        b("setmeta", "reset_at", utc_text)
        for device in (a, b, a, b):
            device.sync()
        hochladungen = self.ruhe([a, b])
        datei = ta.datei().get("markers", {}).get("reset_at")
        ta.bericht("ohne Abstand: Ruhe %d, Marke Datei %s, A %s, B %s" % (
            hochladungen, datei, a.namen(), b.namen()))
        self.assertEqual(hochladungen, 0, "Hin und Her: Hochladungen in Ruhe")
        self.assertEqual(a.marke(), datei)
        self.assertEqual(b.marke(), datei)
        self.assertEqual(a.namen(), b.namen())

    def test_mischbetrieb_v0631(self):
        """Neues Geraet und v0.63.1 (behaelt bei Gleichstand die eigene
        Marke): beide Rollen, nach dem Angleichen Ruhe."""
        alt = self.alter_code("v0.63.1")
        for nr, (code_a, code_b) in enumerate(((ta.CODE, alt), (alt, ta.CODE))):
            with self.subTest(alt="B" if nr == 0 else "A"):
                ta.server_reset()
                moment, utc_text, berlin_text = marke_jetzt()
                a = self.geraet("A%d" % nr, "Europe/Berlin", code_a)
                b = self.geraet("B%d" % nr, "UTC", code_b)
                hochladungen = self._ablauf(a, b, berlin_text, utc_text, moment)
                self._pruefe_ende(a, b, hochladungen,
                                  {"a%d-nach" % nr: 2, "b%d-nach" % nr: 2})

    def test_mischbetrieb_v0623(self):
        """Zwei neue Geraete mit Gleichstand und ein Geraet v0.62.3
        (Textvergleich, schreibt ohne "schreiber"): Ruhe nach dem
        Angleichen, alle drei mit derselben Marke und denselben Eintraegen.
        Hier gilt schon ohne FG-116 der Textvergleich (keine Aenderung)."""
        alt = self.alter_code("v0.62.3")
        moment, utc_text, berlin_text = marke_jetzt()
        a = self.geraet("A", "Europe/Berlin")
        b = self.geraet("B", "UTC")
        c = self.geraet("C", "Europe/Berlin", alt)
        for device in (a, b, c):
            device("lerne", 2, "nach")
        for device in (a, b, c, a, b, c):
            device.sync()
        a("setmeta", "reset_at", berlin_text)
        b("setmeta", "reset_at", utc_text)
        for device in (a, b, c, a, b, c):
            device.sync()
        hochladungen = self.ruhe([a, b, c])
        datei = ta.datei().get("markers", {}).get("reset_at")
        ta.bericht("Mischbetrieb v0.62.3: Ruhe %d, Marke Datei %s, A %s, B %s, C %s" % (
            hochladungen, datei, a.marke(), b.marke(), c.marke()))
        self.assertEqual(hochladungen, 0, "Hin und Her: Hochladungen in Ruhe")
        self.assertEqual({a.marke(), b.marke(), c.marke()}, {datei})
        # Alle drei mit denselben Eintraegen. Welche das sind, entscheidet der
        # Textvergleich im Mischbetrieb (wie bis 0.62.3, nicht Teil von
        # FG-116): Eine Marke in "+02:00" erfasst beim Geraet in UTC auch
        # Eintraege bis 2 h nach ihr.
        self.assertEqual(a.namen(), c.namen())
        self.assertEqual(b.namen(), c.namen())
        self.assertEqual(c.namen().get("c-nach"), 2)


def tearDownModule():
    ta.tearDownModule()


if __name__ == "__main__":
    if os.name == "nt":
        print("test_abgleich_gleichstand_0632.py braucht Zeitzonen je Prozess (TZ) - "
              "nur Linux/macOS.")
        sys.exit(0)
    print("Code der neuen Geraete: %s" % ta.CODE)
    unittest.main(verbosity=2)
