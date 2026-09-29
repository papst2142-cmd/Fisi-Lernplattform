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
    Card, GradientBar, NeoButton, OptionList, ScrollArea, F,
    make_label, px, tk_font,
)

PRIORITY_COLOR = {"niedrig": C["muted"], "normal": C["cyan"], "hoch": C["yellow"],
                  "kritisch": C["red"]}
STATUS_TEXT = {fg.ST_OPEN: ("offen", C["cyan"]), fg.ST_RIGHT: ("erledigt", C["green"]),
               fg.ST_WRONG: ("mit Fehlern", C["red"]),
               fg.ST_DEFERRED: ("verschoben", C["yellow"])}
# Hinweis, wenn beim Einreichen noch nichts eingegeben ist
EMPTY_HINT = {"bauteile": "Bitte setze zuerst Bauteile ein.",
              "bestellung": "Der Warenkorb ist noch leer.",
              "rack": "Bitte baue zuerst Geräte in den Schrank ein.",
              "formular": "Bitte fülle zuerst die Felder aus.",
              "terminal": "Bitte führe zuerst alle Schritte im Terminal aus.",
              "diagnose": "Bitte wähle Ursache und Maßnahme."}
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
    """Das Buerogebaeude von oben (Zeichnung aus fisi_game.building_shapes).
    Raeume sind anklickbar (Treffer ueber die Raumflaechen mit room_at)."""

    MAX_HEIGHT = 440

    def __init__(self, parent, on_room, bg=None, max_height=None):
        self.bg = bg or C["card"]
        self.on_room = on_room
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

    def _layout(self):
        width = self.winfo_width()
        building = fg.GAME["gebaeude"]
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
                                  quests=set(self.state.quests()),
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
        item = fg.room_at(*self.to_building(event))
        if item:
            self.on_room(item["id"])


