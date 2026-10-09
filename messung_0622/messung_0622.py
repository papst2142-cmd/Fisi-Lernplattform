#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Messung 0.62.2 im Bau (nur Messung, kein Teil des Programms).

Grundlage: zeitleiste_0622.py aus dem Plan (Abschnitt 6.1, Belege b3). Misst
eine Programmfassung (Ordner als Argument) mit leerer Datenbank. Erkennt
selbst, ob es die Fassung vor 0.62.2 ("vorher", Bereiche farben/schrift/
rahmenplan) oder danach ("nachher", optik/lerninhalte) ist.

MESS_ART=zeitleiste (Standard):
  * Vorladen fertig, Optionen vorgeladen nach, Block "settings" (Schritt
    samt Zeichnen), laengster Vorlade-Teil "settings:..."
  * Darstellungswechsel von der Startseite, Vorladen fertig danach, Block
    "settings" nach dem Wechsel
  * Hilfe oeffnen, Optionen oeffnen (nach dem Vorladen)
  * erstes Aufklappen: vorher "Farben", dann "Schriftgröße" (Summe beider =
    Grenze F6), "Rahmenplan", "Lerninhalte"; nachher "Optische Anpassungen",
    "Lerninhalte"
  * Schriftwechsel aus den Optionen (Normal -> Groß -> Normal) mit offenem
    "Schriftgröße" (vorher) bzw. "Optische Anpassungen" (nachher), je
    Gesamtdauer und Dauer des Neuaufbaus (_recolor)
  * Speicher und Elemente (nur berichtet)
MESS_ART=ohne_vorladen: FISI_VORLADEN=0, Optionen 1,5 s nach dem Start oeffnen.

