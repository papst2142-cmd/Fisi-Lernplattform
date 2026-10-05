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
    "muted":     "#9986B8",
    "on_accent": "#FFFFFF",
    # Knopf der Schalter am Handy (sitzt in der farbigen Spur); im Hellen reines Weiss.
    # Am PC ragt der Knopf ueber die Spur hinaus und bleibt deshalb "text" (dunkel im Hellen).
    "knob":      "#ECE6F8",
    # Akzentfarben (aktiver Menuepunkt, Ringe, Links, Kalender-Pfeile ...).
    # Sie folgen der gewaehlten Grundfarbe (siehe PRESETS unten); "cyan" und
    # "pink" bleiben fest, weil sie auch Fachbereichsfarben sind.
    "accent":    "#22D3EE",
    "accent2":   "#F472B6",
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
    "accent":  ("#0E7490", "#4F46E5"),   # Tuerkis -> Indigo
    # Ab 0.56 (Kontrastpruefung): weisse Schrift braucht 4,5:1 auf beiden
    # Enden. Vorher Orange #F97316 (2,8:1), Gruen #059669 (3,8:1) und Tuerkis
    # #22D3EE (1,8:1) - jeweils nur so weit abgedunkelt wie noetig.
    "danger":  ("#DC2626", "#BF5811"),   # Rot -> Orange
    "success": ("#05875F", "#158293"),   # Gruen -> Tuerkis
    "hero":    ("#4C1D95", "#9D174D"),   # Banner im Dashboard
}

# ============================================================================
#  GRUNDFARBE (ab 0.31)
# ============================================================================
#
# Waehlbar unter "Optionen", gespeichert lokal je Geraet in einstellungen.json
# (Schluessel "grundfarbe", wird nicht abgeglichen). Es wechseln nur die
# Akzente: C["accent"], C["accent2"] und die Verlaeufe primary, accent und
# hero. Hintergrund, Texte, Fachbereichs-, Themen- und Bedeutungsfarben
# (Erfolg, Fehler, Warnung) bleiben fest.

SETTING_KEY = "grundfarbe"
DEFAULT_PRESET = "cyan_pink"
PRESETS = [
    {"id": "cyan_pink", "name": "Cyan/Pink",
     "accent": "#22D3EE", "accent2": "#F472B6",
     "primary": ("#7C3AED", "#DB2777"), "verlauf": ("#0E7490", "#4F46E5"),
     "hero": ("#4C1D95", "#9D174D")},
    {"id": "lila_magenta", "name": "Lila/Magenta",
     "accent": "#C084FC", "accent2": "#F0ABFC",
     "primary": ("#7C3AED", "#C026D3"), "verlauf": ("#9333EA", "#DB2777"),
     "hero": ("#4C1D95", "#86198F")},
    {"id": "blau_tuerkis", "name": "Blau/Türkis",
     "accent": "#60A5FA", "accent2": "#2DD4BF",
     "primary": ("#2563EB", "#0F766E"), "verlauf": ("#1D4ED8", "#0E7490"),
     "hero": ("#1E3A8A", "#115E59")},
    {"id": "gruen_lime", "name": "Grün/Lime",
     "accent": "#34D399", "accent2": "#A3E635",
     "primary": ("#047857", "#4D7C0F"), "verlauf": ("#065F46", "#3F6212"),
     "hero": ("#064E3B", "#3F6212")},
    {"id": "orange_gelb", "name": "Orange/Gelb",
     "accent": "#FDBA74", "accent2": "#FDE047",
     "primary": ("#C2410C", "#A16207"), "verlauf": ("#9A3412", "#854D0E"),
     "hero": ("#7C2D12", "#713F12")},
    {"id": "rot_pink", "name": "Rot/Pink",
     "accent": "#FB7185", "accent2": "#F9A8D4",
     "primary": ("#E11D48", "#DB2777"), "verlauf": ("#BE123C", "#C026D3"),
     "hero": ("#7F1D1D", "#831843")},
]
PRESET_IDS = [item["id"] for item in PRESETS]