class WalkPlan(FloorPlan):
    """Grossansicht des Bueros: Die Spielfigur laeuft per Klick (oder mit den
    Pfeiltasten) durch Flur und Tueren. Der Weg kommt aus fisi_game.walk_path,
    genau wie auf dem Handy."""

    SPEED = 7.0            # Grundriss-Einheiten pro Sekunde
    TICK = 16              # Millisekunden pro Bild

    def __init__(self, parent, on_arrive, max_height=640):
        super().__init__(parent, on_room=lambda _room: None, max_height=max_height)
        self.on_arrive = on_arrive
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
        self._draw_player()

    def _draw_player(self):
        self.delete("player")
        profile = self.state.profile
        for shape in fg.player_shapes(self.player_pos, (profile["name"],
                                                        profile["aussehen"])):
            self._shape(shape, tags=("player",))

    def _click(self, event):
        self.focus_set()
        if self.scale <= 0 or self.state is None:
            return
        x, y = self.to_building(event)
        person = fg.person_at(x, y)
        if person:
            route = fg.walk_path(self.player_pos, person["platz"], reach=fg.REACH)
        else:
            route = fg.walk_path(self.player_pos, (x, y))
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
        person = self.target or fg.person_near(*self.player_pos)
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
        if fg.can_stand(x, y):
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
                             text_color=C["cyan"] if value else C["muted"])
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
        badge = make_label(head, extra, font=F["small_bold"], fg=extra_color or C["cyan"],
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
            make_label(self, "Vorgaben: " + rules, font=F["small_bold"], fg=C["cyan"],
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
                             text_color=C["cyan"] if part_id else C["muted"])
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
        make_label(need, lines[-1], font=F["small_bold"], fg=C["cyan"], anchor="w").pack(
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
            count.configure(text=str(value), text_color=C["cyan"] if value else C["muted"])
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
            make_label(head, line, font=F["small_bold"], fg=C["cyan"], anchor="w").pack(
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
                badge.configure(text=fg._he_text(bottom, item["he"]), text_color=C["cyan"])
            else:
                badge.configure(text="liegt bereit", text_color=C["muted"])
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
            entry._entry.configure(insertbackground=C["cyan"], selectbackground=C["purple"])
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
                       fg=C["cyan"] if role == "cursor" else C["text"], wraplength=820,
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

    def __init__(self, parent, task, available=None):
        super().__init__(parent, fg_color="transparent")
        self.task = task
        self.done = []
        self.locked = False
        spare = fg.spare_parts_text(task, available)
        if spare:
            make_label(self, spare, font=F["small_bold"], fg=C["cyan"], anchor="w").pack(
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
        self._paint()

    def check(self, check_id):
        if not self.locked and check_id not in self.done:
            self.done.append(check_id)
            self._paint()

    @property
    def answer(self):
        return {"pruefungen": list(self.done), "ursache": self.cause.get() or "",
                "massnahme": self.measure.get() or ""}

    def complete(self):
        return bool(self.cause.get() and self.measure.get())

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
            make_label(self.notes, item["ergebnis"], font=F["small"], fg=C["cyan"],
                       wraplength=420, justify="left", anchor="w").pack(anchor="w", padx=14)
        if self.done:
            _frame(self.notes, height=10).pack()
        self.counter.configure(text=fg.diagnosis_counter(self.task, self.done))

    def reveal(self, right):
        self.locked = True
        self.cause.reveal(self.task["ursache"])
        self.measure.reveal(self.task["massnahme"])
        self._paint()


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
        # Standort der Figur im Buero (nur waehrend die App laeuft)
        self.player_pos = fg.start_position()
        self.return_to = None     # Ticket kam aus der Bueroansicht
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

    # -- Spielfigur ---------------------------------------------------------

    def _build_profile_editor(self, state):
        profile = state.profile or {"name": "", "aussehen": dict(fg.DEFAULT_APPEARANCE)}
        look = fg.normalize_appearance(self.draft.get("aussehen") or profile["aussehen"])
        self.draft["aussehen"] = look

        if state.profile is None:
            intro = Card(self.content, title="Willkommen im Spiel", accent=C["pink"],
                         subtitle="%s · Kunde: %s" % (fg.GAME["gebaeude"]["firma"],
                                                      fg.GAME["gebaeude"]["kunde"]))
            intro.pack(fill="x")
            make_label(intro.body, fg.GAME["story"]["intro"], font=F["body"],
                       fg=C["text_soft"], wraplength=980, justify="left",
                       anchor="w").pack(anchor="w")

        card = Card(self.content, title="Deine Spielfigur", accent=C["cyan"])
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
        profile = Card(top, title="Spielfigur", accent=C["pink"],
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
        make_label(info, "%s bei der %s" % (state.rank, fg.GAME["gebaeude"]["firma"]),
                   font=F["body_bold"], fg=C["cyan"], anchor="w").pack(anchor="w", pady=(2, 0))
        make_label(info, "Kontostand: %s   ·   Gehalt: %s pro Arbeitstag"
                   % (_euro(state.money), _euro(state.salary)),
                   font=F["small"], fg=C["text_dim"], anchor="w").pack(anchor="w", pady=(8, 0))
        goal = fg.GAME["balancing"]["gruendung"]
        bar = GradientBar(info, "Weg zum eigenen Unternehmen", C["green"], C["cyan"],
                          parent_bg=C["card"])
        bar.pack(fill="x", pady=(8, 0))
        bar.set(state.founding_progress() * 100,
                "Ziel: %s und %d %% Ansehen" % (_euro(goal["startkapital"]),
                                                goal["mindest_reputation"]))
        NeoButton(profile.body, "Figur bearbeiten", self._edit_profile, kind="ghost",
                  height=32, font=F["small_bold"]).pack(anchor="w", pady=(12, 0))

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

        plan = Card(middle, title="Grundriss", accent=C["cyan"],
                    subtitle="Raum anklicken, um die Tickets dort zu sehen")
        plan.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        self.floor = FloorPlan(plan.body, self._select_room)
        self.floor.pack(fill="x")
        self.floor.set_state(state, self.room, self.player_pos)
        NeoButton(plan.body, "Büro öffnen", lambda: self.app.show_view("buero"),
                  kind="ghost", height=32, font=F["small_bold"]).pack(anchor="w",
                                                                      pady=(10, 0))

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
            card = Card(self.content, title="Tickets heute", accent=C["pink"],
                        subtitle="Arbeitstag %d · %d von %d bearbeitet"
                        % (state.day, len(state.handled), len(tickets)))
        card.pack(fill="x", pady=(14, 0))
        body = card.body

        if item:
            make_label(body, item["text"], font=F["small"], fg=C["text_dim"],
                       wraplength=980, justify="left", anchor="w").pack(anchor="w")
            if any(person.get("lagerist") for person in fg.GAME["kollegen"]
                   if person["raum"] == item["id"]):
                self._build_warehouse(body, state)
            for person in fg.GAME["kollegen"]:
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
                    fg.GAME["story"]["alle_erledigt"] if state.all_done() else
                    "Heute stehen keine Tickets an. %s auf eine Lieferung."
                    % ("1 Auftrag wartet" if waiting == 1 else "%d Aufträge warten" % waiting)
                    if waiting else "Heute stehen keine Tickets an.")
            make_label(body, text, font=F["body"], fg=C["text_soft"], wraplength=980,
                       justify="left", anchor="w").pack(anchor="w", pady=(8, 0))

        for task, status in tickets:
            self._ticket_row(body, task, status)

        if not item:
            footer = _frame(body)
            footer.pack(fill="x", pady=(12, 0))
            button = NeoButton(footer, "Arbeitstag beenden", self._end_day, kind="accent")
            button.pack(side="left")
            button.set_enabled(state.can_end_day())
            hint = ("Erst alle Tickets bearbeiten oder verschieben." if not state.can_end_day()
                    else "Alle Tickets für heute sind bearbeitet." if state.handled else
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
        title = make_label(inner, task["titel"], font=F["body_bold"], fg=C["text"],
                           anchor="w")
        title.pack(anchor="w")
        detail = make_label(
            inner, "%s · %s · Priorität %s · %s" % (
                person["name"], fg.room(task["raum"])["name"], task["prioritaet"],
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

    def _end_day(self):
        try:
            payload = self.game.end_day()
        except ValueError as exc:
            messagebox.showinfo("Hinweis", str(exc))
            return
        messagebox.showinfo("Arbeitstag %d beendet" % payload["tag"],
                            "%s\n\nGehalt: %s" % (fg.GAME["story"]["tagesende"],
                                                  _euro(payload["gehalt"])))
        self.room = None
        self.app.notify_progress()
        self.render()

    # -- Ticket bearbeiten --------------------------------------------------

    def _open_ticket(self, task_id):
        self.ticket = task_id
        self.render()

    def open_from_office(self, task_id):
        """Auftrag direkt bei der Person im Buero angenommen."""
        self.return_to = "buero"
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
        task = fg.task_by_id(task_id)
        person = fg.colleague(task["auftraggeber"])
        levels = self.game.knowledge()
        gaps = fg.requirement_gaps(task, levels)
        self.used_help = False
        self.answered = False

        back = NeoButton(self.content, "Zurück ins Büro" if self.return_to else
                         "Zurück zur Übersicht", self._close_ticket, kind="ghost", height=32, font=F["small_bold"], icon="arrow_left")
        back.pack(anchor="w")

        card = Card(self.content, title=task["titel"],
                    accent=PRIORITY_COLOR[task["prioritaet"]],
                    subtitle="Priorität %s · %s" % (
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
            self.options = DiagnoseBoard(body, task, self.available)
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
        box = ctk.CTkFrame(self.help_box, fg_color=mix(C["card"], C["cyan"], 0.08),
                           corner_radius=12, border_width=1,
                           border_color=mix(C["cyan"], C["card"], 0.5))
        box.pack(fill="x", pady=(14, 0))
        make_label(box, "HILFE", font=F["label"], fg=C["cyan"]).pack(anchor="w", padx=14,
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
                messagebox.showwarning("Hinweis", EMPTY_HINT[task["typ"]])
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
        NeoButton(self.controls, "Zurück ins Büro" if self.return_to else
                  "Zurück zur Übersicht", self._close_ticket,
                  kind="primary").pack(side="left")

    def _open_learn(self, kind, title):
        self.ticket = None
        self.app.open_search_hit(kind, title)

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


class OfficeView(ScrollArea):
    """Unterpunkt "Buero": das Gebaeude in gross. Die Spielfigur laeuft per
    Klick zu Kolleginnen und Kollegen; wer einen Auftrag hat, traegt ein
    gruenes "!" - dort laesst sich das Ticket direkt annehmen."""

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self.content = _frame(self.inner)
        self.content.pack(fill="both", expand=True, padx=28, pady=(2, 28))
        self.plan = None

    @property
    def game_view(self):
        return self.app.views["game"]

    def on_show(self):
        self.game_view.game.reload()
        self.render()

    def refresh(self):
        self.on_show()

    def render(self):
        for child in self.content.winfo_children():
            child.destroy()
        state = self.game_view.game.state
        if state.profile is None:
            card = Card(self.content, title="Büro", accent=C["cyan"])
            card.pack(fill="x")
            make_label(card.body, "Lege zuerst unter „Spiel“ deine Spielfigur an.",
                       font=F["body"], fg=C["text_soft"]).pack(anchor="w")
            NeoButton(card.body, "Zum Spiel", lambda: self.app.show_view("game"),
                      kind="primary").pack(anchor="w", pady=(12, 0))
            return
        card = Card(self.content, title="Büro", accent=C["cyan"],
                    subtitle="Klicke auf eine Person oder einen Ort · Pfeiltasten gehen auch")
        card.pack(fill="x")
        self.plan = WalkPlan(card.body, self._arrived)
        self.plan.pack(fill="x")
        self.plan.set_state(state, None, self.game_view.player_pos)
        self.info = _frame(card.body)
        self.info.pack(fill="x", pady=(12, 0))
        self._show_info(self.game_view.player_pos, fg.person_near(*self.game_view.player_pos))
        self.after(50, self.plan.focus_set)

    def _arrived(self, position, person):
        self.game_view.player_pos = position
        self._show_info(position, person)

    def _show_info(self, position, person):
        for child in self.info.winfo_children():
            child.destroy()
        state = self.game_view.game.state
        quests = state.quests()
        title, text = fg.office_message(position, person, quests, state=state)
        make_label(self.info, title, font=F["body_bold"], fg=C["text"],
                   anchor="w").pack(anchor="w")
        make_label(self.info, text, font=F["small"], fg=C["text_soft"], anchor="w",
                   wraplength=900, justify="left").pack(anchor="w", pady=(2, 0))
        if person and quests.get(person["id"]):
            task = quests[person["id"]][0]
            NeoButton(self.info, "Auftrag annehmen",
                      lambda: self.game_view.open_from_office(task["id"]),
                      kind="primary").pack(anchor="w", pady=(10, 0))


def _euro(value):
    text = "{:,.0f}".format(value).replace(",", ".")
    return "%s €" % text
