#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FISI Lernplattform - Oberflaechenbausteine
==========================================

Alle Bausteine des dunklen Dashboard-Designs. Bewusst mit reinem Tkinter
umgesetzt (Canvas-Zeichnungen statt Bilddateien), damit das Programm ohne
externe Bibliotheken auf jedem Betriebssystem identisch aussieht.
"""

import calendar as calmod
import datetime
import tkinter as tk
import tkinter.font as tkfont

from fisi_core import C, mix, lighten

# Wird beim Start durch setup_fonts() gefuellt.
F = {}


# ============================================================================
#  SCHRIFTEN
# ============================================================================

def setup_fonts(root):
    """Waehlt vorhandene Schriftarten aus und legt die Groessen fest."""
    families = set(tkfont.families(root))

    def pick(candidates, fallback):
        for name in candidates:
            if name in families:
                return name
        return fallback

    ui = pick(["Segoe UI", "Inter", "Ubuntu", "Noto Sans", "DejaVu Sans",
               "Helvetica Neue", "Helvetica", "Arial"], "TkDefaultFont")
    mono = pick(["Cascadia Mono", "Consolas", "JetBrains Mono", "Ubuntu Mono",
                 "DejaVu Sans Mono", "Menlo", "Courier New"], "TkFixedFont")

    F.clear()
    F.update({
        "family": ui,
        "mono_family": mono,
        "display": (ui, 26, "bold"),
        "h1": (ui, 19, "bold"),
        "h2": (ui, 15, "bold"),
        "h3": (ui, 12, "bold"),
        "body": (ui, 10),
        "body_bold": (ui, 10, "bold"),
        "small": (ui, 9),
        "small_bold": (ui, 9, "bold"),
        "tiny": (ui, 8),
        "label": (ui, 9, "bold"),
        "nav": (ui, 10, "bold"),
        "mono": (mono, 10),
        "mono_small": (mono, 9),
        "ring_big": (ui, 17, "bold"),
        "ring_small": (ui, 8),
    })
    return F


# ============================================================================
#  ZEICHENHILFEN
# ============================================================================

def rounded_rect(canvas, x1, y1, x2, y2, radius=12, **kwargs):
    """Zeichnet ein Rechteck mit abgerundeten Ecken auf einen Canvas."""
    radius = max(0, min(radius, (x2 - x1) / 2, (y2 - y1) / 2))
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


def draw_icon(canvas, name, x, y, size=16, color="#FFFFFF", width=2, tags=None):
    """Zeichnet ein Symbol als Vektorgrafik mittig auf (x, y).

    Bewusst selbst gezeichnet statt als Unicode-Zeichen: nicht jedes System
    hat eine Schriftart mit den passenden Symbolen, und fehlende Zeichen
    wuerden sonst als roher Code (z.B. \\u25c8) erscheinen.
    """
    half = size / 2.0
    left, top, right, bottom = x - half, y - half, x + half, y + half
    opts = {"fill": color, "width": width, "capstyle": "round",
            "joinstyle": "round"}
    if tags:
        opts["tags"] = tags
    fill_opts = {"fill": color, "outline": ""}
    if tags:
        fill_opts["tags"] = tags
    line_opts = {"outline": color, "width": width}
    if tags:
        line_opts["tags"] = tags

    if name == "grid":            # Dashboard
        gap = size * 0.12
        cell = (size - gap) / 2
        for cx in (left, left + cell + gap):
            for cy in (top, top + cell + gap):
                canvas.create_rectangle(cx, cy, cx + cell, cy + cell,
                                        fill=color, outline="",
                                        **({"tags": tags} if tags else {}))

    elif name == "cards":         # Karteikarten
        canvas.create_rectangle(left, top + size * 0.18, right - size * 0.18,
                                bottom, fill="", **line_opts)
        canvas.create_line(left + size * 0.18, top, right, top,
                           **opts)
        canvas.create_line(right, top, right, bottom - size * 0.18, **opts)

    elif name == "target":        # Pruefungstrainer
        canvas.create_oval(left, top, right, bottom, fill="", **line_opts)
        inset = size * 0.3
        canvas.create_oval(left + inset, top + inset, right - inset,
                           bottom - inset, fill="", **line_opts)

    elif name == "diamond":       # AP2 Szenarien
        canvas.create_polygon(x, top, right, y, x, bottom, left, y,
                              fill=color, outline="",
                              **({"tags": tags} if tags else {}))

    elif name == "calc":          # Praxis-Rechner
        canvas.create_rectangle(left + size * 0.12, top, right - size * 0.12,
                                bottom, fill="", **line_opts)
        canvas.create_line(left + size * 0.28, top + size * 0.3,
                           right - size * 0.28, top + size * 0.3, **opts)
        for row in (0.58, 0.8):
            for col in (0.3, 0.52, 0.72):
                px, py = left + size * col, top + size * row
                canvas.create_oval(px - 1.2, py - 1.2, px + 1.2, py + 1.2,
                                   **fill_opts)

    elif name == "chart":         # Lernfortschritt
        canvas.create_line(left, bottom, right, bottom, **opts)
        canvas.create_line(left, bottom, left, top, **opts)
        for index, height in enumerate((0.35, 0.65, 0.5, 0.85)):
            bx = left + size * (0.22 + index * 0.2)
            canvas.create_line(bx, bottom - 1, bx, bottom - size * height,
                               fill=color, width=width,
                               **({"tags": tags} if tags else {}))

    elif name == "gear":          # Einstellungen
        canvas.create_oval(left, top, right, bottom, fill="", **line_opts)
        inset = size * 0.33
        canvas.create_oval(left + inset, top + inset, right - inset,
                           bottom - inset, fill=color, outline="",
                           **({"tags": tags} if tags else {}))

    elif name == "node":          # Netzwerk
        radius = size * 0.13
        points = [(x, top + radius), (left + radius, bottom - radius),
                  (right - radius, bottom - radius)]
        for px, py in points:
            canvas.create_line(x, y, px, py, fill=color, width=1,
                               **({"tags": tags} if tags else {}))
        for px, py in points:
            canvas.create_oval(px - radius, py - radius, px + radius,
                               py + radius, **fill_opts)

    elif name == "shield":        # Sicherheit
        canvas.create_polygon(x, top, right, top + size * 0.22,
                              right - size * 0.1, bottom, x, bottom,
                              left + size * 0.1, bottom, left,
                              top + size * 0.22,
                              fill=color, outline="", smooth=False,
                              **({"tags": tags} if tags else {}))

    elif name == "server":        # Systeme
        height = size * 0.26
        for row in range(3):
            ty = top + row * (height + size * 0.11)
            canvas.create_rectangle(left, ty, right, ty + height,
                                    fill="", **line_opts)

    elif name == "flag":           # Test Projekt
        canvas.create_line(left + size * 0.14, top, left + size * 0.14, bottom,
                           **opts)
        canvas.create_polygon(left + size * 0.14, top,
                              right, top + size * 0.22,
                              left + size * 0.14, top + size * 0.44,
                              fill=color, outline="",
                              **({"tags": tags} if tags else {}))

    elif name == "case":          # Wirtschaft
        canvas.create_rectangle(left, top + size * 0.26, right, bottom,
                                fill="", **line_opts)
        canvas.create_line(left + size * 0.3, top + size * 0.26,
                           left + size * 0.3, top + size * 0.08, **opts)
        canvas.create_line(left + size * 0.3, top + size * 0.08,
                           right - size * 0.3, top + size * 0.08, **opts)
        canvas.create_line(right - size * 0.3, top + size * 0.08,
                           right - size * 0.3, top + size * 0.26, **opts)

    elif name == "search":
        radius = size * 0.32
        canvas.create_oval(x - radius - size * 0.1, y - radius - size * 0.1,
                           x + radius - size * 0.1, y + radius - size * 0.1,
                           fill="", **line_opts)
        canvas.create_line(x + radius - size * 0.22, y + radius - size * 0.22,
                           right, bottom, **opts)

    elif name == "bell":
        canvas.create_oval(left + size * 0.16, top, right - size * 0.16,
                           bottom - size * 0.24, fill=color, outline="",
                           **({"tags": tags} if tags else {}))
        canvas.create_line(left + size * 0.3, bottom - size * 0.1,
                           right - size * 0.3, bottom - size * 0.1, **opts)

    elif name in ("chevron_down", "chevron_up", "arrow_left", "arrow_right"):
        small = size * 0.32
        if name == "chevron_down":
            canvas.create_line(x - small, y - small * 0.6, x, y + small * 0.6,
                               x + small, y - small * 0.6, fill=color,
                               width=width, capstyle="round", joinstyle="round",
                               **({"tags": tags} if tags else {}))
        elif name == "chevron_up":
            canvas.create_line(x - small, y + small * 0.6, x, y - small * 0.6,
                               x + small, y + small * 0.6, fill=color,
                               width=width, capstyle="round", joinstyle="round",
                               **({"tags": tags} if tags else {}))
        elif name == "arrow_left":
            canvas.create_polygon(x + small * 0.7, y - small, x - small * 0.7, y,
                                  x + small * 0.7, y + small, fill=color,
                                  outline="", **({"tags": tags} if tags else {}))
        else:
            canvas.create_polygon(x - small * 0.7, y - small, x + small * 0.7, y,
                                  x - small * 0.7, y + small, fill=color,
                                  outline="", **({"tags": tags} if tags else {}))

    elif name == "plus":
        arm = size * 0.34
        canvas.create_line(x - arm, y, x + arm, y, **opts)
        canvas.create_line(x, y - arm, x, y + arm, **opts)

    elif name == "minus":
        arm = size * 0.34
        canvas.create_line(x - arm, y, x + arm, y, **opts)

    else:                          # Rueckfallebene: schlichter Punkt
        radius = size * 0.28
        canvas.create_oval(x - radius, y - radius, x + radius, y + radius,
                           **fill_opts)


def gradient_bar(canvas, x1, y1, x2, y2, color_from, color_to, steps=None):
    """Zeichnet einen waagerechten Farbverlauf als Folge schmaler Rechtecke."""
    width = max(1, int(x2 - x1))
    steps = steps or min(width, 120)
    step_width = width / steps
    items = []
    for index in range(steps):
        color = mix(color_from, color_to, index / max(1, steps - 1))
        sx = x1 + index * step_width
        items.append(canvas.create_rectangle(sx, y1, sx + step_width + 1, y2,
                                             fill=color, outline=color))
    return items


# ============================================================================
#  BUTTONS
# ============================================================================

class NeoButton(tk.Canvas):
    """Auf Canvas gezeichneter Button mit abgerundeten Ecken.

    tk.Button laesst sich auf manchen Plattformen nicht vollstaendig
    einfaerben, deshalb wird der Button hier selbst gezeichnet.
    """

    def __init__(self, parent, text, command=None, kind="primary",
                 width=None, height=36, radius=10, font=None, parent_bg=None,
                 icon=None):
        self.parent_bg = parent_bg or _bg_of(parent)
        self.text = text
        self.icon = icon
        self.command = command
        self.kind = kind
        self.radius = radius
        self.font = font or F["body_bold"]
        self._enabled = True
        self._hover = False
        self._active = False

        measure = tkfont.Font(family=self.font[0], size=self.font[1],
                              weight=self.font[2] if len(self.font) > 2 else "normal")
        self._label = text
        needed = measure.measure(text) + 40 + (22 if icon else 0)
        super().__init__(parent, width=width or needed, height=height,
                         bg=self.parent_bg, highlightthickness=0, bd=0)

        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.configure(cursor="hand2")
        self._draw()

    # -- Darstellung --------------------------------------------------------

    def _palette(self):
        if not self._enabled:
            return C["card_alt"], C["muted"], C["border"]
        if self.kind == "primary":
            base = C["purple"]
            return (lighten(base, 0.12) if self._hover else base), "#12071F", base
        if self.kind == "accent":
            base = C["cyan"]
            return (lighten(base, 0.12) if self._hover else base), "#06121A", base
        if self.kind == "danger":
            base = C["red"]
            return (lighten(base, 0.1) if self._hover else base), "#230A0A", base
        if self.kind == "pill":
            if self._active:
                return C["purple"], "#12071F", C["purple"]
            return (C["card_hi"] if self._hover else C["card_alt"]), C["text_dim"], C["border"]
        # ghost
        return (C["card_hi"] if self._hover else C["card_alt"]), C["text"], C["border"]

    def _draw(self):
        self.delete("all")
        width = self.winfo_width() or int(self["width"])
        height = self.winfo_height() or int(self["height"])
        fill, fg, outline = self._palette()
        rounded_rect(self, 1, 1, width - 1, height - 1, self.radius,
                     fill=fill, outline=outline)
        if self.icon:
            draw_icon(self, self.icon, 20, height / 2, 13, fg, width=2)
            self.create_text(width / 2 + 10, height / 2, text=self._label,
                             fill=fg, font=self.font)
        else:
            self.create_text(width / 2, height / 2, text=self._label, fill=fg,
                             font=self.font)

    # -- Verhalten ----------------------------------------------------------

    def _on_enter(self, _event=None):
        self._hover = True
        self._draw()

    def _on_leave(self, _event=None):
        self._hover = False
        self._draw()

    def _on_click(self, _event=None):
        if self._enabled and self.command:
            self.command()

    def set_enabled(self, flag):
        self._enabled = bool(flag)
        self.configure(cursor="hand2" if flag else "arrow")
        self._draw()

    def set_active(self, flag):
        self._active = bool(flag)
        self._draw()

    def set_text(self, text):
        self.text = text
        self._label = text
        self._draw()


class IconButton(tk.Canvas):
    """Kleiner, runder Symbolknopf (z.B. Pfeile im Kalender)."""

    def __init__(self, parent, icon, command=None, size=28, parent_bg=None,
                 color=None, icon_size=None):
        self.parent_bg = parent_bg or _bg_of(parent)
        self.icon = icon
        self.command = command
        self.size = size
        self.icon_size = icon_size or size * 0.5
        self.color = color or C["text_dim"]
        self._hover = False
        super().__init__(parent, width=size, height=size, bg=self.parent_bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<Button-1>", lambda e: self.command() if self.command else None)
        self._draw()

    def _set_hover(self, flag):
        self._hover = flag
        self._draw()

    def _draw(self):
        self.delete("all")
        size = self.size
        if self._hover:
            self.create_oval(1, 1, size - 1, size - 1, fill=C["card_hi"], outline="")
        draw_icon(self, self.icon, size / 2, size / 2, self.icon_size,
                  C["cyan"] if self._hover else self.color, width=2)


def _bg_of(widget):
    try:
        return widget.cget("bg")
    except tk.TclError:
        return C["card"]


# ============================================================================
#  KARTE (GRUNDBAUSTEIN DES DASHBOARDS)
# ============================================================================

class Card(tk.Frame):
    """Dunkle Kachel mit optionaler Ueberschrift."""

    def __init__(self, parent, title=None, subtitle=None, accent=None,
                 pad=16, bg=None):
        self.bg = bg or C["card"]
        super().__init__(parent, bg=self.bg, highlightbackground=C["border"],
                         highlightcolor=C["border"], highlightthickness=1, bd=0)
        self.head = None
        self.title_label = None
        self.subtitle_label = None
        if title:
            self.head = tk.Frame(self, bg=self.bg)
            self.head.pack(fill="x", padx=pad, pady=(pad, 0))
            self.title_label = tk.Label(self.head, text=title.upper(), bg=self.bg,
                                        fg=accent or C["cyan"], font=F["label"],
                                        anchor="w")
            self.title_label.pack(side="left")
            # Die Unterschrift wird immer angelegt, damit sie spaeter ohne
            # zusaetzliche Widgets geaendert werden kann.
            self.subtitle_label = tk.Label(self.head, text=subtitle or "",
                                           bg=self.bg, fg=C["muted"],
                                           font=F["tiny"], anchor="e")
            self.subtitle_label.pack(side="right")
        self.body = tk.Frame(self, bg=self.bg)
        self.body.pack(fill="both", expand=True, padx=pad,
                       pady=(10 if title else pad, pad))

    def set_subtitle(self, text, color=None):
        """Aendert die Unterschrift der Kachel zur Laufzeit."""
        if self.subtitle_label is not None:
            self.subtitle_label.configure(text=text, fg=color or C["muted"])


# ============================================================================
#  RING-DIAGRAMM
# ============================================================================

class RingStat(tk.Canvas):
    """Segmentierter Fortschrittsring mit Beschriftung in der Mitte."""

    def __init__(self, parent, size=128, thickness=10, segments=40,
                 parent_bg=None):
        self.bg = parent_bg or _bg_of(parent)
        self.size = size
        self.thickness = thickness
        self.segments = segments
        self._data = (0.0, C["cyan"], C["pink"], "", "")
        super().__init__(parent, width=size, height=size, bg=self.bg,
                         highlightthickness=0, bd=0)
        self._draw()

    def set(self, ratio, color_from=None, color_to=None, big="", small=""):
        self._data = (max(0.0, min(1.0, ratio)),
                      color_from or C["cyan"], color_to or C["pink"],
                      big, small)
        self._draw()

    def _draw(self):
        self.delete("all")
        ratio, color_from, color_to, big, small = self._data
        size = self.size
        pad = self.thickness / 2 + 3
        box = (pad, pad, size - pad, size - pad)
        seg_angle = 360.0 / self.segments
        gap = seg_angle * 0.32
        filled = int(round(ratio * self.segments))
        for index in range(self.segments):
            start = 90 - (index + 1) * seg_angle + gap / 2
            extent = seg_angle - gap
            if index < filled:
                color = mix(color_from, color_to, index / max(1, self.segments - 1))
            else:
                color = C["ring_bg"]
            self.create_arc(*box, start=start, extent=extent, style="arc",
                            width=self.thickness, outline=color)
        center = size / 2
        if big:
            offset = -7 if small else 0
            self.create_text(center, center + offset, text=big, fill=C["text"],
                             font=F["ring_big"])
        if small:
            self.create_text(center, center + 13, text=small, fill=C["muted"],
                             font=F["ring_small"])


class MiniRing(tk.Canvas):
    """Kleiner Ring mit Prozentwert - fuer Fachbereiche und Timeline."""

    def __init__(self, parent, size=74, thickness=7, parent_bg=None):
        self.bg = parent_bg or _bg_of(parent)
        self.size = size
        self.thickness = thickness
        self._pct = 0.0
        self._color = C["cyan"]
        super().__init__(parent, width=size, height=size, bg=self.bg,
                         highlightthickness=0, bd=0)
        self._draw()

    def set(self, pct, color):
        self._pct = max(0.0, min(100.0, pct))
        self._color = color
        self._draw()

    def _draw(self):
        self.delete("all")
        size = self.size
        pad = self.thickness / 2 + 2
        box = (pad, pad, size - pad, size - pad)
        self.create_arc(*box, start=90, extent=-359.9, style="arc",
                        width=self.thickness, outline=C["ring_bg"])
        if self._pct > 0:
            extent = -359.9 * (self._pct / 100.0)
            self.create_arc(*box, start=90, extent=extent, style="arc",
                            width=self.thickness, outline=self._color)
        self.create_text(size / 2, size / 2, text="%d%%" % round(self._pct),
                         fill=C["text"], font=F["small_bold"])


# ============================================================================
#  FORTSCHRITTSBALKEN
# ============================================================================

class GradientBar(tk.Canvas):
    """Beschrifteter Balken mit Farbverlauf."""

    def __init__(self, parent, label, color_from, color_to, height=44,
                 parent_bg=None):
        self.bg = parent_bg or _bg_of(parent)
        self.label = label
        self.color_from = color_from
        self.color_to = color_to
        self._pct = 0.0
        self._note = ""
        super().__init__(parent, height=height, bg=self.bg,
                         highlightthickness=0, bd=0)
        self.bind("<Configure>", lambda e: self._draw())

    def set(self, pct, note=""):
        self._pct = max(0.0, min(100.0, pct))
        self._note = note
        self._draw()

    def _draw(self):
        self.delete("all")
        width = self.winfo_width()
        if width <= 1:
            return
        self.create_text(0, 8, text=self.label, anchor="w", fill=C["text_dim"],
                         font=F["small"])
        self.create_text(width, 8, text=self._note, anchor="e", fill=C["muted"],
                         font=F["small"])
        top, bottom = 22, 32
        rounded_rect(self, 0, top, width, bottom, 5, fill=C["ring_bg"], outline="")
        filled = width * (self._pct / 100.0)
        if filled > 6:
            gradient_bar(self, 0, top, filled, bottom, self.color_from, self.color_to)


# ============================================================================
#  LINIENDIAGRAMM
# ============================================================================

class LineChart(tk.Canvas):
    """Liniendiagramm mit gefuellter Flaeche und Gitternetz."""

    def __init__(self, parent, height=220, parent_bg=None):
        self.bg = parent_bg or _bg_of(parent)
        self._labels = []
        self._series = []
        self._y_max = None
        super().__init__(parent, height=height, bg=self.bg,
                         highlightthickness=0, bd=0)
        self.bind("<Configure>", lambda e: self._draw())

    def set_data(self, labels, series, y_max=None):
        """series: Liste von dicts mit name, values, color.

        y_max legt die Obergrenze der y-Achse fest (z.B. 100 bei
        Prozentwerten). Ohne Angabe wird sie aus den Daten bestimmt.
        """
        self._labels = labels
        self._series = series
        self._y_max = y_max
        self._draw()

    def _draw(self):
        self.delete("all")
        width = self.winfo_width()
        height = self.winfo_height()
        if width <= 1 or height <= 1 or not self._labels:
            return

        left, right, top, bottom = 42, 14, 16, 30
        plot_w = width - left - right
        plot_h = height - top - bottom
        if plot_w <= 10 or plot_h <= 10:
            return

        if self._y_max:
            peak = float(self._y_max)
            step = peak / 4.0
        else:
            peak = 0
            for item in self._series:
                if item["values"]:
                    peak = max(peak, max(item["values"]))
            peak = max(5, peak)
            # auf eine glatte Zahl aufrunden
            step = max(1, int(peak / 4) + 1)
            peak = step * 4

        # Gitternetz und y-Achse
        for line in range(5):
            y = top + plot_h - (plot_h * line / 4)
            self.create_line(left, y, width - right, y, fill=C["border"])
            self.create_text(left - 8, y, text="%g" % (step * line), anchor="e",
                             fill=C["muted"], font=F["tiny"])

        count = len(self._labels)
        if count == 1:
            positions = [left + plot_w / 2]
        else:
            positions = [left + plot_w * i / (count - 1) for i in range(count)]

        # x-Beschriftung ausduennen, damit nichts ueberlappt
        stride = max(1, int(count / max(1, plot_w / 55)))
        for index, label in enumerate(self._labels):
            if index % stride == 0 or index == count - 1:
                self.create_text(positions[index], height - bottom + 14, text=label,
                                 fill=C["muted"], font=F["tiny"])

        for item in self._series:
            values = item["values"]
            color = item["color"]
            if not values:
                continue
            points = []
            for index, value in enumerate(values):
                y = top + plot_h - (plot_h * (value / peak))
                points.extend([positions[index], y])

            if len(points) >= 4:
                area = list(points)
                area.extend([positions[-1], top + plot_h, positions[0], top + plot_h])
                self.create_polygon(area, fill=mix(self.bg, color, 0.18),
                                    outline="", smooth=True)
                self.create_line(points, fill=color, width=2, smooth=True,
                                 capstyle="round")
            for index in range(0, len(values)):
                if values[index] > 0:
                    x, y = positions[index], points[index * 2 + 1]
                    self.create_oval(x - 3, y - 3, x + 3, y + 3, fill=color,
                                     outline=self.bg, width=1)

        # Legende
        legend_x = left + 4
        for item in self._series:
            self.create_rectangle(legend_x, top - 8, legend_x + 9, top - 3,
                                  fill=item["color"], outline="")
            self.create_text(legend_x + 14, top - 6, text=item["name"], anchor="w",
                             fill=C["text_dim"], font=F["tiny"])
            legend_x += 20 + len(item["name"]) * 6


# ============================================================================
#  HEATMAP
# ============================================================================

class Heatmap(tk.Canvas):
    """Farbgitter: eine Zeile je Fachbereich, eine Spalte je Tag."""

    def __init__(self, parent, height=200, parent_bg=None):
        self.bg = parent_bg or _bg_of(parent)
        self._rows = []
        self._columns = 0
        super().__init__(parent, height=height, bg=self.bg,
                         highlightthickness=0, bd=0)
        self.bind("<Configure>", lambda e: self._draw())

    def set_data(self, rows, columns):
        """rows: Liste von (label, color, [werte])."""
        self._rows = rows
        self._columns = columns
        self._draw()

    def _draw(self):
        self.delete("all")
        width = self.winfo_width()
        height = self.winfo_height()
        if width <= 1 or height <= 1 or not self._rows or not self._columns:
            return

        label_w = 84
        grid_x = label_w
        grid_w = width - label_w - 4
        row_h = min(30, (height - 16) / max(1, len(self._rows)))
        cell_w = grid_w / self._columns
        peak = 1
        for _label, _color, values in self._rows:
            if values:
                peak = max(peak, max(values))

        for row_index, (label, color, values) in enumerate(self._rows):
            y = 8 + row_index * (row_h + 8)
            self.create_text(0, y + row_h / 2, text=label, anchor="w",
                             fill=C["text_dim"], font=F["small"])
            for col in range(self._columns):
                value = values[col] if col < len(values) else 0
                intensity = 0.0 if peak == 0 else min(1.0, value / peak)
                cell = C["ring_bg"] if value == 0 else mix(darken_bg(color), color, intensity)
                x1 = grid_x + col * cell_w
                self.create_rectangle(x1 + 1, y, x1 + cell_w - 1, y + row_h,
                                      fill=cell, outline="")


def darken_bg(color):
    return mix(C["ring_bg"], color, 0.25)


# ============================================================================
#  KALENDER
# ============================================================================

class CalendarPanel(tk.Frame):
    """Monatskalender, der Lerntage hervorhebt."""

    WEEKDAYS = ["M", "D", "M", "D", "F", "S", "S"]

    def __init__(self, parent, bg=None):
        self.bg = bg or C["card"]
        super().__init__(parent, bg=self.bg)
        today = datetime.date.today()
        self.year = today.year
        self.month = today.month
        self._active_days = set()
        self._provider = None

        header = tk.Frame(self, bg=self.bg)
        header.pack(fill="x")
        IconButton(header, "arrow_left", self._prev_month, parent_bg=self.bg,
                   color=C["yellow"]).pack(side="left")
        self.lbl_month = tk.Label(header, text="", bg=self.bg, fg=C["text"],
                                  font=F["h3"])
        self.lbl_month.pack(side="left", expand=True)
        IconButton(header, "arrow_right", self._next_month, parent_bg=self.bg,
                   color=C["yellow"]).pack(side="right")

        self.canvas = tk.Canvas(self, bg=self.bg, highlightthickness=0, bd=0,
                                height=170)
        self.canvas.pack(fill="both", expand=True, pady=(8, 0))
        self.canvas.bind("<Configure>", lambda e: self._draw())

    def set_provider(self, provider):
        """provider(year, month) liefert die Menge aktiver Tage."""
        self._provider = provider
        self.refresh()

    def to_current_month(self):
        """Springt zurueck auf den laufenden Monat."""
        today = datetime.date.today()
        self.year, self.month = today.year, today.month
        self.refresh()

    def refresh(self):
        if self._provider:
            self._active_days = self._provider(self.year, self.month) or set()
        self.lbl_month.config(text="%s %d" % (self._month_name(), self.year))
        self._draw()

    def _month_name(self):
        names = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
                 "August", "September", "Oktober", "November", "Dezember"]
        return names[self.month - 1]

    def _prev_month(self):
        self.month -= 1
        if self.month < 1:
            self.month, self.year = 12, self.year - 1
        self.refresh()

    def _next_month(self):
        self.month += 1
        if self.month > 12:
            self.month, self.year = 1, self.year + 1
        self.refresh()

    def _draw(self):
        self.canvas.delete("all")
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width <= 1:
            return

        cell_w = width / 7.0
        cell_h = max(19, min(24, (height - 22) / 6.0))
        today = datetime.date.today()

        for index, day in enumerate(self.WEEKDAYS):
            color = C["pink"] if index >= 5 else C["muted"]
            self.canvas.create_text(cell_w * index + cell_w / 2, 8, text=day,
                                    fill=color, font=F["tiny"])

        weeks = calmod.Calendar(firstweekday=0).monthdayscalendar(self.year, self.month)
        for row, week in enumerate(weeks):
            for col, day in enumerate(week):
                if day == 0:
                    continue
                cx = cell_w * col + cell_w / 2
                cy = 26 + row * cell_h + cell_h / 2
                is_today = (day == today.day and self.month == today.month
                            and self.year == today.year)
                active = day in self._active_days
                radius = min(cell_w, cell_h) / 2 - 2
                if active:
                    self.canvas.create_oval(cx - radius, cy - radius, cx + radius,
                                            cy + radius, fill=C["purple"], outline="")
                if is_today:
                    self.canvas.create_oval(cx - radius, cy - radius, cx + radius,
                                            cy + radius, outline=C["cyan"], width=2)
                if active:
                    color = "#12071F"
                elif col >= 5:
                    color = C["pink"]
                else:
                    color = C["text_dim"]
                self.canvas.create_text(cx, cy, text=str(day), fill=color,
                                        font=F["small_bold"] if active else F["small"])


# ============================================================================
#  TIMELINE
# ============================================================================

class ThemeTimeline(tk.Canvas):
    """Fortschrittsleiste der AP2-Themen: Ringe plus verbindende Zeitachse."""

    def __init__(self, parent, height=190, parent_bg=None):
        self.bg = parent_bg or _bg_of(parent)
        self._items = []
        super().__init__(parent, height=height, bg=self.bg,
                         highlightthickness=0, bd=0)
        self.bind("<Configure>", lambda e: self._draw())

    def set_data(self, items):
        """items: Liste von (label, prozent, farbe)."""
        self._items = items
        self._draw()

    def _draw(self):
        self.delete("all")
        width = self.winfo_width()
        height = self.winfo_height()
        if width <= 1 or not self._items:
            return

        count = len(self._items)
        slot = width / count
        ring_r = min(30.0, slot / 2 - 10, (height - 90) / 2)
        ring_r = max(18.0, ring_r)
        ring_cy = 12 + ring_r
        line_y = ring_cy + ring_r + 26

        self.create_line(slot / 2, line_y, width - slot / 2, line_y,
                         fill=C["border_hi"], width=2)

        for index, (label, pct, color) in enumerate(self._items):
            cx = slot * index + slot / 2
            box = (cx - ring_r, ring_cy - ring_r, cx + ring_r, ring_cy + ring_r)
            self.create_arc(*box, start=90, extent=-359.9, style="arc",
                            width=6, outline=C["ring_bg"])
            if pct > 0:
                self.create_arc(*box, start=90, extent=-359.9 * (pct / 100.0),
                                style="arc", width=6, outline=color)
            self.create_text(cx, ring_cy, text="%d%%" % round(pct), fill=C["text"],
                             font=F["small_bold"])
            dot = 5 if pct <= 0 else 6
            self.create_oval(cx - dot, line_y - dot, cx + dot, line_y + dot,
                             fill=color if pct > 0 else C["ring_bg"],
                             outline=self.bg, width=2)
            self._wrapped_text(cx, line_y + 16, label, slot - 8)

    def _wrapped_text(self, x, y, text, max_width):
        words = text.split()
        lines, current = [], ""
        font = tkfont.Font(family=F["family"], size=F["tiny"][1])
        for word in words:
            candidate = (current + " " + word).strip()
            if font.measure(candidate) > max_width and current:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        for offset, line in enumerate(lines[:2]):
            self.create_text(x, y + offset * 12, text=line, fill=C["muted"],
                             font=F["tiny"])


# ============================================================================
#  ANTWORTOPTIONEN (MULTIPLE CHOICE)
# ============================================================================

class OptionList(tk.Frame):
    """Anklickbare Antwortzeilen statt klassischer Radiobuttons."""

    def __init__(self, parent, bg=None, on_change=None):
        self.bg = bg or C["card"]
        super().__init__(parent, bg=self.bg)
        self.on_change = on_change
        self._rows = []
        self._selected = None
        self._locked = False
        self.bind("<Configure>", self._on_resize)

    # -- Aufbau -------------------------------------------------------------

    def set_options(self, options):
        self.clear()
        for option in options:
            self._add_row(option)

    def clear(self):
        for row in self._rows:
            row["frame"].destroy()
        self._rows = []
        self._selected = None
        self._locked = False

    def _add_row(self, text):
        frame = tk.Frame(self, bg=C["card_alt"], highlightthickness=1,
                         highlightbackground=C["border"], bd=0, cursor="hand2")
        frame.pack(fill="x", pady=4)

        marker = tk.Canvas(frame, width=22, height=22, bg=C["card_alt"],
                           highlightthickness=0, bd=0, cursor="hand2")
        marker.pack(side="left", padx=(12, 8), pady=11)

        label = tk.Label(frame, text=text, bg=C["card_alt"], fg=C["text"],
                         font=F["body"], justify="left", anchor="w",
                         wraplength=640, cursor="hand2")
        label.pack(side="left", fill="x", expand=True, padx=(0, 12), pady=10)

        row = {"frame": frame, "marker": marker, "label": label, "text": text,
               "state": "idle"}
        for widget in (frame, marker, label):
            widget.bind("<Button-1>", lambda _e, value=text: self.select(value))
            widget.bind("<Enter>", lambda _e, r=row: self._hover(r, True))
            widget.bind("<Leave>", lambda _e, r=row: self._hover(r, False))
        self._rows.append(row)
        self._paint(row)

    # -- Zustand ------------------------------------------------------------

    def select(self, value):
        if self._locked:
            return
        self._selected = value
        for row in self._rows:
            row["state"] = "selected" if row["text"] == value else "idle"
            self._paint(row)
        if self.on_change:
            self.on_change(value)

    def get(self):
        return self._selected

    def reveal(self, correct_value):
        """Markiert nach dem Einreichen richtige und falsche Auswahl."""
        self._locked = True
        for row in self._rows:
            if row["text"] == correct_value:
                row["state"] = "correct"
            elif row["text"] == self._selected:
                row["state"] = "wrong"
            else:
                row["state"] = "muted"
            row["frame"].configure(cursor="arrow")
            self._paint(row)

    def _hover(self, row, flag):
        if self._locked or row["state"] == "selected":
            return
        row["frame"].configure(highlightbackground=C["border_hi"] if flag else C["border"])

    def _paint(self, row):
        state = row["state"]
        if state == "selected":
            bg, border, fg, dot = C["card_hi"], C["purple"], C["text"], C["purple"]
        elif state == "correct":
            bg, border, fg, dot = mix(C["card"], C["green"], 0.18), C["green"], C["text"], C["green"]
        elif state == "wrong":
            bg, border, fg, dot = mix(C["card"], C["red"], 0.18), C["red"], C["text"], C["red"]
        elif state == "muted":
            bg, border, fg, dot = C["card_alt"], C["border"], C["muted"], C["ring_bg"]
        else:
            bg, border, fg, dot = C["card_alt"], C["border"], C["text"], C["ring_bg"]

        row["frame"].configure(bg=bg, highlightbackground=border)
        row["label"].configure(bg=bg, fg=fg)
        marker = row["marker"]
        marker.configure(bg=bg)
        marker.delete("all")
        marker.create_oval(3, 3, 19, 19, outline=border, width=2)
        if state in ("selected", "correct", "wrong"):
            marker.create_oval(7, 7, 15, 15, fill=dot, outline="")

    def _on_resize(self, event):
        wrap = max(200, event.width - 80)
        for row in self._rows:
            row["label"].configure(wraplength=wrap)


# ============================================================================
#  SCROLLBARER BEREICH
# ============================================================================

class ScrollArea(tk.Frame):
    """Senkrecht scrollbarer Container fuer lange Ansichten."""

    def __init__(self, parent, bg=None):
        self.bg = bg or C["bg"]
        super().__init__(parent, bg=self.bg)
        self.canvas = tk.Canvas(self, bg=self.bg, highlightthickness=0, bd=0)
        self.scrollbar = tk.Scrollbar(self, orient="vertical",
                                      command=self.canvas.yview,
                                      bg=C["card"], troughcolor=self.bg,
                                      activebackground=C["purple"],
                                      highlightthickness=0, bd=0,
                                      relief="flat", width=10)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner = tk.Frame(self.canvas, bg=self.bg)
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.bind("<Enter>", lambda e: self._bind_wheel(True))
        self.bind("<Leave>", lambda e: self._bind_wheel(False))

    def _on_inner_configure(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self._window, width=event.width)

    def _bind_wheel(self, flag):
        if flag:
            self.canvas.bind_all("<MouseWheel>", self._on_wheel)
            self.canvas.bind_all("<Button-4>", self._on_wheel)
            self.canvas.bind_all("<Button-5>", self._on_wheel)
        else:
            self.canvas.unbind_all("<MouseWheel>")
            self.canvas.unbind_all("<Button-4>")
            self.canvas.unbind_all("<Button-5>")

    def _on_wheel(self, event):
        first, last = self.canvas.yview()
        if first <= 0.0 and last >= 1.0:
            return
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            delta = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(delta, "units")

    def to_top(self):
        self.canvas.yview_moveto(0.0)


# ============================================================================
#  KLEINE HILFSBAUSTEINE
# ============================================================================

def make_label(parent, text, font=None, fg=None, bg=None, **kwargs):
    bg = bg or _bg_of(parent)
    return tk.Label(parent, text=text, bg=bg, fg=fg or C["text"],
                    font=font or F["body"], **kwargs)


def make_text(parent, height=6, readonly=False):
    widget = tk.Text(parent, height=height, wrap="word", bd=0,
                     bg=C["card_alt"], fg=C["text"], insertbackground=C["cyan"],
                     selectbackground=C["purple"], selectforeground="#FFFFFF",
                     relief="flat", padx=12, pady=10, font=F["body"],
                     highlightthickness=1, highlightbackground=C["border"],
                     highlightcolor=C["border_hi"])
    if readonly:
        widget.configure(state="disabled")
    return widget


def set_text(widget, content):
    """Setzt den Inhalt eines (ggf. schreibgeschuetzten) Textfelds."""
    state = str(widget.cget("state"))
    widget.configure(state="normal")
    widget.delete("1.0", tk.END)
    widget.insert("1.0", content)
    if state == "disabled":
        widget.configure(state="disabled")


class Divider(tk.Frame):
    def __init__(self, parent, bg=None):
        super().__init__(parent, bg=C["border"], height=1)
