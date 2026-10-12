#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fachinformatiker Lernplattform - Lernwerkzeuge ab 0.51 (ohne Oberflaeche)
=========================================================================

Gemeinsam fuer PC und Handy:
  * Wiederholungssystem (Spaced Repetition) fuer Karteikarten und
    Pruefungstrainer-Fragen - berechnet nur aus den Antworten, die ohnehin
    abgeglichen werden. PC und Handy rechnen deshalb immer gleich.
  * Tagesziel und Lernserie, ab 0.54 auch "Aufgaben pro Tag" (Fortschritt)
  * ab 0.54: Uebungsrunde zu einem schwachen Thema ("Jetzt ueben")
  * Subnetting-Trainer (Zufallsaufgaben, Pruefung der Eingaben, Rechenweg)

Die Oberflaechen (app_gui.py, mobile/src/main.py) zeichnen nur.
"""

import datetime
import hashlib
import ipaddress
import random
import sys

from fisi_core import (KARTEIKARTEN, LEVEL_RED, Q_DONE, Q_PRACTICE, QUIZ_QUESTIONS,
                       SRC_CARD, SRC_QUIZ, TOPIC_NAME, StatusBook, learning_streak,
                       plural)


# ============================================================================
#  WIEDERHOLUNGSSYSTEM
# ============================================================================
#
# Regeln (Nicos Plan 0.51):
#   * Abstaende 1, 3, 7, 14, 30 Tage (Stufe 1 bis 5).
#   * Eine richtige Antwort am oder nach dem Faelligkeitstag hebt die Stufe
#     um eins, die naechste Faelligkeit ist dann heute + Abstand der Stufe.
#     Richtig vor dem Faelligkeitstag (normales Weiterlernen) aendert nichts.
#   * Ein Fehler setzt auf Anfang (Stufe 0), die Karte ist morgen wieder
#     faellig. Der Notizblock-Status wird davon nicht beruehrt: der zeigt
#     nach einem Fehler ohnehin "Zu ueben".
#   * Altbestand: Karten, die nur vor SR_START bearbeitet wurden, waeren
#     sonst alle auf einmal faellig. Davon werden pro Tag hoechstens
#     SR_LEGACY_PER_DAY freigegeben (zu Uebende zuerst). Wer an einem Tag
#     schon alte Karten wiederholt hat, bekommt entsprechend weniger neue.

SR_INTERVALS = (1, 3, 7, 14, 30)
SR_START = "2026-10-01"
SR_LEGACY_PER_DAY = 20
SR_SOURCES = (SRC_CARD, SRC_QUIZ)
# Hoechstens so viele Fragen in einer Wiederholungs-Sitzung
SR_SESSION_MAX = 50


def _date(timestamp):
    return datetime.date.fromisoformat(str(timestamp)[:10])


def review_state(entries):
    """(stufe, faellig_am) einer Frage aus ihren Antworten (aelteste zuerst,
    (timestamp, True/False/None)). faellig_am ist None, wenn die Frage noch
    nie bewertet wurde."""
    stage, due = 0, None
    for timestamp, value in entries:
        if value is None:
            continue
        day = _date(timestamp)
        if not value:
            stage, due = 0, day + datetime.timedelta(days=1)
        elif due is None or day >= due:
            stage = min(stage + 1, len(SR_INTERVALS))
            due = day + datetime.timedelta(days=SR_INTERVALS[stage - 1])
    return stage, due


if sys.version_info >= (3, 9):
    def _md5(data):
        """MD5 nur fuer eine feste Reihenfolge, nicht fuer Sicherheit (ab
        0.62.5, B-B-07: kein Alarm im Sicherheitswerkzeug, kein Absturz auf
        Systemen, die MD5 fuer Sicherheit sperren)."""
        return hashlib.md5(data, usedforsecurity=False)
else:  # Python 3.8 kennt usedforsecurity noch nicht
    def _md5(data):
        return hashlib.md5(data)  # nosec B324 - nur Reihenfolge, keine Sicherheit


def _stable_rank(source, key):
    """Feste, auf allen Geraeten gleiche Reihenfolge fuer den Altbestand."""
    return _md5(("%s|%s" % (source, key)).encode("utf-8")).hexdigest()


class ReviewPlan:
    """Faellige Wiederholungen fuer einen Tag, einmal aus dem StatusBook
    berechnet. due[quelle] = Liste der faelligen Schluessel (zuerst die am
    laengsten ueberfaelligen)."""

    def __init__(self, book, today=None, valid=None):
        self.today = today or datetime.date.today()
        start = datetime.date.fromisoformat(SR_START)
        if valid is None:
            valid = {SRC_CARD: {card["q"] for card in KARTEIKARTEN},
                     SRC_QUIZ: {question["q"] for question in QUIZ_QUESTIONS}}
        self.state = {}
        regular, legacy = [], []
        migrated_today = 0
        for (source, key), entries in book.results.items():
            if source not in SR_SOURCES or key not in valid[source]:
                continue
            graded = [(t, v) for t, v in entries if v is not None]
            if not graded:
                continue
            stage, due = review_state(graded)
            self.state[(source, key)] = (stage, due)
            old = [t for t, _v in graded if _date(t) < start]
            new = [t for t, _v in graded if _date(t) >= start]
            if old and not new:
                legacy.append((source, key))
                continue
            if old and new and _date(new[0]) == self.today:
                migrated_today += 1
            if due <= self.today:
                regular.append((due, source, key))
        regular.sort(key=lambda item: (item[0], _stable_rank(item[1], item[2])))
        # Altbestand: zu Uebende (rot vor gelb) zuerst, sonst feste Reihenfolge
        if self.today >= start:
            def legacy_rank(item):
                status, level = book.status(*item)
                order = 0 if (status, level) == (Q_PRACTICE, LEVEL_RED) else \
                    1 if status == Q_PRACTICE else 3 if status == Q_DONE else 2
                return order, _stable_rank(*item)
            legacy.sort(key=legacy_rank)
            quota = max(0, SR_LEGACY_PER_DAY - migrated_today)
            released = legacy[:quota]
        else:
            released = []
        self.legacy_waiting = len(legacy) - len(released)
        self.due = {source: [] for source in SR_SOURCES}
        for _due, source, key in regular:
            self.due[source].append(key)
        for source, key in released:
            self.due[source].append(key)

    @classmethod
    def from_db(cls, db, today=None):
        return cls(StatusBook(db), today=today)

    def count(self, source=None):
        if source is not None:
            return len(self.due[source])
        return sum(len(keys) for keys in self.due.values())

    def is_due(self, source, key):
        return key in self.due.get(source, ())

    def stage(self, source, key):
        return self.state.get((source, key), (0, None))[0]

    def session(self, source, limit=SR_SESSION_MAX):
        """Schluessel fuer eine Wiederholungs-Sitzung (hoechstens limit)."""
        return list(self.due[source][:limit])

    def first_source(self):
        """Womit "Jetzt wiederholen" beginnt: zuerst Karteikarten, dann
        Pruefungstrainer. None, wenn nichts faellig ist."""
        for source in SR_SOURCES:
            if self.due[source]:
                return source
        return None


def due_text(plan):
    """Anzeigetext fuer Dashboard/Start."""
    cards, quiz = plan.count(SRC_CARD), plan.count(SRC_QUIZ)
    if not cards and not quiz:
        return "Heute ist nichts fällig"
    parts = []
    if cards:
        parts.append("%d Karteikarte%s" % (cards, "" if cards == 1 else "n"))
    if quiz:
        parts.append("%d Prüfungsfrage%s" % (quiz, "" if quiz == 1 else "n"))
    return "Heute fällig: " + " · ".join(parts)


# ============================================================================
#  TAGESZIEL UND LERNSERIE
# ============================================================================

GOAL_DEFAULT = 20
GOAL_MIN = 5
GOAL_MAX = 100
GOAL_STEP = 5
REMINDER_DEFAULT = "18:00"

# Einstellungen je Geraet (einstellungen.json, wie die Farben)
GOAL_SETTINGS = {
    "ziel_an": True,
    "ziel_anzahl": GOAL_DEFAULT,
    "serie_an": True,
    "erinnerung_an": True,
    "erinnerung_zeit": REMINDER_DEFAULT,
}


def goal_settings(settings):
    """Einstellungen fuers Tagesziel mit Standardwerten und gueltigen Grenzen."""
    values = dict(GOAL_SETTINGS)
    for key in GOAL_SETTINGS:
        if key in settings:
            values[key] = settings[key]
    try:
        count = int(values["ziel_anzahl"])
    except (TypeError, ValueError):
        count = GOAL_DEFAULT
    values["ziel_anzahl"] = max(GOAL_MIN, min(GOAL_MAX, count))
    values["erinnerung_zeit"] = parse_time(values["erinnerung_zeit"]) or REMINDER_DEFAULT
    for key in ("ziel_an", "serie_an", "erinnerung_an"):
        values[key] = bool(values[key])
    return values


def learning_settings():
    """Tagesziel-Einstellungen dieses Geraets (einstellungen.json)."""
    from fisi_update import load_settings
    return goal_settings(load_settings())


def save_learning_settings(**values):
    """Speichert Tagesziel-Einstellungen (nur die bekannten Schluessel)."""
    from fisi_update import load_settings, save_settings
    settings = load_settings()
    settings.update({key: value for key, value in values.items()
                     if key in GOAL_SETTINGS or key == "erinnerung_gezeigt"})
    return save_settings(settings)


def parse_time(text):
    """"HH:MM" oder None bei ungueltiger Eingabe."""
    try:
        hours, minutes = str(text).strip().split(":")
        hours, minutes = int(hours), int(minutes)
    except (ValueError, AttributeError):
        return None
    if not (0 <= hours <= 23 and 0 <= minutes <= 59):
        return None
    return "%02d:%02d" % (hours, minutes)


class DailyGoal:
    """Stand des Tagesziels, aus den Lernaktivitaeten berechnet."""

    def __init__(self, activity, target, today=None):
        self.today = today or datetime.date.today()
        self.target = target
        self.done = activity.get(self.today.isoformat(), 0)
        self.streak = learning_streak({day for day, count in activity.items() if count},
                                      self.today)

    @classmethod
    def from_db(cls, db, target, today=None):
        return cls(db.activity_days(), target, today)

    @property
    def reached(self):
        return self.done >= self.target

    @property
    def fraction(self):
        return min(1.0, self.done / self.target) if self.target else 1.0

    def text(self):
        if self.reached:
            return "Tagesziel erreicht: %d von %d Aufgaben" % (self.done, self.target)
        return "Tagesziel: %d von %d Aufgaben" % (self.done, self.target)

    def streak_text(self):
        return "Lernserie: %s" % plural(self.streak, "Tag", "Tage")


def reminder_due(settings, goal, now=None, shown_on=""):
    """Soll jetzt an das Tagesziel erinnert werden? Nur einmal am Tag
    (shown_on = Datum der letzten Erinnerung), nach der eingestellten
    Uhrzeit und nur, wenn das Ziel noch offen ist."""
    values = goal_settings(settings)
    if not (values["ziel_an"] and values["erinnerung_an"]) or goal.reached:
        return False
    now = now or datetime.datetime.now()
    if shown_on == now.date().isoformat():
        return False
    return now.strftime("%H:%M") >= values["erinnerung_zeit"]


def reminder_text(goal):
    rest = max(0, goal.target - goal.done)
    return ("Dein Tagesziel ist noch offen: %d von %d Aufgaben, es fehlen noch %d."
            % (goal.done, goal.target, rest))


# ============================================================================
#  AUFGABEN PRO TAG (ab 0.54)
# ============================================================================
#
# Diagramm im Fortschritt. Gezaehlt wird genau wie beim Tagesziel und der
# Lernserie (DBManager.activity_days: bewertete Aufgaben je Kalendertag in
# Ortszeit, die Zeitstempel stehen schon in Ortszeit in der Datenbank). Ein
# neuer Tag beginnt um Mitternacht, Tage ohne Aufgaben zaehlen 0.

DAY_CHART_TITLE = "Aufgaben pro Tag"
DAY_CHART_SUBTITLE = "bewertete Aufgaben, Tagesziel als Linie"
DAY_CHART_RANGES = [(7, "7 Tage"), (30, "30 Tage")]
DAY_CHART_SERIES = "Aufgaben"
# Legende "Lernverlauf" (Dashboard/Start, ab 0.58). Ab 0.60 eigener Name: der
# Lernverlauf zaehlt alle Lernschritte (auch nur aufgedeckte Karten), das
# Tagesziel und "Aufgaben pro Tag" im Fortschritt nur bewertete.
LEARN_CHART_SERIES = "Lernaktivitäten pro Tag"

# Ab 0.60 (K-B): Beschriftungen von Dashboard (PC) und Start (Handy), an
# beiden Stellen gleich. "Prüfungstrainer" ist der Menuename; "bearbeitet"
# heisst angesehen oder beantwortet (auch falsch), "richtig" nur richtig.
DASH_LEARNED = "%d von %d Karten und Fragen bearbeitet"
DASH_RATE = "Prüfungstrainer %d %% richtig"
DASH_TOTAL = "Gesamtfortschritt"
DASH_RING_CARDS = "Karteikarten"
DASH_RING_QUIZ = "Prüfungstrainer"
DASH_RING_AP1 = "AP1-Szenarien"
DASH_RING_AP2 = "AP2-Szenarien"
DASH_CARDS_SUB = "von %d Karten bearbeitet"
DASH_QUIZ_SUB = "von %d Fragen beantwortet"
DASH_SCEN_SUB = "von %d bearbeitet"
DASH_QUOTE_TITLE = "Erfolgsquote"
DASH_QUOTE_SUBTITLE = "Prüfungstrainer gesamt"
DASH_QUOTE_EMPTY = "noch keine Antworten erfasst"
DASH_SIDEBAR_BAR = "Karten und Fragen bearbeitet"


def dash_quote_text(correct, answered):
    """Unterzeile der Erfolgsquote: gezaehlt werden Antworten (jeder Versuch),
    nicht verschiedene Fragen."""
    if not answered:
        return DASH_QUOTE_EMPTY
    return "%d von %s richtig" % (correct, plural(answered, "Antwort", "Antworten"))
WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def daily_series(activity, days, today=None):
    """[(datum, anzahl)] der letzten days Tage bis einschliesslich heute,
    aelteste zuerst. activity: {"JJJJ-MM-TT": anzahl} wie activity_days."""
    today = today or datetime.date.today()
    start = today - datetime.timedelta(days=days - 1)
    return [(day, int(activity.get(day.isoformat(), 0) or 0))
            for day in (start + datetime.timedelta(days=offset) for offset in range(days))]


def day_labels(series):
    """Beschriftung der x-Achse: bei einer Woche der Wochentag, sonst TT.MM."""
    if len(series) <= 7:
        return [WEEKDAYS[day.weekday()] for day, _count in series]
    return [day.strftime("%d.%m") for day, _count in series]


def goal_line_text(target):
    return "Tagesziel %d" % target


def daily_summary(series, target=None):
    """Kurztext unter dem Diagramm, z.B. "7 Tage: 85 Aufgaben · Tagesziel an
    3 von 7 Tagen erreicht"."""
    total = sum(count for _day, count in series)
    text = "%s: %s" % (plural(len(series), "Tag", "Tage"),
                       plural(total, "Aufgabe", "Aufgaben"))
    if target:
        reached = sum(1 for _day, count in series if count >= target)
        text += " · Tagesziel an %d von %s erreicht" % (
            reached, plural(len(series), "Tag", "Tagen"))
    return text


