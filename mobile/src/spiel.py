# -*- coding: utf-8 -*-
"""
FISI Lernplattform (Handy) - Lernspiel
======================================

Die Seite "Spiel" der Handy-App. Die Spiellogik steckt in fisi_game.py (wird
wie fisi_core.py von mobile/vorbereiten.py hierher kopiert), hier wird nur
angezeigt und bedient - mit denselben Daten und Regeln wie am PC.

Hinweis wie in ui.py: In Ereignissen (Tippen) nie control.update() aufrufen,
Flet uebernimmt die Aenderungen danach selbst.
"""

import asyncio
import math
import random

import flet as ft
import flet.canvas as cv

import fisi_game as fg
from fisi_core import CATEGORY_SHORT
from fisi_theme import C, CATEGORY_COLOR, GRADIENTS, lighten, mix
import ui

PRIORITY_COLOR = {"niedrig": C["muted"], "normal": C["cyan"], "hoch": C["yellow"],
                  "kritisch": C["red"]}
STATUS_TEXT = {fg.ST_OPEN: ("offen", C["cyan"]), fg.ST_RIGHT: ("erledigt", C["green"]),
               fg.ST_WRONG: ("mit Fehlern", C["red"]),
               fg.ST_DEFERRED: ("verschoben", C["yellow"])}
# Hinweis, wenn beim Einreichen noch nichts eingegeben ist (wie am PC)
EMPTY_HINT = {"bauteile": "Bitte setze zuerst Bauteile ein.",
              "bestellung": "Der Warenkorb ist noch leer.",
              "rack": "Bitte baue zuerst Geräte in den Schrank ein.",
              "formular": "Bitte fülle zuerst die Felder aus."}
AXIS_GRADIENT = {"fachkompetenz": (C["cyan"], "#6366F1"),
                 "zuverlaessigkeit": GRADIENTS["success"],
                 "kundenzufriedenheit": ("#F59E0B", C["pink"]),
                 "sicherheit": ("#DB2777", C["purple"])}


def cat_color(key):
    return CATEGORY_COLOR[fg.CAT_NAME[key]]


def euro(value):
    return "%s €" % "{:,.0f}".format(value).replace(",", ".")


def screen_list(controls, spacing=14):
    return ft.ListView(controls, spacing=spacing, expand=True,
                       padding=ft.Padding.only(left=16, right=16, top=4, bottom=24))


# ============================================================================
#  AVATAR UND GRUNDRISS
# ============================================================================

def avatar_shapes(appearance, size):
    """Formen aus fisi_game.avatar_shapes() als Flet-Canvas-Elemente."""
    scale = size / 100.0
    shapes = [cv.Circle(size / 2, size / 2, size / 2 - 1, ft.Paint(color=C["card_hi"]))]
    inner = 0.84
    offset = size * (1 - inner) / 2
    s = scale * inner
    for kind, (x1, y1, x2, y2), color in fg.avatar_shapes(appearance):
        ax, ay = offset + x1 * s, offset + size * 0.04 + y1 * s
        bx, by = offset + x2 * s, offset + size * 0.04 + y2 * s
        # Unterkante in den Kreis einpassen
        by = min(by, size * 0.93)
        paint = ft.Paint(color=color, style=ft.PaintingStyle.FILL)
        if kind == "oval":
            shapes.append(cv.Oval(ax, ay, bx - ax, by - ay, paint))
        elif kind == "rect":
            shapes.append(cv.Rect(ax, ay, bx - ax, by - ay, border_radius=6 * s,
                                  paint=paint))
        else:
            shapes.append(cv.Line(ax, ay, bx, by, ft.Paint(
                color=color, stroke_width=max(2, 3 * s), stroke_cap=ft.StrokeCap.ROUND)))
    return shapes


def avatar(appearance, size=96):
    return cv.Canvas(avatar_shapes(appearance, size), width=size, height=size)


class FloorPlan(ft.GestureDetector):
    """Das Buerogebaeude von oben (Zeichnung aus fisi_game.building_shapes).
    Treffer ueber die Raumflaechen (fisi_game.room_at), genau wie am PC."""

    MAX_HEIGHT = 300
    ROTATE = False

    def __init__(self, state, selected, on_room, player_pos=None):
        self.state = state
        self.selected = selected
        self.on_room = on_room
        self.player_pos = player_pos or fg.start_position()
        self.width_px = 340
        self.canvas = cv.Canvas(expand=True, height=240, on_resize=self._resized,
                                resize_interval=100)
        super().__init__(content=self.canvas, on_tap_down=self._tapped)
        self._draw()

    def _resized(self, event):
        self.width_px = event.width
        self._draw()
        self.canvas.update()

    def _layout(self):
        """Massstab und Verschiebung - gleicher Massstab in beide Richtungen."""
        width, height = fg.plan_size(self.ROTATE)
        margin = fg.PLAN_MARGIN
        scale = min(self.width_px / (width + 2 * margin),
                    self.MAX_HEIGHT / (height + 2 * margin))
        offset_x = (self.width_px - scale * width) / 2.0
        return scale, offset_x, margin * scale

    def _building(self, with_player=True):
        profile = self.state.profile
        player = (profile["name"], profile["aussehen"]) if with_player else None
        return fg.building_shapes(self.state.open_count_by_room(), self.selected, player,
                                  quests=set(self.state.quests()),
                                  player_pos=self.player_pos, rotate=self.ROTATE)

    def _draw(self):
        scale, ox, oy = self._layout()
        self.canvas.height = scale * (fg.plan_size(self.ROTATE)[1] + 2 * fg.PLAN_MARGIN)
        shapes = []
        for shape in self._building():
            shapes += self._shape(shape, scale, ox, oy)
        self.canvas.shapes = shapes

    @staticmethod
    def _shape(shape, scale, ox, oy):
        kind = shape["k"]

        def stroke(color, width):
            return ft.Paint(color=color, style=ft.PaintingStyle.STROKE,
                            stroke_width=max(1.0, width * scale),
                            stroke_cap=ft.StrokeCap.ROUND)

        if kind in ("rect", "oval"):
            x, y = ox + shape["x"] * scale, oy + shape["y"] * scale
            w, h = shape["w"] * scale, shape["h"] * scale
            paints = []
            if shape["fill"]:
                paints.append(ft.Paint(color=shape["fill"]))
            if shape["line"]:
                paints.append(stroke(shape["line"], shape["lw"]))
            if kind == "oval":
                return [cv.Oval(x, y, w, h, paint) for paint in paints]
            return [cv.Rect(x, y, w, h, border_radius=shape["r"] * scale, paint=paint)
                    for paint in paints]
        if kind == "line":
            x1, y1, x2, y2 = shape["pts"]
            return [cv.Line(ox + x1 * scale, oy + y1 * scale, ox + x2 * scale,
                            oy + y2 * scale, stroke(shape["color"], shape["lw"]))]
        if kind == "arc":
            return [cv.Arc(ox + shape["x"] * scale, oy + shape["y"] * scale,
                           shape["w"] * scale, shape["h"] * scale,
                           math.radians(shape["start"]), math.radians(shape["extent"]),
                           paint=stroke(shape["color"], shape["lw"]))]
        # Text: Namen der Kollegen nur, wenn genug Platz ist (Grossansicht)
        role = shape["role"]
        if role == "person" and scale < 18:
            return []
        size = 11 if role in ("raum", "badge", "player") else 9
        text = shape["text"]
        # Ohne Textmessung: Breite grob ueber die Zeichenzahl schaetzen
        if shape.get("maxw") and len(text) * size * 0.56 > shape["maxw"] * scale:
            text = shape["kurz"]
        x, y = ox + shape["x"] * scale, oy + shape["y"] * scale
        style = ft.TextStyle(size=size, color=shape["color"],
                             weight=ft.FontWeight.BOLD if role != "person" else None)
        result = []
        if shape.get("bg"):
            width = len(text) * size * 0.56 + 12
            height = size + 8
            left = x - 6 if shape["anchor"] == "w" else x - width / 2.0
            result.append(cv.Rect(left, y - height / 2.0, width, height,
                                  border_radius=height / 2.0,
                                  paint=ft.Paint(color=shape["bg"])))
            if shape.get("border"):
                result.append(cv.Rect(left, y - height / 2.0, width, height,
                                      border_radius=height / 2.0,
                                      paint=stroke(shape["border"], 1.0 / scale)))
        alignment = ft.Alignment.CENTER_LEFT if shape["anchor"] == "w" \
            else ft.Alignment.CENTER
        result.append(cv.Text(x, y, text, style=style, alignment=alignment))
        return result

    def _to_building(self, event):
        scale, ox, oy = self._layout()
        position = event.local_position
        return fg.from_view((position.x - ox) / scale, (position.y - oy) / scale,
                            self.ROTATE)

    def _tapped(self, event):
        item = fg.room_at(*self._to_building(event))
        if item:
            self.on_room(item["id"])


