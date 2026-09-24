#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FISI Lernplattform - Startprogramm
==================================

Diese Datei ist der Einstiegspunkt. Sie prueft zuerst, ob alle
Voraussetzungen erfuellt sind, und gibt sonst eine verstaendliche Meldung
aus, statt mit einem unverstaendlichen Fehler abzubrechen.

Aufruf:  python3 start.py      (Linux/macOS)
         python start.py       (Windows)
"""

import os
import sys

MIN_PYTHON = (3, 8)


def fail(title, message):
    """Meldet einen Startfehler - moeglichst als Fenster, sonst im Terminal."""
    text = "%s\n\n%s" % (title, message)
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("FISI Lernplattform", text)
        root.destroy()
    except Exception:
        print(text, file=sys.stderr)
    sys.exit(1)


def main():
    if sys.version_info < MIN_PYTHON:
        fail("Python-Version zu alt",
             "Benoetigt wird mindestens Python %d.%d, gefunden wurde %d.%d.\n\n"
             "Bitte eine aktuelle Python-Version von python.org installieren."
             % (MIN_PYTHON[0], MIN_PYTHON[1],
                sys.version_info[0], sys.version_info[1]))

    try:
        import tkinter  # noqa: F401
    except ImportError:
        hint = ("Unter Debian/Ubuntu laesst sich das mit folgendem Befehl "
                "nachinstallieren:\n\n    sudo apt install python3-tk\n\n"
                "Unter Fedora:\n\n    sudo dnf install python3-tkinter")
        if os.name == "nt":
            hint = ("Bitte Python neu installieren und dabei die Option\n"
                    "\"tcl/tk and IDLE\" aktiviert lassen.")
        fail("Tkinter fehlt",
             "Die grafische Oberflaeche benoetigt Tkinter.\n\n" + hint)

    # Das Programmverzeichnis in den Suchpfad legen, damit die Module auch
    # gefunden werden, wenn das Programm aus einem anderen Ordner gestartet
    # wird (z.B. ueber eine Verknuepfung).
    base = os.path.dirname(os.path.abspath(__file__))
    if base not in sys.path:
        sys.path.insert(0, base)

    try:
        import app_gui
    except ImportError as exc:
        fail("Programmdateien unvollstaendig",
             "Ein Modul konnte nicht geladen werden:\n\n%s\n\n"
             "Bitte sicherstellen, dass app_gui.py, fisi_core.py und "
             "fisi_widgets.py im selben Ordner liegen." % exc)
        return

    app_gui.main()


if __name__ == "__main__":
    main()
