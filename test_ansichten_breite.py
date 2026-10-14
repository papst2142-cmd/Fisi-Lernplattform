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
  * bei 1360 x 900 Normal bleibt die Anordnung wie bisher (zwei Spalten im
    Raster mit gleich breiten Einheiten, Kopfzeilen nicht umbrochen)

Aufbau zum Erweitern (S1c2, Z3): Jede Ansicht ist ein Eintrag in ANSICHTEN
(Name -> Pruef-Funktion, siehe @ansicht) und hat eine eigene Testklasse
(Unterklasse von AnsichtBreiteBasis mit NAME). Alle Ansichten laufen je
Schriftgroesse und Fenster in EINEM Prozess (Schriftgroesse und Skalierung
gelten ab dem Start); das Ergebnis wird fuer alle Klassen zwischengespeichert.

Gegen 14b3bd4 (0.63.1) rot (seitlicher Schieberegler in allen vier Ansichten
bei 1120 x 720, Messung Plan: +34 bis +565 px).

Ab S1c2-Nachbesserung (Weisung Antwort Meldung 41, 4): Auf GitHub fehlt
Inter, dort waehlt die App DejaVu Sans (breiter). Deshalb laeuft auch jeder
Z3-Fall zusaetzlich mit einer anderen Schrift (test_..._andere_schrift, wie
CI Welle 3b): die Standardschrift wird per fontconfig abgelehnt - im
Container DejaVu Sans statt Inter wie auf GitHub, auf GitHub eine dritte
Schrift. Geprueft wird, dass wirklich eine andere Schrift gewaehlt wurde;
alle Anforderungen und Deckel gelten unveraendert (gemessen mit Inter).
Notizblock, Fortschritt und Optionen passen ab B-4b auch bei Normal; bei
Normal darf dort nur umgestellt werden, wo die Seite ohne Anpassung zu breit
waere (Vergleich mit einem Lauf ohne Normal-Anpassung, siehe Z3_NORMAL_ANSICHTEN).

