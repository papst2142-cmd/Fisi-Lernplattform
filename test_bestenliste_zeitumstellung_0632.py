#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bestenliste und echte Zeitumstellung (0.63.2, Weisung zu Meldung 42,
Abschnitt 2.20, Frage 25; uebernommen aus der Probe der Gegenpruefung
bau_0.63.2/s6b/gp_fg100/belege/probe_dst.py).

B-G-17 / FG-100: "Bestenliste loeschen" setzt die Marke auf "jetzt"; ein
Eintrag, der nicht nach der Marke liegt, bekommt Marke + 1 s in deren Zone.
Hier mit dem echten _marker_now/_stamp (nur device_now liefert einen festen
Augenblick in einer echten Zeitzone aus zoneinfo): Berlin, New York, Kolkata,
UTC, 12 Faelle, darunter die Umstellungen im Fruehjahr und Herbst.

Je Fall: Marke und gespeicherter Eintrag (Ortszeit, Abstand) genau wie
erwartet; der Eintrag faellt beim Abgleich weder mit Zone (UTC) noch als
Text (Mischbetrieb) noch ueber den SQL-Weg (_delete_before) unter die Marke
und liegt in UTC nach der Marke.

Kein skip: Fehlen die Zeitzonendaten (zoneinfo), ist der Test rot.
Laeuft im Linux-Teil "rest" (pruefung/ci_tests.sh), nicht in der Windows-Liste.
"""

import datetime
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fisi_core  # noqa: E402
import fisi_sync  # noqa: E402

UTC = datetime.timezone.utc
B, N, K, U = "Europe/Berlin", "America/New_York", "Asia/Kolkata", "UTC"


def D(*args):
    return datetime.datetime(*args, tzinfo=UTC)


# (Name, Marke UTC, Zone beim Loeschen, Eintrag UTC, Zone beim Eintrag,
#  erwartete Marke, erwarteter Eintrag (Ortszeit, Abstand in Minuten))
FAELLE = [
    ("Berlin gleiche Sekunde Sommer",
     D(2026, 7, 1, 10, 0, 0, 300000), B, D(2026, 7, 1, 10, 0, 0, 900000), B,
     "2026-07-01 12:00:00+02:00", ("2026-07-01 12:00:01", 120)),
    ("Herbst: Marke 02:30 CEST, Eintrag gleich",
     D(2026, 10, 25, 0, 30, 0), B, D(2026, 10, 25, 0, 30, 0, 500000), B,
     "2026-10-25 02:30:00+02:00", ("2026-10-25 02:30:01", 120)),
    ("Herbst: Marke 02:30 CEST, Eintrag 02:10 CET",
     D(2026, 10, 25, 0, 30, 0), B, D(2026, 10, 25, 1, 10, 0), B,
     "2026-10-25 02:30:00+02:00", ("2026-10-25 02:30:01", 120)),
    ("Herbst: Marke 02:59:59 CEST, Eintrag 02:00 CET",
     D(2026, 10, 25, 0, 59, 59), B, D(2026, 10, 25, 1, 0, 0), B,
     "2026-10-25 02:59:59+02:00", ("2026-10-25 03:00:00", 120)),
    ("Fruehjahr 01:59:59 -> 03:00",
     D(2026, 3, 29, 0, 59, 59), B, D(2026, 3, 29, 1, 0, 0), B,
     "2026-03-29 01:59:59+01:00", ("2026-03-29 03:00:00", 120)),
    ("Fruehjahr gleiche Sekunde 03:00",
     D(2026, 3, 29, 1, 0, 0), B, D(2026, 3, 29, 1, 0, 0, 400000), B,
     "2026-03-29 03:00:00+02:00", ("2026-03-29 03:00:01", 120)),
    ("Marke New York, Eintrag Berlin gleiche Sekunde",
     D(2026, 11, 1, 5, 59, 59, 100000), N, D(2026, 11, 1, 5, 59, 59, 800000), B,
     "2026-11-01 01:59:59-04:00", ("2026-11-01 02:00:00", -240)),
    ("New York Herbst: 01:30 EDT, Eintrag 01:10 EST",
     D(2026, 11, 1, 5, 30, 0), N, D(2026, 11, 1, 6, 10, 0), N,
     "2026-11-01 01:30:00-04:00", ("2026-11-01 01:30:01", -240)),
    ("Marke Berlin, Eintrag Kolkata (+05:30)",
     D(2026, 7, 1, 10, 0, 0), B, D(2026, 7, 1, 10, 0, 0, 500000), K,
     "2026-07-01 12:00:00+02:00", ("2026-07-01 12:00:01", 120)),
    ("Marke Kolkata, Eintrag UTC",
     D(2026, 7, 1, 10, 0, 0), K, D(2026, 7, 1, 10, 0, 0, 500000), U,
     "2026-07-01 15:30:00+05:30", ("2026-07-01 15:30:01", 330)),
    ("Marke Berlin, Eintrag UTC eine Stunde spaeter",
     D(2026, 7, 1, 10, 0, 0), B, D(2026, 7, 1, 11, 0, 0), U,
     "2026-07-01 12:00:00+02:00", ("2026-07-01 12:00:01", 120)),
    ("Eintrag frueher als die Marke (Uhr zurueck)",
     D(2026, 7, 1, 10, 0, 5), B, D(2026, 7, 1, 10, 0, 1), B,
     "2026-07-01 12:00:05+02:00", ("2026-07-01 12:00:06", 120)),
]


def augenblick(utc, zone):
    return lambda: utc.astimezone(ZoneInfo(zone))


class BestenlisteZeitumstellungTest(unittest.TestCase):

    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="fisi_bl_dst_")
        self.addCleanup(shutil.rmtree, self.ordner, True)

    def test_zeitzonendaten_vorhanden(self):
        """Ohne zoneinfo-Daten rot (kein skip): alle vier Zonen laden, die
        Abstaende stimmen auch ueber die Umstellungen."""
        self.assertEqual(D(2026, 7, 1, 10).astimezone(ZoneInfo(B)).utcoffset(),
                         datetime.timedelta(hours=2))
        self.assertEqual(D(2026, 10, 25, 1, 10).astimezone(ZoneInfo(B)).utcoffset(),
                         datetime.timedelta(hours=1))
        self.assertEqual(D(2026, 11, 1, 6, 10).astimezone(ZoneInfo(N)).utcoffset(),
                         datetime.timedelta(hours=-5))
        self.assertEqual(D(2026, 7, 1, 10).astimezone(ZoneInfo(K)).utcoffset(),
                         datetime.timedelta(hours=5, minutes=30))
        self.assertEqual(D(2026, 7, 1, 10).astimezone(ZoneInfo(U)).utcoffset(),
                         datetime.timedelta(0))

    def test_zwoelf_faelle_echte_zeitumstellung(self):
        self.assertEqual(len(FAELLE), 12)
        for nr, (name, marke_utc, marke_zone, eintrag_utc, eintrag_zone,
                 soll_marke, soll_eintrag) in enumerate(FAELLE, 1):
            with self.subTest(fall=name):
                db = fisi_core.DBManager(os.path.join(self.ordner, "f%d.db" % nr),
                                         error_handler=lambda m: None)
                with mock.patch.object(fisi_core, "device_now",
                                       augenblick(marke_utc, marke_zone)):
                    self.assertTrue(db.reset_records())
                marke = db.get_meta("bestenliste_reset_at")
                self.assertEqual(marke, soll_marke)
                with mock.patch.object(fisi_core, "device_now",
                                       augenblick(eintrag_utc, eintrag_zone)):
                    self.assertTrue(db.log_record("l", "rekord", "k", 1.0))
                conn = sqlite3.connect(db.db_path)
                try:
                    zeilen = conn.execute(
                        "SELECT timestamp, utc_offset FROM spiel_bestenliste").fetchall()
                    self.assertEqual(zeilen, [soll_eintrag])
                    stempel, abstand = zeilen[0]
                    eintrag = {"timestamp": stempel, "utc_offset": abstand}
                    geparst = fisi_sync.parse_marker(marke)
                    self.assertFalse(fisi_sync._falls_under(eintrag, geparst), "mit Zone weg")
                    self.assertFalse(fisi_sync._falls_under(eintrag, (marke, None)),
                                     "als Text weg")
                    weg = fisi_sync._delete_before(conn.cursor(), "spiel_bestenliste", geparst)
                    conn.rollback()
                    self.assertEqual(weg, set(), "SQL-Weg loescht den Eintrag")
                finally:
                    conn.close()
                utc = (datetime.datetime.strptime(stempel, "%Y-%m-%d %H:%M:%S")
                       - datetime.timedelta(minutes=abstand))
                self.assertGreater(utc, geparst[1])
                # Abgleich mit der eigenen Datei behaelt den Eintrag
                fisi_sync.merge_into_local(db, fisi_sync.export_local(db), check_future=False)
                self.assertEqual(len(db.records()), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
