# -*- coding: utf-8 -*-
"""
FISI Lernplattform (Handy) - Bausteine der Oberflaeche
======================================================

Karten, Verlaufs-Knoepfe, Ringe, Diagramme, Kalender - im selben Look wie die
PC-Version (Farben und Verlaeufe aus fisi_theme.py), aber fuer Touch und
schmale Bildschirme gebaut. Alles mit Flet-Bordmitteln, ohne Pillow.
"""

import calendar
import datetime
import math

import flet as ft
import flet.canvas as cv

from fisi_theme import C, GRADIENTS, mix

MONO = "monospace"


# ============================================================================
#  TEXT
# ============================================================================

def text(value, size=14, color=None, weight=None, **kwargs):
    return ft.Text(value, size=size, color=color or C["text"], weight=weight, **kwargs)


def label(value, color=None):
    """Kleine Ueberschrift in Grossbuchstaben (wie MENUE/FACHBEREICH am PC)."""
    return ft.Text(value.upper(), size=11, weight=ft.FontWeight.BOLD,
                   color=color or C["muted"])


def gradient(kind, begin=ft.Alignment.CENTER_LEFT, end=ft.Alignment.CENTER_RIGHT):
    start, stop = GRADIENTS[kind] if isinstance(kind, str) else kind
    return ft.LinearGradient(colors=[start, stop], begin=begin, end=end)


# ============================================================================
#  KARTE
# ============================================================================

