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
import random
import sqlite3
import datetime

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
#  KATEGORIEN UND FARBEN
# ============================================================================

CAT_NET = "Netzwerk & Protokolle"
CAT_SEC = "IT-Sicherheit & Datenschutz"
CAT_SYS = "Systeme, RAID & Hardware"
CAT_BIZ = "Wirtschaft & Prozesse"

CATEGORIES = [CAT_NET, CAT_SEC, CAT_SYS, CAT_BIZ]

CATEGORY_SHORT = {
    CAT_NET: "Netzwerk",
    CAT_SEC: "Sicherheit",
    CAT_SYS: "Systeme",
    CAT_BIZ: "Wirtschaft",
}

CATEGORY_ICON = {
    CAT_NET: "\u25c8",
    CAT_SEC: "\u25c9",
    CAT_SYS: "\u25a3",
    CAT_BIZ: "\u25b2",
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
}


def theme_block(theme):
    """Themenblock, zu dem ein Szenario-Thema im Dashboard zaehlt."""
    return THEME_BLOCK.get(theme, theme)


# ============================================================================
#  DATENBANK
# ============================================================================

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
                theme TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS project_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                project_index INTEGER NOT NULL,
                title TEXT NOT NULL,
                category TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS ap1_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                scenario_index INTEGER NOT NULL,
                title TEXT NOT NULL,
                theme TEXT NOT NULL
            )
            """,
        ]
        conn = None
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            for statement in statements:
                cur.execute(statement)
            conn.commit()
        except sqlite3.Error as exc:
            self._report("Datenbank konnte nicht initialisiert werden: %s" % exc)
        finally:
            if conn is not None:
                conn.close()

    @staticmethod
    def _now():
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # -- Schreiben ----------------------------------------------------------

    def save_test_result(self, score, total, percentage, note, duration_seconds):
        return bool(self._execute(
            "INSERT INTO test_results (timestamp, score, total, percentage, note, duration_seconds)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (self._now(), score, total, percentage, note, duration_seconds),
            commit=True, default=False))

    def log_card(self, category, question, mode, correct):
        correct_value = None if correct is None else (1 if correct else 0)
        self._execute(
            "INSERT INTO card_events (timestamp, category, question, mode, correct)"
            " VALUES (?, ?, ?, ?, ?)",
            (self._now(), category, question, mode, correct_value),
            commit=True, default=False)

    def log_quiz_answer(self, category, question, correct):
        self._execute(
            "INSERT INTO quiz_answers (timestamp, category, question, correct)"
            " VALUES (?, ?, ?, ?)",
            (self._now(), category, question, 1 if correct else 0),
            commit=True, default=False)

    def log_scenario(self, index, title, theme):
        self._execute(
            "INSERT INTO scenario_events (timestamp, scenario_index, title, theme)"
            " VALUES (?, ?, ?, ?)",
            (self._now(), index, title, theme),
            commit=True, default=False)

    def log_project(self, index, title, category):
        self._execute(
            "INSERT INTO project_events (timestamp, project_index, title, category)"
            " VALUES (?, ?, ?, ?)",
            (self._now(), index, title, category),
            commit=True, default=False)

    def log_ap1(self, index, title, theme):
        self._execute(
            "INSERT INTO ap1_events (timestamp, scenario_index, title, theme)"
            " VALUES (?, ?, ?, ?)",
            (self._now(), index, title, theme),
            commit=True, default=False)

    # -- Loeschen -----------------------------------------------------------

    def clear_history(self):
        return bool(self._execute("DELETE FROM test_results", commit=True, default=False))

    def reset_all(self):
        conn = None
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            for table in ("test_results", "card_events", "quiz_answers",
                          "scenario_events", "project_events", "ap1_events"):
                cur.execute("DELETE FROM " + table)
            conn.commit()
            return True
        except sqlite3.Error as exc:
            self._report("Zuruecksetzen fehlgeschlagen: %s" % exc)
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
        rows = self._execute(
            "SELECT DISTINCT project_index FROM project_events", fetch="all", default=[]) or []
        return {row[0] for row in rows}

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

    def streak(self):
        """Anzahl der aufeinanderfolgenden Tage mit Lernaktivitaet."""
        rows = self._execute(
            "SELECT DISTINCT substr(timestamp, 1, 10) FROM ("
            "  SELECT timestamp FROM card_events"
            "  UNION ALL SELECT timestamp FROM quiz_answers"
            "  UNION ALL SELECT timestamp FROM scenario_events"
            "  UNION ALL SELECT timestamp FROM project_events"
            "  UNION ALL SELECT timestamp FROM ap1_events"
            ") ORDER BY 1 DESC", fetch="all", default=[]) or []
        days = []
        for (value,) in rows:
            try:
                days.append(datetime.date.fromisoformat(value))
            except ValueError:
                pass
        if not days:
            return 0
        today = datetime.date.today()
        if days[0] not in (today, today - datetime.timedelta(days=1)):
            return 0
        count = 1
        for previous, current in zip(days, days[1:]):
            if (previous - current).days == 1:
                count += 1
            else:
                break
        return count


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
            "cat": CAT_NET,
            "q": "Wie lautet die Subnetzmaske für die CIDR-Notation /%d?" % prefix,
            "options": [mask] + mask_wrong,
            "a": mask,
            "exp": "/%d entspricht der Maske %s." % (prefix, mask),
        })
        host_distractors = sorted({h for h in all_hosts if h != hosts})
        host_wrong = random.Random(str(hosts)).sample(host_distractors, min(3, len(host_distractors)))
        db.append({
            "cat": CAT_NET,
            "q": "Wie viele nutzbare Host-IP-Adressen bietet ein Subnetz mit /%d?" % prefix,
            "options": [str(hosts)] + [str(h) for h in host_wrong],
            "a": str(hosts),
            "exp": "2^(32 - %d) minus 2 (Network-ID und Broadcast) = %d Hosts." % (prefix, hosts),
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
            "cat": CAT_NET,
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
    for abbr, meaning in sec_abbr:
        distractors = [m for _a, m in sec_abbr if m != meaning]
        wrong = random.Random(abbr).sample(distractors, 3)
        db.append({
            "cat": CAT_SEC,
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
            "cat": CAT_SYS,
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
            "cat": CAT_SYS,
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
    for abbr, meaning in biz_abbr:
        distractors = [m for _a, m in biz_abbr if m != meaning]
        wrong = random.Random(abbr).sample(distractors, 3)
        db.append({
            "cat": CAT_BIZ,
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


# ============================================================================
#  LERNINHALTE: AP2-SZENARIEN
# ============================================================================

SZENARIEN = load_content("szenarien_ap2")


# ============================================================================
#  LERNINHALTE: AP1 SZENARIEN (GRUNDLAGENPRUEFUNG)
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

    for number, scenario in enumerate(SZENARIEN, start=1):
        if theme_block(scenario.get("theme")) not in AP2_THEMES:
            problems.append("AP2-Szenario Nr. %d: unbekanntes Thema '%s' (AP2_THEMES "
                            "oder THEME_BLOCK ergaenzen)" % (number, scenario.get("theme")))
    for number, scenario in enumerate(AP1_SZENARIEN, start=1):
        if scenario.get("theme") not in AP1_THEMES:
            problems.append("AP1-Szenario Nr. %d: unbekanntes Thema '%s'"
                            % (number, scenario.get("theme")))
    for number, project in enumerate(PROJEKTARBEITEN, start=1):
        if len(project.get("aufgaben", [])) != len(project.get("hinweise", [])):
            problems.append("Testprojekt Nr. %d: je Aufgabe wird genau ein Hinweis "
                            "gebraucht" % number)
    return problems


def content_totals():
    """Anzahl verfuegbarer Inhalte je Fachbereich (Karten + Quizfragen)."""
    totals = {cat: 0 for cat in CATEGORIES}
    for card in KARTEIKARTEN:
        totals[card["cat"]] = totals.get(card["cat"], 0) + 1
    for question in QUIZ_QUESTIONS:
        totals[question["cat"]] = totals.get(question["cat"], 0) + 1
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

COLOR_DEPTHS = [("8", "8 Bit (256 Farben)"), ("16", "16 Bit (High Color)"),
                ("24", "24 Bit (True Color)"),
                ("32", "32 Bit (True Color + Alpha)")]


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
        hosts = network.num_addresses - 2 if network.prefixlen < 31 else \
            (2 if network.prefixlen == 31 else 1)
        host_list = list(network.hosts())
        first = host_list[0] if host_list else network.network_address
        last = host_list[-1] if host_list else network.broadcast_address
        lines = [
            "Netzwerk-Adresse      : %s" % network.network_address,
            "Subnetzmaske          : %s" % network.netmask,
            "Wildcard-Maske        : %s" % network.hostmask,
            "Broadcast-Adresse     : %s" % network.broadcast_address,
            "Erste Host-Adresse    : %s" % first,
            "Letzte Host-Adresse   : %s" % last,
            "Nutzbare Hosts        : %d" % hosts,
            "Adressen gesamt       : %d" % network.num_addresses,
            "CIDR-Präfix           : /%d" % network.prefixlen,
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

    minimum, formula = RAID_RULES[level]
    if disks < minimum or (level == "RAID 10" and disks % 2 != 0):
        extra = " und eine gerade Anzahl" if level == "RAID 10" else ""
        return ("Ungültige Konfiguration für %s.\n\n"
                "Benötigt werden mindestens %d Festplatten%s."
                % (level, minimum, extra))

    netto, tolerance = formula(disks, size)
    brutto = disks * size
    loss = brutto - netto
    efficiency = (netto / brutto * 100) if brutto else 0
    return "\n".join([
        "RAID-Level            : %s" % level,
        "Festplatten           : %d x %.0f GB" % (disks, size),
        "Bruttokapazität       : %.2f GB" % brutto,
        "Nutzkapazität         : %.2f GB" % netto,
        "Parität / Verlust     : %.2f GB" % loss,
        "Speichereffizienz     : %.1f %%" % efficiency,
        "Ausfalltoleranz       : %d Festplatte(n)" % tolerance,
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


# Rechenwege zum Aufklappen unter den Praxis-Rechnern
CALC_EXPLAIN_SUBNET = (
    "RECHENWEG SUBNETTING\n"
    "Am Beispiel 192.168.1.50/24\n\n"
    "SCHRITT 1: Praefix in Subnetzmaske umwandeln\n"
    "   Das Praefix (die Zahl nach dem /) gibt an, wie viele Bits von\n"
    "   links auf 1 gesetzt sind. /24 bedeutet: die ersten 24 Bits der\n"
    "   32-Bit-Adresse sind 1, der Rest ist 0.\n"
    "   /24 = 11111111.11111111.11111111.00000000\n"
    "       =    255   .   255   .   255   .    0\n"
    "   -> Subnetzmaske: 255.255.255.0\n\n"
    "SCHRITT 2: Netzwerk-Adresse berechnen\n"
    "   Netzwerk-Adresse = IP-Adresse AND Subnetzmaske\n"
    "   (bitweise UND-Verknuepfung: nur wenn IP UND Maske an der\n"
    "   selben Stelle eine 1 haben, bleibt dort eine 1 stehen)\n"
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
    "SCHRITT 4: Nutzbare Host-Adressen zaehlen\n"
    "   Anzahl aller Adressen im Netz = 2^(32 - Praefixlaenge)\n"
    "   Bei /24: 2^(32-24) = 2^8 = 256 Adressen\n"
    "   Davon sind die Netzwerk-Adresse (192.168.1.0) und die\n"
    "   Broadcast-Adresse (192.168.1.255) nicht als Host vergebbar,\n"
    "   deshalb -2:\n"
    "   Nutzbare Hosts = 2^(32 - Praefixlaenge) - 2 = 256 - 2 = 254\n"
    "   -> erste nutzbare Adresse: 192.168.1.1\n"
    "   -> letzte nutzbare Adresse: 192.168.1.254\n\n"
    "HINWEIS ZU IPv6\n"
    "   IPv6 kennt keine Broadcast-Adresse, daher entfaellt dort der\n"
    "   Abzug der -2 und alle Adressen im Netz gelten als nutzbar."
)
CALC_EXPLAIN_RAID = (
    "RECHENWEG RAID\n"
    "Am Beispiel 4 Festplatten x 1000 GB (Bruttokapazitaet 4000 GB)\n\n"
    "RAID 0 - Striping (min. 1 Platte)\n"
    "   Die Daten werden ohne Redundanz auf alle Platten verteilt.\n"
    "   Formel:  Netto = Anzahl x Kapazitaet\n"
    "   Beispiel: 4 x 1000 GB = 4000 GB nutzbar\n"
    "   Ausfalltoleranz: 0 Platten (faellt eine aus, sind alle Daten weg)\n\n"
    "RAID 1 - Mirroring (min. 2 Platten)\n"
    "   Die Daten werden 1:1 auf eine zweite Platte gespiegelt.\n"
    "   Formel:  Netto = 1 x Kapazitaet\n"
    "   Beispiel: 1000 GB nutzbar (bei 4 Platten stehen nur 1000 GB\n"
    "   Nutzkapazitaet zur Verfuegung, der Rest ist Spiegelung)\n"
    "   Ausfalltoleranz: n-1 Platten\n\n"
    "RAID 5 - Parity, verteilte Paritaet (min. 3 Platten)\n"
    "   Eine Platte Kapazitaet wird rechnerisch fuer Paritaetsdaten\n"
    "   verwendet (die Paritaet selbst liegt verteilt auf allen Platten).\n"
    "   Formel:  Netto = (Anzahl - 1) x Kapazitaet\n"
    "   Beispiel: (4 - 1) x 1000 GB = 3000 GB nutzbar\n"
    "   Ausfalltoleranz: 1 Platte\n\n"
    "RAID 6 - Double Parity (min. 4 Platten)\n"
    "   Wie RAID 5, aber mit doppelter Paritaet fuer mehr Sicherheit.\n"
    "   Formel:  Netto = (Anzahl - 2) x Kapazitaet\n"
    "   Beispiel: (4 - 2) x 1000 GB = 2000 GB nutzbar\n"
    "   Ausfalltoleranz: 2 Platten\n\n"
    "RAID 10 - Spiegelung + Striping (min. 4 Platten, gerade Anzahl)\n"
    "   Je zwei Platten werden gespiegelt (RAID 1), diese Spiegel-\n"
    "   Paare werden anschliessend im Striping-Verfahren (RAID 0)\n"
    "   zusammengefasst.\n"
    "   Formel:  Netto = (Anzahl / 2) x Kapazitaet\n"
    "   Beispiel: (4 / 2) x 1000 GB = 2000 GB nutzbar\n"
    "   Ausfalltoleranz: 1 Platte je Spiegel-Paar\n\n"
    "SPEICHEREFFIZIENZ\n"
    "   Effizienz = Nettokapazitaet / Bruttokapazitaet x 100\n"
    "   Beispiel RAID 5: 3000 GB / 4000 GB x 100 = 75 %"
)
CALC_EXPLAIN_SCREEN = (
    "RECHENWEG BILDSCHIRM-DATENVOLUMEN\n"
    "Am Beispiel 1920 x 1080 Pixel, 24 Bit Farbtiefe\n\n"
    "SCHRITT 1: Pixel gesamt ermitteln\n"
    "   Pixel gesamt = Breite x Hoehe\n"
    "   Beispiel: 1920 x 1080 = 2.073.600 Pixel\n\n"
    "SCHRITT 2: Datenmenge pro Bild in Bit berechnen\n"
    "   Jedes Pixel benoetigt fuer seine Farbe eine feste Anzahl Bit,\n"
    "   die sogenannte Farbtiefe (z.B. 8 Bit = 256 Farben, 24 Bit =\n"
    "   True Color mit rund 16,7 Mio. Farben: je 8 Bit fuer Rot,\n"
    "   Gruen und Blau).\n"
    "   Datenmenge (Bit) = Pixel gesamt x Farbtiefe\n"
    "   Beispiel: 2.073.600 x 24 Bit = 49.766.400 Bit\n\n"
    "SCHRITT 3: In Byte, KB und MB umrechnen\n"
    "   Da 1 Byte = 8 Bit sind, wird durch 8 geteilt; danach wird\n"
    "   jeweils durch 1024 geteilt, um die naechstgroessere Einheit\n"
    "   zu erhalten (Byte -> KB -> MB).\n"
    "   Byte = Bit / 8            -> 49.766.400 / 8 = 6.220.800 Byte\n"
    "   KB   = Byte / 1024        -> 6.220.800 / 1024 = 6.075,00 KB\n"
    "   MB   = KB / 1024          -> 6.075,00 / 1024 = 5,93 MB\n"
    "   -> Ein einzelnes Bild in dieser Aufloesung und Farbtiefe\n"
    "      benoetigt also rund 5,93 MB unkomprimierten Speicher.\n\n"
    "SCHRITT 4: Datenrate bei bewegten Bildern (Video)\n"
    "   Bei Videos wird nicht nur ein Bild, sondern mehrere Bilder\n"
    "   pro Sekunde angezeigt (Bildwiederholrate, engl. frames per\n"
    "   second, fps). Die Datenrate gibt an, wie viele Daten dafuer\n"
    "   pro Sekunde anfallen.\n"
    "   Datenrate = Datenmenge pro Bild x Bildwiederholrate (fps)\n"
    "   Beispiel bei 30 fps: 6.220.800 Byte x 30 = 186.624.000 Byte/s\n"
    "   -> das sind rund 177,98 MB/s bzw. 1.492,99 Mbit/s bzw.\n"
    "      rund 10,43 GB/Minute.\n"
    "   Dieser enorme Wert zeigt, warum Videos in der Praxis fast\n"
    "   immer komprimiert (z.B. per H.264/H.265) uebertragen werden."
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
