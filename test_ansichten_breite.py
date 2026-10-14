#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests 0.63.2 D2 (B-D-01/B-D-02): Nicht-Spiel-Ansichten passen in die Breite.

Plan 0.63.2 (4.1 D2, Teilplan S1 "Teilschritt B-D-01/B-D-02"): Bei den
Schriftgroessen Normal, Gross und Sehr gross (Faktor 1,00 / 1,15 / 1,30)
und den Fenstern 1120 x 720 (Mindestgroesse) und 1360 x 900 gilt fuer jede
geprueften Ansicht, in jedem geprueften Zustand:
  * kein seitlicher Schieberegler: canvas.xview() == (0.0, 1.0), der
    Inhalt ist nicht breiter als der sichtbare Bereich
  * jedes Bedienelement (Knopf, Feld, Aufklappliste, Haken, Textkasten)
    liegt ganz im sichtbaren Bereich und ganz in seinem Rahmen (nicht
    abgeschnitten) und ueberlappt kein anderes
  * steht der Inhalt neben der Liste, ist er mindestens 440 logische px
    breit; sonst stehen Liste und Inhalt untereinander (beide in voller
    Breite), und der Inhalt steht nach "Naechstes ..." oben im sichtbaren
    Bereich
  * Ueberschrift, Meta-Zeile und Hinweis: passt der Text in die Spalte,
    steht er in einer Zeile (1360 Normal wie 14b3bd4), sonst bricht er erst
    an der Spaltenbreite um (untereinander nicht so schmal wie neben der
    Liste, kein Umbruch mitten im Wort)
  * Aufklapplisten zaehlen auch als abgeleitete Klasse (FramedOptionMenu)
  * bei 1360 x 900 Normal bleibt die Anordnung wie bisher (zwei Spalten im
    Raster mit gleich breiten Einheiten, Kopfzeilen nicht umbrochen)

Aufbau zum Erweitern (S1c2, Z3): Jede Ansicht ist ein Eintrag in ANSICHTEN
(Name -> Pruef-Funktion, siehe @ansicht) und hat eine eigene Testklasse
(Unterklasse von AnsichtBreiteBasis mit NAME). Alle Ansichten laufen je
Schriftgroesse und Fenster in EINEM Prozess (Schriftgroesse und Skalierung
gelten ab dem Start); das Ergebnis wird fuer alle Klassen zwischengespeichert.

Gegen 14b3bd4 (0.63.1) rot (seitlicher Schieberegler in allen vier Ansichten
bei 1120 x 720, Messung Plan: +34 bis +565 px).

Ab CI Welle 3b (0.63.2): Auf GitHub fehlt Inter, dort waehlt die App DejaVu
Sans (breiter). Dann war AP2 bei Sehr gross 1360 nach "Musterloesung
anzeigen" 25 px zu breit (der laengere Knopftext loeste keine neue Anpassung
aus) und das Testprojekt bei Normal 1360 nicht mehr im Raster wie bisher.
Deshalb laeuft jeder Fall zusaetzlich mit einer anderen Schrift
(test_..._andere_schrift): die Standardschrift wird per fontconfig abgelehnt
- im Container DejaVu Sans statt Inter wie auf GitHub, auf GitHub eine
dritte Schrift. Geprueft wird, dass wirklich eine andere Schrift gewaehlt
wurde; alle Anforderungen oben gelten unveraendert.

Start:  xvfb-run -a python test_ansichten_breite.py
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

FAKTOREN = {1.0: "normal", 1.15: "gross", 1.3: "sehr_gross"}
FENSTER = ((1120, 720), (1360, 900))

# Name -> Pruef-Funktion(ctx); Reihenfolge = Reihenfolge im Prozess
ANSICHTEN = {}


def ansicht(name):
    """Pruef-Funktion fuer eine Ansicht anmelden. Sie bekommt ctx (siehe
    Ctx) und ruft ctx.pruefe(zustand) fuer jeden Zustand der Ansicht."""
    def register(func):
        ANSICHTEN[name] = func
        return func
    return register


