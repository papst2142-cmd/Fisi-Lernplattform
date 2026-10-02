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
                "fisi_pdf.py", "fisi_sicherung.py", "fisi_diagnose.py"]
SHARED_DIRS = ["inhalte"]


def main():
    for name in SHARED_FILES:
        shutil.copy2(os.path.join(ROOT, name), os.path.join(SRC, name))
        print("kopiert:", name)
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
