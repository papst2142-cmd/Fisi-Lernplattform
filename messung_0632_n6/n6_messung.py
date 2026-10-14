#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
N6 (0.63.2) Messwerkzeug - nach pruefung_0.62.4/teil5_H_M/werkzeuge/i_messung.py
(Wegwerf-HOME, kein Netz, Dialoge abgefangen), erweitert um die Phasen von
B-I-01 und die Vorlade-Schritte von B-I-04. Laeuft auf jedem Stand (vorher
e0f9c7e und nachher N6); was es auf einem Stand nicht gibt, bleibt leer.

Aufruf (unter xvfb-run -a -s "-screen 0 1920x1080x24"):
  python -I n6_messung.py APPKOPIE AUSGABE.jsonl MODUS
MODUS:
  wechsel  Optionen mit offenem Bereich "Optische Anpassungen"; je Fall
           (Schrift Gross->Normal->Gross, Hell<->Dunkel, Grundfarbe) n-mal:
           (i)  Klick -> Abdeckung weg (bedienbar)
           (ii) Klick -> alte Oberflaeche ganz abgebaut und alles erledigt
           (iii) laengstes einzelnes Ereignis zwischen (i) und (ii)
           (iv) laengste Wartezeit eines Klicks in den 3 s nach (i)
           (Ereignisschleife wie mainloop: je Durchlauf ein dooneevent)
  start    Vorladen nach dem Start: fertig_ms, laengste Blockade, je Schritt
           block_ms (Schritt samt Zeichnen), die 5 Ansichten aus B-I-04 und
           "abschluss" einzeln
Umgebung: N6_HOME (Pflicht), N6_N (Wiederholungen je Fall, Standard 5),
          N6_RUNDE (Protokoll)