class WalkPlan(FloorPlan):
    """Grossansicht des Bueros (hochkant): Die Spielfigur laeuft per Tipp
    durch Flur und Tueren - Weg aus fisi_game.walk_path, genau wie am PC.
    Beim Laufen werden nur die Formen der Figur verschoben, nicht das ganze
    Gebaeude neu gezeichnet."""

    MAX_HEIGHT = 900
    ROTATE = True
    SPEED = 7.0            # Grundriss-Einheiten pro Sekunde
    FRAME = 0.04           # Sekunden pro Bild

    def __init__(self, state, player_pos, on_arrive):
        self.on_arrive = on_arrive
        self.player = []
        self.walk_id = 0
        super().__init__(state, None, lambda _room: None, player_pos)

    def _draw(self):
        scale, ox, oy = self._layout()
        self.canvas.height = scale * (fg.plan_size(True)[1] + 2 * fg.PLAN_MARGIN)
        shapes = []
        for shape in self._building(with_player=False):
            shapes += self._shape(shape, scale, ox, oy)
        profile = self.state.profile
        self.player = []
        for shape in fg.player_shapes(self.player_pos, (profile["name"],
                                                        profile["aussehen"]), True):
            self.player += self._shape(shape, scale, ox, oy)
        self.canvas.shapes = shapes + self.player

    def _shift(self, dx, dy):
        for shape in self.player:
            if isinstance(shape, cv.Line):
                shape.x1 += dx
                shape.x2 += dx
                shape.y1 += dy
                shape.y2 += dy
            else:
                shape.x += dx
                shape.y += dy

    def _tapped(self, event):
        x, y = self._to_building(event)
        person = fg.person_at(x, y)
        if person:
            route = fg.walk_path(self.player_pos, person["platz"], reach=fg.REACH)
        else:
            route = fg.walk_path(self.player_pos, (x, y))
        self.walk_id += 1
        self.page.run_task(self._walk, route, person, self.walk_id)

    async def _walk(self, route, person, walk_id):
        scale = self._layout()[0]
        for tx, ty in route:
            while walk_id == self.walk_id:
                x, y = self.player_pos
                dist = ((tx - x) ** 2 + (ty - y) ** 2) ** 0.5
                step = self.SPEED * self.FRAME
                if dist <= step:
                    new = (tx, ty)
                else:
                    new = (x + (tx - x) * step / dist, y + (ty - y) * step / dist)
                old_v = fg.to_view(x, y, True)
                new_v = fg.to_view(new[0], new[1], True)
                self._shift((new_v[0] - old_v[0]) * scale, (new_v[1] - old_v[1]) * scale)
                self.player_pos = new
                self.canvas.update()
                await asyncio.sleep(self.FRAME)
                if new == (tx, ty):
                    break
            if walk_id != self.walk_id:
                return        # neuer Tipp - dieser Weg ist abgebrochen
        self.on_arrive(self.player_pos, person or fg.person_near(*self.player_pos))


# ============================================================================
#  ZUORDNUNG
# ============================================================================

