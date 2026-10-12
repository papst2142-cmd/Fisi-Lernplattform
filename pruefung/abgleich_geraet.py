#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ein "Geraet" fuer test_abgleich.py (ab 0.62.4, B-A-02).

Laeuft als eigener Prozess mit eigener Wegwerf-Datenbank (FISI_DB_PATH, HOME,
TMPDIR und die Zeitzone TZ setzt der Aufrufer) und fuehrt Befehle mit dem
ECHTEN Code aus (fisi_core.DBManager, fisi_sync.sync, fisi_sicherung) - wahl-
weise mit dem Code eines anderen Stands (z.B. v0.62.3 als altes Geraet).
Einzige Eingriffe (Behelfe):
  * fisi_sync.API zeigt auf die Attrappe (http://127.0.0.1:<port>).
  * Die Uhr dieses Geraets laesst sich verstellen ("uhr", "zeit"):
    datetime.datetime.now() in fisi_core/fisi_sync/fisi_sicherung liefert dann
    echte Zeit + Versatz.
  * Ab 0.62.5 (Restrisiko 3): die Laufzeit-Uhr (fisi_core._boot_clock) laeuft
    mit einem eigenen Versatz ("uhr SEK LAUF"); ohne LAUF laeuft sie mit der
    Geraeteuhr mit (verstrichene Zeit, kein Stellen der Uhr - wie bis 0.62.4
    in allen Tests). "neustart" spielt einen Neustart des Systems nach (neue
    Kennung des Systemstarts und des Prozesses), "ohne_start" ein System ohne
    lesbare Kennung des Systemstarts (Windows, macOS). Fehlt das im Code
    (aeltere Staende), bleiben diese Befehle ohne Wirkung.

Aufruf:  python -I -B abgleich_geraet.py <code-ordner> <api-url> <name>
Danach je Zeile auf stdin ein Befehl als JSON-Liste, z.B. ["lerne", 3, "vorher"];
je Befehl eine JSON-Zeile auf stdout. Befehle:
  lerne N ETIKETT        N Karteikarten "<geraet>-<etikett>-<i>"
  eintrag ETIKETT ZEIT ABSTAND   eine Karte mit vorgegebenem Zeitpunkt (Text)
                         und utc_offset (None = ohne; fehlt die Spalte, ohne)
  namen                  {etikett: anzahl} der Karteikarten
  zaehle                 Zeilen, uids und inhaltlich Doppelte je Tabelle
  meta / setmeta K W     sync_meta lesen / einen Wert setzen
  spalten                Spalten von card_events
  uhr SEK [LAUF]         Geraeteuhr = echte Zeit + SEK; Laufzeit-Uhr = echte
                         Laufzeit + LAUF (ohne LAUF: + SEK)
  neustart [LAUF]        Neustart des Systems nachspielen (Laufzeit-Uhr dann
                         echte Laufzeit + LAUF, ohne LAUF wie bisher)
  ohne_start             keine Kennung des Systemstarts (wie Windows/macOS)
  zeit ISO               Geraeteuhr = dieser Zeitpunkt (UTC, "2026-10-25T00:30:00")
  timeout SEK            fisi_sync.TIMEOUT
  sync                   Abgleich; Meldung, received, sent, removed
  reset_all | clear_history | reset_records     wie die Knoepfe
  sicherung_erstellen PFAD | sicherung_zusammen PFAD | sicherung_ersetzen PFAD
  ende
"""

import sys
sys.dont_write_bytecode = True

import datetime as _real_dt  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import sqlite3  # noqa: E402
import time  # noqa: E402
import types  # noqa: E402
import uuid  # noqa: E402

CODE, API, NAME = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, CODE)

import fisi_core  # noqa: E402
import fisi_sync  # noqa: E402
import fisi_sicherung  # noqa: E402

fisi_sync.API = API.rstrip("/")
OFFSET = [0.0]
LAUF = [0.0]
_HAS_BOOT = hasattr(fisi_core, "_boot_clock")
if _HAS_BOOT:
    _real_boot_clock = fisi_core._boot_clock
    fisi_core._boot_clock = lambda: _real_boot_clock() + LAUF[0]


class _FakeDT(_real_dt.datetime):
    @classmethod
    def now(cls, tz=None):
        # ueber UTC, damit die Ortszeit auch ueber eine Zeitumstellung stimmt
        moment = (_real_dt.datetime.now(_real_dt.timezone.utc)
                  + _real_dt.timedelta(seconds=OFFSET[0]))
        if tz is None:
            return cls._plain(moment.astimezone().replace(tzinfo=None))
        return cls._plain(moment.astimezone(tz))

    @classmethod
    def _plain(cls, value):
        return cls(value.year, value.month, value.day, value.hour, value.minute,
                   value.second, value.microsecond, value.tzinfo)


_shim = types.ModuleType("datetime")
_shim.__dict__.update(_real_dt.__dict__)
_shim.datetime = _FakeDT
for _mod in (fisi_core, fisi_sync, fisi_sicherung):
    _mod.datetime = _shim

fisi_sync.save_sync_settings(sync_repo="pruef/lernstand-attrappe",
                             sync_token="PLATZHALTER-KEIN-ECHTES-TOKEN")
db = fisi_core.DBManager(error_handler=lambda m: sys.stderr.write("DB: %s\n" % m))
TAG = NAME.lower()


def _conn():
    return sqlite3.connect(db.db_path)


def counts():
    conn = _conn()
    try:
        result = {}
        for table, columns in fisi_core.SYNC_TABLES.items():
            n = conn.execute("SELECT COUNT(*) FROM %s" % table).fetchone()[0]
            if not n:
                continue
            u = conn.execute("SELECT COUNT(DISTINCT uid) FROM %s" % table).fetchone()[0]
            data = [c for c in columns if c != "utc_offset"]
            d = conn.execute("SELECT COALESCE(SUM(c - 1), 0) FROM (SELECT COUNT(*) c FROM %s"
                             " GROUP BY %s)" % (table, ", ".join(data))).fetchone()[0]
            result[table] = {"zeilen": n, "uids": u, "doppelt": d}
        return result
    finally:
        conn.close()


def run(name, *args):
    if name == "lerne":
        for i in range(int(args[0])):
            db.log_card("Kat", "%s-%s-%d" % (TAG, args[1], i), "karte", 1)
        return {"ok": True}
    if name == "eintrag":
        conn = _conn()
        try:
            columns = [row[1] for row in conn.execute("PRAGMA table_info(card_events)")]
            if "utc_offset" in columns and args[2] is not None:
                conn.execute("INSERT INTO card_events (timestamp, utc_offset, category, "
                             "question, mode, correct, uid) VALUES (?, ?, ?, ?, ?, ?, ?)",
                             (args[1], int(args[2]), "Kat", "%s-%s-0" % (TAG, args[0]),
                              "karte", 1, uuid.uuid4().hex))
            else:
                conn.execute("INSERT INTO card_events (timestamp, category, question, mode, "
                             "correct, uid) VALUES (?, ?, ?, ?, ?, ?)",
                             (args[1], "Kat", "%s-%s-0" % (TAG, args[0]), "karte", 1,
                              uuid.uuid4().hex))
            conn.commit()
        finally:
            conn.close()
        return {"ok": True}
    if name == "namen":
        conn = _conn()
        try:
            names = [row[0] for row in conn.execute("SELECT question FROM card_events")]
        finally:
            conn.close()
        groups = {}
        for item in names:
            label = item.rsplit("-", 1)[0]
            groups[label] = groups.get(label, 0) + 1
        return {"namen": groups}
    if name == "zaehle":
        return {"tabellen": counts()}
    if name == "meta":
        conn = _conn()
        try:
            return {"meta": dict(conn.execute("SELECT key, value FROM sync_meta"))}
        finally:
            conn.close()
    if name == "setmeta":
        conn = _conn()
        try:
            conn.execute("INSERT OR REPLACE INTO sync_meta (key, value) VALUES (?, ?)",
                         (args[0], args[1]))
            conn.commit()
        finally:
            conn.close()
        return {"ok": True}
    if name == "spalten":
        conn = _conn()
        try:
            return {"spalten": [row[1] for row in conn.execute("PRAGMA table_info(card_events)")]}
        finally:
            conn.close()
    if name == "uhr":
        OFFSET[0] = float(args[0])
        LAUF[0] = float(args[1]) if len(args) > 1 and args[1] is not None else OFFSET[0]
        return {"ok": True}
    if name == "zeit":
        target = _real_dt.datetime.fromisoformat(args[0]).replace(tzinfo=_real_dt.timezone.utc)
        OFFSET[0] = (target - _real_dt.datetime.now(_real_dt.timezone.utc)).total_seconds()
        LAUF[0] = OFFSET[0]
        return {"versatz": OFFSET[0]}
    if name == "neustart":
        if _HAS_BOOT:
            start = uuid.uuid4().hex
            fisi_core._boot_id = lambda: start
            fisi_core.PROCESS_TOKEN = uuid.uuid4().hex
            if args and args[0] is not None:
                LAUF[0] = float(args[0])
        return {"ok": _HAS_BOOT}
    if name == "ohne_start":
        if _HAS_BOOT:
            fisi_core._boot_id = lambda: None
        return {"ok": _HAS_BOOT}
    if name == "timeout":
        fisi_sync.TIMEOUT = float(args[0])
        return {"ok": True}
    if name == "sync":
        try:
            result = fisi_sync.sync(db, device=NAME)
        except fisi_sync.SyncError as error:
            return {"sync": "SyncError", "meldung": str(error)}
        except Exception as error:      # wie die Oberflaeche: "Unerwarteter Fehler"
            return {"sync": "Unerwartet", "meldung": "%s: %s" % (type(error).__name__, error)}
        return {"sync": "ok", "meldung": result.message, "received": result.received,
                "sent": result.sent, "removed": getattr(result, "removed", None),
                "uhr_fix": getattr(db, "last_clock_fix", None)}
    if name in ("reset_all", "clear_history", "reset_records"):
        ok = getattr(db, name)()
        return {"ok": ok, "uhr_fix": getattr(db, "last_clock_fix", None)}
    if name == "sicherung_erstellen":
        with open(args[0], "wb") as handle:
            handle.write(fisi_sicherung.create_backup(db, "test", NAME))
        return {"ok": True}
    if name == "sicherung_zusammen":
        with open(args[0], "rb") as handle:
            backup = fisi_sicherung.read_backup(handle.read())
        n = fisi_sicherung.merge_backup(db, backup, device=NAME)
        return {"meldung": fisi_sicherung.merge_message(n)}
    if name == "sicherung_ersetzen":
        with open(args[0], "rb") as handle:
            backup = fisi_sicherung.read_backup(handle.read())
        fisi_sicherung.replace_all(db, backup, os.path.dirname(db.db_path), "test", NAME)
        return {"ok": True}
    raise ValueError("unbekannter Befehl: %s" % name)


def main():
    print(json.dumps({"bereit": NAME}), flush=True)
    for line in sys.stdin:
        command = json.loads(line)
        if command[0] == "ende":
            break
        try:
            result = run(*command)
        except Exception as error:      # Testfehler sichtbar machen, Geraet laeuft weiter
            result = {"fehler": "%s: %s" % (type(error).__name__, error)}
        result["befehl"] = command[0]
        print(json.dumps(result, ensure_ascii=False), flush=True)
    time.sleep(0)


if __name__ == "__main__":
    main()