"""
import json
import os
import shutil
import sys
import time
import traceback
import _tkinter

REPO = os.path.abspath(sys.argv[1])
OUTFILE = os.path.abspath(sys.argv[2])
MODE = sys.argv[3]
HOME = os.path.abspath(os.environ["N6_HOME"])
N = int(os.environ.get("N6_N", "5"))
RUNDE = os.environ.get("N6_RUNDE", "")
shutil.rmtree(HOME, ignore_errors=True)
os.makedirs(HOME)
os.environ["HOME"] = HOME
os.environ["APPDATA"] = HOME          # Windows
os.environ["USERPROFILE"] = HOME
os.environ["XDG_DATA_HOME"] = os.path.join(HOME, ".local", "share")
os.environ["XDG_CONFIG_HOME"] = os.path.join(HOME, ".config")
os.environ["FISI_DB_PATH"] = os.path.join(HOME, "fisi.db")
os.environ["FISI_SELFTEST"] = os.path.join(HOME, "selftest.log")
with open(os.path.join(HOME, "einstellungen.json"), "w", encoding="utf-8") as fh:
    json.dump({"auto_check": False, "darstellung": "dunkel", "schriftgroesse": "normal"}, fh)
sys.path.insert(0, REPO)
os.chdir(REPO)

from tkinter import messagebox, filedialog   # noqa: E402
for _name in ("showinfo", "showwarning", "showerror", "askyesno", "askokcancel",
              "askyesnocancel", "askquestion", "askretrycancel"):
    setattr(messagebox, _name, lambda *a, **k: False)
filedialog.asksaveasfilename = lambda *a, **k: ""
filedialog.askopenfilename = lambda *a, **k: ""

import customtkinter as ctk   # noqa: E402
import app_gui                # noqa: E402
import fisi_theme             # noqa: E402

ERRORS = []
app_gui.apply_appearance()
root = ctk.CTk()
root.report_callback_exception = lambda *exc: ERRORS.append(
    "".join(traceback.format_exception(*exc))[-800:])
app = app_gui.FISIApp(root)
root.geometry("1360x900+0+0")


def loadavg():
    try:   # unter Windows gibt es /proc nicht -> leer
        with open("/proc/loadavg") as fh:
            return float(fh.read().split()[0])
    except OSError:
        return None


def rss_mb():
    try:
        with open("/proc/self/status") as fh:
            for line in fh:
                if line.startswith("VmRSS:"):
                    return round(int(line.split()[1]) / 1024.0, 1)
    except OSError:
        return None


def emit(art, **values):
    row = {"modus": MODE, "runde": RUNDE, "art": art,
           "stand": os.path.basename(REPO.rstrip("/"))}
    row.update(values)
    with open(OUTFILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def pump_until(condition, limit):
    start = time.perf_counter()
    longest = 0.0
    while not condition():
        if time.perf_counter() - start > limit:
            break
        t = time.perf_counter()
        handled = root.tk.dooneevent(_tkinter.DONT_WAIT)
        longest = max(longest, time.perf_counter() - t)
        if not handled:
            time.sleep(0.003)
    return (time.perf_counter() - start) * 1000, longest * 1000


def pending():
    return bool(getattr(app, "recolor_pending", False))


def wait_preload():
    app.preloader.last_input = 0
    return pump_until(lambda: app.preloader.done and not pending(), 300)


if MODE == "start":
    load = loadavg()
    waited, longest = wait_preload()
    # die Dauer des letzten Schritts ("abschluss") wird erst im naechsten
    # Leerlauf-Durchgang eingetragen (_release_task): kurz weiterlaufen
    pump_until(lambda: False, 0.5)
    pre = app.preloader
    steps = {app_gui.task_label(t): ms for t, ms in pre.block_ms.items()}
    emit("start", fertig_ms=pre.finished_ms, laengste_blockade_ms=round(longest),
         schritte=steps, load_vor=load, load_nach=loadavg(), rss_mb=rss_mb(),
         fehler=ERRORS[:3])
    root.destroy()
    sys.exit(0)

# -- wechsel -----------------------------------------------------------------
wait_preload()
app.show_view("settings")
app.views["settings"].open_area("optik")
pump_until(lambda: False, 0.5)

marks = {}
hide = app._hide_busy


def hide_busy(overlay):
    hide(overlay)
    marks["bedienbar"] = time.perf_counter()
app._hide_busy = hide_busy


def one(case, action):
    marks.clear()
    load = loadavg()
    rss = rss_mb()
    t0 = time.perf_counter()
    action()
    t_call = time.perf_counter()
    ready = marks.get("bedienbar", t_call)
    # bis alles erledigt (neuer Stand: Abbau-Schritte; alter: nichts mehr offen)
    done_ms, longest = pump_until(lambda: not pending(), 60)
    t_done = time.perf_counter()
    # (iv) Klick-Wartezeit in den 3 s nach "bedienbar": laengstes Ereignis
    rest = max(0.0, 3.0 - (t_done - ready))
    _w, longest3 = pump_until(lambda: False, rest)
    emit("wechsel", fall=case, bedienbar_ms=round((ready - t0) * 1000, 1),
         aufruf_ms=round((t_call - t0) * 1000, 1),
         fertig_ms=round((t_done - t0) * 1000, 1),
         laengstes_ereignis_abbau_ms=round(max(longest, 0.0), 1),
         laengstes_ereignis_3s_ms=round(max(longest, longest3), 1),
         load_vor=load, load_nach=loadavg(), rss_vor=rss, rss_nach=rss_mb(),
         optik_offen=app.views["settings"].folds["optik"].opened, fehler=ERRORS[-1:])
    wait_preload()


presets = [p["id"] for p in fisi_theme.PRESETS]
for i in range(N):
    one("schrift_gross", lambda: app.change_font_size("gross"))
    one("schrift_normal", lambda: app.change_font_size("normal"))
    other = fisi_theme.MODE_LIGHT if not fisi_theme.light else fisi_theme.MODE_DARK
    one("hell_dunkel", lambda: app.change_color(mode=other))
    one("grundfarbe", lambda: app.change_color(preset_id=presets[(i + 1) % len(presets)]))
root.destroy()