# ============================================================================
#  RICHTIG UND FALSCH PRO TAG, ERGEBNISSE IM PRUEFUNGSTRAINER (ab 0.56)
# ============================================================================
#
# Richtig/falsch je Tag: dieselben bewerteten Aufgaben wie "Aufgaben pro Tag"
# (DBManager.activity_split_days), als Anteil in Prozent. Eine Aufgabe zaehlt
# so, wie sie gespeichert ist: Karteikarten und Szenarien mit der eigenen
# Bewertung, Quiz und Trainer mit dem Ergebnis der Pruefung.
#
# "Ergebnisse im Zeitverlauf" (bis 0.55) zeigte die Erfolgsquote je
# abgeschlossener Session im Pruefungstrainer (Tabelle test_results: eine
# Zeile, wenn eine Runde bis zur Auswertung gespielt wurde). Ohne Session
# zeichnete das Diagramm einen Platzhalter-Punkt "heute" bei 0 % - das war
# kein Ergebnis. Ab 0.56 erscheint stattdessen ein Hinweis.

SPLIT_CHART_TITLE = "Richtig und falsch pro Tag"
SPLIT_RIGHT = "richtig"
SPLIT_WRONG = "falsch"
SPLIT_EMPTY_DAY = "–"

RESULT_CHART_TITLE = "Ergebnisse im Prüfungstrainer"
RESULT_CHART_SUBTITLE = "% richtig je abgeschlossener Session"
RESULT_CHART_SERIES = "richtig in %"
RESULT_CHART_EMPTY = ("Noch keine Ergebnisse. Hier erscheint nach jeder abgeschlossenen "
                      "Session im Prüfungstrainer (Runde bis zur Auswertung gespielt), wie "
                      "viel Prozent der Fragen du richtig beantwortet hast – mit Datum.")

