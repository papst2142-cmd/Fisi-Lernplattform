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
    CATEGORY_KEYS, CATEGORY_SHORT, CONTENT_DIR, PROJEKTARBEITEN, TOPIC_CAT, TOPIC_NAME,
    TOPIC_ORDER, TOPIC_SHORT, TOPICS, ipv4_values, raid_values, search_content, topic_totals,
)
from fisi_theme import C, CATEGORY_COLOR, mix

GAME_DIR = os.path.join(CONTENT_DIR, "spiel")

# Kurzname -> langer Name des Fachbereichs (wie in der Datenbank)
CAT_NAME = dict(CATEGORY_KEYS)
CAT_KEY = {name: key for key, name in CATEGORY_KEYS.items()}
CAT_ORDER = list(CATEGORY_KEYS)
# Themen je Fachbereich (Kurzname -> Themen-Kennungen, ab 0.37)
CAT_TOPICS = {key: list(TOPICS.get(name, [])) for key, name in CATEGORY_KEYS.items()}

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
# Kredite der eigenen Firma (ab 0.41). Raten, geplatzte Raten und Mahnstufen
# werden beim Feierabend aus diesen Ereignissen berechnet, nicht gespeichert.
EV_LOAN = "kredit_aufgenommen"
EV_LOAN_REPAID = "kredit_abgeloest"
# Werbung und Zertifizierungen (ab 0.42). Die Umsatzsteuer und die laufenden
# Werbekosten rechnet der Spielstand beim Feierabend selbst aus.
EV_ADS = "werbung_gebucht"
EV_ADS_STOP = "werbung_beendet"
EV_CERT = "zertifizierung"
# Personal (ab 0.43): Antworten auf Urlaubsanfragen und Entscheidungen bei
# Konflikten. Krankheit, Urlaubsanfragen, Konflikte und Kuendigungen stehen
# im Feierabend (firma.personal), die Stimmung rechnet der Spielstand aus.
EV_VACATION_OK = "urlaub_genehmigt"
EV_VACATION_NO = "urlaub_abgelehnt"
EV_CONFLICT = "konflikt_ereignis"
# Rivalitaet (ab 0.44): Antwort auf ein Rueckhol-Angebot eines Mitbewerbers.
# Konjunktur, Trends und Gegenwind rechnet der Spielstand selbst aus.
EV_RECALL = "rueckhol_angebot"
# Zweiter Standort (ab 0.45): Eroeffnung (stufe 1, mit dem frei gewaehlten
# Namen) und jeder weitere Ausbau der Filiale; Versetzen zwischen den Standorten
EV_BRANCH = "filiale_ausgebaut"
EV_TRANSFER = "mitarbeiter_versetzt"
# Erfolge (ab 0.46): Abzeichen-Stufe erreicht. Berechnet wird alles aus dem
# Spielstand, das Ereignis haelt nur fest, wann (und dass der Meilenstein-
# Moment schon gezeigt wurde - auch auf dem anderen Geraet)
EV_ACHIEVEMENT = "erfolg_freigeschaltet"
FIRM_EVENTS = (EV_FOUNDED, EV_HIRED, EV_FIRED, EV_TRAINING, EV_EXPAND, EV_OFFER_WON,
               EV_OFFER_LOST, EV_DELEGATED, EV_PROJECT_WON, EV_PROJECT_LOST,
               EV_PROJECT_TEAM, EV_ROOM, EV_LOAN, EV_LOAN_REPAID, EV_ADS, EV_ADS_STOP,
               EV_CERT, EV_VACATION_OK, EV_VACATION_NO, EV_CONFLICT, EV_RECALL,
               EV_BRANCH, EV_TRANSFER)

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
        # Weltkarte mit Orten und Gebaeude-Aussenmodellen (ab 0.45)
        "orte": read("orte") if os.path.exists(os.path.join(folder, "orte.json")) else {},
        # Erfolge und Bestwerte (ab 0.46)
        "erfolge": read("erfolge") if os.path.exists(os.path.join(folder, "erfolge.json"))
        else {},
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
    for stage in ((content.get("firma") or {}).get("filiale") or {}).get("stufen", [])[-1:]:
        site_rooms[SITE_BRANCH] = {item["id"] for item in stage["gebaeude"]["raeume"]}
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
    problems += _validate_loans(content)
    problems += _validate_business(content)
    problems += _validate_world(content)
    problems += _validate_achievements(content)

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
            if key not in TOPIC_CAT or not 0 <= value <= 100:
                problems.append("%s: ungueltige Anforderung %s: %s (erwartet wird ein "
                                "Thema aus inhalte/themen.json)" % (where, key, value))
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

