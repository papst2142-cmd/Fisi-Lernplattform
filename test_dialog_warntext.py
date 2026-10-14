#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer 0.63.2: Warntext vor "Alles ersetzen" ganz lesbar (Befund S1 der
dritten Gegenpruefung FG-81).

Bis d54397f zeigte der PC den Text (fsi.replace_question, zwei Absaetze) mit
messagebox.askyesno. Tk staucht diesen Dialog auf Bildschirmhoehe: der Text
war abgeschnitten (1366x768: Saetze 5-8 fehlten), es gab keinen Bildlauf,
die Knoepfe lagen 12 px unter dem Bildschirmrand, "Sehr gross" wirkte nicht.
Am Handy (FISIMobileApp.confirm) liess sich der Inhalt nicht rollen.

PC (echtes Hauptfenster FISIApp, echter Weg SettingsView._replace_backup,
je Fall ein eigener Prozess auf einer eigenen Xvfb-Anzeige in echter
Bildschirmgroesse 1280x720 bzw. 1366x768, Schrift Normal und Sehr gross,
Hell und Dunkel):
  * der ganze Text steht im Textfeld (zeichengleich mit replace_question),
  * per Mausrad laesst er sich bis zum letzten Satz rollen ("Bewahre die
    Sicherungsdatei deshalb auf." sichtbar, Bildlauf am Ende),
  * Knoepfe "Ja"/"Nein" ganz innerhalb des Bildschirms, Fenster passt hinein,
    auch auf die Mindestgroesse verkleinert bleiben die Knoepfe ganz sichtbar,
  * Breite und Schrift folgen der Schriftstufe, Farben der Darstellung,
  * Antworten wie bisher: "Ja" -> weiter zur zweiten Rueckfrage; "Nein",
    Esc und Schliessen des Fensters -> Abbruch; Eingabetaste ohne Klick ->
    Abbruch (Fokus auf dem sicheren Knopf "Nein").
Handy (Struktur, ohne Flet-Anzeige): confirm-Dialog mit scrollable=True,
Text ganz und unveraendert, Knoepfe wie bisher, Aufruf aus _replace_backup.

Start:  python test_dialog_warntext.py   (PC-Teil nur unter Linux mit Xvfb)
Anderer Code (z. B. Gegenprobe gegen d54397f):  DIALOG_CODE=<ordner> python ...
"""

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

LAST_SENTENCE = "Bewahre die Sicherungsdatei deshalb auf."
FIRST_WORDS = "Der komplette Lernstand dieses Geräts"
STAMP = "13.10.2026 21:47"

# (Bildschirm, Schrift, Darstellung): beide kleinsten Bildschirme, beide
# Schriftstufen, jede Darstellung zweimal
FAELLE = [((1280, 720), "normal", "hell"), ((1280, 720), "sehr_gross", "dunkel"),
          ((1366, 768), "normal", "dunkel"), ((1366, 768), "sehr_gross", "hell")]

CHILD = r"""
import json, os, sys, time, types
code, schrift, modus, out = sys.argv[1:5]
sys.path.insert(0, code)
os.chdir(code)
import fisi_theme
fisi_theme.save_font_size(schrift)
fisi_theme.save_mode(modus)
import fisi_hilfe
fisi_hilfe.mark_tour_seen()
from tkinter import messagebox
import tkinter.font as tkfont
gefragt = []
def _ask(title=None, message=None, **kw):
    gefragt.append([title, str(message)])
    return False
messagebox.askyesno = _ask
import customtkinter as ctk
import app_gui
app_gui.UpdateController.auto_check = lambda self: None
app_gui.SyncController.auto_start = lambda self: None
app_gui.fsi.backup_summary = lambda b: {"erstellt": %(stamp)r}
TEXT = app_gui.fsi.replace_question({})
LAST = %(last)r
app_gui.apply_appearance()
root = ctk.CTk()
app = app_gui.FISIApp(root)
root.geometry("1120x720+0+0")
res = {"screen": [root.winfo_screenwidth(), root.winfo_screenheight()],
       "faktor": fisi_theme.font_factor(), "laeufe": []}
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

def bottom(w):
    return w.winfo_rooty() + w.winfo_height()

def measure(d):
    box = d.text._textbox
    m = {"text_im_feld": box.get("1.0", "end-1c"),
         "titel": d.title(),
         "fenster": [d.winfo_rootx(), d.winfo_rooty(), d.winfo_width(), d.winfo_height()],
         "knoepfe": [[b._caption, b.winfo_rootx(), b.winfo_rooty(),
                      b.winfo_rootx() + b.winfo_width(), bottom(b), b.winfo_viewable()]
                     for b in (d.btn_yes, d.btn_no)],
         "fokus": str(d.focus_get() or ""), "nein": str(d.btn_no), "ja": str(d.btn_yes),
         "zeilenhoehe": tkfont.Font(font=box.cget("font")).metrics("linespace"),
         "farbe_feld": str(box.cget("bg")), "soll_feld": d._apply_appearance_mode(
             d.text.cget("fg_color")),
         "farbe_text": str(box.cget("fg")), "soll_text": d._apply_appearance_mode(
             d.text.cget("text_color")),
         "c_card_alt": fisi_theme.C["card_alt"], "c_text_soft": fisi_theme.C["text_soft"]}
    last = box.search(LAST, "1.0", "end")
    m["letzter_satz_gefunden"] = bool(last)
    m["yview_oben"] = list(box.yview())
    m["letzter_oben_sichtbar"] = bool(last) and box.bbox(last + " lineend -1c") is not None
    for step in range(200):
        before = box.yview()
        box.event_generate("<Button-5>", x=10, y=10)
        settle(2)
        if box.yview() == before:
            break
    m["schritte"] = step
    m["yview_unten"] = list(box.yview())
    m["letzter_unten_sichtbar"] = bool(last) and box.bbox(last + " lineend -1c") is not None
    # kleinstes erlaubtes Fenster (wm minsize): Knoepfe weiter ganz im Fenster
    width, height = d.wm_minsize()
    d.wm_geometry("%%dx%%d" %% (width, height))
    settle(10)
    m["mindestgroesse"] = [width, height, d.winfo_width(), d.winfo_height()]
    m["mindest_fenster_unten"] = bottom(d)
    m["mindest_knoepfe"] = [[b._caption, bottom(b), b.winfo_viewable(), b.winfo_height()]
                            for b in (d.btn_yes, d.btn_no)]
    return m

def one(art, laeufe):
    # "keiner": bis d54397f geht die Frage an messagebox.askyesno (hier
    # mitgeschrieben), es erscheint kein rollbarer Dialog
    lauf = {"art": art, "dialog": "keiner"}
    def act():
        settle()
        found = dialogs()
        lauf["dialog"] = "LongQuestionDialog" if found else (
            "tk_messagebox" if tk_box() else "keiner")
        if not found:
            if tk_box():
                w = ".__tk__messagebox"
                lauf["tk_knopf_unterkante"] = max(
                    int(root.tk.call("winfo", "rooty", w + "." + n))
                    + int(root.tk.call("winfo", "height", w + "." + n)) for n in ("yes", "no"))
                root.tk.call(w + ".no", "invoke")
            return
        d = found[0]
        if art == "messen":
            lauf.update(measure(d))
            d.btn_no._on_click()
        elif art == "ja":
            d.btn_yes._on_click()
        elif art == "nein":
            d.btn_no._on_click()
        elif art == "esc":
            d.event_generate("<Escape>")
        elif art == "eingabe":
            w = d.focus_get()
            lauf["fokus"] = str(w or "")
            lauf["nein"] = str(d.btn_no)
            if w is not None:
                w.event_generate("<Return>")
            else:
                d.btn_no.event_generate("<Return>")
        elif art == "schliessen":
            root.tk.call(d.protocol("WM_DELETE_WINDOW"))
        settle(2)
        lauf["offen_danach"] = bool(dialogs())
    del gefragt[:]
    root.after(1500, act)
    notbremse = root.after(30000, lambda: [w.destroy() for w in dialogs()])
    app_gui.SettingsView._replace_backup(fake, {})
    root.after_cancel(notbremse)
    lauf["zweite_rueckfrage"] = [g[0] for g in gefragt]
    laeufe.append(lauf)

def run():
    try:
        for art in ("messen", "ja", "nein", "esc", "eingabe", "schliessen"):
            one(art, res["laeufe"])
    except Exception as error:
        import traceback
        res["fehler"] = traceback.format_exc()
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


def _run_child(size, schrift, modus):
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
        done = subprocess.run([sys.executable, script, CODE, schrift, modus, out], env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=240)
    finally:
        proc.terminate()
        proc.wait()
    if not os.path.exists(out):
        raise AssertionError("Kindprozess ohne Ergebnis:\n" + done.stdout.decode(
            "utf-8", "replace")[-3000:])
    with open(out, encoding="utf-8") as handle:
        return json.load(handle)


@unittest.skipUnless(_xvfb(), "nur unter Linux mit Xvfb (eigene Anzeige je Bildschirmgroesse)")
class PCDialogTest(unittest.TestCase):
    ERGEBNISSE = {}

    @classmethod
    def ergebnis(cls, fall):
        if fall not in cls.ERGEBNISSE:
            cls.ERGEBNISSE[fall] = _run_child(*fall)
        return cls.ERGEBNISSE[fall]

    def _messung(self, fall):
        res = self.ergebnis(fall)
        self.assertNotIn("fehler", res, res.get("fehler"))
        self.assertEqual(res["screen"], list(fall[0]), "Anzeige nicht in der Sollgroesse")
        lauf = res["laeufe"][0]
        self.assertEqual(lauf["art"], "messen")
        self.assertEqual(lauf["dialog"], "LongQuestionDialog",
                         "kein rollbarer Dialog (%s)" % lauf)
        return res, lauf

    def test_ganzer_text_rollbar_bis_zum_letzten_satz(self):
        for fall in FAELLE:
            with self.subTest(fall=fall):
                _res, m = self._messung(fall)
                self.assertTrue(m["text_im_feld"].startswith(FIRST_WORDS))
                self.assertTrue(m["text_im_feld"].endswith(LAST_SENTENCE))
                self.assertIn(STAMP, m["text_im_feld"])
                self.assertEqual(m["titel"], fsi.REPLACE_TITLE)
                self.assertTrue(m["letzter_satz_gefunden"])
                # zu Beginn oben, am Ende per Mausrad bis ganz unten
                self.assertEqual(m["yview_oben"][0], 0.0)
                self.assertEqual(m["yview_unten"][1], 1.0)
                self.assertTrue(m["letzter_unten_sichtbar"], m)

    def test_text_zeichengleich_mit_replace_question(self):
        import importlib
        sicherung = importlib.import_module("fisi_sicherung")
        original = sicherung.backup_summary
        sicherung.backup_summary = lambda b: {"erstellt": STAMP}
        try:
            soll = sicherung.replace_question({})
        finally:
            sicherung.backup_summary = original
        self.assertEqual(soll.count("\n\n"), 1)
        for fall in FAELLE:
            with self.subTest(fall=fall):
                _res, m = self._messung(fall)
                self.assertEqual(m["text_im_feld"], soll)

    def test_knoepfe_und_fenster_im_bildschirm(self):
        for fall in FAELLE:
            with self.subTest(fall=fall):
                res, m = self._messung(fall)
                width, height = res["screen"]
                x, y, w, h = m["fenster"]
                self.assertGreaterEqual(x, 0)
                self.assertGreaterEqual(y, 0)
                self.assertLessEqual(x + w, width)
                self.assertLessEqual(y + h, height)
                self.assertEqual([k[0] for k in m["knoepfe"]], ["Ja", "Nein"])
                for caption, left, top, right, low, viewable in m["knoepfe"]:
                    self.assertTrue(viewable, caption)
                    self.assertGreaterEqual(top, y, caption)
                    self.assertGreaterEqual(left, 0, caption)
                    self.assertLessEqual(right, width, caption)
                    self.assertLessEqual(low, height, "%s unter dem Bildschirmrand" % caption)
                    self.assertLessEqual(low, y + h, caption)

    def test_kleinstes_fenster_knoepfe_ganz_sichtbar(self):
        """Auch auf die Mindestgroesse verkleinert schrumpft nur das Textfeld."""
        for fall in FAELLE:
            with self.subTest(fall=fall):
                _res, m = self._messung(fall)
                for caption, low, viewable, height in m["mindest_knoepfe"]:
                    self.assertTrue(viewable, caption)
                    self.assertGreaterEqual(height, 36, caption)
                    self.assertLessEqual(low, m["mindest_fenster_unten"], (caption, m))

    def test_schriftstufe_und_darstellung(self):
        for screen in ((1280, 720), (1366, 768)):
            with self.subTest(screen=screen):
                fall_n = [f for f in FAELLE if f[0] == screen and f[1] == "normal"][0]
                fall_s = [f for f in FAELLE if f[0] == screen and f[1] == "sehr_gross"][0]
                res_n, normal = self._messung(fall_n)
                res_s, gross = self._messung(fall_s)
                self.assertEqual(res_n["faktor"], 1.0)
                self.assertEqual(res_s["faktor"], 1.3)
                self.assertEqual(normal["fenster"][2], 560)
                self.assertEqual(gross["fenster"][2], 728)
                self.assertGreater(gross["zeilenhoehe"], normal["zeilenhoehe"])
                # beim kleinen Bildschirm muss bei Sehr gross gerollt werden
                self.assertLess(gross["yview_oben"][1], 1.0)
                self.assertFalse(gross["letzter_oben_sichtbar"])
        for fall in FAELLE:
            with self.subTest(fall=fall):
                _res, m = self._messung(fall)
                self.assertEqual(m["farbe_feld"].lower(), m["soll_feld"].lower())
                self.assertEqual(m["soll_feld"].lower(), m["c_card_alt"].lower())
                self.assertEqual(m["farbe_text"].lower(), m["c_text_soft"].lower())
        hell = self._messung(FAELLE[0])[1]["c_card_alt"]
        dunkel = self._messung(FAELLE[1])[1]["c_card_alt"]
        self.assertNotEqual(hell.lower(), dunkel.lower())

    def test_antworten_wie_bisher(self):
        """Ja -> zweite Rueckfrage (REPLACE_CONFIRM); alles andere bricht ab.
        Die Eingabetaste ohne Klick trifft den sicheren Knopf "Nein"."""
        for fall in FAELLE:
            with self.subTest(fall=fall):
                res, _m = self._messung(fall)
                laeufe = {lauf["art"]: lauf for lauf in res["laeufe"]}
                self.assertEqual(sorted(laeufe), sorted(
                    ["messen", "ja", "nein", "esc", "eingabe", "schliessen"]))
                for art, lauf in laeufe.items():
                    self.assertEqual(lauf["dialog"], "LongQuestionDialog", art)
                    self.assertFalse(lauf["offen_danach"], art)
                    soll = [fsi.REPLACE_CONFIRM_TITLE] if art == "ja" else []
                    self.assertEqual(lauf["zweite_rueckfrage"], soll, art)
                self.assertEqual(laeufe["eingabe"]["fokus"], laeufe["eingabe"]["nein"])
                self.assertEqual(laeufe["messen"]["fokus"], laeufe["messen"]["nein"])


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
        self.assertEqual(len(self.shown), 1)
        return self.shown[0]

    def test_warntext_rollbar_und_ganz(self):
        original = fsi.backup_summary
        fsi.backup_summary = lambda b: {"erstellt": STAMP}
        try:
            text = fsi.replace_question({})
        finally:
            fsi.backup_summary = original
        dialog = self._confirm(fsi.REPLACE_TITLE, text)
        self.assertTrue(dialog.scrollable, "Inhalt nicht rollbar")
        self.assertTrue(dialog.modal)
        self.assertEqual(dialog.title.value, fsi.REPLACE_TITLE)
        self.assertEqual(dialog.content.value, text)
        self.assertTrue(dialog.content.value.endswith(LAST_SENTENCE))
        self.assertEqual([button.content for button in dialog.actions], ["Abbrechen", "Ja"])

    def test_replace_backup_nutzt_confirm(self):
        asked = []
        fake = types.SimpleNamespace(app=types.SimpleNamespace(
            confirm=lambda title, message, on_yes: asked.append((title, message))))
        original = fsi.backup_summary
        fsi.backup_summary = lambda b: {"erstellt": STAMP}
        try:
            self.main.SettingsScreen._replace_backup(fake, {})
            text = fsi.replace_question({})
        finally:
            fsi.backup_summary = original
        self.assertEqual(asked, [(fsi.REPLACE_TITLE, text)])


def tearDownModule():
    shutil.rmtree(_TMP, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
