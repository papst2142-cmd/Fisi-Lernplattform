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

import datetime
import os
import platform
import queue
import random
import sys
import threading
import time
import traceback
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox

import customtkinter as ctk
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fisi_core import (  # noqa: E402
    AP1_SZENARIEN, AP1_THEMES, AP2_THEMES, CALC_EXPLAIN_RAID,
    CALC_EXPLAIN_SCREEN, CALC_EXPLAIN_SUBNET, CATEGORIES, CATEGORY_SHORT,
    COLOR_DEPTHS, DBManager, FILTER_ALL, InputError, KARTEIKARTEN,
    LIST_PAGE_SIZE, PROJEKTARBEITEN, QUIZ_QUESTIONS, RAID_LEVELS,
    STATUS_FILTERS, SZENARIEN,
    TOPIC_NAME, TOPIC_SHORT, TOPICS,
    LEVEL_RED, LEVEL_YELLOW, Q_DONE, Q_OPEN, Q_PRACTICE, Q_STATUS_NAME, Q_STATUS_TABS,
    SOURCE_NAME, SOURCE_PLURAL, SOURCES, SRC_AP1, SRC_AP2, SRC_CARD, SRC_PROJECT,
    SRC_QUIZ, StatusBook, model_answer, notebook_entries, notebook_summary,
    position_statuses, status_label,
    REMINDER_TOAST_MS, plural,
    ap1_theme_totals, content_totals, filter_positions, group_values, ihk_note,
    page_slice, raid_report, screen_report, search_content, subnet_report,
    theme_totals, validate_content,
)
from fisi_core import install_error_log, log_exception  # noqa: E402
import fisi_game  # noqa: E402
import fisi_projekt as fpj  # noqa: E402
import fisi_pruefung as fp  # noqa: E402
from fisi_lernen import (  # noqa: E402
    GOAL_MAX, GOAL_MIN, GOAL_STEP, TRAINER_KIND_NAME, TRAINER_KINDS, TRAINER_LEVEL_NAME,
    TRAINER_LEVELS, TRAINER_ROUND, DailyGoal, ReviewPlan, due_text, learning_settings,
    parse_time, reminder_due, reminder_text, save_learning_settings, trainer_round,
    trainer_summary,
)
import fisi_game_gui  # noqa: E402
import fisi_sicherung as fsi  # noqa: E402
import fisi_sync  # noqa: E402
import fisi_update  # noqa: E402
import fisi_theme  # noqa: E402
from fisi_theme import C, CATEGORY_COLOR, GRADIENTS, THEME_COLOR, mix  # noqa: E402
from fisi_game_gui import (  # noqa: E402
    BranchView, ChoiceRow, CustomerView, FarmView, FirmView, GameView, HomeView, JourneyView,
    MilestoneMoment, OfficeView, close_badge_toasts, show_badge_toast,
)
from fisi_widgets import (  # noqa: E402
    Card, CalendarPanel, GradientBar, GradientPanel, Heatmap, IconButton,
    IconCanvas, LineChart, MiniRing, NeoButton, OptionList, RingStat,
    ScrollArea, ThemeTimeline, F,
    circle_image, ctk_image, make_autogrow_text, make_label, make_text, px,
    ring_image, rounded_gradient, set_text, setup_fonts, tk_font, tk_photo,
)

APP_TITLE = "FISI Lernplattform"
# Versionsschema bis zur Vollversion 1.0:
#   Update (neue Funktionen/Aenderungen): 0.x   -> 0.21 -> 0.22 -> 0.23
#   Fehlerbehebung (Fix):                 0.x.y -> 0.22.1 -> 0.22.2
# Mit jedem Update beginnt die Fixnummer wieder bei 0 (wird dann weggelassen).
# Neue Version immer mit "python build.py --setze-version <Version>" setzen,
# damit sie auch in LIESMICH.txt und im Inno-Setup-Skript gleich lautet.
APP_VERSION = "0.52"


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
    ("ap1scenarios", "layers", "AP1-Szenarien", None),
    ("scenarios", "diamond", "AP2-Szenarien", None),
    ("testproject", "flag", "Testprojekt", None),
    ("abschluss", "case", "Abschlussprojekt", None),
    ("notebook", "notebook", "Notizblock", None),
    ("calc", "calc", "Rechner", None),
    ("game", "game", "Spiel", [("buero", "office", "Büro"), ("kunde", "station", "Kunde"),
                                 ("zuhause", "home", "Zuhause"), ("firma", "case", "Firma"),
                                 ("reise", "journey", "Reise")]),
    ("progress", "chart", "Fortschritt", None),
    ("settings", "gear", "Optionen", None),
]

# Dieselben Symbole wie in der Handy-App (ab 0.39), siehe fisi_widgets.SYMBOLS
NAV_SYMBOLS = {
    "dashboard": "dashboard", "cards": "style", "quiz": "track_changes",
    "ap1scenarios": "layers", "scenarios": "diamond", "testproject": "flag",
    "abschluss": "workspace_premium",
    "notebook": "edit_note", "calc": "calculate", "game": "sports_esports",
    "progress": "insights", "settings": "settings",
    # Unterpunkte: Spiel
    "buero": "business", "kunde": "storefront", "zuhause": "home", "firma": "work",
    "reise": "route",
}
CATEGORY_NAV_SYMBOL = {
    CATEGORIES[0]: "lan",
    CATEGORIES[1]: "security",
    CATEGORIES[2]: "dns",
    CATEGORIES[3]: "euro",
    CATEGORIES[4]: "storage",
}

# Symbole der Fachbereiche im Untermenue der Seitenleiste
CATEGORY_NAV_ICON = {
    CATEGORIES[0]: "node",
    CATEGORIES[1]: "shield",
    CATEGORIES[2]: "server",
    CATEGORIES[3]: "case",
    CATEGORIES[4]: "database",
}

