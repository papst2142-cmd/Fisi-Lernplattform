#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fachinformatiker Lernplattform - Klausursimulation (ab 0.51, ohne Oberflaeche)
==============================================================================

Pruefungen nach dem Aufbau der Fachinformatiker-Ausbildungsverordnung 2020
(FIAusbV, §§ 9, 19-25) und der IHK-Praxis, abgestimmt mit Nico am
01.10.2026 (Konzept_0.51.md):

  AP1        Einrichten eines IT-gestuetzten Arbeitsplatzes   90 Min  20 %
  Projekt    Planen und Umsetzen eines Projektes              -       50 %
  Konzeption Konzeption und Administration von IT-Systemen    90 Min  10 %
  Netzwerke  Analyse und Entwicklung von Netzwerken           90 Min  10 %
  WiSo       Wirtschafts- und Sozialkunde                     60 Min  10 %

Offene Aufgaben: 4 Aufgaben zu je 25 Punkten, keine Abwahl, die Punkte
verteilen sich auf die Teilaufgaben. Bewertet wird nach der Abgabe selbst,
mit einer Kriterien-Checkliste aus der Musterloesung. WiSo: 30 gebundene
Aufgaben (Auswahlfragen), automatisch bewertet. Keine Pause (Nicos Wunsch):
die Zeit laeuft nach der Uhr weiter, auch wenn die App zu ist.

