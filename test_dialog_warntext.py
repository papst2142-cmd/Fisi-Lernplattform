#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer 0.63.2: Warntext vor "Alles ersetzen" ganz lesbar (Befund S1 der
dritten Gegenpruefung FG-81; Weisung zu Meldung 38 und 40, Frage 2;
Testplan bau_0.63.2/dialog_warntext/Testplan_Dialog.md, Ablaeufe D1-D9).

Bis d54397f zeigte der PC den Text (fsi.replace_question, zwei Absaetze) mit
messagebox.askyesno. Tk staucht diesen Dialog auf Bildschirmhoehe: der Text
war abgeschnitten, es gab keinen Bildlauf, die Knoepfe lagen unter dem
Bildschirmrand, "Sehr gross" wirkte nicht. Am Handy (FISIMobileApp.confirm)
liess sich der Inhalt nicht rollen.

Regeln (Testplan 0): Der Sollwert ist immer fsi.replace_question(backup) im
selben Lauf - der Text steht nie als Kopie in diesem Test (nur Anfang und
letzter Satz, siehe FIRST_WORDS/LAST_SENTENCE). Vergleich byte-genau.

PC (echtes Hauptfenster FISIApp, echter Weg SettingsView._replace_backup, je
Fall ein eigener Prozess auf einer eigenen Xvfb-Anzeige in echter
Bildschirmgroesse 1280x720 bzw. 1366x768, Schrift Normal und Sehr gross,
Hell und Dunkel; Zusatz je Bildschirm einmal mit CTk-Bildschirmfaktor 1,25
wie Windows bei 125 %):
  D1 Text im Textfeld byte-genau == replace_question, Durchreich-Probe
     (umhuellte Funktion mit Marke), keine Textkopie in dieser Datei,
  D2 Fenstertitel, Kartenueberschrift, Knoepfe "Ja"/"Nein", zweite
     Rueckfrage mit allen Argumenten,
  D3 Standard "Nein": Eingabetaste, Escape (an das Element mit dem Fokus,
     auch im Textfeld), Schliessen -> Abbruch; Tab auf "Ja" + Eingabe und
     Klick "Ja" -> zweite Rueckfrage; Fenster gesperrt (grab) und danach frei.
     Schliessen: ClientMessage WM_DELETE_WINDOW an das Fenster (so meldet ein
     Fenstermanager den Schliessknopf; ohne Fenstermanager und ohne echten
     Schliessknopf) und zusaetzlich - als BEHELF so benannt - der Aufruf des
     Protokoll-Befehls,
  D4 nur diese Rueckfrage nutzt den Dialog (AST gegen d54397f + Kindlauf mit
     den anderen Rueckfragen der Optionen),
  D5 Text ganz erreichbar (Mausrad und Tastatur), letzte Zeile GANZ sichtbar
     (nicht nur angeschnitten), nicht seitlich abgeschnitten,
  D6 Knoepfe ganz sichtbar: offen, nach dem Rollen, groesser gezogen,
     kleinstes Fenster; Fenster nie groesser als Bildschirm minus Raender,
  D7 Breite und Schriften folgen der Schriftstufe, Farben der Darstellung,
  V7 laesst sich das Fenster nicht sperren (grab_set), steht das einmal in
     fehler.log; der Dialog antwortet wie sonst.
Handy (Struktur, ohne Flet-Anzeige):
  D8 confirm-Dialog rollbar, Text byte-genau, Durchreich-Probe,
  D9 kurze Rueckfragen: alle Eigenschaften wie d54397f ausser scrollable.
Windows/macOS: nicht geprueft (PC-Teil nur unter Linux mit Xvfb; die
Windows-Liste in pruefung/ci_tests.sh enthaelt die Datei nicht, kein
macOS-Testschritt) - Testliste fuer Nico.

Start:  python test_dialog_warntext.py   (PC-Teil nur unter Linux mit Xvfb)
Anderer Code (z. B. Gegenprobe gegen d54397f):  DIALOG_CODE=<ordner> python ...
"""

import ast
import dataclasses
import enum
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("DIALOG_CODE") or HERE)
sys.path.insert(0, CODE)
sys.path.insert(1, os.path.join(CODE, "mobile", "src"))

_TMP = tempfile.mkdtemp(prefix="fisi_dialog_warntext_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "start.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(_TMP, "selbsttest.log"))
os.environ["HOME"] = _TMP
os.environ["APPDATA"] = _TMP
os.environ["FISI_VORLADEN"] = "0"

import fisi_sicherung as fsi  # noqa: E402

# Testplan 0.1: die einzigen erlaubten festen Bruchstuecke des Texts
LAST_SENTENCE = "Bewahre die Sicherungsdatei deshalb auf."
FIRST_WORDS = "Der komplette Lernstand dieses Geräts"
STAMP = "13.10.2026 21:47"
MARKE = "\n\n[PRUEFMARKE 7f3a]"

# (Bildschirm, Schrift, Darstellung, Bildschirmfaktor)
FAELLE = [((1280, 720), "normal", "hell", 1.0), ((1280, 720), "sehr_gross", "dunkel", 1.0),
          ((1366, 768), "normal", "dunkel", 1.0), ((1366, 768), "sehr_gross", "hell", 1.0)]
# Testplan O4 (Hauptstrang: ja): je Bildschirm einmal wie Windows bei 125 %
FAELLE_125 = [((1366, 768), "normal", "hell", 1.25), ((1280, 720), "sehr_gross", "dunkel", 1.25)]
ARTEN = ["messen", "tastatur", "klick_ja", "klick_nein", "tab_ja_eingabe", "eingabe", "esc",
         "esc_textfeld", "schliessen_x11", "schliessen_protokoll", "grab_fehlt"]
ARTEN_125 = ["messen", "tastatur"]
ABBRUCH = ["klick_nein", "eingabe", "esc", "esc_textfeld", "schliessen_x11",
           "schliessen_protokoll", "grab_fehlt"]
WEITER = ["klick_ja", "tab_ja_eingabe"]

CHILD = r"""
import ctypes, json, os, sys, time, types
code, schrift, modus, out, skal, arten, marke = sys.argv[1:8]
skal = float(skal)
arten = arten.split(",")
sys.path.insert(0, code)
os.chdir(code)
import fisi_theme
fisi_theme.save_font_size(schrift)
fisi_theme.save_mode(modus)
import fisi_hilfe
fisi_hilfe.mark_tour_seen()
import tkinter as tk
from tkinter import messagebox
import tkinter.font as tkfont
gefragt = []
gezeigt = []
def _ask(title=None, message=None, **kw):
    gefragt.append({"title": title, "message": str(message),
                    "kw": dict((k, str(v)) for k, v in sorted(kw.items()))})
    return False