VIEW_TITLES = {
    "dashboard": ("DASHBOARD", "HOME"),
    "cards": ("LERNEN", "KARTEIKARTEN"),
    "quiz": ("LERNEN", "PRÜFUNGSTRAINER"),
    "ap1scenarios": ("LERNEN", "AP1-SZENARIEN"),
    "scenarios": ("LERNEN", "AP2-SZENARIEN"),
    "testproject": ("LERNEN", "TESTPROJEKT"),
    "abschluss": ("LERNEN", "ABSCHLUSSPROJEKT"),
    "notebook": ("LERNEN", "NOTIZBLOCK"),
    "calc": ("WERKZEUGE", "RECHNER"),
    "game": ("PRAXIS", "SPIEL"),
    "buero": ("SPIEL", "BÜRO"),
    "kunde": ("SPIEL", "KUNDE"),
    "zuhause": ("SPIEL", "ZUHAUSE"),
    "firma": ("SPIEL", "FIRMA"),
    "filiale": ("SPIEL", "FILIALE"),
    "serverfarm": ("SPIEL", "SERVERFARM"),
    "reise": ("SPIEL", "REISE"),
    "progress": ("AUSWERTUNG", "FORTSCHRITT"),
    "settings": ("SYSTEM", "OPTIONEN"),
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
                         text_color=C["text_soft"], font=font or F["body"])
        # Aeltere Aufrufer greifen ueber .entry auf das Eingabefeld zu
        self.entry = self
        self._entry.configure(insertbackground=C["accent"],
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

    def __init__(self, parent, value=10, minimum=1, maximum=100, step=5, bg=None,
                 on_change=None):
        super().__init__(parent, fg_color="transparent")
        self.on_change = on_change
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
        if self.on_change:
            self.on_change(self.value)

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


def option_menu(parent, values, command=None, width=None):
    """Aufklappliste im Stil der Filter (z.B. Thema)."""
    options = {} if width is None else {"width": width}
    menu = ctk.CTkOptionMenu(
        parent, values=values, command=command,
        height=32, corner_radius=10, dynamic_resizing=False,
        fg_color=C["card_alt"], button_color=C["card_alt"],
        button_hover_color=C["card_hi"], text_color=C["text"],
        dropdown_fg_color=C["card"], dropdown_hover_color=C["card_hi"],
        dropdown_text_color=C["text"], font=F["small"],
        dropdown_font=F["small"], **options)
    menu.set(values[0])
    return menu


def status_color(key):
    """Farbe zum Lernstand einer Frage (Schluessel aus status_label)."""
    return {LEVEL_RED: C["red"], LEVEL_YELLOW: C["yellow"], "fertig": C["green"],
            Q_DONE: C["green"]}.get(key, C["muted"])


class TopicMenu:
    """Aufklappliste "Thema" passend zum gewaehlten Fachbereich."""

    def __init__(self, parent, command):
        self.command = command
        self.names = {}
        self.menu = option_menu(parent, [FILTER_ALL], command=lambda _v: command(),
                                width=260)

    def set_category(self, category, topic=None):
        topics = [t for cat in CATEGORIES for t in TOPICS[cat]] \
            if category in (None, FILTER_ALL) else TOPICS.get(category, [])
        self.names = {TOPIC_NAME[t]: t for t in topics}
        self.menu.configure(values=[FILTER_ALL] + list(self.names))
        self.menu.set(TOPIC_NAME[topic] if topic in TOPIC_NAME and
                      TOPIC_NAME[topic] in self.names else FILTER_ALL)

    def get(self):
        return self.names.get(self.menu.get(), FILTER_ALL)


def count_text(counts):
    return "Offen %d  ·  Zu üben %d  ·  Abgeschlossen %d" % (
        counts[Q_OPEN], counts[Q_PRACTICE], counts[Q_DONE])


def rate_box(parent, command):
    """Zeile "Gewusst" / "Nicht gewusst" nach dem Aufdecken einer Loesung
    (Selbsteinschaetzung ab 0.39). Wird erst beim Aufdecken eingeblendet."""
    box = transparent_frame(parent)
    make_label(box, "Wusstest du es?", font=F["small"],
               fg=C["text_dim"]).pack(side="left", padx=(0, 12))
    NeoButton(box, "Gewusst", lambda: command(True), kind="primary", height=34,
              font=F["small_bold"]).pack(side="left")
    NeoButton(box, "Nicht gewusst", lambda: command(False), kind="ghost", height=34,
              font=F["small_bold"]).pack(side="left", padx=(8, 0))
    return box


class PagedList:
    """Liste mit Suchfeld, Filtern und Seiten fuer Szenarien und Testprojekte.

    Es werden einmalig LIST_PAGE_SIZE Zeilen angelegt und beim Blaettern oder
    Filtern nur neu beschriftet. Die Zahl der Widgets bleibt dadurch gleich,
    egal wie viele Eintraege es gibt (lange Listen liessen das Programm frueher
    beim Aufbau abstuerzen). on_select erhaelt die Position in der
    Gesamtliste, status_source liefert den Lernstand der bearbeiteten
    Positionen {position: (status, stufe)} (ab 0.39, siehe position_statuses).
    """

    def __init__(self, parent, items, on_select, subtitle, status_source,
                 category_filter=False, group_field=None, group_label="Thema"):
        self.items = items
        self.on_select = on_select
        self.subtitle = subtitle
        self.status_source = status_source
        self.group_field = group_field
        self.statuses = {}
        self.filtered = list(range(len(items)))
        self.page = 0
        self.active = None
        self.menus = {}

        self.search = EntryBox(parent, width=18, font=F["small"])
        self.search.configure(placeholder_text="Titel oder Nummer suchen",
                              placeholder_text_color=C["muted"], height=34)
        self.search.pack(fill="x")
        self.search.bind("<KeyRelease>", lambda _e: self.refresh(), add="+")

        filters = []
        if category_filter:
            self.short_to_cat = {CATEGORY_SHORT[c]: c for c in CATEGORIES}
            filters.append(("category", "FACHBEREICH",
                            [FILTER_ALL] + [CATEGORY_SHORT[c] for c in CATEGORIES]))
        if group_field:
            filters.append(("group", group_label.upper(),
                            [FILTER_ALL] + group_values(items, group_field)))
        filters.append(("status", "STATUS", STATUS_FILTERS))
        for key, label, values in filters:
            make_label(parent, label, font=F["label"], fg=C["muted"]).pack(
                anchor="w", pady=(10, 4))
            menu = ctk.CTkOptionMenu(
                parent, values=values, command=lambda _v: self.refresh(),
                height=32, corner_radius=10, dynamic_resizing=False,
                fg_color=C["card_alt"], button_color=C["card_alt"],
                button_hover_color=C["card_hi"], text_color=C["text"],
                dropdown_fg_color=C["card"], dropdown_hover_color=C["card_hi"],
                dropdown_text_color=C["text"], font=F["small"],
                dropdown_font=F["small"])
            menu.set(FILTER_ALL)
            menu.pack(fill="x")
            self.menus[key] = menu

        self.lbl_count = make_label(parent, "", font=F["tiny"], fg=C["muted"])
        self.lbl_count.pack(anchor="w", pady=(12, 2))

        self.rows_box = transparent_frame(parent)
        self.rows_box.pack(fill="x")
        self.lbl_empty = make_label(self.rows_box, "Keine Treffer für diese Auswahl.",
                                    font=F["small"], fg=C["muted"])
        self.rows = [self._make_row(slot) for slot in range(LIST_PAGE_SIZE)]

        pager = transparent_frame(parent)
        pager.pack(fill="x", pady=(10, 0))
        IconButton(pager, "arrow_left", lambda: self.turn(-1),
                   parent_bg=C["card"]).pack(side="left")
        self.lbl_page = make_label(pager, "", font=F["small_bold"], fg=C["text_dim"])
        self.lbl_page.pack(side="left", expand=True)
        IconButton(pager, "arrow_right", lambda: self.turn(1),
                   parent_bg=C["card"]).pack(side="right")

    def _make_row(self, slot):
        row, marker, inner = clickable_row(self.rows_box, C["purple"])
        title = ctk.CTkLabel(inner, text="", text_color=C["text_dim"],
                             font=F["small_bold"], height=0, anchor="w",
                             justify="left", wraplength=190, cursor="hand2")
        title.pack(anchor="w")
        sub = ctk.CTkLabel(inner, text="", text_color=C["muted"], font=F["tiny"],
                           anchor="w", height=0, cursor="hand2")
        sub.pack(anchor="w")
        bind_click((row, inner, title, sub, marker), lambda _e, s=slot: self._clicked(s))
        return {"frame": row, "marker": marker, "title": title, "sub": sub,
                "position": None}

    def _clicked(self, slot):
        position = self.rows[slot]["position"]
        if position is not None:
            self.on_select(position)

    def _criteria(self):
        category = FILTER_ALL
        if "category" in self.menus:
            category = self.short_to_cat.get(self.menus["category"].get(), FILTER_ALL)
        group = self.menus["group"].get() if "group" in self.menus else FILTER_ALL
        return {"query": self.search.get(), "category": category,
                "group_field": self.group_field, "group": group,
                "status": self.menus["status"].get(), "statuses": self.statuses}

    def refresh(self, keep_page=False):
        """Filter neu anwenden. Ohne keep_page springt die Liste auf Seite 1."""
        self.statuses = self.status_source()
        self.filtered = filter_positions(self.items, **self._criteria())
        if not keep_page:
            self.page = 0
        self._paint()

    def _paint(self):
        visible, self.page, pages = page_slice(self.filtered, self.page)
        for row in self.rows:
            row["frame"].pack_forget()
        self.lbl_empty.pack_forget()
        if not visible:
            self.lbl_empty.pack(anchor="w", pady=6)
        for row, position in zip(self.rows, visible):
            item = self.items[position]
            active = position == self.active
            status, level = self.statuses.get(position, (Q_OPEN, ""))
            mark = " ✓" if status == Q_DONE else ""
            row["position"] = position
            row["title"].configure(text="%d. %s%s" % (position + 1, item["title"], mark),
                                   text_color=C["text"] if active else C["text_dim"])
            sub = self.subtitle(item)
            if status != Q_OPEN:
                sub += "  ·  " + Q_STATUS_NAME[status]
            row["sub"].configure(text=sub, text_color=status_color(level or status))
            row["marker"].configure(fg_color=CATEGORY_COLOR[item["cat"]])
            row["frame"].configure(fg_color=C["card_hi"] if active else C["card_alt"],
                                   border_color=C["purple"] if active else C["border"])
            row["frame"].pack(fill="x", pady=4)
        for row in self.rows[len(visible):]:
            row["position"] = None
        self.lbl_count.configure(text="%d von %d Aufgaben" % (len(self.filtered),
                                                               len(self.items)))
        self.lbl_page.configure(text="Seite %d / %d" % (self.page + 1, pages))

    def turn(self, delta):
        self.page += delta
        self._paint()

    def show(self, position):
        """Markiert position und blaettert zu ihrer Seite. Passt sie nicht zu
        den Filtern (z.B. nach einem Suchtreffer), werden diese zurueckgesetzt."""
        self.active = position
        if position not in self.filtered:
            self.search.delete(0, "end")
            for menu in self.menus.values():
                menu.set(FILTER_ALL)
            self.statuses = self.status_source()
            self.filtered = filter_positions(self.items, **self._criteria())
        self.page = self.filtered.index(position) // LIST_PAGE_SIZE
        self._paint()

    def next_after(self, position):
        """Naechste Position innerhalb der aktuellen Auswahl (am Ende wieder
        die erste). Ohne Treffer einfach der naechste Eintrag der Gesamtliste."""
        if not self.filtered:
            return (position + 1) % len(self.items)
        order = [p for p in self.filtered if p > position] + \
            [p for p in self.filtered if p <= position]
        # Ohne Status-Filter geht es bevorzugt mit Nicht-Abgeschlossenem weiter
        if self.menus["status"].get() == FILTER_ALL:
            for candidate in order:
                if candidate != position and \
                        self.statuses.get(candidate, (Q_OPEN, ""))[0] != Q_DONE:
                    return candidate
        return order[0]


# ============================================================================
#  SEITENLEISTE
# ============================================================================

# Unsichtbarer Platzhalter fuer den Farbstreifen inaktiver Menuezeilen
BLANK_INDICATOR = Image.new("RGBA", (16, 80), (0, 0, 0, 0))


class NavRow(ctk.CTkFrame):
    """Eine abgerundete Zeile in der Seitenleiste."""

    def __init__(self, parent, icon, text, command, sub=False, expandable=False,
                 symbol=None):
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
                                      parent_bg=C["sidebar"], cursor="hand2",
                                      symbol=symbol)
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
        color = C["accent"] if self.active else C["muted"]
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
            bar = rounded_gradient(4, 20, 2, C["accent"], GRADIENTS["accent"][1],
                                   direction="v")
            self.indicator.configure(image=ctk_image(bar, 4, 20))
            self.text_label.configure(text_color=C["text"])
            self.icon_canvas.paint(C["accent"])
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
        self.parents = {}         # Unteransicht -> Menuepunkt (buero -> game)

        logo = transparent_frame(self)
        logo.pack(fill="x", pady=(22, 20), padx=20)
        mark = tk.Canvas(logo, width=px(34), height=px(34), bg=C["sidebar"],
                         highlightthickness=0, bd=0)
        mark.pack(side="left")
        ring = ring_image(34, 5, 1.0, C["accent"], C["accent2"], C["ring_bg"])
        dot = circle_image(12, fill=C["accent2"])
        self._logo_images = (tk_photo(ring, px(34), px(34)),
                             tk_photo(dot, px(12), px(12)))
        mark.create_image(px(17), px(17), image=self._logo_images[0])
        mark.create_image(px(17), px(17), image=self._logo_images[1])
        ctk.CTkLabel(logo, text="FISI", text_color=C["text"], font=F["logo"],
                     height=0).pack(side="left", padx=(12, 0))
        ctk.CTkLabel(logo, text="Lernplattform", text_color=C["muted"],
                     font=F["tiny"], height=0).pack(side="left", padx=(7, 0),
                                                    pady=(7, 0))

        self.footer = make_label(self, "Version %s" % APP_VERSION,
                                 font=F["tiny"], fg=C["muted"])
        self.footer.pack(side="bottom", pady=(8, 14))
        self._build_status()

        # Ab 0.48: Das Menue scrollt, wenn ausgeklappte Reiter nicht mehr in
        # das Fenster passen. Der Schieberegler erscheint nur bei Bedarf.
        self.menu_area = ScrollArea(self, bg=C["sidebar"], hide_vbar=True)
        self.menu_area.pack(fill="both", expand=True, pady=(0, 8))
        menu = self.menu_area.inner

        make_label(menu, "MENÜ", font=F["label"], fg=C["muted"],
                   anchor="w").pack(fill="x", padx=24, pady=(0, 6))

        for key, icon, text, sub_items in NAV_ITEMS:
            expandable = bool(sub_items)
            row = NavRow(menu, icon, text,
                         command=lambda k=key: self._on_nav(k),
                         expandable=expandable, symbol=NAV_SYMBOLS.get(key))
            row.pack(fill="x", padx=12, pady=1)
            self.rows[key] = row

            if sub_items:
                container = transparent_frame(menu)
                self.sub_frames[key] = container
                for item in sub_items:
                    if isinstance(item, tuple):
                        # Eigene Unteransicht, z.B. Spiel -> Buero
                        sub_key, sub_icon, sub_text = item
                        sub_row = NavRow(container, sub_icon, sub_text,
                                         command=lambda k=sub_key: self.app.show_view(k),
                                         sub=True, symbol=NAV_SYMBOLS.get(sub_key))
                        self.parents[sub_key] = key
                    else:
                        sub_row = NavRow(container, CATEGORY_NAV_ICON.get(item, "dot"),
                                         CATEGORY_SHORT.get(item, item),
                                         command=lambda c=item: self.app.open_cards(c),
                                         sub=True, symbol=CATEGORY_NAV_SYMBOL.get(item))
                    sub_row.pack(fill="x", pady=1)

    def _build_status(self):
        status = ctk.CTkFrame(self, fg_color=C["card"], corner_radius=14,
                              border_width=1, border_color=C["border"])
        status.pack(side="bottom", fill="x", padx=14)
        make_label(status, "LERNSTATUS", font=F["label"], fg=C["muted"],
                   anchor="w").pack(fill="x", padx=14, pady=(12, 0))
        self.streak_label = make_label(status, "", font=F["small_bold"],
                                       fg=C["text"], anchor="w")
        self.streak_label.pack(fill="x", padx=14, pady=(6, 0))
        self.status_bar = GradientBar(status, "Inhalte bearbeitet", C["accent"],
                                      C["accent2"], parent_bg=C["card"])
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
        if key in self.parents:
            if self.parents[key] not in self.expanded:
                self._toggle(self.parents[key])
            key = self.parents[key]
        for name, row in self.rows.items():
            row.set_active(name == key)

    def update_status(self, streak, learned, total):
        self.streak_label.configure(text="Lernserie: %s" % plural(streak, "Tag", "Tage"))
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
        self.crumb_sub = make_label(left, "HOME", font=F["label"], fg=C["accent"])
        self.crumb_sub.pack(side="left")
        # Ab 0.48: aktiver Spielstand-Platz in den Spielansichten
        self.slot_box = transparent_frame(left)
        self.slot_label = make_label(self.slot_box, "", font=F["small"], fg=C["muted"])
        self.slot_label.pack(side="left", padx=(16, 8))
        NeoButton(self.slot_box, "Platz wechseln", lambda: self.app.open_slot_picker(),
                  kind="ghost", height=26, font=F["small_bold"]).pack(side="left")

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
        self.search_entry._entry.configure(insertbackground=C["accent"],
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

    def set_slot(self, text):
        """Platzanzeige (ab 0.48): leer = ausblenden."""
        if text:
            self.slot_label.configure(text="·   " + text)
            self.slot_box.pack(side="left")
        else:
            self.slot_box.pack_forget()


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

        # --- Heute (ab 0.51): Tagesziel, Lernserie, Wiederholungen --------
        self.today_card = Card(self.content, title="Heute",
                               subtitle="Tagesziel und Wiederholung", accent=C["green"])
        self.today_card.pack(fill="x", pady=(16, 0))
        today = transparent_frame(self.today_card.body)
        today.pack(fill="x")
        self.goal_box = transparent_frame(today)
        self.goal_ring = MiniRing(self.goal_box, size=74, thickness=7, parent_bg=C["card"])
        self.goal_ring.pack(side="left")
        goal_text = transparent_frame(self.goal_box)
        goal_text.pack(side="left", padx=(12, 0))
        self.lbl_goal = make_label(goal_text, "", font=F["body_bold"], fg=C["text"])
        self.lbl_goal.pack(anchor="w")
        self.lbl_streak = make_label(goal_text, "", font=F["small"], fg=C["text_soft"])
        self.lbl_streak.pack(anchor="w", pady=(4, 0))
        self.review_box = transparent_frame(today)
        self.review_box.pack(side="right")
        self.lbl_due = make_label(self.review_box, "", font=F["body_bold"], fg=C["text"])
        self.lbl_due.pack(side="left", padx=(0, 14))
        self.btn_review = NeoButton(self.review_box, "Jetzt wiederholen",
                                    self.app.start_review, kind="primary")
        self.btn_review.pack(side="left")

        # --- Reihe 1: Kennzahlen (fuenf gleich breite Kacheln) -----------
        row1 = transparent_frame(self.content)
        row1.pack(fill="x", pady=(16, 0))
        for column in range(5):
            row1.columnconfigure(column, weight=1, uniform="row1")

        self.ring_cards = self._ring_card(row1, 0, "Karteikarten")
        self.ring_quiz = self._ring_card(row1, 1, "Quizfragen")
        self.ring_ap1 = self._ring_card(row1, 2, "AP1-Szenarien")
        self.ring_scen = self._ring_card(row1, 3, "AP2-Szenarien")

        quote = Card(row1, title="Erfolgsquote", subtitle="Quiz gesamt",
                     accent=C["accent2"])
        quote.grid(row=0, column=4, sticky="nsew")
        self.lbl_quote = make_label(quote.body, "0 %", font=F["display"],
                                    fg=C["accent"])
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
        self.bar_cards = GradientBar(cover.body, "Karteikarten", C["accent"],
                                     C["purple"], parent_bg=C["card"])
        self.bar_cards.pack(fill="x", pady=(4, 8))
        self.bar_quiz = GradientBar(cover.body, "Quizfragen", C["purple"],
                                    C["accent2"], parent_bg=C["card"])
        self.bar_quiz.pack(fill="x", pady=8)
        self.bar_ap1 = GradientBar(cover.body, "AP1-Szenarien", C["blue"],
                                   C["accent"], parent_bg=C["card"])
        self.bar_ap1.pack(fill="x", pady=8)
        self.bar_scen = GradientBar(cover.body, "AP2-Szenarien", C["accent2"],
                                    C["orange"], parent_bg=C["card"])
        self.bar_scen.pack(fill="x", pady=8)

        # --- Reihe 3: Heatmap und Fachbereiche ---------------------------
        row3 = self.row3 = transparent_frame(self.content)
        row3.pack(fill="x", pady=(14, 0))
        row3.columnconfigure(0, weight=2, uniform="row3")
        row3.columnconfigure(1, weight=3, uniform="row3")

        heat_card = Card(row3, title="Aktivität je Fachbereich",
                         subtitle="Auswahl zeigt die Themen", accent=C["accent2"])
        heat_card.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        self.heatmap = Heatmap(heat_card.body, height=190, parent_bg=C["card"],
                               on_click=lambda index: self._toggle_zoom(CATEGORIES[index]))
        self.heatmap.pack(fill="both", expand=True)

        fach_card = Card(row3, title="Fortschritt je Fachbereich",
                         subtitle="Auswahl zeigt die Themen", accent=C["green"])
        fach_card.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        holder = transparent_frame(fach_card.body)
        holder.pack(fill="x")
        self.fach_rings = {}
        for category in CATEGORIES:
            column = transparent_frame(holder)
            column.pack(side="left", fill="both", expand=True)
            ring = MiniRing(column, size=88, thickness=8, parent_bg=C["card"])
            ring.pack()
            name = make_label(column, CATEGORY_SHORT[category], font=F["small_bold"],
                              fg=C["text"])
            name.pack(pady=(8, 0))
            detail = make_label(column, "", font=F["tiny"], fg=C["muted"],
                                justify="center")
            detail.pack()
            for widget in (column, ring, name, detail):
                widget.configure(cursor="hand2")
                widget.bind("<Button-1>",
                            lambda _e, cat=category: self._toggle_zoom(cat))
            self.fach_rings[category] = (ring, detail, name)

        # --- Reinzoom: Themen eines Fachbereichs (ab 0.37) ----------------
        # Erscheint unter Reihe 3, sobald ein Fachbereich angeklickt wird.
        self.zoom_category = None
        self.zoom_card = None

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
                          subtitle="bearbeitete Szenarien", accent=C["accent2"])
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
        # Ab 0.50: nur neu rechnen und zeichnen, wenn sich seit dem letzten
        # Mal etwas getan hat (Datenbank-Stempel, Tag, Reinzoomen)
        key = self._refresh_key()
        if key is not None and key == getattr(self, "_refreshed", None):
            return
        self.refresh()
        self._refreshed = key

    def _refresh_key(self):
        stamp = self.db.change_stamp() if hasattr(self.db, "change_stamp") else None
        if stamp is None:
            return None
        return (stamp, datetime.date.today(), self.zoom_category,
                tuple(sorted(learning_settings().items())))

    def _refresh_today(self):
        """Kachel "Heute" (ab 0.51)."""
        settings = learning_settings()
        goal = DailyGoal.from_db(self.db, settings["ziel_anzahl"])
        show_goal, show_streak = settings["ziel_an"], settings["serie_an"]
        if show_goal or show_streak:
            self.goal_box.pack(side="left")
        else:
            self.goal_box.pack_forget()
        if show_goal:
            self.goal_ring.pack(side="left")
            self.goal_ring.set(goal.fraction * 100,
                               C["green"] if goal.reached else C["accent"])
            self.lbl_goal.configure(text=goal.text())
            self.lbl_goal.pack(anchor="w")
        else:
            self.goal_ring.pack_forget()
            self.lbl_goal.pack_forget()
        if show_streak:
            self.lbl_streak.configure(text=goal.streak_text())
            self.lbl_streak.pack(anchor="w", pady=(4, 0))
        else:
            self.lbl_streak.pack_forget()
        plan = ReviewPlan.from_db(self.db)
        self.lbl_due.configure(text=due_text(plan))
        self.btn_review.set_enabled(plan.count() > 0)

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
        self._refresh_today()
        streak = ("Lernserie: %s   ·   " % plural(self.db.streak(), "Tag", "Tage")
                  if learning_settings()["serie_an"] else "")
        self.hero.set_data(
            "Dein Lernstand",
            "%s%d von %d Inhalten bearbeitet   ·   "
            "Quiz-Erfolgsquote %d %%"
            % (streak, learned, self.total_content, round(rate)),
            "%d %%" % round(learned / max(1, self.total_content) * 100),
            "Gesamtfortschritt")

        self.ring_cards.set(learned_cards / max(1, total_cards), C["accent"],
                            C["purple"], str(learned_cards),
                            "von %d Karten" % total_cards)
        self.ring_quiz.set(quiz_distinct / max(1, total_quiz), C["purple"],
                           C["accent2"], str(quiz_answered),
                           "%d von %d Fragen" % (quiz_distinct, total_quiz))
        self.ring_ap1.set(ap1_done / max(1, total_ap1), C["blue"],
                          C["accent"], str(ap1_done),
                          "von %d Szenarien" % total_ap1)
        self.ring_scen.set(scen_done / max(1, total_scen), C["accent2"],
                           C["orange"], str(scen_done),
                           "von %d Szenarien" % total_scen)

        self.lbl_quote.configure(text="%d %%" % round(rate))
        if answered:
            self.lbl_quote_sub.configure(
                text="%d von %s richtig beantwortet"
                % (correct, plural(answered, "Frage", "Fragen")))
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
            {"name": "Aufgaben pro Tag", "values": values, "color": C["accent"]},
        ])

        # Heatmap
        matrix = self.db.category_daily(self.DAYS)
        rows = [(CATEGORY_SHORT[cat], CATEGORY_COLOR[cat], matrix[cat])
                for cat in CATEGORIES]
        self.heatmap.set_data(rows, self.DAYS, selected=CATEGORIES.index(self.zoom_category)
                              if self.zoom_category else None)

        # Fachbereiche
        coverage = self.db.category_coverage(self.totals)
        stats = self.db.category_stats()
        for category in CATEGORIES:
            ring, detail, name = self.fach_rings[category]
            name.configure(text_color=CATEGORY_COLOR[category]
                           if category == self.zoom_category else C["text"])
            ring.set(coverage.get(category, 0.0), CATEGORY_COLOR[category])
            data = stats.get(category, {"answered": 0, "correct": 0})
            if data["answered"]:
                quota = data["correct"] / data["answered"] * 100
                detail.configure(text="%s\n%d %% richtig"
                                      % (plural(data["answered"], "Antwort", "Antworten"),
                                         round(quota)))
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
        self._refresh_zoom()

        progress = self.db.theme_progress(theme_totals())
        self.timeline.set_data([(name, progress.get(name, 0.0), THEME_COLOR[name])
                                for name in AP2_THEMES])

        progress_ap1 = self.db.theme_progress(ap1_theme_totals(), themes=AP1_THEMES,
                                              table="ap1_events")
        self.timeline_ap1.set_data([(name, progress_ap1.get(name, 0.0),
                                     THEME_COLOR[name]) for name in AP1_THEMES])

    # -- Reinzoom in die Themen eines Fachbereichs ---------------------------

    def _toggle_zoom(self, category):
        """Klick auf einen Fachbereich: dessen Themen zeigen, erneuter Klick
        (oder Schliessen) blendet sie wieder aus."""
        self.zoom_category = None if category == self.zoom_category else category
        if self.zoom_card is not None:
            self.zoom_card.destroy()
            self.zoom_card = None
        if self.zoom_category:
            self._build_zoom(self.zoom_category)
        self.refresh()

    def _build_zoom(self, category):
        color = CATEGORY_COLOR[category]
        topics = TOPICS[category]
        card = self.zoom_card = Card(self.content, title="Themen · %s" % category,
                                     subtitle="Aktivität und Wissen",
                                     accent=color)
        card.pack(fill="x", pady=(14, 0), after=self.row3)
        NeoButton(card.head, "Schließen", lambda: self._toggle_zoom(category), kind="ghost",
                  height=28, font=F["small_bold"], parent_bg=C["card"]).pack(
                      side="right", padx=(12, 0))
        body = transparent_frame(card.body)
        body.pack(fill="x")
        body.columnconfigure(0, weight=2, uniform="zoom")
        body.columnconfigure(1, weight=3, uniform="zoom")

        left = transparent_frame(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        make_label(left, "Aktivität je Thema (letzte %d Tage)" % self.DAYS,
                   font=F["tiny"], fg=C["muted"]).pack(anchor="w")
        self.zoom_heatmap = Heatmap(left, height=12 + 34 * len(topics), parent_bg=C["card"],
                                    label_w=118)
        self.zoom_heatmap.pack(fill="x", pady=(6, 0))

        right = transparent_frame(body)
        right.grid(row=0, column=1, sticky="nsew", padx=(14, 0))
        make_label(right, "Wissensstand je Thema (zählt für die Aufträge im Spiel)",
                   font=F["tiny"], fg=C["muted"]).pack(anchor="w")
        self.zoom_bars = {}
        for index, topic in enumerate(topics):
            shade = mix(color, C["card"], 0.12 * (index % 3))
            bar = GradientBar(right, TOPIC_NAME[topic], mix(shade, C["card"], 0.4), shade,
                              height=40, parent_bg=C["card"])
            bar.pack(fill="x", pady=(4, 0))
            self.zoom_bars[topic] = bar

    def _refresh_zoom(self):
        category = self.zoom_category
        if not category or self.zoom_card is None:
            return
        color = CATEGORY_COLOR[category]
        matrix = self.db.topic_daily(category, self.DAYS)
        self.zoom_heatmap.set_data([(TOPIC_SHORT[topic], color, matrix[topic])
                                    for topic in TOPICS[category]], self.DAYS)
        levels = fisi_game.topic_knowledge(self.db)
        stats = self.db.topic_stats()
        for topic, bar in self.zoom_bars.items():
            answered = stats[topic]["answered"]
            if answered:
                note = "Wissen %d %%  ·  %s" % (levels[topic],
                                                 plural(answered, "Antwort", "Antworten"))
            else:
                note = "noch nicht bearbeitet"
            bar.set(levels[topic], note)

    def _activity_row(self, timestamp, kind, detail, extra):
        row = ctk.CTkFrame(self.activity_box, fg_color=C["card_alt"],
                           corner_radius=10)
        row.pack(fill="x", pady=3)
        color = {"Karteikarte": C["accent"], "Quizfrage": C["purple"],
                 "AP1-Szenario": C["blue"], "AP2-Szenario": C["accent2"],
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
        self.by_question = {card["q"]: card for card in self.cards}
        self.filtered = list(self.cards)
        self.index = 0
        self.mode = "freitext"
        self.book = StatusBook(self.db)
        # Je Anzeige einer Karte wird hoechstens einmal gespeichert; im Modus
        # "Aufdecken" erst mit der Selbsteinschaetzung (ab 0.39)
        self.logged = False
        self.pending = None

        top = Card(self.content)
        top.pack(fill="x")
        bar = transparent_frame(top.body)
        bar.pack(fill="x")

        make_label(bar, "FACHBEREICH", font=F["label"], fg=C["muted"]).pack(anchor="w")
        options = [("Alle", "Alle")] + [(c, CATEGORY_SHORT[c]) for c in CATEGORIES]
        self.cat_pills = PillGroup(bar, options, on_change=self._on_category)
        self.cat_pills.pack(anchor="w", pady=(8, 14))

        filters = transparent_frame(bar)
        filters.pack(fill="x", pady=(0, 14))
        status_box = transparent_frame(filters)
        status_box.pack(side="left")
        make_label(status_box, "STATUS", font=F["label"], fg=C["muted"]).pack(anchor="w")
        self.status_pills = PillGroup(status_box, Q_STATUS_TABS,
                                      on_change=lambda _v: self.apply_filter())
        self.status_pills.pack(anchor="w", pady=(8, 0))
        topic_box = transparent_frame(filters)
        topic_box.pack(side="left", padx=(16, 0))
        make_label(topic_box, "THEMA", font=F["label"], fg=C["muted"]).pack(anchor="w")
        self.topic_menu = TopicMenu(topic_box, self.apply_filter)
        self.topic_menu.menu.pack(anchor="w", pady=(8, 0))
        self.topic_menu.set_category(FILTER_ALL)
        self.lbl_counts = make_label(bar, "", font=F["tiny"], fg=C["muted"])
        self.lbl_counts.pack(anchor="w", pady=(0, 12))

        make_label(bar, "LERNMODUS", font=F["label"], fg=C["muted"]).pack(anchor="w")
        self.mode_pills = PillGroup(bar, self.MODES, on_change=self._on_mode)
        self.mode_pills.pack(anchor="w", pady=(8, 0))

        # Frage
        self.question_card = Card(self.content, title="Frage", accent=C["accent"],
                                  subtitle="")
        self.question_card.pack(fill="x", pady=(14, 0))
        self.lbl_status = make_label(self.question_card.body, "", font=F["small_bold"],
                                     fg=C["muted"], anchor="w")
        self.lbl_status.pack(anchor="w")
        self.lbl_question = make_label(self.question_card.body, "",
                                       font=F["h2"], fg=C["text_soft"],
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
                                       font=F["body_bold"], fg=C["text_soft"],
                                       wraplength=900, justify="left", anchor="w")
        self.lbl_feedback.pack(anchor="w", pady=(14, 0))
        self.lbl_solution = make_label(self.answer_card.body, "",
                                       font=F["body"], fg=C["text_dim"],
                                       wraplength=900, justify="left", anchor="w")
        self.lbl_solution.pack(anchor="w", pady=(6, 0))
        # Selbsteinschaetzung im Modus "Aufdecken" (ab 0.39)
        self.rate_box = rate_box(self.answer_card.body, self.rate)

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

        self.apply_filter()

    # -- Steuerung ----------------------------------------------------------

    def on_show(self):
        # Neue Antworten (z.B. nach einem Abgleich) im Status beruecksichtigen
        self.book = StatusBook(self.db)
        self._show_status()

    def set_category(self, category, topic=None):
        """Fachbereich waehlen; mit topic nur die Karten dieses Themas (aus
        dem Spiel: "Karteikarten zu ...")."""
        self.cat_pills.select_value(category, notify=False)
        self.topic_menu.set_category(category, topic)
        self.apply_filter()

    def practice(self, questions):
        """Gezielte Uebungsrunde aus dem Notizblock: nur diese Karten."""
        self.cat_pills.select_value("Alle", notify=False)
        self.topic_menu.set_category(FILTER_ALL)
        self.status_pills.select_value(FILTER_ALL, notify=False)
        self._flush()
        self.book = StatusBook(self.db)
        self.filtered = [self.by_question[q] for q in questions if q in self.by_question]
        self.index = 0
        self._counts([card["q"] for card in self.filtered])
        self.update_ui()

    def _on_category(self, category):
        self.topic_menu.set_category(category)
        self.apply_filter()

    def apply_filter(self):
        """Fachbereich, Thema und Status anwenden. Ohne Status-Filter kommen
        unbearbeitete Karten zuerst (mit gelegentlicher Wiederholung)."""
        self._flush()
        self.book = StatusBook(self.db)
        category = self.cat_pills.get()
        topic = self.topic_menu.get()
        status = self.status_pills.get()
        base = [card for card in self.cards
                if (category == "Alle" or card["cat"] == category)
                and (topic == FILTER_ALL or card.get("thema") == topic)]
        keys = [card["q"] for card in base]
        if status == FILTER_ALL:
            keys = self.book.preferred_order(SRC_CARD, keys)
        else:
            keys = [key for key in keys if self.book.status(SRC_CARD, key)[0] == status]
        self.filtered = [self.by_question[key] for key in keys]
        self.index = 0
        self._counts([card["q"] for card in base])
        self.update_ui()

    def _counts(self, keys):
        self.count_keys = keys
        self.lbl_counts.configure(text=count_text(self.book.counts(SRC_CARD, keys)))

    def set_mode(self, mode):
        """Setzt den Lernmodus inklusive der Auswahlknoepfe."""
        self.mode_pills.select_value(mode, notify=False)
        self._on_mode(mode)

    def _on_mode(self, mode):
        self._flush()
        self.mode = mode
        self.update_ui()

    def jump_to_question(self, question_text):
        for position, card in enumerate(self.filtered):
            if card["q"] == question_text:
                self._flush()
                self.index = position
                self.update_ui()
                return
        # nicht im aktuellen Filter: Filter zuruecksetzen
        self.cat_pills.select(0, notify=False)
        self.status_pills.select_value(FILTER_ALL, notify=False)
        self.topic_menu.set_category(FILTER_ALL)
        self.apply_filter()
        for position, card in enumerate(self.filtered):
            if card["q"] == question_text:
                self.index = position
                break
        self.update_ui()

    def _flush(self):
        """Aufgedeckt, aber nicht bewertet: als angesehen speichern."""
        if self.pending is not None:
            card, self.pending = self.pending, None
            self.db.log_card(card["cat"], card["q"], "reveal", None)
            self.app.notify_progress()

    def _show_status(self):
        if not self.filtered:
            self.lbl_status.configure(text="")
            return
        card = self.filtered[self.index]
        text, key = status_label(self.book, SRC_CARD, card["q"])
        self.lbl_status.configure(text=text, text_color=status_color(key))

    def update_ui(self):
        self._flush()
        self.logged = False
        self.lbl_feedback.configure(text="")
        self.lbl_solution.configure(text="")
        self.rate_box.pack_forget()
        self.frame_free.pack_forget()
        self.options.pack_forget()
        self.frame_reveal.pack_forget()
        self.options.clear()

        if not self.filtered:
            self.lbl_question.configure(text="Für diese Auswahl gibt es keine "
                                             "Karteikarten.")
            self.lbl_status.configure(text="")
            self.lbl_counter.configure(text="0 / 0")
            self.btn_check.set_enabled(False)
            return

        self.btn_check.set_enabled(True)
        card = self.filtered[self.index]
        self.lbl_question.configure(text=card["q"])
        self._show_status()
        self.lbl_counter.configure(text="Karte %d / %d"
                                        % (self.index + 1, len(self.filtered)))
        self.question_card.set_subtitle("%s · %s" % (CATEGORY_SHORT[card["cat"]],
                                                     TOPIC_SHORT[card["thema"]]),
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
            self.lbl_feedback.configure(text="Musterlösung", text_color=C["accent"])
            self.lbl_solution.configure(text=card["a_full"])
            if not self.logged:
                self.pending = card
                self.rate_box.pack(anchor="w", pady=(12, 0))
            return

        if not self.logged:
            self.logged = True
            self._save(card, correct)

    def rate(self, correct):
        """Selbsteinschaetzung nach dem Aufdecken."""
        card, self.pending = self.pending, None
        if card is None:
            return
        self.rate_box.pack_forget()
        self.logged = True
        self._save(card, correct)

    def _save(self, card, correct):
        self.db.log_card(card["cat"], card["q"], self.mode, correct)
        self.book = StatusBook(self.db)
        self._show_status()
        self._counts(self.count_keys)
        self.app.notify_progress()

    def next_card(self):
        if self.filtered:
            self._flush()
            self.index = (self.index + 1) % len(self.filtered)
            self.update_ui()

    def prev_card(self):
        if self.filtered:
            self._flush()
            self.index = (self.index - 1) % len(self.filtered)
            self.update_ui()


# ============================================================================
#  PRUEFUNGSTRAINER
# ============================================================================

class QuizView(View):
    def build(self):
        # Ab 0.51: Umschalter Uebung / Pruefung (Klausursimulation)
        outer = self.content
        self.mode_pills = PillGroup(outer, QUIZ_MODES, on_change=self._on_mode)
        self.mode_pills.pack(anchor="w", pady=(0, 14))
        self.practice_box = transparent_frame(outer)
        self.practice_box.pack(fill="both", expand=True)
        self.exam = ExamPanel(outer, self.app)
        self.content = self.practice_box
        self._build_practice()
        self.content = outer

    def _on_mode(self, mode):
        if mode == "pruefung":
            if self.running:
                self.stop_timer()
                self._reset_controls()
            self.practice_box.pack_forget()
            self.exam.pack(fill="both", expand=True)
            self.exam.show()
        else:
            self.exam.hide()
            self.exam.pack_forget()
            self.practice_box.pack(fill="both", expand=True)
        self.to_top()

    def _build_practice(self):
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

        filters = transparent_frame(body)
        filters.pack(fill="x", pady=(0, 14))
        status_box = transparent_frame(filters)
        status_box.pack(side="left")
        make_label(status_box, "STATUS", font=F["label"], fg=C["muted"]).pack(anchor="w")
        self.status_pills = PillGroup(status_box, Q_STATUS_TABS,
                                      on_change=lambda _v: self._update_pool())
        self.status_pills.pack(anchor="w", pady=(8, 0))
        topic_box = transparent_frame(filters)
        topic_box.pack(side="left", padx=(16, 0))
        make_label(topic_box, "THEMA", font=F["label"], fg=C["muted"]).pack(anchor="w")
        self.topic_menu = TopicMenu(topic_box, self._update_pool)
        self.topic_menu.menu.pack(anchor="w", pady=(8, 0))
        self.topic_menu.set_category(FILTER_ALL)

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
                                    fg=C["accent"])
        self.lbl_timer.pack(side="right")
        self.lbl_score = make_label(status, "", font=F["small"], fg=C["muted"])
        self.lbl_score.pack(side="right", padx=16)

        # Frage
        self.question_card = Card(self.content, title="Prüfungsaufgabe",
                                  accent=C["accent"])
        self.question_card.pack(fill="both", expand=True, pady=(14, 0))
        self.lbl_question = make_label(
            self.question_card.body,
            "Wähle Fachbereich und Fragenanzahl und starte die Session.",
            font=F["h2"], fg=C["text_soft"], wraplength=900, justify="left", anchor="w")
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
        self.topic_menu.set_category(category)
        self._update_pool()

    def on_show(self):
        # Ab 0.51: eine laufende Pruefung geht vor
        if fp.load_running() is not None and self.mode_pills.get() != "pruefung":
            self.mode_pills.select_value("pruefung")
            return
        if self.mode_pills.get() == "pruefung":
            self.exam.show()
        elif not self.running:
            self._update_pool()

    def _update_pool(self):
        """Fachbereich, Thema und Status (ab 0.39) anwenden."""
        category = self.cat_pills.get()
        topic = self.topic_menu.get()
        status = self.status_pills.get()
        self.book = StatusBook(self.db)
        base = [q for q in self.questions
                if (category == "Alle" or q["cat"] == category)
                and (topic == FILTER_ALL or q.get("thema") == topic)]
        self.pool = [q for q in base if self.book.matches(SRC_QUIZ, q["q"], status)]
        self.stepper.set_maximum(max(5, len(self.pool)))
        counts = self.book.counts(SRC_QUIZ, [q["q"] for q in base])
        self.lbl_pool.configure(text="%s verfügbar  ·  %s"
                                     % (plural(len(self.pool), "Frage", "Fragen"),
                                        count_text(counts)))

    # -- Ablauf -------------------------------------------------------------

    def practice(self, questions, keep_order=False):
        """Gezielte Uebungsrunde aus dem Notizblock: nur diese Fragen
        (hoechstens 50). keep_order: die erste Frage kommt zuerst."""
        if self.mode_pills.get() != "uebung":
            if fp.load_running() is not None:
                messagebox.showinfo("Prüfung läuft", "Es läuft gerade eine Prüfung. "
                                                     "Gib sie zuerst ab oder brich sie ab.")
                return
            self.mode_pills.select_value("uebung")
        if self.running:
            self.stop_timer()
            self._reset_controls()
        by_question = {q["q"]: q for q in self.questions}
        session = [by_question[key] for key in questions if key in by_question]
        if not session:
            return
        if not keep_order:
            random.shuffle(session)
        self.session = session[:50]
        self.pool = list(self.session)
        self._begin()

    def start_quiz(self):
        if not self.pool:
            messagebox.showinfo("Hinweis", "Für diese Auswahl gibt es keine Fragen.")
            return
        count = min(self.stepper.get(), len(self.pool))
        if self.status_pills.get() == FILTER_ALL:
            # Unbearbeitete Fragen zuerst, dazwischen Wiederholungen
            keys = self.book.preferred_order(SRC_QUIZ, [q["q"] for q in self.pool],
                                             rng=random.Random())
            by_question = {q["q"]: q for q in self.pool}
            self.session = [by_question[key] for key in keys[:count]]
            random.shuffle(self.session)
        else:
            self.session = random.sample(self.pool, count)
        self._begin()

    def _begin(self):
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
        self._update_pool()

    def jump_to_question(self, question_text):
        if self.mode_pills.get() != "uebung" and fp.load_running() is None:
            self.mode_pills.select_value("uebung")
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
#  KLAUSURSIMULATION (ab 0.51)
# ============================================================================

QUIZ_MODES = [("uebung", "Übung"), ("pruefung", "Prüfung")]
WISO_PAGE = 5


class ExamPanel(ctk.CTkFrame):
    """Pruefungsmodus im Pruefungstrainer: Auswahl, laufende Pruefung mit
    Countdown (ohne Pause), Selbstbewertung mit Kriterien, Ergebnis."""

    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.db = app.db
        self.state = None
        self.task_no = 0
        self.wiso_page = 0
        self.timer_job = None
        self.save_job = None
        self.result = None
        self.body = transparent_frame(self)
        self.body.pack(fill="both", expand=True)

    # -- Allgemein ----------------------------------------------------------

    def _clear(self):
        self._stop_timer()
        for child in self.body.winfo_children():
            child.destroy()

    def _stop_timer(self):
        if self.timer_job is not None:
            try:
                self.app.root.after_cancel(self.timer_job)
            except tk.TclError:
                pass
            self.timer_job = None

    def show(self):
        """Beim Anzeigen: laufende Pruefung fortsetzen oder Auswahl zeigen."""
        self.state = fp.load_running()
        if self.state is None:
            self.show_choice()
        elif self.state["phase"] == "laeuft":
            if fp.seconds_left(self.state) <= 0:
                self._submit(auto=True)
            else:
                self.show_running()
        else:
            self.show_grading()

    def hide(self):
        if self.save_job is not None:   # ab 0.53: geplantes Speichern jetzt erledigen
            self.app.root.after_cancel(self.save_job)
        self._flush_answers()
        self._stop_timer()

    # -- Auswahl ------------------------------------------------------------

    def show_choice(self):
        self._clear()
        intro = Card(self.body, title="Prüfung nach IHK-Vorbild", accent=C["accent"],
                     subtitle="Aufbau nach der Ausbildungsverordnung 2020")
        intro.pack(fill="x")
        make_label(intro.body,
                   "Wie in der echten Prüfung: feste Zeit ohne Pause, alle Aufgaben sind "
                   "Pflicht, keine Musterlösung während der Prüfung. Offene Aufgaben "
                   "bewertest du nach der Abgabe selbst anhand der Musterlösung, WiSo wird "
                   "automatisch ausgewertet. Notenschlüssel der IHK: ab 92 Punkten sehr gut, "
                   "ab 81 gut, ab 67 befriedigend, ab 50 ausreichend, ab 30 mangelhaft.",
                   font=F["small"], fg=C["text_soft"], wraplength=900, justify="left",
                   anchor="w").pack(anchor="w")
        for exam in fp.EXAMS:
            row = ctk.CTkFrame(intro.body, fg_color=C["card_alt"], corner_radius=12,
                               border_width=1, border_color=C["border"])
            row.pack(fill="x", pady=(10, 0))
            text = transparent_frame(row)
            text.pack(side="left", fill="x", expand=True, padx=14, pady=10)
            make_label(text, exam["name"], font=F["body_bold"], fg=C["text"]).pack(anchor="w")
            detail = ("%d Minuten · %d Auswahlfragen · 100 Punkte" % (exam["minuten"],
                                                                      fp.WISO_COUNT)
                      if exam["art"] == fp.WISO else
                      "%d Minuten · 4 Aufgaben zu je 25 Punkten" % exam["minuten"])
            make_label(text, detail, font=F["small"], fg=C["muted"]).pack(anchor="w")
            NeoButton(row, "Starten", lambda a=exam["art"]: self.start(a),
                      kind="primary").pack(side="right", padx=14)
        self._results_cards(self.body)

    def _results_cards(self, parent):
        history = self.db.exams()
        card = Card(parent, title="Letzte Prüfungen", accent=C["purple"],
                    subtitle="%d insgesamt" % len(history))
        card.pack(fill="x", pady=(14, 0))
        if not history:
            make_label(card.body, "Noch keine Prüfung abgelegt.", font=F["small"],
                       fg=C["muted"]).pack(anchor="w")
        for entry in history[:8]:
            exam = fp.EXAM.get(entry["art"])
            row = transparent_frame(card.body)
            row.pack(fill="x", pady=2)
            make_label(row, _german_time(entry["timestamp"]), font=F["small"],
                       fg=C["muted"], width=150, anchor="w").pack(side="left")
            make_label(row, exam["kurz"] if exam else entry["art"], font=F["small_bold"],
                       fg=C["text"], width=110, anchor="w").pack(side="left")
            make_label(row, "%s Punkte" % _points(entry["punkte"]), font=F["small"],
                       fg=C["text_soft"], width=110, anchor="w").pack(side="left")
            make_label(row, entry["note"], font=F["small_bold"],
                       fg=_note_color(entry["punkte"])).pack(side="left")
        overall_card(parent, self.db)

    def start(self, art):
        exam = fp.EXAM[art]
        if not messagebox.askyesno(
                "Prüfung starten",
                "%s\n\nDie Zeit (%d Minuten) läuft sofort und lässt sich nicht anhalten - "
                "auch nicht, wenn du das Programm schließt. Jetzt starten?"
                % (exam["name"], exam["minuten"])):
            return
        self.state = fp.new_exam(art, self.db.exams(), seed=random.randrange(1 << 30))
        fp.save_running(self.state)
        self.task_no = 0
        self.wiso_page = 0
        self.show_running()

    # -- Laufende Pruefung --------------------------------------------------

    def show_running(self):
        self._clear()
        state = self.state
        exam = fp.EXAM[state["art"]]
        head = Card(self.body, title=exam["kurz"], accent=C["accent"], subtitle=exam["name"])
        head.pack(fill="x")
        row = transparent_frame(head.body)
        row.pack(fill="x")
        self.lbl_clock = make_label(row, "", font=F["display"], fg=C["accent"])
        self.lbl_clock.pack(side="left")
        make_label(row, "verbleibend", font=F["small"], fg=C["muted"]).pack(
            side="left", padx=(10, 0), pady=(14, 0))
        NeoButton(row, "Abbrechen", self.cancel, kind="ghost").pack(side="right")
        NeoButton(row, "Abgeben", lambda: self._submit(), kind="primary").pack(
            side="right", padx=10)
        self.lbl_progress = make_label(head.body, "", font=F["small"], fg=C["muted"])
        self.lbl_progress.pack(anchor="w", pady=(6, 0))
        self.task_box = transparent_frame(self.body)
        self.task_box.pack(fill="both", expand=True, pady=(14, 0))
        if state["art"] == fp.WISO:
            self._paint_wiso()
        else:
            options = [(number, "Aufgabe %d" % (number + 1))
                       for number in range(len(state["aufgaben"]))]
            self.task_pills = PillGroup(self.body, options, on_change=self._switch_task,
                                        initial=self.task_no)
            self.task_pills.pack(anchor="w", pady=(14, 0), before=self.task_box)
            self._paint_task()
        self._tick()

    def _tick(self):
        left = fp.seconds_left(self.state)
        self.lbl_clock.configure(text=fp.time_text(left),
                                 text_color=C["red"] if left < 300 else C["accent"])
        if left <= 0:
            self.timer_job = None
            self._submit(auto=True)
            return
        self.timer_job = self.app.root.after(1000, self._tick)

    def _progress(self):
        answers = self.state["antworten"]
        if self.state["art"] == fp.WISO:
            done = sum(1 for q in self.state["fragen"] if answers.get(q))
            return "%d von %d Fragen beantwortet" % (done, len(self.state["fragen"]))
        total = sum(len(fp.task_details(self.state, n)["teile"])
                    for n in range(len(self.state["aufgaben"])))
        done = sum(1 for value in answers.values() if value.strip())
        return "%d von %d Teilaufgaben bearbeitet" % (done, total)

    def _switch_task(self, number):
        self._flush_answers()
        self.task_no = number
        self._paint_task()

    def _paint_task(self):
        for child in self.task_box.winfo_children():
            child.destroy()
        details = fp.task_details(self.state, self.task_no)
        card = Card(self.task_box, title="Aufgabe %d" % (self.task_no + 1),
                    accent=C["purple"], subtitle="%s · 25 Punkte" % details["titel"])
        card.pack(fill="x")
        if details["einleitung"]:
            make_label(card.body, details["einleitung"], font=F["body"], fg=C["text_soft"],
                       wraplength=900, justify="left", anchor="w").pack(anchor="w")
        self.answer_boxes = {}
        for part_no, part in enumerate(details["teile"]):
            key = fp.answer_key(self.task_no, part_no)
            make_label(card.body, "%s) %s  (%d Punkte)" % (chr(97 + part_no), part["text"],
                                                          part["punkte"]),
                       font=F["body_bold"], fg=C["text"], wraplength=900, justify="left",
                       anchor="w").pack(anchor="w", pady=(14, 6))
            box = make_autogrow_text(card.body, min_height=4, max_height=16)
            box.pack(fill="x")
            set_text(box, self.state["antworten"].get(key, ""))
            box.bind("<KeyRelease>", lambda _e: self._schedule_save(), add="+")
            self.answer_boxes[key] = box
        self.lbl_progress.configure(text=self._progress())

    def _paint_wiso(self):
        for child in self.task_box.winfo_children():
            child.destroy()
        questions = self.state["fragen"]
        pages = (len(questions) + WISO_PAGE - 1) // WISO_PAGE
        card = Card(self.task_box, title="Wirtschafts- und Sozialkunde", accent=C["purple"],
                    subtitle="Seite %d von %d" % (self.wiso_page + 1, pages))
        card.pack(fill="x")
        by_question = {q["q"]: q for q in QUIZ_QUESTIONS}
        start = self.wiso_page * WISO_PAGE
        for number, question in enumerate(questions[start:start + WISO_PAGE], start=start):
            make_label(card.body, "%d. %s" % (number + 1, question), font=F["body_bold"],
                       fg=C["text"], wraplength=900, justify="left",
                       anchor="w").pack(anchor="w", pady=(12, 4))
            options = OptionList(card.body, bg=C["card"],
                                 on_change=lambda value, q=question: self._choose(q, value))
            options.pack(fill="x")
            options.set_options(self.state["optionen"].get(question) or
                                by_question[question]["options"])
            chosen = self.state["antworten"].get(question)
            if chosen:
                options._selected = chosen
                for row in options._rows:
                    row["state"] = "selected" if row["text"] == chosen else "idle"
                    options._paint(row)
        nav = transparent_frame(self.task_box)
        nav.pack(fill="x", pady=(14, 0))
        back = NeoButton(nav, "Zurück", lambda: self._wiso_turn(-1), kind="ghost")
        back.pack(side="left")
        back.set_enabled(self.wiso_page > 0)
        forward = NeoButton(nav, "Weiter", lambda: self._wiso_turn(1), kind="ghost")
        forward.pack(side="left", padx=10)
        forward.set_enabled(self.wiso_page < pages - 1)
        self.lbl_progress.configure(text=self._progress())

    def _wiso_turn(self, delta):
        self.wiso_page += delta
        self._paint_wiso()
        self.app.views["quiz"].to_top()

    def _choose(self, question, value):
        self.state["antworten"][question] = value
        fp.save_running(self.state)
        self.lbl_progress.configure(text=self._progress())

    def _schedule_save(self):
        if self.save_job is not None:
            self.app.root.after_cancel(self.save_job)
        self.save_job = self.app.root.after(1200, self._flush_answers)

    def _flush_answers(self):
        self.save_job = None
        if not self.state or self.state.get("phase") != "laeuft" or \
                self.state["art"] == fp.WISO:
            return
        boxes = getattr(self, "answer_boxes", {})
        changed = False
        for key, box in boxes.items():
            try:
                value = box.get("1.0", "end").rstrip("\n")
            except tk.TclError:
                continue
            if self.state["antworten"].get(key, "") != value:
                self.state["antworten"][key] = value
                changed = True
        if changed:
            fp.save_running(self.state)
            try:
                self.lbl_progress.configure(text=self._progress())
            except tk.TclError:
                pass

    def cancel(self):
        if not messagebox.askyesno("Prüfung abbrechen",
                                   "Die Prüfung wirklich abbrechen? Deine Antworten werden "
                                   "verworfen und es gibt kein Ergebnis."):
            return
        fp.clear_running()
        self.state = None
        self.show_choice()

    def _submit(self, auto=False):
        if not auto and not messagebox.askyesno(
                "Abgeben", "Prüfung jetzt abgeben? Danach kannst du nichts mehr ändern."):
            return
        self._flush_answers()
        self._stop_timer()
        fp.submit(self.state)
        if self.state["art"] == fp.WISO:
            self._finish()
            return
        fp.save_running(self.state)
        if auto:
            messagebox.showinfo("Zeit abgelaufen", "Die Zeit ist um, die Prüfung wurde "
                                                   "abgegeben. Jetzt folgt die Bewertung.")
        self.task_no = 0
        self.show_grading()

    # -- Bewertung ----------------------------------------------------------

    def show_grading(self):
        self._clear()
        state = self.state
        exam = fp.EXAM[state["art"]]
        head = Card(self.body, title="Bewertung", accent=C["green"], subtitle=exam["name"])
        head.pack(fill="x")
        make_label(head.body,
                   "Vergleiche deine Antwort mit der Musterlösung und hake ab, was du "
                   "hattest. Die Punkte werden vorgeschlagen, du kannst sie wie ein Prüfer "
                   "anpassen.", font=F["small"], fg=C["text_soft"], wraplength=900,
                   justify="left", anchor="w").pack(anchor="w")
        row = transparent_frame(head.body)
        row.pack(fill="x", pady=(10, 0))
        self.lbl_sum = make_label(row, "", font=F["body_bold"], fg=C["text"])
        self.lbl_sum.pack(side="left")
        NeoButton(row, "Bewertung abschließen", self._finish, kind="primary").pack(
            side="right")
        options = [(number, "Aufgabe %d" % (number + 1))
                   for number in range(len(state["aufgaben"]))]
        PillGroup(self.body, options, on_change=self._grade_task,
                  initial=self.task_no).pack(anchor="w", pady=(14, 0))
        self.task_box = transparent_frame(self.body)
        self.task_box.pack(fill="both", expand=True, pady=(14, 0))
        self._paint_grading()

    def _grade_task(self, number):
        self.task_no = number
        self._paint_grading()
        self.app.views["quiz"].to_top()

    def _sum_text(self):
        total = 0
        for number in range(len(self.state["aufgaben"])):
            for part_no, _part in enumerate(fp.task_details(self.state, number)["teile"]):
                total += int(self.state["punkte"].get(fp.answer_key(number, part_no), 0))
        return "Zwischenstand: %d von 100 Punkten" % total

    def _paint_grading(self):
        for child in self.task_box.winfo_children():
            child.destroy()
        details = fp.task_details(self.state, self.task_no)
        card = Card(self.task_box, title="Aufgabe %d" % (self.task_no + 1),
                    accent=C["purple"], subtitle="%s · %s" % (details["titel"],
                                                             details["thema"]))
        card.pack(fill="x")
        for part_no, part in enumerate(details["teile"]):
            key = fp.answer_key(self.task_no, part_no)
            make_label(card.body, "%s) %s  (%d Punkte)" % (chr(97 + part_no), part["text"],
                                                          part["punkte"]),
                       font=F["body_bold"], fg=C["text"], wraplength=900, justify="left",
                       anchor="w").pack(anchor="w", pady=(14, 6))
            make_label(card.body, "DEINE ANTWORT", font=F["label"],
                       fg=C["muted"]).pack(anchor="w")
            own = make_autogrow_text(card.body, min_height=2, max_height=12)
            own.pack(fill="x", pady=(4, 8))
            set_text(own, self.state["antworten"].get(key, "") or "(keine Antwort)")
            own.configure(state="disabled")
            make_label(card.body, "MUSTERLÖSUNG · KRITERIEN", font=F["label"],
                       fg=C["muted"]).pack(anchor="w")
            marks = self.state["kriterien"].setdefault(key, [False] * len(part["kriterien"]))
            stepper_holder = {}

            def toggled(index, var, key=key, part=part, marks=marks, holder=stepper_holder):
                marks[index] = bool(var.get())
                points = fp.suggested_points(part["punkte"], marks)
                self.state["punkte"][key] = points
                holder["stepper"].value = points
                holder["stepper"]._change(0)
                fp.save_running(self.state)

            for index, criterion in enumerate(part["kriterien"]):
                var = tk.BooleanVar(value=marks[index] if index < len(marks) else False)
                ctk.CTkCheckBox(card.body, text=criterion, variable=var,
                                command=lambda i=index, v=var, t=toggled: t(i, v),
                                font=F["small"], text_color=C["text_soft"],
                                fg_color=C["green"], border_color=C["border_hi"],
                                hover_color=C["card_hi"]).pack(anchor="w", pady=2)
            row = transparent_frame(card.body)
            row.pack(anchor="w", pady=(8, 0))
            make_label(row, "Punkte", font=F["small"], fg=C["text_dim"]).pack(
                side="left", padx=(0, 10))

            def changed(value, key=key):
                self.state["punkte"][key] = value
                fp.save_running(self.state)
                self.lbl_sum.configure(text=self._sum_text())

            stepper = NumberStepper(row, value=int(self.state["punkte"].get(key, 0)),
                                    minimum=0, maximum=part["punkte"], step=1, bg=C["card"],
                                    on_change=changed)
            stepper.pack(side="left")
            make_label(row, "von %d" % part["punkte"], font=F["small"],
                       fg=C["muted"]).pack(side="left", padx=(10, 0))
            stepper_holder["stepper"] = stepper
        self.lbl_sum.configure(text=self._sum_text())

    def _finish(self):
        if self.state["art"] != fp.WISO and not messagebox.askyesno(
                "Bewertung abschließen", "Bewertung abschließen und das Ergebnis "
                                         "speichern?"):
            return
        self.result = fp.finish(self.db, self.state)
        art = self.state["art"]
        self.state = None
        self.app.notify_progress()
        self.show_result(art)

    # -- Ergebnis -----------------------------------------------------------

    def show_result(self, art):
        self._clear()
        result = self.result
        exam = fp.EXAM[art]
        card = Card(self.body, title="Ergebnis", accent=C["green"], subtitle=exam["name"])
        card.pack(fill="x")
        row = transparent_frame(card.body)
        row.pack(fill="x")
        make_label(row, "%s Punkte" % _points(result["punkte"]), font=F["display"],
                   fg=_note_color(result["punkte"])).pack(side="left")
        make_label(row, "IHK-Note %s  ·  Dauer %s" % (result["note"],
                                                     fp.time_text(result["dauer"])),
                   font=F["body_bold"], fg=C["text"]).pack(side="left", padx=(18, 0),
                                                            pady=(12, 0))
        details = result["daten"]
        if art == fp.WISO:
            make_label(card.body, "%d von %d Fragen richtig" % (
                details["richtig"], len(details["fragen"])), font=F["body"],
                fg=C["text_soft"]).pack(anchor="w", pady=(10, 0))
        else:
            for number, task in enumerate(details["aufgaben"], start=1):
                make_label(card.body, "Aufgabe %d · %s: %d von %d Punkten" % (
                    number, task["titel"], task["punkte"], task["max"]),
                    font=F["body"], fg=C["text_soft"], anchor="w").pack(anchor="w",
                                                                        pady=(6, 0))
        themes = Card(self.body, title="Nach Themen", accent=C["purple"],
                      subtitle="Schwachstellen rot")
        themes.pack(fill="x", pady=(14, 0))
        for name, (reached, maximum) in sorted(details["themen"].items()):
            share = reached / maximum * 100 if maximum else 0
            bar = GradientBar(themes.body, name, C["red"] if share < 50 else C["green"],
                              C["orange"] if share < 50 else C["accent"],
                              parent_bg=C["card"])
            bar.pack(fill="x", pady=4)
            bar.set(share, "%s von %s" % (_points(reached), _points(maximum)))
        weak = fp.weak_topics(result)
        if weak:
            make_label(themes.body, "Üben: " + ", ".join(weak), font=F["small_bold"],
                       fg=C["red"], wraplength=900, justify="left",
                       anchor="w").pack(anchor="w", pady=(8, 0))
        NeoButton(self.body, "Zur Prüfungsauswahl", self.show_choice,
                  kind="ghost").pack(anchor="w", pady=(14, 0))


def _points(value):
    return ("%.1f" % value).replace(".", ",").replace(",0", "")


def _note_color(points):
    return C["green"] if points >= 67 else C["yellow"] if points >= 50 else C["red"]


def overall_card(parent, db):
    """Kachel "Gesamtergebnis" (ab 0.51): letzte Simulation je Bereich plus
    geschaetzte Projektnote, Gewichtung und Bestehensregeln nach § 24."""
    scores = fp.latest_results(db.exams())
    project = fpj.projects(db)
    active = fpj.active_project(db, fisi_update.load_settings()) if project else None
    estimate = fpj.estimate(project.get(active, {})) if active else None
    if estimate is not None:
        scores["projekt"] = estimate
    card = Card(parent, title="Gesamtergebnis", accent=C["green"],
                subtitle="Gewichtung 20 / 50 / 10 / 10 / 10 %")
    card.pack(fill="x", pady=(14, 0))
    lines = []
    for area in fp.WEIGHTS:
        value = scores.get(area)
        lines.append("%s (%d %%): %s" % (fp.AREA_NAME[area], fp.WEIGHTS[area],
                                         "%s Punkte" % _points(value) if value is not None
                                         else "noch offen"))
    make_label(card.body, "\n".join(lines), font=F["small"], fg=C["text_soft"],
               justify="left", anchor="w").pack(anchor="w")
    result = fp.overall(scores)
    if not result["complete"]:
        hint = "Für das Gesamtergebnis fehlt noch: %s." % ", ".join(result["fehlend"])
        if "Projekt" in result["fehlend"]:
            hint += " Die Projektnote schätzt du im Abschlussprojekt unter „Übersicht“."
        make_label(card.body, hint, font=F["small"], fg=C["muted"], wraplength=900,
                   justify="left", anchor="w").pack(anchor="w", pady=(10, 0))
        return
    make_label(card.body, "Gesamt %s Punkte · Note %s · %s" % (
        _points(result["gesamt"]), result["note"],
        "bestanden" if result["bestanden"] else "nicht bestanden"),
        font=F["body_bold"], fg=C["green"] if result["bestanden"] else C["red"]).pack(
            anchor="w", pady=(10, 4))
    for text, ok in result["regeln"]:
        make_label(card.body, ("erfüllt:  " if ok else "offen:  ") + text, font=F["small"],
                   fg=C["green"] if ok else C["red"], anchor="w").pack(anchor="w")
    if result["ergaenzung"]:
        make_label(card.body, result["ergaenzung"], font=F["small"], fg=C["yellow"],
                   wraplength=900, justify="left", anchor="w").pack(anchor="w", pady=(8, 0))


# ============================================================================
#  AP2-SZENARIEN
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
    TABLE = "scenario_events"
    SOURCE = SRC_AP2

    def build(self):
        self.index = 0
        self.solution_visible = False
        # Aufgedeckt, aber noch nicht bewertet (Selbsteinschaetzung ab 0.39)
        self.pending = None
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
        self.paged = PagedList(
            list_card.body, self.DATA, self.load_scenario,
            subtitle=lambda item: item["theme"],
            status_source=lambda: position_statuses(StatusBook(self.db), self.SOURCE),
            group_field="theme", group_label="Thema")
        self.paged.refresh()

        detail = transparent_frame(layout)
        detail.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self.task_card = Card(detail, title="Aufgabenstellung", accent=C["accent"])
        self.task_card.pack(fill="both", expand=True)
        self.lbl_status = make_label(self.task_card.body, "", font=F["small_bold"],
                                     fg=C["muted"], anchor="w")
        self.lbl_status.pack(anchor="w")
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
        self.rate_box = rate_box(self.sol_card.body, self.rate)

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

    def on_show(self):
        # Der Lernstand kann sich durch einen Abgleich geaendert haben
        self.paged.refresh(keep_page=True)
        self._show_status()

    def _show_status(self):
        text, key = status_label(StatusBook(self.db), self.SOURCE, self.index)
        self.lbl_status.configure(text=text, text_color=status_color(key))

    def _flush(self):
        """Aufgedeckt, aber nicht bewertet: als angesehen speichern."""
        if self.pending is not None:
            position, self.pending = self.pending, None
            self._log(self.DATA[position], position, None)
            self.app.notify_progress()

    def rate(self, correct):
        """Selbsteinschaetzung "Gewusst" / "Nicht gewusst"."""
        position, self.pending = self.pending, None
        if position is None:
            return
        self.rate_box.pack_forget()
        self._log(self.DATA[position], position, correct)
        self.app.notify_progress()
        self.paged.refresh(keep_page=True)
        self._show_status()

    def load_scenario(self, position):
        self._flush()
        self.index = position
        scenario = self.DATA[position]
        self.rate_box.pack_forget()
        self.lbl_title.configure(text=scenario["title"])
        set_text(self.txt_task, scenario["text"])
        self.solution_visible = False
        set_text(self.txt_solution,
                 "Die Musterlösung ist noch ausgeblendet.\n\n"
                 "Bearbeite die Aufgabe zuerst selbst und decke die Lösung "
                 "anschließend auf.")
        self.btn_toggle.set_text("Musterlösung anzeigen")
        set_text(self.txt_own, self.own_answers.get(position, ""))
        self.paged.refresh(keep_page=True)
        self.paged.show(position)
        self._show_status()

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
            if self.pending is None:
                self.pending = self.index
                self.rate_box.pack(anchor="w", pady=(12, 0))

    def _log(self, scenario, position, correct):
        """In Unterklassen ueberschrieben - schreibt in die passende DB-Tabelle."""
        raise NotImplementedError

    def next_scenario(self):
        self.load_scenario(self.paged.next_after(self.index))


class ScenarioView(ScenarioViewBase):
    """AP2-Szenarien (Schwerpunktpruefung: Netzwerk, Sicherheit, Systeme, Wirtschaft)."""

    DATA = SZENARIEN
    LIST_TITLE = "AP2-Szenarien"

    def _log(self, scenario, position, correct):
        self.db.log_scenario(position, scenario["title"], scenario["theme"], correct)


class Ap1ScenarioView(ScenarioViewBase):
    """AP1-Szenarien (Grundlagenpruefung aus dem 1./2. Lehrjahr)."""

    DATA = AP1_SZENARIEN
    LIST_TITLE = "AP1-Szenarien"
    TABLE = "ap1_events"
    SOURCE = SRC_AP1

    def _log(self, scenario, position, correct):
        self.db.log_ap1(position, scenario["title"], scenario["theme"], correct)


# ============================================================================
#  TESTPROJEKT
# ============================================================================

class ProjectView(View):
    """Uebt die komplette Projektarbeit an einem realistischen Kundenauftrag:
    Ausgangssituation, Auftrag, Rahmenbedingungen und Arbeitsauftraege zum
    selbststaendigen Bearbeiten, dazu Loesungsansaetze zum Vergleich."""

    def build(self):
        self.index = 0
        self.hints_visible = False
        self.pending = None

        layout = transparent_frame(self.content)
        layout.pack(fill="both", expand=True)
        layout.columnconfigure(0, weight=2, uniform="proj")
        layout.columnconfigure(1, weight=5, uniform="proj")

        list_card = Card(layout, title="Testprojekte",
                         subtitle="%d Kundenaufträge" % len(PROJEKTARBEITEN))
        list_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.paged = PagedList(
            list_card.body, PROJEKTARBEITEN, self.load_project,
            subtitle=lambda item: "%s · %s" % (item["schwierigkeit"],
                                               CATEGORY_SHORT[item["cat"]]),
            status_source=lambda: position_statuses(StatusBook(self.db), SRC_PROJECT),
            category_filter=True,
            group_field="schwierigkeit", group_label="Schwierigkeit")
        self.paged.refresh()

        detail = transparent_frame(layout)
        detail.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self.header_label = make_label(detail, "", font=F["h2"], fg=C["text"],
                                       wraplength=760, justify="left", anchor="w")
        self.header_label.pack(anchor="w")
        self.meta_label = make_label(detail, "", font=F["small"], fg=C["muted"])
        self.meta_label.pack(anchor="w", pady=(2, 0))
        self.lbl_status = make_label(detail, "", font=F["small_bold"], fg=C["muted"],
                                     anchor="w")
        self.lbl_status.pack(anchor="w", pady=(2, 12))

        self.task_card = Card(detail, title="Kundenauftrag", accent=C["accent"])
        self.task_card.pack(fill="both", expand=True)
        self.txt_task = make_text(self.task_card.body, height=14, readonly=True)
        self.txt_task.pack(fill="both", expand=True)

        self.hint_card = Card(detail, title="Lösungsansätze", accent=C["green"])
        self.hint_card.pack(fill="both", expand=True, pady=(14, 0))
        self.txt_hints = make_text(self.hint_card.body, height=14, readonly=True)
        self.txt_hints.pack(fill="both", expand=True)
        self.rate_box = rate_box(self.hint_card.body, self.rate)

        controls = transparent_frame(detail)
        controls.pack(fill="x", pady=(14, 0))
        self.btn_toggle = NeoButton(controls, "Lösungsansätze anzeigen",
                                    self.toggle_hints, kind="primary")
        self.btn_toggle.pack(side="left")
        NeoButton(controls, "Nächstes Projekt", self.next_project,
                  kind="ghost", icon="arrow_right").pack(side="left", padx=10)
        # Ab 0.51: als Vorlage fuers eigene Abschlussprojekt
        NeoButton(controls, "Als Vorlage fürs Abschlussprojekt", self.use_as_template,
                  kind="ghost").pack(side="right")

        self.load_project(0)

    def on_show(self):
        self._highlight()

    def _highlight(self):
        """Lernstand der Projekte auffrischen (auch nach einem Abgleich)."""
        self.paged.refresh(keep_page=True)
        text, key = status_label(StatusBook(self.db), SRC_PROJECT, self.index)
        self.lbl_status.configure(text=text, text_color=status_color(key))

    def _flush(self):
        """Aufgedeckt, aber nicht bewertet: als angesehen speichern."""
        if self.pending is not None:
            position, self.pending = self.pending, None
            project = PROJEKTARBEITEN[position]
            self.db.log_project(position, project["title"], project["cat"], None)
            self.app.notify_progress()

    def rate(self, correct):
        """Selbsteinschaetzung "Gewusst" / "Nicht gewusst"."""
        position, self.pending = self.pending, None
        if position is None:
            return
        self.rate_box.pack_forget()
        project = PROJEKTARBEITEN[position]
        self.db.log_project(position, project["title"], project["cat"], correct)
        self.app.notify_progress()
        self._highlight()

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
        self._flush()
        self.index = position
        self.rate_box.pack_forget()
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
        self.paged.show(position)

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
            if self.pending is None:
                self.pending = self.index
                self.rate_box.pack(anchor="w", pady=(12, 0))

    def next_project(self):
        self.load_project(self.paged.next_after(self.index))

    def use_as_template(self):
        self.app.show_view("abschluss")
        self.app.views["abschluss"].use_template(self.index)


# ============================================================================
#  ABSCHLUSSPROJEKT (AB 0.51)
# ============================================================================

PROJECT_SAVE_DELAY = 800      # ms nach dem letzten Tastendruck
NO_CATEGORY = "Kein Fachbereich"


class FinalProjectView(View):
    """Arbeitsbereich fuers eigene IHK-Abschlussprojekt: Uebersicht, Antrag,
    Zeitplan, Kosten, Dokumentation und Fachgespraech. Jede Eingabe wird
    kurz nach dem Tippen gespeichert (Tabelle abschlussprojekt) und mit dem
    Handy abgeglichen. Die Reiter werden erst beim ersten Oeffnen aufgebaut
    und danach wiederverwendet (wie die Ansichten seit 0.48/0.50)."""

    def build(self):
        self.project = None
        self.fields = {}
        self.inputs = {}         # feld -> Funktion, die den Eingabewert liefert
        self.pending = set()
        self.save_job = None
        self.derived = {}        # reiter -> Funktion, die berechnete Werte auffrischt
        self.tab_frames = {}
        self.tab = fpj.TABS[0][0]
        self.fg_index = 0
        self.fg_hint = False
        self.stamp = None
        self.project_ids = []

        top = transparent_frame(self.content)
        top.pack(fill="x")
        make_label(top, "Projekt", font=F["small"], fg=C["text_dim"]).pack(
            side="left", padx=(0, 10))
        self.menu_project = option_menu(top, ["-"], command=self._choose_project, width=320)
        self.menu_project.pack(side="left")
        NeoButton(top, "Neues Projekt", self._new_project, kind="ghost", height=34,
                  font=F["small_bold"]).pack(side="left", padx=(10, 0))
        NeoButton(top, "Löschen", self._delete_project, kind="ghost", height=34,
                  font=F["small_bold"]).pack(side="left", padx=(8, 0))
        NeoButton(top, "Als Text", lambda: self._export("txt"), kind="ghost", height=34,
                  font=F["small_bold"]).pack(side="right")
        NeoButton(top, "Als PDF", lambda: self._export("pdf"), kind="primary", height=34,
                  font=F["small_bold"]).pack(side="right", padx=(0, 8))

        self.tab_pills = PillGroup(self.content, fpj.TABS, on_change=self._on_tab)
        self.tab_pills.pack(anchor="w", pady=(14, 14))
        self.tab_area = transparent_frame(self.content)
        self.tab_area.pack(fill="both", expand=True)
        self._load_project()

    # -- Projekte -----------------------------------------------------------

    def _load_project(self, project=None):
        """Projekt laden (ohne Angabe: das aktive dieses Geraets) und die
        Reiter neu aufbauen."""
        self._flush()
        settings = fisi_update.load_settings()
        self.project = project or fpj.active_project(self.db, settings)
        if settings.get(fpj.ACTIVE_KEY) != self.project:
            settings[fpj.ACTIVE_KEY] = self.project
            fisi_update.save_settings(settings)
        self.fields = dict(fpj.projects(self.db).get(self.project, {}))
        self.stamp = self.db.change_stamp()
        self.fg_index = 0
        self._fill_project_menu()
        for frame in self.tab_frames.values():
            frame.destroy()
        self.tab_frames = {}
        self.inputs = {}
        self.derived = {}
        self._on_tab(self.tab)

    def _fill_project_menu(self):
        existing = fpj.projects(self.db)
        if self.project not in existing:
            existing[self.project] = self.fields
        self.project_ids = sorted(existing, key=lambda key: fpj.project_title(
            existing[key]).lower())
        labels = []
        for key in self.project_ids:
            label = fpj.project_title(self.fields if key == self.project else existing[key])
            while label in labels:
                label += " "
            labels.append(label)
        self.menu_project.configure(values=labels)
        self.menu_project.set(labels[self.project_ids.index(self.project)])
        self.project_labels = labels

    def _choose_project(self, label):
        if label in self.project_labels:
            key = self.project_ids[self.project_labels.index(label)]
            if key != self.project:
                self._load_project(key)

    def _new_project(self):
        self._flush()
        self._load_project(fpj.create_project(self.db))
        self.app.notify_progress(refresh_view=False)

    def _delete_project(self):
        if not messagebox.askyesno(
                "Projekt löschen",
                "„%s“ mit allen Eingaben löschen? Das lässt sich nicht rückgängig machen "
                "und gilt nach dem Abgleich auch auf dem Handy."
                % fpj.project_title(self.fields)):
            return
        self.pending.clear()
        fpj.delete_project(self.db, self.project)
        settings = fisi_update.load_settings()
        settings.pop(fpj.ACTIVE_KEY, None)
        fisi_update.save_settings(settings)
        self.project = None
        self._load_project()
        self.app.notify_progress(refresh_view=False)

    def _export(self, extension):
        self._flush()
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            parent=self.app.root, title="Abschlussprojekt speichern",
            initialfile=fpj.export_name(self.fields, extension),
            defaultextension="." + extension,
            filetypes=[("PDF-Dokument", "*.pdf")] if extension == "pdf"
            else [("Textdatei", "*.txt")])
        if not path:
            return
        try:
            if extension == "pdf":
                data = fpj.export_pdf(self.fields)
            else:
                # ab 0.53: mit BOM und Windows-Zeilenenden, damit auch aeltere
                # Windows-Editoren die Umlaute richtig zeigen
                data = fpj.export_text(self.fields).replace("\n", "\r\n").encode("utf-8-sig")
            with open(path, "wb") as handle:
                handle.write(data)
        except OSError as error:
            messagebox.showerror("Speichern fehlgeschlagen", str(error))
            return
        show_badge_toast(self.app.root, "Gespeichert: %s" % os.path.basename(path))

    def use_template(self, position):
        """Testprojekt als Vorlage uebernehmen (aus der Ansicht "Testprojekt")."""
        self._flush()
        count = fpj.apply_template(self.db, self.project, position)
        self._load_project(self.project)
        show_badge_toast(self.app.root, "%s aus dem Testprojekt übernommen"
                         % plural(count, "Feld", "Felder")
                         if count else "Alle passenden Felder waren schon ausgefüllt")

    # -- Speichern ----------------------------------------------------------

    def _changed(self, field):
        self.pending.add(field)
        if self.save_job is not None:
            try:
                self.app.root.after_cancel(self.save_job)
            except tk.TclError:
                pass
        self.save_job = self.app.root.after(PROJECT_SAVE_DELAY, self._flush)

    def _flush(self):
        """Geaenderte Felder speichern (auch beim Verlassen und Beenden)."""
        self.save_job = None
        if not self.pending or self.project is None:
            self.pending.clear()
            return
        fields, self.pending = self.pending, set()
        changed = False
        title_changed = False
        for field in fields:
            getter = self.inputs.get(field)
            if getter is None:
                continue
            value = getter()
            if value != self.fields.get(field, ""):
                self.db.save_project_field(self.project, field, value)
                self.fields[field] = value
                changed = True
                title_changed = title_changed or field == fpj.TITLE_FIELD
        if changed:
            self.stamp = self.db.change_stamp()
            if title_changed:
                self._fill_project_menu()
            self._refresh_derived()

    def _set(self, field, value):
        """Sofort speichern (Haken, Auswahl, Bewertung)."""
        if self.fields.get(field, "") != value:
            self.db.save_project_field(self.project, field, value)
            self.fields[field] = value
            self.stamp = self.db.change_stamp()
            self._refresh_derived()

    def _refresh_derived(self):
        for refresh in self.derived.values():
            refresh()

    def on_show(self):
        # Nach einem Abgleich koennen neue Eingaben vom Handy da sein
        if self.pending:
            return
        if self.db.change_stamp() != self.stamp:
            fields = fpj.projects(self.db)
            if self.project not in fields or fields[self.project] != self.fields:
                self._load_project(self.project if self.project in fields else None)
            else:
                self.stamp = self.db.change_stamp()

    # -- Bausteine ----------------------------------------------------------

    def _entry(self, parent, field, default="", width=30):
        box = EntryBox(parent, width=width, value=self.fields.get(field, default))
        box.bind("<KeyRelease>", lambda _e: self._changed(field), add="+")
        box.bind("<FocusOut>", lambda _e: self._flush(), add="+")
        self.inputs[field] = lambda: box.get().strip()
        return box

    def _textarea(self, parent, field, min_height=3, max_height=14):
        box = make_autogrow_text(parent, min_height=min_height, max_height=max_height)
        set_text(box, self.fields.get(field, ""))
        box.autogrow_resize()
        box.bind("<KeyRelease>", lambda _e: self._changed(field), add="+")
        box.bind("<FocusOut>", lambda _e: self._flush(), add="+")
        self.inputs[field] = lambda: box.get("1.0", "end-1c").rstrip()
        return box

    def _checklist(self, parent, items):
        for key, text in items:
            var = tk.BooleanVar(value=fpj.checked(self.fields, key))
            ctk.CTkCheckBox(parent, text=text, variable=var,
                            command=lambda k=key, v=var: self._set(
                                "check_" + k, "1" if v.get() else "0"),
                            font=F["small"], text_color=C["text_soft"],
                            fg_color=C["green"], border_color=C["border_hi"],
                            hover_color=C["card_hi"]).pack(anchor="w", pady=2)

    @staticmethod
    def _hint(parent, text):
        make_label(parent, text, font=F["small"], fg=C["muted"], wraplength=860,
                   justify="left", anchor="w").pack(anchor="w", pady=(0, 6))

    @staticmethod
    def _form_row(parent, label):
        row = transparent_frame(parent)
        row.pack(fill="x", pady=4)
        make_label(row, label, font=F["small"], fg=C["text_dim"], width=340,
                   anchor="w").pack(side="left")
        return row

    # -- Reiter -------------------------------------------------------------

    def _on_tab(self, tab):
        self._flush()
        self.tab = tab
        for frame in self.tab_frames.values():
            frame.pack_forget()
        frame = self.tab_frames.get(tab)
        if frame is None:
            frame = self.tab_frames[tab] = transparent_frame(self.tab_area)
            getattr(self, "_build_" + tab)(frame)
        frame.pack(fill="both", expand=True)
        self.tab_pills.select_value(tab, notify=False)
        self._refresh_derived()

    def _build_uebersicht(self, frame):
        card = Card(frame, title="Eckdaten", accent=C["accent"],
                    subtitle="Fristen und Seitenzahl legt deine IHK fest")
        card.pack(fill="x")
        for field, label, _multi in fpj.OVERVIEW_FIELDS:
            self._entry(self._form_row(card.body, label), field, width=48).pack(
                side="left", fill="x", expand=True)
        row = self._form_row(card.body, "Fachbereich (für das Fachgespräch)")
        values = [NO_CATEGORY] + list(CATEGORIES)
        menu = option_menu(row, values, command=self._set_category, width=320)
        menu.set(self.fields.get("fachbereich") or NO_CATEGORY)
        menu.pack(side="left")

        state = Card(frame, title="Stand", accent=C["green"],
                     subtitle="Vom Antrag bis zum Fachgespräch")
        state.pack(fill="x", pady=(14, 0))
        lbl_progress = make_label(state.body, "", font=F["body_bold"], fg=C["text"])
        lbl_progress.pack(anchor="w", pady=(0, 8))
        self._checklist(state.body, fpj.CHECKLIST_OVERVIEW)
        lbl_missing = make_label(state.body, "", font=F["small"], fg=C["muted"],
                                 wraplength=860, justify="left", anchor="w")
        lbl_missing.pack(anchor="w", pady=(10, 0))

        grade = Card(frame, title="Geschätzte Projektnote", accent=C["purple"],
                     subtitle="Fließt ins Gesamtergebnis unter Prüfungstrainer ein")
        grade.pack(fill="x", pady=(14, 0))
        self._hint(grade.body, "Die Projektarbeit zählt 50 % der Abschlussprüfung. Trage "
                               "hier ein, wie viele Punkte (0 bis 100) du für Dokumentation, "
                               "Präsentation und Fachgespräch zusammen erwartest.")
        row = self._form_row(grade.body, "Erwartete Punkte (0-100)")
        self._entry(row, fpj.ESTIMATE_FIELD, width=8).pack(side="left")

        template = Card(frame, title="Testprojekt als Vorlage", accent=C["orange"],
                        subtitle="Füllt nur leere Felder")
        template.pack(fill="x", pady=(14, 0))
        self._hint(template.body, "Übernimmt Titel, Ausgangssituation, Auftrag und "
                                  "Rahmenbedingungen eines Testprojekts als Anregung. "
                                  "Bereits ausgefüllte Felder bleiben unverändert.")
        row = transparent_frame(template.body)
        row.pack(fill="x")
        titles = [p["title"] for p in PROJEKTARBEITEN]
        category_menu = option_menu(row, list(CATEGORIES), width=230)
        category_menu.pack(side="left")
        project_menu = option_menu(row, ["-"], width=420)
        project_menu.pack(side="left", padx=(8, 0))

        def fill(category):
            names = [p["title"] for p in PROJEKTARBEITEN if p["cat"] == category]
            project_menu.configure(values=names)
            project_menu.set(names[0])

        category_menu.configure(command=fill)
        fill(CATEGORIES[0])
        NeoButton(row, "Übernehmen",
                  lambda: self.use_template(titles.index(project_menu.get())),
                  kind="ghost", height=34, font=F["small_bold"]).pack(side="left",
                                                                     padx=(8, 0))

        def refresh():
            done, total = fpj.overview_progress(self.fields)
            lbl_progress.configure(text="%d von %d Schritten erledigt" % (done, total))
            missing = fpj.proposal_missing(self.fields)
            lbl_missing.configure(text="Im Antrag noch offen: %s" % ", ".join(missing)
                                  if missing else "Alle Felder des Antrags sind ausgefüllt.")
        self.derived["uebersicht"] = refresh

    def _set_category(self, value):
        self._set("fachbereich", "" if value == NO_CATEGORY else value)
        self.fg_index = 0
        frame = self.tab_frames.pop("fachgespraech", None)
        if frame is not None:
            frame.destroy()
            self.derived.pop("fachgespraech", None)

    def _build_antrag(self, frame):
        card = Card(frame, title="Projektantrag", accent=C["accent"],
                    subtitle="Gliederung wie bei den IHK-Vorlagen")
        card.pack(fill="x")
        for field, name, hint in fpj.PROPOSAL_FIELDS:
            make_label(card.body, name, font=F["body_bold"], fg=C["text"]).pack(
                anchor="w", pady=(12, 2))
            self._hint(card.body, hint)
            self._textarea(card.body, field).pack(fill="x")
        check = Card(frame, title="Prüfe vor dem Einreichen", accent=C["green"])
        check.pack(fill="x", pady=(14, 0))
        self._checklist(check.body, fpj.CHECKLIST_PROPOSAL)

    def _build_zeitplan(self, frame):
        card = Card(frame, title="Zeitplanung", accent=C["accent"],
                    subtitle="Höchstens %d Stunden inklusive Dokumentation" % fpj.MAX_HOURS)
        card.pack(fill="x")
        for key, name, default in fpj.PHASES:
            row = transparent_frame(card.body)
            row.pack(fill="x", pady=4)
            if key.startswith("frei"):
                self._entry(row, "phase_name_" + key, width=40).pack(side="left")
                make_label(row, "  (weitere Phase, frei benennbar)", font=F["small"],
                           fg=C["muted"]).pack(side="left")
            else:
                make_label(row, name, font=F["small"], fg=C["text_dim"], width=420,
                           anchor="w").pack(side="left")
            self._entry(row, "phase_" + key, str(default) if default else "",
                        width=6).pack(side="right")
        lbl_sum = make_label(card.body, "", font=F["body_bold"], fg=C["text"])
        lbl_sum.pack(anchor="w", pady=(12, 0))
        lbl_warn = make_label(card.body, "", font=F["small"], fg=C["yellow"],
                              wraplength=860, justify="left", anchor="w")
        lbl_warn.pack(anchor="w", pady=(4, 0))

        def refresh():
            _rows, total = fpj.schedule(self.fields)
            lbl_sum.configure(text="Summe: %s von %d Stunden" % (fpj.hours_text(total),
                                                               fpj.MAX_HOURS),
                              text_color=C["red"] if total > fpj.MAX_HOURS else C["text"])
            lbl_warn.configure(text="\n".join(fpj.schedule_warnings(self.fields)))
        self.derived["zeitplan"] = refresh

    def _build_kosten(self, frame):
        card = Card(frame, title="Kostenrechnung", accent=C["accent"],
                    subtitle="Stunden kommen aus der Zeitplanung")
        card.pack(fill="x")
        for key, label, default in fpj.COST_FIELDS:
            self._entry(self._form_row(card.body, label), "kosten_" + key, default,
                        width=10).pack(side="left")
        material = Card(frame, title="Sachkosten", accent=C["orange"],
                        subtitle="Hardware, Lizenzen, Material")
        material.pack(fill="x", pady=(14, 0))
        head = transparent_frame(material.body)
        head.pack(fill="x")
        make_label(head, "BEZEICHNUNG", font=F["label"], fg=C["muted"], width=388,
                   anchor="w").pack(side="left")
        make_label(head, "BETRAG", font=F["label"], fg=C["muted"]).pack(side="left",
                                                                      padx=(8, 0))
        for number in range(fpj.MATERIAL_ROWS):
            row = transparent_frame(material.body)
            row.pack(fill="x", pady=3)
            self._entry(row, "material_name_%d" % number, width=40).pack(side="left")
            self._entry(row, "material_betrag_%d" % number, width=10).pack(
                side="left", padx=(8, 0))
            make_label(row, "€", font=F["small"], fg=C["muted"]).pack(side="left",
                                                                    padx=(6, 0))
        result = Card(frame, title="Ergebnis", accent=C["green"])
        result.pack(fill="x", pady=(14, 0))
        lbl_result = make_label(result.body, "", font=F["body"], fg=C["text_soft"],
                                justify="left", anchor="w")
        lbl_result.pack(anchor="w")

        def refresh():
            lbl_result.configure(text="\n".join(fpj.cost_lines(self.fields)))
        self.derived["kosten"] = refresh

    def _build_doku(self, frame):
        card = Card(frame, title="Dokumentation", accent=C["accent"],
                    subtitle="Kapitelgerüst nach üblicher IHK-Gliederung")
        card.pack(fill="x")
        row = self._form_row(card.body, "Seitenvorgabe deiner IHK")
        self._entry(row, fpj.PAGES_FIELD, str(fpj.DEFAULT_PAGES), width=6).pack(side="left")
        lbl_pages = make_label(card.body, "", font=F["body_bold"], fg=C["text"])
        lbl_pages.pack(anchor="w", pady=(8, 0))
        self._hint(card.body, "Grobe Schätzung: etwa %d Zeichen pro Seite (11 pt, "
                              "1,5-zeilig). Deckblatt, Verzeichnisse und Anhang zählen "
                              "meist nicht mit." % fpj.CHARS_PER_PAGE)
        for key, title, hint in fpj.CHAPTERS:
            make_label(card.body, title, font=F["body_bold"], fg=C["text"]).pack(
                anchor="w", pady=(12, 2))
            self._hint(card.body, hint)
            self._textarea(card.body, "kapitel_" + key, min_height=4,
                           max_height=18).pack(fill="x")

        def refresh():
            pages, target = fpj.page_estimate(self.fields)
            lbl_pages.configure(
                text="Etwa %s von %d Seiten" % (("%.1f" % pages).replace(".", ","), target),
                text_color=C["red"] if pages > target else C["text"])
        self.derived["doku"] = refresh

    def _build_fachgespraech(self, frame):
        presentation = Card(frame, title="Präsentation", accent=C["accent"],
                            subtitle="Höchstens 15 Minuten, danach das Fachgespräch")
        presentation.pack(fill="x")
        self._checklist(presentation.body, fpj.CHECKLIST_PRESENTATION)

        questions = fpj.questions_for(self.fields)
        card = Card(frame, title="Fachgespräch üben", accent=C["purple"],
                    subtitle="%d Fragen · allgemeine plus die deines Fachbereichs"
                    % len(questions))
        card.pack(fill="x", pady=(14, 0))
        lbl_stats = make_label(card.body, "", font=F["small"], fg=C["text_dim"])
        lbl_stats.pack(anchor="w")
        lbl_question = make_label(card.body, "", font=F["h3"], fg=C["text"],
                                  wraplength=860, justify="left", anchor="w")
        lbl_question.pack(anchor="w", pady=(10, 4))
        lbl_status = make_label(card.body, "", font=F["small_bold"], fg=C["muted"])
        lbl_status.pack(anchor="w")
        lbl_hint = make_label(card.body, "", font=F["body"], fg=C["text_soft"],
                              wraplength=860, justify="left", anchor="w")
        lbl_hint.pack(anchor="w", pady=(8, 0))
        controls = transparent_frame(card.body)
        controls.pack(fill="x", pady=(12, 0))
        btn_hint = NeoButton(controls, "Hinweis zeigen", lambda: toggle(), kind="primary",
                             height=34, font=F["small_bold"])
        btn_hint.pack(side="left")
        NeoButton(controls, "Nächste Frage", lambda: turn(1), kind="ghost", height=34,
                  font=F["small_bold"], icon="arrow_right").pack(side="left", padx=(8, 0))
        rating = rate_box(card.body, lambda known: rate(known))
        if not questions:
            return

        def paint():
            question = questions[self.fg_index % len(questions)]
            lbl_question.configure(text=question["q"])
            value = fpj.question_rating(self.fields, question["id"])
            lbl_status.configure(text={True: "Gewusst", False: "Nicht gewusst"}.get(
                value, "Noch nicht bewertet"), text_color={True: C["green"],
                                                           False: C["red"]}.get(value,
                                                                                C["muted"]))
            lbl_hint.configure(text=question["hinweis"] if self.fg_hint else "")
            btn_hint.set_text("Hinweis ausblenden" if self.fg_hint else "Hinweis zeigen")
            if self.fg_hint:
                rating.pack(anchor="w", pady=(12, 0))
            else:
                rating.pack_forget()
            ratings = [fpj.question_rating(self.fields, q["id"]) for q in questions]
            lbl_stats.configure(text="Frage %d von %d · %d gewusst · %d nicht gewusst · "
                                     "%d offen" % (self.fg_index % len(questions) + 1,
                                                   len(questions), ratings.count(True),
                                                   ratings.count(False),
                                                   ratings.count(None)))

        def toggle():
            self.fg_hint = not self.fg_hint
            paint()

        def turn(delta):
            self.fg_index = (self.fg_index + delta) % len(questions)
            self.fg_hint = False
            paint()

        def rate(known):
            question = questions[self.fg_index % len(questions)]
            self._set("fg_" + question["id"], "1" if known else "0")
            turn(1)

        self.derived["fachgespraech"] = paint


# ============================================================================
#  NOTIZBLOCK (AB 0.39)
# ============================================================================

# Farbe je Bereich (wie in "Letzte Aktivitaeten")
SOURCE_COLOR_KEY = {SRC_CARD: "accent", SRC_QUIZ: "purple", SRC_AP1: "blue",
                    SRC_AP2: "accent2", SRC_PROJECT: "orange"}
NOTEBOOK_PAGE = 12


class NotebookView(View):
    """Zentrale Uebersicht aller Fragen, die noch geuebt werden muessen (rot:
    zuletzt falsch, gelb: danach erst einmal richtig) - ueber Karteikarten,
    Pruefungstrainer, AP1, AP2 und Testprojekte hinweg."""

    def build(self):
        self.page = 0
        self.entries = []
        self.opened = set()          # Eintraege mit eingeblendeter Musterantwort
        self.book = StatusBook(self.db)

        # Ueberblick je Bereich
        self.summary_card = Card(self.content, title="Lernstand je Bereich",
                                 accent=C["accent"],
                                 subtitle="Abgeschlossen = zweimal hintereinander richtig")
        self.summary_card.pack(fill="x")
        self.summary_grid = transparent_frame(self.summary_card.body)
        self.summary_grid.pack(fill="x")
        for column in range(len(SOURCES)):
            self.summary_grid.columnconfigure(column, weight=1, uniform="nb")

        # Filter
        filter_card = Card(self.content)
        filter_card.pack(fill="x", pady=(14, 0))
        body = filter_card.body
        make_label(body, "FACHBEREICH", font=F["label"], fg=C["muted"]).pack(anchor="w")
        options = [(FILTER_ALL, "Alle")] + [(c, CATEGORY_SHORT[c]) for c in CATEGORIES]
        self.cat_pills = PillGroup(body, options, on_change=self._on_category)
        self.cat_pills.pack(anchor="w", pady=(8, 14))
        make_label(body, "BEREICH", font=F["label"], fg=C["muted"]).pack(anchor="w")
        self.source_pills = PillGroup(body, [(FILTER_ALL, "Alle")] +
                                      [(src, SOURCE_PLURAL[src]) for src in SOURCES],
                                      on_change=lambda _v: self.refresh())
        self.source_pills.pack(anchor="w", pady=(8, 14))
        row = transparent_frame(body)
        row.pack(fill="x")
        box = transparent_frame(row)
        box.pack(side="left")
        make_label(box, "THEMA", font=F["label"], fg=C["muted"]).pack(anchor="w")
        self.topic_menu = TopicMenu(box, self.refresh)
        self.topic_menu.menu.pack(anchor="w", pady=(8, 0))
        self.topic_menu.set_category(FILTER_ALL)
        box = transparent_frame(row)
        box.pack(side="left", padx=(16, 0))
        box.pack(side="left")
        make_label(box, "STATUS", font=F["label"], fg=C["muted"]).pack(anchor="w")
        self.status_pills = PillGroup(box, [(Q_PRACTICE, "Zu üben"), (Q_DONE, "Abgeschlossen"),
                                            (Q_OPEN, "Offen")],
                                      on_change=lambda _v: self.refresh())
        self.status_pills.pack(anchor="w", pady=(8, 0))
        row = transparent_frame(body)
        row.pack(fill="x", pady=(14, 0))
        box = transparent_frame(row)
        box.pack(side="left")
        make_label(box, "MUSTERANTWORTEN", font=F["label"], fg=C["muted"]).pack(anchor="w")
        self.answer_pills = PillGroup(box, [("aus", "Ausblenden"), ("an", "Einblenden")],
                                      on_change=self._toggle_all)
        self.answer_pills.pack(anchor="w", pady=(8, 0))

        # Gezielt ueben
        self.practice_bar = transparent_frame(self.content)
        self.practice_bar.pack(fill="x", pady=(14, 0))

        # Liste
        self.list_card = Card(self.content, title="Zu üben", accent=C["red"])
        self.list_card.pack(fill="x", pady=(14, 0))
        self.rows_box = transparent_frame(self.list_card.body)
        self.rows_box.pack(fill="x")
        pager = transparent_frame(self.list_card.body)
        pager.pack(fill="x", pady=(10, 0))
        IconButton(pager, "arrow_left", lambda: self.turn(-1),
                   parent_bg=C["card"]).pack(side="left")
        self.lbl_page = make_label(pager, "", font=F["small_bold"], fg=C["text_dim"])
        self.lbl_page.pack(side="left", expand=True)
        IconButton(pager, "arrow_right", lambda: self.turn(1),
                   parent_bg=C["card"]).pack(side="right")
        self.refresh()

    def on_show(self):
        # Ab 0.50: steht der Notizblock noch genau so da (gleicher Datenbank-
        # Stempel, gleiche Filter), wird er nicht neu aufgebaut
        key = self._refresh_key()
        if key is not None and key == getattr(self, "_refreshed", None):
            return
        self.refresh(keep_page=True)
        self._refreshed = key

    def _refresh_key(self):
        stamp = self.db.change_stamp() if hasattr(self.db, "change_stamp") else None
        if stamp is None:
            return None
        return (stamp, self.cat_pills.get(), self.topic_menu.get(), self.source_pills.get(),
                self.status_pills.get(), self.answer_pills.get(), self.page)

    def _on_category(self, category):
        self.topic_menu.set_category(category)
        self.refresh()

    def _toggle_all(self, value):
        self.opened = {(e["source"], e["key"]) for e in self.entries} if value == "an" \
            else set()
        self._paint()

    def refresh(self, keep_page=False):
        self.book = StatusBook(self.db)
        category = self.cat_pills.get()
        topic = self.topic_menu.get()
        source = self.source_pills.get()
        status = self.status_pills.get()
        self.entries = notebook_entries(
            self.book, status=status, category=category, topic=topic,
            sources=None if source == FILTER_ALL else [source])
        if self.answer_pills.get() == "an":
            self.opened = {(e["source"], e["key"]) for e in self.entries}
        if not keep_page:
            self.page = 0
        self._paint_summary(category, topic)
        self._paint_practice()
        self._paint()

    def _paint_summary(self, category, topic):
        for child in self.summary_grid.winfo_children():
            child.destroy()
        summary = notebook_summary(self.book, category, topic)
        for column, source in enumerate(SOURCES):
            counts = summary[source]
            total = sum(counts.values()) or 1
            tile = ctk.CTkFrame(self.summary_grid, fg_color=C["card_alt"], corner_radius=12,
                                border_width=1, border_color=C["border"])
            tile.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 6, 0))
            make_label(tile, SOURCE_PLURAL[source], font=F["small_bold"],
                       fg=C[SOURCE_COLOR_KEY[source]]).pack(anchor="w", padx=12, pady=(10, 2))
            make_label(tile, "%d zu üben" % counts[Q_PRACTICE], font=F["h2"],
                       fg=C["red"] if counts[Q_PRACTICE] else C["text_dim"]).pack(
                anchor="w", padx=12)
            make_label(tile, "Abgeschlossen %d von %d" % (counts[Q_DONE], total),
                       font=F["tiny"], fg=C["text_dim"]).pack(anchor="w", padx=12, pady=(4, 0))
            bar = ctk.CTkProgressBar(tile, height=6, width=40, corner_radius=3,
                                     fg_color=C["card_hi"], progress_color=C["green"])
            bar.pack(fill="x", padx=12, pady=(4, 0))
            bar.set(counts[Q_DONE] / float(total))
            make_label(tile, "Offen %d" % counts[Q_OPEN], font=F["tiny"],
                       fg=C["muted"]).pack(anchor="w", padx=12, pady=(4, 10))

    def _practice_keys(self, source):
        return [e["key"] for e in self.entries if e["source"] == source]

    def _paint_practice(self):
        for child in self.practice_bar.winfo_children():
            child.destroy()
        cards = self._practice_keys(SRC_CARD)
        quiz = self._practice_keys(SRC_QUIZ)
        label = {Q_PRACTICE: "üben", Q_DONE: "wiederholen", Q_OPEN: "lernen"}[
            self.status_pills.get()]
        NeoButton(self.practice_bar,
                  "%s %s" % (plural(len(cards), "Karteikarte", "Karteikarten"), label),
                  lambda: self.practice(SRC_CARD, cards), kind="primary").pack(side="left")
        NeoButton(self.practice_bar,
                  "%s %s" % (plural(len(quiz), "Quizfrage", "Quizfragen"), label),
                  lambda: self.practice(SRC_QUIZ, quiz), kind="accent").pack(
            side="left", padx=10)
        make_label(self.practice_bar, "Startet eine Übungsrunde nur mit den Fragen der "
                   "Liste (Quiz: höchstens 50).", font=F["small"], fg=C["muted"]).pack(
            side="left", padx=6)

    def practice(self, source, keys, first=None):
        if not keys:
            messagebox.showinfo("Notizblock", "In dieser Auswahl gibt es dazu keine Fragen.")
            return
        if first is not None:
            keys = [first] + [key for key in keys if key != first]
        if source == SRC_CARD:
            self.app.show_view("cards")
            self.app.views["cards"].practice(keys)
        elif source == SRC_QUIZ:
            self.app.show_view("quiz")
            self.app.views["quiz"].practice(keys, keep_order=first is not None)
        elif source == SRC_PROJECT:
            self.app.show_view("testproject")
            self.app.views["testproject"].load_project(keys[0])
        else:
            key = "ap1scenarios" if source == SRC_AP1 else "scenarios"
            self.app.show_view(key)
            self.app.views[key].load_scenario(keys[0])

    def _paint(self):
        for child in self.rows_box.winfo_children():
            child.destroy()
        status = self.status_pills.get()
        self.list_card.title_label.configure(text=Q_STATUS_NAME[status].upper(),
                                             text_color=status_color(status if status != Q_PRACTICE
                                                                     else LEVEL_RED))
        visible, self.page, pages = page_slice(self.entries, self.page, NOTEBOOK_PAGE)
        self.list_card.set_subtitle(plural(len(self.entries), "Frage", "Fragen"))
        if not visible:
            text = ("Nichts zu üben - sehr gut! Falsch beantwortete Fragen landen "
                    "automatisch hier." if status == Q_PRACTICE else
                    "Keine Fragen in dieser Auswahl.")
            make_label(self.rows_box, text, font=F["body"], fg=C["text_soft"],
                       anchor="w").pack(anchor="w", pady=6)
        for entry in visible:
            self._row(entry)
        self.lbl_page.configure(text="Seite %d / %d" % (self.page + 1, pages))

    def _row(self, entry):
        source, item = entry["source"], entry["item"]
        color = status_color(entry["level"] or entry["status"])
        row = ctk.CTkFrame(self.rows_box, fg_color=C["card_alt"], corner_radius=12,
                           border_width=1, border_color=C["border"])
        row.pack(fill="x", pady=4)
        marker = ctk.CTkFrame(row, fg_color=color, width=4, height=12, corner_radius=2)
        marker.pack(side="left", fill="y", padx=(10, 0), pady=11)
        inner = transparent_frame(row)
        inner.pack(side="left", fill="x", expand=True, padx=(10, 12), pady=10)
        head = transparent_frame(inner)
        head.pack(fill="x")
        text, _key = status_label(self.book, source, entry["key"])
        topic = TOPIC_SHORT.get(item.get("thema"), "")
        make_label(head, "%s  ·  %s%s" % (SOURCE_NAME[source], CATEGORY_SHORT[item["cat"]],
                                          "  ·  " + topic if topic else ""),
                   font=F["tiny"], fg=C["muted"]).pack(side="left")
        make_label(head, text, font=F["tiny"], fg=color).pack(side="right")
        title = entry["title"]
        if source in (SRC_AP1, SRC_AP2, SRC_PROJECT):
            title = "%d. %s" % (entry["key"] + 1, title)
        make_label(inner, title, font=F["small_bold"], fg=C["text"], wraplength=900,
                   justify="left", anchor="w").pack(anchor="w", pady=(2, 0))
        key = (source, entry["key"])
        if key in self.opened:
            answer = model_answer(source, item)
            if len(answer) > 1200:
                answer = answer[:1200].rsplit(" ", 1)[0] + " …"
            make_label(inner, answer, font=F["small"], fg=C["text_dim"], wraplength=900,
                       justify="left", anchor="w").pack(anchor="w", pady=(6, 0))
        buttons = transparent_frame(inner)
        buttons.pack(anchor="w", pady=(8, 0))
        NeoButton(buttons, "Musterantwort ausblenden" if key in self.opened else
                  "Musterantwort zeigen", lambda k=key: self._toggle(k), kind="ghost",
                  height=30, font=F["small_bold"]).pack(side="left")
        NeoButton(buttons, "Jetzt üben", lambda e=entry: self.practice(
            e["source"], self._practice_keys(e["source"]), first=e["key"]),
                  kind="pill", height=30, font=F["small_bold"]).pack(side="left", padx=(8, 0))

    def _toggle(self, key):
        if key in self.opened:
            self.opened.discard(key)
        else:
            self.opened.add(key)
        self._paint()

    def turn(self, delta):
        self.page += delta
        self._paint()
        self.to_top()


