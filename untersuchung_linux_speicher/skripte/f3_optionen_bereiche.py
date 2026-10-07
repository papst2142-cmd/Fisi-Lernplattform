#!/usr/bin/env python3
"""F3: Was kostet jeder Bereich der Optionsseite beim Aufbau, und wie viele
Elemente hat er? Baut die Optionsseite N-mal neu (wie beim Darstellungs-
wechsel) und misst die Zeit zwischen zwei Bereichen (_area-Aufrufe) sowie
on_show. Aufruf: xvfb-run python3.12 f3_optionen_bereiche.py ORDNER [N]"""
import os
import statistics
import sys
import tempfile
import time

SRC = os.path.abspath(sys.argv[1])
N = int(sys.argv[2]) if len(sys.argv) > 2 else 5
folder = tempfile.mkdtemp(prefix="fisi f3 ")
os.environ["FISI_DB_PATH"] = os.path.join(folder, "test.db")
os.environ["FISI_SELFTEST"] = os.path.join(folder, "log.txt")
os.environ["HOME"] = folder
sys.path.insert(0, SRC)
os.chdir(SRC)
import customtkinter as ctk  # noqa: E402
import app_gui               # noqa: E402

app_gui.apply_appearance()
root = ctk.CTk()
app = app_gui.FISIApp(root)
app.preloader.queue = []
app.preloader.start = lambda *a, **k: None
root.geometry("1360x880+0+0")
root.update()
marks = []
original_area = app_gui.SettingsView._area


def area(self, area_id, *args, **kwargs):
    marks.append((area_id, time.perf_counter()))
    return original_area(self, area_id, *args, **kwargs)


app_gui.SettingsView._area = area
results = {}
for run in range(N):
    old = app.views.built("settings")
    if old is not None:
        old.destroy()
        dict.pop(app.views, "settings")
    marks.clear()
    start = time.perf_counter()
    view = app.views["settings"]      # baut auf (build)
    built = time.perf_counter()
    marks.append(("__ende_build", built))
    app.show_view("settings")
    root.update_idletasks()
    shown = time.perf_counter()
    for (name, t0), (_next, t1) in zip(marks, marks[1:]):
        results.setdefault(name, []).append((t1 - t0) * 1000)
    results.setdefault("ZUSAMMEN build()", []).append((built - start) * 1000)
    results.setdefault("ZUSAMMEN anzeigen (on_show, Zeichnen)", []).append((shown - built) * 1000)
    app.show_view("dashboard")
    root.update()
counts = {}
for area_id, card in view.areas.items():
    counts[area_id] = app_gui.count_widgets(card)
folded = set(view.folds)
print("Bereich;eingeklappt beim Oeffnen;Elemente;Median ms;Anteil")
total = statistics.median(results["ZUSAMMEN build()"])
for name, values in results.items():
    med = statistics.median(values)
    print("%s;%s;%s;%.0f;%s" % (name, "ja" if name in folded else ("nein" if name in counts else ""),
                                counts.get(name, ""), med,
                                "%.0f %%" % (100 * med / total) if name in counts else ""))
print("Elemente Optionsseite gesamt;;%d" % app_gui.count_widgets(view))