def knowledge_from_answers(answers, coverage, params=None, keys=None):
    """Wissensstand 0-100 je Fachbereich (Kurzname) oder - mit
    keys=TOPIC_ORDER - je Thema.

    answers:  {schluessel: [True/False, ...]} - neueste Antwort zuerst
    coverage: {schluessel: Prozent der bereits bearbeiteten Inhalte}

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
    for key in keys or CAT_ORDER:
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


def topic_params(balancing=None):
    """Parameter fuer den Wissensstand je Thema: 'wissen' mit den
    Abweichungen aus 'wissen_thema'."""
    balancing = balancing or GAME["balancing"]
    params = dict(balancing["wissen"])
    params.update({key: value for key, value in (balancing.get("wissen_thema") or {}).items()
                   if not key.startswith("_")})
    return params


def topic_knowledge(db, params=None):
    """Wissensstand je Thema (ab 0.37) - gleiche Formel wie je Fachbereich,
    nur auf die Antworten und Inhalte eines Themas bezogen."""
    params = params or topic_params()
    answers = db.topic_answers(int(params["letzte_antworten"]))
    coverage = db.topic_coverage(topic_totals())
    return knowledge_from_answers(answers, coverage, params, keys=TOPIC_ORDER)


def requirement_gaps(task, levels):
    """Themen, in denen der Wissensstand unter der Anforderung liegt.
    levels: Wissensstand je Thema (topic_knowledge).
    Rueckgabe: Liste von (thema, benoetigt, vorhanden)."""
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
    parts = ["%s: %s (%d %% nötig, du hast %d %%)"
             % (CATEGORY_SHORT[TOPIC_CAT[key]], TOPIC_NAME[key], need, int(have))
             for key, need, have in gaps]
    return ("Dafür fehlt dir noch Wissen: %s. Du kannst das Ticket trotzdem "
            "bearbeiten, ein Fehler kostet dann aber doppelt Reputation. Tipp: "
            "Vorher ein paar Karteikarten %s lernen."
            % ("; ".join(parts), "zu diesem Thema" if len(gaps) == 1 else "zu diesen Themen"))


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
        # Lernen der Mitarbeiter durch Arbeit (ab 0.38)
        self.staff_gains = {}      # mitarbeiter-id -> {thema: dazugelernte Punkte}
        self.staff_routine = {}    # mitarbeiter-id -> Arbeitstage mit Routinearbeit
        self.learn_log = []        # (tag, mitarbeiter-id, thema, vorher, nachher, grund)
        self._topic_base = {}      # Zwischenspeicher: Grundwerte je Thema
        # Reise des Spielers (ab 0.39): Ansehen nach jedem Feierabend und
        # Rangwechsel (Rang ab dem folgenden Arbeitstag)
        self.day_log = []          # (tag, mittleres Ansehen)
        self.rank_log = []         # (ab tag, rang)
        self._rank_seen = balancing["raenge"][0]["name"]
        # Kredite der Firma (ab 0.41)
        self.loans = {}            # kredit-id -> Kredit mit Restschuld und Zahlungen
        self.dunning = 0           # Mahnstufe (0 = alles in Ordnung)
        self.dunning_day = 0       # Arbeitstag der letzten Aenderung der Mahnstufe
        self.loan_log = []         # (tag, art, kredit-id, daten) je Feierabend
        # Umsatzsteuer, Werbung und Zertifizierungen (ab 0.42)
        self.tax_reserve = 0       # Steuerruecklage (nicht auf dem Konto)
        self.tax_debt = 0          # nicht bezahlte Umsatzsteuer (mit Saeumnisgebuehren)
        self.tax_period = new_tax_period()   # laufender Voranmeldungszeitraum
        self.tax_days = 0          # Feierabende mit Umsatzsteuer
        self.tax_log = []          # (tag, art, daten): ruecklage, voranmeldung, ausfall ...
        self.ads = []              # gebuchte Werbung (Ereignisdaten + "ende")
        self.ad_log = []           # (tag, werbung-id, kosten) laufende Werbekosten
        self.certs = {}            # zertifizierung -> Ereignisdaten (auch laufende)
        # Personal (ab 0.43)
        self.mood = {}             # mitarbeiter-id -> Stimmung (0 bis 100)
        self.mood_low = {}         # mitarbeiter-id -> Feierabende in Folge unter "kritisch"
        self.upset = {}            # mitarbeiter-id -> verstimmt bis (ausschliesslich) Tag
        self.absences = []         # {"id", "art" (krank/urlaub), "von", "bis" (ausschl.)}
        self.personal_log = []     # (feierabend-tag, eintrag aus firma.personal)
        self.answers = {}          # urlaubsanfrage/konflikt -> Ereignisdaten der Antwort
        self.mediation_days = set()   # Arbeitstage, an denen du geschlichtet hast
        self.quit_staff = {}       # mitarbeiter-id -> Tag der eigenen Kuendigung
        self._live = False         # Feierabend mit den Regeln ab 0.43?
        # Rivalitaet (ab 0.44)
        self.leaving = {}          # mitarbeiter-id -> Tag, nach dessen Feierabend sie geht
        self.returned_staff = {}   # mitarbeiter-id -> (Tag, Mitbewerber, Name) der Rueckkehr
        self._pressure = {}        # Zwischenspeicher: Tag -> Gegenwind der Mitbewerber
        # Zweiter Standort (ab 0.45)
        self.branch = None         # {"name", "tag", "stufe"} ab der Eroeffnung
        self.staff_site = {}       # mitarbeiter-id -> SITE_BRANCH (sonst Hauptstandort)
        # Erfolge (ab 0.46)
        self.achievements = {}     # (erfolg, stufe) -> Ereignisdaten (fruehestes zaehlt)
        self.staff_peak = 0        # meiste Mitarbeiter gleichzeitig
        self.expand_days = {}      # Gebaeudestufe -> Arbeitstag des Ausbaus
        self.mood_log = []         # (tag, mittlere Stimmung) je Feierabend ab 3 Mitarbeitern
        self.dunning_peak = 0      # hoechste Mahnstufe seit der letzten 0
        self.dunning_over = []     # hoechste Mahnstufe je ueberstandenem Mahnverfahren

        for timestamp, kind, data in events:
            self.history.append((timestamp, kind, data))
            if self.first_event is None:
                self.first_event = str(timestamp)
            today = int(data.get("tag") or 0) if isinstance(data.get("tag"), int) else 0
            today = today or self.days_done + 1
            if kind in FIRM_EVENTS:
                self._apply_firm(kind, data, today)
            if kind == EV_ACHIEVEMENT:
                key = (data.get("erfolg"), int(data.get("stufe", 0) or 0))
                if key[0] and key[1] and key not in self.achievements:
                    self.achievements[key] = dict(data)
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
                # Ab 0.43 wirken Macken beim Lernen und die Stimmung aendert sich -
                # nur bei Feierabenden mit firma.personal (alte Tage bleiben, wie sie waren)
                self._live = "personal" in firm
                # Wer heute im Projekt oder in der Weiterbildung war, macht keine Routine
                busy = {person for item in self.running_projects() for person in item["team"]}
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
                    if item.get("erfolg"):
                        self._learn_from_ticket(item, today)
                    elif self._live:
                        self._mood_after_failure(item, today)
                for item in firm.get("projekte") or []:
                    if self._apply_project_day(item, today) and item.get("fertig"):
                        self._learn_from_project(item, today)
                self._learn_routine(busy, today)
                if self._live:
                    self._personal_day(today, firm.get("personal") or [])
                self._live = False
                if self.firm and len(self.staff) >= 3:
                    self.mood_log.append((today, sum(self.mood_of(staff_id) for staff_id in
                                                     self.staff) / float(len(self.staff))))
                # Ab 0.44: Wer ein Rueckhol-Angebot angenommen hat, geht nach
                # diesem Feierabend zurueck zum Mitbewerber
                for staff_id, until in list(self.leaving.items()):
                    if until <= today and staff_id in self.staff:
                        data = self.staff.pop(staff_id)
                        self.returned_staff[staff_id] = (today, self.answers.get(
                            "leaving:" + staff_id, {}).get("firma", ""), data.get("name", ""))
                        self.leaving.pop(staff_id, None)
                if self.firm:
                    # Ab 0.42: laufende Werbung, dann Kreditraten, dann Umsatzsteuer -
                    # geplatzte Zahlungen landen in derselben Mahnstufe
                    self._ads_day(today)
                    failed = self._loan_day(today)
                    if firm.get("ust"):
                        failed += self._tax_day(today)
                    self._dunning_day(today, failed)
                self.balances.append((today, self.money))
                self.start_reputation = self.mean_reputation
                self.day_log.append((today, round(self.mean_reputation, 1)))
                if self.firm is None:
                    rank = rank_for(self.mean_reputation, balancing, self.day)
                    if rank != self._rank_seen:
                        self.rank_log.append((self.day, rank))
                        self._rank_seen = rank

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
            self.staff_peak = max(self.staff_peak, len(self.staff))
            self.mood[data["id"]] = float(personal_rules(self.content)["stimmung"]["start"])
            if data.get("standort") == SITE_BRANCH:
                self.staff_site[data["id"]] = SITE_BRANCH
        elif kind == EV_FIRED:
            self.staff.pop(data.get("id"), None)
            self.staff_site.pop(data.get("id"), None)
        elif kind == EV_BRANCH:
            number = int(data.get("stufe", 0))
            current = self.branch["stufe"] if self.branch else 0
            # Doppelt (zwei Geraete) oder uebersprungene Stufe: zaehlt nicht
            if number == current + 1 and branch_stage(number, self.content):
                if self.branch is None:
                    self.branch = {"name": data.get("name") or branch_rules(
                        self.content).get("name_vorschlag", "Filiale"),
                        "tag": int(data.get("tag", day)), "stufe": 1}
                else:
                    self.branch["stufe"] = number
                self.money += int(data.get("geld", 0))
                self._book(day, BOOK_BUILDING, data.get("geld", 0))
        elif kind == EV_TRANSFER and data.get("id") in self.staff:
            if data.get("standort") == SITE_BRANCH:
                self.staff_site[data["id"]] = SITE_BRANCH
            else:
                self.staff_site.pop(data["id"], None)
        elif kind in (EV_VACATION_OK, EV_VACATION_NO, EV_CONFLICT, EV_RECALL):
            self._apply_decision(kind, data, day)
        elif kind == EV_TRAINING and data.get("id") in self.staff:
            self.trainings.append(dict(data))
            self.money += int(data.get("geld", 0))
            self._book(day, BOOK_TRAINING, data.get("geld", 0))
        elif kind == EV_EXPAND and int(data.get("stufe", 0)) == self.firm["stufe"] + 1:
            self.firm["stufe"] += 1
            self.expand_days[self.firm["stufe"]] = day
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
        elif kind == EV_LOAN and data.get("kredit") and data["kredit"] not in self.loans:
            # Doppelt (zwei Geraete gleichzeitig) zaehlt nur einmal
            amount = int(data.get("summe", 0))
            self.loans[data["kredit"]] = {
                "id": data["kredit"], "name": data.get("name") or "Kredit",
                "paket": data.get("paket", ""), "summe": amount,
                "laufzeit": int(data.get("laufzeit", 0)), "zins": float(data.get("zins", 0)),
                "rate": int(data.get("rate", 0)), "tag": int(data.get("tag", day)),
                "rest": amount, "zins_offen": 0, "gebuehren": 0, "raten": 0,
                "ausfaelle": 0, "bezahlt_zins": 0, "bezahlt_tilgung": 0,
                "bezahlt_gebuehren": 0, "ende": None, "ende_art": ""}
            self.money += amount
            self._book(day, BOOK_LOAN, amount)
            self.loan_log.append((day, "aufgenommen", data["kredit"], dict(data)))
        elif kind == EV_LOAN_REPAID and data.get("kredit") in self.loans:
            loan = self.loans[data["kredit"]]
            if loan["ende"] is not None:
                return
            payoff = loan_payoff(loan, self.content)
            self.money -= payoff["gesamt"]
            self._book(day, BOOK_LOAN_REPAY, -payoff["tilgung"])
            self._book(day, BOOK_LOAN_INTEREST, -payoff["zinsen"])
            self._book(day, BOOK_LOAN_FEES, -payoff["gebuehren"])
            loan["bezahlt_tilgung"] += payoff["tilgung"]
            loan["bezahlt_zins"] += payoff["zinsen"]
            loan["bezahlt_gebuehren"] += payoff["gebuehren"]
            loan.update(rest=0, zins_offen=0, gebuehren=0, ende=day, ende_art="abgeloest")
            self.loan_log.append((day, "abgeloest", loan["id"], payoff))
        elif kind == EV_ADS and data.get("werbung"):
            # Doppelt (zwei Geraete) oder schon aktiv: zaehlt nicht
            if ad_form(data["werbung"], self.content) and \
                    not self.ad_booking(data["werbung"], int(data.get("tag", day))):
                self.ads.append(dict(data, ende=None))
                self.money += int(data.get("geld", 0))
                self._book(day, BOOK_MARKETING, data.get("geld", 0))
        elif kind == EV_ADS_STOP:
            booking = self.ad_booking(data.get("werbung"), int(data.get("tag", day)))
            if booking and booking.get("art") == AD_RUNNING:
                booking["ende"] = int(data.get("tag", day))
        elif kind == EV_CERT and data.get("zert") and data["zert"] not in self.certs:
            if certificate(data["zert"], self.content):
                self.certs[data["zert"]] = dict(data)
                self.money += int(data.get("geld", 0))
                self._book(day, BOOK_CERT, data.get("geld", 0))
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
            return False
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
        return True

    # -- Kredite (ab 0.41) -------------------------------------------------------

    def _loan_day(self, day):
        """Feierabend: Fuer jeden laufenden Kredit fallen die Zinsen des Tages
        an und die Rate wird abgebucht. Reicht das Konto nicht, platzt sie -
        zurueck kommt die Liste der geplatzten Zahlungen fuer _dunning_day."""
        failed = []
        for loan in self.running_loans():
            if loan["tag"] > day:
                continue
            loan["zins_offen"] += int(round(loan["rest"] * day_interest(
                loan_interest(loan, self.dunning, self.content), self.content)))
            due = min(loan["rate"], loan["rest"] + loan["zins_offen"] + loan["gebuehren"])
            if self.money >= due:
                fees = min(due, loan["gebuehren"])
                interest = min(due - fees, loan["zins_offen"])
                repay = due - fees - interest
                loan["gebuehren"] -= fees
                loan["zins_offen"] -= interest
                loan["rest"] -= repay
                loan["raten"] += 1
                loan["bezahlt_gebuehren"] += fees
                loan["bezahlt_zins"] += interest
                loan["bezahlt_tilgung"] += repay
                self.money -= due
                self._book(day, BOOK_LOAN_FEES, -fees)
                self._book(day, BOOK_LOAN_INTEREST, -interest)
                self._book(day, BOOK_LOAN_REPAY, -repay)
                self.loan_log.append((day, "rate", loan["id"], {
                    "rate": due, "zinsen": interest, "tilgung": repay, "gebuehren": fees,
                    "rest": loan["rest"]}))
                if loan["rest"] <= 0 and loan["zins_offen"] <= 0 and loan["gebuehren"] <= 0:
                    loan.update(rest=0, ende=day, ende_art="zurueckgezahlt")
                    self.loan_log.append((day, "zurueckgezahlt", loan["id"], {}))
            else:
                failed.append(("kredit", loan, due))
        return failed

    def _dunning_day(self, day, failed):
        """Die zentrale Mahnstufe (ab 0.41 fuer Kredite, ab 0.42 auch fuer die
        Umsatzsteuer): Platzt beim Feierabend mindestens eine Zahlung, steigt
        sie um 1 (hoechstens bis zur letzten Stufe), das Ansehen sinkt einmal,
        jede geplatzte Zahlung bekommt die Gebuehr der Stufe. Ohne geplatzte
        Zahlung sinkt sie nach abbau_tage Arbeitstagen wieder um 1."""
        rules = loan_rules(self.content)
        steps = rules["mahnung"]["stufen"]
        if failed:
            # Hoechstens eine Stufe pro Feierabend, auch wenn mehreres platzt
            self.dunning = min(len(steps), self.dunning + 1)
            self.dunning_day = day
            self.dunning_peak = max(self.dunning_peak, self.dunning)
            step = steps[self.dunning - 1]
            self._apply_reputation(step.get("reputation") or {})
            fee = int(step.get("gebuehr", 0))
            for number, (kind, item, due) in enumerate(failed):
                # Das Ansehen sinkt einmal pro Feierabend (steht beim ersten Posten)
                reputation = dict(step.get("reputation") or {}) if not number else {}
                if kind == "kredit":
                    item["gebuehren"] += fee
                    item["ausfaelle"] += 1
                    self.loan_log.append((day, "ausfall", item["id"], {
                        "rate": due, "stufe": self.dunning, "gebuehr": fee,
                        "reputation": reputation}))
                else:
                    self.tax_debt += fee
                    self.tax_log.append((day, "ausfall", {
                        "betrag": due, "stufe": self.dunning, "gebuehr": fee,
                        "reputation": reputation, "schuld": self.tax_debt}))
        elif self.dunning and day - self.dunning_day >= int(rules["mahnung"]["abbau_tage"]):
            self.dunning -= 1
            self.dunning_day = day
            self.loan_log.append((day, "mahnstufe", "", {"stufe": self.dunning}))
            if not self.dunning:
                self.dunning_over.append(self.dunning_peak)
                self.dunning_peak = 0

    # -- Umsatzsteuer und Werbung (ab 0.42) ---------------------------------------

    def _ads_day(self, day):
        """Feierabend: laufende Werbung kostet ihren Tagessatz."""
        for booking in self.ads:
            if booking.get("art") == AD_RUNNING and ad_active(booking, day):
                cost = int(booking.get("kosten", 0))
                self.money -= cost
                self._book(day, BOOK_MARKETING, -cost)
                self.ad_log.append((day, booking["werbung"], cost))

    def _tax_day(self, day):
        """Feierabend: Umsatzsteuer und Vorsteuer des Tages in den laufenden
        Zeitraum, Steuerruecklage auffuellen, alle faellig_tage die
        Voranmeldung. Zurueck: geplatzte Zahlung (fuer _dunning_day) oder []."""
        rules = tax_rules(self.content)
        rate = float(rules["satz"])
        entry = self.book.get(day) or {"ein": {}, "aus": {}}
        gross_in = sum(entry["ein"].get(kind, 0) for kind in TAX_INCOME)
        gross_out = sum(entry["aus"].get(kind, 0) for kind in TAX_INPUT)
        period = self.tax_period
        if period["start"] is None:
            period["start"] = day
        period["ust"] += gross_in * rate / (100.0 + rate)
        period["vst"] += gross_out * rate / (100.0 + rate)
        period["umsatz"] += gross_in
        period["ausgaben"] += gross_out
        period["tage"] += 1
        self.tax_days += 1
        due = tax_due_amount(period)
        # Ruecklage: so viel, wie bisher an Zahllast aufgelaufen ist
        target = max(0, int(round(due * float(rules.get("ruecklage_prozent", 100)) / 100.0)))
        move = target - self.tax_reserve
        if move > 0:
            move = min(move, max(0, self.money))
        if move:
            self.money -= move
            self.tax_reserve += move
            self._book(day, BOOK_TAX, -move)
            self.tax_log.append((day, "ruecklage", {"betrag": move,
                                                    "ruecklage": self.tax_reserve}))
        if self.tax_days % max(1, int(rules["faellig_tage"])) == 0:
            data = {"von": period["start"], "bis": day, "ust": int(round(period["ust"])),
                    "vorsteuer": int(round(period["vst"])), "zahllast": due,
                    "umsatz": period["umsatz"], "ausgaben": period["ausgaben"]}
            if due >= 0:
                from_reserve = min(self.tax_reserve, due)
                self.tax_reserve -= from_reserve
                rest = due - from_reserve
                data.update(aus_ruecklage=from_reserve, vom_konto=0)
                if rest > 0:
                    paid = min(rest, max(0, self.money))
                    self.money -= paid
                    self._book(day, BOOK_TAX, -paid)
                    data["vom_konto"] = paid
                    self.tax_debt += rest - paid
                    data["offen"] = rest - paid
            else:
                self.money -= due
                self._book(day, BOOK_TAX, -due)
                data["erstattung"] = -due
            if self.tax_reserve:
                # Was in der Ruecklage uebrig ist, kommt aufs Konto zurueck
                data["frei"] = self.tax_reserve
                self.money += self.tax_reserve
                self._book(day, BOOK_TAX, self.tax_reserve)
                self.tax_reserve = 0
            self.tax_log.append((day, "voranmeldung", data))
            self.tax_period = new_tax_period()
        if self.tax_debt:
            paid = min(self.tax_debt, max(0, self.money))
            if paid:
                self.money -= paid
                self.tax_debt -= paid
                self._book(day, BOOK_TAX, -paid)
                self.tax_log.append((day, "nachgezahlt", {"betrag": paid,
                                                          "schuld": self.tax_debt}))
            if self.tax_debt:
                return [("steuer", None, self.tax_debt)]
        return []

    def ad_booking(self, ad_id, day):
        """Die gebuchte Werbung dieser Form, die am Tag laeuft oder erst
        beginnt (oder None)."""
        for booking in self.ads:
            if booking.get("werbung") == ad_id and ad_open(booking, day):
                return booking
        return None

    def ads_active(self, day=None):
        """Werbung, die am Tag wirkt."""
        day = self.day if day is None else day
        return [booking for booking in self.ads if ad_active(booking, day)]

    def ad_costs(self, day=None):
        """Laufende Werbekosten pro Arbeitstag."""
        return sum(int(booking.get("kosten", 0)) for booking in self.ads_active(day)
                   if booking.get("art") == AD_RUNNING)

    def certs_held(self, day=None):
        """Abgeschlossene Zertifizierungen am Tag."""
        day = self.day if day is None else day
        return {cert_id for cert_id, data in self.certs.items()
                if int(data.get("bis_tag", 0)) <= day}

    def cert_running(self, day=None):
        day = self.day if day is None else day
        return [data for data in self.certs.values() if int(data.get("bis_tag", 0)) > day]

    def running_loans(self):
        """Laufende Kredite in der Reihenfolge der Aufnahme."""
        return [loan for loan in self.loans.values() if loan["ende"] is None]

    def done_loans(self):
        return [loan for loan in self.loans.values() if loan["ende"] is not None]

    def loan_debt(self):
        """Restschuld aller laufenden Kredite (mit offenen Zinsen/Gebuehren)."""
        return sum(loan["rest"] + loan["zins_offen"] + loan["gebuehren"]
                   for loan in self.running_loans())

    def loan_rates(self):
        """Faellige Raten beim naechsten Feierabend (Summe)."""
        return sum(loan_due(loan, self.dunning, self.content) for loan in self.running_loans())

    # -- Lernen der Mitarbeiter (ab 0.38) ---------------------------------------

    def _learn(self, staff_id, topic, amount, day, reason):
        """Punkte durch Arbeit dazu - ab lernen.halb_ab nur halb so viele,
        nie ueber lernen.deckel (ab 0.40: darueber nur per Weiterbildung).
        Ab 0.43 lernen manche Macken schneller oder langsamer."""
        if staff_id not in self.staff or topic not in TOPIC_CAT or amount <= 0:
            return
        if self._live:
            key = "lernen_hardware" if topic in HARDWARE_TOPICS else "lernen_andere"
            amount *= max(0.0, 1 + (self.quirk_value(staff_id, "lernen", day) +
                                    self.quirk_value(staff_id, key, day)) / 100.0)
            if amount <= 0:
                return
        rule = learn_rules(self.content)
        before = self.staff_topics(staff_id, day)[topic]
        if before >= rule["halb_ab"]:
            amount = amount / 2.0
        after = min(float(learn_cap(self.content)), before + amount)
        if after <= before:
            return
        gains = self.staff_gains.setdefault(staff_id, {})
        gains[topic] = gains.get(topic, 0.0) + after - before
        self.learn_log.append((day, staff_id, topic, before, after, reason))

    def _learn_from_ticket(self, item, day):
        topic = ticket_topic(item.get("vorlage"), self.content)
        self._learn(item.get("an"), topic, learn_rules(self.content)["ticket_erfolg"], day,
                    "ticket")

    def _learn_from_project(self, item, day):
        rule = learn_rules(self.content)
        project = self.projects.get(item.get("projekt")) or {}
        topic = project_topic(project, self.content)
        amount = rule["projekt_fertig"] + (0 if item.get("verzug") else
                                           rule["projekt_puenktlich"])
        people = [share.get("an") for share in item.get("beitraege") or []]
        for person in people:
            self._learn(person, topic, amount, day, "projekt")
        if self._live:
            # Ab 0.43: Wer gern erklaert, bringt den anderen im Team etwas bei
            for teacher in people:
                extra = self.quirk_value(teacher, "team_lernen", day)
                for person in people:
                    if extra and person != teacher:
                        self._learn(person, topic, extra, day, "erklaert")

    def _learn_routine(self, busy, day):
        rule = learn_rules(self.content)
        every = max(1, int(rule["routine_tage"]))
        for staff_id in list(self.staff):
            if staff_id in busy or self.absence_of(staff_id, day):
                continue
            count = self.staff_routine.get(staff_id, 0) + 1
            self.staff_routine[staff_id] = count
            if count % every == 0:
                topics = self.staff_topics(staff_id, day)
                best = max(TOPIC_ORDER, key=lambda key: (topics[key], -TOPIC_ORDER.index(key)))
                self._learn(staff_id, best, rule["routine_plus"], day, "routine")

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
        """Alle Arbeitsplaetze: Gewerbehof plus (ab 0.45) Filiale."""
        return self.site_capacity(SITE_OFFICE) + self.site_capacity(SITE_BRANCH)

    def site_capacity(self, site):
        if not self.firm:
            return 0
        if site == SITE_BRANCH:
            stage = self.branch_stage()
            return len(stage["plaetze"]) if stage else 0
        return len(self.firm_stage()["plaetze"])

    def branch_stage(self):
        """Die Ausbaustufe der Filiale (aus firma.json) oder None."""
        return branch_stage(self.branch["stufe"], self.content) if self.branch else None

    def next_branch_stage(self):
        return branch_stage((self.branch["stufe"] if self.branch else 0) + 1, self.content)

    def site_of(self, staff_id):
        """Standort eines Mitarbeiters: SITE_OFFICE (Gewerbehof) oder SITE_BRANCH."""
        return self.staff_site.get(staff_id, SITE_OFFICE)

    def site_staff(self, site):
        return [staff_id for staff_id in self.staff if self.site_of(staff_id) == site]

    def site_free(self, site):
        """Freie Arbeitsplaetze an einem Standort."""
        return self.site_capacity(site) - len(self.site_staff(site))

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
        branch = int((self.branch_stage() or {}).get("nebenkosten", 0))
        return int(self.firm_stage().get("nebenkosten", 0)) + rooms + branch

    def training_of(self, staff_id, day=None):
        """Laufende Weiterbildung eines Mitarbeiters am Tag (oder None)."""
        day = self.day if day is None else day
        for item in self.trainings:
            if item.get("id") == staff_id and item.get("tag", 0) <= day < item.get("bis_tag", 0):
                return item
        return None

    def staff_topics(self, staff_id, day=None, pending=False):
        """Werte je Thema (ab 0.38): Einstellung plus abgeschlossene
        Weiterbildungen (pending=True: auch die laufende) plus das durch
        Arbeit Dazugelernte. Kommazahlen, angezeigt wird abgerundet."""
        day = self.day if day is None else day
        data = self.staff.get(staff_id) or {}
        if staff_id not in self._topic_base:
            self._topic_base[staff_id] = staff_base_topics(staff_id, data, self.content)
        values = dict(self._topic_base[staff_id])
        for item in self.trainings:
            if item.get("id") == staff_id and (pending or item.get("bis_tag", 0) <= day):
                plus = int(item.get("plus", 0))
                # Vor 0.38 gab es nur Weiterbildungen je Fachbereich (ohne "thema")
                for topic in ([item["thema"]] if item.get("thema") else
                              CAT_TOPICS.get(item.get("cat"), [])):
                    if topic in values:
                        values[topic] += plus
        for topic, plus in (self.staff_gains.get(staff_id) or {}).items():
            values[topic] = values.get(topic, 0) + plus
        top = float(learn_rules(self.content)["max"])
        return {topic: max(0.0, min(top, float(value))) for topic, value in values.items()}

    def staff_topic_value(self, staff_id, topic, day=None):
        return int(self.staff_topics(staff_id, day).get(topic, 0))

    def staff_values(self, staff_id, day=None, pending=False):
        """Werte je Fachbereich = Durchschnitt seiner Themen (ab 0.38)."""
        return cat_values(self.staff_topics(staff_id, day, pending))

    def trainings_of(self, staff_id):
        return [item for item in self.trainings if item.get("id") == staff_id]

    # -- Personal (ab 0.43) -------------------------------------------------------

    def absence_of(self, staff_id, day=None):
        """Warum jemand am Tag fehlt: laufende Weiterbildung oder Coaching
        (Ereignisdaten) oder {"art": "krank"/"urlaub", "von", "bis"} - sonst None."""
        day = self.day if day is None else day
        training = self.training_of(staff_id, day)
        if training:
            return training
        for item in self.absences:
            if item["id"] == staff_id and item["von"] <= day < item["bis"]:
                return item
        return None

    def away_of(self, staff_id, day=None):
        """Krank oder im Urlaub (ohne Weiterbildung) - sonst None."""
        item = self.absence_of(staff_id, day)
        return item if item and item.get("art") in (ABSENT_SICK, ABSENT_VACATION) else None

    def quirk_of(self, staff_id, day=None):
        """Die Macke eines Mitarbeiters mit Stufe am Tag (siehe quirk_state)."""
        data = self.staff.get(staff_id)
        if data is None:
            return None
        day = self.day if day is None else day
        coached = sum(1 for item in self.trainings
                      if item.get("id") == staff_id and item.get("art") == TRAINING_COACHING
                      and item.get("bis_tag", 0) <= day)
        return quirk_state(staff_id, data, day, coached, self.content)

    def quirk_value(self, staff_id, key, day=None):
        """Wirkung der Macke fuer einen Schluessel (Staerke voll, Schwaeche
        nach Stufe) - 0 ohne Macke."""
        item = self.quirk_of(staff_id, day)
        return quirk_effect(item, key) if item else 0

    def mood_of(self, staff_id):
        return int(round(self.mood.get(staff_id, personal_rules(self.content)
                                       ["stimmung"]["start"])))

    def staff_form(self, staff_id, day=None):
        """Abzug durch schlechte Stimmung oder einen ignorierten Konflikt:
        {"leistung": Prozent weniger Umsatz/Projektleistung, "chance": Punkte
        weniger Ticket-Chance, "gruende": [...]}."""
        day = self.day if day is None else day
        rules = personal_rules(self.content)
        result = {"leistung": 0, "chance": 0, "gruende": []}
        if self.mood.get(staff_id, 100) < rules["stimmung"]["tief"]:
            result["leistung"] += rules["stimmung"]["tief_leistung"]
            result["chance"] += rules["stimmung"]["tief_chance"]
            result["gruende"].append("schlechte Stimmung")
        if self.upset.get(staff_id, 0) > day:
            result["leistung"] += rules["konflikt"]["verstimmt_leistung"]
            result["chance"] += rules["konflikt"]["verstimmt_chance"]
            result["gruende"].append("verstimmt nach dem Konflikt")
        return result

    def staff_revenue_of(self, staff_id, values, day=None):
        """Routineumsatz pro Arbeitstag mit Macke und Stimmung (ab 0.43)."""
        base = staff_revenue(values, self.content)
        # Ab 0.44: Die Konjunktur hebt oder senkt den Routineumsatz
        boom = market_state(self, self.day if day is None else day,
                            self.content)["phase_info"].get("umsatz", 0)
        factor = (1 + self.quirk_value(staff_id, "umsatz", day) / 100.0) * \
            (1 - self.staff_form(staff_id, day)["leistung"] / 100.0) * (1 + boom / 100.0)
        return int(round(max(0.0, base * factor)))

    def _mood_change(self, staff_id, delta):
        if staff_id in self.mood:
            self.mood[staff_id] = max(0.0, min(100.0, self.mood[staff_id] + float(delta)))

    def _mood_after_failure(self, item, day):
        """Kundenfluesterer: ein verpatztes Kundenticket schlaegt aufs Gemuet."""
        self._mood_change(item.get("an"), -self.quirk_value(item.get("an"),
                                                           "stimmung_fehlschlag", day))

    def _apply_decision(self, kind, data, day):
        """Antwort auf eine Urlaubsanfrage oder Entscheidung bei einem Konflikt.
        Doppelt (zwei Geraete) zaehlt nur die erste."""
        key = data.get("anfrage") or data.get("konflikt") or data.get("rueckhol")
        if not key or key in self.answers:
            return
        rules = personal_rules(self.content)
        self.answers[key] = dict(data, art=kind)
        if kind == EV_VACATION_OK:
            staff_id = data.get("id")
            self.absences.append({"id": staff_id, "art": ABSENT_VACATION,
                                  "von": int(data.get("von", 0)), "bis": int(data.get("bis", 0))})
            self._mood_change(staff_id, rules["urlaub"]["genehmigt"])
        elif kind == EV_VACATION_NO:
            # Zweimal hintereinander abgelehnt: das sitzt tiefer
            before = [item for item in self.answers.values()
                      if item.get("id") == data.get("id") and item.get("anfrage") and
                      item.get("anfrage") != key]
            again = bool(before) and before[-1]["art"] == EV_VACATION_NO
            self._mood_change(data.get("id"), rules["urlaub"]["abgelehnt_wieder" if again
                                                            else "abgelehnt"])
        elif kind == EV_CONFLICT:
            rule = rules["konflikt"]
            first, second = data.get("a"), data.get("b")
            choice = data.get("wahl")
            if choice == CONFLICT_MEDIATE:
                self.mediation_days.add(int(data.get("tag", day)))
                self._mood_change(first, rule["schlichten"])
                self._mood_change(second, rule["schlichten"])
            elif choice in (CONFLICT_SIDE_A, CONFLICT_SIDE_B):
                winner, loser = (first, second) if choice == CONFLICT_SIDE_A else (second, first)
                self._mood_change(winner, rule["partei_plus"])
                self._mood_change(loser, rule["partei_minus"])
            else:
                until = int(data.get("tag", day)) + int(rule["verstimmt_tage"])
                for person in (first, second):
                    self._mood_change(person, rule["ignorieren"])
                    self.upset[person] = max(self.upset.get(person, 0), until)
        elif kind == EV_RECALL and data.get("id") in self.staff:
            rule = rivalry_rules(self.content).get("rueckhol") or {}
            staff_id = data["id"]
            choice = data.get("wahl")
            if choice == RECALL_RAISE:
                self.staff[staff_id]["gehalt"] = int(data.get("gehalt") or
                                                     self.staff[staff_id].get("gehalt", 0))
                self._mood_change(staff_id, rule.get("gehalt_stimmung", 0))
            elif choice == RECALL_BONUS:
                self.money += int(data.get("geld", 0))
                self._book(day, BOOK_WAGES, data.get("geld", 0))
                self._mood_change(staff_id, rule.get("bonus_stimmung", 0))
            else:
                self.leaving[staff_id] = int(data.get("tag", day))
                self.answers["leaving:" + staff_id] = dict(data)

    def _personal_day(self, day, items):
        """Feierabend ab 0.43: Die Stimmung erholt sich ein Stueck, dazu die
        Personal-Ereignisse aus dem Feierabend (Krankheit, Anfragen,
        Konflikte, Kuendigungen)."""
        rules = personal_rules(self.content)["stimmung"]
        cheer = {staff_id: self.quirk_value(staff_id, "stimmung_team", day)
                 for staff_id in self.staff}
        for staff_id in list(self.staff):
            step = float(rules["erholung"]) + sum(value for other, value in cheer.items()
                                                  if other != staff_id)
            value = self.mood.get(staff_id, float(rules["start"]))
            goal = float(rules["ziel"])
            if value < goal:
                value = min(goal, value + step)
            elif value > goal:
                value = max(goal, value - float(rules["erholung"]))
            self.mood[staff_id] = value
            if value < rules["kritisch"]:
                self.mood_low[staff_id] = self.mood_low.get(staff_id, 0) + 1
            else:
                self.mood_low[staff_id] = 0
        for item in items:
            self.personal_log.append((day, dict(item)))
            art = item.get("art")
            if art == PERSONAL_SICK and item.get("id") in self.staff:
                self.absences.append({"id": item["id"], "art": ABSENT_SICK,
                                      "von": int(item["von"]), "bis": int(item["bis"])})
            elif art == PERSONAL_QUIT and item.get("id") in self.staff:
                self.staff.pop(item["id"], None)
                self.quit_staff[item["id"]] = day

    def open_decisions(self):
        """Offene Entscheidungen zum Personal (Urlaubsanfragen, Konflikte),
        siehe personal_decisions."""
        return personal_decisions(self, self.content) if self.firm else []

    def staff_list(self):
        """Mitarbeiter in der Reihenfolge der Einstellung, mit Arbeitsplatz.
        Ab 0.45 je Standort: Wer in der Filiale arbeitet, sitzt dort."""
        places = {SITE_OFFICE: self.firm_stage()["plaetze"] if self.firm else [],
                  SITE_BRANCH: (self.branch_stage() or {}).get("plaetze") or []}
        seated = {SITE_OFFICE: 0, SITE_BRANCH: 0}
        result = []
        for staff_id, data in self.staff.items():
            topics = self.staff_topics(staff_id)
            item = dict(data, werte=cat_values(topics), themen=topics,
                        staerken=strongest_topics(topics))
            item["weiterbildung"] = self.training_of(staff_id)
            item["abwesend"] = self.away_of(staff_id)
            item["projekt"] = self.project_of(staff_id)
            item["macke_info"] = self.quirk_of(staff_id)
            item["stimmung"] = self.mood_of(staff_id)
            item["form"] = self.staff_form(staff_id)
            # Wer in einem Projekt mitarbeitet, macht keine Routineauftraege
            item["umsatz"] = 0 if item["weiterbildung"] or item["abwesend"] or \
                item["projekt"] else self.staff_revenue_of(staff_id, item["werte"])
            site = self.site_of(staff_id)
            item["standort"] = site
            index = seated[site]
            seated[site] += 1
            if index < len(places[site]):
                item["platz"] = places[site][index]
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
        return project_tenders(self, self.day, self.content) + \
            gross_tenders(self, self.day, self.content)

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
            # Ab 0.43: offene Entscheidungen zum Personal zuerst treffen
            return not self.open_decisions()
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
        self.unlocked = []         # neu erreichte Abzeichen-Stufen fuer die Anzeige (ab 0.46)
        self._checking = False
        self.reload()

    def reload(self):
        self.state = GameState(self.db.game_events(), self.content)
        return self.state

    def knowledge(self):
        return knowledge(self.db, self.content["balancing"]["wissen"])

    def topic_knowledge(self):
        return topic_knowledge(self.db, topic_params(self.content["balancing"]))

    def firm_levels(self):
        """Wissensstand je Fachbereich und je Thema zusammen (ab 0.38 fuer die
        Firma: Kundentickets und Projekte rechnen mit dem Thema)."""
        levels = dict(self.knowledge())
        levels.update(self.topic_knowledge())
        return levels

    def _log(self, kind, data):
        self.db.log_game_event(kind, json.dumps(data, ensure_ascii=False), self.device)
        self.reload()
        if kind != EV_ACHIEVEMENT:
            self.check_achievements(day_end=kind == EV_DAY_END)

    # -- Erfolge und Bestenliste (ab 0.46) --------------------------------------

    def records(self):
        """Alle Zeilen der Bestenliste (ueber alle Spielstaende)."""
        return self.db.records() if hasattr(self.db, "records") else []

    def check_achievements(self, knowledge=None, day_end=False, force=False):
        """Haelt neu erreichte Abzeichen-Stufen fest und schreibt die Bestenliste
        fort. knowledge: Wissensstand je Thema (nur dann zaehlen die Wissen-
        Abzeichen). Ein aelterer Spielstand, der noch gar keine Abzeichen hat,
        bekommt sie still nachgetragen (ohne Meilenstein-Moment). Zurueck: neue
        Stufen (unlock_info), die auch in self.unlocked landen."""
        state = self.state
        if self._checking or state is None or state.profile is None or not state.first_event:
            return []
        self._checking = True
        try:
            records = self.records()
            found = new_achievements(state, knowledge, self.content)
            silent = not state.achievements and state.days_done > 0
            infos = []
            if found:
                day = max(1, state.days_done if day_end else state.day)
                for rule, level in found:
                    info = unlock_info(state, rule, level, records, self.content)
                    self.db.log_game_event(EV_ACHIEVEMENT, json.dumps(
                        {"erfolg": rule["id"], "stufe": level, "tag": day,
                         "nachgetragen": silent}, ensure_ascii=False), self.device)
                    if not silent:
                        infos.append(info)
                self.reload()
            if hasattr(self.db, "log_record"):
                for kind, key, value, data in record_rows(self.state, records, self.content,
                                                          force):
                    self.db.log_record(self.state.first_event, kind, key, value,
                                       json.dumps(data, ensure_ascii=False))
            self.unlocked += infos
            return infos
        finally:
            self._checking = False

    def check_knowledge(self):
        """Wie check_achievements, dazu die Wissen-Abzeichen (Lernplattform)."""
        return self.check_achievements(self.topic_knowledge())

    def take_unlocks(self):
        """Neue Stufen fuer die Anzeige abholen: je Abzeichen nur die hoechste,
        Meilenstein-Momente zuerst."""
        best = {}
        for info in self.unlocked:
            if info["erfolg"] not in best or info["stufe"] > best[info["erfolg"]]["stufe"]:
                best[info["erfolg"]] = info
        self.unlocked = []
        return sorted(best.values(), key=lambda info: not info["moment"])

    def reset_records(self):
        """Bestenliste loeschen. Der laufende Spielstand traegt sich gleich neu ein."""
        ok = self.db.reset_records()
        self.check_achievements()
        return ok

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
        payload = evaluate(task, answer, used_help, self.topic_knowledge(), self.state.day,
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
            if self.state.firm:
                raise ValueError(DECISIONS_OPEN_TEXT)
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
            days = project_outcomes(self.state, self.firm_levels(), self.learned_projects(),
                                    self.content)
            if days:
                payload["firma"]["projekte"] = days
            # Ab 0.42: Umsatzsteuer ab diesem Feierabend (aeltere Tage bleiben
            # steuerfrei, damit alte Spielstaende nicht nachtraeglich zahlen)
            payload["firma"]["ust"] = 1
            # Ab 0.43: Macken und Stimmung wirken ab diesem Feierabend
            payload["firma"]["personal"] = []
            # Einmal durchrechnen, was der Feierabend bringt (nur fuer die Anzeige)
            after = GameState(list(self.state.history) + [("", EV_DAY_END, payload)],
                              self.content)
            # Personal fuer den naechsten Arbeitstag: Krankheit, Urlaubsanfragen,
            # Konflikte, Kuendigungen (aus der Stimmung nach diesem Feierabend)
            payload["firma"]["personal"] = personal_events(after, self.state.day,
                                                           self.content)
            learned = learned_today(self.state, payload, self.content, after)
            if learned:
                payload["firma"]["gelernt"] = learned
            # Mahnstufe: Kredite und Umsatzsteuer zusammen (steht bei den Krediten)
            loans = loans_today(after, self.state.day)
            if loans:
                payload["firma"]["kredite"] = loans
            taxes = taxes_today(after, self.state.day)
            if taxes:
                payload["firma"]["steuer"] = taxes
            ads = sum(cost for day, _ad, cost in after.ad_log if day == self.state.day)
            if ads:
                payload["firma"]["werbung"] = ads
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
                                                   "themen", "gehalt", "herkunft",
                                                   "schwerpunkt", "macke", "rolle")}
        if applicant.get("macke_id"):
            payload["macke_id"] = applicant["macke_id"]
        if "vorher" in applicant:
            payload["vorher"] = applicant["vorher"]
        payload["tag"] = self.state.day
        # Ab 0.45: Ist der Gewerbehof voll, faengt die Person in der Filiale an
        if self.state.site_free(SITE_OFFICE) <= 0 and self.state.site_free(SITE_BRANCH) > 0:
            payload["standort"] = SITE_BRANCH
        self._log(EV_HIRED, payload)
        return payload

    def fire(self, staff_id):
        self._firm_required()
        if staff_id not in self.state.staff:
            raise ValueError("Diese Person arbeitet nicht bei dir.")
        payload = {"id": staff_id, "tag": self.state.day}
        self._log(EV_FIRED, payload)
        return payload

    def train(self, staff_id, target):
        """Abstrakte Weiterbildung: kostet Geld und Arbeitstage ohne Umsatz,
        danach steigt der Wert im Thema bzw. in allen Themen des
        Fachbereichs (target = Thema oder Fachbereich)."""
        self._firm_required()
        offer = training_offer(self.state, staff_id, target, self.content)
        if offer["problem"]:
            raise ValueError(offer["problem"])
        payload = {"id": staff_id, "cat": offer["cat"], "art": offer["art"],
                   "geld": -offer["preis"], "tag": self.state.day,
                   "bis_tag": self.state.day + offer["tage"], "plus": offer["plus"]}
        if offer["thema"]:
            payload["thema"] = offer["thema"]
        self._log(EV_TRAINING, payload)
        return payload

    def coach(self, staff_id):
        """Coaching (ab 0.43): kostet Geld und Arbeitstage wie eine
        Weiterbildung, danach wirkt die Schwaeche der Macke eine Stufe
        schwaecher."""
        self._firm_required()
        offer = coaching_offer(self.state, staff_id, self.content)
        if offer["problem"]:
            raise ValueError(offer["problem"])
        payload = {"id": staff_id, "art": TRAINING_COACHING, "cat": None,
                   "geld": -offer["preis"], "tag": self.state.day,
                   "bis_tag": self.state.day + offer["tage"], "plus": 0,
                   "macke": offer["macke"]}
        self._log(EV_TRAINING, payload)
        return payload

    def decide(self, decision_id, choice):
        """Entscheidung zum Personal (ab 0.43): Urlaubsanfrage genehmigen
        oder ablehnen, bei einem Konflikt eingreifen."""
        self._firm_required()
        item = next((entry for entry in self.state.open_decisions()
                     if entry["id"] == decision_id), None)
        if item is None:
            raise ValueError("Diese Entscheidung steht nicht (mehr) an.")
        option = next((entry for entry in item["optionen"] if entry["id"] == choice), None)
        if option is None:
            raise ValueError("Diese Möglichkeit gibt es hier nicht.")
        if option.get("problem"):
            raise ValueError(option["problem"])
        if item["art"] == DECISION_VACATION:
            payload = {"anfrage": item["id"], "id": item["person"], "name": item["name"],
                       "von": item["von"], "bis": item["bis"], "tag": self.state.day}
            self._log(EV_VACATION_OK if choice == VACATION_YES else EV_VACATION_NO, payload)
        elif item["art"] == DECISION_RECALL:
            payload = {"rueckhol": item["id"], "id": item["person"], "name": item["name"],
                       "firma": item["firma"], "wahl": choice, "tag": self.state.day}
            if choice == RECALL_RAISE:
                payload["gehalt"] = item["gehalt_neu"]
            elif choice == RECALL_BONUS:
                payload["geld"] = -int(item["bonus"])
            self._log(EV_RECALL, payload)
        else:
            payload = {"konflikt": item["id"], "a": item["a"], "b": item["b"],
                       "name_a": item["name_a"], "name_b": item["name_b"],
                       "wahl": choice, "tag": self.state.day}
            self._log(EV_CONFLICT, payload)
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

    # -- Zweiter Standort (ab 0.45) ---------------------------------------------

    def open_branch(self, name):
        """Eroeffnet die Filiale (Stufe 1) mit frei gewaehltem Namen."""
        self._firm_required()
        name = " ".join((name or "").split())[:FIRM_NAME_MAX]
        if not name:
            raise ValueError("Bitte gib deiner Filiale einen Namen.")
        if self.state.branch:
            raise ValueError("Die Filiale ist schon eröffnet.")
        missing = branch_missing(self.state, self.content)
        if missing:
            raise ValueError("Für die Filiale fehlt noch: %s." % ", ".join(missing))
        stage = branch_stage(1, self.content)
        if self.state.money < stage["preis"]:
            raise ValueError("Dafür reicht dein Geld noch nicht (%s fehlen)."
                             % _whole_euro(stage["preis"] - max(0, self.state.money)))
        payload = {"stufe": 1, "name": name, "geld": -int(stage["preis"]),
                   "tag": self.state.day}
        self._log(EV_BRANCH, payload)
        return payload

    def expand_branch(self):
        """Baut die Filiale eine Stufe weiter aus."""
        self._firm_required()
        if not self.state.branch:
            raise ValueError("Eröffne zuerst die Filiale.")
        stage = self.state.next_branch_stage()
        if stage is None:
            raise ValueError("Die Filiale ist fertig ausgebaut.")
        if self.state.money < stage["preis"]:
            raise ValueError("Dafür reicht dein Geld noch nicht (%s fehlen)."
                             % _whole_euro(stage["preis"] - max(0, self.state.money)))
        payload = {"stufe": stage["stufe"], "geld": -int(stage["preis"]),
                   "tag": self.state.day}
        self._log(EV_BRANCH, payload)
        return payload

    def transfer(self, staff_id, site):
        """Versetzt einen Mitarbeiter an den anderen Standort."""
        self._firm_required()
        if staff_id not in self.state.staff:
            raise ValueError("Diese Person arbeitet nicht bei dir.")
        if site not in (SITE_OFFICE, SITE_BRANCH):
            raise ValueError("Unbekannter Standort.")
        if site == SITE_BRANCH and not self.state.branch:
            raise ValueError("Eröffne zuerst die Filiale.")
        if self.state.site_of(staff_id) == site:
            raise ValueError("Die Person arbeitet schon dort.")
        if self.state.site_free(site) <= 0:
            raise ValueError("Dort ist kein Arbeitsplatz mehr frei.")
        payload = {"id": staff_id, "name": self.state.staff[staff_id].get("name", ""),
                   "standort": site, "tag": self.state.day}
        self._log(EV_TRANSFER, payload)
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
                                                          self.firm_levels(), self.content)
                       if item["an"] == person), None)
        if option is None:
            raise ValueError("Diese Person arbeitet nicht bei dir.")
        if option["problem"]:
            raise ValueError(option["problem"])
        payload = {"ticket": ticket_id, "vorlage": ticket["vorlage"], "tag": self.state.day,
                   "an": person, "name": option["name"], "chance": option["chance"]}
        self._log(EV_DELEGATED, payload)
        return payload

    # -- Kredite (ab 0.41) -------------------------------------------------------

    def take_loan(self, amount, term, package_id=None):
        """Nimmt einen Kredit auf: festes Paket (package_id) oder freie Summe
        und Laufzeit. Das Geld ist sofort auf dem Konto."""
        self._firm_required()
        package = None
        if package_id and package_id != FREE_LOAN:
            package = next((item for item in loan_rules(self.content)["pakete"]
                            if item["id"] == package_id), None)
            if package is None:
                raise ValueError("Dieses Kreditpaket gibt es nicht.")
            amount, term = package["summe"], package["laufzeit"]
        offer = loan_offer(self.state, amount, term, package, self.content)
        if offer["problem"]:
            raise ValueError(offer["problem"])
        payload = {"kredit": "%s%d:%d" % (LOAN_PREFIX, self.state.day,
                                          len(self.state.loans) + 1),
                   "tag": self.state.day, "name": offer["name"], "paket": offer["paket"],
                   "summe": offer["summe"], "laufzeit": offer["laufzeit"],
                   "zins": offer["zins"], "rate": offer["rate"]}
        self._log(EV_LOAN, payload)
        return payload

    def repay_loan(self, loan_id):
        """Loest einen laufenden Kredit vorzeitig ab (mit Vorfaelligkeit)."""
        self._firm_required()
        loan = self.state.loans.get(loan_id)
        if loan is None or loan["ende"] is not None:
            raise ValueError("Dieser Kredit läuft nicht (mehr).")
        payoff = loan_payoff(loan, self.content)
        if self.state.money < payoff["gesamt"]:
            raise ValueError("Zum Ablösen fehlen dir noch %s." % _whole_euro(
                payoff["gesamt"] - max(0, self.state.money)))
        payload = {"kredit": loan_id, "tag": self.state.day, "geld": -payoff["gesamt"]}
        self._log(EV_LOAN_REPAID, payload)
        return payload

    # -- Werbung und Zertifizierungen (ab 0.42) -----------------------------------

    def book_ad(self, ad_id, mode):
        """Bucht eine Werbeform laufend (AD_RUNNING, Kosten pro Arbeitstag)
        oder einmalig (AD_ONCE, sofort bezahlt, befristet). Die Wirkung
        beginnt am naechsten Arbeitstag."""
        self._firm_required()
        offer = ad_offer(self.state, ad_id, mode, self.content)
        if offer["problem"]:
            raise ValueError(offer["problem"])
        day = self.state.day
        payload = {"werbung": ad_id, "art": mode, "tag": day, "ab_tag": day + 1}
        if mode == AD_ONCE:
            payload.update(bis_tag=day + offer["tage"], geld=-offer["preis"])
        else:
            payload["kosten"] = offer["kosten"]
        self._log(EV_ADS, payload)
        return payload

    def stop_ad(self, ad_id):
        """Kuendigt laufende Werbung (heute kostet sie noch)."""
        self._firm_required()
        booking = self.state.ad_booking(ad_id, self.state.day)
        if booking is None or booking.get("art") != AD_RUNNING:
            raise ValueError("Diese Werbung läuft nicht dauerhaft.")
        payload = {"werbung": ad_id, "tag": self.state.day}
        self._log(EV_ADS_STOP, payload)
        return payload

    def start_cert(self, cert_id):
        """Beginnt eine Zertifizierung: kostet sofort, gilt nach den Arbeitstagen."""
        self._firm_required()
        offer = cert_offer(self.state, cert_id, self.content)
        if offer["problem"]:
            raise ValueError(offer["problem"])
        payload = {"zert": cert_id, "tag": self.state.day,
                   "bis_tag": self.state.day + offer["tage"], "geld": -offer["preis"]}
        self._log(EV_CERT, payload)
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
            self.state, project, self.firm_levels(), self.content)}
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
        # Der Durchgang endet: seine Bestwerte vollstaendig in die Bestenliste
        self.check_achievements(force=True)
        ok = self.db.reset_game()
        self.unlocked = []
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
BOOK_LOAN = "Kredite"                 # ausgezahlte Kredite (ab 0.41)
BOOK_LOAN_INTEREST = "Kreditzinsen"
BOOK_LOAN_REPAY = "Kredittilgung"
BOOK_LOAN_FEES = "Kreditgebühren"     # Mahngebuehren, Vorfaelligkeit
BOOK_TAX = "Umsatzsteuer"               # Ruecklage, Nachzahlung, Erstattung (ab 0.42)
BOOK_MARKETING = "Werbung"
BOOK_CERT = "Zertifizierung"
# Ab 0.42: In diesen Einnahmen steckt Umsatzsteuer, in diesen Ausgaben
# Vorsteuer (Gehaelter, Zinsen, Gebuehren und die Gruendung haben keine)
TAX_INCOME = (BOOK_REVENUE, BOOK_TICKETS, BOOK_OFFERS, BOOK_PROJECTS)
TAX_INPUT = (BOOK_COSTS, BOOK_MATERIAL, BOOK_BUILDING, BOOK_TRAINING, BOOK_MARKETING,
             BOOK_CERT)

SELF = "ich"                       # Kundenticket uebernimmt die Spielfigur selbst
INQUIRY_PREFIX = "anfrage:"        # anfrage:<tag>:<nummer>
TICKET_PREFIX = "kundenticket:"    # kundenticket:<tag>:<vorlage>
PROJECT_PREFIX = "projekt:"        # projekt:<nummer der ausschreibung>


# Reiter im Unterpunkt "Firma" (PC und Handy gleich beschriftet)
FIRM_TABS = [("auftraege", "Aufträge"), ("projekte", "Projekte"),
             ("mitarbeiter", "Mitarbeiter"),
             ("bewerbungen", "Bewerbungen"),
             ("gebaeude", "Gebäude"), ("marketing", "Marketing"),
             ("zertifizierungen", "Zertifizierungen"),
             ("finanzen", "Finanzen"), ("kredite", "Kredite")]


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
        return absence_text(item)
    left = training["bis_tag"] - state.day
    if training.get("art") == TRAINING_COACHING:
        return "Im Coaching (Macke „%s“) · noch %s" % (
            (item.get("macke_info") or {}).get("name", ""), _days_text(left))
    what = "%s, +%d" % (TOPIC_SHORT[training["thema"]], training["plus"]) \
        if training.get("thema") else "%s, +%d je Thema" % (
            CATEGORY_SHORT[CAT_NAME[training["cat"]]], training["plus"])
    return "In Weiterbildung (%s) · noch %s" % (
        what,
        "1 Arbeitstag" if left == 1 else "%d Arbeitstage" % left)


def firm_rules(content=None):
    return (content or GAME)["firma"]


def learn_rules(content=None):
    return firm_rules(content)["lernen"]


def learn_cap(content=None):
    """Grenze fuer das Lernen durch Arbeit je Thema (ab 0.40) - darueber
    geht es nur noch mit Weiterbildung."""
    rule = learn_rules(content)
    return min(rule.get("deckel", rule["max"]), rule["max"])


def topics_at_cap(topics, content=None):
    """Themen, in denen die Person durch Arbeit nichts mehr dazulernt."""
    cap = learn_cap(content)
    return [topic for topic in TOPIC_ORDER if topics.get(topic, 0) >= cap]


def cap_text(topics, content=None):
    """ "Grenze erreicht: SQL · Routing - weiter nur mit Weiterbildung" (ab 0.40) """
    reached = topics_at_cap(topics, content)
    if not reached:
        return ""
    return "Grenze erreicht: %s – weiter nur mit Weiterbildung" % " · ".join(
        TOPIC_SHORT[topic] for topic in reached)


def cat_values(topics):
    """Werte je Thema -> Werte je Fachbereich (gerundeter Durchschnitt)."""
    result = {}
    for key in CAT_ORDER:
        values = [topics.get(topic, 0) for topic in CAT_TOPICS[key]]
        result[key] = int(round(sum(values) / float(len(values)))) if values else 0
    return result


def strongest_topics(topics, count=2):
    """Die staerksten Themen (bei Gleichstand in der Reihenfolge der Themen)."""
    return sorted(TOPIC_ORDER, key=lambda key: (-topics.get(key, 0),
                                                TOPIC_ORDER.index(key)))[:count]


def spread_topics(values, seed, spread):
    """Werte je Fachbereich -> Werte je Thema: jedes Thema fest gestreut um
    +-spread, der Durchschnitt je Fachbereich bleibt (vor dem Runden) gleich."""
    result = {}
    for key in CAT_ORDER:
        topics = CAT_TOPICS[key]
        offsets = [(_dice(seed, 0, "thema|" + topic) * 2 - 1) * spread for topic in topics]
        mean = sum(offsets) / float(len(offsets)) if offsets else 0
        for topic, offset in zip(topics, offsets):
            result[topic] = max(0, min(90, int(round(values.get(key, 0) + offset - mean))))
    return result


def add_strengths(topics, strengths, plus):
    result = dict(topics)
    for topic in strengths:
        if topic in result:
            result[topic] = min(90, result[topic] + int(plus))
    return result


def staff_base_topics(staff_id, data, content=None):
    """Werte je Thema bei der Einstellung. Mitarbeiter aus Spielstaenden vor
    0.38 haben nur Werte je Fachbereich: dann fest gestreut um den alten Wert."""
    if data.get("themen"):
        return {topic: float(data["themen"].get(topic, 0)) for topic in TOPIC_ORDER}
    spread = learn_rules(content).get("alt_streuung", 5)
    topics = spread_topics(data.get("werte") or {}, "alt|%s" % staff_id, spread)
    return {topic: float(value) for topic, value in topics.items()}


def ticket_topic(template_id, content=None):
    """Thema einer Kundenticket-Vorlage (ab 0.38)."""
    item = next((item for item in ticket_rules(content)["vorlagen"]
                 if item["id"] == template_id), None)
    return (item or {}).get("thema")


def project_topic(project, content=None):
    """Thema eines Projekts - Projekte aus aelteren Spielstaenden holen es
    aus der Projektarbeit (Vorlage)."""
    if project.get("thema"):
        return project["thema"]
    templates = (content or GAME).get("projektarbeiten") or []
    index = project.get("vorlage")
    if isinstance(index, int) and 0 <= index < len(templates):
        return templates[index].get("thema")
    return None


def topic_level(levels, topic, cat):
    """Wissensstand der Spielfigur im Thema (sonst im Fachbereich)."""
    levels = levels or {}
    return int(round(levels.get(topic, levels.get(cat, 0)) if topic else levels.get(cat, 0)))


def strengths_text(item):
    """ "Stark in: IPv4 62 · Linux 55" """
    topics = item.get("themen") or {}
    names = item.get("staerken") or strongest_topics(topics)
    return "Stark in: " + " · ".join("%s %d" % (TOPIC_SHORT[topic], int(topics.get(topic, 0)))
                                     for topic in names)


def topics_text(topics, cat):
    """ "Grundlagen 32 · IPv4 40 · ..." - die Themen eines Fachbereichs """
    return " · ".join("%s %d" % (TOPIC_SHORT[topic], int(topics.get(topic, 0)))
                      for topic in CAT_TOPICS[cat])


LEARN_REASONS = {"ticket": "Kundenticket", "projekt": "Projekt", "routine": "Routinearbeit"}


def learned_text(item):
    """ "Tim: Verkabelung 38 → 40 (Kundenticket)" """
    return "%s: %s %d → %d (%s)" % (short_name({"name": item.get("name", "")}),
                                     TOPIC_SHORT.get(item.get("thema"), item.get("thema")),
                                     int(item.get("vorher", 0)), int(item.get("nachher", 0)),
                                     LEARN_REASONS.get(item.get("grund"), ""))


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
    # Ab 0.38: Werte je Thema, dazu Staerken (die erste im Schwerpunkt)
    rule = rules["bewerbung"]
    topics = spread_topics(values, "%s|%s" % (seed, salt), rule.get("thema_streuung", 10))
    strengths = [_pick(CAT_TOPICS[focus], seed, batch, salt + "staerke0")]
    for extra in range(1, int(rule.get("staerken", 2))):
        rest = [topic for topic in TOPIC_ORDER if topic not in strengths]
        strengths.append(_pick(rest, seed, batch, salt + "staerke%d" % extra))
    topics = add_strengths(topics, strengths, rule.get("staerke_plus", 20))
    values = cat_values(topics)
    names = rules["namen"]
    look = {part: _pick([key for key, _name in options], seed, batch, salt + part)
            for part, options in APPEARANCE.items() if part != "kreis"}
    look["kreis"] = "violett"
    # Ab 0.43: Macken als Objekte, die Bitweiche-Wechsler haben ihre eigene
    quirk = _pick([item for item in rules["macken"] if not item.get("kollege")],
                  seed, batch, salt + "macke")
    staff_id = "bw%d-%d" % (batch, number)
    # Ab 0.44: Manche kommen von einem Mitbewerber (der sie spaeter zurueckwill)
    former = former_for(seed, staff_id, content)
    role = staff_role(values)
    if former:
        role = "%s, bisher bei %s" % (role, competitor(former, content)["kurz"])
    return {"id": staff_id, "macke": quirk["text"], "macke_id": quirk["id"],
            "vorher": former,
            "macke_info": quirk_state(staff_id, {"macke_id": quirk["id"]}, 0, 0, content),
            "name": "%s %s" % (_pick(names["vornamen"], seed, batch, salt + "vor"),
                               _pick(names["nachnamen"], seed, batch, salt + "nach")),
            "aussehen": normalize_appearance(look), "werte": values, "themen": topics,
            "staerken": strongest_topics(topics),
            "gehalt": staff_salary(values, content), "herkunft": "bewerbung",
            "schwerpunkt": staff_focus(values),
            "rolle": role}


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
        topics = add_strengths(
            spread_topics(item["werte"], "wechsel|" + item["kollege"],
                          rules["bewerbung"].get("thema_streuung", 10)),
            item.get("staerken") or [], rules["bewerbung"].get("staerke_plus", 20))
        values = cat_values(topics)
        result.append({"id": staff_id, "name": person["name"],
                       "aussehen": normalize_appearance(person.get("aussehen")),
                       "werte": values, "themen": topics,
                       "staerken": strongest_topics(topics),
                       "gehalt": staff_salary(values, content),
                       "herkunft": "bitweiche", "schwerpunkt": staff_focus(values),
                       "macke": person.get("macke", ""),
                       "macke_id": (quirk_for_colleague(item["kollege"], content) or
                                    {}).get("id"),
                       "macke_info": quirk_state(staff_id, {"herkunft": "bitweiche"}, 0, 0,
                                                 content),
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


def training_offer(state, staff_id, target, content=None):
    """Was eine Weiterbildung kostet und bringt: {"preis", "tage", "plus",
    "art", "cat", "thema", "problem" (leer = moeglich)}. target ist ein
    Thema (+plus in diesem Thema) oder ein Fachbereich (ab 0.38: +plus auf
    alle seine Themen, teurer und laenger)."""
    rules = firm_rules(content)["weiterbildung"]
    whole = target in CAT_ORDER
    rule = rules.get("fachbereich", rules) if whole else rules
    done = len([item for item in state.trainings_of(staff_id)
                if item.get("art") != TRAINING_COACHING])
    # Eigener Schulungsraum (ab 0.36): guenstiger und kuerzer
    price = discounted(int(rule["preis"] + rules["aufschlag"] * done),
                       state.room_effect("weiterbildung_rabatt"))
    days = max(1, int(rule["tage"]) - int(state.room_effect("weiterbildung_tage_minus")))
    # Ab 0.43: Manche Macken lernen lieber mit den Haenden
    days += int(round(state.quirk_value(staff_id, "weiterbildung_tage")))
    cat = target if whole else CAT_KEY.get(TOPIC_CAT.get(target))
    result = {"preis": price, "tage": days, "plus": 0, "problem": "",
              "art": "fachbereich" if whole else "thema", "cat": cat,
              "thema": None if whole else target}
    if staff_id not in state.staff:
        result["problem"] = "Diese Person arbeitet nicht bei dir."
        return result
    if cat is None:
        result["problem"] = "Unbekanntes Thema."
        return result
    top = int(rules["max"])
    values = state.staff_topics(staff_id, pending=True)
    if whole:
        room = max(top - values.get(topic, 0) for topic in CAT_TOPICS[cat])
        result["plus"] = int(rule["plus"]) if room > 0 else 0
    else:
        result["plus"] = max(0, min(int(rule["plus"]), int(top - values.get(target, 0))))
    if state.training_of(staff_id):
        result["problem"] = "Die Person ist gerade schon in einer Weiterbildung."
    elif state.away_of(staff_id):
        result["problem"] = absent_problem(state.staff[staff_id].get("name", ""),
                                           state.away_of(staff_id))
    elif not result["plus"]:
        result["problem"] = "%s ist das Maximum (%d) erreicht." % (
            "In allen Themen des Fachbereichs" if whole else "In diesem Thema", top)
    elif state.money < result["preis"]:
        result["problem"] = "Dafür reicht dein Geld noch nicht (%s fehlen)." % _whole_euro(
            result["preis"] - max(0, state.money))
    return result


# -- Personal: Macken, Stimmung, Krankheit, Urlaub, Konflikte (ab 0.43) --------
#
# Macken haben eine Staerke (wirkt immer voll) und eine Schwaeche (wirkt je
# nach Stufe). Die Stufe sinkt mit der Betriebszugehoerigkeit und durch
# Coaching. Gespeichert wird nur, was beim Feierabend passiert ist
# (firma.personal) und wie du entschieden hast - Stimmung, Ausfaelle und
# Stufen rechnet der Spielstand selbst aus.

TRAINING_COACHING = "coaching"
ABSENT_SICK = "krank"
ABSENT_VACATION = "urlaub"
PERSONAL_SICK = "mitarbeiter_krank"
PERSONAL_VACATION = "urlaub_angefragt"
PERSONAL_CONFLICT = "konflikt"
PERSONAL_QUIT = "kuendigung_selbst"
PERSONAL_WARN = "unzufrieden"
PERSONAL_WEAKER = "macke_abgeschwaecht"
DECISION_VACATION = "urlaub"
DECISION_CONFLICT = "konflikt"
VACATION_YES = "ja"
VACATION_NO = "nein"
CONFLICT_MEDIATE = "schlichten"
CONFLICT_SIDE_A = "a"
CONFLICT_SIDE_B = "b"
CONFLICT_IGNORE = "ignorieren"
PERSONAL_RECALL = "rueckhol"       # ab 0.44: ein Mitbewerber will jemanden zurueck
DECISION_RECALL = "rueckhol"
RECALL_RAISE = "gehalt"
RECALL_BONUS = "bonus"
RECALL_LET = "gehen"
HARDWARE_TOPICS = ("hardware", "storage", "verkabelung")
DECISIONS_OPEN_TEXT = "Erst die offenen Entscheidungen zum Personal treffen."
ACTION_PERSONAL = "personal"       # Knopf: zu den Entscheidungen (Firma > Mitarbeiter)
QUIRK_BAR_FULL = "■"
QUIRK_BAR_EMPTY = "□"


def personal_rules(content=None):
    return firm_rules(content)["personal"]


def quirk_by_id(quirk_id, content=None):
    return next((item for item in firm_rules(content)["macken"]
                 if isinstance(item, dict) and item["id"] == quirk_id), None)


def quirk_for_colleague(colleague_id, content=None):
    """Die Macke eines Bitweiche-Kollegen, der zu dir wechselt."""
    return next((item for item in firm_rules(content)["macken"]
                 if item.get("kollege") == colleague_id), None)


def _quirk_for(staff_id, data, content=None):
    """Macke aus den Einstellungsdaten - aeltere Spielstaende kennen nur
    den Text, Bitweiche-Kollegen erkennt man an der Kennung."""
    item = quirk_by_id(data.get("macke_id"), content) if data.get("macke_id") else None
    if item is None and str(staff_id).startswith(STAFF_PREFIX):
        item = quirk_for_colleague(str(staff_id)[len(STAFF_PREFIX):], content)
    if item is None and data.get("macke"):
        item = next((entry for entry in firm_rules(content)["macken"]
                     if entry["text"] == data["macke"]), None)
    return item


def quirk_start_stage(staff_id, data):
    """Ausgepraegt (3) oder mittel (2) - Bitweiche-Kollegen bringen
    Berufserfahrung mit und starten bei mittel."""
    if data.get("herkunft") == "bitweiche" or str(staff_id).startswith(STAFF_PREFIX):
        return 2
    return 3 if _dice(staff_id, 0, "macke-stufe") < 0.5 else 2


def quirk_state(staff_id, data, day, coached=0, content=None):
    """Macke mit Stufe am Tag: {"id", "name", "text", "plus", "minus",
    "start", "stufe", "stufe_name", "faktor", "plus_texte", "minus_texte",
    "naechste_in" (Arbeitstage bis zur naechsten Stufe durch Erfahrung oder
    None)} - None ohne bekannte Macke."""
    item = _quirk_for(staff_id, data, content)
    if item is None:
        return None
    rules = personal_rules(content)["macken"]
    every = max(1, int(rules["abschwaechen_tage"]))
    start = quirk_start_stage(staff_id, data)
    tenure = max(0, int(day) - int(data.get("tag", day) or day)) if data.get("tag") else 0
    stage = max(1, start - tenure // every - int(coached))
    name, percent = rules["stufen"][str(stage)]
    result = {"id": item["id"], "name": item["name"], "text": item["text"],
              "plus": dict(item.get("plus") or {}), "minus": dict(item.get("minus") or {}),
              "start": start, "stufe": stage, "stufe_name": name,
              "faktor": float(percent) / 100.0,
              "naechste_in": every - tenure % every if stage > 1 else None}
    result["plus_texte"] = [quirk_effect_text(key, value) for key, value in result["plus"].items()]
    result["minus_texte"] = [quirk_effect_text(key, value * result["faktor"])
                             for key, value in result["minus"].items()]
    return result


def quirk_effect(item, key):
    """Wirkung einer Macke (quirk_state) fuer einen Schluessel."""
    if not item:
        return 0
    return item["plus"].get(key, 0) + item["minus"].get(key, 0) * item["faktor"]


def _signed(value, unit=""):
    value = round(float(value), 1)
    text = ("%d" % value if value == int(value) else ("%.1f" % value).replace(".", ","))
    return ("+" + text if value > 0 else text) + unit


def _training_days_text(value):
    """Die Weiterbildung verlaengert sich um ganze Arbeitstage (gerundet)."""
    days = int(round(float(value)))
    if days <= 0:
        return "Weiterbildung dauert nicht mehr länger"
    return "Weiterbildung dauert %s länger" % _days_text(days)


def quirk_effect_text(key, value):
    """Eine Wirkung als kurzer Text: "Ticket-Chance +10 %"."""
    plain = _signed(value).lstrip("+-")
    texts = {
        "umsatz": "Routineumsatz %s" % _signed(value, " %"),
        "chance": "Ticket-Chance %s" % _signed(value, " %"),
        "chance_netzwerk": "Ticket-Chance bei Netzwerk-Tickets %s" % _signed(value, " %"),
        "chance_hardware": "Ticket-Chance bei Hardware-Tickets %s" % _signed(value, " %"),
        "chance_talbahn": "Ticket-Chance bei Talbahn-Kunden %s" % _signed(value, " %"),
        "projekt": "Projektleistung %s" % _signed(value, " %"),
        "team_projekt": "Projektleistung des ganzen Teams %s" % _signed(value, " %"),
        "team_lernen": "Kollegen im Projektteam lernen beim Abschluss %s" % _signed(value),
        "kz_erfolg": "Kundenzufriedenheit bei geschafften Tickets %s" % _signed(value),
        "kz_fehlschlag": "Verpatzte Tickets kosten %s Kundenzufriedenheit weniger" % plain,
        "lernen": "Lernt durch Arbeit %s" % _signed(value, " %"),
        "lernen_hardware": "Lernt in Hardware-Themen %s" % _signed(value, " %"),
        "lernen_andere": "Lernt in allen anderen Themen %s" % _signed(value, " %"),
        "urlaub": "Fragt %s %% öfter nach Urlaub" % plain,
        "krank": "Wird %s %% öfter krank" % plain,
        "konflikt": "Streit im Team %s %% häufiger" % plain,
        "weiterbildung_tage": _training_days_text(value),
        "stimmung_team": "Stimmung der Kollegen erholt sich schneller (%s pro Tag)"
                         % _signed(value),
        "stimmung_fehlschlag": "Stimmung -%s nach einem verpatzten Ticket" % plain,
    }
    return texts.get(key, "%s %s" % (key, _signed(value)))


def quirk_bar(stage):
    """Drei Kaestchen fuer die Stufe: "■■□" = mittel."""
    stage = max(0, min(3, int(stage)))
    return QUIRK_BAR_FULL * stage + QUIRK_BAR_EMPTY * (3 - stage)


def quirk_hint(item):
    """Hinweis zur Abschwaechung (oder leer)."""
    if not item:
        return ""
    if item["stufe"] <= 1:
        return "Schwächer wird die Macke nicht mehr."
    days = item["naechste_in"]
    return "Schwächt sich ab: nächste Stufe in %s (oder per Coaching)." % (
        "1 Arbeitstag" if days == 1 else "%d Arbeitstagen" % days)


def quirk_lines(item):
    """Macke fuer die Anzeige (PC und Handy gleich): {"titel", "balken",
    "stufe", "zitat", "plus", "minus", "hinweis"} - None ohne Macke."""
    if not item:
        return None
    return {"titel": item["name"], "balken": quirk_bar(item["stufe"]),
            "stufe": item["stufe_name"], "zitat": "„%s“" % item["text"],
            "plus": " · ".join(item["plus_texte"]), "minus": " · ".join(item["minus_texte"]),
            "hinweis": quirk_hint(item)}


def mood_level(value):
    """gut / okay / schlecht / kritisch - fuer die Farbe."""
    rules = personal_rules()["stimmung"]
    if value >= rules["ziel"]:
        return "gut"
    if value >= rules["tief"]:
        return "okay"
    if value >= rules["kritisch"]:
        return "schlecht"
    return "kritisch"


def mood_name(value):
    rules = personal_rules()["stimmung"]
    if value >= rules["ziel"]:
        return "gut"
    if value >= rules["tief"]:
        return "okay"
    if value >= rules["kritisch"]:
        return "schlecht"
    return "denkt an Kündigung"


def mood_text(item):
    """ "Stimmung 70 (gut)" - dazu der Leistungsabzug, falls es einen gibt."""
    text = "Stimmung %d (%s)" % (item["stimmung"], mood_name(item["stimmung"]))
    form = item.get("form") or {}
    if form.get("leistung"):
        text += " · %d %% weniger Leistung (%s)" % (form["leistung"],
                                                   ", ".join(form["gruende"]))
    return text


def absence_text(item):
    """Zeile fuer Mitarbeiter, die krank oder im Urlaub sind (oder leer)."""
    away = item.get("abwesend")
    if not away:
        return ""
    return "%s bis einschließlich Arbeitstag %d" % (
        "Krank" if away["art"] == ABSENT_SICK else "Im Urlaub", away["bis"] - 1)


def _days_text(count):
    return "1 Arbeitstag" if count == 1 else "%d Arbeitstage" % count


def coaching_offer(state, staff_id, content=None):
    """Was ein Coaching kostet: {"preis", "tage", "macke", "stufe",
    "problem"} - danach wirkt die Schwaeche eine Stufe schwaecher."""
    rules = personal_rules(content)["coaching"]
    price = discounted(int(rules["preis"]), state.room_effect("weiterbildung_rabatt"))
    days = max(1, int(rules["tage"]) - int(state.room_effect("weiterbildung_tage_minus")))
    quirk = state.quirk_of(staff_id)
    result = {"preis": price, "tage": days, "problem": "",
              "macke": quirk["id"] if quirk else None, "stufe": quirk["stufe"] if quirk else 0}
    name = (state.staff.get(staff_id) or {}).get("name", "")
    absent = state.absence_of(staff_id)
    if staff_id not in state.staff:
        result["problem"] = "Diese Person arbeitet nicht bei dir."
    elif quirk is None:
        result["problem"] = "%s hat keine Macke, an der ein Coaching etwas ändert." % name
    elif quirk["stufe"] <= 1:
        result["problem"] = "Die Macke ist schon so schwach, wie sie werden kann."
    elif absent:
        result["problem"] = absent_problem(name, absent)
    elif state.money < price:
        result["problem"] = "Dafür reicht dein Geld noch nicht (%s fehlen)." % _whole_euro(
            price - max(0, state.money))
    return result


def absent_problem(name, absent):
    """Warum jemand heute nichts uebernehmen kann."""
    if absent.get("art") == ABSENT_SICK:
        return "%s ist krank." % name
    if absent.get("art") == ABSENT_VACATION:
        return "%s ist im Urlaub." % name
    if absent.get("art") == TRAINING_COACHING:
        return "%s ist gerade im Coaching." % name
    return "%s ist gerade in einer Weiterbildung." % name


def staff_ticket_chance(state, staff_id, ticket, value, content=None):
    """Chance eines Mitarbeiters bei einem Kundenticket: Wert im Thema, dazu
    ab 0.43 die Macke (auch nur bei passenden Tickets) und die Stimmung."""
    bonus = state.quirk_value(staff_id, "chance")
    if ticket.get("cat") == "netzwerk":
        bonus += state.quirk_value(staff_id, "chance_netzwerk")
    if ticket.get("thema") in HARDWARE_TOPICS:
        bonus += state.quirk_value(staff_id, "chance_hardware")
    if (ticket.get("kunde") or {}).get("art") == "talbahn":
        bonus += state.quirk_value(staff_id, "chance_talbahn")
    bonus -= state.staff_form(staff_id)["chance"]
    return ticket_chance(value, ticket["anforderung"], content, bonus)


def staff_project_points(state, person, value, content=None):
    """Projektleistung am Tag: Grundwert aus dem Thema, bei Mitarbeitern ab
    0.43 mit Macke und Stimmung."""
    points = project_points(value, content)
    if person == SELF or person not in state.staff:
        return points
    factor = (1 + state.quirk_value(person, "projekt") / 100.0) * \
        (1 - state.staff_form(person)["leistung"] / 100.0)
    return round(max(0.0, points * factor), 1)


def team_factor(state, people):
    """Ab 0.43: Wer das ganze Team mitzieht (Whiteboard), wirkt einmal."""
    best = max([state.quirk_value(person, "team_projekt") for person in people
                if person in state.staff and not state.absence_of(person)] or [0])
    return 1 + best / 100.0


def _vacation_line(item, content=None):
    rules = personal_rules(content)["urlaub"]
    texts = rules.get("texte") or []
    if item.get("talbahn") and rules.get("text_talbahn"):
        return rules["text_talbahn"]
    return _pick(texts, item["anfrage"], 0, "text") if texts else ""


def conflict_pair(state, people, seed, day, content=None):
    """Wer sich streitet: [a, b] und der Text. Wer gern summt, geraet am
    ehesten mit den Genauen aneinander."""
    rule = personal_rules(content)["konflikt"]
    humming = [person for person in people
               if (state.quirk_of(person) or {}).get("id") == "gute_laune"]
    strict = [person for person in people
              if (state.quirk_of(person) or {}).get("id") in ("pedantisch", "gruendlich")]
    if humming and strict and rule.get("summen") and \
            _dice(seed, day, "konflikt-summen") < 0.5:
        return [_pick(humming, seed, day, "summt"), _pick(strict, seed, day, "genervt")], \
            rule["summen"]
    order = sorted(people, key=lambda person: _dice(seed, day, "konflikt-paar|" + person))
    return order[:2], _pick(rule["texte"], seed, day, "konflikt-text")


def _genitive(name):
    """ "Tims", aber "Jonas’" """
    return name + ("’" if name[-1:].lower() in "sßxz" else "s")


def _pair_names(first, second):
    """Vornamen der beiden - bei gleichem Vornamen die ganzen Namen."""
    if short_name({"name": first}) != short_name({"name": second}):
        first, second = short_name({"name": first}), short_name({"name": second})
    return {"a": first, "b": second, "a_von": _genitive(first), "b_von": _genitive(second)}


def personal_events(state, day, content=None):
    """Was beim Feierabend fuer den naechsten Arbeitstag feststeht (state =
    Spielstand nach dem Feierabend): Kuendigungen und Warnungen aus der
    Stimmung, Krankmeldungen, Urlaubsanfragen, Konflikte und schwaecher
    werdende Macken. Fest gewuerfelt - auf allen Geraeten gleich."""
    content = content or state.content
    rules = personal_rules(content)
    seed = state.firm_seed
    tomorrow = day + 1
    result = []
    names = {staff_id: data.get("name", "") for staff_id, data in state.staff.items()}
    for staff_id in list(state.staff):
        low = state.mood_low.get(staff_id, 0)
        if low >= int(rules["stimmung"]["kuendigung_nach"]):
            result.append({"art": PERSONAL_QUIT, "id": staff_id, "name": names[staff_id]})
        elif low == 1:
            result.append({"art": PERSONAL_WARN, "id": staff_id, "name": names[staff_id]})
    leaving = {item["id"] for item in result if item["art"] == PERSONAL_QUIT}
    present = [staff_id for staff_id in state.staff
               if staff_id not in leaving and not state.absence_of(staff_id, tomorrow)]
    rule = rules["krankheit"]
    for staff_id in present:
        chance = float(rule["chance"]) * max(0.0, 1 + state.quirk_value(
            staff_id, "krank", tomorrow) / 100.0)
        if _dice(seed, day, "krank|" + staff_id) * 100 < chance:
            days = _between(seed, day, "krank-tage|" + staff_id, int(rule["tage_min"]),
                            int(rule["tage_max"]))
            result.append({"art": PERSONAL_SICK, "id": staff_id, "name": names[staff_id],
                           "von": tomorrow, "bis": tomorrow + days})
    sick = {item["id"] for item in result if item["art"] == PERSONAL_SICK}
    rule = rules["urlaub"]
    # Kleine Story-Elemente: in der ganzen Firma hoechstens eine Anfrage pro
    # Feierabend und dazwischen ein paar Arbeitstage Ruhe
    last = max([tag for tag, item in state.personal_log
                if item.get("art") == PERSONAL_VACATION] or [-1000])
    for staff_id in present:
        hired = int(state.staff[staff_id].get("tag", 0) or 0)
        if staff_id in sick or day - hired < int(rule["ab_tagen"]) or \
                day - last < int(rule.get("abstand_firma", 0)) or \
                any(item["art"] == PERSONAL_VACATION for item in result):
            continue
        asked = [tag for tag, item in state.personal_log
                 if item.get("art") == PERSONAL_VACATION and item.get("id") == staff_id]
        if asked and day - asked[-1] < int(rule["abstand"]):
            continue
        if any(item["id"] == staff_id and item["art"] == ABSENT_VACATION and
               item["bis"] > tomorrow for item in state.absences):
            continue
        chance = float(rule["chance"]) * max(0.0, 1 + state.quirk_value(
            staff_id, "urlaub", tomorrow) / 100.0)
        if _dice(seed, day, "urlaub|" + staff_id) * 100 < chance:
            start = tomorrow + int(rule["vorlauf"])
            days = _between(seed, day, "urlaub-tage|" + staff_id, int(rule["tage_min"]),
                            int(rule["tage_max"]))
            item = {"art": PERSONAL_VACATION, "anfrage": "urlaub:%d:%s" % (day, staff_id),
                    "id": staff_id, "name": names[staff_id], "von": start, "bis": start + days}
            if (state.quirk_of(staff_id, tomorrow) or {}).get("id") == "talbahn":
                item["talbahn"] = True
            result.append(item)
    rule = rules["konflikt"]
    people = [staff_id for staff_id in present if staff_id not in sick]
    last = max([tag for tag, item in state.personal_log
                if item.get("art") == PERSONAL_CONFLICT] or [-1000])
    if len(people) >= int(rule["ab_mitarbeiter"]) and day - last >= int(rule["abstand"]):
        boost = max(state.quirk_value(staff_id, "konflikt", tomorrow) for staff_id in people)
        chance = float(rule["chance"]) * max(0.0, 1 + boost / 100.0)
        if _dice(seed, day, "konflikt") * 100 < chance:
            (first, second), text = conflict_pair(state, people, seed, day, content)
            result.append({"art": PERSONAL_CONFLICT, "konflikt": "konflikt:%d" % day,
                           "a": first, "b": second, "name_a": names[first],
                           "name_b": names[second],
                           "text": text.format(**_pair_names(names[first], names[second]))})
    # Ab 0.44: Ein Mitbewerber will jemanden zurueck (nicht, wer schon mit
    # Urlaub oder Streit beschaeftigt ist)
    taken = {item.get("id") for item in result} | {item.get("a") for item in result} | \
        {item.get("b") for item in result}
    result += _recall_events(state, day, [staff_id for staff_id in present
                                          if staff_id not in sick], taken, content)
    for staff_id in state.staff:
        if staff_id in leaving:
            continue
        before, after = state.quirk_of(staff_id, day), state.quirk_of(staff_id, tomorrow)
        if before and after and after["stufe"] < before["stufe"]:
            result.append({"art": PERSONAL_WEAKER, "id": staff_id, "name": names[staff_id],
                           "macke": after["name"], "stufe": after["stufe"],
                           "stufe_name": after["stufe_name"]})
    return result


def personal_decisions(state, content=None):
    """Offene Entscheidungen zum Personal: [{"id", "art" (urlaub/konflikt),
    "titel", "text", "optionen": [{"id", "label", "folge", "problem"}], ...}].
    Urlaubsanfragen bis zum Urlaubsbeginn, Konflikte nur am Tag danach."""
    content = content or state.content
    rules = personal_rules(content)
    result = []
    for tag, item in state.personal_log:
        art = item.get("art")
        if art == PERSONAL_VACATION:
            key = item["anfrage"]
            if key in state.answers or item["id"] not in state.staff or \
                    item["von"] <= state.day:
                continue
            first = short_name(item)
            rule = rules["urlaub"]
            before = [entry for entry in state.answers.values()
                      if entry.get("id") == item["id"] and entry.get("anfrage")]
            again = bool(before) and before[-1]["art"] == EV_VACATION_NO
            count = item["bis"] - item["von"]
            text = "%s fragt, ob %s von Arbeitstag %d bis %d Urlaub nehmen darf (%s)." % (
                item["name"], first, item["von"], item["bis"] - 1, _days_text(count))
            line = _vacation_line(item, content)
            if line:
                text += " " + line
            result.append({
                "id": key, "art": DECISION_VACATION, "person": item["id"],
                "name": item["name"], "von": item["von"], "bis": item["bis"],
                "titel": "Urlaubsanfrage von %s" % item["name"], "text": text,
                "optionen": [
                    {"id": VACATION_YES, "label": "Genehmigen", "problem": "",
                     "folge": "%s fehlt %s, dafür Stimmung %s." % (
                         first, _days_text(count), _signed(rule["genehmigt"]))},
                    {"id": VACATION_NO, "label": "Ablehnen", "problem": "",
                     "folge": "%s bleibt da, aber Stimmung %s%s." % (
                         first, _signed(rule["abgelehnt_wieder" if again else "abgelehnt"]),
                         " (schon das zweite Nein in Folge)" if again else "")}]})
        elif art == PERSONAL_RECALL:
            if item["rueckhol"] in state.answers or tag != state.day - 1 or \
                    item["id"] not in state.staff:
                continue
            result.append(_recall_decision(state, item, content))
        elif art == PERSONAL_CONFLICT:
            key = item["konflikt"]
            if key in state.answers or tag != state.day - 1 or \
                    item["a"] not in state.staff or item["b"] not in state.staff:
                continue
            rule = rules["konflikt"]
            names = _pair_names(item["name_a"], item["name_b"])
            first, second = names["a"], names["b"]
            limit = own_ticket_limit(state, content)
            busy = len(state.delegated_to(SELF)) >= limit
            result.append({
                "id": key, "art": DECISION_CONFLICT, "a": item["a"], "b": item["b"],
                "name_a": item["name_a"], "name_b": item["name_b"],
                "titel": "Streit zwischen %s und %s" % (first, second),
                "text": item["text"] + " Du musst eingreifen.",
                "optionen": [
                    {"id": CONFLICT_MEDIATE, "label": "Schlichten",
                     "folge": "Ein Gespräch zu dritt kostet dich heute einen "
                              "Kundenticket-Platz. Beide: Stimmung %s."
                              % _signed(rule["schlichten"]),
                     "problem": "Heute hast du keine Zeit mehr für ein Gespräch, deine "
                                "Kundenticket-Plätze sind belegt." if busy else ""},
                    {"id": CONFLICT_SIDE_A, "label": "%s recht geben" % first, "problem": "",
                     "folge": "%s: Stimmung %s. %s: Stimmung %s." % (
                         first, _signed(rule["partei_plus"]), second,
                         _signed(rule["partei_minus"]))},
                    {"id": CONFLICT_SIDE_B, "label": "%s recht geben" % second,
                     "problem": "",
                     "folge": "%s: Stimmung %s. %s: Stimmung %s." % (
                         second, _signed(rule["partei_plus"]), first,
                         _signed(rule["partei_minus"]))},
                    {"id": CONFLICT_IGNORE, "label": "Ignorieren", "problem": "",
                     "folge": "Beide: Stimmung %s und %s lang %d %% weniger Leistung." % (
                         _signed(rule["ignorieren"]), _days_text(int(rule["verstimmt_tage"])),
                         rule["verstimmt_leistung"])}]})
    return result


def decision_result_text(decision, choice):
    """Kurze Bestaetigung nach einer Entscheidung."""
    option = next((item for item in decision["optionen"] if item["id"] == choice), None)
    label = option["label"] if option else choice
    return "%s: %s. %s" % (decision["titel"], label, option["folge"] if option else "")


def personal_news(state, content=None):
    """Story-Moment am Morgen zum Personal: was beim letzten Feierabend
    feststand, dazu Urlaube, die heute beginnen."""
    lines = []
    for tag, item in state.personal_log:
        if tag != state.day - 1:
            continue
        art = item.get("art")
        first = short_name({"name": item.get("name", "")}) if item.get("name") else ""
        if art == PERSONAL_SICK:
            lines.append("%s hat sich krankgemeldet und fällt %s aus (bis einschließlich "
                         "Arbeitstag %d)." % (item["name"], _days_text(item["bis"] - item["von"]),
                                             item["bis"] - 1))
        elif art == PERSONAL_VACATION:
            lines.append("%s möchte Urlaub nehmen und wartet auf deine Antwort." % item["name"])
        elif art == PERSONAL_CONFLICT:
            lines.append("Ärger im Team: %s" % item["text"])
        elif art == PERSONAL_QUIT:
            lines.append("%s hat gekündigt. Die Stimmung war zu lange im Keller, der Platz "
                         "ist wieder frei." % item["name"])
        elif art == PERSONAL_WARN:
            lines.append("%s wirkt sehr unzufrieden. Wenn sich nichts bessert, kündigt %s "
                         "bald." % (item["name"], first))
        elif art == PERSONAL_WEAKER:
            lines.append("%s hat sich eingearbeitet: Die Macke „%s“ wirkt schwächer (jetzt "
                         "%s)." % (item["name"], item["macke"], item["stufe_name"]))
        elif art == PERSONAL_RECALL:
            lines.append("Abwerbeversuch: %s" % item["text"])
    for day, rival, name in state.returned_staff.values():
        if day == state.day - 1:
            lines.append("%s arbeitet ab heute wieder bei %s. Der Platz ist frei." % (
                name, competitor(rival or BITWEICHE, content)["kurz"]))
    for item in state.absences:
        if item["art"] == ABSENT_VACATION and item["von"] == state.day and \
                item["id"] in state.staff:
            lines.append("%s ist ab heute im Urlaub (bis einschließlich Arbeitstag %d)." % (
                state.staff[item["id"]].get("name", ""), item["bis"] - 1))
    if state.open_decisions():
        lines.append("Unter Firma > Mitarbeiter wartet eine Entscheidung auf dich.")
    return "\n".join(lines)


def conflict_choice_text(data):
    """Wie du dich bei einem Konflikt entschieden hast."""
    names = _pair_names(data.get("name_a", ""), data.get("name_b", ""))
    first, second = names["a"], names["b"]
    choice = data.get("wahl")
    if choice == CONFLICT_MEDIATE:
        return "Du hast geschlichtet."
    if choice == CONFLICT_SIDE_A:
        return "Du hast %s recht gegeben." % first
    if choice == CONFLICT_SIDE_B:
        return "Du hast %s recht gegeben." % second
    return "Du hast den Streit ignoriert."


def firm_people(state, content=None, site=None):
    """Die Mitarbeiter als Personen im eigenen Gebaeude (wie die Kollegen) -
    ab 0.45 je Standort (Gewerbehof oder Filiale)."""
    site = site or SITE_OFFICE
    result = []
    for item in state.staff_list():
        # Wer krank oder im Urlaub ist, sitzt nicht im Buero (ab 0.43)
        if not item.get("platz") or item.get("abwesend") or item.get("standort") != site:
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
                       "in_weiterbildung": bool(training),
                       "im_coaching": bool(training) and
                       training.get("art") == TRAINING_COACHING})
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


# ----------------------------------------------------------------------------
#  Zweiter Standort: Filiale (ab 0.45)
# ----------------------------------------------------------------------------
#
# Alle Zahlen stehen in firma.json unter "filiale". Die Filiale ist ein
# eigenes Gebaeude (eigener Grundriss je Stufe, eigene Arbeitsplaetze); wer
# dort arbeitet, steht im Ereignis (Einstellung mit "standort" oder
# mitarbeiter_versetzt), alles andere rechnet der Spielstand aus.

def branch_rules(content=None):
    return firm_rules(content).get("filiale") or {}


def branch_stage(number, content=None):
    """Stufe der Filiale (1 = Eroeffnung) oder None."""
    for stage in branch_rules(content).get("stufen") or []:
        if int(stage.get("stufe", 0)) == int(number or 0):
            return stage
    return None


def branch_missing(state, content=None):
    """Was fuer die Eroeffnung der Filiale noch fehlt (leer = moeglich,
    ohne das Geld - das zeigt der Knopf)."""
    rules = branch_rules(content or state.content)
    need = rules.get("voraussetzung") or {}
    if not rules or not state.firm:
        return ["eine eigene Firma"]
    missing = []
    if state.firm["stufe"] < int(need.get("stufe", 0)):
        stage = next((item for item in firm_rules(content or state.content)["gebaeude"]["stufen"]
                      if item["stufe"] == int(need["stufe"])), {})
        missing.append("Gewerbehof mindestens Stufe %d (%s)" % (need["stufe"],
                                                               stage.get("name", "")))
    if len(state.staff) < int(need.get("mitarbeiter", 0)):
        missing.append("mindestens %d Mitarbeiter (jetzt %d)" % (need["mitarbeiter"],
                                                                 len(state.staff)))
    age = state.day - int(state.firm["tag"])
    if age < int(need.get("firmentage", 0)):
        missing.append("Firma mindestens %d Arbeitstage alt (jetzt %d)"
                       % (need["firmentage"], age))
    return missing


def branch_possible(state, content=None):
    """Steht die Filiale auf der Karte? Ab erfuellter Voraussetzung (dann
    "zu vermieten") und natuerlich, sobald sie eroeffnet ist."""
    if state is None or not state.firm:
        return False
    return bool(state.branch) or not branch_missing(state, content)


def branch_inquiries(state, content=None):
    """Zusaetzliche Kundenanfragen pro Tag durch die Filiale."""
    if not state.branch:
        return 0
    return int(branch_rules(content or state.content).get("anfragen_plus", 0))


def branch_nearness(state, customer_id, content=None):
    """Preisvorteil in Prozentpunkten bei Kunden in der Naehe der Filiale."""
    if not state.branch or not customer_id:
        return 0
    rule = branch_rules(content or state.content).get("naehe") or {}
    customer = firm_customer(customer_id, content or state.content) or {}
    if customer.get("ort") and customer["ort"] in (rule.get("orte") or []):
        return int(rule.get("vorteil", 0))
    return 0


def branch_building(state, content=None):
    stage = state.branch_stage()
    return stage["gebaeude"] if stage else None


def branch_status(state, content=None):
    """Die Filiale fuer die Oberflaeche: {"offen" (eroeffnet), "name",
    "stufe", "plaetze", "belegt", "nebenkosten", "fehlt" [..],
    "naechste" (Stufe oder None), "problem" (warum der Knopf nicht geht)}."""
    content = content or state.content
    rules = branch_rules(content)
    stage = state.branch_stage()
    following = state.next_branch_stage()
    item = {"offen": bool(state.branch),
            "name": state.branch["name"] if state.branch else rules.get("name_vorschlag", ""),
            "stufe": stage, "plaetze": state.site_capacity(SITE_BRANCH),
            "belegt": len(state.site_staff(SITE_BRANCH)),
            "fehlt": [] if state.branch else branch_missing(state, content),
            "naechste": following, "problem": ""}
    if item["fehlt"]:
        item["problem"] = "Noch nicht so weit: %s." % ", ".join(item["fehlt"])
    elif following is None:
        item["problem"] = "Die Filiale ist fertig ausgebaut."
    elif state.money < int(following["preis"]):
        item["problem"] = "Dafür reicht dein Geld noch nicht (%s fehlen)." % _whole_euro(
            int(following["preis"]) - max(0, state.money))
    return item


def branch_effect_text(content=None):
    """Kurzer Satz zu den Vorteilen der Filiale."""
    rules = branch_rules(content)
    near = rules.get("naehe") or {}
    parts = []
    if rules.get("anfragen_plus"):
        parts.append("+%d Kundenanfrage pro Tag" % rules["anfragen_plus"])
    if near.get("vorteil"):
        names = [item["name"] for item in firm_rules(content).get("kunden", [])
                 if item.get("ort") in (near.get("orte") or [])]
        parts.append("+%d %% Preisvorteil bei %s" % (near["vorteil"],
                                                     " und ".join(names) or "Kunden vor Ort"))
    return ", ".join(parts)


def branch_opened_text(name, content=None):
    return (branch_rules(content).get("eroeffnet") or "%s ist eröffnet.").replace("%s", name)


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
        # Ab 0.41: Ein Kredit ist kein Gewinn und die Tilgung kein Verlust
        # (nur die Zinsen und Gebuehren kosten) - "gewinn" ohne beides
        loan = entry["ein"].get(BOOK_LOAN, 0) - entry["aus"].get(BOOK_LOAN_REPAY, 0)
        result.append({"tag": day, "ein": dict(entry["ein"]), "aus": dict(entry["aus"]),
                       "einnahmen": income, "ausgaben": costs,
                       "gewinn": income - costs - loan})
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
    profit = numbers["umsatz"] - numbers["gehaelter"] - numbers["nebenkosten"] - \
        state.loan_rates() - state.ad_costs()
    return "%d von %d Plätzen besetzt · heute %s%s" % (
        len(state.staff), state.capacity, "+" if profit >= 0 else "-",
        _whole_euro(abs(profit)))


def firm_day_text(numbers):
    """ "Umsatz: +300 €. Gehälter: -180 €. Nebenkosten: -40 €." - dazu je
    Kundenticket eine Zeile mit dem Ergebnis (ab 0.34)."""
    text = "Umsatz Mitarbeiter: +%s. Gehälter: -%s. Nebenkosten: -%s." % (
        _whole_euro(numbers.get("umsatz", 0)), _whole_euro(numbers.get("gehaelter", 0)),
        _whole_euro(numbers.get("nebenkosten", 0)))
    # Ab 0.41: Kreditraten wie Gehaelter und Nebenkosten
    loans = numbers.get("kredite") or []
    paid = sum(item["rate"] for item in loans if item["art"] == "rate")
    if paid:
        text += " Kreditraten: -%s." % _whole_euro(paid)
    # Ab 0.42: Werbung und Umsatzsteuer
    if numbers.get("werbung"):
        text += " Werbung: -%s." % _whole_euro(numbers["werbung"])
    taxes = numbers.get("steuer") or []
    reserve = sum(item["betrag"] for item in taxes if item["art"] == "ruecklage")
    if reserve > 0:
        text += " Umsatzsteuer in die Rücklage: -%s." % _whole_euro(reserve)
    lines = [ticket_result_text(item) for item in numbers.get("tickets") or []]
    if lines:
        text += "\n\nKundentickets:\n" + "\n".join("• " + line for line in lines)
    lines = [project_day_text(item) for item in numbers.get("projekte") or []]
    if lines:
        text += "\n\nProjekte:\n" + "\n".join("• " + line for line in lines)
    lines = loan_day_lines(loans)
    if lines:
        text += "\n\nKredite:\n" + "\n".join("• " + line for line in lines)
    lines = tax_day_lines(taxes)
    if lines:
        text += "\n\nUmsatzsteuer:\n" + "\n".join("• " + line for line in lines)
    learned = numbers.get("gelernt") or []
    lines = [learned_text(item) for item in learned if not item.get("grenze")]
    if lines:
        text += "\n\nDazugelernt:\n" + "\n".join("• " + line for line in lines)
    # Ab 0.40: wer die Grenze fuers Lernen durch Arbeit erreicht, steht extra
    lines = [learned_text(item) for item in learned if item.get("grenze")]
    if lines:
        text += "\n\nGrenze erreicht (weiter nur mit Weiterbildung):\n" + "\n".join(
            "• " + line for line in lines)
    return text


def learned_today(state, payload, content=None, after=None):
    """Was die Mitarbeiter mit diesem Feierabend dazulernen - nur fuer die
    Anzeige; der Spielstand rechnet es selbst aus den Ergebnissen aus."""
    if after is None:
        after = GameState(list(state.history) + [("", EV_DAY_END, payload)], content or
                          state.content)
    result = []
    cap = learn_cap(content or state.content)
    for day, staff_id, topic, before, now, reason in after.learn_log:
        if day != state.day:
            continue
        result.append({"id": staff_id, "name": (after.staff.get(staff_id) or {}).get("name", ""),
                       "thema": topic, "vorher": int(before), "nachher": int(now),
                       "grund": reason, "grenze": now >= cap})
    # Nur zeigen, was sich in der ganzen Zahl bemerkbar macht
    return [item for item in result if item["nachher"] > item["vorher"]]


# -- Kredite (ab 0.41) -------------------------------------------------------------
#
# Die Hausbank leiht der Firma Geld, sobald sie kreditwuerdig ist (Alter,
# Umsatz der letzten Arbeitstage, Ansehen). Gespeichert wird nur, wann welcher
# Kredit aufgenommen oder abgeloest wurde - Raten, geplatzte Raten und
# Mahnstufen rechnet GameState beim Feierabend selbst aus.

LOAN_PREFIX = "kredit:"            # kredit:<tag>:<nummer>
FREE_LOAN = "frei"                 # kein Paket, frei gewaehlte Summe


def loan_rules(content=None):
    return (content or GAME)["balancing"]["kredite"]


def loan_terms(content=None):
    """Erlaubte Laufzeiten in Arbeitstagen (aufsteigend)."""
    return sorted(int(key) for key in loan_rules(content)["zins"]["basis"])


def loan_rate_pa(amount, term, content=None):
    """Zinssatz pro Jahr: Grundzins nach Laufzeit plus Aufschlag fuer grosse
    Summen (lang und gross = teurer, kurz und klein = guenstiger)."""
    rule = loan_rules(content)["zins"]
    base = float(rule["basis"][str(int(term))])
    steps = max(0, int(amount) - int(rule["groesse_ab"])) // int(rule["groesse_schritt"])
    return round(base + steps * float(rule["groesse_plus"]), 2)


def day_interest(rate_pa, content=None):
    """Zinssatz pro Arbeitstag als Bruchteil (8 % p. a. bei 50 Tagen = 0,0016)."""
    return float(rate_pa) / 100.0 / float(loan_rules(content)["tage_pro_jahr"])


def annuity(amount, rate_pa, term, content=None):
    """Gleichbleibende Rate pro Arbeitstag (Zins + Tilgung), aufgerundet."""
    rate = day_interest(rate_pa, content)
    if rate <= 0:
        return int(math.ceil(float(amount) / term))
    return int(math.ceil(amount * rate / (1.0 - (1.0 + rate) ** (-int(term)))))


def dunning_step(stage, content=None):
    """Regeln der Mahnstufe (1 bis 3) oder None bei Stufe 0."""
    steps = loan_rules(content)["mahnung"]["stufen"]
    return steps[min(stage, len(steps)) - 1] if stage > 0 else None


def loan_interest(loan, dunning=0, content=None):
    """Aktueller Zinssatz eines Kredits: vereinbart plus Mahnaufschlag."""
    step = dunning_step(dunning, content)
    return round(float(loan["zins"]) + (float(step.get("zins_plus", 0)) if step else 0), 2)


def loan_due(loan, dunning=0, content=None):
    """Rate beim naechsten Feierabend (die letzte ist meist kleiner)."""
    interest = int(round(loan["rest"] * day_interest(loan_interest(loan, dunning, content),
                                                      content)))
    return min(loan["rate"], loan["rest"] + loan["zins_offen"] + loan["gebuehren"] + interest)


def loan_payoff(loan, content=None):
    """Vorzeitig abloesen: Restschuld, offene Zinsen und Gebuehren plus
    Vorfaelligkeitsentschaedigung (Prozent der Restschuld)."""
    fee = int(math.ceil(loan["rest"] * float(loan_rules(content)["abloesen_prozent"]) / 100.0))
    result = {"tilgung": loan["rest"], "zinsen": loan["zins_offen"],
              "gebuehren": loan["gebuehren"] + fee, "vorfaelligkeit": fee}
    result["gesamt"] = result["tilgung"] + result["zinsen"] + result["gebuehren"]
    return result


def loan_schedule(loan, start_day, dunning=0, content=None, limit=1000):
    """Tilgungsplan ab start_day, wenn jede Rate klappt: [{"tag", "rate",
    "zinsen", "tilgung", "gebuehren", "rest"}]."""
    rest, interest_open, fees = loan["rest"], loan["zins_offen"], loan["gebuehren"]
    rate_day = day_interest(loan_interest(loan, dunning, content), content)
    rows = []
    day = start_day
    while (rest > 0 or interest_open > 0 or fees > 0) and len(rows) < limit:
        interest_open += int(round(rest * rate_day))
        due = min(loan["rate"], rest + interest_open + fees)
        paid_fees = min(due, fees)
        paid_interest = min(due - paid_fees, interest_open)
        repay = due - paid_fees - paid_interest
        fees -= paid_fees
        interest_open -= paid_interest
        rest -= repay
        rows.append({"tag": day, "rate": due, "zinsen": paid_interest, "tilgung": repay,
                     "gebuehren": paid_fees, "rest": max(0, rest)})
        if due <= 0:
            break
        day += 1
    return rows


def loan_offer_numbers(amount, term, content=None):
    """Zins, Rate und Kosten eines neuen Kredits (ohne Bonitaetspruefung)."""
    rate_pa = loan_rate_pa(amount, term, content)
    rate = annuity(amount, rate_pa, term, content)
    loan = {"rest": int(amount), "zins_offen": 0, "gebuehren": 0, "rate": rate,
            "zins": rate_pa}
    rows = loan_schedule(loan, 1, 0, content)
    interest = sum(row["zinsen"] for row in rows)
    return {"summe": int(amount), "laufzeit": int(term), "zins": rate_pa, "rate": rate,
            "zinsen_gesamt": interest, "gesamt": int(amount) + interest}


def firm_income_recent(state, days, content=None):
    """Umsatz der Firma in den letzten `days` abgeschlossenen Arbeitstagen
    (Mitarbeiter, Kundentickets, Angebote, Projekte - ohne Kredite)."""
    kinds = (BOOK_REVENUE, BOOK_TICKETS, BOOK_OFFERS, BOOK_PROJECTS)
    first = state.day - int(days)
    total = 0
    for day, entry in state.book.items():
        if first <= day < state.day:
            total += sum(value for kind, value in entry["ein"].items() if kind in kinds)
    return total


def firm_profit_recent(state, days, content=None):
    """Durchschnittlicher Gewinn pro Arbeitstag der letzten `days` Arbeitstage
    vor Kreditkosten: Umsatz minus Gehaelter, Nebenkosten und Material."""
    kinds_in = (BOOK_REVENUE, BOOK_TICKETS, BOOK_OFFERS, BOOK_PROJECTS)
    # Ab 0.42 auch Werbung und die Umsatzsteuer (Ruecklage minus Erstattung)
    kinds_out = (BOOK_WAGES, BOOK_COSTS, BOOK_MATERIAL, BOOK_MARKETING, BOOK_TAX)
    first = state.day - int(days)
    total = 0
    for day, entry in state.book.items():
        if first <= day < state.day:
            total += sum(value for kind, value in entry["ein"].items() if kind in kinds_in)
            total -= sum(value for kind, value in entry["aus"].items() if kind in kinds_out)
            total += entry["ein"].get(BOOK_TAX, 0)
    return total / float(max(1, int(days)))


def rate_limit(state, content=None):
    """(hoechstens tragbare Raten pro Arbeitstag, davon schon belegt) - die
    Bank prueft die Kapitaldienstfaehigkeit (ab 0.41)."""
    rules = loan_rules(content)
    profit = firm_profit_recent(state, rules["bonitaet"]["umsatz_tage"], content)
    top = max(0, int(profit * float(rules["rahmen"].get("raten_anteil", 1.0))))
    used = sum(loan["rate"] for loan in state.running_loans())
    return top, used


def credit_check(state, content=None):
    """Bonitaet der Firma: {"ok", "punkte" [{"text", "ok"}], "umsatz",
    "rahmen", "frei", "ab_tag", "sperre"} - "frei" ist, was vom Kreditrahmen
    noch nicht durch laufende Kredite belegt ist."""
    rules = loan_rules(content)
    rule = rules["bonitaet"]
    result = {"ok": False, "punkte": [], "umsatz": 0, "rahmen": 0, "frei": 0, "ab_tag": 0,
              "sperre": "", "raten_max": 0, "raten_belegt": 0}
    if not state.firm:
        result["punkte"].append({"text": "Eigene Firma gegründet", "ok": False})
        return result
    since = state.day - int(state.firm["tag"])
    result["ab_tag"] = int(state.firm["tag"]) + int(rule["firmentage"])
    income = firm_income_recent(state, rule["umsatz_tage"], content)
    result["umsatz"] = income
    points = [
        {"text": "Firma seit mindestens %d Arbeitstagen (jetzt %d)"
                 % (rule["firmentage"], since), "ok": since >= int(rule["firmentage"])},
        {"text": "Umsatz der letzten %d Arbeitstage mindestens %s (jetzt %s)"
                 % (rule["umsatz_tage"], _whole_euro(rule["mindest_umsatz"]),
                    _whole_euro(income)), "ok": income >= int(rule["mindest_umsatz"])},
        {"text": "Ansehen mindestens %d %% (jetzt %d %%)"
                 % (rule["mindest_reputation"], round(state.mean_reputation)),
         "ok": state.mean_reputation >= float(rule["mindest_reputation"])},
    ]
    step = dunning_step(state.dunning, content)
    if step is not None:
        factor = float(step.get("rahmen_faktor", 0))
        points.append({"text": "Keine Mahnstufe, die neue Kredite sperrt (jetzt: %s%s)" % (
            step["name"], ", nur %d %% des Rahmens" % round(100 * factor) if factor else ""),
            "ok": factor > 0})
    result["punkte"] = points
    result["ok"] = all(point["ok"] for point in points)
    frame = rules["rahmen"]
    factor = float(frame["faktor_umsatz"])
    for bonus in sorted(frame.get("ansehen_bonus") or [], key=lambda item: -item["ab"]):
        if state.mean_reputation >= bonus["ab"]:
            factor *= float(bonus["faktor"])
            break
    if step is not None:
        factor *= float(step.get("rahmen_faktor", 0))
        if not float(step.get("rahmen_faktor", 0)):
            result["sperre"] = ("Bei „%s“ gibt dir die Bank keinen neuen Kredit. Die Stufe "
                                "sinkt nach %d Arbeitstagen ohne geplatzte Rate."
                                % (step["name"], rules["mahnung"]["abbau_tage"]))
    step_size = int(frame["runden"])
    limit = min(int(frame["hoechstens"]), int(income * factor) // step_size * step_size)
    result["rahmen"] = limit if result["ok"] else 0
    result["frei"] = max(0, result["rahmen"] - sum(loan["rest"]
                                                   for loan in state.running_loans()))
    result["raten_max"], result["raten_belegt"] = rate_limit(state, content)
    return result


def credit_frame_text(check):
    """ "Tragbare Raten: ..." unter dem Kreditrahmen."""
    return ("Tragbare Raten: höchstens %s pro Arbeitstag (die Hälfte des Gewinns der letzten "
            "Arbeitstage), davon belegt %s." % (_whole_euro(check["raten_max"]),
                                               _whole_euro(check["raten_belegt"])))


def credit_wait_text(state, check):
    """Hinweis, solange die Firma noch keinen Kredit bekommt."""
    if check["sperre"]:
        return "Gerade gibt dir die Bank keinen neuen Kredit. Die Bank prüft:"
    if state.firm and state.day < check["ab_tag"]:
        return ("Noch bekommt deine Firma keinen Kredit. Frühestens ab Arbeitstag %d, wenn dann "
                "auch Umsatz und Ansehen reichen. Die Bank prüft:" % check["ab_tag"])
    return "Noch bekommt deine Firma keinen Kredit. Die Bank prüft:"


def loan_offer(state, amount, term, package=None, content=None, check=None):
    """Angebot der Bank fuer Summe und Laufzeit - mit "problem", falls es
    (gerade) nicht geht."""
    rules = loan_rules(content)
    amount, term = int(amount), int(term)
    problem = ""
    if term not in loan_terms(content):
        return {"summe": amount, "laufzeit": term, "problem": "Diese Laufzeit bietet die "
                "Bank nicht an."}
    offer = loan_offer_numbers(amount, term, content)
    check = check or credit_check(state, content)
    free = rules["frei"]
    if not state.firm:
        problem = "Kredite gibt es nur für die eigene Firma."
    elif check["sperre"]:
        problem = check["sperre"]
    elif not check["ok"]:
        problem = "Deine Firma ist noch nicht kreditwürdig."
    elif package is None and (amount < int(free["min"]) or amount % int(free["schritt"])):
        problem = "Die Bank leiht mindestens %s, in Schritten von %s." % (
            _whole_euro(free["min"]), _whole_euro(free["schritt"]))
    elif amount > check["frei"]:
        problem = "Dein Kreditrahmen reicht dafür nicht (frei: %s)." % _whole_euro(
            check["frei"])
    elif offer["rate"] + check["raten_belegt"] > check["raten_max"]:
        problem = ("Die Rate ist zu hoch: Alle Raten zusammen dürfen höchstens %s pro "
                   "Arbeitstag sein (die Hälfte deines Gewinns), %s sind schon belegt. Eine "
                   "längere Laufzeit senkt die Rate." % (
                       _whole_euro(check["raten_max"]), _whole_euro(check["raten_belegt"])))
    offer["problem"] = problem
    offer["paket"] = package["id"] if package else FREE_LOAN
    offer["name"] = package["name"] if package else "Freier Kredit %s" % _whole_euro(amount)
    return offer


def loan_packages(state, content=None):
    """Die festen Kreditpakete mit Zins, Rate und ob sie gerade gehen."""
    check = credit_check(state, content)
    result = []
    for package in loan_rules(content)["pakete"]:
        offer = loan_offer(state, package["summe"], package["laufzeit"], package, content,
                           check)
        offer["text"] = package.get("text", "")
        result.append(offer)
    return result


def free_loan_limits(state, content=None):
    """(kleinste, groesste, Schritt) fuer die frei waehlbare Summe."""
    rule = loan_rules(content)["frei"]
    check = credit_check(state, content)
    step = int(rule["schritt"])
    top = check["frei"] // step * step
    return int(rule["min"]), max(int(rule["min"]), top), step


def clamp_loan_amount(state, amount, content=None):
    low, high, step = free_loan_limits(state, content)
    amount = int(amount) // step * step
    return max(low, min(high, amount))


def percent_text(value):
    """8.5 -> "8,5 %", 10.0 -> "10 %" """
    text = ("%.2f" % float(value)).rstrip("0").rstrip(".")
    return "%s %%" % text.replace(".", ",")


def term_text(term):
    return "1 Arbeitstag" if int(term) == 1 else "%d Arbeitstage" % int(term)


def loan_offer_text(offer):
    """Eine Zeile zu einem Angebot (PC und Handy gleich)."""
    return "%s über %s · %s p. a. · Rate %s pro Arbeitstag · Zinsen gesamt %s" % (
        _whole_euro(offer["summe"]), term_text(offer["laufzeit"]), percent_text(offer["zins"]),
        _whole_euro(offer["rate"]), _whole_euro(offer["zinsen_gesamt"]))


def loan_confirm_text(offer, content=None):
    what = ("Einen Kredit über %s" % _whole_euro(offer["summe"]) if offer["paket"] == FREE_LOAN
            else "„%s“ über %s" % (offer["name"], _whole_euro(offer["summe"])))
    return ("%s bei der %s aufnehmen?\n\nLaufzeit %s, Zins %s p. a. Jeden "
            "Feierabend werden automatisch %s abgebucht (Zins und Tilgung). Zurück zahlst du "
            "insgesamt %s, davon %s Zinsen.\n\nReicht das Konto beim Feierabend nicht, platzt "
            "die Rate: Mahnstufe, Gebühr und weniger Ansehen." % (
                what, loan_rules(content)["bank"],
                term_text(offer["laufzeit"]), percent_text(offer["zins"]),
                _whole_euro(offer["rate"]), _whole_euro(offer["gesamt"]),
                _whole_euro(offer["zinsen_gesamt"])))


def loan_status(state, loan, content=None):
    """Anzeige eines laufenden Kredits: Restschuld, Zins, Rate, restliche
    Raten, bisher bezahlt, Tilgungsplan (ab dem laufenden Arbeitstag)."""
    rows = loan_schedule(loan, state.day, state.dunning, content)
    payoff = loan_payoff(loan, content)
    return {"id": loan["id"], "name": loan["name"], "summe": loan["summe"],
            "tag": loan["tag"], "rest": loan["rest"] + loan["zins_offen"] + loan["gebuehren"],
            "tilgung_offen": loan["rest"], "zins": loan_interest(loan, state.dunning, content),
            "zins_vereinbart": loan["zins"], "rate": loan["rate"],
            "naechste_rate": rows[0]["rate"] if rows else 0,
            "raten_bezahlt": loan["raten"], "raten_offen": len(rows),
            "ausfaelle": loan["ausfaelle"], "gebuehren": loan["gebuehren"],
            "bezahlt_zins": loan["bezahlt_zins"], "bezahlt_tilgung": loan["bezahlt_tilgung"],
            "bezahlt_gebuehren": loan["bezahlt_gebuehren"],
            "zinsen_noch": sum(row["zinsen"] for row in rows),
            "letzter_tag": rows[-1]["tag"] if rows else state.day,
            "plan": rows, "abloesen": payoff}


def loan_status_lines(item):
    """Zeilen zu einem laufenden Kredit (PC und Handy gleich)."""
    lines = ["Restschuld %s von %s · Zins %s p. a.%s" % (
        _whole_euro(item["rest"]), _whole_euro(item["summe"]), percent_text(item["zins"]),
        " (mit Mahnaufschlag)" if item["zins"] > item["zins_vereinbart"] else ""),
        "Rate %s pro Arbeitstag · %d von %d Raten bezahlt · noch %s (bis Arbeitstag %d)" % (
            _whole_euro(item["rate"]), item["raten_bezahlt"],
            item["raten_bezahlt"] + item["raten_offen"], term_text(item["raten_offen"]),
            item["letzter_tag"]),
        "Bisher bezahlt: Zinsen %s · Tilgung %s%s" % (
            _whole_euro(item["bezahlt_zins"]), _whole_euro(item["bezahlt_tilgung"]),
            " · Gebühren %s" % _whole_euro(item["bezahlt_gebuehren"])
            if item["bezahlt_gebuehren"] else "")]
    if item["ausfaelle"]:
        lines.append("Geplatzte Raten: %d%s" % (
            item["ausfaelle"], " · offene Gebühren %s" % _whole_euro(item["gebuehren"])
            if item["gebuehren"] else ""))
    return lines


def loan_plan_rows(item, count=8):
    """Die naechsten Zeilen des Tilgungsplans plus (falls mehr) die letzte:
    [(tag, rate, zinsen, tilgung, rest)], dazu die Zahl ausgelassener Zeilen."""
    rows = item["plan"]
    shown = rows[:count]
    skipped = 0
    if len(rows) > count:
        skipped = len(rows) - count - 1
        shown = shown + [rows[-1]]
    return [(row["tag"], row["rate"], row["zinsen"], row["tilgung"] + row["gebuehren"],
             row["rest"]) for row in shown], skipped


def loan_payoff_text(item, content=None):
    payoff = item["abloesen"]
    return ("„%s“ jetzt ablösen? Du zahlst %s: Restschuld %s%s und %s "
            "Vorfälligkeitsentschädigung (%s der Restschuld)." % (
                item["name"], _whole_euro(payoff["gesamt"]), _whole_euro(payoff["tilgung"]),
                (", offene Zinsen und Gebühren %s" % _whole_euro(
                    payoff["zinsen"] + payoff["gebuehren"] - payoff["vorfaelligkeit"]))
                if payoff["zinsen"] + payoff["gebuehren"] - payoff["vorfaelligkeit"] else "",
                _whole_euro(payoff["vorfaelligkeit"]),
                percent_text(loan_rules(content)["abloesen_prozent"])))


def dunning_text(state, content=None):
    """Hinweis zur Mahnstufe (leer bei Stufe 0)."""
    step = dunning_step(state.dunning, content)
    if step is None:
        return ""
    rules = loan_rules(content)["mahnung"]
    left = max(1, int(rules["abbau_tage"]) - (state.day - 1 - state.dunning_day))
    effects = ["jede weitere geplatzte Zahlung (Kreditrate oder Umsatzsteuer) kostet "
               "Gebühren und Ansehen"]
    if step.get("zins_plus"):
        effects.append("Zinsaufschlag %s auf alle Kredite" % percent_text(step["zins_plus"]))
    effects.append("keine neuen Kredite" if not float(step.get("rahmen_faktor", 0)) else
                   "nur %d %% des Kreditrahmens" % round(100 * float(step["rahmen_faktor"])))
    return ("Mahnstufe %d von %d: %s. Folgen: %s. Ohne geplatzte Zahlung sinkt die Stufe %s." % (
        state.dunning, len(rules["stufen"]), step["name"], ", ".join(effects),
        "beim nächsten Feierabend" if left == 1 else "nach %d Arbeitstagen" % left))


def loans_today(after, day):
    """Was beim Feierabend mit den Krediten passiert ist (nur Anzeige):
    [{"art", "kredit", "name", ...}] aus dem Spielstand nach dem Feierabend."""
    result = []
    for tag, kind, loan_id, data in after.loan_log:
        if tag != day or kind == "aufgenommen" or kind == "abgeloest":
            continue
        item = dict(data, art=kind, kredit=loan_id,
                    name=(after.loans.get(loan_id) or {}).get("name", ""))
        result.append(item)
    return result


def loan_day_lines(items):
    """Zeilen fuer den Feierabend."""
    lines = []
    for item in items:
        if item["art"] == "rate":
            lines.append("%s: Rate %s (Zinsen %s, Tilgung %s%s)" % (
                item["name"], _whole_euro(item["rate"]), _whole_euro(item["zinsen"]),
                _whole_euro(item["tilgung"]),
                ", Gebühren %s" % _whole_euro(item["gebuehren"]) if item.get("gebuehren")
                else ""))
        elif item["art"] == "ausfall":
            step = item.get("stufe", 1)
            text = "%s: Rate %s geplatzt, das Konto hat nicht gereicht! Mahnstufe %d, " \
                "Gebühr %s auf die Restschuld" % (item["name"], _whole_euro(item["rate"]), step,
                                                   _whole_euro(item.get("gebuehr", 0)))
            if item.get("reputation"):
                text += ", Ansehen: %s" % ", ".join(
                    "%s %d" % (dict(AXES)[key], value) for key, value in
                    item["reputation"].items())
            lines.append(text)
        elif item["art"] == "zurueckgezahlt":
            lines.append("%s ist vollständig zurückgezahlt." % item["name"])
        elif item["art"] == "mahnstufe":
            lines.append("Pünktlich bezahlt: Die Mahnstufe sinkt auf %d." % item["stufe"])
    return lines


def fixed_costs_text(state):
    """Laufende Kosten pro Arbeitstag (Finanzen): Gehaelter, Nebenkosten,
    Kreditraten und Miete."""
    numbers = state.firm_day()
    parts = ["Gehälter %s" % _whole_euro(numbers.get("gehaelter", 0)),
             "Nebenkosten %s" % _whole_euro(numbers.get("nebenkosten", 0))]
    if state.running_loans():
        parts.append("Kreditraten %s" % _whole_euro(state.loan_rates()))
    if state.ad_costs():
        parts.append("Werbung %s" % _whole_euro(state.ad_costs()))
    if state.rent:
        parts.append("Miete %s" % _whole_euro(state.rent))
    return "Feste Kosten pro Arbeitstag: " + " · ".join(parts)


# -- Umsatzsteuer (ab 0.42) --------------------------------------------------------
#
# Alle Einnahmen der Firma sind Bruttobetraege. Die darin steckende
# Umsatzsteuer minus der Vorsteuer aus den Ausgaben (Zahllast) wandert jeden
# Feierabend in die Steuerruecklage und wird alle faellig_tage Arbeitstage an
# das Finanzamt gezahlt. Gespeichert wird nichts davon - der Spielstand rechnet
# es aus dem Kassenbuch aus (nur Feierabende mit "ust" im Ereignis zaehlen).

def tax_rules(content=None):
    return (content or GAME)["balancing"]["steuern"]


def new_tax_period():
    """Ein leerer Voranmeldungszeitraum."""
    return {"start": None, "ust": 0.0, "vst": 0.0, "umsatz": 0, "ausgaben": 0, "tage": 0}


def tax_due_amount(period):
    """Zahllast eines Zeitraums: Umsatzsteuer minus Vorsteuer (ganze Euro,
    negativ = Erstattung)."""
    return int(round(period["ust"] - period["vst"]))


def tax_share(amount, content=None):
    """Umsatzsteuer in einem Bruttobetrag (bei 19 %: 19/119 davon)."""
    rate = float(tax_rules(content)["satz"])
    return int(round(float(amount) * rate / (100.0 + rate)))


def tax_next_due(state, content=None):
    """Arbeitstag, an dessen Feierabend die naechste Voranmeldung faellig ist."""
    every = max(1, int(tax_rules(content)["faellig_tage"]))
    return state.day + every - (state.tax_days % every) - 1


def tax_status(state, content=None):
    """Anzeige fuer Finanzen: Ruecklage, laufender Zeitraum, naechste
    Faelligkeit, offene Steuerschuld und die letzten Voranmeldungen."""
    rules = tax_rules(content)
    period = state.tax_period
    filed = [data for _day, kind, data in state.tax_log if kind == "voranmeldung"]
    return {"finanzamt": rules["finanzamt"], "satz": rules["satz"],
            "ruecklage": state.tax_reserve, "schuld": state.tax_debt,
            "ust": int(round(period["ust"])), "vorsteuer": int(round(period["vst"])),
            "zahllast": tax_due_amount(period), "umsatz": period["umsatz"],
            "ausgaben": period["ausgaben"], "tage": period["tage"],
            "faellig_tage": int(rules["faellig_tage"]), "naechste": tax_next_due(state, content),
            "letzte": filed[-4:][::-1], "anzahl": len(filed),
            "gezahlt": sum(item.get("aus_ruecklage", 0) + item.get("vom_konto", 0)
                           for item in filed) +
                       sum(data["betrag"] for _day, kind, data in state.tax_log
                           if kind == "nachgezahlt"),
            "erstattet": sum(item.get("erstattung", 0) for item in filed)}


def tax_status_lines(item):
    """Zeilen zur Umsatzsteuer (PC und Handy gleich)."""
    left = item["naechste"]
    lines = ["Steuerrücklage %s · nächste Voranmeldung beim Feierabend von Arbeitstag %d" % (
        _whole_euro(item["ruecklage"]), left),
        "Dieser Zeitraum (%s): Umsatzsteuer %s aus %s Einnahmen, Vorsteuer %s aus %s "
        "Ausgaben, Zahllast bisher %s" % (
            "noch kein Feierabend" if not item["tage"] else
            term_text(item["tage"]), _whole_euro(item["ust"]), _whole_euro(item["umsatz"]),
            _whole_euro(item["vorsteuer"]), _whole_euro(item["ausgaben"]),
            ("Erstattung " + _whole_euro(-item["zahllast"])) if item["zahllast"] < 0 else
            _whole_euro(item["zahllast"]))]
    if item["anzahl"]:
        lines.append("Bisher %d Voranmeldungen · gezahlt %s%s" % (
            item["anzahl"], _whole_euro(item["gezahlt"]),
            " · erstattet %s" % _whole_euro(item["erstattet"]) if item["erstattet"] else ""))
    return lines


def tax_filing_text(data, unpaid=True):
    """Eine Voranmeldung in einer Zeile (unpaid: mit nicht bezahltem Rest)."""
    text = "Arbeitstag %d bis %d: Umsatzsteuer %s − Vorsteuer %s = " % (
        data["von"], data["bis"], _whole_euro(data["ust"]), _whole_euro(data["vorsteuer"]))
    if data.get("erstattung"):
        return text + "Erstattung %s" % _whole_euro(data["erstattung"])
    text += "Zahllast %s" % _whole_euro(data["zahllast"])
    if data.get("offen") and unpaid:
        text += " · %s konnten nicht bezahlt werden" % _whole_euro(data["offen"])
    return text


def tax_debt_text(state, content=None):
    """Warnung bei offener Steuerschuld (leer, wenn alles bezahlt ist)."""
    if not state.tax_debt:
        return ""
    return ("Offene Umsatzsteuer beim %s: %s. Sie wird beim nächsten Feierabend automatisch "
            "bezahlt, sobald das Konto reicht. Bis dahin gilt jeder Feierabend als geplatzte "
            "Zahlung (Mahnstufe wie bei Kreditraten)." % (tax_rules(content)["finanzamt"],
                                                         _whole_euro(state.tax_debt)))


def taxes_today(after, day):
    """Was beim Feierabend mit der Umsatzsteuer passiert ist (nur Anzeige)."""
    return [dict(data, art=kind) for tag, kind, data in after.tax_log if tag == day]


def tax_day_lines(items, content=None):
    """Zeilen fuer den Feierabend."""
    lines = []
    office = tax_rules(content)["finanzamt"]
    for item in items:
        if item["art"] == "ruecklage":
            if item["betrag"] > 0:
                lines.append("In die Steuerrücklage: %s (jetzt %s)" % (
                    _whole_euro(item["betrag"]), _whole_euro(item["ruecklage"])))
            else:
                lines.append("Aus der Steuerrücklage zurück (Vorsteuer): %s" % _whole_euro(
                    -item["betrag"]))
        elif item["art"] == "voranmeldung":
            text = "Umsatzsteuer-Voranmeldung ans %s: %s" % (office,
                                                            tax_filing_text(item, False))
            if item.get("aus_ruecklage"):
                text += " · aus der Rücklage %s" % _whole_euro(item["aus_ruecklage"])
            if item.get("vom_konto"):
                text += " · vom Konto %s" % _whole_euro(item["vom_konto"])
            if item.get("frei"):
                text += " · Rest der Rücklage zurück aufs Konto: %s" % _whole_euro(item["frei"])
            if item.get("offen"):
                text += " · %s konnten nicht bezahlt werden" % _whole_euro(item["offen"])
            lines.append(text)
        elif item["art"] == "nachgezahlt":
            lines.append("Offene Umsatzsteuer nachgezahlt: %s%s" % (
                _whole_euro(item["betrag"]), " (noch offen %s)" % _whole_euro(item["schuld"])
                if item["schuld"] else ""))
        elif item["art"] == "ausfall":
            text = ("Umsatzsteuer %s nicht bezahlt, das Konto hat nicht gereicht! Mahnstufe %d, "
                    "Säumnisgebühr %s" % (_whole_euro(item["betrag"]), item["stufe"],
                                          _whole_euro(item["gebuehr"])))
            if item.get("reputation"):
                text += ", Ansehen: %s" % ", ".join(
                    "%s %d" % (dict(AXES)[key], value) for key, value in
                    item["reputation"].items())
            lines.append(text)
    return lines


# -- Werbung (ab 0.42) ---------------------------------------------------------------

AD_RUNNING = "laufend"
AD_ONCE = "einmalig"
AD_MODES = ((AD_RUNNING, "Laufend"), (AD_ONCE, "Einmalig"))


def marketing_rules(content=None):
    return (content or GAME)["balancing"].get("marketing") or {"formen": []}


def ad_forms(content=None):
    return list(marketing_rules(content).get("formen") or [])


def ad_form(ad_id, content=None):
    return next((item for item in ad_forms(content) if item["id"] == ad_id), None)


def ad_active(booking, day):
    """Wirkt die gebuchte Werbung an diesem Arbeitstag?"""
    if int(booking.get("ab_tag", 0)) > day:
        return False
    if booking.get("art") == AD_ONCE:
        return day <= int(booking.get("bis_tag", 0))
    return booking.get("ende") is None or day <= int(booking["ende"])


def ad_open(booking, day):
    """Laeuft die Buchung am Tag noch oder beginnt sie erst?"""
    if booking.get("art") == AD_ONCE:
        return day <= int(booking.get("bis_tag", 0))
    return booking.get("ende") is None or day <= int(booking["ende"])


def marketing_effects(state, day=None, content=None):
    """Summe der Wirkung aller Werbung, die am Tag laeuft."""
    day = state.day if day is None else day
    result = {"anfragen": 0.0, "tickets": 0.0, "groesse": 0, "vorteil": 0}
    for booking in state.ads_active(day):
        form = ad_form(booking.get("werbung"), content or state.content) or {}
        for key, value in (form.get("wirkung") or {}).items():
            if key in result:
                result[key] += value
    return result


def _extra_count(value, seed, day, salt):
    """0,5 -> an etwa jedem zweiten Tag eins mehr (fest gewuerfelt)."""
    whole = int(value)
    return whole + (1 if _dice(seed, day, salt) < value - whole else 0)


def _share_text(value):
    return ("%.1f" % value).rstrip("0").rstrip(".").replace(".", ",")


def effect_text(effects):
    """ "+1 Anfrage pro Tag · 10 % größere Bestellungen · +2 % Preisvorteil" """
    parts = []
    if effects.get("anfragen"):
        parts.append("+%s %s pro Tag" % (_share_text(effects["anfragen"]),
                                         "Anfrage" if effects["anfragen"] == 1 else
                                         "Anfragen"))
    if effects.get("tickets"):
        parts.append("+%s %s pro Tag" % (_share_text(effects["tickets"]),
                                         "Kundenticket" if effects["tickets"] == 1 else
                                         "Kundentickets"))
    if effects.get("groesse"):
        parts.append("%d %% größere Bestellungen" % effects["groesse"])
    if effects.get("vorteil"):
        parts.append("+%d %% Preisvorteil gegen Mitbewerber" % effects["vorteil"])
    return " · ".join(parts)


def ad_offer(state, ad_id, mode, content=None):
    """Was eine Buchung kostet - mit "problem", falls es gerade nicht geht."""
    form = ad_form(ad_id, content or state.content)
    if form is None:
        return {"problem": "Diese Werbeform gibt es nicht."}
    result = {"id": ad_id, "name": form["name"], "art": mode, "kosten": 0, "preis": 0,
              "tage": 0, "problem": ""}
    if mode == AD_ONCE:
        result.update(preis=int(form["einmalig"]["preis"]), tage=int(form["einmalig"]["tage"]))
    elif mode == AD_RUNNING:
        result["kosten"] = int(form["laufend"])
    else:
        result["problem"] = "Bitte wähle laufend oder einmalig."
        return result
    booking = state.ad_booking(ad_id, state.day)
    if not state.firm:
        result["problem"] = "Werbung gibt es nur für die eigene Firma."
    elif booking is not None:
        result["problem"] = ("„%s“ läuft schon." % form.get("kurz", form["name"]) if
                             booking.get("art") == AD_RUNNING else
                             "„%s“ läuft noch bis Arbeitstag %d." % (
                                 form.get("kurz", form["name"]), booking["bis_tag"]))
    elif mode == AD_ONCE and state.money < result["preis"]:
        result["problem"] = "Dafür reicht dein Geld nicht (%s fehlen)." % _whole_euro(
            result["preis"] - max(0, state.money))
    elif mode == AD_RUNNING and state.money <= 0:
        result["problem"] = "Mit leerem Konto kannst du keine Werbung buchen."
    return result


def ad_status(state, content=None):
    """Alle Werbeformen mit Stand: [{"id", "name", "text", "wirkung", "laufend",
    "einmalig" {preis, tage}, "buchung", "stand", "angebote" {art: ad_offer}}]"""
    content = content or state.content
    result = []
    for form in ad_forms(content):
        booking = state.ad_booking(form["id"], state.day)
        status = ""
        if booking is not None:
            start = int(booking["ab_tag"])
            if booking["art"] == AD_RUNNING:
                status = "Läuft dauerhaft · %s pro Arbeitstag" % _whole_euro(booking["kosten"])
                if booking.get("ende") is not None:
                    status = "Gekündigt · heute zum letzten Mal"
                elif start > state.day:
                    status += " · wirkt ab dem nächsten Arbeitstag"
                else:
                    status += " · seit Arbeitstag %d" % start
            else:
                left = int(booking["bis_tag"]) - max(state.day, start - 1)
                if start > state.day:
                    status = "Einmalig gebucht · wirkt ab dem nächsten Arbeitstag für %s" % (
                        term_text(left))
                else:
                    status = "Einmalig gebucht · wirkt noch %s (bis Arbeitstag %d)" % (
                        "heute" if left <= 0 else term_text(left + 1), booking["bis_tag"])
        result.append({"id": form["id"], "name": form["name"],
                       "kurz": form.get("kurz", form["name"]), "text": form.get("text", ""),
                       "wirkung": effect_text(form.get("wirkung") or {}),
                       "laufend": int(form["laufend"]), "einmalig": dict(form["einmalig"]),
                       "buchung": booking, "stand": status,
                       "aktiv": booking is not None and ad_active(booking, state.day),
                       "angebote": {mode: ad_offer(state, form["id"], mode, content)
                                    for mode, _label in AD_MODES}})
    return result


def ad_price_text(item):
    """ "Laufend 110 € pro Arbeitstag · Einmalig 900 € für 10 Arbeitstage" """
    once = item["einmalig"]
    return "Laufend %s pro Arbeitstag · einmalig %s für %s (%s pro Tag)" % (
        _whole_euro(item["laufend"]), _whole_euro(once["preis"]), term_text(once["tage"]),
        _whole_euro(int(round(once["preis"] / float(once["tage"])))))


def ad_confirm_text(offer, content=None):
    if offer["art"] == AD_ONCE:
        return ("„%s“ einmalig buchen?\n\nDu zahlst sofort %s. Die Werbung wirkt ab dem "
                "nächsten Arbeitstag %s lang und endet dann von selbst." % (
                    offer["name"], _whole_euro(offer["preis"]), term_text(offer["tage"])))
    return ("„%s“ dauerhaft buchen?\n\nJeden Feierabend werden automatisch %s abgebucht, "
            "bis du kündigst. Die Werbung wirkt ab dem nächsten Arbeitstag." % (
                offer["name"], _whole_euro(offer["kosten"])))


def marketing_summary_text(state, content=None):
    """Was die Werbung heute bewirkt (Kopf des Reiters Marketing)."""
    effects = marketing_effects(state, content=content)
    text = effect_text(effects)
    costs = state.ad_costs()
    if not text:
        return "Gerade läuft keine Werbung. Ohne Werbung kommen nur die üblichen Anfragen."
    return "Deine Werbung bringt heute: %s.%s" % (
        text, " Laufende Kosten: %s pro Arbeitstag." % _whole_euro(costs) if costs else "")


# -- Zertifizierungen (ab 0.42) ------------------------------------------------------

GROSS_PREFIX = "gross:"            # gross:<nummer der ausschreibung>


def cert_rules(content=None):
    return (content or GAME)["balancing"].get("zertifizierungen") or {"liste": []}


def certificates(content=None):
    return list(cert_rules(content).get("liste") or [])


def certificate(cert_id, content=None):
    return next((item for item in certificates(content) if item["id"] == cert_id), None)


def advantage_text(advantage):
    """{"alle": 2, "sicherheit": 4} -> "+2 % bei allen Angeboten · +4 % bei
    Sicherheits-Projekten" """
    parts = []
    for key, value in advantage.items():
        if key == "alle":
            parts.append("+%d %% bei allen Angeboten" % value)
        else:
            parts.append("+%d %% bei Projekten %s" % (value, CAT_NAME.get(key, key)))
    return " · ".join(parts)