Start:  xvfb-run -a python test_ansichten_breite.py
"""

import datetime
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

FAKTOREN = {1.0: "normal"}
# Teil b (Gross/Sehr gross) folgt im eigenen Commit
STUFEN = {1.0: "normal", 1.15: "gross", 1.3: "sehr_gross"}
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
                if type(child).__name__ in BEDIEN_KLASSEN:
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


def _szenarien(ctx, key, gruppe):
    view = ctx.zeige(key)
    ctx.pruefe("start")
    view.toggle_solution()
    ctx.pruefe("loesung")
    view.next_scenario()
    ctx.pump(0.4)
    ctx.pruefe("naechstes")
    if ctx.breit():
        detail = view.task_card.master
        layout = detail.master
        _zwei_spalten_wie_bisher(ctx, layout, layout.grid_slaves(row=0, column=0)[0],
                                 detail, gruppe)


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
    if ctx.breit():
        detail = view.task_card.master
        layout = detail.master
        _zwei_spalten_wie_bisher(ctx, layout, layout.grid_slaves(row=0, column=0)[0],
                                 detail, "proj")


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


# ---------------------------------------------------------------------------
#  Ab 0.63.2 (Z3, S1c2): die fuenf weiteren Ansichten bei Gross/Sehr gross
# ---------------------------------------------------------------------------
#
# Notizblock, Fortschritt, Karteikarten, Pruefungstrainer (Uebung und
# Pruefung) und Optionen (alle Bereiche aufgeklappt). Geprueft wird jede
# Schriftstufe; bei Normal muss die Ansicht genau wie bisher bleiben (keine
# umbrochene Zeile, keine verschobene Unterschrift - Normal ist nicht Teil
# von Z3; Pixelvergleich der Fotos im Bericht).

Z3_STUFEN = {1.0: "normal", 1.15: "gross", 1.3: "sehr_gross"}
# Normal 1120: Notizblock (+99 px) und Fortschritt (+34 px) waren schon in
# 0.63.1 zu breit (Messung Plan S1), die Optionen mit allen Bereichen
# aufgeklappt ebenso (+6 px, Messung S1c2). Normal gehoert nicht zu Z3 und
# bleibt unveraendert (Weisung Hauptstrang) - deshalb dort erwarteter
# Fehlschlag, gemeldet in bau_0.63.2/s1c2/ergebnis.md.
# Pruefungstrainer (Bewertung) ab B-4b nicht mehr: Kriterien brechen auch bei
# Normal um (Weisung Antwort Meldung 36, 3), Deckel 0 bei 1120 und 1360.
# S1c2-Nachbesserung (B-4b Rest, Weisung 32 2.2 / Weisung 41 4): Notizblock,
# Fortschritt und Optionen brechen bei Normal 1120 jetzt auch um - keine
# bekannten Faelle mehr, Deckel 0 (vorher 99/230, 34, 6).
Z3_NORMAL_1120_BEKANNT = ()
# Nacharbeit Gegenpruefung S1c2 (L1) hatte hier den Pruefungstrainer (Bewertung
# mit den laengsten Kriterien, schon auf 14b3bd4 zu breit); mit B-4b behoben,
# die Lockerung N-L2 ist zurueckgenommen.
Z3_NORMAL_1360_BEKANNT = ()
# Bekannte Grenze bei Z3 (Nacharbeit Gegenpruefung M1): Fortschritt mit
# gespeicherten Test-Sessions, Tabelle "Historie der Pruefungssessions" bei
# Sehr gross 1120 (Spaltenkoepfe + Datum passen nicht, ohne Text zu kuerzen).
# Offene Designfrage an Nico (Varianten mit Fotos in ergebnis_nacharbeit_gp.md).
Z3_GRENZE_BEKANNT = {("fortschritt_daten", 1.3, 1120)}


# Nacharbeit Gegenpruefung S1c2 (L2): in bekannten Faellen nur der gemessene
# Ueberstand je Zustand (px, Messung 14b3bd4/b5d12f7 bzw. Nacharbeit), nur
# die Fehlerarten "seitlich verschiebbar", "Inhalt ... breiter" und
# "... ausserhalb des sichtbaren Bereichs" (in einem ueberstehenden Zustand).
# S1c2-Nachbesserung: die Normal-1120-Deckel (Notizblock 99/230, Fortschritt
# 34, Optionen 6) sind mit B-4b weg; der Deckel bei Sehr gross bleibt der
# mit Inter gemessene Wert, auch fuer die andere Schrift (keine Lockerung).
Z3_UEBERSTAND = {
    # N-M1: gemessen mit TESTZEIT (breitestes Datum), vorher 55 mit Uhrzeit des Laufs
    ("fortschritt_daten", 1.3, 1120): {"mit_daten": 70, "neue_zeile": 70},
}
# Gegenpruefung S1c2 Nacharbeit (N-M1): feste Uhrzeit fuer alle
# Testdaten (Zeitstempel ueber fisi_core.device_now, im worker gesetzt).
# Die Tabellen-Spalte "Datum & Uhrzeit" ist so breit wie ihr laengster Text,
# die Ziffern der Schrift (Inter) sind unterschiedlich breit; mit der echten
# Uhr schwankte der Ueberstand bei Sehr gross 1120 (gemessen +40 bis +65).
# 2026-04-04 00:00:00 ist der breiteste Text "%Y-%m-%d %H:%M:%S" des Jahres
# 2026 in allen drei Stufen (Messung ueber alle Tage und alle Uhrzeiten:
# Normal 135 px, Gross 166 px, Sehr gross 182 px; "1" ist am schmalsten,
# "0/4/6/8/9" in allen Stufen am breitesten; Tag und Monat sind immer zweistellig).
TESTZEIT = datetime.datetime(2026, 4, 4, 0, 0, 0)


_ZUSTAND = re.compile(r"^([a-z_]+)/([a-z_0-9]+): (.*)$", re.S)
_INHALT = re.compile(r"^Inhalt (\d+) px breiter als sichtbar")


def _bekannte_fehler(name, faktor, breite, fehler):
    """Fehler, die im bekannten Fall NICHT erlaubt sind (leere Liste = ok)."""
    deckel = Z3_UEBERSTAND.get((name, faktor, breite), {})
    schlecht = []
    for text in fehler:
        treffer = _ZUSTAND.match(text)
        if not treffer or treffer.group(1) != name:
            schlecht.append(text)
            continue
        zustand, rest = treffer.group(2), treffer.group(3)
        inhalt = _INHALT.match(rest)
        if zustand not in deckel:
            schlecht.append(text)
        elif inhalt:
            if int(inhalt.group(1)) > deckel[zustand]:
                schlecht.append("%s (erlaubt hoechstens %d)" % (text, deckel[zustand]))
        elif not (rest.startswith("seitlich verschiebbar")
                  or "ausserhalb des sichtbaren Bereichs" in rest):
            schlecht.append(text)
    return schlecht


def _bekannt(name, faktor, breite):
    return ((faktor == 1.0 and breite == 1120 and name in Z3_NORMAL_1120_BEKANNT)
            or (faktor == 1.0 and breite == 1360 and name in Z3_NORMAL_1360_BEKANNT)
            or (name, faktor, breite) in Z3_GRENZE_BEKANNT)


# B-4b: Zustaende, in denen bei Normal der Pruefungstrainer (nur die Bewertung,
# ExamPanel.body) nach den Z3-Regeln angepasst werden darf
B4B_ZUSTAENDE = ("pruefung_bewertung", "pruefung_bewertung_laengstes")


def _b4b_teil(ctx, zustand):
    """Teil, der bei Normal angepasst werden darf (B-4b), sonst None
    (auch die Aufgaben 2..n: Zustand mit Endung _a<n>)."""
    if ctx.name == "pruefungstrainer" and zustand and \
            re.sub(r"_a\d+$", "", zustand) in B4B_ZUSTAENDE:
        return ctx.view.exam.body
    return None


# S1c2-Nachbesserung (B-4b Rest): diese Ansichten werden auch bei Normal nach
# den Z3-Regeln angepasst (app_gui Z3_NORMAL), aber nur, wo die Seite ohne
# Anpassung zu breit waere. Geprueft im Vergleich mit einem Lauf, in dem
# Z3_NORMAL aus ist (wie 7a32651): passt dort ein Zustand, muss er hier genau
# gleich aussehen (Geometrie aller sichtbaren Teile) und nichts umgestellt sein.
Z3_NORMAL_ANSICHTEN = ("notizblock", "fortschritt", "optionen", "fortschritt_daten")


def _normal_unveraendert(ctx, zustand=None):
    """Bei Normal: keine Zeile umbrochen, keine Unterschrift verschoben.
    Ausnahme B-4b: die Bewertung im Pruefungstrainer (_b4b_teil). In den
    Z3_NORMAL_ANSICHTEN wird das sichtbar Umgestellte nur gemerkt (werte,
    Vergleich im Test mit dem Lauf ohne Normal-Anpassung; Teile in
    zugeklappten Kacheln stellt die Anpassung erst beim Aufklappen zurueck)."""
    if ctx.faktor != 1.0:
        return
    frei = _b4b_teil(ctx, zustand)
    nur_sichtbar = ctx.name in Z3_NORMAL_ANSICHTEN
    funde = []
    stack = [ctx.view.inner]
    while stack:
        widget = stack.pop()
        if widget is frei:
            continue
        if nur_sichtbar and not widget.winfo_ismapped():
            continue
        flow = widget.__dict__.get("_fisi_flow")
        if flow is not None and flow.wrapped:
            funde.append("%s: bei Normal umbrochen: %s" % (ctx.name, widget))
        if widget.__dict__.get("_sub_stacked"):
            funde.append("%s: bei Normal Unterschrift verschoben: %s" % (ctx.name, widget))
        if widget.__dict__.get("_fisi_z3_umgestellt"):
            funde.append("%s: bei Normal umgestellt: %s" % (ctx.name, widget))
        stack.extend(widget.winfo_children())
    if ctx.name in Z3_NORMAL_ANSICHTEN and zustand is not None:
        ctx.werte["%s/%s" % (ctx.name, zustand)]["umgestellt"] = funde
    else:
        ctx.fehler.extend(funde)


def _geometrie(ctx, zustand):
    """Lage und Groesse aller sichtbaren Teile der Seite (relativ zur
    Seite), als Liste in werte - fuer den Vergleich bei Normal. Gemessen,
    wenn sich nichts mehr bewegt (zwei gleiche Messungen hintereinander;
    unter Last kommen spaete Anpassungen der Umbruchbreiten sonst zu spaet)."""
    vorher = None
    for _ in range(20):
        jetzt = _geometrie_jetzt(ctx)
        if jetzt == vorher:
            break
        vorher = jetzt
        ctx.pump(0.3)
    ctx.werte["%s/%s" % (ctx.name, zustand)]["geometrie"] = jetzt


def _geometrie_jetzt(ctx):
    view = ctx.view
    ox, oy = view.inner.winfo_rootx(), view.inner.winfo_rooty()
    zeilen = []
    stack = [view.inner]
    while stack:
        widget = stack.pop()
        for child in widget.winfo_children():
            try:
                if not child.winfo_ismapped():
                    continue
                zeilen.append("%s %r %d %d %d %d" % (
                    type(child).__name__, _text(child), child.winfo_rootx() - ox,
                    child.winfo_rooty() - oy, child.winfo_width(), child.winfo_height()))
            except Exception:  # noqa: BLE001
                continue
            stack.append(child)
    return sorted(zeilen)


def _zugeklappt_unterschrift(ctx, zustand):
    """S1c2-Nachbesserung: eine zugeklappte Kachel (FoldCard), deren
    Unterschrift unter die Ueberschrift gerueckt ist, zeigt sie direkt unter
    der Ueberschrift und mit dem Abstand des Kopfes zum unteren Rand (vorher
    brach das Verschieben bei zugeklappter Kachel ab, Optionen Sehr gross 1120
    mit DejaVu Sans)."""
    import fisi_widgets
    stack = [ctx.view.inner]
    while stack:
        widget = stack.pop()
        stack.extend(widget.winfo_children())
        if not isinstance(widget, fisi_widgets.FoldCard) or widget.opened \
                or not widget._sub_stacked or not widget.winfo_ismapped():
            continue
        unten = widget._sub_below
        name = "%s/%s: %s" % (ctx.name, zustand, widget.fold_title)
        if not unten.winfo_ismapped():
            ctx.fehler.append("%s: Unterschrift nicht sichtbar" % name)
            continue
        kopf = widget.head
        luecke = unten.winfo_y() - (kopf.winfo_y() + kopf.winfo_height())
        rand = widget.winfo_height() - (unten.winfo_y() + unten.winfo_height())
        if luecke > fisi_widgets.px(2) + 1:
            ctx.fehler.append("%s: Unterschrift %d px unter der Ueberschrift" % (name, luecke))
        if rand < fisi_widgets.px(widget._head_top) - 1:
            ctx.fehler.append("%s: Unterschrift nur %d px ueber dem unteren Rand" % (name, rand))


def _unterklassen_sichtbar(ctx, zustand):
    """Ctx.pruefe erkennt Bedienelemente am genauen Klassennamen. Abgeleitete
    Klassen (z. B. eine Aufklappliste mit Rahmen aus S1b) prueft dies hier
    ueber isinstance: ganz im sichtbaren Bereich und in ihrem Rahmen."""
    import customtkinter as ctk
    view = ctx.view
    links = view.canvas.winfo_rootx()
    rechts = links + view.canvas.winfo_width()
    stack = [view.inner]
    while stack:
        widget = stack.pop()
        for child in widget.winfo_children():
            try:
                if not child.winfo_ismapped():
                    continue
            except Exception:  # noqa: BLE001
                continue
            if isinstance(child, (ctk.CTkOptionMenu, ctk.CTkEntry, ctk.CTkCheckBox,
                                  ctk.CTkSwitch, ctk.CTkTextbox)):
                if type(child).__name__ in BEDIEN_KLASSEN:
                    continue
                x, w = child.winfo_rootx(), child.winfo_width()
                master = child.master
                if x < links - 1 or x + w > rechts + 1 or \
                        x + w > master.winfo_rootx() + master.winfo_width() + 1:
                    ctx.fehler.append("%s/%s: %s ausserhalb (x %d..%d, sichtbar %d..%d)"
                                      % (ctx.name, zustand, type(child).__name__,
                                         x, x + w, links, rechts))
                continue
            stack.append(child)


def _tabellen_lesbar(ctx, zustand):
    """Nacharbeit Gegenpruefung S1c2 (M1/L3): in jeder sichtbaren Tabelle
    (ttk.Treeview) passt jeder Spaltenkopf und jeder Zelltext in seine
    Spalte - nichts ist abgeschnitten. Nur Gross/Sehr gross (Z3); Normal
    bleibt wie 0.63.1 (dort ist "Pruefung" mit langem Namen schon zu schmal,
    gemeldet in ergebnis_nacharbeit_gp.md) - ausser die Ansicht wird bei
    Normal angepasst (B-4b Rest, Z3_NORMAL)."""
    if ctx.faktor == 1.0 and not ctx.view.__dict__.get("_z3_normal_on"):
        return
    from tkinter import ttk
    import tkinter.font as tkfont
    stack = [ctx.view.inner]
    while stack:
        widget = stack.pop()
        stack.extend(widget.winfo_children())
        if not isinstance(widget, ttk.Treeview) or not widget.winfo_ismapped():
            continue
        style = widget.cget("style") or "Treeview"
        lookup = ttk.Style().lookup
        head = tkfont.Font(font=lookup(style + ".Heading", "font") or "TkHeadingFont")
        body = tkfont.Font(font=lookup(style, "font") or "TkDefaultFont")
        spalten = widget["displaycolumns"]
        if spalten in ("#all", ("#all",)):
            spalten = widget["columns"]
        for key in spalten:
            breite = int(widget.column(key, "width"))
            texte = [(head, widget.heading(key, "text"))]
            texte += [(body, widget.set(item, key)) for item in widget.get_children()]
            for font, text in texte:
                if font.measure(text) > breite:
                    ctx.fehler.append("%s/%s: Tabellentext abgeschnitten %r (%d > Spalte %d)"
                                      % (ctx.name, zustand, text, font.measure(text), breite))


def px_tol(widget):
    """Spielraum fuer Innenraender (Haken-Text, 8 logische px)."""
    import fisi_widgets
    return fisi_widgets.px(8)


def _haken_nur_wo_noetig(ctx, zustand):
    """B-4b (Normal, Bewertung): ein Haken-Text bricht nur um, wenn er
    laenger ist als seine Umbruchbreite, nutzt dann den Platz im Rahmen und
    steht auf mindestens zwei Zeilen. Gezaehlt werden die umbrochenen Haken (werte)."""
    teil = _b4b_teil(ctx, zustand)
    if ctx.faktor != 1.0 or teil is None:
        return
    import customtkinter as ctk
    import tkinter.font as tkfont
    umbrochen = 0
    stack = [teil]
    while stack:
        widget = stack.pop()
        stack.extend(widget.winfo_children())
        if not isinstance(widget, ctk.CTkCheckBox):
            continue
        label = widget._text_label
        text = label.cget("text")
        wrap = int(float(str(label.cget("wraplength") or 0)))
        if wrap:
            # Breite des Textes ohne Umbruch, wie Tk sie zeichnet (ohne Innenrand);
            # die Messung per Schriftart ist schmaler als Tk
            label.configure(wraplength=0)
            voll = label.winfo_reqwidth() - 2 * sum(
                int(float(label.cget(name))) for name in ("padx", "borderwidth",
                                                          "highlightthickness"))
            label.configure(wraplength=wrap)
            umbrochen += 1
            if voll <= wrap:
                ctx.fehler.append("%s/%s: Haken umbrochen, obwohl er passt (%d <= %d): %r"
                                  % (ctx.name, zustand, voll, wrap, text[:40]))
            # die Umbruchbreite nutzt den Platz im Rahmen (nicht unnoetig schmal)
            platz = widget.master.winfo_width() - widget.winfo_x()
            genutzt = widget.winfo_reqwidth() - label.winfo_reqwidth() + wrap
            if genutzt < platz - px_tol(widget):
                ctx.fehler.append("%s/%s: Haken schmaler umbrochen als Platz ist (%d < %d): %r"
                                  % (ctx.name, zustand, genutzt, platz, text[:40]))
            zeilen = max(1, round(label.winfo_reqheight()
                                  / tkfont.Font(font=label.cget("font")).metrics("linespace")))
            if zeilen < 2:
                ctx.fehler.append("%s/%s: Haken mit Umbruch in einer Zeile: %r"
                                  % (ctx.name, zustand, text[:40]))
    ctx.werte["%s/%s" % (ctx.name, zustand)]["haken_umbrochen"] = umbrochen


def _haken_erste_zeile(ctx, zustand):
    """Nico, Meldung 39 Frage 2c: Bewertungskriterium umbrochen -> das
    Kaestchen steht auf der Hoehe der ersten Textzeile (Mitte Kaestchen =
    Mitte erste Zeile, 2 px Spielraum), nicht mittig zum ganzen Text."""
    import customtkinter as ctk
    stack = [ctx.view.inner]
    while stack:
        widget = stack.pop()
        stack.extend(widget.winfo_children())
        if (not isinstance(widget, ctk.CTkCheckBox) or not widget.winfo_ismapped()
                or not widget.__dict__.get("_fisi_z3_erste_zeile")):
            continue
        label, box = widget._text_label, widget._canvas
        # Zeilenhoehe wie das Label sie zeichnet (Probezeile)
        import tkinter
        probe = tkinter.Label(widget, font=label.cget("font"), text="Ag",
                              pady=0, bd=0, highlightthickness=0)
        line = probe.winfo_reqheight()
        probe.destroy()
        inset = (int(label.cget("pady")) + int(label.cget("bd"))
                 + int(label.cget("highlightthickness")))
        text_hoch = label.winfo_height() - 2 * inset
        zeilen = int(round(text_hoch / float(line)))
        if zeilen < 2:
            continue
        ctx.werte.setdefault("%s/%s" % (ctx.name, zustand), {}).setdefault("haken_mehrzeilig", 0)
        ctx.werte["%s/%s" % (ctx.name, zustand)]["haken_mehrzeilig"] += 1
        # Text steht im Label mittig: oberer Rand des Textblocks
        oben = label.winfo_rooty() + (label.winfo_height() - zeilen * line) / 2.0
        erste = oben + line / 2.0
        mitte = box.winfo_rooty() + box.winfo_height() / 2.0
        if abs(mitte - erste) > 2:
            ctx.fehler.append("%s/%s: Kaestchen nicht an der ersten Zeile (%d Zeilen, "
                              "Kaestchen-Mitte %.1f, erste Zeile %.1f): %r"
                              % (ctx.name, zustand, zeilen, mitte - label.winfo_rooty(),
                                 erste - label.winfo_rooty(), label.cget("text")[:50]))
    if (ctx.name == "pruefungstrainer" and zustand == "pruefung_bewertung_laengstes"
            and not ctx.werte.get("%s/%s" % (ctx.name, zustand), {}).get("haken_mehrzeilig")):
        ctx.fehler.append("%s/%s: kein umbrochenes Kriterium - Pruefung der ersten Zeile "
                          "laeuft ins Leere" % (ctx.name, zustand))


def _spalte_erfolgsquote(ctx, zustand):
    """Nico, Meldung 39 Frage 1a (Variante B): "Erfolgsquote" in der
    Historie der Pruefungssessions faellt nur bei "Sehr gross" weg (und nur,
    wenn die Tabelle sonst nicht passt); bei Normal und Gross bleibt sie."""
    tree = getattr(ctx.view, "tree", None)
    if ctx.name not in ("fortschritt", "fortschritt_daten") or tree is None:
        return
    spalten = tree["displaycolumns"]
    if spalten in ("#all", ("#all",)):
        spalten = tree["columns"]
    weg = "prozent" not in spalten
    ctx.werte.setdefault("%s/%s" % (ctx.name, zustand), {})["erfolgsquote_weg"] = weg
    if weg and ctx.faktor != 1.3:
        ctx.fehler.append("%s/%s: Spalte Erfolgsquote fehlt bei Faktor %s"
                          % (ctx.name, zustand, ctx.faktor))


def _z3_pruefe(ctx, zustand):
    ctx.pruefe(zustand)
    _haken_erste_zeile(ctx, zustand)
    _spalte_erfolgsquote(ctx, zustand)
    _unterklassen_sichtbar(ctx, zustand)
    _tabellen_lesbar(ctx, zustand)
    _normal_unveraendert(ctx, zustand)
    _haken_nur_wo_noetig(ctx, zustand)
    _zugeklappt_unterschrift(ctx, zustand)
    if ctx.faktor == 1.0 and ctx.name in Z3_NORMAL_ANSICHTEN:
        _geometrie(ctx, zustand)


@ansicht("notizblock")
def pruefe_notizblock(ctx):
    import fisi_core
    view = ctx.zeige("notebook")
    _z3_pruefe(ctx, "start")
    # Status "Offen": Liste mit Eintraegen und Uebungsknoepfen
    view.status_pills.select_value(fisi_core.Q_OPEN)
    ctx.pump(0.6)
    _z3_pruefe(ctx, "offen")
    view.answer_pills.select_value("an")
    ctx.pump(0.6)
    _z3_pruefe(ctx, "musterantworten")
    view.answer_pills.select_value("aus")
    view.status_pills.select_value(fisi_core.Q_PRACTICE)
    ctx.pump(0.3)


@ansicht("fortschritt")
def pruefe_fortschritt(ctx):
    ctx.zeige("progress")
    ctx.pump(1.0)    # Rahmenplan-Karte kommt nach dem ersten Zeichnen
    _z3_pruefe(ctx, "start")


@ansicht("karteikarten")
def pruefe_karteikarten(ctx):
    view = ctx.zeige("cards")
    _z3_pruefe(ctx, "freitext")
    view.txt_answer.insert("1.0", "Eine Antwort")
    view.check_answer()
    ctx.pump(0.4)
    _z3_pruefe(ctx, "freitext_geprueft")
    view.next_card()
    view.set_mode("mc")
    ctx.pump(0.4)
    _z3_pruefe(ctx, "mc")
    view.options.select(view.options._rows[0]["text"])
    view.check_answer()
    ctx.pump(0.4)
    _z3_pruefe(ctx, "mc_geprueft")
    view.set_mode("reveal")
    ctx.pump(0.3)
    view.check_answer()
    ctx.pump(0.4)
    _z3_pruefe(ctx, "aufgedeckt")
    view.set_mode("freitext")
    ctx.pump(0.3)


def _laengstes_kriterium(quelle, index):
    import fisi_pruefung as fp
    teile = fp.scenario_parts(fp.source_data(quelle)[index])["teile"]
    return max(len(k) for teil in teile for k in teil["kriterien"])


def _pruefung_gezielt(view, art):
    """Pruefung ohne Zufall (Nacharbeit Gegenpruefung S1c2, L1): je Thema
    die Aufgabe mit dem laengsten Bewertungskriterium (Haken-Text); bei
    Konzeption (Themen aus dem Pool) steht die Aufgabe mit dem laengsten
    Kriterium aller AP2-Aufgaben vorn. Startet wie view.exam.start(art),
    nur ohne Rueckfrage und ohne Zufall."""
    import fisi_pruefung as fp
    state = fp.new_exam(art, seed=0)
    aufgaben, genommen = [], set()
    for aufgabe in state["aufgaben"]:
        quelle = aufgabe["quelle"]
        thema = fp.source_data(quelle)[aufgabe["index"]]["theme"]
        frei = [i for i in fp.usable_indices(quelle, thema) if i not in genommen]
        beste = max(frei, key=lambda i: (_laengstes_kriterium(quelle, i), -i))
        genommen.add(beste)
        aufgaben.append({"quelle": quelle, "index": beste})
    if fp.EXAM[art]["themen"] == "4ausPool":
        quelle = fp.EXAM[art]["quelle"]
        alle = [i for thema in fp.EXAM[art]["pool"] for i in fp.usable_indices(quelle, thema)]
        beste = max(alle, key=lambda i: (_laengstes_kriterium(quelle, i), -i))
        aufgaben = [{"quelle": quelle, "index": beste}] + \
            [a for a in aufgaben if a["index"] != beste][:len(aufgaben) - 1]
    state["aufgaben"] = aufgaben
    view.exam.state = state
    view.exam.task_no = 0
    view.exam.wiso_page = 0
    view.exam.show_running()


def _bewertung_aufgaben(ctx, view, zustand):
    """B-4b: Bewertung der Aufgaben 2..n (Zustand <zustand>_a<n>), danach
    wieder Aufgabe 1."""
    for nummer in range(1, len(view.exam.state["aufgaben"])):
        view.exam._grade_task(nummer)
        ctx.pump(0.6)
        _z3_pruefe(ctx, "%s_a%d" % (zustand, nummer + 1))
    view.exam._grade_task(0)
    ctx.pump(0.3)


@ansicht("pruefungstrainer")
def pruefe_pruefungstrainer(ctx):
    import app_gui
    import random
    import fisi_pruefung as fp
    random.seed(6302)    # Uebungsfragen und WiSo fest; Bewertung gezielt (_pruefung_gezielt)
    view = ctx.zeige("quiz")
    _z3_pruefe(ctx, "start")
    view.start_quiz()
    ctx.pump(0.4)
    _z3_pruefe(ctx, "frage")
    view.options.select(view.options._rows[0]["text"])
    view.submit_answer()
    ctx.pump(0.4)
    _z3_pruefe(ctx, "beantwortet")
    ja = app_gui.messagebox.askyesno
    app_gui.messagebox.askyesno = lambda *a, **k: True
    try:
        view.cancel_quiz()
        view.mode_pills.select_value("pruefung")
        ctx.pump(0.6)
        _z3_pruefe(ctx, "pruefung_auswahl")
        _pruefung_gezielt(view, fp.AP1)
        ctx.pump(0.6)
        _z3_pruefe(ctx, "pruefung_laeuft")
        view.exam._submit()
        ctx.pump(0.6)
        _z3_pruefe(ctx, "pruefung_bewertung")
        # B-4b: auch die uebrigen Aufgaben (je Thema das laengste Kriterium)
        _bewertung_aufgaben(ctx, view, "pruefung_bewertung")
        view.exam._finish()
        ctx.pump(0.6)
        _z3_pruefe(ctx, "pruefung_ergebnis")
        view.exam.show_choice()
        _pruefung_gezielt(view, fp.KONZEPTION)
        ctx.pump(0.6)
        view.exam._submit()
        ctx.pump(0.6)
        _z3_pruefe(ctx, "pruefung_bewertung_laengstes")
        _bewertung_aufgaben(ctx, view, "pruefung_bewertung_laengstes")
        view.exam.cancel()
        ctx.pump(0.4)
        view.exam.show_choice()
        view.exam.start(fp.WISO)
        ctx.pump(0.6)
        _z3_pruefe(ctx, "pruefung_wiso")
        view.exam.cancel()
        ctx.pump(0.4)
        _z3_pruefe(ctx, "pruefung_historie")
        view.mode_pills.select_value("uebung")
        ctx.pump(0.3)
    finally:
        app_gui.messagebox.askyesno = ja


@ansicht("optionen")
def pruefe_optionen(ctx):
    view = ctx.zeige("settings")
    _z3_pruefe(ctx, "start")
    for card in view.folds.values():
        card.set_opened(True)
        ctx.pump(0.2)
    ctx.pump(0.8)
    _z3_pruefe(ctx, "alles_offen")
    for card in view.folds.values():
        card.set_opened(False)
    ctx.pump(0.8)
    # S1c2-Nachbesserung: wieder zugeklappt (verschobene Unterschriften)
    _z3_pruefe(ctx, "wieder_zu")


@ansicht("fortschritt_daten")
def pruefe_fortschritt_daten(ctx):
    """Fortschritt MIT gespeicherten Klausursimulationen und Test-Sessions
    (Gegenpruefung S1c2, M1): je Pruefungsart eine Simulation, darunter der
    laengste Name ("AP2 · Konzeption und Administration von IT-Systemen"),
    laengste Note und Dauer. Steht als letzte Ansicht, damit die anderen
    Ansichten weiter mit leerer Datenbank laufen."""
    import fisi_pruefung as fp
    view = ctx.zeige("progress")
    ctx.pump(1.0)
    db = ctx.app.db
    for art in fp.EXAM:
        db.save_exam(art, 55.5, "3 (Befriedigend)", 5999, {})
    for _ in range(3):
        db.save_test_result(37, 40, 92.5, "3 (Befriedigend)", 5999)
    view.refresh()      # wie "Aktualisieren": neue Zeilen nach dem ersten Anpassen
    ctx.pump(1.0)
    _z3_pruefe(ctx, "mit_daten")
    # noch eine Simulation: neue Zeile, sonst aendert sich keine Groesse -
    # nur das Neuanpassen nach refresh (Z3_REFIT) passt sie an
    db.save_exam(fp.KONZEPTION, 55.5, "3 (Befriedigend)", 5999, {})
    view.refresh()
    ctx.pump(1.0)
    _z3_pruefe(ctx, "neue_zeile")


def worker(faktor, breite, hoehe, namen, z3_aus=False):
    """Laeuft im eigenen Prozess; gibt eine JSON-Zeile "ERG {...}" aus.
    z3_aus: Ansichten ohne Anpassung bei Normal (Z3_NORMAL aus, wie 7a32651)."""
    home = tempfile.mkdtemp(prefix="fisi_ansichten_")
    os.environ.update(HOME=home, APPDATA=home, FISI_DB_PATH=os.path.join(home, "t.db"),
                      FISI_SELFTEST=os.path.join(home, "log.txt"))
    import customtkinter as ctk
    import app_gui
    import fisi_theme
    import fisi_widgets
    import fisi_core
    # feste Uhrzeit der Testdaten (TESTZEIT, N-M1): Ergebnis unabhaengig vom Testlauf
    fisi_core.device_now = lambda: TESTZEIT.astimezone()
    fisi_theme.apply_font_size(STUFEN[faktor])
    fisi_widgets.apply_ui_scale(faktor)
    app_gui.UpdateController.auto_check = lambda self: None
    app_gui.SyncController.auto_start = lambda self: None
    if z3_aus:
        for klasse in vars(app_gui).values():
            if isinstance(klasse, type) and "Z3_NORMAL" in vars(klasse):
                klasse.Z3_NORMAL = False
    import random
    random.seed(6301)    # Kartenauswahl fest: Laeufe mit und ohne Anpassung vergleichbar
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


_LAUFEND = {}


def _starte(faktor, breite, hoehe, ohne, z3_aus):
    """Startet den Prozess fuer einen Fall (noch nicht abgewartet)."""
    key = (faktor, breite, hoehe, ohne, z3_aus)
    if key in _ERGEBNISSE or key in _LAUFEND:
        return
    # gleicher Ablauf in beiden Laeufen (Vergleich mit z3_aus): feste
    # Hash-Reihenfolge und dieselben vorangehenden Ansichten
    env = dict(os.environ, PYTHONHASHSEED="0")
    if ohne:
        env["FONTCONFIG_FILE"] = _fc_ohne(ohne)
    namen = list(ANSICHTEN)
    # Ausgaben in Dateien: ein Rohr koennte volllaufen, solange der andere
    # Prozess abgewartet wird
    out, err = tempfile.TemporaryFile("w+"), tempfile.TemporaryFile("w+")
    lauf = subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), "--fall", str(faktor), str(breite), str(hoehe)]
        + (["--z3-aus"] if z3_aus else []) + namen,
        stdout=out, stderr=err, text=True, cwd=HERE, env=env)
    _LAUFEND[key] = (lauf, out, err)


def ergebnis(faktor, breite, hoehe, ohne=None, z3_aus=False):
    """Alle angemeldeten Ansichten fuer eine Schriftgroesse und ein Fenster
    (ein Prozess, Ergebnis zwischengespeichert); ohne = abgelehnte Schrift;
    z3_aus: dieselben Ansichten, aber ohne Anpassung bei Normal. Bei Normal
    laeuft der Vergleichslauf z3_aus gleichzeitig mit (CI-Laufzeit)."""
    key = (faktor, breite, hoehe, ohne, z3_aus)
    if key not in _ERGEBNISSE:
        _starte(faktor, breite, hoehe, ohne, z3_aus)
        if faktor == 1.0 and not z3_aus:
            _starte(faktor, breite, hoehe, ohne, True)
        lauf, out_datei, err_datei = _LAUFEND.pop(key)
        try:
            lauf.wait(timeout=900)
        except subprocess.TimeoutExpired:
            lauf.kill()
            lauf.wait()
        out_datei.seek(0)
        err_datei.seek(0)
        out, err = out_datei.read(), err_datei.read()
        out_datei.close()
        err_datei.close()
        lines = [line for line in out.splitlines() if line.startswith("ERG ")]
        _ERGEBNISSE[key] = (json.loads(lines[-1][4:]) if lines else
                            "kein Ergebnis:\n%s\n%s" % (out[-2000:], err[-4000:]))
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
        print("\n  %s %s %dx%d (%s): %s" % (self.NAME, Z3_STUFEN[faktor], breite, hoehe,
                                           mine["schrift"],
                                           {k: v["inhalt"] for k, v in mine["werte"].items()}))
        if faktor == 1.0 and self.NAME in Z3_NORMAL_ANSICHTEN:
            self._nur_wo_noetig(faktor, breite, hoehe, ohne, mine)
        if getattr(self, "_bekannt", False):
            # Bekannte Luecke Normal 1120 (cfb32a9): nur Ueberstand erlaubt, aber
            # nichts darf bei Normal umgestellt sein (faengt eine fehlende Normal-Sperre).
            normal = [f for f in mine["fehler"] if "bei Normal" in f]
            self.assertEqual(normal, [], "%s Normal %dx%d umgestellt" % (self.NAME, breite, hoehe))
            self.assertEqual(_bekannte_fehler(self.NAME, faktor, breite, mine["fehler"]), [],
                             "%s %s %dx%d: mehr als der bekannte Ueberstand"
                             % (self.NAME, Z3_STUFEN[faktor], breite, hoehe))
            if ohne is None:
                # Erinnerung an die Liste nur mit der Standardschrift: mit
                # einer anderen Schrift kann der bekannte Ueberstand fehlen
                # (GitHub, dritte Schrift: Fortschritt mit Daten passt dort)
                self.assertTrue(mine["fehler"], "%s %s %dx%d: Luecke behoben - "
                                "Z3_NORMAL_*_BEKANNT/Z3_GRENZE_BEKANNT anpassen"
                                % (self.NAME, Z3_STUFEN[faktor], breite, hoehe))
        else:
            self.assertEqual(mine["fehler"], [], "%s %s %dx%d (Schrift %s)"
                             % (self.NAME, Z3_STUFEN[faktor], breite, hoehe, mine["schrift"]))
        self.assertTrue(mine["werte"], "keine Zustaende geprueft")
        return mine

    def _nur_wo_noetig(self, faktor, breite, hoehe, ohne, mine):
        """B-4b Rest (Z3_NORMAL_ANSICHTEN): bei Normal nur umgestellt, wo die
        Seite ohne Anpassung zu breit waere. Vergleich je Zustand mit dem
        Lauf ohne Normal-Anpassung (gleiche Schrift): passt der Zustand dort,
        ist hier nichts umgestellt und jedes sichtbare Teil liegt gleich."""
        aus = ergebnis(faktor, breite, hoehe, ohne, z3_aus=True)
        self.assertIsInstance(aus, dict, aus)
        aus = aus[self.NAME]
        self.assertEqual(aus["schrift"], mine["schrift"])
        for zustand, wert in mine["werte"].items():
            vorher = aus["werte"][zustand]
            if vorher["inhalt"] > vorher["sichtbar"]:
                continue        # ohne Anpassung zu breit: Umstellen erlaubt
            self.assertEqual(wert["umgestellt"], [], "%s %dx%d (%s): umgestellt, obwohl "
                             "es ohne Anpassung passt" % (zustand, breite, hoehe, mine["schrift"]))
            anders = sorted(set(wert["geometrie"]) ^ set(vorher["geometrie"]))
            self.assertEqual(wert["geometrie"], vorher["geometrie"],
                             "%s %dx%d (%s): anders als ohne Anpassung, obwohl es passt "
                             "(ohne/mit: %s)" % (zustand, breite, hoehe, mine["schrift"],
                                                 [("ohne" if z in vorher["geometrie"] else "mit", z)
                                                  for z in anders][:12]))


def _make(faktor, breite, hoehe, bekannt=False):
    def test(self):
        self._bekannt = bekannt
        self.run_case(faktor, breite, hoehe)
    return test


def _make_ohne(faktor, breite, hoehe, bekannt=False):
    """Derselbe Fall mit abgelehnter Standardschrift (andere Schriftmetrik,
    Muster CI Welle 3b); bekannte Faelle mit denselben Deckeln."""
    def test(self):
        if self.NAME is None:
            self.skipTest("Basisklasse")
        self._bekannt = bekannt
        standard = ergebnis(faktor, breite, hoehe)
        self.assertIsInstance(standard, dict, standard)
        family = standard[self.NAME]["schrift"]
        mine = self.run_case(faktor, breite, hoehe, ohne=family)
        self.assertNotEqual(mine["schrift"], family, "Schrift nicht gewechselt")
    return test


def fuer_alle_fenster(cls):
    """Klassen-Dekorator: je Schriftgroesse und Fenster ein Testfall."""
    for faktor in FAKTOREN:
        for breite, hoehe in FENSTER:
            setattr(cls, "test_%s_%d" % (FAKTOREN[faktor], breite), _make(faktor, breite, hoehe))
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


def fuer_alle_stufen(cls):
    """Z3: je Schriftstufe (Normal, Gross, Sehr gross) und Fenster ein
    Testfall. Bekannte Faelle (_bekannt): nur Ueberstand erlaubt, bei Normal nichts umgestellt."""
    for faktor, stufe in Z3_STUFEN.items():
        for breite, hoehe in FENSTER:
            bekannt = _bekannt(cls.NAME, faktor, breite)
            test = _make(faktor, breite, hoehe, bekannt)
            setattr(cls, "test_%s_%d" % (stufe, breite), test)
            setattr(cls, "test_%s_%d_andere_schrift" % (stufe, breite),
                    _make_ohne(faktor, breite, hoehe, bekannt))
    return cls


@fuer_alle_stufen
class NotizblockBreiteTest(AnsichtBreiteBasis):
    NAME = "notizblock"


@fuer_alle_stufen
class FortschrittBreiteTest(AnsichtBreiteBasis):
    NAME = "fortschritt"


@fuer_alle_stufen
class KarteikartenBreiteTest(AnsichtBreiteBasis):
    NAME = "karteikarten"


@fuer_alle_stufen
class PruefungstrainerBreiteTest(AnsichtBreiteBasis):
    NAME = "pruefungstrainer"


@fuer_alle_stufen
class OptionenBreiteTest(AnsichtBreiteBasis):
    NAME = "optionen"


@fuer_alle_stufen
class FortschrittDatenBreiteTest(AnsichtBreiteBasis):
    NAME = "fortschritt_daten"


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
        namen = sys.argv[position + 4:]
        z3_aus = "--z3-aus" in namen
        worker(float(sys.argv[position + 1]), int(sys.argv[position + 2]),
               int(sys.argv[position + 3]), [n for n in namen if n != "--z3-aus"], z3_aus)
    else:
        unittest.main(verbosity=2)
