#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FISI Lernplattform - Lernspiel (PC-Oberflaeche)
===============================================

Die Ansicht "Lernspiel" der PC-Version. Die Spiellogik steckt in
fisi_game.py, hier wird nur angezeigt und bedient. Gebaut aus den Bausteinen
von fisi_widgets.py und in der Farbwelt aus fisi_theme.py.
"""

import random
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox

import customtkinter as ctk

import fisi_game as fg
from fisi_core import CATEGORY_SHORT
from fisi_theme import C, CATEGORY_COLOR, GRADIENTS, lighten, mix
from fisi_widgets import (
    Card, GradientBar, LineChart, NeoButton, OptionList, ScrollArea, F,
    make_label, px, tk_font,
)

PRIORITY_COLOR = {"niedrig": C["muted"], "normal": C["cyan"], "hoch": C["yellow"],
                  "kritisch": C["red"]}
STATUS_TEXT = {fg.ST_OPEN: ("offen", C["cyan"]), fg.ST_RIGHT: ("erledigt", C["green"]),
               fg.ST_WRONG: ("mit Fehlern", C["red"]),
               fg.ST_DEFERRED: ("verschoben", C["yellow"]),
               fg.ST_WAITING: ("wartet auf Teil", C["purple"])}
# Hinweis, wenn beim Einreichen noch nichts eingegeben ist
EMPTY_HINT = {"bauteile": "Bitte setze zuerst Bauteile ein.",
              "bestellung": "Der Warenkorb ist noch leer.",
              "rack": "Bitte baue zuerst Geräte in den Schrank ein.",
              "formular": "Bitte fülle zuerst die Felder aus.",
              "terminal": "Bitte führe zuerst alle Schritte im Terminal aus.",
              "diagnose": "Bitte wähle Ursache und Maßnahme.",
              "austausch": "Bitte wähle Ursache, Maßnahme, Ersatzteil und Ablauf.",
              "wartung": "Bitte prüfe und bewerte alle Prüfpunkte und wähle den Abschluss."}
# Beschriftung "Zurueck ..." je nachdem, wo ein Auftrag angenommen wurde
RETURN_LABEL = {"buero": "Zurück ins Büro", "kunde": "Zurück zum Kunden"}
AXIS_GRADIENT = {"fachkompetenz": (C["cyan"], "#6366F1"),
                 "zuverlaessigkeit": GRADIENTS["success"],
                 "kundenzufriedenheit": ("#F59E0B", C["pink"]),
                 "sicherheit": ("#DB2777", C["purple"])}


def cat_color(key):
    return CATEGORY_COLOR[fg.CAT_NAME[key]]


def _frame(parent, **kwargs):
    return ctk.CTkFrame(parent, fg_color="transparent", corner_radius=0, **kwargs)


def rounded_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
    """Abgerundetes Rechteck auf einem Tk-Canvas (Polygon mit Glaettung)."""
    r = min(radius, (x2 - x1) / 2, (y2 - y1) / 2)
    points = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
              x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(points, smooth=True, **kwargs)


def draw_avatar(canvas, appearance, size, x=0, y=0):
    """Zeichnet den Avatar aus fisi_game.avatar_shapes() auf ein Canvas."""
    scale = size / 100.0
    for kind, (x1, y1, x2, y2), color in fg.avatar_shapes(appearance):
        coords = (x + x1 * scale, y + y1 * scale, x + x2 * scale, y + y2 * scale)
        if kind == "oval":
            canvas.create_oval(*coords, fill=color, outline="")
        elif kind == "rect":
            rounded_rect(canvas, *coords, radius=6 * scale, fill=color, outline="")
        else:
            canvas.create_line(*coords, fill=color, width=max(2, int(3 * scale)),
                               capstyle="round")


class AvatarCanvas(tk.Canvas):
    def __init__(self, parent, size=120, bg=None):
        self.size = size
        super().__init__(parent, width=px(size), height=px(size), bg=bg or C["card"],
                         highlightthickness=0, bd=0)

    def show(self, appearance):
        self.delete("all")
        size = px(self.size)
        self.create_oval(2, 2, size - 2, size - 2, fill=C["card_hi"], outline=C["border_hi"])
        # Den Avatar etwas kleiner in den Kreis setzen
        inner = size * 0.84
        offset = (size - inner) / 2
        draw_avatar(self, appearance, inner, offset, offset + size * 0.04)


class ChoiceRow(ctk.CTkFrame):
    """Reihe sich gegenseitig ausschliessender Auswahlknoepfe (Pills)."""

    def __init__(self, parent, options, value, on_change):
        super().__init__(parent, fg_color="transparent")
        self.on_change = on_change
        self.buttons = {}
        for key, label in options:
            button = NeoButton(self, label, kind="pill", height=32, font=F["small_bold"],
                               command=lambda k=key: self.select(k))
            button.pack(side="left", padx=(0, 6))
            self.buttons[key] = button
        self.value = value
        self._paint()

    def select(self, key):
        self.value = key
        self._paint()
        self.on_change(key)

    def _paint(self):
        for key, button in self.buttons.items():
            button.set_active(key == self.value)


class FloorPlan(tk.Canvas):
    """Ein Ort von oben (Zeichnung aus fisi_game.building_shapes): das Buero,
    ein Kundenort oder die Wohnung. Raeume sind anklickbar (Treffer ueber die
    Raumflaechen mit room_at)."""

    MAX_HEIGHT = 440

    def __init__(self, parent, on_room, bg=None, max_height=None, site=fg.SITE_OFFICE):
        self.bg = bg or C["card"]
        self.on_room = on_room
        self.site = site
        self.max_height = max_height or self.MAX_HEIGHT
        self.state = None
        self.selected = None
        self.player_pos = None
        self.scale = 1.0
        self.offset = 0.0
        self.offset_y = 0.0
        super().__init__(parent, height=px(300), width=px(400), bg=self.bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.bind("<Configure>", lambda _e: self.draw())
        self.bind("<Button-1>", self._click)

    def set_state(self, state, selected=None, player_pos=None):
        self.state = state
        self.selected = selected
        self.player_pos = player_pos
        self.draw()

    def content(self):
        """Inhalte des Ortes (Grundriss und Personen, die gerade da sind)."""
        return fg.site_content(self.site, self.state)

    def _layout(self):
        width = self.winfo_width()
        building = self.content()["gebaeude"]
        # Gleicher Massstab in beide Richtungen, damit das Gebaeude nicht
        # verzerrt; bei sehr breitem Fenster wird es mittig gesetzt.
        margin = fg.PLAN_MARGIN
        self.scale = min(width / (building["breite"] + 2 * margin),
                         px(self.max_height) / (building["hoehe"] + 2 * margin))
        self.offset = (width - self.scale * building["breite"]) / 2.0
        self.offset_y = margin * self.scale
        height = int(round(self.scale * (building["hoehe"] + 2 * margin)))
        if abs(int(self.cget("height")) - height) > 2:
            self.configure(height=height)

    def _building(self, with_player=True):
        profile = self.state.profile
        player = (profile["name"], profile["aussehen"]) if with_player else None
        return fg.building_shapes(self.state.open_count_by_room(), self.selected, player,
                                  content=self.content(),
                                  quests=set(self.state.quests(self.site)),
                                  player_pos=self.player_pos)

    def draw(self):
        self.delete("all")
        if self.winfo_width() <= 1 or self.state is None:
            return
        self._layout()
        for shape in self._building():
            self._shape(shape)

    def _xy(self, x, y):
        return self.offset + x * self.scale, self.offset_y + y * self.scale

    def _stroke(self, value):
        return max(1, int(round(value * self.scale)))

    def _shape(self, shape, tags=()):
        kind = shape["k"]
        if kind in ("rect", "oval"):
            x1, y1 = self._xy(shape["x"], shape["y"])
            x2, y2 = self._xy(shape["x"] + shape["w"], shape["y"] + shape["h"])
            width = self._stroke(shape["lw"]) if shape["line"] else 0
            if kind == "oval":
                self.create_oval(x1, y1, x2, y2, fill=shape["fill"],
                                 outline=shape["line"], width=width, tags=tags)
            elif shape["r"] * self.scale >= 2:
                rounded_rect(self, x1, y1, x2, y2, shape["r"] * self.scale,
                             fill=shape["fill"], outline=shape["line"], width=width,
                             tags=tags)
            else:
                self.create_rectangle(x1, y1, x2, y2, fill=shape["fill"],
                                      outline=shape["line"], width=width, tags=tags)
        elif kind == "line":
            x1, y1, x2, y2 = shape["pts"]
            self.create_line(*self._xy(x1, y1), *self._xy(x2, y2), fill=shape["color"],
                             width=self._stroke(shape["lw"]), capstyle="round", tags=tags)
        elif kind == "arc":
            x1, y1 = self._xy(shape["x"], shape["y"])
            x2, y2 = self._xy(shape["x"] + shape["w"], shape["y"] + shape["h"])
            # Tk zaehlt Winkel gegen den Uhrzeigersinn
            self.create_arc(x1, y1, x2, y2, start=-(shape["start"] + shape["extent"]),
                            extent=shape["extent"], style="arc", outline=shape["color"],
                            width=self._stroke(shape["lw"]), tags=tags)
        elif kind == "text":
            self._text(shape, tags)

    def _text(self, shape, tags=()):
        role = shape["role"]
        bold = role in ("raum", "badge", "player")
        font = tk_font(F["small_bold"] if bold else F["tiny"])
        x, y = self._xy(shape["x"], shape["y"])
        text = shape["text"]
        if shape.get("maxw") and tkfont.Font(font=font).measure(text) > \
                shape["maxw"] * self.scale:
            text = shape["kurz"]
        item = self.create_text(x, y, text=text, fill=shape["color"], font=font,
                                anchor="w" if shape["anchor"] == "w" else "center",
                                tags=tags)
        if shape.get("bg"):
            x1, y1, x2, y2 = self.bbox(item)
            pad_x, pad_y = px(8), px(3)
            back = rounded_rect(self, x1 - pad_x, y1 - pad_y, x2 + pad_x, y2 + pad_y,
                                (y2 - y1) / 2.0 + pad_y, fill=shape["bg"],
                                outline=shape.get("border", ""), width=px(1), tags=tags)
            self.tag_lower(back, item)

    def to_building(self, event):
        return ((event.x - self.offset) / self.scale,
                (event.y - self.offset_y) / self.scale)

    def _click(self, event):
        if self.scale <= 0:
            return
        item = fg.room_at(*self.to_building(event), content=self.content())
        if item:
            self.on_room(item["id"])


class WalkPlan(FloorPlan):
    """Grossansicht eines Ortes: Die Spielfigur laeuft per Klick (oder mit den
    Pfeiltasten) durch Flur und Tueren. Der Weg kommt aus fisi_game.walk_path,
    genau wie auf dem Handy. on_click(x, y) darf einen Klick selbst behandeln
    (True zurueckgeben), z.B. beim Einrichten der Wohnung."""

    SPEED = 7.0            # Grundriss-Einheiten pro Sekunde
    TICK = 16              # Millisekunden pro Bild

    def __init__(self, parent, on_arrive, max_height=640, site=fg.SITE_OFFICE,
                 on_click=None):
        super().__init__(parent, on_room=lambda _room: None, max_height=max_height,
                         site=site)
        self.on_arrive = on_arrive
        self.on_click = on_click
        self.overlay = []      # zusaetzliche Zeichenbefehle (z.B. Auswahlrahmen)
        self.route = []
        self.target = None
        self._job = None
        for key in ("<Left>", "<Right>", "<Up>", "<Down>", "a", "d", "w", "s"):
            self.bind(key, self._key)

    def draw(self):
        self.delete("all")
        if self.winfo_width() <= 1 or self.state is None:
            return
        self._layout()
        for shape in self._building(with_player=False):
            self._shape(shape)
        for shape in self.overlay:
            self._shape(shape)
        self._draw_player()

    def _draw_player(self):
        self.delete("player")
        profile = self.state.profile
        for shape in fg.player_shapes(self.player_pos, (profile["name"],
                                                        profile["aussehen"]),
                                      content=self.content()):
            self._shape(shape, tags=("player",))

    def _click(self, event):
        self.focus_set()
        if self.scale <= 0 or self.state is None:
            return
        x, y = self.to_building(event)
        if self.on_click and self.on_click(x, y):
            return
        content = self.content()
        person = fg.person_at(x, y, content)
        if person:
            route = fg.walk_path(self.player_pos, person["platz"], reach=fg.REACH,
                                 content=content)
        else:
            route = fg.walk_path(self.player_pos, (x, y), content=content)
        self.walk(route, person)

    def walk(self, route, person=None):
        self.route = list(route)
        self.target = person
        if self._job is None:
            self._step()
        if not self.route:
            self._arrived()

    def _step(self):
        self._job = None
        if not self.route:
            return
        x, y = self.player_pos
        tx, ty = self.route[0]
        dist = ((tx - x) ** 2 + (ty - y) ** 2) ** 0.5
        step = self.SPEED * self.TICK / 1000.0
        if dist <= step:
            self.player_pos = (tx, ty)
            self.route.pop(0)
        else:
            self.player_pos = (x + (tx - x) * step / dist, y + (ty - y) * step / dist)
        self._draw_player()
        if self.route:
            self._job = self.after(self.TICK, self._step)
        else:
            self._arrived()

    def _arrived(self):
        person = self.target or fg.person_near(*self.player_pos, content=self.content())
        self.target = None
        self.on_arrive(self.player_pos, person)

    def _key(self, event):
        moves = {"Left": (-1, 0), "a": (-1, 0), "Right": (1, 0), "d": (1, 0),
                 "Up": (0, -1), "w": (0, -1), "Down": (0, 1), "s": (0, 1)}
        dx, dy = moves.get(event.keysym, (0, 0))
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None
        self.route = []
        x = self.player_pos[0] + dx * fg.WALK_STEP
        y = self.player_pos[1] + dy * fg.WALK_STEP
        if fg.can_stand(x, y, content=self.content()):
            self.player_pos = (x, y)
            self._draw_player()
            self._arrived()
        return "break"

    def destroy(self):
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None
        super().destroy()


class MatchBoard(ctk.CTkFrame):
    """Zuordnungsaufgabe: erst links einen Begriff waehlen, dann rechts das
    passende Gegenstueck. Funktioniert mit Klicks, ohne Ziehen."""

    def __init__(self, parent, task):
        super().__init__(parent, fg_color="transparent")
        self.task = task
        self.lefts = [left for left, _right in task["paare"]]
        self.rights = [right for _left, right in task["paare"]]
        random.shuffle(self.rights)
        self.answer = {}
        self.current = None
        self.locked = False
        self.columnconfigure(0, weight=1, uniform="match")
        self.columnconfigure(1, weight=1, uniform="match")

        make_label(self, "1. BEGRIFF WÄHLEN", font=F["label"], fg=C["muted"]).grid(
            row=0, column=0, sticky="w", pady=(0, 6))
        make_label(self, "2. PASSENDES GEGENSTÜCK", font=F["label"], fg=C["muted"]).grid(
            row=0, column=1, sticky="w", pady=(0, 6), padx=(12, 0))
        self.left_rows = {}
        for index, left in enumerate(self.lefts, start=1):
            row = ctk.CTkFrame(self, fg_color=C["card_alt"], corner_radius=12,
                               border_width=1, border_color=C["border"], cursor="hand2")
            row.grid(row=index, column=0, sticky="ew", pady=3)
            title = make_label(row, left, font=F["body_bold"], fg=C["text"], anchor="w",
                               cursor="hand2")
            title.pack(fill="x", padx=14, pady=(9, 0))
            target = make_label(row, "noch nicht zugeordnet", font=F["small"],
                                fg=C["muted"], anchor="w", cursor="hand2")
            target.pack(fill="x", padx=14, pady=(2, 9))
            for widget in (row, title, target):
                widget.bind("<Button-1>", lambda _e, value=left: self.pick_left(value))
            self.left_rows[left] = (row, target)
        self.right_buttons = {}
        for index, right in enumerate(self.rights, start=1):
            button = NeoButton(self, right, kind="pill", height=40, font=F["small_bold"],
                               command=lambda value=right: self.pick_right(value))
            button.grid(row=index, column=1, sticky="w", pady=3, padx=(12, 0))
            self.right_buttons[right] = button
        self._paint()

    def pick_left(self, left):
        if not self.locked:
            self.current = left
            self._paint()

    def pick_right(self, right):
        if self.locked or self.current is None:
            return
        for left, value in list(self.answer.items()):
            if value == right:
                del self.answer[left]
        self.answer[self.current] = right
        # Automatisch zum naechsten noch offenen Begriff springen
        missing = [left for left in self.lefts if left not in self.answer]
        self.current = missing[0] if missing else None
        self._paint()

    def complete(self):
        return len(self.answer) == len(self.lefts)

    def _paint(self):
        solution = dict(self.task["paare"])
        for left, (row, target) in self.left_rows.items():
            value = self.answer.get(left)
            if self.locked:
                right = value == solution[left]
                border = C["green"] if right else C["red"]
                text = value or "nicht zugeordnet"
                if not right:
                    text += "   (richtig: %s)" % solution[left]
                row.configure(border_color=border, border_width=2,
                              fg_color=mix(C["card"], border, 0.16))
                target.configure(text=text, text_color=C["text_soft"])
                continue
            active = left == self.current
            row.configure(border_color=C["purple"] if active else C["border"],
                          border_width=2 if active else 1,
                          fg_color=C["card_hi"] if active else C["card_alt"])
            target.configure(text=("→ " + value) if value else "noch nicht zugeordnet",
                             text_color=C["accent"] if value else C["muted"])
        used = set(self.answer.values())
        for right, button in self.right_buttons.items():
            button.set_active(right in used)

    def reveal(self):
        self.locked = True
        self.current = None
        self._paint()


def _pick_row(parent, title, detail, extra=None, extra_color=None):
    """Anklickbare Zeile (Rahmen mit Titel und Detailzeile) fuer Steckplaetze
    und Bauteile. Rueckgabe: (Rahmen, Titel, Detail, alle Widgets)."""
    row = ctk.CTkFrame(parent, fg_color=C["card_alt"], corner_radius=12, border_width=1,
                       border_color=C["border"], cursor="hand2")
    head = _frame(row)
    head.pack(fill="x", padx=14, pady=(9, 0))
    title_label = make_label(head, title, font=F["body_bold"], fg=C["text"], anchor="w",
                             cursor="hand2")
    title_label.pack(side="left")
    widgets = [row, head, title_label]
    if extra:
        badge = make_label(head, extra, font=F["small_bold"], fg=extra_color or C["accent"],
                           cursor="hand2")
        badge.pack(side="right")
        widgets.append(badge)
    detail_label = make_label(row, detail, font=F["small"], fg=C["muted"], anchor="w",
                              cursor="hand2")
    detail_label.pack(fill="x", padx=14, pady=(2, 9))
    widgets.append(detail_label)
    return row, title_label, detail_label, widgets


class SlotBoard(ctk.CTkFrame):
    """PC zusammensetzen: links einen Steckplatz waehlen, rechts ein Bauteil
    einsetzen. Nur Klicks, kein Ziehen (wie im Konzept)."""

    def __init__(self, parent, task, available, stock=None):
        super().__init__(parent, fg_color="transparent")
        self.task = task
        self.available = list(available)
        self.from_stock = {pid for pid in self.available if pid not in task.get("teile", [])
                           and pid in (stock or {})}
        self.answer = {}
        self.current = task["slots"][0]
        self.locked = False
        self.columnconfigure(0, weight=2, uniform="slot")
        self.columnconfigure(1, weight=3, uniform="slot")

        rules = fg.build_rules_text(task)
        if rules:
            make_label(self, "Vorgaben: " + rules, font=F["small_bold"], fg=C["accent"],
                       anchor="w").grid(row=0, column=0, columnspan=2, sticky="w",
                                        pady=(0, 10))
        make_label(self, "1. STECKPLATZ WÄHLEN", font=F["label"], fg=C["muted"]).grid(
            row=1, column=0, sticky="w", pady=(0, 6))
        make_label(self, "2. BAUTEIL EINSETZEN", font=F["label"], fg=C["muted"]).grid(
            row=1, column=1, sticky="w", pady=(0, 6), padx=(12, 0))
        left = _frame(self)
        left.grid(row=2, column=0, sticky="new")
        self.slot_rows = {}
        for slot in task["slots"]:
            optional = slot in (task.get("optional") or [])
            row, _title, detail, widgets = _pick_row(
                left, fg.slot_name(slot), "leer", "optional" if optional else None,
                C["muted"])
            row.pack(fill="x", pady=3)
            for widget in widgets:
                widget.bind("<Button-1>", lambda _e, value=slot: self.pick_slot(value))
            self.slot_rows[slot] = (row, detail)
        self.parts_box = _frame(self)
        self.parts_box.grid(row=2, column=1, sticky="new", padx=(12, 0))
        self._paint()

    def candidates(self, slot):
        return [pid for pid in self.available if fg.part(pid)["typ"] == slot]

    def pick_slot(self, slot):
        if not self.locked:
            self.current = slot
            self._paint()

    def pick_part(self, part_id):
        if self.locked or self.current is None:
            return
        self.answer[self.current] = part_id
        missing = [slot for slot in self.task["slots"] if slot not in self.answer]
        self.current = missing[0] if missing else self.current
        self._paint()

    def clear_slot(self):
        if not self.locked and self.current in self.answer:
            del self.answer[self.current]
            self._paint()

    def complete(self):
        return bool(self.answer)

    def _paint(self):
        for slot, (row, detail) in self.slot_rows.items():
            part_id = self.answer.get(slot)
            active = slot == self.current and not self.locked
            border = C["purple"] if active else C["border"]
            if self.locked:
                border = C["green"] if self.success else C["red"]
            row.configure(border_color=border, border_width=2 if active or self.locked else 1,
                          fg_color=C["card_hi"] if active else C["card_alt"])
            detail.configure(text=("→ " + fg.part(part_id)["name"]) if part_id else "leer",
                             text_color=C["accent"] if part_id else C["muted"])
        for child in self.parts_box.winfo_children():
            child.destroy()
        if self.locked or self.current is None:
            return
        chosen = self.answer.get(self.current)
        options = self.candidates(self.current)
        if not options:
            make_label(self.parts_box, "Für diesen Steckplatz liegt nichts bereit.",
                       font=F["small"], fg=C["muted"], anchor="w").pack(anchor="w")
        for part_id in options:
            item = fg.part(part_id)
            extra = "aus dem Lager" if part_id in self.from_stock else None
            row, _title, _detail, widgets = _pick_row(
                self.parts_box, item["name"], "%s · %s" % (fg.part_specs(item),
                                                          _euro(item["preis"])), extra)
            row.pack(fill="x", pady=3)
            if part_id == chosen:
                row.configure(border_color=C["purple"], border_width=2, fg_color=C["card_hi"])
            for widget in widgets:
                widget.bind("<Button-1>", lambda _e, value=part_id: self.pick_part(value))
        if chosen:
            NeoButton(self.parts_box, "Steckplatz leeren", self.clear_slot, kind="ghost",
                      height=30, font=F["small_bold"]).pack(anchor="w", pady=(6, 0))

    def reveal(self, right):
        self.locked = True
        self.success = right
        self.current = None
        self._paint()


class OrderBoard(ctk.CTkFrame):
    """Bestellung: Stueckzahlen je Angebot in einen Warenkorb legen. Preis
    und Lieferzeit rechnet die Anzeige mit."""

    def __init__(self, parent, task):
        super().__init__(parent, fg_color="transparent")
        self.task = task
        self.cart = {}
        self.locked = False
        need = ctk.CTkFrame(self, fg_color=C["card_alt"], corner_radius=12, border_width=1,
                            border_color=C["border"])
        need.pack(fill="x")
        make_label(need, "BEDARF", font=F["label"], fg=C["muted"]).pack(anchor="w", padx=14,
                                                                        pady=(10, 2))
        lines = fg.order_header(task)
        for line in lines[:-1]:
            make_label(need, line, font=F["body_bold"], fg=C["text"], anchor="w").pack(
                anchor="w", padx=14)
        make_label(need, lines[-1], font=F["small_bold"], fg=C["accent"], anchor="w").pack(
            anchor="w", padx=14, pady=(4, 10))

        make_label(self, "ANGEBOTE", font=F["label"], fg=C["muted"]).pack(anchor="w",
                                                                          pady=(14, 6))
        self.counts = {}
        self.minus = {}
        for offer in task["angebote"]:
            item = fg.part(offer["teil"])
            row = ctk.CTkFrame(self, fg_color=C["card_alt"], corner_radius=12, border_width=1,
                               border_color=C["border"])
            row.pack(fill="x", pady=3)
            stepper = _frame(row)
            stepper.pack(side="right", padx=(8, 12), pady=8)
            minus = NeoButton(stepper, "−", lambda o=offer["id"]: self.change(o, -1),
                              kind="ghost", width=34, height=32)
            minus.pack(side="left")
            count = make_label(stepper, "0", font=F["h3"], fg=C["text"], width=34)
            count.pack(side="left", padx=4)
            NeoButton(stepper, "+", lambda o=offer["id"]: self.change(o, 1), kind="ghost",
                      width=34, height=32).pack(side="left")
            days = offer["lieferzeit"]
            price = _frame(row)
            price.pack(side="right", padx=8)
            make_label(price, _euro(offer["preis"]), font=F["body_bold"], fg=C["text"],
                       anchor="e").pack(anchor="e")
            make_label(price, "Lieferung %d Tag%s" % (days, "" if days == 1 else "e"),
                       font=F["small"], fg=C["muted"], anchor="e").pack(anchor="e")
            info = _frame(row)
            info.pack(side="left", fill="x", expand=True, padx=14, pady=9)
            make_label(info, item["name"], font=F["body_bold"], fg=C["text"],
                       anchor="w").pack(anchor="w")
            make_label(info, "%s · %s" % (fg.part_specs(item), fg.dealer(offer["haendler"])["name"]),
                       font=F["small"], fg=C["muted"], anchor="w").pack(anchor="w")
            self.counts[offer["id"]] = (row, count)
            self.minus[offer["id"]] = minus
        self.summary = make_label(self, "", font=F["body_bold"], fg=C["text_soft"], anchor="w")
        self.summary.pack(anchor="w", pady=(10, 0))
        self._paint()

    def change(self, offer_id, step):
        if self.locked:
            return
        value = max(0, min(9, self.cart.get(offer_id, 0) + step))
        if value:
            self.cart[offer_id] = value
        else:
            self.cart.pop(offer_id, None)
        self._paint()

    @property
    def answer(self):
        return dict(self.cart)

    def complete(self):
        return bool(self.cart)

    def _paint(self):
        for offer_id, (row, count) in self.counts.items():
            value = self.cart.get(offer_id, 0)
            count.configure(text=str(value), text_color=C["accent"] if value else C["muted"])
            row.configure(border_color=C["purple"] if value else C["border"],
                          border_width=2 if value else 1,
                          fg_color=C["card_hi"] if value else C["card_alt"])
            self.minus[offer_id].set_enabled(bool(value) and not self.locked)
        text, too_much, too_late = fg.cart_summary(self.task, self.cart)
        self.summary.configure(text="Warenkorb: " + text,
                               text_color=C["yellow"] if too_much or too_late else C["text_soft"])

    def reveal(self, right):
        self.locked = True
        for offer_id, (row, _count) in self.counts.items():
            if self.cart.get(offer_id):
                row.configure(border_color=C["green"] if right else C["red"])


class RackBoard(ctk.CTkFrame):
    """Serverschrank bestuecken: links ein Geraet waehlen, rechts im Schrank
    die Hoeheneinheit anklicken, in der es unten sitzen soll. Ein Klick auf
    ein eingebautes Geraet waehlt es aus (zum Versetzen oder Ausbauen)."""

    UNIT = 26          # Hoehe einer HE in Pixeln (bei 100 % Skalierung)
    NUMBERS = 40       # Spalte fuer die HE-Nummern

    def __init__(self, parent, task):
        super().__init__(parent, fg_color="transparent")
        self.task = task
        self.devices = task["geraete"]
        self.size = task["schrank"]["he"]
        self.answer = {}
        self.current = 0
        self.hover = None
        self.locked = False
        self.success = False

        head = ctk.CTkFrame(self, fg_color=C["card_alt"], corner_radius=12, border_width=1,
                            border_color=C["border"])
        head.pack(fill="x")
        make_label(head, "SCHRANK", font=F["label"], fg=C["muted"]).pack(anchor="w", padx=14,
                                                                         pady=(10, 2))
        lines = fg.rack_header(task)
        make_label(head, lines[0], font=F["body_bold"], fg=C["text"], anchor="w").pack(
            anchor="w", padx=14)
        for line in lines[1:]:
            make_label(head, line, font=F["small_bold"], fg=C["accent"], anchor="w").pack(
                anchor="w", padx=14, pady=(4, 0))
        _frame(head, height=10).pack()

        grid = _frame(self)
        grid.pack(fill="x", pady=(14, 0))
        grid.columnconfigure(0, weight=3, uniform="rack")
        grid.columnconfigure(1, weight=2, uniform="rack")
        make_label(grid, "1. GERÄT WÄHLEN", font=F["label"], fg=C["muted"]).grid(
            row=0, column=0, sticky="w", pady=(0, 6))
        make_label(grid, "2. HÖHENEINHEIT ANKLICKEN", font=F["label"], fg=C["muted"]).grid(
            row=0, column=1, sticky="w", pady=(0, 6), padx=(12, 0))
        left = _frame(grid)
        left.grid(row=1, column=0, sticky="new")
        self.rows = []
        for index, device_id in enumerate(self.devices):
            item = fg.rack_device(device_id)
            row, _title, detail, widgets = _pick_row(left, item["name"], fg.rack_specs(item),
                                                    " ", C["muted"])
            row.pack(fill="x", pady=3)
            badge = widgets[3]
            dot = tk.Canvas(row, width=px(6), height=px(6), bg=C["card_alt"],
                            highlightthickness=0)
            dot.place(x=px(5), y=px(15))
            dot.create_oval(0, 0, px(6), px(6), fill=fg.RACK_COLORS[item["typ"]], outline="")
            for widget in widgets:
                widget.bind("<Button-1>", lambda _e, value=index: self.pick_device(value))
            self.rows.append((row, badge, dot))
        right = _frame(grid)
        right.grid(row=1, column=1, sticky="new", padx=(12, 0))
        self.unit = px(self.UNIT if self.size <= 14 else 20)
        height = self.unit * self.size + px(16)
        self.canvas = tk.Canvas(right, height=height, bg=C["card"], highlightthickness=0,
                                cursor="hand2")
        self.canvas.pack(fill="x")
        self.canvas.bind("<Configure>", lambda _e: self._draw_rack())
        self.canvas.bind("<Motion>", self._motion)
        self.canvas.bind("<Leave>", lambda _e: self._set_hover(None))
        self.canvas.bind("<Button-1>", self._click)
        self.remove_button = NeoButton(right, "Gerät ausbauen", self.remove, kind="ghost",
                                       height=30, font=F["small_bold"])
        self.summary = make_label(self, "", font=F["body_bold"], fg=C["text_soft"], anchor="w")
        self.summary.pack(anchor="w", pady=(10, 0))
        self._paint()

    # -- Bedienung ----------------------------------------------------------

    def _unit_at(self, y):
        top = px(8)
        index = int((y - top) // self.unit)
        if 0 <= index < self.size:
            return self.size - index
        return None

    def pick_device(self, index):
        if not self.locked:
            self.current = index
            self._paint()

    def place(self, unit):
        if self.locked or unit is None:
            return
        if self.current is None:
            occupant = fg.rack_occupant(self.task, self.answer, unit)
            if occupant is not None:
                self.current = occupant
                self._paint()
            return
        self.answer = fg.rack_place(self.task, self.answer, self.current, unit)
        self.current = None
        self._paint()

    def remove(self):
        if not self.locked and self.current is not None:
            self.answer.pop(str(self.current), None)
            self._paint()

    def _click(self, event):
        self.place(self._unit_at(event.y))

    def _motion(self, event):
        self._set_hover(self._unit_at(event.y))

    def _set_hover(self, unit):
        if unit != self.hover:
            self.hover = unit
            self._draw_rack()

    def complete(self):
        return bool(self.answer)

    # -- Anzeige ------------------------------------------------------------

    def _paint(self):
        for index, (row, badge, dot) in enumerate(self.rows):
            bottom = self.answer.get(str(index))
            active = index == self.current and not self.locked
            border = C["purple"] if active else C["border"]
            if self.locked and bottom:
                border = C["green"] if self.success else C["red"]
            row.configure(border_color=border,
                          border_width=2 if active or (self.locked and bottom) else 1,
                          fg_color=C["card_hi"] if active else C["card_alt"])
            dot.configure(bg=C["card_hi"] if active else C["card_alt"])
            if bottom:
                item = fg.rack_device(self.devices[index])
                badge.configure(text=fg._he_text(bottom, item["he"]), text_color=C["accent"])
            else:
                badge.configure(text=fg.rack_source_text(self.task, index),
                                text_color=C["muted"])
        if self.current is not None and str(self.current) in self.answer and not self.locked:
            self.remove_button.pack(anchor="w", pady=(8, 0))
        else:
            self.remove_button.pack_forget()
        text, over = fg.rack_summary(self.task, self.answer)
        self.summary.configure(text="Belegt: " + text,
                               text_color=C["yellow"] if over else C["text_soft"])
        self._draw_rack()

    def _draw_rack(self):
        canvas = self.canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), px(200))
        unit, top = self.unit, px(8)
        x1, x2 = self.NUMBERS * width / 400.0 + px(8), width - px(8)
        rounded_rect(canvas, x1 - px(6), top - px(6), x2 + px(6),
                     top + unit * self.size + px(6), px(8), fill="#1E1A30",
                     outline="#5B5480", width=2)
        small = tk_font(F["tiny"])
        for index in range(self.size):
            number = self.size - index
            y = top + index * unit
            canvas.create_rectangle(x1, y + 1, x2, y + unit - 1, fill="#2A2442", outline="")
            canvas.create_text(x1 - px(12), y + unit / 2, text=str(number), fill=C["muted"],
                               font=small, anchor="e")
        # Vorschau: wo das gewaehlte Geraet landen wuerde
        if self.hover and self.current is not None and not self.locked:
            item = fg.rack_device(self.devices[self.current])
            y_bottom = top + (self.size - self.hover + 1) * unit
            y_top = y_bottom - item["he"] * unit
            canvas.create_rectangle(x1 + 2, max(top, y_top) + 2, x2 - 2, y_bottom - 2,
                                    outline=C["purple"], width=2, dash=(4, 3))
        bold = tk_font(F["small_bold"])
        for key, bottom in sorted(self.answer.items(), key=lambda row: row[1]):
            index = int(key)
            item = fg.rack_device(self.devices[index])
            color = fg.RACK_COLORS[item["typ"]]
            y_bottom = top + (self.size - bottom + 1) * unit
            y_top = y_bottom - item["he"] * unit
            if y_top < top:
                y_top = top - px(4)
                color = C["red"]
            selected = index == self.current and not self.locked
            rounded_rect(canvas, x1 + 3, y_top + 3, x2 - 3, y_bottom - 3, px(5),
                         fill=mix(C["card"], color, 0.55 if selected else 0.35),
                         outline=color, width=2 if selected else 1)
            canvas.create_oval(x2 - px(18), y_top + unit / 2 - px(3), x2 - px(12),
                               y_top + unit / 2 + px(3), fill=C["green"], outline="")
            canvas.create_text(x1 + px(10), (y_top + y_bottom) / 2, text=item["name"],
                               fill=C["text"], font=bold, anchor="w")

    def reveal(self, right):
        self.locked = True
        self.success = right
        self.current = None
        self.canvas.configure(cursor="arrow")
        self._paint()


class FormBoard(ctk.CTkFrame):
    """Formular: Eingabefelder mit Einheit. Teilnetze eines IP-Plans stehen
    als Tabelle (eine Zeile je Netz), alles andere untereinander."""

    def __init__(self, parent, task):
        super().__init__(parent, fg_color="transparent")
        self.task = task
        self.fields = fg.form_fields(task)
        self.entries = {}
        self.choices = {}
        self.marks = {}
        self.locked = False

        head = ctk.CTkFrame(self, fg_color=C["card_alt"], corner_radius=12, border_width=1,
                            border_color=C["border"])
        head.pack(fill="x")
        make_label(head, "AUSGANGSDATEN", font=F["label"], fg=C["muted"]).pack(
            anchor="w", padx=14, pady=(10, 2))
        lines = fg.form_given(task)
        for line in lines:
            make_label(head, line, font=F["body_bold"], fg=C["text"], anchor="w").pack(
                anchor="w", padx=14)
        _frame(head, height=10).pack()

        box = _frame(self)
        box.pack(fill="x", pady=(14, 0))
        single = [field for field in self.fields if not field["gruppe"]]
        groups = []
        for field in self.fields:
            if field["gruppe"] and field["gruppe"] not in groups:
                groups.append(field["gruppe"])
        row = 0
        for field in single:
            make_label(box, field["label"], font=F["body_bold"], fg=C["text"],
                       anchor="w").grid(row=row, column=0, sticky="w", pady=4, padx=(0, 16))
            self._input(box, field).grid(row=row, column=1, sticky="w", pady=4)
            row += 1
        if groups:
            columns = [field for field in self.fields if field["gruppe"] == groups[0]]
            if single:
                _frame(box, height=10).grid(row=row, column=0)
                row += 1
            make_label(box, "TEILNETZ", font=F["label"], fg=C["muted"]).grid(
                row=row, column=0, sticky="w", pady=(0, 4))
            for col, field in enumerate(columns, start=1):
                make_label(box, field["label"].upper(), font=F["label"], fg=C["muted"]).grid(
                    row=row, column=col, sticky="w", pady=(0, 4), padx=(0, 10))
            row += 1
            for group in groups:
                make_label(box, group, font=F["body_bold"], fg=C["text"], anchor="w").grid(
                    row=row, column=0, sticky="w", pady=4, padx=(0, 16))
                for col, field in enumerate([f for f in self.fields if f["gruppe"] == group],
                                            start=1):
                    self._input(box, field).grid(row=row, column=col, sticky="w", pady=4,
                                                 padx=(0, 10))
                row += 1

    def _input(self, parent, field):
        holder = _frame(parent)
        if field["art"] == "wahl":
            choice = ChoiceRow(holder, [(o, o) for o in field["optionen"]], None,
                               lambda _v: None)
            choice.pack(side="left")
            self.choices[field["id"]] = choice
        else:
            wide = {"ip": 17, "praefix": 7, "zahl": 9, "prozent": 9, "geld": 12}[field["art"]]
            entry = ctk.CTkEntry(holder, width=wide * 9 + 28, height=36, corner_radius=10,
                                 border_width=1, fg_color=C["card_alt"],
                                 border_color=C["border"], text_color=C["text_soft"],
                                 font=F["body"])
            entry._entry.configure(insertbackground=C["accent"], selectbackground=C["purple"])
            entry.bind("<FocusIn>", lambda _e, w=entry: w.configure(border_color=C["purple"]))
            entry.bind("<FocusOut>", lambda _e, w=entry: w.configure(border_color=C["border"]))
            entry.pack(side="left")
            self.entries[field["id"]] = entry
            if field["einheit"]:
                make_label(holder, field["einheit"], font=F["small"], fg=C["muted"]).pack(
                    side="left", padx=(6, 0))
        mark = make_label(holder, "", font=F["small_bold"], fg=C["red"])
        mark.pack(side="left", padx=(8, 0))
        self.marks[field["id"]] = mark
        return holder

    @property
    def answer(self):
        result = {key: entry.get() for key, entry in self.entries.items()}
        for key, choice in self.choices.items():
            result[key] = choice.value or ""
        return result

    def complete(self):
        return any((value or "").strip() for value in self.answer.values())

    def reveal(self, right):
        self.locked = True
        check = fg.form_check(self.task, self.answer)
        for field in self.fields:
            ok = check[field["id"]]
            color = C["green"] if ok else C["red"]
            if field["id"] in self.entries:
                entry = self.entries[field["id"]]
                entry.configure(border_color=color, border_width=2, state="disabled")
            else:
                for button in self.choices[field["id"]].buttons.values():
                    button.set_enabled(False)
            self.marks[field["id"]].configure(
                text="✓" if ok else "→ %s" % field["anzeige"], text_color=color)


# Farben der Terminalzeilen (fisi_game.terminal_log liefert die Rollen)
TERMINAL_BG = C["sidebar"]
TERMINAL_COLOR = {"start": C["muted"], "ausgabe": C["text_soft"], "fehler": C["red"],
                  "gefahr": C["yellow"], "kommentar": C["muted"]}


class TerminalBoard(ctk.CTkFrame):
    """Simuliertes Terminal: Zu jedem Schritt einen Befehl anklicken. Die
    Ausgabe erscheint im Terminal, bei einem falschen Befehl darf man es
    noch einmal versuchen (keine echte Shell)."""

    def __init__(self, parent, task):
        super().__init__(parent, fg_color="transparent")
        self.task = task
        self.attempts = [[] for _step in task["schritte"]]
        self.locked = False
        self.success = None
        self.step_label = make_label(self, "", font=F["label"], fg=C["muted"], anchor="w")
        self.step_label.pack(anchor="w")
        self.goal_label = make_label(self, "", font=F["body_bold"], fg=C["text"],
                                     wraplength=940, justify="left", anchor="w")
        self.goal_label.pack(anchor="w", pady=(2, 8))
        self.screen = ctk.CTkFrame(self, fg_color=TERMINAL_BG, corner_radius=12,
                                   border_width=1, border_color=C["border"])
        self.screen.pack(fill="x")
        self.lines = _frame(self.screen)
        self.lines.pack(fill="x", padx=16, pady=12)
        # Mindesthoehe 1, sonst reserviert der leere Rahmen 200 Pixel
        self.choices = _frame(self, height=1)
        self.choices.pack(fill="x", pady=(12, 0))
        self._paint()

    @property
    def answer(self):
        return {"schritte": [list(tries) for tries in self.attempts]}

    def complete(self):
        return fg.terminal_current_step(self.task, self.attempts) is None

    def run(self, index):
        step = fg.terminal_current_step(self.task, self.attempts)
        if self.locked or step is None or index in self.attempts[step]:
            return
        self.attempts[step].append(index)
        self._paint()

    def _line(self, role, text):
        row = _frame(self.lines)
        row.pack(fill="x", anchor="w")
        if role == "eingabe" or role == "cursor":
            make_label(row, self.task["prompt"], font=F["mono_small"], fg=C["green"]).pack(
                side="left", anchor="n")
            make_label(row, text, font=F["mono_small"],
                       fg=C["accent"] if role == "cursor" else C["text"], wraplength=820,
                       justify="left", anchor="w").pack(side="left", anchor="n", padx=(8, 0))
            return
        make_label(row, text, font=F["mono_small"], fg=TERMINAL_COLOR[role],
                   wraplength=900, justify="left", anchor="w").pack(anchor="w")

    def _paint(self):
        for child in self.lines.winfo_children():
            child.destroy()
        for role, text in fg.terminal_log(self.task, self.attempts):
            self._line(role, text)
        step = fg.terminal_current_step(self.task, self.attempts)
        if step is not None and not self.locked:
            self._line("cursor", "▌")
        border = C["border"]
        if self.locked:
            border = C["green"] if self.success else C["red"]
        self.screen.configure(border_color=border, border_width=2 if self.locked else 1)

        for child in self.choices.winfo_children():
            child.destroy()
        # Platzhalter: Tk verkleinert einen Rahmen ohne Inhalt sonst nicht
        _frame(self.choices, height=1).pack()
        if step is None:
            self.step_label.configure(text="ALLE SCHRITTE ERLEDIGT")
            self.goal_label.configure(text=self.task["schritte"][-1]["ziel"])
            if not self.locked:
                make_label(self.choices, "Das System ist eingerichtet. Reiche jetzt die "
                           "Lösung ein.", font=F["small"], fg=C["green"],
                           anchor="w").pack(anchor="w")
            return
        self.step_label.configure(text=fg.terminal_step_label(self.task, step).upper())
        self.goal_label.configure(text=self.task["schritte"][step]["ziel"])
        if self.locked:
            return
        make_label(self.choices, "BEFEHL WÄHLEN", font=F["label"], fg=C["muted"]).pack(
            anchor="w", pady=(0, 4))
        for index, command in enumerate(self.task["schritte"][step]["befehle"]):
            tried = index in self.attempts[step]
            row = ctk.CTkFrame(self.choices, fg_color=C["card"] if tried else C["card_alt"],
                               corner_radius=12, border_width=1,
                               border_color=C["border"], cursor="" if tried else "hand2")
            row.pack(fill="x", pady=3)
            label = make_label(row, command["befehl"], font=F["mono_small"],
                               fg=C["muted"] if tried else C["text_soft"], wraplength=900,
                               justify="left", anchor="w",
                               cursor="" if tried else "hand2")
            label.pack(anchor="w", padx=14, pady=10)
            if not tried:
                for widget in (row, label):
                    widget.bind("<Button-1>", lambda _e, value=index: self.run(value))

    def reveal(self, right):
        self.locked = True
        self.success = right
        self._paint()


class DiagnoseBoard(ctk.CTkFrame):
    """Fehlersuche: Pruefungen anklicken, die Ergebnisse landen im Notizblock.
    Danach Ursache und Massnahme waehlen."""

    def __init__(self, parent, task, available=None, stock=None, on_order=None):
        super().__init__(parent, fg_color="transparent")
        self.task = task
        self.done = []
        self.locked = False
        self.exchange = None
        spare = fg.spare_parts_text(task, available)
        if spare:
            make_label(self, spare, font=F["small_bold"], fg=C["accent"], anchor="w").pack(
                anchor="w", pady=(0, 10))
        columns = _frame(self)
        columns.pack(fill="x")
        columns.columnconfigure(0, weight=1, uniform="diag")
        columns.columnconfigure(1, weight=1, uniform="diag")
        left = _frame(columns)
        left.grid(row=0, column=0, sticky="new")
        make_label(left, "PRÜFUNGEN", font=F["label"], fg=C["muted"]).pack(anchor="w",
                                                                          pady=(0, 6))
        self.check_rows = {}
        for item in task["pruefungen"]:
            row = ctk.CTkFrame(left, fg_color=C["card_alt"], corner_radius=12,
                               border_width=1, border_color=C["border"], cursor="hand2")
            row.pack(fill="x", pady=3)
            label = make_label(row, item["text"], font=F["body"], fg=C["text_soft"],
                               wraplength=400, justify="left", anchor="w", cursor="hand2")
            label.pack(side="left", fill="x", expand=True, padx=14, pady=10)
            mark = make_label(row, "", font=F["small_bold"], fg=C["green"])
            mark.pack(side="right", padx=(0, 14))
            for widget in (row, label, mark):
                widget.bind("<Button-1>", lambda _e, value=item["id"]: self.check(value))
            self.check_rows[item["id"]] = (row, label, mark)
        right = _frame(columns)
        right.grid(row=0, column=1, sticky="new", padx=(14, 0))
        make_label(right, "NOTIZBLOCK", font=F["label"], fg=C["muted"]).pack(anchor="w",
                                                                            pady=(0, 6))
        self.notes = ctk.CTkFrame(right, fg_color=C["card_alt"], corner_radius=12,
                                  border_width=1, border_color=C["border"])
        self.notes.pack(fill="x")
        self.counter = make_label(right, "", font=F["small"], fg=C["muted"], anchor="w")
        self.counter.pack(anchor="w", pady=(6, 0))

        make_label(self, "URSACHE", font=F["label"], fg=C["muted"]).pack(anchor="w",
                                                                        pady=(16, 2))
        self.cause = OptionList(self, bg=C["card"])
        causes = list(task["ursachen"])
        random.shuffle(causes)
        self.cause.set_options(causes)
        self.cause.pack(fill="x")
        make_label(self, "MASSNAHME", font=F["label"], fg=C["muted"]).pack(anchor="w",
                                                                          pady=(14, 2))
        self.measure = OptionList(self, bg=C["card"])
        measures = list(task["massnahmen"])
        random.shuffle(measures)
        self.measure.set_options(measures)
        self.measure.pack(fill="x")
        if task.get("austausch"):
            self.exchange = ExchangePanel(self, task, stock, on_order)
            self.exchange.pack(fill="x")
        self._paint()

    def check(self, check_id):
        if not self.locked and check_id not in self.done:
            self.done.append(check_id)
            self._paint()

    @property
    def answer(self):
        result = {"pruefungen": list(self.done), "ursache": self.cause.get() or "",
                  "massnahme": self.measure.get() or ""}
        if self.exchange:
            result.update(teil=self.exchange.part, reihenfolge=list(self.exchange.order))
        return result

    @property
    def hint_key(self):
        return "austausch" if self.exchange else "diagnose"

    def complete(self):
        return bool(self.cause.get() and self.measure.get()) and \
            (self.exchange is None or self.exchange.complete())

    def _paint(self):
        keys = fg.diagnosis_key_checks(self.task)
        for check_id, (row, label, mark) in self.check_rows.items():
            done = check_id in self.done
            if self.locked and check_id in keys:
                row.configure(border_color=C["green"], border_width=2)
                mark.configure(text="geprüft · wichtig" if done else "wichtig")
            else:
                mark.configure(text="geprüft" if done else "")
            row.configure(fg_color=C["card"] if done else C["card_alt"])
            label.configure(text_color=C["muted"] if done else C["text_soft"])
        for child in self.notes.winfo_children():
            child.destroy()
        if not self.done:
            make_label(self.notes, "Noch nichts geprüft. Die Ergebnisse erscheinen hier.",
                       font=F["small"], fg=C["muted"], wraplength=420, justify="left",
                       anchor="w").pack(anchor="w", padx=14, pady=10)
        for number, check_id in enumerate(self.done, start=1):
            item = fg.diagnosis_check(self.task, check_id)
            make_label(self.notes, "%d. %s" % (number, item["text"]), font=F["small_bold"],
                       fg=C["text"], wraplength=420, justify="left", anchor="w").pack(
                anchor="w", padx=14, pady=(10 if number == 1 else 6, 0))
            make_label(self.notes, item["ergebnis"], font=F["small"], fg=C["accent"],
                       wraplength=420, justify="left", anchor="w").pack(anchor="w", padx=14)
        if self.done:
            _frame(self.notes, height=10).pack()
        self.counter.configure(text=fg.diagnosis_counter(self.task, self.done))

    def reveal(self, right):
        self.locked = True
        self.cause.reveal(self.task["ursache"])
        self.measure.reveal(self.task["massnahme"])
        if self.exchange:
            self.exchange.reveal()
        self._paint()


class ExchangePanel(ctk.CTkFrame):
    """Austausch-Schritt einer Diagnose: Ersatzteil waehlen (aus dem Lager,
    sonst nachbestellen) und den Ablauf in die richtige Reihenfolge bringen."""

    def __init__(self, parent, task, stock, on_order=None):
        super().__init__(parent, fg_color="transparent")
        self.task = task
        self.stock = dict(stock or {})
        self.on_order = on_order
        self.part = None
        self.order = []
        self.locked = False
        exchange = task["austausch"]
        kind = fg.spare_kinds().get(exchange["typ"], "Ersatzteil")
        make_label(self, "AUSTAUSCH: %s" % kind.upper(), font=F["label"],
                   fg=C["muted"]).pack(anchor="w", pady=(16, 2))
        make_label(self, "Wähle ein Teil aus dem Lager. Fehlt das passende, bestelle es "
                   "nach: Es kommt am nächsten Arbeitstag, bis dahin wartet das Ticket.",
                   font=F["small"], fg=C["text_dim"], wraplength=940, justify="left",
                   anchor="w").pack(anchor="w", pady=(0, 6))
        self.part_rows = {}
        for item in fg.spare_catalog(task):
            count = self.stock.get(item["id"], 0)
            extra = "im Lager: %d" % count if count else "nicht im Lager"
            row, title, detail, widgets = _pick_row(
                self, item["name"], "%s · %d €" % (fg.spare_specs(item), item["preis"]),
                extra, C["green"] if count else C["muted"])
            row.pack(fill="x", pady=3)
            if count:
                for widget in widgets:
                    widget.bind("<Button-1>", lambda _e, pid=item["id"]: self.pick(pid))
            elif on_order:
                NeoButton(row, "Nachbestellen (%d €)" % item["preis"],
                          lambda pid=item["id"]: self.on_order(pid), kind="ghost",
                          height=28, font=F["small_bold"]).pack(anchor="w", padx=14,
                                                               pady=(0, 9))
            self.part_rows[item["id"]] = (row, title)

        make_label(self, "ABLAUF", font=F["label"], fg=C["muted"]).pack(anchor="w",
                                                                        pady=(14, 2))
        make_label(self, "Klicke die Schritte in der richtigen Reihenfolge an. Nicht "
                   "jeder Schritt gehört dazu.", font=F["small"], fg=C["text_dim"],
                   anchor="w").pack(anchor="w", pady=(0, 6))
        self.step_rows = {}
        for text in fg.exchange_steps(task):
            row = ctk.CTkFrame(self, fg_color=C["card_alt"], corner_radius=12,
                               border_width=1, border_color=C["border"], cursor="hand2")
            row.pack(fill="x", pady=3)
            number = make_label(row, "", font=F["body_bold"], fg=C["accent"], width=28)
            number.pack(side="left", padx=(12, 0))
            label = make_label(row, text, font=F["body"], fg=C["text_soft"], wraplength=860,
                               justify="left", anchor="w", cursor="hand2")
            label.pack(side="left", fill="x", expand=True, padx=(4, 14), pady=10)
            for widget in (row, number, label):
                widget.bind("<Button-1>", lambda _e, value=text: self.step(value))
            self.step_rows[text] = (row, number, label)
        NeoButton(self, "Ablauf zurücksetzen", self.reset, kind="ghost", height=30,
                  font=F["small_bold"]).pack(anchor="w", pady=(8, 0))
        self._paint()

    def pick(self, part_id):
        if not self.locked:
            self.part = part_id
            self._paint()

    def step(self, text):
        if not self.locked and text not in self.order:
            self.order.append(text)
            self._paint()

    def reset(self):
        if not self.locked:
            self.order = []
            self._paint()

    def complete(self):
        return bool(self.part and self.order)

    def _paint(self, solution=None):
        for part_id, (row, title) in self.part_rows.items():
            chosen = part_id == self.part
            right = solution is not None and not fg.spare_fits(self.task, part_id)
            row.configure(border_color=C["green"] if right else
                          (C["accent"] if chosen else C["border"]),
                          border_width=2 if chosen or right else 1,
                          fg_color=C["card"] if chosen else C["card_alt"])
        for text, (row, number, label) in self.step_rows.items():
            index = self.order.index(text) + 1 if text in self.order else None
            number.configure(text=str(index) if index else "")
            row.configure(fg_color=C["card"] if index else C["card_alt"])
            if solution is not None:
                steps = self.task["austausch"]["schritte"]
                good = text in steps
                row.configure(border_color=C["green"] if good else C["border"],
                              border_width=2 if good else 1)
                number.configure(text=str(steps.index(text) + 1) if good else "")

    def reveal(self):
        self.locked = True
        self._paint(solution=True)


class MaintenanceBoard(ctk.CTkFrame):
    """Wartung: Pruefpunkte anklicken (Messwert erscheint), jeden als „in
    Ordnung“ oder „auffällig“ bewerten, dann den Abschluss waehlen."""

    def __init__(self, parent, task):
        super().__init__(parent, fg_color="transparent")
        self.task = task
        self.checked = []
        self.ratings = {}
        self.shown = set()
        self.locked = False
        make_label(self, "PRÜFPUNKTE", font=F["label"], fg=C["muted"]).pack(anchor="w",
                                                                            pady=(0, 6))
        self.rows = {}
        for item in task["pruefpunkte"]:
            row = ctk.CTkFrame(self, fg_color=C["card_alt"], corner_radius=12,
                               border_width=1, border_color=C["border"], cursor="hand2")
            row.pack(fill="x", pady=3)
            head = _frame(row)
            head.pack(fill="x", padx=14, pady=(10, 0))
            label = make_label(head, item["text"], font=F["body"], fg=C["text_soft"],
                               wraplength=620, justify="left", anchor="w", cursor="hand2")
            label.pack(side="left", fill="x", expand=True)
            choice = ChoiceRow(head, [(key, fg.RATING_TEXT[key])
                                      for key in (fg.RATING_OK, fg.RATING_ISSUE)], None,
                               lambda key, pid=item["id"]: self.rate(pid, key))
            result = make_label(row, "Zum Prüfen anklicken.", font=F["small"],
                                fg=C["muted"], wraplength=900, justify="left", anchor="w",
                                cursor="hand2")
            result.pack(anchor="w", padx=14, pady=(2, 10))
            for widget in (row, head, label, result):
                widget.bind("<Button-1>", lambda _e, value=item["id"]: self.check(value))
            self.rows[item["id"]] = (row, label, choice, result)
        self.counter = make_label(self, "", font=F["small"], fg=C["muted"], anchor="w")
        self.counter.pack(anchor="w", pady=(6, 0))
        make_label(self, "ABSCHLUSS FÜR DAS PROTOKOLL", font=F["label"],
                   fg=C["muted"]).pack(anchor="w", pady=(16, 2))
        self.closing = OptionList(self, bg=C["card"])
        options = list(task["abschluss"])
        random.shuffle(options)
        self.closing.set_options(options)
        self.closing.pack(fill="x")
        self._paint()

    def check(self, point_id):
        if not self.locked and point_id not in self.checked:
            self.checked.append(point_id)
            self._paint()

    def rate(self, point_id, key):
        if self.locked:
            return
        if point_id not in self.checked:
            self.checked.append(point_id)
        self.ratings[point_id] = key
        self._paint()

    @property
    def answer(self):
        return {"bewertung": dict(self.ratings), "abschluss": self.closing.get() or ""}

    def complete(self):
        return len(self.ratings) == len(self.task["pruefpunkte"]) and bool(self.closing.get())

    def _paint(self, solution=False):
        for point_id, (row, label, choice, result) in self.rows.items():
            item = fg.maintenance_point(self.task, point_id)
            done = point_id in self.checked
            if done and point_id not in self.shown:
                choice.pack(side="right", padx=(10, 0))
                self.shown.add(point_id)
            if choice.value != self.ratings.get(point_id):
                choice.value = self.ratings.get(point_id)
                choice._paint()
            result.configure(text=item["ergebnis"] if done else "Zum Prüfen anklicken.",
                             text_color=C["accent"] if done else C["muted"])
            row.configure(fg_color=C["card"] if done else C["card_alt"])
            if solution:
                wanted = fg.RATING_ISSUE if item.get("auffaellig") else fg.RATING_OK
                good = self.ratings.get(point_id) == wanted
                row.configure(border_color=C["green"] if good else C["red"], border_width=2)
                result.configure(text="%s · richtig: %s" % (item["ergebnis"],
                                                            fg.RATING_TEXT[wanted]))
        self.counter.configure(text=fg.maintenance_counter(self.task, self.ratings))

    def reveal(self, right):
        self.locked = True
        self.closing.reveal(self.task["abschluss_antwort"])
        for point_id in self.rows:
            if point_id not in self.checked:
                self.checked.append(point_id)
        self._paint(solution=True)


class GameView(ScrollArea):
    """Ansicht "Lernspiel" in der PC-Version."""

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self.db = app.db
        self.game = fg.Game(app.db, device="PC")
        self.content = _frame(self.inner)
        self.content.pack(fill="both", expand=True, padx=28, pady=(2, 28))
        self.room = None
        self.ticket = None
        self.draft = {}
        # Standort der Figur je Ort (nur waehrend die App laeuft)
        self.positions = {}
        self.notices = {}         # Ort -> (Ueberschrift, Text), einmal anzeigen
        self.place = None         # gewaehlter Kundenort
        self.return_to = None     # Ticket kam aus einer Grossansicht (buero, kunde)
        self.render()

    # -- Aufbau -------------------------------------------------------------

    def on_show(self):
        self.game.reload()
        self.render()

    def refresh(self):
        self.on_show()

    def render(self, keep_scroll=False):
        for child in self.content.winfo_children():
            child.destroy()
        state = self.game.state
        if state.profile is None or self.draft.get("edit"):
            self._build_profile_editor(state)
        elif self.ticket:
            self._build_ticket(self.ticket)
        else:
            self._build_overview(state)
        if not keep_scroll:
            self.to_top()

    @property
    def player_pos(self):
        return self.position(fg.SITE_OFFICE)

    def position(self, site):
        if site not in self.positions:
            self.positions[site] = fg.start_position(
                fg.site_content(site, self.game.state))
        return self.positions[site]

    # -- Orte wechseln ------------------------------------------------------

    def go_home(self):
        """Feierabend: Arbeitstag beenden und nach Hause gehen."""
        try:
            payload = self.game.end_day()
        except ValueError as exc:
            messagebox.showinfo("Hinweis", str(exc))
            return
        self.room = None
        self.positions.pop(fg.SITE_HOME, None)
        self.positions.pop(fg.SITE_OFFICE, None)
        self.notices[fg.SITE_HOME] = (
            "Feierabend nach Arbeitstag %d" % payload["tag"],
            "%s %s" % (fg.day_end_text(payload["tag"], firm=bool(payload.get("firma"))),
                       fg.day_end_money_text(payload)))
        self.app.notify_progress()
        self.render()
        self.app.show_view("zuhause")

    def go_to_work(self):
        """Von zu Hause (oder vom Kunden) ins Buero - morgens mit der Szene
        des Tages, falls es eine gibt."""
        state = self.game.state
        scene = fg.morning_text(state.day, state=state)
        self.positions.pop(fg.SITE_OFFICE, None)
        if scene:
            self.notices[fg.SITE_OFFICE] = ("Arbeitstag %d" % state.day, scene)
        self.app.show_view("buero")

    def run_action(self, action, view_key):
        """Knoepfe unter den Grossansichten (siehe fisi_game.place_message)."""
        if action.startswith("auftrag:"):
            self.open_from_site(action.split(":", 1)[1], view_key)
        elif action == "feierabend":
            self.go_home()
        elif action == "buero":
            self.go_to_work()
        elif action == "lernen":
            self.app.show_view("cards")
        elif action == "schlafen":
            self.notices[fg.SITE_HOME] = ("Gute Nacht", fg.sleep_text(self.game.state))
            self.app.views["zuhause"].render()

    # -- Spielfigur ---------------------------------------------------------

    def _build_profile_editor(self, state):
        profile = state.profile or {"name": "", "aussehen": dict(fg.DEFAULT_APPEARANCE)}
        look = fg.normalize_appearance(self.draft.get("aussehen") or profile["aussehen"])
        self.draft["aussehen"] = look

        if state.profile is None:
            intro = Card(self.content, title="Willkommen im Spiel", accent=C["accent2"],
                         subtitle="%s · Kunde: %s" % (fg.GAME["gebaeude"]["firma"],
                                                      fg.GAME["gebaeude"]["kunde"]))
            intro.pack(fill="x")
            make_label(intro.body, fg.GAME["story"]["intro"], font=F["body"],
                       fg=C["text_soft"], wraplength=980, justify="left",
                       anchor="w").pack(anchor="w")

        card = Card(self.content, title="Deine Spielfigur", accent=C["accent"])
        card.pack(fill="x", pady=(14, 0))
        body = _frame(card.body)
        body.pack(fill="x")
        avatar = AvatarCanvas(body, size=150)
        avatar.pack(side="left", anchor="n", padx=(0, 24))
        avatar.show(look)
        form = _frame(body)
        form.pack(side="left", fill="x", expand=True)

        make_label(form, "NAME", font=F["label"], fg=C["muted"]).pack(anchor="w")
        entry = ctk.CTkEntry(form, width=320, height=38, corner_radius=10, border_width=1,
                             fg_color=C["card_alt"], border_color=C["border"],
                             text_color=C["text_soft"], font=F["body"],
                             placeholder_text="Wie heißt deine Figur?",
                             placeholder_text_color=C["muted"])
        entry.pack(anchor="w", pady=(6, 12))
        name = self.draft.get("name", profile["name"])
        if name:
            entry.insert(0, name)
        entry.bind("<KeyRelease>", lambda _e: self.draft.update(name=entry.get()))

        def changed(part, value):
            look[part] = value
            avatar.show(look)

        for part, caption in fg.APPEARANCE_LABELS:
            make_label(form, caption.upper(), font=F["label"], fg=C["muted"]).pack(anchor="w")
            ChoiceRow(form, fg.APPEARANCE[part], look[part],
                      lambda value, p=part: changed(p, value)).pack(anchor="w", pady=(6, 10))

        buttons = _frame(card.body)
        buttons.pack(fill="x", pady=(8, 0))
        NeoButton(buttons, "Los geht's" if state.profile is None else "Speichern",
                  lambda: self._save_profile(entry.get(), look), kind="primary").pack(side="left")
        if state.profile is not None:
            NeoButton(buttons, "Abbrechen", self._cancel_edit, kind="ghost").pack(
                side="left", padx=10)

    def _save_profile(self, name, look):
        try:
            self.game.set_profile(name, look)
        except ValueError as exc:
            messagebox.showwarning("Hinweis", str(exc))
            return
        self.draft = {}
        self.app.notify_progress()
        self.render()

    def _edit_profile(self):
        self.draft = {"edit": True}
        self.render()

    def _cancel_edit(self):
        self.draft = {}
        self.render()

    # -- Uebersicht ---------------------------------------------------------

    def _build_overview(self, state):
        levels = self.game.knowledge()
        top = _frame(self.content)
        top.pack(fill="x")
        top.columnconfigure(0, weight=3, uniform="top")
        top.columnconfigure(1, weight=2, uniform="top")

        # Profil
        profile = Card(top, title="Spielfigur", accent=C["accent2"],
                       subtitle="Arbeitstag %d" % state.day)
        profile.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        row = _frame(profile.body)
        row.pack(fill="x")
        avatar = AvatarCanvas(row, size=104)
        avatar.pack(side="left", padx=(0, 18))
        avatar.show(state.profile["aussehen"])
        info = _frame(row)
        info.pack(side="left", fill="x", expand=True)
        make_label(info, state.profile["name"], font=F["h1"], fg=C["text"],
                   anchor="w").pack(anchor="w")
        job = ("Geschäftsführung · %s" % state.firm["name"] if state.firm else
               "%s bei der %s" % (state.rank, fg.GAME["gebaeude"]["firma"]))
        make_label(info, job, font=F["body_bold"], fg=C["accent"], anchor="w").pack(
            anchor="w", pady=(2, 0))
        hint = "" if state.firm else fg.rank_hint(state)
        if hint:
            make_label(info, hint, font=F["small"], fg=C["muted"], anchor="w").pack(anchor="w")
        money = "Kontostand: %s   ·   Gehalt: %s pro Arbeitstag" % (
            _euro(state.money), _euro(state.salary))
        if state.firm:
            money = "Kontostand: %s   ·   %s" % (_euro(state.money), fg.firm_summary(state))
        if state.rent:
            money += "   ·   Miete: %s pro Arbeitstag" % _euro(state.rent)
        make_label(info, money,
                   font=F["small"], fg=C["text_dim"], anchor="w").pack(anchor="w", pady=(8, 0))
        goal = fg.GAME["balancing"]["gruendung"]
        if not state.firm:
            bar = GradientBar(info, "Weg zum eigenen Unternehmen", C["green"], C["accent"],
                              parent_bg=C["card"])
            bar.pack(fill="x", pady=(8, 0))
            bar.set(state.founding_progress() * 100,
                    "Ziel: %s und %d %% Ansehen" % (_euro(goal["startkapital"]),
                                                    goal["mindest_reputation"]))
        buttons = _frame(profile.body)
        buttons.pack(anchor="w", pady=(12, 0))
        NeoButton(buttons, "Figur bearbeiten", self._edit_profile, kind="ghost",
                  height=32, font=F["small_bold"]).pack(side="left")
        if state.firm or state.founding_ready():
            NeoButton(buttons, "Firma öffnen" if state.firm else "Firma gründen",
                      lambda: self.app.show_view("firma"),
                      kind="ghost" if state.firm else "primary", height=32,
                      font=F["small_bold"]).pack(side="left", padx=(10, 0))

        # Reputation
        reputation = Card(top, title="Reputation", accent=C["purple"],
                          subtitle="Ansehen %d %%" % round(state.mean_reputation))
        reputation.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        for key, name in fg.AXES:
            start, end = AXIS_GRADIENT[key]
            bar = GradientBar(reputation.body, name, start, end, parent_bg=C["card"])
            bar.pack(fill="x", pady=(0, 2))
            bar.set(state.reputation[key], "%d / 100" % state.reputation[key])

        middle = _frame(self.content)
        middle.pack(fill="x", pady=(14, 0))
        middle.columnconfigure(0, weight=3, uniform="mid")
        middle.columnconfigure(1, weight=2, uniform="mid")

        plan = Card(middle, title="Grundriss", accent=C["accent"],
                    subtitle="Raum anklicken, um die Tickets dort zu sehen")
        plan.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        self.floor = FloorPlan(plan.body, self._select_room)
        self.floor.pack(fill="x")
        self.floor.set_state(state, self.room, self.player_pos)
        places = _frame(plan.body)
        places.pack(anchor="w", pady=(10, 0))
        for label, key in (("Büro öffnen", "buero"), ("Kunde öffnen", "kunde"),
                           ("Zuhause öffnen", "zuhause"), ("Firma öffnen", "firma")):
            NeoButton(places, label, lambda k=key: self.app.show_view(k), kind="ghost",
                      height=32, font=F["small_bold"]).pack(side="left", padx=(0, 8))
        away = state.open_count_by_site()
        at_customer = sum(count for site, count in away.items() if site != fg.SITE_OFFICE)
        if at_customer:
            make_label(places, "%s beim Kunden" % ("1 Auftrag" if at_customer == 1 else
                                                   "%d Aufträge" % at_customer),
                       font=F["small"], fg=C["muted"]).pack(side="left", padx=6)

        wissen = Card(middle, title="Wissensstand", accent=C["green"],
                      subtitle="aus deinem Lernfortschritt")
        wissen.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        for key in fg.CAT_ORDER:
            color = cat_color(key)
            bar = GradientBar(wissen.body, CATEGORY_SHORT[fg.CAT_NAME[key]], color,
                              lighten(color, 0.35), parent_bg=C["card"])
            bar.pack(fill="x", pady=(0, 2))
            bar.set(levels[key], "%d %%" % levels[key])
        make_label(wissen.body, "Wer lernt, schafft schwierigere Tickets. Berechnet aus "
                   "den letzten Antworten und dem Anteil bearbeiteter Inhalte.",
                   font=F["tiny"], fg=C["muted"], wraplength=380, justify="left",
                   anchor="w").pack(anchor="w", pady=(8, 0))

        self._build_ticket_list(state)

    def _build_ticket_list(self, state):
        if self.room:
            item = fg.room(self.room)
            tickets = state.tickets_in_room(self.room)
            card = Card(self.content, title=item["name"], accent=cat_color(item["cat"]),
                        subtitle="Tickets in diesem Raum")
        else:
            item = None
            tickets = state.todays_tickets()
            card = Card(self.content, title="Tickets heute", accent=C["accent2"],
                        subtitle="Arbeitstag %d · %d von %d bearbeitet"
                        % (state.day, len(state.handled), len(tickets)))
        card.pack(fill="x", pady=(14, 0))
        body = card.body

        scene = fg.morning_text(state.day, state=state)
        if scene and not item:
            box = ctk.CTkFrame(body, fg_color=mix(C["card"], C["purple"], 0.1),
                               corner_radius=12, border_width=1,
                               border_color=mix(C["purple"], C["card"], 0.45))
            box.pack(fill="x", pady=(0, 8))
            make_label(box, "HEUTE", font=F["label"], fg=C["purple"]).pack(
                anchor="w", padx=14, pady=(10, 0))
            make_label(box, scene, font=F["small"], fg=C["text_soft"], wraplength=940,
                       justify="left", anchor="w").pack(anchor="w", padx=14, pady=(2, 10))

        if item:
            make_label(body, item["text"], font=F["small"], fg=C["text_dim"],
                       wraplength=980, justify="left", anchor="w").pack(anchor="w")
            people = fg.people_at_site(fg.SITE_OFFICE, state)
            if any(person.get("lagerist") for person in people
                   if person["raum"] == item["id"]):
                self._build_warehouse(body, state)
            for person in people:
                if person["raum"] == item["id"]:
                    make_label(body, "%s · %s" % (person["name"], person["rolle"]),
                               font=F["body_bold"], fg=C["text"], anchor="w").pack(
                        anchor="w", pady=(10, 0))
                    make_label(body, person["macke"], font=F["small"], fg=C["muted"],
                               wraplength=980, justify="left", anchor="w").pack(anchor="w")
            NeoButton(body, "Alle Tickets zeigen", lambda: self._select_room(None),
                      kind="ghost", height=32, font=F["small_bold"]).pack(anchor="w",
                                                                          pady=(12, 4))

        if not tickets:
            waiting = len(state.waiting_for_delivery())
            text = ("In diesem Raum ist heute nichts zu tun." if item else
                    (fg.firm_orders_summary(state) or fg.FIRM_IDLE_TEXT) if state.firm else
                    fg.GAME["story"]["alle_erledigt"] if state.all_done() else
                    "Heute stehen keine Tickets an. %s auf eine Lieferung."
                    % ("1 Auftrag wartet" if waiting == 1 else "%d Aufträge warten" % waiting)
                    if waiting else "Heute stehen keine Tickets an.")
            make_label(body, text, font=F["body"], fg=C["text_soft"], wraplength=980,
                       justify="left", anchor="w").pack(anchor="w", pady=(8, 0))
            if not item and state.firm and state.firm_open_count():
                NeoButton(body, "Aufträge öffnen",
                          lambda: self.app.views["firma"].open_tab("auftraege"),
                          kind="primary").pack(anchor="w", pady=(8, 0))
            if not item and state.firm and fg.projects_summary(state):
                make_label(body, fg.projects_summary(state), font=F["body"],
                           fg=C["text_soft"], wraplength=980, justify="left",
                           anchor="w").pack(anchor="w", pady=(10, 0))
                NeoButton(body, "Projekte öffnen",
                          lambda: self.app.views["firma"].open_tab("projekte"),
                          kind="primary").pack(anchor="w", pady=(8, 0))
            if not item and state.founding_ready():
                make_label(body, fg.FOUNDING_TEASER, font=F["body_bold"], fg=C["green"],
                           wraplength=980, justify="left", anchor="w").pack(anchor="w",
                                                                            pady=(8, 0))
                NeoButton(body, "Firma gründen", lambda: self.app.show_view("firma"),
                          kind="primary").pack(anchor="w", pady=(8, 0))

        for task, status in tickets:
            self._ticket_row(body, task, status)

        if not item:
            footer = _frame(body)
            footer.pack(fill="x", pady=(12, 0))
            button = NeoButton(footer, "Feierabend machen", self.go_home, kind="accent")
            button.pack(side="left")
            button.set_enabled(state.can_end_day())
            hint = ("Erst alle Tickets bearbeiten oder verschieben." if not state.can_end_day()
                    else "Offene Anfragen und Tickets verfallen beim Feierabend."
                    if state.firm and state.firm_open_count() else
                    "Alle Tickets für heute sind bearbeitet." if state.handled else
                    "Heute ist nichts mehr zu tun.")
            make_label(footer, hint, font=F["small"], fg=C["muted"]).pack(side="left",
                                                                          padx=14)

    def _build_warehouse(self, parent, state):
        """Lager: was unterwegs ist, was da ist und was ausgeliefert wurde."""
        store = state.warehouse()
        box = ctk.CTkFrame(parent, fg_color=C["card_alt"], corner_radius=12, border_width=1,
                           border_color=C["border"])
        box.pack(fill="x", pady=(12, 0))
        sections = [
            ("UNTERWEGS", ["%d × %s · %s · kommt an Arbeitstag %d" % (
                item["menge"], fg.part(item["teil"])["name"],
                fg.dealer(item["haendler"])["name"], item["ankunft"])
                for item in store["unterwegs"]]),
            ("AUF LAGER", ["%d × %s" % (count, fg.part(part_id)["name"])
                           for part_id, count in store["bestand"]]),
            ("AUSGELIEFERT", ["%d × %s an %s" % (
                item["menge"], fg.part(item["teil"])["name"],
                fg.colleague(item["empfaenger"])["name"]) for item in store["ausgeliefert"]]),
        ]
        shown = False
        for title, lines in sections:
            if not lines:
                continue
            shown = True
            make_label(box, title, font=F["label"], fg=C["muted"]).pack(anchor="w", padx=14,
                                                                        pady=(10, 2))
            for line in lines:
                make_label(box, line, font=F["small"], fg=C["text_soft"], anchor="w").pack(
                    anchor="w", padx=14)
        if not shown:
            make_label(box, "Das Lager ist leer. Bestellte Ware taucht hier auf, sobald sie "
                       "unterwegs ist.", font=F["small"], fg=C["muted"], anchor="w").pack(
                anchor="w", padx=14, pady=(10, 0))
        _frame(box, height=10).pack()

    def _ticket_row(self, parent, task, status):
        person = fg.colleague(task["auftraggeber"])
        where = fg.room(task["raum"])["name"]
        if fg.task_site(task) != fg.SITE_OFFICE:
            where = "beim Kunden · %s" % where
        status_text, status_color = STATUS_TEXT[status]
        row = ctk.CTkFrame(parent, fg_color=C["card_alt"], corner_radius=12, border_width=1,
                           border_color=C["border"],
                           cursor="hand2" if status == fg.ST_OPEN else "arrow")
        row.pack(fill="x", pady=4)
        marker = ctk.CTkFrame(row, fg_color=PRIORITY_COLOR[task["prioritaet"]], width=4,
                              height=12, corner_radius=2)
        marker.pack(side="left", fill="y", padx=(10, 0), pady=11)
        inner = _frame(row)
        inner.pack(side="left", fill="x", expand=True, padx=(12, 12), pady=9)
        if task.get("zwischenfall"):
            make_label(inner, "ZWISCHENFALL", font=F["label"], fg=C["red"],
                       anchor="w").pack(anchor="w")
        title = make_label(inner, task["titel"], font=F["body_bold"], fg=C["text"],
                           anchor="w")
        title.pack(anchor="w")
        detail = make_label(
            inner, "%s · %s · Priorität %s · %s" % (
                person["name"], where, task["prioritaet"],
                CATEGORY_SHORT[fg.CAT_NAME[task["cat"]]]),
            font=F["small"], fg=C["muted"], anchor="w")
        detail.pack(anchor="w")
        badge = make_label(row, status_text, font=F["small_bold"], fg=status_color)
        badge.pack(side="right", padx=16)
        if status == fg.ST_OPEN:
            for widget in (row, inner, title, detail, badge, marker):
                widget.bind("<Button-1>", lambda _e, t=task["id"]: self._open_ticket(t))
            row.bind("<Enter>", lambda _e: row.configure(fg_color=C["card_hi"]))
            row.bind("<Leave>", lambda _e: row.configure(fg_color=C["card_alt"]))

    def _select_room(self, room_id):
        self.room = None if room_id == self.room else room_id
        self.render(keep_scroll=True)

    # -- Ticket bearbeiten --------------------------------------------------

    def _open_ticket(self, task_id):
        self.ticket = task_id
        self.render()

    def open_from_site(self, task_id, view_key="buero"):
        """Auftrag direkt bei der Person im Buero oder beim Kunden angenommen."""
        self.return_to = view_key
        self.ticket = task_id
        self.app.show_view("game")

    def _close_ticket(self):
        self.ticket = None
        if self.return_to:
            target, self.return_to = self.return_to, None
            self.render()
            self.app.show_view(target)
            return
        self.render()

    def _build_ticket(self, task_id):
        task = self.game.state.prepared_task(fg.task_by_id(task_id))
        person = fg.colleague(task["auftraggeber"])
        levels = self.game.knowledge()
        gaps = fg.requirement_gaps(task, levels)
        self.used_help = False
        self.answered = False

        back = NeoButton(self.content, RETURN_LABEL.get(self.return_to,
                                                        "Zurück zur Übersicht"), self._close_ticket, kind="ghost", height=32, font=F["small_bold"], icon="arrow_left")
        back.pack(anchor="w")

        card = Card(self.content, title=task["titel"],
                    accent=PRIORITY_COLOR[task["prioritaet"]],
                    subtitle="%sPriorität %s · %s" % (
                        "Zwischenfall · " if task.get("zwischenfall") else "",
                        task["prioritaet"], CATEGORY_SHORT[fg.CAT_NAME[task["cat"]]]))
        card.pack(fill="x", pady=(12, 0))
        body = card.body
        make_label(body, "%s · %s" % (person["name"], person["rolle"]),
                   font=F["body_bold"], fg=C["text"], anchor="w").pack(anchor="w")
        make_label(body, task["ticket"], font=F["body"], fg=C["text_soft"],
                   wraplength=980, justify="left", anchor="w").pack(anchor="w", pady=(8, 0))

        if gaps:
            warn = ctk.CTkFrame(body, fg_color=mix(C["card"], C["yellow"], 0.12),
                                corner_radius=12, border_width=1,
                                border_color=mix(C["yellow"], C["card"], 0.35))
            warn.pack(fill="x", pady=(12, 0))
            make_label(warn, fg.gap_warning(gaps), font=F["small"], fg=C["yellow"],
                       wraplength=940, justify="left", anchor="w").pack(anchor="w",
                                                                        padx=14, pady=10)
            key = gaps[0][0]
            NeoButton(warn, "Karteikarten %s lernen" % CATEGORY_SHORT[fg.CAT_NAME[key]],
                      lambda: self.app.open_cards(fg.CAT_NAME[key]), kind="ghost",
                      height=30, font=F["small_bold"]).pack(anchor="w", padx=14,
                                                            pady=(0, 10))

        make_label(body, task["frage"], font=F["h3"], fg=C["text"], wraplength=980,
                   justify="left", anchor="w").pack(anchor="w", pady=(16, 8))
        state = self.game.state
        self.available = state.available_parts(task)
        if task["typ"] == "auswahl":
            self.options = OptionList(body, bg=C["card"])
            options = list(task["optionen"])
            random.shuffle(options)
            self.options.set_options(options)
            self.options.pack(fill="x")
        elif task["typ"] == "bauteile":
            self.options = SlotBoard(body, task, self.available, state.stock())
            self.options.pack(fill="x")
        elif task["typ"] == "bestellung":
            self.options = OrderBoard(body, task)
            self.options.pack(fill="x")
        elif task["typ"] == "rack":
            self.options = RackBoard(body, task)
            self.options.pack(fill="x")
        elif task["typ"] == "formular":
            self.options = FormBoard(body, task)
            self.options.pack(fill="x")
        elif task["typ"] == "terminal":
            self.options = TerminalBoard(body, task)
            self.options.pack(fill="x")
        elif task["typ"] == "diagnose":
            self.options = DiagnoseBoard(body, task, self.available, state.stock(),
                                         lambda part_id: self._order_spare(task, part_id))
            self.options.pack(fill="x")
        elif task["typ"] == "wartung":
            self.options = MaintenanceBoard(body, task)
            self.options.pack(fill="x")
        else:
            self.options = MatchBoard(body, task)
            self.options.pack(fill="x")

        # Leere Rahmen bekommen eine Mindesthoehe von 1, sonst reservieren
        # CTkFrames 200 Pixel, bevor Hilfe oder Ergebnis darin stehen.
        self.help_box = _frame(body, height=1)
        self.help_box.pack(fill="x")
        self.result_box = _frame(body, height=1)
        self.result_box.pack(fill="x")

        self.controls = _frame(self.content)
        self.controls.pack(fill="x", pady=(14, 0))
        self.btn_submit = NeoButton(self.controls, "Lösung einreichen",
                                    lambda: self._submit(task), kind="primary")
        self.btn_submit.pack(side="left")
        self.btn_help = NeoButton(self.controls, "Hilfe anzeigen",
                                  lambda: self._show_help(task), kind="ghost")
        self.btn_help.pack(side="left", padx=10)
        self.btn_defer = NeoButton(self.controls, "Verschieben",
                                   lambda: self._defer(task), kind="ghost")
        self.btn_defer.pack(side="left")
        make_label(self.controls, "Ohne Hilfe gibt es %d %% Bonus."
                   % round(fg.GAME["balancing"]["bonus_ohne_hilfe"] * 100),
                   font=F["small"], fg=C["muted"]).pack(side="left", padx=14)

    def _show_help(self, task):
        if self.used_help or self.answered:
            return
        self.used_help = True
        self.btn_help.set_enabled(False)
        box = ctk.CTkFrame(self.help_box, fg_color=mix(C["card"], C["accent"], 0.08),
                           corner_radius=12, border_width=1,
                           border_color=mix(C["accent"], C["card"], 0.5))
        box.pack(fill="x", pady=(14, 0))
        make_label(box, "HILFE", font=F["label"], fg=C["accent"]).pack(anchor="w", padx=14,
                                                                     pady=(10, 0))
        make_label(box, task["hilfe"], font=F["body"], fg=C["text_soft"], wraplength=940,
                   justify="left", anchor="w").pack(anchor="w", padx=14, pady=(4, 12))

    def _submit(self, task):
        if self.answered:
            return
        if task["typ"] == "auswahl":
            answer = self.options.get()
            if not answer:
                messagebox.showwarning("Hinweis", "Bitte wähle eine Antwort aus.")
                return
        elif task["typ"] in fg.PROBLEM_TYPES:
            if not self.options.complete():
                messagebox.showwarning("Hinweis", EMPTY_HINT[getattr(
                    self.options, "hint_key", task["typ"])])
                return
            answer = dict(self.options.answer)
        else:
            if not self.options.complete():
                messagebox.showwarning("Hinweis", "Bitte ordne zuerst alle Begriffe zu.")
                return
            answer = dict(self.options.answer)
        try:
            payload = self.game.solve(task["id"], answer, self.used_help)
        except ValueError as exc:
            messagebox.showinfo("Hinweis", str(exc))
            self._close_ticket()
            return
        self.answered = True
        if task["typ"] == "auswahl":
            self.options.reveal(task["antwort"])
        elif task["typ"] in fg.PROBLEM_TYPES:
            self.options.reveal(payload["richtig"])
        else:
            self.options.reveal()
        self.app.notify_progress()
        self._show_result(task, payload)

    def _show_result(self, task, payload):
        right = payload["richtig"]
        color = C["green"] if right else C["red"]
        box = ctk.CTkFrame(self.result_box, fg_color=mix(C["card"], color, 0.1),
                           corner_radius=12, border_width=1,
                           border_color=mix(color, C["card"], 0.4))
        box.pack(fill="x", pady=(14, 0))
        make_label(box, fg.result_text(task, payload, self.available), font=F["body_bold"],
                   fg=color,
                   wraplength=940, justify="left", anchor="w").pack(anchor="w", padx=14,
                                                                    pady=(12, 4))
        make_label(box, task["erklaerung"], font=F["body"], fg=C["text_soft"],
                   wraplength=940, justify="left", anchor="w").pack(anchor="w", padx=14,
                                                                    pady=(0, 12))

        links = fg.learn_links(task, limit=5)
        if links:
            learn = Card(self.result_box, title="Passend dazu lernen", accent=C["purple"],
                         subtitle="Karteikarten und Fragen zum Thema", bg=C["card_alt"])
            learn.pack(fill="x", pady=(14, 0))
            for kind, category, title, _detail in links:
                row = ctk.CTkFrame(learn.body, fg_color=C["card"], corner_radius=10,
                                   cursor="hand2")
                row.pack(fill="x", pady=3)
                label = make_label(row, "%s · %s" % (kind, title), font=F["small"],
                                   fg=C["text_soft"], wraplength=900, justify="left",
                                   anchor="w", cursor="hand2")
                label.pack(anchor="w", padx=12, pady=8)
                for widget in (row, label):
                    widget.bind("<Button-1>",
                                lambda _e, k=kind, t=title: self._open_learn(k, t))

        for child in self.controls.winfo_children():
            child.destroy()
        NeoButton(self.controls, RETURN_LABEL.get(self.return_to, "Zurück zur Übersicht"),
                  self._close_ticket,
                  kind="primary").pack(side="left")

    def _open_learn(self, kind, title):
        self.ticket = None
        self.app.open_search_hit(kind, title)

    def _order_spare(self, task, part_id):
        """Austausch: fehlendes Ersatzteil nachbestellen, das Ticket wartet."""
        if self.answered:
            return
        item = fg.part(part_id)
        days = fg.spare_delivery_days()
        if not messagebox.askyesno(
                "Ersatzteil nachbestellen",
                "%s für %d € nachbestellen? Es kommt %s, bis dahin wartet das Ticket." % (
                    item["name"], item["preis"], "am nächsten Arbeitstag" if days == 1
                    else "in %d Arbeitstagen" % days)):
            return
        try:
            self.game.order_spare(task["id"], part_id)
        except ValueError as exc:
            messagebox.showinfo("Hinweis", str(exc))
        self.app.notify_progress()
        self._close_ticket()

    def _defer(self, task):
        if self.answered:
            return
        if not messagebox.askyesno("Ticket verschieben",
                                   "Das Ticket auf einen späteren Arbeitstag verschieben? "
                                   "Das kostet etwas Zuverlässigkeit."):
            return
        try:
            self.game.defer(task["id"])
        except ValueError as exc:
            messagebox.showinfo("Hinweis", str(exc))
        self.app.notify_progress()
        self._close_ticket()


class SiteView(ScrollArea):
    """Grossansicht eines Ortes (Buero, Kunde, Zuhause): Die Spielfigur laeuft
    per Klick; unter dem Grundriss stehen Text und Knoepfe aus
    fisi_game.place_message - so verhalten sich PC und Handy gleich."""

    KEY = "buero"
    TITLE = "Büro"
    SUBTITLE = "Klicke auf eine Person oder einen Ort · Pfeiltasten gehen auch"

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self.content = _frame(self.inner)
        self.content.pack(fill="both", expand=True, padx=28, pady=(2, 28))
        self.plan = None
        self.info = None

    @property
    def game_view(self):
        return self.app.views["game"]

    @property
    def state(self):
        return self.game_view.game.state

    def site(self):
        return fg.SITE_OFFICE

    def on_show(self):
        self.game_view.game.reload()
        self.render()

    def refresh(self):
        self.on_show()

    def render(self):
        for child in self.content.winfo_children():
            child.destroy()
        state = self.state
        if state.profile is None:
            card = Card(self.content, title=self.TITLE, accent=C["accent"])
            card.pack(fill="x")
            make_label(card.body, "Lege zuerst unter „Spiel“ deine Spielfigur an.",
                       font=F["body"], fg=C["text_soft"]).pack(anchor="w")
            NeoButton(card.body, "Zum Spiel", lambda: self.app.show_view("game"),
                      kind="primary").pack(anchor="w", pady=(12, 0))
            return
        self._build_head(state)
        card = Card(self.content, title=self.card_title(), accent=self.accent(),
                    subtitle=self.SUBTITLE)
        card.pack(fill="x", pady=(0, 0))
        site = self.site()
        self.plan = WalkPlan(card.body, self._arrived, site=site,
                             on_click=self.plan_click)
        self.plan.pack(fill="x")
        position = self.game_view.position(site)
        self.plan.overlay = self.overlay()
        self.plan.set_state(state, None, position)
        self.info = _frame(card.body)
        self.info.pack(fill="x", pady=(12, 0))
        self._show_info(position, fg.person_near(*position, content=self.plan.content()))
        self._build_below(state)
        plan = self.plan
        self.after(50, lambda: plan.winfo_exists() and plan.focus_set())

    # Hooks fuer die Unterklassen
    def card_title(self):
        return fg.site_name(self.site())

    def accent(self):
        return C["accent"]

    def _build_head(self, state):
        pass

    def _build_below(self, state):
        pass

    def overlay(self):
        return []

    def plan_click(self, _x, _y):
        return False

    def _arrived(self, position, person):
        self.game_view.positions[self.site()] = position
        self._show_info(position, person)

    def _show_info(self, position, person):
        for child in self.info.winfo_children():
            child.destroy()
        state = self.state
        site = self.site()
        notice = self.game_view.notices.pop(site, None)
        if notice:
            box = ctk.CTkFrame(self.info, fg_color=mix(C["card"], C["purple"], 0.1),
                               corner_radius=12, border_width=1,
                               border_color=mix(C["purple"], C["card"], 0.45))
            box.pack(fill="x", pady=(0, 10))
            make_label(box, notice[0], font=F["body_bold"], fg=C["text"], anchor="w").pack(
                anchor="w", padx=14, pady=(10, 0))
            make_label(box, notice[1], font=F["small"], fg=C["text_soft"], wraplength=900,
                       justify="left", anchor="w").pack(anchor="w", padx=14, pady=(2, 10))
        title, text, actions = fg.place_message(site, position, person, state,
                                                self.plan.content())
        make_label(self.info, title, font=F["body_bold"], fg=C["text"],
                   anchor="w").pack(anchor="w")
        make_label(self.info, text, font=F["small"], fg=C["text_soft"], anchor="w",
                   wraplength=900, justify="left").pack(anchor="w", pady=(2, 0))
        if actions:
            row = _frame(self.info)
            row.pack(anchor="w", pady=(10, 0))
            for action, label in actions:
                NeoButton(row, label, lambda a=action: self.game_view.run_action(a, self.KEY),
                          kind="primary").pack(side="left", padx=(0, 10))


class OfficeView(SiteView):
    """Unterpunkt "Buero": das Gebaeude in gross. Die Spielfigur laeuft per
    Klick zu Kolleginnen und Kollegen; wer einen Auftrag hat, traegt ein
    gruenes "!" - dort laesst sich das Ticket direkt annehmen. An der
    Eingangstuer geht es in den Feierabend."""

    def card_title(self):
        return "Büro"


class CustomerView(SiteView):
    """Unterpunkt "Kunde": Bahnhof Talheim und (ab Tag 12) Talheim-Nord."""

    KEY = "kunde"
    TITLE = "Kunde"

    def site(self):
        places = [place["id"] for place in fg.open_places(self.state)]
        if self.game_view.place not in places:
            self.game_view.place = places[0]
        return self.game_view.place

    def accent(self):
        return C["blue"]

    def _build_head(self, state):
        places = fg.open_places(state)
        counts = state.open_count_by_site()
        if len(places) > 1:
            options = [(place["id"], "%s%s" % (fg.place_label(place, places), " (%d)" % counts[place["id"]]
                                               if counts.get(place["id"]) else ""))
                       for place in places]
            ChoiceRow(self.content, options, self.site(), self._choose).pack(
                anchor="w", pady=(0, 12))
        place = fg.customer_place(self.site())
        if place.get("text"):
            make_label(self.content, place["text"], font=F["small"], fg=C["text_dim"],
                       wraplength=980, justify="left", anchor="w").pack(anchor="w",
                                                                        pady=(0, 10))

    def _choose(self, place_id):
        self.game_view.place = place_id
        self.render()


class HomeView(SiteView):
    """Unterpunkt "Zuhause": die eigene Wohnung. Im Modus "Einrichten" kauft
    man Moebel, stellt sie per Klick auf, dreht, verschiebt oder verkauft sie,
    waehlt Boeden und zieht in groessere Wohnungen um."""

    KEY = "zuhause"
    TITLE = "Zuhause"

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.editing = False
        self.selected = None      # Stueck, das gerade eingerichtet wird
        self.turn = 0
        self.problem = ""

    def site(self):
        return fg.SITE_HOME

    def accent(self):
        return C["accent2"]

    def card_title(self):
        return fg.apartment(self.state.home_id)["name"]

    @property
    def SUBTITLE(self):
        if self.editing:
            return "Möbel anklicken zum Auswählen · freie Stelle anklicken zum Aufstellen"
        return "Klicke irgendwo hin, um dorthin zu gehen · Pfeiltasten gehen auch"

    def _build_head(self, state):
        row = _frame(self.content)
        row.pack(fill="x", pady=(0, 12))
        money = "Kontostand: %s" % _euro(state.money)
        if state.rent:
            money += "   ·   Miete: %s pro Arbeitstag" % _euro(state.rent)
        make_label(row, money, font=F["body_bold"],
                   fg=C["text"] if state.money >= 0 else C["red"]).pack(side="left")
        NeoButton(row, "Fertig" if self.editing else "Einrichten", self._toggle_edit,
                  kind="primary" if self.editing else "ghost", height=32,
                  font=F["small_bold"]).pack(side="right")

    def _toggle_edit(self):
        self.editing = not self.editing
        self.selected = None
        self.problem = ""
        self.render()

    # -- Einrichten ---------------------------------------------------------

    def overlay(self):
        if not self.editing or not self.selected:
            return []
        item = next((i for i in fg.placed_furniture(self.state)
                     if i["stueck"] == self.selected), None)
        if item is None:
            return []
        return [{"k": "rect", "x": item["x"] - 0.08, "y": item["y"] - 0.08,
                 "w": item["w"] + 0.16, "h": item["h"] + 0.16, "fill": "",
                 "line": C["accent"], "lw": 0.08, "r": 0.1}]

    def plan_click(self, x, y):
        if not self.editing:
            return False
        state = self.state
        hit = fg.furniture_at(state, x, y)
        if hit and hit["stueck"] != self.selected:
            self.selected = hit["stueck"]
            self.turn = hit["dreh"]
            self.problem = ""
            self.render()
            return True
        if not self.selected:
            self.problem = "Wähle zuerst ein Möbelstück aus (im Grundriss oder im Karton)."
            self.render()
            return True
        item = fg.furniture_item(state.furniture.get(self.selected))
        w, h = fg.furniture_size(item, self.turn)
        try:
            self.game_view.game.place_furniture(self.selected, x - w / 2.0, y - h / 2.0,
                                                self.turn)
            self.problem = ""
        except ValueError as exc:
            self.problem = str(exc)
        self.render()
        return True

    def _select(self, piece):
        self.selected = piece
        self.turn = fg.home_layout(self.state)["moebel"].get(piece, [0, 0, 0])[2]
        self.problem = "Klicke im Grundriss auf die Stelle, wo es stehen soll."
        self.render()

    def _rotate(self):
        self.turn = (self.turn + 1) % 4
        placed = fg.home_layout(self.state)["moebel"].get(self.selected)
        if placed:
            item = fg.furniture_item(self.state.furniture[self.selected])
            old_w, old_h = fg.furniture_size(item, placed[2])
            new_w, new_h = fg.furniture_size(item, self.turn)
            # um die Mitte drehen
            x = placed[0] + old_w / 2.0 - new_w / 2.0
            y = placed[1] + old_h / 2.0 - new_h / 2.0
            try:
                self.game_view.game.place_furniture(self.selected, x, y, self.turn)
                self.problem = ""
            except ValueError as exc:
                self.turn = placed[2]
                self.problem = str(exc)
        self.render()

    def _box(self):
        self.game_view.game.box_furniture(self.selected)
        self.selected = None
        self.problem = ""
        self.render()

    def _sell(self):
        item = fg.furniture_item(self.state.furniture.get(self.selected))
        price = int(item["preis"] * fg.GAME["wohnungen"].get("rueckkauf", 0.5))
        if not messagebox.askyesno("Verkaufen", "%s für %s verkaufen?"
                                   % (item["name"], _euro(price))):
            return
        try:
            self.game_view.game.sell_furniture(self.selected)
        except ValueError as exc:
            messagebox.showinfo("Hinweis", str(exc))
        self.selected = None
        self.problem = ""
        self.render()

    def _buy(self, item_id):
        try:
            piece = self.game_view.game.buy_furniture(item_id)
        except ValueError as exc:
            messagebox.showinfo("Hinweis", str(exc))
            return
        self.app.notify_progress()
        self._select(piece)

    def _floor(self, room_id, kind=None, color=None):
        current = fg.home_layout(self.state)["boeden"].get(room_id)
        building = fg.apartment(self.state.home_id)["gebaeude"]
        base = next(r for r in building["raeume"] if r["id"] == room_id)
        old_kind, old_color = current or [base.get("boden", "parkett"), None]
        self.game_view.game.set_floor(room_id, kind or old_kind, color or old_color)
        self.render()

    def _move(self, home):
        rent = fg.rent_mode()
        if not messagebox.askyesno("Umziehen",
                                   fg.move_texts(self.state, home, rent)[1]):
            return
        try:
            self.game_view.game.move_home(home["id"], rent=rent)
        except ValueError as exc:
            messagebox.showinfo("Hinweis", str(exc))
            return
        self.game_view.positions.pop(fg.SITE_HOME, None)
        self.selected = None
        self.editing = True
        self.app.notify_progress()
        self.render()

    def _build_below(self, state):
        if not self.editing:
            return
        if self.problem:
            make_label(self.info, self.problem, font=F["small_bold"], fg=C["yellow"],
                       wraplength=900, justify="left", anchor="w").pack(anchor="w",
                                                                        pady=(10, 0))
        grid = _frame(self.content)
        grid.pack(fill="x", pady=(14, 0))
        grid.columnconfigure(0, weight=1, uniform="home")
        grid.columnconfigure(1, weight=1, uniform="home")

        # Auswahl und Kartons
        mine = Card(grid, title="Deine Möbel", accent=C["accent"],
                    subtitle="Ausgewähltes Stück und Umzugskartons")
        mine.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        if self.selected and self.selected in state.furniture:
            item = fg.furniture_item(state.furniture[self.selected])
            make_label(mine.body, "AUSGEWÄHLT", font=F["label"], fg=C["muted"]).pack(
                anchor="w")
            make_label(mine.body, item["name"], font=F["body_bold"], fg=C["text"],
                       anchor="w").pack(anchor="w", pady=(2, 8))
            row = _frame(mine.body)
            row.pack(anchor="w")
            for label, command in (("Drehen", self._rotate), ("In den Karton", self._box),
                                   ("Verkaufen", self._sell)):
                NeoButton(row, label, command, kind="ghost", height=32,
                          font=F["small_bold"]).pack(side="left", padx=(0, 8))
        boxed = fg.boxed_furniture(state)
        make_label(mine.body, "IM KARTON", font=F["label"], fg=C["muted"]).pack(
            anchor="w", pady=(14, 4))
        if not boxed:
            make_label(mine.body, "Alles ist ausgepackt.", font=F["small"],
                       fg=C["text_dim"]).pack(anchor="w")
        for piece, item_id in boxed:
            item = fg.furniture_item(item_id)
            self._item_row(mine.body, item["name"], "", "Aufstellen",
                           lambda p=piece: self._select(p), active=piece == self.selected)

        # Moebelhaus
        shop = Card(grid, title="Möbelhaus", accent=C["purple"],
                    subtitle="Einmal bezahlen, für immer behalten")
        shop.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        for item in fg.shop_items():
            self._item_row(shop.body, item["name"], _euro(item["preis"]), "Kaufen",
                           lambda i=item["id"]: self._buy(i),
                           enabled=state.money >= item["preis"])

        lower = _frame(self.content)
        lower.pack(fill="x", pady=(14, 0))
        lower.columnconfigure(0, weight=1, uniform="home2")
        lower.columnconfigure(1, weight=1, uniform="home2")

        # Boeden
        floors = Card(lower, title="Böden", accent=C["green"],
                      subtitle="Belag und Farbe je Raum")
        floors.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        layout = fg.home_layout(state)
        for item in fg.apartment(state.home_id)["gebaeude"]["raeume"]:
            kind, color = layout["boeden"].get(item["id"], [item.get("boden", "parkett"),
                                                            None])
            make_label(floors.body, item["name"], font=F["body_bold"], fg=C["text"],
                       anchor="w").pack(anchor="w", pady=(8, 4))
            ChoiceRow(floors.body, fg.FLOOR_KINDS, kind,
                      lambda k, r=item["id"]: self._floor(r, kind=k)).pack(anchor="w")
            ChoiceRow(floors.body, fg.FLOOR_COLORS, color,
                      lambda c, r=item["id"]: self._floor(r, color=c)).pack(anchor="w",
                                                                            pady=(4, 0))

        # Wohnungen
        rent = fg.rent_mode()
        homes = Card(lower, title="Wohnung", accent=C["orange"],
                     subtitle=fg.HOME_SUBTITLE[rent])
        homes.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        flat = fg.apartment(state.home_id)
        make_label(homes.body, "Du wohnst in: %s" % flat["name"], font=F["body_bold"],
                   fg=C["text"], anchor="w").pack(anchor="w")
        if fg.rent_text(state):
            make_label(homes.body, fg.rent_text(state), font=F["small_bold"],
                       fg=C["orange"], anchor="w").pack(anchor="w", pady=(2, 0))
        make_label(homes.body, flat.get("text", ""), font=F["small"], fg=C["text_dim"],
                   wraplength=420, justify="left", anchor="w").pack(anchor="w", pady=(2, 8))
        for home in fg.moves_available(state):
            # Kaution und Miete sind zu lang fuer die Preisspalte - eigene Zeile
            price = fg.move_texts(state, home, rent)[0]
            self._item_row(homes.body, home["name"], "" if rent else price,
                           "Umziehen", lambda h=home: self._move(h),
                           enabled=not fg.move_offer(state, home, rent)["fehlt"],
                           detail=home.get("text", ""), price_line=price if rent else "")
        if not fg.moves_available(state):
            make_label(homes.body, "Du wohnst schon in der größten Wohnung.",
                       font=F["small"], fg=C["text_dim"]).pack(anchor="w")

    def _item_row(self, parent, title, price, label, command, enabled=True, active=False,
                  detail="", price_line=""):
        row = ctk.CTkFrame(parent, fg_color=C["card_hi"] if active else C["card_alt"],
                           corner_radius=10, border_width=1, border_color=C["border"])
        row.pack(fill="x", pady=3)
        text = _frame(row)
        text.pack(side="left", fill="x", expand=True, padx=12, pady=7)
        make_label(text, title, font=F["small_bold"], fg=C["text"], anchor="w").pack(
            anchor="w")
        if price_line:
            make_label(text, price_line, font=F["small"], fg=C["text_dim"], anchor="w").pack(
                anchor="w")
        if detail:
            make_label(text, detail, font=F["tiny"], fg=C["muted"], wraplength=300,
                       justify="left", anchor="w").pack(anchor="w")
        button = NeoButton(row, label, command, kind="ghost", height=28,
                           font=F["small_bold"])
        button.pack(side="right", padx=10)
        button.set_enabled(enabled)
        if price:
            make_label(row, price, font=F["small"], fg=C["text_dim"]).pack(side="right",
                                                                           padx=4)


class FirmView(ScrollArea):
    """Unterpunkt "Firma" (ab 0.33): Gruendung, Mitarbeiter, Bewerbungen,
    Gebaeude und Finanzen. Vor der Gruendung nur die Finanzen und was fuer
    die Gruendung noch fehlt."""

    KEY = "firma"

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self.content = _frame(self.inner)
        self.content.pack(fill="both", expand=True, padx=28, pady=(2, 28))
        self.tab = "auftraege"
        self.training_for = None     # Mitarbeiter, fuer den gerade ein Fach gewaehlt wird
        self.name_entry = None
        self.offer_for = None        # Anfrage, die gerade kalkuliert wird
        self.markup = None           # gewaehlter Gewinnzuschlag
        self.board = None            # Formular der Kalkulation
        self.saved_answer = {}
        self.show_help = False
        self.assign_for = None       # Kundenticket, fuer das gerade jemand gewaehlt wird
        self.team_for = None         # Projekt, dessen Team gerade geaendert wird
        self.details_for = set()     # Projekte/Ausschreibungen mit aufgeklappten Details

    @property
    def game(self):
        return self.app.views["game"].game

    def on_show(self):
        self.game.reload()
        self.render()

    def refresh(self):
        self.on_show()

    def render(self, keep_scroll=False):
        for child in self.content.winfo_children():
            child.destroy()
        state = self.game.state
        if state.profile is None:
            card = Card(self.content, title="Firma", accent=C["accent"])
            card.pack(fill="x")
            make_label(card.body, "Lege zuerst unter „Spiel“ deine Spielfigur an.",
                       font=F["body"], fg=C["text_soft"]).pack(anchor="w")
            NeoButton(card.body, "Zum Spiel", lambda: self.app.show_view("game"),
                      kind="primary").pack(anchor="w", pady=(12, 0))
            return
        if state.firm:
            self._build_head(state)
        else:
            self._build_founding(state)
        tabs = fg.firm_tabs(state)
        if self.tab not in dict(tabs):
            self.tab = tabs[0][0]
        if len(tabs) > 1:
            ChoiceRow(self.content, tabs, self.tab, self._choose).pack(anchor="w",
                                                                       pady=(14, 0))
        getattr(self, "_build_" + self.tab)(state)
        if not keep_scroll:
            self.to_top()

    def _choose(self, tab):
        self.tab = tab
        self.training_for = None
        self.offer_for = self.assign_for = self.team_for = None
        self.render()

    def open_tab(self, tab):
        """Von aussen (Spieluebersicht) direkt einen Reiter oeffnen."""
        self.tab = tab
        self.app.show_view(self.KEY)

    def _error(self, exc):
        messagebox.showinfo("Hinweis", str(exc))

    def _changed(self):
        self.app.notify_progress()
        self.render(keep_scroll=True)

    # -- Kopf und Gruendung ---------------------------------------------------

    def _build_head(self, state):
        card = Card(self.content, title="Eigene Firma", accent=C["green"],
                    subtitle="gegründet an Arbeitstag %d" % state.firm["tag"])
        card.pack(fill="x")
        make_label(card.body, state.firm["name"], font=F["h1"], fg=C["text"],
                   anchor="w").pack(anchor="w")
        stage = state.firm_stage()
        make_label(card.body, "%s · %s" % (fg.firm_rules()["gebaeude"]["name"], stage["name"]),
                   font=F["body_bold"], fg=C["green"], anchor="w").pack(anchor="w",
                                                                        pady=(2, 0))
        make_label(card.body, "Kontostand: %s   ·   %s" % (_euro(state.money),
                                                         fg.firm_summary(state)),
                   font=F["small"], fg=C["text_dim"] if state.money >= 0 else C["red"],
                   anchor="w").pack(anchor="w", pady=(8, 0))

    def _build_founding(self, state):
        goal = fg.GAME["balancing"]["gruendung"]
        card = Card(self.content, title="Eigenes Unternehmen", accent=C["green"],
                    subtitle="Ziel: %s, %d %% Ansehen, alle Aufträge erledigt"
                    % (_euro(goal["startkapital"]), goal["mindest_reputation"]))
        card.pack(fill="x")
        missing = state.founding_missing()
        if missing:
            bar = GradientBar(card.body, "Weg zum eigenen Unternehmen", C["green"],
                              C["accent"], parent_bg=C["card"])
            bar.pack(fill="x")
            bar.set(state.founding_progress() * 100, "%d %%" % round(
                state.founding_progress() * 100))
            make_label(card.body, "Noch nicht so weit: %s." % ", ".join(missing),
                       font=F["body"], fg=C["text_soft"], wraplength=980, justify="left",
                       anchor="w").pack(anchor="w", pady=(10, 0))
            make_label(card.body, "Sobald alles erfüllt ist, kannst du hier als Konkurrenz "
                       "zu Bitweiche deine eigene Firma gründen.", font=F["small"],
                       fg=C["muted"], wraplength=980, justify="left",
                       anchor="w").pack(anchor="w", pady=(4, 0))
            return
        make_label(card.body, fg.founding_text(), font=F["body"], fg=C["text_soft"],
                   wraplength=980, justify="left", anchor="w").pack(anchor="w")
        make_label(card.body, "FIRMENNAME", font=F["label"], fg=C["muted"]).pack(
            anchor="w", pady=(14, 0))
        entry = ctk.CTkEntry(card.body, width=360, height=38, corner_radius=10,
                             border_width=1, fg_color=C["card_alt"],
                             border_color=C["border"], text_color=C["text_soft"],
                             font=F["body"], placeholder_text="Wie heißt deine Firma?",
                             placeholder_text_color=C["muted"])
        entry.pack(anchor="w", pady=(6, 12))
        entry.insert(0, fg.default_firm_name(state))
        self.name_entry = entry
        NeoButton(card.body, "Firma gründen", lambda: self._found(entry.get()),
                  kind="primary").pack(anchor="w")

    def _found(self, name):
        cost = fg.firm_rules()["gruendung"]["kosten"]
        if not messagebox.askyesno("Firma gründen", "„%s“ für %s gründen? Danach arbeitest "
                                   "du nicht mehr bei Bitweiche." % (name.strip(),
                                                                     _euro(cost))):
            return
        try:
            payload = self.game.found_firm(name)
        except ValueError as exc:
            self._error(exc)
            return
        game_view = self.app.views["game"]
        game_view.positions.pop(fg.SITE_OFFICE, None)
        game_view.notices[fg.SITE_OFFICE] = ("Willkommen in deiner Firma",
                                             fg.founded_text(payload["name"]))
        self.tab = "bewerbungen"
        self._changed()

    # -- Auftraege (ab 0.34) ------------------------------------------------------

    def _build_auftraege(self, state):
        rules = fg.offer_rules()
        card = Card(self.content, title="Kundenanfragen", accent=C["pink"],
                    subtitle="Angebote gegen die Mitbewerber · Handlungskosten %d %%, "
                    "Umsatzsteuer %d %%" % (rules["handlungskosten"], rules["ust"]))
        card.pack(fill="x", pady=(14, 0))
        make_label(card.body, "Wähle deinen Gewinnzuschlag und rechne das Angebot durch. "
                   "Gegen dich bieten Bitweiche und andere Firmen, wer genau, siehst du erst "
                   "im Ergebnis. Bist du am günstigsten und stimmt die Rechnung, bekommst du "
                   "den Auftrag. Offene Anfragen verfallen beim Feierabend.", font=F["small"],
                   fg=C["text_dim"], wraplength=980, justify="left", anchor="w").pack(
            anchor="w", pady=(0, 6))
        for inquiry in state.inquiries():
            self._inquiry_row(card.body, state, inquiry)

        tickets = state.customer_tickets()
        free = sum(1 for item in tickets if not item.get("an"))
        box = Card(self.content, title="Kundentickets", accent=C["accent"],
                   subtitle="%d von %d verteilt · Ergebnisse beim Feierabend"
                   % (len(tickets) - free, len(tickets)))
        box.pack(fill="x", pady=(14, 0))
        limits = fg.ticket_rules()
        make_label(box.body, "Verteile die Tickets an deine Leute oder übernimm selbst "
                   "welche (höchstens %d, mit deinem Wissensstand). Jeder Mitarbeiter schafft "
                   "%d Ticket pro Tag, die Chance hängt vom Wert im Fachbereich ab."
                   % (limits["spieler_max"], limits["mitarbeiter_max"]), font=F["small"],
                   fg=C["text_dim"], wraplength=980, justify="left", anchor="w").pack(
            anchor="w", pady=(0, 6))
        levels = self.game.knowledge()
        for ticket in tickets:
            self._ticket_row(box.body, state, ticket, levels)

    def _inquiry_row(self, parent, state, inquiry):
        row = ctk.CTkFrame(parent, fg_color=C["card_alt"], corner_radius=12, border_width=1,
                           border_color=C["border"])
        row.pack(fill="x", pady=5)
        head = _frame(row)
        head.pack(fill="x", padx=14, pady=(10, 0))
        result = inquiry.get("ergebnis")
        if not result and self.offer_for != inquiry["id"]:
            NeoButton(head, "Angebot kalkulieren", lambda i=inquiry["id"]: self._calc(i),
                      kind="primary", height=32, font=F["small_bold"]).pack(side="right")
        make_label(head, inquiry["kunde"]["name"], font=F["body_bold"], fg=C["text"],
                   anchor="w").pack(anchor="w")
        make_label(head, "%d × %s" % (inquiry["menge"], inquiry["artikel"]),
                   font=F["small_bold"], fg=C["pink"], anchor="w").pack(anchor="w")
        make_label(row, inquiry["text"], font=F["small"], fg=C["text_soft"], wraplength=960,
                   justify="left", anchor="w").pack(anchor="w", padx=14, pady=(4, 0))
        make_label(row, fg.inquiry_status_text(inquiry), font=F["small"],
                   fg=C["text_dim"] if not result else
                   C["green"] if result.get("gewonnen") else C["red"],
                   anchor="w").pack(anchor="w", padx=14, pady=(4, 0))
        if result:
            _head, text = fg.offer_result_text(result)
            make_label(row, text, font=F["small"], fg=C["text_soft"], wraplength=960,
                       justify="left", anchor="w").pack(anchor="w", padx=14, pady=(2, 0))
            for line in result.get("probleme") or []:
                make_label(row, "• " + line, font=F["tiny"], fg=C["red"], wraplength=940,
                           justify="left", anchor="w").pack(anchor="w", padx=14)
        elif self.offer_for == inquiry["id"]:
            self._build_calc(row, inquiry)
        _frame(row, height=10).pack()

    def _build_calc(self, parent, inquiry, project=False):
        rules = fg.offer_rules()
        hints = fg.project_rules().get("hilfe") if project else rules.get("hilfe")
        box = _frame(parent)
        box.pack(fill="x", padx=14, pady=(10, 0))
        make_label(box, "GEWINNZUSCHLAG", font=F["label"], fg=C["muted"]).pack(anchor="w")
        ChoiceRow(box, [(value, "%d %%" % value) for value in rules["zuschlaege"]],
                  self.markup, self._pick_markup).pack(anchor="w", pady=(4, 10))
        if self.markup is None:
            make_label(box, "Je höher der Zuschlag, desto mehr bleibt hängen, aber desto "
                       "eher ist ein Mitbewerber günstiger.", font=F["small"], fg=C["muted"],
                       anchor="w").pack(anchor="w")
            NeoButton(box, "Abbrechen", self._cancel_calc, kind="ghost", height=32,
                      font=F["small_bold"]).pack(anchor="w", pady=(10, 0))
            return
        old = self.saved_answer
        task = fg.project_task(inquiry, self.markup) if project else \
            fg.inquiry_task(inquiry, self.markup)
        self.board = FormBoard(box, task)
        self.board.pack(fill="x")
        for key, value in old.items():
            if key in self.board.entries and value:
                self.board.entries[key].insert(0, value)
        if self.show_help:
            tip = ctk.CTkFrame(box, fg_color=mix(C["card_alt"], C["accent"], 0.08),
                               corner_radius=10)
            tip.pack(fill="x", pady=(10, 0))
            for line in hints or []:
                make_label(tip, "• " + line, font=F["small"], fg=C["text_soft"],
                           wraplength=920, justify="left", anchor="w").pack(
                    anchor="w", padx=12, pady=(4, 0))
            _frame(tip, height=8).pack()
        buttons = _frame(box)
        buttons.pack(anchor="w", pady=(12, 0))
        NeoButton(buttons, "Angebot abschicken",
                  lambda: self._send_offer(inquiry, project),
                  kind="primary", height=34, font=F["small_bold"]).pack(side="left")
        NeoButton(buttons, "Hilfe ausblenden" if self.show_help else "Hilfe",
                  self._toggle_help, kind="ghost", height=34,
                  font=F["small_bold"]).pack(side="left", padx=(10, 0))
        NeoButton(buttons, "Abbrechen", self._cancel_calc, kind="ghost", height=34,
                  font=F["small_bold"]).pack(side="left", padx=(10, 0))

    def _calc(self, inquiry_id):
        self.offer_for = inquiry_id
        self.markup = None
        self.board = None
        self.saved_answer = {}
        self.show_help = False
        self.render(keep_scroll=True)

    def _keep_answer(self):
        """Eingaben merken, bevor das Formular neu gebaut wird."""
        self.saved_answer = self.board.answer if self.board is not None else {}

    def _pick_markup(self, value):
        self._keep_answer()
        self.markup = value
        self.render(keep_scroll=True)

    def _toggle_help(self):
        self._keep_answer()
        self.show_help = not self.show_help
        self.render(keep_scroll=True)

    def _cancel_calc(self):
        self.offer_for = None
        self.board = None
        self.render(keep_scroll=True)

    def _send_offer(self, inquiry, project=False):
        if self.board is None or not self.board.complete():
            messagebox.showinfo("Hinweis", "Bitte rechne das Angebot zuerst durch.")
            return
        send = self.game.send_project_offer if project else self.game.send_offer
        try:
            payload = send(inquiry["id"], self.markup, self.board.answer)
        except ValueError as exc:
            self._error(exc)
            return
        self.offer_for = None
        self.board = None
        head, text = fg.offer_result_text(payload)
        messagebox.showinfo(head, text)
        self._changed()

    def _ticket_row(self, parent, state, ticket, levels):
        row = ctk.CTkFrame(parent, fg_color=C["card_alt"], corner_radius=12, border_width=1,
                           border_color=C["border"])
        row.pack(fill="x", pady=5)
        stripe = tk.Frame(row, width=6, bg=cat_color(ticket["cat"]), highlightthickness=0)
        stripe.pack(side="left", fill="y", padx=(10, 0), pady=12)
        buttons = None
        if not ticket.get("an"):
            buttons = _frame(row)
            buttons.pack(side="right", padx=12, pady=10, anchor="n")
        text = _frame(row)
        text.pack(side="left", fill="x", expand=True, padx=(12, 0), pady=10)
        make_label(text, ticket["titel"], font=F["body_bold"], fg=C["text"], anchor="w").pack(
            anchor="w")
        make_label(text, ticket["kunde"]["name"], font=F["small_bold"],
                   fg=cat_color(ticket["cat"]), anchor="w").pack(anchor="w")
        make_label(text, ticket["text"], font=F["small"], fg=C["text_soft"], wraplength=760,
                   justify="left", anchor="w").pack(anchor="w", pady=(2, 0))
        make_label(text, fg.ticket_line(ticket), font=F["small"],
                   fg=C["green"] if ticket.get("an") else C["text_dim"], anchor="w").pack(
            anchor="w", pady=(4, 0))
        if ticket.get("an"):
            return
        if self.assign_for != ticket["id"]:
            NeoButton(buttons, "Zuweisen", lambda i=ticket["id"]: self._pick_ticket(i),
                      kind="primary", height=32, font=F["small_bold"]).pack()
            return
        NeoButton(buttons, "Abbrechen", lambda: self._pick_ticket(None), kind="ghost",
                  height=32, font=F["small_bold"]).pack()
        make_label(text, "WER ÜBERNIMMT?", font=F["label"], fg=C["muted"]).pack(
            anchor="w", pady=(10, 2))
        for option in fg.ticket_candidates(state, ticket, levels):
            line = _frame(text)
            line.pack(anchor="w", pady=2)
            button = NeoButton(line, "%s · %s %d · Chance %d %%" % (
                option["name"], CATEGORY_SHORT[fg.CAT_NAME[ticket["cat"]]], option["wert"],
                option["chance"]), lambda a=option["an"]: self._delegate(ticket["id"], a),
                kind="pill", height=30, font=F["small_bold"])
            button.pack(side="left")
            button.set_enabled(not option["problem"])
            if option["problem"]:
                make_label(line, option["problem"], font=F["tiny"], fg=C["muted"]).pack(
                    side="left", padx=(8, 0))

    def _pick_ticket(self, ticket_id):
        self.assign_for = ticket_id
        self.render(keep_scroll=True)

    def _delegate(self, ticket_id, person):
        try:
            self.game.delegate(ticket_id, person)
        except ValueError as exc:
            self._error(exc)
            return
        self.assign_for = None
        self._changed()

    # -- Projekte (ab 0.35) -------------------------------------------------------

    def _build_projekte(self, state):
        running = state.running_projects()
        limit = state.project_limit()
        card = Card(self.content, title="Laufende Projekte", accent=C["green"],
                    subtitle="%d von %d · Fortschritt beim Feierabend" % (len(running), limit))
        card.pack(fill="x", pady=(14, 0))
        if not running:
            make_label(card.body, "Gerade läuft kein Projekt. Gib unten ein Angebot für eine "
                       "Ausschreibung ab. Gewinnst du, stellst du hier das Team zusammen.",
                       font=F["body"], fg=C["text_soft"], wraplength=980, justify="left",
                       anchor="w").pack(anchor="w")
        levels = self.game.knowledge()
        for project in running:
            self._project_row(card.body, state, project, levels)

        rules = fg.project_rules()
        box = Card(self.content, title="Ausschreibungen", accent=C["pink"],
                   subtitle="Angebote gegen die Mitbewerber · alle %d Arbeitstage eine neue"
                   % rules["abstand_tage"])
        box.pack(fill="x", pady=(14, 0))
        make_label(box.body, "Rechne das Angebot wie bei den Anfragen: Projektarbeit (Punkte "
                   "× %s) plus Material, dazu Handlungskosten und dein Zuschlag. Bei Projekten "
                   "bieten meist zwei oder drei Firmen mit. Gewonnen gibt es %d %% Anzahlung, "
                   "den Rest bei Fertigstellung." % (_euro(rules["stundensatz"]),
                                                     rules["anzahlung"]),
                   font=F["small"], fg=C["text_dim"], wraplength=980, justify="left",
                   anchor="w").pack(anchor="w", pady=(0, 6))
        problem = fg.project_offer_problem(state)
        tenders = state.tenders()
        if not tenders:
            make_label(box.body, "Gerade liegt keine Ausschreibung vor.", font=F["body"],
                       fg=C["text_soft"], anchor="w").pack(anchor="w")
        for project in tenders:
            self._tender_row(box.body, state, project, problem)

        done = state.done_projects()
        if done:
            past = Card(self.content, title="Abgeschlossene Projekte", accent=C["accent"],
                        subtitle="%d insgesamt" % len(done))
            past.pack(fill="x", pady=(14, 0))
            for project in done[-6:][::-1]:
                last = project["tage"][-1] if project["tage"] else {}
                make_label(past.body, "• %s · %s · fertig an Arbeitstag %d%s" % (
                    project["titel"], project["kunde_kurz"], project["fertig"],
                    " · %d %s zu spät" % (last["verzug"], "Tag" if last["verzug"] == 1
                                          else "Tage") if last.get("verzug") else
                    " · pünktlich"), font=F["small"], fg=C["text_soft"], wraplength=980,
                    justify="left", anchor="w").pack(anchor="w", pady=1)

    def _project_head(self, row, project):
        stripe = tk.Frame(row, width=6, bg=cat_color(project["cat"]), highlightthickness=0)
        stripe.pack(side="left", fill="y", padx=(10, 0), pady=12)
        text = _frame(row)
        text.pack(side="left", fill="x", expand=True, padx=(12, 12), pady=10)
        make_label(text, project["titel"], font=F["body_bold"], fg=C["text"],
                   wraplength=760, justify="left", anchor="w").pack(anchor="w")
        make_label(text, project["kunde_kurz"], font=F["small_bold"],
                   fg=cat_color(project["cat"]), anchor="w").pack(anchor="w")
        return text

    def _project_details(self, parent, project):
        key = project.get("projekt") or project["id"]
        if key not in self.details_for:
            return
        template = fg.GAME["projektarbeiten"][project["vorlage"]]
        tip = ctk.CTkFrame(parent, fg_color=mix(C["card_alt"], C["accent"], 0.08),
                           corner_radius=10)
        tip.pack(fill="x", pady=(8, 0))
        for head, body in (("Kunde", template["branche"]),
                           ("Ausgangssituation", template["ausgangssituation"]),
                           ("Auftrag", template["auftrag"])):
            make_label(tip, head.upper(), font=F["label"], fg=C["muted"]).pack(
                anchor="w", padx=12, pady=(8, 0))
            make_label(tip, body, font=F["small"], fg=C["text_soft"], wraplength=740,
                       justify="left", anchor="w").pack(anchor="w", padx=12)
        make_label(tip, "RAHMENBEDINGUNGEN", font=F["label"], fg=C["muted"]).pack(
            anchor="w", padx=12, pady=(8, 0))
        for line in template.get("rahmenbedingungen") or []:
            make_label(tip, "• " + line, font=F["small"], fg=C["text_soft"], wraplength=740,
                       justify="left", anchor="w").pack(anchor="w", padx=12)
        make_label(tip, "Tipp: Unter „Projektarbeit“ im Lernbereich kannst du dieses Projekt "
                   "durcharbeiten. Dann arbeitet dein Team %d %% schneller."
                   % fg.project_rules().get("lernbonus", 0), font=F["tiny"], fg=C["muted"],
                   wraplength=740, justify="left", anchor="w").pack(anchor="w", padx=12,
                                                                     pady=(8, 8))

    def _project_row(self, parent, state, project, levels):
        row = ctk.CTkFrame(parent, fg_color=C["card_alt"], corner_radius=12, border_width=1,
                           border_color=C["border"])
        row.pack(fill="x", pady=5)
        text = self._project_head(row, project)
        share = project["stand"] / float(project["aufwand"]) * 100
        bar = GradientBar(text, "Fortschritt", C["green"], C["accent"], parent_bg=C["card_alt"])
        bar.pack(fill="x", pady=(8, 0))
        bar.set(share, "%d %%" % round(share))
        make_label(text, fg.project_phase_text(project),
                   font=F["small"], fg=C["text_soft"], wraplength=760, justify="left",
                   anchor="w").pack(anchor="w", pady=(6, 0))
        make_label(text, fg.project_status_text(state, project, levels), font=F["small"],
                   fg=C["red"] if state.day > project["frist_tag"] else C["text_dim"],
                   wraplength=760, justify="left", anchor="w").pack(anchor="w", pady=(4, 0))
        make_label(text, fg.project_team_text(state, project), font=F["small_bold"],
                   fg=C["green"] if project["team"] else C["orange"], anchor="w").pack(
            anchor="w", pady=(2, 0))
        buttons = _frame(text)
        buttons.pack(anchor="w", pady=(8, 0))
        pid = project["projekt"]
        editing = self.team_for == pid
        NeoButton(buttons, "Team fertig" if editing else "Team ändern",
                  lambda: self._pick_team(None if editing else pid),
                  kind="ghost" if editing else "primary", height=32,
                  font=F["small_bold"]).pack(side="left")
        NeoButton(buttons, "Details ausblenden" if pid in self.details_for else "Details",
                  lambda: self._toggle_details(pid), kind="ghost", height=32,
                  font=F["small_bold"]).pack(side="left", padx=(10, 0))
        if editing:
            make_label(text, "WER ARBEITET MIT? (antippen zum Aufnehmen oder Herausnehmen)",
                       font=F["label"], fg=C["muted"]).pack(anchor="w", pady=(10, 2))
            for option in fg.project_candidates(state, project, levels):
                line = _frame(text)
                line.pack(anchor="w", pady=2)
                button = NeoButton(line, "%s · %s %d · %s Punkte am Tag" % (
                    option["name"], CATEGORY_SHORT[fg.CAT_NAME[project["cat"]]],
                    option["wert"], fg._num(option["punkte"])),
                    lambda a=option["an"]: self._toggle_member(pid, a),
                    kind="pill", height=30, font=F["small_bold"])
                button.pack(side="left")
                button.set_active(option["im_team"])
                button.set_enabled(option["im_team"] or not option["problem"])
                if option["problem"]:
                    make_label(line, option["problem"], font=F["tiny"], fg=C["muted"]).pack(
                        side="left", padx=(8, 0))
            make_label(text, "Wer im Projekt ist, macht keine Kundentickets und keine "
                       "Routineaufträge. Du selbst hast dann nur noch einen Ticketplatz.",
                       font=F["tiny"], fg=C["muted"], wraplength=760, justify="left",
                       anchor="w").pack(anchor="w", pady=(4, 0))
        self._project_details(text, project)

    def _tender_row(self, parent, state, project, problem):
        row = ctk.CTkFrame(parent, fg_color=C["card_alt"], corner_radius=12, border_width=1,
                           border_color=C["border"])
        row.pack(fill="x", pady=5)
        text = self._project_head(row, project)
        make_label(text, project["text"], font=F["small"], fg=C["text_soft"], wraplength=760,
                   justify="left", anchor="w").pack(anchor="w", pady=(2, 0))
        make_label(text, fg.tender_line(project), font=F["small_bold"], fg=C["text_dim"],
                   anchor="w").pack(anchor="w", pady=(4, 0))
        result = project.get("ergebnis")
        make_label(text, fg.tender_status_text(state, project), font=F["small"],
                   fg=C["text_dim"] if not result else
                   C["green"] if result.get("gewonnen") else C["red"],
                   anchor="w").pack(anchor="w", pady=(2, 0))
        if result:
            _head, body = fg.offer_result_text(result)
            make_label(text, body, font=F["small"], fg=C["text_soft"], wraplength=760,
                       justify="left", anchor="w").pack(anchor="w", pady=(2, 0))
            for line in result.get("probleme") or []:
                make_label(text, "• " + line, font=F["tiny"], fg=C["red"], wraplength=740,
                           justify="left", anchor="w").pack(anchor="w")
        buttons = _frame(text)
        buttons.pack(anchor="w", pady=(8, 0))
        if not result and self.offer_for != project["id"]:
            button = NeoButton(buttons, "Angebot kalkulieren",
                               lambda i=project["id"]: self._calc(i), kind="primary",
                               height=32, font=F["small_bold"])
            button.pack(side="left")
            button.set_enabled(not problem)
        NeoButton(buttons, "Details ausblenden" if project["id"] in self.details_for
                  else "Details", lambda i=project["id"]: self._toggle_details(i),
                  kind="ghost", height=32, font=F["small_bold"]).pack(side="left",
                                                                     padx=(10, 0))
        if problem and not result:
            make_label(text, problem, font=F["tiny"], fg=C["muted"], wraplength=740,
                       justify="left", anchor="w").pack(anchor="w", pady=(4, 0))
        self._project_details(text, project)
        if not result and self.offer_for == project["id"]:
            self._build_calc(text, project, project=True)

    def _pick_team(self, project_id):
        self.team_for = project_id
        self.render(keep_scroll=True)

    def _toggle_details(self, key):
        if key in self.details_for:
            self.details_for.discard(key)
        else:
            self.details_for.add(key)
        self.render(keep_scroll=True)

    def _toggle_member(self, project_id, person):
        try:
            self.game.toggle_project_member(project_id, person)
        except ValueError as exc:
            self._error(exc)
            return
        self._changed()

    # -- Mitarbeiter ------------------------------------------------------------

    def _person_row(self, parent, item, state, applicant=False):
        row = ctk.CTkFrame(parent, fg_color=C["card_alt"], corner_radius=12, border_width=1,
                           border_color=C["border"])
        row.pack(fill="x", pady=5)
        avatar = AvatarCanvas(row, size=72, bg=C["card_alt"])
        avatar.pack(side="left", padx=(12, 14), pady=10, anchor="n")
        avatar.show(item["aussehen"])
        # Knoepfe zuerst packen, damit sie neben breitem Text sichtbar bleiben
        buttons = _frame(row)
        buttons.pack(side="right", padx=12, pady=10, anchor="n")
        text = _frame(row)
        text.pack(side="left", fill="x", expand=True, pady=10)
        make_label(text, item["name"], font=F["body_bold"], fg=C["text"], anchor="w").pack(
            anchor="w")
        role = item["rolle"]
        if item.get("herkunft") == "bitweiche" and "Bitweiche" not in role:
            role += " · früher bei Bitweiche"
        make_label(text, role, font=F["small"], fg=C["pink"] if item.get("herkunft") ==
                   "bitweiche" else C["accent"], anchor="w").pack(anchor="w")
        make_label(text, fg.values_text(item["werte"]), font=F["small"], fg=C["text_dim"],
                   anchor="w").pack(anchor="w", pady=(4, 0))
        make_label(text, fg.staff_money_text(item), font=F["small"], fg=C["text_dim"],
                   anchor="w").pack(anchor="w")
        extra = fg.training_text(state, item) if not applicant else \
            "Bewerbung liegt vor bis Arbeitstag %d" % item["bis_tag"]
        if extra:
            make_label(text, extra, font=F["small"], fg=C["yellow"] if not applicant else
                       C["muted"], anchor="w").pack(anchor="w")
        if item.get("macke"):
            make_label(text, item["macke"], font=F["tiny"], fg=C["muted"], wraplength=640,
                       justify="left", anchor="w").pack(anchor="w", pady=(2, 0))
        return text, buttons

    def _build_mitarbeiter(self, state):
        staff = state.staff_list()
        card = Card(self.content, title="Mitarbeiter", accent=C["accent"],
                    subtitle="%d von %d Plätzen besetzt" % (len(staff), state.capacity))
        card.pack(fill="x", pady=(14, 0))
        if not staff:
            make_label(card.body, "Noch arbeitest du allein. Unter „Bewerbungen“ findest du "
                       "Leute für deine Firma.", font=F["body"], fg=C["text_soft"],
                       anchor="w").pack(anchor="w")
            return
        numbers = state.firm_day()
        make_label(card.body, "Heute: %s" % fg.firm_day_text(numbers), font=F["small"],
                   fg=C["text_dim"], anchor="w").pack(anchor="w", pady=(0, 6))
        for item in staff:
            text, buttons = self._person_row(card.body, item, state)
            NeoButton(buttons, "Weiterbilden", lambda i=item["id"]: self._pick_training(i),
                      kind="ghost", height=30, font=F["small_bold"]).pack(pady=(0, 6))
            NeoButton(buttons, "Entlassen", lambda i=item: self._fire(i), kind="ghost",
                      height=30, font=F["small_bold"]).pack()
            if self.training_for == item["id"]:
                self._training_choice(text, state, item)

    def _training_choice(self, parent, state, item):
        box = _frame(parent)
        box.pack(anchor="w", pady=(8, 0))
        make_label(box, "Weiterbildung in welchem Fachbereich?", font=F["small_bold"],
                   fg=C["text"], anchor="w").pack(anchor="w")
        row = _frame(box)
        row.pack(anchor="w", pady=(4, 0))
        for key in fg.CAT_ORDER:
            offer = fg.training_offer(state, item["id"], key)
            button = NeoButton(row, "%s (%s)" % (CATEGORY_SHORT[fg.CAT_NAME[key]],
                                                 _euro(offer["preis"])),
                               lambda k=key: self._train(item["id"], k), kind="pill",
                               height=30, font=F["small_bold"])
            button.pack(side="left", padx=(0, 6))
            button.set_enabled(not offer["problem"])
        rules = fg.firm_rules()["weiterbildung"]
        make_label(box, "+%d im Fachbereich (höchstens %d), dauert %d Arbeitstage ohne "
                   "Umsatz." % (rules["plus"], rules["max"], rules["tage"]),
                   font=F["tiny"], fg=C["muted"], anchor="w").pack(anchor="w", pady=(4, 0))
        problem = next((fg.training_offer(state, item["id"], key)["problem"]
                        for key in fg.CAT_ORDER), "")
        if problem and all(fg.training_offer(state, item["id"], key)["problem"]
                           for key in fg.CAT_ORDER):
            make_label(box, problem, font=F["tiny"], fg=C["yellow"], anchor="w").pack(
                anchor="w")

    def _pick_training(self, staff_id):
        self.training_for = None if self.training_for == staff_id else staff_id
        self.render(keep_scroll=True)

    def _train(self, staff_id, cat):
        try:
            self.game.train(staff_id, cat)
        except ValueError as exc:
            self._error(exc)
            return
        self.training_for = None
        self._changed()

    def _fire(self, item):
        if not messagebox.askyesno("Entlassen", "%s wirklich entlassen? Die Person bewirbt "
                                   "sich danach nicht erneut." % item["name"]):
            return
        try:
            self.game.fire(item["id"])
        except ValueError as exc:
            self._error(exc)
            return
        self._changed()

    # -- Bewerbungen ------------------------------------------------------------

    def _build_bewerbungen(self, state):
        found = fg.applicants(state)
        free = state.capacity - len(state.staff)
        rules = fg.firm_rules()["bewerbung"]
        card = Card(self.content, title="Bewerbungen", accent=C["pink"],
                    subtitle="alle %d Arbeitstage neue Bewerbungen" % rules["abstand_tage"])
        card.pack(fill="x", pady=(14, 0))
        make_label(card.body, "Freie Plätze: %d von %d. Gehalt und Umsatz richten sich nach "
                   "den Werten je Fachbereich." % (max(0, free), state.capacity),
                   font=F["small"], fg=C["text_dim"], anchor="w").pack(anchor="w",
                                                                       pady=(0, 6))
        if not found:
            make_label(card.body, "Gerade liegen keine Bewerbungen vor.", font=F["body"],
                       fg=C["text_soft"], anchor="w").pack(anchor="w")
        for item in found:
            _text, buttons = self._person_row(card.body, item, state, applicant=True)
            button = NeoButton(buttons, "Einstellen", lambda i=item["id"]: self._hire(i),
                               kind="primary", height=32, font=F["small_bold"])
            button.pack()
            button.set_enabled(free > 0)

    def _hire(self, applicant_id):
        try:
            self.game.hire(applicant_id)
        except ValueError as exc:
            self._error(exc)
            return
        self._changed()

    # -- Gebaeude ---------------------------------------------------------------

    def _build_gebaeude(self, state):
        stage = state.firm_stage()
        rules = fg.firm_rules()["gebaeude"]
        card = Card(self.content, title=rules["name"], accent=C["green"],
                    subtitle="Stufe %d · %d Arbeitsplätze · Nebenkosten %s pro Arbeitstag"
                    % (stage["stufe"], state.capacity, _euro(stage["nebenkosten"])))
        card.pack(fill="x", pady=(14, 0))
        make_label(card.body, "%s %s" % (rules["text"], stage["text"]), font=F["small"],
                   fg=C["text_soft"], wraplength=980, justify="left", anchor="w").pack(
            anchor="w", pady=(0, 8))
        plan = FloorPlan(card.body, lambda _room: None, max_height=300)
        plan.pack(fill="x")
        plan.set_state(state)
        NeoButton(card.body, "Büro öffnen", lambda: self.app.show_view("buero"), kind="ghost",
                  height=32, font=F["small_bold"]).pack(anchor="w", pady=(10, 0))
        following = state.next_stage()
        more = Card(self.content, title="Ausbau", accent=C["accent"])
        more.pack(fill="x", pady=(14, 0))
        if following is None:
            make_label(more.body, "Mehr Ausbau gibt es in einem der nächsten Updates.",
                       font=F["body"], fg=C["text_soft"], anchor="w").pack(anchor="w")
            return
        make_label(more.body, "%s: %s" % (following["name"], following["text"]),
                   font=F["body"], fg=C["text_soft"], wraplength=980, justify="left",
                   anchor="w").pack(anchor="w")
        make_label(more.body, "Kosten %s · danach %d Arbeitsplätze · Nebenkosten %s pro "
                   "Arbeitstag" % (_euro(following["preis"]), len(following["plaetze"]),
                                   _euro(following["nebenkosten"])),
                   font=F["small"], fg=C["text_dim"], anchor="w").pack(anchor="w",
                                                                       pady=(4, 10))
        button = NeoButton(more.body, "Ausbauen", lambda: self._expand(following),
                           kind="primary")
        button.pack(anchor="w")
        button.set_enabled(state.money >= following["preis"])

    def _expand(self, stage):
        if not messagebox.askyesno("Ausbauen", "„%s“ für %s bauen?" % (
                stage["name"], _euro(stage["preis"]))):
            return
        try:
            self.game.expand()
        except ValueError as exc:
            self._error(exc)
            return
        self.app.views["game"].positions.pop(fg.SITE_OFFICE, None)
        self._changed()

    # -- Finanzen ---------------------------------------------------------------

    def _build_finanzen(self, state):
        card = Card(self.content, title="Kontostand", accent=C["accent"],
                    subtitle="nach den letzten Arbeitstagen")
        card.pack(fill="x", pady=(14, 0))
        make_label(card.body, _euro(state.money), font=F["h1"],
                   fg=C["text"] if state.money >= 0 else C["red"], anchor="w").pack(anchor="w")
        labels, values = fg.balance_series(state)
        chart = LineChart(card.body, height=220, parent_bg=C["card"])
        chart.pack(fill="x", pady=(8, 0))
        chart.set_data(labels, [{"name": "Kontostand", "values": values,
                                 "color": C["green"]}])

        days = Card(self.content, title="Einnahmen und Ausgaben", accent=C["green"],
                    subtitle="die letzten 7 Arbeitstage")
        days.pack(fill="x", pady=(14, 0))
        rows = fg.finance_days(state)
        if not rows:
            make_label(days.body, "Noch nichts gebucht.", font=F["body"],
                       fg=C["text_soft"], anchor="w").pack(anchor="w")
        for item in rows:
            row = ctk.CTkFrame(days.body, fg_color=C["card_alt"], corner_radius=10,
                               border_width=1, border_color=C["border"])
            row.pack(fill="x", pady=3)
            head = _frame(row)
            head.pack(fill="x", padx=12, pady=(7, 0))
            make_label(head, "Arbeitstag %d" % item["tag"], font=F["small_bold"],
                       fg=C["text"]).pack(side="left")
            make_label(head, "%s%s" % ("+" if item["gewinn"] >= 0 else "-",
                                       _euro(abs(item["gewinn"]))), font=F["small_bold"],
                       fg=C["green"] if item["gewinn"] >= 0 else C["red"]).pack(side="right")
            detail = []
            detail += ["%s +%s" % (kind, _euro(value)) for kind, value in item["ein"].items()]
            detail += ["%s -%s" % (kind, _euro(value)) for kind, value in item["aus"].items()]
            make_label(row, " · ".join(detail), font=F["tiny"], fg=C["text_dim"],
                       wraplength=960, justify="left", anchor="w").pack(anchor="w", padx=12,
                                                                        pady=(2, 7))

        lost = fg.lost_to(state)
        rivals = Card(self.content, title="Gegen wen verloren", accent=C["pink"],
                      subtitle="Anfragen und Projekte, die an Mitbewerber gingen")
        rivals.pack(fill="x", pady=(14, 0))
        if not lost:
            make_label(rivals.body, "Bisher hast du keinen Auftrag an einen Mitbewerber "
                       "verloren.", font=F["body"], fg=C["text_soft"], anchor="w").pack(
                anchor="w")
        for name, number in lost:
            line = _frame(rivals.body)
            line.pack(fill="x", pady=1)
            make_label(line, name, font=F["small_bold"], fg=C["text"]).pack(side="left")
            make_label(line, "1 Auftrag" if number == 1 else "%d Aufträge" % number,
                       font=F["small"], fg=C["text_dim"]).pack(side="right")


def _euro(value):
    text = "{:,.0f}".format(value).replace(",", ".")
    return "%s €" % text
