#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""0.63.2 A13 (S5c, Messzweig messung-0632): Kopie von messung_0631/tabelle_0631.py
(c18d902). Geaendert nur: liest m_*.json (p_*.json gehoeren zu
profil_oeffnen.py/teile_tabelle.py) und nennt zusaetzlich das A13-Ziel
(Teilplan S5 4.1): Median "erstes Mal" NACHHER <= Median VORHER + 100 ms.

0.63.1 Teil 1.4: Tabelle und Grenzen (nur Messung, kein Teil des Programms).

Fassung 0.63.1 von bau_0.63/t7_messung/werkzeug/tabelle_063.py. Liest die
Ergebnisse von mess_rechner_0631.py (*.json mit "stand") aus einem Ordner und
vergleicht drei Staende: VORHER (0.62.5), MITTE (0.63) und NACHHER (0.63.1).
Grenzen nach Plan 0.63.1 Abschnitt 6.5 (Lesart G1 nach Antwort 16: mild):

  G1 Oeffnen (erstes Mal und erneut), je Vorlade-Art:
     Median NACHHER <= hoechster Wert VORHER (aus DIESER Messung);
     zusaetzlich berichtet: Abstand der Mediane NACHHER - VORHER und
     NACHHER - MITTE (Auflage C-3)
  G2 Moduswechsel IPv4<->IPv6 NACHHER, je Vorlade-Art: Median (Mittel je
     Lauf und alle Einzelwechsel) <= Grenze; Grenze = --grenze-modus MS
     (Container: 137,2 aus Plan 0.63 8.1) oder sonst hoechster Mittelwert
     Reiterwechsel VORHER; kein Einzelwechsel > 500 ms
  G3 erster Wechsel IPv4->IPv6 (mit Ruhe wie T7) und erstes Antippen der
     drei Ansichten NACHHER <= 300 ms; gewertet wird streng: KEIN Einzelwert
     ueber 300 ms (Median und Hoechstwert werden genannt).
     "Erster Wechsel ohne Ruhe" (MESS_ART=ohne_ruhe) nur berichtet.
  G4 Rechnen und Blaettern ohne Oberflaeche (T-K-6) NACHHER: < 50 ms

Aufruf: python tabelle_0631.py ORDNER [--vorher 0625] [--mitte 063]
        [--nachher 0631] [--grenze-modus MS] [--notice]
