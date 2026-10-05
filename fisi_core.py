#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FISI Lernplattform - Kernmodul
==============================

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
import unicodedata
import uuid

# ============================================================================
#  PFADE
# ============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEGACY_DB_PATH = os.path.join(BASE_DIR, "fisi_lernplattform.db")
APP_NAME = "FISI-Lernplattform"


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

    if os.name == "nt":
        root = os.environ.get("APPDATA") or os.path.expanduser("~")
        folder = os.path.join(root, APP_NAME)
    elif sys.platform == "darwin":
        folder = os.path.expanduser("~/Library/Application Support/" + APP_NAME)
    else:
        root = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
        folder = os.path.join(root, "fisi-lernplattform")

    try:
        os.makedirs(folder, exist_ok=True)
    except OSError:
        return LEGACY_DB_PATH
    return os.path.join(folder, "fisi_lernplattform.db")


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


def write_error_log(text):
    """Haengt einen Fehler mit Zeitpunkt und Version an fehler.log an. Darf
    selbst nie scheitern (kein Schreibrecht, volles Laufwerk ...)."""
    try:
        path = error_log_path()
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


class DBManager:
    """SQLite-Anbindung fuer Testergebnisse und einzelne Lern-Ereignisse.

    Die Tabelle test_results stammt aus der Vorgaengerversion und bleibt
    unveraendert erhalten. Neu hinzu kommen drei Ereignistabellen, die das
    Dashboard mit echten Zahlen versorgen.
    """

    def __init__(self, db_path=None, error_handler=None):
        self.db_path = db_path or resolve_db_path()
        self.error_handler = error_handler
        self.init_db()

    # -- Infrastruktur ------------------------------------------------------

    def _report(self, message):
        if self.error_handler:
            self.error_handler(message)
        else:
            print("[DB] " + message, file=sys.stderr)

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def _execute(self, sql, params=(), fetch=None, commit=False, default=None):
        """Fuehrt eine Abfrage aus und faengt Datenbankfehler zentral ab.

        Rueckgabe: bei fetch das Abfrageergebnis, bei einem reinen
        Schreibvorgang True. Im Fehlerfall immer der Wert von default.
        """
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
            cur.execute("UPDATE %s SET uid = lower(hex(randomblob(16))) "
                        "WHERE uid IS NULL" % table)
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
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
            "INSERT INTO test_results (timestamp, score, total, percentage, note,"
            " duration_seconds, uid) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (self._now(), score, total, percentage, note, duration_seconds, self._uid()),
            commit=True, default=False))

    def log_card(self, category, question, mode, correct):
        correct_value = None if correct is None else (1 if correct else 0)
        self._execute(
            "INSERT INTO card_events (timestamp, category, question, mode, correct, uid)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (self._now(), category, question, mode, correct_value, self._uid()),
            commit=True, default=False)

    def log_quiz_answer(self, category, question, correct):
        self._execute(
            "INSERT INTO quiz_answers (timestamp, category, question, correct, uid)"
            " VALUES (?, ?, ?, ?, ?)",
            (self._now(), category, question, 1 if correct else 0, self._uid()),
            commit=True, default=False)

    @staticmethod
    def _flag(correct):
        return None if correct is None else (1 if correct else 0)

    def log_scenario(self, index, title, theme, correct=None):
        """correct: Selbsteinschaetzung nach dem Aufdecken (ab 0.39), None =
        nur angesehen."""
        self._execute(
            "INSERT INTO scenario_events (timestamp, scenario_index, title, theme, correct,"
            " uid) VALUES (?, ?, ?, ?, ?, ?)",
            (self._now(), index, title, theme, self._flag(correct), self._uid()),
            commit=True, default=False)

    def log_project(self, index, title, category, correct=None):
        self._execute(
            "INSERT INTO project_events (timestamp, project_index, title, category, correct,"
            " uid) VALUES (?, ?, ?, ?, ?, ?)",
            (self._now(), index, title, category, self._flag(correct), self._uid()),
            commit=True, default=False)

    def log_ap1(self, index, title, theme, correct=None):
        self._execute(
            "INSERT INTO ap1_events (timestamp, scenario_index, title, theme, correct, uid)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (self._now(), index, title, theme, self._flag(correct), self._uid()),
            commit=True, default=False)

    # -- Ab 0.51: Trainer, Pruefungen, Abschlussprojekt ----------------------

    def log_trainer(self, kind, level, correct):
        """Eine geloeste Aufgabe des Subnetting-Trainers."""
        return bool(self._execute(
            "INSERT INTO trainer_aufgaben (timestamp, art, stufe, correct, uid)"
            " VALUES (?, ?, ?, ?, ?)",
            (self._now(), kind, int(level), 1 if correct else 0, self._uid()),
            commit=True, default=False))

    def trainer_stats(self):
        """{art: (geloest, richtig)} ueber alle Trainer-Aufgaben."""
        rows = self._execute("SELECT art, COUNT(*), SUM(correct) FROM trainer_aufgaben"
                             " GROUP BY art", fetch="all", default=[]) or []
        return {kind: (count or 0, right or 0) for kind, count, right in rows}

    def save_exam(self, kind, points, note, duration, data):
        """Ergebnis einer Klausursimulation (data: dict, als JSON gespeichert)."""
        return bool(self._execute(
            "INSERT INTO pruefungen (timestamp, art, punkte, note, dauer, daten, uid)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (self._now(), kind, float(points), note, int(duration),
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
            "INSERT INTO spiel_ereignisse (timestamp, typ, daten, geraet, uid, lauf)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (self._now(), kind, data, device or "", self._uid(), self._run(run)),
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
            "INSERT INTO spiel_bestenliste (timestamp, durchgang, art, schluessel, wert,"
            " daten, uid) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (self._now(), run or "", kind, key, value, data or "{}", self._uid()),
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
            cur.execute("INSERT OR REPLACE INTO sync_meta (key, value) VALUES (?, ?)",
                        ("bestenliste_reset_at", self._now()))
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
            cur.execute("INSERT OR REPLACE INTO sync_meta (key, value) VALUES (?, ?)",
                        ("history_cleared_at", self._now()))
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
            cur.execute("INSERT OR REPLACE INTO sync_meta (key, value) VALUES (?, ?)",
                        ("reset_at", self._now()))
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
            cur.execute("INSERT OR REPLACE INTO sync_meta (key, value) VALUES (?, ?)",
                        ("spiel_reset_at", self._now()))
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
            "  SELECT timestamp, 'Quizfrage', category,"
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
SOURCE_NAME = {SRC_CARD: "Karteikarte", SRC_QUIZ: "Quizfrage", SRC_AP1: "AP1-Szenario",
               SRC_AP2: "AP2-Szenario", SRC_PROJECT: "Testprojekt"}
SOURCE_PLURAL = {SRC_CARD: "Karteikarten", SRC_QUIZ: "Quizfragen", SRC_AP1: "AP1-Szenarien",
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
    host_list = list(network.hosts())
    return {
        "netz": network.network_address,
        "maske": network.netmask,
        "wildcard": network.hostmask,
        "broadcast": network.broadcast_address,
        "erste": host_list[0] if host_list else network.network_address,
        "letzte": host_list[-1] if host_list else network.broadcast_address,
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
        lines = [
            "Netzwerk-Adresse      : %s" % v["netz"],
            "Subnetzmaske          : %s" % v["maske"],
            "Wildcard-Maske        : %s" % v["wildcard"],
            "Broadcast-Adresse     : %s" % v["broadcast"],
            "Erste Host-Adresse    : %s" % v["erste"],
            "Letzte Host-Adresse   : %s" % v["letzte"],
            "Nutzbare Hosts        : %d" % v["hosts"],
            "Adressen gesamt       : %d" % v["adressen"],
            "CIDR-Präfix           : /%d" % v["praefix"],
        ]
    else:
        lines = [
            "Netzwerk-Adresse      : %s" % network.network_address,
            "Präfixlänge           : /%d" % network.prefixlen,
            "Erste Adresse         : %s" % network.network_address,
            "Letzte Adresse        : %s" % network[-1],
            "Adressen gesamt       : %d" % network.num_addresses,
        ]
    return "\n".join(lines)


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


def raid_report(level, disks_text, size_text):
    """Berechnet Nettokapazitaet, Paritaetsverlust und Effizienz eines RAID."""
    try:
        disks = int(disks_text)
        size = float(size_text.replace(",", "."))
    except ValueError:
        raise InputError("Bitte gültige Zahlen für Anzahl und "
                         "Kapazität eingeben.")
    if disks <= 0 or size <= 0:
        raise InputError("Anzahl und Kapazität müssen größer als 0 sein.")

    values = raid_input_values(level, disks, size)
    if values is None:
        minimum = raid_min_disks(level)
        extra = " und eine gerade Anzahl" if level == "RAID 10" else ""
        return ("Ungültige Konfiguration für %s.\n\n"
                "Benötigt werden mindestens %d Festplatten%s."
                % (level, minimum, extra))
    return "\n".join([
        "RAID-Level            : %s" % level,
        "Festplatten           : %d x %.0f GB" % (disks, size),
        "Bruttokapazität       : %.2f GB" % values["brutto"],
        "Nutzkapazität         : %.2f GB" % values["netto"],
        "Parität / Verlust     : %.2f GB" % values["verlust"],
        "Speichereffizienz     : %.1f %%" % values["effizienz"],
        "Ausfalltoleranz       : %s" % plural(values["toleranz"], "Festplatte", "Festplatten"),
    ])


def screen_report(width_text, height_text, depth, fps_text):
    """Berechnet das Datenvolumen eines Bildes und optional die Datenrate."""
    try:
        width = int(width_text)
        height = int(height_text)
        depth = int(depth)
        fps_raw = fps_text.strip().replace(",", ".")
        fps = float(fps_raw) if fps_raw else 0.0
    except ValueError:
        raise InputError("Bitte gültige Zahlen für Breite, Höhe und "
                         "Bildwiederholrate eingeben.")
    if width <= 0 or height <= 0:
        raise InputError("Breite und Höhe müssen größer als 0 sein.")
    if fps < 0:
        raise InputError("Die Bildwiederholrate darf nicht negativ sein.")

    pixels = width * height
    bits = pixels * depth
    data_bytes = bits / 8
    data_kb = data_bytes / 1024
    data_mb = data_kb / 1024

    lines = [
        "Auflösung             : %d x %d Pixel" % (width, height),
        "Pixel gesamt          : %s" % format(pixels, ","),
        "Farbtiefe             : %d Bit/Pixel" % depth,
        "Datenmenge pro Bild   : %d Bit" % bits,
        "                       : %s Byte" % format(int(data_bytes), ","),
        "                       : %.2f KB" % data_kb,
        "                       : %.2f MB" % data_mb,
    ]
    if fps > 0:
        bytes_per_sec = data_bytes * fps
        mbit_per_sec = bytes_per_sec * 8 / 1_000_000
        mb_per_sec = bytes_per_sec / (1024 * 1024)
        gb_per_min = bytes_per_sec * 60 / (1024 ** 3)
        lines += [
            "",
            "Bildwiederholrate     : %.0f Bilder/Sekunde" % fps,
            "Datenrate             : %.2f MB/s" % mb_per_sec,
            "                       : %.2f Mbit/s" % mbit_per_sec,
            "                       : %.2f GB/Minute" % gb_per_min,
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
UPS_TASKS_TITLE = "ÜBUNGSAUFGABEN"
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
    """Zahl in deutscher Schreibweise (1.234,56)."""
    text = "{:,.{}f}".format(value, digits)
    return text.replace(",", "#").replace(".", ",").replace("#", ".")


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
    raw = str(fields.get(key, "") or "").strip().replace(" ", "")
    if not raw:
        raise InputError("Bitte einen Wert eingeben: %s." % caption)
    raw = raw.replace(".", "").replace(",", ".") if raw.count(".") and \
        raw.count(",") else raw.replace(",", ".")
    try:
        value = float(raw)
    except ValueError:
        raise InputError("Bitte eine Zahl eingeben: %s." % caption)
    if value != value or value in (float("inf"), float("-inf")):
        raise InputError("Bitte eine Zahl eingeben: %s." % caption)
    if integer and value != int(value):
        raise InputError("Bitte eine ganze Zahl eingeben: %s." % caption)
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
    return bars


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
            "Laufzeit Lebensende   : %s min (%s %% Kapazität)"
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
            lines += ["  %s  %s" % ("ok  " if ok else "NEIN", text)
                      for ok, text in checks]
            if rated_w is None:
                lines.append("  Hinweis: ohne Nennleistung in W nur VA geprüft.")
    lines += ["", UPS_SIMPLE_TEXT]
    return {"text": "\n".join(lines), "bild": picture, "passend": passend}


# Uebungsaufgaben zum USV-Rechner: Werte typisch aus der Praxis (Annahmen,
# gekennzeichnet), Loesung wird mit denselben Formeln gerechnet.
UPS_TASKS = [
    {"titel": "Scheinleistung und Wirkleistung",
     "frage": "Ein Server hat laut Typenschild 800 VA bei einem Leistungsfaktor "
              "von 0,9. Wie groß ist die Wirkleistung in W? Welche Nennleistung "
              "in VA sollte die USV mindestens haben, wenn die Last höchstens "
              "80 % betragen soll?",
     "annahmen": "Leistungsfaktor 0,9 (Annahme, sonst Typenschild).",
     "werte": {"s": 800, "pf": 0.9}},
    {"titel": "Akku-Kapazität (Beispiel EnerSys)",
     "frage": "Eine USV soll 450 W Last 8 Stunden lang versorgen. Der "
              "Wechselrichter hat bei dieser Last einen Wirkungsgrad von 84 %, "
              "der Akkustrang hat 48 V. Wie viel Ah braucht der Strang?",
     "annahmen": "Ohne Alterungszuschlag, volle Nennkapazität nutzbar.",
     "werte": {"w": 450, "eta": 84, "min": 480, "v": 48, "alt": 0}},
    {"titel": "Laufzeit eines vorhandenen Akkus",
     "frage": "Eine kleine USV hat 2 Blöcke zu je 12 V und 9 Ah in Reihe. Die "
              "Last beträgt 300 W, der Wirkungsgrad 85 %. Wie lange läuft sie "
              "mit neuem Akku und am Lebensende (80 % Kapazität)?",
     "annahmen": "Wirkungsgrad 85 % (Annahme), volle Nennkapazität nutzbar.",
     "werte": {"w": 300, "eta": 85, "v": 12, "ah": 9, "reihe": 2, "par": 1,
               "alt": 25}},
    {"titel": "Passt die USV?",
     "frage": "Angeschlossen sind 1200 VA bei einem Leistungsfaktor von 0,9. "
              "Die USV hat 1500 VA und 1000 W Nennleistung. Ist sie nach der "
              "80-%-Regel passend?",
     "annahmen": "Leistungsfaktor 0,9 (Annahme). Nur die Leistung wird geprüft.",
     "werte": {"s": 1200, "pf": 0.9, "nenn_va": 1500, "nenn_w": 1000}},
    {"titel": "Akku mit Alterungszuschlag",
     "frage": "Ein Switch-Schrank braucht 1000 W für 10 Minuten. Wirkungsgrad "
              "90 %, Strangspannung 48 V, Alterungszuschlag 25 %. Wie viel Wh "
              "und Ah braucht der Akku?",
     "annahmen": "Wirkungsgrad 90 % (Annahme), volle Nennkapazität nutzbar.",
     "werte": {"w": 1000, "eta": 90, "min": 10, "v": 48, "alt": 25}},
    {"titel": "Wie viele Stränge?",
     "frage": "500 W sollen 30 Minuten überbrückt werden. Wirkungsgrad 80 %, "
              "Alterungszuschlag 25 %. Ein Strang besteht aus 2 Blöcken zu je "
              "12 V und 12 Ah in Reihe. Wie viele Stränge braucht man parallel?",
     "annahmen": "Wirkungsgrad 80 % (EnerSys-Richtwert ohne Herstellerwert).",
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
        steps = ["Zeit = %s min / 60 = %s h" % (_de_short(w["min"]), hours),
                 "Energie Last = %s W x %s h = %s Wh"
                 % (w["w"], hours, de_number(need["last_wh"])),
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
    count = int(need_wh // string_wh)
    return count + (1 if need_wh - count * string_wh > 1e-9 else 0)


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
    "   (in VA und in W). Beispiel USV 1500 VA / 900 W:\n"
    "   667 / 1500 = 44 %, 600 / 900 = 67 % -> passend,\n"
    "   18,43 min am Lebensende >= 15 min -> passend.\n\n"
    "QUELLEN\n"
    "   Leistungsfaktor = P / S: Wikipedia, Leistungsfaktor\n"
    "   Ah-Formel und Wirkungsgrad 0,80: EnerSys, Runtime and\n"
    "   right-sizing a UPS\n"
    "   Faktor 1,25 und 80 %: IEEE 485 (Vertiv/Battcon 2000)\n"
    "   80 % Auslastung: Schneider Electric, FAQ000268376"
)

# Rechenwege zum Aufklappen unter den Praxis-Rechnern
CALC_EXPLAIN_SUBNET = (
    "RECHENWEG SUBNETTING\n"
    "Am Beispiel 192.168.1.50/24\n\n"
    "SCHRITT 1: Präfix in Subnetzmaske umwandeln\n"
    "   Das Präfix (die Zahl nach dem /) gibt an, wie viele Bits von\n"
    "   links auf 1 gesetzt sind. /24 bedeutet: die ersten 24 Bits der\n"
    "   32-Bit-Adresse sind 1, der Rest ist 0.\n"
    "   /24 = 11111111.11111111.11111111.00000000\n"
    "       =    255   .   255   .   255   .    0\n"
    "   -> Subnetzmaske: 255.255.255.0\n\n"
    "SCHRITT 2: Netzwerk-Adresse berechnen\n"
    "   Netzwerk-Adresse = IP-Adresse AND Subnetzmaske\n"
    "   (bitweise UND-Verknüpfung: nur wenn IP UND Maske an\n"
    "   derselben Stelle eine 1 haben, bleibt dort eine 1 stehen)\n"
    "     192.168.1.50   = 11000000.10101000.00000001.00110010\n"
    "   AND 255.255.255.0 = 11111111.11111111.11111111.00000000\n"
    "   -------------------------------------------------------\n"
    "     Ergebnis         = 11000000.10101000.00000001.00000000\n"
    "   -> Netzwerk-Adresse: 192.168.1.0\n\n"
    "SCHRITT 3: Broadcast-Adresse berechnen\n"
    "   Wildcard-Maske = invertierte Subnetzmaske (alle Bits\n"
    "   umgedreht): 255.255.255.0 -> 0.0.0.255\n"
    "   Broadcast-Adresse = Netzwerk-Adresse OR Wildcard-Maske\n"
    "   (alle Host-Bits werden auf 1 gesetzt)\n"
    "   -> Broadcast-Adresse: 192.168.1.255\n\n"
    "SCHRITT 4: Nutzbare Host-Adressen zählen\n"
    "   Anzahl aller Adressen im Netz = 2^(32 - Präfixlänge)\n"
    "   Bei /24: 2^(32-24) = 2^8 = 256 Adressen\n"
    "   Davon sind die Netzwerk-Adresse (192.168.1.0) und die\n"
    "   Broadcast-Adresse (192.168.1.255) nicht als Host vergebbar,\n"
    "   deshalb -2:\n"
    "   Nutzbare Hosts = 2^(32 - Präfixlänge) - 2 = 256 - 2 = 254\n"
    "   -> erste nutzbare Adresse: 192.168.1.1\n"
    "   -> letzte nutzbare Adresse: 192.168.1.254\n\n"
    "HINWEIS ZU IPv6\n"
    "   IPv6 kennt keine Broadcast-Adresse, daher entfällt dort der\n"
    "   Abzug der -2 und alle Adressen im Netz gelten als nutzbar."
)
CALC_EXPLAIN_RAID = (
    "RECHENWEG RAID\n"
    "Am Beispiel 4 Festplatten x 1000 GB (Bruttokapazität 4000 GB)\n\n"
    "RAID 0 - Striping (min. 2 Platten)\n"
    "   Die Daten werden ohne Redundanz auf alle Platten verteilt.\n"
    "   Formel:  Netto = Anzahl x Kapazität\n"
    "   Beispiel: 4 x 1000 GB = 4000 GB nutzbar\n"
    "   Ausfalltoleranz: 0 Platten (fällt eine aus, sind alle Daten weg)\n\n"
    "RAID 1 - Mirroring (min. 2 Platten)\n"
    "   Die Daten werden 1:1 auf eine zweite Platte gespiegelt.\n"
    "   Formel:  Netto = 1 x Kapazität\n"
    "   Beispiel: 1000 GB nutzbar (bei 4 Platten stehen nur 1000 GB\n"
    "   Nutzkapazität zur Verfügung, der Rest ist Spiegelung)\n"
    "   Ausfalltoleranz: n-1 Platten\n\n"
    "RAID 5 - Parity, verteilte Parität (min. 3 Platten)\n"
    "   Eine Platte Kapazität wird rechnerisch für Paritätsdaten\n"
    "   verwendet (die Parität selbst liegt verteilt auf allen Platten).\n"
    "   Formel:  Netto = (Anzahl - 1) x Kapazität\n"
    "   Beispiel: (4 - 1) x 1000 GB = 3000 GB nutzbar\n"
    "   Ausfalltoleranz: 1 Platte\n\n"
    "RAID 6 - Double Parity (min. 4 Platten)\n"
    "   Wie RAID 5, aber mit doppelter Parität für mehr Sicherheit.\n"
    "   Formel:  Netto = (Anzahl - 2) x Kapazität\n"
    "   Beispiel: (4 - 2) x 1000 GB = 2000 GB nutzbar\n"
    "   Ausfalltoleranz: 2 Platten\n\n"
    "RAID 10 - Spiegelung + Striping (min. 4 Platten, gerade Anzahl)\n"
    "   Je zwei Platten werden gespiegelt (RAID 1), diese Spiegel-\n"
    "   Paare werden anschließend im Striping-Verfahren (RAID 0)\n"
    "   zusammengefasst.\n"
    "   Formel:  Netto = (Anzahl / 2) x Kapazität\n"
    "   Beispiel: (4 / 2) x 1000 GB = 2000 GB nutzbar\n"
    "   Ausfalltoleranz: 1 Platte je Spiegel-Paar\n\n"
    "SPEICHEREFFIZIENZ\n"
    "   Effizienz = Nettokapazität / Bruttokapazität x 100\n"
    "   Beispiel RAID 5: 3000 GB / 4000 GB x 100 = 75 %"
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
    "   True Color mit rund 16,7 Mio. Farben: je 8 Bit für Rot,\n"
    "   Grün und Blau).\n"
    "   Datenmenge (Bit) = Pixel gesamt x Farbtiefe\n"
    "   Beispiel: 2.073.600 x 24 Bit = 49.766.400 Bit\n\n"
    "SCHRITT 3: In Byte, KB und MB umrechnen\n"
    "   Da 1 Byte = 8 Bit sind, wird durch 8 geteilt; danach wird\n"
    "   jeweils durch 1024 geteilt, um die nächstgrößere Einheit\n"
    "   zu erhalten (Byte -> KB -> MB).\n"
    "   Byte = Bit / 8            -> 49.766.400 / 8 = 6.220.800 Byte\n"
    "   KB   = Byte / 1024        -> 6.220.800 / 1024 = 6.075,00 KB\n"
    "   MB   = KB / 1024          -> 6.075,00 / 1024 = 5,93 MB\n"
    "   -> Ein einzelnes Bild in dieser Auflösung und Farbtiefe\n"
    "      benötigt also rund 5,93 MB unkomprimierten Speicher.\n\n"
    "SCHRITT 4: Datenrate bei bewegten Bildern (Video)\n"
    "   Bei Videos wird nicht nur ein Bild, sondern mehrere Bilder\n"
    "   pro Sekunde angezeigt (Bildwiederholrate, engl. frames per\n"
    "   second, fps). Die Datenrate gibt an, wie viele Daten dafür\n"
    "   pro Sekunde anfallen.\n"
    "   Datenrate = Datenmenge pro Bild x Bildwiederholrate (fps)\n"
    "   Beispiel bei 30 fps: 6.220.800 Byte x 30 = 186.624.000 Byte/s\n"
    "   -> das sind rund 177,98 MB/s bzw. 1.492,99 Mbit/s bzw.\n"
    "      rund 10,43 GB/Minute.\n"
    "   Dieser enorme Wert zeigt, warum Videos in der Praxis fast\n"
    "   immer komprimiert (z.B. per H.264/H.265) übertragen werden."
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
            hits.append(("Quizfrage", question["cat"], question["q"],
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
