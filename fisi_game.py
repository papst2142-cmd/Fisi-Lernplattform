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
Geld, Reputation, Rang und der aktuelle Arbeitstag werden immer daraus
berechnet. Nur so laesst sich der Stand von PC und Handy beim Abgleich
einfach vereinigen, ohne dass Zahlen doppelt zaehlen.

Die Inhalte (Aufgaben, Kollegen, Raeume, Story, Stellschrauben) liegen als
JSON in inhalte/spiel/.
"""

import json
import os

from fisi_core import (
    CATEGORY_KEYS, CATEGORY_SHORT, CONTENT_DIR, search_content,
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
TASK_TYPES = ("auswahl", "zuordnung")

# Ereignistypen im Protokoll
EV_PROFILE = "profil_gesetzt"
EV_SOLVED = "ticket_erledigt"
EV_DEFERRED = "ticket_verschoben"
EV_DAY_END = "tag_beendet"

# Status eines Tickets am aktuellen Arbeitstag
ST_OPEN = "offen"
ST_RIGHT = "richtig"
ST_WRONG = "falsch"
ST_DEFERRED = "verschoben"

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

    tasks = read("aufgaben")
    for task in tasks:
        for field in ("ticket", "hilfe", "erklaerung"):
            task[field] = _lines(task.get(field))
    building = read("gebaeude")
    story = read("story")
    return {
        "aufgaben": tasks,
        "kollegen": read("kollegen"),
        "gebaeude": building,
        "story": {key: _lines(value) for key, value in story.items()},
        "balancing": read("balancing"),
    }


GAME = load_game_content()


def task_by_id(task_id, content=None):
    for task in (content or GAME)["aufgaben"]:
        if task["id"] == task_id:
            return task
    return None


def colleague(colleague_id, content=None):
    for person in (content or GAME)["kollegen"]:
        if person["id"] == colleague_id:
            return person
    return None


def room(room_id, content=None):
    for item in (content or GAME)["gebaeude"]["raeume"]:
        if item["id"] == room_id:
            return item
    return None


def validate_game_content(content=None):
    """Prueft die Spielinhalte auf formale Fehler. Leere Liste = in Ordnung.
    Wird von fisi_core.validate_content() mit aufgerufen."""
    content = content or GAME
    problems = []
    rooms = {item["id"] for item in content["gebaeude"]["raeume"]}
    people = {item["id"] for item in content["kollegen"]}
    balancing = content["balancing"]

    for item in content["gebaeude"]["raeume"]:
        where = "Spiel-Raum %s" % item.get("id")
        if item.get("cat") not in CATEGORY_KEYS:
            problems.append("%s: unbekannter Fachbereich '%s'" % (where, item.get("cat")))
        if item["x"] < 0 or item["y"] < 0 or \
                item["x"] + item["w"] > content["gebaeude"]["breite"] or \
                item["y"] + item["h"] > content["gebaeude"]["hoehe"]:
            problems.append("%s: liegt ausserhalb des Grundrisses" % where)
        door = item.get("tuer")
        if door and not item["x"] <= door["von"] < door["bis"] <= item["x"] + item["w"]:
            problems.append("%s: Tuer liegt nicht an der Raumwand" % where)
        for deco in item.get("deko", []):
            if deco.get("typ") not in DECO_TYPES:
                problems.append("%s: unbekannte Einrichtung '%s'" % (where, deco.get("typ")))
            elif not _inside(deco, item):
                problems.append("%s: Einrichtung '%s' ragt aus dem Raum" % (where, deco["typ"]))
    hall = content["gebaeude"].get("flur", {})
    hall_area = {"x": 0, "y": hall.get("y", 0), "w": content["gebaeude"]["breite"],
                 "h": hall.get("h", 0)}
    for deco in hall.get("deko", []):
        if deco.get("typ") not in DECO_TYPES or not _inside(deco, hall_area):
            problems.append("Spiel-Flur: Einrichtung '%s' unbekannt oder ausserhalb"
                            % deco.get("typ"))
    for person in content["kollegen"]:
        where = "Spiel-Kollege %s" % person.get("id")
        if person.get("raum") not in rooms:
            problems.append("%s: unbekannter Raum '%s'" % (where, person.get("raum")))
        elif person.get("platz"):
            x, y = person["platz"]
            if room_at(x, y, content) is not room(person["raum"], content):
                problems.append("%s: Sitzplatz liegt nicht im eigenen Raum" % where)

    for rank in balancing["raenge"]:
        if rank["name"] not in balancing["gehalt_pro_tag"]:
            problems.append("Spiel-Balancing: kein Gehalt fuer Rang '%s'" % rank["name"])

    seen = set()
    for number, task in enumerate(content["aufgaben"], start=1):
        where = "Spiel-Aufgabe Nr. %d (%s)" % (number, task.get("id"))
        for field in ("id", "typ", "titel", "auftraggeber", "raum", "prioritaet",
                      "cat", "ticket", "frage", "hilfe", "erklaerung",
                      "suchbegriffe", "belohnung"):
            if not task.get(field):
                problems.append("%s: Feld '%s' fehlt oder ist leer" % (where, field))
        if task.get("id") in seen:
            problems.append("%s: Kennung doppelt vorhanden" % where)
        seen.add(task.get("id"))
        if task.get("typ") not in TASK_TYPES:
            problems.append("%s: unbekannter Typ '%s'" % (where, task.get("typ")))
        if task.get("raum") not in rooms:
            problems.append("%s: unbekannter Raum '%s'" % (where, task.get("raum")))
        if task.get("auftraggeber") not in people:
            problems.append("%s: unbekannter Auftraggeber '%s'"
                            % (where, task.get("auftraggeber")))
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

def learn_links_for_term(term, limit=6):
    hits = [hit for hit in search_content(term)
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
#  AUFGABEN PRUEFEN
# ============================================================================

def check_answer(task, answer):
    """Prueft eine Antwort. Rueckgabe: (richtig, anzahl_fehler).

    auswahl:   answer ist der gewaehlte Antworttext
    zuordnung: answer ist {links: rechts}
    """
    if task["typ"] == "auswahl":
        right = answer == task["antwort"]
        return right, 0 if right else 1
    if task["typ"] == "zuordnung":
        answer = answer or {}
        errors = sum(1 for left, right in task["paare"] if answer.get(left) != right)
        return errors == 0, errors
    raise ValueError("Unbekannter Aufgabentyp: %s" % task["typ"])


def _scaled(value, factor):
    return int(round(value * factor))


def evaluate(task, answer, used_help, levels, day, balancing=None):
    """Bewertet eine bearbeitete Aufgabe und liefert die Nutzdaten fuer das
    Ereignis ticket_erledigt (Geld und Reputationsaenderung werden mit
    gespeichert, damit spaetere Balancing-Aenderungen den Stand nicht
    rueckwirkend verschieben)."""
    balancing = balancing or GAME["balancing"]
    right, errors = check_answer(task, answer)
    gaps = requirement_gaps(task, levels)
    below = bool(gaps)
    axes = ["fachkompetenz"] + [a for a in task.get("achsen") or [] if a != "fachkompetenz"]
    reward = task["belohnung"]
    delta = {key: 0 for key in AXIS_KEYS}
    delta["zuverlaessigkeit"] += balancing["zuverlaessigkeit_pro_ticket"]

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

    return {
        "aufgabe": task["id"],
        "tag": day,
        "richtig": right,
        "fehler": errors,
        "hilfe": bool(used_help),
        "unter_niveau": below,
        "geld": money,
        "reputation": {key: value for key, value in delta.items() if value},
    }


def defer_payload(task, day, balancing=None):
    balancing = balancing or GAME["balancing"]
    factor = balancing["prioritaet_faktor"].get(task["prioritaet"], 1)
    loss = _scaled(balancing["verschieben_verlust"], factor)
    return {"aufgabe": task["id"], "tag": day,
            "reputation": {"zuverlaessigkeit": -loss}}


# ============================================================================
#  SPIELSTAND AUS DEN EREIGNISSEN
# ============================================================================

def rank_for(value, balancing=None):
    balancing = balancing or GAME["balancing"]
    name = balancing["raenge"][0]["name"]
    for rank in balancing["raenge"]:
        if value >= rank["ab"]:
            name = rank["name"]
    return name


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

        for timestamp, kind, data in events:
            self.history.append((timestamp, kind, data))
            if kind == EV_PROFILE:
                # Der juengste Eintrag gewinnt (Ereignisse sind sortiert)
                self.profile = {"name": data.get("name", ""),
                                "aussehen": normalize_appearance(data.get("aussehen"))}
            elif kind in (EV_SOLVED, EV_DEFERRED):
                self._apply_reputation(data.get("reputation") or {})
                self.money += int(data.get("geld", 0))
                if kind == EV_SOLVED:
                    self.tickets_done += 1
                    if data.get("richtig"):
                        self.solved.add(data.get("aufgabe"))
            elif kind == EV_DAY_END:
                self.days_done += 1
                self.money += int(data.get("gehalt", 0))

        # Tickets des laufenden Tages (Tag steht in den Nutzdaten)
        for _timestamp, kind, data in self.history:
            if kind in (EV_SOLVED, EV_DEFERRED) and data.get("tag") == self.day:
                if kind == EV_DEFERRED:
                    status = ST_DEFERRED
                else:
                    status = ST_RIGHT if data.get("richtig") else ST_WRONG
                self.handled[data.get("aufgabe")] = status

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
        return rank_for(self.mean_reputation, self.content["balancing"])

    @property
    def salary(self):
        return self.content["balancing"]["gehalt_pro_tag"].get(self.rank, 0)

    def founding_progress(self):
        """Fortschritt zum eigenen Unternehmen (0.0 bis 1.0) - Kapital und
        Mindest-Reputation muessen beide erreicht sein."""
        goal = self.content["balancing"]["gruendung"]
        capital = min(1.0, max(0, self.money) / float(goal["startkapital"]))
        reputation = min(1.0, self.mean_reputation / float(goal["mindest_reputation"]))
        return min(capital, reputation)

    # -- Tickets ------------------------------------------------------------

    def _pool(self):
        return [task for task in self.content["aufgaben"]
                if task.get("ab_tag", 1) <= self.day
                and task["id"] not in self.solved
                and task["id"] not in self.handled]

    def open_tickets(self):
        per_day = self.content["balancing"]["tickets_pro_tag"]
        return self._pool()[:max(0, per_day - len(self.handled))]

    def todays_tickets(self):
        """Tickets des aktuellen Arbeitstags: [(aufgabe, status)]."""
        result = [(task_by_id(task_id, self.content), status)
                  for task_id, status in self.handled.items()]
        result = [(task, status) for task, status in result if task]
        result += [(task, ST_OPEN) for task in self.open_tickets()]
        return result

    def tickets_in_room(self, room_id):
        return [(task, status) for task, status in self.todays_tickets()
                if task["raum"] == room_id]

    def quests(self):
        """Offene Tickets je Auftraggeber: {kollegen_id: [aufgabe, ...]}."""
        result = {}
        for task in self.open_tickets():
            result.setdefault(task["auftraggeber"], []).append(task)
        return result

    def open_count_by_room(self):
        counts = {}
        for task in self.open_tickets():
            counts[task["raum"]] = counts.get(task["raum"], 0) + 1
        return counts

    def can_end_day(self):
        return bool(self.handled) and not self.open_tickets()

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
        task = task_by_id(task_id, self.content)
        if task is None or not self.state.is_open(task_id):
            raise ValueError("Dieses Ticket ist heute nicht (mehr) offen.")
        payload = evaluate(task, answer, used_help, self.knowledge(), self.state.day,
                           self.content["balancing"])
        self._log(EV_SOLVED, payload)
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
        self._log(EV_DAY_END, payload)
        return payload

    def reset(self):
        ok = self.db.reset_game()
        self.reload()
        return ok


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
              "wasserspender", "feuerloescher", "teppich", "fussmatte", "bank")


def _inside(deco, area):
    return area["x"] <= deco["x"] and deco["x"] + deco["w"] <= area["x"] + area["w"] and \
        area["y"] <= deco["y"] and deco["y"] + deco["h"] <= area["y"] + area["h"]


def _deco(item):
    """Ein Einrichtungsgegenstand als Zeichenbefehle."""
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
    s += _floor(0, hall["y"], width, hall["h"], "flur", mix(C["card_alt"], "#FFFFFF", 0.05))
    for item in building["raeume"]:
        color = mix(C["card_alt"], CATEGORY_COLOR[CAT_NAME[item["cat"]]], 0.13)
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

    # Tueren: Oeffnung in der Wand, Tuerblatt und Schwenkbogen zum Flur hin
    floor_hall = mix(C["card_alt"], "#FFFFFF", 0.05)
    for item in building["raeume"]:
        door = item.get("tuer")
        if not door:
            continue
        top_row = item["y"] + item["h"] <= hall["y"]
        wall_y = item["y"] + item["h"] if top_row else item["y"]
        span = door["bis"] - door["von"]
        s.append(_rect(door["von"], wall_y - 0.16, span, 0.32, floor_hall))
        swing = span if top_row else -span
        hinge = door["von"]
        s.append(_line(hinge, wall_y, hinge, wall_y + swing * 0.9, WALL_OUTER, 0.07))
        s.append({"k": "arc", "x": hinge - span, "y": wall_y - span, "w": span * 2,
                  "h": span * 2, "start": 0 if top_row else -90, "extent": 90,
                  "color": mix(WALL, C["card_alt"], 0.45), "lw": 0.03})
    entrance = hall["eingang"]
    s.append(_rect(-0.2, entrance["von"], 0.4, entrance["bis"] - entrance["von"], floor_hall))
    s.append(_line(0, entrance["von"], 0, entrance["bis"], mix(WINDOW, C["card"], 0.3), 0.06))

    if rotate:
        s = [_rotate_shape(shape, height) for shape in s]

    # Ab hier in Zeichnungs-Koordinaten, damit Schrift nie mitgedreht wird.
    # Beschriftung, Auswahl und Ticket-Plaketten zuletzt, damit sie oben liegen
    for item in building["raeume"]:
        x, y, w, h = _view_rect(item, rotate, content)
        color = CATEGORY_COLOR[CAT_NAME[item["cat"]]]
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
        s.append(_text(px_, py_ + 0.62, person["name"].split()[0], "person",
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
WALK_FREE = ("teppich", "fussmatte", "whiteboard")   # darueber laeuft man
_GRID_CACHE = {}


def _segments(content):
    """Wandstuecke als Rechtecke (x1, y1, x2, y2) - Tueroeffnungen ausgespart."""
    building = content["gebaeude"]
    hall = building["flur"]
    width, height = building["breite"], building["hoehe"]
    half = WALL_INNER / 2.0
    walls = []

    def horizontal(x1, x2, y, gap=None):
        if gap:
            walls.append((x1, y - half, gap[0], y + half))
            walls.append((gap[1], y - half, x2, y + half))
        else:
            walls.append((x1, y - half, x2, y + half))

    for item in building["raeume"]:
        x, y, w, h = item["x"], item["y"], item["w"], item["h"]
        door = item.get("tuer")
        gap = (door["von"], door["bis"]) if door else None
        top_row = y + h <= hall["y"]
        horizontal(x, x + w, y, None if top_row else gap)
        horizontal(x, x + w, y + h, gap if top_row else None)
        walls.append((x - half, y, x + half, y + h))
        walls.append((x + w - half, y, x + w + half, y + h))
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


def _walk_grid(content=None):
    """Begehbare Rasterzellen als Menge von (spalte, zeile)."""
    content = content or GAME
    key = id(content)
    if key in _GRID_CACHE:
        return _GRID_CACHE[key]
    building = content["gebaeude"]
    cols = int(building["breite"] / WALK_STEP)
    rows = int(building["hoehe"] / WALK_STEP)
    rects = _obstacles(content)
    people = [p["platz"] for p in content["kollegen"] if p.get("platz")]
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
                for px_, py_ in people:
                    if (px_ - cx) ** 2 + (py_ - cy) ** 2 < PERSON_RADIUS ** 2:
                        blocked = True
                        break
            if not blocked:
                free.add((col, row))
    _GRID_CACHE[key] = free
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


def office_message(position, person, quests, content=None):
    """Text unter der Grossansicht: (Ueberschrift, Text) je nach Standort."""
    if person:
        first = person["name"].split()[0]
        tasks = quests.get(person["id"]) or []
        if tasks:
            more = " (und %d weitere)" % (len(tasks) - 1) if len(tasks) > 1 else ""
            return ("%s hat einen Auftrag für dich" % first,
                    "„%s“ · Priorität %s%s" % (tasks[0]["titel"], tasks[0]["prioritaet"],
                                               more))
        return ("%s · %s" % (person["name"], person["rolle"]),
                "Gerade nichts für dich. %s" % person.get("macke", ""))
    item = room_at(position[0], position[1], content)
    waiting = sum(len(tasks) for tasks in quests.values())
    where = "Du bist im Raum %s." % item["name"] if item else "Du bist im Flur."
    if waiting:
        hint = "%d Auftrag wartet." % waiting if waiting == 1 else \
            "%d Aufträge warten." % waiting
        return (where, hint + " Wer einen hat, trägt ein grünes „!“.")
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


def result_text(task, payload):
    """Rueckmeldung nach dem Bearbeiten eines Tickets."""
    lines = []
    if payload["richtig"]:
        lines.append("Richtig gelöst!")
    elif task["typ"] == "zuordnung":
        lines.append("Leider nicht ganz: %d Zuordnung(en) stimmen nicht."
                     % payload["fehler"])
    else:
        lines.append("Leider falsch. Richtig wäre: %s" % task["antwort"])
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
