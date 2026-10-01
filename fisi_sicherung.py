#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FISI Lernplattform - Sicherung und Wiederherstellung
====================================================

Speichert den gesamten Lernstand in einer Datei (*.fisisicherung) und spielt
ihn wieder ein - ohne GitHub, z.B. vor einem Handywechsel. Bewusst ohne
Oberflaeche und nur mit der Standardbibliothek, damit PC- und Handy-App
denselben Code nutzen.

Die Datei ist gzip-gepacktes JSON. Die Lern-Eintraege stehen darin genau im
Austauschformat des Abgleichs (fisi_sync.export_local), samt uid und
Loeschzeitpunkten. Darum funktioniert "Zusammenfuehren" wie ein Abgleich:
Es kommt nur hinzu, was fehlt, doppelt wird nichts. "Alles ersetzen" stellt
genau den Stand der Sicherung her (vorher landet eine Sicherheitskopie des
jetzigen Stands neben der Datenbank).

Von den Einstellungen kommt nur das Tagesziel mit (GOAL_SETTINGS). Token,
Repository, Farben usw. bleiben auf dem Geraet und stehen nie in der Datei.

Ablauf:
  daten = create_backup(db, "0.52", geraet="PC")   -> bytes zum Speichern
  sicherung = read_backup(daten)                   -> dict oder BackupError
  zeilen = backup_summary(sicherung)["zeilen"]     -> Vorschau
  neu = merge_backup(db, sicherung)                -> Zusammenfuehren
  pfad = replace_all(db, sicherung, ordner)        -> Alles ersetzen
