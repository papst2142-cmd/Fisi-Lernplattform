#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fachinformatiker Lernplattform - Abgleich zwischen Geraeten
===========================================================

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

Ab 0.62.4 tragen Loeschzeitpunkte und Eintraege ihren Abstand zu UTC (Marke
"2026-10-25 02:30:00+02:00", Spalte utc_offset). Dann wird ueber Zeitzonen und
die Zeitumstellung hinweg in UTC verglichen; ohne Abstand (aeltere Versionen)
bleibt es beim Textvergleich wie bisher. Eine Marke, die nach der Uhrzeit von
GitHub in der Zukunft liegt (falsche Geraeteuhr), wird einmal auf diese
Uhrzeit gesetzt - aber nur, wenn zuletzt ein Geraet ab 0.62.4 die Datei
geschrieben hat (Feld "schreiber"), sonst wuerde ein aelteres Geraet die
alte Marke immer wieder hochladen. Ungueltige Marken gelten nicht.

Ablauf:
  ergebnis = sync(db, einstellungen, geraet="PC")   -> SyncResult
"""

import base64
import datetime
import email.utils
import gzip
import http.client
import json
import re
import socket
import sqlite3
import threading
import urllib.error
import urllib.parse
import urllib.request

from fisi_core import (CLOCK_KEY, CLOCK_TOLERANCE, CLOCK_VALID, GAME_TABLES,
                       HISTORY_TABLES, MARKED_TABLES, OPTIONAL_COLUMNS, PROJECT_TABLES,
                       RECORD_TABLES, SLOT_TABLES, SYNC_TABLES, UTC_OFFSET,
                       purge_deleted_runs, apply_question_renames,
                       clock_deviation, clock_measurement, device_now, format_with_zone,
                       offset_minutes, plural, purge_superseded_project_rows, write_error_log)
from fisi_core import DB_READ_ONLY_LINES
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
# Ab 0.62.4: Feld in der Datei - zuletzt hat ein Geraet geschrieben, das
# Marken mit Zone versteht. Aeltere Versionen lassen es beim Hochladen weg.
WRITER_KEY = "schreiber"
WRITER = "0.62.4"
# Ab 0.62.4: Feld in der Datei - welche Zukunftsmarke auf welche Uhrzeit von
# GitHub gesetzt wurde ({"reset_at": [alt, neu]}). Ein Geraet, das die alte
# Marke noch hat, nimmt dann dasselbe neu, statt selbst eine Uhrzeit zu
# waehlen. Lokal steht es in sync_meta unter CLAMP_PREFIX + Schluessel.
CLAMP_KEY = "gekappt"
CLAMP_PREFIX = "gekappt:"
# Ab 0.62.4: Feld in der Datei und Schluessel in sync_meta - wann (UTC) zuletzt
# eine Datei gesehen wurde, die ein Geraet vor 0.62.4 geschrieben hat. So
# lange danach MIXED_HOLD nicht vorbei ist, setzt kein neues Geraet eine
# Zukunftsmarke aus der Datei auf die Uhrzeit von GitHub: Ein altes Geraet
# kann sie schon haben, naehme sie immer wieder, und beide luden abwechselnd
# hoch (Gegenpruefung A-9, F2).
MIXED_KEY = "mischbetrieb"
MIXED_HOLD = 7 * 86400
# Gueltige Marke: Ortszeit, optional Mikrosekunden und Abstand zu UTC
_MARKER_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(\.\d{1,6})?"
                        r"(?:([+-])(\d{2}):(\d{2}))?$")
MSG_INVALID_MARKER = ("Die Abgleich-Datei enthält eine ungültige Löschmarke. Sie wurde "
                      "nicht angewendet.")
MSG_FUTURE_MARKER = ("Eine Löschmarke lag in der Zukunft (falsche Uhr) und wurde auf die "
                     "Uhrzeit von GitHub gesetzt.")
MSG_FUTURE_BACKUP = ("Die Sicherung enthält eine Löschmarke in der Zukunft. Sie wurde "
                     "nicht angewendet.")
# Ab 0.62.5 (B-G-27): abgebrochene oder fremde Antwort (z.B. Seite eines
# Proxys oder Virenscanners) statt "Unerwarteter Fehler: IncompleteRead ..."
MSG_INCOMPLETE = "Die Antwort von GitHub war unvollständig. Bitte später noch einmal."
# Ab 0.62.5 (B-G-28): GitHub lehnt das Hochladen auch nach drei Versuchen mit
# 422 ab - nicht "gleichzeitig abgeglichen"
MSG_UPLOAD_REJECTED = ("GitHub hat das Hochladen des Lernstands abgelehnt (HTTP 422). "
                       "Der Lernstand auf diesem Gerät bleibt erhalten.")

# Ab 0.62.5 (Gegenpruefung M-1, B-G-06): Wird nichts mehr gespeichert
# (DBManager.read_only_reason, z.B. beschaedigte Datenbank), schreibt auch
# der Abgleich nicht - %s ist die rote Zeile aus DB_READ_ONLY_LINES
MSG_READ_ONLY = "Der Abgleich ist ausgesetzt. %s"

SETTING_DEFAULTS = {"sync_repo": "", "sync_token": "", "sync_auto": True,
                    "sync_last": ""}


class SyncError(Exception):
    """Fehler beim Abgleich - der Text ist fuer die Anzeige gedacht."""


class _Conflict(Exception):
    """Die Datei wurde zwischen Lesen und Schreiben von einem anderen Geraet
    geaendert - dann einfach noch einmal abgleichen. code: HTTP-Code (ab
    0.62.5, B-G-28)."""

    def __init__(self, code=409):
        Exception.__init__(self, code)
        self.code = code


class SyncResult:
    def __init__(self, received, sent, removed=0, notes=()):
        self.received = received
        self.sent = sent
        self.removed = removed          # ab 0.62.4: wegen einer Loeschung entfernt
        self.notes = list(notes)        # ab 0.62.4: Hinweise zu Marken

    @property
    def message(self):
        if not self.received and not self.sent and not self.removed:
            text = "Alles auf dem neuesten Stand."
        else:
            parts = []
            if self.received:
                parts.append("%s von anderen Geräten übernommen"
                             % plural(self.received, "Eintrag", "Einträge"))
            if self.sent:
                parts.append("%s hochgeladen" % plural(self.sent, "Eintrag", "Einträge"))
            if self.removed:
                parts.append(removed_text(self.removed))
            text = ", ".join(parts) + "."
        return " ".join([text] + self.notes)


def refuse_read_only(db, message=MSG_READ_ONLY, error=SyncError):
    """Ab 0.62.5 (Gegenpruefung M-1): Wirft error(message), wenn die
    Datenbank nur gelesen werden darf (read_only_reason) - dann darf weder
    der Abgleich noch die Sicherung hineinschreiben."""
    reason = getattr(db, "read_only_reason", None)
    if reason:
        raise error((message % DB_READ_ONLY_LINES.get(reason, "")).strip())


def removed_text(count):
    """'3 Einträge wegen einer Löschung entfernt' (PC, Handy, Sicherung)."""
    return "%s wegen einer Löschung entfernt" % plural(count, "Eintrag", "Einträge")


def clock_fix_text(seconds):
    """Hinweis nach einer Loeschung, wenn die Marke mit der Uhrzeit von GitHub
    statt der falschen Geraeteuhr gespeichert wurde (ab 0.62.4, PC und Handy
    gleich). seconds = Geraeteuhr minus GitHub; 0 = kein Hinweis."""
    if not seconds:
        return ""
    size = abs(seconds)
    if size >= 86400:
        amount = plural(int(round(size / 86400.0)), "Tag", "Tage")
    elif size >= 3600:
        amount = plural(int(round(size / 3600.0)), "Stunde", "Stunden")
    else:
        amount = plural(max(1, int(round(size / 60.0))), "Minute", "Minuten")
    return ("Die Uhr dieses Geräts geht um %s %s. Die Löschung wurde mit der "
            "Uhrzeit von GitHub gespeichert." % (amount, "vor" if seconds > 0 else "nach"))


class MergeStats:
    """Was beim Zusammenfuehren wegen Loeschmarken passiert ist (ab 0.62.4)."""

    def __init__(self):
        self.gone = set()       # (Tabelle, uid): lokal geloescht oder nicht uebernommen
        self.invalid = 0        # ungueltige Marken (nicht angewendet)
        self.future = 0         # Zukunftsmarken (Sicherung: nicht angewendet)
        self.backup = False     # Zusammenfuehren einer Sicherung (ohne GitHub-Uhr)

    @property
    def removed(self):
        return len(self.gone)

    def notes(self, backup=False):
        notes = []
        if self.invalid:
            notes.append(MSG_INVALID_MARKER)
        if self.future and backup:
            notes.append(MSG_FUTURE_BACKUP)
        return notes


# Ergebnis des letzten Zusammenfuehrens - fuer die Meldung nach "Sicherung
# zusammenfuehren" (fisi_sicherung.merge_message)
LAST_MERGE = MergeStats()


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
        if not _resolved_in_time(url):
            raise OSError("Namensauflösung hängt")
        with urllib.request.urlopen(request, timeout=TIMEOUT,
                                    context=_ssl_context()) as response:
            body = response.read()
            _note_server_time(response.headers.get("Date"))
            return body
    except urllib.error.HTTPError:
        raise
    except (urllib.error.URLError, OSError):
        raise SyncError("Keine Verbindung zu GitHub. Bitte die Internetverbindung "
                        "prüfen.")
    except http.client.HTTPException:
        # ab 0.62.5 (B-G-27): z.B. IncompleteRead - Verbindung brach mitten in
        # der Antwort ab
        raise SyncError(MSG_INCOMPLETE)


def _resolved_in_time(url):
    """Ab 0.62.5 (B-G-22): Der timeout von urlopen gilt nicht fuer die
    Namensaufloesung (DNS). Haengt sie, dauerte ein Fehlversuch deutlich
    laenger als TIMEOUT. Deshalb loest vorher ein Hilfs-Thread den Namen auf;
    False, wenn er nach TIMEOUT noch nicht fertig ist (er endet von selbst,
    sobald das System aufgibt). Scheitert die Aufloesung schnell, geht es wie
    bisher weiter (urlopen meldet den Fehler). Mit Proxy loest der Proxy die
    Namen auf - dann keine Vorab-Aufloesung."""
    parts = urllib.parse.urlsplit(url)
    if not parts.hostname or parts.scheme in urllib.request.getproxies():
        return True
    port = parts.port or (443 if parts.scheme == "https" else 80)

    def resolve():
        try:
            socket.getaddrinfo(parts.hostname, port, 0, socket.SOCK_STREAM)
        except Exception:
            pass

    worker = threading.Thread(target=resolve, name="abgleich-dns", daemon=True)
    worker.start()
    worker.join(TIMEOUT)
    return not worker.is_alive()


# Ab 0.62.4: Uhrzeit von GitHub aus dem Date-Kopf der letzten Antwort und die
# Geraeteuhr in diesem Moment (beides UTC) - None, solange keine da ist
_SERVER_CLOCK = {"server": None, "device": None}


def _note_server_time(value):
    try:
        server = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return
    if server is None or server.tzinfo is None:
        return
    _SERVER_CLOCK["server"] = server.astimezone(datetime.timezone.utc)
    _SERVER_CLOCK["device"] = device_now().astimezone(datetime.timezone.utc)


_NO_DATE_LOGGED = []


def _log_missing_date():
    """Ohne Date-Kopf gibt es keine Uhrzeit von GitHub: Der Abgleich laeuft
    wie bis 0.62.3. Einmal je Programmstart eine Zeile in fehler.log."""
    if not _NO_DATE_LOGGED:
        _NO_DATE_LOGGED.append(True)
        write_error_log("Abgleich: GitHub-Antwort ohne Date-Kopf, Uhrzeit-Prüfung "
                        "entfällt (wie bis 0.62.3).")


def _clock_deviation():
    """Geraeteuhr minus Uhrzeit von GitHub in Sekunden, oder None."""
    if _SERVER_CLOCK["server"] is None:
        return None
    return (_SERVER_CLOCK["device"] - _SERVER_CLOCK["server"]).total_seconds()


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
    except ValueError:
        # ab 0.62.5 (B-G-27): kein JSON (fremde Seite, abgeschnitten)
        raise SyncError(MSG_INCOMPLETE)
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise SyncError(_http_error(error.code, repo))
        # 404 heisst entweder "Datei fehlt noch" oder "Repo nicht erreichbar"
        try:
            _request("GET", "%s/repos/%s" % (API, repo), token)
        except urllib.error.HTTPError as repo_error:
            raise SyncError(_http_error(repo_error.code, repo))
        return None, None
    if not isinstance(meta, dict):
        raise SyncError(MSG_INCOMPLETE)     # ab 0.62.5 (B-G-27): z.B. eine Liste

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
            raise _Conflict(error.code)
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
        meta = dict(conn.execute("SELECT key, value FROM sync_meta"))
    finally:
        conn.close()
    markers = {key: value for key, value in meta.items() if key in MARKERS and value}
    clamps = {}
    for key in MARKERS:
        pair = _clamp_pair(meta.get(CLAMP_PREFIX + key))
        if pair:
            clamps[key] = pair
    result = {
        "format": FORMAT,
        WRITER_KEY: WRITER,
        CLAMP_KEY: clamps,
        "columns": {table: list(columns) for table, columns in SYNC_TABLES.items()},
        "markers": markers,
        "tables": tables,
    }
    if meta.get(MIXED_KEY):
        result[MIXED_KEY] = meta[MIXED_KEY]
    return result


def _parse_utc(value):
    """ISO-Zeitpunkt mit Zone als UTC, sonst None."""
    try:
        moment = datetime.datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return moment.astimezone(datetime.timezone.utc) if moment.tzinfo else None


def _mixed_recent(db, now=None):
    """True, solange die letzte Datei eines Geraets vor 0.62.4 hoechstens
    MIXED_HOLD her ist (Geraeteuhr, wenn now fehlt)."""
    seen = _parse_utc(db.get_meta(MIXED_KEY))
    now = now or device_now().astimezone(datetime.timezone.utc)
    return seen is not None and (now - seen).total_seconds() <= MIXED_HOLD


def _note_mixed(db, remote, deviation):
    """Merkt sich, ob ein Geraet vor 0.62.4 mit abgleicht (ab 0.62.4), und
    liefert True, solange das hoechstens MIXED_HOLD her ist. Die Zeit ist die
    Uhrzeit von GitHub, wenn bekannt, sonst die Geraeteuhr."""
    now = device_now().astimezone(datetime.timezone.utc)
    if deviation is not None:
        now -= datetime.timedelta(seconds=deviation)
    local = _parse_utc(db.get_meta(MIXED_KEY))
    # Mit der Uhrzeit von GitHub gilt ein Wert in der Zukunft als falsch (er
    # entstand ohne Date-Kopf mit einer vorgehenden Uhr) und zaehlt nicht;
    # so entscheiden alle Geraete gleich (Gegenpruefung A-9). Ohne sie haelt
    # wenigstens ein Wert weit in der Zukunft nicht ewig fest.
    limit = CLOCK_TOLERANCE if deviation is not None else MIXED_HOLD
    if local is not None and (local - now).total_seconds() > limit:
        local = None
        db.set_meta(MIXED_KEY, "")
    if remote is not None and remote.get(WRITER_KEY) is None:
        local = now
        db.set_meta(MIXED_KEY, now.isoformat())
    elif remote is not None:
        seen = _parse_utc(remote.get(MIXED_KEY))
        if seen is not None and (seen - now).total_seconds() <= limit and (
                local is None or seen > local):
            local = seen
            db.set_meta(MIXED_KEY, seen.isoformat())
    return _mixed_recent(db, now)


def parse_marker(value):
    """Zerlegt eine Marke: (Ortszeit-Text ohne Zone, Zeitpunkt in UTC ohne
    tzinfo oder None bei einer Marke ohne Zone). None bei einer ungueltigen
    Marke (falsches Muster, kein gueltiges Datum, kein Text)."""
    if not isinstance(value, str):
        return None
    match = _MARKER_RE.match(value)
    if not match:
        return None
    text = match.group(1) + (match.group(2) or "")
    try:
        local = datetime.datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    if match.group(2):
        local = local.replace(microsecond=int(match.group(2)[1:].ljust(6, "0")))
    if not match.group(3):
        return text, None
    hours, minutes = int(match.group(4)), int(match.group(5))
    if hours > 23 or minutes > 59:
        return None
    delta = datetime.timedelta(hours=hours, minutes=minutes)
    return text, (local - delta if match.group(3) == "+" else local + delta)


def _later(first, second, zone=True):
    """Die spaetere von zwei Marken. Haben beide eine Zone (und zone ist an),
    zaehlt UTC, sonst der Text wie bisher. Ungueltige Marken zaehlen nicht
    (ohne zone nur solche, die kein Text sind - wie bis 0.62.3)."""
    values = [value for value in (first, second)
              if value and (parse_marker(value) if zone else isinstance(value, str))]
    if not values:
        return None
    if zone and len(values) == 2:
        parsed = [parse_marker(value)[1] for value in values]
        if parsed[0] is not None and parsed[1] is not None:
            return values[0] if parsed[0] >= parsed[1] else values[1]
    return max(values)


def _merged_markers(local, remote, zone=True):
    markers = {}
    for key in MARKERS:
        value = _later(local.get(key), remote.get(key), zone)
        if value:
            markers[key] = value
    return markers


def _invalid_markers(markers, zone=True):
    """Schluessel mit einem Wert, der keine gueltige Marke ist. Ohne zone
    (Mischbetrieb) nur Werte, die kein Text sind: Einen Text wendet ein Geraet
    vor 0.62.4 als Text an, und neue Geraete tun dasselbe."""
    return [key for key in MARKERS if markers.get(key) and not (
        parse_marker(markers[key]) if zone else isinstance(markers[key], str))]


def _falls_under(record, marker):
    """True, wenn ein Eintrag zeitlich nicht nach der Marke liegt (geloescht
    bzw. nicht uebernommen wird). marker ist parse_marker(...); utc None =
    Textvergleich wie bisher."""
    text, utc = marker
    offset = record.get(UTC_OFFSET)
    if utc is not None and offset is not None:
        try:
            moment = datetime.datetime.strptime(str(record["timestamp"])[:19],
                                                "%Y-%m-%d %H:%M:%S")
            return moment - datetime.timedelta(minutes=int(offset)) <= utc
        except (TypeError, ValueError):
            pass
    return str(record["timestamp"]) <= text


def _delete_before(cur, table, marker):
    """Loescht lokal alles, was nicht nach der Marke liegt. Mit Zone: Eintraege
    mit utc_offset in UTC, die uebrigen als Text wie bisher. Liefert die uids
    der geloeschten Eintraege."""
    text, utc = marker
    if utc is None or UTC_OFFSET not in SYNC_TABLES[table]:
        where, params = "timestamp <= ?", (text,)
    else:
        where = ("(utc_offset IS NULL AND timestamp <= ?) OR (utc_offset IS NOT NULL AND "
                 "datetime(substr(timestamp, 1, 19), printf('%d minutes', -utc_offset))"
                 " <= ?)")
        params = (text, utc.strftime("%Y-%m-%d %H:%M:%S.%f"))
    gone = {row[0] for row in cur.execute("SELECT uid FROM %s WHERE %s" % (table, where),
                                          params)}
    cur.execute("DELETE FROM %s WHERE %s" % (table, where), params)
    return gone


def merge_into_local(db, remote, check_future=True, stats=None, mixed=None):
    """Uebernimmt fehlende Eintraege und Loeschzeitpunkte aus remote in die
    lokale Datenbank. Liefert die Zahl der neu uebernommenen Eintraege.

    Ab 0.62.4: Ungueltige Marken gelten nicht. check_future (Sicherung
    zusammenfuehren, keine Uhrzeit von GitHub): Marken mit Zone, die mehr als
    CLOCK_TOLERANCE nach der Geraeteuhr liegen, gelten nicht. Der Abgleich
    prueft das vorher selbst mit der Uhrzeit von GitHub. stats (MergeStats)
    zaehlt mit, was die Marken entfernt haben; zusaetzlich in LAST_MERGE.
    Ab 0.62.5 (M-1): SyncError, wenn die Datenbank nur gelesen werden darf."""
    global LAST_MERGE
    refuse_read_only(db)
    stats = stats if stats is not None else MergeStats()
    stats.backup = check_future
    LAST_MERGE = stats
    local_markers = export_local(db)["markers"]
    remote_markers = dict(remote.get("markers") or {}) if isinstance(
        remote.get("markers"), dict) else {}
    # Mischbetrieb: Hat zuletzt ein Geraet vor 0.62.4 die Datei (bzw. die
    # Sicherung) geschrieben, wird wie dort als Text verglichen - auch eine
    # ungueltige Marke wie "x" gilt dann wie dort. Sonst verwuerfe das aeltere
    # Geraet Eintraege, die ein neues behaelt, und beide luden sie abwechselnd
    # hoch (ueber Zeitzonen, die Zeitumstellung und ungueltige Marken).
    # Ebenso, solange ein altes Geraet vor kurzem mitgeschrieben hat
    # (MIXED_KEY): Sonst fielen z.B. Eintraege eines Geraets mit falscher Uhr
    # unter eine Zukunftsmarke, die ein altes Geraet festhaelt.
    # Der Abgleich gibt mixed mit der Uhrzeit von GitHub mit, damit alle
    # Geraete gleichzeitig umschalten (Gegenpruefung A-9, F4).
    if mixed is None:
        mixed = _mixed_recent(db)
    zone = remote.get(WRITER_KEY) is not None and not mixed
    for source in (local_markers, remote_markers):
        for key in _invalid_markers(source, zone):
            del source[key]
            stats.invalid += 1
    if check_future:
        limit = (device_now().astimezone(datetime.timezone.utc).replace(tzinfo=None)
                 + datetime.timedelta(seconds=CLOCK_TOLERANCE))
        for key in MARKERS:
            parsed = parse_marker(remote_markers.get(key))
            if parsed and parsed[1] is not None and parsed[1] > limit:
                del remote_markers[key]
                stats.future += 1
    markers = _merged_markers(local_markers, remote_markers, zone)
    reset = markers.get("reset_at")
    cleared = _later(reset, markers.get("history_cleared_at"), zone)
    game_reset = markers.get("spiel_reset_at")
    remote_columns = remote.get("columns") or {}
    remote_tables = remote.get("tables") or {}

    received = []       # ab 0.62.5 (B-G-18): (Tabelle, uid) neu uebernommen
    refuse_read_only(db)    # ab 0.63.2 (G-B): direkt vor dem Schreibblock
    conn = sqlite3.connect(db.db_path)
    try:
        cur = conn.cursor()
        # Ab 0.62.4: ungueltige lokale Marken fallen dabei weg
        cur.execute("DELETE FROM sync_meta WHERE key IN (%s)" % ", ".join("?" * len(MARKERS)),
                    MARKERS)
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
            if cutoff and zone:
                cutoff = parse_marker(cutoff)
            elif cutoff:
                cutoff = (cutoff, None)         # Text wie bis 0.62.3
            gone = _delete_before(cur, table, cutoff) if cutoff else set()
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
                if cutoff and _falls_under(record, cutoff):
                    if cur.execute("SELECT 1 FROM %s WHERE uid = ?" % table,
                                   (record["uid"],)).fetchone() is None:
                        gone.add(record["uid"])
                    continue
                cur.execute(sql, [record["uid"]] + [record[c] for c in columns])
                if cur.rowcount > 0:
                    received.append((table, record["uid"]))
            stats.gone.update((table, uid) for uid in gone)
        # Geloeschte Durchgaenge (ab 0.48) verschwinden, auch wenn ihre
        # Ereignisse gerade erst von einem anderen Geraet kamen
        purge_deleted_runs(cur)
        # Ab 0.62.5 (B-G-18): netto zaehlen - was purge_deleted_runs gleich
        # wieder entfernt hat (nur Spielereignisse), gilt nicht als "uebernommen"
        received = sum(1 for table, uid in received if table != "spiel_ereignisse"
                       or cur.execute("SELECT 1 FROM spiel_ereignisse WHERE uid = ?",
                                      (uid,)).fetchone() is not None)
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
    refuse_read_only(db)        # ab 0.62.5 (M-1): vor jedem Zugriff aufs Netz

    received = 0
    stats = MergeStats()
    clamped = False
    rejected = False        # ab 0.62.5 (B-G-28): letzter Versuch mit 422 abgelehnt
    for _attempt in range(3):
        _SERVER_CLOCK.update(server=None, device=None)
        sha, remote = fetch_remote(repo, token)
        refuse_read_only(db)    # ab 0.63.2 (G-B): auch nach dem Netz, vor dem Schreiben
        raw_markers = dict((remote or {}).get("markers") or {}) if remote else {}
        deviation = _clock_deviation()
        mixed = _note_mixed(db, remote, deviation)
        if deviation is None:
            _log_missing_date()
        else:
            _correct_own_entries(db, remote, deviation)
            db.set_meta(CLOCK_KEY, clock_measurement(deviation))
            clamped = _clamp_future_markers(db, remote, deviation, mixed) or clamped
        if remote:
            received += merge_into_local(db, remote, check_future=False, stats=stats,
                                         mixed=mixed)
        local = export_local(db)
        remote_uids = _uids(remote) if remote else {}
        local_uids = _uids(local)
        if remote and local_uids == remote_uids and local["markers"] == raw_markers:
            result = SyncResult(received, 0)
            break
        sent = sum(len(uids - remote_uids.get(table, set()))
                   for table, uids in local_uids.items())
        try:
            upload(repo, token, local, sha, device)
        except _Conflict as conflict:
            rejected = conflict.code == 422
            continue
        result = SyncResult(received, sent)
        break
    else:
        if rejected:
            raise SyncError(MSG_UPLOAD_REJECTED)
        raise SyncError("Ein anderes Gerät hat gleichzeitig abgeglichen. Bitte "
                        "gleich noch einmal versuchen.")

    result.removed = stats.removed
    result.notes = stats.notes() + ([MSG_FUTURE_MARKER] if clamped else [])
    save_sync_settings(sync_last=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    return result


def _correct_own_entries(db, remote, deviation):
    """Traegt eine neu gemessene Abweichung der Geraeteuhr in utc_offset der
    eigenen, noch nicht hochgeladenen Eintraege nach (ab 0.62.4). Sie
    entstanden mit derselben falschen Uhr, bevor die Abweichung bekannt war;
    ohne Nachtrag laegen sie nach einer Loeschung mit der Uhrzeit von GitHub
    scheinbar spaeter und kaemen zurueck. Eigene Eintraege sind die, die die
    Datei noch nicht kennt. Nur die letzten CLOCK_VALID Sekunden (nach der
    Geraeteuhr): Was aelter ist, kann vor dem Verstellen der Uhr entstanden
    sein. Nur Eintraege, deren Abstand noch der reine Zonen-Abstand ihrer
    Ortszeit ist: Hat _stamp schon eine Abweichung eingerechnet, bleibt der
    Eintrag, wie er ist (sonst kaeme sie doppelt hinein).

    Ab 0.62.5 (Restrisiko 18): Nur Eintraege, die mit der Abweichung nicht
    vor die letzte Messung fallen. Was dann davor laege, entstand nach der
    letzten Messung mit noch richtiger Uhr (die Datei kennt es nicht, es kam
    also nach dem letzten Hochladen) - es wuerde sonst unter eine Loeschung
    geschoben, die vor ihm lag."""
    if abs(deviation) <= CLOCK_TOLERANCE:
        return
    # War schon eine Abweichung bekannt, hat _stamp sie eingerechnet. Am
    # Abstand allein ist das nicht sicher zu erkennen: Bei genau einer
    # Stunde sieht ein Eintrag aus der doppelten Stunde am Ende der Sommerzeit
    # wie unkorrigiert aus (Gegenpruefung A-9, F5).
    # Ab 0.62.5: Wurde die Uhr seit der Messung richtig gestellt (Laufzeit-Uhr,
    # Restrisiko 3), liefert clock_deviation die kleine Abweichung danach -
    # _stamp rechnet seitdem nichts mehr ein, der Nachtrag darf wieder.
    known_before = clock_deviation(db.get_meta(CLOCK_KEY))
    if known_before is not None and abs(known_before) > CLOCK_TOLERANCE:
        return
    shift = int(round(deviation / 60.0))
    earliest = _measured_server_time(db)
    known = _uids(remote) if remote else {}
    since = (device_now() - datetime.timedelta(seconds=CLOCK_VALID)).strftime(
        "%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(db.db_path)
    try:
        with conn:
            for table in MARKED_TABLES:
                if UTC_OFFSET not in SYNC_TABLES.get(table, ()):
                    continue
                skip = known.get(table, set())
                rows = conn.execute("SELECT rowid, uid, timestamp, utc_offset FROM %s WHERE "
                                    "utc_offset IS NOT NULL AND timestamp >= ?" % table,
                                    (since,)).fetchall()
                updates = []
                for rowid, uid, stamp, offset in rows:
                    if uid in skip:
                        continue
                    try:
                        moment = datetime.datetime.strptime(str(stamp)[:19],
                                                            "%Y-%m-%d %H:%M:%S")
                        # beide Lesarten der doppelten Stunde (Zeitumstellung)
                        plain = {offset_minutes(moment.replace(fold=fold).astimezone())
                                 for fold in (0, 1)}
                    except (TypeError, ValueError, OverflowError, OSError):
                        continue
                    if offset in plain and (earliest is None or moment - datetime.timedelta(
                            minutes=offset + shift) >= earliest):
                        updates.append((offset + shift, rowid))
                conn.executemany("UPDATE %s SET utc_offset = ? WHERE rowid = ?" % table,
                                 updates)
    finally:
        conn.close()


def _last_measurement(db):
    """Letzte gespeicherte Messung der Geraeteuhr (ab 0.62.5): (Abweichung in
    Sekunden, Geraeteuhr beim Messen in UTC ohne tzinfo), ohne Altersgrenze -
    oder None."""
    try:
        data = json.loads(db.get_meta(CLOCK_KEY))
        seconds = float(data["s"])
        measured = _parse_utc(data["gemessen"])
    except (TypeError, ValueError, KeyError, IndexError):
        return None
    if measured is None:
        return None
    return seconds, measured.replace(tzinfo=None)


def _measured_server_time(db):
    """Uhrzeit von GitHub bei der letzten Messung (UTC ohne tzinfo) minus
    CLOCK_TOLERANCE, oder None (ab 0.62.5). Eigene, noch nicht hochgeladene
    Eintraege und Marken entstanden nicht davor."""
    previous = _last_measurement(db)
    if previous is None:
        return None
    seconds, measured = previous
    return measured - datetime.timedelta(seconds=seconds + CLOCK_TOLERANCE)


def _clamp_pair(value):
    """[alt, neu] aus sync_meta (JSON-Text) oder aus der Datei, sonst None."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return None
    if isinstance(value, list) and len(value) == 2 and all(
            isinstance(item, str) and parse_marker(item) for item in value):
        return value
    return None