Rueckgabe 0; die letzte Zeile ist "GRENZEN: alle erfuellt" bzw.
"GRENZEN: GERISSEN ..."."""
import glob
import json
import os
import statistics as st
import sys

FOLDER = sys.argv[1]
NOTICE = "--notice" in sys.argv


def opt(name, default=None):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


VOR, MITTE, NACH = opt("--vorher", "0625"), opt("--mitte", "063"), opt("--nachher", "0631")
STAENDE = (VOR, MITTE, NACH)
GRENZE_MODUS = opt("--grenze-modus")
ARTEN = ("normal", "0")
ARTNAME = {"normal": "mit Vorladen", "0": "ohne Vorladen"}
ANTIPPEN = ("ipv6/aufteilen", "ipv4/aufteilen", "ipv4/bedarf")
LINES = []
GERISSEN = []


def out(text=""):
    LINES.append(text)
    print(text)


def fmt(v):
    return ("%.1f" % v).replace(".", ",") if v is not None else "-"


def spanne(vals):
    if not vals:
        return "-"
    return "%s (%s-%s) n=%d" % (fmt(st.median(vals)), fmt(min(vals)), fmt(max(vals)), len(vals))


runs, kurz = {}, {}
for path in sorted(glob.glob(os.path.join(FOLDER, "m_*.json"))):
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:   # noqa: BLE001
        continue
    if "stand" not in data:
        continue
    target = kurz if data.get("art") == "ohne_ruhe" else runs
    target.setdefault((data["stand"], data["vorladen"]), []).append(data)

out("Staende: vorher %s, mitte %s, nachher %s" % STAENDE)
out("Laeufe (voll): " + ", ".join("%s/%s=%d" % (s, ARTNAME[a], len(runs.get((s, a), [])))
                                  for s in STAENDE for a in ARTEN))
out("Laeufe (ohne Ruhe): " + (", ".join("%s/%s=%d" % (s, ARTNAME[a], len(kurz[(s, a)]))
                                        for s in STAENDE for a in ARTEN if kurz.get((s, a)))
                              or "keine"))
for s in STAENDE:
    for a in ARTEN:
        if len(runs.get((s, a), [])) != 7:
            GERISSEN.append("UNVOLLSTAENDIG %s/%s: %d statt 7 Laeufe"
                            % (s, ARTNAME[a], len(runs.get((s, a), []))))
lasten = [x for group in (runs, kurz) for rs in group.values() for r in rs
          for x in ((r.get("last_start") or [None])[0], (r.get("last_ende") or [None])[0])
          if x is not None]
if lasten:
    out("Last (1-min-Mittel, Start/Ende je Lauf): Median %s (%s-%s)"
        % (fmt(st.median(lasten)), fmt(min(lasten)), fmt(max(lasten))))


def col(s, a, key, group=None):
    return [r[key] for r in (runs if group is None else group).get((s, a), [])
            if r.get(key) is not None]


def flat(s, a, key):
    return [x for r in runs.get((s, a), []) for x in r.get(key, [])]


def tap(s, a, name):
    return [r["antippen_ms"][name] for r in runs.get((s, a), []) if "antippen_ms" in r]


def tap_built(s, a, name):
    return sorted({r["antippen_gebaut"][name] for r in runs.get((s, a), [])
                   if "antippen_gebaut" in r}, key=str)


ROW = "  %-44s %-26s %-26s %s"
out("")
out("Tabelle: Median (min-max) n   [ms]")
for a in ARTEN:
    out("== %s (FISI_VORLADEN=%s) ==" % (ARTNAME[a], a))
    for s in STAENDE:
        rs = runs.get((s, a), [])
        out("  %s: calc vorgeladen %s, ipv6 vorgebaut %s, IPv6-Eingabe geprueft %s"
            % (s, sorted({r["calc_vorgeladen"] for r in rs}),
               sorted({r.get("ipv6_vorgebaut") for r in rs}, key=str),
               sorted({r.get("ipv6_eingabe_geprueft") for r in rs}, key=str)))
    out(ROW % ("Wert", VOR, MITTE, NACH))
    for key, name in (("oeffnen_ms", "Rechner oeffnen (erstes Mal)"),
                      ("wieder_ms", "Rechner erneut oeffnen"),
                      ("reiter_ms", "Reiterwechsel, Mittel aus 6 je Lauf"),
                      ("rechnen_ms", "Berechnen IPv4"),
                      ("rechnen6_ms", "Berechnen IPv6"),
                      ("rechenweg_ms", "Rechenweg IPv4 einblenden"),
                      ("erster_wechsel_ms", "Erster Wechsel IPv4->IPv6 (mit Ruhe)"),
                      ("modus_ms", "Moduswechsel, Mittel aus 6 je Lauf"),
                      ("rechenweg6_ms", "Rechenweg IPv6 einblenden")):
        out(ROW % (name, spanne(col(VOR, a, key)), spanne(col(MITTE, a, key)),
                   spanne(col(NACH, a, key))))
    out(ROW % ("Reiterwechsel einzeln", spanne(flat(VOR, a, "reiter_einzeln_ms")),
               spanne(flat(MITTE, a, "reiter_einzeln_ms")), spanne(flat(NACH, a, "reiter_einzeln_ms"))))
    out(ROW % ("Moduswechsel einzeln", "-", spanne(flat(MITTE, a, "modus_einzeln_ms")),
               spanne(flat(NACH, a, "modus_einzeln_ms"))))
    for name in ANTIPPEN:
        out(ROW % ("Erstes Antippen %s" % name, "-", spanne(tap(MITTE, a, name)),
                   spanne(tap(NACH, a, name))))
        out(ROW % ("   (Ansicht vorher schon gebaut?)", "-", tap_built(MITTE, a, name),
                   tap_built(NACH, a, name)))
    out(ROW % ("Erster Wechsel OHNE Ruhe (eigene Laeufe)", "-",
               spanne(col(MITTE, a, "erster_wechsel_ohne_ruhe_ms", kurz)),
               spanne(col(NACH, a, "erster_wechsel_ohne_ruhe_ms", kurz))))
    out(ROW % ("   Oeffnen in diesen Laeufen", "-", spanne(col(MITTE, a, "oeffnen_ms", kurz)),
               spanne(col(NACH, a, "oeffnen_ms", kurz))))
    for i, netz in ((0, "::/0 in 2^64"), (1, "10.0.0.0/8 in 2^24")):
        for what in ("Berechnen", "je Seite"):
            vals = {}
            for s in (MITTE, NACH):
                rs = [r for r in runs.get((s, a), []) if "blaettern" in r]
                if what == "Berechnen":
                    vals[s] = [r["blaettern"][i]["berechnen_ms"] for r in rs]
                else:
                    vals[s] = [v for r in rs for v in r["blaettern"][i]["seite_ms"].values()]
            out(ROW % ("Aufteilen %s %s (Oberfl.)" % (netz, what), "-",
                       spanne(vals[MITTE]), spanne(vals[NACH])))
    kern = {s: [v for r in runs.get((s, a), []) if "kern" in r for fall in r["kern"]
                for k, v in fall.items() if k.endswith("_ms")] for s in (MITTE, NACH)}
    out(ROW % ("Kern ohne Oberfl. (T-K-6), alle Werte", "-", spanne(kern[MITTE]),
               spanne(kern[NACH])))

out("")
out("Grenzen (Plan 0.63.1 Abschnitt 6.5; G1 milde Lesart, Antwort 16)")
for a in ARTEN:
    for key, name in (("oeffnen_ms", "Oeffnen erstes Mal"), ("wieder_ms", "Oeffnen erneut")):
        vor, mitte, nach = col(VOR, a, key), col(MITTE, a, key), col(NACH, a, key)
        if not vor or not nach:
            continue
        ok = st.median(nach) <= max(vor)
        out("  G1 %-20s %-14s Median %s %s <= hoechster %s %s: %s"
            % (name, ARTNAME[a], NACH, fmt(st.median(nach)), VOR, fmt(max(vor)),
               "ja" if ok else "NEIN"))
        abstand = st.median(nach) - st.median(vor)
        text = "     Abstand Median %s - Median %s (%s): %s ms (%s %%)" % (
            NACH, VOR, fmt(st.median(vor)), fmt(abstand), fmt(100 * abstand / st.median(vor)))
        if mitte:
            d = st.median(nach) - st.median(mitte)
            text += "; Median %s - Median %s (%s): %s ms" % (NACH, MITTE, fmt(st.median(mitte)),
                                                              fmt(d))
        out(text)
        if not ok:
            GERISSEN.append("G1 %s %s" % (name, ARTNAME[a]))
out("A13 (Teilplan S5 4.1): Median erstes Mal %s <= Median %s + 100 ms (dieser Lauf)" % (NACH, VOR))
for a in ARTEN:
    vor, nach = col(VOR, a, "oeffnen_ms"), col(NACH, a, "oeffnen_ms")
    if vor and nach:
        grenze_a13 = st.median(vor) + 100
        out("  A13 %-14s Median %s %s <= %s: %s (Abstand %s ms)"
            % (ARTNAME[a], NACH, fmt(st.median(nach)), fmt(grenze_a13),
               "ja" if st.median(nach) <= grenze_a13 else "NEIN",
               fmt(st.median(nach) - st.median(vor))))
reiter_max_vor = max(col(VOR, "normal", "reiter_ms") + col(VOR, "0", "reiter_ms") or [0])
if GRENZE_MODUS:
    grenze = float(GRENZE_MODUS)
    herkunft = "vorgegeben (--grenze-modus)"
else:
    grenze = reiter_max_vor
    herkunft = "hoechster Mittelwert Reiterwechsel %s, diese Messung" % VOR
out("  G2 Grenze Moduswechsel %s ms (%s)" % (fmt(grenze), herkunft))
for a in ARTEN:
    mittel, einzeln = col(NACH, a, "modus_ms"), flat(NACH, a, "modus_einzeln_ms")
    if not mittel:
        continue
    ok1 = st.median(mittel) <= grenze and st.median(einzeln) <= grenze
    ok3 = max(einzeln) <= 500
    out("  G2 Moduswechsel %-14s Median Mittel %s, Median einzeln %s <= %s: %s; "
        "groesster Einzelwechsel %s <= 500: %s"
        % (ARTNAME[a], fmt(st.median(mittel)), fmt(st.median(einzeln)), fmt(grenze),
           "ja" if ok1 else "NEIN", fmt(max(einzeln)), "ja" if ok3 else "NEIN"))
    if not ok1:
        GERISSEN.append("G2 Median Moduswechsel %s" % ARTNAME[a])
    if not ok3:
        GERISSEN.append("G2 Einzelwechsel > 500 ms %s" % ARTNAME[a])
for a in ARTEN:
    werte = [("erster Wechsel IPv4->IPv6", col(NACH, a, "erster_wechsel_ms"))]
    werte += [("erstes Antippen %s" % name, tap(NACH, a, name)) for name in ANTIPPEN]
    for name, vals in werte:
        if not vals:
            continue
        ueber = [v for v in vals if v > 300]
        out("  G3 %-30s %-14s Median %s, hoechster %s; ueber 300 ms: %s -> %s"
            % (name, ARTNAME[a], fmt(st.median(vals)), fmt(max(vals)),
               ", ".join(fmt(v) for v in ueber) if ueber else "keiner",
               "ja" if not ueber else "NEIN"))
        if ueber:
            GERISSEN.append("G3 %s %s" % (name, ARTNAME[a]))
    ohne = col(NACH, a, "erster_wechsel_ohne_ruhe_ms", kurz)
    if ohne:
        out("     erster Wechsel OHNE Ruhe %-14s %s (nur berichtet; ueber 300 ms: %s)"
            % (ARTNAME[a], spanne(ohne), ", ".join(fmt(v) for v in ohne if v > 300) or "keiner"))
for a in ARTEN:
    kern = [(fall["netz"], fall["anzahl"], k, v) for r in runs.get((NACH, a), []) if "kern" in r
            for fall in r["kern"] for k, v in fall.items() if k.endswith("_ms")]
    if kern:
        hoch = max(kern, key=lambda x: x[3])
        ok = hoch[3] < 50
        out("  G4 Rechnen/Blaettern ohne Oberfl. %-14s groesster Wert %s ms (%s %s %s) < 50: %s"
            % (ARTNAME[a], fmt(hoch[3]), hoch[0], hoch[1], hoch[2], "ja" if ok else "NEIN"))
        if not ok:
            GERISSEN.append("G4 Kern %s" % ARTNAME[a])
out("")
out("GRENZEN: " + ("alle erfuellt" if not GERISSEN else "GERISSEN: " + "; ".join(GERISSEN)))
if NOTICE:
    for line in LINES:
        if line.strip():
            print("::notice::" + line.replace("%", "%25"))
