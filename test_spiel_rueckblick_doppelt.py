#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E-5 (ab 0.63.2, Weg A): Der Rueckblick im Spiel (Meine Reise) zaehlt doppelte
Feierabende und Tickets nur einmal - wie die Kopfzahlen seit 0.62.5 (B-G-26).

Doppel (Regeln unveraendert aus 0.62.5): dasselbe Ticket (Aufgabe als nicht
leerer Text) mit derselben gueltigen Tagesangabe (ganze Zahl > 0) bzw. ein
zweiter Feierabend mit derselben gueltigen Tagesangabe. Ab 0.63.2 werden sie
schon beim Einlesen uebersprungen und stehen nicht in state.history; alle
Leser von history (journey, journey_stats, run_metrics, laufender Tag)
sehen sie damit nicht mehr.

Erwartung: ROT gegen 14b3bd4 (R1-R6), gruen nach der Aenderung.
  R1 journey_stats: Tickets/richtig ohne Doppel
  R2 journey: Personal-Eintrag eines doppelten Feierabends genau einmal,
     Tageszahl folgender Eintraege ohne Tagesangabe stimmt
  R3 journey: Meilensteine ("10 Tickets gelöst", "Erster Zwischenfall
     gemeistert") nicht zu frueh, nicht doppelt
  R4 run_metrics: tickets und fehlerfrei_serie
  R5 laufender Tag: gleiches Ticket erst richtig, dann (zweites Geraet)
     falsch -> "richtig" (das erste gilt)
  R6 kein Hilfsattribut _counted_once mehr im Zustand
  echte API (zwei Geraete, Abgleich der Zeilen wie test_spiel_doppelt.py):
     Rueckblick des abgeglichenen Stands = Rueckblick von Geraet A allein
SCHUTZ (auch gegen 14b3bd4 gruen): Stand ohne Doppel unveraendert; Ticket
ohne Tag oder an anderem Tag zaehlt weiter; verschobene Tickets unveraendert.

SPIEL_CODE=<ordner> prueft einen anderen Stand (Gegenprobe gegen 14b3bd4).
Nur Wegwerf-Datenbanken.
Start:  python test_spiel_rueckblick_doppelt.py
"""

import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("SPIEL_CODE") or HERE)
_HOME = tempfile.mkdtemp(prefix="fisi_rueckblick_doppelt_")
os.environ["HOME"] = _HOME
os.environ["FISI_DB_PATH"] = os.path.join(_HOME, "nie_benutzt.db")
sys.path.insert(0, CODE)

import fisi_core as core  # noqa: E402
import fisi_game as fg  # noqa: E402

assert os.path.dirname(os.path.abspath(fg.__file__)) == CODE, fg.__file__


def tearDownModule():
    shutil.rmtree(_HOME, ignore_errors=True)


def _ts(n):
    return "2026-10-01 %02d:%02d:%02d" % (8 + n // 3600, (n // 60) % 60, n % 60)


def _events(items):
    return [(_ts(index), kind, data) for index, (kind, data) in enumerate(items)]


def _solved(task, day, right=True, money=50, **extra):
    data = {"aufgabe": task, "geld": money if right else -money, "richtig": right,
            "tag": day}
    data.update(extra)
    return (fg.EV_SOLVED, data)


def _day_end(day, salary=100, **extra):
    data = {"tag": day, "gehalt": salary, "miete": 0}
    data.update(extra)
    return (fg.EV_DAY_END, data)


def _profile():
    return (fg.EV_PROFILE, {"name": "Ada", "aussehen": {}})


def _day(day, count=3, right=True):
    return [_solved("t%d-%d" % (day, n), day, right) for n in range(count)] + [_day_end(day)]


def _state(items):
    return fg.GameState(_events(items))


def _review(state):
    """Alles, was der Rueckblick zeigt (ohne Zeitstempel)."""
    return {"journey": fg.journey(state), "stats": fg.journey_stats(state),
            "metrics": fg.run_metrics(state)}


class RueckblickTest(unittest.TestCase):

    def assert_like_without(self, with_doubles, without):
        """Rueckblick und Kopfzahlen mit Doppeln = ohne Doppel."""
        a, b = _state(with_doubles), _state(without)
        self.assertEqual((a.days_done, a.money, a.tickets_done),
                         (b.days_done, b.money, b.tickets_done))
        ra, rb = _review(a), _review(b)
        for key in ("stats", "metrics", "journey"):
            with self.subTest(key):
                self.assertEqual(ra[key], rb[key])
        return a, ra

    def test_r1_journey_stats_ohne_doppel(self):
        base = [_profile()] + _day(1) + _day(2)
        doubled = base + [_solved("t2-0", 2, right=False), _solved("t2-1", 2), _day_end(2)]
        state, review = self.assert_like_without(doubled, base)
        stats = review["stats"]
        self.assertEqual((stats["tickets"], stats["richtig"], stats["diensttage"]), (6, 6, 2))
        self.assertEqual(stats["tickets"], state.tickets_done)
        self.assertEqual((stats["tage_richtig"], stats["tage_falsch"]), ([3, 3], [0, 0]))

    def test_r2_journey_feierabend_personal_einmal(self):
        personal = {"personal": [{"art": fg.PERSONAL_SICK, "name": "Bob", "von": 2,
                                  "bis": 4}]}
        base = [_profile(), _solved("t1", 1), _day_end(1, firma=personal),
                (fg.EV_DAY_END, {"gehalt": 100, "miete": 0})]      # ohne Tagesangabe
        doubled = [_profile(), _solved("t1", 1), _day_end(1, firma=personal),
                   _day_end(1, firma=personal),
                   (fg.EV_DAY_END, {"gehalt": 100, "miete": 0})]
        _state_, review = self.assert_like_without(doubled, base)
        sick = [entry for entry in review["journey"] if entry["art"] == fg.PERSONAL_SICK]
        self.assertEqual(len(sick), 1, sick)
        self.assertEqual(sick[0]["tag"], 1)

    def test_r2_tageszahl_folgender_eintraege(self):
        # Ein Ereignis ohne Tagesangabe nach einem doppelten Feierabend steht
        # am richtigen Tag (journey zaehlt Feierabende mit)
        move = (fg.EV_MOVE, {"wohnung": "wg", "miete": 0, "geld": 0})
        base = [_profile(), _solved("t1", 1), _day_end(1), move]
        doubled = [_profile(), _solved("t1", 1), _day_end(1), _day_end(1), move]
        _state_, review = self.assert_like_without(doubled, base)
        moves = [entry for entry in review["journey"] if entry["art"] == "umzug"]
        self.assertEqual([entry["tag"] for entry in moves], [2])

    def test_r3_meilensteine_nicht_zu_frueh(self):
        nine = [_solved("m%d" % n, 1) for n in range(9)]
        incident = _solved("zf1", 1, zwischenfall=True)
        base = [_profile()] + nine + [incident, _day_end(1)]
        doubled = [_profile()] + nine + [_solved("m8", 1), incident, incident, _day_end(1)]
        _state_, review = self.assert_like_without(doubled, base)
        titles = [entry["titel"] for entry in review["journey"]]
        self.assertNotIn("10 Tickets gelöst", titles)
        self.assertEqual(titles.count("Erster Zwischenfall gemeistert"), 1)
        self.assertNotIn("Zwischenfall gemeistert", titles)

    def test_r4_run_metrics_tickets_und_serie(self):
        base = [_profile()] + _day(1) + _day(2) + _day(3)
        # zweites Geraet hat Tag 2 nachgespielt, ein Ticket dort falsch
        doubled = [_profile()] + _day(1) + _day(2) + [
            _solved("t2-0", 2, right=False), _day_end(2)] + _day(3)
        _state_, review = self.assert_like_without(doubled, base)
        self.assertEqual(review["metrics"]["tickets"], 9)
        self.assertEqual(review["metrics"]["fehlerfrei_serie"], 3)

    def test_r5_laufender_tag_das_erste_gilt(self):
        state = _state([_profile(), _solved("heute", 1), _solved("heute", 1, right=False)])
        self.assertEqual(state.handled.get("heute"), fg.ST_RIGHT)
        self.assertEqual(state.tickets_done, 1)

    def test_r6_kein_hilfsattribut(self):
        state = _state([_profile()] + _day(1) + _day(1))
        self.assertNotIn("_counted_once", vars(state))
        self.assertEqual(len([e for e in state.history if e[1] == fg.EV_DAY_END]), 1)


class TempDB:
    def __init__(self):
        self.folder = tempfile.mkdtemp(dir=_HOME)
        self.path = os.path.join(self.folder, "spiel.db")

    def open(self):
        return core.DBManager(self.path)


def _play_day(game):
    for _ in range(60):
        todo = game.state.open_tickets()
        if not todo:
            break
        task = todo[0]
        prepared = game.state.prepared_task(task)
        answer = fg.find_solution(prepared, game.state.available_parts(prepared)) or {}
        try:
            game.solve(task["id"], answer, False)
        except ValueError:
            try:
                game.solve(task["id"], {}, False)
            except ValueError:
                game.defer(task["id"])
    game.end_day()


def _merge_rows(source_path, target_path):
    """Abgleich nachgestellt wie in test_spiel_doppelt.py: Zeilen aus source,
    deren uid in target fehlt, mit ihrem Zeitstempel uebernehmen."""
    src, dst = sqlite3.connect(source_path), sqlite3.connect(target_path)
    try:
        cols = [row[1] for row in src.execute("PRAGMA table_info(spiel_ereignisse)")
                if row[1] != "id"]
        have = {row[0] for row in dst.execute("SELECT uid FROM spiel_ereignisse")}
        rows = [row for row in src.execute(
            "SELECT %s FROM spiel_ereignisse ORDER BY id" % ", ".join(cols))
            if row[cols.index("uid")] not in have]
        dst.executemany("INSERT INTO spiel_ereignisse (%s) VALUES (%s)" % (
            ", ".join(cols), ", ".join("?" * len(cols))), rows)
        dst.commit()
        return len(rows)
    finally:
        src.close()
        dst.close()


class EchteApiTest(unittest.TestCase):

    def test_zwei_geraete_rueckblick_wie_allein(self):
        """Geraet A spielt Tag 1, Kopie auf B, beide spielen Tag 2 offline,
        dann kommen die Zeilen von B zu A. Soll: Rueckblick (Tickets,
        Feierabende) wie Geraet A allein."""
        a, b = TempDB(), TempDB()
        game_a = fg.Game(a.open(), device="PC")
        game_a.set_profile("Ada", {})
        _play_day(game_a)
        shutil.copy(a.path, b.path)
        game_b = fg.Game(b.open(), device="Handy")
        _play_day(game_a)
        _play_day(game_b)
        alone = game_a.reload()
        alone_stats = fg.journey_stats(alone)
        alone_metrics = fg.run_metrics(alone)
        self.assertEqual(alone_stats["diensttage"], 2)
        self.assertGreater(_merge_rows(b.path, a.path), 0)
        game_a.invalidate()
        merged = fg.GameState(a.open().game_events(game_a.run))
        stats = fg.journey_stats(merged)
        self.assertEqual(stats["tickets"], alone_stats["tickets"])
        # journey_stats zaehlt Zwischenfaelle getrennt, tickets_done zusammen
        self.assertEqual(stats["tickets"] + stats["zwischenfaelle_gesamt"],
                         merged.tickets_done)
        self.assertEqual((stats["tage_richtig"], stats["tage_falsch"]),
                         (alone_stats["tage_richtig"], alone_stats["tage_falsch"]))
        self.assertEqual(fg.run_metrics(merged)["tickets"], alone_metrics["tickets"])
        self.assertEqual(fg.run_metrics(merged)["fehlerfrei_serie"],
                         alone_metrics["fehlerfrei_serie"])
        self.assertEqual(
            [e for e in fg.journey(merged) if e["art"] in ("meilenstein", "zwischenfall")],
            [e for e in fg.journey(alone) if e["art"] in ("meilenstein", "zwischenfall")])


class SchutzTest(unittest.TestCase):
    """Auch gegen 14b3bd4 gruen."""

    def test_ohne_doppel_unveraendert(self):
        state = _state([_profile()] + _day(1) + _day(2))
        self.assertEqual(len(state.history), 9)
        self.assertEqual(fg.journey_stats(state)["tickets"], 6)

    def test_ohne_tag_und_anderer_tag_zaehlen(self):
        no_day = (fg.EV_SOLVED, {"aufgabe": "x", "geld": 5, "richtig": True})
        state = _state([_profile(), no_day, no_day, _solved("y", 1), _solved("y", 2),
                        (fg.EV_DAY_END, {"gehalt": 1}), (fg.EV_DAY_END, {"gehalt": 1})])
        self.assertEqual(fg.journey_stats(state)["tickets"], 4)
        self.assertEqual(state.days_done, 2)

    def test_verschoben_unveraendert(self):
        deferred = (fg.EV_DEFERRED, {"aufgabe": "z", "tag": 1})
        state = _state([_profile(), deferred, deferred])
        self.assertEqual(fg.journey_stats(state)["verschoben"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
