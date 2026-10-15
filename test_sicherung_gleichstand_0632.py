#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer FG-119 (ab 0.63.2): Sicherung zusammenfuehren bei Gleichstand
einer Loeschmarke in zwei Schreibweisen.

Befund (Probe 3b, fg116/clamp_probe): FG-116 laesst bei Gleichstand (dieselbe
Zeit in UTC, andere Schreibweise) in fisi_sync._merged_markers die Gegenseite
gelten. Beim Abgleich ist das die Datei (gewollt). merge_into_local laeuft aber
auch beim Zusammenfuehren einer Sicherung (remote = Sicherung). Dort galt damit
die Schreibweise der Sicherung, und ein Eintrag ohne utc_offset (Text-Vergleich)
zwischen den beiden Ortszeiten fiel weg - war er noch nicht hochgeladen, war er
verloren. Mit FG-119 behaelt das Zusammenfuehren bei Gleichstand wieder die
eigene Marke (wie vor FG-116); der Abgleich nimmt weiter die der Datei.

Geprueft wird mit echten Geraeteprozessen gegen die Attrappe (wie
test_abgleich.py). X und Z (gleiche Zone) gleichen ab, Y (andere Zone, ohne
Abgleich) hat dieselbe Marke in seiner Schreibweise und macht die Sicherung:
  * b1: X hat den Eintrag (schon in der Datei) - er bleibt;
  * b1n: wie b1, aber noch nicht hochgeladen - er bleibt und wird hochgeladen;
  * b2: die Sicherung bringt den Eintrag mit - er kommt nicht herein (die
    eigene Marke gilt);
  * b3: "Alles ersetzen" (anderer Weg, Waechter): danach gilt beim Abgleich
    die Datei, keine Hochladung in Ruhe.

