#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FISI Lernplattform - Farbwelt
=============================

Farbpalette, Farbverlaeufe und Farbzuordnungen der Oberflaeche. Liegt bewusst
getrennt von fisi_core.py, damit der Kern (Datenbank, Lerninhalte, Rechner)
ohne jede Oberflaeche nutzbar bleibt.
"""

from fisi_core import (
    AP1_THEMES, AP2_THEMES, CAT_BIZ, CAT_DB, CAT_NET, CAT_SEC, CAT_SYS,
)

# ============================================================================
#  PALETTE
# ============================================================================

C = {
    "bg":        "#120A24",
    "sidebar":   "#0C0619",
    "card":      "#1B1031",
    "card_alt":  "#241541",
    "card_hi":   "#301C57",
    "border":    "#2F1D52",
    "border_hi": "#553289",
    # Neutrales Grau (kein Lila-Stich) fuer die Scrollbalken, damit sie zum
    # dunkelgrauen Ton der nativen Windows-Fensterleiste passen.
    "scrollbar":    "#2A2A2F",
    "scrollbar_hi": "#40404A",
    "text":      "#ECE6F8",
    # Leicht gedaempftes Weiss fuer laengere Fliesstexte (Fragen, Antworten,
    # Textfelder). Reines Hellweiss wirkt dort grell und leicht verschwommen;
    # Ueberschriften behalten "text".
    "text_soft": "#CFC6E0",
    "text_dim":  "#A794C6",
    "muted":     "#7D6B9C",
    "on_accent": "#FFFFFF",
    "cyan":      "#22D3EE",
    "pink":      "#F472B6",
    "purple":    "#A78BFA",
    "violet":    "#7C3AED",
    "green":     "#34D399",
    "yellow":    "#FBBF24",
    "orange":    "#FB923C",
    "blue":      "#60A5FA",
    "red":       "#F87171",
    "ring_bg":   "#2C1A4D",
}

# Farbverlaeufe (von, nach) - einheitlich fuer Buttons, Balken und Ringe
GRADIENTS = {
    "primary": ("#7C3AED", "#DB2777"),   # Violett -> Magenta
    "accent":  ("#0891B2", "#6366F1"),   # Tuerkis -> Indigo
    "danger":  ("#DC2626", "#F97316"),   # Rot -> Orange
    "success": ("#059669", "#22D3EE"),   # Gruen -> Tuerkis
    "hero":    ("#4C1D95", "#9D174D"),   # Banner im Dashboard
}

CATEGORY_COLOR = {
    CAT_NET: C["cyan"],
    CAT_SEC: C["pink"],
    CAT_SYS: C["purple"],
    CAT_BIZ: C["green"],
    CAT_DB: C["orange"],
}

# Farbe je Themenblock der AP1/AP2 (gleiche Reihenfolge wie in fisi_core)
_THEME_ORDER = [C["cyan"], C["pink"], C["purple"], C["blue"], C["green"]]
THEME_COLOR = dict(zip(AP2_THEMES, _THEME_ORDER))
THEME_COLOR.update(zip(AP1_THEMES, _THEME_ORDER))


# ============================================================================
#  FARBHILFSFUNKTIONEN
# ============================================================================

def hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(round(v)))) for v in rgb)


def mix(color_a, color_b, t):
    """Mischt zwei Farben. t=0 liefert color_a, t=1 liefert color_b."""
    t = max(0.0, min(1.0, t))
    ra, ga, ba = hex_to_rgb(color_a)
    rb, gb, bb = hex_to_rgb(color_b)
    return rgb_to_hex((ra + (rb - ra) * t, ga + (gb - ga) * t, ba + (bb - ba) * t))


def lighten(color, amount=0.15):
    return mix(color, "#FFFFFF", amount)


def darken(color, amount=0.15):
    return mix(color, "#000000", amount)
