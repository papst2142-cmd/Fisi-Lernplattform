#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests 0.63.1 Teil 1.3: PC-Subnetting-Karte - Umbruch und Breite.

Plan 0.63.1 Abschnitt 5.6: Fuer die Schriftgroessen Normal, Gross und Sehr
gross (Faktor 1,00 / 1,15 / 1,30) und die Fenster 1120 x 800 und 1360 x 900:
  * die Subnetting-Karte endet am rechten sichtbaren Rand (nie breiter als
    der sichtbare Bereich, Seite ganz links), ebenso jeder Kasten darin
  * die Unterschrift "IPv4"/"IPv6" ist abgebildet und im sichtbaren Bereich
  * jede Zeile, die keine Tabellenzeile ist, passt in die Breite des Kastens
    (in Pixeln gemessen, Festbreitenschrift)
  * Wortlaut: angezeigter Text ohne Leerraum = Rohtext ohne Leerraum
  * Woerter und Werte werden nie geteilt; erlaubte Bruchstellen sind nur
    nach ":" (IPv6) und vor "." (grosse Zahl), wie am Handy (fit_lines)
  * Tabellenzeilen (doppelte Leerzeichen) bleiben unveraendert (kein
    Tk-Umbruch, wrap="none"); passt eine nicht, laesst sich der Kasten
    seitlich schieben (Antwort 11)
fuer IPv4 (3 Ansichten) und IPv6 (2 Ansichten), Ergebnis und Rechenweg.

Jede Kombination laeuft in einem eigenen Prozess (Schriftgroesse und
Skalierung gelten ab dem Start). Gegen a74712d (0.63) rot.

Start:  xvfb-run -a python test_subnetz_pc_breite.py
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
FENSTER = ((1120, 800), (1360, 900))
# (Modus, Ansicht, Netz, zweites Feld)
FAELLE = (
    ("ipv4", "netzdaten", "192.168.1.50/24", None),
    ("ipv4", "netzdaten", "10.0.0.0/8", None),
    ("ipv6", "netzdaten", "fc00::/8", None),
    ("ipv6", "netzdaten", "4000::/16", None),
    ("ipv6", "netzdaten", "2001:db8::/32", None),
    ("ipv4", "aufteilen", "10.0.0.0/8", "1000"),
    ("ipv6", "aufteilen", "::/0", "300"),
    ("ipv6", "aufteilen", "2001:db8::/32", "300"),
    ("ipv4", "bedarf", "192.168.10.0/24", "A 50\nB 20\nC 10\nD 2"),
    ("ipv4", "bedarf", "10.0.0.0/8", "Server 2000\nBuero 500\nWLAN 300\nGaeste 60\nLink 2"),
)


def is_table(line):
    """Tabellenzeile wie in fit_lines: keine Zeile "Beschriftung : Wert" und
    Spalten durch zwei Leerzeichen getrennt."""
    pos = line.find(": ")
    if pos >= 0 and line[pos + 2:].strip():
        return False
    return "  " in line.strip()


def token_problems(raw, shown):
    """Woerter des Rohtexts muessen ganz bleiben; erlaubt ist nur ein Bruch
    nach ':' oder vor '.' (fit_lines, Plan 4.3 0.63). Gibt Fehltexte zurueck."""
    # "Beschriftung      : Wert" wird zu "Beschriftung:" (Abstand vor dem
    # Doppelpunkt entfaellt); das ist kein geteiltes Wort
    want = re.sub(r" +: ", ": ", raw).split()
    have = re.sub(r" +: ", ": ", shown).split()
    problems = []
    index = 0
    for word in want:
        built = ""
        parts = []
        while index < len(have) and len(built) < len(word):
            built += have[index]
            parts.append(have[index])
            index += 1
        if built != word:
            problems.append("Wort %r nicht wiedergefunden (%r)" % (word, parts))
            break
        for left, right in zip(parts, parts[1:]):
            if not (left.endswith(":") or right.startswith(".")):
                problems.append("Wort %r geteilt in %r" % (word, parts))
    if not problems and index != len(have):
        problems.append("Rest im Kasten: %r" % have[index:])
    return problems


