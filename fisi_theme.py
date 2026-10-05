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

# Ab 0.56: kurze Ladeanzeige, wenn eine Ansicht beim Oeffnen trotz Vorladen
# laenger braucht (PC und Handy gleiche Beschriftung)
LOADING_TEXT = "Wird geladen …"
LOADING_THRESHOLD_MS = 150
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


def tile_text():
    """Ab 0.57: Schrift des gewaehlten Namens auf einer Hintergrund-Kachel.
    Die Kacheln zeigen immer die Farbwelt der Darstellung - die Schrift folgt
    deshalb der Darstellung, nicht eigenen Farben (die hell/dunkel kippen
    koennen). Ohne eigene Farben ist das genau C["text"]."""
    return LIGHT_TEXT["text"] if current_mode == MODE_LIGHT else _DARK_FIXED["text"]


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
    Grundfarbe und Darstellung (alles in C, in place). Ab 0.57: Gibt es fuer
    die Darstellung eigene Farben, kommen alle Werte aus custom_palette."""
    global light
    values = custom_colors.get(current_mode)
    # Ab 0.57 ("sanft", Entscheidung Nico): Stehen die Regler auf dem
    # Startwert, gilt die Farbwelt exakt, erst danach die Ableitungsregel
    if values and values != custom_start(current_mode):
        palette = custom_palette(values)
        light = palette["light"]
        C.update(palette["colors"])
        GRADIENTS.update(palette["gradients"])
        _refresh_tables()
        return
    light = current_mode == MODE_LIGHT
    item = light_background(current_background) if light else background(current_background)
    for key in BACKGROUND_FIELDS:
        C[key] = item[key]
    for key, value in _DARK_FIXED.items():
        C[key] = value
    accent = preset(current_preset)
    C["accent"], C["accent2"] = accent["accent"], accent["accent2"]
    # Ab 0.57: Verlaeufe immer aus der Grundfarbe (eigene Farben der anderen
    # Darstellung koennen sie vorher ueberschrieben haben)
    GRADIENTS["primary"] = accent["primary"]
    GRADIENTS["accent"] = accent["verlauf"]
    GRADIENTS["hero"] = accent["hero"]
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


def _apply_control_colors(is_light, colors=None):
    """Ab 0.56: Farben fuer Bedienelemente.
    field_border: Rand von Eingabefeldern und Antwortkreisen (vorher "border"
    bzw. "border_hi" mit 1,1 bis 2,3:1). Aus border_hi im selben Farbton,
    gerade so weit aufgehellt (dunkel) bzw. abgedunkelt (hell), dass 3:1
    erreicht werden. focus: Fokusrahmen am PC (Akzentfarbe, mind. 4,5:1).
    Ab 0.57: colors waehlt das Woerterbuch (Vorgabe C, sonst eine Palette
    der eigenen Farben)."""
    colors = C if colors is None else colors
    surfaces = [colors[key] for key in CONTROL_SURFACES]
    colors["field_border"] = shade_until(colors["border_hi"],
                                         "#000000" if is_light else "#FFFFFF",
                                         surfaces, CONTROL_CONTRAST)
    colors["focus"] = shade_until(colors["accent"], "#000000" if is_light else "#FFFFFF",
                                  surfaces, CONTROL_CONTRAST)


# ============================================================================
#  EIGENE FARBEN (ab 0.57)
# ============================================================================
#
# Drei Regler-Gruppen (Akzent 1, Akzent 2, Hintergrund) mit Farbton,
# Saettigung und Helligkeit (HSL). Gespeichert lokal je Geraet und je
# Darstellung in einstellungen.json ("eigene_farben": {"dunkel": {...},
# "hell": {...}}), nie im Abgleich. Fehlt der Eintrag fuer die aktuelle
# Darstellung oder ist er ungueltig, gilt die gewaehlte Farbwelt unveraendert.
#
# Stehen die Regler genau auf dem Startwert (der Farbwelt), gilt die Farbwelt
# exakt (Entscheidung Nico 05.10.2026, "sanft"); erst nach dem Verschieben
# gilt die Ableitungsregel (im Bericht 0.57 erklaert):
# - Akzent 1 und 2 sind die beiden Farben des Knopfverlaufs ("primary").
#   Zweiter Verlauf = beide 20 % dunkler, Banner = beide 40 % dunkler.
#   Schriftakzente (Menue, Ringe, Links) = gleicher Farbton, so weit
#   aufgehellt (dunkel) bzw. abgedunkelt (hell), dass sie 4,5:1 erreichen.
# - Der Hintergrund-Regler setzt Farbton, Saettigung und Helligkeit der
#   Hauptflaeche. Seitenleiste, Karten, Rahmen und Ring folgen in festen
#   Helligkeitsstufen (gemessen an den sechs vorgefertigten Hintergruenden).
# - Ob die Schrift hell oder dunkel ist, entscheidet die Helligkeit des
#   Hintergrunds (die Schrift mit dem hoeheren Kontrast gewinnt). Bei dunkler
#   Schrift gilt alles wie in der hellen Darstellung (Stufen, abgedunkelte
#   Fachbereichsfarben, Karte).

CUSTOM_KEY = "eigene_farben"
CUSTOM_PARTS = (("akzent1", "Akzent 1"), ("akzent2", "Akzent 2"),
                ("hintergrund", "Hintergrund"))
CUSTOM_PART_IDS = tuple(key for key, _name in CUSTOM_PARTS)
# (Kennung, Beschriftung, kleinster Wert, groesster Wert, Einheit kurz, Einheit gesprochen)
CUSTOM_CHANNELS = (("h", "Farbton", 0, 359, "°", "Grad"),
                   ("s", "Sättigung", 0, 100, " %", "Prozent"),
                   ("l", "Helligkeit", 0, 100, " %", "Prozent"))
# Texte (PC und Handy gleich)
CUSTOM_TITLE = "EIGENE FARBEN"
CUSTOM_HINT = ("Mit den Reglern stellst du die zwei Farben der Farbverläufe (Akzent 1 und 2) "
               "und den Hintergrund selbst ein. Alle anderen Farben werden daraus abgeleitet. "
               "Gilt nur für dieses Gerät und nur für die gewählte Darstellung.")
CUSTOM_STATE_ON = "Eigene Farben aktiv (%s)"
CUSTOM_STATE_OFF = "Startwerte aus der Farbwelt (%s)"
CUSTOM_TILE_HINT = ("Ein Klick auf eine Grundfarbe oder einen Hintergrund setzt nur die "
                    "Regler auf diese Farbwelt. Gespeichert wird erst mit „Speichern“.")
CUSTOM_PREVIEW = "Vorschau"
CUSTOM_PREVIEW_TITLE = "Überschrift"
CUSTOM_PREVIEW_TEXT = "Fließtext einer Frage"
CUSTOM_PREVIEW_MUTED = "Nebentext"
CUSTOM_PREVIEW_LINK = "Link"
CUSTOM_PREVIEW_BUTTON = "Knopf"
CUSTOM_PREVIEW_MAP = "Karte"
CUSTOM_SAVE = "Speichern"
CUSTOM_RESET = "Auf Farbwelt zurücksetzen"
CUSTOM_OK = "Alle Kontraste reichen aus."
CUSTOM_WARN_TITLE = "Zu wenig Kontrast (Speichern ist trotzdem möglich):"
CUSTOM_WARN_MORE = "… und %d weitere"
custom_colors = {}          # Darstellung -> {"akzent1": (h, s, l), ...}

# Helligkeitsstufen der Flaechen relativ zum Hintergrund: (Abstand, Saettigungsfaktor).
# Gemessen an den sechs Hintergruenden (z. B. Violett dunkel: Hintergrund 9 %,
# Karte 13 %, Rahmen hervorgehoben 37 %; hell: Hintergrund 96 %, Karte weiss).
_DARK_STEPS = {"sidebar": (-3, 1.05), "card": (4, 0.9), "card_alt": (8, 0.9),
               "card_hi": (14, 0.9), "border": (13, 0.85), "border_hi": (28, 0.83),
               "ring_bg": (11, 0.88)}
_LIGHT_STEPS = {"sidebar": (-3, 0.97), "card_alt": (0, 1.0), "card_hi": (-4, 1.0),
                "border": (-8, 0.83), "border_hi": (-21, 0.8), "ring_bg": (-6, 0.9)}
# Nebentexte: (Helligkeit, Saettigungsfaktor), danach bis 4,5:1 nachgeregelt
_DARK_DIM = {"text_dim": (68, 0.53), "muted": (62, 0.46)}
_LIGHT_DIM = {"text_dim": (38, 0.43), "muted": (44, 0.38)}


def hsl_to_hex(hue, saturation, lightness):
    """Farbton 0-359 Grad, Saettigung und Helligkeit 0-100 % -> "#RRGGBB"."""
    import colorsys
    red, green, blue = colorsys.hls_to_rgb((hue % 360) / 360.0,
                                           max(0.0, min(100.0, lightness)) / 100.0,
                                           max(0.0, min(100.0, saturation)) / 100.0)
    return rgb_to_hex((red * 255, green * 255, blue * 255))


def hex_to_hsl(color):
    """"#RRGGBB" -> (Farbton, Saettigung, Helligkeit) als ganze Zahlen."""
    import colorsys
    red, green, blue = (value / 255.0 for value in hex_to_rgb(color))
    hue, lightness, saturation = colorsys.rgb_to_hls(red, green, blue)
    return (int(round(hue * 360)) % 360, int(round(saturation * 100)),
            int(round(lightness * 100)))


def _valid_channel(value, low, high):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and value == value and low <= value <= high)


def valid_custom(value):
    """Prueft einen gespeicherten Satz eigener Farben. Liefert
    {"akzent1": (h, s, l), ...} oder None, wenn irgendetwas fehlt, falsch
    getippt oder ausserhalb der Grenzen ist (dann gilt die Farbwelt)."""
    if not isinstance(value, dict):
        return None
    result = {}
    for part in CUSTOM_PART_IDS:
        triple = value.get(part)
        if not isinstance(triple, (list, tuple)) or len(triple) != 3:
            return None
        for number, channel in zip(triple, CUSTOM_CHANNELS):
            if not _valid_channel(number, channel[2], channel[3]):
                return None
        result[part] = tuple(int(round(number)) for number in triple)
    return result


def custom_start(mode=None, world=None):
    """Startwerte der Regler: die gewaehlte Farbwelt der Darstellung (Knopf-
    verlauf der Grundfarbe und Hauptflaeche des Hintergrunds). Ab 0.57 (F3):
    world = (Grundfarbe, Hintergrund) einer angeklickten, noch nicht
    gespeicherten Farbwelt, sonst die gespeicherte."""
    mode = current_mode if mode is None else mode
    preset_id, background_id = world or (current_preset, current_background)
    accent = preset(preset_id)
    back = (light_background(background_id) if mode == MODE_LIGHT
            else background(background_id))
    return {"akzent1": hex_to_hsl(accent["primary"][0]),
            "akzent2": hex_to_hsl(accent["primary"][1]),
            "hintergrund": hex_to_hsl(back["bg"])}


def custom_values(mode=None):
    """Die Reglerwerte der Darstellung: eigene Farben oder die Startwerte."""
    mode = current_mode if mode is None else mode
    return dict(custom_colors.get(mode) or custom_start(mode))


def _step(hue, saturation, lightness, offset, factor):
    return hsl_to_hex(hue, saturation * factor, max(0, min(100, lightness + offset)))


def custom_palette(values):
    """Alle Farben aus den drei Reglern (Ableitungsregel oben). Veraendert
    nichts: liefert {"light": bool, "colors": {...}, "gradients": {...}}."""
    hue, saturation, lightness = values["hintergrund"]
    ground = hsl_to_hex(hue, saturation, lightness)
    is_light = contrast(LIGHT_TEXT["text"], ground) > contrast(_DARK_FIXED["text"], ground)
    colors = dict(_DARK_FIXED, on_accent="#FFFFFF")
    colors["bg"] = ground
    if is_light:
        colors.update(LIGHT_TEXT)
    # Die Stufen werden nur so weit gespreizt, dass die festen Schriftfarben
    # (Text, im Dunklen auch Fachbereichs- und Bedeutungsfarben) auf allen
    # Flaechen 4,5:1 behalten: Spreizung 100 %, 90 % ... bis 50 %.
    fixed = ("text", "text_soft") + (() if is_light else _LIGHT_SHADED)
    for spread in (1.0, 0.9, 0.8, 0.7, 0.6, 0.5):
        if is_light:
            for key, (offset, factor) in _LIGHT_STEPS.items():
                colors[key] = _step(hue, saturation, lightness, offset * spread, factor)
            # Karte: 90 % des Wegs zu Weiss (bei den Farbwelten reines Weiss)
            colors["card"] = hsl_to_hex(hue, saturation,
                                        lightness + (100 - lightness) * 0.9)
        else:
            for key, (offset, factor) in _DARK_STEPS.items():
                colors[key] = _step(hue, saturation, lightness, offset * spread, factor)
            colors["sidebar"] = hsl_to_hex(hue, min(100, saturation * 1.05), lightness * 0.66)
        surfaces = [colors[key] for key in LIGHT_SURFACES]
        if all(contrast(colors[key], surface) >= MIN_CONTRAST
               for key in fixed for surface in surfaces):
            break
    target = "#000000" if is_light else "#FFFFFF"
    for key, (level, factor) in (_LIGHT_DIM if is_light else _DARK_DIM).items():
        colors[key] = shade_until(hsl_to_hex(hue, saturation * factor, level), target,
                                  surfaces, MIN_CONTRAST)
    if is_light:
        for key in _LIGHT_SHADED:
            colors[key] = readable_on(colors[key], surfaces)
    first = hsl_to_hex(*values["akzent1"])
    second = hsl_to_hex(*values["akzent2"])
    for key, (h, s, l) in (("accent", values["akzent1"]), ("accent2", values["akzent2"])):
        start = hsl_to_hex(h, s, min(l, 45) if is_light else max(l, 60))
        colors[key] = shade_until(start, target, surfaces, MIN_CONTRAST)
    _apply_control_colors(is_light, colors)
    gradients = {"primary": (first, second),
                 "accent": (darken(first, 0.2), darken(second, 0.2)),
                 "hero": (darken(first, 0.4), darken(second, 0.4))}
    return {"light": is_light, "colors": colors, "gradients": gradients}


def is_start(values, mode=None, world=None):
    """True, wenn die Regler genau auf dem Startwert (der Farbwelt) stehen."""
    return dict(values) == custom_start(mode, world)


def farbwelt_palette(mode=None, world=None):
    """Die Farben der gewaehlten (bzw. mit world angeklickten) Farbwelt einer
    Darstellung als Palette (wie custom_palette), ohne eigene Farben und ohne
    etwas zu veraendern."""
    global current_mode, current_preset, current_background, light
    mode = current_mode if mode is None else mode
    saved = (dict(C), dict(GRADIENTS), light, current_mode, dict(custom_colors),
             current_preset, current_background)
    try:
        custom_colors.clear()
        current_mode = mode
        if world:
            current_preset = preset(world[0])["id"]
            current_background = background(world[1])["id"]
        _apply_mode_colors()
        return {"light": light, "colors": dict(C), "gradients": dict(GRADIENTS)}
    finally:
        C.clear()
        C.update(saved[0])
        GRADIENTS.clear()
        GRADIENTS.update(saved[1])
        light, current_mode = saved[2], saved[3]
        custom_colors.update(saved[4])
        current_preset, current_background = saved[5], saved[6]
        _refresh_tables()


def values_palette(values, mode=None, world=None):
    """Palette fuer Regler-Werte: am Startwert exakt die Farbwelt ("sanft"),
    sonst die Ableitungsregel. Fuer Vorschau und Warnhinweis."""
    if is_start(values, mode, world):
        return farbwelt_palette(mode, world)
    return custom_palette(values)


def custom_to_save(mode, values, world=None):
    """Ab 0.57 (F3): Was "Speichern" ablegt. Stehen die Regler genau auf dem
    Startwert der (angeklickten) Farbwelt, wird nur die Farbwelt gespeichert
    (None = keine eigenen Farben), sonst die Reglerwerte."""
    if values is None or is_start(values, mode, world):
        return None
    return valid_custom(values)


def tile_sets_sliders(mode, values, world=None):
    """Ab 0.57 (F3): True, wenn ein Klick auf eine Farbwelt-Kachel nur die
    Regler setzen soll - weil eigene Farben gespeichert sind oder die Regler
    schon bewegt wurden. Sonst waehlt die Kachel wie bisher die Farbwelt."""
    return mode in custom_colors or world is not None or not is_start(values, mode)


class preview_colors:
    """Setzt eine Palette voruebergehend in C/GRADIENTS (fuer Vorschau und
    Kontrastpruefung der Karte) und stellt danach alles wieder her:
        with preview_colors(palette): ..."""

    def __init__(self, palette):
        self.palette = palette

    def __enter__(self):
        global light
        self.saved = (dict(C), dict(GRADIENTS), light)
        C.update(self.palette["colors"])
        GRADIENTS.update(self.palette["gradients"])
        light = self.palette["light"]
        _refresh_tables()
        return self.palette

    def __exit__(self, *_exc):
        global light
        C.clear()
        C.update(self.saved[0])
        GRADIENTS.clear()
        GRADIENTS.update(self.saved[1])
        light = self.saved[2]
        _refresh_tables()
        return False


# Kontrastziele wie in 0.56: Schrift 4,5:1, Linien/Flaechen/Fokusrahmen 3:1
TEXT_TARGET = 4.5
AREA_TARGET = 3.0
_CATEGORY_NAMES = (("cyan", "Fachbereich Netzwerk (Cyan)"),
                   ("pink", "Fachbereich Sicherheit (Pink)"),
                   ("purple", "Fachbereich Systeme (Lila)"),
                   ("green", "Fachbereich Wirtschaft (Grün)"),
                   ("orange", "Fachbereich Datenbanken (Orange)"), ("blue", "Themenfarbe Blau"),
                   ("red", "Fehler (Rot)"), ("yellow", "Warnung (Gelb)"))


def custom_checks(palette, map_colors=None):
    """Alle Kontrastpruefungen einer Palette: [(Element, Messwert, Ziel)].
    Gemessen wird gegen die schwaechste Flaeche (Hintergrund, Seitenleiste,
    Karten). map_colors: Kartenfarben (fisi_game.map_palette unter
    preview_colors), sonst ohne Karte."""
    colors, gradients = palette["colors"], palette["gradients"]
    surfaces = [colors[key] for key in LIGHT_SURFACES]

    def worst(color, grounds=None):
        return min(contrast(color, ground) for ground in (grounds or surfaces))
    checks = [("Überschriften", worst(colors["text"]), TEXT_TARGET),
              ("Fließtext", worst(colors["text_soft"]), TEXT_TARGET),
              ("Nebentext", min(worst(colors["text_dim"]), worst(colors["muted"])), TEXT_TARGET),
              ("Knopfschrift auf Akzent 1", contrast(colors["on_accent"],
                                                     gradients["primary"][0]), TEXT_TARGET),
              ("Knopfschrift auf Akzent 2", contrast(colors["on_accent"],
                                                     gradients["primary"][1]), TEXT_TARGET),
              ("Bannerschrift", min(contrast("#FFFFFF", color) for color in gradients["hero"]),
               TEXT_TARGET),
              ("Akzent 1 als Schrift (Menü, Links)", worst(colors["accent"]), TEXT_TARGET),
              ("Akzent 2 als Schrift", worst(colors["accent2"]), TEXT_TARGET),
              ("Rahmen von Eingabefeldern", worst(colors["field_border"]), AREA_TARGET),
              ("Fokusrahmen", worst(colors["focus"]), AREA_TARGET)]
    for key, name in _CATEGORY_NAMES:
        checks.append((name + " als Schrift", worst(colors[key]), TEXT_TARGET))
    # Karte ab 0.57 in beiden Darstellungen (die dunkle Karte ist seit 0.57
    # wie die helle nachgeregelt)
    if map_colors:
        ground = map_colors["boden"]
        checks.append(("Karte: Beschriftung", contrast(map_colors["schrift"], ground),
                       TEXT_TARGET))
        checks.append(("Karte: Straßen", contrast(map_colors["strasse"], ground), AREA_TARGET))
        checks.append(("Karte: Fluss", contrast(map_colors["wasser"], ground), AREA_TARGET))
    return checks


def custom_problems(palette, map_colors=None):
    """Nur die Pruefungen unter dem Ziel, schlechteste zuerst."""
    problems = [item for item in custom_checks(palette, map_colors) if item[1] < item[2]]
    return sorted(problems, key=lambda item: item[1] / item[2])


def format_ratio(value):
    """4.5 -> "4,5:1" (eine Nachkommastelle, abgerundet wie in den Berichten)."""
    return ("%.1f:1" % (int(value * 10) / 10.0)).replace(".", ",")


def warning_lines(problems, limit=4):
    """Warnhinweis-Zeilen mit Messwert (PC und Handy gleich)."""
    lines = ["%s: %s (nötig %s)" % (name, format_ratio(value), format_ratio(target))
             for name, value, target in problems[:limit]]
    if len(problems) > limit:
        lines.append(CUSTOM_WARN_MORE % (len(problems) - limit))
    return lines


# Ab 0.57 (Entscheidung Nico F4): Die fuenf Fachbereichsfarben muessen sich
# untereinander unterscheiden lassen. Gemessen wird der Farbabstand Delta E
# (CIE 1976, Lab-Farbraum) jedes Paares. Die Farbwelten liegen bei mindestens
# 27,8 (Cyan/Gruen, hell auf Aubergine); unter 20 gibt es eine eigene Warnzeile.
CATEGORY_DISTANCE = 20.0
CUSTOM_CLASH = "Fachbereichsfarben schwer unterscheidbar: %s und %s (Farbabstand %s, nötig %s)"
_CATEGORY_KEYS_ORDER = ("cyan", "pink", "purple", "green", "orange")


def _lab(color):
    """"#RRGGBB" -> (L, a, b) im CIE-Lab-Farbraum (Weisspunkt D65)."""
    def linear(channel):
        channel /= 255.0
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
    red, green, blue = (linear(channel) for channel in hex_to_rgb(color))
    x = (0.4124 * red + 0.3576 * green + 0.1805 * blue) / 0.95047
    y = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    z = (0.0193 * red + 0.1192 * green + 0.9505 * blue) / 1.08883

    def f(value):
        return value ** (1.0 / 3.0) if value > 0.008856 else 7.787 * value + 16.0 / 116.0
    return 116.0 * f(y) - 16.0, 500.0 * (f(x) - f(y)), 200.0 * (f(y) - f(z))


def color_distance(color_a, color_b):
    """Farbabstand Delta E (CIE 1976) zweier Farben."""
    return sum((a - b) ** 2 for a, b in zip(_lab(color_a), _lab(color_b))) ** 0.5


def category_clash(palette):
    """Das am schwersten unterscheidbare Paar der Fachbereichsfarben unter
    CATEGORY_DISTANCE als (Name 1, Name 2, Abstand), sonst None."""
    colors = palette["colors"]
    names = dict(_CATEGORY_NAMES)
    worst = None
    for index, first in enumerate(_CATEGORY_KEYS_ORDER):
        for second in _CATEGORY_KEYS_ORDER[index + 1:]:
            distance = color_distance(colors[first], colors[second])
            if worst is None or distance < worst[2]:
                worst = (names[first].replace("Fachbereich ", ""),
                         names[second].replace("Fachbereich ", ""), distance)
    return worst if worst[2] < CATEGORY_DISTANCE else None


def _format_distance(value):
    return ("%.1f" % (int(value * 10) / 10.0)).replace(".", ",")


def custom_warning(palette, map_colors=None):
    """Ab 0.57: Der ganze Warnhinweis als Liste von Zeilen (PC und Handy
    gleich), leer, wenn alles reicht. Erst die Kontrastwerte, dann (F4) die
    eigene Zeile fuer schwer unterscheidbare Fachbereichsfarben."""
    lines = []
    problems = custom_problems(palette, map_colors)
    if problems:
        lines.append(CUSTOM_WARN_TITLE)
        lines += ["• " + line for line in warning_lines(problems)]
    clash = category_clash(palette)
    if clash:
        lines.append(CUSTOM_CLASH % (clash[0], clash[1], _format_distance(clash[2]),
                                     _format_distance(CATEGORY_DISTANCE)))
    return lines


def slider_label(part_name, channel, value):
    """Beschriftung fuer Screenreader/TalkBack: "Akzent 1, Farbton, 210 Grad"."""
    return "%s, %s, %d %s" % (part_name, channel[1], value, channel[5])


def slider_text(channel, value):
    """Sichtbarer Wert neben dem Regler: "210°", "45 %"."""
    return "%d%s" % (value, channel[4])


# ---------------------------------------------------------------------------
# Farbige Reglerspuren (ab 0.58, Plan 3a). Nur Optik: Die Spur zeigt, was ein
# Schieben bewirkt. Farbton-Spur = alle Farbtoene in der aktuellen Saettigung
# und Helligkeit, Saettigungs-Spur = grau bis voll, Helligkeits-Spur = dunkel
# ueber die Farbe bis hell. PC und Handy rechnen hier.
# ---------------------------------------------------------------------------

KNOB_LIGHT = "#FFFFFF"      # Reglerknopf hell
KNOB_DARK = "#1B1628"       # Reglerknopf dunkel (Schriftfarbe der hellen Darstellung)
KNOB_MIN_CONTRAST = 3.0     # Knopf gegen die Spur an seiner Stelle (Plan 3a)
_CHANNEL_INDEX = {"h": 0, "s": 1, "l": 2}


def _channel(key):
    for channel in CUSTOM_CHANNELS:
        if channel[0] == key:
            return channel
    raise KeyError(key)


def _safe_triple(values):
    """(h, s, l) fuer die Spur; Unbrauchbares faellt auf (0, 0, 50) bzw. die
    Grenzen zurueck, damit eine Spur nie das Zeichnen abbricht."""
    result = []
    for index, (key, _name, low, high) in enumerate(c[:4] for c in CUSTOM_CHANNELS):
        try:
            number = float(values[index])
        except (TypeError, ValueError, IndexError, KeyError):
            number = (0, 0, 50)[index]
        if number != number:                       # NaN
            number = (0, 0, 50)[index]
        result.append(max(low, min(high, number)))
    return tuple(result)


def track_color(values, key, fraction):
    """Farbe der Spur des Reglers key ("h", "s", "l") an der Stelle fraction
    (0 = links, 1 = rechts) bei den Reglerwerten values = (h, s, l)."""
    triple = list(_safe_triple(values))
    _key, _name, low, high = _channel(key)[:4]
    fraction = max(0.0, min(1.0, float(fraction)))
    triple[_CHANNEL_INDEX[key]] = low + (high - low) * fraction
    return hsl_to_hex(*triple)


def track_colors(values, key, count):
    """count gleichmaessig verteilte Spurfarben von links nach rechts."""
    count = max(2, int(count))
    return [track_color(values, key, index / (count - 1)) for index in range(count)]


def track_fraction(values, key):
    """Stelle des Knopfes (0..1) beim aktuellen Wert."""
    _key, _name, low, high = _channel(key)[:4]
    value = _safe_triple(values)[_CHANNEL_INDEX[key]]
    return (value - low) / float(high - low)


def knob_colors(values, key):
    """(Fuellung, Rand) des Reglerknopfes: die Fuellung ist die von Hell und
    Dunkel mit dem hoeheren Kontrast zur Spur an der Stelle des Knopfes, der
    Rand die andere. So hebt sich der Knopf auf jeder Spur ab (mindestens
    etwa 4,1:1, weil Hell zu Dunkel 17:1 hat)."""
    under = track_color(values, key, track_fraction(values, key))
    if contrast(KNOB_LIGHT, under) >= contrast(KNOB_DARK, under):
        return KNOB_LIGHT, KNOB_DARK
    return KNOB_DARK, KNOB_LIGHT


def knob_contrast(values, key):
    """Kontrast Knopffuellung zur Spur an der Stelle des Knopfes."""
    under = track_color(values, key, track_fraction(values, key))
    return contrast(knob_colors(values, key)[0], under)


def saved_custom():
    """Gespeicherte eigene Farben {Darstellung: Werte}, ungueltiges entfaellt."""
    import fisi_update
    stored = fisi_update.load_settings().get(CUSTOM_KEY)
    result = {}
    if isinstance(stored, dict):
        for mode in MODE_IDS:
            values = valid_custom(stored.get(mode))
            if values:
                result[mode] = values
    return result


def apply_custom(mode, values):
    """Setzt (values) bzw. entfernt (None) die eigenen Farben einer Darstellung."""
    values = valid_custom(values) if values is not None else None
    if values:
        custom_colors[mode] = values
    else:
        custom_colors.pop(mode, None)
    _apply_mode_colors()
    return values


def save_custom(mode, values):
    """Speichert die eigenen Farben einer Darstellung (None = zuruecksetzen)
    nur lokal und wendet sie an."""
    import fisi_update
    values = apply_custom(mode, values)
    settings = fisi_update.load_settings()
    stored = settings.get(CUSTOM_KEY)
    stored = dict(stored) if isinstance(stored, dict) else {}
    if values:
        stored[mode] = {key: list(value) for key, value in values.items()}
    else:
        stored.pop(mode, None)
    if stored:
        settings[CUSTOM_KEY] = stored
    else:
        settings.pop(CUSTOM_KEY, None)
    fisi_update.save_settings(settings)
    return values


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
    custom_colors.update(saved_custom())     # ab 0.57
    apply_font_size(saved_font_size())
    apply_preset(saved_preset())
    apply_background(saved_background())
except Exception:  # noqa: BLE001 - kaputte Einstellungen duerfen nie den Start verhindern
    current_mode = DEFAULT_MODE
    custom_colors.clear()
    apply_font_size(FONT_NORMAL)
    apply_preset(DEFAULT_PRESET)
    apply_background(DEFAULT_BACKGROUND)


# ============================================================================
#  KURVEN IN DIAGRAMMEN (ab 0.56)
# ============================================================================

def curve_controls(points):
    """Kontrollpunkte einer weichen Kurve durch alle Punkte (Bildschirm-
    koordinaten, x aufsteigend): [(c1, c2)] je Abschnitt fuer kubische
    Bezier-Segmente von points[i] nach points[i + 1]. PC und Handy gleich.

    Monotone Interpolation nach Fritsch und Carlson: Zwischen zwei Punkten
    bleibt die Kurve immer zwischen deren Werten. Sie schwingt also nie unter
    die Nulllinie und nie ueber einen Datenpunkt hinaus; an Hoch- und
    Tiefpunkten und auf gleichen Werten laeuft sie waagerecht."""
    count = len(points)
    if count < 2:
        return []
    slopes = []
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        slopes.append((y2 - y1) / (x2 - x1) if x2 != x1 else 0.0)
    tangents = [slopes[0]]
    for before, after in zip(slopes, slopes[1:]):
        if before * after <= 0:
            tangents.append(0.0)
        else:
            # harmonisches Mittel: hoechstens doppelt so steil wie die flachere Seite
            tangents.append(2.0 / (1.0 / before + 1.0 / after))
    tangents.append(slopes[-1])
    controls = []
    for index in range(count - 1):
        (x1, y1), (x2, y2) = points[index], points[index + 1]
        third = (x2 - x1) / 3.0
        controls.append(((x1 + third, y1 + tangents[index] * third),
                         (x2 - third, y2 - tangents[index + 1] * third)))
    return controls


# ============================================================================
#  BESCHRIFTUNG DER ZEITACHSE (ab 0.58)
# ============================================================================

# Datumsbeschriftungen der Tagesdiagramme ausduennen. Zwischen zwei
# Beschriftungen liegt mindestens LABEL_SPACING mal die Textbreite; gezaehlt
# wird vom rechten Ende (heute steht immer da), die Schrittweite kommt aus
# LABEL_STRIDES (jede 2., 3. ... Beschriftung). PC und Handy gleich.
LABEL_SPACING = 1.8
LABEL_STRIDES = (1, 2, 3, 5, 7, 10, 14, 15, 30)


def label_stride(count, slot, label_width):
    """Schrittweite fuer count Beschriftungen im Abstand slot (Pixel), wenn
    eine Beschriftung label_width Pixel breit ist."""
    if count <= 1 or slot <= 0:
        return 1
    for stride in LABEL_STRIDES:
        if slot * stride >= label_width * LABEL_SPACING:
            return stride
    return max(1, count)


def shown_labels(count, stride):
    """Indizes der beschrifteten Punkte, vom letzten Punkt aus gezaehlt."""
    return [index for index in range(count) if (count - 1 - index) % stride == 0]