# Meldung waehrend des Farbwechsels (ab 0.48, PC und Handy gleich)
BUSY_TITLE = "Farben werden angewendet"
BUSY_TEXT = "Bitte warten, die Oberfläche wird mit den neuen Farben aufgebaut …"
BUSY_MIN_SECONDS = 0.6
current_preset = DEFAULT_PRESET

# Lesbarkeit (WCAG-Kontrast, geprueft in test_spiel.FarbenTest): Texte und
# "muted" mindestens 4,5:1 auf allen Flaechen, weisse Schrift auf den
# Button-Verlaeufen mindestens 4,5:1, Akzentfarben als Schrift mindestens 4,5:1.
#
# Hintergrund (ab 0.31): Flaechen, Rahmen und die gedaempften Nebentexte.
# Ueberschriften und Fliesstexte ("text", "text_soft") bleiben gleich, alle
# Hintergruende sind dunkel genug dafuer. Lokal je Geraet ("hintergrund").
BACKGROUND_KEY = "hintergrund"
DEFAULT_BACKGROUND = "violett"
BACKGROUND_FIELDS = ("bg", "sidebar", "card", "card_alt", "card_hi", "border",
                     "border_hi", "ring_bg", "text_dim", "muted")
BACKGROUNDS = [
    {"id": "violett", "name": "Violett",
     "bg": "#120A24", "sidebar": "#0C0619", "card": "#1B1031", "card_alt": "#241541",
     "card_hi": "#301C57", "border": "#2F1D52", "border_hi": "#553289",
     "ring_bg": "#2C1A4D", "text_dim": "#A794C6", "muted": "#9986B8"},
    {"id": "nachtblau", "name": "Nachtblau",
     "bg": "#0B1224", "sidebar": "#070C19", "card": "#111B33", "card_alt": "#172441",
     "card_hi": "#1E2F57", "border": "#1F2E52", "border_hi": "#33518A",
     "ring_bg": "#1A2848", "text_dim": "#94A3C6", "muted": "#8998BA"},
    {"id": "tannengruen", "name": "Tannengrün",
     "bg": "#0A1814", "sidebar": "#06100D", "card": "#10231D", "card_alt": "#152D26",
     # Ab 0.56: card_hi minimal dunkler (#1C3A31), damit Rot darauf 4,5:1 erreicht
     "card_hi": "#1C3931", "border": "#1D3A31", "border_hi": "#2F5F50",
     "ring_bg": "#183229", "text_dim": "#93BBAE", "muted": "#7EA498"},
    {"id": "aubergine", "name": "Aubergine",
     "bg": "#1A0A14", "sidebar": "#11060D", "card": "#26101D", "card_alt": "#311527",
     "card_hi": "#401C33", "border": "#3D1D31", "border_hi": "#6A3255",
     "ring_bg": "#3A1A2E", "text_dim": "#C294B0", "muted": "#AE829D"},
    {"id": "anthrazit", "name": "Anthrazit",
     "bg": "#141416", "sidebar": "#0D0D0F", "card": "#1C1C20", "card_alt": "#242429",
     "card_hi": "#2E2E35", "border": "#2C2C33", "border_hi": "#4A4A55",
     "ring_bg": "#2A2A31", "text_dim": "#A3A3B0", "muted": "#9595A2"},
    {"id": "schwarz", "name": "Schwarz",
     "bg": "#050507", "sidebar": "#000000", "card": "#111114", "card_alt": "#18181C",
     "card_hi": "#222228", "border": "#25252B", "border_hi": "#3E3E48",
     "ring_bg": "#1F1F25", "text_dim": "#A3A3B0", "muted": "#888895"},
]
BACKGROUND_IDS = [item["id"] for item in BACKGROUNDS]
current_background = DEFAULT_BACKGROUND


