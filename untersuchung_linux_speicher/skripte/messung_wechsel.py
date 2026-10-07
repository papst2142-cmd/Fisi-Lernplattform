#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Messskript Untersuchung Linux-Speicher (07.10.2026) - kein Teil des Programms.

Startet das Hauptfenster einer Programmfassung (Ordner als Argument) mit
leerer Datenbank unter einer Anzeige (xvfb-run) und misst Nicos Ablauf:
  1. Start, Vorladen abwarten
  2. Seitenrunde (alle grossen Seiten einmal)
  3. WECHSEL Darstellungswechsel Hell/Dunkel aus den Optionen heraus;
     dazwischen 3 Seitenbesuche und Vorladen abwarten (MESS_WARTEN=1, Standard)
     bzw. sofort weiter (MESS_WARTEN=0)
Je Wechsel: Gesamtdauer, Teilzeiten (Abdeckung, Neuaufbau Rahmen,
Optionsseite bauen, Zeichnen, Abbau alt, Schlaf), Elemente vorher/nachher,
Speicher (RSS) vorher/Spitze/nachher (Abtastung alle 20 ms im Hintergrund).
Leistungsmessung des Programms selbst eingeschaltet (MESS_PERF=1, Standard),
damit es wie bei Nico laeuft; ihre CSV wird mitgeliefert.