# Optionen: alle Loeschfunktionen in einem aufklappbaren Bereich
DELETE_TITLE = "Löschen und zurücksetzen"
DELETE_SUBTITLE = "Lerndaten, Historie, Spielstand, Bestenliste"
# Ab 0.56 (Nachbesserung): "Historie loeschen" aus dem Fortschritt hierher
# verschoben, die Sicherheitsabfrage ist unveraendert
HISTORY_LABEL = "Historie"
HISTORY_TEXT = ("Löscht alle gespeicherten Testergebnisse und Prüfungen, die im "
                "„Fortschritt“ stehen. Die übrigen Lerndaten (Tagesziel, Lernserie, "
                "Aufgaben pro Tag) bleiben erhalten. Dieser Schritt lässt sich nicht "
                "rückgängig machen.")
HISTORY_BUTTON = "Historie löschen"
FOLD_OPEN = "aufklappen"
FOLD_CLOSE = "zuklappen"


def daily_split_series(split, days, today=None):
    """[(datum, richtig, falsch)] der letzten days Tage bis heute, aelteste
    zuerst. split: {"JJJJ-MM-TT": (richtig, falsch)} wie activity_split_days."""
    today = today or datetime.date.today()
    start = today - datetime.timedelta(days=days - 1)
    series = []
    for offset in range(days):
        day = start + datetime.timedelta(days=offset)
        right, wrong = split.get(day.isoformat(), (0, 0))
        series.append((day, int(right or 0), int(wrong or 0)))
    return series


def split_percent(right, wrong):
    """(richtig %, falsch %) gerundet, Summe 100; (None, None) ohne Aufgaben."""
    total = right + wrong
    if not total:
        return None, None
    share = int(round(right * 100.0 / total))
    return share, 100 - share


def split_summary(series):
    """Kurztext, z.B. "7 Tage: 83 % richtig, 17 % falsch (265 von 320)"."""
    right = sum(r for _day, r, _w in series)
    wrong = sum(w for _day, _r, w in series)
    head = "%s: " % plural(len(series), "Tag", "Tage")
    if not right + wrong:
        return head + "noch keine bewerteten Aufgaben"
    share, rest = split_percent(right, wrong)
    return head + "%d %% richtig, %d %% falsch (%d von %d)" % (share, rest, right,
                                                               right + wrong)


def result_series(results):
    """Werte fuer "Ergebnisse im Pruefungstrainer" aus DBManager.get_all_results
    (neueste zuerst): ([Beschriftung TT.MM.], [Prozent]) der letzten 20,
    aelteste zuerst. Ohne Session ([], [])."""
    ordered = list(reversed(results))[-20:]
    labels = ["%s.%s." % (row[0][8:10], row[0][5:7]) for row in ordered]
    return labels, [row[3] for row in ordered]


# ============================================================================
#  SCHWAECHEN DIREKT UEBEN (ab 0.54)
# ============================================================================
#
# "Jetzt ueben" neben einem schwachen Thema (Auswertung der Pruefungs-
# simulation, Fortschritt) startet eine normale Uebungsrunde - die Antworten
# laufen ueber die ueblichen Speicherwege und zaehlen fuer Tagesziel,
# Lernserie und Wiederholungssystem. Die Themen der Pruefung (Szenario-
# Themen bzw. WiSo-Bereiche) haben eigene Namen; EXAM_THEME_TOPICS ordnet
# ihnen die passenden Themen der Karteikarten und Quizfragen zu.

PRACTICE_ROUND = 10     # wie die vorgegebene Fragenanzahl im Pruefungstrainer
PRACTICE_BUTTON = "Jetzt üben"
PRACTICE_NONE = "Zu diesem Thema gibt es keine Übungsfragen."
PRACTICE_NEXT_TITLE = "Weiter üben"