def preset(preset_id):
    """Das Preset zur Kennung (unbekannt -> Standard Cyan/Pink)."""
    for item in PRESETS:
        if item["id"] == preset_id:
            return item
    return PRESETS[0]


def apply_preset(preset_id):
    """Setzt die Akzentfarben in C und GRADIENTS (die Woerterbuecher werden
    veraendert, nicht ersetzt - alle Module sehen so sofort die neuen Werte).
    Bereits gezeichnete Oberflaechen muessen danach neu aufgebaut werden."""
    global current_preset
    item = preset(preset_id)
    C["accent"], C["accent2"] = item["accent"], item["accent2"]
    GRADIENTS["primary"] = item["primary"]
    GRADIENTS["accent"] = item["verlauf"]
    GRADIENTS["hero"] = item["hero"]
    current_preset = item["id"]
    _apply_mode_colors()
    return item


def background(background_id):
    """Der Hintergrund zur Kennung (unbekannt -> Standard Violett)."""
    for item in BACKGROUNDS:
        if item["id"] == background_id:
            return item
    return BACKGROUNDS[0]


def apply_background(background_id):
    """Setzt die Hintergrund-Farben in C (wie apply_preset)."""
    global current_background
    item = background(background_id)
    current_background = item["id"]
    _apply_mode_colors()
    return item


def saved_background():
    import fisi_update
    value = fisi_update.load_settings().get(BACKGROUND_KEY, DEFAULT_BACKGROUND)
    return value if value in BACKGROUND_IDS else DEFAULT_BACKGROUND


def save_background(background_id):
    """Speichert den Hintergrund (nur lokal) und wendet ihn an."""
    import fisi_update
    item = apply_background(background_id)
    settings = fisi_update.load_settings()
    settings[BACKGROUND_KEY] = item["id"]
    fisi_update.save_settings(settings)
    return item


def saved_preset():
    """Die gespeicherte Grundfarbe dieses Geraets."""
    import fisi_update
    value = fisi_update.load_settings().get(SETTING_KEY, DEFAULT_PRESET)
    return value if value in PRESET_IDS else DEFAULT_PRESET


def save_preset(preset_id):
    """Speichert die Grundfarbe (nur lokal) und wendet sie an."""
    import fisi_update
    item = apply_preset(preset_id)
    settings = fisi_update.load_settings()
    settings[SETTING_KEY] = item["id"]
    fisi_update.save_settings(settings)
    return item


CATEGORY_COLOR = {}
THEME_COLOR = {}
_CATEGORY_KEYS = {CAT_NET: "cyan", CAT_SEC: "pink", CAT_SYS: "purple", CAT_BIZ: "green",
                  CAT_DB: "orange"}
# Farbe je Themenblock der AP1/AP2 (gleiche Reihenfolge wie in fisi_core)
_THEME_KEYS = ["cyan", "pink", "purple", "blue", "green"]


def _refresh_tables():
    """Fachbereichs- und Themenfarben aus C (Woerterbuecher bleiben dieselben)."""
    CATEGORY_COLOR.update({cat: C[key] for cat, key in _CATEGORY_KEYS.items()})
    order = [C[key] for key in _THEME_KEYS]
    THEME_COLOR.update(zip(AP2_THEMES, order))
    THEME_COLOR.update(zip(AP1_THEMES, order))


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


# ============================================================================
#  DARSTELLUNG DUNKEL / HELL (ab 0.49)
# ============================================================================
#
# Lokal je Geraet ("darstellung"): "dunkel" (Standard) oder "hell", waehlbar
# unter Optionen > Farben. Im Hellmodus bekommt jeder Hintergrund eine
# helle Fassung im selben Farbton; Texte werden dunkel, und alle Farben, die
# auch als Schrift dienen (Akzente, Fachbereiche, Erfolg/Fehler/Warnung),
# werden so weit abgedunkelt, dass sie auf jeder Flaeche 4,5:1 erreichen.

