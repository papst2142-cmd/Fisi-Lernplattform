#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fachinformatiker Lernplattform - Problem melden (ab 0.54)
=========================================================

Baut einen Bericht fuer die Fehlersuche: Programmversion, Geraet, Datenordner,
ein paar Systemwerte (Anzahl Eintraege, Groesse der Datenbank) und das
Fehlerprotokoll fehler.log (fisi_core.install_error_log, nur gelesen,
hoechstens die letzten ERROR_LOG_MAX Bytes), ab 0.55.1 auch update.log, ab
0.59.2 am PC haenger.log (letzte HANG_LOG_MAX Bytes) und laeuft.info. Ohne Oberflaeche, damit PC und
Handy denselben Text zeigen, kopieren und speichern.

Datenschutz wie bei der Sicherung (fisi_sicherung.py): Von den Einstellungen
kommt nur Unbedenkliches in den Bericht (Tagesziel, ob der Abgleich
eingerichtet ist). Zugangsschluessel und Passwoerter werden zusaetzlich aus
dem ganzen Text entfernt (scrub) - auch wenn sie in fehler.log stehen, z.B.
in einer Fehlermeldung mit Adresse oder Kopfzeile. Persoenliche Inhalte
(Antworten, Projekttexte) stehen nie darin.

Ablauf:
  text = build_report(db, "0.54", geraet="PC")   -> fertiger, gefilterter Text
  name = default_name()                          -> Vorschlag zum Speichern