messagebox.askyesno = _ask
messagebox.showinfo = lambda *a, **k: gezeigt.append(["showinfo"] + [str(x) for x in a])
messagebox.showerror = lambda *a, **k: gezeigt.append(["showerror"] + [str(x) for x in a])
import customtkinter as ctk
if skal != 1.0:
    # wie Windows bei 125 %%: CTk liest dort diesen Faktor vom Bildschirm
    ctk.ScalingTracker.get_window_dpi_scaling = classmethod(lambda cls, window: skal)
import app_gui
import fisi_core
app_gui.UpdateController.auto_check = lambda self: None
app_gui.SyncController.auto_start = lambda self: None
app_gui.fsi.backup_summary = lambda b: {"erstellt": %(stamp)r}
ORIGINAL = app_gui.fsi.replace_question({})
if marke:
    _orig = app_gui.fsi.replace_question
    app_gui.fsi.replace_question = lambda b: _orig(b) + marke
SOLL = app_gui.fsi.replace_question({})
LAST = %(last)r
DLG = getattr(app_gui, "LongQuestionDialog", None)
zaehler = [0]
if DLG is not None:
    _init = DLG.__init__
    def _gezaehlt(self, *a, **k):
        zaehler[0] += 1
        _init(self, *a, **k)
    DLG.__init__ = _gezaehlt
app_gui.apply_appearance()
root = ctk.CTk()
app = app_gui.FISIApp(root)
root.geometry("1120x720+0+0")
res = {"screen": [root.winfo_screenwidth(), root.winfo_screenheight()],
       "faktor": fisi_theme.font_factor(), "skal": skal, "laeufe": [],
       "soll_kind": SOLL, "original_kind": ORIGINAL,
       "fehlerlog": fisi_core.error_log_path()}
fake = types.SimpleNamespace(app=app, db=None)

def settle(n=8):
    for _ in range(n):
        root.update()
        time.sleep(0.03)

def dialogs():
    return [w for w in root.winfo_children() if type(w).__name__ == "LongQuestionDialog"]

def tk_box():
    try:
        return bool(root.tk.call("winfo", "exists", ".__tk__messagebox"))
    except Exception:
        return False

def rect(w):
    return [w.winfo_rootx(), w.winfo_rooty(), w.winfo_width(), w.winfo_height(),
            int(w.winfo_viewable())]

def zustand(d):
    return {"fenster": rect(d), "knoepfe": {"Ja": rect(d.btn_yes), "Nein": rect(d.btn_no)},
            "yview": list(d.text._textbox.yview()), "xview": list(d.text._textbox.xview())}

def zeile_ganz(d, index):
    # Liegt die Anzeigezeile von index GANZ im sichtbaren Teil des Textfelds
    # und ueber den Knoepfen? (bbox allein ist auch bei halber Zeile wahr)
    box = d.text._textbox
    info = box.dlineinfo(index)
    if not info:
        return {"ganz": False, "grund": "nicht angezeigt"}
    _x, y, _w, h, _b = info
    inset = int(float(str(box.cget("borderwidth")))) \
        + int(float(str(box.cget("highlightthickness")))) + int(float(str(box.cget("pady"))))
    oben = box.winfo_rooty() + y
    unten = oben + h
    grenze = min(box.winfo_rooty() + box.winfo_height() - inset, d.btn_yes.winfo_rooty(),
                 d.btn_no.winfo_rooty(), d.winfo_rooty() + d.winfo_height())
    return {"ganz": oben >= box.winfo_rooty() + inset and unten <= grenze,
            "oben": oben, "unten": unten, "grenze": grenze, "h": h}

def letzter_satz(d):
    box = d.text._textbox
    start = box.search(LAST, "1.0", "end")
    if not start:
        return {"gefunden": False, "ganz": False}
    a, e = zeile_ganz(d, start), zeile_ganz(d, "end-1c")
    return {"gefunden": True, "ganz": a["ganz"] and e["ganz"], "anfang": a, "ende": e}

def maus_bis_ende(d):
    box = d.text._textbox
    for step in range(300):
        before = box.yview()
        box.event_generate("<Button-5>", x=10, y=10)
        settle(2)
        if box.yview() == before:
            return step
    return -1

def tab_bis(d, ziel, n=8):
    weg = []
    for _ in range(n):
        w = d.focus_get()
        weg.append(str(w or ""))
        if w is not None and str(w) == str(ziel):
            return weg, True
        (w or d).event_generate("<Tab>")
        settle(2)
    w = d.focus_get()
    weg.append(str(w or ""))
    return weg, w is not None and str(w) == str(ziel)

def klick(knopf):
    # echte Maus-Ereignisse auf die Beschriftung des Knopfs (NeoButton ist
    # ein CTkLabel; die Antwort kommt schon mit dem Druecken)
    inner = knopf._label
    inner.event_generate("<Enter>", x=5, y=5)
    inner.event_generate("<Button-1>", x=5, y=5)
    try:
        inner.event_generate("<ButtonRelease-1>", x=5, y=5)
    except tk.TclError:
        pass                               # Fenster ist schon zu

def x11_schliessen(d):
    # ClientMessage WM_PROTOCOLS/WM_DELETE_WINDOW an das Tk-Fenster - so
    # meldet ein Fenstermanager den Schliessknopf (hier ohne Fenstermanager)
    x = ctypes.cdll.LoadLibrary("libX11.so.6")
    x.XOpenDisplay.restype = ctypes.c_void_p
    x.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x.XInternAtom.restype = ctypes.c_ulong
    x.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
    class Msg(ctypes.Structure):
        _fields_ = [("type", ctypes.c_int), ("serial", ctypes.c_ulong),
                    ("send_event", ctypes.c_int), ("display", ctypes.c_void_p),
                    ("window", ctypes.c_ulong), ("message_type", ctypes.c_ulong),
                    ("format", ctypes.c_int), ("l", ctypes.c_long * 5)]
    class Ev(ctypes.Union):
        _fields_ = [("xclient", Msg), ("pad", ctypes.c_long * 24)]
    x.XSendEvent.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_long,
                             ctypes.POINTER(Ev)]
    x.XFlush.argtypes = [ctypes.c_void_p]
    x.XCloseDisplay.argtypes = [ctypes.c_void_p]
    dpy = x.XOpenDisplay(None)
    win = int(d.tk.call("wm", "frame", d._w), 16)
    ev = Ev()
    ev.xclient.type = 33                  # ClientMessage
    ev.xclient.window = win
    ev.xclient.message_type = x.XInternAtom(dpy, b"WM_PROTOCOLS", 0)
    ev.xclient.format = 32
    ev.xclient.l[0] = x.XInternAtom(dpy, b"WM_DELETE_WINDOW", 0)
    ev.xclient.l[1] = 0
    gesendet = x.XSendEvent(dpy, win, 0, 0, ctypes.byref(ev))
    x.XFlush(dpy)
    x.XCloseDisplay(dpy)
    return gesendet

