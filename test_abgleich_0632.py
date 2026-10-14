#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Abgleich-Kern 0.63.2 (Plan 0.63.2, Bauauftrag S6a; Teilplan S6 1.1, 1.7, 1.8, 2):

  G-B     Sperre bei beschaedigter Datenbank vor JEDEM Schreibblock: im
          Abgleich auch nach dem Netzzugriff (fisi_sync.sync) und direkt vor
          dem Schreibblock von merge_into_local; in der Sicherung vor dem
          Schreibblock von "Alles ersetzen" (nach der Sicherheitskopie) und
          vor dem Zurueckholen geloeschter Spielstaende (merge_backup).
  B-G-17  "Bestenliste loeschen" (ab Weisung zu Meldung 41, Frage 8, FG-100):
          Die Marke ist wieder "jetzt"; ein Eintrag, der nicht nach der Marke
          liegt, bekommt Marke + 1 s (in deren Zone) und bleibt (auch auf
          einem Geraet mit 0.63.1); Eintraege anderer Geraete aus derselben
          Sekunde vor dem Loeschen sind weg.
  B-G-29  Sehr alte Datenbank (vor v0.24, Eintraege ohne uid) als Datei auf
          zwei Geraete kopiert: Die uid kommt aus Tabelle, id und Inhalt,
          beide Kopien zaehlen nach dem Abgleich nicht doppelt. Abgesichert
          (Freigabe F5): ohne Eintraege ohne uid kein einziger Schreibzugriff,
          vorhandene uids bleiben, Kollision -> zufaellige uid.
  Z4      Die Meldung zum Repository nennt ein Beispiel statt eines echten
          Repositorys.
  T-a     Altes Geraet (v0.63.1) -> neues Geraet (0.63.2): Datenbank mit Code
          v0.63.1 und vollem Inhalt anlegen, mit dem neuen Code oeffnen ->
          Datei byte-gleich; danach Abgleich, dieselben Zahlen.
  T-b/T-c Mischbetrieb: Nicos Geraet mit v0.63.1, ein neues Geraet mit 0.63.2,
          danach kommt ein Geraet zurueck, das waehrend der Loeschungen offline
          war (Freigabe F3, Zusatz). Vergleich mit demselben Ablauf nur mit
          v0.63.1: Nichts geht verloren, was 0.63.1 nicht auch verliert;
          gleiche uids, keine Doppelten, keine Hochladung ohne neue Eintraege.
          T-b: das alte Geraet handelt zuerst, T-c umgekehrt.
          Fuer S6b (B-G-08) wiederverwendbar: mischbetrieb(...) mit eigenen
          Schritten (Parameter zwischen).
  FP      Abgleich-Fingerabdruck: export_local derselben Datenbank mit v0.63.1
          und mit dem neuen Code -> gleiches kanonisches JSON (sha256).
  B-G-08  (S6b) "Alles ersetzen" nach abgeglichenem "Alle Lerndaten
          loeschen": Der naechste Abgleich loescht den eingespielten Stand
          nicht mehr (Feld "aufgehoben"); BG08Kern im Testprozess,
          BG08Ersetzen mit Geraeten inkl. T-b/T-c und Geraet v0.63.1.
  FG-81/  (S6b, Antwort Meldung 31, 35 und 37) Verhaltenstests je Satz der Texte vor
  FG-92   "Alles ersetzen" und "Zusammenfuehren" (test_fg81_*, test_fg92_*).

Geraete wie in test_abgleich.py (eigene Prozesse, Attrappe der GitHub-API,
Wegwerf-HOME); fuer vollen Inhalt pruefung/abgleich_geraet_voll.py. Der Code
von v0.63.1 kommt per git archive aus dem Tag (in der CI rot statt
uebersprungen, wenn er fehlt). Die Kern-Tests (G-B, B-G-17, B-G-29, Z4)
laufen im Testprozess mit Wegwerf-Datenbanken.

Gegenprobe gegen einen anderen Stand (14b3bd4: G-B, B-G-17, B-G-29, Z4 und
T-b/T-c-Teil B-G-17 rot; Schutztests gruen):
    ABGLEICH_CODE=<ordner mit dem Code> python test_abgleich_0632.py
