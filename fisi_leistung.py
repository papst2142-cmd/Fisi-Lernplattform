#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FISI Lernplattform - Leistungsmessung (ab 0.58.1)
=================================================

Zeichnet auf Wunsch (Schalter in den Optionen, standardmaessig aus) auf, wie
lange Seitenwechsel, Darstellungswechsel und Aenderungen der Fenstergroesse
dauern und wie viel Arbeitsspeicher das Programm dabei braucht. Damit lassen
sich Zahlen vom eigenen Geraet mit der Messung in der Cloud vergleichen
(plan_0.58.1).

Ohne Oberflaeche, damit PC und Handy dieselben Texte und dasselbe
Dateiformat haben. Die Oberflaechen melden nur Ereignisse (record) und
rufen regelmaessig flush() auf.

Datenschutz: In die Datei kommen nur Zeitpunkt, Programmversion, Geraetetyp,
Betriebssystem, Ereignis (z. B. Seitenwechsel "dashboard" -> "settings"),
Dauer, Speicher und Anzahlen. Keine Lernstand-Daten, kein Name, keine
Inhalte. Nichts wird gesendet. Der Schalter liegt nur in einstellungen.json
(nicht im Abgleich, fisi_sync).

Ist die Messung aus, kostet sie nichts: record() kehrt sofort zurueck, die
Oberflaechen binden ihre Zusatz-Ereignisse (Fenstergroesse) erst beim
Einschalten, und es entsteht keine Datei.

Ablauf:
  rec = Recorder("0.58.1", "PC")
  rec.record("seite", von="dashboard", nach="settings", dauer_ms=42.0,
             elemente=3300, aufgaben=25)
  rec.flush()              -> gebuendelt schreiben (die Oberflaeche ruft das
                              alle FLUSH_SECONDS Sekunden und beim Beenden auf)