# ---------------------------------------------------------------------------
#  Im Prozess (worker)
# ---------------------------------------------------------------------------

BEDIEN_KLASSEN = ("NeoButton", "EntryBox", "CTkEntry", "CTkOptionMenu", "CTkCheckBox",
                  "CTkTextbox", "CTkSwitch", "IconButton")


def ist_bedienelement(widget):
    """Auch abgeleitete Klassen zaehlen (z. B. FramedOptionMenu aus
    CTkOptionMenu): Vergleich ueber alle Basisklassen, nicht nur den
    genauen Klassennamen."""
    return any(klasse.__name__ in BEDIEN_KLASSEN for klasse in type(widget).__mro__)


class Ctx:
    """Umgebung einer Pruefung im Prozess: app, root, pump, Fundliste."""

    def __init__(self, app, root, faktor, breite, hoehe):
        self.app = app
        self.root = root
        self.faktor = faktor
        self.breite = breite
        self.hoehe = hoehe
        self.fehler = []
        self.werte = {}
        self.view = None
        self.name = ""

    def pump(self, seconds=0.4):
        end = time.time() + seconds
        while time.time() < end:
            self.root.update()
            time.sleep(0.01)

    def zeige(self, key):
        self.app.show_view(key)
        self.pump(0.6)
        self.view = self.app.views[key]
        self.view.to_top()
        self.pump(0.6)
        return self.view

    def breit(self):
        """Breites Fenster mit normaler Schrift (Anordnung wie bisher)."""
        return self.faktor == 1.0 and self.breite >= 1360

    def pruefe(self, zustand):
        """Allgemeine Breiten-Pruefung der aktuellen Ansicht."""
        view = self.view
        self.pump(0.3)
        name = "%s/%s" % (self.name, zustand)
        sicht = view.canvas.winfo_width()
        inhalt = view.inner.winfo_reqwidth()
        xview = tuple(round(x, 4) for x in view.canvas.xview())
        self.werte[name] = {"sichtbar": sicht, "inhalt": inhalt}
        if xview != (0.0, 1.0):
            self.fehler.append("%s: seitlich verschiebbar, xview %s (Inhalt %d > sichtbar %d)"
                               % (name, xview, inhalt, sicht))
        if inhalt > sicht + 1:
            self.fehler.append("%s: Inhalt %d px breiter als sichtbar (%d)"
                               % (name, inhalt - sicht, sicht))
        links = view.canvas.winfo_rootx()
        rechts = links + sicht
        boxes = []
        stack = [view.inner]
        while stack:
            widget = stack.pop()
            for child in widget.winfo_children():
                try:
                    if not child.winfo_ismapped():
                        continue
                except Exception:  # noqa: BLE001
                    continue
                if ist_bedienelement(child):
                    boxes.append(child)
                    continue
                stack.append(child)
        for child in boxes:
            x, y = child.winfo_rootx(), child.winfo_rooty()
            w, h = child.winfo_width(), child.winfo_height()
            text = ""
            try:
                text = str(child.cget("text"))[:30]
            except Exception:  # noqa: BLE001
                pass
            label = "%s %r" % (type(child).__name__, text)
            if x < links - 1 or x + w > rechts + 1:
                self.fehler.append("%s: %s ausserhalb des sichtbaren Bereichs (x %d..%d, "
                                   "sichtbar %d..%d)" % (name, label, x, x + w, links, rechts))
            master = child.master
            mx, my = master.winfo_rootx(), master.winfo_rooty()
            if (x < mx - 1 or y < my - 1 or x + w > mx + master.winfo_width() + 1
                    or y + h > my + master.winfo_height() + 1):
                self.fehler.append("%s: %s ragt aus seinem Rahmen (abgeschnitten)" % (name, label))
            if w < child.winfo_reqwidth() - 2 and type(child).__name__ not in (
                    "CTkTextbox", "EntryBox", "CTkEntry"):
                self.fehler.append("%s: %s schmaler als verlangt (%d < %d)"
                                   % (name, label, w, child.winfo_reqwidth()))
        rects = [(c, c.winfo_rootx(), c.winfo_rooty(), c.winfo_width(), c.winfo_height())
                 for c in boxes]
        for i, (a, ax, ay, aw, ah) in enumerate(rects):
            for b, bx, by, bw, bh in rects[i + 1:]:
                if ax < bx + bw - 1 and bx < ax + aw - 1 and ay < by + bh - 1 and by < ay + ah - 1:
                    self.fehler.append("%s: %s und %s ueberlappen" % (
                        name, type(a).__name__ + repr(_text(a)), type(b).__name__ + repr(_text(b))))
        self.werte[name]["bedienelemente"] = len(boxes)
        return boxes