Belegdatei des Fingerabdrucks: ABGLEICH_FP_BELEG=<datei.json>
Nur unter Linux/macOS (Zeitzone je Prozess ueber TZ).
"""

import datetime
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
WORK_KERN = tempfile.mkdtemp(prefix="fisi_abgleich_0632_")
HOME = os.path.join(WORK_KERN, "home")
os.makedirs(HOME)
os.environ["HOME"] = HOME
os.environ["APPDATA"] = HOME
os.environ["FISI_DB_PATH"] = os.path.join(HOME, "start.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(WORK_KERN, "selbsttest.log"))
os.environ["FISI_VORLADEN"] = "0"

import test_abgleich as ta  # noqa: E402  (Attrappe, Geraete, git archive)

CODE = ta.CODE
sys.path.insert(0, CODE)
import fisi_core  # noqa: E402
import fisi_sicherung as fsi  # noqa: E402
import fisi_sync  # noqa: E402

VOLL = os.path.join(HERE, "pruefung", "abgleich_geraet_voll.py")
ALT = "v0.63.1"
TOKEN = "PLATZHALTER_KEIN_ECHTER_SCHLUESSEL"
KAPUTT = fisi_core.DB_READ_ONLY_LINES["kaputt"]
_ZAEHLER = [0]


def bericht(text):
    ta.bericht(text)


def sha(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def neuer_pfad(name):
    _ZAEHLER[0] += 1
    folder = os.path.join(WORK_KERN, "%s_%d" % (name, _ZAEHLER[0]))
    os.makedirs(folder)
    return os.path.join(folder, "fisi_lernplattform.db")


def neue_db(name="db"):
    return fisi_core.DBManager(neuer_pfad(name), error_handler=lambda message: None)


def zeilen(path, sql, params=()):
    conn = sqlite3.connect(path)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def sekundenanfang():
    """Wartet, bis eine neue Sekunde gerade begonnen hat."""
    while True:
        rest = time.time() % 1.0
        if rest < 0.05:
            return
        time.sleep(1.0 - rest + 0.001)


def fremde_datei(uid="fremd1"):
    """Abgleich-Datei eines anderen Geraets mit einer Quiz-Antwort."""
    columns = list(fisi_sync.SYNC_TABLES["quiz_answers"])
    values = {"timestamp": "2026-09-03 10:00:00", "category": "Netzwerktechnik",
              "question": "Frage", "correct": 1}
    return {"format": fisi_sync.FORMAT, "markers": {},
            "columns": {"quiz_answers": columns},
            "tables": {"quiz_answers": [[uid] + [values.get(c) for c in columns]]}}


def alte_db(path, karten=5):
    """Datenbank wie vor v0.24: Tabellen ohne uid (und ohne die spaeter
    dazugekommenen Spalten), karten Karteikarten, eine Quiz-Antwort."""
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE card_events (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                     "timestamp TEXT NOT NULL, category TEXT NOT NULL, question TEXT NOT NULL,"
                     " mode TEXT NOT NULL, correct INTEGER)")
        conn.execute("CREATE TABLE quiz_answers (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                     "timestamp TEXT NOT NULL, category TEXT NOT NULL, question TEXT NOT NULL,"
                     " correct INTEGER NOT NULL)")
        for i in range(karten):
            conn.execute("INSERT INTO card_events (timestamp, category, question, mode, correct)"
                         " VALUES (?, 'Kat', ?, 'karte', ?)",
                         ("2023-03-0%d 10:00:00" % (i % 9 + 1), "alt-karte-%d" % i, i % 2))
        conn.execute("INSERT INTO quiz_answers (timestamp, category, question, correct) "
                     "VALUES ('2023-03-01 11:00:00', 'Kat', 'alt-quiz', 1)")
        conn.commit()
    finally:
        conn.close()
    return path


def abgeleitete_uid(path, table, rowid):
    """uid, die der neue Code einem Eintrag ohne uid gibt (B-G-29) - hier
    unabhaengig nachgerechnet, nur fuer den Kollisions-Test."""
    conn = sqlite3.connect(path)
    try:
        cur = conn.execute("SELECT rowid, * FROM %s WHERE rowid = ?" % table, (rowid,))
        names = [item[0] for item in cur.description][1:]
        row = cur.fetchone()
    finally:
        conn.close()
    content = json.dumps([table] + [[n, v] for n, v in zip(names, row[1:]) if n != "uid"],
                         ensure_ascii=True, default=repr)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]


def tearDownModule():
    shutil.rmtree(WORK_KERN, ignore_errors=True)


# ============================================================================
#  G-B: Sperre vor jedem Schreibblock
# ============================================================================

class GBSperre(unittest.TestCase):
    """Die Sperre (read_only_reason) kommt waehrend des Vorgangs dazu - z.B.
    weil die Oberflaeche gerade einen Schaden bemerkt. Vorher pruefte der
    Abgleich nur einmal vor dem Netz, die Sicherung nur am Anfang."""

    SETTINGS = {"sync_repo": "pruef/attrappe", "sync_token": TOKEN, "sync_auto": True,
                "sync_last": ""}

    def test_g_b_sperre_waehrend_abgleich(self):
        """Sperre kommt waehrend fetch_remote, Uhr 2 h vor: SyncError, Datei
        byte-gleich (vorher schrieb der Uhr-Nachtrag _correct_own_entries)."""
        db = neue_db("gb_sync")
        for i in range(3):
            db.log_card("Kat", "eigen-%d" % i, "karte", 1)
        vorher = sha(db.db_path)
        offsets = zeilen(db.db_path, "SELECT utc_offset FROM card_events")
        calls = []
        now = fisi_core.device_now().astimezone(fisi_core.datetime.timezone.utc)

        def fetch(repo, token):
            calls.append("GET")
            fisi_sync._SERVER_CLOCK.update(
                server=now - fisi_core.datetime.timedelta(hours=2), device=now)
            db.read_only_reason = "kaputt"
            return "sha1", fremde_datei()

        def upload(*args, **kwargs):
            calls.append("PUT")
            return "sha2"

        with mock.patch.object(fisi_sync, "fetch_remote", fetch), \
                mock.patch.object(fisi_sync, "upload", upload):
            with self.assertRaises(fisi_sync.SyncError) as caught:
                fisi_sync.sync(db, settings=dict(self.SETTINGS), device="Test")
        bericht("G-B Abgleich: %s | Aufrufe %s" % (caught.exception, calls))
        self.assertEqual(str(caught.exception), (fisi_sync.MSG_READ_ONLY % KAPUTT).strip())
        self.assertEqual(calls, ["GET"])
        self.assertEqual(zeilen(db.db_path, "SELECT utc_offset FROM card_events"), offsets)
        self.assertEqual(sha(db.db_path), vorher, "Datei wurde veraendert")

    def test_fg_78_sperre_vor_dem_uhr_nachtrag(self):
        """FG-78 (gp_s6a L2, Versuch gb_sync_rest.py): Die Sperre entsteht
        zwischen der Pruefung nach dem Netz und dem Uhr-Nachtrag (beim
        Schreiben in _note_mixed). Der Nachtrag wird nicht geschrieben
        (SyncError, utc_offset unveraendert); beim naechsten Abgleich ohne
        Sperre wird er nachgeholt - nichts geht verloren."""
        db = neue_db("fg78")
        for i in range(3):
            db.log_card("Kat", "eigen-%d" % i, "karte", 1)
        offsets = zeilen(db.db_path, "SELECT utc_offset FROM card_events ORDER BY rowid")
        now = fisi_core.device_now().astimezone(fisi_core.datetime.timezone.utc)

        def fetch(repo, token):
            fisi_sync._SERVER_CLOCK.update(
                server=now - fisi_core.datetime.timedelta(hours=2), device=now)
            datei = fremde_datei()
            return "sha1", datei        # ohne "schreiber": _note_mixed schreibt

        echt = db.set_meta

        def set_meta(key, value):
            if key == fisi_sync.MIXED_KEY:
                db.read_only_reason = "kaputt"      # Schaden genau hier erkannt
                return False
            return echt(key, value)

        with mock.patch.object(fisi_sync, "fetch_remote", fetch), \
                mock.patch.object(fisi_sync, "upload", lambda *a, **k: "sha2"), \
                mock.patch.object(db, "set_meta", set_meta):
            with self.assertRaises(fisi_sync.SyncError) as caught:
                fisi_sync.sync(db, settings=dict(self.SETTINGS), device="Test")
        nach_sperre = zeilen(db.db_path, "SELECT utc_offset FROM card_events ORDER BY rowid")
        bericht("FG-78 Sperre vor dem Uhr-Nachtrag: %s | utc_offset vorher %s, danach %s"
                % (caught.exception, offsets, nach_sperre))
        self.assertIn(KAPUTT, str(caught.exception))
        self.assertEqual(nach_sperre, offsets)
        self.assertIsNone(db.get_meta(fisi_core.CLOCK_KEY))
        db.read_only_reason = None                  # Schaden behoben
        with mock.patch.object(fisi_sync, "fetch_remote", fetch), \
                mock.patch.object(fisi_sync, "upload", lambda *a, **k: "sha2"):
            fisi_sync.sync(db, settings=dict(self.SETTINGS), device="Test")
        nachgeholt = zeilen(db.db_path, "SELECT utc_offset FROM card_events ORDER BY rowid")
        bericht("FG-78 naechster Abgleich: utc_offset %s" % (nachgeholt,))
        self.assertEqual(nachgeholt, [(row[0] + 120,) for row in offsets])
        self.assertEqual(zeilen(db.db_path, "SELECT count(*) FROM card_events"), [(3,)])

    def test_g_b_merge_into_local_vor_schreibblock(self):
        """Sperre kommt nach der Pruefung am Anfang von merge_into_local
        (waehrend export_local): kein Schreiben, SyncError."""
        db = neue_db("gb_merge")
        vorher = sha(db.db_path)
        echt = fisi_sync.export_local

        def export(arg):
            db.read_only_reason = "kaputt"
            return echt(arg)

        with mock.patch.object(fisi_sync, "export_local", export):
            with self.assertRaises(fisi_sync.SyncError) as caught:
                fisi_sync.merge_into_local(db, fremde_datei(), check_future=False)
        bericht("G-B merge_into_local: %s" % caught.exception)
        self.assertIn(KAPUTT, str(caught.exception))
        self.assertEqual(sha(db.db_path), vorher, "Datei wurde veraendert")
        self.assertEqual(zeilen(db.db_path, "SELECT count(*) FROM quiz_answers"), [(0,)])

    def test_g_b_sicherung_einspielen_sperre_waehrend_kopie(self):
        """"Alles ersetzen": Sperre kommt waehrend der Sicherheitskopie ->
        BackupError, Lernstand byte-gleich (vorher: kein Fehler, ersetzt)."""
        quelle = neue_db("gb_quelle")
        quelle.log_quiz_answer("Netzwerktechnik", "Frage aus der Sicherung", True)
        backup = fsi.read_backup(fsi.create_backup(quelle, "0.63.2", "Test"))
        db = neue_db("gb_ersetzen")
        db.log_card("Kat", "bleibt", "karte", 1)
        vorher = sha(db.db_path)
        echt = fsi.create_backup

        def kopie(*args, **kwargs):
            db.read_only_reason = "kaputt"
            return echt(*args, **kwargs)

        with mock.patch.object(fsi, "create_backup", kopie):
            with self.assertRaises(fsi.BackupError) as caught:
                fsi.replace_all(db, backup, os.path.dirname(db.db_path), "0.63.2", "Test")
        bericht("G-B Alles ersetzen: %s" % caught.exception)
        self.assertEqual(str(caught.exception), (fsi.MSG_READ_ONLY % KAPUTT).strip())
        self.assertEqual(sha(db.db_path), vorher, "Datei wurde veraendert")

    def test_g_b_merge_backup_restore_runs_sperre(self):
        """Sicherung zusammenfuehren mit geloeschtem Spielstand: Sperre kommt
        nach merge_into_local -> BackupError, danach kein Schreiben mehr
        (vorher: Platz und Ereignisse wurden trotzdem eingetragen)."""
        quelle = neue_db("gb_quelle2")
        quelle.log_quiz_answer("Netzwerktechnik", "Frage", True)
        backup = fsi.read_backup(fsi.create_backup(quelle, "0.63.2", "Test"))
        db = neue_db("gb_zusammen")
        echt = fsi.merge_into_local
        nach_merge = []

        def merge(*args, **kwargs):
            result = echt(*args, **kwargs)
            nach_merge.append(sha(db.db_path))
            db.read_only_reason = "kaputt"
            return result

        with mock.patch.object(fsi, "merge_into_local", merge):
            with self.assertRaises(fsi.BackupError) as caught:
                fsi.merge_backup(db, backup, restore_runs=["lalterlauf"], device="Test")
        bericht("G-B merge_backup: %s" % caught.exception)
        self.assertIn(KAPUTT, str(caught.exception))
        self.assertEqual(len(nach_merge), 1)
        self.assertEqual(sha(db.db_path), nach_merge[0], "nach der Sperre geschrieben")
        self.assertEqual(zeilen(db.db_path, "SELECT count(*) FROM spiel_plaetze"), [(0,)])

    def test_g_b_schutz_ohne_sperre_unveraendert(self):
        """Schutz: ohne Sperre laufen Abgleich und Zusammenfuehren wie bisher."""
        db = neue_db("gb_schutz")
        received = fisi_sync.merge_into_local(db, fremde_datei(), check_future=False)
        self.assertEqual(received, 1)
        quelle = neue_db("gb_quelle3")
        quelle.log_card("Kat", "aus Sicherung", "karte", 1)
        backup = fsi.read_backup(fsi.create_backup(quelle, "0.63.2", "Test"))
        self.assertEqual(fsi.merge_backup(db, backup, device="Test"), 1)
        fsi.replace_all(db, backup, os.path.dirname(db.db_path), "0.63.2", "Test")
        self.assertEqual(zeilen(db.db_path, "SELECT question FROM card_events"),
                         [("aus Sicherung",)])


# ============================================================================
#  B-G-17: Bestenliste loeschen, Eintrag in derselben Sekunde
# ============================================================================

class BG17Bestenliste(unittest.TestCase):

    def test_b_g_17_bestenliste_selbe_sekunde(self):
        """Loeschen und neuer Eintrag in derselben Sekunde, danach Abgleich
        mit der eigenen Datei: Der neue Eintrag bleibt (vorher: 0 Zeilen).
        Ab FG-100: Der Eintrag traegt Marke + 1 s."""
        db = neue_db("bg17")
        db.log_record("lauf1", "rekord", "vorher", 1.0)
        sekundenanfang()
        self.assertTrue(db.reset_records())
        db.log_record("lauf1", "rekord", "nachher", 2.0)
        marke = db.get_meta("bestenliste_reset_at")
        stempel = zeilen(db.db_path, "SELECT timestamp FROM spiel_bestenliste")
        bericht("B-G-17 Marke %s, Eintrag %s" % (marke, stempel))
        self.assertEqual(len(stempel), 1)
        self.assertEqual(stempel[0][0][:19], (fisi_core.datetime.datetime.strptime(
            marke[:19], "%Y-%m-%d %H:%M:%S") + fisi_core.datetime.timedelta(
                seconds=1)).strftime("%Y-%m-%d %H:%M:%S"), "nicht dieselbe Sekunde")
        fisi_sync.merge_into_local(db, fisi_sync.export_local(db), check_future=False)
        self.assertEqual(zeilen(db.db_path, "SELECT schluessel FROM spiel_bestenliste"),
                         [("nachher",)])

    def test_b_g_17_fg100_marke_ist_jetzt(self):
        """FG-100 (neu, 0.63.2): Die Marke ist genau der Zeitpunkt des
        Loeschens mit Zone (nicht mehr 1 s frueher)."""
        for jetzt in ("2026-10-25 02:00:00+01:00", "2027-01-01 00:00:00+01:00",
                      "2026-07-01 12:30:15+02:00", "2026-07-01 12:30:15-05:30"):
            db = neue_db("bg17_marke")
            with mock.patch.object(fisi_core.DBManager, "_marker_now",
                                   staticmethod(lambda cur, v=jetzt: (v, 0))):
                self.assertTrue(db.reset_records())
            self.assertEqual(db.get_meta("bestenliste_reset_at"), jetzt)

    # (Marke, Stempel des Geraets (Ortszeit, Abstand min), erwarteter Stempel)
    _FG100_FAELLE = [
        # dieselbe Sekunde, gleiche Zone -> Marke + 1 s
        ("2026-07-01 12:30:15+02:00", ("2026-07-01 12:30:15", 120), ("2026-07-01 12:30:16", 120)),
        # schon nach der Marke -> unveraendert
        ("2026-07-01 12:30:15+02:00", ("2026-07-01 12:30:16", 120), ("2026-07-01 12:30:16", 120)),
        # Marke von einem Geraet in anderer Zone, in UTC gleich -> Marke + 1 s in deren Zone
        ("2026-07-01 12:30:15-05:30", ("2026-07-01 20:00:15", 120), ("2026-07-01 12:30:16", -330)),
        # andere Zone, in UTC und als Text danach -> unveraendert
        ("2026-07-01 12:30:15-05:30", ("2026-07-01 20:00:16", 120), ("2026-07-01 20:00:16", 120)),
        # Zeitumstellung (doppelte Stunde): als Text spaeter, in UTC frueher -> Marke + 1 s
        ("2026-10-25 02:30:00+01:00", ("2026-10-25 02:45:00", 120), ("2026-10-25 02:30:01", 60)),
        # Zeitumstellung: in UTC spaeter, als Text frueher (Mischbetrieb liest als Text)
        ("2026-10-25 02:59:59+02:00", ("2026-10-25 02:00:00", 60), ("2026-10-25 03:00:00", 120)),
        # Zeitumstellung Fruehjahr, dieselbe Sekunde
        ("2026-03-29 03:00:00+02:00", ("2026-03-29 03:00:00", 120), ("2026-03-29 03:00:01", 120)),
        # Jahreswechsel
        ("2026-12-31 23:59:59+01:00", ("2026-12-31 23:59:59", 60), ("2027-01-01 00:00:00", 60)),
        # Marke mit Sekundenbruchteil
        ("2026-07-01 12:30:15.250000+02:00", ("2026-07-01 12:30:15", 120),
         ("2026-07-01 12:30:16", 120)),
        # Marke ohne Zone (wie bis 0.62.3): als Text, Abstand des Geraets bleibt
        ("2026-07-01 12:30:15", ("2026-07-01 12:30:15", 120), ("2026-07-01 12:30:16", 120)),
        ("2026-07-01 12:30:15", ("2026-07-01 12:30:16", 120), ("2026-07-01 12:30:16", 120)),
        # keine bzw. ungueltige Marke -> unveraendert
        (None, ("2026-07-01 12:30:15", 120), ("2026-07-01 12:30:15", 120)),
        ("x", ("2026-07-01 12:30:15", 120), ("2026-07-01 12:30:15", 120)),
        ("2026-02-30 12:00:00+01:00", ("2026-02-28 12:00:00", 60), ("2026-02-28 12:00:00", 60)),
    ]

    def test_b_g_17_fg100_stempel_zonen_und_zeitumstellung(self):
        """FG-100 (neu, 0.63.2): Der Eintrag liegt danach nach der Marke - in
        UTC (Abgleich mit Zone) und als Text (Mischbetrieb) -, und der Abgleich
        mit der eigenen Datei behaelt ihn."""
        for marke, stempel, soll in self._FG100_FAELLE:
            with self.subTest(marke=marke, stempel=stempel):
                db = neue_db("bg17_stempel")
                if marke is not None:
                    db.set_meta("bestenliste_reset_at", marke)
                with mock.patch.object(fisi_core.DBManager, "_stamp",
                                       lambda self, v=stempel: v):
                    self.assertTrue(db.log_record("l", "rekord", "k", 1.0))
                ist = zeilen(db.db_path, "SELECT timestamp, utc_offset FROM spiel_bestenliste")
                self.assertEqual(ist, [soll])
                geparst = fisi_sync.parse_marker(marke)
                if geparst:
                    self.assertGreater(soll[0], geparst[0][:19])
                    if geparst[1] is not None:
                        utc = (datetime.datetime.strptime(soll[0], "%Y-%m-%d %H:%M:%S")
                               - datetime.timedelta(minutes=soll[1]))
                        self.assertGreater(utc, geparst[1])
                fisi_sync.merge_into_local(db, fisi_sync.export_local(db), check_future=False)
                self.assertEqual(zeilen(db.db_path, "SELECT count(*) FROM spiel_bestenliste"),
                                 [(1,)])

    def test_b_g_17_fg100_fremd_selbe_sekunde_vorher_weg(self):
        """FG-100 (neu, 0.63.2): Ein Eintrag eines anderen Geraets aus derselben
        Sekunde wie die Marke (vor dem Loeschen entstanden) verschwindet beim
        Abgleich; der eigene neue Eintrag bleibt."""
        db = neue_db("bg17_fremd")
        sekundenanfang()
        jetzt = fisi_core.device_now()      # Sekunde des Loeschens
        db.reset_records()
        self.assertEqual(fisi_core.device_now().strftime("%Y-%m-%d %H:%M:%S"),
                         jetzt.strftime("%Y-%m-%d %H:%M:%S"), "Sekunde gewechselt")
        db.log_record("lauf1", "rekord", "nachher", 2.0)
        marke = db.get_meta("bestenliste_reset_at")
        bericht("FG-100 fremd: Loeschen %s, Marke %s" % (fisi_core.format_with_zone(jetzt), marke))
        columns = list(fisi_sync.SYNC_TABLES["spiel_bestenliste"])
        werte = {"timestamp": jetzt.strftime("%Y-%m-%d %H:%M:%S"),
                 "utc_offset": fisi_core.offset_minutes(jetzt), "durchgang": "l2",
            "art": "rekord", "schluessel": "fremd-selbe-sekunde", "wert": 3.0, "daten": "{}"}
        fremd = {"format": fisi_sync.FORMAT, fisi_sync.WRITER_KEY: "x", "markers": {},
                 "columns": {"spiel_bestenliste": columns},
                 "tables": {"spiel_bestenliste": [["u-fremd"] + [werte[c] for c in columns]]}}
        fisi_sync.merge_into_local(db, fremd, check_future=False)
        self.assertEqual(zeilen(db.db_path, "SELECT schluessel FROM spiel_bestenliste"),
                         [("nachher",)])

    def test_b_g_17_schutz_andere_loeschknoepfe(self):
        """Schutz: "Alle Lerndaten loeschen", "Historie loeschen" und
        "Spielstand zuruecksetzen" setzen die Marke wie bisher (unveraendert)."""
        jetzt = "2026-07-01 12:30:15+02:00"
        db = neue_db("bg17_andere")
        with mock.patch.object(fisi_core.DBManager, "_marker_now",
                               staticmethod(lambda cur: (jetzt, 0))):
            db.reset_all()
            db.clear_history()
            db.reset_game()
        for key in ("reset_at", "history_cleared_at", "spiel_reset_at"):
            self.assertEqual(db.get_meta(key), jetzt, key)

    def test_b_g_17_schutz_vorher_bleibt_weg(self):
        """Schutz: Ein Eintrag eines anderen Geraets VOR dem Loeschen (2 s)
        verschwindet beim Abgleich weiter."""
        db = neue_db("bg17_vorher")
        sekundenanfang()
        db.reset_records()
        marke = db.get_meta("bestenliste_reset_at")
        vorher = (fisi_core.datetime.datetime.strptime(marke[:19], "%Y-%m-%d %H:%M:%S")
                  - fisi_core.datetime.timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
        columns = list(fisi_sync.SYNC_TABLES["spiel_bestenliste"])
        werte = {"timestamp": vorher, "utc_offset": int(marke[-6:-3]) * 60 + (
            1 if marke[-6] == "+" else -1) * int(marke[-2:]), "durchgang": "l2",
            "art": "rekord", "schluessel": "fremd-vorher", "wert": 3.0, "daten": "{}"}
        fremd = {"format": fisi_sync.FORMAT, fisi_sync.WRITER_KEY: "x", "markers": {},
                 "columns": {"spiel_bestenliste": columns},
                 "tables": {"spiel_bestenliste": [["u-fremd"] + [werte[c] for c in columns]]}}
        fisi_sync.merge_into_local(db, fremd, check_future=False)
        self.assertEqual(zeilen(db.db_path, "SELECT count(*) FROM spiel_bestenliste"), [(0,)])


# ============================================================================
#  B-G-29: sehr alte Datenbank ohne uid
# ============================================================================

class BG29AlteDatenbank(unittest.TestCase):

    def test_b_g_29_zwei_kopien_gleiche_uids(self):
        """Zwei Kopien derselben alten Datei bekommen dieselben uids; nach dem
        Zusammenfuehren 5 Karten, nicht 10."""
        vorlage = alte_db(neuer_pfad("bg29_vorlage"))
        kopien = []
        for name in ("bg29_a", "bg29_b"):
            path = neuer_pfad(name)
            shutil.copyfile(vorlage, path)
            kopien.append(fisi_core.DBManager(path, error_handler=lambda m: None))
        uids = [zeilen(db.db_path, "SELECT uid FROM card_events ORDER BY id") for db in kopien]
        bericht("B-G-29 uids Kopie A %s..., Kopie B %s..." % (uids[0][0], uids[1][0]))
        self.assertEqual(uids[0], uids[1])
        self.assertEqual(len({u for (u,) in uids[0]}), 5)
        for (u,) in uids[0]:
            self.assertRegex(u, r"^[0-9a-f]{32}$")
        a, b = kopien
        fisi_sync.merge_into_local(a, fisi_sync.export_local(b), check_future=False)
        self.assertEqual(zeilen(a.db_path, "SELECT count(*) FROM card_events"), [(5,)])
        self.assertEqual(zeilen(a.db_path, "SELECT count(*) FROM quiz_answers"), [(1,)])

    def test_b_g_29_keine_schreibzugriffe_ohne_eintraege_ohne_uid(self):
        """F5 (i): Hat jeder Eintrag eine uid, schreibt _migrate nichts zur uid
        (kein UPDATE), die Datei bleibt byte-gleich."""
        db = neue_db("bg29_schreib")
        db.log_card("Kat", "a", "karte", 1)
        db.log_record("l", "rekord", "k", 1.0)
        vorher = sha(db.db_path)
        statements = []
        echt = sqlite3.connect

        def connect(*args, **kwargs):
            conn = echt(*args, **kwargs)
            conn.set_trace_callback(statements.append)
            return conn

        with mock.patch.object(fisi_core.sqlite3, "connect", connect):
            fisi_core.DBManager(db.db_path, error_handler=lambda m: None)
        # Nur Schreibzugriffe, die die uid betreffen (die Umbenennung alter
        # Fragetexte beim Start, apply_question_renames, ist davon unabhaengig
        # und trifft hier keine Zeile)
        schreibend = [s for s in statements if s.lstrip().split(" ", 1)[0].upper()
                      in ("UPDATE", "INSERT", "DELETE", "ALTER", "REPLACE") and "uid" in s]
        bericht("B-G-29 Start: %d Anweisungen, schreibend zur uid %s"
                % (len(statements), schreibend))
        self.assertEqual(schreibend, [])
        self.assertEqual(sha(db.db_path), vorher)

    def test_b_g_29_schutz_vorhandene_uids_unveraendert(self):
        """Schutz (ii): vorhandene uids bleiben, auch wenn daneben Eintraege
        ohne uid nachgetragen werden."""
        db = neue_db("bg29_vorhanden")
        for i in range(3):
            db.log_card("Kat", "k%d" % i, "karte", 1)
        alt = zeilen(db.db_path, "SELECT id, uid FROM card_events ORDER BY id")
        conn = sqlite3.connect(db.db_path)
        conn.execute("INSERT INTO card_events (timestamp, category, question, mode, correct)"
                     " VALUES ('2023-01-01 10:00:00', 'Kat', 'ohne uid', 'karte', 1)")
        conn.commit()
        conn.close()
        fisi_core.DBManager(db.db_path, error_handler=lambda m: None)
        neu = zeilen(db.db_path, "SELECT id, uid FROM card_events ORDER BY id")
        self.assertEqual(neu[:3], alt)
        self.assertRegex(neu[3][1], r"^[0-9a-f]{32}$")
        self.assertNotIn(neu[3][1], {u for _, u in alt})

    def test_b_g_29_kollision_zufaellige_uid(self):
        """F5 (iv): Ist die abgeleitete uid schon vergeben, gibt es eine
        zufaellige; der Start gelingt (eindeutiger Index), nichts geht verloren."""
        db = neue_db("bg29_kollision")
        conn = sqlite3.connect(db.db_path)
        conn.execute("INSERT INTO card_events (timestamp, category, question, mode, correct)"
                     " VALUES ('2023-01-01 10:00:00', 'Kat', 'ohne uid', 'karte', 1)")
        conn.commit()
        rowid = conn.execute("SELECT id FROM card_events").fetchone()[0]
        conn.close()
        besetzt = abgeleitete_uid(db.db_path, "card_events", rowid)
        conn = sqlite3.connect(db.db_path)
        conn.execute("INSERT INTO card_events (timestamp, category, question, mode, correct, "
                     "uid) VALUES ('2023-01-02 10:00:00', 'Kat', 'besetzt', 'karte', 0, ?)",
                     (besetzt,))
        conn.commit()
        conn.close()
        meldungen = []
        neu = fisi_core.DBManager(db.db_path, error_handler=meldungen.append)
        rows = dict(zeilen(db.db_path, "SELECT question, uid FROM card_events"))
        bericht("B-G-29 Kollision: besetzt %s, neu %s" % (besetzt, rows["ohne uid"]))
        self.assertEqual(meldungen, [])
        self.assertIsNone(neu.read_only_reason)
        self.assertEqual(rows["besetzt"], besetzt)
        self.assertRegex(rows["ohne uid"] or "", r"^[0-9a-f]{32}$")
        self.assertNotEqual(rows["ohne uid"], besetzt)


# ============================================================================
#  Z4: Beispiel statt echtem Repository
# ============================================================================

class BG08Kern(unittest.TestCase):
    """B-G-08 im Testprozess: "Alles ersetzen" merkt sich die Aufhebung
    (fisi_sicherung.replace_all), der Abgleich wendet sie an
    (fisi_sync.merge_into_local), export_local schreibt das Feld."""
    R0 = "2026-09-01 10:00:00+02:00"
    R1 = "2026-10-03 10:00:00+02:00"
    R = "2026-10-05 10:00:00+02:00"
    R2 = "2026-10-07 10:00:00+02:00"

    def db_mit(self, name, marke, karten=()):
        db = neue_db(name)
        conn = sqlite3.connect(db.db_path)
        try:
            for etikett, zeit in karten:
                conn.execute("INSERT INTO card_events (timestamp, utc_offset, category, "
                             "question, mode, correct, uid) VALUES (?, 120, 'Kat', ?, "
                             "'karte', 1, ?)", (zeit, etikett, "uid-" + etikett))
            if marke:
                conn.execute("INSERT INTO sync_meta (key, value) VALUES ('reset_at', ?)",
                             (marke,))
            conn.commit()
        finally:
            conn.close()
        return db

    def sicherung(self, marke, karten):
        db = self.db_mit("sicherung", marke, karten)
        return fsi.read_backup(fsi.create_backup(db, "test"))

    def ersetzen(self, db, backup):
        fsi.replace_all(db, backup, os.path.join(os.path.dirname(db.db_path), "kopie"))

    @staticmethod
    def datei(marke):
        return {"format": fisi_sync.FORMAT, fisi_sync.WRITER_KEY: fisi_sync.WRITER,
                "markers": {"reset_at": marke} if marke else {},
                "columns": {"card_events": list(fisi_sync.SYNC_TABLES["card_events"])},
                "tables": {"card_events": []}}

    @staticmethod
    def karten(db):
        return sorted(r[0] for r in zeilen(db.db_path, "SELECT question FROM card_events"))

    def test_b_g_08_kern_ersetzen_merkt_aufhebung(self):
        """Ersetzen (Geraet: Marke R, Sicherung: R0) -> Aufhebung [R, R0] in
        sync_meta und im Feld "aufgehoben"; die Datei mit R loescht nichts;
        eine spaetere Loeschung R2 gilt wieder."""
        db = self.db_mit("kern1", self.R)
        self.ersetzen(db, self.sicherung(self.R0, [("k1", "2026-10-02 12:00:00")]))
        self.assertEqual(json.loads(db.get_meta("aufgehoben:reset_at")), [self.R, self.R0])
        self.assertEqual(fisi_sync.export_local(db)["aufgehoben"],
                         {"reset_at": [self.R, self.R0]})
        fisi_sync.merge_into_local(db, self.datei(self.R), check_future=False, mixed=False)
        self.assertEqual(self.karten(db), ["k1"])
        self.assertEqual(db.get_meta("reset_at"), self.R0)
        fisi_sync.merge_into_local(db, self.datei(self.R2), check_future=False, mixed=False)
        self.assertEqual(self.karten(db), [])
        self.assertEqual(db.get_meta("reset_at"), self.R2)

    def test_b_g_08_kern_zweimal_ersetzen_aeltere_sicherung(self):
        """Zweimal ersetzen, die zweite Sicherung ist aelter (R1, dann R0):
        Die Aufhebung umfasst beide ([R, R0]), die Datei mit R loescht keine
        der eingespielten Karten (k0 liegt zwischen R0 und R1)."""
        db = self.db_mit("kern2", self.R)
        self.ersetzen(db, self.sicherung(self.R1, [("k1", "2026-10-04 12:00:00")]))
        self.assertEqual(json.loads(db.get_meta("aufgehoben:reset_at")), [self.R, self.R1])
        self.ersetzen(db, self.sicherung(self.R0, [("k0", "2026-10-02 12:00:00"),
                                                   ("k1", "2026-10-04 12:00:00")]))
        self.assertEqual(json.loads(db.get_meta("aufgehoben:reset_at")), [self.R, self.R0])
        fisi_sync.merge_into_local(db, self.datei(self.R), check_future=False, mixed=False)
        self.assertEqual(self.karten(db), ["k0", "k1"])

    def test_b_g_08_kern_sicherung_kennt_loeschung(self):
        """Schutz: Sicherung mit derselben Marke wie das Geraet -> keine
        Aufhebung, export_local ohne das Feld (wie bisher)."""
        db = self.db_mit("kern3", self.R)
        self.ersetzen(db, self.sicherung(self.R, [("k1", "2026-10-06 12:00:00")]))
        self.assertIsNone(db.get_meta("aufgehoben:reset_at"))
        self.assertNotIn("aufgehoben", fisi_sync.export_local(db))
        fisi_sync.merge_into_local(db, self.datei(self.R), check_future=False, mixed=False)
        self.assertEqual(self.karten(db), ["k1"])

    def test_b_g_08_kern_vereinigung_in_jeder_reihenfolge(self):
        """Zwei Geraete mit verschiedenen Aufhebungen kommen auf dieselbe."""
        paare = [[self.R, self.R0], [self.R2, self.R1], [self.R1, ""], [self.R, self.R1]]
        for eins in paare:
            for zwei in paare:
                self.assertEqual(fisi_sync._union_lift(eins, zwei),
                                 fisi_sync._union_lift(zwei, eins), (eins, zwei))
        self.assertEqual(fisi_sync._union_lift([self.R, self.R0], [self.R2, self.R1]),
                         [self.R2, self.R0])
        self.assertEqual(fisi_sync._union_lift([self.R, self.R1], [self.R1, ""]), [self.R, ""])


class Z4Beispiel(unittest.TestCase):

    def test_z4_meldung_mit_beispiel(self):
        db = neue_db("z4")
        with self.assertRaises(fisi_sync.SyncError) as caught:
            fisi_sync.sync(db, settings={"sync_repo": "ohneschraegstrich",
                                         "sync_token": TOKEN})
        text = str(caught.exception)
        bericht("Z4: %s" % text)
        self.assertEqual(text, "Das Repository bitte als „Benutzer/Name“ angeben, "
                               "z. B. deinname/fisi-lernstand.")
        with open(os.path.join(CODE, "fisi_sync.py"), encoding="utf-8") as handle:
            self.assertNotIn("papst2142", handle.read())


# ============================================================================
#  Geraete-Tests: altes Geraet -> neues Geraet, Mischbetrieb, Fingerabdruck
# ============================================================================

class GeraetVoll(ta.Geraet):
    """Wie test_abgleich.Geraet, aber mit pruefung/abgleich_geraet_voll.py
    (voller Lernstand) und wahlweise einer vorhandenen Datenbank (vorlage)."""

    def __init__(self, ordner, name, tz="Europe/Berlin", code=CODE, uhr=0.0, vorlage=None):
        self.name, self.code = name, code
        self.home = os.path.join(ta.WORK, ordner, name)
        os.makedirs(os.path.join(self.home, "tmp"), exist_ok=True)
        if vorlage:
            shutil.copyfile(vorlage, os.path.join(self.home, "lern.db"))
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": self.home,
               "TMPDIR": os.path.join(self.home, "tmp"),
               "FISI_DB_PATH": os.path.join(self.home, "lern.db"), "TZ": tz,
               "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C.UTF-8",
               "PYTHONIOENCODING": "utf-8"}
        self.err = open(os.path.join(self.home, "stderr.txt"), "a")
        self.proc = subprocess.Popen(
            [sys.executable, "-I", "-B", VOLL, code, ta.API, name], env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.err, text=True,
            encoding="utf-8", cwd=self.home)
        first = self.proc.stdout.readline()
        if not first:
            raise RuntimeError("Geraet %s startet nicht: %s" % (name, self._stderr()))
        if uhr:
            self("uhr", uhr)


# Spalten, die von Ablauf zu Ablauf anders sind (Zeit, Kennung): fuer den
# Vergleich "gemischt" gegen "nur v0.63.1" weggelassen
_FLUECHTIG = ("uid", "timestamp", "utc_offset")


def inhalt_ohne_zeit(inhalt):
    """{tabelle: sortierte Inhalte ohne uid/Zeit} aus dem Befehl "inhalt"."""
    result = {}
    for table, rows in inhalt["tabellen"].items():
        columns = ["uid"] + list(fisi_sync.SYNC_TABLES[table])
        keep = [i for i, c in enumerate(columns) if c not in _FLUECHTIG]
        result[table] = sorted(json.dumps([json.loads(r)[i] for i in keep], ensure_ascii=False)
                               for r in rows)
    return result


# Weisung zu Meldung 41, Frage 9 (erst im Integrationsstand mit S6c/B-G-09):
# Loescht ein Geraet mit 0.63.2 ein Projekt, schreibt es je Feld eine leere
# neuere Fassung (B-G-09); 0.63.1 blendet nur aus. Erwartet wird deshalb genau
# fuer diese Projekte "" statt des Texts - fuer kein anderes Projekt.
PROJEKTE_LEER = None    # Kontrollfehler: {"Projekt a-2"} zusaetzlich muss rot werden


def projekt_leer_erwarten(referenz, projekte):
    """referenz (inhalt_ohne_zeit) mit leeren Feldern fuer projekte."""
    projekte = set(projekte) | set(PROJEKTE_LEER or ())
    if not projekte:
        return referenz
    neu = dict(referenz)
    zeilen_neu = []
    for zeile in referenz.get("abschlussprojekt", []):
        werte = json.loads(zeile)
        if werte[0] in projekte and werte[1] != "_geloescht":
            werte[2] = ""
        zeilen_neu.append(json.dumps(werte, ensure_ascii=False))
    neu["abschlussprojekt"] = sorted(zeilen_neu)
    return neu


class GeraeteTest(unittest.TestCase):
    """Geraete-Prozesse gegen die Attrappe (Werkzeuge aus test_abgleich, ohne
    dessen Tests zu erben)."""
    setUp = ta.AbgleichTest.setUp
    tearDown = ta.AbgleichTest.tearDown
    alle_sync = ta.AbgleichTest.alle_sync
    stabil = ta.AbgleichTest.stabil
    alter_code = ta.AbgleichTest.alter_code

    def voll(self, name, code=CODE, ordner=None, **kwargs):
        device = GeraetVoll(ordner or self.id().rsplit(".", 1)[-1], name, code=code, **kwargs)
        self.geraete.append(device)
        return device

    def neu_starten(self, device, code):
        """Dasselbe Geraet (gleiches HOME, gleiche Datenbank) mit anderem Code."""
        device.close()
        self.geraete.remove(device)
        return self.voll(device.name, code=code,
                         ordner=os.path.basename(os.path.dirname(device.home)))

    def gleich_und_ohne_doppelte(self, geraete):
        bezug = geraete[0]("inhalt")
        for device in geraete:
            stand = device("inhalt")
            self.assertEqual(stand, bezug, "%s weicht von %s ab" % (device.name, geraete[0].name))
            for table, werte in device("zaehle")["tabellen"].items():
                self.assertEqual(werte["doppelt"], 0, "%s %s" % (device.name, table))
                self.assertEqual(werte["zeilen"], werte["uids"], "%s %s" % (device.name, table))
        return bezug

    # ------------------------------------------------------------ T-a
    def _alte_datenbank(self, ordner):
        """Datenbank mit Code v0.63.1 und vollem Inhalt: alle Tabellen, alle
        Loeschmarken, Projekt geloescht (ausgeblendet), Eintraege danach."""
        alt = self.alter_code(ALT)
        a = self.voll("A", code=alt, ordner=ordner)
        a("fuelle", "vor")
        a("lerne", 3, "vor")
        ta.pause()
        for knopf in ("reset_all", "clear_history", "reset_records"):
            self.assertTrue(a(knopf)["ok"], knopf)
        a("setmeta", "spiel_reset_at", "2026-01-02 03:04:05+01:00")
        ta.pause()
        a("fuelle", "nach")
        a("lerne", 2, "nach")
        a("projekt_loeschen", "Projekt a-nach")
        return a

    def test_t_a_altes_geraet_neues_geraet_byte_gleich(self):
        """T-a: Datenbank mit Code v0.63.1 anlegen, mit 0.63.2 oeffnen ->
        Datei byte-gleich (ohne -wal/-journal); Abgleich danach -> dieselben
        Zahlen wie vorher, mit v0.63.1 und mit 0.63.2 gleich."""
        a = self._alte_datenbank("t_a")
        vorher = a("db_sha")
        anzahl_alt = a("schluessel")["anzahl"]
        a = self.neu_starten(a, CODE)
        nachher = a("db_sha")
        bericht("T-a v0.63.1: %s (%d Byte) -> neu: %s (%d Byte), Nebendateien %s"
                % (vorher["sha"][:16], vorher["groesse"], nachher["sha"][:16],
                   nachher["groesse"], nachher["nebendateien"]))
        self.assertEqual(nachher["sha"], vorher["sha"], "Datei nach dem Oeffnen veraendert")
        self.assertEqual(nachher["groesse"], vorher["groesse"])
        self.assertEqual(nachher["nebendateien"], [])
        self.assertEqual(a("schluessel")["anzahl"], anzahl_alt)
        a.sync()
        self.assertEqual(a("schluessel")["anzahl"], anzahl_alt)
        # zweites Geraet (v0.63.1) holt alles; beide gleich, kein Hin und Her
        b = self.voll("B", code=self.alter_code(ALT))
        b.sync()
        a.sync()
        self.assertEqual(b("schluessel")["anzahl"], anzahl_alt)
        self.gleich_und_ohne_doppelte([a, b])
        self.stabil([a, b])
        bericht("T-a Zahlen je Tabelle: %s" % anzahl_alt)

    # ------------------------------------------------------------ Fingerabdruck
    def test_abgleich_fingerabdruck_alt_neu_gleich(self):
        """Abgleich-Fingerabdruck: dieselbe Datenbank (Kopie), export_local
        mit v0.63.1 und mit 0.63.2 -> gleiches kanonisches JSON."""
        a = self._alte_datenbank("fp")
        alt = a("export_sha")
        vorlage = os.path.join(WORK_KERN, "fp_vorlage.db")
        a.close()
        self.geraete.remove(a)
        shutil.copyfile(os.path.join(a.home, "lern.db"), vorlage)
        b = self.voll("B", code=CODE, ordner="fp_neu", vorlage=vorlage)
        neu = b("export_sha")
        bericht("Abgleich-Fingerabdruck v0.63.1 %s / neu %s (%d Zeilen)"
                % (alt["sha"], neu["sha"], neu["zeilen"]))
        ziel = os.environ.get("ABGLEICH_FP_BELEG")
        if ziel:
            with open(ziel, "w", encoding="utf-8") as handle:
                json.dump({"alt_v0.63.1": alt, "neu": neu, "code": CODE,
                           "gleich": alt == neu}, handle, indent=1)
        self.assertEqual(neu, alt)

    # ------------------------------------------------------------ B-G-17 Mischbetrieb
    def test_b_g_17_mischbetrieb_altes_geraet_behaelt(self):
        """B (0.63.2) loescht die Bestenliste, der Eintrag derselben Sekunde
        kommt auch auf A (v0.63.1) an und bleibt; kein Hin und Her."""
        a = self.voll("A", code=self.alter_code(ALT))
        b = self.voll("B")
        a("bestenliste", "alt")
        self.alle_sync([a, b], 1)
        ta.pause()
        antwort = b("bestenliste_neu", "neu")
        bericht("B-G-17 Mischbetrieb: Marke %s, Eintrag %s"
                % (antwort["marke"], antwort["eintraege"]))
        self.alle_sync([b, a, b, a], 1)
        for device in (a, b):
            keys = [json.loads(r)[5] for r in device("inhalt")["tabellen"]["spiel_bestenliste"]]
            self.assertEqual(keys, ["b-neu"], device.name)
        self.stabil([a, b])

    def test_b_g_17_fg100_mischbetrieb_zonen_und_altes_geraet_loescht(self):
        """FG-100 (neu, 0.63.2): B (0.63.2, Zone UTC) loescht, sein Eintrag
        derselben Sekunde traegt Marke + 1 s und bleibt auch auf A (v0.63.1,
        Europe/Berlin). Loescht danach A (v0.63.1), ist alles weg wie mit
        0.63.1; ein spaeterer Eintrag von B kommt ueberall an; kein Hin und Her."""
        a = self.voll("A", code=self.alter_code(ALT))
        b = self.voll("B", tz="UTC")

        def schluessel():
            return {d.name: sorted(json.loads(r)[5] for r in
                                   d("inhalt")["tabellen"]["spiel_bestenliste"]) for d in (a, b)}
        a("bestenliste", "alt")
        b("bestenliste", "vorher")
        self.alle_sync([a, b, a], 1)
        ta.pause()
        antwort = b("bestenliste_neu", "neu")
        marke = antwort["marke"]
        bericht("FG-100 Mischbetrieb: Marke B %s, Eintrag %s" % (marke, antwort["eintraege"]))
        self.assertTrue(marke.endswith("+00:00"), marke)
        self.assertEqual(antwort["eintraege"], [(datetime.datetime.strptime(
            marke[:19], "%Y-%m-%d %H:%M:%S") + datetime.timedelta(seconds=1)).strftime(
                "%Y-%m-%d %H:%M:%S")])
        self.alle_sync([b, a, b, a], 1)
        self.assertEqual(schluessel(), {"A": ["b-neu"], "B": ["b-neu"]})
        ta.pause()
        antwort = a("bestenliste_neu", "neu")
        bericht("FG-100 Mischbetrieb: Marke A (v0.63.1) %s, Eintrag %s"
                % (antwort["marke"], antwort["eintraege"]))
        self.alle_sync([a, b, a, b], 1)
        self.assertEqual(schluessel(), {"A": [], "B": []})
        ta.pause()
        b("bestenliste", "spaeter")
        self.alle_sync([b, a, b], 1)
        self.assertEqual(schluessel(), {"A": ["b-spaeter"], "B": ["b-spaeter"]})
        self.stabil([a, b])

    # ------------------------------------------------------------ B-G-29 Geraete
    def test_b_g_29_alte_db_kopie_zwei_geraete(self):
        """Fall D6: alte Datei (vor v0.24) auf zwei Geraete kopiert, beide
        0.63.2, Abgleich -> 5 Karten (vorher 10)."""
        vorlage = alte_db(os.path.join(WORK_KERN, "d6_vorlage.db"))
        a = self.voll("A", vorlage=vorlage)
        b = self.voll("B", vorlage=vorlage)
        self.alle_sync([a, b, a], 1)
        for device in (a, b):
            self.assertEqual(device("schluessel")["anzahl"]["card_events"], 5, device.name)
        self.gleich_und_ohne_doppelte([a, b])
        self.stabil([a, b])

    def test_grenze_b_g_29_kopie_mit_v0631(self):
        """Grenz-Test (bekannte Grenze, kein Fehler des Fixes): Oeffnet ein
        Geraet mit v0.63.1 die Kopie, bekommt es zufaellige uids - dann bleibt
        es wie bisher bei 10. Haelt das Verhalten fest; aendert es sich, faellt
        es hier auf."""
        vorlage = alte_db(os.path.join(WORK_KERN, "d6g_vorlage.db"))
        a = self.voll("A", vorlage=vorlage)
        b = self.voll("B", code=self.alter_code(ALT), vorlage=vorlage)
        self.alle_sync([a, b, a], 1)
        for device in (a, b):
            self.assertEqual(device("schluessel")["anzahl"]["card_events"], 10, device.name)
        self.stabil([a, b])

    # ------------------------------------------------------------ T-b / T-c
    def mischbetrieb(self, code_a, code_b, code_c, a_zuerst=True, zwischen=None, lauf="",
                     vorher=None, pruefen=True):
        """Ablauf mit drei Geraeten (A = Nicos Geraet, B = zweites Geraet, C =
        Geraet, das waehrend der Loeschungen offline ist):
          1. alle lernen (alle Tabellen), Abgleich A, B, C, A, B
             vorher(self, a, b, c) - z.B. Sicherung erstellen (S6b)
          2. C lernt offline weiter (vor den Loeschungen)
          3. erster (A oder B) lernt, "Bestenliste loeschen" + Eintrag in
             derselben Sekunde, "Projekt loeschen"; Abgleich
          4. zweiter lernt, "Bestenliste loeschen" + Eintrag; Abgleich
          5. erster: "Alle Lerndaten loeschen"; beide lernen danach;
             3 Runden Abgleich, Ruhe
          6. zwischen(self, a, b, c) - Platz fuer weitere Schritte (S6b)
          7. C kommt zurueck, lernt, 3 Runden Abgleich mit allen, Ruhe
        Rueckgabe: Lernstand ohne uid/Zeit (gleich auf allen Geraeten).
        pruefen=False (S6b, B-G-08 mit Hin und Her): ohne Ruhe und ohne
        Gleichheit am Ende; Rueckgabe ({Geraet: Lernstand ohne uid/Zeit},
        (a, b, c))."""
        ordner = self.id().rsplit(".", 1)[-1] + lauf
        a = self.voll("A", code=code_a, ordner=ordner)
        b = self.voll("B", code=code_b, ordner=ordner)
        c = self.voll("C", code=code_c, tz="UTC", ordner=ordner)
        for device in (a, b, c):
            device("fuelle", "1")
        self.alle_sync([a, b, c, a, b], 1)
        if vorher:
            vorher(self, a, b, c)
        ta.pause()
        c("fuelle", "2-offline")
        ta.pause()
        erster, zweiter = (a, b) if a_zuerst else (b, a)
        erster("fuelle", "2")
        bericht("Bestenliste %s: %s" % (erster.name, erster("bestenliste_neu", "bl1")))
        erster("projekt_loeschen", "Projekt a-1")
        self.alle_sync([erster, zweiter], 1)
        ta.pause()
        zweiter("fuelle", "2")
        bericht("Bestenliste %s: %s" % (zweiter.name, zweiter("bestenliste_neu", "bl2")))
        self.alle_sync([zweiter, erster], 1)
        ta.pause()
        self.assertTrue(erster("reset_all")["ok"])
        ta.pause()
        zweiter("fuelle", "3")
        erster("fuelle", "3")
        self.alle_sync([erster, zweiter], 3)
        self.stabil([a, b])
        if zwischen:
            zwischen(self, a, b, c)
        c("fuelle", "3")
        self.alle_sync([c, a, b], 3)
        if not pruefen:
            return {d.name: inhalt_ohne_zeit(d("inhalt")) for d in (a, b, c)}, (a, b, c)
        self.stabil([a, b, c])
        stand = self.gleich_und_ohne_doppelte([a, b, c])
        meta_b = b("meta")["meta"]
        bericht("Mischbetrieb-Merker auf B: %s" % meta_b.get(fisi_sync.MIXED_KEY))
        if code_a != CODE or code_b != CODE:
            # Geraete ab 0.62.4 schreiben "schreiber": kein Mischbetrieb-Merker
            self.assertIsNone(meta_b.get(fisi_sync.MIXED_KEY))
        return inhalt_ohne_zeit(stand), stand

    def _vergleich_mit_v0631(self, a_zuerst, code_c):
        """Mischbetrieb gegen denselben Ablauf nur mit v0.63.1: gleich bis auf
        den Bestenliste-Eintrag, den 0.63.2 nach eigenem Loeschen behaelt."""
        alt = self.alter_code(ALT)
        referenz, _ = self.mischbetrieb(alt, alt, alt, a_zuerst, lauf="_nur_alt")
        # T-c: B (0.63.2) loescht "Projekt a-1" (Frage 9)
        referenz = projekt_leer_erwarten(referenz, () if a_zuerst else ("Projekt a-1",))
        for device in list(self.geraete):
            device.close()
            self.geraete.remove(device)
        ta.server_reset()
        gemischt, roh = self.mischbetrieb(alt, CODE, code_c, a_zuerst, lauf="_gemischt")
        for table in sorted(set(referenz) | set(gemischt)):
            ref, mix = referenz.get(table, []), gemischt.get(table, [])
            bericht("%s: nur v0.63.1 %d, gemischt %d" % (table, len(ref), len(mix)))
            if table == "spiel_bestenliste":
                verloren = set(ref) - set(mix)
                self.assertEqual(verloren, set(), "gemischt verliert mehr als v0.63.1")
            else:
                self.assertEqual(mix, ref, table)
        alle = [json.loads(r)[5] for r in roh["tabellen"]["spiel_bestenliste"]]
        bericht("Bestenliste am Ende: %s (nur v0.63.1: %s)"
                % (sorted(alle), sorted(json.loads(r)[2] for r in referenz["spiel_bestenliste"])))
        bestenliste = sorted(k for k in alle if k.endswith(("-bl1", "-bl2")))
        # Erster Bestenliste-Loescher A (v0.63.1), zweiter B (0.63.2): Bs
        # Eintrag aus derselben Sekunde bleibt (B-G-17) - auch auf A und C
        if a_zuerst:
            self.assertEqual(bestenliste, ["b-bl2"])
        else:
            self.assertEqual(bestenliste, [])
        return referenz, gemischt

    def test_t_b_mischbetrieb_altes_geraet_zuerst_offline_neu(self):
        """T-b: Nicos Geraet v0.63.1 (A) und neues Geraet 0.63.2 (B), A
        loescht zuerst; danach kommt ein Offline-Geraet mit 0.63.2 (C)."""
        self._vergleich_mit_v0631(True, CODE)

    def test_t_b_mischbetrieb_altes_geraet_zuerst_offline_alt(self):
        """T-b wie oben, das Offline-Geraet hat noch v0.63.1."""
        self._vergleich_mit_v0631(True, self.alter_code(ALT))

    def test_t_c_mischbetrieb_neues_geraet_zuerst(self):
        """T-c: umgekehrt, das neue Geraet (B, 0.63.2) loescht zuerst;
        Offline-Geraet mit 0.63.2."""
        self._vergleich_mit_v0631(False, CODE)

    def test_t_c_mischbetrieb_neues_geraet_zuerst_offline_alt(self):
        """T-c, das Offline-Geraet hat noch v0.63.1."""
        self._vergleich_mit_v0631(False, self.alter_code(ALT))



# ============================================================================
#  B-G-08 (S6b): "Alles ersetzen" nach abgeglichenem "Alle Lerndaten loeschen"
# ============================================================================

def karten(device, endung):
    """Zahl der Karteikarten, deren Etikett mit endung endet."""
    return sum(n for k, n in device.namen().items() if k.endswith(endung))


def verlauf(device):
    """Verlauf (Klausuren aus "fuelle", Tabelle pruefungen) auf dem Geraet:
    {etikett: anzahl}, direkt aus der Datenbank des Geraets gelesen."""
    result = {}
    for (raw,) in zeilen(os.path.join(device.home, "lern.db"), "SELECT daten FROM pruefungen"):
        data = json.loads(raw)
        if isinstance(data, str):
            data = json.loads(data)
        result[data["etikett"]] = result.get(data["etikett"], 0) + 1
    return result


def fehlt_gegen(referenz, stand):
    """{tabelle: Inhalte, die in referenz stehen, in stand aber fehlen}."""
    result = {}
    for table, rows in referenz.items():
        missing = sorted(set(rows) - set(stand.get(table, [])))
        if missing:
            result[table] = missing
    return result


class BG08Ersetzen(unittest.TestCase):
    """B-G-08 Weg (a), Freigabe F3/FG-12/FG-14: "Alles ersetzen" hebt eine
    schon abgeglichene Loeschung auf (Feld "aufgehoben" in der Abgleich-Datei).
    Geraete wie GeraeteTest (eigene Prozesse gegen die Attrappe)."""
    setUp = GeraeteTest.setUp
    tearDown = GeraeteTest.tearDown
    alle_sync = GeraeteTest.alle_sync
    stabil = GeraeteTest.stabil
    alter_code = GeraeteTest.alter_code
    voll = GeraeteTest.voll
    neu_starten = GeraeteTest.neu_starten
    gleich_und_ohne_doppelte = GeraeteTest.gleich_und_ohne_doppelte
    mischbetrieb = GeraeteTest.mischbetrieb

    def pfad(self, device, name="sicherung.fisisicherung"):
        return os.path.join(device.home, name)

    def ersetzen_nach_loeschen(self, a, n=5, danach=()):
        """Fall 7: n Karten, Abgleich, Sicherung, "Alle Lerndaten loeschen",
        Abgleich (auch danach: weitere Geraete), "Alles ersetzen". Liefert das
        Ergebnis des Abgleichs danach."""
        eigene = "%s-vorher" % a.name.lower()
        a("lerne", n, "vorher")
        a.sync()
        a("sicherung_erstellen", self.pfad(a))
        ta.pause()
        self.assertTrue(a("reset_all")["ok"])
        ta.pause()
        a.sync()
        for device in danach:
            device.sync()
        self.assertEqual(karten(a, eigene), 0)
        a("sicherung_ersetzen", self.pfad(a))
        self.assertEqual(karten(a, eigene), n)
        return a.sync()

    def test_b_g_08_fall7_ersetzen_nach_loeschen(self):
        """Fall 7 (Teilplan S6 1.6): nach "Alles ersetzen" bleibt der
        eingespielte Lernstand beim naechsten Abgleich (heute 5 -> 0 mit
        "5 Eintraege wegen einer Loeschung entfernt.")."""
        a = self.voll("A")
        ergebnis = self.ersetzen_nach_loeschen(a)
        bericht("B-G-08 Fall 7: %s, Karten danach %d, Datei: %s"
                % (ergebnis, karten(a, "-vorher"), ta.datei().get("aufgehoben")))
        self.assertEqual(karten(a, "-vorher"), 5)
        self.assertEqual(ergebnis["removed"], 0)
        self.assertNotIn("wegen einer Löschung", ergebnis["meldung"])
        self.assertEqual(sorted(ta.datei().get("aufgehoben", {})), ["reset_at"])
        self.assertNotIn("reset_at", ta.datei()["markers"])
        a.sync()
        self.assertEqual(karten(a, "-vorher"), 5)
        self.stabil([a])

    def test_b_g_08_zwei_neue_geraete_konvergieren(self):
        """Zwei Geraete mit 0.63.2: B hat die Loeschung schon uebernommen und
        bringt die alte Marke zurueck - sie gilt als aufgehoben. Beide haben
        danach denselben Lernstand, kein Hin und Her; Bs Eintraege nach der
        Loeschung bleiben."""
        a, b = self.voll("A"), self.voll("B", tz="UTC")
        b("lerne", 2, "vorher")
        self.alle_sync([b, a], 1)
        ergebnis = self.ersetzen_nach_loeschen(a, danach=[b])
        self.assertEqual(ergebnis["removed"], 0)
        self.assertEqual(karten(b, "-vorher"), 0)
        self.assertTrue(b("meta")["meta"].get("reset_at"))
        b.sync()            # B: alte Marke reset_at, Datei mit "aufgehoben"
        ta.pause()
        b("lerne", 2, "nachher")
        self.alle_sync([b, a], 2)
        for device in (a, b):
            namen = device.namen()
            self.assertEqual(namen.get("a-vorher"), 5, (device.name, namen))
            self.assertEqual(namen.get("b-vorher"), 2, (device.name, namen))
            self.assertEqual(namen.get("b-nachher"), 2, (device.name, namen))
        self.assertEqual(a("meta")["meta"].get("aufgehoben:reset_at"),
                         b("meta")["meta"].get("aufgehoben:reset_at"))
        self.gleich_und_ohne_doppelte([a, b])
        self.stabil([a, b])

    def test_b_g_08_schutz_offline_geraet_loescht_weiter(self):
        """Schutz: Gerät war bei der Loeschung offline (kein Ersetzen) - seine
        Eintraege von vor der Loeschung fallen weiter weg (wie heute)."""
        a, c = self.voll("A"), self.voll("C", tz="UTC")
        a("lerne", 2, "vorher")
        self.alle_sync([a, c], 1)
        c("lerne", 3, "offline")
        ta.pause()
        self.assertTrue(a("reset_all")["ok"])
        a.sync()
        ta.pause()
        a("lerne", 1, "nachher")
        self.alle_sync([c, a], 2)
        for device in (a, c):
            namen = device.namen()
            self.assertEqual(namen, {"a-nachher": 1}, device.name)
        self.stabil([a, c])

    def test_b_g_08_schutz_sicherung_kennt_loeschung(self):
        """Schutz: Kennt die Sicherung die Loeschung schon (nach dem Loeschen
        erstellt), wird nichts aufgehoben - Eintraege eines Offline-Geraets
        von vor der Loeschung fallen weiter weg."""
        a, c = self.voll("A"), self.voll("C", tz="UTC")
        a("lerne", 2, "vorher")
        self.alle_sync([a, c], 1)
        c("lerne", 3, "offline")
        ta.pause()
        self.assertTrue(a("reset_all")["ok"])
        ta.pause()
        a("lerne", 1, "nachher")
        a.sync()
        a("sicherung_erstellen", self.pfad(a))
        ta.pause()
        a("sicherung_ersetzen", self.pfad(a))
        self.alle_sync([a, c, a], 1)
        self.assertNotIn("aufgehoben", ta.datei())
        for device in (a, c):
            self.assertEqual(device.namen(), {"a-nachher": 1}, device.name)
        self.stabil([a, c])

    def test_b_g_08_schutz_neue_loeschung_nach_dem_ersetzen(self):
        """Schutz: Eine Loeschung nach dem Ersetzen gilt wieder auf allen
        Geraeten."""
        a, b = self.voll("A"), self.voll("B", tz="UTC")
        self.ersetzen_nach_loeschen(a)
        self.alle_sync([b, a], 1)
        self.assertEqual(karten(b, "-vorher"), 5)
        ta.pause()
        self.assertTrue(b("reset_all")["ok"])
        ta.pause()
        a("lerne", 1, "danach")
        self.alle_sync([b, a], 2)
        for device in (a, b):
            self.assertEqual(device.namen(), {"a-danach": 1}, device.name)
        self.stabil([a, b])

    def test_b_g_08_altes_geraet_ignoriert_feld(self):
        """FG-14: Ein Geraet mit v0.63.1 liest die Datei mit dem Feld
        "aufgehoben" ohne Fehler und verhaelt sich wie heute (der eingespielte
        Stand faellt dort weg). Das neue Geraet behaelt ihn (kein groesserer
        Verlust als heute); solange das alte Geraet mitmacht, laden beide hin
        und her (Grenze, gezaehlt). Mit 0.63.2 auf beiden: gleich, Ruhe."""
        a = self.voll("A")
        b = self.voll("B", code=self.alter_code(ALT))
        self.ersetzen_nach_loeschen(a, danach=[b])      # B kennt die Loeschung
        antwort = b("sync")
        self.assertEqual(antwort["sync"], "ok", antwort)
        self.assertEqual(karten(b, "-vorher"), 0)
        vorher = ta.commits()
        self.alle_sync([a, b], 3)
        hin_und_her = ta.commits() - vorher
        bericht("B-G-08 Mischbetrieb v0.63.1: 3 Runden A, B ohne Lernen -> %d Hochladungen; "
                "Meldung am alten Geraet: %s" % (hin_und_her, b.sync()["meldung"]))
        self.assertEqual(karten(a, "-vorher"), 5)
        self.assertEqual(karten(b, "-vorher"), 0)
        b = self.neu_starten(b, CODE)
        self.alle_sync([b, a], 2)
        for device in (a, b):
            self.assertEqual(karten(device, "-vorher"), 5, device.name)
        self.gleich_und_ohne_doppelte([a, b])
        self.stabil([a, b])

    def test_b_g_08_schutz_unbekannte_spaetere_loeschung(self):
        """Beleg FG-81 Satz 4: Eine Loeschung, die das ersetzende Geraet noch
        nicht kennt (B loescht nach As Loeschung, ohne Abgleich), gilt nach dem
        Ersetzen weiter - auch fuer das Eingespielte."""
        a, b = self.voll("A"), self.voll("B", tz="UTC")
        a("lerne", 2, "vorher")
        self.alle_sync([a, b], 1)
        a("sicherung_erstellen", self.pfad(a))
        ta.pause()
        self.assertTrue(a("reset_all")["ok"])
        self.alle_sync([a, b], 1)
        ta.pause()
        b("lerne", 1, "offline")
        ta.pause()
        self.assertTrue(b("reset_all")["ok"])      # A kennt diese Loeschung nicht
        a("sicherung_ersetzen", self.pfad(a))
        self.assertEqual(karten(a, "-vorher"), 2)
        self.alle_sync([a, b], 3)
        for device in (a, b):
            self.assertEqual(device.namen(), {}, device.name)
        self.stabil([a, b])

    def test_b_g_08_offline_eintraege_bleiben_erhalten(self):
        """gp_s6b M2, von Chat angenommen (Meldung 24, Frage 7 a), Beleg fuer
        den Satz "Auch was ein anderes Geraet ohne Verbindung gelernt hat,
        bleibt erhalten, sobald es sich wieder abgleicht.": C lernt offline,
        waehrend A alles loescht; A ersetzt danach mit einer Sicherung von vor
        der Loeschung. Mit 0.63.2 bleiben Cs Eintraege (v0.63.1: A {}, C {});
        As Eintraege zwischen Sicherung und Loeschung bleiben weg."""
        def ablauf(code, ordner):
            a = self.voll("A", code=code, ordner=ordner)
            c = self.voll("C", tz="UTC", code=code, ordner=ordner)
            a("lerne", 2, "vorher")
            self.alle_sync([a, c], 1)
            a("sicherung_erstellen", self.pfad(a))
            ta.pause()
            c("lerne", 3, "offline")
            ta.pause()
            a("lerne", 1, "zwischen")
            a.sync()
            ta.pause()
            self.assertTrue(a("reset_all")["ok"])
            a.sync()
            ta.pause()
            a("sicherung_ersetzen", self.pfad(a))
            a.sync()
            self.alle_sync([c, a], 2)
            return {d.name: d.namen() for d in (a, c)}
        alt = ablauf(self.alter_code(ALT), "m2_alt")
        for device in list(self.geraete):
            device.close()
            self.geraete.remove(device)
        ta.server_reset()
        neu = ablauf(CODE, "m2_neu")
        bericht("B-G-08 M2: v0.63.1 %s | 0.63.2 %s" % (alt, neu))
        self.assertEqual(alt, {"A": {}, "C": {}})
        for name in ("A", "C"):
            self.assertEqual(neu[name], {"a-vorher": 2, "c-offline": 3}, name)

    # ------------------------------------------------------------ FG-81 Neufassung / FG-92
    # Verhaltenstests je Satz der Texte aus der Antwort auf Meldung 31 (B.3
    # Warntext "Alles ersetzen", B.4 PREVIEW_HINT). Vorlagen: gp_s6b_nacharbeit
    # skripte/gezielt.py f2b, f2c, f4b, f4c, f5, f6, f7, f9 (Ablaeufe gleich,
    # Geraete hier mit vollem Lernstand). Zuordnung Satz -> Test:
    # bau_0.63.2/s6b/ergebnis_texte_fg81_fg92.md. Ohne Uhrverstellung.
    def _offline_drei(self, codes):
        """f4b/f4c bis vor den ersten Abgleich von C: A, B, C gleichen ab, A
        erstellt eine Sicherung, C lernt offline, A loescht alles und gleicht
        ab, B gleicht ab (kennt die Loeschung), A ersetzt, A und B gleichen
        ab. codes: Code von A, B, C."""
        a = self.voll("A", code=codes[0])
        b = self.voll("B", tz="America/New_York", code=codes[1])
        c = self.voll("C", tz="UTC", code=codes[2])
        a("lerne", 2, "vorher")
        self.alle_sync([a, b, c, a], 1)
        a("sicherung_erstellen", self.pfad(a))
        ta.pause()
        c("lerne", 3, "offline")
        ta.pause()
        self.assertTrue(a("reset_all")["ok"])
        a.sync()
        b.sync()
        self.assertEqual(karten(b, "-vorher"), 0)
        ta.pause()
        a("sicherung_ersetzen", self.pfad(a))
        a.sync()
        b.sync()
        return a, b, c

    def test_fg81_satz4_offline_guenstiger_fall_alle_0632(self):
        """FG-81 Saetze 2 und 4, guenstiger Fall (gezielt.py f4b mit NEU, NEU,
        NEU): alle Geraete hatten schon beim Ersetzen 0.63.2, C gleicht erst
        nach dem Ersetzen wieder ab -> Cs Offline-Eintraege bleiben auf allen
        Geraeten erhalten, ebenso das Eingespielte."""
        a, b, c = self._offline_drei((CODE, CODE, CODE))
        self.assertIn("aufgehoben", ta.datei())
        c.sync()
        self.assertEqual(c.namen(), {"a-vorher": 2, "c-offline": 3})
        self.alle_sync([c, a, b], 3)
        for device in (a, b, c):
            self.assertEqual(device.namen(), {"a-vorher": 2, "c-offline": 3}, device.name)
        self.stabil([a, b, c])

    def test_fg81_satz4_f4b_altes_geraet_kennt_loeschung(self):
        """FG-81 Satz 4 (Bedingung "alle deine Geraete schon beim Ersetzen
        mindestens 0.63.2") und Satz 3, gezielt.py f4b (NEU, ALT, NEU): B mit
        v0.63.1 kennt die Loeschung und laedt seine Marke ohne das Feld wieder
        hoch, bevor C zurueckkommt -> C (0.63.2) verliert seine
        Offline-Eintraege (wie in v0.63.1); A behaelt das Eingespielte, B
        (alt, kennt die Loeschung) loescht es bei sich weiterhin."""
        a, b, c = self._offline_drei((CODE, self.alter_code(ALT), CODE))
        datei = ta.datei()
        self.assertTrue(datei["markers"].get("reset_at"))
        self.assertNotIn("aufgehoben", datei)
        c.sync()
        c_direkt = c.namen()
        self.alle_sync([c, a, b], 3)
        stand = {d.name: d.namen() for d in (a, b, c)}
        bericht("FG-81 f4b (NEU, ALT, NEU): C nach erstem Abgleich %s, Ende (Reihenfolge "
                "C, A, B) %s" % (c_direkt, stand))
        self.assertEqual(c_direkt, {})
        for device in (a, b, c):
            self.assertNotIn("c-offline", device.namen(), device.name)
        self.assertEqual(karten(a, "-vorher"), 2)
        self.assertEqual(karten(b, "-vorher"), 0)

    def test_fg81_satz2_satz3_f4c_neues_geraet_nach_abgleich_hinter_neuem(self):
        """FG-81 Satz 3 ("kann das Eingespielte auf deinen anderen Geraeten
        zeitweise wieder fehlen", Endfassung Meldung 35 B.2), gezielt.py f4c
        (NEU, ALT, NEU):
        C (0.63.2) loescht das Eingespielte beim ersten Abgleich direkt nach B
        (v0.63.1) voruebergehend; gleicht C einmal nach A (0.63.2) ab, hat es
        die Aufhebung und behaelt das Eingespielte dauerhaft, obwohl B die
        alte Marke immer wieder hochlaedt. B (alt, kennt die Loeschung)
        loescht es bei sich weiterhin."""
        a, b, c = self._offline_drei((CODE, self.alter_code(ALT), CODE))
        c.sync()
        self.assertEqual(c.namen(), {})                 # voruebergehend
        verlauf = []
        for _ in range(3):
            for device in (a, c, b):
                device.sync()
                verlauf.append((device.name, device.namen()))
                if device is c:
                    self.assertEqual(c.namen(), {"a-vorher": 2}, verlauf)
                if device is b:
                    self.assertEqual(b.namen(), {}, verlauf)
                    self.assertNotIn("aufgehoben", ta.datei())
        bericht("FG-81 f4c (NEU, ALT, NEU): %s" % verlauf)
        self.assertTrue(c("meta")["meta"].get("aufgehoben:reset_at"))
        self.assertEqual(a.namen(), {"a-vorher": 2})

    def test_fg81_satz4_f5_offline_geraet_gleicht_vor_dem_ersetzen_ab(self):
        """FG-81 Satz 4 (Bedingung "erst nach dem Ersetzen wieder abgleicht"),
        gezielt.py f5, alle 0.63.2: C gleicht zwischen As Loeschung und dem
        Ersetzen ab -> Cs Offline-Eintraege sind weg, nur das Eingespielte
        kommt."""
        a, c = self.voll("A"), self.voll("C", tz="UTC")
        a("lerne", 2, "vorher")
        self.alle_sync([a, c], 1)
        a("sicherung_erstellen", self.pfad(a))
        ta.pause()
        c("lerne", 3, "offline")
        ta.pause()
        self.assertTrue(a("reset_all")["ok"])
        a.sync()
        ta.pause()
        c.sync()                                     # vor dem Ersetzen
        self.assertEqual(c.namen(), {})
        a("sicherung_ersetzen", self.pfad(a))
        a.sync()
        self.alle_sync([c, a], 3)
        for device in (a, c):
            self.assertEqual(device.namen(), {"a-vorher": 2}, device.name)
        self.stabil([a, c])

    def test_fg81_satz4_f6_sicherung_kennt_fruehere_loeschung(self):
        """FG-81 Satz 4 ("in der Regel"), gezielt.py f6, alle 0.63.2: Cs
        Offline-Eintraege liegen vor einer frueheren Loeschung, die die
        Sicherung schon kennt -> sie bleiben weg, obwohl C erst nach dem
        Ersetzen abgleicht (Ausnahme, die "in der Regel" traegt)."""
        a, c = self.voll("A"), self.voll("C", tz="UTC")
        a("lerne", 2, "vorher")
        self.alle_sync([a, c], 1)
        ta.pause()
        c("lerne", 3, "offline")
        ta.pause()
        self.assertTrue(a("reset_all")["ok"])
        a.sync()
        ta.pause()
        a("lerne", 2, "danach")
        a.sync()
        a("sicherung_erstellen", self.pfad(a))
        ta.pause()
        self.assertTrue(a("reset_all")["ok"])
        a.sync()
        ta.pause()
        a("sicherung_ersetzen", self.pfad(a))
        a.sync()
        self.alle_sync([c, a], 3)
        for device in (a, c):
            self.assertEqual(device.namen(), {"a-danach": 2}, device.name)
        self.stabil([a, c])

    def test_fg81_satz5_f7_schon_abgeglichenes_bleibt_geloescht(self):
        """FG-81 Satz 5, gezielt.py f7, alle 0.63.2: B lernt nach dem Erstellen
        der Sicherung und gleicht vor der Loeschung ab -> "b-zwischen" bleibt
        auf A und B geloescht; das Eingespielte kommt. Satz 5 ist gestrichen
        (Weisung zu Meldung 38 und 40, Frage 1); der Fall bleibt als Beleg des
        Verhaltens, Gegenstueck: h7, h7h, h9 (bekannte Grenze)."""
        a, b = self.voll("A"), self.voll("B", tz="UTC")
        a("lerne", 2, "vorher")
        self.alle_sync([a, b], 1)
        a("sicherung_erstellen", self.pfad(a))
        ta.pause()
        b("lerne", 2, "zwischen")
        b.sync()
        a.sync()
        self.assertEqual(karten(a, "-zwischen"), 2)
        ta.pause()
        self.assertTrue(a("reset_all")["ok"])
        a.sync()
        b.sync()
        ta.pause()
        a("sicherung_ersetzen", self.pfad(a))
        a.sync()
        self.alle_sync([a, b], 3)
        for device in (a, b):
            self.assertEqual(device.namen(), {"a-vorher": 2}, device.name)
        self.stabil([a, b])

    def test_fg81_satz6_f2c_unbekannte_spaetere_loeschung_gilt(self):
        """FG-81 Satz 6, erster Teil, gezielt.py f2c, alle 0.63.2: B loescht
        NACH As Loeschung, A kennt das nicht und ersetzt -> Bs spaetere
        Loeschung gilt weiter, auch fuer das Eingespielte (A {}, B {})."""
        a, b = self.voll("A"), self.voll("B", tz="UTC")
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        self.alle_sync([a, b, a], 1)
        a("sicherung_erstellen", self.pfad(a))
        ta.pause()
        self.assertTrue(a("reset_all")["ok"])         # ohne Abgleich
        ta.pause()
        b("lerne", 1, "spaet")
        ta.pause()
        self.assertTrue(b("reset_all")["ok"])         # spaeter als As Loeschung
        b.sync()
        ta.pause()
        a("sicherung_ersetzen", self.pfad(a))
        self.assertEqual(karten(a, "-vorher"), 4)
        self.alle_sync([a, b], 3)
        for device in (a, b):
            self.assertEqual(device.namen(), {}, device.name)
        self.stabil([a, b])

    def test_fg81_satz6_f2b_unbekannte_fruehere_loeschung_aufgehoben(self):
        """FG-81 Satz 6, zweiter Teil, gezielt.py f2b, alle 0.63.2: B loescht
        VOR As Loeschung, A kennt das nicht, loescht spaeter selbst und
        ersetzt -> Bs fruehere Loeschung DERSELBEN Art (beide "Alle Lerndaten
        loeschen") ist aufgehoben: A und B haben "a-vorher" und "b-vorher"
        (v0.63.1 haette A {}, B {}). Gegenstueck andere Art: f2e, f2f."""
        a, b = self.voll("A"), self.voll("B", tz="UTC")
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        self.alle_sync([a, b, a], 1)
        a("sicherung_erstellen", self.pfad(a))
        ta.pause()
        b("lerne", 1, "spaet")
        ta.pause()
        self.assertTrue(b("reset_all")["ok"])         # A kennt diese Loeschung nicht
        b.sync()
        ta.pause()
        a("lerne", 1, "zw")
        ta.pause()
        self.assertTrue(a("reset_all")["ok"])         # spaeter, ohne Abgleich
        ta.pause()
        a("sicherung_ersetzen", self.pfad(a))
        self.alle_sync([a, b], 3)
        for device in (a, b):
            self.assertEqual(device.namen(), {"a-vorher": 2, "b-vorher": 2}, device.name)
        self.assertEqual(sorted(ta.datei().get("aufgehoben", {})), ["reset_at"])
        self.stabil([a, b])

    # ------------------------------------------------------------ FG-81 Endfassung
    # Antwort Meldung 35 B.2/B.3: Grenzen der Saetze 2 und 4 (f4f, Vorlage
    # gp_s6b_texte skripte/texte_ablaeufe.py f4f) und von Satz 6 (f2e, f2f
    # "andere Art", ebendort f2e_verlauf, f2f_verlauf). Ohne Uhrverstellung.
    def _f4f(self, code_b):
        """gp_s6b_texte f4f: A, B, C, D gleichen ab, A erstellt eine
        Sicherung, C lernt offline, A loescht alles, A und D gleichen ab (D
        kennt die Loeschung, B und C nicht), A ersetzt und gleicht ab. B (Code
        code_b) lernt etwas und gleicht ab, danach D einmal, danach C einmal,
        dann drei Runden A, D, C, B. Liefert die Zwischenstaende."""
        a = self.voll("A")
        b = self.voll("B", tz="America/New_York", code=code_b)
        c = self.voll("C", tz="UTC")
        d = self.voll("D", tz="Asia/Tokyo")
        a("lerne", 2, "vorher")
        self.alle_sync([a, b, c, d, a], 1)
        a("sicherung_erstellen", self.pfad(a))
        ta.pause()
        c("lerne", 3, "offline")
        ta.pause()
        self.assertTrue(a("reset_all")["ok"])
        a.sync()
        d.sync()
        self.assertEqual(d.namen(), {})                  # D kennt die Loeschung
        ta.pause()
        a("sicherung_ersetzen", self.pfad(a))
        a.sync()
        ta.pause()
        b("lerne", 1, "neu")
        ta.pause()
        b.sync()                                         # nach dem Ersetzen
        stand = {"datei_nach_B": ta.datei()}
        ta.pause()
        d.sync()
        stand["D_erster_abgleich"] = d.namen()
        stand["datei_nach_D"] = ta.datei()
        ta.pause()
        c.sync()
        stand["C_erster_abgleich"] = c.namen()
        stand["A_verlauf"] = []
        for _ in range(3):
            for device in (a, d, c, b):
                device.sync()
                if device is a:
                    stand["A_verlauf"].append(a.namen())
        stand["ende"] = {x.name: x.namen() for x in (a, b, c, d)}
        stand["geraete"] = (a, b, c, d)
        return stand

    def test_fg81_satz2_satz4_f4f_grenze_altes_geraet_ohne_kenntnis_laedt_nach_dem_ersetzen_hoch(self):
        """FG-81 Saetze 2 und 4, Grenze (gp_s6b_texte M1/M2, f4f mit NEU, ALT,
        NEU, NEU): B hatte beim Ersetzen noch v0.63.1, kennt die Loeschung
        NICHT, laedt aber nach dem Ersetzen hoch und laesst dabei das Feld
        "aufgehoben" weg. Danach traegt D (0.63.2, kennt die Loeschung) seine
        Marke neu ein: D verliert das Eingespielte zeitweise (Satz 2 gilt nur,
        wenn alle schon beim Ersetzen 0.63.2 hatten; Satz 3 "zeitweise wieder
        fehlen"), Cs Offline-Eintraege sind dauerhaft auf allen Geraeten weg
        (Satz 4 nur mit derselben Bedingung). A behaelt das Eingespielte
        immer, am Ende ist es ueberall zurueck."""
        stand = self._f4f(self.alter_code(ALT))
        bericht("FG-81 f4f (NEU, ALT, NEU, NEU): D %s, C %s, Ende %s"
                % (stand["D_erster_abgleich"], stand["C_erster_abgleich"], stand["ende"]))
        self.assertNotIn("aufgehoben", stand["datei_nach_B"])
        self.assertFalse(stand["datei_nach_B"]["markers"].get("reset_at"))
        self.assertEqual(stand["D_erster_abgleich"], {"b-neu": 1})
        self.assertTrue(stand["datei_nach_D"]["markers"].get("reset_at"))
        self.assertNotIn("aufgehoben", stand["datei_nach_D"])
        self.assertEqual(stand["C_erster_abgleich"], {"b-neu": 1})
        for namen in stand["A_verlauf"]:
            self.assertEqual(namen, {"a-vorher": 2, "b-neu": 1})
        for name, namen in stand["ende"].items():
            self.assertEqual(namen, {"a-vorher": 2, "b-neu": 1}, name)

    def test_fg81_satz2_satz4_f4f_guenstiger_fall_alle_schon_beim_ersetzen_0632(self):
        """FG-81 Saetze 2 und 4, guenstiger Fall zu f4f (NEU, NEU, NEU, NEU):
        derselbe Ablauf, aber alle Geraete hatten schon beim Ersetzen 0.63.2.
        Bs Hochladung behaelt das Feld, D loescht das Eingespielte nicht noch
        einmal, Cs Offline-Eintraege bleiben auf allen Geraeten erhalten."""
        stand = self._f4f(CODE)
        bericht("FG-81 f4f (NEU, NEU, NEU, NEU): D %s, C %s, Ende %s"
                % (stand["D_erster_abgleich"], stand["C_erster_abgleich"], stand["ende"]))
        self.assertEqual(sorted(stand["datei_nach_B"].get("aufgehoben", {})), ["reset_at"])
        self.assertFalse(stand["datei_nach_D"]["markers"].get("reset_at"))
        self.assertEqual(stand["D_erster_abgleich"], {"a-vorher": 2, "b-neu": 1})
        self.assertEqual(stand["C_erster_abgleich"], {"a-vorher": 2, "b-neu": 1, "c-offline": 3})
        for name, namen in stand["ende"].items():
            self.assertEqual(namen, {"a-vorher": 2, "b-neu": 1, "c-offline": 3}, name)
        self.stabil(list(stand["geraete"]))

    def test_fg81_satz6_f2e_grenze_fruehere_loeschung_andere_art_verlauf_bleibt_weg(self):
        """FG-81 Satz 6, Grenze "derselben Art" (gp_s6b_texte M3, f2e), alle
        0.63.2: B loescht frueher nur den Verlauf ("Verlauf loeschen"), A kennt
        das nicht, loescht spaeter "Alle Lerndaten" und ersetzt -> direkt nach
        dem Ersetzen hat A den Verlauf beider Geraete, nach dem Abgleich ist
        er auf A und B weg (Bs fruehere Loeschung anderer Art wird NICHT
        aufgehoben); die Karten aus der Sicherung bleiben. Gegenstueck
        gleiche Art: f2b."""
        a, b = self.voll("A"), self.voll("B", tz="UTC")
        a("lerne", 2, "vorher")
        a("fuelle", "vl")
        b("fuelle", "vl")
        self.alle_sync([a, b, a], 1)
        a("sicherung_erstellen", self.pfad(a))
        ta.pause()
        self.assertTrue(b("clear_history")["ok"])     # A kennt diese Loeschung nicht
        b.sync()
        ta.pause()
        self.assertTrue(a("reset_all")["ok"])         # spaeter, andere Art, ohne Abgleich
        ta.pause()
        a("sicherung_ersetzen", self.pfad(a))
        self.assertEqual(verlauf(a), {"a-vl": 1, "b-vl": 1})
        self.alle_sync([a, b], 3)
        bericht("FG-81 f2e: Verlauf A %s, B %s; Karten A %s; Feld %s"
                % (verlauf(a), verlauf(b), a.namen(), ta.datei().get("aufgehoben")))
        for device in (a, b):
            self.assertEqual(verlauf(device), {}, device.name)
            self.assertEqual(device.namen(), {"a-vorher": 2, "a-vl": 1, "b-vl": 1}, device.name)
        self.assertTrue(ta.datei()["markers"].get("history_cleared_at"))
        self.assertNotIn("history_cleared_at", ta.datei().get("aufgehoben") or {})
        self.stabil([a, b])

    def test_fg81_satz6_f2f_grenze_fruehere_loeschung_andere_art_lerndaten_bleiben_weg(self):
        """FG-81 Satz 6, Grenze "derselben Art" (gp_s6b_texte M3, f2f), alle
        0.63.2, umgekehrt zu f2e: B loescht frueher "Alle Lerndaten", A kennt
        das nicht, loescht spaeter nur den Verlauf und ersetzt -> direkt nach
        dem Ersetzen hat A die Karten beider Geraete, nach dem Abgleich sind
        sie auf A und B weg (nicht aufgehoben). Gegenstueck gleiche Art:
        f2b."""
        a, b = self.voll("A"), self.voll("B", tz="UTC")
        a("lerne", 2, "vorher")
        a("fuelle", "vl")
        b("lerne", 2, "vorher")
        self.alle_sync([a, b, a], 1)
        a("sicherung_erstellen", self.pfad(a))
        ta.pause()
        self.assertTrue(b("reset_all")["ok"])         # A kennt diese Loeschung nicht
        b.sync()
        ta.pause()
        self.assertTrue(a("clear_history")["ok"])     # spaeter, andere Art, ohne Abgleich
        ta.pause()
        a("sicherung_ersetzen", self.pfad(a))
        self.assertEqual(a.namen(), {"a-vorher": 2, "a-vl": 1, "b-vorher": 2})
        self.assertEqual(verlauf(a), {"a-vl": 1})
        self.alle_sync([a, b], 3)
        bericht("FG-81 f2f: Karten A %s, B %s; Verlauf A %s; Feld %s"
                % (a.namen(), b.namen(), verlauf(a), ta.datei().get("aufgehoben")))
        for device in (a, b):
            self.assertEqual(device.namen(), {}, device.name)
            self.assertEqual(verlauf(device), {}, device.name)
        self.assertTrue(ta.datei()["markers"].get("reset_at"))
        self.assertNotIn("reset_at", ta.datei().get("aufgehoben") or {})
        self.stabil([a, b])

    # ------------------------------------------------------------ FG-81 Weisung zu Meldung 37
    # Satz 6 neu ("Loeschungen eines anderen Geraets, die dieses Geraet noch
    # nicht kennt, gelten weiter - ausser sie kamen vor der letzten Loeschung
    # derselben Art, die dieses Geraet kennt ...; solche werden aufgehoben.")
    # und Satz 7 neu ("Bei Spielstaenden und Projekten ist das anders: ...
    # bleiben geloescht, wenn die Loeschung von einem anderen Geraet kam oder
    # schon abgeglichen war."). Einer je Ablauf; Vorlagen: s6b/texte_endfassung
    # skripte/zusatz_ablaeufe.py f2g, gp_meldung_37 skripte/ablaeufe_m37.py
    # S1-S5, S1b, S2b; neuer Fall: s6b/texte_m37 skripte/neuer_fall.py.
    # Ohne Uhrverstellung. Satz 6 ausserdem: f2b, f2c, f2e, f2f (oben).
    def _f2g(self, variante):
        """f2g: A kennt eine spaetere Loeschung "Alle Lerndaten" von C (t2),
        nicht die von B (t1); As eigene letzte Loeschung ist "Historie
        loeschen" (tA). vor: t1 < t2 < tA; nach: tA < t1 < t2; ohne_c: tA <
        t1, ohne C (A kennt keine Loeschung dieser Art). Liefert Marken und
        Endstaende (Karten, Verlauf) von A, B, C."""
        a = self.voll("A")
        b = self.voll("B", tz="UTC")
        c = self.voll("C", tz="Asia/Tokyo")
        a("lerne", 2, "vorher")
        a("fuelle", "vl")
        b("lerne", 2, "vorher")
        b("fuelle", "vl")
        c("lerne", 2, "vorher")
        self.alle_sync([a, b, c], 2)
        a("sicherung_erstellen", self.pfad(a))
        ta.pause()
        if variante in ("nach", "ohne_c"):
            self.assertTrue(a("clear_history")["ok"])    # tA, ohne Abgleich
            ta.pause()
        b("lerne", 1, "zw")
        ta.pause()
        self.assertTrue(b("reset_all")["ok"])            # t1, A kennt das nicht
        b.sync()
        ta.pause()
        stand = {"t1": b.marke(), "t2": None}
        if variante != "ohne_c":
            c.sync()
            ta.pause()
            c("lerne", 1, "zw")
            ta.pause()
            self.assertTrue(c("reset_all")["ok"])        # t2, spaeter
            c.sync()
            ta.pause()
            stand["t2"] = c.marke()
            a.sync()                                     # A kennt t2 (nicht t1)
            ta.pause()
        if variante == "vor":
            self.assertTrue(a("clear_history")["ok"])    # tA nach t2
            ta.pause()
        stand["reset_at_A"] = a.marke()
        stand["tA"] = a.marke("history_cleared_at")
        a("sicherung_ersetzen", self.pfad(a))
        stand["A_direkt"] = a.namen()
        self.alle_sync([a, b, c], 3)
        stand["karten"] = {d.name: d.namen() for d in (a, b, c)}
        stand["verlauf"] = {d.name: verlauf(d) for d in (a, b, c)}
        stand["aufgehoben_A"] = {k: v for k, v in a("meta")["meta"].items()
                                 if k.startswith("aufgehoben:")}
        stand["geraete"] = (a, b, c)
        return stand

    _F2G_ALLES = {"a-vorher": 2, "a-vl": 1, "b-vorher": 2, "b-vl": 1, "c-vorher": 2}

    def _vor(self, frueher, spaeter):
        # Zeitpunkt in UTC (Marken der Geraete in verschiedenen Zeitzonen)
        self.assertLess(fisi_sync.parse_marker(frueher)[1], fisi_sync.parse_marker(spaeter)[1],
                        (frueher, spaeter))

    def test_fg81_satz6_f2g_vor_bekannte_spaetere_gleicher_art_hebt_frueher_auf(self):
        """FG-81 Satz 6 (Weisung zu Meldung 37), f2g "vor", alle 0.63.2:
        t1 (B, unbekannt) < t2 (C, bekannt) < tA (A "Historie loeschen"). t1
        kam vor der letzten Loeschung derselben Art, die A kennt (t2) -> wird
        aufgehoben: Karten und Verlauf aus der Sicherung bleiben auf A, B, C."""
        stand = self._f2g("vor")
        bericht("FG-81 f2g vor: %s" % {k: v for k, v in stand.items() if k != "geraete"})
        self._vor(stand["t1"], stand["t2"])
        self._vor(stand["t2"], stand["tA"])
        self.assertEqual(stand["reset_at_A"], stand["t2"])
        self.assertEqual(stand["A_direkt"], self._F2G_ALLES)
        for name in "ABC":
            self.assertEqual(stand["karten"][name], self._F2G_ALLES, name)
            self.assertEqual(stand["verlauf"][name], {"a-vl": 1, "b-vl": 1}, name)
        self.assertIn("aufgehoben:reset_at", stand["aufgehoben_A"])
        self.stabil(list(stand["geraete"]))

    def test_fg81_satz6_f2g_nach_unbekannte_nach_eigener_loeschung_aufgehoben(self):
        """FG-81 Satz 6 (Weisung zu Meldung 37), f2g "nach", alle 0.63.2:
        tA (A "Historie loeschen") < t1 (B, unbekannt) < t2 (C, bekannt). t1
        kam nach As eigener Loeschung, aber vor der letzten Loeschung
        derselben Art, die A kennt (t2) -> wird aufgehoben (die Fassung von
        dd0c2a0 sagte hier "gelten weiter")."""
        stand = self._f2g("nach")
        bericht("FG-81 f2g nach: %s" % {k: v for k, v in stand.items() if k != "geraete"})
        self._vor(stand["tA"], stand["t1"])
        self._vor(stand["t1"], stand["t2"])
        self.assertEqual(stand["reset_at_A"], stand["t2"])
        self.assertEqual(stand["A_direkt"], self._F2G_ALLES)
        for name in "ABC":
            self.assertEqual(stand["karten"][name], self._F2G_ALLES, name)
            self.assertEqual(stand["verlauf"][name], {"a-vl": 1, "b-vl": 1}, name)
        self.assertIn("aufgehoben:reset_at", stand["aufgehoben_A"])
        self.stabil(list(stand["geraete"]))

    def test_fg81_satz6_f2g_ohne_c_keine_bekannte_gleicher_art_gilt_weiter(self):
        """FG-81 Satz 6 (Weisung zu Meldung 37), f2g "ohne C", alle 0.63.2:
        tA (A "Historie loeschen") < t1 (B "Alle Lerndaten", unbekannt); A
        kennt keine Loeschung dieser Art -> t1 gilt weiter: Karten und Verlauf
        sind auf A, B, C weg, "reset_at" wird nicht aufgehoben."""
        stand = self._f2g("ohne_c")
        bericht("FG-81 f2g ohne C: %s" % {k: v for k, v in stand.items() if k != "geraete"})
        self._vor(stand["tA"], stand["t1"])
        self.assertFalse(stand["reset_at_A"])
        self.assertEqual(stand["A_direkt"], self._F2G_ALLES)
        for name in "ABC":
            self.assertEqual(stand["karten"][name], {}, name)
            self.assertEqual(stand["verlauf"][name], {}, name)
        self.assertNotIn("aufgehoben:reset_at", stand["aufgehoben_A"])
        self.assertEqual(ta.datei()["markers"].get("reset_at"), stand["t1"])
        self.stabil(list(stand["geraete"]))

    def test_fg81_satz6_s3_bestenliste_unbekannte_fruehere_aufgehoben(self):
        """FG-81 Satz 6 (beide "Bestenliste loeschen"), gp_meldung_37 S3,
        alle 0.63.2: B loescht die Bestenliste (t1, A kennt es nicht), A
        loescht sie spaeter selbst (tA) und ersetzt -> t1 wird aufgehoben, der
        Eintrag aus der Sicherung bleibt auf A und B."""
        a, b = self.voll("A"), self.voll("B", tz="UTC")
        a("bestenliste", "vorher")
        self.alle_sync([a, b, a], 1)
        a("sicherung_erstellen", self.pfad(a))
        ta.pause()
        self.assertTrue(b("reset_records")["ok"])        # t1, A kennt das nicht
        b.sync()
        ta.pause()
        self.assertTrue(a("reset_records")["ok"])        # tA, spaeter, ohne Abgleich
        ta.pause()
        t1, ta_ = b.marke("bestenliste_reset_at"), a.marke("bestenliste_reset_at")
        self._vor(t1, ta_)
        a("sicherung_ersetzen", self.pfad(a))
        self.assertEqual(a("bestenzahl")["besten"], ["a-vorher"])
        self.alle_sync([a, b], 3)
        bericht("FG-81 S3 Bestenliste: A %s, B %s, Feld %s"
                % (a("bestenzahl")["besten"], b("bestenzahl")["besten"],
                   ta.datei().get("aufgehoben")))
        for device in (a, b):
            self.assertEqual(device("bestenzahl")["besten"], ["a-vorher"], device.name)
        self.assertIn("bestenliste_reset_at", ta.datei().get("aufgehoben") or {})
        self.stabil([a, b])

    def test_fg81_satz6_s4_mehrere_fremde_spaetere_gilt_weiter(self):
        """FG-81 Satz 6, mehrere fremde Loeschungen, gp_meldung_37 S4, alle
        0.63.2: B "Alle Lerndaten" (t1) < A selbst (tA) < C (t3); A kennt weder
        t1 noch t3. t1 kam vor As Loeschung derselben Art (aufgehoben), t3
        danach und unbekannt -> gilt weiter: alles von vor t3 ist auf A, B, C
        weg, Cs Eintrag danach bleibt."""
        a, b, c = self.voll("A"), self.voll("B", tz="UTC"), self.voll("C", tz="Asia/Tokyo")
        a("lerne", 2, "vorher")
        self.alle_sync([a, b, c, a], 1)
        a("sicherung_erstellen", self.pfad(a))
        ta.pause()
        b("lerne", 1, "zw")
        self.assertTrue(b("reset_all")["ok"])            # t1
        b.sync()
        ta.pause()
        self.assertTrue(a("reset_all")["ok"])            # tA, ohne Abgleich
        ta.pause()
        c.sync()
        c("lerne", 1, "zw")
        ta.pause()
        self.assertTrue(c("reset_all")["ok"])            # t3
        c.sync()
        ta.pause()
        c("lerne", 1, "nach")
        c.sync()
        ta.pause()
        t3 = c.marke()
        self._vor(a.marke(), t3)
        a("sicherung_ersetzen", self.pfad(a))
        self.assertEqual(a.namen(), {"a-vorher": 2})
        self.alle_sync([a, b, c], 3)
        bericht("FG-81 S4: %s, Datei %s" % ({d.name: d.namen() for d in (a, b, c)},
                                            ta.datei().get("markers")))
        for device in (a, b, c):
            self.assertEqual(device.namen(), {"c-nach": 1}, device.name)
        self.assertEqual(ta.datei()["markers"].get("reset_at"), t3)
        self.stabil([a, b, c])

    def test_fg81_satz6_s5_mehrere_fremde_beide_frueher_aufgehoben(self):
        """FG-81 Satz 6, mehrere fremde Loeschungen, gp_meldung_37 S5, alle
        0.63.2: B (t1) < C (t2) < A selbst (tA), alle "Alle Lerndaten"; A
        kennt weder t1 noch t2 -> beide aufgehoben, das Eingespielte bleibt
        auf A, B, C."""
        a, b, c = self.voll("A"), self.voll("B", tz="UTC"), self.voll("C", tz="Asia/Tokyo")
        a("lerne", 2, "vorher")
        self.alle_sync([a, b, c, a], 1)
        a("sicherung_erstellen", self.pfad(a))
        ta.pause()
        self.assertTrue(b("reset_all")["ok"])            # t1
        b.sync()
        ta.pause()
        c.sync()
        self.assertTrue(c("reset_all")["ok"])            # t2
        c.sync()
        ta.pause()
        self.assertTrue(a("reset_all")["ok"])            # tA, ohne Abgleich
        ta.pause()
        self._vor(c.marke(), a.marke())
        a("sicherung_ersetzen", self.pfad(a))
        self.alle_sync([a, b, c], 3)
        for device in (a, b, c):
            self.assertEqual(device.namen(), {"a-vorher": 2}, device.name)
        self.assertEqual(sorted(ta.datei().get("aufgehoben", {})), ["reset_at"])
        self.stabil([a, b, c])

    def _spiel_projekt_start(self):
        """A mit Spielstaenden lx, ly (je 3 Ereignisse), Projekten p1, p2 und
        2 Karten; A und B gleichen ab; A erstellt eine Sicherung."""
        a, b = self.voll("A"), self.voll("B", tz="UTC")
        a("spiel_anlegen", 1, "lx", 3)
        a("spiel_anlegen", 2, "ly", 3)
        a("projekt_anlegen", "p1")
        a("projekt_anlegen", "p2")
        a("lerne", 2, "vorher")
        self.alle_sync([a, b, a], 1)
        self.assertEqual(b("spielzahl")["spiel"], {"lx": 3, "ly": 3})
        self.assertEqual(b("projekte")["projekte"], ["p1", "p2"])
        a("sicherung_erstellen", self.pfad(a))
        ta.pause()
        return a, b

    def _ende(self, a, b):
        return {d.name: {"spiel": d("spielzahl")["spiel"], "projekte": d("projekte")["projekte"],
                         "karten": d.namen()} for d in (a, b)}

    def test_fg81_satz7_s1_spielstand_anderes_geraet_bleibt_geloescht(self):
        """FG-81 Satz 7 (Weisung zu Meldung 37), gp_meldung_37 S1, alle
        0.63.2: B setzt Spielstand lx zurueck (delete_run, wie "Spielstand
        zuruecksetzen") und gleicht ab, A kennt das nicht; A loescht danach
        ly selbst (ohne Abgleich) und ersetzt -> lx bleibt auf A und B
        geloescht (keine Aufhebung, anders als Satz 6), ly kommt zurueck
        (eigene, nicht abgeglichene Loeschung)."""
        a, b = self._spiel_projekt_start()
        self.assertTrue(b("spiel_loeschen", 1, "lx")["ok"])
        b.sync()
        ta.pause()
        self.assertTrue(a("spiel_loeschen", 2, "ly")["ok"])
        ta.pause()
        self.assertEqual(a("spielzahl")["spiel"], {"lx": 3})
        a("sicherung_ersetzen", self.pfad(a))
        self.assertEqual(a("spielzahl")["spiel"], {"lx": 3, "ly": 3})
        self.alle_sync([a, b], 3)
        ende = self._ende(a, b)
        bericht("FG-81 S1 Spielstand: %s" % ende)
        for name in "AB":
            self.assertEqual(ende[name]["spiel"], {"ly": 3}, name)
            self.assertEqual(ende[name]["karten"], {"a-vorher": 2}, name)
        self.stabil([a, b])

    def test_fg81_satz7_s2_projekt_anderes_geraet_bleibt_geloescht(self):
        """FG-81 Satz 7 (Weisung zu Meldung 37), gp_meldung_37 S2, alle
        0.63.2: B loescht Projekt p1 und gleicht ab, A kennt das nicht; A
        loescht danach p2 selbst (ohne Abgleich) und ersetzt -> p1 bleibt auf
        A und B geloescht, p2 kommt zurueck."""
        a, b = self._spiel_projekt_start()
        b("projekt_loeschen", "p1")
        b.sync()
        ta.pause()
        a("projekt_loeschen", "p2")
        ta.pause()
        self.assertEqual(a("projekte")["projekte"], ["p1"])
        a("sicherung_ersetzen", self.pfad(a))
        self.assertEqual(a("projekte")["projekte"], ["p1", "p2"])
        self.alle_sync([a, b], 3)
        ende = self._ende(a, b)
        bericht("FG-81 S2 Projekt: %s" % ende)
        for name in "AB":
            self.assertEqual(ende[name]["projekte"], ["p2"], name)
        self.stabil([a, b])

    def test_fg81_satz7_s1b_spielstand_schon_abgeglichen_bleibt_geloescht(self):
        """FG-81 Satz 7 (grenzt Satz 2 ein), gp_meldung_37 S1b, alle 0.63.2:
        A setzt Spielstand ly zurueck und gleicht ab (bekannte, abgeglichene
        Loeschung); A ersetzt -> direkt danach ist ly da, nach dem Abgleich
        auf A und B wieder weg (bleibt geloescht); die Karten bleiben."""
        a, b = self._spiel_projekt_start()
        self.assertTrue(a("spiel_loeschen", 2, "ly")["ok"])
        a.sync()
        ta.pause()
        a("sicherung_ersetzen", self.pfad(a))
        self.assertEqual(a("spielzahl")["spiel"], {"lx": 3, "ly": 3})
        self.alle_sync([a, b], 3)
        ende = self._ende(a, b)
        bericht("FG-81 S1b Spielstand: %s" % ende)
        for name in "AB":
            self.assertEqual(ende[name]["spiel"], {"lx": 3}, name)
            self.assertEqual(ende[name]["karten"], {"a-vorher": 2}, name)
        self.stabil([a, b])

    def test_fg81_satz7_s2b_projekt_schon_abgeglichen_bleibt_geloescht(self):
        """FG-81 Satz 7 (grenzt Satz 2 ein), gp_meldung_37 S2b, alle 0.63.2:
        A loescht Projekt p2 und gleicht ab; A ersetzt -> direkt danach ist
        p2 da, nach dem Abgleich auf A und B wieder weg."""
        a, b = self._spiel_projekt_start()
        a("projekt_loeschen", "p2")
        a.sync()
        ta.pause()
        a("sicherung_ersetzen", self.pfad(a))
        self.assertEqual(a("projekte")["projekte"], ["p1", "p2"])
        self.alle_sync([a, b], 3)
        ende = self._ende(a, b)
        bericht("FG-81 S2b Projekt: %s" % ende)
        for name in "AB":
            self.assertEqual(ende[name]["projekte"], ["p1"], name)
        self.stabil([a, b])

    def test_fg81_satz7_neu_spielstand_anderes_geraet_offline_gleicht_nach_dem_ersetzen_ab(self):
        """FG-81 Satz 7, Pflicht-Beleg Weisung zu Meldung 37 Abschnitt 2, alle
        0.63.2: B setzt Spielstand lx OHNE Verbindung zurueck; A ersetzt und
        gleicht ab (lx noch da); B gleicht erst danach ab -> lx bleibt auf A
        und B geloescht."""
        a, b = self._spiel_projekt_start()
        self.assertTrue(b("spiel_loeschen", 1, "lx")["ok"])     # ohne Verbindung
        ta.pause()
        a("sicherung_ersetzen", self.pfad(a))
        a.sync()
        self.assertEqual(a("spielzahl")["spiel"], {"lx": 3, "ly": 3})
        ta.pause()
        b.sync()                                                # erst nach dem Ersetzen
        self.assertEqual(b("spielzahl")["spiel"], {"ly": 3})
        self.alle_sync([a, b], 3)
        ende = self._ende(a, b)
        bericht("FG-81 neuer Fall Spielstand: %s" % ende)
        for name in "AB":
            self.assertEqual(ende[name]["spiel"], {"ly": 3}, name)
            self.assertEqual(ende[name]["projekte"], ["p1", "p2"], name)
            self.assertEqual(ende[name]["karten"], {"a-vorher": 2}, name)
        self.stabil([a, b])

    def test_fg81_satz7_neu_projekt_anderes_geraet_offline_gleicht_nach_dem_ersetzen_ab(self):
        """FG-81 Satz 7, Pflicht-Beleg Weisung zu Meldung 37 Abschnitt 2, alle
        0.63.2: B loescht Projekt p1 OHNE Verbindung; A ersetzt und gleicht ab
        (p1 noch da); B gleicht erst danach ab -> p1 bleibt auf A und B
        geloescht."""
        a, b = self._spiel_projekt_start()
        b("projekt_loeschen", "p1")                             # ohne Verbindung
        ta.pause()
        a("sicherung_ersetzen", self.pfad(a))
        a.sync()
        self.assertEqual(a("projekte")["projekte"], ["p1", "p2"])
        ta.pause()
        b.sync()                                                # erst nach dem Ersetzen
        self.assertEqual(b("projekte")["projekte"], ["p2"])
        self.alle_sync([a, b], 3)
        ende = self._ende(a, b)
        bericht("FG-81 neuer Fall Projekt: %s" % ende)
        for name in "AB":
            self.assertEqual(ende[name]["projekte"], ["p2"], name)
            self.assertEqual(ende[name]["spiel"], {"lx": 3, "ly": 3}, name)
            self.assertEqual(ende[name]["karten"], {"a-vorher": 2}, name)
        self.stabil([a, b])

    # ------------------------------------------------------------------
    # Weisung zu Meldung 38 und 40, Abschnitt 2 Frage 1 (Ablaeufe aus
    # gp3_fg81_m37: h1, h7, h7h, h9). Satznummern wie in gp3 (Fassung
    # d54397f); nach dem Streichen von Satz 5 ist "Satz 6" der fuenfte Satz.

    def test_fg81_satz6_h1_beide_historie_loeschen_frueher_unbekannt_aufgehoben(self):
        """FG-81 Satz 6 (beide "Historie loeschen"), gp3 h1, alle 0.63.2: B
        "Historie loeschen" t1 und Abgleich (A kennt es nicht), danach A
        "Historie loeschen" tA ohne Abgleich; A ersetzt -> t1 kam vor der
        letzten Loeschung derselben Art, die A kennt, und wird aufgehoben: der
        Verlauf aus der Sicherung bleibt auf A und B."""
        a, b = self.voll("A"), self.voll("B", tz="UTC")
        a("fuelle", "vorher")
        b("fuelle", "vorher")
        self.alle_sync([a, b, a], 1)
        a("sicherung_erstellen", self.pfad(a))
        ta.pause()
        self.assertTrue(b("clear_history")["ok"])     # t1, A kennt es nicht
        b.sync()
        ta.pause()
        self.assertTrue(a("clear_history")["ok"])     # tA, ohne Abgleich
        ta.pause()
        a("sicherung_ersetzen", self.pfad(a))
        self.alle_sync([a, b], 3)
        aufgehoben = ta.datei().get("aufgehoben") or {}
        bericht("FG-81 h1: aufgehoben=%s" % aufgehoben)
        self.assertIn("history_cleared_at", aufgehoben)
        for device in (a, b):
            self.assertEqual(verlauf(device), {"a-vorher": 1, "b-vorher": 1}, device.name)
            self.assertEqual(zeilen(os.path.join(device.home, "lern.db"),
                                    "SELECT COUNT(*) FROM test_results")[0][0], 2, device.name)
            self.assertEqual(device.namen(), {"a-vorher": 1, "b-vorher": 1}, device.name)
        self.stabil([a, b])

    def _h7_zwischen(self):
        """gp3 _zwischen: A lernt und fuellt "vorher", Abgleich, A erstellt die
        Sicherung; B lernt und fuellt "zwischen" (nach dem Erstellen), B und A
        gleichen ab (A hat "b-zwischen")."""
        a, b = self.voll("A"), self.voll("B", tz="UTC")
        a("lerne", 2, "vorher")
        a("fuelle", "vorher")
        self.alle_sync([a, b, a], 1)
        a("sicherung_erstellen", self.pfad(a))
        ta.pause()
        b("lerne", 2, "zwischen")
        b("fuelle", "zwischen")
        b.sync()
        a.sync()
        self.assertEqual(karten(a, "-zwischen"), 3)
        ta.pause()
        return a, b

    def _h7_ende(self, geraete):
        return {d.name: {"karten": d.namen(), "verlauf": verlauf(d),
                         "besten": d("bestenzahl")["besten"]} for d in geraete}

    # Soll "bekannte Grenze, kein Versprechen": Gelerntes nach dem Erstellen
    # der Sicherung kommt auf allen Geraeten zurueck, nichts geht verloren.
    _H7_KOMMT_ZURUECK = {"karten": {"a-vorher": 3, "b-zwischen": 3},
                         "verlauf": {"a-vorher": 1, "b-zwischen": 1},
                         "besten": ["a-vorher", "b-zwischen"]}

    def test_fg81_bekannte_grenze_kein_versprechen_h7_geraet_offline_bei_loeschung(self):
        """Bekannte Grenze, kein Versprechen (Weisung zu Meldung 38 und 40,
        Frage 1; gp3 h7, alle 0.63.2): B lernt nach dem Erstellen der
        Sicherung und gleicht ab, ist dann ohne Verbindung. A "Alle Lerndaten
        loeschen", Abgleich, "Alles ersetzen", Abgleich; B gleicht erst danach
        ab -> "b-zwischen" taucht auf A und B wieder auf (nichts geht
        verloren). Haelt das heutige Verhalten fest; der Warntext verspricht
        dazu nichts (der fruehere Satz 5 ist gestrichen)."""
        a, b = self._h7_zwischen()
        self.assertTrue(a("reset_all")["ok"])
        a.sync()
        ta.pause()
        a("sicherung_ersetzen", self.pfad(a))
        a.sync()
        self.assertEqual(a.namen(), {"a-vorher": 3})    # vor Bs Abgleich
        b.sync()
        self.assertEqual(b.namen(), {"a-vorher": 3, "b-zwischen": 3})
        self.alle_sync([a, b], 3)
        ende = self._h7_ende([a, b])
        bericht("FG-81 bekannte Grenze h7: %s" % ende)
        for name in "AB":
            self.assertEqual(ende[name], self._H7_KOMMT_ZURUECK, name)
        self.stabil([a, b])

    def test_fg81_bekannte_grenze_kein_versprechen_h7h_historie_geraet_offline(self):
        """Bekannte Grenze, kein Versprechen (gp3 h7h, alle 0.63.2): wie h7,
        aber A "Historie loeschen" -> der Verlauf "b-zwischen" taucht auf A
        und B wieder auf, nichts geht verloren. Haelt das heutige Verhalten
        fest."""
        a, b = self._h7_zwischen()
        self.assertTrue(a("clear_history")["ok"])
        a.sync()
        ta.pause()
        a("sicherung_ersetzen", self.pfad(a))
        a.sync()
        self.assertEqual(verlauf(a), {"a-vorher": 1})   # vor Bs Abgleich
        b.sync()
        self.alle_sync([a, b], 3)
        ende = self._h7_ende([a, b])
        bericht("FG-81 bekannte Grenze h7h: %s" % ende)
        for name in "AB":
            self.assertEqual(ende[name], self._H7_KOMMT_ZURUECK, name)
        self.stabil([a, b])

    def test_fg81_bekannte_grenze_kein_versprechen_h9_drittes_geraet(self):
        """Bekannte Grenze, kein Versprechen (gp3 h9, alle 0.63.2): wie h7,
        aber B gleicht nach der Loeschung ab (B leer); C hatte "b-zwischen"
        vor der Loeschung abgeglichen und ist dann ohne Verbindung. A ersetzt,
        A und B gleichen ab, C erst danach -> "b-zwischen" taucht auf A, B
        und C wieder auf, nichts geht verloren. Haelt das heutige Verhalten
        fest."""
        a, b = self._h7_zwischen()
        c = self.voll("C", tz="Asia/Tokyo")
        c.sync()
        self.assertEqual(karten(c, "-zwischen"), 3)
        self.assertTrue(a("reset_all")["ok"])
        a.sync()
        b.sync()
        self.assertEqual(karten(b, "-zwischen"), 0)
        ta.pause()
        a("sicherung_ersetzen", self.pfad(a))
        a.sync()
        b.sync()
        for device in (a, b):                           # vor Cs Abgleich
            self.assertEqual(device.namen(), {"a-vorher": 3}, device.name)
        c.sync()
        self.alle_sync([a, b, c], 3)
        ende = self._h7_ende([a, b, c])
        bericht("FG-81 bekannte Grenze h9: %s" % ende)
        for name in "ABC":
            self.assertEqual(ende[name], self._H7_KOMMT_ZURUECK, name)
        self.stabil([a, b, c])

    def _f9_bis_zum_ersetzen(self):
        """gezielt.py f9 bis nach dem Ersetzen: A, B lernen und gleichen ab,
        A erstellt Sicherung S, B loescht selbst und gleicht ab, A gleicht ab
        (kennt die Loeschung) und erstellt Sicherung Q (vor dem Ersetzen),
        dann ersetzt A mit S."""
        a, b = self.voll("A"), self.voll("B", tz="UTC")
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        self.alle_sync([a, b, a], 1)
        a("sicherung_erstellen", self.pfad(a))
        ta.pause()
        self.assertTrue(b("reset_all")["ok"])
        b.sync()
        a.sync()
        self.assertEqual(a.namen(), {})
        a("sicherung_erstellen", self.pfad(a, "q.fisisicherung"))
        ta.pause()
        a("sicherung_ersetzen", self.pfad(a))
        self.assertEqual(a.namen(), {"a-vorher": 2, "b-vorher": 2})
        return a, b

    def test_fg92_f9_sicherung_nach_dem_ersetzen_bringt_stand_zurueck(self):
        """FG-92 PREVIEW_HINT ("ausser die Sicherung wurde auf einem Geraet
        erstellt, nachdem es nach dieser Loeschung mit "Alles ersetzen" einen
        aelteren Stand eingespielt hatte; dann kommt dieser Stand zurueck"),
        gezielt.py f9: A erstellt NACH dem Ersetzen die Sicherung P, B fuehrt
        P ohne Abgleich zusammen -> Bs eigene Loeschung ist aufgehoben."""
        a, b = self._f9_bis_zum_ersetzen()
        ta.pause()
        a("sicherung_erstellen", self.pfad(a, "p.fisisicherung"))
        self.assertEqual(b.namen(), {})
        b("sicherung_zusammen", self.pfad(a, "p.fisisicherung"))
        bericht("FG-92 f9: B nach Zusammenfuehren von P %s" % b.namen())
        self.assertEqual(b.namen(), {"a-vorher": 2, "b-vorher": 2})

    def test_fg92_sicherung_von_vor_dem_ersetzen_bringt_nichts_zurueck(self):
        """FG-92 PREVIEW_HINT ("Was auf diesem Geraet geloescht wurde ...,
        bleibt geloescht"), Gegenstueck zu f9: Sicherungen desselben Geraets A
        von VOR dem Ersetzen (S vor der Loeschung, Q nach der Loeschung)
        bringen auf B nichts zurueck; erst P (nach dem Ersetzen) tut es
        (Gegenprobe im selben Ablauf)."""
        a, b = self._f9_bis_zum_ersetzen()
        ta.pause()
        a("sicherung_erstellen", self.pfad(a, "p.fisisicherung"))
        meldungen = []
        for name in ("sicherung.fisisicherung", "q.fisisicherung"):
            meldungen.append(b("sicherung_zusammen", self.pfad(a, name))["meldung"])
            self.assertEqual(b.namen(), {}, name)
        self.assertIn("bleiben gelöscht", meldungen[0])
        b("sicherung_zusammen", self.pfad(a, "p.fisisicherung"))       # Gegenprobe
        bericht("FG-92 vor dem Ersetzen: Meldungen %s; danach P: %s" % (meldungen, b.namen()))
        self.assertEqual(b.namen(), {"a-vorher": 2, "b-vorher": 2})

    # ------------------------------------------------------------ A1 (gp_s6b M1)
    def _zukunft(self, code, uhr, abgleich_vorher=False, ordner=None):
        """Vorlage gp_s6b skripte/bg08_gezielt.py _zukunft: A gleicht mit
        richtiger Uhr ab, dann wird As Uhr um uhr Sekunden vorgestellt (die
        Laufzeit-Uhr laeuft weiter: gestellt). A loescht alles (Marke in der
        Zukunft) und ersetzt VOR dem naechsten Abgleich. Danach gleichen A, B
        ab, B (richtige Uhr) lernt und loescht WIRKLICH alles. Liefert die
        Lernstaende von A und B am Ende und die Aufhebung auf A."""
        a = self.voll("A", code=code, ordner=ordner)
        b = self.voll("B", tz="UTC", code=code, ordner=ordner)
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        self.alle_sync([a, b, a], 1)
        a("sicherung_erstellen", self.pfad(a))
        a("uhr", uhr, 0)
        ta.pause()
        self.assertTrue(a("reset_all")["ok"])
        if abgleich_vorher:
            a.sync()
        a("sicherung_ersetzen", self.pfad(a))
        self.alle_sync([a, b], 2)
        ta.pause()
        b("lerne", 2, "spaeter")
        b.sync()
        ta.pause()
        self.assertTrue(b("reset_all")["ok"])
        self.alle_sync([b, a], 3)
        return {"A": a.namen(), "B": b.namen(),
                "aufhebung": a("meta")["meta"].get("aufgehoben:reset_at")}

    def _a1(self, uhr):
        """v0.63.1 im selben Ablauf: A {}, B {} (Schutzprobe). 0.63.2: ebenso -
        die echte Loeschung auf B gilt, die Aufhebung haelt sie nicht auf."""
        alt = self._zukunft(self.alter_code(ALT), uhr, ordner="%s_alt" % uhr)
        for device in list(self.geraete):
            device.close()
            self.geraete.remove(device)
        ta.server_reset()
        neu = self._zukunft(CODE, uhr, ordner="%s_neu" % uhr)
        bericht("A1 Uhr %+d s: v0.63.1 %s | 0.63.2 %s" % (uhr, alt, neu))
        self.assertEqual((alt["A"], alt["B"]), ({}, {}))
        self.assertEqual((neu["A"], neu["B"]), ({}, {}))
        self.assertTrue(neu["aufhebung"])

    def test_b_g_08_a1_zukunftsmarke_eine_stunde(self):
        """A1 (gp_s6b M1): Uhr 1 h vorgestellt ("Winterzeit von Hand")."""
        self._a1(3600)

    def test_b_g_08_a1_zukunftsmarke_zehn_tage(self):
        """A1 (gp_s6b M1): Uhr 10 Tage vorgestellt."""
        self._a1(10 * 86400)

    def test_b_g_08_a1_schutz_abgleich_vor_dem_ersetzen(self):
        """Schutz (gp Test 6): A gleicht vor dem Ersetzen ab (Marke gekappt) -
        Bs Loeschung danach gilt (wie bisher)."""
        e = self._zukunft(CODE, 10 * 86400, abgleich_vorher=True)
        self.assertEqual((e["A"], e["B"]), ({}, {}))

    def test_b_g_08_a1_schutz_eingespieltes_bleibt(self):
        """Schutz: Die gekappte Aufhebung hebt die eigene Loeschung weiter auf -
        nach dem Ersetzen mit vorgestellter Uhr bleibt der eingespielte Stand
        auf A und B (ohne neue Loeschung)."""
        a = self.voll("A")
        b = self.voll("B", tz="UTC")
        a("lerne", 2, "vorher")
        self.alle_sync([a, b], 1)
        a("sicherung_erstellen", self.pfad(a))
        ta.pause()
        self.assertTrue(a("reset_all")["ok"])
        self.alle_sync([a, b], 1)            # Loeschung abgeglichen
        self.assertEqual(karten(b, "-vorher"), 0)
        a("uhr", 10 * 86400, 0)
        ta.pause()
        self.assertTrue(a("reset_all")["ok"])          # Zukunftsmarke
        a("sicherung_ersetzen", self.pfad(a))
        self.alle_sync([a, b], 2)
        b("lerne", 1, "neu")
        self.alle_sync([b, a], 2)
        paar = json.loads(a("meta")["meta"]["aufgehoben:reset_at"])
        bericht("A1 Schutz eingespielt: A %s, B %s, Aufhebung %s"
                % (a.namen(), b.namen(), paar))
        for device in (a, b):
            self.assertEqual(device.namen(), {"a-vorher": 2, "b-neu": 1}, device.name)
        # gekappt auf die Uhrzeit von GitHub (nicht 10 Tage voraus)
        alt = fisi_sync.parse_marker(paar[0])[1]
        jetzt = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        self.assertLess(alt, jetzt + datetime.timedelta(seconds=fisi_core.CLOCK_TOLERANCE))
        self.stabil([a, b])

    # ------------------------------------------------------------ T-b / T-c mit B-G-08
    def _bg08_haken(self, ersetzer):
        """vorher/zwischen fuer mischbetrieb: ersetzer ("A" oder "B") erstellt
        nach Schritt 1 eine Sicherung und spielt sie nach den Loeschungen mit
        "Alles ersetzen" ein; danach Abgleich A, B."""
        def geraet(a, b):
            return a if ersetzer == "A" else b

        def vorher(test, a, b, c):
            device = geraet(a, b)
            device("sicherung_erstellen", self.pfad(device, "s6b.fisisicherung"))

        def zwischen(test, a, b, c):
            device = geraet(a, b)
            ta.pause()
            device("sicherung_ersetzen", self.pfad(device, "s6b.fisisicherung"))
            test.alle_sync([device, b if device is a else a], 2)
        return vorher, zwischen

    def _bg08_referenz(self, a_zuerst, ersetzer):
        alt = self.alter_code(ALT)
        vorher, zwischen = self._bg08_haken(ersetzer)
        referenz, _ = self.mischbetrieb(alt, alt, alt, a_zuerst, zwischen=zwischen,
                                        vorher=vorher, lauf="_nur_alt")
        # T-c: B (0.63.2) loescht "Projekt a-1" (Frage 9)
        referenz = projekt_leer_erwarten(referenz, () if a_zuerst else ("Projekt a-1",))
        for device in list(self.geraete):
            device.close()
            self.geraete.remove(device)
        ta.server_reset()
        return referenz

    def _bg08_nichts_verloren(self, referenz, staende, text):
        for name, stand in staende.items():
            fehlt = fehlt_gegen(referenz, stand)
            bericht("%s %s: fehlt gegen nur v0.63.1: %s; Zeilen %s" % (
                text, name, fehlt or "nichts",
                {t: len(r) for t, r in sorted(stand.items()) if r}))
            self.assertEqual(fehlt, {}, "%s %s verliert mehr als v0.63.1" % (text, name))

    def _bg08_altes_geraet_ersetzt(self, a_zuerst, code_c):
        """Nicos Geraet A (v0.63.1) ersetzt: wie heute (nichts aufgehoben),
        gleich dem Ablauf nur mit v0.63.1 bis auf B-G-17."""
        referenz = self._bg08_referenz(a_zuerst, "A")
        vorher, zwischen = self._bg08_haken("A")
        gemischt, _ = self.mischbetrieb(self.alter_code(ALT), CODE, code_c, a_zuerst,
                                        zwischen=zwischen, vorher=vorher, lauf="_gemischt")
        self._bg08_nichts_verloren(referenz, {"alle": gemischt}, "B-G-08 A ersetzt")
        for table in referenz:
            if table != "spiel_bestenliste":
                self.assertEqual(gemischt[table], referenz[table], table)
        self.assertNotIn("aufgehoben", ta.datei())

    def _bg08_neues_geraet_ersetzt(self, a_zuerst, code_c):
        """Das neue Geraet B (0.63.2) ersetzt, Nicos Geraet A hat v0.63.1,
        danach kommt das Offline-Geraet C: Kein Geraet verliert etwas, was es
        im Ablauf nur mit v0.63.1 behaelt. Solange A alt ist: Hin und Her
        (gezaehlt). Danach A (und C) auf 0.63.2: alle gleich, Ruhe, der
        eingespielte Stand ist ueberall da."""
        alt = self.alter_code(ALT)
        referenz = self._bg08_referenz(a_zuerst, "B")
        vorher, zwischen = self._bg08_haken("B")
        staende, (a, b, c) = self.mischbetrieb(alt, CODE, code_c, a_zuerst, zwischen=zwischen,
                                               vorher=vorher, lauf="_gemischt", pruefen=False)
        self._bg08_nichts_verloren(referenz, staende, "B-G-08 B ersetzt, gemischt")
        # Sonderfall FG-81 (Antwort Meldung 21, 2.7, hart): A (v0.63.1) loescht
        # das Eingespielte bei sich (alte Marke) und laedt die Loeschung immer
        # wieder hoch - B (und C mit 0.63.2) behalten es trotzdem; ein Geraet
        # mit v0.63.1 loescht es bei sich weiterhin.
        bericht("B-G-08 Sonderfall FG-81: Datei-Marken %s, Feld %s; Karten x-1 A %s, B %s, C %s"
                % (ta.datei().get("markers"), ta.datei().get("aufgehoben"),
                   *[[karten(d, "%s-1" % n) for n in "abc"] for d in (a, b, c)]))
        for name in ("a", "b", "c"):
            self.assertEqual(karten(b, "%s-1" % name), 1, "B (0.63.2) %s-1" % name)
            self.assertEqual(karten(a, "%s-1" % name), 0, "A (v0.63.1) %s-1" % name)
            self.assertEqual(karten(c, "%s-1" % name), 1 if code_c == CODE else 0,
                             "C %s-1" % name)
        a.sync()            # A (v0.63.1) laedt seine Loeschung hoch, ohne das Feld
        datei = ta.datei()
        self.assertTrue(datei["markers"].get("reset_at"))
        self.assertNotIn("aufgehoben", datei)
        b.sync()            # B bekommt genau diese Datei
        bericht("B-G-08 Sonderfall FG-81 direkt: Datei von A %s -> B danach %s"
                % (datei["markers"].get("reset_at"), [karten(b, "%s-1" % n) for n in "abc"]))
        for name in ("a", "b", "c"):
            self.assertEqual(karten(b, "%s-1" % name), 1, "B nach As Loeschung %s-1" % name)
        vorher_n = ta.commits()
        self.alle_sync([a, b, c], 2)
        bericht("B-G-08 B ersetzt: 2 Runden ohne Lernen im Mischbetrieb -> %d Hochladungen"
                % (ta.commits() - vorher_n))
        a = self.neu_starten(a, CODE)
        if code_c != CODE:
            c = self.neu_starten(c, CODE)
        self.alle_sync([a, b, c], 3)
        self.stabil([a, b, c])
        stand = inhalt_ohne_zeit(self.gleich_und_ohne_doppelte([a, b, c]))
        self._bg08_nichts_verloren(referenz, {"alle (aktualisiert)": stand},
                                   "B-G-08 B ersetzt, danach alle 0.63.2")
        for name in ("a", "b", "c"):
            self.assertEqual(karten(a, "%s-1" % name), 1, name)

    def test_t_b_b_g_08_neues_geraet_ersetzt_offline_neu(self):
        """T-b (F3-Zusatz): Nicos Geraet v0.63.1 + neues Geraet 0.63.2 (es
        ersetzt), dann Offline-Geraet mit 0.63.2."""
        self._bg08_neues_geraet_ersetzt(True, CODE)

    def test_t_b_b_g_08_neues_geraet_ersetzt_offline_alt(self):
        """T-b wie oben, das Offline-Geraet hat v0.63.1."""
        self._bg08_neues_geraet_ersetzt(True, self.alter_code(ALT))

    def test_t_b_b_g_08_altes_geraet_ersetzt(self):
        """T-b: Nicos Geraet v0.63.1 ersetzt selbst, Offline-Geraet 0.63.2."""
        self._bg08_altes_geraet_ersetzt(True, CODE)

    def test_t_c_b_g_08_neues_geraet_zuerst_ersetzt(self):
        """T-c: das neue Geraet loescht zuerst und ersetzt; Offline-Geraet
        mit 0.63.2."""
        self._bg08_neues_geraet_ersetzt(False, CODE)

    def test_t_c_b_g_08_altes_geraet_ersetzt_offline_alt(self):
        """T-c: neues Geraet loescht zuerst, Nicos Geraet v0.63.1 ersetzt,
        Offline-Geraet v0.63.1."""
        self._bg08_altes_geraet_ersetzt(False, self.alter_code(ALT))



if __name__ == "__main__":
    unittest.main(verbosity=2)
