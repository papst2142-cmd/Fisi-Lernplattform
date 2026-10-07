#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FISI Lernplattform - Eingabemethoden-Umgehung (ab 0.59.3, nur PC, Linux)
=========================================================================

Unter Linux mit Wayland (das Programm laeuft dort ueber XWayland) und der
X-Eingabemethode von IBus (XMODIFIERS=@im=ibus) kann das Programm dauerhaft
einfrieren: Tk legt fuer neue Fenster einen Eingabekontext an (XCreateIC),
ibus-x11 fragt dafuer ibus-daemon, die Anfrage laeuft in einen Timeout und
ibus-x11 antwortet Tk nie. Tk wartet dann unendlich (belegt auf Nicos
Ubuntu-26.04-VM und im Container mit angehaltenem ibus-daemon).

Abhilfe: Vor dem ersten Fenster XMODIFIERS=@im=none setzen. Xlib nimmt dann
seine eingebaute Eingabemethode (Compose-Tabelle der Sprache) - deutsche
Zeichen, AltGr, tote Tasten und Compose gehen weiter, nur die IBus-Extras
(z. B. Chinesisch, Emoji-Fenster) fehlen im Programm.

Greift nur, wenn ALLE Bedingungen gelten:
  * Linux
  * Wayland-Sitzung: XDG_SESSION_TYPE=wayland oder WAYLAND_DISPLAY gesetzt
  * XMODIFIERS enthaelt "@im=ibus"
  * Schalter FISI_XIM ist nicht "1" (FISI_XIM=1 laesst alles wie bisher)
Unter Windows, macOS und allen anderen Linux-Konstellationen aendert sich
nichts.

Die Variable gilt fuer den ganzen Prozess, also auch fuer Programme, die
FISI selbst startet (Ordner, Browser). Sie wird bewusst NICHT
zurueckgesetzt (Entscheidung Nico 07.10.2026): Ob Tk die Eingabemethode
spaeter (z. B. nach einem Neustart von IBus) neu oeffnet und die Variable
dann noch einmal liest, ist nicht geprueft. Ein Neustart nach einem Update
prueft die Bedingungen selbst neu (er erbt "@im=none", die Umgehung ist
dann schon wirksam).

apply() nur einmal je Prozess wirksam; spaetere Aufrufe liefern das erste
Ergebnis und aendern nichts. Fehler werden geschluckt - im Zweifel bleibt
alles wie bisher.
"""

import os
import sys

SWITCH = "FISI_XIM"          # =1: Umgehung aus
IM_IBUS = "@im=ibus"
IM_NONE = "@im=none"
MESS_TASK = "eingabe-umgehung"   # Spalte "vorgang" der Startzeile der Messdatei
# Grund, wenn XMODIFIERS schon @im=none ist - z. B. beim Neustart nach einem
# Update, der die Umgebung des alten Prozesses erbt (Abnahme 0.59.3, A1)
GRUND_SCHON_NONE = "schon @im=none (geerbt oder von Hand)"

_result = None


def wanted(environ, platform):
    """(aktiv, Grund) nach den Bedingungen oben - aendert nichts."""
    if not str(platform).startswith("linux"):
        return False, "kein Linux"
    wayland = (environ.get("XDG_SESSION_TYPE", "").strip().lower() == "wayland"
               or bool(environ.get("WAYLAND_DISPLAY")))
    if not wayland:
        return False, "keine Wayland-Sitzung"
    modifiers = environ.get("XMODIFIERS", "")
    if IM_IBUS not in modifiers:
        if IM_NONE in modifiers:
            return False, GRUND_SCHON_NONE
        return False, "kein IBus"
    if environ.get(SWITCH, "").strip() == "1":
        return False, "%s=1" % SWITCH
    return True, ""


def apply(environ=None, platform=None):
    """Beim Start vor dem ersten Fenster aufrufen. Liefert ein dict:
    aktiv (bool), grund, sitzung, vorher, nachher (XMODIFIERS; None = nicht
    gesetzt)."""
    global _result
    if _result is not None:
        return _result
    environ = os.environ if environ is None else environ
    platform = sys.platform if platform is None else platform
    result = {"aktiv": False, "grund": "", "sitzung": "", "vorher": None,
              "nachher": None}
    try:
        result["sitzung"] = environ.get("XDG_SESSION_TYPE", "") or (
            "wayland" if environ.get("WAYLAND_DISPLAY") else "")
        result["vorher"] = environ.get("XMODIFIERS")
        active, reason = wanted(environ, platform)
        if active:
            environ["XMODIFIERS"] = IM_NONE
        result["aktiv"] = active
        result["grund"] = reason
        result["nachher"] = environ.get("XMODIFIERS")
    except Exception:  # noqa: BLE001 - nie den Start stoeren
        pass
    _result = result
    return result


def result():
    """Ergebnis von apply() oder None, wenn es noch nicht lief."""
    return _result


def start_text(info=None):
    """Teil fuer die Startzeile in haenger.log."""
    info = info or _result
    if not info:
        return ""
    if not info.get("aktiv"):
        text = "Eingabe-Umgehung nein"
        if info.get("grund"):
            text += " (%s)" % info["grund"]
        if info.get("vorher"):
            text = "XMODIFIERS %s | %s" % (info["vorher"], text)
        if info.get("sitzung"):
            text = "Sitzung %s | %s" % (info["sitzung"], text)
        return text
    return "Sitzung %s | XMODIFIERS %s -> %s | Eingabe-Umgehung aktiv" % (
        info.get("sitzung") or "?", info.get("vorher") or "-", info.get("nachher") or "-")


def _reset_for_tests():
    global _result
    _result = None
