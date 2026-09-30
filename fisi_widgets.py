#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FISI Lernplattform - Oberflaechenbausteine
==========================================

Alle Bausteine des dunklen Dashboard-Designs auf Basis von CustomTkinter.
CustomTkinter liefert abgerundete Karten, Eingabefelder, Textfelder und
Scrollbalken. Farbverlaeufe (Buttons, Balken, Ringe, Banner) kann es nicht
selbst zeichnen - diese werden mit Pillow kantengeglaettet als Bild erzeugt
und zwischengespeichert. Diagramme (Liniendiagramm, Heatmap, Kalender)
bleiben Tk-Canvas-Zeichnungen in derselben Farbwelt.

Groessenangaben sind "logische" Pixel wie bei CustomTkinter. Fuer klassische
Tk-Widgets (Canvas) rechnet px() sie mit der Bildschirmskalierung um.
"""

import calendar as calmod
import datetime
import math
import os
import sys
import tkinter as tk
import tkinter.font as tkfont

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont, ImageTk

from fisi_theme import C, GRADIENTS, lighten, mix

# Wird beim Start durch setup_fonts() gefuellt.
F = {}

# Skalierungsfaktor der Oberflaeche (1.0 bei 100 % Windows-Skalierung)
_SCALE = [1.0]

# Bereits erzeugte Verlaufsbilder, damit Hover-Effekte nichts neu rendern
_IMAGE_CACHE = {}

# Pillow zeichnet in dieser Vergroesserung und rechnet dann herunter - so
# entstehen glatte Kanten ohne Treppeneffekt.
SUPERSAMPLE = 4


# ============================================================================
#  SCHRIFTEN UND SKALIERUNG
# ============================================================================

def setup_fonts(root):
    """Waehlt vorhandene Schriftarten aus und legt die Groessen fest.

    Die Groessen sind Pixelangaben im Sinne von CustomTkinter. Fuer Tk-Canvas
    rechnet tk_font() sie passend um.
    """
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

    _SCALE[0] = ctk.ScalingTracker.get_widget_scaling(root)

    F.clear()
    F.update({
        "family": ui,
        "mono_family": mono,
        "display": (ui, 34, "bold"),
        "h1": (ui, 26, "bold"),
        "h2": (ui, 19, "bold"),
        "h3": (ui, 15, "bold"),
        "body": (ui, 14),
        "body_bold": (ui, 14, "bold"),
        "small": (ui, 13),
        "small_bold": (ui, 13, "bold"),
        "tiny": (ui, 11),
        "label": (ui, 11, "bold"),
        "nav": (ui, 14, "bold"),
        "logo": (ui, 21, "bold"),
        "mono": (mono, 13),
        "mono_small": (mono, 12),
        "ring_big": (ui, 23, "bold"),
        "ring_small": (ui, 11),
    })
    return F


def px(value):
    """Logische Pixel in echte Bildschirmpixel (fuer Tk-Canvas)."""
    return int(round(value * _SCALE[0]))


def tk_font(font):
    """Rechnet eine Schriftangabe fuer klassische Tk-Widgets um. Negative
    Groessen bedeuten bei Tk Pixel - so passen Canvas-Texte exakt zu den
    CustomTkinter-Widgets."""
    return (font[0], -px(font[1])) + tuple(font[2:])


def text_width(text, font):
    """Breite eines einzeiligen Textes in logischen Pixeln."""
    return tkfont.Font(font=tk_font(font)).measure(text) / _SCALE[0]


def line_height(font):
    """Zeilenhoehe einer Schrift in logischen Pixeln."""
    return tkfont.Font(font=tk_font(font)).metrics("linespace") / _SCALE[0]


def _bg_of(widget):
    """Ermittelt die sichtbare Hintergrundfarbe eines Widgets - auch fuer
    CustomTkinter-Widgets mit transparentem Hintergrund."""
    while widget is not None:
        try:
            if isinstance(widget, (ctk.CTkBaseClass, ctk.CTk)):
                color = widget.cget("fg_color")
            else:
                color = widget.cget("bg")
        except (tk.TclError, ValueError, AttributeError):
            color = None
        if isinstance(color, (tuple, list)):
            color = color[1]
        if color and color != "transparent":
            return color
        widget = getattr(widget, "master", None)
    return C["bg"]


# ============================================================================
#  VERLAEUFE UND FORMEN (PILLOW)
# ============================================================================

def _gradient_fill(width, height, color_from, color_to, direction="h"):
    """Rechteckiger Farbverlauf. direction: h (links->rechts),
    v (oben->unten) oder d (diagonal)."""
    base = Image.linear_gradient("L")
    if direction == "h":
        mask = base.rotate(90).resize((width, height))
    elif direction == "v":
        mask = base.resize((width, height))
    else:
        horizontal = base.rotate(90).resize((width, height))
        mask = Image.blend(horizontal, base.resize((width, height)), 0.5)
    start = Image.new("RGB", (width, height), color_from)
    end = Image.new("RGB", (width, height), color_to)
    return Image.composite(end, start, mask)


def rounded_gradient(width, height, radius, color_from, color_to,
                     direction="h", border=None, border_width=1):
    """Abgerundetes Rechteck mit Farbverlauf als RGBA-Bild in
    SUPERSAMPLE-facher Groesse (wird beim Anzeigen heruntergerechnet)."""
    key = ("rect", width, height, radius, color_from, color_to, direction,
           border, border_width)
    cached = _IMAGE_CACHE.get(key)
    if cached is not None:
        return cached

    s = SUPERSAMPLE
    w, h, r = max(1, int(width * s)), max(1, int(height * s)), radius * s
    image = _gradient_fill(w, h, color_from, color_to, direction).convert("RGBA")
    if border:
        bw = border_width * s
        framed = Image.new("RGBA", (w, h), border)
        inner = Image.new("L", (w, h), 0)
        ImageDraw.Draw(inner).rounded_rectangle(
            (bw, bw, w - 1 - bw, h - 1 - bw), radius=max(0, r - bw), fill=255)
        framed.paste(image, (0, 0), inner)
        image = framed
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=255)
    image.putalpha(mask)
    _IMAGE_CACHE[key] = image
    return image


def ring_image(size, thickness, ratio, color_from, color_to, track):
    """Fortschrittsring mit Farbverlauf und runden Enden (RGBA, SUPERSAMPLE)."""
    ratio = max(0.0, min(1.0, ratio))
    key = ("ring", size, thickness, round(ratio, 3), color_from, color_to, track)
    cached = _IMAGE_CACHE.get(key)
    if cached is not None:
        return cached

    s = SUPERSAMPLE
    full = int(size * s)
    width = int(thickness * s)
    pad = s
    image = Image.new("RGBA", (full, full), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    box = (pad, pad, full - pad, full - pad)
    draw.ellipse(box, outline=track, width=width)

    if ratio > 0:
        sweep = 360.0 * ratio
        steps = max(2, int(sweep / 2))
        for index in range(steps):
            start = -90 + sweep * index / steps
            end = -90 + sweep * (index + 1) / steps + 0.8
            color = mix(color_from, color_to, index / max(1, steps - 1))
            draw.arc(box, start, min(end, -90 + sweep), fill=color, width=width)
        # Runde Enden
        center = full / 2.0
        radius = (full - 2 * pad) / 2.0 - width / 2.0
        for angle, color in ((-90, color_from), (-90 + sweep, color_to)):
            rad = math.radians(angle)
            cx = center + radius * math.cos(rad)
            cy = center + radius * math.sin(rad)
            draw.ellipse((cx - width / 2, cy - width / 2, cx + width / 2,
                          cy + width / 2), fill=color)
    _IMAGE_CACHE[key] = image
    return image


def circle_image(diameter, fill=None, outline=None, outline_width=2, dot=None):
    """Kreis bzw. Radio-Markierung als RGBA-Bild (SUPERSAMPLE)."""
    key = ("circle", diameter, fill, outline, outline_width, dot)
    cached = _IMAGE_CACHE.get(key)
    if cached is not None:
        return cached
    s = SUPERSAMPLE
    size = int(diameter * s)
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((0, 0, size - 1, size - 1), fill=fill, outline=outline,
                 width=int(outline_width * s) if outline else 0)
    if dot:
        inset = size * 0.3
        draw.ellipse((inset, inset, size - 1 - inset, size - 1 - inset), fill=dot)
    _IMAGE_CACHE[key] = image
    return image


def ctk_image(image, width, height):
    """Verpackt ein Pillow-Bild als CTkImage (skaliert automatisch mit)."""
    key = ("ctk", id(image), width, height)
    cached = _IMAGE_CACHE.get(key)
    if cached is None:
        cached = ctk.CTkImage(light_image=image, dark_image=image,
                              size=(int(width), int(height)))
        _IMAGE_CACHE[key] = cached
    return cached


def tk_photo(image, width, height):
    """Rechnet ein Pillow-Bild auf echte Bildschirmpixel herunter und liefert
    ein PhotoImage fuer Tk-Canvas. Die Referenz muss der Aufrufer halten."""
    return ImageTk.PhotoImage(image.resize((max(1, int(width)), max(1, int(height))),
                                           Image.LANCZOS))


# ============================================================================
#  SYMBOLE
# ============================================================================

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
                cx, cy = left + size * col, top + size * row
                dot = size * 0.07
                canvas.create_oval(cx - dot, cy - dot, cx + dot, cy + dot,
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
        for cx, cy in points:
            canvas.create_line(x, y, cx, cy, fill=color, width=1,
                               **({"tags": tags} if tags else {}))
        for cx, cy in points:
            canvas.create_oval(cx - radius, cy - radius, cx + radius,
                               cy + radius, **fill_opts)

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

    elif name == "layers":         # AP1 Szenarien (Grundlagen)
        step = size * 0.22
        for i in range(3):
            oy = top + size * 0.18 + i * step
            canvas.create_polygon(x, oy,
                                  right, oy + size * 0.12,
                                  x, oy + size * 0.24,
                                  left, oy + size * 0.12,
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

    elif name == "database":      # Datenbanken
        rim = size * 0.32
        canvas.create_oval(left, top, right, top + rim, **fill_opts)
        canvas.create_line(left, top + rim / 2, left, bottom - rim / 2, **opts)
        canvas.create_line(right, top + rim / 2, right, bottom - rim / 2, **opts)
        canvas.create_arc(left, bottom - rim, right, bottom, start=180,
                          extent=180, style="arc", **line_opts)

    elif name == "office":        # Buero (Gebaeude mit Fenstern)
        canvas.create_rectangle(left + size * 0.14, top + size * 0.06,
                                right - size * 0.14, bottom, fill="", **line_opts)
        win = size * 0.07
        for dx in (0.36, 0.64):
            for dy in (0.28, 0.52):
                px_, py_ = left + size * dx, top + size * dy
                canvas.create_rectangle(px_ - win, py_ - win, px_ + win, py_ + win,
                                        **fill_opts)
        canvas.create_line(x, bottom - size * 0.2, x, bottom, **opts)

    elif name == "home":          # Zuhause (Haus mit Dach und Tuer)
        roof = top + size * 0.42
        canvas.create_line(left + size * 0.02, roof + size * 0.04, x, top + size * 0.04,
                           right - size * 0.02, roof + size * 0.04, **opts)
        canvas.create_rectangle(left + size * 0.16, roof, right - size * 0.16, bottom,
                                fill="", **line_opts)
        canvas.create_rectangle(x - size * 0.1, bottom - size * 0.3, x + size * 0.1,
                                bottom, **fill_opts)

    elif name == "station":       # Kunde (Zug von vorne)
        canvas.create_rectangle(left + size * 0.16, top + size * 0.04, right - size * 0.16,
                                bottom - size * 0.2, fill="", **line_opts)
        canvas.create_rectangle(left + size * 0.3, top + size * 0.18, right - size * 0.3,
                                top + size * 0.42, **fill_opts)
        dot = size * 0.07
        for dx in (0.34, 0.66):
            px_, py_ = left + size * dx, bottom - size * 0.38
            canvas.create_oval(px_ - dot, py_ - dot, px_ + dot, py_ + dot, **fill_opts)
        canvas.create_line(left + size * 0.22, bottom, left + size * 0.34,
                           bottom - size * 0.2, **opts)
        canvas.create_line(right - size * 0.22, bottom, right - size * 0.34,
                           bottom - size * 0.2, **opts)

    elif name == "game":          # Spiel (Gamepad)
        canvas.create_rectangle(left, top + size * 0.2, right, bottom - size * 0.16,
                                fill="", **line_opts)
        arm = size * 0.14
        cx, cy = left + size * 0.3, y + size * 0.02
        canvas.create_line(cx - arm, cy, cx + arm, cy, **opts)
        canvas.create_line(cx, cy - arm, cx, cy + arm, **opts)
        dot = size * 0.07
        for dx, dy in ((0.66, -0.06), (0.78, 0.1)):
            px_, py_ = left + size * dx, y + size * dy
            canvas.create_oval(px_ - dot, py_ - dot, px_ + dot, py_ + dot,
                               **fill_opts)

    elif name == "notebook":      # Notizblock (Block mit Ringen und Zeilen)
        canvas.create_rectangle(left + size * 0.12, top + size * 0.1, right - size * 0.12,
                                bottom, fill="", **line_opts)
        for dx in (0.32, 0.5, 0.68):
            px_ = left + size * dx
            canvas.create_line(px_, top, px_, top + size * 0.22, **opts)
        for dy in (0.46, 0.64, 0.82):
            py_ = top + size * dy
            canvas.create_line(left + size * 0.3, py_, right - size * 0.3, py_, **opts)

    elif name == "journey":       # Reise (Weg mit Start und Ziel)
        dot = size * 0.1
        canvas.create_oval(left + size * 0.08 - dot, bottom - size * 0.12 - dot,
                           left + size * 0.08 + dot, bottom - size * 0.12 + dot, **fill_opts)
        canvas.create_line(left + size * 0.08, bottom - size * 0.12, left + size * 0.5,
                           bottom - size * 0.2, left + size * 0.3, y, left + size * 0.72,
                           top + size * 0.34, smooth=True, **opts)
        canvas.create_line(right - size * 0.2, top + size * 0.44, right - size * 0.2, top,
                           **opts)
        canvas.create_polygon(right - size * 0.2, top, right + size * 0.08, top + size * 0.1,
                              right - size * 0.2, top + size * 0.22, **fill_opts)

    elif name == "search":
        radius = size * 0.32
        canvas.create_oval(x - radius - size * 0.1, y - radius - size * 0.1,
                           x + radius - size * 0.1, y + radius - size * 0.1,
                           fill="", **line_opts)
        canvas.create_line(x + radius - size * 0.22, y + radius - size * 0.22,
                           right, bottom, **opts)

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


# Symbole der Handy-App (Material Icons, gerundet) fuer die Seitenleiste am
# PC (ab 0.39). fisi_symbole.otf enthaelt nur diese Zeichen aus der Schrift
# "Material Icons" von Google (Apache-Lizenz 2.0, siehe
# fisi_symbole_LIZENZ.txt). Fehlt die Datei, zeichnet draw_icon() wie bisher.
SYMBOL_FONT_FILE = "fisi_symbole.otf"
SYMBOLS = {
    "dashboard": 0xF68E,
    "style": 0xF01E8,
    "track_changes": 0xF0248,
    "layers": 0xF847,
    "diamond": 0xF0306,
    "flag": 0xF768,
    "edit_note": 0xF030F,
    "calculate": 0xF5FD,
    "sports_esports": 0xF01BC,
    "insights": 0xF820,
    "settings": 0xF0164,
    "lan": 0xF034B,
    "security": 0xF013E,
    "dns": 0xF6C1,
    "euro": 0xF716,
    "storage": 0xF01DE,
    "business": 0xF5F8,
    "storefront": 0xF01E1,
    "home": 0xF7F5,
    "work": 0xF02C7,
    "route": 0xF0377,
}
_SYMBOL_FONTS = {}


def _symbol_font(size):
    if size not in _SYMBOL_FONTS:
        base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        try:
            _SYMBOL_FONTS[size] = ImageFont.truetype(os.path.join(base, SYMBOL_FONT_FILE),
                                                     size)
        except (OSError, ValueError):
            _SYMBOL_FONTS[size] = None
    return _SYMBOL_FONTS[size]


def symbol_image(name, size, color):
    """Ein Symbol der Handy-App als Bild (oder None, wenn es fehlt)."""
    key = ("symbol", name, size, color)
    if key in _IMAGE_CACHE:
        return _IMAGE_CACHE[key]
    font = _symbol_font(size)
    if font is None or name not in SYMBOLS:
        return None
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(image).text((size / 2.0, size / 2.0), chr(SYMBOLS[name]), font=font,
                               fill=color, anchor="mm")
    _IMAGE_CACHE[key] = image
    return image


class IconCanvas(tk.Canvas):
    """Kleine Flaeche fuer ein einzelnes Symbol aus draw_icon() - oder, mit
    symbol=..., fuer ein Symbol der Handy-App."""

    def __init__(self, parent, icon, size=20, color=None, icon_scale=0.72,
                 parent_bg=None, cursor="", symbol=None):
        self.icon = icon
        self.symbol = symbol
        self._photo = None
        self.size = size
        self.icon_scale = icon_scale
        super().__init__(parent, width=px(size), height=px(size),
                         bg=parent_bg or _bg_of(parent), highlightthickness=0,
                         bd=0, cursor=cursor)
        self.paint(color or C["muted"])

    def paint(self, color, icon=None):
        if icon:
            self.icon = icon
        self.delete("all")
        box = px(self.size)
        # Unterpunkte (kleinere icon_scale) bekommen entsprechend kleinere Symbole
        image = symbol_image(self.symbol, int(round(box * min(1.0, self.icon_scale / 0.72))),
                             color) if self.symbol else None
        if image is not None:
            self._photo = ImageTk.PhotoImage(image)
            self.create_image(box / 2, box / 2, image=self._photo)
            return
        draw_icon(self, self.icon, box / 2, box / 2, box * self.icon_scale,
                  color, width=max(2, px(2)))


# ============================================================================
#  BUTTONS
# ============================================================================

# Symbole fuer Buttons (als Textzeichen, die jede verbreitete Schrift kennt)
BUTTON_GLYPHS = {"arrow_left": "←", "arrow_right": "→"}


class NeoButton(ctk.CTkLabel):
    """Button mit abgerundeten Ecken und Farbverlauf.

    CTkButton kennt keine Verlaeufe - deshalb ein CTkLabel, das ein mit
    Pillow gerendertes Verlaufsbild zeigt und den Text darueberlegt.

    kind: primary, accent, danger (Verlauf), ghost (dezent), pill (Auswahl)
    """

    def __init__(self, parent, text, command=None, kind="primary",
                 width=None, height=38, radius=None, font=None, parent_bg=None,
                 icon=None):
        self.command = command
        self.kind = kind
        self.btn_font = font or F["body_bold"]
        self.btn_height = height
        self.radius = height / 2 if radius is None else radius
        self.icon = icon
        self.fixed_width = width
        self._enabled = True
        self._hovering = False
        self._active = False
        self._caption = self._compose(text)
        super().__init__(parent, text=self._caption, font=self.btn_font,
                         compound="center", cursor="hand2",
                         fg_color=parent_bg or "transparent",
                         width=self._button_width(), height=height)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self._render()

    # -- Darstellung --------------------------------------------------------

    def _compose(self, text):
        glyph = BUTTON_GLYPHS.get(self.icon)
        return "%s  %s" % (glyph, text) if glyph else text

    def _button_width(self):
        if self.fixed_width:
            return self.fixed_width
        return int(text_width(self._caption, self.btn_font) + 44)

    def _palette(self):
        """Liefert (Verlauf von, Verlauf nach, Rahmen, Textfarbe)."""
        if not self._enabled:
            return C["card_alt"], C["card_alt"], C["border"], C["muted"]
        if self.kind in ("primary", "accent", "danger") or (
                self.kind == "pill" and self._active):
            start, end = GRADIENTS["primary" if self.kind == "pill" else self.kind]
            if self._hovering:
                start, end = lighten(start, 0.14), lighten(end, 0.14)
            return start, end, None, C["on_accent"]
        if self.kind == "pill":
            fill = C["card_hi"] if self._hovering else C["card_alt"]
            return fill, fill, C["border_hi"] if self._hovering else C["border"], C["text_dim"]
        # ghost
        fill = C["card_hi"] if self._hovering else C["card_alt"]
        return fill, fill, C["border_hi"] if self._hovering else C["border"], C["text"]

    def _render(self):
        width = self._button_width()
        start, end, border, fg = self._palette()
        image = rounded_gradient(width, self.btn_height, self.radius, start, end,
                                 border=border)
        self.configure(image=ctk_image(image, width, self.btn_height),
                       text=self._caption, text_color=fg, width=width,
                       height=self.btn_height)

    # -- Verhalten ----------------------------------------------------------

    def _on_enter(self, _event=None):
        if not self._hovering:
            self._hovering = True
            self._render()

    def _on_leave(self, _event=None):
        if self._hovering:
            self._hovering = False
            self._render()

    def _on_click(self, _event=None):
        if self._enabled and self.command:
            self.command()

    def set_enabled(self, flag):
        self._enabled = bool(flag)
        self.configure(cursor="hand2" if flag else "arrow")
        self._render()

    def set_active(self, flag):
        self._active = bool(flag)
        self._render()

    def set_text(self, text):
        self._caption = self._compose(text)
        self._render()


class IconButton(tk.Canvas):
    """Kleiner, runder Symbolknopf (z.B. Pfeile im Kalender)."""

    def __init__(self, parent, icon, command=None, size=30, parent_bg=None,
                 color=None, icon_size=None, press_color=None):
        self.parent_bg = parent_bg or _bg_of(parent)
        self.icon = icon
        self.command = command
        self.size = size
        self.icon_size = icon_size or size * 0.46
        self.color = color or C["text_dim"]
        # Optionale Farbe, solange die Maustaste gedrueckt gehalten wird
        self.press_color = press_color
        self._hover = False
        self._pressed = False
        self._photos = {}
        super().__init__(parent, width=px(size), height=px(size),
                         bg=self.parent_bg, highlightthickness=0, bd=0,
                         cursor="hand2")
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", lambda e: self._set_pressed(False))
        self._draw()

    def _on_press(self, _event=None):
        self._set_pressed(True)
        if self.command:
            self.command()

    def _set_pressed(self, flag):
        if self.press_color:
            self._pressed = flag
            self._draw()

    def _set_hover(self, flag):
        self._hover = flag
        if not flag:
            self._pressed = False
        self._draw()

    def _draw(self):
        self.delete("all")
        size = px(self.size)
        fill = C["card_hi"] if self._hover else C["card_alt"]
        photo = self._photos.get(fill)
        if photo is None:
            photo = tk_photo(circle_image(self.size, fill=fill), size, size)
            self._photos[fill] = photo
        self.create_image(size / 2, size / 2, image=photo)
        if self._pressed:
            icon_color = self.press_color
        elif self._hover:
            icon_color = C["accent"]
        else:
            icon_color = self.color
        draw_icon(self, self.icon, size / 2, size / 2, px(self.icon_size),
                  icon_color, width=max(2, px(2)))


# ============================================================================
#  KARTE (GRUNDBAUSTEIN DES DASHBOARDS)
# ============================================================================

class Card(ctk.CTkFrame):
    """Dunkle, abgerundete Kachel mit optionaler Ueberschrift.

    Die Ueberschrift bekommt links einen kleinen senkrechten Farbverlauf in
    der Akzentfarbe der Kachel.
    """

    def __init__(self, parent, title=None, subtitle=None, accent=None,
                 pad=18, bg=None):
        self.bg = bg or C["card"]
        super().__init__(parent, fg_color=self.bg, corner_radius=16,
                         border_width=1, border_color=C["border"])
        self.head = None
        self.title_label = None
        self.subtitle_label = None
        if title:
            color = accent or C["accent"]
            self.head = ctk.CTkFrame(self, fg_color="transparent")
            self.head.pack(fill="x", padx=pad, pady=(pad - 2, 0))
            tick = rounded_gradient(4, 14, 2, lighten(color, 0.2),
                                    mix(color, self.bg, 0.45), direction="v")
            ctk.CTkLabel(self.head, text="", image=ctk_image(tick, 4, 14),
                         width=4, height=14).pack(side="left", padx=(0, 9))
            self.title_label = ctk.CTkLabel(self.head, text=title.upper(),
                                            text_color=color, font=F["label"],
                                            anchor="w", height=0)
            self.title_label.pack(side="left")
            # Die Unterschrift wird immer angelegt, damit sie spaeter ohne
            # zusaetzliche Widgets geaendert werden kann.
            self.subtitle_label = ctk.CTkLabel(self.head, text=subtitle or "",
                                               text_color=C["muted"],
                                               font=F["tiny"], anchor="e",
                                               height=0)
            self.subtitle_label.pack(side="right")
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=pad,
                       pady=(12 if title else pad, pad))

    def set_subtitle(self, text, color=None):
        """Aendert die Unterschrift der Kachel zur Laufzeit."""
        if self.subtitle_label is not None:
            self.subtitle_label.configure(text=text, text_color=color or C["muted"])


# ============================================================================
#  BANNER MIT FARBVERLAUF
# ============================================================================

class GradientPanel(tk.Canvas):
    """Breites Banner mit diagonalem Farbverlauf, Titel und Kennzahl."""

    def __init__(self, parent, height=128, gradient=None, parent_bg=None):
        self.bg = parent_bg or _bg_of(parent)
        self.gradient = gradient or GRADIENTS["hero"]
        self.panel_height = height
        self._texts = ("", "", "", "")
        self._photo = None
        self._size = None
        self._job = None
        super().__init__(parent, height=px(height), width=px(160), bg=self.bg,
                         highlightthickness=0, bd=0)
        self.bind("<Configure>", self._schedule)

    def set_data(self, title, subtitle, big="", big_sub=""):
        self._texts = (title, subtitle, big, big_sub)
        self._draw()

    def _schedule(self, _event=None):
        # Beim Ziehen des Fensters nicht bei jedem Pixel neu rendern
        if self._job is not None:
            self.after_cancel(self._job)
        self._job = self.after(40, self._draw)

    def _draw(self):
        self._job = None
        width, height = self.winfo_width(), self.winfo_height()
        if width <= 1:
            return
        if self._size != (width, height):
            logical_w = width / _SCALE[0]
            image = rounded_gradient(logical_w, self.panel_height, 18,
                                     self.gradient[0], self.gradient[1],
                                     direction="d")
            self._photo = tk_photo(image, width, height)
            self._size = (width, height)
        self.delete("all")
        self.create_image(0, 0, image=self._photo, anchor="nw")
        # dezente Kreise als Dekoration im Verlauf
        for cx, cy, r, alpha in ((0.86, 0.1, 0.55, 0.10), (0.97, 0.95, 0.4, 0.08)):
            radius = height * r
            color = mix(self.gradient[1], "#FFFFFF", alpha)
            self.create_oval(width * cx - radius, height * cy - radius,
                             width * cx + radius, height * cy + radius,
                             outline=color, width=max(1, px(2)))
        title, subtitle, big, big_sub = self._texts
        left = px(28)
        self.create_text(left, height * 0.36, text=title, anchor="w",
                         fill=C["on_accent"], font=tk_font(F["h1"]))
        self.create_text(left, height * 0.66, text=subtitle, anchor="w",
                         fill=mix(C["on_accent"], self.gradient[0], 0.25),
                         font=tk_font(F["body"]))
        if big:
            right = width - px(34)
            self.create_text(right, height * 0.40, text=big, anchor="e",
                             fill=C["on_accent"], font=tk_font(F["display"]))
            self.create_text(right, height * 0.72, text=big_sub, anchor="e",
                             fill=mix(C["on_accent"], self.gradient[1], 0.25),
                             font=tk_font(F["small"]))


# ============================================================================
#  RING-DIAGRAMME
# ============================================================================

class RingStat(tk.Canvas):
    """Fortschrittsring mit Farbverlauf und Beschriftung in der Mitte."""

    def __init__(self, parent, size=128, thickness=11, segments=None,
                 parent_bg=None):
        self.bg = parent_bg or _bg_of(parent)
        self.size = size
        self.thickness = thickness
        self._data = (0.0, C["accent"], C["accent2"], "", "")
        self._photo = None
        super().__init__(parent, width=px(size), height=px(size), bg=self.bg,
                         highlightthickness=0, bd=0)
        self._draw()

    def set(self, ratio, color_from=None, color_to=None, big="", small=""):
        self._data = (max(0.0, min(1.0, ratio)),
                      color_from or C["accent"], color_to or C["accent2"],
                      big, small)
        self._draw()

    def _draw(self):
        self.delete("all")
        ratio, color_from, color_to, big, small = self._data
        size = px(self.size)
        image = ring_image(self.size, self.thickness, ratio, color_from,
                           color_to, C["ring_bg"])
        self._photo = tk_photo(image, size, size)
        self.create_image(size / 2, size / 2, image=self._photo)
        center = size / 2
        if big:
            offset = -px(8) if small else 0
            self.create_text(center, center + offset, text=big, fill=C["text"],
                             font=tk_font(F["ring_big"]))
        if small:
            self.create_text(center, center + px(15), text=small, fill=C["muted"],
                             font=tk_font(F["ring_small"]))


class MiniRing(tk.Canvas):
    """Kleiner Ring mit Prozentwert - fuer Fachbereiche."""

    def __init__(self, parent, size=74, thickness=7, parent_bg=None):
        self.bg = parent_bg or _bg_of(parent)
        self.size = size
        self.thickness = thickness
        self._pct = 0.0
        self._color = C["accent"]
        self._photo = None
        super().__init__(parent, width=px(size), height=px(size), bg=self.bg,
                         highlightthickness=0, bd=0)
        self._draw()

    def set(self, pct, color):
        self._pct = max(0.0, min(100.0, pct))
        self._color = color
        self._draw()

    def _draw(self):
        self.delete("all")
        size = px(self.size)
        image = ring_image(self.size, self.thickness, self._pct / 100.0,
                           mix(self._color, C["card"], 0.35), self._color,
                           C["ring_bg"])
        self._photo = tk_photo(image, size, size)
        self.create_image(size / 2, size / 2, image=self._photo)
        self.create_text(size / 2, size / 2, text="%d%%" % round(self._pct),
                         fill=C["text"], font=tk_font(F["small_bold"]))


# ============================================================================
#  FORTSCHRITTSBALKEN
# ============================================================================

class GradientBar(tk.Canvas):
    """Beschrifteter, abgerundeter Balken mit Farbverlauf."""

    def __init__(self, parent, label, color_from, color_to, height=46,
                 parent_bg=None):
        self.bg = parent_bg or _bg_of(parent)
        self.label = label
        self.color_from = color_from
        self.color_to = color_to
        self._pct = 0.0
        self._note = ""
        self._photos = []
        super().__init__(parent, height=px(height), width=px(160), bg=self.bg,
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
        self.create_text(0, px(9), text=self.label, anchor="w", fill=C["text_dim"],
                         font=tk_font(F["small"]))
        self.create_text(width, px(9), text=self._note, anchor="e", fill=C["muted"],
                         font=tk_font(F["small"]))
        top, bar_h = px(24), px(9)
        logical_w = width / _SCALE[0]
        track = rounded_gradient(logical_w, 9, 4.5, C["ring_bg"], C["ring_bg"])
        self._photos = [tk_photo(track, width, bar_h)]
        self.create_image(0, top, image=self._photos[0], anchor="nw")
        filled = logical_w * (self._pct / 100.0)
        if filled >= 9:
            bar = rounded_gradient(int(filled), 9, 4.5, self.color_from,
                                   self.color_to)
            self._photos.append(tk_photo(bar, px(int(filled)), bar_h))
            self.create_image(0, top, image=self._photos[1], anchor="nw")


# ============================================================================
#  LINIENDIAGRAMM
# ============================================================================

def _nice_step(raw):
    """Glatte Schrittweite fuer eine Achse, mindestens 1."""
    if raw <= 1:
        return 1
    power = 10 ** math.floor(math.log10(raw))
    for factor in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        step = factor * power
        if raw <= step and step == int(step):
            return int(step)
    return int(10 * power)


def _axis_text(value):
    """Achsenbeschriftung mit Tausenderpunkt (12.500 statt 12500)."""
    if value == int(value):
        return "{:,}".format(int(value)).replace(",", ".")
    return ("%g" % value).replace(".", ",")


class LineChart(tk.Canvas):
    """Liniendiagramm mit gefuellter Flaeche und Gitternetz."""

    def __init__(self, parent, height=220, parent_bg=None):
        self.bg = parent_bg or _bg_of(parent)
        self._labels = []
        self._series = []
        self._y_max = None
        self._photos = []
        super().__init__(parent, height=px(height), width=px(160), bg=self.bg,
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

        if self._y_max:
            peak = float(self._y_max)
            step = peak / 4.0
        else:
            peak = 0
            for item in self._series:
                if item["values"]:
                    peak = max(peak, max(item["values"]))
            peak = max(5, peak)
            # auf eine glatte Zahl aufrunden (1, 2, 2,5 oder 5 mal Zehnerpotenz)
            step = _nice_step(peak / 4.0)
            peak = step * 4
        y_texts = [_axis_text(step * line) for line in range(5)]

        # Der linke Rand richtet sich nach der breitesten y-Beschriftung, damit
        # auch sechsstellige Betraege (Kontostand) nicht abgeschnitten werden
        widest = max(text_width(text, F["tiny"]) for text in y_texts)
        left = max(px(42), int(widest * _SCALE[0]) + px(16))
        right, top, bottom = px(14), px(22), px(30)
        plot_w = width - left - right
        plot_h = height - top - bottom
        if plot_w <= 10 or plot_h <= 10:
            return

        # Gitternetz und y-Achse
        for line in range(5):
            y = top + plot_h - (plot_h * line / 4)
            self.create_line(left, y, width - right, y, fill=C["border"],
                             dash=(2, 4) if line else ())
            self.create_text(left - px(8), y, text=y_texts[line], anchor="e",
                             fill=C["muted"], font=tk_font(F["tiny"]))

        count = len(self._labels)
        if count == 1:
            positions = [left + plot_w / 2]
        else:
            positions = [left + plot_w * i / (count - 1) for i in range(count)]

        # x-Beschriftung ausduennen, damit nichts ueberlappt
        stride = max(1, int(count / max(1, plot_w / px(55))))
        shown = [index for index in range(count) if index % stride == 0 or index == count - 1]
        if len(shown) > 1:
            # Die letzte Beschriftung endet am rechten Rand statt darueber; die
            # davor faellt weg, wenn sie sonst ueberlappen wuerde
            last_left = positions[-1] + px(6) - text_width(
                str(self._labels[-1]), F["tiny"]) * _SCALE[0]
            before = shown[-2]
            before_right = positions[before] + text_width(
                str(self._labels[before]), F["tiny"]) * _SCALE[0] / 2
            if before_right + px(4) > last_left:
                shown.remove(before)
        for index, label in enumerate(self._labels):
            if index in shown:
                last = index == count - 1 and count > 1
                self.create_text(positions[index] + (px(6) if last else 0),
                                 height - bottom + px(15), text=label,
                                 anchor="e" if last else "center", fill=C["muted"],
                                 font=tk_font(F["tiny"]))

        self._photos = []
        base_y = top + plot_h
        for item in self._series:
            values = item["values"]
            color = item["color"]
            if not values:
                continue
            points = [(positions[index], top + plot_h - (plot_h * (value / peak)))
                      for index, value in enumerate(values)]
            curve = _smooth_curve(points, base_y, top)

            if len(curve) >= 2:
                self._draw_area(curve, color, left, top, width - right, base_y)
                self.create_line([coord for point in curve for coord in point],
                                 fill=color, width=max(2, px(2.5)),
                                 capstyle="round", joinstyle="round")
            dot = px(4)
            for index, (x, y) in enumerate(points):
                if values[index] > 0:
                    self.create_oval(x - dot, y - dot, x + dot, y + dot,
                                     fill=color, outline=self.bg, width=px(2))

        # Legende
        legend_x = left + px(4)
        for item in self._series:
            self.create_oval(legend_x, top - px(14), legend_x + px(8), top - px(6),
                             fill=item["color"], outline="")
            self.create_text(legend_x + px(14), top - px(10), text=item["name"],
                             anchor="w", fill=C["text_dim"], font=tk_font(F["tiny"]))
            legend_x += px(24) + text_width(item["name"], F["tiny"]) * _SCALE[0]

    def _draw_area(self, curve, color, x1, y1, x2, y2):
        """Flaeche unter der Kurve mit senkrechtem Verlauf, der nach unten
        in den Hintergrund auslaeuft (als kantengeglaettetes Pillow-Bild)."""
        width, height = int(x2 - x1), int(y2 - y1)
        if width < 2 or height < 2:
            return
        s = 2
        shape = [((x - x1) * s, (y - y1) * s) for x, y in curve]
        shape += [((curve[-1][0] - x1) * s, height * s), ((curve[0][0] - x1) * s, height * s)]
        mask = Image.new("L", (width * s, height * s), 0)
        ImageDraw.Draw(mask).polygon(shape, fill=255)
        fade = Image.linear_gradient("L").transpose(Image.FLIP_TOP_BOTTOM)
        fade = fade.resize((width * s, height * s)).point(lambda v: int(v * 0.42))
        alpha = Image.composite(fade, Image.new("L", mask.size, 0), mask)
        image = Image.new("RGBA", mask.size, color)
        image.putalpha(alpha)
        photo = tk_photo(image, width, height)
        self._photos.append(photo)
        self.create_image(x1, y1, image=photo, anchor="nw")


def _smooth_curve(points, floor, ceiling, steps=12):
    """Catmull-Rom-Kurve durch alle Punkte - anders als Tk-smooth laeuft sie
    exakt durch die Messwerte, die Punkte liegen also auf der Linie."""
    if len(points) < 3:
        return list(points)
    curve = []
    padded = [points[0]] + list(points) + [points[-1]]
    for i in range(1, len(padded) - 2):
        p0, p1, p2, p3 = padded[i - 1], padded[i], padded[i + 1], padded[i + 2]
        for step in range(steps):
            t = step / float(steps)
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t
                       + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                       + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t
                       + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                       + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            # Die Kurve darf nicht unter die Nulllinie oder ueber den Rand schwingen
            curve.append((x, max(ceiling, min(floor, y))))
    curve.append(points[-1])
    return curve


# ============================================================================
#  HEATMAP
# ============================================================================

class Heatmap(tk.Canvas):
    """Farbgitter: eine Zeile je Fachbereich (oder Thema), eine Spalte je Tag.

    on_click(index) macht die Zeilen anklickbar (Reinzoom in die Themen);
    die ausgewaehlte Zeile wird hervorgehoben."""

    def __init__(self, parent, height=200, parent_bg=None, on_click=None, label_w=98):
        self.bg = parent_bg or _bg_of(parent)
        self._rows = []
        self._columns = 0
        self._photos = []
        self._row_spans = []
        self._selected = None
        self._on_click = on_click
        self._label_w = label_w
        super().__init__(parent, height=px(height), width=px(160), bg=self.bg,
                         highlightthickness=0, bd=0,
                         cursor="hand2" if on_click else "")
        self.bind("<Configure>", lambda e: self._draw())
        if on_click:
            self.bind("<Button-1>", self._click)

    def set_data(self, rows, columns, selected=None):
        """rows: Liste von (label, color, [werte]); selected: hervorgehobene Zeile."""
        self._rows = rows
        self._columns = columns
        self._selected = selected
        self._draw()

    def _click(self, event):
        for index, (top, bottom) in enumerate(self._row_spans):
            if top - px(3) <= event.y <= bottom + px(3):
                self._on_click(index)
                return

    def _draw(self):
        self.delete("all")
        self._photos = []
        self._row_spans = []
        width = self.winfo_width()
        height = self.winfo_height()
        if width <= 1 or height <= 1 or not self._rows or not self._columns:
            return

        label_w = px(self._label_w)
        grid_x = label_w
        grid_w = width - label_w - px(4)
        gap = px(4)
        count = max(1, len(self._rows))
        row_h = min(px(34), (height - px(16)) / count - gap)
        if px(8) + count * (row_h + gap * 2) > height:
            # Viele Zeilen (Themen): so eng setzen, dass die letzte noch passt
            row_h = (height - px(8)) / count - gap * 2
        cell_w = grid_w / self._columns
        peak = 1
        for _label, _color, values in self._rows:
            if values:
                peak = max(peak, max(values))

        for row_index, (label, color, values) in enumerate(self._rows):
            y = px(8) + row_index * (row_h + gap * 2)
            self._row_spans.append((y, y + row_h))
            chosen = row_index == self._selected
            self.create_text(0, y + row_h / 2, text=label, anchor="w",
                             fill=color if chosen else C["text_dim"],
                             font=tk_font(F["small_bold"] if chosen else F["small"]))
            for col in range(self._columns):
                value = values[col] if col < len(values) else 0
                intensity = 0.0 if peak == 0 else min(1.0, value / peak)
                cell = C["ring_bg"] if value == 0 else mix(darken_bg(color), color, intensity)
                x1 = grid_x + col * cell_w
                w_cell, h_cell = int(cell_w - 2 * max(1, px(1.5))), int(row_h)
                if w_cell < 2 or h_cell < 2:
                    continue
                image = rounded_gradient(w_cell / _SCALE[0], h_cell / _SCALE[0], 4,
                                         cell, cell)
                photo = tk_photo(image, w_cell, h_cell)
                self._photos.append(photo)
                self.create_image(x1 + max(1, px(1.5)), y, image=photo, anchor="nw")


def darken_bg(color):
    return mix(C["ring_bg"], color, 0.25)


# ============================================================================
#  KALENDER
# ============================================================================

class CalendarPanel(ctk.CTkFrame):
    """Monatskalender, der Lerntage hervorhebt."""

    WEEKDAYS = ["M", "D", "M", "D", "F", "S", "S"]

    def __init__(self, parent, bg=None):
        self.bg = bg or C["card"]
        super().__init__(parent, fg_color="transparent")
        today = datetime.date.today()
        self.year = today.year
        self.month = today.month
        self._active_days = set()
        self._provider = None
        self._photos = {}

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x")
        IconButton(header, "arrow_left", self._prev_month, parent_bg=self.bg,
                   color=C["accent"], press_color=C["green"]).pack(side="left")
        self.lbl_month = ctk.CTkLabel(header, text="", text_color=C["text"],
                                      font=F["h3"], height=0)
        self.lbl_month.pack(side="left", expand=True)
        IconButton(header, "arrow_right", self._next_month, parent_bg=self.bg,
                   color=C["accent"], press_color=C["green"]).pack(side="right")

        self.canvas = tk.Canvas(self, bg=self.bg, highlightthickness=0, bd=0,
                                height=px(190), width=px(160))
        self.canvas.pack(fill="both", expand=True, pady=(8, 0))
        self.canvas.bind("<Configure>", lambda e: self._draw_days())

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
        self.lbl_month.configure(text="%s %d" % (self._month_name(), self.year))
        self._draw_days()

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

    def _circle(self, diameter, **style):
        key = (diameter, tuple(sorted(style.items())))
        photo = self._photos.get(key)
        if photo is None:
            logical = diameter / _SCALE[0]
            photo = tk_photo(circle_image(logical, **style), diameter, diameter)
            self._photos[key] = photo
        return photo

    def _draw_days(self):
        self.canvas.delete("all")
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width <= 1:
            return

        cell_w = width / 7.0
        cell_h = max(px(22), min(px(27), (height - px(24)) / 6.0))
        today = datetime.date.today()

        for index, day in enumerate(self.WEEKDAYS):
            color = C["accent2"] if index >= 5 else C["muted"]
            self.canvas.create_text(cell_w * index + cell_w / 2, px(8), text=day,
                                    fill=color, font=tk_font(F["tiny"]))

        weeks = calmod.Calendar(firstweekday=0).monthdayscalendar(self.year, self.month)
        diameter = int(min(cell_w, cell_h) - px(3))
        for row, week in enumerate(weeks):
            for col, day in enumerate(week):
                if day == 0:
                    continue
                cx = cell_w * col + cell_w / 2
                cy = px(26) + row * cell_h + cell_h / 2
                is_today = (day == today.day and self.month == today.month
                            and self.year == today.year)
                active = day in self._active_days
                if active:
                    self.canvas.create_image(cx, cy, image=self._circle(
                        diameter, fill=C["purple"]))
                if is_today:
                    self.canvas.create_image(cx, cy, image=self._circle(
                        diameter, outline=C["accent"], outline_width=2))
                if active:
                    color = "#12071F"
                elif col >= 5:
                    color = C["accent2"]
                else:
                    color = C["text_dim"]
                self.canvas.create_text(cx, cy, text=str(day), fill=color,
                                        font=tk_font(F["small_bold"] if active
                                                     else F["small"]))


# ============================================================================
#  TIMELINE
# ============================================================================

class ThemeTimeline(tk.Canvas):
    """Fortschrittsleiste der Pruefungsthemen: Ringe plus verbindende Achse."""

    def __init__(self, parent, height=190, parent_bg=None):
        self.bg = parent_bg or _bg_of(parent)
        self._items = []
        self._photos = []
        super().__init__(parent, height=px(height), width=px(160), bg=self.bg,
                         highlightthickness=0, bd=0)
        self.bind("<Configure>", lambda e: self._draw())

    def set_data(self, items):
        """items: Liste von (label, prozent, farbe)."""
        self._items = items
        self._draw()

    def _draw(self):
        self.delete("all")
        self._photos = []
        width = self.winfo_width()
        height = self.winfo_height()
        if width <= 1 or not self._items:
            return

        count = len(self._items)
        slot = width / count
        ring_r = min(px(32), slot / 2 - px(10), (height - px(90)) / 2)
        ring_r = max(px(18), ring_r)
        ring_cy = px(12) + ring_r
        line_y = ring_cy + ring_r + px(26)

        self.create_line(slot / 2, line_y, width - slot / 2, line_y,
                         fill=C["border_hi"], width=max(2, px(2)))

        for index, (label, pct, color) in enumerate(self._items):
            cx = slot * index + slot / 2
            diameter = int(ring_r * 2)
            image = ring_image(diameter / _SCALE[0], 6, pct / 100.0,
                               mix(color, C["card"], 0.35), color, C["ring_bg"])
            photo = tk_photo(image, diameter, diameter)
            self._photos.append(photo)
            self.create_image(cx, ring_cy, image=photo)
            self.create_text(cx, ring_cy, text="%d%%" % round(pct), fill=C["text"],
                             font=tk_font(F["small_bold"]))
            dot = px(12) if pct > 0 else px(10)
            dot_photo = tk_photo(circle_image(
                dot / _SCALE[0], fill=color if pct > 0 else C["ring_bg"],
                outline=self.bg, outline_width=2), dot, dot)
            self._photos.append(dot_photo)
            self.create_image(cx, line_y, image=dot_photo)
            self._wrapped_text(cx, line_y + px(17), label, slot - px(8))

    def _wrapped_text(self, x, y, text, max_width):
        words = text.split()
        lines, current = [], ""
        font = tkfont.Font(font=tk_font(F["tiny"]))
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
            self.create_text(x, y + offset * px(14), text=line, fill=C["muted"],
                             font=tk_font(F["tiny"]))


# ============================================================================
#  ANTWORTOPTIONEN (MULTIPLE CHOICE)
# ============================================================================

class OptionList(ctk.CTkFrame):
    """Anklickbare, abgerundete Antwortzeilen statt klassischer Radiobuttons."""

    def __init__(self, parent, bg=None, on_change=None):
        self.bg = bg or C["card"]
        super().__init__(parent, fg_color="transparent")
        self.on_change = on_change
        self._rows = []
        self._selected = None
        self._locked = False
        self._wrap = 640
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
        frame = ctk.CTkFrame(self, fg_color=C["card_alt"], corner_radius=12,
                             border_width=1, border_color=C["border"],
                             cursor="hand2")
        frame.pack(fill="x", pady=4)

        marker = ctk.CTkLabel(frame, text="", width=20, height=20, cursor="hand2")
        marker.pack(side="left", padx=(14, 10), pady=12)

        label = ctk.CTkLabel(frame, text=text, text_color=C["text_soft"],
                             font=F["body"], justify="left", anchor="w",
                             wraplength=self._wrap, cursor="hand2", height=0)
        label.pack(side="left", fill="x", expand=True, padx=(0, 14), pady=11)

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
            for widget in (row["frame"], row["marker"], row["label"]):
                widget.configure(cursor="arrow")
            self._paint(row)

    def _hover(self, row, flag):
        if self._locked or row["state"] == "selected":
            return
        row["frame"].configure(border_color=C["border_hi"] if flag else C["border"],
                               fg_color=C["card_hi"] if flag else C["card_alt"])

    def _paint(self, row):
        state = row["state"]
        if state == "selected":
            bg, border, fg, dot = C["card_hi"], C["purple"], C["text_soft"], C["purple"]
        elif state == "correct":
            bg, border, fg, dot = mix(C["card"], C["green"], 0.18), C["green"], C["text_soft"], C["green"]
        elif state == "wrong":
            bg, border, fg, dot = mix(C["card"], C["red"], 0.18), C["red"], C["text_soft"], C["red"]
        elif state == "muted":
            bg, border, fg, dot = C["card_alt"], C["border"], C["muted"], None
        else:
            bg, border, fg, dot = C["card_alt"], C["border"], C["text_soft"], None

        row["frame"].configure(fg_color=bg, border_color=border,
                               border_width=2 if state in ("selected", "correct", "wrong") else 1)
        row["label"].configure(text_color=fg)
        ring = border if state != "idle" else C["border_hi"]
        image = circle_image(20, outline=ring, outline_width=2, dot=dot)
        row["marker"].configure(image=ctk_image(image, 20, 20))

    def _on_resize(self, event):
        wrap = max(200, int(event.width / _SCALE[0]) - 90)
        if wrap == self._wrap:
            return
        self._wrap = wrap
        for row in self._rows:
            row["label"].configure(wraplength=wrap)


# ============================================================================
#  SCROLLBARER BEREICH
# ============================================================================

class ScrollArea(tk.Frame):
    """Senkrecht UND waagerecht scrollbarer Container fuer lange/breite
    Ansichten. Bei einem zu schmalen Fenster wird der Inhalt nicht mehr
    zusammengequetscht, sondern behaelt seine natuerliche Mindestbreite und
    laesst sich stattdessen ueber den unteren Schieberegler seitlich
    verschieben (bzw. mit gedrueckter Umschalttaste + Mausrad). Der untere
    Schieberegler erscheint nur, wenn er gebraucht wird."""

    def __init__(self, parent, bg=None):
        self.bg = bg or C["bg"]
        super().__init__(parent, bg=self.bg)
        self.canvas = tk.Canvas(self, bg=self.bg, highlightthickness=0, bd=0,
                                yscrollincrement=px(24), xscrollincrement=px(24))
        self.scrollbar = ctk.CTkScrollbar(
            self, orientation="vertical", command=self.canvas.yview,
            fg_color=self.bg, button_color=C["scrollbar"],
            button_hover_color=C["scrollbar_hi"])
        self.hscrollbar = ctk.CTkScrollbar(
            self, orientation="horizontal", command=self.canvas.xview,
            fg_color=self.bg, button_color=C["scrollbar"],
            button_hover_color=C["scrollbar_hi"])
        self.canvas.configure(yscrollcommand=self.scrollbar.set,
                              xscrollcommand=self._set_hscroll)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 2))
        self.hscrollbar.grid(row=1, column=0, sticky="ew")
        self.hscrollbar.grid_remove()
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.inner = tk.Frame(self.canvas, bg=self.bg)
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.bind("<Enter>", lambda e: self._bind_wheel(True))
        self.bind("<Leave>", lambda e: self._bind_wheel(False))

    def _set_hscroll(self, first, last):
        self.hscrollbar.set(first, last)
        if float(first) <= 0.0 and float(last) >= 1.0:
            self.hscrollbar.grid_remove()
        else:
            self.hscrollbar.grid()

    def _on_inner_configure(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        # Der Inhalt wird nur bis zur Fensterbreite gestreckt, wenn er von
        # Natur aus schmaler ist als das Fenster. Braucht er mehr Platz
        # (z.B. mehrspaltige Kacheln bei schmalem Fenster), behaelt er seine
        # benoetigte Breite und wird ueber den horizontalen Balken erreichbar,
        # statt zusammengequetscht zu werden.
        needed = self.inner.winfo_reqwidth()
        self.canvas.itemconfigure(self._window, width=max(event.width, needed))

    def _bind_wheel(self, flag):
        if flag:
            self.canvas.bind_all("<MouseWheel>", self._on_wheel)
            self.canvas.bind_all("<Shift-MouseWheel>", self._on_wheel_shift)
            self.canvas.bind_all("<Button-4>", self._on_wheel)
            self.canvas.bind_all("<Button-5>", self._on_wheel)
        else:
            self.canvas.unbind_all("<MouseWheel>")
            self.canvas.unbind_all("<Shift-MouseWheel>")
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
        self.canvas.yview_scroll(delta * 2, "units")

    def _on_wheel_shift(self, event):
        """Umschalttaste + Mausrad scrollt waagerecht statt senkrecht."""
        first, last = self.canvas.xview()
        if first <= 0.0 and last >= 1.0:
            return
        delta = -1 if event.delta > 0 else 1
        self.canvas.xview_scroll(delta * 2, "units")

    def to_top(self):
        self.canvas.yview_moveto(0.0)
        self.canvas.xview_moveto(0.0)


# ============================================================================
#  KLEINE HILFSBAUSTEINE
# ============================================================================

def make_label(parent, text, font=None, fg=None, bg=None, **kwargs):
    kwargs.setdefault("height", 0)
    return ctk.CTkLabel(parent, text=text, text_color=fg or C["text"],
                        fg_color=bg or "transparent", font=font or F["body"],
                        **kwargs)


def make_text(parent, height=6, readonly=False, font=None):
    """Abgerundetes, mehrzeiliges Textfeld. height ist die Zeilenanzahl."""
    font = font or F["body"]
    widget = ctk.CTkTextbox(parent, height=_text_height(font, height), wrap="word",
                            fg_color=C["card_alt"], text_color=C["text_soft"],
                            border_color=C["border"], border_width=1,
                            corner_radius=12, font=font,
                            scrollbar_button_color=C["scrollbar"],
                            scrollbar_button_hover_color=C["scrollbar_hi"],
                            padx=6, pady=6, insertofftime=0)
    widget._textbox.configure(insertbackground=C["accent"],
                              selectbackground=C["purple"],
                              selectforeground="#FFFFFF")
    if readonly:
        widget.configure(state="disabled")
    return widget


def _text_height(font, lines):
    """Hoehe eines Textfelds fuer eine Zeilenanzahl in logischen Pixeln."""
    return int(lines * line_height(font) + 26)


def set_text(widget, content):
    """Setzt den Inhalt eines (ggf. schreibgeschuetzten) Textfelds."""
    state = str(widget.cget("state"))
    widget.configure(state="normal")
    widget.delete("1.0", "end")
    widget.insert("1.0", content)
    if state == "disabled":
        widget.configure(state="disabled")
    resize = getattr(widget, "autogrow_resize", None)
    if resize is not None:
        resize()


def fit_text_height(widget, lines, font=None):
    """Passt die Hoehe eines Textfelds an eine Zeilenanzahl an."""
    widget.configure(height=_text_height(font or F["body"], lines))


def _display_line_count(widget):
    """Anzahl der (umgebrochenen) Anzeigezeilen im Textfeld, robust gegenueber
    unterschiedlichen Rueckgabeformen von Text.count() je nach Tk-Version."""
    try:
        result = widget._textbox.count("1.0", "end", "displaylines")
    except tk.TclError:
        return 1
    if isinstance(result, tuple):
        result = result[0] if result else None
    try:
        return max(1, int(result))
    except (TypeError, ValueError):
        return 1


def make_autogrow_text(parent, min_height=4, max_height=18, font=None):
    """Mehrzeiliges Eingabefeld, das mit seinem Inhalt automatisch mitwaechst
    (bis zu max_height Zeilen), statt eine feste Groesse mit Scrollbalken zu
    haben. Fuer laengere Freitext-Loesungen bei AP1-/AP2-Szenarien gedacht."""
    font = font or F["body"]
    widget = make_text(parent, height=min_height, font=font)
    state = {"lines": min_height}

    def _resize(_event=None):
        lines = _display_line_count(widget) + 1
        new_height = max(min_height, min(max_height, lines))
        if state["lines"] != new_height:
            state["lines"] = new_height
            fit_text_height(widget, new_height, font)

    widget.bind("<KeyRelease>", _resize)
    widget.bind("<<Paste>>", lambda _e: widget.after(1, _resize))
    widget.bind("<Configure>", _resize, add="+")
    # Aufrufbar von aussen, z.B. nach set_text() beim Laden eines Szenarios.
    widget.autogrow_resize = _resize
    return widget


class Divider(ctk.CTkFrame):
    def __init__(self, parent, bg=None):
        super().__init__(parent, fg_color=bg or C["border"], height=1,
                         corner_radius=0)