EXAM_THEME_TOPICS = {
    # AP2 (Szenario-Themen); ab 0.55 um die Lernthemen ergaenzt, aus denen die
    # Szenarien des Pruefungsthemas tatsaechlich stammen (Zuordnung_0.55)
    "Subnetting & Routing": ["ipv4", "ipv6", "routing", "wan_vpn"],
    "IT-Sicherheit": ["isms", "krypto", "zugriff", "angriffe", "netzsicherheit", "haertung",
                      "notfall", "datenschutz"],
    "Storage & RAID": ["storage", "notfall", "db_betrieb"],
    "Netzwerkdesign": ["switching", "wlan", "verkabelung", "wan_vpn", "grundlagen",
                       "dienste", "routing"],
    "Wirtschaft & Beratung": ["kalkulation", "beschaffung", "beratung", "service", "recht"],
    "Virtualisierung": ["virtualisierung"],
    "Projektmanagement": ["projekt", "service"],
    "Systemadministration": ["windows", "linux", "zugriff", "haertung", "it_betrieb"],
    "Automatisierung & Skripte": ["programmierung", "windows", "linux"],
    # AP1
    "Rechnertechnik & Zahlensysteme": ["hardware", "zahlen", "programmierung", "it_betrieb",
                                       "storage"],
    "Rechnernetze Grundlagen": ["grundlagen", "ipv4", "dienste", "verkabelung", "wan_vpn",
                                "wlan", "fehlersuche", "switching"],
    "Datenschutz & Sicherheit": ["datenschutz", "zugriff", "angriffe", "notfall", "isms",
                                 "krypto", "haertung", "netzsicherheit"],
    "Projektplanung": ["projekt", "beschaffung", "kalkulation"],
    "Arbeitsplatz einrichten: Bedarf, Beschaffung, Übergabe": [
        "beschaffung", "beratung", "hardware", "it_betrieb", "kalkulation", "projekt"],
    "Wirtschafts- und Sozialkunde": ["recht", "arbeitswelt", "kalkulation"],
    # WiSo (fisi_pruefung.evaluate)
    "Recht & Verträge": ["recht"],
    "Arbeitswelt": ["arbeitswelt"],
}


def practice_topics(name):
    """Themen-IDs (fisi_core.TOPICS) zu einem Pruefungsthema, einer
    Themen-ID oder einem Themennamen. Unbekannt = leere Liste."""
    if name in EXAM_THEME_TOPICS:
        return list(EXAM_THEME_TOPICS[name])
    if name in TOPIC_NAME:
        return [name]
    return [topic for topic, title in TOPIC_NAME.items() if title == name]


def _practice_rank(book, source, key):
    """Reihenfolge in der Runde: rot, gelb, unbearbeitet, angefangen,
    abgeschlossen."""
    if not book.touched(source, key):
        return 2
    status, level = book.status(source, key)
    if status == Q_PRACTICE:
        return 0 if level == LEVEL_RED else 1
    return 4 if status == Q_DONE else 3


def topic_practice_parts(book, topics, size=PRACTICE_ROUND, rng=None):
    """Gemischte Uebungsrunde zu den Themen topics (ab 0.54): Liste von
    (quelle, schluessel) mit Quizfragen UND Karteikarten, je hoechstens size,
    Ungewusstes (rot, dann gelb) zuerst. Zuerst der Pruefungstrainer (seine
    Runde hat ein Ende mit Ergebnis), danach die Karteikarten. Bereiche ohne
    passende Fragen fehlen; ohne jede passende Frage []."""
    wanted = set(topics)
    pools = {SRC_QUIZ: [q["q"] for q in QUIZ_QUESTIONS if q.get("thema") in wanted],
             SRC_CARD: [c["q"] for c in KARTEIKARTEN if c.get("thema") in wanted]}
    return key_practice_parts(book, pools, size, rng)


def key_practice_parts(book, pools, size=PRACTICE_ROUND, rng=None):
    """Wie topic_practice_parts, aber mit festen Inhalten (ab 0.55, z.B. die
    eines Rahmenplan-Punktes): pools = {quelle: [schluessel]}."""
    parts = []
    for source in (SRC_QUIZ, SRC_CARD):
        keys = list(pools.get(source) or ())
        if rng is not None:
            rng.shuffle(keys)
        ranks = {key: _practice_rank(book, source, key) for key in keys}
        if keys:
            parts.append((source, sorted(keys, key=lambda key: ranks[key])[:size]))
    return parts


def topic_practice(book, topics, size=PRACTICE_ROUND, rng=None):
    """Erster Teil der gemischten Runde (topic_practice_parts) als (quelle,
    schluessel). Ohne passende Fragen (None, [])."""
    parts = topic_practice_parts(book, topics, size, rng)
    return parts[0] if parts else (None, [])


def practice_next_text(source, count):
    """Rueckfrage nach dem ersten Teil von "Jetzt ueben": weiter mit dem
    zweiten Bereich?"""
    if source == SRC_CARD:
        what = plural(count, "Karteikarte", "Karteikarten")
    else:
        what = plural(count, "Prüfungsfrage", "Prüfungsfragen")
    return "Zum selben Thema gibt es noch %s. Jetzt weiterüben?" % what


# ============================================================================
#  SUBNETTING-TRAINER
# ============================================================================

TRAINER_KINDS = [
    ("ipv4", "IPv4-Subnetz"),
    ("vlsm", "VLSM"),
    ("zahlen", "Binär/Hex/Dezimal"),
    ("ipv6", "IPv6 kürzen"),
    ("teilen", "Netz aufteilen"),
    ("bedarf", "Nach Hostbedarf"),
]
TRAINER_KIND_NAME = dict(TRAINER_KINDS)
TRAINER_LEVELS = [(1, "Leicht"), (2, "Mittel"), (3, "Schwer")]
TRAINER_LEVEL_NAME = dict(TRAINER_LEVELS)
TRAINER_ROUND = 10


class TrainerTask:
    """Eine Aufgabe: text, felder [(schluessel, beschriftung)], loesung
    {schluessel: text}, rechenweg (Zeilen). check() prueft Eingaben."""

    def __init__(self, kind, level, text, fields, solution, steps, matchers):
        self.kind = kind
        self.level = level
        self.text = text
        self.fields = fields
        self.solution = solution
        self.steps = steps
        self._matchers = matchers

    def check(self, answers):
        """{schluessel: True/False} je Feld."""
        return {key: bool(self._matchers[key](answers.get(key, "")))
                for key, _label in self.fields}

    def all_correct(self, answers):
        return all(self.check(answers).values())


def _clean(text):
    return "".join(str(text).split()).lower()


def _ip_matcher(expected):
    def match(text):
        try:
            return ipaddress.ip_address(_clean(text)) == expected
        except ValueError:
            return False
    return match


def _int_matcher(expected):
    def match(text):
        value = _clean(text).replace(".", "")
        return value.isdigit() and int(value) == expected
    return match


def _base_matcher(expected, base):
    prefix = {2: ("0b",), 16: ("0x", "h")}.get(base, ())

    def match(text):
        value = _clean(text)
        for mark in prefix:
            if value.startswith(mark):
                value = value[len(mark):]
            elif value.endswith(mark) and mark == "h":
                value = value[:-1]
        value = value.replace("_", "")
        try:
            return value != "" and int(value, base) == expected
        except ValueError:
            return False
    return match


def _network_matcher(expected):
    def match(text):
        try:
            return ipaddress.ip_network(_clean(text), strict=True) == expected
        except ValueError:
            return False
    return match


def _ipv6_text_matcher(expected):
    def match(text):
        return _clean(text) == expected.lower()
    return match


