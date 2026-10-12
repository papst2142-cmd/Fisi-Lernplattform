#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T7 0.63: Tabelle und Grenzen (nur Messung, kein Teil des Programms).

Liest die Ergebnisse von mess_rechner_063.py (*.json mit "fassung") aus einem
Ordner und prueft die Grenzen aus Plan 0.63 Abschnitt 8.2:

  G1 Oeffnen (erstes Mal und erneut), je Vorlade-Art:
     Median nachher <= hoechster Wert vorher (aus DIESER Messung)
  G2 Moduswechsel IPv4<->IPv6, je Vorlade-Art: Median (Mittel je Lauf und
     alle Einzelwechsel) <= Grenze; Grenze = --grenze-modus MS (Container:
     137,2 aus Plan 8.1) oder sonst hoechster Mittelwert Reiterwechsel vorher
     (beide Vorlade-Arten, aus dieser Messung); kein Einzelwechsel > 500 ms
  G3 erster Wechsel ohne Vorladen: nur berichtet, > 300 ms markiert
  G4 Rechnen und Blaettern ohne Oberflaeche (T-K-6): jede Seite < 50 ms;
     die Werte mit Oberflaeche werden berichtet (> 50 ms markiert)

Aufruf: python tabelle_063.py ORDNER [--notice] [--grenze-modus MS]
        [--plan-oeffnen NORMAL,OHNE]   (zusaetzlicher Vergleich mit Plan 8.2)