def _text(widget):
    try:
        return str(widget.cget("text"))[:30]
    except Exception:  # noqa: BLE001
        return ""


def _zwei_spalten_wie_bisher(ctx, layout, links, rechts, gruppe):
    """1360 x 900 Normal: Liste links, Inhalt rechts, Raster mit gleich
    breiten Einheiten (uniform) wie vor 0.63.2."""
    name = "%s/breit" % ctx.name
    info_l, info_r = links.grid_info(), rechts.grid_info()
    if (int(info_l["row"]), int(info_l["column"])) != (0, 0) or \
            (int(info_r["row"]), int(info_r["column"])) != (0, 1):
        ctx.fehler.append("%s: Spalten nicht nebeneinander (%s / %s)"
                          % (name, (info_l["row"], info_l["column"]),
                             (info_r["row"], info_r["column"])))
    for column, weight in ((0, 2), (1, 5)):
        conf = layout.grid_columnconfigure(column)
        if int(conf["weight"]) != weight or str(conf["uniform"]) != gruppe:
            ctx.fehler.append("%s: Spalte %d %s statt Gewicht %d, uniform %r"
                              % (name, column, conf, weight, gruppe))


def _inhalt_breit_genug(ctx, detail):
    """Teil b: steht der Inhalt neben der Liste, ist er mindestens 440
    logische px breit (lesbar); sonst stehen beide untereinander."""
    if int(detail.grid_info()["column"]) != 1:
        return
    breite = detail.winfo_width() / ctx.faktor
    if breite < 440 - 1:
        ctx.fehler.append("%s: Inhalt neben der Liste nur %d logische px breit"
                          % (ctx.name, breite))


def _gestapelt_volle_breite(ctx, detail):
    """Untereinander nutzen Liste und Inhalt die ganze Breite (Gegenpruefung
    L5, Mutation G3: Gewichte 2 : 5 blieben, die leere Spalte 1 nahm dann
    5/7 der Breite)."""
    if getattr(ctx.view, "column_mode", None) != "gestapelt":
        return
    layout = detail.master
    links = layout.grid_slaves(row=0, column=0)[0]
    voll = layout.winfo_width()
    for teil, name in ((links, "Liste"), (detail, "Inhalt")):
        if teil.winfo_width() < voll - 2:
            ctx.fehler.append("%s/gestapelt: %s nur %d von %d px breit"
                              % (ctx.name, name, teil.winfo_width(), voll))


def _inhalt_sichtbar(ctx, detail):
    """Untereinander (Teil b): nach "Naechstes ..." steht der Inhalt (unter
    der Liste) oben im sichtbaren Bereich."""
    view = ctx.view
    if getattr(view, "column_mode", None) != "gestapelt":
        return
    ctx.pump(0.3)
    oben = detail.winfo_rooty() - view.canvas.winfo_rooty()
    if not 0 <= oben < view.canvas.winfo_height() // 3:
        ctx.fehler.append("%s/naechstes: Inhalt nicht oben im Bild (y %d)" % (ctx.name, oben))


