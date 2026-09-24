#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FISI Lernplattform - Dashboard Edition
======================================

Lernprogramm fuer die Umschulung zum Fachinformatiker Systemintegration.

Start:      python3 app_gui.py
Benoetigt:  Python 3.8 oder neuer mit Tkinter (Standardbibliothek)

Die Oberflaeche besteht aus einer festen Seitenleiste, einer Kopfzeile mit
Suche und einem Inhaltsbereich, in dem die einzelnen Ansichten umgeschaltet
werden. Alle Lernaktivitaeten werden in einer lokalen SQLite-Datenbank
protokolliert und im Dashboard ausgewertet.
"""

import ipaddress
import os
import random
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fisi_core import (  # noqa: E402
    AP2_THEMES, CATEGORIES, CATEGORY_COLOR, CATEGORY_SHORT,
    C, DBManager, KARTEIKARTEN, PROJEKTARBEITEN, QUIZ_QUESTIONS, SZENARIEN,
    content_totals, ihk_note, mix, theme_totals,
)
from fisi_widgets import (  # noqa: E402
    Card, CalendarPanel, GradientBar, Heatmap, IconButton, LineChart, MiniRing,
    NeoButton, OptionList, RingStat, ScrollArea, ThemeTimeline, F,
    draw_icon, make_label, make_text, set_text, setup_fonts,
)

APP_TITLE = "FISI Lernplattform"
# Solange es keine Vollversion (1.0) gibt, wird hier nur die Zahl hinter dem
# Punkt bei jedem Update erhoeht (0.4 -> 0.5 -> 0.6 -> ...).
APP_VERSION = "0.4"

NAV_ITEMS = [
    ("dashboard", "grid", "Dashboard", None),
    ("cards", "cards", "Karteikarten", CATEGORIES),
    ("quiz", "target", "Prüfungstrainer", None),
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
    "scenarios": ("LERNEN", "AP2 SZENARIEN"),
    "testproject": ("LERNEN", "TEST PROJEKT"),
    "calc": ("WERKZEUGE", "PRAXIS-RECHNER"),
    "progress": ("AUSWERTUNG", "LERNFORTSCHRITT"),
    "settings": ("SYSTEM", "EINSTELLUNGEN"),
    "search": ("SUCHE", "ERGEBNISSE"),
}


# ============================================================================
#  KLEINE EINGABEFELDER
# ============================================================================

class EntryBox(tk.Frame):
    """Dunkles Eingabefeld mit Rahmen und Innenabstand."""

    def __init__(self, parent, width=18, value="", font=None):
        super().__init__(parent, bg=C["card_alt"], highlightthickness=1,
                         highlightbackground=C["border"],
                         highlightcolor=C["purple"], bd=0)
        self.entry = tk.Entry(self, bg=C["card_alt"], fg=C["text"],
                              insertbackground=C["cyan"], relief="flat",
                              font=font or F["body"], width=width,
                              highlightthickness=0, bd=0,
                              selectbackground=C["purple"])
        self.entry.pack(fill="x", padx=10, pady=8)
        if value:
            self.entry.insert(0, value)

    def get(self):
        return self.entry.get()

    def set(self, value):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, str(value))


class NumberStepper(tk.Frame):
    """Zahlenfeld mit Plus- und Minus-Knopf."""

    def __init__(self, parent, value=10, minimum=1, maximum=100, step=5, bg=None):
        self.bg = bg or C["card"]
        super().__init__(parent, bg=self.bg)
        self.value = value
        self.minimum = minimum
        self.maximum = maximum
        self.step = step

        IconButton(self, "minus", lambda: self._change(-self.step),
                   parent_bg=self.bg).pack(side="left")
        self.label = tk.Label(self, text=str(value), bg=C["card_alt"],
                              fg=C["text"], font=F["body_bold"], width=5,
                              pady=6)
        self.label.pack(side="left", padx=6)
        IconButton(self, "plus", lambda: self._change(self.step),
                   parent_bg=self.bg).pack(side="left")

    def _change(self, delta):
        self.value = max(self.minimum, min(self.maximum, self.value + delta))
        self.label.config(text=str(self.value))

    def get(self):
        return self.value

    def set_maximum(self, maximum):
        self.maximum = max(1, maximum)
        self._change(0)


class PillGroup(tk.Frame):
    """Gruppe sich gegenseitig ausschliessender Auswahlknoepfe."""

    def __init__(self, parent, options, on_change=None, bg=None, initial=0):
        self.bg = bg or C["card"]
        super().__init__(parent, bg=self.bg)
        self.on_change = on_change
        self.buttons = []
        self.values = []
        for index, (value, label) in enumerate(options):
            button = NeoButton(self, label, kind="pill", height=32, radius=16,
                               font=F["small_bold"], parent_bg=self.bg,
                               command=lambda i=index: self.select(i))
            button.pack(side="left", padx=(0, 6))
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


# ============================================================================
#  SEITENLEISTE
# ============================================================================

class NavRow(tk.Frame):
    """Eine Zeile in der Seitenleiste."""

    def __init__(self, parent, icon, text, command, sub=False, expandable=False):
        bg = C["sidebar"]
        super().__init__(parent, bg=bg, cursor="hand2")
        self.command = command
        self.active = False
        self.sub = sub

        self.accent = tk.Frame(self, bg=bg, width=3)
        self.accent.pack(side="left", fill="y")

        inner = tk.Frame(self, bg=bg)
        inner.pack(side="left", fill="both", expand=True)
        self.inner = inner

        pad_left = 26 if sub else 14
        self.icon = icon
        self.icon_canvas = None
        if icon:
            box = 20 if sub else 22
            self.icon_canvas = tk.Canvas(inner, width=box, height=box, bg=bg,
                                         highlightthickness=0, bd=0,
                                         cursor="hand2")
            self.icon_canvas.pack(side="left", padx=(pad_left, 8), pady=9)
            self._paint_icon(C["muted"])
            text_pad = 0
        else:
            text_pad = pad_left

        self.text_label = tk.Label(inner, text=text, bg=bg,
                                   fg=C["muted"] if sub else C["text_dim"],
                                   font=F["small"] if sub else F["nav"],
                                   anchor="w")
        self.text_label.pack(side="left", fill="x", expand=True,
                             padx=(text_pad, 8), pady=9)

        self.chevron = None
        self._expanded = False
        if expandable:
            self.chevron = tk.Canvas(inner, width=16, height=16, bg=bg,
                                     highlightthickness=0, bd=0, cursor="hand2")
            self.chevron.pack(side="right", padx=(0, 14))
            self._paint_chevron()

        for widget in self._widgets():
            widget.bind("<Button-1>", self._on_click)
            widget.bind("<Enter>", lambda _e: self._hover(True))
            widget.bind("<Leave>", lambda _e: self._hover(False))

    def _paint_icon(self, color):
        if not self.icon_canvas:
            return
        self.icon_canvas.delete("all")
        box = int(self.icon_canvas["width"])
        draw_icon(self.icon_canvas, self.icon, box / 2, box / 2,
                  box * (0.62 if self.sub else 0.72), color, width=2)

    def _paint_chevron(self):
        if not self.chevron:
            return
        self.chevron.delete("all")
        color = C["cyan"] if self.active else C["muted"]
        draw_icon(self.chevron, "chevron_up" if self._expanded else "chevron_down",
                  8, 8, 10, color, width=2)

    def _widgets(self):
        items = [self, self.inner, self.text_label]
        if self.icon_canvas:
            items.append(self.icon_canvas)
        if self.chevron:
            items.append(self.chevron)
        return items

    def _on_click(self, _event=None):
        if self.command:
            self.command()

    def _hover(self, flag):
        if self.active:
            return
        bg = C["card"] if flag else C["sidebar"]
        self._apply_bg(bg)
        self.text_label.configure(fg=C["text"] if flag else
                                  (C["muted"] if self.sub else C["text_dim"]))

    def _apply_bg(self, bg):
        self.configure(bg=bg)
        self.inner.configure(bg=bg)
        self.text_label.configure(bg=bg)
        if self.icon_canvas:
            self.icon_canvas.configure(bg=bg)
        if self.chevron:
            self.chevron.configure(bg=bg)

    def set_active(self, flag):
        self.active = flag
        if flag:
            self._apply_bg(C["card"])
            self.accent.configure(bg=C["cyan"])
            self.text_label.configure(fg=C["text"])
            self._paint_icon(C["cyan"])
        else:
            self._apply_bg(C["sidebar"])
            self.accent.configure(bg=C["sidebar"])
            self.text_label.configure(fg=C["muted"] if self.sub else C["text_dim"])
            self._paint_icon(C["muted"])
        self._paint_chevron()

    def set_expanded(self, flag):
        self._expanded = bool(flag)
        self._paint_chevron()


class Sidebar(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["sidebar"], width=232)
        self.app = app
        self.pack_propagate(False)
        self.rows = {}
        self.sub_frames = {}
        self.expanded = set()

        logo = tk.Frame(self, bg=C["sidebar"])
        logo.pack(fill="x", pady=(20, 18), padx=16)
        mark = tk.Canvas(logo, width=30, height=30, bg=C["sidebar"],
                         highlightthickness=0, bd=0)
        mark.pack(side="left")
        mark.create_oval(2, 2, 28, 28, outline=C["cyan"], width=2)
        mark.create_oval(9, 9, 21, 21, fill=C["pink"], outline="")
        tk.Label(logo, text="FISI", bg=C["sidebar"], fg=C["text"],
                 font=(F["family"], 16, "bold")).pack(side="left", padx=(10, 0))
        tk.Label(logo, text="Lernplattform", bg=C["sidebar"], fg=C["muted"],
                 font=F["tiny"]).pack(side="left", padx=(6, 0), pady=(6, 0))

        for key, icon, text, sub_items in NAV_ITEMS:
            expandable = bool(sub_items)
            row = NavRow(self, icon, text,
                         command=lambda k=key: self._on_nav(k),
                         expandable=expandable)
            row.pack(fill="x")
            self.rows[key] = row

            if sub_items:
                container = tk.Frame(self, bg=C["sidebar"])
                self.sub_frames[key] = container
                for item in sub_items:
                    sub_row = NavRow(container, CATEGORY_NAV_ICON.get(item, "dot"),
                                     CATEGORY_SHORT.get(item, item),
                                     command=lambda c=item: self.app.open_cards(c),
                                     sub=True)
                    sub_row.pack(fill="x")

        tk.Frame(self, bg=C["border"], height=1).pack(fill="x", pady=18, padx=16)
        tk.Label(self, text="LERNSTATUS", bg=C["sidebar"], fg=C["muted"],
                 font=F["label"], anchor="w").pack(fill="x", padx=18)

        self.streak_label = tk.Label(self, text="", bg=C["sidebar"],
                                     fg=C["text_dim"], font=F["small"],
                                     anchor="w", justify="left")
        self.streak_label.pack(fill="x", padx=18, pady=(10, 0))

        self.footer = tk.Label(self, text="Version %s" % APP_VERSION,
                               bg=C["sidebar"], fg=C["muted"], font=F["tiny"])
        self.footer.pack(side="bottom", pady=14)

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
            container.pack(fill="x", after=self.rows[key])
            self.expanded.add(key)
            self.rows[key].set_expanded(True)

    def set_active(self, key):
        for name, row in self.rows.items():
            row.set_active(name == key)

    def update_status(self, streak, learned, total):
        self.streak_label.config(
            text="Lernserie: %d Tag(e)\nInhalte bearbeitet: %d / %d"
                 % (streak, learned, total))


# ============================================================================
#  KOPFZEILE
# ============================================================================

class Header(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app

        left = tk.Frame(self, bg=C["bg"])
        left.pack(side="left", padx=(26, 0), pady=18)
        self.crumb_main = tk.Label(left, text="DASHBOARD", bg=C["bg"],
                                   fg=C["text"], font=F["label"])
        self.crumb_main.pack(side="left")
        self.crumb_sep = tk.Label(left, text="/", bg=C["bg"], fg=C["muted"],
                                  font=F["label"])
        self.crumb_sep.pack(side="left", padx=6)
        self.crumb_sub = tk.Label(left, text="HOME", bg=C["bg"], fg=C["muted"],
                                  font=F["label"])
        self.crumb_sub.pack(side="left")

        right = tk.Frame(self, bg=C["bg"])
        right.pack(side="right", padx=(0, 26), pady=14)

        search_box = tk.Frame(right, bg=C["card"], highlightthickness=1,
                              highlightbackground=C["border"],
                              highlightcolor=C["purple"], bd=0)
        search_box.pack(side="left", padx=(0, 14))
        search_icon = tk.Canvas(search_box, width=16, height=16, bg=C["card"],
                                highlightthickness=0, bd=0)
        search_icon.pack(side="left", padx=(12, 0))
        draw_icon(search_icon, "search", 8, 8, 12, C["muted"], width=2)
        self.search_entry = tk.Entry(search_box, bg=C["card"], fg=C["text"],
                                     insertbackground=C["cyan"], relief="flat",
                                     font=F["small"], width=26,
                                     highlightthickness=0, bd=0)
        self.search_entry.pack(side="left", padx=10, pady=9)
        self.search_entry.insert(0, "Suchen ...")
        self.search_entry.bind("<FocusIn>", self._clear_placeholder)
        self.search_entry.bind("<FocusOut>", self._restore_placeholder)
        self.search_entry.bind("<Return>", lambda _e: self._search())

    def _clear_placeholder(self, _event=None):
        if self.search_entry.get() == "Suchen ...":
            self.search_entry.delete(0, tk.END)

    def _restore_placeholder(self, _event=None):
        if not self.search_entry.get().strip():
            self.search_entry.insert(0, "Suchen ...")

    def _search(self):
        query = self.search_entry.get().strip()
        if query and query != "Suchen ...":
            self.app.do_search(query)

    def set_crumbs(self, main, sub):
        self.crumb_main.config(text=main)
        self.crumb_sub.config(text=sub)


# ============================================================================
#  BASISKLASSE FUER ANSICHTEN
# ============================================================================

class View(ScrollArea):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self.db = app.db
        self.content = tk.Frame(self.inner, bg=C["bg"])
        self.content.pack(fill="both", expand=True, padx=26, pady=(4, 26))
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

        # --- Reihe 1: Kennzahlen -----------------------------------------
        row1 = tk.Frame(self.content, bg=C["bg"])
        row1.pack(fill="x")

        self.ring_cards = self._ring_card(row1, "Karteikarten", "gelernt")
        self.ring_quiz = self._ring_card(row1, "Quizfragen", "beantwortet")
        self.ring_scen = self._ring_card(row1, "AP2 Szenarien", "bearbeitet")

        quote = Card(row1, title="Erfolgsquote", subtitle="Quiz gesamt",
                     accent=C["pink"])
        quote.pack(side="left", fill="both", expand=True, padx=6)
        self.lbl_quote = make_label(quote.body, "0 %", font=F["display"],
                                    fg=C["cyan"])
        self.lbl_quote.pack(anchor="w", pady=(6, 0))
        self.lbl_quote_sub = make_label(quote.body, "noch keine Antworten",
                                        font=F["small"], fg=C["muted"],
                                        justify="left", wraplength=180)
        self.lbl_quote_sub.pack(anchor="w", pady=(6, 0))

        cover = Card(row1, title="Abdeckung", subtitle="Material",
                     accent=C["purple"])
        cover.pack(side="left", fill="both", expand=True, padx=(6, 0))
        self.bar_cards = GradientBar(cover.body, "Karteikarten", C["cyan"],
                                     C["purple"], parent_bg=C["card"])
        self.bar_cards.pack(fill="x")
        self.bar_quiz = GradientBar(cover.body, "Quizfragen", C["purple"],
                                    C["pink"], parent_bg=C["card"])
        self.bar_quiz.pack(fill="x")
        self.bar_scen = GradientBar(cover.body, "Szenarien", C["pink"],
                                    C["orange"], parent_bg=C["card"])
        self.bar_scen.pack(fill="x")

        # --- Reihe 2: Verlauf und Heatmap --------------------------------
        row2 = tk.Frame(self.content, bg=C["bg"])
        row2.pack(fill="x", pady=(14, 0))
        row2.columnconfigure(0, weight=3, uniform="row2")
        row2.columnconfigure(1, weight=2, uniform="row2")

        chart_card = Card(row2, title="Lernverlauf",
                          subtitle="letzte %d Tage" % self.DAYS)
        chart_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.chart = LineChart(chart_card.body, height=230, parent_bg=C["card"])
        self.chart.pack(fill="both", expand=True)

        heat_card = Card(row2, title="Aktivität je Fachbereich",
                         subtitle="Intensität pro Tag", accent=C["pink"])
        heat_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.heatmap = Heatmap(heat_card.body, height=230, parent_bg=C["card"])
        self.heatmap.pack(fill="both", expand=True)

        # --- Reihe 3: Fachbereiche ---------------------------------------
        fach_card = Card(self.content, title="Fortschritt je Fachbereich",
                         subtitle="Abdeckung und Erfolgsquote", accent=C["green"])
        fach_card.pack(fill="x", pady=(14, 0))
        holder = tk.Frame(fach_card.body, bg=C["card"])
        holder.pack(fill="x")
        self.fach_rings = {}
        for category in CATEGORIES:
            column = tk.Frame(holder, bg=C["card"])
            column.pack(side="left", fill="both", expand=True)
            ring = MiniRing(column, size=86, thickness=8, parent_bg=C["card"])
            ring.pack()
            make_label(column, CATEGORY_SHORT[category], font=F["small_bold"],
                       fg=C["text"]).pack(pady=(8, 0))
            detail = make_label(column, "", font=F["tiny"], fg=C["muted"])
            detail.pack()
            self.fach_rings[category] = (ring, detail)

        # --- Reihe 4: Aktivitaeten, Kalender, Timeline --------------------
        row4 = tk.Frame(self.content, bg=C["bg"])
        row4.pack(fill="x", pady=(14, 0))
        row4.columnconfigure(0, weight=2, uniform="row4")
        row4.columnconfigure(1, weight=2, uniform="row4")
        row4.columnconfigure(2, weight=3, uniform="row4")

        act_card = Card(row4, title="Aktivitäten", subtitle="zuletzt")
        act_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.activity_box = tk.Frame(act_card.body, bg=C["card"])
        self.activity_box.pack(fill="both", expand=True)

        cal_card = Card(row4, title="Lerntage", subtitle="Monatsübersicht",
                        accent=C["purple"])
        cal_card.grid(row=0, column=1, sticky="nsew", padx=6)
        self.calendar = CalendarPanel(cal_card.body, bg=C["card"])
        self.calendar.pack(fill="both", expand=True)
        self.calendar.set_provider(self.db.month_activity)

        theme_card = Card(row4, title="AP2 Prüfungsthemen",
                          subtitle="bearbeitete Szenarien", accent=C["pink"])
        theme_card.grid(row=0, column=2, sticky="nsew", padx=(6, 0))
        self.timeline = ThemeTimeline(theme_card.body, height=200,
                                      parent_bg=C["card"])
        self.timeline.pack(fill="both", expand=True)

    def _ring_card(self, parent, title, subtitle):
        card = Card(parent, title=title, subtitle=subtitle)
        card.pack(side="left", fill="both", expand=True, padx=(0, 6))
        ring = RingStat(card.body, size=124, parent_bg=C["card"])
        ring.pack()
        return ring

    # -- Aktualisierung -----------------------------------------------------

    def on_show(self):
        self.calendar.to_current_month()
        self.refresh()

    def refresh(self):
        total_cards = len(KARTEIKARTEN)
        total_quiz = len(QUIZ_QUESTIONS)
        total_scen = len(SZENARIEN)

        learned_cards = self.db.distinct_cards_learned()
        quiz_answered = self.db.count_quiz_answers()
        quiz_distinct = self.db.distinct_quiz_questions()
        scen_done = self.db.distinct_scenarios()

        self.ring_cards.set(learned_cards / max(1, total_cards), C["cyan"],
                            C["purple"], str(learned_cards),
                            "von %d Karten" % total_cards)
        self.ring_quiz.set(quiz_distinct / max(1, total_quiz), C["purple"],
                           C["pink"], str(quiz_answered),
                           "%d von %d Fragen" % (quiz_distinct, total_quiz))
        self.ring_scen.set(scen_done / max(1, total_scen), C["pink"],
                           C["orange"], str(scen_done),
                           "von %d Szenarien" % total_scen)

        rate, correct, answered = self.db.quiz_success_rate()
        self.lbl_quote.config(text="%d %%" % round(rate))
        if answered:
            self.lbl_quote_sub.config(
                text="%d von %d Fragen richtig beantwortet" % (correct, answered))
        else:
            self.lbl_quote_sub.config(text="noch keine Antworten erfasst")

        self.bar_cards.set(learned_cards / max(1, total_cards) * 100,
                           "%d / %d" % (learned_cards, total_cards))
        self.bar_quiz.set(quiz_distinct / max(1, total_quiz) * 100,
                          "%d / %d" % (quiz_distinct, total_quiz))
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
                detail.config(text="%d Antworten · %d%% richtig"
                                   % (data["answered"], round(quota)))
            else:
                detail.config(text="noch nicht bearbeitet")

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
        self.timeline.set_data([(name, progress.get(name, 0.0), color)
                                for name, color in AP2_THEMES])

    def _activity_row(self, timestamp, kind, detail, extra):
        row = tk.Frame(self.activity_box, bg=C["card"])
        row.pack(fill="x", pady=3)
        color = {"Karteikarte": C["cyan"], "Quizfrage": C["purple"],
                 "AP2-Szenario": C["pink"], "Test-Session": C["green"]}.get(kind, C["muted"])
        dot = tk.Canvas(row, width=8, height=8, bg=C["card"],
                        highlightthickness=0, bd=0)
        dot.pack(side="left", padx=(0, 8), pady=6)
        dot.create_oval(1, 1, 7, 7, fill=color, outline="")

        text_box = tk.Frame(row, bg=C["card"])
        text_box.pack(side="left", fill="x", expand=True)
        short_detail = detail if len(str(detail)) <= 28 else str(detail)[:26] + "…"
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
        bar = tk.Frame(top.body, bg=C["card"])
        bar.pack(fill="x")

        make_label(bar, "FACHBEREICH", font=F["label"], fg=C["muted"]).pack(anchor="w")
        options = [("Alle", "Alle")] + [(c, CATEGORY_SHORT[c]) for c in CATEGORIES]
        self.cat_pills = PillGroup(bar, options, on_change=self._on_category,
                                   bg=C["card"])
        self.cat_pills.pack(anchor="w", pady=(8, 14))

        make_label(bar, "LERNMODUS", font=F["label"], fg=C["muted"]).pack(anchor="w")
        self.mode_pills = PillGroup(bar, self.MODES, on_change=self._on_mode,
                                    bg=C["card"])
        self.mode_pills.pack(anchor="w", pady=(8, 0))

        # Frage
        self.question_card = Card(self.content, title="Frage", accent=C["cyan"],
                                  subtitle="")
        self.question_card.pack(fill="x", pady=(14, 0))
        self.lbl_question = make_label(self.question_card.body, "",
                                       font=F["h2"], fg=C["text"],
                                       wraplength=900, justify="left")
        self.lbl_question.pack(anchor="w", pady=6)

        # Antwortbereich
        self.answer_card = Card(self.content, title="Deine Antwort",
                                accent=C["purple"])
        self.answer_card.pack(fill="both", expand=True, pady=(14, 0))

        # Fester Platzhalter fuer den Eingabebereich. Ohne diesen Container
        # wuerden spaeter eingeblendete Elemente unterhalb der Rueckmeldung
        # landen, weil Tk die Reihenfolge der pack-Aufrufe beibehaelt.
        self.input_area = tk.Frame(self.answer_card.body, bg=C["card"])
        self.input_area.pack(fill="x")

        self.frame_free = tk.Frame(self.input_area, bg=C["card"])
        make_label(self.frame_free,
                   "Formuliere deine Antwort in eigenen Worten:",
                   font=F["small"], fg=C["text_dim"]).pack(anchor="w")
        self.txt_answer = make_text(self.frame_free, height=5)
        self.txt_answer.pack(fill="x", pady=(8, 0))

        self.options = OptionList(self.input_area, bg=C["card"])

        self.frame_reveal = tk.Frame(self.input_area, bg=C["card"])
        make_label(self.frame_reveal,
                   "Überlege dir die Antwort und decke sie anschließend auf.",
                   font=F["small"], fg=C["text_dim"]).pack(anchor="w", pady=4)

        self.lbl_feedback = make_label(self.answer_card.body, "",
                                       font=F["body_bold"], fg=C["text"],
                                       wraplength=900, justify="left")
        self.lbl_feedback.pack(anchor="w", pady=(14, 0))
        self.lbl_solution = make_label(self.answer_card.body, "",
                                       font=F["body"], fg=C["text_dim"],
                                       wraplength=900, justify="left")
        self.lbl_solution.pack(anchor="w", pady=(6, 0))

        # Steuerung
        controls = tk.Frame(self.content, bg=C["bg"])
        controls.pack(fill="x", pady=(14, 0))
        self.btn_prev = NeoButton(controls, "Zurück", self.prev_card,
                                  kind="ghost", parent_bg=C["bg"],
                                  icon="arrow_left")
        self.btn_prev.pack(side="left")
        self.btn_check = NeoButton(controls, "Antwort prüfen", self.check_answer,
                                   kind="primary", parent_bg=C["bg"])
        self.btn_check.pack(side="left", padx=10)
        self.btn_next = NeoButton(controls, "Nächste Karte", self.next_card,
                                  kind="accent", parent_bg=C["bg"])
        self.btn_next.pack(side="left")
        self.lbl_counter = make_label(controls, "", font=F["body_bold"],
                                      fg=C["text_dim"], bg=C["bg"])
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
        self.lbl_feedback.config(text="")
        self.lbl_solution.config(text="")
        self.frame_free.pack_forget()
        self.options.pack_forget()
        self.frame_reveal.pack_forget()
        self.options.clear()

        if not self.filtered:
            self.lbl_question.config(text="Für diesen Fachbereich sind keine "
                                          "Karteikarten hinterlegt.")
            self.lbl_counter.config(text="0 / 0")
            self.btn_check.set_enabled(False)
            return

        self.btn_check.set_enabled(True)
        card = self.filtered[self.index]
        self.lbl_question.config(text=card["q"])
        self.lbl_counter.config(text="Karte %d / %d"
                                     % (self.index + 1, len(self.filtered)))
        self.question_card.set_subtitle(CATEGORY_SHORT[card["cat"]],
                                        CATEGORY_COLOR[card["cat"]])

        if self.mode == "freitext":
            self.frame_free.pack(fill="x")
            self.txt_answer.delete("1.0", tk.END)
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
            user_input = self.txt_answer.get("1.0", tk.END).strip()
            if not user_input:
                messagebox.showwarning("Hinweis", "Bitte gib zuerst deine Antwort ein.")
                return
            correct = card["a"].lower() in user_input.lower()
            if correct:
                self.lbl_feedback.config(text="Sehr gut - deine Antwort enthält "
                                              "die Kernlösung.", fg=C["green"])
            else:
                self.lbl_feedback.config(text="Vergleiche deine Eingabe mit der "
                                              "Musterlösung:", fg=C["yellow"])
            self.lbl_solution.config(text="Musterlösung: " + card["a_full"])

        elif self.mode == "mc":
            choice = self.options.get()
            if not choice:
                messagebox.showwarning("Hinweis", "Bitte wähle eine Antwort aus.")
                return
            correct = choice == card["a"]
            self.options.reveal(card["a"])
            if correct:
                self.lbl_feedback.config(text="Richtig beantwortet.", fg=C["green"])
            else:
                self.lbl_feedback.config(text="Leider falsch. Richtig wäre: "
                                              + card["a"], fg=C["red"])
            self.lbl_solution.config(text=card["a_full"])

        else:
            self.lbl_feedback.config(text="Musterlösung", fg=C["cyan"])
            self.lbl_solution.config(text=card["a_full"])

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
        self.cat_pills = PillGroup(body, options, on_change=self._on_category,
                                   bg=C["card"])
        self.cat_pills.pack(anchor="w", pady=(8, 14))

        row = tk.Frame(body, bg=C["card"])
        row.pack(anchor="w", fill="x")
        make_label(row, "Fragenanzahl", font=F["small"],
                   fg=C["text_dim"]).pack(side="left", padx=(0, 10))
        self.stepper = NumberStepper(row, value=10, minimum=5, maximum=len(self.questions),
                                     step=5, bg=C["card"])
        self.stepper.pack(side="left")
        self.btn_start = NeoButton(row, "Session starten", self.start_quiz,
                                   kind="primary", parent_bg=C["card"])
        self.btn_start.pack(side="left", padx=16)
        self.lbl_pool = make_label(row, "", font=F["small"], fg=C["muted"])
        self.lbl_pool.pack(side="left")

        # Statusleiste
        self.status_card = Card(self.content)
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
            font=F["h2"], fg=C["text"], wraplength=900, justify="left")
        self.lbl_question.pack(anchor="w", pady=(4, 12))

        self.options = OptionList(self.question_card.body, bg=C["card"])
        self.options.pack(fill="x")

        self.lbl_explain = make_label(self.question_card.body, "", font=F["body"],
                                      fg=C["text_dim"], wraplength=900,
                                      justify="left")
        self.lbl_explain.pack(anchor="w", pady=(12, 0))

        controls = tk.Frame(self.content, bg=C["bg"])
        controls.pack(fill="x", pady=(14, 0))
        self.btn_submit = NeoButton(controls, "Antwort einreichen",
                                    self.submit_answer, kind="primary",
                                    parent_bg=C["bg"])
        self.btn_submit.pack(side="left")
        self.btn_submit.set_enabled(False)
        self.btn_cancel = NeoButton(controls, "Session abbrechen",
                                    self.cancel_quiz, kind="ghost",
                                    parent_bg=C["bg"])
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
        self.lbl_pool.config(text="%d Fragen verfügbar" % len(self.pool))

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
        self.lbl_timer.config(text="%02d:%02d" % (elapsed // 60, elapsed % 60))
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
        self.lbl_question.config(text="%d. %s" % (self.index + 1, question["q"]))
        self.lbl_explain.config(text="")
        shuffled = list(question["options"])
        random.shuffle(shuffled)
        self.options.set_options(shuffled)
        self.lbl_progress.config(text="Frage %d / %d"
                                      % (self.index + 1, len(self.session)))
        self.lbl_score.config(text="%d richtig" % self.score)
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
        self.lbl_explain.config(text=prefix + question["exp"],
                                fg=C["green"] if correct else C["text_dim"])
        self.lbl_score.config(text="%d richtig" % self.score)
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
        self.lbl_question.config(text="Session abgebrochen. Du kannst jederzeit "
                                      "eine neue starten.")
        self.options.clear()
        self.lbl_explain.config(text="")

    def finish_quiz(self):
        self.stop_timer()
        total = len(self.session)
        percentage = (self.score / total) * 100 if total else 0.0
        elapsed = int(time.time() - self.start_time)
        note = ihk_note(percentage)
        saved = self.db.save_test_result(self.score, total, percentage, note, elapsed)

        self.options.clear()
        self.lbl_explain.config(text="")
        self._reset_controls()

        hint = ("Das Ergebnis wurde gespeichert."
                if saved else "Achtung: Das Ergebnis konnte nicht gespeichert werden.")
        self.lbl_question.config(
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
        self.lbl_progress.config(text="Frage 0 / 0")
        self.lbl_timer.config(text="00:00")

    def jump_to_question(self, question_text):
        for question in self.questions:
            if question["q"] == question_text:
                self.stop_timer()
                self._reset_controls()
                self.lbl_question.config(text=question["q"])
                self.options.set_options(list(question["options"]))
                self.options.reveal(question["a"])
                self.lbl_explain.config(text=question["exp"], fg=C["text_dim"])
                return


# ============================================================================
#  AP2 SZENARIEN
# ============================================================================

class ScenarioView(View):
    def build(self):
        self.index = 0
        self.solution_visible = False

        layout = tk.Frame(self.content, bg=C["bg"])
        layout.pack(fill="both", expand=True)
        layout.columnconfigure(0, weight=2, uniform="scen")
        layout.columnconfigure(1, weight=5, uniform="scen")

        list_card = Card(layout, title="Szenarien",
                         subtitle="%d Aufgaben" % len(SZENARIEN))
        list_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.list_box = tk.Frame(list_card.body, bg=C["card"])
        self.list_box.pack(fill="both", expand=True)
        self.list_rows = []
        for position, scenario in enumerate(SZENARIEN):
            self.list_rows.append(self._list_row(position, scenario))

        detail = tk.Frame(layout, bg=C["bg"])
        detail.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self.task_card = Card(detail, title="Aufgabenstellung", accent=C["cyan"])
        self.task_card.pack(fill="both", expand=True)
        self.lbl_title = make_label(self.task_card.body, "", font=F["h2"],
                                    fg=C["text"], wraplength=760, justify="left")
        self.lbl_title.pack(anchor="w", pady=(0, 10))
        self.txt_task = make_text(self.task_card.body, height=11, readonly=True)
        self.txt_task.pack(fill="both", expand=True)

        self.sol_card = Card(detail, title="Musterlösung", accent=C["green"])
        self.sol_card.pack(fill="both", expand=True, pady=(14, 0))
        self.txt_solution = make_text(self.sol_card.body, height=11, readonly=True)
        self.txt_solution.pack(fill="both", expand=True)

        controls = tk.Frame(detail, bg=C["bg"])
        controls.pack(fill="x", pady=(14, 0))
        self.btn_toggle = NeoButton(controls, "Musterlösung anzeigen",
                                    self.toggle_solution, kind="primary",
                                    parent_bg=C["bg"])
        self.btn_toggle.pack(side="left")
        NeoButton(controls, "Nächstes Szenario", self.next_scenario,
                  kind="ghost", parent_bg=C["bg"]).pack(side="left", padx=10)

        self.load_scenario(0)

    def _list_row(self, position, scenario):
        row = tk.Frame(self.list_box, bg=C["card_alt"], cursor="hand2",
                       highlightthickness=1, highlightbackground=C["border"])
        row.pack(fill="x", pady=4)
        marker = tk.Frame(row, bg=CATEGORY_COLOR[scenario["cat"]], width=3)
        marker.pack(side="left", fill="y")
        inner = tk.Frame(row, bg=C["card_alt"])
        inner.pack(side="left", fill="x", expand=True, padx=10, pady=9)
        title = tk.Label(inner, text="%d. %s" % (position + 1, scenario["title"]),
                         bg=C["card_alt"], fg=C["text"], font=F["small_bold"],
                         anchor="w", justify="left", wraplength=190)
        title.pack(anchor="w")
        theme = tk.Label(inner, text=scenario["theme"], bg=C["card_alt"],
                         fg=C["muted"], font=F["tiny"], anchor="w")
        theme.pack(anchor="w")
        for widget in (row, inner, title, theme, marker):
            widget.bind("<Button-1>", lambda _e, p=position: self.load_scenario(p))
        return {"frame": row, "inner": inner, "title": title, "theme": theme}

    def _highlight(self):
        for position, row in enumerate(self.list_rows):
            active = position == self.index
            bg = C["card_hi"] if active else C["card_alt"]
            row["frame"].configure(bg=bg,
                                   highlightbackground=C["purple"] if active else C["border"])
            row["inner"].configure(bg=bg)
            row["title"].configure(bg=bg, fg=C["text"] if active else C["text_dim"])
            row["theme"].configure(bg=bg)

    def load_scenario(self, position):
        self.index = position
        scenario = SZENARIEN[position]
        self.lbl_title.config(text=scenario["title"])
        set_text(self.txt_task, scenario["text"])
        self.solution_visible = False
        set_text(self.txt_solution,
                 "Die Musterlösung ist noch ausgeblendet.\n\n"
                 "Bearbeite die Aufgabe zuerst selbst und decke die Lösung "
                 "anschließend auf.")
        self.btn_toggle.set_text("Musterlösung anzeigen")
        self._highlight()

    def toggle_solution(self):
        scenario = SZENARIEN[self.index]
        if self.solution_visible:
            set_text(self.txt_solution, "Die Musterlösung ist ausgeblendet.")
            self.btn_toggle.set_text("Musterlösung anzeigen")
            self.solution_visible = False
        else:
            set_text(self.txt_solution, scenario["solution"])
            self.btn_toggle.set_text("Musterlösung ausblenden")
            self.solution_visible = True
            self.db.log_scenario(self.index, scenario["title"], scenario["theme"])
            self.app.notify_progress()

    def next_scenario(self):
        self.load_scenario((self.index + 1) % len(SZENARIEN))


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

        layout = tk.Frame(self.content, bg=C["bg"])
        layout.pack(fill="both", expand=True)
        layout.columnconfigure(0, weight=2, uniform="proj")
        layout.columnconfigure(1, weight=5, uniform="proj")

        list_card = Card(layout, title="Testprojekte",
                         subtitle="%d Kundenaufträge" % len(PROJEKTARBEITEN))
        list_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.list_box = tk.Frame(list_card.body, bg=C["card"])
        self.list_box.pack(fill="both", expand=True)
        self.list_rows = []
        for position, project in enumerate(PROJEKTARBEITEN):
            self.list_rows.append(self._list_row(position, project))

        detail = tk.Frame(layout, bg=C["bg"])
        detail.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self.header_label = make_label(detail, "", font=F["h2"], fg=C["text"],
                                       wraplength=760, justify="left")
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

        controls = tk.Frame(detail, bg=C["bg"])
        controls.pack(fill="x", pady=(14, 0))
        self.btn_toggle = NeoButton(controls, "Lösungsansätze anzeigen",
                                    self.toggle_hints, kind="primary",
                                    parent_bg=C["bg"])
        self.btn_toggle.pack(side="left")
        NeoButton(controls, "Nächstes Projekt", self.next_project,
                  kind="ghost", parent_bg=C["bg"]).pack(side="left", padx=10)

        self.load_project(0)

    def _list_row(self, position, project):
        row = tk.Frame(self.list_box, bg=C["card_alt"], cursor="hand2",
                       highlightthickness=1, highlightbackground=C["border"])
        row.pack(fill="x", pady=4)
        marker = tk.Frame(row, bg=CATEGORY_COLOR[project["cat"]], width=3)
        marker.pack(side="left", fill="y")
        inner = tk.Frame(row, bg=C["card_alt"])
        inner.pack(side="left", fill="x", expand=True, padx=10, pady=9)
        title = tk.Label(inner, text="%d. %s" % (position + 1, project["title"]),
                         bg=C["card_alt"], fg=C["text"], font=F["small_bold"],
                         anchor="w", justify="left", wraplength=190)
        title.pack(anchor="w")
        sub = tk.Label(inner, text="%s · %s" % (project["schwierigkeit"],
                                                 CATEGORY_SHORT[project["cat"]]),
                       bg=C["card_alt"], fg=C["muted"], font=F["tiny"], anchor="w")
        sub.pack(anchor="w")
        for widget in (row, inner, title, sub, marker):
            widget.bind("<Button-1>", lambda _e, p=position: self.load_project(p))
        return {"frame": row, "inner": inner, "title": title, "sub": sub}

    def _highlight(self):
        done = self.db.completed_projects()
        for position, row in enumerate(self.list_rows):
            active = position == self.index
            bg = C["card_hi"] if active else C["card_alt"]
            row["frame"].configure(bg=bg,
                                   highlightbackground=C["purple"] if active else C["border"])
            row["inner"].configure(bg=bg)
            mark = " ✓" if position in done else ""
            project = PROJEKTARBEITEN[position]
            row["title"].configure(
                bg=bg, fg=C["text"] if active else C["text_dim"],
                text="%d. %s%s" % (position + 1, project["title"], mark))
            row["sub"].configure(bg=bg)

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
        self.header_label.config(text=project["title"])
        self.meta_label.config(
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
    RAID_LEVELS = [("RAID 0", "RAID 0"), ("RAID 1", "RAID 1"), ("RAID 5", "RAID 5"),
                   ("RAID 6", "RAID 6"), ("RAID 10", "RAID 10")]

    def build(self):
        layout = tk.Frame(self.content, bg=C["bg"])
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
        NeoButton(subnet.body, "Berechnen", self.calc_subnet, kind="accent",
                  parent_bg=C["card"]).pack(anchor="w")
        self.txt_subnet = make_text(subnet.body, height=11, readonly=True)
        self.txt_subnet.configure(font=F["mono_small"])
        self.txt_subnet.pack(fill="both", expand=True, pady=(14, 0))

        # --- RAID ---------------------------------------------------------
        raid = Card(layout, title="RAID-Kapazität", accent=C["purple"],
                    subtitle="Netto, Parität, Effizienz")
        raid.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        make_label(raid.body, "RAID-Level", font=F["small"],
                   fg=C["text_dim"]).pack(anchor="w")
        self.raid_pills = PillGroup(raid.body, self.RAID_LEVELS, initial=2,
                                    bg=C["card"])
        self.raid_pills.pack(anchor="w", pady=(8, 12))

        grid = tk.Frame(raid.body, bg=C["card"])
        grid.pack(anchor="w", fill="x")
        make_label(grid, "Anzahl Festplatten", font=F["small"],
                   fg=C["text_dim"]).grid(row=0, column=0, sticky="w", pady=4)
        self.entry_disks = EntryBox(grid, width=8, value="4")
        self.entry_disks.grid(row=0, column=1, sticky="w", padx=12, pady=4)
        make_label(grid, "Kapazität je Platte (GB)", font=F["small"],
                   fg=C["text_dim"]).grid(row=1, column=0, sticky="w", pady=4)
        self.entry_size = EntryBox(grid, width=8, value="1000")
        self.entry_size.grid(row=1, column=1, sticky="w", padx=12, pady=4)

        NeoButton(raid.body, "Berechnen", self.calc_raid, kind="primary",
                  parent_bg=C["card"]).pack(anchor="w", pady=(12, 0))
        self.txt_raid = make_text(raid.body, height=11, readonly=True)
        self.txt_raid.configure(font=F["mono_small"])
        self.txt_raid.pack(fill="both", expand=True, pady=(14, 0))

        set_text(self.txt_subnet, "Noch keine Berechnung durchgeführt.")
        set_text(self.txt_raid, "Noch keine Berechnung durchgeführt.")

    def calc_subnet(self):
        value = self.entry_ip.get().strip()
        try:
            network = ipaddress.ip_network(value, strict=False)
        except ValueError:
            messagebox.showerror(
                "Ungültige Eingabe",
                "Bitte eine gültige Adresse angeben.\n\n"
                "Beispiele:\n  192.168.1.50/24\n  10.0.0.0/255.255.255.0\n"
                "  2001:db8::1/64")
            return

        if network.version == 4:
            hosts = network.num_addresses - 2 if network.prefixlen < 31 else \
                (2 if network.prefixlen == 31 else 1)
            host_list = list(network.hosts())
            first = host_list[0] if host_list else network.network_address
            last = host_list[-1] if host_list else network.broadcast_address
            lines = [
                "Netzwerk-Adresse      : %s" % network.network_address,
                "Subnetzmaske          : %s" % network.netmask,
                "Wildcard-Maske        : %s" % network.hostmask,
                "Broadcast-Adresse     : %s" % network.broadcast_address,
                "Erste Host-Adresse    : %s" % first,
                "Letzte Host-Adresse   : %s" % last,
                "Nutzbare Hosts        : %d" % hosts,
                "Adressen gesamt       : %d" % network.num_addresses,
                "CIDR-Präfix           : /%d" % network.prefixlen,
            ]
        else:
            lines = [
                "Netzwerk-Adresse      : %s" % network.network_address,
                "Präfixlänge           : /%d" % network.prefixlen,
                "Erste Adresse         : %s" % network.network_address,
                "Letzte Adresse        : %s" % network[-1],
                "Adressen gesamt       : %d" % network.num_addresses,
            ]
        set_text(self.txt_subnet, "\n".join(lines))

    def calc_raid(self):
        level = self.raid_pills.get()
        try:
            disks = int(self.entry_disks.get())
            size = float(self.entry_size.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Ungültige Eingabe",
                                 "Bitte gültige Zahlen für Anzahl und "
                                 "Kapazität eingeben.")
            return
        if disks <= 0 or size <= 0:
            messagebox.showerror("Ungültige Eingabe",
                                 "Anzahl und Kapazität müssen größer als 0 sein.")
            return

        rules = {
            "RAID 0": (1, lambda n, s: (n * s, 0)),
            "RAID 1": (2, lambda n, s: (s, n - 1)),
            "RAID 5": (3, lambda n, s: ((n - 1) * s, 1)),
            "RAID 6": (4, lambda n, s: ((n - 2) * s, 2)),
            "RAID 10": (4, lambda n, s: ((n / 2) * s, 1)),
        }
        minimum, formula = rules[level]
        if disks < minimum or (level == "RAID 10" and disks % 2 != 0):
            extra = " und eine gerade Anzahl" if level == "RAID 10" else ""
            set_text(self.txt_raid,
                     "Ungültige Konfiguration für %s.\n\n"
                     "Benötigt werden mindestens %d Festplatten%s."
                     % (level, minimum, extra))
            return

        netto, tolerance = formula(disks, size)
        brutto = disks * size
        loss = brutto - netto
        efficiency = (netto / brutto * 100) if brutto else 0
        set_text(self.txt_raid, "\n".join([
            "RAID-Level            : %s" % level,
            "Festplatten           : %d x %.0f GB" % (disks, size),
            "Bruttokapazität       : %.2f GB" % brutto,
            "Nutzkapazität         : %.2f GB" % netto,
            "Parität / Verlust     : %.2f GB" % loss,
            "Speichereffizienz     : %.1f %%" % efficiency,
            "Ausfalltoleranz       : %d Festplatte(n)" % tolerance,
        ]))


# ============================================================================
#  LERNFORTSCHRITT
# ============================================================================

class ProgressView(View):
    def build(self):
        row = tk.Frame(self.content, bg=C["bg"])
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
            self.tree.column(key, width=width, anchor="center")
        # Bewusst eine klassische tk-Scrollbar: die ttk-Variante laesst sich
        # nicht auf allen Systemen zuverlaessig dunkel einfaerben.
        scroll = tk.Scrollbar(table_card.body, orient="vertical",
                              command=self.tree.yview, bg=C["card_hi"],
                              troughcolor=C["card"], activebackground=C["purple"],
                              highlightthickness=0, bd=0, relief="flat", width=10)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        controls = tk.Frame(self.content, bg=C["bg"])
        controls.pack(fill="x", pady=(14, 0))
        NeoButton(controls, "Aktualisieren", self.refresh, kind="ghost",
                  parent_bg=C["bg"]).pack(side="left")
        NeoButton(controls, "Historie löschen", self.clear_history, kind="danger",
                  parent_bg=C["bg"]).pack(side="right")

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

        self.stat_tests[0].config(text=str(count))
        self.stat_tests[1].config(text="abgeschlossene Sessions")
        self.stat_avg[0].config(text="%.1f %%" % average)
        self.stat_avg[1].config(text="über alle Sessions")

        if results:
            best = max(row[3] for row in results)
            self.stat_best[0].config(text="%.1f %%" % best)
            self.stat_best[1].config(text=ihk_note(best))
        else:
            self.stat_best[0].config(text="-")
            self.stat_best[1].config(text="noch keine Session")

        streak = self.db.streak()
        self.stat_streak[0].config(text="%d" % streak)
        self.stat_streak[1].config(text="Tage in Folge")

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
        path_box = make_text(info.body, height=2)
        path_box.pack(fill="x", pady=(8, 0))
        set_text(path_box, self.db.db_path)
        path_box.configure(state="disabled", font=F["mono_small"])
        make_label(info.body,
                   "Der Pfad lässt sich über die Umgebungsvariable "
                   "FISI_DB_PATH überschreiben, zum Beispiel um die Datenbank "
                   "auf einem Netzlaufwerk abzulegen.",
                   font=F["tiny"], fg=C["muted"], wraplength=800,
                   justify="left").pack(anchor="w", pady=(8, 0))

        content = Card(self.content, title="Lerninhalte", accent=C["purple"])
        content.pack(fill="x", pady=(14, 0))
        totals = content_totals()
        lines = ["Karteikarten gesamt: %d" % len(KARTEIKARTEN),
                 "Quizfragen gesamt: %d" % len(QUIZ_QUESTIONS),
                 "AP2-Szenarien gesamt: %d" % len(SZENARIEN),
                 ""]
        for category in CATEGORIES:
            lines.append("%s: %d Inhalte" % (CATEGORY_SHORT[category],
                                             totals.get(category, 0)))
        make_label(content.body, "\n".join(lines), font=F["body"],
                   fg=C["text_dim"], justify="left").pack(anchor="w")

        danger = Card(self.content, title="Daten zurücksetzen", accent=C["red"])
        danger.pack(fill="x", pady=(14, 0))
        make_label(danger.body,
                   "Setzt sämtliche Lernfortschritte zurück: Testergebnisse, "
                   "Karteikarten-Verlauf, Quiz-Antworten und bearbeitete "
                   "Szenarien. Dieser Schritt lässt sich nicht rückgängig machen.",
                   font=F["small"], fg=C["text_dim"], wraplength=800,
                   justify="left").pack(anchor="w")
        NeoButton(danger.body, "Alle Lerndaten löschen", self.reset_all,
                  kind="danger", parent_bg=C["card"]).pack(anchor="w", pady=(12, 0))

        about = Card(self.content, title="Über das Programm", accent=C["green"])
        about.pack(fill="x", pady=(14, 0))
        make_label(about.body,
                   "%s Version %s\n\n"
                   "Lernprogramm für die Umschulung zum Fachinformatiker "
                   "Systemintegration mit Karteikarten, Prüfungstrainer, "
                   "AP2-Szenarien und Praxis-Rechnern.\n\n"
                   "Umgesetzt mit Python und Tkinter ohne externe "
                   "Abhängigkeiten - dadurch läuft das Programm unter Windows, "
                   "Linux und macOS gleichermaßen."
                   % (APP_TITLE, APP_VERSION),
                   font=F["body"], fg=C["text_dim"], wraplength=800,
                   justify="left").pack(anchor="w")

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

        self.results_box = tk.Frame(self.content, bg=C["bg"])
        self.results_box.pack(fill="both", expand=True, pady=(14, 0))

    def search(self, query):
        for child in self.results_box.winfo_children():
            child.destroy()

        needle = query.lower()
        hits = []
        for card in KARTEIKARTEN:
            if needle in card["q"].lower() or needle in card["a_full"].lower():
                hits.append(("Karteikarte", card["cat"], card["q"], card["a_full"]))
        for question in QUIZ_QUESTIONS:
            if needle in question["q"].lower() or needle in question["exp"].lower():
                hits.append(("Quizfrage", question["cat"], question["q"],
                             question["exp"]))
        for position, scenario in enumerate(SZENARIEN):
            haystack = scenario["title"] + scenario["text"] + scenario["solution"]
            if needle in haystack.lower():
                hits.append(("AP2-Szenario", scenario["cat"], scenario["title"],
                             scenario["text"].split("\n")[0]))

        self.lbl_info.config(text='%d Treffer für "%s"' % (len(hits), query))
        if not hits:
            make_label(self.results_box,
                       "Keine Treffer. Versuche einen anderen Suchbegriff.",
                       font=F["body"], fg=C["muted"], bg=C["bg"]).pack(anchor="w")
            return

        for kind, category, title, detail in hits[:60]:
            self._result_row(kind, category, title, detail)
        if len(hits) > 60:
            make_label(self.results_box,
                       "... weitere %d Treffer nicht angezeigt." % (len(hits) - 60),
                       font=F["small"], fg=C["muted"], bg=C["bg"]).pack(anchor="w",
                                                                       pady=8)

    def _result_row(self, kind, category, title, detail):
        row = tk.Frame(self.results_box, bg=C["card"], cursor="hand2",
                       highlightthickness=1, highlightbackground=C["border"])
        row.pack(fill="x", pady=4)
        marker = tk.Frame(row, bg=CATEGORY_COLOR.get(category, C["purple"]), width=3)
        marker.pack(side="left", fill="y")
        inner = tk.Frame(row, bg=C["card"])
        inner.pack(side="left", fill="x", expand=True, padx=14, pady=11)

        head = tk.Label(inner, text="%s · %s" % (kind, CATEGORY_SHORT.get(category, "")),
                        bg=C["card"], fg=C["muted"], font=F["tiny"], anchor="w")
        head.pack(anchor="w")
        title_label = tk.Label(inner, text=title, bg=C["card"], fg=C["text"],
                               font=F["body_bold"], anchor="w", justify="left",
                               wraplength=800)
        title_label.pack(anchor="w", pady=(2, 0))
        snippet = detail if len(detail) <= 140 else detail[:138] + "…"
        detail_label = tk.Label(inner, text=snippet, bg=C["card"], fg=C["text_dim"],
                                font=F["small"], anchor="w", justify="left",
                                wraplength=800)
        detail_label.pack(anchor="w", pady=(4, 0))

        def open_hit(_event=None):
            self.app.open_search_hit(kind, title)

        for widget in (row, inner, head, title_label, detail_label, marker):
            widget.bind("<Button-1>", open_hit)


# ============================================================================
#  HAUPTANWENDUNG
# ============================================================================

class FISIApp:
    def __init__(self, root):
        self.root = root
        root.title("%s %s" % (APP_TITLE, APP_VERSION))
        root.geometry("1360x880")
        root.minsize(1120, 720)
        root.configure(bg=C["bg"])

        setup_fonts(root)
        self._setup_ttk_style()

        self.db = DBManager(error_handler=self._db_error)

        container = tk.Frame(root, bg=C["bg"])
        container.pack(fill="both", expand=True)

        self.sidebar = Sidebar(container, self)
        self.sidebar.pack(side="left", fill="y")

        main = tk.Frame(container, bg=C["bg"])
        main.pack(side="left", fill="both", expand=True)

        self.header = Header(main, self)
        self.header.pack(fill="x")

        self.view_area = tk.Frame(main, bg=C["bg"])
        self.view_area.pack(fill="both", expand=True)
        self.view_area.rowconfigure(0, weight=1)
        self.view_area.columnconfigure(0, weight=1)

        self.views = {}
        for key, cls in (("dashboard", DashboardView), ("cards", CardsView),
                         ("quiz", QuizView), ("scenarios", ScenarioView),
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
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Dash.Treeview",
                        background=C["card_alt"], fieldbackground=C["card_alt"],
                        foreground=C["text"], rowheight=30, borderwidth=0,
                        relief="flat", font=F["small"],
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
                        font=F["small_bold"], relief="flat", borderwidth=0)
        style.map("Dash.Treeview.Heading",
                  background=[("active", C["purple"])],
                  foreground=[("active", "#FFFFFF")])
        style.map("Dash.Treeview",
                  background=[("selected", C["purple"])],
                  foreground=[("selected", "#FFFFFF")])
        style.configure("Dash.Vertical.TScrollbar",
                        background=C["card_hi"], troughcolor=C["card"],
                        bordercolor=C["card"], arrowcolor=C["text_dim"],
                        darkcolor=C["card_hi"], lightcolor=C["card_hi"])

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


def main():
    root = tk.Tk()
    FISIApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
