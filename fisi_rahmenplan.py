#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FISI Lernplattform - Ausbildungsrahmenplan (ab 0.55, ohne Oberflaeche)
======================================================================

Gemeinsam fuer PC und Handy:
  * Rahmenplan und Lernfelder als Daten (inhalte/rahmenplan.json)
  * Zuordnung Lerninhalt -> Rahmenplan-Punkt (inhalte/rahmenplan_zuordnung.json)
  * "Rahmenplan-Abdeckung" im Fortschritt: Wissensstand je Punkt, Position,
    Abschnitt und Lernfeld - berechnet wie der Wissensstand je Thema, nur auf
    die Inhalte des Punktes bezogen
  * Gewichtung der Reihenfolge NEUER Inhalte beim normalen Weiterlernen

Alles wird aus den Antworten berechnet, die ohnehin gespeichert und
abgeglichen werden. Abgleich-Format, Ereignisprotokoll, Wiederholungstermine
und Spielstaende bleiben unberuehrt. Die Schalter liegen je Geraet in
einstellungen.json (wie Farben und Tagesziel).
"""

import datetime
import hashlib
import json
import math
import os
import re
import threading

from fisi_core import (CONTENT_DIR, KARTEIKARTEN, QUIZ_QUESTIONS, SRC_CARD, SRC_QUIZ,
                       TOPIC_NAME, TOPIC_ORDER, plural)


# ============================================================================
#  DATEN
# ============================================================================

def _load(name):
    with open(os.path.join(CONTENT_DIR, name + ".json"), encoding="utf-8") as handle:
        return json.load(handle)


_RP = _load("rahmenplan")
_ZU = _load("rahmenplan_zuordnung")

SECTIONS = [entry["id"] for entry in _RP["abschnitte"]]
SECTION_TITLE = {entry["id"]: entry["titel"] for entry in _RP["abschnitte"]}
# B, D und E gehoeren zu anderen Fachrichtungen: in den Optionen schaltbar
OPTIONAL_SECTIONS = [entry["id"] for entry in _RP["abschnitte"] if entry["optional"]]

POINTS = _RP["punkte"]
POINT = {point["id"]: point for point in POINTS}
POINT_IDS = [point["id"] for point in POINTS]

# (Abschnitt, Nr.) -> Titel der Position, in Reihenfolge des Rahmenplans
POSITIONS = {}
for _point in POINTS:
    POSITIONS.setdefault((_point["abschnitt"], _point["nr"]), _point["position"])

LEARNING_FIELDS = _RP["lernfelder"]
LEARNING_FIELD = {entry["id"]: entry for entry in LEARNING_FIELDS}
LF_IDS = [entry["id"] for entry in LEARNING_FIELDS]

MATCH_RULES = [(entry["id"], entry["themen"], entry["stichworte"]) for entry in _ZU["punkte"]]
DEFAULT_POINT = dict(_ZU["standard_punkt"])
TOPIC_FIELDS = {topic: list(fields) for topic, fields in _ZU["themen_lernfelder"].items()}


def validate_rahmenplan():
    """Formale Pruefung der Rahmenplan-Daten (wird von validate_content
    aufgerufen). Liefert eine Liste von Meldungen."""
    problems = []
    seen = set()
    for point in POINTS:
        if point["id"] in seen:
            problems.append("Rahmenplan: Punkt %s doppelt" % point["id"])
        seen.add(point["id"])
        if point["abschnitt"] not in SECTIONS:
            problems.append("Rahmenplan %s: unbekannter Abschnitt" % point["id"])
        for field in point["lernfelder"]:
            if field not in LEARNING_FIELD:
                problems.append("Rahmenplan %s: unbekanntes Lernfeld %s" % (point["id"], field))
        for area in point["ap2"]:
            if area not in AP2_AREAS:
                problems.append("Rahmenplan %s: unbekannter Prüfungsbereich %s"
                                % (point["id"], area))
    for point_id, topics, pattern in MATCH_RULES:
        if point_id not in POINT:
            problems.append("Rahmenplan-Zuordnung: unbekannter Punkt %s" % point_id)
        for topic in topics or ():
            if topic not in TOPIC_NAME:
                problems.append("Rahmenplan-Zuordnung %s: unbekanntes Thema %s"
                                % (point_id, topic))
        try:
            re.compile(pattern)
        except re.error as exc:
            problems.append("Rahmenplan-Zuordnung %s: Stichworte fehlerhaft (%s)"
                            % (point_id, exc))
    for topic in TOPIC_ORDER:
        if DEFAULT_POINT.get(topic) not in POINT:
            problems.append("Rahmenplan-Zuordnung: Standard-Punkt fuer Thema %s fehlt" % topic)
        for field in TOPIC_FIELDS.get(topic, ()):
            if field not in LEARNING_FIELD:
                problems.append("Rahmenplan-Zuordnung: Thema %s mit unbekanntem Lernfeld %s"
                                % (topic, field))
    for label, items in (("Karteikarte", KARTEIKARTEN), ("Quizfrage", QUIZ_QUESTIONS)):
        for number, item in enumerate(items, start=1):
            for point_id in item.get("rahmenplan") or ():
                if point_id not in POINT:
                    problems.append("%s Nr. %d: unbekannter Rahmenplan-Punkt %s"
                                    % (label, number, point_id))
    return problems


# ============================================================================
#  ZUORDNUNG INHALT -> PUNKT
# ============================================================================
#
# Ein Inhalt gehoert zu einem Punkt, wenn sein Thema zum Punkt passt und ein
# Stichwort in Frage, Antwort oder Erklaerung vorkommt. Trifft nichts, zaehlt
# er beim Standard-Punkt seines Themas. Neue Inhalte ab 0.55 tragen ihre
# Punkte direkt im Feld "rahmenplan". Einmal berechnet und gehalten.

_ITEM_POINTS = {}
_LOCK = threading.Lock()


def _item_text(item, fields):
    parts = []
    for field in fields:
        value = item.get(field)
        if isinstance(value, str):
            parts.append(value)
    return " ".join(parts).lower()


def item_points():
    """{(quelle, frage): [Punkt-Kennungen]} fuer alle Karteikarten und
    Quizfragen."""
    with _LOCK:     # warm_up rechnet evtl. gerade im Hintergrund
        if not _ITEM_POINTS:
            _ITEM_POINTS.update(_compute_item_points())
    return _ITEM_POINTS


def _compute_item_points():
    rules = [(point_id, set(topics) if topics else None, re.compile(pattern))
             for point_id, topics, pattern in MATCH_RULES]
    result = {}
    for source, items, fields in ((SRC_CARD, KARTEIKARTEN, ("q", "a", "a_full")),
                                  (SRC_QUIZ, QUIZ_QUESTIONS, ("q", "a", "exp"))):
        for item in items:
            own = item.get("rahmenplan")
            if own:
                result[(source, item["q"])] = list(own)
                continue
            topic = item.get("thema")
            text = _item_text(item, fields)
            hits = [point_id for point_id, topics, pattern in rules
                    if (topics is None or topic in topics) and pattern.search(text)]
            if not hits and topic in DEFAULT_POINT:
                hits = [DEFAULT_POINT[topic]]
            result[(source, item["q"])] = hits
    return result


_POINT_ITEMS = {}


def point_items():
    """{punkt: {quelle: [fragen]}} - Umkehrung von item_points."""
    if _POINT_ITEMS:
        return _POINT_ITEMS
    result = {point_id: {SRC_QUIZ: [], SRC_CARD: []} for point_id in POINT_IDS}
    for (source, key), points in item_points().items():
        for point_id in points:
            if point_id in result:
                result[point_id][source].append(key)
    _POINT_ITEMS.update(result)
    return _POINT_ITEMS


def warm_up():
    """Zuordnung im Hintergrund vorberechnen (beim Programmstart), damit der
    erste Aufruf von Fortschritt, Karteikarten und Pruefungstrainer nicht
    wartet. Fehler hier sind egal: dann wird beim ersten Aufruf gerechnet."""
    def run():
        try:
            point_items()
        except Exception:
            pass
    thread = threading.Thread(target=run, name="rahmenplan", daemon=True)
    thread.start()
    return thread


def topic_items(topic):
    """{quelle: [fragen]} eines Lernthemas."""
    return {SRC_QUIZ: [q["q"] for q in QUIZ_QUESTIONS if q.get("thema") == topic],
            SRC_CARD: [c["q"] for c in KARTEIKARTEN if c.get("thema") == topic]}


# ============================================================================
#  EINSTELLUNGEN (JE GERAET)
# ============================================================================

AP1_DATE_DEFAULT = "2027-09-29"
AP2_DATE_DEFAULT = "2028-04-26"

RP_SETTINGS = {
    "rp_abschnitt_b": False,
    "rp_abschnitt_d": False,
    "rp_abschnitt_e": False,
    "rp_gewichtung": True,
    "rp_lernfeld": "",
    "rp_termin_ap1": AP1_DATE_DEFAULT,
    "rp_termin_ap2": AP2_DATE_DEFAULT,
}
SECTION_SETTING = {"B": "rp_abschnitt_b", "D": "rp_abschnitt_d", "E": "rp_abschnitt_e"}


def parse_date(text):
    """Datum aus "TT.MM.JJJJ" oder "JJJJ-MM-TT", sonst None."""
    text = str(text or "").strip()
    for pattern in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(text, pattern).date()
        except ValueError:
            pass
    return None


def date_text(value):
    """Anzeige "TT.MM.JJJJ" (leer ohne gueltiges Datum)."""
    day = parse_date(value) if not isinstance(value, datetime.date) else value
    return day.strftime("%d.%m.%Y") if day else ""


def rp_settings(settings):
    """Rahmenplan-Einstellungen mit Standardwerten."""
    values = dict(RP_SETTINGS)
    for key in RP_SETTINGS:
        if key in settings:
            values[key] = settings[key]
    for key in ("rp_abschnitt_b", "rp_abschnitt_d", "rp_abschnitt_e", "rp_gewichtung"):
        values[key] = bool(values[key])
    if values["rp_lernfeld"] not in LEARNING_FIELD:
        values["rp_lernfeld"] = ""
    for key in ("rp_termin_ap1", "rp_termin_ap2"):
        day = parse_date(values[key])
        values[key] = day.isoformat() if day else ""
    return values


def load_rp_settings():
    from fisi_update import load_settings
    return rp_settings(load_settings())


def save_rp_settings(**values):
    """Speichert Rahmenplan-Einstellungen (nur die bekannten Schluessel)."""
    from fisi_update import load_settings, save_settings
    settings = load_settings()
    settings.update({key: value for key, value in values.items() if key in RP_SETTINGS})
    return save_settings(settings)


def enabled_sections(values):
    """Sichtbare Abschnitte: A, C, F immer, B/D/E nach Einstellung."""
    return [section for section in SECTIONS
            if section not in SECTION_SETTING or values.get(SECTION_SETTING[section])]


def visible_fields(values):
    """Lernfelder der Ansicht: LF 10a-12a nur mit Abschnitt B."""
    sections = enabled_sections(values)
    return [entry["id"] for entry in LEARNING_FIELDS
            if not entry["abschnitt"] or entry["abschnitt"] in sections]


# ============================================================================
#  RAHMENPLAN-ABDECKUNG (FORTSCHRITT)
# ============================================================================

COVERAGE_TITLE = "Rahmenplan-Abdeckung"
COVERAGE_SUBTITLE = "Wissensstand je Punkt"
VIEW_PLAN = "rahmenplan"
VIEW_FIELDS = "lernfeld"
COVERAGE_VIEWS = [(VIEW_PLAN, "Rahmenplan"), (VIEW_FIELDS, "Lernfeld")]
FILTER_ALL = "Alle"
FILTER_AP1 = "AP1"
AP2_AREAS = ["Konzeption", "Netzwerke", "Projekt", "WiSo"]
COVERAGE_FILTERS = [(FILTER_ALL, "Alle"), (FILTER_AP1, "AP1")] + \
    [(area, area) for area in AP2_AREAS]
NO_CONTENT = "kein Lerninhalt vorhanden"
NO_ANSWERS = "Noch keine Antworten. Starte mit Karteikarten oder dem Prüfungstrainer."
CURRENT_FIELD_TEXT = "Dein aktuelles Lernfeld"
FILTER_EMPTY = "Zu diesem Filter gibt es in den eingeschalteten Abschnitten keine Punkte."

# Ampel (Nicos Plan 0.55): unter 50 % rot, 50-79 % orange, ab 80 % gruen.
# Die Farben kommen aus fisi_theme.C ("red", "orange", "green"), Kontrast
# in Hell und Dunkel geprueft (test_spiel).
LEVEL_LOW, LEVEL_MID, LEVEL_HIGH = "rot", "orange", "gruen"
LEVEL_COLOR_KEY = {LEVEL_LOW: "red", LEVEL_MID: "orange", LEVEL_HIGH: "green"}


def level(value):
    if value < 50:
        return LEVEL_LOW
    if value < 80:
        return LEVEL_MID
    return LEVEL_HIGH


def percent_text(value):
    return ("%d %%" % int(round(value))) if value is not None else "–"


def matches_filter(point, name):
    if name in (None, FILTER_ALL):
        return True
    if name == FILTER_AP1:
        return bool(point["ap1"])
    return name in point["ap2"]


def _point_weight(point):
    # Punkte ohne Zeitrichtwert (F1-F4: ganze Ausbildung) zaehlen wie 1 Woche
    return point["wochen_punkt"] or 1.0


def _weighted_mean(pairs):
    pairs = [(value, weight) for value, weight in pairs if value is not None]
    total = sum(weight for _value, weight in pairs)
    if not total:
        return None
    return sum(value * weight for value, weight in pairs) / total


def coverage_key(db, values):
    """Schluessel, an dem PC und Handy erkennen, ob die Abdeckung neu
    berechnet werden muss: Stempel der Antwort-Tabellen (Spielereignisse
    aendern nichts daran) und die Rahmenplan-Einstellungen. None = immer
    neu rechnen."""
    try:
        stamp = db.change_stamp(db.ANSWER_TABLES)
    except (AttributeError, TypeError):
        return None
    if stamp is None:
        return None
    return stamp, tuple(sorted(values.items()))


class Coverage:
    """Wissensstand je Rahmenplan-Punkt, einmal aus dem StatusBook berechnet.
    Wert eines Punktes: knowledge_from_answers mit den Parametern fuer den
    Wissensstand je Thema, bezogen auf die Inhalte des Punktes. None = kein
    Lerninhalt vorhanden."""

    def __init__(self, book, values=None, params=None):
        from fisi_game import knowledge_from_answers, topic_params
        self.book = book
        self.values = values if values is not None else dict(RP_SETTINGS)
        self.params = params or topic_params()
        self._formula = knowledge_from_answers
        self.items = point_items()
        self.point = {point_id: self.group_value(self.items[point_id])
                      for point_id in POINT_IDS}
        self.any_answers = any(book.touched(source, key)
                               for (source, key) in item_points())

    def group_value(self, keys_by_source):
        """Wissensstand 0-100 einer Gruppe von Inhalten, None ohne Inhalte."""
        total = sum(len(keys) for keys in keys_by_source.values())
        if not total:
            return None
        window = max(1, int(self.params["letzte_antworten"]))
        entries, touched = [], 0
        for source, keys in keys_by_source.items():
            for key in keys:
                results = self.book.results.get((source, key))
                if not results:
                    continue
                touched += 1
                entries.extend((timestamp, value) for timestamp, value in results
                               if value is not None)
        entries.sort(key=lambda item: item[0], reverse=True)
        answers = [value for _timestamp, value in entries[:window]]
        share = touched / float(total) * 100.0
        return self._formula({"x": answers}, {"x": share}, self.params, keys=["x"])["x"]

    def point_count(self, point_id):
        return sum(len(keys) for keys in self.items[point_id].values())

    def sections(self, filter_name=FILTER_ALL):
        """Baum fuer die Ansicht Rahmenplan: Liste von
        {"id", "titel", "wert", "positionen": [{"id", "titel", "wert",
        "punkte": [{"id", "text", "wert", "anzahl"}]}]}. Werte None = kein
        Lerninhalt."""
        tree = []
        for section in enabled_sections(self.values):
            positions = []
            for (sec, number), title in POSITIONS.items():
                if sec != section:
                    continue
                points = [point for point in POINTS
                          if point["abschnitt"] == sec and point["nr"] == number
                          and matches_filter(point, filter_name)]
                if not points:
                    continue
                rows = [{"id": point["id"], "text": point["text"],
                         "wert": self.point[point["id"]],
                         "anzahl": self.point_count(point["id"])} for point in points]
                value = _weighted_mean([(self.point[point["id"]], _point_weight(point))
                                        for point in points])
                positions.append({"id": "%s%d" % (sec, number), "titel": title,
                                  "wert": value, "punkte": rows})
            if not positions:
                continue
            value = _weighted_mean([(self.point[row["id"]], _point_weight(POINT[row["id"]]))
                                    for position in positions for row in position["punkte"]])
            tree.append({"id": section, "titel": SECTION_TITLE[section], "wert": value,
                         "positionen": positions})
        return tree

    def fields(self):
        """Baum fuer die Ansicht Lernfeld: Liste von {"jahr", "felder":
        [{"id", "titel", "stunden", "wert", "aktuell", "themen": [{"id",
        "titel", "wert", "anzahl"}]}]}. Das aktuelle Lernfeld (Optionen)
        steht oben in seinem Jahr."""
        current = self.values.get("rp_lernfeld") or ""
        years = {}
        for field_id in visible_fields(self.values):
            entry = LEARNING_FIELD[field_id]
            topics = [topic for topic in TOPIC_ORDER if field_id in TOPIC_FIELDS.get(topic, ())]
            rows = []
            for topic in topics:
                keys = topic_items(topic)
                count = sum(len(value) for value in keys.values())
                rows.append({"id": topic, "titel": TOPIC_NAME[topic],
                             "wert": self.group_value(keys), "anzahl": count})
            value = _weighted_mean([(row["wert"], row["anzahl"]) for row in rows])
            years.setdefault(entry["jahr"], []).append({
                "id": field_id, "titel": entry["titel"], "stunden": entry["stunden"],
                "wert": value, "aktuell": field_id == current, "themen": rows})
        result = []
        for year in sorted(years):
            fields = sorted(years[year], key=lambda item: not item["aktuell"])
            result.append({"jahr": year, "felder": fields})
        return result


def point_label(point_id):
    """"C3e Konzepte zur Datensicherung ..." fuer eine Zeile."""
    return "%s %s" % (point_id, POINT[point_id]["text"])


def section_label(section):
    return "%s %s" % (section, SECTION_TITLE[section])


def year_label(year):
    return "%d. Ausbildungsjahr" % year


def field_label(entry):
    return "%s %s" % (entry["id"], entry["titel"])


def count_text(count):
    return plural(count, "Inhalt", "Inhalte")


def point_practice_parts(book, point_id, size=None, rng=None):
    """Gemischte Uebungsrunde ("Jetzt ueben") zu einem Rahmenplan-Punkt,
    wie topic_practice_parts, nur mit den Inhalten des Punktes."""
    from fisi_lernen import PRACTICE_ROUND, key_practice_parts
    return key_practice_parts(book, point_items()[point_id], size or PRACTICE_ROUND, rng)


# ============================================================================
#  GEWICHTUNG NEUER INHALTE (TEIL 4)
# ============================================================================
#
# Wirkt nur auf die Reihenfolge der NOCH NIE bearbeiteten Inhalte beim
# normalen Weiterlernen (StatusBook.preferred_order, Status-Filter "Alle").
# Wiederholungen, Tagesziel und Lernserie bleiben unberuehrt.
#
#   Gewicht = 1 + 1,5 * Wurzel(Wochen je Punkt / 10) + 0,5 * (LF-Stunden / 120)
#
# Wochen je Punkt: groesster Wert unter den (eingeschalteten) Punkten des
# Inhalts; LF-Stunden: groesste Stundenzahl der Lernfelder seines Themas.
# In den 6 Monaten vor dem AP1-Termin zaehlen AP1-relevante Punkte mit
# Faktor 1,5, danach in den 6 Monaten vor dem AP2-Termin alle Punkte mit
# AP2-Bereich. Aus den Gewichten wird eine gewichtete Zufallsreihenfolge
# (Zufallszahl hoch 1/Gewicht, absteigend), der Zufall haengt nur vom Datum
# und vom Inhalt ab: am selben Tag auf PC und Handy dieselbe Reihenfolge.

WEEKS_MAX = 10.0
HOURS_MAX = 120.0
EXAM_FACTOR = 1.5
EXAM_MONTHS = 6


def months_before(day, months):
    month = day.month - months
    year = day.year
    while month < 1:
        month += 12
        year -= 1
    last = (datetime.date(year + month // 12, month % 12 + 1, 1)
            - datetime.timedelta(days=1)).day
    return datetime.date(year, month, min(day.day, last))


def exam_phase(values, today):
    """"ap1", "ap2" oder None: liegt today in den 6 Monaten vor einem
    Pruefungstermin? Vor dem AP1-Termin gilt AP1, danach AP2."""
    ap1 = parse_date(values.get("rp_termin_ap1"))
    ap2 = parse_date(values.get("rp_termin_ap2"))
    if ap1 and today < ap1:
        return "ap1" if today >= months_before(ap1, EXAM_MONTHS) else None
    if ap2 and today < ap2 and today >= months_before(ap2, EXAM_MONTHS):
        return "ap2"
    return None


def _field_hours(topic, values):
    visible = set(visible_fields(values))
    hours = [LEARNING_FIELD[field]["stunden"] for field in TOPIC_FIELDS.get(topic, ())
             if field in visible]
    return max(hours) if hours else 0


_TOPIC = {}


def _item_topic(source, key):
    if not _TOPIC:
        for item in KARTEIKARTEN:
            _TOPIC[(SRC_CARD, item["q"])] = item.get("thema")
        for item in QUIZ_QUESTIONS:
            _TOPIC[(SRC_QUIZ, item["q"])] = item.get("thema")
    return _TOPIC.get((source, key))


def item_weight(source, key, values, today=None):
    """Gewicht eines Inhalts (etwa 1 bis 3, mit Pruefungsnaehe bis 4,5)."""
    today = today or datetime.date.today()
    sections = set(enabled_sections(values))
    points = [POINT[point_id] for point_id in item_points().get((source, key), ())
              if point_id in POINT and POINT[point_id]["abschnitt"] in sections]
    weeks = max([point["wochen_punkt"] for point in points] or [0])
    weight = 1.0 + 1.5 * math.sqrt(min(weeks, WEEKS_MAX) / WEEKS_MAX) + \
        0.5 * (_field_hours(_item_topic(source, key), values) / HOURS_MAX)
    phase = exam_phase(values, today)
    if phase == "ap1" and any(point["ap1"] for point in points):
        weight *= EXAM_FACTOR
    elif phase == "ap2" and any(point["ap2"] for point in points):
        weight *= EXAM_FACTOR
    return weight


def _day_random(source, key, today):
    digest = hashlib.md5(("%s|%s|%s" % (today.isoformat(), source, key))
                         .encode("utf-8")).hexdigest()
    # (0, 1], nie 0 (sonst waere u ** (1 / w) fuer alle Gewichte gleich)
    return (int(digest[:13], 16) + 1) / float(16 ** 13 + 1)


def weighted_order(source, keys, values=None, today=None):
    """keys in gewichteter Zufallsreihenfolge (Efraimidis-Spirakis)."""
    today = today or datetime.date.today()
    values = values if values is not None else dict(RP_SETTINGS)
    scored = [(_day_random(source, key, today) ** (1.0 / item_weight(source, key, values, today)),
               key) for key in keys]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [key for _score, key in scored]


def fresh_order(source, values=None, today=None):
    """Funktion fuer StatusBook.preferred_order(fresh_order=...) oder None,
    wenn die Gewichtung in den Optionen aus ist (dann wie 0.54)."""
    values = values if values is not None else load_rp_settings()
    if not values.get("rp_gewichtung"):
        return None
    return lambda keys: weighted_order(source, keys, values, today)


# ============================================================================
#  OPTIONEN (TEXTE, PC UND HANDY GLEICH)
# ============================================================================

OPTIONS_TITLE = "Rahmenplan"
OPTIONS_SUBTITLE = "Abdeckung im Fortschritt und Reihenfolge neuer Aufgaben"
SECTION_OPTION_TEXT = {
    "B": "Abschnitt B anzeigen (Anwendungsentwicklung)",
    "D": "Abschnitt D anzeigen (Daten- und Prozessanalyse)",
    "E": "Abschnitt E anzeigen (Digitale Vernetzung)",
}
WEIGHT_OPTION_TEXT = "Übungsauswahl nach Rahmenplan gewichten"
WEIGHT_OPTION_HINT = ("Neue Aufgaben zu Punkten mit viel Ausbildungszeit kommen etwas "
                      "früher dran, vor einem Prüfungstermin die prüfungsrelevanten. "
                      "Wiederholungen bleiben unverändert.")
FIELD_OPTION_TEXT = "Aktuelles Lernfeld"
FIELD_OPTION_OFF = "Aus"
AP1_DATE_TEXT = "Termin AP1"
AP2_DATE_TEXT = "Termin AP2"
DATE_HINT = "TT.MM.JJJJ"
DATE_INVALID = "Bitte ein Datum im Format TT.MM.JJJJ eingeben."


def field_options():
    """[(wert, beschriftung)] fuer die Auswahl "Aktuelles Lernfeld"."""
    return [("", FIELD_OPTION_OFF)] + [(entry["id"], entry["id"]) for entry in LEARNING_FIELDS]
