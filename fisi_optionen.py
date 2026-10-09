#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fachinformatiker Lernplattform - Aufbau der Optionen (ab 0.59)
==============================================================

Gemeinsam fuer PC (app_gui.py) und Handy (mobile/src/main.py), damit beide
dieselbe Reihenfolge, dieselben Beschriftungen und dieselbe Suche haben.

- AREAS: alle Bereiche der Optionen in der angezeigten Reihenfolge.
  "Updates" steht ganz oben (E2) und ist kein Klappbereich. Beim Oeffnen der
  Optionen sind alle Bereiche eingeklappt (E1; bis 0.59.1 auch "Problem
  melden" offen), ab 0.62.2 ausser "Über das Programm" (E-B3,
  unfolded_at_start). Der Klappzustand wird nicht gespeichert (E4) - es gibt
  keine neue Einstellung.
- Ab 0.59.2 (U): "Problem melden", "Leistungsmessung" und am PC die
  "Hänger-Diagnose" stehen zusammen im Bereich "Diagnose und Werkzeuge"
  (Zwischenueberschriften wie bei "Löschen", DIAGNOSE_SECTIONS).
- Ab 0.62.2: "Schriftgröße" und "Farben" stehen zusammen im Bereich
  "Optische Anpassungen", der "Rahmenplan" im Bereich "Lerninhalte"
  (Zwischenueberschriften, SECTIONS). "Über das Programm" steht ganz unten,
  unter "Diagnose und Werkzeuge" (E-B2).
- search_options(): Treffer fuer die Suche (Strg+F). Ein Treffer oeffnet die
  Optionen, klappt den Bereich (und ggf. den Unterbereich "Vorlagen") auf und
  springt hin (E5).