def cert_advantage(state, cat=None, day=None, content=None):
    """Preisvorteil aus allen abgeschlossenen Zertifizierungen."""
    total = 0
    for cert_id in state.certs_held(day):
        advantage = (certificate(cert_id, content or state.content) or {}).get("vorteil") or {}
        total += int(advantage.get("alle", 0))
        if cat:
            total += int(advantage.get(cat, 0))
    return total


def cert_offer(state, cert_id, content=None):
    content = content or state.content
    cert = certificate(cert_id, content)
    if cert is None:
        return {"problem": "Diese Zertifizierung gibt es nicht."}
    result = {"id": cert_id, "name": cert["name"], "preis": int(cert["preis"]),
              "tage": int(cert["tage"]), "problem": ""}
    running = state.cert_running()
    limit = int(cert_rules(content).get("gleichzeitig", 1))
    if not state.firm:
        result["problem"] = "Zertifizierungen gibt es nur für die eigene Firma."
    elif cert_id in state.certs_held():
        result["problem"] = "Deine Firma hat diese Zertifizierung schon."
    elif cert_id in state.certs:
        result["problem"] = "Läuft schon, fertig beim Feierabend von Arbeitstag %d." % (
            int(state.certs[cert_id]["bis_tag"]) - 1)
    elif len(running) >= limit:
        other = certificate(running[0]["zert"], content) or {}
        result["problem"] = ("Es läuft schon eine Zertifizierung (%s, bis Arbeitstag %d)."
                             % (other.get("kurz", ""), int(running[0]["bis_tag"]) - 1))
    elif state.money < result["preis"]:
        result["problem"] = "Dafür reicht dein Geld nicht (%s fehlen)." % _whole_euro(
            result["preis"] - max(0, state.money))
    return result


