#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Abgleich-Kern 0.63.2 (Plan 0.63.2, Bauauftrag S6a; Teilplan S6 1.1, 1.7, 1.8, 2):

  G-B     Sperre bei beschaedigter Datenbank vor JEDEM Schreibblock: im
          Abgleich auch nach dem Netzzugriff (fisi_sync.sync) und direkt vor
          dem Schreibblock von merge_into_local; in der Sicherung vor dem
          Schreibblock von "Alles ersetzen" (nach der Sicherheitskopie) und
          vor dem Zurueckholen geloeschter Spielstaende (merge_backup).
  B-G-17  "Bestenliste loeschen": Die Marke liegt eine Sekunde vor dem
          Loeschen; ein Eintrag aus derselben Sekunde bleibt (auch auf einem
          Geraet mit 0.63.1).
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
        mit der eigenen Datei: Der neue Eintrag bleibt (vorher: 0 Zeilen)."""
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

    def test_b_g_17_marke_eine_sekunde_frueher(self):
        """Die Marke ist genau eine Sekunde frueher, die Zone bleibt (auch
        ueber die Zeitumstellung und den Jahreswechsel; als UTC exakt)."""
        faelle = [("2026-10-25 02:00:00+01:00", "2026-10-25 01:59:59+01:00"),
                  ("2027-01-01 00:00:00+01:00", "2026-12-31 23:59:59+01:00"),
                  ("2026-07-01 12:30:15+02:00", "2026-07-01 12:30:14+02:00"),
                  ("2026-07-01 12:30:15-05:30", "2026-07-01 12:30:14-05:30")]
        for jetzt, soll in faelle:
            db = neue_db("bg17_marke")
            with mock.patch.object(fisi_core.DBManager, "_marker_now",
                                   staticmethod(lambda cur, v=jetzt: (v, 0))):
                self.assertTrue(db.reset_records())
            self.assertEqual(db.get_meta("bestenliste_reset_at"), soll)
            parsed = fisi_sync.parse_marker(soll)
            vorher = fisi_sync.parse_marker(jetzt)
            self.assertEqual((vorher[1] - parsed[1]).total_seconds(), 1.0)

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
    def mischbetrieb(self, code_a, code_b, code_c, a_zuerst=True, zwischen=None, lauf=""):
        """Ablauf mit drei Geraeten (A = Nicos Geraet, B = zweites Geraet, C =
        Geraet, das waehrend der Loeschungen offline ist):
          1. alle lernen (alle Tabellen), Abgleich A, B, C, A, B
          2. C lernt offline weiter (vor den Loeschungen)
          3. erster (A oder B) lernt, "Bestenliste loeschen" + Eintrag in
             derselben Sekunde, "Projekt loeschen"; Abgleich
          4. zweiter lernt, "Bestenliste loeschen" + Eintrag; Abgleich
          5. erster: "Alle Lerndaten loeschen"; beide lernen danach;
             3 Runden Abgleich, Ruhe
          6. zwischen(self, a, b, c) - Platz fuer weitere Schritte (S6b)
          7. C kommt zurueck, lernt, 3 Runden Abgleich mit allen, Ruhe
        Rueckgabe: Lernstand ohne uid/Zeit (gleich auf allen Geraeten)."""
        ordner = self.id().rsplit(".", 1)[-1] + lauf
        a = self.voll("A", code=code_a, ordner=ordner)
        b = self.voll("B", code=code_b, ordner=ordner)
        c = self.voll("C", code=code_c, tz="UTC", ordner=ordner)
        for device in (a, b, c):
            device("fuelle", "1")
        self.alle_sync([a, b, c, a, b], 1)
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



if __name__ == "__main__":
    unittest.main(verbosity=2)
