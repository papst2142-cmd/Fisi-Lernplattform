#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""0.63.2 A13 (S5c): Tabelle "Bauteil - ms 0625 - ms 0631 - Delta" aus den
p_*.json von profil_oeffnen.py (nur Messung, Zweig messung-0632, nie mergen).

Je Stand und Vorlade-Art: Median ueber die Laeufe (MESS_ART=teile) fuer
oeffnen/Phasen/Widgets, je Bauteil Aufrufe sowie Zeit inklusive und exklusiv,
die Tk-Rueckrufe je Phase; aus den cProfile-Laeufen die exklusive Zeit je
Datei und die groessten kumulierten Eintraege (Median). Sortiert nach dem
groessten Unterschied.
Aufruf: python teile_tabelle.py ORDNER [--vorher 0625] [--nachher 0631] [--notice]"""
import glob
import json
import os
import statistics as st
import sys

FOLDER = sys.argv[1]
NOTICE = "--notice" in sys.argv


def opt(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


VOR, NACH = opt("--vorher", "0625"), opt("--nachher", "0631")
LINES = []


def out(text=""):
    LINES.append(text)
    print(text)


def fmt(v):
    return "-" if v is None else ("%.1f" % v).replace(".", ",")


def med(vals):
    return st.median(vals) if vals else None


runs = {}
for path in sorted(glob.glob(os.path.join(FOLDER, "p_*.json"))):
    with open(path, encoding="utf-8") as h:
        d = json.load(h)
    runs.setdefault((d["art"], d["vorladen"], d["stand"]), []).append(d)

for vorladen in ("0", "normal"):
    t = {s: runs.get(("teile", vorladen, s), []) for s in (VOR, NACH)}
    p = {s: runs.get(("cprofile", vorladen, s), []) for s in (VOR, NACH)}
    if not any(t.values()) and not any(p.values()):
        continue
    out("== FISI_VORLADEN=%s: Laeufe teile %s=%d %s=%d, cprofile %s=%d %s=%d =="
        % (vorladen, VOR, len(t[VOR]), NACH, len(t[NACH]), VOR, len(p[VOR]), NACH, len(p[NACH])))
    ROW = "  %-46s %16s %16s %10s"
    out(ROW % ("Wert (Median der Laeufe, ms)", VOR, NACH, "Delta"))
    for key, name in (("oeffnen_ms", "Oeffnen erstes Mal (mit Zeitmessern)"),
                      ("wieder_ms", "erneut oeffnen")):
        a, b = med([r[key] for r in t[VOR]]), med([r[key] for r in t[NACH]])
        out(ROW % (name, fmt(a), fmt(b), fmt(b - a) if a is not None and b is not None else "-"))
    for ph in ("show_view", "update_idletasks", "update"):
        a = med([r["phasen_ms"][ph] for r in t[VOR]])
        b = med([r["phasen_ms"][ph] for r in t[NACH]])
        out(ROW % ("  Phase " + ph, fmt(a), fmt(b), fmt(b - a) if a is not None and b is not None else "-"))
    for key in ("widgets_rechner", "widgets_fenster"):
        a, b = med([r[key] for r in t[VOR]]), med([r[key] for r in t[NACH]])
        out(ROW % ("Zahl " + key, fmt(a), fmt(b), fmt(b - a) if a is not None and b is not None else "-"))

    namen = sorted({k for s in (VOR, NACH) for r in t[s] for k in r.get("teile", {})})
    zeilen = []
    for k in namen:
        werte = {}
        for s in (VOR, NACH):
            rs = [r["teile"][k] for r in t[s] if k in r.get("teile", {})]
            # fehlt ein Teil in einem Lauf, zaehlt er dort als 0
            werte[s] = {f: med([x[f] for x in rs] + [0] * (len(t[s]) - len(rs))) if t[s] else None
                        for f in ("n", "inkl_ms", "exkl_ms")}
        d = (werte[NACH]["exkl_ms"] or 0) - (werte[VOR]["exkl_ms"] or 0)
        zeilen.append((d, k, werte))
    out("")
    out("  Bauteil (Median; n = Aufrufe)                 %s n / inkl / exkl        %s n / inkl / exkl        Delta exkl"
        % (VOR, NACH))
    for d, k, w in sorted(zeilen, key=lambda z: -abs(z[0])):
        out("  %-44s %4s %8s %8s   %4s %8s %8s   %8s"
            % (k, fmt(w[VOR]["n"]), fmt(w[VOR]["inkl_ms"]), fmt(w[VOR]["exkl_ms"]),
               fmt(w[NACH]["n"]), fmt(w[NACH]["inkl_ms"]), fmt(w[NACH]["exkl_ms"]), fmt(d)))
    summe = {s: med([sum(v["exkl_ms"] for v in r["teile"].values()) for r in t[s]]) for s in (VOR, NACH)}
    out("  %-44s %22s %22s   %8s" % ("Summe exkl aller gemessenen Teile", fmt(summe[VOR]), fmt(summe[NACH]),
                                     fmt(summe[NACH] - summe[VOR]) if summe[VOR] is not None and summe[NACH] is not None else "-"))

    rnamen = sorted({k for s in (VOR, NACH) for r in t[s] for k in r.get("rueckrufe", {})})
    rz = []
    for k in rnamen:
        w = {}
        for s in (VOR, NACH):
            rs = [r["rueckrufe"][k] for r in t[s] if k in r.get("rueckrufe", {})]
            w[s] = (med([x["n"] for x in rs] + [0] * (len(t[s]) - len(rs))) if t[s] else None,
                    med([x["ms"] for x in rs] + [0] * (len(t[s]) - len(rs))) if t[s] else None)
        rz.append(((w[NACH][1] or 0) - (w[VOR][1] or 0), k, w))
    out("")
    out("  Tk-Rueckrufe (Phase|Funktion; Median n / ms), groesste 25 nach Delta")
    for d, k, w in sorted(rz, key=lambda z: -abs(z[0]))[:25]:
        out("  %-70s %4s %8s   %4s %8s   %8s" % (k[:70], fmt(w[VOR][0]), fmt(w[VOR][1]),
                                                fmt(w[NACH][0]), fmt(w[NACH][1]), fmt(d)))

    if any(p.values()):
        out("")
        out("  cProfile: exklusive Zeit je Datei (Median ms)")
        dateien = sorted({k for s in (VOR, NACH) for r in p[s] for k in r.get("je_datei_ms", {})})
        dz = []
        for k in dateien:
            a = med([r["je_datei_ms"].get(k, 0) for r in p[VOR]])
            b = med([r["je_datei_ms"].get(k, 0) for r in p[NACH]])
            dz.append(((b or 0) - (a or 0), k, a, b))
        for d, k, a, b in sorted(dz, key=lambda z: -abs(z[0]))[:20]:
            out("  %-46s %10s %10s %10s" % (k, fmt(a), fmt(b), fmt(d)))
        out("  cProfile: kumuliert (Median ms; nur Eintraege der Top 40)")
        kn = sorted({e[0] for s in (VOR, NACH) for r in p[s] for e in r.get("kumuliert", [])})
        kz = []
        for k in kn:
            vals = {}
            for s in (VOR, NACH):
                vals[s] = med([e[2] for r in p[s] for e in r.get("kumuliert", []) if e[0] == k])
            kz.append(((vals[NACH] or 0) - (vals[VOR] or 0), k, vals))
        for d, k, v in sorted(kz, key=lambda z: -abs(z[0]))[:30]:
            out("  %-70s %10s %10s %10s" % (k[:70], fmt(v[VOR]), fmt(v[NACH]), fmt(d)))
    out("")
if NOTICE:
    for line in LINES:
        if line.strip():
            print("::notice::" + line.replace("%", "%25"))
