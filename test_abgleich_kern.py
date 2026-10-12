#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kern des Abgleichs ab 0.62.4 auf allen Systemen, auch unter Windows
(Zwischenabnahme Bau 1, Auflage C-1).

test_abgleich.py stellt mehrere Geraete in verschiedenen Zeitzonen nach. Das
geht nur unter Linux/macOS (Zeitzone je Prozess ueber TZ). Diese Datei prueft
dieselben Bausteine in einem Prozess und ohne fremde Zeitzone: Andere Zonen
stecken hier in den Daten (Marken mit "+05:30", Eintraege mit utc_offset),
nicht in der Uhr des Rechners. Dazu ein echter Abgleich zweier Datenbanken
gegen die Attrappe der GitHub-Schnittstelle (pruefung/abgleich_attrappe.py).

Wegwerf-Daten: HOME, APPDATA usw. und FISI_DB_PATH zeigen auf einen eigenen
Ordner, bevor fisi_core geladen wird.
Start:  python test_abgleich_kern.py
"""

import datetime
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = tempfile.mkdtemp(prefix="fisi_abgleich_kern_")
for _name in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "XDG_DATA_HOME",
              "XDG_CONFIG_HOME"):
    os.environ[_name] = WORK
os.environ["FISI_DB_PATH"] = os.path.join(WORK, "standard.db")
# ABGLEICH_CODE=<ordner> prueft einen anderen Stand (Gegenprobe gegen v0.62.3)
sys.path.insert(0, os.path.join(HERE, "pruefung"))
sys.path.insert(0, os.path.abspath(os.environ.get("ABGLEICH_CODE") or HERE))

import fisi_core  # noqa: E402
import fisi_sync  # noqa: E402
import abgleich_attrappe as att  # noqa: E402

SERVER, PORT = att.start_server()
fisi_sync.API = "http://127.0.0.1:%d" % PORT
SETTINGS = {"sync_repo": "pruef/lernstand-attrappe",
            "sync_token": "PLATZHALTER-KEIN-ECHTES-TOKEN"}


def neue_db(name):
    return fisi_core.DBManager(db_path=os.path.join(WORK, name + ".db"),
                               error_handler=lambda m: sys.stderr.write("DB: %s\n" % m))


def eintrag(db, frage, zeit, abstand):
    """Eine Karteikarte mit vorgegebener Ortszeit und utc_offset (Minuten)."""
    conn = sqlite3.connect(db.db_path)
    try:
        conn.execute("INSERT INTO card_events (timestamp, utc_offset, category, question, "
                     "mode, correct, uid) VALUES (?, ?, 'Kat', ?, 'karte', 1, ?)",
                     (zeit, abstand, frage, frage + "-uid"))
        conn.commit()
    finally:
        conn.close()


def ortszeit(sekunden):
    """(Ortszeit-Text, utc_offset) fuer jetzt + sekunden (richtige Uhr)."""
    moment = (datetime.datetime.now(datetime.timezone.utc)
              + datetime.timedelta(seconds=sekunden)).astimezone()
    return moment.strftime("%Y-%m-%d %H:%M:%S"), fisi_core.offset_minutes(moment)


def fragen(db):
    conn = sqlite3.connect(db.db_path)
    try:
        return sorted(row[0] for row in conn.execute("SELECT question FROM card_events"))
    finally:
        conn.close()


def datei(markers, tables=None):
    """Eine Abgleich-Datei wie von einem Geraet mit 0.62.4."""
    return {"format": fisi_sync.FORMAT, fisi_sync.WRITER_KEY: fisi_sync.WRITER,
            fisi_sync.CLAMP_KEY: {},
            "columns": {t: list(c) for t, c in fisi_sync.SYNC_TABLES.items()},
            "markers": markers, "tables": tables or {}}


class MarkenTest(unittest.TestCase):
    def test_format_und_lesen(self):
        """Marke mit Zone hin und zurueck, fuer mehrere Zonen."""
        utc = datetime.datetime(2026, 10, 25, 0, 30, tzinfo=datetime.timezone.utc)
        for minuten in (0, 60, 120, -300, 330, -570):
            zone = datetime.timezone(datetime.timedelta(minutes=minuten))
            with self.subTest(minuten=minuten):
                text = fisi_core.format_with_zone(utc.astimezone(zone))
                self.assertEqual(fisi_core.offset_minutes(utc.astimezone(zone)), minuten)
                lokal, zeit = fisi_sync.parse_marker(text)
                self.assertEqual(zeit, utc.replace(tzinfo=None), text)
                self.assertEqual(lokal, utc.astimezone(zone).strftime("%Y-%m-%d %H:%M:%S"))

    def test_ungueltige_marken(self):
        for wert in ("x", "2026-13-45 10:00:00", 12345, "12345",
                     "2026-10-12 05:00:00+24:00"):
            with self.subTest(wert=wert):
                self.assertIsNone(fisi_sync.parse_marker(wert))
        self.assertEqual(fisi_sync.parse_marker("2026-10-12 05:00:00"),
                         ("2026-10-12 05:00:00", None))
        marken = {"reset_at": "x", "history_cleared_at": 12345,
                  "spiel_reset_at": "2026-10-12 05:00:00+02:00"}
        self.assertEqual(sorted(fisi_sync._invalid_markers(marken, zone=True)),
                         ["history_cleared_at", "reset_at"])
        # Mischbetrieb: Text gilt wie bis 0.62.3, nur Nicht-Text ist ungueltig
        self.assertEqual(fisi_sync._invalid_markers(marken, zone=False),
                         ["history_cleared_at"])

    def test_spaetere_marke_ueber_zonen(self):
        """Zeitumstellung: 02:10 Winterzeit liegt nach 02:30 Sommerzeit."""
        sommer = "2026-10-25 02:30:00+02:00"
        winter = "2026-10-25 02:10:00+01:00"
        self.assertEqual(fisi_sync._later(sommer, winter), winter)
        self.assertEqual(fisi_sync._later(winter, sommer), winter)
        # als Text (Mischbetrieb) wie bis 0.62.3
        self.assertEqual(fisi_sync._later(sommer, winter, zone=False), sommer)
        # eine Marke ohne Zone: Textvergleich
        self.assertEqual(fisi_sync._later("2026-10-25 03:00:00", winter), "2026-10-25 03:00:00")

    def test_uhrabweichung(self):
        jetzt = datetime.datetime.now().astimezone()
        wert = json.dumps({"s": -3600.0, "gemessen": jetzt.isoformat()})
        self.assertEqual(fisi_core.clock_deviation(wert, jetzt), -3600.0)
        spaeter = jetzt + datetime.timedelta(seconds=fisi_core.CLOCK_VALID + 1)
        self.assertIsNone(fisi_core.clock_deviation(wert, spaeter))
        self.assertIsNone(fisi_core.clock_deviation("kein json", jetzt))
        self.assertTrue(fisi_sync.clock_fix_text(7200))
        self.assertEqual(fisi_sync.clock_fix_text(0), "")


class DatenbankTest(unittest.TestCase):
    def test_spalte_und_eigener_abstand(self):
        db = neue_db("spalte")
        db.log_card("Kat", "frage", "karte", 1)
        conn = sqlite3.connect(db.db_path)
        try:
            spalten = [row[1] for row in conn.execute("PRAGMA table_info(card_events)")]
            zeit, abstand = conn.execute(
                "SELECT timestamp, utc_offset FROM card_events").fetchone()
        finally:
            conn.close()
        self.assertIn("utc_offset", spalten)
        moment = datetime.datetime.strptime(zeit[:19], "%Y-%m-%d %H:%M:%S")
        self.assertIn(abstand, {fisi_core.offset_minutes(moment.replace(fold=f).astimezone())
                                for f in (0, 1)})
        daten = fisi_sync.export_local(db)
        self.assertEqual(daten[fisi_sync.WRITER_KEY], fisi_sync.WRITER)
        self.assertIn("utc_offset", daten["columns"]["card_events"])

    def test_loeschmarke_in_utc(self):
        """Marke aus Indien (+05:30), Eintraege aus Berlin (+120) und New York
        (-240): geloescht wird, was in UTC nicht nach der Marke liegt."""
        db = neue_db("utc")
        eintrag(db, "berlin-vorher", "2026-10-01 10:00:00", 120)   # 08:00 UTC
        eintrag(db, "newyork-nachher", "2026-10-01 05:00:00", -240)  # 09:00 UTC
        eintrag(db, "berlin-nachher", "2026-10-01 11:00:00", 120)  # 09:00 UTC
        marke = "2026-10-01 14:00:00+05:30"                        # 08:30 UTC
        fisi_sync.merge_into_local(db, datei({"reset_at": marke}), mixed=False)
        self.assertEqual(fragen(db), ["berlin-nachher", "newyork-nachher"])

    def test_mischbetrieb_als_text(self):
        """Mit einem alten Geraet (mischbetrieb) zaehlt der Text wie bis 0.62.3."""
        db = neue_db("text")
        eintrag(db, "newyork", "2026-10-01 05:00:00", -240)        # Text vor 14:00
        fisi_sync.merge_into_local(db, datei({"reset_at": "2026-10-01 14:00:00+05:30"}),
                                   mixed=True)
        self.assertEqual(fragen(db), [])

    def test_ungueltige_marke_wird_nicht_angewendet(self):
        db = neue_db("ungueltig")
        eintrag(db, "bleibt", "2026-10-01 10:00:00", 120)
        stats = fisi_sync.MergeStats()
        fisi_sync.merge_into_local(db, datei({"reset_at": "x"}), stats=stats, mixed=False)
        self.assertEqual(fragen(db), ["bleibt"])
        self.assertTrue(stats.notes())


class AbgleichTest(unittest.TestCase):
    """Zwei Datenbanken gleichen ueber die Attrappe ab (echtes fisi_sync.sync)."""

    def setUp(self):
        att.STATE.reset()
        att.STATE.ctl["datum_versatz"] = 0

    def test_hin_und_zurueck(self):
        a, b = neue_db("a"), neue_db("b")
        for i in range(3):
            a.log_card("Kat", "a-%d" % i, "karte", 1)
        self.assertEqual(fisi_sync.sync(a, SETTINGS, "A").sent, 3)
        self.assertEqual(fisi_sync.sync(b, SETTINGS, "B").received, 3)
        b.log_card("Kat", "b-0", "karte", 1)
        fisi_sync.sync(b, SETTINGS, "B")
        fisi_sync.sync(a, SETTINGS, "A")
        self.assertEqual(fragen(a), fragen(b))
        self.assertEqual(len(fragen(a)), 4)
        # Ruhe: nichts mehr hochzuladen
        self.assertEqual(fisi_sync.sync(a, SETTINGS, "A").sent, 0)

    def test_zukunftsmarke_wird_gekappt(self):
        """B-G-24: Die Uhr von A geht eine Stunde vor. A loescht; die Marke
        bekommt die Uhrzeit von GitHub, ein spaeterer Eintrag von B bleibt
        (bis 0.62.3 loeschte die Zukunftsmarke ihn mit)."""
        a, b = neue_db("za"), neue_db("zb")
        # Zeiten mit Abstand zur Loeschung (der Date-Kopf hat nur Sekunden)
        eintrag(b, "vorher", *ortszeit(-600))
        fisi_sync.sync(b, SETTINGS, "B")
        with uhr_versatz(3600):
            fisi_sync.sync(a, SETTINGS, "A")         # misst die Abweichung
            self.assertTrue(a.reset_all())
            fisi_sync.sync(a, SETTINGS, "A")
        eintrag(b, "nachher", *ortszeit(120))
        fisi_sync.sync(b, SETTINGS, "B")
        with uhr_versatz(3600):
            fisi_sync.sync(a, SETTINGS, "A")
        self.assertEqual(fragen(a), ["nachher"])
        self.assertEqual(fragen(b), ["nachher"])


class uhr_versatz:
    """Geraeteuhr fuer die Dauer des Blocks um sekunden verstellt."""

    def __init__(self, sekunden):
        self.sekunden = sekunden

    def __enter__(self):
        echt = fisi_core.device_now
        self.echt = echt
        verstellt = lambda: (echt() + datetime.timedelta(seconds=self.sekunden)).astimezone()  # noqa: E731
        fisi_core.device_now = fisi_sync.device_now = verstellt

    def __exit__(self, *args):
        fisi_core.device_now = fisi_sync.device_now = self.echt


def tearDownModule():
    SERVER.shutdown()
    shutil.rmtree(WORK, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
