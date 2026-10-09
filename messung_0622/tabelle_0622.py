#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Zusammenfassung der Messung 0.62.2 (nur Messung, kein Teil des Programms).

Liest die Ergebnisse von messung_0622.py (z_*.json, o_*.json) und
messung_wechsel.py (w_*.json) aus einem Ordner und vergleicht vorher und
nachher nach Plan 0.62.2 Abschnitt 6.4 und Freigabe F6:

  Grenze: Median nachher <= hoechster Wert vorher (je Zeitwert)
  "Optische Anpassungen" aufklappen gegen "Schriftgröße + Farben" vorher
  (Summe je Lauf), "Farben allein" nur berichtet
  kein einzelner Vorlade-Teil nachher ueber 150 ms
  Speicher, Elemente, Hilfe, Lerninhalte: nur berichtet

Aufruf: python tabelle_0622.py ORDNER [--notice]
"""
import glob
import json
import os
import statistics as st
import sys

FOLDER = sys.argv[1]
NOTICE = "--notice" in sys.argv
PART_LIMIT_MS = 150


def load(pattern):
    rows = {"vorher": [], "nachher": []}
    for path in sorted(glob.glob(os.path.join(FOLDER, pattern))):
        try:
            data = json.load(open(path, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if "neu" in data:
            rows["nachher" if data["neu"] else "vorher"].append(data)
        else:   # messung_wechsel: Fassung am Dateinamen
            rows["nachher" if "_n" in os.path.basename(path) else "vorher"].append(data)
    return rows


def settings_parts(run):
    return {k: v for k, v in run["teil_ms"].items()
            if k.startswith("settings:") and not k.endswith(":summe")}


# (Name, Wert vorher, Wert nachher, Grenze?)
Z = [
    ("Vorladen fertig (s)", lambda r: r["fertig_s"], None, True),
    ("Optionen vorgeladen nach (s)", lambda r: r["bereit_s"].get("settings"), None, True),
    ("Block settings am Stueck (ms)", lambda r: r["block_ms"].get("settings"), None, True),
    ("Block settings nach Wechsel (ms)", lambda r: r["block_nach_wechsel_ms"].get("settings"),
     None, True),
    ("Darstellungswechsel Startseite (ms)", lambda r: r["wechsel_ms"], None, True),
    ("Vorladen fertig nach Wechsel (s)", lambda r: r["fertig_nach_wechsel_s"], None, True),
    ("Optionen oeffnen vorgeladen (ms)", lambda r: r["optionen_ms"], None, True),
    ("Laengster Teil settings:* (ms)", lambda r: max(settings_parts(r).values()), None, True),
    ("Summe Teile settings:* (ms)", lambda r: sum(v for k, v in r["teil_ms"].items()
                                                 if k.startswith("settings:")
                                                 and k.endswith(":summe")), None, True),
    ("F6: Schrift+Farben vorher / Optik nachher (ms)", lambda r: r["schrift_farben_ms"],
     lambda r: r["optik_ms"], True),
    ("Nur berichtet: Farben allein vorher / Optik (ms)", lambda r: r["farben_ms"],
     lambda r: r["optik_ms"], False),
    ("Schriftwechsel Normal->Gross (ms)", lambda r: r["schrift_gross_ms"], None, True),
    ("Schriftwechsel Gross->Normal (ms)", lambda r: r["schrift_normal_ms"], None, True),
    ("  davon Neuaufbau Normal->Gross (ms)", lambda r: r["schrift_gross_neuaufbau_ms"], None,
     False),
    ("  davon Neuaufbau Gross->Normal (ms)", lambda r: r["schrift_normal_neuaufbau_ms"], None,
     False),
    ("Nur berichtet: Lerninhalte(+Rahmenplan) (ms)", lambda r: r["lerninhalte_rahmenplan_ms"],
     lambda r: r["lerninhalte_ms"], False),
    ("Nur berichtet: Hilfe oeffnen (ms)", lambda r: r["hilfe_ms"], None, False),
    ("Nur berichtet: Speicher (MB)", lambda r: r["rss_mb"], None, False),
    ("Nur berichtet: Elemente", lambda r: r["elemente"], None, False),
]


def values(runs, getter):
    out = []
    for run in runs:
        try:
            value = getter(run)
        except (KeyError, ValueError):
            value = None
        if value is not None:
            out.append(value)
    return out


def fmt(vals):
    if not vals:
        return "-"
    return "%s (%s-%s)" % (round(st.median(vals), 2), min(vals), max(vals))


lines = []
broken = []


def compare(name, before, after, limit):
    if not before or not after:
        lines.append("%-48s vorher %-22s nachher %-22s FEHLT" % (name, fmt(before), fmt(after)))
        if limit:
            broken.append(name + " (Werte fehlen)")
        return
    verdict = ""
    if limit:
        ok = st.median(after) <= max(before)
        verdict = "OK" if ok else "GRENZE GERISSEN"
        if not ok:
            broken.append("%s: Median nachher %s > max vorher %s"
                          % (name, round(st.median(after), 2), max(before)))
    lines.append("%-48s vorher %-22s nachher %-22s %s"
                 % (name, fmt(before), fmt(after), verdict or "(berichtet)"))


z = load("z_*.json")
lines.append("Zeitleiste: vorher n=%d, nachher n=%d" % (len(z["vorher"]), len(z["nachher"])))
for name, get_before, get_after, limit in Z:
    compare(name, values(z["vorher"], get_before),
            values(z["nachher"], get_after or get_before), limit)
parts = [(k, v, run["fassung"]) for run in z["nachher"] for k, v in run["teil_ms"].items()
         if not k.endswith(":summe")]
worst = max(parts, key=lambda p: p[1]) if parts else ("-", 0, "-")
lines.append("%-48s %s %d ms (Grenze %d) %s" % ("Laengster Vorlade-Teil nachher (alle)", worst[0],
             worst[1], PART_LIMIT_MS, "OK" if worst[1] <= PART_LIMIT_MS else "GRENZE GERISSEN"))
if worst[1] > PART_LIMIT_MS:
    broken.append("Vorlade-Teil %s %d ms > %d" % (worst[0], worst[1], PART_LIMIT_MS))
font_open = values(z["nachher"], lambda r: r["schrift_bereich_offen_danach"])
lines.append("%-48s %s" % ("Optik nach Schriftwechsel offen (nachher)", font_open))
errors = [run["fehler"] for run in z["vorher"] + z["nachher"] if run.get("fehler")]
lines.append("%-48s %s" % ("Fehler in den Laeufen", errors or "keine"))

o = load("o_*.json")
compare("Optionen oeffnen ohne Vorladen (ms)",
        values(o["vorher"], lambda r: r["optionen_ohne_vorladen_ms"]),
        values(o["nachher"], lambda r: r["optionen_ohne_vorladen_ms"]), True)

w = load("w_*.json")
wb = [x["gesamt_ms"] for run in w["vorher"] for x in run["wechsel"]]
wa = [x["gesamt_ms"] for run in w["nachher"] for x in run["wechsel"]]
compare("Wechsel aus den Optionen, Bereich offen (ms)", wb, wa, True)
for label, runs in (("vorher", w["vorher"]), ("nachher", w["nachher"])):
    lines.append("  Wechsel %s: Runden %d, Fehler %s" % (
        label, len(runs), [run.get("fehler") for run in runs if run.get("fehler")] or "keine"))

lines.append("")
lines.append("ERGEBNIS: " + ("alle Grenzen eingehalten" if not broken else
                             "GERISSEN: " + " | ".join(broken)))
if NOTICE:
    # GitHub zeigt nur wenige Hinweise je Schritt: Zeilen buendeln (%0A =
    # Zeilenumbruch im Hinweis), dazu je Wert alle Einzelwerte
    for line in lines:
        print(line)
    detail = []
    for name, get_before, get_after, _limit in Z:
        detail.append("%s: vorher %s / nachher %s" % (
            name.strip(), values(z["vorher"], get_before),
            values(z["nachher"], get_after or get_before)))
    detail.append("ohne Vorladen: vorher %s / nachher %s" % (
        values(o["vorher"], lambda r: r["optionen_ohne_vorladen_ms"]),
        values(o["nachher"], lambda r: r["optionen_ohne_vorladen_ms"])))
    detail.append("Wechsel aus Optionen: vorher %s / nachher %s" % (wb, wa))
    body = [line for line in lines if line.strip()] + detail
    for start in range(0, len(body), 8):
        print("::notice::" + "%0A".join(body[start:start + 8]))
else:
    for line in lines:
        print(line)