Aufruf: xvfb-run -s "-screen 0 1920x1080x24" python3.12 messung_wechsel.py ORDNER AUSGABE.json
"""
import cProfile
import gc
import io
import json
import os
import pstats
import shutil
import sys
import tempfile
import threading
import time
import traceback
from time import sleep as _sleep

SRC = os.path.abspath(sys.argv[1])
OUT = os.path.abspath(sys.argv[2])
SWITCHES = int(os.environ.get("MESS_WECHSEL", "6"))
WAIT = os.environ.get("MESS_WARTEN", "1") == "1"
PERF = os.environ.get("MESS_PERF", "1") == "1"
PROFILE_AT = int(os.environ.get("MESS_PROFIL", "0"))   # Nummer des Wechsels mit cProfile

folder = tempfile.mkdtemp(prefix="fisi messung ")
os.environ["FISI_DB_PATH"] = os.path.join(folder, "test.db")
os.environ["FISI_SELFTEST"] = os.path.join(folder, "log.txt")   # kein Netz, kein Rundgang
os.environ["HOME"] = folder
os.environ["XDG_CONFIG_HOME"] = os.path.join(folder, ".config")
os.environ["XDG_DATA_HOME"] = os.path.join(folder, ".local", "share")
sys.path.insert(0, SRC)
os.chdir(SRC)

if os.environ.get("MESS_STAPEL"):
    # Diagnose wie in F9 vorgeschlagen: kill -USR1 <PID> schreibt die
    # Python-Stapel aller Threads in diese Datei (auch wenn der Hauptfaden haengt)
    import faulthandler
    import signal
    _stack_file = open(os.environ["MESS_STAPEL"], "a")
    faulthandler.register(signal.SIGUSR1, file=_stack_file, all_threads=True)

import customtkinter as ctk          # noqa: E402
import app_gui                       # noqa: E402
import fisi_theme                    # noqa: E402
import fisi_widgets                  # noqa: E402

if sys.platform == "win32":
    import psutil
    _PROC = psutil.Process()

    def rss_mb():
        """Windows: Arbeitssatz (wie WorkingSetSize)."""
        return _PROC.memory_info().rss / 1048576.0
else:
    PAGE = os.sysconf("SC_PAGE_SIZE")

    def rss_mb():
        with open("/proc/self/statm") as handle:
            return int(handle.read().split()[1]) * PAGE / 1048576.0


class Sampler:
    """Liest alle 20 ms den RSS (Hintergrund, nur /proc - kein Tk)."""
    def __init__(self):
        self.peak = 0.0
        self.stop = False
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        while not self.stop:
            value = rss_mb()
            if value > self.peak:
                self.peak = value
            _sleep(0.02)

    def reset(self):
        self.peak = rss_mb()


def count_widgets(widget):
    total = 1
    for child in widget.winfo_children():
        total += count_widgets(child)
    return total


class Bench:
    def __init__(self):
        app_gui.apply_appearance()
        self.errors = []
        if sys.platform.startswith("linux") and hasattr(app_gui, "LINUX_CLASS_NAME"):
            self.root = ctk.CTk(className=app_gui.LINUX_CLASS_NAME)
        else:
            self.root = ctk.CTk()
        self.root.report_callback_exception = lambda *exc: self.errors.append(
            "".join(traceback.format_exception(*exc))[-1500:])
        started = time.perf_counter()
        self.app = app_gui.FISIApp(self.root)
        self.root.geometry("1360x880+0+0")
        self.pump(0.3)
        self.start_ms = (time.perf_counter() - started) * 1000
        if PERF:
            self.app.perf.set_active(True)
        self.sampler = Sampler()

    def pump(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.root.update()
            time.sleep(0.005)

    def settle(self):
        self.root.update_idletasks()
        self.root.update()

    def preload_wait(self, timeout=300):
        pre = getattr(self.app, "preloader", None)
        if pre is None:
            return 0.0
        started = time.perf_counter()
        end = time.monotonic() + timeout
        # wie ein Nutzer, der nichts tut: Ereignisschleife laufen lassen
        while time.monotonic() < end and not pre.done:
            self.root.update()
            time.sleep(0.005)
        return (time.perf_counter() - started) * 1000

    def show(self, key):
        started = time.perf_counter()
        self.app.show_view(key)
        self.settle()
        return (time.perf_counter() - started) * 1000

    def built_views(self):
        return [k for k in self.app.views.keys() if self.app.views.built(k) is not None]


def timed_switch(bench, mode):
    """Ein Darstellungswechsel mit Teilzeiten."""
    app, root = bench.app, bench.root
    parts = {"abdeckung_ms": 0.0, "rahmen_ms": 0.0, "optionen_bauen_ms": 0.0,
             "update_ms": [], "update_idle_ms": [], "abbau_alt_ms": 0.0,
             "schlaf_ms": 0.0, "verwaiste_zeitgeber_ms": 0.0}
    originals = {}

    def wrap(obj, name, key, is_list=False):
        original = getattr(obj, name)
        own = name in getattr(obj, "__dict__", {})
        originals[(obj, name)] = (original, own)

        def wrapper(*args, **kwargs):
            started = time.perf_counter()
            try:
                return original(*args, **kwargs)
            finally:
                ms = (time.perf_counter() - started) * 1000
                if is_list:
                    parts[key].append(round(ms, 1))
                else:
                    parts[key] += ms
        setattr(obj, name, wrapper)

    wrap(app, "_show_busy", "abdeckung_ms")
    wrap(app, "_build_ui", "rahmen_ms")
    wrap(app, "show_view", "optionen_bauen_ms")
    wrap(root, "update", "update_ms", True)
    wrap(root, "update_idletasks", "update_idle_ms", True)
    wrap(app.container, "destroy", "abbau_alt_ms")
    wrap(app, "_cancel_orphaned_timers", "verwaiste_zeitgeber_ms")
    for key in ("umfaerben_ms", "spieltabellen_ms", "eingaben_sichern_ms", "messung_ms",
                "vorlader_start_ms"):
        parts[key] = 0.0
    wrap(app_gui, "apply_appearance", "umfaerben_ms")
    wrap(app_gui.fisi_game_gui, "refresh_theme_tables", "spieltabellen_ms")
    wrap(app, "flush_inputs", "eingaben_sichern_ms")
    wrap(app.perf, "theme", "messung_ms")
    wrap(app.preloader, "start", "vorlader_start_ms")
    sleep = time.sleep

    def timed_sleep(seconds):
        parts["schlaf_ms"] += seconds * 1000
        sleep(seconds)
    app_gui.time.sleep = timed_sleep
    before_widgets = count_widgets(root)
    before_views = bench.built_views()
    gc.collect()
    rss_before = rss_mb()
    bench.sampler.reset()
    started = time.perf_counter()
    try:
        app.change_color(mode=mode)
        total = (time.perf_counter() - started) * 1000
        bench.settle()
        total_drawn = (time.perf_counter() - started) * 1000
    finally:
        app_gui.time.sleep = sleep
        for (obj, name), (original, own) in originals.items():
            if own:
                setattr(obj, name, original)
            else:
                delattr(obj, name)
    peak = bench.sampler.peak
    for key in ("abdeckung_ms", "rahmen_ms", "optionen_bauen_ms", "abbau_alt_ms",
                "schlaf_ms", "verwaiste_zeitgeber_ms", "umfaerben_ms", "spieltabellen_ms",
                "eingaben_sichern_ms", "messung_ms", "vorlader_start_ms"):
        parts[key] = round(parts[key], 1)
    return dict(mode=mode, gesamt_ms=round(total), bis_gezeichnet_ms=round(total_drawn),
                elemente_vorher=before_widgets, ansichten_vorher=len(before_views),
                elemente_nachher=count_widgets(root),
                rss_vorher=round(rss_before, 1), rss_spitze=round(peak, 1),
                rss_nachher=round(rss_mb(), 1), **parts)


def main():
    result = {"quelle": SRC, "warten": WAIT, "perf": PERF, "fehler": []}
    bench = Bench()
    app, root = bench.app, bench.root
    lean = os.environ.get("MESS_OHNE_VORLADEN") == "1"
    if lean:
        # Gegenprobe Skalierung: nichts vorladen, keine Seitenrunde - beim
        # Wechsel existieren nur Dashboard und Optionen
        app.preloader.queue = []
        app.preloader.done = True
        app.preloader.start = lambda *args, **kwargs: None
        app.preloader.add_game = lambda *args, **kwargs: None
    result["version"] = app_gui.APP_VERSION
    result["start_ms"] = round(bench.start_ms)
    result["rss_start"] = round(rss_mb(), 1)
    result["elemente_start"] = count_widgets(root)
    bench.sampler.reset()
    result["vorladen_ms"] = round(bench.preload_wait())
    if os.environ.get("MESS_SPIEL", "1") == "1" and not lean:
        # Spielstand anlegen (wie bei Nico), dann werden die Spielansichten
        # mit ihren Reitern zusaetzlich vorgeladen
        bench.show("game")
        app.views["game"]._new_slot(1)
        bench.settle()
        result["vorladen_spiel_ms"] = round(bench.preload_wait())
    result["rss_nach_vorladen"] = round(rss_mb(), 1)
    result["rss_spitze_vorladen"] = round(bench.sampler.peak, 1)
    result["elemente_nach_vorladen"] = count_widgets(root)
    result["vorladen_schritte"] = {"%s:%s" % (t[0], "/".join(t[1:])): ms
                                   for t, ms in app.preloader.step_ms.items()}
    pages = {}
    for key in () if lean else ("dashboard", "cards", "quiz", "progress", "notebook", "calc",
                "ap1scenarios", "scenarios", "testproject", "abschluss", "help", "settings"):
        pages[key] = round(bench.show(key), 1)
    result["seitenrunde_ms"] = pages
    result["rss_nach_seiten"] = round(rss_mb(), 1)
    result["elemente_nach_seiten"] = count_widgets(root)
    result["opt_elemente"] = count_widgets(app.views["settings"])
    switches = []
    for index in range(SWITCHES):
        bench.show("settings")
        mode = fisi_theme.MODE_LIGHT if fisi_theme.current_mode != fisi_theme.MODE_LIGHT \
            else fisi_theme.MODE_DARK
        profiler = None
        if PROFILE_AT == index + 1:
            profiler = cProfile.Profile()
            profiler.enable()
        row = timed_switch(bench, mode)
        if profiler is not None:
            profiler.disable()
            stream = io.StringIO()
            stats = pstats.Stats(profiler, stream=stream)
            stats.sort_stats("cumulative").print_stats(60)
            stats.sort_stats("tottime").print_stats(40)
            with open(OUT.replace(".json", "_profil.txt"), "w") as handle:
                handle.write(stream.getvalue())
            stats.dump_stats(OUT.replace(".json", ".prof"))
        row["nr"] = index + 1
        row["opt_elemente"] = count_widgets(app.views["settings"])
        # Seiten dazwischen, dann Vorladen wie ein ruhender Nutzer abwarten
        visits = {}
        for key in () if lean else ("dashboard", "progress", "cards"):
            visits[key] = round(bench.show(key), 1)
        row["besuche_ms"] = visits
        bench.sampler.reset()
        if WAIT:
            row["vorladen_ms"] = round(bench.preload_wait())
        else:
            bench.pump(0.3)
        row["rss_spitze_vorladen"] = round(bench.sampler.peak, 1)
        row["elemente_danach"] = count_widgets(root)
        row["rss_danach"] = round(rss_mb(), 1)
        row["bildspeicher_mb"] = round(fisi_widgets._IMAGE_CACHE.bytes / 2**20, 1) \
            if hasattr(fisi_widgets._IMAGE_CACHE, "bytes") else None
        switches.append(row)
        print(json.dumps({k: row[k] for k in ("nr", "gesamt_ms", "elemente_vorher",
                                             "abbau_alt_ms", "optionen_bauen_ms",
                                             "rss_spitze", "rss_danach")}), flush=True)
    result["wechsel"] = switches
    result["fehler"] = bench.errors
    # Leistungsmessung des Programms mitnehmen
    try:
        app.perf.rec.flush()
        with open(app.perf.rec.path, encoding="utf-8") as handle:
            result["messdatei"] = handle.read()
    except Exception as error:
        result["messdatei"] = "nicht lesbar: %r" % error
    bench.sampler.stop = True
    # Schliessen wie im Programm, Dauer des Abbaus messen
    started = time.perf_counter()
    app_gui.EXIT_GRACE_SECONDS = 3600
    app.on_close(final_sync=False)
    result["schliessen_on_close_ms"] = round((time.perf_counter() - started) * 1000)
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=1, ensure_ascii=False)
    shutil.rmtree(folder, ignore_errors=True)


if __name__ == "__main__":
    main()
