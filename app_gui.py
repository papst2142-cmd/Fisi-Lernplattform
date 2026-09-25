#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FISI Lernplattform - Dashboard Edition
======================================

Lernprogramm fuer die Umschulung zum Fachinformatiker Systemintegration.

Start:      python3 app_gui.py
Benoetigt:  Python 3.8 oder neuer mit Tkinter, dazu CustomTkinter und Pillow
            (pip install -r requirements.txt)

Die Oberflaeche besteht aus einer festen Seitenleiste, einer Kopfzeile mit
Suche und einem Inhaltsbereich, in dem die einzelnen Ansichten umgeschaltet
werden. Alle Lernaktivitaeten werden in einer lokalen SQLite-Datenbank
protokolliert und im Dashboard ausgewertet.
"""

import os
import random
import sys
import time
import traceback
import tkinter as tk
from tkinter import ttk, messagebox

import customtkinter as ctk
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fisi_core import (  # noqa: E402
    AP1_SZENARIEN, AP1_THEMES, AP2_THEMES, CALC_EXPLAIN_RAID,
    CALC_EXPLAIN_SCREEN, CALC_EXPLAIN_SUBNET, CATEGORIES, CATEGORY_SHORT,
    COLOR_DEPTHS, DBManager, InputError, KARTEIKARTEN, PROJEKTARBEITEN,
    QUIZ_QUESTIONS, RAID_LEVELS, SZENARIEN,
    ap1_theme_totals, content_totals, ihk_note, raid_report, screen_report,
    search_content, subnet_report, theme_totals,
)
from fisi_theme import C, CATEGORY_COLOR, GRADIENTS, THEME_COLOR, mix  # noqa: E402
from fisi_widgets import (  # noqa: E402
    Card, CalendarPanel, GradientBar, GradientPanel, Heatmap, IconButton,
    IconCanvas, LineChart, MiniRing, NeoButton, OptionList, RingStat,
    ScrollArea, ThemeTimeline, F,
    circle_image, ctk_image, make_autogrow_text, make_label, make_text, px,
    ring_image, rounded_gradient, set_text, setup_fonts, tk_font, tk_photo,
)

APP_TITLE = "FISI Lernplattform"
# Solange es keine Vollversion (1.0) gibt, wird hier nur die Zahl hinter dem
# Punkt bei jedem Update erhoeht (0.17 -> 0.18 -> 0.19 -> ...).
APP_VERSION = "0.21"


def _resource_path(filename):
    """Pfad zu einer mitgelieferten Ressourcendatei (z.B. icon.ico). Findet
    sie sowohl beim Start aus dem Quellcode als auch in der mit PyInstaller
    gebauten .exe, wo Ressourcen in einem temporaeren Ordner (sys._MEIPASS)
    liegen."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, filename)

NAV_ITEMS = [
    ("dashboard", "grid", "Dashboard", None),
    ("cards", "cards", "Karteikarten", CATEGORIES),
    ("quiz", "target", "Prüfungstrainer", None),
    ("ap1scenarios", "layers", "AP1 Szenarien", None),
    ("scenarios", "diamond", "AP2 Szenarien", None),
    ("testproject", "flag", "Test Projekt", None),
    ("calc", "calc", "Praxis-Rechner", None),
    ("progress", "chart", "Lernfortschritt", None),
    ("settings", "gear", "Einstellungen", None),
]

# Symbole der Fachbereiche im Untermenue der Seitenleiste
CATEGORY_NAV_ICON = {
    CATEGORIES[0]: "node",
    CATEGORIES[1]: "shield",
    CATEGORIES[2]: "server",
    CATEGORIES[3]: "case",
}

VIEW_TITLES = {
    "dashboard": ("DASHBOARD", "HOME"),
    "cards": ("LERNEN", "KARTEIKARTEN"),
    "quiz": ("LERNEN", "PRÜFUNGSTRAINER"),
    "ap1scenarios": ("LERNEN", "AP1 SZENARIEN"),
    "scenarios": ("LERNEN", "AP2 SZENARIEN"),
    "testproject": ("LERNEN", "TEST PROJEKT"),
    "calc": ("WERKZEUGE", "PRAXIS-RECHNER"),
    "progress": ("AUSWERTUNG", "LERNFORTSCHRITT"),
    "settings": ("SYSTEM", "EINSTELLUNGEN"),
    "search": ("SUCHE", "ERGEBNISSE"),
}


def transparent_frame(parent, **kwargs):
    """Layout-Container ohne eigene Flaeche (uebernimmt die Farbe darunter)."""
    return ctk.CTkFrame(parent, fg_color="transparent", corner_radius=0, **kwargs)


# ============================================================================
#  KLEINE EINGABEFELDER
# ============================================================================

class EntryBox(ctk.CTkEntry):
    """Dunkles, abgerundetes Eingabefeld. Hebt beim Fokus den Rahmen hervor."""

    def __init__(self, parent, width=18, value="", font=None):
        super().__init__(parent, width=width * 9 + 28, height=38,
                         corner_radius=10, border_width=1,
                         fg_color=C["card_alt"], border_color=C["border"],
                         text_color=C["text"], font=font or F["body"])
        # Aeltere Aufrufer greifen ueber .entry auf das Eingabefeld zu
        self.entry = self
        self._entry.configure(insertbackground=C["cyan"],
                              selectbackground=C["purple"], insertofftime=0)
        self.bind("<FocusIn>", lambda _e: self.configure(border_color=C["purple"]))
        self.bind("<FocusOut>", lambda _e: self.configure(border_color=C["border"]))
        if value:
            self.insert(0, value)

    def set(self, value):
        self.delete(0, "end")
        self.insert(0, str(value))


class NumberStepper(ctk.CTkFrame):
    """Zahlenfeld mit Plus- und Minus-Knopf."""

    def __init__(self, parent, value=10, minimum=1, maximum=100, step=5, bg=None):
        super().__init__(parent, fg_color="transparent")
        self.value = value
        self.minimum = minimum
        self.maximum = maximum
        self.step = step

        IconButton(self, "minus", lambda: self._change(-self.step),
                   parent_bg=bg or C["card"]).pack(side="left")
        self.label = ctk.CTkLabel(self, text=str(value), fg_color=C["card_alt"],
                                  corner_radius=10, text_color=C["text"],
                                  font=F["body_bold"], width=58, height=34)
        self.label.pack(side="left", padx=6)
        IconButton(self, "plus", lambda: self._change(self.step),
                   parent_bg=bg or C["card"]).pack(side="left")

    def _change(self, delta):
        self.value = max(self.minimum, min(self.maximum, self.value + delta))
        self.label.configure(text=str(self.value))

    def get(self):
        return self.value

    def set_maximum(self, maximum):
        self.maximum = max(1, maximum)
        self._change(0)


class PillGroup(ctk.CTkFrame):
    """Gruppe sich gegenseitig ausschliessender Auswahlknoepfe."""

    def __init__(self, parent, options, on_change=None, initial=0):
        super().__init__(parent, fg_color="transparent")
        self.on_change = on_change
        self.buttons = []
        self.values = []
        for index, (value, label) in enumerate(options):
            button = NeoButton(self, label, kind="pill", height=34,
                               font=F["small_bold"],
                               command=lambda i=index: self.select(i))
            button.pack(side="left", padx=(0, 8))
            self.buttons.append(button)
            self.values.append(value)
        self.current = initial
        self._paint()

    def _paint(self):
        for index, button in enumerate(self.buttons):
            button.set_active(index == self.current)

    def select(self, index, notify=True):
        self.current = index
        self._paint()
        if notify and self.on_change:
            self.on_change(self.values[index])

    def select_value(self, value, notify=True):
        if value in self.values:
            self.select(self.values.index(value), notify)

    def get(self):
        return self.values[self.current]


def clickable_row(parent, accent, bg=None):
    """Abgerundete Listenzeile mit farbiger Markierung links. Liefert
    (Zeile, Textbereich)."""
    row = ctk.CTkFrame(parent, fg_color=bg or C["card_alt"], corner_radius=12,
                       border_width=1, border_color=C["border"], cursor="hand2")
    marker = ctk.CTkFrame(row, fg_color=accent, width=4, height=12,
                          corner_radius=2, cursor="hand2")
    marker.pack(side="left", fill="y", padx=(10, 0), pady=11)
    inner = transparent_frame(row, cursor="hand2")
    inner.pack(side="left", fill="x", expand=True, padx=(10, 12), pady=10)
    return row, marker, inner


def bind_click(widgets, callback):
    for widget in widgets:
        widget.bind("<Button-1>", callback)


# ============================================================================
#  SEITENLEISTE
# ============================================================================

# Unsichtbarer Platzhalter fuer den Farbstreifen inaktiver Menuezeilen
BLANK_INDICATOR = Image.new("RGBA", (16, 80), (0, 0, 0, 0))


class NavRow(ctk.CTkFrame):
    """Eine abgerundete Zeile in der Seitenleiste."""

    def __init__(self, parent, icon, text, command, sub=False, expandable=False):
        super().__init__(parent, fg_color=C["sidebar"], corner_radius=10,
                         cursor="hand2")
        self.command = command
        self.active = False
        self.sub = sub

        # Senkrechter Farbverlauf links, sichtbar nur bei der aktiven Zeile
        self.indicator = ctk.CTkLabel(self, text="", width=4, height=20)
        self.indicator.pack(side="left", padx=(6, 0))

        pad_left = 20 if sub else 8
        self.icon_canvas = IconCanvas(self, icon, size=20 if sub else 22,
                                      icon_scale=0.62 if sub else 0.72,
                                      parent_bg=C["sidebar"], cursor="hand2")
        self.icon_canvas.pack(side="left", padx=(pad_left, 10), pady=8 if sub else 9)

        self.text_label = ctk.CTkLabel(self, text=text, anchor="w", height=0,
                                       text_color=C["muted"] if sub else C["text_dim"],
                                       font=F["small"] if sub else F["nav"],
                                       cursor="hand2")
        self.text_label.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.chevron = None
        self._expanded = False
        if expandable:
            self.chevron = IconCanvas(self, "chevron_down", size=16,
                                      icon_scale=0.62, parent_bg=C["sidebar"],
                                      cursor="hand2")
            self.chevron.pack(side="right", padx=(0, 12))

        for widget in self._widgets():
            widget.bind("<Button-1>", self._on_click)
            widget.bind("<Enter>", lambda _e: self._hover(True))
            widget.bind("<Leave>", lambda _e: self._hover(False))

    def _paint_chevron(self):
        if not self.chevron:
            return
        color = C["cyan"] if self.active else C["muted"]
        self.chevron.paint(color, "chevron_up" if self._expanded else "chevron_down")

    def _widgets(self):
        items = [self, self.text_label, self.icon_canvas, self.indicator]
        if self.chevron:
            items.append(self.chevron)
        return items

    def _on_click(self, _event=None):
        if self.command:
            self.command()

    def _hover(self, flag):
        if self.active:
            return
        self._apply_bg(C["card"] if flag else C["sidebar"])
        self.text_label.configure(text_color=C["text"] if flag else
                                  (C["muted"] if self.sub else C["text_dim"]))

    def _apply_bg(self, bg):
        self.configure(fg_color=bg)
        self.icon_canvas.configure(bg=bg)
        if self.chevron:
            self.chevron.configure(bg=bg)

    def set_active(self, flag):
        self.active = flag
        if flag:
            self._apply_bg(C["card_hi"])
            bar = rounded_gradient(4, 20, 2, C["cyan"], GRADIENTS["accent"][1],
                                   direction="v")
            self.indicator.configure(image=ctk_image(bar, 4, 20))
            self.text_label.configure(text_color=C["text"])
            self.icon_canvas.paint(C["cyan"])
        else:
            self._apply_bg(C["sidebar"])
            self.indicator.configure(image=ctk_image(BLANK_INDICATOR, 4, 20))
            self.text_label.configure(text_color=C["muted"] if self.sub else C["text_dim"])
            self.icon_canvas.paint(C["muted"])
        self._paint_chevron()

    def set_expanded(self, flag):
        self._expanded = bool(flag)
        self._paint_chevron()