def _umbruch_passend(ctx, label, detail, immer):
    """Textbreiten an die Spalte gekoppelt: passt der Text in die Spalte,
    steht er in einer Zeile (bei breitem Fenster wie 14b3bd4); sonst bricht
    er erst an der Spaltenbreite um (nicht schmaler, nicht mitten im Wort).
    immer=False: nur untereinander gefordert (sonst wie bisher)."""
    import tkinter as tk
    import tkinter.font as tkfont
    if not immer and getattr(ctx.view, "column_mode", None) != "gestapelt":
        return
    text = str(label.cget("text"))
    if not text or not label.winfo_ismapped():
        return
    inner = label._label
    font = tkfont.Font(font=inner.cget("font"))
    wort = max(font.measure(w) for w in text.split())
    einzug = label.winfo_rootx() - detail.winfo_rootx()
    spalte = detail.winfo_width() - 2 * einzug
    toleranz = int(24 * ctx.faktor)
    # Breite und Hoehe in einer Zeile so, wie Tk den Text setzt
    # (font.measure liegt bei "  ·  " einige px darunter)
    probe = tk.Label(inner.master, text=text, font=inner.cget("font"),
                     padx=inner.cget("padx"), pady=inner.cget("pady"),
                     borderwidth=inner.cget("borderwidth"))
    natur = probe.winfo_reqwidth()
    eine_zeile = probe.winfo_reqheight()
    probe.destroy()
    hoehe = inner.winfo_reqheight()
    wrap = int(float(str(inner.cget("wraplength")) or 0))
    name = "%s/%s" % (ctx.name, label.winfo_name())
    if natur <= spalte - toleranz:
        if hoehe > eine_zeile:
            ctx.fehler.append("%s: Text bricht um, obwohl er in die Spalte passt "
                              "(Text %d, Spalte %d, Hoehe %d statt %d)"
                              % (name, natur, spalte, hoehe, eine_zeile))
    elif wrap and wrap < spalte - toleranz:
        ctx.fehler.append("%s: Umbruch bei %d px, Spalte %d px breit"
                          % (name, wrap, spalte))
    if wrap and wrap < wort:
        ctx.fehler.append("%s: Wort breiter als die Umbruchbreite (%d > %d): "
                          "Umbruch mitten im Wort" % (name, wort, wrap))


def _laengste_titel(daten, anzahl=4):
    """Die Titel mit den laengsten Woertern und die laengsten Titel (alle
    330 AP2-Szenarien zu laden dauert zu lange)."""
    wort = sorted(range(len(daten)), key=lambda i: -max(
        len(w) for w in daten[i]["title"].split()))[:anzahl]
    lang = sorted(range(len(daten)), key=lambda i: -len(daten[i]["title"]))[:anzahl]
    return sorted(set(wort + lang))


def _szenarien(ctx, key, gruppe):
    view = ctx.zeige(key)
    ctx.pruefe("start")
    view.toggle_solution()
    ctx.pruefe("loesung")
    view.next_scenario()
    ctx.pump(0.4)
    ctx.pruefe("naechstes")
    _inhalt_sichtbar(ctx, view.task_card.master)
    _inhalt_breit_genug(ctx, view.task_card.master)
    _gestapelt_volle_breite(ctx, view.task_card.master)
    detail = view.task_card.master
    if ctx.breit():
        layout = detail.master
        _zwei_spalten_wie_bisher(ctx, layout, layout.grid_slaves(row=0, column=0)[0],
                                 detail, gruppe)
    hinweis = getattr(view, "lbl_own_hint", None) or next(
        w for w in view.own_card.body.winfo_children() if type(w).__name__ == "CTkLabel")
    _umbruch_passend(ctx, hinweis, detail, True)
    for nummer in _laengste_titel(view.DATA):
        view.load_scenario(nummer)
        ctx.pump(0.05)
        _umbruch_passend(ctx, view.lbl_title, detail, False)


@ansicht("ap1")
def pruefe_ap1(ctx):
    _szenarien(ctx, "ap1scenarios", "scen")


@ansicht("ap2")
def pruefe_ap2(ctx):
    _szenarien(ctx, "scenarios", "scen")


