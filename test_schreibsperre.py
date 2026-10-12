#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests zur Gegenpruefung 0.62.5 (gegenpruefung_0625/gegenpruefung.md):

  M-1  (Gruppe 5.1, B-G-06) Wird nichts mehr gespeichert (read_only_reason,
       z.B. beschaedigte Datenbank), schreiben auch der Abgleich
       (fisi_sync.sync, merge_into_local) und die Sicherung (Zusammenfuehren,
       Alles ersetzen) nicht in die Datei, sondern brechen mit einer
       deutschen Meldung ab. "Sicherung erstellen" (nur lesen) geht weiter.
  G-1  (Gruppe 5.2) Die Hilfsdatei einstellungen.json.sicherung.tmp bekommt
       0600, auch wenn eine alte Hilfsdatei mit 0644 liegt - einstellungen.json
       hat nach "Alles ersetzen" 0600 (nur Linux/macOS, unter Windows
       uebersprungen: os.chmod wirkt dort kaum).
  G-2  (Gruppe 5.2) Eine liegengebliebene Hilfsdatei (mit Zugangsschluessel)
       wird beim Start (PC und Handy) bzw. vor der naechsten Sicherung
       aufgeraeumt.
  G-4  (Gruppe 5.4) Startet der Abgleich-Thread nicht, wartet das Schliessen
       nicht die ganze Frist (app_gui.SyncController._idle).

Die beschaedigte Datenbank wird wie in der Gegenpruefung gebaut
(skripte/sync_kaputt.py): 6000 Trainer-Aufgaben, eine Blattseite des Index
ix_trainer_aufgaben_uid mit Zufall ueberschrieben. Alles in Temp-Ordnern
(HOME, FISI_DB_PATH), nie echte Daten, keine Verbindung nach aussen
(fetch_remote/upload sind Attrappen).

Gegenprobe gegen einen anderen Stand (auf 4528241 sind alle Tests ausser den
mit "Schutz" gekennzeichneten rot):
    SPERRE_CODE=<ordner mit dem Code> xvfb-run -a python test_schreibsperre.py