def cert_status(state, content=None):
    """Alle Zertifizierungen mit Stand: [{"id", "name", "kurz", "art", "text",
    "preis", "tage", "vorteil", "freischaltet" [titel], "stand" ("erworben",
    "laeuft", "offen"), "stand_text", "angebot"}]"""
    content = content or state.content
    gross = gross_rules(content).get("liste") or []
    held = state.certs_held()
    result = []
    for cert in certificates(content):
        data = state.certs.get(cert["id"])
        if cert["id"] in held:
            stand, text = "erworben", "Erworben an Arbeitstag %d" % int(data["bis_tag"])
        elif data:
            stand = "laeuft"
            left = int(data["bis_tag"]) - state.day
            text = "Läuft · fertig %s" % ("beim heutigen Feierabend" if left <= 1 else
                                          "in %d Arbeitstagen" % left)
        else:
            stand, text = "offen", ""
        result.append({"id": cert["id"], "name": cert["name"],
                       "kurz": cert.get("kurz", cert["name"]), "art": cert.get("art", "firma"),
                       "text": cert.get("text", ""), "preis": int(cert["preis"]),
                       "tage": int(cert["tage"]),
                       "vorteil": advantage_text(cert.get("vorteil") or {}),
                       "freischaltet": [item["titel"] for item in gross
                                        if cert["id"] in item.get("braucht", [])],
                       "stand": stand, "stand_text": text,
                       "angebot": cert_offer(state, cert["id"], content)})
    return result


def cert_unlock_text(item, content=None):
    """ "Schaltet frei: ... (zusammen mit DSGVO)" """
    if not item["freischaltet"]:
        return ""
    return "Schaltet Großaufträge frei: " + "; ".join("„%s“" % title
                                                      for title in item["freischaltet"])


def cert_confirm_text(offer, content=None):
    return ("„%s“ beginnen?\n\nKosten %s sofort. Audit, Schulungen und Prüfung dauern %s, "
            "danach gilt die Zertifizierung dauerhaft. Deine Leute arbeiten in der Zeit "
            "normal weiter." % (offer["name"], _whole_euro(offer["preis"]),
                                term_text(offer["tage"])))


def certs_summary_text(state, content=None):
    held = state.certs_held()
    if not held:
        return ("Noch keine Zertifizierung. Mit Zertifizierungen bekommst du große und "
                "öffentliche Aufträge und bessere Chancen gegen die Mitbewerber.")
    names = [item.get("kurz", item["name"]) for item in certificates(content or state.content)
             if item["id"] in held]
    return "Deine Firma ist zertifiziert: %s." % ", ".join(names)


def offer_advantage_parts(state, cat=None, content=None):
    """Woraus sich der Preisvorteil zusammensetzt: [(grund, prozent)]."""
    content = content or state.content
    rule = offer_rules(content)["vorteil"]
    parts = []
    if state.reputation.get("kundenzufriedenheit", 0) >= rule["ab_kundenzufriedenheit"]:
        parts.append(("guter Ruf", int(rule["prozent"])))
    certs = cert_advantage(state, cat, content=content)
    if certs:
        parts.append(("Zertifizierungen", certs))
    ads = int(marketing_effects(state, content=content)["vorteil"])
    if ads:
        parts.append(("Werbung", ads))
    return parts


# -- Grossauftraege (ab 0.42) --------------------------------------------------------

def gross_rules(content=None):
    return cert_rules(content).get("grossauftraege") or {}


def gross_template(entry_id, content=None):
    return next((item for item in gross_rules(content).get("liste") or []
                 if item["id"] == entry_id), None)


def gross_tenders(state, day, content=None):
    """Grosse und oeffentliche Ausschreibungen, die am Tag vorliegen. Alle
    abstand_tage Arbeitstage eine, wenn die Firma an deren erstem Tag die
    noetigen Zertifizierungen hat - bevorzugt, was noch nicht dran war, und
    nie zweimal hintereinander dieselbe und keine, die gerade als Projekt
    laeuft (sonst faellt die Ausschreibung aus)."""
    content = content or GAME
    rules = gross_rules(content)
    if not state.firm or not rules.get("liste") or not state.certs:
        return []
    gap, valid = int(rules["abstand_tage"]), int(rules["gilt_tage"])
    first = int(state.firm["tag"]) + int(rules.get("versatz", 0))
    seed = state.firm_seed
    used = {}
    result = []
    slot = 0
    last = None
    while first + slot * gap <= day:
        start = first + slot * gap
        held = state.certs_held(start)
        busy = {project.get("vorlage") for project in state.projects.values()
                if int(project.get("tag", 0) or 0) < start and
                (not project["fertig"] or project["fertig"] >= start)}
        options = [item for item in rules["liste"] if held and item["id"] != last and
                   GROSS_PREFIX + item["id"] not in busy and
                   set(item.get("braucht") or []) <= held]
        last = None
        if options:
            fewest = min(used.get(item["id"], 0) for item in options)
            options = [item for item in options if used.get(item["id"], 0) == fewest]
            entry = min(options, key=lambda item: _dice(seed, start, "gross|" + item["id"]))
            used[entry["id"]] = used.get(entry["id"], 0) + 1
            last = entry["id"]
            if start + valid - 1 >= day:
                result.append(_gross_tender(state, entry, slot, start, content))
        slot += 1
    return result