@ansicht("testprojekt")
def pruefe_testprojekt(ctx):
    view = ctx.zeige("testproject")
    ctx.pruefe("start")
    view.toggle_hints()
    ctx.pruefe("loesung")
    view.next_project()
    ctx.pump(0.4)
    ctx.pruefe("naechstes")
    _inhalt_sichtbar(ctx, view.task_card.master)
    _inhalt_breit_genug(ctx, view.task_card.master)
    _gestapelt_volle_breite(ctx, view.task_card.master)
    detail = view.task_card.master
    if ctx.breit():
        layout = detail.master
        _zwei_spalten_wie_bisher(ctx, layout, layout.grid_slaves(row=0, column=0)[0],
                                 detail, "proj")
    # alle Projekte durchgehen: lange Titel ("Wirtschaftlichkeitsvergleich")
    # und Meta-Zeilen (Normal 1360: eine Zeile wie 14b3bd4)
    import app_gui
    for nummer in range(len(app_gui.PROJEKTARBEITEN)):  # 50, alle
        view.load_project(nummer)
        ctx.pump(0.05)
        _umbruch_passend(ctx, view.header_label, detail, False)
        _umbruch_passend(ctx, view.meta_label, detail, True)


@ansicht("abschlussprojekt")
def pruefe_abschlussprojekt(ctx):
    import fisi_projekt as fpj
    view = ctx.zeige("abschluss")
    for tab, _label in fpj.TABS:
        view._on_tab(tab)
        ctx.pump(0.5)
        ctx.pruefe(tab)
    view._on_tab(fpj.TABS[0][0])
    ctx.pump(0.3)
    if ctx.breit():
        # Kopfzeile wie bisher: alles in einer Zeile (gepackt)
        top = view.content.pack_slaves()[0]
        if len(top.pack_slaves()) < 6:
            ctx.fehler.append("abschlussprojekt/breit: Kopfzeile nicht mehr gepackt "
                              "(%d Teile)" % len(top.pack_slaves()))


def worker(faktor, breite, hoehe, namen):
    """Laeuft im eigenen Prozess; gibt eine JSON-Zeile "ERG {...}" aus."""
    home = tempfile.mkdtemp(prefix="fisi_ansichten_")
    os.environ.update(HOME=home, APPDATA=home, FISI_DB_PATH=os.path.join(home, "t.db"),
                      FISI_SELFTEST=os.path.join(home, "log.txt"))
    import customtkinter as ctk
    import app_gui
    import fisi_theme
    import fisi_widgets
    fisi_theme.apply_font_size(FAKTOREN[faktor])
    fisi_widgets.apply_ui_scale(faktor)
    app_gui.UpdateController.auto_check = lambda self: None
    app_gui.SyncController.auto_start = lambda self: None
    meldungen = []
    app_gui.messagebox.showerror = lambda *a, **k: meldungen.append(a)
    root = ctk.CTk()
    root.geometry("%dx%d+0+0" % (breite, hoehe))
    app = app_gui.FISIApp(root)
    ctx = Ctx(app, root, faktor, breite, hoehe)
    ctx.pump(0.8)
    root.geometry("%dx%d+0+0" % (breite, hoehe))
    ctx.pump(0.8)
    ergebnis = {}
    for name in namen:
        ctx.fehler, ctx.werte, ctx.name = [], {}, name
        try:
            ANSICHTEN[name](ctx)
        except Exception as error:  # noqa: BLE001
            import traceback
            ctx.fehler.append("%s: Ausnahme %r\n%s" % (name, error, traceback.format_exc()))
        ergebnis[name] = {"fehler": ctx.fehler, "werte": ctx.werte}
    if meldungen:
        for name in namen:
            ergebnis[name]["fehler"].append("Fehlermeldungen: %r" % meldungen)
    for name in namen:
        ergebnis[name]["schrift"] = fisi_widgets.F.get("family")
    print("ERG " + json.dumps(ergebnis, ensure_ascii=False))
    sys.stdout.flush()
    os._exit(0)


# ---------------------------------------------------------------------------
#  Testfaelle
# ---------------------------------------------------------------------------

def _tk_ok():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:  # noqa: BLE001
        return False


HAS_DISPLAY = False if "--fall" in sys.argv else _tk_ok()
_ERGEBNISSE = {}