def worker(faktor, breite, hoehe):
    """Laeuft im eigenen Prozess; gibt eine JSON-Zeile "ERG {...}" aus."""
    home = tempfile.mkdtemp(prefix="fisi_breite_")
    os.environ.update(HOME=home, APPDATA=home, FISI_DB_PATH=os.path.join(home, "t.db"),
                      FISI_SELFTEST=os.path.join(home, "log.txt"))
    import customtkinter as ctk
    import app_gui
    import fisi_core as fc
    import fisi_theme
    import fisi_widgets
    fisi_theme.apply_font_size(FAKTOREN[faktor])
    fisi_widgets.apply_ui_scale(faktor)
    app_gui.UpdateController.auto_check = lambda self: None
    app_gui.SyncController.auto_start = lambda self: None
    errors = []
    app_gui.messagebox.showerror = lambda *a, **k: errors.append(a)
    root = ctk.CTk()
    root.geometry("%dx%d+0+0" % (breite, hoehe))
    app = app_gui.FISIApp(root)

    def pump(seconds=0.35):
        end = time.time() + seconds
        while time.time() < end:
            root.update()
            time.sleep(0.01)

    pump(0.8)
    app.show_view("calc")
    root.geometry("%dx%d+0+0" % (breite, hoehe))
    pump(1.0)
    view = app.views["calc"]
    sub = view.subnet
    found = []
    stats = {"kaesten": 0, "zeilen": 0, "tabelle_zu_breit": 0, "umbrochen": 0}

    def raw_of(mode, key, net, other, info):
        version = 4 if mode == "ipv4" else 6
        if key == "netzdaten":
            if info:
                return fc.CALC_EXPLAIN_SUBNET if mode == "ipv4" else fc.CALC_EXPLAIN_SUBNET_V6
            text = fc.subnet_report(net)
            details = getattr(fc, "ipv6_details", None) if mode == "ipv6" else None
            if details is not None:
                text += "".join("\n%-22s: %s" % pair for pair in details(net))
            return text
        if key == "aufteilen":
            result = fc.split_network(net, other, version=version)
            return fc.split_explain(result) if info else fc.split_report(result, 1)
        result = fc.subnet_by_hosts(net, other, version=4)
        return fc.hosts_explain(result) if info else fc.hosts_report(result)

    def check_box(name, box, raw):
        stats["kaesten"] += 1
        text = box._textbox
        shown = box.get("1.0", "end-1c")
        fit_raw = getattr(box, "fit_raw", None)
        if fit_raw is not None and fit_raw != raw:
            found.append("%s: gemerkter Rohtext weicht vom Kern ab" % name)
        if str(text.cget("wrap")) != "none":
            # Plan 5.2 Schritt 3: der Kasten bricht selbst um (fit_lines); ein
            # Tk-Umbruch wuerde Tabellenzeilen zerreissen
            found.append("%s: Kasten bricht per Tk um (wrap=%s)" % (name, text.cget("wrap")))
        font = text.cget("font")
        edge = sum(int(float(text.cget(o))) for o in ("padx", "borderwidth",
                                                       "highlightthickness"))
        inner = text.winfo_width() - 2 * edge
        raw_lines = raw.split("\n")
        wide_table = False
        for line in shown.split("\n"):
            stats["zeilen"] += 1
            width = int(text.tk.call("font", "measure", font, line))
            if is_table(line):
                if line not in raw_lines:
                    found.append("%s: Tabellenzeile veraendert: %r" % (name, line))
                if width > inner:
                    wide_table = True
                continue
            if width > inner:
                found.append("%s: Zeile breiter als der Kasten (%d > %d px): %r"
                             % (name, width, inner, line))
        for line in raw_lines:
            if is_table(line) and line not in shown.split("\n"):
                found.append("%s: Tabellenzeile fehlt: %r" % (name, line))
        if "".join(shown.split()) != "".join(raw.split()):
            found.append("%s: Wortlaut weicht ab" % name)
        found.extend("%s: %s" % (name, p) for p in token_problems(raw, shown))
        if shown != raw:
            stats["umbrochen"] += 1
        if wide_table:
            stats["tabelle_zu_breit"] += 1
            bar = getattr(box, "_x_scrollbar", None)
            if bar is None or not bar.winfo_ismapped():
                found.append("%s: Tabelle breiter als der Kasten, aber kein Rollbalken im Kasten"
                             % name)
        right = box.winfo_rootx() + box.winfo_width()
        visible = view.canvas.winfo_rootx() + view.canvas.winfo_width()
        if right > visible:
            found.append("%s: Kasten ragt %d px ueber den sichtbaren Rand" % (name, right - visible))

    for mode, key, net, other in FAELLE:
        sub.mode_pills.select_value(mode)
        sub.view_pills[mode].select_value(key)
        data = sub.views[(mode, key)]
        data["net"].set(net)
        if key == "aufteilen":
            data["count"].set(other)
        elif key == "bedarf":
            app_gui.set_text(data["needs"], other)
        sub.calc(mode, key)
        if not data["info_open"]:
            sub.toggle_info(mode, key)
        view.canvas.xview_moveto(0)
        pump()
        name = "%s/%s %s" % (mode, key, net)
        check_box(name + " Ergebnis", data["box"], raw_of(mode, key, net, other, False))
        check_box(name + " Rechenweg", data["info"], raw_of(mode, key, net, other, True))
        sub.toggle_info(mode, key)
        # Karte und Unterschrift
        card = sub.card
        right = card.winfo_rootx() + card.winfo_width()
        visible = view.canvas.winfo_rootx() + view.canvas.winfo_width()
        if right > visible:
            found.append("%s: Karte ragt %d px ueber den sichtbaren Rand" % (name, right - visible))
        label = card._sub_below if getattr(card, "_sub_stacked", False) else card.subtitle_label
        if not label.winfo_ismapped() or label.cget("text") != fc.SUBNET_SUBTITLE[mode]:
            found.append("%s: Unterschrift nicht abgebildet (%r)" % (name, label.cget("text")))
        elif label.winfo_rootx() + label.winfo_width() > visible:
            found.append("%s: Unterschrift ausserhalb des sichtbaren Bereichs" % name)
    if errors:
        found.append("Fehlermeldungen: %r" % errors)
    print("ERG " + json.dumps({"fehler": found, "werte": stats}, ensure_ascii=False))
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


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class BreiteTest(unittest.TestCase):
    """Je Schriftgroesse und Fenster ein Prozess (worker)."""

    def run_case(self, faktor, breite, hoehe):
        done = subprocess.run([sys.executable, os.path.abspath(__file__), "--fall",
                               str(faktor), str(breite), str(hoehe)],
                              capture_output=True, text=True, timeout=600, cwd=HERE)
        lines = [line for line in done.stdout.splitlines() if line.startswith("ERG ")]
        self.assertTrue(lines, "kein Ergebnis:\n%s\n%s" % (done.stdout[-2000:], done.stderr[-4000:]))
        result = json.loads(lines[-1][4:])
        print("\n  %s %dx%d: %s" % (FAKTOREN[faktor], breite, hoehe, result["werte"]))
        self.assertEqual(result["fehler"], [], "%s %dx%d" % (FAKTOREN[faktor], breite, hoehe))
        return result["werte"]


