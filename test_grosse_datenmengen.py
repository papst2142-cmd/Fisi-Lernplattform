#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Belastungstest: Startet die PC-Version mit kuenstlich vervielfachten
Lerninhalten im Testmodus (jede Ansicht wird einmal geoeffnet) und meldet,
ob sie stabil laeuft. Damit laesst sich vor dem Ergaenzen vieler neuer
Aufgaben pruefen, dass die Oberflaeche auch deutlich mehr Inhalte verkraftet
als heute vorhanden sind.

Aufruf:  python test_grosse_datenmengen.py
         (unter Linux ohne Bildschirm: xvfb-run -a python test_grosse_datenmengen.py)

Die echten Inhalte in inhalte/ und die Lern-Datenbank bleiben unveraendert:
Die Kopien existieren nur im Arbeitsspeicher, die Datenbank liegt in einem
temporaeren Ordner.
"""

import copy
import os
import sys
import tempfile
import time

# Deutlich mehr als das Ziel von 4000 Aufgaben
TARGETS = {
    "KARTEIKARTEN": ("q", 2000),
    "QUIZ_QUESTIONS": ("q", 3000),
    "AP1_SZENARIEN": ("title", 1000),
    "SZENARIEN": ("title", 1000),
    "PROJEKTARBEITEN": ("title", 300),
}


def grow(items, key, count):
    """Vervielfacht eine Liste bis count Eintraege (Titel eindeutig)."""
    base = list(items)
    while len(items) < count:
        for item in base:
            if len(items) >= count:
                break
            clone = copy.deepcopy(item)
            clone[key] = "%s (Kopie %d)" % (clone[key], len(items) + 1)
            items.append(clone)


def main():
    temp = tempfile.mkdtemp(prefix="fisi-belastungstest-")
    # Eigene, leere Datenbank statt der echten Lern-Datenbank
    os.environ["XDG_DATA_HOME"] = temp
    os.environ["APPDATA"] = temp
    os.environ["HOME"] = temp
    os.environ["FISI_SELFTEST"] = log_path = os.path.join(temp, "selftest.log")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    import fisi_core
    for name, (key, count) in TARGETS.items():
        grow(getattr(fisi_core, name), key, count)
    print("Testdaten: " + ", ".join("%s %d" % (name, len(getattr(fisi_core, name)))
                                    for name in TARGETS))

    import app_gui
    started = time.time()
    try:
        app_gui.main()
    except SystemExit:
        pass
    with open(log_path, encoding="utf-8") as handle:
        result = handle.read().strip()
    print("Dauer: %.1f s" % (time.time() - started))
    if result != "OK":
        print("FEHLER:\n" + result)
        sys.exit(1)
    print("Belastungstest OK")


if __name__ == "__main__":
    main()