"""

import datetime
import os
import platform
import re
import sys

from fisi_core import (APP_DISPLAY_NAME, ERROR_LOG_MAX, EVENT_TABLES, GAME_TABLES, anonymize_paths,
                       error_log_path, plural)

# Texte (PC und Handy gleich)
TITLE = "Problem melden"
SUBTITLE = "Angaben für die Fehlersuche"
HELP = ("Zeigt Programmversion, Gerät, Datenordner und das Fehlerprotokoll. "
        "Zugangsschlüssel, Passwörter und dein Benutzername in Pfaden werden "
        "entfernt, deine Antworten und "
        "Projekttexte stehen nicht darin. Speichere den Bericht als Datei (oder "
        "kopiere ihn) und gib ihn mit deiner Beschreibung des Problems an die "
        "Person weiter, von der du das Programm hast.")
BTN_COPY = "Kopieren"
BTN_SAVE = "Als Datei speichern"
BTN_FOLDER = "Datenordner öffnen"
MSG_COPIED = "Bericht in die Zwischenablage kopiert"
MSG_FOLDER_ERROR = "Der Datenordner ließ sich nicht öffnen: %s"
NO_LOG = ("Keine Fehler aufgezeichnet – die Datei fehler.log ist leer oder noch nicht "
          "vorhanden. Das ist ein gutes Zeichen.")
LOG_CUT = "… (ältere Einträge gekürzt, gezeigt werden die letzten %d KB)"
FILE_TYPE = "Textdatei"
# Ab 0.59.2 (PC): Haenger-Diagnose (fisi_haenger) und Halter der Sperre
# (fisi_einzelstart). Nur Dateinamen, damit das Handy fisi_haenger nicht braucht.
HANG_LOG_NAME = "haenger.log"
HANG_LOG_MAX = 16 * 1024
INFO_NAME = "laeuft.info"
FILE_EXT = ".txt"
REDACTED = "[entfernt]"

# Einstellungs-Schluessel, deren Werte nie im Bericht stehen duerfen
SECRET_KEY = re.compile(r"token|passw|kennwort|secret|geheim|api[_-]?key", re.I)

# Muster fuer Zugangsdaten im freien Text (fehler.log, Fehlermeldungen)
_PATTERNS = [
    # GitHub-Zugangsschluessel (klassisch und fein eingestellt)
    (re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{16,})"), REDACTED),
    # Kopfzeile "Authorization: Bearer ..."
    (re.compile(r"(?i)(authorization['\"]?\s*[:=]\s*['\"]?)(?:bearer\s+|token\s+|basic\s+)?"
                r"[^\s'\",}]+"), r"\1" + REDACTED),
    (re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/=-]{8,}"), r"\1" + REDACTED),
    # Schluessel = Wert bzw. "schluessel": "wert"
    (re.compile(r"(?i)([\"']?[\w-]*(?:token|passw\w*|kennwort|secret|api[_-]?key)[\"']?"
                r"\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^\s,;}]+)"), r"\1" + REDACTED),
    # Zugangsdaten in Adressen: https://name:passwort@host oder https://token@host
    (re.compile(r"(?i)\b(https?://)[^\s/@]+@"), r"\1" + REDACTED + "@"),
]


def _now():
    return datetime.datetime.now()


def default_name(now=None):
    """Vorschlag fuer den Dateinamen, z.B. Lernplattform-Problembericht_2026-10-02_1423.txt."""
    return "Lernplattform-Problembericht_%s%s" % ((now or _now()).strftime("%Y-%m-%d_%H%M"), FILE_EXT)


def secrets_of(settings):
    """Werte geheimer Einstellungen (Token, Passwoerter), laengste zuerst."""
    values = set()
    for key, value in (settings or {}).items():
        if SECRET_KEY.search(str(key)) and isinstance(value, str) and \
                len(value.strip()) >= 6:
            values.add(value.strip())
    return sorted(values, key=len, reverse=True)


def scrub(text, secrets=()):
    """Entfernt Zugangsschluessel und Passwoerter aus text: zuerst die
    bekannten Werte (secrets, z.B. der eingetragene Token), dann alles, was
    nach Zugangsdaten aussieht."""
    for secret in secrets:
        if secret:
            text = text.replace(secret, REDACTED)
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def read_log(path=None, limit=ERROR_LOG_MAX):
    """Inhalt von fehler.log, hoechstens die letzten limit Bytes (bei
    gekuerztem Anfang ab der naechsten ganzen Zeile, mit Hinweis). Fehlt
    die Datei oder ist sie leer: ""."""
    path = path or error_log_path()
    try:
        with open(path, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - limit))
            raw = handle.read(limit)
    except OSError:
        return ""
    text = raw.decode("utf-8", errors="replace")
    if size > limit:
        cut = text.find("\n")
        text = (LOG_CUT % (limit // 1024)) + "\n" + (text[cut + 1:] if cut >= 0 else "")
    return text.strip()


def _size_text(size):
    if size < 1024:
        return "%d Bytes" % size
    if size < 1024 * 1024:
        return ("%.1f KB" % (size / 1024.0)).replace(".", ",")
    return ("%.1f MB" % (size / 1024.0 / 1024.0)).replace(".", ",")


def _db_size(db_path):
    total = 0
    for suffix in ("", "-wal", "-journal"):
        try:
            total += os.path.getsize(db_path + suffix)
        except OSError:
            pass
    return total


def device_text(geraet=""):
    """z.B. "PC · Linux 6.8 (x86_64)" - ohne Rechnernamen."""
    system = platform.system() or sys.platform
    release = platform.release()
    machine = platform.machine()
    text = " ".join(part for part in (system, release) if part)
    if machine:
        text += " (%s)" % machine
    return "%s · %s" % (geraet, text) if geraet else text


def report_lines(db=None, version="", geraet="", settings=None, now=None):
    """Kopfteil des Berichts als Zeilen (ohne fehler.log)."""
    from fisi_lernen import goal_settings
    settings = settings or {}
    lines = ["%s – Problembericht" % APP_DISPLAY_NAME,
             "Erstellt: %s" % (now or _now()).strftime("%d.%m.%Y %H:%M"),
             "Programmversion: %s" % (version or "?"),
             "Gerät: %s" % device_text(geraet),
             "Python: %s" % platform.python_version()]
    db_path = getattr(db, "db_path", None)
    if db_path:
        lines.append("Datenordner: %s" % os.path.dirname(os.path.abspath(db_path)))
        lines.append("Datenbankgröße: %s" % _size_text(_db_size(db_path)))
        try:
            learning = sum(db.table_counts(EVENT_TABLES).values())
            game = sum(db.table_counts(GAME_TABLES).values())
            lines.append("Ereignisse: %s, %s" % (
                plural(learning, "Lern-Eintrag", "Lern-Einträge"),
                plural(game, "Spielereignis", "Spielereignisse")))
        except Exception as error:   # Bericht soll auch bei kaputter Datenbank gehen
            lines.append("Ereignisse: nicht lesbar (%s)" % error)
    goal = goal_settings(settings)
    lines.append("Tagesziel: %s" % (plural(goal["ziel_anzahl"], "Aufgabe", "Aufgaben")
                                    if goal["ziel_an"] else "aus"))
    configured = bool(str(settings.get("sync_repo", "")).strip() and
                      str(settings.get("sync_token", "")).strip())
    lines.append("Abgleich eingerichtet: %s" % ("ja" if configured else "nein"))
    return lines


def build_report(db=None, version="", geraet="", settings=None, log_path=None, now=None):
    """Der ganze Bericht als Text, schon gefiltert (vor Anzeigen und Speichern
    nichts weiter noetig). settings: Einstellungen dieses Geraets (Standard:
    einstellungen.json)."""
    if settings is None:
        from fisi_update import load_settings
        settings = load_settings()
    lines = report_lines(db, version, geraet, settings, now)
    log = read_log(log_path)
    lines += ["", "--- fehler.log ---", log or NO_LOG]
    # ab 0.55.1: Protokoll des letzten Updates (nur am PC vorhanden; am Handy
    # installiert Android das Update, dort gibt es die Datei nicht)
    from fisi_update import read_update_log
    update_log = read_update_log()
    if update_log:
        lines += ["", "--- update.log ---", update_log]
    # ab 0.59.2: nur angehaengt, wenn die Dateien da sind (am Handy nie)
    folder = os.path.dirname(os.path.abspath(log_path or error_log_path()))
    hang_log = read_log(os.path.join(folder, HANG_LOG_NAME), HANG_LOG_MAX)
    if hang_log:
        lines += ["", "--- %s ---" % HANG_LOG_NAME, hang_log]
    info = read_log(os.path.join(folder, INFO_NAME), 4096)
    if info:
        lines += ["", "--- %s ---" % INFO_NAME, info]
    # ab 0.55: Benutzerpfade durch %APPDATA%, ~ bzw. "…" ersetzt (auch in
    # Eintraegen, die eine aeltere Version in fehler.log geschrieben hat)
    return anonymize_paths(scrub("\n".join(lines), secrets_of(settings)))