class MatchBoard(ft.Column):
    """Zuordnung zum Antippen: erst den Begriff, dann das Gegenstueck."""

    def __init__(self, task):
        super().__init__(spacing=8, tight=True,
                         horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self.task = task
        self.lefts = [left for left, _right in task["paare"]]
        self.rights = [right for _left, right in task["paare"]]
        random.shuffle(self.rights)
        self.answer = {}
        self.current = self.lefts[0]
        self.locked = False
        self.left_rows = {}
        for left in self.lefts:
            target = ft.Text("noch nicht zugeordnet", size=12, color=C["muted"])
            row = ft.Container(
                content=ft.Column([ft.Text(left, size=15, weight=ft.FontWeight.BOLD,
                                           color=C["text"]), target],
                                  spacing=2, tight=True),
                padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                border_radius=12, ink=True,
                on_click=lambda _e, value=left: self.pick_left(value))
            self.left_rows[left] = (row, target)
        self.right_pills = {}
        for right in self.rights:
            pill = ft.Container(
                content=ft.Text(right, size=13, weight=ft.FontWeight.BOLD),
                border_radius=18, padding=ft.Padding.symmetric(horizontal=14, vertical=9),
                ink=True, on_click=lambda _e, value=right: self.pick_right(value))
            self.right_pills[right] = pill
        self.controls = [
            ui.label("1. Begriff antippen"),
            *[row for row, _target in self.left_rows.values()],
            ui.label("2. Passendes Gegenstück antippen"),
            ft.Row(list(self.right_pills.values()), wrap=True, spacing=8, run_spacing=8),
        ]
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
                color = C["green"] if right else C["red"]
                row.bgcolor = mix(C["card"], color, 0.16)
                row.border = ft.Border.all(2, color)
                target.value = (value or "nicht zugeordnet") + (
                    "" if right else "  (richtig: %s)" % solution[left])
                target.color = C["text_soft"]
                continue
            active = left == self.current
            row.bgcolor = C["card_hi"] if active else C["card_alt"]
            row.border = ft.Border.all(2 if active else 1,
                                       C["purple"] if active else C["border"])
            target.value = ("passt zu: " + value) if value else "noch nicht zugeordnet"
            target.color = C["cyan"] if value else C["muted"]
        used = set(self.answer.values())
        for right, pill in self.right_pills.items():
            active = right in used
            pill.gradient = ui.gradient("primary") if active else None
            pill.bgcolor = None if active else C["card_alt"]
            pill.border = None if active else ft.Border.all(1, C["border"])
            pill.content.color = C["on_accent"] if active else C["text_dim"]

    def reveal(self):
        self.locked = True
        self.current = None
        self._paint()


class SlotBoard(ft.Column):
    """PC zusammensetzen zum Antippen: Steckplatz antippen, darunter klappen
    die passenden Bauteile auf. Kein Ziehen noetig."""

    def __init__(self, task, available, stock=None):
        super().__init__(spacing=8, tight=True,
                         horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self.task = task
        self.available = list(available)
        self.from_stock = {pid for pid in self.available if pid not in task.get("teile", [])
                           and pid in (stock or {})}
        self.answer = {}
        self.current = task["slots"][0]
        self.locked = False
        self.success = False
        self.slot_boxes = {}
        for slot in task["slots"]:
            box = ft.Container(border_radius=12, ink=True,
                               padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                               on_click=lambda _e, value=slot: self.pick_slot(value))
            self.slot_boxes[slot] = box
        rules = fg.build_rules_text(task)
        self.controls = ([ui.text("Vorgaben: " + rules, size=13, color=C["cyan"],
                                  weight=ft.FontWeight.BOLD)] if rules else []) + [
            ui.label("Steckplatz antippen, dann das Bauteil"),
            *self.slot_boxes.values()]
        self._paint()

    def pick_slot(self, slot):
        if not self.locked:
            self.current = None if slot == self.current else slot
            self._paint()

    def pick_part(self, part_id):
        if self.locked or self.current is None:
            return
        self.answer[self.current] = part_id
        missing = [slot for slot in self.task["slots"] if slot not in self.answer]
        self.current = missing[0] if missing else None
        self._paint()

    def clear_slot(self, _event=None):
        if not self.locked and self.current in self.answer:
            del self.answer[self.current]
            self._paint()

    def complete(self):
        return bool(self.answer)

    def _part_row(self, part_id, chosen):
        item = fg.part(part_id)
        head = [ui.text(item["name"], size=14, weight=ft.FontWeight.BOLD, expand=True)]
        if part_id in self.from_stock:
            head.append(ui.text("aus dem Lager", size=11, color=C["cyan"],
                                weight=ft.FontWeight.BOLD))
        return ft.Container(
            content=ft.Column([
                ft.Row(head, spacing=8),
                ui.text("%s · %s" % (fg.part_specs(item), euro(item["preis"])), size=12,
                        color=C["muted"]),
            ], spacing=2, tight=True),
            bgcolor=C["card_hi"] if chosen else C["card"],
            border=ft.Border.all(2 if chosen else 1, C["purple"] if chosen else C["border"]),
            border_radius=10, padding=ft.Padding.symmetric(horizontal=12, vertical=9),
            ink=True, on_click=lambda _e, value=part_id: self.pick_part(value))

    def _paint(self):
        optional = self.task.get("optional") or []
        for slot, box in self.slot_boxes.items():
            part_id = self.answer.get(slot)
            active = slot == self.current and not self.locked
            name = fg.slot_name(slot) + (" (optional)" if slot in optional else "")
            rows = [ui.text(name, size=15, weight=ft.FontWeight.BOLD),
                    ui.text(("eingesetzt: " + fg.part(part_id)["name"]) if part_id else "leer",
                            size=12, color=C["cyan"] if part_id else C["muted"])]
            if active:
                options = [pid for pid in self.available if fg.part(pid)["typ"] == slot]
                if not options:
                    rows.append(ui.text("Für diesen Steckplatz liegt nichts bereit.",
                                        size=12, color=C["muted"]))
                rows += [self._part_row(pid, pid == part_id) for pid in options]
                if part_id:
                    rows.append(ft.Row([ui.GradientButton(
                        "Steckplatz leeren", self.clear_slot, kind="ghost", height=36)]))
            box.content = ft.Column(rows, spacing=6, tight=True)
            if self.locked:
                color = C["green"] if self.success else C["red"]
                box.bgcolor = mix(C["card"], color, 0.12)
                box.border = ft.Border.all(2, color)
            else:
                box.bgcolor = C["card_hi"] if active else C["card_alt"]
                box.border = ft.Border.all(2 if active else 1,
                                           C["purple"] if active else C["border"])

    def reveal(self, right):
        self.locked = True
        self.success = right
        self.current = None
        self._paint()


class OrderBoard(ft.Column):
    """Bestellung: Stueckzahl je Angebot mit Minus und Plus, darunter die
    Summe und die laengste Lieferzeit."""

    def __init__(self, task):
        super().__init__(spacing=8, tight=True,
                         horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self.task = task
        self.cart = {}
        self.locked = False
        lines = fg.order_header(task)
        need = ft.Container(
            content=ft.Column([ui.label("Bedarf")] +
                              [ui.text(line, size=14, weight=ft.FontWeight.BOLD)
                               for line in lines[:-1]] +
                              [ui.text(lines[-1], size=13, color=C["cyan"],
                                       weight=ft.FontWeight.BOLD)],
                              spacing=4, tight=True),
            bgcolor=C["card_alt"], border=ft.Border.all(1, C["border"]), border_radius=12,
            padding=ft.Padding.symmetric(horizontal=14, vertical=10))
        self.rows = {}
        offers = []
        for offer in task["angebote"]:
            item = fg.part(offer["teil"])
            count = ft.Text("0", size=16, weight=ft.FontWeight.BOLD, color=C["muted"],
                            width=26, text_align=ft.TextAlign.CENTER)
            days = offer["lieferzeit"]
            row = ft.Container(
                content=ft.Column([
                    ft.Row([ui.text(item["name"], size=14, weight=ft.FontWeight.BOLD,
                                    expand=True),
                            ui.text(euro(offer["preis"]), size=14,
                                    weight=ft.FontWeight.BOLD)], spacing=8),
                    ui.text("%s · %s" % (fg.part_specs(item),
                                         fg.dealer(offer["haendler"])["name"]),
                            size=12, color=C["muted"]),
                    ft.Row([
                        ui.text("Lieferung %d Tag%s" % (days, "" if days == 1 else "e"),
                                size=12, color=C["text_dim"], expand=True),
                        self._step_button(ft.Icons.REMOVE, offer["id"], -1),
                        count,
                        self._step_button(ft.Icons.ADD, offer["id"], 1),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ], spacing=4, tight=True),
                border_radius=12, padding=ft.Padding.symmetric(horizontal=14, vertical=10))
            self.rows[offer["id"]] = (row, count)
            offers.append(row)
        self.summary = ui.text("", size=14, weight=ft.FontWeight.BOLD)
        self.controls = [need, ui.label("Angebote"), *offers, self.summary]
        self._paint()

    def _step_button(self, icon, offer_id, step):
        return ft.Container(
            content=ft.Icon(icon, size=18, color=C["text"]), width=36, height=36,
            border_radius=18, bgcolor=C["card"], ink=True,
            border=ft.Border.all(1, C["border"]), alignment=ft.Alignment.CENTER,
            on_click=lambda _e: self.change(offer_id, step))

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

    def _paint(self, right=None):
        for offer_id, (row, count) in self.rows.items():
            value = self.cart.get(offer_id, 0)
            count.value = str(value)
            count.color = C["cyan"] if value else C["muted"]
            border = C["purple"] if value else C["border"]
            if right is not None and value:
                border = C["green"] if right else C["red"]
            row.bgcolor = C["card_hi"] if value else C["card_alt"]
            row.border = ft.Border.all(2 if value else 1, border)
        text, too_much, too_late = fg.cart_summary(self.task, self.cart)
        self.summary.value = "Warenkorb: " + text
        self.summary.color = C["yellow"] if too_much or too_late else C["text_soft"]

    def reveal(self, right):
        self.locked = True
        self._paint(right)


class RackBoard(ft.Column):
    """Serverschrank bestuecken zum Antippen: Geraet antippen, dann die
    Hoeheneinheit im Schrank. Ein eingebautes Geraet antippen waehlt es zum
    Versetzen oder Ausbauen aus. Gleiche Regeln wie am PC (fg.rack_place)."""

    def __init__(self, task):
        super().__init__(spacing=8, tight=True,
                         horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self.task = task
        self.devices = task["geraete"]
        self.size = task["schrank"]["he"]
        self.unit = 30 if self.size <= 14 else 24
        self.answer = {}
        self.current = 0
        self.locked = False
        self.success = False
        lines = fg.rack_header(task)
        head = ft.Container(
            content=ft.Column([ui.label("Schrank"),
                               ui.text(lines[0], size=14, weight=ft.FontWeight.BOLD)] +
                              [ui.text(line, size=13, color=C["cyan"],
                                       weight=ft.FontWeight.BOLD) for line in lines[1:]],
                              spacing=4, tight=True),
            bgcolor=C["card_alt"], border=ft.Border.all(1, C["border"]), border_radius=12,
            padding=ft.Padding.symmetric(horizontal=14, vertical=10))
        self.device_rows = []
        for index, _device_id in enumerate(self.devices):
            row = ft.Container(border_radius=12, ink=True,
                               padding=ft.Padding.symmetric(horizontal=12, vertical=9),
                               on_click=lambda _e, value=index: self.pick_device(value))
            self.device_rows.append(row)
        self.cabinet = ft.Column(spacing=0, tight=True)
        self.remove_row = ft.Row([])
        self.summary = ui.text("", size=14, weight=ft.FontWeight.BOLD)
        self.controls = [head, ui.label("Gerät antippen"), *self.device_rows,
                         ui.label("Dann die Höheneinheit (HE 1 ist unten)"),
                         ft.Container(content=self.cabinet, bgcolor="#1E1A30",
                                      border=ft.Border.all(2, "#5B5480"), border_radius=10,
                                      padding=6),
                         self.remove_row, self.summary]
        self._paint()

    def pick_device(self, index):
        if not self.locked:
            self.current = None if index == self.current else index
            self._paint()

    def tap_unit(self, unit):
        if self.locked:
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

    def remove(self, _event=None):
        if not self.locked and self.current is not None:
            self.answer.pop(str(self.current), None)
            self._paint()

    def complete(self):
        return bool(self.answer)

    def _device_content(self, index):
        item = fg.rack_device(self.devices[index])
        bottom = self.answer.get(str(index))
        where = fg._he_text(bottom, item["he"]) if bottom else "liegt bereit"
        return ft.Row([
            ft.Container(width=4, height=34, border_radius=2,
                         bgcolor=fg.RACK_COLORS[item["typ"]]),
            ft.Column([
                ft.Row([ui.text(item["name"], size=14, weight=ft.FontWeight.BOLD,
                                expand=True),
                        ui.text(where, size=12, weight=ft.FontWeight.BOLD,
                                color=C["cyan"] if bottom else C["muted"])], spacing=8),
                ui.text(fg.rack_specs(item), size=12, color=C["muted"]),
            ], spacing=2, tight=True, expand=True),
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def _unit_row(self, unit, height, content=None, fill=None, border=None, on_click=None):
        return ft.Row([
            ft.Container(content=ui.text(str(unit), size=11, color=C["muted"]), width=24,
                         height=height, alignment=ft.Alignment.CENTER_RIGHT),
            ft.Container(content=content, height=height - 4, expand=True, bgcolor=fill,
                         border=border, border_radius=6, ink=on_click is not None,
                         padding=ft.Padding.symmetric(horizontal=10),
                         alignment=ft.Alignment.CENTER_LEFT, on_click=on_click),
        ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def _paint(self):
        for index, row in enumerate(self.device_rows):
            bottom = self.answer.get(str(index))
            active = index == self.current and not self.locked
            row.content = self._device_content(index)
            if self.locked and bottom:
                color = C["green"] if self.success else C["red"]
                row.bgcolor = mix(C["card"], color, 0.12)
                row.border = ft.Border.all(2, color)
            else:
                row.bgcolor = C["card_hi"] if active else C["card_alt"]
                row.border = ft.Border.all(2 if active else 1,
                                           C["purple"] if active else C["border"])
        rows = []
        unit = self.size
        while unit >= 1:
            occupant = fg.rack_occupant(self.task, self.answer, unit)
            if occupant is None:
                rows.append(self._unit_row(unit, self.unit, fill="#2A2442",
                                           on_click=lambda _e, u=unit: self.tap_unit(u)))
                unit -= 1
                continue
            item = fg.rack_device(self.devices[occupant])
            color = fg.RACK_COLORS[item["typ"]]
            selected = occupant == self.current and not self.locked
            bottom = self.answer[str(occupant)]
            rows.append(self._unit_row(
                unit if item["he"] == 1 else "%d–%d" % (bottom, unit), self.unit * item["he"],
                content=ui.text(item["name"], size=13, weight=ft.FontWeight.BOLD),
                fill=mix(C["card"], color, 0.55 if selected else 0.35),
                border=ft.Border.all(2 if selected else 1, color),
                on_click=lambda _e, u=unit: self.tap_unit(u)))
            unit = bottom - 1
        self.cabinet.controls = rows
        placed = self.current is not None and str(self.current) in self.answer
        self.remove_row.controls = [ui.GradientButton(
            "Gerät ausbauen", self.remove, kind="ghost", height=36)] \
            if placed and not self.locked else []
        text, over = fg.rack_summary(self.task, self.answer)
        self.summary.value = "Belegt: " + text
        self.summary.color = C["yellow"] if over else C["text_soft"]

    def reveal(self, right):
        self.locked = True
        self.success = right
        self.current = None
        self._paint()


class FormBoard(ft.Column):
    """Formular: Eingabefelder untereinander, bei IP-Plaenen ein Kasten je
    Teilnetz. Nach dem Einreichen gruen/rot mit dem richtigen Wert."""

    def __init__(self, task):
        super().__init__(spacing=8, tight=True,
                         horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self.task = task
        self.fields = fg.form_fields(task)
        self.inputs = {}
        self.choices = {}
        self.marks = {}
        self.locked = False
        head = ft.Container(
            content=ft.Column([ui.label("Ausgangsdaten")] +
                              [ui.text(line, size=14, weight=ft.FontWeight.BOLD)
                               for line in fg.form_given(task)], spacing=4, tight=True),
            bgcolor=C["card_alt"], border=ft.Border.all(1, C["border"]), border_radius=12,
            padding=ft.Padding.symmetric(horizontal=14, vertical=10))
        controls = [head]
        groups = []
        for field in self.fields:
            if not field["gruppe"]:
                controls.append(self._input(field))
            elif field["gruppe"] not in groups:
                groups.append(field["gruppe"])
        for group in groups:
            controls.append(ft.Container(
                content=ft.Column([ui.text(group, size=15, weight=ft.FontWeight.BOLD)] +
                                  [self._input(field) for field in self.fields
                                   if field["gruppe"] == group], spacing=8, tight=True,
                                  horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
                bgcolor=C["card_alt"], border=ft.Border.all(1, C["border"]),
                border_radius=12, padding=ft.Padding.symmetric(horizontal=12, vertical=10)))
        self.controls = controls

    def _input(self, field):
        mark = ui.text("", size=12, weight=ft.FontWeight.BOLD)
        self.marks[field["id"]] = mark
        if field["art"] == "wahl":
            pills = []
            for option in field["optionen"]:
                pill = ft.Container(
                    content=ft.Text(option, size=13, weight=ft.FontWeight.BOLD),
                    height=36, border_radius=18, alignment=ft.Alignment.CENTER,
                    padding=ft.Padding.symmetric(horizontal=16), ink=True,
                    on_click=lambda _e, f=field["id"], o=option: self._choose(f, o))
                pills.append((option, pill))
            self.choices[field["id"]] = {"value": "", "pills": pills}
            self._paint_choice(field["id"])
            return ft.Column([ui.text(field["label"], size=13, color=C["text_dim"]),
                              ft.Row([pill for _o, pill in pills], spacing=8), mark],
                             spacing=6, tight=True)
        whole = field["art"] in ("zahl", "praefix") and float(field["soll"]).is_integer()
        box = ui.entry(hint=field["einheit"] or None,
                       keyboard=ft.KeyboardType.NUMBER if whole and field["art"] == "zahl"
                       else ft.KeyboardType.TEXT)
        if field["einheit"]:
            box.suffix = ft.Text(field["einheit"], color=C["muted"])
            box.hint_text = None
        self.inputs[field["id"]] = box
        return ft.Column([ui.text(field["label"], size=13, color=C["text_dim"]), box, mark],
                         spacing=4, tight=True,
                         horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    def _choose(self, field_id, option):
        if not self.locked:
            self.choices[field_id]["value"] = option
            self._paint_choice(field_id)

    def _paint_choice(self, field_id):
        choice = self.choices[field_id]
        for option, pill in choice["pills"]:
            active = option == choice["value"]
            pill.gradient = ui.gradient("primary") if active else None
            pill.bgcolor = None if active else C["card"]
            pill.border = None if active else ft.Border.all(1, C["border"])
            pill.content.color = C["on_accent"] if active else C["text_dim"]

    @property
    def answer(self):
        result = {key: box.value or "" for key, box in self.inputs.items()}
        for key, choice in self.choices.items():
            result[key] = choice["value"]
        return result

    def complete(self):
        return any((value or "").strip() for value in self.answer.values())

    def reveal(self, right):
        self.locked = True
        check = fg.form_check(self.task, self.answer)
        for field in self.fields:
            ok = check[field["id"]]
            color = C["green"] if ok else C["red"]
            if field["id"] in self.inputs:
                box = self.inputs[field["id"]]
                box.border_color = color
                box.focused_border_color = color
                box.read_only = True
            mark = self.marks[field["id"]]
            mark.value = "richtig" if ok else "richtig wäre: %s" % field["anzeige"]
            mark.color = color


# ============================================================================
#  SEITE "SPIEL"
# ============================================================================

class GameScreen:
    """Seite "Spiel" der Handy-App (gleiche Schnittstelle wie Screen in
    main.py: crumbs, root, on_show)."""

    crumbs = ("PRAXIS", "SPIEL")

    def __init__(self, app):
        self.app = app
        self.db = app.db
        self.game = fg.Game(app.db, device="Handy")
        self.room = None
        self.draft = {}
        # Standort der Figur im Buero (nur waehrend die App laeuft)
        self.player_pos = fg.start_position()
        self.from_office = False
        self.office = None
        self.root = screen_list([])
        self.render()

    def toast(self, message, color=None):
        self.app.toast(message, color)

    def on_show(self):
        self.game.reload()
        self.render()

    def render(self):
        state = self.game.state
        if state.profile is None or self.draft.get("edit"):
            self.root.controls = self._profile_editor(state)
        else:
            self.root.controls = self._overview(state)

    # -- Spielfigur ---------------------------------------------------------

    def _profile_editor(self, state):
        profile = state.profile or {"name": "", "aussehen": dict(fg.DEFAULT_APPEARANCE)}
        look = fg.normalize_appearance(self.draft.get("aussehen") or profile["aussehen"])
        self.draft["aussehen"] = look
        preview = ft.Container(content=avatar(look, 120), alignment=ft.Alignment.CENTER)
        name = ui.entry(self.draft.get("name", profile["name"]),
                        hint="Wie heißt deine Figur?",
                        on_change=lambda e: self.draft.update(name=e.control.value))

        def changed(part, value):
            look[part] = value
            preview.content = avatar(look, 120)

        controls = [preview, ui.label("Name"), name]
        for part, caption in fg.APPEARANCE_LABELS:
            options = fg.APPEARANCE[part]
            keys = [key for key, _name in options]
            controls += [ui.label(caption),
                         ui.PillGroup(options, initial=keys.index(look[part]),
                                      on_change=lambda value, p=part: changed(p, value))]
        buttons = [ui.GradientButton("Los geht's" if state.profile is None else "Speichern",
                                     lambda _e: self._save_profile(name.value, look),
                                     expand=True)]
        if state.profile is not None:
            buttons.append(ui.GradientButton("Abbrechen", self._cancel_edit, kind="ghost"))

        result = []
        if state.profile is None:
            result.append(ui.Card("Willkommen im Spiel", [
                ui.text(fg.GAME["story"]["intro"], size=14, color=C["text_soft"]),
                ui.text("%s · Kunde: %s" % (fg.GAME["gebaeude"]["firma"],
                                            fg.GAME["gebaeude"]["kunde"]),
                        size=11, color=C["muted"]),
            ], accent=C["pink"]))
        result += [ui.Card("Deine Spielfigur", controls, accent=C["cyan"]),
                   ft.Row(buttons, spacing=10)]
        return result

    def _save_profile(self, name, look):
        try:
            self.game.set_profile(name, look)
        except ValueError as exc:
            self.toast(str(exc), C["yellow"])
            return
        self.draft = {}
        self.app.notify_progress()
        self.render()

    def _edit_profile(self, _event=None):
        self.draft = {"edit": True}
        self.render()

    def _cancel_edit(self, _event=None):
        self.draft = {}
        self.render()

    # -- Uebersicht ---------------------------------------------------------

    def _overview(self, state):
        levels = self.game.knowledge()
        goal = fg.GAME["balancing"]["gruendung"]
        founding = ui.GradientBar("Weg zum eigenen Unternehmen", C["green"], C["cyan"])
        founding.set(state.founding_progress() * 100, "Ziel %s" % euro(goal["startkapital"]))
        profile = ui.Card("Spielfigur", [
            ft.Row([
                avatar(state.profile["aussehen"], 84),
                ft.Column([
                    ui.text(state.profile["name"], size=22, weight=ft.FontWeight.BOLD),
                    ui.text(state.rank, size=14, color=C["cyan"], weight=ft.FontWeight.BOLD),
                    ui.text("Konto: %s · Gehalt: %s/Tag" % (euro(state.money),
                                                           euro(state.salary)),
                            size=12, color=C["text_dim"]),
                ], spacing=3, tight=True, expand=True),
            ], spacing=14),
            founding,
            ft.Row([ui.GradientButton("Figur bearbeiten", self._edit_profile, kind="ghost",
                                      height=38)]),
        ], accent=C["pink"], subtitle="Arbeitstag %d" % state.day)

        reputation_bars = []
        for key, name in fg.AXES:
            bar = ui.GradientBar(name, *AXIS_GRADIENT[key])
            bar.set(state.reputation[key], "%d / 100" % state.reputation[key])
            reputation_bars.append(bar)
        reputation = ui.Card("Reputation", reputation_bars, accent=C["purple"],
                             subtitle="Ansehen %d %%" % round(state.mean_reputation))

        plan = ui.Card("Grundriss", [
            FloorPlan(state, self.room, self._select_room, self.player_pos),
            ui.text("Raum antippen, um zu sehen, wer dort etwas braucht.", size=11,
                    color=C["muted"]),
            ui.GradientButton("Büro öffnen", self.open_office, kind="ghost", height=38),
        ], accent=C["cyan"])

        knowledge_bars = []
        for key in fg.CAT_ORDER:
            color = cat_color(key)
            bar = ui.GradientBar(CATEGORY_SHORT[fg.CAT_NAME[key]], color, lighten(color, 0.35))
            bar.set(levels[key], "%d %%" % levels[key])
            knowledge_bars.append(bar)
        knowledge_bars.append(ui.text("Aus deinem Lernfortschritt: Wer lernt, schafft "
                                      "schwierigere Tickets.", size=11, color=C["muted"]))
        wissen = ui.Card("Wissensstand", knowledge_bars, accent=C["green"])

        return [profile, self._ticket_card(state), plan, reputation, wissen]

    def _ticket_card(self, state):
        if self.room:
            item = fg.room(self.room)
            tickets = state.tickets_in_room(self.room)
            controls = [ui.text(item["text"], size=13, color=C["text_dim"])]
            if any(person.get("lagerist") for person in fg.GAME["kollegen"]
                   if person["raum"] == item["id"]):
                controls.append(self._warehouse(state))
            for person in fg.GAME["kollegen"]:
                if person["raum"] == item["id"]:
                    controls.append(ft.Column([
                        ui.text("%s · %s" % (person["name"], person["rolle"]), size=14,
                                weight=ft.FontWeight.BOLD),
                        ui.text(person["macke"], size=12, color=C["muted"]),
                    ], spacing=2, tight=True))
            controls.append(ft.Row([ui.GradientButton(
                "Alle Tickets zeigen", lambda _e: self._select_room(None), kind="ghost",
                height=38)]))
            title, accent, subtitle = item["name"], cat_color(item["cat"]), "Tickets hier"
        else:
            tickets = state.todays_tickets()
            controls = []
            title, accent = "Tickets heute", C["pink"]
            subtitle = "%d von %d bearbeitet" % (len(state.handled), len(tickets))

        if not tickets:
            waiting = len(state.waiting_for_delivery())
            text = ("In diesem Raum ist heute nichts zu tun." if self.room else
                    fg.GAME["story"]["alle_erledigt"] if state.all_done() else
                    "Heute stehen keine Tickets an. %s auf eine Lieferung."
                    % ("1 Auftrag wartet" if waiting == 1 else "%d Aufträge warten" % waiting)
                    if waiting else "Heute stehen keine Tickets an.")
            controls.append(ui.text(text, size=14, color=C["text_soft"]))
        for task, status in tickets:
            controls.append(self._ticket_row(task, status))
        if not self.room:
            end = ui.GradientButton("Arbeitstag beenden", self._end_day, kind="accent",
                                    expand=True)
            end.set_enabled(state.can_end_day())
            controls.append(ft.Row([end]))
        return ui.Card(title, controls, accent=accent, subtitle=subtitle)

    def _warehouse(self, state):
        """Lager: was unterwegs ist, was da ist und was ausgeliefert wurde."""
        store = state.warehouse()
        sections = [
            ("Unterwegs", ["%d × %s · %s · kommt an Arbeitstag %d" % (
                item["menge"], fg.part(item["teil"])["name"],
                fg.dealer(item["haendler"])["name"], item["ankunft"])
                for item in store["unterwegs"]]),
            ("Auf Lager", ["%d × %s" % (count, fg.part(part_id)["name"])
                           for part_id, count in store["bestand"]]),
            ("Ausgeliefert", ["%d × %s an %s" % (
                item["menge"], fg.part(item["teil"])["name"],
                fg.colleague(item["empfaenger"])["name"]) for item in store["ausgeliefert"]]),
        ]
        rows = []
        for title, lines in sections:
            if lines:
                rows.append(ui.label(title))
                rows += [ui.text(line, size=13, color=C["text_soft"]) for line in lines]
        if not rows:
            rows = [ui.text("Das Lager ist leer. Bestellte Ware taucht hier auf, sobald sie "
                            "unterwegs ist.", size=13, color=C["muted"])]
        return ft.Container(content=ft.Column(rows, spacing=4, tight=True),
                            bgcolor=C["card_alt"], border=ft.Border.all(1, C["border"]),
                            border_radius=12,
                            padding=ft.Padding.symmetric(horizontal=14, vertical=10))

    def _ticket_row(self, task, status):
        person = fg.colleague(task["auftraggeber"])
        status_text, status_color = STATUS_TEXT[status]
        return ft.Container(
            content=ft.Row([
                ft.Container(width=4, height=40, border_radius=2,
                             bgcolor=PRIORITY_COLOR[task["prioritaet"]]),
                ft.Column([
                    ui.text(task["titel"], size=14, weight=ft.FontWeight.BOLD),
                    ui.text("%s · %s" % (person["name"], fg.room(task["raum"])["name"]),
                            size=12, color=C["muted"]),
                ], spacing=2, tight=True, expand=True),
                ui.text(status_text, size=12, color=status_color, weight=ft.FontWeight.BOLD),
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=C["card_alt"], border=ft.Border.all(1, C["border"]), border_radius=12,
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            ink=status == fg.ST_OPEN,
            on_click=(lambda _e, t=task["id"]: self.open_ticket(t))
            if status == fg.ST_OPEN else None)

    def _select_room(self, room_id):
        self.room = None if room_id == self.room else room_id
        self.render()

    def _end_day(self, _event=None):
        try:
            payload = self.game.end_day()
        except ValueError as exc:
            self.toast(str(exc), C["yellow"])
            return
        self.room = None
        self.toast("Arbeitstag %d beendet. Gehalt: %s" % (payload["tag"],
                                                          euro(payload["gehalt"])),
                   C["green"])
        self.app.notify_progress()
        self.render()

    # -- Ticket als eigene Seite -------------------------------------------

    def open_ticket(self, task_id, from_office=False):
        self.from_office = from_office
        task = fg.task_by_id(task_id)
        person = fg.colleague(task["auftraggeber"])
        gaps = fg.requirement_gaps(task, self.game.knowledge())
        self.used_help = False
        self.answered = False
        self.task = task

        controls = [
            ui.text(task["titel"], size=19, weight=ft.FontWeight.BOLD),
            ui.text("Priorität %s · %s" % (task["prioritaet"],
                                           CATEGORY_SHORT[fg.CAT_NAME[task["cat"]]]),
                    size=12, color=PRIORITY_COLOR[task["prioritaet"]]),
        ]
        ticket = ui.Card("Ticket", [
            ui.text("%s · %s" % (person["name"], person["rolle"]), size=14,
                    weight=ft.FontWeight.BOLD),
            ui.text(task["ticket"], size=14, color=C["text_soft"]),
        ], accent=PRIORITY_COLOR[task["prioritaet"]])
        controls.append(ticket)

        if gaps:
            key = gaps[0][0]
            controls.append(ft.Container(
                content=ft.Column([
                    ui.text(fg.gap_warning(gaps), size=13, color=C["yellow"]),
                    ft.Row([ui.GradientButton(
                        "Karteikarten %s" % CATEGORY_SHORT[fg.CAT_NAME[key]],
                        lambda _e: self._open_cards(fg.CAT_NAME[key]), kind="ghost",
                        height=38)]),
                ], spacing=8, tight=True),
                bgcolor=mix(C["card"], C["yellow"], 0.12), border_radius=14, padding=14,
                border=ft.Border.all(1, mix(C["yellow"], C["card"], 0.35))))

        state = self.game.state
        self.available = state.available_parts(task)
        if task["typ"] == "auswahl":
            self.options = ui.OptionList()
            options = list(task["optionen"])
            random.shuffle(options)
            self.options.set_options(options)
        elif task["typ"] == "bauteile":
            self.options = SlotBoard(task, self.available, state.stock())
        elif task["typ"] == "bestellung":
            self.options = OrderBoard(task)
        elif task["typ"] == "rack":
            self.options = RackBoard(task)
        elif task["typ"] == "formular":
            self.options = FormBoard(task)
        else:
            self.options = MatchBoard(task)
        self.help_box = ft.Column(spacing=10, tight=True)
        self.result_box = ft.Column(spacing=10, tight=True)
        controls.append(ui.Card("Aufgabe", [
            ui.text(task["frage"], size=16, weight=ft.FontWeight.BOLD),
            self.options, self.help_box, self.result_box,
        ], accent=C["cyan"]))

        self.btn_submit = ui.GradientButton("Lösung einreichen", self._submit, expand=True)
        self.btn_help = ui.GradientButton("Hilfe", self._show_help, kind="ghost")
        self.btn_defer = ui.GradientButton("Verschieben", self._defer, kind="ghost",
                                           expand=True)
        self.buttons = ft.Column([
            ft.Row([self.btn_submit, self.btn_help], spacing=10),
            ft.Row([self.btn_defer]),
            ui.text("Ohne Hilfe gibt es %d %% Bonus."
                    % round(fg.GAME["balancing"]["bonus_ohne_hilfe"] * 100),
                    size=12, color=C["muted"]),
        ], spacing=10, tight=True)
        controls.append(self.buttons)
        self.app.push(self.crumbs, screen_list(controls))

    def _show_help(self, _event=None):
        if self.used_help or self.answered:
            return
        self.used_help = True
        self.btn_help.set_enabled(False)
        self.help_box.controls = [ft.Container(
            content=ft.Column([ui.label("Hilfe", C["cyan"]),
                               ui.text(self.task["hilfe"], size=14, color=C["text_soft"])],
                              spacing=6, tight=True),
            bgcolor=mix(C["card"], C["cyan"], 0.08), border_radius=12, padding=14,
            border=ft.Border.all(1, mix(C["cyan"], C["card"], 0.5)))]

    def _submit(self, _event=None):
        if self.answered:
            return
        task = self.task
        if task["typ"] == "auswahl":
            answer = self.options.get()
            if not answer:
                self.toast("Bitte wähle eine Antwort aus.", C["yellow"])
                return
        elif task["typ"] in fg.PROBLEM_TYPES:
            if not self.options.complete():
                self.toast(EMPTY_HINT[task["typ"]], C["yellow"])
                return
            answer = dict(self.options.answer)
        else:
            if not self.options.complete():
                self.toast("Bitte ordne zuerst alle Begriffe zu.", C["yellow"])
                return
            answer = dict(self.options.answer)
        try:
            payload = self.game.solve(task["id"], answer, self.used_help)
        except ValueError as exc:
            self.toast(str(exc), C["yellow"])
            return
        self.answered = True
        if task["typ"] == "auswahl":
            self.options.reveal(task["antwort"])
        elif task["typ"] in fg.PROBLEM_TYPES:
            self.options.reveal(payload["richtig"])
        else:
            self.options.reveal()
        self.app.notify_progress()

        color = C["green"] if payload["richtig"] else C["red"]
        result = [ft.Container(
            content=ft.Column([
                ui.text(fg.result_text(task, payload, self.available), size=14, color=color,
                        weight=ft.FontWeight.BOLD),
                ui.text(task["erklaerung"], size=14, color=C["text_soft"]),
            ], spacing=8, tight=True),
            bgcolor=mix(C["card"], color, 0.1), border_radius=12, padding=14,
            border=ft.Border.all(1, mix(color, C["card"], 0.4)))]
        links = fg.learn_links(task, limit=5)
        if links:
            result.append(ui.label("Passend dazu lernen", C["purple"]))
            for kind, _category, title, _detail in links:
                result.append(ft.Container(
                    content=ui.text("%s · %s" % (kind, title), size=13,
                                    color=C["text_soft"]),
                    bgcolor=C["card_alt"], border_radius=10,
                    padding=ft.Padding.symmetric(horizontal=12, vertical=10), ink=True,
                    on_click=lambda _e, k=kind, t=title: self._open_learn(k, t)))
        self.result_box.controls = result
        self.buttons.controls = [ft.Row([ui.GradientButton(
            "Zurück ins Büro" if self.from_office else "Zurück zur Übersicht",
            self._close, expand=True)])]

    def _defer(self, _event=None):
        if self.answered:
            return

        def confirmed():
            try:
                self.game.defer(self.task["id"])
            except ValueError as exc:
                self.toast(str(exc), C["yellow"])
            self.app.notify_progress()
            self._close()

        self.app.confirm("Ticket verschieben",
                         "Das Ticket auf einen späteren Arbeitstag verschieben? Das kostet "
                         "etwas Zuverlässigkeit.", confirmed)

    def _close(self, _event=None):
        page = self.app.page
        if self.from_office:
            # zurueck in die Bueroansicht (die liegt direkt unter dem Ticket)
            self.from_office = False
            while len(page.views) > 2:
                page.views.pop()
            self.game.reload()
            self.on_show()
            self._fill_office()
            page.update()
            return
        while len(page.views) > 1:
            page.views.pop()
        self.on_show()
        page.update()

    # -- Buero (Grossansicht) ---------------------------------------------

    def open_office(self, _event=None):
        self.game.reload()
        self.office = ft.Column(spacing=12, tight=True,
                                horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self._fill_office()
        self.app.push(("SPIEL", "BÜRO"), screen_list([self.office]))

    def _fill_office(self):
        state = self.game.state
        self.office_info = ft.Column(spacing=6, tight=True,
                                     horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self.office_plan = WalkPlan(state, self.player_pos, self._arrived)
        self.office.controls = [ui.Card("Büro", [self.office_plan, self.office_info],
                                        accent=C["cyan"],
                                        subtitle="Tippe auf eine Person oder einen Ort")]
        self._office_text(self.player_pos, fg.person_near(*self.player_pos))

    def _arrived(self, position, person):
        self.player_pos = position
        self._office_text(position, person)
        self.office_info.update()

    def _office_text(self, position, person):
        quests = self.game.state.quests()
        title, text = fg.office_message(position, person, quests, state=self.game.state)
        controls = [ui.text(title, size=15, weight=ft.FontWeight.BOLD),
                    ui.text(text, size=13, color=C["text_soft"])]
        if person and quests.get(person["id"]):
            task = quests[person["id"]][0]
            controls.append(ui.GradientButton(
                "Auftrag annehmen", lambda _e: self._accept(task["id"]), height=42))
        self.office_info.controls = controls

    def _accept(self, task_id):
        self.open_ticket(task_id, from_office=True)

    def _open_cards(self, category):
        self.app.screens["cards"].set_category(category)
        self.app.open("cards")

    def _open_learn(self, kind, title):
        self.app.open_search_hit(kind, title)
