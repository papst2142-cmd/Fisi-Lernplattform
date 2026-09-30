#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer das Lernspiel (fisi_game.py) - ohne Oberflaeche.

Start:  python test_spiel.py
"""

import copy
import json
import math
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fisi_core as core  # noqa: E402
import fisi_game as fg  # noqa: E402
import fisi_sync  # noqa: E402
from fisi_core import (  # noqa: E402
    AP1_SZENARIEN, CAT_NET, CAT_SYS, KARTEIKARTEN, PROJEKTARBEITEN, QUIZ_QUESTIONS, SZENARIEN,
    TOPICS, DBManager, topic_totals, validate_content,
)

BALANCING = fg.GAME["balancing"]


class TempDB:
    """Eine frische Datenbank in einem temporaeren Ordner."""

    def __enter__(self):
        self.folder = tempfile.mkdtemp()
        self.db = DBManager(os.path.join(self.folder, "test.db"))
        return self.db

    def __exit__(self, *_exc):
        shutil.rmtree(self.folder, ignore_errors=True)


def _ordered_stock(state):
    """Lagerbestand ohne Rainers Ersatzteilregal (Grundbestand)."""
    base = fg.GAME["hardware"].get("grundbestand", {})
    stock = dict(state.stock())
    for part_id, count in base.items():
        if stock.get(part_id) == count:
            del stock[part_id]
    return stock


def levels(value):
    return {key: value for key in fg.CAT_ORDER}


def topic_levels(value):
    return {key: value for key in fg.TOPIC_ORDER}


class InhalteTest(unittest.TestCase):
    def test_inhalte_fehlerfrei(self):
        self.assertEqual(fg.validate_game_content(), [])
        self.assertEqual(validate_content(), [])

    def test_fehler_werden_gefunden(self):
        content = json.loads(json.dumps(fg.GAME))
        content["aufgaben"][0]["raum"] = "keller"
        content["aufgaben"][1]["antwort"] = "gibt es nicht"
        problems = fg.validate_game_content(content)
        self.assertTrue(any("keller" in p for p in problems))
        self.assertTrue(any("nicht in den Optionen" in p for p in problems))

    def test_alle_fachbereiche_kommen_vor(self):
        cats = {task["cat"] for task in fg.GAME["aufgaben"]}
        self.assertEqual(cats, set(fg.CAT_ORDER))


class WissenTest(unittest.TestCase):
    def test_ohne_antworten_null(self):
        self.assertEqual(fg.knowledge_from_answers({}, {}), levels(0.0))

    def test_alles_richtig_volle_abdeckung(self):
        answers = {"netzwerk": [True] * 50}
        coverage = {"netzwerk": 60.0}
        self.assertEqual(fg.knowledge_from_answers(answers, coverage)["netzwerk"], 100.0)

    def test_wenige_antworten_werden_gedaempft(self):
        few = fg.knowledge_from_answers({"netzwerk": [True] * 5}, {"netzwerk": 60.0})
        many = fg.knowledge_from_answers({"netzwerk": [True] * 40}, {"netzwerk": 60.0})
        self.assertLess(few["netzwerk"], many["netzwerk"])

    def test_neuere_antworten_zaehlen_staerker(self):
        besser = fg.knowledge_from_answers({"netzwerk": [True] * 20 + [False] * 20},
                                           {"netzwerk": 60.0})
        schlechter = fg.knowledge_from_answers({"netzwerk": [False] * 20 + [True] * 20},
                                               {"netzwerk": 60.0})
        self.assertGreater(besser["netzwerk"], schlechter["netzwerk"])

    def test_abdeckung_wird_gedaempft_nicht_linear(self):
        # 12,5 % Abdeckung bei voller Wirkung ab 50 % -> Wurzel(0,25) = 50 %
        value = fg.knowledge_from_answers({"netzwerk": [True] * 40},
                                          {"netzwerk": 12.5})["netzwerk"]
        self.assertAlmostEqual(value, 50.0, places=1)

    def test_aus_der_datenbank(self):
        with TempDB() as db:
            for _ in range(30):
                db.log_quiz_answer(CAT_NET, "Frage netz %d" % _, True)
            db.log_card(CAT_SYS, "Karte", "mc", False)
            result = fg.knowledge(db)
            self.assertGreater(result["netzwerk"], 0)
            self.assertEqual(result["systeme"], 0)
            self.assertEqual(result["wirtschaft"], 0)


class ThemenTest(unittest.TestCase):
    """Wissensstand je Thema (ab 0.37)."""

    def test_jeder_inhalt_hat_ein_thema_seines_fachbereichs(self):
        for items in (KARTEIKARTEN, QUIZ_QUESTIONS, SZENARIEN, AP1_SZENARIEN, PROJEKTARBEITEN):
            for item in items:
                self.assertIn(item.get("thema"), TOPICS[item["cat"]], item.get("q") or
                              item.get("title"))

    def test_jedes_thema_hat_genug_inhalte(self):
        # Der Wissensstand braucht mindestens 20 Antworten je Thema
        for topic, count in topic_totals().items():
            self.assertGreaterEqual(count, 20, topic)

    def test_auftraege_verlangen_themen(self):
        for task in fg.GAME["aufgaben"]:
            self.assertTrue(task["anforderungen"], task["id"])
            for key in task["anforderungen"]:
                self.assertIn(key, fg.TOPIC_CAT, task["id"])

    def test_aus_der_datenbank(self):
        ipv4 = [q["q"] for q in QUIZ_QUESTIONS if q["thema"] == "ipv4"][:30]
        with TempDB() as db:
            for question in ipv4:
                db.log_quiz_answer(CAT_NET, question, True)
            card = next(c for c in KARTEIKARTEN if c["thema"] == "linux")
            db.log_card(CAT_SYS, card["q"], "mc", True)
            db.log_quiz_answer(CAT_NET, "Frage, die es nicht gibt", True)
            result = fg.topic_knowledge(db)
            self.assertEqual(set(result), set(fg.TOPIC_ORDER))
            self.assertGreater(result["ipv4"], 0)
            self.assertEqual(result["ipv6"], 0)
            self.assertEqual(result["switching"], 0)
            # Eine einzelne Karte reicht nicht (mindestens 20 Antworten)
            self.assertLess(result["linux"], 5)
            stats = db.topic_stats()
            self.assertEqual(stats["ipv4"]["answered"], len(ipv4))
            self.assertEqual(stats["linux"], {"answered": 1, "correct": 1})
            daily = db.topic_daily(CAT_NET, 7)
            self.assertEqual(daily["ipv4"][-1], len(ipv4))
            self.assertEqual(sum(daily["routing"]), 0)
            coverage = db.topic_coverage(topic_totals())
            self.assertGreater(coverage["ipv4"], 0)

    def test_sperre_je_thema(self):
        task = next(t for t in fg.GAME["aufgaben"] if len(t["anforderungen"]) == 2)
        first, second = list(task["anforderungen"])
        values = topic_levels(100)
        values[first] = 0
        gaps = fg.requirement_gaps(task, values)
        self.assertEqual([gap[0] for gap in gaps], [first])
        self.assertIn(fg.TOPIC_NAME[first], fg.gap_warning(gaps))


class AufgabenTest(unittest.TestCase):
    def setUp(self):
        self.choice = next(t for t in fg.GAME["aufgaben"] if t["typ"] == "auswahl")
        self.match = next(t for t in fg.GAME["aufgaben"] if t["typ"] == "zuordnung")

    def test_auswahl(self):
        self.assertEqual(fg.check_answer(self.choice, self.choice["antwort"]), (True, 0))
        wrong = [o for o in self.choice["optionen"] if o != self.choice["antwort"]][0]
        self.assertEqual(fg.check_answer(self.choice, wrong), (False, 1))

    def test_zuordnung(self):
        right = {left: r for left, r in self.match["paare"]}
        self.assertEqual(fg.check_answer(self.match, right), (True, 0))
        lefts = [left for left, _r in self.match["paare"]]
        swapped = dict(right)
        swapped[lefts[0]], swapped[lefts[1]] = right[lefts[1]], right[lefts[0]]
        self.assertEqual(fg.check_answer(self.match, swapped), (False, 2))
        self.assertEqual(fg.check_answer(self.match, {})[0], False)

    def test_bonus_ohne_hilfe(self):
        base = self.choice["belohnung"]
        with_help = fg.evaluate(self.choice, self.choice["antwort"], True, topic_levels(100), 1)
        without = fg.evaluate(self.choice, self.choice["antwort"], False, topic_levels(100), 1)
        self.assertGreater(without["geld"], with_help["geld"])
        self.assertGreaterEqual(with_help["geld"], base["geld"])
        self.assertGreater(without["reputation"]["fachkompetenz"],
                           with_help["reputation"]["fachkompetenz"])

    def test_weiche_sperre_doppelter_verlust(self):
        wrong = [o for o in self.choice["optionen"] if o != self.choice["antwort"]][0]
        normal = fg.evaluate(self.choice, wrong, False, topic_levels(100), 1)
        below = fg.evaluate(self.choice, wrong, False, topic_levels(0), 1)
        self.assertTrue(below["unter_niveau"])
        self.assertFalse(normal["unter_niveau"])
        self.assertEqual(below["reputation"]["fachkompetenz"],
                         2 * normal["reputation"]["fachkompetenz"])
        self.assertLess(normal["geld"], 0)

    def test_warnhinweis(self):
        gaps = fg.requirement_gaps(self.choice, topic_levels(0))
        self.assertTrue(gaps)
        self.assertIn("fehlt dir noch Wissen", fg.gap_warning(gaps))
        self.assertEqual(fg.gap_warning(fg.requirement_gaps(self.choice, topic_levels(100))), "")

    def test_verweise_ins_lernen(self):
        for task in fg.GAME["aufgaben"]:
            links = fg.learn_links(task)
            self.assertTrue(links, task["id"])
            self.assertTrue(all(hit[0] in ("Karteikarte", "Quizfrage") for hit in links))


class SpielstandTest(unittest.TestCase):
    def test_leerer_stand(self):
        state = fg.GameState([])
        self.assertIsNone(state.profile)
        self.assertEqual(state.day, 1)
        self.assertEqual(state.money, 0)
        self.assertEqual(state.rank, "Azubi-Niveau")
        self.assertEqual(len(state.todays_tickets()), fg.tickets_per_day("Azubi-Niveau"))
        self.assertFalse(state.can_end_day())

    def test_juengstes_profil_gewinnt(self):
        state = fg.GameState([
            ("2026-09-28 10:00:00", fg.EV_PROFILE, {"name": "Alt", "aussehen": {}}),
            ("2026-09-28 11:00:00", fg.EV_PROFILE,
             {"name": "Neu", "aussehen": {"frisur": "locken", "haut": "unsinn"}}),
        ])
        self.assertEqual(state.profile["name"], "Neu")
        self.assertEqual(state.profile["aussehen"]["frisur"], "locken")
        self.assertEqual(state.profile["aussehen"]["haut"], "hell")

    def test_reputation_bleibt_zwischen_0_und_100(self):
        events = [("t%03d" % i, fg.EV_SOLVED,
                   {"aufgabe": "x", "tag": 1, "richtig": False, "geld": -1,
                    "reputation": {"fachkompetenz": -30}}) for i in range(5)]
        events += [("u%03d" % i, fg.EV_SOLVED,
                    {"aufgabe": "x", "tag": 1, "richtig": True, "geld": 1,
                     "reputation": {"fachkompetenz": 40}}) for i in range(5)]
        state = fg.GameState(events)
        self.assertEqual(state.reputation["fachkompetenz"], 100)
        self.assertEqual(state.money, 0)


class SpielMitDatenbankTest(unittest.TestCase):
    def test_arbeitstag_ablauf(self):
        with TempDB() as db:
            game = fg.Game(db, device="Test")
            game.set_profile("Nico", {"frisur": "kurz"})
            tickets = game.state.open_tickets()
            first, second, third = tickets
            payload = game.solve(first["id"], _right_answer(first), used_help=False)
            self.assertTrue(payload["richtig"])
            self.assertEqual(game.state.status_of(first["id"]), fg.ST_RIGHT)
            game.solve(second["id"], _wrong_answer(second), used_help=True)
            self.assertEqual(game.state.status_of(second["id"]), fg.ST_WRONG)
            self.assertFalse(game.state.can_end_day())
            game.defer(third["id"])
            # Keine neuen Tickets am selben Tag, Tag kann enden
            self.assertEqual(game.state.open_tickets(), [])
            self.assertTrue(game.state.can_end_day())
            money_before = game.state.money
            salary = game.state.salary
            game.end_day()
            self.assertEqual(game.state.day, 2)
            self.assertEqual(game.state.money, money_before + salary)
            # Falsch geloeste und verschobene Tickets kommen wieder
            open_ids = [task["id"] for task in game.state.open_tickets()]
            self.assertIn(second["id"], open_ids)
            self.assertIn(third["id"], open_ids)
            self.assertNotIn(first["id"], open_ids)
            with self.assertRaises(ValueError):
                game.solve(first["id"], _right_answer(first), False)

    def test_alle_aufgaben_loesbar(self):
        with TempDB() as db:
            game = fg.Game(db)
            game.set_profile("Test", {})
            _play_through(game, days=150)
            self.assertTrue(game.state.all_done())
            self.assertGreater(game.state.money, 0)
            self.assertNotEqual(game.state.rank, "Azubi-Niveau")

    def test_zuruecksetzen_getrennt(self):
        with TempDB() as db:
            game = fg.Game(db)
            game.set_profile("Nico", {})
            db.log_quiz_answer(CAT_NET, "Frage", True)
            # "Alle Lerndaten loeschen" laesst den Spielstand stehen
            db.reset_all()
            self.assertEqual(game.reload().profile["name"], "Nico")
            db.clear_history()
            self.assertEqual(game.reload().profile["name"], "Nico")
            # "Spielstand zuruecksetzen" laesst den Lernfortschritt stehen
            db.log_quiz_answer(CAT_NET, "Frage 2", True)
            game.reset()
            self.assertIsNone(game.state.profile)
            self.assertEqual(db.count_quiz_answers(), 1)
            self.assertTrue(db.get_meta("spiel_reset_at"))


class AbgleichTest(unittest.TestCase):
    def test_spielstand_wird_abgeglichen(self):
        with TempDB() as pc, TempDB() as handy:
            fg.Game(pc, "PC").set_profile("Nico", {"extra": "brille"})
            fisi_sync.merge_into_local(handy, fisi_sync.export_local(pc))
            state = fg.Game(handy, "Handy").state
            self.assertEqual(state.profile["name"], "Nico")
            # Doppelter Abgleich zaehlt nichts doppelt
            fisi_sync.merge_into_local(handy, fisi_sync.export_local(pc))
            # Profil, (ab 0.46) das Abzeichen "Erster Arbeitstag" und (ab 0.47)
            # der Schwierigkeitsgrad
            self.assertEqual(len(handy.game_events()), 3)
            self.assertEqual(state.level, fg.DIFF_NORMAL)

    def test_zuruecksetzen_wird_abgeglichen(self):
        with TempDB() as pc, TempDB() as handy:
            game = fg.Game(pc, "PC")
            game.set_profile("Nico", {})
            fisi_sync.merge_into_local(handy, fisi_sync.export_local(pc))
            handy_game = fg.Game(handy, "Handy")
            # Zeitstempel sind sekundengenau - Reset eindeutig spaeter setzen
            handy._execute("UPDATE spiel_ereignisse SET timestamp = '2026-01-01 00:00:00'",
                           commit=True)
            pc._execute("UPDATE spiel_ereignisse SET timestamp = '2026-01-01 00:00:00'",
                        commit=True)
            handy_game.reset()
            fisi_sync.merge_into_local(pc, fisi_sync.export_local(handy))
            self.assertIsNone(fg.Game(pc).state.profile)

    def test_lern_reset_loescht_spiel_nicht_beim_abgleich(self):
        with TempDB() as pc, TempDB() as handy:
            fg.Game(pc, "PC").set_profile("Nico", {})
            pc._execute("UPDATE spiel_ereignisse SET timestamp = '2026-01-01 00:00:00'",
                        commit=True)
            handy.reset_all()
            fisi_sync.merge_into_local(pc, fisi_sync.export_local(handy))
            self.assertEqual(fg.Game(pc).state.profile["name"], "Nico")


class LernstandJeFrageTest(unittest.TestCase):
    """Notizblock (ab 0.39): Status je Frage aus den Antworten."""

    def test_status_regeln(self):
        qs = core.question_status
        self.assertEqual(qs([]), (core.Q_OPEN, ""))
        self.assertEqual(qs([True]), (core.Q_OPEN, ""))
        self.assertEqual(qs([None, None]), (core.Q_OPEN, ""))
        self.assertEqual(qs([False]), (core.Q_PRACTICE, core.LEVEL_RED))
        self.assertEqual(qs([False, True]), (core.Q_PRACTICE, core.LEVEL_YELLOW))
        self.assertEqual(qs([False, True, True]), (core.Q_DONE, ""))
        self.assertEqual(qs([True, True]), (core.Q_DONE, ""))
        # Faellt nach einem spaeteren Fehler zurueck
        self.assertEqual(qs([True, True, False]), (core.Q_PRACTICE, core.LEVEL_RED))
        self.assertEqual(qs([True, None, True]), (core.Q_DONE, ""))

    def test_aus_der_datenbank_und_notizblock(self):
        with TempDB() as db:
            card, quiz = KARTEIKARTEN[0], QUIZ_QUESTIONS[0]
            db.log_card(card["cat"], card["q"], "mc", False)
            db.log_quiz_answer(quiz["cat"], quiz["q"], False)
            db.log_quiz_answer(quiz["cat"], quiz["q"], True)
            db.log_ap1(3, AP1_SZENARIEN[3]["title"], AP1_SZENARIEN[3]["theme"], True)
            db.log_ap1(3, AP1_SZENARIEN[3]["title"], AP1_SZENARIEN[3]["theme"], True)
            db.log_scenario(1, SZENARIEN[1]["title"], SZENARIEN[1]["theme"], None)
            db.log_project(2, PROJEKTARBEITEN[2]["title"], PROJEKTARBEITEN[2]["cat"], False)
            book = core.StatusBook(db)
            self.assertEqual(book.status(core.SRC_CARD, card["q"]),
                             (core.Q_PRACTICE, core.LEVEL_RED))
            self.assertEqual(book.status(core.SRC_QUIZ, quiz["q"]),
                             (core.Q_PRACTICE, core.LEVEL_YELLOW))
            self.assertEqual(book.status(core.SRC_AP1, 3), (core.Q_DONE, ""))
            self.assertEqual(book.status(core.SRC_AP2, 1), (core.Q_OPEN, ""))
            self.assertTrue(book.touched(core.SRC_AP2, 1))
            entries = core.notebook_entries(book)
            self.assertEqual({(e["source"], e["key"]) for e in entries},
                             {(core.SRC_CARD, card["q"]), (core.SRC_QUIZ, quiz["q"]),
                              (core.SRC_PROJECT, 2)})
            self.assertNotEqual(entries[-1]["level"], core.LEVEL_RED)   # rot vor gelb
            only_net = core.notebook_entries(book, category=card["cat"],
                                             sources=[core.SRC_CARD])
            self.assertEqual(len(only_net), 1)
            summary = core.notebook_summary(book)
            self.assertEqual(summary[core.SRC_AP1][core.Q_DONE], 1)
            self.assertEqual(sum(summary[core.SRC_CARD].values()), len(KARTEIKARTEN))
            # Status-Filter der Listen
            statuses = core.position_statuses(book, core.SRC_AP1)
            self.assertEqual(core.filter_positions(AP1_SZENARIEN, status=core.STATUS_DONE,
                                                   statuses=statuses), [3])
            self.assertEqual(len(core.filter_positions(AP1_SZENARIEN, status=core.STATUS_OPEN,
                                                       statuses=statuses)),
                             len(AP1_SZENARIEN) - 1)

    def test_unbearbeitete_zuerst(self):
        results = {(core.SRC_CARD, "a"): [("1", False)], (core.SRC_CARD, "b"): [("1", True)],
                   (core.SRC_CARD, "z"): [("1", True), ("2", True)]}
        book = core.StatusBook(results=results)
        keys = ["z", "b", "a", "c", "d", "e", "f", "g"]
        order = book.preferred_order(core.SRC_CARD, keys)
        self.assertEqual(order[:core.NEW_PER_REPEAT], ["c", "d", "e", "f"])
        self.assertEqual(order[core.NEW_PER_REPEAT], "a")      # zu ueben zuerst
        self.assertEqual(sorted(order), sorted(keys))
        self.assertEqual(order[-1], "z")                       # abgeschlossen zuletzt

    def test_abgleich_mit_alter_version(self):
        """Eintraege ohne die neue Spalte correct werden weiter uebernommen."""
        with TempDB() as pc, TempDB() as handy:
            pc.log_ap1(0, AP1_SZENARIEN[0]["title"], AP1_SZENARIEN[0]["theme"], False)
            data = fisi_sync.export_local(pc)
            columns = data["columns"]["ap1_events"]
            index = columns.index("correct") + 1       # +1 wegen uid vorne
            data["columns"]["ap1_events"] = [c for c in columns if c != "correct"]
            data["tables"]["ap1_events"] = [row[:index] + row[index + 1:]
                                            for row in data["tables"]["ap1_events"]]
            self.assertEqual(fisi_sync.merge_into_local(handy, data), 1)
            self.assertEqual(core.StatusBook(handy).status(core.SRC_AP1, 0),
                             (core.Q_OPEN, ""))
            # Mit der neuen Spalte kommt auch die Bewertung mit
            with TempDB() as other:
                fisi_sync.merge_into_local(other, fisi_sync.export_local(pc))
                self.assertEqual(core.StatusBook(other).status(core.SRC_AP1, 0)[0],
                                 core.Q_PRACTICE)

    def test_alte_datenbank_bekommt_spalte(self):
        with TempDB() as db:
            conn = db.get_connection()
            conn.execute("DROP TABLE project_events")
            conn.execute("CREATE TABLE project_events (id INTEGER PRIMARY KEY AUTOINCREMENT,"
                         " timestamp TEXT NOT NULL, project_index INTEGER NOT NULL,"
                         " title TEXT NOT NULL, category TEXT NOT NULL, uid TEXT)")
            conn.commit()
            conn.close()
            db.init_db()
            db.log_project(0, "x", CAT_NET, True)
            self.assertEqual(core.StatusBook(db).results[(core.SRC_PROJECT, 0)][0][1], True)


class ReiseTest(unittest.TestCase):
    """Reise des Spielers (ab 0.39): Tagebuch und Rueckblick aus dem Protokoll."""

    def test_tagebuch_und_statistik(self):
        with TempDB() as db:
            game = fg.Game(db)
            game.set_profile("Nico", {})
            _play_through(game, days=12)
            state = game.state
            entries = fg.journey(state)
            kinds = [entry["art"] for entry in entries]
            self.assertEqual(kinds[0], "start")
            self.assertIn("meilenstein", kinds)
            self.assertIn("rang", kinds)                    # Junior ab Tag 10
            self.assertIn("story", kinds)                   # Story ab Tag 12
            days = [entry["tag"] for entry in entries]
            self.assertEqual(days, sorted(days))
            self.assertTrue(all(entry["tag"] <= state.day for entry in entries))
            story = fg.journey_filter(entries, fg.JOURNEY_STORY)
            self.assertTrue(story and all(e["gruppe"] == fg.JOURNEY_STORY for e in story))
            stats = fg.journey_stats(state)
            self.assertEqual(stats["diensttage"], state.days_done)
            self.assertEqual(stats["richtig"] + stats["zwischenfaelle"], len(state.solved))
            self.assertEqual(len(stats["ansehen"]), min(30, state.days_done))
            self.assertEqual(sum(stats["je_fachbereich"].values()), stats["richtig"])

    def test_firma_im_tagebuch(self):
        with TempDB() as db:
            game = _rich_game(db, money=200000)
            game._log(fg.EV_FOUNDED, {"tag": 2, "name": "Nico IT", "geld": -1000})
            game._log(fg.EV_FOUNDED, {"tag": 2, "name": "Doppelt", "geld": -1000})
            game._log(fg.EV_EXPAND, {"tag": 2, "stufe": 2, "geld": -100})
            titles = [entry["titel"] for entry in fg.journey(game.state)]
            self.assertIn("Firma gegründet: Nico IT", titles)
            self.assertNotIn("Firma gegründet: Doppelt", titles)
            self.assertTrue(any(title.startswith("Gebäude ausgebaut") for title in titles))

    def test_alle_zwischenfaelle_und_angebote(self):
        with TempDB() as db:
            game = _rich_game(db, money=200000)
            incident = fg.GAME["zwischenfaelle"][0]
            for day, right in ((3, True), (5, False), (7, True)):
                game._log(fg.EV_SOLVED, {"tag": day, "aufgabe": incident["id"],
                                         "zwischenfall": True, "richtig": right})
            customer = fg.firm_rules()["kunden"][0]["id"]
            for day, kind in ((8, fg.EV_OFFER_WON), (9, fg.EV_OFFER_LOST), (10, fg.EV_OFFER_WON)):
                game._log(kind, {"tag": day, "anfrage": "a%d" % day, "kunde": customer,
                                 "artikel": "Switch", "menge": 2, "geld": 120,
                                 "grund": "" if kind == fg.EV_OFFER_WON else "preis"})
            titles = [entry["titel"] for entry in fg.journey(game.state)]
            self.assertEqual([t for t in titles if "Zwischenfall" in t],
                             ["Erster Zwischenfall gemeistert", "Zwischenfall nicht gemeistert",
                              "Zwischenfall gemeistert"])
            self.assertEqual([t for t in titles if "Angebot" in t],
                             ["Erstes Angebot gewonnen", "Angebot verloren", "Angebot gewonnen"])

    def test_leerer_spielstand(self):
        state = fg.GameState([])
        self.assertEqual(fg.journey(state), [])
        self.assertEqual(fg.journey_stats(state)["tickets"], 0)


class SymbolSchriftTest(unittest.TestCase):
    """Die Seitenleiste am PC nutzt ab 0.39 die Symbole der Handy-App."""

    def test_alle_symbole_in_der_schrift(self):
        try:
            from PIL import ImageFont
            import fisi_widgets as fw
        except Exception as error:      # ohne Oberflaechen-Pakete
            self.skipTest(str(error))
        font = ImageFont.truetype(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                               fw.SYMBOL_FONT_FILE), 24)
        for name in fw.SYMBOLS:
            self.assertIsNotNone(fw.symbol_image(name, 24, "#FFFFFF").getbbox(), name)
        self.assertTrue(font)
        import app_gui
        self.assertLessEqual(set(app_gui.NAV_SYMBOLS.values()), set(fw.SYMBOLS))
        keys = {item[0] for item in app_gui.NAV_ITEMS}
        for item in app_gui.NAV_ITEMS:
            keys |= {sub[0] for sub in item[3] or [] if isinstance(sub, tuple)}
        self.assertEqual(set(app_gui.NAV_SYMBOLS), keys)
        self.assertEqual(set(app_gui.CATEGORY_NAV_SYMBOL), set(app_gui.CATEGORIES))
        self.assertLessEqual(set(app_gui.CATEGORY_NAV_SYMBOL.values()), set(fw.SYMBOLS))


class GrundrissUndAvatarTest(unittest.TestCase):
    def test_raum_treffer(self):
        for item in fg.GAME["gebaeude"]["raeume"]:
            hit = fg.room_at(item["x"] + item["w"] / 2.0, item["y"] + item["h"] / 2.0)
            self.assertEqual(hit["id"], item["id"])
        self.assertIsNone(fg.room_at(-1, -1))

    def test_raeume_ueberlappen_nicht(self):
        building = fg.GAME["gebaeude"]
        for x in range(building["breite"]):
            for y in range(building["hoehe"]):
                hits = [r for r in building["raeume"]
                        if r["x"] <= x < r["x"] + r["w"] and r["y"] <= y < r["y"] + r["h"]]
                self.assertLessEqual(len(hits), 1, (x, y))

    def test_gebaeude_zeichnung(self):
        state = fg.GameState([])
        shapes = fg.building_shapes(state.open_count_by_room(), "serverraum",
                                    ("Nico", fg.DEFAULT_APPEARANCE))
        kinds = {shape["k"] for shape in shapes}
        self.assertLessEqual(kinds, {"rect", "oval", "line", "arc", "text"})
        texts = [shape["text"] for shape in shapes if shape["k"] == "text"]
        for item in fg.GAME["gebaeude"]["raeume"]:
            self.assertIn(item["name"], texts)
        self.assertIn("Nico", texts)
        # Ohne Spielfigur keine Figur im Flur
        texts = [shape["text"] for shape in fg.building_shapes() if shape["k"] == "text"]
        self.assertNotIn("Nico", texts)

    def test_einrichtung_und_plaetze_in_den_raeumen(self):
        for item in fg.GAME["gebaeude"]["raeume"]:
            for deco in item.get("deko", []):
                self.assertIn(deco["typ"], fg.DECO_TYPES)
                self.assertTrue(fg._inside(deco, item), (item["id"], deco))
        for person in fg.GAME["kollegen"]:
            hit = fg.room_at(*person["platz"])
            self.assertEqual(hit["id"], person["raum"], person["id"])
        # Der Flur gehoert zu keinem Raum
        hall = fg.GAME["gebaeude"]["flur"]
        self.assertIsNone(fg.room_at(5, hall["y"] + hall["h"] / 2.0))

    def test_alle_kollegen_erreichbar(self):
        start = fg.start_position()
        self.assertTrue(fg.can_stand(*start))
        for person in fg.GAME["kollegen"]:
            if any(o.get("nachfolger") == person["id"] for o in fg.GAME["kollegen"]):
                continue    # sitzt spaeter am Platz der Vorgaengerin/des Vorgaengers
            route = fg.walk_path(start, person["platz"], reach=fg.REACH)
            self.assertTrue(route, person["id"])
            end = route[-1]
            self.assertLessEqual((end[0] - person["platz"][0]) ** 2 +
                                 (end[1] - person["platz"][1]) ** 2,
                                 fg.REACH ** 2 + 1e-9)
            self.assertEqual(fg.person_near(*end)["id"], person["id"])
            # jeder Wegpunkt ist begehbar
            for point in route:
                self.assertTrue(fg.can_stand(*point), (person["id"], point))

    def test_waende_nur_durch_tueren(self):
        # Von Raum zu Raum fuehrt der Weg immer durch den Flur
        hall = fg.GAME["gebaeude"]["flur"]
        route = fg.walk_path((3.5, 12.0), (3.5, 4.5))
        self.assertTrue(route)
        self.assertTrue(any(hall["y"] <= y <= hall["y"] + hall["h"] for _x, y in route))

    def test_drehung_hin_und_zurueck(self):
        for point in ((0, 0), (3.5, 12.25), (30, 16)):
            self.assertEqual(fg.from_view(*fg.to_view(*point, rotate=True), rotate=True),
                             point)
        self.assertEqual(fg.plan_size(True), (16, 30))
        shapes = fg.building_shapes(rotate=True)
        width, height = fg.plan_size(True)
        for shape in shapes:
            if shape["k"] == "text":
                self.assertTrue(-1 <= shape["x"] <= width + 1 and -1 <= shape["y"] <= height + 1)

    def test_auftraege_je_person(self):
        state = fg.GameState([])
        quests = state.quests(fg.SITE_OFFICE)
        self.assertEqual(sum(len(tasks) for tasks in state.quests().values()),
                         len(state.open_tickets()))
        person_id = next(iter(quests))
        person = fg.colleague(person_id)
        title, _text = fg.office_message(person["platz"], person, quests)
        self.assertIn("Auftrag", title)
        texts = [s["text"] for s in fg.building_shapes(quests=set(quests)) if s["k"] == "text"]
        self.assertEqual(texts.count("!"), len(quests))

    def test_kreisfarbe_waehlbar(self):
        for key, _name in fg.APPEARANCE["kreis"]:
            shapes = fg.player_shapes(fg.start_position(), ("Nico", {"kreis": key}))
            self.assertEqual(shapes[0]["line"], fg.RING_COLORS[key])
            self.assertEqual(shapes[-1]["color"], fg.RING_COLORS[key])
        # alte Spielstaende ohne Kreis bekommen Pink
        self.assertEqual(fg.normalize_appearance({})["kreis"], "pink")

    def test_avatar_alle_varianten(self):
        for part, options in fg.APPEARANCE.items():
            for key, _name in options:
                shapes = fg.avatar_shapes({part: key})
                self.assertTrue(shapes)
                for kind, coords, color in shapes:
                    self.assertIn(kind, ("oval", "rect", "line"))
                    self.assertEqual(len(coords), 4)
                    self.assertTrue(color.startswith("#"))


def _right_answer(task, state=None):
    if state is not None:
        task = state.prepared_task(task)
    available = state.available_parts(task) if state is not None else None
    return fg.find_solution(task, available)


def _wrong_answer(task):
    if task["typ"] == "auswahl":
        return [o for o in task["optionen"] if o != task["antwort"]][0]
    return {}


def _task(task_id):
    return fg.task_by_id(task_id)


def _solved_event(stamp, task, answer, day, state=None):
    available = state.available_parts(task) if state is not None else None
    stock = state.stock() if state is not None else None
    payload = fg.evaluate(task, answer, False, topic_levels(100), day, BALANCING, available,
                          None, stock)
    return (stamp, fg.EV_SOLVED, payload)


def _day_ends(count):
    return [("d%03d" % index, fg.EV_DAY_END, {"tag": index + 1, "gehalt": 0})
            for index in range(count)]


class BauteileTest(unittest.TestCase):
    def parts(self, *ids):
        return {fg.part(pid)["typ"]: fg.part(pid) for pid in ids}

    def test_kompatibilitaet(self):
        ok = self.parts("mb_a620_matx", "cpu_r5_7600", "ram_ddr5_2x8", "ssd_nvme_500",
                        "nt_300", "geh_matx")
        self.assertEqual(fg.compatibility_problems(ok), [])
        cases = [
            (("mb_a620_matx", "cpu_i5_13400"), "Sockel"),
            (("mb_b760_matx", "ram_ddr5_2x8"), "DDR5"),
            (("mb_a620_matx", "ram_ddr5_2x8"), None),
            (("mb_h610_itx", "ram_ddr4_4x8"), "Steckplätze"),
            (("mb_b650_atx", "geh_matx"), "Gehäuse"),
            (("mb_h610_itx", "ssd_nvme_500"), "M.2"),
            (("mb_h610_itx", "ssd_sata_500"), None),
            (("cpu_r7_7700x", "gpu_4070", "nt_450"), "zu schwach"),
            (("cpu_r7_7700x", "gpu_4070", "nt_650"), None),
        ]
        for ids, word in cases:
            problems = fg.compatibility_problems(self.parts(*ids))
            if word is None:
                self.assertEqual(problems, [], ids)
            else:
                self.assertEqual(len(problems), 1, ids)
                self.assertIn(word, problems[0], ids)

    def test_netzteil_formel(self):
        # (105 + 200 + 60) * 1,3 = 474,5 -> 475 W
        self.assertEqual(fg.psu_needed(fg.part("cpu_r7_7700x"), fg.part("gpu_4070")), 475)
        self.assertEqual(fg.psu_needed(fg.part("cpu_r5_7600")), 163)

    def test_pc_bauen(self):
        task = _task("pc-servicecenter")
        right = fg.find_solution(task)
        self.assertEqual(fg.check_answer(task, right), (True, 0))
        wrong = dict(right, cpu="cpu_i5_13400f", gehaeuse="geh_itx")
        problems = fg.build_problems(task, wrong)
        self.assertTrue(any("Sockel" in text for text in problems))
        self.assertTrue(any("Gehäuse" in text for text in problems))
        # Leerer Steckplatz und Teil, das nicht bereitliegt
        missing = dict(right)
        del missing["netzteil"]
        self.assertIn("Netzteil fehlt noch.", fg.build_problems(task, missing))
        foreign = dict(right, ram="ram_ddr5_2x16")
        self.assertIn("Arbeitsspeicher fehlt noch.", fg.build_problems(task, foreign))
        payload = fg.evaluate(task, wrong, False, topic_levels(100), 4)
        self.assertFalse(payload["richtig"])
        self.assertEqual(payload["fehler"], len(payload["probleme"]))
        text = fg.result_text(task, payload)
        self.assertIn("Probleme", text)
        self.assertIn("Eine passende Zusammenstellung", text)

    def test_kein_bild_ohne_grafik(self):
        task = _task("pc-servicecenter")
        answer = {"mainboard": "mb_b760_matx", "cpu": "cpu_i5_13400f"}
        self.assertTrue(any("Kein Bild" in text for text in fg.build_problems(task, answer)))
        # Mit Grafikkarte ist die CPU ohne Grafik in Ordnung
        task = _task("grafik-arbeitsplatz")
        answer = fg.find_solution(task, task["teile"] + ["nt_650"])
        answer["cpu"] = "cpu_i5_13400f"
        problems = fg.build_problems(task, answer, task["teile"] + ["nt_650"])
        self.assertFalse(any("Kein Bild" in text for text in problems))

    def test_bestellung(self):
        task = _task("ram-leitstelle")
        self.assertEqual(fg.valid_carts(task), [{"a3": 2}])
        self.assertEqual(fg.check_answer(task, {"a3": 2}), (True, 0))
        checks = [
            ({}, "leer"),
            ({"a1": 2}, "DDR5"),
            ({"a4": 2}, "zu klein"),
            ({"a2": 2}, "Zu spät"),
            ({"a3": 1, "a5": 1}, "Budget"),
            ({"a3": 3}, "Zu viel"),
            ({"a3": 1}, "nicht gedeckt"),
        ]
        for cart, word in checks:
            problems = fg.order_problems(task, cart)
            self.assertTrue(any(word in text for text in problems), (cart, problems))
        self.assertEqual(fg.cart_total(task, {"a3": 2, "a1": 0}), (110, 2))

    def test_ersparnis_und_lieferung(self):
        task = _task("ssd-automaten")
        cheap = fg.evaluate(task, {"s2": 3}, True, topic_levels(100), 6)
        dear = fg.evaluate(task, {"s2": 1, "s3": 2}, True, topic_levels(100), 6)
        self.assertTrue(cheap["richtig"] and dear["richtig"])
        self.assertGreater(cheap["ersparnis_bonus"], dear.get("ersparnis_bonus", 0))
        self.assertEqual(cheap["geld"] - dear["geld"],
                         cheap["ersparnis_bonus"] - dear.get("ersparnis_bonus", 0))
        self.assertEqual(cheap["kosten"], 126)
        self.assertEqual(cheap["lieferung"], [{"teil": "ssd_sata_500", "menge": 3,
                                               "haendler": "kabelkoenig", "ankunft": 8}])
        self.assertEqual({item["ankunft"] for item in dear["lieferung"]}, {7, 8})
        self.assertIn("Arbeitstag 8", fg.result_text(task, cheap))
        wrong = fg.evaluate(task, {"s1": 3}, True, topic_levels(100), 6)
        # Falsch bestellt: Die Ware kommt trotzdem (ohne Spar-Bonus)
        self.assertTrue(wrong["fehllieferung"])
        self.assertEqual(wrong["lieferung"][0]["menge"], 3)
        self.assertNotIn("ersparnis_bonus", wrong)
        self.assertLess(wrong["geld"], 0)
        self.assertIn("Rainer", fg.result_text(task, wrong))
        self.assertIn("So hätte es gepasst", fg.result_text(task, wrong))

    def test_unloesbare_inhalte_werden_gefunden(self):
        content = json.loads(json.dumps(fg.GAME))
        order = next(t for t in content["aufgaben"] if t["id"] == "ram-leitstelle")
        order["budget"] = 50
        build = next(t for t in content["aufgaben"] if t["id"] == "pc-servicecenter")
        build["teile"].remove("nt_300")
        problems = fg.validate_game_content(content)
        self.assertTrue(any("ram-leitstelle" in p and "keine gueltige" in p
                            for p in problems), problems)
        self.assertTrue(any("pc-servicecenter" in p and "nicht bauen" in p
                            for p in problems), problems)
        # Der Folgeauftrag haengt an der (jetzt unmoeglichen) Bestellung
        self.assertTrue(any("leitstelle-pc" in p for p in problems), problems)


class LagerTest(unittest.TestCase):
    def test_folgeauftrag_wartet_auf_lieferung(self):
        order = _task("ram-leitstelle")
        events = _day_ends(3)                              # Arbeitstag 4
        events.append(_solved_event("e1", order, {"a3": 2}, 4))
        state = fg.GameState(events)
        self.assertNotIn("leitstelle-pc", [t["id"] for t in state._pool()])
        self.assertEqual([t["id"] for t in state.waiting_for_delivery()], ["leitstelle-pc"])
        store = state.warehouse()
        self.assertEqual(store["unterwegs"][0]["teil"], "ram_ddr4_2x8")
        self.assertEqual(store["unterwegs"][0]["ankunft"], 6)
        self.assertEqual(_ordered_stock(state), {})
        self.assertIn("Arbeitstag 6", fg.warehouse_summary(state))

        events += [("f%d" % i, fg.EV_DAY_END, {"tag": 4 + i, "gehalt": 0}) for i in range(2)]
        state = fg.GameState(events)                       # Arbeitstag 6
        self.assertEqual(state.day, 6)
        self.assertTrue(state.arrived("ram-leitstelle"))
        self.assertEqual(_ordered_stock(state), {"ram_ddr4_2x8": 2})
        build = _task("leitstelle-pc")
        self.assertIn(build["id"], [t["id"] for t in state._pool()])
        self.assertIn("ram_ddr4_2x8", state.available_parts(build))
        # Der Grafik-Arbeitsplatz darf den RAM nicht aus dem Lager nehmen
        self.assertNotIn("ram_ddr4_2x8", state.available_parts(_task("grafik-arbeitsplatz")))

        answer = fg.find_solution(build, state.available_parts(build))
        events.append(_solved_event("g1", build, answer, 6, state))
        state = fg.GameState(events)
        self.assertEqual(_ordered_stock(state), {"ram_ddr4_2x8": 1})
        self.assertEqual(state.warehouse()["bestand"][0], ("ram_ddr4_2x8", 1))

    def test_ware_mit_empfaenger_geht_nicht_ins_lager(self):
        task = _task("notebook-chefin")
        events = _day_ends(4) + [_solved_event("e1", task, {"b2": 1}, 5)]
        events += [("x1", fg.EV_DAY_END, {"tag": 5, "gehalt": 0})]
        state = fg.GameState(events)
        self.assertEqual(_ordered_stock(state), {})
        handed = state.warehouse()["ausgeliefert"]
        self.assertEqual(handed[0]["empfaenger"], "sabine")

    def test_tag_endet_auch_beim_warten(self):
        # Alles erledigt ausser den Auftraegen, die auf Ware warten
        events = []
        for index, task in enumerate(fg.GAME["aufgaben"]):
            if task.get("nach"):
                continue
            stamp, kind, payload = _solved_event("s%02d" % index, task,
                                                 fg.find_solution(task), 1)
            for item in payload.get("lieferung", []):
                item["ankunft"] = 9
            events.append((stamp, kind, payload))
        events += [("z%d" % i, fg.EV_DAY_END, {"tag": i + 1, "gehalt": 0}) for i in range(4)]
        state = fg.GameState(events)                       # Tag 5, Ware kommt Tag 9
        self.assertEqual(state.open_tickets(), [])
        self.assertFalse(state.handled)
        self.assertTrue(state.waiting_for_delivery())
        self.assertTrue(state.can_end_day())

    def test_lagerist_zeigt_bestand(self):
        rainer = fg.colleague("rainer")
        state = fg.GameState([])
        title, text = fg.office_message(rainer["platz"], rainer, {}, state=state)
        self.assertIn("Lagerist", title)
        self.assertIn("Auf Lager: %d Teile" % sum(fg.GAME["hardware"]["grundbestand"].values()),
                      text)

    def test_lager_nur_durch_die_tuer(self):
        # Von der Verwaltung ins Lager fuehrt der Weg durch den Flur
        hall = fg.GAME["gebaeude"]["flur"]
        route = fg.walk_path((22.5, 3.0), (25.5, 5.3))
        self.assertTrue(route)
        self.assertTrue(any(hall["y"] <= y <= hall["y"] + hall["h"] for _x, y in route))
        self.assertEqual(fg.door_side(fg.room("lager")), "w")
        self.assertEqual(fg.door_side(fg.room("helpdesk")), "n")
        self.assertEqual(fg.door_side(fg.room("chefbuero")), "s")


class RackTest(unittest.TestCase):
    def setUp(self):
        self.task = fg.task_by_id("rack-leitstelle")
        # Plaetze: 0/1 Server 1 HE, 2 Altserver 4 HE, 3 Switch, 4 Patchpanel, 5 USV
        self.good = {"5": 1, "0": 3, "1": 4, "3": 5, "4": 6}

    def test_richtige_belegung(self):
        self.assertEqual(fg.rack_problems(self.task, self.good), [])
        self.assertEqual(fg.check_answer(self.task, self.good), (True, 0))

    def test_leer_und_ueberlappung(self):
        self.assertEqual(fg.rack_problems(self.task, {}), ["Der Schrank ist noch leer."])
        answer = dict(self.good, **{"1": 3})
        self.assertTrue(any("überlappen in HE 3" in p
                            for p in fg.rack_problems(self.task, answer)))

    def test_ragt_oben_heraus(self):
        answer = dict(self.good, **{"4": 13})
        self.assertTrue(any("passt ab HE 13 nicht" in p
                            for p in fg.rack_problems(self.task, answer)))

    def test_usv_nach_unten(self):
        answer = {"0": 1, "1": 2, "3": 3, "4": 4, "5": 5}
        problems = fg.rack_problems(self.task, answer)
        self.assertIn("Die USV gehört ganz nach unten, unter alle anderen Geräte.", problems)
        answer = {"5": 5, "0": 7, "1": 8, "3": 9, "4": 10}
        self.assertTrue(any("wiegt 24 kg" in p for p in fg.rack_problems(self.task, answer)))

    def test_patchpanel_neben_switch(self):
        answer = dict(self.good, **{"4": 8})
        problems = fg.rack_problems(self.task, answer)
        self.assertTrue(any(p.startswith("Patchpanel") for p in problems))
        self.assertTrue(any(p.startswith("Switch") for p in problems))

    def test_strom_und_kuehlung(self):
        answer = dict(self.good, **{"2": 7})           # Altserver 650 W dazu
        problems = fg.rack_problems(self.task, answer)
        self.assertTrue(any("USV schafft mit 20 % Reserve nur 800 W" in p
                            and "1255 W" in p for p in problems), problems)
        self.assertTrue(any("Kühlung" in p for p in problems))

    def test_vorgaben(self):
        answer = {"5": 1, "0": 3, "3": 4, "4": 5}          # nur ein Server
        self.assertTrue(any("2 × Server" in p for p in fg.rack_problems(self.task, answer)))
        task = json.loads(json.dumps(self.task))
        task["vorgaben"]["frei_min"] = 7                  # belegt sind 6 von 12 HE
        self.assertTrue(any("mindestens 7 HE" in p and "frei sind 6" in p
                            for p in fg.rack_problems(task, self.good)))

    def test_traglast_und_ports(self):
        task = fg.task_by_id("rack-servicecenter")
        # 6 = USV 3000 W (48 kg), 2 = PoE-Switch 48, 5 = Patchpanel 48
        problems = fg.rack_problems(task, {"6": 1, "2": 4, "5": 5})
        self.assertEqual(problems, ["Zu schwer: 57 kg bei 50 kg Traglast des Schranks."])
        problems = fg.rack_problems(task, {"7": 1, "0": 3, "3": 4})
        self.assertTrue(any("Zu wenige Ports (Switch): 24" in p for p in problems))
        # Zwei 24er-Paare sind ebenso richtig
        self.assertEqual(fg.rack_problems(task, {"7": 1, "3": 3, "0": 4, "1": 5, "4": 6}), [])

    def test_usv_im_raum(self):
        task = fg.task_by_id("rack-serverraum")
        # Storage + 2 Server + PoE-Switch = 1670 W: zu viel fuer Kuehlung und USV
        answer = {"0": 1, "1": 3, "2": 5, "4": 7, "6": 8}
        problems = fg.rack_problems(task, answer)
        self.assertTrue(any("nur 1600 W" in p for p in problems), problems)
        answer["5"] = answer.pop("4")
        self.assertEqual(fg.rack_problems(task, answer), [])

    def test_einbauen_verdraengt_und_rutscht(self):
        answer = fg.rack_place(self.task, {}, 5, 12)          # USV (2 HE) ganz oben
        self.assertEqual(answer, {"5": 11})
        answer = fg.rack_place(self.task, answer, 2, 9)        # Altserver HE 9-12
        self.assertEqual(answer, {"2": 9})                     # USV ist wieder frei
        answer = fg.rack_place(self.task, answer, 5, 1)
        self.assertEqual(fg.rack_occupant(self.task, answer, 2), 5)
        self.assertEqual(fg.rack_occupant(self.task, answer, 12), 2)
        self.assertIsNone(fg.rack_occupant(self.task, answer, 5))

    def test_anzeige_und_loesungstext(self):
        text, over = fg.rack_summary(self.task, self.good)
        self.assertIn("6 von 12 HE", text)
        self.assertIn("605 W von 800 W", text)
        self.assertFalse(over)
        payload = fg.evaluate(self.task, {"0": 1}, True, topic_levels(100), 6)
        self.assertFalse(payload["richtig"])
        self.assertIn("Eine passende Belegung: HE 1–2: USV 1000 W",
                      fg.result_text(self.task, payload))

    def test_unloesbarer_schrank_wird_gefunden(self):
        content = json.loads(json.dumps(fg.GAME))
        task = next(t for t in content["aufgaben"] if t["id"] == "rack-leitstelle")
        task["schrank"]["traglast"] = 40
        problems = fg.validate_game_content(content)
        self.assertTrue(any("rack-leitstelle" in p and "nicht richtig bestuecken" in p
                            for p in problems), problems)


class FormularTest(unittest.TestCase):
    def test_eingaben_tolerant(self):
        self.assertEqual(fg.parse_number("1.234,50 €"), 1234.5)
        self.assertEqual(fg.parse_number("7351.34"), 7351.34)
        self.assertEqual(fg.parse_number("12.000"), 12000)
        self.assertEqual(fg.parse_number("16 TB"), 16)
        self.assertEqual(fg.parse_number("66,7 %"), 66.7)
        self.assertIsNone(fg.parse_number("viel"))
        self.assertEqual(fg.parse_prefix("/26"), 26)
        self.assertEqual(fg.parse_prefix("26"), 26)
        self.assertEqual(fg.parse_prefix("255.255.255.192"), 26)
        self.assertIsNone(fg.parse_prefix("255.0.255.0"))
        self.assertEqual(fg.parse_ip(" 10.20.0.128/26 "), "10.20.0.128")
        self.assertIsNone(fg.parse_ip("10.20.0.300"))

    def test_ip_plan_gleich_gross(self):
        task = fg.task_by_id("ipplan-talbahn")
        values = {f["id"]: f["anzeige"] for f in fg.form_fields(task)}
        self.assertEqual(values["praefix"], "/26")
        self.assertEqual(values["hosts"], "62")
        self.assertEqual(values["2.netz"], "192.168.40.128")
        self.assertEqual(values["3.broadcast"], "192.168.40.255")

    def test_ip_plan_vlsm(self):
        task = fg.task_by_id("vlsm-talbahn")
        values = {f["id"]: f["anzeige"] for f in fg.form_fields(task)}
        self.assertEqual([values["%d.praefix" % i] for i in range(4)],
                         ["/25", "/26", "/27", "/28"])
        self.assertEqual(values["3.netz"], "10.20.0.224")
        self.assertEqual(values["3.broadcast"], "10.20.0.239")
        # Reihenfolge in der Aufgabe egal: vergeben wird nach Groesse
        swapped = json.loads(json.dumps(task))
        swapped["daten"]["teilnetze"].reverse()
        plan = dict(fg.ip_plan(swapped))
        self.assertEqual(str(plan["WLAN"]), "10.20.0.0/25")
        self.assertEqual(str(plan["Technik"]), "10.20.0.224/28")

    def test_raid_wie_der_rechner(self):
        from fisi_core import raid_values
        task = fg.task_by_id("raid-dateiserver-neu")
        values = {f["id"]: f["soll"] for f in fg.form_fields(task)}
        self.assertEqual(values["netto"], raid_values("RAID 6", 6, 4)["netto"])
        self.assertEqual((values["brutto"], values["netto"], values["toleranz"]), (24, 16, 2))

    def test_angebot_und_leasing(self):
        task = fg.task_by_id("angebot-leitstelle")
        values = {f["id"]: f["soll"] for f in fg.form_fields(task)}
        self.assertEqual(values["netto"], 6177.6)
        self.assertEqual(values["ust"], 1173.74)
        self.assertEqual(values["brutto"], 7351.34)
        task = fg.task_by_id("leasing-server")
        values = {f["id"]: f["soll"] for f in fg.form_fields(task)}
        self.assertEqual((values["leasing"], values["kauf"], values["differenz"]),
                         (15940, 14400, 1540))
        self.assertEqual(values["guenstiger"], "Kauf")

    def test_pruefung_und_rueckmeldung(self):
        task = fg.task_by_id("angebot-leitstelle")
        answer = fg.find_solution(task)
        self.assertEqual(fg.check_answer(task, answer), (True, 0))
        answer["brutto"] = "7351,33"                     # ein Cent Rundung ist ok
        self.assertTrue(fg.check_answer(task, answer)[0])
        answer["gewinn"] = "617,76"                      # Gewinn auf den Netto gerechnet
        answer["ust"] = ""
        right, errors = fg.check_answer(task, answer)
        self.assertEqual((right, errors), (False, 2))
        payload = fg.evaluate(task, answer, False, topic_levels(100), 7)
        text = fg.result_text(task, payload)
        self.assertIn("2 Felder stimmen nicht", text)
        self.assertIn("„617,76“ stimmt nicht, richtig ist 561,60 €", text)
        self.assertIn("Umsatzsteuer (19 %) fehlt", text)
        check = fg.form_check(task, answer)
        self.assertFalse(check["gewinn"])
        self.assertTrue(check["netto"])

    def test_kaputtes_formular_wird_gefunden(self):
        content = json.loads(json.dumps(fg.GAME))
        task = next(t for t in content["aufgaben"] if t["id"] == "raid-dateiserver-neu")
        task["daten"]["platten"] = 3
        problems = fg.validate_game_content(content)
        self.assertTrue(any("raid-dateiserver-neu" in p and "nicht berechnen" in p
                            for p in problems), problems)


class TerminalTest(unittest.TestCase):
    def setUp(self):
        self.task = _task("terminal-datenplatte")

    def test_richtiger_ablauf(self):
        answer = fg.find_solution(self.task)
        review = fg.terminal_review(self.task, answer)
        self.assertTrue(review["richtig"])
        self.assertEqual((review["fehlgriffe"], review["gefahr"], review["offen"]), (0, 0, 0))
        self.assertEqual(fg.check_answer(self.task, answer), (True, 0))
        self.assertEqual(fg.terminal_commands(self.task)[0], "lsblk")

    def test_ein_fehlgriff_ist_erlaubt(self):
        answer = fg.find_solution(self.task)
        answer["schritte"][0] = [0, 1]                  # erst df -h, dann lsblk
        right, errors = fg.check_answer(self.task, answer)
        self.assertEqual((right, errors), (True, 1))
        payload = fg.evaluate(self.task, answer, False, topic_levels(100), 9)
        self.assertTrue(payload["richtig"])
        self.assertEqual(payload["fehlgriffe"], 1)
        self.assertIn("Ein Fehlgriff war dabei", fg.result_text(self.task, payload))
        answer["schritte"][3] = [0, 2]                  # zweiter Fehlgriff
        payload = fg.evaluate(self.task, answer, False, topic_levels(100), 9)
        self.assertFalse(payload["richtig"])
        text = fg.result_text(self.task, payload)
        self.assertIn("2 Fehlgriffe, erlaubt ist 1", text)
        self.assertIn("Richtiger Ablauf: lsblk →", fg.solution_text(self.task))

    def test_gefaehrlicher_befehl(self):
        answer = fg.find_solution(self.task)
        answer["schritte"][1] = [1, 2]                  # parted auf der Systemplatte
        kind, command, output, hint = fg.terminal_try(self.task, 1, 1)
        self.assertEqual(kind, fg.TRY_DANGER)
        self.assertIn("Ulla", output[0])
        payload = fg.evaluate(self.task, answer, False, topic_levels(100), 9)
        self.assertFalse(payload["richtig"])
        self.assertEqual(payload["gefahr"], 1)
        # Fehler kostet Fachkompetenz, der gefaehrliche Befehl zusaetzlich Sicherheit
        self.assertEqual(payload["reputation"]["sicherheit"], -BALANCING["gefahr_verlust"])
        self.assertIn("gefährlicher Befehl", fg.result_text(self.task, payload))
        self.assertTrue(any("ist gefährlich" in p for p in payload["probleme"]))

    def test_unvollstaendig_und_unsinn(self):
        review = fg.terminal_review(self.task, {"schritte": [[1], [9, "x"]]})
        self.assertFalse(review["richtig"])
        self.assertEqual(review["offen"], 4)
        # Versuche nach dem richtigen Befehl zaehlen nicht mehr
        answer = fg.find_solution(self.task)
        answer["schritte"][0] = [1, 0, 0]
        self.assertTrue(fg.terminal_review(self.task, answer)["richtig"])
        self.assertEqual(fg.terminal_review(self.task, answer)["fehlgriffe"], 0)

    def test_alle_terminal_auftraege(self):
        tasks = [t for t in fg.GAME["aufgaben"] if t["typ"] == "terminal"]
        self.assertGreaterEqual(len(tasks), 6)
        self.assertEqual({t["system"] for t in tasks}, {"linux", "windows"})
        for task in tasks:
            self.assertTrue(fg.check_answer(task, fg.find_solution(task))[0], task["id"])
            # Jeder Auftrag hat mindestens einen gefaehrlichen Befehl
            self.assertTrue(any(c.get("gefaehrlich") for step in task["schritte"]
                                for c in step["befehle"]), task["id"])

    def test_kaputter_terminal_auftrag_wird_gefunden(self):
        content = json.loads(json.dumps(fg.GAME))
        task = next(t for t in content["aufgaben"] if t["id"] == "terminal-webserver")
        for command in task["schritte"][0]["befehle"]:
            command["richtig"] = True
        task["schritte"][1]["befehle"][0]["ausgabe"] = ["x" * 80]
        problems = fg.validate_game_content(content)
        self.assertTrue(any("genau einen richtigen" in p for p in problems), problems)
        self.assertTrue(any("laenger als 60" in p for p in problems), problems)


class DiagnoseTest(unittest.TestCase):
    def setUp(self):
        self.task = _task("diagnose-kassen-pc")

    def test_systematisch(self):
        answer = fg.find_solution(self.task)
        self.assertEqual(answer["pruefungen"], ["ipconfig", "dhcp"])
        answer["pruefungen"] = ["kabel"] + answer["pruefungen"]
        review = fg.diagnosis_review(self.task, answer)
        self.assertTrue(review["richtig"])
        self.assertTrue(review["systematisch"])
        payload = fg.evaluate(self.task, answer, False, topic_levels(100), 9)
        normal = fg.evaluate(self.task, dict(answer, pruefungen=["ipconfig", "dhcp", "kabel",
                                                                 "treiber"]),
                             False, topic_levels(100), 9)
        self.assertEqual(payload["reputation"]["zuverlaessigkeit"] -
                         normal["reputation"].get("zuverlaessigkeit", 0),
                         BALANCING["systematik_bonus"])
        self.assertIn("Systematisch vorgegangen", fg.result_text(self.task, payload))
        self.assertIn("3 hätten gereicht", fg.result_text(self.task, normal))

    def test_geraten_ist_nicht_systematisch(self):
        # Richtig geraten, ohne die entscheidenden Pruefungen: richtig, aber kein Bonus
        answer = dict(fg.find_solution(self.task), pruefungen=[])
        review = fg.diagnosis_review(self.task, answer)
        self.assertTrue(review["richtig"])
        self.assertFalse(review["systematisch"])

    def test_falsche_ursache_und_unsichere_massnahme(self):
        answer = {"pruefungen": ["kabel"], "ursache": self.task["ursachen"][1],
                  "massnahme": "Die Firewall am Kassen-PC abschalten"}
        payload = fg.evaluate(self.task, answer, False, topic_levels(100), 9)
        self.assertFalse(payload["richtig"])
        self.assertEqual(payload["gefahr"], 1)
        self.assertEqual(payload["reputation"]["sicherheit"], -BALANCING["gefahr_verlust"])
        text = fg.result_text(self.task, payload)
        self.assertIn("„ipconfig /all ausführen“", text)
        self.assertIn("ist unsicher", text)
        self.assertIn("Richtig: Ursache – Der DHCP-Dienst", text)
        self.assertEqual(fg.check_answer(self.task, {})[0], False)

    def test_ersatzteil_aus_dem_lager(self):
        order = _task("ssd-automaten")
        events = _day_ends(5)                                          # Tag 6
        events.append(_solved_event("e1", order, fg.find_solution(order), 6))
        events += [("x%d" % i, fg.EV_DAY_END, {"tag": 6 + i, "gehalt": 0}) for i in range(4)]
        state = fg.GameState(events)                                   # Tag 10
        self.assertEqual(_ordered_stock(state), {"ssd_sata_500": 3})
        task = _task("diagnose-automat-ssd")
        self.assertIn(task["id"], [t["id"] for t in state._pool()])
        self.assertEqual(state.available_parts(task), ["ssd_sata_500"])
        events.append(_solved_event("g1", task, fg.find_solution(task), 10, state))
        payload = events[-1][2]
        self.assertEqual(payload["aus_lager"], ["ssd_sata_500"])
        self.assertIn("Ersatzteil aus dem Lager eingebaut: SATA-SSD 500 GB",
                      fg.result_text(task, payload))
        self.assertEqual(_ordered_stock(fg.GameState(events)), {"ssd_sata_500": 2})

    def test_wartet_auf_die_bestellung(self):
        state = fg.GameState(_day_ends(9))                              # Tag 10
        ids = [t["id"] for t in state._pool()]
        self.assertNotIn("diagnose-automat-ssd", ids)
        self.assertNotIn("diagnose-leitstelle-netzteil", ids)

    def test_netzteil_reicht_fuer_zwei_auftraege(self):
        # Zwei Netzteile bestellt: eins fuer den Grafik-Arbeitsplatz, eins als Ersatz
        order = _task("netzteile-lager")
        events = _day_ends(4) + [_solved_event("e1", order, fg.find_solution(order), 5)]
        events += [("x%d" % i, fg.EV_DAY_END, {"tag": 5 + i, "gehalt": 0}) for i in range(6)]
        state = fg.GameState(events)                                    # Tag 11
        build = _task("grafik-arbeitsplatz")
        answer = dict(_right_answer(build, state), netzteil="nt_650")
        events.append(_solved_event("g1", build, answer, 11, state))
        state = fg.GameState(events)
        self.assertEqual(_ordered_stock(state), {"nt_650": 1})
        task = _task("diagnose-leitstelle-netzteil")
        events.append(_solved_event("g2", task, fg.find_solution(task), 11, state))
        self.assertEqual(events[-1][2]["aus_lager"], ["nt_650"])
        self.assertEqual(_ordered_stock(fg.GameState(events)), {})

    def test_zu_viele_abnehmer_werden_gefunden(self):
        content = json.loads(json.dumps(fg.GAME))
        order = next(t for t in content["aufgaben"] if t["id"] == "ssd-automaten")
        order["bedarf"][0]["menge"] = 0
        task = next(t for t in content["aufgaben"] if t["id"] == "diagnose-kassen-pc")
        task["ziel_pruefungen"] = 1
        task["unsicher"] = ["gibt es nicht"]
        problems = fg._validate_diagnosis_task(task, content)
        self.assertTrue(any("ziel_pruefungen" in p for p in problems), problems)
        self.assertTrue(any("unsichere Massnahme" in p for p in problems), problems)
        problems = fg._stock_users_problems(order, content)
        self.assertTrue(problems)


def _play_through(game, days=150, on_ticket=None):
    """Spielt Tag fuer Tag alles richtig durch. on_ticket(game, task) darf
    True liefern, wenn der Test das Ticket selbst erledigt hat."""
    for _day in range(days):
        for task in game.state.open_tickets():
            if on_ticket and on_ticket(game, task):
                continue
            answer = _right_answer(task, game.state)
            if task.get("austausch") and \
                    answer["teil"] not in game.state.available_parts(task):
                game.order_spare(task["id"], answer["teil"])
                continue
            game.solve(task["id"], answer, used_help=False)
        if game.state.all_done():
            break
        game.end_day()


def _rich_game(db, money=20000):
    game = fg.Game(db)
    game.set_profile("Test", {})
    game._log(fg.EV_DAY_END, {"tag": 1, "gehalt": money})
    return game


class ZwischenfallTest(unittest.TestCase):
    def test_auf_allen_geraeten_gleich(self):
        events = [("2026-09-29 08:00:00", fg.EV_PROFILE, {"name": "A", "aussehen": {}})]
        first, second = [], []
        for day in range(1, 40):
            state_a = fg.GameState(events + _day_ends(day - 1))
            state_b = fg.GameState(list(events + _day_ends(day - 1)))
            first.append((state_a.incident_today() or {}).get("id"))
            second.append((state_b.incident_today() or {}).get("id"))
        self.assertEqual(first, second)
        self.assertIsNone(first[0])          # Tag 1: noch kein Zwischenfall
        self.assertTrue(any(first))

    def test_hoechstens_einer_am_tag_und_keiner_doppelt(self):
        with TempDB() as db:
            game = fg.Game(db)
            game.set_profile("Test", {})
            seen = []

            def check(game, task):
                if task.get("zwischenfall"):
                    seen.append(task["id"])
                tickets = game.state.open_tickets()
                self.assertLessEqual(sum(1 for t in tickets if t.get("zwischenfall")), 1)
                self.assertLessEqual(sum(1 for t in tickets if not t.get("zwischenfall")),
                                     game.state.tickets_today)
                return False

            _play_through(game, on_ticket=check)
            self.assertTrue(game.state.all_done())
            self.assertTrue(seen)
            self.assertEqual(len(seen), len(set(seen)))
            self.assertEqual(game.state.seen_incidents, set(seen))

    def test_verschoben_kommt_nicht_wieder(self):
        with TempDB() as db:
            game = fg.Game(db)
            game.set_profile("Test", {})
            deferred = []

            def defer_incidents(game, task):
                if task.get("zwischenfall"):
                    game.defer(task["id"])
                    deferred.append(task["id"])
                    return True
                return False

            _play_through(game, on_ticket=defer_incidents)
            self.assertTrue(deferred)
            self.assertEqual(len(deferred), len(set(deferred)))
            self.assertFalse(set(deferred) & game.state.solved)

    def test_zwischenfall_zaehlt_nicht_zum_tageslimit(self):
        with TempDB() as db:
            game = fg.Game(db)
            game.set_profile("Test", {})
            for _day in range(40):
                if game.state.incident_today():
                    break
                _play_through(game, days=1)
            incident = game.state.incident_today()
            self.assertIsNotNone(incident)
            regular = [t for t in game.state.open_tickets() if not t.get("zwischenfall")]
            self.assertEqual(game.state.open_tickets()[0]["id"], incident["id"])
            game.solve(incident["id"], _right_answer(incident, game.state), False)
            self.assertEqual([t["id"] for t in game.state.open_tickets()],
                             [t["id"] for t in regular])
            self.assertIn(fg.task_by_id(incident["id"])["titel"],
                          [t["titel"] for t, _s in game.state.todays_tickets()])


class WohnungTest(unittest.TestCase):
    def test_start_mit_matratze(self):
        state = fg.GameState([])
        self.assertEqual(state.home_id, "apartment")
        placed = fg.placed_furniture(state)
        self.assertEqual([item["moebel"] for item in placed], ["matratze"])
        self.assertNotIn("matratze", [item["id"] for item in fg.shop_items()])
        shapes = fg.building_shapes(content=fg.site_content(fg.SITE_HOME, state))
        self.assertTrue(shapes)

    def test_kaufen_und_geld(self):
        with TempDB() as db:
            game = fg.Game(db)
            game.set_profile("Test", {})
            with self.assertRaises(ValueError):
                game.buy_furniture("sofa")            # noch kein Geld
            with self.assertRaises(ValueError):
                game.buy_furniture("matratze")        # gibt es nicht im Laden
            game._log(fg.EV_DAY_END, {"tag": 1, "gehalt": 1000})
            piece = game.buy_furniture("sofa")
            self.assertEqual(game.state.money, 1000 - 450)
            self.assertIn(piece, dict(fg.boxed_furniture(game.state)))
            # Der Kauf zaehlt auch auf dem anderen Geraet (gleiche Ereignisse)
            self.assertEqual(fg.GameState(db.game_events()).furniture[piece], "sofa")

    def test_aufstellen_und_regeln(self):
        with TempDB() as db:
            game = _rich_game(db)
            sofa = game.buy_furniture("sofa")
            game.place_furniture(sofa, 4.1, 0.3)
            self.assertEqual(fg.boxed_furniture(game.state), [])
            self.assertEqual(fg.home_layout(game.state)["moebel"][sofa], [4.0, 0.25, 0])
            table = game.buy_furniture("couchtisch")
            with self.assertRaisesRegex(ValueError, "stößt"):  # ueberlappt das Sofa
                game.place_furniture(table, 4.5, 0.5)
            with self.assertRaisesRegex(ValueError, "Raum"):  # ragt ueber die Wand
                game.place_furniture(table, 8.5, 2.0)
            with self.assertRaisesRegex(ValueError, "Tür"):   # versperrt die Tuer
                game.place_furniture(table, 1.6, 4.25)
            game.place_furniture(table, 4.5, 2.0)
            carpet = game.buy_furniture("teppich")
            game.place_furniture(carpet, 4.0, 1.5)    # Teppich darf unter Moebel
            self.assertEqual(fg.furniture_at(game.state, 5.0, 2.4)["moebel"], "couchtisch")
            # drehen: aus 3,6 x 1,4 wird 1,4 x 3,6
            game.place_furniture(sofa, 7.0, 0.25, 1)
            item = next(i for i in fg.placed_furniture(game.state) if i["stueck"] == sofa)
            self.assertEqual((item["w"], item["h"]), (1.4, 3.6))
            game.box_furniture(table)
            self.assertIn(table, dict(fg.boxed_furniture(game.state)))

    def test_verkaufen_zum_halben_preis(self):
        with TempDB() as db:
            game = _rich_game(db, 1000)
            piece = game.buy_furniture("fernseher")
            game.place_furniture(piece, 3.0, 0.25)
            price = game.sell_furniture(piece)
            self.assertEqual(price, 260)
            self.assertEqual(game.state.money, 1000 - 520 + 260)
            self.assertNotIn(piece, game.state.furniture)
            self.assertNotIn(piece, fg.home_layout(game.state)["moebel"])

    def test_umzug(self):
        with TempDB() as db:
            game = _rich_game(db, 3000)
            bed = game.buy_furniture("bett_einzel")
            game.place_furniture(bed, 7.0, 0.25)
            self.assertEqual([w["id"] for w in fg.moves_available(game.state)],
                             ["zweizimmer", "altbau", "loft"])
            with self.assertRaises(ValueError):
                game.move_home("loft", rent=False)    # zu teuer
            game.move_home("zweizimmer", rent=False)
            self.assertEqual(game.state.home_id, "zweizimmer")
            self.assertEqual(game.state.money, 3000 - 150 - 2500)
            # Alle Moebel kommen in Kartons und werden neu aufgestellt
            self.assertEqual(fg.placed_furniture(game.state), [])
            self.assertEqual(len(fg.boxed_furniture(game.state)), 2)
            self.assertNotIn("zweizimmer", [w["id"] for w in fg.moves_available(game.state)])
            with self.assertRaises(ValueError):
                game.move_home("apartment")

    def test_boden_waehlen(self):
        with TempDB() as db:
            game = _rich_game(db, 0)
            game.set_floor("wohnraum", "teppichboden", "cyan")
            building = fg.home_building(game.state)
            room = next(r for r in building["raeume"] if r["id"] == "wohnraum")
            self.assertEqual(room["boden"], "teppichboden")
            self.assertEqual(room["bodenfarbe"], fg.floor_color("cyan"))

    def test_bett_schreibtisch_und_tuer(self):
        with TempDB() as db:
            game = _rich_game(db, 1000)
            desk = game.buy_furniture("schreibtisch")
            game.place_furniture(desk, 5.0, 0.25)
            state = game.state
            content = fg.site_content(fg.SITE_HOME, state)
            door = content["gebaeude"]["flur"]["spieler"]
            _t, _x, actions = fg.place_message(fg.SITE_HOME, door, None, state, content)
            self.assertEqual(actions, [("buero", "Zur Arbeit")])
            _t, _x, actions = fg.place_message(fg.SITE_HOME, (2.2, 3.9), None, state, content)
            self.assertEqual(actions, [("schlafen", "Schlafen")])
            _t, _x, actions = fg.place_message(fg.SITE_HOME, (6.0, 1.6), None, state, content)
            self.assertEqual(actions, [("lernen", "Lernen")])
            self.assertTrue(fg.walk_path(door, (6.0, 1.8), content=content))
            self.assertTrue(fg.sleep_text(state))


class KundeTest(unittest.TestCase):
    def test_alle_raeume_erreichbar(self):
        # Jeder Raum jedes Kundenorts ist vom Eingang aus zu betreten
        for place in fg.customer_places():
            view = fg.site_content(place["id"])
            start = view["gebaeude"]["flur"]["spieler"]
            for item in view["gebaeude"]["raeume"]:
                door = item["tuer"]
                middle = (door["von"] + door["bis"]) / 2.0
                inside = (middle, item["y"] + 0.6) if item["y"] >= start[1] \
                    else (middle, item["y"] + item["h"] - 0.6)
                self.assertTrue(fg.walk_path(start, inside, content=view),
                                "%s/%s" % (place["id"], item["id"]))

    def test_petra_arbeitet_beim_kunden(self):
        state = fg.GameState([])
        office = [p["id"] for p in fg.people_at_site(fg.SITE_OFFICE, state)]
        customer = [p["id"] for p in fg.people_at_site("talheim", state)]
        self.assertNotIn("petra", office)
        self.assertIn("petra", customer)
        self.assertEqual(fg.task_site(fg.task_by_id("diagnose-automat-ssd")), "talheim")
        self.assertEqual(fg.task_site(fg.task_by_id("rack-talheim-nord")), "talheim_nord")

    def test_talheim_nord_ab_tag_12(self):
        early = fg.GameState(_day_ends(3))
        late = fg.GameState(_day_ends(11))
        self.assertEqual([p["id"] for p in fg.open_places(early)], ["talheim"])
        self.assertEqual([p["id"] for p in fg.open_places(late)], ["talheim", "talheim_nord"])

    def test_bahnhof_waechst_mit(self):
        building = fg.customer_place("talheim_nord")["gebaeude"]
        before = fg._visible_building(building, set())
        after = fg._visible_building(building, {"rack-talheim-nord", "pc-talheim-nord",
                                                "abnahme-talheim-nord",
                                                "kamera-loeschfrist"})

        def kinds(item):
            return [d["typ"] for r in item["raeume"] for d in r.get("deko", [])] + \
                [d["typ"] for d in item["flur"].get("deko", [])]
        self.assertIn("absperrband", kinds(before))
        self.assertNotIn("wimpel", kinds(before))
        self.assertIn("wimpel", kinds(after))
        self.assertNotIn("absperrband", kinds(after))

    def test_auftrag_vor_ort_und_ausgang(self):
        state = fg.GameState([])
        content = fg.site_content("talheim", state)
        quests = state.quests("talheim")
        self.assertTrue(quests)
        for person_id, tasks in quests.items():
            person = next(p for p in content["kollegen"] if p["id"] == person_id)
            title, _text, actions = fg.place_message("talheim", person["platz"], person,
                                                     state, content)
            self.assertIn("Auftrag", title)
            self.assertEqual(actions[0][0], "auftrag:" + tasks[0]["id"])
        entrance = content["gebaeude"]["flur"]["spieler"]
        _t, _x, actions = fg.place_message("talheim", entrance, None, state, content)
        self.assertEqual(actions, [("buero", "Zurück ins Büro")])
        texts = [s["text"] for s in fg.building_shapes(quests=set(quests), content=content)
                 if s["k"] == "text"]
        self.assertEqual(texts.count("!"), len(quests))

    def test_wartet_an_der_stelle(self):
        with TempDB() as db:
            game = fg.Game(db)
            game.set_profile("Test", {})
            found = []

            def look(game, task):
                if task["id"] == "diagnose-automat-ssd":
                    petra = next(p for p in fg.people_at_site("talheim", game.state)
                                 if p["id"] == "petra")
                    found.append(petra["platz"])
                return False

            _play_through(game, on_ticket=look)
            self.assertEqual(found[0], [4.9, 10.5])
            petra = next(p for p in fg.people_at_site("talheim", game.state)
                         if p["id"] == "petra")
            self.assertEqual(petra["platz"], [2.3, 2.95])


class RackAusLagerTest(unittest.TestCase):
    def test_geraete_kommen_aus_dem_lager(self):
        with TempDB() as db:
            game = fg.Game(db)
            game.set_profile("Test", {})
            seen = {}

            def watch(game, task):
                if task["id"] == "rack-talheim-nord":
                    prepared = game.state.prepared_task(task)
                    seen["stock"] = dict(game.state.stock())
                    seen["lager_ab"] = prepared["lager_ab"]
                    seen["geraete"] = prepared["geraete"]
                    payload = game.solve(task["id"], _right_answer(task, game.state), False)
                    seen["payload"] = payload
                    seen["after"] = dict(game.state.stock())
                    return True
                return False

            _play_through(game, on_ticket=watch)
            self.assertTrue(seen, "Rack-Auftrag kam nicht dran")
            self.assertEqual(seen["lager_ab"], 2)
            self.assertGreater(len(seen["geraete"]), 2)
            payload = seen["payload"]
            self.assertTrue(payload["richtig"])
            self.assertTrue(payload["aus_lager"])
            for part_id in payload["aus_lager"]:
                self.assertEqual(seen["after"].get(part_id, 0),
                                 seen["stock"][part_id] - payload["aus_lager"].count(part_id))
            self.assertIn("Aus dem Lager eingebaut",
                          fg.result_text(fg.task_by_id("rack-talheim-nord"), payload))


class StoryTest(unittest.TestCase):
    def test_szenen_und_feierabend(self):
        for day in range(12, 17):
            self.assertTrue(fg.morning_text(day), day)
        self.assertEqual(fg.morning_text(3), "")
        texts = {fg.day_end_text(day) for day in range(1, 6)}
        self.assertEqual(len(texts), 5)

    def test_reaktionen(self):
        task = fg.task_by_id("diagnose-automat-ssd")
        payload = {"richtig": True, "tag": 4}
        self.assertTrue(fg.reaction_text(task, payload).startswith("Petra: "))
        for person in fg.all_people():
            self.assertTrue((person.get("reaktionen") or {}).get("richtig"), person["id"])
            self.assertTrue((person.get("reaktionen") or {}).get("falsch"), person["id"])

    def test_neue_kollegen_ab_tag_12(self):
        early = [p["id"] for p in fg.people_at_site(fg.SITE_OFFICE, fg.GameState([]))]
        late = [p["id"] for p in fg.people_at_site(fg.SITE_OFFICE,
                                                   fg.GameState(_day_ends(11)))]
        self.assertNotIn("tim", early)
        self.assertIn("tim", late)
        self.assertIn("karin", late)


class FalschlieferungTest(unittest.TestCase):
    def _play_to_order(self, game, order_id):
        """Spielt richtig, bis die Bestellung order_id offen ist."""
        for _day in range(40):
            for task in game.state.open_tickets():
                if task["id"] == order_id:
                    return task
                game.solve(task["id"], _right_answer(task, game.state), False)
            game.end_day()
        self.fail("Bestellung kam nicht dran")

    def test_falsche_bestellung_wird_geliefert_und_muss_zurueck(self):
        with TempDB() as db:
            game = fg.Game(db)
            game.set_profile("Test", {})
            order = self._play_to_order(game, "ssd-automaten")
            payload = game.solve(order["id"], {"s1": 3}, False)
            self.assertFalse(payload["richtig"])
            arrival = payload["lieferung"][0]["ankunft"]
            task_id = fg.WRONG_DELIVERY + order["id"]
            # Bis zur Ankunft: kein Zwischenfall, die Bestellung ist gesperrt
            while game.state.day < arrival:
                ids = [t["id"] for t in game.state.open_tickets()]
                self.assertNotIn(task_id, ids)
                self.assertNotIn(order["id"], ids)
                for task in game.state.open_tickets():
                    game.solve(task["id"], _right_answer(task, game.state), False)
                game.end_day()
            self.assertEqual(game.state.stock().get("ssd_nvme_500"), 3)
            tickets = game.state.open_tickets()
            self.assertEqual(tickets[0]["id"], task_id)
            self.assertNotIn(order["id"], [t["id"] for t in tickets])
            incident = game.state.prepared_task(fg.task_by_id(task_id))
            self.assertIn("3 × NVMe-SSD 500 GB", incident["ticket"])
            # Verschieben hilft nicht: Er kommt am naechsten Tag wieder
            game.defer(task_id)
            for task in game.state.open_tickets():
                game.solve(task["id"], _right_answer(task, game.state), False)
            game.end_day()
            self.assertIn(task_id, [t["id"] for t in game.state.open_tickets()])
            money = game.state.money
            done = game.solve(task_id, incident["antwort"], False)
            self.assertTrue(done["richtig"])
            self.assertEqual(done["ruecksendung"], {"ssd_nvme_500": 3})
            self.assertEqual(game.state.stock().get("ssd_nvme_500", 0), 0)
            self.assertEqual(game.state.money, money + done["geld"])
            self.assertLess(done["geld"], 0)
            self.assertIn("Rücksendekosten", fg.result_text(incident, done))
            # Die Bestellung kommt wieder, jetzt ohne Spar-Bonus
            for task in game.state.open_tickets():
                if task["id"] != order["id"]:
                    game.solve(task["id"], _right_answer(task, game.state), False)
            again = self._play_to_order(game, order["id"])
            self.assertTrue(game.state.prepared_task(again).get("kein_sparbonus"))
            payload = game.solve(order["id"], {"s2": 3}, False)
            self.assertTrue(payload["richtig"])
            self.assertTrue(payload["bonus_verloren"])
            self.assertNotIn("ersparnis_bonus", payload)
            self.assertIn("Spar-Bonus", fg.result_text(again, payload))

    def test_vorlage_und_pc_handy_gleich(self):
        task = fg.task_by_id(fg.WRONG_DELIVERY + "ssd-automaten")
        self.assertIn(task["antwort"], task["optionen"])
        self.assertTrue(task["zwischenfall"])
        self.assertEqual(fg.task_site(task), fg.SITE_OFFICE)
        self.assertIsNone(fg.task_by_id(fg.WRONG_DELIVERY + "gibt-es-nicht"))


def _finish_day(game):
    """Alle offenen Tickets verschieben und den Arbeitstag beenden."""
    for task in game.state.open_tickets():
        game.defer(task["id"])
    return game.end_day()


class MieteTest(unittest.TestCase):
    """Ab 0.31: Schalter Einmalzahlung/Miete fuer Wohnungen."""

    def test_mieten_kaution_und_tagesmiete(self):
        with TempDB() as db:
            game = _rich_game(db, 1000)
            payload = game.move_home("zweizimmer", rent=True)
            self.assertEqual(payload["kaution"], 375)       # 15 % von 2.500 €
            self.assertEqual(payload["miete"], 60)
            self.assertEqual(game.state.money, 1000 - 375)
            self.assertEqual((game.state.rent, game.state.deposit), (60, 375))
            before, salary = game.state.money, game.state.salary
            day = _finish_day(game)
            self.assertEqual(day["miete"], 60)
            money_after = game.state.money
            # Verschieben kostet kein Geld, nur Reputation
            self.assertEqual(money_after, before + salary - 60)

    def test_kaufen_kostet_keine_miete(self):
        with TempDB() as db:
            game = _rich_game(db, 3000)
            game.move_home("zweizimmer", rent=False)
            self.assertEqual(game.state.money, 500)
            self.assertEqual(game.state.rent, 0)
            day = _finish_day(game)
            self.assertNotIn("miete", day)

    def test_kaution_kommt_beim_naechsten_umzug_zurueck(self):
        with TempDB() as db:
            game = _rich_game(db, 6000)
            game.move_home("zweizimmer", rent=True)          # 6000 - 375
            game.move_home("altbau", rent=False)             # + 375 - 6000
            self.assertEqual(game.state.money, 0)
            self.assertEqual((game.state.rent, game.state.deposit), (0, 0))
            day = _finish_day(game)
            self.assertNotIn("miete", day)

    def test_kaution_zaehlt_beim_umzug_mit(self):
        with TempDB() as db:
            game = _rich_game(db, 900)
            game.move_home("zweizimmer", rent=True)          # bleiben 525 €
            # Altbau-Kaution 900 €: 525 € + 375 € zurueck reichen genau
            offer = fg.move_offer(game.state, fg.apartment("altbau"), True)
            self.assertEqual(offer["fehlt"], 0)
            with self.assertRaisesRegex(ValueError, "fehlen"):
                game.move_home("loft", rent=True)            # 1.800 € Kaution
            game.move_home("altbau", rent=True)
            self.assertEqual((game.state.money, game.state.rent), (0, 140))

    def test_schalter_wirkt_nicht_rueckwirkend(self):
        folder = tempfile.mkdtemp()
        old = os.environ.get("FISI_DB_PATH")
        os.environ["FISI_DB_PATH"] = os.path.join(folder, "fisi.db")
        try:
            with TempDB() as db:
                self.assertFalse(fg.rent_mode())             # Standard: Einmalzahlung
                fg.set_rent_mode(True)
                game = _rich_game(db, 1000)
                game.move_home("zweizimmer")                 # nimmt den Schalter: Miete
                self.assertEqual(game.state.rent, 60)
                fg.set_rent_mode(False)
                # Der Mietvertrag laeuft bis zum naechsten Umzug weiter
                self.assertEqual(_finish_day(game)["miete"], 60)
        finally:
            if old is None:
                os.environ.pop("FISI_DB_PATH", None)
            else:
                os.environ["FISI_DB_PATH"] = old
            shutil.rmtree(folder, ignore_errors=True)

    def test_pc_und_handy_rechnen_gleich(self):
        with TempDB() as pc, TempDB() as handy:
            game = _rich_game(pc, 1000)
            game.move_home("zweizimmer", rent=True)
            _finish_day(game)
            fisi_sync.merge_into_local(handy, fisi_sync.export_local(pc))
            state = fg.Game(handy, "Handy").state
            self.assertEqual(state.money, game.state.money)
            self.assertEqual((state.rent, state.deposit), (60, 375))

    def test_texte(self):
        state = fg.GameState([])
        price, question = fg.move_texts(state, fg.apartment("altbau"), True)
        self.assertEqual(price, "Kaution 900 € · Miete 140 €/Tag")
        self.assertIn("140 € Miete pro Arbeitstag", question)
        self.assertEqual(fg.move_texts(state, fg.apartment("loft"), False)[0], "12.000 €")
        self.assertEqual(fg.day_end_money_text({"gehalt": 190, "miete": 140}),
                         "Gehalt: +190 €. Miete: -140 €.")

    def test_pruefung_der_mietwerte(self):
        content = json.loads(json.dumps(fg.GAME))
        del content["balancing"]["miete"]["pro_tag"]["loft"]
        content["balancing"]["miete"]["pro_tag"]["apartment"] = 20
        content["balancing"]["miete"]["kaution_anteil"] = 3
        problems = fg.validate_game_content(content)
        self.assertTrue(any("'loft'" in p for p in problems))
        self.assertTrue(any("mietfrei" in p for p in problems))
        self.assertTrue(any("kaution_anteil" in p for p in problems))


class FarbenTest(unittest.TestCase):
    """Ab 0.31: Grundfarbe und Hintergrund waehlbar, Fachbereiche fest."""

    def test_presets_aendern_nur_akzente_und_flaechen(self):
        import fisi_theme as th
        before = dict(th.CATEGORY_COLOR), dict(th.THEME_COLOR), th.C["cyan"], th.C["green"]
        try:
            th.apply_preset("gruen_lime")
            th.apply_background("anthrazit")
            self.assertEqual(th.C["accent"], "#34D399")
            self.assertEqual(th.C["bg"], "#141416")
            self.assertEqual(th.GRADIENTS["primary"], ("#047857", "#4D7C0F"))
            self.assertEqual((dict(th.CATEGORY_COLOR), dict(th.THEME_COLOR), th.C["cyan"],
                              th.C["green"]), before)
            # Unbekannte Kennung -> Standard
            self.assertEqual(th.apply_background("gibt-es-nicht")["id"], "violett")
        finally:
            th.apply_preset(th.DEFAULT_PRESET)
            th.apply_background(th.DEFAULT_BACKGROUND)

    def test_alle_hintergruende_vollstaendig(self):
        import fisi_theme as th
        for item in th.BACKGROUNDS:
            self.assertEqual(set(th.BACKGROUND_FIELDS) - set(item), set(), item["id"])
        self.assertEqual(len(set(th.BACKGROUND_IDS)), len(th.BACKGROUNDS))
        self.assertEqual(len(set(th.PRESET_IDS)), len(th.PRESETS))

    def test_lesbarkeit_aller_kombinationen(self):
        """WCAG-Kontrast: 4,5:1 fuer Schrift, auch in jeder Farbkombination."""
        import fisi_theme as th

        def lum(color):
            def part(value):
                value /= 255.0
                return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
            r, g, b = th.hex_to_rgb(color)
            return 0.2126 * part(r) + 0.7152 * part(g) + 0.0722 * part(b)

        def ratio(a, b):
            high, low = sorted((lum(a), lum(b)), reverse=True)
            return (high + 0.05) / (low + 0.05)

        surfaces = ("bg", "card", "card_alt", "card_hi")
        for back in th.BACKGROUNDS:
            for surface in surfaces:
                for key in ("text", "text_soft"):
                    self.assertGreaterEqual(ratio(th.C[key], back[surface]), 4.5)
                for key in ("text_dim", "muted"):
                    self.assertGreaterEqual(ratio(back[key], back[surface]), 4.5,
                                            (back["id"], key, surface))
                for item in th.PRESETS:
                    for key in ("accent", "accent2"):
                        self.assertGreaterEqual(ratio(item[key], back[surface]), 4.5,
                                                (item["id"], back["id"], key, surface))
        for item in th.PRESETS:
            for gradient in ("primary", "verlauf", "hero"):
                for color in item[gradient]:
                    self.assertGreaterEqual(ratio("#FFFFFF", color), 4.5,
                                            (item["id"], gradient, color))


# ============================================================================
#  Ab 0.32: Raenge, Vorlagen, Wartung, Austausch, Drucker, Zwischenfall-
#  Varianten, Ruhestand
# ============================================================================

def _content():
    """Eine veraenderbare Kopie der Spielinhalte."""
    return json.loads(json.dumps(fg.GAME))


class RangTest(unittest.TestCase):
    def test_befoerderung_braucht_arbeitstage(self):
        self.assertEqual(fg.rank_for(100), "Senior")
        self.assertEqual(fg.rank_for(100, day=1), "Azubi-Niveau")
        self.assertEqual(fg.rank_for(100, day=10), "Junior")
        self.assertEqual(fg.rank_for(100, day=30), "Fachkraft")
        self.assertEqual(fg.rank_for(100, day=60), "Senior")
        self.assertEqual(fg.rank_for(40, day=60), "Junior")

    def test_tickets_je_rang(self):
        values = [fg.tickets_per_day(rank["name"]) for rank in BALANCING["raenge"]]
        self.assertEqual(values, sorted(values))
        self.assertGreater(values[-1], values[0])
        self.assertEqual(fg.tickets_per_day("Azubi-Niveau", {"tickets_pro_tag": 3}), 3)

    def test_ticketzahl_richtet_sich_nach_dem_tagesbeginn(self):
        events = [("a", fg.EV_PROFILE, {"name": "A", "aussehen": {}})] + _day_ends(14)
        state = fg.GameState(events)
        self.assertEqual(state.day_rank, "Azubi-Niveau")   # Reputation 20 zu Beginn
        # Viel Reputation im Laufe des Tages: der Rang steigt, die Ticketzahl nicht
        events.append(("z", fg.EV_SOLVED, {"aufgabe": "x", "tag": 15, "richtig": True,
                                           "reputation": {key: 60 for key in fg.AXIS_KEYS}}))
        state = fg.GameState(events)
        self.assertEqual(state.rank, "Junior")
        self.assertEqual(state.day_rank, "Azubi-Niveau")
        self.assertEqual(state.tickets_today, fg.tickets_per_day("Azubi-Niveau"))
        events.append(("zz", fg.EV_DAY_END, {"tag": 15, "gehalt": 0}))
        state = fg.GameState(events)
        self.assertEqual(state.tickets_today, fg.tickets_per_day("Junior"))

    def test_hinweis_zum_naechsten_rang(self):
        state = fg.GameState([("a", fg.EV_PROFILE, {"name": "A", "aussehen": {}})])
        self.assertIn("Junior", fg.rank_hint(state))
        self.assertIn("Arbeitstage", fg.rank_hint(state))


class VorlagenTest(unittest.TestCase):
    def test_varianten_werden_zu_auftraegen(self):
        items = [{"id": "v", "titel": "Tausch in {{ort}}", "ticket": ["{{wer}} ruft an."],
                  "ab_tag": 3, "wiederholen": {"start": 10, "abstand": 5},
                  "varianten": [{"werte": {"ort": "A", "wer": "Petra"}},
                                {"werte": {"ort": "B", "wer": "Horst"}, "raum": "x"},
                                {"werte": {"ort": "C", "wer": "Ulla"}, "ab_tag": 99}]}]
        tasks = fg.expand_variants(items, template=True)
        self.assertEqual([t["id"] for t in tasks], ["v", "v#2", "v#3"])
        self.assertEqual([t["titel"] for t in tasks], ["Tausch in A", "Tausch in B",
                                                       "Tausch in C"])
        self.assertEqual([t["ab_tag"] for t in tasks], [10, 15, 99])
        self.assertEqual(tasks[1]["raum"], "x")
        self.assertTrue(all(t["vorlage"] == "v" and t["gruppe"] == "v" for t in tasks))
        self.assertNotIn("varianten", tasks[0])

    def test_vergessene_platzhalter_fallen_auf(self):
        content = _content()
        content["aufgaben"][0]["titel"] = "Hallo {{name}}"
        self.assertTrue(any("Platzhalter" in p for p in fg.validate_game_content(content)))

    def test_kein_auftrag_doppelt(self):
        tickets = [task["ticket"] for task in fg.GAME["aufgaben"] + fg.GAME["zwischenfaelle"]]
        self.assertEqual(len(tickets), len(set(tickets)))
        content = _content()
        content["aufgaben"][1]["ticket"] = content["aufgaben"][0]["ticket"]
        self.assertTrue(any("gleicher Tickettext" in p
                            for p in fg.validate_game_content(content)))

    def test_story_vor_vorlagen(self):
        """Story-Auftraege kommen zuerst dran, Vorlagen fuellen auf."""
        state = fg.GameState([("a", fg.EV_PROFILE, {"name": "A", "aussehen": {}})] +
                             _day_ends(200))
        pool = state._pool()
        kinds = [bool(task.get("vorlage")) for task in pool]
        self.assertEqual(kinds, sorted(kinds))


class WartungTest(unittest.TestCase):
    def setUp(self):
        self.task = _task("wartung-usv-nord")

    def test_eigene_loesung_richtig(self):
        solution = fg.find_solution(self.task)
        self.assertTrue(fg.check_answer(self.task, solution)[0])
        self.assertEqual(solution["bewertung"]["selbsttest"], fg.RATING_ISSUE)
        self.assertEqual(solution["bewertung"]["last"], fg.RATING_OK)

    def test_uebersehene_auffaelligkeit(self):
        answer = fg.find_solution(self.task)
        answer["bewertung"]["akkudatum"] = fg.RATING_OK
        review = fg.maintenance_review(self.task, answer)
        self.assertFalse(review["richtig"])
        self.assertEqual(review["uebersehen"], 1)
        self.assertIn("auffällig", review["probleme"][0])

    def test_ungeprueft_und_falscher_abschluss(self):
        answer = {"bewertung": {"last": fg.RATING_OK},
                  "abschluss": "Alles in Ordnung, nächste Wartung in drei Monaten"}
        problems = fg.answer_problems(self.task, answer)
        self.assertTrue(any("nicht geprüft" in p for p in problems))
        self.assertTrue(any("Abschluss" in p for p in problems))

    def test_folgeauftrag_nach_wartung(self):
        follow = _task("usv-akkutausch-nord")
        self.assertEqual(follow["nach"], self.task["id"])
        events = [("a", fg.EV_PROFILE, {"name": "A", "aussehen": {}})] + _day_ends(16)
        state = fg.GameState(events)
        self.assertFalse(state._ready(follow))
        events.append(_solved_event("w", self.task, fg.find_solution(self.task), 17, state))
        state = fg.GameState(events)
        self.assertTrue(state._ready(follow))
        text = fg.result_text(self.task, events[-1][2])
        self.assertIn(follow["titel"], text)

    def test_vorlage_wiederholt_sich(self):
        tasks = [task for task in fg.GAME["aufgaben"]
                 if task.get("vorlage") == "wartung-pc-reinigung"]
        self.assertGreaterEqual(len(tasks), 3)
        days = [task["ab_tag"] for task in tasks]
        self.assertEqual(days, sorted(set(days)))
        right = [fg.find_solution(task)["abschluss"] for task in tasks]
        self.assertGreater(len(set(right)), 1)     # mal alles gut, mal auffaellig


class AustauschTest(unittest.TestCase):
    def setUp(self):
        self.task = _task("usv-akkutausch-nord")

    def test_passendes_teil(self):
        self.assertEqual(fg.spare_fits(self.task, "akkusatz_48v9"), [])
        problems = fg.spare_fits(self.task, "akku_12v9_f2")
        self.assertTrue(problems)
        self.assertIn("Spannung 12 V statt 48 V", problems[0])

    def test_reihenfolge_und_falsche_schritte(self):
        answer = fg.find_solution(self.task, ["akkusatz_48v9"])
        self.assertTrue(fg.check_answer(self.task, answer, ["akkusatz_48v9"])[0])
        wrong = dict(answer, reihenfolge=list(reversed(answer["reihenfolge"])))
        self.assertTrue(any("Ablauf" in p for p in
                            fg.answer_problems(self.task, wrong, ["akkusatz_48v9"])))
        extra = dict(answer, reihenfolge=answer["reihenfolge"] +
                     [self.task["austausch"]["falsch"][0]])
        self.assertTrue(any("gehört nicht" in p for p in
                            fg.answer_problems(self.task, extra, ["akkusatz_48v9"])))
        # Passt, liegt aber nicht im Lager
        self.assertTrue(any("nicht im Lager" in p for p in
                            fg.answer_problems(self.task, answer, [])))

    def test_alle_schritte_zur_auswahl_gemischt(self):
        steps = fg.exchange_steps(self.task)
        exchange = self.task["austausch"]
        self.assertEqual(sorted(steps), sorted(exchange["schritte"] + exchange["falsch"]))
        self.assertEqual(steps, fg.exchange_steps(self.task))     # immer gleich

    def test_nachbestellen_und_einbauen(self):
        with TempDB() as db:
            game = fg.Game(db)
            game.set_profile("Test", {})
            task_id = self.task["id"]
            # Alles andere ist schon erledigt, nur der Akkutausch ist offen
            for other in fg.GAME["aufgaben"]:
                if other["id"] != task_id:
                    game._log(fg.EV_SOLVED, {"aufgabe": other["id"], "tag": 0,
                                             "richtig": True})
            for _day in range(16):
                game._log(fg.EV_DAY_END, {"tag": game.state.day, "gehalt": 0})
            self.assertTrue(game.state.is_open(task_id))
            # Nur im Lager stehende Teile koennen verbaut werden
            self.assertNotIn("akkusatz_48v9", game.state.available_parts(self.task))
            money = game.state.money
            payload = game.order_spare(task_id, "akkusatz_48v9")
            self.assertEqual(game.state.money, money - fg.part("akkusatz_48v9")["preis"])
            self.assertEqual(game.state.status_of(task_id), fg.ST_WAITING)
            self.assertFalse(game.state.is_open(task_id))
            self.assertIn(self.task, game.state.waiting_for_delivery())
            for task in game.state.open_tickets():      # hoechstens ein Zwischenfall
                self.assertTrue(task.get("zwischenfall"))
                game.defer(task["id"])
            self.assertTrue(game.state.can_end_day())
            game.end_day()
            self.assertEqual(game.state.day, payload["ankunft"])
            self.assertTrue(game.state.is_open(task_id))
            self.assertEqual(game.state.status_of(task_id), fg.ST_OPEN)
            self.assertIn("akkusatz_48v9", game.state.available_parts(self.task))
            answer = fg.find_solution(self.task, game.state.available_parts(self.task))
            result = game.solve(task_id, answer, used_help=False)
            self.assertTrue(result["richtig"])
            self.assertEqual(result["aus_lager"], ["akkusatz_48v9"])
            self.assertNotIn("akkusatz_48v9", game.state.stock())
            self.assertIn("Funktionstest", fg.result_text(self.task, result))

    def test_falsches_teil_nicht_bestellbar(self):
        with TempDB() as db:
            game = fg.Game(db)
            game.set_profile("Test", {})
            with self.assertRaises(ValueError):
                game.order_spare(self.task["id"], "akkusatz_48v9")   # nicht offen
            with self.assertRaises(ValueError):
                game.order_spare("ports-serverraum", "akkusatz_48v9")

    def test_grundbestand_im_lager(self):
        state = fg.GameState([])
        for part_id, count in fg.GAME["hardware"]["grundbestand"].items():
            self.assertEqual(state.stock()[part_id], count)


class DruckerTest(unittest.TestCase):
    def test_erste_freie_adresse(self):
        values = fg.printer_values({"netz": "192.168.20.0/24", "bereich": [200, 219],
                                    "belegt": [200, 201, 203], "treiber": ["a"],
                                    "treiber_richtig": "a"})
        self.assertEqual(values["ip"], "192.168.20.202")
        self.assertEqual(values["gateway"], "192.168.20.1")
        self.assertEqual(values["maske"], "255.255.255.0")

    def test_ohne_freie_adresse(self):
        with self.assertRaises(fg.FormError):
            fg.printer_values({"netz": "10.0.0.0/28", "bereich": [5, 6], "belegt": [5, 6],
                               "treiber": ["a"], "treiber_richtig": "a"})

    def test_formular_pruefen(self):
        task = _task("drucker-einrichten-verwaltung")
        answer = fg.find_solution(task)
        self.assertEqual(answer["ip"], "192.168.20.202")
        self.assertEqual(fg.form_problems(task, answer), [])
        answer = dict(answer, ip="192.168.20.200", treiber="Nur Text (generisch)")
        problems = fg.form_problems(task, answer)
        self.assertEqual(len(problems), 2)
        self.assertTrue(any("Schon belegt" in line for line in fg.form_given(task)))

    def test_drucker_geht_an_frank(self):
        order = _task("bestellung-drucker-verwaltung")
        events = _day_ends(15) + [_solved_event("b", order, fg.find_solution(order), 16)]
        state = fg.GameState(events)
        self.assertFalse(state._ready(_task("drucker-einrichten-verwaltung")))
        state = fg.GameState(events + [("x%d" % n, fg.EV_DAY_END, {"tag": 16 + n})
                                       for n in range(3)])
        self.assertTrue(state._ready(_task("drucker-einrichten-verwaltung")))
        self.assertNotIn("drucker_lx420", state.stock())
        self.assertTrue(any(item["teil"] == "drucker_lx420"
                            for item in state.warehouse()["ausgeliefert"]))


class ZwischenfallVariantenTest(unittest.TestCase):
    def setUp(self):
        self.content = _content()
        base = self.content["zwischenfaelle"][0]
        self.kind = base["id"]
        extra = []
        for number in range(2, 6):
            extra.append(dict(base, id="%s#%d" % (base["id"], number), gruppe=base["id"],
                              ticket=base["ticket"] + " (%d)" % number))
        base["gruppe"] = base["id"]
        self.content["zwischenfaelle"] += extra

    def test_abstand_zwischen_gleicher_art(self):
        events = [("2026-09-29 08:00:00", fg.EV_PROFILE, {"name": "A", "aussehen": {}})]
        gap = BALANCING["zwischenfaelle"]["abstand_gleiche_art"]
        seen = {}
        for day in range(1, 150):
            state = fg.GameState(events, self.content)
            incident = state.incident_today()
            if incident:
                kind = incident.get("gruppe", incident["id"])
                if kind in seen:
                    self.assertGreaterEqual(day - seen[kind], gap)
                seen[kind] = day
                events.append(("t%03d" % day, fg.EV_SOLVED,
                               {"aufgabe": incident["id"], "tag": day, "richtig": True,
                                "zwischenfall": True}))
            events.append(("u%03d" % day, fg.EV_DAY_END, {"tag": day}))
        state = fg.GameState(events, self.content)
        variants = [task for task in self.content["zwischenfaelle"]
                    if task.get("gruppe") == self.kind]
        self.assertGreater(len([t for t in variants if t["id"] in state.seen_incidents]), 1)

    def test_chance_gestaffelt(self):
        rules = {"chance": 0.4, "staffel": [{"ab_tag": 30, "chance": 0.5}]}
        self.assertEqual(fg.incident_chance(29, rules), 0.4)
        self.assertEqual(fg.incident_chance(30, rules), 0.5)


class RuhestandTest(unittest.TestCase):
    def setUp(self):
        self.content = _content()
        frank = next(p for p in self.content["kollegen"] if p["id"] == "frank")
        frank["bis_tag"] = 3
        frank["nachfolger"] = "paul"
        self.content["kollegen"].append(dict(frank, id="paul", name="Paul Adler", ab_tag=4,
                                             bis_tag=None, nachfolger=None))

    def test_nachfolge_uebernimmt(self):
        self.assertEqual(fg.active_person("frank", 3, self.content), "frank")
        self.assertEqual(fg.active_person("frank", 4, self.content), "paul")
        self.assertEqual(fg.active_person("ulla", 50, self.content), "ulla")

    def test_im_ruhestand_nicht_mehr_im_buero(self):
        events = [("a", fg.EV_PROFILE, {"name": "A", "aussehen": {}})]
        ids = lambda state: {p["id"] for p in fg.people_at_site(fg.SITE_OFFICE, state,
                                                                 self.content)}
        self.assertIn("frank", ids(fg.GameState(events + _day_ends(2), self.content)))
        later = ids(fg.GameState(events + _day_ends(5), self.content))
        self.assertNotIn("frank", later)
        self.assertIn("paul", later)

    def test_offene_auftraege_gehen_an_die_nachfolge(self):
        state = fg.GameState([("a", fg.EV_PROFILE, {"name": "A", "aussehen": {}})] +
                             _day_ends(20), self.content)
        frank_tasks = [task for task in state._pool()
                       if fg.task_by_id(task["id"], self.content)["auftraggeber"] == "frank"]
        self.assertTrue(frank_tasks)
        self.assertTrue(all(task["auftraggeber"] == "paul" for task in frank_tasks))



class FirmaTest(unittest.TestCase):
    """Eigenes Unternehmen (ab 0.33)."""

    def setUp(self):
        self.content = _content()
        self.task = self.content["aufgaben"][0]
        self.content["aufgaben"] = [self.task]
        self.content["zwischenfaelle"] = []

    def _rich(self, db, money=30000, done=True):
        """Spielfigur mit genug Geld und Ansehen, alle Auftraege erledigt."""
        game = fg.Game(db, "PC", self.content)
        game.set_profile("Nico", {})
        db.log_game_event(fg.EV_SOLVED, json.dumps(
            {"aufgabe": self.task["id"] if done else "anderes", "tag": 1, "richtig": True,
             "geld": money, "reputation": {key: 60 for key in fg.AXIS_KEYS}}), "PC")
        game.reload()
        return game

    def _founded(self, db, money=30000):
        game = self._rich(db, money)
        game.found_firm("Nico IT-Service")
        return game

    def test_inhalte(self):
        self.assertEqual(fg._validate_firm(fg.GAME), [])
        stages = fg.GAME["firma"]["gebaeude"]["stufen"]
        self.assertEqual([len(stage["plaetze"]) for stage in stages], [2, 5, 7, 9, 11])

    def test_gruendung_braucht_schwelle_und_alles_erledigt(self):
        with TempDB() as db:
            game = self._rich(db, money=20000, done=False)
            missing = game.state.founding_missing()
            self.assertEqual(len(missing), 2)
            self.assertFalse(game.state.founding_ready())
            with self.assertRaises(ValueError):
                game.found_firm("Test")
        with TempDB() as db:
            game = self._rich(db)
            self.assertTrue(game.state.founding_ready())
            # Alles erledigt: Feierabend geht weiter (bis zur Gruendung sparen)
            self.assertTrue(game.state.can_end_day())
            with self.assertRaises(ValueError):
                game.found_firm("   ")

    def test_gruendung(self):
        with TempDB() as db:
            game = self._founded(db)
            state = game.state
            cost = fg.GAME["firma"]["gruendung"]["kosten"]
            self.assertEqual(state.money, 30000 - cost)
            self.assertEqual(state.firm["name"], "Nico IT-Service")
            self.assertEqual(state.salary, 0)
            self.assertEqual(state.open_tickets(), [])
            self.assertTrue(state.can_end_day())
            self.assertEqual(fg.site_name(fg.SITE_OFFICE, state=state), "Nico IT-Service")
            site = fg.site_content(fg.SITE_OFFICE, state, self.content)
            self.assertIs(site["gebaeude"], state.firm_stage()["gebaeude"])
            with self.assertRaises(ValueError):
                game.found_firm("Noch eine")
            # Doppelte Gruendung (zwei Geraete) zaehlt nur einmal
            db.log_game_event(fg.EV_FOUNDED, json.dumps({"tag": 1, "name": "X",
                                                         "geld": -cost}), "Handy")
            self.assertEqual(game.reload().money, 30000 - cost)
            self.assertEqual(game.state.firm["name"], "Nico IT-Service")

    def test_bewerber_einstellen_und_platzgrenze(self):
        with TempDB() as db:
            game = self._founded(db)
            first = fg.applicants(game.state, self.content)
            self.assertEqual(len(first), fg.GAME["firma"]["bewerbung"]["anzahl"])
            self.assertEqual(first, fg.applicants(game.reload(), self.content))
            for item in first:
                self.assertEqual(item["gehalt"], fg.staff_salary(item["werte"]))
            game.hire(first[0]["id"])
            game.hire(first[1]["id"])
            self.assertEqual(len(game.state.staff), 2)
            with self.assertRaises(ValueError):
                game.hire(first[2]["id"])      # nur 2 Plaetze in Stufe 1
            ids = [item["id"] for item in fg.applicants(game.state, self.content)]
            self.assertNotIn(first[0]["id"], ids)
            people = fg.people_at_site(fg.SITE_OFFICE, game.state, self.content)
            self.assertEqual([p["id"] for p in people], [first[0]["id"], first[1]["id"]])
            game.fire(first[0]["id"])
            self.assertEqual(len(game.state.staff), 1)
            ids = [item["id"] for item in fg.applicants(game.state, self.content)]
            self.assertNotIn(first[0]["id"], ids)    # bewirbt sich nicht erneut

    def test_neue_bewerber_je_runde(self):
        with TempDB() as db:
            game = self._founded(db)
            first = {item["id"] for item in fg.applicants(game.state, self.content)}
            step = fg.GAME["firma"]["bewerbung"]["abstand_tage"]
            for _ in range(step):
                game.end_day()
            later = {item["id"] for item in fg.applicants(game.state, self.content)
                     if item["herkunft"] == "bewerbung"}
            self.assertFalse(first & later)

    def test_kollege_wechselt(self):
        with TempDB() as db:
            game = self._founded(db)
            tim = next(item for item in fg.GAME["firma"]["wechsel"] if item["kollege"] == "tim")
            for _ in range(tim["nach_tagen"]):
                game.end_day()
            state = game.state
            self.assertIn("Tim", fg.morning_text(state.day, self.content, state))
            found = [item for item in fg.applicants(state, self.content)
                     if item["id"] == "kollege:tim"]
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0]["name"], "Tim Becker")
            game.hire("kollege:tim")
            self.assertNotIn("Tim", fg.morning_text(game.state.day, self.content, game.state))

    def test_tagesabschluss_mit_firma(self):
        with TempDB() as db:
            game = self._founded(db)
            first = fg.applicants(game.state, self.content)
            game.hire(first[0]["id"])
            before = game.state.money
            numbers = game.state.firm_day()
            self.assertEqual(numbers["umsatz"], fg.staff_revenue(first[0]["werte"]))
            payload = game.end_day()
            self.assertEqual(payload["gehalt"], 0)
            self.assertEqual({key: payload["firma"][key] for key in numbers}, numbers)
            # Ab 0.42 wandert die Umsatzsteuer (Zahllast) in die Ruecklage
            self.assertEqual(payload["firma"]["ust"], 1)
            reserve = game.state.tax_reserve
            self.assertEqual(reserve, round((numbers["umsatz"] - numbers["nebenkosten"])
                                            * 19 / 119.0))
            self.assertEqual(game.state.money + reserve, before + numbers["umsatz"] -
                             numbers["gehaelter"] - numbers["nebenkosten"])
            self.assertIn("Umsatz Mitarbeiter", fg.day_end_money_text(payload))
            days = fg.finance_days(game.state)
            self.assertEqual(days[0]["ein"][fg.BOOK_REVENUE], numbers["umsatz"])
            self.assertEqual(days[0]["aus"][fg.BOOK_WAGES], numbers["gehaelter"])
            self.assertEqual(days[0]["gewinn"], days[0]["einnahmen"] - days[0]["ausgaben"])
            self.assertIn(fg.BOOK_FOUNDING, days[0]["aus"])
            labels, values = fg.balance_series(game.state)
            self.assertEqual(values[-1], game.state.money)

    def test_weiterbildung(self):
        """Ab 0.38: Weiterbildung je Thema (+10 im Thema)."""
        with TempDB() as db:
            game = self._founded(db)
            staff_id = fg.applicants(game.state, self.content)[0]["id"]
            game.hire(staff_id)
            topic = "kalkulation"
            value = game.state.staff_topic_value(staff_id, topic)
            rules = fg.GAME["firma"]["weiterbildung"]
            money = game.state.money
            payload = game.train(staff_id, topic)
            self.assertEqual((payload["thema"], payload["cat"]), (topic, "wirtschaft"))
            self.assertEqual(game.state.money, money - rules["preis"])
            self.assertEqual(game.state.firm_day()["umsatz"], 0)
            with self.assertRaises(ValueError):
                game.train(staff_id, "netzwerk")      # schon in Weiterbildung
            for _ in range(rules["tage"]):
                game.end_day()
            self.assertEqual(game.state.day, payload["bis_tag"])
            self.assertEqual(game.state.staff_topic_value(staff_id, topic),
                             min(rules["max"], value + rules["plus"]))
            self.assertGreater(game.state.firm_day()["umsatz"], 0)
            offer = fg.training_offer(game.state, staff_id, topic, self.content)
            self.assertEqual(offer["preis"], rules["preis"] + rules["aufschlag"])

    def test_weiterbildung_fachbereich(self):
        """Ab 0.38: Weiterbildung je Fachbereich (+plus auf alle Themen)."""
        with TempDB() as db:
            game = self._founded(db)
            staff_id = fg.applicants(game.state, self.content)[0]["id"]
            game.hire(staff_id)
            before = game.state.staff_topics(staff_id)
            rules = fg.GAME["firma"]["weiterbildung"]
            whole = rules["fachbereich"]
            money = game.state.money
            payload = game.train(staff_id, "netzwerk")
            self.assertEqual(payload["art"], "fachbereich")
            self.assertNotIn("thema", payload)
            self.assertEqual(game.state.money, money - whole["preis"])
            for _ in range(whole["tage"]):
                game.end_day()
            after = game.state.staff_topics(staff_id)
            for topic in fg.CAT_TOPICS["netzwerk"]:
                self.assertAlmostEqual(after[topic], min(90, before[topic] + whole["plus"]))
            for topic in fg.CAT_TOPICS["systeme"]:
                self.assertEqual(after[topic], before[topic])

    def test_ausbau(self):
        with TempDB() as db:
            game = self._founded(db, money=200000)
            for stage in fg.GAME["firma"]["gebaeude"]["stufen"][1:]:
                money = game.state.money
                game.expand()
                self.assertEqual(game.state.capacity, len(stage["plaetze"]))
                self.assertEqual(game.state.money, money - stage["preis"])
            with self.assertRaises(ValueError):
                game.expand()

    def test_gleicher_stand_nach_abgleich(self):
        with TempDB() as pc, TempDB() as handy:
            game = self._founded(pc)
            game.hire(fg.applicants(game.state, self.content)[0]["id"])
            game.end_day()
            fisi_sync.merge_into_local(handy, fisi_sync.export_local(pc))
            other = fg.Game(handy, "Handy", self.content)
            self.assertEqual(other.state.money, game.state.money)
            self.assertEqual(other.state.firm, game.state.firm)
            self.assertEqual(fg.applicants(other.state, self.content),
                             fg.applicants(game.state, self.content))


class AuftraegeTest(unittest.TestCase):
    """Angebote, Wettbewerb gegen Bitweiche und Kundentickets (ab 0.34)."""

    setUp = FirmaTest.setUp
    _rich = FirmaTest._rich
    _founded = FirmaTest._founded

    def _answer(self, inquiry, markup):
        task = fg.inquiry_task(inquiry, markup)
        return fg.find_solution(task)

    def test_inhalte(self):
        self.assertEqual(fg._validate_orders(fg.GAME["firma"]), [])
        broken = copy.deepcopy(fg.GAME["firma"])
        broken["tickets"]["vorlagen"][0]["kunde"] = "gibtsnicht"
        broken["kunden"][0]["art"] = "unbekannt"
        self.assertEqual(len(fg._validate_orders(broken)), 2)
        self.assertEqual(fg.FIRM_TABS[0], ("auftraege", "Aufträge"))

    def test_anfragen_fest_und_verschieden(self):
        with TempDB() as db:
            game = self._founded(db)
            first = game.state.inquiries()
            self.assertEqual(len(first), fg.GAME["firma"]["angebote"]["pro_tag"])
            self.assertEqual(first, game.reload().inquiries())
            self.assertNotEqual(first[0]["kunde"]["id"], first[1]["kunde"]["id"])
            for item in first:
                self.assertIn(item["artikel"], item["text"])
            game.end_day()
            self.assertNotEqual([item["id"] for item in game.state.inquiries()],
                                [item["id"] for item in first])

    def test_bitweiche_zuschlag_unberechenbar(self):
        """Meist aus der Spanne der Kundenart, manchmal Kampfpreis oder teuer:
        kein Zuschlag gewinnt oder verliert immer."""
        with TempDB() as db:
            state = self._founded(db).state
            rules = fg.GAME["firma"]["angebote"]
            seen = {}
            for day in range(state.day, state.day + 400):
                for item in fg.inquiries_for_day(state, day, self.content):
                    if item.get("konjunktur") or item.get("trend"):
                        continue    # ab 0.44: Markt verschiebt die Zuschlaege (eigener Test)
                    kind = rules["arten"][item["kunde"]["art"]]
                    for bid in item["bieter"]:
                        if bid["id"] != fg.BITWEICHE:
                            continue
                        seen.setdefault(bid["laune"], []).append(bid["zuschlag"])
                        if not bid["laune"]:
                            self.assertTrue(kind["von"] <= bid["zuschlag"] <= kind["bis"])
            self.assertEqual(set(seen), {"", "kampfpreis", "ausgelastet"})
            fight = rules["laune"]["kampfpreis"]
            self.assertTrue(all(fight["von"] <= value <= fight["bis"]
                                for value in seen["kampfpreis"]))
            markets = [value for values in seen.values() for value in values]
            lowest, highest = min(rules["zuschlaege"]), max(rules["zuschlaege"])
            self.assertTrue(any(value < lowest for value in markets))     # 5 % kann verlieren
            self.assertTrue(any(value >= highest for value in markets))   # 30 % kann gewinnen
            payload = {"netto": 100.0, "marktpreis": 90.0, "markt_zuschlag": 2,
                       "zuschlag": 10, "gewonnen": False, "grund": "preis",
                       "laune": "kampfpreis", "vorteil": 0}
            self.assertIn("Kampfpreis", fg.offer_result_text(payload)[1])

    def test_angebot_gewonnen_und_verloren(self):
        rules = self.content["firma"]["angebote"]
        rules["laune"] = {}
        for kind in rules["arten"].values():
            kind["von"] = kind["bis"] = 15
        # Nur Bitweiche bietet mit (wie in 0.34)
        rivals = self.content["firma"]["mitbewerber"]["firmen"]
        rivals[:] = [item for item in rivals if item["id"] == fg.BITWEICHE]
        with TempDB() as db:
            game = self._founded(db)
            low, high = game.state.inquiries()
            money = game.state.money
            # Bitweiche nimmt hier immer 15 %
            payload = game.send_offer(low["id"], 5, self._answer(low, 5))
            self.assertTrue(payload["gewonnen"])
            numbers = fg.offer_numbers(low, 5)
            self.assertEqual(payload["geld"], int(round(numbers["gewinn"])))
            self.assertEqual(game.state.money, money + payload["geld"])
            self.assertTrue(game.state.inquiries()[0]["ergebnis"]["gewonnen"])
            with self.assertRaises(ValueError):
                game.send_offer(low["id"], 5, self._answer(low, 5))
            # 30 % ist teurer als Bitweiche (15 % + hoechstens 3 % Vorteil)
            payload = game.send_offer(high["id"], 30, self._answer(high, 30))
            self.assertFalse(payload["gewonnen"])
            self.assertEqual(payload["grund"], "preis")
            self.assertEqual(payload["geld"], 0)
            head, _text = fg.offer_result_text(payload)
            self.assertIn("Bitweiche", head)
            days = fg.finance_days(game.state)
            self.assertIn(fg.BOOK_OFFERS, days[0]["ein"])

    def test_rechenfehler_verliert(self):
        with TempDB() as db:
            game = self._founded(db)
            inquiry = game.state.inquiries()[0]
            answer = self._answer(inquiry, 5)
            answer["brutto"] = "1"
            payload = game.send_offer(inquiry["id"], 5, answer)
            self.assertFalse(payload["gewonnen"])
            self.assertEqual(payload["grund"], "rechenfehler")
            self.assertTrue(payload["probleme"])
            with self.assertRaises(ValueError):
                game.send_offer(game.state.inquiries()[1]["id"], 7, {})   # kein Zuschlag

    def test_marktpreis_und_vorteil(self):
        with TempDB() as db:
            game = self._founded(db)
            inquiry = dict(game.state.inquiries()[0], markt=10)
            cost = fg.offer_numbers(inquiry, 0)["selbstkosten"]
            self.assertAlmostEqual(fg.market_price(inquiry), cost * 1.1, places=1)
            game.state.reputation["kundenzufriedenheit"] = 50
            self.assertFalse(fg.offer_result(game.state, dict(inquiry, markt=9), 10,
                                             self._answer(inquiry, 10))["gewonnen"])
            game.state.reputation["kundenzufriedenheit"] = 90
            self.assertTrue(fg.offer_result(game.state, dict(inquiry, markt=9), 10,
                                            self._answer(inquiry, 10))["gewonnen"])
            self.assertTrue(fg.offer_result(game.state, inquiry, 10,
                                            self._answer(inquiry, 10))["gewonnen"])

    def test_chance(self):
        rule = fg.GAME["firma"]["tickets"]["chance"]
        self.assertEqual(fg.ticket_chance(45, 45), rule["basis"])
        self.assertEqual(fg.ticket_chance(50, 45), 68)
        self.assertEqual(fg.ticket_chance(0, 65), rule["min"])
        self.assertEqual(fg.ticket_chance(100, 25), rule["max"])

    def test_tickets_verteilen(self):
        with TempDB() as db:
            game = self._founded(db)
            rules = fg.GAME["firma"]["tickets"]
            self.assertEqual(len(game.state.customer_tickets()), rules["mindestens"])
            staff_id = fg.applicants(game.state, self.content)[0]["id"]
            game.hire(staff_id)
            tickets = game.state.customer_tickets()
            self.assertEqual(len(tickets), max(rules["mindestens"],
                                               rules["grundzahl"] + rules["je_mitarbeiter"]))
            self.assertEqual(tickets, game.reload().customer_tickets())
            options = fg.ticket_candidates(game.state, tickets[0], game.knowledge())
            self.assertEqual([item["an"] for item in options], [fg.SELF, staff_id])
            payload = game.delegate(tickets[0]["id"], staff_id)
            self.assertEqual(payload["chance"], options[1]["chance"])
            with self.assertRaises(ValueError):
                game.delegate(tickets[0]["id"], fg.SELF)      # schon verteilt
            with self.assertRaises(ValueError):
                game.delegate(tickets[1]["id"], staff_id)     # nur 1 pro Mitarbeiter
            game.delegate(tickets[1]["id"], fg.SELF)
            self.assertEqual(game.state.firm_open_count(), 2 + 0)
            people = fg.firm_people(game.state, self.content)
            self.assertEqual(people[0]["kundenticket"]["id"], tickets[0]["id"])
            _head, text = fg.office_message(None, people[0], {}, self.content, game.state)
            self.assertIn(tickets[0]["titel"], text)
            money = game.state.money
            numbers = game.state.firm_day()
            outcomes = fg.ticket_outcomes(game.state, self.content)
            payload = game.end_day()
            self.assertEqual(payload["firma"]["tickets"], outcomes)
            self.assertEqual(len(outcomes), 2)
            gained = sum(item["geld"] for item in outcomes)
            self.assertEqual(game.state.money + game.state.tax_reserve,
                             money + gained + numbers["umsatz"] -
                             numbers["gehaelter"] - numbers["nebenkosten"])
            for item in outcomes:
                self.assertEqual(item["geld"] > 0, item["erfolg"])
            self.assertIn("Kundentickets", fg.day_end_money_text(payload))
            for day in range(1, 8):
                self.assertNotIn("Gehalt", fg.day_end_text(day, firm=True))

    def test_weiterbildung_sperrt_tickets(self):
        with TempDB() as db:
            game = self._founded(db)
            staff_id = fg.applicants(game.state, self.content)[0]["id"]
            game.hire(staff_id)
            game.train(staff_id, "netzwerk")
            ticket = game.state.customer_tickets()[0]
            with self.assertRaises(ValueError):
                game.delegate(ticket["id"], staff_id)

    def test_gleicher_stand_nach_abgleich(self):
        with TempDB() as pc, TempDB() as handy:
            game = self._founded(pc)
            inquiry = game.state.inquiries()[0]
            game.send_offer(inquiry["id"], 10, self._answer(inquiry, 10))
            ticket = game.state.customer_tickets()[0]
            game.delegate(ticket["id"], fg.SELF)
            fisi_sync.merge_into_local(handy, fisi_sync.export_local(pc))
            other = fg.Game(handy, "Handy", self.content)
            self.assertEqual(other.state.inquiries(), game.state.inquiries())
            self.assertEqual(other.state.customer_tickets(), game.state.customer_tickets())
            # Dasselbe Ticket auf dem Handy nochmal verteilt: zaehlt nur einmal
            handy.log_game_event(fg.EV_DELEGATED, json.dumps(
                {"ticket": ticket["id"], "tag": ticket and game.state.day, "an": "x",
                 "name": "X", "chance": 90}), "Handy")
            handy.log_game_event(fg.EV_OFFER_WON, json.dumps(
                {"anfrage": inquiry["id"], "tag": 1, "geld": 99999}), "Handy")
            other.reload()
            self.assertEqual(other.state.delegations[ticket["id"]]["an"], fg.SELF)
            self.assertEqual(other.state.money, game.state.money)
            game.end_day()
            fisi_sync.merge_into_local(handy, fisi_sync.export_local(pc))
            self.assertEqual(other.reload().ticket_results, game.state.ticket_results)


class MitarbeiterThemenTest(unittest.TestCase):
    """Mitarbeiter mit Werten je Thema und Lernen durch Arbeit (ab 0.38)."""

    setUp = FirmaTest.setUp
    _rich = FirmaTest._rich
    _founded = FirmaTest._founded

    def _hired(self, db):
        game = self._founded(db)
        applicant = fg.applicants(game.state, self.content)[0]
        game.hire(applicant["id"])
        return game, applicant["id"]

    def _day_end(self, game, firm):
        game.db.log_game_event(fg.EV_DAY_END, json.dumps(
            {"tag": game.state.day, "gehalt": 0, "firma": firm}), "PC")
        return game.reload()

    def test_werte_je_thema_und_staerken(self):
        with TempDB() as db:
            game = self._founded(db)
            for item in fg.applicants(game.state, self.content):
                self.assertEqual(set(item["themen"]), set(fg.TOPIC_ORDER))
                self.assertEqual(item["werte"], fg.cat_values(item["themen"]))
                self.assertEqual(item["gehalt"], fg.staff_salary(item["werte"]))
                best = max(item["themen"].values())
                self.assertEqual(item["themen"][item["staerken"][0]], best)
                self.assertIn("Stark in: ", fg.strengths_text(item))
            switch = self.content["firma"]["wechsel"][0]
            staff_id = fg.applicants(game.state, self.content)[0]["id"]
            game.hire(staff_id)
            item = game.state.staff_list()[0]
            self.assertEqual(item["themen"], {key: float(value) for key, value in
                                              game.state.staff[staff_id]["themen"].items()})
            self.assertEqual(len(item["staerken"]), 2)
            self.assertEqual(len(switch["staerken"]), 2)

    def test_alter_spielstand_ohne_themen(self):
        """Mitarbeiter aus 0.37: Themen gestreut um den alten Fachbereichswert."""
        with TempDB() as db:
            game = self._founded(db)
            old = {"netzwerk": 40, "sicherheit": 20, "systeme": 60, "wirtschaft": 10,
                   "datenbanken": 30}
            db.log_game_event(fg.EV_HIRED, json.dumps(
                {"id": "alt1", "name": "Alte Hasen", "aussehen": {}, "werte": old,
                 "gehalt": 200, "herkunft": "bewerbung", "tag": game.state.day}), "PC")
            db.log_game_event(fg.EV_TRAINING, json.dumps(
                {"id": "alt1", "cat": "wirtschaft", "plus": 10, "geld": -600,
                 "tag": game.state.day, "bis_tag": game.state.day}), "PC")
            state = game.reload()
            topics = state.staff_topics("alt1")
            spread = self.content["firma"]["lernen"]["alt_streuung"]
            for key, value in old.items():
                plus = 10 if key == "wirtschaft" else 0
                for topic in fg.CAT_TOPICS[key]:
                    self.assertLessEqual(abs(topics[topic] - value - plus), spread + 1)
                self.assertLessEqual(abs(state.staff_values("alt1")[key] - value - plus), 1)
            self.assertEqual(topics, fg.GameState(state.history, self.content)
                             .staff_topics("alt1"))

    def test_lernen_durch_kundentickets(self):
        with TempDB() as db:
            game, staff_id = self._hired(db)
            template = self.content["firma"]["tickets"]["vorlagen"][0]
            topic = template["thema"]
            before = game.state.staff_topics(staff_id)[topic]
            state = self._day_end(game, {"tickets": [
                {"ticket": "kt1:a", "vorlage": template["id"], "an": staff_id,
                 "name": "X", "erfolg": True, "geld": 60},
                {"ticket": "kt1:b", "vorlage": template["id"], "an": staff_id,
                 "name": "X", "erfolg": False, "geld": 0}]})
            rule = self.content["firma"]["lernen"]
            amount = rule["ticket_erfolg"] / (2.0 if before >= rule["halb_ab"] else 1.0)
            self.assertAlmostEqual(state.staff_topics(staff_id)[topic],
                                   _work_learned(before, amount, self.content))
            self.assertEqual(len([item for item in state.learn_log
                                  if item[5] == "ticket"]), 1)   # Fehlschlag: nichts

    def test_lernen_ab_schwelle_halb(self):
        with TempDB() as db:
            self.content["firma"]["lernen"]["halb_ab"] = 0
            game, staff_id = self._hired(db)
            template = self.content["firma"]["tickets"]["vorlagen"][0]
            topic = template["thema"]
            before = game.state.staff_topics(staff_id)[topic]
            state = self._day_end(game, {"tickets": [
                {"ticket": "kt1:a", "vorlage": template["id"], "an": staff_id,
                 "name": "X", "erfolg": True, "geld": 60}]})
            self.assertAlmostEqual(state.staff_topics(staff_id)[topic], _work_learned(
                before, self.content["firma"]["lernen"]["ticket_erfolg"] / 2.0, self.content))

    def test_lernen_durch_routine(self):
        with TempDB() as db:
            game, staff_id = self._hired(db)
            rule = self.content["firma"]["lernen"]
            topics = game.state.staff_topics(staff_id)
            best = fg.strongest_topics(topics, 1)[0]
            payload = None
            for _ in range(rule["routine_tage"]):
                payload = game.end_day()
            after = game.state.staff_topics(staff_id)
            amount = rule["routine_plus"] / (2.0 if topics[best] >= rule["halb_ab"] else 1.0)
            self.assertAlmostEqual(after[best], _work_learned(topics[best], amount, self.content))
            if int(after[best]) > int(topics[best]):
                self.assertEqual(payload["firma"]["gelernt"][0]["thema"], best)
                self.assertIn("Dazugelernt", fg.firm_day_text(payload["firma"]))

    def test_ticket_chance_rechnet_mit_thema(self):
        with TempDB() as db:
            game, staff_id = self._hired(db)
            ticket = game.state.customer_tickets()[0]
            topic = ticket["thema"]
            self.assertIn(topic, fg.CAT_TOPICS[ticket["cat"]])
            levels = {ticket["cat"]: 10, topic: 80}
            options = fg.ticket_candidates(game.state, ticket, levels, self.content)
            self.assertEqual(options[0]["wert"], 80)
            self.assertEqual(options[1]["wert"],
                             game.state.staff_topic_value(staff_id, topic))
            self.assertIn(fg.TOPIC_SHORT[topic], fg.ticket_line(ticket))

    def test_lernen_durch_projekt(self):
        with TempDB() as db:
            helper = ProjekteTest()
            helper.content, helper.task = self.content, self.task
            game, project = ProjekteTest._won(helper, db)
            staff_id = next(iter(game.state.staff))
            topic = fg.project_topic(project, self.content)
            self.assertIn(topic, fg.CAT_TOPICS[project["cat"]])
            before = game.state.staff_topics(staff_id)[topic]
            state = self._day_end(game, {"projekte": [
                {"projekt": project["projekt"], "tag": game.state.day, "punkte": 999,
                 "fertig": True, "verzug": 0, "geld": 0,
                 "beitraege": [{"an": staff_id, "name": "X", "punkte": 3}]}]})
            rule = self.content["firma"]["lernen"]
            amount = (rule["projekt_fertig"] + rule["projekt_puenktlich"]) / (
                2.0 if before >= rule["halb_ab"] else 1.0)
            self.assertAlmostEqual(state.staff_topics(staff_id)[topic],
                                   _work_learned(before, amount, self.content))

    def _one_ticket(self, game, staff_id, template, number, success=True):
        return self._day_end(game, {"tickets": [
            {"ticket": "kt%d:a" % number, "vorlage": template["id"], "an": staff_id,
             "name": "X", "erfolg": success, "geld": 60}]})

    def test_lernen_durch_arbeit_endet_an_grenze(self):
        """Ab 0.40: Arbeit bringt nur bis lernen.deckel, Weiterbildung darueber."""
        with TempDB() as db:
            rule = self.content["firma"]["lernen"]
            rule["ticket_erfolg"], rule["halb_ab"], rule["deckel"] = 30, 90, 70
            game, staff_id = self._hired(db)
            template = self.content["firma"]["tickets"]["vorlagen"][0]
            topic = template["thema"]
            for number in range(1, 5):
                state = self._one_ticket(game, staff_id, template, number)
            self.assertAlmostEqual(state.staff_topics(staff_id)[topic], 70)
            self.assertIn(topic, fg.topics_at_cap(state.staff_topics(staff_id), self.content))
            self.assertIn("Grenze erreicht", fg.cap_text(state.staff_topics(staff_id),
                                                        self.content))
            # Weiterbildung geht ueber die Grenze hinaus
            game.train(staff_id, topic)
            for _ in range(10):
                game.end_day()
            self.assertGreater(game.state.staff_topics(staff_id)[topic], 70)
            # ... und Arbeit bringt dort nichts mehr
            before = game.state.staff_topics(staff_id)[topic]
            state = self._one_ticket(game, staff_id, template, 9)
            self.assertAlmostEqual(state.staff_topics(staff_id)[topic], before)

    def test_grenze_erreicht_in_feierabend_meldung(self):
        with TempDB() as db:
            rule = self.content["firma"]["lernen"]
            rule["ticket_erfolg"], rule["halb_ab"] = 90, 90
            game, staff_id = self._hired(db)
            template = self.content["firma"]["tickets"]["vorlagen"][0]
            before = game.state.staff_topics(staff_id)[template["thema"]]
            payload = {"tickets": [{"ticket": "kt1:a", "vorlage": template["id"],
                                    "an": staff_id, "name": "X", "erfolg": True,
                                    "geld": 60}]}
            learned = fg.learned_today(game.state, {"firma": payload}, self.content)
            if before < fg.learn_cap(self.content):
                self.assertTrue(learned[0]["grenze"])
                text = fg.firm_day_text({"gelernt": learned})
                self.assertIn("Grenze erreicht", text)
                self.assertNotIn("Dazugelernt", text)

    def test_lernen_langsamer_als_weiterbildung(self):
        """Ein geschafftes Ticket bringt hoechstens ein Fuenftel einer Weiterbildung."""
        rules = self.content["firma"]
        self.assertLessEqual(rules["lernen"]["ticket_erfolg"] * 5,
                             rules["weiterbildung"]["plus"])
        self.assertLess(rules["lernen"]["deckel"], rules["weiterbildung"]["max"])


def _work_learned(before, amount, content):
    """Erwarteter Wert nach Lernen durch Arbeit: nie ueber die Grenze (ab 0.40)."""
    cap = fg.learn_cap(content)
    return before if before >= cap else min(cap, before + amount)


class ProjekteTest(unittest.TestCase):
    """Kundenprojekte und Mitbewerber (ab 0.35)."""

    setUp = FirmaTest.setUp
    _rich = FirmaTest._rich
    _founded = FirmaTest._founded

    def _only_bitweiche(self, markup=15):
        """Nur Bitweiche bietet, immer mit demselben Zuschlag."""
        rules = self.content["firma"]["angebote"]
        rules["laune"] = {}
        for kind in rules["arten"].values():
            kind["von"] = kind["bis"] = markup
        rivals = self.content["firma"]["mitbewerber"]
        rivals["firmen"] = [item for item in rivals["firmen"] if item["id"] == fg.BITWEICHE]
        rivals["projekt_bieter"] = {"von": 1, "bis": 1}

    def _answer(self, project, markup):
        return fg.find_solution(fg.project_task(project, markup))

    def _won(self, db):
        """Firma mit zwei Mitarbeitern und einem gewonnenen Projekt."""
        self._only_bitweiche()
        game = self._founded(db, money=60000)
        for applicant in fg.applicants(game.state, self.content)[:2]:
            game.hire(applicant["id"])
        project = game.state.tenders()[0]
        game.send_project_offer(project["id"], 5, self._answer(project, 5))
        return game, game.state.projects[project["id"]]

    def test_inhalte(self):
        self.assertEqual(fg._validate_projects(fg.GAME["firma"], fg.GAME), [])
        self.assertEqual(fg.FIRM_TABS[1], ("projekte", "Projekte"))
        self.assertEqual(len(fg.GAME["projektarbeiten"]), 50)
        names = {item["kurz"] for item in fg.competitors()}
        self.assertEqual(len(names), 6)
        broken = copy.deepcopy(fg.GAME["firma"])
        broken["mitbewerber"]["firmen"][1]["fach"] = {"gibtsnicht": -5}
        self.assertEqual(len(fg._validate_projects(broken, fg.GAME)), 1)
        broken = copy.deepcopy(fg.GAME["firma"])
        del broken["projekte"]["stufen"]["Leicht"]
        self.assertEqual(len(fg._validate_projects(broken, fg.GAME)),
                         sum(1 for item in fg.GAME["projektarbeiten"]
                             if item["schwierigkeit"] == "Leicht"))

    def test_kundenname(self):
        self.assertEqual(fg.customer_short("Einzelhandelskette (ModeWelt GmbH), 13. Filiale"),
                         "ModeWelt GmbH")
        self.assertEqual(fg.customer_short("Steuerberatungskanzlei, 25 Mitarbeiter"),
                         "Steuerberatungskanzlei")

    def test_ausschreibungen_fest(self):
        with TempDB() as db:
            game = self._founded(db)
            first = game.state.tenders()
            self.assertEqual(len(first), 1)
            self.assertEqual(first, game.reload().tenders())
            rules = self.content["firma"]["projekte"]
            seen = set()
            for _day in range(rules["abstand_tage"] * 4):
                tenders = game.state.tenders()
                self.assertTrue(1 <= len(tenders) <= rules["max_offen"])
                seen.update(item["id"] for item in tenders)
                for item in tenders:
                    self.assertTrue(item["von_tag"] <= game.state.day <= item["bis_tag"])
                    self.assertTrue(2 <= len(item["bieter"]) + len(item["ausgefallen"]) <= 3
                                    or len(item["bieter"]) == 1)
                game.end_day()
            self.assertGreaterEqual(len(seen), 4)
            # Alle 50 Testprojekte kommen dran, bevor sich eins wiederholt
            state = game.state
            templates = [fg.project_for_slot(state, slot, self.content)["vorlage"]
                         for slot in range(50)]
            self.assertEqual(sorted(templates), list(range(50)))
            self.assertEqual(fg.project_for_slot(state, 50, self.content)["folge"], 1)

    def test_projekt_gewinnen(self):
        with TempDB() as db:
            self._only_bitweiche()
            game = self._founded(db, money=60000)
            money = game.state.money
            project = game.state.tenders()[0]
            payload = game.send_project_offer(project["id"], 5, self._answer(project, 5))
            self.assertTrue(payload["gewonnen"])
            self.assertEqual(payload["anzahlung"], int(round(payload["netto"] * 0.3)))
            self.assertEqual(game.state.money,
                             money + payload["anzahlung"] - project["material"])
            running = game.state.running_projects()
            self.assertEqual([item["projekt"] for item in running], [project["id"]])
            self.assertEqual(game.state.tenders()[0]["ergebnis"]["gewonnen"], True)
            head, text = fg.offer_result_text(payload)
            self.assertEqual(head, "Projekt gewonnen")
            self.assertIn("Anzahlung", text)
            with self.assertRaises(ValueError):
                game.send_project_offer(project["id"], 5, self._answer(project, 5))
            days = fg.finance_days(game.state)
            self.assertIn(fg.BOOK_PROJECTS, days[0]["ein"])
            self.assertIn(fg.BOOK_MATERIAL, days[0]["aus"])
            # Im Startbuero laeuft nur ein Projekt gleichzeitig
            for _day in range(3):
                game.end_day()
            other = [item for item in game.state.tenders() if not item.get("ergebnis")][0]
            self.assertTrue(fg.project_offer_problem(game.state, self.content))
            with self.assertRaises(ValueError):
                game.send_project_offer(other["id"], 5, self._answer(other, 5))

    def test_projekt_verlieren(self):
        with TempDB() as db:
            self._only_bitweiche()
            game = self._founded(db)
            project = game.state.tenders()[0]
            payload = game.send_project_offer(project["id"], 30, self._answer(project, 30))
            self.assertFalse(payload["gewonnen"])
            self.assertEqual(payload["konkurrent"], fg.BITWEICHE)
            self.assertEqual(game.state.running_projects(), [])
            head, _text = fg.offer_result_text(payload)
            self.assertIn("Bitweiche", head)
            self.assertEqual(fg.lost_to(game.state), [("Bitweiche IT-Service GmbH", 1)])

    def test_mitbewerber(self):
        with TempDB() as db:
            state = self._founded(db).state
            winners, counts = set(), set()
            for day in range(state.day, state.day + 200):
                for item in fg.inquiries_for_day(state, day, self.content):
                    counts.add(len(item["bieter"]) + len(item["ausgefallen"]))
                    winners.add(item["konkurrent"])
                    self.assertEqual(item["markt"], min(bid["zuschlag"]
                                                        for bid in item["bieter"]))
            self.assertEqual(counts, {1, 2})
            self.assertEqual(winners, {item["id"] for item in fg.competitors()})
            # Byteschmiede ist manchmal ausgelastet und bietet dann nicht
            rival = fg.competitor("byteschmiede")
            skipped = sum(1 for day in range(300) if fg._rival_markup(
                rival, fg.offer_rules(), "normal", None, "x", day, "s") is None)
            self.assertTrue(0 < skipped < 200)
            # Fachbereich macht Spezialisten guenstiger
            kranich = fg.competitor("kranich")
            net = [fg._rival_markup(kranich, fg.offer_rules(), "normal", "netzwerk", "x",
                                    day, "s")[0] for day in range(200)]
            other = [fg._rival_markup(kranich, fg.offer_rules(), "normal", "wirtschaft", "x",
                                      day, "s")[0] for day in range(200)]
            self.assertLess(sum(net), sum(other))
            payload = {"netto": 100.0, "marktpreis": 90.0, "markt_zuschlag": 2, "zuschlag": 10,
                       "gewonnen": False, "grund": "preis", "laune": "", "vorteil": 0,
                       "konkurrent": "cloudkontor",
                       "bieter": [{"id": "cloudkontor", "zuschlag": 2, "netto": 90.0},
                                  {"id": "bitweiche", "zuschlag": 20, "netto": 105.0}]}
            head, text = fg.offer_result_text(payload)
            self.assertIn("CloudKontor Nord", head)
            self.assertIn("Mitgeboten haben", text)

    def test_team_und_fortschritt(self):
        with TempDB() as db:
            game, project = self._won(db)
            self.content["firma"]["projekte"]["rueckschlag"]["chance"] = 0
            staff = [item["id"] for item in game.state.staff_list()]
            revenue = game.state.firm_day()["umsatz"]
            game.set_project_team(project["projekt"], [staff[0], fg.SELF])
            state = game.state
            self.assertEqual(state.project_of(staff[0]), project["projekt"])
            self.assertEqual(state.staff_list()[0]["umsatz"], 0)
            self.assertLess(state.firm_day()["umsatz"], revenue)
            self.assertEqual(fg.own_ticket_limit(state), 1)
            ticket = state.customer_tickets()[0]
            options = {item["an"]: item for item in
                       fg.ticket_candidates(state, ticket, game.knowledge())}
            self.assertIn("Projekt", options[staff[0]]["problem"])
            self.assertEqual(options[fg.SELF]["problem"], "")
            expected = fg.project_team_points(state, state.projects[project["projekt"]],
                                              game.knowledge())
            payload = game.end_day()
            item = payload["firma"]["projekte"][0]
            self.assertEqual(item["punkte"], expected)
            running = game.state.projects[project["projekt"]]
            self.assertAlmostEqual(running["stand"], expected)
            self.assertIn("Projekte:", fg.firm_day_text(payload["firma"]))
            phases = fg.project_phases(running)
            self.assertEqual(len(phases), 5)
            self.assertIn("Jetzt: ", fg.project_phase_text(running))
            self.assertIn("Tag 2 von", fg.project_status_text(game.state, running,
                                                               game.knowledge()))
            # Team wieder aufloesen: Routineumsatz ist zurueck
            game.toggle_project_member(project["projekt"], staff[0])
            self.assertEqual(game.state.firm_day()["umsatz"], revenue)
            self.assertEqual(game.state.project_of(staff[0]), None)

    def test_fertig_puenktlich_und_zu_spaet(self):
        for extra_days, late in ((0, False), (8, True)):
            with TempDB() as db:
                game, project = self._won(db)
                self.content["firma"]["projekte"]["rueckschlag"]["chance"] = 0
                pid = project["projekt"]
                for _day in range(extra_days):
                    game.end_day()
                staff = [item["id"] for item in game.state.staff_list()]
                game.set_project_team(pid, staff + [fg.SELF])
                reputation = game.state.reputation["kundenzufriedenheit"]
                for _day in range(40):
                    if game.state.projects[pid]["fertig"]:
                        break
                    money = game.state.money
                    payload = game.end_day()
                done = game.state.projects[pid]
                self.assertTrue(done["fertig"])
                item = payload["firma"]["projekte"][0]
                self.assertTrue(item["fertig"])
                self.assertEqual(bool(item["verzug"]), late)
                rest = done["netto"] - done["anzahlung"]
                if late:
                    self.assertLess(item["geld"], rest)
                    self.assertLess(game.state.reputation["kundenzufriedenheit"], reputation)
                else:
                    self.assertEqual(item["geld"], int(round(rest)))
                    self.assertGreater(game.state.reputation["kundenzufriedenheit"],
                                       reputation)
                self.assertEqual(done["team"], [])
                self.assertEqual(game.state.running_projects(), [])
                self.assertGreater(game.state.money, money - 2000)

    def test_lernbonus_und_rueckschlag(self):
        with TempDB() as db:
            game, project = self._won(db)
            state = game.state
            running = state.projects[project["projekt"]]
            staff = [item["id"] for item in state.staff_list()]
            game.set_project_team(project["projekt"], staff[:1])
            state = game.state
            running = state.projects[project["projekt"]]
            plain = fg.project_outcomes(state, game.knowledge(), set(), self.content)[0]
            bonus = fg.project_outcomes(state, game.knowledge(), {running["vorlage"]},
                                        self.content)[0]
            self.assertTrue(bonus["lernbonus"])
            if not plain["rueckschlag"]:
                self.assertAlmostEqual(bonus["punkte"], round(plain["punkte"] * 1.2, 1))
            rules = self.content["firma"]["projekte"]
            rules["rueckschlag"]["chance"] = 1.0
            running["anforderung"] = 100
            item = fg.project_outcomes(state, game.knowledge(), set(), self.content)[0]
            self.assertTrue(item["rueckschlag"])
            self.assertIn(item["rueckschlag"], rules["rueckschlaege"][running["cat"]])
            self.assertIn("Rückschlag", fg.project_day_text(item))

    def test_buero_und_uebersicht(self):
        with TempDB() as db:
            game, project = self._won(db)
            self.assertIn("ohne Team", fg.projects_summary(game.state))
            staff = [item["id"] for item in game.state.staff_list()]
            game.set_project_team(project["projekt"], staff[:1])
            people = {item["id"]: item for item in fg.firm_people(game.state, self.content)}
            text = people[staff[0]]["projekt_text"]
            self.assertTrue(text)
            _head, message = fg.office_message((0, 0), people[staff[0]], {}, self.content)
            self.assertIn("Projekt", message)
            # Wer in einem Projekt ist, wechselt beim neuen Team dorthin
            with self.assertRaises(ValueError):
                game.set_project_team(project["projekt"], ["gibtsnicht"])

    def test_gleicher_stand_nach_abgleich(self):
        with TempDB() as pc, TempDB() as handy:
            game, project = self._won(pc)
            staff = [item["id"] for item in game.state.staff_list()]
            game.set_project_team(project["projekt"], staff)
            game.end_day()
            fisi_sync.merge_into_local(handy, fisi_sync.export_local(pc))
            other = fg.Game(handy, "Handy", self.content)
            self.assertEqual(other.state.projects, game.state.projects)
            self.assertEqual(other.state.money, game.state.money)
            # Dasselbe Projekt auf dem Handy nochmal gewonnen: zaehlt nur einmal
            handy.log_game_event(fg.EV_PROJECT_WON, json.dumps(
                {"projekt": project["projekt"], "tag": 1, "anzahlung": 99999}), "Handy")
            other.reload()
            self.assertEqual(other.state.money, game.state.money)



class GebaeudeAusbauTest(unittest.TestCase):
    """Ausbaustufen 3 bis 5 und Sonderraeume (ab 0.36)."""

    setUp = FirmaTest.setUp
    _rich = FirmaTest._rich
    _founded = FirmaTest._founded
    _only_bitweiche = ProjekteTest._only_bitweiche
    _answer = ProjekteTest._answer

    def _stage(self, db, number, money=300000):
        game = self._founded(db, money=money)
        while game.state.firm["stufe"] < number:
            game.expand()
        return game

    def test_inhalte(self):
        self.assertEqual(fg._validate_rooms(fg.GAME["firma"]), [])
        rooms = fg.special_rooms()
        self.assertEqual([item["id"] for item in rooms],
                         ["lager", "besprechung", "serverraum", "schulung"])
        self.assertEqual([item["ab_stufe"] for item in rooms], [3, 3, 4, 5])
        broken = copy.deepcopy(fg.GAME["firma"])
        broken["sonderraeume"]["raeume"][0]["effekt"] = {"gibtsnicht": 1}
        broken["sonderraeume"]["raeume"][1]["raum"] = "buero3"
        self.assertEqual(len(fg._validate_rooms(broken)), 1 + 3)

    def test_raum_erst_ab_stufe(self):
        with TempDB() as db:
            game = self._stage(db, 2)
            status = {item["id"]: item for item in fg.room_status(game.state, self.content)}
            self.assertIn("Ausbaustufe 3", status["lager"]["problem"])
            with self.assertRaises(ValueError):
                game.build_room("lager")
            # Ein Ereignis ohne die Stufe (z.B. von einem alten Geraet) zaehlt nicht
            game._log(fg.EV_ROOM, {"raum": "lager", "geld": -8000, "tag": game.state.day})
            self.assertFalse(game.state.has_room("lager"))
            game.expand()
            money = game.state.money
            game.build_room("lager")
            self.assertTrue(game.state.has_room("lager"))
            self.assertEqual(game.state.money, money - fg.special_room("lager")["preis"])
            with self.assertRaises(ValueError):
                game.build_room("lager")
            with self.assertRaises(ValueError):
                game.build_room("serverraum")
            with self.assertRaises(ValueError):
                game.build_room("gibtsnicht")

    def test_doppelt_zaehlt_einmal(self):
        with TempDB() as pc, TempDB() as handy:
            game = self._stage(pc, 3)
            fisi_sync.merge_into_local(handy, fisi_sync.export_local(pc))
            other = fg.Game(handy, "Handy", self.content)
            game.build_room("besprechung")
            other.build_room("besprechung")
            fisi_sync.merge_into_local(handy, fisi_sync.export_local(pc))
            other.reload()
            self.assertEqual(list(other.state.rooms), ["besprechung"])
            self.assertEqual(other.state.money, game.state.money)

    def test_leerstand_im_grundriss(self):
        with TempDB() as db:
            game = self._stage(db, 3)
            rooms = {item["id"]: item for item in
                     fg.firm_building(game.state, self.content)["raeume"]}
            self.assertEqual(rooms["firmenlager"]["name"], "Leerstand")
            self.assertEqual(rooms["firmenlager"]["deko"], [])
            self.assertIn("Lager", rooms["firmenlager"]["text"])
            self.assertTrue(rooms["buero3"]["deko"])
            game.build_room("lager")
            rooms = {item["id"]: item for item in
                     fg.firm_building(game.state, self.content)["raeume"]}
            self.assertEqual(rooms["firmenlager"]["name"], "Lager")
            self.assertTrue(rooms["firmenlager"]["deko"])
            self.assertEqual(rooms["besprechung"]["name"], "Leerstand")
            site = fg.site_content(fg.SITE_OFFICE, game.state, self.content)
            self.assertEqual(len(site["gebaeude"]["raeume"]), len(rooms))

    def test_schilder_versetzt(self):
        """Kleine Ansicht: untere Reihe von links abwechselnd oben, unten, oben ..."""
        building = self.content["firma"]["gebaeude"]["stufen"][4]["gebaeude"]
        self.assertEqual(fg._staggered_labels(building), {"besprechung", "buero4"})
        names = {item["id"]: item["name"] for item in building["raeume"]}
        self.assertEqual([names[key] for key in ("buero2", "buero3", "buero4", "buero5")],
                         ["Büro 2", "Büro 3", "Büro 4", "Büro 5"])
        content = dict(self.content, gebaeude=building, kollegen=[])
        def label_y(stagger):
            return {shape["text"]: shape["y"] for shape in
                    fg.building_shapes(content=content, stagger=stagger)
                    if shape["k"] == "text" and shape["role"] == "raum"}
        flat, staggered = label_y(False), label_y(True)
        self.assertEqual(flat["Lager"], flat["Besprechungsraum"])
        self.assertGreater(staggered["Besprechungsraum"], staggered["Lager"])
        self.assertGreater(staggered["Büro 4"], staggered["Büro 5"])
        self.assertEqual(staggered["Büro 2"], flat["Büro 2"])
        # Ein Name direkt ueber einem Schild unten faellt in der kleinen Ansicht weg
        content["kollegen"] = [{"id": "leon", "name": "Leon", "platz": [24.5, 12.85]},
                               {"id": "jan", "name": "Jan", "platz": [24.5, 9.95]}]
        def people(stagger):
            return [shape["text"] for shape in
                    fg.building_shapes(content=content, stagger=stagger)
                    if shape["k"] == "text" and shape["role"] == "person"]
        self.assertEqual(len(people(False)), 2)
        self.assertEqual(len(people(True)), 1)

    def test_nebenkosten(self):
        with TempDB() as db:
            game = self._stage(db, 3)
            self.assertEqual(game.state.firm_day()["nebenkosten"], 130)
            game.build_room("lager")
            game.build_room("besprechung")
            self.assertEqual(game.state.firm_day()["nebenkosten"], 170)
            money = game.state.money
            game.end_day()
            self.assertEqual(game.state.money, money - 170)

    def test_lager_macht_guenstiger(self):
        with TempDB() as db:
            self._only_bitweiche(markup=10)
            game = self._stage(db, 3)
            before = game.state.inquiries()[0]
            game.build_room("lager")
            after = game.state.inquiries()[0]
            self.assertEqual(after["listenpreis"], before["einkaufspreis"])
            self.assertEqual(after["einkaufspreis"], fg.discounted(before["einkaufspreis"], 15))
            self.assertNotIn("Lager-Rabatt", fg.inquiry_status_text(before))
            self.assertIn("Lager-Rabatt", fg.inquiry_status_text(after))
            # Mit 15 % Zuschlag waere man ohne Lager teurer als Bitweiche (10 %),
            # mit Lager ist man guenstiger
            answer = fg.find_solution(fg.inquiry_task(after, 15))
            payload = game.send_offer(after["id"], 15, answer)
            self.assertTrue(payload["gewonnen"])
            self.assertLess(payload["netto"], payload["marktpreis"])
            tender = game.state.tenders()[0]
            self.assertEqual(tender["material"], fg.discounted(tender["material_markt"], 15))

    def test_besprechungsraum(self):
        with TempDB() as db:
            self._only_bitweiche(markup=30)
            game = self._stage(db, 3)
            self.assertEqual(len(game.state.inquiries()), 2)
            first = game.state.inquiries()
            game.build_room("besprechung")
            now = game.state.inquiries()
            self.assertEqual(len(now), 3)
            self.assertEqual(now[:2], first)
            before = game.state.reputation["kundenzufriedenheit"]
            payload = game.send_offer(now[0]["id"], 5, fg.find_solution(
                fg.inquiry_task(now[0], 5)))
            self.assertTrue(payload["gewonnen"])
            self.assertEqual(payload["reputation"]["kundenzufriedenheit"],
                             self.content["firma"]["angebote"]["kundenzufriedenheit_gewonnen"]
                             + 1)
            self.assertGreater(game.state.reputation["kundenzufriedenheit"], before)

    def test_serverraum(self):
        with TempDB() as db:
            game = self._stage(db, 4)
            self.assertEqual(fg.project_limit(game.state, self.content), 3)
            game.build_room("serverraum")
            self.assertEqual(fg.project_limit(game.state, self.content), 4)
            self.assertEqual(game.state.room_effect("rueckschlag_faktor", 1.0), 0.5)
            self.assertEqual(game.state.room_effect("anfragen_plus"), 0)

    def test_schulungsraum(self):
        with TempDB() as db:
            game = self._stage(db, 5)
            staff_id = fg.applicants(game.state, self.content)[0]["id"]
            game.hire(staff_id)
            rules = self.content["firma"]["weiterbildung"]
            offer = fg.training_offer(game.state, staff_id, "ipv4", self.content)
            self.assertEqual((offer["preis"], offer["tage"]), (rules["preis"], rules["tage"]))
            game.build_room("schulung")
            offer = fg.training_offer(game.state, staff_id, "ipv4", self.content)
            self.assertEqual(offer["preis"], fg.discounted(rules["preis"], 30))
            self.assertEqual(offer["tage"], rules["tage"] - 1)

    def test_alter_stand_bleibt(self):
        """Ein Spielstand aus 0.35 (Stufe 2, keine Sonderraeume) rechnet gleich."""
        with TempDB() as db:
            game = self._stage(db, 2)
            self.assertEqual(game.state.firm_day()["nebenkosten"], 90)
            self.assertEqual(fg.project_limit(game.state, self.content), 2)
            self.assertEqual(len(game.state.inquiries()), 2)
            building = fg.firm_building(game.state, self.content)
            self.assertIs(building, game.state.firm_stage()["gebaeude"])


class KrediteTest(unittest.TestCase):
    """Kredite fuer die eigene Firma (ab 0.41)."""

    setUp = FirmaTest.setUp
    _rich = FirmaTest._rich
    _founded = FirmaTest._founded

    def _days(self, game, count, revenue=2000, costs=0):
        """Feierabende mit festem Umsatz (ohne Mitarbeiter)."""
        payloads = []
        for _ in range(count):
            payload = {"tag": game.state.day, "gehalt": 0,
                       "firma": {"umsatz": revenue, "gehaelter": 0, "nebenkosten": costs}}
            game._log(fg.EV_DAY_END, payload)
            payloads.append(payload)
        return payloads

    def _worthy(self, db, money=30000):
        game = self._founded(db, money)
        self._days(game, 10)
        return game

    def _spend(self, game, amount):
        game._log(fg.EV_SOLVED, {"aufgabe": "ausgabe", "tag": game.state.day, "richtig": False,
                                 "geld": -int(amount)})

    def test_inhalte(self):
        self.assertEqual(fg._validate_loans(fg.GAME), [])
        broken = copy.deepcopy(fg.GAME)
        rules = broken["balancing"]["kredite"]
        rules["pakete"][1]["id"] = "kurz"
        rules["pakete"][2]["laufzeit"] = 33
        rules["mahnung"]["stufen"][0]["reputation"] = {"gibtsnicht": -1}
        self.assertEqual(len(fg._validate_loans(broken)), 3)
        del broken["balancing"]["kredite"]
        self.assertEqual(len(fg._validate_loans(broken)), 1)

    def test_zinsstaffel(self):
        # Kurz und klein guenstiger, lang und gross teurer
        packages = [fg.loan_offer_numbers(item["summe"], item["laufzeit"])
                    for item in fg.loan_rules()["pakete"]]
        rates = [item["zins"] for item in packages]
        self.assertEqual(rates, sorted(rates))
        self.assertLess(rates[0], rates[-1])
        by_term = [fg.loan_rate_pa(20000, term) for term in fg.loan_terms()]
        self.assertEqual(by_term, sorted(by_term))
        self.assertLess(fg.loan_rate_pa(10000, 50), fg.loan_rate_pa(90000, 50))
        # Annuitaet: nach genau "laufzeit" Raten ist alles bezahlt
        for item in packages:
            loan = {"rest": item["summe"], "zins_offen": 0, "gebuehren": 0,
                    "rate": item["rate"], "zins": item["zins"]}
            rows = fg.loan_schedule(loan, 1)
            self.assertEqual(len(rows), item["laufzeit"])
            self.assertEqual(sum(row["tilgung"] for row in rows), item["summe"])
            self.assertEqual(rows[-1]["rest"], 0)
            self.assertLessEqual(rows[-1]["rate"], item["rate"])
            self.assertEqual(sum(row["rate"] for row in rows), item["gesamt"])
            # Zinsanteil sinkt, Tilgungsanteil steigt
            self.assertGreater(rows[0]["zinsen"], rows[-2]["zinsen"])
            self.assertLess(rows[0]["tilgung"], rows[-2]["tilgung"])

    def test_bonitaet(self):
        with TempDB() as db:
            game = self._founded(db)
            self.assertIn(("kredite", "Kredite"), fg.firm_tabs(game.state))
            check = fg.credit_check(game.state, self.content)
            self.assertFalse(check["ok"])
            self.assertEqual([point["ok"] for point in check["punkte"]], [False, False, True])
            self.assertEqual(check["ab_tag"], game.state.firm["tag"] + 10)
            self.assertEqual(check["rahmen"], 0)
            with self.assertRaises(ValueError):
                game.take_loan(0, 0, "kurz")
            # 9 Tage reichen nicht, der zehnte schon (2.000 EUR Umsatz pro Tag)
            self._days(game, 9)
            self.assertFalse(fg.credit_check(game.state, self.content)["ok"])
            self._days(game, 1)
            check = fg.credit_check(game.state, self.content)
            self.assertTrue(check["ok"])
            self.assertEqual(check["umsatz"], 20000)
            self.assertEqual(check["rahmen"], 33000)   # 1,5 x Umsatz x 1,1 (Ansehen 80)
            packages = {item["paket"]: item for item in fg.loan_packages(game.state,
                                                                         self.content)}
            self.assertEqual(packages["kurz"]["problem"], "")
            self.assertEqual(packages["investition"]["problem"], "")
            self.assertIn("Kreditrahmen", packages["gross"]["problem"])
            # Freie Summe: Mindestbetrag und Schritte
            self.assertTrue(fg.loan_offer(game.state, 4000, 50, content=self.content)["problem"])
            self.assertTrue(fg.loan_offer(game.state, 10500, 50,
                                          content=self.content)["problem"])
            self.assertTrue(fg.loan_offer(game.state, 10000, 44,
                                          content=self.content)["problem"])
            self.assertEqual(fg.loan_offer(game.state, 33000, 50,
                                           content=self.content)["problem"], "")
            self.assertTrue(fg.loan_offer(game.state, 34000, 50,
                                          content=self.content)["problem"])
            self.assertEqual(fg.free_loan_limits(game.state, self.content), (5000, 33000, 1000))
            self.assertEqual(fg.clamp_loan_amount(game.state, 99999, self.content), 33000)
            # Umsatz bricht ein: keine Bonitaet mehr
            self._days(game, 10, revenue=500)
            self.assertFalse(fg.credit_check(game.state, self.content)["ok"])

    def test_raten_muessen_tragbar_sein(self):
        """Kapitaldienstfaehigkeit: alle Raten hoechstens die Haelfte des Gewinns."""
        with TempDB() as db:
            game = self._founded(db)
            self._days(game, 10, revenue=2500, costs=500)     # Gewinn 2.000 pro Tag
            check = fg.credit_check(game.state, self.content)
            self.assertEqual((check["raten_max"], check["raten_belegt"]), (1000, 0))
            short = fg.loan_offer(game.state, 30000, 20, content=self.content)
            self.assertIn("Rate ist zu hoch", short["problem"])
            self.assertEqual(fg.loan_offer(game.state, 30000, 50,
                                           content=self.content)["problem"], "")
            game.take_loan(30000, 50)
            check = fg.credit_check(game.state, self.content)
            self.assertEqual(check["raten_belegt"], game.state.loan_rates())
            self.assertIn("Tragbare Raten", fg.credit_frame_text(check))
            with self.assertRaises(ValueError):
                game.take_loan(10000, 20)

    def test_ansehen_zaehlt(self):
        with TempDB() as db:
            game = self._worthy(db)
            game._log(fg.EV_SOLVED, {"aufgabe": "x", "tag": game.state.day, "richtig": False,
                                     "geld": 0, "reputation": {key: -25 for key in
                                                               fg.AXIS_KEYS}})
            check = fg.credit_check(game.state, self.content)
            self.assertFalse(check["ok"])
            self.assertFalse(check["punkte"][2]["ok"])
        with TempDB() as db:
            game = self._worthy(db)
            game._log(fg.EV_SOLVED, {"aufgabe": "x", "tag": game.state.day, "richtig": True,
                                     "geld": 0, "reputation": {key: 30 for key in
                                                               fg.AXIS_KEYS}})
            # Ansehen 100: Rahmen x 1,25
            self.assertEqual(fg.credit_check(game.state, self.content)["rahmen"], 37000)

    def test_aufnahme_und_tilgung(self):
        with TempDB() as db:
            game = self._worthy(db)
            before = game.state.money
            payload = game.take_loan(0, 0, "investition")
            offer = fg.loan_offer_numbers(30000, 50, self.content)
            self.assertEqual((payload["summe"], payload["laufzeit"], payload["rate"]),
                             (30000, 50, offer["rate"]))
            state = game.state
            self.assertEqual(state.money, before + 30000)
            self.assertEqual(state.book[state.day]["ein"][fg.BOOK_LOAN], 30000)
            self.assertEqual(fg.credit_check(state, self.content)["frei"], 3000)
            self.assertEqual(state.loan_rates(), offer["rate"])
            self.assertIn("Kreditraten", fg.fixed_costs_text(state))
            # Erster Feierabend: Rate automatisch, Zins und Tilgung getrennt gebucht
            day = state.day
            end = game.end_day()
            self.assertEqual(end["firma"]["kredite"][0]["art"], "rate")
            self.assertIn("Kreditraten: -", fg.firm_day_text(end["firma"]))
            state = game.state
            loan = state.running_loans()[0]
            first = fg.loan_schedule({"rest": 30000, "zins_offen": 0, "gebuehren": 0,
                                      "rate": offer["rate"], "zins": offer["zins"]}, 1)[0]
            self.assertEqual(state.book[day]["aus"][fg.BOOK_LOAN_INTEREST], first["zinsen"])
            self.assertEqual(state.book[day]["aus"][fg.BOOK_LOAN_REPAY], first["tilgung"])
            self.assertEqual(loan["rest"], 30000 - first["tilgung"])
            status = fg.loan_status(state, loan, self.content)
            self.assertEqual(status["raten_offen"], 49)
            self.assertTrue(fg.loan_status_lines(status))
            # Alle 50 Raten: vollstaendig zurueckgezahlt, Zinsen wie angeboten
            self._days(game, 49)
            state = game.state
            self.assertEqual(state.running_loans(), [])
            loan = state.done_loans()[0]
            self.assertEqual((loan["ende_art"], loan["bezahlt_tilgung"]), ("zurueckgezahlt",
                                                                           30000))
            self.assertEqual(loan["bezahlt_zins"], offer["zinsen_gesamt"])
            self.assertEqual(state.dunning, 0)
            kinds = [entry["art"] for entry in fg.journey(state, self.content)]
            self.assertIn("kredit", kinds)
            self.assertIn("kredit_ende", kinds)

    def test_mehrere_kredite_parallel(self):
        with TempDB() as db:
            game = self._worthy(db)
            game.take_loan(0, 0, "kurz")
            game.take_loan(10000, 30)
            state = game.state
            self.assertEqual(len(state.running_loans()), 2)
            self.assertEqual(len({loan["id"] for loan in state.running_loans()}), 2)
            self.assertEqual(fg.credit_check(state, self.content)["frei"], 13000)
            short = fg.loan_offer_numbers(10000, 20, self.content)
            free = fg.loan_offer_numbers(10000, 30, self.content)
            self.assertEqual(state.loan_rates(), short["rate"] + free["rate"])
            self._days(game, 20)
            state = game.state
            self.assertEqual([loan["name"] for loan in state.running_loans()],
                             ["Freier Kredit 10.000 €"])
            self.assertEqual(state.done_loans()[0]["name"], "Kurzkredit")
            self._days(game, 10)
            self.assertEqual(game.state.running_loans(), [])
            self.assertEqual(game.state.loan_debt(), 0)

    def test_geplatzte_rate_und_mahnstufen(self):
        with TempDB() as db:
            game = self._worthy(db)
            game.take_loan(0, 0, "kurz")
            steps = fg.loan_rules()["mahnung"]["stufen"]
            reliability = game.state.reputation["zuverlaessigkeit"]
            self._spend(game, game.state.money + 1000)       # Konto leer
            end = game.end_day()
            state = game.state
            loan = state.running_loans()[0]
            self.assertEqual(state.dunning, 1)
            self.assertEqual(loan["raten"], 0)
            self.assertEqual(loan["ausfaelle"], 1)
            self.assertEqual(loan["gebuehren"], steps[0]["gebuehr"])
            self.assertEqual(state.reputation["zuverlaessigkeit"], reliability - 2)
            self.assertIn("geplatzt", fg.firm_day_text(end["firma"]))
            self.assertIn("Zahlungserinnerung", fg.dunning_text(state, self.content))
            # Stufe 1: nur halber Rahmen (18.000 Umsatz x 1,5 x 1,1 / 2, auf 1.000 abgerundet)
            check = fg.credit_check(state, self.content)
            self.assertEqual(check["umsatz"], 18000)
            self.assertEqual(check["rahmen"], 14000)
            # Zweite geplatzte Rate: Mahnung, Zinsaufschlag, keine neuen Kredite
            self._days(game, 1, revenue=0)
            state = game.state
            self.assertEqual(state.dunning, 2)
            loan = state.running_loans()[0]
            self.assertEqual(fg.loan_interest(loan, state.dunning, self.content),
                             loan["zins"] + steps[1]["zins_plus"])
            self.assertTrue(fg.credit_check(state, self.content)["sperre"])
            with self.assertRaises(ValueError):
                game.take_loan(0, 0, "kurz")
            # Hoechstens Stufe 3, auch wenn weiter Raten platzen
            self._days(game, 3, revenue=0)
            self.assertEqual(game.state.dunning, 3)
            self.assertEqual(game.state.running_loans()[0]["ausfaelle"], 5)
            kinds = [entry["art"] for entry in fg.journey(game.state, self.content)]
            self.assertEqual(kinds.count("kredit_ausfall"), 5)
            # Wieder Geld: Raten laufen, die Stufe sinkt alle 10 Arbeitstage um 1
            self._days(game, 9, revenue=5000)
            self.assertEqual(game.state.dunning, 3)
            self._days(game, 1, revenue=5000)
            self.assertEqual(game.state.dunning, 2)
            self._days(game, 20, revenue=5000)
            state = game.state
            self.assertEqual(state.dunning, 0)
            # Geplatzte Raten verlaengern die Laufzeit, Gebuehren sind bezahlt
            loan = state.loans[next(iter(state.loans))]
            self.assertEqual(loan["ende_art"], "zurueckgezahlt")
            self.assertGreater(loan["raten"], 20)
            self.assertEqual(loan["bezahlt_gebuehren"],
                             steps[0]["gebuehr"] + steps[1]["gebuehr"] + 3 * steps[2]["gebuehr"])
            self.assertGreater(loan["bezahlt_zins"],
                               fg.loan_offer_numbers(10000, 20, self.content)["zinsen_gesamt"])

    def test_mehrere_geplatzte_raten_eine_stufe(self):
        with TempDB() as db:
            game = self._worthy(db)
            game.take_loan(0, 0, "kurz")
            game.take_loan(20000, 50)
            self._spend(game, game.state.money)
            self._days(game, 1, revenue=0)
            state = game.state
            self.assertEqual(state.dunning, 1)
            self.assertEqual([loan["ausfaelle"] for loan in state.running_loans()], [1, 1])

    def test_abloesen(self):
        with TempDB() as db:
            game = self._worthy(db)
            game.take_loan(0, 0, "investition")
            self._days(game, 5)
            state = game.state
            loan = state.running_loans()[0]
            payoff = fg.loan_payoff(loan, self.content)
            self.assertEqual(payoff["vorfaelligkeit"], -(-loan["rest"] // 100))
            status = fg.loan_status(state, loan, self.content)
            self.assertIn("Vorfälligkeitsentschädigung", fg.loan_payoff_text(status,
                                                                              self.content))
            before = state.money
            game.repay_loan(loan["id"])
            state = game.state
            self.assertEqual(state.money, before - payoff["gesamt"])
            self.assertEqual(state.running_loans(), [])
            self.assertEqual(state.done_loans()[0]["ende_art"], "abgeloest")
            self.assertEqual(state.book[state.day]["aus"][fg.BOOK_LOAN_FEES],
                             payoff["vorfaelligkeit"])
            with self.assertRaises(ValueError):
                game.repay_loan(loan["id"])
            self._days(game, 1)
            self.assertEqual(game.state.loan_log[-1][1], "abgeloest")
        with TempDB() as db:
            game = self._worthy(db)
            game.take_loan(0, 0, "kurz")
            self._spend(game, game.state.money)
            with self.assertRaises(ValueError):
                game.repay_loan(game.state.running_loans()[0]["id"])

    def test_abgleich_zwei_geraete(self):
        """Dasselbe Kredit-Ereignis doppelt (zwei Geraete) zaehlt einmal, und
        ein zweites Geraet rechnet aus den Ereignissen denselben Stand."""
        with TempDB() as db:
            game = self._worthy(db)
            payload = game.take_loan(0, 0, "kurz")
            db.log_game_event(fg.EV_LOAN, json.dumps(payload), "Handy")
            game.reload()
            self.assertEqual(len(game.state.loans), 1)
            self._days(game, 3)
            other = fg.Game(db, "Handy", self.content)
            self.assertEqual(other.state.money, game.state.money)
            self.assertEqual(other.state.running_loans()[0]["rest"],
                             game.state.running_loans()[0]["rest"])

    def test_ohne_kredit_alles_wie_bisher(self):
        with TempDB() as db:
            game = self._founded(db)
            end = game.end_day()
            self.assertNotIn("kredite", end["firma"])
            self.assertNotIn("Kredit", fg.firm_day_text(end["firma"]))
            self.assertNotIn("Kreditraten", fg.fixed_costs_text(game.state))
            self.assertEqual(game.state.loan_rates(), 0)


class SteuernTest(unittest.TestCase):
    """Umsatzsteuer der eigenen Firma (ab 0.42)."""

    setUp = FirmaTest.setUp
    _rich = FirmaTest._rich
    _founded = FirmaTest._founded
    _spend = KrediteTest._spend

    def _days(self, game, count, revenue=1190, costs=0, wages=0, tax=True):
        """Feierabende mit festem (Brutto-)Umsatz, ab 0.42 mit Umsatzsteuer."""
        for _ in range(count):
            payload = {"tag": game.state.day, "gehalt": 0,
                       "firma": {"umsatz": revenue, "gehaelter": wages, "nebenkosten": costs}}
            if tax:
                payload["firma"]["ust"] = 1
            game._log(fg.EV_DAY_END, payload)

    def test_inhalte(self):
        self.assertEqual(fg._validate_business(fg.GAME), [])
        broken = copy.deepcopy(fg.GAME)
        broken["balancing"]["steuern"]["faellig_tage"] = 0
        broken["balancing"]["marketing"]["formen"][1]["id"] = "anzeige"
        broken["balancing"]["marketing"]["formen"][2]["wirkung"] = {"gibtsnicht": 1}
        broken["balancing"]["zertifizierungen"]["liste"][0]["vorteil"] = {"kochen": 2}
        broken["balancing"]["zertifizierungen"]["grossauftraege"]["liste"][0]["braucht"] = \
            ["gibtsnicht"]
        broken["balancing"]["zertifizierungen"]["grossauftraege"]["liste"][1]["thema"] = "wlan"
        self.assertEqual(len(fg._validate_business(broken)), 6)

    def test_ruecklage_und_voranmeldung(self):
        with TempDB() as db:
            game = self._founded(db)
            start = game.state.money
            self.assertEqual(fg.tax_next_due(game.state, self.content), game.state.day + 11)
            # 1.190 brutto Umsatz = 190 Umsatzsteuer, 119 Nebenkosten = 19 Vorsteuer
            self._days(game, 11, revenue=1190, costs=119)
            state = game.state
            self.assertEqual(state.tax_reserve, 11 * 171)
            self.assertEqual(state.money, start + 11 * (1190 - 119 - 171))
            days = fg.finance_days(state)
            self.assertEqual(days[0]["aus"][fg.BOOK_TAX], 171)
            self.assertEqual(days[0]["gewinn"], 1190 - 119 - 171)
            status = fg.tax_status(state, self.content)
            self.assertEqual((status["ust"], status["vorsteuer"], status["zahllast"]),
                             (11 * 190, 11 * 19, 11 * 171))
            self.assertTrue(fg.tax_status_lines(status))
            # Zwoelfter Feierabend: Voranmeldung, bezahlt aus der Ruecklage
            self._days(game, 1, revenue=1190, costs=119)
            state = game.state
            self.assertEqual(state.tax_reserve, 0)
            self.assertEqual(state.money, start + 12 * (1190 - 119 - 171))
            kind, data = state.tax_log[-1][1], state.tax_log[-1][2]
            self.assertEqual(kind, "voranmeldung")
            self.assertEqual((data["ust"], data["vorsteuer"], data["zahllast"],
                              data["aus_ruecklage"]), (2280, 228, 2052, 2052))
            self.assertIn("Zahllast 2.052 €", fg.tax_filing_text(data))
            self.assertEqual(state.dunning, 0)
            self.assertEqual(fg.tax_status(state, self.content)["tage"], 0)
            kinds = [entry["art"] for entry in fg.journey(state, self.content)]
            self.assertIn("steuer", kinds)

    def test_vorsteuer_erstattung(self):
        with TempDB() as db:
            game = self._founded(db)
            start = game.state.money
            # Mehr Ausgaben mit Vorsteuer als Einnahmen: das Finanzamt zahlt zurueck
            self._days(game, 12, revenue=0, costs=1190)
            state = game.state
            data = state.tax_log[-1][2]
            self.assertEqual(data["erstattung"], 12 * 190)
            self.assertEqual(state.money, start - 12 * 1190 + 12 * 190)
            self.assertEqual(state.book[state.day - 1]["ein"][fg.BOOK_TAX], 12 * 190)
            self.assertIn("Erstattung", fg.tax_filing_text(data))

    def test_alte_feierabende_ohne_steuer(self):
        """Feierabende aus 0.41 (ohne "ust") bleiben steuerfrei."""
        with TempDB() as db:
            game = self._founded(db)
            start = game.state.money
            self._days(game, 15, tax=False)
            state = game.state
            self.assertEqual((state.tax_days, state.tax_reserve), (0, 0))
            self.assertEqual(state.money, start + 15 * 1190)
            # Der erste echte Feierabend in 0.42 startet den Zeitraum
            end = game.end_day()
            self.assertEqual(end["firma"]["ust"], 1)
            self.assertEqual(game.state.tax_days, 1)
            self.assertEqual(game.state.tax_period["start"], state.day)

    def test_engpass_mahnstufe_wie_bei_krediten(self):
        with TempDB() as db:
            game = self._founded(db)
            self._spend(game, game.state.money)          # Konto leer
            reliability = game.state.reputation["zuverlaessigkeit"]
            # Umsatz und Gehaelter gleich: kein Geld fuer die Ruecklage
            self._days(game, 12, revenue=1190, wages=1190)
            state = game.state
            steps = fg.loan_rules()["mahnung"]["stufen"]
            self.assertEqual(state.dunning, 1)
            self.assertEqual(state.tax_debt, 12 * 190 + steps[0]["gebuehr"])
            self.assertEqual(state.reputation["zuverlaessigkeit"], reliability - 2)
            self.assertIn("Umsatzsteuer", fg.tax_debt_text(state, self.content))
            self.assertIn("Kreditrate oder Umsatzsteuer", fg.dunning_text(state, self.content))
            # Dieselbe Stufe sperrt auch neue Kredite (halber Rahmen bei Stufe 1)
            self.assertIn("Zahlungserinnerung", fg.dunning_text(state, self.content))
            # Noch ein Feierabend ohne Geld: Stufe 2
            self._days(game, 1, revenue=0)
            self.assertEqual(game.state.dunning, 2)
            self.assertTrue(fg.credit_check(game.state, self.content)["sperre"])
            # Wieder Geld: Schuld wird nachgezahlt, Stufe sinkt spaeter wieder
            self._days(game, 1, revenue=11900)
            state = game.state
            self.assertEqual(state.tax_debt, 0)
            self.assertEqual(state.dunning, 2)
            # Gezahlt zaehlt nur, was wirklich ans Finanzamt ging (samt Gebuehren)
            status = fg.tax_status(state, self.content)
            self.assertEqual(status["gezahlt"], 12 * 190 + sum(s["gebuehr"] for s in steps[:2]))
            self.assertEqual([kind for _day, kind, _data in state.tax_log].count("ausfall"), 2)
            kinds = [entry["art"] for entry in fg.journey(state, self.content)]
            self.assertEqual(kinds.count("steuer_ausfall"), 2)
            self._days(game, 20, revenue=11900)
            self.assertEqual(game.state.dunning, 0)

    def test_kredit_und_steuer_nur_eine_stufe(self):
        with TempDB() as db:
            game = self._founded(db)
            self._spend(game, game.state.money)
            # Umsatz geht komplett fuer Gehaelter drauf: Ruecklage bleibt leer
            self._days(game, 11, revenue=1900, wages=1900)
            self.assertEqual(game.state.tax_reserve, 0)
            # Kredit direkt als Ereignis (die Bank prueft sonst den Gewinn)
            offer = fg.loan_offer_numbers(10000, 20, self.content)
            game._log(fg.EV_LOAN, {"kredit": "kredit:%d:1" % game.state.day,
                                   "tag": game.state.day, "name": "Kurzkredit",
                                   "paket": "kurz", "summe": 10000, "laufzeit": 20,
                                   "zins": offer["zins"], "rate": offer["rate"]})
            self._spend(game, game.state.money)
            # Rate und Voranmeldung platzen am selben Feierabend: nur eine Stufe
            self._days(game, 1, revenue=0)
            state = game.state
            self.assertEqual(state.dunning, 1)
            self.assertEqual(state.running_loans()[0]["ausfaelle"], 1)
            steps = fg.loan_rules()["mahnung"]["stufen"]
            self.assertEqual(state.tax_debt, round(11 * 1900 * 19 / 119.0) + steps[0]["gebuehr"])
            items = fg.taxes_today(state, state.day - 1)
            self.assertEqual([item["art"] for item in items], ["voranmeldung", "ausfall"])
            # Das Ansehen sinkt nur einmal (steht beim Kredit)
            self.assertEqual(items[1]["reputation"], {})
            self.assertTrue(fg.tax_day_lines(items, self.content))

    def test_feierabend_text(self):
        with TempDB() as db:
            game = self._founded(db)
            game.hire(fg.applicants(game.state, self.content)[0]["id"])
            end = game.end_day()
            self.assertEqual(end["firma"]["steuer"][0]["art"], "ruecklage")
            self.assertIn("Umsatzsteuer in die Rücklage", fg.firm_day_text(end["firma"]))


class MarketingTest(unittest.TestCase):
    """Werbung der eigenen Firma (ab 0.42)."""

    setUp = FirmaTest.setUp
    _rich = FirmaTest._rich
    _founded = FirmaTest._founded
    _days = SteuernTest._days

    def test_laufend(self):
        with TempDB() as db:
            game = self._founded(db)
            day = game.state.day
            today = game.state.inquiries()
            before = fg.GameState(list(game.state.history), self.content)
            payload = game.book_ad("online", fg.AD_RUNNING)
            self.assertEqual((payload["ab_tag"], payload["kosten"]), (day + 1, 110))
            state = game.state
            # Heute aendert sich nichts, erst ab dem naechsten Arbeitstag
            self.assertEqual(state.inquiries(), today)
            self.assertEqual(state.ads_active(), [])
            with self.assertRaises(ValueError):
                game.book_ad("online", fg.AD_ONCE)        # laeuft schon
            money = state.money
            self._days(game, 1, revenue=0, tax=False)
            self.assertEqual(game.state.money, money)      # heute noch keine Kosten
            state = game.state
            plain = fg.inquiries_for_day(before, state.day, self.content)
            more = state.inquiries()
            self.assertEqual(len(more), len(plain) + 1)
            for old, new in zip(plain, more):
                self.assertEqual(new["menge"], math.ceil(old["menge"] * 1.1))
            self.assertIn("+1 Anfrage pro Tag", fg.marketing_summary_text(state, self.content))
            self.assertIn("Werbung 110 €", fg.fixed_costs_text(state))
            money = state.money
            self._days(game, 1, revenue=0, tax=False)
            self.assertEqual(game.state.money, money - 110)
            self.assertEqual(game.state.book[state.day]["aus"][fg.BOOK_MARKETING], 110)
            # Kuendigen: heute kostet es noch, morgen nicht mehr
            game.stop_ad("online")
            money = game.state.money
            self._days(game, 1, revenue=0, tax=False)
            self.assertEqual(game.state.money, money - 110)
            self.assertEqual(game.state.ads_active(), [])
            money = game.state.money
            self._days(game, 1, revenue=0, tax=False)
            self.assertEqual(game.state.money, money)
            with self.assertRaises(ValueError):
                game.stop_ad("online")
            # Danach wieder buchbar
            game.book_ad("online", fg.AD_ONCE)

    def test_einmalig_und_tickets(self):
        with TempDB() as db:
            game = self._founded(db)
            money = game.state.money
            tickets = len(game.state.customer_tickets())
            game.book_ad("bus", fg.AD_ONCE)
            form = fg.ad_form("bus")
            self.assertEqual(game.state.money, money - form["einmalig"]["preis"])
            status = {item["id"]: item for item in fg.ad_status(game.state, self.content)}
            self.assertIn("nächsten Arbeitstag", status["bus"]["stand"])
            self._days(game, 1, revenue=0, tax=False)
            state = game.state
            self.assertEqual(len(state.customer_tickets()), tickets + 1)
            # Guter Ruf (Kundenzufriedenheit 80) plus Werbung
            self.assertEqual(fg.offer_advantage_parts(state, None, self.content),
                             [("guter Ruf", 3), ("Werbung", 1)])
            self.assertEqual(fg.offer_advantage(state, self.content), 4)
            # Wirkt genau "tage" Arbeitstage, danach laeuft es von selbst aus
            self._days(game, form["einmalig"]["tage"] - 1, revenue=0, tax=False)
            self.assertEqual(len(game.state.ads_active()), 1)
            self._days(game, 1, revenue=0, tax=False)
            self.assertEqual(game.state.ads_active(), [])
            self.assertEqual(fg.offer_advantage(game.state, self.content), 3)
            game.book_ad("bus", fg.AD_ONCE)
            kinds = [entry["art"] for entry in fg.journey(game.state, self.content)]
            self.assertEqual(kinds.count("werbung"), 2)

    def test_geld_und_zwei_geraete(self):
        with TempDB() as db:
            game = self._founded(db)
            KrediteTest._spend(self, game, game.state.money - 1000)
            offer = fg.ad_offer(game.state, "messe", fg.AD_ONCE, self.content)
            self.assertIn("reicht dein Geld nicht", offer["problem"])
            with self.assertRaises(ValueError):
                game.book_ad("messe", fg.AD_ONCE)
            with self.assertRaises(ValueError):
                game.book_ad("gibtsnicht", fg.AD_RUNNING)
            payload = game.book_ad("anzeige", fg.AD_RUNNING)
            db.log_game_event(fg.EV_ADS, json.dumps(payload), "Handy")
            game.reload()
            self.assertEqual(len(game.state.ads), 1)
            self._days(game, 2, revenue=0, tax=False)
            other = fg.Game(db, "Handy", self.content)
            self.assertEqual(other.state.money, game.state.money)


class ZertifizierungTest(unittest.TestCase):
    """Zertifizierungen und Grossauftraege (ab 0.42)."""

    setUp = FirmaTest.setUp
    _rich = FirmaTest._rich
    _founded = FirmaTest._founded
    _days = SteuernTest._days

    def test_erwerb_und_vorteil(self):
        with TempDB() as db:
            game = self._founded(db, money=60000)
            money = game.state.money
            cert = fg.certificate("iso27001")
            payload = game.start_cert("iso27001")
            self.assertEqual(payload["bis_tag"], game.state.day + cert["tage"])
            self.assertEqual(game.state.money, money - cert["preis"])
            self.assertEqual(game.state.book[game.state.day]["aus"][fg.BOOK_CERT],
                             cert["preis"])
            # Nur eine gleichzeitig, keine doppelt
            self.assertIn("läuft schon", fg.cert_offer(game.state, "windows",
                                                        self.content)["problem"])
            with self.assertRaises(ValueError):
                game.start_cert("iso27001")
            self.assertEqual(game.state.certs_held(), set())
            self.assertEqual(fg.cert_advantage(game.state, "sicherheit"), 0)
            self._days(game, cert["tage"] - 1, revenue=0, tax=False)
            self.assertEqual(game.state.certs_held(), set())
            self._days(game, 1, revenue=0, tax=False)
            state = game.state
            self.assertEqual(state.certs_held(), {"iso27001"})
            self.assertEqual(fg.cert_advantage(state, "sicherheit"), 4)
            self.assertEqual(fg.cert_advantage(state, "netzwerk"), 1)
            self.assertEqual(fg.cert_advantage(state, None), 0)
            status = {item["id"]: item for item in fg.cert_status(state, self.content)}
            self.assertEqual(status["iso27001"]["stand"], "erworben")
            self.assertIn("Kreisklinikum", fg.cert_unlock_text(status["iso27001"]))
            self.assertIn("schon", status["iso27001"]["angebot"]["problem"])
            self.assertEqual(status["windows"]["angebot"]["problem"], "")
            kinds = [entry["art"] for entry in fg.journey(state, self.content)]
            self.assertIn("zertifizierung", kinds)
            # Obergrenze aller Vorteile
            content = copy.deepcopy(self.content)
            content["balancing"]["zertifizierungen"]["vorteil_max"] = 3
            self.assertEqual(fg.offer_advantage(state, content, "sicherheit"), 3)

    def test_grossauftraege(self):
        with TempDB() as db:
            game = self._founded(db, money=60000)
            self.assertEqual(fg.gross_tenders(game.state, game.state.day + 30,
                                              self.content), [])
            game.start_cert("windows")
            self._days(game, 7, revenue=0, tax=False)
            for _ in range(10):
                tenders = [item for item in game.state.tenders() if item.get("gross")]
                if tenders:
                    break
                self._days(game, 1, revenue=0, tax=False)
            state = game.state
            self.assertEqual(len(tenders), 1)
            tender = tenders[0]
            self.assertEqual(tender["vorlage"], "gross:rathaus-windows")
            self.assertTrue(tender["id"].startswith(fg.GROSS_PREFIX))
            self.assertEqual(tender["aufwand"], 100)
            self.assertIn("nur mit Microsoft-Partner", fg.gross_badge_text(tender))
            details = fg.project_details(tender, self.content)
            self.assertFalse(details["lernbar"])
            self.assertIn("Windows 11", details["auftrag"])
            # Angebot mit Kampfpreis gewinnen: laeuft wie ein normales Projekt
            markup = min(fg.offer_rules()["zuschlaege"])
            answer = fg.find_solution(fg.project_task(tender, markup))
            result = game.send_project_offer(tender["id"], markup, answer)
            state = game.state
            self.assertEqual(result["vorteil"], fg.offer_advantage(state, self.content,
                                                                   "systeme"))
            self.assertIn("Zertifizierungen", result["vorteil_gruende"])
            if result["gewonnen"]:
                project = state.projects[tender["id"]]
                self.assertEqual(fg.project_details(project, self.content)["kunde"],
                                 "Stadtverwaltung Talheim")
                self.assertTrue(fg.gross_badge_text(project))
            # Grossauftraege mit zwei Zertifizierungen erst, wenn beide da sind
            names = {fg.gross_tenders(state, day, self.content)[0]["titel"]
                     for day in range(state.day, state.day + 60, 5)
                     if fg.gross_tenders(state, day, self.content)}
            self.assertEqual(names, {"Windows 11 für 60 Arbeitsplätze im Rathaus"})
            # Bei Grossauftraegen bietet ein Mitbewerber mehr mit als bei Projekten
            extra = fg.gross_rules(self.content)["mitbieter_extra"]
            self.assertEqual(extra, 1)
            for day in range(1, 30):
                normal = fg.competitor_bids("projekt", "normal", "systeme", 7, day, "x",
                                            self.content)
                more = fg.competitor_bids("projekt", "normal", "systeme", 7, day, "x",
                                          self.content, extra=extra)
                self.assertEqual(sum(map(len, more)), sum(map(len, normal)) + 1)
            # Derselbe Grossauftrag nie zweimal hintereinander
            slots = [[item["vorlage"] for item in fg.gross_tenders(state, day, self.content)
                      if item["slot"] == slot]
                     for slot, day in enumerate(range(state.firm["tag"] + 2,
                                                      state.day + 60, 5))]
            for before, after in zip(slots, slots[1:]):
                self.assertFalse(before and before == after)


class PersonalTest(unittest.TestCase):
    """Personal ab 0.43: Macken mit Staerke/Schwaeche und Stufen, Coaching,
    Stimmung, Krankheit, Urlaub, Konflikte."""

    setUp = FirmaTest.setUp
    _rich = FirmaTest._rich
    _founded = FirmaTest._founded
    _day_end = MitarbeiterThemenTest._day_end

    def _hire(self, game, quirk_id, number=0, **extra):
        """Stellt einen Bewerber mit einer bestimmten Macke ein."""
        applicant = dict(fg.applicants(game.state, self.content)[0])
        quirk = fg.quirk_by_id(quirk_id, self.content)
        data = {key: applicant[key] for key in ("name", "aussehen", "werte", "themen",
                                                "gehalt", "herkunft", "schwerpunkt", "rolle")}
        data.update(id="test-%d" % number, macke=quirk["text"], macke_id=quirk_id,
                    tag=game.state.day, name="Person%d Test" % number)
        data.update(extra)
        game.db.log_game_event(fg.EV_HIRED, json.dumps(data), "PC")
        game.reload()
        return data["id"]

    def _live_day(self, game, personal=None, **firm):
        """Feierabend mit den Regeln ab 0.43 (firma.personal vorhanden)."""
        firm = dict(firm)
        firm["personal"] = personal or []
        return self._day_end(game, firm)

    def test_inhalte(self):
        self.assertEqual(fg._validate_firm(fg.GAME), [])
        quirks = fg.GAME["firma"]["macken"]
        self.assertEqual(len([item for item in quirks if not item.get("kollege")]), 12)
        self.assertEqual({item["kollege"] for item in quirks if item.get("kollege")},
                         {item["kollege"] for item in fg.GAME["firma"]["wechsel"]})
        for item in quirks:
            self.assertTrue(item["plus"] and item["minus"], item["id"])
            for key, value in list(item["plus"].items()) + list(item["minus"].items()):
                # Jede Wirkung hat einen eigenen Text (kein Rueckfall auf den Schluessel)
                self.assertNotEqual(fg.quirk_effect_text(key, value).split()[0], key)
        broken = _content()
        broken["firma"]["macken"][0]["minus"] = {"gibtsnicht": 1}
        self.assertTrue(fg._validate_firm(broken))

    def test_macke_bei_bewerbern_und_alten_spielstaenden(self):
        with TempDB() as db:
            game = self._founded(db)
            applicant = fg.applicants(game.state, self.content)[0]
            self.assertTrue(applicant["macke_id"])
            self.assertIn(applicant["macke_info"]["stufe"], (2, 3))
            game.hire(applicant["id"])
            self.assertEqual(game.state.staff[applicant["id"]]["macke_id"],
                             applicant["macke_id"])
            # Aeltere Spielstaende kennen nur den Text der Macke
            quirk = fg.GAME["firma"]["macken"][6]
            old = dict(game.state.staff[applicant["id"]], id="alt-1", macke=quirk["text"])
            old.pop("macke_id")
            db.log_game_event(fg.EV_HIRED, json.dumps(old), "PC")
            game.reload()
            self.assertEqual(game.state.quirk_of("alt-1")["id"], "gruendlich")
            # Bitweiche-Kollegen bringen ihre eigene Macke mit (Stufe mittel)
            tim = dict(old, id=fg.STAFF_PREFIX + "tim", herkunft="bitweiche",
                       macke=fg.colleague("tim")["macke"])
            db.log_game_event(fg.EV_HIRED, json.dumps(tim), "PC")
            game.reload()
            info = game.state.quirk_of(fg.STAFF_PREFIX + "tim")
            self.assertEqual((info["id"], info["stufe"]), ("neugierig", 2))

    def test_stufen_schwaechen_sich_ab(self):
        rules = self.content["firma"]["personal"]["macken"]
        every = rules["abschwaechen_tage"]
        data = {"macke_id": "gruendlich", "tag": 10}
        start = fg.quirk_start_stage("x", data)
        for days, coached in ((0, 0), (every - 1, 0), (every, 0), (2 * every, 0),
                              (5 * every, 0), (0, 1), (every, 1)):
            item = fg.quirk_state("x", data, 10 + days, coached, self.content)
            expected = max(1, start - days // every - coached)
            self.assertEqual(item["stufe"], expected)
            factor = rules["stufen"][str(expected)][1] / 100.0
            # Die Schwaeche wird schwaecher, die Staerke bleibt
            self.assertAlmostEqual(fg.quirk_effect(item, "umsatz"), -15 * factor)
            self.assertEqual(fg.quirk_effect(item, "chance"), 10)
            if expected > 1:
                self.assertEqual(item["naechste_in"], every - days % every)
            else:
                self.assertIsNone(item["naechste_in"])
                self.assertIn("nicht mehr", fg.quirk_hint(item))
        self.assertEqual(fg.quirk_bar(2), "■■□")
        lines = fg.quirk_lines(fg.quirk_state("x", data, 10, 0, self.content))
        self.assertIn("Ticket-Chance +10 %", lines["plus"])
        self.assertIn("Routineumsatz -", lines["minus"])

    def test_wirkung_umsatz_chance_projekt(self):
        with TempDB() as db:
            game = self._founded(db)
            slow = self._hire(game, "gruendlich", 1)
            state = game.state
            info = state.quirk_of(slow)
            item = next(entry for entry in state.staff_list() if entry["id"] == slow)
            base = fg.staff_revenue(item["werte"], self.content)
            self.assertEqual(item["umsatz"],
                             int(round(base * (1 - 0.15 * info["faktor"]))))
            ticket = state.customer_tickets()[0]
            option = next(entry for entry in fg.ticket_candidates(
                state, ticket, game.firm_levels(), self.content) if entry["an"] == slow)
            plain = fg.ticket_chance(option["wert"], ticket["anforderung"], self.content)
            self.assertEqual(option["chance"], min(95, plain + 10))
            self.assertAlmostEqual(fg.staff_project_points(state, slow, 50, self.content),
                                   round(fg.project_points(50, self.content) *
                                         (1 - 0.10 * info["faktor"]), 1))
            # Whiteboard-Fan zieht das ganze Team mit (einmal)
            board = self._hire(game, "whiteboard", 2)
            self.assertAlmostEqual(fg.team_factor(game.state, [slow, board]), 1.05)
            self.assertAlmostEqual(fg.team_factor(game.state, [slow]), 1.0)

    def test_macken_beim_lernen_und_kundenzufriedenheit(self):
        with TempDB() as db:
            game = self._founded(db)
            rule = self.content["firma"]["lernen"]
            rule["halb_ab"] = 90
            collector = self._hire(game, "sammler", 1)
            template = next(item for item in self.content["firma"]["tickets"]["vorlagen"]
                            if item["thema"] == "hardware")
            other = next(item for item in self.content["firma"]["tickets"]["vorlagen"]
                         if item["thema"] not in fg.HARDWARE_TOPICS)
            before = game.state.staff_topics(collector)
            done = {"ticket": "kt1:a", "vorlage": template["id"], "an": collector,
                    "name": "X", "erfolg": True, "geld": 60}
            state = self._live_day(game, tickets=[done])
            self.assertAlmostEqual(state.staff_topics(collector)["hardware"],
                                   min(70, before["hardware"] + 2 * rule["ticket_erfolg"]))
            factor = state.quirk_of(collector)["faktor"]
            before = state.staff_topics(collector)
            state = self._live_day(game, tickets=[dict(done, ticket="kt2:a",
                                                       vorlage=other["id"])])
            self.assertAlmostEqual(state.staff_topics(collector)[other["thema"]],
                                   min(70, before[other["thema"]] + rule["ticket_erfolg"] *
                                       (1 - 0.5 * factor)))
            # Vor 0.43 (ohne firma.personal) wirkt die Macke beim Lernen nicht
            before = state.staff_topics(collector)
            state = self._day_end(game, {"tickets": [dict(done, ticket="kt3:a")]})
            self.assertAlmostEqual(state.staff_topics(collector)["hardware"],
                                   min(70, before["hardware"] + rule["ticket_erfolg"]))
            # Dokumentiert alles: Kunden zufriedener
            writer = self._hire(game, "dokumentiert", 2)
            state = game.state
            for ticket in state.customer_tickets():
                if not ticket.get("an"):
                    game.delegate(ticket["id"], writer)
                    break
            outcome = fg.ticket_outcomes(game.state, self.content)[0]
            self.assertEqual(outcome["reputation"]["kundenzufriedenheit"],
                             2 if outcome["erfolg"] else -1)

    def test_urlaub_genehmigen_und_ablehnen(self):
        with TempDB() as db:
            game = self._founded(db)
            worker = self._hire(game, "listenmensch", 1)
            rules = self.content["firma"]["personal"]
            day = game.state.day
            ask = {"art": fg.PERSONAL_VACATION, "anfrage": "urlaub:%d:x" % day, "id": worker,
                   "name": "Person1 Test", "von": day + 6, "bis": day + 9}
            state = self._live_day(game, [ask])
            decisions = state.open_decisions()
            self.assertEqual([item["art"] for item in decisions], [fg.DECISION_VACATION])
            self.assertEqual([option["id"] for option in decisions[0]["optionen"]],
                             [fg.VACATION_YES, fg.VACATION_NO])
            self.assertIn("Urlaub", fg.personal_news(state, self.content))
            self.assertFalse(state.can_end_day())
            with self.assertRaises(ValueError):
                game.end_day()
            mood = state.mood_of(worker)
            game.decide(ask["anfrage"], fg.VACATION_YES)
            state = game.state
            self.assertEqual(state.mood_of(worker), min(100, mood + rules["urlaub"]["genehmigt"]))
            self.assertEqual(state.open_decisions(), [])
            self.assertTrue(state.can_end_day())
            with self.assertRaises(ValueError):
                game.decide(ask["anfrage"], fg.VACATION_NO)
            # Im Urlaub: kein Umsatz, keine Tickets
            self.assertIsNone(state.away_of(worker, day + 5))
            self.assertEqual(state.away_of(worker, day + 6)["art"], fg.ABSENT_VACATION)
            self.assertIsNone(state.away_of(worker, day + 9))
            while game.state.day < day + 6:
                game.end_day()
                for decision in game.state.open_decisions():
                    game.decide(decision["id"], decision["optionen"][-1]["id"])
            state = game.state
            item = next(entry for entry in state.staff_list() if entry["id"] == worker)
            self.assertEqual(item["umsatz"], 0)
            self.assertIn("Im Urlaub", fg.training_text(state, item))
            self.assertNotIn(worker, [person["id"] for person in fg.firm_people(state)])
            ticket = state.customer_tickets()[0]
            option = next(entry for entry in fg.ticket_candidates(
                state, ticket, game.firm_levels(), self.content) if entry["an"] == worker)
            self.assertIn("im Urlaub", option["problem"])
            # Zweimal hintereinander abgelehnt sitzt tiefer
            for number, penalty in ((1, "abgelehnt"), (2, "abgelehnt_wieder")):
                day = game.state.day
                ask = dict(ask, anfrage="urlaub:%d:n%d" % (day, number), von=day + 6,
                           bis=day + 8)
                mood = self._live_day(game, [ask]).mood[worker]
                game.decide(ask["anfrage"], fg.VACATION_NO)
                self.assertAlmostEqual(game.state.mood[worker],
                                       max(0, mood + rules["urlaub"][penalty]))
            names = [entry["titel"] for entry in fg.journey(game.state, self.content)]
            self.assertIn("Urlaub genehmigt: Person1 Test", names)
            self.assertIn("Urlaub abgelehnt: Person1 Test", names)

    def test_konflikt_optionen(self):
        with TempDB() as db:
            game = self._founded(db)
            first = self._hire(game, "gute_laune", 1)
            second = self._hire(game, "pedantisch", 2)
            rules = self.content["firma"]["personal"]["konflikt"]

            def conflict():
                day = game.state.day
                item = {"art": fg.PERSONAL_CONFLICT, "konflikt": "konflikt:%d" % day,
                        "a": first, "b": second, "name_a": "Person1 Test",
                        "name_b": "Person2 Test", "text": "Streit."}
                state = self._live_day(game, [item])
                return state, item["konflikt"]

            state, key = conflict()
            decision = state.open_decisions()[0]
            self.assertEqual([option["id"] for option in decision["optionen"]],
                             [fg.CONFLICT_MEDIATE, fg.CONFLICT_SIDE_A, fg.CONFLICT_SIDE_B,
                              fg.CONFLICT_IGNORE])
            self.assertEqual(decision["optionen"][1]["label"], "Person1 recht geben")
            # Schlichten: beide besser gelaunt, dafuer ein Kundenticket weniger fuer dich
            limit = fg.own_ticket_limit(state, self.content)
            moods = (state.mood[first], state.mood[second])
            game.decide(key, fg.CONFLICT_MEDIATE)
            state = game.state
            self.assertEqual(fg.own_ticket_limit(state, self.content), limit - 1)
            self.assertEqual((state.mood[first], state.mood[second]),
                             (min(100, moods[0] + rules["schlichten"]),
                              min(100, moods[1] + rules["schlichten"])))
            # Partei ergreifen
            state, key = conflict()
            moods = (state.mood[first], state.mood[second])
            game.decide(key, fg.CONFLICT_SIDE_B)
            self.assertEqual(game.state.mood[second], min(100, moods[1] + rules["partei_plus"]))
            self.assertEqual(game.state.mood[first], moods[0] + rules["partei_minus"])
            # Ignorieren: beide verstimmt und ein paar Tage schwaecher
            state, key = conflict()
            game.decide(key, fg.CONFLICT_IGNORE)
            state = game.state
            form = state.staff_form(first)
            self.assertEqual(form["leistung"], rules["verstimmt_leistung"])
            self.assertIsNotNone(state.upset.get(second))
            self.assertEqual(state.staff_form(first, state.day + rules["verstimmt_tage"]),
                             {"leistung": 0, "chance": 0, "gruende": []})
            item = next(entry for entry in state.staff_list() if entry["id"] == first)
            base = fg.staff_revenue(item["werte"], self.content) * \
                (1 + state.quirk_value(first, "umsatz") / 100.0)
            self.assertEqual(item["umsatz"], int(round(base * 0.9)))
            # Ein Konflikt, der nicht am Folgetag entschieden wurde, verfaellt
            state, key = conflict()
            state = self._day_end(game, {})
            self.assertEqual(state.open_decisions(), [])
            titles = [entry["titel"] for entry in fg.journey(state, self.content)]
            self.assertIn("Streit: Person1 und Person2", titles)

    def test_krank_und_kuendigung(self):
        with TempDB() as db:
            game = self._founded(db)
            worker = self._hire(game, "nachteule", 1)
            day = game.state.day
            sick = {"art": fg.PERSONAL_SICK, "id": worker, "name": "Person1 Test",
                    "von": day + 1, "bis": day + 3}
            state = self._live_day(game, [sick])
            self.assertEqual(state.away_of(worker)["art"], fg.ABSENT_SICK)
            self.assertIn("krankgemeldet", fg.personal_news(state, self.content))
            self.assertEqual(fg.coaching_offer(state, worker, self.content)["problem"],
                             "Person1 Test ist krank.")
            # Nach dem Ausfall wieder da
            self.assertIsNone(state.away_of(worker, day + 3))
            # Stimmung zu lange im Keller: Warnung, dann Kuendigung
            state.mood[worker] = 5
            state.mood_low[worker] = 1
            events = fg.personal_events(state, state.day, self.content)
            self.assertIn(fg.PERSONAL_WARN, [item["art"] for item in events])
            state.mood_low[worker] = 3
            events = fg.personal_events(state, state.day, self.content)
            self.assertIn(fg.PERSONAL_QUIT, [item["art"] for item in events])
            quit_item = next(item for item in events if item["art"] == fg.PERSONAL_QUIT)
            state = self._live_day(game, [quit_item])
            self.assertNotIn(worker, state.staff)
            self.assertIn(worker, state.quit_staff)
            titles = [entry["titel"] for entry in fg.journey(state, self.content)]
            self.assertIn("Krank: Person1 Test", titles)
            self.assertIn("Selbst gekündigt: Person1 Test", titles)

    def test_stimmung_erholt_sich(self):
        with TempDB() as db:
            game = self._founded(db)
            worker = self._hire(game, "listenmensch", 1)
            rules = self.content["firma"]["personal"]["stimmung"]
            day = game.state.day
            ask = {"art": fg.PERSONAL_VACATION, "anfrage": "urlaub:%d:x" % day, "id": worker,
                   "name": "Person1 Test", "von": day + 6, "bis": day + 8}
            self._live_day(game, [ask])
            game.decide(ask["anfrage"], fg.VACATION_NO)
            low = game.state.mood[worker]
            state = self._live_day(game)
            self.assertEqual(state.mood[worker], low + rules["erholung"])
            # Mit guter Laune im Team geht es schneller
            self._hire(game, "gute_laune", 2)
            state = self._live_day(game)
            self.assertEqual(state.mood[worker], low + 3 * rules["erholung"])

    def test_coaching(self):
        with TempDB() as db:
            game = self._founded(db, money=60000)
            worker = self._hire(game, "gruendlich", 1)
            state = game.state
            info = state.quirk_of(worker)
            offer = fg.coaching_offer(state, worker, self.content)
            rules = self.content["firma"]["personal"]["coaching"]
            if info["stufe"] == 1:
                self.assertTrue(offer["problem"])
                return
            self.assertEqual((offer["preis"], offer["tage"], offer["problem"]),
                             (rules["preis"], rules["tage"], ""))
            money = state.money
            game.coach(worker)
            state = game.state
            self.assertEqual(state.money, money - rules["preis"])
            item = next(entry for entry in state.staff_list() if entry["id"] == worker)
            self.assertEqual(item["umsatz"], 0)
            self.assertIn("Im Coaching", fg.training_text(state, item))
            self.assertTrue(fg.coaching_offer(state, worker, self.content)["problem"])
            # Coaching zaehlt nicht als Weiterbildung (kein Preisaufschlag)
            self.assertEqual(fg.training_offer(state, worker, "hardware", self.content)["preis"],
                             self.content["firma"]["weiterbildung"]["preis"])
            for _ in range(rules["tage"]):
                game.end_day()
            self.assertEqual(game.state.quirk_of(worker)["stufe"], info["stufe"] - 1)
            titles = [entry["titel"] for entry in fg.journey(game.state, self.content)]
            self.assertIn("Coaching: Person1 Test", titles)

    def test_simulation_ueber_viele_arbeitstage(self):
        """Ab 0.43 passieren Krankheit, Urlaub und Konflikte beim Spielen von
        selbst - selten, und alle Entscheidungen lassen sich treffen."""
        with TempDB() as db:
            game = self._founded(db, money=400000)
            game.expand()
            for number, quirk in enumerate(("gute_laune", "pedantisch", "talbahn",
                                            "nachteule", "listenmensch")):
                self._hire(game, quirk, number)
            seen = {}
            for _ in range(150):
                for decision in game.state.open_decisions():
                    options = [item["id"] for item in decision["optionen"]
                               if not item["problem"]]
                    game.decide(decision["id"], options[game.state.day % len(options)])
                payload = game.end_day()
                for item in payload["firma"]["personal"]:
                    seen[item["art"]] = seen.get(item["art"], 0) + 1
            state = game.state
            self.assertTrue(seen.get(fg.PERSONAL_SICK))
            self.assertTrue(seen.get(fg.PERSONAL_VACATION))
            self.assertTrue(seen.get(fg.PERSONAL_CONFLICT))
            self.assertTrue(seen.get(fg.PERSONAL_WEAKER))
            # Kleine Story-Elemente, kein Alltag: hoechstens alle paar Tage
            self.assertLess(seen[fg.PERSONAL_CONFLICT], 150 / 8.0)
            self.assertLess(sum(seen.values()), 150)
            for staff_id in state.staff:
                self.assertTrue(0 <= state.mood_of(staff_id) <= 100)
            # PC und Handy rechnen dasselbe (gleicher Spielstand, gleiche Ereignisse)
            again = fg.GameState(db.game_events(), self.content)
            self.assertEqual(again.mood, state.mood)
            self.assertEqual(again.absences, state.absences)


class RivalitaetMarktTest(unittest.TestCase):
    """Ab 0.44: Rueckhol-Angebote, Gegenwind der Mitbewerber, Konjunktur und
    Technologietrends nach der Story."""

    setUp = FirmaTest.setUp
    _rich = FirmaTest._rich
    _founded = FirmaTest._founded
    _day_end = MitarbeiterThemenTest._day_end
    _hire = PersonalTest._hire
    _live_day = PersonalTest._live_day

    def _without_market(self):
        content = json.loads(json.dumps(self.content))
        content["firma"].pop("markt")
        content["firma"].pop("rivalitaet")
        return content

    def _day_in(self, state, phase=None, trend=False, after=0):
        """Erster Tag (ab after) in dieser Konjunkturphase bzw. mit Trend."""
        start = int(self.content["firma"]["markt"]["ab_tag"])
        for day in range(max(start, after), start + 400):
            now = fg.market_state(state, day, self.content)
            if (phase is None or now["phase"] == phase) and (not trend or now["trend"]):
                return day
        self.fail("keinen passenden Tag gefunden")

    def test_inhalte(self):
        self.assertEqual(fg._validate_firm(fg.GAME), [])
        rules = fg.GAME["firma"]
        self.assertGreaterEqual(len(rules["markt"]["trends"]["liste"]), 5)
        broken = _content()
        broken["firma"]["rivalitaet"]["rueckhol"]["texte"][0] = "{gibtsnicht}"
        broken["firma"]["markt"]["trends"]["liste"][0]["cat"] = "quatsch"
        broken["firma"]["markt"]["konjunktur"]["phasen"].pop("abschwung")
        self.assertEqual(len(fg._validate_firm(broken)), 3)

    def test_frueherer_arbeitgeber(self):
        with TempDB() as db:
            game = self._founded(db)
            seen = []
            for batch in range(6):
                for number in range(3):
                    item = fg._applicant(self.content["firma"], game.state.firm_seed, batch,
                                         number, self.content)
                    seen.append(item)
                    if item["vorher"]:
                        self.assertIn("bisher bei %s" % fg.competitor(item["vorher"])["kurz"],
                                      item["rolle"])
            former = {item["vorher"] for item in seen}
            self.assertIn("", former)            # nicht alle kommen von der Konkurrenz
            self.assertGreaterEqual(len(former), 3)
            applicant = next(item for item in fg.applicants(game.state, self.content)
                             if item["herkunft"] == "bewerbung")
            game.hire(applicant["id"])
            self.assertEqual(game.state.staff[applicant["id"]]["vorher"], applicant["vorher"])
            # Aeltere Spielstaende ohne "vorher": gleich gewuerfelt wie beim Bewerber
            old = dict(game.state.staff[applicant["id"]], id="bw0-0")
            old.pop("vorher")
            self.assertEqual(fg.former_employer(game.state, "bw0-0", old),
                             fg.former_for(game.state.firm_seed, "bw0-0", self.content))
            self.assertEqual(fg.former_employer(game.state, "x", {"herkunft": "bitweiche"}),
                             fg.BITWEICHE)

    def _recall(self, game, staff_id, rival="kranich"):
        day = game.state.day
        item = {"art": fg.PERSONAL_RECALL, "rueckhol": "rueckhol:%d:%s" % (day, staff_id),
                "id": staff_id, "name": "Person1 Test", "firma": rival, "plus": 15,
                "text": "NetzWerk Kranich will Person1 zurück."}
        return item, self._live_day(game, [item])

    def test_rueckhol_gehalt_erhoehen(self):
        with TempDB() as db:
            game = self._founded(db)
            worker = self._hire(game, "listenmensch", 1, vorher="kranich")
            salary = game.state.staff[worker]["gehalt"]
            item, state = self._recall(game, worker)
            decisions = state.open_decisions()
            self.assertEqual([entry["art"] for entry in decisions], [fg.DECISION_RECALL])
            self.assertEqual([option["id"] for option in decisions[0]["optionen"]],
                             [fg.RECALL_RAISE, fg.RECALL_BONUS, fg.RECALL_LET])
            self.assertIn("NetzWerk Kranich", decisions[0]["titel"])
            self.assertIn("Abwerbeversuch", fg.personal_news(state, self.content))
            self.assertFalse(state.can_end_day())
            mood = state.mood_of(worker)
            game.decide(item["rueckhol"], fg.RECALL_RAISE)
            state = game.state
            rule = self.content["firma"]["rivalitaet"]["rueckhol"]
            self.assertEqual(state.staff[worker]["gehalt"], fg.recall_raise(salary, rule))
            self.assertEqual(state.staff[worker]["gehalt"], int(round(salary * 1.1)))
            self.assertEqual(state.mood_of(worker), min(100, mood + rule["gehalt_stimmung"]))
            self.assertEqual(state.open_decisions(), [])
            # Doppelt (zweites Geraet) zaehlt nicht
            with self.assertRaises(ValueError):
                game.decide(item["rueckhol"], fg.RECALL_RAISE)
            self.assertEqual(state.firm_day()["gehaelter"],
                             sum(int(entry["gehalt"]) for entry in state.staff.values()))
            entry = [line for line in fg.journey(state, self.content)
                     if line["art"] == fg.EV_RECALL]
            self.assertEqual(entry[0]["titel"], "Abwerbeversuch abgewehrt: Person1 Test")

    def test_rueckhol_praemie_und_ziehen_lassen(self):
        with TempDB() as db:
            game = self._founded(db)
            worker = self._hire(game, "listenmensch", 1, vorher="cloudkontor")
            other = self._hire(game, "gruendlich", 2, vorher="byteschmiede")
            rule = self.content["firma"]["rivalitaet"]["rueckhol"]
            item, state = self._recall(game, worker, "cloudkontor")
            money = state.money
            salary = state.staff[worker]["gehalt"]
            game.decide(item["rueckhol"], fg.RECALL_BONUS)
            state = game.state
            self.assertEqual(state.money, money - salary * rule["bonus_tage"])
            self.assertEqual(state.staff[worker]["gehalt"], salary)
            # Ohne Geld geht keine Praemie
            item, state = self._recall(game, other, "byteschmiede")
            decision = state.open_decisions()[0]
            self.assertEqual(decision["person"], other)
            game.decide(item["rueckhol"], fg.RECALL_LET)
            state = game.state
            # Arbeitet heute noch mit, nach dem Feierabend ist der Platz frei
            self.assertIn(other, state.staff)
            state = self._live_day(game)
            self.assertNotIn(other, state.staff)
            self.assertIn(other, state.ever_hired)
            self.assertNotIn(other, [entry["id"] for entry in fg.applicants(state, self.content)])
            self.assertIn("wieder bei Byteschmiede", fg.personal_news(state, self.content))
            titles = [line["titel"] for line in fg.journey(state, self.content)]
            self.assertIn("Zurück zu Byteschmiede: Person1 Test", titles)

    def test_rueckhol_wuerfel_und_grenzen(self):
        with TempDB() as db:
            game = self._founded(db)
            content = self.content
            rule = content["firma"]["rivalitaet"]["rueckhol"]
            self.assertEqual(fg.recall_factor(70, rule), 1.0)
            self.assertEqual(fg.recall_factor(100, rule), 0.5)
            self.assertEqual(fg.recall_factor(10, rule), 2.0)
            day = game.state.day
            fresh = self._hire(game, "listenmensch", 1, vorher="kranich")
            none = self._hire(game, "gruendlich", 2, vorher="")
            rule["chance"] = 100
            state = game.state
            # Zu frisch eingestellt: noch kein Angebot
            self.assertEqual(fg._recall_events(state, day, list(state.staff), set(), content), [])
            later = day + rule["ab_tagen"]
            events = fg._recall_events(state, later, list(state.staff), set(), content)
            self.assertEqual([(item["id"], item["firma"]) for item in events],
                             [(fresh, "kranich")])
            self.assertIn("NetzWerk Kranich", events[0]["text"])
            self.assertEqual(fg._recall_events(state, later, list(state.staff), {fresh},
                                               content), [])
            self.assertNotEqual(fg.former_employer(state, none), "kranich")
            rule["chance"] = 0
            self.assertEqual(fg._recall_events(state, later, list(state.staff), set(), content),
                             [])

    def _offers(self, db, game, results, first_day=1):
        for number, won in enumerate(results):
            db.log_game_event(fg.EV_OFFER_WON if won else fg.EV_OFFER_LOST, json.dumps(
                {"anfrage": "anfrage:%d:1" % (first_day + number), "tag": first_day + number,
                 "gewonnen": won, "geld": 0}), "PC")
        return game.reload()

    def test_gegenwind_fest_und_gedeckelt(self):
        with TempDB() as db:
            game = self._founded(db)
            rule = self.content["firma"]["rivalitaet"]["gegenwind"]
            state = self._offers(db, game, [True] * 5 + [False] * 5)
            self.assertFalse(fg.rivalry_pressure(state, 50, self.content)["aktiv"])
            state = self._offers(db, game, [True] * 10, first_day=20)
            pressure = fg.rivalry_pressure(state, 50, self.content)
            self.assertTrue(pressure["aktiv"])
            self.assertEqual((pressure["gewonnen"], pressure["angebote"], pressure["minus"]),
                             (10, 10, rule["zuschlag_minus"]))
            # Angebote vom Tag selbst zaehlen noch nicht (Preise stehen morgens fest)
            self.assertFalse(fg.rivalry_pressure(state, 20, self.content)["aktiv"])
            # Auch 30 Siege in Folge machen es nicht staerker
            state = self._offers(db, game, [True] * 20, first_day=40)
            self.assertEqual(fg.rivalry_pressure(state, 70, self.content)["minus"],
                             rule["zuschlag_minus"])
            plain = fg.GameState(db.game_events(), self._without_market())
            for day in (70, 71, 72):
                hard = fg.inquiries_for_day(state, day, self.content)
                soft = fg.inquiries_for_day(plain, day, plain.content)
                self.assertTrue(all(item["gegenwind"] == 3 for item in hard))
                for mine, other in zip(hard, soft):
                    common = {bid["id"]: bid["zuschlag"] for bid in other["bieter"]}
                    for bid in mine["bieter"]:
                        if bid["id"] in common:
                            self.assertEqual(bid["zuschlag"],
                                             max(0, common[bid["id"]] - 3))
            self.assertIn("gezielt 3 Punkte", fg.pressure_text(
                fg.rivalry_pressure(state, 70, self.content)))
            for number in range(state.day, 72):
                db.log_game_event(fg.EV_DAY_END, json.dumps({"tag": number}), "PC")
            state = game.reload()
            events = [item[:2] for item in fg.market_events(state, self.content)]
            # Tag 9: 5 von 8 gewonnen (ab 60 %). Ab Tag 10 nur noch 5 von 9, aber der
            # Gegenwind haelt mindestens 10 Arbeitstage
            self.assertEqual(events[:2], [(9, "wettbewerb_verschaerft"),
                                          (19, "wettbewerb_entspannt")])
            self.assertTrue(fg.rivalry_pressure(state, 18, self.content)["aktiv"])
            _head, text = fg.offer_result_text(dict(
                fg.offer_result(state, hard[0], 10, {}, self.content)), self.content)
            self.assertIn("gezielt 3 Punkte günstiger", text)

    def test_gegenwind_halbiert_preisvorteil(self):
        with TempDB() as db:
            game = self._founded(db)
            state = self._offers(db, game, [True] * 20, first_day=40)
            state.reputation["kundenzufriedenheit"] = 100
            inquiry = fg.inquiries_for_day(state, 70, self.content)[0]
            self.assertEqual(inquiry["gegenwind"], 3)
            full = fg.offer_advantage(state, self.content, inquiry.get("cat"))
            self.assertGreater(full, 1)
            factor = self.content["firma"]["rivalitaet"]["gegenwind"]["vorteil_faktor"]
            self.assertEqual(factor, 0.5)
            result = fg.offer_result(state, inquiry, 10, {}, self.content)
            self.assertEqual(result["vorteil"], int(full * factor))
            self.assertEqual(result["vorteil_voll"], full)
            calm = dict(inquiry)
            calm.pop("gegenwind")
            self.assertEqual(fg.offer_result(state, calm, 10, {}, self.content)["vorteil"], full)
            _head, text = fg.offer_result_text(result, self.content)
            self.assertIn("nur %d statt %d %%" % (int(full * factor), full), text)
            self.assertIn("nur halb", fg.pressure_text(
                fg.rivalry_pressure(state, 70, self.content)))
            # Projekte und Grossauftraege tragen den Gegenwind ihres Starttags
            for project in fg.project_tenders(state, 70, self.content):
                self.assertIn("gegenwind", project)

    def test_konjunktur_wirkung(self):
        with TempDB() as db:
            game = self._founded(db)
            state = game.state
            rules = self.content["firma"]
            plain = fg.GameState(db.game_events(), self._without_market())
            start = rules["markt"]["ab_tag"]
            self.assertEqual(fg.market_state(state, start - 1, self.content)["phase"], "")
            for phase, sign in (("aufschwung", 1), ("abschwung", -1)):
                day = self._day_in(state, phase)
                info = rules["markt"]["konjunktur"]["phasen"][phase]
                items = [item for item in fg.inquiries_for_day(state, day, self.content)
                         if not item.get("trend")]
                self.assertEqual(len(items), rules["angebote"]["pro_tag"] + info["anfragen"])
                self.assertEqual(info["anfragen"] * sign, 1)
                other = fg.inquiries_for_day(plain, day, plain.content)
                for mine, theirs in zip(items, other):
                    self.assertEqual(mine["konjunktur"], phase)
                    common = {bid["id"]: bid["zuschlag"] for bid in theirs["bieter"]}
                    for bid in mine["bieter"]:
                        if bid["id"] in common and common[bid["id"]] > 3:
                            self.assertEqual(bid["zuschlag"],
                                             common[bid["id"]] + info["zuschlag"])
            # Routineumsatz: +5 % im Aufschwung
            worker = self._hire(game, "gruendlich", 1)
            state = game.state
            values = state.staff_values(worker)
            day = self._day_in(state, "aufschwung")
            normal = self._day_in(state, "neutral", after=day)
            ratio = state.staff_revenue_of(worker, values, day) / float(
                state.staff_revenue_of(worker, values, normal))
            self.assertAlmostEqual(ratio, 1.05, delta=0.02)
            # Die Phasen wechseln sich ab und haben die richtigen Laengen
            phases = fg._phase_list(state.firm_seed, 600, self.content)
            kinds = [kind for _von, _bis, kind in phases]
            self.assertEqual(kinds[0], "neutral")
            self.assertTrue(all(kinds[index] == "neutral" for index in range(0, len(kinds), 2)))
            self.assertIn("aufschwung", kinds)
            self.assertIn("abschwung", kinds)
            for von, bis, kind in phases[1:]:
                low, high = rules["markt"]["konjunktur"]["phasen"][kind]["tage"]
                self.assertTrue(low <= bis - von <= high)

    def test_trend_lebenszyklus(self):
        with TempDB() as db:
            game = self._founded(db)
            self.content["firma"]["markt"]["trends"]["chance"] = 100
            state = game.state
            day = self._day_in(state, trend=True)
            now = fg.market_state(state, day, self.content)
            trend = now["trend"]
            names = [item["name"] for item in trend["artikel"]]
            for current in range(now["trend_von"], now["trend_bis"]):
                items = fg.inquiries_for_day(state, current, self.content)
                special = [item for item in items if item.get("trend")]
                self.assertEqual(len(special), 1)
                self.assertIn(special[0]["artikel"], names)
                self.assertEqual(special[0]["cat"], trend["cat"])
                self.assertEqual(fg.inquiry_badge_text(special[0]),
                                 "Trend-Auftrag: %s" % trend["name"])
                self.assertIn(trend["satz"], special[0]["text"])
            after = fg.inquiries_for_day(state, now["trend_bis"], self.content)
            self.assertFalse(any(item.get("trend") for item in after))
            # Mitbewerber verlangen mehr (hohe Nachfrage)
            self.assertEqual(fg.market_shift(state, day, self.content, trend=True)["trend"], 4)
            # Tagebuch und Anzeige
            db.log_game_event(fg.EV_DAY_END, json.dumps({"tag": 2}), "PC")
            for number in range(3, now["trend_bis"] + 1):
                db.log_game_event(fg.EV_DAY_END, json.dumps({"tag": number}), "PC")
            state = game.reload()
            kinds = [(item[1], item[0]) for item in fg.market_events(state, self.content)]
            self.assertIn(("trend_gestartet", now["trend_von"]), kinds)
            self.assertIn(("trend_beendet", now["trend_bis"]), kinds)
            story = [line for line in fg.journey(state, self.content)
                     if line["art"] == "trend_gestartet"]
            self.assertEqual(story[-1]["gruppe"], fg.JOURNEY_STORY)
            self.assertEqual(story[-1]["titel"], "Trend: %s" % trend["name"])

    def test_zertifikat_hilft_bei_trend_auftrag(self):
        with TempDB() as db:
            game = self._founded(db)
            self.content["firma"]["markt"]["trends"]["chance"] = 100
            state = game.state
            day = next(current for current in range(101, 600)
                       if (fg.market_state(state, current, self.content)["trend"] or {})
                       .get("cat") == "systeme")
            inquiry = next(item for item in fg.inquiries_for_day(state, day, self.content)
                           if item.get("trend"))
            before = fg.offer_advantage(state, self.content, inquiry["cat"])
            db.log_game_event(fg.EV_CERT, json.dumps(
                {"zert": "windows", "tag": 1, "bis_tag": 1, "geld": 0}), "PC")
            state = game.reload()
            self.assertEqual(fg.offer_advantage(state, self.content, inquiry["cat"]), before + 3)
            self.assertEqual(fg.offer_advantage(state, self.content, None), before)

    def test_morgen_und_anzeige(self):
        with TempDB() as db:
            game = self._founded(db)
            start = self.content["firma"]["markt"]["ab_tag"]
            for number in range(game.state.day, start):
                db.log_game_event(fg.EV_DAY_END, json.dumps({"tag": number}), "PC")
            state = game.reload()
            self.assertEqual(state.day, start)
            self.assertIn(self.content["firma"]["markt"]["start_text"],
                          fg.morning_text(state.day, self.content, state))
            lines = fg.market_status(state, self.content)
            self.assertEqual(lines[0][0], "Konjunktur: Normale Lage")
            # Ohne 0.44-Inhalte bleibt alles wie vorher
            plain = fg.GameState(db.game_events(), self._without_market())
            self.assertEqual(fg.market_status(plain, plain.content), [])
            self.assertEqual(fg.market_events(plain, plain.content), [])


class WeltkarteTest(unittest.TestCase):
    """Weltkarte als Startansicht des Spiels, Aussenmodelle (ab 0.45)."""

    setUp = FirmaTest.setUp
    _rich = FirmaTest._rich
    _founded = FirmaTest._founded

    @staticmethod
    def _ids(state, content=None):
        return [item["id"] for item in fg.map_places(state, content)]

    def test_inhalte(self):
        self.assertEqual(fg._validate_world(fg.GAME), [])
        broken = _content()
        broken["orte"]["orte"][0]["modell"] = "gibtsnicht"
        broken["orte"]["orte"][1]["ansicht"] = "irgendwo"
        broken["orte"]["orte"][2]["frei"] = {"zauberei": True}
        broken["orte"]["orte"][3]["x"] = 999
        problems = "\n".join(fg._validate_world(broken))
        for text in ("unbekanntes Modell 'gibtsnicht'", "unbekannte Ansicht 'irgendwo'",
                     "unbekannte Freischaltung 'zauberei'", "ausserhalb der Karte"):
            self.assertIn(text, problems)
        # Jeder Kundenort muss auf der Karte stehen
        broken = _content()
        broken["orte"]["orte"] = [item for item in broken["orte"]["orte"]
                                  if item["id"] != "birkenhain"]
        self.assertTrue(any("birkenhain" in line for line in fg._validate_world(broken)))

    def test_freischaltung_nach_tagen(self):
        with TempDB() as db:
            game = fg.Game(db, "PC")
            game.set_profile("Nico", {})
            ids = self._ids(game.state)
            self.assertIn("zuhause", ids)
            self.assertIn("bitweiche", ids)
            self.assertNotIn("gewerbehof", ids)
            self.assertNotIn("filiale", ids)
            for item in fg.map_places(game.state):
                if item["ansicht"].startswith("kunde:"):
                    place = fg.customer_place(item["ansicht"].split(":", 1)[1])
                    self.assertLessEqual(place.get("ab_tag", 1), game.state.day)
            hidden = [place["id"] for place in fg.customer_places()
                      if place["id"] not in ids]
            self.assertTrue(hidden, "Mindestens ein Kundenort kommt erst spaeter")
            last = max(int(place.get("ab_tag", 1)) for place in fg.customer_places())
            for day in range(1, last):
                db.log_game_event(fg.EV_DAY_END, json.dumps({"tag": day}), "PC")
            state = game.reload()
            ids = self._ids(state)
            for place in fg.customer_places():
                self.assertIn(place["id"], ids)
            new = [item["id"] for item in fg.map_places(state) if item["neu"]]
            self.assertTrue(set(new) <= set(hidden))

    def test_gruendung_aendert_karte(self):
        with TempDB() as db:
            game = self._rich(db)
            places = {item["id"]: item for item in fg.map_places(game.state, self.content)}
            self.assertEqual(places["gewerbehof"]["hinweis"], "Zu vermieten")
            self.assertEqual(places["gewerbehof"]["ansicht"], "firma")
            self.assertEqual(places["bitweiche"]["ansicht"], "buero")
            game.found_firm("Nico IT-Service")
            places = {item["id"]: item for item in fg.map_places(game.state, self.content)}
            self.assertEqual(places["gewerbehof"]["name"], "Nico IT-Service")
            self.assertEqual(places["gewerbehof"]["ansicht"], "buero")
            self.assertEqual(places["gewerbehof"]["hinweis"], "")
            self.assertEqual(places["bitweiche"]["rolle"], "mitbewerber")
            self.assertTrue(places["bitweiche"]["ansicht"].startswith("mitbewerber:"))
            title, text = fg.rival_info(game.state, "bitweiche", self.content)
            self.assertIn("Bitweiche", title)
            self.assertIn("noch kein Angebot", text)
            self.assertEqual(fg.site_place_id(fg.SITE_OFFICE, game.state), "gewerbehof")
            self.assertEqual(fg.site_place_id(fg.SITE_HOME, game.state), "zuhause")

    def test_treffer_auf_gebaeude_und_schild(self):
        with TempDB() as db:
            game = self._founded(db, money=300000)
            state = game.state
            for item in fg.map_places(state, self.content):
                cx, cy = item["schild"]
                self.assertEqual(fg.place_at(cx, cy, state, self.content, scale=30)["id"],
                                 item["id"])
                x1, y1, x2, y2 = item["box"]
                self.assertIsNotNone(fg.place_at((x1 + x2) / 2, (y1 + y2) / 2, state,
                                                 self.content, scale=30))
            self.assertIsNone(fg.place_at(-5, -5, state, self.content))

    def test_zeichnung_und_vorschau(self):
        with TempDB() as db:
            game = self._founded(db, money=300000)
            state = game.state
            shapes = fg.world_shapes(state, self.content)
            kinds = {shape["k"] for shape in shapes}
            self.assertTrue({"rect", "poly", "text"} <= kinds)
            names = [shape["text"] for shape in shapes if shape["k"] == "text"
                     and shape["role"] == "ort"]
            self.assertIn("Nico IT-Service", names)
            for item in fg.map_places(state, self.content):
                preview, width, height = fg.place_preview(item["id"], state, self.content)
                self.assertTrue(preview)
                self.assertGreater(width, 0)
                self.assertGreater(height, 0)
                xs = [shape["x"] for shape in preview if "x" in shape]
                self.assertGreaterEqual(min(xs), -0.01)

    def test_modelle_je_wohnung_und_stufe(self):
        import types
        base = {"firm": None, "branch": None, "rooms": {}, "solved": set()}
        variants = set()
        for home in fg.GAME["wohnungen"]["wohnungen"]:
            state = types.SimpleNamespace(home_id=home["id"], **base)
            parts = fg.model_parts("wohnung", state)
            self.assertTrue(parts)
            variants.add(json.dumps(parts, sort_keys=True))
        self.assertEqual(len(variants), len(fg.GAME["wohnungen"]["wohnungen"]))
        counts = []
        for number in range(1, 6):
            state = types.SimpleNamespace(home_id="x", firm={"stufe": number}, branch=None,
                                          rooms={}, solved=set())
            counts.append(len(fg.model_parts("gewerbehof", state)))
        self.assertEqual(counts, sorted(counts))
        self.assertLess(counts[0], counts[-1])
        # Serverraum auf dem Dach nur, wenn gebaut
        state = types.SimpleNamespace(home_id="x", firm={"stufe": 5}, branch=None,
                                      rooms={"serverraum": {}}, solved=set())
        self.assertGreater(len(fg.model_parts("gewerbehof", state)), counts[-1])

    def test_liste_statt_karte_je_geraet(self):
        import fisi_update
        stored = {}
        original = fisi_update.load_settings, fisi_update.save_settings
        fisi_update.load_settings = lambda: dict(stored)
        fisi_update.save_settings = lambda settings: stored.update(settings) or True
        try:
            self.assertFalse(fg.map_list_mode())
            fg.set_map_list_mode(True)
            self.assertTrue(fg.map_list_mode())
            self.assertEqual(stored, {fg.MAP_LIST_SETTING: True})
            fg.set_map_list_mode(False)
            self.assertFalse(fg.map_list_mode())
        finally:
            fisi_update.load_settings, fisi_update.save_settings = original


class FilialeTest(unittest.TestCase):
    """Zweiter Standort: Filiale in Lindenau (ab 0.45)."""

    setUp = FirmaTest.setUp
    _rich = FirmaTest._rich
    _founded = FirmaTest._founded

    def _staff(self, db, game, count):
        state = game.state
        template = fg.applicants(state, self.content)[0]
        for number in range(count):
            data = {key: copy.deepcopy(template[key]) for key in
                    ("name", "aussehen", "werte", "themen", "gehalt", "herkunft",
                     "schwerpunkt", "rolle")}
            data.update(id="test%d-%d" % (len(state.staff), number), tag=state.day,
                        name="Person %d" % (len(state.staff) + number))
            db.log_game_event(fg.EV_HIRED, json.dumps(data), "PC")
        return game.reload()

    def _ready(self, db, money=400000):
        game = self._founded(db, money=money)
        while game.state.firm["stufe"] < 4:
            game.expand()
        self._staff(db, game, 6)
        start = game.state.day
        for day in range(start, start + 40):
            db.log_game_event(fg.EV_DAY_END, json.dumps({"tag": day, "firma": {}}), "PC")
        game.reload()
        return game

    def test_inhalte(self):
        self.assertEqual(fg._validate_branch(fg.GAME["firma"]), [])
        rules = fg.branch_rules()
        self.assertEqual([len(stage["plaetze"]) for stage in rules["stufen"]], [4, 7])
        self.assertEqual(rules["voraussetzung"], {"stufe": 4, "mitarbeiter": 6,
                                                  "firmentage": 40})
        broken = copy.deepcopy(fg.GAME["firma"])
        broken["filiale"]["naehe"]["orte"] = ["nirgendwo"]
        broken["filiale"]["stufen"][1]["plaetze"] = broken["filiale"]["stufen"][0]["plaetze"]
        self.assertEqual(len(fg._validate_branch(broken)), 2)

    def test_voraussetzung(self):
        with TempDB() as db:
            game = self._founded(db, money=400000)
            self.assertEqual(len(fg.branch_missing(game.state, self.content)), 3)
            self.assertNotIn("filiale", [item["id"] for item in
                                         fg.map_places(game.state, self.content)])
            with self.assertRaises(ValueError):
                game.open_branch("Filiale Lindenau")
        with TempDB() as db:
            game = self._ready(db)
            self.assertEqual(fg.branch_missing(game.state, self.content), [])
            place = fg.place_by_id("filiale", game.state, self.content)
            self.assertEqual(place["hinweis"], "Zu vermieten")
            self.assertEqual(place["ansicht"], "firma:gebaeude")
            self.assertEqual(place["name"], "Filiale Lindenau")

    def test_eroeffnen_mit_eigenem_namen(self):
        with TempDB() as db:
            game = self._ready(db)
            state = game.state
            money, costs, office = state.money, state.firm_costs(), state.capacity
            with self.assertRaises(ValueError):
                game.open_branch("   ")
            payload = game.open_branch("  Meine   Filiale ")
            self.assertEqual(payload["name"], "Meine Filiale")
            state = game.state
            stage = fg.branch_stage(1)
            self.assertEqual(state.money, money - stage["preis"])
            self.assertEqual(state.firm_costs(), costs + stage["nebenkosten"])
            self.assertEqual(state.capacity, office + 4)
            self.assertEqual(state.site_capacity(fg.SITE_BRANCH), 4)
            place = fg.place_by_id("filiale", state, self.content)
            self.assertEqual((place["name"], place["ansicht"], place["hinweis"]),
                             ("Meine Filiale", "filiale", ""))
            self.assertTrue(place["neu"])
            self.assertEqual(fg.site_name(fg.SITE_BRANCH, state=state), "Meine Filiale")
            with self.assertRaises(ValueError):
                game.open_branch("Noch eine")
            kinds = [entry["art"] for entry in fg.journey(state, self.content)]
            self.assertIn("filiale", kinds)

    def test_einstellen_und_versetzen(self):
        with TempDB() as db:
            game = self._ready(db)
            game.open_branch("Filiale Lindenau")
            office = game.state.site_capacity(fg.SITE_OFFICE)
            self._staff(db, game, office - len(game.state.staff))
            self.assertEqual(game.state.site_free(fg.SITE_OFFICE), 0)
            applicant = fg.applicants(game.state, self.content)[0]["id"]
            game.hire(applicant)
            state = game.state
            self.assertEqual(state.site_of(applicant), fg.SITE_BRANCH)
            self.assertEqual(len(state.site_staff(fg.SITE_BRANCH)), 1)
            sites = {item["id"]: item["standort"] for item in state.staff_list()}
            self.assertEqual(sites[applicant], fg.SITE_BRANCH)
            with self.assertRaises(ValueError):
                game.transfer(applicant, fg.SITE_OFFICE)      # Gewerbehof voll
            with self.assertRaises(ValueError):
                game.transfer(applicant, fg.SITE_BRANCH)      # schon dort
            other = state.site_staff(fg.SITE_OFFICE)[0]
            other = other if isinstance(other, str) else other["id"]
            game.transfer(other, fg.SITE_BRANCH)
            game.transfer(applicant, fg.SITE_OFFICE)
            state = game.state
            self.assertEqual(state.site_of(other), fg.SITE_BRANCH)
            self.assertEqual(state.site_of(applicant), fg.SITE_OFFICE)
            kinds = [entry["art"] for entry in fg.journey(state, self.content)]
            self.assertIn("versetzung", kinds)
            site = fg.site_content(fg.SITE_BRANCH, state, self.content)
            self.assertEqual([person["id"] for person in site["kollegen"]], [other])
            game.fire(other)
            self.assertEqual(game.state.site_staff(fg.SITE_BRANCH), [])

    def test_ausbau(self):
        with TempDB() as db:
            game = self._ready(db)
            with self.assertRaises(ValueError):
                game.expand_branch()
            game.open_branch("Filiale Lindenau")
            game.expand_branch()
            self.assertEqual(game.state.branch["stufe"], 2)
            self.assertEqual(game.state.site_capacity(fg.SITE_BRANCH), 7)
            self.assertIsNone(fg.branch_status(game.state, self.content)["naechste"])
            with self.assertRaises(ValueError):
                game.expand_branch()

    def test_doppelt_zaehlt_einmal(self):
        with TempDB() as pc, TempDB() as handy:
            game = self._ready(pc)
            fisi_sync.merge_into_local(handy, fisi_sync.export_local(pc))
            other = fg.Game(handy, "Handy", self.content)
            money = game.state.money
            game.open_branch("Vom PC")
            other.open_branch("Vom Handy")
            fisi_sync.merge_into_local(handy, fisi_sync.export_local(pc))
            state = other.reload()
            self.assertEqual(state.money, money - fg.branch_stage(1)["preis"])
            self.assertEqual(state.branch["stufe"], 1)

    def test_mehr_anfragen_und_naehe(self):
        with TempDB() as db:
            game = self._ready(db)
            state = game.state
            before = len(fg.inquiries_for_day(state, state.day, self.content))
            near = [item["id"] for item in self.content["firma"]["kunden"]
                    if item.get("ort") == "lindenau"]
            self.assertTrue(near)
            self.assertEqual(fg.branch_nearness(state, near[0], self.content), 0)
            game.open_branch("Filiale Lindenau")
            state = game.state
            after = len(fg.inquiries_for_day(state, state.day, self.content))
            self.assertEqual(after, before + 1)
            self.assertEqual(fg.branch_nearness(state, near[0], self.content), 3)
            others = [item["id"] for item in self.content["firma"]["kunden"]
                      if item.get("ort") != "lindenau"]
            self.assertEqual(fg.branch_nearness(state, others[0], self.content), 0)


class ErfolgeTest(unittest.TestCase):
    """Erfolge, Bestenliste und Meilenstein-Moment (ab 0.46)."""

    setUp = FirmaTest.setUp
    _rich = FirmaTest._rich
    _founded = FirmaTest._founded
    OLD = "2026-01-01 00:00:00"

    @staticmethod
    def _events(db, kind):
        return [row[2] for row in db.game_events() if row[1] == kind]

    def _age(self, db, game):
        """Den laufenden Durchgang zeitlich zuruecklegen - Zeitstempel sind
        sekundengenau, zwei Durchgaenge brauchen verschiedene Startzeiten."""
        db._execute("UPDATE spiel_ereignisse SET timestamp = ?", (self.OLD,), commit=True)
        db._execute("UPDATE spiel_bestenliste SET timestamp = ?, durchgang = ?",
                    (self.OLD, self.OLD), commit=True)
        return game.reload()

    def _payday(self, db, game, money):
        """Geld verdienen und Feierabend machen (der Kontostand zaehlt danach)."""
        state = game.state
        db.log_game_event(fg.EV_SOLVED, json.dumps(
            {"aufgabe": "anderes", "tag": state.day, "richtig": True, "geld": money,
             "reputation": {}}), "PC")
        db.log_game_event(fg.EV_DAY_END, json.dumps({"tag": state.day}), "PC")
        game.reload()
        return game.check_achievements(day_end=True)

    def test_inhalte(self):
        self.assertEqual(fg._validate_achievements(fg.GAME), [])
        rules = fg.achievement_rules()
        stages = [stage for rule in rules["erfolge"] for stage in rule["stufen"]]
        # Ab 0.47: zwei Story-Abzeichen dazu (je eine Stufe mit Moment)
        self.assertEqual(len(rules["erfolge"]), 34)
        self.assertEqual(len(stages), 74)
        self.assertEqual(len([stage for stage in stages if stage.get("moment")]), 27)
        self.assertEqual(len(rules["bestwerte"]), 14)
        for rule in rules["erfolge"]:
            self.assertIn(rule["bild"], fg.BADGE_PICTURES)
            self.assertIn(rule["wert"], fg.RUN_METRICS)
        broken = copy.deepcopy(fg.GAME)
        items = broken["erfolge"]["erfolge"]
        items[1]["id"] = items[0]["id"]
        items[2]["stufen"] = list(reversed(items[2]["stufen"]))
        items[3]["wert"] = "gibt_es_nicht"
        self.assertGreaterEqual(len(fg._validate_achievements(broken)), 3)

    def test_freischaltung_mit_ereignis(self):
        with TempDB() as db:
            game = fg.Game(db, "PC", self.content)
            game.set_profile("Nico", {})
            self.assertIn(("erster_tag", 1), game.state.achievements)
            logged = self._events(db, fg.EV_ACHIEVEMENT)
            self.assertEqual([(item["erfolg"], item["stufe"]) for item in logged],
                             [("erster_tag", 1)])
            self.assertFalse(logged[0]["nachgetragen"])
            infos = game.take_unlocks()
            self.assertEqual([info["erfolg"] for info in infos], ["erster_tag"])
            self.assertFalse(infos[0]["moment"])
            self.assertEqual(infos[0]["hinweis"], "Abzeichen: Erster Arbeitstag · Bronze")
            self.assertEqual(game.take_unlocks(), [])
            # Nichts doppelt: erneutes Pruefen schreibt kein weiteres Ereignis
            game.check_achievements()
            self.assertEqual(len(self._events(db, fg.EV_ACHIEVEMENT)), 1)

    def test_meilenstein_moment_bei_gruendung(self):
        with TempDB() as db:
            game = self._rich(db, money=30000)
            game.take_unlocks()
            game.found_firm("Nico IT-Service")
            infos = game.take_unlocks()
            self.assertTrue(infos[0]["moment"], "Momente kommen zuerst")
            firm = [info for info in infos if info["erfolg"] == "eigene_firma"][0]
            self.assertEqual(firm["tier"], "gold")
            self.assertIn("Nico IT-Service ist gegründet", firm["text"])
            self.assertEqual(firm["ort"], "gewerbehof")
            # Ohne frueheren Durchgang kein "Zum ersten Mal" und kein Bestwert
            self.assertFalse(firm["erstes_mal"])
            self.assertEqual(firm["bestwert"], "")
            shapes, width, height = fg.moment_shapes(firm, game.state)
            self.assertTrue(shapes)
            self.assertEqual((width, height), (12.0, 6.0))

    def test_nur_hoechste_stufe_und_kleine_ohne_moment(self):
        with TempDB() as db:
            game = fg.Game(db, "PC", self.content)
            game.set_profile("Nico", {})
            game.take_unlocks()
            self._payday(db, game, 150000)
            infos = game.take_unlocks()
            money = [info for info in infos if info["erfolg"] == "kontostand"]
            self.assertEqual(len(money), 1, "je Abzeichen nur die hoechste neue Stufe")
            self.assertEqual((money[0]["stufe"], money[0]["tier"]), (2, "silber"))
            self.assertTrue(money[0]["moment"])
            self.assertIn(("kontostand", 1), game.state.achievements)

    def test_alter_spielstand_still_nachgetragen(self):
        with TempDB() as db:
            # Spielstand von vor 0.46: Ereignisse ohne jede Abzeichen-Pruefung
            db.log_game_event(fg.EV_PROFILE, json.dumps({"name": "Nico", "aussehen": {}}),
                              "PC")
            db.log_game_event(fg.EV_SOLVED, json.dumps(
                {"aufgabe": "anderes", "tag": 1, "richtig": True, "geld": 30000,
                 "reputation": {}}), "PC")
            db.log_game_event(fg.EV_DAY_END, json.dumps({"tag": 1}), "PC")
            game = fg.Game(db, "PC", self.content)
            game.check_achievements()
            logged = self._events(db, fg.EV_ACHIEVEMENT)
            self.assertIn(("kontostand", 1), [(item["erfolg"], item["stufe"])
                                              for item in logged])
            self.assertTrue(all(item["nachgetragen"] for item in logged))
            self.assertEqual(game.take_unlocks(), [], "nachgetragen = ohne Moment")
            # Nachgetragene Momente stehen nicht im Tagebuch
            self.assertFalse([entry for entry in fg.journey(game.state)
                              if entry["titel"].startswith("Abzeichen")])

    def test_bestwerte_ueber_zwei_durchgaenge(self):
        with TempDB() as db:
            game = fg.Game(db, "PC", self.content)
            game.set_profile("Erster", {})
            self._payday(db, game, 120000)
            self._age(db, game)
            game.reset()
            self.assertIsNone(game.state.profile)
            # Die Bestenliste uebersteht das Zuruecksetzen
            self.assertEqual(fg.record_runs(game.records()), [self.OLD])
            game.set_profile("Zweiter", {})
            game.take_unlocks()
            self._payday(db, game, 40000)
            board = fg.record_board(game.records(), game.state)
            self.assertEqual(board["durchgaenge"], 2)
            money = [item for item in board["werte"] if item["id"] == "kontostand"][0]
            self.assertEqual(money["wert"], 120000)
            self.assertEqual(money["durchgang"], 1)
            self.assertEqual(money["aktuell"], 40000)
            self.assertFalse(money["rekord"])
            self.assertIn("1. Durchgang", fg.record_detail(money, 2))
            # Im zweiten Durchgang: Bronze wieder erreicht, aber nicht zum ersten Mal
            game.unlocked = []
            info = fg.unlock_info(game.state, fg.achievement_rule("kontostand"), 1,
                                  game.records())
            self.assertFalse(info["erstes_mal"])
            # Die fruehere Stufe steht in der Uebersicht ("früher: Silber")
            items = fg.achievement_overview(game.state, None, game.records())
            item = [entry for entry in items if entry["id"] == "kontostand"][0]
            self.assertIn("früher: Silber", fg.badge_status(item)[0])

    def test_moment_in_jedem_durchgang_mit_neuem_bestwert(self):
        with TempDB() as db:
            game = fg.Game(db, "PC", self.content)
            game.set_profile("Erster", {})
            self._payday(db, game, 110000)
            self._age(db, game)
            game.reset()
            game.set_profile("Zweiter", {})
            game.take_unlocks()
            self._payday(db, game, 130000)
            infos = [info for info in game.take_unlocks() if info["erfolg"] == "kontostand"]
            self.assertEqual(len(infos), 1)
            self.assertTrue(infos[0]["moment"], "Moment auch im zweiten Durchgang")
            self.assertFalse(infos[0]["erstes_mal"])
            self.assertEqual(infos[0]["bestwert"], "Neuer Bestwert! Bisher: 110.000 €")

    def test_bestwert_wird_gedrosselt_und_beim_reset_vollstaendig(self):
        with TempDB() as db:
            game = fg.Game(db, "PC", self.content)
            game.set_profile("Nico", {})
            self._payday(db, game, 30000)
            first = [row for row in game.records()
                     if row[2] == fg.REC_BEST and row[3] == "kontostand"]
            self.assertEqual([row[4] for row in first], [30000])
            # Besser, aber keine RECORD_EVERY Tage spaeter: noch keine neue Zeile
            self._payday(db, game, 5000)
            rows = [row for row in game.records()
                    if row[2] == fg.REC_BEST and row[3] == "kontostand"]
            self.assertEqual(len(rows), 1)
            # Vor dem Zuruecksetzen wird der Endstand festgehalten
            game.reset()
            rows = [row[4] for row in game.records()
                    if row[2] == fg.REC_BEST and row[3] == "kontostand"]
            self.assertEqual(max(rows), 35000)

    def test_bleibt_bei_lern_reset_und_loeschen_nur_per_knopf(self):
        with TempDB() as db:
            game = fg.Game(db, "PC", self.content)
            game.set_profile("Nico", {})
            self._payday(db, game, 30000)
            before = len(game.records())
            self.assertTrue(before)
            db.reset_all()
            self.assertEqual(len(game.records()), before)
            game.reset()
            self.assertGreaterEqual(len(game.records()), before)
            self.assertTrue(game.reset_records())
            self.assertEqual(game.records(), [], "ohne Spielfigur bleibt sie leer")
            game.set_profile("Neu", {})
            runs = fg.record_runs(game.records())
            self.assertEqual(runs, [game.state.first_event])

    def test_bestenliste_wird_abgeglichen(self):
        with TempDB() as pc, TempDB() as handy:
            game = fg.Game(pc, "PC", self.content)
            game.set_profile("Nico", {})
            self._payday(pc, game, 30000)
            rows = len(pc.records())
            fisi_sync.merge_into_local(handy, fisi_sync.export_local(pc))
            self.assertEqual(len(handy.records()), rows)
            # Doppelter Abgleich zaehlt nichts doppelt
            fisi_sync.merge_into_local(handy, fisi_sync.export_local(pc))
            self.assertEqual(len(handy.records()), rows)
            # Auch nach "Spielstand zuruecksetzen" am Handy bleibt sie auf beiden Seiten
            for db in (pc, handy):
                db._execute("UPDATE spiel_ereignisse SET timestamp = ?", (self.OLD,),
                            commit=True)
                db._execute("UPDATE spiel_bestenliste SET timestamp = ?", (self.OLD,),
                            commit=True)
            fg.Game(handy, "Handy", self.content).reset()
            fisi_sync.merge_into_local(pc, fisi_sync.export_local(handy))
            self.assertIsNone(fg.Game(pc, "PC", self.content).state.profile)
            self.assertGreaterEqual(len(pc.records()), rows)
            # "Bestenliste löschen" am Handy loescht sie beim Abgleich auch am PC
            handy.reset_records()
            fisi_sync.merge_into_local(pc, fisi_sync.export_local(handy))
            self.assertEqual(pc.records(), [])
            # ... und alte Zeilen vom PC kommen nicht zurueck
            fisi_sync.merge_into_local(handy, fisi_sync.export_local(pc))
            self.assertEqual(handy.records(), [])


class SchwierigkeitTest(unittest.TestCase):
    """Schwierigkeitsgrad Einfach/Normal (ab 0.47): beim Spielstart gewaehlt,
    fest fuer den Durchgang; Einfach macht die Wirtschaft verzeihender."""

    setUp = FirmaTest.setUp
    _day_end = MitarbeiterThemenTest._day_end
    _hire = PersonalTest._hire
    _live_day = PersonalTest._live_day
    _days = KrediteTest._days
    _spend = KrediteTest._spend
    _offers = RivalitaetMarktTest._offers

    def _rich(self, db, money=30000, done=True, level=fg.DIFF_EASY):
        game = fg.Game(db, "PC", self.content)
        game.set_profile("Nico", {}, level)
        db.log_game_event(fg.EV_SOLVED, json.dumps(
            {"aufgabe": self.task["id"] if done else "anderes", "tag": 1, "richtig": True,
             "geld": money, "reputation": {key: 60 for key in fg.AXIS_KEYS}}), "PC")
        game.reload()
        return game

    def _founded(self, db, money=30000, level=fg.DIFF_EASY):
        game = self._rich(db, money, level=level)
        game.found_firm("Nico IT-Service")
        return game

    def _levels(self, db):
        return [row[2] for row in db.game_events() if row[1] == fg.EV_DIFFICULTY]

    def test_inhalte(self):
        rules = fg.difficulty_rules()
        self.assertEqual([key for key, _name, _text in fg.difficulty_levels()],
                         [fg.DIFF_EASY, fg.DIFF_NORMAL])
        self.assertEqual(fg.difficulty_default(), fg.DIFF_NORMAL)
        for key in ("umsatzsteuer", "mahnstufen", "abschwung", "gegenwind", "rueckhol",
                    "kuendigung"):
            self.assertIs(rules["einfach"][key], False)
        # Normal: immer der Normal-Wert, egal was in "einfach" steht
        self.assertEqual(fg.difficulty_rule(fg.DIFF_NORMAL, "krankheit_faktor"), 1.0)
        self.assertEqual(fg.difficulty_rule(fg.DIFF_EASY, "krankheit_faktor"), 0.5)
        self.assertTrue(fg.difficulty_rule(fg.DIFF_NORMAL, "umsatzsteuer", True))

    def test_wahl_beim_start_und_fest(self):
        with TempDB() as db:
            game = fg.Game(db, "PC", self.content)
            self.assertIn("beim Spielstart", fg.difficulty_options_text(game.state))
            game.set_profile("Nico", {}, fg.DIFF_EASY)
            self.assertTrue(game.state.easy)
            self.assertEqual(game.state.level, fg.DIFF_EASY)
            self.assertEqual(fg.difficulty_badge_text(game.state), "Schwierigkeitsgrad: Einfach")
            self.assertIn("Spielstand zurücksetzen", fg.difficulty_options_text(game.state))
            # Aussehen aendern aendert den Schwierigkeitsgrad nicht
            game.set_profile("Nico", {"extra": "brille"}, fg.DIFF_NORMAL)
            self.assertEqual(game.state.level, fg.DIFF_EASY)
            self.assertEqual(len(self._levels(db)), 1)
            # Nach dem Zuruecksetzen wird neu gewaehlt
            game.reset()
            self.assertIsNone(game.state.difficulty)
            game.set_profile("Nico", {}, fg.DIFF_NORMAL)
            self.assertEqual(game.state.level, fg.DIFF_NORMAL)
            self.assertFalse(game.state.easy)

    def test_alter_spielstand_ist_normal(self):
        with TempDB() as db:
            db.log_game_event(fg.EV_PROFILE, json.dumps({"name": "Nico", "aussehen": {}}), "PC")
            game = fg.Game(db, "PC", self.content)
            self.assertIsNone(game.state.difficulty)
            self.assertEqual(game.state.level, fg.DIFF_NORMAL)
            # Das Profil spaeter aendern legt keinen Schwierigkeitsgrad nach
            game.set_profile("Nico", {}, fg.DIFF_EASY)
            self.assertEqual(game.state.level, fg.DIFF_NORMAL)
            self.assertEqual(self._levels(db), [])

    def test_abgleich(self):
        with TempDB() as pc, TempDB() as handy:
            fg.Game(pc, "PC", self.content).set_profile("Nico", {}, fg.DIFF_EASY)
            fisi_sync.merge_into_local(handy, fisi_sync.export_local(pc))
            self.assertTrue(fg.Game(handy, "Handy", self.content).state.easy)
            # Auf beiden Geraeten gleichzeitig gewaehlt: das erste gilt
            handy.log_game_event(fg.EV_DIFFICULTY, json.dumps({"stufe": fg.DIFF_NORMAL}),
                                 "Handy")
            self.assertTrue(fg.Game(handy, "Handy", self.content).state.easy)

    def test_umsatzsteuer_entfaellt(self):
        with TempDB() as easy_db, TempDB() as normal_db:
            easy = self._founded(easy_db)
            normal = self._founded(normal_db, level=fg.DIFF_NORMAL)
            self.assertNotIn("ust", easy.end_day()["firma"])
            self.assertEqual(normal.end_day()["firma"]["ust"], 1)
            self.assertFalse(fg.tax_active(easy.state))
            self.assertTrue(fg.tax_active(normal.state))
            # Einnahmen bleiben ganz auf dem Konto
            before = easy.state.money
            self._days(easy, 12, revenue=1190)
            self.assertEqual(easy.state.money, before + 12 * 1190)
            self.assertEqual(easy.state.tax_log, [])

    def test_keine_mahnstufe(self):
        with TempDB() as db:
            game = self._founded(db)
            self._days(game, 10)
            game.take_loan(0, 0, "kurz")
            reliability = game.state.reputation["zuverlaessigkeit"]
            self._spend(game, game.state.money + 1000)       # Konto leer
            end = game.end_day()
            state = game.state
            loan = state.running_loans()[0]
            self.assertEqual(state.dunning, 0)
            self.assertEqual(loan["raten"], 0)
            self.assertEqual(loan["ausfaelle"], 1)
            self.assertEqual(loan["gebuehren"], 0)
            self.assertEqual(state.reputation["zuverlaessigkeit"], reliability)
            text = fg.firm_day_text(end["firma"])
            self.assertIn("ausgesetzt", text)
            self.assertNotIn("Mahnstufe", text)
            self.assertFalse(fg.dunning_text(state, self.content))
            titles = [entry["titel"] for entry in fg.journey(state, self.content)]
            self.assertIn("Kreditrate ausgesetzt", titles)
            # Weitere geplatzte Raten: immer noch keine Mahnstufe, kein Zinsaufschlag
            self._days(game, 2, revenue=0)
            self.assertEqual(game.state.dunning, 0)
            self.assertFalse(fg.credit_check(game.state, self.content)["sperre"])

    def test_personal_verzeihender(self):
        with TempDB() as db:
            game = self._founded(db)
            worker = self._hire(game, "listenmensch", 1, vorher="kranich")
            state = self._live_day(game)
            # Niemand kuendigt, auch bei dauerhaft schlechter Stimmung
            state.mood[worker] = 5
            state.mood_low[worker] = 5
            arts = [item["art"] for item in fg.personal_events(state, state.day, self.content)]
            self.assertNotIn(fg.PERSONAL_QUIT, arts)
            self.assertNotIn(fg.PERSONAL_WARN, arts)
            # Keine Rueckhol-Angebote, auch bei sicherer Chance
            self.content["firma"]["rivalitaet"]["rueckhol"]["chance"] = 100
            later = state.day + 100
            self.assertEqual(fg._recall_events(state, later, list(state.staff), set(),
                                               self.content), [])
            # Urlaub abgelehnt kostet nur die Haelfte
            rules = self.content["firma"]["personal"]
            state.mood[worker] = 70
            day = state.day
            ask = {"art": fg.PERSONAL_VACATION, "anfrage": "urlaub:%d:x" % day, "id": worker,
                   "name": "Person1 Test", "von": day + 6, "bis": day + 9}
            state = self._live_day(game, [ask])
            mood = state.mood_of(worker)
            game.decide(ask["anfrage"], fg.VACATION_NO)
            self.assertEqual(game.state.mood_of(worker),
                             mood + round(rules["urlaub"]["abgelehnt"] * 0.5))

    def test_krankheit_und_konflikte_seltener(self):
        with TempDB() as easy_db, TempDB() as normal_db:
            counts = {}
            for db, level in ((easy_db, fg.DIFF_EASY), (normal_db, fg.DIFF_NORMAL)):
                game = self._founded(db, level=level)
                for number in range(4):
                    self._hire(game, "gruendlich", number)
                state = game.state
                sick = conflicts = 0
                for day in range(state.day, state.day + 600):
                    arts = [item["art"] for item in
                            fg.personal_events(state, day, self.content)]
                    sick += arts.count(fg.PERSONAL_SICK)
                    conflicts += arts.count(fg.PERSONAL_CONFLICT)
                counts[level] = (sick, conflicts)
            self.assertLess(counts[fg.DIFF_EASY][0], counts[fg.DIFF_NORMAL][0])
            self.assertLess(counts[fg.DIFF_EASY][1], counts[fg.DIFF_NORMAL][1])

    def test_macken_schwaeche_halb(self):
        with TempDB() as easy_db, TempDB() as normal_db:
            easy = self._founded(easy_db)
            normal = self._founded(normal_db, level=fg.DIFF_NORMAL)
            for game in (easy, normal):
                self._hire(game, "pedantisch", 1)
            key = "umsatz"
            hard = normal.state.quirk_value("test-1", key)
            soft = easy.state.quirk_value("test-1", key)
            self.assertLess(hard, 0)
            self.assertAlmostEqual(soft, hard * 0.5)
            # Die Staerke bleibt voll
            self.assertEqual(easy.state.quirk_value("test-1", "chance_netzwerk"),
                             normal.state.quirk_value("test-1", "chance_netzwerk"))
            # Auch bei Bewerbern steht die halbe Schwaeche
            for item in fg.applicants(easy.state, self.content):
                other = next(entry for entry in fg.applicants(normal.state, self.content)
                             if entry["id"] == item["id"])
                self.assertAlmostEqual(item["macke_info"]["faktor"],
                                       other["macke_info"]["faktor"] * 0.5)

    def test_kein_gegenwind_kein_abschwung(self):
        with TempDB() as easy_db, TempDB() as normal_db:
            easy = self._founded(easy_db)
            normal = self._founded(normal_db, level=fg.DIFF_NORMAL)
            easy_state = self._offers(easy_db, easy, [True] * 10, first_day=20)
            normal_state = self._offers(normal_db, normal, [True] * 10, first_day=20)
            self.assertTrue(fg.rivalry_pressure(normal_state, 50, self.content)["aktiv"])
            self.assertFalse(fg.rivalry_pressure(easy_state, 50, self.content)["aktiv"])
            start = int(self.content["firma"]["markt"]["ab_tag"])
            easy_phases = {fg.market_state(easy_state, day, self.content)["phase"]
                           for day in range(start, start + 400)}
            normal_phases = {fg.market_state(normal_state, day, self.content)["phase"]
                             for day in range(start, start + 400)}
            self.assertIn("abschwung", normal_phases)
            self.assertNotIn("abschwung", easy_phases)
            self.assertIn("aufschwung", easy_phases)

    def test_falsches_ticket_kostet_die_haelfte(self):
        with TempDB() as easy_db, TempDB() as normal_db:
            results = {}
            for db, level in ((easy_db, fg.DIFF_EASY), (normal_db, fg.DIFF_NORMAL)):
                game = fg.Game(db, "PC", self.content)
                game.set_profile("Nico", {}, level)
                task = game.state.open_tickets()[0]
                results[level] = game.solve(task["id"], _wrong_answer(task), True)
            hard, soft = results[fg.DIFF_NORMAL], results[fg.DIFF_EASY]
            self.assertFalse(hard["richtig"] or soft["richtig"])
            self.assertEqual(soft["geld"], int(round(hard["geld"] * 0.5)))
            self.assertLess(sum(hard["reputation"].values()), sum(soft["reputation"].values()))
            self.assertLess(sum(soft["reputation"].values()), 0)

    def test_story_abzeichen(self):
        with TempDB() as easy_db, TempDB() as normal_db:
            easy = self._rich(easy_db)
            normal = self._rich(normal_db, level=fg.DIFF_NORMAL)
            for game in (easy, normal):
                game.check_achievements()
            self.assertIn(("story_einfach", 1), easy.state.achievements)
            self.assertNotIn(("story_normal", 1), easy.state.achievements)
            self.assertIn(("story_normal", 1), normal.state.achievements)
            self.assertNotIn(("story_einfach", 1), normal.state.achievements)
            # Mit Meilenstein-Moment
            moments = [info["erfolg"] for info in easy.take_unlocks() if info["moment"]]
            self.assertIn("story_einfach", moments)
            # Drei Abzeichen gibt es auf Einfach nicht
            items = {item["id"]: item for item in fg.achievement_overview(easy.state)}
            for key in ("steuerehrlich", "zurueck_auf_kurs", "treue_mannschaft"):
                self.assertTrue(items[key]["nur_normal"], key)
                self.assertFalse(items[key]["balken"])
            self.assertEqual(fg.badge_status(items["steuerehrlich"])[0], "nur auf Normal")
            normal_items = {item["id"]: item for item in fg.achievement_overview(normal.state)}
            self.assertFalse(normal_items["steuerehrlich"]["nur_normal"])

    def test_alte_fertige_story_still_nachgetragen(self):
        with TempDB() as db:
            db.log_game_event(fg.EV_PROFILE, json.dumps({"name": "Nico", "aussehen": {}}), "PC")
            db.log_game_event(fg.EV_ACHIEVEMENT, json.dumps(
                {"erfolg": "erster_tag", "stufe": 1, "tag": 1}), "PC")
            db.log_game_event(fg.EV_SOLVED, json.dumps(
                {"aufgabe": self.task["id"], "tag": 1, "richtig": True, "geld": 0,
                 "reputation": {}}), "PC")
            db.log_game_event(fg.EV_DAY_END, json.dumps({"tag": 1, "gehalt": 0}), "PC")
            game = fg.Game(db, "PC", self.content)
            game.check_achievements()
            self.assertIn(("story_normal", 1), game.state.achievements)
            self.assertTrue(game.state.achievements[("story_normal", 1)]["nachgetragen"])
            self.assertEqual([info["erfolg"] for info in game.take_unlocks()
                              if info["erfolg"] == "story_normal"], [])


class SkillBalkenTest(unittest.TestCase):
    """Skill-Balken der Mitarbeiter (ab 0.47)."""

    def test_balken_je_fachbereich_und_thema(self):
        topics = {topic: 40 for topic in fg.TOPIC_ORDER}
        first = fg.CAT_TOPICS[fg.CAT_ORDER[0]][0]
        topics[first] = 80
        item = {"themen": topics, "werte": fg.cat_values(topics)}
        rows = fg.skill_bars(item)
        self.assertEqual([row["cat"] for row in rows], list(fg.CAT_ORDER))
        self.assertEqual(sum(len(row["themen"]) for row in rows), len(fg.TOPIC_ORDER))
        top = rows[0]
        self.assertEqual(top["wert"], item["werte"][fg.CAT_ORDER[0]])
        self.assertAlmostEqual(top["anteil"], top["wert"] / 100.0)
        topic = top["themen"][0]
        self.assertEqual((topic["thema"], topic["wert"], topic["anteil"]), (first, 80, 0.8))
        # Ab der Lern-Grenze (70) ist der Wert markiert
        self.assertTrue(topic["grenze"])
        self.assertFalse(top["themen"][1]["grenze"])
        # Die genauen Werte stehen auch im Text wie bisher
        self.assertIn("80", fg.topics_text(topics, fg.CAT_ORDER[0]))


if __name__ == "__main__":
    unittest.main(verbosity=1)