"""

import fisi_diagnose as fdg
import fisi_hilfe as fh
# fisi_haenger nicht importieren: das Handy braucht es nicht (nur Texte unten)
import fisi_leistung as fle
import fisi_rahmenplan as frp
import fisi_sicherung as fsi
import fisi_theme
from fisi_lernen import DELETE_TITLE

SEARCH_KIND = "Optionen"
# Schluessel-Anfang der gemerkten Klappzustaende (werden beim Oeffnen der
# Optionen vergessen, E4)
STATE_PREFIX = "optionen_"

# Unterbereich im Bereich "Optische Anpassungen" bei "Farben" (Entscheidung F1)
TEMPLATES_ID = "vorlagen"
TEMPLATES_TITLE = "Vorlagen"
TEMPLATES_HINT = ("Ein Klick auf eine Vorlage stellt die Farben ein. Sind eigene Farben "
                  "gespeichert oder Regler bewegt, setzt er nur die Regler.")
TEMPLATES_TEXT = ("Die Grundfarbe ändert Buttons, Ringe, Balken und Banner, der "
                  "Hintergrund die Flächen und Karten. Fachbereichsfarben und Erfolg, "
                  "Fehler, Warnung bleiben gleich (in der hellen Darstellung etwas "
                  "dunkler, damit sie gut lesbar sind).")

# Ab 0.59.2 (U): Bereich mit allen Werkzeugen zum Melden und Messen (ab 0.62.2
# der vorletzte, darunter steht nur noch "Über das Programm")
DIAGNOSE_ID = "diagnose"
DIAGNOSE_TITLE = "Diagnose und Werkzeuge"
DIAGNOSE_SUBTITLE = "Fehler melden, messen, Hänger finden"
HANG_TITLE = "Hänger-Diagnose"          # = fisi_haenger.TITLE (nur PC)
# Zwischenueberschriften im Bereich (Reihenfolge), am Handy ohne "nur_pc"
DIAGNOSE_SECTIONS = [
    {"id": "problem", "titel": fdg.TITLE},
    {"id": "leistung", "titel": fle.TITLE},
    {"id": "haenger", "titel": HANG_TITLE, "nur_pc": True},
]

# Ab 0.62.2: zusammengelegte Bereiche und ihre Zwischenueberschriften
OPTIK_ID = "optik"
OPTIK_TITLE = "Optische Anpassungen"
COLORS_TITLE = "Farben"
LEARN_ID = "lerninhalte"
ABOUT_ID = "ueber"
SECTIONS = {
    OPTIK_ID: [{"id": "schrift", "titel": fisi_theme.FONT_TITLE},
               {"id": "farben", "titel": COLORS_TITLE}],
    LEARN_ID: [{"id": "rahmenplan", "titel": frp.OPTIONS_TITLE}],
}

# id, Titel, offen (kein Klappbereich), aufgeklappt beim Oeffnen, nur am PC,
# Stichwoerter fuer die Suche
AREAS = [
    {"id": "updates", "titel": "Updates", "offen": True,
     "stichwoerter": ["Update", "Version", "aktualisieren", "Desktop-Verknüpfung"]},
    {"id": "rundgang", "titel": fh.OPTIONS_TITLE,
     "stichwoerter": ["Rundgang", "Hilfe", "Name", "Einführung"]},
    {"id": OPTIK_ID, "titel": OPTIK_TITLE,
     "stichwoerter": ["Schrift", "Schriftgröße", "groß", "Sehr groß",
                      "Farbe", "Darstellung", "Dunkel", "Hell", TEMPLATES_TITLE,
                      "Grundfarbe", "Hintergrund", "Eigene Farben", "Regler",
                      "Farbton", "Sättigung", "Helligkeit", "Akzent"]
     + [item["name"] for item in fisi_theme.PRESETS]
     + [item["name"] for item in fisi_theme.BACKGROUNDS]
     + list(fisi_theme.LIGHT_NAMES.values())},
    {"id": "tagesziel", "titel": "Tagesziel",
     "stichwoerter": ["Ziel", "Lernserie", "Erinnerung", "Aufgaben pro Tag"]},
    {"id": "abgleich", "titel": "Abgleich PC und Handy",
     "stichwoerter": ["Abgleich", "Repository", "Token", "Zugangsschlüssel", "GitHub"]},
    {"id": "sicherung", "titel": fsi.TITLE,
     "stichwoerter": ["Sicherung", "Backup", "wiederherstellen"]},
    {"id": "datenbank", "titel": "Datenbank", "nur_pc": True,
     "stichwoerter": ["Datenbank", "Speicherort", "FISI_DB_PATH"]},
    {"id": LEARN_ID, "titel": "Lerninhalte",
     "stichwoerter": ["Lerninhalte", "Anzahl", "Karteikarten gesamt",
                      "Rahmenplan", "Lernfeld", "Prüfungstermin", "Gewichtung", "AP1",
                      "AP2"]},
    {"id": "spiel", "titel": "Spiel",
     "stichwoerter": ["Spiel", "Wohnungen", "Miete", "Schwierigkeitsgrad"]},
    {"id": "loeschen", "titel": DELETE_TITLE,
     "stichwoerter": ["Löschen", "zurücksetzen", "Lerndaten", "Historie", "Spielstand",
                      "Bestenliste"]},
    {"id": DIAGNOSE_ID, "titel": DIAGNOSE_TITLE,
     "stichwoerter": ["Diagnose", "Werkzeuge", fdg.TITLE, "Problem", "Fehler",
                      "fehler.log", "Bericht", "melden", fle.TITLE, "Leistung",
                      "Messung", "Messdatei"],
     # nur am PC gesucht (die Hänger-Diagnose gibt es am Handy nicht)
     "stichwoerter_pc": [HANG_TITLE, "Hänger", "haenger.log", "hängt"]},
    # Ab 0.62.2 (E-B2, E-B3): ganz unten, beim Oeffnen der Optionen aufgeklappt
    {"id": ABOUT_ID, "titel": "Über das Programm", "aufgeklappt": True,
     "stichwoerter": ["Über", "Programm", "Version"]},
]
AREA_BY_ID = {area["id"]: area for area in AREAS}
AREA_BY_TITLE = {area["titel"]: area for area in AREAS}
# Stichwoerter, die (auch) den Unterbereich "Vorlagen" oeffnen
TEMPLATE_WORDS = ([TEMPLATES_TITLE, "Grundfarbe", "Hintergrund"]
                  + [item["name"] for item in fisi_theme.PRESETS]
                  + [item["name"] for item in fisi_theme.BACKGROUNDS]
                  + list(fisi_theme.LIGHT_NAMES.values()))


def tile_columns(font_factor):
    """Kacheln je Zeile in den Vorlagen am PC: sechs, bei "Sehr groß" drei."""
    return 3 if font_factor >= 1.3 else 6


def areas(pc=True):
    """Bereiche in der angezeigten Reihenfolge (am Handy ohne "nur PC")."""
    return [area for area in AREAS if pc or not area.get("nur_pc")]


def diagnose_sections(pc=True):
    """Zwischenueberschriften im Bereich "Diagnose und Werkzeuge"."""
    return [item for item in DIAGNOSE_SECTIONS if pc or not item.get("nur_pc")]


def sections(area_id, pc=True):
    """Ab 0.62.2: Zwischenueberschriften eines zusammengelegten Bereichs."""
    if area_id == DIAGNOSE_ID:
        return diagnose_sections(pc)
    return list(SECTIONS.get(area_id, []))


def section_title(area_id, section_id):
    """Titel einer Zwischenueberschrift (PC und Handy lesen ihn von hier)."""
    for item in sections(area_id):
        if item["id"] == section_id:
            return item["titel"]
    raise KeyError(section_id)


def opened_at_start(area_id):
    """E1: Nur "Updates" ist offen und kein Klappbereich (bis 0.59.1 auch
    "Problem melden", ab 0.59.2 im eingeklappten Bereich "Diagnose und
    Werkzeuge")."""
    return bool(AREA_BY_ID[area_id].get("offen"))


def unfolded_at_start(area_id):
    """Ab 0.62.2 (E-B3): Klappbereiche, die beim Oeffnen der Optionen
    aufgeklappt sind (nur "Über das Programm"). Mit .get, weil auch der
    Unterbereich "Vorlagen" in den Klappbereichen steht, aber kein Bereich
    der Liste ist."""
    return bool(AREA_BY_ID.get(area_id, {}).get("aufgeklappt"))


def state_key(area_id):
    return STATE_PREFIX + area_id


def search_options(query, pc=True):
    """Bereiche, deren Titel oder Stichwoerter query enthalten:
    [(id, titel, ausschnitt, vorlagen_oeffnen)]."""
    needle = str(query or "").strip().lower()
    if not needle:
        return []
    hits = []
    for area in areas(pc):
        all_words = area["stichwoerter"] + (area.get("stichwoerter_pc", []) if pc else [])
        words = [word for word in all_words if needle in word.lower()]
        if needle not in area["titel"].lower() and not words:
            continue
        templates = area["id"] == OPTIK_ID and any(
            needle in word.lower() for word in TEMPLATE_WORDS)
        shown = words or all_words
        detail = "Bereich in den Optionen: " + ", ".join(shown[:6])
        hits.append((area["id"], area["titel"], detail, templates))
    return hits


def hit_target(title, query=""):
    """Zu einem Treffer (Titel): (bereich_id, vorlagen_oeffnen)."""
    area = AREA_BY_TITLE.get(title)
    if area is None:
        return None, False
    needle = str(query or "").strip().lower()
    templates = area["id"] == OPTIK_ID and bool(needle) and any(
        needle in word.lower() for word in TEMPLATE_WORDS)
    return area["id"], templates
