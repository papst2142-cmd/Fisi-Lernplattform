#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FISI Lernplattform - Lernspiel (Spiellogik)
===========================================

Der Praxisteil zur Lernplattform: Der Spieler arbeitet bei einem IT-Dienst-
leister, der die IT eines Zugbetreibers betreut, und bearbeitet Tickets. Was
er kann, haengt vom echten Lernfortschritt ab (Wissensstand je Fachbereich).

Bewusst ohne Oberflaeche und nur mit der Standardbibliothek (plus den Farben
aus fisi_theme), damit PC- und Handy-App dieselbe Logik nutzen und sie sich
ohne Bildschirm testen laesst (test_spiel.py). Auch der Grundriss wird hier
beschrieben (building_shapes) und von beiden Oberflaechen nur gezeichnet.

Spielstand als Ereignisprotokoll: In der Datenbank steht nur, was passiert
ist (Profil gesetzt, Ticket erledigt, Ticket verschoben, Arbeitstag beendet).
Geld, Reputation, Rang, Lagerbestand und der aktuelle Arbeitstag werden immer
daraus berechnet. Nur so laesst sich der Stand von PC und Handy beim Abgleich
einfach vereinigen, ohne dass Zahlen doppelt zaehlen.

Die Inhalte (Aufgaben, Kollegen, Raeume, Story, Stellschrauben, Bauteile)
liegen als JSON in inhalte/spiel/.
"""

import copy
import hashlib
import itertools
import json
import math
import os
import uuid

from fisi_core import (
    CATEGORY_KEYS, CATEGORY_SHORT, CONTENT_DIR, PROJEKTARBEITEN, ipv4_values, raid_values,
    search_content,
)
from fisi_theme import C, CATEGORY_COLOR, mix

GAME_DIR = os.path.join(CONTENT_DIR, "spiel")

# Kurzname -> langer Name des Fachbereichs (wie in der Datenbank)
CAT_NAME = dict(CATEGORY_KEYS)
CAT_KEY = {name: key for key, name in CATEGORY_KEYS.items()}
CAT_ORDER = list(CATEGORY_KEYS)

# Die vier Achsen der Reputation (Schluessel, Anzeigename)
AXES = [
    ("fachkompetenz", "Fachkompetenz"),
    ("zuverlaessigkeit", "Zuverlässigkeit"),
    ("kundenzufriedenheit", "Kundenzufriedenheit"),
    ("sicherheit", "Sicherheitsbewusstsein"),
]
AXIS_KEYS = [key for key, _name in AXES]

PRIORITIES = ["niedrig", "normal", "hoch", "kritisch"]
TASK_TYPES = ("auswahl", "zuordnung", "bauteile", "bestellung", "rack", "formular",
              "terminal", "diagnose", "wartung")
# Typen, deren Rueckmeldung eine Liste von Problemen ist
PROBLEM_TYPES = ("bauteile", "bestellung", "rack", "formular", "terminal", "diagnose",
                 "wartung")

# Ereignistypen im Protokoll
EV_PROFILE = "profil_gesetzt"
EV_SOLVED = "ticket_erledigt"
EV_DEFERRED = "ticket_verschoben"
EV_DAY_END = "tag_beendet"
# Wohnung (ab 0.30): Umzug und Moebel kosten Geld, die Einrichtung selbst
# ist ein Schnappschuss ("juengster Stand gewinnt", wie das Profil)
EV_MOVE = "umzug"
EV_BUY = "moebel_gekauft"
EV_SELL = "moebel_verkauft"
EV_LAYOUT = "einrichtung_gesetzt"
# Austausch (ab 0.32): Ersatzteil fehlt im Lager und wird nachbestellt
EV_SPARE_ORDER = "ersatzteil_bestellt"
# Eigenes Unternehmen (ab 0.33): Gruendung, Mitarbeiter, Weiterbildung und
# Ausbau stehen mit allen Werten im Ereignis (Bewerber, Gehalt, Kosten), damit
# PC und Handy nach dem Abgleich dieselbe Firma berechnen
EV_FOUNDED = "firma_gegruendet"
EV_HIRED = "mitarbeiter_eingestellt"
EV_FIRED = "mitarbeiter_gekuendigt"
EV_TRAINING = "weiterbildung"
EV_EXPAND = "gebaeude_erweitert"
# Angebote und Kundentickets (ab 0.34): Das Ergebnis eines Angebots steht mit
# Bitweiche-Preis und Geld im Ereignis; wer ein Kundenticket uebernimmt steht
# in ticket_delegiert, das Ergebnis im Feierabend (tag_beendet -> firma)
EV_OFFER_WON = "angebot_gewonnen"
EV_OFFER_LOST = "angebot_verloren"
EV_DELEGATED = "ticket_delegiert"
EV_PROJECT_WON = "projekt_gewonnen"
EV_PROJECT_LOST = "projekt_verloren"
EV_PROJECT_TEAM = "projekt_team"
# Sonderraeume im eigenen Gebaeude (ab 0.36): Lager, Besprechungsraum ...
EV_ROOM = "raum_ausgebaut"
FIRM_EVENTS = (EV_FOUNDED, EV_HIRED, EV_FIRED, EV_TRAINING, EV_EXPAND, EV_OFFER_WON,
               EV_OFFER_LOST, EV_DELEGATED, EV_PROJECT_WON, EV_PROJECT_LOST,
               EV_PROJECT_TEAM, EV_ROOM)

# Status eines Tickets am aktuellen Arbeitstag
ST_OPEN = "offen"
ST_RIGHT = "richtig"
ST_WRONG = "falsch"
ST_DEFERRED = "verschoben"
ST_WAITING = "wartet"          # Ersatzteil nachbestellt, kommt am naechsten Tag

# Laengen-Grenzen, damit die Texte auch auf dem Handy gut lesbar bleiben
MAX_TICKET_CHARS = 700
MAX_OPTION_CHARS = 110


# ============================================================================
#  AUSSEHEN DES PROTAGONISTEN
# ============================================================================
#
# Jede Wahl ist (Schluessel, Anzeigename). Die Farben stehen in *_COLORS.

APPEARANCE = {
    "haut": [("hell", "Hell"), ("mittel", "Mittel"), ("oliv", "Oliv"),
             ("dunkel", "Dunkel")],
    "frisur": [("kurz", "Kurz"), ("lang", "Lang"), ("zopf", "Zopf"),
               ("locken", "Locken"), ("glatze", "Glatze")],
    "haarfarbe": [("schwarz", "Schwarz"), ("braun", "Braun"), ("blond", "Blond"),
                  ("rot", "Rot"), ("grau", "Grau")],
    "oberteil": [("cyan", "Cyan"), ("pink", "Pink"), ("violett", "Violett"),
                 ("gruen", "Grün"), ("orange", "Orange")],
    "extra": [("keins", "Nichts"), ("brille", "Brille"), ("headset", "Headset"),
              ("kappe", "Kappe")],
    # Kreis um die Spielfigur im Grundriss und im Buero
    "kreis": [("pink", "Pink"), ("cyan", "Cyan"), ("gruen", "Grün"),
              ("violett", "Violett"), ("orange", "Orange"), ("gelb", "Gelb")],
}
APPEARANCE_LABELS = [("haut", "Hautton"), ("frisur", "Frisur"),
                     ("haarfarbe", "Haarfarbe"), ("oberteil", "Oberteil"),
                     ("extra", "Accessoire"), ("kreis", "Kreis im Büro")]
DEFAULT_APPEARANCE = {part: options[0][0] for part, options in APPEARANCE.items()}

SKIN_COLORS = {"hell": "#F5D0B5", "mittel": "#D9A47E", "oliv": "#B98A5E",
               "dunkel": "#7A5238"}
HAIR_COLORS = {"schwarz": "#2B2233", "braun": "#6B4226", "blond": "#E8C872",
               "rot": "#C2562E", "grau": "#B8B4C4"}
# Oberteil in den Farben der Palette (fisi_theme.C)
SHIRT_COLORS = {"cyan": "#22D3EE", "pink": "#F472B6", "violett": "#A78BFA",
                "gruen": "#34D399", "orange": "#FB923C"}
EXTRA_COLOR = "#1B1031"
RING_COLORS = {"pink": "#F472B6", "cyan": "#22D3EE", "gruen": "#34D399",
               "violett": "#A78BFA", "orange": "#FB923C", "gelb": "#FBBF24"}


def normalize_appearance(appearance):
    """Unbekannte oder fehlende Werte durch die Voreinstellung ersetzen."""
    result = dict(DEFAULT_APPEARANCE)
    for part, options in APPEARANCE.items():
        value = (appearance or {}).get(part)
        if value in [key for key, _name in options]:
            result[part] = value
    return result


def avatar_shapes(appearance):
    """Beschreibt den Avatar als einfache Formen auf einer 100 x 100 Flaeche.

    Rueckgabe: Liste von (art, (x1, y1, x2, y2), farbe) mit art "oval",
    "rect" (abgerundet) oder "line". PC (Canvas) und Handy (Flet-Canvas)
    zeichnen daraus dasselbe Bild.
    """
    look = normalize_appearance(appearance)
    skin = SKIN_COLORS[look["haut"]]
    hair = HAIR_COLORS[look["haarfarbe"]]
    shirt = SHIRT_COLORS[look["oberteil"]]
    shapes = []

    # Haare hinter dem Kopf (lang, Zopf)
    if look["frisur"] == "lang":
        shapes.append(("rect", (26, 24, 74, 72), hair))
    elif look["frisur"] == "zopf":
        shapes.append(("oval", (64, 34, 84, 62), hair))

    # Oberkoerper und Hals
    shapes.append(("rect", (18, 70, 82, 104), shirt))
    shapes.append(("rect", (43, 58, 57, 74), skin))
    # Kopf
    shapes.append(("oval", (30, 20, 70, 64), skin))

    # Haare oben
    if look["frisur"] in ("kurz", "lang", "zopf"):
        shapes.append(("oval", (28, 16, 72, 40), hair))
    elif look["frisur"] == "locken":
        for x in (28, 38, 48, 58):
            shapes.append(("oval", (x, 12, x + 16, 30), hair))
        shapes.append(("oval", (24, 22, 38, 38), hair))
        shapes.append(("oval", (62, 22, 76, 38), hair))

    # Augen und Mund
    shapes.append(("oval", (40, 40, 45, 45), EXTRA_COLOR))
    shapes.append(("oval", (55, 40, 60, 45), EXTRA_COLOR))
    shapes.append(("line", (45, 53, 55, 53), EXTRA_COLOR))

    # Accessoire
    if look["extra"] == "brille":
        shapes.append(("line", (36, 42, 64, 42), EXTRA_COLOR))
        shapes.append(("oval", (36, 37, 48, 48), EXTRA_COLOR))
        shapes.append(("oval", (52, 37, 64, 48), EXTRA_COLOR))
        shapes.append(("oval", (38, 39, 46, 46), skin))
        shapes.append(("oval", (54, 39, 62, 46), skin))
        shapes.append(("oval", (40, 40, 45, 45), EXTRA_COLOR))
        shapes.append(("oval", (55, 40, 60, 45), EXTRA_COLOR))
    elif look["extra"] == "headset":
        shapes.append(("line", (28, 38, 32, 16), EXTRA_COLOR))
        shapes.append(("line", (32, 16, 68, 16), EXTRA_COLOR))
        shapes.append(("line", (68, 16, 72, 38), EXTRA_COLOR))
        shapes.append(("rect", (24, 36, 32, 50), EXTRA_COLOR))
        shapes.append(("rect", (68, 36, 76, 50), EXTRA_COLOR))
        shapes.append(("line", (28, 50, 42, 57), EXTRA_COLOR))
    elif look["extra"] == "kappe":
        shapes.append(("rect", (28, 14, 72, 30), shirt))
        shapes.append(("rect", (50, 26, 82, 32), shirt))
    return shapes


# ============================================================================
#  INHALTE LADEN UND PRUEFEN
# ============================================================================

def _lines(value):
    """Texte duerfen in den JSON-Dateien als Liste von Zeilen stehen."""
    if isinstance(value, list):
        return "\n".join(value)
    return value or ""


def load_game_content(folder=None):
    """Laedt alle Spielinhalte aus inhalte/spiel/ in ein Woerterbuch."""
    folder = folder or GAME_DIR

    def read(name):
        with open(os.path.join(folder, name + ".json"), encoding="utf-8") as handle:
            return json.load(handle)

    tasks = expand_variants(read("aufgaben"))
    if os.path.exists(os.path.join(folder, "aufgaben_vorlagen.json")):
        templates = read("aufgaben_vorlagen")
        tasks += expand_variants(templates.get("vorlagen", []), template=True)
    incidents = expand_variants(read("zwischenfaelle"))
    for task in tasks + incidents:
        for field in ("ticket", "hilfe", "erklaerung"):
            task[field] = _lines(task.get(field))
    for task in incidents:
        task["zwischenfall"] = True
    building = read("gebaeude")
    story = read("story")
    return {
        "aufgaben": tasks,
        "zwischenfaelle": incidents,
        "kollegen": read("kollegen"),
        "gebaeude": building,
        "kunden": read("kunden"),
        "wohnungen": read("wohnungen"),
        "story": {key: _story_value(value) for key, value in story.items()},
        "balancing": read("balancing"),
        "hardware": read("hardware"),
        "firma": read("firma") if os.path.exists(os.path.join(folder, "firma.json")) else {},
        # Die 50 Testprojekte aus dem Lernbereich (Kundenprojekte ab 0.35)
        "projektarbeiten": PROJEKTARBEITEN,
    }


# ============================================================================
#  VORLAGEN: EIN AUFTRAG, VIELE VARIANTEN (ab 0.32)
# ============================================================================
#
# Ein Eintrag mit "varianten" wird beim Laden zu mehreren festen Auftraegen:
# Jede Variante ersetzt die Platzhalter {{name}} in allen Texten durch ihre
# "werte" und darf einzelne Felder ueberschreiben (z.B. ab_tag, raum, daten).
# Die erste Variante behaelt die Kennung, die weiteren heissen "<id>#2",
# "<id>#3" ... So sehen PC und Handy dieselben Auftraege, jede Variante gibt
# es genau einmal, und die Inhaltspruefung prueft jede wie einen
# handgeschriebenen Auftrag.
#   wiederholen  {"start": 18, "abstand": 12}: Variante i bekommt ab_tag
#                start + i * abstand (wenn sie keinen eigenen hat)
#   auffaellig   (in einer Variante einer Wartung) Kennungen der Pruefpunkte,
#                die in dieser Variante auffaellig sind

PLACEHOLDER_OPEN = "{{"
VARIANT_MARK = "#"


def _fill(value, values):
    if isinstance(value, str):
        for key, text in values.items():
            value = value.replace("{{%s}}" % key, str(text))
        return value
    if isinstance(value, list):
        return [_fill(item, values) for item in value]
    if isinstance(value, dict):
        return {key: _fill(item, values) for key, item in value.items()}
    return value


def expand_variants(items, template=False):
    """Loest Eintraege mit "varianten" in einzelne Auftraege auf.
    template=True markiert die Ergebnisse als Vorlagen-Auftraege."""
    result = []
    for item in items:
        variants = item.get("varianten")
        if not variants:
            task = dict(item)
            if template:
                task["vorlage"] = item["id"]
            result.append(task)
            continue
        base = {key: value for key, value in item.items()
                if key not in ("varianten", "wiederholen")}
        repeat = item.get("wiederholen") or {}
        for number, variant in enumerate(variants):
            task = _fill(copy.deepcopy(base), variant.get("werte") or {})
            for key, value in variant.items():
                if key not in ("werte", "auffaellig"):
                    task[key] = copy.deepcopy(value)
            if "auffaellig" in variant:
                # Wartung: Liste der auffaelligen Pruefpunkte dieser Variante
                for point in task.get("pruefpunkte") or []:
                    point["auffaellig"] = point["id"] in variant["auffaellig"]
            if "ab_tag" not in variant and repeat:
                task["ab_tag"] = repeat.get("start", 1) + number * repeat.get("abstand", 1)
            task["id"] = item["id"] if number == 0 else "%s%s%d" % (item["id"], VARIANT_MARK,
                                                                     number + 1)
            task["gruppe"] = item["id"]
            if template:
                task["vorlage"] = item["id"]
            result.append(task)
    return result


def _leftover_placeholder(value):
    if isinstance(value, str):
        return PLACEHOLDER_OPEN in value
    if isinstance(value, list):
        return any(_leftover_placeholder(item) for item in value)
    if isinstance(value, dict):
        return any(_leftover_placeholder(item) for item in value.values())
    return False


def _story_value(value):
    """Story-Texte: Liste von Zeilen (ein Text), Liste von Listen (mehrere
    Texte, die sich abwechseln) oder {tag: Zeilen} (Szenen je Arbeitstag)."""
    if isinstance(value, dict):
        return {key: _lines(item) for key, item in value.items()}
    if isinstance(value, list) and value and isinstance(value[0], list):
        return [_lines(item) for item in value]
    return _lines(value)


GAME = load_game_content()


WRONG_DELIVERY = "falschlieferung:"     # Kennung: falschlieferung:<bestellung>
STOCK_BASE = "grundbestand"             # Ersatzteilregal im Lager (hardware.json)


def task_by_id(task_id, content=None):
    content = content or GAME
    if task_id and task_id.startswith(WRONG_DELIVERY):
        return wrong_delivery_task(task_id[len(WRONG_DELIVERY):], content)
    for task in content["aufgaben"] + content.get("zwischenfaelle", []):
        if task["id"] == task_id:
            return task
    return None


def wrong_delivery_task(order_id, content=None, goods=""):
    """Zwischenfall nach einer falschen Bestellung: Die Ware ist trotzdem
    gekommen und muss zurueck (Vorlage "falschlieferung" in hardware.json).
    goods: Text, was geliefert wurde (setzt GameState.prepared_task ein)."""
    content = content or GAME
    order = next((task for task in content["aufgaben"] if task["id"] == order_id), None)
    template = content["hardware"].get("falschlieferung")
    if order is None or template is None:
        return None
    names = {"bestellung": order["titel"], "ware": goods or "die bestellte Ware"}
    task = {key: value for key, value in template.items() if not key.startswith("_")}
    task.update(id=WRONG_DELIVERY + order_id, typ="auswahl", zwischenfall=True,
                falschlieferung=order_id, titel=template["titel"].format(**names),
                ticket=_lines(template["ticket"]).format(**names),
                hilfe=_lines(template.get("hilfe")),
                erklaerung=_lines(template.get("erklaerung")))
    return task


def customer_people(content=None):
    """Personen beim Kunden (stehen in kunden.json bei ihrem Ort)."""
    return [dict(person, ort=place["id"])
            for place in (content or GAME).get("kunden", {}).get("orte", [])
            for person in place.get("personen", [])]


def all_people(content=None):
    """Alle Personen: Kollegen im Buero und Ansprechpartner beim Kunden."""
    content = content or GAME
    return list(content["kollegen"]) + customer_people(content)


def colleague(colleague_id, content=None):
    for person in all_people(content):
        if person["id"] == colleague_id:
            return person
    return None


def room(room_id, content=None):
    """Raum im Buero oder bei einem Kunden (Raum-IDs sind eindeutig)."""
    content = content or GAME
    buildings = [content["gebaeude"]] + [place["gebaeude"] for place in
                                         content.get("kunden", {}).get("orte", [])]
    # Raeume der eigenen Firma (ab 0.33) - die letzte Ausbaustufe hat alle
    stages = content.get("firma", {}).get("gebaeude", {}).get("stufen") or []
    if stages:
        buildings.append(stages[-1]["gebaeude"])
    for building in buildings:
        for item in building["raeume"]:
            if item["id"] == room_id:
                return item
    return None


def _validate_building(building, label, people, cat_rooms=True):
    """Raeume, Tueren und Einrichtung eines Grundrisses (Buero, Kunde,
    Wohnung) und die Plaetze der Personen darin."""
    problems = []
    view = {"gebaeude": building}
    for item in building["raeume"]:
        where = "%s-Raum %s" % (label, item.get("id"))
        if cat_rooms and not item.get("farbe") and item.get("cat") not in CATEGORY_KEYS:
            problems.append("%s: unbekannter Fachbereich '%s'" % (where, item.get("cat")))
        if not cat_rooms and not item.get("farbe"):
            problems.append("%s: Farbe fehlt" % where)
        if item["x"] < 0 or item["y"] < 0 or \
                item["x"] + item["w"] > building["breite"] or \
                item["y"] + item["h"] > building["hoehe"]:
            problems.append("%s: liegt ausserhalb des Grundrisses" % where)
        door = item.get("tuer")
        if door and door_side(item, view) in ("w", "o"):
            hall = building["flur"]
            if not max(item["y"], hall["y"]) <= door["von"] < door["bis"] <= \
                    min(item["y"] + item["h"], hall["y"] + hall["h"]):
                problems.append("%s: Seitentuer fuehrt nicht in den Flur" % where)
        elif door and not item["x"] <= door["von"] < door["bis"] <= item["x"] + item["w"]:
            problems.append("%s: Tuer liegt nicht an der Raumwand" % where)
        for deco in item.get("deko", []):
            if deco.get("typ") not in DECO_TYPES:
                problems.append("%s: unbekannte Einrichtung '%s'" % (where, deco.get("typ")))
            elif not _inside(deco, item):
                problems.append("%s: Einrichtung '%s' ragt aus dem Raum" % (where, deco["typ"]))
    hall = building.get("flur", {})
    hall_area = {"x": 0, "y": hall.get("y", 0), "w": building["breite"], "h": hall.get("h", 0)}
    for deco in hall.get("deko", []):
        if deco.get("typ") not in DECO_TYPES or not _inside(deco, hall_area):
            problems.append("%s-Flur: Einrichtung '%s' unbekannt oder ausserhalb"
                            % (label, deco.get("typ")))
    rooms = {item["id"]: item for item in building["raeume"]}
    for person in people:
        where = "Spiel-Person %s" % person.get("id")
        if person.get("raum") not in rooms:
            problems.append("%s: unbekannter Raum '%s'" % (where, person.get("raum")))
        elif person.get("platz"):
            x, y = person["platz"]
            if room_at(x, y, view) is not rooms[person["raum"]]:
                problems.append("%s: Platz liegt nicht im eigenen Raum" % where)
    return problems


def _validate_homes(content):
    """Wohnungen, Moebel und die Start-Einrichtung."""
    problems = []
    homes = content["wohnungen"]
    items = {item["id"]: item for item in homes["moebel"]}
    for item in homes["moebel"]:
        where = "Spiel-Moebel %s" % item.get("id")
        if item.get("typ") not in DECO_TYPES:
            problems.append("%s: unbekannter Typ '%s'" % (where, item.get("typ")))
        if not (item.get("w", 0) > 0 and item.get("h", 0) > 0 and item.get("preis", -1) >= 0):
            problems.append("%s: Groesse oder Preis fehlt" % where)
        if item.get("aktion") not in (None, "lernen", "schlafen"):
            problems.append("%s: unbekannte Aktion '%s'" % (where, item.get("aktion")))
    for piece, item_id in homes.get("start_moebel", {}).items():
        if item_id not in items:
            problems.append("Spiel-Wohnung: Start-Moebel '%s' unbekannt" % item_id)
    ids = [flat["id"] for flat in homes["wohnungen"]]
    if homes["start"] not in ids or len(set(ids)) != len(ids):
        problems.append("Spiel-Wohnung: Start-Wohnung fehlt oder Kennung doppelt")
    for flat in homes["wohnungen"]:
        label = "Spiel-Wohnung %s" % flat["id"]
        building = flat["gebaeude"]
        problems += _validate_building(building, label, [], cat_rooms=False)
        x, y, w, h = flat["kartons"]
        box = {"x": x, "y": y, "w": w, "h": h}
        if not any(_inside(box, area) for area in _areas(building)):
            problems.append("%s: Umzugskartons liegen ausserhalb" % label)
        # Start-Einrichtung: jedes Moebel muss dort stehen duerfen
        state = GameState([], content)
        state.home_id = flat["id"]
        state.furniture = dict(homes.get("start_moebel", {}))
        for piece, (px_, py_, turn) in (flat.get("einrichtung") or {}).get("moebel", {}).items():
            problem = placement_problem(state, piece, state.furniture.get(piece), px_, py_,
                                        turn, {"moebel": {}, "boeden": {}}, content)
            if problem:
                problems.append("%s: Start-Einrichtung: %s" % (label, problem))
    return problems


def _validate_rent(content):
    """Mietwerte (ab 0.31): jede Wohnung hat eine Miete, die Startwohnung
    ist mietfrei, die Kaution ist ein Anteil des Kaufpreises."""
    problems = []
    rules = content["balancing"].get("miete")
    if not isinstance(rules, dict):
        return ["Spiel-Balancing: Abschnitt 'miete' fehlt"]
    share = rules.get("kaution_anteil")
    if not isinstance(share, (int, float)) or not 0 <= share <= 1:
        problems.append("Spiel-Balancing: kaution_anteil muss zwischen 0 und 1 liegen")
    per_day = rules.get("pro_tag") or {}
    homes = content["wohnungen"]
    for flat in homes["wohnungen"]:
        value = per_day.get(flat["id"])
        if not isinstance(value, int) or value < 0:
            problems.append("Spiel-Balancing: keine gueltige Miete fuer Wohnung '%s'"
                            % flat["id"])
    if per_day.get(homes["start"]):
        problems.append("Spiel-Balancing: die Startwohnung muss mietfrei sein")
    for key in per_day:
        if key not in {flat["id"] for flat in homes["wohnungen"]}:
            problems.append("Spiel-Balancing: Miete fuer unbekannte Wohnung '%s'" % key)
    return problems


def validate_game_content(content=None):
    """Prueft die Spielinhalte auf formale Fehler. Leere Liste = in Ordnung.
    Wird von fisi_core.validate_content() mit aufgerufen."""
    content = content or GAME
    problems = []
    site_rooms = {SITE_OFFICE: {item["id"] for item in content["gebaeude"]["raeume"]}}
    for stage in (content.get("firma") or {}).get("gebaeude", {}).get("stufen", [])[-1:]:
        site_rooms["firma"] = {item["id"] for item in stage["gebaeude"]["raeume"]}
    for place in customer_places(content):
        site_rooms[place["id"]] = {item["id"] for item in place["gebaeude"]["raeume"]}
    rooms = set().union(*site_rooms.values())
    all_room_ids = [rid for ids in site_rooms.values() for rid in ids]
    if len(all_room_ids) != len(set(all_room_ids)):
        problems.append("Spiel: Raum-Kennungen sind nicht eindeutig")
    people = {item["id"] for item in all_people(content)}
    if len(people) != len(all_people(content)):
        problems.append("Spiel: Personen-Kennungen sind nicht eindeutig")
    balancing = content["balancing"]

    problems += _validate_building(content["gebaeude"], "Spiel", content["kollegen"])
    for place in customer_places(content):
        problems += _validate_building(place["gebaeude"], "Spiel-Kunde %s" % place["id"],
                                       place.get("personen", []))
    problems += _validate_homes(content)
    problems += _validate_rent(content)
    problems += _validate_firm(content)

    per_day = balancing["tickets_pro_tag"]
    for rank in balancing["raenge"]:
        if rank["name"] not in balancing["gehalt_pro_tag"]:
            problems.append("Spiel-Balancing: kein Gehalt fuer Rang '%s'" % rank["name"])
        if isinstance(per_day, dict) and not per_day.get(rank["name"], 0) >= 1:
            problems.append("Spiel-Balancing: keine Tickets pro Tag fuer Rang '%s'"
                            % rank["name"])
    days = [rank.get("ab_tag", 1) for rank in balancing["raenge"]]
    if days != sorted(days) or days[0] != 1:
        problems.append("Spiel-Balancing: ab_tag der Raenge muss bei 1 beginnen und steigen")

    problems += _validate_hardware(content)
    problems += _validate_rack_hardware(content)
    problems += _validate_wrong_delivery(content)

    seen = set()
    tickets_seen = {}
    for number, task in enumerate(content["aufgaben"] + content.get("zwischenfaelle", []),
                                  start=1):
        where = "Spiel-Aufgabe Nr. %d (%s)" % (number, task.get("id"))
        for field in ("id", "typ", "titel", "auftraggeber", "raum", "prioritaet",
                      "cat", "ticket", "frage", "hilfe", "erklaerung",
                      "suchbegriffe", "belohnung"):
            if not task.get(field):
                problems.append("%s: Feld '%s' fehlt oder ist leer" % (where, field))
        if task.get("id") in seen:
            problems.append("%s: Kennung doppelt vorhanden" % where)
        if _leftover_placeholder(task):
            problems.append("%s: Platzhalter {{...}} ohne Wert" % where)
        if task.get("ticket") in tickets_seen:
            problems.append("%s: gleicher Tickettext wie '%s'"
                            % (where, tickets_seen[task.get("ticket")]))
        tickets_seen[task.get("ticket")] = task.get("id")
        seen.add(task.get("id"))
        if task.get("typ") not in TASK_TYPES:
            problems.append("%s: unbekannter Typ '%s'" % (where, task.get("typ")))
        if task.get("raum") not in rooms:
            problems.append("%s: unbekannter Raum '%s'" % (where, task.get("raum")))
        if task.get("auftraggeber") not in people:
            problems.append("%s: unbekannter Auftraggeber '%s'"
                            % (where, task.get("auftraggeber")))
        else:
            site = task_site(task, content)
            person = colleague(task["auftraggeber"], content)
            start = task.get("ab_tag", 1)
            if start < person.get("ab_tag", 1):
                problems.append("%s: %s ist erst ab Tag %d da"
                                % (where, person["id"], person["ab_tag"]))
            if person.get("bis_tag") is not None and start > person["bis_tag"] and \
                    not person.get("nachfolger"):
                problems.append("%s: %s ist nur bis Tag %d da"
                                % (where, person["id"], person["bis_tag"]))
            place = customer_place(site, content)
            if place and start < place.get("ab_tag", 1):
                problems.append("%s: Ort '%s' gibt es erst ab Tag %d"
                                % (where, site, place["ab_tag"]))
            if site not in site_rooms:
                problems.append("%s: unbekannter Ort '%s'" % (where, site))
            elif task.get("raum") not in site_rooms[site]:
                problems.append("%s: Raum '%s' liegt nicht am Ort '%s'"
                                % (where, task.get("raum"), site))
            elif task.get("stelle"):
                view = site_content(site, None, content)
                x, y = task["stelle"]
                spot_room = room_at(x, y, view)
                if spot_room is None or spot_room["id"] != task["raum"]:
                    problems.append("%s: Stelle liegt nicht im Raum '%s'"
                                    % (where, task["raum"]))
                elif _cell(x, y) not in _base_grid(view["gebaeude"]):
                    problems.append("%s: an der Stelle kann niemand stehen" % where)
        if task.get("prioritaet") not in PRIORITIES:
            problems.append("%s: unbekannte Prioritaet" % where)
        if task.get("cat") not in CATEGORY_KEYS:
            problems.append("%s: unbekannter Fachbereich '%s'" % (where, task.get("cat")))
        for key, value in (task.get("anforderungen") or {}).items():
            if key not in CATEGORY_KEYS or not 0 <= value <= 100:
                problems.append("%s: ungueltige Anforderung %s: %s" % (where, key, value))
        for axis in task.get("achsen") or []:
            if axis not in AXIS_KEYS:
                problems.append("%s: unbekannte Reputations-Achse '%s'" % (where, axis))
        if len(task.get("ticket", "")) > MAX_TICKET_CHARS:
            problems.append("%s: Tickettext laenger als %d Zeichen (Handy)"
                            % (where, MAX_TICKET_CHARS))

        if task.get("nach") and not task_by_id(task["nach"], content):
            problems.append("%s: Voraussetzung '%s' gibt es nicht" % (where, task["nach"]))
        if task.get("empfaenger") and task["empfaenger"] not in people:
            problems.append("%s: unbekannter Empfaenger '%s'" % (where, task["empfaenger"]))
        if task.get("typ") in ("bauteile", "bestellung"):
            problems += ["%s: %s" % (where, text)
                         for text in _validate_hardware_task(task, content)]
        elif task.get("typ") == "rack":
            problems += ["%s: %s" % (where, text)
                         for text in _validate_rack_task(task, content)]
        elif task.get("typ") == "formular":
            problems += ["%s: %s" % (where, text)
                         for text in _validate_form_task(task, content)]
        elif task.get("typ") == "terminal":
            problems += ["%s: %s" % (where, text)
                         for text in _validate_terminal_task(task, content)]
        elif task.get("typ") == "diagnose":
            problems += ["%s: %s" % (where, text)
                         for text in _validate_diagnosis_task(task, content)]
        elif task.get("typ") == "wartung":
            problems += ["%s: %s" % (where, text)
                         for text in _validate_maintenance_task(task, content)]

        if task.get("typ") == "auswahl":
            options = task.get("optionen") or []
            if len(options) < 2 or len(set(options)) != len(options):
                problems.append("%s: braucht mindestens 2 verschiedene Antworten" % where)
            if task.get("antwort") not in options:
                problems.append("%s: richtige Antwort steht nicht in den Optionen" % where)
            texts = options
        elif task.get("typ") == "zuordnung":
            pairs = task.get("paare") or []
            lefts = [pair[0] for pair in pairs]
            rights = [pair[1] for pair in pairs]
            if len(pairs) < 2 or len(set(lefts)) != len(lefts) or \
                    len(set(rights)) != len(rights):
                problems.append("%s: braucht mindestens 2 eindeutige Paare" % where)
            texts = lefts + rights
        else:
            texts = []
        for text in texts:
            if len(text) > MAX_OPTION_CHARS:
                problems.append("%s: Antwort laenger als %d Zeichen (Handy): %s"
                                % (where, MAX_OPTION_CHARS, text[:40]))

        # Jeder Suchbegriff muss in Karteikarten oder Quizfragen etwas finden,
        # sonst laeuft der Verweis zurueck ins Lernen ins Leere.
        for term in task.get("suchbegriffe") or []:
            if not learn_links_for_term(term, limit=1):
                problems.append("%s: Suchbegriff '%s' findet keine Karteikarte "
                                "oder Quizfrage" % (where, term))
    return problems


def _validate_wrong_delivery(content):
    """Vorlage "falschlieferung" in hardware.json (Zwischenfall nach einer
    falschen Bestellung)."""
    template = content["hardware"].get("falschlieferung")
    if not template:
        return ["hardware.json: Vorlage 'falschlieferung' fehlt"]
    problems = []
    for field in ("titel", "auftraggeber", "raum", "prioritaet", "cat", "ticket", "frage",
                  "optionen", "antwort", "hilfe", "erklaerung", "belohnung"):
        if not template.get(field):
            problems.append("falschlieferung: Feld '%s' fehlt" % field)
    if template.get("antwort") not in (template.get("optionen") or []):
        problems.append("falschlieferung: Antwort steht nicht in den Optionen")
    if colleague(template.get("auftraggeber"), content) is None:
        problems.append("falschlieferung: unbekannter Auftraggeber")
    if template.get("raum") not in [item["id"] for item in content["gebaeude"]["raeume"]]:
        problems.append("falschlieferung: unbekannter Raum")
    try:
        _lines(template.get("ticket")).format(bestellung="x", ware="y")
        template.get("titel", "").format(bestellung="x", ware="y")
    except (KeyError, IndexError, ValueError):
        problems.append("falschlieferung: nur {bestellung} und {ware} als Platzhalter")
    return problems


def _validate_hardware(content):
    """Bauteile und Haendler in hardware.json."""
    problems, seen = [], set()
    hardware = content["hardware"]
    for item in hardware["teile"]:
        where = "Spiel-Bauteil %s" % item.get("id")
        if item.get("id") in seen:
            problems.append("%s: Kennung doppelt vorhanden" % where)
        seen.add(item.get("id"))
        if item.get("typ") not in PART_FIELDS or item.get("typ") not in hardware["typen"]:
            problems.append("%s: unbekannter Typ '%s'" % (where, item.get("typ")))
            continue
        if not item.get("name") or not item.get("preis", 0) > 0:
            problems.append("%s: Name oder Preis fehlt" % where)
        for field in PART_FIELDS[item["typ"]]:
            if field not in item:
                problems.append("%s: Feld '%s' fehlt" % (where, field))
        for form in [item.get("formfaktor")] + list(item.get("formfaktoren") or []):
            if form is not None and form not in hardware["formfaktoren"]:
                problems.append("%s: unbekannter Formfaktor '%s'" % (where, form))
    dealers = [item["id"] for item in hardware["haendler"]]
    if len(set(dealers)) != len(dealers):
        problems.append("Spiel-Haendler: Kennung doppelt vorhanden")
    # Ersatzteile fuer Austausch-Auftraege (ab 0.32)
    kinds = hardware.get("ersatz_typen", {})
    for item in hardware.get("ersatzteile", []):
        where = "Spiel-Ersatzteil %s" % item.get("id")
        if item.get("id") in seen:
            problems.append("%s: Kennung doppelt vorhanden" % where)
        seen.add(item.get("id"))
        if item.get("typ") not in kinds:
            problems.append("%s: unbekannter Typ '%s'" % (where, item.get("typ")))
            continue
        if not item.get("name") or not item.get("preis", 0) > 0:
            problems.append("%s: Name oder Preis fehlt" % where)
        for key, _name, _unit in spare_features(item["typ"], content):
            if key not in item:
                problems.append("%s: Merkmal '%s' fehlt" % (where, key))
    for kind in kinds:
        if not spare_features(kind, content):
            problems.append("Spiel-Ersatzteile: keine Merkmale fuer Typ '%s'" % kind)
    for part_id, count in hardware.get("grundbestand", {}).items():
        if part_id not in seen or not int(count) >= 1:
            problems.append("Spiel-Grundbestand: unbekanntes Teil '%s'" % part_id)
    if hardware.get("ersatzteile"):
        extra = hardware.get("nachbestellung", {})
        if extra.get("haendler") not in dealers or not extra.get("lieferzeit", 0) >= 1:
            problems.append("Spiel-Nachbestellung: Haendler oder Lieferzeit fehlt")
    return problems


def _validate_hardware_task(task, content):
    """Bauteile- und Bestell-Auftraege: Aufbau pruefen und durch Ausprobieren
    beweisen, dass es eine richtige Loesung gibt."""
    problems = []
    if task["typ"] == "bestellung":
        offers = task.get("angebote") or []
        needs = task.get("bedarf") or []
        if not offers or not needs:
            return ["Angebote oder Bedarf fehlen"]
        if not task.get("budget", 0) > 0 or not task.get("frist", 0) >= 1:
            problems.append("Budget oder Frist fehlt")
        ids = [offer.get("id") for offer in offers]
        if len(set(ids)) != len(ids):
            problems.append("Angebots-Kennung doppelt vorhanden")
        for need in needs:
            if (need.get("typ") not in content["hardware"]["typen"] and
                    need.get("typ") not in content["hardware"].get("rack_typen", {}) and
                    need.get("typ") not in content["hardware"].get("ersatz_typen", {})) or \
                    not need.get("text") or not need.get("menge", 0) >= 1:
                problems.append("Bedarf unvollstaendig: %s" % need.get("text"))
            for other in need.get("fuer") or []:
                if not part(other, content):
                    problems.append("Bedarf verweist auf unbekanntes Teil '%s'" % other)
        for offer in offers:
            if not part(offer.get("teil"), content):
                problems.append("Angebot %s: unbekanntes Teil" % offer.get("id"))
            elif not dealer(offer.get("haendler"), content):
                problems.append("Angebot %s: unbekannter Haendler" % offer.get("id"))
            elif not offer.get("preis", 0) > 0 or not offer.get("lieferzeit", 0) >= 1:
                problems.append("Angebot %s: Preis oder Lieferzeit fehlt" % offer.get("id"))
            else:
                item = part(offer["teil"], content)
                matching = [need for need in needs if not _need_mismatch(item, need, content)]
                if len(matching) > 1:
                    problems.append("Angebot %s passt zu mehreren Bedarfen" % offer["id"])
        if not problems and not valid_carts(task, content):
            problems.append("keine gueltige Bestellung moeglich")
        return problems

    slots = task.get("slots") or []
    if not slots or any(slot not in SLOT_ORDER for slot in slots):
        return ["Steckplaetze fehlen oder sind unbekannt"]
    for part_id in task.get("teile") or []:
        if not part(part_id, content):
            problems.append("unbekanntes Bauteil '%s'" % part_id)
    for slot in (task.get("optional") or []) + (task.get("aus_lager") or []):
        if slot not in slots:
            problems.append("'%s' ist kein Steckplatz dieses Auftrags" % slot)
    for key in task.get("vorgaben") or {}:
        if key not in BUILD_RULES:
            problems.append("unbekannte Vorgabe '%s'" % key)
    if problems:
        return problems
    # Welche Teile koennen aus dem Lager dazukommen? Jede gueltige Bestellung
    # des vorigen Auftrags muss zum Ziel fuehren.
    extras = [[]]
    if task.get("aus_lager"):
        first = task_by_id(task.get("nach"), content)
        if not first or first["typ"] != "bestellung":
            return ["Teile aus dem Lager brauchen eine Bestellung als Voraussetzung"]
        extras = []
        if not valid_carts(first, content):
            return ["die Bestellung davor ('%s') hat keine gueltige Loesung" % first["id"]]
        for cart in valid_carts(first, content):
            ids = [offer["teil"] for offer in first["angebote"] if cart.get(offer["id"])]
            extras.append([pid for pid in ids if part(pid, content)["typ"] in task["aus_lager"]])
        problems += _stock_users_problems(first, content)
    for extra in extras:
        available = list(task.get("teile") or []) + [p for p in extra
                                                     if p not in task.get("teile", [])]
        if find_solution(task, available, content) is None:
            problems.append("PC laesst sich mit den bereitliegenden Teilen nicht bauen")
            break
    return problems


# ============================================================================
#  WISSENSSTAND (AUS DEM LERNFORTSCHRITT)
# ============================================================================

def knowledge_from_answers(answers, coverage, params=None):
    """Wissensstand 0-100 je Fachbereich (Kurzname).

    answers:  {kurzname: [True/False, ...]} - neueste Antwort zuerst
    coverage: {kurzname: Prozent der bereits bearbeiteten Inhalte}

    Erfolgsquote: gewichteter Anteil richtiger Antworten, neuere zaehlen
    staerker (lineare Gewichtung). Bei wenigen Antworten wird die Quote
    anteilig abgesenkt, damit drei Glueckstreffer nicht 100 % ergeben.
    Abdeckung: volle Wirkung ab volle_abdeckung_prozent, darunter gedaempft
    ueber den Exponenten (Wurzel), damit der Wert bei vielen Inhalten nicht
    lange bei fast 0 klebt.
    """
    params = params or GAME["balancing"]["wissen"]
    window = max(1, int(params["letzte_antworten"]))
    minimum = max(1, int(params["mindest_antworten"]))
    full = max(1.0, float(params["volle_abdeckung_prozent"]))
    exponent = float(params["abdeckung_exponent"])

    result = {}
    for key in CAT_ORDER:
        recent = list(answers.get(key) or [])[:window]
        if recent:
            weights = [len(recent) - index for index in range(len(recent))]
            quote = sum(w for w, ok in zip(weights, recent) if ok) / float(sum(weights))
            quote *= min(1.0, len(recent) / float(minimum))
        else:
            quote = 0.0
        share = min(1.0, max(0.0, float(coverage.get(key, 0.0))) / full)
        result[key] = round(100.0 * quote * (share ** exponent), 1)
    return result


def knowledge(db, params=None):
    """Wissensstand je Fachbereich aus der Lern-Datenbank. Wird nie
    gespeichert, sondern bei Bedarf neu berechnet."""
    from fisi_core import content_totals
    params = params or GAME["balancing"]["wissen"]
    window = int(params["letzte_antworten"])
    answers = {}
    for name, key in CAT_KEY.items():
        rows = db._execute(
            "SELECT correct FROM ("
            "  SELECT timestamp, id, correct, 0 AS src FROM quiz_answers WHERE category = ?"
            "  UNION ALL"
            "  SELECT timestamp, id, correct, 1 AS src FROM card_events"
            "  WHERE category = ? AND correct IS NOT NULL"
            ") ORDER BY timestamp DESC, id DESC LIMIT ?",
            (name, name, window), fetch="all", default=[]) or []
        answers[key] = [bool(row[0]) for row in rows]
    coverage = {CAT_KEY[name]: value
                for name, value in db.category_coverage(content_totals()).items()
                if name in CAT_KEY}
    return knowledge_from_answers(answers, coverage, params)


def requirement_gaps(task, levels):
    """Fachbereiche, in denen der Wissensstand unter der Anforderung liegt.
    Rueckgabe: Liste von (kurzname, benoetigt, vorhanden)."""
    gaps = []
    for key, need in (task.get("anforderungen") or {}).items():
        have = levels.get(key, 0.0)
        if have < need:
            gaps.append((key, need, have))
    return gaps


def gap_warning(gaps):
    """Warnhinweis der weichen Sperre als Text (leer, wenn nichts fehlt)."""
    if not gaps:
        return ""
    parts = ["%s (%d %% nötig, du hast %d %%)" % (CATEGORY_SHORT[CAT_NAME[key]], need,
                                                   int(have))
             for key, need, have in gaps]
    return ("Dafür fehlt dir noch Wissen: %s. Du kannst das Ticket trotzdem "
            "bearbeiten, ein Fehler kostet dann aber doppelt Reputation. Tipp: "
            "Vorher ein paar Karteikarten in diesem Bereich lernen."
            % ", ".join(parts))


# ============================================================================
#  VERWEISE ZURUECK INS LERNEN
# ============================================================================

_LEARN_CACHE = {}


def learn_links_for_term(term, limit=6):
    hits = _LEARN_CACHE.get(term)
    if hits is None:
        hits = _LEARN_CACHE[term] = [hit for hit in search_content(term)
                                     if hit[0] in ("Karteikarte", "Quizfrage")]
    return hits[:limit]


def learn_links(task, limit=6):
    """Passende Karteikarten und Quizfragen zu einer Aufgabe, bevorzugt aus
    ihrem Fachbereich. Rueckgabe wie search_content: (Art, Fachbereich,
    Titel, Detail)."""
    home = CAT_NAME.get(task.get("cat"))
    found, seen = [], set()
    for term in task.get("suchbegriffe") or []:
        hits = learn_links_for_term(term, limit=50)
        # Treffer im eigenen Fachbereich und mit dem Begriff in der Frage
        # selbst (nicht nur in der Erklaerung) zuerst
        hits.sort(key=lambda hit: (hit[1] != home, term.lower() not in hit[2].lower()))
        for hit in hits:
            if hit[2] not in seen:
                seen.add(hit[2])
                found.append(hit)
    return found[:limit]


# ============================================================================
#  BAUTEILE UND BESTELLUNGEN
# ============================================================================
#
# Die Bauteile stehen in inhalte/spiel/hardware.json. Die Pruefungen liefern
# Saetze auf Deutsch, damit das Spiel nach dem Einreichen genau sagen kann,
# was nicht passt - gleiche Texte auf PC und Handy.

# Steckplaetze eines PCs in der Reihenfolge, in der man ihn zusammenbaut
SLOT_ORDER = ("mainboard", "cpu", "ram", "ssd", "gpu", "netzteil", "gehaeuse")
# Pflichtwerte je Bauteil-Typ (fuer die Inhaltspruefung)
PART_FIELDS = {
    "mainboard": ("sockel", "ram_typ", "formfaktor", "ram_slots", "m2"),
    "cpu": ("sockel", "tdp", "igpu"),
    "ram": ("ram_typ", "groesse", "module"),
    "ssd": ("anschluss", "groesse"),
    "gpu": ("watt",),
    "netzteil": ("watt",),
    "gehaeuse": ("formfaktoren",),
    "notebook": ("groesse",),
}
# Vorgaben eines PC-Auftrags
BUILD_RULES = ("ram_min", "speicher_min", "grafikkarte", "budget")
# Einheiten der Mindestwerte bei Bestellungen
UNITS = {"groesse": "GB", "watt": "W", "leistung": "W", "ports": "Ports"}


def part(part_id, content=None):
    """Bauteil (PC) oder Rack-Geraet - beides laesst sich bestellen und liegt
    dann im Lager."""
    hardware = (content or GAME)["hardware"]
    for item in hardware["teile"] + hardware.get("ersatzteile", []):
        if item["id"] == part_id:
            return item
    return rack_device(part_id, content)


def dealer(dealer_id, content=None):
    for item in (content or GAME)["hardware"]["haendler"]:
        if item["id"] == dealer_id:
            return item
    return None


def slot_name(slot, content=None):
    return (content or GAME)["hardware"]["typen"].get(slot, slot)


def _form(value, content):
    return (content or GAME)["hardware"]["formfaktoren"].get(value, value)


def psu_needed(cpu, gpu=None, content=None):
    """Noetige Netzteil-Leistung in Watt: (CPU + Grafikkarte + Grundlast)
    mal Reserve, aufgerundet."""
    rules = (content or GAME)["hardware"]["regeln"]
    load = (cpu["tdp"] if cpu else 0) + (gpu["watt"] if gpu else 0) + rules["grundlast_watt"]
    return int(math.ceil(load * rules["netzteil_reserve"] - 1e-9))


def compatibility_problems(parts, content=None):
    """Prueft Bauteile untereinander. parts = {typ: bauteil}. Geprueft wird
    nur, was zusammen vorkommt - so passt die Funktion fuer den halben PC
    (Bestellung: "passt dieser RAM zum Mainboard?") wie fuer den ganzen."""
    board = parts.get("mainboard")
    cpu = parts.get("cpu")
    ram = parts.get("ram")
    ssd = parts.get("ssd")
    case = parts.get("gehaeuse")
    psu = parts.get("netzteil")
    problems = []
    if board and cpu and cpu["sockel"] != board["sockel"]:
        problems.append("Die CPU (Sockel %s) passt nicht auf das Mainboard (Sockel %s)."
                        % (cpu["sockel"], board["sockel"]))
    if board and ram:
        if ram["ram_typ"] != board["ram_typ"]:
            problems.append("Der Arbeitsspeicher ist %s, das Mainboard braucht %s."
                            % (ram["ram_typ"], board["ram_typ"]))
        elif ram["module"] > board["ram_slots"]:
            problems.append("%d RAM-Module, aber das Mainboard hat nur %d Steckplätze."
                            % (ram["module"], board["ram_slots"]))
    if board and case and board["formfaktor"] not in case["formfaktoren"]:
        problems.append("Das Mainboard (%s) passt nicht ins Gehäuse (%s)."
                        % (_form(board["formfaktor"], content),
                           ", ".join(_form(f, content) for f in case["formfaktoren"])))
    if board and ssd and ssd["anschluss"] == "m2" and board["m2"] < 1:
        problems.append("Die SSD braucht einen M.2-Steckplatz, das Mainboard hat keinen "
                        "(nur SATA).")
    if psu and cpu:
        need = psu_needed(cpu, parts.get("gpu"), content)
        if psu["watt"] < need:
            problems.append("Das Netzteil ist zu schwach: %d W, gebraucht werden mindestens "
                            "%d W." % (psu["watt"], need))
    return problems


def build_problems(task, answer, available=None, content=None):
    """Alle Probleme eines zusammengebauten PCs (Aufgabentyp "bauteile").
    answer = {steckplatz: bauteil_id}, available = erlaubte Bauteil-IDs."""
    content = content or GAME
    answer = answer or {}
    available = task.get("teile", []) if available is None else available
    optional = task.get("optional") or []
    chosen, problems = {}, []
    for slot in task["slots"]:
        part_id = answer.get(slot)
        item = part(part_id, content) if part_id else None
        if item is None or item["typ"] != slot or part_id not in available:
            if slot not in optional:
                problems.append("%s fehlt noch." % slot_name(slot, content))
            continue
        chosen[slot] = item
    problems += compatibility_problems(chosen, content)
    cpu = chosen.get("cpu")
    if cpu and not cpu["igpu"] and "gpu" not in chosen:
        problems.append("Kein Bild: %s hat keine eingebaute Grafik und es steckt keine "
                        "Grafikkarte im PC." % cpu["name"])
    rules = task.get("vorgaben") or {}
    ram = chosen.get("ram")
    if ram and ram["groesse"] < rules.get("ram_min", 0):
        problems.append("Zu wenig Arbeitsspeicher: %d GB, verlangt sind mindestens %d GB."
                        % (ram["groesse"], rules["ram_min"]))
    ssd = chosen.get("ssd")
    if ssd and ssd["groesse"] < rules.get("speicher_min", 0):
        problems.append("Zu wenig Speicherplatz: %d GB, verlangt sind mindestens %d GB."
                        % (ssd["groesse"], rules["speicher_min"]))
    if rules.get("grafikkarte") and "gpu" not in chosen:
        problems.append("Der Auftrag verlangt eine Grafikkarte.")
    price = sum(item["preis"] for item in chosen.values())
    if rules.get("budget") and price > rules["budget"]:
        problems.append("Zu teuer: %d € bei %d € Budget." % (price, rules["budget"]))
    return problems


def _need_mismatch(item, need, content=None):
    """Warum passt ein Bauteil nicht zu einem Bedarf? Leerer Text = passt."""
    if item["typ"] != need["typ"]:
        return "wird nicht gebraucht"
    for other_id in need.get("fuer") or []:
        other = part(other_id, content)
        problems = compatibility_problems({other["typ"]: other, item["typ"]: item}, content)
        if problems:
            return problems[0]
    for key, value in (need.get("passt") or {}).items():
        if item.get(key) != value:
            labels = {name: (label, unit) for name, label, unit in
                      spare_features(item["typ"], content)}
            label, unit = labels.get(key, (key, ""))
            return "passt nicht: %s %s statt %s" % (
                label, _feature_value(item.get(key), unit), _feature_value(value, unit))
    for key, value in (need.get("min") or {}).items():
        if item.get(key, 0) < value:
            unit = UNITS.get(key, "")
            return "zu klein: %s %s, gebraucht werden mindestens %s %s" % (
                item.get(key, 0), unit, value, unit)
    return ""


def offer_need(offer, task, content=None):
    """Index des Bedarfs, den ein Angebot deckt, oder None."""
    item = part(offer["teil"], content)
    for index, need in enumerate(task["bedarf"]):
        if not _need_mismatch(item, need, content):
            return index
    return None


def cart_total(task, cart):
    """Gesamtpreis und laengste Lieferzeit eines Warenkorbs {angebot: menge}."""
    total, longest = 0, 0
    for offer in task["angebote"]:
        count = int(cart.get(offer["id"], 0) or 0)
        if count > 0:
            total += offer["preis"] * count
            longest = max(longest, offer["lieferzeit"])
    return total, longest


def order_problems(task, cart, content=None):
    """Alle Probleme eines Warenkorbs (Aufgabentyp "bestellung")."""
    content = content or GAME
    cart = {key: int(value) for key, value in (cart or {}).items() if int(value or 0) > 0}
    if not cart:
        return ["Der Warenkorb ist leer."]
    problems = []
    covered = [0] * len(task["bedarf"])
    for offer in task["angebote"]:
        count = cart.get(offer["id"], 0)
        if not count:
            continue
        index = offer_need(offer, task, content)
        if index is None:
            item = part(offer["teil"], content)
            reasons = [_need_mismatch(item, need, content) for need in task["bedarf"]
                       if need["typ"] == item["typ"]]
            problems.append("%s passt nicht: %s" % (
                item["name"], (reasons[0] if reasons else "wird nicht gebraucht")))
        else:
            covered[index] += count
    for need, count in zip(task["bedarf"], covered):
        if count < need["menge"]:
            problems.append("Bedarf nicht gedeckt: %s (%d von %d)."
                            % (need["text"], count, need["menge"]))
        elif count > need["menge"]:
            problems.append("Zu viel bestellt: %s (%d statt %d)."
                            % (need["text"], count, need["menge"]))
    total, longest = cart_total(task, cart)
    if total > task["budget"]:
        problems.append("Budget überschritten: %d € bei %d € Budget." % (total, task["budget"]))
    if longest > task["frist"]:
        problems.append("Zu spät: Die Ware braucht %d Arbeitstage, die Frist ist %d."
                        % (longest, task["frist"]))
    return problems


# ============================================================================
#  RACK (SERVERSCHRANK BESTUECKEN)
# ============================================================================
#
# Die Geraete stehen in hardware.json unter "rack_geraete", die Grenzwerte
# unter "rack_regeln". Ein Rack-Auftrag nennt den Schrank (Hoeheneinheiten,
# Traglast, Kuehlleistung), die bereitliegenden Geraete (Liste von IDs, ein
# Geraet darf mehrfach vorkommen) und seine Vorgaben.
#
# Antwort: {platz: unterste_HE} - platz ist die Nummer des Geraets in der
# Liste "geraete" des Auftrags (als Text oder Zahl), die HE zaehlt von unten
# ab 1. Nicht eingebaute Geraete bleiben einfach liegen.

RACK_FIELDS = ("typ", "name", "he", "gewicht", "watt")
# Farbe der Geraete im Schrank (PC und Handy gleich, aus der Palette)
RACK_COLORS = {"usv": C["yellow"], "server": C["cyan"], "storage": C["purple"],
               "switch": C["green"], "patchpanel": C["pink"]}
# Vorgaben eines Rack-Auftrags
RACK_RULES = ("mindestens", "ports_min", "frei_min")


def rack_source_text(task, index):
    """Woher ein Geraet fuer den Rack-Auftrag kommt (noch nicht eingebaut)."""
    return "aus dem Lager" if index >= task.get("lager_ab", len(task["geraete"])) \
        else "liegt bereit"


def rack_device(device_id, content=None):
    for item in (content or GAME)["hardware"].get("rack_geraete", []):
        if item["id"] == device_id:
            return item
    return None


def rack_type_name(kind, content=None):
    return (content or GAME)["hardware"].get("rack_typen", {}).get(kind, kind)


def _by_rack_type(counts, content=None):
    """(typ, anzahl) in der Reihenfolge von rack_typen (USV zuerst ...)."""
    order = list((content or GAME)["hardware"].get("rack_typen", {}))
    return sorted((counts or {}).items(),
                  key=lambda row: order.index(row[0]) if row[0] in order else len(order))


def _he_text(bottom, height):
    top = bottom + height - 1
    return "HE %d" % bottom if top == bottom else "HE %d–%d" % (bottom, top)


def rack_placed(task, answer, content=None):
    """Eingebaute Geraete als Liste von (platz, geraet, unterste_HE), von
    unten nach oben sortiert. Unbekannte Plaetze werden ignoriert."""
    devices = task.get("geraete") or []
    placed = []
    for key, bottom in (answer or {}).items():
        try:
            index, bottom = int(key), int(bottom)
        except (TypeError, ValueError):
            continue
        if 0 <= index < len(devices) and bottom >= 1:
            item = rack_device(devices[index], content)
            if item:
                placed.append((index, item, bottom))
    placed.sort(key=lambda row: (row[2], row[0]))
    return placed


def rack_place(task, answer, index, bottom, content=None):
    """Baut Geraet Nr. index ab HE bottom ein und liefert die neue Belegung.
    Ragt es oben heraus, rutscht es nach unten, bis es passt. Geraete, die
    im Weg sind, kommen zurueck auf den Stapel (wie beim echten Einbau: zwei
    Geraete koennen nicht in derselben HE stecken). PC und Handy bedienen
    den Schrank ueber diese Funktion."""
    content = content or GAME
    item = rack_device(task["geraete"][index], content)
    size = task["schrank"]["he"]
    bottom = max(1, min(int(bottom), size - item["he"] + 1))
    top = bottom + item["he"] - 1
    result = {}
    for key, other_bottom in (answer or {}).items():
        if int(key) == int(index):
            continue
        other = rack_device(task["geraete"][int(key)], content)
        other_top = int(other_bottom) + other["he"] - 1
        if other_top < bottom or int(other_bottom) > top:
            result[str(key)] = int(other_bottom)
    result[str(index)] = bottom
    return result


def rack_occupant(task, answer, unit, content=None):
    """Nummer des Geraets, das in HE unit steckt, oder None."""
    for key, bottom in (answer or {}).items():
        item = rack_device(task["geraete"][int(key)], content)
        if int(bottom) <= unit < int(bottom) + item["he"]:
            return int(key)
    return None


def rack_power(placed):
    """Leistungsaufnahme aller eingebauten Geraete ohne die USV selbst."""
    return sum(item["watt"] for _index, item, _bottom in placed if item["typ"] != "usv")


def ups_capacity(task, placed, content=None):
    """Nutzbare USV-Leistung mit Reserve (W) oder None, wenn keine USV da ist.
    Eine USV kann eingebaut sein oder schon im Raum stehen (schrank.usv_watt)."""
    rules = (content or GAME)["hardware"]["rack_regeln"]
    total = sum(item.get("leistung", 0) for _i, item, _b in placed if item["typ"] == "usv")
    total += task["schrank"].get("usv_watt", 0)
    if not total:
        return None
    return int(total * (1 - rules["strom_reserve"]))


def lower_third(task):
    """Hoechste HE, in der ein schweres Geraet noch beginnen darf."""
    return max(1, task["schrank"]["he"] // 3)


def _position_problems(task, placed, content):
    """Alles, was von der Anordnung abhaengt (Platz, Gewicht, Verkabelung)."""
    rules = (content or GAME)["hardware"]["rack_regeln"]
    size = task["schrank"]["he"]
    problems = []
    used = {}
    for index, item, bottom in placed:
        top = bottom + item["he"] - 1
        if top > size:
            problems.append("%s (%d HE) passt ab HE %d nicht mehr in den Schrank, er hat "
                            "nur %d HE." % (item["name"], item["he"], bottom, size))
            continue
        for unit in range(bottom, top + 1):
            if unit in used:
                problems.append("%s und %s überlappen in HE %d."
                                % (used[unit]["name"], item["name"], unit))
                break
        for unit in range(bottom, top + 1):
            used.setdefault(unit, item)
    limit = lower_third(task)
    for index, item, bottom in placed:
        if item["gewicht"] >= rules["schwer_ab_kg"] and bottom > limit:
            problems.append("%s wiegt %d kg und gehört ins untere Drittel "
                            "(Beginn bis HE %d), steckt aber in %s."
                            % (item["name"], item["gewicht"], limit,
                               _he_text(bottom, item["he"])))
    ups = [row for row in placed if row[1]["typ"] == "usv"]
    others = [row for row in placed if row[1]["typ"] != "usv"]
    if ups and others and max(b for _i, _it, b in ups) > min(b for _i, _it, b in others):
        problems.append("Die USV gehört ganz nach unten, unter alle anderen Geräte.")

    def neighbours(row, kind):
        _index, item, bottom = row
        top = bottom + item["he"] - 1
        return [other for other in placed if other[1]["typ"] == kind and (
            other[2] == top + 1 or other[2] + other[1]["he"] - 1 == bottom - 1)]

    for row in placed:
        if row[1]["typ"] == "patchpanel" and not neighbours(row, "switch"):
            problems.append("%s in %s hat keinen Switch direkt darüber oder darunter "
                            "(kurze Patchkabel)." % (row[1]["name"],
                                                     _he_text(row[2], row[1]["he"])))
        elif row[1]["typ"] == "switch" and not neighbours(row, "patchpanel"):
            problems.append("%s in %s hat kein Patchpanel direkt darüber oder darunter."
                            % (row[1]["name"], _he_text(row[2], row[1]["he"])))
    return problems


def _load_problems(task, placed, content):
    """Alles, was nur davon abhaengt, WELCHE Geraete eingebaut sind."""
    cabinet = task["schrank"]
    problems = []
    weight = sum(item["gewicht"] for _i, item, _b in placed)
    if weight > cabinet["traglast"]:
        problems.append("Zu schwer: %d kg bei %d kg Traglast des Schranks."
                        % (weight, cabinet["traglast"]))
    power = rack_power(placed)
    capacity = ups_capacity(task, placed, content)
    reserve = int(round(content["hardware"]["rack_regeln"]["strom_reserve"] * 100))
    if capacity is not None and power > capacity:
        problems.append("Die USV schafft mit %d %% Reserve nur %d W, die Geräte brauchen "
                        "%d W." % (reserve, capacity, power))
    if cabinet.get("kuehlung") and power > cabinet["kuehlung"]:
        problems.append("Die Kühlung führt höchstens %d W Abwärme ab, die Geräte erzeugen "
                        "%d W." % (cabinet["kuehlung"], power))
    rules = task.get("vorgaben") or {}
    for kind, count in _by_rack_type(rules.get("mindestens"), content):
        have = sum(1 for _i, item, _b in placed if item["typ"] == kind)
        if have < count:
            problems.append("Der Auftrag verlangt %d × %s, eingebaut %s %d."
                            % (count, rack_type_name(kind, content),
                               "ist" if have == 1 else "sind", have))
    if rules.get("ports_min"):
        for kind in ("switch", "patchpanel"):
            ports = sum(item.get("ports", 0) for _i, item, _b in placed if item["typ"] == kind)
            if ports < rules["ports_min"]:
                problems.append("Zu wenige Ports (%s): %d, gebraucht werden %d."
                                % (rack_type_name(kind, content), ports, rules["ports_min"]))
    if rules.get("frei_min"):
        free = cabinet["he"] - sum(item["he"] for _i, item, _b in placed)
        if free < rules["frei_min"]:
            problems.append("Es sollen mindestens %d HE für später frei bleiben, frei "
                            "sind %d." % (rules["frei_min"], max(0, free)))
    return problems


def rack_problems(task, answer, content=None):
    """Alle Probleme einer Schrankbelegung (Aufgabentyp "rack")."""
    content = content or GAME
    placed = rack_placed(task, answer, content)
    if not placed:
        return ["Der Schrank ist noch leer."]
    return _position_problems(task, placed, content) + _load_problems(task, placed, content)


def rack_summary(task, answer, content=None):
    """Live-Anzeige unter dem Schrank: (Text, ueberlastet)."""
    content = content or GAME
    placed = rack_placed(task, answer, content)
    cabinet = task["schrank"]
    used = sum(item["he"] for _i, item, _b in placed)
    weight = sum(item["gewicht"] for _i, item, _b in placed)
    power = rack_power(placed)
    capacity = ups_capacity(task, placed, content)
    parts = ["%d von %d HE" % (used, cabinet["he"]),
             "%d von %d kg" % (weight, cabinet["traglast"])]
    parts.append("%d W%s" % (power, " von %d W (USV)" % capacity if capacity else ""))
    over = weight > cabinet["traglast"] or (capacity is not None and power > capacity) or \
        bool(cabinet.get("kuehlung") and power > cabinet["kuehlung"])
    return " · ".join(parts), over


def rack_header(task, content=None):
    """Schrank und Vorgaben eines Rack-Auftrags als Zeilen."""
    content = content or GAME
    cabinet = task["schrank"]
    first = "Schrank: %d HE · Traglast %d kg" % (cabinet["he"], cabinet["traglast"])
    if cabinet.get("kuehlung"):
        first += " · Kühlung %d W" % cabinet["kuehlung"]
    if cabinet.get("usv_watt"):
        first += " · USV im Raum %d W" % cabinet["usv_watt"]
    lines = [first]
    rules = task.get("vorgaben") or {}
    wanted = ["%d × %s" % (count, rack_type_name(kind, content))
              for kind, count in _by_rack_type(rules.get("mindestens"), content)]
    if rules.get("ports_min"):
        wanted.append("mind. %d Ports" % rules["ports_min"])
    if rules.get("frei_min"):
        wanted.append("%d HE frei lassen" % rules["frei_min"])
    if wanted:
        lines.append("Verlangt: " + ", ".join(wanted))
    return lines


def rack_specs(item, content=None):
    """Kurze Beschreibung eines Rack-Geraets fuer die Anzeige."""
    parts = ["%d HE" % item["he"], "%d kg" % item["gewicht"]]
    if item["typ"] == "usv":
        parts.append("liefert %d W" % item["leistung"])
    elif item["watt"]:
        parts.append("%d W" % item["watt"])
    else:
        parts.append("passiv, kein Strom")
    if item.get("ports"):
        parts.append("%d Ports" % item["ports"])
    return " · ".join(parts)


def rack_solution(task, content=None):
    """Eine gueltige Belegung oder None. Zuerst wird ausgewaehlt, WELCHE
    Geraete hinein sollen (Gewicht, Strom, Vorgaben), dann werden sie in allen
    Reihenfolgen luekenlos von unten gestapelt. Die Auftraege sind klein."""
    content = content or GAME
    devices = task.get("geraete") or []
    for size in range(1, len(devices) + 1):
        for chosen in itertools.combinations(range(len(devices)), size):
            rows = [(index, rack_device(devices[index], content), 1) for index in chosen]
            if _load_problems(task, rows, content):
                continue
            seen = set()
            for order in itertools.permutations(chosen):
                signature = tuple(devices[index] for index in order)
                if signature in seen:
                    continue
                seen.add(signature)
                answer, bottom = {}, 1
                for index in order:
                    answer[str(index)] = bottom
                    bottom += rack_device(devices[index], content)["he"]
                if not rack_problems(task, answer, content):
                    return answer
    return None


def rack_lines(task, answer, content=None):
    """Belegung als lesbare Zeilen von unten nach oben."""
    return ["%s: %s" % (_he_text(bottom, item["he"]), item["name"])
            for _index, item, bottom in rack_placed(task, answer, content)]


def _validate_rack_task(task, content):
    problems = []
    cabinet = task.get("schrank") or {}
    if not cabinet.get("he", 0) >= 3 or not cabinet.get("traglast", 0) > 0:
        problems.append("Schrank braucht HE (mind. 3) und Traglast")
    devices = task.get("geraete") or []
    if not devices:
        problems.append("keine Geraete")
    for device_id in devices:
        if not rack_device(device_id, content):
            problems.append("unbekanntes Rack-Geraet '%s'" % device_id)
    for key in task.get("vorgaben") or {}:
        if key not in RACK_RULES:
            problems.append("unbekannte Vorgabe '%s'" % key)
    for kind in (task.get("vorgaben") or {}).get("mindestens") or {}:
        if kind not in content["hardware"].get("rack_typen", {}):
            problems.append("unbekannter Geraetetyp '%s'" % kind)
    if problems:
        return problems
    if task.get("aus_lager"):
        # Mit jeder richtigen Bestellung muss sich der Schrank bestuecken lassen
        first = task_by_id(task.get("nach"), content)
        if not first or first["typ"] != "bestellung":
            return ["Geraete aus dem Lager brauchen eine Bestellung als Voraussetzung"]
        carts = valid_carts(first, content)
        if not carts:
            return ["die Bestellung '%s' hat keine richtige Loesung" % first["id"]]
        for cart in carts:
            devices = list(task["geraete"])
            for offer in first["angebote"]:
                item = rack_device(offer["teil"], content)
                if item and item["typ"] in task["aus_lager"]:
                    devices += [offer["teil"]] * int(cart.get(offer["id"], 0) or 0)
            trial = dict(task, geraete=devices, lager_ab=len(task["geraete"]))
            if rack_solution(trial, content) is None:
                problems.append("Schrank laesst sich mit der Lieferung %s nicht richtig "
                                "bestuecken" % ", ".join(sorted(devices)))
                break
        return problems
    if rack_solution(task, content) is None:
        problems.append("Schrank laesst sich mit den bereitliegenden Geraeten nicht "
                        "richtig bestuecken")
    return problems


def _validate_rack_hardware(content):
    problems, seen = [], set()
    hardware = content["hardware"]
    kinds = hardware.get("rack_typen", {})
    for item in hardware.get("rack_geraete", []):
        where = "Spiel-Rack-Geraet %s" % item.get("id")
        if item.get("id") in seen:
            problems.append("%s: Kennung doppelt vorhanden" % where)
        seen.add(item.get("id"))
        for field in RACK_FIELDS:
            if field not in item:
                problems.append("%s: Feld '%s' fehlt" % (where, field))
        if item.get("typ") not in kinds:
            problems.append("%s: unbekannter Typ '%s'" % (where, item.get("typ")))
        if item.get("typ") == "usv" and not item.get("leistung", 0) > 0:
            problems.append("%s: USV ohne Leistung" % where)
        if item.get("typ") in ("switch", "patchpanel") and not item.get("ports", 0) > 0:
            problems.append("%s: Ports fehlen" % where)
    if hardware.get("rack_geraete") and not hardware.get("rack_regeln"):
        problems.append("Spiel-Hardware: 'rack_regeln' fehlen")
    return problems


# ============================================================================
#  FORMULAR (EINGABEFELDER MIT RECHENWEG)
# ============================================================================
#
# Ein Formular-Auftrag nennt nur die Ausgangsdaten ("daten") und welche
# Felder gefragt sind. Die richtigen Werte rechnet das Spiel selbst aus -
# fuer IP-Plaene und RAID mit denselben Funktionen wie die Praxis-Rechner
# (fisi_core.ipv4_values, fisi_core.raid_values). So koennen Aufgabe und
# Rechner nie auseinanderlaufen.
#
# Arten ("art"):
#   ip_plan     daten: netz, teilnetze [{name, hosts}], vlsm (true/false)
#               felder_global: z.B. ["praefix", "hosts"] (nur ohne VLSM)
#               felder: je Teilnetz, z.B. ["netz", "praefix", "broadcast"]
#   raid        daten: level, platten, groesse, einheit (TB/GB)
#   angebot     daten: menge, einkaufspreis, handlungskosten, gewinn, ust
#               (Prozentwerte) - Zuschlagskalkulation bis zum Bruttopreis
#   leasing     daten: kaufpreis, rate, laufzeit, sonderzahlung, restwert
#
# Antwort: {feld_id: eingegebener_text}

FORM_KINDS = ("ip_plan", "raid", "angebot", "leasing", "drucker")

IP_FIELDS = {
    "netz": "Netzadresse", "praefix": "Präfix", "maske": "Subnetzmaske",
    "erste": "Erste Host-Adresse", "letzte": "Letzte Host-Adresse",
    "broadcast": "Broadcast", "hosts": "Nutzbare Hosts",
}
# Art eines IP-Feldes fuer die Eingabepruefung
IP_KIND = {"netz": "ip", "erste": "ip", "letzte": "ip", "broadcast": "ip",
           "praefix": "praefix", "maske": "praefix", "hosts": "zahl"}


class FormError(ValueError):
    """Ungueltige Formular-Aufgabe (nur fuer die Inhaltspruefung)."""


def _prefix_for_hosts(hosts):
    prefix = 32
    while (2 ** (32 - prefix)) - 2 < hosts:
        prefix -= 1
    return prefix


def ip_plan(task):
    """Teilnetze eines IP-Plans in der Reihenfolge der Aufgabe:
    [(name, ipaddress.IPv4Network)]. Ohne VLSM wird das Netz in gleich
    grosse Teile zerlegt (Anzahl auf die naechste Zweierpotenz aufgerundet,
    Vergabe in der genannten Reihenfolge); mit VLSM bekommt jedes Teilnetz
    das kleinste passende Netz, das groesste zuerst, lueckenlos."""
    import ipaddress
    data = task["daten"]
    try:
        base = ipaddress.ip_network(data["netz"], strict=True)
    except ValueError as error:
        raise FormError("ungueltiges Netz: %s" % error)
    if base.version != 4:
        raise FormError("nur IPv4")
    nets = data["teilnetze"]
    if data.get("vlsm"):
        order = sorted(range(len(nets)), key=lambda i: (-nets[i]["hosts"], i))
        result = [None] * len(nets)
        start = int(base.network_address)
        for index in order:
            prefix = _prefix_for_hosts(nets[index]["hosts"])
            if prefix < base.prefixlen:
                raise FormError("Teilnetz %s passt nicht ins Netz" % nets[index]["name"])
            net = ipaddress.ip_network("%s/%d" % (ipaddress.ip_address(start), prefix))
            if not net.subnet_of(base):
                raise FormError("Netz reicht nicht fuer alle Teilnetze")
            result[index] = (nets[index]["name"], net)
            start += net.num_addresses
        return result
    bits = max(0, int(math.ceil(math.log(len(nets), 2) - 1e-9)))
    parts = list(base.subnets(prefixlen_diff=bits))
    result = [(item["name"], net) for item, net in zip(nets, parts)]
    for item, (_name, net) in zip(nets, result):
        if ipv4_values(net)["hosts"] < item.get("hosts", 0):
            raise FormError("Teilnetz %s hat zu wenige Hosts" % item["name"])
    return result


def _money(value):
    return round(value + 1e-9, 2)


def offer_values(data):
    """Zuschlagskalkulation (Angebot) als Liste (schluessel, name, wert)."""
    if data.get("positionen"):
        purchase = _money(sum(item["menge"] * item["preis"] for item in data["positionen"]))
    else:
        purchase = _money(data["menge"] * data["einkaufspreis"])
    overhead = _money(purchase * data["handlungskosten"] / 100.0)
    cost = _money(purchase + overhead)
    profit = _money(cost * data["gewinn"] / 100.0)
    net = _money(cost + profit)
    tax = _money(net * data["ust"] / 100.0)
    return [("einkauf", data.get("einkauf_name") or "Einkaufspreis gesamt", purchase),
            ("handlungskosten", "Handlungskosten (%s %%)" % _num(data["handlungskosten"]),
             overhead),
            ("selbstkosten", "Selbstkosten", cost),
            ("gewinn", "Gewinn (%s %%)" % _num(data["gewinn"]), profit),
            ("netto", "Nettoverkaufspreis", net),
            ("ust", "Umsatzsteuer (%s %%)" % _num(data["ust"]), tax),
            ("brutto", "Bruttoverkaufspreis", _money(net + tax))]


def leasing_values(data):
    """Kauf gegen Leasing als Liste (schluessel, name, wert)."""
    lease = _money(data.get("sonderzahlung", 0) + data["rate"] * data["laufzeit"]
                   + data.get("restwert", 0))
    buy = _money(data["kaufpreis"])
    return [("leasing", "Gesamtkosten Leasing", lease),
            ("kauf", "Gesamtkosten Kauf", buy),
            ("differenz", "Unterschied", _money(abs(lease - buy))),
            ("guenstiger", "Günstiger ist", "Kauf" if buy <= lease else "Leasing")]


def _num(value):
    """Zahl deutsch formatiert: 1.234,5 - ohne ueberfluessige Nachkommastellen."""
    if isinstance(value, float) and not value.is_integer():
        text = ("%.2f" % value).rstrip("0").rstrip(".")
    else:
        text = "%d" % int(round(value))
    whole, _sep, frac = text.partition(".")
    sign = "-" if whole.startswith("-") else ""
    whole = whole.lstrip("-")
    groups = []
    while len(whole) > 3:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    groups.insert(0, whole)
    return sign + ".".join(groups) + ("," + frac if frac else "")


def _euro(value):
    return "%s €" % ("{:,.2f}".format(value).replace(",", "X").replace(".", ",")
                     .replace("X", "."))


def form_fields(task, content=None):
    """Die Felder eines Formulars mit Sollwert:
    [{"id", "gruppe", "label", "einheit", "art", "soll", "anzeige", "optionen"}]
    art: ip, praefix, zahl, geld, prozent, wahl."""
    kind = task.get("art")
    data = task.get("daten") or {}
    fields = []

    def add(key, label, art, soll, group=None, unit="", shown=None, options=None):
        fields.append({"id": key, "gruppe": group, "label": label, "einheit": unit,
                       "art": art, "soll": soll, "anzeige": shown or str(soll),
                       "optionen": options})

    if kind == "ip_plan":
        plan = ip_plan(task)
        first = ipv4_values(plan[0][1])
        for key in task.get("felder_global") or []:
            if key not in IP_FIELDS:
                raise FormError("unbekanntes Feld '%s'" % key)
            soll = first[key]
            shown = "/%d" % soll if key == "praefix" else str(soll)
            add(key, IP_FIELDS[key] + " je Teilnetz", IP_KIND[key],
                first["praefix"] if IP_KIND[key] == "praefix" else soll, shown=shown)
        for number, (name, net) in enumerate(plan):
            values = ipv4_values(net)
            for key in task.get("felder") or []:
                if key not in IP_FIELDS:
                    raise FormError("unbekanntes Feld '%s'" % key)
                soll = values[key]
                shown = "/%d" % soll if key == "praefix" else str(soll)
                if key == "maske":
                    soll, shown = values["praefix"], str(values["maske"])
                add("%d.%s" % (number, key), IP_FIELDS[key], IP_KIND[key],
                    soll if IP_KIND[key] != "ip" else str(soll), group=name, shown=shown)
    elif kind == "raid":
        values = raid_values(data["level"], data["platten"], data["groesse"])
        if values is None:
            raise FormError("RAID-Level passt nicht zur Plattenzahl")
        unit = data.get("einheit", "TB")
        add("brutto", "Bruttokapazität", "zahl", values["brutto"], unit=unit,
            shown="%s %s" % (_num(values["brutto"]), unit))
        add("netto", "Nutzkapazität", "zahl", values["netto"], unit=unit,
            shown="%s %s" % (_num(values["netto"]), unit))
        add("verlust", "Verlust durch Redundanz", "zahl", values["verlust"], unit=unit,
            shown="%s %s" % (_num(values["verlust"]), unit))
        add("toleranz", "Ausfalltoleranz", "zahl", values["toleranz"], unit="Platten",
            shown="%d Platte%s" % (values["toleranz"], "" if values["toleranz"] == 1 else "n"))
        if "effizienz" in (task.get("felder") or []):
            add("effizienz", "Speichereffizienz", "prozent", round(values["effizienz"], 1),
                unit="%", shown="%s %%" % _num(round(values["effizienz"], 1)))
    elif kind in ("angebot", "leasing"):
        rows = offer_values(data) if kind == "angebot" else leasing_values(data)
        wanted = task.get("felder") or [row[0] for row in rows]
        for key, label, value in rows:
            if key not in wanted:
                continue
            if isinstance(value, str):
                add(key, label, "wahl", value, options=["Kauf", "Leasing"])
            else:
                add(key, label, "geld", value, unit="€", shown=_euro(value))
    elif kind == "drucker":
        values = printer_values(data)
        add("ip", "IP-Adresse des Druckers", "ip", values["ip"])
        add("maske", "Subnetzmaske", "praefix", values["praefix"], shown=values["maske"])
        add("gateway", "Standardgateway", "ip", values["gateway"])
        if data.get("dns") == "gateway":
            add("dns", "DNS-Server", "ip", values["gateway"])
        add("treiber", "Treiber", "wahl", data["treiber_richtig"],
            options=list(data["treiber"]))
        if data.get("freigaben"):
            add("freigabe", "Freigabename", "wahl", data["freigabe_richtig"],
                options=list(data["freigaben"]))
    else:
        raise FormError("unbekannte Formular-Art '%s'" % kind)
    return fields


def printer_values(data):
    """Drucker einrichten: erste freie Adresse im Druckerbereich (Hostteil
    von-bis, belegte Hostnummern ausgenommen), Maske und Gateway (erste
    Host-Adresse des Netzes)."""
    import ipaddress
    net = ipaddress.IPv4Network(data["netz"], strict=True)
    low, high = data["bereich"]
    taken = set(data.get("belegt") or [])
    hosts = list(net.hosts())
    free = [number for number in range(low, high + 1) if number not in taken]
    if not free:
        raise FormError("im Druckerbereich ist keine Adresse frei")
    address = net.network_address + free[0]
    if address not in net or address == net.broadcast_address or free[0] < 1:
        raise FormError("Druckerbereich liegt nicht im Netz")
    gateway = hosts[0]
    if address == gateway:
        raise FormError("Druckerbereich ueberschneidet das Gateway")
    for key in ("treiber_richtig",):
        if data[key] not in data["treiber"]:
            raise FormError("richtiger Treiber steht nicht in der Auswahl")
    if data.get("freigaben") and data.get("freigabe_richtig") not in data["freigaben"]:
        raise FormError("richtige Freigabe steht nicht in der Auswahl")
    return {"ip": str(address), "praefix": net.prefixlen, "maske": str(net.netmask),
            "gateway": str(gateway)}


def form_given(task, content=None):
    """Die Ausgangsdaten eines Formulars als Zeilen fuer die Anzeige."""
    kind = task.get("art")
    data = task.get("daten") or {}
    if kind == "ip_plan":
        lines = ["Netz: %s" % data["netz"]]
        lines += ["%s: %d Geräte" % (item["name"], item["hosts"]) for item in data["teilnetze"]]
        lines.append("Vergabe nach Größe, größtes Netz zuerst, lückenlos" if data.get("vlsm")
                     else "Gleich große Teilnetze in der genannten Reihenfolge")
        return lines
    if kind == "raid":
        return ["%s mit %d Festplatten zu je %s %s" % (
            data["level"], data["platten"], _num(data["groesse"]), data.get("einheit", "TB"))]
    if kind == "angebot" and data.get("positionen"):
        lines = []
        for item in data["positionen"]:
            if item["menge"] == 1 and not item.get("einheit"):
                lines.append("%s: %s" % (item["text"], _euro(item["preis"])))
            else:
                lines.append("%s: %d %s × %s" % (item["text"], item["menge"],
                                                  item.get("einheit", "Stück"),
                                                  _euro(item["preis"])))
        lines.append("Handlungskosten %s %% · Gewinn %s %% · Umsatzsteuer %s %%" % (
            _num(data["handlungskosten"]), _num(data["gewinn"]), _num(data["ust"])))
        return lines
    if kind == "angebot":
        return ["%d × %s zu je %s (Einkauf)" % (data["menge"], data.get("artikel", "Artikel"),
                                                _euro(data["einkaufspreis"])),
                "Handlungskosten %s %% · Gewinn %s %% · Umsatzsteuer %s %%" % (
                    _num(data["handlungskosten"]), _num(data["gewinn"]), _num(data["ust"]))]
    if kind == "drucker":
        import ipaddress
        net = ipaddress.IPv4Network(data["netz"], strict=True)
        low, high = data["bereich"]

        def host(number):
            return str(net.network_address + number)
        lines = ["Netz: %s · Gateway ist die erste Host-Adresse" % data["netz"],
                 "Druckerbereich: %s bis %s, die erste freie Adresse nehmen"
                 % (host(low), host(high))]
        taken = sorted(data.get("belegt") or [])
        if taken:
            lines.append("Schon belegt: %s" % ", ".join(host(number) for number in taken))
        if data.get("dns") == "gateway":
            lines.append("DNS übernimmt ebenfalls der Router (Gateway)")
        lines += list(data.get("hinweise") or [])
        return lines
    if kind == "leasing":
        lines = ["Kaufpreis: %s" % _euro(data["kaufpreis"]),
                 "Leasing: %d Monate zu je %s" % (data["laufzeit"], _euro(data["rate"]))]
        if data.get("sonderzahlung"):
            lines.append("Sonderzahlung zu Beginn: %s" % _euro(data["sonderzahlung"]))
        if data.get("restwert"):
            lines.append("Übernahme am Ende (Restwert): %s" % _euro(data["restwert"]))
        return lines
    return []


def parse_number(text):
    """Zahl aus einer Eingabe: "1.234,50 €", "16 TB", "66,7 %", "12000".
    None, wenn es keine Zahl ist."""
    import re
    text = (text or "").strip().replace(" ", "").replace(" ", "")
    text = re.sub(r"(€|EUR|TB|GB|Platten?|%|Hosts?)$", "", text, flags=re.I).strip()
    if not text:
        return None
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", text):
        text = text.replace(".", "")
    try:
        return float(text)
    except ValueError:
        return None


def parse_prefix(text):
    """Praefix aus "/26", "26" oder "255.255.255.192". None bei Unsinn."""
    import ipaddress
    text = (text or "").strip().replace(" ", "")
    if "." in text:
        try:
            mask = int(ipaddress.IPv4Address(text))
        except ValueError:
            return None
        bits = bin(mask)[2:].zfill(32)
        if "01" in bits:
            return None
        return bits.count("1")
    text = text.lstrip("/")
    return int(text) if text.isdigit() and int(text) <= 32 else None


def parse_ip(text):
    import ipaddress
    text = (text or "").strip().replace(" ", "").split("/")[0]
    try:
        return str(ipaddress.IPv4Address(text))
    except ValueError:
        return None


def field_ok(field, text):
    """Stimmt die Eingabe fuer ein Feld?"""
    art = field["art"]
    if art == "ip":
        return parse_ip(text) == field["soll"]
    if art == "praefix":
        return parse_prefix(text) == field["soll"]
    if art == "wahl":
        return (text or "").strip().lower() == field["soll"].lower()
    value = parse_number(text)
    if value is None:
        return False
    tolerance = {"geld": 0.011, "prozent": 0.1}.get(art, 0.01)
    return abs(value - field["soll"]) <= tolerance


def form_check(task, answer, content=None):
    """{feld_id: richtig} fuer alle Felder."""
    answer = answer or {}
    return {field["id"]: field_ok(field, answer.get(field["id"]))
            for field in form_fields(task, content)}


def form_problems(task, answer, content=None):
    """Falsche Felder als Saetze mit dem richtigen Wert."""
    answer = answer or {}
    problems = []
    for field in form_fields(task, content):
        if field_ok(field, answer.get(field["id"])):
            continue
        label = field["label"] if not field["gruppe"] else \
            "%s – %s" % (field["gruppe"], field["label"])
        given = (answer.get(field["id"]) or "").strip()
        if given:
            problems.append("%s: „%s“ stimmt nicht, richtig ist %s."
                            % (label, given, field["anzeige"]))
        else:
            problems.append("%s fehlt, richtig ist %s." % (label, field["anzeige"]))
    return problems


def _validate_form_task(task, content):
    if task.get("art") not in FORM_KINDS:
        return ["unbekannte Formular-Art '%s'" % task.get("art")]
    if not task.get("daten"):
        return ["Ausgangsdaten fehlen"]
    try:
        fields = form_fields(task, content)
        form_given(task, content)
    except (FormError, KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        return ["Formular laesst sich nicht berechnen: %s" % error]
    if not fields:
        return ["keine Eingabefelder"]
    solution = find_solution(task, content=content)
    if form_problems(task, solution, content):
        return ["die eigene Loesung wird nicht als richtig erkannt"]
    return []


# ============================================================================
#  TERMINAL (SIMULIERT) UND DIAGNOSE
# ============================================================================
#
# Terminal: Ein System wird Schritt fuer Schritt in einem nachgebauten
# Terminal eingerichtet. Zu jedem Schritt gibt es 2 bis 4 Befehle zur Wahl,
# genau einer ist richtig. Falsche Befehle liefern eine (nachgebaute)
# Fehlermeldung, dann darf man es erneut versuchen; gefaehrliche Befehle
# werden nicht "ausgefuehrt", kosten aber Sicherheitsbewusstsein.
#   system   "linux" oder "windows"
#   prompt   Eingabezeile, z.B. "root@fahrplan:~#"
#   start    optionale Zeilen, die zu Beginn im Terminal stehen
#   schritte [{"ziel": "...", "befehle": [{"befehl", "ausgabe" (Zeilen),
#            "richtig" | "gefaehrlich", "hinweis"}]}]
# Antwort: {"schritte": [[befehl_index, ...], ...]} - alle Versuche je Schritt
# in der gewaehlten Reihenfolge; der letzte ist der richtige Befehl.
#
# Diagnose: Symptom im Ticket, dazu Pruefungen mit Ergebnis. Am Ende werden
# Ursache und Massnahme gewaehlt (wie bei "auswahl" als Texte).
#   pruefungen      [{"id", "text", "ergebnis", "entscheidend"}]
#   ziel_pruefungen so viele Pruefungen reichen bei systematischem Vorgehen
#   ursachen / ursache, massnahmen / massnahme, unsicher (Liste von Massnahmen)
#   aus_lager       optional: Teiletyp, der als Ersatz aus dem Lager kommt
# Antwort: {"pruefungen": [id, ...], "ursache": text, "massnahme": text}

SYSTEMS = ("linux", "windows")
# Breite einer Ausgabezeile im Terminal (feste Schriftbreite, muss aufs Handy
# passen). Befehle selbst duerfen umbrechen.
MAX_TERMINAL_CHARS = 60
MAX_COMMAND_CHARS = 120
MAX_RESULT_CHARS = 220

TRY_RIGHT = "richtig"
TRY_WRONG = "falsch"
TRY_DANGER = "gefaehrlich"


def _allowed_mistakes(task, content=None):
    return task.get("fehlgriffe_erlaubt",
                    (content or GAME)["balancing"]["terminal_fehlgriffe_erlaubt"])


def terminal_right_index(step):
    for index, command in enumerate(step["befehle"]):
        if command.get("richtig"):
            return index
    return None


def terminal_try(task, step_index, option_index):
    """Ein Befehl im Terminal: (art, befehl, ausgabe_zeilen, hinweis).
    art ist TRY_RIGHT, TRY_WRONG oder TRY_DANGER."""
    command = task["schritte"][step_index]["befehle"][option_index]
    if command.get("richtig"):
        kind = TRY_RIGHT
    elif command.get("gefaehrlich"):
        kind = TRY_DANGER
    else:
        kind = TRY_WRONG
    return kind, command["befehl"], list(command.get("ausgabe") or []), \
        command.get("hinweis", "")


def terminal_attempts(task, answer):
    """Versuche je Schritt (Liste von Befehls-Indizes), bis zum richtigen."""
    given = (answer or {}).get("schritte") or []
    result = []
    for index, step in enumerate(task["schritte"]):
        right = terminal_right_index(step)
        tries = []
        for value in (given[index] if index < len(given) else []) or []:
            try:
                value = int(value)
            except (TypeError, ValueError):
                continue
            if 0 <= value < len(step["befehle"]):
                tries.append(value)
                if value == right:
                    break
        result.append(tries)
    return result


def terminal_review(task, answer, content=None):
    """Auswertung eines Terminal-Auftrags:
    {"richtig", "fehlgriffe", "gefahr", "offen", "probleme"}."""
    mistakes, danger, missing, problems = 0, 0, 0, []
    for number, (step, tries) in enumerate(
            zip(task["schritte"], terminal_attempts(task, answer)), start=1):
        where = "Schritt %d (%s)" % (number, step["ziel"])
        for index in tries:
            kind, command, _output, hint = terminal_try(task, number - 1, index)
            if kind == TRY_DANGER:
                danger += 1
                problems.append("%s: „%s“ ist gefährlich. %s" % (where, command, hint))
            elif kind == TRY_WRONG:
                mistakes += 1
                problems.append("%s: „%s“ war falsch. %s" % (where, command, hint))
        if terminal_right_index(step) not in tries:
            missing += 1
            problems.append("%s wurde nicht abgeschlossen." % where)
    problems = [text.strip() for text in problems]
    right = not missing and not danger and mistakes <= _allowed_mistakes(task, content)
    return {"richtig": right, "fehlgriffe": mistakes, "gefahr": danger,
            "offen": missing, "probleme": problems}


def terminal_solution(task):
    return {"schritte": [[terminal_right_index(step)] for step in task["schritte"]]}


def terminal_commands(task):
    """Die richtigen Befehle der Reihe nach."""
    return [step["befehle"][terminal_right_index(step)]["befehl"]
            for step in task["schritte"]]


def diagnosis_check(task, check_id):
    for item in task["pruefungen"]:
        if item["id"] == check_id:
            return item
    return None


def diagnosis_done(task, answer):
    """Durchgefuehrte Pruefungen (ohne doppelte, in der gewaehlten Reihenfolge)."""
    done = []
    for check_id in (answer or {}).get("pruefungen") or []:
        if diagnosis_check(task, check_id) and check_id not in done:
            done.append(check_id)
    return done


def diagnosis_key_checks(task):
    return [item["id"] for item in task["pruefungen"] if item.get("entscheidend")]


def diagnosis_review(task, answer, content=None, available=None):
    """Auswertung einer Diagnose:
    {"richtig", "pruefungen", "systematisch", "gefahr", "probleme"}.
    available: Teile im Lager (fuer den Austausch-Schritt, None = nicht pruefen)."""
    answer = answer or {}
    done = diagnosis_done(task, answer)
    cause = answer.get("ursache") or ""
    measure = answer.get("massnahme") or ""
    keys = diagnosis_key_checks(task)
    hint = "Den entscheidenden Hinweis gibt: %s." % ", ".join(
        "„%s“" % diagnosis_check(task, key)["text"] for key in keys)
    problems = []
    if not cause:
        problems.append("Es wurde keine Ursache gewählt.")
    elif cause != task["ursache"]:
        problems.append("Die Ursache „%s“ stimmt nicht. %s" % (cause, hint))
    unsafe = measure in (task.get("unsicher") or [])
    if not measure:
        problems.append("Es wurde keine Maßnahme gewählt.")
    elif unsafe:
        problems.append("Die Maßnahme „%s“ ist unsicher und kostet "
                        "Sicherheitsbewusstsein." % measure)
    elif measure != task["massnahme"]:
        problems.append("Die Maßnahme „%s“ behebt den Fehler nicht." % measure)
    problems += exchange_review(task, answer, available, content)
    right = not problems
    systematic = right and all(key in done for key in keys) and \
        len(done) <= task["ziel_pruefungen"]
    return {"richtig": right, "pruefungen": len(done), "systematisch": systematic,
            "gefahr": 1 if unsafe else 0, "probleme": problems}


def diagnosis_solution(task, content=None, available=None):
    result = {"pruefungen": diagnosis_key_checks(task), "ursache": task["ursache"],
              "massnahme": task["massnahme"]}
    result.update(exchange_solution(task, content, available))
    return result


def spare_part(task, stock, content=None):
    """Ersatzteil aus dem Lager fuer eine Diagnose (oder None)."""
    allowed = task.get("aus_lager") or []
    order = [item["id"] for item in (content or GAME)["hardware"]["teile"]]
    for part_id in sorted(stock or {}, key=lambda pid: order.index(pid)
                          if pid in order else len(order)):
        item = part(part_id, content)
        if item and item["typ"] in allowed and (stock or {}).get(part_id, 0) > 0:
            return part_id
    return None


# ============================================================================
#  AUSTAUSCH (DIAGNOSE MIT TEILETAUSCH) UND WARTUNG (ab 0.32)
# ============================================================================
#
# Austausch: Eine Diagnose kann einen Austausch-Schritt haben. Nach Ursache und
# Massnahme wird das Ersatzteil gewaehlt (aus dem Lager, sonst nachbestellen)
# und der Ablauf in die richtige Reihenfolge gebracht: ausbauen, einbauen,
# Funktionstest.
#   austausch {"typ": Ersatzteil-Typ, "passt": {merkmal: wert},
#              "schritte": [...richtige Reihenfolge...], "falsch": [...],
#              "test": "Ergebnis des Funktionstests"}
# Antwort zusaetzlich: {"teil": ersatzteil_id, "reihenfolge": [schritt, ...]}
#
# Wartung: Kein Fehler gemeldet, sondern vorbeugende Pruefung. Jeder
# Pruefpunkt wird geprueft und als "in Ordnung" oder "auffaellig" bewertet,
# danach wird der Abschluss gewaehlt (was ins Protokoll kommt).
#   pruefpunkte [{"id", "text", "ergebnis", "auffaellig": true|false}]
#   abschluss (Liste) / abschluss_antwort
# Antwort: {"bewertung": {id: "ok"|"auffaellig"}, "abschluss": text}

RATING_OK = "ok"
RATING_ISSUE = "auffaellig"
RATING_TEXT = {RATING_OK: "in Ordnung", RATING_ISSUE: "auffällig"}
SPARE_STEPS = (3, 6)        # so viele Schritte hat ein Austausch


def spare_kinds(content=None):
    """Alle Teile-Typen, die ausgetauscht werden koennen: {typ: Name}."""
    hardware = (content or GAME)["hardware"]
    kinds = dict(hardware.get("typen", {}))
    kinds.update(hardware.get("ersatz_typen", {}))
    return kinds


def spare_features(kind, content=None):
    """Merkmale eines Ersatzteil-Typs fuer die Anzeige: [(feld, Name, Einheit)]."""
    return [tuple(item) for item in
            (content or GAME)["hardware"].get("ersatz_merkmale", {}).get(kind, [])]


def spare_catalog(task, content=None):
    """Alle Teile, die fuer einen Austausch infrage kommen (gleicher Typ)."""
    exchange = task.get("austausch") or {}
    hardware = (content or GAME)["hardware"]
    return [item for item in hardware["teile"] + hardware.get("ersatzteile", [])
            if item["typ"] == exchange.get("typ")]


def spare_fits(task, part_id, content=None):
    """Passt ein Ersatzteil? Liefert die Abweichungen als Saetze ([] = passt)."""
    item = part(part_id, content)
    exchange = task.get("austausch") or {}
    if not item or item["typ"] != exchange.get("typ"):
        return ["Das ist kein %s." % spare_kinds(content).get(exchange.get("typ"),
                                                               "passendes Teil")]
    labels = {key: (name, unit) for key, name, unit in
              spare_features(exchange["typ"], content)}
    problems = []
    for key, wanted in (exchange.get("passt") or {}).items():
        if item.get(key) != wanted:
            name, unit = labels.get(key, (key, ""))
            problems.append("%s %s statt %s" % (
                name, _feature_value(item.get(key), unit), _feature_value(wanted, unit)))
    return problems


def _feature_value(value, unit):
    if isinstance(value, float):
        value = _num(value)
    return ("%s %s" % (value, unit)).strip()


def spare_specs(item, content=None):
    """Merkmale eines Ersatzteils als kurze Zeile."""
    parts = [_feature_value(item.get(key), unit)
             for key, _name, unit in spare_features(item["typ"], content)
             if item.get(key) is not None]
    return " · ".join(parts)


def exchange_steps(task):
    """Alle Schritte zur Auswahl (richtige und falsche), fest gemischt."""
    exchange = task.get("austausch") or {}
    steps = list(exchange.get("schritte") or []) + list(exchange.get("falsch") or [])
    return sorted(steps, key=lambda text: _dice(task["id"], 0, text))


def exchange_review(task, answer, available=None, content=None):
    """Probleme im Austausch-Schritt als Saetze ([] = alles richtig)."""
    exchange = task.get("austausch")
    if not exchange:
        return []
    answer = answer or {}
    problems = []
    chosen = answer.get("teil")
    if not chosen:
        problems.append("Es wurde kein Ersatzteil gewählt.")
    else:
        item = part(chosen, content)
        fits = spare_fits(task, chosen, content)
        if fits:
            problems.append("„%s“ passt nicht: %s." % (
                item["name"] if item else chosen, ", ".join(fits)))
        elif available is not None and chosen not in available:
            problems.append("„%s“ liegt nicht im Lager." % item["name"])
    order = list(answer.get("reihenfolge") or [])
    wrong = [text for text in order if text in (exchange.get("falsch") or [])]
    for text in wrong:
        problems.append("„%s“ gehört nicht zum Austausch." % text)
    right = [text for text in order if text not in wrong]
    if right != list(exchange["schritte"]):
        problems.append("Der Ablauf stimmt nicht. Richtig: %s." % " → ".join(
            "%d. %s" % (number, text.rstrip("."))
            for number, text in enumerate(exchange["schritte"], start=1)))
    return problems


def exchange_solution(task, content=None, available=None):
    """Richtige Antwort des Austausch-Schritts: ein passendes Teil (zuerst
    eines, das im Lager liegt, sonst das guenstigste)."""
    exchange = task.get("austausch")
    if not exchange:
        return {}
    fitting = [item for item in spare_catalog(task, content)
               if not spare_fits(task, item["id"], content)]
    fitting.sort(key=lambda item: (item["id"] not in (available or []), item.get("preis", 0)))
    return {"teil": fitting[0]["id"] if fitting else None,
            "reihenfolge": list(exchange["schritte"])}


def spare_delivery_days(content=None):
    return int((content or GAME)["hardware"].get("nachbestellung", {}).get("lieferzeit", 1))


def spare_dealer(content=None):
    return (content or GAME)["hardware"].get("nachbestellung", {}).get("haendler", "")


def _validate_exchange(task, content):
    exchange = task.get("austausch")
    problems = []
    if task.get("zwischenfall"):
        return ["Zwischenfaelle warten nicht - kein Austausch mit Nachbestellung"]
    if exchange.get("typ") not in spare_kinds(content):
        return ["Austausch: unbekannter Teile-Typ '%s'" % exchange.get("typ")]
    catalog = spare_catalog(task, content)
    fitting = [item for item in catalog if not spare_fits(task, item["id"], content)]
    if not fitting:
        problems.append("Austausch: kein passendes Ersatzteil im Katalog")
    if len(fitting) == len(catalog):
        problems.append("Austausch: jedes Teil passt - die Wahl waere egal")
    labels = [key for key, _name, _unit in spare_features(exchange["typ"], content)]
    for key in exchange.get("passt") or {}:
        if key not in labels:
            problems.append("Austausch: Merkmal '%s' hat keine Bezeichnung" % key)
    steps = list(exchange.get("schritte") or [])
    wrong = list(exchange.get("falsch") or [])
    if not SPARE_STEPS[0] <= len(steps) <= SPARE_STEPS[1]:
        problems.append("Austausch: braucht %d bis %d Schritte" % SPARE_STEPS)
    if len(set(steps + wrong)) != len(steps + wrong):
        problems.append("Austausch: Schritte doppelt")
    for text in steps + wrong:
        if len(text) > MAX_OPTION_CHARS:
            problems.append("Austausch: Schritt zu lang (Handy): %s" % text[:40])
    if not exchange.get("test"):
        problems.append("Austausch: Ergebnis des Funktionstests fehlt")
    elif len(exchange["test"]) > MAX_RESULT_CHARS:
        problems.append("Austausch: Funktionstest-Text zu lang (Handy)")
    return problems


def maintenance_point(task, point_id):
    for item in task.get("pruefpunkte") or []:
        if item["id"] == point_id:
            return item
    return None


def maintenance_review(task, answer, content=None):
    """Auswertung einer Wartung: {"richtig", "probleme", "uebersehen"}."""
    answer = answer or {}
    ratings = answer.get("bewertung") or {}
    problems, missed = [], 0
    for item in task["pruefpunkte"]:
        rating = ratings.get(item["id"])
        wanted = RATING_ISSUE if item.get("auffaellig") else RATING_OK
        if rating is None:
            problems.append("„%s“ wurde nicht geprüft." % item["text"].rstrip("."))
        elif rating != wanted:
            if wanted == RATING_ISSUE:
                missed += 1
                problems.append("„%s“ ist auffällig: %s" % (item["text"].rstrip("."),
                                                             item["ergebnis"]))
            else:
                problems.append("„%s“ ist in Ordnung: %s" % (item["text"].rstrip("."),
                                                              item["ergebnis"]))
    closing = answer.get("abschluss") or ""
    if not closing:
        problems.append("Es wurde kein Abschluss gewählt.")
    elif closing != task["abschluss_antwort"]:
        problems.append("Der Abschluss „%s“ passt nicht zum Ergebnis." % closing)
    return {"richtig": not problems, "probleme": problems, "uebersehen": missed}


def maintenance_solution(task):
    return {"bewertung": {item["id"]: RATING_ISSUE if item.get("auffaellig") else RATING_OK
                          for item in task["pruefpunkte"]},
            "abschluss": task["abschluss_antwort"]}


def maintenance_counter(task, ratings):
    done = len([key for key in (ratings or {}) if maintenance_point(task, key)])
    issues = len([value for value in (ratings or {}).values() if value == RATING_ISSUE])
    return "%d von %d Prüfpunkten bewertet · %d auffällig" % (
        done, len(task["pruefpunkte"]), issues)


def _validate_maintenance_task(task, content):
    problems = []
    points = task.get("pruefpunkte") or []
    ids = [item.get("id") for item in points]
    if len(points) < 3 or len(set(ids)) != len(ids) or not all(ids):
        return ["braucht mindestens 3 Pruefpunkte mit eindeutiger Kennung"]
    for item in points:
        if not item.get("text") or not item.get("ergebnis"):
            problems.append("Pruefpunkt '%s': Text oder Ergebnis fehlt" % item["id"])
        if not isinstance(item.get("auffaellig", False), bool):
            problems.append("Pruefpunkt '%s': auffaellig muss true/false sein" % item["id"])
        if len(item.get("text", "")) > MAX_OPTION_CHARS or \
                len(item.get("ergebnis", "")) > MAX_RESULT_CHARS:
            problems.append("Pruefpunkt '%s': Text zu lang (Handy)" % item["id"])
    options = task.get("abschluss") or []
    if len(options) < 3 or len(set(options)) != len(options):
        problems.append("Abschluss: braucht mindestens 3 verschiedene Moeglichkeiten")
    if task.get("abschluss_antwort") not in options:
        problems.append("Abschluss: richtige Antwort steht nicht in der Auswahl")
    for text in options:
        if len(text) > MAX_OPTION_CHARS:
            problems.append("Abschluss zu lang (Handy): %s" % text[:40])
    if not problems and not maintenance_review(task, maintenance_solution(task),
                                               content)["richtig"]:
        problems.append("die eigene Loesung wird nicht als richtig erkannt")
    return problems


def terminal_step_label(task, step_index):
    """Kopfzeile ueber dem Terminal: "Schritt 2 von 5"."""
    return "Schritt %d von %d" % (step_index + 1, len(task["schritte"]))


def terminal_log(task, attempts):
    """Alles, was im Terminal steht, als Zeilen (rolle, text) - fuer PC und
    Handy gleich. attempts wie in der Antwort: Versuche je Schritt.
    Rollen: "start", "eingabe" (Befehl nach der Eingabezeile), "ausgabe",
    "fehler" (Ausgabe eines falschen Befehls), "gefahr" (Einspruch bei einem
    gefaehrlichen Befehl), "kommentar" (Zeilen, die mit "# " beginnen)."""
    lines = [("start", line) for line in task.get("start") or []]
    for step_index, tries in enumerate(attempts):
        for index in tries:
            kind, command, output, _hint = terminal_try(task, step_index, index)
            lines.append(("eingabe", command))
            role = {TRY_RIGHT: "ausgabe", TRY_WRONG: "fehler", TRY_DANGER: "gefahr"}[kind]
            for line in output:
                lines.append(("kommentar" if line.startswith("# ") else role, line))
    return lines


def terminal_current_step(task, attempts):
    """Index des Schritts, der gerade dran ist (None, wenn alle erledigt)."""
    for index, step in enumerate(task["schritte"]):
        tries = attempts[index] if index < len(attempts) else []
        if terminal_right_index(step) not in tries:
            return index
    return None


def diagnosis_counter(task, done):
    count = len(done)
    return "%d Prüfung%s durchgeführt · sinnvoll sind etwa %d" % (
        count, "" if count == 1 else "en", task["ziel_pruefungen"])


def spare_parts_text(task, available, content=None):
    """Zeile "Im Lager bereit: ..." fuer Diagnosen mit Ersatzteil."""
    if not task.get("aus_lager"):
        return ""
    names = []
    for part_id in available or []:
        item = part(part_id, content)
        if item and item["typ"] in task["aus_lager"] and item["name"] not in names:
            names.append(item["name"])
    if not names:
        return "Im Lager liegt gerade kein passendes Ersatzteil."
    return "Im Lager bereit: " + ", ".join(names)


def _validate_terminal_task(task, content):
    problems = []
    if task.get("system") not in SYSTEMS:
        problems.append("unbekanntes System '%s'" % task.get("system"))
    if not task.get("prompt"):
        problems.append("Eingabezeile (prompt) fehlt")
    steps = task.get("schritte") or []
    if len(steps) < 2:
        return problems + ["braucht mindestens 2 Schritte"]
    lines = list(task.get("start") or [])
    for number, step in enumerate(steps, start=1):
        where = "Schritt %d" % number
        commands = step.get("befehle") or []
        if not step.get("ziel"):
            problems.append("%s: Ziel fehlt" % where)
        if not 2 <= len(commands) <= 4:
            problems.append("%s: braucht 2 bis 4 Befehle" % where)
            continue
        texts = [command.get("befehl") for command in commands]
        if not all(texts) or len(set(texts)) != len(texts):
            problems.append("%s: Befehle fehlen oder sind doppelt" % where)
        rights = [command for command in commands if command.get("richtig")]
        if len(rights) != 1:
            problems.append("%s: braucht genau einen richtigen Befehl" % where)
        for command in commands:
            if command.get("richtig") and command.get("gefaehrlich"):
                problems.append("%s: richtiger Befehl ist als gefaehrlich markiert" % where)
            if not command.get("richtig") and not (command.get("ausgabe") and
                                                   command.get("hinweis")):
                problems.append("%s: falscher Befehl '%s' braucht Ausgabe und Hinweis"
                                % (where, command.get("befehl")))
            # Befehle duerfen umbrechen (wie im echten Terminal), Ausgaben nicht
            if len(command.get("befehl") or "") > MAX_COMMAND_CHARS:
                problems.append("%s: Befehl laenger als %d Zeichen" % (where, MAX_COMMAND_CHARS))
            lines += list(command.get("ausgabe") or [])
            if len(command.get("hinweis", "")) > MAX_RESULT_CHARS:
                problems.append("%s: Hinweis zu lang (Handy)" % where)
    prompt = task.get("prompt", "")
    for line in lines:
        if len(line) > MAX_TERMINAL_CHARS:
            problems.append("Terminalzeile laenger als %d Zeichen (Handy): %s"
                            % (MAX_TERMINAL_CHARS, line[:40]))
    if len(prompt) > 24:
        problems.append("Eingabezeile zu lang")
    if not problems and not terminal_review(task, terminal_solution(task), content)["richtig"]:
        problems.append("die eigene Loesung wird nicht als richtig erkannt")
    return problems


def _validate_diagnosis_task(task, content):
    problems = []
    checks = task.get("pruefungen") or []
    ids = [item.get("id") for item in checks]
    if len(checks) < 4 or len(set(ids)) != len(ids) or not all(ids):
        return ["braucht mindestens 4 Pruefungen mit eindeutiger Kennung"]
    for item in checks:
        if not item.get("text") or not item.get("ergebnis"):
            problems.append("Pruefung '%s': Text oder Ergebnis fehlt" % item["id"])
        if len(item.get("text", "")) > MAX_OPTION_CHARS or \
                len(item.get("ergebnis", "")) > MAX_RESULT_CHARS:
            problems.append("Pruefung '%s': Text zu lang (Handy)" % item["id"])
    keys = [item["id"] for item in checks if item.get("entscheidend")]
    if not keys:
        problems.append("keine entscheidende Pruefung")
    goal = task.get("ziel_pruefungen", 0)
    if not len(keys) <= goal <= len(checks):
        problems.append("ziel_pruefungen muss zwischen %d und %d liegen"
                        % (len(keys), len(checks)))
    for options, answer, name in ((task.get("ursachen"), task.get("ursache"), "Ursache"),
                                  (task.get("massnahmen"), task.get("massnahme"),
                                   "Massnahme")):
        options = options or []
        if len(options) < 3 or len(set(options)) != len(options):
            problems.append("%s: braucht mindestens 3 verschiedene Moeglichkeiten" % name)
        if answer not in options:
            problems.append("%s: richtige Antwort steht nicht in der Auswahl" % name)
        for text in options:
            if len(text) > MAX_OPTION_CHARS:
                problems.append("%s zu lang (Handy): %s" % (name, text[:40]))
    for text in task.get("unsicher") or []:
        if text not in (task.get("massnahmen") or []) or text == task.get("massnahme"):
            problems.append("unsichere Massnahme passt nicht zur Auswahl: %s" % text[:40])
    if task.get("aus_lager"):
        first = task_by_id(task.get("nach"), content)
        if not first or first["typ"] != "bestellung":
            problems.append("Ersatzteile aus dem Lager brauchen eine Bestellung als "
                            "Voraussetzung")
        else:
            types = {need["typ"] for need in first["bedarf"]}
            for kind in task["aus_lager"]:
                if kind not in types:
                    problems.append("'%s' wird in '%s' nicht bestellt" % (kind, first["id"]))
            problems += _stock_users_problems(first, content)
    if task.get("austausch"):
        problems += _validate_exchange(task, content)
    if not problems and not diagnosis_review(task, diagnosis_solution(task, content),
                                             content)["richtig"]:
        problems.append("die eigene Loesung wird nicht als richtig erkannt")
    return problems


def _stock_users_problems(first, content):
    """Holen mehr Auftraege Ware aus einer Bestellung, als sie liefert?"""
    users = [other for other in content["aufgaben"]
             if other.get("nach") == first["id"] and other.get("aus_lager")]
    kinds = set()
    for other in users:
        kinds.update(other["aus_lager"])
    supply = sum(need["menge"] for need in first["bedarf"] if need["typ"] in kinds)
    if len(users) > supply:
        return ["mehr Auftraege holen Ware aus '%s', als bestellt wird" % first["id"]]
    return []


def answer_problems(task, answer, available=None, content=None):
    """Probleme einer Loesung als Saetze (Bauteile, Bestellung, Rack, Formular)."""
    if task["typ"] == "bauteile":
        return build_problems(task, answer, available, content)
    if task["typ"] == "bestellung":
        return order_problems(task, answer, content)
    if task["typ"] == "rack":
        return rack_problems(task, answer, content)
    if task["typ"] == "formular":
        return form_problems(task, answer, content)
    if task["typ"] == "terminal":
        return terminal_review(task, answer, content)["probleme"]
    if task["typ"] == "diagnose":
        return diagnosis_review(task, answer, content, available)["probleme"]
    if task["typ"] == "wartung":
        return maintenance_review(task, answer, content)["probleme"]
    return []


def check_answer(task, answer, available=None, content=None):
    """Prueft eine Antwort. Rueckgabe: (richtig, anzahl_fehler).

    auswahl:    answer ist der gewaehlte Antworttext
    zuordnung:  answer ist {links: rechts}
    bauteile:   answer ist {steckplatz: bauteil_id}
    bestellung: answer ist {angebot_id: menge}
    rack:       answer ist {platz: unterste_HE}
    formular:   answer ist {feld_id: eingegebener_text}
    terminal:   answer ist {"schritte": [[befehl_index, ...], ...]}
    diagnose:   answer ist {"pruefungen": [id, ...], "ursache": text,
                            "massnahme": text}
    """
    if task["typ"] == "auswahl":
        right = answer == task["antwort"]
        return right, 0 if right else 1
    if task["typ"] == "zuordnung":
        answer = answer or {}
        errors = sum(1 for left, right in task["paare"] if answer.get(left) != right)
        return errors == 0, errors
    if task["typ"] == "terminal":
        # Ein Fehlgriff ist erlaubt - richtig heisst hier nicht "ohne Probleme"
        review = terminal_review(task, answer, content)
        return review["richtig"], len(review["probleme"])
    if task["typ"] in PROBLEM_TYPES:
        problems = answer_problems(task, answer, available, content)
        return not problems, len(problems)
    raise ValueError("Unbekannter Aufgabentyp: %s" % task["typ"])


def valid_carts(task, content=None):
    """Alle gueltigen Warenkoerbe einer Bestellung, guenstigster zuerst.
    Durchprobiert - die Aufgaben sind klein (wenige Angebote und Stueckzahlen)."""
    offers = [offer["id"] for offer in task["angebote"]]
    # Ein Angebot, das keinen Bedarf deckt, ist in keinem gueltigen Korb;
    # eines, das einen Bedarf deckt, hoechstens so oft wie dessen Menge.
    ranges = []
    for offer in task["angebote"]:
        index = offer_need(offer, task, content)
        ranges.append(range(1) if index is None else
                      range(task["bedarf"][index]["menge"] + 1))
    result = []
    for counts in itertools.product(*ranges):
        cart = {offer: count for offer, count in zip(offers, counts) if count}
        if cart and not order_problems(task, cart, content):
            result.append(cart)
    result.sort(key=lambda cart: cart_total(task, cart))
    return result


def find_solution(task, available=None, content=None):
    """Eine richtige Loesung (fuer die Inhaltspruefung, die Tests und die
    Rueckmeldung "So waere es gegangen"). None, wenn es keine gibt."""
    if task["typ"] == "auswahl":
        return task["antwort"]
    if task["typ"] == "zuordnung":
        return dict(task["paare"])
    if task["typ"] == "bestellung":
        carts = valid_carts(task, content)
        return carts[0] if carts else None
    if task["typ"] == "rack":
        return rack_solution(task, content)
    if task["typ"] == "terminal":
        return terminal_solution(task)
    if task["typ"] == "diagnose":
        return diagnosis_solution(task, content, available)
    if task["typ"] == "wartung":
        return maintenance_solution(task)
    if task["typ"] == "formular":
        result = {}
        for field in form_fields(task, content):
            soll = field["soll"]
            if field["art"] == "praefix":
                result[field["id"]] = "/%d" % soll
            elif field["art"] in ("ip", "wahl"):
                result[field["id"]] = soll
            else:
                result[field["id"]] = _num(soll)
        return result
    available = task.get("teile", []) if available is None else available
    choices = []
    for slot in task["slots"]:
        options = [pid for pid in available if (part(pid, content) or {}).get("typ") == slot]
        if slot in (task.get("optional") or []):
            options = [None] + options
        choices.append(options or [None])
    best = None
    for combo in itertools.product(*choices):
        answer = {slot: pid for slot, pid in zip(task["slots"], combo) if pid}
        if not build_problems(task, answer, available, content):
            price = sum(part(pid, content)["preis"] for pid in answer.values())
            if best is None or price < best[0]:
                best = (price, answer)
    return best[1] if best else None


def cart_lines(task, cart, content=None):
    """Warenkorb als lesbare Zeilen: "2 × DDR4 16 GB (2 × 8 GB) von Bitlager24"."""
    lines = []
    for offer in task["angebote"]:
        count = int((cart or {}).get(offer["id"], 0) or 0)
        if count:
            lines.append("%d × %s von %s" % (count, part(offer["teil"], content)["name"],
                                             dealer(offer["haendler"], content)["name"]))
    return lines


def part_specs(item, content=None):
    """Kurze technische Beschreibung eines Bauteils fuer die Anzeige."""
    kind = item["typ"]
    if kind == "mainboard":
        m2 = "%d × M.2" % item["m2"] if item["m2"] else "kein M.2"
        return "Sockel %s · %s · %s · %d RAM-Plätze · %s" % (
            item["sockel"], item["ram_typ"], _form(item["formfaktor"], content),
            item["ram_slots"], m2)
    if kind == "cpu":
        return "Sockel %s · %d W · %s" % (item["sockel"], item["tdp"],
                                          "mit Grafik" if item["igpu"] else "ohne Grafik")
    if kind == "ram":
        return "%s · %d GB · %d Modul%s" % (item["ram_typ"], item["groesse"], item["module"],
                                           "" if item["module"] == 1 else "e")
    if kind == "ssd":
        size = item["groesse"]
        return "%s · %s" % ("M.2 (NVMe)" if item["anschluss"] == "m2" else "SATA",
                            "%d TB" % (size // 1000) if size % 1000 == 0 else "%d GB" % size)
    if kind == "gpu":
        return "braucht %d W" % item["watt"]
    if kind == "netzteil":
        return "liefert %d W" % item["watt"]
    if kind == "gehaeuse":
        return "für " + ", ".join(_form(f, content) for f in item["formfaktoren"])
    if kind == "notebook":
        return "%d GB RAM" % item["groesse"]
    if kind in (content or GAME)["hardware"].get("rack_typen", {}):
        return rack_specs(item, content)
    if kind in (content or GAME)["hardware"].get("ersatz_typen", {}):
        return spare_specs(item, content)
    return ""


def build_rules_text(task):
    """Vorgaben eines PC-Auftrags in einer Zeile."""
    rules = task.get("vorgaben") or {}
    parts = []
    if rules.get("ram_min"):
        parts.append("mind. %d GB RAM" % rules["ram_min"])
    if rules.get("speicher_min"):
        size = rules["speicher_min"]
        parts.append("mind. %s SSD" % ("%d TB" % (size // 1000) if size % 1000 == 0
                                       else "%d GB" % size))
    if rules.get("grafikkarte"):
        parts.append("Grafikkarte nötig")
    if rules.get("budget"):
        parts.append("höchstens %d €" % rules["budget"])
    return " · ".join(parts)


def order_header(task):
    """Bedarf, Budget und Frist einer Bestellung als Zeilen."""
    lines = ["%d × %s" % (need["menge"], need["text"]) for need in task["bedarf"]]
    days = task["frist"]
    lines.append("Budget %d € · Frist %d Arbeitstag%s" % (task["budget"], days,
                                                          "" if days == 1 else "e"))
    return lines


def cart_summary(task, cart):
    """Live-Anzeige unter dem Warenkorb: (Text, zu_teuer, zu_spaet)."""
    total, longest = cart_total(task, cart)
    count = sum(int(value or 0) for value in (cart or {}).values())
    if not count:
        return "leer", False, False
    text = "%d Artikel · %d € von %d € · Lieferung in %d Arbeitstag%s" % (
        count, total, task["budget"], longest, "" if longest == 1 else "en")
    return text, total > task["budget"], longest > task["frist"]


def solution_text(task, available=None, content=None):
    """Eine richtige Loesung als Text (fuer die Rueckmeldung nach Fehlern)."""
    solution = find_solution(task, available, content)
    if not solution:
        return ""
    if task["typ"] == "bestellung":
        return "So hätte es gepasst: " + ", ".join(cart_lines(task, solution, content)) + "."
    if task["typ"] == "bauteile":
        names = [part(solution[slot], content)["name"] for slot in task["slots"]
                 if solution.get(slot)]
        return "Eine passende Zusammenstellung: " + ", ".join(names) + "."
    if task["typ"] == "rack":
        return "Eine passende Belegung: " + ", ".join(rack_lines(task, solution, content)) + "."
    if task["typ"] == "terminal":
        return "Richtiger Ablauf: " + " → ".join(terminal_commands(task))
    if task["typ"] == "diagnose":
        text = "Richtig: Ursache – %s. Maßnahme – %s." % (
            task["ursache"].rstrip("."), task["massnahme"].rstrip("."))
        if solution.get("teil"):
            text += " Ersatzteil – %s." % part(solution["teil"], content)["name"]
        return text
    if task["typ"] == "wartung":
        issues = [item["text"].rstrip(".") for item in task["pruefpunkte"]
                  if item.get("auffaellig")]
        text = "Auffällig: %s." % ", ".join(issues) if issues else \
            "Alle Prüfpunkte sind in Ordnung."
        return "%s Abschluss – %s." % (text, task["abschluss_antwort"].rstrip("."))
    return ""


def _scaled(value, factor):
    return int(round(value * factor))


def evaluate(task, answer, used_help, levels, day, balancing=None, available=None,
             content=None, stock=None):
    """Bewertet eine bearbeitete Aufgabe und liefert die Nutzdaten fuer das
    Ereignis ticket_erledigt (Geld und Reputationsaenderung werden mit
    gespeichert, damit spaetere Balancing-Aenderungen den Stand nicht
    rueckwirkend verschieben).

    available: Bauteile, die bei einem PC-Auftrag bereitliegen
    stock:     aktueller Lagerbestand {bauteil: anzahl} - was davon verbaut
               wird, zieht der Spielstand spaeter vom Lager ab"""
    balancing = balancing or GAME["balancing"]
    problems = answer_problems(task, answer, available, content)
    right, errors = check_answer(task, answer, available, content)
    gaps = requirement_gaps(task, levels)
    below = bool(gaps)
    axes = ["fachkompetenz"] + [a for a in task.get("achsen") or [] if a != "fachkompetenz"]
    reward = task["belohnung"]
    delta = {key: 0 for key in AXIS_KEYS}
    delta["zuverlaessigkeit"] += balancing["zuverlaessigkeit_pro_ticket"]

    review = {}
    if task["typ"] == "terminal":
        review = terminal_review(task, answer, content)
    elif task["typ"] == "diagnose":
        review = diagnosis_review(task, answer, content, available)
    if review.get("gefahr"):
        # Gefaehrlicher Befehl oder unsichere Massnahme
        delta["sicherheit"] -= balancing["gefahr_verlust"]
    if review.get("systematisch"):
        delta["zuverlaessigkeit"] += balancing["systematik_bonus"]

    if right:
        factor = 1.0
        if not used_help:
            factor += balancing["bonus_ohne_hilfe"]
        if not below:
            factor += balancing["bonus_sicher_geloest"]
        money = _scaled(reward["geld"], factor)
        for axis in axes:
            delta[axis] += _scaled(reward["reputation"], factor)
    else:
        factor = balancing["faktor_unter_niveau"] if below else 1
        money = -balancing["fehlerkosten"]
        loss = task.get("verlust", balancing["reputation_verlust"])
        for axis in axes:
            delta[axis] -= _scaled(loss, factor)

    payload = {
        "aufgabe": task["id"],
        "tag": day,
        "richtig": right,
        "fehler": errors,
        "hilfe": bool(used_help),
        "unter_niveau": below,
        "geld": money,
        "reputation": {key: value for key, value in delta.items() if value},
    }
    if problems:
        payload["probleme"] = problems
    if task["typ"] == "terminal":
        payload["fehlgriffe"] = review["fehlgriffe"]
        payload["gefahr"] = review["gefahr"]
    if task["typ"] == "diagnose":
        payload["pruefungen"] = review["pruefungen"]
        payload["systematisch"] = review["systematisch"]
        payload["gefahr"] = review["gefahr"]
        spare = spare_part(task, stock, content) if right else None
        if right and task.get("austausch"):
            spare = answer.get("teil")
        if spare:
            payload["verbaut"] = [spare]
            payload["aus_lager"] = [spare]
    if right and task["typ"] == "bestellung":
        # Die Ware kommt je Angebot nach dessen Lieferzeit an
        total, _longest = cart_total(task, answer)
        payload["kosten"] = total
        payload["lieferung"] = [
            {"teil": offer["teil"], "menge": int(answer[offer["id"]]),
             "haendler": offer["haendler"], "ankunft": day + offer["lieferzeit"]}
            for offer in task["angebote"] if int(answer.get(offer["id"], 0) or 0) > 0]
        if task.get("empfaenger"):
            for item in payload["lieferung"]:
                item["empfaenger"] = task["empfaenger"]
        bonus = _scaled(max(0, task["budget"] - total), balancing["ersparnis_anteil"])
        if bonus:
            payload["ersparnis_bonus"] = bonus
            payload["geld"] += bonus
    if not right and task["typ"] == "bestellung":
        # Falsch bestellt: Die Ware kommt trotzdem (ins Lager) - ein
        # Zwischenfall "Falsche Ware" folgt, sobald sie da ist
        total, _longest = cart_total(task, answer)
        delivery = [{"teil": offer["teil"], "menge": int(answer[offer["id"]]),
                     "haendler": offer["haendler"], "ankunft": day + offer["lieferzeit"]}
                    for offer in task["angebote"]
                    if int(answer.get(offer["id"], 0) or 0) > 0]
        if delivery:
            payload["kosten"] = total
            payload["lieferung"] = delivery
            payload["fehllieferung"] = True
    if right and task["typ"] == "bestellung" and task.get("kein_sparbonus") and \
            payload.get("ersparnis_bonus"):
        # Nach einer Falschlieferung gibt es keinen Spar-Bonus mehr
        payload["geld"] -= payload.pop("ersparnis_bonus")
        payload["bonus_verloren"] = True
    if task.get("falschlieferung"):
        payload["falschlieferung"] = task["falschlieferung"]
        if right:
            # Zurueck geht, was von der falschen Ware noch im Lager liegt
            stock = dict(stock or {})
            back = {}
            for part_id, count in task.get("falsche_ware") or []:
                count = min(int(count), stock.get(part_id, 0))
                if count > 0:
                    stock[part_id] -= count
                    back[part_id] = back.get(part_id, 0) + count
            payload["ruecksendung"] = back
            payload["ruecksendekosten"] = task.get("ruecksendekosten", 0)
            payload["geld"] -= payload["ruecksendekosten"]
    if task.get("zwischenfall"):
        payload["zwischenfall"] = True
    if right and task["typ"] == "rack" and task.get("lager_ab") is not None:
        # Geraete ab Platz lager_ab kamen aus dem Lager
        used = [item["id"] for index, item, _bottom in rack_placed(task, answer, content)
                if index >= task["lager_ab"]]
        if used:
            payload["verbaut"] = used
            payload["aus_lager"] = used
    if right and task["typ"] == "bauteile":
        stock = dict(stock or {})
        used = []
        for part_id in answer.values():
            if part_id and part_id not in task.get("teile", []) and stock.get(part_id, 0) > 0:
                stock[part_id] -= 1
                used.append(part_id)
        payload["verbaut"] = [answer[slot] for slot in task["slots"] if answer.get(slot)]
        payload["aus_lager"] = used
    return payload


def defer_payload(task, day, balancing=None):
    balancing = balancing or GAME["balancing"]
    factor = balancing["prioritaet_faktor"].get(task["prioritaet"], 1)
    loss = _scaled(balancing["verschieben_verlust"], factor)
    payload = {"aufgabe": task["id"], "tag": day,
               "reputation": {"zuverlaessigkeit": -loss}}
    if task.get("zwischenfall"):
        # Zwischenfaelle warten nicht - er ist danach weg
        payload["zwischenfall"] = True
    return payload


# ============================================================================
#  SPIELSTAND AUS DEN EREIGNISSEN
# ============================================================================

def rank_for(value, balancing=None, day=None):
    """Rang zur mittleren Reputation. Ab 0.32 braucht eine Befoerderung auch
    Berufserfahrung: Mit day zaehlt ein Rang erst ab seinem Arbeitstag."""
    balancing = balancing or GAME["balancing"]
    name = balancing["raenge"][0]["name"]
    for rank in balancing["raenge"]:
        if value >= rank["ab"] and (day is None or day >= rank.get("ab_tag", 1)):
            name = rank["name"]
    return name


def tickets_per_day(rank, balancing=None):
    """Normale Tickets pro Arbeitstag fuer einen Rang (Zwischenfaelle zaehlen
    nicht mit). Aeltere Inhalte hatten eine feste Zahl."""
    value = (balancing or GAME["balancing"])["tickets_pro_tag"]
    if isinstance(value, dict):
        return int(value.get(rank, min(value.values())))
    return int(value)


def next_rank(value, day, balancing=None):
    """Der naechste Rang und was dafuer fehlt: (name, fehlende_reputation,
    fehlende_tage) oder None, wenn schon der hoechste Rang erreicht ist."""
    balancing = balancing or GAME["balancing"]
    current = rank_for(value, balancing, day)
    names = [rank["name"] for rank in balancing["raenge"]]
    index = names.index(current)
    if index + 1 >= len(names):
        return None
    rank = balancing["raenge"][index + 1]
    return (rank["name"], max(0, int(math.ceil(rank["ab"] - value))),
            max(0, rank.get("ab_tag", 1) - day))


def rank_hint(state):
    """Kurzer Satz, was bis zur naechsten Befoerderung fehlt (oder "")."""
    upcoming = state.next_rank()
    if upcoming is None:
        return ""
    name, reputation, days = upcoming
    missing = []
    if days:
        missing.append("noch %d Arbeitstag%s" % (days, "" if days == 1 else "e"))
    if reputation:
        missing.append("noch %d %% Ansehen" % reputation)
    if not missing:
        return "Nächster Rang: %s ab dem nächsten Arbeitstag" % name
    return "Nächster Rang: %s, %s" % (name, " und ".join(missing))


_MIX_CACHE = {}


def _pool_order(index, task):
    """Sortierschluessel der Tagesauswahl (siehe GameState._pool)."""
    if not task.get("vorlage"):
        return (0, task.get("ab_tag", 1), index)
    value = _MIX_CACHE.get(task["id"])
    if value is None:
        value = _MIX_CACHE[task["id"]] = _dice("mischung", 0, task["id"])
    return (1, task.get("ab_tag", 1), value)


def active_person(person_id, day, content=None):
    """Wer eine Rolle am Arbeitstag day ausfuellt: die Person selbst oder -
    nach ihrem letzten Arbeitstag (bis_tag) - ihre Nachfolge."""
    seen = set()
    while person_id not in seen:
        seen.add(person_id)
        person = colleague(person_id, content)
        if not person or person.get("bis_tag") is None or day <= person["bis_tag"] or \
                not person.get("nachfolger"):
            return person_id
        person_id = person["nachfolger"]
    return person_id


def person_present(person, day):
    """Ist die Person an diesem Arbeitstag da (eingestellt, nicht im Ruhestand)?"""
    return person.get("ab_tag", 1) <= day and \
        (person.get("bis_tag") is None or day <= person["bis_tag"])


class GameState:
    """Der aus dem Ereignisprotokoll berechnete Spielstand."""

    def __init__(self, events, content=None):
        self.content = content or GAME
        balancing = self.content["balancing"]
        start = balancing["reputation_start"]
        self.profile = None
        self.reputation = {key: start for key in AXIS_KEYS}
        self.money = 0
        self.days_done = 0
        self.solved = set()
        self.handled = {}          # aufgabe -> Status am aktuellen Tag
        self.history = []          # (timestamp, typ, daten) chronologisch
        self.tickets_done = 0
        # Lieferungen aus richtigen Bestellungen - dazu Rainers Ersatzteilregal
        # (Grundbestand, ab 0.32)
        self.deliveries = [{"teil": part_id, "menge": int(count), "ankunft": 0,
                            "aufgabe": STOCK_BASE, "haendler": ""}
                           for part_id, count in
                           self.content["hardware"].get("grundbestand", {}).items()]
        self.used = {}             # aus dem Lager verbaute Teile: id -> Anzahl
        self.wrong_orders = {}     # falsche Bestellung -> ihre (trotzdem) gelieferte Ware
        self.returned_orders = set()   # Bestellungen mit zurueckgeschickter Falschlieferung
        self.seen_incidents = set()   # schon bearbeitete oder verschobene Zwischenfaelle
        self.incident_days = {}       # Art des Zwischenfalls -> letzter Arbeitstag
        self.spare_orders = []        # nachbestellte Ersatzteile (Austausch)
        homes = self.content["wohnungen"]
        self.home_id = homes["start"]
        self.furniture = dict(homes.get("start_moebel", {}))   # stueck -> moebel
        self.layouts = {}          # wohnung -> juengste Einrichtung
        self.rent = 0              # Miete pro Arbeitstag der jetzigen Wohnung (0 = gekauft)
        self.deposit = 0           # hinterlegte Kaution (kommt beim Auszug zurueck)
        self.first_event = None
        self.start_reputation = start   # mittlere Reputation zu Beginn des Arbeitstags
        # Eigenes Unternehmen (ab 0.33)
        self.firm = None           # {"name", "tag", "stufe"} ab der Gruendung
        self.staff = {}            # mitarbeiter-id -> Daten aus der Einstellung
        self.ever_hired = set()    # auch Entlassene (bewerben sich nicht erneut)
        self.trainings = []        # alle Weiterbildungen (Ereignisdaten)
        # Kassenbuch je Arbeitstag: tag -> {"ein": {art: euro}, "aus": {art: euro}}
        self.book = {}
        self.balances = []         # (tag, kontostand) nach jedem Feierabend
        self.offers = {}           # anfrage -> Ergebnis des Angebots (ab 0.34)
        self.delegations = {}      # kundenticket -> wer es uebernimmt (ab 0.34)
        self.ticket_results = {}   # kundenticket -> Ergebnis aus dem Feierabend
        self.project_offers = {}   # projekt -> Ergebnis des Angebots (ab 0.35)
        self.projects = {}         # projekt -> gewonnenes Projekt mit Stand und Team
        self.project_days = set()  # (projekt, tag) schon verbuchter Projekttage
        self.rooms = {}            # sonderraum -> Ereignisdaten des Ausbaus (ab 0.36)

        for timestamp, kind, data in events:
            self.history.append((timestamp, kind, data))
            if self.first_event is None:
                self.first_event = str(timestamp)
            today = int(data.get("tag") or 0) if isinstance(data.get("tag"), int) else 0
            today = today or self.days_done + 1
            if kind in FIRM_EVENTS:
                self._apply_firm(kind, data, today)
            if kind in (EV_SOLVED, EV_DEFERRED) and data.get("zwischenfall"):
                self.seen_incidents.add(data.get("aufgabe"))
                incident = task_by_id(data.get("aufgabe"), self.content) or {}
                kind_id = incident.get("gruppe", data.get("aufgabe"))
                self.incident_days[kind_id] = max(self.incident_days.get(kind_id, 0),
                                                  int(data.get("tag", 0) or 0))
            if kind == EV_SPARE_ORDER:
                self.money += int(data.get("geld", 0))
                self._book(today, BOOK_GOODS, data.get("geld", 0))
                item = {"teil": data.get("teil"), "menge": 1, "ankunft": data.get("ankunft", 0),
                        "aufgabe": data.get("aufgabe"), "haendler": data.get("haendler", ""),
                        "nachbestellt": True}
                self.deliveries.append(item)
                self.spare_orders.append(dict(data))
            if kind in (EV_MOVE, EV_BUY, EV_SELL):
                self._book(today, BOOK_HOME, data.get("geld", 0))
            if kind == EV_MOVE:
                self.money += int(data.get("geld", 0))
                self.home_id = data.get("wohnung", self.home_id)
                self.rent = int(data.get("miete", 0))
                self.deposit = int(data.get("kaution", 0))
            elif kind == EV_BUY:
                self.money += int(data.get("geld", 0))
                self.furniture[data.get("stueck")] = data.get("moebel")
            elif kind == EV_SELL:
                self.money += int(data.get("geld", 0))
                self.furniture.pop(data.get("stueck"), None)
            elif kind == EV_LAYOUT:
                self.layouts[data.get("wohnung")] = data
            if kind == EV_PROFILE:
                # Der juengste Eintrag gewinnt (Ereignisse sind sortiert)
                self.profile = {"name": data.get("name", ""),
                                "aussehen": normalize_appearance(data.get("aussehen"))}
            elif kind in (EV_SOLVED, EV_DEFERRED):
                self._apply_reputation(data.get("reputation") or {})
                self.money += int(data.get("geld", 0))
                self._book(today, BOOK_TASKS, data.get("geld", 0))
                if kind == EV_SOLVED:
                    self.tickets_done += 1
                    if data.get("fehllieferung"):
                        # Falsch bestellt - die Ware kommt trotzdem ins Lager
                        items = [dict(item, aufgabe=data.get("aufgabe"), falsch=True)
                                 for item in data.get("lieferung") or []]
                        self.deliveries += items
                        self.wrong_orders[data.get("aufgabe")] = items
                    for part_id, count in (data.get("ruecksendung") or {}).items():
                        self.used[part_id] = self.used.get(part_id, 0) + int(count)
                    if data.get("richtig") and data.get("falschlieferung"):
                        self.wrong_orders.pop(data["falschlieferung"], None)
                        self.returned_orders.add(data["falschlieferung"])
                    if data.get("richtig"):
                        self.solved.add(data.get("aufgabe"))
                        for item in data.get("lieferung") or []:
                            self.deliveries.append(dict(item, aufgabe=data.get("aufgabe")))
                        for part_id in data.get("aus_lager") or []:
                            self.used[part_id] = self.used.get(part_id, 0) + 1
            elif kind == EV_DAY_END:
                self.days_done += 1
                self.money += int(data.get("gehalt", 0)) - int(data.get("miete", 0))
                self._book(today, BOOK_SALARY, data.get("gehalt", 0))
                self._book(today, BOOK_HOME, -int(data.get("miete", 0)))
                firm = data.get("firma") or {}
                self.money += int(firm.get("umsatz", 0)) - int(firm.get("gehaelter", 0)) \
                    - int(firm.get("nebenkosten", 0))
                self._book(today, BOOK_REVENUE, firm.get("umsatz", 0))
                self._book(today, BOOK_WAGES, -int(firm.get("gehaelter", 0)))
                self._book(today, BOOK_COSTS, -int(firm.get("nebenkosten", 0)))
                for item in firm.get("tickets") or []:
                    if item.get("ticket") in self.ticket_results:
                        continue
                    self.ticket_results[item.get("ticket")] = dict(item)
                    self.money += int(item.get("geld", 0))
                    self._book(today, BOOK_TICKETS, item.get("geld", 0))
                    self._apply_reputation(item.get("reputation") or {})
                for item in firm.get("projekte") or []:
                    self._apply_project_day(item, today)
                self.balances.append((today, self.money))
                self.start_reputation = self.mean_reputation

        # Tickets des laufenden Tages (Tag steht in den Nutzdaten)
        for _timestamp, kind, data in self.history:
            if kind in (EV_SOLVED, EV_DEFERRED, EV_SPARE_ORDER) and \
                    data.get("tag") == self.day:
                if kind == EV_DEFERRED:
                    status = ST_DEFERRED
                elif kind == EV_SPARE_ORDER:
                    status = ST_WAITING
                else:
                    status = ST_RIGHT if data.get("richtig") else ST_WRONG
                self.handled[data.get("aufgabe")] = status

    def _book(self, day, kind, amount):
        amount = int(amount or 0)
        if not amount:
            return
        side = self.book.setdefault(day, {"ein": {}, "aus": {}})["ein" if amount > 0 else "aus"]
        side[kind] = side.get(kind, 0) + abs(amount)

    def _apply_firm(self, kind, data, day):
        """Ereignisse der eigenen Firma. Doppelte oder ueberholte Ereignisse
        (z.B. auf zwei Geraeten gleichzeitig gegruendet) zaehlen nicht."""
        if kind == EV_FOUNDED:
            if self.firm is None:
                self.firm = {"name": data.get("name", ""), "tag": int(data.get("tag", day)),
                             "stufe": 1}
                self.money += int(data.get("geld", 0))
                self._book(day, BOOK_FOUNDING, data.get("geld", 0))
            return
        if self.firm is None:
            return
        if kind == EV_HIRED and data.get("id") and data["id"] not in self.staff:
            self.staff[data["id"]] = dict(data)
            self.ever_hired.add(data["id"])
        elif kind == EV_FIRED:
            self.staff.pop(data.get("id"), None)
        elif kind == EV_TRAINING and data.get("id") in self.staff:
            self.trainings.append(dict(data))
            self.money += int(data.get("geld", 0))
            self._book(day, BOOK_TRAINING, data.get("geld", 0))
        elif kind == EV_EXPAND and int(data.get("stufe", 0)) == self.firm["stufe"] + 1:
            self.firm["stufe"] += 1
            self.money += int(data.get("geld", 0))
            self._book(day, BOOK_BUILDING, data.get("geld", 0))
        elif kind == EV_ROOM and data.get("raum") not in self.rooms:
            # Doppelt (zwei Geraete) oder ohne die noetige Stufe: zaehlt nicht
            rule = special_room(data.get("raum"), self.content)
            if rule and self.firm["stufe"] >= int(rule["ab_stufe"]):
                self.rooms[data["raum"]] = dict(data)
                self.money += int(data.get("geld", 0))
                self._book(day, BOOK_BUILDING, data.get("geld", 0))
        elif kind in (EV_OFFER_WON, EV_OFFER_LOST) and data.get("anfrage") and \
                data["anfrage"] not in self.offers:
            self.offers[data["anfrage"]] = dict(data, gewonnen=kind == EV_OFFER_WON)
            self.money += int(data.get("geld", 0))
            self._book(day, BOOK_OFFERS, data.get("geld", 0))
            self._apply_reputation(data.get("reputation") or {})
        elif kind == EV_DELEGATED and data.get("ticket") and \
                data["ticket"] not in self.delegations:
            # Auf zwei Geraeten gleichzeitig verteilt: Wer schon voll ist,
            # bekommt nichts mehr dazu
            taken = [item for item in self.delegations.values()
                     if item.get("tag") == data.get("tag") and item.get("an") == data.get("an")]
            if len(taken) < ticket_limit(data.get("an"), self.content):
                self.delegations[data["ticket"]] = dict(data)
        elif kind in (EV_PROJECT_WON, EV_PROJECT_LOST) and data.get("projekt") and \
                data["projekt"] not in self.project_offers:
            won = kind == EV_PROJECT_WON
            self.project_offers[data["projekt"]] = dict(data, gewonnen=won)
            if won:
                self.projects[data["projekt"]] = dict(data, stand=0.0, team=[], fertig=None,
                                                      tage=[])
                self.money += int(data.get("anzahlung", 0)) - int(data.get("material", 0))
                self._book(day, BOOK_PROJECTS, data.get("anzahlung", 0))
                self._book(day, BOOK_MATERIAL, -int(data.get("material", 0)))
        elif kind == EV_PROJECT_TEAM and data.get("projekt") in self.projects:
            project = self.projects[data["projekt"]]
            if project["fertig"]:
                return
            team = [person for person in data.get("team") or [] if person]
            # Jede Person arbeitet nur in einem Projekt mit
            for other in self.projects.values():
                if other is not project:
                    other["team"] = [person for person in other["team"] if person not in team]
            project["team"] = team

    def _apply_project_day(self, item, day):
        """Ein Projekt-Arbeitstag aus dem Feierabend: Punkte dazu, bei
        Fertigstellung die Restzahlung."""
        key = (item.get("projekt"), int(item.get("tag", day) or day))
        project = self.projects.get(item.get("projekt"))
        if project is None or key in self.project_days or project["fertig"]:
            return
        self.project_days.add(key)
        project["stand"] = min(float(project["aufwand"]),
                               project["stand"] + float(item.get("punkte", 0)))
        project["tage"].append(dict(item))
        if item.get("fertig"):
            project["fertig"] = key[1]
            project["team"] = []
            self.money += int(item.get("geld", 0))
            self._book(day, BOOK_PROJECTS, item.get("geld", 0))
            self._apply_reputation(item.get("reputation") or {})

    def _apply_reputation(self, delta):
        for key, value in delta.items():
            if key in self.reputation:
                self.reputation[key] = max(0, min(100, self.reputation[key] + int(value)))

    # -- Kennzahlen ---------------------------------------------------------

    @property
    def day(self):
        return self.days_done + 1

    @property
    def mean_reputation(self):
        return sum(self.reputation.values()) / float(len(self.reputation))

    @property
    def rank(self):
        return rank_for(self.mean_reputation, self.content["balancing"], self.day)

    @property
    def day_rank(self):
        """Rang zu Beginn des Arbeitstags - danach richtet sich die Zahl der
        Tickets, damit sie sich nicht mitten am Tag aendert."""
        return rank_for(self.start_reputation, self.content["balancing"], self.day)

    @property
    def tickets_today(self):
        return tickets_per_day(self.day_rank, self.content["balancing"])

    def next_rank(self):
        return next_rank(self.mean_reputation, self.day, self.content["balancing"])

    @property
    def salary(self):
        """Gehalt von Bitweiche - nach der Gruendung gibt es keins mehr."""
        if self.firm:
            return 0
        return self.content["balancing"]["gehalt_pro_tag"].get(self.rank, 0)

    def founding_progress(self):
        """Fortschritt zum eigenen Unternehmen (0.0 bis 1.0) - Kapital und
        Mindest-Reputation muessen beide erreicht sein."""
        goal = self.content["balancing"]["gruendung"]
        capital = min(1.0, max(0, self.money) / float(goal["startkapital"]))
        reputation = min(1.0, self.mean_reputation / float(goal["mindest_reputation"]))
        return min(capital, reputation)

    # -- Eigenes Unternehmen (ab 0.33) ---------------------------------------

    def founding_missing(self):
        """Was fuer die Gruendung noch fehlt (leere Liste = alles erfuellt)."""
        goal = self.content["balancing"]["gruendung"]
        missing = []
        if self.firm:
            return missing
        if self.money < goal["startkapital"]:
            missing.append("noch %s Erspartes" % _whole_euro(goal["startkapital"] -
                                                             max(0, self.money)))
        if self.mean_reputation < goal["mindest_reputation"]:
            missing.append("Ansehen %d %% statt %d %%" % (round(self.mean_reputation),
                                                         goal["mindest_reputation"]))
        if goal.get("alle_erledigt") and not self.all_done():
            left = sum(1 for task in self.content["aufgaben"] if task["id"] not in self.solved)
            missing.append("%s bei Bitweiche offen" % ("1 Auftrag" if left == 1 else
                                                       "%d Aufträge" % left))
        return missing

    def founding_ready(self):
        return self.profile is not None and self.firm is None and not self.founding_missing()

    def firm_stage(self):
        """Die Ausbaustufe des eigenen Gebaeudes (aus firma.json)."""
        stages = self.content["firma"]["gebaeude"]["stufen"]
        number = self.firm["stufe"] if self.firm else 1
        return stages[min(number, len(stages)) - 1]

    def next_stage(self):
        stages = self.content["firma"]["gebaeude"]["stufen"]
        number = self.firm["stufe"] if self.firm else 1
        return stages[number] if number < len(stages) else None

    @property
    def capacity(self):
        return len(self.firm_stage()["plaetze"]) if self.firm else 0

    def has_room(self, room_id):
        """Ist der Sonderraum (lager, besprechung, ...) ausgebaut?"""
        return room_id in self.rooms

    def room_effect(self, key, default=0):
        """Vorteil aller ausgebauten Sonderraeume: Summe, bei "..._faktor"
        das Produkt (ohne Raum: default)."""
        values = [(special_room(room_id, self.content) or {}).get("effekt", {}).get(key)
                  for room_id in self.rooms]
        values = [value for value in values if value is not None]
        if not values:
            return default
        if key.endswith("_faktor"):
            result = 1.0
            for value in values:
                result *= float(value)
            return result
        return sum(values)

    def firm_costs(self):
        """Nebenkosten pro Arbeitstag: Gebaeudestufe plus Sonderraeume."""
        if not self.firm:
            return 0
        rooms = sum(int((special_room(room_id, self.content) or {}).get("nebenkosten", 0))
                    for room_id in self.rooms)
        return int(self.firm_stage().get("nebenkosten", 0)) + rooms

    def training_of(self, staff_id, day=None):
        """Laufende Weiterbildung eines Mitarbeiters am Tag (oder None)."""
        day = self.day if day is None else day
        for item in self.trainings:
            if item.get("id") == staff_id and item.get("tag", 0) <= day < item.get("bis_tag", 0):
                return item
        return None

    def staff_values(self, staff_id, day=None, pending=False):
        """Werte je Fachbereich: Einstellung plus abgeschlossene
        Weiterbildungen (pending=True: auch die laufende)."""
        day = self.day if day is None else day
        values = dict((self.staff.get(staff_id) or {}).get("werte") or {})
        for item in self.trainings:
            if item.get("id") == staff_id and (pending or item.get("bis_tag", 0) <= day):
                cat = item.get("cat")
                values[cat] = values.get(cat, 0) + int(item.get("plus", 0))
        return values

    def trainings_of(self, staff_id):
        return [item for item in self.trainings if item.get("id") == staff_id]

    def staff_list(self):
        """Mitarbeiter in der Reihenfolge der Einstellung, mit Arbeitsplatz."""
        places = self.firm_stage()["plaetze"] if self.firm else []
        result = []
        for index, (staff_id, data) in enumerate(self.staff.items()):
            item = dict(data, werte=self.staff_values(staff_id))
            item["weiterbildung"] = self.training_of(staff_id)
            item["projekt"] = self.project_of(staff_id)
            # Wer in einem Projekt mitarbeitet, macht keine Routineauftraege
            item["umsatz"] = 0 if item["weiterbildung"] or item["projekt"] else \
                staff_revenue(item["werte"], self.content)
            if index < len(places):
                item["platz"] = places[index]
            result.append(item)
        return result

    def firm_day(self):
        """Umsatz, Gehaelter und Nebenkosten des laufenden Arbeitstags."""
        if not self.firm:
            return {}
        staff = self.staff_list()
        return {"umsatz": sum(item["umsatz"] for item in staff),
                "gehaelter": sum(int(item.get("gehalt", 0)) for item in staff),
                "nebenkosten": self.firm_costs()}

    @property
    def firm_seed(self):
        return "%s|%s" % (self.firm["name"], self.firm["tag"]) if self.firm else ""

    def inquiries(self):
        """Kundenanfragen des laufenden Arbeitstags (mit Ergebnis, falls schon
        ein Angebot abgegeben wurde)."""
        return inquiries_for_day(self, self.day, self.content)

    def customer_tickets(self):
        """Kundentickets des laufenden Arbeitstags (mit "an", falls verteilt)."""
        return tickets_for_day(self, self.day, self.content)

    def delegated_to(self, person, day=None):
        """Kundentickets, die eine Person (Mitarbeiter-Kennung oder SELF) am
        Tag uebernommen hat."""
        day = self.day if day is None else day
        return [item for item in self.delegations.values()
                if item.get("tag") == day and item.get("an") == person]

    def firm_open_count(self):
        """Offene Anfragen und noch nicht verteilte Kundentickets heute."""
        if not self.firm:
            return 0
        return sum(1 for item in self.inquiries() if not item.get("ergebnis")) + \
            sum(1 for item in self.customer_tickets() if not item.get("an"))

    # -- Kundenprojekte (ab 0.35) ------------------------------------------

    def running_projects(self):
        """Gewonnene, noch nicht fertige Projekte (aelteste zuerst)."""
        return [item for item in self.projects.values() if not item["fertig"]]

    def done_projects(self):
        return [item for item in self.projects.values() if item["fertig"]]

    def project_of(self, person):
        """Kennung des laufenden Projekts, in dem eine Person mitarbeitet."""
        for item in self.running_projects():
            if person in item["team"]:
                return item["projekt"]
        return None

    def project_limit(self):
        return project_limit(self, self.content)

    def tenders(self):
        """Projektausschreibungen, die heute vorliegen (mit Ergebnis, falls
        schon ein Angebot abgegeben wurde)."""
        return project_tenders(self, self.day, self.content)

    # -- Lager ------------------------------------------------------------

    def arrived(self, task_id):
        """Ist die Ware einer (richtig erledigten) Bestellung komplett da?"""
        items = [item for item in self.deliveries if item["aufgabe"] == task_id]
        return bool(items) and all(item["ankunft"] <= self.day for item in items)

    def stock(self):
        """Lagerbestand {bauteil_id: anzahl}: angekommen minus verbaut. Ware
        mit Empfaenger (z.B. das Notebook fuer die Chefin) geht direkt weiter."""
        result = {}
        for item in self.deliveries:
            if item["ankunft"] <= self.day and not item.get("empfaenger"):
                result[item["teil"]] = result.get(item["teil"], 0) + item["menge"]
        for part_id, count in self.used.items():
            result[part_id] = result.get(part_id, 0) - count
        return {key: value for key, value in result.items() if value > 0}

    def warehouse(self):
        """Uebersicht fuer die Lager-Ansicht:
        {"unterwegs": [lieferung, ...], "bestand": [(bauteil_id, anzahl)],
         "ausgeliefert": [lieferung, ...]}"""
        on_way = [item for item in self.deliveries if item["ankunft"] > self.day]
        on_way.sort(key=lambda item: item["ankunft"])
        handed = [item for item in self.deliveries
                  if item["ankunft"] <= self.day and item.get("empfaenger")]
        stock = self.stock()
        hardware = self.content["hardware"]
        order = [item["id"] for item in hardware["teile"] + hardware.get("ersatzteile", [])]
        rows = sorted(stock.items(), key=lambda row: order.index(row[0])
                      if row[0] in order else len(order))
        return {"unterwegs": on_way, "bestand": rows, "ausgeliefert": handed}

    def available_parts(self, task):
        """Bauteile, die bei einem PC-Auftrag bereitliegen: die Teile auf der
        Werkbank plus passende Teile aus dem Lager (nur die Typen, die der
        Auftrag aus dem Lager holen darf - so nimmt kein Auftrag einem
        anderen die bestellte Ware weg)."""
        parts = list(task.get("teile", []))
        allowed = list(task.get("aus_lager") or [])
        if task.get("austausch"):
            allowed.append(task["austausch"]["typ"])
        for part_id in self.stock():
            item = part(part_id, self.content)
            if item and item["typ"] in allowed and part_id not in parts:
                parts.append(part_id)
        return parts

    # -- Tickets ------------------------------------------------------------

    def _ready(self, task):
        """Voraussetzung erfuellt? Ein Auftrag mit "nach" wartet, bis der
        vorige Auftrag erledigt und - bei einer Bestellung - die Ware da ist."""
        before = task.get("nach")
        if not before:
            return True
        if before not in self.solved:
            return False
        first = task_by_id(before, self.content)
        return first is None or first["typ"] != "bestellung" or self.arrived(before)

    def _pool(self):
        """Offene Auftraege, die heute drankommen koennen - in der Reihenfolge,
        in der sie verteilt werden: zuerst die Story-Auftraege (nach Tag),
        dann die Auftraege aus Vorlagen (nach Tag, am selben Tag gemischt)."""
        tasks = [(_pool_order(index, task), task)
                 for index, task in enumerate(self.content["aufgaben"])
                 if task.get("ab_tag", 1) <= self.day
                 and task["id"] not in self.solved
                 and task["id"] not in self.handled
                 and task["id"] not in self.wrong_orders
                 and not self.waiting_for_spare(task["id"])
                 and self._ready(task)]
        tasks.sort(key=lambda pair: pair[0])
        return [self.staffed(task) for _key, task in tasks]

    def staffed(self, task):
        """Auftrag einer Person im Ruhestand: Die Nachfolge uebernimmt ihn."""
        if task is None:
            return task
        person = active_person(task["auftraggeber"], self.day, self.content)
        if person == task["auftraggeber"]:
            return task
        return dict(task, auftraggeber=person)

    def waiting_for_spare(self, task_id):
        """Wartet der Auftrag auf ein nachbestelltes Ersatzteil?"""
        return any(order.get("aufgabe") == task_id and order.get("ankunft", 0) > self.day
                   for order in self.spare_orders)

    def spare_order_for(self, task_id):
        """Das juengste nachbestellte Ersatzteil eines Auftrags (oder None)."""
        orders = [order for order in self.spare_orders if order.get("aufgabe") == task_id]
        return orders[-1] if orders else None

    def waiting_for_delivery(self):
        """Auftraege, die nur noch auf eine Lieferung warten."""
        return [task for task in self.content["aufgaben"]
                if task["id"] not in self.solved and (
                    (task.get("nach") in self.solved and not self._ready(task)) or
                    self.waiting_for_spare(task["id"]))]

    def open_tickets(self):
        if self.firm:
            return []       # Bitweiche-Tickets gibt es nach der Gruendung nicht mehr
        per_day = self.tickets_today
        regular = [task_id for task_id in self.handled if not is_incident(task_id, self.content)]
        result = self._pool()[:max(0, per_day - len(regular))]
        incident = self.incident_today()
        if incident and incident["id"] not in self.handled:
            result.insert(0, incident)
        return self.wrong_deliveries() + result

    def wrong_deliveries(self):
        """Offene Zwischenfaelle "Falsche Ware": Die Ware einer falschen
        Bestellung ist da. Sie kommen jeden Tag wieder, bis sie behoben sind."""
        result = []
        for order_id, items in self.wrong_orders.items():
            task_id = WRONG_DELIVERY + order_id
            if task_id in self.handled or \
                    any(item["ankunft"] > self.day for item in items):
                continue
            task = task_by_id(task_id, self.content)
            if task:
                result.append(task)
        return result

    # -- Zwischenfaelle -------------------------------------------------------

    def incident_today(self):
        """Der Zwischenfall des aktuellen Arbeitstags oder None. Kein Zufall
        ueber die Uhr: Der "Wuerfel" ist ein Pruefwert aus Spielbeginn und
        Arbeitstag. So zeigen PC und Handy denselben Zwischenfall, und nichts
        muss zusaetzlich gespeichert werden. Hoechstens einer pro Tag, jeder
        nur einmal pro Spieldurchgang."""
        for task_id in self.handled:
            if is_incident(task_id, self.content) and not task_id.startswith(WRONG_DELIVERY):
                return self.staffed(task_by_id(task_id, self.content))
        rules = self.content["balancing"].get("zwischenfaelle") or {}
        if self.profile is None or self.day < rules.get("ab_tag", 2):
            return None
        seed = self.first_event or ""
        if _dice(seed, self.day, "chance") >= incident_chance(self.day, rules):
            return None
        gap = rules.get("abstand_gleiche_art", 0)
        candidates = [task for task in self.content.get("zwischenfaelle", [])
                      if task["id"] not in self.seen_incidents
                      and task.get("ab_tag", 1) <= self.day and self._ready(task)
                      and self._reporter_present(task)
                      and self.day - self.incident_days.get(task.get("gruppe", task["id"]),
                                                            -gap) >= gap]
        if not candidates:
            return None
        return self.staffed(candidates[int(_dice(seed, self.day, "wahl") * len(candidates))])

    def _reporter_present(self, task):
        """Zwischenfaelle meldet nur, wer noch da ist: Der Text nennt die
        Person oft beim Namen, im Ruhestand passt er nicht mehr."""
        person = colleague(task["auftraggeber"], self.content)
        return person is None or person_present(person, self.day)

    # -- Rack mit Geraeten aus dem Lager -------------------------------------

    def prepared_task(self, task):
        """Rack-Auftrag mit "aus_lager": Zu den bereitliegenden Geraeten kommen
        die passenden Geraete aus dem Lager (je Stueck ein Eintrag)."""
        if task is None:
            return task
        task = self.staffed(task)
        if task.get("falschlieferung"):
            items = self.wrong_orders.get(task["falschlieferung"]) or []
            goods = ", ".join("%d × %s" % (item["menge"], part(item["teil"], self.content)["name"])
                              for item in items)
            result = wrong_delivery_task(task["falschlieferung"], self.content, goods)
            result["falsche_ware"] = [[item["teil"], item["menge"]] for item in items]
            return result
        if task["typ"] == "bestellung" and task["id"] in self.returned_orders:
            return dict(task, kein_sparbonus=True)
        if task["typ"] != "rack" or not task.get("aus_lager"):
            return task
        devices = list(task.get("geraete") or [])
        start = len(devices)
        for part_id, count in self.stock().items():
            item = rack_device(part_id, self.content)
            if item and item["typ"] in task["aus_lager"]:
                devices += [part_id] * count
        return dict(task, geraete=devices, lager_ab=start)

    def todays_tickets(self):
        """Tickets des aktuellen Arbeitstags: [(aufgabe, status)]."""
        result = [(self.staffed(task_by_id(task_id, self.content)), status)
                  for task_id, status in self.handled.items()]
        result = [(task, status) for task, status in result if task]
        result += [(task, ST_OPEN) for task in self.open_tickets()]
        return result

    def tickets_in_room(self, room_id):
        return [(task, status) for task, status in self.todays_tickets()
                if task["raum"] == room_id]

    def quests(self, site=None):
        """Offene Tickets je Auftraggeber: {kollegen_id: [aufgabe, ...]} -
        mit site nur die Auftraege, die an diesem Ort erledigt werden."""
        result = {}
        for task in self.open_tickets():
            if site is not None and task_site(task, self.content) != site:
                continue
            result.setdefault(task["auftraggeber"], []).append(task)
        return result

    def open_count_by_site(self):
        """Offene Tickets je Ort (fuer die Knoepfe "Kunde oeffnen" usw.)."""
        counts = {}
        for task in self.open_tickets():
            site = task_site(task, self.content)
            counts[site] = counts.get(site, 0) + 1
        return counts

    def open_count_by_room(self):
        counts = {}
        for task in self.open_tickets():
            counts[task["raum"]] = counts.get(task["raum"], 0) + 1
        return counts

    def can_end_day(self):
        # Auch ohne bearbeitetes Ticket, wenn heute nur auf Lieferungen oder
        # spaetere Auftraege gewartet wird - sonst saesse man fest. Ab 0.33
        # auch, wenn alles erledigt ist: Bis zur Gruendung wird weiter
        # gespart, danach laeuft die eigene Firma.
        if self.firm:
            return True
        return not self.open_tickets()

    def all_done(self):
        """Keine Aufgabe mehr offen - weder heute noch an spaeteren Tagen."""
        return all(task["id"] in self.solved for task in self.content["aufgaben"])

    def status_of(self, task_id):
        return self.handled.get(task_id, ST_OPEN)

    def is_open(self, task_id):
        return any(task["id"] == task_id for task in self.open_tickets())


# ============================================================================
#  SPIEL MIT DATENBANK
# ============================================================================

class Game:
    """Verbindet Spiellogik und Datenbank. Die Oberflaechen (PC und Handy)
    nutzen nur diese Klasse."""

    def __init__(self, db, device="", content=None):
        self.db = db
        self.device = device
        self.content = content or GAME
        self.state = None
        self.reload()

    def reload(self):
        self.state = GameState(self.db.game_events(), self.content)
        return self.state

    def knowledge(self):
        return knowledge(self.db, self.content["balancing"]["wissen"])

    def _log(self, kind, data):
        self.db.log_game_event(kind, json.dumps(data, ensure_ascii=False), self.device)
        self.reload()

    def set_profile(self, name, appearance):
        name = (name or "").strip()[:30]
        if not name:
            raise ValueError("Bitte gib deiner Spielfigur einen Namen.")
        self._log(EV_PROFILE, {"name": name,
                               "aussehen": normalize_appearance(appearance)})

    def solve(self, task_id, answer, used_help):
        """Wertet ein Ticket aus, speichert das Ereignis und liefert die
        Nutzdaten (richtig, Geld, Reputation ...) fuer die Anzeige."""
        task = self.state.prepared_task(task_by_id(task_id, self.content))
        if task is None or not self.state.is_open(task_id):
            raise ValueError("Dieses Ticket ist heute nicht (mehr) offen.")
        payload = evaluate(task, answer, used_help, self.knowledge(), self.state.day,
                           self.content["balancing"], self.state.available_parts(task),
                           self.content, self.state.stock())
        self._log(EV_SOLVED, payload)
        return payload

    def order_spare(self, task_id, part_id):
        """Austausch: Das passende Ersatzteil fehlt im Lager und wird
        nachbestellt. Das Ticket wartet, bis es da ist."""
        task = self.state.prepared_task(task_by_id(task_id, self.content))
        if task is None or not self.state.is_open(task_id):
            raise ValueError("Dieses Ticket ist heute nicht (mehr) offen.")
        if not task.get("austausch") or task.get("zwischenfall"):
            raise ValueError("Für dieses Ticket kann nichts nachbestellt werden.")
        item = part(part_id, self.content)
        if not item or item["typ"] != task["austausch"]["typ"]:
            raise ValueError("Dieses Teil passt nicht zum Austausch.")
        payload = {"aufgabe": task_id, "tag": self.state.day, "teil": part_id,
                   "geld": -int(item["preis"]), "haendler": spare_dealer(self.content),
                   "ankunft": self.state.day + spare_delivery_days(self.content)}
        self._log(EV_SPARE_ORDER, payload)
        return payload

    def defer(self, task_id):
        task = task_by_id(task_id, self.content)
        if task is None or not self.state.is_open(task_id):
            raise ValueError("Dieses Ticket ist heute nicht (mehr) offen.")
        payload = defer_payload(task, self.state.day, self.content["balancing"])
        self._log(EV_DEFERRED, payload)
        return payload

    def end_day(self):
        if not self.state.can_end_day():
            raise ValueError("Es sind noch Tickets offen.")
        payload = {"tag": self.state.day, "gehalt": self.state.salary,
                   "rang": self.state.rank}
        if self.state.rent:
            payload["miete"] = self.state.rent
        if self.state.firm:
            payload["firma"] = self.state.firm_day()
            outcomes = ticket_outcomes(self.state, self.content)
            if outcomes:
                payload["firma"]["tickets"] = outcomes
            days = project_outcomes(self.state, self.knowledge(), self.learned_projects(),
                                    self.content)
            if days:
                payload["firma"]["projekte"] = days
        self._log(EV_DAY_END, payload)
        return payload

    # -- Eigenes Unternehmen (ab 0.33) -----------------------------------------

    def found_firm(self, name):
        """Gruendet die eigene Firma (Schwelle erreicht, alles erledigt)."""
        name = " ".join((name or "").split())[:FIRM_NAME_MAX]
        if not name:
            raise ValueError("Bitte gib deiner Firma einen Namen.")
        if self.state.firm:
            raise ValueError("Du hast schon eine Firma gegründet.")
        missing = self.state.founding_missing()
        if missing:
            raise ValueError("Für die Gründung fehlt noch: %s." % ", ".join(missing))
        cost = int(self.content["firma"]["gruendung"]["kosten"])
        payload = {"tag": self.state.day, "name": name, "geld": -cost}
        self._log(EV_FOUNDED, payload)
        return payload

    def _firm_required(self):
        if not self.state.firm:
            raise ValueError("Dafür brauchst du zuerst eine eigene Firma.")

    def hire(self, applicant_id):
        self._firm_required()
        applicant = next((item for item in applicants(self.state, self.content)
                          if item["id"] == applicant_id), None)
        if applicant is None:
            raise ValueError("Diese Bewerbung liegt nicht (mehr) vor.")
        if len(self.state.staff) >= self.state.capacity:
            raise ValueError("Alle Arbeitsplätze sind besetzt. Für mehr Leute musst du "
                             "das Gebäude ausbauen.")
        if self.state.money <= 0:
            raise ValueError("Mit leerem Konto kannst du niemanden einstellen.")
        payload = {key: applicant[key] for key in ("id", "name", "aussehen", "werte",
                                                   "gehalt", "herkunft", "schwerpunkt",
                                                   "macke", "rolle")}
        payload["tag"] = self.state.day
        self._log(EV_HIRED, payload)
        return payload

    def fire(self, staff_id):
        self._firm_required()
        if staff_id not in self.state.staff:
            raise ValueError("Diese Person arbeitet nicht bei dir.")
        payload = {"id": staff_id, "tag": self.state.day}
        self._log(EV_FIRED, payload)
        return payload

    def train(self, staff_id, cat):
        """Abstrakte Weiterbildung: kostet Geld und Arbeitstage ohne Umsatz,
        danach steigt der Wert im Fachbereich."""
        self._firm_required()
        offer = training_offer(self.state, staff_id, cat, self.content)
        if offer["problem"]:
            raise ValueError(offer["problem"])
        payload = {"id": staff_id, "cat": cat, "geld": -offer["preis"], "tag": self.state.day,
                   "bis_tag": self.state.day + offer["tage"], "plus": offer["plus"]}
        self._log(EV_TRAINING, payload)
        return payload

    def expand(self):
        self._firm_required()
        stage = self.state.next_stage()
        if stage is None:
            raise ValueError("Das Gebäude ist fertig ausgebaut.")
        if self.state.money < stage["preis"]:
            raise ValueError("Dafür reicht dein Geld noch nicht (%s fehlen)."
                             % _whole_euro(stage["preis"] - max(0, self.state.money)))
        payload = {"stufe": stage["stufe"], "geld": -int(stage["preis"]),
                   "tag": self.state.day}
        self._log(EV_EXPAND, payload)
        return payload

    def build_room(self, room_id):
        """Baut einen Sonderraum aus (ab 0.36), sobald die Stufe erreicht ist."""
        self._firm_required()
        status = next((item for item in room_status(self.state, self.content)
                       if item["id"] == room_id), None)
        if status is None:
            raise ValueError("Diesen Raum gibt es nicht.")
        if status["problem"]:
            raise ValueError(status["problem"])
        payload = {"raum": room_id, "geld": -int(status["preis"]), "tag": self.state.day}
        self._log(EV_ROOM, payload)
        return payload

    def send_offer(self, inquiry_id, markup, answer):
        """Gibt ein Angebot zu einer Kundenanfrage ab. Das Ergebnis (gegen
        Bitweiche gewonnen oder verloren) steht sofort fest."""
        self._firm_required()
        inquiry = next((item for item in self.state.inquiries()
                        if item["id"] == inquiry_id), None)
        if inquiry is None or inquiry.get("ergebnis"):
            raise ValueError("Diese Anfrage liegt heute nicht (mehr) vor.")
        if markup not in offer_rules(self.content)["zuschlaege"]:
            raise ValueError("Bitte wähle einen Gewinnzuschlag.")
        payload = offer_result(self.state, inquiry, markup, answer, self.content)
        self._log(EV_OFFER_WON if payload["gewonnen"] else EV_OFFER_LOST, payload)
        return payload

    def delegate(self, ticket_id, person):
        """Verteilt ein Kundenticket an einen Mitarbeiter oder an sich selbst
        (person = SELF). Die Erfolgschance wird hier festgehalten, das
        Ergebnis gibt es beim Feierabend."""
        self._firm_required()
        ticket = next((item for item in self.state.customer_tickets()
                       if item["id"] == ticket_id), None)
        if ticket is None:
            raise ValueError("Dieses Kundenticket liegt heute nicht (mehr) vor.")
        if ticket.get("an"):
            raise ValueError("Dieses Kundenticket ist schon verteilt.")
        option = next((item for item in ticket_candidates(self.state, ticket,
                                                          self.knowledge(), self.content)
                       if item["an"] == person), None)
        if option is None:
            raise ValueError("Diese Person arbeitet nicht bei dir.")
        if option["problem"]:
            raise ValueError(option["problem"])
        payload = {"ticket": ticket_id, "vorlage": ticket["vorlage"], "tag": self.state.day,
                   "an": person, "name": option["name"], "chance": option["chance"]}
        self._log(EV_DELEGATED, payload)
        return payload

    def learned_projects(self):
        """Nummern der Testprojekte, die im Lernbereich bearbeitet wurden."""
        try:
            return set(self.db.completed_projects())
        except (AttributeError, TypeError):
            return set()

    def send_project_offer(self, project_id, markup, answer):
        """Gibt ein Angebot fuer eine Projektausschreibung ab. Das Ergebnis
        gegen die Mitbewerber steht sofort fest."""
        self._firm_required()
        project = next((item for item in self.state.tenders()
                        if item["id"] == project_id), None)
        if project is None or project.get("ergebnis"):
            raise ValueError("Diese Ausschreibung liegt nicht (mehr) vor.")
        problem = project_offer_problem(self.state, self.content)
        if problem:
            raise ValueError(problem)
        if markup not in offer_rules(self.content)["zuschlaege"]:
            raise ValueError("Bitte wähle einen Gewinnzuschlag.")
        payload = project_offer_result(self.state, project, markup, answer, self.state.day,
                                       self.content)
        self._log(EV_PROJECT_WON if payload["gewonnen"] else EV_PROJECT_LOST, payload)
        return payload

    def set_project_team(self, project_id, team):
        """Stellt das Team eines laufenden Projekts neu zusammen."""
        self._firm_required()
        project = self.state.projects.get(project_id)
        if project is None or project["fertig"]:
            raise ValueError("Dieses Projekt läuft nicht (mehr).")
        team = [person for index, person in enumerate(team or []) if person not in team[:index]]
        options = {item["an"]: item for item in project_candidates(
            self.state, project, self.knowledge(), self.content)}
        for person in team:
            if person not in options:
                raise ValueError("Diese Person arbeitet nicht bei dir.")
            if options[person]["problem"] and person not in project["team"]:
                raise ValueError(options[person]["problem"])
        payload = {"projekt": project_id, "tag": self.state.day, "team": team}
        self._log(EV_PROJECT_TEAM, payload)
        return payload

    def toggle_project_member(self, project_id, person):
        """Nimmt eine Person ins Team auf oder wieder heraus."""
        project = self.state.projects.get(project_id)
        if project is None:
            raise ValueError("Dieses Projekt läuft nicht (mehr).")
        team = list(project["team"])
        if person in team:
            team.remove(person)
        else:
            team.append(person)
        return self.set_project_team(project_id, team)

    def reset(self):
        ok = self.db.reset_game()
        self.reload()
        return ok

    # -- Wohnung --------------------------------------------------------------

    def buy_furniture(self, item_id):
        """Kauft ein Moebelstueck - es landet erst einmal im Karton."""
        item = furniture_item(item_id, self.content)
        if item is None or not item.get("laden", True):
            raise ValueError("Dieses Möbelstück gibt es im Möbelhaus nicht.")
        if self.state.money < item["preis"]:
            raise ValueError("Dafür reicht dein Geld noch nicht (%d € fehlen)."
                             % (item["preis"] - max(0, self.state.money)))
        piece = "m" + uuid.uuid4().hex[:10]
        self._log(EV_BUY, {"stueck": piece, "moebel": item_id, "geld": -item["preis"]})
        return piece

    def sell_furniture(self, piece):
        """Verkauft ein Moebelstueck zum halben Preis."""
        item = furniture_item(self.state.furniture.get(piece), self.content)
        if item is None:
            raise ValueError("Dieses Möbelstück gehört dir nicht.")
        price = int(item["preis"] * self.content["wohnungen"].get("rueckkauf", 0.5))
        layout = home_layout(self.state, self.content)
        if piece in layout["moebel"]:
            del layout["moebel"][piece]
            self._log(EV_LAYOUT, dict(layout, wohnung=self.state.home_id))
        self._log(EV_SELL, {"stueck": piece, "moebel": item["id"], "geld": price})
        return price

    def place_furniture(self, piece, x, y, turn=0):
        """Stellt ein Moebelstueck auf (oder um). Fehler als ValueError."""
        item_id = self.state.furniture.get(piece)
        if item_id is None:
            raise ValueError("Dieses Möbelstück gehört dir nicht.")
        x, y = snap(x), snap(y)
        problem = placement_problem(self.state, piece, item_id, x, y, turn,
                                    content=self.content)
        if problem:
            raise ValueError(problem)
        layout = home_layout(self.state, self.content)
        layout["moebel"][piece] = [x, y, int(turn) % 4]
        self._log(EV_LAYOUT, dict(layout, wohnung=self.state.home_id))

    def box_furniture(self, piece):
        """Packt ein Moebelstueck zurueck in den Karton."""
        layout = home_layout(self.state, self.content)
        if layout["moebel"].pop(piece, None) is not None:
            self._log(EV_LAYOUT, dict(layout, wohnung=self.state.home_id))

    def set_floor(self, room_id, kind, color):
        layout = home_layout(self.state, self.content)
        layout["boeden"][room_id] = [kind, color]
        self._log(EV_LAYOUT, dict(layout, wohnung=self.state.home_id))

    def move_home(self, home_id, rent=None):
        """Umzug in eine groessere Wohnung - alle Moebel kommen in Kartons.
        rent=True mietet (Kaution, danach Miete je Arbeitstag), rent=False
        kauft (Einmalzahlung); None nimmt den Schalter aus den Optionen.
        Der Mietvertrag steht im Ereignis, damit PC und Handy denselben
        Kontostand berechnen - der Schalter selbst ist nur lokal."""
        target = apartment(home_id, self.content)
        if target is None or target not in moves_available(self.state, self.content):
            raise ValueError("In diese Wohnung kannst du nicht umziehen.")
        if rent is None:
            rent = rent_mode()
        offer = move_offer(self.state, target, rent, self.content)
        if offer["fehlt"]:
            raise ValueError("Dafür reicht dein Geld noch nicht (%d € fehlen)."
                             % offer["fehlt"])
        payload = {"wohnung": home_id, "geld": offer["zurueck"] - offer["kosten"]}
        if rent:
            payload.update(miete=offer["miete"], kaution=offer["kosten"])
        if offer["zurueck"]:
            payload["kaution_zurueck"] = offer["zurueck"]
        self._log(EV_MOVE, payload)
        return payload


# ============================================================================
#  EIGENES UNTERNEHMEN (ab 0.33)
# ============================================================================
#
# Alle Zahlen stehen in inhalte/spiel/firma.json. Bewerber werden nicht frei
# ausgewuerfelt, sondern wie die Zwischenfaelle aus festen Pruefwerten
# (Firmenname, Gruendungstag, Bewerbungsrunde) berechnet: PC und Handy sehen
# dieselben Leute, gespeichert wird erst die Einstellung.

FIRM_NAME_MAX = 40
STAFF_PREFIX = "kollege:"          # Bitweiche-Kollegen, die zu dir wechseln

# Arten im Kassenbuch (Anzeige "Finanzen")
BOOK_TASKS = "Aufträge"
BOOK_SALARY = "Gehalt"
BOOK_HOME = "Wohnen"
BOOK_GOODS = "Wareneinkauf"
BOOK_FOUNDING = "Gründung"
BOOK_REVENUE = "Umsatz Mitarbeiter"
BOOK_WAGES = "Gehälter"
BOOK_COSTS = "Nebenkosten"
BOOK_TRAINING = "Weiterbildung"
BOOK_BUILDING = "Ausbau"
BOOK_OFFERS = "Angebote"
BOOK_TICKETS = "Kundentickets"
BOOK_PROJECTS = "Projekte"
BOOK_MATERIAL = "Projektmaterial"

SELF = "ich"                       # Kundenticket uebernimmt die Spielfigur selbst
INQUIRY_PREFIX = "anfrage:"        # anfrage:<tag>:<nummer>
TICKET_PREFIX = "kundenticket:"    # kundenticket:<tag>:<vorlage>
PROJECT_PREFIX = "projekt:"        # projekt:<nummer der ausschreibung>


# Reiter im Unterpunkt "Firma" (PC und Handy gleich beschriftet)
FIRM_TABS = [("auftraege", "Aufträge"), ("projekte", "Projekte"),
             ("mitarbeiter", "Mitarbeiter"),
             ("bewerbungen", "Bewerbungen"),
             ("gebaeude", "Gebäude"), ("finanzen", "Finanzen")]


FIRM_IDLE_TEXT = ("Für heute ist alles verteilt und angeboten. Deine Leute kümmern sich "
                  "außerdem um Routineaufträge, die bringen jeden Arbeitstag Umsatz. "
                  "Die Ergebnisse der Kundentickets gibt es beim Feierabend.")
FOUNDING_TEASER = ("Du hast alles, was du für eine eigene Firma brauchst: genug Erspartes, "
                   "gutes Ansehen und keinen offenen Auftrag mehr.")


def firm_tabs(state):
    """Vor der Gruendung gibt es nur die Finanzen."""
    return FIRM_TABS if state.firm else [tab for tab in FIRM_TABS if tab[0] == "finanzen"]


def values_text(values):
    """ "Netzwerk 35 · Sicherheit 15 · ..." """
    return " · ".join("%s %d" % (CATEGORY_SHORT[CAT_NAME[key]], values.get(key, 0))
                      for key in CAT_ORDER)


def staff_money_text(item, content=None):
    """Gehalt und Umsatz einer Person pro Arbeitstag."""
    revenue = item.get("umsatz")
    if revenue is None:
        revenue = staff_revenue(item["werte"], content)
    return "Gehalt %s · Umsatz %s pro Arbeitstag" % (_whole_euro(item["gehalt"]),
                                                     _whole_euro(revenue))


def training_text(state, item):
    """Zeile zur laufenden Weiterbildung (oder leer)."""
    training = item.get("weiterbildung")
    if not training:
        return ""
    left = training["bis_tag"] - state.day
    return "In Weiterbildung (%s, +%d) · noch %s" % (
        CATEGORY_SHORT[CAT_NAME[training["cat"]]], training["plus"],
        "1 Arbeitstag" if left == 1 else "%d Arbeitstage" % left)


def firm_rules(content=None):
    return (content or GAME)["firma"]


def staff_salary(values, content=None):
    rule = firm_rules(content)["gehalt"]
    return int(round(rule["basis"] + rule["je_punkt"] * sum(values.values())))


def staff_revenue(values, content=None):
    rule = firm_rules(content)["umsatz"]
    return int(round(rule["basis"] + rule["je_punkt"] * sum(values.values())))


def staff_focus(values):
    """Fachbereich mit dem hoechsten Wert (bei Gleichstand der erste)."""
    return max(CAT_ORDER, key=lambda key: (values.get(key, 0), -CAT_ORDER.index(key)))


def staff_role(values):
    return "Schwerpunkt %s" % CATEGORY_SHORT[CAT_NAME[staff_focus(values)]]


def _pick(options, seed, batch, salt):
    return options[int(_dice(seed, batch, salt) * len(options))]


def _applicant(rules, seed, batch, number, content):
    """Ein generischer Bewerber (fest aus seed, Runde und Nummer)."""
    salt = "b%d-%d" % (batch, number)
    low, high = rules["bewerbung"]["werte_min"], rules["bewerbung"]["werte_max"]
    values = {}
    for key in CAT_ORDER:
        raw = low + _dice(seed, batch, salt + key) * (high - low)
        values[key] = int(round(raw / 5.0) * 5)
    focus = _pick(CAT_ORDER, seed, batch, salt + "schwerpunkt")
    values[focus] = min(90, values[focus] + rules["bewerbung"]["schwerpunkt_plus"])
    names = rules["namen"]
    look = {part: _pick([key for key, _name in options], seed, batch, salt + part)
            for part, options in APPEARANCE.items() if part != "kreis"}
    look["kreis"] = "violett"
    return {"id": "bw%d-%d" % (batch, number),
            "name": "%s %s" % (_pick(names["vornamen"], seed, batch, salt + "vor"),
                               _pick(names["nachnamen"], seed, batch, salt + "nach")),
            "aussehen": normalize_appearance(look), "werte": values,
            "gehalt": staff_salary(values, content), "herkunft": "bewerbung",
            "schwerpunkt": staff_focus(values),
            "macke": _pick(rules["macken"], seed, batch, salt + "macke"),
            "rolle": staff_role(values)}


def switchers(state, content=None):
    """Bitweiche-Kollegen, die sich gerade bei dir bewerben:
    [(wechsel-eintrag, erster tag, letzter tag)]."""
    content = content or GAME
    if not state.firm:
        return []
    start = state.firm["tag"]
    result = []
    for item in firm_rules(content).get("wechsel", []):
        first = start + item["nach_tagen"]
        last = first + item.get("offen_tage", 10) - 1
        result.append((item, first, last))
    return result


def applicants(state, content=None):
    """Bewerbungen, die heute vorliegen - generische Bewerber der laufenden
    Runde und wechselwillige Bitweiche-Kollegen. Schon Eingestellte fehlen."""
    content = content or GAME
    if not state.firm:
        return []
    rules = firm_rules(content)
    step = rules["bewerbung"]["abstand_tage"]
    start = state.firm["tag"]
    batch = max(0, state.day - start) // step
    seed = "%s|%s" % (state.firm["name"], start)
    result = []
    for item, first, last in switchers(state, content):
        staff_id = STAFF_PREFIX + item["kollege"]
        person = colleague(item["kollege"], content)
        if person is None or staff_id in state.ever_hired or not first <= state.day <= last:
            continue
        values = dict(item["werte"])
        result.append({"id": staff_id, "name": person["name"],
                       "aussehen": normalize_appearance(person.get("aussehen")),
                       "werte": values, "gehalt": staff_salary(values, content),
                       "herkunft": "bitweiche", "schwerpunkt": staff_focus(values),
                       "macke": person.get("macke", ""),
                       "rolle": "bisher %s bei Bitweiche" % person["rolle"],
                       "bis_tag": last})
    for number in range(rules["bewerbung"]["anzahl"]):
        item = _applicant(rules, seed, batch, number, content)
        if item["id"] in state.ever_hired:
            continue
        item["bis_tag"] = start + (batch + 1) * step - 1
        result.append(item)
    return result


def switch_news(state, content=None):
    """Story-Moment am Morgen: Ein Bitweiche-Kollege will wechseln."""
    texts = []
    for item, first, _last in switchers(state, content):
        if first == state.day and STAFF_PREFIX + item["kollege"] not in state.ever_hired:
            texts.append(_lines(item["text"]))
    return "\n\n".join(texts)


def training_offer(state, staff_id, cat, content=None):
    """Was eine Weiterbildung kostet und bringt: {"preis", "tage", "plus",
    "problem" (leer = moeglich)}."""
    rules = firm_rules(content)["weiterbildung"]
    done = len(state.trainings_of(staff_id))
    # Eigener Schulungsraum (ab 0.36): guenstiger und kuerzer
    price = discounted(int(rules["preis"] + rules["aufschlag"] * done),
                       state.room_effect("weiterbildung_rabatt"))
    days = max(1, int(rules["tage"]) - int(state.room_effect("weiterbildung_tage_minus")))
    result = {"preis": price, "tage": days, "plus": 0, "problem": ""}
    if staff_id not in state.staff:
        result["problem"] = "Diese Person arbeitet nicht bei dir."
        return result
    if cat not in CAT_ORDER:
        result["problem"] = "Unbekannter Fachbereich."
        return result
    value = state.staff_values(staff_id, pending=True).get(cat, 0)
    result["plus"] = max(0, min(int(rules["plus"]), int(rules["max"]) - value))
    if state.training_of(staff_id):
        result["problem"] = "Die Person ist gerade schon in einer Weiterbildung."
    elif not result["plus"]:
        result["problem"] = "In diesem Fachbereich ist das Maximum (%d) erreicht." % rules["max"]
    elif state.money < result["preis"]:
        result["problem"] = "Dafür reicht dein Geld noch nicht (%s fehlen)." % _whole_euro(
            result["preis"] - max(0, state.money))
    return result


def firm_people(state, content=None):
    """Die Mitarbeiter als Personen im eigenen Gebaeude (wie die Kollegen)."""
    result = []
    for item in state.staff_list():
        if not item.get("platz"):
            continue
        x, y, room_id = item["platz"]
        training = item.get("weiterbildung")
        task = next((ticket for ticket in state.customer_tickets()
                     if ticket.get("an") == item["id"]), None)
        project = state.projects.get(item.get("projekt")) if item.get("projekt") else None
        result.append({"id": item["id"], "name": item["name"], "rolle": item["rolle"],
                       "kundenticket": task,
                       "projekt_text": project_office_text(state, project, content)
                       if project else "",
                       "raum": room_id, "platz": [float(x), float(y)],
                       "aussehen": item.get("aussehen"), "macke": item.get("macke", ""),
                       "mitarbeiter": True, "umsatz": item["umsatz"],
                       "in_weiterbildung": bool(training)})
    return result


def room_rules(content=None):
    """firma.json "sonderraeume" (ab 0.36): {"leerstand" {...}, "raeume" [...]}."""
    return firm_rules(content).get("sonderraeume") or {}


def special_rooms(content=None):
    return list(room_rules(content).get("raeume") or [])


def special_room(room_id, content=None):
    return next((item for item in special_rooms(content) if item["id"] == room_id), None)


def room_status(state, content=None):
    """Die Sonderraeume fuer die Oberflaeche: [{"id", "name", "vorteil",
    "preis", "nebenkosten", "ab_stufe", "gebaut", "problem"}] - problem ist
    leer, wenn man den Raum jetzt ausbauen kann."""
    stage = state.firm["stufe"] if state.firm else 0
    result = []
    for rule in special_rooms(content):
        item = {key: rule[key] for key in ("id", "name", "vorteil", "preis", "nebenkosten",
                                           "ab_stufe")}
        item["gebaut"] = state.has_room(rule["id"])
        if item["gebaut"]:
            item["problem"] = "Schon ausgebaut."
        elif stage < int(rule["ab_stufe"]):
            item["problem"] = "Erst ab Ausbaustufe %d möglich." % rule["ab_stufe"]
        elif state.money < int(rule["preis"]):
            item["problem"] = "Dafür reicht dein Geld noch nicht (%s fehlen)." % _whole_euro(
                int(rule["preis"]) - max(0, state.money))
        else:
            item["problem"] = ""
        result.append(item)
    return result


def room_status_text(item):
    """Kurze Zeile zu Preis und Nebenkosten eines Sonderraums. Ist er schon
    ausgebaut, zaehlen nur noch die Nebenkosten."""
    if item["gebaut"]:
        return "Nebenkosten +%s pro Arbeitstag" % _whole_euro(item["nebenkosten"])
    return "%s · Nebenkosten +%s pro Arbeitstag" % (
        _whole_euro(item["preis"]), _whole_euro(item["nebenkosten"]))


def firm_building(state, content=None):
    """Grundriss der jetzigen Ausbaustufe. Nicht ausgebaute Sonderraeume
    sind Leerstand: Estrich, grau, ohne Einrichtung."""
    building = state.firm_stage()["gebaeude"]
    rules = room_rules(content or state.content)
    empty = {rule["raum"]: rule for rule in rules.get("raeume") or []
             if not state.has_room(rule["id"])}
    if not empty or not any(item["id"] in empty for item in building["raeume"]):
        return building
    key = ("leerstand", id(building), frozenset(empty))
    cached = _SITE_CACHE.get(key)
    if cached and cached[0] is building:
        return cached[1]
    look = rules.get("leerstand") or {}
    result = copy.deepcopy(building)
    for item in result["raeume"]:
        rule = empty.get(item["id"])
        if rule is None:
            continue
        item.update({"name": look.get("name", "Leerstand"), "kurz": look.get("kurz", "Frei"),
                     "farbe": look.get("farbe", "#8B93A1"), "boden": look.get("boden", "beton"),
                     "deko": [], "leerstand": rule["id"],
                     "text": look.get("text", "Hier kann ein %s entstehen.") % rule["name"]
                     + " " + rule["vorteil"]})
    _SITE_CACHE[key] = (building, result)
    return result


def founding_text(content=None):
    rules = firm_rules(content)["gruendung"]
    text = _lines(rules["text"])
    return text.replace("%s", _whole_euro(rules["kosten"]))


def founded_text(name, content=None):
    return _lines(firm_rules(content)["gruendung"]["gegruendet"]).replace("%s", name)


def default_firm_name(state):
    name = (state.profile or {}).get("name", "").strip()
    return ("%s IT-Service" % name.split()[0]) if name else "IT-Service"


def finance_days(state, count=7):
    """Die letzten Arbeitstage im Kassenbuch (neuester zuerst):
    [{"tag", "ein" {art: euro}, "aus" {art: euro}, "einnahmen", "ausgaben",
    "gewinn"}] - der laufende Tag ist dabei, sobald etwas gebucht ist."""
    result = []
    for day in sorted(state.book, reverse=True)[:count]:
        entry = state.book[day]
        income = sum(entry["ein"].values())
        costs = sum(entry["aus"].values())
        result.append({"tag": day, "ein": dict(entry["ein"]), "aus": dict(entry["aus"]),
                       "einnahmen": income, "ausgaben": costs, "gewinn": income - costs})
    return result


def finance_totals(state):
    """Summen ueber das ganze Spiel je Art: ({art: ein}, {art: aus})."""
    income, costs = {}, {}
    for entry in state.book.values():
        for kind, value in entry["ein"].items():
            income[kind] = income.get(kind, 0) + value
        for kind, value in entry["aus"].items():
            costs[kind] = costs.get(kind, 0) + value
    return income, costs


def balance_series(state, limit=30):
    """Kontostand nach den letzten Feierabenden: (beschriftungen, werte)."""
    points = state.balances[-limit:] + [(state.day, state.money)]
    return ["T%d" % day for day, _money in points], [max(0, money) for _day, money in points]


def firm_summary(state):
    """Eine Zeile zur Firma (Uebersicht auf PC und Handy)."""
    numbers = state.firm_day()
    profit = numbers["umsatz"] - numbers["gehaelter"] - numbers["nebenkosten"]
    return "%d von %d Plätzen besetzt · heute %s%s" % (
        len(state.staff), state.capacity, "+" if profit >= 0 else "-",
        _whole_euro(abs(profit)))


def firm_day_text(numbers):
    """ "Umsatz: +300 €. Gehälter: -180 €. Nebenkosten: -40 €." - dazu je
    Kundenticket eine Zeile mit dem Ergebnis (ab 0.34)."""
    text = "Umsatz Mitarbeiter: +%s. Gehälter: -%s. Nebenkosten: -%s." % (
        _whole_euro(numbers.get("umsatz", 0)), _whole_euro(numbers.get("gehaelter", 0)),
        _whole_euro(numbers.get("nebenkosten", 0)))
    lines = [ticket_result_text(item) for item in numbers.get("tickets") or []]
    if lines:
        text += "\n\nKundentickets:\n" + "\n".join("• " + line for line in lines)
    lines = [project_day_text(item) for item in numbers.get("projekte") or []]
    if lines:
        text += "\n\nProjekte:\n" + "\n".join("• " + line for line in lines)
    return text


# -- Angebote und Kundentickets (ab 0.34) ---------------------------------------
#
# Anfragen und Tickets eines Arbeitstags werden wie die Bewerber aus festen
# Pruefwerten berechnet (Firmenname, Gruendungstag, Arbeitstag). Gespeichert
# wird erst, was man daraus macht: das abgegebene Angebot mit Ergebnis und wer
# welches Ticket uebernimmt.

def offer_rules(content=None):
    return firm_rules(content)["angebote"]


def ticket_rules(content=None):
    return firm_rules(content)["tickets"]


def firm_customer(customer_id, content=None):
    return next((item for item in firm_rules(content).get("kunden", [])
                 if item["id"] == customer_id), None)


def _between(seed, day, salt, low, high):
    """Ganze Zahl von low bis high (beide einschliesslich), fest gewuerfelt."""
    return low + min(high - low, int(_dice(seed, day, salt) * (high - low + 1)))


def inquiries_for_day(state, day, content=None):
    """Die Kundenanfragen eines Arbeitstags:
    [{"id", "tag", "kunde" {...}, "artikel", "menge", "einkaufspreis",
      "lieferzeit", "markt" (Bitweiche-Zuschlag in %, erst nach dem Angebot
      zeigen), "text", "ergebnis" (Ereignisdaten oder None)}]"""
    content = content or GAME
    if not state.firm:
        return []
    rules = offer_rules(content)
    customers = firm_rules(content)["kunden"]
    seed = state.firm_seed
    first = int(_dice(seed, day, "anfrage-kunde") * len(customers))
    result = []
    discount = state.room_effect("material_rabatt")
    for number in range(int(rules["pro_tag"]) + int(state.room_effect("anfragen_plus"))):
        salt = "anfrage%d-" % number
        # Verschiedene Kunden am selben Tag
        customer = customers[(first + number * max(1, len(customers) // 2 - 1))
                             % len(customers)]
        article = _pick(rules["artikel"], seed, day, salt + "artikel")
        low, high = article["preis"]
        price = int(round((low + _dice(seed, day, salt + "preis") * (high - low)) / 5.0) * 5)
        count = _between(seed, day, salt + "menge", *article["menge"])
        bids, absent = competitor_bids("anfrage", customer["art"], None, seed, day, salt,
                                       content)
        cheapest = min(bids, key=lambda bid: bid["zuschlag"])
        delivery = _between(seed, day, salt + "lieferzeit", rules["lieferzeit"]["von"],
                            rules["lieferzeit"]["bis"])
        text = _pick(rules["texte"], seed, day, salt + "text").format(
            kontakt=customer["kontakt"], menge=count, artikel=article["name"],
            lieferzeit=delivery)
        inquiry_id = "%s%d:%d" % (INQUIRY_PREFIX, day, number + 1)
        result.append({"id": inquiry_id, "tag": day, "kunde": customer,
                       "artikel": article["name"], "menge": count,
                       # Mit eigenem Lager kauft man guenstiger ein als die Mitbewerber
                       "einkaufspreis": discounted(price, discount),
                       "listenpreis": price,
                       "lieferzeit": delivery, "markt": cheapest["zuschlag"],
                       "laune": cheapest["laune"], "konkurrent": cheapest["id"],
                       "bieter": bids, "ausgefallen": absent,
                       "text": "%s\n\n%s" % (text, customer["satz"]),
                       "ergebnis": state.offers.get(inquiry_id)})
    return result


def _market_markup(rules, kind, seed, day, salt):
    """Bitweiches Gewinnzuschlag fuer eine Anfrage: (prozent, laune).
    Meist aus der Spanne der Kundenart (die Mitte ist wahrscheinlicher),
    manchmal ein Kampfpreis oder ein teures Angebot, weil Bitweiche
    ausgelastet ist - so ist kein Zuschlag sicher."""
    low, high = kind["von"], kind["bis"]
    middle = (_dice(seed, day, salt + "markt") + _dice(seed, day, salt + "markt2")) / 2.0
    market = low + min(high - low, int(middle * (high - low + 1)))
    moods = rules.get("laune") or {}
    roll = _dice(seed, day, salt + "laune")
    fight = moods.get("kampfpreis")
    busy = moods.get("ausgelastet")
    if fight and roll < fight["chance"]:
        return _between(seed, day, salt + "kampf", fight["von"], fight["bis"]), "kampfpreis"
    if busy and roll > 1 - busy["chance"]:
        return market + _between(seed, day, salt + "teuer", busy["plus_von"],
                                 busy["plus_bis"]), "ausgelastet"
    return market, ""


def inquiry_task(inquiry, markup, content=None):
    """Die Anfrage als Formular-Aufgabe (Zuschlagskalkulation wie seit 0.28),
    damit PC und Handy die vorhandene Formular-Ansicht nutzen koennen."""
    rules = offer_rules(content)
    return {"id": inquiry["id"], "typ": "formular", "art": "angebot",
            "titel": "Angebot für %s" % inquiry["kunde"]["name"],
            "ticket": inquiry["text"],
            "frage": "Wähle deinen Gewinnzuschlag und rechne das Angebot durch.",
            "daten": {"menge": inquiry["menge"], "artikel": inquiry["artikel"],
                      "einkaufspreis": inquiry["einkaufspreis"],
                      "handlungskosten": rules["handlungskosten"], "gewinn": markup,
                      "ust": rules["ust"]},
            "hilfe": list(rules.get("hilfe") or [])}


def offer_numbers(inquiry, markup, content=None):
    """{schluessel: wert} der richtigen Zuschlagskalkulation."""
    task = inquiry_task(inquiry, markup, content)
    return {key: value for key, _label, value in offer_values(task["daten"])}


def discounted(price, percent):
    """Einkaufspreis mit Rabatt in Prozent (ganze Euro, ab 0.36: Lager)."""
    if not percent:
        return price
    return int(round(price * (1 - percent / 100.0)))


def market_price(inquiry, content=None):
    """Nettopreis von Bitweiche: Selbstkosten zum Listenpreis (ohne den
    Lager-Rabatt der eigenen Firma) plus Bitweiches Zuschlag."""
    market = dict(inquiry, einkaufspreis=inquiry.get("listenpreis", inquiry["einkaufspreis"]))
    cost = offer_numbers(market, 0, content)["selbstkosten"]
    return _money(cost * (1 + inquiry["markt"] / 100.0))


def offer_advantage(state, content=None):
    """Wie viel Prozent man ueber Bitweiche liegen darf (guter Ruf)."""
    rule = offer_rules(content)["vorteil"]
    return rule["prozent"] if state.reputation.get("kundenzufriedenheit", 0) >= \
        rule["ab_kundenzufriedenheit"] else 0


def offer_result(state, inquiry, markup, answer, content=None):
    """Bewertet ein Angebot: Rechnung richtig und Preis nicht hoeher als
    der von Bitweiche (plus Vorteil) - dann ist der Auftrag gewonnen."""
    content = content or GAME
    rules = offer_rules(content)
    task = inquiry_task(inquiry, markup, content)
    market = inquiry_task(dict(inquiry, einkaufspreis=inquiry.get("listenpreis",
                                                                  inquiry["einkaufspreis"])),
                          markup, content)
    payload = _judge_offer(state, task, inquiry, answer, content, market)
    won = payload["gewonnen"]
    satisfaction = rules["kundenzufriedenheit_gewonnen"] + \
        int(state.room_effect("kundenzufriedenheit_plus"))
    payload.update({"anfrage": inquiry["id"], "tag": inquiry["tag"],
                    "kunde": inquiry["kunde"]["id"], "artikel": inquiry["artikel"],
                    "menge": inquiry["menge"], "zuschlag": markup,
                    "geld": int(round(payload["gewinn"])) if won else 0,
                    "reputation": {"kundenzufriedenheit": satisfaction} if won else {}})
    return payload


def _judge_offer(state, task, offer, answer, content=None, market_task=None):
    """Gemeinsame Bewertung fuer Anfragen und Projekte: Rechnung richtig und
    Preis nicht hoeher als das guenstigste Angebot der Mitbewerber (plus
    Vorteil durch guten Ruf). market_task: dieselbe Rechnung zu Listenpreisen
    (die Mitbewerber haben kein eigenes Lager, ab 0.36)."""
    problems = form_problems(task, answer, content)
    numbers = {key: value for key, _label, value in offer_values(task["daten"])}
    cost = rival_cost = numbers["selbstkosten"]
    if market_task is not None:
        rival_cost = {key: value for key, _label, value in
                      offer_values(market_task["daten"])}["selbstkosten"]
    bids = [dict(bid, netto=_money(rival_cost * (1 + bid["zuschlag"] / 100.0)))
            for bid in offer.get("bieter") or []]
    market = _money(rival_cost * (1 + offer["markt"] / 100.0))
    advantage = offer_advantage(state, content)
    right = not problems
    cheap = numbers["netto"] <= _money(market * (1 + advantage / 100.0)) + 0.001
    won = right and cheap
    payload = {"zuschlag": task["daten"]["gewinn"], "antwort": dict(answer or {}),
               "richtig": right, "selbstkosten": cost, "netto": numbers["netto"],
               "gewinn": numbers["gewinn"],
               "marktpreis": market, "markt_zuschlag": offer["markt"],
               "laune": offer.get("laune", ""), "konkurrent": offer.get("konkurrent", ""),
               "bieter": bids, "ausgefallen": list(offer.get("ausgefallen") or []),
               "vorteil": advantage, "gewonnen": won,
               "grund": "" if won else ("rechenfehler" if not right else "preis")}
    if problems:
        payload["probleme"] = problems
    return payload


def offer_result_text(payload, content=None):
    """(Ueberschrift, Text) nach dem Abschicken eines Angebots (Anfrage oder
    Projekt). Aeltere Angebote aus 0.34 liefen nur gegen Bitweiche."""
    head, text = _offer_result_text(payload, content)
    rival = competitor(payload.get("konkurrent") or BITWEICHE, content)
    mood = competitor_mood(rival, payload.get("laune") or "", content)
    if mood:
        text += " " + mood["text"]
    for rival_id in payload.get("ausgefallen") or []:
        mood = competitor_mood(competitor(rival_id, content), "ausgelastet", content)
        if mood:
            text += " " + mood["text"]
    others = bidders_text(payload, content)
    if others:
        text += "\n\n" + others
    return head, text


def bidders_text(payload, content=None):
    """ "Mitgeboten haben: Bitweiche 2.410,00 € (12 %), CloudKontor Nord ..." """
    bids = sorted([bid for bid in payload.get("bieter") or [] if "netto" in bid],
                  key=lambda bid: bid["netto"])
    if len(bids) < 2:
        return ""
    return "Mitgeboten haben: %s." % ", ".join(
        "%s %s (%d %%)" % (competitor(bid["id"], content)["kurz"], _euro(bid["netto"]),
                           bid["zuschlag"]) for bid in bids)


def _offer_result_text(payload, content=None):
    if payload.get("projekt"):
        customer = {"name": payload.get("kunde_kurz") or "Der Kunde"}
        thing, won_head = "das Projekt", "Projekt gewonnen"
    else:
        customer = firm_customer(payload.get("kunde"), content) or {"name": "Der Kunde"}
        thing, won_head = "den Auftrag", "Auftrag gewonnen"
    rival = competitor(payload.get("konkurrent") or BITWEICHE, content)["kurz"]
    own = _euro(payload["netto"])
    market = _euro(payload["marktpreis"])
    if payload.get("gewonnen"):
        if payload.get("projekt"):
            text = ("%s gibt dir den Zuschlag. Du lagst netto bei %s, am günstigsten unter "
                    "den anderen war %s mit %s (Zuschlag %d %%). Anzahlung: +%s, "
                    "Material und Lizenzen: -%s. Stell jetzt ein Team zusammen." % (
                        customer["name"], own, rival, market, payload["markt_zuschlag"],
                        _whole_euro(payload.get("anzahlung", 0)),
                        _whole_euro(payload.get("material", 0))))
        else:
            text = ("%s nimmt dein Angebot an. Du lagst netto bei %s, %s bei %s "
                    "(Zuschlag %d %%). Gewinn für deine Firma: +%s." % (
                        customer["name"], own, rival, market, payload["markt_zuschlag"],
                        _whole_euro(payload["geld"])))
        if payload.get("vorteil") and payload["netto"] > payload["marktpreis"]:
            text += (" Knapp über %s, aber dein guter Ruf bei den Kunden hat "
                     "den Ausschlag gegeben." % rival)
        return won_head, text
    if payload.get("grund") == "rechenfehler":
        head = "%s verloren: Fehler im Angebot" % ("Projekt" if payload.get("projekt")
                                                   else "Auftrag")
        text = ("%s hat einen Fehler in deiner Kalkulation gefunden und gibt %s an "
                "%s (netto %s). Richtig gerechnet wären es mit %d %% Zuschlag "
                "netto %s gewesen." % (customer["name"], thing, rival, market,
                                       payload["zuschlag"], own))
        return head, text
    head = "%s an %s verloren" % ("Projekt" if payload.get("projekt") else "Auftrag", rival)
    text = ("Die Rechnung stimmt, aber %s war günstiger: netto %s (Zuschlag %d %%) "
            "gegen deine %s (Zuschlag %d %%)." % (rival, market, payload["markt_zuschlag"],
                                                  own, payload["zuschlag"]))
    if payload.get("vorteil"):
        text += " Selbst mit dem Bonus für deinen guten Ruf (%d %%) hat es nicht gereicht." \
            % payload["vorteil"]
    return head, text


def inquiry_status_text(inquiry):
    """Kurze Zeile zum Stand einer Anfrage."""
    result = inquiry.get("ergebnis")
    if not result:
        text = "Einkauf %s × %s · Lieferung in %d Arbeitstagen" % (
            inquiry["menge"], _euro(inquiry["einkaufspreis"]), inquiry["lieferzeit"])
        listed = inquiry.get("listenpreis", inquiry["einkaufspreis"])
        if listed > inquiry["einkaufspreis"]:
            text += " · Lager-Rabatt (sonst %s)" % _euro(listed)
        return text
    if result.get("gewonnen"):
        return "Gewonnen · Gewinn +%s" % _whole_euro(result.get("geld", 0))
    if result.get("grund") == "rechenfehler":
        return "Verloren · Fehler im Angebot"
    return "Verloren · %s war günstiger" % competitor(result.get("konkurrent") or BITWEICHE)["kurz"]


def ticket_limit(person, content=None):
    rules = ticket_rules(content)
    return int(rules["spieler_max"] if person == SELF else rules["mitarbeiter_max"])


def own_ticket_limit(state, content=None):
    """Kundentickets fuer die Spielfigur heute: einer weniger, wenn sie in
    einem Projekt mitarbeitet."""
    return max(1, ticket_limit(SELF, content) - (1 if state.project_of(SELF) else 0))


def ticket_chance(value, need, content=None):
    """Erfolgschance in Prozent (ganze Zahl)."""
    rule = ticket_rules(content)["chance"]
    chance = rule["basis"] + rule["je_punkt"] * (float(value) - need)
    return int(round(max(rule["min"], min(rule["max"], chance))))


def tickets_for_day(state, day, content=None):
    """Die Kundentickets eines Arbeitstags:
    [{"id", "vorlage", "titel", "text", "kunde" {...}, "cat", "stufe",
      "anforderung", "geld", "an" (Kennung oder None), "name", "chance",
      "ergebnis" (nach dem Feierabend)}]"""
    content = content or GAME
    if not state.firm:
        return []
    rules = ticket_rules(content)
    seed = state.firm_seed
    count = max(int(rules["mindestens"]),
                int(rules["grundzahl"]) + int(rules["je_mitarbeiter"]) * len(state.staff))
    order = sorted(rules["vorlagen"], key=lambda item: _dice(seed, day, "kt|" + item["id"]))
    chosen = order[:count]
    # Schon verteilte Tickets bleiben, auch wenn inzwischen jemand gegangen ist
    for item in order[count:]:
        if "%s%d:%s" % (TICKET_PREFIX, day, item["id"]) in state.delegations:
            chosen.append(item)
    result = []
    for item in chosen:
        ticket_id = "%s%d:%s" % (TICKET_PREFIX, day, item["id"])
        level = rules["stufen"][item["stufe"]]
        given = state.delegations.get(ticket_id) or {}
        result.append({"id": ticket_id, "vorlage": item["id"], "titel": item["titel"],
                       "text": item["text"], "kunde": firm_customer(item["kunde"], content),
                       "cat": item["cat"], "stufe": level["name"],
                       "anforderung": level["anforderung"], "geld": level["geld"],
                       "an": given.get("an"), "name": given.get("name"),
                       "chance": given.get("chance"),
                       "ergebnis": state.ticket_results.get(ticket_id)})
    return result


def ticket_candidates(state, ticket, levels, content=None):
    """Wer ein Kundenticket uebernehmen kann: [{"an", "name", "wert", "chance",
    "problem"}] - zuerst die Spielfigur (echter Wissensstand), dann die
    Mitarbeiter. problem ist leer, wenn die Person frei ist."""
    content = content or GAME
    cat = ticket["cat"]
    result = []
    own = int(round((levels or {}).get(cat, 0)))
    name = (state.profile or {}).get("name") or "Ich"
    limit = own_ticket_limit(state, content)
    problem = ""
    if len(state.delegated_to(SELF)) >= limit:
        problem = "Du hast heute schon %s übernommen." % (
            "ein Kundenticket" if limit == 1 else "%d Kundentickets" % limit)
        if state.project_of(SELF):
            problem += " Mehr geht nicht, weil du im Projekt mitarbeitest."
    result.append({"an": SELF, "name": "Ich selbst (%s)" % name, "wert": own,
                   "chance": ticket_chance(own, ticket["anforderung"], content),
                   "problem": problem})
    for item in state.staff_list():
        value = int(item["werte"].get(cat, 0))
        problem = ""
        if item.get("weiterbildung"):
            problem = "%s ist gerade in einer Weiterbildung." % item["name"]
        elif item.get("projekt"):
            problem = "%s arbeitet im Projekt „%s“ mit." % (
                item["name"], state.projects[item["projekt"]]["titel"])
        elif len(state.delegated_to(item["id"])) >= ticket_limit(item["id"], content):
            problem = "%s hat heute schon ein Kundenticket." % item["name"]
        result.append({"an": item["id"], "name": item["name"], "wert": value,
                       "chance": ticket_chance(value, ticket["anforderung"], content),
                       "problem": problem})
    return result


def ticket_outcomes(state, content=None):
    """Ergebnisse der heute verteilten Kundentickets fuer den Feierabend.
    Gewuerfelt wird fest aus Firma, Tag und Ticket - auf allen Geraeten gleich."""
    content = content or GAME
    rules = ticket_rules(content)
    result = []
    for ticket in state.customer_tickets():
        if not ticket.get("an") or ticket.get("ergebnis"):
            continue
        roll = _dice(state.firm_seed, state.day, "erfolg|" + ticket["id"])
        success = roll * 100 < ticket["chance"]
        rule = rules["erfolg"] if success else rules["fehlschlag"]
        result.append({"ticket": ticket["id"], "vorlage": ticket["vorlage"],
                       "titel": ticket["titel"], "kunde": ticket["kunde"]["name"],
                       "an": ticket["an"], "name": ticket["name"], "erfolg": success,
                       "geld": ticket["geld"] if success else 0,
                       "reputation": {key: value for key, value in rule.items() if value}})
    return result


def ticket_result_text(item):
    """ "Mira Kessler: Scanner an der Anmeldung installieren (Praxis Dr. Keller)
    erledigt, +60 €" """
    who = "Du" if item.get("an") == SELF else short_name({"name": item.get("name", "")})
    if item.get("erfolg"):
        return "%s: „%s“ für %s erledigt, +%s" % (who, item["titel"], item["kunde"],
                                                  _whole_euro(item.get("geld", 0)))
    return "%s: „%s“ für %s nicht geschafft, der Kunde ist unzufrieden" % (
        who, item["titel"], item["kunde"])


def ticket_line(ticket):
    """Zeile unter einem Kundenticket: Fachbereich, Schwierigkeit, Honorar."""
    text = "%s · %s · %s" % (CATEGORY_SHORT[CAT_NAME[ticket["cat"]]], ticket["stufe"],
                              _whole_euro(ticket["geld"]))
    if ticket.get("an"):
        who = "dir" if ticket["an"] == SELF else short_name({"name": ticket["name"]})
        text += " · übernommen von %s (Chance %d %%)" % (who, ticket["chance"])
    return text


def firm_orders_summary(state):
    """Eine Zeile fuer die Uebersicht: was heute noch zu tun ist."""
    inquiries = [item for item in state.inquiries() if not item.get("ergebnis")]
    tickets = [item for item in state.customer_tickets() if not item.get("an")]
    parts = []
    if inquiries:
        parts.append("1 Anfrage" if len(inquiries) == 1 else "%d Anfragen" % len(inquiries))
    if tickets:
        parts.append("1 Kundenticket" if len(tickets) == 1 else
                     "%d Kundentickets" % len(tickets))
    return "Heute offen: %s" % " und ".join(parts) if parts else ""


# -- Mitbewerber (ab 0.35) --------------------------------------------------
#
# Neben Bitweiche bieten fuenf weitere Firmen mit. Wer bei einer Anfrage oder
# einem Projekt mitbietet und mit welchem Zuschlag, wird wie alles andere fest
# gewuerfelt. Das guenstigste Angebot gewinnt.

BITWEICHE = "bitweiche"
_BITWEICHE_DEFAULT = {"id": BITWEICHE, "name": "Bitweiche IT-Service GmbH",
                      "kurz": "Bitweiche", "text": "", "kundenart": True,
                      "gewicht": {"anfrage": 1, "projekt": 1}}


def competitor_rules(content=None):
    return firm_rules(content).get("mitbewerber") or {}


def competitors(content=None):
    return list(competitor_rules(content).get("firmen") or [_BITWEICHE_DEFAULT])


def competitor(competitor_id, content=None):
    for item in competitors(content):
        if item["id"] == competitor_id:
            return item
    return dict(_BITWEICHE_DEFAULT) if competitor_id == BITWEICHE else \
        {"id": competitor_id, "name": competitor_id, "kurz": competitor_id}


def competitor_mood(rival, mood, content=None):
    """Laune einer Firma ("kampfpreis"/"ausgelastet") mit Text - bei Bitweiche
    aus angebote.laune (wie in 0.34)."""
    if not mood or not rival:
        return None
    moods = (offer_rules(content).get("laune") or {}) if rival.get("kundenart") \
        else (rival.get("laune") or {})
    return moods.get(mood)


def _weighted_order(items, weights, seed, day, salt):
    """Reihenfolge ohne Zuruecklegen, schwere Eintraege eher vorne."""
    keyed = []
    for item, weight in zip(items, weights):
        if weight <= 0:
            continue
        roll = max(1e-9, _dice(seed, day, salt + "|" + item["id"]))
        keyed.append((-math.log(roll) / weight, item))
    return [item for _key, item in sorted(keyed, key=lambda pair: pair[0])]


def _rival_markup(rival, rules, art, cat, seed, day, salt):
    """(Zuschlag, Laune) einer Firma - None, wenn sie gar nicht bietet."""
    if rival.get("kundenart"):
        # Bitweiche wie in 0.34 (gleiche Wuerfel, damit nichts springt)
        return _market_markup(rules, rules["arten"][art], seed, day, salt)
    salt = "%s%s-" % (salt, rival["id"])
    low, high = int(rival.get("von", 5)), int(rival.get("bis", 25))
    if rival.get("gleichmaessig"):
        middle = _dice(seed, day, salt + "markt")
    else:
        middle = (_dice(seed, day, salt + "markt") + _dice(seed, day, salt + "markt2")) / 2.0
    markup = low + min(high - low, int(middle * (high - low + 1)))
    if cat:
        markup += int((rival.get("fach") or {}).get(cat, 0))
    moods = rival.get("laune") or {}
    roll = _dice(seed, day, salt + "laune")
    fight, busy = moods.get("kampfpreis"), moods.get("ausgelastet")
    if fight and roll < fight["chance"]:
        return _between(seed, day, salt + "kampf", fight["von"], fight["bis"]), "kampfpreis"
    if busy and roll > 1 - busy["chance"]:
        if busy.get("bietet_nicht"):
            return None
        markup += _between(seed, day, salt + "teuer", busy.get("plus_von", 10),
                           busy.get("plus_bis", 20))
        return max(0, markup), "ausgelastet"
    return max(0, markup), ""


def competitor_bids(kind, art, cat, seed, day, salt, content=None):
    """Wer mitbietet: ([{"id", "zuschlag", "laune"}], [ausgefallene ids]).
    kind ist "anfrage" oder "projekt"."""
    content = content or GAME
    rules = offer_rules(content)
    setup = competitor_rules(content)
    rivals = competitors(content)
    if kind == "projekt":
        span = setup.get("projekt_bieter") or {"von": 2, "bis": 3}
        count = _between(seed, day, salt + "bieterzahl", span["von"], span["bis"])
    else:
        single = (setup.get("anfrage_bieter") or {}).get("eins", 1.0)
        count = 1 if _dice(seed, day, salt + "bieterzahl") < single else 2
    order = _weighted_order(rivals, [(item.get("gewicht") or {}).get(kind, 1)
                                     for item in rivals], seed, day, salt + "bieter")
    bids, absent = [], []
    for rival in order[:max(1, count)]:
        result = _rival_markup(rival, rules, art, cat, seed, day, salt)
        if result is None:
            absent.append(rival["id"])
            continue
        bids.append({"id": rival["id"], "zuschlag": int(result[0]), "laune": result[1]})
    if not bids:
        # Niemand da? Bitweiche bietet immer
        rival = competitor(BITWEICHE, content)
        markup, mood = _rival_markup(rival, rules, art, cat, seed, day, salt)
        bids.append({"id": BITWEICHE, "zuschlag": int(markup), "laune": mood})
    return bids, absent


def lost_to(state, content=None):
    """Gegen wen Angebote verloren gingen: [(name, anzahl)], meiste zuerst."""
    counts = {}
    for item in list(state.offers.values()) + list(state.project_offers.values()):
        if item.get("gewonnen"):
            continue
        rival = item.get("konkurrent") or BITWEICHE
        counts[rival] = counts.get(rival, 0) + 1
    order = [item["id"] for item in competitors(content)]
    return [(competitor(rival, content)["name"], number) for rival, number in
            sorted(counts.items(), key=lambda pair: (-pair[1], order.index(pair[0])
                                                    if pair[0] in order else 99))]


# -- Kundenprojekte (ab 0.35) -----------------------------------------------
#
# Die 50 Testprojekte aus dem Lernbereich kommen als Ausschreibungen. Wie bei
# den Anfragen gibt man ein Angebot ab und bietet gegen die Mitbewerber. Ein
# gewonnenes Projekt arbeitet ein Team ueber mehrere Arbeitstage ab.

def project_rules(content=None):
    return firm_rules(content).get("projekte") or {}


def project_limit(state, content=None):
    """Wie viele Projekte gleichzeitig laufen koennen (je Gebaeudestufe)."""
    table = project_rules(content).get("laufend") or {"1": 1}
    number = state.firm["stufe"] if state.firm else 1
    best = 1
    for key, value in table.items():
        if int(key) <= number:
            best = max(best, int(value))
    # Eigener Serverraum (ab 0.36): ein Projekt mehr
    return best + int(state.room_effect("projekte_plus"))


def customer_short(branche):
    """Kurzer Kundenname aus der Branche des Testprojekts: der Name in
    Klammern ("ModeWelt GmbH") oder die Branche bis zum ersten Komma."""
    if "(" in branche and ")" in branche:
        inner = branche[branche.index("(") + 1:branche.index(")")].split(",")[0].strip()
        if inner and inner[0].isupper():
            return inner
    return branche.split(",")[0].split(" mit ")[0].strip()


def project_for_slot(state, slot, content=None):
    """Die Ausschreibung Nummer slot (0, 1, 2 ...) seit der Gruendung."""
    content = content or GAME
    rules = project_rules(content)
    templates = content.get("projektarbeiten") or []
    seed = state.firm_seed
    order = sorted(range(len(templates)), key=lambda index: _dice(seed, 0, "projekt|%d"
                                                                  % index))
    index = order[slot % len(order)]
    template = templates[index]
    level = rules["stufen"][template["schwierigkeit"]]
    start = int(state.firm["tag"]) + slot * int(rules["abstand_tage"])
    salt = "projekt%d-" % slot
    low, high = level["material"]
    material = int(round((low + _dice(seed, start, salt + "material") * (high - low)) / 10.0)
                   * 10)
    cat = CAT_KEY.get(template["cat"], template["cat"])
    bids, absent = competitor_bids("projekt", "normal", cat, seed, start, salt, content)
    cheapest = min(bids, key=lambda bid: bid["zuschlag"])
    project_id = "%s%d" % (PROJECT_PREFIX, slot + 1)
    customer = customer_short(template["branche"])
    text = _pick(rules["texte"], seed, start, salt + "text").format(
        kunde=customer, auftrag=template["auftrag"])
    return {"id": project_id, "slot": slot, "vorlage": index, "folge": slot // len(order),
            "titel": template["title"], "kunde": template["branche"],
            "kunde_kurz": customer, "cat": cat,
            "schwierigkeit": template["schwierigkeit"], "aufwand": int(level["aufwand"]),
            "anforderung": int(level["anforderung"]),
            # Mit eigenem Lager ist das Material guenstiger (ab 0.36)
            "material": discounted(material, state.room_effect("material_rabatt")),
            "material_markt": material,
            "frist": int(level["frist"]), "von_tag": start,
            "bis_tag": start + int(rules["gilt_tage"]) - 1,
            "markt": cheapest["zuschlag"], "laune": cheapest["laune"],
            "konkurrent": cheapest["id"], "bieter": bids, "ausgefallen": absent,
            "text": text, "ausgangssituation": template["ausgangssituation"],
            "auftrag": template["auftrag"],
            "rahmenbedingungen": list(template.get("rahmenbedingungen") or []),
            "ergebnis": state.project_offers.get(project_id)}


def project_tenders(state, day, content=None):
    """Ausschreibungen, die an einem Arbeitstag vorliegen."""
    content = content or GAME
    if not state.firm or not content.get("projektarbeiten") or not project_rules(content):
        return []
    rules = project_rules(content)
    gap, valid = int(rules["abstand_tage"]), int(rules["gilt_tage"])
    since = day - int(state.firm["tag"])
    if since < 0:
        return []
    first = max(0, (since - valid) // gap)
    result = []
    for slot in range(first, since // gap + 1):
        item = project_for_slot(state, slot, content)
        if item["von_tag"] <= day <= item["bis_tag"]:
            result.append(item)
    return result[-int(rules.get("max_offen", 2)):]


def project_task(project, markup, content=None):
    """Das Projekt als Formular-Aufgabe (Zuschlagskalkulation mit zwei
    Positionen: Projektarbeit und Material)."""
    rules = project_rules(content)
    offers = offer_rules(content)
    return {"id": project["id"], "typ": "formular", "art": "angebot",
            "titel": "Angebot für „%s“" % project["titel"],
            "ticket": [project["text"]],
            "frage": "Wähle deinen Gewinnzuschlag und rechne das Angebot durch.",
            "daten": {"positionen": [
                {"text": "Projektarbeit", "menge": project["aufwand"], "einheit": "Punkte",
                 "preis": rules["stundensatz"]},
                {"text": "Material und Lizenzen", "menge": 1, "preis": project["material"]}],
                "einkauf_name": "Einzelkosten gesamt",
                "handlungskosten": offers["handlungskosten"], "gewinn": markup,
                "ust": offers["ust"]},
            "hilfe": list(rules.get("hilfe") or [])}


def project_offer_problem(state, content=None):
    """Warum man gerade auf kein Projekt bieten kann (leer = geht)."""
    limit = project_limit(state, content)
    if len(state.running_projects()) >= limit:
        return ("Deine Firma schafft höchstens %s gleichzeitig. Bring zuerst ein "
                "laufendes Projekt zu Ende." % ("1 Projekt" if limit == 1 else
                                              "%d Projekte" % limit))
    return ""


def project_offer_result(state, project, markup, answer, day, content=None):
    """Bewertet ein Projektangebot wie eine Anfrage. Gewonnen: Anzahlung
    kommt, Material wird sofort bezahlt."""
    content = content or GAME
    rules = project_rules(content)
    task = project_task(project, markup, content)
    market = project_task(dict(project, material=project.get("material_markt",
                                                             project["material"])),
                          markup, content)
    payload = _judge_offer(state, task, project, answer, content, market)
    won = payload["gewonnen"]
    down = int(round(payload["netto"] * rules["anzahlung"] / 100.0)) if won else 0
    payload.update({"projekt": project["id"], "vorlage": project["vorlage"],
                    "folge": project["folge"], "titel": project["titel"],
                    "kunde": project["kunde"], "kunde_kurz": project["kunde_kurz"],
                    "cat": project["cat"], "schwierigkeit": project["schwierigkeit"],
                    "tag": day, "aufwand": project["aufwand"],
                    "anforderung": project["anforderung"],
                    "material": project["material"] if won else 0,
                    "anzahlung": down, "frist": project["frist"],
                    "frist_tag": day + project["frist"] - 1,
                    "geld": down - project["material"] if won else 0})
    return payload


def project_points(value, content=None):
    """Tagesleistung einer Person im Projekt (Punkte, eine Nachkommastelle)."""
    rule = project_rules(content).get("leistung") or {"basis": 2, "je_punkt": 0.1}
    return round(rule["basis"] + rule["je_punkt"] * float(value), 1)


def project_value(state, person, cat, levels):
    """Wert einer Person im Fachbereich (Spielfigur: echter Wissensstand)."""
    if person == SELF:
        return int(round((levels or {}).get(cat, 0)))
    return int(state.staff_values(person).get(cat, 0))


def person_name(state, person):
    if person == SELF:
        return "Ich selbst (%s)" % ((state.profile or {}).get("name") or "Ich")
    return (state.staff.get(person) or {}).get("name", person)


def project_candidates(state, project, levels, content=None):
    """Wer im Projektteam mitarbeiten kann: [{"an", "name", "wert", "punkte",
    "im_team", "problem"}] - zuerst die Spielfigur, dann die Mitarbeiter."""
    content = content or GAME
    cat = project["cat"]
    result = []
    own_tickets = len(state.delegated_to(SELF))
    elsewhere = state.project_of(SELF)
    problem = ""
    if elsewhere and elsewhere != project["projekt"]:
        problem = "Du arbeitest schon im Projekt „%s“ mit." % state.projects[elsewhere]["titel"]
    elif SELF not in project["team"] and own_tickets >= ticket_limit(SELF, content):
        problem = "Du hast heute schon %d Kundentickets übernommen." % own_tickets
    value = project_value(state, SELF, cat, levels)
    result.append({"an": SELF, "name": person_name(state, SELF), "wert": value,
                   "punkte": project_points(value, content),
                   "im_team": SELF in project["team"], "problem": problem})
    for item in state.staff_list():
        value = int(item["werte"].get(cat, 0))
        problem = ""
        if item.get("weiterbildung"):
            problem = "%s ist gerade in einer Weiterbildung." % item["name"]
        elif item.get("projekt") and item["projekt"] != project["projekt"]:
            problem = "%s arbeitet schon im Projekt „%s“ mit." % (
                item["name"], state.projects[item["projekt"]]["titel"])
        elif item["id"] not in project["team"] and state.delegated_to(item["id"]):
            problem = "%s hat heute schon ein Kundenticket." % item["name"]
        result.append({"an": item["id"], "name": item["name"], "wert": value,
                       "punkte": project_points(value, content),
                       "im_team": item["id"] in project["team"], "problem": problem})
    return result


def project_team_points(state, project, levels, content=None):
    """Punkte, die das Team an einem Arbeitstag schafft (ohne Zufall)."""
    total = 0.0
    for person in project["team"]:
        if person != SELF and (person not in state.staff or state.training_of(person)):
            continue
        total += project_points(project_value(state, person, project["cat"], levels), content)
    return round(total, 1)


def project_phases(project, content=None):
    """[(name, fertig, aktuell)] der fuenf Phasen je Fachbereich."""
    names = (project_rules(content).get("phasen") or {}).get(project["cat"]) or \
        ["Planung", "Umsetzung", "Abschluss"]
    share = min(1.0, project["stand"] / float(project["aufwand"])) if project["aufwand"] else 1
    done = len(names) if project.get("fertig") or share >= 1 else int(share * len(names))
    return [(name, index < done, index == done) for index, name in enumerate(names)]


def project_phase_text(project, content=None):
    """ "Erledigt: Ist-Analyse, Planung · Jetzt: Beschaffung · Danach: ..." """
    phases = project_phases(project, content)
    parts = []
    done = [name for name, finished, _now in phases if finished]
    now = [name for name, _finished, current in phases if current]
    later = [name for name, finished, current in phases if not finished and not current]
    if done:
        parts.append("Erledigt: " + ", ".join(done))
    if now:
        parts.append("Jetzt: " + now[0])
    if later:
        parts.append("Danach: " + ", ".join(later))
    return " · ".join(parts)


def project_phase_name(project, content=None):
    current = [name for name, _done, now in project_phases(project, content) if now]
    return current[0] if current else project_phases(project, content)[-1][0]


def project_status_text(state, project, levels=None, content=None):
    """ "Tag 2 von 5 · 21 von 35 Punkten · schafft heute etwa 12 Punkte" """
    day = state.day - int(project["tag"]) + 1
    text = "Tag %d von %d · %s von %d Punkten" % (
        day, project["frist"], _num(round(project["stand"], 1)), project["aufwand"])
    if day > project["frist"]:
        text = "Frist überschritten (%d von %d Tagen) · %s von %d Punkten" % (
            day, project["frist"], _num(round(project["stand"], 1)), project["aufwand"])
    if not project["team"]:
        return text + " · noch kein Team"
    if levels is not None:
        points = project_team_points(state, project, levels, content)
        if points > 0:
            left = max(0.0, project["aufwand"] - project["stand"])
            days = int(math.ceil(left / points)) if points else 0
            text += " · Team schafft etwa %s Punkte am Tag, %s" % (
                _num(points), "heute fertig" if days <= 1 else
                "noch etwa %d Arbeitstage" % days)
    return text


def project_team_text(state, project):
    if not project["team"]:
        return "Noch kein Team"
    names = ["du" if person == SELF else short_name({"name": person_name(state, person)})
             for person in project["team"]]
    return "Team: " + ", ".join(names)


def project_outcomes(state, levels, learned, content=None):
    """Ergebnisse der Projekt-Arbeitstage fuer den Feierabend. learned ist
    die Menge der im Lernbereich bearbeiteten Testprojekte (Nummern)."""
    content = content or GAME
    rules = project_rules(content)
    result = []
    for project in state.running_projects():
        if (project["projekt"], state.day) in state.project_days or not project["team"]:
            continue
        shares = []
        best = 0
        for person in project["team"]:
            if person != SELF and (person not in state.staff or state.training_of(person)):
                continue
            value = project_value(state, person, project["cat"], levels)
            best = max(best, value)
            shares.append({"an": person, "name": person_name(state, person),
                           "punkte": project_points(value, content)})
        if not shares:
            continue
        factor = 1.0
        setback = ""
        bonus = project.get("vorlage") in (learned or set())
        if bonus:
            factor *= 1 + rules.get("lernbonus", 0) / 100.0
        rule = rules.get("rueckschlag") or {}
        # Eigener Serverraum (ab 0.36): seltener Rueckschlaege
        chance = rule.get("chance", 0) * state.room_effect("rueckschlag_faktor", 1.0)
        if best < project["anforderung"] and \
                _dice(state.firm_seed, state.day, "rueck|" + project["projekt"]) < chance:
            factor *= rule.get("faktor", 0.5)
            texts = (rules.get("rueckschlaege") or {}).get(project["cat"]) or \
                ["Es gab Probleme, heute ging es nur langsam voran."]
            setback = _pick(texts, state.firm_seed, state.day, "rueck-text|" +
                            project["projekt"])
        points = round(sum(item["punkte"] for item in shares) * factor, 1)
        stand = min(float(project["aufwand"]), project["stand"] + points)
        item = {"projekt": project["projekt"], "titel": project["titel"],
                "kunde": project.get("kunde_kurz", ""), "tag": state.day,
                "beitraege": shares, "rueckschlag": setback, "lernbonus": bonus,
                "punkte": points, "stand": round(stand, 1), "aufwand": project["aufwand"],
                "fertig": stand >= project["aufwand"] - 0.001, "geld": 0, "verzug": 0,
                "abzug": 0, "reputation": {}}
        if item["fertig"]:
            late = max(0, state.day - int(project["frist_tag"]))
            delay = rules.get("verzug") or {}
            cut = min(int(delay.get("max_prozent", 30)),
                      late * int(delay.get("prozent_je_tag", 5)))
            rest = project["netto"] - project["anzahlung"] - project["netto"] * cut / 100.0
            item.update({"verzug": late, "abzug": cut, "geld": int(round(rest))})
            if late:
                item["reputation"] = {"kundenzufriedenheit": max(
                    -20, late * int(delay.get("kundenzufriedenheit_je_tag", -2)))}
            else:
                item["reputation"] = {key: value for key, value in
                                      (rules.get("puenktlich") or {}).items() if value}
        result.append(item)
    return result


def project_day_text(item):
    """Zeile fuer den Feierabend zu einem Projekt-Arbeitstag."""
    text = "„%s“: +%s Punkte, jetzt %s von %d" % (item["titel"], _num(item["punkte"]),
                                                 _num(item["stand"]), item["aufwand"])
    if item.get("lernbonus"):
        text += " (mit Lernbonus)"
    if item.get("rueckschlag"):
        text += ". Rückschlag: %s" % item["rueckschlag"]
    if item.get("fertig"):
        if item.get("verzug"):
            text += ". Fertig, aber %d %s zu spät: Restzahlung +%s (%d %% Abzug)" % (
                item["verzug"], "Tag" if item["verzug"] == 1 else "Tage",
                _whole_euro(item["geld"]), item["abzug"])
        else:
            text += ". Pünktlich fertig! Restzahlung +%s" % _whole_euro(item["geld"])
    return text


def tender_line(project):
    """Zeile unter einer Ausschreibung."""
    return "%s · %s · %d Punkte Aufwand · Frist %d Arbeitstage" % (
        CATEGORY_SHORT[CAT_NAME[project["cat"]]], project["schwierigkeit"],
        project["aufwand"], project["frist"])


def tender_status_text(state, project):
    """Stand einer Ausschreibung: noch offen (bis wann) oder Ergebnis."""
    result = project.get("ergebnis")
    if not result:
        left = project["bis_tag"] - state.day
        return "Angebot möglich %s" % ("nur noch heute" if left <= 0 else
                                       "noch %d Arbeitstage" % (left + 1))
    if result.get("gewonnen"):
        return "Gewonnen · läuft unter „Laufende Projekte“"
    if result.get("grund") == "rechenfehler":
        return "Verloren · Fehler im Angebot"
    return "Verloren · %s war günstiger" % competitor(result.get("konkurrent")
                                                     or BITWEICHE)["kurz"]


def project_office_text(state, project, content=None):
    """Satz eines Mitarbeiters im Buero, der im Projekt mitarbeitet."""
    texts = project_rules(content).get("buero") or ["Ich arbeite am Projekt „{titel}“."]
    return _pick(texts, state.firm_seed, state.day, "buero|" + project["projekt"]).format(
        phase=project_phase_name(project, content), titel=project["titel"],
        kunde=project.get("kunde_kurz", ""))


def projects_summary(state):
    """Zeile fuer die Uebersicht: laufende Projekte und offene Ausschreibungen."""
    parts = []
    running = state.running_projects()
    if running:
        without = [item for item in running if not item["team"]]
        parts.append("%s läuft" % ("1 Projekt" if len(running) == 1 else
                                   "%d Projekte" % len(running)))
        if without:
            parts[-1] += " (%s ohne Team)" % ("eins" if len(without) == 1 else
                                              "%d" % len(without))
    tenders = [item for item in state.tenders() if not item.get("ergebnis")]
    if tenders:
        parts.append("1 Ausschreibung" if len(tenders) == 1 else
                     "%d Ausschreibungen" % len(tenders))
    return "Projekte: %s" % " · ".join(parts) if parts else ""


def _validate_orders(rules):
    """firma.json ab 0.34: Kunden, Anfragen und Kundentickets."""
    problems = []
    for key in ("kunden", "angebote", "tickets"):
        if key not in rules:
            problems.append("Spiel-Firma: Abschnitt '%s' fehlt" % key)
    if problems:
        return problems
    offers, tickets = rules["angebote"], rules["tickets"]
    customers = {}
    for item in rules["kunden"]:
        if item.get("id") in customers:
            problems.append("Spiel-Firma: Kunde '%s' doppelt" % item.get("id"))
        customers[item.get("id")] = item
        if item.get("art") not in offers.get("arten", {}):
            problems.append("Spiel-Firma: Kunde '%s' hat eine unbekannte Art" % item.get("id"))
        for key in ("name", "kontakt", "satz"):
            if not item.get(key):
                problems.append("Spiel-Firma: Kunde '%s' ohne %s" % (item.get("id"), key))
    if len(customers) < 3:
        problems.append("Spiel-Firma: zu wenige Kunden")
    for key, kind in offers.get("arten", {}).items():
        if not 0 <= kind["von"] <= kind["bis"] <= 100:
            problems.append("Spiel-Firma: Spanne der Kundenart '%s' ungueltig" % key)
    for key, mood in (offers.get("laune") or {}).items():
        if not 0 <= mood.get("chance", 0) <= 0.5 or not mood.get("text"):
            problems.append("Spiel-Firma: Laune '%s' ungueltig" % key)
    markups = offers.get("zuschlaege") or []
    if not markups or any(not 0 <= value <= 100 for value in markups):
        problems.append("Spiel-Firma: Gewinnzuschlaege fehlen oder sind ungueltig")
    if not offers.get("artikel"):
        problems.append("Spiel-Firma: keine Artikel fuer Anfragen")
    for item in offers.get("artikel") or []:
        low, high = item["preis"]
        few, many = item["menge"]
        if not 0 < low <= high or not 0 < few <= many:
            problems.append("Spiel-Firma: Artikel '%s' mit ungueltiger Spanne" % item["name"])
    for text in offers.get("texte") or []:
        try:
            text.format(kontakt="", menge=1, artikel="", lieferzeit=1)
        except (KeyError, IndexError, ValueError):
            problems.append("Spiel-Firma: Anfragetext mit unbekanntem Platzhalter")
    if not offers.get("texte"):
        problems.append("Spiel-Firma: keine Anfragetexte")
    seen = set()
    for item in tickets.get("vorlagen") or []:
        where = "Spiel-Firma Kundenticket '%s'" % item.get("id")
        if item.get("id") in seen:
            problems.append("%s: doppelt" % where)
        seen.add(item.get("id"))
        if item.get("cat") not in CAT_ORDER:
            problems.append("%s: unbekannter Fachbereich" % where)
        if item.get("stufe") not in tickets.get("stufen", {}):
            problems.append("%s: unbekannte Schwierigkeit" % where)
        if item.get("kunde") not in customers:
            problems.append("%s: unbekannter Kunde" % where)
        if not item.get("titel") or len(item.get("text", "")) > MAX_TICKET_CHARS:
            problems.append("%s: Titel fehlt oder Text zu lang" % where)
    need = max(int(tickets.get("mindestens", 0)), int(tickets.get("grundzahl", 0)) +
               int(tickets.get("je_mitarbeiter", 0)) * 10)
    if len(seen) < need:
        problems.append("Spiel-Firma: zu wenige Kundentickets (mindestens %d)" % need)
    return problems


def _validate_projects(rules, content):
    """firma.json ab 0.35: Mitbewerber und Kundenprojekte."""
    problems = []
    for key in ("mitbewerber", "projekte"):
        if key not in rules:
            problems.append("Spiel-Firma: Abschnitt '%s' fehlt" % key)
    if problems:
        return problems
    rivals = rules["mitbewerber"].get("firmen") or []
    ids = [item.get("id") for item in rivals]
    if len(set(ids)) != len(ids) or BITWEICHE not in ids:
        problems.append("Spiel-Firma: Mitbewerber doppelt oder Bitweiche fehlt")
    for item in rivals:
        where = "Spiel-Firma Mitbewerber '%s'" % item.get("id")
        for key in ("name", "kurz", "text"):
            if not item.get(key):
                problems.append("%s: %s fehlt" % (where, key))
        if not item.get("kundenart") and not 0 <= item.get("von", -1) <= item.get("bis", -1) \
                <= 100:
            problems.append("%s: Spanne ungueltig" % where)
        for cat in item.get("fach") or {}:
            if cat not in CAT_ORDER:
                problems.append("%s: unbekannter Fachbereich '%s'" % (where, cat))
        for key, mood in (item.get("laune") or {}).items():
            if not 0 <= mood.get("chance", 0) <= 0.5 or not mood.get("text"):
                problems.append("%s: Laune '%s' ungueltig" % (where, key))
        weights = item.get("gewicht") or {}
        if weights.get("anfrage", 0) <= 0 and weights.get("projekt", 0) <= 0:
            problems.append("%s: bietet nie mit" % where)
    span = rules["mitbewerber"].get("projekt_bieter") or {}
    if not 1 <= span.get("von", 0) <= span.get("bis", 0) <= len(rivals):
        problems.append("Spiel-Firma: projekt_bieter ungueltig")
    projects = rules["projekte"]
    for key in ("abstand_tage", "gilt_tage", "stundensatz", "anzahlung", "stufen", "phasen",
                "rueckschlaege", "texte", "buero"):
        if key not in projects:
            problems.append("Spiel-Firma: projekte.%s fehlt" % key)
    if problems:
        return problems
    for template in content.get("projektarbeiten") or []:
        if template.get("schwierigkeit") not in projects["stufen"]:
            problems.append("Spiel-Firma: keine Projektstufe fuer '%s'"
                            % template.get("schwierigkeit"))
        cat = CAT_KEY.get(template.get("cat"))
        if len(projects["phasen"].get(cat) or []) < 2 or \
                not projects["rueckschlaege"].get(cat):
            problems.append("Spiel-Firma: Phasen oder Rueckschlaege fuer '%s' fehlen"
                            % template.get("cat"))
    for key, level in projects["stufen"].items():
        low, high = level["material"]
        if not 0 < level["aufwand"] or not 0 <= low <= high or level["frist"] < 1:
            problems.append("Spiel-Firma: Projektstufe '%s' ungueltig" % key)
    for text in projects["texte"]:
        try:
            text.format(kunde="", auftrag="")
        except (KeyError, IndexError, ValueError):
            problems.append("Spiel-Firma: Ausschreibungstext mit unbekanntem Platzhalter")
    for text in projects["buero"]:
        try:
            text.format(phase="", titel="", kunde="")
        except (KeyError, IndexError, ValueError):
            problems.append("Spiel-Firma: Buerosatz mit unbekanntem Platzhalter")
    if projects["gilt_tage"] < projects["abstand_tage"]:
        problems.append("Spiel-Firma: Ausschreibungen gelten kuerzer als ihr Abstand")
    return problems


ROOM_EFFECTS = ("material_rabatt", "anfragen_plus", "kundenzufriedenheit_plus",
                "projekte_plus", "rueckschlag_faktor", "weiterbildung_rabatt",
                "weiterbildung_tage_minus")


def _validate_rooms(rules):
    """firma.json "sonderraeume" (ab 0.36): jeder Raum liegt ab seiner Stufe
    im Grundriss, ohne Arbeitsplaetze darin, mit bekannten Vorteilen."""
    problems = []
    setup = rules.get("sonderraeume")
    if not setup:
        return problems
    stages = rules["gebaeude"].get("stufen") or []
    ids = [item.get("id") for item in setup.get("raeume") or []]
    if len(ids) != len(set(ids)):
        problems.append("Spiel-Firma: Sonderraum-Kennungen sind nicht eindeutig")
    for item in setup.get("raeume") or []:
        where = "Spiel-Firma Sonderraum %s" % item.get("id")
        for key in ("name", "raum", "vorteil"):
            if not item.get(key):
                problems.append("%s: '%s' fehlt" % (where, key))
        number = item.get("ab_stufe")
        if not isinstance(number, int) or not 1 <= number <= len(stages):
            problems.append("%s: ab_stufe ungueltig" % where)
            continue
        if not isinstance(item.get("preis"), int) or item["preis"] <= 0 or \
                not isinstance(item.get("nebenkosten"), int) or item["nebenkosten"] < 0:
            problems.append("%s: Preis oder Nebenkosten ungueltig" % where)
        for stage in stages[number - 1:]:
            if item["raum"] not in {room_["id"] for room_ in stage["gebaeude"]["raeume"]}:
                problems.append("%s: Flaeche '%s' fehlt in Stufe %d"
                                % (where, item["raum"], stage["stufe"]))
            if any(room_id == item["raum"] for _x, _y, room_id in stage.get("plaetze") or []):
                problems.append("%s: Arbeitsplatz in der Flaeche" % where)
        for key, value in (item.get("effekt") or {}).items():
            if key not in ROOM_EFFECTS or not isinstance(value, (int, float)):
                problems.append("%s: unbekannter Vorteil '%s'" % (where, key))
        if not item.get("effekt"):
            problems.append("%s: kein Vorteil" % where)
    return problems


def _validate_firm(content):
    """firma.json: Gebaeudestufen mit Arbeitsplaetzen, Formeln, Wechsel."""
    problems = []
    rules = content.get("firma") or {}
    if not rules:
        return ["Spiel: firma.json fehlt"]
    for key in ("gruendung", "gebaeude", "bewerbung", "gehalt", "umsatz", "weiterbildung",
                "namen", "macken"):
        if key not in rules:
            problems.append("Spiel-Firma: Abschnitt '%s' fehlt" % key)
    if problems:
        return problems
    stages = rules["gebaeude"].get("stufen") or []
    if not stages:
        problems.append("Spiel-Firma: keine Gebaeudestufen")
    capacity = 0
    for number, stage in enumerate(stages, 1):
        where = "Spiel-Firma Stufe %d" % number
        if stage.get("stufe") != number:
            problems.append("%s: falsche Nummer" % where)
        if number == 1 and stage.get("preis", 0):
            problems.append("%s: die Startstufe kostet nichts extra" % where)
        places = stage.get("plaetze") or []
        if len(places) <= capacity:
            problems.append("%s: bringt keine zusaetzlichen Arbeitsplaetze" % where)
        capacity = len(places)
        people = [{"id": "platz%d" % index, "raum": room_id, "platz": [x, y]}
                  for index, (x, y, room_id) in enumerate(places)]
        problems += _validate_building(stage["gebaeude"], where, people)
        free = _base_grid(stage["gebaeude"])
        for x, y, _room in places:
            if _cell(x, y) not in free:
                problems.append("%s: Arbeitsplatz %.1f/%.1f ist verstellt" % (where, x, y))
    for key in ("vornamen", "nachnamen"):
        if len(rules["namen"].get(key) or []) < 5:
            problems.append("Spiel-Firma: zu wenige %s" % key)
    rule = rules["bewerbung"]
    if not 0 <= rule["werte_min"] <= rule["werte_max"] <= 90:
        problems.append("Spiel-Firma: Wertebereich der Bewerber ungueltig")
    problems += _validate_orders(rules)
    problems += _validate_projects(rules, content)
    problems += _validate_rooms(rules)
    ids = {person["id"] for person in content["kollegen"]}
    for item in rules.get("wechsel", []):
        if item.get("kollege") not in ids:
            problems.append("Spiel-Firma: Wechsel von unbekannter Person '%s'"
                            % item.get("kollege"))
        if set(item.get("werte", {})) != set(CAT_ORDER):
            problems.append("Spiel-Firma: Wechsel %s braucht Werte fuer alle Fachbereiche"
                            % item.get("kollege"))
    return problems


# ============================================================================
#  GRUNDRISS
# ============================================================================
#
# Das Buerogebaeude wird als Liste einfacher Zeichenbefehle in Grundriss-
# Einheiten beschrieben (building_shapes). PC (Tk-Canvas) und Handy (Flet-
# Canvas) muessen sie nur noch skalieren und zeichnen - so sehen beide
# Gebaeude gleich aus und Aenderungen passieren nur an einer Stelle.
#
# Befehle (Woerterbuecher, Schluessel "k"):
#   rect  x, y, w, h, fill, line, lw, r   (r = Eckenradius)
#   oval  x, y, w, h, fill, line, lw
#   line  pts [x1, y1, x2, y2], color, lw
#   arc   x, y, w, h (umgebendes Rechteck), start, extent (Grad, im
#         Uhrzeigersinn ab 3 Uhr wie auf dem Bildschirm), color, lw
#   text  x, y, text, kurz, role, color, anchor ("w" oder "c"), maxw und
#         optional bg/border (Schild hinter dem Text, Groesse nach Textbreite)
# Linienstaerken (lw, r) sind ebenfalls Grundriss-Einheiten. role ist
# "raum", "person" oder "badge" - die Schriftgroesse waehlt die Oberflaeche.

# Rand um das Gebaeude, damit die Aussenwand nicht abgeschnitten wird
PLAN_MARGIN = 0.4

WALL = "#B7A6DD"
WALL_INNER = 0.16
WALL_OUTER = "#D9CCF5"
WINDOW = "#7FE3F5"
WOOD = "#9A6B45"
WOOD_DARK = "#6E4A2F"
METAL = "#8E8AA3"
METAL_DARK = "#4A4560"
SCREEN = "#16122A"
PLANT = "#34D399"
PLANT_DARK = "#159A6C"
POT = "#B7643A"
CARDBOARD = "#C79A62"
CHAIR = "#3A2A5C"
PAPER = "#F4F1FA"


def room_color(item):
    """Farbe eines Raums: je Fachbereich ("cat") oder frei ("farbe", z.B. in
    der Wohnung)."""
    if item.get("farbe"):
        return item["farbe"]
    return CATEGORY_COLOR[CAT_NAME[item["cat"]]]


def door_side(item, content=None):
    """Wand mit der Tuer: "s" (unten, Raeume oberhalb des Flurs), "n" (oben,
    Raeume unterhalb) oder per "seite" gesetzt "w"/"o" (links/rechts, z.B.
    der Lagerfluegel am Ende des Flurs). Bei "w"/"o" sind von/bis y-Werte."""
    door = item.get("tuer") or {}
    if door.get("seite"):
        return door["seite"]
    hall = (content or GAME)["gebaeude"]["flur"]
    return "s" if item["y"] + item["h"] <= hall["y"] else "n"


def _rect(x, y, w, h, fill, line="", lw=0.0, r=0.0):
    return {"k": "rect", "x": x, "y": y, "w": w, "h": h, "fill": fill,
            "line": line, "lw": lw, "r": r}


def _oval(x, y, w, h, fill, line="", lw=0.0):
    return {"k": "oval", "x": x, "y": y, "w": w, "h": h, "fill": fill,
            "line": line, "lw": lw}


def _line(x1, y1, x2, y2, color, lw=0.06):
    return {"k": "line", "pts": [x1, y1, x2, y2], "color": color, "lw": lw}


def _text(x, y, text, role, color, anchor="w", maxw=None, kurz=None):
    return {"k": "text", "x": x, "y": y, "text": text, "kurz": kurz or text,
            "role": role, "color": color, "anchor": anchor, "maxw": maxw}


def _floor(x, y, w, h, kind, color):
    """Bodenbelag: Grundfarbe plus feine Struktur."""
    shapes = [_rect(x, y, w, h, color)]
    seam = mix(color, "#000000", 0.18)
    if kind == "parkett":
        row = 0
        yy = y + 0.5
        while yy < y + h - 0.01:
            shapes.append(_line(x, yy, x + w, yy, seam, 0.025))
            row += 1
            yy += 0.5
        # versetzte Stossfugen der Dielen
        for index in range(int(h / 0.5)):
            offset = 1.3 if index % 2 else 0.4
            xx = x + offset
            while xx < x + w:
                shapes.append(_line(xx, y + index * 0.5, xx, y + index * 0.5 + 0.5,
                                    seam, 0.025))
                xx += 2.2
    elif kind in ("fliesen", "doppelboden", "flur"):
        step = 1.0 if kind != "flur" else 0.66
        xx = x + step
        while xx < x + w - 0.01:
            shapes.append(_line(xx, y, xx, y + h, seam, 0.03))
            xx += step
        yy = y + step
        while yy < y + h - 0.01:
            shapes.append(_line(x, yy, x + w, yy, seam, 0.03))
            yy += step
    elif kind == "beton":
        # Hallenboden: glatter Estrich mit Dehnungsfugen und leichten Flecken
        xx = x + 2.0
        while xx < x + w - 0.01:
            shapes.append(_line(xx, y, xx, y + h, seam, 0.03))
            xx += 2.0
        yy = y + 2.0
        while yy < y + h - 0.01:
            shapes.append(_line(x, yy, x + w, yy, seam, 0.03))
            yy += 2.0
        spot = mix(color, "#FFFFFF", 0.05)
        for index in range(int(w * h / 3)):
            sx = x + ((index * 7.31) % w)
            sy = y + ((index * 3.77) % h)
            shapes.append(_oval(sx, sy, 0.16, 0.12, spot))
    else:  # teppichboden: dezentes Punktmuster
        dot = mix(color, "#FFFFFF", 0.06)
        yy = y + 0.6
        while yy < y + h:
            xx = x + (0.6 if int((yy - y) / 1.2) % 2 else 1.2)
            while xx < x + w:
                shapes.append(_oval(xx - 0.05, yy - 0.05, 0.1, 0.1, dot))
                xx += 1.2
            yy += 1.2
    return shapes


def _chair(cx, cy):
    return [_oval(cx - 0.33, cy - 0.33, 0.66, 0.66, CHAIR, mix(CHAIR, "#000000", 0.3), 0.04),
            _rect(cx - 0.3, cy + 0.18, 0.6, 0.16, mix(CHAIR, "#000000", 0.35), r=0.06)]


DECO_TYPES = ("schreibtisch", "pflanze", "regal", "aktenregal", "sessel",
              "besprechungstisch", "kaffeemaschine", "rack", "usv", "klima",
              "werkbank", "tisch", "pc", "drucker", "kartons", "whiteboard",
              "wasserspender", "feuerloescher", "teppich", "fussmatte", "bank",
              "hochregal", "palette", "hubwagen", "markierung",
              # Wohnung (ab 0.30)
              "bett", "matratze", "sofa", "couchtisch", "fernseher", "esstisch",
              "kuechenzeile", "kuehlschrank", "badewanne", "dusche", "wc",
              "waschbecken", "kleiderschrank", "stehlampe", "aquarium",
              "waschmaschine", "sitzsack", "kommode", "liegestuhl", "grill",
              "sonnenschirm", "hochbeet", "spielkonsole", "bild",
              # Beim Kunden (ab 0.30)
              "automat", "gleis", "zug", "tresen", "monitorwand", "leitstand",
              "absperrband", "wimpel", "anzeigetafel", "kamera", "bauzaun")


def _inside(deco, area):
    return area["x"] <= deco["x"] and deco["x"] + deco["w"] <= area["x"] + area["w"] and \
        area["y"] <= deco["y"] and deco["y"] + deco["h"] <= area["y"] + area["h"]


def _deco(item):
    """Ein Einrichtungsgegenstand als Zeichenbefehle. "dreh" (0 bis 3) dreht
    ihn in Vierteldrehungen im Uhrzeigersinn - w und h sind dann schon die
    gedrehten Masse (so, wie er im Raum Platz braucht)."""
    turns = int(item.get("dreh", 0) or 0) % 4
    if not turns:
        return _deco_plain(item)
    w, h = (item["h"], item["w"]) if turns % 2 else (item["w"], item["h"])
    shapes = _deco_plain(dict(item, x=0.0, y=0.0, w=w, h=h, dreh=0))
    frame_h = h
    for _turn in range(turns):
        shapes = [_rotate_shape(shape, frame_h) for shape in shapes]
        frame_h = w if frame_h == h else h
    return [_moved(shape, item["x"], item["y"]) for shape in shapes]


def _moved(shape, dx, dy):
    shape = dict(shape)
    if shape["k"] == "line":
        x1, y1, x2, y2 = shape["pts"]
        shape["pts"] = [x1 + dx, y1 + dy, x2 + dx, y2 + dy]
    else:
        shape["x"] += dx
        shape["y"] += dy
    return shape


def _deco_plain(item):
    kind = item["typ"]
    x, y, w, h = item["x"], item["y"], item["w"], item["h"]
    s = []
    if kind == "schreibtisch":
        facing = item.get("blick", "s")
        chair_y = y + h + 0.3 if facing == "s" else y - 0.3
        s += _chair(x + w / 2.0, chair_y)
        s.append(_rect(x, y, w, h, WOOD, WOOD_DARK, 0.05, 0.08))
        # Bildschirm auf der dem Stuhl abgewandten Seite, Tastatur davor
        my = y + 0.12 if facing == "s" else y + h - 0.32
        ky = y + h - 0.3 if facing == "s" else y + 0.14
        s.append(_rect(x + w / 2.0 - 0.55, my, 1.1, 0.2, SCREEN, "#6B5F9A", 0.03, 0.03))
        s.append(_rect(x + w / 2.0 - 0.4, ky, 0.8, 0.16, METAL, r=0.03))
        s.append(_oval(x + w / 2.0 + 0.55, ky, 0.16, 0.2, METAL))
        s.append(_rect(x + 0.15, y + 0.2, 0.35, 0.45, PAPER))
        if item.get("klebezettel"):
            for index, color in enumerate(("#FBBF24", "#F472B6", "#FBBF24")):
                s.append(_rect(x + w / 2.0 - 0.5 + index * 0.38, my - 0.12,
                               0.22, 0.22, color))
    elif kind == "pflanze":
        s.append(_oval(x + w * 0.2, y + h * 0.2, w * 0.6, h * 0.6, POT))
        for dx, dy in ((0.05, 0.25), (0.45, 0.2), (0.25, 0.0), (0.25, 0.45)):
            s.append(_oval(x + w * dx, y + h * dy, w * 0.5, h * 0.5, PLANT, PLANT_DARK, 0.03))
        s.append(_oval(x + w * 0.38, y + h * 0.38, w * 0.24, h * 0.24, PLANT_DARK))
    elif kind in ("regal", "aktenregal"):
        s.append(_rect(x, y, w, h, WOOD_DARK, r=0.04))
        colors = (["#60A5FA", "#F87171", "#FBBF24", "#34D399", "#A78BFA"]
                  if kind == "aktenregal" else [METAL, "#22D3EE", METAL, "#F472B6"])
        vertical = h >= w
        count = int((h if vertical else w) / 0.26)
        for index in range(count):
            color = colors[index % len(colors)]
            if vertical:
                s.append(_rect(x + 0.06, y + 0.08 + index * 0.26, w - 0.12, 0.18, color))
            else:
                s.append(_rect(x + 0.08 + index * 0.26, y + 0.06, 0.18, h - 0.12, color))
    elif kind == "sessel":
        s.append(_rect(x, y, w, h, "#7C3AED", mix("#7C3AED", "#000000", 0.3), 0.04, 0.2))
        s.append(_rect(x + 0.14, y + 0.24, w - 0.28, h - 0.34,
                       mix("#7C3AED", "#FFFFFF", 0.18), r=0.14))
    elif kind == "besprechungstisch":
        for index in range(3):
            cx = x + w * (index + 1) / 4.0
            s += _chair(cx, y - 0.3)
            s += _chair(cx, y + h + 0.3)
        s.append(_rect(x, y, w, h, WOOD, WOOD_DARK, 0.05, 0.6))
        s.append(_rect(x + w * 0.35, y + h * 0.3, 0.5, 0.35, PAPER))
        s.append(_oval(x + w * 0.62, y + h * 0.35, 0.3, 0.3, "#F4F1FA", METAL, 0.03))
    elif kind == "kaffeemaschine":
        s.append(_rect(x, y, w, h, METAL_DARK, METAL, 0.03, 0.06))
        s.append(_oval(x + w * 0.3, y + h * 0.3, w * 0.4, w * 0.4, "#F87171"))
        s.append(_oval(x - 0.28, y + h * 0.35, 0.22, 0.22, PAPER, METAL, 0.03))
    elif kind == "rack":
        s.append(_rect(x, y, w, h, "#1E1A30", "#5B5480", 0.05, 0.05))
        units = int((h - 0.2) / 0.28)
        for index in range(units):
            yy = y + 0.12 + index * 0.28
            s.append(_rect(x + 0.1, yy, w - 0.2, 0.2, "#2E2848"))
            led = "#34D399" if index % 3 else "#22D3EE"
            s.append(_oval(x + w - 0.26, yy + 0.05, 0.1, 0.1, led))
    elif kind == "usv":
        s.append(_rect(x, y, w, h, METAL_DARK, METAL, 0.04, 0.06))
        s.append(_rect(x + 0.15, y + 0.15, w * 0.45, 0.25, "#0B3B2E"))
        s.append(_oval(x + w - 0.35, y + 0.18, 0.18, 0.18, "#34D399"))
        s.append(_line(x + 0.15, y + h - 0.25, x + w - 0.15, y + h - 0.25, METAL, 0.04))
    elif kind == "klima":
        s.append(_rect(x, y, w, h, "#DDE6F0", METAL, 0.04, 0.05))
        yy = y + 0.25
        while yy < y + h - 0.15:
            s.append(_line(x + 0.1, yy, x + w - 0.1, yy, "#7FA0B8", 0.035))
            yy += 0.22
    elif kind == "werkbank":
        s += _chair(x + w * 0.5, y - 0.3)
        s.append(_rect(x, y, w, h, "#8A7A5C", "#5E523C", 0.05, 0.05))
        # PC-Gehaeuse mit offener Seite, Werkzeug und Mehmets Schraubenkaesten
        s.append(_rect(x + 0.3, y + 0.15, 0.9, 0.75, METAL_DARK, METAL, 0.03, 0.04))
        s.append(_rect(x + 0.42, y + 0.28, 0.5, 0.2, "#34D399"))
        s.append(_line(x + 1.6, y + 0.3, x + 2.3, y + 0.7, "#F87171", 0.08))
        s.append(_line(x + 2.3, y + 0.7, x + 2.5, y + 0.8, METAL, 0.05))
        for index, color in enumerate(("#F87171", "#FBBF24", "#34D399", "#60A5FA",
                                       "#A78BFA")):
            bx = x + w - 2.3 + index * 0.42
            s.append(_rect(bx, y + 0.3, 0.34, 0.34, color, r=0.05))
    elif kind == "tisch":
        s.append(_rect(x, y, w, h, "#8A7A5C", "#5E523C", 0.05, 0.05))
    elif kind == "pc":
        s.append(_rect(x, y, w, h, METAL_DARK, METAL, 0.04, 0.05))
        s.append(_oval(x + w / 2.0 - 0.07, y + 0.12, 0.14, 0.14, "#22D3EE"))
    elif kind == "drucker":
        s.append(_rect(x, y, w, h, "#CFCBDD", METAL, 0.04, 0.06))
        s.append(_rect(x + 0.15, y + 0.12, w - 0.3, 0.25, PAPER))
        s.append(_rect(x + w - 0.3, y + h - 0.25, 0.15, 0.1, "#34D399"))
    elif kind == "kartons":
        size = min(w, h) * 0.62
        for dx, dy in ((0, 0), (w - size, h - size), (w - size, 0)):
            s.append(_rect(x + dx, y + dy, size, size, CARDBOARD, "#8E6A3E", 0.04))
            s.append(_line(x + dx + size / 2.0, y + dy, x + dx + size / 2.0, y + dy + size,
                           "#E8D2A8", 0.06))
    elif kind == "whiteboard":
        s.append(_rect(x, y, w, h, PAPER, METAL, 0.03))
    elif kind == "wasserspender":
        s.append(_rect(x, y, w, h, METAL_DARK, r=0.06))
        s.append(_oval(x + 0.08, y + 0.08, w - 0.16, h - 0.16, "#60A5FA", "#BFDBFE", 0.03))
    elif kind == "feuerloescher":
        s.append(_oval(x, y, w, h, "#EF4444", "#7F1D1D", 0.03))
        s.append(_oval(x + w * 0.35, y + h * 0.35, w * 0.3, h * 0.3, "#1B1031"))
    elif kind == "teppich":
        s.append(_rect(x, y, w, h, "#3B2466", "#5B3A8F", 0.06, 0.1))
        s.append(_rect(x + 0.2, y + 0.2, w - 0.4, h - 0.4, "", "#6D4AA8", 0.03, 0.08))
    elif kind == "fussmatte":
        s.append(_rect(x, y, w, h, "#3D3550", "#595070", 0.04, 0.05))
        yy = y + 0.15
        while yy < y + h - 0.1:
            s.append(_line(x + 0.1, yy, x + w - 0.1, yy, "#595070", 0.03))
            yy += 0.15
    elif kind == "bank":
        s.append(_rect(x, y, w, h, WOOD, WOOD_DARK, 0.04, 0.08))
        for index in range(1, 4):
            s.append(_line(x + w * index / 4.0, y, x + w * index / 4.0, y + h, WOOD_DARK, 0.03))
    elif kind == "hochregal":
        # Schwerlastregal von oben: blaue Stuetzen, orange Traversen, Kartons
        s.append(_rect(x, y, w, h, "#2A2342"))
        vertical = h >= w
        length, depth = (h, w) if vertical else (w, h)
        fields = max(1, int(round(length / 1.3)))
        step = length / float(fields)
        palette = (CARDBOARD, "#B7864F", CARDBOARD, "#60A5FA", CARDBOARD, "#D9B27C")
        for index in range(fields):
            for row in range(2 if depth >= 0.9 else 1):
                size_a = step - 0.22
                size_b = (depth - 0.22) / (2 if depth >= 0.9 else 1) - 0.06
                a = 0.11 + index * step + 0.03
                b = 0.11 + row * (size_b + 0.06)
                color = palette[(index * 2 + row) % len(palette)]
                bx, by, bw, bh = ((x + b, y + a, size_b, size_a - 0.06) if vertical else
                                  (x + a, y + b, size_a - 0.06, size_b))
                s.append(_rect(bx, by, bw, bh, color, mix(color, "#000000", 0.35), 0.03))
                if vertical:
                    s.append(_line(bx, by + bh / 2.0, bx + bw, by + bh / 2.0, "#E8D2A8", 0.05))
                else:
                    s.append(_line(bx + bw / 2.0, by, bx + bw / 2.0, by + bh, "#E8D2A8", 0.05))
        beam = "#F97316"
        if vertical:
            s.append(_line(x + 0.05, y, x + 0.05, y + h, beam, 0.07))
            s.append(_line(x + w - 0.05, y, x + w - 0.05, y + h, beam, 0.07))
        else:
            s.append(_line(x, y + 0.05, x + w, y + 0.05, beam, 0.07))
            s.append(_line(x, y + h - 0.05, x + w, y + h - 0.05, beam, 0.07))
        for index in range(fields + 1):
            a = min(index * step, length - 0.14)
            for b in (0, depth - 0.14):
                px, py = (x + b, y + a) if vertical else (x + a, y + b)
                s.append(_rect(px, py, 0.14, 0.14, "#3B82F6"))
    elif kind == "palette":
        # Europalette mit gestapelten Kartons und Stretchfolie
        s.append(_rect(x, y, w, h, "#C8A06A", "#8A6A3E", 0.04))
        for index in range(1, 4):
            yy = y + h * index / 4.0
            s.append(_line(x, yy, x + w, yy, "#8A6A3E", 0.04))
        inset = 0.1
        bw = (w - 2 * inset - 0.06) / 2.0
        bh = (h - 2 * inset - 0.06) / 2.0
        for col in range(2):
            for row in range(2):
                bx = x + inset + col * (bw + 0.06)
                by = y + inset + row * (bh + 0.06)
                s.append(_rect(bx, by, bw, bh, CARDBOARD, "#8E6A3E", 0.03))
                s.append(_line(bx + bw / 2.0, by, bx + bw / 2.0, by + bh, "#E8D2A8", 0.05))
        s.append(_rect(x + inset / 2.0, y + inset / 2.0, w - inset, h - inset, "",
                       mix("#FFFFFF", CARDBOARD, 0.5), 0.03, 0.08))
    elif kind == "markierung":
        s.append(_rect(x, y, w, h, "#FBBF24"))
    elif kind == "hubwagen":
        # Handhubwagen: zwei Gabeln, gelber Aufbau, Deichsel
        fork = h * 0.26
        s.append(_rect(x + w * 0.3, y + h * 0.08, w * 0.7, fork, METAL, METAL_DARK, 0.03))
        s.append(_rect(x + w * 0.3, y + h * 0.66, w * 0.7, fork, METAL, METAL_DARK, 0.03))
        s.append(_rect(x + w * 0.14, y, w * 0.2, h, "#F59E0B", "#92400E", 0.04, 0.05))
        s.append(_line(x + w * 0.14, y + h / 2.0, x, y + h / 2.0, METAL_DARK, 0.08))
        s.append(_oval(x - 0.12, y + h / 2.0 - 0.14, 0.28, 0.28, "#1B1031"))
    else:
        s += _deco_more(kind, item, x, y, w, h)
    return s


# Farben der Wohnungs- und Kunden-Einrichtung (aus der Palette abgeleitet)
FABRIC = "#7C3AED"
BLANKET = "#60A5FA"
PILLOW = "#F4F1FA"
TILE_WHITE = "#E6E1F0"
WATER = "#7FE3F5"
RAIL = "#8E8AA3"
SLEEPER = "#6E4A2F"
TRAIN = "#A78BFA"
SIGN_RED = "#F87171"


def _deco_more(kind, item, x, y, w, h):
    """Einrichtung fuer Wohnung und Kundenstandorte. Grundausrichtung: die
    "Rueckseite" (Kopfende, Lehne, Wand) liegt oben - gedreht wird ueber
    "dreh" (siehe _deco)."""
    s = []
    dark = mix(C["card"], "#000000", 0.2)
    if kind in ("bett", "matratze"):
        if kind == "bett":
            s.append(_rect(x, y, w, h, WOOD, WOOD_DARK, 0.05, 0.08))
            s.append(_rect(x, y, w, 0.3, WOOD_DARK, r=0.06))
            inset = 0.14
        else:
            inset = 0.0
        s.append(_rect(x + inset, y + inset + (0.2 if kind == "bett" else 0), w - 2 * inset,
                       h - 2 * inset - (0.2 if kind == "bett" else 0), PAPER, METAL, 0.03, 0.12))
        pillows = 2 if w >= 2.4 else 1
        pw = (w - 2 * inset - 0.3 - 0.15 * (pillows - 1)) / pillows
        for index in range(pillows):
            s.append(_rect(x + inset + 0.15 + index * (pw + 0.15), y + inset + 0.35, pw, 0.55,
                           PILLOW, METAL, 0.03, 0.15))
        s.append(_rect(x + inset, y + h * 0.42, w - 2 * inset, h * 0.58 - inset,
                       BLANKET, mix(BLANKET, "#000000", 0.3), 0.04, 0.12))
        s.append(_line(x + inset + 0.1, y + h * 0.42 + 0.25, x + w - inset - 0.1,
                       y + h * 0.42 + 0.25, mix(BLANKET, "#FFFFFF", 0.35), 0.06))
    elif kind in ("sofa", "sitzsack"):
        if kind == "sitzsack":
            s.append(_oval(x, y, w, h, "#FB923C", mix("#FB923C", "#000000", 0.3), 0.04))
            s.append(_oval(x + w * 0.25, y + h * 0.25, w * 0.5, h * 0.45,
                           mix("#FB923C", "#FFFFFF", 0.2)))
        else:
            s.append(_rect(x, y, w, h, FABRIC, mix(FABRIC, "#000000", 0.3), 0.05, 0.2))
            s.append(_rect(x, y, 0.35, h, mix(FABRIC, "#000000", 0.15), r=0.15))
            s.append(_rect(x + w - 0.35, y, 0.35, h, mix(FABRIC, "#000000", 0.15), r=0.15))
            seats = max(2, int(round((w - 0.7) / 1.1)))
            sw = (w - 0.7) / seats
            for index in range(seats):
                s.append(_rect(x + 0.37 + index * sw, y + 0.4, sw - 0.06, h - 0.48,
                               mix(FABRIC, "#FFFFFF", 0.18), r=0.12))
    elif kind == "couchtisch":
        s.append(_rect(x, y, w, h, WOOD, WOOD_DARK, 0.05, 0.12))
        s.append(_oval(x + w * 0.2, y + h * 0.3, 0.3, 0.3, PAPER, METAL, 0.03))
        s.append(_rect(x + w * 0.55, y + h * 0.25, 0.5, 0.35, "#F472B6", r=0.04))
    elif kind in ("fernseher", "kommode"):
        s.append(_rect(x, y, w, h, WOOD_DARK, mix(WOOD_DARK, "#000000", 0.3), 0.04, 0.05))
        if kind == "fernseher":
            s.append(_rect(x + 0.2, y + 0.05, w - 0.4, 0.18, SCREEN, "#6B5F9A", 0.03, 0.03))
            s.append(_rect(x + w / 2.0 - 0.3, y + h - 0.3, 0.6, 0.18, METAL_DARK, r=0.04))
        else:
            for index in range(1, 3):
                s.append(_line(x + w * index / 3.0, y + 0.08, x + w * index / 3.0,
                               y + h - 0.08, mix(WOOD_DARK, "#000000", 0.3), 0.03))
            s.append(_oval(x + w * 0.15, y + h * 0.25, 0.3, 0.3, "#FBBF24"))
    elif kind == "spielkonsole":
        s.append(_rect(x, y, w, h, METAL_DARK, METAL, 0.03, 0.08))
        s.append(_oval(x + w * 0.15, y + h * 0.3, w * 0.3, h * 0.4, "#22D3EE"))
        s.append(_oval(x + w * 0.55, y + h * 0.3, w * 0.3, h * 0.4, "#F472B6"))
    elif kind == "esstisch":
        seats = max(1, int(round(w / 1.2)))
        for index in range(seats):
            cx = x + w * (index + 0.5) / seats
            s += _chair(cx, y - 0.3)
            s += _chair(cx, y + h + 0.3)
        s.append(_rect(x, y, w, h, WOOD, WOOD_DARK, 0.05, 0.1))
        s.append(_oval(x + w / 2.0 - 0.25, y + h / 2.0 - 0.25, 0.5, 0.5, PLANT, PLANT_DARK,
                       0.03))
    elif kind == "kuechenzeile":
        s.append(_rect(x, y, w, h, "#CFCBDD", METAL, 0.05, 0.05))
        s.append(_line(x, y + h - 0.12, x + w, y + h - 0.12, METAL, 0.04))
        # Spuele links, Kochfeld rechts
        s.append(_rect(x + 0.3, y + 0.15, 0.9, h - 0.4, METAL, METAL_DARK, 0.03, 0.08))
        s.append(_oval(x + 0.65, y + 0.2, 0.18, 0.18, METAL_DARK))
        hob = x + w - 1.4
        s.append(_rect(hob, y + 0.12, 1.1, h - 0.34, "#1E1A30", r=0.05))
        for dx, dy in ((0.28, 0.25), (0.8, 0.25)):
            s.append(_oval(hob + dx - 0.2, y + dy, 0.4, 0.4, "", "#F87171", 0.04))
        if w > 3.2:
            s.append(_rect(x + 1.5, y + 0.2, 0.5, 0.35, METAL_DARK, r=0.05))
    elif kind in ("kuehlschrank", "waschmaschine"):
        base = PAPER if kind == "kuehlschrank" else "#DDE6F0"
        s.append(_rect(x, y, w, h, base, METAL, 0.04, 0.08))
        if kind == "kuehlschrank":
            s.append(_line(x + 0.12, y + h - 0.2, x + w - 0.12, y + h - 0.2, METAL, 0.04))
            s.append(_rect(x + w * 0.3, y + 0.15, w * 0.25, 0.2, "#F472B6", r=0.03))
        else:
            s.append(_oval(x + w * 0.2, y + h * 0.2, w * 0.6, h * 0.6, "#1E1A30", METAL, 0.04))
            s.append(_oval(x + w * 0.32, y + h * 0.32, w * 0.36, h * 0.36, WATER))
    elif kind == "badewanne":
        s.append(_rect(x, y, w, h, TILE_WHITE, METAL, 0.05, 0.3))
        s.append(_rect(x + 0.15, y + 0.15, w - 0.3, h - 0.3, WATER, mix(WATER, "#000000", 0.2),
                       0.03, 0.25))
        s.append(_oval(x + 0.3, y + h / 2.0 - 0.1, 0.2, 0.2, METAL))
    elif kind == "dusche":
        s.append(_rect(x, y, w, h, TILE_WHITE, METAL, 0.05, 0.05))
        s.append(_line(x, y, x + w, y + h, mix(TILE_WHITE, METAL, 0.5), 0.03))
        s.append(_line(x + w, y, x, y + h, mix(TILE_WHITE, METAL, 0.5), 0.03))
        s.append(_oval(x + w / 2.0 - 0.14, y + h / 2.0 - 0.14, 0.28, 0.28, METAL_DARK))
    elif kind == "wc":
        s.append(_rect(x + w * 0.1, y, w * 0.8, h * 0.3, TILE_WHITE, METAL, 0.03, 0.05))
        s.append(_oval(x + w * 0.15, y + h * 0.22, w * 0.7, h * 0.75, TILE_WHITE, METAL, 0.04))
        s.append(_oval(x + w * 0.3, y + h * 0.38, w * 0.4, h * 0.45, mix(WATER, TILE_WHITE, 0.4)))
    elif kind == "waschbecken":
        s.append(_rect(x, y, w, h, TILE_WHITE, METAL, 0.04, 0.12))
        s.append(_oval(x + w * 0.2, y + h * 0.25, w * 0.6, h * 0.6, mix(WATER, TILE_WHITE, 0.5)))
        s.append(_rect(x + w / 2.0 - 0.05, y + 0.02, 0.1, 0.25, METAL))
    elif kind == "kleiderschrank":
        s.append(_rect(x, y, w, h, WOOD, WOOD_DARK, 0.05, 0.04))
        doors = max(2, int(round(w / 0.9)))
        for index in range(1, doors):
            xx = x + w * index / doors
            s.append(_line(xx, y + 0.05, xx, y + h - 0.05, WOOD_DARK, 0.04))
        for index in range(doors):
            xx = x + w * (index + 0.5) / doors
            s.append(_rect(xx - 0.05, y + h - 0.3, 0.1, 0.18, METAL))
    elif kind == "stehlampe":
        s.append(_oval(x, y, w, h, mix("#FBBF24", C["card"], 0.55)))
        s.append(_oval(x + w * 0.25, y + h * 0.25, w * 0.5, h * 0.5, "#FBBF24", "#B45309",
                       0.03))
    elif kind == "aquarium":
        s.append(_rect(x, y, w, h, METAL_DARK, METAL, 0.04, 0.04))
        s.append(_rect(x + 0.1, y + 0.1, w - 0.2, h - 0.2, WATER, r=0.03))
        for fx, fy, color in ((0.3, 0.35, "#FB923C"), (0.62, 0.55, "#F472B6"),
                              (0.45, 0.25, "#FBBF24")):
            s.append(_oval(x + w * fx, y + h * fy, 0.3, 0.16, color))
        s.append(_oval(x + w * 0.15, y + h * 0.55, 0.22, 0.22, PLANT))
    elif kind in ("liegestuhl",):
        s.append(_rect(x, y, w, h, "#DDE6F0", METAL, 0.04, 0.1))
        yy = y + 0.3
        while yy < y + h - 0.1:
            s.append(_line(x + 0.08, yy, x + w - 0.08, yy, "#22D3EE", 0.08))
            yy += 0.3
    elif kind == "grill":
        s.append(_oval(x, y, w, h, METAL_DARK, METAL, 0.04))
        for index in range(1, 4):
            yy = y + h * index / 4.0
            s.append(_line(x + 0.12, yy, x + w - 0.12, yy, METAL, 0.03))
        s.append(_oval(x + w * 0.35, y + h * 0.35, w * 0.3, h * 0.3, "#F87171"))
    elif kind == "sonnenschirm":
        s.append(_oval(x, y, w, h, "#F472B6", mix("#F472B6", "#000000", 0.3), 0.04))
        s.append(_line(x + w / 2.0, y, x + w / 2.0, y + h, PAPER, 0.04))
        s.append(_line(x, y + h / 2.0, x + w, y + h / 2.0, PAPER, 0.04))
        s.append(_oval(x + w / 2.0 - 0.08, y + h / 2.0 - 0.08, 0.16, 0.16, PAPER))
    elif kind == "hochbeet":
        s.append(_rect(x, y, w, h, WOOD, WOOD_DARK, 0.05, 0.05))
        s.append(_rect(x + 0.12, y + 0.12, w - 0.24, h - 0.24, "#6B4226"))
        for index in range(max(1, int(w / 0.6))):
            s.append(_oval(x + 0.2 + index * 0.6, y + h / 2.0 - 0.2, 0.4, 0.4, PLANT,
                           PLANT_DARK, 0.03))
    elif kind == "bild":
        s.append(_rect(x, y, w, h, WOOD_DARK, r=0.02))
        s.append(_rect(x + 0.06, y + 0.04, w - 0.12, h - 0.08, "#22D3EE"))
    # ---- beim Kunden -------------------------------------------------------
    elif kind == "automat":
        # Fahrkartenautomat: Gehaeuse, Bildschirm vorn (unten), Tasten
        s.append(_rect(x, y, w, h, "#3B2466", "#A78BFA", 0.05, 0.08))
        s.append(_rect(x + 0.15, y + h - 0.45, w - 0.3, 0.3, "#22D3EE", r=0.04))
        s.append(_rect(x + 0.15, y + 0.15, w - 0.3, 0.18, "#F472B6", r=0.03))
        if item.get("defekt"):
            s.append(_rect(x + 0.15, y + h - 0.45, w - 0.3, 0.3, SCREEN, r=0.04))
            s.append(_line(x + 0.25, y + h - 0.4, x + w - 0.25, y + h - 0.2, "#F87171", 0.05))
    elif kind == "gleis":
        s.append(_rect(x, y, w, h, "#3A3350"))
        xx = x + 0.2
        while xx < x + w:
            s.append(_rect(xx, y + 0.12, 0.28, h - 0.24, SLEEPER))
            xx += 0.7
        for rail_y in (y + h * 0.3, y + h * 0.7):
            s.append(_line(x, rail_y, x + w, rail_y, RAIL, 0.09))
    elif kind == "zug":
        s.append(_rect(x, y, w, h, TRAIN, mix(TRAIN, "#000000", 0.35), 0.06, 0.45))
        s.append(_rect(x + 0.1, y + 0.18, w - 0.2, 0.2, mix(TRAIN, "#000000", 0.25), r=0.1))
        xx = x + 0.7
        while xx < x + w - 0.9:
            s.append(_rect(xx, y + h - 0.42, 0.7, 0.24, WINDOW, r=0.05))
            xx += 1.0
        car = w / max(1, int(round(w / 8.0)))
        xx = x + car
        while xx < x + w - 0.5:
            s.append(_line(xx, y, xx, y + h, mix(TRAIN, "#000000", 0.35), 0.05))
            xx += car
    elif kind == "tresen":
        s.append(_rect(x, y, w, h, WOOD, WOOD_DARK, 0.05, 0.1))
        places = max(1, int(round(w / 2.0)))
        for index in range(places):
            cx = x + w * (index + 0.5) / places
            s.append(_rect(cx - 0.45, y + 0.1, 0.9, 0.2, SCREEN, "#6B5F9A", 0.03, 0.03))
            s.append(_rect(cx - 0.3, y + h - 0.35, 0.6, 0.22, METAL, r=0.03))
            s += _chair(cx, y - 0.35)
    elif kind == "monitorwand":
        s.append(_rect(x, y, w, h, "#1E1A30", "#5B5480", 0.04, 0.03))
        count = max(2, int(w / 1.1))
        mw = (w - 0.1) / count
        for index in range(count):
            color = ("#22D3EE", "#34D399", "#A78BFA", "#FBBF24")[index % 4]
            s.append(_rect(x + 0.05 + index * mw + 0.04, y + 0.05, mw - 0.08, h - 0.1,
                           mix(SCREEN, color, 0.35), color, 0.02, 0.02))
    elif kind == "leitstand":
        s += _chair(x + w / 2.0, y + h + 0.35)
        s.append(_rect(x, y, w, h, METAL_DARK, METAL, 0.04, 0.12))
        for index in range(3):
            mx = x + w / 2.0 - 1.1 + index * 0.75
            s.append(_rect(mx, y + 0.1, 0.65, 0.2, SCREEN, "#6B5F9A", 0.03, 0.03))
        s.append(_rect(x + w / 2.0 - 0.4, y + h - 0.3, 0.8, 0.16, METAL, r=0.03))
        s.append(_oval(x + w - 0.45, y + h - 0.4, 0.26, 0.26, "#F87171"))
    elif kind in ("absperrband", "bauzaun"):
        if kind == "bauzaun":
            s.append(_rect(x, y, w, h, "", METAL, 0.04))
            s.append(_line(x, y, x + w, y + h, METAL, 0.03))
            s.append(_line(x + w, y, x, y + h, METAL, 0.03))
        vertical = h > w
        length = h if vertical else w
        parts = max(1, int(length / 0.35))
        for index in range(parts):
            color = SIGN_RED if index % 2 == 0 else PAPER
            a, b = length * index / parts, length * (index + 1) / parts
            if vertical:
                s.append(_line(x + w / 2.0, y + a, x + w / 2.0, y + b, color, 0.1))
            else:
                s.append(_line(x + a, y + h / 2.0, x + b, y + h / 2.0, color, 0.1))
    elif kind == "wimpel":
        s.append(_line(x, y + 0.05, x + w, y + 0.05, PAPER, 0.03))
        count = max(2, int(w / 0.4))
        for index in range(count):
            color = ("#22D3EE", "#F472B6", "#34D399", "#FBBF24")[index % 4]
            left = x + w * index / count
            s.append(_rect(left + 0.05, y + 0.08, w / count - 0.1, h - 0.1, color, r=0.02))
    elif kind == "anzeigetafel":
        s.append(_rect(x, y, w, h, SCREEN, METAL, 0.04, 0.05))
        rows = max(1, int((h - 0.1) / 0.22))
        for index in range(rows):
            yy = y + 0.1 + index * 0.22
            s.append(_line(x + 0.12, yy + 0.06, x + w * 0.55, yy + 0.06, "#FBBF24", 0.06))
            s.append(_line(x + w * 0.65, yy + 0.06, x + w - 0.12, yy + 0.06, "#34D399", 0.06))
    elif kind == "kamera":
        s.append(_oval(x, y, w, h, METAL_DARK, METAL, 0.03))
        s.append(_oval(x + w * 0.3, y + h * 0.3, w * 0.4, h * 0.4, "#22D3EE"))
        s.append(_oval(x + w * 0.7, y + h * 0.1, w * 0.2, h * 0.2, "#F87171"))
    return s


def person_shapes(cx, cy, appearance, size=1.0, ring=None):
    """Eine Person von oben: Schultern im Oberteil, Kopf mit Haaren."""
    look = normalize_appearance(appearance)
    skin = SKIN_COLORS[look["haut"]]
    hair = HAIR_COLORS[look["haarfarbe"]]
    shirt = SHIRT_COLORS[look["oberteil"]]
    s = []
    if ring:
        s.append(_oval(cx - size * 0.7, cy - size * 0.55, size * 1.4, size * 1.1, "", ring,
                       0.08))
    s.append(_rect(cx - size / 2.0, cy - size * 0.22, size, size * 0.5, shirt,
                   mix(shirt, "#000000", 0.35), 0.04, size * 0.22))
    head = size * 0.5
    if look["frisur"] == "lang":
        s.append(_oval(cx - head * 0.6, cy - head * 0.55, head * 1.2, head * 1.25, hair))
    if look["frisur"] == "zopf":
        s.append(_oval(cx - head * 0.18, cy + head * 0.35, head * 0.36, head * 0.5, hair))
    s.append(_oval(cx - head / 2.0, cy - head / 2.0, head, head,
                   skin if look["frisur"] == "glatze" else hair,
                   mix(hair, "#000000", 0.4), 0.03))
    if look["frisur"] == "locken":
        for dx, dy in ((-0.28, -0.2), (0.28, -0.2), (0.0, -0.36)):
            s.append(_oval(cx + head * dx - head * 0.2, cy + head * dy - head * 0.2,
                           head * 0.4, head * 0.4, hair))
    if look.get("extra") == "kappe":
        s.append(_oval(cx - head * 0.5, cy - head * 0.5, head, head, shirt))
        s.append(_rect(cx - head * 0.3, cy - head * 0.85, head * 0.6, head * 0.4, shirt,
                       r=0.05))
    return s


def plan_size(rotate=False, content=None):
    """Breite und Hoehe der Zeichnung in Grundriss-Einheiten. Gedreht (rotate)
    steht das Gebaeude hochkant - so nutzt die Grossansicht auf dem Handy den
    Bildschirm aus."""
    building = (content or GAME)["gebaeude"]
    if rotate:
        return building["hoehe"], building["breite"]
    return building["breite"], building["hoehe"]


def to_view(x, y, rotate=False, content=None):
    """Punkt im Gebaeude -> Punkt in der (evtl. gedrehten) Zeichnung."""
    if not rotate:
        return x, y
    return (content or GAME)["gebaeude"]["hoehe"] - y, x


def from_view(x, y, rotate=False, content=None):
    """Punkt in der Zeichnung (z.B. ein Klick) -> Punkt im Gebaeude."""
    if not rotate:
        return x, y
    return y, (content or GAME)["gebaeude"]["hoehe"] - x


def _rotate_shape(shape, height):
    """Dreht einen Zeichenbefehl um 90 Grad im Uhrzeigersinn."""
    shape = dict(shape)
    if shape["k"] in ("rect", "oval", "arc"):
        shape["x"], shape["y"] = height - shape["y"] - shape["h"], shape["x"]
        shape["w"], shape["h"] = shape["h"], shape["w"]
        if shape["k"] == "arc":
            shape["start"] += 90
    elif shape["k"] == "line":
        x1, y1, x2, y2 = shape["pts"]
        shape["pts"] = [height - y1, x1, height - y2, x2]
    elif shape["k"] == "text":
        shape["x"], shape["y"] = height - shape["y"], shape["x"]
    return shape


def _view_rect(item, rotate, content):
    """Raumflaeche in Zeichnungs-Koordinaten (x, y, w, h)."""
    x, y, w, h = item["x"], item["y"], item["w"], item["h"]
    if rotate:
        return content["gebaeude"]["hoehe"] - y - h, x, h, w
    return x, y, w, h


def player_shapes(position, player, rotate=False, content=None):
    """Die Spielfigur (Kreis in der gewaehlten Farbe, Name daneben) an position
    im Gebaeude."""
    x, y = to_view(position[0], position[1], rotate, content)
    ring = RING_COLORS[normalize_appearance(player[1])["kreis"]]
    shapes = person_shapes(x, y, player[1], ring=ring)
    # Name unter der Figur (wie bei den Kollegen), so verdeckt er kein "!"
    shapes.append(_text(x, y + 0.8, player[0] or "Du", "player", ring, anchor="c"))
    return shapes


def building_shapes(counts=None, selected=None, player=None, content=None,
                    quests=None, player_pos=None, rotate=False):
    """Zeichenbefehle fuer das ganze Buerogebaeude.

    counts:     offene Tickets je Raum-ID (rosa Plakette)
    selected:   ausgewaehlte Raum-ID (farbiger Rahmen)
    player:     (Name, Aussehen) des Protagonisten oder None (dann zeichnet
                die Oberflaeche die Figur selbst, z.B. waehrend sie laeuft)
    quests:     IDs der Kollegen mit offenem Auftrag (gruenes "!" ueber dem Kopf)
    player_pos: Standort der Spielfigur, sonst ihr Platz im Flur
    rotate:     Gebaeude hochkant zeichnen (Handy-Grossansicht)
    """
    content = content or GAME
    building = content["gebaeude"]
    counts = counts or {}
    quests = quests or set()
    width, height = building["breite"], building["hoehe"]
    hall = building["flur"]
    s = []

    # Boeden
    s += _floor(0, hall["y"], width, hall["h"], hall.get("boden", "flur"),
                hall.get("bodenfarbe") or mix(C["card_alt"], "#FFFFFF", 0.05))
    for item in building["raeume"]:
        color = mix(C["card_alt"], room_color(item), 0.13)
        if item.get("bodenfarbe"):
            color = item["bodenfarbe"]
        s += _floor(item["x"], item["y"], item["w"], item["h"],
                    item.get("boden", "teppichboden"), color)

    # Einrichtung
    for item in building["raeume"]:
        for deco in item.get("deko", []):
            s += _deco(deco)
    for deco in hall.get("deko", []):
        s += _deco(deco)

    # Kollegen an ihren Plaetzen
    for person in content["kollegen"]:
        if person.get("platz"):
            s += person_shapes(person["platz"][0], person["platz"][1],
                               person.get("aussehen"))

    # Innenwaende (Raumgrenzen) und Aussenwand
    for item in building["raeume"]:
        x, y, w, h = item["x"], item["y"], item["w"], item["h"]
        s.append(_rect(x, y, w, h, "", WALL, WALL_INNER))
    s.append(_rect(0, 0, width, height, "", WALL_OUTER, 0.3))

    # Fenster in der Aussenwand
    for x1, y1, x2, y2 in building.get("fenster", []):
        s.append(_line(x1, y1, x2, y2, WINDOW, 0.14))
        s.append(_line(x1, y1, x2, y2, mix(WINDOW, "#FFFFFF", 0.6), 0.04))
    # Rolltor zur Laderampe: Metall mit gelb-schwarzer Warnmarkierung
    for x1, y1, x2, y2 in building.get("rolltor", []):
        s.append(_line(x1, y1, x2, y2, METAL_DARK, 0.34))
        length = math.hypot(x2 - x1, y2 - y1)
        parts = max(1, int(length / 0.3))
        for index in range(parts):
            if index % 2:
                continue
            a, b = index / float(parts), (index + 1) / float(parts)
            s.append(_line(x1 + (x2 - x1) * a, y1 + (y2 - y1) * a,
                           x1 + (x2 - x1) * b, y1 + (y2 - y1) * b, "#FBBF24", 0.14))

    # Tueren: Oeffnung in der Wand, Tuerblatt und Schwenkbogen zum Flur hin
    floor_hall = hall.get("bodenfarbe") or mix(C["card_alt"], "#FFFFFF", 0.05)
    for item in building["raeume"]:
        door = item.get("tuer")
        if not door:
            continue
        side = door_side(item, content)
        span = door["bis"] - door["von"]
        hinge = door["von"]
        arc_color = mix(WALL, C["card_alt"], 0.45)
        if door.get("offen"):
            # Breite Oeffnung ohne Tuerblatt (z.B. zum Bahnsteig)
            if side in ("w", "o"):
                wall_x = item["x"] if side == "w" else item["x"] + item["w"]
                s.append(_rect(wall_x - 0.16, door["von"], 0.32, span, floor_hall))
            else:
                wall_y = item["y"] + item["h"] if side == "s" else item["y"]
                s.append(_rect(door["von"], wall_y - 0.16, span, 0.32, floor_hall))
            continue
        if side in ("w", "o"):
            # Seitentuer: schwenkt in den Flur (nach links bzw. rechts)
            wall_x = item["x"] if side == "w" else item["x"] + item["w"]
            swing = -span if side == "w" else span
            s.append(_rect(wall_x - 0.16, door["von"], 0.32, span, floor_hall))
            s.append(_line(wall_x, hinge, wall_x + swing * 0.9, hinge, WALL_OUTER, 0.07))
            s.append({"k": "arc", "x": wall_x - span, "y": hinge - span, "w": span * 2,
                      "h": span * 2, "start": 90 if side == "w" else 0, "extent": 90,
                      "color": arc_color, "lw": 0.03})
            continue
        top_row = side == "s"
        wall_y = item["y"] + item["h"] if top_row else item["y"]
        s.append(_rect(door["von"], wall_y - 0.16, span, 0.32, floor_hall))
        swing = span if top_row else -span
        s.append(_line(hinge, wall_y, hinge, wall_y + swing * 0.9, WALL_OUTER, 0.07))
        s.append({"k": "arc", "x": hinge - span, "y": wall_y - span, "w": span * 2,
                  "h": span * 2, "start": 0 if top_row else -90, "extent": 90,
                  "color": arc_color, "lw": 0.03})
    entrance = hall["eingang"]
    s.append(_rect(-0.2, entrance["von"], 0.4, entrance["bis"] - entrance["von"], floor_hall))
    s.append(_line(0, entrance["von"], 0, entrance["bis"], mix(WINDOW, C["card"], 0.3), 0.06))

    if rotate:
        s = [_rotate_shape(shape, height) for shape in s]

    # Ab hier in Zeichnungs-Koordinaten, damit Schrift nie mitgedreht wird.
    # Beschriftung, Auswahl und Ticket-Plaketten zuletzt, damit sie oben liegen
    for item in building["raeume"]:
        x, y, w, h = _view_rect(item, rotate, content)
        color = room_color(item)
        if item["id"] == selected:
            s.append(_rect(x + 0.14, y + 0.14, w - 0.28, h - 0.28, "", color, 0.12, 0.2))
        label = _text(x + 0.55, y + 0.78, item["name"], "raum", C["text"],
                      maxw=w - 2.2, kurz=item.get("kurz"))
        label["bg"] = mix(C["card"], color, 0.1)
        label["border"] = mix(color, C["card"], 0.3)
        s.append(label)
        count = counts.get(item["id"], 0)
        if count:
            s.append(_oval(x + w - 1.05, y + 0.38, 0.8, 0.8, C["pink"], C["card"], 0.06))
            s.append(_text(x + w - 0.65, y + 0.78, str(count), "badge", C["on_accent"],
                           anchor="c"))
    for person in content["kollegen"]:
        if not person.get("platz"):
            continue
        px_, py_ = to_view(person["platz"][0], person["platz"][1], rotate, content)

        s.append(_text(px_, py_ + 0.62, short_name(person), "person",
                       C["text_soft"], anchor="c"))
        if person["id"] in quests:
            s.append(_oval(px_ + 0.25, py_ - 1.15, 0.68, 0.68, C["green"], C["card"], 0.05))
            s.append(_text(px_ + 0.59, py_ - 0.81, "!", "badge", C["card"], anchor="c"))

    if player:
        s += player_shapes(player_pos or hall.get("spieler", [2.4, 7.0]), player,
                           rotate, content)
    return s


# ============================================================================
#  LAUFEN DURCH DAS GEBAEUDE
# ============================================================================
#
# Die Spielfigur laeuft auf einem feinen Raster (WALK_STEP Einheiten). Waende
# (ausser an Tueren), Moebel und Kollegen sind Hindernisse. Der Weg wird mit
# einer Breitensuche gefunden und danach geglaettet, damit die Figur nicht im
# Zickzack laeuft. Alles ohne Oberflaeche, damit PC und Handy gleich laufen.

WALK_STEP = 0.25
BODY_RADIUS = 0.3          # Abstand der Figur zu Waenden und Moebeln
PERSON_RADIUS = 0.5        # Kollegen stehen im Weg
REACH = 1.3                # so nah muss man an eine Person heran
WALK_FREE = ("teppich", "fussmatte", "whiteboard", "markierung", "bild", "wimpel",
             "kamera")   # darueber laeuft man (oder es haengt an der Wand)
_GRID_CACHE = {}
_PEOPLE_CACHE = {}


def _segments(content):
    """Wandstuecke als Rechtecke (x1, y1, x2, y2) - Tueroeffnungen ausgespart."""
    building = content["gebaeude"]
    width, height = building["breite"], building["hoehe"]
    half = WALL_INNER / 2.0
    walls = []

    def horizontal(x1, x2, y, gap=None):
        if gap:
            walls.append((x1, y - half, gap[0], y + half))
            walls.append((gap[1], y - half, x2, y + half))
        else:
            walls.append((x1, y - half, x2, y + half))

    def vertical(x, y1, y2, gap=None):
        if gap:
            walls.append((x - half, y1, x + half, gap[0]))
            walls.append((x - half, gap[1], x + half, y2))
        else:
            walls.append((x - half, y1, x + half, y2))

    for item in building["raeume"]:
        x, y, w, h = item["x"], item["y"], item["w"], item["h"]
        door = item.get("tuer")
        gap = (door["von"], door["bis"]) if door else None
        side = door_side(item, content)
        horizontal(x, x + w, y, gap if side == "n" else None)
        horizontal(x, x + w, y + h, gap if side == "s" else None)
        vertical(x, y, y + h, gap if side == "w" else None)
        vertical(x + w, y, y + h, gap if side == "o" else None)
    # Aussenwand (der Eingang fuehrt nach draussen - dort ist Schluss)
    walls += [(0, -1, width, 0.15), (0, height - 0.15, width, height + 1),
              (-1, 0, 0.15, height), (width - 0.15, 0, width + 1, height)]
    return walls


def _obstacles(content):
    rects = list(_segments(content))
    building = content["gebaeude"]
    decos = [d for item in building["raeume"] for d in item.get("deko", [])]
    decos += building["flur"].get("deko", [])
    for deco in decos:
        if deco["typ"] in WALK_FREE:
            continue
        rects.append((deco["x"], deco["y"], deco["x"] + deco["w"], deco["y"] + deco["h"]))
    return rects


def _base_grid(building):
    """Begehbare Rasterzellen ohne Personen - haengt nur vom Grundriss ab und
    wird je Grundriss einmal berechnet."""
    key = id(building)
    cached = _GRID_CACHE.get(key)
    if cached and cached[0] is building:
        return cached[1]
    if len(_GRID_CACHE) > 40:
        _GRID_CACHE.clear()
    cols = int(building["breite"] / WALK_STEP)
    rows = int(building["hoehe"] / WALK_STEP)
    rects = _obstacles({"gebaeude": building})
    free = set()
    for col in range(cols):
        cx = (col + 0.5) * WALK_STEP
        for row in range(rows):
            cy = (row + 0.5) * WALK_STEP
            blocked = False
            for x1, y1, x2, y2 in rects:
                dx = max(x1 - cx, 0, cx - x2)
                dy = max(y1 - cy, 0, cy - y2)
                if dx * dx + dy * dy < BODY_RADIUS * BODY_RADIUS:
                    blocked = True
                    break
            if not blocked:
                free.add((col, row))
    _GRID_CACHE[key] = (building, free)
    return free


def _walk_grid(content=None):
    """Begehbare Rasterzellen als Menge von (spalte, zeile). Personen stehen
    im Weg - sie werden vom Grundriss-Raster abgezogen."""
    content = content or GAME
    base = _base_grid(content["gebaeude"])
    people = tuple(tuple(p["platz"]) for p in content["kollegen"] if p.get("platz"))
    key = (id(content["gebaeude"]), people)
    cached = _PEOPLE_CACHE.get(key)
    if cached and cached[0] is content["gebaeude"]:
        return cached[1]
    if len(_PEOPLE_CACHE) > 80:
        _PEOPLE_CACHE.clear()
    reach = int(PERSON_RADIUS / WALK_STEP) + 1
    blocked = set()
    for px_, py_ in people:
        col0, row0 = _cell(px_, py_)
        for col in range(col0 - reach, col0 + reach + 1):
            for row in range(row0 - reach, row0 + reach + 1):
                cx, cy = (col + 0.5) * WALK_STEP, (row + 0.5) * WALK_STEP
                if (px_ - cx) ** 2 + (py_ - cy) ** 2 < PERSON_RADIUS ** 2:
                    blocked.add((col, row))
    free = base - blocked if blocked else base
    _PEOPLE_CACHE[key] = (content["gebaeude"], free)
    return free


def _cell(x, y):
    return int(x / WALK_STEP), int(y / WALK_STEP)


def _center(cell):
    return ((cell[0] + 0.5) * WALK_STEP, (cell[1] + 0.5) * WALK_STEP)


def can_stand(x, y, content=None):
    return _cell(x, y) in _walk_grid(content)


def _nearest_free(x, y, free):
    start = _cell(x, y)
    if start in free:
        return start
    best, best_dist = None, None
    for cell in free:
        dist = (cell[0] - start[0]) ** 2 + (cell[1] - start[1]) ** 2
        if best_dist is None or dist < best_dist:
            best, best_dist = cell, dist
    return best


def _line_free(a, b, free):
    """Geht die gerade Strecke a -> b nur ueber begehbare Zellen?"""
    steps = int(max(abs(b[0] - a[0]), abs(b[1] - a[1])) / (WALK_STEP / 3.0)) + 1
    for index in range(steps + 1):
        t = index / float(steps)
        if _cell(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t) not in free:
            return False
    return True


def walk_path(start, target, reach=0.0, content=None):
    """Weg von start zu target als Liste von Punkten (ohne den Startpunkt).

    reach > 0: Es genuegt, bis auf diesen Abstand an target heranzukommen
    (z.B. an eine Person, die selbst im Weg steht). Leere Liste = schon da
    oder nicht erreichbar."""
    free = _walk_grid(content)
    begin = _nearest_free(start[0], start[1], free)
    if reach > 0:
        goals = {cell for cell in free
                 if (_center(cell)[0] - target[0]) ** 2 +
                 (_center(cell)[1] - target[1]) ** 2 <= reach * reach}
    else:
        goal = _nearest_free(target[0], target[1], free)
        goals = {goal} if goal else set()
    if begin is None or not goals:
        return []
    if begin in goals:
        return []
    previous = {begin: None}
    queue = [begin]
    found = None
    for cell in queue:            # Breitensuche (die Liste waechst mit)
        if cell in goals:
            found = cell
            break
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                       (1, 1), (1, -1), (-1, 1), (-1, -1)):
            nxt = (cell[0] + dx, cell[1] + dy)
            if nxt in free and nxt not in previous:
                # diagonal nur, wenn beide Nachbarn frei sind (keine Ecken schneiden)
                if dx and dy and ((cell[0] + dx, cell[1]) not in free or
                                  (cell[0], cell[1] + dy) not in free):
                    continue
                previous[nxt] = cell
                queue.append(nxt)
    if found is None:
        return []
    cells = []
    while found is not None:
        cells.append(found)
        found = previous[found]
    points = [_center(cell) for cell in reversed(cells)]
    if reach <= 0 and can_stand(target[0], target[1], content):
        points[-1] = (target[0], target[1])
    # Glaetten: Zwischenpunkte weglassen, solange die gerade Strecke frei ist
    smooth = [points[0]]
    index = 0
    while index < len(points) - 1:
        nxt = len(points) - 1
        while nxt > index + 1 and not _line_free(points[index], points[nxt], free):
            nxt -= 1
        smooth.append(points[nxt])
        index = nxt
    return smooth[1:]


def person_at(x, y, content=None, radius=0.7):
    """Kollege an der Stelle (x, y) im Gebaeude oder None."""
    for person in (content or GAME)["kollegen"]:
        if person.get("platz") and (person["platz"][0] - x) ** 2 + \
                (person["platz"][1] - y) ** 2 <= radius * radius:
            return person
    return None


def person_near(x, y, content=None):
    """Kollege in Reichweite der Spielfigur (zum Ansprechen) oder None."""
    return person_at(x, y, content, radius=REACH + 0.15)


def warehouse_summary(state, content=None):
    """Lagerstand in einem Satz (fuer den Lageristen im Buero)."""
    content = content or GAME
    store = state.warehouse()
    parts = []
    count = sum(amount for _part, amount in store["bestand"])
    if count:
        parts.append("Auf Lager: %d Teil%s." % (count, "" if count == 1 else "e"))
    if store["unterwegs"]:
        first = store["unterwegs"][0]
        parts.append("Nächste Lieferung: %s an Arbeitstag %d." % (
            part(first["teil"], content)["name"], first["ankunft"]))
    return " ".join(parts) or "Das Lager ist leer, es ist nichts bestellt."


def short_name(person):
    """Kurzname im Grundriss und in Meldungen: der Vorname, bei einem Titel
    wie "Dr." Titel und Nachname ("Dr. Wendt")."""
    parts = person["name"].split()
    if len(parts) > 2 and parts[0].endswith("."):
        return "%s %s" % (parts[0], parts[-1])
    return parts[0]


def office_message(position, person, quests, content=None, state=None):
    """Text unter der Grossansicht: (Ueberschrift, Text) je nach Standort."""
    if person:
        first = short_name(person)
        tasks = quests.get(person["id"]) or []
        if tasks:
            more = " (und %d weitere)" % (len(tasks) - 1) if len(tasks) > 1 else ""
            return ("%s hat einen Auftrag für dich" % first,
                    "„%s“ · Priorität %s%s" % (tasks[0]["titel"], tasks[0]["prioritaet"],
                                               more))
        if person.get("mitarbeiter") and person.get("projekt_text"):
            return ("%s · %s" % (person["name"], person["rolle"]),
                    "%s Heute keine Routineaufträge, der Tag gehört dem Projekt."
                    % person["projekt_text"])
        if person.get("mitarbeiter") and person.get("kundenticket"):
            ticket = person["kundenticket"]
            return ("%s · %s" % (person["name"], person["rolle"]),
                    "Sitzt heute an „%s“ für %s (Chance %d %%). Dazu Routineaufträge: %s "
                    "Umsatz pro Arbeitstag." % (ticket["titel"], ticket["kunde"]["name"],
                                                ticket["chance"],
                                                _whole_euro(person.get("umsatz", 0))))
        if person.get("mitarbeiter"):
            return ("%s · %s" % (person["name"], person["rolle"]),
                    "In der Weiterbildung, heute kein Umsatz." if person.get("in_weiterbildung")
                    else "Kümmert sich um Routineaufträge: %s Umsatz pro Arbeitstag. %s"
                    % (_whole_euro(person.get("umsatz", 0)), person.get("macke", "")))
        if person.get("lagerist") and state is not None:
            return ("%s · %s" % (person["name"], person["rolle"]),
                    "Gerade nichts für dich. " + warehouse_summary(state, content))
        return ("%s · %s" % (person["name"], person["rolle"]),
                "Gerade nichts für dich. %s" % person.get("macke", ""))
    item = room_at(position[0], position[1], content)
    waiting = sum(len(tasks) for tasks in quests.values())
    where = "Du bist im Raum %s." % item["name"] if item else "Du bist im Flur."
    if waiting:
        hint = "%d Auftrag wartet." % waiting if waiting == 1 else \
            "%d Aufträge warten." % waiting
        return (where, hint + " Wer einen hat, trägt ein grünes „!“.")
    if state is not None and state.firm:
        return (where, "Deine Leute kümmern sich um die Routineaufträge. Feierabend "
                       "machst du an der Eingangstür.")
    return (where, "Heute wartet kein Auftrag mehr.")


def start_position(content=None):
    return tuple((content or GAME)["gebaeude"]["flur"].get("spieler", [2.4, 7.0]))


def room_at(x, y, content=None):
    """Raum an der Stelle (x, y) in Grundriss-Einheiten - Treffer ueber die
    Raumflaechen, damit PC und Handy gleich reagieren. Der Flur ist kein Raum."""
    for item in (content or GAME)["gebaeude"]["raeume"]:
        if item["x"] <= x < item["x"] + item["w"] and item["y"] <= y < item["y"] + item["h"]:
            return item
    return None


# ============================================================================
#  ORTE: BUERO, KUNDE, ZUHAUSE (ab 0.30)
# ============================================================================
#
# Alle drei Orte benutzen dasselbe Zeichnen (building_shapes) und Laufen
# (walk_path): site_content() baut dafuer ein "Inhalts-Woerterbuch" wie
# GAME, nur mit dem Grundriss und den Personen des jeweiligen Ortes. Die
# Ergebnisse werden zwischengespeichert, damit gleiche Orte dasselbe Objekt
# bleiben (das Laufraster wird je Grundriss nur einmal berechnet).

SITE_OFFICE = "buero"
SITE_HOME = "zuhause"
ENTRANCE_REACH = 1.4          # so nah an der Eingangstuer zaehlt als "an der Tuer"
FURNITURE_REACH = 0.9         # so nah an einem Moebel kann man es benutzen
GRID = 0.25                   # Moebel rasten auf diesem Raster ein
DOOR_CLEARANCE = 1.0          # vor und hinter Tueren bleibt so viel frei
_SITE_CACHE = {}


def incident_chance(day, rules):
    """Chance auf einen Zwischenfall an diesem Arbeitstag (gestaffelt)."""
    chance = rules.get("chance", 0)
    for step in sorted(rules.get("staffel") or [], key=lambda item: item["ab_tag"]):
        if day >= step["ab_tag"]:
            chance = step["chance"]
    return chance


def _dice(seed, day, salt):
    """Fester "Wuerfel" zwischen 0 und 1 aus Text - auf allen Geraeten gleich."""
    digest = hashlib.sha256(("%s|%s|%s" % (seed, day, salt)).encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(16 ** 12)


def is_incident(task_id, content=None):
    task = task_by_id(task_id, content)
    return bool(task and task.get("zwischenfall"))


def customer_places(content=None):
    return (content or GAME).get("kunden", {}).get("orte", [])


def customer_place(place_id, content=None):
    for place in customer_places(content):
        if place["id"] == place_id:
            return place
    return None


def open_places(state, content=None):
    """Kundenorte, die man schon besuchen kann (ab_tag erreicht)."""
    day = state.day if state is not None else 1
    return [place for place in customer_places(content) if place.get("ab_tag", 1) <= day]


def place_label(place, places):
    """Beschriftung eines Kundenorts in der Auswahl: ab drei Orten die
    Kurzform (sonst wird die Zeile auf dem Handy zu breit)."""
    return place.get("kurz", place["name"]) if len(places) > 2 else place["name"]


def site_name(site_id, content=None, state=None):
    content = content or GAME
    if site_id == SITE_OFFICE:
        if state is not None and state.firm:
            return state.firm["name"]
        return content["gebaeude"]["firma"]
    if site_id == SITE_HOME:
        return "Zuhause"
    place = customer_place(site_id, content)
    return place["name"] if place else site_id


def task_site(task, content=None):
    """Wo ein Auftrag erledigt wird: "ort" des Auftrags oder der Ort der
    Person, die ihn stellt."""
    if task.get("ort"):
        return task["ort"]
    person = colleague(task["auftraggeber"], content)
    return (person or {}).get("ort", SITE_OFFICE)


def _deco_visible(deco, solved):
    """Einrichtung, die erst nach (ab_aufgabe) oder nur bis zu (bis_aufgabe)
    einem erledigten Auftrag da ist - so waechst z.B. der neue Bahnhof mit."""
    if deco.get("ab_aufgabe") and deco["ab_aufgabe"] not in solved:
        return False
    if deco.get("bis_aufgabe") and deco["bis_aufgabe"] in solved:
        return False
    return True


def _conditional_tasks(building):
    tasks = set()
    decos = [d for item in building["raeume"] for d in item.get("deko", [])]
    decos += building.get("flur", {}).get("deko", [])
    for deco in decos:
        for key in ("ab_aufgabe", "bis_aufgabe"):
            if deco.get(key):
                tasks.add(deco[key])
    return tasks


def _visible_building(building, solved):
    """Grundriss mit den gerade sichtbaren Einrichtungsgegenstaenden."""
    relevant = _conditional_tasks(building)
    if not relevant:
        return building
    key = ("sichtbar", id(building), frozenset(relevant & set(solved)))
    cached = _SITE_CACHE.get(key)
    if cached and cached[0] is building:
        return cached[1]
    result = copy.deepcopy(building)
    for item in result["raeume"]:
        item["deko"] = [d for d in item.get("deko", []) if _deco_visible(d, solved)]
    hall = result.get("flur", {})
    hall["deko"] = [d for d in hall.get("deko", []) if _deco_visible(d, solved)]
    _SITE_CACHE[key] = (building, result)
    return result


def people_at_site(site_id, state=None, content=None):
    """Personen an einem Ort mit ihrem aktuellen Platz. Wer einen offenen
    Auftrag mit "stelle" hat, wartet dort (z.B. Petra neben dem kaputten
    Automaten oder Ulla im Technikraum des neuen Bahnhofs)."""
    content = content or GAME
    if site_id == SITE_OFFICE and state is not None and state.firm:
        return firm_people(state, content)
    day = state.day if state is not None else None
    waiting = {}
    if state is not None:
        for task in state.open_tickets():
            if task.get("stelle") and task["auftraggeber"] not in waiting:
                waiting[task["auftraggeber"]] = (task_site(task, content), task["stelle"])
    result = []
    for person in all_people(content):
        if day is not None and not person_present(person, day):
            continue
        where, spot = waiting.get(person["id"], (person.get("ort", SITE_OFFICE),
                                                  person.get("platz")))
        if where == site_id and spot:
            result.append(dict(person, platz=[float(spot[0]), float(spot[1])]))
    return result


def site_content(site_id, state=None, content=None):
    """Inhalte (wie GAME) fuer einen Ort: Buero, Kundenort oder Zuhause."""
    content = content or GAME
    if site_id == SITE_HOME:
        return home_content(state, content)
    if site_id == SITE_OFFICE and state is not None and state.firm:
        base = firm_building(state, content)
    elif site_id == SITE_OFFICE:
        base = content["gebaeude"]
    else:
        place = customer_place(site_id, content)
        if place is None:
            raise ValueError("Unbekannter Ort: %s" % site_id)
        base = place["gebaeude"]
    solved = state.solved if state is not None else set()
    building = _visible_building(base, solved)
    people = people_at_site(site_id, state, content)
    key = ("ort", site_id, id(content), id(building),
           tuple((p["id"], tuple(p["platz"])) for p in people))
    cached = _SITE_CACHE.get(key)
    if cached and cached[0] is building:
        return cached[1]
    if len(_SITE_CACHE) > 60:
        _SITE_CACHE.clear()
    result = dict(content, gebaeude=building, kollegen=people, ort=site_id)
    _SITE_CACHE[key] = (building, result)
    return result


def at_entrance(position, content=None):
    """Steht die Figur an der Eingangstuer (links im Flur)?"""
    hall = (content or GAME)["gebaeude"]["flur"]
    entrance = hall["eingang"]
    return position[0] <= ENTRANCE_REACH and \
        entrance["von"] - 0.6 <= position[1] <= entrance["bis"] + 0.6


def place_message(site_id, position, person, state, content=None):
    """Text und Knoepfe unter der Grossansicht eines Ortes:
    (Ueberschrift, Text, [(aktion, Beschriftung), ...]).

    Aktionen: "auftrag:<id>", "feierabend", "buero", "zuhause", "kunde",
    "lernen", "schlafen" - die Oberflaeche fuehrt sie aus."""
    content = content or site_content(site_id, state)
    if site_id == SITE_HOME:
        return home_message(position, state, content)
    quests = state.quests(site_id)
    actions = []
    if person:
        title, text = office_message(position, person, quests, content, state)
        tasks = quests.get(person["id"]) or []
        if tasks:
            actions.append(("auftrag:%s" % tasks[0]["id"], "Auftrag annehmen"))
        return title, text, actions
    if at_entrance(position, content):
        if site_id == SITE_OFFICE:
            if state.can_end_day():
                return ("Eingangstür", "Für heute ist alles erledigt. Zeit für den "
                        "Feierabend!", [("feierabend", "Feierabend machen")])
            left = len(state.open_tickets())
            return ("Eingangstür", "Noch nicht: %s offen." % (
                "1 Ticket ist" if left == 1 else "%d Tickets sind" % left), [])
        return ("Ausgang", "Hier geht es zurück ins Büro.", [("buero", "Zurück ins Büro")])
    title, text = office_message(position, person, quests, content, state)
    return title, text, actions


# ----------------------------------------------------------------------------
#  Wohnung
# ----------------------------------------------------------------------------

FLOOR_KINDS = [("parkett", "Parkett"), ("teppichboden", "Teppich"),
               ("fliesen", "Fliesen"), ("beton", "Estrich")]
FLOOR_COLORS = [("violett", "Violett"), ("cyan", "Cyan"), ("gruen", "Grün"),
                ("orange", "Orange"), ("pink", "Pink"), ("grau", "Grau")]
_FLOOR_ACCENT = {"violett": C["purple"], "cyan": C["cyan"], "gruen": C["green"],
                 "orange": C["orange"], "pink": C["pink"], "grau": "#FFFFFF"}


def floor_color(key):
    """Bodenfarbe in der Wohnung - wie die Raeume im Buero aus der Palette
    abgeleitet, damit alles zusammenpasst."""
    accent = _FLOOR_ACCENT.get(key, C["purple"])
    return mix(C["card_alt"], accent, 0.07 if key == "grau" else 0.16)


def apartment(home_id, content=None):
    for item in (content or GAME)["wohnungen"]["wohnungen"]:
        if item["id"] == home_id:
            return item
    return None


def furniture_item(item_id, content=None):
    for item in (content or GAME)["wohnungen"]["moebel"]:
        if item["id"] == item_id:
            return item
    return None


def shop_items(content=None):
    return [item for item in (content or GAME)["wohnungen"]["moebel"]
            if item.get("laden", True)]


def furniture_size(item, turn):
    return (item["h"], item["w"]) if int(turn) % 2 else (item["w"], item["h"])


def home_layout(state, content=None):
    """Aktuelle Einrichtung der Wohnung: {"moebel": {stueck: [x, y, dreh]},
    "boeden": {raum: [art, farbe]}}. Nur Moebel, die man noch besitzt."""
    content = content or GAME
    flat = apartment(state.home_id, content)
    data = state.layouts.get(state.home_id)
    if data is None:
        data = flat.get("einrichtung") or {}
    placed = {key: list(value) for key, value in (data.get("moebel") or {}).items()
              if key in state.furniture}
    floors = {key: list(value) for key, value in (data.get("boeden") or {}).items()}
    return {"moebel": placed, "boeden": floors}


def placed_furniture(state, layout=None, content=None):
    """Aufgestellte Moebel als Liste von Einrichtungs-Eintraegen (wie deko)."""
    content = content or GAME
    layout = layout or home_layout(state, content)
    result = []
    for key, (x, y, turn) in sorted(layout["moebel"].items()):
        item = furniture_item(state.furniture.get(key), content)
        if not item:
            continue
        w, h = furniture_size(item, turn)
        result.append({"typ": item["typ"], "x": float(x), "y": float(y), "w": w, "h": h,
                       "dreh": int(turn), "stueck": key, "moebel": item["id"],
                       "blick": item.get("blick", "s")})
    return result


def boxed_furniture(state, layout=None, content=None):
    """Moebel im Umzugskarton (gekauft, aber nicht aufgestellt): [(stueck, moebel)]."""
    layout = layout or home_layout(state, content)
    return sorted(((key, item) for key, item in state.furniture.items()
                   if key not in layout["moebel"]), key=lambda row: row[0])


def _overlap(a, b):
    return a["x"] < b["x"] + b["w"] - 1e-6 and b["x"] < a["x"] + a["w"] - 1e-6 and \
        a["y"] < b["y"] + b["h"] - 1e-6 and b["y"] < a["y"] + a["h"] - 1e-6


def _areas(building):
    """Raeume und Flur als Flaechen (x, y, w, h, name)."""
    hall = building["flur"]
    areas = [dict(item) for item in building["raeume"]]
    areas.append({"id": "flur", "name": hall.get("name", "Flur"), "x": 0, "y": hall["y"],
                  "w": building["breite"], "h": hall["h"]})
    return areas


def _door_zones(building):
    """Flaechen vor und hinter jeder Tuer, die frei bleiben muessen."""
    zones = []
    hall = building["flur"]
    for item in building["raeume"]:
        door = item.get("tuer")
        if not door:
            continue
        side = door_side(item, {"gebaeude": building})
        span_a, span_b = door["von"], door["bis"]
        if side in ("s", "n"):
            wall_y = item["y"] + item["h"] if side == "s" else item["y"]
            zones.append({"x": span_a, "y": wall_y - DOOR_CLEARANCE, "w": span_b - span_a,
                          "h": 2 * DOOR_CLEARANCE})
        else:
            wall_x = item["x"] if side == "w" else item["x"] + item["w"]
            zones.append({"x": wall_x - DOOR_CLEARANCE, "y": span_a, "w": 2 * DOOR_CLEARANCE,
                          "h": span_b - span_a})
    entrance = hall["eingang"]
    zones.append({"x": 0, "y": entrance["von"], "w": DOOR_CLEARANCE * 1.5,
                  "h": entrance["bis"] - entrance["von"]})
    return zones


def snap(value):
    return round(float(value) / GRID) * GRID


def placement_problem(state, piece, item_id, x, y, turn, layout=None, content=None):
    """Warum ein Moebel hier nicht stehen kann - leerer Text = passt."""
    content = content or GAME
    item = furniture_item(item_id, content)
    if item is None:
        return "Dieses Möbelstück gibt es nicht."
    flat = apartment(state.home_id, content)
    building = flat["gebaeude"]
    w, h = furniture_size(item, turn)
    box = {"x": float(x), "y": float(y), "w": w, "h": h}
    if not any(_inside(box, area) for area in _areas(building)):
        return "%s passt hier nicht hin: Es muss ganz in einem Raum stehen." % item["name"]
    free_kind = item["typ"] in WALK_FREE
    if not free_kind:
        for zone in _door_zones(building):
            if _overlap(box, zone):
                return "%s würde eine Tür versperren." % item["name"]
    others = [d for area in building["raeume"] for d in area.get("deko", [])]
    others += building["flur"].get("deko", [])
    layout = layout or home_layout(state, content)
    for other in placed_furniture(state, layout, content):
        if other["stueck"] != piece:
            others.append(other)
    for other in others:
        other_free = other["typ"] in WALK_FREE
        if free_kind != other_free and (free_kind or other_free):
            continue       # Teppich unter Moebeln ist erlaubt
        if _overlap(box, other):
            name = furniture_item(other.get("moebel"), content)
            return "%s stößt an %s." % (item["name"], name["name"] if name else
                                       "die Einrichtung")
    return ""


def home_building(state, content=None):
    """Grundriss der Wohnung mit Boeden und Moebeln aus der Einrichtung."""
    content = content or GAME
    flat = apartment(state.home_id, content)
    layout = home_layout(state, content)
    boxed = boxed_furniture(state, layout, content)
    signature = json.dumps([state.home_id, layout, len(boxed)], sort_keys=True)
    key = ("wohnung", id(content), signature)
    cached = _SITE_CACHE.get(key)
    if cached:
        return cached[1]
    building = copy.deepcopy(flat["gebaeude"])
    for item in building["raeume"]:
        kind, color = layout["boeden"].get(item["id"], [None, None])
        if kind in dict(FLOOR_KINDS):
            item["boden"] = kind
        if color in _FLOOR_ACCENT:
            item["bodenfarbe"] = floor_color(color)
    areas = building["raeume"]
    # Teppiche zuerst, damit sie unter den Moebeln liegen
    for deco in sorted(placed_furniture(state, layout, content),
                       key=lambda item: item["typ"] not in WALK_FREE):
        target = next((area for area in areas if _inside(deco, area)), None)
        if target is None:
            building["flur"].setdefault("deko", []).append(deco)
        else:
            target.setdefault("deko", []).append(deco)
    if boxed and flat.get("kartons"):
        x, y, w, h = flat["kartons"]
        target = next((area for area in areas if _inside(
            {"x": x, "y": y, "w": w, "h": h}, area)), None)
        pile = {"typ": "kartons", "x": x, "y": y, "w": w, "h": h, "umzug": True}
        (target.setdefault("deko", []) if target else
         building["flur"].setdefault("deko", [])).append(pile)
    if len(_SITE_CACHE) > 60:
        _SITE_CACHE.clear()
    _SITE_CACHE[key] = (None, building)
    return building


def home_content(state, content=None):
    content = content or GAME
    building = home_building(state, content)
    key = ("zuhause", id(building))
    cached = _SITE_CACHE.get(key)
    if cached and cached[0] is building:
        return cached[1]
    result = dict(content, gebaeude=building, kollegen=[], ort=SITE_HOME)
    _SITE_CACHE[key] = (building, result)
    return result


def furniture_at(state, x, y, content=None):
    """Aufgestelltes Moebel an der Stelle (x, y) oder None (oberstes zuerst,
    ein Teppich zaehlt nur, wenn nichts darauf steht)."""
    hits = [item for item in placed_furniture(state, content=content)
            if item["x"] <= x <= item["x"] + item["w"] and
            item["y"] <= y <= item["y"] + item["h"]]
    hits.sort(key=lambda item: item["typ"] in WALK_FREE)
    return hits[0] if hits else None


def furniture_near(state, position, content=None):
    """Benutzbares Moebel in Reichweite der Figur (Bett, Schreibtisch ...)."""
    best, best_dist = None, None
    for item in placed_furniture(state, content=content):
        info = furniture_item(item["moebel"], content)
        if not info or not (info.get("aktion") or info.get("texte")):
            continue
        dx = max(item["x"] - position[0], 0, position[0] - item["x"] - item["w"])
        dy = max(item["y"] - position[1], 0, position[1] - item["y"] - item["h"])
        dist = math.hypot(dx, dy)
        if dist <= FURNITURE_REACH and (best_dist is None or dist < best_dist):
            best, best_dist = item, dist
    return best


def home_message(position, state, content=None):
    """Text und Knoepfe in der Wohnung (siehe place_message)."""
    content = content or home_content(state)
    flat = apartment(state.home_id)
    if at_entrance(position, content):
        return ("Wohnungstür", "Von hier geht es zur Arbeit.",
                [("buero", "Zur Arbeit")])
    item = furniture_near(state, position)
    if item:
        info = furniture_item(item["moebel"])
        texts = info.get("texte") or []
        text = texts[int(_dice(state.first_event or "", state.day, item["stueck"]) *
                         len(texts))] if texts else ""
        actions = []
        if info.get("aktion") == "lernen":
            actions.append(("lernen", "Lernen"))
            text = text or "Hier lernt es sich in Ruhe."
        elif info.get("aktion") == "schlafen":
            actions.append(("schlafen", "Schlafen"))
            text = text or "Ein gemütliches Plätzchen."
        return info["name"], text, actions
    area = next((a for a in _areas(content["gebaeude"])
                 if a["x"] <= position[0] < a["x"] + a["w"] and
                 a["y"] <= position[1] < a["y"] + a["h"]), None)
    where = "Du bist im Raum %s." % area["name"] if area and area["id"] != "flur" else \
        "Du bist in der Diele."
    return flat["name"], where + " Geh zum Bett, zum Schreibtisch oder zur Wohnungstür.", []


def sleep_text(state, content=None):
    content = content or GAME
    texts = content["story"].get("schlafen") or ["Gute Nacht!"]
    if isinstance(texts, str):
        return texts
    return texts[state.day % len(texts)]


# ----------------------------------------------------------------------------
#  Miete (ab 0.31)
# ----------------------------------------------------------------------------
#
# Schalter in den Optionen: Einmalzahlung (Standard) oder Miete. Er liegt
# lokal je Geraet in einstellungen.json und wirkt nur auf den naechsten
# Umzug; ein laufender Mietvertrag gilt bis zum naechsten Umzug weiter.

RENT_SETTING = "spiel_miete"
# Auswahl in den Optionen und Untertitel der Karte "Wohnung"
RENT_CHOICES = [("einmal", "Einmalzahlung"), ("miete", "Miete")]
HOME_SUBTITLE = {False: "Größer wohnen kostet einmalig",
                 True: "Größer wohnen: Kaution und Miete je Arbeitstag"}
RENT_HELP = ("Gilt für den nächsten Umzug im Spiel. Einmalzahlung: Die Wohnung wird "
             "gekauft. Miete: nur eine Kaution (%d %% des Kaufpreises), dafür geht "
             "jeden Arbeitstag die Miete vom Spielgeld ab. Ein laufender Mietvertrag "
             "gilt bis zum nächsten Umzug. Die Einstellung gilt nur für dieses Gerät.")


def rent_mode():
    """Ist in den Optionen dieses Geraets "Miete" gewaehlt?"""
    import fisi_update
    return bool(fisi_update.load_settings().get(RENT_SETTING, False))


def set_rent_mode(flag):
    import fisi_update
    settings = fisi_update.load_settings()
    settings[RENT_SETTING] = bool(flag)
    return fisi_update.save_settings(settings)


def rent_terms(home, content=None):
    """(Miete pro Arbeitstag, Kaution) einer Wohnung laut balancing.json."""
    rules = (content or GAME)["balancing"]["miete"]
    rent = int(rules["pro_tag"].get(home["id"], 0))
    deposit = int(round(home.get("preis", 0) * rules["kaution_anteil"]))
    return rent, deposit


def move_offer(state, home, rent, content=None):
    """Was ein Umzug kostet: {"kosten" (Kaufpreis oder Kaution), "miete"
    (pro Arbeitstag, 0 beim Kauf), "zurueck" (Kaution der alten Wohnung),
    "fehlt" (0 = bezahlbar)}."""
    if rent:
        per_day, cost = rent_terms(home, content)
    else:
        per_day, cost = 0, int(home.get("preis", 0))
    back = state.deposit
    missing = max(0, cost - max(0, state.money + back))
    return {"kosten": cost, "miete": per_day, "zurueck": back, "fehlt": missing}


def _whole_euro(value):
    return "%s €" % "{:,.0f}".format(value).replace(",", ".")


def move_texts(state, home, rent, content=None):
    """Anzeige fuer einen Umzug (PC und Handy gleich): (Preiszeile,
    Rueckfrage vor dem Umzug)."""
    offer = move_offer(state, home, rent, content)
    if rent:
        price = "Kaution %s · Miete %s/Tag" % (_whole_euro(offer["kosten"]),
                                              _whole_euro(offer["miete"]))
        question = ("In die Wohnung „%s“ ziehen? Kaution %s, danach %s Miete pro "
                    "Arbeitstag." % (home["name"], _whole_euro(offer["kosten"]),
                                     _whole_euro(offer["miete"])))
    else:
        price = _whole_euro(offer["kosten"])
        question = "Für %s in die Wohnung „%s“ umziehen?" % (price, home["name"])
    if offer["zurueck"]:
        question += (" Die Kaution von %s für deine jetzige Wohnung bekommst du zurück."
                     % _whole_euro(offer["zurueck"]))
    return price, question + " Alle Möbel kommen dabei in Umzugskartons."


def rent_text(state):
    """Zeile zur jetzigen Wohnung: gemietet oder gekauft (leer = Startwohnung)."""
    if state.rent:
        return "Zur Miete: %s pro Arbeitstag, Kaution %s hinterlegt" % (
            _whole_euro(state.rent), _whole_euro(state.deposit))
    return ""


def day_end_money_text(payload):
    """ "Gehalt: +190 €." bzw. "Gehalt: +190 €. Miete: -140 €." """
    if payload.get("firma"):
        text = firm_day_text(payload["firma"])
    else:
        text = "Gehalt: +%s." % _whole_euro(payload.get("gehalt", 0))
    if payload.get("miete"):
        text += " Miete: -%s." % _whole_euro(payload["miete"])
    return text


def moves_available(state, content=None):
    """Wohnungen, in die man umziehen kann (teurer als die jetzige)."""
    content = content or GAME
    current = apartment(state.home_id, content)
    return [item for item in content["wohnungen"]["wohnungen"]
            if item.get("preis", 0) > current.get("preis", 0)]


# ----------------------------------------------------------------------------
#  Story, Reaktionen
# ----------------------------------------------------------------------------

def morning_text(day, content=None, state=None):
    """Szene zum Start eines Arbeitstags (oder leerer Text). Mit state kommen
    die Story-Momente der eigenen Firma dazu (Kollegen, die wechseln wollen)."""
    text = ((content or GAME)["story"].get("tage") or {}).get(str(day), "")
    if state is not None and state.firm:
        news = switch_news(state, content)
        text = "\n\n".join(part for part in (text, news) if part)
    return text


def day_end_text(day, content=None, firm=False):
    """Szene zum Feierabend. Mit eigener Firma (ab 0.34) eigene Texte - dort
    gibt es kein Gehalt von Bitweiche mehr."""
    if firm and (content or GAME).get("firma", {}).get("feierabend"):
        texts = (content or GAME)["firma"]["feierabend"]
        return texts[(day - 1) % len(texts)]
    texts = (content or GAME)["story"].get("feierabend") or \
        [(content or GAME)["story"]["tagesende"]]
    if isinstance(texts, str):
        return texts
    return texts[(day - 1) % len(texts)]


def reaction_text(task, payload, content=None):
    """Kurzer Satz der Person, die den Auftrag gestellt hat."""
    person = colleague(task["auftraggeber"], content)
    if not person or task.get("falschlieferung"):
        return ""
    texts = (person.get("reaktionen") or {}).get("richtig" if payload["richtig"]
                                                  else "falsch") or []
    if not texts:
        return ""
    text = texts[int(_dice(task["id"], payload.get("tag", 0), "reaktion") * len(texts))]
    return "%s: „%s“" % (short_name(person), text)


def result_text(task, payload, available=None, content=None):
    """Rueckmeldung nach dem Bearbeiten eines Tickets."""
    lines = []
    reaction = reaction_text(task, payload, content)
    if payload["richtig"]:
        lines.append("Richtig gelöst!")
    elif task["typ"] == "zuordnung":
        lines.append("Leider nicht ganz: %d Zuordnung(en) stimmen nicht."
                     % payload["fehler"])
    elif task["typ"] == "terminal":
        mistakes = payload.get("fehlgriffe", 0)
        allowed = _allowed_mistakes(task, content)
        if payload.get("gefahr"):
            lines.append("Leider nicht ganz: Ein gefährlicher Befehl war dabei.")
        elif mistakes > allowed:
            lines.append("Leider nicht ganz: %d Fehlgriffe, erlaubt %s %d." % (
                mistakes, "ist" if allowed == 1 else "sind", allowed))
        else:
            lines.append("Leider nicht ganz: Nicht alle Schritte sind erledigt.")
        lines += ["• " + text for text in payload.get("probleme") or []]
    elif task["typ"] in ("diagnose", "wartung"):
        lines.append("Leider nicht ganz.")
        lines += ["• " + text for text in payload.get("probleme") or []]
        lines.append(solution_text(task, available, content))
    elif task["typ"] == "formular":
        count = payload["fehler"]
        lines.append("Leider nicht ganz: %s." % (
            "1 Feld stimmt nicht" if count == 1 else "%d Felder stimmen nicht" % count))
        lines += ["• " + text for text in payload.get("probleme") or []]
    elif task["typ"] in PROBLEM_TYPES:
        count = payload["fehler"]
        lines.append("Leider nicht ganz: %s gefunden." % (
            "1 Problem" if count == 1 else "%d Probleme" % count))
        lines += ["• " + text for text in payload.get("probleme") or []]
        hint = solution_text(task, available, content)
        if hint:
            lines.append(hint)
    else:
        lines.append("Leider falsch. Richtig wäre: %s" % task["antwort"])
    if payload["richtig"] and task["typ"] == "terminal" and payload.get("fehlgriffe"):
        lines.append("Ein Fehlgriff war dabei, das ist noch erlaubt.")
    if payload["richtig"] and task["typ"] == "diagnose":
        count = payload.get("pruefungen", 0)
        if payload.get("systematisch"):
            lines.append("Systematisch vorgegangen: Fehler mit %d Prüfung%s gefunden."
                         % (count, "" if count == 1 else "en"))
        else:
            lines.append("Fehler gefunden mit %d Prüfung%s, %d hätten gereicht." % (
                count, "" if count == 1 else "en", task["ziel_pruefungen"]))
    if payload["richtig"] and task["typ"] == "diagnose" and payload.get("aus_lager"):
        lines.append("Ersatzteil aus dem Lager eingebaut: %s."
                     % part(payload["aus_lager"][0], content)["name"])
    if payload["richtig"] and task.get("austausch"):
        lines.append("Funktionstest: %s" % task["austausch"]["test"])
    if payload["richtig"] and task["typ"] == "wartung":
        issues = sum(1 for item in task["pruefpunkte"] if item.get("auffaellig"))
        follow = [other for other in (content or GAME)["aufgaben"]
                  if other.get("nach") == task["id"]]
        if not issues:
            lines.append("Wartung dokumentiert: alles in Ordnung.")
        else:
            lines.append("Wartung dokumentiert: %s.%s" % (
                "1 Auffälligkeit" if issues == 1 else "%d Auffälligkeiten" % issues,
                " Folgeauftrag ab dem nächsten Arbeitstag: %s." % follow[0]["titel"]
                if follow else ""))
    if payload.get("lieferung"):
        last = max(item["ankunft"] for item in payload["lieferung"])
        if payload.get("fehllieferung"):
            lines.append("Die Bestellung über %d € geht trotzdem raus und kommt an "
                         "Arbeitstag %d. Dann meldet sich Rainer im Lager wegen der "
                         "falschen Ware." % (payload.get("kosten", 0), last))
        else:
            lines.append("Bestellt für %d €. Die Ware kommt an Arbeitstag %d."
                         % (payload.get("kosten", 0), last))
    if payload.get("bonus_verloren"):
        lines.append("Kein Spar-Bonus: Der ist durch die Falschlieferung verloren.")
    if payload.get("falschlieferung") and payload["richtig"]:
        back = payload.get("ruecksendung") or {}
        if back:
            lines.append("Zurückgeschickt: %s." % ", ".join(
                "%d × %s" % (count, part(part_id, content)["name"])
                for part_id, count in back.items()))
        lines.append("Rücksendekosten: -%d €. Die Bestellung kommt jetzt wieder, dann "
                     "ohne Spar-Bonus." % payload.get("ruecksendekosten", 0))
    if payload.get("ersparnis_bonus"):
        lines.append("Sparsam bestellt: +%d € Bonus." % payload["ersparnis_bonus"])
    if payload.get("aus_lager") and task["typ"] == "rack":
        lines.append("Aus dem Lager eingebaut: %s." % ", ".join(
            part(item, content)["name"] for item in payload["aus_lager"]))
    if reaction:
        lines.append(reaction)
    money = payload["geld"]
    lines.append("%s%d € Spielgeld" % ("+" if money >= 0 else "", money))
    names = dict(AXES)
    for key, value in payload["reputation"].items():
        lines.append("%s%d %s" % ("+" if value >= 0 else "", value, names.get(key, key)))
    if payload["richtig"] and not payload["hilfe"]:
        lines.append("Bonus: ohne Hilfe gelöst.")
    if payload["unter_niveau"] and not payload["richtig"]:
        lines.append("Doppelter Reputationsverlust, weil dir hier noch Wissen fehlt.")
    return "\n".join(lines)