def _fc_ohne(family):
    """fontconfig-Datei, die die Einstellungen des eigenen Prozesses nutzt
    (ein gesetztes FONTCONFIG_FILE, sonst die des Systems), aber zusaetzlich
    family (und ihre Display-Variante) ablehnt (Muster aus N5,
    test_spiel_breite_0632)."""
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


def ergebnis(faktor, breite, hoehe, ohne=None):
    """Alle angemeldeten Ansichten fuer eine Schriftgroesse und ein Fenster
    (ein Prozess, Ergebnis zwischengespeichert); ohne = abgelehnte Schrift."""
    key = (faktor, breite, hoehe, ohne)
    if key not in _ERGEBNISSE:
        env = dict(os.environ)
        if ohne:
            env["FONTCONFIG_FILE"] = _fc_ohne(ohne)
        done = subprocess.run([sys.executable, os.path.abspath(__file__), "--fall",
                               str(faktor), str(breite), str(hoehe)] + list(ANSICHTEN),
                              capture_output=True, text=True, timeout=900, cwd=HERE, env=env)
        lines = [line for line in done.stdout.splitlines() if line.startswith("ERG ")]
        _ERGEBNISSE[key] = (json.loads(lines[-1][4:]) if lines else
                            "kein Ergebnis:\n%s\n%s" % (done.stdout[-2000:], done.stderr[-4000:]))
    return _ERGEBNISSE[key]


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class AnsichtBreiteBasis(unittest.TestCase):
    """Basis: Unterklassen setzen NAME (Schluessel in ANSICHTEN)."""

    NAME = None

    def run_case(self, faktor, breite, hoehe, ohne=None):
        if self.NAME is None:
            self.skipTest("Basisklasse")
        result = ergebnis(faktor, breite, hoehe, ohne)
        self.assertIsInstance(result, dict, result)
        mine = result[self.NAME]
        print("\n  %s %s %dx%d (%s): %s" % (self.NAME, FAKTOREN[faktor], breite, hoehe,
                                           mine["schrift"],
                                           {k: v["inhalt"] for k, v in mine["werte"].items()}))
        self.assertEqual(mine["fehler"], [], "%s %s %dx%d (Schrift %s)"
                         % (self.NAME, FAKTOREN[faktor], breite, hoehe, mine["schrift"]))
        self.assertTrue(mine["werte"], "keine Zustaende geprueft")
        return mine


def _make(faktor, breite, hoehe):
    def test(self):
        self.run_case(faktor, breite, hoehe)
    return test


def _make_ohne(faktor, breite, hoehe):
    """Derselbe Fall mit abgelehnter Standardschrift (andere Schriftmetrik)."""
    def test(self):
        if self.NAME is None:
            self.skipTest("Basisklasse")
        standard = ergebnis(faktor, breite, hoehe)
        self.assertIsInstance(standard, dict, standard)
        family = standard[self.NAME]["schrift"]
        mine = self.run_case(faktor, breite, hoehe, ohne=family)
        self.assertNotEqual(mine["schrift"], family, "Schrift nicht gewechselt")
    return test


def fuer_alle_fenster(cls):
    """Klassen-Dekorator: je Schriftgroesse und Fenster ein Testfall, dazu
    derselbe mit einer anderen Schrift (ab CI Welle 3b)."""
    for faktor in FAKTOREN:
        for breite, hoehe in FENSTER:
            setattr(cls, "test_%s_%d" % (FAKTOREN[faktor], breite), _make(faktor, breite, hoehe))
            setattr(cls, "test_%s_%d_andere_schrift" % (FAKTOREN[faktor], breite),
                    _make_ohne(faktor, breite, hoehe))
    return cls


@fuer_alle_fenster
class Ap1BreiteTest(AnsichtBreiteBasis):
    NAME = "ap1"


@fuer_alle_fenster
class Ap2BreiteTest(AnsichtBreiteBasis):
    NAME = "ap2"


@fuer_alle_fenster
class TestprojektBreiteTest(AnsichtBreiteBasis):
    NAME = "testprojekt"


