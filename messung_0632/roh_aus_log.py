#!/usr/bin/env python3
"""Messung 0.63.1 (in 0.63.2 auch p_*.json aus profil_oeffnen.py): Zeilen "ROH <datei> <json>" aus einem Job-Log (Windows-
Messlauf, messung-0631.yml) als einzelne JSON-Dateien ablegen, damit
tabelle_0631.py sie lokal auswerten kann.
Aufruf: python roh_aus_log.py JOBLOG ZIELORDNER"""
import json
import os
import re
import sys

log, ziel = sys.argv[1], sys.argv[2]
os.makedirs(ziel, exist_ok=True)
n = 0
with open(log, encoding="utf-8", errors="replace") as handle:
    for line in handle:
        found = re.search(r"ROH ([mp]_\S+\.json) (\{.*\})\s*$", line)
        if found:
            data = json.loads(found.group(2))
            with open(os.path.join(ziel, found.group(1)), "w", encoding="utf-8") as out:
                json.dump(data, out, indent=1)
            n += 1
print("%d Rohdateien nach %s" % (n, ziel))
