#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FISI Lernplattform - Aufbau der Optionen (ab 0.59)
==================================================

Gemeinsam fuer PC (app_gui.py) und Handy (mobile/src/main.py), damit beide
dieselbe Reihenfolge, dieselben Beschriftungen und dieselbe Suche haben.

- AREAS: alle Bereiche der Optionen in der angezeigten Reihenfolge.
  "Updates" steht ganz oben (E2). Beim Oeffnen der Optionen sind alle
  Bereiche eingeklappt, ausser "Updates" und "Problem melden" (E1). Der
  Klappzustand wird nicht gespeichert (E4) - es gibt keine neue Einstellung.
- search_options(): Treffer fuer die Suche (Strg+F). Ein Treffer oeffnet die
  Optionen, klappt den Bereich (und ggf. den Unterbereich "Vorlagen") auf und
  springt hin (E5).
"""

import fisi_diagnose as fdg
import fisi_hilfe as fh
import fisi_leistung as fle
import fisi_rahmenplan as frp
import fisi_sicherung as fsi
import fisi_theme
from fisi_lernen import DELETE_TITLE

SEARCH_KIND = "Optionen"
# Schluessel-Anfang der gemerkten Klappzustaende (werden beim Oeffnen der
# Optionen vergessen, E4)
STATE_PREFIX = "optionen_"

# Unterbereich im Bereich "Farben" (Entscheidung F1)
TEMPLATES_ID = "vorlagen"
TEMPLATES_TITLE = "Vorlagen"
TEMPLATES_HINT = ("Ein Klick auf eine Vorlage stellt die Farben ein. Sind eigene Farben "
                  "gespeichert oder Regler bewegt, setzt er nur die Regler.")
TEMPLATES_TEXT = ("Die Grundfarbe ändert Buttons, Ringe, Balken und Banner, der "
                  "Hintergrund die Flächen und Karten. Fachbereichsfarben und Erfolg, "
                  "Fehler, Warnung bleiben gleich (in der hellen Darstellung etwas "
                  "dunkler, damit sie gut lesbar sind).")

# id, Titel, offen beim Oeffnen, nur am PC, Stichwoerter fuer die Suche
AREAS = [
    {"id": "updates", "titel": "Updates", "offen": True,
     "stichwoerter": ["Update", "Version", "aktualisieren", "Desktop-Verknüpfung"]},
    {"id": "rundgang", "titel": fh.OPTIONS_TITLE,
     "stichwoerter": ["Rundgang", "Hilfe", "Name", "Einführung"]},
    {"id": "schrift", "titel": fisi_theme.FONT_TITLE,
     "stichwoerter": ["Schrift", "Schriftgröße", "groß", "Sehr groß"]},
    {"id": "farben", "titel": "Farben",
     "stichwoerter": ["Farbe", "Darstellung", "Dunkel", "Hell", TEMPLATES_TITLE,
                      "Grundfarbe", "Hintergrund", "Eigene Farben", "Regler",
                      "Farbton", "Sättigung", "Helligkeit", "Akzent"]
     + [item["name"] for item in fisi_theme.PRESETS]
     + [item["name"] for item in fisi_theme.BACKGROUNDS]
     + list(fisi_theme.LIGHT_NAMES.values())},
    {"id": "tagesziel", "titel": "Tagesziel",
     "stichwoerter": ["Ziel", "Lernserie", "Erinnerung", "Aufgaben pro Tag"]},
    {"id": "rahmenplan", "titel": frp.OPTIONS_TITLE,
     "stichwoerter": ["Rahmenplan", "Lernfeld", "Prüfungstermin", "Gewichtung", "AP1",
                      "AP2"]},
    {"id": "abgleich", "titel": "Abgleich PC und Handy",
     "stichwoerter": ["Abgleich", "Repository", "Token", "Zugangsschlüssel", "GitHub"]},
    {"id": "sicherung", "titel": fsi.TITLE,
     "stichwoerter": ["Sicherung", "Backup", "wiederherstellen"]},
    {"id": "datenbank", "titel": "Datenbank", "nur_pc": True,
     "stichwoerter": ["Datenbank", "Speicherort", "FISI_DB_PATH"]},
    {"id": "problem", "titel": fdg.TITLE, "offen": True,
     "stichwoerter": ["Problem", "Fehler", "Bericht", "melden"]},
    {"id": "leistung", "titel": fle.TITLE,
     "stichwoerter": ["Leistung", "Messung", "Messdatei"]},
    {"id": "lerninhalte", "titel": "Lerninhalte",
     "stichwoerter": ["Lerninhalte", "Anzahl", "Karteikarten gesamt"]},
    {"id": "spiel", "titel": "Spiel",
     "stichwoerter": ["Spiel", "Wohnungen", "Miete", "Schwierigkeitsgrad"]},
    {"id": "loeschen", "titel": DELETE_TITLE,
     "stichwoerter": ["Löschen", "zurücksetzen", "Lerndaten", "Historie", "Spielstand",
                      "Bestenliste"]},
    {"id": "ueber", "titel": "Über das Programm",
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


def opened_at_start(area_id):
    """E1: Nur "Updates" und "Problem melden" sind beim Oeffnen offen."""
    return bool(AREA_BY_ID[area_id].get("offen"))


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
        words = [word for word in area["stichwoerter"] if needle in word.lower()]
        if needle not in area["titel"].lower() and not words:
            continue
        templates = area["id"] == "farben" and any(
            needle in word.lower() for word in TEMPLATE_WORDS)
        shown = words or area["stichwoerter"]
        detail = "Bereich in den Optionen: " + ", ".join(shown[:6])
        hits.append((area["id"], area["titel"], detail, templates))
    return hits


def hit_target(title, query=""):
    """Zu einem Treffer (Titel): (bereich_id, vorlagen_oeffnen)."""
    area = AREA_BY_TITLE.get(title)
    if area is None:
        return None, False
    needle = str(query or "").strip().lower()
    templates = area["id"] == "farben" and bool(needle) and any(
        needle in word.lower() for word in TEMPLATE_WORDS)
    return area["id"], templates