@fuer_alle_fenster
class AbschlussprojektBreiteTest(AnsichtBreiteBasis):
    NAME = "abschlussprojekt"


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class FlowRowTest(unittest.TestCase):
    """fisi_widgets.FlowRow (ab 0.63.2, D2) ohne Ansicht."""

    def setUp(self):
        import customtkinter as ctk
        self.root = ctk.CTk()
        self.root.geometry("900x300+0+0")

    def tearDown(self):
        self.root.destroy()

    def _pump(self):
        for _ in range(6):
            self.root.update()

    def _row(self):
        import customtkinter as ctk
        import fisi_widgets as fw
        frame = ctk.CTkFrame(self.root, fg_color="transparent")
        frame.pack(fill="x")
        flow = fw.FlowRow(frame)
        buttons = []
        for text, side, padx in (("Eins", "left", 0), ("Zwei zwei", "left", 10),
                                 ("Drei drei drei", "left", (8, 0)),
                                 ("Rechts", "right", 0), ("Rechts davor", "right", (0, 8))):
            button = ctk.CTkButton(frame, text=text, width=160)
            button.pack(side=side, padx=padx)
            buttons.append(button)
        self._pump()
        return frame, flow, buttons

    def test_breit_bleibt_gepackt(self):
        frame, flow, buttons = self._row()
        before = [b.winfo_x() for b in buttons]
        self.assertFalse(flow.fit(flow.natural_width()))
        self._pump()
        self.assertEqual([b.winfo_manager() for b in buttons], ["pack"] * 5)
        self.assertEqual([b.winfo_x() for b in buttons], before)

    def test_schmal_bricht_um_und_kehrt_zurueck(self):
        frame, flow, buttons = self._row()
        before = [(b.winfo_x(), b.winfo_y()) for b in buttons]
        room = flow.natural_width() // 2
        self.assertTrue(flow.fit(room))
        self._pump()
        self.assertEqual([b.winfo_manager() for b in buttons], ["place"] * 5)
        self.assertLessEqual(frame.winfo_reqwidth(), room)
        self.assertGreater(len(set(b.winfo_y() for b in buttons)), 1)
        rects = [(b.winfo_x(), b.winfo_y(), b.winfo_width(), b.winfo_height()) for b in buttons]
        for i, (ax, ay, aw, ah) in enumerate(rects):
            for bx, by, bw, bh in rects[i + 1:]:
                self.assertFalse(ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah,
                                 "ueberlappt: %s" % (rects,))
        # Reihenfolge links -> rechts / oben -> unten bleibt
        order = sorted(range(3), key=lambda i: (rects[i][1], rects[i][0]))
        self.assertEqual(order, [0, 1, 2])
        # rechts gepackte bleiben rechtsbuendig und beisammen
        right_edge = frame.winfo_width()
        self.assertEqual(buttons[3].winfo_x() + buttons[3].winfo_width(), right_edge)
        self.assertEqual(buttons[3].winfo_y(), buttons[4].winfo_y())
        self.assertLess(buttons[4].winfo_x(), buttons[3].winfo_x())
        # wieder breit: wie vorher
        self.assertTrue(flow.fit(10 ** 4))
        self._pump()
        self.assertEqual([(b.winfo_x(), b.winfo_y()) for b in buttons], before)

    def test_neuer_text_wird_neu_verteilt(self):
        frame, flow, buttons = self._row()
        flow.fit(flow.natural_width() // 2)
        self._pump()
        buttons[0].configure(text="Ein deutlich laengerer Text", width=320)
        self._pump()
        self.assertGreaterEqual(buttons[1].winfo_x(),
                                buttons[0].winfo_x() + buttons[0].winfo_width()
                                if buttons[1].winfo_y() == buttons[0].winfo_y() else 0)


if __name__ == "__main__":
    if "--fall" in sys.argv:
        position = sys.argv.index("--fall")
        worker(float(sys.argv[position + 1]), int(sys.argv[position + 2]),
               int(sys.argv[position + 3]), sys.argv[position + 4:])
    else:
        unittest.main(verbosity=2)
