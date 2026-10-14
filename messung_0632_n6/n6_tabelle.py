#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""N6 Tabelle: Median/Max je Stand und Fall aus n6_messung.py-Zeilen.
Aufruf: python n6_tabelle.py DATEI_ODER_LOG...   (liest JSON-Zeilen, auch
"ROHN6 {...}" aus einem Job-Log). Grenze 150 ms (Weisung N6-F5) markiert."""
import json
import re
import statistics
import sys
from collections import defaultdict

GRENZE = 150.0
rows = []
for path in sys.argv[1:]:
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = re.search(r"(\{\"modus\".*\})\s*$", line)
            if m:
                rows.append(json.loads(m.group(1)))


def med(v):
    v = [x for x in v if x is not None]
    return (round(statistics.median(v), 1), round(max(v), 1), len(v)) if v else ("-", "-", 0)


def fmt(t):
    flag = " *" if isinstance(t[1], float) and t[1] > GRENZE else ""
    return f"{t[0]:>7} / {t[1]:>7} (n={t[2]}){flag}"


wechsel = defaultdict(lambda: defaultdict(list))
for r in rows:
    if r["art"] == "wechsel":
        k = (r["fall"], r["stand"])
        for f in ("bedienbar_ms", "fertig_ms", "laengstes_ereignis_abbau_ms", "laengstes_ereignis_3s_ms"):
            wechsel[k][f].append(r.get(f))
if wechsel:
    print("== wechsel: Median / Max in ms (* = Max ueber %d ms)" % GRENZE)
    for k in sorted(wechsel):
        print(f"{k[0]:<15} {k[1]:<10} " + "  ".join(
            f"{f.replace('_ms', '')}: {fmt(med(v))}" for f, v in wechsel[k].items()))

start = defaultdict(lambda: defaultdict(list))
for r in rows:
    if r["art"] == "start":
        s = start[r["stand"]]
        s["fertig_ms"].append(r.get("fertig_ms"))
        s["laengste_blockade_ms"].append(r.get("laengste_blockade_ms"))
        for name, ms in (r.get("schritte") or {}).items():
            s["schritt " + name].append(ms)
if start:
    print("== start: Median / Max in ms (* = Max ueber %d ms)" % GRENZE)
    for stand, s in sorted(start.items()):
        for f, v in sorted(s.items()):
            print(f"{stand:<10} {f:<40} {fmt(med(v))}")