def _gross_tender(state, entry, slot, start, content):
    rules = gross_rules(content)
    level = rules["stufe"]
    salt = "gross%d-" % slot
    seed = state.firm_seed
    low, high = level["material"]
    material = int(round((low + _dice(seed, start, salt + "material") * (high - low)) / 10.0)
                   * 10)
    shift = market_shift(state, start, content)
    bids, absent = competitor_bids("projekt", "normal", entry["cat"], seed, start, salt,
                                   content, extra=rules.get("mitbieter_extra", 0),
                                   shift=shift["shift"])
    cheapest = min(bids, key=lambda bid: bid["zuschlag"])
    project_id = "%s%d" % (GROSS_PREFIX, slot + 1)
    what = "Öffentliche Ausschreibung" if entry.get("oeffentlich") else "Großauftrag"
    names = [(certificate(cert_id, content) or {}).get("kurz", cert_id)
             for cert_id in entry.get("braucht") or []]
    return {"id": project_id, "slot": slot, "vorlage": GROSS_PREFIX + entry["id"], "folge": 0,
            "titel": entry["titel"], "kunde": entry["kunde"], "kunde_kurz": entry["kunde_kurz"],
            "cat": entry["cat"], "thema": entry.get("thema"),
            "schwierigkeit": level.get("name", "Großauftrag"),
            "aufwand": int(level["aufwand"]), "anforderung": int(level["anforderung"]),
            "material": discounted(material, state.room_effect("material_rabatt")),
            "material_markt": material, "frist": int(level["frist"]), "von_tag": start,
            "bis_tag": start + int(rules["gilt_tage"]) - 1,
            "markt": cheapest["zuschlag"], "laune": cheapest["laune"],
            "konkurrent": cheapest["id"], "bieter": bids, "ausgefallen": absent,
            "text": "%s von „%s“: %s" % (what, entry["kunde"], entry["auftrag"]),
            "ausgangssituation": entry["ausgangssituation"], "auftrag": entry["auftrag"],
            "rahmenbedingungen": list(entry.get("rahmenbedingungen") or []),
            "gross": True, "oeffentlich": bool(entry.get("oeffentlich")),
            "braucht": list(entry.get("braucht") or []), "zertifikate": names,
            "gegenwind": shift["gegenwind"],
            "ergebnis": state.project_offers.get(project_id)}


def gross_badge_text(project):
    """ "Öffentlicher Großauftrag · nur mit ISO 27001" (leer bei normalen Projekten)"""
    if not project.get("gross") and not str(project.get("vorlage", "")).startswith(
            GROSS_PREFIX):
        return ""
    entry = gross_template(str(project.get("vorlage", ""))[len(GROSS_PREFIX):]) or {}
    names = [(certificate(cert_id) or {}).get("kurz", cert_id)
             for cert_id in entry.get("braucht") or project.get("braucht") or []]
    return "%s · nur mit %s" % ("Öffentlicher Großauftrag" if entry.get("oeffentlich")
                                else "Großauftrag", " und ".join(names))


