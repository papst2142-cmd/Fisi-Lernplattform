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
Z3_NORMAL_1120_BEKANNT = ("notizblock", "fortschritt", "optionen", "fortschritt_daten",
                          "pruefungstrainer")
# Nacharbeit Gegenpruefung S1c2 (L1): Pruefungstrainer, Bewertung mit den
# laengsten Kriterien (_pruefung_gezielt) - die Haken-Texte brechen bei Normal
# nicht um; auf 14b3bd4 (0.63.1) gleich, auch bei 1360. Frage an Nico/Chat.
Z3_NORMAL_1360_BEKANNT = ("pruefungstrainer",)
# Bekannte Grenze bei Z3 (Nacharbeit Gegenpruefung M1): Fortschritt mit
# gespeicherten Test-Sessions, Tabelle "Historie der Pruefungssessions" bei
# Sehr gross 1120 (Spaltenkoepfe + Datum passen nicht, ohne Text zu kuerzen).
# Offene Designfrage an Nico (Varianten mit Fotos in ergebnis_nacharbeit_gp.md).
Z3_GRENZE_BEKANNT = {("fortschritt_daten", 1.3, 1120)}


# Nacharbeit Gegenpruefung S1c2 (L2): in bekannten Faellen nur der gemessene
# Ueberstand je Zustand (px, Messung 14b3bd4/b5d12f7 bzw. Nacharbeit), nur
# die Fehlerarten "seitlich verschiebbar", "Inhalt ... breiter" und
# "... ausserhalb des sichtbaren Bereichs" (in einem ueberstehenden Zustand).
Z3_UEBERSTAND = {
    ("notizblock", 1.0, 1120): {"start": 99, "offen": 230, "musterantworten": 230},
    ("fortschritt", 1.0, 1120): {"start": 34},
    ("fortschritt_daten", 1.0, 1120): {"mit_daten": 34, "neue_zeile": 34},
    ("optionen", 1.0, 1120): {"alles_offen": 6},
    ("pruefungstrainer", 1.0, 1120): {"pruefung_bewertung": 1494,
                                      "pruefung_bewertung_laengstes": 2514},
    ("pruefungstrainer", 1.0, 1360): {"pruefung_bewertung": 1254,
                                      "pruefung_bewertung_laengstes": 2274},
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


def _normal_unveraendert(ctx):
    """Bei Normal: keine Zeile umbrochen, keine Unterschrift verschoben."""
    if ctx.faktor != 1.0:
        return
    stack = [ctx.view.inner]
    while stack:
        widget = stack.pop()
        flow = widget.__dict__.get("_fisi_flow")
        if flow is not None and flow.wrapped:
            ctx.fehler.append("%s: bei Normal umbrochen: %s" % (ctx.name, widget))
        if widget.__dict__.get("_sub_stacked"):
            ctx.fehler.append("%s: bei Normal Unterschrift verschoben: %s" % (ctx.name, widget))
        if widget.__dict__.get("_fisi_z3_umgestellt"):
            ctx.fehler.append("%s: bei Normal umgestellt: %s" % (ctx.name, widget))
        stack.extend(widget.winfo_children())


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
    gemeldet in ergebnis_nacharbeit_gp.md)."""
    if ctx.faktor == 1.0:
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


def _z3_pruefe(ctx, zustand):
    ctx.pruefe(zustand)
    _unterklassen_sichtbar(ctx, zustand)
    _tabellen_lesbar(ctx, zustand)
    _normal_unveraendert(ctx)


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
        view.exam._finish()
        ctx.pump(0.6)
        _z3_pruefe(ctx, "pruefung_ergebnis")
        view.exam.show_choice()
        _pruefung_gezielt(view, fp.KONZEPTION)
        ctx.pump(0.6)
        view.exam._submit()
        ctx.pump(0.6)
        _z3_pruefe(ctx, "pruefung_bewertung_laengstes")
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
    ctx.pump(0.3)


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


def worker(faktor, breite, hoehe, namen):
    """Laeuft im eigenen Prozess; gibt eine JSON-Zeile "ERG {...}" aus."""
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


def ergebnis(faktor, breite, hoehe):
    """Alle angemeldeten Ansichten fuer eine Schriftgroesse und ein Fenster
    (ein Prozess, Ergebnis zwischengespeichert)."""
    key = (faktor, breite, hoehe)
    if key not in _ERGEBNISSE:
        done = subprocess.run([sys.executable, os.path.abspath(__file__), "--fall",
                               str(faktor), str(breite), str(hoehe)] + list(ANSICHTEN),
                              capture_output=True, text=True, timeout=900, cwd=HERE)
        lines = [line for line in done.stdout.splitlines() if line.startswith("ERG ")]
        _ERGEBNISSE[key] = (json.loads(lines[-1][4:]) if lines else
                            "kein Ergebnis:\n%s\n%s" % (done.stdout[-2000:], done.stderr[-4000:]))
    return _ERGEBNISSE[key]


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class AnsichtBreiteBasis(unittest.TestCase):
    """Basis: Unterklassen setzen NAME (Schluessel in ANSICHTEN)."""

    NAME = None

    def run_case(self, faktor, breite, hoehe):
        if self.NAME is None:
            self.skipTest("Basisklasse")
        result = ergebnis(faktor, breite, hoehe)
        self.assertIsInstance(result, dict, result)
        mine = result[self.NAME]
        print("\n  %s %s %dx%d: %s" % (self.NAME, Z3_STUFEN[faktor], breite, hoehe,
                                      {k: v["inhalt"] for k, v in mine["werte"].items()}))
        if getattr(self, "_bekannt", False):
            # Bekannte Luecke Normal 1120 (cfb32a9): nur Ueberstand erlaubt, aber
            # nichts darf bei Normal umgestellt sein (faengt eine fehlende Normal-Sperre).
            normal = [f for f in mine["fehler"] if "bei Normal" in f]
            self.assertEqual(normal, [], "%s Normal %dx%d umgestellt" % (self.NAME, breite, hoehe))
            self.assertEqual(_bekannte_fehler(self.NAME, faktor, breite, mine["fehler"]), [],
                             "%s %s %dx%d: mehr als der bekannte Ueberstand"
                             % (self.NAME, Z3_STUFEN[faktor], breite, hoehe))
            self.assertTrue(mine["fehler"], "%s Normal %dx%d: Luecke behoben - "
                            "Z3_NORMAL_*_BEKANNT/Z3_GRENZE_BEKANNT anpassen" % (self.NAME, breite, hoehe))
        else:
            self.assertEqual(mine["fehler"], [], "%s %s %dx%d" % (self.NAME, Z3_STUFEN[faktor],
                                                                 breite, hoehe))
        self.assertTrue(mine["werte"], "keine Zustaende geprueft")


def _make(faktor, breite, hoehe, bekannt=False):
    def test(self):
        self._bekannt = bekannt
        self.run_case(faktor, breite, hoehe)
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
        worker(float(sys.argv[position + 1]), int(sys.argv[position + 2]),
               int(sys.argv[position + 3]), sys.argv[position + 4:])
    else:
        unittest.main(verbosity=2)
