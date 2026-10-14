#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests 0.63.2 N8 (B-D-08): Rahmen des Suchfelds in der Kopfzeile bei jeder
Schriftgroesse geschlossen.

Plan-Nachtrag 0.63.2 Nr. 21, Testplan N8 Abschnitt 3 (K10, K11, K12,
A-N8-10, A-N8-11, A-N8-13, A-N8-14). Normal/Gross/Sehr gross (je ein Prozess),
Fenster 1120 x 720, 1360 x 900, 1920 x 1080, hell und dunkel, ohne und mit
Fokus, Standardschrift und abgelehnte Standardschrift:

  K10 Geometrie: das innere Eingabefeld liegt ganz in der abgerundeten Form
      des Rahmens - oben/unten Abstand >= Rahmenbreite (echte Pixel), keine
      Ecke des Feld-Rechtecks ausserhalb des Innenbogens.
  K11 Pixel (Xvfb-Bildschirmfoto): auf der oberen und unteren Kante zwischen
      den Boegen hat jede Pixelspalte in den Zeilen [Kante-1, Kante+1] ein
      Pixel nahe der Rahmenfarbe (RGB-Abstand <= 40; C["field_border"], mit
      Fokus C["purple"]); links/rechts je drei Punkte auf dem Bogen.
      Banner-Ecke des Dashboards (A-N8-13, Testplan Frage 5): gemessen und
      ausgegeben, geaendert wird dort nur, wenn der Test eine Luecke zeigt.
  K12 Breite des Suchfelds, Platzhalter, Strg+F und Eingabetaste -> Suche
      wie bisher; Hoehe der Kopfzeile aendert sich hoechstens um den Abstand.
  A-N8-11 Schriftwechsel zur Laufzeit (Normal -> Sehr gross -> Normal): K10.

CI-Teil: "breite" (FG-96; bis die Datei dort eingetragen ist, laeuft sie
in "rest").