def project_details(project, content=None):
    """Kunde, Ausgangssituation, Auftrag und Rahmenbedingungen eines Projekts
    (Projektarbeit aus dem Lernbereich oder Grossauftrag): {"kunde",
    "ausgangssituation", "auftrag", "rahmenbedingungen", "lernbar"}"""
    content = content or GAME
    template = str(project.get("vorlage", ""))
    if template.startswith(GROSS_PREFIX):
        entry = gross_template(template[len(GROSS_PREFIX):], content) or project
        return {"kunde": entry.get("kunde", ""),
                "ausgangssituation": entry.get("ausgangssituation", ""),
                "auftrag": entry.get("auftrag", ""),
                "rahmenbedingungen": list(entry.get("rahmenbedingungen") or []),
                "lernbar": False}
    item = (content.get("projektarbeiten") or [])[project["vorlage"]]
    return {"kunde": item["branche"], "ausgangssituation": item["ausgangssituation"],
            "auftrag": item["auftrag"],
            "rahmenbedingungen": list(item.get("rahmenbedingungen") or []), "lernbar": True}


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
    # Ab 0.42: Werbung bringt mehr Anfragen (Menge) und groessere Bestellungen
    ads = marketing_effects(state, day, content)
    extra = _extra_count(ads["anfragen"], seed, day, "werbung-anfragen")
    # Ab 0.44: Konjunktur (mehr oder weniger Anfragen, Preisniveau), Trend-
    # Anfragen und Gegenwind der Mitbewerber
    shift = market_shift(state, day, content)
    total = max(1, int(rules["pro_tag"]) + int(state.room_effect("anfragen_plus")) + extra +
                int(shift["markt"]["phase_info"].get("anfragen", 0)) +
                branch_inquiries(state, content))
    trend = shift["markt"]["trend"]
    hype = (market_rules(content).get("trends") or {}) if trend else {}
    with_trend = bool(trend) and _dice(seed, day, "trend-anfrage") * 100 < \
        float(hype.get("chance", 0))
    for number in range(total + (1 if with_trend else 0)):
        salt = "anfrage%d-" % number
        is_trend = with_trend and number == total
        # Verschiedene Kunden am selben Tag
        customer = customers[(first + number * max(1, len(customers) // 2 - 1))
                             % len(customers)]
        article = _pick(trend["artikel"] if is_trend else rules["artikel"], seed, day,
                        salt + "artikel")
        low, high = article["preis"]
        price = int(round((low + _dice(seed, day, salt + "preis") * (high - low)) / 5.0) * 5)
        count = _between(seed, day, salt + "menge", *article["menge"])
        if ads["groesse"]:
            count = int(math.ceil(count * (1 + ads["groesse"] / 100.0)))
        cat = trend.get("cat") if is_trend else None
        move = shift["shift"] + (int(hype.get("zuschlag", 0)) if is_trend else 0)
        bids, absent = competitor_bids("anfrage", customer["art"], cat, seed, day, salt,
                                       content, shift=move, second=shift["zweiter"])
        cheapest = min(bids, key=lambda bid: bid["zuschlag"])
        delivery = _between(seed, day, salt + "lieferzeit", rules["lieferzeit"]["von"],
                            rules["lieferzeit"]["bis"])
        text = _pick(rules["texte"], seed, day, salt + "text").format(
            kontakt=customer["kontakt"], menge=count, artikel=article["name"],
            lieferzeit=delivery)
        if is_trend and trend.get("satz"):
            text = "%s „%s“" % (text, trend["satz"])
        inquiry_id = "%s%d:%d" % (INQUIRY_PREFIX, day, number + 1)
        extras = {}
        if is_trend:
            extras = {"trend": trend["id"], "trend_name": trend["name"], "cat": cat}
        if shift["gegenwind"]:
            extras["gegenwind"] = shift["gegenwind"]
        if shift["konjunktur"]:
            extras["konjunktur"] = shift["phase"]
        result.append(dict(extras, **{"id": inquiry_id, "tag": day, "kunde": customer,
                       "artikel": article["name"], "menge": count,
                       # Mit eigenem Lager kauft man guenstiger ein als die Mitbewerber
                       "einkaufspreis": discounted(price, discount),
                       "listenpreis": price,
                       "lieferzeit": delivery, "markt": cheapest["zuschlag"],
                       "laune": cheapest["laune"], "konkurrent": cheapest["id"],
                       "bieter": bids, "ausgefallen": absent,
                       "text": "%s\n\n%s" % (text, customer["satz"]),
                       "ergebnis": state.offers.get(inquiry_id)}))
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


def offer_advantage(state, content=None, cat=None):
    """Wie viel Prozent man ueber dem guenstigsten Mitbewerber liegen darf:
    guter Ruf, ab 0.42 dazu Zertifizierungen (bei Projekten je Fachbereich)
    und Werbung - zusammen hoechstens zertifizierungen.vorteil_max."""
    total = sum(value for _reason, value in offer_advantage_parts(state, cat, content))
    top = cert_rules(content or state.content).get("vorteil_max")
    return min(int(top), total) if top is not None else total


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
    for key in ("trend", "trend_name", "gegenwind", "konjunktur"):
        if inquiry.get(key):
            payload[key] = inquiry[key]
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
    advantage = full = offer_advantage(state, content, offer.get("cat"))
    if offer.get("gegenwind"):
        # Im Gegenwind zaehlt der Preisvorteil nur anteilig (ab 0.44, fester Faktor)
        factor = (rivalry_rules(content).get("gegenwind") or {}).get("vorteil_faktor", 1)
        advantage = int(advantage * factor)
    # Ab 0.45: Naehe zum Kunden durch die Filiale (zaehlt immer voll)
    near = branch_nearness(state, (offer.get("kunde") or {}).get("id")
                           if isinstance(offer.get("kunde"), dict) else offer.get("kunde"),
                           content)
    advantage += near
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
               "vorteil_gruende": ([reason for reason, _value in offer_advantage_parts(
                   state, offer.get("cat"), content)] + (
                   [branch_rules(content)["naehe"].get("text", "Filiale")] if near else []))
               if advantage else [],
               "grund": "" if won else ("rechenfehler" if not right else "preis")}
    if near:
        payload["naehe"] = near
    if offer.get("gegenwind"):
        payload["gegenwind"] = offer["gegenwind"]
        if advantage - near < full:
            payload["vorteil_voll"] = full + near
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
    if payload.get("gegenwind"):
        text += (" Die Mitbewerber haben gezielt %d Punkte günstiger gegen dich geboten."
                 % payload["gegenwind"])
        if payload.get("vorteil_voll"):
            text += (" Dein Preisvorteil zählte dabei nur %d statt %d %%."
                     % (payload["vorteil"], payload["vorteil_voll"]))
    others = bidders_text(payload, content)
    if others:
        text += "\n\n" + others
    return head, text


def inquiry_badge_text(inquiry):
    """ "Trend-Auftrag: Cloud-Boom" (leer bei normalen Anfragen)."""
    if inquiry.get("trend_name"):
        return "Trend-Auftrag: %s" % inquiry["trend_name"]
    return ""


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
            text += (" Knapp über %s, aber %s hat den Ausschlag gegeben." % (
                rival, _reasons_text(payload)))
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
        text += " Selbst mit dem Bonus für %s (%d %%) hat es nicht gereicht." % (
            _reasons_text(payload, short=True), payload["vorteil"])
    return head, text


def _reasons_text(payload, short=False):
    """Woher der Preisvorteil kam, als Text (aeltere Ergebnisse: guter Ruf)."""
    reasons = payload.get("vorteil_gruende") or ["guter Ruf"]
    words = {"guter Ruf": ("dein guter Ruf bei den Kunden", "deinen guten Ruf"),
             "Zertifizierungen": ("deine Zertifizierungen", "deine Zertifizierungen"),
             "Werbung": ("deine Werbung", "deine Werbung")}
    names = [words.get(reason, (reason, reason))[1 if short else 0] for reason in reasons]
    text = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " und " + names[-1]
    return text


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
    einem Projekt mitarbeitet - und ab 0.43 einer weniger nach einem
    Schlichtungsgespraech."""
    limit = max(1, ticket_limit(SELF, content) - (1 if state.project_of(SELF) else 0))
    return limit - (1 if state.day in state.mediation_days else 0)


def ticket_chance(value, need, content=None, bonus=0):
    """Erfolgschance in Prozent (ganze Zahl). bonus (ab 0.43): Punkte durch
    Macke und Stimmung."""
    rule = ticket_rules(content)["chance"]
    chance = rule["basis"] + rule["je_punkt"] * (float(value) - need) + float(bonus)
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
    # Ab 0.42: Werbung bringt mehr Kundentickets
    count += _extra_count(marketing_effects(state, day, content)["tickets"], seed, day,
                          "werbung-tickets")
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
                       "cat": item["cat"], "thema": item.get("thema"),
                       "stufe": level["name"],
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
    topic = ticket.get("thema")
    result = []
    # Ab 0.38 zaehlt der Wert im Thema des Tickets (Spielfigur: Wissensstand)
    own = topic_level(levels, topic, cat)
    name = (state.profile or {}).get("name") or "Ich"
    limit = own_ticket_limit(state, content)
    problem = ""
    if limit <= 0:
        problem = "Heute hast du keine Zeit mehr für Kundentickets, das " \
                  "Schlichtungsgespräch hat deinen Platz gekostet."
    elif len(state.delegated_to(SELF)) >= limit:
        problem = "Du hast heute schon %s übernommen." % (
            "ein Kundenticket" if limit == 1 else "%d Kundentickets" % limit)
        if state.project_of(SELF):
            problem += " Mehr geht nicht, weil du im Projekt mitarbeitest."
        if state.day in state.mediation_days:
            problem += " Einen Platz hat heute das Schlichtungsgespräch gekostet."
    result.append({"an": SELF, "name": "Ich selbst (%s)" % name, "wert": own,
                   "chance": ticket_chance(own, ticket["anforderung"], content),
                   "problem": problem})
    for item in state.staff_list():
        value = int(item["themen"].get(topic, 0)) if topic else int(item["werte"].get(cat, 0))
        problem = ""
        if item.get("weiterbildung") or item.get("abwesend"):
            problem = absent_problem(item["name"], item.get("weiterbildung") or
                                     item["abwesend"])
        elif item.get("projekt"):
            problem = "%s arbeitet im Projekt „%s“ mit." % (
                item["name"], state.projects[item["projekt"]]["titel"])
        elif len(state.delegated_to(item["id"])) >= ticket_limit(item["id"], content):
            problem = "%s hat heute schon ein Kundenticket." % item["name"]
        result.append({"an": item["id"], "name": item["name"], "wert": value,
                       "chance": staff_ticket_chance(state, item["id"], ticket, value,
                                                     content),
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
        rule = dict(rules["erfolg"] if success else rules["fehlschlag"])
        if ticket["an"] in state.staff:
            # Ab 0.43: Macken, die Kunden besonders zufrieden machen
            extra = state.quirk_value(ticket["an"], "kz_erfolg" if success else
                                      "kz_fehlschlag")
            if extra:
                rule["kundenzufriedenheit"] = int(round(
                    rule.get("kundenzufriedenheit", 0) + extra))
                if not success:
                    rule["kundenzufriedenheit"] = min(0, rule["kundenzufriedenheit"])
        result.append({"ticket": ticket["id"], "vorlage": ticket["vorlage"],
                       "titel": ticket["titel"], "kunde": ticket["kunde"]["name"],
                       "an": ticket["an"], "name": ticket["name"], "erfolg": success,
                       "geld": ticket["geld"] if success else 0,
                       "reputation": {key: value for key, value in rule.items() if value}})
    return result


def subject_text(cat, topic=None):
    """ "Netzwerk · WLAN" (ohne Thema nur der Fachbereich)"""
    text = CATEGORY_SHORT[CAT_NAME[cat]]
    return "%s · %s" % (text, TOPIC_SHORT[topic]) if topic in TOPIC_SHORT else text


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
    """Zeile unter einem Kundenticket: Fachbereich, Thema, Schwierigkeit, Honorar."""
    text = "%s · %s · %s" % (subject_text(ticket["cat"], ticket.get("thema")),
                              ticket["stufe"], _whole_euro(ticket["geld"]))
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


def competitor_bids(kind, art, cat, seed, day, salt, content=None, extra=0, shift=0,
                    second=0.0):
    """Wer mitbietet: ([{"id", "zuschlag", "laune"}], [ausgefallene ids]).
    kind ist "anfrage" oder "projekt", extra zusaetzliche Bieter (Grossauftraege).
    Ab 0.44: shift Punkte auf jeden Zuschlag (Konjunktur, Trend, Gegenwind),
    second mehr Chance auf einen zweiten Bieter bei Anfragen (Gegenwind)."""
    content = content or GAME
    rules = offer_rules(content)
    setup = competitor_rules(content)
    rivals = competitors(content)
    if kind == "projekt":
        span = setup.get("projekt_bieter") or {"von": 2, "bis": 3}
        count = _between(seed, day, salt + "bieterzahl", span["von"], span["bis"])
    else:
        single = (setup.get("anfrage_bieter") or {}).get("eins", 1.0) - float(second)
        count = 1 if _dice(seed, day, salt + "bieterzahl") < single else 2
    count += int(extra)
    order = _weighted_order(rivals, [(item.get("gewicht") or {}).get(kind, 1)
                                     for item in rivals], seed, day, salt + "bieter")
    bids, absent = [], []
    for rival in order[:max(1, count)]:
        result = _rival_markup(rival, rules, art, cat, seed, day, salt)
        if result is None:
            absent.append(rival["id"])
            continue
        bids.append({"id": rival["id"], "zuschlag": max(0, int(result[0]) + int(shift)),
                     "laune": result[1]})
    if not bids:
        # Niemand da? Bitweiche bietet immer
        rival = competitor(BITWEICHE, content)
        markup, mood = _rival_markup(rival, rules, art, cat, seed, day, salt)
        bids.append({"id": BITWEICHE, "zuschlag": max(0, int(markup) + int(shift)),
                     "laune": mood})
    return bids, absent


def market_shift(state, day, content=None, trend=False):
    """Punkte auf die Zuschlaege der Mitbewerber an einem Tag (ab 0.44):
    Konjunktur, bei Trend-Anfragen der Trend, minus Gegenwind. Dazu die
    Einzelteile fuer die Anzeige."""
    content = content or state.content
    market = market_state(state, day, content)
    pressure = rivalry_pressure(state, day, content)
    boom = int(market["phase_info"].get("zuschlag", 0))
    hype = int((market_rules(content).get("trends") or {}).get("zuschlag", 0)) if trend else 0
    return {"shift": boom + hype - pressure["minus"], "konjunktur": boom, "trend": hype,
            "gegenwind": pressure["minus"], "zweiter": pressure["zweiter"],
            "phase": market["phase"], "markt": market}


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


# -- Rivalitaet und Markt (ab 0.44) -----------------------------------------
#
# Die Mitbewerber reagieren auf deinen Erfolg: Sie wollen abgeworbene Leute
# zurueck und bieten gezielt guenstiger, wenn du zu oft gewinnst. Nach der
# Story (ab markt.ab_tag) bewegt sich ausserdem der Markt: Konjunkturphasen
# und befristete Technologietrends. Alles wird aus Firmenname, Gruendungstag
# und den Ereignissen berechnet - auf PC und Handy gleich, ohne eigenen Zustand.

def rivalry_rules(content=None):
    return firm_rules(content).get("rivalitaet") or {}


def market_rules(content=None):
    return firm_rules(content).get("markt") or {}


def former_for(seed, staff_id, content=None):
    """Frueherer Arbeitgeber eines normalen Bewerbers (Mitbewerber-id oder
    leer), fest gewuerfelt aus seed und id."""
    rule = rivalry_rules(content).get("rueckhol") or {}
    share = float(rule.get("vorher_anteil", 0))
    if not share or _dice(seed, 0, "vorher|" + staff_id) * 100 >= share:
        return ""
    return _pick(competitors(content), seed, 0, "vorher-firma|" + staff_id)["id"]


def former_employer(state, staff_id, data=None):
    """Bei welchem Mitbewerber jemand vorher war (id oder leer). Aeltere
    Spielstaende kennen "vorher" nicht - dann wie beim Bewerber gewuerfelt."""
    data = data if data is not None else (state.staff.get(staff_id) or {})
    if data.get("herkunft") == "bitweiche":
        return BITWEICHE
    if "vorher" in data:
        return data.get("vorher") or ""
    if data.get("herkunft") != "bewerbung":
        return ""
    return former_for(state.firm_seed, staff_id, state.content)


def recall_factor(mood, rule):
    """Wie viel wahrscheinlicher ein Rueckhol-Angebot bei dieser Stimmung
    ist (zufriedene Leute sind seltener ansprechbar)."""
    factor = 1 + (float(rule.get("stimmung_ziel", 70)) - mood) / \
        float(rule.get("stimmung_teiler", 40) or 40)
    return max(float(rule.get("faktor_min", 0.5)), min(float(rule.get("faktor_max", 2.0)),
                                                       factor))


def recall_raise(salary, rule):
    """Neues Gehalt beim Gegenangebot (ganze Euro, mindestens +1)."""
    return max(int(salary) + 1, int(round(int(salary) * (1 + rule.get("gehalt_plus", 10)
                                                         / 100.0))))


def recall_bonus(salary, rule):
    return int(salary) * int(rule.get("bonus_tage", 10))


def _recall_events(state, day, present, taken, content):
    """Hoechstens ein Rueckhol-Angebot pro Feierabend (fest gewuerfelt)."""
    rule = rivalry_rules(content).get("rueckhol")
    if not rule:
        return []
    seed = state.firm_seed
    last = max([tag for tag, item in state.personal_log
                if item.get("art") == PERSONAL_RECALL] or [-1000])
    if day - last < int(rule.get("abstand_firma", 0)):
        return []
    for staff_id in present:
        data = state.staff[staff_id]
        rival = former_employer(state, staff_id, data)
        if not rival or staff_id in taken or staff_id in state.leaving:
            continue
        if day - int(data.get("tag", 0) or 0) < int(rule["ab_tagen"]):
            continue
        asked = [tag for tag, item in state.personal_log
                 if item.get("art") == PERSONAL_RECALL and item.get("id") == staff_id]
        if asked and day - asked[-1] < int(rule["abstand"]):
            continue
        chance = float(rule["chance"]) * recall_factor(state.mood_of(staff_id), rule)
        if _dice(seed, day, "rueckhol|" + staff_id) * 100 >= chance:
            continue
        company = competitor(rival, content)
        plus = _between(seed, day, "rueckhol-plus|" + staff_id, *rule["angebot_plus"])
        texts = (rule.get("texte_bitweiche") if rival == BITWEICHE else None) or rule["texte"]
        name = data.get("name", "")
        text = _pick(texts, seed, day, "rueckhol-text|" + staff_id).format(
            firma=company["kurz"], name=short_name({"name": name}), plus=plus)
        return [{"art": PERSONAL_RECALL, "rueckhol": "rueckhol:%d:%s" % (day, staff_id),
                 "id": staff_id, "name": name, "firma": rival, "plus": plus, "text": text}]
    return []


def _recall_decision(state, item, content):
    rule = rivalry_rules(content).get("rueckhol") or {}
    data = state.staff[item["id"]]
    first = short_name(item)
    salary = int(data.get("gehalt", 0))
    raised = recall_raise(salary, rule)
    bonus = recall_bonus(salary, rule)
    company = competitor(item.get("firma") or BITWEICHE, content)["kurz"]
    return {
        "id": item["rueckhol"], "art": DECISION_RECALL, "person": item["id"],
        "name": item["name"], "firma": item.get("firma") or BITWEICHE,
        "gehalt_neu": raised, "bonus": bonus,
        "titel": "%s will %s zurück" % (company, item["name"]),
        "text": item["text"] + " Hältst du dagegen?",
        "optionen": [
            {"id": RECALL_RAISE, "label": "Gehalt erhöhen", "problem": "",
             "folge": "%s bleibt. Gehalt dauerhaft +%d %% (%s statt %s pro Arbeitstag), "
                      "Stimmung %s." % (first, rule.get("gehalt_plus", 10),
                                        _whole_euro(raised), _whole_euro(salary),
                                        _signed(rule.get("gehalt_stimmung", 0)))},
            {"id": RECALL_BONUS, "label": "Halteprämie zahlen",
             "folge": "%s bleibt. Einmalig %s (%d Tagesgehälter), Stimmung %s." % (
                 first, _whole_euro(bonus), int(rule.get("bonus_tage", 10)),
                 _signed(rule.get("bonus_stimmung", 0))),
             "problem": "" if state.money >= bonus else
             "Für die Halteprämie reicht dein Kontostand nicht."},
            {"id": RECALL_LET, "label": "Ziehen lassen", "problem": "",
             "folge": "%s arbeitet heute noch mit und geht nach dem Feierabend zurück zu "
                      "%s. Der Platz wird frei." % (first, company)}]}


def recall_choice_text(data, content=None):
    """Wie du auf ein Rueckhol-Angebot reagiert hast."""
    company = competitor(data.get("firma") or BITWEICHE, content)["kurz"]
    choice = data.get("wahl")
    if choice == RECALL_RAISE:
        return "%s wollte %s zurück. Du hast das Gehalt auf %s erhöht." % (
            company, short_name(data), _whole_euro(data.get("gehalt", 0)))
    if choice == RECALL_BONUS:
        return "%s wollte %s zurück. Du hast eine Halteprämie von %s gezahlt." % (
            company, short_name(data), _whole_euro(-int(data.get("geld", 0))))
    return "%s hat das Angebot von %s angenommen." % (short_name(data), company)


def _decided_offers(state):
    """Alle Angebote (Anfragen und Projekte) als [(tag, id, gewonnen)]."""
    items = [(int(item.get("tag") or 0), str(item.get("anfrage") or item.get("projekt") or ""),
              bool(item.get("gewonnen")))
             for item in list(state.offers.values()) + list(state.project_offers.values())]
    return sorted(items)


def rivalry_pressure(state, day, content=None):
    """Gegenwind der Mitbewerber an einem Arbeitstag, aus den Angeboten der
    Tage davor: {"aktiv", "gewonnen", "angebote", "minus", "zweiter", "seit"}.
    Er beginnt ab gegenwind.ab_quote Prozent Siegen und haelt dann mindestens
    gegenwind.mindest_tage Arbeitstage. Die Staerke ist fest - wer noch oefter
    gewinnt, bekommt nicht mehr ab."""
    content = content or state.content
    rule = rivalry_rules(content).get("gegenwind")
    empty = {"aktiv": False, "gewonnen": 0, "angebote": 0, "minus": 0, "zweiter": 0.0,
             "faktor": 1.0, "seit": 0}
    if not rule or not state.firm:
        return empty
    stamp = len(state.offers) + len(state.project_offers)
    cache = state._pressure
    if cache.get("stand") != stamp:
        cache.clear()
        cache["stand"] = stamp
        cache["angebote"] = _decided_offers(state)
    if day in cache:
        return cache[day]
    offers = cache["angebote"]
    founded = int(state.firm["tag"])
    since = 0
    known = [key for key in cache if isinstance(key, int) and key < day]
    begin = max(known) + 1 if known else founded
    if known:
        since = cache[max(known)]["seit"]
    result = empty
    for current in range(begin, max(begin, day) + 1):
        window = [item for item in offers if item[0] < current][-int(rule["fenster"]):]
        won = sum(1 for item in window if item[2])
        hot = len(window) >= int(rule["mindestens"]) and \
            won * 100 >= float(rule["ab_quote"]) * len(window)
        if hot and not since:
            since = current
        elif not hot and since and current - since >= int(rule.get("mindest_tage", 0)):
            since = 0
        active = bool(since)
        result = {"aktiv": active, "gewonnen": won, "angebote": len(window),
                  "minus": int(rule["zuschlag_minus"]) if active else 0,
                  "zweiter": float(rule.get("zweiter_bieter", 0)) if active else 0.0,
                  "faktor": float(rule.get("vorteil_faktor", 1)) if active else 1.0,
                  "seit": since}
        cache[current] = result
    return cache.get(day, result)


def pressure_text(pressure):
    """ "Gegenwind: ..." fuer die Auftraege (leer ohne Gegenwind)."""
    if not pressure.get("aktiv"):
        return ""
    text = ("Gegenwind: Du hast %d deiner letzten %d Angebote gewonnen. Alle Mitbewerber "
            "bieten deshalb gezielt %d Punkte günstiger gegen dich." % (
                pressure["gewonnen"], pressure["angebote"], pressure["minus"]))
    if pressure.get("faktor", 1) < 1:
        text += " Dein Preisvorteil zählt solange nur halb." if pressure["faktor"] == 0.5 \
            else " Dein Preisvorteil zählt solange nur zu %d %%." % round(
                pressure["faktor"] * 100)
    return text


def _phase_list(seed, until, content):
    """Konjunkturphasen ab markt.ab_tag bis mindestens until:
    [(von, bis ausschliesslich, phasen-id)]."""
    rule = market_rules(content)
    setup = rule.get("konjunktur") or {}
    phases = setup.get("phasen") or {}
    if not phases or "neutral" not in phases:
        return []
    day = int(rule.get("ab_tag", 101))
    result = []
    kind = "neutral"
    number = 0
    ups = [key for key in ("aufschwung", "abschwung") if key in phases]
    swing = ""       # letzter Auf- oder Abschwung
    while day <= until:
        span = setup.get("start_tage") if number == 0 else phases[kind]["tage"]
        length = max(1, _between(seed, number, "konjunktur-dauer", *span))
        result.append((day, day + length, kind))
        day += length
        number += 1
        if kind != "neutral":
            swing = kind
            kind = "neutral"
        elif not ups:
            break
        elif swing and len(ups) == 2:
            # Meist folgt auf einen Abschwung ein Aufschwung und umgekehrt
            other = ups[1] if swing == ups[0] else ups[0]
            kind = other if _dice(seed, number, "konjunktur-art") * 100 < \
                float(setup.get("wechsel_chance", 50)) else swing
        else:
            kind = _pick(ups, seed, number, "konjunktur-art")
    return result


def _trend_list(seed, until, content):
    """Technologietrends: [(von, bis ausschliesslich, trend)]."""
    rule = market_rules(content)
    setup = rule.get("trends") or {}
    trends = setup.get("liste") or []
    if not trends:
        return []
    day = int(rule.get("ab_tag", 101)) + _between(seed, 0, "trend-erster",
                                                  *setup["erster_nach"])
    result = []
    last = None
    number = 0
    while day <= until:
        options = [item for item in trends if item["id"] != last] or trends
        trend = _pick(options, seed, number, "trend-art")
        length = max(1, _between(seed, number, "trend-dauer", *setup["dauer"]))
        result.append((day, day + length, trend))
        last = trend["id"]
        day += length + _between(seed, number, "trend-pause", *setup["pause"])
        number += 1
    return result


_NO_PHASE = {"name": "", "anfragen": 0, "zuschlag": 0, "umsatz": 0}


def market_state(state, day, content=None):
    """Konjunktur und Trend an einem Arbeitstag: {"phase" (id oder ""),
    "phase_info", "phase_von", "phase_bis", "trend" (oder None), "trend_von",
    "trend_bis"}. Vor markt.ab_tag und ohne Firma bewegt sich nichts."""
    content = content or state.content
    result = {"phase": "", "phase_info": _NO_PHASE, "phase_von": 0, "phase_bis": 0,
              "trend": None, "trend_von": 0, "trend_bis": 0}
    rule = market_rules(content)
    if not state.firm or not rule or day < int(rule.get("ab_tag", 101)):
        return result
    seed = state.firm_seed
    for start, end, kind in _phase_list(seed, day, content):
        if start <= day < end:
            result.update(phase=kind, phase_info=rule["konjunktur"]["phasen"][kind],
                          phase_von=start, phase_bis=end)
    for start, end, trend in _trend_list(seed, day, content):
        if start <= day < end:
            result.update(trend=trend, trend_von=start, trend_bis=end)
    return result


def market_status(state, content=None):
    """Kleine Anzeige im Firmenbereich (Auftraege): [(ueberschrift, text)]."""
    content = content or state.content
    now = market_state(state, state.day, content)
    lines = []
    if now["phase"]:
        info = now["phase_info"]
        effects = []
        if info.get("anfragen"):
            effects.append("%s Anfrage%s pro Tag" % (_signed(info["anfragen"]),
                                                     "" if abs(info["anfragen"]) == 1 else "n"))
        if info.get("zuschlag"):
            effects.append("Marktpreise %s Punkte" % _signed(info["zuschlag"]))
        if info.get("umsatz"):
            effects.append("Routineumsatz %s" % _signed(info["umsatz"], " %"))
        lines.append(("Konjunktur: %s" % info["name"],
                      " · ".join(effects) if effects else "Anfragen und Preise normal"))
    if now["trend"]:
        trend = now["trend"]
        lines.append(("Trend: %s" % trend["name"],
                      "Noch %s · dazu Trend-Anfragen (%s)" % (
                          _days_text(now["trend_bis"] - state.day),
                          CAT_NAME.get(trend.get("cat"), trend.get("cat", "")))))
    pressure = pressure_text(rivalry_pressure(state, state.day, content))
    if pressure:
        lines.append(("Gegenwind der Mitbewerber", pressure.split(": ", 1)[1]))
    return lines


def market_events(state, content=None):
    """Was sich am Markt geaendert hat, Tag fuer Tag bis heute:
    [(tag, art, titel, text)] mit art konjunktur_wechsel, trend_gestartet,
    trend_beendet, wettbewerb_verschaerft, wettbewerb_entspannt."""
    content = content or state.content
    if not state.firm:
        return []
    rule = market_rules(content)
    founded = int(state.firm["tag"])
    result = []
    if rule:
        seed = state.firm_seed
        start = int(rule.get("ab_tag", 101))
        for day, _end, kind in _phase_list(seed, state.day, content):
            if day <= founded or day == start and kind == "neutral":
                continue
            info = rule["konjunktur"]["phasen"][kind]
            result.append((day, "konjunktur_wechsel", "Konjunktur: %s" % info["name"],
                           info.get("text", "")))
        for day, end, trend in _trend_list(seed, state.day, content):
            if end <= founded:
                continue
            # Lief der Trend schon bei der Gruendung, steht er am Gruendungstag
            result.append((max(day, founded), "trend_gestartet", "Trend: %s" % trend["name"],
                           trend.get("start", "")))
            if end <= state.day:
                result.append((end, "trend_beendet", "Trend vorbei: %s" % trend["name"],
                               trend.get("ende", "")))
    wind = rivalry_rules(content).get("gegenwind")
    if wind:
        before = False
        for day in range(founded + 1, state.day + 1):
            now = rivalry_pressure(state, day, content)["aktiv"]
            if now != before:
                result.append((day, "wettbewerb_verschaerft" if now else "wettbewerb_entspannt",
                               "Gegenwind der Mitbewerber" if now else "Gegenwind vorbei",
                               wind.get("text_start" if now else "text_ende", "")))
            before = now
    return sorted(result, key=lambda item: item[0])


def market_news(state, content=None):
    """Story-Moment am Morgen: was sich heute am Markt geaendert hat."""
    content = content or state.content
    lines = [text for day, _kind, _title, text in market_events(state, content)
             if day == state.day and text]
    rule = market_rules(content)
    if rule and state.day == int(rule.get("ab_tag", 101)) and \
            int(state.firm["tag"]) < state.day and rule.get("start_text"):
        lines.insert(0, rule["start_text"])
    return "\n".join(lines)


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
    shift = market_shift(state, start, content)
    move = shift["shift"]
    bids, absent = competitor_bids("projekt", "normal", cat, seed, start, salt, content,
                                   shift=move)
    cheapest = min(bids, key=lambda bid: bid["zuschlag"])
    project_id = "%s%d" % (PROJECT_PREFIX, slot + 1)
    customer = customer_short(template["branche"])
    text = _pick(rules["texte"], seed, start, salt + "text").format(
        kunde=customer, auftrag=template["auftrag"])
    return {"id": project_id, "slot": slot, "vorlage": index, "folge": slot // len(order),
            "titel": template["title"], "kunde": template["branche"],
            "kunde_kurz": customer, "cat": cat, "thema": template.get("thema"),
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
            "gegenwind": shift["gegenwind"],
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


def project_value(state, person, project, levels, content=None):
    """Wert einer Person im Thema des Projekts (ab 0.38; Spielfigur: echter
    Wissensstand). Ohne Thema zaehlt der Fachbereich."""
    topic = project_topic(project, content or state.content)
    if person == SELF:
        return topic_level(levels, topic, project["cat"])
    if topic:
        return state.staff_topic_value(person, topic)
    return int(state.staff_values(person).get(project["cat"], 0))


def person_name(state, person):
    if person == SELF:
        return "Ich selbst (%s)" % ((state.profile or {}).get("name") or "Ich")
    return (state.staff.get(person) or {}).get("name", person)


def project_candidates(state, project, levels, content=None):
    """Wer im Projektteam mitarbeiten kann: [{"an", "name", "wert", "punkte",
    "im_team", "problem"}] - zuerst die Spielfigur, dann die Mitarbeiter."""
    content = content or GAME
    result = []
    own_tickets = len(state.delegated_to(SELF))
    elsewhere = state.project_of(SELF)
    problem = ""
    if elsewhere and elsewhere != project["projekt"]:
        problem = "Du arbeitest schon im Projekt „%s“ mit." % state.projects[elsewhere]["titel"]
    elif SELF not in project["team"] and own_tickets >= ticket_limit(SELF, content):
        problem = "Du hast heute schon %d Kundentickets übernommen." % own_tickets
    value = project_value(state, SELF, project, levels, content)
    result.append({"an": SELF, "name": person_name(state, SELF), "wert": value,
                   "punkte": project_points(value, content),
                   "im_team": SELF in project["team"], "problem": problem})
    for item in state.staff_list():
        value = project_value(state, item["id"], project, levels, content)
        problem = ""
        if item.get("weiterbildung") or item.get("abwesend"):
            problem = absent_problem(item["name"], item.get("weiterbildung") or
                                     item["abwesend"])
        elif item.get("projekt") and item["projekt"] != project["projekt"]:
            problem = "%s arbeitet schon im Projekt „%s“ mit." % (
                item["name"], state.projects[item["projekt"]]["titel"])
        elif item["id"] not in project["team"] and state.delegated_to(item["id"]):
            problem = "%s hat heute schon ein Kundenticket." % item["name"]
        result.append({"an": item["id"], "name": item["name"], "wert": value,
                       "punkte": staff_project_points(state, item["id"], value, content),
                       "im_team": item["id"] in project["team"], "problem": problem})
    return result


def project_team_points(state, project, levels, content=None):
    """Punkte, die das Team an einem Arbeitstag schafft (ohne Zufall)."""
    total = 0.0
    for person in project["team"]:
        if person != SELF and (person not in state.staff or state.absence_of(person)):
            continue
        total += staff_project_points(state, person, project_value(
            state, person, project, levels, content), content)
    return round(total * team_factor(state, project["team"]), 1)


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
            if person != SELF and (person not in state.staff or state.absence_of(person)):
                continue
            value = project_value(state, person, project, levels, content)
            best = max(best, value)
            shares.append({"an": person, "name": person_name(state, person),
                           "punkte": staff_project_points(state, person, value, content)})
        if not shares:
            continue
        # Ab 0.43: wer das ganze Team mitzieht (Macke), wirkt einmal
        factor = team_factor(state, project["team"])
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
        subject_text(project["cat"], project_topic(project)), project["schwierigkeit"],
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
        elif item.get("thema") not in CAT_TOPICS[item["cat"]]:
            problems.append("%s: Thema fehlt oder passt nicht zum Fachbereich" % where)
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


def _validate_loans(content):
    """balancing.json "kredite" (ab 0.41)."""
    rules = (content.get("balancing") or {}).get("kredite")
    if not rules:
        return ["Spiel: balancing.kredite fehlt"]
    problems = []
    for key in ("bank", "tage_pro_jahr", "bonitaet", "rahmen", "frei", "zins", "pakete",
                "abloesen_prozent", "mahnung"):
        if key not in rules:
            problems.append("Spiel-Kredite: '%s' fehlt" % key)
    if problems:
        return problems
    terms = [key for key in rules["zins"]["basis"]]
    if not terms or not all(key.isdigit() and int(key) > 0 for key in terms):
        problems.append("Spiel-Kredite: Laufzeiten in zins.basis ungueltig")
        return problems
    rates = [float(rules["zins"]["basis"][str(term)]) for term in sorted(int(k) for k in terms)]
    if rates != sorted(rates):
        problems.append("Spiel-Kredite: laengere Laufzeit muss mindestens so teuer sein")
    ids = set()
    for package in rules["pakete"]:
        if package.get("id") in ids or package.get("id") == FREE_LOAN:
            problems.append("Spiel-Kredite: Paket-Kennung '%s' doppelt oder reserviert"
                            % package.get("id"))
        ids.add(package.get("id"))
        if str(package.get("laufzeit")) not in rules["zins"]["basis"]:
            problems.append("Spiel-Kredite: Paket %s mit unbekannter Laufzeit" % package["id"])
        if not isinstance(package.get("summe"), int) or package["summe"] <= 0:
            problems.append("Spiel-Kredite: Paket %s ohne gueltige Summe" % package["id"])
    steps = rules["mahnung"].get("stufen") or []
    if [step.get("stufe") for step in steps] != list(range(1, len(steps) + 1)) or not steps:
        problems.append("Spiel-Kredite: Mahnstufen muessen 1, 2, 3 ... heissen")
    for step in steps:
        for key in (step.get("reputation") or {}):
            if key not in AXIS_KEYS:
                problems.append("Spiel-Kredite: Mahnstufe %s mit unbekannter Achse '%s'"
                                % (step.get("stufe"), key))
    return problems


def _validate_business(content):
    """balancing.json "steuern", "marketing" und "zertifizierungen" (ab 0.42)."""
    balancing = content.get("balancing") or {}
    problems = []
    tax = balancing.get("steuern")
    if not tax:
        problems.append("Spiel: balancing.steuern fehlt")
    else:
        for key in ("finanzamt", "satz", "faellig_tage", "ruecklage_prozent"):
            if key not in tax:
                problems.append("Spiel-Steuern: '%s' fehlt" % key)
        if not 0 < float(tax.get("satz", 0)) < 100:
            problems.append("Spiel-Steuern: Steuersatz ungueltig")
        if int(tax.get("faellig_tage", 0)) < 1:
            problems.append("Spiel-Steuern: faellig_tage muss mindestens 1 sein")
    effects = ("anfragen", "tickets", "groesse", "vorteil")
    ids = set()
    for form in (balancing.get("marketing") or {}).get("formen") or []:
        where = "Spiel-Werbung %s" % form.get("id")
        if not form.get("id") or form["id"] in ids:
            problems.append("%s: Kennung fehlt oder doppelt" % where)
        ids.add(form.get("id"))
        if int(form.get("laufend", 0)) <= 0:
            problems.append("%s: laufende Kosten fehlen" % where)
        once = form.get("einmalig") or {}
        if int(once.get("preis", 0)) <= 0 or int(once.get("tage", 0)) <= 0:
            problems.append("%s: einmalig braucht preis und tage" % where)
        wirkung = form.get("wirkung") or {}
        if not wirkung or any(key not in effects for key in wirkung):
            problems.append("%s: unbekannte oder keine Wirkung" % where)
    if not ids:
        problems.append("Spiel: balancing.marketing ohne Werbeformen")
    certs = balancing.get("zertifizierungen") or {}
    cert_ids = set()
    for cert in certs.get("liste") or []:
        where = "Spiel-Zertifizierung %s" % cert.get("id")
        if not cert.get("id") or cert["id"] in cert_ids:
            problems.append("%s: Kennung fehlt oder doppelt" % where)
        cert_ids.add(cert.get("id"))
        if int(cert.get("preis", 0)) <= 0 or int(cert.get("tage", 0)) <= 0:
            problems.append("%s: preis und tage fehlen" % where)
        for key in cert.get("vorteil") or {}:
            if key != "alle" and key not in CAT_ORDER:
                problems.append("%s: unbekannter Fachbereich '%s'" % (where, key))
    if not cert_ids:
        problems.append("Spiel: balancing.zertifizierungen ohne Liste")
    gross = certs.get("grossauftraege") or {}
    for key in ("abstand_tage", "gilt_tage", "stufe", "liste"):
        if key not in gross:
            problems.append("Spiel-Grossauftraege: '%s' fehlt" % key)
    gross_ids = set()
    for item in gross.get("liste") or []:
        where = "Spiel-Grossauftrag %s" % item.get("id")
        if not item.get("id") or item["id"] in gross_ids:
            problems.append("%s: Kennung fehlt oder doppelt" % where)
        gross_ids.add(item.get("id"))
        if item.get("cat") not in CAT_ORDER:
            problems.append("%s: unbekannter Fachbereich" % where)
        elif item.get("thema") not in CAT_TOPICS[item["cat"]]:
            problems.append("%s: Thema passt nicht zum Fachbereich" % where)
        needs = item.get("braucht") or []
        if not needs or any(cert_id not in cert_ids for cert_id in needs):
            problems.append("%s: braucht unbekannte oder keine Zertifizierung" % where)
        for key in ("titel", "kunde", "kunde_kurz", "ausgangssituation", "auftrag"):
            if not item.get(key):
                problems.append("%s: '%s' fehlt" % (where, key))
    return problems


QUIRK_KEYS = ("umsatz", "chance", "chance_netzwerk", "chance_hardware", "chance_talbahn",
              "projekt", "team_projekt", "team_lernen", "kz_erfolg", "kz_fehlschlag", "lernen",
              "lernen_hardware", "lernen_andere", "urlaub", "krank", "konflikt",
              "weiterbildung_tage", "stimmung_team", "stimmung_fehlschlag")


def _validate_personal(rules, colleagues):
    """firma.json ab 0.43: Macken mit Staerke und Schwaeche, Abschnitt personal."""
    problems = []
    seen = set()
    for item in rules.get("macken") or []:
        if not isinstance(item, dict):
            problems.append("Spiel-Firma: Macke ohne Kennung (ab 0.43 Objekte)")
            continue
        where = "Spiel-Firma Macke %s" % item.get("id")
        for key in ("id", "name", "text"):
            if not item.get(key):
                problems.append("%s: '%s' fehlt" % (where, key))
        if item.get("id") in seen:
            problems.append("%s: Kennung doppelt" % where)
        seen.add(item.get("id"))
        if not item.get("plus") or not item.get("minus"):
            problems.append("%s: braucht Staerke (plus) und Schwaeche (minus)" % where)
        for side in ("plus", "minus"):
            for key, value in (item.get(side) or {}).items():
                if key not in QUIRK_KEYS or not isinstance(value, (int, float)):
                    problems.append("%s: unbekannte Wirkung '%s'" % (where, key))
        if item.get("kollege") and item["kollege"] not in colleagues:
            problems.append("%s: unbekannte Person '%s'" % (where, item["kollege"]))
    if len([item for item in rules.get("macken") or []
            if isinstance(item, dict) and not item.get("kollege")]) < 5:
        problems.append("Spiel-Firma: zu wenige Macken fuer Bewerber")
    personal = rules.get("personal") or {}
    for key in ("stimmung", "krankheit", "urlaub", "konflikt", "coaching", "macken"):
        if key not in personal:
            problems.append("Spiel-Firma: personal.%s fehlt" % key)
    if problems:
        return problems
    stages = personal["macken"].get("stufen") or {}
    if sorted(stages) != ["1", "2", "3"]:
        problems.append("Spiel-Firma: personal.macken.stufen braucht die Stufen 1 bis 3")
    if len(personal["konflikt"].get("texte") or []) < 3:
        problems.append("Spiel-Firma: zu wenige Konflikt-Texte")
    for text in (personal["konflikt"].get("texte") or []) + [personal["konflikt"].get("summen",
                                                                                      "")]:
        try:
            text.format(a="A", b="B", a_von="As", b_von="Bs")
        except (KeyError, IndexError, ValueError):
            problems.append("Spiel-Firma: Konflikt-Text mit falschem Platzhalter: %s" % text[:40])
    return problems


def _validate_market(rules):
    """firma.json ab 0.44: rivalitaet (Rueckhol-Angebote, Gegenwind) und
    markt (Konjunktur, Trends)."""
    problems = []
    rivalry = rules.get("rivalitaet") or {}
    recall = rivalry.get("rueckhol") or {}
    for key in ("vorher_anteil", "ab_tagen", "chance", "abstand", "abstand_firma",
                "gehalt_plus", "bonus_tage"):
        if not isinstance(recall.get(key), (int, float)) or recall[key] < 0:
            problems.append("Spiel-Firma: rivalitaet.rueckhol.%s fehlt oder ist ungueltig" % key)
    span = recall.get("angebot_plus") or []
    if len(span) != 2 or span[0] > span[1]:
        problems.append("Spiel-Firma: rivalitaet.rueckhol.angebot_plus braucht [von, bis]")
    texts = list(recall.get("texte") or []) + list(recall.get("texte_bitweiche") or [])
    if len(recall.get("texte") or []) < 2:
        problems.append("Spiel-Firma: zu wenige Rueckhol-Texte")
    for text in texts:
        try:
            text.format(firma="F", name="N", plus=10)
        except (KeyError, IndexError, ValueError):
            problems.append("Spiel-Firma: Rueckhol-Text mit falschem Platzhalter: %s" % text[:40])
    wind = rivalry.get("gegenwind") or {}
    for key in ("fenster", "mindestens", "ab_quote", "zuschlag_minus"):
        if not isinstance(wind.get(key), (int, float)) or wind[key] < 0:
            problems.append("Spiel-Firma: rivalitaet.gegenwind.%s fehlt oder ist ungueltig" % key)
    if "vorteil_faktor" in wind and (not isinstance(wind["vorteil_faktor"], (int, float))
                                     or not 0 <= wind["vorteil_faktor"] <= 1):
        problems.append("Spiel-Firma: rivalitaet.gegenwind.vorteil_faktor muss zwischen 0 und 1 "
                        "liegen")
    if isinstance(wind.get("mindestens"), int) and isinstance(wind.get("fenster"), int) and \
            wind["mindestens"] > wind["fenster"]:
        problems.append("Spiel-Firma: gegenwind.mindestens liegt ueber dem Fenster")
    market = rules.get("markt") or {}
    phases = (market.get("konjunktur") or {}).get("phasen") or {}
    if set(phases) != {"neutral", "aufschwung", "abschwung"}:
        problems.append("Spiel-Firma: markt.konjunktur.phasen braucht neutral, aufschwung "
                        "und abschwung")
    for key, phase in phases.items():
        for field in ("name", "tage", "anfragen", "zuschlag", "umsatz"):
            if field not in phase:
                problems.append("Spiel-Firma: Konjunktur %s ohne '%s'" % (key, field))
    trends = market.get("trends") or {}
    for key in ("erster_nach", "dauer", "pause"):
        span = trends.get(key) or []
        if len(span) != 2 or span[0] > span[1] or span[0] < 1:
            problems.append("Spiel-Firma: markt.trends.%s braucht [von, bis]" % key)
    seen = set()
    for trend in trends.get("liste") or []:
        where = "Spiel-Firma Trend %s" % trend.get("id")
        for field in ("id", "name", "cat", "start", "ende", "artikel"):
            if not trend.get(field):
                problems.append("%s: '%s' fehlt" % (where, field))
        if trend.get("id") in seen:
            problems.append("%s: Kennung doppelt" % where)
        seen.add(trend.get("id"))
        if trend.get("cat") and trend["cat"] not in CAT_ORDER:
            problems.append("%s: unbekannter Fachbereich '%s'" % (where, trend["cat"]))
        for article in trend.get("artikel") or []:
            if len(article.get("preis") or []) != 2 or len(article.get("menge") or []) != 2 \
                    or not article.get("name"):
                problems.append("%s: Artikel unvollstaendig" % where)
    if len(trends.get("liste") or []) < 2:
        problems.append("Spiel-Firma: mindestens zwei Trends noetig")
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
        for topic in item.get("staerken") or []:
            if topic not in TOPIC_CAT:
                problems.append("Spiel-Firma: Wechsel %s mit unbekannter Staerke '%s'"
                                % (item.get("kollege"), topic))
    problems += _validate_personal(rules, ids)
    problems += _validate_market(rules)
    problems += _validate_branch(rules)
    learn = rules.get("lernen") or {}
    for key in ("ticket_erfolg", "projekt_fertig", "projekt_puenktlich", "routine_tage",
                "routine_plus", "halb_ab", "deckel", "max", "alt_streuung"):
        if not isinstance(learn.get(key), (int, float)) or learn[key] < 0:
            problems.append("Spiel-Firma: lernen.%s fehlt oder ist ungueltig" % key)
    if isinstance(learn.get("deckel"), (int, float)) and isinstance(learn.get("max"), (int, float)) \
            and learn["deckel"] > learn["max"]:
        problems.append("Spiel-Firma: lernen.deckel liegt ueber lernen.max")
    whole = (rules.get("weiterbildung") or {}).get("fachbereich") or {}
    for key in ("preis", "tage", "plus"):
        if not isinstance(whole.get(key), int) or whole[key] <= 0:
            problems.append("Spiel-Firma: weiterbildung.fachbereich.%s ungueltig" % key)
    return problems


def _validate_branch(rules):
    """firma.json "filiale" (ab 0.45): Voraussetzung, Stufen mit Grundriss und
    Arbeitsplaetzen, Naehe zu Kunden."""
    branch = rules.get("filiale")
    if not branch:
        return []
    problems = []
    need = branch.get("voraussetzung") or {}
    for key in ("stufe", "mitarbeiter", "firmentage"):
        if not isinstance(need.get(key), int) or need[key] < 0:
            problems.append("Spiel-Filiale: voraussetzung.%s fehlt oder ist ungueltig" % key)
    if need.get("stufe", 0) > len(rules["gebaeude"].get("stufen") or []):
        problems.append("Spiel-Filiale: voraussetzung.stufe gibt es nicht")
    if not branch.get("name_vorschlag"):
        problems.append("Spiel-Filiale: name_vorschlag fehlt")
    capacity = 0
    for number, stage in enumerate(branch.get("stufen") or [], 1):
        where = "Spiel-Filiale Stufe %d" % number
        if stage.get("stufe") != number:
            problems.append("%s: falsche Nummer" % where)
        if not isinstance(stage.get("preis"), int) or stage["preis"] <= 0:
            problems.append("%s: Preis fehlt" % where)
        places = stage.get("plaetze") or []
        if len(places) <= capacity:
            problems.append("%s: bringt keine zusaetzlichen Arbeitsplaetze" % where)
        capacity = len(places)
        people = [{"id": "filiale%d" % index, "raum": room_id, "platz": [x, y]}
                  for index, (x, y, room_id) in enumerate(places)]
        problems += _validate_building(stage["gebaeude"], where, people)
        free = _base_grid(stage["gebaeude"])
        for x, y, _room in places:
            if _cell(x, y) not in free:
                problems.append("%s: Arbeitsplatz %.1f/%.1f ist verstellt" % (where, x, y))
    if not branch.get("stufen"):
        problems.append("Spiel-Filiale: keine Stufen")
    near = branch.get("naehe") or {}
    towns = {item.get("ort") for item in rules.get("kunden", []) if item.get("ort")}
    for town in near.get("orte") or []:
        if town not in towns:
            problems.append("Spiel-Filiale: kein Kunde mit ort '%s'" % town)
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


def _staggered_labels(building):
    """Raeume der unteren Reihe, deren Schild unten steht: von links gezaehlt
    jeder zweite (der erste oben, der zweite unten, der dritte oben ...)."""
    hall = building["flur"]
    lower = sorted((item for item in building["raeume"]
                    if item["y"] >= hall["y"] + hall["h"] - 0.01),
                   key=lambda item: item["x"])
    return {item["id"] for index, item in enumerate(lower) if index % 2}


def _covered_by_label(building, below):
    """Prueft, ob ein Name unter einem nach unten versetzten Schild laege
    (dann wird er in der kleinen Ansicht weggelassen)."""
    rooms = [item for item in building["raeume"] if item["id"] in below]

    def covered(spot):
        x, y = spot[0], spot[1]
        return any(item["x"] <= x <= item["x"] + item["w"]
                   and item["y"] + item["h"] - 2.0 <= y <= item["y"] + item["h"]
                   for item in rooms)
    return covered


def building_shapes(counts=None, selected=None, player=None, content=None,
                    quests=None, player_pos=None, rotate=False, stagger=False):
    """Zeichenbefehle fuer das ganze Buerogebaeude.

    counts:     offene Tickets je Raum-ID (rosa Plakette)
    selected:   ausgewaehlte Raum-ID (farbiger Rahmen)
    player:     (Name, Aussehen) des Protagonisten oder None (dann zeichnet
                die Oberflaeche die Figur selbst, z.B. waehrend sie laeuft)
    quests:     IDs der Kollegen mit offenem Auftrag (gruenes "!" ueber dem Kopf)
    player_pos: Standort der Spielfigur, sonst ihr Platz im Flur
    rotate:     Gebaeude hochkant zeichnen (Handy-Grossansicht)
    stagger:    Schilder der unteren Raumreihe abwechselnd oben und unten
                (kleine Ansicht, damit sich schmale Raeume nicht verdecken)
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
    below = _staggered_labels(building) if stagger and not rotate else set()
    for item in building["raeume"]:
        x, y, w, h = _view_rect(item, rotate, content)
        color = room_color(item)
        if item["id"] == selected:
            s.append(_rect(x + 0.14, y + 0.14, w - 0.28, h - 0.28, "", color, 0.12, 0.2))
        label_y = y + h - 0.78 if item["id"] in below else y + 0.78
        label = _text(x + 0.55, label_y, item["name"], "raum", C["text"],
                      maxw=w - 2.2, kurz=item.get("kurz"))
        label["bg"] = mix(C["card"], color, 0.1)
        label["border"] = mix(color, C["card"], 0.3)
        s.append(label)
        count = counts.get(item["id"], 0)
        if count:
            s.append(_oval(x + w - 1.05, y + 0.38, 0.8, 0.8, C["pink"], C["card"], 0.06))
            s.append(_text(x + w - 0.65, y + 0.78, str(count), "badge", C["on_accent"],
                           anchor="c"))
    covered = _covered_by_label(building, below)
    for person in content["kollegen"]:
        if not person.get("platz"):
            continue
        px_, py_ = to_view(person["platz"][0], person["platz"][1], rotate, content)

        if not covered(person["platz"]):
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
                    ("Im Coaching, heute kein Umsatz." if person.get("im_coaching") else
                     "In der Weiterbildung, heute kein Umsatz.") if person.get("in_weiterbildung")
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
#  REISE DES SPIELERS (AB 0.39)
# ============================================================================
#
# Tagebuch und Rueckblick werden - wie der Spielstand - nur aus dem
# Ereignisprotokoll berechnet. Es gibt dafuer keine eigenen Ereignisse.

JOURNEY_STORY = "story"
JOURNEY_CAREER = "karriere"
JOURNEY_FIRM = "firma"
JOURNEY_GROUPS = [("alle", "Alles"), (JOURNEY_STORY, "Story"),
                  (JOURNEY_CAREER, "Karriere"), (JOURNEY_FIRM, "Firma")]
# Erledigte Tickets, die im Tagebuch einen Eintrag bekommen
TICKET_MILESTONES = (1, 10, 25, 50, 100, 150, 200, 300, 400, 500, 750, 1000)
JOURNEY_TEXT_MAX = 220


def _short(text, limit=JOURNEY_TEXT_MAX):
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    return text[:limit - 1].rsplit(" ", 1)[0] + " …"


def _story_text(value):
    """Erster Absatz eines Story-Textes (Liste von Zeilen oder Text)."""
    if isinstance(value, list):
        value = value[0] if value else ""
        if isinstance(value, list):
            value = value[0] if value else ""
    return str(value or "").split("\n")[0]


def journey(state, content=None):
    """Das Ereignistagebuch: wichtige Momente chronologisch (aelteste zuerst).
    Jeder Eintrag: {"tag", "gruppe", "art", "titel", "text"}."""
    content = content or state.content
    entries = []

    def add(day, group, kind, title, text=""):
        entries.append({"tag": int(day), "gruppe": group, "art": kind, "titel": title,
                        "text": _short(text), "_nr": len(entries)})

    names = [rank["name"] for rank in content["balancing"]["raenge"]]
    day = 1
    solved = 0
    incidents = 0
    started = False
    hired = {}
    answered = set()
    offers_won = 0
    for _timestamp, kind, data in state.history:
        tag = data.get("tag") if isinstance(data.get("tag"), int) and data.get("tag") else day
        if kind == EV_PROFILE and not started:
            started = True
            add(tag, JOURNEY_CAREER, "start", "Erster Arbeitstag",
                "%s fängt bei der %s an." % (data.get("name") or "Deine Figur",
                                              content["gebaeude"]["firma"]))
        elif kind == EV_SOLVED and data.get("zwischenfall"):
            # Jeder Zwischenfall steht im Tagebuch, gemeistert oder nicht
            task = task_by_id(data.get("aufgabe"), content) or {}
            if data.get("richtig"):
                incidents += 1
                title = ("Erster Zwischenfall gemeistert" if incidents == 1 else
                         "Zwischenfall gemeistert")
            else:
                title = "Zwischenfall nicht gemeistert"
            add(tag, JOURNEY_CAREER, "zwischenfall", title, task.get("titel", ""))
        elif kind == EV_SOLVED and data.get("richtig"):
            solved += 1
            if solved in TICKET_MILESTONES:
                add(tag, JOURNEY_CAREER, "meilenstein",
                    "Erstes Ticket gelöst" if solved == 1 else
                    "%d Tickets gelöst" % solved,
                    (task_by_id(data.get("aufgabe"), content) or {}).get("titel", "")
                    if solved == 1 else "")
        elif kind == EV_MOVE:
            home = apartment(data.get("wohnung"), content) or {}
            add(tag, JOURNEY_CAREER, "umzug", "Umzug: %s" % home.get("name", "neue Wohnung"),
                "Gemietet für %s pro Arbeitstag." % _whole_euro(data["miete"])
                if data.get("miete") else "Gekauft.")
        elif kind == EV_FOUNDED and data.get("name"):
            if not any(entry["art"] == "gruendung" for entry in entries):
                add(tag, JOURNEY_FIRM, "gruendung", "Firma gegründet: %s" % data["name"],
                    "Abschied von der %s - ab jetzt bist du dein eigener Chef."
                    % content["gebaeude"]["firma"])
        elif kind == EV_HIRED and data.get("id") and data["id"] not in hired:
            hired[data["id"]] = data.get("name", "")
            add(tag, JOURNEY_FIRM, "einstellung", "Eingestellt: %s" % data.get("name", ""),
                data.get("rolle", ""))
        elif kind == EV_FIRED and data.get("id") in hired:
            add(tag, JOURNEY_FIRM, "kuendigung", "Gekündigt: %s" % hired[data["id"]])
        elif kind == EV_TRAINING and data.get("art") == TRAINING_COACHING and \
                data.get("id") in hired:
            quirk = quirk_by_id(data.get("macke"), content) or {}
            add(tag, JOURNEY_FIRM, "coaching", "Coaching: %s" % hired[data["id"]],
                "Gegen die Macke „%s“." % quirk.get("name", ""))
        elif kind in (EV_VACATION_OK, EV_VACATION_NO) and data.get("anfrage") and \
                data["anfrage"] not in answered:
            answered.add(data["anfrage"])
            ok = kind == EV_VACATION_OK
            add(tag, JOURNEY_FIRM, kind, "Urlaub %s: %s" % (
                "genehmigt" if ok else "abgelehnt", data.get("name", "")),
                "Arbeitstag %s bis %s." % (data.get("von"), int(data.get("bis", 1)) - 1))
        elif kind == EV_RECALL and data.get("rueckhol") and \
                data["rueckhol"] not in answered:
            answered.add(data["rueckhol"])
            company = competitor(data.get("firma") or BITWEICHE, content)["kurz"]
            add(tag, JOURNEY_FIRM, EV_RECALL,
                ("Zurück zu %s: %s" % (company, data.get("name", "")))
                if data.get("wahl") == RECALL_LET else
                "Abwerbeversuch abgewehrt: %s" % data.get("name", ""),
                recall_choice_text(data, content))
        elif kind == EV_CONFLICT and data.get("konflikt") and \
                data["konflikt"] not in answered:
            answered.add(data["konflikt"])
            names = _pair_names(data.get("name_a", ""), data.get("name_b", ""))
            add(tag, JOURNEY_FIRM, EV_CONFLICT, "Streit: %s und %s" % (names["a"], names["b"]),
                conflict_choice_text(data))
        elif kind == EV_EXPAND:
            stages = (content.get("firma") or {}).get("gebaeude", {}).get("stufen") or []
            stage = next((item for item in stages
                          if int(item.get("stufe", 0)) == int(data.get("stufe", 0))), {})
            add(tag, JOURNEY_FIRM, "ausbau", "Gebäude ausgebaut: %s"
                % stage.get("name", "Stufe %s" % data.get("stufe")),
                "Ausbaustufe %s" % data.get("stufe"))
        elif kind == EV_ROOM:
            item = special_room(data.get("raum"), content) or {}
            add(tag, JOURNEY_FIRM, "raum", "Neuer Raum: %s" % item.get("name", data.get("raum")))
        elif kind == EV_BRANCH:
            stage = branch_stage(data.get("stufe"), content) or {}
            if int(data.get("stufe", 0)) == 1 and data.get("name"):
                if not any(entry["art"] == "filiale" for entry in entries):
                    add(tag, JOURNEY_FIRM, "filiale", "Filiale eröffnet: %s" % data["name"],
                        "Zweiter Standort: %s." % branch_rules(content).get("name", "Lindenau"))
            else:
                add(tag, JOURNEY_FIRM, "ausbau", "Filiale ausgebaut: %s"
                    % stage.get("name", "Stufe %s" % data.get("stufe")),
                    "Ausbaustufe %s" % data.get("stufe"))
        elif kind == EV_ACHIEVEMENT and not data.get("nachgetragen"):
            # Ab 0.46: grosse Abzeichen (mit Meilenstein-Moment) stehen im Tagebuch
            rule = achievement_rule(data.get("erfolg"), content)
            level = int(data.get("stufe", 0) or 0)
            if rule and 0 < level <= len(rule["stufen"]) and \
                    rule["stufen"][level - 1].get("moment") and \
                    (data.get("erfolg"), level) not in answered:
                answered.add((data.get("erfolg"), level))
                tier = rule["stufen"][level - 1]["stufe"]
                add(tag, JOURNEY_CAREER if rule["gruppe"] in ("karriere", "wissen") else
                    JOURNEY_FIRM, "erfolg", "Abzeichen: %s · %s" % (rule["name"],
                                                                     TIER_NAMES[tier]),
                    rule["text"])
        elif kind == EV_TRANSFER and data.get("id") in hired:
            add(tag, JOURNEY_FIRM, "versetzung", "Versetzt: %s" % hired[data["id"]],
                "Arbeitet jetzt %s." % ("in der Filiale" if data.get("standort") == SITE_BRANCH
                                        else "im Gewerbehof am Stellwerk"))
        elif kind in (EV_OFFER_WON, EV_OFFER_LOST):
            # Jedes Angebot steht im Tagebuch, gewonnen oder verloren
            customer = (firm_customer(data.get("kunde"), content) or {}).get("name", "einen Kunden")
            what = "%s × %s" % (data.get("menge", 1), data.get("artikel", "Artikel"))
            if kind == EV_OFFER_WON:
                offers_won += 1
                add(tag, JOURNEY_FIRM, "angebot",
                    "Erstes Angebot gewonnen" if offers_won == 1 else "Angebot gewonnen",
                    "%s für %s, Gewinn %s." % (what, customer, _whole_euro(data.get("geld", 0))))
            else:
                reason = ("Fehler in der Kalkulation" if data.get("grund") == "rechenfehler"
                          else "%s war günstiger" % competitor(
                              data.get("konkurrent") or BITWEICHE, content)["kurz"])
                add(tag, JOURNEY_FIRM, "angebot_verloren", "Angebot verloren",
                    "%s für %s: %s." % (what, customer, reason))
        elif kind == EV_PROJECT_WON:
            add(tag, JOURNEY_FIRM, "projekt", "Projekt gewonnen: %s" % data.get("titel", ""),
                data.get("kunde", ""))
        elif kind == EV_PROJECT_LOST:
            add(tag, JOURNEY_FIRM, "projekt_verloren",
                "Projekt verloren: %s" % data.get("titel", ""), data.get("kunde", ""))
        elif kind == EV_DAY_END:
            day += 1
            # Ab 0.43: Personal (Krankheit, Kuendigung, schwaecher werdende Macken)
            for item in (data.get("firma") or {}).get("personal") or []:
                art = item.get("art")
                if art == PERSONAL_SICK:
                    add(tag, JOURNEY_FIRM, art, "Krank: %s" % item.get("name", ""),
                        "Fällt %s aus." % _days_text(int(item["bis"]) - int(item["von"])))
                elif art == PERSONAL_QUIT:
                    add(tag, JOURNEY_FIRM, art, "Selbst gekündigt: %s" % item.get("name", ""),
                        "Die Stimmung war zu lange im Keller.")
                elif art == PERSONAL_WEAKER:
                    add(tag, JOURNEY_FIRM, art, "Macke schwächer: %s" % item.get("name", ""),
                        "„%s“ jetzt %s." % (item.get("macke", ""), item.get("stufe_name", "")))
            for item in (data.get("firma") or {}).get("projekte") or []:
                if item.get("fertig"):
                    project = state.projects.get(item.get("projekt")) or {}
                    if project.get("fertig") == int(item.get("tag", tag) or tag):
                        add(tag, JOURNEY_FIRM, "projekt_fertig",
                            "Projekt abgeschlossen: %s" % project.get("titel", ""),
                            project.get("kunde", ""))

    # Kredite (ab 0.41): aufgenommen, zurueckgezahlt, geplatzte Raten
    for loan_day, loan_kind, loan_id, data in state.loan_log:
        loan = state.loans.get(loan_id) or {}
        if loan_kind == "aufgenommen":
            add(loan_day, JOURNEY_FIRM, "kredit", "Kredit aufgenommen: %s" % loan.get("name", ""),
                "%s über %s, %s p. a." % (_whole_euro(loan.get("summe", 0)),
                                          term_text(loan.get("laufzeit", 0)),
                                          percent_text(loan.get("zins", 0))))
        elif loan_kind in ("zurueckgezahlt", "abgeloest"):
            add(loan_day, JOURNEY_FIRM, "kredit_ende",
                ("Kredit abgelöst: %s" if loan_kind == "abgeloest" else
                 "Kredit zurückgezahlt: %s") % loan.get("name", ""),
                "Zinsen insgesamt %s." % _whole_euro(loan.get("bezahlt_zins", 0)))
        elif loan_kind == "ausfall":
            step = dunning_step(data.get("stufe", 1), content) or {}
            add(loan_day, JOURNEY_FIRM, "kredit_ausfall", "Kreditrate geplatzt",
                "%s: Mahnstufe %d (%s)." % (loan.get("name", ""), data.get("stufe", 1),
                                            step.get("name", "")))
    # Ab 0.42: Werbung, Zertifizierungen und Umsatzsteuer
    for data in state.ads:
        form = ad_form(data.get("werbung"), content) or {}
        add(data.get("tag", 1), JOURNEY_FIRM, "werbung",
            "Werbung gebucht: %s" % form.get("kurz", data.get("werbung")),
            "Einmalig für %s." % _whole_euro(-int(data.get("geld", 0)))
            if data.get("art") == AD_ONCE else
            "Dauerhaft für %s pro Arbeitstag." % _whole_euro(data.get("kosten", 0)))
    for cert_id, data in state.certs.items():
        if int(data.get("bis_tag", 0)) <= state.day:
            cert = certificate(cert_id, content) or {}
            add(int(data["bis_tag"]) - 1, JOURNEY_FIRM, "zertifizierung",
                "Zertifiziert: %s" % cert.get("name", cert_id),
                advantage_text(cert.get("vorteil") or {}))
    filed = 0
    for tax_day, tax_kind, data in state.tax_log:
        if tax_kind == "voranmeldung":
            filed += 1
            if filed == 1:
                add(tax_day, JOURNEY_FIRM, "steuer", "Erste Umsatzsteuer-Voranmeldung",
                    tax_filing_text(data) + ".")
        elif tax_kind == "ausfall":
            step = dunning_step(data.get("stufe", 1), content) or {}
            add(tax_day, JOURNEY_FIRM, "steuer_ausfall", "Umsatzsteuer nicht bezahlt",
                "Mahnstufe %d (%s)." % (data.get("stufe", 1), step.get("name", "")))
    # Ab 0.44: Konjunktur und Trends (Story), Gegenwind der Mitbewerber (Firma)
    for market_day, market_kind, title, text in market_events(state, content):
        add(market_day, JOURNEY_FIRM if market_kind.startswith("wettbewerb") else
            JOURNEY_STORY, market_kind, title, text)
    previous = 0
    for rank_day, rank in state.rank_log:
        level = names.index(rank) if rank in names else 0
        add(rank_day, JOURNEY_CAREER, "rang", ("Befördert: %s" if level > previous else
                                              "Zurückgestuft: %s") % rank)
        previous = level
    for key, value in (content["story"].get("tage") or {}).items():
        if key.isdigit() and int(key) <= state.day and started:
            add(int(key), JOURNEY_STORY, "story", "Arbeitstag %s" % key, _story_text(value))
    # Story-Momente stehen am Morgen, also vor allem anderen des Tages
    entries.sort(key=lambda entry: (entry["tag"], 0 if entry["art"] == "story" else 1,
                                    entry["_nr"]))
    for entry in entries:
        entry.pop("_nr", None)
    return entries


def journey_filter(entries, group):
    if group in (None, "alle"):
        return list(entries)
    return [entry for entry in entries if entry["gruppe"] == group]


def journey_stats(state, content=None):
    """Rueckblick-Statistik: Kennzahlen und Verlaeufe aus dem Protokoll."""
    content = content or state.content
    tickets = right = incidents = incidents_right = deferred = 0
    by_cat = {key: 0 for key in CAT_ORDER}
    per_day = {}
    for _timestamp, kind, data in state.history:
        if kind == EV_DEFERRED:
            deferred += 1
        if kind != EV_SOLVED:
            continue
        tag = data.get("tag") if isinstance(data.get("tag"), int) else 0
        if data.get("zwischenfall"):
            incidents += 1
            incidents_right += 1 if data.get("richtig") else 0
            continue
        tickets += 1
        bucket = per_day.setdefault(tag, [0, 0])
        if data.get("richtig"):
            right += 1
            bucket[0] += 1
            task = task_by_id(data.get("aufgabe"), content) or {}
            if task.get("cat") in by_cat:
                by_cat[task["cat"]] += 1
        else:
            bucket[1] += 1
    customer = [item for item in state.ticket_results.values() if item.get("erfolg")]
    offers = list(state.offers.values()) + list(state.project_offers.values())
    earned = sum(sum(day["ein"].values()) for day in state.book.values())
    days = sorted(day for day in per_day if day)[-30:]
    return {
        "diensttage": state.days_done,
        "tickets": tickets,
        "richtig": right,
        "quote": round(100.0 * right / tickets) if tickets else 0,
        "zwischenfaelle": incidents_right,
        "zwischenfaelle_gesamt": incidents,
        "verschoben": deferred,
        "kundenprojekte": len(state.done_projects()),
        "projekte_laufend": len(state.running_projects()),
        "kundentickets": len(customer),
        "angebote_gewonnen": sum(1 for item in offers if item.get("gewonnen")),
        "angebote": len(offers),
        "mitarbeiter": len(state.ever_hired),
        "verdient": earned,
        "je_fachbereich": by_cat,
        "tage": ["T%d" % day for day in days],
        "tage_richtig": [per_day[day][0] for day in days],
        "tage_falsch": [per_day[day][1] for day in days],
        "ansehen_tage": ["T%d" % day for day, _value in state.day_log[-30:]],
        "ansehen": [value for _day, value in state.day_log[-30:]],
    }


# ============================================================================
#  ERFOLGE UND BESTENLISTE (AB 0.46)
# ============================================================================
#
# Abzeichen und Bestwerte werden - wie alles andere - aus dem Spielstand
# berechnet (run_metrics). Das Ereignis erfolg_freigeschaltet haelt nur fest,
# wann eine Stufe erreicht wurde. Die Bestenliste (Tabelle spiel_bestenliste)
# gilt ueber alle Spielstaende ("Durchgaenge") und uebersteht das
# Zuruecksetzen: Game schreibt dort nur hinein, wenn ein Wert im laufenden
# Durchgang besser wird oder eine Stufe dazukommt.

TIER_NAMES = {"bronze": "Bronze", "silber": "Silber", "gold": "Gold"}
TIER_COLORS = {"bronze": "#D08A4E", "silber": "#D5DCE8", "gold": "#FACC15"}
TIER_ORDER = ("bronze", "silber", "gold")
# Kennzahlen, die Geld sind (fuer die Anzeige)
EURO_METRICS = ("kontostand", "tagesumsatz", "groesster_auftrag")
# Einnahmen der Firma an einem Arbeitstag (Bestwert und "Umsatzstark")
FIRM_INCOME = (BOOK_REVENUE, BOOK_OFFERS, BOOK_TICKETS, BOOK_PROJECTS)
# Summen ueber alle Durchgaenge (nicht als Bestwert angezeigt)
RECORD_SUMS = ("diensttage",)
REC_RUN = "durchgang"
REC_BEST = "bestwert"
REC_BADGE = "erfolg"
# Die Anzeige rechnet den laufenden Durchgang immer live aus dem Spielstand.
# In die Bestenliste kommt ein besserer Wert darum nur alle RECORD_EVERY
# Arbeitstage (und vor dem Zuruecksetzen alles), damit sie klein bleibt.
RECORD_EVERY = 20
# Texte fuer die Optionen (PC und Handy gleich)
RECORDS_HELP = ("Die Bestenliste unter Spiel > Reise > Erfolge sammelt Bestwerte und "
                "Abzeichen über alle Spielstände. Sie bleibt beim Zurücksetzen des "
                "Spielstands und beim Löschen der Lerndaten erhalten.")
RECORDS_ASK = ("Wirklich die Bestenliste löschen? Bestwerte und Abzeichen früherer "
               "Spielstände sind danach weg. Der laufende Spielstand trägt sich gleich "
               "wieder ein.")
KNOWLEDGE_GOAL = 70           # ab diesem Wissensstand gilt ein Thema als gekonnt
MOOD_GOOD = 70                # "Guter Arbeitgeber": mittlere Stimmung ab diesem Wert
# Kennzahlen, die Stufen zaehlen (Rang, Gebaeude): Fortschritt als Name der Stufe
LEVEL_METRICS = ("rang", "gebaeude")
FLAWLESS_MIN = 3              # "Fehlerfrei": so viele richtige Tickets am Tag mindestens

# Alle Kennzahlen, die erfolge.json unter "wert" nennen darf
RUN_METRICS = (
    "profil", "tickets", "zwischenfaelle", "fehlerfrei_serie", "rang", "ansehen",
    "wohnung_gekauft", "diensttage", "gegruendet", "mitarbeiter", "gebaeude", "filiale",
    "zertifikate", "grossauftraege", "projekte", "angebote_serie", "mitbewerber_besiegt",
    "kontostand", "tagesumsatz", "kredit_getilgt", "mahnung_vorbei", "mahnung_hoch_vorbei",
    "steuer_serie", "stimmung_serie", "stimmung_max", "weiterbildungen", "experte",
    "geschlichtet", "abwerbung_abgewehrt", "macke_gezaehmt", "themen_70", "fachbereiche_70",
    "auftraege", "groesster_auftrag", "tage_gruendung", "tage_stufe5", "tage_filiale",
)


def achievement_rules(content=None):
    return (content or GAME).get("erfolge") or {}


def achievement_rule(achievement_id, content=None):
    for rule in achievement_rules(content).get("erfolge") or []:
        if rule["id"] == achievement_id:
            return rule
    return None


def record_rule(key, content=None):
    for rule in achievement_rules(content).get("bestwerte") or []:
        if rule["id"] == key:
            return rule
    return None


def _longest(flags):
    """Laengste Serie von True in einer Folge."""
    best = run = 0
    for flag in flags:
        run = run + 1 if flag else 0
        best = max(best, run)
    return best


def run_metrics(state, knowledge=None, content=None):
    """Alle Kennzahlen des laufenden Durchgangs (siehe RUN_METRICS). None =
    (noch) nicht zu berechnen, z.B. ohne Firma oder ohne Wissensstand.
    Unter "_texte" stehen Erklaerungen zu einzelnen Werten (groesster Auftrag)."""
    content = content or state.content
    m = {key: 0 for key in RUN_METRICS}
    m["_texte"] = {}
    m["profil"] = 1 if state.profile else 0
    per_day = {}
    seen = set()
    offer_flags = []
    for _timestamp, kind, data in state.history:
        if kind == EV_SOLVED:
            day = data.get("tag") if isinstance(data.get("tag"), int) else 0
            bucket = per_day.setdefault(day, [0, 0])
            bucket[0 if data.get("richtig") else 1] += 1
            if data.get("zwischenfall"):
                m["zwischenfaelle"] += 1 if data.get("richtig") else 0
            elif data.get("richtig"):
                m["tickets"] += 1
        elif kind == EV_MOVE and data.get("wohnung") and not data.get("miete"):
            m["wohnung_gekauft"] = 1
        elif kind in (EV_OFFER_WON, EV_OFFER_LOST, EV_PROJECT_WON, EV_PROJECT_LOST):
            key = data.get("anfrage") or data.get("projekt")
            if key and key not in seen and state.firm:
                seen.add(key)
                offer_flags.append(kind in (EV_OFFER_WON, EV_PROJECT_WON))
    # Fehlerfrei: jeder abgeschlossene Arbeitstag mit genug richtigen und keinem falschen
    m["fehlerfrei_serie"] = _longest(
        per_day.get(day, [0, 0])[0] >= FLAWLESS_MIN and not per_day.get(day, [0, 0])[1]
        for day in range(1, state.days_done + 1))
    names = [rank["name"] for rank in content["balancing"]["raenge"]]
    m["rang"] = max([names.index(rank) for _day, rank in state.rank_log if rank in names] + [0])
    m["ansehen"] = int(round(max([value for _day, value in state.day_log] +
                                 [state.mean_reputation])))
    m["diensttage"] = state.days_done
    m["kontostand"] = max([money for _day, money in state.balances] + [0])
    # Firma
    firm = state.firm
    m["gegruendet"] = 1 if firm else 0
    m["mitarbeiter"] = state.staff_peak
    stage = firm["stufe"] if firm else 0
    rooms = (firm_rules(content).get("sonderraeume") or {}).get("raeume") or []
    m["gebaeude"] = (0 if stage < 3 else 1 if stage < 5 else
                     3 if all(item["id"] in state.rooms for item in rooms) else 2)
    m["filiale"] = state.branch["stufe"] if state.branch else 0
    m["zertifikate"] = sum(1 for data in state.certs.values()
                           if int(data.get("bis_tag", 0)) <= state.day)
    won = [item for item in list(state.offers.values()) + list(state.project_offers.values())
           if item.get("gewonnen")]
    m["grossauftraege"] = sum(1 for item in state.project_offers.values()
                              if item.get("gewonnen") and
                              str(item.get("vorlage", "")).startswith(GROSS_PREFIX))
    m["projekte"] = len(state.done_projects())
    m["angebote_serie"] = _longest(offer_flags)
    m["mitbewerber_besiegt"] = len({item.get("konkurrent") or BITWEICHE for item in won})
    biggest = max(won, key=lambda item: float(item.get("netto", 0) or 0), default=None)
    m["groesster_auftrag"] = int(round(float(biggest.get("netto", 0) or 0))) if biggest else None
    if biggest:
        m["_texte"]["groesster_auftrag"] = biggest.get("titel") or "%s × %s" % (
            biggest.get("menge", 1), biggest.get("artikel", "Artikel"))
    days = [day for day in state.book if firm and day >= firm["tag"]]
    m["tagesumsatz"] = max([sum(state.book[day]["ein"].get(kind, 0) for kind in FIRM_INCOME)
                            for day in days] + [0])
    customer = sum(1 for item in state.ticket_results.values() if item.get("erfolg"))
    m["auftraege"] = m["tickets"] + customer + m["projekte"]
    m["tage_gruendung"] = int(firm["tag"]) if firm else None
    m["tage_stufe5"] = (int(state.expand_days[5]) - int(firm["tag"])
                        if firm and 5 in state.expand_days else None)
    m["tage_filiale"] = (int(state.branch["tag"]) - int(firm["tag"])
                         if firm and state.branch else None)
    # Geld
    m["kredit_getilgt"] = sum(1 for _day, kind, _id, _data in state.loan_log
                              if kind in ("zurueckgezahlt", "abgeloest"))
    m["mahnung_vorbei"] = len(state.dunning_over)
    m["mahnung_hoch_vorbei"] = sum(1 for peak in state.dunning_over if peak >= 2)
    tax_flags = []
    for _day, kind, data in state.tax_log:
        if kind == "voranmeldung":
            tax_flags.append(not data.get("offen"))
        elif kind == "ausfall":
            tax_flags.append(False)
    m["steuer_serie"] = _longest(tax_flags)
    # Personal
    streak = best = 0
    previous = None
    for day, value in state.mood_log:
        if value >= MOOD_GOOD and previous is not None and day == previous + 1:
            streak += 1
        else:
            streak = 1 if value >= MOOD_GOOD else 0
        previous = day
        best = max(best, streak)
    m["stimmung_serie"] = best
    m["stimmung_max"] = int(round(max(value for _day, value in state.mood_log))) \
        if state.mood_log else None
    m["weiterbildungen"] = sum(1 for item in state.trainings
                               if item.get("art") != TRAINING_COACHING)
    m["experte"] = int(max([max(list(state.staff_topics(staff_id).values()) + [0])
                            for staff_id in state.staff] + [0]))
    answers = list(state.answers.values())
    m["geschlichtet"] = sum(1 for item in answers if item.get("art") == EV_CONFLICT and
                            item.get("wahl") == CONFLICT_MEDIATE)
    m["abwerbung_abgewehrt"] = sum(1 for item in answers if item.get("art") == EV_RECALL and
                                   item.get("wahl") and item.get("wahl") != RECALL_LET)
    m["macke_gezaehmt"] = 0
    for staff_id in state.staff:
        item = state.quirk_of(staff_id)
        if item and item["start"] > 1 and item["stufe"] == 1:
            m["macke_gezaehmt"] = 1
            break
    # Wissen aus der Lernplattform (nur mit Wissensstand je Thema)
    if knowledge is None:
        m["themen_70"] = m["fachbereiche_70"] = None
    else:
        m["themen_70"] = sum(1 for topic in TOPIC_ORDER
                             if knowledge.get(topic, 0) >= KNOWLEDGE_GOAL)
        m["fachbereiche_70"] = sum(1 for topics in CAT_TOPICS.values() if topics and all(
            knowledge.get(topic, 0) >= KNOWLEDGE_GOAL for topic in topics))
    if not firm:
        for key in ("mitarbeiter", "tagesumsatz", "stimmung_max"):
            m[key] = m[key] or None
    return m


def achievement_level(rule, value):
    """Wie viele Stufen eines Abzeichens mit diesem Wert erreicht sind."""
    if value is None:
        return 0
    level = 0
    for stage in rule["stufen"]:
        if value >= stage.get("ab", 1):
            level += 1
        else:
            break
    return level


def metric_text(key, value):
    """Wert einer Kennzahl fuer die Anzeige."""
    if value is None:
        return "–"
    if key in EURO_METRICS:
        return _whole_euro(value)
    return "{:,.0f}".format(value).replace(",", ".")


def stage_goal_text(rule, index):
    """Was fuer eine Stufe noetig ist, z.B. "500" oder "Senior"."""
    stage = rule["stufen"][index]
    if stage.get("text"):
        return stage["text"]
    if "ab" in stage and (stage["ab"] != 1 or len(rule["stufen"]) > 1):
        return metric_text(rule["wert"], stage["ab"])
    return ""


def record_value_text(rule, value):
    """Bestwert fuer die Anzeige (mit Einheit)."""
    if value is None:
        return "–"
    unit = rule.get("einheit")
    if unit == "euro":
        return _whole_euro(value)
    if unit == "tag":
        return "Tag %d" % value
    if unit == "tage":
        return _days_text(int(value))
    return metric_text(rule["id"], value)


def _better(rule, value, other):
    if other is None:
        return value is not None
    if value is None:
        return False
    return value < other if rule.get("besser") == "weniger" else value > other


def record_runs(records):
    """Kennungen aller Durchgaenge in der Bestenliste, aelteste zuerst."""
    return sorted({run for _stamp, run, _kind, _key, _value, _data in records if run})


def record_best(records, key, rule, runs=None, exclude=None):
    """(Wert, Daten, Durchgang) des besten Eintrags zu einem Bestwert."""
    best = (None, {}, None)
    for _stamp, run, kind, rec_key, value, data in records:
        if kind != REC_BEST or rec_key != key or run == exclude or value is None:
            continue
        if runs is not None and run not in runs:
            continue
        if _better(rule, value, best[0]):
            best = (value, data, run)
    return best


def record_board(records, state=None, content=None):
    """Die Bestenliste fuer die Anzeige: {"durchgaenge", "diensttage",
    "werte": [{"id", "name", "text", "wert", "wert_text", "durchgang" (Nummer),
    "tag", "extra", "aktuell", "aktuell_text", "rekord" (laufender Durchgang
    haelt ihn)}]}"""
    content = content or GAME
    runs = record_runs(records)
    current = state.first_event if state is not None and state.profile else None
    if current and current not in runs:
        runs.append(current)
        runs.sort()
    number = {run: index + 1 for index, run in enumerate(runs)}
    metrics = run_metrics(state, None, content) if current else {}
    total_days = {}
    for _stamp, run, kind, key, value, _data in records:
        if kind == REC_BEST and key == "diensttage" and value is not None:
            total_days[run] = max(total_days.get(run, 0), int(value))
    if current:
        total_days[current] = max(total_days.get(current, 0), metrics.get("diensttage") or 0)
    values = []
    for rule in achievement_rules(content).get("bestwerte") or []:
        value, data, run = record_best(records, rule["id"], rule)
        mine = metrics.get(rule["id"]) if current else None
        if rule.get("besser") != "weniger" and not mine:
            mine = None         # 0 ist (noch) kein Bestwert
        if current and _better(rule, mine, value):
            value, data, run = mine, {"tag": state.days_done,
                                      "text": metrics["_texte"].get(rule["id"], "")}, current
        values.append({"id": rule["id"], "name": rule["name"], "text": rule.get("text", ""),
                       "wert": value, "wert_text": record_value_text(rule, value),
                       "durchgang": number.get(run), "tag": (data or {}).get("tag"),
                       "extra": (data or {}).get("text", ""),
                       "aktuell": mine, "aktuell_text": record_value_text(rule, mine),
                       "rekord": bool(current) and run == current and value is not None})
    return {"durchgaenge": len(runs), "diensttage": sum(total_days.values()),
            "werte": values, "aktuell": number.get(current)}


def record_detail(item, runs):
    """Zweite Zeile unter einem Bestwert (PC und Handy gleich)."""
    if item["wert"] is None:
        return item["text"] or "noch nicht erreicht"
    parts = []
    if runs > 1:
        if item["rekord"]:
            parts.append("in diesem Durchgang")
        else:
            parts.append("%d. Durchgang" % item["durchgang"] if item["durchgang"] else "")
            if item["aktuell"] is not None:
                parts.append("jetzt %s" % item["aktuell_text"])
    parts.append(item["extra"] or item["text"])
    return " · ".join(part for part in parts if part)


def record_subtitle(board):
    runs = board["durchgaenge"]
    if runs <= 1:
        return "über alle Spielstände · dein erster Durchgang"
    return "über alle Spielstände · %d Durchgänge · %d Diensttage" % (runs, board["diensttage"])


def badge_status(item):
    """(Zeile unter dem Namen, Farbe-Schluessel) fuer ein Abzeichen:
    erreichte Stufe mit Tag, sonst der Fortschritt."""
    if item["geheim"]:
        return "noch nicht entdeckt", "muted"
    if item["tier"]:
        stage = item["stufen"][item["stufe"] - 1]
        text = "%s · Tag %d" % (stage["name"], stage["erreicht"] or 1)
        if item["naechste"] and item["fortschritt"]:
            text += " · %s" % item["fortschritt"]
        if item["je"] > item["stufe"]:
            text += " · früher: %s" % item["stufen"][item["je"] - 1]["name"]
        return text, item["tier"]
    text = item["fortschritt"] or "offen"
    if item["je"]:
        text += " · früher: %s" % item["stufen"][item["je"] - 1]["name"]
    return text, "muted"


def badge_goals(item):
    """Die Ziele aller Stufen in einer Zeile, z.B. "Bronze 50 · Silber 200 · Gold 500"."""
    if item["geheim"]:
        return ""
    parts = []
    for stage in item["stufen"]:
        parts.append(("%s %s" % (stage["name"], stage["ziel"])).strip())
    return " · ".join(parts)


def badge_history(records):
    """(erfolg, stufe) -> Menge der Durchgaenge, in denen die Stufe erreicht wurde."""
    result = {}
    for _stamp, run, kind, key, value, _data in records:
        if kind == REC_BADGE and ":" in str(key):
            achievement_id, stage = str(key).rsplit(":", 1)
            if stage.isdigit():
                result.setdefault((achievement_id, int(stage)), set()).add(run)
    return result


def achievement_overview(state, knowledge=None, records=None, content=None):
    """Alle Abzeichen fuer die Anzeige, in der Reihenfolge von erfolge.json:
    [{"id", "name", "gruppe", "text", "bild", "farbe", "stufe" (erreicht im
    laufenden Durchgang), "tier" (hoechste erreichte oder None), "stufen":
    [{"tier", "name", "ziel", "erreicht" (Tag oder None), "moment"}],
    "naechste" (Ziel der naechsten Stufe), "fortschritt" (Text), "anteil"
    (0 bis 1), "geheim" (noch nie erreicht und geheim), "je" (hoechste Stufe
    ueber alle Durchgaenge), "durchgaenge" (in wie vielen erreicht)}]"""
    content = content or state.content
    metrics = run_metrics(state, knowledge, content)
    history = badge_history(records or [])
    result = []
    for rule in achievement_rules(content).get("erfolge") or []:
        stages = []
        level = 0
        for index, stage in enumerate(rule["stufen"]):
            reached = state.achievements.get((rule["id"], index + 1))
            if reached:
                level = index + 1
            stages.append({"tier": stage["stufe"], "name": TIER_NAMES[stage["stufe"]],
                           "ziel": stage_goal_text(rule, index),
                           "erreicht": int(reached.get("tag") or 0) if reached else None,
                           "moment": bool(stage.get("moment"))})
        ever = max([number for (achievement_id, number), runs in history.items()
                    if achievement_id == rule["id"] and runs] + [level])
        runs = set()
        for (achievement_id, _number), found in history.items():
            if achievement_id == rule["id"]:
                runs |= found
        value = metrics.get(rule["wert"])
        following = rule["stufen"][level] if level < len(rule["stufen"]) else None
        progress, share = "", 1.0
        if following is not None:
            goal = following.get("ab", 1)
            have = value or 0
            share = max(0.0, min(1.0, float(have) / goal)) if goal else 0.0
            if value is None and rule.get("wissen"):
                progress = "Wissensstand wird geladen"
            elif rule["wert"] in LEVEL_METRICS and following.get("text"):
                progress = "nächstes Ziel: %s" % following["text"]
            elif goal > 1:
                progress = "%s / %s" % (metric_text(rule["wert"], min(have, goal)),
                                        metric_text(rule["wert"], goal))
        result.append({
            "id": rule["id"], "name": rule["name"], "gruppe": rule["gruppe"],
            "text": rule["text"], "bild": rule["bild"], "farbe": rule.get("farbe", ""),
            "ort": rule.get("ort"), "stufe": level,
            "tier": rule["stufen"][level - 1]["stufe"] if level else None,
            "stufen": stages,
            "naechste": stages[level] if level < len(stages) else None,
            "fortschritt": progress, "anteil": share,
            "balken": bool(progress) and rule["wert"] not in LEVEL_METRICS and
            not (value is None and rule.get("wissen")),
            "geheim": bool(rule.get("geheim")) and not ever,
            "je": ever, "durchgaenge": len(runs)})
    return result


def achievement_counts(items):
    """(erreichte Stufen, alle Stufen, {tier: Anzahl}) fuer die Ueberschrift."""
    tiers = {tier: 0 for tier in TIER_ORDER}
    reached = total = 0
    for item in items:
        total += len(item["stufen"])
        for stage in item["stufen"]:
            if stage["erreicht"] is not None:
                reached += 1
                tiers[stage["tier"]] += 1
    return reached, total, tiers


def achievement_groups(content=None):
    return [("alle", "Alle")] + [tuple(item) for item in
                                  achievement_rules(content).get("gruppen") or []]


def unlock_info(state, rule, level, records, content=None):
    """Was der Meilenstein-Moment (oder der kurze Hinweis) zu einer neu
    erreichten Stufe zeigt."""
    content = content or state.content
    stage = rule["stufen"][level - 1]
    runs = badge_history(records).get((rule["id"], level), set())
    others = [run for run in record_runs(records) if run != state.first_event]
    first = not (runs - {state.first_event})
    goal = stage_goal_text(rule, level - 1)
    text = rule["text"]
    if goal:
        text = "%s: %s" % (text.rstrip("."), goal)
    if stage.get("moment") and rule.get("moment_text"):
        text = rule["moment_text"].format(
            ziel=goal, tag=state.day, spieler=(state.profile or {}).get("name", ""),
            firma=state.firm["name"] if state.firm else "Deine Firma",
            filiale=state.branch["name"] if state.branch else "Die Filiale")
    record = ""
    key = rule.get("bestwert")
    if key and others:
        best_rule = record_rule(key, content)
        mine = run_metrics(state, None, content).get(key)
        value, _data, _run = record_best(records, key, best_rule, exclude=state.first_event)
        if value is not None and _better(best_rule, mine, value):
            record = "Neuer Bestwert! Bisher: %s" % record_value_text(best_rule, value)
    return {"erfolg": rule["id"], "stufe": level, "name": rule["name"],
            "tier": stage["stufe"], "tier_name": TIER_NAMES[stage["stufe"]],
            "text": text, "moment": bool(stage.get("moment")),
            "erstes_mal": first and bool(others), "bestwert": record,
            "bild": rule["bild"], "farbe": rule.get("farbe", ""), "ort": rule.get("ort"),
            "hinweis": "Abzeichen: %s · %s" % (rule["name"], TIER_NAMES[stage["stufe"]])}


def new_achievements(state, knowledge=None, content=None):
    """Stufen, die laut Spielstand erreicht, aber noch nicht als Ereignis
    festgehalten sind: [(regel, stufe)]."""
    content = content or state.content
    metrics = run_metrics(state, knowledge, content)
    result = []
    for rule in achievement_rules(content).get("erfolge") or []:
        if rule.get("wissen") and knowledge is None:
            continue
        for level in range(1, achievement_level(rule, metrics.get(rule["wert"])) + 1):
            if (rule["id"], level) not in state.achievements:
                result.append((rule, level))
    return result


def record_rows(state, records, content=None, force=False):
    """Zeilen, die fuer den laufenden Durchgang neu in die Bestenliste
    gehoeren: [(art, schluessel, wert, daten)]. Ein besserer Wert kommt nur
    hinein, wenn es fuer ihn noch keinen Eintrag gibt, der letzte RECORD_EVERY
    Arbeitstage her ist oder force (vor dem Zuruecksetzen)."""
    content = content or state.content
    run = state.first_event
    if not run or state.profile is None:
        return []
    mine = [row for row in records if row[1] == run]
    rows = []
    if not any(row[2] == REC_RUN for row in mine):
        rows.append((REC_RUN, "start", None, {"name": state.profile["name"]}))
    metrics = run_metrics(state, None, content)
    rules = list(achievement_rules(content).get("bestwerte") or []) + \
        [{"id": key, "besser": "mehr"} for key in RECORD_SUMS]
    for rule in rules:
        value = metrics.get(rule["id"])
        if value is None or (rule.get("besser") != "weniger" and not value):
            continue
        best, data, _run = record_best(mine, rule["id"], rule)
        last = max([int((row[5] or {}).get("tag") or 0) for row in mine
                    if row[2] == REC_BEST and row[3] == rule["id"]] + [-RECORD_EVERY])
        due = force or best is None or state.days_done - last >= RECORD_EVERY
        if due and _better(rule, value, best):
            rows.append((REC_BEST, rule["id"], value,
                         {"tag": state.days_done, "text": metrics["_texte"].get(rule["id"], "")}))
    have = {row[3] for row in mine if row[2] == REC_BADGE}
    for (achievement_id, level), data in sorted(state.achievements.items()):
        key = "%s:%d" % (achievement_id, level)
        if key not in have:
            rows.append((REC_BADGE, key, level, {"tag": data.get("tag")}))
    return rows


# -- Abzeichen als Bild (Orden mit kleinem Bild im Kartenstil) -----------------

BADGE_SIZE = 2.4              # Kantenlaenge eines Abzeichens in Zeicheneinheiten


def badge_color(name):
    """Farbe des Bildes: Rolle der Weltkarte (firma, filiale ...) oder Farbname."""
    if name in ("bitweiche", "kunde", "firma", "zuhause", "filiale"):
        return map_role_color(name)
    return C.get(name, C["accent"])


def _pic_house(cx, cy, k, color, dim):
    wall = mix(C["card_alt"], color, 0.12) if not dim else color
    s = [_rect(cx - 0.62 * k, cy - 0.5 * k, 1.24 * k, 0.55 * k, color, r=0.08 * k),
         _rect(cx - 0.62 * k, cy + 0.05 * k, 1.24 * k, 0.42 * k, wall)]
    for number in range(3):
        s.append(_rect(cx - 0.47 * k + number * 0.36 * k, cy + 0.14 * k, 0.2 * k, 0.2 * k,
                       C["card"] if dim else mix(C["yellow"], "#FFFFFF", 0.45)))
    return s


def _pic_star(cx, cy, k, color, _dim):
    points = []
    for index in range(10):
        radius = 0.68 * k if index % 2 == 0 else 0.29 * k
        angle = math.pi / 5 * index - math.pi / 2
        points.append((cx + radius * math.cos(angle), cy + 0.06 * k + radius * math.sin(angle)))
    return [_poly(points, color)]


def _pic_ticket(cx, cy, k, color, dim):
    s = [_rect(cx - 0.5 * k, cy - 0.6 * k, 1.0 * k, 1.2 * k, color, r=0.08 * k)]
    for number in range(4):
        s.append(_rect(cx - 0.32 * k, cy - 0.38 * k + number * 0.24 * k,
                       (0.64 if number < 3 else 0.36) * k, 0.08 * k, C["card"]))
    return s


def _pic_lightning(cx, cy, k, color, _dim):
    return [_poly([(cx + 0.12 * k, cy - 0.7 * k), (cx - 0.42 * k, cy + 0.1 * k),
                   (cx - 0.02 * k, cy + 0.1 * k), (cx - 0.16 * k, cy + 0.7 * k),
                   (cx + 0.42 * k, cy - 0.12 * k), (cx + 0.02 * k, cy - 0.12 * k)], color)]


def _pic_check(cx, cy, k, color, _dim):
    return [_line(cx - 0.5 * k, cy + 0.02 * k, cx - 0.14 * k, cy + 0.4 * k, color, 0.2 * k),
            _line(cx - 0.14 * k, cy + 0.4 * k, cx + 0.55 * k, cy - 0.42 * k, color, 0.2 * k)]


def _pic_shield(cx, cy, k, color, dim):
    return [_poly([(cx - 0.55 * k, cy - 0.55 * k), (cx + 0.55 * k, cy - 0.55 * k),
                   (cx + 0.5 * k, cy + 0.1 * k), (cx, cy + 0.68 * k),
                   (cx - 0.5 * k, cy + 0.1 * k)], color),
            _poly([(cx - 0.32 * k, cy - 0.36 * k), (cx, cy - 0.36 * k), (cx, cy + 0.42 * k),
                   (cx - 0.3 * k, cy + 0.02 * k)], mix(color, "#FFFFFF", 0.3) if not dim
                  else color)]


def _pic_key(cx, cy, k, color, _dim):
    return [_oval(cx - 0.62 * k, cy - 0.34 * k, 0.56 * k, 0.56 * k, "", color, 0.16 * k),
            _line(cx - 0.08 * k, cy - 0.06 * k, cx + 0.62 * k, cy - 0.06 * k, color, 0.16 * k),
            _line(cx + 0.36 * k, cy - 0.06 * k, cx + 0.36 * k, cy + 0.26 * k, color, 0.14 * k),
            _line(cx + 0.56 * k, cy - 0.06 * k, cx + 0.56 * k, cy + 0.2 * k, color, 0.14 * k)]


def _pic_rails(cx, cy, k, color, _dim):
    s = []
    for number in range(5):
        y = cy - 0.56 * k + number * 0.28 * k
        s.append(_rect(cx - 0.55 * k, y, 1.1 * k, 0.1 * k, mix(color, C["card"], 0.55)))
    for dx in (-0.28, 0.28):
        s.append(_line(cx + dx * k, cy - 0.7 * k, cx + dx * k, cy + 0.7 * k, color, 0.12 * k))
    return s


def _pic_people(cx, cy, k, color, _dim):
    s = []
    for dx in (-0.42, 0.42, 0.0):
        tone = color if dx == 0 else mix(color, C["card"], 0.3)
        s.append(_oval(cx + (dx - 0.17) * k, cy - 0.45 * k, 0.34 * k, 0.34 * k, tone))
        s.append(_rect(cx + (dx - 0.24) * k, cy - 0.05 * k, 0.48 * k, 0.5 * k, tone,
                       r=0.2 * k))
    return s


def _pic_paper(cx, cy, k, color, dim):
    paper = C["text"] if not dim else color
    s = [_rect(cx - 0.48 * k, cy - 0.62 * k, 0.96 * k, 1.2 * k, paper, r=0.06 * k)]
    for number in range(3):
        s.append(_rect(cx - 0.3 * k, cy - 0.42 * k + number * 0.22 * k, 0.6 * k, 0.07 * k,
                       C["muted"] if not dim else C["card"]))
    s.append(_oval(cx + 0.06 * k, cy + 0.12 * k, 0.4 * k, 0.4 * k, color if not dim else
                   C["card"]))
    return s


def _pic_form(cx, cy, k, color, dim):
    paper = C["text"] if not dim else color
    s = [_rect(cx - 0.48 * k, cy - 0.62 * k, 0.96 * k, 1.2 * k, paper, r=0.06 * k)]
    for number in range(3):
        y = cy - 0.4 * k + number * 0.34 * k
        s.append(_rect(cx - 0.32 * k, y, 0.16 * k, 0.16 * k, color if not dim else C["card"]))
        s.append(_rect(cx - 0.06 * k, y + 0.04 * k, 0.38 * k, 0.07 * k,
                       C["muted"] if not dim else C["card"]))
    return s


def _pic_crane(cx, cy, k, color, _dim):
    return [_line(cx - 0.3 * k, cy + 0.66 * k, cx - 0.3 * k, cy - 0.62 * k, color, 0.14 * k),
            _line(cx - 0.6 * k, cy - 0.55 * k, cx + 0.62 * k, cy - 0.55 * k, color, 0.12 * k),
            _line(cx + 0.42 * k, cy - 0.55 * k, cx + 0.42 * k, cy + 0.02 * k,
                  mix(color, C["card"], 0.3), 0.05 * k),
            _rect(cx + 0.24 * k, cy + 0.02 * k, 0.36 * k, 0.3 * k, color, r=0.04 * k),
            _rect(cx - 0.62 * k, cy + 0.56 * k, 0.64 * k, 0.14 * k, mix(color, C["card"], 0.3))]


def _pic_chart(cx, cy, k, color, _dim):
    s = []
    for number, height in enumerate((0.45, 0.75, 1.1)):
        s.append(_rect(cx - 0.55 * k + number * 0.4 * k, cy + 0.6 * k - height * k, 0.28 * k,
                       height * k, mix(color, C["card"], 0.35 - number * 0.15), r=0.04 * k))
    return s


def _pic_arrow(cx, cy, k, color, _dim):
    return [_line(cx - 0.6 * k, cy + 0.42 * k, cx - 0.18 * k, cy, color, 0.16 * k),
            _line(cx - 0.18 * k, cy, cx + 0.08 * k, cy + 0.22 * k, color, 0.16 * k),
            _line(cx + 0.08 * k, cy + 0.22 * k, cx + 0.46 * k, cy - 0.28 * k, color, 0.16 * k),
            _poly([(cx + 0.64 * k, cy - 0.56 * k), (cx + 0.66 * k, cy - 0.06 * k),
                   (cx + 0.22 * k, cy - 0.38 * k)], color)]


def _pic_cup(cx, cy, k, color, _dim):
    return [_oval(cx - 0.66 * k, cy - 0.5 * k, 0.4 * k, 0.44 * k, "", color, 0.1 * k),
            _oval(cx + 0.26 * k, cy - 0.5 * k, 0.4 * k, 0.44 * k, "", color, 0.1 * k),
            _poly([(cx - 0.45 * k, cy - 0.62 * k), (cx + 0.45 * k, cy - 0.62 * k),
                   (cx + 0.3 * k, cy + 0.02 * k), (cx - 0.3 * k, cy + 0.02 * k)], color),
            _rect(cx - 0.08 * k, cy, 0.16 * k, 0.36 * k, color),
            _rect(cx - 0.36 * k, cy + 0.36 * k, 0.72 * k, 0.2 * k, color, r=0.04 * k)]


def _pic_coins(cx, cy, k, color, _dim):
    s = []
    for number in range(4):
        y = cy + 0.34 * k - number * 0.26 * k
        s.append(_oval(cx - 0.52 * k, y - 0.2 * k, 1.04 * k, 0.4 * k, color,
                       mix(color, "#000000", 0.45), 0.04 * k))
    return s


def _pic_anchor(cx, cy, k, color, _dim):
    return [_oval(cx - 0.14 * k, cy - 0.72 * k, 0.28 * k, 0.28 * k, "", color, 0.08 * k),
            _line(cx, cy - 0.44 * k, cx, cy + 0.6 * k, color, 0.14 * k),
            _line(cx - 0.3 * k, cy - 0.26 * k, cx + 0.3 * k, cy - 0.26 * k, color, 0.12 * k),
            _line(cx, cy + 0.6 * k, cx - 0.52 * k, cy + 0.24 * k, color, 0.12 * k),
            _line(cx, cy + 0.6 * k, cx + 0.52 * k, cy + 0.24 * k, color, 0.12 * k)]


def _pic_heart(cx, cy, k, color, _dim):
    return [_oval(cx - 0.6 * k, cy - 0.5 * k, 0.66 * k, 0.62 * k, color),
            _oval(cx - 0.06 * k, cy - 0.5 * k, 0.66 * k, 0.62 * k, color),
            _poly([(cx - 0.56 * k, cy - 0.04 * k), (cx + 0.56 * k, cy - 0.04 * k),
                   (cx, cy + 0.62 * k)], color)]


def _pic_hat(cx, cy, k, color, _dim):
    return [_poly([(cx - 0.72 * k, cy - 0.2 * k), (cx, cy - 0.54 * k), (cx + 0.72 * k, cy - 0.2 * k),
                   (cx, cy + 0.14 * k)], color),
            _poly([(cx - 0.4 * k, cy - 0.02 * k), (cx + 0.4 * k, cy - 0.02 * k),
                   (cx + 0.4 * k, cy + 0.32 * k), (cx - 0.4 * k, cy + 0.32 * k)],
                  mix(color, C["card"], 0.3)),
            _line(cx + 0.6 * k, cy - 0.22 * k, cx + 0.6 * k, cy + 0.34 * k, color, 0.06 * k)]


def _pic_bubble(cx, cy, k, color, _dim):
    other = mix(color, C["card"], 0.35)
    return [_rect(cx - 0.68 * k, cy - 0.6 * k, 0.86 * k, 0.6 * k, other, r=0.2 * k),
            _poly([(cx - 0.52 * k, cy - 0.04 * k), (cx - 0.3 * k, cy - 0.04 * k),
                   (cx - 0.56 * k, cy + 0.2 * k)], other),
            _rect(cx - 0.18 * k, cy - 0.16 * k, 0.86 * k, 0.6 * k, color, r=0.2 * k),
            _poly([(cx + 0.3 * k, cy + 0.4 * k), (cx + 0.52 * k, cy + 0.4 * k),
                   (cx + 0.56 * k, cy + 0.64 * k)], color)]


def _pic_magnet(cx, cy, k, color, _dim):
    return [_line(cx - 0.36 * k, cy - 0.5 * k, cx - 0.36 * k, cy + 0.2 * k, color, 0.26 * k),
            _line(cx + 0.36 * k, cy - 0.5 * k, cx + 0.36 * k, cy + 0.2 * k, color, 0.26 * k),
            _oval(cx - 0.49 * k, cy - 0.16 * k, 0.98 * k, 0.8 * k, "", color, 0.26 * k),
            _rect(cx - 0.5 * k, cy - 0.66 * k, 0.28 * k, 0.2 * k, C["text"]),
            _rect(cx + 0.22 * k, cy - 0.66 * k, 0.28 * k, 0.2 * k, C["text"])]


def _pic_screwdriver(cx, cy, k, color, _dim):
    return [_line(cx - 0.52 * k, cy + 0.52 * k, cx - 0.12 * k, cy + 0.12 * k, color, 0.3 * k),
            _line(cx - 0.12 * k, cy + 0.12 * k, cx + 0.55 * k, cy - 0.55 * k, METAL, 0.1 * k)]


def _pic_book(cx, cy, k, color, _dim):
    return [_poly([(cx - 0.7 * k, cy - 0.45 * k), (cx - 0.04 * k, cy - 0.32 * k),
                   (cx - 0.04 * k, cy + 0.56 * k), (cx - 0.7 * k, cy + 0.42 * k)], color),
            _poly([(cx + 0.04 * k, cy - 0.32 * k), (cx + 0.7 * k, cy - 0.45 * k),
                   (cx + 0.7 * k, cy + 0.42 * k), (cx + 0.04 * k, cy + 0.56 * k)],
                  mix(color, C["card"], 0.25))]


BADGE_PICTURES = {
    "haus": _pic_house, "stern": _pic_star, "ticket": _pic_ticket, "blitz": _pic_lightning,
    "haken": _pic_check, "schild": _pic_shield, "schluessel": _pic_key, "gleise": _pic_rails,
    "personen": _pic_people, "urkunde": _pic_paper, "formular": _pic_form, "kran": _pic_crane,
    "diagramm": _pic_chart, "pfeil": _pic_arrow, "pokal": _pic_cup, "muenzen": _pic_coins,
    "anker": _pic_anchor, "herz": _pic_heart, "hut": _pic_hat, "sprechblase": _pic_bubble,
    "magnet": _pic_magnet, "schraube": _pic_screwdriver, "buch": _pic_book,
}


def badge_shapes(picture, color, tier=None, ox=0.0, oy=0.0, size=BADGE_SIZE):
    """Zeichenbefehle fuer ein Abzeichen (runder Orden) links oben bei (ox, oy).
    tier None = noch nicht erreicht (dunkel, mit Schloss)."""
    k = size / BADGE_SIZE
    cx, cy = ox + size / 2.0, oy + size / 2.0
    radius = 1.0 * k
    locked = tier is None
    ring = C["border_hi"] if locked else TIER_COLORS[tier]
    dark = C["card_alt"] if locked else mix(ring, "#000000", 0.55)
    s = [_oval(cx - radius - 0.12 * k, cy - radius - 0.12 * k, 2 * (radius + 0.12 * k),
               2 * (radius + 0.12 * k), dark),
         _oval(cx - radius, cy - radius, 2 * radius, 2 * radius, mix(C["bg"], "#000000", 0.2),
               ring, 0.13 * k)]
    tone = mix(C["muted"], C["bg"], 0.45) if locked else badge_color(color)
    draw = BADGE_PICTURES.get(picture, _pic_star)
    s += draw(cx, cy + (0.05 if not locked else -0.08) * k, 0.72 * k, tone, locked)
    if locked:
        lock = C["muted"]
        s.append(_oval(cx - 0.14 * k, cy + 0.34 * k, 0.28 * k, 0.3 * k, "", lock, 0.06 * k))
        s.append(_rect(cx - 0.2 * k, cy + 0.48 * k, 0.4 * k, 0.3 * k, lock, r=0.05 * k))
    return s


def moment_shapes(info, state, content=None):
    """Szene fuer den Meilenstein-Moment: der Ort im Kartenstil mit
    Strahlen in der Farbe der Stufe. (Zeichenbefehle, Breite, Hoehe)."""
    content = content or GAME
    width, height = 12.0, 6.0
    colors = map_palette()
    s = [_rect(0, 0, width, height, colors["boden"], r=0.4),
         _rect(0, height - 1.3, width, 0.8, colors["strasse"]),
         _rect(0, height - 0.94, width, 0.08, colors["strasse_mitte"])]
    for x, y, r in ((0.9, 1.4, 0.45), (1.8, 2.8, 0.4), (10.9, 1.2, 0.42), (11.2, 3.1, 0.45),
                    (0.8, 4.0, 0.38)):
        s += _map_tree(x, y, r, colors)
    ray = TIER_COLORS.get(info.get("tier"), C["yellow"])
    cx, cy = width / 2.0, height / 2.0 - 0.1
    for index in range(16):
        angle = math.pi / 8 * index
        s.append(_line(cx + 2.9 * math.cos(angle), cy + 2.0 * math.sin(angle),
                       cx + 3.9 * math.cos(angle), cy + 2.7 * math.sin(angle),
                       mix(ray, colors["boden"], 0.4), 0.09))
    place = info.get("ort")
    shapes, w, h = place_preview(place, state, content) if place else ([], 0, 0)
    if shapes:
        scale = min(4.6 / w, 3.4 / h)
        dx, dy = cx - w * scale / 2.0, cy - h * scale / 2.0 + 0.2
        for shape in shapes:
            s.append(_scale_shape(shape, scale, dx, dy))
        item = next((entry for entry in map_places(state, content) if entry["id"] == place),
                    None)
        if item:
            label = _text(cx, dy - 0.05, item["name"], "ort", C["text"], anchor="c")
            label["bg"] = colors["schild"]
            label["border"] = item["farbe"]
            s.append(label)
    else:
        s += badge_shapes(info.get("bild"), info.get("farbe"), info.get("tier"),
                          cx - 1.6, cy - 1.6, 3.2)
    return s, width, height


def _scale_shape(shape, scale, dx, dy):
    shape = dict(shape)
    if shape["k"] in ("rect", "oval", "arc", "text"):
        shape["x"] = shape["x"] * scale + dx
        shape["y"] = shape["y"] * scale + dy
        for key in ("w", "h"):
            if key in shape:
                shape[key] = shape[key] * scale
    elif shape["k"] in ("line", "poly"):
        shape["pts"] = [value * scale + (dx if index % 2 == 0 else dy)
                        for index, value in enumerate(shape["pts"])]
    for key in ("lw", "r"):
        if shape.get(key):
            shape[key] = shape[key] * scale
    return shape


def _validate_achievements(content):
    """erfolge.json: Kennzahlen, Stufen, Bilder und Bestwerte."""
    rules = achievement_rules(content)
    if not rules:
        return ["Spiel: erfolge.json fehlt"]
    problems = []
    groups = {item[0] for item in rules.get("gruppen") or []}
    places = {item["id"] for item in map_rules(content).get("orte") or []}
    ids = set()
    for rule in rules.get("erfolge") or []:
        where = "Spiel-Erfolg %s" % rule.get("id")
        if rule.get("id") in ids:
            problems.append("%s: Kennung doppelt" % where)
        ids.add(rule.get("id"))
        if rule.get("gruppe") not in groups:
            problems.append("%s: unbekannte Gruppe '%s'" % (where, rule.get("gruppe")))
        if rule.get("wert") not in RUN_METRICS:
            problems.append("%s: unbekannter Wert '%s'" % (where, rule.get("wert")))
        if rule.get("bild") not in BADGE_PICTURES:
            problems.append("%s: unbekanntes Bild '%s'" % (where, rule.get("bild")))
        if rule.get("ort") and rule["ort"] not in places:
            problems.append("%s: unbekannter Ort '%s'" % (where, rule["ort"]))
        if rule.get("bestwert") and not record_rule(rule["bestwert"], content):
            problems.append("%s: unbekannter Bestwert '%s'" % (where, rule["bestwert"]))
        if rule.get("moment_text"):
            try:
                rule["moment_text"].format(ziel="", tag=1, spieler="", firma="", filiale="")
            except (KeyError, IndexError, ValueError):
                problems.append("%s: unbekannter Platzhalter im moment_text" % where)
        stages = rule.get("stufen") or []
        if not stages or len(stages) > 3:
            problems.append("%s: 1 bis 3 Stufen noetig" % where)
        tiers = [stage.get("stufe") for stage in stages]
        if any(tier not in TIER_ORDER for tier in tiers) or \
                [TIER_ORDER.index(tier) for tier in tiers if tier in TIER_ORDER] != \
                sorted(TIER_ORDER.index(tier) for tier in tiers if tier in TIER_ORDER):
            problems.append("%s: Stufen muessen Bronze, Silber, Gold sein (aufsteigend)" % where)
        goals = [stage.get("ab", 1) for stage in stages]
        if goals != sorted(goals) or len(set(goals)) != len(goals):
            problems.append("%s: Stufen-Werte muessen steigen" % where)
    for rule in rules.get("bestwerte") or []:
        if rule.get("id") not in RUN_METRICS:
            problems.append("Spiel-Bestwert %s: unbekannter Wert" % rule.get("id"))
        if rule.get("besser") not in ("mehr", "weniger"):
            problems.append("Spiel-Bestwert %s: besser muss mehr oder weniger sein"
                            % rule.get("id"))
    return problems


# ============================================================================
#
# Alle drei Orte benutzen dasselbe Zeichnen (building_shapes) und Laufen
# (walk_path): site_content() baut dafuer ein "Inhalts-Woerterbuch" wie
# GAME, nur mit dem Grundriss und den Personen des jeweiligen Ortes. Die
# Ergebnisse werden zwischengespeichert, damit gleiche Orte dasselbe Objekt
# bleiben (das Laufraster wird je Grundriss nur einmal berechnet).

SITE_OFFICE = "buero"
SITE_HOME = "zuhause"
SITE_BRANCH = "filiale"       # zweiter Standort der eigenen Firma (ab 0.45)
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
    if site_id == SITE_BRANCH:
        return state.branch["name"] if state is not None and state.branch else "Filiale"
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
    if site_id == SITE_BRANCH:
        return firm_people(state, content, SITE_BRANCH) if state is not None else []
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
    elif site_id == SITE_BRANCH:
        base = branch_building(state, content) if state is not None else None
        if base is None:
            raise ValueError("Die Filiale ist noch nicht eröffnet.")
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
            if state.firm:
                # Ab 0.43: Urlaubsanfragen und Konflikte warten auf dich
                return ("Eingangstür", DECISIONS_OPEN_TEXT,
                        [(ACTION_PERSONAL, "Zu den Entscheidungen")])
            left = len(state.open_tickets())
            return ("Eingangstür", "Noch nicht: %s offen." % (
                "1 Ticket ist" if left == 1 else "%d Tickets sind" % left), [])
        if site_id == SITE_BRANCH:
            return ("Ausgang", "Von hier geht es zurück zum Gewerbehof am Stellwerk.",
                    [("buero", "Zum Gewerbehof")])
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
        market = market_news(state, content)
        staff = personal_news(state, content)
        text = "\n\n".join(part for part in (text, news, market, staff) if part)
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


# ============================================================================
#  WELTKARTE (ab 0.45)
# ============================================================================
#
# Die Karte ist die Startansicht des Spiels: Landschaft (Strassen, Bahn,
# Fluss, Parks) und alle Orte als Gebaeude in 3/4-Vogelperspektive (Dach
# oben, darunter die Vorderwand). Alles steht in inhalte/spiel/orte.json -
# ein neuer Ort ist ein neuer Eintrag dort. Gezeichnet wird wie beim
# Grundriss ueber Zeichenbefehle (dazu "poly" fuer Dachschraegen), die PC und
# Handy nur noch skalieren. Welche Orte zu sehen sind, folgt aus dem
# Spielstand (Tag, Gruendung, Ausbaustufe, Filiale) - ohne eigenen Zustand.
#
#   poly  pts [x1, y1, x2, y2, ...], fill, line, lw   (geschlossenes Vieleck)

MAP_ROLES = ("bitweiche", "kunde", "firma", "zuhause", "filiale", "mitbewerber")
MAP_VIEWS = ("buero", "zuhause", "firma", "filiale")
MAP_VIEW_PREFIXES = ("kunde:", "firma:", "mitbewerber:")
MAP_UNLOCKS = ("immer", "ab_tag", "kundenort", "aufgabe", "gruendung_moeglich", "gegruendet",
               "stufe_min", "filiale_moeglich", "filiale_gebaut")
MAP_PARTS = ("block", "flaeche", "schild", "kreis", "mast", "tor", "baum", "geruest")
MAP_PART_CONDITIONS = ("ab_stufe", "bis_stufe", "ab_filiale", "bis_filiale", "raum", "wohnung",
                       "erledigt", "offen", "gegruendet")
MAP_ROOFS = ("flach", "sattel", "shed")
MAP_LANDSCAPE = ("park", "fluss", "strasse", "bahn", "baum", "ortsname", "beschriftung",
                 "gebaeude")
MAP_NEW_DAYS = 1              # so viele Arbeitstage nach der Freischaltung steht "Neu" dran
MAP_LIST_SETTING = "spiel_karte_liste"    # Liste statt Karte (je Geraet, einstellungen.json)
MAP_LABEL_MAXW = 5.2          # breiter (in Karteneinheiten) -> Kurzname auf dem Schild
MAP_CHAR_PX = 7.2             # grobe Breite eines Zeichens auf dem Schild (Pixel)


def map_rules(content=None):
    return (content or GAME).get("orte") or {}


def map_size(content=None):
    world = map_rules(content).get("welt") or {}
    return world.get("breite", 32), world.get("hoehe", 24)


def map_palette():
    """Farben der Karte - aus dem Farbschema abgeleitet, damit sie zur
    gewaehlten Grundfarbe passen."""
    ground = mix(C["bg"], C["card"], 0.55)
    return {
        "boden": ground,
        "park": mix(ground, C["green"], 0.10),
        "wasser": mix(ground, C["blue"], 0.22),
        "wasser_hell": mix(ground, C["blue"], 0.40),
        "strasse": mix(ground, C["border_hi"], 0.32),
        "strasse_mitte": mix(ground, C["border_hi"], 0.62),
        "gleis": mix(C["border_hi"], C["purple"], 0.45),
        "schwelle": mix(ground, C["border_hi"], 0.55),
        "baum": mix(ground, C["green"], 0.24),
        "baum_hell": mix(ground, C["green"], 0.42),
        "schatten": mix(ground, "#000000", 0.35),
        "licht": mix(C["yellow"], "#FFFFFF", 0.45),
        "fenster": mix(C["card_alt"], C["border_hi"], 0.35),
        "schrift": mix(C["muted"], ground, 0.25),
        "schild": C["sidebar"],
    }


def map_role_color(role):
    return {"bitweiche": C["cyan"], "kunde": C["blue"], "firma": C["green"],
            "zuhause": C["pink"], "filiale": C["purple"]}.get(role, "#8B93A1")


def _poly(points, fill, line="", lw=0.0):
    flat = []
    for x, y in points:
        flat += [x, y]
    return {"k": "poly", "pts": flat, "fill": fill, "line": line, "lw": lw}


def _polyline(points, color, lw):
    return [_line(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1], color, lw)
            for i in range(len(points) - 1)]


