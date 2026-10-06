#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FISI Lernplattform - Sperre gegen Mehrfachstart (ab 0.59.1)
===========================================================

Ein zweiter Start oeffnet kein zweites Fenster, sondern holt das laufende
nach vorn (auch aus dem minimierten Zustand). Nur PC unter Linux und
Windows; macOS startet eine laufende App ohnehin nicht zweimal, das Handy
ist nicht betroffen.

Sperre: die Datei "laeuft.lock" im Datenordner (neben der Datenbank),
gesperrt mit flock (Linux) bzw. msvcrt.locking (Windows). Das Betriebssystem
gibt die Sperre mit dem Prozess frei, auch nach einem Absturz - es gibt
nichts aufzuraeumen. Jeder Benutzer und jede abweichende Datenbank
(FISI_DB_PATH) hat so eine eigene Sperre.

Kanal: Der zweite Start legt "vordergrund-<pid>.signal" an und wartet
ANSWER_SECONDS auf "vordergrund-<pid>.antwort":
  "da"     - das Fenster ist nach vorn geholt, der zweite Start endet still
             (wird die Sperre in den naechsten ANSWER_SECONDS doch frei,
             startet er trotzdem - Sicherheitsnetz fuer das AppImage-Update)
  "endet"  - das Programm schliesst gerade (auch fuer ein Update): warten,
             bis die Sperre frei ist, dann normal starten
  keine    - ebenso warten. Ist die Sperre nach LOCK_SECONDS noch belegt,
             startet das Programm trotzdem (wie in 0.59) und notiert das in
             fehler.log.

Grundsatz: Die Sperre verhindert den Start nie. Geht beim Anlegen oder
Pruefen etwas schief, startet das Programm normal. Beendet wird ein zweiter
Start nur, wenn das laufende Programm mit "da" geantwortet hat.