"""

import datetime
import os
import platform
import sys

import fisi_update
from fisi_core import resolve_db_path

# Texte (PC und Handy gleich)
TITLE = "Leistungsmessung"
SUBTITLE = "nur für dieses Gerät"
HELP = ("Zeichnet auf, wie lange Seitenwechsel, Darstellungswechsel und Änderungen "
        "der Fenstergröße dauern und wie viel Arbeitsspeicher das Programm braucht. "
        "Die Messdatei bleibt auf diesem Gerät, es wird nichts gesendet. Sie enthält "
        "keine Lerninhalte und keinen Namen. Ist die Messung aus, wird nichts "
        "aufgezeichnet.")
SWITCH = "Messung aufzeichnen"
BTN_SHOW = "Messdatei zeigen"
BTN_DELETE = "Messdatei löschen"
STATE_NONE = "Noch keine Messdatei vorhanden."
STATE_FILE = "Messdatei: %(zeilen)d Einträge, %(kb)s KB"
MSG_DELETED = "Messdatei gelöscht"
MSG_SHOW_ERROR = "Die Messdatei ließ sich nicht öffnen: %s"

SETTING_KEY = "leistungsmessung"
FILE_NAME = "leistungsmessung.csv"
FILE_TYPE = "text/csv"
MAX_BYTES = 1024 * 1024        # hoechstens 1 MB, aelteste Zeilen fallen weg
TRIM_TO = int(MAX_BYTES * 0.8)  # nach dem Kuerzen etwas Luft, damit nicht jede Zeile kuerzt
FLUSH_LINES = 25               # spaetestens nach so vielen Zeilen schreiben
FLUSH_SECONDS = 5              # sonst schreibt die Oberflaeche alle 5 s

COLUMNS = ("zeit", "version", "geraet", "system", "ereignis", "von", "nach", "dauer_ms",
           "max_ms", "anzahl", "ereignisse", "speicher_mb", "privat_mb", "elemente",
           "aufgaben")
SEPARATOR = ";"

# Ereignisse
EVENT_START = "start"            # Messung laeuft (beim Start oder beim Einschalten)
EVENT_PAGE = "seite"             # Seitenwechsel von -> nach
EVENT_THEME = "darstellung"      # Darstellung, Farbe oder Schriftgroesse neu aufgebaut
EVENT_RESIZE = "groesse"         # Groessenaenderung, zusammengefasst
EVENT_STOP = "ende"              # Messung ausgeschaltet oder Programm beendet


# ============================================================================
#  EINSTELLUNG
# ============================================================================

def enabled():
    """Ist die Messung eingeschaltet? Nur ein gespeichertes true gilt -
    alles andere (fehlt, Text, Zahl) ist aus."""
    return fisi_update.load_settings().get(SETTING_KEY) is True


def set_enabled(flag):
    settings = fisi_update.load_settings()
    settings[SETTING_KEY] = bool(flag)
    return fisi_update.save_settings(settings)


def file_path():
    """Die Messdatei liegt im Datenordner neben der Datenbank."""
    return os.path.join(os.path.dirname(resolve_db_path()), FILE_NAME)


# ============================================================================
#  SPEICHER UND SYSTEM
# ============================================================================

def memory_mb():
    """(Arbeitsspeicher, privater Speicher) des Programms in MB.

    Windows: Arbeitssatz (WorkingSetSize) und zugesicherter privater Speicher
    (PrivateUsage) - der Task-Manager zeigt standardmaessig einen Wert
    dazwischen (aktiver privater Arbeitssatz). Linux und Android: belegter
    Speicher (RSS) aus /proc. macOS: hoechster bisher belegter Speicher.
    Nicht ermittelbar: (None, None)."""
    try:
        if sys.platform == "win32":
            return _memory_windows()
        if os.path.exists("/proc/self/statm"):
            with open("/proc/self/statm") as handle:
                pages = int(handle.read().split()[1])
            return pages * os.sysconf("SC_PAGE_SIZE") / 1048576.0, None
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return peak / (1048576.0 if sys.platform == "darwin" else 1024.0), None
    except Exception:  # noqa: BLE001 - die Messung darf das Programm nie stoeren
        return None, None


def _memory_windows():
    import ctypes
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                    ("PrivateUsage", ctypes.c_size_t)]
    counters = Counters()
    counters.cb = ctypes.sizeof(Counters)
    process = ctypes.windll.kernel32.GetCurrentProcess()
    if not ctypes.windll.psapi.GetProcessMemoryInfo(process, ctypes.byref(counters),
                                                    counters.cb):
        return None, None
    return counters.WorkingSetSize / 1048576.0, counters.PrivateUsage / 1048576.0


def system_text():
    """Betriebssystem kurz, z. B. "Windows 11" oder "Linux 6.8"."""
    try:
        name, release = platform.system(), platform.release()
        if hasattr(sys, "getandroidapilevel") or "ANDROID_ROOT" in os.environ:
            name = "Android"
        return ("%s %s" % (name, release)).strip()
    except Exception:  # noqa: BLE001
        return sys.platform


# ============================================================================
#  AUFZEICHNUNG
# ============================================================================

def _number(value, digits=1):
    if value is None:
        return ""
    if isinstance(value, float):
        return ("%.*f" % (digits, value)).replace(".", ",")
    return str(value)


def _clean(value):
    """Keine Trennzeichen oder Zeilenumbrueche in einem Feld."""
    return str(value or "").replace(SEPARATOR, ",").replace("\n", " ").replace("\r", " ")


class Recorder:
    """Sammelt Messzeilen im Speicher und schreibt sie gebuendelt.

    active wird beim Erzeugen aus den Einstellungen gelesen und mit
    set_active() umgeschaltet; ist es aus, tut record() nichts."""

    def __init__(self, version, device, path=None):
        self.version = version
        self.device = device
        self.path = path or file_path()
        self.system = system_text()
        self.buffer = []
        self.active = enabled()

    def set_active(self, flag):
        flag = bool(flag)
        if flag == self.active:
            return
        if not flag:
            self.record(EVENT_STOP)
            self.flush()
        self.active = flag
        set_enabled(flag)
        if flag:
            self.record(EVENT_START)

    def record(self, event, von="", nach="", dauer_ms=None, max_ms=None, anzahl=None,
               ereignisse=None, elemente=None, aufgaben=None, speicher=True):
        if not self.active:
            return
        memory, private = memory_mb() if speicher else (None, None)
        now = datetime.datetime.now().isoformat(timespec="milliseconds")
        values = (now, self.version, self.device, self.system, event, von, nach,
                  _number(dauer_ms), _number(max_ms), _number(anzahl),
                  _number(ereignisse), _number(memory), _number(private),
                  _number(elemente), _number(aufgaben))
        self.buffer.append(SEPARATOR.join(_clean(value) for value in values))
        if len(self.buffer) >= FLUSH_LINES:
            self.flush()

    def flush(self):
        """Gesammelte Zeilen anhaengen und die Datei auf MAX_BYTES begrenzen."""
        if not self.buffer:
            return True
        lines, self.buffer = self.buffer, []
        try:
            new = not os.path.exists(self.path)
            with open(self.path, "a", encoding="utf-8", newline="\n") as handle:
                if new:
                    handle.write(SEPARATOR.join(COLUMNS) + "\n")
                handle.write("\n".join(lines) + "\n")
            if os.path.getsize(self.path) > MAX_BYTES:
                self._trim()
            return True
        except OSError:
            return False   # z. B. Datenordner schreibgeschuetzt: Messung verloren, Programm laeuft

    def _trim(self):
        with open(self.path, encoding="utf-8") as handle:
            header, *rows = handle.read().splitlines()
        size = len(header.encode("utf-8")) + 1
        keep = []
        for row in reversed(rows):
            size += len(row.encode("utf-8")) + 1
            if size > TRIM_TO:
                break
            keep.append(row)
        keep.reverse()
        temp = self.path + ".tmp"
        with open(temp, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join([header] + keep) + "\n")
        os.replace(temp, self.path)

    def delete(self):
        """Messdatei und noch nicht geschriebene Zeilen verwerfen."""
        self.buffer = []
        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass
        except OSError:
            return False
        return True

    def info(self):
        """(Anzahl Eintraege, Groesse in Byte) oder None ohne Datei."""
        self.flush()
        try:
            with open(self.path, encoding="utf-8") as handle:
                rows = max(0, sum(1 for _line in handle) - 1)
            return rows, os.path.getsize(self.path)
        except OSError:
            return None

    def state_text(self):
        info = self.info()
        if info is None:
            return STATE_NONE
        rows, size = info
        return STATE_FILE % {"zeilen": rows, "kb": _number(size / 1024.0)}

    def read_bytes(self):
        """Inhalt der Messdatei (Handy: zum Speichern oder Teilen)."""
        self.flush()
        with open(self.path, "rb") as handle:
            return handle.read()