# ============================================================================
#  PRAXIS-RECHNER
# ============================================================================

class TrainerPanel(ctk.CTkFrame):
    """Subnetting-Trainer im Rechner (ab 0.51): Zufallsaufgaben mit
    Eingabefeldern, automatischer Pruefung und Rechenweg."""

    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.db = app.db
        self.tasks = []
        self.index = 0
        self.results = []
        self.checked = False

        setup = Card(self, title="Subnetting-Trainer", accent=C["accent"],
                     subtitle="Zufallsaufgaben mit Selbstkontrolle")
        setup.pack(fill="x")
        make_label(setup.body, "AUFGABENART", font=F["label"], fg=C["muted"]).pack(anchor="w")
        self.kind_pills = PillGroup(setup.body, TRAINER_KINDS)
        self.kind_pills.pack(anchor="w", pady=(8, 14))
        make_label(setup.body, "SCHWIERIGKEIT", font=F["label"], fg=C["muted"]).pack(anchor="w")
        row = transparent_frame(setup.body)
        row.pack(fill="x", pady=(8, 0))
        self.level_pills = PillGroup(row, TRAINER_LEVELS)
        self.level_pills.pack(side="left")
        self.btn_start = NeoButton(row, "Runde starten", self.start_round, kind="primary")
        self.btn_start.pack(side="left", padx=(16, 0))
        self.lbl_stats = make_label(row, "", font=F["small"], fg=C["muted"])
        self.lbl_stats.pack(side="left", padx=(16, 0))

        self.task_card = Card(self, title="Aufgabe", accent=C["purple"])
        self.task_card.pack(fill="x", pady=(14, 0))
        self.lbl_task = make_label(self.task_card.body,
                                   "Wähle Aufgabenart und Schwierigkeit und starte eine "
                                   "Runde mit %d Aufgaben." % TRAINER_ROUND,
                                   font=F["h2"], fg=C["text_soft"], wraplength=900,
                                   justify="left", anchor="w")
        self.lbl_task.pack(anchor="w", pady=(4, 12))
        self.fields_box = transparent_frame(self.task_card.body)
        self.fields_box.pack(fill="x")
        self.lbl_feedback = make_label(self.task_card.body, "", font=F["body_bold"],
                                       fg=C["text"], anchor="w")
        self.lbl_feedback.pack(anchor="w", pady=(12, 0))
        self.txt_steps = make_autogrow_text(self.task_card.body, min_height=3,
                                            max_height=18, font=F["mono_small"])
        self.txt_steps.configure(state="disabled")
        controls = transparent_frame(self)
        controls.pack(fill="x", pady=(14, 0))
        self.btn_check = NeoButton(controls, "Prüfen", self.check, kind="primary")
        self.btn_check.pack(side="left")
        self.btn_check.set_enabled(False)
        self.lbl_counter = make_label(controls, "", font=F["small"], fg=C["muted"])
        self.lbl_counter.pack(side="left", padx=16)
        self.entries = {}
        self.marks = {}
        self.show_stats()

    def show_stats(self):
        stats = self.db.trainer_stats()
        count = sum(total for total, _right in stats.values())
        right = sum(right for _total, right in stats.values())
        self.lbl_stats.configure(text="bisher %s, %d richtig"
                                 % (plural(count, "Aufgabe", "Aufgaben"), right)
                                 if count else "")

    def start_round(self):
        self.tasks = trainer_round(self.kind_pills.get(), self.level_pills.get(),
                                   random.randrange(1 << 30))
        self.index = 0
        self.results = []
        self.load_task()

    def load_task(self):
        task = self.tasks[self.index]
        self.checked = False
        self.task_card.set_subtitle("%s · %s" % (TRAINER_KIND_NAME[task.kind],
                                                 TRAINER_LEVEL_NAME[task.level]))
        self.lbl_task.configure(text=task.text)
        for child in self.fields_box.winfo_children():
            child.destroy()
        self.entries, self.marks = {}, {}
        for row, (key, label) in enumerate(task.fields):
            make_label(self.fields_box, label, font=F["small"],
                       fg=C["text_dim"]).grid(row=row, column=0, sticky="w", pady=4)
            entry = EntryBox(self.fields_box, width=26)
            entry.grid(row=row, column=1, sticky="w", padx=12, pady=4)
            entry.bind("<Return>", lambda _e: self.check())
            mark = make_label(self.fields_box, "", font=F["small_bold"], fg=C["muted"])
            mark.grid(row=row, column=2, sticky="w")
            self.entries[key], self.marks[key] = entry, mark
        if task.fields:
            self.entries[task.fields[0][0]].focus_set()
        self.lbl_feedback.configure(text="")
        self.txt_steps.pack_forget()
        self.btn_check.set_text("Prüfen")
        self.btn_check.set_enabled(True)
        self.lbl_counter.configure(text="Aufgabe %d / %d" % (self.index + 1, len(self.tasks)))

    def check(self):
        if not self.tasks:
            return
        if self.checked:
            self.advance()
            return
        task = self.tasks[self.index]
        answers = {key: entry.get() for key, entry in self.entries.items()}
        result = task.check(answers)
        for key, ok in result.items():
            self.marks[key].configure(
                text="richtig" if ok else "richtig wäre: %s" % task.solution[key],
                text_color=C["green"] if ok else C["red"])
        correct = all(result.values())
        self.results.append(correct)
        self.db.log_trainer(task.kind, task.level, correct)
        self.app.notify_progress(refresh_view=False)
        self.lbl_feedback.configure(text="Alles richtig." if correct else
                                    "Noch nicht ganz - hier der Rechenweg:",
                                    text_color=C["green"] if correct else C["yellow"])
        set_text(self.txt_steps, "\n".join(task.steps))
        self.txt_steps.pack(fill="x", pady=(10, 0))
        self.checked = True
        last = self.index >= len(self.tasks) - 1
        self.btn_check.set_text("Auswertung" if last else "Nächste Aufgabe")

    def advance(self):
        if self.index < len(self.tasks) - 1:
            self.index += 1
            self.load_task()
            return
        summary = trainer_summary(self.results)
        self.tasks = []
        for child in self.fields_box.winfo_children():
            child.destroy()
        self.txt_steps.pack_forget()
        self.lbl_task.configure(text="Runde beendet: %s." % summary)
        self.lbl_feedback.configure(text="Starte eine neue Runde oder wähle eine andere "
                                         "Aufgabenart.", text_color=C["text_dim"])
        self.btn_check.set_text("Prüfen")
        self.btn_check.set_enabled(False)
        self.lbl_counter.configure(text="")
        self.show_stats()