Waehrend des Starts antwortet ein Hintergrund-Thread (das Fenster kommt
gleich ohnehin), danach der Zeitgeber im Hauptfenster (listen). Haengt das
Hauptfenster, bleibt die Antwort aus und es gilt "keine". Update-Ablauf und
Schliesslogik bleiben unveraendert: on_close bricht den Zeitgeber wie alle
anderen ab.
"""

import glob
import os
import sys
import threading
import time

from fisi_core import resolve_db_path, write_error_log

LOCK_FILE = "laeuft.lock"
SIGNAL_SUFFIX = ".signal"
ANSWER_SUFFIX = ".antwort"
PREFIX = "vordergrund-"
ANSWER_HERE = "da"
ANSWER_ENDING = "endet"

ANSWER_SECONDS = 3      # so lange wartet ein zweiter Start auf die Antwort
LOCK_SECONDS = 25       # 12 s Abgleich beim Beenden + 8 s Notausgang + Reserve
STEP_SECONDS = 0.1
POLL_MS = 400           # Abfrage im laufenden Programm
STALE_SECONDS = 60      # liegengebliebene Signal-/Antwortdateien

_lock_handle = None     # bleibt bis zum Prozessende offen (= Sperre)
_startup_answering = None


class _Busy(Exception):
    """Die Sperre haelt ein anderer Prozess."""


def supported(platform=None):
    platform = platform or sys.platform
    return platform.startswith("linux") or platform == "win32"


def data_folder():
    return os.path.dirname(resolve_db_path())


def _lock(handle):
    """Sperrt handle ohne zu warten. _Busy = belegt, jeder andere Fehler
    bedeutet: Sperre unbekannt."""
    if os.name == "nt":
        import errno
        import msvcrt
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            if error.errno in (errno.EACCES, errno.EDEADLK):
                raise _Busy()
            raise
    else:
        import fcntl
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise _Busy()


def _try_lock(folder):
    """Liefert die gesperrte Datei, _Busy oder wirft OSError (unbekannt)."""
    handle = open(os.path.join(folder, LOCK_FILE), "a+")
    try:
        _lock(handle)
    except BaseException:
        handle.close()
        raise
    return handle


def _answer_path(folder, token):
    return os.path.join(folder, PREFIX + token + ANSWER_SUFFIX)


def _write_answer(folder, token, text):
    path = _answer_path(folder, token)
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(temp, path)


def _remove(path):
    try:
        os.remove(path)
    except OSError:
        pass


def _signals(folder):
    """Tokens der wartenden zweiten Starts."""
    found = []
    for path in glob.glob(os.path.join(folder, PREFIX + "*" + SIGNAL_SUFFIX)):
        name = os.path.basename(path)
        found.append(name[len(PREFIX):-len(SIGNAL_SUFFIX)])
    return found


def answer_signals(folder, closing):
    """Beantwortet alle wartenden zweiten Starts. Liefert True, wenn das
    Fenster nach vorn geholt werden soll."""
    tokens = _signals(folder)
    for token in tokens:
        _remove(os.path.join(folder, PREFIX + token + SIGNAL_SUFFIX))
        try:
            _write_answer(folder, token, ANSWER_ENDING if closing else ANSWER_HERE)
        except OSError:
            pass
    return bool(tokens) and not closing


def _clean_stale(folder, now=None):
    now = time.time() if now is None else now
    for pattern in (PREFIX + "*" + SIGNAL_SUFFIX, PREFIX + "*" + ANSWER_SUFFIX,
                    PREFIX + "*" + ANSWER_SUFFIX + ".tmp"):
        for path in glob.glob(os.path.join(folder, pattern)):
            try:
                if now - os.path.getmtime(path) > STALE_SECONDS:
                    os.remove(path)
            except OSError:
                pass


def _allow_foreground():
    """Windows laesst nur den Prozess im Vordergrund ein Fenster nach vorn
    holen. Der zweite Start ist es gerade (der Benutzer hat ihn geoeffnet)
    und reicht das Recht weiter (ASFW_ANY)."""
    if os.name != "nt":
        return
    try:
        import ctypes
        ctypes.windll.user32.AllowSetForegroundWindow(-1)
    except Exception:
        pass


def _wait_for_answer(folder, token, seconds):
    path = _answer_path(folder, token)
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            with open(path, encoding="utf-8") as handle:
                text = handle.read().strip()
            _remove(path)
            return text
        except OSError:
            time.sleep(STEP_SECONDS)
    return None


def _wait_for_lock(folder, seconds):
    """Versucht bis zu seconds lang die Sperre zu bekommen."""
    end = time.monotonic() + seconds
    while True:
        try:
            return _try_lock(folder)
        except _Busy:
            if time.monotonic() >= end:
                return None
            time.sleep(STEP_SECONDS)


def claim(folder=None, answer_seconds=None, lock_seconds=None):
    """Beim Start vor allem anderen aufrufen. True = normal starten,
    False = ein laufendes Programm wurde nach vorn geholt, still beenden."""
    global _lock_handle
    if _lock_handle is not None:
        return True
    answer_seconds = ANSWER_SECONDS if answer_seconds is None else answer_seconds
    lock_seconds = LOCK_SECONDS if lock_seconds is None else lock_seconds
    try:
        folder = folder or data_folder()
        try:
            _lock_handle = _try_lock(folder)
        except _Busy:
            handle = _second_start(folder, answer_seconds, lock_seconds)
            if handle is False:
                return False
            _lock_handle = handle
        if _lock_handle is not None:
            _clean_stale(folder)
            _start_answering(folder)
    except Exception as error:
        # Grundsatz: nie den Start verhindern
        write_error_log("Sperre gegen Mehrfachstart nicht verfuegbar, Start ohne "
                        "Sperre: %r" % (error,))
    return True


def _second_start(folder, answer_seconds, lock_seconds):
    """Die Sperre ist belegt. Liefert False (beenden), die Sperre oder None
    (ohne Sperre starten)."""
    token = "%d-%d" % (os.getpid(), int(time.time() * 1000))
    signal = os.path.join(folder, PREFIX + token + SIGNAL_SUFFIX)
    _allow_foreground()
    with open(signal, "w", encoding="utf-8"):
        pass
    answer = _wait_for_answer(folder, token, answer_seconds)
    _remove(signal)
    if answer == ANSWER_HERE:
        # Sicherheitsnetz: Endet das laufende Programm gerade doch (Update),
        # ist die Sperre gleich frei - dann selbst starten.
        handle = _wait_for_lock(folder, answer_seconds)
        return handle if handle is not None else False
    handle = _wait_for_lock(folder, lock_seconds)
    if handle is None:
        write_error_log("Mehrfachstart: Das laufende Programm hat nicht geantwortet "
                        "(Antwort: %s) und die Sperre war nach %d s noch belegt. "
                        "Start ohne Sperre." % (answer or "keine", lock_seconds))
    return handle


def _start_answering(folder):
    """Bis listen() uebernimmt: zweite Starts im Hintergrund mit "da"
    beantworten - das Fenster erscheint ohnehin gleich."""
    global _startup_answering
    stop = threading.Event()

    def run():
        while not stop.wait(POLL_MS / 1000.0):
            try:
                answer_signals(folder, closing=False)
            except Exception:
                pass
    threading.Thread(target=run, name="fisi-einzelstart", daemon=True).start()
    _startup_answering = (folder, stop)


def listen(root, closing, bring_to_front):
    """Ab hier antwortet das Hauptfenster (alle POLL_MS ms). closing() liefert
    True, wenn das Programm gerade schliesst oder fuer ein Update endet."""
    global _startup_answering
    if _startup_answering is None:
        return
    folder, stop = _startup_answering
    stop.set()
    _startup_answering = None

    def poll():
        try:
            if answer_signals(folder, closing=closing()):
                bring_to_front()
        except Exception:
            pass
        root.after(POLL_MS, poll)
    root.after(POLL_MS, poll)


def bring_to_front(root):
    """Fenster zeigen (auch aus dem minimierten Zustand), nach oben legen und
    den Fokus anfordern. Unter Windows kurz "immer oben", damit es auch
    ohne Fokus ueber den anderen Fenstern liegt; GNOME (Wayland) zeigt
    statt des Fokuswechsels unter Umstaenden "... ist bereit"."""
    root.deiconify()
    root.lift()
    if os.name == "nt":
        root.attributes("-topmost", True)
        root.after_idle(root.attributes, "-topmost", False)
    root.focus_force()