def messen(d, lauf):
    box = d.text._textbox
    lauf["text_im_feld"] = box.get("1.0", "end-1c")
    lauf["titel"] = d.title()
    lauf["karte"] = d.card.title_label.cget("text") if d.card.title_label else None
    lauf["beschriftung"] = [d.btn_yes._caption, d.btn_no._caption]
    lauf["protokoll"] = str(d.protocol("WM_DELETE_WINDOW"))
    lauf["zeilenhoehe"] = tkfont.Font(font=box.cget("font")).metrics("linespace")
    lauf["knopfschrift"] = tkfont.Font(
        font=d.btn_no._label.cget("font")).metrics("linespace")
    lauf["scales"] = list(d._scales())
    lauf["farbe_feld"] = str(box.cget("bg"))
    lauf["soll_feld"] = d._apply_appearance_mode(d.text.cget("fg_color"))
    lauf["farbe_text"] = str(box.cget("fg"))
    lauf["c_card_alt"] = fisi_theme.C["card_alt"]
    lauf["c_text_soft"] = fisi_theme.C["text_soft"]
    lauf["a_offen"] = zustand(d)
    lauf["a_letzter"] = letzter_satz(d)
    lauf["schritte"] = maus_bis_ende(d)
    lauf["b_gerollt"] = zustand(d)
    lauf["b_letzter"] = letzter_satz(d)
    x0, y0, w0, h0 = d.winfo_rootx(), d.winfo_rooty(), d.winfo_width(), d.winfo_height()
    sw, sh = res["screen"]
    d.wm_geometry("%%dx%%d" %% (min(w0 + 60, sw - x0), min(h0 + 40, sh - y0)))
    settle(10)
    lauf["d_groesser"] = zustand(d)
    width, height = d.wm_minsize()
    d.wm_geometry("%%dx%%d" %% (width, height))
    settle(10)
    lauf["mindestgroesse"] = [width, height]
    lauf["c_klein"] = zustand(d)

def andere_rueckfragen(lauf):
    # D4: die anderen Rueckfragen der Optionen bleiben beim Systemfenster -
    # auch die lange zu geloeschten Spielstaenden
    lang = app_gui.fsi.deleted_question([{"lauf": i, "name": "Spielstand Nummer %%d mit "
                                          "einem recht langen Namen" %% i} for i in range(40)])
    app_gui.fsi.deleted_runs = lambda db, b: [{"lauf": i, "name": "S%%d" %% i}
                                               for i in range(40)]
    app_gui.fsi.deleted_question = lambda runs: lang
    app_gui.fsi.merge_backup = lambda *a, **k: 0
    app_gui.fisi_game.reset_question = lambda game: lang
    spiel = types.SimpleNamespace(game=types.SimpleNamespace(reload=lambda: None))
    attrappe = types.SimpleNamespace(
        app=types.SimpleNamespace(root=root, views={"game": spiel},
                                  notify_progress=lambda: None),
        db=types.SimpleNamespace(), _after_restore=lambda: None)
    vorher = zaehler[0]
    def schliesser():
        # falls doch ein Dialog aufgeht: zaehlen und schliessen, nicht haengen
        for w in dialogs():
            w.destroy()
        root.after(300, schliesser)
    root.after(300, schliesser)
    S = app_gui.SettingsView
    for call in (lambda: S.clear_history(attrappe), lambda: S.reset_records(attrappe),
                 lambda: S.reset_game(attrappe), lambda: S.reset_all(attrappe),
                 lambda: S._merge_backup(attrappe, {})):
        call()
        settle(2)
    lauf["andere_gefragt"] = [g["title"] for g in gefragt]
    lauf["lang_laenge"] = len(lang)
    lauf["dialoge_dabei"] = zaehler[0] - vorher

def one(art, laeufe):
    lauf = {"art": art, "dialog": "keiner"}
    def act():
        try:
            act_inner()
        except Exception:
            import traceback
            lauf["fehler"] = traceback.format_exc()
            for w in dialogs():
                w.destroy()
    def act_inner():
        settle()
        found = dialogs()
        lauf["dialog"] = "LongQuestionDialog" if found else (
            "tk_messagebox" if tk_box() else "keiner")
        if not found:
            if tk_box():
                root.tk.call(".__tk__messagebox.no", "invoke")
            return
        d = found[0]
        lauf["fokus"] = str(d.focus_get() or "")
        lauf["nein"] = str(d.btn_no)
        lauf["ja"] = str(d.btn_yes)
        lauf["textfeld"] = str(d.text._textbox)
        lauf["dialogpfad"] = str(d)
        lauf["grab_offen"] = str(root.grab_current() or "")
        if art == "messen":
            messen(d, lauf)
            klick(d.btn_no)
        elif art == "tastatur":
            lauf["tab_weg"], lauf["tab_erreicht"] = tab_bis(d, d.text._textbox)
            if not lauf["tab_erreicht"]:
                d.text._textbox.focus_set()          # wie ein Klick ins Feld
                settle(2)
            d.focus_get().event_generate("<Control-End>")
            settle(6)
            lauf["tastatur_yview"] = list(d.text._textbox.yview())
            lauf["tastatur_letzter"] = letzter_satz(d)
            klick(d.btn_no)
        elif art == "klick_ja":
            klick(d.btn_yes)
        elif art == "klick_nein":
            klick(d.btn_no)
        elif art == "tab_ja_eingabe":
            lauf["tab_weg"], lauf["tab_erreicht"] = tab_bis(d, d.btn_yes)
            d.focus_get().event_generate("<Return>")
        elif art == "eingabe":
            (d.focus_get() or d).event_generate("<Return>")
        elif art == "esc":
            (d.focus_get() or d).event_generate("<Escape>")
        elif art == "esc_textfeld":
            lauf["tab_weg"], lauf["tab_erreicht"] = tab_bis(d, d.text._textbox)
            if not lauf["tab_erreicht"]:
                d.text._textbox.focus_set()          # wie ein Klick ins Feld
                settle(2)
            lauf["fokus_vor_esc"] = str(d.focus_get() or "")
            d.focus_get().event_generate("<Escape>")
        elif art == "schliessen_x11":
            lauf["gesendet"] = x11_schliessen(d)
        elif art == "schliessen_protokoll":
            root.tk.call(d.protocol("WM_DELETE_WINDOW"))      # BEHELF
        elif art == "grab_fehlt":
            settle(40)                     # alle Versuche (20 x 50 ms) vorbei
            klick(d.btn_no)
        settle(4)
        lauf["offen_danach"] = bool(dialogs())
        lauf["grab_danach"] = str(root.grab_current() or "")
    del gefragt[:]
    if art == "andere":
        andere_rueckfragen(lauf)
        laeufe.append(lauf)
        return
    gesperrt = None
    if art == "grab_fehlt" and DLG is not None:
        gesperrt = DLG.grab_set
        def _kein_grab(self, *a):
            raise tk.TclError("grab failed: Probe")
        DLG.grab_set = _kein_grab
    try:
        root.after(1500, act)
        notbremse = root.after(30000, lambda: [w.destroy() for w in dialogs()])
        app_gui.SettingsView._replace_backup(fake, {})
        root.after_cancel(notbremse)
    finally:
        if gesperrt is not None:
            DLG.grab_set = gesperrt
    lauf["zweite_rueckfrage"] = list(gefragt)
    laeufe.append(lauf)

