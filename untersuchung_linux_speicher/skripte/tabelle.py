#!/usr/bin/env python3
"""Fasst die JSON-Ergebnisse von messung_wechsel.py zu CSV-Dateien und einer
Kurztabelle zusammen. Aufruf: python tabelle.py ZIELORDNER JSON..."""
import json
import os
import statistics
import sys

out = sys.argv[1]
files = sys.argv[2:]
COLS = ("datei", "version", "umgebung", "messung_an", "vorladen_abgewartet", "nr", "mode",
        "gesamt_ms", "elemente_vorher", "elemente_nachher", "umfaerben_ms", "rahmen_ms",
        "optionen_bauen_ms", "update_summe_ms", "abbau_alt_ms", "abdeckung_ms",
        "rest_ms", "rss_vorher", "rss_spitze", "rss_nachher", "vorladen_ms",
        "rss_spitze_vorladen", "elemente_danach", "rss_danach", "bildspeicher_mb")
rows, runs = [], []
for path in files:
    d = json.load(open(path, encoding="utf-8"))
    env = "windows" if "windows" in os.path.basename(path) else \
        ("xwayland" if "xwayland" in os.path.basename(path) else "linux-xvfb")
    for tag in ("ohnevorladen", "grenze1100", "cpu25"):
        if tag in os.path.basename(path):
            env += "-" + tag
    runs.append((path, d))
    for w in d["wechsel"]:
        upd = sum(w["update_ms"]) + sum(w["update_idle_ms"])
        # update-Zeiten stecken teils in den anderen Teilen (verschachtelt);
        # Rest = alles ausser Umfaerben, Rahmen, Optionen bauen, Abbau, Abdeckung
        known = (w["umfaerben_ms"] + w["rahmen_ms"] + w["optionen_bauen_ms"] +
                 w["abbau_alt_ms"] + w["abdeckung_ms"])
        r = dict(w, datei=os.path.basename(path), version=d["version"], umgebung=env,
                 messung_an=d["perf"], vorladen_abgewartet=d["warten"],
                 update_summe_ms=round(upd, 1), rest_ms=round(w["gesamt_ms"] - known, 1))
        rows.append(r)
with open(os.path.join(out, "darstellungswechsel.csv"), "w", encoding="utf-8") as h:
    h.write(";".join(COLS) + "\n")
    for r in rows:
        h.write(";".join(str(r.get(c, "")).replace(".", ",") if isinstance(r.get(c), float)
                         else str(r.get(c, "")) for c in COLS) + "\n")
with open(os.path.join(out, "laeufe.csv"), "w", encoding="utf-8") as h:
    keys = ("version", "start_ms", "rss_start", "vorladen_ms", "rss_nach_vorladen",
            "rss_spitze_vorladen", "elemente_nach_vorladen", "rss_nach_seiten",
            "elemente_nach_seiten", "opt_elemente", "schliessen_on_close_ms")
    h.write("datei;" + ";".join(keys) + "\n")
    for path, d in runs:
        h.write(os.path.basename(path) + ";" + ";".join(str(d.get(k, "")) for k in keys) + "\n")
# Kurztabelle je Gruppe (Datei ohne _rN)
groups = {}
for r in rows:
    key = (r["umgebung"], r["version"], r["messung_an"], r["vorladen_abgewartet"])
    groups.setdefault(key, []).append(r)
print("umgebung | version | messung | vorladen abgewartet | n | gesamt median (min-max) | "
      "umfaerben | optionen bauen | abbau alt | updates | rest | rss spitze max")
for key, items in sorted(groups.items()):
    g = [i["gesamt_ms"] for i in items]
    med = lambda k: round(statistics.median(i[k] for i in items))  # noqa: E731
    print("%s | %s | %s | %s | %d | %d (%d-%d) | %d | %d | %d | %d | %d | %.0f" % (
        key[0], key[1], key[2], key[3], len(items), statistics.median(g), min(g), max(g),
        med("umfaerben_ms"), med("optionen_bauen_ms"), med("abbau_alt_ms"),
        med("update_summe_ms"), med("rest_ms"), max(i["rss_spitze"] for i in items)))
