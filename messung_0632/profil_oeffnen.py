#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""0.63.2 A13 (S5c, M0/M1): Zeit je Bauteil beim ersten Oeffnen des Rechners
(nur Messung, kein Teil des Programms, Zweig messung-0632, nie mergen).

Teilplan S5 Abschnitt 4.4 Schritt 1. Startet eine Programmfassung (Ordner als
Argument) wie mess_rechner_0631.py (leere Wegwerf-Datenbank, eigenes HOME,
FISI_VORLADEN wie gesetzt, wartet auf das Vorladen und 0,5 s Ruhe) und misst
dann EINMAL "Rechner oeffnen (erstes Mal)" = show_view("calc") +
update_idletasks() + update() wie mess_rechner_0631.py:110-113.

MESS_ART=teile  Zeitmesser um Konstruktoren und Hilfsfunktionen (Liste ZIELE,
                fehlende werden uebersprungen und genannt): Aufrufe, Zeit
                inklusive und exklusiv (ohne verschachtelte gemessene Aufrufe);
                dazu Tk-Rueckrufe (Bindungen wie <Configure>, after/after_idle)
                je Funktion in update_idletasks()/update(), Zahl der Widgets
                der Rechner-Ansicht und des ganzen Fensters. Phasen getrennt:
                show_view, update_idletasks, update.
MESS_ART=cprofile  dasselbe Oeffnen unter cProfile (ohne Zeitmesser):
                Top 40 kumuliert, Top 30 exklusiv, exklusive Zeit je Datei.

Aufruf: MESS_STAND=0625|0631 MESS_ART=teile|cprofile FISI_VORLADEN=0|normal \\
        python profil_oeffnen.py ORDNER AUSGABE.json
