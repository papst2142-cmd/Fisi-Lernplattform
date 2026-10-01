#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FISI Lernplattform - Abgleich zwischen Geraeten
===============================================

Gleicht den Lernfortschritt zwischen PC und Handy ueber ein privates
GitHub-Repository ab. Dort liegt eine einzige Datei (lernstand.json.gz) mit
allen Lern-Eintraegen. Bewusst nur mit der Standardbibliothek, damit PC- und
Handy-App denselben Code nutzen.

Warum das ohne Konflikte klappt: Alle Tabellen sind reine Protokolle ("Karte
gelernt", "Frage beantwortet"), Eintraege kommen nur hinzu. Jeder Eintrag
traegt eine eindeutige Kennung (uid) - zusammengefuehrt wird deshalb einfach
die Vereinigung beider Seiten. Nur Loeschen braucht eine Regel: Der Zeitpunkt
von "Alle Lerndaten loeschen" (reset_at) bzw. "Historie loeschen"
(history_cleared_at) wird mit abgeglichen, und alles davor faellt auf allen
Geraeten weg. Der Spielstand des Lernspiels hat einen eigenen Zeitpunkt
(spiel_reset_at, bis 0.47) und bleibt von den beiden anderen unberuehrt. Ab
0.48 gibt es drei Spielstand-Plaetze: Geloeschte Durchgaenge stehen in der
Tabelle spiel_plaetze und werden auf allen Geraeten entfernt, egal wann. Die
Bestenliste (ab 0.46) uebersteht alle drei, sie hat ihren eigenen Zeitpunkt
(bestenliste_reset_at).

Ablauf:
  ergebnis = sync(db, einstellungen, geraet="PC")   -> SyncResult
"""

import base64
import datetime
import gzip
import json
import sqlite3
import urllib.error
import urllib.request

from fisi_core import (GAME_TABLES, HISTORY_TABLES, OPTIONAL_COLUMNS, PROJECT_TABLES,
                       RECORD_TABLES, SLOT_TABLES, SYNC_TABLES, purge_deleted_runs,
                       apply_question_renames, plural, purge_superseded_project_rows)
from fisi_update import USER_AGENT, _ssl_context, load_settings, save_settings

API = "https://api.github.com"
REMOTE_FILE = "lernstand.json.gz"
# Ab 0.51 kommen neue Tabellen hinzu (Trainer, Pruefungen, Abschlussprojekt) -
# ohne neues Format: Aeltere Versionen (ab 0.48.1) uebergehen unbekannte
# Tabellen einfach, ein Geraet mit 0.51 laedt sie beim naechsten Abgleich
# wieder hoch. So wird niemand ausgesperrt.
# Format 2 (ab 0.48): Spielstand-Plaetze. Aeltere Versionen wuerden die
# Ereignisse aller drei Plaetze in einen Spielstand mischen - sie lehnen eine
# Datei mit hoeherem Format ab ("Bitte zuerst aktualisieren").
FORMAT = 2
MARKERS = ("reset_at", "history_cleared_at", "spiel_reset_at", "bestenliste_reset_at")
TIMEOUT = 15

SETTING_DEFAULTS = {"sync_repo": "", "sync_token": "", "sync_auto": True,
                    "sync_last": ""}


class SyncError(Exception):
    """Fehler beim Abgleich - der Text ist fuer die Anzeige gedacht."""


class _Conflict(Exception):
    """Die Datei wurde zwischen Lesen und Schreiben von einem anderen Geraet
    geaendert - dann einfach noch einmal abgleichen."""


class SyncResult:
    def __init__(self, received, sent):
        self.received = received
        self.sent = sent

    @property
    def message(self):
        if not self.received and not self.sent:
            return "Alles auf dem neuesten Stand."
        parts = []
        if self.received:
            parts.append("%s von anderen Geräten übernommen"
                         % plural(self.received, "Eintrag", "Einträge"))
        if self.sent:
            parts.append("%s hochgeladen" % plural(self.sent, "Eintrag", "Einträge"))
        return ", ".join(parts) + "."


# ============================================================================
#  EINSTELLUNGEN
# ============================================================================

def sync_settings():
    """Einstellungen des Abgleichs (liegen in einstellungen.json)."""
    settings = dict(SETTING_DEFAULTS)
    settings.update(load_settings())
    return settings


def save_sync_settings(**values):
    settings = load_settings()
    settings.update(values)
    return save_settings(settings)


def is_configured(settings=None):
    settings = settings or sync_settings()
    return bool(settings.get("sync_repo", "").strip()
                and settings.get("sync_token", "").strip())


# ============================================================================
#  GITHUB
# ============================================================================

def _request(method, url, token, body=None, accept="application/vnd.github+json"):
    headers = {
        "Authorization": "Bearer " + token,
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": USER_AGENT,
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT,
                                    context=_ssl_context()) as response:
            return response.read()
    except urllib.error.HTTPError:
        raise
    except (urllib.error.URLError, OSError):
        raise SyncError("Keine Verbindung zu GitHub. Bitte die Internetverbindung "
                        "prüfen.")


def _http_error(code, repo):
    if code == 401:
        return "Der Zugangsschlüssel (Token) ist ungültig oder abgelaufen."
    if code == 403:
        return ("Der Zugangsschlüssel darf das Repository %s nicht beschreiben. "
                "Er braucht die Berechtigung „Contents: Read and write“." % repo)
    if code == 404:
        return ("Das Repository %s wurde nicht gefunden oder der "
                "Zugangsschlüssel hat keinen Zugriff darauf." % repo)
    return "GitHub hat die Anfrage abgelehnt (HTTP %d)." % code


def _file_url(repo):
    return "%s/repos/%s/contents/%s" % (API, repo, REMOTE_FILE)


def fetch_remote(repo, token):
    """Liefert (sha, daten) der Datei im Repository oder (None, None), wenn
    es sie noch nicht gibt (erster Abgleich)."""
    url = _file_url(repo)
    try:
        meta = json.loads(_request("GET", url, token).decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise SyncError(_http_error(error.code, repo))
        # 404 heisst entweder "Datei fehlt noch" oder "Repo nicht erreichbar"
        try:
            _request("GET", "%s/repos/%s" % (API, repo), token)
        except urllib.error.HTTPError as repo_error:
            raise SyncError(_http_error(repo_error.code, repo))
        return None, None

    try:
        if meta.get("encoding") == "base64" and meta.get("content"):
            raw = base64.b64decode(meta["content"])
        else:
            # Ab 1 MB liefert GitHub den Inhalt nur noch ueber die Rohdaten
            raw = _request("GET", url, token, accept="application/vnd.github.raw")
        data = json.loads(gzip.decompress(raw).decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise SyncError(_http_error(error.code, repo))
    except (OSError, ValueError, TypeError):
        raise SyncError("Die Datei %s im Repository ist beschädigt." % REMOTE_FILE)
    # Ab 0.53: Eine Datei ohne lesbaren Inhalt ist beschaedigt - nicht "neuer"
    if not isinstance(data, dict) or not isinstance(data.get("format", 0), int):
        raise SyncError("Die Datei %s im Repository ist beschädigt." % REMOTE_FILE)
    if data.get("format", 0) > FORMAT:
        raise SyncError("Der Lernstand im Repository stammt von einer neueren "
                        "Programmversion. Bitte zuerst aktualisieren.")
    return meta.get("sha"), data


def _committer(token):
    """Name und noreply-Adresse des GitHub-Kontos fuer den Commit - so landet
    nie eine private E-Mail-Adresse in der Historie."""
    try:
        user = json.loads(_request("GET", API + "/user", token).decode("utf-8"))
        return {"name": user["login"],
                "email": "%d+%s@users.noreply.github.com" % (user["id"], user["login"])}
    except (urllib.error.HTTPError, SyncError, KeyError, ValueError, TypeError):
        return None


def upload(repo, token, data, sha, device):
    payload = gzip.compress(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        mtime=0)
    body = {
        "message": "Lernstand von %s (%s)" % (
            device or "unbekanntem Gerät",
            datetime.datetime.now().strftime("%d.%m.%Y %H:%M")),
        "content": base64.b64encode(payload).decode("ascii"),
    }
    if sha:
        body["sha"] = sha
    committer = _committer(token)
    if committer:
        body["committer"] = committer
        body["author"] = committer
    try:
        _request("PUT", _file_url(repo), token, body=body)
    except urllib.error.HTTPError as error:
        if error.code in (409, 422):
            raise _Conflict()
        raise SyncError(_http_error(error.code, repo))


# ============================================================================
#  LOKALE DATENBANK
# ============================================================================

def export_local(db):
    """Alle Eintraege der lokalen Datenbank im Austauschformat."""
    conn = sqlite3.connect(db.db_path)
    try:
        tables = {}
        for table, columns in SYNC_TABLES.items():
            rows = conn.execute("SELECT uid, %s FROM %s ORDER BY timestamp, id"
                                % (", ".join(columns), table)).fetchall()
            tables[table] = [list(row) for row in rows]
        markers = {key: value for key, value in
                   conn.execute("SELECT key, value FROM sync_meta")
                   if key in MARKERS and value}
    finally:
        conn.close()
    return {
        "format": FORMAT,
        "columns": {table: list(columns) for table, columns in SYNC_TABLES.items()},
        "markers": markers,
        "tables": tables,
    }


def _later(first, second):
    values = [value for value in (first, second) if value]
    return max(values) if values else None


def _merged_markers(local, remote):
    markers = {}
    for key in MARKERS:
        value = _later(local.get(key), remote.get(key))
        if value:
            markers[key] = value
    return markers


def merge_into_local(db, remote):
    """Uebernimmt fehlende Eintraege und Loeschzeitpunkte aus remote in die
    lokale Datenbank. Liefert die Zahl der neu uebernommenen Eintraege."""
    local_markers = export_local(db)["markers"]
    markers = _merged_markers(local_markers, remote.get("markers") or {})
    reset = markers.get("reset_at")
    cleared = _later(reset, markers.get("history_cleared_at"))
    game_reset = markers.get("spiel_reset_at")
    remote_columns = remote.get("columns") or {}
    remote_tables = remote.get("tables") or {}

    received = 0
    conn = sqlite3.connect(db.db_path)
    try:
        cur = conn.cursor()
        for key, value in markers.items():
            cur.execute("INSERT OR REPLACE INTO sync_meta (key, value) VALUES (?, ?)",
                        (key, value))
        for table, columns in SYNC_TABLES.items():
            if table in SLOT_TABLES or table in PROJECT_TABLES:
                cutoff = None     # Platz-Zeilen und Abschlussprojekt bleiben
            elif table in GAME_TABLES:
                cutoff = game_reset
            elif table in RECORD_TABLES:
                cutoff = markers.get("bestenliste_reset_at")
            elif table in HISTORY_TABLES:
                cutoff = cleared
            else:
                cutoff = reset
            if cutoff:
                cur.execute("DELETE FROM %s WHERE timestamp <= ?" % table, (cutoff,))
            names = ["uid"] + list(remote_columns.get(table) or columns)
            sql = "INSERT OR IGNORE INTO %s (uid, %s) VALUES (%s)" % (
                table, ", ".join(columns), ", ".join("?" * (len(columns) + 1)))
            optional = OPTIONAL_COLUMNS.get(table, ())
            for row in remote_tables.get(table) or []:
                record = dict(zip(names, row))
                # Eintraege aelterer Versionen haben spaeter dazugekommene
                # Spalten noch nicht - die bleiben dann leer
                for column in optional:
                    record.setdefault(column, None)
                if not record.get("uid") or any(c not in record for c in columns):
                    continue
                if cutoff and str(record["timestamp"]) <= cutoff:
                    continue
                cur.execute(sql, [record["uid"]] + [record[c] for c in columns])
                received += cur.rowcount
        # Geloeschte Durchgaenge (ab 0.48) verschwinden, auch wenn ihre
        # Ereignisse gerade erst von einem anderen Geraet kamen
        purge_deleted_runs(cur)
        # Abschlussprojekt (ab 0.51): nur die neueste Fassung je Feld behalten
        purge_superseded_project_rows(cur)
        # Ab 0.53: Antworten von Geraeten mit aelterer Version koennen noch
        # alte Fragetexte tragen - sie zaehlen beim neuen Text
        apply_question_renames(cur)
        conn.commit()
    finally:
        conn.close()
    return received


def _uids(data):
    return {table: {row[0] for row in rows}
            for table, rows in (data.get("tables") or {}).items()}


# ============================================================================
#  ABGLEICH
# ============================================================================

def sync(db, settings=None, device=""):
    """Gleicht die lokale Datenbank mit dem Repository ab (in beide
    Richtungen). Wirft SyncError mit einem anzeigbaren Text."""
    settings = settings or sync_settings()
    repo = settings.get("sync_repo", "").strip().strip("/")
    token = settings.get("sync_token", "").strip()
    if not repo or not token:
        raise SyncError("Der Abgleich ist noch nicht eingerichtet.")
    if repo.count("/") != 1:
        raise SyncError("Das Repository bitte als „Benutzer/Name“ angeben, "
                        "z.B. papst2142-cmd/fisi-lernstand.")

    received = 0
    for _attempt in range(3):
        sha, remote = fetch_remote(repo, token)
        if remote:
            received += merge_into_local(db, remote)
        local = export_local(db)
        remote_uids = _uids(remote) if remote else {}
        local_uids = _uids(local)
        if remote and local_uids == remote_uids and \
                local["markers"] == (remote.get("markers") or {}):
            result = SyncResult(received, 0)
            break
        sent = sum(len(uids - remote_uids.get(table, set()))
                   for table, uids in local_uids.items())
        try:
            upload(repo, token, local, sha, device)
        except _Conflict:
            continue
        result = SyncResult(received, sent)
        break
    else:
        raise SyncError("Ein anderes Gerät hat gleichzeitig abgeglichen. Bitte "
                        "gleich noch einmal versuchen.")

    save_sync_settings(sync_last=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    return result
