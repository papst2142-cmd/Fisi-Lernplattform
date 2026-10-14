#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests 0.63.2 N8 (B-D-06, PC): Listentitel brechen nicht mehr mitten im
Wort ohne Trennstrich um, die Nummer bleibt beim Titel, die Umbruchbreite
folgt der Zeile.

Plan-Nachtrag 0.63.2 Nr. 20, Testplan N8 Abschnitt 2 (K1, K2, K4, K5,
A-N8-01..04, A-N8-08). Listen: AP1-Szenarien, AP2-Szenarien, Testprojekt;
Normal/Gross/Sehr gross (je ein Prozess), Fenster 1120 x 720, 1360 x 900,
1920 x 1080; Seite 1 und die Seiten mit "Einführung einer
Mehrfaktor-Authentifizierung" und "Einfache Wirtschaftlichkeitsbetrachtung".
Jeder Fall mit der Standardschrift und mit abgelehnter Standardschrift
(im Container DejaVu Sans wie auf GitHub).

  K1  Umbruchbreite des Titels = Breite der Zeile (+-2 px), auch nach dem
      Ziehen des Fensters 1120 -> 1920 -> 1120 (nachgefuehrt)
  K2  Tk teilt kein Wort selbst (jedes Wort jeder Zeile passt in die
      Umbruchbreite); jede Zeile, die innerhalb eines Wortes endet, endet mit
      "-" (vorhandener Bindestrich oder Trennstrich der Regel) - AUSSER die
      Regel hatte keine zulaessige Stelle (Silbenregel wartet auf N8-F2): dann
      prueft der Test, dass es im Wort wirklich keine passende Stelle gab, und
      zaehlt den Fall (Ausgabe "Rueckfall").
  K4  Die Nummer ("4.") steht in derselben Zeile wie der Anfang des Titels.
  K5  Normal 1360, Standardschrift, ALLE Titel aller drei Listen: passt ein
      Titel mit dem gewoehnlichen Umbruch an Leerzeichen, ist der angezeigte
      Text zeichengleich zum bisherigen ("%d. %s%s").
  A-N8-08  Die Suche findet einen Titel weiter ueber den ungeteilten Text.

CI-Teil: "breite" (FG-96; bis die Datei dort eingetragen ist, laeuft sie
in "rest").

Start:  xvfb-run -a python test_listentitel_breite_0632.py
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

FAKTOREN = {1.0: "normal", 1.15: "gross", 1.3: "sehr_gross"}
FENSTER = ((1120, 720), (1360, 900), (1920, 1080))
ANSICHTEN = ("ap1scenarios", "scenarios", "testproject")
ZIELE = ("Einführung einer Mehrfaktor-Authentifizierung",
         "Einfache Wirtschaftlichkeitsbetrachtung")
NUMMER = re.compile(r"^(\d+)\. ")


def teile_zurueck(raw, shown):
    """Vergleicht den angezeigten Text mit dem urspruenglichen. Liefert je
    eingefuegtem Zeilenumbruch ("leer" = an einem Leerzeichen, "strich" =
    nach vorhandenem Bindestrich, "neu" = nach eingefuegtem Trennstrich,
    "im_wort" = mitten im Wort ohne Strich) oder None, wenn der Text sonst
    abweicht."""
    arten, i, j = [], 0, 0
    while j < len(shown):
        if shown[j] == "\n":
            if i < len(raw) and raw[i] == " ":
                arten.append("leer")
                i += 1
            elif i > 0 and raw[i - 1] == "-":
                arten.append("strich")
            else:
                arten.append("im_wort")
            j += 1
            continue
        if shown[j] == "-" and j + 1 < len(shown) and shown[j + 1] == "\n" and \
                (i >= len(raw) or raw[i] != "-"):
            arten.append("neu")
            j += 2
            continue
        if i >= len(raw) or raw[i] != shown[j]:
            return None
        i += 1
        j += 1
    return arten if i == len(raw) else None


