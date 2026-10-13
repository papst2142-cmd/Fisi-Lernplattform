#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fachinformatiker Lernplattform - Kernmodul
==========================================

Enthaelt:
  * Pfadaufloesung fuer die Datenbank (plattformunabhaengig)
  * DBManager: SQLite-Anbindung inkl. Lern-Events fuer das Dashboard
  * Saemtliche Lerninhalte: Karteikarten, Quizfragen, AP1/AP2-Szenarien,
    Testprojekte
  * Berechnungen der Praxis-Rechner und die Volltextsuche

Bewusst ohne Oberflaeche und ohne externe Abhaengigkeiten: Das Modul laesst
sich unabhaengig vom GUI-Framework nutzen (z.B. in Tests oder Skripten).
"""

import ipaddress
import json
import os
import sys
import re
import random
import sqlite3
import datetime
import time
import unicodedata
import uuid
from decimal import Decimal, ROUND_HALF_UP, localcontext
from fractions import Fraction

# ============================================================================
#  PFADE
# ============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Ab 0.61: technische Namen und Anzeigenamen getrennt (Konzept R2, Abschnitt 3).
# Datenordner unter Windows (%APPDATA%) und macOS (~/Library/Application Support).
# NIE AENDERN: Lernstand, Einstellungen, Sperre und Protokolle liegen dort
# (test_namen.py prueft das).
DATA_DIR_NAME = "FISI-Lernplattform"
DATA_DIR_NAME_LINUX = "fisi-lernplattform"   # $XDG_DATA_HOME bzw. ~/.local/share
DB_FILE_NAME = "fisi_lernplattform.db"       # auch Handy (FLET_APP_STORAGE_DATA)
LEGACY_DB_PATH = os.path.join(BASE_DIR, DB_FILE_NAME)

# Anzeige (ab 0.61). Nur diese Werte duerfen sich bei einer Umbenennung aendern.
APP_DISPLAY_NAME = "Fachinformatiker Lernplattform"
APP_SHORT_NAME = "FI Lernplattform"          # nur an engen Stellen (Handy-Symbol)
APP_LOGO_TEXT = "FI"                          # Logo PC, Standard-Brotkrume PC/Handy
# Uebergangsformulierung bis zur Fachrichtungs-Auswahl (Plan 0.63 bewertet neu)
APP_DESCRIPTION = ("Lernprogramm für die Prüfungsvorbereitung zum Fachinformatiker "
                   "(Schwerpunkt Systemintegration)")


def data_dir(system=None, env=None, home=None):
    """Ab 0.61: Datenordner des Betriebssystems ("nt", "darwin" oder ein
    anderes System = Linux). Parameter nur fuer Tests (test_namen.py), sonst
    gelten die echten Werte."""
    system = system or ("nt" if os.name == "nt" else sys.platform)
    env = os.environ if env is None else env
    home = home or os.path.expanduser("~")
    if system == "nt":
        return os.path.join(env.get("APPDATA") or home, DATA_DIR_NAME)
    if system == "darwin":
        return os.path.join(home, "Library", "Application Support", DATA_DIR_NAME)
    root = env.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
    return os.path.join(root, DATA_DIR_NAME_LINUX)


def resolve_db_path():
    """Ermittelt den Speicherort der Datenbank.

    Reihenfolge:
      1. Umgebungsvariable FISI_DB_PATH (fuer bewusste Abweichungen)
      2. Eine bereits vorhandene Datenbank neben dem Skript (alte Installation,
         damit bestehende Lernfortschritte nicht verloren gehen)
      3. Das benutzerspezifische Datenverzeichnis des Betriebssystems. Das ist
         der saubere Weg fuer eine richtig installierte Anwendung, weil das
         Programmverzeichnis selbst schreibgeschuetzt sein kann.
    """
    env_path = os.environ.get("FISI_DB_PATH")
    if env_path:
        return os.path.abspath(os.path.expanduser(env_path))

    if os.path.exists(LEGACY_DB_PATH):
        return LEGACY_DB_PATH

    folder = data_dir()
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError:
        return LEGACY_DB_PATH
    return os.path.join(folder, DB_FILE_NAME)


# ============================================================================
#  FEHLERPROTOKOLL (ab 0.53)
# ============================================================================
#
# Unerwartete Fehler landen zusaetzlich in "fehler.log" im Datenordner (neben
# der Datenbank). Sichtbar aendert sich dadurch nichts - die Datei hilft nur
# bei der Fehlersuche. Sie bleibt klein: ueber ERROR_LOG_MAX Bytes wird die
# aeltere Haelfte verworfen.

ERROR_LOG_NAME = "fehler.log"
ERROR_LOG_MAX = 256 * 1024
_error_log_version = ""


def error_log_path():
    return os.path.join(os.path.dirname(resolve_db_path()), ERROR_LOG_NAME)


# Ab 0.55 (O2): Benutzerpfade nie im Fehlerprotokoll oder Problembericht.
# Bekannte Ordner werden durch ihren Platzhalter ersetzt (%APPDATA%,
# %LOCALAPPDATA%, ~ fuer das Benutzerverzeichnis), alle uebrigen
# Benutzernamen in Pfaden durch "…".
PATH_ELLIPSIS = "…"
_WINDOWS_USER_PATH = re.compile(
    r"(?i)((?:\b[a-z]:)?\\(?:users|benutzer|documents and settings)\\|"
    r"\b[a-z]:/(?:users|benutzer|documents and settings)/)([^\\/\r\n\"'<>|:;,]+)")
_UNIX_USER_PATH = re.compile(r"(/home/|/Users/)([^/\s\"':;,]+)")


def _path_variants(path):
    path = path.rstrip("\\/")
    variants = {path, path.replace("\\", "/"), path.replace("/", "\\")}
    return [item for item in variants if len(item) > 3]


def anonymize_paths(text, env=None, home=None):
    """Ersetzt Benutzerpfade in text (Fehlerprotokoll, Problembericht)."""
    env = os.environ if env is None else env
    home = home if home is not None else os.path.expanduser("~")
    known = []
    for name in ("LOCALAPPDATA", "APPDATA"):
        if env.get(name):
            known += [(item, "%%%s%%" % name) for item in _path_variants(env[name])]
    if home and home not in ("~", "/", "\\"):
        known += [(item, "~") for item in _path_variants(home)]
    known.sort(key=lambda pair: len(pair[0]), reverse=True)
    for path, placeholder in known:
        text = re.sub(re.escape(path) + r"(?=[\\/\s\"':;,)]|$)",
                      lambda _match, value=placeholder: value, text, flags=re.I)
    for pattern in (_WINDOWS_USER_PATH, _UNIX_USER_PATH):
        text = pattern.sub(lambda match: match.group(1) + PATH_ELLIPSIS, text)
    return text


def write_error_log(text, path=None):
    """Haengt einen Fehler mit Zeitpunkt und Version an fehler.log an. Darf
    selbst nie scheitern (kein Schreibrecht, volles Laufwerk ...). path nur
    fuer eine Datenbank an anderem Ort (ab 0.62.5: fehler.log daneben)."""
    try:
        path = path or error_log_path()
        if os.path.exists(path) and os.path.getsize(path) > ERROR_LOG_MAX:
            with open(path, encoding="utf-8", errors="replace") as handle:
                rest = handle.read()[-ERROR_LOG_MAX // 2:]
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(rest)
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("=== %s | Version %s | %s ===\n%s\n" % (
                stamp, _error_log_version or "?", sys.platform,
                anonymize_paths(text.rstrip())))
    except Exception:
        pass


def log_exception(exc_type, exc_value, exc_tb):
    import traceback
    write_error_log("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))


def install_error_log(version=""):
    """Leitet unbehandelte Fehler (Hauptprogramm, Threads und die Meldungen
    des Flet-Loggers am Handy) zusaetzlich nach fehler.log. Das bisherige
    Verhalten (Ausgabe im Terminal) bleibt."""
    import logging
    import threading
    global _error_log_version
    _error_log_version = version
    if getattr(sys.excepthook, "fisi_error_log", False):
        return    # schon eingerichtet (Handy: main() je Sitzung)
    previous = sys.excepthook

    def excepthook(exc_type, exc_value, exc_tb):
        log_exception(exc_type, exc_value, exc_tb)
        previous(exc_type, exc_value, exc_tb)
    excepthook.fisi_error_log = True
    sys.excepthook = excepthook

    previous_thread = threading.excepthook

    def thread_hook(args):
        if args.exc_type is not SystemExit:
            log_exception(args.exc_type, args.exc_value, args.exc_traceback)
        previous_thread(args)
    threading.excepthook = thread_hook

    class _Handler(logging.Handler):
        def emit(self, record):
            text = record.getMessage()
            if record.exc_info:
                import traceback
                text += "\n" + "".join(traceback.format_exception(*record.exc_info))
            write_error_log(text)
    logging.getLogger("flet").addHandler(_Handler(logging.ERROR))


# ============================================================================
#  KATEGORIEN UND FARBEN
# ============================================================================

CAT_NET = "Netzwerk & Protokolle"
CAT_SEC = "IT-Sicherheit & Datenschutz"
CAT_SYS = "Systeme, RAID & Hardware"
CAT_BIZ = "Wirtschaft & Prozesse"
CAT_DB = "Datenbanken & SQL"

CATEGORIES = [CAT_NET, CAT_SEC, CAT_SYS, CAT_BIZ, CAT_DB]

CATEGORY_SHORT = {
    CAT_NET: "Netzwerk",
    CAT_SEC: "Sicherheit",
    CAT_SYS: "Systeme",
    CAT_BIZ: "Wirtschaft",
    CAT_DB: "Datenbanken",
}

CATEGORY_ICON = {
    CAT_NET: "\u25c8",
    CAT_SEC: "\u25c9",
    CAT_SYS: "\u25a3",
    CAT_BIZ: "\u25b2",
    CAT_DB: "\u25c6",
}

# Die Farben der Oberflaeche (Palette, Kategorie- und Themenfarben) liegen in
# fisi_theme.py, damit dieses Modul ohne Oberflaeche nutzbar bleibt.

# Die fuenf Themenbloecke der AP2 fuer die Timeline im Dashboard
AP2_THEMES = [
    "Subnetting & Routing",
    "IT-Sicherheit",
    "Storage & RAID",
    "Netzwerkdesign",
    "Wirtschaft & Beratung",
]

# Die fuenf Themenbloecke der AP1 (Grundlagenpruefung im 1./2. Lehrjahr)
AP1_THEMES = [
    "Rechnernetze Grundlagen",
    "Datenschutz & Sicherheit",
    "Rechnertechnik & Zahlensysteme",
    "Projektplanung",
    "Wirtschafts- und Sozialkunde",
]

# Szenarien, deren Thema keinen eigenen Block in der Timeline hat, zaehlen
# fuer den Fortschritt zum fachlich passenden Themenblock. Das Thema selbst
# bleibt am Szenario unveraendert sichtbar.
THEME_BLOCK = {
    "Virtualisierung": "Storage & RAID",
    "Projektmanagement": "Wirtschaft & Beratung",
    # ab 0.55
    "Systemadministration": "Storage & RAID",
    "Automatisierung & Skripte": "Storage & RAID",
    "Arbeitsplatz einrichten: Bedarf, Beschaffung, Übergabe": "Projektplanung",
}


def theme_block(theme):
    """Themenblock, zu dem ein Szenario-Thema im Dashboard zaehlt."""
    return THEME_BLOCK.get(theme, theme)


# ============================================================================
#  LISTEN MIT FILTER UND SEITEN
# ============================================================================
#
# AP1-/AP2-Szenarien und Testprojekte werden gefiltert und seitenweise
# angezeigt. So zeichnen PC und Handy nie mehr als LIST_PAGE_SIZE Zeilen auf
# einmal, egal wie gross der Fragenpool wird (mit ca. 200 gleichzeitig
# gezeichneten Zeilen stuerzte die PC-Version beim Aufbau ab).
# Die Positionen bleiben die Indizes in der Gesamtliste - der Lernfortschritt
# wird ueber diese Indizes gespeichert. Neue Inhalte deshalb immer am Ende
# der JSON-Dateien anhaengen, nie einfuegen oder umsortieren.

LIST_PAGE_SIZE = 15
FILTER_ALL = "Alle"
# Status-Filter der Listen - seit 0.39 die drei Zustaende je Aufgabe (siehe
# "Lernstand je Frage" weiter unten)
STATUS_OPEN = "Offen"
STATUS_PRACTICE = "Zu üben"
STATUS_DONE = "Abgeschlossen"
STATUS_FILTERS = [FILTER_ALL, STATUS_OPEN, STATUS_PRACTICE, STATUS_DONE]


def group_values(items, field):
    """Vorkommende Werte eines Feldes (z.B. Thema) in fester Reihenfolge."""
    values = []
    for item in items:
        value = item.get(field)
        if value and value not in values:
            values.append(value)
    return values


def filter_positions(items, query="", category=FILTER_ALL, group_field=None,
                     group=FILTER_ALL, status=FILTER_ALL, statuses=None):
    """Positionen der Eintraege, die zu Suchtext und Filtern passen.

    query durchsucht Titel und das Gruppenfeld, category ist ein Fachbereich
    (CAT_...), group ein Wert von group_field (z.B. ein Thema), status einer
    aus STATUS_FILTERS und statuses {position: (status, stufe)} der Lernstand
    der bereits bearbeiteten Positionen (fehlend = offen)."""
    needle = (query or "").strip().lower()
    statuses = statuses or {}
    positions = []
    for position, item in enumerate(items):
        if category != FILTER_ALL and item.get("cat") != category:
            continue
        if group_field and group != FILTER_ALL and item.get(group_field) != group:
            continue
        if status != FILTER_ALL and \
                Q_STATUS_NAME[statuses.get(position, (Q_OPEN, ""))[0]] != status:
            continue
        if needle:
            haystack = " ".join(str(item.get(key, "")) for key in
                                ("title", group_field or "title")).lower()
            if needle not in haystack and needle != str(position + 1):
                continue
        positions.append(position)
    return positions


def page_slice(positions, page, size=LIST_PAGE_SIZE):
    """Liefert (Positionen der Seite, gueltige Seitennummer ab 0, Seitenanzahl)."""
    pages = max(1, -(-len(positions) // size))
    page = max(0, min(page, pages - 1))
    return positions[page * size:(page + 1) * size], page, pages


# ============================================================================
#  DATENBANK
# ============================================================================

# Alle Tabellen mit Lern-Eintraegen und ihre Datenspalten (ohne id und uid).
# Der Abgleich zwischen Geraeten (fisi_sync.py) arbeitet mit dieser Liste.
EVENT_TABLES = {
    "test_results": ("timestamp", "score", "total", "percentage", "note",
                     "duration_seconds"),
    "card_events": ("timestamp", "category", "question", "mode", "correct"),
    "quiz_answers": ("timestamp", "category", "question", "correct"),
    "scenario_events": ("timestamp", "scenario_index", "title", "theme", "correct"),
    "project_events": ("timestamp", "project_index", "title", "category", "correct"),
    "ap1_events": ("timestamp", "scenario_index", "title", "theme", "correct"),
    # ab 0.51: Aufgaben des Subnetting-Trainers (art z.B. "ipv4", stufe 1-3)
    "trainer_aufgaben": ("timestamp", "art", "stufe", "correct"),
    # ab 0.51: Klausursimulationen (art = Pruefungsbereich, daten = JSON mit
    # Aufgaben, Punkten je Teilaufgabe und Themen)
    "pruefungen": ("timestamp", "art", "punkte", "note", "dauer", "daten"),
}

# Ab 0.51: Tabellen, die "Historie loeschen" mit leert (wie test_results)
HISTORY_TABLES = ("test_results", "pruefungen")

# Spalten, die erst spaeter dazukamen (ab 0.39: Selbsteinschaetzung
# "Gewusst"/"Nicht gewusst" bei AP1, AP2 und Testprojekten). Eintraege von
# Geraeten mit aelterer Version haben sie nicht - sie gelten dann als leer
# (NULL = angesehen, aber nicht bewertet).
OPTIONAL_COLUMNS = {
    "scenario_events": ("correct",),
    "project_events": ("correct",),
    "ap1_events": ("correct",),
    # ab 0.48: Durchgang (Spielstand-Platz) eines Spielereignisses
    "spiel_ereignisse": ("lauf",),
}
# Spalten mit Text statt Zahl (sonst INTEGER)
TEXT_COLUMNS = ("lauf",)

# Abschlussprojekt (ab 0.51): jede Aenderung eines Feldes ist eine Zeile,
# es gilt die neueste je (projekt, feld). Bleibt bei "Alle Lerndaten
# loeschen" erhalten - es sind eigene Texte, keine Lernstaende. Aeltere
# Fassungen raeumt purge_superseded_project_rows auf allen Geraeten gleich
# auf, damit die Abgleich-Datei klein bleibt.
PROJECT_TABLES = {
    "abschlussprojekt": ("timestamp", "projekt", "feld", "wert"),
}

# Tabellen des Lernspiels (fisi_game.py). Bewusst getrennt von EVENT_TABLES:
# "Alle Lerndaten loeschen" und "Historie loeschen" beruehren den Spielstand
# nicht, dafuer gibt es "Spielstand zuruecksetzen" (Marker spiel_reset_at).
GAME_TABLES = {
    "spiel_ereignisse": ("timestamp", "typ", "daten", "geraet", "lauf"),
}

# Spielstand-Plaetze (ab 0.48): Protokoll, welcher Durchgang ("lauf") auf
# welchem der drei Plaetze liegt - Zeilen "angelegt", "geloescht" und
# "umbenannt". Wird nie geloescht (auch nicht per Marke), damit ein
# geloeschter Durchgang auf keinem Geraet wieder auftaucht.
SLOT_TABLES = {
    "spiel_plaetze": ("timestamp", "platz", "lauf", "aktion", "daten", "geraet"),
}
# Der Durchgang vor 0.48 (Ereignisse ohne lauf) - er liegt auf Platz 1
LEGACY_RUN = "alt"
# Aktiver Durchgang dieses Geraets (nur lokal, wird nicht abgeglichen)
ACTIVE_RUN_KEY = "spiel_aktiver_lauf"
_ACTIVE = object()

# Bestenliste des Lernspiels (ab 0.46): Bestwerte und Abzeichen ueber alle
# Spielstaende (Durchgaenge). Uebersteht "Spielstand zuruecksetzen" und
# "Alle Lerndaten loeschen", nur "Bestenliste loeschen" (Marker
# bestenliste_reset_at) leert sie.
RECORD_TABLES = {
    "spiel_bestenliste": ("timestamp", "durchgang", "art", "schluessel", "wert", "daten"),
}

# Ab 0.62.4: Abstand der Ortszeit zu UTC in Minuten (z.B. 120 im Sommer in
# Deutschland). timestamp bleibt Ortszeit, weil Statistik, Lernserie und
# "Heute" daran haengen. Mit dem Abstand vergleicht der Abgleich Eintraege und
# Loeschzeitpunkte ueber Zeitzonen und die Zeitumstellung hinweg richtig.
# Nur in den Tabellen, die ein Loeschzeitpunkt betrifft; Eintraege aelterer
# Versionen haben ihn nicht (NULL = wie bisher als Text vergleichen).
UTC_OFFSET = "utc_offset"
MARKED_TABLES = list(EVENT_TABLES) + list(GAME_TABLES) + list(RECORD_TABLES)
for _table in MARKED_TABLES:
    for _tables in (EVENT_TABLES, GAME_TABLES, RECORD_TABLES):
        if _table in _tables:       # direkt hinter timestamp
            _tables[_table] = _tables[_table][:1] + (UTC_OFFSET,) + _tables[_table][1:]
    OPTIONAL_COLUMNS[_table] = OPTIONAL_COLUMNS.get(_table, ()) + (UTC_OFFSET,)
del _table, _tables

# Alles, was zwischen den Geraeten abgeglichen wird
SYNC_TABLES = dict(EVENT_TABLES)
SYNC_TABLES.update(GAME_TABLES)
SYNC_TABLES.update(SLOT_TABLES)
SYNC_TABLES.update(RECORD_TABLES)
SYNC_TABLES.update(PROJECT_TABLES)


def purge_deleted_runs(cur):
    """Entfernt alle Ereignisse geloeschter Durchgaenge (ab 0.48). Der alte
    Durchgang (LEGACY_RUN) sind die Ereignisse ohne lauf."""
    runs = [row[0] for row in cur.execute(
        "SELECT DISTINCT lauf FROM spiel_plaetze WHERE aktion = 'geloescht'")]
    for run in runs:
        if run == LEGACY_RUN:
            cur.execute("DELETE FROM spiel_ereignisse WHERE lauf IS NULL OR lauf = ''")
        else:
            cur.execute("DELETE FROM spiel_ereignisse WHERE lauf = ?", (run,))


def apply_question_renames(cur):
    """Schreibt alte Fragetexte im Lernstand auf die neuen um (ab 0.53,
    siehe load_question_renames). Kennung (uid) und Zeitpunkt bleiben, der
    Abgleich zaehlt die Eintraege also nicht doppelt."""
    for table, renames in QUESTION_RENAMES.items():
        for old, new in renames.items():
            cur.execute("UPDATE %s SET question = ? WHERE question = ?" % table,
                        (new, old))


def purge_superseded_project_rows(cur):
    """Loescht im Abschlussprojekt alle Zeilen, die eine neuere Fassung
    desselben Feldes haben (ab 0.51). Gleiche Zeit: die groessere uid gilt,
    damit alle Geraete dieselbe Zeile behalten."""
    cur.execute(
        "DELETE FROM abschlussprojekt WHERE EXISTS ("
        " SELECT 1 FROM abschlussprojekt AS neu"
        " WHERE neu.projekt = abschlussprojekt.projekt"
        " AND neu.feld = abschlussprojekt.feld"
        " AND (neu.timestamp > abschlussprojekt.timestamp"
        "  OR (neu.timestamp = abschlussprojekt.timestamp"
        "      AND neu.uid > abschlussprojekt.uid)))")


# ============================================================================
#  ZEIT MIT ZONE (ab 0.62.4)
# ============================================================================

# sync_meta-Schluessel (nur lokal, wird nicht abgeglichen): wie weit die Uhr
# dieses Geraets beim letzten Abgleich von der Uhrzeit von GitHub abwich
CLOCK_KEY = "uhr_abweichung"
# Ab dieser Abweichung gilt die Geraeteuhr als falsch (Sekunden)
CLOCK_TOLERANCE = 300
# So lange gilt eine gemessene Abweichung (Sekunden, nach der Geraeteuhr)
CLOCK_VALID = 24 * 3600


def device_now():
    """Jetzt als Ortszeit mit Zone. Ueber UTC ermittelt, damit auch die
    doppelte Stunde der Zeitumstellung den richtigen Abstand bekommt."""
    return datetime.datetime.now(datetime.timezone.utc).astimezone()


def offset_minutes(moment):
    """Abstand eines Zeitpunkts mit Zone zu UTC in ganzen Minuten."""
    return int(moment.utcoffset().total_seconds() // 60)


def format_with_zone(moment):
    """Zeitpunkt als Text mit Abstand zu UTC, z.B. 2026-10-25 02:30:00+02:00.
    Immer +HH:MM oder -HH:MM, nie "Z": Die ersten 19 Zeichen sind wie bisher,
    aeltere Versionen vergleichen so weiter richtig als Text."""
    minutes = offset_minutes(moment)
    return "%s%s%02d:%02d" % (moment.strftime("%Y-%m-%d %H:%M:%S"),
                              "-" if minutes < 0 else "+",
                              abs(minutes) // 60, abs(minutes) % 60)


# Ab 0.62.5 (Restrisiko 3, Gegenpruefung A-9 F6): Zur Messung gehoert der
# Stand einer Laufzeit-Uhr (seit Systemstart, nicht stellbar) und die Kennung
# von Systemstart und Prozess. Damit zeigt sich beim Stempeln, ob die Uhr
# seit der Messung gestellt wurde (siehe clock_deviation).
PROCESS_TOKEN = uuid.uuid4().hex
_BOOT_ID = []


def _boot_clock():
    """Sekunden seit Systemstart nach einer Uhr, die sich nicht stellen laesst
    und im Ruhezustand weiterlaeuft: Linux/Android CLOCK_BOOTTIME, macOS
    CLOCK_MONOTONIC (laeuft dort im Ruhezustand weiter), sonst (Windows)
    time.monotonic (GetTickCount64, ebenso)."""
    for name in ("CLOCK_BOOTTIME",) + (("CLOCK_MONOTONIC",)
                                       if sys.platform == "darwin" else ()):
        clock = getattr(time, name, None)
        if clock is not None:
            try:
                return time.clock_gettime(clock)
            except OSError:
                pass
    return time.monotonic()


def _boot_id():
    """Kennung des Systemstarts (Linux, Android), sonst None."""
    if not _BOOT_ID:
        try:
            with open("/proc/sys/kernel/random/boot_id", encoding="ascii") as handle:
                _BOOT_ID.append(handle.read().strip() or None)
        except (OSError, ValueError):
            _BOOT_ID.append(None)
    return _BOOT_ID[0]


def clock_measurement(seconds):
    """Gemessene Abweichung als Text fuer sync_meta[CLOCK_KEY]: "s" und
    "gemessen" wie in 0.62.4 (aeltere Versionen lesen nur diese), dazu ab
    0.62.5 "lauf" (Laufzeit-Uhr), "start" (Systemstart) und "prozess"."""
    return json.dumps({"s": round(seconds, 1), "gemessen": device_now().isoformat(),
                       "lauf": round(_boot_clock(), 3), "start": _boot_id(),
                       "prozess": PROCESS_TOKEN})


def _clock_jump(data, age):
    """Um wie viele Sekunden die Geraeteuhr seit der Messung gegenueber der
    Laufzeit-Uhr gesprungen ist (gestellt), oder None, wenn das nicht
    feststellbar ist: Messung ohne Laufzeit-Uhr (aelterer Stand), anderer
    Systemstart, oder ohne Kennung des Systemstarts ein anderer Prozess."""
    try:
        then = float(data["lauf"])
    except (TypeError, ValueError, KeyError):
        return None
    start = data.get("start")
    if not (data.get("prozess") == PROCESS_TOKEN
            or (start is not None and start == _boot_id())):
        return None
    elapsed = _boot_clock() - then
    if elapsed < 0:
        return None
    return age - elapsed


def clock_deviation(value, now=None):
    """Gemessene Abweichung der Geraeteuhr in Sekunden aus dem gespeicherten
    Wert, oder None, wenn sie fehlt, unlesbar oder zu alt ist (die Uhr
    koennte inzwischen gestellt worden sein).

    Ab 0.62.5 (Restrisiko 3): Ist die Uhr seit der Messung um mehr als
    CLOCK_TOLERANCE gesprungen (Laufzeit-Uhr, _clock_jump) und geht sie
    danach richtig (Abweichung + Sprung hoechstens CLOCK_TOLERANCE), wird
    diese kleine Abweichung geliefert - _stamp und _marker_now rechnen dann
    nichts mehr ein. Geht sie nach dem Sprung weiter falsch oder ist ein
    Sprung nicht feststellbar, bleibt es bei der Messung (wie 0.62.4): So
    entsteht kein Verlustweg, den 0.62.4 nicht hatte, auch wenn die
    Laufzeit-Uhr einmal falsch zaehlen sollte."""
    try:
        data = json.loads(value)
        seconds = float(data["s"])
        measured = datetime.datetime.fromisoformat(data["gemessen"])
    except (TypeError, ValueError, KeyError):
        return None
    if measured.tzinfo is None:
        return None
    age = ((now or device_now()) - measured).total_seconds()
    if age < 0 or age > CLOCK_VALID:
        return None
    if abs(seconds) > CLOCK_TOLERANCE:
        jump = _clock_jump(data, age)
        if (jump is not None and abs(jump) > CLOCK_TOLERANCE
                and abs(seconds + jump) <= CLOCK_TOLERANCE):
            return seconds + jump
    return seconds


# ============================================================================
#  DATENBANKFEHLER (ab 0.62.5, B-G-01, B-G-03, B-G-06, B-G-12)
# ============================================================================
#
# Jeder Datenbankfehler landet mit dem technischen Text in fehler.log. Die
# Oberflaeche (PC: Fenster, Handy: roter Hinweis) zeigt je Fehlerart nur die
# erste Meldung, verstaendlich und auf Deutsch; weitere werden gezaehlt.
# Ist die Datenbank beschaedigt, schreibgeschuetzt oder nicht erreichbar,
# speichert die App nichts mehr (read_only_reason) - die Datei wird nie
# ueberschrieben. Texte gelten fuer PC und Handy gleich.

DB_ERROR_TEXTS = {
    "kaputt": ("Die Datenbank mit deinem Lernfortschritt ist beschädigt. Damit sie nicht "
               "weiter Schaden nimmt, speichert die App ab jetzt nichts mehr; angezeigte "
               "Zahlen können unvollständig sein. Die Datei selbst bleibt unverändert. "
               "Den Datenordner findest du unter Optionen > Problem melden."),
    "schreibschutz": ("Dein Lernfortschritt wird nicht gespeichert: Der Datenordner ist "
                      "schreibgeschützt. Die App läuft weiter, Antworten werden aber nicht "
                      "gespeichert. Gib dem Datenordner und der Datei fisi_lernplattform.db "
                      "Schreibrechte und starte die App neu. Den Datenordner findest du "
                      "unter Optionen > Problem melden."),
    "nicht_erreichbar": ("Dein Lernfortschritt wird nicht gespeichert: Der Datenordner ist "
                         "nicht erreichbar. Die Datenbank lässt sich nicht öffnen, zum "
                         "Beispiel weil ein Laufwerk fehlt. Prüfe den Datenordner und "
                         "starte die App neu."),
    "voll": ("Der Speicherplatz ist voll. Dein Lernfortschritt wird erst wieder "
             "gespeichert, wenn Platz frei ist."),
    "gesperrt": ("Die Datenbank ist gerade belegt, zum Beispiel durch ein anderes Programm. "
                 "Der letzte Schritt wurde vielleicht nicht gespeichert."),
    "sonstige": ("Beim Zugriff auf die Datenbank ist ein Fehler aufgetreten. Einzelheiten "
                 "stehen im Fehlerprotokoll (Optionen > Problem melden)."),
}
# Bleibende rote Zeile (PC: Seitenleiste), solange nichts gespeichert wird
DB_READ_ONLY_LINES = {
    "kaputt": "Dein Lernfortschritt wird nicht gespeichert: Die Datenbank ist beschädigt.",
    "schreibschutz": ("Dein Lernfortschritt wird nicht gespeichert: Der Datenordner ist "
                      "schreibgeschützt."),
    "nicht_erreichbar": ("Dein Lernfortschritt wird nicht gespeichert: Der Datenordner ist "
                         "nicht erreichbar."),
}
# Fehlerart aus dem englischen Text von SQLite (erster Treffer gilt)
_DB_ERROR_KINDS = (
    ("schreibschutz", ("readonly", "read-only")),
    ("kaputt", ("malformed", "not a database", "corrupt", "disk image")),
    ("nicht_erreichbar", ("unable to open",)),
    ("voll", ("is full",)),
    ("gesperrt", ("locked", "busy")),
)


def db_error_kind(text):
    """Fehlerart (Schluessel von DB_ERROR_TEXTS) zum Text eines SQLite-Fehlers."""
    text = str(text).lower()
    for kind, needles in _DB_ERROR_KINDS:
        if any(needle in text for needle in needles):
            return kind
    return "sonstige"


def _folder_writable(folder):
    """Echte Probe statt os.access (unter Windows unzuverlaessig): eine
    Wegwerf-Datei anlegen, sie verschwindet beim Schliessen von selbst."""
    import tempfile
    try:
        with tempfile.TemporaryFile(dir=folder, prefix=".fisi_schreibprobe_"):
            pass
        return True
    except OSError:
        return False


def _file_writable(path):
    """Datei zum Schreiben oeffnen, ohne etwas zu aendern (fehlt sie: ja)."""
    if not os.path.exists(path):
        return True
    try:
        with open(path, "r+b"):
            pass
        return True
    except OSError:
        return False


class DBManager:
    """SQLite-Anbindung fuer Testergebnisse und einzelne Lern-Ereignisse.

    Die Tabelle test_results stammt aus der Vorgaengerversion und bleibt
    unveraendert erhalten. Neu hinzu kommen drei Ereignistabellen, die das
    Dashboard mit echten Zahlen versorgen.
    """

    def __init__(self, db_path=None, error_handler=None):
        self.db_path = db_path or resolve_db_path()
        self.error_handler = error_handler
        # Ab 0.62.4: Um wie viele Sekunden die letzte Loeschmarke wegen einer
        # falschen Geraeteuhr korrigiert wurde (0 = nicht), fuer den Hinweis
        self.last_clock_fix = 0
        # Ab 0.62.5: Grund, warum nichts gespeichert wird (Schluessel von
        # DB_READ_ONLY_LINES) oder None; Fehlerzaehler je Art; abgelehnte
        # Schreibzugriffe
        self.read_only_reason = None
        self.error_counts = {}
        self.refused_writes = 0
        self.init_db()

    # -- Infrastruktur ------------------------------------------------------

    def _report(self, message, kind=None):
        """Ab 0.62.5: technischer Text nach fehler.log, je Fehlerart nur die
        erste verstaendliche Meldung an die Oberflaeche, der Rest wird
        gezaehlt. Wird schon nichts mehr gespeichert, kommt keine weitere
        Meldung (die erste hat das gesagt)."""
        kind = kind or db_error_kind(message)
        write_error_log("Datenbankfehler (%s): %s" % (kind, message), os.path.join(
            os.path.dirname(os.path.abspath(self.db_path)), ERROR_LOG_NAME))
        first = kind not in self.error_counts
        self.error_counts[kind] = self.error_counts.get(kind, 0) + 1
        already_read_only = self.read_only_reason is not None
        if not already_read_only and kind in DB_READ_ONLY_LINES:
            self.read_only_reason = kind
        if not self.error_handler:
            print("[DB] " + message, file=sys.stderr)
        elif first and not already_read_only:
            self.error_handler(DB_ERROR_TEXTS[kind])

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        if self.read_only_reason:
            # Ab 0.62.5: auch direkte Schreibzugriffe scheitern, die Datei
            # bleibt unveraendert
            conn.execute("PRAGMA query_only = ON")
        return conn

    def _execute(self, sql, params=(), fetch=None, commit=False, default=None):
        """Fuehrt eine Abfrage aus und faengt Datenbankfehler zentral ab.

        Rueckgabe: bei fetch das Abfrageergebnis, bei einem reinen
        Schreibvorgang True. Im Fehlerfall immer der Wert von default.
        Ab 0.62.5: Wird nichts gespeichert (read_only_reason), lehnt sie
        Schreibvorgaenge still ab (default); die Meldung kam schon.
        """
        if self.read_only_reason and (commit or fetch is None):
            self.refused_writes += 1
            return default
        conn = None
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute(sql, params)
            if fetch == "one":
                result = cur.fetchone()
            elif fetch == "all":
                result = cur.fetchall()
            else:
                # Reiner Schreibvorgang: das Gelingen ist das Ergebnis.
                result = True
            if commit:
                conn.commit()
            return result
        except sqlite3.Error as exc:
            self._report(str(exc))
            return default
        finally:
            if conn is not None:
                conn.close()

    def init_db(self):
        statements = [
            """
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                score INTEGER NOT NULL,
                total INTEGER NOT NULL,
                percentage REAL NOT NULL,
                note TEXT NOT NULL,
                duration_seconds INTEGER NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS card_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                category TEXT NOT NULL,
                question TEXT NOT NULL,
                mode TEXT NOT NULL,
                correct INTEGER
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS quiz_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                category TEXT NOT NULL,
                question TEXT NOT NULL,
                correct INTEGER NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS scenario_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                scenario_index INTEGER NOT NULL,
                title TEXT NOT NULL,
                theme TEXT NOT NULL,
                correct INTEGER
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS project_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                project_index INTEGER NOT NULL,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                correct INTEGER
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS ap1_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                scenario_index INTEGER NOT NULL,
                title TEXT NOT NULL,
                theme TEXT NOT NULL,
                correct INTEGER
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS trainer_aufgaben (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                art TEXT NOT NULL,
                stufe INTEGER NOT NULL,
                correct INTEGER NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS pruefungen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                art TEXT NOT NULL,
                punkte REAL NOT NULL,
                note TEXT NOT NULL,
                dauer INTEGER NOT NULL,
                daten TEXT NOT NULL DEFAULT '{}'
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS abschlussprojekt (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                projekt TEXT NOT NULL,
                feld TEXT NOT NULL,
                wert TEXT NOT NULL DEFAULT ''
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS spiel_ereignisse (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                typ TEXT NOT NULL,
                daten TEXT NOT NULL,
                geraet TEXT NOT NULL DEFAULT '',
                uid TEXT,
                lauf TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS spiel_plaetze (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                platz INTEGER NOT NULL,
                lauf TEXT NOT NULL,
                aktion TEXT NOT NULL,
                daten TEXT NOT NULL DEFAULT '{}',
                geraet TEXT NOT NULL DEFAULT '',
                uid TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS spiel_bestenliste (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                durchgang TEXT NOT NULL,
                art TEXT NOT NULL,
                schluessel TEXT NOT NULL,
                wert REAL,
                daten TEXT NOT NULL DEFAULT '{}',
                uid TEXT
            )
            """,
        ]
        # Ab 0.62.5: erst pruefen, ob gespeichert werden darf (Schreibrecht,
        # Datei heil) - sonst nichts anlegen und nichts nachruesten
        if not self._check_storage():
            return
        conn = None
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            for statement in statements:
                cur.execute(statement)
            self._migrate(cur)
            conn.commit()
        except sqlite3.Error as exc:
            self._report("Datenbank konnte nicht initialisiert werden: %s" % exc)
        finally:
            if conn is not None:
                conn.close()

    def _check_storage(self):
        """Ab 0.62.5 (B-G-03, B-G-06): Beim Start einmal pruefen, ob Ordner
        und Datei beschreibbar sind und ob die Datei heil ist (PRAGMA
        quick_check, nur lesend). Rueckgabe False = nichts schreiben; dann
        ist read_only_reason gesetzt und die Meldung gezeigt."""
        folder = os.path.dirname(os.path.abspath(self.db_path))
        if os.path.isdir(folder) and not (_folder_writable(folder)
                                          and _file_writable(self.db_path)):
            self._report("Schreibprobe beim Start gescheitert: Datenordner oder %s "
                         "ist schreibgeschuetzt" % os.path.basename(self.db_path),
                         kind="schreibschutz")
            return False
        if not os.path.isfile(self.db_path) or os.path.getsize(self.db_path) == 0:
            return True
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute("PRAGMA quick_check(1)").fetchall()
        except sqlite3.Error as exc:
            if db_error_kind(exc) != "kaputt":
                return True    # z.B. gesperrt: der normale Weg meldet es
            self._report("Pruefung beim Start (quick_check): %s" % exc, kind="kaputt")
            return False
        finally:
            if conn is not None:
                conn.close()
        if rows != [("ok",)]:
            self._report("Pruefung beim Start (quick_check) meldet Schaden: %s"
                         % (rows[0][0] if rows else "keine Antwort"), kind="kaputt")
            return False
        return True

    @staticmethod
    def _migrate(cur):
        """Ergaenzt aeltere Datenbanken um das, was der Abgleich zwischen
        mehreren Geraeten braucht: eine eindeutige Kennung (uid) je Eintrag,
        damit zusammengefuehrte Eintraege nie doppelt zaehlen, und die
        Tabelle sync_meta fuer Zeitpunkte wie "alles zurueckgesetzt"."""
        for table in SYNC_TABLES:
            columns = [row[1] for row in cur.execute("PRAGMA table_info(%s)" % table)]
            if "uid" not in columns:
                cur.execute("ALTER TABLE %s ADD COLUMN uid TEXT" % table)
            # Ab 0.63.2 (B-G-29): Nur wenn es Eintraege ohne uid gibt (sehr
            # alte Datenbank, vor v0.24), wird ueberhaupt geschrieben - sonst
            # bleibt die Datei unberuehrt. Die uid kommt dann aus Tabelle, id
            # und Inhalt: Zwei Kopien derselben alten Datei bekommen dieselben
            # uids, der Abgleich zaehlt ihre Eintraege nicht doppelt. Ist die
            # uid schon vergeben (Kollision), gilt wie bisher eine zufaellige.
            if cur.execute("SELECT 1 FROM %s WHERE uid IS NULL LIMIT 1"
                           % table).fetchone() is not None:
                import hashlib
                taken = {row[0] for row in cur.execute(
                    "SELECT uid FROM %s WHERE uid IS NOT NULL" % table)}
                cur.execute("SELECT rowid, * FROM %s WHERE uid IS NULL" % table)
                names = [item[0] for item in cur.description][1:]
                for row in cur.fetchall():
                    content = json.dumps([table] + [[name, value] for name, value in
                                                    zip(names, row[1:]) if name != "uid"],
                                         ensure_ascii=True, default=repr)
                    uid = hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]
                    if uid in taken:
                        uid = uuid.uuid4().hex
                    taken.add(uid)
                    cur.execute("UPDATE %s SET uid = ? WHERE rowid = ?" % table,
                                (uid, row[0]))
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_%s_uid ON %s (uid)"
                        % (table, table))
        for table, extra in OPTIONAL_COLUMNS.items():
            columns = [row[1] for row in cur.execute("PRAGMA table_info(%s)" % table)]
            for column in extra:
                if column not in columns:
                    cur.execute("ALTER TABLE %s ADD COLUMN %s %s" % (
                        table, column, "TEXT" if column in TEXT_COLUMNS else "INTEGER"))
        cur.execute("CREATE TABLE IF NOT EXISTS sync_meta ("
                    " key TEXT PRIMARY KEY, value TEXT)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_spiel_ereignisse_lauf"
                    " ON spiel_ereignisse (lauf)")
        # ab 0.53: korrigierte Fragetexte im Lernstand nachziehen
        apply_question_renames(cur)

    @staticmethod
    def _now():
        return device_now().strftime("%Y-%m-%d %H:%M:%S")

    def _stamp(self):
        """Ortszeit als Text und ihr Abstand zu UTC in Minuten (ab 0.62.4),
        aus demselben Augenblick. Wich die Uhr beim letzten Abgleich um mehr
        als CLOCK_TOLERANCE von GitHub ab, enthaelt der Abstand diese
        Abweichung: Dann ist "Ortszeit minus Abstand" die echte UTC-Zeit, und
        eine Loeschung erfasst auch Eintraege, die mit der falschen Uhr
        entstanden. Die Ortszeit selbst (Statistik, "Heute") bleibt wie bisher.
        Ab 0.62.5 nicht mehr, sobald die Uhr seit der Messung richtig gestellt
        wurde (clock_deviation, Restrisiko 3)."""
        moment = device_now()
        offset = offset_minutes(moment)
        deviation = clock_deviation(self.get_meta(CLOCK_KEY), moment)
        if deviation is not None and abs(deviation) > CLOCK_TOLERANCE:
            offset += int(round(deviation / 60.0))
        return moment.strftime("%Y-%m-%d %H:%M:%S"), offset

    @staticmethod
    def _marker_now(cur):
        """Zeitpunkt fuer eine Loeschmarke (ab 0.62.4): Ortszeit mit Zone.
        Wich die Uhr beim letzten Abgleich um mehr als CLOCK_TOLERANCE von
        GitHub ab, gilt stattdessen die Uhrzeit von GitHub - ab 0.62.5 nicht
        mehr, sobald die Uhr seit der Messung richtig gestellt wurde
        (clock_deviation, Restrisiko 3). Liefert (Text, korrigierte Sekunden
        oder 0)."""
        moment = device_now()
        row = cur.execute("SELECT value FROM sync_meta WHERE key = ?",
                          (CLOCK_KEY,)).fetchone()
        deviation = clock_deviation(row[0], moment) if row else None
        if deviation is not None and abs(deviation) > CLOCK_TOLERANCE:
            moment = (moment - datetime.timedelta(seconds=deviation)).astimezone()
            return format_with_zone(moment), deviation
        return format_with_zone(moment), 0

    @staticmethod
    def _now_fine():
        """Wie _now, aber mit Mikrosekunden - fuer die Platz-Tabelle, deren
        Reihenfolge (angelegt, umbenannt) auch innerhalb einer Sekunde zaehlt.
        Sortiert sich trotzdem richtig zwischen sekundengenaue Zeitpunkte."""
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    @staticmethod
    def _uid():
        return uuid.uuid4().hex

    def get_meta(self, key):
        row = self._execute("SELECT value FROM sync_meta WHERE key = ?", (key,),
                            fetch="one", default=None)
        return row[0] if row else None

    def set_meta(self, key, value):
        return bool(self._execute(
            "INSERT OR REPLACE INTO sync_meta (key, value) VALUES (?, ?)",
            (key, value), commit=True, default=False))

    # -- Schreiben ----------------------------------------------------------

    def save_test_result(self, score, total, percentage, note, duration_seconds):
        return bool(self._execute(
            "INSERT INTO test_results (timestamp, utc_offset, score, total, percentage, note,"
            " duration_seconds, uid) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (*self._stamp(), score, total, percentage, note, duration_seconds, self._uid()),
            commit=True, default=False))

    def log_card(self, category, question, mode, correct):
        correct_value = None if correct is None else (1 if correct else 0)
        self._execute(
            "INSERT INTO card_events (timestamp, utc_offset,"
            " category, question, mode, correct, uid)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (*self._stamp(), category, question, mode, correct_value, self._uid()),
            commit=True, default=False)

    def log_quiz_answer(self, category, question, correct):
        self._execute(
            "INSERT INTO quiz_answers (timestamp, utc_offset,"
            " category, question, correct, uid)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (*self._stamp(), category, question, 1 if correct else 0, self._uid()),
            commit=True, default=False)

    @staticmethod
    def _flag(correct):
        return None if correct is None else (1 if correct else 0)

    def log_scenario(self, index, title, theme, correct=None):
        """correct: Selbsteinschaetzung nach dem Aufdecken (ab 0.39), None =
        nur angesehen."""
        self._execute(
            "INSERT INTO scenario_events (timestamp, utc_offset,"
            " scenario_index, title, theme, correct,"
            " uid) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (*self._stamp(), index, title, theme, self._flag(correct), self._uid()),
            commit=True, default=False)

    def log_project(self, index, title, category, correct=None):
        self._execute(
            "INSERT INTO project_events (timestamp, utc_offset,"
            " project_index, title, category, correct,"
            " uid) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (*self._stamp(), index, title, category, self._flag(correct), self._uid()),
            commit=True, default=False)

    def log_ap1(self, index, title, theme, correct=None):
        self._execute(
            "INSERT INTO ap1_events (timestamp, utc_offset,"
            " scenario_index, title, theme, correct, uid)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (*self._stamp(), index, title, theme, self._flag(correct), self._uid()),
            commit=True, default=False)

    # -- Ab 0.51: Trainer, Pruefungen, Abschlussprojekt ----------------------

    def log_trainer(self, kind, level, correct):
        """Eine geloeste Aufgabe des Subnetting-Trainers."""
        return bool(self._execute(
            "INSERT INTO trainer_aufgaben (timestamp, utc_offset, art, stufe, correct, uid)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (*self._stamp(), kind, int(level), 1 if correct else 0, self._uid()),
            commit=True, default=False))

    def trainer_stats(self):
        """{art: (geloest, richtig)} ueber alle Trainer-Aufgaben."""
        rows = self._execute("SELECT art, COUNT(*), SUM(correct) FROM trainer_aufgaben"
                             " GROUP BY art", fetch="all", default=[]) or []
        return {kind: (count or 0, right or 0) for kind, count, right in rows}

    def save_exam(self, kind, points, note, duration, data):
        """Ergebnis einer Klausursimulation (data: dict, als JSON gespeichert)."""
        return bool(self._execute(
            "INSERT INTO pruefungen (timestamp, utc_offset,"
            " art, punkte, note, dauer, daten, uid)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (*self._stamp(), kind, float(points), note, int(duration),
             json.dumps(data, ensure_ascii=False), self._uid()),
            commit=True, default=False))

    def exams(self):
        """Alle Klausursimulationen, neueste zuerst: [dict]."""
        rows = self._execute("SELECT timestamp, art, punkte, note, dauer, daten, uid"
                             " FROM pruefungen ORDER BY timestamp DESC, id DESC",
                             fetch="all", default=[]) or []
        result = []
        for timestamp, kind, points, note, duration, data, uid in rows:
            try:
                details = json.loads(data or "{}")
            except ValueError:
                details = {}
            result.append({"timestamp": timestamp, "art": kind, "punkte": points,
                           "note": note, "dauer": duration, "daten": details,
                           "uid": uid})
        return result

    def save_project_field(self, project, field, value):
        """Speichert ein Feld des Abschlussprojekts (neueste Fassung gilt) und
        raeumt die aeltere Fassung gleich auf."""
        conn = None
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO abschlussprojekt (timestamp, projekt, feld, wert, uid)"
                        " VALUES (?, ?, ?, ?, ?)",
                        (self._now_fine(), project, field, value, self._uid()))
            purge_superseded_project_rows(cur)
            conn.commit()
            return True
        except sqlite3.Error as exc:
            self._report("Abschlussprojekt speichern fehlgeschlagen: %s" % exc)
            return False
        finally:
            if conn is not None:
                conn.close()

    def project_fields(self):
        """{projekt: {feld: wert}} - jeweils die neueste Fassung."""
        rows = self._execute("SELECT projekt, feld, wert FROM abschlussprojekt"
                             " ORDER BY timestamp, uid", fetch="all", default=[]) or []
        projects = {}
        for project, field, value in rows:
            projects.setdefault(project, {})[field] = value
        return projects

    def activity_days(self):
        """{tag: Anzahl bewerteter Aufgaben} (ab 0.51, fuers Tagesziel):
        Karteikarten und Szenarien nur mit Bewertung, Quiz und Trainer immer."""
        rows = self._execute(
            "SELECT substr(timestamp, 1, 10) AS tag, COUNT(*) FROM ("
            "  SELECT timestamp FROM card_events WHERE correct IS NOT NULL"
            "  UNION ALL SELECT timestamp FROM quiz_answers"
            "  UNION ALL SELECT timestamp FROM scenario_events WHERE correct IS NOT NULL"
            "  UNION ALL SELECT timestamp FROM project_events WHERE correct IS NOT NULL"
            "  UNION ALL SELECT timestamp FROM ap1_events WHERE correct IS NOT NULL"
            "  UNION ALL SELECT timestamp FROM trainer_aufgaben"
            ") GROUP BY tag", fetch="all", default=[]) or []
        return {day: count for day, count in rows}

    def activity_split_days(self):
        """{tag: (richtig, falsch)} (ab 0.56, Fortschritt "Richtig und falsch
        pro Tag"): dieselben Aufgaben wie activity_days, getrennt nach der
        gespeicherten Bewertung (Spalte correct). Liest nur vorhandene Daten."""
        rows = self._execute(
            "SELECT substr(timestamp, 1, 10) AS tag, SUM(correct = 1), SUM(correct = 0)"
            " FROM ("
            "  SELECT timestamp, correct FROM card_events WHERE correct IS NOT NULL"
            "  UNION ALL SELECT timestamp, correct FROM quiz_answers"
            "  UNION ALL SELECT timestamp, correct FROM scenario_events WHERE correct IS NOT NULL"
            "  UNION ALL SELECT timestamp, correct FROM project_events WHERE correct IS NOT NULL"
            "  UNION ALL SELECT timestamp, correct FROM ap1_events WHERE correct IS NOT NULL"
            "  UNION ALL SELECT timestamp, correct FROM trainer_aufgaben"
            ") GROUP BY tag", fetch="all", default=[]) or []
        return {day: (int(right or 0), int(wrong or 0)) for day, right, wrong in rows}

    def _run(self, run):
        """Durchgang fuer Lesen/Schreiben: ohne Angabe der aktive dieses
        Geraets. Liefert None fuer den alten Durchgang (Spalte lauf leer)."""
        if run is _ACTIVE:
            run = self.get_meta(ACTIVE_RUN_KEY)
        return None if not run or run == LEGACY_RUN else run

    def log_game_event(self, kind, data, device="", run=_ACTIVE):
        """Ein Ereignis des Lernspiels (data ist JSON-Text). run: Durchgang
        (ab 0.48), ohne Angabe der aktive Durchgang dieses Geraets."""
        return bool(self._execute(
            "INSERT INTO spiel_ereignisse (timestamp, utc_offset,"
            " typ, daten, geraet, uid, lauf)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (*self._stamp(), kind, data, device or "", self._uid(), self._run(run)),
            commit=True, default=False))

    def game_events(self, run=_ACTIVE):
        """Die Spielereignisse eines Durchgangs chronologisch:
        [(timestamp, typ, daten-dict)]. Ohne Angabe der aktive Durchgang."""
        run = self._run(run)
        if run is None:
            where, params = "lauf IS NULL OR lauf = ''", ()
        else:
            where, params = "lauf = ?", (run,)
        rows = self._execute(
            "SELECT timestamp, typ, daten FROM spiel_ereignisse WHERE %s"
            " ORDER BY timestamp, id" % where, params, fetch="all", default=[]) or []
        events = []
        for timestamp, kind, data in rows:
            try:
                payload = json.loads(data) if data else {}
            except ValueError:
                continue
            if isinstance(payload, dict):
                events.append((timestamp, kind, payload))
        return events

    def game_event_stamp(self, run=_ACTIVE):
        """Ab 0.50: billiger Stempel des Ereignisprotokolls eines Durchgangs
        (Anzahl, hoechste Nummer, juengster Zeitstempel). Aendert sich bei
        jedem neuen, geloeschten oder per Abgleich eingetroffenen Ereignis -
        der Spielstand muss nur dann neu berechnet werden."""
        run = self._run(run)
        if run is None:
            where, params = "lauf IS NULL OR lauf = ''", ()
        else:
            where, params = "lauf = ?", (run,)
        row = self._execute(
            "SELECT COUNT(*), MAX(id), MAX(timestamp) FROM spiel_ereignisse WHERE %s"
            % where, params, fetch="one", default=None)
        return tuple(row) if row else None

    # Tabellen, deren Inhalt in den Ansichten sichtbar ist (fuer change_stamp)
    STAMP_TABLES = ("card_events", "quiz_answers", "test_results", "scenario_events",
                    "project_events", "ap1_events", "spiel_ereignisse", "spiel_plaetze",
                    "spiel_bestenliste", "trainer_aufgaben", "pruefungen",
                    "abschlussprojekt")

    # Tabellen, aus denen question_results den Lernstand liest (ab 0.55)
    ANSWER_TABLES = ("card_events", "quiz_answers", "ap1_events", "scenario_events",
                     "project_events")

    def change_stamp(self, tables=None):
        """Ab 0.50: Stempel ueber alle Lern- und Spieltabellen (Anzahl und
        hoechste Nummer je Tabelle) in einer einzigen, billigen Abfrage.
        Ist er unveraendert, hat sich seit dem letzten Mal nichts getan, was
        eine Ansicht anders aussehen liesse - sie muss dann beim Wechsel
        nicht neu aufgebaut werden. None, wenn die Abfrage scheitert.
        tables (ab 0.55): nur diese Tabellen, z.B. ANSWER_TABLES."""
        sql = "SELECT " + ", ".join(
            "(SELECT COUNT(*) FROM %s), (SELECT MAX(rowid) FROM %s)" % (table, table)
            for table in (tables or self.STAMP_TABLES))
        row = self._execute(sql, fetch="one", default=None)
        return tuple(row) if row else None

    def table_counts(self, tables):
        """{tabelle: Anzahl Zeilen} (ab 0.54, fuer "Problem melden")."""
        counts = {}
        for table in tables:
            row = self._execute("SELECT COUNT(*) FROM %s" % table, fetch="one",
                                default=None)
            counts[table] = row[0] if row else 0
        return counts

    def has_legacy_events(self):
        """Gibt es Spielereignisse von vor 0.48 (ohne Durchgang)?"""
        row = self._execute("SELECT 1 FROM spiel_ereignisse WHERE lauf IS NULL OR"
                            " lauf = '' LIMIT 1", fetch="one", default=None)
        return row is not None

    def event_counts(self):
        """Anzahl Spielereignisse je Durchgang (alter Durchgang = LEGACY_RUN)."""
        rows = self._execute(
            "SELECT COALESCE(NULLIF(lauf, ''), ?), COUNT(*) FROM spiel_ereignisse"
            " GROUP BY 1", (LEGACY_RUN,), fetch="all", default=[]) or []
        return {run: count for run, count in rows}

    # -- Spielstand-Plaetze (ab 0.48) -----------------------------------------

    def log_slot(self, slot, run, action, data="", device=""):
        return bool(self._execute(
            "INSERT INTO spiel_plaetze (timestamp, platz, lauf, aktion, daten, geraet, uid)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (self._now_fine(), int(slot), run, action, data or "{}", device or "",
             self._uid()), commit=True, default=False))

    def slot_rows(self):
        """Alle Zeilen der Platz-Tabelle: [(timestamp, uid, platz, lauf, aktion,
        daten-dict)] chronologisch."""
        rows = self._execute(
            "SELECT timestamp, uid, platz, lauf, aktion, daten FROM spiel_plaetze"
            " ORDER BY timestamp, uid", fetch="all", default=[]) or []
        result = []
        for timestamp, uid, slot, run, action, data in rows:
            try:
                payload = json.loads(data) if data else {}
            except ValueError:
                payload = {}
            result.append((timestamp, uid, slot, run, action,
                           payload if isinstance(payload, dict) else {}))
        return result

    def delete_run(self, slot, run, device=""):
        """Loescht einen Durchgang endgueltig - auch auf den anderen Geraeten:
        die Zeile "geloescht" bleibt stehen, und der Abgleich entfernt jedes
        Ereignis dieses Durchgangs, egal wann und wo es entstand."""
        conn = None
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO spiel_plaetze (timestamp, platz, lauf, aktion, daten,"
                        " geraet, uid) VALUES (?, ?, ?, 'geloescht', '{}', ?, ?)",
                        (self._now_fine(), int(slot), run, device or "", self._uid()))
            purge_deleted_runs(cur)
            conn.commit()
            return True
        except sqlite3.Error as exc:
            self._report("Spielstand loeschen fehlgeschlagen: %s" % exc)
            return False
        finally:
            if conn is not None:
                conn.close()

    # -- Bestenliste des Lernspiels (ab 0.46) --------------------------------

    def log_record(self, run, kind, key, value, data=""):
        """Eine Zeile der Bestenliste (data ist JSON-Text)."""
        return bool(self._execute(
            "INSERT INTO spiel_bestenliste (timestamp, utc_offset,"
            " durchgang, art, schluessel, wert,"
            " daten, uid) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (*self._stamp(), run or "", kind, key, value, data or "{}", self._uid()),
            commit=True, default=False))

    def records(self):
        """Alle Zeilen der Bestenliste: [(timestamp, durchgang, art, schluessel,
        wert, daten-dict)] chronologisch."""
        rows = self._execute(
            "SELECT timestamp, durchgang, art, schluessel, wert, daten FROM spiel_bestenliste"
            " ORDER BY timestamp, id", fetch="all", default=[]) or []
        result = []
        for timestamp, run, kind, key, value, data in rows:
            try:
                payload = json.loads(data) if data else {}
            except ValueError:
                payload = {}
            result.append((timestamp, run, kind, key, value,
                           payload if isinstance(payload, dict) else {}))
        return result

    def reset_records(self):
        """Bestenliste loeschen (auch auf den anderen Geraeten beim Abgleich)."""
        conn = None
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            for table in RECORD_TABLES:
                cur.execute("DELETE FROM " + table)
            marker, self.last_clock_fix = self._marker_now(cur)
            # Ab 0.63.2 (B-G-17): Marke eine Sekunde frueher (Zone bleibt).
            # Das Spiel traegt den laufenden Spielstand gleich danach neu ein,
            # oft in derselben Sekunde - mit "nicht nach der Marke = weg"
            # entfernte der naechste Abgleich ihn sonst wieder (auch auf
            # Geraeten mit aelterer Version, die die Marke so uebernehmen).
            marker = (datetime.datetime.strptime(marker[:19], "%Y-%m-%d %H:%M:%S")
                      - datetime.timedelta(seconds=1)).strftime(
                          "%Y-%m-%d %H:%M:%S") + marker[19:]
            cur.execute("INSERT OR REPLACE INTO sync_meta (key, value) VALUES (?, ?)",
                        ("bestenliste_reset_at", marker))
            conn.commit()
            return True
        except sqlite3.Error as exc:
            self._report("Bestenliste loeschen fehlgeschlagen: %s" % exc)
            return False
        finally:
            if conn is not None:
                conn.close()

    # -- Loeschen -----------------------------------------------------------

    # Der Zeitpunkt des Loeschens wird in sync_meta vermerkt: Der Abgleich
    # loescht damit auch auf den anderen Geraeten alles, was davor lag.

    def clear_history(self):
        conn = None
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            for table in HISTORY_TABLES:
                cur.execute("DELETE FROM " + table)
            marker, self.last_clock_fix = self._marker_now(cur)
            cur.execute("INSERT OR REPLACE INTO sync_meta (key, value) VALUES (?, ?)",
                        ("history_cleared_at", marker))
            conn.commit()
            return True
        except sqlite3.Error as exc:
            self._report(str(exc))
            return False
        finally:
            if conn is not None:
                conn.close()

    def reset_all(self):
        conn = None
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            for table in EVENT_TABLES:
                cur.execute("DELETE FROM " + table)
            marker, self.last_clock_fix = self._marker_now(cur)
            cur.execute("INSERT OR REPLACE INTO sync_meta (key, value) VALUES (?, ?)",
                        ("reset_at", marker))
            conn.commit()
            return True
        except sqlite3.Error as exc:
            self._report("Zuruecksetzen fehlgeschlagen: %s" % exc)
            return False
        finally:
            if conn is not None:
                conn.close()

    def reset_game(self):
        """Spielstand zuruecksetzen (Profil, Geld, Reputation, Tickets). Der
        Lernfortschritt bleibt unberuehrt."""
        conn = None
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            for table in GAME_TABLES:
                cur.execute("DELETE FROM " + table)
            marker, self.last_clock_fix = self._marker_now(cur)
            cur.execute("INSERT OR REPLACE INTO sync_meta (key, value) VALUES (?, ?)",
                        ("spiel_reset_at", marker))
            conn.commit()
            return True
        except sqlite3.Error as exc:
            self._report("Spielstand zuruecksetzen fehlgeschlagen: %s" % exc)
            return False
        finally:
            if conn is not None:
                conn.close()

    # -- Lesen: Testhistorie ------------------------------------------------

    def get_all_results(self):
        return self._execute(
            "SELECT timestamp, score, total, percentage, note, duration_seconds"
            " FROM test_results ORDER BY id DESC",
            fetch="all", default=[]) or []

    def get_stats(self):
        row = self._execute(
            "SELECT COUNT(*), AVG(percentage) FROM test_results",
            fetch="one", default=(0, 0.0))
        if not row:
            return 0, 0.0
        return row[0] or 0, row[1] or 0.0

    # -- Lesen: Kennzahlen fuer das Dashboard -------------------------------

    def distinct_cards_learned(self):
        row = self._execute(
            "SELECT COUNT(DISTINCT question) FROM card_events", fetch="one", default=(0,))
        return (row[0] if row else 0) or 0

    def count_card_events(self):
        row = self._execute("SELECT COUNT(*) FROM card_events", fetch="one", default=(0,))
        return (row[0] if row else 0) or 0

    def count_quiz_answers(self):
        row = self._execute("SELECT COUNT(*) FROM quiz_answers", fetch="one", default=(0,))
        return (row[0] if row else 0) or 0

    def distinct_quiz_questions(self):
        row = self._execute(
            "SELECT COUNT(DISTINCT question) FROM quiz_answers", fetch="one", default=(0,))
        return (row[0] if row else 0) or 0

    def distinct_scenarios(self):
        row = self._execute(
            "SELECT COUNT(DISTINCT scenario_index) FROM scenario_events", fetch="one", default=(0,))
        return (row[0] if row else 0) or 0

    def distinct_ap1(self):
        row = self._execute(
            "SELECT COUNT(DISTINCT scenario_index) FROM ap1_events", fetch="one", default=(0,))
        return (row[0] if row else 0) or 0

    def distinct_projects(self):
        row = self._execute(
            "SELECT COUNT(DISTINCT project_index) FROM project_events", fetch="one", default=(0,))
        return (row[0] if row else 0) or 0

    def completed_projects(self):
        """Menge der Indizes bereits bearbeiteter Testprojekte."""
        return self.completed_indices("project_events")

    def completed_indices(self, table):
        """Menge der Indizes bereits bearbeiteter Szenarien bzw. Testprojekte
        (table: scenario_events, ap1_events oder project_events)."""
        column = {"scenario_events": "scenario_index", "ap1_events": "scenario_index",
                  "project_events": "project_index"}[table]
        rows = self._execute(
            "SELECT DISTINCT %s FROM %s" % (column, table), fetch="all", default=[]) or []
        return {row[0] for row in rows}

    def question_results(self):
        """Alle Antworten je Frage bzw. Aufgabe, aelteste zuerst (ab 0.39):
        {(quelle, schluessel): [(timestamp, True/False/None), ...]}.
        quelle ist eine aus SOURCES, schluessel der Fragetext (Karteikarte,
        Quiz) bzw. die Position in der Liste (AP1, AP2, Testprojekt).
        None heisst angesehen, aber nicht bewertet."""
        queries = [
            (SRC_CARD, "SELECT timestamp, question, correct FROM card_events"),
            (SRC_QUIZ, "SELECT timestamp, question, correct FROM quiz_answers"),
            (SRC_AP1, "SELECT timestamp, scenario_index, correct FROM ap1_events"),
            (SRC_AP2, "SELECT timestamp, scenario_index, correct FROM scenario_events"),
            (SRC_PROJECT, "SELECT timestamp, project_index, correct FROM project_events"),
        ]
        results = {}
        for source, sql in queries:
            rows = self._execute(sql + " ORDER BY timestamp, id", fetch="all",
                                 default=[]) or []
            for timestamp, key, correct in rows:
                value = None if correct is None else bool(correct)
                results.setdefault((source, key), []).append((timestamp, value))
        return results

    def quiz_success_rate(self):
        """Erfolgsquote ueber alle je beantworteten Quizfragen in Prozent."""
        row = self._execute(
            "SELECT COUNT(*), SUM(correct) FROM quiz_answers", fetch="one", default=(0, 0))
        if not row or not row[0]:
            return 0.0, 0, 0
        total = row[0]
        correct = row[1] or 0
        return (correct / total) * 100.0, correct, total

    def category_stats(self):
        """Antworten und Treffer je Fachbereich, ueber Karten und Quiz hinweg."""
        stats = {cat: {"answered": 0, "correct": 0} for cat in CATEGORIES}
        rows = self._execute(
            "SELECT category, COUNT(*), SUM(correct) FROM ("
            "  SELECT category, correct FROM quiz_answers"
            "  UNION ALL"
            "  SELECT category, correct FROM card_events WHERE correct IS NOT NULL"
            ") GROUP BY category", fetch="all", default=[]) or []
        for category, answered, correct in rows:
            if category in stats:
                stats[category]["answered"] = answered or 0
                stats[category]["correct"] = correct or 0
        return stats

    def category_coverage(self, totals):
        """Anteil der je Fachbereich bereits angefassten Inhalte in Prozent."""
        coverage = {}
        rows = self._execute(
            "SELECT category, COUNT(DISTINCT question) FROM ("
            "  SELECT category, question FROM quiz_answers"
            "  UNION"
            "  SELECT category, question FROM card_events"
            ") GROUP BY category", fetch="all", default=[]) or []
        seen = {row[0]: row[1] for row in rows}
        for cat in CATEGORIES:
            total = max(1, totals.get(cat, 1))
            coverage[cat] = min(100.0, (seen.get(cat, 0) / total) * 100.0)
        return coverage

    def daily_counts(self, days=14):
        """Aktivitaeten pro Tag fuer die letzten n Tage (inklusive heute)."""
        today = datetime.date.today()
        start = today - datetime.timedelta(days=days - 1)
        rows = self._execute(
            "SELECT substr(timestamp, 1, 10) AS tag, COUNT(*) FROM ("
            "  SELECT timestamp FROM card_events"
            "  UNION ALL SELECT timestamp FROM quiz_answers"
            "  UNION ALL SELECT timestamp FROM scenario_events"
            "  UNION ALL SELECT timestamp FROM project_events"
            "  UNION ALL SELECT timestamp FROM ap1_events"
            "  UNION ALL SELECT timestamp FROM trainer_aufgaben"
            ") WHERE substr(timestamp, 1, 10) >= ? GROUP BY tag",
            (start.isoformat(),), fetch="all", default=[]) or []
        lookup = {row[0]: row[1] for row in rows}
        series = []
        for offset in range(days):
            day = start + datetime.timedelta(days=offset)
            series.append((day, lookup.get(day.isoformat(), 0)))
        return series

    def category_daily(self, days=14):
        """Aktivitaeten pro Fachbereich und Tag - Grundlage fuer die Heatmap."""
        today = datetime.date.today()
        start = today - datetime.timedelta(days=days - 1)
        rows = self._execute(
            "SELECT category, substr(timestamp, 1, 10) AS tag, COUNT(*) FROM ("
            "  SELECT category, timestamp FROM card_events"
            "  UNION ALL SELECT category, timestamp FROM quiz_answers"
            ") WHERE substr(timestamp, 1, 10) >= ? GROUP BY category, tag",
            (start.isoformat(),), fetch="all", default=[]) or []
        matrix = {cat: [0] * days for cat in CATEGORIES}
        for category, tag, count in rows:
            if category not in matrix:
                continue
            try:
                day = datetime.date.fromisoformat(tag)
            except ValueError:
                continue
            index = (day - start).days
            if 0 <= index < days:
                matrix[category][index] = count
        return matrix

    # -- Themen (ab 0.37) ----------------------------------------------------
    # Das Thema einer Antwort steht nicht in der Datenbank, sondern ergibt
    # sich aus der Frage (event_topic). source: 1 = Karteikarte, 0 = Quiz.

    def topic_answers(self, window):
        """Die neuesten Antworten je Thema: {thema: [True/False, ...]},
        neueste zuerst, hoechstens window je Thema."""
        rows = self._execute(
            "SELECT src, question, correct FROM ("
            "  SELECT timestamp, id, 0 AS src, question, correct FROM quiz_answers"
            "  UNION ALL"
            "  SELECT timestamp, id, 1 AS src, question, correct FROM card_events"
            "  WHERE correct IS NOT NULL"
            ") ORDER BY timestamp DESC, id DESC", fetch="all", default=[]) or []
        answers = {}
        for source, question, correct in rows:
            topic = event_topic(source, question)
            if topic is None:
                continue
            bucket = answers.setdefault(topic, [])
            if len(bucket) < window:
                bucket.append(bool(correct))
        return answers

    def topic_stats(self):
        """Antworten und Treffer je Thema, ueber Karten und Quiz hinweg."""
        stats = {topic: {"answered": 0, "correct": 0} for topic in TOPIC_ORDER}
        rows = self._execute(
            "SELECT src, question, COUNT(*), SUM(correct) FROM ("
            "  SELECT 0 AS src, question, correct FROM quiz_answers"
            "  UNION ALL"
            "  SELECT 1 AS src, question, correct FROM card_events WHERE correct IS NOT NULL"
            ") GROUP BY src, question", fetch="all", default=[]) or []
        for source, question, answered, correct in rows:
            topic = event_topic(source, question)
            if topic in stats:
                stats[topic]["answered"] += answered or 0
                stats[topic]["correct"] += correct or 0
        return stats

    def topic_coverage(self, totals):
        """Anteil der je Thema bereits angefassten Inhalte in Prozent."""
        rows = self._execute(
            "SELECT DISTINCT 0, question FROM quiz_answers"
            " UNION SELECT DISTINCT 1, question FROM card_events",
            fetch="all", default=[]) or []
        seen = {}
        for source, question in rows:
            topic = event_topic(source, question)
            if topic is not None:
                seen[topic] = seen.get(topic, 0) + 1
        return {topic: min(100.0, seen.get(topic, 0) / float(max(1, totals.get(topic, 1)))
                           * 100.0) for topic in TOPIC_ORDER}

    def topic_daily(self, category, days=14):
        """Aktivitaeten je Thema eines Fachbereichs und Tag (Heatmap-Reinzoom)."""
        today = datetime.date.today()
        start = today - datetime.timedelta(days=days - 1)
        rows = self._execute(
            "SELECT src, question, substr(timestamp, 1, 10) AS tag, COUNT(*) FROM ("
            "  SELECT 1 AS src, question, category, timestamp FROM card_events"
            "  UNION ALL SELECT 0, question, category, timestamp FROM quiz_answers"
            ") WHERE category = ? AND substr(timestamp, 1, 10) >= ?"
            " GROUP BY src, question, tag",
            (category, start.isoformat()), fetch="all", default=[]) or []
        matrix = {topic: [0] * days for topic in TOPICS.get(category, [])}
        for source, question, tag, count in rows:
            topic = event_topic(source, question)
            if topic not in matrix:
                continue
            try:
                index = (datetime.date.fromisoformat(tag) - start).days
            except ValueError:
                continue
            if 0 <= index < days:
                matrix[topic][index] += count
        return matrix

    def month_activity(self, year, month):
        """Alle Tage eines Monats, an denen gelernt wurde."""
        prefix = "%04d-%02d" % (year, month)
        rows = self._execute(
            "SELECT DISTINCT substr(timestamp, 1, 10) FROM ("
            "  SELECT timestamp FROM card_events"
            "  UNION ALL SELECT timestamp FROM quiz_answers"
            "  UNION ALL SELECT timestamp FROM scenario_events"
            "  UNION ALL SELECT timestamp FROM project_events"
            "  UNION ALL SELECT timestamp FROM ap1_events"
            "  UNION ALL SELECT timestamp FROM test_results"
            ") WHERE substr(timestamp, 1, 7) = ?",
            (prefix,), fetch="all", default=[]) or []
        days = set()
        for (value,) in rows:
            try:
                days.add(int(value[8:10]))
            except (ValueError, IndexError):
                pass
        return days

    def recent_activities(self, limit=12):
        """Die juengsten Lernaktivitaeten als Liste fuer das Dashboard."""
        rows = self._execute(
            "SELECT timestamp, art, detail, extra FROM ("
            "  SELECT timestamp, 'Karteikarte' AS art, category AS detail,"
            "         CASE WHEN correct IS NULL THEN 'angesehen'"
            "              WHEN correct = 1 THEN 'richtig' ELSE 'falsch' END AS extra"
            "  FROM card_events"
            "  UNION ALL"
            "  SELECT timestamp, 'Prüfungsfrage', category,"
            "         CASE WHEN correct = 1 THEN 'richtig' ELSE 'falsch' END"
            "  FROM quiz_answers"
            "  UNION ALL"
            "  SELECT timestamp, 'AP2-Szenario', theme, 'bearbeitet'"
            "  FROM scenario_events"
            "  UNION ALL"
            "  SELECT timestamp, 'Testprojekt', category, 'bearbeitet'"
            "  FROM project_events"
            "  UNION ALL"
            "  SELECT timestamp, 'AP1-Szenario', theme, 'bearbeitet'"
            "  FROM ap1_events"
            "  UNION ALL"
            "  SELECT timestamp, 'Test-Session', note,"
            "         CAST(score AS TEXT) || ' / ' || CAST(total AS TEXT)"
            "  FROM test_results"
            ") ORDER BY timestamp DESC LIMIT ?",
            (limit,), fetch="all", default=[]) or []
        return rows

    def theme_progress(self, theme_totals, themes=AP2_THEMES, table="scenario_events"):
        """Fortschritt je Themenblock in Prozent (AP2 per Default, AP1 ueber
        themes=AP1_THEMES, table='ap1_events' aufrufbar)."""
        table = table if table in ("scenario_events", "ap1_events") else "scenario_events"
        rows = self._execute(
            "SELECT theme, COUNT(DISTINCT scenario_index) FROM %s GROUP BY theme" % table,
            fetch="all", default=[]) or []
        done = {}
        for theme, count in rows:
            block = theme_block(theme)
            done[block] = done.get(block, 0) + count
        progress = {}
        for theme in themes:
            total = max(1, theme_totals.get(theme, 1))
            progress[theme] = min(100.0, (done.get(theme, 0) / total) * 100.0)
        return progress

    def streak(self, today=None):
        """Anzahl der aufeinanderfolgenden Tage mit Lernaktivitaet. Ab 0.53
        dieselbe Zaehlung wie die Kachel "Heute" (Tagesziel): nur bewertete
        Aufgaben (activity_days), Eintraege mit spaeterem Datum zaehlen nicht."""
        return learning_streak({day for day, count in self.activity_days().items() if count},
                               today)


# ============================================================================
#  LERNINHALTE LADEN
# ============================================================================
#
# Saemtliche Lerninhalte stehen als JSON-Dateien im Ordner "inhalte" - dort
# lassen sie sich leichter erweitern und spaeter auch von anderen Programmen
# (z.B. einer Handy-App) nutzen. Mehrzeilige Texte sind dort als Liste von
# Zeilen gespeichert, der Fachbereich als Kurzname.

CONTENT_DIR = os.path.join(getattr(sys, "_MEIPASS", BASE_DIR), "inhalte")

CATEGORY_KEYS = {
    "netzwerk": CAT_NET,
    "sicherheit": CAT_SEC,
    "systeme": CAT_SYS,
    "wirtschaft": CAT_BIZ,
    "datenbanken": CAT_DB,
}

# Felder, die in den JSON-Dateien auch als Liste von Zeilen stehen duerfen
TEXT_FIELDS = ("text", "solution", "ausgangssituation", "auftrag", "a_full", "exp")


def load_content(name):
    """Laedt inhalte/<name>.json und wandelt Kurznamen und Zeilenlisten um."""
    path = os.path.join(CONTENT_DIR, name + ".json")
    with open(path, encoding="utf-8") as handle:
        items = json.load(handle)
    for item in items:
        item["cat"] = CATEGORY_KEYS[item["cat"]]
        for field in TEXT_FIELDS:
            if isinstance(item.get(field), list):
                item[field] = "\n".join(item[field])
    return items


# ============================================================================
#  LERNINHALTE: KARTEIKARTEN
# ============================================================================

KARTEIKARTEN = load_content("karteikarten")


# ============================================================================
#  LERNINHALTE: QUIZFRAGEN
# ============================================================================

def build_quiz_database():
    """Baut den Fragenkatalog auf - feste Fragen plus generierte Aufgaben."""
    db = load_content("quizfragen")

    # Automatisch erzeugte Subnetz-Aufgaben
    prefix_table = {
        24: ("255.255.255.0", 254), 25: ("255.255.255.128", 126),
        26: ("255.255.255.192", 62), 27: ("255.255.255.224", 30),
        28: ("255.255.255.240", 14), 29: ("255.255.255.248", 6),
        30: ("255.255.255.252", 2),
    }
    all_masks = [m for m, _h in prefix_table.values()]
    all_hosts = [h for _m, h in prefix_table.values()]
    for prefix, (mask, hosts) in prefix_table.items():
        mask_distractors = [m for m in all_masks if m != mask]
        mask_wrong = random.Random(mask).sample(mask_distractors, 3)
        db.append({
            "cat": CAT_NET, "thema": "ipv4",
            "q": "Wie lautet die Subnetzmaske für die CIDR-Notation /%d?" % prefix,
            "options": [mask] + mask_wrong,
            "a": mask,
            "exp": "/%d entspricht der Maske %s." % (prefix, mask),
        })
        host_distractors = sorted({h for h in all_hosts if h != hosts})
        host_wrong = random.Random(str(hosts)).sample(host_distractors, min(3, len(host_distractors)))
        db.append({
            "cat": CAT_NET, "thema": "ipv4",
            "q": "Wie viele nutzbare Host-IP-Adressen bietet ein Subnetz mit /%d?" % prefix,
            "options": [str(hosts)] + [str(h) for h in host_wrong],
            "a": str(hosts),
            "exp": "2^(32 - %d) minus 2 (Netzwerk-Adresse und Broadcast) = %d Hosts." % (prefix, hosts),
        })

    # Automatisch erzeugte Port-Aufgaben
    ports = [
        ("20/21", "FTP"), ("22", "SSH / SFTP"), ("23", "Telnet"), ("25", "SMTP"),
        ("53", "DNS"), ("67/68", "DHCP"), ("80", "HTTP"), ("110", "POP3"),
        ("123", "NTP"), ("143", "IMAP"), ("161/162", "SNMP"), ("389", "LDAP"),
        ("443", "HTTPS"), ("445", "SMB"), ("636", "LDAPS"), ("3389", "RDP"),
    ]
    for port, service in ports:
        distractors = [s for _p, s in ports if s != service]
        wrong = random.Random(port).sample(distractors, 3)
        db.append({
            "cat": CAT_NET, "thema": "dienste",
            "q": "Welcher Standard-Dienst verwendet primär den Port %s?" % port,
            "options": [service] + wrong,
            "a": service,
            "exp": "Der TCP/UDP-Port %s gehört standardmäßig zu %s." % (port, service),
        })

    # Automatisch erzeugte Aufgaben: Sicherheits-Abkuerzungen
    sec_abbr = [
        ("VPN", "Virtual Private Network"), ("IDS", "Intrusion Detection System"),
        ("IPS", "Intrusion Prevention System"), ("MFA", "Multi-Factor Authentication"),
        ("WAF", "Web Application Firewall"), ("DLP", "Data Loss Prevention"),
        ("CERT", "Computer Emergency Response Team"), ("SOC", "Security Operations Center"),
    ]
    sec_topic = {"VPN": "netzsicherheit", "IDS": "netzsicherheit", "IPS": "netzsicherheit",
                 "MFA": "zugriff", "WAF": "netzsicherheit", "DLP": "datenschutz",
                 "CERT": "notfall", "SOC": "haertung"}
    for abbr, meaning in sec_abbr:
        distractors = [m for _a, m in sec_abbr if m != meaning]
        wrong = random.Random(abbr).sample(distractors, 3)
        db.append({
            "cat": CAT_SEC, "thema": sec_topic[abbr],
            "q": "Wofür steht die Abkürzung %s im Sicherheitskontext?" % abbr,
            "options": [meaning] + wrong,
            "a": meaning,
            "exp": "%s steht für %s." % (abbr, meaning),
        })

    # Automatisch erzeugte Aufgaben: RAID-Level-Eigenschaften
    raid_levels = [
        ("RAID 0", "Striping ohne Redundanz - maximale Performance, kein Ausfallschutz", 2),
        ("RAID 1", "Spiegelung (Mirroring) - volle Redundanz, halbierte Nutzkapazität", 2),
        ("RAID 5", "Striping mit verteilter einfacher Parität - 1 Plattenausfall verkraftbar", 3),
        ("RAID 6", "Striping mit verteilter doppelter Parität - 2 Plattenausfälle verkraftbar", 4),
        ("RAID 10", "Kombination aus Spiegelung und Striping - hohe Performance und Redundanz", 4),
    ]
    for level, description, min_disks in raid_levels:
        desc_distractors = [d for _l, d, _m in raid_levels if d != description]
        desc_wrong = random.Random(level + "d").sample(desc_distractors, 3)
        db.append({
            "cat": CAT_SYS, "thema": "storage",
            "q": "Welche Eigenschaft beschreibt %s am besten?" % level,
            "options": [description] + desc_wrong,
            "a": description,
            "exp": "%s: %s." % (level, description),
        })
        disk_counts = sorted({m for _l, _d, m in raid_levels})
        disk_wrong = [str(n) for n in disk_counts if n != min_disks][:3]
        while len(disk_wrong) < 3:
            disk_wrong.append(str(min_disks + len(disk_wrong) + 1))
        db.append({
            "cat": CAT_SYS, "thema": "storage",
            "q": "Wie viele Festplatten werden für %s mindestens benötigt?" % level,
            "options": [str(min_disks)] + disk_wrong,
            "a": str(min_disks),
            "exp": "%s benötigt mindestens %d Festplatten." % (level, min_disks),
        })

    # Automatisch erzeugte Aufgaben: Wirtschafts-Abkuerzungen
    biz_abbr = [
        ("EBIT", "Earnings Before Interest and Taxes"), ("USt.", "Umsatzsteuer"),
        ("BGB", "Bürgerliches Gesetzbuch"), ("HGB", "Handelsgesetzbuch"),
        ("AGB", "Allgemeine Geschäftsbedingungen"), ("WBS", "Work Breakdown Structure"),
        ("MVP", "Minimum Viable Product"), ("JIT", "Just in Time"),
    ]
    biz_topic = {"EBIT": "kalkulation", "USt.": "kalkulation", "BGB": "recht",
                 "HGB": "recht", "AGB": "recht", "WBS": "projekt", "MVP": "projekt",
                 "JIT": "beschaffung"}
    for abbr, meaning in biz_abbr:
        distractors = [m for _a, m in biz_abbr if m != meaning]
        wrong = random.Random(abbr).sample(distractors, 3)
        db.append({
            "cat": CAT_BIZ, "thema": biz_topic[abbr],
            "q": "Wofür steht die Abkürzung %s im wirtschaftlichen Kontext?" % abbr,
            "options": [meaning] + wrong,
            "a": meaning,
            "exp": "%s steht für %s." % (abbr, meaning),
        })

    # Erzeugte Aufgaben duerfen feste Fragen nicht doppeln (z.B. die
    # Mindestanzahl Platten fuer RAID 5/6 steht auch in quizfragen.json)
    unique, seen = [], set()
    for question in db:
        key = question["q"].strip().lower()
        if key not in seen:
            seen.add(key)
            unique.append(question)
    return unique


QUIZ_QUESTIONS = build_quiz_database()


def load_question_renames():
    """Alte -> neue Fragetexte aus inhalte/umbenennungen.json (ab 0.53).

    Karteikarten und Quizfragen werden im Lernstand ueber ihren Fragetext
    gefuehrt. Wird ein Fragetext korrigiert, uebertraegt diese Liste die
    vorhandenen Antworten auf den neuen Text - auch Antworten, die spaeter
    noch per Abgleich von einem Geraet mit aelterer Version kommen."""
    try:
        with open(os.path.join(CONTENT_DIR, "umbenennungen.json"),
                  encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return {"card_events": dict(data.get("karte") or {}),
            "quiz_answers": dict(data.get("quiz") or {})}


QUESTION_RENAMES = load_question_renames()


# ============================================================================
#  LERNINHALTE: AP2-SZENARIEN
# ============================================================================

SZENARIEN = load_content("szenarien_ap2")


# ============================================================================
#  LERNINHALTE: AP1-SZENARIEN (GRUNDLAGENPRUEFUNG)
# ============================================================================
#
# Die AP1 (gestreckte Abschlusspruefung, Teil 1) prueft die Grundlagen aus
# dem 1. und 2. Lehrjahr - im Gegensatz zur AP2 noch ohne Schwerpunkt auf
# komplexe Netzwerk-/Sicherheitskonzeption. Die Aufgaben hier sind bewusst
# einfacher und grundlagenorientierter gehalten als die AP2-Szenarien oben.

AP1_SZENARIEN = load_content("szenarien_ap1")


# ============================================================================
#  LERNINHALTE: TESTPROJEKTE (PROJEKTARBEIT UEBEN)
# ============================================================================
#
# Anders als die kurzen AP2-Szenarien oben simulieren die Testprojekte einen
# kompletten Kundenauftrag, wie er als Grundlage fuer einen Projektantrag
# (z.B. zur AP2-Projektdokumentation) dienen koennte: Ausgangssituation,
# Auftrag, Rahmenbedingungen und eine Reihe von Arbeitsauftraegen, die die
# ueblichen Bestandteile einer Projektarbeit abdecken (Ist-Analyse,
# Konzeption, Zeit- und Kostenplanung, Risiken, Qualitaetssicherung).
# Die "hinweise" sind bewusst keine fertigen Musterloesungen, sondern
# Loesungsansaetze zum Vergleich nach der eigenen Bearbeitung.

PROJEKTARBEITEN = load_content("projektarbeiten")


# ============================================================================
#  THEMEN JE FACHBEREICH (AB 0.37)
# ============================================================================
#
# Jeder Fachbereich ist in Themen unterteilt (inhalte/themen.json). Jeder
# Lerninhalt traegt im Feld "thema" die Kennung seines Themas. Der
# Wissensstand je Thema wird - wie der je Fachbereich - aus den vorhandenen
# Antworten berechnet: gespeichert wird weiterhin nur die Frage, ihr Thema
# ergibt sich ueber CARD_TOPIC/QUIZ_TOPIC. So zaehlen auch alle Antworten aus
# der Zeit vor 0.37 sofort je Thema.

def _load_topics():
    with open(os.path.join(CONTENT_DIR, "themen.json"), encoding="utf-8") as handle:
        data = json.load(handle)["themen"]
    return {CATEGORY_KEYS[key]: entries for key, entries in data.items()}


_TOPIC_DATA = _load_topics()

# Fachbereich (voller Name) -> Themenkennungen in fester Reihenfolge
TOPICS = {cat: [entry["id"] for entry in _TOPIC_DATA.get(cat, [])] for cat in CATEGORIES}
TOPIC_NAME = {entry["id"]: entry["name"] for entries in _TOPIC_DATA.values()
              for entry in entries}
TOPIC_SHORT = {entry["id"]: entry["kurz"] for entries in _TOPIC_DATA.values()
               for entry in entries}
TOPIC_CAT = {topic: cat for cat, topics in TOPICS.items() for topic in topics}
TOPIC_ORDER = [topic for cat in CATEGORIES for topic in TOPICS[cat]]

# Frage -> Thema, getrennt nach Karteikarten und Quizfragen (so werden die
# Antworten in card_events und quiz_answers zugeordnet)
CARD_TOPIC = {card["q"]: card.get("thema") for card in KARTEIKARTEN}
QUIZ_TOPIC = {question["q"]: question.get("thema") for question in QUIZ_QUESTIONS}


def event_topic(source, question):
    """Thema einer gespeicherten Antwort (source 1 = Karteikarte, 0 = Quiz)."""
    return (CARD_TOPIC if source else QUIZ_TOPIC).get(question)


# ============================================================================
#  ABGELEITETE KENNZAHLEN
# ============================================================================

def validate_content():
    """Prueft alle Lerninhalte auf formale Fehler, z.B. nach dem Ergaenzen
    neuer Fragen. Liefert eine Liste von Meldungen - leer heisst: alles in
    Ordnung. build.py und der Starttest brechen bei Fehlern ab."""
    problems = []

    def check(items, label, fields, choice=False):
        seen = set()
        for number, item in enumerate(items, start=1):
            where = "%s Nr. %d" % (label, number)
            for field in fields:
                if not item.get(field):
                    problems.append("%s: Feld '%s' fehlt oder ist leer" % (where, field))
            key = (item.get("q") or item.get("title") or "").strip().lower()
            if key in seen:
                problems.append("%s: doppelt vorhanden (%s)" % (where, key[:60]))
            seen.add(key)
            if choice:
                options = item.get("options") or []
                if len(options) != 4 or len(set(options)) != 4:
                    problems.append("%s: braucht genau 4 verschiedene Antworten" % where)
                if item.get("a") not in options:
                    problems.append("%s: richtige Antwort steht nicht in den Optionen" % where)

    check(KARTEIKARTEN, "Karteikarte", ("cat", "q", "a", "a_full", "options"), choice=True)
    check(QUIZ_QUESTIONS, "Quizfrage", ("cat", "q", "a", "exp", "options"), choice=True)
    check(SZENARIEN, "AP2-Szenario", ("cat", "title", "theme", "text", "solution"))
    check(AP1_SZENARIEN, "AP1-Szenario", ("cat", "title", "theme", "text", "solution"))
    check(PROJEKTARBEITEN, "Testprojekt",
          ("cat", "title", "branche", "schwierigkeit", "ausgangssituation", "auftrag",
           "rahmenbedingungen", "aufgaben", "hinweise"))

    for label, items in (("Karteikarte", KARTEIKARTEN), ("Quizfrage", QUIZ_QUESTIONS),
                         ("AP2-Szenario", SZENARIEN), ("AP1-Szenario", AP1_SZENARIEN),
                         ("Testprojekt", PROJEKTARBEITEN)):
        for number, item in enumerate(items, start=1):
            if item.get("thema") not in TOPICS.get(item.get("cat"), ()):
                problems.append("%s Nr. %d: Thema '%s' fehlt oder gehoert nicht zum "
                                "Fachbereich (inhalte/themen.json)"
                                % (label, number, item.get("thema")))

    for number, scenario in enumerate(SZENARIEN, start=1):
        if theme_block(scenario.get("theme")) not in AP2_THEMES:
            problems.append("AP2-Szenario Nr. %d: unbekanntes Thema '%s' (AP2_THEMES "
                            "oder THEME_BLOCK ergaenzen)" % (number, scenario.get("theme")))
    for number, scenario in enumerate(AP1_SZENARIEN, start=1):
        if theme_block(scenario.get("theme")) not in AP1_THEMES:
            problems.append("AP1-Szenario Nr. %d: unbekanntes Thema '%s'"
                            % (number, scenario.get("theme")))
    for number, project in enumerate(PROJEKTARBEITEN, start=1):
        if len(project.get("aufgaben", [])) != len(project.get("hinweise", [])):
            problems.append("Testprojekt Nr. %d: je Aufgabe wird genau ein Hinweis "
                            "gebraucht" % number)

    # Ausbildungsrahmenplan (ab 0.55)
    from fisi_rahmenplan import validate_rahmenplan
    problems.extend(validate_rahmenplan())

    # Inhalte des Lernspiels (inhalte/spiel/)
    from fisi_game import validate_game_content
    problems.extend(validate_game_content())
    return problems


# Ab 0.55: Feld neu angehaengter Karten und Quizfragen mit der Version, z.B.
# "neu_ab": "0.55". Das Spiel zaehlt sie erst, wenn sie bearbeitet wurden
# (fisi_game.game_items), damit ein Update keinen Spielstand senkt.
NEW_SINCE_FIELD = "neu_ab"


def content_totals():
    """Anzahl verfuegbarer Inhalte je Fachbereich (Karten + Quizfragen)."""
    totals = {cat: 0 for cat in CATEGORIES}
    for card in KARTEIKARTEN:
        totals[card["cat"]] = totals.get(card["cat"], 0) + 1
    for question in QUIZ_QUESTIONS:
        totals[question["cat"]] = totals.get(question["cat"], 0) + 1
    return totals


def topic_totals():
    """Anzahl verfuegbarer Inhalte je Thema (Karten + Quizfragen)."""
    totals = {topic: 0 for topic in TOPIC_ORDER}
    for item in KARTEIKARTEN + QUIZ_QUESTIONS:
        if item.get("thema") in totals:
            totals[item["thema"]] += 1
    return totals


def theme_totals():
    """Anzahl Szenarien je AP2-Themenblock."""
    totals = {}
    for scenario in SZENARIEN:
        block = theme_block(scenario["theme"])
        totals[block] = totals.get(block, 0) + 1
    return totals


def ap1_theme_totals():
    """Anzahl Szenarien je AP1-Themenblock."""
    totals = {}
    for scenario in AP1_SZENARIEN:
        block = theme_block(scenario["theme"])
        totals[block] = totals.get(block, 0) + 1
    return totals


# ============================================================================
#  LERNSTAND JE FRAGE (AB 0.39)
# ============================================================================
#
# Jede Frage bzw. Aufgabe des Fragenpools hat genau einen von drei Zustaenden.
# Er wird - wie der Wissensstand - bei Bedarf aus den gespeicherten Antworten
# berechnet und nie selbst gespeichert. Damit gilt er nach einem Abgleich
# automatisch auch auf dem anderen Geraet.
#
#   Offen          noch nie bewertet (oder erst einmal richtig, ohne Fehler)
#   Zu ueben       zuletzt falsch (rot) oder nach einem Fehler erst einmal
#                  richtig (gelb)
#   Abgeschlossen  die letzten DONE_STREAK Antworten richtig; ein spaeterer
#                  Fehler setzt die Frage wieder auf "Zu ueben"

SRC_CARD = "karte"
SRC_QUIZ = "quiz"
SRC_AP1 = "ap1"
SRC_AP2 = "ap2"
SRC_PROJECT = "projekt"
SOURCES = [SRC_CARD, SRC_QUIZ, SRC_AP1, SRC_AP2, SRC_PROJECT]
# Ab 0.60 (K-B): Anzeigename einer Frage des Pruefungstrainers in Suche,
# Aktivitaeten und Notizblock (vorher "Quizfrage"); nur Anzeige, nicht gespeichert
KIND_QUIZ = "Prüfungsfrage"
SOURCE_NAME = {SRC_CARD: "Karteikarte", SRC_QUIZ: KIND_QUIZ, SRC_AP1: "AP1-Szenario",
               SRC_AP2: "AP2-Szenario", SRC_PROJECT: "Testprojekt"}
SOURCE_PLURAL = {SRC_CARD: "Karteikarten", SRC_QUIZ: "Prüfungsfragen", SRC_AP1: "AP1-Szenarien",
                 SRC_AP2: "AP2-Szenarien", SRC_PROJECT: "Testprojekte"}

Q_OPEN = "offen"
Q_PRACTICE = "ueben"
Q_DONE = "fertig"
LEVEL_RED = "rot"
LEVEL_YELLOW = "gelb"
Q_STATUS_NAME = {Q_OPEN: "Offen", Q_PRACTICE: "Zu üben", Q_DONE: "Abgeschlossen"}
# Auswahl der Status-Reiter: (Wert, Anzeige)
Q_STATUS_TABS = [(FILTER_ALL, "Alle"), (Q_OPEN, "Offen"), (Q_PRACTICE, "Zu üben"),
                 (Q_DONE, "Abgeschlossen")]
DONE_STREAK = 2
# Beim normalen Weiterlernen: auf NEW_PER_REPEAT unbearbeitete Fragen folgt
# eine Wiederholung (zuerst "Zu ueben", dann angefangene, dann abgeschlossene)
NEW_PER_REPEAT = 4


def question_status(results):
    """(status, stufe) aus den Antworten einer Frage, aelteste zuerst.
    results: True/False/None oder (timestamp, wert). stufe ist bei "Zu ueben"
    LEVEL_RED oder LEVEL_YELLOW, sonst ""."""
    values = [item[1] if isinstance(item, tuple) else item for item in results]
    values = [bool(value) for value in values if value is not None]
    if len(values) >= DONE_STREAK and all(values[-DONE_STREAK:]):
        return Q_DONE, ""
    if values and not values[-1]:
        return Q_PRACTICE, LEVEL_RED
    if False in values:
        return Q_PRACTICE, LEVEL_YELLOW
    return Q_OPEN, ""


class StatusBook:
    """Lernstand aller Fragen, einmal aus der Datenbank berechnet.
    Nach neuen Antworten einfach neu anlegen (StatusBook(db))."""

    def __init__(self, db=None, results=None):
        self.results = results if results is not None else \
            (db.question_results() if db is not None else {})
        self._cache = {}

    def status(self, source, key):
        """(status, stufe) einer Frage."""
        value = self._cache.get((source, key))
        if value is None:
            value = self._cache[(source, key)] = question_status(
                self.results.get((source, key), ()))
        return value

    def touched(self, source, key):
        """Wurde die Frage schon einmal bearbeitet (auch nur angesehen)?"""
        return bool(self.results.get((source, key)))

    def last_time(self, source, key):
        entries = self.results.get((source, key))
        return entries[-1][0] if entries else ""

    def streak(self, source, key):
        """Richtige Antworten in Folge (zuletzt)."""
        count = 0
        for _timestamp, value in reversed(self.results.get((source, key), ())):
            if value is None:
                continue
            if not value:
                break
            count += 1
        return count

    def counts(self, source, keys):
        """{status: Anzahl} fuer die Fragen keys."""
        result = {Q_OPEN: 0, Q_PRACTICE: 0, Q_DONE: 0}
        for key in keys:
            result[self.status(source, key)[0]] += 1
        return result

    def matches(self, source, key, status):
        return status in (None, FILTER_ALL) or self.status(source, key)[0] == status

    def preferred_order(self, source, keys, rng=None, fresh_order=None):
        """Reihenfolge fuers normale Weiterlernen: unbearbeitete Fragen
        zuerst, nach je NEW_PER_REPEAT davon eine Wiederholung zur Festigung.
        Wiederholt wird zuerst, was zu ueben ist (rot vor gelb), dann
        Angefangenes, zuletzt Abgeschlossenes. Mit rng werden die Gruppen
        gemischt (Pruefungstrainer), sonst bleibt die Reihenfolge von keys.
        fresh_order (ab 0.55, Gewichtung nach Rahmenplan) legt die
        Reihenfolge der unbearbeiteten Fragen fest; die Wiederholungen
        bleiben davon unberuehrt."""
        fresh, repeat = [], []
        for key in keys:
            if not self.touched(source, key):
                fresh.append(key)
            else:
                status, level = self.status(source, key)
                rank = {(Q_PRACTICE, LEVEL_RED): 0, (Q_PRACTICE, LEVEL_YELLOW): 1,
                        (Q_OPEN, ""): 2}.get((status, level), 3)
                repeat.append((rank, key))
        if rng is not None:
            rng.shuffle(fresh)
            rng.shuffle(repeat)
        if fresh_order is not None:
            fresh = fresh_order(fresh)
        repeat = [key for _rank, key in sorted(repeat, key=lambda item: item[0])]
        ordered = []
        while fresh or repeat:
            ordered += fresh[:NEW_PER_REPEAT]
            fresh = fresh[NEW_PER_REPEAT:]
            if repeat:
                ordered.append(repeat.pop(0))
            if not fresh:
                ordered += repeat
                repeat = []
        return ordered


def position_statuses(book, source):
    """{position: (status, stufe)} der bearbeiteten AP1-/AP2-Szenarien bzw.
    Testprojekte (fuer filter_positions)."""
    return {key: book.status(src, key) for (src, key) in book.results if src == source}


def status_label(book, source, key):
    """(Text, Farbschluessel) fuer die Anzeige an einer Frage. Farbschluessel:
    "offen", LEVEL_RED, LEVEL_YELLOW oder "fertig"."""
    status, level = book.status(source, key)
    streak = book.streak(source, key)
    if status == Q_DONE:
        return "Abgeschlossen · %d-mal in Folge richtig" % streak, "fertig"
    if status == Q_PRACTICE:
        if level == LEVEL_RED:
            return "Zu üben · zuletzt falsch", LEVEL_RED
        return "Zu üben · %d von %d richtig" % (streak, DONE_STREAK), LEVEL_YELLOW
    if streak:
        return "Offen · %d von %d richtig" % (streak, DONE_STREAK), "offen"
    if book.touched(source, key):
        return "Offen · angesehen, noch nicht bewertet", "offen"
    return "Offen · noch nicht bearbeitet", "offen"


def source_items(source):
    """[(schluessel, eintrag)] aller Fragen einer Quelle."""
    if source == SRC_CARD:
        return [(card["q"], card) for card in KARTEIKARTEN]
    if source == SRC_QUIZ:
        return [(question["q"], question) for question in QUIZ_QUESTIONS]
    data = {SRC_AP1: AP1_SZENARIEN, SRC_AP2: SZENARIEN, SRC_PROJECT: PROJEKTARBEITEN}[source]
    return list(enumerate(data))


def item_title(source, item):
    return item["q"] if source in (SRC_CARD, SRC_QUIZ) else item["title"]


def model_answer(source, item):
    """Musterantwort zum Nachlesen im Notizblock."""
    if source == SRC_CARD:
        return item["a_full"]
    if source == SRC_QUIZ:
        return "Richtig: %s\n%s" % (item["a"], item.get("exp", ""))
    if source == SRC_PROJECT:
        return "\n".join("%d. %s\n   Lösungsansatz: %s" % (number, task, hint)
                         for number, (task, hint) in
                         enumerate(zip(item["aufgaben"], item["hinweise"]), start=1))
    return item["solution"]


def notebook_entries(book, status=Q_PRACTICE, category=FILTER_ALL, topic=FILTER_ALL,
                     sources=None):
    """Eintraege des Notizblocks: alle Fragen mit dem Status status (Standard
    "Zu ueben"), gefiltert nach Fachbereich und Thema. Rot vor gelb, darin
    die zuletzt bearbeiteten zuerst. Jeder Eintrag ist ein dict mit source,
    key, item, title, level, time."""
    entries = []
    for source in sources or SOURCES:
        for key, item in source_items(source):
            if category != FILTER_ALL and item.get("cat") != category:
                continue
            if topic != FILTER_ALL and item.get("thema") != topic:
                continue
            value, level = book.status(source, key)
            if status not in (None, FILTER_ALL) and value != status:
                continue
            entries.append({"source": source, "key": key, "item": item,
                            "title": item_title(source, item), "status": value,
                            "level": level, "time": book.last_time(source, key)})
    entries.sort(key=lambda entry: entry["time"], reverse=True)
    entries.sort(key=lambda entry: 0 if entry["level"] == LEVEL_RED else 1)
    return entries


# Suche im Notizblock (ab 0.54): Frage, Antwort, Thema und Fachbereich. Die
# Inhalte aendern sich zur Laufzeit nicht, darum wird der Suchtext je Frage
# nur einmal gebaut (sonst kostete jeder Tastendruck tausende model_answer).
NOTEBOOK_SEARCH_HINT = "Stichwort suchen (Frage, Antwort, Thema)"
NOTEBOOK_NO_HITS = ("Keine Treffer für „%s“. Versuch ein anderes Stichwort oder setze "
                    "die Filter zurück.")
_SEARCH_TEXT = {}


def search_key(text):
    """Vergleichsform fuer die Suche: Unicode vereinheitlicht (Umlaute als
    ein Zeichen), ohne Gross/klein (casefold, also auch ß = ss), Leerraum
    an den Raendern entfernt."""
    return unicodedata.normalize("NFC", str(text or "")).casefold().strip()


def _entry_search_text(entry):
    key = (entry["source"], entry["key"])
    text = _SEARCH_TEXT.get(key)
    if text is None:
        item = entry["item"]
        topic = item.get("thema")
        # Ohne Fachbereich (ab 0.54 nach Abnahme): der kommt ueber die Filter,
        # sonst faende "raid" den ganzen Bereich "Systeme, RAID & Hardware"
        parts = [entry["title"], model_answer(entry["source"], item),
                 TOPIC_NAME.get(topic, ""), TOPIC_SHORT.get(topic, ""),
                 str(item.get("theme", ""))]
        text = _SEARCH_TEXT[key] = search_key(" ".join(parts))
    return text


def notebook_search(entries, query):
    """Eintraege des Notizblocks, die das Stichwort query enthalten
    (zusaetzlich zu den Filtern von notebook_entries). Leeres Stichwort =
    alle. Die Reihenfolge bleibt."""
    needle = search_key(query)
    if not needle:
        return list(entries)
    return [entry for entry in entries if needle in _entry_search_text(entry)]


def notebook_summary(book, category=FILTER_ALL, topic=FILTER_ALL):
    """{quelle: {status: Anzahl}} ueber den ganzen Fragenpool."""
    summary = {}
    for source in SOURCES:
        keys = [key for key, item in source_items(source)
                if (category == FILTER_ALL or item.get("cat") == category)
                and (topic == FILTER_ALL or item.get("thema") == topic)]
        summary[source] = book.counts(source, keys)
    return summary


NUMBER_WORDS = ["null", "ein", "zwei", "drei", "vier", "fünf", "sechs", "sieben",
                "acht", "neun", "zehn", "elf", "zwölf"]


def count_word(number):
    """Zahl als Wort fuer Fliesstexte ("fuenf Fachbereiche"), ab 13 als Ziffern.
    Ab 0.51, damit Anzahlen nie mehr von Hand im Text stehen."""
    return NUMBER_WORDS[number] if 0 <= number < len(NUMBER_WORDS) else str(number)


def plural(number, singular, plural_form, word=False):
    """Anzahl mit passender Einzahl/Mehrzahl ("1 Tag", "2 Tage") - ab 0.53,
    damit Platzhalter-Saetze nie mehr "1 Tage" oder "Tag(e)" zeigen.
    word=True schreibt kleine Zahlen als Wort (count_word)."""
    noun = singular if number == 1 else plural_form
    shown = count_word(number) if word else "{:,}".format(number).replace(",", ".")
    return "%s %s" % (shown, noun)


def learning_streak(days, today=None):
    """Lerntage in Folge bis heute (heute ohne Aktivitaet zaehlt noch nicht
    als Unterbrechung, solange gestern gelernt wurde). days: Menge von
    "JJJJ-MM-TT" mit Aktivitaet. (Bis 0.52 in fisi_lernen.)"""
    today = today or datetime.date.today()
    day = today if today.isoformat() in days else today - datetime.timedelta(days=1)
    count = 0
    while day.isoformat() in days:
        count += 1
        day -= datetime.timedelta(days=1)
    return count


# Anzeigedauer kurzer Hinweise (Toast/SnackBar) - ab 0.53 auf PC und Handy gleich
TOAST_MS = 4000
REMINDER_TOAST_MS = 9000   # Erinnerung ans Tagesziel


def ihk_note(percentage):
    """IHK-Notenschluessel."""
    if percentage >= 92:
        return "1 (Sehr gut)"
    if percentage >= 81:
        return "2 (Gut)"
    if percentage >= 67:
        return "3 (Befriedigend)"
    if percentage >= 50:
        return "4 (Ausreichend)"
    if percentage >= 30:
        return "5 (Mangelhaft)"
    return "6 (Ungenügend)"


# ============================================================================
#  PRAXIS-RECHNER
# ============================================================================

class InputError(ValueError):
    """Ungueltige Benutzereingabe - der Text ist fuer die Anzeige gedacht."""


# Ab 0.62.4 (B-D-15, Plan 0.62.4 Abschnitt 3.5, Entscheidung F-7 A): eine
# gemeinsame Leseregel fuer die Zahlfelder von RAID, Bildschirm und USV.
#  1. Komma ist immer das Dezimalzeichen ("1,5" = 1,5; "1,000" = 1).
#  2. Punkt vor vollstaendigen Dreiergruppen ist ein Tausenderpunkt, wenn die
#     Zahl nicht mit 0 beginnt ("1.000", "12.500", "1.000.000", "1.000,5").
#  3. Sonst ist ein einzelner Punkt ein Dezimalpunkt ("1.5", "0.125").
#  4. Abgelehnt: englische Mischform ("1,000.5"), schiefe Gruppen ("1.00,5"),
#     e-Schreibweise, "_", inf, nan, fremde Ziffern, mehr als 20 Zeichen,
#     mehr als 3 Nachkommastellen.
#  7. Ganzzahlfelder melden "1.5" als "ganze Zahl".
# Leerzeichen (auch geschuetzt oder schmal) duerfen Dreiergruppen trennen
# ("1 000"), "-0" wird 0. Obergrenzen je Feld kommen erst mit 0.62.5.
# raid_values, raid_input_values, raid_input_problem und ipv4_values (Spiel)
# bleiben unberuehrt; die Regel gilt nur fuer die Text-Lesestellen.
NUMBER_MAX_CHARS = 20
NUMBER_MAX_DECIMALS = 3          # reicht fuer 23,976 Bilder/Sekunde
_NUMBER_GROUPS = re.compile(r"[1-9][0-9]{0,2}(\.[0-9]{3})+")
_NUMBER_GROUPS_SPACE = re.compile(r"[1-9][0-9]{0,2}([   ][0-9]{3})+(,[0-9]+)?")


class _NumberProblem(ValueError):
    """Interner Grund, warum read_number ablehnt: "leer", "keine Zahl" oder
    "Nachkommastellen" (die Meldung fuer die Anzeige baut read_number)."""


def _number_value(text):
    """Liest einen Text nach der Leseregel oben als float oder wirft
    _NumberProblem. Ohne Meldungstext, ohne Grenzen."""
    raw = str(text if text is not None else "").strip()
    if not raw:
        raise _NumberProblem("leer")
    if len(raw) > NUMBER_MAX_CHARS:
        raise _NumberProblem("keine Zahl")
    negative = raw.startswith("-")
    if negative:
        raw = raw[1:]
    if _NUMBER_GROUPS_SPACE.fullmatch(raw):
        raw = re.sub(r"[   ]", ".", raw)
    if not re.fullmatch(r"[0-9.,]+", raw) or raw.count(",") > 1:
        raise _NumberProblem("keine Zahl")          # e, _, inf, nan, fremde Ziffern
    whole, comma, rest = raw.partition(",")
    decimal = bool(comma)
    if comma:
        if "." in whole:
            if not _NUMBER_GROUPS.fullmatch(whole):
                raise _NumberProblem("keine Zahl")  # 1.00,5 / 1,000.5 / 1.000.5
            whole = whole.replace(".", "")
    elif "." in whole:
        if _NUMBER_GROUPS.fullmatch(whole):          # Tausenderpunkt
            whole = whole.replace(".", "")
        elif whole.count(".") == 1:                  # Dezimalpunkt
            whole, _point, rest = whole.partition(".")
            decimal = True
        else:
            raise _NumberProblem("keine Zahl")      # 1.000.5 / 1.2.3
    if decimal:
        if not rest.isdigit():                       # "5," / "5." ohne Ziffer danach
            raise _NumberProblem("keine Zahl")
        if len(rest) > NUMBER_MAX_DECIMALS:
            raise _NumberProblem("Nachkommastellen")
    whole = whole or "0"                             # ",5" / ".5" = 0,5
    if not whole.isdigit():
        raise _NumberProblem("keine Zahl")
    value = float(whole + ("." + rest if rest else ""))
    return 0.0 if value == 0 else (-value if negative else value)


def read_number(text, caption, ganz=False):
    """Liest ein Zahlfeld der Rechner (RAID, Bildschirm, USV) nach der
    gemeinsamen Leseregel. caption = Feldbeschriftung fuer die Meldung.
    Liefert float, bei ganz=True int. Fehler -> InputError."""
    try:
        value = _number_value(text)
    except _NumberProblem as problem:
        if str(problem) == "leer":
            raise InputError("Bitte einen Wert eingeben: %s." % caption) from None
        raise InputError("Bitte eine Zahl eingeben: %s. Zum Beispiel %s."
                         % (caption, "1.000" if ganz else "1.000 oder 1,5")) from None
    if ganz:
        if value != int(value):
            raise InputError("Bitte eine ganze Zahl eingeben: %s." % caption)
        return int(value)
    return value


RAID_LEVELS = ["RAID 0", "RAID 1", "RAID 5", "RAID 6", "RAID 10"]

# Mindestanzahl Platten und Formel -> (Nettokapazitaet, Ausfalltoleranz)
RAID_RULES = {
    "RAID 0": (1, lambda n, s: (n * s, 0)),
    "RAID 1": (2, lambda n, s: (s, n - 1)),
    "RAID 5": (3, lambda n, s: ((n - 1) * s, 1)),
    "RAID 6": (4, lambda n, s: ((n - 2) * s, 2)),
    "RAID 10": (4, lambda n, s: ((n / 2) * s, 1)),
}
# Ab 0.54: Bei der Eingabe (RAID-Rechner, Server bestuecken im Spiel) braucht
# RAID 0 mindestens 2 Platten - so ist es fachlich richtig. RAID_RULES bleibt
# unveraendert, damit gespeicherte Spielstaende rueckwirkend gleich rechnen.
RAID_INPUT_MIN = {"RAID 0": 2}

COLOR_DEPTHS = [("8", "8 Bit (256 Farben)"), ("16", "16 Bit (High Color)"),
                ("24", "24 Bit (True Color)"),
                ("32", "32 Bit (True Color + Alpha)")]


def ipv4_values(network):
    """Kennwerte eines IPv4-Netzes (ipaddress.IPv4Network) als Woerterbuch.
    Genutzt vom Subnetz-Rechner und von den IP-Plaenen im Lernspiel."""
    hosts = network.num_addresses - 2 if network.prefixlen < 31 else \
        (2 if network.prefixlen == 31 else 1)
    if network.prefixlen < 31:
        # Ab 0.62.3 ohne Adressliste (Netzadresse + 1, Broadcast-Adresse - 1):
        # list(network.hosts()) brauchte bei /8 rund 16 s und 1,7 GB Speicher
        first = network.network_address + 1
        last = network.broadcast_address - 1
    else:
        # /31 und /32 wie bisher (hoechstens zwei Adressen)
        host_list = list(network.hosts())
        first = host_list[0] if host_list else network.network_address
        last = host_list[-1] if host_list else network.broadcast_address
    return {
        "netz": network.network_address,
        "maske": network.netmask,
        "wildcard": network.hostmask,
        "broadcast": network.broadcast_address,
        "erste": first,
        "letzte": last,
        "hosts": hosts,
        "adressen": network.num_addresses,
        "praefix": network.prefixlen,
    }


def subnet_report(value):
    """Berechnet die Netzwerkdaten zu einer Adresse mit Praefix (IPv4 oder
    IPv6) und liefert sie als mehrzeiligen Text."""
    try:
        network = ipaddress.ip_network(value.strip(), strict=False)
    except ValueError:
        raise InputError(
            "Bitte eine gültige Adresse angeben.\n\n"
            "Beispiele:\n  192.168.1.50/24\n  10.0.0.0/255.255.255.0\n"
            "  2001:db8::1/64")

    if network.version == 4:
        v = ipv4_values(network)
        # Ab 0.62.3: /31 hat keine Broadcast-Adresse (Punkt-zu-Punkt, RFC 3021)
        broadcast = "keine (/31, RFC 3021)" if v["praefix"] == 31 else v["broadcast"]
        lines = [
            "Netzadresse           : %s" % v["netz"],
            "Subnetzmaske          : %s" % v["maske"],
            "Wildcard-Maske        : %s" % v["wildcard"],
            "Broadcast-Adresse     : %s" % broadcast,
            "Erste Host-Adresse    : %s" % v["erste"],
            "Letzte Host-Adresse   : %s" % v["letzte"],
            "Nutzbare Hosts        : %s" % de_int(v["hosts"]),
            "Adressen gesamt       : %s" % de_int(v["adressen"]),
            "Präfixlänge           : /%d" % v["praefix"],
        ]
    else:
        lines = [
            "Netzadresse           : %s" % network.network_address,
            "Präfixlänge           : /%d" % network.prefixlen,
            "Erste Adresse         : %s" % network.network_address,
            "Letzte Adresse        : %s" % network[-1],
            "Adressen gesamt       : %s" % de_int(network.num_addresses),
        ]
    return "\n".join(lines)


# ----------------------------------------------------------------------------
#  Ab 0.63 (Plan 0.63, F-63-4 Variante A nach F-63-17): IPv6 ausgeschrieben
#  und Adresstyp als zwei Ergebniszeilen. subnet_report bleibt unveraendert;
#  PC und Handy haengen die Zeilen im Modus IPv6 an.
# ----------------------------------------------------------------------------
# Beschriftungen: eine Quelle fuer PC und Handy
IPV6_LABEL_AUSGESCHRIEBEN = "Ausgeschrieben"
IPV6_LABEL_ADRESSTYP = "Adresstyp"
# Gleicher Text wie die Meldung von subnet_report (dort keine Konstante)
IPV6_DETAILS_ERROR = ("Bitte eine gültige Adresse angeben.\n\n"
                      "Beispiele:\n  192.168.1.50/24\n  10.0.0.0/255.255.255.0\n"
                      "  2001:db8::1/64")
# Adresstypen nach Plan 0.63 Abschnitt 2.1 und 2.5 (E-63-1 bis E-63-9,
# F-63-16 = Ja). Quellen: RFC 4291 2.4 (Unspezifiziert, Loopback, Multicast,
# Link-Local, Rest), RFC 4193 3.1 (fc00::/7, L-Bit), RFC 3849 und RFC 9637
# (Dokumentation), RFC 3879 (Site-Local veraltet). Je Eintrag: Praefix als
# ganze Zahl, Praefixlaenge, Text.
_IPV6_ULA = "Unique Local (fc00::/7, RFC 4193)"
IPV6_TYPES = [
    (0, 128, "Unspezifiziert (::/128)"),
    (1, 128, "Loopback (::1/128)"),
    (0xff << 120, 8, "Multicast (ff00::/8)"),
    (0xfe80 << 112, 10, "Link-Local (fe80::/10)"),
    (0xfec0 << 112, 10, "Site-Local (veraltet, RFC 3879)"),
    (0xfc << 120, 7, _IPV6_ULA),
    (0xfd << 120, 8, _IPV6_ULA + ", lokal vergeben, fd00::/8"),
    (0xfc << 120, 8, _IPV6_ULA + ", L-Bit 0, bisher nicht vergeben"),
    (0x20010db8 << 96, 32, "Dokumentation (2001:db8::/32, RFC 3849)"),
    (0x3fff << 112, 20, "Dokumentation (3fff::/20, RFC 9637)"),
    (0x2000 << 112, 3, "Global Unicast (2000::/3)"),
]
IPV6_TYPE_REST = "nicht zugeordnet (laut RFC 4291 als Global Unicast zu behandeln)"
IPV6_TYPE_MIXED = "mehrere Adresstypen (Präfix kürzer als Typbereich)"


def _ipv6_in(value, prefix, base, length):
    """True, wenn das Netz value/prefix ganz im Bereich base/length liegt."""
    return prefix >= length and (value >> (128 - length)) == (base >> (128 - length))


def ipv6_type(value, prefix):
    """Adresstyp eines IPv6-Netzes (Netzadresse als ganze Zahl, Praefix).
    Regel: Es gilt der genaueste Bereich (laengstes Praefix), in dem das
    GANZE Netz liegt. Liegt das Netz in keinem Bereich und beruehrt auch
    keinen, ist es "nicht zugeordnet" (RFC 4291: als Global Unicast zu
    behandeln). Ist das Praefix kuerzer als ein Typbereich, den das Netz
    beruehrt, und liegt es in keinem (z. B. ::/64 mit :: und ::1, fe80::/9),
    heisst es "mehrere Adresstypen"."""
    best = None
    for base, length, text in IPV6_TYPES:
        if _ipv6_in(value, prefix, base, length) and (best is None or length > best[0]):
            best = (length, text)
    if best is not None:
        return best[1]
    for base, length, _text in IPV6_TYPES:
        if _ipv6_in(base, length, value, prefix):
            return IPV6_TYPE_MIXED
    return IPV6_TYPE_REST


def ipv6_long(value, prefix):
    """Ausgeschriebene Form (8 Hextette zu je 4 Stellen) mit Praefix."""
    return "%s/%d" % (":".join("%04x" % g for g in ipv6_groups(value)), prefix)


def ipv6_details(value):
    """Zwei Ergebniszeilen fuer IPv6-Netzdaten (F-63-4):
    [(IPV6_LABEL_AUSGESCHRIEBEN, Netzadresse ausgeschrieben/Praefix),
     (IPV6_LABEL_ADRESSTYP, Adresstyp-Text)].
    Eingabe wie subnet_report; ungueltig oder IPv4 -> InputError."""
    try:
        network = ipaddress.ip_network(value.strip(), strict=False)
    except ValueError:
        raise InputError(IPV6_DETAILS_ERROR) from None
    if network.version != 6:
        raise InputError(IPV6_DETAILS_ERROR)
    address = int(network.network_address)
    return [(IPV6_LABEL_AUSGESCHRIEBEN, ipv6_long(address, network.prefixlen)),
            (IPV6_LABEL_ADRESSTYP, ipv6_type(address, network.prefixlen))]


# ----------------------------------------------------------------------------
#  Ab 0.63 (Plan 0.63, T1): Netz aufteilen und Netz nach Hostbedarf
# ----------------------------------------------------------------------------
# Gerechnet wird nur mit ganzen Zahlen: Subnetz Nr. i hat die Netzadresse
# Netz + (i - 1) x Groesse. Es entsteht nie eine Liste aller Subnetze oder
# Adressen (Lehre aus dem /8-Fehler in 0.62.2), darum rechnen auch IPv6 /0 in
# 2^64 Subnetze und IPv4 /8 in 2^24 Subnetze sofort. ipaddress liest nur die
# Eingabe; die Schreibweise der Ausgabe ist eigen (RFC 5952), weil ipaddress
# ::ffff-Adressen je nach Python-Patchstand anders schreibt (Plan 0.63 E-63-6;
# Mischform ::ffff:1.2.3.4 erst mit R-9 in 0.63.1).
# subnet_report und ipv4_values (Spiel) bleiben unveraendert.

# Beschriftungen: eine Quelle fuer PC und Handy (Plan 0.63 Abschnitt 4.1)
SUBNET_TITLE = "Subnetting"
SUBNET_MODES = [("ipv4", "IPv4"), ("ipv6", "IPv6")]
SUBNET_SUBTITLE = {"ipv4": "IPv4", "ipv6": "IPv6"}
SUBNET_VIEWS = {
    "ipv4": [("netzdaten", "Netzdaten"), ("aufteilen", "Netz aufteilen"),
             ("bedarf", "Nach Hostbedarf")],
    "ipv6": [("netzdaten", "Netzdaten"), ("aufteilen", "Netz aufteilen")],
}
SUBNET_FIELD_NET = {"ipv4": "Netz mit Präfix (z. B. 192.168.10.0/24)",
                    "ipv6": "Netz mit Präfix (z. B. 2001:db8:abcd::/48)"}
SUBNET_FIELD_COUNT = "Anzahl Subnetze"
SUBNET_FIELD_NEEDS = "Subnetze, je Zeile Name und Hosts (z. B. A 50)"
SUBNET_PAGE_FIRST = "Erste Seite"
SUBNET_PAGE_BACK = "Zurück"
SUBNET_PAGE_NEXT = "Weiter"
SUBNET_PAGE_LAST = "Letzte Seite"
SUBNET_PAGE_OF = "Seite %s von %s"
# Sprung auf eine Seitennummer (Plan 0.63 Abschnitt 2.2 Nr. 8): Zahlfeld und
# Knopf neben "Seite x von y"; gelesen mit read_number(..., ganz=True)
SUBNET_PAGE_JUMP_FIELD = "Seite"
SUBNET_PAGE_JUMP = "Zur Seite"
# Vorgaben vor dem ersten "Berechnen" (Beispiele B, C und D aus Plan 0.63)
SUBNET_DEFAULTS = {
    ("ipv4", "aufteilen"): ("192.168.10.0/24", "6"),
    ("ipv6", "aufteilen"): ("2001:db8:abcd::/48", "6"),
    ("ipv4", "bedarf"): ("192.168.10.0/24", "A 50\nB 20\nC 10\nD 2"),
}
SUBNET_PAGE_SIZE = 8          # Subnetze je Seite, PC und Handy (F-63-9)
SUBNET_HOSTS_MAX = 12         # Zeilen bei "Nach Hostbedarf" (F-63-10)
SUBNET_NAME_MAX = 16          # Zeichen je Name bei "Nach Hostbedarf"
SUBNET_STATE_USED = "verwendet"
SUBNET_STATE_FREE = "frei, Reserve"

SUBNET_NET_ERROR = ("Bitte ein gültiges Netz mit Präfix angeben.\n\n"
                    "Beispiele:\n  192.168.10.0/24\n  2001:db8:abcd::/48")
SUBNET_COUNT_ERROR = "Die Anzahl muss mindestens 1 sein."
SUBNET_TOO_MANY = "Zu viele Subnetze: /%d + %d Bit = /%d, mehr als /%d geht nicht."
# Fassung 4 (Z-10 Fund 10, N-4e): dahinter die Hoechstzahl, ab 2^33 als Potenz
SUBNET_TOO_MANY_MAX = "Höchstens %s %s."
SUBNET_HOST_HINT = ("Hinweis: %s ist eine Host-Adresse. "
                    "Gerechnet wird mit dem Netz %s.")
SUBNET_NO_SPLIT = "Keine Teilung nötig: Bei 1 Subnetz bleibt das Netz, wie es ist."
SUBNET_HINT_31 = "/31: 2 Adressen, nur für Punkt-zu-Punkt-Verbindungen (RFC 3021)"
SUBNET_HINT_32 = "/32: eine einzelne Adresse"
SUBNET_HOSTS_V6_ERROR = ("„Nach Hostbedarf“ rechnet nur mit IPv4. "
                         "Für IPv6 bitte „Netz aufteilen“ nutzen.")
SUBNET_NEEDS_EMPTY = ("Bitte mindestens ein Subnetz eingeben, je Zeile Name und "
                      "Hosts (z. B. A 50).")
SUBNET_NEEDS_TOO_MANY = "Höchstens %d Subnetze, eingegeben sind %d."
SUBNET_NEED_NUMBER = ("Zeile %d: Bitte die Anzahl Hosts als ganze Zahl angeben "
                      "(z. B. A 50).")
SUBNET_NEED_MIN = "Zeile %d: Der Hostbedarf muss mindestens 1 sein."
SUBNET_NEED_MAX = "Zeile %d: Mehr als %s Hosts passen in kein IPv4-Netz."
SUBNET_NAME_LONG = "Zeile %d: Der Name ist zu lang (höchstens %d Zeichen)."
SUBNET_NEED_COMMA = ("Zeile %d: Bitte je Zeile genau ein Subnetz angeben, ohne Komma, "
                     "Semikolon oder Schrägstrich (z. B. A 50).")                # M-3
SUBNET_NEED_NUMBERS = ("Zeile %d: Mehrere Zahlen in der Zeile. Je Zeile ein Subnetz; "
                       "steht im Namen eine Zahl, bitte mit Doppelpunkt trennen "
                       "(z. B. VLAN 10: 20).")                                  # M-12
SUBNET_NAME_TWICE = ("Zeile %d: Der Name „%s“ kommt schon in Zeile %d vor. "
                     "Bitte jeden Namen nur einmal verwenden.")
SUBNET_NAME_AUTO_TAKEN = ("Zeile %d: Den Namen „%s“ hat schon Zeile %d automatisch "
                          "bekommen (sie hat keinen Namen). Bitte einen anderen Namen "
                          "wählen.")                                            # M-13a
SUBNET_NAME_AUTO_CLASH = ("Zeile %d: Ohne Namen heißt das Subnetz automatisch „%s“, "
                          "diesen Namen hat schon Zeile %d. Bitte einen Namen "
                          "angeben.")                                           # M-13b
SUBNET_MISSING = "Es fehlen %s Adressen. Nötig wäre mindestens ein /%d (%s Adressen)."
SUBNET_MISSING_ALL = ("Es fehlen %s Adressen. Das passt in kein IPv4-Netz "
                      "(höchstens 2^32 Adressen).")
SUBNET_HINT_P2P = ("Hinweis: Für eine Punkt-zu-Punkt-Verbindung mit 2 Hosts "
                   "reicht auch ein /31 (RFC 3021). Gerechnet wird wie üblich "
                   "mit /30.")


def ipv4_text(value):
    """IPv4-Adresse aus einer ganzen Zahl (192.168.10.0)."""
    return ".".join(str((value >> shift) & 255) for shift in (24, 16, 8, 0))


def ipv6_groups(value):
    """Die acht Hextette einer IPv6-Adresse als ganze Zahlen."""
    return [(value >> (16 * (7 - i))) & 0xFFFF for i in range(8)]


def ipv6_text(value):
    """IPv6-Kurzschreibweise nach RFC 5952 aus einer ganzen Zahl: fuehrende
    Nullen weg, die laengste Folge von mindestens zwei Null-Hextetten wird
    "::" (bei Gleichstand die erste), Kleinbuchstaben."""
    groups = ipv6_groups(value)
    best_start, best_len, start = 0, 0, None
    for i in range(9):
        if i < 8 and groups[i] == 0:
            if start is None:
                start = i
        elif start is not None:
            if i - start > best_len:
                best_start, best_len = start, i - start
            start = None
    parts = ["%x" % group for group in groups]
    if best_len < 2:
        return ":".join(parts)
    return ":".join(parts[:best_start]) + "::" + ":".join(parts[best_start + best_len:])


def subnet_addr_text(version, value):
    """Adresse (ganze Zahl) in der Schreibweise ihrer Version."""
    return ipv4_text(value) if version == 4 else ipv6_text(value)


def subnet_net_text(version, value, prefix):
    return "%s/%d" % (subnet_addr_text(version, value), prefix)


def subnet_mask(prefix):
    """IPv4-Subnetzmaske zur Praefixlaenge als ganze Zahl."""
    return ((1 << 32) - 1) ^ ((1 << (32 - prefix)) - 1)


def subnet_parse(text, version=None):
    """Liest ein Netz mit Praefix (IPv4 oder IPv6). version = 4 oder 6
    verlangt diese Version (Schalter im Rechner). Ein gesetzter Hostanteil
    wird auf die Netzadresse gesetzt, dazu kommt ein Hinweis."""
    raw = str(text if text is not None else "").strip()
    if "/" not in raw or "%" in raw:
        raise InputError(SUBNET_NET_ERROR)
    try:
        interface = ipaddress.ip_interface(raw)
    except ValueError:
        raise InputError(SUBNET_NET_ERROR) from None
    found = interface.version
    if version is not None and found != version:
        example = "192.168.10.0/24" if version == 4 else "2001:db8:abcd::/48"
        raise InputError("Im Modus IPv%d bitte ein IPv%d-Netz angeben (z. B. %s)."
                         % (version, version, example))
    width = 32 if found == 4 else 128
    prefix = interface.network.prefixlen
    address = int(interface.ip)
    base = address - (address & ((1 << (width - prefix)) - 1))
    hint = None
    if address != base:
        hint = SUBNET_HOST_HINT % (subnet_net_text(found, address, prefix),
                                   subnet_net_text(found, base, prefix))
    return {"version": found, "breite": width, "netz": base, "praefix": prefix,
            "adresse": address, "hinweis": hint}


def _subnet_whole(text):
    """Ganze Zahl genau aus dem Text (read_number liefert ueber 2^53 nur
    einen gerundeten Wert). Nur nach erfolgreichem read_number aufrufen."""
    raw = str(text).strip()
    negative = raw.startswith("-")
    raw = raw.lstrip("-")
    if _NUMBER_GROUPS_SPACE.fullmatch(raw):
        raw = re.sub(r"[   ]", ".", raw)
    whole, comma, rest = raw.partition(",")
    if not comma and "." in whole and not _NUMBER_GROUPS.fullmatch(whole):
        whole, _point, rest = whole.partition(".")
    if rest.strip("0"):
        raise InputError("Bitte eine ganze Zahl eingeben: %s." % SUBNET_FIELD_COUNT)
    value = int(whole.replace(".", "") or "0")
    return -value if negative else value


def subnet_count(value):
    """Anzahl Subnetze aus dem Feld (gemeinsame Leseregel, "1.000" = 1000)
    oder als ganze Zahl. Fehler -> InputError."""
    if isinstance(value, int) and not isinstance(value, bool):
        number = value
    else:
        number = read_number(value, SUBNET_FIELD_COUNT, ganz=True)
        if abs(number) >= 2 ** 53:
            number = _subnet_whole(value)
    if number < 1:
        raise InputError(SUBNET_COUNT_ERROR)
    return number


def split_network(net_text, count, version=None):
    """Netz in count gleich grosse Subnetze aufteilen (IPv4 und IPv6).
    Liefert ein Woerterbuch mit den Kennwerten; die Subnetze selbst liefern
    split_entry und split_page (ohne Aufzaehlen)."""
    result = subnet_parse(net_text, version)
    wanted = subnet_count(count)
    prefix, width = result["praefix"], result["breite"]
    bits = (wanted - 1).bit_length()        # kleinstes k mit 2^k >= N
    new = prefix + bits
    if new > width:
        room = width - prefix               # hoechstens 2^room Subnetze
        most = SUBNET_TOO_MANY_MAX % (
            de_int(1 << room) if room <= 32 else "2^%d" % room,
            "Subnetz" if room == 0 else "Subnetze")
        raise InputError(SUBNET_TOO_MANY % (prefix, bits, new, width) + " " + most)
    total = 1 << bits
    result.update({
        "gewuenscht": wanted, "k": bits, "neu": new, "anzahl": total,
        "groesse": 1 << (width - new),
        "seiten": (total + SUBNET_PAGE_SIZE - 1) // SUBNET_PAGE_SIZE,
    })
    hints = [result["hinweis"]] if result["hinweis"] else []
    if bits == 0:
        hints.append(SUBNET_NO_SPLIT)
    if result["version"] == 4:
        result["maske"] = subnet_mask(new)
        result["hosts"] = result["groesse"] - 2 if new < 31 else result["groesse"]
        if new == 31:
            hints.append(SUBNET_HINT_31)
        elif new == 32:
            hints.append(SUBNET_HINT_32)
    else:
        result["hosts"] = None              # IPv6: kein Abzug, kein Broadcast
    if result["version"] == 6 and new % 4:
        nibble = (new + 3) // 4 * 4         # naechste 4-Bit-Grenze (E-63-7)
        result["nibble"] = nibble
        result["nibble_anzahl"] = 1 << (nibble - prefix)
    else:
        result["nibble"] = None
        result["nibble_anzahl"] = None
    result["hinweise"] = hints
    return result


def split_entry(result, index):
    """Subnetz Nr. index + 1 (index ab 0) ohne Liste: Netz + index x Groesse.
    IPv4: erste/letzte Host-Adresse und Broadcast (bei /31 und /32 keiner),
    IPv6: Anfang und Ende des Bereichs."""
    if not 0 <= index < result["anzahl"]:
        raise IndexError("Subnetz %d gibt es nicht" % (index + 1))
    size = result["groesse"]
    net = result["netz"] + index * size
    end = net + size - 1
    entry = {"nr": index + 1, "netz": net, "ende": end, "praefix": result["neu"],
             "status": SUBNET_STATE_USED if index < result["gewuenscht"]
             else SUBNET_STATE_FREE}
    if result["version"] == 4 and result["neu"] < 31:
        entry.update(erste=net + 1, letzte=end - 1, broadcast=end)
    else:
        entry.update(erste=net, letzte=end, broadcast=None)
    return entry


def split_page(result, page):
    """Eine Seite mit hoechstens SUBNET_PAGE_SIZE Subnetzen. Seiten ausserhalb
    werden auf die erste bzw. letzte Seite begrenzt."""
    pages = result["seiten"]
    page = min(max(int(page), 1), pages)
    start = (page - 1) * SUBNET_PAGE_SIZE
    stop = min(start + SUBNET_PAGE_SIZE, result["anzahl"])
    return {"seite": page, "seiten": pages,
            "text": SUBNET_PAGE_OF % (de_int(page), de_int(pages)),
            "eintraege": [split_entry(result, i) for i in range(start, stop)]}


def _subnet_host_label(result):
    if result["version"] == 6:
        return None
    if result["neu"] == 31:
        return SUBNET_HINT_31
    if result["neu"] == 32:
        return SUBNET_HINT_32
    return de_int(result["hosts"])


def split_report(result, page=1, schmal=False):
    """Ergebnistext "Netz aufteilen" mit einer Seite der Subnetze. schmal =
    Handy (Bloecke, hoechstens CALC_EXPLAIN_HANDY_WIDTH Zeichen je Zeile)."""
    version = result["version"]
    data = split_page(result, page)
    base = subnet_net_text(version, result["netz"], result["praefix"])
    used = result["gewuenscht"]
    free = result["anzahl"] - used
    count_text = de_int(result["anzahl"])
    if free:
        count_text += " (%s verwendet, %s frei, Reserve)" % (de_int(used), de_int(free))
    rows = [("Ausgangsnetz", base),
            ("Gesucht", "1 Subnetz" if used == 1 else "%s Subnetze" % de_int(used)),
            ("Benötigte Bits", "k = %d" % result["k"]),
            ("Neue Präfixlänge", "/%d" % result["neu"])]
    if version == 4:
        rows.append(("Subnetzmaske", ipv4_text(result["maske"])))
    rows.append(("Adressen je Subnetz", de_int(result["groesse"])))
    if version == 4:
        rows.append(("Nutzbare Hosts", _subnet_host_label(result)))
    rows.append(("Subnetze", count_text))
    lines = list(result["hinweise"])
    if result["nibble"]:
        lines.append("Hinweis: An der nächsten 4-Bit-Grenze (Nibble): /%d = %s Subnetze."
                     % (result["nibble"], de_int(result["nibble_anzahl"])))
    if lines:
        lines.append("")
    if schmal:
        for caption, value in rows:
            lines += ["%s:" % caption, " %s" % value]
        lines.append("")
        for entry in data["eintraege"]:
            lines.append("Subnetz %s: %s" % (de_int(entry["nr"]), entry["status"]))
            net = subnet_net_text(version, entry["netz"], entry["praefix"])
            lines += _handy_address(" Netz: ", net)
            if version == 4:
                lines += [" Erste: %s" % ipv4_text(entry["erste"]),
                          " Letzte: %s" % ipv4_text(entry["letzte"]),
                          " Broadcast: %s" % (ipv4_text(entry["broadcast"])
                                              if entry["broadcast"] is not None else "keine")]
            else:
                lines += _handy_address(" bis: ", ipv6_text(entry["ende"]))
        lines.append(data["text"])
        return "\n".join(_handy_fit(lines))
    for caption, value in rows:
        lines.append("%-22s: %s" % (caption, value))
    lines.append("")
    # Spalten so breit wie noetig; "*" hinter der Nummer = frei, Reserve
    numbers = ["%s%s" % (de_int(entry["nr"]),
                         "" if entry["status"] == SUBNET_STATE_USED else "*")
               for entry in data["eintraege"]]
    width = max(2, max(len(number) for number in numbers))
    if version == 4:
        cells = [[subnet_net_text(4, entry["netz"], entry["praefix"]),
                  ipv4_text(entry["erste"]), ipv4_text(entry["letzte"]),
                  ipv4_text(entry["broadcast"]) if entry["broadcast"] is not None
                  else "keine"] for entry in data["eintraege"]]
        heads = ["Netzadresse", "Erster Host", "Letzter Host", "Broadcast"]
        sizes = [max(len(heads[c]), max(len(row[c]) for row in cells)) for c in range(4)]
        lines.append(" ".join(["Nr".ljust(width)] + [heads[c].ljust(sizes[c])
                                                    for c in range(4)]).rstrip())
        for number, row in zip(numbers, cells):
            lines.append(" ".join([number.ljust(width)] + [row[c].ljust(sizes[c])
                                                         for c in range(4)]).rstrip())
    else:
        lines.append("%s Subnetz und letzte Adresse" % "Nr".ljust(width))
        for number, entry in zip(numbers, data["eintraege"]):
            lines.append("%s %s" % (number.ljust(width),
                                    subnet_net_text(6, entry["netz"], entry["praefix"])))
            lines.append("%s bis %s" % (" " * width, ipv6_text(entry["ende"])))
    if any(number.endswith("*") for number in numbers):
        lines.append("* frei, Reserve")
    lines.append(data["text"])
    return "\n".join(_fit_lines(lines, CALC_EXPLAIN_PC_WIDTH))


_HOST_NUMBER_WORD = re.compile(r"-?[0-9.]+")     # Wort, das wie eine Zahl aussieht
_HOST_WORDS = ("hosts", "host")


def _host_is_number(text):
    try:
        _number_value(text)
    except _NumberProblem:
        return False
    return True


def subnet_hosts_text(need):
    """ "50 Hosts", bei 1 "1 Host" (Plan 0.63 Fassung 4, Z-10 Fund 5)."""
    return "%s %s" % (de_int(need), "Host" if need == 1 else "Hosts")


def read_host_lines(text):
    """Liest die Bedarfszeilen "Name Hosts", "Name: Hosts" oder nur "Hosts"
    (dann Name "Netz 1", "Netz 2" ...; n zaehlt die Subnetze). Ein Wort
    "Hosts" am Ende ist erlaubt. Regeln je Zeile (Plan 0.63 Fassung 4,
    Abschnitt 2.3.1, in dieser Reihenfolge):
      * Leere Zeilen werden uebergangen, zaehlen aber bei "Zeile n" mit.
        Ein Tabulator zaehlt wie ein Leerzeichen, das Minus "−" wie "-".
      * Komma, Semikolon oder Schraegstrich: Meldung (M-3); "A 50, B 20"
        waere sonst ein Subnetz "A 50, B" (Komma = Dezimalzeichen).
      * Mehr als ein Doppelpunkt: Meldung (M-12).
      * Mit Doppelpunkt: links der Name, rechts der Bedarf nach der
        Leseregel von read_number ("1.000", "1 000", "50.0" erlaubt).
      * Ohne Doppelpunkt: Ist die ganze Zeile eine Zahl, ist das der Bedarf;
        sonst ist das letzte Wort der Bedarf und der Rest der Name. Steht im
        Namen noch ein Wort aus Ziffern ("A 50 B 20", "A 1 000", "VLAN 10
        20"), ist die Zeile mehrdeutig: Meldung (M-12).
      * Ein Strich am Ende des Namens ist ein Trenner ("A - 50" = "A").
      * Namen eindeutig, Gross/Klein zaehlt nicht; automatische Namen zaehlen
        mit und haben eigene Meldungen (M-13a, M-13b).
    Liefert [(Name, Bedarf)] in der Reihenfolge der Eingabe."""
    lines = str(text if text is not None else "").splitlines()
    filled = [line for line in lines if line.strip()]
    if not filled:
        raise InputError(SUBNET_NEEDS_EMPTY)
    if len(filled) > SUBNET_HOSTS_MAX:
        raise InputError(SUBNET_NEEDS_TOO_MANY % (SUBNET_HOSTS_MAX, len(filled)))
    wants = []
    seen = {}
    for number, line in enumerate(lines, 1):
        line = line.replace("\t", " ").replace("\u2212", "-").strip()
        if not line:
            continue
        if any(sign in line for sign in ",;/"):
            raise InputError(SUBNET_NEED_COMMA % number)
        if line.count(":") > 1:
            raise InputError(SUBNET_NEED_NUMBERS % number)
        if ":" in line:
            name, _colon, rest = line.partition(":")
            words = rest.split()
            if len(words) > 1 and words[-1].lower() in _HOST_WORDS:
                words = words[:-1]
            name, need_text = " ".join(name.split()), " ".join(words)
        else:
            words = line.split()
            if len(words) > 1 and words[-1].lower() in _HOST_WORDS:
                words = words[:-1]
            if _host_is_number(" ".join(words)):         # "50", "1 000"
                name, need_text = "", " ".join(words)
            else:
                if any(_HOST_NUMBER_WORD.fullmatch(word) for word in words[:-1]):
                    raise InputError(SUBNET_NEED_NUMBERS % number)
                name, need_text = " ".join(words[:-1]), words[-1]
        name = name.rstrip(" -\u2013\u2014")
        try:
            need = read_number(need_text, SUBNET_FIELD_NEEDS, ganz=True)
        except InputError:
            raise InputError(SUBNET_NEED_NUMBER % number) from None
        if need < 1:
            raise InputError(SUBNET_NEED_MIN % number)
        if need > (1 << 32) - 2:
            raise InputError(SUBNET_NEED_MAX % (number, de_int((1 << 32) - 2)))
        auto = not name
        name = name or "Netz %d" % (len(wants) + 1)
        if len(name) > SUBNET_NAME_MAX:
            raise InputError(SUBNET_NAME_LONG % (number, SUBNET_NAME_MAX))
        key = name.casefold()
        if key in seen:
            earlier, earlier_auto = seen[key]
            if auto:
                raise InputError(SUBNET_NAME_AUTO_CLASH % (number, name, earlier))
            if earlier_auto:
                raise InputError(SUBNET_NAME_AUTO_TAKEN % (number, name, earlier))
            raise InputError(SUBNET_NAME_TWICE % (number, name, earlier))
        seen[key] = (number, auto)
        wants.append((name, need))
    return wants


def subnet_host_bits(need):
    """Kleinstes h mit 2^h - 2 >= Bedarf, mindestens 2 (also /30)."""
    return max(2, (need + 1).bit_length())


def subnet_blocks(start, end):
    """Bereich start bis end - 1 als ausgerichtete Bloecke [(Netz, Praefix)],
    jeweils der groesste Block, der an start passt (hoechstens 64 Bloecke)."""
    blocks = []
    while start < end:
        size = start & -start if start else 1 << 32
        while start + size > end:
            size //= 2
        blocks.append((start, 32 - (size.bit_length() - 1)))
        start += size
    return blocks


def subnet_by_hosts(net_text, needs, version=None):
    """Netz nach Hostbedarf aufteilen (VLSM, nur IPv4): groesster Bedarf
    zuerst, Vergabe nacheinander ab der Netzadresse (dadurch ausgerichtet).
    needs = Text der Bedarfszeilen oder Liste [(Name, Bedarf)]."""
    result = subnet_parse(net_text, version)
    if result["version"] != 4:
        raise InputError(SUBNET_HOSTS_V6_ERROR)
    wants = read_host_lines(needs) if isinstance(needs, str) else list(needs)
    order = sorted(range(len(wants)), key=lambda i: (-wants[i][1], i))
    capacity = 1 << (32 - result["praefix"])
    subnets = []
    for name, need in wants:
        bits = subnet_host_bits(need)
        subnets.append({"name": name, "bedarf": need, "h": bits, "praefix": 32 - bits,
                        "groesse": 1 << bits, "maske": subnet_mask(32 - bits)})
    total = sum(item["groesse"] for item in subnets)
    result.update({"bedarfe": wants, "subnetze": subnets, "reihenfolge": order,
                   "kapazitaet": capacity, "summe": total, "passt": total <= capacity,
                   "fehlt": max(0, total - capacity), "noetig": None, "meldung": None,
                   "rest": None, "rest_von": None, "rest_bis": None, "bloecke": []})
    hints = [result["hinweis"]] if result["hinweis"] else []
    if result["passt"]:
        cursor = result["netz"]
        for index in order:
            item = subnets[index]
            item.update(netz=cursor, erste=cursor + 1, letzte=cursor + item["groesse"] - 2,
                        broadcast=cursor + item["groesse"] - 1)
            cursor += item["groesse"]
        end = result["netz"] + capacity
        result.update(rest=end - cursor, rest_von=cursor, rest_bis=end - 1,
                      bloecke=subnet_blocks(cursor, end))
        if any(need <= 2 for _name, need in wants):
            hints.append(SUBNET_HINT_P2P)
    else:
        needed = 32 - (total - 1).bit_length()
        if needed < 0:
            result["meldung"] = SUBNET_MISSING_ALL % de_int(result["fehlt"])
        else:
            result["noetig"] = needed
            result["meldung"] = SUBNET_MISSING % (de_int(result["fehlt"]), needed,
                                                  de_int(1 << (32 - needed)))
    result["hinweise"] = hints
    return result


def hosts_report(result, schmal=False):
    """Ergebnistext "Nach Hostbedarf" in der Reihenfolge der Eingabe."""
    lines = [h for h in result["hinweise"] if h != SUBNET_HINT_P2P]
    if lines:
        lines.append("")
    base = subnet_net_text(4, result["netz"], result["praefix"])
    if not result["passt"]:
        lines += ["Ausgangsnetz: %s" % base,
                  "Benötigt: %s Adressen, vorhanden: %s" % (
                      de_int(result["summe"]), de_int(result["kapazitaet"])),
                  "", result["meldung"]]
        return "\n".join(_fit_lines(lines, CALC_EXPLAIN_HANDY_WIDTH if schmal
                                     else CALC_EXPLAIN_PC_WIDTH))
    rest = "%s bis %s = %s Adressen" % (ipv4_text(result["rest_von"]),
                                        ipv4_text(result["rest_bis"]),
                                        de_int(result["rest"])) if result["rest"] \
        else "keiner, das Netz ist genau voll"
    order = ", ".join(result["subnetze"][i]["name"] for i in result["reihenfolge"])
    if schmal:
        lines += ["Ausgangsnetz:", " " + base,
                  "Summe: %s von %s Adressen" % (de_int(result["summe"]),
                                                 de_int(result["kapazitaet"])),
                  "Freier Rest:", " " + rest, "Vergeben in der Reihenfolge:", " " + order, ""]
        for item in result["subnetze"]:
            lines += ["%s (%s)" % (item["name"], subnet_hosts_text(item["bedarf"])),
                      " Netz: %s/%d" % (ipv4_text(item["netz"]), item["praefix"]),
                      " Maske: %s" % ipv4_text(item["maske"]),
                      " Erste: %s" % ipv4_text(item["erste"]),
                      " Letzte: %s" % ipv4_text(item["letzte"]),
                      " Broadcast: %s" % ipv4_text(item["broadcast"])]
    else:
        lines += ["%-22s: %s" % ("Ausgangsnetz", base),
                  "%-22s: %s von %s Adressen" % ("Summe der Subnetze", de_int(result["summe"]),
                                                 de_int(result["kapazitaet"])),
                  "%-22s: %s" % ("Freier Rest", rest),
                  "%-22s: %s" % ("Vergabe-Reihenfolge", order), ""]
        for item in result["subnetze"]:
            lines += ["%s (%s): %s/%d, Maske %s" % (
                          item["name"], subnet_hosts_text(item["bedarf"]),
                          ipv4_text(item["netz"]),
                          item["praefix"], ipv4_text(item["maske"])),
                      "   Hosts %s bis %s, Broadcast %s" % (
                          ipv4_text(item["erste"]), ipv4_text(item["letzte"]),
                          ipv4_text(item["broadcast"]))]
    if SUBNET_HINT_P2P in result["hinweise"]:
        lines += ["", SUBNET_HINT_P2P]
    return "\n".join(_fit_lines(lines, CALC_EXPLAIN_HANDY_WIDTH if schmal
                                     else CALC_EXPLAIN_PC_WIDTH))


# Zeilen fuer Ergebnis und Rechenweg auf eine Breite bringen (Handy 28,
# PC 75 Zeichen). Ganze Zahlen brechen vor einem Tausenderpunkt (der Punkt
# steht am Anfang der neuen Zeile, Plan 0.63 G-12), IPv6-Adressen nach einem
# Doppelpunkt, lange Woerter nach einem Bindestrich.
CALC_EXPLAIN_PC_WIDTH = 75


def _fit_pieces(word):
    if re.fullmatch(r"[0-9]{1,3}(\.[0-9]{3})+[,;)]?", word):
        return re.split(r"(?=\.)", word)
    if ":" in word:
        pieces = []
        for piece in re.findall(r"[^:]*:|[^:]+", word):
            if pieces and (piece == ":" or piece.startswith("/")):
                pieces[-1] += piece          # "::" und "/64" nicht abtrennen
            else:
                pieces.append(piece)
        return pieces
    if "-" in word.strip("-"):
        return re.findall(r"[^-]*-|[^-]+", word)
    return [word]


def _fit_line(line, width, more):
    """Eine zu lange Zeile umbrechen; Folgezeilen beginnen mit more."""
    lead = line[:len(line) - len(line.lstrip(" "))]
    parts = re.split(r"( +)", line.strip())
    out, current, fresh = [], lead, True
    for word, gap in zip(parts[0::2], [""] + parts[1::2]):
        glue = "" if fresh else gap          # Abstaende in der Zeile bleiben
        if len(current + glue + word) <= width:
            current, fresh = current + glue + word, False
            continue
        if len(more + word) <= width:        # ganzes Wort in die naechste Zeile
            if not fresh:
                out.append(current)
            current, fresh = more + word, False
            continue
        for number, piece in enumerate(_fit_pieces(word)):
            glue = ("" if fresh else gap) if number == 0 else ""
            if len(current + glue + piece) <= width:
                current, fresh = current + glue + piece, False
                continue
            if not fresh:
                out.append(current)
            current, fresh = more + piece, False
            while len(current) > width:
                out.append(current[:width])
                current = more + current[width:]
    out.append(current)
    return out


def _fit_lines(lines, width):
    """Jede Zeile hoechstens width Zeichen; kuerzere bleiben unveraendert."""
    out = []
    for line in lines:
        if len(line) <= width:
            out.append(line)
        else:
            lead = line[:len(line) - len(line.lstrip(" "))]
            out += _fit_line(line, width, lead + " ")
    return out


def _handy_fit(lines):
    return _fit_lines(lines, CALC_EXPLAIN_HANDY_WIDTH)


# ============================================================================
#  Ab 0.63.1 (Plan 0.63.1 Teil 1.3, Antwort 12 (A)): fit_lines - Umbruch eines
#  Ergebnis- bzw. Rechenweg-Textes auf die Breite eines Kastens in Zeichen.
#  Eine Quelle fuer PC (app_gui, Subnetting-Karte) und Handy (mobile/src/ui.py
#  FitBox, importiert von hier). Die Funktionen stammen unveraendert aus
#  mobile/src/ui.py (0.63, a74712d Z. 687-845); einzig _fit_pieces heisst hier
#  _fit_value_pieces (Namensgleichheit mit _fit_pieces oben). Reine
#  Textfunktionen ohne Oberflaeche.
# ============================================================================

import itertools  # noqa: E402  (nur fuer _fit_balanced)


def _fit_parts(line):
    """Zeile "Beschriftung : Wert" zerlegen -> (Einzug, Beschriftung, Wert).
    Ohne ": " oder ohne Wert: None. Folgezeilen ("        : Wert") haben
    eine leere Beschriftung."""
    pos = line.find(": ")
    if pos < 0:
        return None
    value = line[pos + 2:].strip()
    if not value:
        return None
    head = line[:pos]
    label = head.strip()
    indent = head[:len(head) - len(head.lstrip(" "))] if label else ""
    return indent, label, value


def _fit_sentence(line, zeichen):
    """Satz an Leerzeichen auf hoechstens `zeichen` Zeichen umbrechen; ein
    Wort, das allein zu lang ist, bleibt ganz. Zeilen mit Spalten (doppelte
    Leerzeichen) und ohne Leerzeichen bleiben unveraendert."""
    body = line.lstrip(" ")
    indent = line[:len(line) - len(body)]
    if "  " in body.rstrip() or " " not in body.strip():
        return [line]
    rows = []
    current = ""
    words = []
    for word in body.split():
        # ab 0.63.1 (Teil 1.6 Nr. 3): "RFC" und die Zahl dahinter bleiben
        # zusammen ("RFC 3849"), wie ein Wort
        if words and words[-1].endswith("RFC") and word[:1].isdigit():
            words[-1] += " " + word
        else:
            words.append(word)
    for word in words:
        if current and len(indent) + len(current) + 1 + len(word) > zeichen:
            rows.append(indent + current)
            current = word
        else:
            current = "%s %s" % (current, word) if current else word
    rows.append(indent + current)
    return rows


# Ab 0.63 (Plan 4.3, G-12): grosse Zahl mit Tausenderpunkten
_FIT_NUMBER = re.compile(r"^\d{1,3}(?:\.\d{3})+(?:,\d+)?$")


_FIT_UNIT = re.compile(r"^(?:%|[A-Za-zÄÖÜäöü/]{1,4})[,;)]?$")


# (in mobile/src/ui.py bis 0.63 hiess sie _fit_pieces; hier umbenannt, weil
# fisi_core schon ein anderes _fit_pieces fuer _fit_lines hat)
def _fit_value_pieces(word):
    """Bruchstellen eines Wortes, das allein nicht passt (Plan 4.3):
    IPv6 (enthaelt ':') nach einem Doppelpunkt ("::" bleibt zusammen),
    grosse Zahl VOR einem Tausenderpunkt (Punkt beginnt die neue Zeile).
    Sonst keine Bruchstelle."""
    if ":" in word:
        return [piece for piece in re.split(r"(?<=:)(?=[^:])", word) if piece]
    groups = word.split(".")
    if _FIT_NUMBER.match(word) and not (len(groups) == 4 and
                                        all(int(group) <= 255 for group in groups)):
        # (vier Gruppen bis 255 sehen aus wie eine IPv4-Adresse: nie teilen)
        return [piece for piece in re.split(r"(?=\.)", word) if piece]
    return [word]


def _fit_balanced(pieces, room):
    """Stuecke (ohne Trenner) auf moeglichst wenige Zeilen <= room verteilen,
    bei gleicher Zeilenzahl moeglichst gleich lang ("etwa in der Mitte")."""
    for count in range(1, len(pieces) + 1):
        best = None
        for cuts in itertools.combinations(range(1, len(pieces)), count - 1):
            bounds = (0,) + cuts + (len(pieces),)
            rows = ["".join(pieces[a:b]) for a, b in zip(bounds, bounds[1:])]
            longest = max(len(row) for row in rows)
            if longest <= room and (best is None or longest < best[0]):
                best = (longest, rows)
        if best:
            return best[1]
    return None


def _fit_value(value, room):
    """Wert auf Zeilen zu hoechstens `room` Zeichen verteilen (Plan 4.3):
    an Leerzeichen, ein zu langes Wort an seinen Bruchstellen (_fit_pieces).
    Eine allein stehende IPv6-Adresse bricht etwa in der Mitte. Was sich so
    nicht teilen laesst, bleibt ganz (dann "→ wischen"); Werte mit Spalten
    (doppelte Leerzeichen) bleiben unveraendert."""
    if room <= 0 or len(value) <= room or "  " in value:
        return [value]
    words = []
    for word in value.split(" "):
        # Zahl und Einheit bleiben zusammen ("288,00 Wh", "45 min", "925,9 %")
        if words and words[-1][-1:].isdigit() and _FIT_UNIT.match(word):
            words[-1] += " " + word
        elif words and words[-1].endswith("RFC") and word[:1].isdigit():
            # ab 0.63.1 (Teil 1.6 Nr. 3): "RFC" und die Zahl dahinter bleiben
            # zusammen ("RFC 3849)")
            words[-1] += " " + word
        else:
            words.append(word)
    if len(words) == 1 and ":" in value and " " not in value:
        rows = _fit_balanced(_fit_value_pieces(value), room)
        if rows:
            return rows
    rows = []
    current = ""
    for word in words:
        pieces = _fit_value_pieces(word) if len(word) > room else [word]
        for number, piece in enumerate(pieces):
            glue = " " if number == 0 and current else ""
            if current and len(current) + len(glue) + len(piece) > room:
                rows.append(current)
                current = piece
            else:
                current += glue + piece
    rows.append(current)
    return rows


def fit_lines(text, zeichen):
    """Ab 0.63 (B-E-01, F-8 b): Text fuer einen Kasten mit `zeichen` Zeichen
    Breite setzen. Eine Zeile "Beschriftung : Wert", die nicht passt, wird zu
    "Beschriftung:" und darunter "  Wert"; ihre Folgezeilen ("     : Wert",
    z.B. Datenmenge in Byte/KiB/MiB) ruecken mit. Passt der Wert auch dann
    nicht (Plan 4.3): IPv6 bricht nach einem Doppelpunkt etwa in der Mitte,
    eine grosse Zahl vor einem Tausenderpunkt, Text an Leerzeichen; die
    Fortsetzung steht wieder mit 2 Leerzeichen Einzug. Sonst wird nie mitten
    im Wort geteilt; was dann noch zu lang ist, bleibt ganz (der Kasten
    wischt, "→ wischen").
    Ein reiner Satz ohne "Beschriftung : Wert" (z.B. "Noch keine Berechnung
    durchgeführt.") bricht an Leerzeichen um, wenn er nicht passt; einzelne
    Woerter werden nie geteilt (Festlegung Hauptsitzung 0.63). Zeilen mit
    Spalten (zwei Leerzeichen hintereinander, z.B. Tabellen) bleiben, wie
    sie sind. zeichen None/0: Text unveraendert. Reine Textfunktion ohne
    Flet."""
    if not text or not zeichen or zeichen <= 0:
        return text
    lines = text.split("\n")
    out = []
    index = 0
    while index < len(lines):
        line = lines[index]
        parts = _fit_parts(line)
        if parts is None or not parts[1]:
            # keine Beschriftung (oder Folgezeile ohne Kopf)
            if parts is not None and len(line) > zeichen:
                out.extend("  " + row for row in _fit_value(parts[2], zeichen - 2))
            elif parts is None and len(line) > zeichen:
                out.extend(_fit_sentence(line, zeichen))
            else:
                out.append(line)
            index += 1
            continue
        block = [(line, parts)]
        index += 1
        while index < len(lines):
            follow = _fit_parts(lines[index])
            if follow is None or follow[1]:
                break
            block.append((lines[index], follow))
            index += 1
        if all(len(item) <= zeichen for item, _parts in block):
            out.extend(item for item, _parts in block)
            continue
        indent, label, _value = parts
        out.append("%s%s:" % (indent, label))
        for _item, item_parts in block:
            out.extend("%s  %s" % (indent, row)
                       for row in _fit_value(item_parts[2], zeichen - len(indent) - 2))
    return "\n".join(out)


def _wrap_para(text, lead, width):
    """Fliesstext mit gleichem Einzug in jeder Zeile."""
    return _fit_line(lead + text, width, lead) if len(lead + text) > width \
        else [lead + text]


def _join_items(first, items, glue, more, width):
    """Aufzaehlung (z. B. "A: 50, B: 20") auf Zeilen verteilen; ", " bleibt am
    Zeilenende, " + " kommt an den Anfang der Folgezeile. Platz fuer das
    Komma am Zeilenende braucht nur ein Eintrag, nach dem noch einer kommt."""
    lines, current = [], first + items[0]
    for number, item in enumerate(items[1:], 2):
        tail = glue.rstrip(" +") if number < len(items) else ""
        if len(current + glue + item + tail) <= width:
            current += glue + item
        elif glue.startswith(" "):
            lines.append(current)
            current = more + glue.lstrip() + item
        else:
            lines.append(current + glue.rstrip())
            current = more + item
    lines.append(current)
    return lines


def _pc_table(heads, rows, widths):
    """Tabelle am PC: Spalten wie vorgegeben breit; wird eine Zeile breiter
    als CALC_EXPLAIN_PC_WIDTH, nur so breit wie noetig."""
    def build(sizes):
        return [("  " + " ".join([cell.ljust(size) for cell, size in zip(cells, sizes)]
                                 + [cells[-1]])).rstrip() for cells in [heads] + rows]
    lines = build(widths)
    if max(len(line) for line in lines) > CALC_EXPLAIN_PC_WIDTH:
        lines = build([max(len(cells[i]) for cells in [heads] + rows)
                       for i in range(len(widths))])
    return lines


def _handy_address(caption, address, indent="  "):
    """Beschriftung und Adresse am Handy: passt beides nicht in eine Zeile,
    kommt die Adresse eingerueckt in die naechste; passt sie dann noch
    nicht (IPv6), wird nach einem Doppelpunkt etwa in der Mitte getrennt."""
    width = CALC_EXPLAIN_HANDY_WIDTH
    if len(caption + address) <= width:
        return [caption + address]
    head = [caption.rstrip()] if caption.strip() else []
    lead = indent if caption.strip() else caption
    if len(lead + address) <= width:
        return head + [lead + address]
    cut = address.find(":", len(address) // 2 - 3) + 1 or len(address) // 2
    return head + _handy_fit([lead + address[:cut], indent + address[cut:]])


def raid_values(level, disks, size):
    """Kennwerte eines RAID als Woerterbuch (brutto, netto, verlust,
    effizienz in Prozent, toleranz) oder None, wenn die Plattenzahl fuer das
    Level nicht passt. Genutzt vom RAID-Rechner und vom Lernspiel."""
    minimum, formula = RAID_RULES[level]
    if disks < minimum or (level == "RAID 10" and disks % 2 != 0):
        return None
    netto, tolerance = formula(disks, size)
    brutto = disks * size
    return {"brutto": brutto, "netto": netto, "verlust": brutto - netto,
            "effizienz": (netto / brutto * 100) if brutto else 0,
            "toleranz": tolerance}


def raid_min_disks(level):
    """Mindestanzahl Platten fuer eine neue Eingabe (Rechner und Spiel)."""
    return max(RAID_RULES[level][0], RAID_INPUT_MIN.get(level, 0))


def raid_input_problem(level, disks):
    """Meldung, wenn eine neue Eingabe die Mindestanzahl unterschreitet, die
    nur fuer die Eingabe gilt (RAID 0 mit 1 Platte), sonst leerer Text."""
    minimum = RAID_INPUT_MIN.get(level, 0)
    if disks < minimum:
        return "%s braucht mindestens %d Platten." % (level, minimum)
    return ""


def raid_input_values(level, disks, size):
    """Wie raid_values, aber mit den Mindestwerten fuer neue Eingaben."""
    if raid_input_problem(level, disks):
        return None
    return raid_values(level, disks, size)


def raid_tolerance_lines(level, disks, tolerance):
    """Ausfalltoleranz als Zeilen. Ab 0.62.3 bei RAID 10 wie im Rechenweg:
    1 Festplatte sicher, bis zu Anzahl / 2, wenn je Spiegelpaar nur eine
    ausfaellt (ungerade Anzahl ist ungueltig und kommt hier nicht an)."""
    text = plural(tolerance, "Festplatte", "Festplatten")
    if level != "RAID 10":
        return [text]
    return [text + " sicher", "(bis zu %d, wenn je Spiegelpaar" % (disks // 2),
            "nur eine ausfällt)"]


def raid_report(level, disks_text, size_text):
    """Berechnet Nutzkapazitaet, Verlust und Effizienz eines RAID."""
    # Ab 0.62.4: gemeinsame Leseregel (read_number), "1.000" = 1000
    disks = read_number(disks_text, "Anzahl Festplatten", ganz=True)
    size = read_number(size_text, "Kapazität je Festplatte (GB)")
    if disks <= 0 or size <= 0:
        raise InputError("Anzahl und Kapazität müssen größer als 0 sein.")

    values = raid_input_values(level, disks, size)
    if values is None:
        minimum = raid_min_disks(level)
        extra = " und eine gerade Anzahl" if level == "RAID 10" else ""
        return ("Ungültige Konfiguration für %s.\n\n"
                "Benötigt werden mindestens %d Festplatten%s."
                % (level, minimum, extra))
    # Ab 0.62.3: deutsche Schreibweise, Plattengroesse mit Nachkommastellen,
    # "Redundanz" statt "Paritaet" (RAID 0/1/10 haben keine Paritaet)
    tolerance = raid_tolerance_lines(level, disks, values["toleranz"])
    lines = [
        "RAID-Level            : %s" % level,
        "Festplatten           : %d x %s GB" % (disks, _de_short(size)),
        "Bruttokapazität       : %s GB" % de_number(values["brutto"]),
        "Nutzkapazität         : %s GB" % de_number(values["netto"]),
        "Redundanz / Verlust   : %s GB" % de_number(values["verlust"]),
        "Speichereffizienz     : %s %%" % de_number(values["effizienz"], 1),
        "Ausfalltoleranz       : %s" % tolerance[0],
    ]
    lines += [" " * 24 + line for line in tolerance[1:]]
    return "\n".join(lines)


SCREEN_FPS_MAX = 1000


def screen_report(width_text, height_text, depth, fps_text):
    """Berechnet das Datenvolumen eines Bildes und optional die Datenrate."""
    # Ab 0.62.4: gemeinsame Leseregel (read_number); Bildrate leer = ohne
    width = read_number(width_text, "Breite (Pixel)", ganz=True)
    height = read_number(height_text, "Höhe (Pixel)", ganz=True)
    try:
        depth = int(depth)
    except ValueError:
        raise InputError("Bitte gültige Zahlen für Breite, Höhe und "
                         "Bildrate eingeben.")
    fps = read_number(fps_text, "Bildrate (fps)") if fps_text.strip() else 0.0
    if width <= 0 or height <= 0:
        raise InputError("Breite und Höhe müssen größer als 0 sein.")
    if fps < 0:
        raise InputError("Die Bildrate darf nicht negativ sein.")
    # Ab 0.62.4: "23.976" liest die Leseregel als 23976 (Tausenderpunkt);
    # ueber 1.000 fps gibt es eine Meldung statt einer falschen Rechnung
    if fps > SCREEN_FPS_MAX:
        raise InputError("Die Bildrate ist zu groß (höchstens %s Bilder pro "
                         "Sekunde). Nachkommastellen bitte mit Komma eingeben, "
                         "zum Beispiel 23,976." % de_int(SCREEN_FPS_MAX))

    pixels = width * height
    bits = pixels * depth
    data_bytes = bits / 8
    data_kb = data_bytes / 1024
    data_mb = data_kb / 1024

    # Ab 0.62.3: deutsche Schreibweise, Doppelpunkte untereinander und
    # KiB/MiB/GiB, weil durch 1024 geteilt wird (Mbit/s bleibt dezimal)
    lines = [
        "Auflösung             : %d x %d Pixel" % (width, height),
        "Pixel gesamt          : %s" % de_int(pixels),
        "Farbtiefe             : %d Bit/Pixel" % depth,
        "Datenmenge pro Bild   : %s Bit" % de_int(bits),
        "                      : %s Byte" % de_int(int(data_bytes)),
        "                      : %s KiB" % de_number(data_kb),
        "                      : %s MiB" % de_number(data_mb),
    ]
    if fps > 0:
        bytes_per_sec = data_bytes * fps
        mbit_per_sec = bytes_per_sec * 8 / 1_000_000
        mb_per_sec = bytes_per_sec / (1024 * 1024)
        gb_per_min = bytes_per_sec * 60 / (1024 ** 3)
        lines += [
            "",
            "Bildrate (fps)        : %.0f Bilder/Sekunde" % fps,
            "Datenrate             : %s MiB/s" % de_number(mb_per_sec),
            "                      : %s Mbit/s" % de_number(mbit_per_sec),
            "                      : %s GiB/Minute" % de_number(gb_per_min),
        ]
    return "\n".join(lines)


# ----------------------------------------------------------------------------
#  USV-Kapazitaetsrechner (ab 0.58, Plan 2)
# ----------------------------------------------------------------------------
# Formeln und Quellen (vollstaendig im Bericht 0.58):
#   Wirkleistung P (W) = Scheinleistung S (VA) x Leistungsfaktor
#       (de.wikipedia.org/wiki/Leistungsfaktor: Leistungsfaktor = P / S)
#   Akku (Ah) = ((Last W / Wirkungsgrad) / Strangspannung V) x Stunden
#       (EnerSys, "Runtime and right-sizing a UPS", Beispiel
#        ((450 / 0,84) / 48) x 8 = 89,29 Ah; ohne Herstellerwert 0,80 annehmen)
#   Laufzeit (h) = Akku-Energie (Wh) x Wirkungsgrad / Last W  (dieselbe Formel
#       nach der Zeit umgestellt)
#   Alterungszuschlag 25 % (Faktor 1,25): IEEE 485 nach Vertiv/Battcon 2000 -
#       am Lebensende hat der Akku noch 80 % der Nennkapazitaet
#   Empfehlung: Last hoechstens 80 % der USV-Nennleistung (Schneider Electric,
#       FAQ000268376: "preferably around 80% of the UPS' maximum capacity")
# Vereinfachungen (im Rechner sichtbar): volle Nennkapazitaet nutzbar,
# kein Peukert-Effekt, keine Temperatur. Leistungsfaktor 0,9 ist nur ein
# Beispielwert (Annahme) - richtig ist der Wert vom Typenschild/Datenblatt.

UPS_TITLE = "USV-Kapazität"
UPS_SUBTITLE = "Akku, Laufzeit, Empfehlung"
UPS_GROUP_LOAD = "LAST UND USV"
UPS_GROUP_BATTERY = "AKKU UND LAUFZEIT"
UPS_TASKS_TITLE = "Übungsaufgaben"
UPS_TASK_NEXT = "Nächste Aufgabe"
UPS_SOLUTION_SHOW = "Lösung anzeigen"
UPS_SOLUTION_HIDE = "Lösung ausblenden"
UPS_UNITS = [("W", "W"), ("VA", "VA")]
UPS_MODES = [("akku", "Akku berechnen"), ("laufzeit", "Laufzeit berechnen"),
             ("empfehlung", "Empfehlung")]
UPS_LOAD_LIMIT = 80        # Prozent der Nennleistung (Schneider Electric)
UPS_PF_DEFAULT = 0.9       # Annahme, Beispielwert
UPS_ETA_DEFAULT = 80       # Prozent (EnerSys: ohne Herstellerwert 0,80)
UPS_AGING_DEFAULT = 25     # Prozent (IEEE 485: Faktor 1,25)

# Vorbelegung der Felder (PC und Handy gleich)
UPS_FIELDS = [
    # Schluessel, Beschriftung, Vorgabe
    ("last", "Last", "600"),
    ("pf", "Leistungsfaktor (λ)", "0,9"),
    ("eta", "Wirkungsgrad der USV (%)", "80"),
    ("minuten", "Gewünschte Laufzeit (min)", "15"),
    ("alterung", "Alterungszuschlag (%)", "25"),
    ("block_v", "Spannung je Akku-Block (V)", "12"),
    ("block_ah", "Kapazität je Akku-Block (Ah)", "12"),
    ("reihe", "Blöcke in Reihe", "2"),
    ("parallel", "Stränge parallel", "1"),
    ("nenn_va", "USV-Nennleistung (VA)", "1500"),
    ("nenn_w", "USV-Nennleistung (W, optional)", "900"),
]
UPS_FIELD_CAPTIONS = {key: caption for key, caption, _value in UPS_FIELDS}
UPS_FIELD_DEFAULTS = {key: value for key, _caption, value in UPS_FIELDS}
UPS_UNIT_CAPTION = "Einheit der Last"

# Grenzen je Feld: (kleinster Wert, groesster Wert, ganze Zahl, 0 erlaubt)
UPS_LIMITS = {
    "last": (0, 1000000, False, False),
    "pf": (0.1, 1, False, True),
    "eta": (10, 100, False, True),
    "minuten": (0, 1440, False, False),
    "alterung": (0, 100, False, True),
    "block_v": (0, 1000, False, False),
    "block_ah": (0, 10000, False, False),
    "reihe": (1, 100, True, True),
    "parallel": (1, 20, True, True),
    "nenn_va": (0, 1000000, False, False),
    "nenn_w": (0, 1000000, False, False),
}

UPS_RULE_TEXT = (
    "Regel für die Empfehlung: Die USV ist passend, wenn (1) die Last höchstens "
    "%d %% ihrer Nennleistung in VA und in W ausmacht (20 %% Reserve, Empfehlung "
    "von Schneider Electric) und (2) der Akku auch am Lebensende (nach dem "
    "Alterungszuschlag) die gewünschte Laufzeit schafft. Sonst ist sie zu klein."
    % UPS_LOAD_LIMIT)
UPS_SIMPLE_TEXT = (
    "Vereinfacht: Der Rechner nimmt die volle Nennkapazität des Akkus. Bei kurzen "
    "Laufzeiten (hoher Strom), Kälte oder Hitze liefert ein Bleiakku deutlich "
    "weniger. Für eine echte Planung die Laufzeittabelle des Herstellers nutzen. "
    "Der Leistungsfaktor 0,9 ist nur ein Beispielwert, der echte Wert steht auf "
    "dem Typenschild oder im Datenblatt.")


def de_number(value, digits=2):
    """Zahl in deutscher Schreibweise (1.234,56). Ab 0.62.3 kaufmaennisch
    gerundet: 390,625 -> 390,63 (vorher je nach interner Darstellung 390,62).
    Unendlich und "nan" (Eingabe "inf") wie bis 0.62.2 ohne Decimal."""
    if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
        text = "{:,.{}f}".format(value, digits)
    else:
        exact = Decimal(repr(value)) if isinstance(value, float) else Decimal(value)
        with localcontext() as context:
            context.prec = 400       # auch 1e300 (Eingabe "1e300") ohne Fehler
            rounded = exact.quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)
        text = "{:,.{}f}".format(rounded, digits)
    return text.replace(",", "#").replace(".", ",").replace("#", ".")


def de_int(value):
    """Ganze Zahl mit Tausenderpunkten (ab 0.62.3), auch sehr gross (IPv6)."""
    return "{:,}".format(int(value)).replace(",", ".")


def _de_short(value, digits=2):
    """Wie de_number, aber ohne ueberfluessige Nullen (0,9 statt 0,90)."""
    text = de_number(value, digits)
    if "," in text:
        text = text.rstrip("0").rstrip(",")
    return text


def ups_number(fields, key):
    """Liest ein Feld des USV-Rechners (Komma oder Punkt) und prueft die
    Grenzen. Fehler kommen als InputError mit der Feldbeschriftung."""
    caption = UPS_FIELD_CAPTIONS[key]
    low, high, integer, zero_ok = UPS_LIMITS[key]
    # Ab 0.62.4: gemeinsame Leseregel (read_number), "1.000" = 1000
    value = read_number(str(fields.get(key, "") or ""), caption, ganz=integer)
    too_small = value < low if zero_ok else value <= low
    if too_small or value > high:
        if zero_ok:
            raise InputError("%s muss zwischen %s und %s liegen."
                             % (caption, _de_short(low), _de_short(high)))
        raise InputError("%s muss größer als %s und höchstens %s sein."
                         % (caption, _de_short(low), _de_short(high)))
    return int(value) if integer else value


def ups_load(load, unit, pf):
    """Last in W und VA: P = S x Leistungsfaktor."""
    if unit == "VA":
        return load * pf, load
    return load, load / pf


def ups_battery_need(watt, eta_pct, minutes, aging_pct, string_volt):
    """Berechnung A: noetige Akku-Energie und Kapazitaet je Strang."""
    hours = minutes / 60.0
    out_wh = watt * hours                      # Energie fuer die Last
    battery_wh = out_wh / (eta_pct / 100.0)    # was der Akku liefern muss
    need_wh = battery_wh * (1 + aging_pct / 100.0)
    return {"stunden": hours, "last_wh": out_wh, "akku_wh": battery_wh,
            "bedarf_wh": need_wh, "bedarf_ah": need_wh / string_volt}


def ups_battery_energy(block_v, block_ah, series, parallel):
    """Energie (Wh) eines Akkus aus Bloecken in Reihe und Straengen."""
    return block_v * series * block_ah * parallel


def ups_runtime(watt, eta_pct, battery_wh, aging_pct):
    """Berechnung B: Laufzeit in Minuten, neu und am Lebensende."""
    new = battery_wh * (eta_pct / 100.0) / watt * 60.0
    return {"neu": new, "ende": new / (1 + aging_pct / 100.0)}


def ups_end_share(aging_pct):
    """Restkapazitaet am Lebensende in Prozent (1,25 -> 80 %)."""
    return 100.0 / (1 + aging_pct / 100.0)


def ups_check(watt, va, rated_va, rated_w, minutes_end, minutes):
    """Empfehlung nach UPS_RULE_TEXT. Liefert (passend, Pruefzeilen)."""
    checks = []
    share_va = va / rated_va * 100
    checks.append((share_va <= UPS_LOAD_LIMIT,
                   "Auslastung Scheinleistung: %s VA von %s VA = %s %%"
                   % (de_number(va, 0), de_number(rated_va, 0),
                      de_number(share_va, 1))))
    if rated_w:
        share_w = watt / rated_w * 100
        checks.append((share_w <= UPS_LOAD_LIMIT,
                       "Auslastung Wirkleistung: %s W von %s W = %s %%"
                       % (de_number(watt, 0), de_number(rated_w, 0),
                          de_number(share_w, 1))))
    checks.append((minutes_end >= minutes,
                   "Laufzeit am Lebensende: %s min, gewünscht %s min"
                   % (de_number(minutes_end, 1), _de_short(minutes))))
    return all(ok for ok, _text in checks), checks


def _ups_bars(minutes, runtime=None, aging_pct=0):
    """Balken fuer das Bild: gewuenscht, Akku neu, Akku am Lebensende."""
    bars = [{"label": "Gewünschte Laufzeit", "minuten": minutes, "art": "ziel"}]
    if runtime is not None:
        bars.append({"label": "Akku neu", "minuten": runtime["neu"], "art": "neu"})
        bars.append({"label": "Akku am Lebensende (%s %%)"
                     % de_number(ups_end_share(aging_pct), 0),
                     "minuten": runtime["ende"],
                     "art": "ok" if runtime["ende"] >= minutes else "knapp"})
    top = max(bar["minuten"] for bar in bars) or 1
    for bar in bars:
        bar["anteil"] = bar["minuten"] / top
        bar["text"] = "%s min" % de_number(bar["minuten"], 1)
        if bar["art"] == "knapp":
            bar["text"] += ", zu kurz"
    return bars


def ups_picture_summary(picture):
    """Vorlesetext des Bildes (TalkBack), gleiche Angaben wie das Bild."""
    parts = ["Last %s, %s" % (picture["last"], picture["last_detail"]),
             "USV %s, %s" % (picture["usv"], picture["usv_detail"]),
             "Akku %s, %s" % (picture["akku"], picture["akku_detail"])]
    parts += ["%s %s" % (bar["label"], bar["text"]) for bar in picture["balken"]]
    if picture.get("urteil"):
        parts.append("Empfehlung: USV %s" % picture["urteil"])
    return "Bild: " + "; ".join(parts)


def ups_calculate(mode, fields, unit="W"):
    """Rechnet eine der drei Aufgaben des USV-Rechners.

    mode: "akku" (Berechnung A), "laufzeit" (Berechnung B) oder
    "empfehlung". fields: Texte der Eingabefelder (Schluessel aus
    UPS_FIELDS). Liefert {"text", "bild", "passend"}; "bild" beschreibt
    die bildliche Darstellung (Kaesten Last -> USV -> Akku und Balken der
    Laufzeit) fuer PC und Handy gleich. Ungueltige Eingaben -> InputError.
    """
    if mode not in dict(UPS_MODES):
        raise InputError("Unbekannte Berechnung.")
    load = ups_number(fields, "last")
    pf = ups_number(fields, "pf")
    eta = ups_number(fields, "eta")
    minutes = ups_number(fields, "minuten")
    aging = ups_number(fields, "alterung")
    block_v = ups_number(fields, "block_v")
    series = ups_number(fields, "reihe")
    string_v = block_v * series
    watt, va = ups_load(load, unit, pf)

    lines = [
        "Last                  : %s W / %s VA (Leistungsfaktor %s)"
        % (de_number(watt, 0), de_number(va, 0), _de_short(pf)),
        "Wirkungsgrad der USV  : %s %%" % _de_short(eta),
        "Strangspannung        : %s x %s V = %s V"
        % (series, _de_short(block_v), _de_short(string_v)),
    ]
    picture = {"last": "%s W" % de_number(watt, 0),
               "last_detail": "%s VA, λ %s" % (de_number(va, 0), _de_short(pf)),
               "usv": "η %s %%" % _de_short(eta), "usv_detail": "Wirkungsgrad",
               "akku": "", "akku_detail": "", "auslastung": None,
               "grenze": UPS_LOAD_LIMIT, "balken": [],
               "urteil": None}
    passend = None

    if mode == "akku":
        need = ups_battery_need(watt, eta, minutes, aging, string_v)
        runtime = {"neu": minutes * (1 + aging / 100.0), "ende": minutes}
        lines += [
            "Gewünschte Laufzeit   : %s min = %s h"
            % (_de_short(minutes), de_number(need["stunden"], 3)),
            "",
            "Energie für die Last  : %s Wh" % de_number(need["last_wh"]),
            "Energie aus dem Akku  : %s Wh (geteilt durch Wirkungsgrad)"
            % de_number(need["akku_wh"]),
            "Mit Alterungszuschlag : %s Wh (+%s %%)"
            % (de_number(need["bedarf_wh"]), _de_short(aging)),
            "Benötigte Kapazität   : %s Ah bei %s V"
            % (de_number(need["bedarf_ah"]), _de_short(string_v)),
        ]
        picture["akku"] = "%s Wh" % de_number(need["bedarf_wh"], 0)
        picture["akku_detail"] = "%s Ah bei %s V" % (de_number(need["bedarf_ah"], 1),
                                                    _de_short(string_v))
        picture["balken"] = _ups_bars(minutes, runtime, aging)
    else:
        block_ah = ups_number(fields, "block_ah")
        parallel = ups_number(fields, "parallel")
        battery_wh = ups_battery_energy(block_v, block_ah, series, parallel)
        runtime = ups_runtime(watt, eta, battery_wh, aging)
        lines += [
            "Akku                  : %s x %s V, %s Ah, %s"
            % (series, _de_short(block_v), _de_short(block_ah),
               plural(parallel, "Strang", "Stränge")),
            "Akku-Energie          : %s V x %s Ah x %s = %s Wh"
            % (_de_short(string_v), _de_short(block_ah), parallel,
               de_number(battery_wh)),
            "",
            "Laufzeit (Akku neu)   : %s min" % de_number(runtime["neu"], 1),
            "Laufzeit (Lebensende) : %s min (%s %% Kapazität)"
            % (de_number(runtime["ende"], 1), de_number(ups_end_share(aging), 0)),
        ]
        picture["akku"] = "%s Wh" % de_number(battery_wh, 0)
        picture["akku_detail"] = "%s x %s V, %s Ah" % (series * parallel,
                                                      _de_short(block_v),
                                                      _de_short(block_ah))
        picture["balken"] = _ups_bars(minutes, runtime, aging)

        if mode == "empfehlung":
            rated_va = ups_number(fields, "nenn_va")
            rated_w = ups_number(fields, "nenn_w") if str(
                fields.get("nenn_w", "") or "").strip() else None
            passend, checks = ups_check(watt, va, rated_va, rated_w,
                                        runtime["ende"], minutes)
            share = max(va / rated_va, watt / rated_w if rated_w else 0) * 100
            picture["auslastung"] = share
            picture["usv_detail"] = "Auslastung %s %%" % de_number(share, 0)
            picture["urteil"] = "passend" if passend else "zu klein"
            lines += ["", "Empfehlung            : USV %s"
                      % ("passend" if passend else "zu klein")]
            lines += ["  %s  %s" % ("ja  " if ok else "nein", text)
                      for ok, text in checks]
            if rated_w is None:
                lines.append("  Hinweis: ohne Nennleistung in W nur VA geprüft.")
    lines += ["", UPS_SIMPLE_TEXT]
    return {"text": "\n".join(lines), "bild": picture, "passend": passend}


# Uebungsaufgaben zum USV-Rechner: Werte typisch aus der Praxis, Loesung wird
# mit denselben Formeln gerechnet. "annahmen" nennt nur, was die Aufgabe offen
# laesst und der Loesungsweg voraussetzt (Nachtrag 0.58), sonst "keine.".
UPS_TASKS = [
    {"titel": "Scheinleistung und Wirkleistung",
     "frage": "Ein Server hat laut Typenschild 800 VA bei einem Leistungsfaktor "
              "von 0,9. Wie groß ist die Wirkleistung in W? Welche Nennleistung "
              "in VA sollte die USV mindestens haben, wenn die Last höchstens "
              "80 % betragen soll?",
     "annahmen": "keine.",
     "werte": {"s": 800, "pf": 0.9}},
    {"titel": "Akku-Kapazität (Beispiel EnerSys)",
     "frage": "Eine USV soll 450 W Last 8 Stunden lang versorgen. Der "
              "Wechselrichter hat bei dieser Last einen Wirkungsgrad von 84 %, "
              "der Akku-Strang hat 48 V. Wie viel Ah braucht der Strang?",
     "annahmen": "Kein Alterungszuschlag, volle Nennkapazität nutzbar.",
     "werte": {"w": 450, "eta": 84, "min": 480, "v": 48, "alt": 0}},
    {"titel": "Laufzeit eines vorhandenen Akkus",
     "frage": "Eine kleine USV hat 2 Blöcke zu je 12 V und 9 Ah in Reihe. Die "
              "Last beträgt 300 W, der Wirkungsgrad 85 %. Wie lange läuft sie "
              "mit neuem Akku und am Lebensende (80 % Kapazität)?",
     "annahmen": "Volle Nennkapazität nutzbar.",
     "werte": {"w": 300, "eta": 85, "v": 12, "ah": 9, "reihe": 2, "par": 1,
               "alt": 25}},
    {"titel": "Passt die USV?",
     "frage": "Angeschlossen sind 1.200 VA bei einem Leistungsfaktor von 0,9. "
              "Die USV hat 1.500 VA und 1.000 W Nennleistung. Ist sie nach der "
              "80-%-Regel passend?",
     "annahmen": "Nur die Leistung wird geprüft, nicht die Laufzeit.",
     "werte": {"s": 1200, "pf": 0.9, "nenn_va": 1500, "nenn_w": 1000}},
    {"titel": "Akku mit Alterungszuschlag",
     "frage": "Ein Switch-Schrank braucht 1.000 W für 10 Minuten. Wirkungsgrad "
              "90 %, Strangspannung 48 V, Alterungszuschlag 25 %. Wie viel Wh "
              "und Ah braucht der Akku?",
     "annahmen": "Volle Nennkapazität nutzbar.",
     "werte": {"w": 1000, "eta": 90, "min": 10, "v": 48, "alt": 25}},
    {"titel": "Wie viele Stränge?",
     "frage": "500 W sollen 30 Minuten überbrückt werden. Wirkungsgrad 80 %, "
              "Alterungszuschlag 25 %. Ein Strang besteht aus 2 Blöcken zu je "
              "12 V und 12 Ah in Reihe. Wie viele Stränge braucht man parallel?",
     "annahmen": "Volle Nennkapazität nutzbar.",
     "werte": {"w": 500, "eta": 80, "min": 30, "alt": 25, "v": 12, "ah": 12,
               "reihe": 2}},
]


def ups_task_solution(index):
    """Loesungsweg einer Uebungsaufgabe (gerechnet, nicht abgeschrieben)."""
    task = UPS_TASKS[index]
    w = task["werte"]
    if index == 0:
        watt, _va = ups_load(w["s"], "VA", w["pf"])
        need = w["s"] / (UPS_LOAD_LIMIT / 100.0)
        return ("P = S x Leistungsfaktor = %s VA x %s = %s W\n"
                "Nennleistung = Last / 0,8 = %s VA / 0,8 = %s VA\n"
                "Antwort: %s W Wirkleistung, USV mit mindestens %s VA."
                % (de_number(w["s"], 0), _de_short(w["pf"]), de_number(watt, 0),
                   de_number(w["s"], 0), de_number(need, 0), de_number(watt, 0),
                   de_number(need, 0)))
    if index in (1, 4):
        need = ups_battery_need(w["w"], w["eta"], w["min"], w["alt"], w["v"])
        hours = _de_short(need["stunden"], 4)
        hours_first = hours + " h"
        fraction = Fraction(w["min"], 60)
        if fraction.denominator != 1 and round(need["stunden"], 4) != need["stunden"]:
            # Ab 0.62.3: 10 min = 1/6 h, damit der Zwischenwert nachrechenbar ist
            hours_first = "%s h (≈ %s h)" % (fraction, hours)
            hours = str(fraction)
        steps = ["Zeit = %s min / 60 = %s" % (_de_short(w["min"]), hours_first),
                 "Energie Last = %s W x %s h = %s Wh"
                 % (de_number(w["w"], 0), hours, de_number(need["last_wh"])),
                 "Energie Akku = %s Wh / %s = %s Wh"
                 % (de_number(need["last_wh"]), _de_short(w["eta"] / 100.0),
                    de_number(need["akku_wh"]))]
        if w["alt"]:
            steps.append("Mit Alterungszuschlag = %s Wh x %s = %s Wh"
                         % (de_number(need["akku_wh"]),
                            _de_short(1 + w["alt"] / 100.0),
                            de_number(need["bedarf_wh"])))
        steps.append("Kapazität = %s Wh / %s V = %s Ah"
                     % (de_number(need["bedarf_wh"]), w["v"],
                        de_number(need["bedarf_ah"])))
        steps.append("Antwort: %s Wh, also %s Ah bei %s V."
                     % (de_number(need["bedarf_wh"]), de_number(need["bedarf_ah"]),
                        w["v"]))
        return "\n".join(steps)
    if index == 2:
        energy = ups_battery_energy(w["v"], w["ah"], w["reihe"], w["par"])
        runtime = ups_runtime(w["w"], w["eta"], energy, w["alt"])
        return ("Akku-Energie = %s x %s V x %s Ah = %s Wh\n"
                "Laufzeit = %s Wh x %s / %s W x 60 = %s min\n"
                "Lebensende = %s min x 0,8 = %s min\n"
                "Antwort: neu etwa %s min, am Lebensende etwa %s min."
                % (w["reihe"], w["v"], w["ah"], de_number(energy, 0),
                   de_number(energy, 0), _de_short(w["eta"] / 100.0), w["w"],
                   de_number(runtime["neu"]), de_number(runtime["neu"]),
                   de_number(runtime["ende"]), de_number(runtime["neu"], 1),
                   de_number(runtime["ende"], 1)))
    if index == 3:
        watt, va = ups_load(w["s"], "VA", w["pf"])
        share_va = va / w["nenn_va"] * 100
        share_w = watt / w["nenn_w"] * 100
        return ("P = %s VA x %s = %s W\n"
                "Auslastung VA = %s / %s = %s %% (höchstens 80 %%: %s)\n"
                "Auslastung W = %s / %s = %s %% (höchstens 80 %%: %s)\n"
                "Antwort: Die USV ist zu klein, weil die Wirkleistung über "
                "80 %% liegt (sogar über 100 %%)."
                % (de_number(w["s"], 0), _de_short(w["pf"]), de_number(watt, 0),
                   de_number(va, 0), de_number(w["nenn_va"], 0),
                   de_number(share_va, 0), "ja" if share_va <= 80 else "nein",
                   de_number(watt, 0), de_number(w["nenn_w"], 0),
                   de_number(share_w, 0), "ja" if share_w <= 80 else "nein"))
    # index 5: Anzahl Straenge
    need = ups_battery_need(w["w"], w["eta"], w["min"], w["alt"], w["v"] * w["reihe"])
    string_wh = ups_battery_energy(w["v"], w["ah"], w["reihe"], 1)
    count = ups_strings_needed(need["bedarf_wh"], string_wh)
    return ("Bedarf = %s W x %s h / %s x %s = %s Wh\n"
            "Ein Strang = %s x %s V x %s Ah = %s Wh\n"
            "Stränge = %s Wh / %s Wh = %s, aufgerundet %d\n"
            "Antwort: %d Stränge parallel (%s Wh)."
            % (w["w"], _de_short(need["stunden"]), _de_short(w["eta"] / 100.0),
               _de_short(1 + w["alt"] / 100.0), de_number(need["bedarf_wh"]),
               w["reihe"], w["v"], w["ah"], de_number(string_wh, 0),
               de_number(need["bedarf_wh"]), de_number(string_wh, 0),
               de_number(need["bedarf_wh"] / string_wh), count, count,
               de_number(string_wh * count, 0)))


def ups_strings_needed(need_wh, string_wh):
    """Anzahl paralleler Straenge (immer aufrunden)."""
    import math
    return max(1, int(math.ceil(need_wh / float(string_wh) - 1e-6)))


def ups_task_text(index, solution=False):
    """Aufgabe (und auf Wunsch der Loesungsweg) als Text."""
    task = UPS_TASKS[index % len(UPS_TASKS)]
    text = "Aufgabe %d von %d: %s\n\n%s\n\nAnnahmen: %s" % (
        index % len(UPS_TASKS) + 1, len(UPS_TASKS), task["titel"], task["frage"],
        task["annahmen"])
    if solution:
        text += "\n\nLösungsweg:\n" + ups_task_solution(index % len(UPS_TASKS))
    return text


CALC_EXPLAIN_UPS = (
    "RECHENWEG USV-KAPAZITÄT\n"
    "Am Beispiel 600 W Last, Wirkungsgrad 80 %, 15 Minuten,\n"
    "Akku 2 x 12 V in Reihe (24 V), Alterungszuschlag 25 %\n\n"
    "SCHRITT 1: VA und W\n"
    "   Wirkleistung P (W) = Scheinleistung S (VA) x Leistungsfaktor\n"
    "   600 W / 0,9 = 667 VA (Leistungsfaktor 0,9 ist eine Annahme,\n"
    "   der echte Wert steht auf dem Typenschild).\n\n"
    "SCHRITT 2: Energie für die Last\n"
    "   Energie (Wh) = Last (W) x Zeit (h) = 600 W x 0,25 h = 150 Wh\n\n"
    "SCHRITT 3: Verluste der USV\n"
    "   Der Akku muss mehr liefern, weil die USV Verluste hat:\n"
    "   150 Wh / 0,8 = 187,5 Wh\n\n"
    "SCHRITT 4: Alterungszuschlag\n"
    "   Ein Bleiakku gilt mit 80 % Restkapazität als verbraucht. Damit\n"
    "   er auch dann reicht, plant man 25 % mehr ein (Faktor 1,25):\n"
    "   187,5 Wh x 1,25 = 234,38 Wh\n\n"
    "SCHRITT 5: Kapazität in Ah\n"
    "   Ah = Wh / Strangspannung = 234,38 Wh / 24 V = 9,77 Ah\n\n"
    "LAUFZEIT (umgekehrt)\n"
    "   Akku-Energie = 24 V x 12 Ah = 288 Wh\n"
    "   Laufzeit = 288 Wh x 0,8 / 600 W x 60 = 23,04 min (neu)\n"
    "   am Lebensende: 23,04 min x 0,8 = 18,43 min\n\n"
    "EMPFEHLUNG\n"
    "   Die Last soll höchstens 80 % der USV-Nennleistung betragen\n"
    "   (in VA und in W). Beispiel USV 1.500 VA / 900 W:\n"
    "   667 / 1.500 = 44 %, 600 / 900 = 67 % -> passend,\n"
    "   18,43 min am Lebensende >= 15 min -> passend.\n\n"
    "QUELLEN\n"
    "   Leistungsfaktor = P / S: Wikipedia, Leistungsfaktor\n"
    "   Ah-Formel und Wirkungsgrad 0,80: EnerSys, Runtime and\n"
    "   right-sizing a UPS\n"
    "   Faktor 1,25 und 80 %: IEEE 485 (Vertiv/Battcon 2000)\n"
    "   80 % Auslastung: Schneider Electric, FAQ000268376"
)

# Rechenwege zum Aufklappen unter den Praxis-Rechnern
# Ab 0.62.3 (Teil E): Begriffe einheitlich (Netzadresse, Host-Adresse,
# Hostbits, Praefixlaenge, UND/ODER, Nutzkapazitaet, Festplatten, KiB/MiB),
# Spalten gerade, Fehler aus der Pruefung e3 berichtigt. Zu jedem Rechenweg
# gibt es eine Handy-Fassung (..._HANDY, weiter unten) mit denselben
# Schritten und Zahlen, aber hoechstens 28 Zeichen je Zeile.
CALC_EXPLAIN_SUBNET = (
    "RECHENWEG SUBNETTING\n"
    "Am Beispiel 192.168.1.50/24\n\n"
    "SCHRITT 1: Präfixlänge in Subnetzmaske umwandeln\n"
    "   Die Präfixlänge (die Zahl nach dem /) gibt an, wie viele\n"
    "   Bits von links auf 1 gesetzt sind. /24 bedeutet: die ersten\n"
    "   24 Bit der 32-Bit-Subnetzmaske sind 1, der Rest ist 0.\n"
    "   /24 = 11111111.11111111.11111111.00000000\n"
    "       =   255   .  255   .  255   .   0\n"
    "   -> Subnetzmaske: 255.255.255.0\n\n"
    "SCHRITT 2: Netzadresse berechnen\n"
    "   Netzadresse = IP-Adresse UND Subnetzmaske\n"
    "   (bitweise UND-Verknüpfung: nur wenn IP-Adresse und\n"
    "   Maske an derselben Stelle eine 1 haben, bleibt dort\n"
    "   eine 1 stehen)\n"
    "     192.168.1.50    = 11000000.10101000.00000001.00110010\n"
    "   UND 255.255.255.0 = 11111111.11111111.11111111.00000000\n"
    "   -------------------------------------------------------\n"
    "     Ergebnis        = 11000000.10101000.00000001.00000000\n"
    "   -> Netzadresse: 192.168.1.0\n\n"
    "SCHRITT 3: Broadcast-Adresse berechnen\n"
    "   Wildcard-Maske = invertierte Subnetzmaske (alle Bits\n"
    "   umgedreht): 255.255.255.0 -> 0.0.0.255\n"
    "   Broadcast-Adresse = Netzadresse ODER Wildcard-Maske\n"
    "   (bitweise ODER-Verknüpfung: alle Hostbits\n"
    "   werden auf 1 gesetzt)\n"
    "   -> Broadcast-Adresse: 192.168.1.255\n\n"
    "SCHRITT 4: Nutzbare Host-Adressen zählen\n"
    "   Anzahl aller Adressen im Netz = 2^(32 - Präfixlänge)\n"
    "   Bei /24: 2^(32 - 24) = 2^8 = 256 Adressen\n"
    "   Davon sind die Netzadresse (192.168.1.0) und die\n"
    "   Broadcast-Adresse (192.168.1.255) nicht als Host vergebbar,\n"
    "   deshalb -2:\n"
    "   Nutzbare Hosts = 2^(32 - Präfixlänge) - 2 = 256 - 2 = 254\n"
    "   -> erste Host-Adresse: 192.168.1.1\n"
    "   -> letzte Host-Adresse: 192.168.1.254\n\n"
    "HINWEIS ZU IPv6\n"
    "   IPv6 kennt keine Broadcast-Adresse, daher entfällt dort der\n"
    "   Abzug von 2 Adressen. Gezählt werden alle\n"
    "   2^(128 - Präfixlänge) Adressen (einzelne Adressen sind\n"
    "   reserviert, z.B. Subnet-Router-Anycast)."
)
CALC_EXPLAIN_RAID = (
    "RECHENWEG RAID\n"
    "Am Beispiel 4 Festplatten x 1.000 GB (Bruttokapazität 4.000 GB)\n\n"
    "RAID 0 - Striping (ohne Redundanz, min. 2 Festplatten)\n"
    "   Die Daten werden ohne Redundanz auf alle Festplatten verteilt.\n"
    "   Formel:  Nutzkapazität = Anzahl x Kapazität\n"
    "   Beispiel: 4 x 1.000 GB = 4.000 GB nutzbar\n"
    "   Ausfalltoleranz: 0 Festplatten (fällt eine aus, sind alle\n"
    "   Daten weg)\n\n"
    "RAID 1 - Spiegelung (Mirroring, min. 2 Festplatten)\n"
    "   Die Daten werden 1:1 auf alle weiteren Festplatten gespiegelt\n"
    "   (bei 2 Festplatten auf die zweite).\n"
    "   Formel:  Nutzkapazität = 1 x Kapazität\n"
    "   Beispiel: 1.000 GB nutzbar (bei 4 Festplatten stehen nur\n"
    "   1.000 GB Nutzkapazität zur Verfügung, der Rest ist Spiegelung)\n"
    "   Ausfalltoleranz: n-1 Festplatten\n\n"
    "RAID 5 - verteilte Parität (min. 3 Festplatten)\n"
    "   Eine Festplatte Kapazität wird rechnerisch für Paritätsdaten\n"
    "   verwendet (die Parität selbst liegt verteilt auf allen\n"
    "   Festplatten).\n"
    "   Formel:  Nutzkapazität = (Anzahl - 1) x Kapazität\n"
    "   Beispiel: (4 - 1) x 1.000 GB = 3.000 GB nutzbar\n"
    "   Ausfalltoleranz: 1 Festplatte\n\n"
    "RAID 6 - doppelte Parität (min. 4 Festplatten)\n"
    "   Wie RAID 5, aber mit doppelter Parität für mehr Sicherheit.\n"
    "   Formel:  Nutzkapazität = (Anzahl - 2) x Kapazität\n"
    "   Beispiel: (4 - 2) x 1.000 GB = 2.000 GB nutzbar\n"
    "   Ausfalltoleranz: 2 Festplatten\n\n"
    "RAID 10 - Spiegelung + Striping (min. 4 Festplatten, gerade Anzahl)\n"
    "   Je zwei Festplatten werden gespiegelt (RAID 1), diese\n"
    "   Spiegelpaare werden anschließend im Striping-Verfahren\n"
    "   (RAID 0) zusammengefasst.\n"
    "   Formel:  Nutzkapazität = (Anzahl / 2) x Kapazität\n"
    "   Beispiel: (4 / 2) x 1.000 GB = 2.000 GB nutzbar\n"
    "   Ausfalltoleranz: 1 Festplatte sicher (bis zu 2, wenn je\n"
    "   Spiegelpaar nur eine ausfällt)\n\n"
    "SPEICHEREFFIZIENZ\n"
    "   Effizienz = Nutzkapazität / Bruttokapazität x 100\n"
    "   Beispiel RAID 5: 3.000 GB / 4.000 GB x 100 = 75 %"
)
CALC_EXPLAIN_SCREEN = (
    "RECHENWEG BILDSCHIRM-DATENVOLUMEN\n"
    "Am Beispiel 1920 x 1080 Pixel, 24 Bit Farbtiefe\n\n"
    "SCHRITT 1: Pixel gesamt ermitteln\n"
    "   Pixel gesamt = Breite x Höhe\n"
    "   Beispiel: 1920 x 1080 = 2.073.600 Pixel\n\n"
    "SCHRITT 2: Datenmenge pro Bild in Bit berechnen\n"
    "   Jedes Pixel benötigt für seine Farbe eine feste Anzahl Bit,\n"
    "   die sogenannte Farbtiefe (z.B. 8 Bit = 256 Farben, 24 Bit =\n"
    "   True Color mit rund 16,8 Mio. Farben: je 8 Bit für Rot,\n"
    "   Grün und Blau).\n"
    "   Datenmenge (Bit) = Pixel gesamt x Farbtiefe\n"
    "   Beispiel: 2.073.600 x 24 Bit = 49.766.400 Bit\n\n"
    "SCHRITT 3: In Byte, KiB und MiB umrechnen\n"
    "   Da 1 Byte = 8 Bit sind, wird durch 8 geteilt; danach wird\n"
    "   jeweils durch 1024 geteilt, um die nächstgrößere Einheit\n"
    "   zu erhalten (Byte -> KiB -> MiB).\n"
    "   Byte = Bit / 8            -> 49.766.400 / 8 = 6.220.800 Byte\n"
    "   KiB  = Byte / 1024        -> 6.220.800 / 1024 = 6.075,00 KiB\n"
    "   MiB  = KiB / 1024         -> 6.075,00 / 1024 = 5,93 MiB\n"
    "   -> Ein einzelnes Bild in dieser Auflösung und Farbtiefe\n"
    "      benötigt also rund 5,93 MiB unkomprimierten Speicher.\n\n"
    "SCHRITT 4: Datenrate bei bewegten Bildern (Video)\n"
    "   Bei Videos wird nicht nur ein Bild, sondern mehrere Bilder\n"
    "   pro Sekunde angezeigt (Bildrate, engl. frames per\n"
    "   second, fps). Die Datenrate gibt an, wie viele Daten dafür\n"
    "   pro Sekunde anfallen.\n"
    "   Datenrate = Datenmenge pro Bild x Bildrate (fps)\n"
    "   Beispiel bei 30 fps: 6.220.800 Byte x 30 = 186.624.000 Byte/s\n"
    "   -> das sind rund 177,98 MiB/s (das sind 1.492,99 Mbit/s)\n"
    "      bzw. rund 10,43 GiB/Minute.\n"
    "   Dieser enorme Wert zeigt, warum Videos in der Praxis fast\n"
    "   immer komprimiert (z.B. per H.264/H.265) übertragen werden."
)

# Ab 0.62.3 (Teil E, F-E1): Handy-Fassungen der vier Rechenwege. Dieselben
# Schritte, Zahlen und Ergebnisse in derselben Reihenfolge wie am PC, aber
# hoechstens 28 Zeichen je Zeile (passt am Galaxy S24 auch bei "Sehr gross"),
# Bitreihen Oktett fuer Oktett. Am Handy sind die Zeilen also kuerzer als am
# PC (dort bis 67 Zeichen). test_rechenweg.py prueft Laenge, Zahlen,
# Reihenfolge und Schritte gegen die PC-Texte.
CALC_EXPLAIN_HANDY_WIDTH = 28
CALC_EXPLAIN_SUBNET_HANDY = (
    "RECHENWEG SUBNETTING\n"
    "Am Beispiel 192.168.1.50/24\n"
    "\n"
    "SCHRITT 1: Präfixlänge in\n"
    "Subnetzmaske umwandeln\n"
    " Die Präfixlänge (die Zahl\n"
    " nach dem /) gibt an, wie\n"
    " viele Bits von links auf 1\n"
    " gesetzt sind. /24 bedeutet:\n"
    " die ersten 24 Bit der\n"
    " 32-Bit-Subnetzmaske sind 1,\n"
    " der Rest ist 0.\n"
    " /24, Oktett für Oktett:\n"
    " 1. Oktett 11111111 = 255\n"
    " 2. Oktett 11111111 = 255\n"
    " 3. Oktett 11111111 = 255\n"
    " 4. Oktett 00000000 =   0\n"
    " -> Subnetzmaske:\n"
    "    255.255.255.0\n"
    "\n"
    "SCHRITT 2: Netzadresse\n"
    "berechnen\n"
    " Netzadresse = IP-Adresse\n"
    " UND Subnetzmaske\n"
    " (bitweise UND-Verknüpfung:\n"
    " nur wenn IP-Adresse und\n"
    " Maske an derselben Stelle\n"
    " eine 1 haben, bleibt dort\n"
    " eine 1 stehen)\n"
    " 192.168.1.50 UND\n"
    " 255.255.255.0, Oktett für\n"
    " Oktett:\n"
    " 1. Oktett\n"
    "       192 = 11000000\n"
    "   UND 255 = 11111111\n"
    "  Ergebnis = 11000000\n"
    " 2. Oktett\n"
    "       168 = 10101000\n"
    "   UND 255 = 11111111\n"
    "  Ergebnis = 10101000\n"
    " 3. Oktett\n"
    "         1 = 00000001\n"
    "   UND 255 = 11111111\n"
    "  Ergebnis = 00000001\n"
    " 4. Oktett\n"
    "        50 = 00110010\n"
    "   UND   0 = 00000000\n"
    "  Ergebnis = 00000000\n"
    " -> Netzadresse:\n"
    "    192.168.1.0\n"
    "\n"
    "SCHRITT 3: Broadcast-Adresse\n"
    "berechnen\n"
    " Wildcard-Maske =\n"
    " invertierte Subnetzmaske\n"
    " (alle Bits umgedreht):\n"
    " 255.255.255.0 -> 0.0.0.255\n"
    " Broadcast-Adresse =\n"
    " Netzadresse ODER\n"
    " Wildcard-Maske\n"
    " (bitweise ODER-Verknüpfung:\n"
    " alle Hostbits werden auf 1\n"
    " gesetzt)\n"
    " -> Broadcast-Adresse:\n"
    "    192.168.1.255\n"
    "\n"
    "SCHRITT 4: Nutzbare\n"
    "Host-Adressen zählen\n"
    " Anzahl aller Adressen im\n"
    " Netz = 2^(32 - Präfixlänge)\n"
    " Bei /24: 2^(32 - 24) = 2^8\n"
    " = 256 Adressen\n"
    " Davon sind die Netzadresse\n"
    " (192.168.1.0) und die\n"
    " Broadcast-Adresse\n"
    " (192.168.1.255) nicht als\n"
    " Host vergebbar, deshalb -2:\n"
    " Nutzbare Hosts =\n"
    " 2^(32 - Präfixlänge) - 2\n"
    " = 256 - 2 = 254\n"
    " -> erste Host-Adresse:\n"
    "    192.168.1.1\n"
    " -> letzte Host-Adresse:\n"
    "    192.168.1.254\n"
    "\n"
    "HINWEIS ZU IPv6\n"
    " IPv6 kennt keine\n"
    " Broadcast-Adresse, daher\n"
    " entfällt dort der Abzug von\n"
    " 2 Adressen. Gezählt werden\n"
    " alle 2^(128 - Präfixlänge)\n"
    " Adressen (einzelne Adressen\n"
    " sind reserviert, z.B.\n"
    " Subnet-Router-Anycast)."
)
CALC_EXPLAIN_RAID_HANDY = (
    "RECHENWEG RAID\n"
    "Am Beispiel 4 Festplatten\n"
    "x 1.000 GB\n"
    "(Bruttokapazität 4.000 GB)\n"
    "\n"
    "RAID 0 - Striping (ohne\n"
    "Redundanz, min. 2\n"
    "Festplatten)\n"
    " Die Daten werden ohne\n"
    " Redundanz auf alle\n"
    " Festplatten verteilt.\n"
    " Formel:\n"
    " Nutzkapazität =\n"
    " Anzahl x Kapazität\n"
    " Beispiel:\n"
    " 4 x 1.000 GB = 4.000 GB\n"
    " nutzbar\n"
    " Ausfalltoleranz:\n"
    " 0 Festplatten (fällt eine\n"
    " aus, sind alle Daten weg)\n"
    "\n"
    "RAID 1 - Spiegelung\n"
    "(Mirroring, min. 2\n"
    "Festplatten)\n"
    " Die Daten werden 1:1 auf\n"
    " alle weiteren Festplatten\n"
    " gespiegelt (bei 2\n"
    " Festplatten auf die\n"
    " zweite).\n"
    " Formel:\n"
    " Nutzkapazität =\n"
    " 1 x Kapazität\n"
    " Beispiel: 1.000 GB nutzbar\n"
    " (bei 4 Festplatten stehen\n"
    " nur 1.000 GB Nutzkapazität\n"
    " zur Verfügung, der Rest ist\n"
    " Spiegelung)\n"
    " Ausfalltoleranz:\n"
    " n-1 Festplatten\n"
    "\n"
    "RAID 5 - verteilte Parität\n"
    "(min. 3 Festplatten)\n"
    " Eine Festplatte Kapazität\n"
    " wird rechnerisch für\n"
    " Paritätsdaten verwendet\n"
    " (die Parität selbst liegt\n"
    " verteilt auf allen\n"
    " Festplatten).\n"
    " Formel:\n"
    " Nutzkapazität =\n"
    " (Anzahl - 1) x Kapazität\n"
    " Beispiel:\n"
    " (4 - 1) x 1.000 GB\n"
    " = 3.000 GB nutzbar\n"
    " Ausfalltoleranz:\n"
    " 1 Festplatte\n"
    "\n"
    "RAID 6 - doppelte Parität\n"
    "(min. 4 Festplatten)\n"
    " Wie RAID 5, aber mit\n"
    " doppelter Parität für mehr\n"
    " Sicherheit.\n"
    " Formel:\n"
    " Nutzkapazität =\n"
    " (Anzahl - 2) x Kapazität\n"
    " Beispiel:\n"
    " (4 - 2) x 1.000 GB\n"
    " = 2.000 GB nutzbar\n"
    " Ausfalltoleranz:\n"
    " 2 Festplatten\n"
    "\n"
    "RAID 10 - Spiegelung +\n"
    "Striping (min. 4\n"
    "Festplatten, gerade Anzahl)\n"
    " Je zwei Festplatten werden\n"
    " gespiegelt (RAID 1), diese\n"
    " Spiegelpaare werden\n"
    " anschließend im\n"
    " Striping-Verfahren (RAID 0)\n"
    " zusammengefasst.\n"
    " Formel:\n"
    " Nutzkapazität =\n"
    " (Anzahl / 2) x Kapazität\n"
    " Beispiel:\n"
    " (4 / 2) x 1.000 GB\n"
    " = 2.000 GB nutzbar\n"
    " Ausfalltoleranz:\n"
    " 1 Festplatte sicher (bis zu\n"
    " 2, wenn je Spiegelpaar nur\n"
    " eine ausfällt)\n"
    "\n"
    "SPEICHEREFFIZIENZ\n"
    " Effizienz =\n"
    " Nutzkapazität /\n"
    " Bruttokapazität x 100\n"
    " Beispiel RAID 5:\n"
    " 3.000 GB / 4.000 GB x 100\n"
    " = 75 %"
)
CALC_EXPLAIN_SCREEN_HANDY = (
    "RECHENWEG\n"
    "BILDSCHIRM-DATENVOLUMEN\n"
    "Am Beispiel 1920 x 1080\n"
    "Pixel, 24 Bit Farbtiefe\n"
    "\n"
    "SCHRITT 1: Pixel gesamt\n"
    "ermitteln\n"
    " Pixel gesamt =\n"
    " Breite x Höhe\n"
    " Beispiel: 1920 x 1080\n"
    " = 2.073.600 Pixel\n"
    "\n"
    "SCHRITT 2: Datenmenge pro\n"
    "Bild in Bit berechnen\n"
    " Jedes Pixel benötigt für\n"
    " seine Farbe eine feste\n"
    " Anzahl Bit, die sogenannte\n"
    " Farbtiefe (z.B. 8 Bit = 256\n"
    " Farben, 24 Bit = True Color\n"
    " mit rund 16,8 Mio. Farben:\n"
    " je 8 Bit für Rot, Grün und\n"
    " Blau).\n"
    " Datenmenge (Bit) =\n"
    " Pixel gesamt x Farbtiefe\n"
    " Beispiel:\n"
    " 2.073.600 x 24 Bit\n"
    " = 49.766.400 Bit\n"
    "\n"
    "SCHRITT 3: In Byte, KiB und\n"
    "MiB umrechnen\n"
    " Da 1 Byte = 8 Bit sind,\n"
    " wird durch 8 geteilt;\n"
    " danach wird jeweils durch\n"
    " 1024 geteilt, um die\n"
    " nächstgrößere Einheit zu\n"
    " erhalten\n"
    " (Byte -> KiB -> MiB).\n"
    " Byte = Bit / 8\n"
    " -> 49.766.400 / 8\n"
    " = 6.220.800 Byte\n"
    " KiB = Byte / 1024\n"
    " -> 6.220.800 / 1024\n"
    " = 6.075,00 KiB\n"
    " MiB = KiB / 1024\n"
    " -> 6.075,00 / 1024\n"
    " = 5,93 MiB\n"
    " -> Ein einzelnes Bild in\n"
    " dieser Auflösung und\n"
    " Farbtiefe benötigt also\n"
    " rund 5,93 MiB\n"
    " unkomprimierten Speicher.\n"
    "\n"
    "SCHRITT 4: Datenrate bei\n"
    "bewegten Bildern (Video)\n"
    " Bei Videos wird nicht nur\n"
    " ein Bild, sondern mehrere\n"
    " Bilder pro Sekunde\n"
    " angezeigt (Bildrate, engl.\n"
    " frames per second, fps).\n"
    " Die Datenrate gibt an, wie\n"
    " viele Daten dafür pro\n"
    " Sekunde anfallen.\n"
    " Datenrate =\n"
    " Datenmenge pro Bild\n"
    " x Bildrate (fps)\n"
    " Beispiel bei 30 fps:\n"
    " 6.220.800 Byte x 30\n"
    " = 186.624.000 Byte/s\n"
    " -> das sind rund\n"
    " 177,98 MiB/s (das sind\n"
    " 1.492,99 Mbit/s) bzw. rund\n"
    " 10,43 GiB/Minute.\n"
    " Dieser enorme Wert zeigt,\n"
    " warum Videos in der Praxis\n"
    " fast immer komprimiert\n"
    " (z.B. per H.264/H.265)\n"
    " übertragen werden."
)
CALC_EXPLAIN_UPS_HANDY = (
    "RECHENWEG USV-KAPAZITÄT\n"
    "Am Beispiel 600 W Last,\n"
    "Wirkungsgrad 80 %,\n"
    "15 Minuten, Akku 2 x 12 V in\n"
    "Reihe (24 V),\n"
    "Alterungszuschlag 25 %\n"
    "\n"
    "SCHRITT 1: VA und W\n"
    " Wirkleistung P (W) =\n"
    " Scheinleistung S (VA)\n"
    " x Leistungsfaktor\n"
    " 600 W / 0,9 = 667 VA\n"
    " (Leistungsfaktor 0,9 ist\n"
    " eine Annahme, der echte\n"
    " Wert steht auf dem\n"
    " Typenschild).\n"
    "\n"
    "SCHRITT 2: Energie für die\n"
    "Last\n"
    " Energie (Wh) =\n"
    " Last (W) x Zeit (h)\n"
    " = 600 W x 0,25 h = 150 Wh\n"
    "\n"
    "SCHRITT 3: Verluste der USV\n"
    " Der Akku muss mehr liefern,\n"
    " weil die USV Verluste hat:\n"
    " 150 Wh / 0,8 = 187,5 Wh\n"
    "\n"
    "SCHRITT 4: Alterungszuschlag\n"
    " Ein Bleiakku gilt mit 80 %\n"
    " Restkapazität als\n"
    " verbraucht. Damit er auch\n"
    " dann reicht, plant man 25 %\n"
    " mehr ein (Faktor 1,25):\n"
    " 187,5 Wh x 1,25\n"
    " = 234,38 Wh\n"
    "\n"
    "SCHRITT 5: Kapazität in Ah\n"
    " Ah = Wh / Strangspannung\n"
    " = 234,38 Wh / 24 V\n"
    " = 9,77 Ah\n"
    "\n"
    "LAUFZEIT (umgekehrt)\n"
    " Akku-Energie =\n"
    " 24 V x 12 Ah = 288 Wh\n"
    " Laufzeit =\n"
    " 288 Wh x 0,8 / 600 W x 60\n"
    " = 23,04 min (neu)\n"
    " am Lebensende:\n"
    " 23,04 min x 0,8\n"
    " = 18,43 min\n"
    "\n"
    "EMPFEHLUNG\n"
    " Die Last soll höchstens\n"
    " 80 % der USV-Nennleistung\n"
    " betragen (in VA und in W).\n"
    " Beispiel USV 1.500 VA /\n"
    " 900 W:\n"
    " 667 / 1.500 = 44 %,\n"
    " 600 / 900 = 67 %\n"
    " -> passend,\n"
    " 18,43 min am Lebensende\n"
    " >= 15 min -> passend.\n"
    "\n"
    "QUELLEN\n"
    " Leistungsfaktor = P / S:\n"
    " Wikipedia, Leistungsfaktor\n"
    " Ah-Formel und\n"
    " Wirkungsgrad 0,80: EnerSys,\n"
    " Runtime and right-sizing a\n"
    " UPS\n"
    " Faktor 1,25 und 80 %:\n"
    " IEEE 485 (Vertiv/Battcon\n"
    " 2000)\n"
    " 80 % Auslastung: Schneider\n"
    " Electric, FAQ000268376"
)



# ----------------------------------------------------------------------------
#  Ab 0.63 (Plan 0.63, T2): Rechenwege "Netz aufteilen" und "Nach Hostbedarf"
# ----------------------------------------------------------------------------
# Aus der Eingabe erzeugt, Schritt fuer Schritt wie in der Pruefung (Plan 0.63
# Anhang A). Je Text eine PC-Fassung (hoechstens CALC_EXPLAIN_PC_WIDTH
# Zeichen je Zeile) und eine Handy-Fassung (schmal=True, hoechstens
# CALC_EXPLAIN_HANDY_WIDTH Zeichen). Gegenueber Anhang A kommen nur diese
# Zeilen dazu (Plan 0.63 Abschnitt 2.2 Punkt 3 und 9, E-63-4): Nibble-Zeile
# (IPv6, Praefix nicht durch 4 teilbar), Subnet-Router-Anycast (IPv6) und der
# Satz zu aelteren Buechern (IPv4). Mehr als SUBNET_EXPLAIN_ALL Subnetze
# listet der Rechenweg nur am Anfang und am Ende (alle stehen im Ergebnis).
SUBNET_EXPLAIN_ALL = 16
SUBNET_EXPLAIN_NIBBLE = ("An der nächsten 4-Bit-Grenze (Nibble): /%d = %s Subnetze. "
                         "In der Praxis üblich, weil dann jede Hex-Ziffer ein Teil "
                         "der Subnetz-Nummer ist. Gerechnet wird hier weiter mit /%d.")
SUBNET_EXPLAIN_ANYCAST = ("Einzelne Adressen sind reserviert, z. B. die "
                          "Subnet-Router-Anycast-Adresse (alle Bits der "
                          "Schnittstellenkennung 0, RFC 4291 2.6.1).")
SUBNET_EXPLAIN_BOOKS = ("Ältere Bücher ziehen 2 Subnetze ab. "
                        "Das ist veraltet (RFC 1878).")
# Fassung 4 (Lehrbuch-Gegenpruefung Z-10): /64-Hinweis (Fund 7), Lage der
# Subnetz-Bits und Uebertrag, wenn sie ueber eine Oktett- bzw. Hextett-Grenze
# reichen (Fund 2; Wortlaut belege/b21, Beispiele I und J)
SUBNET_EXPLAIN_HINT_64 = ("Hinweis: /%d ist länger als /64. Ein LAN bekommt in der "
                          "Regel ein /64, sonst geht die automatische Adressvergabe "
                          "(SLAAC) nicht.")
SUBNET_EXPLAIN_BITS = "Die %d Subnetz-Bits (Bit %d bis %d): %s."
SUBNET_EXPLAIN_CARRY = ("Übertrag: Wird das %d. %s %s, steht dort 0 und das %d. %s "
                        "zählt um 1 weiter.")
SUBNET_EXPLAIN_CARRY_EXAMPLE = "Beispiel: Nr. %s %s + %s = Nr. %s %s"


def _explain_list_indexes(total):
    """Welche Subnetze der Rechenweg zeigt: alle oder 4 vorne, 2 hinten."""
    if total <= SUBNET_EXPLAIN_ALL:
        return list(range(total)), None
    return [0, 1, 2, 3, None, total - 2, total - 1], (5, total - 2)


def _explain_k(result, pad, schmal):
    wanted, bits = result["gewuenscht"], result["k"]
    lines = []
    for power in range(max(0, bits - 1), bits + 1):
        value = de_int(1 << power)
        if power == bits:
            line = "%s2^%d = %s >= %s -> k = %d" % (pad, power, value, de_int(wanted), bits)
            rest = "%s>= %s -> k = %d" % (pad + " ", de_int(wanted), bits)
        else:
            line = "%s2^%d = %s < %s (zu wenig)" % (pad, power, value, de_int(wanted))
            rest = "%s< %s (zu wenig)" % (pad + " ", de_int(wanted))
        if schmal and len(line) > CALC_EXPLAIN_HANDY_WIDTH:
            lines += ["%s2^%d = %s" % (pad, power, value), rest]
        else:
            lines.append(line)
    if bits == 0:
        lines += _wrap_para(SUBNET_NO_SPLIT, pad, CALC_EXPLAIN_HANDY_WIDTH if schmal
                            else CALC_EXPLAIN_PC_WIDTH)
    return lines


def _explain_reserve(result, schmal):
    wanted, total, bits = result["gewuenscht"], result["anzahl"], result["k"]
    if total == wanted:
        return []
    if schmal:
        return [" %s ist keine Zweierpotenz:" % de_int(wanted),
                " Es entstehen 2^%d = %s" % (bits, de_int(total)),
                " Subnetze. Die ersten %s" % de_int(wanted),
                " werden verwendet, der Rest", " bleibt frei (Reserve)."]
    free = total - wanted
    if free == 1:
        rest, verb = "Nr. %s" % de_int(total), "bleibt"
    else:
        rest = "Nr. %s %s %s" % (de_int(wanted + 1), "und" if free == 2 else "bis",
                                 de_int(total))
        verb = "bleiben"
    lines = ["   %s ist keine Zweierpotenz: Es entstehen 2^%d = %s Subnetze."
             % (de_int(wanted), bits, de_int(total))]
    used = "Die ersten %s werden verwendet (Nr. 1 bis %s), %s" % (
        de_int(wanted), de_int(wanted), rest)
    if len("   " + used) <= CALC_EXPLAIN_PC_WIDTH:
        return lines + ["   " + used, "   %s frei (Reserve)." % verb]
    return lines + _wrap_para("%s %s frei (Reserve)." % (used, verb), "   ",
                              CALC_EXPLAIN_PC_WIDTH)


def _explain_head(result, title, schmal):
    version = result["version"]
    base = subnet_net_text(version, result["netz"], result["praefix"])
    width = CALC_EXPLAIN_HANDY_WIDTH if schmal else CALC_EXPLAIN_PC_WIDTH
    if schmal:
        lines = [title, "(IPv%d)" % version, "Ausgangsnetz"] + _handy_address(" ", base)
        if result["gewuenscht"] == 1:
            lines.append("gesucht: 1 Subnetz")
        else:
            lines += ["gesucht: %s gleich große" % de_int(result["gewuenscht"]), "Subnetze"]
    else:
        lines = ["%s (IPv%d)" % (title, version),
                 "Ausgangsnetz %s, gesucht: %s"
                 % (base, "1 Subnetz" if result["gewuenscht"] == 1 else
                    "%s gleich große Subnetze" % de_int(result["gewuenscht"]))]
    if result["hinweis"]:
        lines += _wrap_para(result["hinweis"], "", width)
    lines.append("")
    if schmal:
        lines += ["SCHRITT 1: Bits für die", "Subnetze", " Gesucht: kleinstes k mit",
                  " 2^k >= %s" % de_int(result["gewuenscht"])]
        lines += _explain_k(result, " ", True)
        lines += ["", "SCHRITT 2: Neue Präfixlänge", " alte Präfixlänge + k",
                  " = %d + %d = %d -> /%d" % (result["praefix"], result["k"],
                                              result["neu"], result["neu"])]
    else:
        lines += ["SCHRITT 1: Benötigte Bits für die Subnetze",
                  "   Gesucht ist das kleinste k mit 2^k >= %s." % de_int(result["gewuenscht"])]
        lines += _explain_k(result, "   ", False)
        lines += ["", "SCHRITT 2: Neue Präfixlänge",
                  "   neue Präfixlänge = alte Präfixlänge + k = %d + %d = %d -> /%d"
                  % (result["praefix"], result["k"], result["neu"], result["neu"])]
    if result["nibble"]:
        lines += _wrap_para(SUBNET_EXPLAIN_NIBBLE % (result["nibble"],
                                                     de_int(result["nibble_anzahl"]),
                                                     result["neu"]),
                            " " if schmal else "   ", width)
    if version == 6 and result["neu"] > 64:
        lines += _wrap_para(SUBNET_EXPLAIN_HINT_64 % result["neu"],
                            " " if schmal else "   ", width)
    lines.append("")
    return lines


def _explain_carry(result, unit, name, step_text, schmal):
    """Lage der Subnetz-Bits (Schritt 3) und Uebertrag mit Beispiel aus der
    Liste (Schritt 4), nur wenn die Subnetz-Bits ueber eine Oktett- (unit 8)
    bzw. Hextett-Grenze (unit 16) reichen; sonst zwei leere Listen."""
    prefix, new = result["praefix"], result["neu"]
    parts = []                                   # (Anzahl Bits, Nr. der Einheit)
    for index in range(prefix // unit, (new - 1) // unit + 1):
        low, high = max(prefix + 1, index * unit + 1), min(new, (index + 1) * unit)
        if high >= low:
            parts.append((high - low + 1, index + 1))
    if len(parts) < 2:
        return [], []
    width = CALC_EXPLAIN_HANDY_WIDTH if schmal else CALC_EXPLAIN_PC_WIDTH
    pad = " " if schmal else "   "
    items = ["%d im %d." % part for part in parts]
    where = "%s und %s %s" % (", ".join(items[:-1]), items[-1], name)
    lage = _wrap_para(SUBNET_EXPLAIN_BITS % (new - prefix, prefix + 1, new, where), pad, width)
    border = parts[-1][1]
    carry = _wrap_para(SUBNET_EXPLAIN_CARRY % (border, name, "256" if unit == 8 else
                                               "hex 10000", border - 1, name), pad, width)
    number = 1 << parts[-1][0]                   # Nr. number + 1 hat den ersten Uebertrag
    before = subnet_addr_text(result["version"], split_entry(result, number - 1)["netz"])
    after = subnet_addr_text(result["version"], split_entry(result, number)["netz"])
    if schmal:
        carry += [" Beispiel:"] + _handy_address(" Nr. %s: " % de_int(number), before) \
            + [" + %s" % step_text] + _handy_address(" = Nr. %s: " % de_int(number + 1), after)
    else:
        carry += _wrap_para(SUBNET_EXPLAIN_CARRY_EXAMPLE % (
            de_int(number), before, step_text, de_int(number + 1), after), pad, width)
    return lage, carry


def _split_explain_v4(result, schmal):
    new, size = result["neu"], result["groesse"]
    hostbits = 32 - new
    mask = result["maske"]
    octet = max(0, (new - 1) // 8)               # Oktett der Grenze (0 bis 3)
    mask_octet = (mask >> (8 * (3 - octet))) & 255
    step = 256 - mask_octet
    if new == 31:
        hosts = [SUBNET_HINT_31]
    elif new == 32:
        hosts = [SUBNET_HINT_32]
    elif schmal:
        hosts = [" Nutzbare Hosts je Subnetz",
                 " = 2^%d - 2 = %s" % (hostbits, de_int(size - 2))]
    else:
        hosts = ["   Nutzbare Hosts je Subnetz = 2^%d - 2 = %s" % (hostbits, de_int(size - 2))]
    lines = _explain_head(result, "RECHENWEG NETZ AUFTEILEN", schmal)
    lage, carry = _explain_carry(result, 8, "Oktett", "%d" % step, schmal)
    if schmal:
        if new >= 31:
            hosts = _wrap_para(hosts[0], " ", CALC_EXPLAIN_HANDY_WIDTH)
        lines += ["SCHRITT 3: Maske, Hostbits,", "Schrittweite",
                  " /%d, Oktett für Oktett:" % new]
        for number in range(4):
            value = (mask >> (8 * (3 - number))) & 255
            lines.append(" %d. Oktett %s = %3d" % (number + 1, format(value, "08b"), value))
        lines += [" -> Subnetzmaske:", "    %s" % ipv4_text(mask),
                  " Hostbits = 32 - %d = %d" % (new, hostbits),
                  " Adressen je Subnetz", " = 2^%d = %s" % (hostbits, de_int(size)),
                  " Schrittweite im %d. Oktett" % (octet + 1),
                  " = 256 - %d = %d" % (mask_octet, step)] + lage + hosts
        lines += ["", "SCHRITT 4: Subnetze", "auflisten",
                  " Netzadresse + Schrittweite", " ergibt das nächste Subnetz."] + carry
    else:
        if new >= 31:
            hosts = ["   " + hosts[0]]
        bits = ".".join(format((mask >> shift) & 255, "08b") for shift in (24, 16, 8, 0))
        lines += ["SCHRITT 3: Subnetzmaske, Hostbits und Schrittweite",
                  "   /%d = %s" % (new, bits),
                  "   -> Subnetzmaske: %s" % ipv4_text(mask),
                  "   Hostbits = 32 - %d = %d" % (new, hostbits),
                  "   Adressen je Subnetz = 2^%d = %s" % (hostbits, de_int(size)),
                  "   Schrittweite im %d. Oktett = 256 - %d = %d"
                  % (octet + 1, mask_octet, step)] + lage + hosts
        lines += ["", "SCHRITT 4: Subnetze auflisten",
                  "   (Netzadresse + Schrittweite = nächstes Subnetz)"] + carry
    indexes, gap = _explain_list_indexes(result["anzahl"])
    entries = [split_entry(result, i) if i is not None else None for i in indexes]
    rows = []
    for entry in entries:
        if entry is None:
            if schmal:
                lines += _wrap_para("Subnetz %s bis %s: je + Schrittweite (alle im "
                                    "Ergebnis)" % (de_int(gap[0]), de_int(gap[1])),
                                    "", CALC_EXPLAIN_HANDY_WIDTH)
            else:
                rows.append(None)
            continue
        broadcast = ipv4_text(entry["broadcast"]) if entry["broadcast"] is not None \
            else "keine"
        net = subnet_net_text(4, entry["netz"], new)
        if schmal:
            lines += ["Subnetz %s: %s" % (de_int(entry["nr"]), entry["status"]),
                      " Netz: %s" % net, " Erste: %s" % ipv4_text(entry["erste"]),
                      " Letzte: %s" % ipv4_text(entry["letzte"]),
                      " Broadcast: %s" % broadcast]
        else:
            rows.append([de_int(entry["nr"]), net, ipv4_text(entry["erste"]),
                         ipv4_text(entry["letzte"]), broadcast])
    if not schmal:
        filled = [row for row in rows if row]
        width = max(2, max(len(row[0]) for row in filled))
        table = _pc_table(["Nr", "Netzadresse", "Erster Host", "Letzter Host", "Broadcast"],
                          filled, [width, 18, 15, 15])
        if gap:
            table.insert(5, "  %s Nr. %s bis %s: je + Schrittweite (alle im Ergebnis)"
                         % ("..".ljust(width), de_int(gap[0]), de_int(gap[1])))
        lines += table
    total, prefix = result["anzahl"], result["praefix"]
    lines += ["", "SCHRITT 5: Kontrolle"]
    if schmal:
        lines += [" %s x %s" % (de_int(total), de_int(size)),
                  " = %s Adressen" % de_int(total * size),
                  " = Größe von /%d" % prefix,
                  " (2^%d = %s)" % (32 - prefix, de_int(1 << (32 - prefix)))]
    else:
        lines.append("   %s x %s = %s Adressen = Größe von /%d (2^%d = %s)"
                     % (de_int(total), de_int(size), de_int(total * size), prefix,
                        32 - prefix, de_int(1 << (32 - prefix))))
    lines += _explain_reserve(result, schmal)
    if not schmal and total == result["gewuenscht"]:
        lines.append("   Das eine Subnetz wird verwendet." if total == 1 else
                     "   Alle %s Subnetze werden verwendet." % de_int(total))
    if result["k"]:
        lines += _wrap_para(SUBNET_EXPLAIN_BOOKS, " " if schmal else "   ",
                            CALC_EXPLAIN_HANDY_WIDTH if schmal else CALC_EXPLAIN_PC_WIDTH)
    return lines


def _split_explain_v6(result, schmal):
    new, size, prefix = result["neu"], result["groesse"], result["praefix"]
    hextet = max(0, (new - 1) // 16)             # Hextett der Grenze (0 bis 7)
    low, high = 16 * hextet + 1, 16 * (hextet + 1)
    step = 1 << (high - new)
    in_hextet = new - 16 * hextet
    unit = "Bit" if in_hextet == 1 else "Bits"
    lines = _explain_head(result, "RECHENWEG NETZ AUFTEILEN", schmal)
    lage, carry = _explain_carry(result, 16, "Hextett", "hex %x" % step, schmal)
    anycast = new < 127
    if schmal:
        lines += ["SCHRITT 3: Wo liegt die", "Grenze?",
                  " /%d endet im %d. Hextett" % (new, hextet + 1),
                  " (Bits %d bis %d)." % (low, high),
                  " Davon Netzanteil:", " %d - %d = %d %s" % (new, 16 * hextet, in_hextet, unit)]
        lines += lage + [
                  " Schrittweite im %d. Hextett" % (hextet + 1),
                  " = 2^(%d - %d) = 2^%d" % (high, new, high - new),
                  " = %s = hex %x" % (de_int(step), step),
                  " Adressen je Subnetz:", " 2^(128 - %d) = 2^%d" % (new, 128 - new),
                  " = %s" % de_int(size),
                  " Kein Abzug von 2: IPv6", " hat keine Broadcast-", " Adresse."]
        if anycast:
            lines += _wrap_para(SUBNET_EXPLAIN_ANYCAST, " ", CALC_EXPLAIN_HANDY_WIDTH)
        lines += ["", "SCHRITT 4: Subnetze", "auflisten",
                  " %d. Hextett um die" % (hextet + 1), " Schrittweite erhöhen:"] + carry
    else:
        lines += ["SCHRITT 3: Wo liegt die Grenze? Schrittweite und Größe",
                  "   /%d endet im %d. Hextett (Bits %d bis %d). Davon gehören"
                  % (new, hextet + 1, low, high),
                  "   %d - %d = %d %s zum Netzanteil." % (new, 16 * hextet, in_hextet, unit)]
        lines += lage + [
                  "   Schrittweite im %d. Hextett = 2^(%d - %d) = 2^%d = %s = hex %x"
                  % (hextet + 1, high, new, high - new, de_int(step), step),
                  "   Adressen je Subnetz = 2^(128 - %d) = 2^%d" % (new, 128 - new),
                  "      = %s" % de_int(size),
                  "   Kein Abzug von 2: IPv6 hat keine Broadcast-Adresse."]
        if anycast:
            lines += _wrap_para(SUBNET_EXPLAIN_ANYCAST, "   ", CALC_EXPLAIN_PC_WIDTH)
        lines += ["", "SCHRITT 4: Subnetze auflisten (%d. Hextett um die Schrittweite "
                  "erhöhen)" % (hextet + 1)] + carry
    bits = result["k"]
    # Subnetz-Bits nur bis 16 Stellen; "im n. Hextett" nur, wenn alle dort liegen
    show_bits = bits <= 16
    inside = bits >= 1 and prefix >= 16 * hextet
    indexes, gap = _explain_list_indexes(result["anzahl"])
    entries = [split_entry(result, i) if i is not None else None for i in indexes]
    numbers = [de_int(e["nr"]) for e in entries if e]
    width = max(2, max(len(number) for number in numbers))
    bit_width = max(4, bits)
    if not schmal:
        head = "  %s " % "Nr".ljust(width)
        if show_bits:
            head += "Bits".ljust(bit_width) + " "
        lines.append(head + ("%d. Hextett binär" % (hextet + 1)).ljust(24) + "hex   Subnetz")
    for entry in entries:
        if entry is None:
            if schmal:
                lines += _wrap_para("Subnetz %s bis %s: je + Schrittweite (alle im "
                                    "Ergebnis)" % (de_int(gap[0]), de_int(gap[1])),
                                    "", CALC_EXPLAIN_HANDY_WIDTH)
            else:
                lines.append("  %s Nr. %s bis %s: je + Schrittweite (alle im Ergebnis)"
                             % ("..".ljust(width), de_int(gap[0]), de_int(gap[1])))
            continue
        group = ipv6_groups(entry["netz"])[hextet]
        binary = format(group, "016b")
        binary = " ".join(binary[i:i + 4] for i in range(0, 16, 4))
        sub_bits = format(entry["nr"] - 1, "0%db" % bits) if bits else "-"
        net = subnet_net_text(6, entry["netz"], new)
        if schmal:
            lines.append("Subnetz %s: %s" % (de_int(entry["nr"]), entry["status"]))
            caption = " Bits %s im %d. Hextett:" % (sub_bits, hextet + 1)
            if inside and len(caption) <= CALC_EXPLAIN_HANDY_WIDTH:
                lines.append(caption)
            else:
                if show_bits and bits:
                    lines += _handy_fit([" Subnetz-Bits: %s" % sub_bits])
                lines.append(" %d. Hextett:" % (hextet + 1))
            lines.append("  %s = %04x" % (binary, group))
            lines += _handy_address(" Netz: ", net)
            lines += _handy_address(" bis: ", ipv6_text(entry["ende"]))
        else:
            row = "  %s " % de_int(entry["nr"]).ljust(width)
            if show_bits:
                row += sub_bits.ljust(bit_width) + " "
            lines.append(row + "%s = %04x  %s" % (binary, group, net))
    if not schmal:
        first = split_entry(result, 0)
        lines += ["", "   Bereich je Subnetz: von der Netzadresse bis zur letzten Adresse,",
                  "   z. B. Subnetz 1: %s bis" % ipv6_text(first["netz"]),
                  "                    %s" % ipv6_text(first["ende"])]
    lines += ["", "SCHRITT 5: Kontrolle"]
    total = result["anzahl"]
    if schmal:
        lines += [" %s x 2^%d = 2^%d" % (de_int(total), 128 - new, 128 - prefix),
                  " = Größe von /%d" % prefix]
    else:
        lines.append("   %s x 2^%d = 2^%d Adressen = Größe von /%d"
                     % (de_int(total), 128 - new, 128 - prefix, prefix))
    lines += _explain_reserve(result, schmal)
    return lines


def split_explain(result, schmal=False):
    """Rechenweg "Netz aufteilen" zum Ergebnis von split_network. schmal =
    Handy-Fassung (hoechstens CALC_EXPLAIN_HANDY_WIDTH Zeichen je Zeile)."""
    lines = _split_explain_v4(result, schmal) if result["version"] == 4 \
        else _split_explain_v6(result, schmal)
    return "\n".join(_fit_lines(lines, CALC_EXPLAIN_HANDY_WIDTH if schmal
                                else CALC_EXPLAIN_PC_WIDTH))


def hosts_explain(result, schmal=False):
    """Rechenweg "Nach Hostbedarf" (VLSM, IPv4) zum Ergebnis von
    subnet_by_hosts. schmal = Handy-Fassung."""
    width = CALC_EXPLAIN_HANDY_WIDTH if schmal else CALC_EXPLAIN_PC_WIDTH
    pad = " " if schmal else "   "
    base = subnet_net_text(4, result["netz"], result["praefix"])
    subnets, order = result["subnetze"], result["reihenfolge"]
    capacity, total = result["kapazitaet"], result["summe"]
    host_bits = 32 - result["praefix"]
    if schmal:
        lines = ["RECHENWEG NACH HOSTBEDARF", "(VLSM, IPv4)", "Ausgangsnetz", " " + base,
                 "Bedarf:"]
        lines += [" %s: %s" % (item["name"], subnet_hosts_text(item["bedarf"]))
                  for item in subnets]
    else:
        lines = ["RECHENWEG NACH HOSTBEDARF (VLSM, IPv4)", "Ausgangsnetz %s" % base]
        lines += _join_items("Bedarf: ", ["%s: %s" % (item["name"],
                                                      subnet_hosts_text(item["bedarf"]))
                                          for item in subnets], ", ", "        ", width)
    if result["hinweis"]:
        lines += _wrap_para(result["hinweis"], "", width)
    lines.append("")
    sorted_items = ["%s: %s" % (subnets[i]["name"], de_int(subnets[i]["bedarf"]))
                    for i in order]
    if schmal:
        lines += ["SCHRITT 1: Sortieren,", "größter Bedarf zuerst"]
        lines += _join_items(" ", sorted_items, ", ", " ", width)
        lines += [" So liegt jedes Subnetz an", " seiner Größe ausgerichtet,",
                  " es entstehen keine Lücken.", "",
                  "SCHRITT 2: Größe je Subnetz", " kleinstes h mit", " 2^h - 2 >= Bedarf"]
    else:
        lines.append("SCHRITT 1: Nach Hostbedarf sortieren, größter Bedarf zuerst")
        lines += _join_items("   ", sorted_items, ", ", "   ", width)
        lines += ["   Begründung: So beginnt jedes Subnetz an einer Grenze, die zu",
                  "   seiner Größe passt, und es entstehen keine Lücken.", "",
                  "SCHRITT 2: Größe je Subnetz (kleinstes h mit 2^h - 2 >= Bedarf)"]
    for index in order:
        item = subnets[index]
        bits, need = item["h"], de_int(item["bedarf"])
        need_text = subnet_hosts_text(item["bedarf"])
        below = "2^%d - 2 = %s < %s" % (bits - 1, de_int((1 << (bits - 1)) - 2), need) \
            if bits > 2 else ""
        enough = "2^%d - 2 = %s >= %s" % (bits, de_int((1 << bits) - 2), need)
        if schmal:
            lines.append(" %s: %s" % (item["name"], need_text))
            if below:
                lines.append("  " + below)
            lines += ["  " + enough, "  h = %d -> /%d (32 - %d)" % (bits, 32 - bits, bits),
                      "  Größe %s Adressen" % de_int(item["groesse"])]
        else:
            line = "   %s (%s): %s%s" % (item["name"], need_text,
                                          below + ", " if below else "", enough)
            if len(line) > width and below:
                lines += ["   %s (%s): %s," % (item["name"], need_text, below),
                          "      " + enough]
            else:
                lines.append(line)
            lines += ["      -> h = %d, /%d (32 - %d), Maske %s, Größe %s"
                      % (bits, 32 - bits, bits, ipv4_text(item["maske"]),
                         de_int(item["groesse"]))]
    sizes = [de_int(subnets[i]["groesse"]) for i in order]
    verdict = "passt" if result["passt"] else "passt nicht"
    lines += ["", "SCHRITT 3: Passt es?"]
    if schmal:
        if len(sizes) > 1:
            lines += _join_items(" Summe: ", sizes, " + ", "  ", width)
        else:
            lines.append(" Größe:")             # Fassung 4 (Z-10 Fund 10)
        lines += [" = %s Adressen" % de_int(total),
                  " Ausgangsnetz /%d: 2^%d" % (result["praefix"], host_bits),
                  " = %s Adressen" % de_int(capacity),
                  " %s %s %s -> %s" % (de_int(total), "<=" if result["passt"] else ">",
                                       de_int(capacity), verdict)]
    else:
        if len(sizes) > 1:
            summe = _join_items("   Summe der Größen: ", sizes, " + ", "      ", width)
            summe[-1] += " = %s Adressen" % de_int(total)
            lines += summe
        else:                                    # Fassung 4 (Z-10 Fund 10)
            lines.append("   Größe: %s Adressen" % de_int(total))
        lines.append("   Ausgangsnetz /%d: 2^%d = %s Adressen -> %s"
                     % (result["praefix"], host_bits, de_int(capacity), verdict))
    if not result["passt"]:
        power = (total - 1).bit_length()
        lines += _wrap_para(result["meldung"], pad, width)
        lines += _wrap_para("Nötige Größe: die nächste Zweierpotenz ab %s ist 2^%d = %s "
                            "Adressen, also /%s (32 - %d)."
                            % (de_int(total), power, de_int(1 << power),
                               32 - power, power) if power <= 32 else
                            "Nötige Größe: mehr als 2^32 Adressen.", pad, width)
        return "\n".join(_fit_lines(lines, width))
    lines.append("")
    if schmal:
        lines += ["SCHRITT 4: Vergabe", "nacheinander", " Jedes Subnetz beginnt",
                  " direkt hinter dem vorigen."]
    else:
        lines.append("SCHRITT 4: Vergabe nacheinander ab der ersten Adresse")
        rows = []
    for number, index in enumerate(order, 1):
        item = subnets[index]
        net = "%s/%d" % (ipv4_text(item["netz"]), item["praefix"])
        if schmal:
            lines += ["%d. %s (%s)" % (number, item["name"], subnet_hosts_text(item["bedarf"])),
                      " Netz: %s" % net, " Maske: %s" % ipv4_text(item["maske"]),
                      " Erste: %s" % ipv4_text(item["erste"]),
                      " Letzte: %s" % ipv4_text(item["letzte"]),
                      " Broadcast: %s" % ipv4_text(item["broadcast"])]
        else:
            rows.append([str(number), item["name"], net, ipv4_text(item["erste"]),
                         ipv4_text(item["letzte"]), ipv4_text(item["broadcast"])])
    if not schmal:
        name_width = max(4, max(len(item["name"]) for item in subnets))
        lines += _pc_table(["Nr", "Name", "Netzadresse", "Erster Host", "Letzter Host",
                            "Broadcast"], rows, [2, name_width, 18, 15, 15])
    lines.append("")
    blocks = ["%s/%d" % (ipv4_text(start), prefix) for start, prefix in result["bloecke"]]
    if not result["rest"]:
        lines += ["SCHRITT 5: Rest" if schmal else "SCHRITT 5: Freier Rest"]
        lines += _wrap_para("Kein Rest: Das Ausgangsnetz ist genau voll.", pad, width)
    elif schmal:
        lines += ["SCHRITT 5: Rest", " frei: %s" % ipv4_text(result["rest_von"]),
                  " bis %s" % ipv4_text(result["rest_bis"]),
                  " = %s Adressen" % de_int(result["rest"]), "", " als Blöcke:"]
        lines += ["  " + block for block in blocks]
    else:
        lines += ["SCHRITT 5: Freier Rest",
                  "   %s bis %s = %s Adressen" % (ipv4_text(result["rest_von"]),
                                                 ipv4_text(result["rest_bis"]),
                                                 de_int(result["rest"])), ""]
        lines += _join_items("   als ausgerichtete Blöcke: ", blocks, ", ", "   ", width)
    lines.append("")
    if schmal:
        lines.append("Reihenfolge der Eingabe:")
        lines += [" %s: %s/%d" % (item["name"], ipv4_text(item["netz"]), item["praefix"])
                  for item in subnets]
    else:
        lines.append("Ergebnis in der Reihenfolge der Eingabe:")
        lines += ["   %s: %s/%d" % (item["name"], ipv4_text(item["netz"]), item["praefix"])
                  for item in subnets]
    return "\n".join(_fit_lines(lines, width))


# Rechenweg "Netzdaten" fuer IPv6 (fester Text, Plan 0.63 Abschnitt 4.1:
# Praefix, Anzahl 2^(128 - p), kein Broadcast, /64 je LAN, Kurzschreibweise
# in 5 Regeln). Der IPv4-Text bleibt CALC_EXPLAIN_SUBNET (unveraendert).
CALC_EXPLAIN_SUBNET_V6 = (
    "RECHENWEG NETZDATEN (IPv6)\n"
    "Am Beispiel 2001:db8:abcd:12::1/64\n\n"
    "SCHRITT 1: Präfixlänge lesen\n"
    "   Eine IPv6-Adresse hat 128 Bit in 8 Hextetten zu je 16 Bit.\n"
    "   Die Präfixlänge (die Zahl nach dem /) sagt, wie viele Bits\n"
    "   von links zum Netz gehören: /64 = die ersten 4 Hextette.\n\n"
    "SCHRITT 2: Netzadresse bestimmen\n"
    "   Alle Bits nach dem Präfix auf 0 setzen:\n"
    "   2001:db8:abcd:12::1 -> 2001:db8:abcd:12::\n"
    "   -> Netzadresse: 2001:db8:abcd:12::/64\n\n"
    "SCHRITT 3: Adressen zählen\n"
    "   Anzahl Adressen = 2^(128 - Präfixlänge)\n"
    "   Bei /64: 2^(128 - 64) = 2^64 = 18.446.744.073.709.551.616\n"
    "   Kein Abzug von 2: IPv6 hat keine Broadcast-Adresse.\n"
    "   -> erste Adresse: 2001:db8:abcd:12::\n"
    "   -> letzte Adresse: 2001:db8:abcd:12:ffff:ffff:ffff:ffff\n"
    "   Einzelne Adressen sind reserviert, z. B. die Subnet-Router-\n"
    "   Anycast-Adresse (alle Bits der Schnittstellenkennung 0,\n"
    "   RFC 4291 2.6.1).\n\n"
    "HINWEIS: /64 JE LAN\n"
    "   Ein LAN bekommt in der Regel ein /64. Die hinteren 64 Bit\n"
    "   sind die Schnittstellenkennung (RFC 4291 2.5.1).\n\n"
    "KURZSCHREIBWEISE (RFC 5952) IN 5 REGELN\n"
    "   2001:0db8:abcd:0012:0000:0000:0000:0001 -> 2001:db8:abcd:12::1\n"
    "   1. Führende Nullen in jedem Hextett weglassen (0db8 -> db8).\n"
    "   2. Die längste Folge aus mindestens 2 Null-Hextetten wird\n"
    "      zu \"::\". \"::\" darf nur einmal vorkommen.\n"
    "   3. Bei zwei gleich langen Folgen wird die erste gekürzt.\n"
    "   4. Ein einzelnes Null-Hextett bleibt \"0\", nicht \"::\".\n"
    "   5. Die Buchstaben a bis f werden klein geschrieben."
)
CALC_EXPLAIN_SUBNET_V6_HANDY = (
    "RECHENWEG NETZDATEN (IPv6)\n"
    "Am Beispiel\n"
    " 2001:db8:abcd:12::1/64\n\n"
    "SCHRITT 1: Präfixlänge\n"
    "lesen\n"
    " IPv6 hat 128 Bit in 8\n"
    " Hextetten zu je 16 Bit.\n"
    " Die Zahl nach dem / sagt,\n"
    " wie viele Bits von links\n"
    " zum Netz gehören:\n"
    " /64 = die ersten 4\n"
    " Hextette.\n\n"
    "SCHRITT 2: Netzadresse\n"
    "bestimmen\n"
    " Alle Bits nach dem Präfix\n"
    " auf 0 setzen:\n"
    "  2001:db8:abcd:12::1\n"
    "  -> 2001:db8:abcd:12::\n"
    " -> Netzadresse:\n"
    "  2001:db8:abcd:12::/64\n\n"
    "SCHRITT 3: Adressen zählen\n"
    " Anzahl Adressen\n"
    " = 2^(128 - Präfixlänge)\n"
    " Bei /64: 2^(128 - 64)\n"
    " = 2^64\n"
    " = 18.446.744.073.709.551\n"
    "  .616\n"
    " Kein Abzug von 2: IPv6\n"
    " hat keine Broadcast-\n"
    " Adresse.\n"
    " -> erste Adresse:\n"
    "  2001:db8:abcd:12::\n"
    " -> letzte Adresse:\n"
    "  2001:db8:abcd:12:\n"
    "  ffff:ffff:ffff:ffff\n"
    " Einzelne Adressen sind\n"
    " reserviert, z. B. die\n"
    " Subnet-Router-Anycast-\n"
    " Adresse (alle Bits der\n"
    " Schnittstellenkennung 0,\n"
    " RFC 4291 2.6.1).\n\n"
    "HINWEIS: /64 JE LAN\n"
    " Ein LAN bekommt in der\n"
    " Regel ein /64. Die hinteren\n"
    " 64 Bit sind die\n"
    " Schnittstellenkennung\n"
    " (RFC 4291 2.5.1).\n\n"
    "KURZSCHREIBWEISE\n"
    "(RFC 5952) IN 5 REGELN\n"
    " 2001:0db8:abcd:0012:\n"
    " 0000:0000:0000:0001\n"
    " -> 2001:db8:abcd:12::1\n"
    " 1. Führende Nullen in\n"
    " jedem Hextett weglassen\n"
    " (0db8 -> db8).\n"
    " 2. Die längste Folge aus\n"
    " mindestens 2 Null-\n"
    " Hextetten wird zu \"::\".\n"
    " \"::\" darf nur einmal\n"
    " vorkommen.\n"
    " 3. Bei zwei gleich langen\n"
    " Folgen wird die erste\n"
    " gekürzt.\n"
    " 4. Ein einzelnes Null-\n"
    " Hextett bleibt \"0\",\n"
    " nicht \"::\".\n"
    " 5. Die Buchstaben a bis f\n"
    " werden klein geschrieben."
)


# ============================================================================
#  SUCHE
# ============================================================================

def search_content(query):
    """Durchsucht alle Lerninhalte. Liefert eine Liste von Treffern der Form
    (Art, Fachbereich, Titel, Detailtext)."""
    needle = query.lower()
    hits = []
    for card in KARTEIKARTEN:
        if needle in card["q"].lower() or needle in card["a_full"].lower():
            hits.append(("Karteikarte", card["cat"], card["q"], card["a_full"]))
    for question in QUIZ_QUESTIONS:
        if needle in question["q"].lower() or needle in question["exp"].lower():
            hits.append((KIND_QUIZ, question["cat"], question["q"],
                         question["exp"]))
    for scenario in SZENARIEN:
        haystack = scenario["title"] + scenario["text"] + scenario["solution"]
        if needle in haystack.lower():
            hits.append(("AP2-Szenario", scenario["cat"], scenario["title"],
                         scenario["text"].split("\n")[0]))
    for scenario in AP1_SZENARIEN:
        haystack = scenario["title"] + scenario["text"] + scenario["solution"]
        if needle in haystack.lower():
            hits.append(("AP1-Szenario", scenario["cat"], scenario["title"],
                         scenario["text"].split("\n")[0]))
    return hits
