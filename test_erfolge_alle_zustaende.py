#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test ab 0.62.3: Alle Abzeichen aus inhalte/spiel/erfolge.json in vielen
Zustaenden - ohne Oberflaeche, auf der Datenebene, die PC und Handy teilen.

Geprueft werden genau die Funktionen, die PC (fisi_game_gui.JourneyView,
Erfolge) und Handy (mobile/src/spiel.py, Erfolge) zum Zeichnen eines
Abzeichens nutzen: achievement_overview, achievement_counts,
achievement_groups, badge_status, tier_text_color, badge_goals (bei
mehrstufigen Abzeichen), dazu Name, Text und Balkenanteil 0 bis 1.

Zustaende je Abzeichen:
  * erreichte Stufe 0 bis letzte Stufe
  * Zaehlerwert None, 0, 1, Ziel-1, Ziel, Ziel*10+7
  * "frueher": keine, gleiche oder hoechste Stufe in einem frueheren Durchgang
  * Einfach / Normal, erreicht an Tag 0, 1, 50, 400
  * geheim wie in der Datei oder zusaetzlich erzwungen
Jede Ausnahme und jedes unerwartet leere Ergebnis ist ein Fehler. Erwartet
leer: badge_goals bei geheimen Abzeichen (so gewollt, fisi_game.badge_goals).

Grenze (offen genannt): Der Test prueft die Daten, nicht das Zeichnen (Tk,
Flet). Den Fehler "Erfolge leer" von 0.62.2 (Zeichnen) haette er nicht
gefunden; dafuer gibt es test_reiter_sichtbar.py.

Die Kennzahlen des Durchgangs werden je Zustand fest vorgegeben (run_metrics
wird fuer den Aufruf ersetzt), alles andere ist der echte Code.

Start:  python test_erfolge_alle_zustaende.py
"""

import copy
import os
import shutil
import sys
import tempfile
import traceback
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import fisi_core as core   # noqa: E402
import fisi_game as fg     # noqa: E402

TAGE = (0, 1, 50, 400)


def _werte(rule, level):
    stages = rule["stufen"]
    goal = stages[level].get("ab", 1) if level < len(stages) else stages[-1].get("ab", 1)
    out = [None, 0, 1, max(0, goal - 1), goal, goal * 10 + 7]
    return sorted(set(out), key=lambda v: (v is not None, v or 0))


def pruefe_alle(state, badge_status=None):
    """Laeuft alle Abzeichen x Zustaende durch. Liefert (Aufrufe, erwartet
    leer, Liste der Probleme). badge_status nur fuer die Gegenprobe."""
    status_fn = badge_status or fg.badge_status
    rules = fg.achievement_rules(state.content)["erfolge"]
    real_metrics = fg.run_metrics
    calls = expected = 0
    problems = []

    def one(rule, level, value, earlier, easy, tag, secret):
        nonlocal calls, expected
        content = copy.copy(state.content)
        rule_one = dict(rule)
        if secret is not None:
            rule_one["geheim"] = secret
        content["erfolge"] = dict(fg.achievement_rules(state.content), erfolge=[rule_one])
        state.achievements = {(rule["id"], i + 1): {"tag": tag} for i in range(level)}
        records = [("2026-01-01 10:00:00", "frueherer-lauf", fg.REC_BADGE,
                    "%s:%d" % (rule["id"], i + 1), 1, "") for i in range(earlier)]
        metrics = {key: value for key in fg.RUN_METRICS}
        metrics["_texte"] = {}
        metrics[rule["wert"]] = value
        fg.run_metrics = lambda *_a, **_k: dict(metrics)
        old_diff = state.difficulty
        label = "%s stufe=%d wert=%r frueher=%d einfach=%s tag=%d geheim=%s" % (
            rule["id"], level, value, earlier, easy, tag, secret)
        try:
            state.difficulty = fg.DIFF_EASY if easy else fg.DIFF_NORMAL
            steps = []
            items = fg.achievement_overview(state, None, records, content)
            steps.append(("achievement_overview", items))
            steps.append(("achievement_counts", fg.achievement_counts(items)))
            steps.append(("achievement_groups", fg.achievement_groups(content)))
            for item in items:
                status, color = status_fn(item)
                steps.append(("badge_status", status))
                steps.append(("tier_text_color", fg.tier_text_color(color)))
                if len(item["stufen"]) > 1:
                    steps.append(("badge_goals", fg.badge_goals(item)))
                steps.append(("name", "???" if item["geheim"] else item["name"]))
                steps.append(("text", "Noch nicht entdeckt." if item["geheim"]
                              else item["text"]))
                if item["naechste"] and item["balken"] and not item["geheim"]:
                    if not 0.0 <= item["anteil"] <= 1.0:
                        steps.append(("anteil", ""))
            for name, result in steps:
                calls += 1
                if result in ("", None, [], ()):
                    if name == "badge_goals" and any(i["geheim"] for i in items):
                        expected += 1
                        continue
                    problems.append("LEER %s: %s" % (name, label))
        except Exception:
            calls += 1
            problems.append("FEHLER %s:\n%s" % (label, traceback.format_exc()))
        finally:
            state.difficulty = old_diff
            fg.run_metrics = real_metrics

    for rule in rules:
        n = len(rule["stufen"])
        for level in range(n + 1):
            for value in _werte(rule, level):
                for earlier in sorted({0, level, n}):
                    for easy in (False, True):
                        for tag in TAGE:
                            for secret in (None, True):
                                one(rule, level, value, earlier, easy, tag, secret)
    return calls, expected, problems


class ErfolgeAlleZustaendeTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="fisi erfolge ")
        self.db = core.DBManager(os.path.join(self.folder, "test.db"))
        game = fg.Game(self.db, "PC")
        game.set_profile("Test", {})
        game.reload()
        self.state = game.state

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def test_alle_abzeichen_alle_zustaende(self):
        rules = fg.achievement_rules(self.state.content)["erfolge"]
        self.assertGreaterEqual(len(rules), 38, "weniger Abzeichen als erwartet")
        calls, expected, problems = pruefe_alle(self.state)
        print("Abzeichen %d, Pruefschritte %d, davon erwartet leer %d, Probleme %d"
              % (len(rules), calls, expected, len(problems)))
        self.assertGreater(calls, 100000, "zu wenige Pruefschritte - Schleifen pruefen")
        self.assertEqual(problems[:5], [], "%d Probleme" % len(problems))


if __name__ == "__main__":
    unittest.main(verbosity=2)
