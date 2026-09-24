#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FISI Lernplattform - Kernmodul
==============================

Enthaelt:
  * Pfadaufloesung fuer die Datenbank (plattformunabhaengig)
  * DBManager: SQLite-Anbindung inkl. Lern-Events fuer das Dashboard
  * Farbpalette und Schriftaufloesung (Design-System)
  * Saemtliche Lerninhalte: Karteikarten, Quizfragen, AP2-Szenarien

Bewusst ohne externe Abhaengigkeiten, damit das Programm unter Windows,
Linux und macOS mit einer reinen Python-Installation laeuft.
"""

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

# Farbpalette der Oberflaeche
C = {
    "bg":        "#160C2A",
    "sidebar":   "#0F0720",
    "card":      "#1C1033",
    "card_alt":  "#251543",
    "card_hi":   "#311C58",
    "border":    "#33205A",
    "border_hi": "#553289",
    "text":      "#ECE6F8",
    "text_dim":  "#A794C6",
    "muted":     "#7D6B9C",
    "cyan":      "#22D3EE",
    "pink":      "#F472B6",
    "purple":    "#A78BFA",
    "green":     "#34D399",
    "yellow":    "#FBBF24",
    "orange":    "#FB923C",
    "blue":      "#60A5FA",
    "red":       "#F87171",
    "ring_bg":   "#2C1A4D",
}

CATEGORY_COLOR = {
    CAT_NET: C["cyan"],
    CAT_SEC: C["pink"],
    CAT_SYS: C["purple"],
    CAT_BIZ: C["green"],
}

# Die fuenf Themenbloecke der AP2 fuer die Timeline im Dashboard
AP2_THEMES = [
    ("Subnetting & Routing", C["cyan"]),
    ("IT-Sicherheit", C["pink"]),
    ("Storage & RAID", C["purple"]),
    ("Netzwerkdesign", C["blue"]),
    ("Wirtschaft & Beratung", C["green"]),
]


# ============================================================================
#  FARBHILFSFUNKTIONEN
# ============================================================================

def hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(round(v)))) for v in rgb)


def mix(color_a, color_b, t):
    """Mischt zwei Farben. t=0 liefert color_a, t=1 liefert color_b."""
    t = max(0.0, min(1.0, t))
    ra, ga, ba = hex_to_rgb(color_a)
    rb, gb, bb = hex_to_rgb(color_b)
    return rgb_to_hex((ra + (rb - ra) * t, ga + (gb - ga) * t, ba + (bb - ba) * t))


def lighten(color, amount=0.15):
    return mix(color, "#FFFFFF", amount)


def darken(color, amount=0.15):
    return mix(color, "#000000", amount)


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

    # -- Loeschen -----------------------------------------------------------

    def clear_history(self):
        return bool(self._execute("DELETE FROM test_results", commit=True, default=False))

    def reset_all(self):
        conn = None
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            for table in ("test_results", "card_events", "quiz_answers",
                          "scenario_events", "project_events"):
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
            "  SELECT timestamp, 'Test-Session', note,"
            "         CAST(score AS TEXT) || ' / ' || CAST(total AS TEXT)"
            "  FROM test_results"
            ") ORDER BY timestamp DESC LIMIT ?",
            (limit,), fetch="all", default=[]) or []
        return rows

    def theme_progress(self, theme_totals):
        """Fortschritt je AP2-Themenblock in Prozent."""
        rows = self._execute(
            "SELECT theme, COUNT(DISTINCT scenario_index) FROM scenario_events GROUP BY theme",
            fetch="all", default=[]) or []
        done = {row[0]: row[1] for row in rows}
        progress = {}
        for theme, _color in AP2_THEMES:
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
#  LERNINHALTE: KARTEIKARTEN
# ============================================================================

KARTEIKARTEN = [
    # --- Netzwerk & Protokolle -------------------------------------------
    {"cat": CAT_NET, "q": "Was ist der Standard-Port für HTTPS?",
     "a": "443",
     "a_full": "TCP Port 443 (verschlüsselte Webübertragung per TLS/SSL).",
     "options": ["80", "443", "22", "8080"]},
    {"cat": CAT_NET, "q": "Wofür steht die Abkürzung DNS?",
     "a": "Domain Name System",
     "a_full": "Domain Name System: Übersetzt menschlich lesbare Domainnamen in IP-Adressen.",
     "options": ["Domain Name System", "Data Network Service", "Dynamic Node Server", "Digital Network Storage"]},
    {"cat": CAT_NET, "q": "Welche Schicht des OSI-Modells ist für das Routing von IP-Paketen zuständig?",
     "a": "Schicht 3 (Netzwerkschicht)",
     "a_full": "Schicht 3 - Vermittlungsschicht / Network Layer (Routing, IP-Adressierung).",
     "options": ["Schicht 1 (Bitübertragung)", "Schicht 2 (Sicherung)", "Schicht 3 (Netzwerkschicht)", "Schicht 4 (Transport)"]},
    {"cat": CAT_NET, "q": "Wie viele Bits umfasst eine IPv6-Adresse?",
     "a": "128 Bits",
     "a_full": "Eine IPv6-Adresse ist 128 Bits lang.",
     "options": ["32 Bits", "64 Bits", "128 Bits", "256 Bits"]},
    {"cat": CAT_NET, "q": "Welches Protokoll weist Netzwerkgeräten automatisch IP-Adressen zu?",
     "a": "DHCP",
     "a_full": "DHCP (Dynamic Host Configuration Protocol) vergibt dynamisch IP-Adressen.",
     "options": ["DNS", "DHCP", "ARP", "ICMP"]},
    {"cat": CAT_NET, "q": "Welche Adressklasse hat den Bereich 192.0.0.0 - 223.255.255.255?",
     "a": "Klasse C",
     "a_full": "Klasse-C-Netze reichen von 192.0.0.0 bis 223.255.255.255, Standardmaske /24.",
     "options": ["Klasse A", "Klasse B", "Klasse C", "Klasse D"]},
    {"cat": CAT_NET, "q": "Wie nennt man ein Verfahren, bei dem mehrere physische Verbindungen zu einer logischen zusammengefasst werden?",
     "a": "Link Aggregation",
     "a_full": "Link Aggregation (z.B. LACP nach IEEE 802.3ad) bündelt mehrere physische Leitungen zu einer logischen mit höherer Bandbreite und Redundanz.",
     "options": ["Link Aggregation", "VLAN-Trunking", "Spanning Tree", "Port Mirroring"]},
    {"cat": CAT_NET, "q": "Welches Protokoll verhindert Schleifen (Loops) in geswitchten Netzwerken?",
     "a": "Spanning Tree Protocol (STP)",
     "a_full": "STP (IEEE 802.1D) erkennt redundante Pfade und blockiert sie logisch, um Broadcast-Stürme zu verhindern.",
     "options": ["Spanning Tree Protocol (STP)", "ARP", "NAT", "VRRP"]},
    {"cat": CAT_NET, "q": "Was übersetzt NAT (Network Address Translation)?",
     "a": "Private IP-Adressen in öffentliche IP-Adressen (und umgekehrt)",
     "a_full": "NAT übersetzt private, nicht routbare IP-Adressen in öffentliche Adressen für die Kommunikation im Internet.",
     "options": ["Private IP-Adressen in öffentliche IP-Adressen (und umgekehrt)", "MAC-Adressen in IP-Adressen", "Domainnamen in IP-Adressen", "VLAN-IDs in Ports"]},
    {"cat": CAT_NET, "q": "Welcher Netzwerktyp verbindet Standorte über das öffentliche Internet mit verschlüsseltem Tunnel?",
     "a": "VPN (Virtual Private Network)",
     "a_full": "Ein VPN baut einen verschlüsselten Tunnel über ein unsicheres Netz (meist Internet) auf, um Standorte oder Clients sicher zu verbinden.",
     "options": ["VPN (Virtual Private Network)", "WAN", "DMZ", "VLAN"]},
    {"cat": CAT_NET, "q": "Wie viele nutzbare Hosts bietet ein /30-Subnetz?",
     "a": "2",
     "a_full": "/30 hat 4 Gesamtadressen, minus Network- und Broadcast-Adresse bleiben 2 nutzbare Hosts (typisch für Punkt-zu-Punkt-Verbindungen).",
     "options": ["2", "4", "6", "14"]},
    {"cat": CAT_NET, "q": "Welches Protokoll ermittelt zu einer bekannten IP-Adresse die MAC-Adresse im lokalen Netz?",
     "a": "ARP",
     "a_full": "ARP (Address Resolution Protocol) ermittelt zu einer bekannten IP-Adresse die zugehörige MAC-Adresse im LAN.",
     "options": ["ARP", "DNS", "DHCP", "RARP"]},

    # --- IT-Sicherheit & Datenschutz --------------------------------------
    {"cat": CAT_SEC, "q": "Welches Schutzziel der IT-Sicherheit schützt vor unbefugter Datenveränderung?",
     "a": "Integrität",
     "a_full": "Integrität stellt sicher, dass Daten korrekt und unmanipuliert bleiben.",
     "options": ["Vertraulichkeit", "Integrität", "Verfügbarkeit", "Authentizität"]},
    {"cat": CAT_SEC, "q": "Was bedeutet die '1' in der bekannten 3-2-1-Backup-Regel?",
     "a": "1 Kopie an einem externen Ort",
     "a_full": "1 Kopie muss an einem physikalisch getrennten Ort aufbewahrt werden.",
     "options": ["1 Backup pro Tag", "1 Kopie an einem externen Ort", "1 verschlüsselte Datei", "1 zentraler Server"]},
    {"cat": CAT_SEC, "q": "Welches Schutzziel stellt sicher, dass Daten nur befugten Personen zugänglich sind?",
     "a": "Vertraulichkeit",
     "a_full": "Vertraulichkeit (Confidentiality) schützt Daten vor unbefugtem Zugriff, z.B. durch Verschlüsselung und Zugriffsrechte.",
     "options": ["Vertraulichkeit", "Integrität", "Verfügbarkeit", "Nichtabstreitbarkeit"]},
    {"cat": CAT_SEC, "q": "Was ist eine Zwei-Faktor-Authentifizierung (2FA)?",
     "a": "Anmeldung mit zwei unabhängigen Nachweisen (z.B. Passwort + Code)",
     "a_full": "2FA kombiniert zwei unterschiedliche Faktoren (Wissen, Besitz, Biometrie), um die Sicherheit gegenüber reiner Passwortauthentifizierung zu erhöhen.",
     "options": ["Anmeldung mit zwei unabhängigen Nachweisen (z.B. Passwort + Code)", "Zwei separate Passwörter hintereinander", "Anmeldung von zwei Geräten gleichzeitig", "Doppelte Verschlüsselung derselben Datei"]},
    {"cat": CAT_SEC, "q": "Wofür steht die Abkürzung DSGVO?",
     "a": "Datenschutz-Grundverordnung",
     "a_full": "Die DSGVO ist die EU-weite Datenschutz-Grundverordnung zum Schutz personenbezogener Daten.",
     "options": ["Datenschutz-Grundverordnung", "Datensicherungs- und Gefahrenverordnung", "Digitale Schutz- und Gewährleistungsordnung", "Datenschutz-Gesetzesverordnung"]},
    {"cat": CAT_SEC, "q": "Was beschreibt eine DDoS-Attacke?",
     "a": "Überlastung eines Systems durch massenhafte Anfragen aus vielen Quellen",
     "a_full": "Distributed Denial of Service: Viele verteilte Systeme (z.B. Botnetz) überlasten gleichzeitig ein Ziel, um es lahmzulegen.",
     "options": ["Überlastung eines Systems durch massenhafte Anfragen aus vielen Quellen", "Diebstahl von Zugangsdaten per E-Mail", "Verschlüsselung von Dateien gegen Lösegeld", "Abhören von Netzwerkverkehr"]},
    {"cat": CAT_SEC, "q": "Welche Rolle nach DSGVO überwacht die Einhaltung des Datenschutzes im Unternehmen?",
     "a": "Datenschutzbeauftragter",
     "a_full": "Der Datenschutzbeauftragte (DSB) berät und überwacht die Einhaltung der DSGVO im Unternehmen.",
     "options": ["Datenschutzbeauftragter", "IT-Administrator", "Compliance Officer", "Systemarchitekt"]},
    {"cat": CAT_SEC, "q": "Was ist eine Firewall im Kern?",
     "a": "Ein System, das Netzwerkverkehr nach definierten Regeln filtert",
     "a_full": "Eine Firewall überwacht und filtert ein- und ausgehenden Datenverkehr anhand von Regeln, um unerwünschte Zugriffe zu verhindern.",
     "options": ["Ein System, das Netzwerkverkehr nach definierten Regeln filtert", "Ein Programm zur Virenentfernung", "Ein Backup-Server", "Ein Verschlüsselungsalgorithmus"]},
    {"cat": CAT_SEC, "q": "Was unterscheidet eine Vollsicherung von einer inkrementellen Sicherung?",
     "a": "Vollsicherung sichert alle Daten, inkrementell nur Änderungen seit der letzten Sicherung",
     "a_full": "Eine Vollsicherung kopiert den kompletten Datenbestand, eine inkrementelle Sicherung nur die seit dem letzten Backup (egal welcher Art) geänderten Daten - spart Zeit und Speicherplatz, verlängert aber die Wiederherstellung.",
     "options": ["Vollsicherung sichert alle Daten, inkrementell nur Änderungen seit der letzten Sicherung", "Beide sichern immer den kompletten Datenbestand", "Inkrementell sichert nur einmal im Jahr", "Vollsicherung ist immer verschlüsselt, inkrementell nie"]},
    {"cat": CAT_SEC, "q": "Was regelt eine Passwort-Richtlinie nach aktuellen BSI-Empfehlungen primär?",
     "a": "Mindestlänge, Komplexität und Umgang mit Passwörtern (z.B. kein Wechselzwang ohne Anlass)",
     "a_full": "Das BSI empfiehlt heute lange, individuelle Passwörter (z.B. Passphrasen) statt starrem, regelmäßigem Passwortwechsel, sowie 2FA wo möglich.",
     "options": ["Mindestlänge, Komplexität und Umgang mit Passwörtern (z.B. kein Wechselzwang ohne Anlass)", "Passwörter müssen monatlich gewechselt werden", "Passwörter dürfen maximal 6 Zeichen lang sein", "Ein Passwort für alle Systeme genügt"]},
    {"cat": CAT_SEC, "q": "Wofür wird IPsec typischerweise eingesetzt?",
     "a": "Absicherung von VPN-Verbindungen auf Netzwerkebene (Schicht 3)",
     "a_full": "IPsec verschlüsselt und authentifiziert IP-Pakete auf Schicht 3 und wird häufig für Site-to-Site-VPNs eingesetzt.",
     "options": ["Absicherung von VPN-Verbindungen auf Netzwerkebene (Schicht 3)", "Verschlüsselung von E-Mail-Anhängen", "Absicherung von WLAN-Passwörtern", "Ein Protokoll zur Portfreigabe"]},
    {"cat": CAT_SEC, "q": "Wofür sorgt TLS (Transport Layer Security) bei einer HTTPS-Verbindung?",
     "a": "Verschlüsselung, Authentizität und Integrität der Datenübertragung",
     "a_full": "TLS baut über einen Handshake eine verschlüsselte, authentifizierte Verbindung zwischen Client und Server auf und schützt die Daten während der Übertragung.",
     "options": ["Verschlüsselung, Authentizität und Integrität der Datenübertragung", "Nur die Kompression der Webseite", "Automatisches Backup des Servers", "Die Zuweisung von IP-Adressen"]},
    {"cat": CAT_SEC, "q": "Was ist der Hauptunterschied zwischen einem Computervirus und einem Computerwurm?",
     "a": "Ein Virus benötigt ein Wirtsprogramm, ein Wurm verbreitet sich eigenständig über Netzwerke",
     "a_full": "Viren hängen sich an bestehende Dateien/Programme an und brauchen deren Ausführung, während sich Würmer selbstständig ohne Wirtsdatei über Netzwerke verbreiten.",
     "options": ["Ein Virus benötigt ein Wirtsprogramm, ein Wurm verbreitet sich eigenständig über Netzwerke", "Ein Wurm befällt nur Smartphones", "Ein Virus kann sich nicht verbreiten", "Beide Begriffe meinen dasselbe"]},
    {"cat": CAT_SEC, "q": "Warum ist regelmäßiges Patchmanagement sicherheitsrelevant?",
     "a": "Es schließt bekannte Schwachstellen zeitnah, bevor sie ausgenutzt werden können",
     "a_full": "Patchmanagement sorgt für die geplante, zeitnahe Einspielung von Sicherheitsupdates, um bekannte Sicherheitslücken zu schließen, bevor Angreifer sie ausnutzen.",
     "options": ["Es schließt bekannte Schwachstellen zeitnah, bevor sie ausgenutzt werden können", "Es beschleunigt nur die Systemleistung", "Es ist nur bei Neuinstallationen relevant", "Es ersetzt die Notwendigkeit von Backups"]},
    {"cat": CAT_SEC, "q": "Was beschreibt das Konzept einer Public-Key-Infrastruktur (PKI)?",
     "a": "Ein System zur Verwaltung digitaler Zertifikate und öffentlicher Schlüssel",
     "a_full": "Eine PKI stellt Prozesse und Komponenten (Zertifizierungsstelle, Registrierungsstelle, Zertifikate) bereit, um öffentliche Schlüssel vertrauenswürdig Personen oder Systemen zuzuordnen.",
     "options": ["Ein System zur Verwaltung digitaler Zertifikate und öffentlicher Schlüssel", "Ein Verfahren zur Passwortvergabe", "Ein Netzwerkprotokoll für DNS", "Ein RAID-Verfahren für Schlüsseldateien"]},
    {"cat": CAT_SEC, "q": "Was ist eine kryptografische Hashfunktion wie SHA-256 im Kern?",
     "a": "Eine Einwegfunktion, die aus beliebigen Daten einen Prüfwert fester Länge erzeugt",
     "a_full": "SHA-256 erzeugt aus beliebig großen Eingabedaten einen 256-Bit-Hashwert; die Berechnung ist nicht umkehrbar und dient z.B. der Integritätsprüfung.",
     "options": ["Eine Einwegfunktion, die aus beliebigen Daten einen Prüfwert fester Länge erzeugt", "Ein symmetrisches Verschlüsselungsverfahren", "Ein Kompressionsalgorithmus für Videos", "Ein Protokoll zur Schlüsselverteilung"]},
    {"cat": CAT_SEC, "q": "Was unterscheidet Datenschutz von Datensicherheit?",
     "a": "Datenschutz schützt personenbezogene Daten vor Missbrauch, Datensicherheit schützt Daten allgemein vor Verlust/Zugriff",
     "a_full": "Datenschutz (z.B. DSGVO) regelt den Umgang mit personenbezogenen Daten, während Datensicherheit technische und organisatorische Maßnahmen zum Schutz aller Daten vor Verlust, Manipulation oder unbefugtem Zugriff umfasst.",
     "options": ["Datenschutz schützt personenbezogene Daten vor Missbrauch, Datensicherheit schützt Daten allgemein vor Verlust/Zugriff", "Beide Begriffe sind rechtlich identisch", "Datensicherheit gilt nur für Backups", "Datenschutz betrifft nur Passwörter"]},
    {"cat": CAT_SEC, "q": "Was ist eine DMZ-Firewall-Regel typischerweise?",
     "a": "Nur bestimmte, notwendige Ports zu definierten Servern werden freigegeben, alles andere wird blockiert",
     "a_full": "Nach dem Prinzip 'Deny All, Allow by Exception' werden in einer DMZ nur die für den jeweiligen Dienst notwendigen Ports gezielt freigegeben.",
     "options": ["Nur bestimmte, notwendige Ports zu definierten Servern werden freigegeben, alles andere wird blockiert", "Es werden grundsätzlich alle Ports geöffnet", "DMZ-Server benötigen keine Firewall", "Firewall-Regeln gelten nur für ausgehenden Verkehr"]},
    {"cat": CAT_SEC, "q": "Was bedeutet Verbindlichkeit (Nichtabstreitbarkeit) als Schutzziel der IT-Sicherheit?",
     "a": "Ein Urheber einer Handlung/Nachricht kann diese im Nachhinein nicht abstreiten",
     "a_full": "Verbindlichkeit (Non-Repudiation) stellt sicher, dass z.B. eine digital signierte Nachricht eindeutig einem Absender zugeordnet und von diesem nicht bestritten werden kann.",
     "options": ["Ein Urheber einer Handlung/Nachricht kann diese im Nachhinein nicht abstreiten", "Daten sind jederzeit verfügbar", "Nur befugte Personen haben Zugriff", "Daten können nicht verändert werden"]},
    {"cat": CAT_SEC, "q": "Wofür steht die Abkürzung SIEM?",
     "a": "Security Information and Event Management",
     "a_full": "Ein SIEM-System sammelt, korreliert und analysiert sicherheitsrelevante Log- und Ereignisdaten aus verschiedenen Quellen in Echtzeit.",
     "options": ["Security Information and Event Management", "System Integrity and Encryption Module", "Secure Internal Email Monitoring", "Server Infrastructure and Endpoint Maintenance"]},

    # --- Systeme, RAID & Hardware -----------------------------------------
    {"cat": CAT_SYS, "q": "Wie viele Festplatten können bei einem RAID 5 maximal gleichzeitig ohne Datenverlust ausfallen?",
     "a": "1 Festplatte",
     "a_full": "RAID 5 verkraftet genau 1 Festplattenausfall.",
     "options": ["0 Festplatten", "1 Festplatte", "2 Festplatten", "Unbegrenzt"]},
    {"cat": CAT_SYS, "q": "Was ist der Unterschied zwischen RAID 5 und RAID 6?",
     "a": "RAID 6 nutzt doppelte Parität, RAID 5 einfache",
     "a_full": "RAID 6 schreibt Parität auf zwei Platten und verkraftet 2 Ausfälle, RAID 5 nur eine Paritätsplatte und verkraftet 1 Ausfall.",
     "options": ["RAID 6 nutzt doppelte Parität, RAID 5 einfache", "RAID 5 ist schneller als RAID 6 bei Schreibzugriffen", "RAID 6 benötigt weniger Platten als RAID 5", "Es gibt keinen Unterschied"]},
    {"cat": CAT_SYS, "q": "Was versteht man unter Virtualisierung?",
     "a": "Abstraktion physischer Hardware zur parallelen Nutzung durch mehrere virtuelle Systeme",
     "a_full": "Virtualisierung erlaubt es, mehrere voneinander unabhängige virtuelle Maschinen auf gemeinsam genutzter physischer Hardware zu betreiben.",
     "options": ["Abstraktion physischer Hardware zur parallelen Nutzung durch mehrere virtuelle Systeme", "Verschlüsselung von Festplatteninhalten", "Automatische Datensicherung in die Cloud", "Physisches Klonen von Festplatten"]},
    {"cat": CAT_SYS, "q": "Was ist ein Snapshot bei virtuellen Maschinen?",
     "a": "Ein Zustandsabbild der VM zu einem bestimmten Zeitpunkt",
     "a_full": "Ein Snapshot speichert den Zustand (Disk, RAM, Konfiguration) einer VM, um später darauf zurückzusetzen.",
     "options": ["Ein Zustandsabbild der VM zu einem bestimmten Zeitpunkt", "Ein vollständiges Backup auf Band", "Ein Netzwerk-Diagnosewerkzeug", "Ein RAID-Level"]},
    {"cat": CAT_SYS, "q": "Wofür wird eine USV (Unterbrechungsfreie Stromversorgung) primär eingesetzt?",
     "a": "Überbrückung kurzzeitiger Stromausfälle für Server/Systeme",
     "a_full": "Eine USV puffert Stromausfälle kurzfristig und ermöglicht ein geordnetes Herunterfahren kritischer Systeme.",
     "options": ["Überbrückung kurzzeitiger Stromausfälle für Server/Systeme", "Erhöhung der Netzwerkgeschwindigkeit", "Kühlung von Serverräumen", "Verschlüsselung von Datenträgern"]},
    {"cat": CAT_SYS, "q": "Was unterscheidet SSD grundsätzlich von HDD?",
     "a": "SSD speichert Daten elektronisch (Flash), HDD magnetisch auf rotierenden Scheiben",
     "a_full": "SSDs nutzen Flash-Speicherchips ohne bewegliche Teile, HDDs speichern Daten magnetisch auf rotierenden Scheiben mit Lese-/Schreibkopf.",
     "options": ["SSD speichert Daten elektronisch (Flash), HDD magnetisch auf rotierenden Scheiben", "SSD ist immer größer als HDD", "HDD ist grundsätzlich schneller als SSD", "Es gibt keinen technischen Unterschied"]},
    {"cat": CAT_SYS, "q": "Was zeichnet RAID 0 aus?",
     "a": "Striping ohne Redundanz - hohe Performance, aber kein Ausfallschutz",
     "a_full": "RAID 0 verteilt Daten blockweise auf mehrere Platten (Striping) und erhöht so die Geschwindigkeit, bietet aber keinerlei Redundanz - fällt eine Platte aus, sind alle Daten verloren.",
     "options": ["Striping ohne Redundanz - hohe Performance, aber kein Ausfallschutz", "Spiegelung mit vollem Ausfallschutz", "Parität auf zwei Platten verteilt", "Ein Backup-Verfahren ohne Festplatten"]},
    {"cat": CAT_SYS, "q": "Was ist ein JBOD (Just a Bunch Of Disks)?",
     "a": "Mehrere Festplatten werden ohne RAID-Verbund zu einem großen Volumen zusammengefasst",
     "a_full": "Bei JBOD werden einzelne Platten aneinandergereiht (Spanning) statt gestriped oder gespiegelt - ohne Performance- oder Redundanzvorteil eines echten RAID-Levels.",
     "options": ["Mehrere Festplatten werden ohne RAID-Verbund zu einem großen Volumen zusammengefasst", "Ein RAID-Level mit doppelter Parität", "Eine Cloud-Backup-Lösung", "Ein Verschlüsselungsstandard für SSDs"]},
    {"cat": CAT_SYS, "q": "Was bedeutet Thin Provisioning bei Speichersystemen?",
     "a": "Es wird nur der tatsächlich genutzte Speicherplatz physisch belegt, nicht der zugewiesene",
     "a_full": "Thin Provisioning weist einer VM oder einem Volume virtuell mehr Speicher zu, als physisch reserviert wird - Speicher wird erst bei tatsächlicher Nutzung belegt.",
     "options": ["Es wird nur der tatsächlich genutzte Speicherplatz physisch belegt, nicht der zugewiesene", "Jeder VM wird sofort die volle Kapazität physisch reserviert", "Ein Verfahren zur Datenkompression auf SSDs", "Ein RAID-Level speziell für Thin Clients"]},
    {"cat": CAT_SYS, "q": "Was ist der Unterschied zwischen Load Balancing und einem Failover-Cluster?",
     "a": "Load Balancing verteilt Last aktiv auf mehrere Systeme, Failover-Cluster übernimmt erst bei Ausfall",
     "a_full": "Load Balancing arbeitet mit mehreren gleichzeitig aktiven Systemen zur Lastverteilung, während ein Failover-Cluster im Normalfall meist nur ein aktives System hat und bei dessen Ausfall automatisch umschaltet.",
     "options": ["Load Balancing verteilt Last aktiv auf mehrere Systeme, Failover-Cluster übernimmt erst bei Ausfall", "Beide Begriffe beschreiben identische Verfahren", "Failover-Cluster benötigt keine Netzwerkverbindung", "Load Balancing funktioniert nur mit einer einzigen Platte"]},
    {"cat": CAT_SYS, "q": "Was ist der zentrale Unterschied zwischen einer VM und einem Container?",
     "a": "Eine VM virtualisiert komplette Hardware inkl. eigenem Betriebssystem, ein Container teilt sich den Kernel des Host-OS",
     "a_full": "Container (z.B. Docker) nutzen den Kernel des Hosts gemeinsam und sind dadurch deutlich leichtgewichtiger und schneller startbar als vollständige virtuelle Maschinen mit eigenem Gast-Betriebssystem.",
     "options": ["Eine VM virtualisiert komplette Hardware inkl. eigenem Betriebssystem, ein Container teilt sich den Kernel des Host-OS", "Container benötigen immer mehr Ressourcen als VMs", "Es gibt technisch keinen Unterschied", "VMs können nicht auf Servern betrieben werden"]},
    {"cat": CAT_SYS, "q": "Was ist die Hauptaufgabe von UEFI gegenüber dem klassischen BIOS?",
     "a": "Moderneres Firmware-Interface mit grafischer Oberfläche, Secure Boot und größeren Festplatten-Grenzen",
     "a_full": "UEFI (Unified Extensible Firmware Interface) löst das ältere BIOS ab, unterstützt GPT-Partitionen über 2 TB, Secure Boot und bietet meist eine grafische Bedienoberfläche.",
     "options": ["Moderneres Firmware-Interface mit grafischer Oberfläche, Secure Boot und größeren Festplatten-Grenzen", "Ein reines Backup-Programm für Server", "Ein RAID-Controller-Treiber", "Ein Netzwerkprotokoll für Fernwartung"]},
    {"cat": CAT_SYS, "q": "Wofür dient ein geplantes Wartungsfenster (Patchday) im Serverbetrieb?",
     "a": "Definierter Zeitraum für Updates/Wartung mit minimaler Störung des laufenden Betriebs",
     "a_full": "In einem Wartungsfenster werden Patches, Updates und Wartungsarbeiten gebündelt zu einem angekündigten, planbaren Zeitpunkt durchgeführt, um den Produktivbetrieb möglichst wenig zu stören.",
     "options": ["Definierter Zeitraum für Updates/Wartung mit minimaler Störung des laufenden Betriebs", "Ein täglicher automatischer Neustart aller Server", "Ein RAID-Level für Hochverfügbarkeit", "Ein Protokoll zur Fehlerdiagnose"]},
    {"cat": CAT_SYS, "q": "Was unterscheidet horizontale von vertikaler Skalierung?",
     "a": "Horizontal: mehr Server hinzufügen, Vertikal: Ressourcen eines Servers erhöhen",
     "a_full": "Horizontale Skalierung (Scale-out) fügt weitere Systeme hinzu, vertikale Skalierung (Scale-up) rüstet ein bestehendes System mit mehr CPU/RAM/Storage auf.",
     "options": ["Horizontal: mehr Server hinzufügen, Vertikal: Ressourcen eines Servers erhöhen", "Beide Begriffe bedeuten dasselbe", "Vertikale Skalierung betrifft nur Netzwerkkabel", "Horizontale Skalierung ist immer günstiger als vertikale"]},
    {"cat": CAT_SYS, "q": "Was beschreibt das Großvater-Vater-Sohn-Prinzip bei Backups?",
     "a": "Ein rotierendes Generationenkonzept mit täglichen, wöchentlichen und monatlichen Sicherungen",
     "a_full": "Das Großvater-Vater-Sohn-Verfahren (GFS) organisiert Backup-Medien in täglichen (Sohn), wöchentlichen (Vater) und monatlichen (Großvater) Sicherungsgenerationen zur effizienten Aufbewahrung.",
     "options": ["Ein rotierendes Generationenkonzept mit täglichen, wöchentlichen und monatlichen Sicherungen", "Ein RAID-Level mit drei Paritätsplatten", "Ein Cluster mit drei Serverknoten", "Ein Verfahren zur Benutzerverwaltung"]},
    {"cat": CAT_SYS, "q": "Wofür steht die Abkürzung SAN im Storage-Kontext?",
     "a": "Storage Area Network",
     "a_full": "Ein SAN ist ein eigenständiges, meist über Fibre Channel oder iSCSI angebundenes Speichernetzwerk, das Servern blockbasierten Speicher zentral bereitstellt.",
     "options": ["Storage Area Network", "System Area Node", "Secure Access Network", "Server Allocation Node"]},
    {"cat": CAT_SYS, "q": "Was ist der Vorteil eines Hot-Spare-Laufwerks in einem RAID-Verbund?",
     "a": "Es springt automatisch als Ersatz ein, sobald eine aktive Platte ausfällt",
     "a_full": "Ein Hot-Spare läuft mit, aber ungenutzt im System und wird bei Ausfall einer aktiven Platte automatisch in den RAID-Verbund eingebunden, um den Rebuild sofort zu starten.",
     "options": ["Es springt automatisch als Ersatz ein, sobald eine aktive Platte ausfällt", "Es erhöht dauerhaft die Lesegeschwindigkeit", "Es ersetzt die Notwendigkeit von Backups vollständig", "Es wird nur für RAID 0 benötigt"]},
    {"cat": CAT_SYS, "q": "Was misst die Kenngröße MTBF (Mean Time Between Failures)?",
     "a": "Die durchschnittliche Zeit zwischen zwei Ausfällen eines Geräts",
     "a_full": "MTBF ist eine statistische Kenngröße der Zuverlässigkeit, die angibt, wie lange ein System im Mittel störungsfrei läuft, bevor ein Ausfall auftritt.",
     "options": ["Die durchschnittliche Zeit zwischen zwei Ausfällen eines Geräts", "Die maximale Betriebstemperatur eines Servers", "Die Zeit bis zum vollständigen Datenverlust", "Die Anzahl der RAID-Level eines Systems"]},

    # --- Wirtschaft & Prozesse --------------------------------------------
    {"cat": CAT_BIZ, "q": "Wofür steht die Abkürzung TCO?",
     "a": "Total Cost of Ownership",
     "a_full": "Total Cost of Ownership betrachtet die Gesamtkosten über die Lebensdauer.",
     "options": ["Total Cost of Ownership", "Technical Control Office", "Time Critical Operation", "Target Cost Optimization"]},
    {"cat": CAT_BIZ, "q": "Was beschreibt die ITIL-Methodik primär?",
     "a": "Best Practices für IT-Service-Management",
     "a_full": "ITIL (IT Infrastructure Library) liefert einen Best-Practice-Rahmen für die Planung, Erbringung und Verbesserung von IT-Services.",
     "options": ["Best Practices für IT-Service-Management", "Ein Programmierparadigma", "Eine Netzwerktopologie", "Ein Verschlüsselungsstandard"]},
    {"cat": CAT_BIZ, "q": "Was ist der Unterschied zwischen Lasten- und Pflichtenheft?",
     "a": "Lastenheft = Anforderungen des Auftraggebers, Pflichtenheft = Umsetzungskonzept des Auftragnehmers",
     "a_full": "Das Lastenheft beschreibt das WAS und WOFÜR aus Kundensicht, das Pflichtenheft das WIE der Umsetzung aus Sicht des Auftragnehmers.",
     "options": ["Lastenheft = Anforderungen des Auftraggebers, Pflichtenheft = Umsetzungskonzept des Auftragnehmers", "Beide Begriffe meinen dasselbe Dokument", "Lastenheft ist für Hardware, Pflichtenheft für Software", "Pflichtenheft wird nur bei Reklamationen erstellt"]},
    {"cat": CAT_BIZ, "q": "Was misst der Return on Investment (ROI)?",
     "a": "Das Verhältnis von Gewinn zu eingesetztem Kapital",
     "a_full": "Der ROI zeigt, wie rentabel eine Investition war, indem der erzielte Gewinn ins Verhältnis zum eingesetzten Kapital gesetzt wird.",
     "options": ["Das Verhältnis von Gewinn zu eingesetztem Kapital", "Die Ausfallzeit eines Systems pro Jahr", "Die Anzahl der Support-Tickets pro Monat", "Die Lizenzkosten pro Nutzer"]},
    {"cat": CAT_BIZ, "q": "Welches Prinzip beschreibt Kaizen im Prozessmanagement?",
     "a": "Kontinuierlicher Verbesserungsprozess",
     "a_full": "Kaizen steht für die Philosophie der kontinuierlichen, schrittweisen Verbesserung von Prozessen.",
     "options": ["Kontinuierlicher Verbesserungsprozess", "Einmalige Großreform von Prozessen", "Ein Projektmanagement-Framework wie Scrum", "Eine Qualitätsnorm für Rechenzentren"]},
    {"cat": CAT_BIZ, "q": "Was zeigt der Deckungsbeitrag in der Kostenrechnung?",
     "a": "Den Betrag, der nach Abzug der variablen Kosten vom Umsatz zur Deckung der Fixkosten übrig bleibt",
     "a_full": "Deckungsbeitrag = Umsatz - variable Kosten. Er zeigt, wie viel vom Verkaufspreis zur Deckung der Fixkosten und zur Gewinnerzielung beiträgt.",
     "options": ["Den Betrag, der nach Abzug der variablen Kosten vom Umsatz zur Deckung der Fixkosten übrig bleibt", "Den kompletten Umsatz eines Produkts", "Nur die Fixkosten eines Unternehmens", "Den Gewinn nach Steuern"]},
    {"cat": CAT_BIZ, "q": "Was beschreibt der Break-Even-Point?",
     "a": "Den Punkt, an dem Erlöse und Kosten gleich hoch sind (Gewinnschwelle)",
     "a_full": "Am Break-Even-Point deckt der Umsatz genau die Gesamtkosten - ab diesem Punkt erwirtschaftet ein Produkt/Projekt Gewinn.",
     "options": ["Den Punkt, an dem Erlöse und Kosten gleich hoch sind (Gewinnschwelle)", "Den Zeitpunkt der höchsten Fixkosten", "Den Zeitpunkt, an dem alle Mitarbeiter Urlaub nehmen", "Den Beginn eines Geschäftsjahres"]},
    {"cat": CAT_BIZ, "q": "In welcher Reihenfolge werden Rabatt und Skonto im klassischen Kalkulationsschema abgezogen?",
     "a": "Zuerst Rabatt vom Listenpreis, danach Skonto vom Zielverkaufspreis",
     "a_full": "Listenpreis minus Rabatt ergibt den Zielverkaufspreis; davon wird anschließend der Skonto (Sofortzahlungsabzug) berechnet.",
     "options": ["Zuerst Rabatt vom Listenpreis, danach Skonto vom Zielverkaufspreis", "Zuerst Skonto, danach Rabatt", "Rabatt und Skonto werden addiert", "Beide werden gleichzeitig vom Bruttopreis abgezogen"]},
    {"cat": CAT_BIZ, "q": "Welche drei zentralen Rollen definiert das Scrum-Framework?",
     "a": "Product Owner, Scrum Master und Entwicklungsteam",
     "a_full": "Der Product Owner verantwortet das Product Backlog, der Scrum Master moderiert den Prozess, das Entwicklungsteam setzt die Arbeit in Sprints um.",
     "options": ["Product Owner, Scrum Master und Entwicklungsteam", "Projektleiter, Tester und Kunde", "CEO, CTO und Product Manager", "Auftraggeber, Auftragnehmer und Berater"]},
    {"cat": CAT_BIZ, "q": "Was ist ein zentraler Unterschied zwischen dem Wasserfallmodell und agilen Vorgehensweisen?",
     "a": "Wasserfall arbeitet in starren, aufeinanderfolgenden Phasen, agile Methoden iterativ mit flexiblen Anpassungen",
     "a_full": "Das Wasserfallmodell durchläuft feste Phasen (Anforderung, Design, Umsetzung, Test) nacheinander, während agile Methoden wie Scrum in kurzen Iterationen arbeiten und Anforderungen laufend anpassen.",
     "options": ["Wasserfall arbeitet in starren, aufeinanderfolgenden Phasen, agile Methoden iterativ mit flexiblen Anpassungen", "Beide Modelle sind inhaltlich identisch", "Agile Methoden erlauben keine Kundenrückmeldung", "Wasserfall wird nur bei Hardwareprojekten eingesetzt"]},
    {"cat": CAT_BIZ, "q": "Was ist der Unterschied zwischen Gewährleistung und Garantie?",
     "a": "Gewährleistung ist gesetzlich vorgeschrieben, Garantie ist eine freiwillige Zusatzleistung des Verkäufers/Herstellers",
     "a_full": "Die gesetzliche Gewährleistung (Sachmängelhaftung) gilt automatisch für jeden Kaufvertrag, eine Garantie ist ein freiwilliges, zusätzliches Versprechen des Verkäufers oder Herstellers.",
     "options": ["Gewährleistung ist gesetzlich vorgeschrieben, Garantie ist eine freiwillige Zusatzleistung des Verkäufers/Herstellers", "Beide Begriffe sind rechtlich identisch", "Garantie gilt immer länger als die Gewährleistung", "Gewährleistung gilt nur für digitale Produkte"]},
    {"cat": CAT_BIZ, "q": "Was unterscheidet eine Ersatzinvestition von einer Erweiterungsinvestition?",
     "a": "Ersatzinvestition ersetzt vorhandene Anlagen, Erweiterungsinvestition schafft zusätzliche Kapazitäten",
     "a_full": "Eine Ersatzinvestition tauscht abgenutzte oder veraltete Anlagen aus, eine Erweiterungsinvestition baut die Kapazität eines Unternehmens zusätzlich aus.",
     "options": ["Ersatzinvestition ersetzt vorhandene Anlagen, Erweiterungsinvestition schafft zusätzliche Kapazitäten", "Beide Begriffe meinen denselben Vorgang", "Erweiterungsinvestitionen betreffen nur Software", "Ersatzinvestitionen sind immer teurer"]},
    {"cat": CAT_BIZ, "q": "Was berechnet die statische Amortisationsrechnung?",
     "a": "Den Zeitraum, bis eine Investition durch die erzielten Rückflüsse wieder ausgeglichen ist",
     "a_full": "Die Amortisationsdauer zeigt, wie lange es dauert, bis die Summe der Rückflüsse einer Investition deren Anschaffungskosten deckt.",
     "options": ["Den Zeitraum, bis eine Investition durch die erzielten Rückflüsse wieder ausgeglichen ist", "Den Gesamtgewinn eines Unternehmens pro Jahr", "Die Höhe der jährlichen Abschreibung", "Den Marktwert einer gebrauchten Anlage"]},
    {"cat": CAT_BIZ, "q": "Was beschreibt die betriebswirtschaftliche Kennzahl Liquidität?",
     "a": "Die Fähigkeit eines Unternehmens, seinen Zahlungsverpflichtungen fristgerecht nachzukommen",
     "a_full": "Liquidität misst, ob und wie schnell ein Unternehmen fällige Zahlungen (z.B. an Lieferanten oder Mitarbeiter) begleichen kann.",
     "options": ["Die Fähigkeit eines Unternehmens, seinen Zahlungsverpflichtungen fristgerecht nachzukommen", "Die Anzahl der Mitarbeiter eines Unternehmens", "Den Marktanteil eines Unternehmens", "Die technische Verfügbarkeit eines Servers"]},
    {"cat": CAT_BIZ, "q": "Wer legt die wesentlichen Inhalte eines Ausbildungsvertrags nach dem Berufsbildungsgesetz (BBiG) fest?",
     "a": "Ausbildender (Betrieb) und Auszubildender einigen sich schriftlich, u.a. auf Ausbildungsziel, -dauer, Vergütung und Probezeit",
     "a_full": "Nach § 11 BBiG müssen im Ausbildungsvertrag u.a. Art, Ziel und Dauer der Ausbildung, Ausbildungsvergütung, Arbeitszeit, Probezeit und Kündigungsregeln schriftlich festgehalten werden.",
     "options": ["Ausbildender (Betrieb) und Auszubildender einigen sich schriftlich, u.a. auf Ausbildungsziel, -dauer, Vergütung und Probezeit", "Nur die IHK legt die Vertragsinhalte einseitig fest", "Der Vertrag muss nicht schriftlich abgeschlossen werden", "Die Ausbildungsvergütung ist gesetzlich nicht geregelt"]},
    {"cat": CAT_BIZ, "q": "Wodurch übt der Betriebsrat Mitbestimmung im Unternehmen aus?",
     "a": "Er vertritt die Interessen der Belegschaft u.a. bei sozialen, personellen und wirtschaftlichen Angelegenheiten",
     "a_full": "Der Betriebsrat wird von den Arbeitnehmern gewählt und hat nach dem Betriebsverfassungsgesetz Mitspracherechte, etwa bei Arbeitszeiten, Einstellungen oder Kündigungen.",
     "options": ["Er vertritt die Interessen der Belegschaft u.a. bei sozialen, personellen und wirtschaftlichen Angelegenheiten", "Er legt allein die Gehälter aller Mitarbeiter fest", "Er ersetzt die Geschäftsführung des Unternehmens", "Er ist nur für die IT-Sicherheit zuständig"]},
    {"cat": CAT_BIZ, "q": "Was ist der Unterschied zwischen Vollkosten- und Teilkostenrechnung?",
     "a": "Vollkostenrechnung verrechnet alle Kosten auf Produkte, Teilkostenrechnung nur die variablen (relevanten) Kosten",
     "a_full": "Die Vollkostenrechnung schlüsselt sämtliche fixen und variablen Kosten auf Kostenträger um, während die Teilkostenrechnung (z.B. Deckungsbeitragsrechnung) nur variable Kosten den Produkten direkt zuordnet.",
     "options": ["Vollkostenrechnung verrechnet alle Kosten auf Produkte, Teilkostenrechnung nur die variablen (relevanten) Kosten", "Beide Verfahren liefern immer identische Ergebnisse", "Teilkostenrechnung berücksichtigt nur Personalkosten", "Vollkostenrechnung wird nur bei Verlust angewendet"]},
]


# ============================================================================
#  LERNINHALTE: QUIZFRAGEN
# ============================================================================

def build_quiz_database():
    """Baut den Fragenkatalog auf - feste Fragen plus generierte Aufgaben."""
    db = [
        # --- Netzwerke & Protokolle ---------------------------------------
        {"cat": CAT_NET, "q": "Welches Protokoll überträgt Dateien verschlüsselt über TCP-Port 22?",
         "options": ["SFTP / SSH", "FTP", "TFTP", "HTTP"], "a": "SFTP / SSH",
         "exp": "SFTP nutzt SSH zur Verschlüsselung über TCP-Port 22."},
        {"cat": CAT_NET, "q": "Welches Protokoll dient zur dynamischen Zuweisung von IP-Adressen?",
         "options": ["DHCP", "DNS", "ARP", "ICMP"], "a": "DHCP",
         "exp": "DHCP (Dynamic Host Configuration Protocol) verteilt automatisch IP-Konfigurationen."},
        {"cat": CAT_NET, "q": "Auf welcher OSI-Schicht arbeitet ein Layer-2-Switch?",
         "options": ["Schicht 2 (Sicherungsschicht)", "Schicht 1 (Bitübertragung)", "Schicht 3 (Vermittlungsschicht)", "Schicht 4 (Transport)"],
         "a": "Schicht 2 (Sicherungsschicht)",
         "exp": "Layer-2-Switches verarbeiten MAC-Adressen auf Schicht 2 (Data Link Layer)."},
        {"cat": CAT_NET, "q": "Welches Protokoll wird von ping verwendet, um Erreichbarkeit zu prüfen?",
         "options": ["ICMP", "IGMP", "UDP", "ARP"], "a": "ICMP",
         "exp": "Ping nutzt ICMP (Internet Control Message Protocol) Echo-Request und Echo-Reply."},
        {"cat": CAT_NET, "q": "Was ist die Hauptaufgabe des IEEE-Standards 802.1Q?",
         "options": ["VLAN-Tagging im Ethernet-Frame", "WLAN-Verschlüsselung", "Spanning Tree Protocol", "Power over Ethernet (PoE)"],
         "a": "VLAN-Tagging im Ethernet-Frame",
         "exp": "802.1Q definiert das Tagging von VLANs in Ethernet-Frames."},
        {"cat": CAT_NET, "q": "Welche Standard-Subnetzmaske entspricht der CIDR-Notation /28?",
         "options": ["255.255.255.240", "255.255.255.0", "255.255.255.224", "255.255.255.248"],
         "a": "255.255.255.240",
         "exp": "/28 entspricht 255.255.255.240 (16 Gesamt-IPs, 14 nutzbare Hosts)."},
        {"cat": CAT_NET, "q": "Welches Routing-Protokoll ist ein internes Link-State-Protokoll?",
         "options": ["OSPF", "BGP", "RIP", "EGP"], "a": "OSPF",
         "exp": "OSPF (Open Shortest Path First) ist ein internes Link-State-Routing-Protokoll."},
        {"cat": CAT_NET, "q": "Welcher Port wird standardmäßig für unverschlüsseltes HTTP genutzt?",
         "options": ["80", "443", "8080", "21"], "a": "80",
         "exp": "Port 80 TCP ist der Standard-Port für HTTP."},
        {"cat": CAT_NET, "q": "Welches Protokoll wird für den Versand von E-Mails genutzt?",
         "options": ["SMTP", "IMAP", "POP3", "FTP"], "a": "SMTP",
         "exp": "SMTP (Simple Mail Transfer Protocol) wird zum Versenden von E-Mails zwischen Servern verwendet."},
        {"cat": CAT_NET, "q": "Was ist der Unterschied zwischen IMAP und POP3?",
         "options": ["IMAP synchronisiert Mails auf dem Server, POP3 lädt sie herunter und löscht sie meist lokal ab", "POP3 ist verschlüsselt, IMAP nicht", "IMAP funktioniert nur mit Exchange-Servern", "Es gibt funktional keinen Unterschied"],
         "a": "IMAP synchronisiert Mails auf dem Server, POP3 lädt sie herunter und löscht sie meist lokal ab",
         "exp": "IMAP hält den Postfach-Zustand auf dem Server synchron (mehrere Geräte), POP3 lädt Mails in der Regel lokal herunter."},
        {"cat": CAT_NET, "q": "Welches Gerät verbindet unterschiedliche Netzwerksegmente auf OSI-Schicht 3?",
         "options": ["Router", "Switch", "Hub", "Repeater"], "a": "Router",
         "exp": "Router arbeiten auf Schicht 3 und leiten Pakete anhand von IP-Adressen zwischen unterschiedlichen Netzen weiter."},
        {"cat": CAT_NET, "q": "Was beschreibt Broadcast in einem Netzwerk?",
         "options": ["Eine Nachricht wird an alle Teilnehmer im Netzsegment gesendet", "Eine Nachricht wird nur an einen einzigen Empfänger gesendet", "Eine Nachricht wird an eine definierte Gruppe gesendet", "Eine Nachricht wird verschlüsselt übertragen"],
         "a": "Eine Nachricht wird an alle Teilnehmer im Netzsegment gesendet",
         "exp": "Ein Broadcast wird an alle Geräte im gleichen Broadcast-Domain-Segment gesendet."},
        {"cat": CAT_NET, "q": "Wofür wird Traceroute / tracert verwendet?",
         "options": ["Anzeigen der Route (Hops) eines Pakets zum Ziel", "Messen der WLAN-Signalstärke", "Scannen offener Ports", "Anzeigen der MAC-Adresstabelle"],
         "a": "Anzeigen der Route (Hops) eines Pakets zum Ziel",
         "exp": "Traceroute zeigt alle Zwischenstationen (Hops) auf dem Weg zu einem Zielhost inklusive Laufzeiten."},
        {"cat": CAT_NET, "q": "Was ist eine DMZ (Demilitarized Zone) im Netzwerkkontext?",
         "options": ["Ein abgeschirmtes Zwischennetz für öffentlich erreichbare Server", "Ein Backup-Rechenzentrum", "Ein VLAN für Gäste-WLAN", "Ein Verschlüsselungsprotokoll"],
         "a": "Ein abgeschirmtes Zwischennetz für öffentlich erreichbare Server",
         "exp": "Die DMZ trennt öffentlich erreichbare Dienste (z.B. Webserver) vom internen, schützenswerten Netz."},
        {"cat": CAT_NET, "q": "Welcher Adressbereich ist laut RFC 1918 für private Netze reserviert?",
         "options": ["10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16", "127.0.0.0/8", "169.254.0.0/16", "224.0.0.0/4"],
         "a": "10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16",
         "exp": "RFC 1918 definiert diese drei Bereiche als privaten, nicht öffentlich routbaren Adressraum."},
        {"cat": CAT_NET, "q": "Wofür steht MTU bei Netzwerkverbindungen?",
         "options": ["Maximum Transmission Unit - maximale Paketgröße", "Maximum Transfer Uplink", "Media Traffic Unit", "Multi Terminal Unit"],
         "a": "Maximum Transmission Unit - maximale Paketgröße",
         "exp": "Die MTU gibt die maximale Größe eines Datenpakets an, das ohne Fragmentierung übertragen werden kann (Ethernet-Standard: 1500 Byte)."},

        # --- IT-Sicherheit & Datenschutz ----------------------------------
        {"cat": CAT_SEC, "q": "Welches Schutzziel der IT-Sicherheit stellt sicher, dass Daten nicht unbefugt verändert werden?",
         "options": ["Integrität", "Vertraulichkeit", "Verfügbarkeit", "Authentizität"], "a": "Integrität",
         "exp": "Integrität schützt vor unautorisierter Manipulation von Daten."},
        {"cat": CAT_SEC, "q": "Welches symmetrische Verschlüsselungsverfahren gilt heute als weltweiter Standard?",
         "options": ["AES", "DES", "RSA", "3DES"], "a": "AES",
         "exp": "AES (Advanced Encryption Standard) ist der aktuelle Industriestandard für symmetrische Verschlüsselung."},
        {"cat": CAT_SEC, "q": "Was ist das Hauptmerkmal einer asymmetrischen Verschlüsselung?",
         "options": ["Ein öffentlicher Schlüssel (Public Key) und ein privater Schlüssel (Private Key)", "Ein gemeinsamer geheimer Schlüssel für Sender und Empfänger", "Nur Einweg-Hashes ohne Entschlüsselung", "Automatische Zertifikatsgenerierung"],
         "a": "Ein öffentlicher Schlüssel (Public Key) und ein privater Schlüssel (Private Key)",
         "exp": "Asymmetrische Verfahren nutzen ein Schlüsselpaar aus Public Key (Verschlüsseln) und Private Key (Entschlüsseln)."},
        {"cat": CAT_SEC, "q": "Was beschreibt der Begriff Phishing?",
         "options": ["Täuschung von Benutzern über gefälschte Mails/Websites zur Erlangung von Zugangsdaten", "Überlastung von Servern durch Massenanfragen", "Einschleusen von Schadcode über Formulareingaben", "Abfangen von Daten im lokalen WLAN"],
         "a": "Täuschung von Benutzern über gefälschte Mails/Websites zur Erlangung von Zugangsdaten",
         "exp": "Phishing ist Social Engineering zur Entwendung vertraulicher Daten."},
        {"cat": CAT_SEC, "q": "Gemäß DSGVO müssen Datenschutzverstöße an die Aufsichtsbehörde gemeldet werden. Wie lang ist die Frist?",
         "options": ["72 Stunden", "24 Stunden", "7 Tage", "14 Tage"], "a": "72 Stunden",
         "exp": "Die Meldung von Datenpannen nach Art. 33 DSGVO muss binnen 72 Stunden erfolgen."},
        {"cat": CAT_SEC, "q": "Was beschreibt die 3-2-1-Backup-Regel?",
         "options": ["3 Kopien, 2 verschiedene Medien, 1 Kopie außer Haus", "3 Backups pro Tag, 2 Wochen Aufbewahrung, 1 Jahresarchiv", "3 Cloud-Anbieter, 2 lokale Server, 1 Bandlaufwerk", "3 Vollbackups, 2 inkrementelle, 1 differentielles"],
         "a": "3 Kopien, 2 verschiedene Medien, 1 Kopie außer Haus",
         "exp": "3-2-1-Regel: Mindestens 3 Datenkopien, 2 unterschiedliche Medientypen, 1 extern gelagert."},
        {"cat": CAT_SEC, "q": "Was ist ein Zero-Day-Exploit?",
         "options": ["Ausnutzung einer Sicherheitslücke, für die noch kein Patch existiert", "Ein Angriff, der genau um Mitternacht stattfindet", "Ein Backup ohne Aufbewahrungsfrist", "Ein Verschlüsselungsverfahren ohne Schlüssel"],
         "a": "Ausnutzung einer Sicherheitslücke, für die noch kein Patch existiert",
         "exp": "Ein Zero-Day-Exploit nutzt eine Schwachstelle aus, bevor der Hersteller einen Patch bereitstellen konnte."},
        {"cat": CAT_SEC, "q": "Was beschreibt das Prinzip Least Privilege?",
         "options": ["Nutzer erhalten nur die minimal notwendigen Rechte für ihre Aufgabe", "Administratoren erhalten automatisch alle Rechte", "Passwörter müssen mindestens 8 Zeichen haben", "Jeder Nutzer bekommt Gastrechte"],
         "a": "Nutzer erhalten nur die minimal notwendigen Rechte für ihre Aufgabe",
         "exp": "Least Privilege minimiert Schaden im Missbrauchsfall, indem nur notwendige Berechtigungen vergeben werden."},
        {"cat": CAT_SEC, "q": "Was ist der Zweck eines Penetrationstests?",
         "options": ["Gezieltes, autorisiertes Aufspüren von Sicherheitslücken durch simulierte Angriffe", "Automatisches Patchen von Systemen", "Löschen alter Log-Dateien", "Messen der Netzwerkgeschwindigkeit"],
         "a": "Gezieltes, autorisiertes Aufspüren von Sicherheitslücken durch simulierte Angriffe",
         "exp": "Ein Penetrationstest simuliert reale Angriffe, um Schwachstellen aufzudecken, bevor es echte Angreifer tun."},
        {"cat": CAT_SEC, "q": "Was versteht man unter Social Engineering?",
         "options": ["Manipulation von Personen, um an vertrauliche Informationen zu gelangen", "Automatisiertes Scannen von Netzwerken", "Ein Verschlüsselungsverfahren", "Ein Framework für agile Teams"],
         "a": "Manipulation von Personen, um an vertrauliche Informationen zu gelangen",
         "exp": "Social Engineering nutzt psychologische Manipulation statt technischer Lücken, um an Informationen oder Zugriff zu gelangen."},
        {"cat": CAT_SEC, "q": "Wofür steht IDS im Sicherheitskontext?",
         "options": ["Intrusion Detection System", "Internal Data Storage", "Integrated Device Security", "Instant Data Sync"],
         "a": "Intrusion Detection System",
         "exp": "Ein IDS überwacht Netzwerk- oder Systemaktivitäten und meldet verdächtige Ereignisse."},
        {"cat": CAT_SEC, "q": "Was ist der Unterschied zwischen einem IDS und einem IPS?",
         "options": ["IDS erkennt und meldet nur, IPS kann Angriffe zusätzlich aktiv blockieren", "IDS ist nur Hardware, IPS nur Software", "IPS überwacht E-Mails, IDS überwacht Netzwerke", "Es gibt keinen Unterschied"],
         "a": "IDS erkennt und meldet nur, IPS kann Angriffe zusätzlich aktiv blockieren",
         "exp": "Ein Intrusion Prevention System (IPS) kann im Gegensatz zum reinen Intrusion Detection System (IDS) aktiv eingreifen und Verkehr blockieren."},
        {"cat": CAT_SEC, "q": "Was ist Hashing im Sicherheitskontext?",
         "options": ["Umwandlung von Daten in einen Prüfwert fester Länge, der nicht umkehrbar ist", "Ein symmetrisches Verschlüsselungsverfahren", "Ein Backup-Verfahren", "Ein Netzwerkprotokoll"],
         "a": "Umwandlung von Daten in einen Prüfwert fester Länge, der nicht umkehrbar ist",
         "exp": "Hashfunktionen erzeugen aus beliebigen Daten einen eindeutigen Prüfwert, z.B. zur Integritätsprüfung oder Passwortspeicherung - Hashing ist nicht umkehrbar."},
        {"cat": CAT_SEC, "q": "Wie hoch kann ein DSGVO-Bußgeld maximal ausfallen?",
         "options": ["Bis zu 20 Mio. Euro oder 4% des weltweiten Jahresumsatzes", "Maximal 1.000 Euro pro Verstoß", "Maximal 500.000 Euro pauschal", "Es drohen keine Bußgelder, nur Verwarnungen"],
         "a": "Bis zu 20 Mio. Euro oder 4% des weltweiten Jahresumsatzes",
         "exp": "Art. 83 DSGVO sieht Bußgelder bis 20 Mio. Euro oder 4% des weltweiten Jahresumsatzes vor, je nachdem, was höher ist."},
        {"cat": CAT_SEC, "q": "Was besagt Kerckhoffs' Prinzip in der Kryptografie?",
         "options": ["Die Sicherheit eines Verschlüsselungsverfahrens darf nur vom geheimen Schlüssel abhängen, nicht von der Geheimhaltung des Algorithmus", "Verschlüsselung ist nur bei geheimem Algorithmus sicher", "Jeder Schlüssel darf nur einmal verwendet werden", "Passwörter müssen mindestens 20 Zeichen lang sein"],
         "a": "Die Sicherheit eines Verschlüsselungsverfahrens darf nur vom geheimen Schlüssel abhängen, nicht von der Geheimhaltung des Algorithmus",
         "exp": "Kerckhoffs' Prinzip fordert offen dokumentierte, öffentlich prüfbare Algorithmen - Sicherheit entsteht allein durch den geheimen Schlüssel."},
        {"cat": CAT_SEC, "q": "Was ist der wesentliche Sicherheitsvorteil von WPA3 gegenüber WPA2 bei WLAN?",
         "options": ["Individuelle Verschlüsselung pro Verbindung (Forward Secrecy) und besserer Schutz gegen Offline-Wörterbuchangriffe", "WPA3 benötigt kein Passwort mehr", "WPA3 funktioniert nur mit 5-GHz-WLAN", "WPA3 verzichtet komplett auf Verschlüsselung"],
         "a": "Individuelle Verschlüsselung pro Verbindung (Forward Secrecy) und besserer Schutz gegen Offline-Wörterbuchangriffe",
         "exp": "WPA3 nutzt SAE (Simultaneous Authentication of Equals) und schützt so besser gegen Brute-Force- und Wörterbuchangriffe auf das Passwort."},
        {"cat": CAT_SEC, "q": "Was ist ein Honeypot in der IT-Sicherheit?",
         "options": ["Ein absichtlich verwundbar aufgestelltes System, um Angreifer anzulocken und zu beobachten", "Ein Passwort-Tresor für Administratoren", "Ein besonders stark abgesichertes Produktivsystem", "Ein Verschlüsselungsverfahren für Datenbanken"],
         "a": "Ein absichtlich verwundbar aufgestelltes System, um Angreifer anzulocken und zu beobachten",
         "exp": "Ein Honeypot dient als Köder, um Angriffsmuster zu analysieren und Angreifer vom eigentlichen Produktivsystem abzulenken."},
        {"cat": CAT_SEC, "q": "Wodurch lässt sich ein Brute-Force-Angriff auf Login-Formulare wirksam erschweren?",
         "options": ["Kontosperrung/Verzögerung nach mehreren Fehlversuchen und 2FA", "Kürzere Passwörter erlauben", "Login-Versuche unbegrenzt und ohne Verzögerung zulassen", "Auf Verschlüsselung der Übertragung verzichten"],
         "a": "Kontosperrung/Verzögerung nach mehreren Fehlversuchen und 2FA",
         "exp": "Rate-Limiting, temporäre Sperren und Zwei-Faktor-Authentifizierung erschweren automatisiertes Durchprobieren von Passwörtern erheblich."},
        {"cat": CAT_SEC, "q": "Was passiert bei einer SQL-Injection?",
         "options": ["Ein Angreifer schleust über ungeprüfte Eingabefelder eigenen SQL-Code in eine Datenbankabfrage ein", "Ein Angreifer überflutet die Datenbank mit Anfragen (DoS)", "Ein Angreifer verschlüsselt die komplette Datenbank", "Ein Angreifer fälscht die IP-Adresse des Datenbankservers"],
         "a": "Ein Angreifer schleust über ungeprüfte Eingabefelder eigenen SQL-Code in eine Datenbankabfrage ein",
         "exp": "SQL-Injection nutzt fehlende Eingabevalidierung aus, um eigene SQL-Befehle auszuführen - Prepared Statements schützen wirksam davor."},
        {"cat": CAT_SEC, "q": "Was beschreibt Cross-Site-Scripting (XSS)?",
         "options": ["Einschleusen von schädlichem Skript-Code in Webseiten, der im Browser anderer Nutzer ausgeführt wird", "Ein Verfahren zum Testen der Ladezeit einer Webseite", "Ein Protokoll zur Übertragung von Cookies", "Eine Methode zur Verschlüsselung von Formulardaten"],
         "a": "Einschleusen von schädlichem Skript-Code in Webseiten, der im Browser anderer Nutzer ausgeführt wird",
         "exp": "XSS nutzt unzureichend gefilterte Nutzereingaben, um Skriptcode im Kontext einer vertrauenswürdigen Webseite bei anderen Besuchern auszuführen."},
        {"cat": CAT_SEC, "q": "Wofür wird Sandboxing in der IT-Sicherheit eingesetzt?",
         "options": ["Ausführung potenziell unsicherer Programme in einer isolierten Umgebung ohne Zugriff auf das restliche System", "Verschlüsselung von Datenbankinhalten", "Automatisches Erstellen von Backups", "Physische Absicherung von Serverräumen"],
         "a": "Ausführung potenziell unsicherer Programme in einer isolierten Umgebung ohne Zugriff auf das restliche System",
         "exp": "Eine Sandbox kapselt Programme ab, sodass mögliche Schadwirkungen das Host-System nicht beeinträchtigen können."},
        {"cat": CAT_SEC, "q": "Was ist der Zweck des TLS-Handshakes zu Beginn einer HTTPS-Verbindung?",
         "options": ["Aushandeln der Verschlüsselungsparameter und Authentifizierung des Servers per Zertifikat", "Übertragung der eigentlichen Nutzdaten unverschlüsselt", "Löschen alter Sitzungsdaten auf dem Server", "Feststellen der physischen Entfernung zum Server"],
         "a": "Aushandeln der Verschlüsselungsparameter und Authentifizierung des Servers per Zertifikat",
         "exp": "Im TLS-Handshake einigen sich Client und Server auf Verschlüsselungsverfahren und Sitzungsschlüssel, der Server weist sich mit seinem Zertifikat aus."},
        {"cat": CAT_SEC, "q": "Wozu dient eine digitale Signatur?",
         "options": ["Nachweis der Authentizität und Integrität eines Dokuments durch den privaten Schlüssel des Absenders", "Verschlüsselung des gesamten Dokumentinhalts", "Komprimierung großer Dateianhänge", "Automatische Übersetzung von Dokumenten"],
         "a": "Nachweis der Authentizität und Integrität eines Dokuments durch den privaten Schlüssel des Absenders",
         "exp": "Eine digitale Signatur wird mit dem privaten Schlüssel des Absenders erstellt und mit dessen öffentlichem Schlüssel überprüft - sie bestätigt Herkunft und Unverändertheit."},
        {"cat": CAT_SEC, "q": "Was ist das Ziel des IT-Grundschutzes nach BSI?",
         "options": ["Ein methodisches Vorgehen zur Etablierung eines angemessenen Sicherheitsniveaus in Organisationen", "Eine Vorschrift ausschließlich für Bundesbehörden ohne Praxisrelevanz für Unternehmen", "Ein reines Antivirenprogramm", "Ein Verschlüsselungsstandard für E-Mails"],
         "a": "Ein methodisches Vorgehen zur Etablierung eines angemessenen Sicherheitsniveaus in Organisationen",
         "exp": "Der BSI-IT-Grundschutz liefert standardisierte Methoden und Bausteine, um Informationssicherheit systematisch zu planen, umzusetzen und zu prüfen."},
        {"cat": CAT_SEC, "q": "Welchen Zweck erfüllen regelmäßige Security-Awareness-Schulungen?",
         "options": ["Mitarbeiter für Gefahren wie Phishing und Social Engineering sensibilisieren", "Ausschließlich technische Firewalls konfigurieren", "Passwörter der Mitarbeiter zentral verwalten", "Hardware-Inventuren durchführen"],
         "a": "Mitarbeiter für Gefahren wie Phishing und Social Engineering sensibilisieren",
         "exp": "Da viele Angriffe auf den 'Faktor Mensch' zielen, reduzieren Awareness-Schulungen das Risiko erfolgreicher Social-Engineering-Angriffe deutlich."},
        {"cat": CAT_SEC, "q": "Was bedeutet ein 'Air Gap' im Backup-Konzept?",
         "options": ["Mindestens eine Sicherungskopie ist physisch/logisch komplett vom Netzwerk getrennt", "Backups werden ausschließlich in der Cloud gespeichert", "Backups laufen ohne jede Verschlüsselung", "Es wird auf Backups vollständig verzichtet"],
         "a": "Mindestens eine Sicherungskopie ist physisch/logisch komplett vom Netzwerk getrennt",
         "exp": "Ein Air Gap schützt Backups z.B. vor Ransomware, da eine getrennte Kopie von einem Netzwerkangriff nicht erreicht werden kann."},
        {"cat": CAT_SEC, "q": "Was ist ein Rootkit?",
         "options": ["Schadsoftware, die sich tief im System versteckt und ihre Präsenz sowie Aktivitäten verschleiert", "Ein Werkzeug zur Systemadministration mit Root-Rechten", "Ein Verfahren zur Verschlüsselung von Root-Verzeichnissen", "Ein Backup-Tool für Linux-Systeme"],
         "a": "Schadsoftware, die sich tief im System versteckt und ihre Präsenz sowie Aktivitäten verschleiert",
         "exp": "Rootkits manipulieren oft das Betriebssystem selbst, um Erkennung durch Antivirenprogramme oder Administratoren zu vermeiden."},
        {"cat": CAT_SEC, "q": "Was ist ein Keylogger?",
         "options": ["Schadsoftware oder Hardware, die Tastatureingaben protokolliert, um z.B. Passwörter abzugreifen", "Ein Programm zur Protokollierung von Serverauslastung", "Ein Tool zur Verwaltung von Verschlüsselungsschlüsseln", "Ein Protokoll zur Fernwartung von Systemen"],
         "a": "Schadsoftware oder Hardware, die Tastatureingaben protokolliert, um z.B. Passwörter abzugreifen",
         "exp": "Keylogger zeichnen Tastatureingaben mit, um vertrauliche Informationen wie Zugangsdaten unbemerkt auszuspähen."},
        {"cat": CAT_SEC, "q": "Was unterscheidet eine Paketfilter-Firewall von einer Application-Layer-Firewall (Proxy-Firewall)?",
         "options": ["Paketfilter prüft nur Header-Informationen, Application-Layer-Firewall analysiert den Inhalt auf Anwendungsebene", "Beide arbeiten identisch auf Schicht 7", "Paketfilter kann keine IP-Adressen filtern", "Application-Layer-Firewalls filtern nur E-Mails"],
         "a": "Paketfilter prüft nur Header-Informationen, Application-Layer-Firewall analysiert den Inhalt auf Anwendungsebene",
         "exp": "Application-Layer-Firewalls (Proxies) können den Inhalt von Anwendungsprotokollen (z.B. HTTP) tiefergehend prüfen als einfache Paketfilter."},

        # --- Systeme, RAID & Hardware -------------------------------------
        {"cat": CAT_SYS, "q": "Welches RAID-Level bietet Spiegelung ohne Parität auf mindestens 2 Platten?",
         "options": ["RAID 1", "RAID 0", "RAID 5", "RAID 6"], "a": "RAID 1",
         "exp": "RAID 1 spiegelt alle Daten 1:1 auf mindestens zwei Festplatten."},
        {"cat": CAT_SYS, "q": "Wie viele Festplatten können bei einem RAID 6 gleichzeitig ohne Datenverlust ausfallen?",
         "options": ["2 Festplatten", "1 Festplatte", "3 Festplatten", "Keine"], "a": "2 Festplatten",
         "exp": "RAID 6 nutzt duale Parität und verkraftet den Ausfall von bis zu 2 Platten."},
        {"cat": CAT_SYS, "q": "Was versteht man unter einem Hypervisor Typ 1 (Bare-Metal)?",
         "options": ["Läuft direkt auf der Hardware ohne zugrunde liegendes Host-Betriebssystem", "Benötigt ein installiertes Windows/Linux als Host", "Ist eine reine Softwarelösung für Docker-Container", "Wird ausschließlich in Webbrowsern ausgeführt"],
         "a": "Läuft direkt auf der Hardware ohne zugrunde liegendes Host-Betriebssystem",
         "exp": "Typ-1-Hypervisoren (z.B. VMware ESXi, Proxmox VE) installieren direkt auf der nackten Hardware."},
        {"cat": CAT_SYS, "q": "Welches Protokoll verbindet Speichernetzwerke (SAN) über IP-Netzwerke?",
         "options": ["iSCSI", "Fibre Channel", "NFS", "SMB"], "a": "iSCSI",
         "exp": "iSCSI kapselt SCSI-Befehle in TCP/IP-Paketen für kostengünstige SAN-Anbindungen."},
        {"cat": CAT_SYS, "q": "Wofür steht die Abkürzung NVMe?",
         "options": ["Non-Volatile Memory Express", "New Virtual Memory Engine", "Network Video Management Extension", "Non-Virtual Module Environment"],
         "a": "Non-Volatile Memory Express",
         "exp": "NVMe ist ein Protokoll für den schnellen Zugriff auf SSDs über den PCIe-Bus."},
        {"cat": CAT_SYS, "q": "Was ist der Vorteil von RAID 10 gegenüber RAID 5?",
         "options": ["Deutlich bessere Schreibperformance und schnellerer Rebuild bei Ausfall", "Geringerer Speicherbedarf pro Festplatte", "Weniger benötigte Festplatten", "Höhere Kapazitätseffizienz"],
         "a": "Deutlich bessere Schreibperformance und schnellerer Rebuild bei Ausfall",
         "exp": "RAID 10 (Striping + Mirroring) bietet sehr gute Schreib-/Leseperformance und einen schnellen, unkomplizierten Rebuild, kostet aber 50% Kapazität."},
        {"cat": CAT_SYS, "q": "Was ist ein Cluster im Serverkontext?",
         "options": ["Ein Verbund mehrerer Server, die gemeinsam einen Dienst hochverfügbar bereitstellen", "Eine RAID-Konfiguration", "Ein einzelner Hochleistungsserver", "Ein Backup-Medium"],
         "a": "Ein Verbund mehrerer Server, die gemeinsam einen Dienst hochverfügbar bereitstellen",
         "exp": "Ein Cluster bündelt mehrere Server, um Ausfallsicherheit (Failover) und/oder Lastverteilung zu erreichen."},
        {"cat": CAT_SYS, "q": "Was bedeutet Hot-Swap bei Festplatten?",
         "options": ["Austausch defekter Laufwerke im laufenden Betrieb ohne Herunterfahren", "Automatisches Klonen von Laufwerken", "Verschlüsselung im laufenden Betrieb", "Beschleunigtes Booten des Systems"],
         "a": "Austausch defekter Laufwerke im laufenden Betrieb ohne Herunterfahren",
         "exp": "Hot-Swap-fähige Laufwerke können bei laufendem System getauscht werden, ohne den Betrieb zu unterbrechen."},
        {"cat": CAT_SYS, "q": "Was unterscheidet Cold Site, Warm Site und Hot Site im Notfallmanagement?",
         "options": ["Sie unterscheiden sich im Grad der Betriebsbereitschaft eines Ausweich-Rechenzentrums", "Sie beschreiben unterschiedliche RAID-Level", "Sie beschreiben die Temperatur im Serverraum", "Sie sind Synonyme für dasselbe Konzept"],
         "a": "Sie unterscheiden sich im Grad der Betriebsbereitschaft eines Ausweich-Rechenzentrums",
         "exp": "Cold Site (nur Infrastruktur), Warm Site (teilweise vorbereitet) und Hot Site (sofort einsatzbereit) unterscheiden sich in Wiederanlaufzeit und Kosten."},
        {"cat": CAT_SYS, "q": "Wofür steht IOPS bei Speichermedien?",
         "options": ["Input/Output Operations Per Second", "Internal Operating Power Supply", "Input Output Protocol Standard", "Integrated Object Processing System"],
         "a": "Input/Output Operations Per Second",
         "exp": "IOPS misst, wie viele Lese-/Schreiboperationen ein Speichermedium pro Sekunde verarbeiten kann - eine wichtige Kenngröße besonders bei SSDs und Datenbanken."},
        {"cat": CAT_SYS, "q": "Wie viele Festplatten werden für RAID 5 mindestens benötigt?",
         "options": ["3", "2", "4", "6"], "a": "3",
         "exp": "RAID 5 (Striping mit verteilter Parität) benötigt mindestens 3 Festplatten."},
        {"cat": CAT_SYS, "q": "Wie viele Festplatten werden für RAID 6 mindestens benötigt?",
         "options": ["4", "2", "3", "5"], "a": "4",
         "exp": "RAID 6 mit doppelter, verteilter Parität benötigt mindestens 4 Festplatten."},
        {"cat": CAT_SYS, "q": "Was ist beim Aufbau von RAID 10 charakteristisch?",
         "options": ["Kombination aus Spiegelung (RAID 1) und Striping (RAID 0) über mindestens 4 Platten", "Nur eine einzige Parity-Platte für alle Daten", "Reine Spiegelung ohne Striping auf 2 Platten", "Striping ohne jede Redundanz"],
         "a": "Kombination aus Spiegelung (RAID 1) und Striping (RAID 0) über mindestens 4 Platten",
         "exp": "RAID 10 spiegelt zunächst Plattenpaare (RAID 1) und verteilt die Daten dann per Striping (RAID 0) darüber - hohe Performance und Ausfallsicherheit."},
        {"cat": CAT_SYS, "q": "Wofür steht die Abkürzung SATA bei Festplattenschnittstellen?",
         "options": ["Serial Advanced Technology Attachment", "System Area Transfer Adapter", "Storage Access Transmission Architecture", "Serial Array Technology Access"],
         "a": "Serial Advanced Technology Attachment",
         "exp": "SATA ist eine serielle Schnittstelle zum Anschluss von Festplatten und SSDs an das Mainboard."},
        {"cat": CAT_SYS, "q": "Was ist ein Kaltstart (Cold Boot) gegenüber einem Warmstart (Reboot)?",
         "options": ["Vollständiges Aus- und Wiedereinschalten der Stromversorgung, statt nur eines Neustarts der Software", "Beide Begriffe beschreiben denselben Vorgang", "Ein Kaltstart betrifft nur die Netzwerkkarte", "Ein Warmstart löscht immer alle Daten"],
         "a": "Vollständiges Aus- und Wiedereinschalten der Stromversorgung, statt nur eines Neustarts der Software",
         "exp": "Ein Kaltstart trennt das System vollständig von der Stromversorgung, während ein Warmstart nur das Betriebssystem neu startet, ohne die Hardware auszuschalten."},
        {"cat": CAT_SYS, "q": "Was ist der Hauptvorteil von NVMe-SSDs gegenüber klassischen SATA-SSDs?",
         "options": ["Deutlich höhere Geschwindigkeit durch direkte Anbindung über PCIe", "NVMe-SSDs sind grundsätzlich günstiger", "NVMe-SSDs benötigen keine Stromversorgung", "SATA-SSDs bieten mehr parallele Warteschlangen als NVMe"],
         "a": "Deutlich höhere Geschwindigkeit durch direkte Anbindung über PCIe",
         "exp": "NVMe nutzt den schnelleren PCIe-Bus direkt und viele parallele Warteschlangen, wodurch deutlich höhere Datenraten als über SATA möglich sind."},
        {"cat": CAT_SYS, "q": "Wofür wird ein KVM-Switch typischerweise verwendet?",
         "options": ["Steuerung mehrerer Rechner mit nur einer Tastatur, Maus und einem Monitor", "Virtualisierung mehrerer Betriebssysteme auf einem Host", "Verwaltung von RAID-Arrays über das Netzwerk", "Verschlüsselung von Tastatureingaben"],
         "a": "Steuerung mehrerer Rechner mit nur einer Tastatur, Maus und einem Monitor",
         "exp": "Ein KVM-Switch (Keyboard, Video, Mouse) erlaubt das Umschalten zwischen mehreren angeschlossenen Rechnern mit nur einem Satz Eingabegeräte und Monitor."},
        {"cat": CAT_SYS, "q": "Was beschreibt Redundanz allgemein im IT-Systembetrieb?",
         "options": ["Das Vorhandensein zusätzlicher, funktional gleicher Komponenten, um Ausfälle abzufedern", "Die vollständige Auslastung eines Systems", "Das Löschen doppelt vorhandener Dateien", "Ein Backup-Verfahren ohne Wiederherstellungsmöglichkeit"],
         "a": "Das Vorhandensein zusätzlicher, funktional gleicher Komponenten, um Ausfälle abzufedern",
         "exp": "Redundante Komponenten (z.B. Netzteile, RAID, Cluster-Knoten) übernehmen die Funktion, wenn eine andere Komponente ausfällt, und erhöhen so die Verfügbarkeit."},
        {"cat": CAT_SYS, "q": "Was ist eine typische Aufgabe von Puppet, Ansible oder ähnlichen Tools im Systembetrieb?",
         "options": ["Automatisierte, reproduzierbare Konfiguration von Servern (Configuration Management)", "Erstellung von RAID-Arrays auf Hardwareebene", "Physische Verkabelung von Netzwerkports", "Verschlüsselung von Backup-Medien"],
         "a": "Automatisierte, reproduzierbare Konfiguration von Servern (Configuration Management)",
         "exp": "Configuration-Management-Tools automatisieren das Aufsetzen und Konfigurieren vieler Server konsistent nach definierten Vorgaben (Infrastructure as Code)."},
        {"cat": CAT_SYS, "q": "Was unterscheidet eine differentielle Sicherung von einer inkrementellen Sicherung?",
         "options": ["Differentiell sichert alle Änderungen seit der letzten Vollsicherung, inkrementell nur seit der letzten Sicherung jeder Art", "Beide Verfahren sind identisch", "Differentiell sichert nur einmal im Monat", "Inkrementell sichert immer den kompletten Datenbestand"],
         "a": "Differentiell sichert alle Änderungen seit der letzten Vollsicherung, inkrementell nur seit der letzten Sicherung jeder Art",
         "exp": "Differentielle Backups wachsen mit der Zeit an (bis zur nächsten Vollsicherung), inkrementelle Backups bleiben klein, benötigen bei der Wiederherstellung aber alle Zwischenschritte."},
        {"cat": CAT_SYS, "q": "Wofür steht die Abkürzung RAID?",
         "options": ["Redundant Array of Independent Disks", "Rapid Access Internal Drive", "Remote Attached Internal Disk", "Redundant Access to Internal Data"],
         "a": "Redundant Array of Independent Disks",
         "exp": "RAID beschreibt den Verbund mehrerer physischer Festplatten zu einem logischen Laufwerk zur Erhöhung von Performance und/oder Ausfallsicherheit."},
        {"cat": CAT_SYS, "q": "Was ist der Zweck eines Betriebssystem-Images (z.B. per Clonezilla) in der Systemadministration?",
         "options": ["Schnelle, identische Wiederherstellung oder Verteilung eines vorkonfigurierten Systemzustands", "Verschlüsselung des gesamten Netzwerkverkehrs", "Automatische RAID-Konfiguration ohne Controller", "Überwachung der CPU-Temperatur in Echtzeit"],
         "a": "Schnelle, identische Wiederherstellung oder Verteilung eines vorkonfigurierten Systemzustands",
         "exp": "Ein Image speichert den kompletten Zustand eines Systems und ermöglicht so schnelles Rollout gleichartiger Arbeitsplätze oder Server."},
        {"cat": CAT_SYS, "q": "Wofür steht die Abkürzung DAS bei Speichersystemen?",
         "options": ["Direct Attached Storage", "Data Access Server", "Dynamic Allocation Storage", "Distributed Application Storage"],
         "a": "Direct Attached Storage",
         "exp": "DAS bezeichnet Speicher, der direkt (ohne Netzwerk) an einen einzelnen Server angeschlossen ist, im Gegensatz zu NAS oder SAN."},
        {"cat": CAT_SYS, "q": "Was ist der Vorteil eines Blade-Servers gegenüber klassischen Rack-Servern?",
         "options": ["Höhere Packungsdichte durch gemeinsame Nutzung von Stromversorgung, Kühlung und Verkabelung im Chassis", "Blade-Server benötigen keinerlei Stromversorgung", "Blade-Server sind ausschließlich für Heimanwender gedacht", "Blade-Server können kein RAID nutzen"],
         "a": "Höhere Packungsdichte durch gemeinsame Nutzung von Stromversorgung, Kühlung und Verkabelung im Chassis",
         "exp": "Blade-Server teilen sich im Blade-Chassis gemeinsame Infrastruktur, was Platz, Verkabelung und Energieeffizienz im Rechenzentrum verbessert."},

        # --- Wirtschaft & Prozesse ----------------------------------------
        {"cat": CAT_BIZ, "q": "Wofür steht die Abkürzung TCO?",
         "options": ["Total Cost of Ownership", "Technical Control Operations", "Total Capacity Optimization", "Time Critical Output"],
         "a": "Total Cost of Ownership",
         "exp": "TCO erfasst alle Anschaffungs-, Betriebs- und Entsorgungskosten einer IT-Investition."},
        {"cat": CAT_BIZ, "q": "Was ist ein SLA (Service Level Agreement)?",
         "options": ["Ein Vertrag zur Festlegung vereinbarter IT-Dienstleistungsqualitäten und Zeiten", "Ein Lizenzvertrag für Microsoft-Produkte", "Eine Sicherheitsvorschrift des BSI", "Ein Protokoll zur Serverüberwachung"],
         "a": "Ein Vertrag zur Festlegung vereinbarter IT-Dienstleistungsqualitäten und Zeiten",
         "exp": "Ein SLA regelt Qualitätskriterien, Verfügbarkeiten und Reaktionszeiten zwischen Dienstleister und Kunde."},
        {"cat": CAT_BIZ, "q": "Welche Phase gehört zum ITIL-Service-Lebenszyklus?",
         "options": ["Service Operation", "Code Deployment", "Hardware Assembly", "Database Indexing"],
         "a": "Service Operation",
         "exp": "Service Operation sichert den laufenden Betrieb von IT-Services nach ITIL."},
        {"cat": CAT_BIZ, "q": "Was bedeutet RPO (Recovery Point Objective)?",
         "options": ["Maximal tolerierbarer Datenverlust ausgedrückt in Zeit", "Zeitraum bis zur vollständigen Wiederherstellung des Dienstes", "Maximale Ausfallzeit im Jahr", "Prozentuale Verfügbarkeit des Servers"],
         "a": "Maximal tolerierbarer Datenverlust ausgedrückt in Zeit",
         "exp": "RPO bestimmt, wie alt der letzte gesicherte Datenstand im Katastrophenfall maximal sein darf."},
        {"cat": CAT_BIZ, "q": "Was bedeutet RTO (Recovery Time Objective)?",
         "options": ["Maximal tolerierbare Ausfallzeit bis zur Wiederherstellung", "Maximal tolerierbarer Datenverlust", "Zeitpunkt der letzten Sicherung", "Durchschnittliche Reparaturzeit eines Servers"],
         "a": "Maximal tolerierbare Ausfallzeit bis zur Wiederherstellung",
         "exp": "RTO gibt vor, wie lange ein Systemausfall maximal dauern darf, bevor der Dienst wiederhergestellt sein muss."},
        {"cat": CAT_BIZ, "q": "Was beschreibt das Vier-Augen-Prinzip?",
         "options": ["Wichtige Entscheidungen/Vorgänge werden von mindestens zwei Personen geprüft und freigegeben", "Zwei Bildschirme pro Arbeitsplatz", "Doppelte Datensicherung", "Zwei Administratoren pro Server"],
         "a": "Wichtige Entscheidungen/Vorgänge werden von mindestens zwei Personen geprüft und freigegeben",
         "exp": "Das Vier-Augen-Prinzip reduziert Fehler und Missbrauch, indem kritische Vorgänge von einer zweiten Person kontrolliert werden."},
        {"cat": CAT_BIZ, "q": "Was ist der Unterschied zwischen OPEX und CAPEX?",
         "options": ["OPEX sind laufende Betriebskosten, CAPEX sind Investitionsausgaben", "OPEX ist für Hardware, CAPEX für Software", "Beide Begriffe sind identisch", "CAPEX bezeichnet nur Personalkosten"],
         "a": "OPEX sind laufende Betriebskosten, CAPEX sind Investitionsausgaben",
         "exp": "CAPEX (Capital Expenditure) sind einmalige Investitionen, OPEX (Operational Expenditure) laufende Betriebskosten - relevant z.B. bei Cloud gegenüber eigener Hardware."},
        {"cat": CAT_BIZ, "q": "Was ist ein Kanban-Board im Projektmanagement?",
         "options": ["Eine visuelle Tafel zur Darstellung von Arbeitsschritten und Aufgabenstatus", "Ein Netzwerkdiagramm", "Ein Backup-Zeitplan", "Ein Sicherheitskonzept"],
         "a": "Eine visuelle Tafel zur Darstellung von Arbeitsschritten und Aufgabenstatus",
         "exp": "Kanban visualisiert den Arbeitsfluss in Spalten (z.B. To-Do, In Arbeit, Fertig) zur Steuerung von Arbeitslast und Durchlaufzeit."},
        {"cat": CAT_BIZ, "q": "Was regelt ein NDA (Non-Disclosure Agreement)?",
         "options": ["Vertrauliche Behandlung von Informationen zwischen Vertragsparteien", "Die Nutzung von Netzwerkressourcen", "Die Haftung bei Datenverlust", "Die Vergabe von Softwarelizenzen"],
         "a": "Vertrauliche Behandlung von Informationen zwischen Vertragsparteien",
         "exp": "Ein NDA (Geheimhaltungsvereinbarung) verpflichtet Vertragsparteien zur Vertraulichkeit über ausgetauschte Informationen."},
        {"cat": CAT_BIZ, "q": "Was ist der Zweck einer Risikoanalyse im IT-Projekt?",
         "options": ["Systematisches Identifizieren, Bewerten und Priorisieren potenzieller Risiken", "Messen der Serverauslastung", "Erstellen des Netzwerkplans", "Dokumentation der Codequalität"],
         "a": "Systematisches Identifizieren, Bewerten und Priorisieren potenzieller Risiken",
         "exp": "Die Risikoanalyse identifiziert mögliche Gefahren für ein Projekt oder System und bewertet Eintrittswahrscheinlichkeit und Auswirkung."},
        {"cat": CAT_BIZ, "q": "Was regelt das Allgemeine Gleichbehandlungsgesetz (AGG) im Betrieb?",
         "options": ["Schutz vor Diskriminierung u.a. wegen Geschlecht, Herkunft, Religion oder Behinderung", "Die Höhe des Mindestlohns", "Die Kündigungsfristen von Arbeitsverträgen", "Die Aufbewahrungsfristen von Geschäftsunterlagen"],
         "a": "Schutz vor Diskriminierung u.a. wegen Geschlecht, Herkunft, Religion oder Behinderung",
         "exp": "Das AGG soll Benachteiligungen aus den im Gesetz genannten Gründen im Arbeitsleben verhindern oder beseitigen."},
        {"cat": CAT_BIZ, "q": "Was ist der Unterschied zwischen Brutto- und Nettopreis?",
         "options": ["Der Bruttopreis enthält die Umsatzsteuer, der Nettopreis nicht", "Beide Preise sind identisch", "Der Nettopreis enthält immer Versandkosten", "Der Bruttopreis gilt nur für Geschäftskunden"],
         "a": "Der Bruttopreis enthält die Umsatzsteuer, der Nettopreis nicht",
         "exp": "Nettopreis + Umsatzsteuer (i.d.R. 19% oder 7%) ergibt den Bruttopreis, den Endkunden zahlen."},
        {"cat": CAT_BIZ, "q": "Was ist ein Pflichtenheft im Projektkontext?",
         "options": ["Die Beschreibung, WIE der Auftragnehmer die Anforderungen des Kunden konkret umsetzt", "Eine reine Aufgabenliste für Auszubildende", "Ein Vertrag zur Geheimhaltung", "Ein Dokument zur Gehaltsabrechnung"],
         "a": "Die Beschreibung, WIE der Auftragnehmer die Anforderungen des Kunden konkret umsetzt",
         "exp": "Während das Lastenheft die Kundenanforderungen (WAS) beschreibt, legt das Pflichtenheft die technische Umsetzung (WIE) durch den Auftragnehmer fest."},
        {"cat": CAT_BIZ, "q": "Was versteht man unter dem Kontinuierlichen Verbesserungsprozess (KVP)?",
         "options": ["Schrittweise, fortlaufende Optimierung von Arbeitsabläufen durch alle Mitarbeiter", "Eine einmalige, radikale Prozessumstellung", "Ein IT-Sicherheitszertifikat", "Ein Verfahren zur RAID-Konfiguration"],
         "a": "Schrittweise, fortlaufende Optimierung von Arbeitsabläufen durch alle Mitarbeiter",
         "exp": "KVP (auch Kaizen) zielt auf viele kleine, dauerhafte Verbesserungen statt einmaliger großer Umbrüche."},
        {"cat": CAT_BIZ, "q": "Was ist ein Lastenheft im Projektkontext?",
         "options": ["Beschreibung der Anforderungen und Ziele aus Sicht des Auftraggebers", "Eine Rechnung über erbrachte Leistungen", "Ein technisches Konzept des Auftragnehmers", "Ein Arbeitszeitnachweis"],
         "a": "Beschreibung der Anforderungen und Ziele aus Sicht des Auftraggebers",
         "exp": "Das Lastenheft beschreibt aus Kundensicht, WAS erreicht werden soll, bevor der Auftragnehmer im Pflichtenheft das WIE festlegt."},
        {"cat": CAT_BIZ, "q": "Was misst der Return on Investment (ROI) genau?",
         "options": ["Das Verhältnis von erzieltem Gewinn zum eingesetzten Kapital, meist in Prozent", "Die absolute Höhe des Umsatzes", "Die Anzahl verkaufter Einheiten pro Monat", "Die Höhe der jährlichen Lohnkosten"],
         "a": "Das Verhältnis von erzieltem Gewinn zum eingesetzten Kapital, meist in Prozent",
         "exp": "ROI = Gewinn / eingesetztes Kapital x 100 - eine zentrale Kennzahl zur Bewertung der Rentabilität einer Investition."},
        {"cat": CAT_BIZ, "q": "Was regelt ein Rahmenvertrag zwischen Unternehmen und Lieferant?",
         "options": ["Allgemeine, langfristige Konditionen (Preise, Lieferzeiten) für wiederkehrende Einzelbestellungen", "Nur eine einmalige Bestellung ohne Folgeverpflichtung", "Ausschließlich die Kündigung von Mitarbeitern", "Die technische Konfiguration von Servern"],
         "a": "Allgemeine, langfristige Konditionen (Preise, Lieferzeiten) für wiederkehrende Einzelbestellungen",
         "exp": "Ein Rahmenvertrag legt wiederkehrend genutzte Konditionen fest, einzelne Bestellungen (Abrufe) erfolgen dann jeweils darunter."},
        {"cat": CAT_BIZ, "q": "Was ist eine Win-Win-Situation in einer Verhandlung?",
         "options": ["Beide Vertragsparteien erzielen ein für sich vorteilhaftes Ergebnis", "Nur eine Partei profitiert vollständig", "Der Vertrag wird ohne Einigung abgebrochen", "Ein Rechtsstreit vor Gericht wird gewonnen"],
         "a": "Beide Vertragsparteien erzielen ein für sich vorteilhaftes Ergebnis",
         "exp": "In einer Win-Win-Verhandlung profitieren idealerweise beide Seiten, was die Basis für eine langfristige Geschäftsbeziehung stärkt."},
        {"cat": CAT_BIZ, "q": "Was beschreibt der Begriff Outsourcing?",
         "options": ["Auslagerung von Unternehmensfunktionen oder IT-Dienstleistungen an externe Dienstleister", "Einstellung neuer interner Mitarbeiter", "Interne Umstrukturierung ohne externe Beteiligung", "Verkauf von Firmenanteilen an der Börse"],
         "a": "Auslagerung von Unternehmensfunktionen oder IT-Dienstleistungen an externe Dienstleister",
         "exp": "Beim Outsourcing werden bestimmte Aufgaben (z.B. IT-Support, Hosting) bewusst an spezialisierte externe Anbieter vergeben."},
        {"cat": CAT_BIZ, "q": "Was ist der Unterschied zwischen Cross-Selling und Up-Selling?",
         "options": ["Cross-Selling bietet ergänzende Produkte an, Up-Selling ein höherwertiges Produkt derselben Kategorie", "Beide Begriffe bezeichnen denselben Vorgang", "Cross-Selling gilt nur für digitale Produkte", "Up-Selling senkt immer den Verkaufspreis"],
         "a": "Cross-Selling bietet ergänzende Produkte an, Up-Selling ein höherwertiges Produkt derselben Kategorie",
         "exp": "Cross-Selling ('dazu passt auch...') und Up-Selling ('das bessere Modell...') sind gängige Verkaufsstrategien zur Umsatzsteigerung."},
        {"cat": CAT_BIZ, "q": "Was ist eine Stärken-Schwächen-Analyse (SWOT) im Kern?",
         "options": ["Bewertung interner Stärken/Schwächen sowie externer Chancen/Risiken eines Unternehmens oder Projekts", "Eine reine Finanzkennzahl zur Liquidität", "Ein Verfahren zur Netzwerksicherheit", "Eine Methode zur RAID-Konfiguration"],
         "a": "Bewertung interner Stärken/Schwächen sowie externer Chancen/Risiken eines Unternehmens oder Projekts",
         "exp": "SWOT steht für Strengths, Weaknesses, Opportunities, Threats und dient als strukturiertes Werkzeug der strategischen Planung."},
        {"cat": CAT_BIZ, "q": "Wofür steht die Abkürzung KPI?",
         "options": ["Key Performance Indicator", "Key Process Interface", "Kritischer Prozess-Indikator (nur deutsch gebräuchlich)", "Keyboard Performance Input"],
         "a": "Key Performance Indicator",
         "exp": "KPIs sind zentrale Kennzahlen zur Messung des Erfolgs oder Fortschritts gegenüber definierten Zielen."},
        {"cat": CAT_BIZ, "q": "Was ist der Zweck einer Ist-Analyse zu Beginn eines IT-Projekts?",
         "options": ["Erfassung des aktuellen Zustands (Systeme, Prozesse) als Grundlage für die weitere Planung", "Direktes Erstellen der Rechnung an den Kunden", "Festlegung des Projektendtermins ohne weitere Prüfung", "Abschluss des Projekts und Übergabe an den Kunden"],
         "a": "Erfassung des aktuellen Zustands (Systeme, Prozesse) als Grundlage für die weitere Planung",
         "exp": "Die Ist-Analyse dokumentiert den Ausgangszustand, bevor im Soll-Konzept die gewünschte Zielsituation geplant wird."},
        {"cat": CAT_BIZ, "q": "Was regelt eine Wartungsvereinbarung (Maintenance-Vertrag) typischerweise?",
         "options": ["Regelmäßige Pflege, Updates und Support für IT-Systeme gegen Entgelt", "Nur die einmalige Erstinstallation eines Systems", "Die Vergütung von Auszubildenden", "Die physische Sicherheit eines Rechenzentrums"],
         "a": "Regelmäßige Pflege, Updates und Support für IT-Systeme gegen Entgelt",
         "exp": "Wartungsverträge sichern dem Kunden laufende Betreuung, Updates und definierte Reaktionszeiten bei Problemen zu."},
        {"cat": CAT_BIZ, "q": "Was versteht man unter Stakeholdern eines Projekts?",
         "options": ["Alle Personen oder Gruppen mit einem Interesse am oder Einfluss auf das Projekt", "Ausschließlich die Geschäftsführung", "Nur externe Kunden", "Nur das Entwicklungsteam"],
         "a": "Alle Personen oder Gruppen mit einem Interesse am oder Einfluss auf das Projekt",
         "exp": "Stakeholder umfassen z.B. Auftraggeber, Nutzer, Management, Betriebsrat oder externe Partner - ihre Interessen sollten im Projektverlauf berücksichtigt werden."},
    ]

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

    return db


QUIZ_QUESTIONS = build_quiz_database()


# ============================================================================
#  LERNINHALTE: AP2-SZENARIEN
# ============================================================================

SZENARIEN = [
    {
        "title": "Subnetting & redundantes Routing",
        "cat": CAT_NET,
        "theme": "Subnetting & Routing",
        "text": "Ein neuer Standort erhält den Netzbereich 172.16.0.0/21.\n\n"
                "1. Bilden Sie passende Subnetze für Verwaltung, Produktion, DMZ und Punkt-zu-Punkt.\n"
                "2. Konfigurieren Sie redundantes Routing über eine Floating Static Route.",
        "solution": "Subnetze:\n"
                    "  - A (Verwaltung): 172.16.0.0/23\n"
                    "  - B (Produktion): 172.16.2.0/24\n"
                    "  - C (DMZ): 172.16.3.0/26\n"
                    "  - D (P2P): 172.16.3.64/30\n\n"
                    "Routing:\n"
                    "  - Primäre Route mit Administrative Distance 1\n"
                    "  - Backup-Route mit Administrative Distance 10 (Floating Static Route)",
    },
    {
        "title": "Ransomware-Vorfall & Incident Response",
        "cat": CAT_SEC,
        "theme": "IT-Sicherheit",
        "text": "Ein System wurde mit Ransomware infiziert (Dateiendung .crypto).\n\n"
                "1. Nennen Sie drei Sofortmaßnahmen nach BSI-Empfehlung.\n"
                "2. Begründen Sie den Einsatz hybrider Verschlüsselung durch die Angreifer.\n"
                "3. Welche Meldefrist gilt nach DSGVO?",
        "solution": "1. Netzwerk isolieren, Backups sichern und vom Netz trennen, Incident-Response-Team aktivieren.\n"
                    "2. AES verschlüsselt die Dateien schnell (symmetrisch), RSA schützt den AES-Schlüssel "
                    "(asymmetrisch) - so bleibt die Entschlüsselung ohne privaten Schlüssel unmöglich.\n"
                    "3. Meldung innerhalb von 72 Stunden an die zuständige Aufsichtsbehörde (Art. 33 DSGVO).",
    },
    {
        "title": "RAID-Ausfall & Wiederherstellung",
        "cat": CAT_SYS,
        "theme": "Storage & RAID",
        "text": "Ein Fileserver mit RAID 5 (6 Platten à 2 TB) meldet den Ausfall einer Festplatte.\n\n"
                "1. Ist der Datenbestand aktuell gefährdet? Begründen Sie.\n"
                "2. Welche Kapazität steht nach dem Rebuild mit einer neuen Platte zur Verfügung?\n"
                "3. Welches Risiko besteht während des Rebuilds und wie lässt es sich reduzieren?",
        "solution": "1. Noch kein Datenverlust, da RAID 5 einen Ausfall toleriert - das System läuft im "
                    "degraded mode ohne Redundanz.\n"
                    "2. Die Nutzkapazität bleibt bei (6 - 1) x 2 TB = 10 TB nach erfolgreichem Rebuild.\n"
                    "3. Während des Rebuilds besteht durch die hohe Last eine erhöhte Ausfallwahrscheinlichkeit "
                    "einer weiteren Platte - reduzierbar durch RAID 6 oder Hot-Spare-Platten.",
    },
    {
        "title": "VLAN-Konzept für ein Bürogebäude",
        "cat": CAT_NET,
        "theme": "Netzwerkdesign",
        "text": "Ein Unternehmen mit den Abteilungen Verwaltung, Entwicklung und Gäste-WLAN soll "
                "strukturiert vernetzt werden.\n\n"
                "1. Warum sollten die Bereiche in separate VLANs aufgeteilt werden?\n"
                "2. Was wird für die Kommunikation zwischen den VLANs benötigt?\n"
                "3. Welche Sicherheitsmaßnahme ist für das Gäste-WLAN besonders wichtig?",
        "solution": "1. VLANs trennen Broadcast-Domänen, erhöhen die Sicherheit durch Segmentierung und "
                    "erleichtern die Verwaltung unabhängig von der physischen Verkabelung.\n"
                    "2. Ein Layer-3-fähiges Gerät (Router oder Layer-3-Switch) mit Inter-VLAN-Routing.\n"
                    "3. Strikte Isolation des Gäste-VLANs vom internen Netz über eigene Firewall-Regeln, "
                    "damit Gäste keinen Zugriff auf interne Ressourcen erhalten.",
    },
    {
        "title": "Phishing-Angriff auf Mitarbeiter",
        "cat": CAT_SEC,
        "theme": "IT-Sicherheit",
        "text": "Mehrere Mitarbeiter haben eine gefälschte E-Mail erhalten, die zur Eingabe ihrer "
                "Zugangsdaten auf einer nachgebauten Login-Seite auffordert.\n\n"
                "1. Um welche Angriffsart handelt es sich?\n"
                "2. Welche drei Sofortmaßnahmen sollten ergriffen werden?\n"
                "3. Welche präventiven, organisatorischen Maßnahmen helfen langfristig?",
        "solution": "1. Phishing als Form des Social Engineering zum Diebstahl von Zugangsdaten.\n"
                    "2. Betroffene Passwörter sofort zurücksetzen, betroffene Konten auf Missbrauch prüfen, "
                    "IT-Sicherheitsteam informieren und alle Mitarbeiter warnen.\n"
                    "3. Regelmäßige Security-Awareness-Schulungen, simulierte Phishing-Tests, "
                    "Spam- und Phishing-Filter sowie 2FA für wichtige Konten.",
    },
    {
        "title": "Angebotsvergleich & TCO-Betrachtung",
        "cat": CAT_BIZ,
        "theme": "Wirtschaft & Beratung",
        "text": "Ein Kunde möchte zwischen zwei Serverangeboten wählen: Angebot A (günstiger Kaufpreis, "
                "hoher Stromverbrauch, kurze Garantie) und Angebot B (höherer Kaufpreis, energieeffizient, "
                "längere Garantie).\n\n"
                "1. Warum reicht der reine Anschaffungspreis für die Entscheidung nicht aus?\n"
                "2. Welche Kostenfaktoren gehören in eine TCO-Betrachtung?\n"
                "3. Welche Rolle spielt das Lastenheft des Kunden bei der Entscheidung?",
        "solution": "1. Der Anschaffungspreis bildet nur einen Teil der Gesamtkosten ab; Betrieb, Wartung "
                    "und Ausfallrisiken können langfristig stärker ins Gewicht fallen.\n"
                    "2. Anschaffung, Energie- und Kühlkosten, Wartung, Support, Ausfallzeiten, "
                    "Entsorgung beziehungsweise Restwert.\n"
                    "3. Das Lastenheft definiert die tatsächlichen Anforderungen des Kunden (Leistung, "
                    "Verfügbarkeit, Budget) und dient als objektive Entscheidungsgrundlage statt eines "
                    "reinen Preisvergleichs.",
    },
    {
        "title": "WAN-Anbindung mit Redundanz",
        "cat": CAT_NET,
        "theme": "Netzwerkdesign",
        "text": "Ein Unternehmen betreibt zwei Standorte und möchte diese redundant über zwei "
                "unterschiedliche Internetprovider koppeln.\n\n"
                "1. Welches Konzept ermöglicht automatisches Umschalten bei Ausfall einer Leitung?\n"
                "2. Welche Rolle spielt dabei die Administrative Distance (AD)?\n"
                "3. Welche kostengünstige Alternative zu einer MPLS-Standortkopplung gibt es?",
        "solution": "1. Floating Static Routes beziehungsweise dynamisches Routing mit Tracking ermöglichen "
                    "automatisches Failover zwischen den Leitungen.\n"
                    "2. Die Route mit der niedrigeren AD wird bevorzugt genutzt (Primärroute); die "
                    "Backup-Route mit höherer AD wird erst bei Ausfall der Primärroute aktiv.\n"
                    "3. Ein Site-to-Site-VPN über das öffentliche Internet als kostengünstige Alternative "
                    "zu dedizierten MPLS-Leitungen.",
    },
    {
        "title": "Backup-Konzept nach Ransomware-Vorfall",
        "cat": CAT_SEC,
        "theme": "IT-Sicherheit",
        "text": "Nach einem Ransomware-Vorfall soll ein neues, widerstandsfähigeres Backup-Konzept "
                "für einen Fileserver mit 2 TB Nutzdaten entworfen werden.\n\n"
                "1. Welches Sicherungsverfahren (voll/differentiell/inkrementell) empfehlen Sie für die tägliche "
                "Sicherung und warum?\n"
                "2. Welche Rolle spielt ein 'Air Gap' in diesem Konzept?\n"
                "3. Wie lässt sich die 3-2-1-Regel konkret auf dieses Szenario anwenden?",
        "solution": "1. Inkrementelle tägliche Sicherungen nach einer wöchentlichen Vollsicherung sparen Zeit "
                    "und Speicherplatz, da nur geänderte Daten gesichert werden.\n"
                    "2. Eine per Air Gap getrennte Kopie (offline oder isoliertes Netz) kann von Ransomware im "
                    "Produktivnetz nicht verschlüsselt werden und ermöglicht so eine garantierte Wiederherstellung.\n"
                    "3. 3 Kopien der Daten (Original + 2 Backups), auf 2 unterschiedlichen Medientypen "
                    "(z.B. NAS und Band/Cloud), davon 1 Kopie extern bzw. per Air Gap getrennt gelagert.",
    },
    {
        "title": "Härtung eines öffentlich erreichbaren Webservers",
        "cat": CAT_SEC,
        "theme": "IT-Sicherheit",
        "text": "Ein Webserver soll aus dem Internet erreichbar sein und in die DMZ eines Unternehmens "
                "gestellt werden.\n\n"
                "1. Welche Firewall-Regeln sind für die DMZ grundsätzlich sinnvoll?\n"
                "2. Welche zwei technischen Maßnahmen schützen die Datenübertragung und die Anmeldung "
                "am Server?\n"
                "3. Warum sollte der Webserver nicht direkt im internen LAN stehen?",
        "solution": "1. Nach dem Prinzip 'Deny All, Allow by Exception' werden nur die für den Webserver "
                    "notwendigen Ports (z.B. 443) gezielt freigegeben, alle anderen Verbindungen blockiert.\n"
                    "2. TLS-Verschlüsselung (HTTPS) für die Datenübertragung und Zwei-Faktor-Authentifizierung "
                    "für den administrativen Zugang.\n"
                    "3. Bei einer Kompromittierung im internen LAN hätte ein Angreifer direkten Zugriff auf "
                    "schützenswerte interne Systeme - die DMZ isoliert öffentlich erreichbare Dienste vom "
                    "internen Netz.",
    },
    {
        "title": "Social Engineering am Telefon",
        "cat": CAT_SEC,
        "theme": "IT-Sicherheit",
        "text": "Ein vermeintlicher IT-Dienstleister ruft den Support an und bittet unter Zeitdruck um die "
                "Herausgabe eines Administrator-Passworts, um angeblich einen 'kritischen Fehler' zu beheben.\n\n"
                "1. Um welche Angriffsart handelt es sich hier?\n"
                "2. Wie sollte der Mitarbeiter korrekt reagieren?\n"
                "3. Welche organisatorische Regel verhindert solche Vorfälle langfristig?",
        "solution": "1. Ein klassischer Social-Engineering-Angriff (Pretexting), der Autorität und Zeitdruck "
                    "ausnutzt, um Sicherheitsregeln zu umgehen.\n"
                    "2. Passwörter niemals telefonisch herausgeben, die Identität des Anrufers über einen "
                    "bekannten, offiziellen Rückrufweg verifizieren und den Vorfall dem Sicherheitsteam melden.\n"
                    "3. Klare Richtlinie, dass Passwörter grundsätzlich nie telefonisch oder per E-Mail "
                    "weitergegeben werden, kombiniert mit regelmäßigen Awareness-Schulungen.",
    },
    {
        "title": "Speicherkonzept für eine wachsende Datenbank",
        "cat": CAT_SYS,
        "theme": "Storage & RAID",
        "text": "Eine Datenbank mit hoher Schreiblast soll auf einem neuen Server mit 8 Festplatten "
                "gleicher Größe betrieben werden. Höchste Ausfallsicherheit und gute Performance sind "
                "gefordert, das Budget erlaubt den Verlust von 50% Kapazität für Redundanz.\n\n"
                "1. Welches RAID-Level empfehlen Sie und warum?\n"
                "2. Welche Nutzkapazität ergibt sich bei 8 Platten à 4 TB?\n"
                "3. Welche zusätzliche Maßnahme reduziert die Ausfallzeit bei einem Plattendefekt?",
        "solution": "1. RAID 10 (Spiegelung + Striping), da es hohe Schreib-/Leseperformance mit sehr guter "
                    "Ausfallsicherheit und schnellem Rebuild verbindet - passend zum vorgegebenen "
                    "50%-Kapazitätsbudget.\n"
                    "2. Bei RAID 10 steht die Hälfte der Rohkapazität zur Verfügung: 8 x 4 TB / 2 = 16 TB "
                    "nutzbare Kapazität.\n"
                    "3. Ein Hot-Spare-Laufwerk, das bei Ausfall automatisch in den Verbund einspringt und den "
                    "Rebuild sofort startet, ohne auf einen manuellen Plattentausch zu warten.",
    },
    {
        "title": "Virtualisierung eines physischen Servers",
        "cat": CAT_SYS,
        "theme": "Virtualisierung",
        "text": "Ein Unternehmen betreibt fünf separate, wenig ausgelastete physische Server und möchte "
                "diese konsolidieren.\n\n"
                "1. Welche Technologie eignet sich zur Konsolidierung und warum?\n"
                "2. Welchen Vorteil bietet ein Snapshot vor einer geplanten Änderung an einer virtuellen "
                "Maschine?\n"
                "3. Welches Risiko entsteht durch die Konsolidierung auf einen einzigen Host und wie lässt "
                "es sich reduzieren?",
        "solution": "1. Virtualisierung mit einem Typ-1-Hypervisor (z.B. Proxmox VE, VMware ESXi) fasst "
                    "die gering ausgelasteten Server als VMs auf gemeinsam genutzter Hardware zusammen und "
                    "spart so Anschaffungs-, Energie- und Wartungskosten.\n"
                    "2. Ein Snapshot ermöglicht ein schnelles Zurücksetzen auf den vorherigen Zustand, falls "
                    "die Änderung fehlschlägt - ohne aufwendige Neuinstallation.\n"
                    "3. Ein Ausfall des einzigen Hosts würde alle VMs gleichzeitig lahmlegen (Single Point of "
                    "Failure) - reduzierbar durch einen Cluster mit mindestens zwei Hosts und Failover.",
    },
    {
        "title": "Notfallwiederherstellung nach Serverausfall",
        "cat": CAT_SYS,
        "theme": "Storage & RAID",
        "text": "Ein physischer Server mit kritischer Anwendung fällt komplett aus (Mainboard-Defekt). "
                "Es existiert ein tägliches Backup sowie ein zweiter, baugleicher Server als Kaltreserve.\n\n"
                "1. Was bedeuten RTO und RPO in diesem Zusammenhang konkret?\n"
                "2. Welche Schritte sind zur Wiederherstellung des Dienstes notwendig?\n"
                "3. Wie könnte die Ausfallzeit künftig weiter reduziert werden?",
        "solution": "1. Die RPO gibt vor, wie viele Daten seit dem letzten Backup maximal verloren gehen "
                    "dürfen (hier: bis zu 24 Stunden), die RTO die maximal tolerierbare Zeit bis zur "
                    "Wiederherstellung des Dienstes.\n"
                    "2. Das letzte Backup auf den Ersatzserver einspielen, Netzwerk- und Dienstkonfiguration "
                    "prüfen, Funktionstest durchführen und den Dienst wieder freigeben.\n"
                    "3. Aufbau eines Clusters mit automatischem Failover oder eines Hot-Standby-Systems, "
                    "sodass bei einem Hardwaredefekt kein manueller Eingriff mehr nötig ist.",
    },
    {
        "title": "Investitionsentscheidung: Kauf vs. Leasing",
        "cat": CAT_BIZ,
        "theme": "Wirtschaft & Beratung",
        "text": "Ein Kunde überlegt, neue Arbeitsplatzrechner zu kaufen oder zu leasen.\n\n"
                "1. Nennen Sie je einen wirtschaftlichen Vorteil von Kauf und von Leasing.\n"
                "2. Welche Kennzahl hilft dabei, die tatsächlichen Gesamtkosten beider Varianten "
                "vergleichbar zu machen?\n"
                "3. Welche Rolle spielt die Nutzungsdauer der Geräte bei der Entscheidung?",
        "solution": "1. Kauf: Die Geräte gehören dem Unternehmen und können frei genutzt/verkauft werden. "
                    "Leasing: Geringere einmalige Kapitalbindung und planbare, konstante monatliche Raten.\n"
                    "2. Die TCO-Betrachtung (Total Cost of Ownership) erfasst neben dem reinen Anschaffungs- "
                    "bzw. Leasingpreis auch Wartung, Support, Versicherung und Restwert.\n"
                    "3. Bei kurzer geplanter Nutzungsdauer und schnellem technischem Wandel ist Leasing oft "
                    "vorteilhafter, bei langer Nutzung kann sich ein Kauf finanziell eher lohnen.",
    },
    {
        "title": "Angebotsabgabe mit Lasten- und Pflichtenheft",
        "cat": CAT_BIZ,
        "theme": "Wirtschaft & Beratung",
        "text": "Ein Kunde möchte eine neue Serverinfrastruktur ausschreiben und beauftragt Ihr Unternehmen "
                "mit einem Angebot.\n\n"
                "1. Welches Dokument erstellt der Kunde, welches Ihr Unternehmen als Auftragnehmer?\n"
                "2. Warum ist eine gründliche Ist-Analyse vor der Angebotserstellung wichtig?\n"
                "3. Welche Konsequenz kann ein unklares Lastenheft für das spätere Projekt haben?",
        "solution": "1. Der Kunde erstellt das Lastenheft (WAS wird benötigt), Ihr Unternehmen als "
                    "Auftragnehmer erstellt darauf aufbauend das Pflichtenheft (WIE wird es technisch "
                    "umgesetzt).\n"
                    "2. Die Ist-Analyse deckt die vorhandene Infrastruktur und tatsächlichen Anforderungen "
                    "auf, wodurch Fehlplanungen und spätere teure Nachbesserungen vermieden werden.\n"
                    "3. Ein unklares Lastenheft führt häufig zu Missverständnissen, Nachträgen (Change "
                    "Requests), Budget- und Terminüberschreitungen im weiteren Projektverlauf.",
    },
    {
        "title": "Projektorganisation mit Scrum",
        "cat": CAT_BIZ,
        "theme": "Projektmanagement",
        "text": "Ein internes Entwicklungsteam soll künftig nach Scrum arbeiten statt nach dem bisherigen "
                "Wasserfallmodell.\n\n"
                "1. Welche drei Rollen müssen im Team besetzt werden?\n"
                "2. Welchen Vorteil bietet die iterative Arbeitsweise in Sprints gegenüber dem "
                "Wasserfallmodell bei sich ändernden Anforderungen?\n"
                "3. Wofür dient das Sprint Review am Ende eines Sprints?",
        "solution": "1. Product Owner (verantwortet das Product Backlog und Anforderungen), Scrum Master "
                    "(moderiert den Prozess und beseitigt Hindernisse) und das Entwicklungsteam (setzt die "
                    "Arbeit um).\n"
                    "2. Da Anforderungen zu Sprintbeginn neu priorisiert werden können, lassen sich "
                    "Änderungen deutlich schneller einarbeiten als beim starren, sequenziellen "
                    "Wasserfallmodell.\n"
                    "3. Im Sprint Review wird das fertiggestellte Increment den Stakeholdern präsentiert, um "
                    "frühzeitig Feedback zu erhalten und die weitere Priorisierung anzupassen.",
    },
]


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

PROJEKTARBEITEN = [
    {
        "title": "Netzwerk-Rollout für eine neue Filiale",
        "cat": CAT_NET,
        "branche": "Einzelhandelskette (ModeWelt GmbH), 13. Filiale",
        "schwierigkeit": "Mittel",
        "ausgangssituation": (
            "Die Modekette \"ModeWelt GmbH\" betreibt zwölf Filialen mit "
            "zentralem Rechenzentrum am Hauptsitz. Für die neue 13. Filiale "
            "(ca. 180 m², 8 Kassenarbeitsplätze, Lager mit 2 PCs, Büro mit "
            "3 PCs, WLAN für Kunden) muss die komplette Netzwerkinfrastruktur "
            "neu geplant und aufgebaut werden. Die Filiale soll an das "
            "zentrale Warenwirtschaftssystem am Hauptsitz angebunden werden."
        ),
        "auftrag": (
            "Planen und dokumentieren Sie den Netzwerk-Rollout inklusive "
            "Verkabelung, aktiver Komponenten, WLAN-Konzept und Anbindung "
            "an den Hauptsitz."
        ),
        "rahmenbedingungen": [
            "Zeitrahmen: 6 Wochen bis zur Ladeneröffnung",
            "Budget: 8.500 Euro für Hardware und Verkabelung",
            "Anbindung Hauptsitz: vorhandene Internetleitung 100 Mbit/s Down / 40 Mbit/s Up",
            "Kassensystem und Warenwirtschaft benötigen eine priorisierte, stabile Verbindung",
            "Das Kunden-WLAN muss vom internen Netz vollständig getrennt sein",
        ],
        "aufgaben": [
            "Ist-Analyse: Welche Informationen benötigen Sie vor Planungsbeginn vom Kunden und vor Ort?",
            "Entwerfen Sie ein Netzwerk-/VLAN-Konzept (Anzahl Netze, Zweck, grobe IP-Adressierung).",
            "Erstellen Sie einen groben Projektstrukturplan mit den wichtigsten Arbeitspaketen.",
            "Kalkulieren Sie überschlägig die Kosten für aktive Komponenten und ordnen Sie diese dem Budget zu.",
            "Welche Maßnahme sichert die Anbindung an den Hauptsitz gegen den Ausfall der Standleitung ab?",
            "Wie stellen Sie die Abnahme/Qualitätssicherung des Projekts sicher?",
        ],
        "hinweise": [
            "Grundriss und Anzahl der Arbeitsplätze, vorhandene Verkabelung, Position von Serverraum/Technikschrank, "
            "Stromversorgung, bauliche Gegebenheiten (Kabelwege), bestehende Provider-Verträge sowie die genauen "
            "Anforderungen des Warenwirtschaftssystems.",
            "Mindestens drei VLANs sind sinnvoll: Kassen/Warenwirtschaft (hohe Priorität, QoS), Büro/Verwaltung und "
            "Kunden-WLAN (isoliert, eigenes Gastnetz ohne Zugriff auf interne Ressourcen) - je eigener privater "
            "IP-Bereich, z.B. 10.13.10.0/24, 10.13.20.0/24, 10.13.30.0/24.",
            "Arbeitspakete z.B.: Materialbeschaffung, Verkabelung, Installation aktiver Komponenten, Konfiguration "
            "VLANs/Firewall, Einrichtung VPN zum Hauptsitz, Funktionstest, Schulung des Personals, Pufferzeit vor "
            "der Eröffnung.",
            "Grobkalkulation: verwaltbarer PoE-Switch ca. 400-600 Euro, Firewall/Router ca. 500-800 Euro, "
            "2 Access Points ca. 300-400 Euro, Verkabelung/Patchpanel/Material ca. 1.000-1.500 Euro - Arbeitszeit "
            "separat kalkulieren und eine Reserve für Unvorhergesehenes einplanen.",
            "Eine zweite, unabhängige Anbindung (z.B. LTE/5G-Backup-Router mit automatischem Failover) sichert die "
            "Verbindung zum Hauptsitz gegen den Ausfall der Hauptleitung ab.",
            "Funktionstest aller Arbeitsplätze und der Anbindung vor Eröffnung, ein Abnahmeprotokoll mit dem Kunden "
            "sowie eine vollständige Dokumentation (Netzplan, IP-Konzept, Zugangsdaten), die dem Kunden übergeben wird.",
        ],
    },
    {
        "title": "Einführung einer Mehrfaktor-Authentifizierung",
        "cat": CAT_SEC,
        "branche": "Steuerberatungskanzlei, 25 Mitarbeiter",
        "schwierigkeit": "Mittel",
        "ausgangssituation": (
            "Die Kanzlei arbeitet mit sensiblen Mandantendaten (DATEV, "
            "E-Mail, Cloud-Speicher) und sichert die Anmeldung bislang "
            "ausschließlich über Benutzername und Passwort ab. Ein "
            "Phishing-Vorfall bei einem vergleichbaren Betrieb hat den "
            "Kanzleiinhaber alarmiert."
        ),
        "auftrag": (
            "Konzipieren und führen Sie eine Zwei- bzw. Mehrfaktor-"
            "Authentifizierung für alle kritischen Systeme ein und "
            "sensibilisieren Sie die Mitarbeiter für das Thema."
        ),
        "rahmenbedingungen": [
            "25 Mitarbeiter mit unterschiedlichem IT-Kenntnisstand (teils gering)",
            "Zeitrahmen: 4 Wochen inklusive Schulung",
            "Bestehende Systeme: Microsoft 365, DATEV-Arbeitsplatz, VPN-Zugang für Homeoffice",
            "Budget: 2.000 Euro für Lizenzen/Hardware-Token",
            "Der Kanzleibetrieb darf während der Einführung nicht unterbrochen werden",
        ],
        "aufgaben": [
            "Welche Systeme priorisieren Sie zuerst für MFA, und warum?",
            "Welche MFA-Verfahren kommen infrage, und welches empfehlen Sie für diese Zielgruppe?",
            "Planen Sie den Rollout in Phasen (Pilotgruppe, Vollausrollung).",
            "Welche Risiken und Stolpersteine erwarten Sie bei der Einführung, und wie begegnen Sie ihnen?",
            "Wie dokumentieren und schulen Sie die Mitarbeiter?",
            "Wie stellen Sie sicher, dass niemand bei Verlust des zweiten Faktors ausgesperrt wird?",
        ],
        "hinweise": [
            "Zuerst Microsoft 365 (E-Mail, Cloud-Daten) und der VPN-Zugang (Einfallstor fürs Homeoffice), da hier "
            "das größte Schadenspotenzial und die höchste Angriffswahrscheinlichkeit durch Phishing besteht.",
            "Eine Authenticator-App (TOTP) ist für die meisten Mitarbeiter praktikabel und kostengünstig; "
            "Hardware-Token als Alternative für Mitarbeiter ohne Diensthandy. SMS-basierte Verfahren möglichst "
            "vermeiden (anfällig für SIM-Swapping).",
            "Phase 1: Pilotgruppe (z.B. Geschäftsleitung/IT-affine Mitarbeiter, ca. 1 Woche Testbetrieb), "
            "Phase 2: schrittweiser Rollout nach Abteilungen, Phase 3: verpflichtende Aktivierung mit Stichtag, "
            "begleitet von Support-Sprechstunden.",
            "Stolpersteine: fehlende Diensthandys, Akzeptanzprobleme, Geräteverlust, erhöhtes Support-Aufkommen in "
            "der ersten Woche - gegensteuern mit Hardware-Token als Alternative, klarer Anleitung und einem "
            "benannten Ansprechpartner.",
            "Kurzanleitung mit Schritt-für-Schritt-Bildern, eine kurze Präsenzschulung oder ein Kurzvideo, ein "
            "FAQ-Dokument sowie ein begleiteter Test-Login pro Mitarbeiter.",
            "Bei der Einrichtung Backup-Codes generieren und sicher hinterlegen (z.B. verschlüsselt beim "
            "IT-Verantwortlichen) sowie einen definierten Prozess zur Identitätsprüfung festlegen, bevor bei "
            "Verlust ein Reset durchgeführt wird.",
        ],
    },
    {
        "title": "Serverkonsolidierung durch Virtualisierung",
        "cat": CAT_SYS,
        "branche": "Mittelständischer Maschinenbaubetrieb, 60 Mitarbeiter",
        "schwierigkeit": "Anspruchsvoll",
        "ausgangssituation": (
            "Der Betrieb nutzt fünf in die Jahre gekommene physische Server "
            "(Fileserver, Druckserver, ERP-Server, Domänencontroller, "
            "Backup-Server), die einzeln nur schwach ausgelastet sind und "
            "regelmäßig Wartungsaufwand verursachen. Die Hardware ist teils "
            "über sechs Jahre alt."
        ),
        "auftrag": (
            "Konsolidieren Sie die bestehende Serverlandschaft durch "
            "Virtualisierung auf neuer Hardware, inklusive Migrationskonzept "
            "ohne längere Betriebsunterbrechung."
        ),
        "rahmenbedingungen": [
            "Zeitrahmen: 3 Monate inklusive Testphase",
            "Budget: 18.000 Euro für neue Serverhardware und Lizenzen",
            "Die Migration darf nur an einem Wochenende die Produktion unterbrechen",
            "Bestehende Daten und Benutzerkonten müssen vollständig erhalten bleiben",
            "Die Ausfallsicherheit soll sich gegenüber dem Ist-Zustand verbessern",
        ],
        "aufgaben": [
            "Ist-Analyse: Welche Kennzahlen der bestehenden Server erheben Sie vor der Planung?",
            "Welchen Hypervisor-Typ empfehlen Sie, und warum?",
            "Wie dimensionieren Sie die neue Hardware (CPU, RAM, Storage) grob?",
            "Planen Sie das RAID- und Backup-Konzept für die neue Umgebung.",
            "Entwerfen Sie den Migrationsablauf für das Umstellungswochenende inklusive Rückfallplan (Rollback).",
            "Wie weisen Sie den erfolgreichen Projektabschluss gegenüber dem Kunden nach?",
        ],
        "hinweise": [
            "CPU-/RAM-Auslastung, Speicherbedarf und dessen Wachstum, Anzahl gleichzeitiger Nutzer, kritische "
            "Dienste und ihre Abhängigkeiten sowie bisherige Ausfallzeiten und Wartungsaufwand je Server.",
            "Ein Typ-1-Hypervisor (z.B. Proxmox VE oder VMware ESXi), da er direkt auf der Hardware läuft und "
            "dadurch ressourcenschonender und für den Produktivbetrieb geeigneter ist als ein Typ-2-Hypervisor.",
            "Die summierte Spitzenlast der fünf bisherigen Server plus Reserve (ca. 30-40 %) für Wachstum und "
            "gleichzeitige Lastspitzen; ausreichend RAM für alle VMs plus Hypervisor-Overhead; Storage nach "
            "heutigem Bedarf plus Wachstumsprognose für die kommenden drei bis fünf Jahre.",
            "RAID 10 oder RAID 6 für eine gute Balance aus Performance und Ausfallschutz, dazu ein Backup-Konzept "
            "nach der 3-2-1-Regel mit mindestens einer extern bzw. per Air Gap getrennt gelagerten Kopie gegen "
            "Ransomware.",
            "Vorbereitung und Tests unter der Woche, die eigentliche Migration am Wochenende mit klar definierten "
            "Zeitfenstern je Dienst, ein vollständiges Backup vor Beginn als Rollback-Basis, Funktionstests nach "
            "jedem Schritt sowie ein festgelegter Zeitpunkt, bis zu dem notfalls auf die alte Umgebung "
            "zurückgeschaltet wird.",
            "Ein Abnahmeprotokoll mit dem Kunden, gemeinsame Funktionstests aller migrierten Dienste mit den "
            "Fachabteilungen, eine Dokumentation der neuen Umgebung (Netzplan, VM-Übersicht, Backup-Konzept) sowie "
            "eine vereinbarte kurze Nachbetreuungsphase.",
        ],
    },
    {
        "title": "Wirtschaftlichkeitsvergleich: Kauf vs. Leasing von Arbeitsplatzrechnern",
        "cat": CAT_BIZ,
        "branche": "Ingenieurbüro, 15 Mitarbeiter",
        "schwierigkeit": "Mittel",
        "ausgangssituation": (
            "Die vorhandenen 15 Arbeitsplatzrechner sind fünf Jahre alt und "
            "für aktuelle CAD-Software nicht mehr ausreichend "
            "leistungsfähig. Die Geschäftsführung möchte vor der "
            "Neubeschaffung eine fundierte Entscheidungsgrundlage: Kauf "
            "oder Leasing der neuen Rechner."
        ),
        "auftrag": (
            "Erstellen Sie einen Wirtschaftlichkeitsvergleich und eine "
            "Beschaffungsempfehlung inklusive Argumentation für die "
            "Geschäftsführung."
        ),
        "rahmenbedingungen": [
            "Geplante Nutzungsdauer: 4 Jahre",
            "Geschätzter Kaufpreis je Arbeitsplatz: 2.200 Euro (CAD-taugliche Ausstattung)",
            "Geschätzte Leasingrate: 55 Euro/Monat je Gerät bei 4 Jahren Laufzeit",
            "Wartung/Support beim Kauf: geschätzt 150 Euro/Jahr und Gerät nach Garantieablauf (ab Jahr 3)",
            "Beim Leasing im Vertrag enthalten: Austauschservice bei Defekt",
        ],
        "aufgaben": [
            "Stellen Sie die relevanten Kostenfaktoren für Kauf und Leasing gegenüber.",
            "Berechnen Sie überschlägig die Gesamtkosten (TCO) beider Varianten über die Nutzungsdauer für alle 15 Arbeitsplätze.",
            "Welche nicht-monetären Faktoren sollten zusätzlich in die Entscheidung einfließen?",
            "Welche Rolle spielt die Liquidität des Unternehmens bei der Entscheidung?",
            "Formulieren Sie eine begründete Empfehlung an die Geschäftsführung.",
        ],
        "hinweise": [
            "Kauf: Anschaffungspreis, ggf. Finanzierungskosten, Wartung/Reparatur nach Garantieablauf, Restwert am "
            "Ende der Nutzungsdauer. Leasing: monatliche Raten, ggf. Anzahlung, im Vertrag enthaltene Leistungen "
            "(Austauschservice), kein Restwert, da Rückgabe.",
            "Kauf: 15 x 2.200 Euro = 33.000 Euro Anschaffung, plus Wartung ab Jahr 3 (2 Jahre x 150 Euro x "
            "15 Geräte = 4.500 Euro) = ca. 37.500 Euro, abzüglich eines möglichen Restwerts. Leasing: "
            "15 x 55 Euro x 48 Monate = 39.600 Euro, dafür planbare Kosten ohne separates Wartungsrisiko - bei "
            "diesen Annahmen ist der Kauf rechnerisch etwas günstiger.",
            "Bilanzielle Behandlung (Kauf als Anlagevermögen mit Abschreibung, Leasing meist als laufender "
            "Aufwand), Flexibilität bei technologischem Wandel, Verwaltungsaufwand sowie Ausfallrisiko und "
            "Reaktionszeit bei Defekten.",
            "Kauf bindet sofort Kapital (Liquiditätsabfluss), Leasing verteilt die Belastung gleichmäßig über die "
            "Laufzeit und schont die Liquidität - relevant, wenn das Kapital anderweitig, z.B. für Investitionen, "
            "benötigt wird.",
            "Beispiel: Bei ausreichender Liquidität und Fokus auf die geringsten Gesamtkosten spricht die "
            "Berechnung für den Kauf; ist Planungssicherheit und Schonung der Liquidität wichtiger, ist Leasing "
            "trotz höherer Gesamtkosten die passendere Wahl - die Entscheidung hängt von der individuellen "
            "Unternehmenssituation ab, nicht allein vom reinen Zahlenvergleich.",
        ],
    },
    {
        "title": "WLAN- und Gästenetz für ein Autohaus",
        "cat": CAT_NET,
        "branche": "Autohaus mit Werkstatt und Kundenbereich",
        "schwierigkeit": "Mittel",
        "ausgangssituation": (
            "Ein neues Autohausgebäude (Verkaufsraum, Werkstatt, "
            "Kundenlounge, Büros) verfügt noch über keine WLAN-"
            "Infrastruktur. Kunden sollen in der Lounge kostenlos surfen "
            "können, die Werkstatt benötigt WLAN für mobile "
            "Diagnosegeräte, der Verkauf für Tablets bei der "
            "Fahrzeugpräsentation."
        ),
        "auftrag": (
            "Planen Sie ein WLAN-Konzept, das interne Nutzung und "
            "Gästezugang sauber trennt und alle Bereiche zuverlässig "
            "abdeckt."
        ),
        "rahmenbedingungen": [
            "Gebäudegröße: ca. 1.200 m² auf zwei Ebenen",
            "Zeitrahmen: 3 Wochen",
            "Budget: 4.500 Euro",
            "Die Werkstatt enthält viel Metall (Hebebühnen), das die Funkausbreitung beeinträchtigt",
            "Das Gästenetz darf keinen Zugriff auf interne Systeme haben, die Bandbreite soll begrenzbar sein",
        ],
        "aufgaben": [
            "Wie ermitteln Sie die benötigte Anzahl und Platzierung der Access Points?",
            "Entwerfen Sie das Netzwerk-/VLAN-Konzept für Gäste-, Werkstatt- und Verkaufs-WLAN.",
            "Welche Sicherheitsmaßnahmen setzen Sie für das Gästenetz um?",
            "Wie begegnen Sie der besonderen Funkumgebung in der Werkstatt?",
            "Wie kalkulieren Sie die Hardwarekosten grob im Rahmen des Budgets?",
        ],
        "hinweise": [
            "Eine WLAN-Ausleuchtungsplanung (Site Survey) mit Grundriss, Berücksichtigung von Wänden/Materialien "
            "und der erwarteten Nutzerzahl je Bereich; bei 1.200 m² auf zwei Ebenen sind grob 6-8 Access Points "
            "zu erwarten, die genaue Zahl ergibt sich erst nach einer Vor-Ort-Messung.",
            "Mindestens drei WLANs/VLANs: Gäste-WLAN (isoliert, eigenes Subnetz, nur Internetzugang), "
            "Werkstatt-WLAN (Zugriff auf Diagnosesysteme/Herstellerportale) und Verkaufs-WLAN (Zugriff auf "
            "CRM/Warenwirtschaft) - jeweils eigene SSID und VLAN mit Firewall-Regeln zwischen den Netzen.",
            "Eine eigene, vom internen Netz isolierte SSID mit Client-Isolation (Gäste sehen sich nicht "
            "gegenseitig), Bandbreitenbegrenzung pro Nutzer sowie ggf. eine Splash-Page mit Nutzungsbedingungen "
            "und regelmäßigem Passwortwechsel.",
            "Zusätzliche Access Points bzw. Modelle mit höherer Sendeleistung/besserer Antenne gezielt außerhalb "
            "direkter Metallabschattung in der Werkstatt platzieren und nach der Installation eine Nachmessung "
            "der Feldstärke durchführen.",
            "Beispielkalkulation: 6-8 Access Points (je ca. 150-250 Euro) = ca. 1.200-2.000 Euro, ein "
            "verwaltbarer PoE-Switch ca. 400-600 Euro, Verkabelung/Montage ca. 800-1.200 Euro, Rest als Puffer "
            "für Lizenzen/Controller-Software.",
        ],
    },
    {
        "title": "Backup- und Notfallkonzept für eine Zahnarztpraxis",
        "cat": CAT_SYS,
        "branche": "Zahnarztpraxis mit Praxisverwaltungssoftware und digitalem Röntgen",
        "schwierigkeit": "Anspruchsvoll",
        "ausgangssituation": (
            "Die Praxis speichert Patientendaten, Röntgenbilder und "
            "Abrechnungsdaten ausschließlich auf einem lokalen Server. "
            "Bisher existiert keine strukturierte Datensicherung - "
            "gelegentlich wird von Hand auf eine externe Festplatte "
            "kopiert. Der Praxisinhaber möchte ein zuverlässiges Backup- "
            "und Notfallkonzept, da ein Datenverlust den Praxisbetrieb "
            "gefährden würde."
        ),
        "auftrag": (
            "Entwickeln Sie ein Backup- und Notfallwiederherstellungs-"
            "konzept inklusive Umgang mit den besonders sensiblen "
            "(personenbezogenen) Gesundheitsdaten."
        ),
        "rahmenbedingungen": [
            "Zeitrahmen: 3 Wochen",
            "Budget: 3.000 Euro",
            "Datenvolumen: aktuell ca. 800 GB, wächst um ca. 150 GB/Jahr",
            "Maximal tolerierbarer Datenverlust: 1 Arbeitstag",
            "Maximal tolerierbare Ausfallzeit bis zur Wiederherstellung: 4 Stunden während der Sprechzeiten",
            "Datenschutzrechtliche Vorgaben für Gesundheitsdaten sind zwingend zu beachten",
        ],
        "aufgaben": [
            "Leiten Sie aus den Vorgaben RPO und RTO für dieses Projekt ab.",
            "Entwerfen Sie ein passendes Backup-Konzept (Rhythmus, Medien, Aufbewahrungsorte).",
            "Welche besonderen Anforderungen ergeben sich durch die Verarbeitung von Gesundheitsdaten?",
            "Wie testen Sie regelmäßig, dass die Datensicherung im Ernstfall tatsächlich funktioniert?",
            "Kalkulieren Sie überschlägig die notwendige Hardware/Software im Rahmen des Budgets.",
        ],
        "hinweise": [
            "RPO = maximal 1 Arbeitstag (mindestens tägliche Sicherung notwendig), RTO = maximal 4 Stunden (der "
            "Wiederherstellungsprozess muss entsprechend vorbereitet und geübt sein, z.B. durch ein "
            "Standby-System oder eine schnell einspielbare Vollsicherung).",
            "Tägliche automatisierte Sicherung (z.B. inkrementell unter der Woche, wöchentliche Vollsicherung) "
            "nach der 3-2-1-Regel: mindestens 3 Kopien, 2 unterschiedliche Medien (z.B. NAS und externe "
            "Festplatte/Cloud), mindestens 1 Kopie extern bzw. per Air Gap getrennt gelagert.",
            "Gesundheitsdaten zählen nach Art. 9 DSGVO zu besonders sensiblen Daten und erfordern erhöhte "
            "Schutzmaßnahmen: Verschlüsselung der Backups, Zugriffsbeschränkung, ggf. ein "
            "Auftragsverarbeitungsvertrag bei Nutzung eines Cloud-Anbieters sowie dokumentierte Löschkonzepte "
            "nach den gesetzlichen Aufbewahrungsfristen.",
            "Regelmäßige Testwiederherstellungen (z.B. quartalsweise) auf einem Testsystem durchführen und "
            "protokollieren - ein ungetestetes Backup ist kein verlässliches Backup.",
            "Beispielkalkulation: NAS-System mit ausreichender Kapazität und RAID (ca. 800-1.200 Euro), externe "
            "Wechselfestplatten für die extern gelagerte Kopie (ca. 200-300 Euro), Backup-Software-Lizenz "
            "(ca. 200-400 Euro/Jahr), Rest als Puffer für Einrichtung/Dienstleistung.",
        ],
    },
]


# ============================================================================
#  ABGELEITETE KENNZAHLEN
# ============================================================================

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
        totals[scenario["theme"]] = totals.get(scenario["theme"], 0) + 1
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
