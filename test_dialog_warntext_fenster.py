#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer 0.63.2 (FG-102): Warntext-Dialog vor "Alles ersetzen" prozess-
intern - auch unter Windows (Windows-Liste in pruefung/ci_tests.sh) und
macOS (Schritt "Dialogtest Warntext (macOS)" am Ende des Bau-Jobs).

test_dialog_warntext.py prueft den Dialog nur unter Linux (je Fall ein
Kindprozess auf eigener Xvfb-Anzeige). Diese Datei laeuft im Testprozess:
ein ctk.CTk(), keine Kindprozesse, kein Xvfb, kein flet, kein ctypes. Sie
ueberspringt NIE etwas - ohne Anzeige ist sie rot (statische Pruefung
unten, Kontrollfehler KF-D10a).

Bildschirm nachgestellt wie test_update_fenster.py: winfo_screenwidth/
-height an der Klasse LongQuestionDialog ersetzt, nach dem Fall zurueck.
Ist der echte Bildschirm kleiner, gilt der echte (kleinere) Wert (FG-102,
T2); beide Werte stehen in der Ausgabe.

Echter Weg SettingsView._replace_backup(fake, backup) mit fake.app.root =
Hauptfenster; Sollwert fsi.replace_question im selben Prozess, keine
Textkopie (nur Anfang und letzter Satz), Durchreich-Probe mit Marke.
  D1 Text byte-genau, Durchreich-Probe,
  D2 Titel, Kartenueberschrift, Knoepfe, zweite Rueckfrage,
  D3 Standard "Nein": Eingabetaste, Escape (auch im Textfeld), Schliessen
     (BEHELF: Protokoll-Befehl WM_DELETE_WINDOW, kein echter Schliessknopf),
     Klick/Tab+Eingabe auf "Ja" -> zweite Rueckfrage, Sperre und danach frei,
  D5 Text ganz erreichbar (Mausrad plattformgerecht, Strg+Ende), letzte
     Zeile ganz sichtbar, nicht seitlich abgeschnitten,
  D6 Knoepfe ganz sichtbar: offen, gerollt, groesser gezogen, kleinstes
     Fenster; Fenster nie groesser als Bildschirm minus Raender,
  D7 Breite und Schriften folgen der Schriftstufe, Farben der Darstellung.
Nicht abdeckbar: echte Bildschirmaufloesung, echter Schliessknopf/Alt+F4,
Aussehen (Testliste fuer Nico).

Fokus: unter Linux focus_get(); sonst focus_lastfor() (der Testprozess ist
unter macOS/Windows nicht unbedingt die aktive Anwendung), Ereignisse an
dieses Element. Notbremse: faulthandler (240 s, rot mit Stapelausgabe), je
Dialog zusaetzlich Schliessen nach 30 s.

Letzte Ausgabezeile: "Dialog prozessintern: <n> Faelle, Plattform <...>,
Bildschirm echt <w>x<h>".