MODE_KEY = "darstellung"
MODE_DARK, MODE_LIGHT = "dunkel", "hell"
DEFAULT_MODE = MODE_DARK
MODES = [(MODE_DARK, "Dunkel"), (MODE_LIGHT, "Hell")]
MODE_IDS = [key for key, _name in MODES]
current_mode = DEFAULT_MODE
light = False               # aktuell hell?

# Die dunklen Grundwerte (so wie oben in C festgelegt)
_DARK_FIXED = {key: C[key] for key in (
    "text", "text_soft", "knob", "scrollbar", "scrollbar_hi", "cyan", "pink", "purple", "violet",
    "green", "yellow", "orange", "blue", "red")}
# Farben, die im Hellen als Schrift lesbar sein muessen
_LIGHT_SHADED = ("cyan", "pink", "purple", "violet", "green", "yellow", "orange",
                 "blue", "red")

LIGHT_TEXT = {"text": "#1B1628", "text_soft": "#2F2940", "knob": "#FFFFFF",
              "scrollbar": "#C9C9D1", "scrollbar_hi": "#A9A9B5"}

# Helle Fassungen der Hintergruende (gleicher Farbton wie die dunklen)
LIGHT_BACKGROUNDS = {
    "violett": {"bg": "#F4F0FB", "sidebar": "#EAE3F7", "card": "#FFFFFF",
                "card_alt": "#F3EEFB", "card_hi": "#E8DFF7", "border": "#DCD1EF",
                "border_hi": "#B7A3DD", "ring_bg": "#E3D9F3", "text_dim": "#5A4979",
                "muted": "#685889"},
    "nachtblau": {"bg": "#EFF3FA", "sidebar": "#E2E9F5", "card": "#FFFFFF",
                  "card_alt": "#EEF2FA", "card_hi": "#DFE7F5", "border": "#D0DAEC",
                  "border_hi": "#9FB2D6", "ring_bg": "#DAE3F2", "text_dim": "#45557A",
                  "muted": "#56658A"},
    "tannengruen": {"bg": "#EFF6F3", "sidebar": "#E1EEE8", "card": "#FFFFFF",
                    "card_alt": "#EDF5F1", "card_hi": "#DCEBE4", "border": "#CCE0D7",
                    "border_hi": "#93BBAA", "ring_bg": "#D6E8DF", "text_dim": "#3E5E53",
                    "muted": "#4D6C61"},
    "aubergine": {"bg": "#FAF0F5", "sidebar": "#F3E2EC", "card": "#FFFFFF",
                  "card_alt": "#F9EEF4", "card_hi": "#F0DCE7", "border": "#E6CCDA",
                  "border_hi": "#CE9BB7", "ring_bg": "#EDD6E3", "text_dim": "#6E4560",
                  "muted": "#7B536D"},
    "anthrazit": {"bg": "#F3F3F5", "sidebar": "#E7E7EB", "card": "#FFFFFF",
                  "card_alt": "#F1F1F4", "card_hi": "#E4E4E9", "border": "#D6D6DD",
                  "border_hi": "#ABABB7", "ring_bg": "#DFDFE5", "text_dim": "#4E4E5B",
                  "muted": "#5C5C69"},
    "schwarz": {"bg": "#FFFFFF", "sidebar": "#F2F2F4", "card": "#FFFFFF",
                "card_alt": "#F5F5F7", "card_hi": "#EBEBEF", "border": "#DDDDE3",
                "border_hi": "#B0B0BC", "ring_bg": "#E6E6EB", "text_dim": "#4A4A55",
                "muted": "#585864"},
}
LIGHT_SURFACES = ("bg", "sidebar", "card", "card_alt", "card_hi")
MIN_CONTRAST = 4.6