class Card(ft.Container):
    """Abgerundete Karte mit farbigem Strich und Titel in Grossbuchstaben."""

    def __init__(self, title=None, controls=None, accent=None, subtitle=None,
                 padding=16, spacing=10, expand=None, action=None):
        self.body = ft.Column(controls or [], spacing=spacing, tight=True,
                              horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self.subtitle_text = ft.Text(subtitle or "", size=11, color=C["muted"],
                                     text_align=ft.TextAlign.RIGHT)
        self.title_text = None
        self.tick = None
        column = [self.body]
        if title:
            accent = accent or C["accent"]
            self.tick = ft.Container(width=4, height=14, border_radius=2, bgcolor=accent)
            self.title_text = ft.Text(title.upper(), size=11, weight=ft.FontWeight.BOLD,
                                      color=accent, expand=True)
            header = ft.Row([
                self.tick, self.title_text,
                self.subtitle_text,
            ] + ([action] if action is not None else []),
                spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            column = [header, self.body]
        super().__init__(
            content=ft.Column(column, spacing=12, tight=True),
            bgcolor=C["card"], border_radius=16,
            border=ft.Border.all(1, C["border"]), padding=padding, expand=expand)

    def set_subtitle(self, value, color=None):
        self.subtitle_text.value = value
        self.subtitle_text.color = color or C["muted"]

    def set_title(self, value, color=None):
        """Titel (und Farbe) zur Laufzeit aendern - nur bei Karten mit Titel."""
        if self.title_text is not None:
            self.title_text.value = value.upper()
            if color:
                self.title_text.color = self.tick.bgcolor = color


# ============================================================================
#  KNOEPFE UND AUSWAHL
# ============================================================================

class GradientButton(ft.Container):
    """Knopf mit Farbverlauf (primary/accent/danger/success) oder als
    dezenter Rahmen-Knopf (kind='ghost')."""

    def __init__(self, caption, on_click=None, kind="primary", icon=None,
                 expand=None, height=46):
        self._kind = kind
        self._handler = on_click
        self.caption = ft.Text(caption, size=14, weight=ft.FontWeight.BOLD,
                               color=C["on_accent"] if kind != "ghost" else C["text"])
        row = [self.caption]
        if icon:
            row.insert(0, ft.Icon(icon, size=18,
                                  color=C["on_accent"] if kind != "ghost" else C["text"]))
        super().__init__(
            content=ft.Row(row, spacing=8, tight=True,
                           alignment=ft.MainAxisAlignment.CENTER),
            height=height, border_radius=height // 2,
            padding=ft.Padding.symmetric(horizontal=20),
            alignment=ft.Alignment.CENTER, expand=expand,
            on_click=self._clicked, ink=True)
        self._paint(True)

    def _paint(self, enabled):
        if self._kind == "ghost":
            self.gradient = None
            self.bgcolor = C["card_alt"]
            self.border = ft.Border.all(1, C["border_hi"])
        else:
            self.gradient = gradient(self._kind)
            self.border = None
        self.opacity = 1.0 if enabled else 0.4

    def _clicked(self, event):
        if self._handler and not self.disabled:
            self._handler(event)

    def set_enabled(self, flag):
        self.disabled = not flag
        self._paint(flag)

    def set_text(self, value):
        self.caption.value = value


class PillGroup(ft.Stack):
    """Sich gegenseitig ausschliessende Auswahl-Pillen, seitlich scrollbar.
    Ab 0.48: Passt die Reihe nicht auf den Bildschirm, laeuft sie rechts
    weich aus und ein Pfeil zeigt, dass es weitergeht (Tippen scrollt).

    Hinweis fuer alle Bausteine: In Ereignissen (Tippen) nie selbst update()
    aufrufen - sonst uebernimmt Flet danach die uebrigen Aenderungen der
    Seite nicht automatisch."""

    HINT_WIDTH = 34

    def __init__(self, options, on_change=None, initial=0):
        self.values = [value for value, _caption in options]
        self.on_select = on_change
        self.current = initial
        self.pills = []
        for index, (_value, caption) in enumerate(options):
            pill = ft.Container(
                content=ft.Text(caption, size=13, weight=ft.FontWeight.BOLD),
                height=36, border_radius=18, alignment=ft.Alignment.CENTER,
                padding=ft.Padding.symmetric(horizontal=16), ink=True,
                on_click=lambda _e, i=index: self.select(i))
            self.pills.append(pill)
        # Geschaetzte Breiten (fett, 13 px: etwa 7,6 px je Zeichen)
        self._widths = [32 + 7.6 * len(str(caption)) for _v, caption in options]
        self._captions = [caption for _v, caption in options]
        self._estimate = sum(self._widths) + 8 * max(0, len(options) - 1)
        self._placed = False
        self.row = ft.Row(self.pills, spacing=8, scroll=ft.ScrollMode.HIDDEN,
                          on_scroll=self._scrolled, scroll_interval=50)
        self.mask = ft.ShaderMask(
            content=self.row, blend_mode=ft.BlendMode.DST_IN,
            shader=ft.LinearGradient(begin=ft.Alignment.CENTER_LEFT,
                                     end=ft.Alignment.CENTER_RIGHT,
                                     colors=[ft.Colors.WHITE, ft.Colors.WHITE,
                                             ft.Colors.TRANSPARENT],
                                     stops=[0.0, 0.86, 1.0]))
        self.hint = ft.Container(
            content=ft.Icon(ft.Icons.CHEVRON_RIGHT, size=20, color=C["text_dim"]),
            width=self.HINT_WIDTH, height=36, right=0, top=0,
            alignment=ft.Alignment.CENTER_RIGHT, on_click=self._step,
            tooltip="Weitere Einträge")
        super().__init__([self.mask, self.hint], height=36,
                         on_size_change=self._sized, size_change_interval=100)
        self._more = None
        self._overflow(False)
        self._paint()

    def _overflow(self, flag):
        """Rechten Auslauf und Pfeil zeigen, solange es rechts weitergeht."""
        self._more = flag
        self.hint.visible = flag
        self.mask.shader.colors = [ft.Colors.WHITE, ft.Colors.WHITE,
                                   ft.Colors.TRANSPARENT if flag else ft.Colors.WHITE]

    def _sized(self, event):
        # Erste Schaetzung, bevor der Nutzer scrollt
        width = getattr(event, "width", 0) or 0
        if width and self._estimate > width - 4:
            if not self._more:
                self._overflow(True)
                self.update()
            # Liegt die gewaehlte Pille ausserhalb (z.B. Firma > Zertifizierungen),
            # einmal dorthin scrollen
            start = sum(self._widths[:self.current]) + 8 * self.current
            if not self._placed and start + self._widths[self.current] > width - self.HINT_WIDTH:
                self._placed = True
                # Ab 0.53 Zielposition knapper geschaetzt (etwa 7 px je Zeichen)
                # und mit mehr Rand, damit die Pille links nicht angeschnitten ist
                left = sum(32 + 7.0 * len(str(caption))
                           for caption in self._captions[:self.current])
                self.page.run_task(self._scroll_to, max(0, left + 8 * self.current - 24))
        self._placed = True

    async def _scroll_to(self, offset):
        try:
            await self.row.scroll_to(offset=offset, duration=0)
        except Exception:
            pass

    def _scrolled(self, event):
        more = (getattr(event, "extent_after", 0) or 0) > 4
        if more != self._more:
            self._overflow(more)
            self.update()

    async def _step(self, _event):
        try:
            await self.row.scroll_to(delta=160, duration=250)
        except Exception:
            pass

    def _paint(self):
        for index, pill in enumerate(self.pills):
            active = index == self.current
            pill.gradient = gradient("primary") if active else None
            pill.bgcolor = None if active else C["card_alt"]
            pill.border = None if active else ft.Border.all(1, C["border"])
            pill.content.color = C["on_accent"] if active else C["text_dim"]

    def select(self, index, notify=True):
        self.current = index
        self._paint()
        if notify and self.on_select:
            self.on_select(self.values[index])

    def select_value(self, value, notify=True):
        if value in self.values:
            self.current = self.values.index(value)
            self._paint()
            if notify and self.on_select:
                self.on_select(value)

    def get(self):
        return self.values[self.current]


class OptionList(ft.Column):
    """Antwortzeilen zum Antippen, nach dem Pruefen gruen/rot markiert."""

    def __init__(self):
        super().__init__(spacing=8, tight=True)
        self._rows = []
        self.selected = None
        self.locked = False

    def set_options(self, options):
        self.controls.clear()
        self._rows = []
        self.selected = None
        self.locked = False
        for option in options:
            marker = ft.Container(width=20, height=20, border_radius=10)
            caption = ft.Text(option, size=15, expand=True)
            row = ft.Container(
                content=ft.Row([marker, caption], spacing=12,
                               vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.Padding.symmetric(horizontal=14, vertical=12),
                border_radius=12, ink=True,
                on_click=lambda _e, value=option: self.select(value))
            entry = {"row": row, "marker": marker, "caption": caption,
                     "text": option, "state": "idle"}
            self._rows.append(entry)
            self._paint(entry)
            self.controls.append(row)

    def clear(self):
        self.set_options([])

    def select(self, value):
        if self.locked:
            return
        self.selected = value
        for entry in self._rows:
            entry["state"] = "selected" if entry["text"] == value else "idle"
            self._paint(entry)

    def get(self):
        return self.selected

    def reveal(self, correct_value):
        self.locked = True
        for entry in self._rows:
            if entry["text"] == correct_value:
                entry["state"] = "correct"
            elif entry["text"] == self.selected:
                entry["state"] = "wrong"
            else:
                entry["state"] = "muted"
            self._paint(entry)

    @staticmethod
    def _paint(entry):
        state = entry["state"]
        if state == "selected":
            bg, border, fg, dot = C["card_hi"], C["purple"], C["text"], C["purple"]
        elif state == "correct":
            bg, border, fg, dot = mix(C["card"], C["green"], 0.18), C["green"], C["text"], C["green"]
        elif state == "wrong":
            bg, border, fg, dot = mix(C["card"], C["red"], 0.18), C["red"], C["text"], C["red"]
        elif state == "muted":
            bg, border, fg, dot = C["card_alt"], C["border"], C["muted"], None
        else:
            bg, border, fg, dot = C["card_alt"], C["border"], C["text"], None
        strong = state in ("selected", "correct", "wrong")
        entry["row"].bgcolor = bg
        entry["row"].border = ft.Border.all(2 if strong else 1, border)
        entry["caption"].color = fg
        ring = border if state != "idle" else C["border_hi"]
        entry["marker"].border = ft.Border.all(2, ring)
        entry["marker"].content = ft.Container(
            width=10, height=10, border_radius=5, bgcolor=dot) if dot else None
        entry["marker"].alignment = ft.Alignment.CENTER


class Stepper(ft.Row):
    """Zahl mit Minus- und Plus-Knopf."""

    def __init__(self, value=10, minimum=1, maximum=100, step=5):
        self.value = value
        self.minimum = minimum
        self.maximum = maximum
        self.step = step
        self.label = ft.Container(
            content=ft.Text(str(value), size=15, weight=ft.FontWeight.BOLD,
                            color=C["text"]),
            width=58, height=38, border_radius=10, bgcolor=C["card_alt"],
            alignment=ft.Alignment.CENTER)
        super().__init__([
            self._button(ft.Icons.REMOVE, -1), self.label,
            self._button(ft.Icons.ADD, 1)], spacing=6, tight=True)

    def _button(self, icon, direction):
        return ft.Container(
            content=ft.Icon(icon, size=18, color=C["text"]), width=38, height=38,
            border_radius=19, bgcolor=C["card_alt"], ink=True,
            border=ft.Border.all(1, C["border"]), alignment=ft.Alignment.CENTER,
            on_click=lambda _e: self.change(direction * self.step))

    def change(self, delta):
        self.value = max(self.minimum, min(self.maximum, self.value + delta))
        self.label.content.value = str(self.value)

    def set_maximum(self, maximum):
        self.maximum = max(1, maximum)
        self.value = max(self.minimum, min(self.maximum, self.value))
        self.label.content.value = str(self.value)

    def get(self):
        return self.value


def entry(value="", hint=None, password=False, multiline=False, min_lines=1,
          max_lines=None, mono=False, keyboard=None, on_change=None, expand=None):
    """Dunkles, abgerundetes Eingabefeld. Bei password=True gibt es ab 0.48
    einen eigenen Augen-Knopf mit Beschriftung (auch fuer Screenreader)."""
    field = ft.TextField(
        value=value, hint_text=hint, password=password,
        multiline=multiline, min_lines=min_lines,
        max_lines=max_lines, keyboard_type=keyboard, on_change=on_change,
        bgcolor=C["card_alt"], filled=True, fill_color=C["card_alt"],
        border_color=C["border"], focused_border_color=C["purple"],
        border_radius=12, color=C["text"], cursor_color=C["accent"],
        hint_style=ft.TextStyle(color=C["muted"]),
        text_style=ft.TextStyle(font_family=MONO if mono else None, size=14),
        content_padding=ft.Padding.symmetric(horizontal=14, vertical=12),
        expand=expand)
    if password:
        def toggle(_event):
            field.password = not field.password
            eye.icon = ft.Icons.VISIBILITY_OFF if not field.password else ft.Icons.VISIBILITY
            eye.tooltip = "Verbergen" if not field.password else "Anzeigen"
        eye = ft.IconButton(icon=ft.Icons.VISIBILITY, icon_color=C["muted"],
                            tooltip="Anzeigen", on_click=toggle)
        field.suffix_icon = eye
    return field


def check_row(caption, value=False, on_change=None):
    """Haken mit mehrzeiliger Beschriftung (ab 0.51): ft.Checkbox bricht
    lange Texte nicht um. Auch das Tippen auf den Text setzt den Haken.
    on_change erhaelt den neuen Wert (True/False)."""
    box = ft.Checkbox(value=value, active_color=C["green"], check_color=C["on_accent"])

    def changed(_event=None):
        if on_change:
            on_change(bool(box.value))

    def toggle(_event):
        box.value = not box.value
        changed()

    box.on_change = changed
    return ft.Row([box, ft.Container(content=ft.Text(caption, size=13, color=C["text_soft"]),
                                     expand=True, on_click=toggle,
                                     padding=ft.Padding.symmetric(vertical=6))],
                  spacing=4, vertical_alignment=ft.CrossAxisAlignment.START)


def read_box(value="", mono=False):
    """Mehrzeiliger Text zum Lesen (Aufgaben, Loesungen, Rechenergebnisse)."""
    return ft.Container(
        content=ft.Text(value, size=13 if mono else 14, color=C["text_dim"],
                        font_family=MONO if mono else None, selectable=True),
        bgcolor=C["card_alt"], border_radius=12, padding=14,
        border=ft.Border.all(1, C["border"]))


def list_row(title, subtitle, accent, on_click, active=False, sub_color=None):
    """Antippbare Listenzeile mit farbiger Markierung links."""
    return ft.Container(
        content=ft.Row([
            ft.Container(width=4, height=34, border_radius=2, bgcolor=accent),
            ft.Column([
                ft.Text(title, size=14, weight=ft.FontWeight.BOLD,
                        color=C["text"] if active else C["text_dim"]),
                ft.Text(subtitle, size=12, color=sub_color or C["muted"]),
            ], spacing=2, tight=True, expand=True),
            ft.Icon(ft.Icons.CHEVRON_RIGHT, size=20, color=C["muted"]),
        ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=C["card_hi"] if active else C["card_alt"],
        border=ft.Border.all(1, C["purple"] if active else C["border"]),
        border_radius=12, padding=ft.Padding.symmetric(horizontal=12, vertical=10),
        ink=True, on_click=on_click)


def dot(color, size=9):
    return ft.Container(width=size, height=size, border_radius=size / 2, bgcolor=color)


# ============================================================================
#  BANNER, RINGE, BALKEN
# ============================================================================

class HeroPanel(ft.Container):
    """Farbverlaufs-Banner oben im Dashboard."""

    def __init__(self):
        self.title = ft.Text("", size=22, weight=ft.FontWeight.BOLD, color=C["on_accent"])
        self.sub = ft.Text("", size=13, color=mix(C["on_accent"], C["accent2"], 0.25))
        self.big = ft.Text("", size=30, weight=ft.FontWeight.BOLD, color=C["on_accent"])
        self.big_sub = ft.Text("", size=12, color=mix(C["on_accent"], C["accent2"], 0.25))
        super().__init__(
            content=ft.Row([
                ft.Column([self.title, self.sub], spacing=6, tight=True, expand=True),
                ft.Column([self.big, self.big_sub], spacing=0, tight=True,
                          horizontal_alignment=ft.CrossAxisAlignment.END),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            gradient=gradient("hero", ft.Alignment.TOP_LEFT, ft.Alignment.BOTTOM_RIGHT),
            border_radius=18, padding=20)

    def set_data(self, title, sub, big, big_sub):
        self.title.value = title
        self.sub.value = sub
        self.big.value = big
        self.big_sub.value = big_sub


class Ring(ft.Stack):
    """Fortschrittsring mit Farbverlauf und Text in der Mitte."""

    def __init__(self, size=120, thickness=11, big_size=22, small_size=11):
        self.size = size
        self.thickness = thickness
        self.canvas = cv.Canvas(width=size, height=size)
        self.big = ft.Text("", size=big_size, weight=ft.FontWeight.BOLD, color=C["text"],
                           text_align=ft.TextAlign.CENTER)
        self.small = ft.Text("", size=small_size, color=C["text_dim"],
                             text_align=ft.TextAlign.CENTER)
        center = ft.Container(
            content=ft.Column([self.big, self.small], spacing=0, tight=True,
                              horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=size, height=size, alignment=ft.Alignment.CENTER,
            padding=thickness + 6)
        super().__init__([self.canvas, center], width=size, height=size)

    def set(self, fraction, color_a, color_b=None, big="", small=""):
        fraction = max(0.0, min(1.0, fraction))
        color_b = color_b or color_a
        half = self.thickness / 2
        box = self.size - self.thickness
        shapes = [cv.Circle(self.size / 2, self.size / 2, box / 2, ft.Paint(
            color=C["ring_bg"], stroke_width=self.thickness,
            style=ft.PaintingStyle.STROKE))]
        # Ab 0.53 immer zwei Formen (Bogen bei 0 unsichtbar): Faellt ein Ring
        # auf 0, liess das Weglassen des Bogens den Flet-Client mit IndexError
        # abbrechen (z.B. Startseite nach "Sicherung einspielen > Alles ersetzen")
        if fraction <= 0:
            color_a = color_b = ft.Colors.TRANSPARENT
        sweep = max(0.02, fraction) * 2 * math.pi
        shapes.append(cv.Arc(
            half, half, box, box, start_angle=-math.pi / 2, sweep_angle=sweep,
            paint=ft.Paint(
                stroke_width=self.thickness, style=ft.PaintingStyle.STROKE,
                stroke_cap=ft.StrokeCap.ROUND,
                gradient=ft.PaintSweepGradient(
                    center=ft.Offset(self.size / 2, self.size / 2),
                    colors=[color_a, color_b, color_a if fraction >= 0.999 else color_b],
                    color_stops=[0.0, max(0.01, fraction), 1.0],
                    rotation=-math.pi / 2))))
        self.canvas.shapes = shapes
        self.big.value = big
        self.small.value = small


class GradientBar(ft.Column):
    """Beschriftung plus waagerechter Balken mit Farbverlauf."""

    def __init__(self, caption, color_a, color_b):
        self.colors = (color_a, color_b)
        self.value_text = ft.Text("", size=12, color=C["muted"])
        self.fill = ft.Container(height=8, border_radius=4,
                                 gradient=gradient((color_a, color_b)))
        self.rest = ft.Container(height=8)
        track = ft.Container(
            content=ft.Row([self.fill, self.rest], spacing=0),
            bgcolor=C["ring_bg"], border_radius=4, height=8)
        super().__init__([
            ft.Row([ft.Text(caption, size=13, color=C["text_dim"], expand=True),
                    self.value_text]),
            track,
        ], spacing=6, tight=True)

    def set(self, percent, value_text=""):
        share = int(round(max(0.0, min(100.0, percent)) * 10))
        self.fill.expand = share
        self.fill.visible = share > 0
        self.rest.expand = 1000 - share
        self.rest.visible = share < 1000
        self.value_text.value = value_text


# ============================================================================
#  DIAGRAMME
# ============================================================================

def _smooth(points, limits=None):
    """Catmull-Rom-Kurve durch alle Punkte als Bezier-Segmente (wie am PC)."""
    elements = [cv.Path.MoveTo(*points[0])]
    for index in range(len(points) - 1):
        p0 = points[index - 1] if index else points[index]
        p1, p2 = points[index], points[index + 1]
        p3 = points[index + 2] if index + 2 < len(points) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        if limits:
            # Kurve nicht unter die Nulllinie bzw. ueber den Rand schwingen lassen
            c1 = (c1[0], min(max(c1[1], limits[0]), limits[1]))
            c2 = (c2[0], min(max(c2[1], limits[0]), limits[1]))
        elements.append(cv.Path.CubicTo(c1[0], c1[1], c2[0], c2[1], p2[0], p2[1]))
    return elements


class LineChart(cv.Canvas):
    """Liniendiagramm mit weicher Kurve und Verlaufsflaeche. Zeichnet sich bei
    jeder Groessenaenderung neu (Breite kommt vom Handy-Bildschirm)."""

    def __init__(self, height=200):
        self._labels = []
        self._series = []
        self._color = C["accent"]
        self._y_max = None
        self._width = 300
        super().__init__(height=height, expand=True, on_resize=self._resized,
                         resize_interval=100)

    def _resized(self, event):
        self._width = event.width
        self._draw()
        self.update()

    def set_data(self, labels, values, color, y_max=None):
        self._labels = list(labels)
        self._series = list(values)
        self._color = color
        self._y_max = y_max
        self._draw()

    def _draw(self):
        width, height = self._width, self.height
        left, right, top, bottom = 30, 8, 10, 22
        plot_w = max(10, width - left - right)
        plot_h = max(10, height - top - bottom)
        values = self._series or [0]
        peak = self._y_max or max(4, max(values))
        step = _nice_step(peak)
        peak = step * math.ceil(peak / step)

        shapes = []
        grid_paint = ft.Paint(color=C["border"], stroke_width=1)
        axis_style = ft.TextStyle(size=10, color=C["muted"])
        tick = 0
        while tick <= peak + 0.001:
            y = top + plot_h - tick / peak * plot_h
            shapes.append(cv.Line(left, y, left + plot_w, y, grid_paint))
            shapes.append(cv.Text(left - 6, y, _fmt(tick), style=axis_style,
                                  alignment=ft.Alignment.CENTER_RIGHT))
            tick += step

        count = len(values)
        xs = [left + (plot_w * index / (count - 1) if count > 1 else plot_w / 2)
              for index in range(count)]
        points = [(x, top + plot_h - min(value, peak) / peak * plot_h)
                  for x, value in zip(xs, values)]
        if count > 1:
            curve = _smooth(points, (top, top + plot_h))
            area = curve + [cv.Path.LineTo(points[-1][0], top + plot_h),
                            cv.Path.LineTo(points[0][0], top + plot_h), cv.Path.Close()]
            shapes.append(cv.Path(area, paint=ft.Paint(
                style=ft.PaintingStyle.FILL,
                gradient=ft.PaintLinearGradient(
                    begin=ft.Offset(0, top), end=ft.Offset(0, top + plot_h),
                    colors=[ft.Colors.with_opacity(0.45, self._color),
                            ft.Colors.with_opacity(0.02, self._color)]))))
            shapes.append(cv.Path(curve, paint=ft.Paint(
                color=self._color, stroke_width=2.5, style=ft.PaintingStyle.STROKE,
                stroke_cap=ft.StrokeCap.ROUND, stroke_join=ft.StrokeJoin.ROUND)))
        for x, y in points:
            shapes.append(cv.Circle(x, y, 3, ft.Paint(color=self._color)))

        # Beschriftung der x-Achse: hoechstens ca. alle 45 Pixel eine
        every = max(1, math.ceil(count / max(1, plot_w / 45)))
        for index, (x, caption) in enumerate(zip(xs, self._labels)):
            last = index == count - 1
            if (index % every == 0 and (last or xs[-1] - x >= 40)) or last:
                # Die letzte Beschriftung endet am rechten Rand statt darueber
                shapes.append(cv.Text(x + (4 if last and count > 1 else 0), top + plot_h + 12,
                                      caption, style=axis_style,
                                      alignment=ft.Alignment.CENTER_RIGHT if last and count > 1
                                      else ft.Alignment.CENTER))
        self.shapes = shapes


def _nice_step(peak):
    for step in (1, 2, 5, 10, 20, 25, 50, 100, 200, 500):
        if peak / step <= 4:
            return step
    return 1000


def _fmt(value):
    return str(int(value)) if float(value).is_integer() else "%.1f" % value


class Heatmap(ft.Column):
    """Aktivitaet je Fachbereich (oder Thema) und Tag als Kaestchen-Raster.
    on_click(index) macht die Zeilen antippbar (Reinzoom in die Themen)."""

    def set_data(self, rows, days, on_click=None, selected=None, label_width=78):
        peak = max([max(values) for _name, _color, values in rows] + [1])
        self.controls = []
        for index, (name, color, values) in enumerate(rows):
            cells = [ft.Container(
                height=18, expand=True, border_radius=4,
                bgcolor=mix(C["card_alt"], color, 0.18 + 0.82 * value / peak)
                if value else C["card_alt"])
                for value in values[-days:]]
            chosen = index == selected
            row = ft.Row([
                ft.Text(name, size=12, width=label_width,
                        color=color if chosen else C["text_dim"],
                        weight=ft.FontWeight.BOLD if chosen else None)] + cells,
                spacing=3)
            if on_click:
                row = ft.Container(content=row, border_radius=6,
                                   on_click=lambda _e, i=index: on_click(i))
            self.controls.append(row)
        self.spacing = 8
        self.tight = True


class CalendarPanel(ft.Column):
    """Monatsuebersicht mit markierten Lerntagen und Blaettern."""

    MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
              "August", "September", "Oktober", "November", "Dezember"]

    def __init__(self, provider):
        super().__init__(spacing=6, tight=True)
        self.provider = provider
        today = datetime.date.today()
        self.year, self.month = today.year, today.month

    def to_current_month(self):
        today = datetime.date.today()
        self.year, self.month = today.year, today.month

    def _shift(self, delta):
        month = self.month + delta
        self.year += (month - 1) // 12
        self.month = (month - 1) % 12 + 1
        self.refresh()

    def _arrow(self, icon, delta):
        # Standard Cyan, beim Druecken gruen wie die Kachel
        # "Fortschritt je Fachbereich" (wie am PC)
        return ft.IconButton(
            icon=icon, icon_size=18, width=34, height=34,
            style=ft.ButtonStyle(
                icon_color={ft.ControlState.PRESSED: C["green"],
                            ft.ControlState.DEFAULT: C["accent"]},
                bgcolor=C["card_alt"],
                overlay_color=mix(C["card_alt"], C["green"], 0.18),
                padding=0, shape=ft.CircleBorder()),
            on_click=lambda _e: self._shift(delta))

    def refresh(self):
        active = self.provider(self.year, self.month)
        today = datetime.date.today()
        head = ft.Row([
            self._arrow(ft.Icons.CHEVRON_LEFT, -1),
            ft.Text("%s %d" % (self.MONTHS[self.month - 1], self.year), size=15,
                    weight=ft.FontWeight.BOLD, color=C["text"], expand=True,
                    text_align=ft.TextAlign.CENTER),
            self._arrow(ft.Icons.CHEVRON_RIGHT, 1),
        ])
        names = ft.Row([ft.Text(name, size=11, expand=True, text_align=ft.TextAlign.CENTER,
                                color=C["accent2"] if index > 4 else C["muted"])
                        for index, name in enumerate("MDMDFSS")])
        rows = [head, names]
        for week in calendar.Calendar().monthdayscalendar(self.year, self.month):
            cells = []
            for index, day in enumerate(week):
                if not day:
                    cells.append(ft.Container(height=32, expand=True))
                    continue
                learned = day in active
                is_today = (self.year, self.month, day) == (today.year, today.month, today.day)
                cells.append(ft.Container(
                    content=ft.Container(
                        content=ft.Text(str(day), size=12, weight=ft.FontWeight.BOLD
                                        if learned else None,
                                        color=C["sidebar"] if learned else
                                        (C["accent2"] if index > 4 else C["text_dim"])),
                        width=28, height=28, border_radius=14,
                        bgcolor=C["purple"] if learned else None,
                        border=ft.Border.all(2, C["accent"]) if is_today else None,
                        alignment=ft.Alignment.CENTER),
                    height=32, expand=True, alignment=ft.Alignment.CENTER))
            rows.append(ft.Row(cells, spacing=0))
        self.controls = rows


class ThemeProgress(ft.Column):
    """Fortschritt je Pruefungsthema (am PC eine Timeline mit Ringen)."""

    def set_data(self, items):
        self.controls = []
        for name, percent, color in items:
            ring = Ring(size=46, thickness=5, big_size=11, small_size=1)
            ring.set(percent / 100.0, color, mix(color, C["text"], 0.25),
                     "%d%%" % round(percent), "")
            ring.small.visible = False
            self.controls.append(ft.Row([
                ring, ft.Text(name, size=13, color=C["text_dim"], expand=True)],
                spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER))
        self.spacing = 8
        self.tight = True