Aufruf: python messung_0622.py ORDNER AUSGABE.json
Ausgabe zusaetzlich: eine Zeile "ERG ..." (kurz, fuer ::notice::)."""
import json, os, sys, tempfile, time

SRC = os.path.abspath(sys.argv[1]); OUT = os.path.abspath(sys.argv[2])
ART = os.environ.get("MESS_ART", "zeitleiste")
folder = tempfile.mkdtemp(prefix="fisi messung0622 ")
os.environ["FISI_DB_PATH"] = os.path.join(folder, "test.db")
os.environ["FISI_SELFTEST"] = os.path.join(folder, "log.txt")
os.environ["HOME"] = folder
os.environ["APPDATA"] = folder
if ART == "ohne_vorladen":
    os.environ["FISI_VORLADEN"] = "0"
sys.path.insert(0, SRC)
os.chdir(SRC)
import customtkinter as ctk  # noqa: E402
import app_gui  # noqa: E402
import fisi_theme  # noqa: E402

NEU = hasattr(app_gui.fo, "OPTIK_ID")

if sys.platform == "win32":
    import psutil
    def rss_mb():
        return round(psutil.Process().memory_info().rss / 1048576.0, 1)
else:
    def rss_mb():
        with open("/proc/self/statm") as h:
            return round(int(h.read().split()[1]) * os.sysconf("SC_PAGE_SIZE") / 1048576.0, 1)

T = {"t0": None}
steps = []          # (task-name, ende_s, block_ms)
orig_run = app_gui.ViewPreloader._run


def name(task):
    if task[0] == "view":
        return task[1]
    if task[0] == "part":
        return task[1] + ":teil"
    return "%s:%s" % (task[1], task[2])


def run(self, task):
    started = time.perf_counter()
    worked = orig_run(self, task)
    if worked:
        def drawn():
            steps.append((name(task), round(time.perf_counter() - T["t0"], 2),
                          round((time.perf_counter() - started) * 1000)))
        self.root.after_idle(drawn)
    return worked


app_gui.ViewPreloader._run = run
app_gui.UpdateController.auto_check = lambda self: None
app_gui.SyncController.auto_start = lambda self: None
app_gui.apply_appearance()
root = ctk.CTk()
errors = []
root.report_callback_exception = lambda *exc: errors.append(repr(exc[1]))
T["t0"] = time.perf_counter()
app = app_gui.FISIApp(root)
root.geometry("1360x880+0+0")


def settle():
    root.update_idletasks(); root.update()


def timed(action):
    a = time.perf_counter(); action(); settle()
    return round((time.perf_counter() - a) * 1000)


def pump(seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        root.update(); time.sleep(0.005)


def wait_done():
    end = time.monotonic() + 240
    while time.monotonic() < end and not app.preloader.done:
        root.update(); time.sleep(0.005)
    done = round(time.perf_counter() - T["t0"], 2)
    pump(0.5)
    return done


def summary(rows):
    ready, block, parts = {}, {}, {}
    for step, t, ms in rows:
        base = step.split(":")[0] if step.endswith(":teil") else step
        ready[base] = t                      # letzter Teil = fertig
        if ":" in step:
            parts[step] = max(parts.get(step, 0), ms)
            parts[step + ":summe"] = parts.get(step + ":summe", 0) + ms
        else:
            block[step] = max(block.get(step, 0), ms)
    return ready, block, parts


def open_area(area_id):
    view = app.views["settings"]
    if area_id not in view.areas:
        raise SystemExit("Bereich %r fehlt in dieser Fassung" % area_id)
    ms = timed(lambda: view.open_area(area_id))
    if not view.folds[area_id].opened:
        raise SystemExit("Bereich %r nicht offen" % area_id)
    return ms


def font_change(size_id):
    """Schriftwechsel wie ein Klick in der Schriftwahl: Gesamtdauer und
    Dauer des Neuaufbaus (_recolor)."""
    rec = {"ms": 0.0}
    original = app._recolor

    def wrapped(*args, **kwargs):
        a = time.perf_counter()
        try:
            return original(*args, **kwargs)
        finally:
            rec["ms"] += (time.perf_counter() - a) * 1000
    app._recolor = wrapped
    try:
        total = timed(lambda: app.change_font_size(size_id))
    finally:
        del app._recolor
    if fisi_theme.current_font_size != size_id:
        raise SystemExit("Schriftwechsel auf %r nicht angekommen" % size_id)
    return total, round(rec["ms"])


res = {"version": app_gui.APP_VERSION, "fassung": os.path.basename(SRC.rstrip("/\\")),
       "neu": NEU, "art": ART, "system": sys.platform}

if ART == "ohne_vorladen":
    pump(1.5)
    res["vorlader_modus"] = app.preloader.mode
    res["settings_gebaut_vorher"] = app.views.built("settings") is not None
    res["optionen_ohne_vorladen_ms"] = timed(lambda: app.show_view("settings"))
    res["elemente"] = app_gui.count_widgets(root)
    res["fehler"] = errors
    with open(OUT, "w", encoding="utf-8") as h:
        json.dump(res, h, indent=1)
    print("ERG %s %s ohne Vorladen: Optionen %d ms (vorher gebaut: %s)"
          % (res["fassung"], "nachher" if NEU else "vorher", res["optionen_ohne_vorladen_ms"],
             res["settings_gebaut_vorher"]))
    sys.stdout.flush()
    os._exit(0)

res["fertig_s"] = wait_done()
res["schritte"] = list(steps)
res["bereit_s"], res["block_ms"], res["teil_ms"] = summary(steps)
res["rss_mb"] = rss_mb()
res["elemente"] = app_gui.count_widgets(root)
# Darstellungswechsel (vorher nichts geoeffnet)
steps.clear()
other = fisi_theme.MODE_LIGHT if not fisi_theme.light else fisi_theme.MODE_DARK
a = time.perf_counter()
res["wechsel_ms"] = timed(lambda: app.change_color(mode=other))
T["t0"] = a
res["fertig_nach_wechsel_s"] = wait_done()
res["bereit_nach_wechsel_s"], res["block_nach_wechsel_ms"], _ = summary(steps)
res["rss_nach_wechsel_mb"] = rss_mb()
# Oeffnen nach dem Vorladen
res["hilfe_ms"] = timed(lambda: app.show_view("help"))
res["optionen_ms"] = timed(lambda: app.show_view("settings"))
if NEU:
    res["optik_ms"] = open_area("optik")
    res["lerninhalte_ms"] = open_area("lerninhalte")
    font_area = "optik"
else:
    res["farben_ms"] = open_area("farben")
    res["schrift_ms"] = open_area("schrift")
    res["schrift_farben_ms"] = res["farben_ms"] + res["schrift_ms"]
    res["rahmenplan_ms"] = open_area("rahmenplan")
    res["lerninhalte_ms"] = open_area("lerninhalte")
    res["lerninhalte_rahmenplan_ms"] = res["lerninhalte_ms"] + res["rahmenplan_ms"]
    font_area = "schrift"
pump(0.3)
res["schrift_gross_ms"], res["schrift_gross_neuaufbau_ms"] = font_change("gross")
view = app.views["settings"]
res["schrift_bereich_offen_danach"] = bool(view.folds[font_area].opened)
pump(0.3)
res["schrift_normal_ms"], res["schrift_normal_neuaufbau_ms"] = font_change("normal")
res["fehler"] = errors
with open(OUT, "w", encoding="utf-8") as h:
    json.dump(res, h, indent=1)
b = res["block_ms"]
tp = {k: v for k, v in res["teil_ms"].items() if not k.endswith(":summe")}
bigp = max(tp.items(), key=lambda kv: kv[1]) if tp else ("-", 0)
klick = ("Optik %d" % res["optik_ms"]) if NEU else (
    "Farben %d + Schrift %d = %d" % (res["farben_ms"], res["schrift_ms"], res["schrift_farben_ms"]))
print("ERG %s %s fertig %.1f s | Block settings %d | Teil max %s %d | Optionen %d | %s | "
      "Lerninhalte %d | Wechsel %d | Schrift %d/%d | %s MB"
      % (res["fassung"], "nachher" if NEU else "vorher", res["fertig_s"], b.get("settings", 0),
         bigp[0], bigp[1], res["optionen_ms"], klick, res["lerninhalte_ms"], res["wechsel_ms"],
         res["schrift_gross_ms"], res["schrift_normal_ms"], res["rss_mb"]))
sys.stdout.flush()
os._exit(0)