Start:  xvfb-run -a python test_schreibsperre.py   (G-4 braucht app_gui)
"""

import hashlib
import json
import os
import random
import shutil
import sqlite3
import stat
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("SPERRE_CODE") or HERE)
WORK = tempfile.mkdtemp(prefix="fisi_schreibsperre_")
HOME = os.path.join(WORK, "home")
os.makedirs(HOME)
os.environ["HOME"] = HOME
os.environ["APPDATA"] = HOME
os.environ["FISI_DB_PATH"] = os.path.join(HOME, "start.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(WORK, "selbsttest.log"))
os.environ["FISI_VORLADEN"] = "0"

sys.path.insert(0, CODE)
sys.path.insert(1, os.path.join(CODE, "mobile", "src"))
import fisi_core  # noqa: E402
import fisi_sicherung as fsi  # noqa: E402
import fisi_sync  # noqa: E402
import fisi_update  # noqa: E402

TOKEN = "PLATZHALTER_KEIN_ECHTER_SCHLUESSEL"
_COUNTER = [0]


def beleg(text):
    print("  [Beleg] %s" % text, flush=True)


def sha(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def new_path(name):
    _COUNTER[0] += 1
    folder = os.path.join(WORK, "%s_%d" % (name, _COUNTER[0]))
    os.makedirs(folder)
    return os.path.join(folder, "fisi_lernplattform.db")


def broken_db():
    """Datenbank mit beschaedigter Indexseite (wie die Gegenpruefung):
    quick_check findet den Schaden, Tabellen sind noch lesbar."""
    path = new_path("kaputt")
    fisi_core.DBManager(path, error_handler=lambda message: None)
    conn = sqlite3.connect(path)
    conn.executemany("INSERT INTO trainer_aufgaben (timestamp, art, stufe, correct, uid)"
                     " VALUES (?, 'subnetz', 1, ?, ?)",
                     [("2026-09-02 08:00:00", i % 2, "t%05d" % i) for i in range(6000)])
    conn.commit()
    page = conn.execute("PRAGMA page_size").fetchone()[0]
    leaves = [r[0] for r in conn.execute(
        "SELECT pageno FROM dbstat WHERE name='ix_trainer_aufgaben_uid' AND pagetype='leaf'"
        " ORDER BY pageno")]
    conn.close()
    victim = leaves[len(leaves) // 2]
    with open(path, "r+b") as handle:
        handle.seek((victim - 1) * page)
        handle.write(random.Random(42).randbytes(page))
    messages = []
    db = fisi_core.DBManager(path, error_handler=messages.append)
    return db, messages


def remote_data(uid="fremd1"):
    """Lernstand eines anderen Geraets mit einer Quiz-Antwort."""
    columns = list(fisi_sync.SYNC_TABLES["quiz_answers"])
    values = {"timestamp": "2026-09-03 10:00:00", "category": "Netzwerktechnik",
              "question": "Frage", "correct": 1}
    return {"format": fisi_sync.FORMAT, "markers": {},
            "columns": {"quiz_answers": columns},
            "tables": {"quiz_answers": [[uid] + [values.get(c) for c in columns]]}}


def count_uid(path, uid):
    conn = sqlite3.connect(path)
    try:
        return conn.execute("SELECT count(*) FROM quiz_answers WHERE uid=?",
                            (uid,)).fetchone()[0]
    finally:
        conn.close()


def a_backup(only_quiz=False):
    """Sicherung eines heilen Geraets mit einer Quiz-Antwort. only_quiz: nur
    die Tabelle quiz_answers (wie eine Sicherung mit weniger Tabellen) - der
    Schaden im Index von trainer_aufgaben wird dann beim Zusammenfuehren nicht
    beruehrt, ohne Sperre wuerde geschrieben."""
    healthy = fisi_core.DBManager(new_path("heil"), error_handler=lambda message: None)
    healthy.log_quiz_answer("Netzwerktechnik", "Frage aus der Sicherung", True)
    backup = fsi.read_backup(fsi.create_backup(healthy, "0.62.5", "Test"))
    if only_quiz:
        data = backup["daten"]
        data["tables"] = {"quiz_answers": data["tables"]["quiz_answers"]}
        data["columns"] = {"quiz_answers": data["columns"]["quiz_answers"]}
    return backup


def flagged_db(reason):
    """Heile Datenbank, Merker von 5.1 gesetzt (z.B. Schreibschutz, der unter
    root nicht nachzustellen ist): ohne Sperre im Abgleich/in der Sicherung
    wuerde geschrieben."""
    db = fisi_core.DBManager(new_path(reason), error_handler=lambda message: None)
    db.read_only_reason = reason
    return db


def tearDownModule():
    shutil.rmtree(WORK, ignore_errors=True)


# ============================================================================
#  M-1: Schreibsperre auch fuer Abgleich und Sicherung
# ============================================================================

class SchreibsperreAbgleich(unittest.TestCase):

    def setUp(self):
        self.db, self.messages = broken_db()
        self.before = sha(self.db.db_path)
        self.line = fisi_core.DB_READ_ONLY_LINES["kaputt"]

    def test_vorbedingung_sperre_aktiv(self):
        """Schutz (auch auf 4528241 gruen): die Gruppe 5.1 erkennt den
        Schaden, genau eine Meldung."""
        self.assertEqual(self.db.read_only_reason, "kaputt")
        self.assertEqual(len(self.messages), 1)

    def test_merge_into_local_schreibt_nicht(self):
        with self.assertRaises(fisi_sync.SyncError) as caught:
            fisi_sync.merge_into_local(self.db, remote_data(), check_future=False)
        beleg("merge_into_local: %s" % caught.exception)
        self.assertIn(self.line, str(caught.exception))
        self.assertEqual(sha(self.db.db_path), self.before, "Datei wurde veraendert")
        self.assertEqual(count_uid(self.db.db_path, "fremd1"), 0)

    def test_abgleich_bricht_vor_dem_netz_ab(self):
        calls = []

        def fetch(repo, token):
            calls.append("GET")
            return "sha1", remote_data()

        def upload(*args, **kwargs):
            calls.append("PUT")
            return "sha2"

        settings = {"sync_repo": "pruef/attrappe", "sync_token": TOKEN, "sync_auto": True,
                    "sync_last": ""}
        with mock.patch.object(fisi_sync, "fetch_remote", fetch), \
                mock.patch.object(fisi_sync, "upload", upload):
            try:
                fisi_sync.sync(self.db, settings=settings, device="Test")
                error = None
            except fisi_sync.SyncError as exc:
                error = str(exc)
        beleg("Abgleich: Meldung %r, Netz-Aufrufe %s" % (error, calls))
        self.assertEqual(sha(self.db.db_path), self.before, "Datei wurde veraendert")
        self.assertEqual(count_uid(self.db.db_path, "fremd1"), 0)
        self.assertIsNotNone(error, "kein Abbruch")
        self.assertEqual(error, fisi_sync.MSG_READ_ONLY % self.line)
        self.assertEqual(calls, [])

    def test_abgleich_schreibschutz_meldung(self):
        """Auch der Schreibschutz (Merker von 5.1) sperrt den Abgleich."""
        db = flagged_db("schreibschutz")
        settings = {"sync_repo": "pruef/attrappe", "sync_token": TOKEN, "sync_auto": True,
                    "sync_last": ""}
        with mock.patch.object(fisi_sync, "fetch_remote",
                               lambda repo, token: ("sha1", remote_data())), \
                mock.patch.object(fisi_sync, "upload", lambda *a, **k: "sha2"):
            with self.assertRaises(fisi_sync.SyncError) as caught:
                fisi_sync.sync(db, settings=settings, device="Test")
        self.assertIn(fisi_core.DB_READ_ONLY_LINES["schreibschutz"], str(caught.exception))
        self.assertEqual(count_uid(db.db_path, "fremd1"), 0)


class SchreibsperreSicherung(unittest.TestCase):

    def setUp(self):
        self.backup = a_backup(only_quiz=True)
        self.db, _messages = broken_db()
        self.before = sha(self.db.db_path)
        self.line = fisi_core.DB_READ_ONLY_LINES["kaputt"]

    def test_zusammenfuehren_schreibt_nicht(self):
        with self.assertRaises(fsi.RESTORE_ERRORS) as caught:
            fsi.merge_backup(self.db, self.backup)
        text = fsi.restore_error_text(caught.exception)
        beleg("Zusammenfuehren: %s" % text)
        self.assertEqual(text, fsi.MSG_READ_ONLY % self.line)
        self.assertEqual(sha(self.db.db_path), self.before, "Datei wurde veraendert")

    def test_alles_ersetzen_schreibt_nicht(self):
        safety = os.path.join(os.path.dirname(self.db.db_path), "kopien")
        settings_before = fisi_update.load_settings()
        with self.assertRaises(fsi.RESTORE_ERRORS) as caught:
            fsi.replace_all(self.db, self.backup, safety, "0.62.5", "Test")
        text = fsi.restore_error_text(caught.exception)
        beleg("Alles ersetzen: %s" % text)
        self.assertEqual(text, fsi.MSG_READ_ONLY % self.line)
        self.assertEqual(sha(self.db.db_path), self.before, "Datei wurde veraendert")
        self.assertEqual(fisi_update.load_settings(), settings_before)

    def test_zusammenfuehren_schreibschutz(self):
        db = flagged_db("schreibschutz")
        before = sha(db.db_path)
        with self.assertRaises(fsi.RESTORE_ERRORS) as caught:
            fsi.merge_backup(db, a_backup())
        self.assertEqual(fsi.restore_error_text(caught.exception), fsi.MSG_READ_ONLY
                         % fisi_core.DB_READ_ONLY_LINES["schreibschutz"])
        self.assertEqual(sha(db.db_path), before, "Datei wurde veraendert")

    def test_alles_ersetzen_schreibschutz(self):
        db = flagged_db("schreibschutz")
        before = sha(db.db_path)
        safety = os.path.join(os.path.dirname(db.db_path), "kopien")
        with self.assertRaises(fsi.RESTORE_ERRORS) as caught:
            fsi.replace_all(db, a_backup(), safety, "0.62.5", "Test")
        self.assertEqual(fsi.restore_error_text(caught.exception), fsi.MSG_READ_ONLY
                         % fisi_core.DB_READ_ONLY_LINES["schreibschutz"])
        self.assertEqual(sha(db.db_path), before, "Datei wurde veraendert")

    def test_schutz_sicherung_erstellen_geht(self):
        """Schutz (auch auf 4528241 gruen): Sicherung erstellen liest nur."""
        data = fsi.create_backup(self.db, "0.62.5", "Test")
        backup = fsi.read_backup(data)
        self.assertEqual(len(backup["daten"]["tables"]["trainer_aufgaben"]), 6000)
        self.assertEqual(sha(self.db.db_path), self.before)


class SchutzHeileDatenbank(unittest.TestCase):
    """Schutz (auch auf 4528241 gruen): ohne Sperre wird wie bisher geschrieben."""

    def test_merge_into_local(self):
        db = fisi_core.DBManager(new_path("heil"), error_handler=lambda message: None)
        self.assertEqual(fisi_sync.merge_into_local(db, remote_data(), check_future=False), 1)
        self.assertEqual(count_uid(db.db_path, "fremd1"), 1)

    def test_zusammenfuehren(self):
        db = fisi_core.DBManager(new_path("heil"), error_handler=lambda message: None)
        self.assertEqual(fsi.merge_backup(db, a_backup()), 1)


# ============================================================================
#  G-1, G-2: Hilfsdatei einstellungen.json.sicherung.tmp
# ============================================================================

def _temp_path():
    return fisi_update._settings_path() + ".sicherung.tmp"


def _mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


class HilfsdateiTagesziel(unittest.TestCase):

    def setUp(self):
        for path in (_temp_path(), fisi_update._settings_path()):
            if os.path.exists(path):
                os.remove(path)

    @unittest.skipIf(os.name == "nt", "os.chmod wirkt unter Windows kaum")
    def test_g1_alte_hilfsdatei_0644_alles_ersetzen_0600(self):
        with open(_temp_path(), "w", encoding="utf-8") as handle:
            handle.write("{}")
        os.chmod(_temp_path(), 0o644)
        db = fisi_core.DBManager(new_path("ersetzen"), error_handler=lambda message: None)
        fisi_update.save_settings({"sync_token": TOKEN})
        fsi.replace_all(db, a_backup(), os.path.join(WORK, "kopien_g1"), "0.62.5", "Test")
        mode = _mode(fisi_update._settings_path())
        beleg("einstellungen.json nach Alles ersetzen: %s" % oct(mode))
        self.assertEqual(mode, 0o600)
        self.assertFalse(os.path.exists(_temp_path()))

    def test_g2_aufraeumen_beim_start(self):
        with open(_temp_path(), "w", encoding="utf-8") as handle:
            json.dump({"sync_token": TOKEN}, handle)
        fsi.remove_stale_temp()
        self.assertFalse(os.path.exists(_temp_path()))

    def test_g2_start_pc_und_handy_raeumen_auf(self):
        """PC (app_gui.FISIApp) und Handy (FISIMobileApp) rufen das Aufraeumen
        beim Start auf, direkt nach dem Oeffnen der Datenbank (aus dem
        Quelltext)."""
        for name in ("app_gui.py", os.path.join("mobile", "src", "main.py")):
            with open(os.path.join(CODE, name), encoding="utf-8") as handle:
                source = handle.read()
            self.assertEqual(source.count("fsi.remove_stale_temp()"), 1, name)
            start = source.index("fsi.remove_stale_temp()")
            before = source[:start].rsplit("self.db = DBManager(", 1)
            self.assertEqual(len(before), 2, name)
            self.assertLess(before[1].count("\n"), 4, name)

    def test_g2_schutz_ohne_hilfsdatei(self):
        """Schutz: ohne Hilfsdatei passiert nichts (kein Fehler)."""
        if hasattr(fsi, "remove_stale_temp"):
            fsi.remove_stale_temp()
        self.assertFalse(os.path.exists(_temp_path()))


# ============================================================================
#  G-4: Abgleich-Thread startet nicht
# ============================================================================

class _FakeRoot:
    def after(self, *_args):
        return None


class AbgleichThreadStartetNicht(unittest.TestCase):

    def test_g4_schliessen_wartet_nicht_die_ganze_frist(self):
        import app_gui
        fisi_sync.save_sync_settings(sync_repo="pruef/attrappe", sync_token=TOKEN,
                                     sync_auto=True)
        db = fisi_core.DBManager(new_path("g4"), error_handler=lambda message: None)
        app = types.SimpleNamespace(root=_FakeRoot(), db=db)
        app.updater = app_gui.UpdateController(app)
        controller = app_gui.SyncController(app)
        calls = []

        def fake_sync(*args, **kwargs):
            calls.append(threading.current_thread().name)

        def no_thread(_self):
            raise RuntimeError("can't start new thread")

        with mock.patch.object(threading.Thread, "start", no_thread):
            try:
                controller.run()
            except RuntimeError:
                pass
        controller.dirty = True
        with mock.patch.object(fisi_sync, "sync", fake_sync):
            start = time.monotonic()
            controller.run_before_exit(timeout=3)
            took = time.monotonic() - start
        beleg("Schliessen nach nicht gestartetem Thread: %.2f s, Abgleiche %d, "
              "busy %s, offene Auftraege %d" % (took, len(calls), controller._busy,
                                                app.updater._pending))
        self.assertLess(took, 2.0)
        self.assertEqual(len(calls), 1)
        self.assertFalse(controller._busy)
        self.assertEqual(app.updater._pending, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