Nur unter Linux/macOS (Zeitzone je Prozess ueber TZ).
Start:  python test_sicherung_gleichstand_0632.py
"""

import datetime
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import test_abgleich as ta  # noqa: E402

UTC = datetime.timezone.utc
# Feste Abstaende statt der echten Zone (Berlin hat ab Ende Oktober +01:00);
# die Zone der Marke muss nicht die des Geraets sein.
ZONEN = {"Europe/Berlin": datetime.timezone(datetime.timedelta(hours=2)), "UTC": UTC}


def datei_namen():
    """Eintraege der Abgleich-Datei, gruppiert wie Geraet.namen()."""
    data = ta.datei()
    names = ["uid"] + list((data.get("columns") or {}).get("card_events") or [])
    groups = {}
    for row in (data.get("tables") or {}).get("card_events") or []:
        label = dict(zip(names, row)).get("question", "").rsplit("-", 1)[0]
        groups[label] = groups.get(label, 0) + 1
    return groups


class SicherungGleichstandTest(unittest.TestCase):
    def setUp(self):
        ta.server_reset()
        self.geraete = []

    def tearDown(self):
        for geraet in self.geraete:
            geraet.close()

    def geraet(self, name, tz):
        device = ta.Geraet(self.id().rsplit(".", 1)[-1], name, tz)
        self.geraete.append(device)
        return device

    def ruhe(self, geraete, runden=2):
        vorher = ta.commits()
        for _ in range(runden):
            for device in geraete:
                device.sync()
        return ta.commits() - vorher

    def _basis(self, tz_x, tz_y, x_hat_zw, zw_spaet=False):
        """X und Z (Zone tz_x) gleichen mit der Marke M in der Schreibweise
        von X ab; Y (Zone tz_y, kein Abgleich) hat M in seiner Schreibweise
        und erstellt die Sicherung. Der Zwischen-Eintrag (ohne utc_offset)
        liegt 1 h nach M in UTC, also zwischen den beiden Ortszeiten."""
        x = self.geraet("X", tz_x)
        z = self.geraet("Z", tz_x)
        y = self.geraet("Y", tz_y)
        moment = (datetime.datetime.now(UTC) - datetime.timedelta(hours=3)
                  ).replace(microsecond=0)
        m_x = moment.astimezone(ZONEN[tz_x]).isoformat(" ")
        m_y = moment.astimezone(ZONEN[tz_y]).isoformat(" ")
        zw = (moment + datetime.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        vor = moment - datetime.timedelta(minutes=30)
        for device in (x, z, y):
            device("lerne", 2, "nach")
        x("eintrag", "vor", vor.astimezone(ZONEN[tz_x]).strftime("%Y-%m-%d %H:%M:%S"),
          int(ZONEN[tz_x].utcoffset(None).total_seconds() // 60))
        if x_hat_zw and not zw_spaet:
            x("eintrag", "zw", zw, None)
        elif not x_hat_zw:
            y("eintrag", "zw", zw, None)
        x("setmeta", "reset_at", m_x)
        y("setmeta", "reset_at", m_y)
        for device in (x, z, x, z):
            device.sync()
        self.assertEqual(self.ruhe([x, z], 1), 0, "keine Ruhe vor der Sicherung")
        self.assertEqual(x.marke(), m_x)
        self.assertEqual(ta.datei()["markers"]["reset_at"], m_x)
        if zw_spaet:            # nach dem letzten Abgleich, nicht in der Datei
            x("eintrag", "zw", zw, None)
            self.assertNotIn("x-zw", datei_namen())
        pfad = os.path.join(y.home, "y.fisi")
        y("sicherung_erstellen", pfad)
        return x, z, m_x, pfad

    def _nach_abgleich(self, x, z, m_x, soll, name):
        """Zwei Abgleiche zum Angleichen, dann Ruhe; X, Z und die Datei
        enden mit der Marke m_x (Schreibweise der Datei) und soll."""
        for device in (x, z, x, z):
            device.sync()
        hochladungen = self.ruhe([x, z])
        ta.bericht("%s: Ruhe %d, Marke X %s, Z %s, Datei %s, Eintraege X %s, Z %s, Datei %s"
                   % (name, hochladungen, x.marke(), z.marke(),
                      ta.datei()["markers"]["reset_at"], x.namen(), z.namen(),
                      datei_namen()))
        self.assertEqual(hochladungen, 0, "Hin und Her: Hochladungen in Ruhe")
        self.assertEqual(ta.datei()["markers"]["reset_at"], m_x)
        self.assertEqual(x.marke(), m_x)
        self.assertEqual(z.marke(), m_x)
        self.assertEqual(x.namen(), soll)
        self.assertEqual(z.namen(), soll)
        self.assertEqual(datei_namen(), soll)

    def test_b1_eintrag_bleibt(self):
        """b1: X (UTC) hat den Zwischen-Eintrag, er steht schon in der Datei;
        die Sicherung von Y (+02:00) wird zusammengefuehrt. X behaelt seine
        Marke, der Eintrag bleibt - auch nicht kurz weg."""
        x, z, m_x, pfad = self._basis("UTC", "Europe/Berlin", True)
        self.assertEqual(datei_namen().get("x-zw"), 1)
        x("sicherung_zusammen", pfad)
        ta.bericht("b1 direkt nach dem Einspielen: Marke X %s, Eintraege X %s" % (
            x.marke(), x.namen()))
        self.assertEqual(x.namen().get("x-zw"), 1, "Zwischen-Eintrag geloescht")
        self.assertEqual(x.marke(), m_x)
        self._nach_abgleich(x, z, m_x, {"x-nach": 2, "z-nach": 2, "y-nach": 2, "x-zw": 1},
                            "b1")

    def test_b1n_eintrag_nicht_hochgeladen_bleibt(self):
        """b1n: wie b1, der Eintrag ist aber noch nicht hochgeladen. Er darf
        beim Zusammenfuehren nicht verloren gehen und kommt mit dem naechsten
        Abgleich in die Datei und auf Z."""
        x, z, m_x, pfad = self._basis("UTC", "Europe/Berlin", True, zw_spaet=True)
        x("sicherung_zusammen", pfad)
        ta.bericht("b1n direkt nach dem Einspielen: Marke X %s, Eintraege X %s" % (
            x.marke(), x.namen()))
        self.assertEqual(x.namen().get("x-zw"), 1, "Zwischen-Eintrag verloren")
        self.assertEqual(x.marke(), m_x)
        self._nach_abgleich(x, z, m_x, {"x-nach": 2, "z-nach": 2, "y-nach": 2, "x-zw": 1},
                            "b1n")

    def test_b2_eintrag_aus_sicherung_kommt_nicht(self):
        """b2: X (+02:00) hat den Eintrag nicht, die Sicherung (UTC) bringt
        ihn mit. Nach der eigenen Marke faellt er darunter und kommt nicht
        herein (weder kurz noch nach dem Abgleich)."""
        x, z, m_x, pfad = self._basis("Europe/Berlin", "UTC", False)
        x("sicherung_zusammen", pfad)
        ta.bericht("b2 direkt nach dem Einspielen: Marke X %s, Eintraege X %s" % (
            x.marke(), x.namen()))
        self.assertNotIn("y-zw", x.namen())
        self.assertEqual(x.marke(), m_x)
        self._nach_abgleich(x, z, m_x, {"x-nach": 2, "z-nach": 2, "y-nach": 2}, "b2")

    def test_b3_alles_ersetzen_ruhig(self):
        """b3: "Alles ersetzen" mit der Sicherung von Y (+02:00) auf X (UTC):
        X uebernimmt die Marke von Y; der Abgleich gleicht an die Datei an
        (FG-116), danach keine Hochladung mehr, der Eintrag kommt aus der
        Datei zurueck."""
        x, z, m_x, pfad = self._basis("UTC", "Europe/Berlin", True)
        x("sicherung_ersetzen", pfad)
        self._nach_abgleich(x, z, m_x, {"x-nach": 2, "z-nach": 2, "y-nach": 2, "x-zw": 1},
                            "b3")


def tearDownModule():
    ta.tearDownModule()


if __name__ == "__main__":
    if os.name == "nt":
        print("test_sicherung_gleichstand_0632.py braucht Zeitzonen je Prozess (TZ) - "
              "nur Linux/macOS.")
        sys.exit(0)
    print("Code der Geraete: %s" % ta.CODE)
    unittest.main(verbosity=2)