"""

import datetime
import gzip
import hashlib
import json
import os
import sqlite3
import uuid
import zlib

from fisi_core import (EVENT_TABLES, LEGACY_RUN, OPTIONAL_COLUMNS, SYNC_TABLES,
                       purge_deleted_runs)
from fisi_lernen import GOAL_SETTINGS, goal_settings
from fisi_sync import FORMAT as SYNC_FORMAT, MARKERS, export_local, merge_into_local
from fisi_update import load_settings, save_settings

BACKUP_EXT = ".fisisicherung"
FORMAT_VERSION = 1
KIND = "FISI-Sicherung"
SAFETY_PREFIX = "vor_wiederherstellung_"

# Spielstand-Plaetze wie in fisi_game (SLOT_COUNT, Aktionen der Tabelle
# spiel_plaetze) - hier nachgebildet, damit dieses Modul das grosse Spiel-
# Modul nicht laden muss. test_sicherung.py prueft, dass beides passt.
SLOT_COUNT = 3
SLOT_CREATED = "angelegt"
SLOT_DELETED = "geloescht"
SLOT_RENAMED = "umbenannt"
SLOT_NAME_MAX = 24
FALLBACK_NAME = "Spielstand"
# Bestenliste: Zeilen dieser Art sind erreichte Abzeichen-Stufen
BADGE_KIND = "erfolg"

# Texte (PC und Handy gleich)
TITLE = "Sicherung"
SUBTITLE = "Lernstand als Datei"
HELP = ("Speichert den gesamten Lernstand in einer Datei: Lernfortschritt, Prüfungen, "
        "Abschlussprojekt, Spielstände, Bestenliste und das Tagesziel. Mit „Sicherung "
        "einspielen“ holst du ihn zurück, auch auf einem anderen Gerät. "
        "Zugangsschlüssel und Farben kommen nicht mit in die Datei.")
BTN_CREATE = "Sicherung erstellen"
BTN_RESTORE = "Sicherung einspielen"
BTN_MERGE = "Zusammenführen"
BTN_REPLACE = "Alles ersetzen"
BTN_CANCEL = "Abbrechen"
FILE_TYPE = "FISI-Sicherung"
PREVIEW_HINT = ("Zusammenführen übernimmt alles, was auf diesem Gerät noch fehlt – "
                "nichts geht verloren, doppelt wird nichts. Alles ersetzen stellt genau "
                "den Stand der Sicherung her.")
DELETED_TITLE = "Gelöschter Spielstand"
REPLACE_TITLE = "Alles ersetzen"
REPLACE_CONFIRM_TITLE = "Wirklich ersetzen?"
REPLACE_CONFIRM = ("Letzte Rückfrage: Den Lernstand dieses Geräts jetzt durch die "
                   "Sicherung ersetzen?")
ERROR_TITLE = "Sicherung einspielen"
SAVE_ERROR_TITLE = "Speichern fehlgeschlagen"

MSG_NOT_BACKUP = "Diese Datei ist keine FISI-Sicherung."
MSG_DAMAGED = "Die Sicherung ist beschädigt (Prüfsumme stimmt nicht)."
MSG_NEWER = "Die Sicherung stammt aus Version %s. Bitte zuerst die App aktualisieren."
MSG_SLOTS_FULL = ("Alle %d Spielstand-Plätze sind belegt. Lösche zuerst einen Platz, "
                  "dann kannst du den Spielstand wiederherstellen." % SLOT_COUNT)


class BackupError(Exception):
    """Fehler beim Lesen oder Einspielen - der Text ist fuer die Anzeige gedacht."""


# ============================================================================
#  HILFEN
# ============================================================================

def _now():
    return datetime.datetime.now()


def default_name(now=None):
    """Vorschlag fuer den Dateinamen, z.B. FISI-Sicherung_2026-10-01_1423.fisisicherung."""
    return "FISI-Sicherung_%s%s" % ((now or _now()).strftime("%Y-%m-%d_%H%M"), BACKUP_EXT)


def _checksum(data, settings):
    """SHA-256 ueber eine feste Schreibweise von Daten und Einstellungen."""
    text = json.dumps({"daten": data, "einstellungen": settings}, sort_keys=True,
                      separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _goal_values(settings):
    """Nur die Tagesziel-Schluessel (mit gueltigen Werten)."""
    return {key: value for key, value in goal_settings(settings or {}).items()
            if key in GOAL_SETTINGS}


def _records(data, table):
    """Zeilen einer Tabelle aus dem Austauschformat als dicts (mit uid).
    Zeilen aelterer Formate ohne spaeter dazugekommene Spalten bekommen sie
    leer; unvollstaendige Zeilen fallen weg (wie beim Abgleich)."""
    columns = SYNC_TABLES[table]
    names = ["uid"] + list(((data.get("columns") or {}).get(table)) or columns)
    optional = OPTIONAL_COLUMNS.get(table, ())
    result = []
    for row in (data.get("tables") or {}).get(table) or []:
        record = dict(zip(names, row))
        for column in optional:
            record.setdefault(column, None)
        if record.get("uid") and all(column in record for column in columns):
            result.append(record)
    return result


def _run_key(lauf):
    """Durchgang eines Spielereignisses (ohne lauf: der alte Durchgang)."""
    return lauf or LEGACY_RUN


def _slot_payload(record):
    try:
        payload = json.loads(record.get("daten") or "{}")
    except (TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _slot_state(rows, legacy):
    """Belegung der Plaetze wie fisi_game.slot_layout: ({platz: lauf},
    {platz: name}). rows: dicts der Tabelle spiel_plaetze."""
    rows = sorted(rows, key=lambda r: (str(r["timestamp"]), str(r["uid"])))
    deleted = {r["lauf"] for r in rows if r["aktion"] == SLOT_DELETED}
    created, seen, names = [], set(), {}
    if legacy:
        created.append(LEGACY_RUN)
        seen.add(LEGACY_RUN)
    for record in rows:
        slot = int(record["platz"] or 0)
        if record["aktion"] == SLOT_CREATED and record["lauf"] and \
                record["lauf"] not in seen:
            seen.add(record["lauf"])
            created.append((slot, record["lauf"]))
        elif record["aktion"] == SLOT_RENAMED and 1 <= slot <= SLOT_COUNT:
            names[slot] = str(_slot_payload(record).get("name") or "").strip()[:SLOT_NAME_MAX]
    slots = {}
    for item in created:
        slot, run = (1, item) if item == LEGACY_RUN else item
        if run in deleted:
            continue
        if not (1 <= slot <= SLOT_COUNT and slot not in slots):
            free = [n for n in range(1, SLOT_COUNT + 1) if n not in slots]
            if not free:
                continue
            slot = free[0]
        slots[slot] = run
    return slots, {slot: name for slot, name in names.items() if name}


def _run_name(slot_rows, run):
    """Name, den ein Durchgang in der Sicherung trug: die letzte Umbenennung
    seines Platzes nach dem Anlegen (und vor dem naechsten Durchgang dort)."""
    rows = sorted(slot_rows, key=lambda r: (str(r["timestamp"]), str(r["uid"])))
    slot, start = (1, "") if run == LEGACY_RUN else (None, None)
    for record in rows:
        if record["aktion"] == SLOT_CREATED and record["lauf"] == run:
            slot, start = int(record["platz"] or 0), str(record["timestamp"])
            break
    if slot is None:
        return FALLBACK_NAME
    name = ""
    for record in rows:
        stamp = str(record["timestamp"])
        if stamp <= start or int(record["platz"] or 0) != slot:
            continue
        if record["aktion"] == SLOT_CREATED and record["lauf"] != run:
            break
        if record["aktion"] == SLOT_DELETED and record["lauf"] == run:
            break
        if record["aktion"] == SLOT_RENAMED:
            name = str(_slot_payload(record).get("name") or "").strip()[:SLOT_NAME_MAX]
    return name or FALLBACK_NAME


def _local_slot_rows(db):
    return [{"timestamp": t, "uid": u, "platz": s, "lauf": r, "aktion": a,
             "daten": json.dumps(d)} for t, u, s, r, a, d in db.slot_rows()]


def _summary_counts(data):
    events = sum(len((data.get("tables") or {}).get(table) or [])
                 for table in EVENT_TABLES)
    slot_rows = _records(data, "spiel_plaetze")
    deleted = {r["lauf"] for r in slot_rows if r["aktion"] == SLOT_DELETED}
    runs = {r["lauf"] for r in slot_rows if r["aktion"] == SLOT_CREATED and r["lauf"]}
    runs |= {_run_key(r["lauf"]) for r in _records(data, "spiel_ereignisse")}
    badges = sum(1 for r in _records(data, "spiel_bestenliste") if r["art"] == BADGE_KIND)
    projects = {r["projekt"] for r in _records(data, "abschlussprojekt") if r["projekt"]}
    return {"lerneintraege": events, "spielstaende": len(runs - deleted),
            "abzeichen": badges, "projekte": len(projects)}


# ============================================================================
#  ERSTELLEN UND LESEN
# ============================================================================

def create_backup(db, app_version, device=""):
    """Der gesamte Lernstand als Sicherungsdatei (bytes)."""
    data = export_local(db)
    settings = _goal_values(load_settings())
    backup = {
        "art": KIND,
        "formatversion": FORMAT_VERSION,
        "app_version": str(app_version or ""),
        "erstellt": _now().isoformat(timespec="seconds"),
        "geraet": device or "",
        "daten": data,
        "einstellungen": settings,
        "zusammenfassung": _summary_counts(data),
        "pruefsumme": _checksum(data, settings),
    }
    return gzip.compress(json.dumps(backup, ensure_ascii=False,
                                    separators=(",", ":")).encode("utf-8"))


def read_backup(raw_bytes):
    """Prueft eine Sicherungsdatei, bevor irgendetwas geschrieben wird.
    Liefert das dict der Sicherung oder wirft BackupError."""
    try:
        backup = json.loads(gzip.decompress(raw_bytes).decode("utf-8"))
    except (OSError, EOFError, zlib.error, TypeError, ValueError):
        raise BackupError(MSG_NOT_BACKUP)
    if not isinstance(backup, dict) or backup.get("art") != KIND:
        raise BackupError(MSG_NOT_BACKUP)
    data = backup.get("daten")
    try:
        version = int(backup.get("formatversion", 0))
        sync_format = int(data.get("format", 0)) if isinstance(data, dict) else 0
    except (TypeError, ValueError):
        raise BackupError(MSG_NOT_BACKUP)
    # Erst die Version: eine neuere App koennte die Pruefsumme anders bilden
    if version > FORMAT_VERSION or sync_format > SYNC_FORMAT:
        raise BackupError(MSG_NEWER % (backup.get("app_version") or "?"))
    settings = backup.get("einstellungen")
    if backup.get("pruefsumme") != _checksum(data, settings):
        raise BackupError(MSG_DAMAGED)
    if not isinstance(data, dict) or not isinstance(data.get("tables"), dict) or \
            not isinstance(settings, dict):
        raise BackupError(MSG_NOT_BACKUP)
    return backup


def _german_number(number):
    return "{:,}".format(number).replace(",", ".")


def _german_created(text):
    try:
        moment = datetime.datetime.fromisoformat(str(text))
    except ValueError:
        return str(text or "?")
    return moment.strftime("%d.%m.%Y, %H:%M Uhr")


def backup_summary(backup):
    """Vorschau vor dem Einspielen: dict mit Zahlen und "zeilen" (Text)."""
    counts = _summary_counts(backup.get("daten") or {})
    summary = dict(counts)
    summary.update({"erstellt": _german_created(backup.get("erstellt")),
                    "version": backup.get("app_version") or "?",
                    "geraet": backup.get("geraet") or ""})
    lines = ["Erstellt: %s" % summary["erstellt"],
             "App-Version: %s" % summary["version"]]
    if summary["geraet"]:
        lines.append("Gerät: %s" % summary["geraet"])
    lines += ["Lern-Einträge: %s" % _german_number(counts["lerneintraege"]),
              "Spielstände: %d" % counts["spielstaende"],
              "Abzeichen: %d" % counts["abzeichen"],
              "Abschlussprojekte: %d" % counts["projekte"]]
    summary["zeilen"] = lines
    return summary


def preview_text(backup):
    """Text des Vorschau-Dialogs (PC und Handy gleich)."""
    return "\n".join(backup_summary(backup)["zeilen"]) + "\n\n" + PREVIEW_HINT


# ============================================================================
#  ZUSAMMENFUEHREN
# ============================================================================

def deleted_runs(db, backup):
    """Durchgaenge mit Ereignissen in der Sicherung, die auf diesem Geraet
    geloescht sind. Beim Zusammenfuehren blieben sie still geloescht (siehe
    purge_deleted_runs) - die Oberflaeche fragt deshalb nach.
    Zurueck: [{"lauf", "name", "ereignisse"}] nach dem ersten Ereignis."""
    local_deleted = {run for _t, _u, _s, run, action, _d in db.slot_rows()
                     if action == SLOT_DELETED}
    data = backup.get("daten") or {}
    counts, first = {}, {}
    for record in _records(data, "spiel_ereignisse"):
        run = _run_key(record["lauf"])
        if run in local_deleted:
            counts[run] = counts.get(run, 0) + 1
            first.setdefault(run, str(record["timestamp"]))
    slot_rows = _records(data, "spiel_plaetze")
    return [{"lauf": run, "name": _run_name(slot_rows, run), "ereignisse": counts[run]}
            for run in sorted(counts, key=lambda r: (first[r], r))]


def deleted_question(runs):
    """Rueckfrage zu geloeschten Spielstaenden (PC und Handy gleich)."""
    names = "“, „".join(item["name"] for item in runs)
    if len(runs) == 1:
        return ("Die Sicherung enthält %d gelöschten Spielstand („%s“). Als neuen Platz "
                "wiederherstellen?" % (len(runs), names))
    return ("Die Sicherung enthält %d gelöschte Spielstände („%s“). Als neue Plätze "
            "wiederherstellen?" % (len(runs), names))


def _free_slots_after_merge(db, backup):
    """Freie Plaetze, wie sie nach dem Zusammenfuehren waeren, und die Namen
    der Plaetze - ohne etwas zu schreiben."""
    rows = {r["uid"]: r for r in _local_slot_rows(db)}
    data = backup.get("daten") or {}
    for record in _records(data, "spiel_plaetze"):
        rows.setdefault(record["uid"], record)
    legacy = db.has_legacy_events() or any(
        not record["lauf"] for record in _records(data, "spiel_ereignisse"))
    slots, names = _slot_state(list(rows.values()), legacy)
    return [n for n in range(1, SLOT_COUNT + 1) if n not in slots], names


def _uid_set(db):
    """Alle (Tabelle, uid) der lokalen Datenbank."""
    conn = sqlite3.connect(db.db_path)
    try:
        return {(table, row[0]) for table in SYNC_TABLES
                for row in conn.execute("SELECT uid FROM " + table)}
    finally:
        conn.close()


def merge_backup(db, backup, restore_runs=(), device=""):
    """Fuehrt die Sicherung mit dem Lernstand dieses Geraets zusammen (wie ein
    Abgleich: nichts geht verloren, doppelte Eintraege erkennt die uid). Die
    Tagesziel-Einstellungen dieses Geraets bleiben unberuehrt.

    restore_runs: Durchgaenge aus deleted_runs, die als neuer Spielstand auf
    einen freien Platz zurueckkommen - mit neuer Kennung (lauf) und neuen
    uids, damit die alte Loeschung sie nicht wieder entfernt (auch nicht auf
    den anderen Geraeten). Reichen die freien Plaetze nicht, kommt BackupError,
    bevor irgendetwas geschrieben ist.
    Zurueck: Zahl der neu uebernommenen Eintraege (gezaehlt wird, was danach
    wirklich da ist - Ereignisse geloeschter Durchgaenge zaehlen nicht mit)."""
    restore_runs = [run for run in restore_runs if run]
    data = backup.get("daten") or {}
    free, names = _free_slots_after_merge(db, backup) if restore_runs else ([], {})
    if len(free) < len(restore_runs):
        raise BackupError(MSG_SLOTS_FULL)
    before = _uid_set(db)
    merge_into_local(db, data)
    if not restore_runs:
        return len(_uid_set(db) - before)

    events = _records(data, "spiel_ereignisse")
    slot_rows = _records(data, "spiel_plaetze")
    conn = sqlite3.connect(db.db_path)
    try:
        cur = conn.cursor()
        for run, slot in zip(restore_runs, free):
            new_run = "l" + uuid.uuid4().hex[:16]        # wie fisi_game.Game.new_run
            name = _run_name(slot_rows, run)
            custom = "" if name == FALLBACK_NAME else name
            stamp = _now().strftime("%Y-%m-%d %H:%M:%S.%f")
            cur.execute("INSERT INTO spiel_plaetze (timestamp, platz, lauf, aktion, daten,"
                        " geraet, uid) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (stamp, slot, new_run, SLOT_CREATED,
                         json.dumps({"name": name}, ensure_ascii=False), device or "",
                         uuid.uuid4().hex))
            # Der Platz traegt wieder den alten Namen (und keinen fremden)
            if custom or names.get(slot):
                cur.execute("INSERT INTO spiel_plaetze (timestamp, platz, lauf, aktion,"
                            " daten, geraet, uid) VALUES (?, ?, '', ?, ?, ?, ?)",
                            (stamp, slot, SLOT_RENAMED,
                             json.dumps({"name": custom}, ensure_ascii=False),
                             device or "", uuid.uuid4().hex))
            for record in events:
                if _run_key(record["lauf"]) != run:
                    continue
                cur.execute("INSERT INTO spiel_ereignisse (timestamp, typ, daten, geraet,"
                            " uid, lauf) VALUES (?, ?, ?, ?, ?, ?)",
                            (record["timestamp"], record["typ"], record["daten"],
                             record["geraet"], uuid.uuid4().hex, new_run))
        purge_deleted_runs(cur)
        conn.commit()
    finally:
        conn.close()
    return len(_uid_set(db) - before)


def merge_message(count, restored=()):
    """Rueckmeldung nach dem Zusammenfuehren (PC und Handy gleich)."""
    if count:
        text = "Sicherung eingespielt: %s Einträge übernommen." % _german_number(count)
    else:
        text = "Sicherung eingespielt: Es fehlte nichts, alles war schon da."
    for name in restored:
        text += " Der Spielstand „%s“ liegt wieder auf einem freien Platz." % name
    return text


# ============================================================================
#  ALLES ERSETZEN
# ============================================================================

def replace_question(backup):
    """Warnung vor "Alles ersetzen" (PC und Handy gleich)."""
    return ("Der komplette Lernstand dieses Geräts – Lernfortschritt, Prüfungen, "
            "Abschlussprojekt, Spielstände und Bestenliste – wird durch die Sicherung "
            "vom %s ersetzt. Das Tagesziel kommt ebenfalls aus der Sicherung. Vorher wird "
            "der jetzige Stand als Sicherheitskopie neben der Datenbank gespeichert.\n\n"
            "Mit eingerichtetem Abgleich kommen beim nächsten Abgleich die Daten aus dem "
            "Repository wieder dazu, und Löschungen anderer Geräte gelten weiterhin."
            % backup_summary(backup)["erstellt"])


def _safety_path(folder):
    base = SAFETY_PREFIX + _now().strftime("%Y-%m-%d_%H%M")
    path = os.path.join(folder, base + BACKUP_EXT)
    number = 2
    while os.path.exists(path):      # zweimal in einer Minute: nichts ueberschreiben
        path = os.path.join(folder, "%s_%d%s" % (base, number, BACKUP_EXT))
        number += 1
    return path


def replace_all(db, backup, safety_dir, app_version="", device=""):
    """Ersetzt den gesamten Lernstand durch die Sicherung: dieselben Eintraege
    mit derselben uid, dieselben Loeschzeitpunkte, dazu das Tagesziel. Vorher
    kommt der jetzige Stand als Sicherheitskopie nach safety_dir (Pfad ist
    der Rueckgabewert). Geraetebezogenes (aktiver Platz, Farben, Token)
    bleibt. Die Tabellen zaehlen ihre Nummern weiter (AUTOINCREMENT) - so
    sehen change_stamp und game_event_stamp die Aenderung auf jeden Fall."""
    os.makedirs(safety_dir, exist_ok=True)
    path = _safety_path(safety_dir)
    safety = create_backup(db, app_version, device)
    try:
        with open(path, "wb") as handle:
            handle.write(safety)
    except OSError as error:
        raise BackupError("Die Sicherheitskopie ließ sich nicht speichern: %s" % error)

    data = backup.get("daten") or {}
    markers = {key: value for key, value in (data.get("markers") or {}).items()
               if key in MARKERS and value}
    conn = sqlite3.connect(db.db_path)
    try:
        cur = conn.cursor()
        for table, columns in SYNC_TABLES.items():
            cur.execute("DELETE FROM " + table)
            sql = "INSERT OR IGNORE INTO %s (uid, %s) VALUES (%s)" % (
                table, ", ".join(columns), ", ".join("?" * (len(columns) + 1)))
            for record in _records(data, table):
                cur.execute(sql, [record["uid"]] + [record[c] for c in columns])
        cur.execute("DELETE FROM sync_meta WHERE key IN (%s)" % ", ".join("?" * len(MARKERS)),
                    MARKERS)
        for key, value in markers.items():
            cur.execute("INSERT INTO sync_meta (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
    except sqlite3.Error as error:
        conn.rollback()
        raise BackupError("Die Sicherung ließ sich nicht einspielen: %s" % error)
    finally:
        conn.close()

    settings = load_settings()
    settings.update(_goal_values(backup.get("einstellungen")))
    save_settings(settings)
    return path


def replace_message(backup, safety_path):
    """Rueckmeldung nach "Alles ersetzen" (PC und Handy gleich)."""
    return ("Sicherung eingespielt: Der Lernstand entspricht jetzt der Sicherung vom %s. "
            "Sicherheitskopie des vorherigen Stands: %s"
            % (backup_summary(backup)["erstellt"], os.path.basename(safety_path)))