def _clamp_future_markers(db, remote, deviation, mixed=False):
    """Setzt Marken mit Zone, die mehr als CLOCK_TOLERANCE nach der Uhrzeit von
    GitHub liegen, einmal auf diese Uhrzeit S (ab 0.62.4) - lokal und in der
    gelesenen Datei, die danach mit S hochgeladen wird. So nehmen alle Geraete
    dasselbe S. Hat zuletzt ein aelteres Geraet geschrieben (Feld "schreiber"
    fehlt), wird keine Marke gesetzt, weder in der Datei noch lokal: Das
    aeltere Geraet naehme sonst beim naechsten Abgleich wieder seine Marke,
    und beide luden abwechselnd hoch. Marken ohne Zone bleiben (ihre Zone ist
    unbekannt). mixed (_note_mixed): Eine Zukunftsmarke, die schon in der
    Datei steht, bleibt; ein altes Geraet kann sie uebernommen haben. Nur eine
    Marke, die erst auf diesem Geraet steht, wird gesetzt, bevor sie in die
    Datei kommt. Liefert True, wenn eine Marke gesetzt wurde."""
    if remote is not None and remote.get(WRITER_KEY) is None:
        return False
    server = (device_now() - datetime.timedelta(seconds=deviation)).astimezone()
    server_utc = server.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    limit = server_utc + datetime.timedelta(seconds=CLOCK_TOLERANCE)
    value_s = format_with_zone(server)
    remote_markers = (remote or {}).get("markers")
    remote_markers = remote_markers if isinstance(remote_markers, dict) else {}

    def future(value):
        parsed = parse_marker(value)
        return bool(parsed and parsed[1] is not None and parsed[1] > limit)

    remote_clamps = (remote or {}).get(CLAMP_KEY)
    remote_clamps = remote_clamps if isinstance(remote_clamps, dict) else {}
    changed = False
    for key in MARKERS:
        remote_value = remote_markers.get(key)
        local_value = db.get_meta(key)
        if mixed and future(remote_value):
            continue
        known = _clamp_pair(remote_clamps.get(key))
        own = _clamp_pair(db.get_meta(CLAMP_PREFIX + key))
        # Zwei Geraete haben dieselbe Marke gleichzeitig gesetzt: die fruehere
        # Uhrzeit gilt fuer alle
        if known and own and known[0] == own[0] and known[1] != own[1]:
            first = known if _later(known[1], own[1]) == own[1] else own
            if local_value in (known[1], own[1]):
                db.set_meta(key, first[1])
                local_value = first[1]
            db.set_meta(CLAMP_PREFIX + key, json.dumps(first))
            own = first
        elif known and not own:
            db.set_meta(CLAMP_PREFIX + key, json.dumps(known))
            own = known
        for value in (remote_value, local_value):
            if not future(value):
                continue
            target = own[1] if own and own[0] == value else value_s
            if own is None or own[0] != value:
                own = [value, target]
                db.set_meta(CLAMP_PREFIX + key, json.dumps(own))
            if value == remote_value:
                remote_markers[key] = target
            if value == local_value:
                db.set_meta(key, target)
                local_value = target
            changed = True
    return changed
