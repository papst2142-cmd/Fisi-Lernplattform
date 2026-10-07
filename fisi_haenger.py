#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FISI Lernplattform - Haenger-Diagnose (ab 0.59.2, nur PC)
=========================================================

Haelt fest, WO das Programm steht, wenn der Hauptfaden haengt oder lange
blockiert ist - nur Diagnose, kein anderes Verhalten.

Bausteine:
  * Herzschlag: Die Oberflaeche ruft beat() alle BEAT_MS ms im Hauptfaden
    auf (after-Zeitgeber, laeuft immer, auch ohne Leistungsmessung). beat()
    merkt sich die Zeit und setzt alle ARM_SECONDS den faulthandler-Zeitgeber
    (DUMP_AFTER s) neu.
  * faulthandler: Steht der Hauptfaden DUMP_AFTER s still, schreibt
    faulthandler aus seinem eigenen C-Faden die Stapel aller Threads nach
    haenger.log - auch wenn der Hauptfaden in C (Tcl/Xlib) festhaengt.
  * Waechter (Thread "fisi-waechter", daemon, liest nur): prueft jede
    Sekunde das Alter des Herzschlags. Ab BLOCK_SECONDS (bei bekannten
    langen Vorgaengen ab KNOWN_SECONDS) eine Zeile in fehler.log und
    haenger.log mit Seite, Vorgang und (Linux) den Wartepunkten der Threads
    aus /proc/self/task/*/wchan; endet die Blockade, eine Zeile "wieder
    frei". Hoechstens MAX_LINES Blockaden je Sitzung in fehler.log.
    Nach dem ersten Stapel setzt der Waechter den Zeitgeber einmal auf
    weitere DUMP_AGAIN s (der Herzschlag kann es ja nicht). Danach kein
    Stapel mehr, bis der Hauptfaden wieder laeuft; je Sitzung hoechstens
    MAX_AUTO_DUMPS automatische Stapel.
  * Stapel auf Abruf (Linux, macOS): kill -USR1 <pid> schreibt die Stapel
    aller Threads nach haenger.log. Erst ab 0.59.2 - in aelteren Versionen
    beendet dieses Signal das Programm.
  * Beim Schliessen (dump_on_close): Lebt der Prozess 5 s nach dem
    Schliessen noch, schreibt faulthandler die Stapel (der Notausgang nach
    8 s bleibt unveraendert).

Unter Windows kein faulthandler.enable() (meldet dort auch Ausnahmen, die
Treiber selbst abfangen) und kein Signal; Zeitgeber und Waechter laufen.

Grundsatz: Die Diagnose zeigt nie einen Fehler und stoppt nie das Programm.
Jede Funktion faengt alle Fehler ab; geht die Datei nicht auf
(schreibgeschuetzter Datenordner), bleibt sie still aus.

Datenschutz: haenger.log enthaelt Zeit, Version, Prozessnummer, Seiten- und
Vorgangsnamen, Code-Orte (Datei, Zeile, Funktion) und Kernel-Wartepunkte -
keine Variablenwerte, keine Lerninhalte, keine Zugangsdaten.
"""

import datetime
import faulthandler
import os
import sys
import threading
import time

from fisi_core import resolve_db_path, write_error_log

# Texte (nur PC; Abschnitt im Bereich "Diagnose und Werkzeuge")
TITLE = "Hänger-Diagnose"
HELP = ("Bleibt das Programm hängen, schreibt es nach 30 Sekunden automatisch in die "
        "Datei haenger.log, an welcher Stelle es steht. Blockaden ab 5 Sekunden stehen "
        "kurz in fehler.log, bei bekannten langen Vorgängen (Seitenaufbau, "
        "Darstellungswechsel, Schriftwechsel, Vorladen) erst ab 30 Sekunden. Der "
        "Abgleich läuft im Hintergrund und blockiert nicht. Beide Dateien liegen im "
        "Datenordner und stehen im Problembericht. Es wird nichts gesendet.")
SIGNAL_HELP = ("Ab Version 0.59.2 unter Linux: Hängt das Programm, öffne ein Terminal "
               "und gib diesen Befehl ein. Das Programm schreibt dann in die Datei "
               "haenger.log, an welcher Stelle es gerade steht, und wird dabei nicht "
               "beendet. Achtung: In Version 0.59.1 und älter beendet derselbe Befehl "
               "das Programm.")
KILL_COMMAND = "kill -USR1 $(pgrep -x FISI-Lernplattf | head -1)"
BTN_COPY = "Befehl kopieren"
MSG_COPIED = "Befehl in die Zwischenablage kopiert"
STATE_NONE = "Keine Hänger aufgezeichnet."
STATE_FILE = "haenger.log: %(kb)s KB, zuletzt geändert %(zeit)s"

LOG_NAME = "haenger.log"
LOG_MAX = 512 * 1024          # groesser -> beim Start auf LOG_KEEP kuerzen
LOG_KEEP = 256 * 1024
REPORT_MAX = 16 * 1024        # so viel kommt in den Problembericht

BEAT_MS = 500                 # Herzschlag
ARM_SECONDS = 5.0             # so oft setzt der Herzschlag faulthandler neu
DUMP_AFTER = 30               # erster Stapel nach so viel Stillstand
DUMP_AGAIN = 90               # zweiter Stapel nach weiteren ... s
MAX_AUTO_DUMPS = 3            # automatische Stapel je Sitzung
CHECK_SECONDS = 1.0           # Waechter
BLOCK_SECONDS = 5             # Zeile in fehler.log ab ... s
KNOWN_SECONDS = 30            # ... bei bekannten langen Vorgaengen
KNOWN = ("seite", "darstellung", "schrift", "vorladen", "abgleich")
MAX_LINES = 10                # Blockaden je Sitzung in fehler.log
FREE_SECONDS = 2.0            # Herzschlag juenger -> wieder frei
MEASURE_SECONDS = 2.0
FIRED_MARGIN = 1.5            # erst so lange nach dem Ablauf gilt der Stapel als
                              # geschrieben (sonst koennte das Neusetzen ihn abbrechen)         # Leistungsmessung: Ereignis "blockiert" ab ... s

IDLE = "bereit"

_lock = threading.RLock()
_log = None                   # offene haenger.log (bleibt bis Prozessende offen)
_state = {
    "beat": None,             # monotonic des letzten Herzschlags (None = noch keiner)
    "armed": None,            # monotonic, wann faulthandler zuletzt gesetzt wurde
    "armed_for": 0,           # ... auf wie viele Sekunden
    "auto_dumps": 0,          # schon geschriebene automatische Stapel
    "seite": "",
    "vorgang": IDLE,
    "closing": None,          # Abfrage: schliesst das Programm gerade?
    "lines": 0,               # Blockaden in fehler.log in dieser Sitzung
    "block": None,            # laufende Blockade: {"start", "reported", "dumps"}
    "watching": False,
    "zuletzt": None,          # (vorgang, Ende monotonic) des letzten Vorgangs
}


def _now_text():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_path(folder=None):
    """haenger.log liegt im Datenordner neben der Datenbank."""
    try:
        folder = folder or os.path.dirname(resolve_db_path())
        return os.path.join(folder, LOG_NAME)
    except Exception:
        return None


def _trim(path):
    """Beim Start: groesser als LOG_MAX -> die letzten LOG_KEEP Bytes
    behalten (ab einem Zeilenanfang)."""
    try:
        if os.path.getsize(path) <= LOG_MAX:
            return
        with open(path, "rb") as handle:
            handle.seek(-LOG_KEEP, os.SEEK_END)
            rest = handle.read()
        cut = rest.find(b"\n")
        rest = rest[cut + 1:] if cut >= 0 else rest
        with open(path, "wb") as handle:
            handle.write(rest)
    except OSError:
        pass


def _write(text):
    """Eine Zeile nach haenger.log (mit Uhrzeit); still bei Fehlern."""
    with _lock:
        if _log is None:
            return
        try:
            _log.write("=== %s | %s ===\n" % (_now_text(), text))
            _log.flush()
        except Exception:
            pass


def setup(version="", folder=None, closing=None, platform=None):
    """Beim Start einmal aufrufen (nach install_error_log). Liefert True,
    wenn haenger.log offen ist. closing(): True, waehrend das Programm
    schliesst (der Waechter schweigt dann)."""
    global _log
    platform = platform or sys.platform
    _state["closing"] = closing
    try:
        path = log_path(folder)
        if path and _log is None:
            _trim(path)
            # Python oeffnet nicht vererbbar (O_CLOEXEC bzw. ohne
            # HANDLE_FLAG_INHERIT) - Hilfsprozesse bekommen die Datei nie
            _log = open(path, "a", encoding="utf-8", errors="replace")
            _write("Start | Version %s | %s | pid %d" % (version or "?", platform,
                                                          os.getpid()))
            if platform != "win32":
                faulthandler.enable(file=_log, all_threads=True)
            if hasattr(faulthandler, "register") and platform != "win32":
                import signal
                faulthandler.register(signal.SIGUSR1, file=_log, all_threads=True,
                                      chain=False)
    except Exception:
        _log = None
    _start_watcher()
    return _log is not None


def enabled():
    return _log is not None


def _start_watcher():
    with _lock:
        if _state["watching"]:
            return
        _state["watching"] = True
    try:
        threading.Thread(target=_watch, name="fisi-waechter", daemon=True).start()
    except Exception:
        _state["watching"] = False


def _arm(seconds):
    """faulthandler-Zeitgeber setzen (aus Hauptfaden oder Waechter)."""
    with _lock:
        if _log is None or _state["auto_dumps"] >= MAX_AUTO_DUMPS:
            return
        try:
            faulthandler.dump_traceback_later(seconds, repeat=False, file=_log)
            _state["armed"] = time.monotonic()
            _state["armed_for"] = seconds
        except Exception:
            pass


def beat(now=None):
    """Vom Herzschlag im Hauptfaden aufgerufen. Liefert die Verspaetung in
    Sekunden gegenueber dem geplanten Takt (fuer die Leistungsmessung)."""
    try:
        now = time.monotonic() if now is None else now
        last = _state["beat"]
        _state["beat"] = now
        armed = _state["armed"]
        if armed is None or now - armed >= ARM_SECONDS or _state["armed_for"] != DUMP_AFTER:
            _arm(DUMP_AFTER)
        if last is None:
            return 0.0
        return max(0.0, now - last - BEAT_MS / 1000.0)
    except Exception:
        return 0.0


def seite(name):
    _state["seite"] = str(name or "")


def vorgang(name):
    """Merker fuer den laufenden Vorgang, z. B. "darstellung",
    "vorladen:settings". Liefert den vorherigen (zum Zuruecksetzen)."""
    before = _state["vorgang"]
    name = str(name or IDLE)
    _state["vorgang"] = name
    if before != IDLE and name != before:
        # merken, was zuletzt lief und wann es endete (fuer "blockiert"
        # nach dem Ende des Vorgangs)
        _state["zuletzt"] = (before, time.monotonic())
    return before


def set_closing(closing):
    """closing(): True, waehrend das Programm schliesst."""
    _state["closing"] = closing


def recent(since):
    """Laufender Vorgang oder - wenn gerade keiner laeuft - der letzte, der
    nach since (monotonic) endete; sonst IDLE."""
    task = _state["vorgang"]
    if task != IDLE:
        return task
    last = _state.get("zuletzt")
    if last and last[1] >= since:
        return last[0]
    return IDLE


def current():
    """(seite, vorgang) - fuer Meldungen und die Leistungsmessung."""
    return _state["seite"], _state["vorgang"]


def _known(name):
    return str(name).split(":", 1)[0] in KNOWN


def threads_text(pid="self"):
    """Linux: "tid name Zustand Wartepunkt; ..." aller Threads, sonst ""."""
    base = "/proc/%s/task" % pid
    if not os.path.isdir(base):
        return ""
    parts = []
    try:
        for tid in sorted(os.listdir(base), key=lambda value: int(value)):
            try:
                with open(os.path.join(base, tid, "comm")) as handle:
                    name = handle.read().strip()
                with open(os.path.join(base, tid, "stat")) as handle:
                    state = handle.read().rsplit(")", 1)[1].split()[0]
                with open(os.path.join(base, tid, "wchan")) as handle:
                    wchan = handle.read().strip() or "-"
                parts.append("%s %s %s %s" % (tid, name, state, wchan))
            except (OSError, IndexError):
                continue
    except OSError:
        return ""
    return "; ".join(parts)


def _closing():
    try:
        check = _state["closing"]
        return bool(check and check())
    except Exception:
        return False


def _message(text, age, page, task):
    line = "Hänger-Diagnose: %s (Seite: %s, Vorgang: %s)" % (
        text % {"s": ("%.1f" % age).replace(".", ",")}, page or "-", task)
    waits = threads_text()
    if waits:
        line += "\nWartepunkte: " + waits
    return line


def check(now=None):
    """Ein Durchlauf des Waechters (auch fuer Tests einzeln aufrufbar)."""
    now = time.monotonic() if now is None else now
    last = _state["beat"]
    if last is None:
        return None      # Herzschlag noch nicht gestartet (Programmstart)
    if _closing():
        _state["block"] = None
        return None
    age = now - last
    block = _state["block"]
    if age < FREE_SECONDS:
        if block is not None:
            _state["block"] = None
            if block["reported"] or block["dumps"]:
                text = _message("Hauptfaden wieder frei nach %(s)s s", now - block["start"],
                                block["seite"], block["vorgang"])
                _write(text)
                if block["logged"]:
                    write_error_log(text)
                return "frei"
        return None
    if block is None:
        page, task = current()
        block = {"start": last, "reported": False, "logged": False, "dumps": 0,
                 "seite": page, "vorgang": recent(last)}
        _state["block"] = block
    result = None
    if block["vorgang"] == IDLE:
        block["vorgang"] = _state["vorgang"]
    limit = KNOWN_SECONDS if _known(block["vorgang"]) else BLOCK_SECONDS
    if not block["reported"] and age >= limit:
        block["reported"] = True
        text = _message("Hauptfaden seit %(s)s s ohne Rückruf", age, block["seite"],
                        block["vorgang"])
        _write(text)
        if _state["lines"] < MAX_LINES:
            write_error_log(text)
            block["logged"] = True
        elif _state["lines"] == MAX_LINES:
            write_error_log("Hänger-Diagnose: Weitere Blockaden in dieser Sitzung "
                            "nicht einzeln notiert.")
        _state["lines"] += 1
        result = "blockiert"
    # Stapel: faulthandler hat geschrieben, wenn der Zeitgeber abgelaufen
    # ist, ohne dass ihn jemand neu gesetzt hat
    armed = _state["armed"]
    if armed is not None and now - armed >= _state["armed_for"] + FIRED_MARGIN:
        with _lock:
            if _state["armed"] == armed:
                _state["armed"] = None
                _state["auto_dumps"] += 1
                block["dumps"] += 1
                _write("Stapel %d geschrieben (Hauptfaden seit %d s still, Seite: %s, "
                       "Vorgang: %s)" % (_state["auto_dumps"], int(age),
                                         block["seite"] or "-", block["vorgang"]))
                if block["dumps"] == 1:
                    # Der Herzschlag steht - der Waechter setzt den
                    # zweiten Stapel (einmal je Blockade)
                    _arm(DUMP_AGAIN)
        result = result or "stapel"
    return result


def _watch():
    while True:
        time.sleep(CHECK_SECONDS)
        try:
            check()
        except Exception:
            pass


def dump_on_close(seconds=5):
    """Lebt der Prozess seconds nach dem Schliessen noch, schreibt
    faulthandler die Stapel aller Threads nach haenger.log. Aendert nichts
    am Ablauf (der Notausgang bleibt, wie er ist)."""
    try:
        with _lock:
            if _log is None:
                return
            _write("schliessen")
            faulthandler.dump_traceback_later(seconds, repeat=False, file=_log)
            _state["armed"] = None   # kein automatischer Stapel mehr zaehlen
    except Exception:
        pass


def state_text(path=None):
    """Zustand fuer die Optionen."""
    try:
        path = path or log_path()
        text = _read(path, REPORT_MAX * 4)
        if not text or ('File "' not in text and "Hauptfaden" not in text):
            return STATE_NONE
        when = datetime.datetime.fromtimestamp(os.path.getmtime(path))
        kb = ("%.1f" % (os.path.getsize(path) / 1024.0)).replace(".", ",")
        return STATE_FILE % {"kb": kb, "zeit": when.strftime("%d.%m.%Y %H:%M")}
    except Exception:
        return STATE_NONE


def _read(path, limit):
    try:
        with open(path, "rb") as handle:
            size = os.path.getsize(path)
            if size > limit:
                handle.seek(-limit, os.SEEK_END)
            return handle.read().decode("utf-8", errors="replace")
    except (OSError, TypeError):
        return ""


def tail(path=None, limit=REPORT_MAX):
    """Die letzten limit Bytes von haenger.log fuer den Problembericht
    (ab einem Zeilenanfang), "" ohne Datei. cut: ob gekuerzt wurde."""
    path = path or log_path()
    text = _read(path, limit)
    try:
        cut = os.path.getsize(path) > limit
    except (OSError, TypeError):
        cut = False
    if cut and "\n" in text:
        text = text.split("\n", 1)[1]
    return text.strip(), cut