class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=C["sidebar"], corner_radius=0, width=244)
        self.app = app
        self.pack_propagate(False)
        self.rows = {}
        self.sub_frames = {}
        self.expanded = set()

        logo = transparent_frame(self)
        logo.pack(fill="x", pady=(22, 20), padx=20)
        mark = tk.Canvas(logo, width=px(34), height=px(34), bg=C["sidebar"],
                         highlightthickness=0, bd=0)
        mark.pack(side="left")
        ring = ring_image(34, 5, 1.0, C["cyan"], C["pink"], C["ring_bg"])
        dot = circle_image(12, fill=C["pink"])
        self._logo_images = (tk_photo(ring, px(34), px(34)),
                             tk_photo(dot, px(12), px(12)))
        mark.create_image(px(17), px(17), image=self._logo_images[0])
        mark.create_image(px(17), px(17), image=self._logo_images[1])
        ctk.CTkLabel(logo, text="FISI", text_color=C["text"], font=F["logo"],
                     height=0).pack(side="left", padx=(12, 0))
        ctk.CTkLabel(logo, text="Lernplattform", text_color=C["muted"],
                     font=F["tiny"], height=0).pack(side="left", padx=(7, 0),
                                                    pady=(7, 0))

        make_label(self, "MENÜ", font=F["label"], fg=C["muted"],
                   anchor="w").pack(fill="x", padx=24, pady=(0, 6))

        for key, icon, text, sub_items in NAV_ITEMS:
            expandable = bool(sub_items)
            row = NavRow(self, icon, text,
                         command=lambda k=key: self._on_nav(k),
                         expandable=expandable)
            row.pack(fill="x", padx=12, pady=1)
            self.rows[key] = row

            if sub_items:
                container = transparent_frame(self)
                self.sub_frames[key] = container
                for item in sub_items:
                    sub_row = NavRow(container, CATEGORY_NAV_ICON.get(item, "dot"),
                                     CATEGORY_SHORT.get(item, item),
                                     command=lambda c=item: self.app.open_cards(c),
                                     sub=True)
                    sub_row.pack(fill="x", pady=1)

        self.footer = make_label(self, "Version %s" % APP_VERSION,
                                 font=F["tiny"], fg=C["muted"])
        self.footer.pack(side="bottom", pady=(8, 14))

        status = ctk.CTkFrame(self, fg_color=C["card"], corner_radius=14,
                              border_width=1, border_color=C["border"])
        status.pack(side="bottom", fill="x", padx=14)
        make_label(status, "LERNSTATUS", font=F["label"], fg=C["muted"],
                   anchor="w").pack(fill="x", padx=14, pady=(12, 0))
        self.streak_label = make_label(status, "", font=F["small_bold"],
                                       fg=C["text"], anchor="w")
        self.streak_label.pack(fill="x", padx=14, pady=(6, 0))
        self.status_bar = GradientBar(status, "Inhalte bearbeitet", C["cyan"],
                                      C["pink"], parent_bg=C["card"])
        self.status_bar.pack(fill="x", padx=14, pady=(6, 10))

    def _on_nav(self, key):
        if key in self.sub_frames:
            self._toggle(key)
        self.app.show_view(key)

    def _toggle(self, key):
        container = self.sub_frames[key]
        if key in self.expanded:
            container.pack_forget()
            self.expanded.discard(key)
            self.rows[key].set_expanded(False)
        else:
            container.pack(fill="x", padx=12, after=self.rows[key])
            self.expanded.add(key)
            self.rows[key].set_expanded(True)

    def set_active(self, key):
        for name, row in self.rows.items():
            row.set_active(name == key)

    def update_status(self, streak, learned, total):
        self.streak_label.configure(text="Lernserie: %d Tag(e)" % streak)
        self.status_bar.set(learned / max(1, total) * 100,
                            "%d / %d" % (learned, total))


# ============================================================================
#  KOPFZEILE
# ============================================================================

class Header(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=C["bg"], corner_radius=0)
        self.app = app

        left = transparent_frame(self)
        left.pack(side="left", padx=(28, 0), pady=20)
        self.crumb_main = make_label(left, "DASHBOARD", font=F["label"],
                                     fg=C["text"])
        self.crumb_main.pack(side="left")
        make_label(left, "/", font=F["label"], fg=C["muted"]).pack(side="left", padx=7)
        self.crumb_sub = make_label(left, "HOME", font=F["label"], fg=C["cyan"])
        self.crumb_sub.pack(side="left")

        self.search_box = ctk.CTkFrame(self, fg_color=C["card"], corner_radius=20,
                                       border_width=1, border_color=C["border"])
        self.search_box.pack(side="right", padx=(0, 28), pady=14)
        IconCanvas(self.search_box, "search", size=16, icon_scale=0.75,
                   color=C["muted"], parent_bg=C["card"]).pack(side="left",
                                                               padx=(14, 0))
        self.search_entry = ctk.CTkEntry(self.search_box, width=250, height=36,
                                         border_width=0, fg_color=C["card"],
                                         text_color=C["text"],
                                         placeholder_text="Suchen ...  (Strg+F)",
                                         placeholder_text_color=C["muted"],
                                         font=F["small"])
        self.search_entry.pack(side="left", padx=(6, 12), pady=2)
        self.search_entry._entry.configure(insertbackground=C["cyan"],
                                           insertofftime=0)
        self.search_entry.bind("<Return>", lambda _e: self._search())
        self.search_entry.bind(
            "<FocusIn>", lambda _e: self.search_box.configure(border_color=C["purple"]))
        self.search_entry.bind(
            "<FocusOut>", lambda _e: self.search_box.configure(border_color=C["border"]))

    def _search(self):
        query = self.search_entry.get().strip()
        if query:
            self.app.do_search(query)

    def set_crumbs(self, main, sub):
        self.crumb_main.configure(text=main)
        self.crumb_sub.configure(text=sub)


# ============================================================================
#  BASISKLASSE FUER ANSICHTEN
# ============================================================================

class View(ScrollArea):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self.db = app.db
        self.content = transparent_frame(self.inner)
        self.content.pack(fill="both", expand=True, padx=28, pady=(2, 28))
        self.build()

    def build(self):
        raise NotImplementedError

    def on_show(self):
        pass


# ============================================================================
#  DASHBOARD
# ============================================================================