def luminance(color):
    def part(value):
        value /= 255.0
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    r, g, b = hex_to_rgb(color)
    return 0.2126 * part(r) + 0.7152 * part(g) + 0.0722 * part(b)


def contrast(color_a, color_b):
    high, low = sorted((luminance(color_a), luminance(color_b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def readable_on(color, surfaces, minimum=MIN_CONTRAST):
    """Dunkelt eine Farbe schrittweise ab, bis sie auf allen Flaechen als
    Schrift lesbar ist (Farbton bleibt erhalten)."""
    shade = color
    for step in range(1, 41):
        if all(contrast(shade, surface) >= minimum for surface in surfaces):
            return shade
        shade = mix(color, "#000000", step * 0.025)
    return shade


def light_background(background_id):
    """Die helle Fassung eines Hintergrunds (Werte wie BACKGROUNDS)."""
    item = background(background_id)
    return dict(LIGHT_BACKGROUNDS.get(item["id"], LIGHT_BACKGROUNDS["violett"]),
                id=item["id"], name=item["name"])


def _apply_mode_colors():
    """Setzt Flaechen, Texte und Schriftfarben passend zu Hintergrund,
    Grundfarbe und Darstellung (alles in C, in place)."""
    global light
    light = current_mode == MODE_LIGHT
    item = light_background(current_background) if light else background(current_background)
    for key in BACKGROUND_FIELDS:
        C[key] = item[key]
    for key, value in _DARK_FIXED.items():
        C[key] = value
    accent = preset(current_preset)
    C["accent"], C["accent2"] = accent["accent"], accent["accent2"]
    if light:
        C.update(LIGHT_TEXT)
        surfaces = [item[key] for key in LIGHT_SURFACES]
        for key in _LIGHT_SHADED + ("accent", "accent2"):
            C[key] = readable_on(C[key], surfaces)
        for key in ("text_dim", "muted"):
            C[key] = readable_on(C[key], surfaces)
    _apply_control_colors(light)
    _refresh_tables()


# Ab 0.56: Mindestkontrast fuer Bedienelemente ohne Schrift (Rahmen von
# Eingabefeldern, Antwortkreise, Fokusrahmen) gegenueber den Flaechen
CONTROL_CONTRAST = 3.0
CONTROL_SURFACES = ("bg", "sidebar", "card", "card_alt", "card_hi")


def shade_until(color, target, surfaces, minimum):
    """Mischt eine Farbe in kleinen Schritten zu target (weiss/schwarz), bis
    sie auf allen Flaechen den Mindestkontrast erreicht (Farbton bleibt)."""
    shade = color
    for step in range(1, 401):
        if all(contrast(shade, surface) >= minimum for surface in surfaces):
            return shade
        shade = mix(color, target, step * 0.0025)
    return shade


def _apply_control_colors(is_light):
    """Ab 0.56: Farben fuer Bedienelemente.
    field_border: Rand von Eingabefeldern und Antwortkreisen (vorher "border"
    bzw. "border_hi" mit 1,1 bis 2,3:1). Aus border_hi im selben Farbton,
    gerade so weit aufgehellt (dunkel) bzw. abgedunkelt (hell), dass 3:1
    erreicht werden. focus: Fokusrahmen am PC (Akzentfarbe, mind. 4,5:1)."""
    surfaces = [C[key] for key in CONTROL_SURFACES]
    C["field_border"] = shade_until(C["border_hi"], "#000000" if is_light else "#FFFFFF",
                                    surfaces, CONTROL_CONTRAST)
    C["focus"] = shade_until(C["accent"], "#000000" if is_light else "#FFFFFF",
                             surfaces, CONTROL_CONTRAST)


# ============================================================================
#  SCHRIFTGROESSE (ab 0.56)
# ============================================================================
#
# Lokal je Geraet ("schriftgroesse", wird nicht abgeglichen). Am PC waechst
# die ganze Oberflaeche mit (Skalierung von customtkinter: Schrift, Knoepfe,
# Abstaende), damit nichts abgeschnitten wird. Am Handy werden die
# Schriftgroessen vervielfacht; die Schriftgroesse des Systems (Android)
# wirkt zusaetzlich (Flutter-Standard).

FONT_KEY = "schriftgroesse"
FONT_NORMAL = "normal"
FONT_SIZES = [
    {"id": "normal", "name": "Normal", "faktor": 1.0},
    {"id": "gross", "name": "Groß", "faktor": 1.15},
    {"id": "sehr_gross", "name": "Sehr groß", "faktor": 1.3},
]
FONT_IDS = [item["id"] for item in FONT_SIZES]
FONT_CHOICES = [(item["id"], item["name"]) for item in FONT_SIZES]
# Texte (PC und Handy gleich)
FONT_TITLE = "Schriftgröße"
FONT_SUBTITLE = "nur für dieses Gerät"
FONT_HINT = ("Gilt sofort und nur für dieses Gerät. Am PC wächst die ganze Oberfläche mit "
             "(Schrift, Knöpfe, Abstände); passt sie nicht mehr ins Fenster, lässt sie sich "
             "seitlich verschieben. Am Handy kommt die Schriftgröße aus den "
             "Systemeinstellungen noch hinzu.")
BUSY_FONT_TITLE = "Schriftgröße wird angewendet"
BUSY_FONT_TEXT = "Bitte warten, die Oberfläche wird in der neuen Größe aufgebaut …"
current_font_size = FONT_NORMAL


def font_size(size_id):
    """Die Schriftgroesse zur Kennung (unbekannt -> Normal)."""
    for item in FONT_SIZES:
        if item["id"] == size_id:
            return item
    return FONT_SIZES[0]


def font_factor(size_id=None):
    """Vergroesserung (1.0 = Normal) der gewaehlten bzw. aktuellen Groesse."""
    return font_size(current_font_size if size_id is None else size_id)["faktor"]


def apply_font_size(size_id):
    global current_font_size
    current_font_size = font_size(size_id)["id"]
    return current_font_size


def saved_font_size():
    import fisi_update
    value = fisi_update.load_settings().get(FONT_KEY, FONT_NORMAL)
    return value if value in FONT_IDS else FONT_NORMAL


def save_font_size(size_id):
    """Speichert die Schriftgroesse (nur lokal) und merkt sie sich."""
    import fisi_update
    value = apply_font_size(size_id)
    settings = fisi_update.load_settings()
    settings[FONT_KEY] = value
    fisi_update.save_settings(settings)
    return value


def apply_mode(mode):
    """Setzt die Darstellung (dunkel/hell) und alle Farben."""
    global current_mode
    current_mode = mode if mode in MODE_IDS else DEFAULT_MODE
    _apply_mode_colors()
    return current_mode


def saved_mode():
    import fisi_update
    value = fisi_update.load_settings().get(MODE_KEY, DEFAULT_MODE)
    return value if value in MODE_IDS else DEFAULT_MODE


def save_mode(mode):
    """Speichert die Darstellung (nur lokal) und wendet sie an."""
    import fisi_update
    value = apply_mode(mode)
    settings = fisi_update.load_settings()
    settings[MODE_KEY] = value
    fisi_update.save_settings(settings)
    return value


# Gespeicherte Grundfarbe gleich beim Import anwenden, bevor irgendeine
# Oberflaeche gebaut wird.
try:
    current_mode = saved_mode()
    apply_font_size(saved_font_size())
    apply_preset(saved_preset())
    apply_background(saved_background())
except Exception:  # noqa: BLE001 - kaputte Einstellungen duerfen nie den Start verhindern
    current_mode = DEFAULT_MODE
    apply_font_size(FONT_NORMAL)
    apply_preset(DEFAULT_PRESET)
    apply_background(DEFAULT_BACKGROUND)