Ausgabe zusaetzlich Zeilen "PROF ...". Rueckgabe 3 (ohne Ergebnisdatei), wenn
die Ansicht nicht aufgeht oder eine Fehlermeldung kaeme."""
import collections
import cProfile
import functools
import json
import os
import pstats
import sys
import tempfile
import time
import traceback

SRC = os.path.abspath(sys.argv[1])
OUT = os.path.abspath(sys.argv[2])
STAND = os.environ.get("MESS_STAND", "")
ART = os.environ.get("MESS_ART", "teile")
if not STAND or ART not in ("teile", "cprofile"):
    print("ABBRUCH: MESS_STAND fehlt oder MESS_ART unbekannt (%r, %r)" % (STAND, ART))
    sys.stdout.flush()
    os._exit(3)
folder = tempfile.mkdtemp(prefix="fisi prof0632 ")
os.environ["FISI_DB_PATH"] = os.path.join(folder, "test.db")
os.environ["FISI_SELFTEST"] = os.path.join(folder, "log.txt")
os.environ["HOME"] = folder
os.environ["APPDATA"] = folder
os.environ["USERPROFILE"] = folder
sys.path.insert(0, SRC)
os.chdir(SRC)
import tkinter  # noqa: E402
import customtkinter as ctk  # noqa: E402
import app_gui  # noqa: E402
import fisi_widgets  # noqa: E402

VORLADEN = os.environ.get("FISI_VORLADEN", "normal")


def abbruch(grund):
    print("ABBRUCH (%s %s vorladen=%s): %s" % (STAND, ART, VORLADEN, grund))
    sys.stdout.flush()
    os._exit(3)


def _keine_meldung(title, text, *a, **k):
    abbruch("Fehlermeldung statt Ergebnis: %s: %s" % (title, text))


app_gui.messagebox.showerror = _keine_meldung
app_gui.messagebox.showwarning = _keine_meldung
app_gui.UpdateController.auto_check = lambda self: None
app_gui.SyncController.auto_start = lambda self: None

# ---------------------------------------------------------------- Zeitmesser
AKTIV = [False]
STAPEL = []                       # [label, start, kindzeit]
WERTE = collections.OrderedDict()  # label -> [aufrufe, inkl_s, exkl_s]
FEHLT = []


def _eintrag(label):
    return WERTE.setdefault(label, [0, 0.0, 0.0])


def _messe(label, func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not AKTIV[0]:
            return func(*args, **kwargs)
        name = label
        if label == "make_text":    # je Umbruch-Art getrennt (ab 0.63.1 wrap="none")
            name = "make_text[wrap=%s]" % kwargs.get("wrap", args[4] if len(args) > 4 else "word")
        frame = [name, time.perf_counter(), 0.0]
        STAPEL.append(frame)
        try:
            return func(*args, **kwargs)
        finally:
            dauer = time.perf_counter() - frame[1]
            STAPEL.pop()
            werte = _eintrag(name)
            werte[0] += 1
            werte[1] += dauer
            werte[2] += dauer - frame[2]
            if STAPEL:
                STAPEL[-1][2] += dauer
    wrapper._prof_original = func
    return wrapper


MODULE = [app_gui, fisi_widgets] + [sys.modules[n] for n in ("fisi_core", "fisi_theme", "fisi_game_gui")
                                    if n in sys.modules]

# (Besitzer-Name, Attribut): Besitzer ist eine Klasse aus app_gui/fisi_widgets
# oder "func" fuer eine Modul-Funktion (in allen MODULE ersetzt, wo gebunden)
ZIELE = [
    ("FISIApp", "_show_view"), ("FISIApp", "_show_loading"), ("FISIApp", "_hide_loading"),
    ("LoadingHint", "__enter__"), ("LoadingHint", "__exit__"), ("PerfMonitor", "page"),
    ("ScrollArea", "__init__"), ("View", "__init__"),
    ("CalcView", "build"), ("CalcView", "_build_ups"), ("CalcView", "_build_info_toggle"),
    ("CalcView", "_schedule_fit"), ("CalcView", "_fit"), ("CalcView", "prepare"),
    ("CalcView", "available_width"), ("CalcView", "_show_ups_task"), ("CalcView", "calc_ups"),
    ("TrainerPanel", "__init__"), ("TrainerPanel", "start_round"), ("TrainerPanel", "load_task"),
    ("TrainerPanel", "show_stats"),
    ("SubnetCalc", "__init__"), ("SubnetCalc", "build_mode"), ("SubnetCalc", "build_rest"),
    ("SubnetCalc", "_build_view"), ("SubnetCalc", "_build_pager"), ("SubnetCalc", "_fit_box"),
    ("SubnetCalc", "_schedule_refit"), ("SubnetCalc", "_refit"), ("SubnetCalc", "put"),
    ("SubnetCalc", "set_view"), ("SubnetCalc", "set_mode"),
    ("Card", "__init__"), ("PillGroup", "__init__"), ("EntryBox", "__init__"),
    ("NeoButton", "__init__"), ("NumberStepper", "__init__"), ("UpsDiagram", "__init__"),
    ("Divider", "__init__"),
    ("ctk.CTkTextbox", "__init__"), ("ctk.CTkTextbox", "_check_if_scrollbars_needed"),
    ("ctk.CTkScrollbar", "__init__"), ("ctk.CTkEntry", "__init__"), ("ctk.CTkLabel", "__init__"),
    ("ctk.CTkFrame", "__init__"),
    ("func", "make_text"), ("func", "make_label"), ("func", "set_text"),
    ("func", "transparent_frame"), ("func", "ctk_image"), ("func", "text_width"),
    ("func", "fit_lines"), ("func", "fit_text_height"), ("func", "tk_font"),
    ("func", "rounded_gradient"), ("func", "triangle_image"), ("func", "symbol_image"),
    ("func", "subnet_core"), ("func", "box_chars"),
]


def _klasse(name):
    if name.startswith("ctk."):
        cls = getattr(ctk, name[4:], None)
        return cls if isinstance(cls, type) else None
    for mod in (app_gui, fisi_widgets):
        cls = getattr(mod, name, None)
        if isinstance(cls, type):
            return cls
    return None


def installieren():
    for owner, attr in ZIELE:
        label = attr if owner == "func" else "%s.%s" % (owner, attr)
        if owner == "func":
            orig = None
            for mod in MODULE:
                if callable(getattr(mod, attr, None)):
                    orig = getattr(mod, attr)
                    break
            if orig is None:
                FEHLT.append(label)
                continue
            wrapped = _messe(label, orig)
            for mod in MODULE:
                if getattr(mod, attr, None) is orig:
                    setattr(mod, attr, wrapped)
            continue
        cls = _klasse(owner)
        if cls is None or not hasattr(cls, attr):
            FEHLT.append(label)
            continue
        # vererbte Methode: auf der Klasse selbst ablegen (gilt fuer Unterklassen,
        # die sie nicht ueberschreiben)
        setattr(cls, attr, _messe(label, getattr(cls, attr)))


RUECKRUFE = collections.OrderedDict()   # phase|name -> [zahl, s]
PHASE = ["-"]


def _ruf_name(func):
    name = getattr(func, "__qualname__", None) or repr(func)
    if name.endswith("callit") and getattr(func, "__closure__", None):
        for var, cell in zip(func.__code__.co_freevars, func.__closure__):
            if var == "func":
                try:
                    inner = cell.cell_contents
                except ValueError:
                    break
                return "after:" + (getattr(inner, "__qualname__", None) or repr(inner))
    mod = getattr(func, "__module__", "") or ""
    return "%s.%s" % (mod, name) if mod and mod != "__main__" else name


_call_orig = tkinter.CallWrapper.__call__


def _call(self, *args):
    if not AKTIV[0]:
        return _call_orig(self, *args)
    a = time.perf_counter()
    try:
        return _call_orig(self, *args)
    finally:
        werte = RUECKRUFE.setdefault("%s|%s" % (PHASE[0], _ruf_name(self.func)), [0, 0.0])
        werte[0] += 1
        werte[1] += time.perf_counter() - a


def zaehle(widget):
    n = 1
    for child in widget.winfo_children():
        n += zaehle(child)
    return n


# ---------------------------------------------------------------- Ablauf
if ART == "teile":
    installieren()
    tkinter.CallWrapper.__call__ = _call

app_gui.apply_appearance()
root = ctk.CTk()
app = app_gui.FISIApp(root)
root.geometry("1360x880+0+0")

end = time.monotonic() + 240
while time.monotonic() < end and not app.preloader.done:
    root.update()
    time.sleep(0.005)
end = time.monotonic() + 0.5
while time.monotonic() < end:
    root.update()
    time.sleep(0.01)

res = {"stand": STAND, "art": ART, "version": app_gui.APP_VERSION, "vorladen": VORLADEN,
       "vorladen_fertig": bool(app.preloader.done),
       "calc_vorgeladen": app.views.built("calc") is not None,
       "widgets_vorher": zaehle(root)}

try:
    profil = cProfile.Profile() if ART == "cprofile" else None
    AKTIV[0] = True
    if profil:
        profil.enable()
    t0 = time.perf_counter()
    PHASE[0] = "show_view"
    app.show_view("calc")
    t1 = time.perf_counter()
    PHASE[0] = "update_idletasks"
    root.update_idletasks()
    t2 = time.perf_counter()
    PHASE[0] = "update"
    root.update()
    t3 = time.perf_counter()
    if profil:
        profil.disable()
    AKTIV[0] = False
    PHASE[0] = "-"
    if app.current != "calc":
        abbruch("Rechner nicht offen")
    res["oeffnen_ms"] = round((t3 - t0) * 1000, 1)
    res["phasen_ms"] = {"show_view": round((t1 - t0) * 1000, 1),
                        "update_idletasks": round((t2 - t1) * 1000, 1),
                        "update": round((t3 - t2) * 1000, 1)}
    view = app.views["calc"]
    res["widgets_rechner"] = zaehle(view)
    res["widgets_fenster"] = zaehle(root)
    # zweites Oeffnen (wie mess_rechner: ueber die Startseite), ohne Zeitmesser
    app.show_view("dashboard")
    root.update_idletasks()
    root.update()
    a = time.perf_counter()
    app.show_view("calc")
    root.update_idletasks()
    root.update()
    res["wieder_ms"] = round((time.perf_counter() - a) * 1000, 1)
except SystemExit:
    raise
except Exception:   # noqa: BLE001
    abbruch("Ausnahme:\n" + traceback.format_exc())

kopf = "PROF %s %s vorladen=%s" % (STAND, ART, VORLADEN)
print("%s | oeffnen %.1f | show_view %.1f | update_idletasks %.1f | update %.1f | wieder %.1f"
      " | widgets rechner %d fenster %d (vorher %d)"
      % (kopf, res["oeffnen_ms"], res["phasen_ms"]["show_view"], res["phasen_ms"]["update_idletasks"],
         res["phasen_ms"]["update"], res["wieder_ms"], res["widgets_rechner"], res["widgets_fenster"],
         res["widgets_vorher"]))
if ART == "teile":
    res["fehlt"] = FEHLT
    res["teile"] = {k: {"n": v[0], "inkl_ms": round(v[1] * 1000, 2), "exkl_ms": round(v[2] * 1000, 2)}
                    for k, v in WERTE.items()}
    res["rueckrufe"] = {k: {"n": v[0], "ms": round(v[1] * 1000, 2)} for k, v in RUECKRUFE.items()}
    print("%s | nicht vorhanden: %s" % (kopf, ", ".join(FEHLT) or "-"))
    for k, v in sorted(res["teile"].items(), key=lambda kv: -kv[1]["inkl_ms"]):
        print("%s | teil %-34s n=%4d inkl %8.1f exkl %8.1f" % (kopf, k, v["n"], v["inkl_ms"], v["exkl_ms"]))
    for k, v in sorted(res["rueckrufe"].items(), key=lambda kv: -kv[1]["ms"])[:40]:
        print("%s | ruf %-60s n=%4d %8.1f" % (kopf, k, v["n"], v["ms"]))
else:
    stats = pstats.Stats(profil)
    roh = stats.stats   # (datei, zeile, name) -> (cc, nc, tt, ct, callers)

    def kurz(key):
        datei, zeile, name = key
        return "%s:%d(%s)" % (os.path.basename(datei), zeile, name)

    kum = sorted(roh.items(), key=lambda kv: -kv[1][3])[:40]
    exk = sorted(roh.items(), key=lambda kv: -kv[1][2])[:30]
    je_datei = collections.Counter()
    for (datei, _z, _n), werte in roh.items():
        je_datei[os.path.basename(datei) or datei] += werte[2]
    res["kumuliert"] = [[kurz(k), v[1], round(v[3] * 1000, 2)] for k, v in kum]
    res["exklusiv"] = [[kurz(k), v[1], round(v[2] * 1000, 2)] for k, v in exk]
    res["je_datei_ms"] = {k: round(v * 1000, 2) for k, v in je_datei.most_common(25)}
    for name, n, ms in res["kumuliert"]:
        print("%s | kum %-70s n=%6d %8.1f" % (kopf, name, n, ms))
    for name, n, ms in res["exklusiv"]:
        print("%s | exk %-70s n=%6d %8.1f" % (kopf, name, n, ms))
    for name, ms in res["je_datei_ms"].items():
        print("%s | datei %-40s %8.1f" % (kopf, name, ms))
with open(OUT, "w", encoding="utf-8") as h:
    json.dump(res, h, indent=1)
sys.stdout.flush()
os._exit(0)