def run():
    try:
        for art in arten:
            one(art, res["laeufe"])
    except Exception:
        import traceback
        res["fehler"] = traceback.format_exc()
    try:
        with open(res["fehlerlog"], encoding="utf-8") as handle:
            res["fehlerlog_text"] = handle.read()
    except OSError:
        res["fehlerlog_text"] = ""
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(res, handle, ensure_ascii=False)

# Nicht aus einem after-Rueckruf heraus: Tk bedient Zeitgeber, die waehrend
# eines Zeitgeber-Rueckrufs angelegt werden, in dessen innerer Warteschleife
# (wait_window) nicht zuverlaessig.
end = time.time() + 2.5
while time.time() < end:
    settle(1)
run()
root.destroy()
""" % {"stamp": STAMP, "last": LAST_SENTENCE}


def _xvfb():
    if not sys.platform.startswith("linux"):
        return None
    return shutil.which("Xvfb")


def _start_display(size):
    """Eigene Xvfb-Anzeige in echter Bildschirmgroesse; liefert (Prozess, ":N")."""
    for number in range(140, 240):
        if os.path.exists("/tmp/.X%d-lock" % number):
            continue
        proc = subprocess.Popen(
            [_xvfb(), ":%d" % number, "-screen", "0", "%dx%dx24" % size, "-nolisten", "tcp"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            if os.path.exists("/tmp/.X11-unix/X%d" % number):
                return proc, ":%d" % number
            if proc.poll() is not None:
                break
            time.sleep(0.1)
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    raise RuntimeError("keine freie Xvfb-Anzeige")


def _run_child(size, schrift, modus, skal, arten, marke=""):
    home = tempfile.mkdtemp(prefix="home_", dir=_TMP)
    script = os.path.join(_TMP, "kind.py")
    with open(script, "w", encoding="utf-8") as handle:
        handle.write(CHILD)
    out = os.path.join(home, "ergebnis.json")
    proc, display = _start_display(size)
    try:
        env = dict(os.environ, DISPLAY=display, HOME=home, APPDATA=home,
                   FISI_DB_PATH=os.path.join(home, "kind.db"),
                   FISI_SELFTEST=os.path.join(home, "selbsttest.log"))
        done = subprocess.run([sys.executable, script, CODE, schrift, modus, out, str(skal),
                               ",".join(arten), marke], env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900)
    finally:
        proc.terminate()
        proc.wait()
    if not os.path.exists(out):
        raise AssertionError("Kindprozess ohne Ergebnis:\n" + done.stdout.decode(
            "utf-8", "replace")[-3000:])
    with open(out, encoding="utf-8") as handle:
        return json.load(handle)


def _soll():
    """replace_question im Testprozess (Code unter CODE), festes Datum."""
    original = fsi.backup_summary
    fsi.backup_summary = lambda b: {"erstellt": STAMP}
    try:
        return fsi.replace_question({})
    finally:
        fsi.backup_summary = original


def _bytegleich(test, ist, soll, wo):
    test.assertEqual(len(ist), len(soll), wo)
    test.assertEqual(ist.encode("utf-8"), soll.encode("utf-8"), wo)


@unittest.skipUnless(_xvfb(), "nur unter Linux mit Xvfb (eigene Anzeige je Bildschirmgroesse)")
class PCDialogTest(unittest.TestCase):
    ERGEBNISSE = {}

    @classmethod
    def ergebnis(cls, fall, arten=None, marke=""):
        key = (fall, marke)
        if key not in cls.ERGEBNISSE:
            if arten is None:
                arten = ARTEN_125 if fall[3] != 1.0 else ARTEN + (
                    ["andere"] if fall == FAELLE[0] else [])
            cls.ERGEBNISSE[key] = _run_child(*fall, arten=arten, marke=marke)
        return cls.ERGEBNISSE[key]

    def _laeufe(self, fall):
        res = self.ergebnis(fall)
        self.assertNotIn("fehler", res, res.get("fehler"))
        self.assertEqual(res["screen"], list(fall[0]), "Anzeige nicht in der Sollgroesse")
        laeufe = {lauf["art"]: lauf for lauf in res["laeufe"]}
        for art, lauf in laeufe.items():
            self.assertNotIn("fehler", lauf, "%s: %s" % (art, lauf.get("fehler")))
            if art != "andere":
                self.assertEqual(lauf["dialog"], "LongQuestionDialog",
                                 "kein rollbarer Dialog (%s: %s)" % (art, lauf))
        return res, laeufe

    def _messung(self, fall):
        res, laeufe = self._laeufe(fall)
        return res, laeufe["messen"]

    # ------------------------------------------------------------------ D1
    def test_d1_text_bytegenau_wie_replace_question(self):
        soll = _soll()
        self.assertEqual(soll.count("\n\n"), 1)
        self.assertTrue(soll.startswith(FIRST_WORDS))
        self.assertTrue(soll.endswith(LAST_SENTENCE))
        for fall in FAELLE + FAELLE_125:
            with self.subTest(fall=fall):
                res, m = self._messung(fall)
                _bytegleich(self, res["soll_kind"], soll, "Kind == Testprozess")
                _bytegleich(self, m["text_im_feld"], res["soll_kind"], "angezeigt")
                self.assertEqual(m["text_im_feld"].count("\n\n"), 1)
                self.assertIn(STAMP, m["text_im_feld"])
                for zeichen in ("–", "„", "“"):
                    self.assertEqual(m["text_im_feld"].count(zeichen), soll.count(zeichen))

    def test_d1_durchreich_probe_marke_kommt_an(self):
        """replace_question wird umhuellt (Marke angehaengt): angezeigt wird
        genau Original + Marke - der Aufruf reicht die Funktion durch."""
        res = self.ergebnis(FAELLE[2], arten=["messen"], marke=MARKE)
        self.assertNotIn("fehler", res, res.get("fehler"))
        m = res["laeufe"][0]
        self.assertEqual(m["dialog"], "LongQuestionDialog")
        _bytegleich(self, res["original_kind"], _soll(), "Original")
        _bytegleich(self, m["text_im_feld"], res["original_kind"] + MARKE, "Durchreich-Probe")

    # ------------------------------------------------------------------ D2
    def test_d2_titel_knoepfe_zweite_rueckfrage(self):
        for fall in FAELLE:
            with self.subTest(fall=fall):
                _res, laeufe = self._laeufe(fall)
                m = laeufe["messen"]
                self.assertEqual(m["titel"], fsi.REPLACE_TITLE)
                # Kartenueberschrift (Card: Grossbuchstaben) - Aussehen entscheidet Nico
                self.assertEqual(m["karte"], fsi.REPLACE_TITLE.upper())
                self.assertEqual(m["beschriftung"], ["Ja", "Nein"])
                ja, nein = m["a_offen"]["knoepfe"]["Ja"], m["a_offen"]["knoepfe"]["Nein"]
                self.assertLess(ja[0], nein[0], "Reihenfolge Ja, Nein")
                for art in WEITER:
                    self.assertEqual(laeufe[art]["zweite_rueckfrage"], [{
                        "title": fsi.REPLACE_CONFIRM_TITLE, "message": fsi.REPLACE_CONFIRM,
                        "kw": {"default": "no", "icon": "warning"}}], art)

    # ------------------------------------------------------------------ D3
    def test_d3_standard_nein_eingabe_escape_schliessen(self):
        for fall in FAELLE:
            with self.subTest(fall=fall):
                _res, laeufe = self._laeufe(fall)
                self.assertEqual(sorted(a for a in laeufe if a != "andere"), sorted(ARTEN))
                for art, lauf in laeufe.items():
                    if art == "andere":
                        continue
                    self.assertEqual(lauf["fokus"], lauf["nein"], "Fokus beim Oeffnen (%s)" % art)
                    self.assertFalse(lauf["offen_danach"], art)
                    self.assertEqual(lauf["grab_danach"], "", art)
                    if art != "grab_fehlt":
                        self.assertEqual(lauf["grab_offen"], lauf["dialogpfad"],
                                         "Hauptfenster nicht gesperrt (%s)" % art)
                for art in ABBRUCH:
                    self.assertEqual(laeufe[art]["zweite_rueckfrage"], [], art)
                for art in WEITER:
                    self.assertEqual([g["title"] for g in laeufe[art]["zweite_rueckfrage"]],
                                     [fsi.REPLACE_CONFIRM_TITLE], art)
                self.assertTrue(laeufe["tab_ja_eingabe"]["tab_erreicht"],
                                laeufe["tab_ja_eingabe"]["tab_weg"])
                self.assertTrue(laeufe["esc_textfeld"]["tab_erreicht"])
                self.assertEqual(laeufe["esc_textfeld"]["fokus_vor_esc"],
                                 laeufe["esc_textfeld"]["textfeld"])
                self.assertEqual(laeufe["schliessen_x11"]["gesendet"], 1)
                self.assertTrue(laeufe["messen"]["protokoll"])

    def test_v7_ohne_sperre_eine_zeile_im_fehlerlog(self):
        """grab_set scheitert immer: Dialog antwortet wie sonst, fehler.log
        nennt es genau einmal (nicht still)."""
        for fall in FAELLE:
            with self.subTest(fall=fall):
                res, laeufe = self._laeufe(fall)
                lauf = laeufe["grab_fehlt"]
                self.assertEqual(lauf["grab_offen"], "")
                self.assertFalse(lauf["offen_danach"])
                self.assertEqual(lauf["zweite_rueckfrage"], [])
                zeilen = [z for z in res["fehlerlog_text"].splitlines()
                          if "liess sich nicht sperren" in z]
                self.assertEqual(len(zeilen), 1, res["fehlerlog_text"])
                self.assertIn('"%s"' % fsi.REPLACE_TITLE, zeilen[0])

    # ------------------------------------------------------------------ D4
    def test_d4_andere_rueckfragen_bleiben_beim_systemfenster(self):
        _res, laeufe = self._laeufe(FAELLE[0])
        lauf = laeufe["andere"]
        self.assertEqual(lauf["dialoge_dabei"], 0)
        self.assertEqual(lauf["andere_gefragt"], [
            "Historie löschen", "Bestenliste löschen", "Spielstand zurücksetzen",
            "Alles zurücksetzen", fsi.DELETED_TITLE])
        self.assertGreater(lauf["lang_laenge"], len(_soll()))

    # ------------------------------------------------------------------ D5
    def test_d5_text_ganz_erreichbar_maus_und_tastatur(self):
        for fall in FAELLE + FAELLE_125:
            with self.subTest(fall=fall):
                _res, laeufe = self._laeufe(fall)
                m = laeufe["messen"]
                self.assertEqual(m["a_offen"]["yview"][0], 0.0)
                self.assertEqual(m["a_offen"]["xview"], [0.0, 1.0], "seitlich abgeschnitten")
                self.assertGreaterEqual(m["schritte"], 0, "Mausrad endet nicht")
                self.assertEqual(m["b_gerollt"]["yview"][1], 1.0)
                self.assertTrue(m["b_letzter"]["gefunden"])
                self.assertTrue(m["b_letzter"]["ganz"], m["b_letzter"])
                t = laeufe["tastatur"]
                self.assertTrue(t["tab_erreicht"], "Textfeld per Tab nicht erreichbar %s"
                                % t["tab_weg"])
                self.assertEqual(t["tastatur_yview"][1], 1.0)
                self.assertTrue(t["tastatur_letzter"]["ganz"], t["tastatur_letzter"])
                if fall[1] == "sehr_gross":
                    # Rollen wird wirklich gebraucht (sonst prueft das nichts)
                    self.assertLess(m["a_offen"]["yview"][1], 1.0)
                    self.assertFalse(m["a_letzter"]["ganz"])

    # ------------------------------------------------------------------ D6
    def test_d6_knoepfe_immer_ganz_sichtbar(self):
        import app_gui as ag
        for fall in FAELLE + FAELLE_125:
            with self.subTest(fall=fall):
                res, m = self._messung(fall)
                sw, sh = res["screen"]
                window = m["scales"][0]
                for name in ("a_offen", "b_gerollt", "d_groesser", "c_klein"):
                    z = m[name]
                    x, y, w, h, _v = z["fenster"]
                    self.assertGreaterEqual(x, 0, name)
                    self.assertGreaterEqual(y, 0, name)
                    self.assertLessEqual(x + w, sw, name)
                    self.assertLessEqual(y + h, sh, name)
                    for caption, (bx, by, bw, bh, viewable) in z["knoepfe"].items():
                        wo = "%s %s" % (name, caption)
                        self.assertTrue(viewable, wo)
                        self.assertGreaterEqual(bh, 36, wo)
                        self.assertGreaterEqual(bx, x, wo)
                        self.assertGreaterEqual(by, y, wo)
                        self.assertLessEqual(bx + bw, x + w, wo)
                        self.assertLessEqual(by + bh, y + h, wo)
                        self.assertLessEqual(by + bh, sh, wo)
                x, y, w, h, _v = m["a_offen"]["fenster"]
                self.assertLessEqual(w, sw - 2 * ag.UPDATE_SCREEN_MARGIN_X * window + 1)
                self.assertLessEqual(h, sh - ag.UPDATE_SCREEN_MARGIN_Y * window + 1)

    # ------------------------------------------------------------------ D7
    def test_d7_schriftstufe_und_darstellung(self):
        import app_gui as ag
        for fall in FAELLE + FAELLE_125:
            with self.subTest(fall=fall):
                res, m = self._messung(fall)
                faktor = {"normal": 1.0, "sehr_gross": 1.3}[fall[1]]
                self.assertEqual(res["faktor"], faktor)
                window = m["scales"][0]
                self.assertEqual(window, fall[3])
                logisch = min(int(round(ag.UPDATE_WINDOW_BASE[0] * faktor)),
                              int(res["screen"][0] / window) - 2 * ag.UPDATE_SCREEN_MARGIN_X)
                self.assertLessEqual(abs(m["a_offen"]["fenster"][2] - logisch * window), 2)
                self.assertEqual(m["farbe_feld"].lower(), m["soll_feld"].lower())
                self.assertEqual(m["soll_feld"].lower(), m["c_card_alt"].lower())
                self.assertEqual(m["farbe_text"].lower(), m["c_text_soft"].lower())
        for screen in ((1280, 720), (1366, 768)):
            with self.subTest(screen=screen):
                normal = self._messung([f for f in FAELLE if f[0] == screen and
                                        f[1] == "normal"][0])[1]
                gross = self._messung([f for f in FAELLE if f[0] == screen and
                                       f[1] == "sehr_gross"][0])[1]
                self.assertEqual(normal["a_offen"]["fenster"][2], 560)
                self.assertEqual(gross["a_offen"]["fenster"][2], 728)
                self.assertGreater(gross["zeilenhoehe"], normal["zeilenhoehe"])
                self.assertGreater(gross["knopfschrift"], normal["knopfschrift"])
        hell = self._messung(FAELLE[0])[1]["c_card_alt"]
        dunkel = self._messung(FAELLE[1])[1]["c_card_alt"]
        self.assertNotEqual(hell.lower(), dunkel.lower())


# D4 statisch: alle Rueckfragen am PC (Datei, Funktion, Aufruf, erstes
# Argument). Stand d54397f, mit rueckfragen() aus git show erzeugt (Beleg
# bau_0.63.2/s6b/m38/logs/rueckfragen_d54397f.txt): 33 Aufrufe
# messagebox.askyesno. Erwartet ist genau dieser Stand, nur der Aufruf in
# _replace_backup mit REPLACE_TITLE geht an ask_long_question, dazu dessen
# Rueckfall ohne Hauptfenster.
RUECKFRAGEN_D54397F = [
    ("app_gui.py", "QuizView.cancel_quiz", "messagebox.askyesno", "'Session abbrechen'"),
    ("app_gui.py", "ExamPanel.start", "messagebox.askyesno", "'Prüfung starten'"),
    ("app_gui.py", "ExamPanel.cancel", "messagebox.askyesno", "'Prüfung abbrechen'"),
    ("app_gui.py", "ExamPanel._submit", "messagebox.askyesno", "'Abgeben'"),
    ("app_gui.py", "ExamPanel._finish", "messagebox.askyesno", "'Bewertung abschließen'"),
    ("app_gui.py", "FinalProjectView._delete_project", "messagebox.askyesno",
     "fpj.DELETE_TITLE"),
    ("app_gui.py", "SettingsView.reset_game", "messagebox.askyesno",
     "'Spielstand zurücksetzen'"),
    ("app_gui.py", "SettingsView.reset_records", "messagebox.askyesno", "'Bestenliste löschen'"),
    ("app_gui.py", "SettingsView._merge_backup", "messagebox.askyesno", "fsi.DELETED_TITLE"),
    ("app_gui.py", "SettingsView._replace_backup", "messagebox.askyesno", "fsi.REPLACE_TITLE"),
    ("app_gui.py", "SettingsView._replace_backup", "messagebox.askyesno",
     "fsi.REPLACE_CONFIRM_TITLE"),
    ("app_gui.py", "SettingsView.clear_history", "messagebox.askyesno", "'Historie löschen'"),
    ("app_gui.py", "SettingsView.reset_all", "messagebox.askyesno", "'Alles zurücksetzen'"),
    ("app_gui.py", "FISIApp._practice_part.ask", "messagebox.askyesno", "PRACTICE_NEXT_TITLE"),
    ("fisi_game_gui.py", "GameView._delete_slot", "messagebox.askyesno", "'Spielstand löschen'"),
    ("fisi_game_gui.py", "GameView._order_spare", "messagebox.askyesno",
     "'Ersatzteil nachbestellen'"),
    ("fisi_game_gui.py", "GameView._defer", "messagebox.askyesno", "'Ticket verschieben'"),
    ("fisi_game_gui.py", "FarmView._start", "messagebox.askyesno", "'Ausschreibung ansehen'"),
    ("fisi_game_gui.py", "HomeView._toggle_edit", "messagebox.askyesno", "'Weg versperrt'"),
    ("fisi_game_gui.py", "HomeView._sell", "messagebox.askyesno", "'Verkaufen'"),
    ("fisi_game_gui.py", "HomeView._move", "messagebox.askyesno", "'Umziehen'"),
    ("fisi_game_gui.py", "FirmView._found", "messagebox.askyesno", "'Firma gründen'"),
    ("fisi_game_gui.py", "FirmView._coach", "messagebox.askyesno", "'Coaching'"),
    ("fisi_game_gui.py", "FirmView._fire", "messagebox.askyesno", "'Entlassen'"),
    ("fisi_game_gui.py", "FirmView._open_branch", "messagebox.askyesno", "'Filiale eröffnen'"),
    ("fisi_game_gui.py", "FirmView._expand_branch", "messagebox.askyesno",
     "'Filiale ausbauen'"),
    ("fisi_game_gui.py", "FirmView._build_room", "messagebox.askyesno", "'Ausbauen'"),
    ("fisi_game_gui.py", "FirmView._expand", "messagebox.askyesno", "'Ausbauen'"),
    ("fisi_game_gui.py", "FirmView._book_ad", "messagebox.askyesno", "'Werbung buchen'"),
    ("fisi_game_gui.py", "FirmView._stop_ad", "messagebox.askyesno", "'Werbung kündigen'"),
    ("fisi_game_gui.py", "FirmView._start_cert", "messagebox.askyesno", "'Zertifizierung'"),
    ("fisi_game_gui.py", "FirmView._take_loan", "messagebox.askyesno", "'Kredit aufnehmen'"),
    ("fisi_game_gui.py", "FirmView._repay_loan", "messagebox.askyesno", "'Kredit ablösen'"),
]


def rueckfragen(path):
    """Alle Aufrufe messagebox.ask*, ask_long_question und LongQuestionDialog
    einer Datei: (Datei, Funktion, Aufruf, erstes Argument bzw. Titel)."""
    with open(os.path.join(CODE, path), encoding="utf-8") as handle:
        tree = ast.parse(handle.read())
    found = []

    def walk(node, stack):
        for child in ast.iter_child_nodes(node):
            inner = stack
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                inner = stack + [child.name]
            if isinstance(child, ast.Call):
                func, name, arg = child.func, None, None
                if (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
                        and func.value.id == "messagebox" and func.attr.startswith("ask")):
                    name = "messagebox." + func.attr
                    arg = child.args[0] if child.args else None
                elif isinstance(func, ast.Name) and func.id in ("ask_long_question",
                                                                 "LongQuestionDialog"):
                    name = func.id
                    arg = child.args[1] if len(child.args) > 1 else None
                if name:
                    found.append((path, ".".join(inner), name,
                                  ast.unparse(arg) if arg is not None else ""))
            walk(child, inner)

    walk(tree, [])
    return found


class StatischTest(unittest.TestCase):

    def test_d4_nur_diese_rueckfrage_nutzt_den_dialog(self):
        ist = rueckfragen("app_gui.py") + rueckfragen("fisi_game_gui.py")
        soll = list(RUECKFRAGEN_D54397F)
        alt = ("app_gui.py", "SettingsView._replace_backup", "messagebox.askyesno",
               "fsi.REPLACE_TITLE")
        soll[soll.index(alt)] = ("app_gui.py", "SettingsView._replace_backup",
                                 "ask_long_question", "fsi.REPLACE_TITLE")
        vor = soll.index(("app_gui.py", "FISIApp._practice_part.ask", "messagebox.askyesno",
                          "PRACTICE_NEXT_TITLE"))
        soll[vor:vor] = [("app_gui.py", "ask_long_question", "messagebox.askyesno", "title"),
                         ("app_gui.py", "ask_long_question", "LongQuestionDialog", "title")]
        self.assertEqual(ist, soll)

    def test_d4_aufruf_reicht_replace_question_durch(self):
        with open(os.path.join(CODE, "app_gui.py"), encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name) and node.func.id == "ask_long_question"]
        self.assertEqual([ast.unparse(c) for c in calls], [
            "ask_long_question(self.app, fsi.REPLACE_TITLE, fsi.replace_question(backup))"])

    def test_d1_kein_stueck_des_warntexts_als_kopie_in_dieser_datei(self):
        """Testplan 0.1/D1 Schritt 5: ausser Anfang und letztem Satz steht
        kein Stueck des Texts (30 Zeichen) in dieser Datei - sonst prueft der
        Test gegen eine Kopie statt gegen replace_question."""
        with open(os.path.abspath(__file__), encoding="utf-8") as handle:
            source = handle.read()
        text = _soll()
        erlaubt = [FIRST_WORDS, LAST_SENTENCE]
        for start in range(0, len(text) - 30):
            stueck = text[start:start + 30]
            if any(stueck in e for e in erlaubt) or STAMP in stueck:
                continue
            self.assertNotIn(stueck, source)


def eigenschaften(obj):
    """Alle gesetzten Eigenschaften eines Flet-Steuerelements (rekursiv, ohne
    Rueckrufe, interne Felder und leere Werte), fuer den Vergleich mit
    d54397f."""
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, enum.Enum):
        return "%s.%s" % (type(obj).__name__, obj.name)
    if isinstance(obj, (list, tuple)):
        return [eigenschaften(item) for item in obj]
    if dataclasses.is_dataclass(obj):
        out = {"_typ": type(obj).__name__}
        for field in dataclasses.fields(obj):
            if field.name.startswith(("_", "on_")) or field.name in ("parent", "page", "data",
                                                                     "key"):
                continue
            value = getattr(obj, field.name, None)
            if callable(value) and not dataclasses.is_dataclass(value):
                continue
            value = eigenschaften(value)
            if value is not None:
                out[field.name] = value
        return out
    return type(obj).__name__


# D9: kurze Rueckfragen am Handy. Eigenschaften auf d54397f, mit
# DIALOG_CODE=<Kopie d54397f> und eigenschaften() unter denselben
# Bedingungen wie hier erzeugt (frisches HOME, Standard-Darstellung; Beleg
# bau_0.63.2/s6b/m38/logs/kurz_d54397f.json und werkzeug/kurz_d54397f.py).
KURZ = [("Bestenliste löschen", None),
        ("Alles zurücksetzen", "Wirklich ALLE Lerndaten unwiderruflich löschen?"),
        ("Filiale ausbauen", "„Serverraum“ für 12.000 € bauen?")]
KURZ_D54397F = json.loads(r"""
[{"_typ":"AlertDialog","actions":[{"_typ":"TextButton","autofocus":false,"clip_behavior":"ClipBehavior.NONE",
"col":12,"content":"Abbrechen","disabled":false,"expand_loose":false,"opacity":1.0,
"rtl":false,"size_change_interval":10,"visible":true},{"_typ":"TextButton","autofocus":false,
"clip_behavior":"ClipBehavior.NONE","col":12,"content":"Ja","disabled":false,"expand_loose":false,
"opacity":1.0,"rtl":false,"size_change_interval":10,"visible":true}],"bgcolor":"#1B1031",
"clip_behavior":"ClipBehavior.NONE","col":12,"content":{"_typ":"Text","col":12,"color":"#A794C6",
"disabled":false,"enable_interactive_selection":true,"expand_loose":false,"italic":false,
"no_wrap":false,"opacity":1.0,"overflow":"TextOverflow.CLIP","rtl":false,"selection_cursor_width":2.0,
"show_selection_cursor":false,"size":14,"size_change_interval":10,"text_align":"TextAlign.START",
"value":"Wirklich die Bestenliste löschen? Bestwerte und Abzeichen früherer Spielstände sind danach weg. Der laufende Spielstand trägt sich gleich wieder ein.",
"visible":true},"disabled":false,"expand_loose":false,"modal":true,"opacity":1.0,
"open":false,"rtl":false,"scrollable":false,"title":{"_typ":"Text","col":12,"color":"#ECE6F8",
"disabled":false,"enable_interactive_selection":true,"expand_loose":false,"italic":false,
"no_wrap":false,"opacity":1.0,"overflow":"TextOverflow.CLIP","rtl":false,"selection_cursor_width":2.0,
"show_selection_cursor":false,"size":18,"size_change_interval":10,"text_align":"TextAlign.START",
"value":"Bestenliste löschen","visible":true,"weight":"FontWeight.BOLD"},"visible":true},
{"_typ":"AlertDialog","actions":[{"_typ":"TextButton","autofocus":false,"clip_behavior":"ClipBehavior.NONE",
"col":12,"content":"Abbrechen","disabled":false,"expand_loose":false,"opacity":1.0,
"rtl":false,"size_change_interval":10,"visible":true},{"_typ":"TextButton","autofocus":false,
"clip_behavior":"ClipBehavior.NONE","col":12,"content":"Ja","disabled":false,"expand_loose":false,
"opacity":1.0,"rtl":false,"size_change_interval":10,"visible":true}],"bgcolor":"#1B1031",
"clip_behavior":"ClipBehavior.NONE","col":12,"content":{"_typ":"Text","col":12,"color":"#A794C6",
"disabled":false,"enable_interactive_selection":true,"expand_loose":false,"italic":false,
"no_wrap":false,"opacity":1.0,"overflow":"TextOverflow.CLIP","rtl":false,"selection_cursor_width":2.0,
"show_selection_cursor":false,"size":14,"size_change_interval":10,"text_align":"TextAlign.START",
"value":"Wirklich ALLE Lerndaten unwiderruflich löschen?","visible":true},"disabled":false,
"expand_loose":false,"modal":true,"opacity":1.0,"open":false,"rtl":false,"scrollable":false,
"title":{"_typ":"Text","col":12,"color":"#ECE6F8","disabled":false,"enable_interactive_selection":true,
"expand_loose":false,"italic":false,"no_wrap":false,"opacity":1.0,"overflow":"TextOverflow.CLIP",
"rtl":false,"selection_cursor_width":2.0,"show_selection_cursor":false,"size":18,
"size_change_interval":10,"text_align":"TextAlign.START","value":"Alles zurücksetzen",
"visible":true,"weight":"FontWeight.BOLD"},"visible":true},{"_typ":"AlertDialog",
"actions":[{"_typ":"TextButton","autofocus":false,"clip_behavior":"ClipBehavior.NONE",
"col":12,"content":"Abbrechen","disabled":false,"expand_loose":false,"opacity":1.0,
"rtl":false,"size_change_interval":10,"visible":true},{"_typ":"TextButton","autofocus":false,
"clip_behavior":"ClipBehavior.NONE","col":12,"content":"Ja","disabled":false,"expand_loose":false,
"opacity":1.0,"rtl":false,"size_change_interval":10,"visible":true}],"bgcolor":"#1B1031",
"clip_behavior":"ClipBehavior.NONE","col":12,"content":{"_typ":"Text","col":12,"color":"#A794C6",
"disabled":false,"enable_interactive_selection":true,"expand_loose":false,"italic":false,
"no_wrap":false,"opacity":1.0,"overflow":"TextOverflow.CLIP","rtl":false,"selection_cursor_width":2.0,
"show_selection_cursor":false,"size":14,"size_change_interval":10,"text_align":"TextAlign.START",
"value":"„Serverraum“ für 12.000 € bauen?","visible":true},"disabled":false,"expand_loose":false,
"modal":true,"opacity":1.0,"open":false,"rtl":false,"scrollable":false,"title":{"_typ":"Text",
"col":12,"color":"#ECE6F8","disabled":false,"enable_interactive_selection":true,"expand_loose":false,
"italic":false,"no_wrap":false,"opacity":1.0,"overflow":"TextOverflow.CLIP","rtl":false,
"selection_cursor_width":2.0,"show_selection_cursor":false,"size":18,"size_change_interval":10,
"text_align":"TextAlign.START","value":"Filiale ausbauen","visible":true,"weight":"FontWeight.BOLD"},
"visible":true}]
""")


class HandyTest(unittest.TestCase):
    """Struktur des Handy-Dialogs (ohne Flet-Anzeige)."""

    def setUp(self):
        import main
        self.main = main
        self.shown = []
        self.page = types.SimpleNamespace(show_dialog=self.shown.append,
                                          pop_dialog=lambda: None, update=lambda: None)

    def _confirm(self, title, message):
        fake = types.SimpleNamespace(page=self.page)
        self.main.FISIMobileApp.confirm(fake, title, message, lambda: None)
        return self.shown[-1]

    def kurz(self):
        import fisi_game
        return [eigenschaften(self._confirm(title, message or fisi_game.RECORDS_ASK))
                for title, message in KURZ]

    def test_d8_warntext_rollbar_und_bytegenau(self):
        text = _soll()
        dialog = self._confirm(fsi.REPLACE_TITLE, text)
        self.assertEqual(len(self.shown), 1)
        self.assertTrue(dialog.scrollable, "Inhalt nicht rollbar")
        self.assertTrue(dialog.modal)
        self.assertEqual(dialog.title.value, fsi.REPLACE_TITLE)
        _bytegleich(self, dialog.content.value, text, "Handy")
        self.assertEqual([button.content for button in dialog.actions], ["Abbrechen", "Ja"])

    def _replace_backup(self):
        asked = []
        fake = types.SimpleNamespace(app=types.SimpleNamespace(
            confirm=lambda title, message, on_yes: asked.append((title, message))))
        self.main.SettingsScreen._replace_backup(fake, {})
        return asked

    def test_d8_replace_backup_reicht_text_durch(self):
        mobile_fsi = self.main.fsi
        summary, question = mobile_fsi.backup_summary, mobile_fsi.replace_question
        mobile_fsi.backup_summary = lambda b: {"erstellt": STAMP}
        try:
            normal = self._replace_backup()
            mobile_fsi.replace_question = lambda b: question(b) + MARKE
            markiert = self._replace_backup()
        finally:
            mobile_fsi.backup_summary = summary
            mobile_fsi.replace_question = question
        self.assertEqual(len(normal), 1)
        self.assertEqual(normal[0][0], fsi.REPLACE_TITLE)
        _bytegleich(self, normal[0][1], _soll(), "Handy _replace_backup")
        _bytegleich(self, markiert[0][1], _soll() + MARKE, "Handy Durchreich-Probe")
        dialog = self._confirm(*markiert[0])
        _bytegleich(self, dialog.content.value, _soll() + MARKE, "Handy Dialog")

    def test_d9_kurze_rueckfragen_nur_scrollable_anders(self):
        ist = self.kurz()
        self.assertEqual(len(KURZ_D54397F), len(KURZ))
        for alt, neu, (title, _m) in zip(KURZ_D54397F, ist, KURZ):
            with self.subTest(title=title):
                alt = dict(alt)
                self.assertIs(alt.pop("scrollable", None), False)   # d54397f: aus
                self.assertIs(neu.pop("scrollable", None), True)
                self.assertEqual(neu, alt)


def tearDownModule():
    shutil.rmtree(_TMP, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