class DashboardView(View):
    DAYS = 14

    def build(self):
        self.totals = content_totals()
        self.total_content = sum(self.totals.values())

        # --- Banner --------------------------------------------------------
        self.hero = GradientPanel(self.content, height=118)
        self.hero.pack(fill="x")

        # --- Reihe 1: Kennzahlen (fuenf gleich breite Kacheln) -----------
        row1 = transparent_frame(self.content)
        row1.pack(fill="x", pady=(16, 0))
        for column in range(5):
            row1.columnconfigure(column, weight=1, uniform="row1")

        self.ring_cards = self._ring_card(row1, 0, "Karteikarten")
        self.ring_quiz = self._ring_card(row1, 1, "Quizfragen")
        self.ring_ap1 = self._ring_card(row1, 2, "AP1 Szenarien")
        self.ring_scen = self._ring_card(row1, 3, "AP2 Szenarien")

        quote = Card(row1, title="Erfolgsquote", subtitle="Quiz gesamt",
                     accent=C["pink"])
        quote.grid(row=0, column=4, sticky="nsew")
        self.lbl_quote = make_label(quote.body, "0 %", font=F["display"],
                                    fg=C["cyan"])
        self.lbl_quote.pack(anchor="w", pady=(10, 0))
        self.lbl_quote_sub = make_label(quote.body, "noch keine Antworten",
                                        font=F["small"], fg=C["muted"],
                                        justify="left", wraplength=150,
                                        anchor="w")
        self.lbl_quote_sub.pack(anchor="w", pady=(6, 0))

        # --- Reihe 2: Verlauf und Abdeckung ------------------------------
        row2 = transparent_frame(self.content)
        row2.pack(fill="x", pady=(14, 0))
        row2.columnconfigure(0, weight=3, uniform="row2")
        row2.columnconfigure(1, weight=2, uniform="row2")

        chart_card = Card(row2, title="Lernverlauf",
                          subtitle="letzte %d Tage" % self.DAYS)
        chart_card.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        self.chart = LineChart(chart_card.body, height=230, parent_bg=C["card"])
        self.chart.pack(fill="both", expand=True)

        cover = Card(row2, title="Abdeckung", subtitle="Material",
                     accent=C["purple"])
        cover.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        self.bar_cards = GradientBar(cover.body, "Karteikarten", C["cyan"],
                                     C["purple"], parent_bg=C["card"])
        self.bar_cards.pack(fill="x", pady=(4, 8))
        self.bar_quiz = GradientBar(cover.body, "Quizfragen", C["purple"],
                                    C["pink"], parent_bg=C["card"])
        self.bar_quiz.pack(fill="x", pady=8)
        self.bar_ap1 = GradientBar(cover.body, "AP1-Szenarien", C["blue"],
                                   C["cyan"], parent_bg=C["card"])
        self.bar_ap1.pack(fill="x", pady=8)
        self.bar_scen = GradientBar(cover.body, "AP2-Szenarien", C["pink"],
                                    C["orange"], parent_bg=C["card"])
        self.bar_scen.pack(fill="x", pady=8)

        # --- Reihe 3: Heatmap und Fachbereiche ---------------------------
        row3 = transparent_frame(self.content)
        row3.pack(fill="x", pady=(14, 0))
        row3.columnconfigure(0, weight=2, uniform="row3")
        row3.columnconfigure(1, weight=3, uniform="row3")

        heat_card = Card(row3, title="Aktivität je Fachbereich",
                         subtitle="Intensität pro Tag", accent=C["pink"])
        heat_card.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        self.heatmap = Heatmap(heat_card.body, height=190, parent_bg=C["card"])
        self.heatmap.pack(fill="both", expand=True)

        fach_card = Card(row3, title="Fortschritt je Fachbereich",
                         subtitle="Abdeckung und Erfolgsquote", accent=C["green"])
        fach_card.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        holder = transparent_frame(fach_card.body)
        holder.pack(fill="x")
        self.fach_rings = {}
        for category in CATEGORIES:
            column = transparent_frame(holder)
            column.pack(side="left", fill="both", expand=True)
            ring = MiniRing(column, size=88, thickness=8, parent_bg=C["card"])
            ring.pack()
            make_label(column, CATEGORY_SHORT[category], font=F["small_bold"],
                       fg=C["text"]).pack(pady=(8, 0))
            detail = make_label(column, "", font=F["tiny"], fg=C["muted"],
                                justify="center")
            detail.pack()
            self.fach_rings[category] = (ring, detail)

        # --- Reihe 4: Aktivitaeten, Kalender -------------------------------
        row4 = transparent_frame(self.content)
        row4.pack(fill="x", pady=(14, 0))
        row4.columnconfigure(0, weight=1, uniform="row4")
        row4.columnconfigure(1, weight=1, uniform="row4")

        act_card = Card(row4, title="Aktivitäten", subtitle="zuletzt")
        act_card.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        self.activity_box = transparent_frame(act_card.body)
        self.activity_box.pack(fill="both", expand=True)

        cal_card = Card(row4, title="Lerntage", subtitle="Monatsübersicht",
                        accent=C["purple"])
        cal_card.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        self.calendar = CalendarPanel(cal_card.body, bg=C["card"])
        self.calendar.pack(fill="both", expand=True)
        self.calendar.set_provider(self.db.month_activity)

        # --- Reihe 5: AP1- und AP2-Themenfortschritt, direkt nebeneinander -
        row5 = transparent_frame(self.content)
        row5.pack(fill="x", pady=(14, 0))
        row5.columnconfigure(0, weight=1, uniform="row5")
        row5.columnconfigure(1, weight=1, uniform="row5")

        ap1_theme_card = Card(row5, title="AP1 Prüfungsthemen",
                              subtitle="bearbeitete Grundlagenaufgaben",
                              accent=C["blue"])
        ap1_theme_card.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        self.timeline_ap1 = ThemeTimeline(ap1_theme_card.body, height=200,
                                          parent_bg=C["card"])
        self.timeline_ap1.pack(fill="both", expand=True)

        theme_card = Card(row5, title="AP2 Prüfungsthemen",
                          subtitle="bearbeitete Szenarien", accent=C["pink"])
        theme_card.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        self.timeline = ThemeTimeline(theme_card.body, height=200,
                                      parent_bg=C["card"])
        self.timeline.pack(fill="both", expand=True)

    def _ring_card(self, parent, column, title):
        card = Card(parent, title=title)
        card.grid(row=0, column=column, sticky="nsew", padx=(0, 14))
        ring = RingStat(card.body, size=126, parent_bg=C["card"])
        ring.pack()
        return ring

    # -- Aktualisierung -----------------------------------------------------

    def on_show(self):
        self.calendar.to_current_month()
        self.refresh()

    def refresh(self):
        total_cards = len(KARTEIKARTEN)
        total_quiz = len(QUIZ_QUESTIONS)
        total_ap1 = len(AP1_SZENARIEN)
        total_scen = len(SZENARIEN)

        learned_cards = self.db.distinct_cards_learned()
        quiz_answered = self.db.count_quiz_answers()
        quiz_distinct = self.db.distinct_quiz_questions()
        ap1_done = self.db.distinct_ap1()
        scen_done = self.db.distinct_scenarios()

        rate, correct, answered = self.db.quiz_success_rate()
        learned = learned_cards + quiz_distinct
        self.hero.set_data(
            "Dein Lernstand",
            "Lernserie: %d Tag(e)   ·   %d von %d Inhalten bearbeitet   ·   "
            "Quiz-Erfolgsquote %d %%"
            % (self.db.streak(), learned, self.total_content, round(rate)),
            "%d %%" % round(learned / max(1, self.total_content) * 100),
            "Gesamtfortschritt")

        self.ring_cards.set(learned_cards / max(1, total_cards), C["cyan"],
                            C["purple"], str(learned_cards),
                            "von %d Karten" % total_cards)
        self.ring_quiz.set(quiz_distinct / max(1, total_quiz), C["purple"],
                           C["pink"], str(quiz_answered),
                           "%d von %d Fragen" % (quiz_distinct, total_quiz))
        self.ring_ap1.set(ap1_done / max(1, total_ap1), C["blue"],
                          C["cyan"], str(ap1_done),
                          "von %d Szenarien" % total_ap1)
        self.ring_scen.set(scen_done / max(1, total_scen), C["pink"],
                           C["orange"], str(scen_done),
                           "von %d Szenarien" % total_scen)

        self.lbl_quote.configure(text="%d %%" % round(rate))
        if answered:
            self.lbl_quote_sub.configure(
                text="%d von %d Fragen richtig beantwortet" % (correct, answered))
        else:
            self.lbl_quote_sub.configure(text="noch keine Antworten erfasst")

        self.bar_cards.set(learned_cards / max(1, total_cards) * 100,
                           "%d / %d" % (learned_cards, total_cards))
        self.bar_quiz.set(quiz_distinct / max(1, total_quiz) * 100,
                          "%d / %d" % (quiz_distinct, total_quiz))
        self.bar_ap1.set(ap1_done / max(1, total_ap1) * 100,
                         "%d / %d" % (ap1_done, total_ap1))
        self.bar_scen.set(scen_done / max(1, total_scen) * 100,
                          "%d / %d" % (scen_done, total_scen))

        # Lernverlauf
        daily = self.db.daily_counts(self.DAYS)
        labels = [day.strftime("%d.%m") for day, _count in daily]
        values = [count for _day, count in daily]
        self.chart.set_data(labels, [
            {"name": "Aufgaben pro Tag", "values": values, "color": C["cyan"]},
        ])

        # Heatmap
        matrix = self.db.category_daily(self.DAYS)
        rows = [(CATEGORY_SHORT[cat], CATEGORY_COLOR[cat], matrix[cat])
                for cat in CATEGORIES]
        self.heatmap.set_data(rows, self.DAYS)

        # Fachbereiche
        coverage = self.db.category_coverage(self.totals)
        stats = self.db.category_stats()
        for category in CATEGORIES:
            ring, detail = self.fach_rings[category]
            ring.set(coverage.get(category, 0.0), CATEGORY_COLOR[category])
            data = stats.get(category, {"answered": 0, "correct": 0})
            if data["answered"]:
                quota = data["correct"] / data["answered"] * 100
                detail.configure(text="%d Antworten\n%d%% richtig"
                                      % (data["answered"], round(quota)))
            else:
                detail.configure(text="noch nicht\nbearbeitet")

        # Aktivitaeten
        for child in self.activity_box.winfo_children():
            child.destroy()
        activities = self.db.recent_activities(7)
        if not activities:
            make_label(self.activity_box,
                       "Noch keine Aktivitäten.\nStarte mit den Karteikarten "
                       "oder dem Prüfungstrainer.",
                       font=F["small"], fg=C["muted"], justify="left").pack(anchor="w")
        else:
            for timestamp, kind, detail, extra in activities:
                self._activity_row(timestamp, kind, detail, extra)

        self.calendar.refresh()

        progress = self.db.theme_progress(theme_totals())
        self.timeline.set_data([(name, progress.get(name, 0.0), THEME_COLOR[name])
                                for name in AP2_THEMES])

        progress_ap1 = self.db.theme_progress(ap1_theme_totals(), themes=AP1_THEMES,
                                              table="ap1_events")
        self.timeline_ap1.set_data([(name, progress_ap1.get(name, 0.0),
                                     THEME_COLOR[name]) for name in AP1_THEMES])

    def _activity_row(self, timestamp, kind, detail, extra):
        row = ctk.CTkFrame(self.activity_box, fg_color=C["card_alt"],
                           corner_radius=10)
        row.pack(fill="x", pady=3)
        color = {"Karteikarte": C["cyan"], "Quizfrage": C["purple"],
                 "AP1-Szenario": C["blue"], "AP2-Szenario": C["pink"],
                 "Test-Session": C["green"]}.get(kind, C["muted"])
        ctk.CTkLabel(row, text="", width=9, height=9,
                     image=ctk_image(circle_image(9, fill=color), 9, 9)).pack(
                         side="left", padx=(12, 10))

        text_box = transparent_frame(row)
        text_box.pack(side="left", fill="x", expand=True, pady=7)
        short_detail = detail if len(str(detail)) <= 34 else str(detail)[:32] + "…"
        make_label(text_box, "%s · %s" % (kind, short_detail),
                   font=F["small"], fg=C["text_dim"], anchor="w").pack(anchor="w")
        make_label(text_box, "%s  ·  %s" % (timestamp[:16].replace("-", "."), extra),
                   font=F["tiny"], fg=C["muted"], anchor="w").pack(anchor="w")


# ============================================================================
#  KARTEIKARTEN
# ============================================================================

