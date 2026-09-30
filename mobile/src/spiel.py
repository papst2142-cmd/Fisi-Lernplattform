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
               fg.ST_DEFERRED: ("verschoben", C["yellow"]),
               fg.ST_WAITING: ("wartet auf Teil", C["purple"])}
# Hinweis, wenn beim Einreichen noch nichts eingegeben ist (wie am PC)
EMPTY_HINT = {"bauteile": "Bitte setze zuerst Bauteile ein.",
              "bestellung": "Der Warenkorb ist noch leer.",
              "rack": "Bitte baue zuerst Geräte in den Schrank ein.",
              "formular": "Bitte fülle zuerst die Felder aus.",
              "terminal": "Bitte führe zuerst alle Schritte im Terminal aus.",
              "diagnose": "Bitte wähle Ursache und Maßnahme.",
              "austausch": "Bitte wähle Ursache, Maßnahme, Ersatzteil und Ablauf.",
              "wartung": "Bitte prüfe und bewerte alle Prüfpunkte und wähle den Abschluss."}
# Grossansichten der Orte: Kopfzeile und "Zurueck ..." nach einem Auftrag
SITE_CRUMBS = {"buero": ("SPIEL", "BÜRO"), "kunde": ("SPIEL", "KUNDE"),
               "zuhause": ("SPIEL", "ZUHAUSE")}
FIRM_CRUMBS = ("SPIEL", "FIRMA")
JOURNEY_CRUMBS = ("SPIEL", "REISE")
JOURNEY_COLOR = {fg.JOURNEY_STORY: C["purple"], fg.JOURNEY_CAREER: C["accent"],
                 fg.JOURNEY_FIRM: C["green"]}
RETURN_LABEL = {"buero": "Zurück ins Büro", "kunde": "Zurück zum Kunden"}
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
    """Ein Ort von oben (Zeichnung aus fisi_game.building_shapes): Buero,
    Kundenort oder Wohnung. Treffer ueber die Raumflaechen (fisi_game.room_at),
    genau wie am PC."""

    MAX_HEIGHT = 300
    ROTATE = False

    def __init__(self, state, selected, on_room, player_pos=None, site=fg.SITE_OFFICE,
                 stagger=False):
        self.state = state
        self.stagger = stagger
        self.selected = selected
        self.on_room = on_room
        self.site = site
        self.site_data = fg.site_content(site, state)
        self.player_pos = player_pos or fg.start_position(self.site_data)
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
        width, height = fg.plan_size(self.ROTATE, self.site_data)
        margin = fg.PLAN_MARGIN
        scale = min(self.width_px / (width + 2 * margin),
                    self.MAX_HEIGHT / (height + 2 * margin))
        offset_x = (self.width_px - scale * width) / 2.0
        return scale, offset_x, margin * scale

    def _building(self, with_player=True):
        profile = self.state.profile
        player = (profile["name"], profile["aussehen"]) if with_player else None
        return fg.building_shapes(self.state.open_count_by_room(), self.selected, player,
                                  content=self.site_data,
                                  quests=set(self.state.quests(self.site)),
                                  player_pos=self.player_pos, rotate=self.ROTATE,
                                  stagger=self.stagger)

    def _draw(self):
        scale, ox, oy = self._layout()
        self.canvas.height = scale * (fg.plan_size(self.ROTATE, self.site_data)[1] +
                                      2 * fg.PLAN_MARGIN)
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
                            self.ROTATE, self.site_data)

    def _tapped(self, event):
        item = fg.room_at(*self._to_building(event), content=self.site_data)
        if item:
            self.on_room(item["id"])


