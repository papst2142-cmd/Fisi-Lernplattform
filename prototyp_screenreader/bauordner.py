#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Legt prototyp_screenreader/bau/ an, damit "flet build windows" den Prototyp
als eigenstaendiges Windows-Programm baut (fuer den NVDA-Test ohne Python).
Nur fuer den Zweig proto-screenreader; kein Teil des Programms.

Aufruf (im Hauptordner):  python prototyp_screenreader/bauordner.py
"""

import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(HERE, "bau")
SRC = os.path.join(BUILD, "src")
sys.path.insert(0, os.path.join(ROOT, "mobile"))
from vorbereiten import SHARED_DIRS, SHARED_FILES  # noqa: E402  (dieselbe Liste wie am Handy)


def main():
    if os.path.isdir(BUILD):
        shutil.rmtree(BUILD)
    os.makedirs(SRC)
    shutil.copy2(os.path.join(HERE, "optionen_flet.py"), os.path.join(SRC, "main.py"))
    shutil.copy2(os.path.join(HERE, "pyproject.toml"), os.path.join(BUILD, "pyproject.toml"))
    for name in SHARED_FILES:
        shutil.copy2(os.path.join(ROOT, name), os.path.join(SRC, name))
    for name in SHARED_DIRS:
        shutil.copytree(os.path.join(ROOT, name), os.path.join(SRC, name))
    print("Bauordner fertig:", BUILD)


if __name__ == "__main__":
    main()