class CardsView(View):
    MODES = [("freitext", "Freitext"), ("mc", "Multiple Choice"),
             ("reveal", "Aufdecken")]

    def build(self):
        self.cards = list(KARTEIKARTEN)
        self.filtered = list(self.cards)
        self.index = 0
        self.mode = "freitext"
        self.logged = set()

        top = Card(self.content)
        top.pack(fill="x")
        bar = transparent_frame(top.body)
        bar.pack(fill="x")

        make_label(bar, "FACHBEREICH", font=F["label"], fg=C["muted"]).pack(anchor="w")
        options = [("Alle", "Alle")] + [(c, CATEGORY_SHORT[c]) for c in CATEGORIES]
        self.cat_pills = PillGroup(bar, options, on_change=self._on_category)
        self.cat_pills.pack(anchor="w", pady=(8, 14))

        make_label(bar, "LERNMODUS", font=F["label"], fg=C["muted"]).pack(anchor="w")
        self.mode_pills = PillGroup(bar, self.MODES, on_change=self._on_mode)
        self.mode_pills.pack(anchor="w", pady=(8, 0))

        # Frage
        self.question_card = Card(self.content, title="Frage", accent=C["cyan"],
                                  subtitle="")
        self.question_card.pack(fill="x", pady=(14, 0))
        self.lbl_question = make_label(self.question_card.body, "",
                                       font=F["h2"], fg=C["text"],
                                       wraplength=900, justify="left", anchor="w")
        self.lbl_question.pack(anchor="w", pady=6)

        # Antwortbereich
        self.answer_card = Card(self.content, title="Deine Antwort",
                                accent=C["purple"])
        self.answer_card.pack(fill="both", expand=True, pady=(14, 0))

        # Fester Platzhalter fuer den Eingabebereich. Ohne diesen Container
        # wuerden spaeter eingeblendete Elemente unterhalb der Rueckmeldung
        # landen, weil Tk die Reihenfolge der pack-Aufrufe beibehaelt.
        self.input_area = transparent_frame(self.answer_card.body)
        self.input_area.pack(fill="x")

        self.frame_free = transparent_frame(self.input_area)
        make_label(self.frame_free,
                   "Formuliere deine Antwort in eigenen Worten:",
                   font=F["small"], fg=C["text_dim"]).pack(anchor="w")
        self.txt_answer = make_text(self.frame_free, height=5)
        self.txt_answer.pack(fill="x", pady=(8, 0))

        self.options = OptionList(self.input_area, bg=C["card"])

        self.frame_reveal = transparent_frame(self.input_area)
        make_label(self.frame_reveal,
                   "Überlege dir die Antwort und decke sie anschließend auf.",
                   font=F["small"], fg=C["text_dim"]).pack(anchor="w", pady=4)

        self.lbl_feedback = make_label(self.answer_card.body, "",
                                       font=F["body_bold"], fg=C["text"],
                                       wraplength=900, justify="left", anchor="w")
        self.lbl_feedback.pack(anchor="w", pady=(14, 0))
        self.lbl_solution = make_label(self.answer_card.body, "",
                                       font=F["body"], fg=C["text_dim"],
                                       wraplength=900, justify="left", anchor="w")
        self.lbl_solution.pack(anchor="w", pady=(6, 0))

        # Steuerung
        controls = transparent_frame(self.content)
        controls.pack(fill="x", pady=(14, 0))
        self.btn_prev = NeoButton(controls, "Zurück", self.prev_card,
                                  kind="ghost", icon="arrow_left")
        self.btn_prev.pack(side="left")
        self.btn_check = NeoButton(controls, "Antwort prüfen", self.check_answer,
                                   kind="primary")
        self.btn_check.pack(side="left", padx=10)
        self.btn_next = NeoButton(controls, "Nächste Karte", self.next_card,
                                  kind="accent", icon="arrow_right")
        self.btn_next.pack(side="left")
        self.lbl_counter = make_label(controls, "", font=F["body_bold"],
                                      fg=C["text_dim"])
        self.lbl_counter.pack(side="right", pady=8)

        self.update_ui()

    # -- Steuerung ----------------------------------------------------------

    def set_category(self, category):
        self.cat_pills.select_value(category, notify=False)
        self._on_category(category)

    def _on_category(self, category):
        if category == "Alle":
            self.filtered = list(self.cards)
        else:
            self.filtered = [c for c in self.cards if c["cat"] == category]
        self.index = 0
        self.update_ui()

    def set_mode(self, mode):
        """Setzt den Lernmodus inklusive der Auswahlknoepfe."""
        self.mode_pills.select_value(mode, notify=False)
        self._on_mode(mode)

    def _on_mode(self, mode):
        self.mode = mode
        self.update_ui()

    def jump_to_question(self, question_text):
        for position, card in enumerate(self.filtered):
            if card["q"] == question_text:
                self.index = position
                self.update_ui()
                return
        # nicht im aktuellen Filter: Filter zuruecksetzen
        self.cat_pills.select(0, notify=False)
        self.filtered = list(self.cards)
        for position, card in enumerate(self.filtered):
            if card["q"] == question_text:
                self.index = position
                break
        self.update_ui()

    def update_ui(self):
        self.lbl_feedback.configure(text="")
        self.lbl_solution.configure(text="")
        self.frame_free.pack_forget()
        self.options.pack_forget()
        self.frame_reveal.pack_forget()
        self.options.clear()

        if not self.filtered:
            self.lbl_question.configure(text="Für diesen Fachbereich sind keine "
                                             "Karteikarten hinterlegt.")
            self.lbl_counter.configure(text="0 / 0")
            self.btn_check.set_enabled(False)
            return

        self.btn_check.set_enabled(True)
        card = self.filtered[self.index]
        self.lbl_question.configure(text=card["q"])
        self.lbl_counter.configure(text="Karte %d / %d"
                                        % (self.index + 1, len(self.filtered)))
        self.question_card.set_subtitle(CATEGORY_SHORT[card["cat"]],
                                        CATEGORY_COLOR[card["cat"]])

        if self.mode == "freitext":
            self.frame_free.pack(fill="x")
            self.txt_answer.delete("1.0", "end")
            self.btn_check.set_text("Antwort prüfen")
        elif self.mode == "mc":
            self.options.pack(fill="x")
            shuffled = list(card["options"])
            random.Random(hash(card["q"]) & 0xFFFF).shuffle(shuffled)
            self.options.set_options(shuffled)
            self.btn_check.set_text("Antwort prüfen")
        else:
            self.frame_reveal.pack(fill="x")
            self.btn_check.set_text("Lösung aufdecken")

    def check_answer(self):
        if not self.filtered:
            return
        card = self.filtered[self.index]
        correct = None

        if self.mode == "freitext":
            user_input = self.txt_answer.get("1.0", "end").strip()
            if not user_input:
                messagebox.showwarning("Hinweis", "Bitte gib zuerst deine Antwort ein.")
                return
            correct = card["a"].lower() in user_input.lower()
            if correct:
                self.lbl_feedback.configure(text="Sehr gut - deine Antwort enthält "
                                                 "die Kernlösung.",
                                            text_color=C["green"])
            else:
                self.lbl_feedback.configure(text="Vergleiche deine Eingabe mit der "
                                                 "Musterlösung:",
                                            text_color=C["yellow"])
            self.lbl_solution.configure(text="Musterlösung: " + card["a_full"])

        elif self.mode == "mc":
            choice = self.options.get()
            if not choice:
                messagebox.showwarning("Hinweis", "Bitte wähle eine Antwort aus.")
                return
            correct = choice == card["a"]
            self.options.reveal(card["a"])
            if correct:
                self.lbl_feedback.configure(text="Richtig beantwortet.",
                                            text_color=C["green"])
            else:
                self.lbl_feedback.configure(text="Leider falsch. Richtig wäre: "
                                                 + card["a"], text_color=C["red"])
            self.lbl_solution.configure(text=card["a_full"])

        else:
            self.lbl_feedback.configure(text="Musterlösung", text_color=C["cyan"])
            self.lbl_solution.configure(text=card["a_full"])

        key = (card["q"], self.mode)
        if key not in self.logged:
            self.logged.add(key)
            self.db.log_card(card["cat"], card["q"], self.mode, correct)
            self.app.notify_progress()

    def next_card(self):
        if self.filtered:
            self.index = (self.index + 1) % len(self.filtered)
            self.update_ui()

    def prev_card(self):
        if self.filtered:
            self.index = (self.index - 1) % len(self.filtered)
            self.update_ui()


# ============================================================================
#  PRUEFUNGSTRAINER
# ============================================================================