Start:  xvfb-run -a python test_suchfeld_rahmen_0632.py
"""

import json
import math
import os
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

FAKTOREN = {1.0: "normal", 1.15: "gross", 1.3: "sehr_gross"}
FENSTER = ((1120, 720), (1360, 900), (1920, 1080))
# Rahmenfarbe bis zu diesem RGB-Abstand (Kantenglaettung) - Testplan K11
FARB_ABSTAND = 40


def _rgb(text, widget):
    r, g, b = widget.winfo_rgb(text)
    return r >> 8, g >> 8, b >> 8


def _abstand(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def geometrie(frame, entry, scale):
    """K10: Fehlerliste fuer das Feld im Rahmen (echte Pixel). Das Feld ist
    ein Rechteck mit abgerundeten Ecken (corner_radius des Felds, gleiche
    Fuellfarbe wie der Rahmen): geprueft wird, dass sein Eckbogen ganz im
    Innenbogen des Rahmens liegt (Abstand der Mittelpunkte + Eckradius des
    Felds <= Innenradius des Rahmens)."""
    fehler = []
    fw, fh = frame.winfo_width(), frame.winfo_height()
    ex = entry.winfo_rootx() - frame.winfo_rootx()
    ey = entry.winfo_rooty() - frame.winfo_rooty()
    ew, eh = entry.winfo_width(), entry.winfo_height()
    border = math.ceil(frame.cget("border_width") * scale)
    radius = min(frame.cget("corner_radius") * scale, fh / 2.0, fw / 2.0)
    if ey < border:
        fehler.append("oben Abstand %d < Rahmen %d" % (ey, border))
    if fh - (ey + eh) < border:
        fehler.append("unten Abstand %d < Rahmen %d" % (fh - (ey + eh), border))
    if ex < border or fw - (ex + ew) < border:
        fehler.append("seitlich Abstand %d/%d < Rahmen %d" % (ex, fw - (ex + ew), border))
    innen = radius - border
    feld_r = min(entry.cget("corner_radius") * scale, eh / 2.0, ew / 2.0)
    for cx, cy, sx, sy in ((ex, ey, 1, 1), (ex + ew, ey, -1, 1), (ex, ey + eh, 1, -1),
                           (ex + ew, ey + eh, -1, -1)):
        # Mittelpunkt des Eckbogens des Felds
        kx, ky = cx + sx * feld_r, cy + sy * feld_r
        mx = radius if kx < radius else (fw - radius if kx > fw - radius else None)
        my = radius if ky < radius else (fh - radius if ky > fh - radius else None)
        if mx is None or my is None:
            continue
        dist = math.hypot(kx - mx, ky - my) + feld_r
        if dist > innen + 0.5:
            fehler.append("Ecke (%d,%d) ausserhalb des Innenbogens (%.1f > %.1f)"
                          % (cx, cy, dist, innen))
    return fehler, {"rahmen": [fw, fh], "feld": [ex, ey, ew, eh], "rand": border,
                    "radius": round(radius, 1)}


def pixel(frame, farbe, scale):
    """K11: Fehlerliste - Kante des Rahmens im Bildschirmfoto geschlossen."""
    from PIL import ImageGrab
    x0, y0 = frame.winfo_rootx(), frame.winfo_rooty()
    fw, fh = frame.winfo_width(), frame.winfo_height()
    bild = ImageGrab.grab(bbox=(x0, y0, x0 + fw, y0 + fh)).convert("RGB")
    radius = int(math.ceil(min(frame.cget("corner_radius") * scale, fh / 2.0)))
    border = max(1, int(round(frame.cget("border_width") * scale)))
    fehler = []

    hintergrund = bild.getpixel((0, 0))
    fuellung = bild.getpixel((fw - radius - 2, fh // 2))

    def rahmen(x, y):
        """Pixel gehoert zum Rahmen: nahe der Rahmenfarbe (<= FARB_ABSTAND)
        oder - Kantenglaettung - naeher an ihr als an Fuellung und
        Hintergrund."""
        if not (0 <= x < fw and 0 <= y < fh):
            return False
        wert = bild.getpixel((x, y))
        d = _abstand(wert, farbe)
        return d <= FARB_ABSTAND or (d < _abstand(wert, fuellung) and
                                     d < _abstand(wert, hintergrund))

    def nah(px_, py_):
        return any(rahmen(px_ + dx, py_ + dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1))

    luecken = []
    for x in range(radius + 1, fw - radius - 1):
        for kante in (border // 2, fh - 1 - border // 2):
            if not any(rahmen(x, kante + d) for d in (-1, 0, 1)):
                luecken.append((x, kante))
    if luecken:
        fehler.append("Kante oben/unten unterbrochen an %d Stellen, z. B. %r"
                      % (len(luecken), luecken[:4]))
    # Boegen: je Ecke drei Punkte (30, 45, 60 Grad) auf der Mitte des Rahmens
    r = radius - border / 2.0
    for mx, my, sx, sy in ((radius, radius, -1, -1), (fw - 1 - radius, radius, 1, -1),
                           (radius, fh - 1 - radius, -1, 1),
                           (fw - 1 - radius, fh - 1 - radius, 1, 1)):
        for grad in (30, 45, 60):
            w = math.radians(grad)
            px_, py_ = int(round(mx + sx * r * math.cos(w))), int(round(my + sy * r * math.sin(w)))
            if not nah(px_, py_):
                fehler.append("Bogen unterbrochen bei (%d,%d)" % (px_, py_))
    return fehler


def banner_ecken(panel, scale):
    """A-N8-13 (Testplan Frage 5): In den vier Ecken des Dashboard-Banners
    liegt ausserhalb des abgerundeten Verlaufs nur der Hintergrund (keine
    Linie der Zierkreise, kein Verlauf). Liefert (Fehler, Pixel ausserhalb
    gezaehlt)."""
    from PIL import ImageGrab
    x0, y0 = panel.winfo_rootx(), panel.winfo_rooty()
    fw, fh = panel.winfo_width(), panel.winfo_height()
    bild = ImageGrab.grab(bbox=(x0, y0, x0 + fw, y0 + fh)).convert("RGB")
    hintergrund = _rgb(panel.cget("bg"), panel)
    radius = 18 * scale
    fehler, gezaehlt = [], 0
    for mx, my, sx, sy in ((radius, radius, 0, 0), (fw - radius, radius, fw - radius, 0),
                           (radius, fh - radius, 0, fh - radius),
                           (fw - radius, fh - radius, fw - radius, fh - radius)):
        for y in range(int(sy), int(sy + radius)):
            for x in range(int(sx), int(sx + radius)):
                if math.hypot(x + 0.5 - mx, y + 0.5 - my) <= radius + 1.5:
                    continue
                gezaehlt += 1
                wert = bild.getpixel((x, y))
                if _abstand(wert, hintergrund) > FARB_ABSTAND:
                    fehler.append("Banner-Ecke: Pixel (%d,%d) %r ausserhalb der Rundung"
                                  % (x, y, wert))
    return fehler[:6], gezaehlt


def worker(faktor, gegenfarbe=False):
    home = tempfile.mkdtemp(prefix="fisi_bd08_")
    os.environ.update(HOME=home, APPDATA=home, FISI_DB_PATH=os.path.join(home, "t.db"),
                      FISI_SELFTEST=os.path.join(home, "log.txt"))
    import customtkinter as ctk
    import app_gui
    import fisi_theme
    import fisi_widgets
    if hasattr(app_gui, "apply_appearance"):
        app_gui.apply_appearance()
    fisi_theme.apply_font_size(FAKTOREN[faktor])
    fisi_widgets.apply_ui_scale(faktor)
    app_gui.UpdateController.auto_check = lambda self: None
    app_gui.SyncController.auto_start = lambda self: None
    errors = []
    app_gui.messagebox.showerror = lambda *a, **k: errors.append(a)
    root = ctk.CTk()
    root.geometry("%dx%d+0+0" % FENSTER[0])
    app = app_gui.FISIApp(root)

    def pump(seconds=0.3):
        end = time.time() + seconds
        while time.time() < end:
            root.update()
            time.sleep(0.01)

    pump(1.0)
    found, werte = [], {}
    for farbe in ("dunkel", "hell"):
        if farbe == "hell":
            app.change_color(mode=fisi_theme.MODE_LIGHT)
            pump(1.5)
        for breite, hoehe in FENSTER:
            app.show_view("dashboard")
            root.geometry("%dx%d+0+0" % (breite, hoehe))
            pump(0.8)
            header = app.header
            scale = fisi_widgets.px(1000) / 1000.0
            fehler, gezaehlt = banner_ecken(app.views["dashboard"].hero, scale)
            werte["Banner %s %dx%d %s" % (FAKTOREN[faktor], breite, hoehe, farbe)] = {
                "ecke_pixel": gezaehlt}
            found += ["Banner %s %dx%d %s: %s" % (FAKTOREN[faktor], breite, hoehe, farbe, f)
                      for f in fehler]
            for fokus in (False, True):
                if fokus:
                    header.search_entry.focus_force()
                else:
                    app.views["dashboard"].focus_force()
                pump(0.5)
                name = "%s %dx%d %s %s" % (FAKTOREN[faktor], breite, hoehe, farbe,
                                           "Fokus" if fokus else "ohne Fokus")
                scale = fisi_widgets.px(1000) / 1000.0
                fehler, geo = geometrie(header.search_box, header.search_entry, scale)
                soll = app_gui.C["purple"] if fokus else app_gui.C["field_border"]
                if gegenfarbe:
                    # Kontrollfehler K-N8-14: falsche Farbe -> muss rot werden
                    soll = app_gui.C["accent"]
                fehler += pixel(header.search_box, _rgb(soll, root), scale)
                geo["kopf"] = header.winfo_height()
                geo["feld_breite"] = header.search_entry.winfo_width()
                werte[name] = geo
                found += ["%s: %s" % (name, f) for f in fehler]
    # K12: Platzhalter, Breite, Strg+F, Eingabetaste
    header = app.header
    # (N-c: Auslassungszeichen statt drei Punkten)
    if header.search_entry.cget("placeholder_text") != "Suchen …  (Strg+F)":
        found.append("Platzhalter %r" % header.search_entry.cget("placeholder_text"))
    if header.search_entry.cget("width") != 250:
        found.append("Breite des Suchfelds %r" % header.search_entry.cget("width"))
    app.views["dashboard"].focus_force()
    pump(0.3)
    root.event_generate("<Control-f>")
    pump(0.3)
    if root.focus_get() is not header.search_entry._entry:
        found.append("Strg+F setzt den Fokus nicht ins Suchfeld")
    gesucht = []
    app.do_search = gesucht.append
    header.search_entry.delete(0, "end")
    header.search_entry.insert(0, "Subnetz")
    header.search_entry._entry.event_generate("<Return>")
    pump(0.3)
    if gesucht != ["Subnetz"]:
        found.append("Eingabetaste sucht nicht: %r" % gesucht)
    # A-N8-11: Schriftwechsel zur Laufzeit
    for stufe in ("sehr_gross", "normal"):
        app.change_font_size(stufe)
        pump(2.0)
        scale = fisi_widgets.px(1000) / 1000.0
        fehler, geo = geometrie(app.header.search_box, app.header.search_entry, scale)
        werte["Wechsel %s -> %s" % (FAKTOREN[faktor], stufe)] = geo
        found += ["Wechsel -> %s: %s" % (stufe, f) for f in fehler]
    if errors:
        found.append("Fehlermeldungen: %r" % errors)
    print("ERG " + json.dumps({"fehler": found, "werte": werte,
                               "schrift": fisi_widgets.F.get("family")}, ensure_ascii=False))
    sys.stdout.flush()
    os._exit(0)


def _tk_ok():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:  # noqa: BLE001
        return False


HAS_DISPLAY = False if "--fall" in sys.argv else _tk_ok()


def _fc_ohne(family):
    """fontconfig-Datei wie die des eigenen Prozesses, lehnt aber family (und
    ihre Display-Variante) ab (Muster test_rechner_seite_breite)."""
    path = os.path.join(tempfile.mkdtemp(prefix="fisi_fc_"), "fonts.conf")
    basis = os.path.abspath(os.environ.get("FONTCONFIG_FILE") or "/etc/fonts/fonts.conf")
    patterns = "".join(
        "<pattern><patelt name=\"family\"><string>%s</string></patelt></pattern>" % name
        for name in (family, family + " Display"))
    with open(path, "w", encoding="utf-8") as handle:
        handle.write('<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n'
                     '<fontconfig><include ignore_missing="yes">%s</include>'
                     '<selectfont><rejectfont>%s</rejectfont></selectfont>'
                     '</fontconfig>\n' % (basis, patterns))
    return path


_ERGEBNISSE = {}


def ergebnis(faktor, ohne=None, gegenfarbe=False):
    key = (faktor, ohne, gegenfarbe)
    if key not in _ERGEBNISSE:
        env = dict(os.environ)
        if ohne:
            env["FONTCONFIG_FILE"] = _fc_ohne(ohne)
        args = [sys.executable, os.path.abspath(__file__), "--fall", str(faktor)]
        if gegenfarbe:
            args.append("--gegenfarbe")
        done = subprocess.run(args, capture_output=True, text=True, timeout=900, cwd=HERE,
                              env=env)
        lines = [line for line in done.stdout.splitlines() if line.startswith("ERG ")]
        _ERGEBNISSE[key] = (json.loads(lines[-1][4:]) if lines else
                            "kein Ergebnis:\n%s\n%s" % (done.stdout[-2000:],
                                                        done.stderr[-4000:]))
    return _ERGEBNISSE[key]


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class SuchfeldRahmenTest(unittest.TestCase):

    def pruefen(self, faktor, ohne=None):
        result = ergebnis(faktor, ohne)
        self.assertIsInstance(result, dict, result)
        print("\n  Schrift %s" % result["schrift"])
        for name, geo in sorted(result["werte"].items()):
            print("    %s: %s" % (name, geo))
        self.assertEqual(result["fehler"], [], FAKTOREN[faktor])
        self.assertEqual(len(result["werte"]), 2 * 3 * len(FENSTER) + 2)
        self.assertTrue(all(geo["ecke_pixel"] > 0 for name, geo in result["werte"].items()
                            if name.startswith("Banner")))
        return result


class SuchfeldSchriftwechselTest(SuchfeldRahmenTest):
    """Dieselben Faelle mit abgelehnter Standardschrift."""

    def pruefen(self, faktor, ohne=None):
        standard = ergebnis(1.0)
        self.assertIsInstance(standard, dict, standard)
        result = super().pruefen(faktor, standard["schrift"])
        self.assertNotEqual(result["schrift"], standard["schrift"],
                            "fontconfig hat die Schrift nicht gewechselt")


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class PixelGegenprobeTest(unittest.TestCase):
    """K-N8-14: Mit einer falschen Sollfarbe (Akzentfarbe statt Rahmenfarbe)
    muss die Pixelpruefung rot werden - sie ist nicht immer gruen."""

    def test_falsche_farbe_wird_erkannt(self):
        result = ergebnis(1.0, gegenfarbe=True)
        self.assertIsInstance(result, dict, result)
        self.assertTrue(any("Kante oben/unten unterbrochen" in f for f in result["fehler"]),
                        result["fehler"][:5])


def _make(faktor):
    def test(self):
        self.pruefen(faktor)
    return test


for _faktor in FAKTOREN:
    setattr(SuchfeldRahmenTest, "test_%s" % FAKTOREN[_faktor], _make(_faktor))


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--fall":
        worker(float(sys.argv[2]), "--gegenfarbe" in sys.argv)
    unittest.main(verbosity=2)