def _dotted_binary(address):
    return ".".join(format(octet, "08b") for octet in address.packed)


def _ipv4_and_narrow(address, network):
    """Ab 0.62.3 (F-E7): Schritt 3 der IPv4-Aufgabe fuer das Handy, Oktett
    fuer Oktett untereinander, hoechstens 28 Zeichen je Zeile. Gleiche
    Bitreihen und gleiches Ergebnis wie am PC, dazu je Oktett der Dezimalwert."""
    lines = ["3. UND-Verknüpfung je Oktett"]
    for number, (addr, mask, net) in enumerate(zip(address.packed, network.netmask.packed,
                                                   network.network_address.packed), 1):
        lines += ["   Oktett %d:" % number,
                  "     Adresse %s" % format(addr, "08b"),
                  "     Maske   %s" % format(mask, "08b"),
                  "     UND     %s = %d" % (format(net, "08b"), net)]
    lines.append("   Ergebnis: %s" % network.network_address)
    return lines


def _ipv4_task(rng, level, schmal=False):
    prefix = {1: rng.randint(24, 30), 2: rng.randint(17, 30),
              3: rng.randint(8, 30)}[level]
    first = rng.choice([10, 172, 192])
    if first == 10:
        octets = [10, rng.randint(0, 255), rng.randint(0, 255), rng.randint(1, 254)]
    elif first == 172:
        octets = [172, rng.randint(16, 31), rng.randint(0, 255), rng.randint(1, 254)]
    else:
        octets = [192, 168, rng.randint(0, 255), rng.randint(1, 254)]
    address = ipaddress.IPv4Address(".".join(map(str, octets)))
    network = ipaddress.IPv4Network("%s/%d" % (address, prefix), strict=False)
    hosts = network.num_addresses - 2
    first_host = network.network_address + 1
    last_host = network.broadcast_address - 1
    block_octet = prefix // 8
    fields = [("netz", "Netzadresse"), ("maske", "Subnetzmaske"),
              ("broadcast", "Broadcast-Adresse"), ("erste", "Erste Host-Adresse"),
              ("letzte", "Letzte Host-Adresse"), ("hosts", "Nutzbare Hosts")]
    solution = {"netz": str(network.network_address), "maske": str(network.netmask),
                "broadcast": str(network.broadcast_address), "erste": str(first_host),
                "letzte": str(last_host), "hosts": str(hosts)}
    matchers = {"netz": _ip_matcher(network.network_address),
                "maske": _ip_matcher(network.netmask),
                "broadcast": _ip_matcher(network.broadcast_address),
                "erste": _ip_matcher(first_host), "letzte": _ip_matcher(last_host),
                "hosts": _int_matcher(hosts)}
    steps = [
        "1. Präfix /%d: %d Bit Netzanteil, %d Bit Hostanteil." % (prefix, prefix, 32 - prefix),
        "2. Maske: %d Einsen = %s" % (prefix, network.netmask),
    ]
    if schmal:
        steps += _ipv4_and_narrow(address, network)
    else:
        # Ab 0.62.3: die drei Bitreihen beginnen in derselben Spalte
        steps += [
            "3. Adresse binär:   %s" % _dotted_binary(address),
            "   Maske binär:     %s" % _dotted_binary(network.netmask),
            "   UND-Verknüpfung: %s = %s" % (_dotted_binary(network.network_address),
                                             network.network_address),
        ]
    if prefix % 8:
        mask_octet = network.netmask.packed[block_octet]
        steps.append("   Kurzweg: Blockgröße im %d. Oktett = 256 - %d = %d; "
                     "%d liegt im Block ab %d."
                     % (block_octet + 1, mask_octet, 256 - mask_octet,
                        address.packed[block_octet],
                        network.network_address.packed[block_octet]))
    steps += [
        "4. Broadcast-Adresse: alle Hostbits auf 1 = %s" % network.broadcast_address,
        "5. Hostbereich: %s bis %s (Netzadresse + 1 bis Broadcast-Adresse - 1)"
        % (first_host, last_host),
        "6. Nutzbare Hosts: 2^%d - 2 = %d" % (32 - prefix, hosts),
    ]
    text = "Berechne zur Adresse %s/%d die Netzdaten." % (address, prefix)
    return TrainerTask("ipv4", level, text, fields, solution, steps, matchers)


