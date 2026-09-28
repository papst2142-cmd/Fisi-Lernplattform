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

    def __init__(self, state, selected, on_room):
        self.state = state
        self.selected = selected
        self.on_room = on_room
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
        building = fg.GAME["gebaeude"]
        margin = fg.PLAN_MARGIN
        scale = min(self.width_px / (building["breite"] + 2 * margin),
                    self.MAX_HEIGHT / (building["hoehe"] + 2 * margin))
        offset_x = (self.width_px - scale * building["breite"]) / 2.0
        return scale, offset_x, margin * scale

    def _draw(self):
        building = fg.GAME["gebaeude"]
        scale, ox, oy = self._layout()
        self.canvas.height = scale * (building["hoehe"] + 2 * fg.PLAN_MARGIN)
        profile = self.state.profile
        shapes = []
        for shape in fg.building_shapes(self.state.open_count_by_room(), self.selected,
                                        (profile["name"], profile["aussehen"])):
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
        # Text: Namen der Kollegen nur, wenn genug Platz ist (Tablet, quer)
        role = shape["role"]
        if role == "person" and scale < 18:
            return []
        size = 11 if role in ("raum", "badge") else 9
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

    def _tapped(self, event):
        scale, ox, oy = self._layout()
        position = event.local_position
        item = fg.room_at((position.x - ox) / scale, (position.y - oy) / scale)
        if item:
            self.on_room(item["id"])


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


# ============================================================================
#  SEITE "SPIEL"
# ============================================================================

class GameScreen:
    """Seite "Spiel" der Handy-App (gleiche Schnittstelle wie Screen in
    main.py: crumbs, root, on_show)."""

    crumbs = ("PRAXIS", "LERNSPIEL")

    def __init__(self, app):
        self.app = app
        self.db = app.db
        self.game = fg.Game(app.db, device="Handy")
        self.room = None
        self.draft = {}
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
            result.append(ui.Card("Willkommen im Lernspiel", [
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
            FloorPlan(state, self.room, self._select_room),
            ui.text("Raum antippen, um zu sehen, wer dort etwas braucht.", size=11,
                    color=C["muted"]),
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
            text = ("In diesem Raum ist heute nichts zu tun." if self.room else
                    fg.GAME["story"]["alle_erledigt"] if state.all_done() else
                    "Heute stehen keine Tickets an.")
            controls.append(ui.text(text, size=14, color=C["text_soft"]))
        for task, status in tickets:
            controls.append(self._ticket_row(task, status))
        if not self.room:
            end = ui.GradientButton("Arbeitstag beenden", self._end_day, kind="accent",
                                    expand=True)
            end.set_enabled(state.can_end_day())
            controls.append(ft.Row([end]))
        return ui.Card(title, controls, accent=accent, subtitle=subtitle)

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

    def open_ticket(self, task_id):
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

        if task["typ"] == "auswahl":
            self.options = ui.OptionList()
            options = list(task["optionen"])
            random.shuffle(options)
            self.options.set_options(options)
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
        else:
            self.options.reveal()
        self.app.notify_progress()

        color = C["green"] if payload["richtig"] else C["red"]
        result = [ft.Container(
            content=ft.Column([
                ui.text(fg.result_text(task, payload), size=14, color=color,
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
            "Zurück zur Übersicht", self._close, expand=True)])]

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
        while len(page.views) > 1:
            page.views.pop()
        self.on_show()
        page.update()

    def _open_cards(self, category):
        self.app.screens["cards"].set_category(category)
        self.app.open("cards")

    def _open_learn(self, kind, title):
        self.app.open_search_hit(kind, title)