class WalkPlan(FloorPlan):
    """Grossansicht eines Ortes (hochkant): Die Spielfigur laeuft per Tipp
    durch Flur und Tueren - Weg aus fisi_game.walk_path, genau wie am PC.
    Beim Laufen werden nur die Formen der Figur verschoben, nicht das ganze
    Gebaeude neu gezeichnet. on_tap(x, y) darf einen Tipp selbst behandeln
    (True zurueckgeben), z.B. beim Einrichten der Wohnung."""

    MAX_HEIGHT = 900
    ROTATE = True
    SPEED = 7.0            # Grundriss-Einheiten pro Sekunde
    FRAME = 0.04           # Sekunden pro Bild

    def __init__(self, state, player_pos, on_arrive, site=fg.SITE_OFFICE, on_tap=None,
                 overlay=None):
        self.on_arrive = on_arrive
        self.tap_hook = on_tap
        self.overlay = overlay or []
        self.player = []
        self.walk_id = 0
        super().__init__(state, None, lambda _room: None, player_pos, site)

    def _draw(self):
        scale, ox, oy = self._layout()
        self.canvas.height = scale * (fg.plan_size(True, self.site_data)[1] +
                                      2 * fg.PLAN_MARGIN)
        shapes = []
        height = self.site_data["gebaeude"]["hoehe"]
        for shape in self._building(with_player=False):
            shapes += self._shape(shape, scale, ox, oy)
        for shape in self.overlay:
            shapes += self._shape(fg._rotate_shape(shape, height), scale, ox, oy)
        profile = self.state.profile
        self.player = []
        for shape in fg.player_shapes(self.player_pos, (profile["name"],
                                                        profile["aussehen"]), True,
                                      self.site_data):
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
        if self.tap_hook and self.tap_hook(x, y):
            return
        person = fg.person_at(x, y, self.site_data)
        if person:
            route = fg.walk_path(self.player_pos, person["platz"], reach=fg.REACH,
                                 content=self.site_data)
        else:
            route = fg.walk_path(self.player_pos, (x, y), content=self.site_data)
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
                old_v = fg.to_view(x, y, True, self.site_data)
                new_v = fg.to_view(new[0], new[1], True, self.site_data)
                self._shift((new_v[0] - old_v[0]) * scale, (new_v[1] - old_v[1]) * scale)
                self.player_pos = new
                self.canvas.update()
                await asyncio.sleep(self.FRAME)
                if new == (tx, ty):
                    break
            if walk_id != self.walk_id:
                return        # neuer Tipp - dieser Weg ist abgebrochen
        self.on_arrive(self.player_pos,
                       person or fg.person_near(*self.player_pos, content=self.site_data))


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
            target.color = C["accent"] if value else C["muted"]
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
        self.controls = ([ui.text("Vorgaben: " + rules, size=13, color=C["accent"],
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
            head.append(ui.text("aus dem Lager", size=11, color=C["accent"],
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
                            size=12, color=C["accent"] if part_id else C["muted"])]
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
                              [ui.text(lines[-1], size=13, color=C["accent"],
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
            count.color = C["accent"] if value else C["muted"]
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
                              [ui.text(line, size=13, color=C["accent"],
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
        where = fg._he_text(bottom, item["he"]) if bottom else \
            fg.rack_source_text(self.task, index)
        return ft.Row([
            ft.Container(width=4, height=34, border_radius=2,
                         bgcolor=fg.RACK_COLORS[item["typ"]]),
            ft.Column([
                ft.Row([ui.text(item["name"], size=14, weight=ft.FontWeight.BOLD,
                                expand=True),
                        ui.text(where, size=12, weight=ft.FontWeight.BOLD,
                                color=C["accent"] if bottom else C["muted"])], spacing=8),
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
                              ft.Row([pill for _o, pill in pills], spacing=8, wrap=True,
                                     run_spacing=8), mark],
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


# Farben der Terminalzeilen (wie am PC)
TERMINAL_BG = C["sidebar"]
TERMINAL_COLOR = {"start": C["muted"], "ausgabe": C["text_soft"], "fehler": C["red"],
                  "gefahr": C["yellow"], "kommentar": C["muted"]}


class TerminalBoard(ft.Column):
    """Simuliertes Terminal: je Schritt einen Befehl antippen, die Ausgabe
    erscheint im Terminal. Nach einem falschen Befehl noch einmal versuchen."""

    def __init__(self, task):
        super().__init__(spacing=10, tight=True,
                         horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self.task = task
        self.attempts = [[] for _step in task["schritte"]]
        self.locked = False
        self.success = None
        self.step_label = ui.label("")
        self.goal_label = ui.text("", size=15, weight=ft.FontWeight.BOLD)
        self.lines = ft.Column(spacing=2, tight=True)
        self.screen = ft.Container(content=self.lines, bgcolor=TERMINAL_BG, border_radius=12,
                                   border=ft.Border.all(1, C["border"]),
                                   padding=ft.Padding.symmetric(horizontal=12, vertical=10))
        self.choices = ft.Column(spacing=8, tight=True,
                                 horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self.controls = [ft.Column([self.step_label, self.goal_label], spacing=2, tight=True),
                         self.screen, self.choices]
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

    def _line(self, role, value):
        if role in ("eingabe", "cursor"):
            return ft.Text(spans=[
                ft.TextSpan(self.task["prompt"] + " ",
                            ft.TextStyle(color=C["green"], font_family=ui.MONO, size=12)),
                ft.TextSpan(value, ft.TextStyle(
                    color=C["accent"] if role == "cursor" else C["text"],
                    font_family=ui.MONO, size=12))])
        return ft.Text(value, size=12, font_family=ui.MONO, color=TERMINAL_COLOR[role])

    def _paint(self):
        lines = [self._line(role, value)
                 for role, value in fg.terminal_log(self.task, self.attempts)]
        step = fg.terminal_current_step(self.task, self.attempts)
        if step is not None and not self.locked:
            lines.append(self._line("cursor", "_"))
        self.lines.controls = lines
        border = C["border"]
        if self.locked:
            border = C["green"] if self.success else C["red"]
        self.screen.border = ft.Border.all(2 if self.locked else 1, border)

        choices = []
        if step is None:
            self.step_label.value = "ALLE SCHRITTE ERLEDIGT"
            self.goal_label.value = self.task["schritte"][-1]["ziel"]
            if not self.locked:
                choices.append(ui.text("Das System ist eingerichtet. Reiche jetzt die "
                                       "Lösung ein.", size=13, color=C["green"]))
        else:
            self.step_label.value = fg.terminal_step_label(self.task, step).upper()
            self.goal_label.value = self.task["schritte"][step]["ziel"]
            if not self.locked:
                choices.append(ui.label("Befehl wählen"))
                for index, command in enumerate(self.task["schritte"][step]["befehle"]):
                    tried = index in self.attempts[step]
                    choices.append(ft.Container(
                        content=ft.Text(command["befehl"], size=13, font_family=ui.MONO,
                                        color=C["muted"] if tried else C["text_soft"]),
                        bgcolor=C["card"] if tried else C["card_alt"], border_radius=12,
                        border=ft.Border.all(1, C["border"]),
                        padding=ft.Padding.symmetric(horizontal=14, vertical=12),
                        ink=not tried,
                        on_click=None if tried else (lambda _e, value=index: self.run(value))))
        self.choices.controls = choices

    def reveal(self, right):
        self.locked = True
        self.success = right
        self._paint()


class DiagnoseBoard(ft.Column):
    """Fehlersuche: Pruefungen antippen, Ergebnisse im Notizblock sammeln,
    dann Ursache und Massnahme waehlen."""

    def __init__(self, task, available=None, stock=None, on_order=None):
        super().__init__(spacing=10, tight=True,
                         horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self.task = task
        self.done = []
        self.locked = False
        self.exchange = None
        controls = []
        spare = fg.spare_parts_text(task, available)
        if spare:
            controls.append(ui.text(spare, size=13, color=C["accent"],
                                    weight=ft.FontWeight.BOLD))
        controls.append(ui.label("Prüfungen"))
        self.check_rows = {}
        for item in task["pruefungen"]:
            caption = ft.Text(item["text"], size=14, color=C["text_soft"], expand=True)
            mark = ft.Text("", size=12, color=C["green"], weight=ft.FontWeight.BOLD)
            row = ft.Container(
                content=ft.Row([caption, mark], spacing=10,
                               vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=C["card_alt"], border_radius=12, border=ft.Border.all(1, C["border"]),
                padding=ft.Padding.symmetric(horizontal=14, vertical=11), ink=True,
                on_click=lambda _e, value=item["id"]: self.check(value))
            self.check_rows[item["id"]] = (row, caption, mark)
            controls.append(row)
        self.notes = ft.Column(spacing=4, tight=True)
        self.counter = ui.text("", size=12, color=C["muted"])
        controls += [ui.label("Notizblock"), ft.Container(
            content=self.notes, bgcolor=C["card_alt"], border_radius=12,
            border=ft.Border.all(1, C["border"]),
            padding=ft.Padding.symmetric(horizontal=14, vertical=10)), self.counter]
        self.cause = ui.OptionList()
        causes = list(task["ursachen"])
        random.shuffle(causes)
        self.cause.set_options(causes)
        self.measure = ui.OptionList()
        measures = list(task["massnahmen"])
        random.shuffle(measures)
        self.measure.set_options(measures)
        controls += [ui.label("Ursache"), self.cause, ui.label("Maßnahme"), self.measure]
        if task.get("austausch"):
            self.exchange = ExchangePanel(task, stock, on_order)
            controls.append(self.exchange)
        self.controls = controls
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
        for check_id, (row, caption, mark) in self.check_rows.items():
            done = check_id in self.done
            if self.locked and check_id in keys:
                row.border = ft.Border.all(2, C["green"])
                mark.value = "geprüft · wichtig" if done else "wichtig"
            else:
                mark.value = "geprüft" if done else ""
            row.bgcolor = C["card"] if done else C["card_alt"]
            caption.color = C["muted"] if done else C["text_soft"]
        notes = []
        if not self.done:
            notes.append(ui.text("Noch nichts geprüft. Die Ergebnisse erscheinen hier.",
                                 size=13, color=C["muted"]))
        for number, check_id in enumerate(self.done, start=1):
            item = fg.diagnosis_check(self.task, check_id)
            notes.append(ui.text("%d. %s" % (number, item["text"]), size=13,
                                 weight=ft.FontWeight.BOLD))
            notes.append(ui.text(item["ergebnis"], size=13, color=C["accent"]))
        self.notes.controls = notes
        self.counter.value = fg.diagnosis_counter(self.task, self.done)

    def reveal(self, right):
        self.locked = True
        self.cause.reveal(self.task["ursache"])
        self.measure.reveal(self.task["massnahme"])
        if self.exchange:
            self.exchange.reveal()
        self._paint()


def _pill(caption, on_click):
    return ft.Container(content=ft.Text(caption, size=13, weight=ft.FontWeight.BOLD),
                        height=34, border_radius=17, alignment=ft.Alignment.CENTER,
                        padding=ft.Padding.symmetric(horizontal=14), ink=True,
                        on_click=on_click)


def _paint_pill(pill, active):
    pill.gradient = ui.gradient("primary") if active else None
    pill.bgcolor = None if active else C["card"]
    pill.border = None if active else ft.Border.all(1, C["border"])
    pill.content.color = C["on_accent"] if active else C["text_dim"]


class ExchangePanel(ft.Column):
    """Austausch-Schritt einer Diagnose (wie am PC): Ersatzteil waehlen (aus
    dem Lager, sonst nachbestellen) und den Ablauf antippen."""

    def __init__(self, task, stock, on_order=None):
        super().__init__(spacing=8, tight=True,
                         horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self.task = task
        self.stock = dict(stock or {})
        self.part = None
        self.order = []
        self.locked = False
        self.solution = False
        kind = fg.spare_kinds().get(task["austausch"]["typ"], "Ersatzteil")
        controls = [ui.label("Austausch: %s" % kind),
                    ui.text("Wähle ein Teil aus dem Lager. Fehlt das passende, bestelle es "
                            "nach: Es kommt am nächsten Arbeitstag, bis dahin wartet das "
                            "Ticket.", size=12, color=C["text_dim"])]
        self.part_boxes = {}
        for item in fg.spare_catalog(task):
            count = self.stock.get(item["id"], 0)
            rows = [ft.Row([ui.text(item["name"], size=14, weight=ft.FontWeight.BOLD,
                                    expand=True),
                            ui.text("im Lager: %d" % count if count else "nicht im Lager",
                                    size=11, color=C["green"] if count else C["muted"],
                                    weight=ft.FontWeight.BOLD)], spacing=8),
                    ui.text("%s · %s" % (fg.spare_specs(item), euro(item["preis"])), size=12,
                            color=C["muted"])]
            if not count and on_order:
                rows.append(ft.Row([ui.GradientButton(
                    "Nachbestellen (%s)" % euro(item["preis"]),
                    lambda _e, pid=item["id"]: on_order(pid), kind="ghost", height=34)]))
            box = ft.Container(
                content=ft.Column(rows, spacing=4, tight=True), border_radius=10,
                padding=ft.Padding.symmetric(horizontal=12, vertical=9), ink=bool(count),
                on_click=(lambda _e, pid=item["id"]: self.pick(pid)) if count else None)
            self.part_boxes[item["id"]] = box
            controls.append(box)
        controls += [ui.label("Ablauf"),
                     ui.text("Tippe die Schritte in der richtigen Reihenfolge an. Nicht "
                             "jeder Schritt gehört dazu.", size=12, color=C["text_dim"])]
        self.step_boxes = {}
        for text in fg.exchange_steps(task):
            number = ft.Text("", size=14, color=C["accent"], weight=ft.FontWeight.BOLD,
                             width=22)
            box = ft.Container(
                content=ft.Row([number, ft.Text(text, size=14, color=C["text_soft"],
                                                expand=True)], spacing=6),
                border_radius=12, ink=True,
                padding=ft.Padding.symmetric(horizontal=12, vertical=11),
                on_click=lambda _e, value=text: self.step(value))
            self.step_boxes[text] = (box, number)
            controls.append(box)
        controls.append(ft.Row([ui.GradientButton("Ablauf zurücksetzen", self.reset,
                                                  kind="ghost", height=38)]))
        self.controls = controls
        self._paint()

    def pick(self, part_id):
        if not self.locked:
            self.part = part_id
            self._paint()

    def step(self, text):
        if not self.locked and text not in self.order:
            self.order.append(text)
            self._paint()

    def reset(self, _event=None):
        if not self.locked:
            self.order = []
            self._paint()

    def complete(self):
        return bool(self.part and self.order)

    def _paint(self):
        for part_id, box in self.part_boxes.items():
            chosen = part_id == self.part
            right = self.solution and not fg.spare_fits(self.task, part_id)
            box.bgcolor = C["card_hi"] if chosen else C["card_alt"]
            box.border = ft.Border.all(2 if chosen or right else 1,
                                       C["green"] if right else
                                       (C["purple"] if chosen else C["border"]))
        steps = self.task["austausch"]["schritte"]
        for text, (box, number) in self.step_boxes.items():
            index = self.order.index(text) + 1 if text in self.order else None
            if self.solution:
                index = steps.index(text) + 1 if text in steps else None
            number.value = str(index) if index else ""
            good = self.solution and text in steps
            box.bgcolor = C["card"] if index else C["card_alt"]
            box.border = ft.Border.all(2 if good else 1, C["green"] if good else C["border"])

    def reveal(self):
        self.locked = True
        self.solution = True
        self._paint()


class MaintenanceBoard(ft.Column):
    """Wartung (wie am PC): Pruefpunkt antippen, Messwert lesen, als „in
    Ordnung“ oder „auffällig“ bewerten, dann den Abschluss waehlen."""

    def __init__(self, task):
        super().__init__(spacing=10, tight=True,
                         horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self.task = task
        self.checked = []
        self.ratings = {}
        self.locked = False
        self.solution = False
        controls = [ui.label("Prüfpunkte")]
        self.rows = {}
        for item in task["pruefpunkte"]:
            result = ft.Text("Zum Prüfen antippen.", size=13, color=C["muted"])
            pills = {key: _pill(fg.RATING_TEXT[key],
                                lambda _e, pid=item["id"], k=key: self.rate(pid, k))
                     for key in (fg.RATING_OK, fg.RATING_ISSUE)}
            pill_row = ft.Row(list(pills.values()), spacing=8, visible=False)
            box = ft.Container(
                content=ft.Column([ft.Text(item["text"], size=14, color=C["text_soft"]),
                                   result, pill_row], spacing=6, tight=True),
                border_radius=12, ink=True,
                padding=ft.Padding.symmetric(horizontal=14, vertical=11),
                on_click=lambda _e, value=item["id"]: self.check(value))
            self.rows[item["id"]] = (box, result, pills, pill_row)
            controls.append(box)
        self.counter = ui.text("", size=12, color=C["muted"])
        self.closing = ui.OptionList()
        options = list(task["abschluss"])
        random.shuffle(options)
        self.closing.set_options(options)
        controls += [self.counter, ui.label("Abschluss für das Protokoll"), self.closing]
        self.controls = controls
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

    def _paint(self):
        for point_id, (box, result, pills, pill_row) in self.rows.items():
            item = fg.maintenance_point(self.task, point_id)
            done = point_id in self.checked
            pill_row.visible = done
            result.value = item["ergebnis"] if done else "Zum Prüfen antippen."
            result.color = C["accent"] if done else C["muted"]
            for key, pill in pills.items():
                _paint_pill(pill, self.ratings.get(point_id) == key)
            box.bgcolor = C["card"] if done else C["card_alt"]
            border = C["border"]
            if self.solution:
                wanted = fg.RATING_ISSUE if item.get("auffaellig") else fg.RATING_OK
                border = C["green"] if self.ratings.get(point_id) == wanted else C["red"]
                result.value = "%s · richtig: %s" % (item["ergebnis"], fg.RATING_TEXT[wanted])
            box.border = ft.Border.all(2 if self.solution else 1, border)
        self.counter.value = fg.maintenance_counter(self.task, self.ratings)

    def reveal(self, right):
        self.locked = True
        self.solution = True
        self.closing.reveal(self.task["abschluss_antwort"])
        for point_id in self.rows:
            if point_id not in self.checked:
                self.checked.append(point_id)
        self._paint()


# ============================================================================
#  SEITE "SPIEL"
# ============================================================================

MOOD_COLOR = {"gut": "green", "okay": "text_dim", "schlecht": "yellow", "kritisch": "pink"}


def stage_boxes(stage, color=None):
    """Drei Kaestchen fuer die Auspraegung einer Macke (ab 0.43)."""
    color = color or C["purple"]
    return ft.Row([ft.Container(width=16, height=9, border_radius=3,
                                bgcolor=color if number <= stage else C["card"],
                                border=ft.Border.all(1, color))
                   for number in range(1, 4)], spacing=3, tight=True)


def quirk_block(info):
    """Macke mit Stufe, Staerke und Schwaeche (ab 0.43, wie am PC)."""
    lines = fg.quirk_lines(info)
    if not lines:
        return []
    controls = [ft.Row([ui.text("Macke: %s" % lines["titel"], size=12,
                                weight=ft.FontWeight.BOLD),
                        stage_boxes(info["stufe"]),
                        ui.text(lines["stufe"], size=12, color=C["purple"])],
                       spacing=8, wrap=True,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ui.text(lines["zitat"], size=11, color=C["muted"])]
    if lines["plus"]:
        controls.append(ui.text("+ " + lines["plus"], size=11, color=C["green"]))
    if lines["minus"]:
        controls.append(ui.text("- " + lines["minus"], size=11, color=C["yellow"]))
    if lines["hinweis"]:
        controls.append(ui.text(lines["hinweis"], size=11, color=C["muted"]))
    return [ft.Column(controls, spacing=2, tight=True)]


def decision_box(decision, on_choose):
    """Entscheidung zum Personal (ab 0.43): Text und je Moeglichkeit ein
    Knopf mit der Folge darunter."""
    controls = [ui.label("Entscheidung", C["pink"]),
                ui.text(decision["titel"], size=15, weight=ft.FontWeight.BOLD),
                ui.text(decision["text"], size=13, color=C["text_soft"])]
    for option in decision["optionen"]:
        button = ui.GradientButton(option["label"],
                                   lambda _e, o=option["id"]: on_choose(decision["id"], o),
                                   kind="ghost", height=38)
        button.set_enabled(not option["problem"])
        controls.append(ft.Column([
            button, ui.text(option["problem"] or option["folge"], size=11,
                            color=C["yellow"] if option["problem"] else C["text_dim"])],
            spacing=4, tight=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH))
    return ft.Container(
        content=ft.Column(controls, spacing=6, tight=True,
                          horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
        bgcolor=mix(C["card"], C["pink"], 0.08), border_radius=12, padding=12,
        border=ft.Border.all(1, mix(C["pink"], C["card"], 0.45)))


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
        # Standort der Figur je Ort (nur waehrend die App laeuft)
        self.positions = {}
        self.notices = {}          # Ort -> (Ueberschrift, Text), einmal anzeigen
        self.place = None          # gewaehlter Kundenort
        self.site_key = None       # offene Grossansicht: buero, kunde, zuhause
        self.from_site = None      # Ticket kam aus einer Grossansicht
        self.office = None
        # Einrichten der Wohnung
        self.editing = False
        self.selected = None
        self.turn = 0
        self.problem = ""
        # Unterseite "Firma" (ab 0.33)
        self.firm_box = None
        self.firm_tab = "auftraege"
        self.offer_for = None        # Anfrage, die gerade kalkuliert wird (ab 0.34)
        self.markup = None
        self.offer_board = None
        self.offer_help = False
        self.assign_for = None       # Kundenticket, fuer das jemand gewaehlt wird
        self.team_for = None         # Projekt, dessen Team geaendert wird (ab 0.35)
        self.details_for = set()     # Projekte/Ausschreibungen mit aufgeklappten Details
        self.loan_amount = None      # frei gewaehlte Kreditsumme (ab 0.41)
        self.loan_term = 50          # gewaehlte Laufzeit
        self.plans_for = set()       # Kredite mit aufgeklapptem Tilgungsplan
        self.training_for = None
        self.training_cat = None     # gewaehlter Fachbereich der Weiterbildung (ab 0.38)
        self.topics_for = set()      # Mitarbeiter mit aufgeklappten Themen (ab 0.38)
        # Unterseite "Reise" (ab 0.39)
        self.journey_box = None
        self.journey_group = "alle"
        self.journey_page = 0
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

    @property
    def player_pos(self):
        return self.position(fg.SITE_OFFICE)

    def position(self, site):
        if site not in self.positions:
            self.positions[site] = fg.start_position(
                fg.site_content(site, self.game.state))
        return self.positions[site]

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
            ], accent=C["accent2"]))
        result += [ui.Card("Deine Spielfigur", controls, accent=C["accent"]),
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
        founding = ui.GradientBar("Weg zum eigenen Unternehmen", C["green"], C["accent"])
        founding.set(state.founding_progress() * 100, "Ziel %s" % euro(goal["startkapital"]))
        founding.visible = not state.firm
        job = "Geschäftsführung · %s" % state.firm["name"] if state.firm else state.rank
        hint = "" if state.firm else fg.rank_hint(state)
        money = ("Konto: %s · Gehalt: %s/Tag" % (euro(state.money), euro(state.salary))
                 if not state.firm else "Konto: %s" % euro(state.money))
        buttons = [ui.GradientButton("Figur bearbeiten", self._edit_profile, kind="ghost",
                                     height=38)]
        if state.firm or state.founding_ready():
            buttons.append(ui.GradientButton(
                "Firma öffnen" if state.firm else "Firma gründen", self.open_firm,
                kind="ghost" if state.firm else "primary", height=38))
        profile = ui.Card("Spielfigur", [
            ft.Row([
                avatar(state.profile["aussehen"], 84),
                ft.Column([
                    ui.text(state.profile["name"], size=22, weight=ft.FontWeight.BOLD),
                    ui.text(job, size=14, color=C["accent"], weight=ft.FontWeight.BOLD),
                    ui.text(hint, size=12, color=C["muted"], visible=bool(hint)),
                    ui.text(money, size=12, color=C["text_dim"]),
                    ui.text(fg.firm_summary(state) if state.firm else "", size=12,
                            color=C["text_dim"], visible=bool(state.firm)),
                    ui.text("Miete: %s/Tag" % euro(state.rent), size=12,
                            color=C["text_dim"], visible=bool(state.rent)),
                ], spacing=3, tight=True, expand=True),
            ], spacing=14),
            founding,
            ft.Row(buttons, wrap=True, spacing=8, run_spacing=8),
        ], accent=C["accent2"], subtitle="Arbeitstag %d" % state.day)

        reputation_bars = []
        for key, name in fg.AXES:
            bar = ui.GradientBar(name, *AXIS_GRADIENT[key])
            bar.set(state.reputation[key], "%d / 100" % state.reputation[key])
            reputation_bars.append(bar)
        reputation = ui.Card("Reputation", reputation_bars, accent=C["purple"],
                             subtitle="Ansehen %d %%" % round(state.mean_reputation))

        away = state.open_count_by_site()
        at_customer = sum(count for site, count in away.items() if site != fg.SITE_OFFICE)
        plan_controls = [
            FloorPlan(state, self.room, self._select_room, self.player_pos),
            ui.text("Raum antippen, um zu sehen, wer dort etwas braucht.", size=11,
                    color=C["muted"]),
            ft.Row([ui.GradientButton(label, lambda _e, k=key: self.open_site(k),
                                      kind="ghost", height=38)
                    for label, key in (("Büro öffnen", "buero"), ("Kunde öffnen", "kunde"),
                                       ("Zuhause öffnen", "zuhause"))] +
                   [ui.GradientButton("Firma öffnen", self.open_firm, kind="ghost", height=38),
                    ui.GradientButton("Reise öffnen", self.open_journey, kind="ghost",
                                      height=38)],
                   wrap=True, spacing=8, run_spacing=8),
        ]
        if at_customer:
            plan_controls.append(ui.text("%s beim Kunden" % (
                "1 Auftrag" if at_customer == 1 else "%d Aufträge" % at_customer),
                size=12, color=C["muted"]))
        plan = ui.Card("Grundriss", plan_controls, accent=C["accent"])

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
            people = fg.people_at_site(fg.SITE_OFFICE, state)
            if any(person.get("lagerist") for person in people
                   if person["raum"] == item["id"]):
                controls.append(self._warehouse(state))
            for person in people:
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
            scene = fg.morning_text(state.day, state=state)
            if scene:
                controls.append(ft.Container(
                    content=ft.Column([ui.label("Heute", C["purple"]),
                                       ui.text(scene, size=13, color=C["text_soft"])],
                                      spacing=4, tight=True),
                    bgcolor=mix(C["card"], C["purple"], 0.1), border_radius=12, padding=12,
                    border=ft.Border.all(1, mix(C["purple"], C["card"], 0.45))))
            if state.firm:
                # Ab 0.43: Entscheidungen zum Personal direkt hier
                for decision in state.open_decisions():
                    controls.append(decision_box(decision, self._decide_here))
            title, accent = "Tickets heute", C["accent2"]
            subtitle = "%d von %d bearbeitet" % (len(state.handled), len(tickets))

        if not tickets:
            waiting = len(state.waiting_for_delivery())
            text = ("In diesem Raum ist heute nichts zu tun." if self.room else
                    (fg.firm_orders_summary(state) or fg.FIRM_IDLE_TEXT) if state.firm else
                    fg.GAME["story"]["alle_erledigt"] if state.all_done() else
                    "Heute stehen keine Tickets an. %s auf eine Lieferung."
                    % ("1 Auftrag wartet" if waiting == 1 else "%d Aufträge warten" % waiting)
                    if waiting else "Heute stehen keine Tickets an.")
            controls.append(ui.text(text, size=14, color=C["text_soft"]))
            if not self.room and state.firm and state.firm_open_count():
                controls.append(ft.Row([ui.GradientButton("Aufträge öffnen", self.open_orders,
                                                          expand=True)]))
            if not self.room and state.firm and fg.projects_summary(state):
                controls += [ui.text(fg.projects_summary(state), size=14,
                                     color=C["text_soft"]),
                             ft.Row([ui.GradientButton("Projekte öffnen", self.open_projects,
                                                       expand=True)])]
            if not self.room and state.founding_ready():
                controls += [ui.text(fg.FOUNDING_TEASER, size=14, color=C["green"],
                                     weight=ft.FontWeight.BOLD),
                             ft.Row([ui.GradientButton("Firma gründen", self.open_firm,
                                                       expand=True)])]
        for task, status in tickets:
            controls.append(self._ticket_row(task, status))
        if not self.room:
            end = ui.GradientButton("Feierabend machen", self._end_day, kind="accent",
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
        where = fg.room(task["raum"])["name"]
        if fg.task_site(task) != fg.SITE_OFFICE:
            where = "beim Kunden · %s" % where
        lines = [ui.text(task["titel"], size=14, weight=ft.FontWeight.BOLD),
                 ui.text("%s · %s" % (person["name"], where), size=12, color=C["muted"])]
        if task.get("zwischenfall"):
            lines.insert(0, ui.label("Zwischenfall", C["red"]))
        return ft.Container(
            content=ft.Row([
                ft.Container(width=4, height=40, border_radius=2,
                             bgcolor=PRIORITY_COLOR[task["prioritaet"]]),
                ft.Column(lines, spacing=2, tight=True, expand=True),
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
        """Feierabend: Arbeitstag beenden und nach Hause gehen."""
        self.run_action("feierabend")

    def _decide_here(self, decision_id, choice):
        """Entscheidung zum Personal aus der Uebersicht (ab 0.43)."""
        try:
            self.game.decide(decision_id, choice)
        except ValueError as exc:
            self.toast(str(exc), C["yellow"])
            return
        self.app.notify_progress()
        self.render()

    # -- Ticket als eigene Seite -------------------------------------------

    def open_ticket(self, task_id, from_site=None):
        self.from_site = from_site
        task = self.game.state.prepared_task(fg.task_by_id(task_id))
        person = fg.colleague(task["auftraggeber"])
        gaps = fg.requirement_gaps(task, self.game.topic_knowledge())
        self.used_help = False
        self.answered = False
        self.task = task

        controls = [
            ui.text(task["titel"], size=19, weight=ft.FontWeight.BOLD),
            ui.text("%sPriorität %s · %s" % ("Zwischenfall · " if task.get("zwischenfall")
                                             else "", task["prioritaet"],
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
                        "Karteikarten zu %s" % fg.TOPIC_SHORT[key],
                        lambda _e: self._open_cards(fg.TOPIC_CAT[key], key), kind="ghost",
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
        elif task["typ"] == "terminal":
            self.options = TerminalBoard(task)
        elif task["typ"] == "diagnose":
            self.options = DiagnoseBoard(task, self.available, state.stock(),
                                         self._order_spare)
        elif task["typ"] == "wartung":
            self.options = MaintenanceBoard(task)
        else:
            self.options = MatchBoard(task)
        self.help_box = ft.Column(spacing=10, tight=True)
        self.result_box = ft.Column(spacing=10, tight=True)
        controls.append(ui.Card("Aufgabe", [
            ui.text(task["frage"], size=16, weight=ft.FontWeight.BOLD),
            self.options, self.help_box, self.result_box,
        ], accent=C["accent"]))

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
            content=ft.Column([ui.label("Hilfe", C["accent"]),
                               ui.text(self.task["hilfe"], size=14, color=C["text_soft"])],
                              spacing=6, tight=True),
            bgcolor=mix(C["card"], C["accent"], 0.08), border_radius=12, padding=14,
            border=ft.Border.all(1, mix(C["accent"], C["card"], 0.5)))]

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
                self.toast(EMPTY_HINT[getattr(self.options, "hint_key", task["typ"])],
                           C["yellow"])
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
            RETURN_LABEL.get(self.from_site, "Zurück zur Übersicht"),
            self._close, expand=True)])]

    def _order_spare(self, part_id):
        """Austausch: fehlendes Ersatzteil nachbestellen, das Ticket wartet."""
        if self.answered:
            return
        item = fg.part(part_id)
        days = fg.spare_delivery_days()

        def confirmed():
            try:
                self.game.order_spare(self.task["id"], part_id)
            except ValueError as exc:
                self.toast(str(exc), C["yellow"])
            self.app.notify_progress()
            self._close()

        self.app.confirm("Ersatzteil nachbestellen",
                         "%s für %s nachbestellen? Es kommt %s, bis dahin wartet das "
                         "Ticket." % (item["name"], euro(item["preis"]),
                                      "am nächsten Arbeitstag" if days == 1
                                      else "in %d Arbeitstagen" % days), confirmed)

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
        if self.from_site:
            # zurueck in die Grossansicht (die liegt direkt unter dem Ticket)
            self.from_site = None
            while len(page.views) > 2:
                page.views.pop()
            self.game.reload()
            self.on_show()
            self._fill_site()
            page.update()
            return
        while len(page.views) > 1:
            page.views.pop()
        self.on_show()
        page.update()

    # -- Grossansichten: Buero, Kunde, Zuhause -----------------------------

    def _site(self):
        if self.site_key == "zuhause":
            return fg.SITE_HOME
        if self.site_key == "kunde":
            places = [place["id"] for place in fg.open_places(self.game.state)]
            if self.place not in places:
                self.place = places[0]
            return self.place
        return fg.SITE_OFFICE

    def open_site(self, key, replace=False):
        """Oeffnet eine Grossansicht. replace: die offene Grossansicht ersetzen
        (z.B. vom Buero direkt nach Hause)."""
        self.game.reload()
        page = self.app.page
        if replace:
            while len(page.views) > 1:
                page.views.pop()
        self.site_key = key
        self.editing = False
        self.selected = None
        self.problem = ""
        self.office = ft.Column(spacing=12, tight=True,
                                horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self._fill_site()
        self.app.push(SITE_CRUMBS[key], screen_list([self.office]))

    def open_office(self, _event=None):
        self.open_site("buero")

    def _fill_site(self):
        state = self.game.state
        site = self._site()
        self.office_info = ft.Column(spacing=6, tight=True,
                                     horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        home = site == fg.SITE_HOME
        overlay = self._selection_overlay() if home else []
        self.office_plan = WalkPlan(state, self.position(site), self._arrived, site,
                                    on_tap=self._home_tap if home else None,
                                    overlay=overlay)
        controls = []
        if self.site_key == "kunde":
            places = fg.open_places(state)
            counts = state.open_count_by_site()
            if len(places) > 1:
                options = [(place["id"], "%s%s" % (fg.place_label(place, places), " (%d)" % counts[place["id"]]
                                                   if counts.get(place["id"]) else ""))
                           for place in places]
                keys = [key for key, _name in options]
                controls.append(ui.PillGroup(options, on_change=self._choose_place,
                                             initial=keys.index(site)))
            place = fg.customer_place(site)
            if place.get("text"):
                controls.append(ui.text(place["text"], size=12, color=C["text_dim"]))
        if home:
            money = [ui.text("Kontostand: %s" % euro(state.money), size=14,
                             weight=ft.FontWeight.BOLD,
                             color=C["text"] if state.money >= 0 else C["red"])]
            if state.rent:
                money.append(ui.text("Miete: %s pro Arbeitstag" % euro(state.rent), size=12,
                                     color=C["text_dim"]))
            controls.append(ft.Row([
                ft.Column(money, spacing=2, tight=True, expand=True),
                ui.GradientButton("Fertig" if self.editing else "Einrichten",
                                  self._toggle_edit, kind="primary" if self.editing
                                  else "ghost", height=38),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER))
            title, accent = fg.apartment(state.home_id)["name"], C["accent2"]
            subtitle = ("Möbel antippen, dann Stelle antippen" if self.editing
                        else "Tippe irgendwo hin")
        else:
            title = "Büro" if site == fg.SITE_OFFICE else fg.site_name(site)
            accent = C["accent"] if site == fg.SITE_OFFICE else C["blue"]
            subtitle = "Tippe auf eine Person oder einen Ort"
        controls.append(ui.Card(title, [self.office_plan, self.office_info], accent=accent,
                                subtitle=subtitle))
        if home and self.editing:
            controls += self._home_editor(state)
        self.office.controls = controls
        position = self.position(site)
        self._office_text(position, fg.person_near(*position,
                                                   content=self.office_plan.site_data))

    def _choose_place(self, place_id):
        self.place = place_id
        self._fill_site()

    def _arrived(self, position, person):
        self.positions[self._site()] = position
        self._office_text(position, person)
        self.office_info.update()

    def _office_text(self, position, person):
        state = self.game.state
        site = self._site()
        controls = []
        notice = self.notices.pop(site, None)
        if notice:
            controls.append(ft.Container(
                content=ft.Column([ui.text(notice[0], size=14, weight=ft.FontWeight.BOLD),
                                   ui.text(notice[1], size=13, color=C["text_soft"])],
                                  spacing=4, tight=True),
                bgcolor=mix(C["card"], C["purple"], 0.1), border_radius=12, padding=12,
                border=ft.Border.all(1, mix(C["purple"], C["card"], 0.45))))
        title, text, actions = fg.place_message(site, position, person, state,
                                                self.office_plan.site_data)
        controls += [ui.text(title, size=15, weight=ft.FontWeight.BOLD),
                     ui.text(text, size=13, color=C["text_soft"])]
        if self.problem and site == fg.SITE_HOME and self.editing:
            controls.append(ui.text(self.problem, size=13, color=C["yellow"],
                                    weight=ft.FontWeight.BOLD))
        for action, label in actions:
            controls.append(ui.GradientButton(
                label, lambda _e, a=action: self.run_action(a), height=42))
        self.office_info.controls = controls

    def run_action(self, action):
        """Knoepfe unter den Grossansichten (siehe fisi_game.place_message)."""
        if action.startswith("auftrag:"):
            self.open_ticket(action.split(":", 1)[1], from_site=self.site_key)
        elif action == fg.ACTION_PERSONAL:
            self.firm_tab = "mitarbeiter"
            self.open_firm()
        elif action == "feierabend":
            try:
                payload = self.game.end_day()
            except ValueError as exc:
                self.toast(str(exc), C["yellow"])
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
            self.open_site("zuhause", replace=True)
        elif action == "buero":
            state = self.game.state
            scene = fg.morning_text(state.day, state=state)
            self.positions.pop(fg.SITE_OFFICE, None)
            if scene:
                self.notices[fg.SITE_OFFICE] = ("Arbeitstag %d" % state.day, scene)
            self.open_site("buero", replace=True)
        elif action == "lernen":
            self.app.open("cards")
        elif action == "schlafen":
            self.notices[fg.SITE_HOME] = ("Gute Nacht", fg.sleep_text(self.game.state))
            self._fill_site()

    def _accept(self, task_id):
        self.open_ticket(task_id, from_site=self.site_key or "buero")

    # -- Reise des Spielers (ab 0.39) -----------------------------------------

    def open_journey(self, _event=None):
        self.game.reload()
        self.journey_page = 0
        self.journey_box = ft.Column(spacing=12, tight=True,
                                     horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self._fill_journey()
        self.app.push(JOURNEY_CRUMBS, screen_list([self.journey_box]))

    def _fill_journey(self):
        state = self.game.state
        stats = fg.journey_stats(state)
        tiles = [
            ("Diensttage", str(stats["diensttage"]), "Arbeitstage"),
            ("Tickets gelöst", str(stats["richtig"]),
             "von %d · %d %%" % (stats["tickets"], stats["quote"])),
            ("Zwischenfälle", str(stats["zwischenfaelle"]),
             "gemeistert von %d" % stats["zwischenfaelle_gesamt"]),
            ("Kundenprojekte", str(stats["kundenprojekte"]), "abgeschlossen"),
            ("Angebote", str(stats["angebote_gewonnen"]), "gewonnen von %d" % stats["angebote"]),
            ("Verdient", euro(stats["verdient"]), "alle Einnahmen"),
        ]
        grid = []
        for index in range(0, len(tiles), 2):
            grid.append(ft.Row([self._stat_tile(*tile) for tile in tiles[index:index + 2]],
                               spacing=8))
        controls = [ui.Card("Rückblick", grid, accent=C["accent2"],
                            subtitle="%s · Tag %d" % (state.profile["name"], state.day))]
        chart = ui.LineChart(height=160)
        chart.set_data(stats["tage"], stats["tage_richtig"], C["green"])
        controls.append(ui.Card("Tickets je Arbeitstag", [
            ui.text("Gelöste Tickets der letzten 30 Arbeitstage", size=11, color=C["muted"]),
            chart], accent=C["accent"]))
        chart = ui.LineChart(height=150)
        chart.set_data(stats["ansehen_tage"], stats["ansehen"], C["purple"], y_max=100)
        controls.append(ui.Card("Ansehen im Verlauf", [chart], accent=C["purple"],
                                subtitle="nach jedem Feierabend"))
        bars = []
        peak = max(stats["je_fachbereich"].values()) or 1
        for key in fg.CAT_ORDER:
            color = cat_color(key)
            bar = ui.GradientBar(CATEGORY_SHORT[fg.CAT_NAME[key]], color, lighten(color, 0.35))
            value = stats["je_fachbereich"][key]
            bar.set(100.0 * value / peak, str(value))
            bars.append(bar)
        bars.append(ui.text("Mitarbeiter eingestellt: %d · Tickets verschoben: %d · "
                            "Kundentickets deiner Leute: %d"
                            % (stats["mitarbeiter"], stats["verschoben"],
                               stats["kundentickets"]), size=12, color=C["text_dim"]))
        controls.append(ui.Card("Gelöst je Fachbereich", bars, accent=C["green"]))

        entries = fg.journey_filter(fg.journey(state), self.journey_group)
        entries.reverse()   # neueste zuerst
        keys = [key for key, _name in fg.JOURNEY_GROUPS]
        diary = [ui.PillGroup(fg.JOURNEY_GROUPS, initial=keys.index(self.journey_group),
                              on_change=self._journey_choose)]
        size = 12
        pages = max(1, -(-len(entries) // size))
        self.journey_page = max(0, min(self.journey_page, pages - 1))
        for entry in entries[self.journey_page * size:(self.journey_page + 1) * size]:
            color = JOURNEY_COLOR.get(entry["gruppe"], C["accent"])
            lines = [ui.text("Tag %d" % entry["tag"], size=11, color=C["muted"],
                             weight=ft.FontWeight.BOLD),
                     ui.text(entry["titel"], size=14, weight=ft.FontWeight.BOLD)]
            if entry["text"]:
                lines.append(ui.text(entry["text"], size=12, color=C["text_dim"]))
            diary.append(ft.Container(
                content=ft.Row([
                    ft.Container(width=4, height=40, border_radius=2, bgcolor=color),
                    ft.Column(lines, spacing=2, tight=True, expand=True),
                ], spacing=12),
                bgcolor=C["card_alt"], border=ft.Border.all(1, C["border"]), border_radius=12,
                padding=ft.Padding.symmetric(horizontal=12, vertical=8)))
        if not entries:
            diary.append(ui.text("Noch keine Einträge - dein erster Arbeitstag wartet.",
                                 size=14, color=C["text_soft"]))
        if pages > 1:
            diary.append(ft.Row([
                ui.GradientButton("Neuere", lambda _e: self._journey_turn(-1), kind="ghost",
                                  height=36),
                ui.text("Seite %d / %d" % (self.journey_page + 1, pages), size=13,
                        color=C["text_dim"]),
                ui.GradientButton("Ältere", lambda _e: self._journey_turn(1), kind="ghost",
                                  height=36),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
        controls.append(ui.Card("Tagebuch", diary, accent=C["purple"],
                                subtitle="%d Einträge · neueste zuerst" % len(entries)))
        self.journey_box.controls = controls

    @staticmethod
    def _stat_tile(title, value, detail):
        return ft.Container(
            content=ft.Column([
                ui.text(title.upper(), size=10, color=C["muted"], weight=ft.FontWeight.BOLD),
                ui.text(value, size=20, weight=ft.FontWeight.BOLD),
                ui.text(detail, size=11, color=C["text_dim"]),
            ], spacing=1, tight=True),
            bgcolor=C["card_alt"], border=ft.Border.all(1, C["border"]), border_radius=12,
            padding=ft.Padding.symmetric(horizontal=12, vertical=8), expand=True)

    def _journey_choose(self, group):
        self.journey_group = group
        self.journey_page = 0
        self._fill_journey()

    def _journey_turn(self, delta):
        self.journey_page += delta
        self._fill_journey()

    # -- Firma (ab 0.33) ------------------------------------------------------

    def open_firm(self, _event=None):
        self.game.reload()
        self.training_for = self.training_cat = None
        self.firm_box = ft.Column(spacing=12, tight=True,
                                  horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self._fill_firm()
        self.app.push(FIRM_CRUMBS, screen_list([self.firm_box]))

    def _fill_firm(self):
        state = self.game.state
        if state.firm:
            controls = [self._firm_head(state)]
        else:
            controls = [self._firm_founding(state)]
        tabs = fg.firm_tabs(state)
        keys = [key for key, _name in tabs]
        if self.firm_tab not in keys:
            self.firm_tab = keys[0]
        if len(tabs) > 1:
            controls.append(ui.PillGroup(tabs, initial=keys.index(self.firm_tab),
                                         on_change=self._firm_choose))
        controls += getattr(self, "_firm_" + self.firm_tab)(state)
        self.firm_box.controls = controls

    def _firm_choose(self, tab):
        self.firm_tab = tab
        self.training_for = self.training_cat = None
        self.offer_for = self.assign_for = self.team_for = None
        self._fill_firm()

    def open_projects(self, _event=None):
        """Aus der Spieluebersicht direkt zu Firma > Projekte."""
        self.firm_tab = "projekte"
        self.open_firm()

    def open_orders(self, _event=None):
        """Aus der Spieluebersicht direkt zu Firma > Auftraege."""
        self.firm_tab = "auftraege"
        self.open_firm()

    # -- Auftraege (ab 0.34) --------------------------------------------------

    def _firm_auftraege(self, state):
        rules = fg.offer_rules()
        offers = [ui.text("Wähle deinen Gewinnzuschlag und rechne das Angebot durch. Gegen "
                          "dich bieten Bitweiche und andere Firmen, wer genau, siehst du erst "
                          "im Ergebnis. Bist du am günstigsten und stimmt die Rechnung, "
                          "bekommst du den Auftrag. Offene Anfragen verfallen beim Feierabend.",
                          size=12, color=C["text_dim"])]
        for inquiry in state.inquiries():
            offers.append(self._inquiry_box(inquiry))
        tickets = state.customer_tickets()
        free = sum(1 for item in tickets if not item.get("an"))
        limits = fg.ticket_rules()
        rows = [ui.text("Verteile die Tickets an deine Leute oder übernimm selbst welche "
                        "(höchstens %d, mit deinem Wissensstand). Jeder Mitarbeiter schafft "
                        "%d Ticket pro Tag, die Chance hängt vom Wert im Thema des Tickets ab."
                        % (limits["spieler_max"], limits["mitarbeiter_max"]), size=12,
                        color=C["text_dim"])]
        levels = self.game.firm_levels()
        for ticket in tickets:
            rows.append(self._customer_ticket_box(state, ticket, levels))
        return [ui.Card("Kundenanfragen", offers, accent=C["pink"],
                        subtitle="Handlungskosten %d %%, USt %d %%"
                        % (rules["handlungskosten"], rules["ust"])),
                ui.Card("Kundentickets", rows, accent=C["accent"],
                        subtitle="%d von %d verteilt" % (len(tickets) - free, len(tickets)))]

    def _inquiry_box(self, inquiry):
        result = inquiry.get("ergebnis")
        parts = [ui.text(inquiry["kunde"]["name"], size=15, weight=ft.FontWeight.BOLD),
                 ui.text("%d × %s" % (inquiry["menge"], inquiry["artikel"]), size=13,
                         weight=ft.FontWeight.BOLD, color=C["pink"]),
                 ui.text(inquiry["text"], size=13, color=C["text_soft"]),
                 ui.text(fg.inquiry_status_text(inquiry), size=12,
                         color=C["text_dim"] if not result else
                         C["green"] if result.get("gewonnen") else C["red"])]
        if result:
            _head, text = fg.offer_result_text(result)
            parts.append(ui.text(text, size=12, color=C["text_soft"]))
            parts += [ui.text("• " + line, size=11, color=C["red"])
                      for line in result.get("probleme") or []]
        elif self.offer_for == inquiry["id"]:
            parts += self._offer_calc(inquiry)
        else:
            parts.append(ft.Row([ui.GradientButton(
                "Angebot kalkulieren", lambda _e, i=inquiry["id"]: self._calc(i),
                height=38, expand=True)]))
        return self._person_box(parts)

    def _offer_calc(self, inquiry, project=False):
        rules = fg.offer_rules()
        hints = fg.project_rules().get("hilfe") if project else rules.get("hilfe")
        values = rules["zuschlaege"]
        controls = [ui.label("Gewinnzuschlag"),
                    ui.PillGroup([(value, "%d %%" % value) for value in values],
                                 initial=values.index(self.markup) if self.markup in values
                                 else -1, on_change=self._pick_markup)]
        cancel = ui.GradientButton("Abbrechen", lambda _e: self._cancel_calc(), kind="ghost",
                                   height=38, expand=True)
        if self.markup is None:
            controls += [ui.text("Je höher der Zuschlag, desto mehr bleibt hängen, aber desto "
                                 "eher ist ein Mitbewerber günstiger.", size=12,
                                 color=C["muted"]),
                         ft.Row([cancel])]
            return controls
        old = self.offer_board.answer if self.offer_board is not None else {}
        self.offer_board = FormBoard(fg.project_task(inquiry, self.markup) if project
                                     else fg.inquiry_task(inquiry, self.markup))
        for key, value in old.items():
            if key in self.offer_board.inputs:
                self.offer_board.inputs[key].value = value
        controls.append(self.offer_board)
        if self.offer_help:
            controls.append(ft.Container(
                content=ft.Column([ui.text("• " + line, size=12, color=C["text_soft"])
                                   for line in hints or []], spacing=4,
                                  tight=True),
                bgcolor=mix(C["card_alt"], C["accent"], 0.08), border_radius=10, padding=10))
        controls += [
            ft.Row([ui.GradientButton("Angebot abschicken",
                                      lambda _e: self._send_offer(inquiry, project), height=40,
                                      expand=True)]),
            ft.Row([ui.GradientButton("Hilfe ausblenden" if self.offer_help else "Hilfe",
                                      lambda _e: self._toggle_offer_help(), kind="ghost",
                                      height=38, expand=True), cancel], spacing=8)]
        return controls

    def _calc(self, inquiry_id):
        self.offer_for = inquiry_id
        self.markup = None
        self.offer_board = None
        self.offer_help = False
        self._fill_firm()

    def _pick_markup(self, value):
        self.markup = value
        self._fill_firm()

    def _toggle_offer_help(self):
        self.offer_help = not self.offer_help
        self._fill_firm()

    def _cancel_calc(self):
        self.offer_for = None
        self.offer_board = None
        self._fill_firm()

    def _send_offer(self, inquiry, project=False):
        if self.offer_board is None or not self.offer_board.complete():
            self.toast("Bitte rechne das Angebot zuerst durch.", C["yellow"])
            return
        send = self.game.send_project_offer if project else self.game.send_offer
        try:
            payload = send(inquiry["id"], self.markup, self.offer_board.answer)
        except ValueError as exc:
            self.toast(str(exc), C["yellow"])
            return
        self.offer_for = None
        self.offer_board = None
        head, _text = fg.offer_result_text(payload)
        self.toast(head, C["green"] if payload["gewonnen"] else C["yellow"])
        self._firm_changed()

    def _customer_ticket_box(self, state, ticket, levels):
        parts = [ft.Row([ft.Container(width=6, height=38, border_radius=3,
                                      bgcolor=cat_color(ticket["cat"])),
                         ft.Column([ui.text(ticket["titel"], size=15,
                                            weight=ft.FontWeight.BOLD),
                                    ui.text(ticket["kunde"]["name"], size=12,
                                            weight=ft.FontWeight.BOLD,
                                            color=cat_color(ticket["cat"]))],
                                   spacing=2, tight=True, expand=True)], spacing=10),
                 ui.text(ticket["text"], size=13, color=C["text_soft"]),
                 ui.text(fg.ticket_line(ticket), size=12,
                         color=C["green"] if ticket.get("an") else C["text_dim"])]
        if ticket.get("an"):
            return self._person_box(parts)
        if self.assign_for != ticket["id"]:
            parts.append(ft.Row([ui.GradientButton(
                "Zuweisen", lambda _e, i=ticket["id"]: self._pick_ticket(i), height=38,
                expand=True)]))
            return self._person_box(parts)
        parts.append(ui.label("Wer übernimmt? (Wert in %s)"
                              % fg.TOPIC_SHORT.get(ticket.get("thema"), "")))
        for option in fg.ticket_candidates(state, ticket, levels):
            button = ui.GradientButton("%s · %d · Chance %d %%" % (
                option["name"], option["wert"], option["chance"]),
                lambda _e, a=option["an"]: self._delegate(ticket["id"], a), kind="ghost",
                height=38)
            button.set_enabled(not option["problem"])
            parts.append(button)
            if option["problem"]:
                parts.append(ui.text(option["problem"], size=11, color=C["muted"]))
        parts.append(ft.Row([ui.GradientButton("Abbrechen", lambda _e: self._pick_ticket(None),
                                               kind="ghost", height=38, expand=True)]))
        return self._person_box(parts)

    def _pick_ticket(self, ticket_id):
        self.assign_for = ticket_id
        self._fill_firm()

    def _delegate(self, ticket_id, person):
        try:
            self.game.delegate(ticket_id, person)
        except ValueError as exc:
            self.toast(str(exc), C["yellow"])
            return
        self.assign_for = None
        self._firm_changed()

    # -- Projekte (ab 0.35) -----------------------------------------------------

    def _firm_projekte(self, state):
        running = state.running_projects()
        levels = self.game.firm_levels()
        rows = []
        if not running:
            rows.append(ui.text("Gerade läuft kein Projekt. Gib unten ein Angebot für eine "
                                "Ausschreibung ab. Gewinnst du, stellst du hier das Team "
                                "zusammen.", size=14, color=C["text_soft"]))
        for project in running:
            rows.append(self._project_box(state, project, levels))
        rules = fg.project_rules()
        tenders = [ui.text("Rechne das Angebot wie bei den Anfragen: Projektarbeit (Punkte × %s) "
                           "plus Material, dazu Handlungskosten und dein Zuschlag. Bei "
                           "Projekten bieten meist zwei oder drei Firmen mit. Gewonnen gibt es "
                           "%d %% Anzahlung, den Rest bei Fertigstellung."
                           % (euro(rules["stundensatz"]), rules["anzahlung"]), size=12,
                           color=C["text_dim"])]
        problem = fg.project_offer_problem(state)
        items = state.tenders()
        if not items:
            tenders.append(ui.text("Gerade liegt keine Ausschreibung vor.", size=14,
                                   color=C["text_soft"]))
        for project in items:
            tenders.append(self._tender_box(state, project, problem))
        result = [ui.Card("Laufende Projekte", rows, accent=C["green"],
                          subtitle="%d von %d" % (len(running), state.project_limit())),
                  ui.Card("Ausschreibungen", tenders, accent=C["pink"],
                          subtitle="alle %d Arbeitstage eine neue" % rules["abstand_tage"])]
        done = state.done_projects()
        if done:
            lines = []
            for project in done[-6:][::-1]:
                last = project["tage"][-1] if project["tage"] else {}
                lines.append(ui.text("• %s · %s · fertig an Arbeitstag %d%s" % (
                    project["titel"], project["kunde_kurz"], project["fertig"],
                    " · %d %s zu spät" % (last["verzug"], "Tag" if last["verzug"] == 1
                                          else "Tage") if last.get("verzug") else
                    " · pünktlich"), size=12, color=C["text_soft"]))
            result.append(ui.Card("Abgeschlossene Projekte", lines, accent=C["accent"],
                                  subtitle="%d insgesamt" % len(done)))
        return result

    def _project_title(self, project):
        lines = [ui.text(project["titel"], size=15, weight=ft.FontWeight.BOLD),
                 ui.text(project["kunde_kurz"], size=12, weight=ft.FontWeight.BOLD,
                         color=cat_color(project["cat"]))]
        badge = fg.gross_badge_text(project)
        if badge:
            lines.append(ui.text(badge, size=12, weight=ft.FontWeight.BOLD, color=C["yellow"]))
        return ft.Row([ft.Container(width=6, height=38, border_radius=3,
                                    bgcolor=cat_color(project["cat"])),
                       ft.Column(lines, spacing=2, tight=True, expand=True)], spacing=10)

    def _project_details(self, project):
        key = project.get("projekt") or project["id"]
        if key not in self.details_for:
            return []
        template = fg.project_details(project)
        lines = []
        for head, body in (("Kunde", template["kunde"]),
                           ("Ausgangssituation", template["ausgangssituation"]),
                           ("Auftrag", template["auftrag"])):
            lines += [ui.label(head), ui.text(body, size=12, color=C["text_soft"])]
        lines.append(ui.label("Rahmenbedingungen"))
        lines += [ui.text("• " + line, size=12, color=C["text_soft"])
                  for line in template["rahmenbedingungen"]]
        if template["lernbar"]:
            lines.append(ui.text("Tipp: Unter „Projektarbeit“ im Lernbereich kannst du dieses "
                                 "Projekt durcharbeiten. Dann arbeitet dein Team %d %% "
                                 "schneller."
                                 % fg.project_rules().get("lernbonus", 0), size=11,
                                 color=C["muted"]))
        return [ft.Container(content=ft.Column(lines, spacing=4, tight=True),
                             bgcolor=mix(C["card_alt"], C["accent"], 0.08), border_radius=10,
                             padding=10)]

    def _details_button(self, key):
        return ui.GradientButton("Details ausblenden" if key in self.details_for else "Details",
                                 lambda _e, k=key: self._toggle_details(k), kind="ghost",
                                 height=38, expand=True)

    def _project_box(self, state, project, levels):
        pid = project["projekt"]
        share = project["stand"] / float(project["aufwand"]) * 100
        bar = ui.GradientBar("Fortschritt", C["green"], C["accent"])
        bar.set(share, "%d %%" % round(share))
        parts = [self._project_title(project), bar,
                 ui.text(fg.project_phase_text(project), size=12, color=C["text_soft"]),
                 ui.text(fg.project_status_text(state, project, levels), size=12,
                         color=C["red"] if state.day > project["frist_tag"] else C["text_dim"]),
                 ui.text(fg.project_team_text(state, project), size=13,
                         weight=ft.FontWeight.BOLD,
                         color=C["green"] if project["team"] else C["orange"])]
        editing = self.team_for == pid
        parts.append(ft.Row([ui.GradientButton(
            "Team fertig" if editing else "Team ändern",
            lambda _e: self._pick_team(None if editing else pid),
            kind="ghost" if editing else "primary", height=38, expand=True),
            self._details_button(pid)], spacing=8))
        if editing:
            parts.append(ui.label("Wer arbeitet mit? (antippen)"))
            for option in fg.project_candidates(state, project, levels):
                button = ui.GradientButton("%s · %d · %s Punkte am Tag" % (
                    option["name"], option["wert"], fg._num(option["punkte"])),
                    lambda _e, a=option["an"]: self._toggle_member(pid, a),
                    kind="success" if option["im_team"] else "ghost", height=38)
                button.set_enabled(option["im_team"] or not option["problem"])
                parts.append(button)
                if option["problem"]:
                    parts.append(ui.text(option["problem"], size=11, color=C["muted"]))
            parts.append(ui.text("Wer im Projekt ist, macht keine Kundentickets und keine "
                                 "Routineaufträge. Du selbst hast dann nur noch einen "
                                 "Ticketplatz.", size=11, color=C["muted"]))
        parts += self._project_details(project)
        return self._person_box(parts)

    def _tender_box(self, state, project, problem):
        result = project.get("ergebnis")
        parts = [self._project_title(project),
                 ui.text(project["text"], size=13, color=C["text_soft"]),
                 ui.text(fg.tender_line(project), size=12, weight=ft.FontWeight.BOLD,
                         color=C["text_dim"]),
                 ui.text(fg.tender_status_text(state, project), size=12,
                         color=C["text_dim"] if not result else
                         C["green"] if result.get("gewonnen") else C["red"])]
        if result:
            _head, text = fg.offer_result_text(result)
            parts.append(ui.text(text, size=12, color=C["text_soft"]))
            parts += [ui.text("• " + line, size=11, color=C["red"])
                      for line in result.get("probleme") or []]
            parts.append(ft.Row([self._details_button(project["id"])]))
        elif self.offer_for == project["id"]:
            parts += self._project_details(project)
            parts += self._offer_calc(project, project=True)
            return self._person_box(parts)
        else:
            button = ui.GradientButton("Angebot kalkulieren",
                                       lambda _e, i=project["id"]: self._calc(i), height=38,
                                       expand=True)
            button.set_enabled(not problem)
            parts.append(ft.Row([button, self._details_button(project["id"])], spacing=8))
            if problem:
                parts.append(ui.text(problem, size=11, color=C["muted"]))
        parts += self._project_details(project)
        return self._person_box(parts)

    def _pick_team(self, project_id):
        self.team_for = project_id
        self._fill_firm()

    def _toggle_details(self, key):
        if key in self.details_for:
            self.details_for.discard(key)
        else:
            self.details_for.add(key)
        self._fill_firm()

    def _toggle_member(self, project_id, person):
        try:
            self.game.toggle_project_member(project_id, person)
        except ValueError as exc:
            self.toast(str(exc), C["yellow"])
            return
        self._firm_changed()

    def _firm_changed(self):
        self.app.notify_progress()
        self.render()
        self._fill_firm()

    def _firm_head(self, state):
        stage = state.firm_stage()
        return ui.Card("Eigene Firma", [
            ui.text(state.firm["name"], size=22, weight=ft.FontWeight.BOLD),
            ui.text("%s · %s" % (fg.firm_rules()["gebaeude"]["name"], stage["name"]),
                    size=14, color=C["green"], weight=ft.FontWeight.BOLD),
            ui.text("Konto: %s" % euro(state.money), size=13,
                    color=C["text_dim"] if state.money >= 0 else C["red"]),
            ui.text(fg.firm_summary(state), size=13, color=C["text_dim"]),
        ], accent=C["green"], subtitle="seit Tag %d" % state.firm["tag"])

    def _firm_founding(self, state):
        missing = state.founding_missing()
        if missing:
            bar = ui.GradientBar("Weg zum eigenen Unternehmen", C["green"], C["accent"])
            bar.set(state.founding_progress() * 100,
                    "%d %%" % round(state.founding_progress() * 100))
            return ui.Card("Eigenes Unternehmen", [
                bar,
                ui.text("Noch nicht so weit: %s." % ", ".join(missing), size=14,
                        color=C["text_soft"]),
                ui.text("Sobald alles erfüllt ist, kannst du hier als Konkurrenz zu "
                        "Bitweiche deine eigene Firma gründen.", size=12, color=C["muted"]),
            ], accent=C["green"])
        name = ui.entry(fg.default_firm_name(state), hint="Wie heißt deine Firma?")
        return ui.Card("Eigenes Unternehmen", [
            ui.text(fg.founding_text(), size=14, color=C["text_soft"]),
            ui.label("Firmenname"), name,
            ft.Row([ui.GradientButton("Firma gründen", lambda _e: self._found(name.value),
                                      expand=True)]),
        ], accent=C["green"])

    def _found(self, name):
        cost = fg.firm_rules()["gruendung"]["kosten"]

        def confirmed():
            try:
                payload = self.game.found_firm(name)
            except ValueError as exc:
                self.toast(str(exc), C["yellow"])
                return
            self.positions.pop(fg.SITE_OFFICE, None)
            self.notices[fg.SITE_OFFICE] = ("Willkommen in deiner Firma",
                                            fg.founded_text(payload["name"]))
            self.firm_tab = "bewerbungen"
            self._firm_changed()

        self.app.confirm("Firma gründen", "„%s“ für %s gründen? Danach arbeitest du nicht "
                         "mehr bei Bitweiche." % ((name or "").strip(), euro(cost)), confirmed)

    def _person_card(self, state, item, applicant=False):
        role = item["rolle"]
        if item.get("herkunft") == "bitweiche" and "Bitweiche" not in role:
            role += " · früher bei Bitweiche"
        lines = [ui.text(item["name"], size=15, weight=ft.FontWeight.BOLD),
                 ui.text(role, size=12, weight=ft.FontWeight.BOLD,
                         color=C["pink"] if item.get("herkunft") == "bitweiche"
                         else C["accent"])]
        extra = [ui.text(fg.values_text(item["werte"]), size=12, color=C["text_dim"]),
                 ui.text(fg.strengths_text(item), size=12, color=C["text_dim"]),
                 ui.text(fg.staff_money_text(item), size=12, color=C["text_dim"])]
        if not applicant and "stimmung" in item:
            # Ab 0.43: Stimmung (Farbe nach Lage)
            extra.append(ui.text(fg.mood_text(item), size=12,
                                 color=C[MOOD_COLOR[fg.mood_level(item["stimmung"])]]))
        if item["id"] in self.topics_for:
            for key in fg.CAT_ORDER:
                extra.append(ft.Column([
                    ui.text("%s %d" % (CATEGORY_SHORT[fg.CAT_NAME[key]], item["werte"][key]),
                            size=12, weight=ft.FontWeight.BOLD,
                            color=CATEGORY_COLOR[fg.CAT_NAME[key]]),
                    ui.text(fg.topics_text(item["themen"], key), size=11,
                            color=C["text_dim"])], spacing=0, tight=True))
            limit = fg.cap_text(item["themen"]) if not applicant else ""
            if limit:
                extra.append(ui.text(limit, size=11, color=C["yellow"]))
        note = fg.training_text(state, item) if not applicant else \
            "Bewerbung liegt vor bis Arbeitstag %d" % item["bis_tag"]
        if note:
            extra.append(ui.text(note, size=12, color=C["yellow"] if not applicant
                                 else C["muted"]))
        if item.get("macke_info"):
            extra += quirk_block(item["macke_info"])
        elif item.get("macke"):
            extra.append(ui.text(item["macke"], size=11, color=C["muted"]))
        return [ft.Row([avatar(item["aussehen"], 56),
                        ft.Column(lines, spacing=2, tight=True, expand=True)],
                       spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER)] + extra

    def _person_box(self, controls):
        return ft.Container(
            content=ft.Column(controls, spacing=6, tight=True,
                              horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
            bgcolor=C["card_alt"], border=ft.Border.all(1, C["border"]), border_radius=12,
            padding=12)

    def _firm_mitarbeiter(self, state):
        staff = state.staff_list()
        controls = []
        if not staff:
            controls.append(ui.text("Noch arbeitest du allein. Unter „Bewerbungen“ findest "
                                    "du Leute für deine Firma.", size=14,
                                    color=C["text_soft"]))
        else:
            controls.append(ui.text("Heute: %s" % fg.firm_day_text(state.firm_day()),
                                    size=12, color=C["text_dim"]))
        # Ab 0.43: Urlaubsanfragen und Konflikte zuerst
        for decision in state.open_decisions():
            controls.append(decision_box(decision, self._decide))
        for item in staff:
            parts = self._person_card(state, item)
            parts.append(ft.Row([
                ui.GradientButton("Weiterbilden", lambda _e, i=item["id"]: self._pick_training(i),
                                  kind="ghost", height=36, expand=True),
                ui.GradientButton("Themen", lambda _e, i=item["id"]: self._toggle_topics(i),
                                  kind="success" if item["id"] in self.topics_for else "ghost",
                                  height=36, expand=True),
                ui.GradientButton("Entlassen", lambda _e, i=item: self._fire(i), kind="ghost",
                                  height=36, expand=True),
            ], spacing=8))
            coaching = fg.coaching_offer(state, item["id"])
            if coaching["macke"]:
                button = ui.GradientButton("Coaching (%s)" % euro(coaching["preis"]),
                                           lambda _e, i=item: self._coach(i), kind="ghost",
                                           height=36, expand=True)
                button.set_enabled(not coaching["problem"])
                parts.append(ft.Row([button]))
            if self.training_for == item["id"]:
                parts += self._training_choice(state, item)
            controls.append(self._person_box(parts))
        return [ui.Card("Mitarbeiter", controls, accent=C["accent"],
                        subtitle="%d von %d Plätzen" % (len(staff), state.capacity))]

    def _training_choice(self, state, item):
        """Weiterbildung (ab 0.38): erst den Fachbereich waehlen, dann ein Thema
        oder den ganzen Fachbereich."""
        rules = fg.firm_rules()["weiterbildung"]
        cat = self.training_cat
        if cat is None:
            controls = [ui.text("Weiterbildung in welchem Fachbereich?", size=13,
                                weight=ft.FontWeight.BOLD)]
            for key in fg.CAT_ORDER:
                controls.append(ui.GradientButton(
                    "%s %d" % (CATEGORY_SHORT[fg.CAT_NAME[key]], item["werte"][key]),
                    lambda _e, k=key: self._pick_training_cat(k), kind="ghost", height=36))
            return controls
        whole = rules["fachbereich"]
        controls = [ui.text("Weiterbildung %s: ein Thema oder der ganze Fachbereich?"
                            % CATEGORY_SHORT[fg.CAT_NAME[cat]], size=13,
                            weight=ft.FontWeight.BOLD)]
        offers = [fg.training_offer(state, item["id"], cat)]
        offers += [fg.training_offer(state, item["id"], topic) for topic in fg.CAT_TOPICS[cat]]
        for offer in offers:
            if offer["thema"]:
                caption = "%s %d (%s)" % (fg.TOPIC_SHORT[offer["thema"]],
                                          int(item["themen"][offer["thema"]]),
                                          euro(offer["preis"]))
            else:
                caption = "Ganzer Fachbereich (%s)" % euro(offer["preis"])
            target = offer["thema"] or cat
            button = ui.GradientButton(caption, lambda _e, t=target: self._train(item["id"], t),
                                       kind="ghost", height=36)
            button.set_enabled(not offer["problem"])
            controls.append(button)
        controls.append(ui.text(
            "Thema: +%d, dauert %d Arbeitstage. Ganzer Fachbereich: +%d auf alle Themen, "
            "dauert %d Arbeitstage. Höchstens %d, in der Zeit kein Umsatz. Durch Arbeit "
            "allein geht es nur bis %d."
            % (rules["plus"], offers[1]["tage"] if len(offers) > 1 else rules["tage"],
               whole["plus"], offers[0]["tage"], rules["max"], fg.learn_cap()), size=11,
            color=C["muted"]))
        problems = [offer["problem"] for offer in offers]
        if all(problems):
            controls.append(ui.text(problems[0], size=12, color=C["yellow"]))
        controls.append(ui.GradientButton("Anderer Fachbereich",
                                          lambda _e: self._pick_training_cat(None),
                                          kind="ghost", height=36))
        return controls

    def _pick_training(self, staff_id):
        self.training_for = None if self.training_for == staff_id else staff_id
        self.training_cat = None
        self._fill_firm()

    def _pick_training_cat(self, cat):
        self.training_cat = cat
        self._fill_firm()

    def _toggle_topics(self, staff_id):
        if staff_id in self.topics_for:
            self.topics_for.discard(staff_id)
        else:
            self.topics_for.add(staff_id)
        self._fill_firm()

    def _train(self, staff_id, target):
        try:
            self.game.train(staff_id, target)
        except ValueError as exc:
            self.toast(str(exc), C["yellow"])
            return
        self.training_for = self.training_cat = None
        self._firm_changed()

    def _decide(self, decision_id, choice):
        try:
            self.game.decide(decision_id, choice)
        except ValueError as exc:
            self.toast(str(exc), C["yellow"])
            return
        self._firm_changed()

    def _coach(self, item):
        offer = fg.coaching_offer(self.game.state, item["id"])
        if offer["problem"]:
            self.toast(offer["problem"], C["yellow"])
            return

        def confirmed():
            try:
                self.game.coach(item["id"])
            except ValueError as exc:
                self.toast(str(exc), C["yellow"])
                return
            self._firm_changed()

        self.app.confirm("Coaching", "Coaching für %s: %s, %d Arbeitstage ohne Umsatz. Danach "
                         "wirkt die Schwäche der Macke „%s“ eine Stufe schwächer." % (
                             item["name"], euro(offer["preis"]), offer["tage"],
                             item["macke_info"]["name"]), confirmed)

    def _fire(self, item):
        def confirmed():
            try:
                self.game.fire(item["id"])
            except ValueError as exc:
                self.toast(str(exc), C["yellow"])
                return
            self._firm_changed()

        self.app.confirm("Entlassen", "%s wirklich entlassen? Die Person bewirbt sich danach "
                         "nicht erneut." % item["name"], confirmed)

    def _firm_bewerbungen(self, state):
        found = fg.applicants(state)
        free = state.capacity - len(state.staff)
        rules = fg.firm_rules()["bewerbung"]
        controls = [ui.text("Freie Plätze: %d von %d. Gehalt und Umsatz richten sich nach den "
                            "Werten je Fachbereich." % (max(0, free), state.capacity),
                            size=12, color=C["text_dim"])]
        if not found:
            controls.append(ui.text("Gerade liegen keine Bewerbungen vor.", size=14,
                                    color=C["text_soft"]))
        for item in found:
            parts = self._person_card(state, item, applicant=True)
            button = ui.GradientButton("Einstellen", lambda _e, i=item["id"]: self._hire(i),
                                       height=38, expand=True)
            button.set_enabled(free > 0)
            parts.append(ft.Row([button]))
            controls.append(self._person_box(parts))
        return [ui.Card("Bewerbungen", controls, accent=C["pink"],
                        subtitle="alle %d Tage neue" % rules["abstand_tage"])]

    def _hire(self, applicant_id):
        try:
            self.game.hire(applicant_id)
        except ValueError as exc:
            self.toast(str(exc), C["yellow"])
            return
        self._firm_changed()

    def _firm_gebaeude(self, state):
        stage = state.firm_stage()
        rules = fg.firm_rules()["gebaeude"]
        result = [ui.Card(rules["name"], [
            ui.text("%s %s" % (rules["text"], stage["text"]), size=13, color=C["text_soft"]),
            ui.text("Stufe %d · %d Arbeitsplätze · Nebenkosten %s pro Arbeitstag"
                    % (stage["stufe"], state.capacity, euro(stage["nebenkosten"])),
                    size=12, color=C["text_dim"]),
            FloorPlan(state, None, lambda _room: None, stagger=True),
            ft.Row([ui.GradientButton("Büro öffnen", lambda _e: self.open_site("buero"),
                                      kind="ghost", height=38)]),
        ], accent=C["green"])]
        following = state.next_stage()
        if following is None:
            more = [ui.text("Der Gewerbehof ist fertig ausgebaut. Mehr Ausbau gibt es in "
                            "einem der nächsten Updates.", size=14, color=C["text_soft"])]
        else:
            button = ui.GradientButton("Ausbauen", lambda _e: self._expand(following),
                                       expand=True)
            button.set_enabled(state.money >= following["preis"])
            more = [ui.text("Stufe %d · %s: %s" % (following["stufe"], following["name"],
                                                  following["text"]), size=14,
                            color=C["text_soft"]),
                    ui.text("Kosten %s · danach %d Arbeitsplätze · Nebenkosten %s pro "
                            "Arbeitstag" % (euro(following["preis"]), len(following["plaetze"]),
                                            euro(following["nebenkosten"])),
                            size=12, color=C["text_dim"]),
                    ft.Row([button])]
        result.append(ui.Card("Ausbau", more, accent=C["accent"]))
        rooms = self._firm_rooms(state)
        if rooms:
            result.append(rooms)
        return result

    def _firm_rooms(self, state):
        """Sonderraeume (ab 0.36): je Raum Vorteil, Preis und Zustand."""
        rooms = fg.room_status(state)
        if not rooms:
            return None
        boxes = [ui.text("Frei wählbar, sobald die Ausbaustufe erreicht ist.", size=12,
                         color=C["text_dim"])]
        for item in rooms:
            parts = [ui.text(item["name"], size=15, weight=ft.FontWeight.BOLD),
                     ui.text(item["vorteil"], size=13, color=C["text_soft"]),
                     ui.text(fg.room_status_text(item), size=12, color=C["text_dim"])]
            if item["gebaut"]:
                parts.append(ui.text("ausgebaut", size=13, weight=ft.FontWeight.BOLD,
                                     color=C["green"]))
            elif state.firm["stufe"] < item["ab_stufe"]:
                parts.append(ui.text("ab Stufe %d" % item["ab_stufe"], size=13,
                                     weight=ft.FontWeight.BOLD, color=C["muted"]))
            else:
                button = ui.GradientButton("Ausbauen", lambda _e, i=item: self._build_room(i),
                                           height=38)
                button.set_enabled(not item["problem"])
                parts.append(ft.Row([button]))
            boxes.append(self._person_box(parts))
        return ui.Card("Sonderräume", boxes, accent=C["purple"])

    def _build_room(self, item):
        def confirmed():
            try:
                self.game.build_room(item["id"])
            except ValueError as exc:
                self.toast(str(exc), C["yellow"])
                return
            self._firm_changed()

        self.app.confirm("Ausbauen", "„%s“ für %s ausbauen? Die Nebenkosten steigen um %s "
                         "pro Arbeitstag." % (item["name"], euro(item["preis"]),
                                              euro(item["nebenkosten"])), confirmed)

    def _expand(self, stage):
        def confirmed():
            try:
                self.game.expand()
            except ValueError as exc:
                self.toast(str(exc), C["yellow"])
                return
            self.positions.pop(fg.SITE_OFFICE, None)
            self._firm_changed()

        self.app.confirm("Ausbauen", "„%s“ für %s bauen?" % (stage["name"],
                                                            euro(stage["preis"])), confirmed)

    def _firm_finanzen(self, state):
        labels, values = fg.balance_series(state)
        chart = ui.LineChart(height=180)
        chart.set_data(labels, [round(value / 1000.0, 1) for value in values], C["green"])
        result = [ui.Card("Kontostand", [
            ui.text(euro(state.money), size=24, weight=ft.FontWeight.BOLD,
                    color=C["text"] if state.money >= 0 else C["red"]),
            ui.text("Verlauf in Tausend Euro", size=11, color=C["muted"]),
            chart,
        ] + ([ui.text(fg.fixed_costs_text(state), size=12, color=C["text_dim"])]
             if state.firm else []), accent=C["accent"])]
        rows = []
        for item in fg.finance_days(state):
            detail = ["%s +%s" % (kind, euro(value)) for kind, value in item["ein"].items()]
            detail += ["%s -%s" % (kind, euro(value)) for kind, value in item["aus"].items()]
            rows.append(ft.Container(
                content=ft.Column([
                    ft.Row([ui.text("Arbeitstag %d" % item["tag"], size=14,
                                    weight=ft.FontWeight.BOLD, expand=True),
                            ui.text("%s%s" % ("+" if item["gewinn"] >= 0 else "-",
                                              euro(abs(item["gewinn"]))), size=14,
                                    weight=ft.FontWeight.BOLD,
                                    color=C["green"] if item["gewinn"] >= 0 else C["red"])]),
                    ui.text(" · ".join(detail), size=11, color=C["text_dim"]),
                ], spacing=2, tight=True),
                bgcolor=C["card_alt"], border=ft.Border.all(1, C["border"]), border_radius=12,
                padding=ft.Padding.symmetric(horizontal=12, vertical=8)))
        if not rows:
            rows.append(ui.text("Noch nichts gebucht.", size=14, color=C["text_soft"]))
        if state.loans:
            rows.insert(0, ui.text("Gewinn je Tag ohne Kredit und Tilgung, die Zinsen zählen "
                                   "als Kosten.", size=12, color=C["text_dim"]))
        result.append(ui.Card("Einnahmen und Ausgaben", rows, accent=C["green"],
                              subtitle="letzte 7 Arbeitstage"))
        lost = fg.lost_to(state)
        lines = [ft.Row([ui.text(name, size=13, weight=ft.FontWeight.BOLD, expand=True),
                         ui.text("1 Auftrag" if number == 1 else "%d Aufträge" % number,
                                 size=12, color=C["text_dim"])]) for name, number in lost]
        if not lines:
            lines.append(ui.text("Bisher hast du keinen Auftrag an einen Mitbewerber verloren.",
                                 size=14, color=C["text_soft"]))
        if state.firm:
            result.insert(2, self._tax_card(state))
        result.append(ui.Card("Gegen wen verloren", lines, accent=C["pink"],
                              subtitle="an Mitbewerber"))
        return result

    # -- Umsatzsteuer, Marketing, Zertifizierungen (ab 0.42) --------------------

    def _tax_card(self, state):
        item = fg.tax_status(state)
        parts = [ui.text("%s · %d %% · Voranmeldung alle %d Arbeitstage" % (
                     item["finanzamt"], item["satz"], item["faellig_tage"]), size=12,
                     color=C["text_dim"]),
                 ui.text("Steuerrücklage %s" % euro(item["ruecklage"]), size=20,
                         weight=ft.FontWeight.BOLD),
                 ui.text("Deine Einnahmen enthalten %d %% Umsatzsteuer. Die Vorsteuer aus "
                         "Nebenkosten, Material, Ausbau, Weiterbildung, Werbung und "
                         "Zertifizierungen wird abgezogen. Die Zahllast legt die Firma jeden "
                         "Feierabend automatisch zurück, sie gehört dem Finanzamt."
                         % item["satz"], size=13, color=C["text_soft"])]
        parts += [ui.text(line, size=12, color=C["text_dim"])
                  for line in fg.tax_status_lines(item)]
        for warning in (fg.tax_debt_text(state), fg.dunning_text(state)):
            if warning:
                parts.append(ui.text(warning, size=13, color=C["red"],
                                     weight=ft.FontWeight.BOLD))
        if item["letzte"]:
            parts.append(ui.label("Letzte Voranmeldungen"))
            parts += [ui.text("• " + fg.tax_filing_text(data), size=12, color=C["text_soft"])
                      for data in item["letzte"]]
        return ui.Card("Umsatzsteuer", parts, accent=C["orange"])

    def _firm_marketing(self, state):
        result = [ui.Card("Werbung", [
            ui.text(fg.marketing_summary_text(state), size=14, color=C["text_soft"]),
            ui.text("Jede Werbeform kannst du laufend buchen (Kosten pro Arbeitstag, "
                    "jederzeit kündbar) oder einmalig (sofort bezahlt, wirkt eine feste Zahl "
                    "von Arbeitstagen). Die Wirkung beginnt am nächsten Arbeitstag.", size=12,
                    color=C["text_dim"])], accent=C["pink"])]
        boxes = []
        for item in fg.ad_status(state):
            parts = [ui.text(item["name"], size=15, weight=ft.FontWeight.BOLD),
                     ui.text(item["text"], size=13, color=C["text_soft"]),
                     ui.text("Wirkung: " + item["wirkung"], size=12, color=C["text_soft"],
                             weight=ft.FontWeight.BOLD),
                     ui.text(fg.ad_price_text(item), size=12, color=C["text_dim"])]
            if item["stand"]:
                parts.append(ui.text(item["stand"], size=13, color=C["green"],
                                     weight=ft.FontWeight.BOLD))
            booking = item["buchung"]
            if booking and booking["art"] == fg.AD_RUNNING and booking.get("ende") is None:
                parts.append(ft.Row([ui.GradientButton(
                    "Kündigen", lambda _e, i=item: self._stop_ad(i), kind="ghost", height=38,
                    expand=True)]))
            elif not booking:
                buttons = []
                for mode, label in fg.AD_MODES:
                    offer = item["angebote"][mode]
                    button = ui.GradientButton(label, lambda _e, o=offer: self._book_ad(o),
                                               kind="primary" if mode == fg.AD_RUNNING
                                               else "ghost", height=38, expand=True)
                    button.set_enabled(not offer["problem"])
                    buttons.append(button)
                parts.append(ft.Row(buttons, spacing=8))
                problem = item["angebote"][fg.AD_ONCE]["problem"] or \
                    item["angebote"][fg.AD_RUNNING]["problem"]
                if problem:
                    parts.append(ui.text(problem, size=12, color=C["yellow"]))
            box = self._person_box(parts)
            if booking:
                box.border = ft.Border.all(1, C["green"])
            boxes.append(box)
        result.append(ui.Card("Werbeformen", boxes, accent=C["accent"]))
        return result

    def _book_ad(self, offer):
        def confirmed():
            try:
                self.game.book_ad(offer["id"], offer["art"])
            except ValueError as exc:
                self.toast(str(exc), C["yellow"])
                return
            self._firm_changed()

        self.app.confirm("Werbung buchen", fg.ad_confirm_text(offer), confirmed)

    def _stop_ad(self, item):
        def confirmed():
            try:
                self.game.stop_ad(item["id"])
            except ValueError as exc:
                self.toast(str(exc), C["yellow"])
                return
            self._firm_changed()

        self.app.confirm("Werbung kündigen", "„%s“ kündigen? Heute kostet sie noch, ab dem "
                         "nächsten Arbeitstag nicht mehr." % item["kurz"], confirmed)

    def _firm_zertifizierungen(self, state):
        rules = fg.cert_rules()
        result = [ui.Card("Zertifizierungen", [
            ui.text(fg.certs_summary_text(state), size=14, color=C["text_soft"]),
            ui.text("Zertifizierungen schalten große und öffentliche Aufträge frei (sie "
                    "erscheinen unter „Projekte“) und geben dir einen Preisvorteil gegen "
                    "Bitweiche und die anderen Mitbewerber. Alle Vorteile zusammen (Ruf, "
                    "Zertifizierungen, Werbung) höchstens %d %%. Es läuft immer nur eine "
                    "Zertifizierung gleichzeitig." % rules.get("vorteil_max", 10), size=12,
                    color=C["text_dim"])], accent=C["yellow"])]
        items = fg.cert_status(state)
        for kind, title, color in (("firma", "Qualität, Sicherheit und Datenschutz",
                                    C["cyan"]),
                                   ("fach", "Fachliche Zertifizierungen", C["green"])):
            boxes = []
            for item in [entry for entry in items if entry["art"] == kind]:
                parts = [ui.text(item["name"], size=15, weight=ft.FontWeight.BOLD),
                         ui.text(item["text"], size=13, color=C["text_soft"]),
                         ui.text("Kosten %s · Dauer %s" % (euro(item["preis"]),
                                                           fg.term_text(item["tage"])),
                                 size=12, color=C["text_dim"]),
                         ui.text("Vorteil: " + item["vorteil"], size=12,
                                 color=C["text_soft"], weight=ft.FontWeight.BOLD)]
                unlock = fg.cert_unlock_text(item)
                if unlock:
                    parts.append(ui.text(unlock, size=12, color=C["text_dim"]))
                if item["stand"] == "erworben":
                    parts.append(ui.text(item["stand_text"], size=13, color=C["green"],
                                         weight=ft.FontWeight.BOLD))
                elif item["stand"] == "laeuft":
                    parts.append(ui.text(item["stand_text"], size=13, color=C["cyan"],
                                         weight=ft.FontWeight.BOLD))
                else:
                    offer = item["angebot"]
                    button = ui.GradientButton("Beginnen",
                                               lambda _e, o=offer: self._start_cert(o),
                                               height=38)
                    button.set_enabled(not offer["problem"])
                    parts.append(ft.Row([button]))
                    if offer["problem"]:
                        parts.append(ui.text(offer["problem"], size=12, color=C["yellow"]))
                box = self._person_box(parts)
                if item["stand"] == "erworben":
                    box.border = ft.Border.all(1, C["green"])
                boxes.append(box)
            result.append(ui.Card(title, boxes, accent=color))
        return result

    def _start_cert(self, offer):
        def confirmed():
            try:
                self.game.start_cert(offer["id"])
            except ValueError as exc:
                self.toast(str(exc), C["yellow"])
                return
            self._firm_changed()

        self.app.confirm("Zertifizierung", fg.cert_confirm_text(offer), confirmed)

    # -- Kredite (ab 0.41) ----------------------------------------------------

    def _firm_kredite(self, state):
        rules = fg.loan_rules()
        check = fg.credit_check(state)
        bank = [ui.text("Deine Hausbank. Zinsen pro Jahr, ein Spieljahr hat %d Arbeitstage."
                        % rules["tage_pro_jahr"], size=12, color=C["text_dim"])]
        if check["ok"]:
            bank += [ui.text("Kreditrahmen %s" % euro(check["rahmen"]), size=20,
                             weight=ft.FontWeight.BOLD),
                     ui.text("davon frei %s" % euro(check["frei"]), size=14,
                             color=C["green"], weight=ft.FontWeight.BOLD),
                     ui.text("Der Rahmen richtet sich nach dem Umsatz der letzten %d "
                             "Arbeitstage und deinem Ansehen. Das Geld ist frei verwendbar, "
                             "die Raten werden jeden Feierabend automatisch abgebucht."
                             % rules["bonitaet"]["umsatz_tage"], size=13,
                             color=C["text_soft"]),
                     ui.text(fg.credit_frame_text(check), size=13, color=C["text_soft"],
                             weight=ft.FontWeight.BOLD)]
        else:
            bank.append(ui.text(fg.credit_wait_text(state, check), size=14,
                                color=C["text_soft"]))
        for point in check["punkte"]:
            color = C["green"] if point["ok"] else C["yellow"]
            bank.append(ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE if point["ok"] else ft.Icons.CANCEL, size=16,
                        color=color),
                ui.text(point["text"], size=13, color=color, expand=True,
                        weight=None if point["ok"] else ft.FontWeight.BOLD)],
                spacing=8, vertical_alignment=ft.CrossAxisAlignment.START))
        warning = fg.dunning_text(state)
        if warning:
            bank.append(ui.text(warning, size=13, color=C["red"], weight=ft.FontWeight.BOLD))
        result = [ui.Card(rules["bank"], bank, accent=C["cyan"]),
                  self._running_loans(state)]

        boxes = []
        for offer in fg.loan_packages(state):
            button = ui.GradientButton("Aufnehmen", lambda _e, o=offer: self._take_loan(o),
                                       height=38)
            button.set_enabled(not offer["problem"])
            boxes.append(self._person_box([
                ui.text(offer["name"], size=15, weight=ft.FontWeight.BOLD),
                ui.text(fg.loan_offer_text(offer), size=12, color=C["text_dim"]),
                ui.text(offer["text"], size=13, color=C["text_soft"])]
                + ([ui.text(offer["problem"], size=12, color=C["yellow"])]
                   if offer["problem"] and check["ok"] else [])
                + [ft.Row([button])]))
        result.append(ui.Card("Kreditpakete", boxes, accent=C["green"],
                              subtitle="feste Angebote"))

        _low, _high, step = fg.free_loan_limits(state)
        if self.loan_amount is None:
            self.loan_amount = rules["frei"]["start"]
        amount = fg.clamp_loan_amount(state, self.loan_amount)
        terms = [(str(term), "%d Tage" % term) for term in fg.loan_terms()]
        keys = [key for key, _name in terms]
        offer = fg.loan_offer(state, amount, self.loan_term, check=check)
        button = ui.GradientButton("Aufnehmen", lambda _e: self._take_loan(offer),
                                   expand=True)
        button.set_enabled(not offer["problem"])
        free = [ui.text("Summe und Laufzeit selbst wählen, bis zum freien Kreditrahmen.",
                        size=12, color=C["text_dim"]),
                ui.text(euro(amount), size=22, weight=ft.FontWeight.BOLD),
                ft.Row([ui.GradientButton(label, lambda _e, d=delta: self._loan_step(d),
                                          kind="ghost", height=38, expand=True)
                        for label, delta in (("−5.000", -5 * step), ("−1.000", -step),
                                             ("+1.000", step), ("+5.000", 5 * step))],
                       spacing=6),
                ui.label("Laufzeit"),
                ui.PillGroup(terms, initial=keys.index(str(self.loan_term))
                             if str(self.loan_term) in keys else 0,
                             on_change=self._loan_choose_term),
                ui.text(fg.loan_offer_text(offer), size=14, color=C["text_soft"])]
        if offer["problem"]:
            free.append(ui.text(offer["problem"], size=13, color=C["yellow"]))
        free.append(ft.Row([button]))
        result.append(ui.Card("Freie Kredithöhe", free, accent=C["accent"]))

        done = state.done_loans()
        if done:
            result.append(ui.Card("Abgeschlossene Kredite", [
                ui.text("%s über %s · %s an Arbeitstag %d · Zinsen %s" % (
                    loan["name"], euro(loan["summe"]),
                    "abgelöst" if loan["ende_art"] == "abgeloest" else "zurückgezahlt",
                    loan["ende"], euro(loan["bezahlt_zins"])), size=12, color=C["text_dim"])
                for loan in done], accent=C["muted"]))
        return result

    def _running_loans(self, state):
        loans = [fg.loan_status(state, loan) for loan in state.running_loans()]
        if not loans:
            return ui.Card("Laufende Kredite", [ui.text("Du hast gerade keinen Kredit.",
                                                        size=14, color=C["text_soft"])],
                           accent=C["orange"])
        boxes = [ui.text("Restschuld %s · Raten %s pro Arbeitstag" % (
            euro(sum(item["rest"] for item in loans)), euro(state.loan_rates())), size=13,
            color=C["text_soft"], weight=ft.FontWeight.BOLD)]
        for item in loans:
            parts = [ui.text(item["name"], size=15, weight=ft.FontWeight.BOLD),
                     ui.text("aufgenommen an Arbeitstag %d" % item["tag"], size=12,
                             color=C["muted"])]
            parts += [ui.text(line, size=12, color=C["red"] if line.startswith("Geplatzte")
                              else C["text_dim"]) for line in fg.loan_status_lines(item)]
            opened = item["id"] in self.plans_for
            if opened:
                parts.append(self._loan_plan(item))
            repay = ui.GradientButton("Ablösen", lambda _e, i=item: self._repay_loan(i),
                                      kind="ghost", height=38, expand=True)
            repay.set_enabled(state.money >= item["abloesen"]["gesamt"])
            parts.append(ft.Row([
                ui.GradientButton("Plan ausblenden" if opened else "Tilgungsplan",
                                  lambda _e, i=item["id"]: self._toggle_plan(i), kind="ghost",
                                  height=38, expand=True), repay], spacing=8))
            box = self._person_box(parts)
            if item["ausfaelle"]:
                box.border = ft.Border.all(1, C["red"])
            boxes.append(box)
        return ui.Card("Laufende Kredite", boxes, accent=C["orange"])

    def _loan_plan(self, item):
        rows, skipped = fg.loan_plan_rows(item)

        def line(values, color, weight=None):
            return ft.Row([ui.text(value, size=11, color=color, weight=weight, expand=True,
                                   text_align=ft.TextAlign.RIGHT) for value in values],
                          spacing=4)

        lines = [line(("Tag", "Rate", "Zinsen", "Tilgung", "Rest"), C["muted"],
                      ft.FontWeight.BOLD)]
        for number, row in enumerate(rows):
            if skipped and number == len(rows) - 1:
                lines.append(ui.text("… %d weitere Raten …" % skipped, size=11,
                                     color=C["muted"]))
            lines.append(line(["%d" % row[0]] + [euro(value) for value in row[1:]],
                              C["text_soft"]))
        lines.append(ui.text("Noch zu zahlende Zinsen, wenn jede Rate klappt: %s"
                             % euro(item["zinsen_noch"]), size=12, color=C["text_dim"]))
        return ft.Column(lines, spacing=3, tight=True)

    def _toggle_plan(self, loan_id):
        if loan_id in self.plans_for:
            self.plans_for.discard(loan_id)
        else:
            self.plans_for.add(loan_id)
        self._fill_firm()

    def _loan_step(self, delta):
        state = self.game.state
        self.loan_amount = fg.clamp_loan_amount(state, fg.clamp_loan_amount(
            state, self.loan_amount or 0) + delta)
        self._fill_firm()

    def _loan_choose_term(self, term):
        self.loan_term = int(term)
        self._fill_firm()

    def _take_loan(self, offer):
        def confirmed():
            try:
                if offer["paket"] == fg.FREE_LOAN:
                    self.game.take_loan(offer["summe"], offer["laufzeit"])
                else:
                    self.game.take_loan(0, 0, offer["paket"])
            except ValueError as exc:
                self.toast(str(exc), C["yellow"])
                return
            self._firm_changed()

        self.app.confirm("Kredit aufnehmen", fg.loan_confirm_text(offer), confirmed)

    def _repay_loan(self, item):
        def confirmed():
            try:
                self.game.repay_loan(item["id"])
            except ValueError as exc:
                self.toast(str(exc), C["yellow"])
                return
            self._firm_changed()

        self.app.confirm("Kredit ablösen", fg.loan_payoff_text(item), confirmed)

    # -- Wohnung einrichten -------------------------------------------------

    def _toggle_edit(self, _event=None):
        self.editing = not self.editing
        self.selected = None
        self.problem = ""
        self._fill_site()

    def _selection_overlay(self):
        if not self.editing or not self.selected:
            return []
        item = next((i for i in fg.placed_furniture(self.game.state)
                     if i["stueck"] == self.selected), None)
        if item is None:
            return []
        return [{"k": "rect", "x": item["x"] - 0.08, "y": item["y"] - 0.08,
                 "w": item["w"] + 0.16, "h": item["h"] + 0.16, "fill": "",
                 "line": C["accent"], "lw": 0.08, "r": 0.1}]

    def _home_tap(self, x, y):
        if not self.editing:
            return False
        state = self.game.state
        hit = fg.furniture_at(state, x, y)
        if hit and hit["stueck"] != self.selected:
            self.selected = hit["stueck"]
            self.turn = hit["dreh"]
            self.problem = ""
        elif not self.selected:
            self.problem = "Wähle zuerst ein Möbelstück aus (im Grundriss oder im Karton)."
        else:
            item = fg.furniture_item(state.furniture.get(self.selected))
            w, h = fg.furniture_size(item, self.turn)
            try:
                self.game.place_furniture(self.selected, x - w / 2.0, y - h / 2.0, self.turn)
                self.problem = ""
            except ValueError as exc:
                self.problem = str(exc)
        self._fill_site()
        return True

    def _select_piece(self, piece):
        self.selected = piece
        self.turn = fg.home_layout(self.game.state)["moebel"].get(piece, [0, 0, 0])[2]
        self.problem = "Tippe im Grundriss auf die Stelle, wo es stehen soll."
        self._fill_site()

    def _rotate(self, _event=None):
        state = self.game.state
        self.turn = (self.turn + 1) % 4
        placed = fg.home_layout(state)["moebel"].get(self.selected)
        if placed:
            item = fg.furniture_item(state.furniture[self.selected])
            old_w, old_h = fg.furniture_size(item, placed[2])
            new_w, new_h = fg.furniture_size(item, self.turn)
            try:
                self.game.place_furniture(self.selected, placed[0] + old_w / 2.0 - new_w / 2.0,
                                          placed[1] + old_h / 2.0 - new_h / 2.0, self.turn)
                self.problem = ""
            except ValueError as exc:
                self.turn = placed[2]
                self.problem = str(exc)
        self._fill_site()

    def _box(self, _event=None):
        self.game.box_furniture(self.selected)
        self.selected = None
        self.problem = ""
        self._fill_site()

    def _sell(self, _event=None):
        item = fg.furniture_item(self.game.state.furniture.get(self.selected))
        price = int(item["preis"] * fg.GAME["wohnungen"].get("rueckkauf", 0.5))

        def confirmed():
            try:
                self.game.sell_furniture(self.selected)
            except ValueError as exc:
                self.toast(str(exc), C["yellow"])
            self.selected = None
            self.problem = ""
            self.app.notify_progress()
            self._fill_site()

        self.app.confirm("Verkaufen", "%s für %s verkaufen?" % (item["name"], euro(price)),
                         confirmed)

    def _buy(self, item_id):
        try:
            piece = self.game.buy_furniture(item_id)
        except ValueError as exc:
            self.toast(str(exc), C["yellow"])
            return
        self.app.notify_progress()
        self._select_piece(piece)

    def _floor(self, room_id, kind=None, color=None):
        state = self.game.state
        current = fg.home_layout(state)["boeden"].get(room_id)
        building = fg.apartment(state.home_id)["gebaeude"]
        base = next(r for r in building["raeume"] if r["id"] == room_id)
        old_kind, old_color = current or [base.get("boden", "parkett"), None]
        self.game.set_floor(room_id, kind or old_kind, color or old_color)
        self._fill_site()

    def _move(self, home):
        rent = fg.rent_mode()

        def confirmed():
            try:
                self.game.move_home(home["id"], rent=rent)
            except ValueError as exc:
                self.toast(str(exc), C["yellow"])
                return
            self.positions.pop(fg.SITE_HOME, None)
            self.selected = None
            self.app.notify_progress()
            self._fill_site()

        self.app.confirm("Umziehen", fg.move_texts(self.game.state, home, rent)[1],
                         confirmed)

    def _item_row(self, title, price, label, on_click, enabled=True, active=False,
                  detail=""):
        lines = [ui.text(title, size=14, weight=ft.FontWeight.BOLD)]
        if detail:
            lines.append(ui.text(detail, size=11, color=C["muted"]))
        if price:
            lines.append(ui.text(price, size=12, color=C["text_dim"]))
        button = ui.GradientButton(label, on_click, kind="ghost", height=36)
        button.set_enabled(enabled)
        return ft.Container(
            content=ft.Row([ft.Column(lines, spacing=2, tight=True, expand=True), button],
                           spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=C["card_hi"] if active else C["card_alt"],
            border=ft.Border.all(1, C["border"]), border_radius=12,
            padding=ft.Padding.symmetric(horizontal=12, vertical=8))

    def _home_editor(self, state):
        mine = []
        if self.selected and self.selected in state.furniture:
            item = fg.furniture_item(state.furniture[self.selected])
            mine += [ui.label("Ausgewählt"),
                     ui.text(item["name"], size=15, weight=ft.FontWeight.BOLD),
                     ft.Row([ui.GradientButton("Drehen", self._rotate, kind="ghost",
                                               height=38),
                             ui.GradientButton("In den Karton", self._box, kind="ghost",
                                               height=38),
                             ui.GradientButton("Verkaufen", self._sell, kind="ghost",
                                               height=38)],
                            wrap=True, spacing=8, run_spacing=8)]
        mine.append(ui.label("Im Karton"))
        boxed = fg.boxed_furniture(state)
        if not boxed:
            mine.append(ui.text("Alles ist ausgepackt.", size=13, color=C["text_dim"]))
        for piece, item_id in boxed:
            mine.append(self._item_row(fg.furniture_item(item_id)["name"], "", "Aufstellen",
                                       lambda _e, p=piece: self._select_piece(p),
                                       active=piece == self.selected))

        shop = [self._item_row(item["name"], euro(item["preis"]), "Kaufen",
                               lambda _e, i=item["id"]: self._buy(i),
                               enabled=state.money >= item["preis"])
                for item in fg.shop_items()]

        floors = []
        layout = fg.home_layout(state)
        for room in fg.apartment(state.home_id)["gebaeude"]["raeume"]:
            kind, color = layout["boeden"].get(room["id"], [room.get("boden", "parkett"),
                                                            None])
            kinds = [key for key, _name in fg.FLOOR_KINDS]
            colors = [key for key, _name in fg.FLOOR_COLORS]
            floors += [ui.text(room["name"], size=14, weight=ft.FontWeight.BOLD),
                       ui.PillGroup(fg.FLOOR_KINDS, initial=kinds.index(kind)
                                    if kind in kinds else 0,
                                    on_change=lambda k, r=room["id"]: self._floor(r, kind=k)),
                       ui.PillGroup(fg.FLOOR_COLORS, initial=colors.index(color)
                                    if color in colors else -1,
                                    on_change=lambda c, r=room["id"]: self._floor(r, color=c))]

        flat = fg.apartment(state.home_id)
        rent = fg.rent_mode()
        homes = [ui.text("Du wohnst in: %s" % flat["name"], size=14,
                         weight=ft.FontWeight.BOLD)]
        if fg.rent_text(state):
            homes.append(ui.text(fg.rent_text(state), size=12, color=C["orange"],
                                 weight=ft.FontWeight.BOLD))
        homes.append(ui.text(flat.get("text", ""), size=12, color=C["text_dim"]))
        moves = fg.moves_available(state)
        for home in moves:
            homes.append(self._item_row(home["name"], fg.move_texts(state, home, rent)[0],
                                        "Umziehen", lambda _e, h=home: self._move(h),
                                        enabled=not fg.move_offer(state, home, rent)["fehlt"],
                                        detail=home.get("text", "")))
        if not moves:
            homes.append(ui.text("Du wohnst schon in der größten Wohnung.", size=13,
                                 color=C["text_dim"]))
        return [ui.Card("Deine Möbel", mine, accent=C["accent"]),
                ui.Card("Möbelhaus", shop, accent=C["purple"],
                        subtitle="Einmal bezahlen, für immer behalten"),
                ui.Card("Böden", floors, accent=C["green"]),
                ui.Card("Wohnung", homes, accent=C["orange"],
                        subtitle=fg.HOME_SUBTITLE[rent])]

    def _open_cards(self, category, topic=None):
        self.app.screens["cards"].set_category(category, topic)
        self.app.open("cards")

    def _open_learn(self, kind, title):
        self.app.open_search_hit(kind, title)