Rueckgabe 0; die Zeile "GRENZEN: alle erfuellt" bzw. "GRENZEN: GERISSEN ..."
steht am Ende."""
import glob
import json
import os
import statistics as st
import sys

FOLDER = sys.argv[1]
NOTICE = "--notice" in sys.argv


def opt(name):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return None


GRENZE_MODUS = opt("--grenze-modus")
PLAN_OEFFNEN = opt("--plan-oeffnen")
ARTEN = ("normal", "0")
ARTNAME = {"normal": "mit Vorladen", "0": "ohne Vorladen"}
LINES = []
GERISSEN = []


def out(text=""):
    LINES.append(text)
    print(text)


def fmt(v):
    return ("%.1f" % v).replace(".", ",") if v is not None else "-"


def spanne(vals):
    if not vals:
        return "keine Werte"
    return "%s (%s-%s), n=%d" % (fmt(st.median(vals)), fmt(min(vals)), fmt(max(vals)), len(vals))


runs = {}
for path in sorted(glob.glob(os.path.join(FOLDER, "*.json"))):
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception:   # noqa: BLE001
        continue
    if "fassung" not in data:
        continue
    runs.setdefault((data["fassung"], data["vorladen"]), []).append(data)

out("Laeufe: " + ", ".join("%s/%s=%d" % (f, ARTNAME[a], len(runs.get((f, a), [])))
                            for f in ("vor", "nach") for a in ARTEN))
for f in ("vor", "nach"):
    for a in ARTEN:
        if len(runs.get((f, a), [])) != 7:
            GERISSEN.append("UNVOLLSTAENDIG %s/%s: %d statt 7 Laeufe"
                            % (f, ARTNAME[a], len(runs.get((f, a), []))))


def col(f, a, key):
    return [r[key] for r in runs.get((f, a), []) if r.get(key) is not None]


def flat(f, a, key):
    return [x for r in runs.get((f, a), []) for x in r.get(key, [])]


out("")
out("Tabelle: Median (min-max), n   [ms]")
for a in ARTEN:
    out("== %s (FISI_VORLADEN=%s) ==" % (ARTNAME[a], a))
    for f in ("vor", "nach"):
        rs = runs.get((f, a), [])
        out("  %s: calc vorgeladen %s, ipv6 vorgebaut %s, IPv6-Eingabe geprueft %s"
            % (f, sorted({r["calc_vorgeladen"] for r in rs}),
               sorted({r.get("ipv6_vorgebaut") for r in rs}, key=str),
               sorted({r.get("ipv6_eingabe_geprueft") for r in rs}, key=str)))
    for key, name in (("oeffnen_ms", "Rechner oeffnen (erstes Mal)"),
                      ("wieder_ms", "Rechner erneut oeffnen"),
                      ("reiter_ms", "Reiterwechsel, Mittel aus 6 je Lauf"),
                      ("rechnen_ms", "Berechnen IPv4"),
                      ("rechnen6_ms", "Berechnen IPv6"),
                      ("rechenweg_ms", "Rechenweg IPv4 einblenden")):
        out("  %-38s vorher %-28s nachher %s" % (name, spanne(col("vor", a, key)),
                                                   spanne(col("nach", a, key))))
    out("  %-38s vorher %-28s nachher %s" % ("Reiterwechsel einzeln",
                                              spanne(flat("vor", a, "reiter_einzeln_ms")),
                                              spanne(flat("nach", a, "reiter_einzeln_ms"))))
    for key, name in (("erster_wechsel_ms", "Erster Wechsel IPv4->IPv6"),
                      ("modus_ms", "Moduswechsel, Mittel aus 6 je Lauf"),
                      ("rechenweg6_ms", "Rechenweg IPv6 einblenden")):
        out("  %-38s nachher %s" % (name, spanne(col("nach", a, key))))
    out("  %-38s nachher %s" % ("Moduswechsel einzeln", spanne(flat("nach", a, "modus_einzeln_ms"))))
    for i, netz in ((0, "::/0 in 2^64"), (1, "10.0.0.0/8 in 2^24")):
        ber = [r["blaettern"][i]["berechnen_ms"] for r in runs.get(("nach", a), [])]
        seite = [v for r in runs.get(("nach", a), []) for v in r["blaettern"][i]["seite_ms"].values()]
        out("  %-38s nachher %s" % ("Aufteilen %s Berechnen (Oberfl.)" % netz, spanne(ber)))
        out("  %-38s nachher %s" % ("Aufteilen %s je Seite (Oberfl.)" % netz, spanne(seite)))
    kern = [v for r in runs.get(("nach", a), []) for fall in r["kern"]
            for k, v in fall.items() if k.endswith("_ms")]
    out("  %-38s nachher %s" % ("Kern ohne Oberfl. (T-K-6), alle Werte", spanne(kern)))

out("")
out("Grenzen (Plan 0.63 Abschnitt 8.2)")
plan = None
if PLAN_OEFFNEN:
    plan = dict(zip(ARTEN, (float(x) for x in PLAN_OEFFNEN.split(","))))
for a in ARTEN:
    for key, name in (("oeffnen_ms", "Oeffnen erstes Mal"), ("wieder_ms", "Oeffnen erneut")):
        vor, nach = col("vor", a, key), col("nach", a, key)
        if not vor or not nach:
            continue
        ok = st.median(nach) <= max(vor)
        out("  G1 %-20s %-14s Median nachher %s <= hoechster vorher %s: %s"
            % (name, ARTNAME[a], fmt(st.median(nach)), fmt(max(vor)), "ja" if ok else "NEIN"))
        if not ok:
            GERISSEN.append("G1 %s %s" % (name, ARTNAME[a]))
        if plan and key == "oeffnen_ms":
            out("     (zusaetzlich Plan-Zahl bdc6126: <= %s: %s, nur berichtet)"
                % (fmt(plan[a]), "ja" if st.median(nach) <= plan[a] else "nein"))
reiter_max_vor = max(col("vor", "normal", "reiter_ms") + col("vor", "0", "reiter_ms") or [0])
if GRENZE_MODUS:
    grenze = float(GRENZE_MODUS)
    herkunft = "Plan 8.1 (Container bdc6126)"
else:
    grenze = reiter_max_vor
    herkunft = "hoechster Mittelwert Reiterwechsel vorher, diese Messung"
out("  G2 Grenze Moduswechsel %s ms (%s); hoechster Reiter-Mittelwert vorher in dieser Messung %s ms"
    % (fmt(grenze), herkunft, fmt(reiter_max_vor)))
for a in ARTEN:
    mittel, einzeln = col("nach", a, "modus_ms"), flat("nach", a, "modus_einzeln_ms")
    if not mittel:
        continue
    ok1 = st.median(mittel) <= grenze
    ok2 = st.median(einzeln) <= grenze
    ok3 = max(einzeln) <= 500
    out("  G2 Moduswechsel %-14s Median Mittel %s, Median einzeln %s <= %s: %s; groesster Einzelwechsel %s <= 500: %s"
        % (ARTNAME[a], fmt(st.median(mittel)), fmt(st.median(einzeln)), fmt(grenze),
           "ja" if ok1 and ok2 else "NEIN", fmt(max(einzeln)), "ja" if ok3 else "NEIN"))
    if not (ok1 and ok2):
        GERISSEN.append("G2 Median Moduswechsel %s" % ARTNAME[a])
    if not ok3:
        GERISSEN.append("G2 Einzelwechsel > 500 ms %s" % ARTNAME[a])
for a in ARTEN:
    erste = col("nach", a, "erster_wechsel_ms")
    if erste:
        ueber = [v for v in erste if v > 300]
        out("  G3 erster Wechsel %-14s %s; ueber 300 ms: %s (nur berichtet)"
            % (ARTNAME[a], spanne(erste), ", ".join(fmt(v) for v in ueber) if ueber else "keiner"))
for a in ARTEN:
    kern = [(fall["netz"], fall["anzahl"], k, v) for r in runs.get(("nach", a), [])
            for fall in r["kern"] for k, v in fall.items() if k.endswith("_ms")]
    if kern:
        hoch = max(kern, key=lambda x: x[3])
        ok = hoch[3] < 50
        out("  G4 Rechnen/Blaettern ohne Oberfl. %-14s groesster Wert %s ms (%s %s %s) < 50: %s"
            % (ARTNAME[a], fmt(hoch[3]), hoch[0], hoch[1], hoch[2], "ja" if ok else "NEIN"))
        if not ok:
            GERISSEN.append("G4 Kern %s" % ARTNAME[a])
    gui = col("nach", a, "rechnen_ms") + col("nach", a, "rechnen6_ms")
    gui += [r["blaettern"][i]["berechnen_ms"] for r in runs.get(("nach", a), []) for i in (0, 1)]
    gui += [v for r in runs.get(("nach", a), []) for b in r["blaettern"] for v in b["seite_ms"].values()]
    if gui:
        ueber = [v for v in gui if v >= 50]
        out("     mit Oberflaeche %-14s groesster Wert %s ms; >= 50 ms: %s (berichtet)"
            % (ARTNAME[a], fmt(max(gui)), ", ".join(fmt(v) for v in ueber) if ueber else "keiner"))
out("")
out("GRENZEN: " + ("alle erfuellt" if not GERISSEN else "GERISSEN: " + "; ".join(GERISSEN)))
if NOTICE:
    for line in LINES:
        if line.strip():
            print("::notice::" + line.replace("%", "%25"))