Die laufende Pruefung liegt je Geraet in einstellungen.json, das Ergebnis
in der Tabelle pruefungen (wird abgeglichen).
"""

import datetime
import difflib
import math
import random
import re
import time

from fisi_core import (AP1_SZENARIEN, QUESTION_RENAMES, QUIZ_QUESTIONS, SZENARIEN, ihk_note,
                       plural)

TASK_POINTS = 25
WISO_COUNT = 30

AP1 = "ap1"
KONZEPTION = "konzeption"
NETZWERKE = "netzwerke"
WISO = "wiso"

# (art, Kurzname, voller Name, Minuten, Quelle, Themen je Aufgabe)
EXAMS = [
    {"art": AP1, "kurz": "AP1", "minuten": 90, "quelle": "ap1",
     "name": "AP1 · Einrichten eines IT-gestützten Arbeitsplatzes",
     "themen": [["Rechnertechnik & Zahlensysteme"], ["Rechnernetze Grundlagen"],
                ["Datenschutz & Sicherheit"],
                # ab 0.55: Arbeitsplatz einrichten (LF 2, § 9 Abs. 2) im selben Platz
                ["Projektplanung", "Arbeitsplatz einrichten: Bedarf, Beschaffung, Übergabe"]]},
    {"art": KONZEPTION, "kurz": "Konzeption", "minuten": 90, "quelle": "ap2",
     "name": "AP2 · Konzeption und Administration von IT-Systemen",
     # vier verschiedene Themen aus dem Pool, zufaellig (ab 0.55 sieben
     # Themen: Systemadministration und Automatisierung nach § 21)
     "themen": "4ausPool",
     "pool": ["Storage & RAID", "Virtualisierung", "IT-Sicherheit", "Projektmanagement",
              "Wirtschaft & Beratung", "Systemadministration", "Automatisierung & Skripte"]},
    {"art": NETZWERKE, "kurz": "Netzwerke", "minuten": 90, "quelle": "ap2",
     "name": "AP2 · Analyse und Entwicklung von Netzwerken",
     "themen": [["Subnetting & Routing"], ["Subnetting & Routing"], ["Netzwerkdesign"],
                ["IT-Sicherheit"]]},
    {"art": WISO, "kurz": "WiSo", "minuten": 60, "quelle": "quiz",
     "name": "AP2 · Wirtschafts- und Sozialkunde",
     "quiz_themen": ["recht", "arbeitswelt"]},
]
EXAM = {exam["art"]: exam for exam in EXAMS}
EXAM_TABS = [(exam["art"], exam["kurz"]) for exam in EXAMS]

# Gewichtung im Gesamtergebnis (§ 24 Abs. 1 FIAusbV)
WEIGHTS = {AP1: 20, "projekt": 50, KONZEPTION: 10, NETZWERKE: 10, WISO: 10}
PART2 = ["projekt", KONZEPTION, NETZWERKE, WISO]
AREA_NAME = {AP1: "AP1 (Teil 1)", "projekt": "Projekt", KONZEPTION: "Konzeption",
             NETZWERKE: "Netzwerke", WISO: "WiSo"}

_SUBTASK = re.compile(r"^\s*(\d+)\.\s*")


# ============================================================================
#  AUFGABEN AUFBEREITEN
# ============================================================================

def split_numbered(lines):
    """(Einleitung, [Teil 1, Teil 2, ...]) aus Zeilen mit "1. ...", "2. ..."."""
    if isinstance(lines, str):
        lines = lines.split("\n")
    intro, parts = [], []
    for line in lines:
        if _SUBTASK.match(line):
            parts.append([_SUBTASK.sub("", line, count=1)])
        elif parts:
            parts[-1].append(line)
        else:
            intro.append(line)
    clean = ["\n".join(part).strip() for part in parts]
    return "\n".join(intro).strip(), clean


def subtask_points(count, total=TASK_POINTS):
    """Punkte je Teilaufgabe, Summe total (3 Teile: 9/8/8)."""
    base, rest = divmod(total, count)
    return [base + (1 if number < rest else 0) for number in range(count)]


_ABBREVIATIONS = ("z.B.", "z. B.", "d.h.", "d. h.", "ca.", "bzw.", "u.a.", "usw.", "ggf.",
                  "inkl.", "Nr.", "evtl.", "vgl.", "bspw.", "max.", "min.", "o.ä.", "u.U.",
                  "Abs.", "Std.", "Min.", "Mio.", "Tsd.", "etc.", "z.T.")


def criteria(text):
    """Bewertungskriterien aus einer Musterloesung: jeder Satz bzw. jede
    Aufzaehlungszeile ein Kriterium."""
    items = []
    for line in text.split("\n"):
        line = line.strip().lstrip("-•*").strip()
        if not line:
            continue
        protected = line
        for number, abbreviation in enumerate(_ABBREVIATIONS):
            protected = protected.replace(abbreviation, "\x00%d\x00" % number)
        protected = re.sub(r"(\d)\.(\d)", "\\1\x01\\2", protected)
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ0-9„\"(])", protected):
            for number, abbreviation in enumerate(_ABBREVIATIONS):
                sentence = sentence.replace("\x00%d\x00" % number, abbreviation)
            sentence = sentence.replace("\x01", ".").strip()
            if len(sentence) > 2:
                items.append(sentence)
    return items or [text.strip()]


def scenario_parts(scenario):
    """Aufbereitete Aufgabe: Einleitung, Teilaufgaben mit Punkten und
    Musterloesung. None, wenn Aufgaben und Loesungen nicht zusammenpassen."""
    intro, tasks = split_numbered(scenario["text"])
    _intro, solutions = split_numbered(scenario["solution"])
    if not tasks or len(tasks) != len(solutions):
        return None
    points = subtask_points(len(tasks))
    return {"titel": scenario["title"], "thema": scenario["theme"], "einleitung": intro,
            "teile": [{"text": task, "punkte": value, "loesung": solution,
                       "kriterien": criteria(solution)}
                      for task, solution, value in zip(tasks, solutions, points)]}


def source_data(source):
    return AP1_SZENARIEN if source == "ap1" else SZENARIEN


def usable_indices(source, theme):
    """Aufgaben eines Themas, die sich fuer die Pruefung eignen."""
    return [index for index, scenario in enumerate(source_data(source))
            if scenario["theme"] == theme and scenario_parts(scenario) is not None]


def wiso_pool(exam=None):
    exam = exam or EXAM[WISO]
    return [question["q"] for question in QUIZ_QUESTIONS
            if question.get("thema") in exam["quiz_themen"]]


# ============================================================================
#  PRUEFUNG ZUSAMMENSTELLEN
# ============================================================================

def used_items(history, art):
    """Bereits gestellte Aufgaben/Fragen dieses Pruefungsbereichs."""
    used = set()
    for entry in history:
        if entry.get("art") != art:
            continue
        details = entry.get("daten") or {}
        for task in details.get("aufgaben", []):
            used.add(task.get("index"))
        for question in details.get("fragen", []):
            used.add(question.get("q") if isinstance(question, dict) else question)
    return used


def _pick(rng, candidates, used, taken):
    """Bevorzugt noch nie gestellte Aufgaben; ist der Vorrat aufgebraucht,
    kommen wieder alle in Frage. Nie zweimal dieselbe in einer Pruefung."""
    free = [item for item in candidates if item not in used and item not in taken]
    if not free:
        free = [item for item in candidates if item not in taken]
    return rng.choice(free) if free else None


def new_exam(art, history=(), seed=None, now=None):
    """Neue Pruefung als dict (wird so gespeichert, bis sie bewertet ist)."""
    exam = EXAM[art]
    rng = random.Random(seed)
    used = used_items(history, art)
    now = (now or datetime.datetime.now()).replace(microsecond=0)
    # "start_utc" (ab 0.53): Sekunden seit 1970 (UTC), unabhaengig von
    # Sommer-/Winterzeit; "start" bleibt fuer Anzeige und aeltere Versionen
    state = {"art": art, "start": now.strftime("%Y-%m-%d %H:%M:%S"),
             "start_utc": int(now.timestamp()),
             "minuten": exam["minuten"], "phase": "laeuft", "antworten": {},
             "punkte": {}, "kriterien": {}}
    if art == WISO:
        pool = wiso_pool(exam)
        fresh = [q for q in pool if q not in used]
        questions = rng.sample(fresh, min(len(fresh), WISO_COUNT))
        if len(questions) < WISO_COUNT:
            rest = [q for q in pool if q not in questions]
            questions += rng.sample(rest, min(len(rest), WISO_COUNT - len(questions)))
        rng.shuffle(questions)
        state["fragen"] = questions
        state["optionen"] = {}
        by_question = {q["q"]: q for q in QUIZ_QUESTIONS}
        for question in questions:
            options = list(by_question[question]["options"])
            rng.shuffle(options)
            state["optionen"][question] = options
        return state
    themes = exam["themen"]
    if themes == "4ausPool":
        themes = [[theme] for theme in rng.sample(exam["pool"], 4)]
    tasks, taken = [], set()
    for choice in themes:
        theme = rng.choice(choice)
        index = _pick(rng, usable_indices(exam["quelle"], theme), used, taken)
        if index is None:
            continue
        taken.add(index)
        tasks.append({"quelle": exam["quelle"], "index": index})
    state["aufgaben"] = tasks
    return state


def task_details(state, number):
    """Aufbereitete Aufgabe number (0-basiert) einer Pruefung."""
    task = state["aufgaben"][number]
    return scenario_parts(source_data(task["quelle"])[task["index"]])


def answer_key(number, part):
    return "%d-%d" % (number, part)


# ============================================================================
#  ZEIT
# ============================================================================

def deadline(state):
    start = datetime.datetime.strptime(state["start"], "%Y-%m-%d %H:%M:%S")
    return start + datetime.timedelta(minutes=state["minuten"])


def _timestamp(moment):
    """Zeitpunkt (datetime, auch naive Ortszeit) als Sekunden seit 1970."""
    return moment.timestamp() if moment is not None else time.time()


def elapsed_seconds(state, now=None):
    """Seit dem Start vergangene Sekunden (ab 0.53 ueber UTC, damit die
    Zeitumstellung keine Stunde schenkt oder wegnimmt). Aeltere gespeicherte
    Pruefungen haben nur "start" (Ortszeit) - die wird mit der Zeitzone des
    Geraets umgerechnet. Nie negativ (Uhr zurueckgestellt)."""
    start = state.get("start_utc")
    if not isinstance(start, (int, float)):
        start = datetime.datetime.strptime(state["start"], "%Y-%m-%d %H:%M:%S").timestamp()
    return max(0.0, _timestamp(now) - start)


def seconds_left(state, now=None):
    total = state["minuten"] * 60
    return max(0, min(total, int(total - elapsed_seconds(state, now))))


def time_text(seconds):
    return "%d:%02d:%02d" % (seconds // 3600, seconds % 3600 // 60, seconds % 60) \
        if seconds >= 3600 else "%02d:%02d" % (seconds // 60, seconds % 60)


def submit(state, now=None):
    """Abgeben: Zeit festhalten, bei WiSo gleich auswerten."""
    state["dauer"] = min(state["minuten"] * 60, int(elapsed_seconds(state, now)))
    state["phase"] = "bewertung"
    return state


# ============================================================================
#  BEWERTUNG
# ============================================================================

def suggested_points(max_points, checked):
    """Punktevorschlag aus abgehakten Kriterien (Liste True/False)."""
    if not checked:
        return 0
    return int(round(max_points * sum(1 for value in checked if value) / len(checked)))


def wiso_result(state):
    """[(frage, gewaehlt, richtig, ist_richtig)]. Ab 0.63.2: alte Fragetexte
    (inhalte/umbenennungen.json) zaehlen beim neuen Text; eine Frage, die es
    nicht mehr gibt, bleibt stehen und zaehlt als nicht richtig (vorher
    KeyError, die Pruefung liess sich nicht abgeben)."""
    by_question = {q["q"]: q for q in QUIZ_QUESTIONS}
    rows = []
    for question in state["fragen"]:
        chosen = state["antworten"].get(question, "")
        current = current_question(question)
        right = by_question[current]["a"] if current in by_question else ""
        rows.append((current, chosen, right, bool(right) and chosen == right))
    return rows


def evaluate(state):
    """Gesamtergebnis einer bewerteten Pruefung: dict mit punkte (0-100),
    note, aufgaben/fragen und themen {thema: [erreicht, moeglich]}."""
    themes = {}
    if state["art"] == WISO:
        # Ab 0.63.2 (Nacharbeit S4, L2): eine Frage, die es nicht mehr gibt
        # (weder im Inhalt noch in umbenennungen.json), senkt die Punkte nicht:
        # sie zaehlt weder im Nenner noch bei den Themen, bleibt aber unter
        # "unbekannt" im gespeicherten Ergebnis stehen.
        known = {q["q"] for q in QUIZ_QUESTIONS}
        all_rows = wiso_result(state)
        rows = [row for row in all_rows if row[0] in known]
        unknown = [row[0] for row in all_rows if row[0] not in known]
        right = sum(1 for row in rows if row[3])
        points = round(100.0 * right / max(1, len(rows)), 1)
        topics = {q["q"]: q.get("thema") for q in QUIZ_QUESTIONS}
        for question, _chosen, _right, ok in rows:
            name = "Recht & Verträge" if topics.get(question) == "recht" else "Arbeitswelt"
            entry = themes.setdefault(name, [0, 0])
            entry[0] += 1 if ok else 0
            entry[1] += 1
        details = {"fragen": [{"q": q, "richtig": ok} for q, _c, _r, ok in rows],
                   "richtig": right}
        if unknown:
            details["unbekannt"] = unknown
    else:
        tasks, total = [], 0
        for number, task in enumerate(state["aufgaben"]):
            parts = task_details(state, number)
            reached = 0
            for part_number, part in enumerate(parts["teile"]):
                value = state["punkte"].get(answer_key(number, part_number), 0)
                reached += max(0, min(part["punkte"], int(value)))
            maximum = sum(part["punkte"] for part in parts["teile"])
            total += reached
            entry = themes.setdefault(parts["thema"], [0, 0])
            entry[0] += reached
            entry[1] += maximum
            tasks.append({"quelle": task["quelle"], "index": task["index"],
                          "titel": parts["titel"], "thema": parts["thema"],
                          "punkte": reached, "max": maximum})
        points = float(total)
        details = {"aufgaben": tasks}
    details["themen"] = themes
    details["minuten"] = state["minuten"]
    return {"punkte": points, "note": ihk_note(points), "daten": details,
            "dauer": state.get("dauer", 0)}


def weak_topics(result):
    """Themen unter 50 %, schwaechstes zuerst."""
    rows = [(reached / maximum if maximum else 0, name)
            for name, (reached, maximum) in result["daten"]["themen"].items()]
    return [name for share, name in sorted(rows) if share < 0.5]



def latest_weak(exams):
    """Schwache Themen der juengsten Pruefung (ab 0.54, "Jetzt ueben" im
    Fortschritt): (Ueberschrift, [themen]) oder (None, []), wenn die letzte
    Pruefung keine Schwaechen hatte. exams wie DBManager.exams (neueste
    zuerst)."""
    if not exams:
        return None, []
    entry = exams[0]
    try:
        weak = weak_topics({"daten": {"themen": entry["daten"].get("themen") or {}}})
    except (AttributeError, TypeError, ValueError, ZeroDivisionError):
        return None, []
    if not weak:
        return None, []
    exam = EXAM.get(entry["art"])
    stamp = str(entry.get("timestamp", ""))
    day = "%s.%s.%s" % (stamp[8:10], stamp[5:7], stamp[:4]) if len(stamp) >= 10 else ""
    return ("Üben (letzte Prüfung: %s%s)" % (exam["kurz"] if exam else entry["art"],
                                             ", " + day if day else ""), weak)

# ============================================================================
#  GESAMTERGEBNIS (§ 24, § 25 FIAusbV)
# ============================================================================

def latest_results(history):
    """{art: punkte} der jeweils letzten Simulation (history: neueste zuerst)."""
    latest = {}
    for entry in history:
        latest.setdefault(entry["art"], entry["punkte"])
    return latest


def _abrunden(wert):
    """Auf eine Nachkommastelle abrunden (ab 0.63.1, B-C-01): Die Kachel zeigt
    nie mehr, als Note und Regeln werten (49,97 -> 49,9, nicht 50). Vorher auf
    9 Stellen runden, damit Gleitkomma-Reste (49,99999999999999) nicht kippen."""
    return math.floor(round(wert, 9) * 10) / 10


def overall(scores):
    """Gesamtergebnis aus {bereich: punkte} (bereiche aus WEIGHTS). Fehlt ein
    Bereich, ist das Ergebnis unvollstaendig (complete False).
    Liefert dict: gesamt, teil2, complete, bestanden, regeln [(text, erfuellt)],
    ergaenzung (Hinweis oder "")."""
    complete = all(area in scores for area in WEIGHTS)
    if not complete:
        return {"complete": False, "fehlend": [AREA_NAME[a] for a in WEIGHTS
                                               if a not in scores]}
    total = sum(scores[area] * weight for area, weight in WEIGHTS.items()) / 100.0
    part2 = sum(scores[area] * WEIGHTS[area] for area in PART2) / \
        sum(WEIGHTS[area] for area in PART2)
    rules = _rules(scores)
    passed = all(ok for _text, ok in rules)
    hint = ""
    if not passed:
        hint = _supplement_hint(scores)
    return {"complete": True, "gesamt": _abrunden(total), "teil2": _abrunden(part2),
            "note": ihk_note(total), "regeln": rules, "bestanden": passed,
            "ergaenzung": hint}


def _rules(scores):
    total = sum(scores[area] * weight for area, weight in WEIGHTS.items()) / 100.0
    part2 = sum(scores[area] * WEIGHTS[area] for area in PART2) / \
        sum(WEIGHTS[area] for area in PART2)
    sufficient = sum(1 for area in PART2 if scores[area] >= 50)
    return [
        ("Gesamtergebnis Teil 1 und 2 mindestens ausreichend (50)", total >= 50),
        ("Ergebnis Teil 2 mindestens ausreichend (50)", part2 >= 50),
        ("Mindestens drei Bereiche von Teil 2 ausreichend (%d von 4)" % sufficient,
         sufficient >= 3),
        ("Kein Bereich von Teil 2 ungenügend (unter 30)",
         all(scores[area] >= 30 for area in PART2)),
    ]


def _supplement_hint(scores):
    """Mündliche Ergaenzungspruefung (§ 25): nur Konzeption, Netzwerke oder
    WiSo, nur bei schlechter als ausreichend, Gewichtung alt:muendlich 2:1.
    Prueft, ob die bestmoegliche Ergaenzungspruefung das Bestehen bringt."""
    options = []
    for area in (KONZEPTION, NETZWERKE, WISO):
        if scores[area] >= 50:
            continue
        best = dict(scores)
        best[area] = (2 * scores[area] + 100) / 3.0
        if all(ok for _text, ok in _rules(best)):
            # Mindestpunktzahl in der muendlichen Pruefung suchen
            for oral in range(0, 101):
                trial = dict(scores)
                trial[area] = (2 * scores[area] + oral) / 3.0
                if all(ok for _text, ok in _rules(trial)):
                    options.append((oral, AREA_NAME[area]))
                    break
    if not options:
        return ("Eine mündliche Ergänzungsprüfung würde hier nicht reichen (nur in "
                "Konzeption, Netzwerke oder WiSo möglich, Gewichtung 2:1).")
    oral, name = min(options)
    return ("Eine mündliche Ergänzungsprüfung in %s könnte reichen: Dafür wären dort "
            "mindestens %s nötig (alt zu mündlich 2:1)."
            % (name, plural(oral, "Punkt", "Punkte")))


# ============================================================================
#  LAUFENDE PRUEFUNG (je Geraet) UND ABSCHLUSS
# ============================================================================

RUNNING_KEY = "laufende_pruefung"


def load_running():
    """Die laufende bzw. noch nicht bewertete Pruefung dieses Geraets oder None.
    Ab 0.63.2 an korrigierte Lerninhalte angepasst (migrate_running)."""
    from fisi_update import load_settings
    state = load_settings().get(RUNNING_KEY)
    if not isinstance(state, dict) or state.get("art") not in EXAM:
        return None
    return migrate_running(state)


def current_question(question):
    """Heutiger Fragetext einer Quizfrage (folgt inhalte/umbenennungen.json,
    auch ueber mehrere Umbenennungen)."""
    renames = QUESTION_RENAMES.get("quiz_answers") or {}
    seen = set()
    while question in renames and question not in seen:
        seen.add(question)
        question = renames[question]
    return question


def migrate_running(state):
    """Ab 0.63.2 (Nacharbeit S4): Eine Pruefung, die beim Update lief, liegt
    mit den Texten der alten Version in einstellungen.json. Hier wird sie an
    die heutigen Inhalte angepasst, ohne etwas zu verwerfen:
    WiSo - alte Fragetexte -> neue (umbenennungen.json) in fragen, antworten
    und optionen; ist genau eine Antwortmoeglichkeit umformuliert, wird sie
    (und eine gewaehlte Antwort) auf den neuen Text gesetzt. Unbekanntes
    bleibt unveraendert stehen.
    AP1/AP2 - hat eine Musterloesung jetzt mehr Kriterien, wird die Liste der
    Haken mit "nicht abgehakt" verlaengert (vorher IndexError beim Abhaken);
    gesetzte Haken und vergebene Punkte bleiben.
    Gespeichert wird erst beim naechsten save_running (kein Schreiben hier)."""
    try:
        if state.get("art") == WISO:
            _migrate_wiso(state)
        else:
            _migrate_tasks(state)
    except Exception:        # im Zweifel die Pruefung so lassen, wie sie war
        pass
    return state


def _migrate_wiso(state):
    by_question = {q["q"]: q for q in QUIZ_QUESTIONS}
    answers, options = state.get("antworten") or {}, state.get("optionen") or {}
    questions = []
    for old in state.get("fragen") or []:
        new = current_question(old)
        if new != old and new not in answers and old in answers:
            answers[new] = answers.pop(old)
        if new != old and new not in options and old in options:
            options[new] = options.pop(old)
        questions.append(new)
        item = by_question.get(new)
        stored = options.get(new)
        if item is None or not isinstance(stored, list):
            continue
        gone = [text for text in stored if text not in item["options"]]
        added = [text for text in item["options"] if text not in stored]
        if len(gone) == 1 and len(added) == 1:
            options[new] = [added[0] if text == gone[0] else text for text in stored]
            if answers.get(new) == gone[0]:
                answers[new] = added[0]
    state["fragen"] = questions
    state["antworten"], state["optionen"] = answers, options


def _migrate_tasks(state):
    marks = state.get("kriterien")
    if not isinstance(marks, dict):
        return
    for number, task in enumerate(state.get("aufgaben") or []):
        details = task_details(state, number)
        if details is None:
            continue
        for part_number, part in enumerate(details["teile"]):
            key = answer_key(number, part_number)
            checked = marks.get(key)
            if not isinstance(checked, list) or len(checked) >= len(part["kriterien"]):
                continue
            old = CRITERIA_BEFORE.get((task.get("quelle"), task.get("index"), part_number))
            if old is not None and len(old) == len(checked):
                marks[key] = align_marks(checked, old, part["kriterien"])
            else:
                # unbekannte Aenderung: Haken behalten, Rest "nicht abgehakt"
                checked.extend([False] * (len(part["kriterien"]) - len(checked)))


# Ab 0.63.2 (Nacharbeit S4, M1): Kriterien der Musterloesungen, die in 0.63.2
# laenger wurden, im Stand 0.63.1 (Schluessel: Quelle, Index, Teilaufgabe).
# Damit stehen die Haken einer beim Update laufenden Pruefung wieder beim
# richtigen Kriterium (A2-135: neues Kriterium an Position 3, nicht hinten).
CRITERIA_BEFORE = {
    ("ap1", 4, 2): [
        "Damit ein lokales Ereignis wie Brand, Diebstahl oder ein Wasserschaden nicht "
        "gleichzeitig Originaldaten und alle Sicherungskopien vernichtet (Prinzip des Air Gap)."],
    ("ap1", 58, 2): [
        "Nach Arbeitsende gilt eine ununterbrochene Ruhezeit von mindestens 11 Stunden, also "
        "frühestens am nächsten Tag um 7:00 Uhr."],
    ("ap2", 134, 0): [
        "Erste Meldung: 24 Stunden nach Kenntnis, also bis Samstag, 03.10.2026, 22:40 Uhr "
        "(dass der 3.",
        "Oktober ein Feiertag ist, spielt keine Rolle).",
        "Meldung: 72 Stunden nach Kenntnis, bis Montag, 05.10.2026, 22:40 Uhr.",
        "Die Meldung um 15:00 Uhr ist rechtzeitig.",
        "Abschlussmeldung: einen Monat nach der Meldung, also bis 05.11.2026."],
}


def align_marks(checked, old, new):
    """Haken (zu den Kriterien old) auf die Kriterien new uebertragen. Nur fuer
    die von Hand geprueften Eintraege in CRITERIA_BEFORE gedacht: gleiche
    Kriterien behalten ihren Haken, ein umformuliertes behaelt den Haken an
    seiner Stelle, neu eingefuegte sind "nicht abgehakt". Grundsatz: nie einen
    fremden Haken setzen. Der Haken eines weggefallenen Kriteriums faellt weg
    (wandert nicht weiter); gesetzte Punkte und der Lernstand bleiben
    unberuehrt."""
    result = []
    matcher = difflib.SequenceMatcher(None, old, new, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "insert":
            result.extend([False] * (j2 - j1))
        elif tag in ("equal", "replace"):
            # der Reihe nach; fehlende "nicht abgehakt", ueberzaehlige fallen weg
            width = j2 - j1
            block = list(checked[i1:i2])[:width]
            result.extend(block + [False] * (width - len(block)))
        # "delete": Haken des weggefallenen Kriteriums faellt weg
    return result


def save_running(state):
    from fisi_update import load_settings, save_settings
    settings = load_settings()
    settings[RUNNING_KEY] = state
    return save_settings(settings)


def clear_running():
    from fisi_update import load_settings, save_settings
    settings = load_settings()
    settings.pop(RUNNING_KEY, None)
    return save_settings(settings)


def finish(db, state):
    """Bewertete Pruefung speichern: Ergebnis in pruefungen, jede Aufgabe
    zusaetzlich als "Gewusst" (ab 50 % der Punkte) bzw. "Nicht gewusst" in
    den Notizblock, WiSo-Fragen als Antworten im Pruefungstrainer (zaehlen
    damit auch fuer Wiederholung und Tagesziel). Liefert das Ergebnis."""
    result = evaluate(state)
    if state["art"] == WISO:
        by_question = {q["q"]: q for q in QUIZ_QUESTIONS}
        for question, _chosen, _right, ok in wiso_result(state):
            if question in by_question:     # ab 0.63.2: unbekannte Frage nicht loggen
                db.log_quiz_answer(by_question[question]["cat"], question, ok)
    else:
        for task in result["daten"]["aufgaben"]:
            known = task["punkte"] * 2 >= task["max"]
            scenario = source_data(task["quelle"])[task["index"]]
            if task["quelle"] == "ap1":
                db.log_ap1(task["index"], scenario["title"], scenario["theme"], known)
            else:
                db.log_scenario(task["index"], scenario["title"], scenario["theme"], known)
    db.save_exam(state["art"], result["punkte"], result["note"], result["dauer"],
                 result["daten"])
    clear_running()
    return result