def _along(points, step):
    """Punkte im Abstand step entlang einer Linie: [(x, y, dx, dy)] mit
    Richtung (Einheitsvektor)."""
    result = []
    rest = 0.0
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        length = math.hypot(x2 - x1, y2 - y1)
        if length <= 0:
            continue
        dx, dy = (x2 - x1) / length, (y2 - y1) / length
        pos = rest
        while pos <= length:
            result.append((x1 + dx * pos, y1 + dy * pos, dx, dy))
            pos += step
        rest = pos - length
    return result


def _dashes(points, color, lw, dash, gap):
    """Gestrichelte Linie als einzelne Striche."""
    shapes = []
    for x, y, dx, dy in _along(points, dash + gap):
        shapes.append(_line(x, y, x + dx * dash, y + dy * dash, color, lw))
    return shapes


def _map_tree(x, y, r, colors):
    return [_oval(x - r + 0.1, y - r + 0.12, 2 * r, 2 * r, colors["schatten"]),
            _oval(x - r, y - r, 2 * r, 2 * r, colors["baum"]),
            _oval(x - r * 0.75, y - r * 0.75, r * 0.9, r * 0.9, colors["baum_hell"])]


def landscape_shapes(content=None):
    """Boden, Parks, Fluss, Strassen, Bahn, Baeume und Beschriftungen."""
    colors = map_palette()
    width, height = map_size(content)
    items = (map_rules(content).get("welt") or {}).get("landschaft") or []
    s = [_rect(0, 0, width, height, colors["boden"])]
    order = ("park", "fluss", "strasse", "bahn")
    for kind in order:
        for item in items:
            if item["typ"] != kind:
                continue
            if kind == "park":
                s.append(_rect(item["x"], item["y"], item["w"], item["h"], colors["park"],
                               r=1.1))
            elif kind == "fluss":
                s += _polyline(item["punkte"], colors["wasser"], 0.65)
                s += _dashes(item["punkte"], colors["wasser_hell"], 0.07, 0.25, 0.35)
            elif kind == "strasse":
                s += _polyline(item["punkte"], colors["strasse"], 0.72)
            elif kind == "bahn":
                for x, y, dx, dy in _along(item["punkte"], 0.17):
                    s.append(_line(x - dy * 0.15, y + dx * 0.15, x + dy * 0.15, y - dx * 0.15,
                                   colors["schwelle"], 0.05))
                s += _polyline(item["punkte"], colors["gleis"], 0.06)
    for item in items:
        if item["typ"] == "strasse":
            s += _dashes(item["punkte"], colors["strasse_mitte"], 0.04, 0.2, 0.25)
    for item in items:
        if item["typ"] == "baum":
            for x, y in item["punkte"]:
                s += _map_tree(x, y, item.get("r", 0.45), colors)
        elif item["typ"] == "ortsname":
            s.append(_text(item["x"], item["y"], item["text"], "ortsname", colors["schrift"],
                           anchor="c"))
        elif item["typ"] == "beschriftung":
            s.append(_text(item["x"], item["y"], item["text"], "person", colors["schrift"]))
    return s


