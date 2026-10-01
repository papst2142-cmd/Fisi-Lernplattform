#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer Sicherung und Wiederherstellung (fisi_sicherung.py) - ohne
Oberflaeche. Alle Datenbanken und die einstellungen.json liegen in einem
Temp-Ordner (FISI_DB_PATH), die echten Einstellungen bleiben unberuehrt.

Start:  python test_sicherung.py
"""

import gzip
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fisi_game as fg  # noqa: E402
import fisi_sicherung as fs  # noqa: E402
import fisi_sync  # noqa: E402
from fisi_core import ACTIVE_RUN_KEY, LEGACY_RUN, SYNC_TABLES, DBManager  # noqa: E402
from fisi_update import load_settings, save_settings  # noqa: E402

FAKE_TOKEN = "github_pat_GEHEIM1234567890"


def _rows(db, table):
    """Alle Zeilen einer Tabelle (uid und Datenspalten), nach uid sortiert."""
    conn = sqlite3.connect(db.db_path)
    try:
        return conn.execute("SELECT uid, %s FROM %s ORDER BY uid"
                            % (", ".join(SYNC_TABLES[table]), table)).fetchall()
    finally:
        conn.close()


def _all_rows(db):
    return {table: _rows(db, table) for table in SYNC_TABLES}


def _markers(db):
    return fisi_sync.export_local(db)["markers"]


def _fill_learning(db, tag="A"):
    """Lern-Eintraege ueber die echten Schreibfunktionen der Datenbank."""
    db.log_card("Netzwerk", "Frage %s1" % tag, "lernen", True)
    db.log_card("Netzwerk", "Frage %s2" % tag, "lernen", False)
    db.log_quiz_answer("Systeme", "Quiz %s" % tag, True)
    db.save_test_result(8, 10, 80.0, "gut", 300)
    db.log_scenario(1, "Szenario %s" % tag, "Netz", True)
    db.log_project(2, "Projekt %s" % tag, "Netzwerk", None)
    db.log_ap1(3, "AP1 %s" % tag, "Hardware", False)
    db.log_trainer("ipv4", 2, True)
    db.save_exam("ap1", 77, "befriedigend", 900, json.dumps({"tag": tag}))
    db.save_project_field("p_%s" % tag, "titel", "Abschluss %s" % tag)


def _new_slot(db, slot, name="", events=3, device="PC"):
    """Spielstand-Platz mit ein paar Ereignissen (ueber fisi_game.Game)."""
    game = fg.Game(db, device)
    run = game.new_run(slot)
    if name:
        game.rename_slot(slot, name)
    for number in range(events):
        db.log_game_event("test_%d" % number, json.dumps({"n": number}), device, run)
    db.log_record("2026-01-01 10:00:00", "erfolg", "%s:1" % run, 1, "{}")
    return game, run


class Temp:
    """Temp-Ordner mit FISI_DB_PATH dorthin (fuer einstellungen.json)."""

    def __init__(self):
        self.folder = tempfile.mkdtemp()
        self.old = os.environ.get("FISI_DB_PATH")
        os.environ["FISI_DB_PATH"] = os.path.join(self.folder, "fisi.db")
        self.count = 0

    def db(self):
        self.count += 1
        return DBManager(os.path.join(self.folder, "db%d.db" % self.count))

    def close(self):
        if self.old is None:
            os.environ.pop("FISI_DB_PATH", None)
        else:
            os.environ["FISI_DB_PATH"] = self.old
        shutil.rmtree(self.folder, ignore_errors=True)


class SicherungTest(unittest.TestCase):
    def setUp(self):
        self.temp = Temp()
        self.addCleanup(self.temp.close)

    def _full_db(self):
        db = self.temp.db()
        _fill_learning(db)
        _new_slot(db, 1, "Firma Nord")
        _new_slot(db, 2)
        db.set_meta("history_cleared_at", "2020-01-01 00:00:00")
        db.set_meta("spiel_reset_at", "2020-02-01 00:00:00")
        return db

    # -- Rundreise ------------------------------------------------------------

    def test_ersetzen_stellt_alles_zeilengenau_her(self):
        source = self._full_db()
        backup = fs.read_backup(fs.create_backup(source, "0.51", "PC"))
        target = self.temp.db()
        path = fs.replace_all(target, backup, os.path.join(self.temp.folder, "kopie"))
        self.assertTrue(os.path.exists(path))
        expected, actual = _all_rows(source), _all_rows(target)
        for table in SYNC_TABLES:
            self.assertEqual(actual[table], expected[table], table)
        for table in ("card_events", "spiel_ereignisse", "spiel_plaetze",
                      "spiel_bestenliste", "abschlussprojekt", "pruefungen"):
            self.assertTrue(expected[table], table)
        self.assertTrue(any(row[-1] for row in expected["spiel_ereignisse"]))  # lauf
        self.assertEqual(_markers(target), _markers(source))
        self.assertEqual(fg.Game(target).layout()["namen"], {1: "Firma Nord"})

    def test_sicherheitskopie_vor_dem_ersetzen(self):
        target = self.temp.db()
        _fill_learning(target, "alt")
        before = _all_rows(target)
        backup = fs.read_backup(fs.create_backup(self._full_db(), "0.51"))
        folder = os.path.join(self.temp.folder, "kopie")
        path = fs.replace_all(target, backup, folder)
        self.assertTrue(os.path.basename(path).startswith("vor_wiederherstellung_"))
        self.assertTrue(path.endswith(fs.BACKUP_EXT))
        with open(path, "rb") as handle:
            safety = fs.read_backup(handle.read())
        restored = self.temp.db()
        fs.replace_all(restored, safety, folder)
        self.assertEqual(_all_rows(restored), before)
        # Zweimal in derselben Minute: die erste Kopie bleibt erhalten
        second = fs.replace_all(target, backup, folder)
        self.assertNotEqual(second, path)
        self.assertTrue(os.path.exists(path))

    def test_ersetzen_aendert_die_stempel(self):
        db = self._full_db()
        game = fg.Game(db)
        before, game_before = db.change_stamp(), db.game_event_stamp(game.run)
        backup = fs.read_backup(fs.create_backup(db, "0.51"))
        fs.replace_all(db, backup, self.temp.folder)
        self.assertNotEqual(db.change_stamp(), before)
        self.assertNotEqual(db.game_event_stamp(game.run), game_before)
        self.assertEqual(db.game_event_stamp(game.run)[0], game_before[0])

    # -- Zusammenfuehren ------------------------------------------------------

    def test_zusammenfuehren_vereinigt_ohne_doppelte(self):
        first, second = self.temp.db(), self.temp.db()
        _fill_learning(first, "A")
        _new_slot(first, 1, "PC-Firma")
        _fill_learning(second, "B")
        _new_slot(second, 2, "Handy-Firma", events=2, device="Handy")
        uids_first = {t: {r[0] for r in rows} for t, rows in _all_rows(first).items()}
        uids_second = {t: {r[0] for r in rows} for t, rows in _all_rows(second).items()}
        backup = fs.read_backup(fs.create_backup(second, "0.51", "Handy"))
        received = fs.merge_backup(first, backup)
        merged = {t: {r[0] for r in rows} for t, rows in _all_rows(first).items()}
        for table in SYNC_TABLES:
            self.assertEqual(merged[table], uids_first[table] | uids_second[table], table)
        self.assertEqual(received, sum(len(u) for u in uids_second.values()))
        self.assertEqual(fs.merge_backup(first, backup), 0)
        layout = fg.Game(first).layout()
        self.assertEqual(len(layout["plaetze"]), 2)
        # Das Abschlussprojekt bleibt pro Feld die neueste Fassung (zwei Projekte)
        self.assertEqual(len(_rows(first, "abschlussprojekt")), 2)

    def test_geloeschter_platz_bleibt_beim_zusammenfuehren_geloescht(self):
        db = self.temp.db()
        game, run = _new_slot(db, 1, "Firma Nord", events=4)
        backup = fs.read_backup(fs.create_backup(db, "0.51"))
        game.delete_run(run)
        self.assertEqual(fs.merge_backup(db, backup), 0)
        self.assertEqual(db.event_counts().get(run, 0), 0)
        self.assertEqual(fs.deleted_runs(db, backup),
                         [{"lauf": run, "name": "Firma Nord", "ereignisse": 4}])
        self.assertIn("1 gelöschten Spielstand („Firma Nord“)",
                      fs.deleted_question(fs.deleted_runs(db, backup)))

    def test_geloeschten_platz_als_neuen_platz_wiederherstellen(self):
        db = self.temp.db()
        game, run = _new_slot(db, 1, "Firma Nord", events=4)
        events = db.game_events(run)
        backup = fs.read_backup(fs.create_backup(db, "0.51"))
        game.delete_run(run)
        received = fs.merge_backup(db, backup, restore_runs=[run], device="PC")
        self.assertEqual(received, 4 + 2)          # Ereignisse, angelegt, umbenannt
        layout = fg.Game(db).layout()
        self.assertEqual(len(layout["plaetze"]), 1)
        slot, new_run = next(iter(layout["plaetze"].items()))
        self.assertNotEqual(new_run, run)
        self.assertEqual(layout["namen"].get(slot), "Firma Nord")
        self.assertEqual(db.game_events(new_run), events)
        uids_old = {row[0] for row in json.loads(json.dumps(
            backup["daten"]["tables"]["spiel_ereignisse"]))}
        uids_new = {row[0] for row in _rows(db, "spiel_ereignisse")}
        self.assertFalse(uids_old & uids_new)
        # Ein weiteres Zusammenfuehren (oder ein Abgleich) loescht ihn nicht wieder
        fs.merge_backup(db, backup)
        self.assertEqual(len(db.game_events(new_run)), 4)
        other = self.temp.db()
        fisi_sync.merge_into_local(other, fisi_sync.export_local(db))
        self.assertEqual(len(other.game_events(new_run)), 4)
        self.assertEqual(fs.deleted_runs(db, backup)[0]["lauf"], run)

    def test_alter_durchgang_ohne_lauf_wiederherstellen(self):
        db = self.temp.db()
        for number in range(2):
            db.log_game_event("alt_%d" % number, "{}", "PC", run=None)
        backup = fs.read_backup(fs.create_backup(db, "0.47"))
        db.delete_run(1, LEGACY_RUN)
        found = fs.deleted_runs(db, backup)
        self.assertEqual(found, [{"lauf": LEGACY_RUN, "name": "Spielstand", "ereignisse": 2}])
        self.assertEqual(fs.merge_backup(db, backup, [LEGACY_RUN]), 2 + 1)
        self.assertEqual(len(fg.Game(db).layout()["plaetze"]), 1)

    def test_volle_plaetze_schreiben_nichts(self):
        db = self.temp.db()
        game, run = _new_slot(db, 1, "Weg")
        backup = fs.read_backup(fs.create_backup(db, "0.51"))
        game.delete_run(run)
        for slot in (1, 2, 3):
            _new_slot(db, slot)
        before = _all_rows(db)
        with self.assertRaises(fs.BackupError) as caught:
            fs.merge_backup(db, backup, restore_runs=[run])
        self.assertEqual(str(caught.exception),
                         "Alle 3 Spielstand-Plätze sind belegt. Lösche zuerst einen Platz, "
                         "dann kannst du den Spielstand wiederherstellen.")
        self.assertEqual(_all_rows(db), before)

    def test_plaetze_der_sicherung_zaehlen_beim_pruefen_mit(self):
        """Bringt die Sicherung selbst Plaetze mit, sind die danach belegt."""
        db = self.temp.db()
        game, run = _new_slot(db, 1, "Weg")
        backup_old = fs.read_backup(fs.create_backup(db, "0.51"))
        game.delete_run(run)
        other = self.temp.db()
        fisi_sync.merge_into_local(other, fisi_sync.export_local(db))
        for slot in (1, 2, 3):
            _new_slot(other, slot)
        fs.merge_backup(db, backup_old)                       # Platz-Zeilen zuerst
        backup_full = fs.read_backup(fs.create_backup(other, "0.51"))
        merged = dict(backup_full)
        merged["daten"] = dict(backup_full["daten"])
        tables = dict(backup_full["daten"]["tables"])
        tables["spiel_ereignisse"] = (tables["spiel_ereignisse"] +
                                      backup_old["daten"]["tables"]["spiel_ereignisse"])
        merged["daten"]["tables"] = tables
        self.assertEqual(len(fg.Game(db).layout()["plaetze"]), 0)   # hier noch alles frei
        before = _all_rows(db)
        with self.assertRaises(fs.BackupError):
            fs.merge_backup(db, merged, restore_runs=[run])
        self.assertEqual(_all_rows(db), before)

    def test_belegung_wie_im_spiel(self):
        db = self.temp.db()
        game, run = _new_slot(db, 2, "Zwei")
        _new_slot(db, 3, "Drei")
        game.delete_run(run)
        _new_slot(db, 1, "Eins")
        rows = fs._local_slot_rows(db)
        slots, names = fs._slot_state(rows, False)
        layout = fg.slot_layout(db.slot_rows(), False)
        self.assertEqual((slots, names), (layout["plaetze"], layout["namen"]))
        self.assertEqual((fs.SLOT_COUNT, fs.SLOT_CREATED, fs.SLOT_DELETED, fs.SLOT_RENAMED,
                          fs.SLOT_NAME_MAX, fs.BADGE_KIND),
                         (fg.SLOT_COUNT, fg.SLOT_CREATED, fg.SLOT_DELETED, fg.SLOT_RENAMED,
                          fg.SLOT_NAME_MAX, fg.REC_BADGE))

    # -- Pruefen beim Lesen ---------------------------------------------------

    def _pack(self, value):
        return gzip.compress(json.dumps(value).encode("utf-8"))

    def _unpack(self, raw):
        return json.loads(gzip.decompress(raw).decode("utf-8"))

    def test_fehlerhafte_dateien(self):
        good = fs.create_backup(self._full_db(), "0.51")
        cases = [
            (b"keine Sicherung", fs.MSG_NOT_BACKUP),
            (b"", fs.MSG_NOT_BACKUP),
            (good[:40], fs.MSG_NOT_BACKUP),
            (gzip.compress(b"\xff\xfe kein JSON"), fs.MSG_NOT_BACKUP),
            (self._pack({"art": "Etwas anderes", "daten": {}}), fs.MSG_NOT_BACKUP),
            (self._pack([1, 2, 3]), fs.MSG_NOT_BACKUP),
        ]
        broken = self._unpack(good)
        broken["daten"]["tables"]["card_events"][0][2] = "Manipuliert"
        cases.append((self._pack(broken), "Die Sicherung ist beschädigt (Prüfsumme "
                                          "stimmt nicht)."))
        newer = self._unpack(good)
        newer["formatversion"] = fs.FORMAT_VERSION + 1
        newer["app_version"] = "0.60"
        cases.append((self._pack(newer), "Die Sicherung stammt aus Version 0.60. Bitte "
                                         "zuerst die App aktualisieren."))
        newer_sync = self._unpack(good)
        newer_sync["daten"]["format"] = fisi_sync.FORMAT + 1
        newer_sync["app_version"] = "0.70"
        newer_sync["pruefsumme"] = fs._checksum(newer_sync["daten"],
                                                newer_sync["einstellungen"])
        cases.append((self._pack(newer_sync), "Die Sicherung stammt aus Version 0.70. "
                                              "Bitte zuerst die App aktualisieren."))
        for raw, message in cases:
            with self.assertRaises(fs.BackupError) as caught:
                fs.read_backup(raw)
            self.assertEqual(str(caught.exception), message)

    def test_aufbau_der_datei(self):
        db = self._full_db()
        backup = self._unpack(fs.create_backup(db, "0.51", "PC test"))
        self.assertEqual(backup["art"], "FISI-Sicherung")
        self.assertEqual(backup["formatversion"], 1)
        self.assertEqual((backup["app_version"], backup["geraet"]), ("0.51", "PC test"))
        self.assertEqual(backup["daten"], json.loads(json.dumps(fisi_sync.export_local(db))))
        self.assertEqual(backup["daten"]["format"], fisi_sync.FORMAT)
        self.assertEqual(len(backup["pruefsumme"]), 64)
        summary = fs.backup_summary(backup)
        self.assertEqual((summary["lerneintraege"], summary["spielstaende"],
                          summary["abzeichen"], summary["projekte"]), (9, 2, 2, 1))
        self.assertEqual(backup["zusammenfassung"]["lerneintraege"], 9)
        self.assertIn("Lern-Einträge: 9", summary["zeilen"])
        self.assertIn("Gerät: PC test", summary["zeilen"])
        self.assertRegex(summary["zeilen"][0], r"^Erstellt: \d\d\.\d\d\.\d{4}, \d\d:\d\d Uhr$")
        self.assertRegex(fs.default_name(), r"^FISI-Sicherung_\d{4}-\d\d-\d\d_\d{4}"
                                            r"\.fisisicherung$")
        import datetime
        self.assertEqual(fs.default_name(datetime.datetime(2026, 10, 1, 14, 23)),
                         "FISI-Sicherung_2026-10-01_1423.fisisicherung")

    # -- Einstellungen ----------------------------------------------------------

    def test_token_kommt_nie_in_die_sicherung(self):
        settings = load_settings()
        settings.update({"sync_token": FAKE_TOKEN, "sync_repo": "nutzer/geheim-repo",
                         "farbe": "lila", "ziel_anzahl": 35})
        self.assertTrue(save_settings(settings))
        raw = gzip.decompress(fs.create_backup(self._full_db(), "0.51")).decode("utf-8")
        self.assertNotIn(FAKE_TOKEN, raw)
        self.assertNotIn("geheim-repo", raw)
        self.assertNotIn("lila", raw)
        backup = json.loads(raw)
        self.assertEqual(set(backup["einstellungen"]),
                         {"ziel_an", "ziel_anzahl", "serie_an", "erinnerung_an",
                          "erinnerung_zeit"})
        self.assertEqual(backup["einstellungen"]["ziel_anzahl"], 35)

    def test_einstellungen_zusammenfuehren_und_ersetzen(self):
        save_settings({"sync_token": FAKE_TOKEN, "ziel_anzahl": 40, "erinnerung_zeit": "07:30",
                       "farbe": "blau"})
        db = self._full_db()
        backup = fs.read_backup(fs.create_backup(db, "0.51"))
        save_settings({"sync_token": FAKE_TOKEN, "ziel_anzahl": 10, "erinnerung_zeit": "20:00",
                       "farbe": "gruen"})
        fs.merge_backup(db, backup)
        settings = load_settings()
        self.assertEqual((settings["ziel_anzahl"], settings["erinnerung_zeit"]), (10, "20:00"))
        fs.replace_all(db, backup, self.temp.folder)
        settings = load_settings()
        self.assertEqual((settings["ziel_anzahl"], settings["erinnerung_zeit"]), (40, "07:30"))
        self.assertEqual((settings["sync_token"], settings["farbe"]), (FAKE_TOKEN, "gruen"))

    def test_aktiver_platz_bleibt_geraetebezogen(self):
        db = self._full_db()
        active = db.get_meta(ACTIVE_RUN_KEY)
        backup = fs.read_backup(fs.create_backup(db, "0.51"))
        fs.replace_all(db, backup, self.temp.folder)
        self.assertEqual(db.get_meta(ACTIVE_RUN_KEY), active)
        self.assertNotIn(ACTIVE_RUN_KEY, json.dumps(backup))


if __name__ == "__main__":
    unittest.main(verbosity=2)