CALC_TABS = [("rechner", "Rechner"), ("trainer", "Trainer")]


class CalcView(View):
    def build(self):
        self.info_visible = {"subnet": False, "raid": False, "screen": False}
        self.info_frames = {}
        self.info_buttons = {}

        # Ab 0.51: Umschalter Rechner / Trainer
        self.tab_pills = PillGroup(self.content, CALC_TABS, on_change=self._on_tab)
        self.tab_pills.pack(anchor="w", pady=(0, 14))
        self.trainer = TrainerPanel(self.content, self.app)

        layout = self.calc_layout = transparent_frame(self.content)
        layout.pack(fill="both", expand=True)
        layout.columnconfigure(0, weight=1, uniform="calc")
        layout.columnconfigure(1, weight=1, uniform="calc")

        # --- Subnetting ---------------------------------------------------
        subnet = Card(layout, title="Subnetting / VLSM", accent=C["accent"],
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

    def _on_tab(self, value):
        if value == "trainer":
            self.calc_layout.pack_forget()
            self.trainer.pack(fill="both", expand=True)
        else:
            self.trainer.pack_forget()
            self.calc_layout.pack(fill="both", expand=True)

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
        self.stat_tests = self._stat_card(row, "Test-Sessions", C["accent"])
        self.stat_avg = self._stat_card(row, "Durchschnitt", C["purple"])
        self.stat_best = self._stat_card(row, "Bestes Ergebnis", C["accent2"])
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

        # Ab 0.51: Klausursimulationen
        exam_card = Card(self.content, title="Prüfungen (Klausursimulation)",
                         accent=C["green"], subtitle="aus dem Prüfungstrainer")
        exam_card.pack(fill="x", pady=(14, 0))
        columns = ("datum", "pruefung", "punkte", "note", "dauer")
        self.exam_tree = ttk.Treeview(exam_card.body, columns=columns, show="headings",
                                      height=6, style="Dash.Treeview")
        for key, text, width in [("datum", "Datum & Uhrzeit", 170),
                                 ("pruefung", "Prüfung", 300), ("punkte", "Punkte", 90),
                                 ("note", "IHK-Note", 150), ("dauer", "Dauer", 90)]:
            self.exam_tree.heading(key, text=text)
            self.exam_tree.column(key, width=px(width), anchor="center")
        self.exam_tree.pack(fill="x")

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
            {"name": "Erfolgsquote in %", "values": values, "color": C["accent2"]},
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
        for item in self.exam_tree.get_children():
            self.exam_tree.delete(item)
        for entry in self.db.exams():
            exam = fp.EXAM.get(entry["art"])
            self.exam_tree.insert("", "end", values=(
                entry["timestamp"], exam["name"] if exam else entry["art"],
                _points(entry["punkte"]), entry["note"],
                "%02d:%02d min" % (entry["dauer"] // 60, entry["dauer"] % 60)))

    def clear_history(self):
        if messagebox.askyesno("Historie löschen",
                               "Wirklich alle gespeicherten Testergebnisse und "
                               "Prüfungen löschen?\n\nDie Lern-Ereignisse für das "
                               "Dashboard bleiben erhalten."):
            if self.db.clear_history():
                self.refresh()
                self.app.notify_progress()


# ============================================================================
#  EINSTELLUNGEN
# ============================================================================

class ColorTile(ctk.CTkFrame):
    """Kachel einer Grundfarbe in den Optionen: Verlauf der Buttons, die
    beiden Akzentfarben und der Name. Die gewaehlte Kachel ist umrandet."""

    def __init__(self, parent, item, active, command):
        super().__init__(parent, fg_color=C["card_hi"] if active else C["card_alt"],
                         corner_radius=12, border_width=2,
                         border_color=item["accent"] if active else C["border"],
                         cursor="hand2")
        bar = rounded_gradient(120, 14, 7, item["primary"][0], item["primary"][1])
        strip = ctk.CTkLabel(self, text="", image=ctk_image(bar, 120, 14))
        strip.pack(padx=12, pady=(12, 8))
        dots = transparent_frame(self)
        dots.pack()
        for color in (item["accent"], item["accent2"]):
            ctk.CTkLabel(dots, text="", image=ctk_image(circle_image(12, fill=color), 12, 12)
                         ).pack(side="left", padx=3)
        name = make_label(self, item["name"], font=F["small_bold"],
                          fg=C["text"] if active else C["text_dim"])
        name.pack(padx=10, pady=(6, 12))
        for widget in (self, strip, dots, name) + tuple(dots.winfo_children()):
            widget.bind("<Button-1>", lambda _e: command(item["id"]))


class BackgroundTile(ctk.CTkFrame):
    """Kachel eines Hintergrunds: Flaeche mit einer kleinen Karte darauf,
    ein Punkt in der Grundfarbe und der Name. Gewaehlt = umrandet."""

    def __init__(self, parent, item, active, command):
        if fisi_theme.light:
            item = fisi_theme.light_background(item["id"])   # ab 0.49
        super().__init__(parent, fg_color=item["bg"], corner_radius=12, border_width=2,
                         border_color=C["accent"] if active else item["border_hi"],
                         cursor="hand2")
        card = ctk.CTkFrame(self, fg_color=item["card"], corner_radius=8, border_width=1,
                            border_color=item["border"], width=120, height=34)
        card.pack(padx=12, pady=(12, 8))
        card.pack_propagate(False)
        dot = ctk.CTkLabel(card, text="", image=ctk_image(circle_image(10, fill=C["accent"]),
                                                          10, 10), fg_color=item["card"],
                           width=10, height=10)
        dot.place(x=12, rely=0.5, anchor="w")
        name = ctk.CTkLabel(self, text=item["name"], font=F["small_bold"],
                            text_color=C["text"] if active else item["text_dim"],
                            fg_color=item["bg"])
        name.pack(padx=10, pady=(0, 12))
        for widget in (self, card, dot, name):
            widget.bind("<Button-1>", lambda _e: command(item["id"]))


class SettingsView(View):
    def build(self):
        updates = Card(self.content, title="Updates", accent=C["accent2"],
                       subtitle="installierte Version %s" % APP_VERSION)
        updates.pack(fill="x")
        row = transparent_frame(updates.body)
        row.pack(fill="x")
        self.btn_update = NeoButton(row, "Nach Updates suchen",
                                    self.check_updates, kind="primary")
        self.btn_update.pack(side="left")
        self.lbl_update = make_label(row, "", font=F["small"], fg=C["text_dim"],
                                     justify="left", anchor="w", wraplength=560)
        self.lbl_update.pack(side="left", padx=(16, 0))
        self.var_auto = tk.BooleanVar(value=fisi_update.load_settings()["auto_check"])
        ctk.CTkSwitch(updates.body, text="Beim Start automatisch nach Updates suchen",
                      variable=self.var_auto, command=self._toggle_auto,
                      font=F["small"], text_color=C["text_dim"],
                      fg_color=C["card_alt"], progress_color=C["violet"],
                      button_color=C["text"], button_hover_color="#FFFFFF"
                      ).pack(anchor="w", pady=(14, 0))

        colors = Card(self.content, title="Farben", accent=C["accent"],
                      subtitle="nur für dieses Gerät")
        colors.pack(fill="x", pady=(14, 0))
        # Ab 0.49: Darstellung Dunkel / Hell
        make_label(colors.body, "DARSTELLUNG", font=F["label"], fg=C["muted"]).pack(anchor="w")
        fisi_game_gui.ChoiceRow(colors.body, fisi_theme.MODES, fisi_theme.current_mode,
                                self._change_mode).pack(anchor="w", pady=(6, 14))
        make_label(colors.body, "GRUNDFARBE", font=F["label"], fg=C["muted"]).pack(anchor="w")
        tiles = transparent_frame(colors.body)
        tiles.pack(anchor="w", pady=(6, 14))
        for index, item in enumerate(fisi_theme.PRESETS):
            ColorTile(tiles, item, item["id"] == fisi_theme.current_preset,
                      self._change_color).grid(row=0, column=index, padx=(0, 10))
        make_label(colors.body, "HINTERGRUND", font=F["label"], fg=C["muted"]).pack(anchor="w")
        tiles = transparent_frame(colors.body)
        tiles.pack(anchor="w", pady=(6, 0))
        for index, item in enumerate(fisi_theme.BACKGROUNDS):
            BackgroundTile(tiles, item, item["id"] == fisi_theme.current_background,
                           self._change_background).grid(row=0, column=index, padx=(0, 10))
        make_label(colors.body,
                   "Die Grundfarbe ändert Buttons, Ringe, Balken und Banner, der Hintergrund "
                   "die Flächen und Karten. Die Farben der Fachbereiche und von Erfolg, "
                   "Fehler und Warnung bleiben gleich (in der hellen Darstellung etwas "
                   "dunkler, damit sie gut lesbar sind).",
                   font=F["tiny"], fg=C["muted"], wraplength=800,
                   justify="left", anchor="w").pack(anchor="w", pady=(12, 0))

        # Ab 0.51: Tagesziel, Lernserie, Erinnerung (je Geraet)
        goal = Card(self.content, title="Tagesziel", accent=C["green"],
                    subtitle="nur für dieses Gerät")
        goal.pack(fill="x", pady=(14, 0))
        values = learning_settings()
        self.goal_vars = {}
        for key, text in (("ziel_an", "Tagesziel anzeigen"),
                          ("serie_an", "Lernserie anzeigen"),
                          ("erinnerung_an", "An das Tagesziel erinnern")):
            var = self.goal_vars[key] = tk.BooleanVar(value=values[key])
            ctk.CTkSwitch(goal.body, text=text, variable=var,
                          command=lambda k=key: self._save_goal(k),
                          font=F["small"], text_color=C["text_dim"],
                          fg_color=C["card_alt"], progress_color=C["violet"],
                          button_color=C["text"], button_hover_color="#FFFFFF"
                          ).pack(anchor="w", pady=(0, 10))
        row = transparent_frame(goal.body)
        row.pack(anchor="w", pady=(4, 0))
        make_label(row, "Aufgaben pro Tag", font=F["small"],
                   fg=C["text_dim"]).pack(side="left", padx=(0, 10))
        self.goal_stepper = NumberStepper(row, value=values["ziel_anzahl"],
                                          minimum=GOAL_MIN, maximum=GOAL_MAX,
                                          step=GOAL_STEP, bg=C["card"],
                                          on_change=lambda _v: self._save_goal("ziel_anzahl"))
        self.goal_stepper.pack(side="left")
        make_label(row, "Erinnerung um", font=F["small"],
                   fg=C["text_dim"]).pack(side="left", padx=(28, 10))
        self.entry_reminder = EntryBox(row, width=7, value=values["erinnerung_zeit"])
        self.entry_reminder.pack(side="left")
        self.entry_reminder.bind("<FocusOut>", lambda _e: self._save_goal("erinnerung_zeit"))
        self.entry_reminder.bind("<Return>", lambda _e: self._save_goal("erinnerung_zeit"))
        make_label(goal.body,
                   "Gezählt werden bewertete Karteikarten, Prüfungstrainer-Fragen, "
                   "Szenarien, Testprojekte und Trainer-Aufgaben. Die Erinnerung "
                   "erscheint als Hinweis, solange das Programm geöffnet ist.",
                   font=F["tiny"], fg=C["muted"], wraplength=800,
                   justify="left", anchor="w").pack(anchor="w", pady=(12, 0))

        sync = Card(self.content, title="Abgleich PC und Handy", accent=C["accent"],
                    subtitle="über ein privates GitHub-Repository")
        sync.pack(fill="x", pady=(14, 0))
        settings = fisi_sync.sync_settings()
        grid = transparent_frame(sync.body)
        grid.pack(fill="x")
        grid.columnconfigure(1, weight=1)
        make_label(grid, "Repository (Benutzer/Name)", font=F["small"],
                   fg=C["text_dim"]).grid(row=0, column=0, sticky="w", pady=4)
        self.entry_repo = EntryBox(grid, width=34, value=settings["sync_repo"])
        self.entry_repo.grid(row=0, column=1, sticky="w", padx=12, pady=4)
        make_label(grid, "Zugangsschlüssel (Token)", font=F["small"],
                   fg=C["text_dim"]).grid(row=1, column=0, sticky="w", pady=4)
        self.entry_token = EntryBox(grid, width=34, value=settings["sync_token"])
        self.entry_token.configure(show="•")
        self.entry_token.grid(row=1, column=1, sticky="w", padx=12, pady=4)

        row = transparent_frame(sync.body)
        row.pack(fill="x", pady=(12, 0))
        self.btn_sync = NeoButton(row, "Speichern und abgleichen", self.sync_now,
                                  kind="accent")
        self.btn_sync.pack(side="left")
        self.lbl_sync = make_label(row, "", font=F["small"], fg=C["text_dim"],
                                   justify="left", anchor="w", wraplength=520)
        self.lbl_sync.pack(side="left", padx=(16, 0))
        self.var_sync_auto = tk.BooleanVar(value=settings["sync_auto"])
        ctk.CTkSwitch(sync.body, text="Automatisch abgleichen (beim Start, nach dem "
                                      "Lernen und beim Beenden)",
                      variable=self.var_sync_auto, command=self._toggle_sync_auto,
                      font=F["small"], text_color=C["text_dim"],
                      fg_color=C["card_alt"], progress_color=C["violet"],
                      button_color=C["text"], button_hover_color="#FFFFFF"
                      ).pack(anchor="w", pady=(14, 0))
        make_label(sync.body,
                   "Auf PC und Handy dasselbe Repository und denselben "
                   "Zugangsschlüssel eintragen. Wie beides angelegt wird, steht "
                   "in LIESMICH.txt unter „Abgleich PC und Handy“.",
                   font=F["tiny"], fg=C["muted"], wraplength=800,
                   justify="left", anchor="w").pack(anchor="w", pady=(10, 0))
        self.show_sync_status(None, None)

        # Sicherung als Datei (fisi_sicherung.py), Texte wie auf dem Handy
        backup = Card(self.content, title=fsi.TITLE, accent=C["accent2"],
                      subtitle=fsi.SUBTITLE)
        backup.pack(fill="x", pady=(14, 0))
        make_label(backup.body, fsi.HELP, font=F["small"], fg=C["text_dim"],
                   wraplength=800, justify="left", anchor="w").pack(anchor="w")
        row = transparent_frame(backup.body)
        row.pack(anchor="w", pady=(12, 0))
        NeoButton(row, fsi.BTN_CREATE, self.create_backup, kind="primary").pack(side="left")
        NeoButton(row, fsi.BTN_RESTORE, self.restore_backup,
                  kind="ghost").pack(side="left", padx=10)

        info = Card(self.content, title="Datenbank", accent=C["accent"])
        info.pack(fill="x", pady=(14, 0))
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
                   "Szenarien. Der Spielstand des Lernspiels bleibt erhalten. "
                   "Dieser Schritt lässt sich nicht rückgängig machen.",
                   font=F["small"], fg=C["text_dim"], wraplength=800,
                   justify="left", anchor="w").pack(anchor="w")
        NeoButton(danger.body, "Alle Lerndaten löschen", self.reset_all,
                  kind="danger").pack(anchor="w", pady=(12, 0))

        game = Card(self.content, title="Spiel", accent=C["accent2"])
        # Ab 0.47: Schwierigkeitsgrad des laufenden Spielstands (nur Anzeige)
        self.lbl_difficulty = make_label(game.body, "", font=F["body_bold"],
                                         fg=C["text_soft"], anchor="w")
        self.lbl_difficulty.pack(anchor="w", pady=(0, 10))
        game.pack(fill="x", pady=(14, 0))
        make_label(game.body, "WOHNUNGEN", font=F["label"], fg=C["muted"]).pack(anchor="w")
        ChoiceRow(game.body, fisi_game.RENT_CHOICES,
                  "miete" if fisi_game.rent_mode() else "einmal",
                  lambda key: fisi_game.set_rent_mode(key == "miete")).pack(
            anchor="w", pady=(6, 6))
        make_label(game.body, fisi_game.RENT_HELP
                   % round(fisi_game.GAME["balancing"]["miete"]["kaution_anteil"] * 100),
                   font=F["tiny"], fg=C["muted"], wraplength=800,
                   justify="left", anchor="w").pack(anchor="w", pady=(0, 14))
        self.lbl_reset = make_label(game.body, "", font=F["small"], fg=C["text_dim"],
                                    wraplength=800, justify="left", anchor="w")
        self.lbl_reset.pack(anchor="w")
        NeoButton(game.body, "Spielstand zurücksetzen", self.reset_game,
                  kind="danger").pack(anchor="w", pady=(12, 0))
        make_label(game.body, fisi_game.RECORDS_HELP, font=F["small"], fg=C["text_dim"],
                   wraplength=800, justify="left", anchor="w").pack(anchor="w", pady=(16, 0))
        NeoButton(game.body, "Bestenliste löschen", self.reset_records,
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
                   "nichts zusätzlich installiert werden. Die Handy-App für "
                   "Android nutzt dieselben Lerninhalte."
                   % (APP_TITLE, APP_VERSION),
                   font=F["body"], fg=C["text_dim"], wraplength=800,
                   justify="left", anchor="w").pack(anchor="w")

    def _change_color(self, preset_id):
        if preset_id != fisi_theme.current_preset:
            # Nach dem aktuellen Klick neu aufbauen (die Kachel wird zerstoert)
            self.after(10, lambda: self.app.change_color(preset_id=preset_id))

    def _change_background(self, background_id):
        if background_id != fisi_theme.current_background:
            self.after(10, lambda: self.app.change_color(background_id=background_id))

    def _change_mode(self, mode):
        if mode != fisi_theme.current_mode:
            self.after(10, lambda: self.app.change_color(mode=mode))

    def _save_goal(self, key):
        """Tagesziel-Einstellung speichern (ab 0.51)."""
        if key == "ziel_anzahl":
            save_learning_settings(ziel_anzahl=self.goal_stepper.get())
        elif key == "erinnerung_zeit":
            value = parse_time(self.entry_reminder.get())
            if value is None:
                value = learning_settings()["erinnerung_zeit"]
            self.entry_reminder.set(value)
            save_learning_settings(erinnerung_zeit=value)
        else:
            save_learning_settings(**{key: bool(self.goal_vars[key].get())})

    def _toggle_auto(self):
        settings = fisi_update.load_settings()
        settings["auto_check"] = bool(self.var_auto.get())
        fisi_update.save_settings(settings)

    def _toggle_sync_auto(self):
        fisi_sync.save_sync_settings(sync_auto=bool(self.var_sync_auto.get()))

    def sync_now(self):
        fisi_sync.save_sync_settings(sync_repo=self.entry_repo.get().strip(),
                                     sync_token=self.entry_token.get().strip())
        if not fisi_sync.is_configured():
            self.lbl_sync.configure(text="Bitte Repository und Zugangsschlüssel "
                                         "eintragen.", text_color=C["yellow"])
            return
        self.btn_sync.set_enabled(False)
        self.lbl_sync.configure(text="Gleiche ab ...", text_color=C["text_dim"])
        self.app.sync.run()

    def show_sync_status(self, result, error):
        """Wird nach jedem Abgleich aufgerufen (auch automatischen)."""
        self.btn_sync.set_enabled(True)
        if error:
            self.lbl_sync.configure(text=error, text_color=C["red"])
            return
        last = fisi_sync.sync_settings()["sync_last"]
        if not fisi_sync.is_configured():
            text, color = "Noch nicht eingerichtet.", C["muted"]
        elif result is not None:
            text, color = result.message, C["green"]
        elif last:
            text, color = "Zuletzt abgeglichen: %s" % _german_time(last), C["text_dim"]
        else:
            text, color = "Noch nicht abgeglichen.", C["muted"]
        self.lbl_sync.configure(text=text, text_color=color)

    def check_updates(self):
        self.btn_update.set_enabled(False)
        self.lbl_update.configure(text="Suche nach Updates ...", text_color=C["text_dim"])
        self.app.updater.check(manual=True, on_done=self._update_checked)

    def _update_checked(self, info, error):
        self.btn_update.set_enabled(True)
        if error:
            self.lbl_update.configure(text=error, text_color=C["red"])
        elif info is None:
            self.lbl_update.configure(
                text="Du hast die neueste Version (%s)." % APP_VERSION,
                text_color=C["green"])
        else:
            self.lbl_update.configure(text="Version %s ist verfügbar." % info.version,
                                      text_color=C["accent"])

    def on_show(self):
        self._show_difficulty()

    def _show_difficulty(self):
        try:
            game = self.app.views["game"].game
            game.reload()
        except (KeyError, AttributeError):
            return
        self.lbl_difficulty.configure(text=fisi_game.slot_options_text(game))
        self.lbl_reset.configure(text=fisi_game.reset_help(game))

    def reset_game(self):
        game = self.app.views["game"].game
        game.reload()
        if not messagebox.askyesno("Spielstand zurücksetzen",
                                   fisi_game.reset_question(game)):
            return
        if game.reset():
            messagebox.showinfo("Zurückgesetzt",
                                "Der Spielstand wurde zurückgesetzt.")
            self.app.views["game"].ticket = None
            self.app.views["game"].room = None
            self.app.notify_progress()
            self._show_difficulty()

    def reset_records(self):
        if not messagebox.askyesno("Bestenliste löschen", fisi_game.RECORDS_ASK):
            return
        if self.app.views["game"].game.reset_records():
            messagebox.showinfo("Gelöscht", "Die Bestenliste wurde gelöscht.")
            self.app.notify_progress()

    # -- Sicherung ------------------------------------------------------------

    def create_backup(self):
        from tkinter import filedialog
        self.app.flush_inputs(revealed=False)
        path = filedialog.asksaveasfilename(
            parent=self.app.root, title=fsi.BTN_CREATE, initialfile=fsi.default_name(),
            defaultextension=fsi.BACKUP_EXT,
            filetypes=[(fsi.FILE_TYPE, "*" + fsi.BACKUP_EXT)])
        if not path:
            return
        try:
            data = fsi.create_backup(self.db, APP_VERSION, SyncController.device())
            with open(path, "wb") as handle:
                handle.write(data)
        except OSError as error:
            messagebox.showerror(fsi.SAVE_ERROR_TITLE, str(error))
            return
        show_badge_toast(self.app.root, "Gespeichert: %s" % os.path.basename(path))

    def restore_backup(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            parent=self.app.root, title=fsi.BTN_RESTORE,
            filetypes=[(fsi.FILE_TYPE, "*" + fsi.BACKUP_EXT), ("Alle Dateien", "*")])
        if not path:
            return
        try:
            with open(path, "rb") as handle:
                backup = fsi.read_backup(handle.read())
        except (OSError, fsi.BackupError) as error:
            messagebox.showerror(fsi.ERROR_TITLE, str(error))
            return
        self.app.flush_inputs(revealed=False)
        BackupDialog(self.app, backup, self._merge_backup, self._replace_backup)

    def _merge_backup(self, backup):
        runs = fsi.deleted_runs(self.db, backup)
        if runs and not messagebox.askyesno(fsi.DELETED_TITLE, fsi.deleted_question(runs)):
            runs = []
        try:
            count = fsi.merge_backup(self.db, backup, [item["lauf"] for item in runs],
                                     SyncController.device())
        except fsi.BackupError as error:
            messagebox.showerror(fsi.ERROR_TITLE, str(error))
            return
        self._after_restore()
        messagebox.showinfo(fsi.ERROR_TITLE,
                            fsi.merge_message(count, [item["name"] for item in runs]))

    def _replace_backup(self, backup):
        if not messagebox.askyesno(fsi.REPLACE_TITLE, fsi.replace_question(backup),
                                   icon="warning"):
            return
        if not messagebox.askyesno(fsi.REPLACE_CONFIRM_TITLE, fsi.REPLACE_CONFIRM,
                                   icon="warning", default="no"):
            return
        try:
            path = fsi.replace_all(self.db, backup, os.path.dirname(self.db.db_path),
                                   APP_VERSION, SyncController.device())
        except fsi.BackupError as error:
            messagebox.showerror(fsi.ERROR_TITLE, str(error))
            return
        self._after_restore()
        messagebox.showinfo(fsi.ERROR_TITLE, fsi.replace_message(backup, path))

    def _after_restore(self):
        """Nach dem Einspielen alles neu anzeigen (wie nach dem Zuruecksetzen)."""
        game_view = self.app.views.built("game")
        if game_view is not None:
            game_view.game.invalidate()
            game_view.game._summaries.clear()   # Kurzinfos der Plaetze neu rechnen
            game_view.game.reload()
            game_view.ticket = None
            game_view.room = None
        values = learning_settings()
        for key, var in self.goal_vars.items():
            var.set(values[key])
        self.goal_stepper.value = values["ziel_anzahl"]
        self.goal_stepper.label.configure(text=str(values["ziel_anzahl"]))
        self.entry_reminder.set(values["erinnerung_zeit"])
        self.app.notify_progress()
        self.app.refresh_after_sync()
        self._show_difficulty()

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
                                accent=C["accent"])
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
        self.lbl_info.configure(text='%d Treffer für „%s“' % (len(hits), query))
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

class UpdateController:
    """Sucht im Hintergrund nach Updates, ohne die Oberflaeche zu blockieren.

    Netzwerk und Download laufen in einem eigenen Thread. Tk darf nur aus dem
    Hauptthread angesprochen werden - deshalb landen die Ergebnisse in einer
    Warteschlange, die per after() im Hauptthread abgeholt wird.
    """

    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.dialog = None
        self._queue = queue.Queue()
        self._pending = 0
        self._busy = False

    def run_in_background(self, work, on_done):
        """work() laeuft im Thread; on_done(ergebnis, fehlertext) danach im
        Hauptthread."""
        self._pending += 1

        def worker():
            try:
                self._queue.put((on_done, work(), None))
            except (fisi_update.UpdateError, fisi_sync.SyncError) as error:
                self._queue.put((on_done, None, str(error)))
            except Exception as error:  # unerwartet - nie den Thread sterben lassen
                self._queue.put((on_done, None, "Unerwarteter Fehler: %s" % error))
        threading.Thread(target=worker, daemon=True).start()
        if self._pending == 1:
            self.root.after(150, self._poll)

    def _poll(self):
        try:
            while True:
                on_done, result, error = self._queue.get_nowait()
                self._pending -= 1
                on_done(result, error)
        except queue.Empty:
            pass
        if self._pending > 0:
            self.root.after(150, self._poll)

    def check(self, manual=False, on_done=None):
        """Sucht nach einer neuen Version. Automatische Pruefungen melden sich
        nur, wenn es wirklich ein Update gibt - ohne Fehlermeldungen."""
        if self._busy:
            return
        self._busy = True

        def done(info, error):
            self._busy = False
            if on_done:
                on_done(info, error)
            if info is not None and (self.dialog is None
                                     or not self.dialog.winfo_exists()):
                self.dialog = UpdateDialog(self.app, info)

        self.run_in_background(lambda: fisi_update.check_for_update(APP_VERSION), done)

    def auto_check(self):
        if fisi_update.load_settings().get("auto_check", True):
            self.check(manual=False)


def _german_time(timestamp):
    """'2026-09-27 21:40:05' -> '27.09.2026 21:40'"""
    try:
        return "%s.%s.%s %s" % (timestamp[8:10], timestamp[5:7], timestamp[:4],
                                timestamp[11:16])
    except (TypeError, IndexError):
        return str(timestamp)


class SyncController:
    """Gleicht den Lernfortschritt im Hintergrund mit dem Repository ab
    (siehe fisi_sync.py): beim Start, eine Minute nach dem Lernen und beim
    Beenden - sofern eingerichtet und nicht abgeschaltet."""

    DELAY_MS = 60000

    def __init__(self, app):
        self.app = app
        self._busy = False
        self._again = False
        self._job = None
        self.dirty = False

    @staticmethod
    def device():
        return "PC %s" % (platform.node() or "").strip()

    @staticmethod
    def auto_enabled():
        settings = fisi_sync.sync_settings()
        return fisi_sync.is_configured(settings) and settings["sync_auto"]

    def run(self):
        if self._busy:
            self._again = True
            return
        self._busy = True
        self.dirty = False

        def done(result, error):
            self._busy = False
            if result is not None and result.received:
                self.app.refresh_after_sync()
            self.app.views["settings"].show_sync_status(result, error)
            if self._again:
                self._again = False
                self.run()

        self.app.updater.run_in_background(
            lambda: fisi_sync.sync(self.app.db, device=self.device()), done)

    def auto_start(self):
        if self.auto_enabled():
            self.run()

    def schedule(self):
        """Nach einer Lernaktivitaet: in einer Minute abgleichen. Weitere
        Aktivitaeten in dieser Zeit verschieben den Abgleich nicht."""
        self.dirty = True
        if self._job is None and self.auto_enabled():
            self._job = self.app.root.after(self.DELAY_MS, self._scheduled)

    def _scheduled(self):
        self._job = None
        self.run()

    def run_before_exit(self, timeout=12):
        """Letzter Abgleich beim Beenden, falls seitdem gelernt wurde. Das
        Fenster ist dann schon versteckt; nach timeout Sekunden wird nicht
        laenger gewartet."""
        if not (self.dirty and self.auto_enabled()):
            return
        worker = threading.Thread(
            target=lambda: _quietly(fisi_sync.sync, self.app.db, device=self.device()),
            daemon=True)
        worker.start()
        worker.join(timeout)


def _quietly(function, *args, **kwargs):
    try:
        function(*args, **kwargs)
    except Exception:
        pass


class BackupDialog(ctk.CTkToplevel):
    """Vorschau einer Sicherung mit der Wahl Zusammenfuehren / Alles ersetzen."""

    def __init__(self, app, backup, on_merge, on_replace):
        super().__init__(app.root, fg_color=C["bg"])
        self.title(fsi.ERROR_TITLE)
        self.geometry("560x390")
        self.resizable(False, False)
        self.transient(app.root)
        self.after(250, lambda: _apply_window_icon(self))

        card = Card(self, title=fsi.ERROR_TITLE, accent=C["accent2"])
        card.pack(fill="both", expand=True, padx=18, pady=18)
        make_label(card.body, "\n".join(fsi.backup_summary(backup)["zeilen"]),
                   font=F["body"], fg=C["text_soft"], justify="left",
                   anchor="w").pack(anchor="w")
        make_label(card.body, fsi.PREVIEW_HINT, font=F["small"], fg=C["text_dim"],
                   justify="left", anchor="w", wraplength=480).pack(anchor="w", pady=(14, 0))

        def choose(action):
            self.destroy()
            action(backup)

        buttons = transparent_frame(card.body)
        buttons.pack(fill="x", side="bottom", pady=(12, 0))
        NeoButton(buttons, fsi.BTN_MERGE, lambda: choose(on_merge),
                  kind="primary").pack(side="left")
        NeoButton(buttons, fsi.BTN_REPLACE, lambda: choose(on_replace),
                  kind="danger").pack(side="left", padx=10)
        NeoButton(buttons, fsi.BTN_CANCEL, self.destroy, kind="ghost").pack(side="left")
        self.after(100, self._focus)

    def _focus(self):
        self.lift()
        self.focus_force()


class UpdateDialog(ctk.CTkToplevel):
    """Zeigt ein verfuegbares Update und fuehrt durch Download und Installation."""

    def __init__(self, app, info):
        super().__init__(app.root, fg_color=C["bg"])
        self.app = app
        self.info = info
        self._downloading = False
        self.title("Update verfügbar")
        self.geometry("560x470")
        self.resizable(False, False)
        self.transient(app.root)
        # CTkToplevel setzt unter Windows kurz nach dem Oeffnen sein eigenes
        # Symbol - deshalb das Programm-Icon etwas verzoegert setzen.
        self.after(250, lambda: _apply_window_icon(self))

        card = Card(self, title="Neue Version", accent=C["accent2"],
                    subtitle="installiert: %s" % APP_VERSION)
        card.pack(fill="both", expand=True, padx=18, pady=18)
        make_label(card.body, "FISI Lernplattform %s ist verfügbar" % info.version,
                   font=F["h2"], anchor="w").pack(anchor="w")

        make_label(card.body, "Neuerungen", font=F["label"], fg=C["muted"]
                   ).pack(anchor="w", pady=(12, 4))
        notes = make_text(card.body, height=6, font=F["small"])
        notes.pack(fill="both", expand=True)
        set_text(notes, fisi_update.plain_notes(info.notes)
                 or "Keine Beschreibung vorhanden.")
        notes.configure(state="disabled")

        self.progress = ctk.CTkProgressBar(card.body, height=10, corner_radius=5,
                                           fg_color=C["ring_bg"],
                                           progress_color=C["violet"])
        self.progress.set(0)
        self.lbl_status = make_label(card.body, "", font=F["small"],
                                     fg=C["text_dim"], anchor="w",
                                     justify="left", wraplength=480)
        self.lbl_status.pack(anchor="w", pady=(10, 0))

        buttons = transparent_frame(card.body)
        buttons.pack(fill="x", pady=(12, 0))
        if info.installable:
            self.btn_main = NeoButton(buttons, "Jetzt aktualisieren",
                                      self.start_update, kind="primary")
        else:
            self.lbl_status.configure(
                text="Automatisches Aktualisieren ist nur in der installierten "
                     "Anwendung möglich. Die neue Version gibt es auf der "
                     "Download-Seite.")
            self.btn_main = NeoButton(buttons, "Zur Download-Seite",
                                      lambda: webbrowser.open(info.page_url),
                                      kind="primary")
        self.btn_main.pack(side="left")
        self.btn_later = NeoButton(buttons, "Später", self.destroy, kind="ghost")
        self.btn_later.pack(side="left", padx=10)

        self.after(100, self._focus)

    def _focus(self):
        self.lift()
        self.focus_force()

    def start_update(self):
        self.btn_main.set_enabled(False)
        self.btn_later.set_enabled(False)
        self.progress.pack(fill="x", pady=(12, 0), before=self.lbl_status)
        self.lbl_status.configure(text="Update wird heruntergeladen ...",
                                  text_color=C["text_dim"])
        state = {"loaded": 0, "total": self.info.asset_size or 1}
        self._downloading = True

        def progress(loaded, total):
            # Wird im Download-Thread aufgerufen - nur Zahlen merken
            state["loaded"], state["total"] = loaded, max(1, total)

        def refresh():
            if self._downloading and self.winfo_exists():
                self.progress.set(state["loaded"] / state["total"])
                self.lbl_status.configure(
                    text="Update wird heruntergeladen ... %.1f von %.1f MB"
                         % (state["loaded"] / 1048576, state["total"] / 1048576))
                self.after(200, refresh)

        self.app.updater.run_in_background(
            lambda: fisi_update.download(self.info, progress), self._downloaded)
        refresh()

    def _downloaded(self, path, error):
        self._downloading = False
        if error:
            self._failed(error)
            return
        self.progress.set(1)
        self.lbl_status.configure(text="Update wird installiert ...")
        self.app.updater.run_in_background(lambda: fisi_update.install(path),
                                           self._installed)

    def _installed(self, result, error):
        if error:
            self._failed(error)
            return
        must_quit, message = result
        self.lbl_status.configure(text=message, text_color=C["green"])
        if must_quit:
            # Programm schliessen, damit der Installer die Dateien ersetzen kann
            self.after(1500, lambda: self.app.on_close(final_sync=False))
        else:
            self.btn_later.set_text("Schließen")
            self.btn_later.set_enabled(True)

    def _failed(self, error):
        self.lbl_status.configure(text=error, text_color=C["red"])
        self.btn_main.set_text("Erneut versuchen")
        self.btn_main.set_enabled(True)
        self.btn_later.set_enabled(True)


def _orphaned_timers(root):
    """Zeitgeber (after), deren Tcl-Befehl nicht mehr existiert."""
    tk_ = root.tk
    orphaned = []
    for timer in tk_.splitlist(tk_.call("after", "info")):
        try:
            words = tk_.splitlist(tk_.splitlist(tk_.call("after", "info", timer))[0])
        except tk.TclError:
            continue  # inzwischen abgelaufen
        if words and not tk_.call("info", "commands", words[0]):
            orphaned.append(timer)
    return orphaned


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


# Ansichten des Spiels (ab 0.48 mit Platzanzeige im Kopf)
GAME_SUBVIEWS = ("buero", "kunde", "zuhause", "firma", "filiale", "serverfarm", "reise")
GAME_VIEWS = ("game",) + GAME_SUBVIEWS


class LazyViews(dict):
    """Die Ansichten des Hauptfensters (ab 0.48): Jede wird erst beim ersten
    Zugriff aufgebaut (views["quiz"], views.get("quiz")). built() liefert eine
    Ansicht nur, wenn es sie schon gibt. Die Schluessel sind immer alle
    Ansichten, auch die noch nicht aufgebauten."""

    def __init__(self, parent, app, classes):
        super().__init__()
        self._parent = parent
        self._app = app
        self._classes = dict(classes)

    def __missing__(self, key):
        cls = self._classes[key]      # KeyError bei unbekannter Ansicht
        view = cls(self._parent, self._app)
        view.grid(row=0, column=0, sticky="nsew")
        # Ab 0.50: Eine nebenbei aufgebaute Ansicht (z.B. das Spiel, das die
        # Optionen fuer den Schwierigkeitsgrad brauchen) legt Tk zuoberst -
        # sie wuerde die gerade gezeigte Ansicht verdecken. Deshalb nach ganz
        # unten; show_view hebt die gewuenschte Ansicht selbst nach oben.
        view.lower()
        dict.__setitem__(self, key, view)
        return view

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def built(self, key):
        return dict.get(self, key)

    def __iter__(self):
        return iter(self._classes)

    def keys(self):
        return self._classes.keys()

    def __contains__(self, key):
        return key in self._classes

    def __len__(self):
        return len(self._classes)


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
        self.container = None
        self._recoloring = False
        self.slot_chosen = False   # Spielstand nach dem Start schon gewaehlt? (ab 0.48)
        self._build_ui()
        self.show_view("dashboard")
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.bind("<Control-f>", lambda _e: self.header.search_entry.focus_set())

        self.updater = UpdateController(self)
        self.sync = SyncController(self)
        # Im automatischen Starttest (FISI_SELFTEST) nicht ins Netz gehen
        if not os.environ.get("FISI_SELFTEST"):
            root.after(1500, self.sync.auto_start)
            root.after(3000, self.updater.auto_check)
            # Erinnerung ans Tagesziel (ab 0.51), nach dem Abgleich
            root.after(8000, self.check_reminder)

    def _build_ui(self, show=True):
        """Seitenleiste, Kopfzeile und alle Ansichten (auch zum Neuaufbau
        nach einem Wechsel der Grundfarbe). Mit show=False bleibt der
        Rahmen unsichtbar, bis ihn der Aufrufer selbst einblendet."""
        container = ctk.CTkFrame(self.root, fg_color=C["bg"], corner_radius=0)
        if show:
            container.pack(fill="both", expand=True)
        self.container = container

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

        # Ab 0.48 wird eine Ansicht erst beim ersten Oeffnen aufgebaut. Das
        # beschleunigt den Start und vor allem den Farbwechsel, bei dem sonst
        # alle Ansichten auf einmal neu gezeichnet werden muessten.
        self.views = LazyViews(self.view_area, self, (
            ("dashboard", DashboardView), ("cards", CardsView),
            ("quiz", QuizView), ("ap1scenarios", Ap1ScenarioView),
            ("scenarios", ScenarioView),
            ("testproject", ProjectView), ("abschluss", FinalProjectView),
            ("notebook", NotebookView),
            ("calc", CalcView), ("game", GameView), ("buero", OfficeView),
            ("kunde", CustomerView), ("zuhause", HomeView),
            ("firma", FirmView), ("filiale", BranchView), ("serverfarm", FarmView),
            ("reise", JourneyView),
            ("progress", ProgressView),
            ("settings", SettingsView), ("search", SearchView)))

        self.current = None

    def change_color(self, preset_id=None, background_id=None, mode=None):
        """Neue Grundfarbe bzw. neuen Hintergrund speichern und die Oberflaeche
        neu aufbauen - alle Ansichten werden mit den neuen Farben gezeichnet."""
        if self._recoloring:
            return  # Ein Klick waehrend des Umbaus wird ignoriert
        self._recoloring = True
        started = time.monotonic()
        overlay = self._show_busy()
        try:
            self._recolor(preset_id, background_id, overlay, mode)
        finally:
            # Die Meldung bleibt mindestens kurz stehen, damit sie nicht nur
            # aufblitzt, und verschwindet erst, wenn alles neu gezeichnet ist.
            rest = fisi_theme.BUSY_MIN_SECONDS - (time.monotonic() - started)
            if rest > 0:
                time.sleep(rest)
            self._hide_busy(overlay)
            self._recoloring = False
            self.root.configure(cursor="")

    def _show_busy(self):
        """Ab 0.48: deckt das Fenster waehrend des Farbwechsels mit einer
        deutlichen Meldung ab. Die Abdeckung faengt alle Klicks und Tasten ab
        (grab), damit kein Doppelklick einen Zwischenzustand erzeugt."""
        overlay = tk.Frame(self.root, bg=C["bg"], cursor="watch")
        overlay.place(x=0, y=0, relwidth=1, relheight=1)
        card = ctk.CTkFrame(overlay, fg_color=C["card"], corner_radius=px(18),
                            border_width=1, border_color=C["border_hi"])
        card.place(relx=0.5, rely=0.45, anchor="center")
        ring = tk.Canvas(card, width=px(56), height=px(56), bg=C["card"],
                         highlightthickness=0, bd=0)
        ring._photo = tk_photo(ring_image(56, 6, 0.7, mix(C["accent"], C["card"], 0.35),
                                          C["accent"], C["ring_bg"]), px(56), px(56))
        ring.create_image(px(28), px(28), image=ring._photo)
        ring.pack(pady=(px(26), px(10)))
        make_label(card, fisi_theme.BUSY_TITLE, font=F["h2"], fg=C["text"],
                   bg=C["card"]).pack(padx=px(40))
        make_label(card, fisi_theme.BUSY_TEXT, font=F["body"], fg=C["text_dim"], bg=C["card"],
                   wraplength=px(440), justify="center").pack(padx=px(40),
                                                               pady=(px(6), px(26)))
        overlay.lift()
        try:
            overlay.grab_set()
        except tk.TclError:
            pass  # Ohne sichtbares Fenster (Starttest) gibt es keinen grab
        self.root.update_idletasks()
        self.root.update()
        return overlay

    def _hide_busy(self, overlay):
        try:
            overlay.grab_release()
            overlay.destroy()
        except tk.TclError:
            pass
        self.root.update_idletasks()
        self._cancel_orphaned_timers()

    def _recolor(self, preset_id, background_id, overlay=None, mode=None):
        if preset_id:
            fisi_theme.save_preset(preset_id)
        if mode:
            fisi_theme.save_mode(mode)
            apply_appearance()
        if background_id or mode:
            if background_id:
                fisi_theme.save_background(background_id)
            self.root.configure(fg_color=C["bg"])
            self._setup_ttk_style()
        fisi_game_gui.refresh_theme_tables()
        current = self.current or "settings"
        old = self.container
        # Die neue Oberflaeche wird unsichtbar aufgebaut und dann unter der
        # alten gezeichnet; die alte bleibt bis zuletzt stehen. Sonst sieht
        # man einige Sekunden lang jede Ansicht einzeln aufblitzen (Flackern).
        # Der Aufbau dauert einige Sekunden - solange zeigt die Maus "bitte warten".
        self.root.configure(cursor="watch")
        self.root.update_idletasks()
        # Ab 0.53 wie am Handy: Uebungs- und Pruefungsuhr der alten Oberflaeche
        # anhalten (sie laufen ueber root.after und fassten sonst zerstoerte
        # Widgets an) und offene Eingaben vor dem Umbau speichern
        quiz = self.views.built("quiz")
        if quiz is not None:
            quiz.stop_timer()
            quiz.exam.hide()
        self.flush_inputs(revealed=False)
        self._build_ui(show=False)
        self.show_view(current)
        self.container.place(x=0, y=0, relwidth=1, relheight=1)
        old.lift()
        if overlay is not None:
            overlay.lift()   # die Meldung bleibt ganz oben
        self.root.update_idletasks()
        self.root.update()
        # Auf einen Schlag ausblenden, erst danach (unsichtbar) abbauen.
        # Nach dem ersten Wechsel liegt die alte Oberflaeche per place.
        old.pack_forget()
        old.place_forget()
        self.root.update()
        old.destroy()
        self._cancel_orphaned_timers()

    def _cancel_orphaned_timers(self):
        """Nach dem Abbau der alten Oberflaeche stehen noch Zeitgeber (after)
        der zerstoerten Widgets aus, deren Befehl es nicht mehr gibt.
        Tkinter benennt Befehle nach Speicheradresse und Funktionsname
        (z.B. "140...<lambda>"). Bekommt eine neue Funktion dieselbe Adresse,
        wuerde der alte Zeitgeber sie ohne Argumente aufrufen - deshalb
        werden solche verwaisten Zeitgeber sofort abgebrochen."""
        for timer in _orphaned_timers(self.root):
            try:
                self.root.tk.call("after", "cancel", timer)
            except tk.TclError:
                pass

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
        # Ab 0.48: Beim ersten Oeffnen des Spiels nach dem Start erst den
        # Spielstand waehlen (Auswahlbildschirm in der Spiel-Ansicht)
        if key in GAME_SUBVIEWS and not self.slot_chosen:
            key = "game"
        view = self.views.get(key)
        if view is None:
            return
        close_badge_toasts()   # ab 0.53: Hinweise gehoeren zur alten Ansicht
        view.tkraise()
        # Ab 0.50: wiederverwendete Spielansichten behalten ihre Scroll-Position
        # (sie springen nur beim Neuzeichnen nach oben)
        if not getattr(view, "keeps_scroll", False):
            view.to_top()
        self.current = key
        main, sub = VIEW_TITLES.get(key, ("FISI", ""))
        self.header.set_crumbs(main, sub)
        # Die Suche hat keinen eigenen Menuepunkt - dann bleibt nichts markiert.
        # Die Filiale (ab 0.45) erreicht man ueber Karte und Liste unter "Spiel".
        # Ebenso die Serverfarm (ab 0.52, Lokschuppen auf der Karte).
        self.sidebar.set_active("game" if key in ("filiale", "serverfarm") else key)
        view.on_show()
        # Ab 0.50: on_show kann weitere Ansichten aufbauen - die gewaehlte
        # bleibt trotzdem oben (siehe LazyViews), sofern on_show nicht selbst
        # schon zu einer anderen Ansicht gewechselt hat.
        if self.current == key:
            view.tkraise()
        self.update_slot_label()
        self.notify_progress(refresh_view=False)

    def update_slot_label(self):
        """Platzanzeige im Kopf der Spielansichten (ab 0.48)."""
        text = ""
        if self.current in GAME_VIEWS and self.slot_chosen:
            game_view = self.views.built("game")
            if game_view is not None and not game_view.picking:
                text = game_view.game.active_label()
        self.header.set_slot(text)

    def open_slot_picker(self):
        self.views["game"].open_picker()

    def open_cards(self, category, topic=None):
        self.views["cards"].set_category(category, topic)
        self.show_view("cards")

    def do_search(self, query):
        self.views["search"].search(query)
        self.show_view("search")

    def open_raid_calc(self, level, disks, size):
        """RAID-Rechner mit den Werten aus der Server-Bestueckung (ab 0.52)."""
        view = self.views["calc"]
        view.raid_pills.select_value(level, notify=False)
        view.entry_disks.set(str(disks))
        view.entry_size.set(str(size))
        view.calc_raid()
        self.show_view("calc")

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

    def show_unlocks(self):
        """Neu erreichte Abzeichen zeigen (ab 0.46): grosse als Meilenstein-
        Moment ueber dem Fenster, kleinere als kurzer Hinweis unten."""
        view = self.views.built("game") if hasattr(self, "views") else None
        game = getattr(view, "game", None)
        if game is None or not game.unlocked:
            return
        items = game.take_unlocks()
        moments = [item for item in items if item["moment"]]
        others = [item for item in items if not item["moment"]]
        if others:
            show_badge_toast(self.root, "   ·   ".join(item["hinweis"] for item in others[:3]) +
                             ("   ·   +%d" % (len(others) - 3) if len(others) > 3 else ""))
        if moments:
            current = getattr(self, "_moment", None)
            if current is not None and current.winfo_exists():
                current.add(moments)
            else:
                self._moment = MilestoneMoment(self.root, moments, game.state,
                                               on_open=self.open_achievements)

    def open_achievements(self):
        self.views["reise"].tab = "erfolge"
        self.show_view("reise")

    def notify_progress(self, refresh_view=True):
        """Aktualisiert die Statusanzeige der Seitenleiste."""
        totals = content_totals()
        total = sum(totals.values())
        learned = self.db.distinct_cards_learned() + self.db.distinct_quiz_questions()
        self.sidebar.update_status(self.db.streak(), learned, total)
        if refresh_view:
            # Etwas wurde gelernt oder geloescht - bald abgleichen
            if hasattr(self, "sync"):
                self.sync.schedule()
            if self.current == "dashboard":
                self.views["dashboard"].refresh()
        # Kurz warten, damit erst die neue Ansicht (z.B. der Feierabend) steht
        self.root.after(400, self.show_unlocks)

    def start_review(self):
        """"Jetzt wiederholen" (ab 0.51): erst die faelligen Karteikarten,
        dann die faelligen Pruefungstrainer-Fragen."""
        plan = ReviewPlan.from_db(self.db)
        source = plan.first_source()
        if source is None:
            messagebox.showinfo("Wiederholung", "Heute ist nichts mehr fällig.")
            return
        key = "cards" if source == SRC_CARD else "quiz"
        self.show_view(key)
        self.views[key].practice(plan.session(source))

    def check_reminder(self):
        """Erinnerung ans Tagesziel (ab 0.51): als Hinweis, solange das
        Programm laeuft - beim Start und danach alle 5 Minuten."""
        try:
            # Ab 0.53: nach Mitternacht Kachel "Heute" und Seitenleiste auffrischen
            today = datetime.date.today()
            if getattr(self, "_reminder_day", today) != today:
                self.notify_progress(refresh_view=False)
                if self.current == "dashboard":
                    self.views["dashboard"].refresh()
            self._reminder_day = today
            settings = fisi_update.load_settings()
            values = learning_settings()
            goal = DailyGoal.from_db(self.db, values["ziel_anzahl"])
            if reminder_due(settings, goal, shown_on=settings.get("erinnerung_gezeigt", "")):
                save_learning_settings(erinnerung_gezeigt=datetime.date.today().isoformat())
                show_badge_toast(self.root, reminder_text(goal), delay=REMINDER_TOAST_MS)
        except Exception:
            # Ab 0.53 abgefangen (z.B. Datenbank gesperrt): beim naechsten Mal neu
            if sys.stderr is not None:
                traceback.print_exc()
        finally:
            self.root.after(5 * 60 * 1000, self.check_reminder)

    def refresh_after_sync(self):
        """Nach einem Abgleich mit neuen Eintraegen die Anzeige auffrischen."""
        self.notify_progress(refresh_view=False)
        if self.current in ("dashboard", "progress"):
            self.views[self.current].refresh()
        elif self.current == "game" and not self.views["game"].ticket:
            self.views["game"].refresh()
        elif self.current == "testproject":
            self.views["testproject"]._highlight()
        elif self.current in ("notebook", "reise", "cards"):
            self.views[self.current].on_show()

    def flush_inputs(self, revealed=True):
        """Offene Eingaben speichern (beim Beenden und vor einer Sicherung).
        revealed: auch aufgedeckte, aber nicht bewertete Loesungen als
        angesehen speichern (nur beim Beenden)."""
        keys = ("cards", "ap1scenarios", "scenarios", "testproject") if revealed else ()
        for key in keys + ("abschluss",):
            view = self.views.built(key)
            if view is not None:
                view._flush()
        quiz = self.views.built("quiz")
        if quiz is not None:
            quiz.exam._flush_answers()   # Antworten einer laufenden Pruefung (ab 0.51)

    def on_close(self, final_sync=True):
        quiz = self.views.built("quiz")
        if quiz is not None:
            quiz.stop_timer()
        self.flush_inputs()
        self.root.withdraw()
        # Nicht vor einem Update: Der Installer soll nicht warten muessen, der
        # Abgleich folgt dann beim naechsten Start.
        if final_sync:
            self.sync.run_before_exit()
        self.root.destroy()


def _run_selftest(root, app, log_path):
    """Automatischer Starttest nach dem Build (siehe build.py): oeffnet jede
    Ansicht einmal, fuehrt eine Suche aus und beendet das Programm wieder.
    Fehler landen in log_path; main() meldet sie ueber den Exit-Code."""
    failures = []

    def record(*exc_info):
        failures.append("".join(traceback.format_exception(*exc_info)))

    root.report_callback_exception = record

    # Kommen die Lerninhalte vollstaendig im fertigen Programm an?
    failures.extend(validate_content())

    def step(keys):
        if not keys:
            try:
                # Reinzoom in die Themen eines Fachbereichs (ab 0.37); bleibt
                # fuer den Farbwechsel offen
                app.show_view("dashboard")
                for category in (CATEGORIES[0], CATEGORIES[-1], CATEGORIES[-1],
                                 CATEGORIES[1]):
                    app.views["dashboard"]._toggle_zoom(category)
                    root.update()
                # Grundfarbe wechseln baut alle Ansichten neu auf
                original = fisi_theme.current_preset
                app.change_color("gruen_lime")
                root.update()
                app.change_color(original)
                root.update()
                original = fisi_theme.current_background
                app.change_color(background_id="anthrazit")
                root.update()
                app.change_color(background_id=original)
                root.update()
                # Ab 0.49: Darstellung hell und zurueck
                original = fisi_theme.current_mode
                app.change_color(mode=fisi_theme.MODE_LIGHT)
                root.update()
                app.change_color(mode=original)
                if _orphaned_timers(root):
                    failures.append("Nach dem Farbwechsel stehen noch %d verwaiste "
                                    "Zeitgeber aus." % len(_orphaned_timers(root)))
                root.update()
                dialog = UpdateDialog(app, fisi_update.UpdateInfo(
                    "9.9", "Starttest", fisi_update.RELEASES_PAGE))
                root.update()
                dialog.destroy()
            except Exception:
                failures.append(traceback.format_exc())
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


def apply_appearance():
    """Ab 0.49: Darstellung (Dunkel/Hell) auf customtkinter und die
    Fensterleiste uebertragen."""
    ctk.set_appearance_mode("light" if fisi_theme.light else "dark")


def main():
    # ab 0.53: unerwartete Fehler zusaetzlich in fehler.log im Datenordner
    install_error_log(APP_VERSION)
    apply_appearance()
    root = ctk.CTk()
    show_error = root.report_callback_exception

    def report_error(*exc_info):
        log_exception(*exc_info)
        show_error(*exc_info)
    root.report_callback_exception = report_error
    app = FISIApp(root)
    selftest_log = os.environ.get("FISI_SELFTEST")
    failures = _run_selftest(root, app, selftest_log) if selftest_log else None
    root.mainloop()
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