Start:  python test_dialog_warntext_fenster.py
"""

import ast
import faulthandler
import os
import sys
import tempfile
import time
import types
import unittest

# Notbremse (FG-102, 5.3 Nr. 6): ein Haenger wird rot mit Stapelausgabe
NOTBREMSE_S = 240
faulthandler.dump_traceback_later(NOTBREMSE_S, exit=True)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_TMP = tempfile.mkdtemp(prefix="fisi_dialog_fenster_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "start.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(_TMP, "selbsttest.log"))
os.environ["HOME"] = _TMP
os.environ["APPDATA"] = _TMP
os.environ["FISI_VORLADEN"] = "0"

import fisi_sicherung as fsi  # noqa: E402

LAST_SENTENCE = "Bewahre die Sicherungsdatei deshalb auf."
FIRST_WORDS = "Der komplette Lernstand dieses Geräts"
STAMP = "13.10.2026 21:47"
MARKE = "\n\n[PRUEFMARKE 7f3a]"

# (Bildschirm, Schrift, Darstellung, Bildschirmfaktor) - wie test_dialog_warntext.py
FAELLE = [((1280, 720), "normal", "hell", 1.0), ((1280, 720), "sehr_gross", "dunkel", 1.0),
          ((1366, 768), "normal", "dunkel", 1.0), ((1366, 768), "sehr_gross", "hell", 1.0)]
FAELLE_125 = [((1366, 768), "normal", "hell", 1.25), ((1280, 720), "sehr_gross", "dunkel", 1.25)]
ARTEN = ["messen", "tastatur", "klick_ja", "klick_nein", "tab_ja_eingabe", "eingabe",
         "eingabe_textfeld", "esc", "esc_textfeld", "schliessen_protokoll"]
ARTEN_125 = ["messen", "tastatur"]
ABBRUCH = ["klick_nein", "eingabe", "eingabe_textfeld", "esc", "esc_textfeld",
           "schliessen_protokoll"]
WEITER = ["klick_ja", "tab_ja_eingabe"]

LINUX = sys.platform.startswith("linux")
STEP_NAME = "Dialogtest Warntext (macOS)"
STEP_IF = "if: runner.os == 'macOS' && vars.TESTS_UEBERSPRINGEN != 'ja'"
STEP_RUN = "run: python test_dialog_warntext_fenster.py"

# Zaehler fuer die Schlusszeile
GELAUFEN = set()
ECHT = []


def _soll():
    original = fsi.backup_summary
    fsi.backup_summary = lambda b: {"erstellt": STAMP}
    try:
        return fsi.replace_question({})
    finally:
        fsi.backup_summary = original


def _bytegleich(test, ist, soll, wo):
    test.assertEqual(len(ist), len(soll), wo)
    test.assertEqual(ist.encode("utf-8"), soll.encode("utf-8"), wo)


class Umgebung:
    """Ein Hauptfenster fuer alle Faelle (prozessintern)."""
    root = None

    @classmethod
    def hauptfenster(cls):
        if cls.root is None:
            import customtkinter as ctk
            import app_gui
            app_gui.UpdateController.auto_check = lambda self: None
            app_gui.SyncController.auto_start = lambda self: None
            cls.root = ctk.CTk()
            cls.root.geometry("300x200+0+0")
            ECHT[:] = [cls.root.winfo_screenwidth(), cls.root.winfo_screenheight()]
        return cls.root


def _fokus(d):
    """Element mit dem Fokus im Dialog (R1: ausserhalb Linux focus_lastfor)."""
    if LINUX:
        return d.focus_get()
    return d.focus_lastfor()


def _lauf_fall(fall, arten, marke=""):
    """Oeffnet den Dialog je Art ueber den echten Weg und misst."""
    import customtkinter as ctk
    import tkinter as tk
    import tkinter.font as tkfont
    from tkinter import messagebox
    import fisi_theme
    import fisi_widgets
    import app_gui

    screen_soll, schrift, modus, skal = fall
    root = Umgebung.hauptfenster()
    echt = (root.winfo_screenwidth(), root.winfo_screenheight())
    # FG-102 T2: kleinerer echter Bildschirm gilt (strenger), beide in die Ausgabe
    screen = (min(screen_soll[0], echt[0]), min(screen_soll[1], echt[1]))
    res = {"screen_soll": list(screen_soll), "screen": list(screen), "echt": list(echt),
           "skal": skal, "laeufe": []}

    vorher_modus = fisi_theme.current_mode
    fisi_theme.apply_mode(modus)
    app_gui.apply_appearance()
    fisi_theme.apply_font_size(schrift)
    fisi_widgets.apply_ui_scale(fisi_theme.font_factor())
    fisi_widgets.setup_fonts(root)
    res["faktor"] = fisi_theme.font_factor()

    gefragt = []
    saved_mb = (messagebox.askyesno, messagebox.showinfo, messagebox.showerror)

    def _ask(title=None, message=None, **kw):
        gefragt.append({"title": title, "message": str(message),
                        "kw": dict((k, str(v)) for k, v in sorted(kw.items()))})
        return False
    messagebox.askyesno = _ask
    messagebox.showinfo = lambda *a, **k: None
    messagebox.showerror = lambda *a, **k: None
    saved_summary = app_gui.fsi.backup_summary
    app_gui.fsi.backup_summary = lambda b: {"erstellt": STAMP}
    saved_question = app_gui.fsi.replace_question
    res["original"] = saved_question({})
    if marke:
        app_gui.fsi.replace_question = lambda b: saved_question(b) + marke
    res["soll"] = app_gui.fsi.replace_question({})
    cls = app_gui.LongQuestionDialog
    saved_screen = (cls.winfo_screenwidth, cls.winfo_screenheight)
    cls.winfo_screenwidth = lambda _self: screen[0]
    cls.winfo_screenheight = lambda _self: screen[1]
    saved_dpi = ctk.ScalingTracker.get_window_dpi_scaling
    if skal != 1.0:
        # wie Windows bei 125 %: CTk liest dort diesen Faktor vom Bildschirm
        ctk.ScalingTracker.get_window_dpi_scaling = classmethod(lambda c, window: skal)
    fake = types.SimpleNamespace(app=types.SimpleNamespace(root=root), db=None)

    def settle(n=8):
        for _ in range(n):
            root.update()
            time.sleep(0.03)

    def dialogs():
        return [w for w in root.winfo_children() if isinstance(w, cls)]

    def rect(w):
        return [w.winfo_rootx(), w.winfo_rooty(), w.winfo_width(), w.winfo_height(),
                int(w.winfo_viewable())]

    def zustand(d):
        return {"fenster": rect(d), "knoepfe": {"Ja": rect(d.btn_yes), "Nein": rect(d.btn_no)},
                "yview": list(d.text._textbox.yview()), "xview": list(d.text._textbox.xview())}

    def zeile_ganz(d, index):
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
        start = box.search(LAST_SENTENCE, "1.0", "end")
        if not start:
            return {"gefunden": False, "ganz": False}
        a, e = zeile_ganz(d, start), zeile_ganz(d, "end-1c")
        return {"gefunden": True, "ganz": a["ganz"] and e["ganz"], "anfang": a, "ende": e}

    def maus_bis_ende(d):
        # 5.3 Nr. 5: Linux <Button-5>, sonst <MouseWheel> mit delta=-120
        box = d.text._textbox
        for step in range(300):
            before = box.yview()
            if LINUX:
                box.event_generate("<Button-5>", x=10, y=10)
            else:
                box.event_generate("<MouseWheel>", delta=-120, x=10, y=10)
            settle(2)
            if box.yview() == before:
                return step
        return -1

    def tab_bis(d, ziel, n=8):
        weg = []
        for _ in range(n):
            w = _fokus(d)
            weg.append(str(w or ""))
            if w is not None and str(w) == str(ziel):
                return weg, True
            (w or d).event_generate("<Tab>")
            settle(2)
        w = _fokus(d)
        weg.append(str(w or ""))
        return weg, w is not None and str(w) == str(ziel)

    def klick(knopf):
        inner = knopf._label
        inner.event_generate("<Enter>", x=5, y=5)
        inner.event_generate("<Button-1>", x=5, y=5)
        try:
            inner.event_generate("<ButtonRelease-1>", x=5, y=5)
        except tk.TclError:
            pass

    def messen(d, lauf):
        box = d.text._textbox
        lauf["text_im_feld"] = box.get("1.0", "end-1c")
        lauf["titel"] = d.title()
        lauf["karte"] = d.card.title_label.cget("text") if d.card.title_label else None
        lauf["beschriftung"] = [d.btn_yes._caption, d.btn_no._caption]
        lauf["protokoll"] = str(d.protocol("WM_DELETE_WINDOW"))
        lauf["zeilenhoehe"] = tkfont.Font(font=box.cget("font")).metrics("linespace")
        lauf["knopfschrift"] = tkfont.Font(font=d.btn_no._label.cget("font")).metrics(
            "linespace")
        lauf["scales"] = list(d._scales())
        lauf["bildschirm_im_dialog"] = [d.winfo_screenwidth(), d.winfo_screenheight()]
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
        sw, sh = screen
        d.wm_geometry("%dx%d" % (min(w0 + 60, sw - x0), min(h0 + 40, sh - y0)))
        settle(10)
        lauf["d_groesser"] = zustand(d)
        width, height = d.wm_minsize()
        d.wm_geometry("%dx%d" % (width, height))
        settle(10)
        lauf["mindestgroesse"] = [width, height]
        lauf["c_klein"] = zustand(d)

    def one(art):
        lauf = {"art": art, "dialog": "keiner"}

        def act():
            try:
                act_inner()
            except Exception:  # noqa: BLE001 - Fehler in den Bericht, Dialog zu
                import traceback
                lauf["fehler"] = traceback.format_exc()
                for w in dialogs():
                    w.destroy()

        def act_inner():
            settle()
            found = dialogs()
            lauf["dialog"] = type(found[0]).__name__ if found else "keiner"
            if not found:
                return
            d = found[0]
            lauf["fokus"] = str(_fokus(d) or "")
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
                    d.text._textbox.focus_set()
                    settle(2)
                (_fokus(d) or d.text._textbox).event_generate("<Control-End>")
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
                (_fokus(d) or d).event_generate("<Return>")
            elif art == "eingabe":
                (_fokus(d) or d).event_generate("<Return>")
            elif art == "esc":
                (_fokus(d) or d).event_generate("<Escape>")
            elif art == "eingabe_textfeld":
                lauf["tab_weg"], lauf["tab_erreicht"] = tab_bis(d, d.text._textbox)
                (_fokus(d) or d).event_generate("<Return>")
                settle(4)
                if dialogs():
                    klick(d.btn_no)
            elif art == "esc_textfeld":
                lauf["tab_weg"], lauf["tab_erreicht"] = tab_bis(d, d.text._textbox)
                if not lauf["tab_erreicht"]:
                    d.text._textbox.focus_set()
                    settle(2)
                lauf["fokus_vor_esc"] = str(_fokus(d) or "")
                (_fokus(d) or d).event_generate("<Escape>")
            elif art == "schliessen_protokoll":
                root.tk.call(d.protocol("WM_DELETE_WINDOW"))      # BEHELF
            settle(4)
            lauf["offen_danach"] = bool(dialogs())
            lauf["grab_danach"] = str(root.grab_current() or "")

        del gefragt[:]
        timer = root.after(700, act)
        notbremse = root.after(30000, lambda: [w.destroy() for w in dialogs()])
        try:
            app_gui.SettingsView._replace_backup(fake, {})
        finally:
            root.after_cancel(notbremse)
            try:
                root.after_cancel(timer)
            except Exception:  # noqa: BLE001
                pass
        lauf["zweite_rueckfrage"] = list(gefragt)
        res["laeufe"].append(lauf)

    try:
        settle(4)
        for art in arten:
            one(art)
    finally:
        cls.winfo_screenwidth, cls.winfo_screenheight = saved_screen
        ctk.ScalingTracker.get_window_dpi_scaling = saved_dpi
        messagebox.askyesno, messagebox.showinfo, messagebox.showerror = saved_mb
        app_gui.fsi.backup_summary = saved_summary
        app_gui.fsi.replace_question = saved_question
        for w in dialogs():
            w.destroy()
        # Schrift und Darstellung zurueck (Regel Weisung 45)
        fisi_theme.apply_font_size("normal")
        fisi_widgets.apply_ui_scale(1.0)
        fisi_theme.apply_mode(vorher_modus)
        app_gui.apply_appearance()
        settle(4)
    GELAUFEN.add((fall, marke))
    return res


class DialogFensterTest(unittest.TestCase):
    """Der echte Dialog im Testprozess - unter Linux, Windows und macOS."""
    ERGEBNISSE = {}

    def setUp(self):
        # Notbremse je Test neu (die Datei hat mehrere Tests; ein Haenger in
        # einem Test wird nach NOTBREMSE_S rot mit Stapelausgabe)
        faulthandler.dump_traceback_later(NOTBREMSE_S, exit=True)

    @classmethod
    def ergebnis(cls, fall, arten=None, marke=""):
        key = (fall, marke)
        if key not in cls.ERGEBNISSE:
            if arten is None:
                arten = ARTEN_125 if fall[3] != 1.0 else ARTEN
            cls.ERGEBNISSE[key] = _lauf_fall(fall, arten, marke)
        return cls.ERGEBNISSE[key]

    def _laeufe(self, fall):
        res = self.ergebnis(fall)
        laeufe = {lauf["art"]: lauf for lauf in res["laeufe"]}
        for art, lauf in laeufe.items():
            self.assertNotIn("fehler", lauf, "%s: %s" % (art, lauf.get("fehler")))
            self.assertEqual(lauf["dialog"], "LongQuestionDialog",
                             "kein rollbarer Dialog (%s: %s)" % (art, lauf))
        return res, laeufe

    def _messung(self, fall):
        res, laeufe = self._laeufe(fall)
        return res, laeufe["messen"]

    # -------------------------------------------------------- Bildschirm
    def test_bildschirm_ersatz_wirkt(self):
        """Der Dialog sieht genau den nachgestellten (bzw. kleineren echten)
        Bildschirm (Kontrollfehler KF-102e: Ersatz an der falschen Klasse)."""
        for fall in FAELLE + FAELLE_125:
            with self.subTest(fall=fall):
                res, m = self._messung(fall)
                self.assertEqual(m["bildschirm_im_dialog"], res["screen"])
                if res["screen"] != res["screen_soll"]:
                    print("Hinweis: echter Bildschirm %s kleiner als nachgestellt %s - "
                          "der echte gilt" % (res["echt"], res["screen_soll"]))

    # ---------------------------------------------------------------- D1
    def test_d1_text_bytegenau_wie_replace_question(self):
        soll = _soll()
        self.assertEqual(soll.count("\n\n"), 1)
        self.assertTrue(soll.startswith(FIRST_WORDS))
        self.assertTrue(soll.endswith(LAST_SENTENCE))
        for fall in FAELLE + FAELLE_125:
            with self.subTest(fall=fall):
                res, m = self._messung(fall)
                _bytegleich(self, res["soll"], soll, "Sollwert")
                _bytegleich(self, m["text_im_feld"], soll, "angezeigt")
                self.assertIn(STAMP, m["text_im_feld"])

    def test_d1_durchreich_probe_marke_kommt_an(self):
        res = self.ergebnis(FAELLE[2], arten=["messen"], marke=MARKE)
        m = res["laeufe"][0]
        self.assertNotIn("fehler", m, m.get("fehler"))
        self.assertEqual(m["dialog"], "LongQuestionDialog")
        _bytegleich(self, res["original"], _soll(), "Original")
        _bytegleich(self, m["text_im_feld"], res["original"] + MARKE, "Durchreich-Probe")

    # ---------------------------------------------------------------- D2
    def test_d2_titel_knoepfe_zweite_rueckfrage(self):
        for fall in FAELLE:
            with self.subTest(fall=fall):
                _res, laeufe = self._laeufe(fall)
                m = laeufe["messen"]
                self.assertEqual(m["titel"], fsi.REPLACE_TITLE)
                self.assertEqual(m["karte"], fsi.REPLACE_TITLE.upper())
                self.assertEqual(m["beschriftung"], ["Ja", "Nein"])
                ja, nein = m["a_offen"]["knoepfe"]["Ja"], m["a_offen"]["knoepfe"]["Nein"]
                self.assertLess(ja[0], nein[0], "Reihenfolge Ja, Nein")
                for art in WEITER:
                    self.assertEqual(laeufe[art]["zweite_rueckfrage"], [{
                        "title": fsi.REPLACE_CONFIRM_TITLE, "message": fsi.REPLACE_CONFIRM,
                        "kw": {"default": "no", "icon": "warning"}}], art)

    # ---------------------------------------------------------------- D3
    def test_d3_standard_nein_eingabe_escape_schliessen(self):
        for fall in FAELLE:
            with self.subTest(fall=fall):
                _res, laeufe = self._laeufe(fall)
                self.assertEqual(sorted(laeufe), sorted(ARTEN))
                for art, lauf in laeufe.items():
                    self.assertEqual(lauf["fokus"], lauf["nein"], "Fokus beim Oeffnen (%s)" % art)
                    self.assertFalse(lauf["offen_danach"], art)
                    self.assertEqual(lauf["grab_danach"], "", art)
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
                self.assertTrue(laeufe["eingabe_textfeld"]["tab_erreicht"])
                self.assertEqual(laeufe["esc_textfeld"]["fokus_vor_esc"],
                                 laeufe["esc_textfeld"]["textfeld"])
                self.assertTrue(laeufe["messen"]["protokoll"])

    # ---------------------------------------------------------------- D5
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
                    self.assertLess(m["a_offen"]["yview"][1], 1.0)
                    self.assertFalse(m["a_letzter"]["ganz"])

    # ---------------------------------------------------------------- D6
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
                x, y, w, h, _v = m["a_offen"]["fenster"]
                self.assertLessEqual(w, sw - 2 * ag.UPDATE_SCREEN_MARGIN_X * window + 1)
                self.assertLessEqual(h, sh - ag.UPDATE_SCREEN_MARGIN_Y * window + 1)

    # ---------------------------------------------------------------- D7
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


class StatischTest(unittest.TestCase):
    """5.3 Nr. 2 und 7: nichts wird uebersprungen; die Datei steht in der
    Windows-Liste, der macOS-Schritt steht genau so im Workflow."""

    def test_kein_ueberspringen_in_dieser_datei(self):
        # Woerter zusammengesetzt, damit diese Pruefung sich nicht selbst findet
        verboten = {"sk" + "ip", "sk" + "ipIf", "sk" + "ipUnless", "Sk" + "ipTest",
                    "sk" + "ipTest", "expected" + "Failure"}
        with open(os.path.abspath(__file__), encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        funde = []
        for node in ast.walk(tree):
            name = None
            if isinstance(node, ast.Attribute):
                name = node.attr
            elif isinstance(node, ast.Name):
                name = node.id
            if name in verboten:
                funde.append((name, getattr(node, "lineno", 0)))
        self.assertEqual(funde, [])

    def test_windows_liste_enthaelt_datei(self):
        with open(os.path.join(HERE, "pruefung", "ci_tests.sh"), encoding="utf-8") as handle:
            text = handle.read()
        start = text.index("  windows) DATEIEN=\"")
        liste = text[start:text.index('" ;;', start)]
        self.assertIn("test_dialog_warntext_fenster.py", liste.split())

    def test_macos_schritt_im_bau_job(self):
        with open(os.path.join(HERE, ".github", "workflows", "build.yml"),
                  encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        index = [i for i, line in enumerate(lines)
                 if line.strip() == "- name: " + STEP_NAME]
        self.assertEqual(len(index), 1, "Schritt fehlt oder doppelt")
        block = []
        for line in lines[index[0] + 1:]:
            if line.strip().startswith("- ") or not line.startswith("        "):
                break
            block.append(line.strip())
        self.assertEqual(block, [STEP_IF, "timeout-minutes: 5", STEP_RUN])
        # im Job "build", nach dem Hochladen, vor dem Job "android"
        jobs = [i for i, line in enumerate(lines) if line.startswith("  ") and
                not line.startswith("   ") and line.rstrip().endswith(":")]
        vorher = [i for i in jobs if i < index[0]]
        self.assertEqual(lines[vorher[-1]].strip(), "build:")
        upload = [i for i in range(vorher[-1], index[0])
                  if "actions/upload-artifact" in lines[i]]
        self.assertTrue(upload, "Schritt steht nicht nach dem Hochladen")


if __name__ == "__main__":
    programm = unittest.main(verbosity=2, exit=False)
    faulthandler.cancel_dump_traceback_later()
    echt = ECHT or ["?", "?"]
    print("Dialog prozessintern: %d Faelle, Plattform %s, Bildschirm echt %sx%s"
          % (len(GELAUFEN), sys.platform, echt[0], echt[1]), flush=True)
    sys.exit(0 if programm.result.wasSuccessful() else 1)
