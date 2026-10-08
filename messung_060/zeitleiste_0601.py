#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Messung 0.60.1 (nur Messung, kein Teil des Programms).

Startet eine Programmfassung (Ordner als Argument) mit leerer Datenbank und misst:
  * Zeitleiste des Vorladens: wann ist welche Seite fertig (s ab Anlegen des
    Hauptfensters), Fertigzeit insgesamt
  * laengster Block im Hauptfaden je Schritt = Schritt PLUS Zeichnen danach
    (bis zur naechsten Leerlauf-Runde), getrennt fuer Hilfe-/Farben-Teile
  * Hilfe oeffnen, Optionen oeffnen, "Farben" aufklappen (nach dem Vorladen)
  * Speicher nach dem Vorladen, Elemente
  * ein Darstellungswechsel (vorher nichts geoeffnet) und die Fertigzeit
    des Vorladens danach
Gleich fuer 0.59.3, 0.60 und 0.60.1 (misst ueber ViewPreloader._run).

Aufruf: python zeitleiste_0601.py ORDNER AUSGABE.json
Ausgabe zusaetzlich: eine Zeile "ERG ..." (kurz, fuer ::notice::)."""
import json, os, sys, tempfile, time

SRC = os.path.abspath(sys.argv[1]); OUT = os.path.abspath(sys.argv[2])
folder = tempfile.mkdtemp(prefix="fisi zeitleiste ")
os.environ["FISI_DB_PATH"] = os.path.join(folder, "test.db")
os.environ["FISI_SELFTEST"] = os.path.join(folder, "log.txt")
os.environ["HOME"] = folder
os.environ["APPDATA"] = folder
sys.path.insert(0, SRC)
os.chdir(SRC)
import customtkinter as ctk  # noqa: E402
import app_gui  # noqa: E402
import fisi_theme  # noqa: E402

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
T["t0"] = time.perf_counter()
app = app_gui.FISIApp(root)
root.geometry("1360x880+0+0")


def settle():
    root.update_idletasks(); root.update()


def timed(action):
    a = time.perf_counter(); action(); settle()
    return round((time.perf_counter() - a) * 1000)


def wait_done():
    end = time.monotonic() + 240
    while time.monotonic() < end and not app.preloader.done:
        root.update(); time.sleep(0.005)
    done = round(time.perf_counter() - T["t0"], 2)
    end = time.monotonic() + 0.5
    while time.monotonic() < end:
        root.update(); time.sleep(0.01)
    return done


def summary(rows):
    ready, block, parts = {}, {}, {}
    for step, t, ms in rows:
        base = step.split(":")[0] if step.endswith(":teil") else step
        ready[base] = t                      # letzter Teil = fertig
        if ":" in step:
            parts[step] = max(parts.get(step, 0), ms)
        else:
            block[step] = max(block.get(step, 0), ms)
    return ready, block, parts


res = {"version": app_gui.APP_VERSION, "fassung": os.path.basename(SRC.rstrip("/\\")), "system": sys.platform}
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
res["farben_ms"] = timed(lambda: app.views["settings"].open_area("farben"))
with open(OUT, "w", encoding="utf-8") as h:
    json.dump(res, h, indent=1)
b = res["block_ms"]; big = max(b.items(), key=lambda kv: kv[1]) if b else ("-", 0)
tp = res["teil_ms"]; bigp = max(tp.items(), key=lambda kv: kv[1]) if tp else ("-", 0)
r = res["bereit_s"]
first = " ".join("%s=%.1f" % (k[:5], r[k]) for k in ("cards", "game", "settings", "progress", "help") if k in r)
print("ERG %s fertig %.1f s | %s | Block max %s %d | Teil max %s %d | Hilfe %d Farben %d | Wechsel %d, fertig danach %.1f s | %s MB"
      % (res["fassung"], res["fertig_s"], first, big[0], big[1], bigp[0], bigp[1],
         res["hilfe_ms"], res["farben_ms"], res["wechsel_ms"], res["fertig_nach_wechsel_s"], res["rss_mb"]))
sys.stdout.flush()
os._exit(0)