def _vlsm_task(rng, level):
    count = {1: 2, 2: 3, 3: 4}[level]
    base_prefix = {1: 24, 2: 24, 3: rng.choice([22, 23])}[level]
    capacity = 2 ** (32 - base_prefix)
    names = ["Verwaltung", "Produktion", "Vertrieb", "Lager", "Technik", "Gäste-WLAN",
             "Server", "Entwicklung"]
    while True:
        wanted = sorted(rng.sample(range(5, capacity // count), count), reverse=True)
        # Kleinste Zweierpotenz >= Hosts + 2
        sizes = []
        for need in wanted:
            size = 4
            while size - 2 < need:
                size *= 2
            sizes.append(size)
        if sum(sizes) <= capacity:
            break
    if base_prefix == 24:
        base = ipaddress.IPv4Network("192.168.%d.0/24" % rng.randint(0, 250))
    else:
        third = rng.randint(0, 60) * 4
        base = ipaddress.IPv4Network("10.%d.%d.0/%d" % (rng.randint(0, 255), third,
                                                        base_prefix), strict=False)
    departments = rng.sample(names, count)
    order = sorted(range(count), key=lambda i: (-wanted[i], i))
    start = int(base.network_address)
    nets = {}
    steps = ["Vorgehen: größtes Netz zuerst, jedes Netz beginnt direkt hinter dem "
             "vorherigen."]
    for number, index in enumerate(order, start=1):
        size = sizes[index]
        prefix = 32 - size.bit_length() + 1
        net = ipaddress.IPv4Network((start, prefix))
        nets[index] = net
        steps.append("%d. %s: %d Hosts + 2 = %d Adressen nötig -> Block %d (/%d) -> %s, "
                     "Broadcast-Adresse %s" % (number, departments[index], wanted[index],
                                       wanted[index] + 2, size, prefix, net,
                                       net.broadcast_address))
        start += size
    fields = [("netz%d" % i, "%s (%d Hosts)" % (departments[i], wanted[i]))
              for i in range(count)]
    solution = {"netz%d" % i: str(nets[i]) for i in range(count)}
    matchers = {"netz%d" % i: _network_matcher(nets[i]) for i in range(count)}
    text = ("Teile das Netz %s nach VLSM auf (größtes Netz zuerst, lückenlos ab der "
            "ersten Adresse). Gib je Abteilung Netzadresse/Präfix an, z.B. "
            "192.168.1.0/26." % base)
    return TrainerTask("vlsm", level, text, fields, solution, steps, matchers)


def _number_task(rng, level):
    maximum = {1: 255, 2: 4095, 3: 65535}[level]
    value = rng.randint(1 if level == 1 else 16, maximum)
    given = rng.choice(["dez", "bin", "hex"])
    digits = {1: 8, 2: 12, 3: 16}[level]
    shown = {"dez": str(value), "bin": format(value, "0%db" % digits),
             "hex": format(value, "X")}
    names = {"dez": "Dezimal", "bin": "Binär", "hex": "Hexadezimal"}
    fields = [(key, names[key]) for key in ("dez", "bin", "hex") if key != given]
    matchers = {"dez": _int_matcher(value), "bin": _base_matcher(value, 2),
                "hex": _base_matcher(value, 16)}
    solution = {key: shown[key] for key, _label in fields}
    binary = format(value, "b")
    nibbles = [binary[::-1][i:i + 4][::-1] for i in range(0, len(binary), 4)][::-1]
    weights = [2 ** i for i in range(len(binary) - 1, -1, -1)]
    parts = ["%d" % w for w, bit in zip(weights, binary) if bit == "1"]
    steps = []
    if given == "dez":
        rest, lines = value, []
        while rest:
            lines.append("%d : 2 = %d Rest %d" % (rest, rest // 2, rest % 2))
            rest //= 2
        steps.append("Dezimal -> Binär (fortgesetzt durch 2 teilen, Reste von unten "
                     "nach oben lesen):")
        steps += ["   " + line for line in lines[:12]]
        if len(lines) > 12:
            steps.append("   ...")
    elif given == "hex":
        hex_digits = format(value, "X")
        terms = ["%s x 16^%d" % (digit, len(hex_digits) - 1 - i)
                 for i, digit in enumerate(hex_digits)]
        steps.append("Hex -> Dezimal: %s = %d" % (" + ".join(terms), value))
    else:
        steps.append("Stellenwerte der Einsen addieren: %s = %d"
                     % (" + ".join(parts), value))
    steps.append("Binär -> Hex: in Vierergruppen (Nibbles) von rechts teilen: %s"
                 % " ".join(n.zfill(4) for n in nibbles))
    steps.append("Jede Gruppe ist eine Hex-Ziffer: %s"
                 % " ".join("%s=%X" % (n.zfill(4), int(n, 2)) for n in nibbles))
    text = "Rechne %s %s in die anderen Zahlensysteme um." % (names[given], shown[given])
    return TrainerTask("zahlen", level, text, fields, solution, steps, matchers)


def _ipv6_task(rng, level):
    groups = []
    zero_runs = {1: 1, 2: 2, 3: 2}[level]
    for _ in range(8):
        groups.append(rng.choice([0, 0, rng.randint(1, 0xF), rng.randint(0x10, 0xFFF),
                                  rng.randint(0x1000, 0xFFFF)]))
    groups[0] = 0x2001
    groups[1] = 0x0DB8
    # Nullbloecke einbauen
    for _ in range(zero_runs):
        start = rng.randint(2, 6)
        length = rng.randint(1, 8 - start)
        for i in range(start, start + length):
            groups[i] = 0
    address = ipaddress.IPv6Address(":".join("%x" % g for g in groups))
    full = address.exploded
    short = address.compressed
    if level == 3 and rng.random() < 0.5:
        fields = [("lang", "Ausgeschrieben (8 Blöcke à 4 Stellen)")]
        solution = {"lang": full}
        matchers = {"lang": _ipv6_text_matcher(full)}
        text = "Schreibe die IPv6-Adresse %s vollständig aus." % short
        steps = ["1. '::' steht für so viele Nullblöcke, dass es 8 Blöcke werden.",
                 "2. Jeden Block mit führenden Nullen auf 4 Stellen auffüllen.",
                 "Ergebnis: %s" % full]
    else:
        fields = [("kurz", "Kürzeste Schreibweise")]
        solution = {"kurz": short}
        matchers = {"kurz": _ipv6_text_matcher(short)}
        text = "Kürze die IPv6-Adresse %s so weit wie möglich." % full
        steps = ["1. Führende Nullen in jedem Block weglassen: %s"
                 % ":".join("%x" % g for g in groups),
                 "2. Den längsten Block aufeinanderfolgender Nullblöcke (mindestens "
                 "zwei) durch '::' ersetzen, bei Gleichstand den ersten.",
                 "3. '::' darf nur einmal vorkommen; Kleinbuchstaben verwenden.",
                 "Ergebnis: %s" % short]
    return TrainerTask("ipv6", level, text, fields, solution, steps, matchers)


# ============================================================================
#  Ab 0.63.1 (Plan 0.63 Abschnitt 4.5, Freigabe G-63-1): zwei neue Arten
#  "Netz aufteilen" und "Nach Hostbedarf". Gerechnet und erklaert wird mit
#  dem Rechenkern des Rechners (split_network, subnet_by_hosts und deren
#  Rechenwege). Die Handy-Fassung des Rechenwegs (hoechstens
#  CALC_EXPLAIN_HANDY_WIDTH Zeichen je Zeile) liegt als task.steps_schmal an
#  der Aufgabe (F-63-18 = S1); trainer_task bleibt unveraendert.
# ============================================================================

from fisi_core import (CALC_EXPLAIN_HANDY_WIDTH, de_int, hosts_explain,  # noqa: E402
                       ipv4_text, split_entry, split_explain, split_network,
                       subnet_addr_text, subnet_by_hosts, subnet_hosts_text,
                       subnet_net_text)
from fisi_core import _explain_list_indexes, _wrap_para  # noqa: E402

TRAINER_NAMES = ["Verwaltung", "Produktion", "Vertrieb", "Lager", "Technik", "Gäste-WLAN",
                 "Server", "Entwicklung", "Einkauf", "Buchhaltung"]


def _digits(text):
    return text != "" and all(char in "0123456789" for char in text)


def _prefix_matcher(expected):
    """Praefixlaenge als "/27" oder "27"."""
    def match(text):
        value = _clean(text)
        value = value[1:] if value.startswith("/") else value
        return _digits(value) and int(value) == expected
    return match


def _count_matcher(expected, power=False):
    """Ganze Zahl mit oder ohne Tausenderpunkte, mit power=True auch als
    Zweierpotenz "2^64". Nur die Ziffern 0 bis 9 (anders als _int_matcher)."""
    def match(text):
        value = _clean(text)
        if power and value.startswith("2^"):
            return _digits(value[2:]) and len(value) <= 6 and 2 ** int(value[2:]) == expected
        groups = value.split(".")
        if len(groups) > 1 and not (1 <= len(groups[0]) <= 3
                                    and all(len(group) == 3 for group in groups[1:])):
            return False                    # Punkte nur als Tausenderpunkte
        value = "".join(groups)
        return _digits(value) and int(value) == expected
    return match


def _trainer_v4_net(rng, prefix):
    """Zufaelliges privates IPv4-Netz mit diesem Praefix (als ganze Zahl)."""
    first = rng.choice([10] + [172] * (prefix >= 12) + [192] * (prefix >= 16))
    if first == 10:
        value = (10 << 24) | rng.getrandbits(24)
    elif first == 172:
        value = (172 << 24) | ((16 + rng.randint(0, 15)) << 16) | rng.getrandbits(16)
    else:
        value = (192 << 24) | (168 << 16) | rng.getrandbits(16)
    return value >> (32 - prefix) << (32 - prefix)


def _trainer_v6_net(rng, prefix):
    """Zufaelliges Netz im Dokumentationsbereich 2001:db8::/32."""
    value = 0x20010DB8 << 96
    if prefix > 32:
        value |= rng.getrandbits(prefix - 32) << (128 - prefix)
    return value


def _narrow_address(caption, address):
    """Handy: Adresse hinter caption, sonst an einem Doppelpunkt geteilt."""
    if len(caption + address) <= CALC_EXPLAIN_HANDY_WIDTH:
        return [caption + address]
    cut = address.find(":", len(address) // 2 - 3) + 1
    return [caption + address[:cut], "   " + address[cut:]]


def _split_nibble_lines(wanted, prefix, bits, nibble, schmal):
    """Vorueberlegung "an Nibble-Grenzen": von /neu auf die naechste 4-Bit-Grenze."""
    new, total, used = prefix + bits, de_int(1 << (nibble - prefix)), de_int(wanted)
    if schmal:
        return ["VORÜBERLEGUNG:", "NIBBLE-GRENZE",
                " %s Subnetze brauchen" % used,
                " k = %d Bit: /%d + %d = /%d" % (bits, prefix, bits, new),
                " /%d liegt nicht an einer" % new, " 4-Bit-Grenze (Nibble).",
                " Die nächste ist /%d." % nibble,
                " Dort entstehen 2^%d" % (nibble - prefix),
                " = %s Subnetze. Damit" % total, " geht es weiter; verwendet",
                " werden die ersten %s." % used, ""]
    return ["VORÜBERLEGUNG: NIBBLE-GRENZE",
            "   %s Subnetze brauchen k = %d Bit: /%d + %d = /%d."
            % (used, bits, prefix, bits, new),
            "   /%d liegt nicht an einer 4-Bit-Grenze (Nibble). Die nächste ist /%d."
            % (new, nibble),
            "   Dort entstehen 2^%d = %s Subnetze. Damit geht es weiter;"
            % (nibble - prefix, total),
            "   verwendet werden die ersten %s." % used, ""]


def _split_pick_lines(result, number, schmal):
    """Letzter Schritt: das gefragte Subnetz Nr. number aus Netz + (Nr. - 1) x Groesse."""
    version, size = result["version"], result["groesse"]
    entry = split_entry(result, number - 1)
    base = subnet_addr_text(version, result["netz"])
    net = subnet_addr_text(version, entry["netz"])
    end = subnet_addr_text(version, entry["ende"])
    size_text = de_int(size) if version == 4 else "2^%d" % (result["breite"] - result["neu"])
    end_caption = "Broadcast-Adresse" if version == 4 else "Letzte Adresse"
    bits = format(number - 1, "0%db" % result["k"]) if result["k"] else "0"
    if schmal:
        lines = ["", "SCHRITT 6: Gefragt ist", "Subnetz Nr. %d" % number]
        if version == 6:
            lines += [" Subnetz-Bits: %d - 1 = %d" % (number, number - 1),
                      " = binär %s" % bits]
        lines += [" Netzadresse = Nr. 1", " + (%d - 1) x %s" % (number, size_text)]
        if version == 4:
            lines += [" = %s" % base, " + %s" % de_int((number - 1) * size)]
        lines += _narrow_address(" = ", net)
        lines += [" %s" % end_caption, " = nächste Netzadresse - 1"]
        return lines + _narrow_address(" = ", end)
    lines = ["", "SCHRITT 6: Gefragt ist Subnetz Nr. %d" % number]
    if version == 6:
        lines.append("   Subnetz-Bits: %d - 1 = %d = binär %s" % (number, number - 1, bits))
    lines.append("   Netzadresse = Nr. 1 + (%d - 1) x %s Adressen" % (number, size_text))
    if version == 4:
        lines.append("   = %s + %s = %s" % (base, de_int((number - 1) * size), net))
        lines.append("   %s = nächste Netzadresse - 1 = %s" % (end_caption, end))
    else:
        lines += ["   = %s" % net, "   %s = nächste Netzadresse - 1" % end_caption,
                  "   = %s" % end]
    return lines


# 0.63.1 (Antwort 7 auf Meldung 10, Variante T): Der Trainer zeigt kein Ergebnis
# mit allen Subnetzen. Die Lueckenzeile des Rechenwegs sagt darum hier
# "(nicht einzeln aufgelistet)"; der Rechner (fisi_core) bleibt beim alten Satz.
TRAINER_GAP_OLD = "(alle im Ergebnis)"
TRAINER_GAP_NEW = "(nicht einzeln aufgelistet)"


def _split_gap_lines(result, steps, narrow):
    """Lueckenzeile im Trainer-Rechenweg ersetzen: am PC in der Zeile, am Handy
    den Absatz mit derselben Kern-Hilfe (_wrap_para, 28 Zeichen) neu umbrechen."""
    gap = _explain_list_indexes(result["anzahl"])[1]
    if not gap:
        return steps, narrow
    steps = [line.replace(TRAINER_GAP_OLD, TRAINER_GAP_NEW) for line in steps]
    text = "Subnetz %s bis %s: je + Schrittweite " % (de_int(gap[0]), de_int(gap[1]))
    old = _wrap_para(text + TRAINER_GAP_OLD, "", CALC_EXPLAIN_HANDY_WIDTH)
    new = _wrap_para(text + TRAINER_GAP_NEW, "", CALC_EXPLAIN_HANDY_WIDTH)
    for start in range(len(narrow) - len(old) + 1):
        if narrow[start:start + len(old)] == old:
            return steps, narrow[:start] + new + narrow[start + len(old):]
    return steps, narrow


def _split_task(rng, level):
    """Netz aufteilen: N gleich grosse Subnetze (Stufe 3 auch IPv6, zur Haelfte
    an Nibble-Grenzen)."""
    version = 6 if level == 3 and rng.random() < 0.5 else 4
    nibble = version == 6 and rng.random() < 0.5
    while True:
        if version == 4:
            prefix = 24 if level == 1 else rng.randint(*{2: (16, 23), 3: (8, 22)}[level])
            wanted = rng.randint(2, {1: 8, 2: 32, 3: 300}[level])
        else:
            prefix, wanted = rng.randint(32, 56), rng.randint(2, 300)
        bits = (wanted - 1).bit_length()
        new = prefix + bits
        if version == 4 and new <= 30:
            break
        if version == 6 and (not nibble or new % 4) and (new + 3) // 4 * 4 <= 64:
            break
    width = 32 if version == 4 else 128
    value = _trainer_v4_net(rng, prefix) if version == 4 else _trainer_v6_net(rng, prefix)
    net_text = subnet_net_text(version, value, prefix)
    number = rng.randint(2, wanted)
    if nibble:
        target = (new + 3) // 4 * 4
        result = split_network(net_text, 1 << (target - prefix), version)
        steps = _split_nibble_lines(wanted, prefix, bits, target, False)
        narrow = _split_nibble_lines(wanted, prefix, bits, target, True)
    else:
        result = split_network(net_text, wanted, version)
        steps, narrow = [], []
    steps += split_explain(result).split("\n") + _split_pick_lines(result, number, False)
    narrow += split_explain(result, True).split("\n") + _split_pick_lines(result, number, True)
    steps, narrow = _split_gap_lines(result, steps, narrow)
    entry = split_entry(result, number - 1)
    size = result["groesse"]
    if version == 4:
        fields = [("praefix", "Neue Präfixlänge"), ("maske", "Subnetzmaske"),
                  ("adressen", "Adressen je Subnetz"), ("hosts", "Nutzbare Hosts je Subnetz"),
                  ("netz", "Netzadresse des %d. Subnetzes (ohne Präfix)" % number),
                  ("broadcast", "Broadcast-Adresse des %d. Subnetzes" % number)]
        solution = {"maske": ipv4_text(result["maske"]), "adressen": de_int(size),
                    "hosts": de_int(result["hosts"]), "broadcast": ipv4_text(entry["ende"])}
        matchers = {"maske": _ip_matcher(ipaddress.IPv4Address(result["maske"])),
                    "adressen": _count_matcher(size, power=True),
                    "hosts": _count_matcher(result["hosts"]),
                    "broadcast": _ip_matcher(ipaddress.IPv4Address(entry["ende"]))}
        asked = ("neue Präfixlänge, Subnetzmaske, Adressen und nutzbare Hosts je Subnetz "
                 "sowie Netzadresse und Broadcast-Adresse des %d. Subnetzes" % number)
    else:
        fields = [("praefix", "Neue Präfixlänge"),
                  ("adressen", "Adressen je Subnetz (als 2^n)"),
                  ("netz", "Netzadresse des %d. Subnetzes (ohne Präfix)" % number),
                  ("letzte", "Letzte Adresse des %d. Subnetzes" % number)]
        solution = {"adressen": "2^%d" % (width - result["neu"]),
                    "letzte": subnet_addr_text(6, entry["ende"])}
        matchers = {"adressen": _count_matcher(size, power=True),
                    "letzte": _ip_matcher(ipaddress.IPv6Address(entry["ende"]))}
        asked = ("neue Präfixlänge, Adressen je Subnetz sowie Netzadresse und letzte "
                 "Adresse des %d. Subnetzes" % number)
    solution.update(praefix="/%d" % result["neu"],
                    netz=subnet_addr_text(version, entry["netz"]))
    matchers.update(praefix=_prefix_matcher(result["neu"]),
                    netz=_ip_matcher(ipaddress.ip_address(entry["netz"]) if version == 4
                                     else ipaddress.IPv6Address(entry["netz"])))
    text = ("Das Netz %s soll in %s gleich große Subnetze %saufgeteilt werden. "
            "Gib an: %s." % (net_text, de_int(wanted),
                             "an Nibble-Grenzen (4-Bit-Grenzen) " if nibble else "",
                             asked))
    task = TrainerTask("teilen", level, text, fields, solution, steps, matchers)
    task.steps_schmal = narrow
    return task


def _hosts_sizes(rng, capacity, count, full):
    """Blockgroessen (Zweierpotenzen ab 4), die ins Netz passen: das Netz so
    lange an einem zufaelligen Block halbieren, bis count (full: Summe genau
    die Netzgroesse, Rest 0) bzw. count + 1 Bloecke da sind; ohne full
    bleibt ein Block frei."""
    blocks = [capacity]
    while len(blocks) < count + (0 if full else 1):
        index = rng.choice([i for i, size in enumerate(blocks) if size >= 8])
        half = blocks.pop(index) // 2
        blocks += [half, half]
    if not full:
        blocks.pop(rng.randrange(len(blocks)))
    rng.shuffle(blocks)
    return blocks


def _hosts_task(rng, level):
    """Nach Hostbedarf: erst die Groessen, dann je Groesse ein Bedarf, fuer den
    genau diese Groesse die kleinste passende ist. Darum immer loesbar; etwa
    jede dritte Aufgabe fuellt das Netz genau (Rest 0)."""
    count = rng.randint(*{1: (2, 3), 2: (3, 4), 3: (4, 6)}[level])
    prefix = 24 if level == 1 else rng.choice({2: [23, 24], 3: [22, 23]}[level])
    sizes = _hosts_sizes(rng, 1 << (32 - prefix), count, rng.random() < 1 / 3)
    needs = [rng.randint(max(1, size // 2 - 1), size - 2) for size in sizes]
    names = rng.sample(TRAINER_NAMES, count)
    net_text = subnet_net_text(4, _trainer_v4_net(rng, prefix), prefix)
    result = subnet_by_hosts(net_text, list(zip(names, needs)), 4)
    subnets, order = result["subnetze"], result["reihenfolge"]
    number = rng.randint(1, count)
    fields, solution, matchers = [], {}, {}
    for index, item in enumerate(subnets):
        net = ipaddress.IPv4Network((item["netz"], item["praefix"]))
        fields += [("netz%d" % index, "%s (%s): Netzadresse/Präfix"
                    % (item["name"], subnet_hosts_text(item["bedarf"]))),
                   ("maske%d" % index, "%s: Subnetzmaske" % item["name"])]
        solution["netz%d" % index] = str(net)
        solution["maske%d" % index] = ipv4_text(item["maske"])
        matchers["netz%d" % index] = _network_matcher(net)
        matchers["maske%d" % index] = _ip_matcher(net.netmask)
    asked = subnets[order[number - 1]]["broadcast"]
    fields += [("broadcast", "Broadcast-Adresse des %d. vergebenen Subnetzes" % number),
               ("rest", "Freier Rest (Anzahl Adressen)")]
    solution.update(broadcast=ipv4_text(asked), rest=de_int(result["rest"]))
    matchers.update(broadcast=_ip_matcher(ipaddress.IPv4Address(asked)),
                    rest=_count_matcher(result["rest"]))
    wants = ", ".join("%s: %s" % (item["name"], subnet_hosts_text(item["bedarf"]))
                      for item in subnets)
    text = ("Das Netz %s soll nach Hostbedarf aufgeteilt werden: %s. Vergeben wird "
            "lückenlos ab der ersten Adresse, das größte Subnetz zuerst. Gib je "
            "Subnetz Netzadresse/Präfix und Subnetzmaske an, dazu die Broadcast-Adresse "
            "des %d. vergebenen Subnetzes und den freien Rest in Adressen."
            % (net_text, wants, number))
    task = TrainerTask("bedarf", level, text, fields, solution,
                       hosts_explain(result).split("\n"), matchers)
    task.steps_schmal = hosts_explain(result, True).split("\n")
    return task


TRAINER_BUILDERS = {"ipv4": _ipv4_task, "vlsm": _vlsm_task, "zahlen": _number_task,
                    "ipv6": _ipv6_task, "teilen": _split_task, "bedarf": _hosts_task}


def trainer_task(kind, level, seed, schmal=False):
    """Eine Aufgabe, durch kind, level und seed eindeutig festgelegt.
    schmal=True (ab 0.62.3, nur das Handy): Schritt 3 der IPv4-Aufgaben
    Oktett fuer Oktett; Aufgabe, Loesung und alle anderen Schritte gleich."""
    rng = random.Random("%s-%d-%s" % (kind, level, seed))
    if kind == "ipv4":
        return _ipv4_task(rng, level, schmal)
    return TRAINER_BUILDERS[kind](rng, level)


def trainer_round(kind, level, seed, count=TRAINER_ROUND, schmal=False):
    """Eine Runde mit count Aufgaben (fester Startwert seed)."""
    return [trainer_task(kind, level, "%s-%d" % (seed, number), schmal)
            for number in range(count)]


def trainer_summary(results):
    """Zusammenfassung einer Runde: results = Liste True/False."""
    right = sum(1 for value in results if value)
    return "%d von %d Aufgaben richtig" % (right, len(results))
