#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FISI Lernplattform - Lernwerkzeuge ab 0.51 (ohne Oberflaeche)
=============================================================

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


def _stable_rank(source, key):
    """Feste, auf allen Geraeten gleiche Reihenfolge fuer den Altbestand."""
    return hashlib.md5(("%s|%s" % (source, key)).encode("utf-8")).hexdigest()


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
    # AP2 (Szenario-Themen)
    "Subnetting & Routing": ["ipv4", "ipv6", "routing"],
    "IT-Sicherheit": ["isms", "krypto", "zugriff", "angriffe", "netzsicherheit", "haertung"],
    "Storage & RAID": ["storage", "notfall"],
    "Netzwerkdesign": ["switching", "wlan", "verkabelung", "wan_vpn", "grundlagen"],
    "Wirtschaft & Beratung": ["kalkulation", "beschaffung", "beratung", "service"],
    "Virtualisierung": ["virtualisierung"],
    "Projektmanagement": ["projekt"],
    # AP1
    "Rechnertechnik & Zahlensysteme": ["hardware", "zahlen"],
    "Rechnernetze Grundlagen": ["grundlagen", "ipv4", "dienste", "verkabelung"],
    "Datenschutz & Sicherheit": ["datenschutz", "zugriff", "angriffe"],
    "Projektplanung": ["projekt"],
    "Wirtschafts- und Sozialkunde": ["recht", "arbeitswelt"],
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
    parts = []
    for source in (SRC_QUIZ, SRC_CARD):
        keys = list(pools[source])
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
        what = plural(count, "Quizfrage", "Quizfragen")
    return "Zum selben Thema gibt es noch %s. Jetzt weiterüben?" % what


# ============================================================================
#  SUBNETTING-TRAINER
# ============================================================================

TRAINER_KINDS = [
    ("ipv4", "IPv4-Subnetz"),
    ("vlsm", "VLSM"),
    ("zahlen", "Binär/Hex/Dezimal"),
    ("ipv6", "IPv6 kürzen"),
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


def _ipv4_task(rng, level):
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
              ("broadcast", "Broadcast"), ("erste", "Erster Host"),
              ("letzte", "Letzter Host"), ("hosts", "Nutzbare Hosts")]
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
        "3. Adresse binär:  %s" % _dotted_binary(address),
        "   Maske binär:    %s" % _dotted_binary(network.netmask),
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
        "4. Broadcast: alle Hostbits auf 1 = %s" % network.broadcast_address,
        "5. Hostbereich: %s bis %s (Netzadresse + 1 bis Broadcast - 1)"
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
                     "Broadcast %s" % (number, departments[index], wanted[index],
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
        terms = ["%s·16^%d" % (digit, len(hex_digits) - 1 - i)
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


TRAINER_BUILDERS = {"ipv4": _ipv4_task, "vlsm": _vlsm_task, "zahlen": _number_task,
                    "ipv6": _ipv6_task}


def trainer_task(kind, level, seed):
    """Eine Aufgabe, durch kind, level und seed eindeutig festgelegt."""
    rng = random.Random("%s-%d-%s" % (kind, level, seed))
    return TRAINER_BUILDERS[kind](rng, level)


def trainer_round(kind, level, seed, count=TRAINER_ROUND):
    """Eine Runde mit count Aufgaben (fester Startwert seed)."""
    return [trainer_task(kind, level, "%s-%d" % (seed, number)) for number in range(count)]


def trainer_summary(results):
    """Zusammenfassung einer Runde: results = Liste True/False."""
    right = sum(1 for value in results if value)
    return "%d von %d Aufgaben richtig" % (right, len(results))