class QuizView(View):
    def build(self):
        self.questions = list(QUIZ_QUESTIONS)
        self.pool = list(self.questions)
        self.session = []
        self.index = 0
        self.score = 0
        self.running = False
        self.answered = False
        self.start_time = 0
        self.timer_job = None

        # Setup
        self.setup_card = Card(self.content, title="Test-Session",
                               subtitle="%d Aufgaben im Katalog" % len(self.questions))
        self.setup_card.pack(fill="x")
        body = self.setup_card.body

        make_label(body, "FACHBEREICH", font=F["label"], fg=C["muted"]).pack(anchor="w")
        options = [("Alle", "Alle")] + [(c, CATEGORY_SHORT[c]) for c in CATEGORIES]
        self.cat_pills = PillGroup(body, options, on_change=self._on_category)
        self.cat_pills.pack(anchor="w", pady=(8, 14))

        row = transparent_frame(body)
        row.pack(anchor="w", fill="x")
        make_label(row, "Fragenanzahl", font=F["small"],
                   fg=C["text_dim"]).pack(side="left", padx=(0, 10))
        self.stepper = NumberStepper(row, value=10, minimum=5, maximum=len(self.questions),
                                     step=5, bg=C["card"])
        self.stepper.pack(side="left")
        self.btn_start = NeoButton(row, "Session starten", self.start_quiz,
                                   kind="primary")
        self.btn_start.pack(side="left", padx=16)
        self.lbl_pool = make_label(row, "", font=F["small"], fg=C["muted"])
        self.lbl_pool.pack(side="left")

        # Statusleiste
        self.status_card = Card(self.content, pad=14)
        self.status_card.pack(fill="x", pady=(14, 0))
        status = self.status_card.body
        self.lbl_progress = make_label(status, "Frage 0 / 0", font=F["body_bold"],
                                       fg=C["text_dim"])
        self.lbl_progress.pack(side="left")
        self.lbl_timer = make_label(status, "00:00", font=F["body_bold"],
                                    fg=C["cyan"])
        self.lbl_timer.pack(side="right")
        self.lbl_score = make_label(status, "", font=F["small"], fg=C["muted"])
        self.lbl_score.pack(side="right", padx=16)

        # Frage
        self.question_card = Card(self.content, title="Prüfungsaufgabe",
                                  accent=C["cyan"])
        self.question_card.pack(fill="both", expand=True, pady=(14, 0))
        self.lbl_question = make_label(
            self.question_card.body,
            "Wähle Fachbereich und Fragenanzahl und starte die Session.",
            font=F["h2"], fg=C["text"], wraplength=900, justify="left", anchor="w")
        self.lbl_question.pack(anchor="w", pady=(4, 12))

        self.options = OptionList(self.question_card.body, bg=C["card"])
        self.options.pack(fill="x")

        self.lbl_explain = make_label(self.question_card.body, "", font=F["body"],
                                      fg=C["text_dim"], wraplength=900,
                                      justify="left", anchor="w")
        self.lbl_explain.pack(anchor="w", pady=(12, 0))

        controls = transparent_frame(self.content)
        controls.pack(fill="x", pady=(14, 0))
        self.btn_submit = NeoButton(controls, "Antwort einreichen",
                                    self.submit_answer, kind="primary")
        self.btn_submit.pack(side="left")
        self.btn_submit.set_enabled(False)
        self.btn_cancel = NeoButton(controls, "Session abbrechen",
                                    self.cancel_quiz, kind="ghost")
        self.btn_cancel.pack(side="left", padx=10)
        self.btn_cancel.set_enabled(False)

        self._on_category("Alle")

    # -- Vorbereitung -------------------------------------------------------

    def _on_category(self, category):
        if category == "Alle":
            self.pool = list(self.questions)
        else:
            self.pool = [q for q in self.questions if q["cat"] == category]
        self.stepper.set_maximum(max(5, len(self.pool)))
        self.lbl_pool.configure(text="%d Fragen verfügbar" % len(self.pool))

    # -- Ablauf -------------------------------------------------------------

    def start_quiz(self):
        if not self.pool:
            messagebox.showinfo("Hinweis", "Für diesen Fachbereich sind keine "
                                           "Fragen hinterlegt.")
            return
        count = min(self.stepper.get(), len(self.pool))
        self.session = random.sample(self.pool, count)
        self.index = 0
        self.score = 0
        self.running = True
        self.answered = False
        self.start_time = time.time()

        self.btn_start.set_enabled(False)
        self.btn_cancel.set_enabled(True)
        self.btn_submit.set_enabled(True)
        self._tick()
        self.load_question()

    def _tick(self):
        if not self.running:
            return
        elapsed = int(time.time() - self.start_time)
        self.lbl_timer.configure(text="%02d:%02d" % (elapsed // 60, elapsed % 60))
        self.timer_job = self.app.root.after(1000, self._tick)

    def stop_timer(self):
        self.running = False
        if self.timer_job is not None:
            try:
                self.app.root.after_cancel(self.timer_job)
            except tk.TclError:
                pass
            self.timer_job = None

    def load_question(self):
        self.answered = False
        question = self.session[self.index]
        self.lbl_question.configure(text="%d. %s" % (self.index + 1, question["q"]))
        self.lbl_explain.configure(text="")
        shuffled = list(question["options"])
        random.shuffle(shuffled)
        self.options.set_options(shuffled)
        self.lbl_progress.configure(text="Frage %d / %d"
                                         % (self.index + 1, len(self.session)))
        self.lbl_score.configure(text="%d richtig" % self.score)
        self.btn_submit.set_text("Antwort einreichen")
        self.btn_submit.set_enabled(True)

    def submit_answer(self):
        if not self.running:
            return
        if self.answered:
            self._advance()
            return

        choice = self.options.get()
        if not choice:
            messagebox.showwarning("Hinweis", "Bitte wähle eine Antwort aus.")
            return

        question = self.session[self.index]
        correct = choice == question["a"]
        if correct:
            self.score += 1
        self.options.reveal(question["a"])
        self.answered = True
        prefix = "Richtig. " if correct else "Falsch. Richtig wäre: %s. " % question["a"]
        self.lbl_explain.configure(text=prefix + question["exp"],
                                   text_color=C["green"] if correct else C["text_dim"])
        self.lbl_score.configure(text="%d richtig" % self.score)
        self.db.log_quiz_answer(question["cat"], question["q"], correct)
        self.app.notify_progress()

        last = self.index >= len(self.session) - 1
        self.btn_submit.set_text("Auswertung anzeigen" if last else "Nächste Frage")

    def _advance(self):
        if self.index >= len(self.session) - 1:
            self.finish_quiz()
        else:
            self.index += 1
            self.load_question()

    def cancel_quiz(self):
        if not self.running:
            return
        if not messagebox.askyesno("Session abbrechen",
                                   "Die laufende Session wirklich abbrechen? "
                                   "Bereits beantwortete Fragen bleiben in der "
                                   "Statistik erhalten."):
            return
        self.stop_timer()
        self._reset_controls()
        self.lbl_question.configure(text="Session abgebrochen. Du kannst jederzeit "
                                         "eine neue starten.")
        self.options.clear()
        self.lbl_explain.configure(text="")

    def finish_quiz(self):
        self.stop_timer()
        total = len(self.session)
        percentage = (self.score / total) * 100 if total else 0.0
        elapsed = int(time.time() - self.start_time)
        note = ihk_note(percentage)
        saved = self.db.save_test_result(self.score, total, percentage, note, elapsed)

        self.options.clear()
        self.lbl_explain.configure(text="")
        self._reset_controls()

        hint = ("Das Ergebnis wurde gespeichert."
                if saved else "Achtung: Das Ergebnis konnte nicht gespeichert werden.")
        self.lbl_question.configure(
            text="Session beendet\n\n"
                 "Ergebnis: %d von %d richtig (%.1f %%)\n"
                 "IHK-Note: %s\n"
                 "Dauer: %02d:%02d Minuten\n\n%s"
                 % (self.score, total, percentage, note,
                    elapsed // 60, elapsed % 60, hint))
        self.app.notify_progress()

    def _reset_controls(self):
        self.running = False
        self.btn_start.set_enabled(True)
        self.btn_cancel.set_enabled(False)
        self.btn_submit.set_enabled(False)
        self.btn_submit.set_text("Antwort einreichen")
        self.lbl_progress.configure(text="Frage 0 / 0")
        self.lbl_timer.configure(text="00:00")

    def jump_to_question(self, question_text):
        for question in self.questions:
            if question["q"] == question_text:
                self.stop_timer()
                self._reset_controls()
                self.lbl_question.configure(text=question["q"])
                self.options.set_options(list(question["options"]))
                self.options.reveal(question["a"])
                self.lbl_explain.configure(text=question["exp"],
                                           text_color=C["text_dim"])
                return


# ============================================================================
#  AP2 SZENARIEN
# ============================================================================

class ScenarioViewBase(View):
    """Gemeinsame Basis fuer AP1- und AP2-Szenarien: Liste links, rechts die
    Aufgabenstellung, ein frei wachsendes Feld fuer die eigene schriftliche
    Loesung und darunter die Musterloesung zum Aufdecken.

    Unterklassen ueberschreiben DATA (Liste der Szenarien), LIST_TITLE
    (Ueberschrift der linken Liste) und _log() (welche DB-Tabelle protokolliert
    wird), der restliche Ablauf ist identisch.
    """

    DATA = SZENARIEN
    LIST_TITLE = "Szenarien"

    def build(self):
        self.index = 0
        self.solution_visible = False
        # Eigene Loesungstexte bleiben nur waehrend der laufenden Sitzung
        # erhalten (kein Datenbank-Feld), damit man beim Szenario-Wechsel
        # nicht jedes Mal von vorn anfangen muss.
        self.own_answers = {}

        layout = transparent_frame(self.content)
        layout.pack(fill="both", expand=True)
        layout.columnconfigure(0, weight=2, uniform="scen")
        layout.columnconfigure(1, weight=5, uniform="scen")

        list_card = Card(layout, title=self.LIST_TITLE,
                         subtitle="%d Aufgaben" % len(self.DATA))
        list_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.list_box = transparent_frame(list_card.body)
        self.list_box.pack(fill="both", expand=True)
        self.list_rows = []
        for position, scenario in enumerate(self.DATA):
            self.list_rows.append(self._list_row(position, scenario))

        detail = transparent_frame(layout)
        detail.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self.task_card = Card(detail, title="Aufgabenstellung", accent=C["cyan"])
        self.task_card.pack(fill="both", expand=True)
        self.lbl_title = make_label(self.task_card.body, "", font=F["h2"],
                                    fg=C["text"], wraplength=760, justify="left",
                                    anchor="w")
        self.lbl_title.pack(anchor="w", pady=(0, 10))
        self.txt_task = make_text(self.task_card.body, height=11, readonly=True)
        self.txt_task.pack(fill="both", expand=True)

        self.own_card = Card(detail, title="Deine Lösung", accent=C["purple"],
                             subtitle="wächst automatisch mit dem Text")
        self.own_card.pack(fill="x", pady=(14, 0))
        make_label(self.own_card.body,
                   "Löse die Aufgabe hier schriftlich, bevor du die "
                   "Musterlösung aufdeckst.",
                   font=F["small"], fg=C["text_dim"]).pack(anchor="w", pady=(0, 6))
        self.txt_own = make_autogrow_text(self.own_card.body, min_height=4,
                                          max_height=18)
        self.txt_own.pack(fill="x")
        self.txt_own.bind("<KeyRelease>", self._on_own_change, add="+")

        self.sol_card = Card(detail, title="Musterlösung", accent=C["green"])
        self.sol_card.pack(fill="both", expand=True, pady=(14, 0))
        self.txt_solution = make_text(self.sol_card.body, height=11, readonly=True)
        self.txt_solution.pack(fill="both", expand=True)

        controls = transparent_frame(detail)
        controls.pack(fill="x", pady=(14, 0))
        self.btn_toggle = NeoButton(controls, "Musterlösung anzeigen",
                                    self.toggle_solution, kind="primary")
        self.btn_toggle.pack(side="left")
        NeoButton(controls, "Nächstes Szenario", self.next_scenario,
                  kind="ghost", icon="arrow_right").pack(side="left", padx=10)

        self.load_scenario(0)

    def _on_own_change(self, _event=None):
        self.own_answers[self.index] = self.txt_own.get("1.0", "end-1c")

    def _list_row(self, position, scenario):
        row, marker, inner = clickable_row(self.list_box,
                                           CATEGORY_COLOR[scenario["cat"]])
        row.pack(fill="x", pady=4)
        title = ctk.CTkLabel(inner, text="%d. %s" % (position + 1, scenario["title"]),
                             text_color=C["text"], font=F["small_bold"], height=0,
                             anchor="w", justify="left", wraplength=190,
                             cursor="hand2")
        title.pack(anchor="w")
        theme = ctk.CTkLabel(inner, text=scenario["theme"], text_color=C["muted"],
                             font=F["tiny"], anchor="w", height=0, cursor="hand2")
        theme.pack(anchor="w")
        bind_click((row, inner, title, theme, marker),
                   lambda _e, p=position: self.load_scenario(p))
        return {"frame": row, "title": title}

    def _highlight(self):
        for position, row in enumerate(self.list_rows):
            active = position == self.index
            row["frame"].configure(fg_color=C["card_hi"] if active else C["card_alt"],
                                   border_color=C["purple"] if active else C["border"])
            row["title"].configure(text_color=C["text"] if active else C["text_dim"])

    def load_scenario(self, position):
        self.index = position
        scenario = self.DATA[position]
        self.lbl_title.configure(text=scenario["title"])
        set_text(self.txt_task, scenario["text"])
        self.solution_visible = False
        set_text(self.txt_solution,
                 "Die Musterlösung ist noch ausgeblendet.\n\n"
                 "Bearbeite die Aufgabe zuerst selbst und decke die Lösung "
                 "anschließend auf.")
        self.btn_toggle.set_text("Musterlösung anzeigen")
        set_text(self.txt_own, self.own_answers.get(position, ""))
        self._highlight()

    def toggle_solution(self):
        scenario = self.DATA[self.index]
        if self.solution_visible:
            set_text(self.txt_solution, "Die Musterlösung ist ausgeblendet.")
            self.btn_toggle.set_text("Musterlösung anzeigen")
            self.solution_visible = False
        else:
            set_text(self.txt_solution, scenario["solution"])
            self.btn_toggle.set_text("Musterlösung ausblenden")
            self.solution_visible = True
            self._log(scenario)
            self.app.notify_progress()

    def _log(self, scenario):
        """In Unterklassen ueberschrieben - schreibt in die passende DB-Tabelle."""
        raise NotImplementedError

    def next_scenario(self):
        self.load_scenario((self.index + 1) % len(self.DATA))


class ScenarioView(ScenarioViewBase):
    """AP2-Szenarien (Schwerpunktpruefung: Netzwerk, Sicherheit, Systeme, Wirtschaft)."""

    DATA = SZENARIEN
    LIST_TITLE = "AP2-Szenarien"

    def _log(self, scenario):
        self.db.log_scenario(self.index, scenario["title"], scenario["theme"])


class Ap1ScenarioView(ScenarioViewBase):
    """AP1-Szenarien (Grundlagenpruefung aus dem 1./2. Lehrjahr)."""

    DATA = AP1_SZENARIEN
    LIST_TITLE = "AP1-Szenarien"

    def _log(self, scenario):
        self.db.log_ap1(self.index, scenario["title"], scenario["theme"])


# ============================================================================
#  TEST PROJEKT
# ============================================================================

class ProjectView(View):
    """Uebt die komplette Projektarbeit an einem realistischen Kundenauftrag:
    Ausgangssituation, Auftrag, Rahmenbedingungen und Arbeitsauftraege zum
    selbststaendigen Bearbeiten, dazu Loesungsansaetze zum Vergleich."""

    def build(self):
        self.index = 0
        self.hints_visible = False

        layout = transparent_frame(self.content)
        layout.pack(fill="both", expand=True)
        layout.columnconfigure(0, weight=2, uniform="proj")
        layout.columnconfigure(1, weight=5, uniform="proj")

        list_card = Card(layout, title="Testprojekte",
                         subtitle="%d Kundenaufträge" % len(PROJEKTARBEITEN))
        list_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.list_box = transparent_frame(list_card.body)
        self.list_box.pack(fill="both", expand=True)
        self.list_rows = []
        for position, project in enumerate(PROJEKTARBEITEN):
            self.list_rows.append(self._list_row(position, project))

        detail = transparent_frame(layout)
        detail.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self.header_label = make_label(detail, "", font=F["h2"], fg=C["text"],
                                       wraplength=760, justify="left", anchor="w")
        self.header_label.pack(anchor="w")
        self.meta_label = make_label(detail, "", font=F["small"], fg=C["muted"])
        self.meta_label.pack(anchor="w", pady=(2, 12))

        self.task_card = Card(detail, title="Kundenauftrag", accent=C["cyan"])
        self.task_card.pack(fill="both", expand=True)
        self.txt_task = make_text(self.task_card.body, height=14, readonly=True)
        self.txt_task.pack(fill="both", expand=True)

        self.hint_card = Card(detail, title="Lösungsansätze", accent=C["green"])
        self.hint_card.pack(fill="both", expand=True, pady=(14, 0))
        self.txt_hints = make_text(self.hint_card.body, height=14, readonly=True)
        self.txt_hints.pack(fill="both", expand=True)

        controls = transparent_frame(detail)
        controls.pack(fill="x", pady=(14, 0))
        self.btn_toggle = NeoButton(controls, "Lösungsansätze anzeigen",
                                    self.toggle_hints, kind="primary")
        self.btn_toggle.pack(side="left")
        NeoButton(controls, "Nächstes Projekt", self.next_project,
                  kind="ghost", icon="arrow_right").pack(side="left", padx=10)

        self.load_project(0)

    def _list_row(self, position, project):
        row, marker, inner = clickable_row(self.list_box,
                                           CATEGORY_COLOR[project["cat"]])
        row.pack(fill="x", pady=4)
        title = ctk.CTkLabel(inner, text="%d. %s" % (position + 1, project["title"]),
                             text_color=C["text"], font=F["small_bold"], height=0,
                             anchor="w", justify="left", wraplength=190,
                             cursor="hand2")
        title.pack(anchor="w")
        sub = ctk.CTkLabel(inner, text="%s · %s" % (project["schwierigkeit"],
                                                     CATEGORY_SHORT[project["cat"]]),
                           text_color=C["muted"], font=F["tiny"], anchor="w",
                           height=0, cursor="hand2")
        sub.pack(anchor="w")
        bind_click((row, inner, title, sub, marker),
                   lambda _e, p=position: self.load_project(p))
        return {"frame": row, "title": title}

    def _highlight(self):
        done = self.db.completed_projects()
        for position, row in enumerate(self.list_rows):
            active = position == self.index
            row["frame"].configure(fg_color=C["card_hi"] if active else C["card_alt"],
                                   border_color=C["purple"] if active else C["border"])
            mark = " ✓" if position in done else ""
            project = PROJEKTARBEITEN[position]
            row["title"].configure(
                text_color=C["text"] if active else C["text_dim"],
                text="%d. %s%s" % (position + 1, project["title"], mark))

    @staticmethod
    def _task_text(project):
        lines = [
            "AUSGANGSSITUATION", project["ausgangssituation"], "",
            "AUFTRAG", project["auftrag"], "",
            "RAHMENBEDINGUNGEN",
        ]
        lines += ["  - " + item for item in project["rahmenbedingungen"]]
        lines += ["", "IHRE AUFGABEN (Projektantrag)"]
        for position, aufgabe in enumerate(project["aufgaben"], start=1):
            lines.append("  %d. %s" % (position, aufgabe))
        return "\n".join(lines)

    @staticmethod
    def _hint_text(project):
        lines = [
            "Diese Hinweise ersetzen keine eigene Bearbeitung - nutze sie zum "
            "Vergleich, nachdem du deinen eigenen Projektantrag geschrieben hast.",
            "",
        ]
        for position, (aufgabe, hinweis) in enumerate(
                zip(project["aufgaben"], project["hinweise"]), start=1):
            lines.append("%d. %s" % (position, aufgabe))
            lines.append("   Lösungsansatz: %s" % hinweis)
            lines.append("")
        return "\n".join(lines).rstrip()

    def load_project(self, position):
        self.index = position
        project = PROJEKTARBEITEN[position]
        self.header_label.configure(text=project["title"])
        self.meta_label.configure(
            text="%s  ·  Schwierigkeit: %s  ·  Fachbereich: %s"
                 % (project["branche"], project["schwierigkeit"],
                    CATEGORY_SHORT[project["cat"]]))
        set_text(self.txt_task, self._task_text(project))
        self.hints_visible = False
        set_text(self.txt_hints,
                 "Die Lösungsansätze sind noch ausgeblendet.\n\n"
                 "Bearbeite den Projektantrag zuerst selbst - Ist-Analyse, "
                 "Konzept, Zeit- und Kostenplanung, Risiken - und decke die "
                 "Lösungsansätze anschließend zum Vergleich auf.")
        self.btn_toggle.set_text("Lösungsansätze anzeigen")
        self._highlight()

    def toggle_hints(self):
        project = PROJEKTARBEITEN[self.index]
        if self.hints_visible:
            set_text(self.txt_hints, "Die Lösungsansätze sind ausgeblendet.")
            self.btn_toggle.set_text("Lösungsansätze anzeigen")
            self.hints_visible = False
        else:
            set_text(self.txt_hints, self._hint_text(project))
            self.btn_toggle.set_text("Lösungsansätze ausblenden")
            self.hints_visible = True
            self.db.log_project(self.index, project["title"], project["cat"])
            self.app.notify_progress()
            self._highlight()

    def next_project(self):
        self.load_project((self.index + 1) % len(PROJEKTARBEITEN))


# ============================================================================
#  PRAXIS-RECHNER
# ============================================================================

class CalcView(View):
    def build(self):
        self.info_visible = {"subnet": False, "raid": False, "screen": False}
        self.info_frames = {}
        self.info_buttons = {}

        layout = transparent_frame(self.content)
        layout.pack(fill="both", expand=True)
        layout.columnconfigure(0, weight=1, uniform="calc")
        layout.columnconfigure(1, weight=1, uniform="calc")

        # --- Subnetting ---------------------------------------------------
        subnet = Card(layout, title="Subnetting / VLSM", accent=C["cyan"],
                      subtitle="IPv4 und IPv6")
        subnet.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        make_label(subnet.body, "IP-Adresse mit Präfix (z.B. 192.168.1.50/24)",
                   font=F["small"], fg=C["text_dim"]).pack(anchor="w")
        self.entry_ip = EntryBox(subnet.body, width=28, value="192.168.1.50/24")
        self.entry_ip.pack(anchor="w", pady=(8, 12), fill="x")
        self.entry_ip.entry.bind("<Return>", lambda _e: self.calc_subnet())
        NeoButton(subnet.body, "Berechnen", self.calc_subnet,
                  kind="accent").pack(anchor="w")
        self.txt_subnet = make_text(subnet.body, height=9, readonly=True,
                                    font=F["mono_small"])
        self.txt_subnet.pack(fill="both", expand=True, pady=(14, 0))
        self._build_info_toggle(subnet.body, "subnet", CALC_EXPLAIN_SUBNET)

        # --- RAID ---------------------------------------------------------
        raid = Card(layout, title="RAID-Kapazität", accent=C["purple"],
                    subtitle="Netto, Parität, Effizienz")
        raid.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        make_label(raid.body, "RAID-Level", font=F["small"],
                   fg=C["text_dim"]).pack(anchor="w")
        self.raid_pills = PillGroup(raid.body, [(level, level) for level in RAID_LEVELS],
                                    initial=2)
        self.raid_pills.pack(anchor="w", pady=(8, 12))

        grid = transparent_frame(raid.body)
        grid.pack(anchor="w", fill="x")
        make_label(grid, "Anzahl Festplatten", font=F["small"],
                   fg=C["text_dim"]).grid(row=0, column=0, sticky="w", pady=4)
        self.entry_disks = EntryBox(grid, width=8, value="4")
        self.entry_disks.grid(row=0, column=1, sticky="w", padx=12, pady=4)
        make_label(grid, "Kapazität je Platte (GB)", font=F["small"],
                   fg=C["text_dim"]).grid(row=1, column=0, sticky="w", pady=4)
        self.entry_size = EntryBox(grid, width=8, value="1000")
        self.entry_size.grid(row=1, column=1, sticky="w", padx=12, pady=4)

        NeoButton(raid.body, "Berechnen", self.calc_raid,
                  kind="primary").pack(anchor="w", pady=(12, 0))
        self.txt_raid = make_text(raid.body, height=9, readonly=True,
                                  font=F["mono_small"])
        self.txt_raid.pack(fill="both", expand=True, pady=(14, 0))
        self._build_info_toggle(raid.body, "raid", CALC_EXPLAIN_RAID)

        # --- Bildschirm-Datenvolumen ---------------------------------------
        screen = Card(layout, title="Bildschirm-Datenvolumen", accent=C["green"],
                      subtitle="Pixel, Farbtiefe, Datenrate")
        screen.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(16, 0))

        screen_grid = transparent_frame(screen.body)
        screen_grid.pack(anchor="w", fill="x")
        make_label(screen_grid, "Breite (Pixel)", font=F["small"],
                   fg=C["text_dim"]).grid(row=0, column=0, sticky="w", pady=4)
        self.entry_width = EntryBox(screen_grid, width=8, value="1920")
        self.entry_width.grid(row=0, column=1, sticky="w", padx=12, pady=4)
        make_label(screen_grid, "Höhe (Pixel)", font=F["small"],
                   fg=C["text_dim"]).grid(row=1, column=0, sticky="w", pady=4)
        self.entry_height = EntryBox(screen_grid, width=8, value="1080")
        self.entry_height.grid(row=1, column=1, sticky="w", padx=12, pady=4)
        make_label(screen_grid, "Bildwiederholrate (fps, optional)",
                   font=F["small"], fg=C["text_dim"]).grid(
                       row=0, column=2, sticky="w", padx=(24, 0), pady=4)
        self.entry_fps = EntryBox(screen_grid, width=8, value="0")
        self.entry_fps.grid(row=0, column=3, sticky="w", padx=12, pady=4)
        self.entry_fps.entry.bind("<Return>", lambda _e: self.calc_screen())

        make_label(screen.body, "Farbtiefe", font=F["small"],
                   fg=C["text_dim"]).pack(anchor="w", pady=(14, 0))
        self.depth_pills = PillGroup(screen.body, COLOR_DEPTHS, initial=2)
        self.depth_pills.pack(anchor="w", pady=(8, 12))

        NeoButton(screen.body, "Berechnen", self.calc_screen,
                  kind="accent").pack(anchor="w")
        self.txt_screen = make_text(screen.body, height=8, readonly=True,
                                    font=F["mono_small"])
        self.txt_screen.pack(fill="both", expand=True, pady=(14, 0))
        self._build_info_toggle(screen.body, "screen", CALC_EXPLAIN_SCREEN)

        set_text(self.txt_subnet, "Noch keine Berechnung durchgeführt.")
        set_text(self.txt_raid, "Noch keine Berechnung durchgeführt.")
        set_text(self.txt_screen, "Noch keine Berechnung durchgeführt.")

    def _build_info_toggle(self, parent, key, explanation):
        """Baut den 'Rechenweg anzeigen'-Knopf samt (zunaechst
        ausgeblendeter) Erklaerungsbox fuer einen Praxis-Rechner."""
        controls = transparent_frame(parent)
        controls.pack(fill="x", pady=(10, 0))
        button = NeoButton(controls, "Rechenweg anzeigen",
                           lambda: self.toggle_info(key), kind="ghost")
        button.pack(anchor="w")
        self.info_buttons[key] = button

        # Waechst mit, falls Zeilen bei schmalem Fenster umbrechen
        lines = explanation.count("\n") + 1
        info_text = make_autogrow_text(parent, min_height=lines,
                                       max_height=lines * 2, font=F["mono_small"])
        set_text(info_text, explanation)
        info_text.configure(state="disabled")
        self.info_frames[key] = info_text

    def toggle_info(self, key):
        visible = not self.info_visible[key]
        self.info_visible[key] = visible
        button = self.info_buttons[key]
        frame = self.info_frames[key]
        if visible:
            frame.pack(fill="x", pady=(10, 0))
            button.set_text("Rechenweg ausblenden")
        else:
            frame.pack_forget()
            button.set_text("Rechenweg anzeigen")

    def calc_subnet(self):
        try:
            set_text(self.txt_subnet, subnet_report(self.entry_ip.get()))
        except InputError as error:
            messagebox.showerror("Ungültige Eingabe", str(error))

    def calc_raid(self):
        try:
            set_text(self.txt_raid, raid_report(self.raid_pills.get(),
                                                self.entry_disks.get(),
                                                self.entry_size.get()))
        except InputError as error:
            messagebox.showerror("Ungültige Eingabe", str(error))

    def calc_screen(self):
        try:
            set_text(self.txt_screen, screen_report(self.entry_width.get(),
                                                    self.entry_height.get(),
                                                    self.depth_pills.get(),
                                                    self.entry_fps.get()))
        except InputError as error:
            messagebox.showerror("Ungültige Eingabe", str(error))


# ============================================================================
#  LERNFORTSCHRITT
# ============================================================================

class ProgressView(View):
    def build(self):
        row = transparent_frame(self.content)
        row.pack(fill="x")
        self.stat_tests = self._stat_card(row, "Test-Sessions", C["cyan"])
        self.stat_avg = self._stat_card(row, "Durchschnitt", C["purple"])
        self.stat_best = self._stat_card(row, "Bestes Ergebnis", C["pink"])
        self.stat_streak = self._stat_card(row, "Lernserie", C["green"], last=True)

        chart_card = Card(self.content, title="Ergebnisse im Zeitverlauf",
                          subtitle="Erfolgsquote je Session")
        chart_card.pack(fill="x", pady=(14, 0))
        self.chart = LineChart(chart_card.body, height=220, parent_bg=C["card"])
        self.chart.pack(fill="both", expand=True)

        table_card = Card(self.content, title="Historie der Prüfungssessions",
                          accent=C["purple"])
        table_card.pack(fill="x", pady=(14, 0))
        columns = ("datum", "score", "prozent", "note", "dauer")
        self.tree = ttk.Treeview(table_card.body, columns=columns, show="headings",
                                 height=9, style="Dash.Treeview")
        headings = [("datum", "Datum & Uhrzeit", 170), ("score", "Ergebnis", 110),
                    ("prozent", "Erfolgsquote", 110), ("note", "IHK-Note", 150),
                    ("dauer", "Dauer", 90)]
        for key, text, width in headings:
            self.tree.heading(key, text=text)
            self.tree.column(key, width=px(width), anchor="center")
        scroll = ctk.CTkScrollbar(table_card.body, orientation="vertical",
                                  command=self.tree.yview,
                                  button_color=C["scrollbar"],
                                  button_hover_color=C["scrollbar_hi"])
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y", padx=(6, 0))

        controls = transparent_frame(self.content)
        controls.pack(fill="x", pady=(14, 0))
        NeoButton(controls, "Aktualisieren", self.refresh,
                  kind="ghost").pack(side="left")
        NeoButton(controls, "Historie löschen", self.clear_history,
                  kind="danger").pack(side="right")

    def _stat_card(self, parent, title, color, last=False):
        card = Card(parent, title=title, accent=color)
        card.pack(side="left", fill="both", expand=True,
                  padx=(0, 0) if last else (0, 12))
        label = make_label(card.body, "-", font=F["h1"], fg=C["text"])
        label.pack(anchor="w")
        sub = make_label(card.body, "", font=F["tiny"], fg=C["muted"])
        sub.pack(anchor="w", pady=(4, 0))
        return label, sub

    def on_show(self):
        self.refresh()

    def refresh(self):
        results = self.db.get_all_results()
        count, average = self.db.get_stats()

        self.stat_tests[0].configure(text=str(count))
        self.stat_tests[1].configure(text="abgeschlossene Sessions")
        self.stat_avg[0].configure(text="%.1f %%" % average)
        self.stat_avg[1].configure(text="über alle Sessions")

        if results:
            best = max(row[3] for row in results)
            self.stat_best[0].configure(text="%.1f %%" % best)
            self.stat_best[1].configure(text=ihk_note(best))
        else:
            self.stat_best[0].configure(text="-")
            self.stat_best[1].configure(text="noch keine Session")

        streak = self.db.streak()
        self.stat_streak[0].configure(text="%d" % streak)
        self.stat_streak[1].configure(text="Tage in Folge")

        ordered = list(reversed(results))[-20:]
        labels = [row[0][5:10].replace("-", ".") for row in ordered]
        values = [row[3] for row in ordered]
        if not labels:
            labels, values = ["heute"], [0]
        self.chart.set_data(labels, [
            {"name": "Erfolgsquote in %", "values": values, "color": C["pink"]},
        ], y_max=100)

        for item in self.tree.get_children():
            self.tree.delete(item)
        for timestamp, score, total, percentage, note, duration in results:
            self.tree.insert("", "end", values=(
                timestamp,
                "%d / %d" % (score, total),
                "%.1f %%" % percentage,
                note,
                "%02d:%02d min" % (duration // 60, duration % 60),
            ))

    def clear_history(self):
        if messagebox.askyesno("Historie löschen",
                               "Wirklich alle gespeicherten Testergebnisse "
                               "löschen?\n\nDie Lern-Ereignisse für das "
                               "Dashboard bleiben erhalten."):
            if self.db.clear_history():
                self.refresh()
                self.app.notify_progress()


# ============================================================================
#  EINSTELLUNGEN
# ============================================================================

class SettingsView(View):
    def build(self):
        info = Card(self.content, title="Datenbank", accent=C["cyan"])
        info.pack(fill="x")
        make_label(info.body, "Speicherort der Lernfortschritte:",
                   font=F["small"], fg=C["text_dim"]).pack(anchor="w")
        path_box = make_text(info.body, height=2, font=F["mono_small"])
        path_box.pack(fill="x", pady=(8, 0))
        set_text(path_box, self.db.db_path)
        path_box.configure(state="disabled")
        make_label(info.body,
                   "Der Pfad lässt sich über die Umgebungsvariable "
                   "FISI_DB_PATH überschreiben, zum Beispiel um die Datenbank "
                   "auf einem Netzlaufwerk abzulegen.",
                   font=F["tiny"], fg=C["muted"], wraplength=800,
                   justify="left", anchor="w").pack(anchor="w", pady=(8, 0))

        content = Card(self.content, title="Lerninhalte", accent=C["purple"])
        content.pack(fill="x", pady=(14, 0))
        totals = content_totals()
        lines = ["Karteikarten gesamt: %d" % len(KARTEIKARTEN),
                 "Quizfragen gesamt: %d" % len(QUIZ_QUESTIONS),
                 "AP1-Szenarien gesamt: %d" % len(AP1_SZENARIEN),
                 "AP2-Szenarien gesamt: %d" % len(SZENARIEN),
                 ""]
        for category in CATEGORIES:
            lines.append("%s: %d Inhalte" % (CATEGORY_SHORT[category],
                                             totals.get(category, 0)))
        make_label(content.body, "\n".join(lines), font=F["body"],
                   fg=C["text_dim"], justify="left", anchor="w").pack(anchor="w")

        danger = Card(self.content, title="Daten zurücksetzen", accent=C["red"])
        danger.pack(fill="x", pady=(14, 0))
        make_label(danger.body,
                   "Setzt sämtliche Lernfortschritte zurück: Testergebnisse, "
                   "Karteikarten-Verlauf, Quiz-Antworten und bearbeitete "
                   "Szenarien. Dieser Schritt lässt sich nicht rückgängig machen.",
                   font=F["small"], fg=C["text_dim"], wraplength=800,
                   justify="left", anchor="w").pack(anchor="w")
        NeoButton(danger.body, "Alle Lerndaten löschen", self.reset_all,
                  kind="danger").pack(anchor="w", pady=(12, 0))

        about = Card(self.content, title="Über das Programm", accent=C["green"])
        about.pack(fill="x", pady=(14, 0))
        make_label(about.body,
                   "%s Version %s\n\n"
                   "Lernprogramm für die Umschulung zum Fachinformatiker "
                   "Systemintegration mit Karteikarten, Prüfungstrainer, "
                   "AP1-/AP2-Szenarien, Testprojekten und Praxis-Rechnern.\n\n"
                   "Umgesetzt mit Python und CustomTkinter. Die Installer für "
                   "Windows, Linux und macOS bringen alles Nötige mit - es muss "
                   "nichts zusätzlich installiert werden."
                   % (APP_TITLE, APP_VERSION),
                   font=F["body"], fg=C["text_dim"], wraplength=800,
                   justify="left", anchor="w").pack(anchor="w")

    def reset_all(self):
        if not messagebox.askyesno("Alles zurücksetzen",
                                   "Wirklich ALLE Lerndaten unwiderruflich "
                                   "löschen?"):
            return
        if self.db.reset_all():
            messagebox.showinfo("Zurückgesetzt",
                                "Alle Lerndaten wurden gelöscht.")
            self.app.notify_progress()


# ============================================================================
#  SUCHE
# ============================================================================

class SearchView(View):
    def build(self):
        self.header_card = Card(self.content, title="Suchergebnisse",
                                accent=C["cyan"])
        self.header_card.pack(fill="x")
        self.lbl_info = make_label(self.header_card.body, "", font=F["body"],
                                   fg=C["text_dim"])
        self.lbl_info.pack(anchor="w")

        self.results_box = transparent_frame(self.content)
        self.results_box.pack(fill="both", expand=True, pady=(14, 0))

    def search(self, query):
        for child in self.results_box.winfo_children():
            child.destroy()

        hits = search_content(query)
        self.lbl_info.configure(text='%d Treffer für "%s"' % (len(hits), query))
        if not hits:
            make_label(self.results_box,
                       "Keine Treffer. Versuche einen anderen Suchbegriff.",
                       font=F["body"], fg=C["muted"]).pack(anchor="w")
            return

        for kind, category, title, detail in hits[:60]:
            self._result_row(kind, category, title, detail)
        if len(hits) > 60:
            make_label(self.results_box,
                       "... weitere %d Treffer nicht angezeigt." % (len(hits) - 60),
                       font=F["small"], fg=C["muted"]).pack(anchor="w", pady=8)

    def _result_row(self, kind, category, title, detail):
        row, marker, inner = clickable_row(
            self.results_box, CATEGORY_COLOR.get(category, C["purple"]),
            bg=C["card"])
        row.pack(fill="x", pady=4)

        head = ctk.CTkLabel(inner, text="%s · %s" % (kind, CATEGORY_SHORT.get(category, "")),
                            text_color=C["muted"], font=F["tiny"], anchor="w",
                            height=0, cursor="hand2")
        head.pack(anchor="w")
        title_label = ctk.CTkLabel(inner, text=title, text_color=C["text"],
                                   font=F["body_bold"], anchor="w", justify="left",
                                   wraplength=800, height=0, cursor="hand2")
        title_label.pack(anchor="w", pady=(2, 0))
        snippet = detail if len(detail) <= 140 else detail[:138] + "…"
        detail_label = ctk.CTkLabel(inner, text=snippet, text_color=C["text_dim"],
                                    font=F["small"], anchor="w", justify="left",
                                    wraplength=800, height=0, cursor="hand2")
        detail_label.pack(anchor="w", pady=(4, 0))

        def open_hit(_event=None):
            self.app.open_search_hit(kind, title)

        bind_click((row, inner, head, title_label, detail_label, marker), open_hit)
        for widget in (row, inner, head, title_label, detail_label, marker):
            widget.bind("<Enter>", lambda _e: row.configure(border_color=C["border_hi"]))
            widget.bind("<Leave>", lambda _e: row.configure(border_color=C["border"]))


# ============================================================================
#  HAUPTANWENDUNG
# ============================================================================

def _apply_window_icon(root):
    """Setzt das Programm-Icon (icon.ico bzw. icon.png) fuer Titelleiste
    und Taskleiste, falls die Datei vorhanden ist. Schlaegt nie fehl, auch
    wenn die Datei fehlt oder das Format auf der jeweiligen Plattform nicht
    unterstuetzt wird - dann bleibt einfach das Standard-Icon."""
    try:
        ico_path = _resource_path("icon.ico")
        if sys.platform == "win32" and os.path.exists(ico_path):
            root.iconbitmap(ico_path)
            return
    except tk.TclError:
        pass
    try:
        png_path = _resource_path("icon.png")
        if os.path.exists(png_path):
            icon_image = tk.PhotoImage(file=png_path)
            root.iconphoto(True, icon_image)
            root._icon_image_ref = icon_image  # Referenz halten, sonst Garbage Collection
    except tk.TclError:
        pass


class FISIApp:
    def __init__(self, root):
        self.root = root
        root.title("%s %s" % (APP_TITLE, APP_VERSION))
        root.geometry("1360x880")
        root.minsize(1120, 720)
        root.configure(fg_color=C["bg"])
        _apply_window_icon(root)

        setup_fonts(root)
        self._setup_ttk_style()

        self.db = DBManager(error_handler=self._db_error)

        container = ctk.CTkFrame(root, fg_color=C["bg"], corner_radius=0)
        container.pack(fill="both", expand=True)

        self.sidebar = Sidebar(container, self)
        self.sidebar.pack(side="left", fill="y")

        main = transparent_frame(container)
        main.pack(side="left", fill="both", expand=True)

        self.header = Header(main, self)
        self.header.pack(fill="x")

        self.view_area = tk.Frame(main, bg=C["bg"])
        self.view_area.pack(fill="both", expand=True)
        self.view_area.rowconfigure(0, weight=1)
        self.view_area.columnconfigure(0, weight=1)

        self.views = {}
        for key, cls in (("dashboard", DashboardView), ("cards", CardsView),
                         ("quiz", QuizView), ("ap1scenarios", Ap1ScenarioView),
                         ("scenarios", ScenarioView),
                         ("testproject", ProjectView),
                         ("calc", CalcView), ("progress", ProgressView),
                         ("settings", SettingsView), ("search", SearchView)):
            view = cls(self.view_area, self)
            view.grid(row=0, column=0, sticky="nsew")
            self.views[key] = view

        self.current = None
        self.show_view("dashboard")
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.bind("<Control-f>", lambda _e: self.header.search_entry.focus_set())

    # -- Infrastruktur ------------------------------------------------------

    def _db_error(self, message):
        messagebox.showerror("Datenbankfehler", message)

    def _setup_ttk_style(self):
        """Nur noch fuer die Tabelle im Lernfortschritt - CustomTkinter hat
        kein eigenes Tabellen-Widget."""
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Dash.Treeview",
                        background=C["card_alt"], fieldbackground=C["card_alt"],
                        foreground=C["text"], rowheight=px(32), borderwidth=0,
                        relief="flat", font=tk_font(F["small"]),
                        bordercolor=C["border"], lightcolor=C["card_alt"],
                        darkcolor=C["card_alt"])
        # Der Rahmen, den das Theme clam um die Tabelle zeichnet, wuerde hell
        # aufblitzen - deshalb wird er aus dem Layout entfernt.
        try:
            style.layout("Dash.Treeview", [
                ("Treeview.padding", {"sticky": "nswe", "children": [
                    ("Treeview.treearea", {"sticky": "nswe"})]}),
            ])
        except tk.TclError:
            pass
        style.configure("Dash.Treeview.Heading",
                        background=C["card_hi"], foreground=C["text_dim"],
                        font=tk_font(F["small_bold"]), relief="flat",
                        borderwidth=0, padding=(0, px(6)))
        style.map("Dash.Treeview.Heading",
                  background=[("active", C["violet"])],
                  foreground=[("active", "#FFFFFF")])
        style.map("Dash.Treeview",
                  background=[("selected", mix(C["card_alt"], C["purple"], 0.45))],
                  foreground=[("selected", "#FFFFFF")])

    # -- Navigation ---------------------------------------------------------

    def show_view(self, key):
        view = self.views.get(key)
        if view is None:
            return
        view.tkraise()
        view.to_top()
        self.current = key
        main, sub = VIEW_TITLES.get(key, ("FISI", ""))
        self.header.set_crumbs(main, sub)
        # Die Suche hat keinen eigenen Menuepunkt - dann bleibt nichts markiert.
        self.sidebar.set_active(key)
        view.on_show()
        self.notify_progress(refresh_view=False)

    def open_cards(self, category):
        self.views["cards"].set_category(category)
        self.show_view("cards")

    def do_search(self, query):
        self.views["search"].search(query)
        self.show_view("search")

    def open_search_hit(self, kind, title):
        if kind == "Karteikarte":
            self.show_view("cards")
            self.views["cards"].jump_to_question(title)
        elif kind == "Quizfrage":
            self.show_view("quiz")
            self.views["quiz"].jump_to_question(title)
        elif kind == "AP1-Szenario":
            self.show_view("ap1scenarios")
            for position, scenario in enumerate(AP1_SZENARIEN):
                if scenario["title"] == title:
                    self.views["ap1scenarios"].load_scenario(position)
                    break
        else:
            self.show_view("scenarios")
            for position, scenario in enumerate(SZENARIEN):
                if scenario["title"] == title:
                    self.views["scenarios"].load_scenario(position)
                    break

    def notify_progress(self, refresh_view=True):
        """Aktualisiert die Statusanzeige der Seitenleiste."""
        totals = content_totals()
        total = sum(totals.values())
        learned = self.db.distinct_cards_learned() + self.db.distinct_quiz_questions()
        self.sidebar.update_status(self.db.streak(), learned, total)
        if refresh_view and self.current == "dashboard":
            self.views["dashboard"].refresh()

    def on_close(self):
        quiz = self.views.get("quiz")
        if quiz is not None:
            quiz.stop_timer()
        self.root.destroy()


def _run_selftest(root, app, log_path):
    """Automatischer Starttest nach dem Build (siehe build.py): oeffnet jede
    Ansicht einmal, fuehrt eine Suche aus und beendet das Programm wieder.
    Fehler landen in log_path; main() meldet sie ueber den Exit-Code."""
    failures = []

    def record(*exc_info):
        failures.append("".join(traceback.format_exception(*exc_info)))

    root.report_callback_exception = record

    def step(keys):
        if not keys:
            with open(log_path, "w", encoding="utf-8") as handle:
                handle.write("\n".join(failures) if failures else "OK")
            root.destroy()
            return
        try:
            if keys[0] == "search":
                app.do_search("raid")
            else:
                app.show_view(keys[0])
        except Exception:
            failures.append(traceback.format_exc())
        root.after(250, step, keys[1:])

    root.after(1000, step, list(app.views))
    return failures


def main():
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    app = FISIApp(root)
    selftest_log = os.environ.get("FISI_SELFTEST")
    failures = _run_selftest(root, app, selftest_log) if selftest_log else None
    root.mainloop()
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