def _make(faktor, breite, hoehe):
    def test(self):
        werte = self.run_case(faktor, breite, hoehe)
        self.assertEqual(werte["kaesten"], 2 * len(FAELLE))
    return test


for _faktor in FAKTOREN:
    for _breite, _hoehe in FENSTER:
        setattr(BreiteTest, "test_%s_%d" % (FAKTOREN[_faktor], _breite),
                _make(_faktor, _breite, _hoehe))


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class AutogrowOhneUmbruchTest(unittest.TestCase):
    """Plan 5.2 Schritt 3: make_autogrow_text(wrap="none") zaehlt Textzeilen
    (eine zu lange Zeile bleibt eine Anzeigezeile) und waechst danach."""

    def test_zeilen(self):
        import customtkinter as ctk
        import fisi_widgets as fw
        mono = ("Courier", 10)
        root = ctk.CTk()
        try:
            box = fw.make_autogrow_text(root, min_height=2, max_height=40,
                                        font=mono, wrap="none")
            box.configure(width=120)
            box.pack()
            fw.set_text(box, "\n".join(["x" * 200] * 5))
            for _ in range(5):
                root.update()
            self.assertEqual(str(box._textbox.cget("wrap")), "none")
            self.assertEqual(fw._display_line_count(box), 5)
            self.assertEqual(box.cget("height"), fw._text_height(mono, 6))
            # Standard bleibt "word" (alle anderen Aufrufer unveraendert)
            plain = fw.make_autogrow_text(root, font=mono)
            self.assertEqual(str(plain._textbox.cget("wrap")), "word")
            self.assertEqual(str(fw.make_text(root, font=mono)._textbox.cget("wrap")), "word")
        finally:
            root.destroy()


class TokenRegelTest(unittest.TestCase):
    """Die Pruefhilfe selbst (ohne Oberflaeche)."""

    def test_token_regel(self):
        self.assertEqual(token_problems("A : fd12:3456::1", "A:\n  fd12:\n  3456::1"), [])
        self.assertEqual(token_problems("Z : 1.208.925.819", "Z:\n  1.208\n  .925.819"), [])
        self.assertTrue(token_problems("Satz mit Wort", "Satz mit Wo\nrt"))
        self.assertTrue(token_problems("a b", "a b c"))


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "--fall":
        worker(float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]))
    unittest.main(verbosity=2)