def _map_context(state, content=None):
    """Was die Gebaeudemodelle vom Spielstand wissen muessen."""
    if state is None:
        return {"stufe": 0, "gegruendet": False, "filiale": 0, "raeume": set(),
                "wohnung": (content or GAME)["wohnungen"]["start"], "solved": set()}
    return {"stufe": state.firm["stufe"] if state.firm else 0,
            "gegruendet": bool(state.firm),
            "filiale": state.branch["stufe"] if state.branch else 0,
            "raeume": set(state.rooms), "wohnung": state.home_id, "solved": state.solved}


def _part_visible(part, ctx):
    if "ab_stufe" in part and ctx["stufe"] < part["ab_stufe"]:
        return False
    if "bis_stufe" in part and ctx["stufe"] > part["bis_stufe"]:
        return False
    if "ab_filiale" in part and ctx["filiale"] < part["ab_filiale"]:
        return False
    if "bis_filiale" in part and ctx["filiale"] > part["bis_filiale"]:
        return False
    if "raum" in part and part["raum"] not in ctx["raeume"]:
        return False
    if "wohnung" in part and ctx["wohnung"] not in part["wohnung"]:
        return False
    if "erledigt" in part and part["erledigt"] not in ctx["solved"]:
        return False
    if "offen" in part and part["offen"] in ctx["solved"]:
        return False
    if "gegruendet" in part and bool(part["gegruendet"]) != ctx["gegruendet"]:
        return False
    return True


def model_parts(model_id, state=None, content=None):
    """Die sichtbaren Teile eines Gebaeudemodells (je nach Spielstand)."""
    ctx = _map_context(state, content)
    return [part for part in map_rules(content).get("modelle", {}).get(model_id, [])
            if _part_visible(part, ctx)]


def _lit(seed, index, share):
    """Fester "Wuerfel": brennt in diesem Fenster Licht?"""
    digest = hashlib.sha256(("%s|%d" % (seed, index)).encode("utf-8")).hexdigest()
    return int(digest[:6], 16) / float(16 ** 6) < share


def _part_fill(name, accent, colors):
    return {"bahnsteig": mix(C["blue"], C["card"], 0.55),
            "glas": mix(C["cyan"], C["card"], 0.62),
            "holz": WOOD_DARK, "technik": METAL,
            "akzent": accent}.get(name, name or accent)


def model_part_shapes(part, ox, oy, accent, colors, seed):
    """Zeichenbefehle fuer ein Teil eines Gebaeudemodells an (ox, oy)."""
    kind = part["art"]
    x, y = ox + part.get("x", 0), oy + part.get("y", 0)
    s = []
    if kind == "block":
        w, t, h = part["w"], part["t"], part["h"]
        tone = accent if part.get("farbe") in (None, "akzent") else part["farbe"]
        wall = mix(C["card_alt"], tone, 0.12)
        roof = mix(C["card"], tone, 0.30)
        edge = mix(wall, "#000000", 0.35)
        # Schatten nach rechts oben (Licht von links)
        s.append(_poly([(x + w, y + t), (x + w + h * 0.35, y + t - h * 0.2),
                        (x + w + h * 0.35, y - h * 0.2 + 0.2), (x + w, y - h + 0.2)],
                       colors["schatten"]))
        s.append(_rect(x, y + t - h, w, h, wall, edge, 0.03))
        if part.get("fenster", True):
            rows = max(1, int(h / 0.7))
            cols = max(1, int(w / 0.8))
            cell_w, cell_h = (w - 0.3) / cols, (h - 0.2) / rows
            for row in range(rows):
                for col in range(cols):
                    lit = _lit(seed, row * cols + col, part.get("licht", 0.5))
                    s.append(_rect(x + 0.25 + col * cell_w, y + t - h + 0.2 + row * cell_h,
                                   cell_w - 0.25, cell_h - 0.3,
                                   colors["licht"] if lit else colors["fenster"]))
        top = y - h
        roof_edge = mix(roof, "#000000", 0.3)
        if part.get("dach") == "sattel":
            s.append(_poly([(x, top + t), (x, top + t * 0.5), (x + w, top + t * 0.5),
                            (x + w, top + t)], roof, roof_edge, 0.03))
            s.append(_poly([(x, top + t * 0.5), (x, top), (x + w, top), (x + w, top + t * 0.5)],
                           mix(roof, "#FFFFFF", 0.12), roof_edge, 0.03))
            s.append(_line(x, top + t * 0.5, x + w, top + t * 0.5, mix(tone, "#FFFFFF", 0.2),
                           0.04))
        elif part.get("dach") == "shed":
            s.append(_rect(x, top, w, t, roof, roof_edge, 0.03))
            count = max(2, int(w / 1.0))
            for number in range(count):
                left = x + number * w / count
                s.append(_poly([(left, top + t), (left, top), (left + 0.35 * w / count, top)],
                               mix(tone, C["card"], 0.55)))
        else:
            s.append(_rect(x, top, w, t, roof, roof_edge, 0.03))
            s.append(_rect(x + 0.15, top + 0.15, w - 0.3, t - 0.3, mix(roof, "#FFFFFF", 0.05)))
    elif kind == "flaeche":
        s.append(_rect(x, y, part["w"], part["h"], _part_fill(part.get("farbe"), accent, colors),
                       r=0.05))
    elif kind == "schild":
        s.append(_rect(x, y, part["w"], 0.28, accent, r=0.08))
    elif kind == "tor":
        s.append(_rect(x, y, part["w"], part["h"], mix(C["card"], accent, 0.18),
                       mix(accent, "#000000", 0.4), 0.03))
    elif kind == "kreis":
        r = part["r"]
        s.append(_oval(x - r, y - r, 2 * r, 2 * r, _part_fill(part.get("farbe"), accent,
                                                               colors)))
    elif kind == "mast":
        s.append(_line(x, y, x, y - part["h"], METAL, 0.1))
        s.append(_oval(x - 0.12, y - part["h"] - 0.12, 0.24, 0.24, C["red"]))
    elif kind == "baum":
        s += _map_tree(x, y, part.get("r", 0.4), colors)
    elif kind == "geruest":
        w, h = part["w"], part["h"]
        steps = max(2, int(w / 0.7))
        for number in range(steps + 1):
            left = x + number * w / steps
            s.append(_line(left, y, left, y + h, METAL, 0.05))
        for number in range(int(h / 0.8) + 1):
            s.append(_line(x, y + number * 0.8, x + w, y + number * 0.8, METAL, 0.05))
        s.append(_line(x, y, x + w, y + h, METAL, 0.03))
    return s


def _part_box(part, ox, oy):
    """Umriss eines Teils (x1, y1, x2, y2) in Karteneinheiten."""
    x, y = ox + part.get("x", 0), oy + part.get("y", 0)
    kind = part["art"]
    if kind == "block":
        return x, y - part["h"], x + part["w"] + part["h"] * 0.35, y + part["t"]
    if kind in ("kreis", "baum"):
        r = part.get("r", 0.4)
        return x - r, y - r, x + r, y + r
    if kind == "mast":
        return x - 0.12, y - part["h"] - 0.12, x + 0.12, y
    if kind == "schild":
        return x, y, x + part["w"], y + 0.28
    return x, y, x + part["w"], y + part["h"]


def model_shapes(model_id, ox, oy, accent, state=None, content=None, seed=""):
    """(Zeichenbefehle, Umriss) eines Gebaeudemodells an (ox, oy)."""
    colors = map_palette()
    shapes = []
    box = None
    for part in model_parts(model_id, state, content):
        shapes += model_part_shapes(part, ox, oy, accent, colors, "%s|%s" % (seed, len(shapes)))
        if part["art"] == "baum":
            continue
        x1, y1, x2, y2 = _part_box(part, ox, oy)
        box = (x1, y1, x2, y2) if box is None else (min(box[0], x1), min(box[1], y1),
                                                    max(box[2], x2), max(box[3], y2))
    return shapes, box or (ox, oy, ox + 1, oy + 1)


def place_unlocked(rule, state, content=None):
    """Ist der Ort laut "frei" schon zu sehen? (alle Bedingungen muessen gelten)"""
    content = content or GAME
    need = rule.get("frei") or {}
    day = state.day if state is not None else 1
    if "ab_tag" in need and day < int(need["ab_tag"]):
        return False
    if "kundenort" in need:
        place = customer_place(need["kundenort"], content)
        if place is None or day < int(place.get("ab_tag", 1)):
            return False
    if "aufgabe" in need and (state is None or need["aufgabe"] not in state.solved):
        return False
    if need.get("gruendung_moeglich") and (state is None or not (state.firm or
                                                                  state.founding_ready())):
        return False
    if need.get("gegruendet") and (state is None or not state.firm):
        return False
    if "stufe_min" in need and (state is None or not state.firm or
                                state.firm["stufe"] < int(need["stufe_min"])):
        return False
    if need.get("filiale_moeglich") and not branch_possible(state, content):
        return False
    if need.get("filiale_gebaut") and (state is None or not state.branch):
        return False
    return True


def _place_since(rule, state, content):
    """Arbeitstag, an dem der Ort auf die Karte kam (fuer "Neu"), sonst None."""
    need = rule.get("frei") or {}
    if "kundenort" in need:
        place = customer_place(need["kundenort"], content) or {}
        return int(place.get("ab_tag", 1))
    if "ab_tag" in need:
        return int(need["ab_tag"])
    if (need.get("filiale_gebaut") or need.get("filiale_moeglich")) and state is not None \
            and state.branch:
        return int(state.branch["tag"])
    return None


def map_places(state, content=None):
    """Die sichtbaren Orte mit allem, was Karte und Liste brauchen:
    [{"id", "name", "kurz", "rolle", "farbe", "ansicht", "hinweis", "zahl"
      (offene Tickets/Anfragen), "neu", "text", "x", "y", "schild", "modell",
      "box" (Umriss des Gebaeudes)}]"""
    content = content or GAME
    counts = state.open_count_by_site() if state is not None else {}
    result = []
    for rule in map_rules(content).get("orte") or []:
        if not place_unlocked(rule, state, content):
            continue
        item = {key: rule.get(key) for key in ("id", "name", "kurz", "rolle", "ansicht",
                                               "x", "y", "schild", "modell")}
        item["kurz"] = item["kurz"] or item["name"]
        item["hinweis"] = ""
        founded = state is not None and state.firm
        if founded and rule.get("nach_gruendung"):
            item.update(rule["nach_gruendung"])
        if not founded and rule.get("vor_gruendung"):
            item.update(rule["vor_gruendung"])
        if rule.get("vor_filiale") and not (state is not None and state.branch):
            item.update(rule["vor_filiale"])
        if rule.get("name_firma") and founded:
            item["name"] = state.firm["name"]
        if rule.get("name_filiale"):
            item["name"] = state.branch["name"] if state is not None and state.branch else \
                branch_rules(content).get("name_vorschlag", item["name"])
        item["farbe"] = map_role_color(item["rolle"])
        view = item["ansicht"] or ""
        number = 0
        if state is not None:
            if view == "buero" and founded:
                number = state.firm_open_count() + len(state.open_decisions())
            elif view == "buero":
                number = counts.get(SITE_OFFICE, 0)
            elif view.startswith("kunde:"):
                number = counts.get(view.split(":", 1)[1], 0)
        item["zahl"] = number
        since = _place_since(rule, state, content)
        day = state.day if state is not None else 1
        item["neu"] = since is not None and since > 1 and 0 <= day - since <= MAP_NEW_DAYS
        item["text"] = _place_text(item, rule, state, content)
        _shapes, item["box"] = model_shapes(item["modell"], item["x"], item["y"], item["farbe"],
                                            state, content, item["id"])
        result.append(item)
    return result


def _place_text(item, rule, state, content):
    """Eine Zeile zum Ort fuer die Liste."""
    view = item["ansicht"] or ""
    if view.startswith("kunde:"):
        place = customer_place(view.split(":", 1)[1], content) or {}
        return place.get("text", "")
    if view == "zuhause":
        home = apartment(state.home_id if state is not None else
                         content["wohnungen"]["start"], content) or {}
        return home.get("name", "")
    if view.startswith("mitbewerber:"):
        return "Dein alter Arbeitgeber, jetzt Mitbewerber."
    if rule["id"] == "bitweiche":
        return "Dein Arbeitgeber: Tickets, Kollegen und das Lager."
    if item["hinweis"] and rule.get("vor_filiale") and state is not None and not state.branch:
        return "%s. Eröffnen unter Firma > Gebäude." % item["hinweis"]
    if item["hinweis"]:
        return "%s: Hier kann deine Firma einziehen." % item["hinweis"]
    if view == "filiale" and state is not None and state.branch:
        stage = state.branch_stage() or {}
        return "Filiale · %s · %d Arbeitsplätze" % (stage.get("name", ""),
                                                  state.site_capacity(SITE_BRANCH))
    if view == "buero" and state is not None and state.firm:
        return "%s · %s" % (firm_rules(content)["gebaeude"]["name"],
                            state.firm_stage()["name"])
    return ""


def world_shapes(state, content=None, places=None):
    """Zeichenbefehle fuer die ganze Weltkarte (Landschaft, Gebaeude, Schilder)."""
    content = content or GAME
    places = map_places(state, content) if places is None else places
    colors = map_palette()
    shapes = landscape_shapes(content)
    buildings = []
    for item in (map_rules(content).get("welt") or {}).get("landschaft") or []:
        if item["typ"] == "gebaeude":
            model, box = model_shapes(item["modell"], item["x"], item["y"],
                                      item.get("farbe", "#8B93A1"), state, content,
                                      item["modell"])
            buildings.append((box[3], model))
    for item in places:
        model, _box = model_shapes(item["modell"], item["x"], item["y"], item["farbe"], state,
                                   content, item["id"])
        buildings.append((item["box"][3], model))
    # Von hinten nach vorn: was weiter unten steht, verdeckt das Dahinter
    for _bottom, model in sorted(buildings, key=lambda entry: entry[0]):
        shapes += model
    for item in places:
        cx, cy = item["schild"]
        label = _text(cx, cy, item["name"], "ort", C["text"], anchor="c", maxw=MAP_LABEL_MAXW,
                      kurz=item["kurz"])
        label["bg"] = colors["schild"]
        label["border"] = item["farbe"]
        shapes.append(label)
        if item["hinweis"]:
            shapes.append(_text(cx, cy + 0.62, item["hinweis"], "person", C["yellow"],
                                anchor="c"))
        x1, y1, x2, _y2 = item["box"]
        if item["zahl"]:
            # Als Schild mit Hintergrund: waechst mit der Schrift (auch am Handy lesbar)
            count = _text(x2 - 0.35, y1 + 0.2, str(item["zahl"]), "badge", C["on_accent"],
                          anchor="c")
            count["bg"] = C["pink"]
            shapes.append(count)
        if item["neu"]:
            new = _text(x1 + 0.3, y1 + 0.1, "Neu", "badge", C["card"], anchor="c")
            new["bg"] = C["green"]
            shapes.append(new)
    return shapes


def place_at(x, y, state, content=None, scale=30.0, places=None):
    """Der Ort unter einem Klick/Tipp (Karteneinheiten) oder None. scale
    (Pixel je Einheit) schaetzt die Groesse der Schilder."""
    places = map_places(state, content) if places is None else places
    scale = max(1.0, float(scale))
    for item in reversed(places):
        cx, cy = item["schild"]
        text = item["name"] if len(item["name"]) * MAP_CHAR_PX <= MAP_LABEL_MAXW * scale \
            else item["kurz"]
        half_w = (len(text) * MAP_CHAR_PX + 20) / 2.0 / scale
        half_h = 13.0 / scale
        if abs(x - cx) <= half_w and abs(y - cy) <= half_h:
            return item
    for item in reversed(places):
        x1, y1, x2, y2 = item["box"]
        if x1 - 0.3 <= x <= x2 + 0.3 and y1 - 0.3 <= y <= y2 + 0.3:
            return item
    return None


def place_by_id(place_id, state, content=None):
    return next((item for item in map_places(state, content) if item["id"] == place_id), None)


def place_preview(place_id, state, content=None):
    """Kleines Vorschaubild eines Ortes: (Zeichenbefehle, Breite, Hoehe) in
    Karteneinheiten, mit Rand, links oben bei (0, 0)."""
    content = content or GAME
    rule = next((item for item in map_rules(content).get("orte") or []
                 if item["id"] == place_id), None)
    if rule is None:
        return [], 1, 1
    item = next((entry for entry in map_places(state, content) if entry["id"] == place_id),
                None)
    color = item["farbe"] if item else map_role_color(rule.get("rolle"))
    shapes, box = model_shapes(rule["modell"], 0, 0, color, state, content, place_id)
    # Baeume zaehlen fuer Klicks nicht zum Umriss, im Vorschaubild sollen sie ganz drauf
    for part in model_parts(rule["modell"], state, content):
        if part["art"] == "baum":
            x1, y1, x2, y2 = _part_box(part, 0, 0)
            box = (min(box[0], x1), min(box[1], y1), max(box[2], x2 + 0.1),
                   max(box[3], y2 + 0.12))
    margin = 0.3
    dx, dy = margin - box[0], margin - box[1]
    moved = [_shift_shape(shape, dx, dy) for shape in shapes]
    return moved, box[2] - box[0] + 2 * margin, box[3] - box[1] + 2 * margin


def _shift_shape(shape, dx, dy):
    shape = dict(shape)
    if shape["k"] in ("rect", "oval", "arc", "text"):
        shape["x"] += dx
        shape["y"] += dy
    elif shape["k"] in ("line", "poly"):
        shape["pts"] = [value + (dx if index % 2 == 0 else dy)
                        for index, value in enumerate(shape["pts"])]
    return shape


def site_place_id(site, state=None):
    """Welcher Ort der Karte gehoert zu einer Grossansicht (fuer das Vorschaubild)?"""
    if site == SITE_HOME:
        return "zuhause"
    if site == SITE_BRANCH:
        return "filiale"
    if site == SITE_OFFICE:
        return "gewerbehof" if state is not None and state.firm else "bitweiche"
    return site


def rival_record(state, rival_id):
    """(gewonnen, verloren) aller Angebote, bei denen dieser Mitbewerber der
    guenstigste war."""
    won = lost = 0
    for item in list(state.offers.values()) + list(state.project_offers.values()):
        if (item.get("konkurrent") or BITWEICHE) != rival_id:
            continue
        if item.get("gewonnen"):
            won += 1
        else:
            lost += 1
    return won, lost


def rival_info(state, rival_id, content=None):
    """(Ueberschrift, Text) fuer einen Mitbewerber auf der Karte."""
    rival = competitor(rival_id, content)
    won, lost = rival_record(state, rival_id)
    text = rival.get("text") or ""
    if won or lost:
        text += " Deine Bilanz gegen %s: %d gewonnen, %d verloren." % (rival["kurz"], won,
                                                                        lost)
    else:
        text += " Bisher hast du noch kein Angebot gegen %s abgegeben." % rival["kurz"]
    return rival["name"], text.strip()


def map_list_mode():
    """Liste statt Karte (je Geraet in den Einstellungen gemerkt)?"""
    import fisi_update
    try:
        return bool(fisi_update.load_settings().get(MAP_LIST_SETTING, False))
    except Exception:
        return False


def set_map_list_mode(flag):
    import fisi_update
    try:
        settings = fisi_update.load_settings()
        settings[MAP_LIST_SETTING] = bool(flag)
        return fisi_update.save_settings(settings)
    except Exception:
        return False


def _validate_world(content):
    """orte.json: Landschaft, Orte (Ansicht, Freischaltung, Modell) und Modelle."""
    rules = content.get("orte") or {}
    if not rules:
        return ["Spiel: orte.json fehlt"]
    problems = []
    world = rules.get("welt") or {}
    width, height = world.get("breite", 0), world.get("hoehe", 0)
    if width <= 0 or height <= 0:
        problems.append("Spiel-Karte: Breite/Hoehe fehlt")
    models = rules.get("modelle") or {}
    for item in world.get("landschaft") or []:
        if item.get("typ") not in MAP_LANDSCAPE:
            problems.append("Spiel-Karte: unbekannte Landschaft '%s'" % item.get("typ"))
        if item.get("typ") == "gebaeude" and item.get("modell") not in models:
            problems.append("Spiel-Karte: unbekanntes Modell '%s'" % item.get("modell"))
    places = {item["id"] for item in customer_places(content)}
    tasks = {task["id"] for task in content["aufgaben"]}
    rooms = {item["id"] for item in special_rooms(content)}
    homes = {item["id"] for item in content["wohnungen"]["wohnungen"]}
    seen = set()
    for item in rules.get("orte") or []:
        where = "Spiel-Ort %s" % item.get("id")
        if not item.get("id") or item["id"] in seen:
            problems.append("%s: Kennung fehlt oder doppelt" % where)
        seen.add(item.get("id"))
        if not item.get("name"):
            problems.append("%s: Name fehlt" % where)
        if item.get("modell") not in models:
            problems.append("%s: unbekanntes Modell '%s'" % (where, item.get("modell")))
        if not (0 <= item.get("x", -1) <= width and 0 <= item.get("y", -1) <= height):
            problems.append("%s: liegt ausserhalb der Karte" % where)
        sign = item.get("schild") or []
        if len(sign) != 2 or not (0 <= sign[0] <= width and 0 <= sign[1] <= height):
            problems.append("%s: Schild fehlt oder liegt ausserhalb" % where)
        for variant in [item] + [item[key] for key in ("nach_gruendung", "vor_gruendung",
                                                       "vor_filiale") if key in item]:
            if "rolle" in variant and variant["rolle"] not in MAP_ROLES:
                problems.append("%s: unbekannte Rolle '%s'" % (where, variant["rolle"]))
            view = variant.get("ansicht")
            if view is None and variant is not item:
                continue
            if view not in MAP_VIEWS and not any(str(view).startswith(prefix)
                                                 for prefix in MAP_VIEW_PREFIXES):
                problems.append("%s: unbekannte Ansicht '%s'" % (where, view))
            elif str(view).startswith("kunde:") and view.split(":", 1)[1] not in places:
                problems.append("%s: unbekannter Kundenort in '%s'" % (where, view))
        need = item.get("frei") or {}
        if not need:
            problems.append("%s: Freischaltung ('frei') fehlt" % where)
        for key in need:
            if key not in MAP_UNLOCKS:
                problems.append("%s: unbekannte Freischaltung '%s'" % (where, key))
        if "kundenort" in need and need["kundenort"] not in places:
            problems.append("%s: unbekannter Kundenort '%s'" % (where, need["kundenort"]))
        if "aufgabe" in need and need["aufgabe"] not in tasks:
            problems.append("%s: unbekannte Aufgabe '%s'" % (where, need["aufgabe"]))
    for customer_id in places:
        if not any((item.get("frei") or {}).get("kundenort") == customer_id
                   for item in rules.get("orte") or []):
            problems.append("Spiel-Karte: Kundenort '%s' fehlt auf der Karte" % customer_id)
    for model_id, parts in models.items():
        where = "Spiel-Modell %s" % model_id
        if not parts:
            problems.append("%s: keine Teile" % where)
        for part in parts:
            if part.get("art") not in MAP_PARTS:
                problems.append("%s: unbekanntes Teil '%s'" % (where, part.get("art")))
                continue
            if part["art"] == "block":
                if not all(isinstance(part.get(key), (int, float)) and part[key] > 0
                           for key in ("w", "t", "h")):
                    problems.append("%s: Block ohne Groesse" % where)
                if part.get("dach", "flach") not in MAP_ROOFS:
                    problems.append("%s: unbekanntes Dach '%s'" % (where, part.get("dach")))
            for key in part:
                if key in ("art", "x", "y", "w", "t", "h", "r", "dach", "fenster", "licht",
                           "farbe"):
                    continue
                if key not in MAP_PART_CONDITIONS:
                    problems.append("%s: unbekannte Angabe '%s'" % (where, key))
            if "raum" in part and part["raum"] not in rooms:
                problems.append("%s: unbekannter Sonderraum '%s'" % (where, part["raum"]))
            for home in part.get("wohnung") or []:
                if home not in homes:
                    problems.append("%s: unbekannte Wohnung '%s'" % (where, home))
            for key in ("erledigt", "offen"):
                if key in part and part[key] not in tasks:
                    problems.append("%s: unbekannte Aufgabe '%s'" % (where, part[key]))
    # Jede Wohnung und jede Ausbaustufe braucht ein sichtbares Aussenmodell
    for rule in rules.get("orte") or []:
        if rule.get("ansicht") == "zuhause":
            for home in homes:
                ctx = dict(_map_context(None, content), wohnung=home)
                if not any(part["art"] == "block" and _part_visible(part, ctx)
                           for part in models.get(rule.get("modell"), [])):
                    problems.append("Spiel-Karte: kein Gebaeude fuer Wohnung '%s'" % home)
    return problems
