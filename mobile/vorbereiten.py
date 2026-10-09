#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kopiert die gemeinsamen Dateien der PC-Version nach mobile/src, damit
"flet build apk" sie in die Handy-App packt. Die Kopien stehen in .gitignore -
gepflegt wird nur das Original im Hauptordner.

Aufruf:  python mobile/vorbereiten.py
"""

import os
import shutil
import sys

MOBILE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(MOBILE)
SRC = os.path.join(MOBILE, "src")
SHARED_FILES = ["fisi_core.py", "fisi_theme.py", "fisi_update.py", "fisi_sync.py",
                "fisi_game.py", "fisi_lernen.py", "fisi_pruefung.py", "fisi_projekt.py",
                "fisi_pdf.py", "fisi_sicherung.py", "fisi_diagnose.py", "fisi_rahmenplan.py",
                "fisi_hilfe.py",   # ab 0.56: Rundgang und Hilfe
                "fisi_leistung.py",   # ab 0.58.1: Leistungsmessung
                "fisi_optionen.py",   # ab 0.59: Aufbau und Suche der Optionen
                "fisi_rechtliches.py",   # ab 0.62: Lizenz, Hinweistext, Erststart
                "LICENSE.txt"]
SHARED_DIRS = ["inhalte"]
# Ab 0.62: Hinweise zu Fremdbestandteilen der Handy-App. Die Datei im Repo
# erzeugt pruefung/lizenzen_android.py aus der APK (Weg B), in der App heisst
# sie wie am PC.
NOTICES = (os.path.join("mobile", "lizenzen_android.txt"), "THIRD_PARTY_NOTICES.txt")


def main():
    for name in SHARED_FILES:
        shutil.copy2(os.path.join(ROOT, name), os.path.join(SRC, name))
        print("kopiert:", name)
    shutil.copy2(os.path.join(ROOT, NOTICES[0]), os.path.join(SRC, NOTICES[1]))
    print("kopiert:", NOTICES[0], "->", NOTICES[1])
    for name in SHARED_DIRS:
        target = os.path.join(SRC, name)
        if os.path.isdir(target):
            shutil.rmtree(target)
        shutil.copytree(os.path.join(ROOT, name), target)
        print("kopiert:", name + "/")

    sys.path.insert(0, SRC)
    from fisi_core import validate_content
    problems = validate_content()
    if problems:
        print("\n".join(problems), file=sys.stderr)
        sys.exit(1)
    print("Inhalte geprueft: OK")


if __name__ == "__main__":
    main()