def worker(faktor):
    home = tempfile.mkdtemp(prefix="fisi_bd06_")
    os.environ.update(HOME=home, APPDATA=home, FISI_DB_PATH=os.path.join(home, "t.db"),
                      FISI_SELFTEST=os.path.join(home, "log.txt"))
    import customtkinter as ctk
    import tkinter.font as tkfont
    import app_gui
    import fisi_theme
    import fisi_trennung
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

    pump(0.8)
    found, rueckfall, noop, werte = [], [], {}, {}

    def pruefe_seite(name, paged):
        for row in paged.rows:
            if row["position"] is None:
                continue
            item = paged.items[row["position"]]
            title = row["title"]
            # (alter Stand ohne "raw"/"title_box": der Titel steht ungeteilt
            # im Label, der Textbereich ist das Elternelement - so misst der
            # Test auch dort das Verhalten, nicht den Aufbau)
            raw = row.get("raw") or str(title.cget("text"))
            shown = str(title.cget("text"))
            fall = "%s #%d" % (name, row["position"] + 1)
            if not raw.startswith("%d. %s" % (row["position"] + 1, item["title"])):
                found.append("%s: Titeltext %r unerwartet" % (fall, raw))
                continue
            wrap = float(title._label.cget("wraplength"))
            box_w = row.get("title_box", title.master).winfo_width()
            inner_w = row.get("title_box", title).master.winfo_width()
            werte.setdefault(name, []).append([round(wrap), box_w])
            # K2: nichts abgeschnitten - der Rahmen ist so hoch wie der Titel
            if "title_box" in row and \
                    row["title_box"].winfo_height() < title.winfo_reqheight() - 1:
                found.append("%s: Titel abgeschnitten (Rahmen %d < Titel %d) (K2)"
                             % (fall, row["title_box"].winfo_height(),
                                title.winfo_reqheight()))
            # K1
            if abs(wrap - box_w) > 2 or abs(box_w - inner_w) > 2:
                found.append("%s: Umbruchbreite %d, Zeile %d, Textbereich %d (K1)"
                             % (fall, wrap, box_w, inner_w))
            font = tkfont.Font(font=title._label.cget("font"))
            # K2: Tk teilt kein Wort selbst
            for zeile in shown.split("\n"):
                for wort in zeile.split(" "):
                    if font.measure(wort) > wrap + 1:
                        found.append("%s: Wort %r breiter als die Umbruchbreite (%d > %d): "
                                     "Tk teilt es ohne Strich (K2)"
                                     % (fall, wort, font.measure(wort), wrap))
            arten = teile_zurueck(raw, shown)
            if arten is None:
                found.append("%s: angezeigter Text %r weicht vom Titel %r ab" % (fall, shown, raw))
                continue
            if "im_wort" in arten:
                # nur erlaubt, wenn die Regel keine passende Stelle hatte
                zeilen = shown.split("\n")
                for index, art in enumerate(arten):
                    if art != "im_wort":
                        continue
                    stueck = zeilen[index].split(" ")[-1] + zeilen[index + 1].split(" ")[0]
                    wort_ganz = [w for w in raw.split(" ") if stueck in w or
                                 stueck.startswith(w)]
                    wort = wort_ganz[0] if wort_ganz else stueck
                    # steht das Wort am Titelanfang, bleibt die Nummer davor
                    # (K4 geht vor): sie zaehlt zur ersten Zeile mit
                    vorn = ""
                    m_nr = NUMMER.match(raw)
                    if m_nr and index == 0 and raw.split(" ")[1:2] == [wort]:
                        vorn = m_nr.group(0).rstrip() + " "
                    passend = [p for p in fisi_trennung.trennstellen(wort)
                               if font.measure(vorn + (wort[:p] if wort[p - 1] == "-" else
                                                       wort[:p] + "-")) <= wrap]
                    if passend:
                        found.append("%s: Zeile endet im Wort ohne Strich, obwohl %r eine "
                                     "passende Stelle hat (K2)" % (fall, wort))
                    else:
                        rueckfall.append("%s: %r" % (fall, wort))
            # K4: Nummer nie allein
            erste = shown.split("\n")[0]
            m = NUMMER.match(raw)
            if m:
                ohne_umbruch = "\n" not in shown
                if ohne_umbruch:
                    erstes = raw.split(" ")[1] if len(raw.split(" ")) > 1 else ""
                    if font.measure(m.group(0) + erstes) > wrap + 1:
                        found.append("%s: Nummer allein in der ersten Zeile (K4)" % fall)
                elif erste.strip() == m.group(0).strip():
                    found.append("%s: Nummer allein in der ersten Zeile (K4)" % fall)
            # K5 (Normal 1360, Standardschrift - Auswertung im Elternprozess)
            if FAKTOREN[faktor] == "normal" and name.split()[1] == "1360x900":
                woerter_passen = all(font.measure(w) <= wrap for w in raw.split(" "))
                nummer_passt = True
                if m and len(raw.split(" ")) > 1:
                    nummer_passt = font.measure(m.group(0) + raw.split(" ")[1]) <= wrap
                noop["%s|%d" % (name.split()[2], row["position"])] = [
                    woerter_passen and nummer_passt, shown == raw]

    for breite, hoehe in FENSTER:
        for key in ANSICHTEN:
            app.show_view(key)
            root.geometry("%dx%d+0+0" % (breite, hoehe))
            pump(1.0)
            paged = app.views[key].paged
            seiten = {0, 1}   # Seite 2: Blaettern mit neuem Text (Hoehe folgt)
            for ziel in ZIELE:
                for position, item in enumerate(paged.items):
                    if item["title"] == ziel:
                        seiten.add(position // app_gui.LIST_PAGE_SIZE)
            alle = range(-(-len(paged.items) // app_gui.LIST_PAGE_SIZE)) \
                if FAKTOREN[faktor] == "normal" and breite == 1360 else sorted(seiten)
            for seite in alle:
                paged.page = seite
                paged._paint()
                pump(0.15)
                pruefe_seite("%s %dx%d %s S%d" % (FAKTOREN[faktor], breite, hoehe, key,
                                                  seite + 1), paged)
            paged.page = 0
            paged._paint()
    # K1 nachgefuehrt: 1120 -> 1920 -> 1120 mit offener Liste
    app.show_view("testproject")
    paged = app.views["testproject"].paged
    breiten = []
    for schritt, (breite, hoehe) in enumerate(((1120, 720), (1920, 1080), (1120, 720))):
        root.geometry("%dx%d+0+0" % (breite, hoehe))
        pump(1.2)
        row = paged.rows[0]
        breiten.append(row.get("title_box", row["title"].master).winfo_width())
        pruefe_seite("%s %dx%d gezogen %d" % (FAKTOREN[faktor], breite, hoehe, schritt + 1),
                     paged)
    # (je nach Stufe ist die Liste bei 1920 breiter oder - nebeneinander statt
    # untereinander - schmaler als bei 1120; sie muss sich aendern und
    # zurueckkehren, und in jedem Zustand gilt K1)
    if breiten[1] == breiten[0] or abs(breiten[2] - breiten[0]) > 2:
        found.append("Umbruchbreite folgt dem Fenster nicht: %r (K1)" % breiten)
    # A-N8-08: Suche ueber den ungeteilten Text
    for key, ziel in (("testproject", ZIELE[0]), ("ap1scenarios", ZIELE[1])):
        app.show_view(key)
        pump(0.5)
        paged = app.views[key].paged
        paged.search.delete(0, "end")
        paged.search.insert(0, ziel.split(" ")[-1])
        paged.refresh()
        pump(0.3)
        treffer = [paged.items[p]["title"] for p in paged.filtered]
        if ziel not in treffer:
            found.append("Suche nach %r findet %r nicht (A-N8-08)" % (ziel.split(" ")[-1], ziel))
        paged.search.delete(0, "end")
        paged.refresh()
    if errors:
        found.append("Fehlermeldungen: %r" % errors)
    print("ERG " + json.dumps({"fehler": found, "rueckfall": rueckfall, "noop": noop,
                               "breiten": breiten, "werte": werte,
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


def ergebnis(faktor, ohne=None):
    key = (faktor, ohne)
    if key not in _ERGEBNISSE:
        env = dict(os.environ)
        if ohne:
            env["FONTCONFIG_FILE"] = _fc_ohne(ohne)
        done = subprocess.run([sys.executable, os.path.abspath(__file__), "--fall",
                               str(faktor)],
                              capture_output=True, text=True, timeout=1200, cwd=HERE, env=env)
        lines = [line for line in done.stdout.splitlines() if line.startswith("ERG ")]
        _ERGEBNISSE[key] = (json.loads(lines[-1][4:]) if lines else
                            "kein Ergebnis:\n%s\n%s" % (done.stdout[-2000:],
                                                        done.stderr[-4000:]))
    return _ERGEBNISSE[key]


class TeileZurueckTest(unittest.TestCase):
    """Hilfsfunktion des Tests (ohne Anzeige)."""

    def test_arten(self):
        self.assertEqual(teile_zurueck("4. Ab Cd", "4. Ab\nCd"), ["leer"])
        self.assertEqual(teile_zurueck("Mehr-Faktor", "Mehr-\nFaktor"), ["strich"])
        self.assertEqual(teile_zurueck("Wirtschaft", "Wirt-\nschaft"), ["neu"])
        self.assertEqual(teile_zurueck("Wirtschaft", "Wirtsch\naft"), ["im_wort"])
        self.assertIsNone(teile_zurueck("Wirtschaft", "Wirtschaf"))


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class ListentitelBreiteTest(unittest.TestCase):

    def pruefen(self, faktor, ohne=None):
        result = ergebnis(faktor, ohne)
        self.assertIsInstance(result, dict, result)
        print("\n  Schrift %s, Breiten gezogen %r, Rueckfall (Silbenregel offen, N8-F2): %d"
              % (result["schrift"], result["breiten"], len(result["rueckfall"])))
        for zeile in result["rueckfall"]:
            print("    Rueckfall %s" % zeile)
        self.assertEqual(result["fehler"], [], FAKTOREN[faktor])
        # jede Ansicht in jedem Fenster geprueft, dazu dreimal gezogen
        for breite, hoehe in FENSTER:
            for key in ANSICHTEN:
                self.assertTrue(any(name.startswith("%s %dx%d %s S" % (
                    FAKTOREN[faktor], breite, hoehe, key)) for name in result["werte"]),
                    (breite, key))
        self.assertEqual(sum(1 for name in result["werte"] if "gezogen" in name), 3)
        return result


class ListentitelSchriftwechselTest(ListentitelBreiteTest):
    """Dieselben Faelle mit abgelehnter Standardschrift."""

    def pruefen(self, faktor, ohne=None):
        standard = ergebnis(1.0)
        self.assertIsInstance(standard, dict, standard)
        result = super().pruefen(faktor, standard["schrift"])
        self.assertNotEqual(result["schrift"], standard["schrift"],
                            "fontconfig hat die Schrift nicht gewechselt")


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class ListentitelNoOpTest(unittest.TestCase):
    """K5: Normal 1360, Standardschrift, alle Titel aller drei Listen."""

    def test_normal_1360_zeichengleich(self):
        result = ergebnis(1.0)
        self.assertIsInstance(result, dict, result)
        import fisi_core as fc
        anzahl = len(fc.AP1_SZENARIEN) + len(fc.SZENARIEN) + len(fc.PROJEKTARBEITEN)
        self.assertEqual(len(result["noop"]), anzahl)
        abweichend = sorted(k for k, (passt, gleich) in result["noop"].items()
                            if passt and not gleich)
        geaendert = sorted(k for k, (passt, gleich) in result["noop"].items() if not passt)
        print("\n  K5: %d Titel, davon %d mit Wortteilung/Nummer (Text geaendert): %s"
              % (anzahl, len(geaendert), geaendert))
        self.assertEqual(abweichend, [])


def _make(faktor):
    def test(self):
        self.pruefen(faktor)
    return test


for _faktor in FAKTOREN:
    setattr(ListentitelBreiteTest, "test_%s" % FAKTOREN[_faktor], _make(_faktor))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--fall":
        worker(float(sys.argv[2]))
    unittest.main(verbosity=2)
